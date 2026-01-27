"""
HTTP Transport for MCP Server.

Provides HTTP-based transport for MCP protocol, supporting:
- JSON-RPC over HTTP POST
- Server-Sent Events (SSE) for streaming responses
- WebSocket for bidirectional communication
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional
import asyncio
import json
import logging
import secrets
import time
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_429_TOO_MANY_REQUESTS

from .server import MCPServer
from .protocol import MCPRequest, MCPResponse, MCPErrorCode

logger = logging.getLogger(__name__)


# =============================================================================
# Data Models
# =============================================================================


class TransportType(str, Enum):
    """MCP transport types."""
    HTTP = "http"
    SSE = "sse"
    WEBSOCKET = "websocket"


@dataclass
class MCPSession:
    """Represents an MCP client session."""
    session_id: str
    created_at: datetime
    last_activity: datetime
    transport: TransportType
    client_info: Dict[str, Any]
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    is_initialized: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HTTPTransportConfig:
    """Configuration for HTTP transport."""
    # Session management
    session_timeout_seconds: int = 3600  # 1 hour
    max_sessions: int = 1000

    # Rate limiting
    requests_per_minute: int = 60
    requests_per_second: int = 10

    # Request limits
    max_request_size_bytes: int = 10 * 1024 * 1024  # 10MB
    request_timeout_seconds: int = 30

    # SSE configuration
    sse_heartbeat_seconds: int = 30
    sse_max_connections: int = 100

    # WebSocket configuration
    ws_ping_interval_seconds: int = 30
    ws_max_connections: int = 100

    # Security
    require_auth: bool = True
    allowed_origins: List[str] = field(default_factory=list)


class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0 request."""
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Any] = None


class JSONRPCResponse(BaseModel):
    """JSON-RPC 2.0 response."""
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[Any] = None


class JSONRPCError(BaseModel):
    """JSON-RPC 2.0 error."""
    code: int
    message: str
    data: Optional[Any] = None


# =============================================================================
# Session Manager
# =============================================================================


class SessionManager:
    """Manages MCP client sessions."""

    def __init__(self, config: HTTPTransportConfig):
        self.config = config
        self._sessions: Dict[str, MCPSession] = {}
        self._session_servers: Dict[str, MCPServer] = {}
        self._lock = asyncio.Lock()

    async def create_session(
        self,
        transport: TransportType,
        client_info: Dict[str, Any],
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
    ) -> MCPSession:
        """Create a new session."""
        async with self._lock:
            # Check session limit
            if len(self._sessions) >= self.config.max_sessions:
                # Remove oldest inactive session
                await self._cleanup_oldest_session()

            session_id = secrets.token_urlsafe(32)
            now = datetime.utcnow()

            session = MCPSession(
                session_id=session_id,
                created_at=now,
                last_activity=now,
                transport=transport,
                client_info=client_info,
                user_id=user_id,
                organization_id=organization_id,
            )

            self._sessions[session_id] = session
            logger.info(f"Created MCP session: {session_id} ({transport.value})")

            return session

    async def get_session(self, session_id: str) -> Optional[MCPSession]:
        """Get session by ID."""
        session = self._sessions.get(session_id)

        if session:
            # Check if expired
            elapsed = (datetime.utcnow() - session.last_activity).total_seconds()
            if elapsed > self.config.session_timeout_seconds:
                await self.destroy_session(session_id)
                return None

            # Update activity
            session.last_activity = datetime.utcnow()

        return session

    async def destroy_session(self, session_id: str) -> bool:
        """Destroy a session."""
        async with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                if session_id in self._session_servers:
                    del self._session_servers[session_id]
                logger.info(f"Destroyed MCP session: {session_id}")
                return True
            return False

    def get_server_for_session(
        self,
        session_id: str,
        server_factory: Callable[[], MCPServer],
    ) -> Optional[MCPServer]:
        """Get or create MCP server for session."""
        if session_id not in self._sessions:
            return None

        if session_id not in self._session_servers:
            self._session_servers[session_id] = server_factory()

        return self._session_servers[session_id]

    async def _cleanup_oldest_session(self) -> None:
        """Remove the oldest inactive session."""
        if not self._sessions:
            return

        oldest_id = min(
            self._sessions.keys(),
            key=lambda k: self._sessions[k].last_activity,
        )
        await self.destroy_session(oldest_id)

    async def cleanup_expired_sessions(self) -> int:
        """Cleanup all expired sessions."""
        now = datetime.utcnow()
        expired = []

        for session_id, session in self._sessions.items():
            elapsed = (now - session.last_activity).total_seconds()
            if elapsed > self.config.session_timeout_seconds:
                expired.append(session_id)

        for session_id in expired:
            await self.destroy_session(session_id)

        return len(expired)

    def get_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        now = datetime.utcnow()
        by_transport = {}
        active_count = 0

        for session in self._sessions.values():
            transport = session.transport.value
            by_transport[transport] = by_transport.get(transport, 0) + 1

            elapsed = (now - session.last_activity).total_seconds()
            if elapsed < 300:  # Active in last 5 minutes
                active_count += 1

        return {
            "total_sessions": len(self._sessions),
            "active_sessions": active_count,
            "by_transport": by_transport,
            "max_sessions": self.config.max_sessions,
        }


# =============================================================================
# Rate Limiter
# =============================================================================


class TransportRateLimiter:
    """Rate limiter for HTTP transport."""

    def __init__(self, config: HTTPTransportConfig):
        self.config = config
        self._requests: Dict[str, List[float]] = {}  # key -> timestamps
        self._lock = asyncio.Lock()

    async def check_rate_limit(self, key: str) -> tuple[bool, Optional[int]]:
        """
        Check if request is allowed.

        Returns:
            (allowed, retry_after_seconds)
        """
        async with self._lock:
            now = time.time()

            if key not in self._requests:
                self._requests[key] = []

            # Clean old timestamps
            minute_ago = now - 60
            second_ago = now - 1
            self._requests[key] = [t for t in self._requests[key] if t > minute_ago]

            # Check per-minute limit
            if len(self._requests[key]) >= self.config.requests_per_minute:
                oldest = min(self._requests[key])
                retry_after = int(60 - (now - oldest)) + 1
                return False, retry_after

            # Check per-second limit
            recent = [t for t in self._requests[key] if t > second_ago]
            if len(recent) >= self.config.requests_per_second:
                return False, 1

            # Allow request
            self._requests[key].append(now)
            return True, None

    async def cleanup(self) -> None:
        """Cleanup old entries."""
        async with self._lock:
            now = time.time()
            minute_ago = now - 60

            for key in list(self._requests.keys()):
                self._requests[key] = [t for t in self._requests[key] if t > minute_ago]
                if not self._requests[key]:
                    del self._requests[key]


# =============================================================================
# HTTP Transport
# =============================================================================


class MCPHTTPTransport:
    """
    HTTP Transport for MCP Server.

    Provides multiple transport options:
    - JSON-RPC over HTTP POST
    - Server-Sent Events (SSE) for real-time updates
    - WebSocket for bidirectional communication
    """

    def __init__(
        self,
        server_factory: Callable[[], MCPServer],
        config: Optional[HTTPTransportConfig] = None,
    ):
        self.server_factory = server_factory
        self.config = config or HTTPTransportConfig()
        self.session_manager = SessionManager(self.config)
        self.rate_limiter = TransportRateLimiter(self.config)

        # SSE connections
        self._sse_connections: Dict[str, asyncio.Queue] = {}

        # WebSocket connections
        self._ws_connections: Dict[str, WebSocket] = {}

        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None

    def create_router(self, prefix: str = "/mcp") -> APIRouter:
        """Create FastAPI router for MCP HTTP transport."""
        router = APIRouter(prefix=prefix, tags=["mcp"])

        # JSON-RPC endpoint
        @router.post("")
        async def handle_jsonrpc(request: Request) -> JSONRPCResponse:
            return await self._handle_http_request(request)

        @router.post("/")
        async def handle_jsonrpc_slash(request: Request) -> JSONRPCResponse:
            return await self._handle_http_request(request)

        # Session management
        @router.post("/session")
        async def create_session(request: Request) -> Dict[str, Any]:
            return await self._create_session_endpoint(request)

        @router.delete("/session/{session_id}")
        async def destroy_session(session_id: str) -> Dict[str, str]:
            success = await self.session_manager.destroy_session(session_id)
            if not success:
                raise HTTPException(status_code=404, detail="Session not found")
            return {"status": "destroyed"}

        @router.get("/session/{session_id}")
        async def get_session_info(session_id: str) -> Dict[str, Any]:
            session = await self.session_manager.get_session(session_id)
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
            return {
                "session_id": session.session_id,
                "created_at": session.created_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
                "transport": session.transport.value,
                "is_initialized": session.is_initialized,
            }

        # SSE endpoint
        @router.get("/sse/{session_id}")
        async def sse_endpoint(session_id: str, request: Request):
            return await self._handle_sse_connection(session_id, request)

        # WebSocket endpoint
        @router.websocket("/ws/{session_id}")
        async def ws_endpoint(websocket: WebSocket, session_id: str):
            await self._handle_websocket_connection(websocket, session_id)

        # Health and stats
        @router.get("/health")
        async def health() -> Dict[str, str]:
            return {"status": "healthy"}

        @router.get("/stats")
        async def stats() -> Dict[str, Any]:
            return {
                "sessions": self.session_manager.get_stats(),
                "sse_connections": len(self._sse_connections),
                "ws_connections": len(self._ws_connections),
            }

        return router

    async def start(self) -> None:
        """Start background tasks."""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("MCP HTTP transport started")

    async def stop(self) -> None:
        """Stop background tasks."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Close all SSE connections
        for queue in self._sse_connections.values():
            await queue.put(None)  # Signal to close

        # Close all WebSocket connections
        for ws in self._ws_connections.values():
            await ws.close()

        logger.info("MCP HTTP transport stopped")

    async def _cleanup_loop(self) -> None:
        """Background cleanup loop."""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute

                # Cleanup expired sessions
                expired = await self.session_manager.cleanup_expired_sessions()
                if expired:
                    logger.info(f"Cleaned up {expired} expired MCP sessions")

                # Cleanup rate limiter
                await self.rate_limiter.cleanup()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Error in cleanup loop: {e}")

    async def _create_session_endpoint(self, request: Request) -> Dict[str, Any]:
        """Handle session creation."""
        try:
            body = await request.json()
        except Exception:
            body = {}

        # Extract auth info from request
        user_id = request.headers.get("X-User-ID")
        organization_id = request.headers.get("X-Organization-ID")

        # Validate auth if required
        if self.config.require_auth and not user_id:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        session = await self.session_manager.create_session(
            transport=TransportType.HTTP,
            client_info=body.get("clientInfo", {}),
            user_id=user_id,
            organization_id=organization_id,
        )

        return {
            "session_id": session.session_id,
            "created_at": session.created_at.isoformat(),
            "expires_in": self.config.session_timeout_seconds,
        }

    async def _handle_http_request(self, request: Request) -> JSONRPCResponse:
        """Handle JSON-RPC over HTTP request."""
        # Get session from header
        session_id = request.headers.get("X-MCP-Session")

        # Rate limit by session or IP
        rate_key = session_id or request.client.host if request.client else "unknown"
        allowed, retry_after = await self.rate_limiter.check_rate_limit(rate_key)

        if not allowed:
            raise HTTPException(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(retry_after)},
            )

        # Parse request
        try:
            body = await request.json()
            jsonrpc_request = JSONRPCRequest(**body)
        except Exception as e:
            return JSONRPCResponse(
                error=JSONRPCError(
                    code=-32700,
                    message="Parse error",
                    data=str(e),
                ).dict(),
            )

        # Get or create session
        session = None
        if session_id:
            session = await self.session_manager.get_session(session_id)

        if not session and self.config.require_auth:
            return JSONRPCResponse(
                id=jsonrpc_request.id,
                error=JSONRPCError(
                    code=-32001,
                    message="Session required",
                    data="Create a session first via POST /mcp/session",
                ).dict(),
            )

        # Get server for session
        server = self.session_manager.get_server_for_session(
            session_id or "default",
            self.server_factory,
        )

        if not server:
            server = self.server_factory()

        # Build context
        context = {
            "transport": "http",
            "session_id": session_id,
            "user_id": session.user_id if session else request.headers.get("X-User-ID"),
            "organization_id": session.organization_id if session else request.headers.get("X-Organization-ID"),
            "client_ip": request.client.host if request.client else None,
        }

        # Convert to MCP request
        mcp_request = MCPRequest(
            id=jsonrpc_request.id or str(uuid4()),
            method=jsonrpc_request.method,
            params=jsonrpc_request.params or {},
        )

        # Handle request
        try:
            mcp_response = await asyncio.wait_for(
                server.handle_request(mcp_request, context),
                timeout=self.config.request_timeout_seconds,
            )
        except asyncio.TimeoutError:
            return JSONRPCResponse(
                id=jsonrpc_request.id,
                error=JSONRPCError(
                    code=-32000,
                    message="Request timeout",
                ).dict(),
            )

        # Update session if initialized
        if session and mcp_request.method == "initialize":
            session.is_initialized = True

        # Convert to JSON-RPC response
        if mcp_response.error:
            return JSONRPCResponse(
                id=mcp_response.id,
                error=JSONRPCError(
                    code=mcp_response.error.code,
                    message=mcp_response.error.message,
                    data=mcp_response.error.data,
                ).dict(),
            )

        return JSONRPCResponse(
            id=mcp_response.id,
            result=mcp_response.result,
        )

    async def _handle_sse_connection(
        self,
        session_id: str,
        request: Request,
    ) -> StreamingResponse:
        """Handle Server-Sent Events connection."""
        # Validate session
        session = await self.session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Check connection limit
        if len(self._sse_connections) >= self.config.sse_max_connections:
            raise HTTPException(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many SSE connections",
            )

        # Create message queue for this connection
        queue: asyncio.Queue = asyncio.Queue()
        self._sse_connections[session_id] = queue

        async def event_generator() -> AsyncGenerator[str, None]:
            try:
                while True:
                    # Wait for message or timeout for heartbeat
                    try:
                        message = await asyncio.wait_for(
                            queue.get(),
                            timeout=self.config.sse_heartbeat_seconds,
                        )

                        if message is None:
                            break

                        yield f"data: {json.dumps(message)}\n\n"

                    except asyncio.TimeoutError:
                        # Send heartbeat
                        yield f": heartbeat\n\n"

            finally:
                # Cleanup
                if session_id in self._sse_connections:
                    del self._sse_connections[session_id]

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    async def send_sse_message(self, session_id: str, message: Dict[str, Any]) -> bool:
        """Send a message to SSE client."""
        queue = self._sse_connections.get(session_id)
        if queue:
            await queue.put(message)
            return True
        return False

    async def _handle_websocket_connection(
        self,
        websocket: WebSocket,
        session_id: str,
    ) -> None:
        """Handle WebSocket connection."""
        # Validate session
        session = await self.session_manager.get_session(session_id)
        if not session:
            await websocket.close(code=4004, reason="Session not found")
            return

        # Check connection limit
        if len(self._ws_connections) >= self.config.ws_max_connections:
            await websocket.close(code=4029, reason="Too many connections")
            return

        await websocket.accept()
        self._ws_connections[session_id] = websocket

        # Update session transport
        session.transport = TransportType.WEBSOCKET

        # Get server for session
        server = self.session_manager.get_server_for_session(
            session_id,
            self.server_factory,
        )

        try:
            while True:
                # Receive message
                try:
                    data = await asyncio.wait_for(
                        websocket.receive_json(),
                        timeout=self.config.ws_ping_interval_seconds * 2,
                    )
                except asyncio.TimeoutError:
                    # Send ping
                    await websocket.send_json({"type": "ping"})
                    continue

                # Handle ping/pong
                if data.get("type") == "pong":
                    continue

                # Parse JSON-RPC request
                try:
                    jsonrpc_request = JSONRPCRequest(**data)
                except Exception as e:
                    await websocket.send_json(
                        JSONRPCResponse(
                            error=JSONRPCError(
                                code=-32700,
                                message="Parse error",
                                data=str(e),
                            ).dict(),
                        ).dict()
                    )
                    continue

                # Build context
                context = {
                    "transport": "websocket",
                    "session_id": session_id,
                    "user_id": session.user_id,
                    "organization_id": session.organization_id,
                }

                # Convert to MCP request
                mcp_request = MCPRequest(
                    id=jsonrpc_request.id or str(uuid4()),
                    method=jsonrpc_request.method,
                    params=jsonrpc_request.params or {},
                )

                # Handle request
                mcp_response = await server.handle_request(mcp_request, context)

                # Send response
                if mcp_response.error:
                    response = JSONRPCResponse(
                        id=mcp_response.id,
                        error=JSONRPCError(
                            code=mcp_response.error.code,
                            message=mcp_response.error.message,
                            data=mcp_response.error.data,
                        ).dict(),
                    )
                else:
                    response = JSONRPCResponse(
                        id=mcp_response.id,
                        result=mcp_response.result,
                    )

                await websocket.send_json(response.dict())

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: {session_id}")
        except Exception as e:
            logger.exception(f"WebSocket error: {e}")
        finally:
            if session_id in self._ws_connections:
                del self._ws_connections[session_id]

    async def send_ws_message(self, session_id: str, message: Dict[str, Any]) -> bool:
        """Send a message to WebSocket client."""
        ws = self._ws_connections.get(session_id)
        if ws:
            try:
                await ws.send_json(message)
                return True
            except Exception:
                return False
        return False


# =============================================================================
# Singleton
# =============================================================================


_http_transport: Optional[MCPHTTPTransport] = None


def get_mcp_http_transport() -> Optional[MCPHTTPTransport]:
    """Get the singleton HTTP transport instance."""
    return _http_transport


def create_mcp_http_transport(
    server_factory: Callable[[], MCPServer],
    config: Optional[HTTPTransportConfig] = None,
) -> MCPHTTPTransport:
    """Create and set the singleton HTTP transport."""
    global _http_transport
    _http_transport = MCPHTTPTransport(server_factory, config)
    return _http_transport


def reset_mcp_http_transport() -> None:
    """Reset the singleton (for testing)."""
    global _http_transport
    _http_transport = None
