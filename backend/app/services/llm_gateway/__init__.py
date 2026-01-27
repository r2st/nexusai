"""LLM Gateway Service.

Unified interface for LLM providers with intelligent routing,
failover, caching, and cost tracking.

Features:
- Multi-provider support (OpenAI, Anthropic, Google, Ollama)
- Automatic failover between providers
- Semantic caching for repeated queries
- Token-based rate limiting
- Cost tracking and budgeting
- Request queuing for high load

Usage:
    from app.services.llm_gateway import gateway, LLMRequest

    response = await gateway.complete(
        LLMRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="gpt-4",
            user_id="user_123",
        )
    )
"""

from app.services.llm_gateway.config import (
    GatewayConfig,
    ProviderPriority,
    ModelConfig,
    CostConfig,
    get_gateway_config,
)
from app.services.llm_gateway.models import (
    LLMRequest,
    LLMResponse,
    LLMStreamChunk,
    UsageStats,
    ProviderStatus,
)
from app.services.llm_gateway.router import (
    ProviderRouter,
    RouteStrategy,
)
from app.services.llm_gateway.cost_tracker import (
    CostTracker,
    CostEntry,
    CostReport,
)
from app.services.llm_gateway.service import (
    LLMGateway,
    get_gateway,
)
from app.services.llm_gateway.queue import (
    RequestQueue,
    RequestPriority,
    RateLimitConfig,
    get_request_queue,
)

__all__ = [
    # Config
    "GatewayConfig",
    "ProviderPriority",
    "ModelConfig",
    "CostConfig",
    "get_gateway_config",
    # Models
    "LLMRequest",
    "LLMResponse",
    "LLMStreamChunk",
    "UsageStats",
    "ProviderStatus",
    # Router
    "ProviderRouter",
    "RouteStrategy",
    # Cost Tracking
    "CostTracker",
    "CostEntry",
    "CostReport",
    # Service
    "LLMGateway",
    "get_gateway",
    # Queue
    "RequestQueue",
    "RequestPriority",
    "RateLimitConfig",
    "get_request_queue",
]
