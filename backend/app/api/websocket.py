"""WebSocket endpoints for real-time chat with MCP support."""

import asyncio
import json
import time
from collections import deque
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from starlette.websockets import WebSocketState
import re
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.database import get_db_context
from app.core.config import settings
from app.core.security import decode_token
from app.models.conversation import ModelProvider
from app.models.user import User
from app.services.chat import ChatService
from app.services.agents.mcp import MCPServerConfig, MCPTransport
from sqlalchemy import select

logger = structlog.get_logger()

TOOL_CALL_INLINE = re.compile(r"\[Calling tool:\s*([^\]]+?)\.\.\.\]")
TOOL_RESULT_INLINE = re.compile(r"\[Tool result:\s*([^\]]+)\]")

router = APIRouter()


IDLE_TIMEOUT_SECONDS = settings.WS_IDLE_TIMEOUT_SECONDS
RATE_LIMIT_WINDOW_SECONDS = settings.WS_RATE_LIMIT_WINDOW_SECONDS
MAX_MESSAGES_PER_WINDOW = settings.WS_MAX_MESSAGES_PER_WINDOW


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        # Map of user_id -> list of connections
        self.active_connections: dict[str, list[WebSocket]] = {}
        # Map of websocket -> user_id for quick lookup
        self.connection_users: dict[WebSocket, str] = {}
        # Per-connection metadata for telemetry/rate limiting
        self.connection_meta: dict[WebSocket, dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept and track a new connection."""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        self.connection_users[websocket] = user_id
        self.connection_meta[websocket] = {
            "connected_at": time.time(),
            "last_activity_at": time.time(),
            "message_count": 0,
            "message_timestamps": deque(),
        }
        logger.info(
            "WebSocket connected",
            user_id=user_id,
            websocket_id=id(websocket),
            connections=len(self.active_connections[user_id]),
        )

    def disconnect(self, websocket: WebSocket):
        """Remove a connection."""
        user_id = self.connection_users.get(websocket)
        if user_id and user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        if websocket in self.connection_users:
            del self.connection_users[websocket]
        meta = self.connection_meta.pop(websocket, None)
        duration = None
        if meta and meta.get("connected_at"):
            duration = int(time.time() - meta["connected_at"])
        logger.info(
            "WebSocket disconnected",
            user_id=user_id,
            websocket_id=id(websocket),
            duration_seconds=duration,
        )

    def touch(self, websocket: WebSocket) -> None:
        """Update activity timestamp."""
        meta = self.connection_meta.get(websocket)
        if meta:
            meta["last_activity_at"] = time.time()

    def register_message(self, websocket: WebSocket) -> bool:
        """Track inbound message and enforce a simple rate limit."""
        meta = self.connection_meta.get(websocket)
        if not meta:
            return True

        now = time.time()
        timestamps: deque[float] = meta["message_timestamps"]
        while timestamps and now - timestamps[0] > RATE_LIMIT_WINDOW_SECONDS:
            timestamps.popleft()
        timestamps.append(now)
        meta["message_count"] += 1
        return len(timestamps) <= MAX_MESSAGES_PER_WINDOW

    async def send_message(self, websocket: WebSocket, message: dict[str, Any]):
        """Send a message to a specific connection."""
        if websocket.application_state != WebSocketState.CONNECTED:
            logger.debug(
                "Skipping WebSocket send; not connected",
                websocket_id=id(websocket),
                state=websocket.application_state,
                message_type=message.get("type"),
            )
            return
        if message.get("type") == "error":
            error_payload = message.get("error")
            if not isinstance(error_payload, str) or not error_payload.strip():
                logger.warning(
                    "WebSocket error payload is empty or non-string",
                    websocket_id=id(websocket),
                    error_payload=error_payload,
                )
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error("Failed to send WebSocket message", error=str(e))

    async def broadcast_to_user(self, user_id: str, message: dict[str, Any]):
        """Broadcast a message to all connections of a user."""
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                await self.send_message(connection, message)


# Global connection manager
manager = ConnectionManager()


async def get_user_from_token(token: str, db: AsyncSession) -> User | None:
    """Validate token and get user."""
    try:
        token_data = decode_token(token)
        if not token_data:
            return None
        
        user_id = token_data.user_id
        if not user_id:
            return None
        
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error("Token validation failed", error=str(e))
        return None


@router.websocket("/chat")
async def websocket_chat(
    websocket: WebSocket,
    token: str = Query(...),
):
    """
    WebSocket endpoint for chat.
    
    Connect with: ws://localhost:8000/api/v1/ws/chat?token=<access_token>
    
    Message formats:
    
    Client -> Server:
    {
        "type": "chat",
        "conversation_id": "uuid",
        "message": "Hello!",
        "temperature": 0.7,  // optional
        "max_tokens": 4096   // optional
    }
    
    {
        "type": "new_conversation",
        "title": "New Chat",
        "model_provider": "google",  // optional
        "model_name": "gemini-2.0-flash-exp"  // optional
    }
    
    {
        "type": "ping"
    }
    
    Server -> Client:
    {
        "type": "connected",
        "user_id": "uuid"
    }
    
    {
        "type": "conversation_created",
        "conversation": {...}
    }
    
    {
        "type": "message_start",
        "conversation_id": "uuid",
        "message_id": "uuid"
    }
    
    {
        "type": "token",
        "conversation_id": "uuid",
        "content": "Hello"
    }
    
    {
        "type": "message_complete",
        "conversation_id": "uuid",
        "message": {...}
    }
    
    {
        "type": "error",
        "error": "Error message"
    }
    
    {
        "type": "pong"
    }
    """
    # Use context manager for proper session lifecycle
    async with get_db_context() as db:
        # Authenticate user
        user = await get_user_from_token(token, db)
        if not user:
            await websocket.close(code=4001, reason="Invalid or expired token")
            return

        # Accept connection
        await manager.connect(websocket, str(user.id))

        try:
            # Send connected confirmation
            await manager.send_message(websocket, {
                "type": "connected",
                "user_id": str(user.id),
            })

            # Handle messages
            while True:
                if websocket.application_state != WebSocketState.CONNECTED:
                    logger.info(
                        "WebSocket not connected; stopping receive loop",
                        user_id=str(user.id),
                        websocket_id=id(websocket),
                        state=websocket.application_state,
                    )
                    break
                try:
                    data = await asyncio.wait_for(
                        websocket.receive_json(),
                        timeout=IDLE_TIMEOUT_SECONDS,
                    )
                    logger.debug(
                        "WebSocket message received",
                        user_id=str(user.id),
                        websocket_id=id(websocket),
                        message_type=data.get("type"),
                        message_size=len(json.dumps(data, default=str)),
                    )
                    manager.touch(websocket)
                    if not manager.register_message(websocket):
                        await manager.send_message(websocket, {
                            "type": "error",
                            "error": "Rate limit exceeded",
                        })
                        await websocket.close(code=4008, reason="Rate limit exceeded")
                        break
                    await handle_message(websocket, user, data, db)
                except asyncio.TimeoutError:
                    logger.info(
                        "WebSocket idle timeout",
                        user_id=str(user.id),
                        websocket_id=id(websocket),
                    )
                    await websocket.close(code=4000, reason="Idle timeout")
                    break
                except WebSocketDisconnect:
                    logger.info(
                        "WebSocket disconnected during receive",
                        user_id=str(user.id),
                        websocket_id=id(websocket),
                    )
                    break
                except RuntimeError as e:
                    msg = str(e)
                    if "accept" in msg.lower() or "not connected" in msg.lower():
                        logger.warning(
                            "WebSocket receive after disconnect",
                            user_id=str(user.id),
                            websocket_id=id(websocket),
                            error=msg,
                        )
                        break
                    raise
                except json.JSONDecodeError:
                    await manager.send_message(websocket, {
                        "type": "error",
                        "error": "Invalid JSON",
                    })
                except Exception as e:
                    logger.error("WebSocket message handling error", error=str(e))
                    await manager.send_message(websocket, {
                        "type": "error",
                        "error": str(e),
                    })
        finally:
            manager.disconnect(websocket)


async def handle_message(
    websocket: WebSocket,
    user: User,
    data: dict[str, Any],
    db: AsyncSession,
):
    """Handle incoming WebSocket messages."""
    msg_type = data.get("type")

    if msg_type == "ping":
        await manager.send_message(websocket, {"type": "pong"})
        return

    if msg_type == "new_conversation":
        await handle_new_conversation(websocket, user, data, db)
        return

    if msg_type == "chat":
        await handle_chat(websocket, user, data, db)
        return

    await manager.send_message(websocket, {
        "type": "error",
        "error": f"Unknown message type: {msg_type}",
    })


async def handle_new_conversation(
    websocket: WebSocket,
    user: User,
    data: dict[str, Any],
    db: AsyncSession,
):
    """Handle creating a new conversation."""
    chat_service = ChatService(db)

    title = data.get("title", "New Conversation")
    model_provider_str = data.get("model_provider")
    model_name = data.get("model_name")

    # Determine model provider
    if model_provider_str:
        try:
            model_provider = ModelProvider(model_provider_str)
        except ValueError:
            model_provider = ModelProvider.GOOGLE
    else:
        # Auto-detect based on available API keys
        from app.api.chat import get_default_provider
        model_provider = get_default_provider()

    conversation = await chat_service.create_conversation(
        user_id=str(user.id),
        title=title,
        model_provider=model_provider,
        model_name=model_name,
    )

    await db.commit()

    await manager.send_message(websocket, {
        "type": "conversation_created",
        "conversation": {
            "id": str(conversation.id),
            "title": conversation.title,
            "model_provider": conversation.model_provider,
            "model_name": conversation.model_name,
            "message_count": conversation.message_count,
            "total_tokens": conversation.total_tokens,
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
        },
    })


async def handle_chat(
    websocket: WebSocket,
    user: User,
    data: dict[str, Any],
    db: AsyncSession,
):
    """Handle chat message and stream response with MCP support."""
    conversation_id = data.get("conversation_id")
    message = data.get("message")
    temperature = data.get("temperature", 0.7)
    max_tokens = data.get("max_tokens", 4096)
    use_mcp = data.get("use_mcp", True)  # Enable MCP by default
    mcp_servers_data = data.get("mcp_servers", [])  # Optional MCP server configs

    logger.info(
        "Handle chat called",
        user_id=str(user.id),
        conversation_id=conversation_id,
        message_preview=message[:100] if message else None,
        use_mcp=use_mcp,
    )

    if not conversation_id or not message:
        await manager.send_message(websocket, {
            "type": "error",
            "error": "conversation_id and message are required",
        })
        return

    # Parse external MCP server configs if provided
    mcp_servers = []
    for server_data in mcp_servers_data:
        try:
            mcp_servers.append(MCPServerConfig(
                name=server_data.get("name", "unknown"),
                transport=MCPTransport(server_data.get("transport", "http")),
                url=server_data.get("url"),
                command=server_data.get("command"),
                args=server_data.get("args", []),
                env=server_data.get("env", {}),
                headers=server_data.get("headers", {}),
                timeout_seconds=server_data.get("timeout_seconds", 30),
            ))
        except Exception as e:
            logger.warning("Failed to parse MCP server config", error=str(e))

    # Create chat service with built-in DevLake tools enabled by default
    chat_service = ChatService(
        db=db,
        user_id=str(user.id),
        mcp_servers=mcp_servers if mcp_servers else None,
        enable_builtin_tools=use_mcp,  # Enable built-in DevLake tools
    )

    # Initialize MCP (built-in tools + any external servers)
    if use_mcp:
        await chat_service.initialize_mcp()

    try:
        # Get conversation
        conversation = await chat_service.get_conversation(conversation_id, str(user.id))
        if not conversation:
            await manager.send_message(websocket, {
                "type": "error",
                "error": "Conversation not found",
            })
            return

        # Generate message ID for the assistant response
        assistant_message_id = str(uuid4())

        # Send message start
        await manager.send_message(websocket, {
            "type": "message_start",
            "conversation_id": str(conversation_id),
            "message_id": assistant_message_id,
        })

        # Stream the response
        full_content = ""
        tool_calls: list[dict[str, Any]] = []
        tool_results: list[dict[str, Any]] = []
        async for chunk in chat_service.chat_stream(
            conversation=conversation,
            user_message=message,
            temperature=temperature,
            max_tokens=max_tokens,
            use_mcp_tools=use_mcp,
        ):
            full_content += chunk
            for match in TOOL_CALL_INLINE.finditer(chunk):
                name = match.group(1).strip()
                if name:
                    tool_call = {"name": name, "status": "running"}
                    tool_calls.append(tool_call)
                    await manager.send_message(websocket, {
                        "type": "tool_call",
                        "conversation_id": str(conversation_id),
                        "tool_call": tool_call,
                    })
            for match in TOOL_RESULT_INLINE.finditer(chunk):
                output = match.group(1).strip()
                if output:
                    tool_result = {"output": output, "success": True}
                    tool_results.append(tool_result)
                    await manager.send_message(websocket, {
                        "type": "tool_result",
                        "conversation_id": str(conversation_id),
                        "tool_result": tool_result,
                    })
            await manager.send_message(websocket, {
                "type": "token",
                "conversation_id": str(conversation_id),
                "content": chunk,
            })

        await db.commit()

        # Send message complete
        await manager.send_message(websocket, {
            "type": "message_complete",
            "conversation_id": str(conversation_id),
            "message": {
                "id": assistant_message_id,
                "role": "assistant",
                "content": full_content,
                "model_name": conversation.model_name,
                "created_at": conversation.updated_at.isoformat(),
                "tool_calls": tool_calls,
                "tool_results": tool_results,
            },
        })

    except Exception as e:
        logger.error("Chat streaming error", error=str(e))
        await manager.send_message(websocket, {
            "type": "error",
            "error": f"Chat error: {str(e)}",
            "conversation_id": str(conversation_id),
        })
    finally:
        # Cleanup MCP connections
        if use_mcp:
            await chat_service.cleanup_mcp()
