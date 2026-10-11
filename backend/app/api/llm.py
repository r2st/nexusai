"""LLM Gateway API endpoints.

Provides REST API for interacting with the LLM Gateway including:
- Chat completions (sync and streaming)
- Provider management
- Model listing
- Gateway status and health
- Usage statistics
"""

from collections.abc import AsyncGenerator
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import structlog

from app.api.deps import get_current_user, get_current_user_optional
from app.models.user import User
from app.services.llm_gateway.service import get_gateway, LLMGateway
from app.services.llm_gateway.models import (
    GatewayStatus,
    LLMRequest,
    Message,
    MessageRole,
    ProviderStatus,
    RateLimitInfo,
    UsageStats,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/llm", tags=["llm"])


# =============================================================================
# Request/Response Models
# =============================================================================


class ChatMessage(BaseModel):
    """Chat message input."""

    role: str = Field(..., description="Message role: system, user, assistant, or tool")
    content: str = Field(..., description="Message content")
    name: str | None = Field(None, description="Optional name for the message sender")
    tool_call_id: str | None = Field(None, description="Tool call ID for tool responses")


class ChatCompletionRequest(BaseModel):
    """Request for chat completion."""

    messages: list[ChatMessage] = Field(..., description="List of messages in the conversation")
    model: str | None = Field(None, description="Model to use (e.g., gpt-4o, claude-3-5-sonnet)")
    provider: str | None = Field(None, description="Provider to use (e.g., openai, anthropic)")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int | None = Field(None, ge=1, le=128000, description="Maximum tokens to generate")
    top_p: float | None = Field(None, ge=0.0, le=1.0, description="Top-p sampling")
    stream: bool = Field(False, description="Enable streaming response")
    tools: list[dict[str, Any]] | None = Field(None, description="Tools/functions for the model")
    use_cache: bool = Field(True, description="Use semantic cache for responses")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ChatCompletionResponse(BaseModel):
    """Response from chat completion."""

    id: UUID = Field(..., description="Request ID")
    model: str = Field(..., description="Model used")
    provider: str = Field(..., description="Provider used")
    content: str = Field(..., description="Generated content")
    finish_reason: str | None = Field(None, description="Reason for completion")
    tool_calls: list[dict[str, Any]] | None = Field(None, description="Tool calls if any")
    usage: UsageStats = Field(..., description="Token usage statistics")
    latency_ms: float = Field(..., description="Request latency in milliseconds")
    from_cache: bool = Field(False, description="Whether response was from cache")


class ModelsResponse(BaseModel):
    """Available models response."""

    providers: dict[str, list[str]] = Field(..., description="Models by provider")
    default_model: str | None = Field(None, description="Default model")
    default_provider: str | None = Field(None, description="Default provider")


class HealthResponse(BaseModel):
    """Health check response."""

    healthy: bool = Field(..., description="Overall health status")
    providers: dict[str, bool] = Field(..., description="Provider health status")


class UsageResponse(BaseModel):
    """Usage statistics response."""

    user_id: str | None = Field(None, description="User ID")
    total_requests: int = Field(0, description="Total requests")
    total_tokens: int = Field(0, description="Total tokens used")
    total_cost_usd: float = Field(0.0, description="Total cost in USD")
    rate_limit: RateLimitInfo = Field(..., description="Current rate limit status")


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/chat/completions",
    response_model=ChatCompletionResponse,
    summary="Create chat completion",
    description="Generate a response from the LLM for the given messages.",
)
async def create_chat_completion(
    request: ChatCompletionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    gateway: Annotated[LLMGateway, Depends(get_gateway)],
) -> ChatCompletionResponse | StreamingResponse:
    """Create a chat completion."""
    try:
        # Convert messages
        messages = [
            Message(
                role=MessageRole(msg.role),
                content=msg.content,
                name=msg.name,
                tool_call_id=msg.tool_call_id,
            )
            for msg in request.messages
        ]

        # Build LLM request
        llm_request = LLMRequest(
            user_id=str(current_user.id),
            tenant_id=str(current_user.organization_id) if current_user.organization_id else None,
            messages=messages,
            model=request.model,
            provider=request.provider,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
            tools=request.tools,
            stream=request.stream,
            use_cache=request.use_cache,
            metadata=request.metadata,
        )

        # Handle streaming
        if request.stream:
            return StreamingResponse(
                _stream_response(gateway, llm_request),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )

        # Non-streaming completion
        response = await gateway.complete(llm_request)

        return ChatCompletionResponse(
            id=response.request_id,
            model=response.model,
            provider=response.provider,
            content=response.content,
            finish_reason=response.finish_reason,
            tool_calls=response.tool_calls,
            usage=response.usage,
            latency_ms=response.latency_ms,
            from_cache=response.from_cache,
        )

    except Exception as e:
        logger.error("Chat completion failed", error=str(e), user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Chat completion failed. Please try again later.",
        )


async def _stream_response(
    gateway: LLMGateway,
    request: LLMRequest,
) -> AsyncGenerator[str, None]:
    """Generate SSE stream for chat completion."""
    try:
        async for chunk in gateway.stream(request):
            # Format as SSE
            data = chunk.model_dump_json()
            yield f"data: {data}\n\n"

            if chunk.is_final:
                yield "data: [DONE]\n\n"

    except Exception as e:
        logger.error("Streaming failed", error=str(e))
        yield 'data: {"error": "Streaming failed. Please try again."}\n\n'


@router.get(
    "/models",
    response_model=ModelsResponse,
    summary="List available models",
    description="Get list of available models grouped by provider.",
)
async def list_models(
    gateway: Annotated[LLMGateway, Depends(get_gateway)],
    current_user: Annotated[User | None, Depends(get_current_user_optional)] = None,
) -> ModelsResponse:
    """List available models."""
    models = gateway.list_models()

    # Get default provider from the default model's config
    default_provider = None
    if gateway.config.default_model:
        default_provider = gateway.router.get_provider_for_model(gateway.config.default_model)

    return ModelsResponse(
        providers=models,
        default_model=gateway.config.default_model,
        default_provider=default_provider,
    )


@router.get(
    "/status",
    response_model=GatewayStatus,
    summary="Get gateway status",
    description="Get the current status of the LLM gateway including provider health.",
)
async def get_status(
    gateway: Annotated[LLMGateway, Depends(get_gateway)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> GatewayStatus:
    """Get gateway status."""
    return await gateway.get_status()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Check health of all LLM providers.",
)
async def health_check(
    gateway: Annotated[LLMGateway, Depends(get_gateway)],
) -> HealthResponse:
    """Health check endpoint."""
    provider_health = await gateway.health_check()
    overall_healthy = any(provider_health.values())

    return HealthResponse(
        healthy=overall_healthy,
        providers=provider_health,
    )


@router.get(
    "/providers",
    response_model=list[ProviderStatus],
    summary="List providers",
    description="Get detailed status of all configured providers.",
)
async def list_providers(
    gateway: Annotated[LLMGateway, Depends(get_gateway)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[ProviderStatus]:
    """List all providers with their status."""
    status = await gateway.get_status()
    return status.providers


@router.get(
    "/usage",
    response_model=UsageResponse,
    summary="Get usage statistics",
    description="Get usage statistics for the current user.",
)
async def get_usage(
    gateway: Annotated[LLMGateway, Depends(get_gateway)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UsageResponse:
    """Get usage statistics for current user."""
    user_id = str(current_user.id)

    # Get rate limit info
    rate_info = gateway._check_rate_limit(user_id)

    # Get usage from cost tracker
    user_stats = gateway.cost_tracker.get_user_stats(user_id)

    return UsageResponse(
        user_id=user_id,
        total_requests=user_stats.get("total_requests", 0),
        total_tokens=user_stats.get("total_tokens", 0),
        total_cost_usd=user_stats.get("total_cost_usd", 0.0),
        rate_limit=rate_info,
    )


@router.post(
    "/cache/clear",
    summary="Clear cache",
    description="Clear the semantic cache for the current user.",
)
async def clear_cache(
    gateway: Annotated[LLMGateway, Depends(get_gateway)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    """Clear cache for current user."""
    try:
        await gateway.clear_cache(user_id=str(current_user.id))
    except AttributeError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Semantic cache is not configured",
        )
    return {"status": "ok", "message": "Cache cleared"}


@router.post(
    "/test",
    response_model=ChatCompletionResponse,
    summary="Test LLM connection",
    description="Send a test message to verify LLM connectivity.",
)
async def test_connection(
    gateway: Annotated[LLMGateway, Depends(get_gateway)],
    current_user: Annotated[User, Depends(get_current_user)],
    provider: str | None = Query(None, description="Provider to test"),
    model: str | None = Query(None, description="Model to test"),
) -> ChatCompletionResponse:
    """Test LLM connection with a simple message."""
    try:
        request = LLMRequest(
            user_id=str(current_user.id),
            messages=[
                Message(
                    role=MessageRole.USER,
                    content="Hello! Please respond with 'Connection successful.' to confirm the connection.",
                )
            ],
            model=model,
            provider=provider,
            max_tokens=50,
            temperature=0.0,
        )

        response = await gateway.complete(request)

        return ChatCompletionResponse(
            id=response.request_id,
            model=response.model,
            provider=response.provider,
            content=response.content,
            finish_reason=response.finish_reason,
            tool_calls=response.tool_calls,
            usage=response.usage,
            latency_ms=response.latency_ms,
            from_cache=response.from_cache,
        )

    except Exception as e:
        logger.error("Test connection failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Connection test failed. Please verify provider configuration and try again.",
        )


# =============================================================================
# Circuit Breaker Endpoints
# =============================================================================


class CircuitBreakerStatus(BaseModel):
    """Circuit breaker status for a provider."""

    provider: str
    state: str = Field(..., description="Circuit state: closed, open, or half_open")
    metrics: dict[str, Any] = Field(..., description="Circuit breaker metrics")
    config: dict[str, Any] = Field(..., description="Circuit breaker configuration")
    redis_available: bool = Field(..., description="Whether Redis persistence is available")
    time_until_half_open_seconds: float | None = Field(
        None, description="Time until circuit enters half-open state (only for open circuits)"
    )


class AllCircuitBreakersResponse(BaseModel):
    """Response containing all circuit breaker statuses."""

    circuit_breakers: dict[str, CircuitBreakerStatus]


@router.get(
    "/circuit-breakers",
    response_model=AllCircuitBreakersResponse,
    summary="Get all circuit breaker statuses",
    description="Get the current status of all provider circuit breakers.",
)
async def get_circuit_breakers(
    gateway: Annotated[LLMGateway, Depends(get_gateway)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AllCircuitBreakersResponse:
    """Get status of all circuit breakers."""
    try:
        statuses = await gateway.router.get_all_circuit_statuses()
        return AllCircuitBreakersResponse(
            circuit_breakers={
                name: CircuitBreakerStatus(
                    provider=status["provider"],
                    state=status["state"],
                    metrics=status["metrics"],
                    config=status["config"],
                    redis_available=status["redis_available"],
                    time_until_half_open_seconds=status.get("time_until_half_open_seconds"),
                )
                for name, status in statuses.items()
            }
        )
    except Exception as e:
        logger.error("Failed to get circuit breaker statuses", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve circuit breaker statuses. Please try again later.",
        )


@router.get(
    "/circuit-breakers/{provider}",
    response_model=CircuitBreakerStatus,
    summary="Get circuit breaker status for a provider",
    description="Get the current status of a specific provider's circuit breaker.",
)
async def get_circuit_breaker(
    provider: str,
    gateway: Annotated[LLMGateway, Depends(get_gateway)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> CircuitBreakerStatus:
    """Get circuit breaker status for a specific provider."""
    try:
        status_data = await gateway.router.get_circuit_status(provider)
        return CircuitBreakerStatus(
            provider=status_data["provider"],
            state=status_data["state"],
            metrics=status_data["metrics"],
            config=status_data["config"],
            redis_available=status_data["redis_available"],
            time_until_half_open_seconds=status_data.get("time_until_half_open_seconds"),
        )
    except Exception as e:
        logger.error("Failed to get circuit breaker status", provider=provider, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve circuit breaker status. Please try again later.",
        )


@router.post(
    "/circuit-breakers/{provider}/reset",
    summary="Reset circuit breaker for a provider",
    description="Manually reset a provider's circuit breaker to closed state.",
)
async def reset_circuit_breaker(
    provider: str,
    gateway: Annotated[LLMGateway, Depends(get_gateway)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    """Manually reset a circuit breaker."""
    try:
        await gateway.router.reset_circuit(provider)
        return {"status": "success", "message": f"Circuit breaker for {provider} has been reset"}
    except Exception as e:
        logger.error("Failed to reset circuit breaker", provider=provider, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset circuit breaker. Please try again later.",
        )
