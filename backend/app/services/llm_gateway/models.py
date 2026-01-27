"""LLM Gateway data models."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Message roles."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class Message(BaseModel):
    """A chat message."""

    role: MessageRole
    content: str
    name: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None


class LLMRequest(BaseModel):
    """Request to the LLM gateway."""

    # Request identification
    request_id: UUID = Field(default_factory=uuid4)
    user_id: str | None = None
    tenant_id: str | None = None
    conversation_id: str | None = None

    # Messages
    messages: list[Message]

    # Model configuration
    model: str | None = None  # If None, use default
    provider: str | None = None  # If None, use router
    temperature: float = 0.7
    max_tokens: int | None = None
    top_p: float | None = None
    stop: list[str] | None = None

    # Tool/Function calling
    tools: list[dict[str, Any]] | None = None
    tool_choice: str | dict[str, Any] | None = None

    # Options
    stream: bool = False
    use_cache: bool = True  # Use semantic cache
    bypass_guardrails: bool = False  # For internal use only

    # Hallucination detection
    check_hallucination: bool = False  # Enable hallucination checking
    rag_context: list[str] | None = None  # Context documents for RAG grounding

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class UsageStats(BaseModel):
    """Token usage statistics."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cached: bool = False
    cost_usd: float = 0.0


class LLMResponse(BaseModel):
    """Response from the LLM gateway."""

    # Request tracking
    request_id: UUID
    model: str
    provider: str

    # Response content
    content: str
    role: MessageRole = MessageRole.ASSISTANT
    finish_reason: str | None = None
    tool_calls: list[dict[str, Any]] | None = None

    # Usage
    usage: UsageStats = Field(default_factory=UsageStats)

    # Timing
    latency_ms: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Cache info
    from_cache: bool = False
    cache_key: str | None = None

    # Hallucination detection
    hallucination_check: "HallucinationCheckResult | None" = None


class LLMStreamChunk(BaseModel):
    """A streaming response chunk."""

    request_id: UUID
    content: str
    role: MessageRole = MessageRole.ASSISTANT
    finish_reason: str | None = None
    tool_calls: list[dict[str, Any]] | None = None

    # Only included in final chunk
    usage: UsageStats | None = None
    is_final: bool = False


class ProviderHealth(str, Enum):
    """Provider health status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ProviderStatus(BaseModel):
    """Status of a provider."""

    name: str
    enabled: bool = True
    health: ProviderHealth = ProviderHealth.UNKNOWN
    available_models: list[str] = Field(default_factory=list)
    requests_last_minute: int = 0
    errors_last_minute: int = 0
    avg_latency_ms: float = 0.0
    last_check: datetime | None = None
    last_error: str | None = None


class GatewayStatus(BaseModel):
    """Overall gateway status."""

    healthy: bool = True
    providers: list[ProviderStatus] = Field(default_factory=list)
    total_requests_today: int = 0
    total_cost_today_usd: float = 0.0
    cache_hit_rate: float = 0.0
    avg_latency_ms: float = 0.0


class RateLimitInfo(BaseModel):
    """Rate limit information."""

    user_id: str | None = None
    requests_remaining: int = 60
    requests_limit: int = 60
    reset_at: datetime | None = None
    is_limited: bool = False


class HallucinationCheckResult(BaseModel):
    """Result of hallucination detection on a response."""

    checked: bool = False
    is_hallucination: bool = False
    hallucination_score: float = 0.0  # 0.0 = no hallucination, 1.0 = full hallucination
    grounding_score: float = 1.0  # How well grounded in context
    relevance_score: float = 1.0  # Relevance to query
    factuality_score: float = 1.0  # Factual accuracy
    confidence: float = 0.0
    explanation: str = ""
    issues: list[str] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Check if the response passed hallucination detection."""
        return self.checked and not self.is_hallucination
