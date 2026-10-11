"""Provider router for intelligent LLM routing."""

from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any

import structlog

from app.services.llm_gateway.config import (
    AllowlistConfig,
    GatewayConfig,
    ModelConfig,
    ProviderPriority,
    RouteStrategy,
)
from app.services.llm_gateway.models import ProviderHealth, ProviderStatus
from app.services.llm_gateway.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerRegistry,
    CircuitState,
)
from app.services.llm_gateway.exceptions import LLMProviderError, classify_error

logger = structlog.get_logger()


class ProviderMetrics:
    """Track provider performance metrics."""

    def __init__(self):
        self.requests: deque[datetime] = deque(maxlen=500)
        self.errors: deque[datetime] = deque(maxlen=500)
        self.latencies: deque[float] = deque(maxlen=100)
        self.last_error: str | None = None
        self.last_check: datetime | None = None
        self.health: ProviderHealth = ProviderHealth.UNKNOWN

    def record_request(self, latency_ms: float, success: bool, error: str | None = None):
        """Record a request result."""
        now = datetime.utcnow()
        self.requests.append(now)
        self.latencies.append(latency_ms)

        if not success:
            self.errors.append(now)
            self.last_error = error

    def get_stats(self) -> dict[str, Any]:
        """Get current statistics."""
        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)

        requests_last_minute = sum(1 for r in self.requests if r > minute_ago)
        errors_last_minute = sum(1 for e in self.errors if e > minute_ago)
        avg_latency = sum(self.latencies) / len(self.latencies) if self.latencies else 0

        return {
            "requests_last_minute": requests_last_minute,
            "errors_last_minute": errors_last_minute,
            "avg_latency_ms": avg_latency,
            "error_rate": errors_last_minute / max(requests_last_minute, 1),
        }

    def update_health(self) -> ProviderHealth:
        """Update and return health status based on metrics."""
        stats = self.get_stats()
        self.last_check = datetime.utcnow()

        error_rate = stats["error_rate"]
        if error_rate == 0 and stats["requests_last_minute"] > 0:
            self.health = ProviderHealth.HEALTHY
        elif error_rate < 0.1:
            self.health = ProviderHealth.HEALTHY
        elif error_rate < 0.5:
            self.health = ProviderHealth.DEGRADED
        else:
            self.health = ProviderHealth.UNHEALTHY

        return self.health


class ProviderRouter:
    """Routes requests to appropriate LLM providers."""

    def __init__(self, config: GatewayConfig, redis_cache: Any = None):
        self.config = config
        self.metrics: dict[str, ProviderMetrics] = defaultdict(ProviderMetrics)
        self._round_robin_index = 0
        self._model_to_provider: dict[str, str] = {}
        self._provider_models: dict[str, list[str]] = {}
        self._model_configs: dict[str, ModelConfig] = {}

        # Circuit breaker registry
        self._circuit_breakers = CircuitBreakerRegistry(redis=redis_cache)

        # Build model -> provider mapping
        self._build_model_mapping()

    def _build_model_mapping(self):
        """Build mapping of models to providers."""
        # From model configs
        for model in self.config.models:
            self._model_to_provider[model.name] = model.provider
            self._model_configs[model.name] = model

        # From provider configs
        for provider in self.config.providers:
            self._provider_models[provider.name] = provider.models
            for model in provider.models:
                if model not in self._model_to_provider:
                    self._model_to_provider[model] = provider.name

    def get_provider_for_model(self, model: str) -> str | None:
        """Get the provider for a specific model."""
        return self._model_to_provider.get(model)

    def get_model_config(self, model: str) -> ModelConfig | None:
        """Get configuration for a model."""
        return self._model_configs.get(model)

    def get_available_providers(self) -> list[str]:
        """Get list of available (enabled) providers."""
        return [p.name for p in self.config.providers if p.enabled]

    def select_provider(
        self,
        model: str | None = None,
        preferred_provider: str | None = None,
        exclude_providers: list[str] | None = None,
    ) -> tuple[str, str]:
        """
        Select a provider and model for a request.

        Enforces allowlist / blocklist constraints defined in ``GatewayConfig.allowlist``.

        Returns:
            Tuple of (provider_name, model_name)

        Raises:
            ValueError: If no providers are available or the requested
                model / provider is blocked by the allowlist.
        """
        exclude = set(exclude_providers or [])
        allowlist = self.config.allowlist

        # ----- Allowlist pre-checks -----
        if model and not allowlist.is_model_allowed(model):
            raise ValueError(
                f"Model '{model}' is not permitted by the allowlist configuration"
            )

        if preferred_provider and not allowlist.is_provider_allowed(preferred_provider):
            logger.warning(
                "provider_blocked_by_allowlist",
                provider=preferred_provider,
            )
            preferred_provider = None  # Fall through to routing

        # If specific model requested, find its provider
        if model:
            provider = self.get_provider_for_model(model)
            if provider and provider not in exclude and allowlist.is_provider_allowed(provider):
                return provider, model

        # If specific provider requested
        if preferred_provider and preferred_provider not in exclude:
            provider_config = self._get_provider_config(preferred_provider)
            if provider_config and provider_config.enabled:
                model_to_use = model or (
                    provider_config.models[0] if provider_config.models else self.config.default_model
                )
                if not allowlist.is_model_allowed(model_to_use):
                    # Pick first allowed model from this provider
                    model_to_use = next(
                        (m for m in provider_config.models if allowlist.is_model_allowed(m)),
                        None,
                    )
                    if model_to_use is None:
                        raise ValueError(
                            f"No allowed models available from provider '{preferred_provider}'"
                        )
                return preferred_provider, model_to_use

        # Use routing strategy — filter by allowlist
        available = [
            p
            for p in self.config.providers
            if p.enabled and p.name not in exclude and allowlist.is_provider_allowed(p.name)
        ]

        if not available:
            raise ValueError("No available providers (allowlist may be too restrictive)")

        if self.config.route_strategy == RouteStrategy.PRIORITY:
            provider = self._select_by_priority(available)
        elif self.config.route_strategy == RouteStrategy.ROUND_ROBIN:
            provider = self._select_round_robin(available)
        elif self.config.route_strategy == RouteStrategy.LEAST_LATENCY:
            provider = self._select_by_latency(available)
        elif self.config.route_strategy == RouteStrategy.COST_OPTIMIZED:
            provider = self._select_by_cost(available, model)
        else:
            provider = self._select_by_priority(available)

        # Determine model — respect allowlist
        model_to_use = model or (
            provider.models[0] if provider.models else self.config.default_model
        )
        if not allowlist.is_model_allowed(model_to_use):
            model_to_use = next(
                (m for m in provider.models if allowlist.is_model_allowed(m)),
                None,
            )
            if model_to_use is None:
                raise ValueError(
                    f"No allowed models available from provider '{provider.name}'"
                )

        return provider.name, model_to_use

    def _get_provider_config(self, name: str) -> ProviderPriority | None:
        """Get provider configuration by name."""
        for p in self.config.providers:
            if p.name == name:
                return p
        return None

    def _select_by_priority(self, providers: list[ProviderPriority]) -> ProviderPriority:
        """Select provider by priority (lowest first)."""
        # Filter out unhealthy providers
        healthy = [
            p for p in providers
            if self.metrics[p.name].health != ProviderHealth.UNHEALTHY
        ]

        if not healthy:
            healthy = providers  # Fallback to all if none healthy

        return min(healthy, key=lambda p: p.priority)

    def _select_round_robin(self, providers: list[ProviderPriority]) -> ProviderPriority:
        """Select provider using round-robin."""
        # Filter out unhealthy
        healthy = [
            p for p in providers
            if self.metrics[p.name].health != ProviderHealth.UNHEALTHY
        ]

        if not healthy:
            healthy = providers

        self._round_robin_index = (self._round_robin_index + 1) % len(healthy)
        return healthy[self._round_robin_index]

    def _select_by_latency(self, providers: list[ProviderPriority]) -> ProviderPriority:
        """Select provider with lowest latency."""
        # Filter out unhealthy
        healthy = [
            p for p in providers
            if self.metrics[p.name].health != ProviderHealth.UNHEALTHY
        ]

        if not healthy:
            healthy = providers

        def get_latency(p: ProviderPriority) -> float:
            stats = self.metrics[p.name].get_stats()
            return stats["avg_latency_ms"] or float("inf")

        return min(healthy, key=get_latency)

    def _select_by_cost(
        self, providers: list[ProviderPriority], model: str | None
    ) -> ProviderPriority:
        """Select provider with lowest cost."""
        # Ollama (local) is always cheapest
        for p in providers:
            if p.name == "ollama":
                return p

        # Otherwise, use model pricing
        def get_cost(p: ProviderPriority) -> float:
            if not model:
                return float("inf")

            model_config = self.get_model_config(model)
            if model_config:
                return model_config.input_cost_per_1k + model_config.output_cost_per_1k
            return float("inf")

        return min(providers, key=get_cost)

    def record_request(
        self,
        provider: str,
        latency_ms: float,
        success: bool,
        error: str | None = None,
    ):
        """Record a request result for metrics."""
        self.metrics[provider].record_request(latency_ms, success, error)
        self.metrics[provider].update_health()

    def get_provider_status(self, provider: str) -> ProviderStatus:
        """Get status for a specific provider."""
        metrics = self.metrics[provider]
        stats = metrics.get_stats()
        provider_config = self._get_provider_config(provider)

        return ProviderStatus(
            name=provider,
            enabled=provider_config.enabled if provider_config else False,
            health=metrics.health,
            available_models=self._provider_models.get(provider, []),
            requests_last_minute=stats["requests_last_minute"],
            errors_last_minute=stats["errors_last_minute"],
            avg_latency_ms=stats["avg_latency_ms"],
            last_check=metrics.last_check,
            last_error=metrics.last_error,
        )

    def get_all_provider_status(self) -> list[ProviderStatus]:
        """Get status for all providers."""
        return [
            self.get_provider_status(p.name) for p in self.config.providers
        ]

    def should_failover(self, provider: str, error: Exception) -> bool:
        """Determine if we should failover to another provider."""
        if not self.config.enable_failover:
            return False

        # Always failover on connection errors
        error_str = str(error).lower()
        if any(
            term in error_str
            for term in ["connection", "timeout", "rate limit", "capacity", "overloaded"]
        ):
            return True

        # Check provider health
        metrics = self.metrics[provider]
        return metrics.health == ProviderHealth.UNHEALTHY

    def get_failover_provider(
        self,
        original_provider: str,
        model: str | None = None,
        attempted: list[str] | None = None,
    ) -> tuple[str, str] | None:
        """Get a failover provider."""
        exclude = set(attempted or [])
        exclude.add(original_provider)

        try:
            return self.select_provider(model=model, exclude_providers=list(exclude))
        except ValueError:
            return None

    # =========================================================================
    # CIRCUIT BREAKER INTEGRATION
    # =========================================================================

    async def get_circuit_breaker(self, provider: str) -> CircuitBreaker:
        """Get circuit breaker for a provider."""
        return await self._circuit_breakers.get(provider)

    async def check_circuit(self, provider: str) -> tuple[bool, str]:
        """
        Check if a provider's circuit allows requests.

        Returns:
            Tuple of (allowed, reason)
        """
        cb = await self.get_circuit_breaker(provider)
        return await cb.can_execute()

    async def record_circuit_success(self, provider: str) -> None:
        """Record a successful request in the circuit breaker."""
        cb = await self.get_circuit_breaker(provider)
        await cb.record_success()

    async def record_circuit_failure(
        self,
        provider: str,
        error: Exception,
    ) -> None:
        """Record a failed request in the circuit breaker."""
        # Classify the error
        if isinstance(error, LLMProviderError):
            classified_error = error
        else:
            classified_error = classify_error(provider, error)

        cb = await self.get_circuit_breaker(provider)
        await cb.record_failure(classified_error)

    async def get_circuit_status(self, provider: str) -> dict[str, Any]:
        """Get circuit breaker status for a provider."""
        cb = await self.get_circuit_breaker(provider)
        return await cb.get_status()

    async def get_all_circuit_statuses(self) -> dict[str, dict[str, Any]]:
        """Get circuit breaker status for all providers."""
        return await self._circuit_breakers.get_all_statuses()

    async def reset_circuit(self, provider: str) -> None:
        """Manually reset a provider's circuit breaker."""
        cb = await self.get_circuit_breaker(provider)
        await cb.reset()

    async def select_provider_with_circuit(
        self,
        model: str | None = None,
        preferred_provider: str | None = None,
        exclude_providers: list[str] | None = None,
    ) -> tuple[str, str]:
        """
        Select a provider, respecting circuit breaker states.

        Like select_provider, but also checks circuit breakers.
        """
        exclude = set(exclude_providers or [])

        # Add providers with open circuits to exclusion
        for provider_config in self.config.providers:
            if provider_config.enabled:
                allowed, reason = await self.check_circuit(provider_config.name)
                if not allowed:
                    exclude.add(provider_config.name)
                    logger.debug(
                        "provider_excluded_circuit_open",
                        provider=provider_config.name,
                        reason=reason,
                    )

        return self.select_provider(
            model=model,
            preferred_provider=preferred_provider,
            exclude_providers=list(exclude),
        )

    def should_failover_with_circuit(
        self,
        provider: str,
        error: Exception,
    ) -> bool:
        """
        Determine if we should failover, considering both error type and circuit state.

        Uses the new exception classification for smarter decisions.
        """
        if not self.config.enable_failover:
            return False

        # Use existing classification if error is already an LLMProviderError
        if isinstance(error, LLMProviderError):
            classified = error
        else:
            classified = classify_error(provider, error)

        # If not retryable, no point in failover
        if not classified.retryable:
            logger.debug(
                "no_failover_non_retryable",
                provider=provider,
                error_type=type(classified).__name__,
            )
            return False

        # Check provider health
        metrics = self.metrics[provider]
        if metrics.health == ProviderHealth.UNHEALTHY:
            return True

        # Retryable errors should trigger failover
        return True
