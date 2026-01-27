"""LLM Gateway configuration."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.core.config import settings


class RouteStrategy(str, Enum):
    """Routing strategy for provider selection."""

    PRIORITY = "priority"  # Use provider priority order
    ROUND_ROBIN = "round_robin"  # Distribute load evenly
    LEAST_LATENCY = "least_latency"  # Choose fastest provider
    COST_OPTIMIZED = "cost_optimized"  # Choose cheapest provider


class ProviderPriority(BaseModel):
    """Provider priority configuration."""

    name: str
    priority: int = 1  # Lower = higher priority
    enabled: bool = True
    weight: float = 1.0  # For weighted routing
    max_requests_per_minute: int = 60
    models: list[str] = Field(default_factory=list)


class ModelConfig(BaseModel):
    """Model-specific configuration."""

    name: str
    provider: str
    context_window: int = 4096
    max_output_tokens: int = 4096
    input_cost_per_1k: float = 0.0  # Cost per 1000 input tokens
    output_cost_per_1k: float = 0.0  # Cost per 1000 output tokens
    supports_vision: bool = False
    supports_tools: bool = True
    supports_streaming: bool = True


class CostConfig(BaseModel):
    """Cost tracking configuration."""

    enabled: bool = True
    budget_per_user_daily: float = 10.0  # USD
    budget_per_user_monthly: float = 100.0
    budget_total_daily: float = 1000.0
    alert_threshold: float = 0.8  # Alert at 80% of budget


class CacheConfig(BaseModel):
    """Cache configuration."""

    enabled: bool = True
    similarity_threshold: float = 0.92  # Semantic similarity threshold
    ttl_seconds: int = 86400  # 24 hours
    max_entries: int = 10000


class GatewayConfig(BaseModel):
    """Complete gateway configuration."""

    # Routing
    route_strategy: RouteStrategy = RouteStrategy.PRIORITY
    enable_failover: bool = True
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    request_timeout_seconds: int = 120

    # Providers
    providers: list[ProviderPriority] = Field(default_factory=list)

    # Models
    models: list[ModelConfig] = Field(default_factory=list)
    default_model: str = Field(default_factory=lambda: settings.OPENAI_DEFAULT_MODEL)

    # Cost tracking
    cost: CostConfig = Field(default_factory=CostConfig)

    # Caching
    cache: CacheConfig = Field(default_factory=CacheConfig)

    # Rate limiting
    global_rate_limit_per_minute: int = 1000
    user_rate_limit_per_minute: int = 60


# Default provider configurations - Gemini is the default/priority provider
DEFAULT_PROVIDERS = [
    ProviderPriority(
        name="google",
        priority=1,
        models=["gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash", "gemini-pro"],
    ),
    ProviderPriority(
        name="anthropic",
        priority=2,
        models=["claude-3-opus", "claude-3-sonnet", "claude-3-haiku", "claude-3-5-sonnet"],
    ),
    ProviderPriority(
        name="openai",
        priority=3,
        models=["gpt-4-turbo", "gpt-4", "gpt-3.5-turbo", "gpt-4o", "gpt-4o-mini"],
    ),
    ProviderPriority(
        name="ollama",
        priority=4,
        models=["llama3", "llama3:70b", "mistral", "mixtral", "codellama", "phi3"],
    ),
    ProviderPriority(
        name="groq",
        priority=5,
        models=["llama-3.3-70b-versatile", "mixtral-8x7b-32768"],
    ),
]

# Default model configurations with pricing (USD per 1000 tokens)
DEFAULT_MODELS = [
    # OpenAI
    ModelConfig(
        name="gpt-4-turbo",
        provider="openai",
        context_window=128000,
        max_output_tokens=4096,
        input_cost_per_1k=0.01,
        output_cost_per_1k=0.03,
        supports_vision=True,
    ),
    ModelConfig(
        name="gpt-4o",
        provider="openai",
        context_window=128000,
        max_output_tokens=4096,
        input_cost_per_1k=0.005,
        output_cost_per_1k=0.015,
        supports_vision=True,
    ),
    ModelConfig(
        name="gpt-4o-mini",
        provider="openai",
        context_window=128000,
        max_output_tokens=16384,
        input_cost_per_1k=0.00015,
        output_cost_per_1k=0.0006,
        supports_vision=True,
    ),
    ModelConfig(
        name="gpt-3.5-turbo",
        provider="openai",
        context_window=16385,
        max_output_tokens=4096,
        input_cost_per_1k=0.0005,
        output_cost_per_1k=0.0015,
    ),
    # Anthropic
    ModelConfig(
        name="claude-3-opus",
        provider="anthropic",
        context_window=200000,
        max_output_tokens=4096,
        input_cost_per_1k=0.015,
        output_cost_per_1k=0.075,
        supports_vision=True,
    ),
    ModelConfig(
        name="claude-3-5-sonnet",
        provider="anthropic",
        context_window=200000,
        max_output_tokens=8192,
        input_cost_per_1k=0.003,
        output_cost_per_1k=0.015,
        supports_vision=True,
    ),
    ModelConfig(
        name="claude-3-sonnet",
        provider="anthropic",
        context_window=200000,
        max_output_tokens=4096,
        input_cost_per_1k=0.003,
        output_cost_per_1k=0.015,
        supports_vision=True,
    ),
    ModelConfig(
        name="claude-3-haiku",
        provider="anthropic",
        context_window=200000,
        max_output_tokens=4096,
        input_cost_per_1k=0.00025,
        output_cost_per_1k=0.00125,
        supports_vision=True,
    ),
    # Google - Gemini models (default provider)
    ModelConfig(
        name="gemini-2.0-flash-exp",
        provider="google",
        context_window=1000000,
        max_output_tokens=8192,
        input_cost_per_1k=0.0,  # Free during experimental phase
        output_cost_per_1k=0.0,
        supports_vision=True,
    ),
    ModelConfig(
        name="gemini-1.5-pro",
        provider="google",
        context_window=1000000,
        max_output_tokens=8192,
        input_cost_per_1k=0.00125,
        output_cost_per_1k=0.005,
        supports_vision=True,
    ),
    ModelConfig(
        name="gemini-1.5-flash",
        provider="google",
        context_window=1000000,
        max_output_tokens=8192,
        input_cost_per_1k=0.000075,
        output_cost_per_1k=0.0003,
        supports_vision=True,
    ),
    ModelConfig(
        name="gemini-pro",
        provider="google",
        context_window=32000,
        max_output_tokens=8192,
        input_cost_per_1k=0.00025,
        output_cost_per_1k=0.0005,
    ),
    # Ollama (local, no cost)
    ModelConfig(
        name="llama3",
        provider="ollama",
        context_window=8192,
        max_output_tokens=4096,
        input_cost_per_1k=0.0,
        output_cost_per_1k=0.0,
    ),
    ModelConfig(
        name="llama3:70b",
        provider="ollama",
        context_window=8192,
        max_output_tokens=4096,
        input_cost_per_1k=0.0,
        output_cost_per_1k=0.0,
    ),
    ModelConfig(
        name="mistral",
        provider="ollama",
        context_window=32768,
        max_output_tokens=4096,
        input_cost_per_1k=0.0,
        output_cost_per_1k=0.0,
    ),
    ModelConfig(
        name="mixtral",
        provider="ollama",
        context_window=32768,
        max_output_tokens=4096,
        input_cost_per_1k=0.0,
        output_cost_per_1k=0.0,
    ),
    ModelConfig(
        name="codellama",
        provider="ollama",
        context_window=16384,
        max_output_tokens=4096,
        input_cost_per_1k=0.0,
        output_cost_per_1k=0.0,
    ),
]


def get_gateway_config() -> GatewayConfig:
    """Get gateway configuration from settings.

    Respects DEFAULT_AI_PROVIDER from environment if set,
    otherwise uses priority order: Anthropic > Google > OpenAI > Ollama.
    """
    # Get configured default provider from environment
    default_provider = getattr(settings, "DEFAULT_AI_PROVIDER", None)

    # Provider configurations with their default models
    provider_configs = {
        "anthropic": {
            "api_key_attr": "ANTHROPIC_API_KEY",
            "models": [
                "claude-sonnet-4-20250514",
                "claude-3-5-sonnet-20241022",
                "claude-3-opus-20240229",
                "claude-3-haiku-20240307",
            ],
            "default_model_attr": "ANTHROPIC_DEFAULT_MODEL",
            "fallback_model": "claude-sonnet-4-20250514",
        },
        "google": {
            "api_key_attr": "GOOGLE_API_KEY",
            "models": ["gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash", "gemini-pro"],
            "default_model_attr": "GOOGLE_DEFAULT_MODEL",
            "fallback_model": "gemini-2.0-flash-exp",
        },
        "openai": {
            "api_key_attr": "OPENAI_API_KEY",
            "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
            "default_model_attr": "OPENAI_DEFAULT_MODEL",
            "fallback_model": "gpt-4o",
        },
        "groq": {
            "api_key_attr": "GROQ_API_KEY",
            "models": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"],
            "default_model_attr": "GROQ_DEFAULT_MODEL",
            "fallback_model": "llama-3.3-70b-versatile",
        },
        "ollama": {
            "api_key_attr": None,  # No API key needed
            "models": ["llama3", "llama3.2", "mistral", "codellama", "mixtral"],
            "default_model_attr": "OLLAMA_DEFAULT_MODEL",
            "fallback_model": "llama3.2",
        },
    }

    # Default priority order (lower = higher priority)
    # If no default provider is set, use this order
    default_priority_order = ["anthropic", "google", "openai", "groq", "ollama"]

    # Build available providers list
    available_providers = []
    priority = 1

    # If a default provider is specified, put it first
    if default_provider and default_provider in provider_configs:
        order = [default_provider] + [p for p in default_priority_order if p != default_provider]
    else:
        order = default_priority_order

    for provider_name in order:
        config = provider_configs[provider_name]
        api_key_attr = config["api_key_attr"]

        # Check if provider is available (has API key or is ollama)
        if provider_name == "ollama":
            ollama_url = getattr(settings, "OLLAMA_BASE_URL", None)
            if ollama_url:
                available_providers.append(
                    ProviderPriority(
                        name="ollama",
                        priority=priority,
                        enabled=True,
                        models=config["models"],
                    )
                )
                priority += 1
        elif api_key_attr:
            api_key = getattr(settings, api_key_attr, None)
            # Skip placeholder API keys
            if api_key and not api_key.startswith("sk-your"):
                available_providers.append(
                    ProviderPriority(
                        name=provider_name,
                        priority=priority,
                        enabled=True,
                        models=config["models"],
                    )
                )
                priority += 1

    # Determine default model based on default provider or first available
    default_model = settings.OLLAMA_DEFAULT_MODEL  # Ultimate fallback if nothing else configured

    if default_provider and default_provider in provider_configs:
        config = provider_configs[default_provider]
        # Check if the default provider is actually available
        provider_available = any(p.name == default_provider for p in available_providers)
        if provider_available:
            # Use configured default model or fallback
            default_model = getattr(
                settings,
                config["default_model_attr"],
                config["fallback_model"]
            )
    elif available_providers:
        # Use first available provider's default model
        first_provider = available_providers[0].name
        config = provider_configs[first_provider]
        default_model = getattr(
            settings,
            config["default_model_attr"],
            config["fallback_model"]
        )

    return GatewayConfig(
        providers=available_providers if available_providers else DEFAULT_PROVIDERS,
        models=DEFAULT_MODELS,
        default_model=default_model,
        enable_failover=True,
        max_retries=3,
    )
