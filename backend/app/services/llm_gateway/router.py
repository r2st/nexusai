"""Provider router for intelligent LLM routing."""

import asyncio
import random
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

import structlog

from app.services.llm_gateway.config import (
    GatewayConfig,
    ModelConfig,
    ProviderPriority,
    RouteStrategy,
)
from app.services.llm_gateway.models import ProviderHealth, ProviderStatus

logger = structlog.get_logger()


class ProviderMetrics:
    """Track provider performance metrics."""

    def __init__(self):
        self.requests: list[datetime] = []
        self.errors: list[datetime] = []
        self.latencies: list[float] = []
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

        # Keep only last 5 minutes of data
        cutoff = now - timedelta(minutes=5)
        self.requests = [r for r in self.requests if r > cutoff]
        self.errors = [e for e in self.errors if e > cutoff]
        self.latencies = self.latencies[-100:]  # Keep last 100

    def get_stats(self) -> dict[str, Any]:
        """Get current statistics."""
        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)

        requests_last_minute = len([r for r in self.requests if r > minute_ago])
        errors_last_minute = len([e for e in self.errors if e > minute_ago])
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

    def __init__(self, config: GatewayConfig):
        self.config = config
        self.metrics: dict[str, ProviderMetrics] = defaultdict(ProviderMetrics)
        self._round_robin_index = 0
        self._model_to_provider: dict[str, str] = {}
        self._provider_models: dict[str, list[str]] = {}

        # Build model -> provider mapping
        self._build_model_mapping()

    def _build_model_mapping(self):
        """Build mapping of models to providers."""
        # From model configs
        for model in self.config.models:
            self._model_to_provider[model.name] = model.provider

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
        for m in self.config.models:
            if m.name == model:
                return m
        return None

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

        Returns:
            Tuple of (provider_name, model_name)
        """
        exclude = set(exclude_providers or [])

        # If specific model requested, find its provider
        if model:
            provider = self.get_provider_for_model(model)
            if provider and provider not in exclude:
                return provider, model

        # If specific provider requested
        if preferred_provider and preferred_provider not in exclude:
            provider_config = self._get_provider_config(preferred_provider)
            if provider_config and provider_config.enabled:
                model_to_use = model or (
                    provider_config.models[0] if provider_config.models else self.config.default_model
                )
                return preferred_provider, model_to_use

        # Use routing strategy
        available = [
            p for p in self.config.providers if p.enabled and p.name not in exclude
        ]

        if not available:
            raise ValueError("No available providers")

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

        # Determine model
        model_to_use = model or (
            provider.models[0] if provider.models else self.config.default_model
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
