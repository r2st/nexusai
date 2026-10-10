"""Chat API endpoints with MCP support."""

import time

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import json
import re
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.conversation import ModelProvider
from app.models.user import User
from app.services.chat import ChatService
from app.services.agents.mcp import MCPServerConfig, MCPTransport

router = APIRouter()
logger = structlog.get_logger()


def get_default_provider() -> ModelProvider:
    """Get the default model provider from environment settings.

    Respects DEFAULT_AI_PROVIDER from environment. Falls back to checking
    available API keys if the configured provider's key is missing.
    """
    # First, check if DEFAULT_AI_PROVIDER is set in environment
    default_provider = getattr(settings, "DEFAULT_AI_PROVIDER", "").lower()

    if default_provider == "google" and settings.GOOGLE_API_KEY:
        return ModelProvider.GOOGLE
    if default_provider == "anthropic" and settings.ANTHROPIC_API_KEY:
        return ModelProvider.ANTHROPIC
    if default_provider == "openai" and settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("sk-your"):
        return ModelProvider.OPENAI
    if default_provider == "ollama":
        return ModelProvider.OLLAMA

    # Fallback: check API keys in order of preference if default provider not available
    if settings.GOOGLE_API_KEY:
        return ModelProvider.GOOGLE
    if settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("sk-your"):
        return ModelProvider.OPENAI
    if settings.ANTHROPIC_API_KEY:
        return ModelProvider.ANTHROPIC

    # Final fallback to Ollama (local, no API key needed)
    return ModelProvider.OLLAMA


class CreateConversationRequest(BaseModel):
    """Create conversation request."""

    title: str = Field(default="New Conversation", max_length=500)
    model_provider: ModelProvider | None = None  # None means auto-detect
    model_name: str | None = Field(default=None, max_length=200)
    system_prompt: str | None = Field(default=None, max_length=50000)


class ConversationResponse(BaseModel):
    """Conversation response model."""

    id: str
    title: str
    model_provider: str
    model_name: str
    message_count: int
    total_tokens: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """Message response model."""

    id: str
    role: str
    content: str
    model_name: str | None
    created_at: str
    tool_calls: list[dict] | None = None
    tool_results: list[dict] | None = None

    class Config:
        from_attributes = True


class MCPServerConfigRequest(BaseModel):
    """MCP server configuration for chat."""

    name: str
    transport: str = "http"
    url: str | None = None
    command: str | None = None
    args: list[str] = []
    env: dict[str, str] = {}
    headers: dict[str, str] = {}
    timeout_seconds: int = 30


class ChatRequest(BaseModel):
    """Chat request with MCP support."""

    message: str = Field(..., min_length=1, max_length=100000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1, le=128000)
    stream: bool = True
    use_mcp: bool = True
    mcp_servers: list[MCPServerConfigRequest] = Field(default_factory=list, max_length=10)


class ChatResponse(BaseModel):
    """Chat response (non-streaming)."""

    message: MessageResponse
    conversation: ConversationResponse


TOOL_CALL_FENCE = re.compile(r"```tool_call\s*([\s\S]*?)```", re.IGNORECASE)
TOOL_RESULT_FENCE = re.compile(r"```tool_result\s*([\s\S]*?)```", re.IGNORECASE)
TOOL_CALL_INLINE = re.compile(r"\[Calling tool:\s*([^\]]+?)\.\.\.\]")
TOOL_RESULT_INLINE = re.compile(r"\[Tool result:\s*([^\]]+)\]")


def _parse_tool_payloads(content: str) -> tuple[list[dict], list[dict]]:
    tool_calls: list[dict] = []
    tool_results: list[dict] = []

    for match in TOOL_CALL_FENCE.finditer(content):
        try:
            parsed = json.loads(match.group(1).strip())
            if isinstance(parsed, dict) and "name" in parsed:
                tool_calls.append(parsed)
        except json.JSONDecodeError:
            continue

    for match in TOOL_RESULT_FENCE.finditer(content):
        try:
            parsed = json.loads(match.group(1).strip())
            if isinstance(parsed, dict):
                tool_results.append(parsed)
        except json.JSONDecodeError:
            continue

    for match in TOOL_CALL_INLINE.finditer(content):
        name = match.group(1).strip()
        if name:
            tool_calls.append({"name": name, "status": "running"})

    for match in TOOL_RESULT_INLINE.finditer(content):
        output = match.group(1).strip()
        if output:
            tool_results.append({"output": output, "success": True})

    return tool_calls, tool_results


@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    request: CreateConversationRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    """Create a new conversation."""
    chat_service = ChatService(db)

    # Use default provider if not specified
    model_provider = request.model_provider or get_default_provider()

    conversation = await chat_service.create_conversation(
        user_id=user.id,
        title=request.title,
        model_provider=model_provider,
        model_name=request.model_name,
        system_prompt=request.system_prompt,
    )

    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        model_provider=conversation.model_provider,
        model_name=conversation.model_name,
        message_count=conversation.message_count,
        total_tokens=conversation.total_tokens,
        created_at=conversation.created_at.isoformat(),
        updated_at=conversation.updated_at.isoformat(),
    )


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    limit: int = 50,
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ConversationResponse]:
    """List user's conversations."""
    chat_service = ChatService(db)
    conversations = await chat_service.list_conversations(user.id, limit, offset)

    return [
        ConversationResponse(
            id=c.id,
            title=c.title,
            model_provider=c.model_provider,
            model_name=c.model_name,
            message_count=c.message_count,
            total_tokens=c.total_tokens,
            created_at=c.created_at.isoformat(),
            updated_at=c.updated_at.isoformat(),
        )
        for c in conversations
    ]


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    """Get a conversation by ID."""
    chat_service = ChatService(db)
    conversation = await chat_service.get_conversation(conversation_id, user.id)

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        model_provider=conversation.model_provider,
        model_name=conversation.model_name,
        message_count=conversation.message_count,
        total_tokens=conversation.total_tokens,
        created_at=conversation.created_at.isoformat(),
        updated_at=conversation.updated_at.isoformat(),
    )


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MessageResponse]:
    """Get messages for a conversation."""
    chat_service = ChatService(db)

    # Verify conversation belongs to user
    conversation = await chat_service.get_conversation(conversation_id, user.id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    messages = await chat_service.get_messages(conversation_id)

    response_messages = []
    for m in messages:
        tool_calls, tool_results = _parse_tool_payloads(m.content)
        response_messages.append(
            MessageResponse(
                id=m.id,
                role=m.role,
                content=m.content,
                model_name=m.model_name,
                created_at=m.created_at.isoformat(),
                tool_calls=tool_calls,
                tool_results=tool_results,
            )
        )
    return response_messages


@router.post("/conversations/{conversation_id}/chat")
async def chat(
    conversation_id: str,
    request: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a message and get AI response with optional MCP tool support."""
    chat_start = time.perf_counter()
    # Parse external MCP server configs
    mcp_servers = []
    for server_data in request.mcp_servers:
        try:
            mcp_servers.append(MCPServerConfig(
                name=server_data.name,
                transport=MCPTransport(server_data.transport),
                url=server_data.url,
                command=server_data.command,
                args=server_data.args,
                env=server_data.env,
                headers=server_data.headers,
                timeout_seconds=server_data.timeout_seconds,
            ))
        except Exception as e:
            logger.warning("Failed to parse MCP server config", error=str(e))

    # Create chat service with built-in DevLake tools enabled by default
    chat_service = ChatService(
        db=db,
        user_id=user.id,
        mcp_servers=mcp_servers if mcp_servers else None,
        enable_builtin_tools=request.use_mcp,  # Enable built-in DevLake tools
    )

    # Initialize MCP (built-in tools + any external servers)
    if request.use_mcp:
        await chat_service.initialize_mcp()

    try:
        # Get conversation
        conversation = await chat_service.get_conversation(conversation_id, user.id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )

        if request.stream:
            # Streaming response with MCP support
            async def generate():
                try:
                    async for chunk in chat_service.chat_stream(
                        conversation=conversation,
                        user_message=request.message,
                        temperature=request.temperature,
                        max_tokens=request.max_tokens,
                        use_mcp_tools=request.use_mcp,
                    ):
                        yield f"data: {chunk}\n\n"
                    yield "data: [DONE]\n\n"
                finally:
                    # Cleanup MCP connections
                    if request.use_mcp:
                        await chat_service.cleanup_mcp()

            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )
        else:
            # Non-streaming response
            message = await chat_service.chat(
                conversation=conversation,
                user_message=request.message,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )

            duration_ms = round((time.perf_counter() - chat_start) * 1000, 2)
            logger.info(
                "Chat response generated",
                conversation_id=conversation_id,
                user_id=str(user.id),
                model=conversation.model_name,
                duration_ms=duration_ms,
            )

            tool_calls, tool_results = _parse_tool_payloads(message.content)
            return ChatResponse(
                message=MessageResponse(
                    id=message.id,
                    role=message.role,
                    content=message.content,
                    model_name=message.model_name,
                    created_at=message.created_at.isoformat(),
                    tool_calls=tool_calls,
                    tool_results=tool_results,
                ),
                conversation=ConversationResponse(
                    id=conversation.id,
                    title=conversation.title,
                    model_provider=conversation.model_provider,
                    model_name=conversation.model_name,
                    message_count=conversation.message_count,
                    total_tokens=conversation.total_tokens,
                    created_at=conversation.created_at.isoformat(),
                    updated_at=conversation.updated_at.isoformat(),
                ),
            )
    finally:
        # Cleanup MCP connections for non-streaming
        if not request.stream and request.use_mcp:
            await chat_service.cleanup_mcp()


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a conversation."""
    chat_service = ChatService(db)

    conversation = await chat_service.get_conversation(conversation_id, user.id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    await chat_service.delete_conversation(conversation)


@router.get("/tools")
async def list_available_tools(
    user: User = Depends(get_current_user),
):
    """List all available chat tools (all MCP tools across all services)."""
    from app.services.mcp import get_all_tools_summary, list_available_tools

    try:
        summary = get_all_tools_summary()
        tools = list_available_tools()

        return {
            "total_tools": summary["total_tools"],
            "services": summary["services"],
            "service_descriptions": summary["service_descriptions"],
            "tools": tools,
        }
    except Exception as e:
        logger.error("Failed to list tools", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list available tools. Please try again later.",
        )
