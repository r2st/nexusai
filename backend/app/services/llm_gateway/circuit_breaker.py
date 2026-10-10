"""Circuit breaker implementation for LLM provider resilience.

Implements the circuit breaker pattern with state persistence to Redis.
Falls back to in-memory state if Redis is unavailable.
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import structlog

from app.core.cache import RedisCache, CacheConfig
from app.services.llm_gateway.exceptions import LLMProviderError

logger = structlog.get_logger()


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation - requests allowed
    OPEN = "open"  # Circuit tripped - requests rejected
    HALF_OPEN = "half_open"  # Testing recovery - limited requests


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    # Threshold for opening circuit
    failure_threshold: int = 5  # Number of failures before opening
    failure_rate_threshold: float = 0.5  # Error rate threshold (0-1)
    minimum_requests: int = 5  # Minimum requests before rate is considered

    # Recovery settings
    recovery_timeout_seconds: float = 30.0  # Time before half-open
    half_open_max_requests: int = 3  # Max requests in half-open state
    success_threshold: int = 2  # Successes needed to close from half-open

    # Monitoring window
    window_size_seconds: int = 60  # Rolling window for metrics

    # State persistence
    state_ttl_seconds: int = 300  # TTL for Redis state (5 minutes)


@dataclass
class CircuitMetrics:
    """Metrics tracked by the circuit breaker."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_failure_time: float | None = None
    last_success_time: float | None = None
    half_open_requests: int = 0
    state_changed_at: float = field(default_factory=time.time)

    @property
    def failure_rate(self) -> float:
        """Calculate failure rate."""
        if self.total_requests == 0:
            return 0.0
        return self.failed_requests / self.total_requests

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "consecutive_failures": self.consecutive_failures,
            "consecutive_successes": self.consecutive_successes,
            "last_failure_time": self.last_failure_time,
            "last_success_time": self.last_success_time,
            "half_open_requests": self.half_open_requests,
            "state_changed_at": self.state_changed_at,
            "failure_rate": self.failure_rate,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CircuitMetrics":
        """Create from dictionary."""
        return cls(
            total_requests=data.get("total_requests", 0),
            successful_requests=data.get("successful_requests", 0),
            failed_requests=data.get("failed_requests", 0),
            consecutive_failures=data.get("consecutive_failures", 0),
            consecutive_successes=data.get("consecutive_successes", 0),
            last_failure_time=data.get("last_failure_time"),
            last_success_time=data.get("last_success_time"),
            half_open_requests=data.get("half_open_requests", 0),
            state_changed_at=data.get("state_changed_at", time.time()),
        )


class CircuitBreaker:
    """
    Circuit breaker for LLM provider resilience.

    Implements three states:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Circuit tripped, requests fail fast
    - HALF_OPEN: Testing recovery, limited requests allowed

    State is persisted to Redis for cluster-wide consistency.
    Falls back to in-memory state if Redis is unavailable.
    """

    # Key prefixes for Redis
    KEY_PREFIX = f"{CacheConfig.PREFIX}circuit:"

    def __init__(
        self,
        provider: str,
        config: CircuitBreakerConfig | None = None,
        redis: RedisCache | None = None,
    ):
        """
        Initialize circuit breaker.

        Args:
            provider: Provider name (e.g., "openai", "anthropic")
            config: Circuit breaker configuration
            redis: Redis cache client (optional, falls back to in-memory)
        """
        self.provider = provider
        self.config = config or CircuitBreakerConfig()
        self._redis = redis
        self._redis_available = redis is not None

        # In-memory fallback state
        self._local_state = CircuitState.CLOSED
        self._local_metrics = CircuitMetrics()
        self._lock = asyncio.Lock()

    def _get_key(self, suffix: str) -> str:
        """Generate Redis key for this circuit breaker."""
        return f"{self.KEY_PREFIX}{self.provider}:{suffix}"

    async def _get_from_store(self, key: str, default: Any = None) -> Any:
        """Get value from Redis or return default."""
        if not self._redis_available or not self._redis:
            return default

        try:
            value = await self._redis.get(key)
            return value if value is not None else default
        except Exception as e:
            logger.warning(
                "circuit_breaker_redis_error",
                provider=self.provider,
                operation="get",
                key=key,
                error=str(e),
            )
            self._redis_available = False
            return default

    async def _set_in_store(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> bool:
        """Set value in Redis."""
        if not self._redis_available or not self._redis:
            return False

        try:
            ttl = ttl or self.config.state_ttl_seconds
            await self._redis.set(key, value, ttl=ttl)
            return True
        except Exception as e:
            logger.warning(
                "circuit_breaker_redis_error",
                provider=self.provider,
                operation="set",
                key=key,
                error=str(e),
            )
            self._redis_available = False
            return False

    async def get_state(self) -> CircuitState:
        """Get current circuit state."""
        state_str = await self._get_from_store(
            self._get_key("state"),
            default=self._local_state.value,
        )
        if isinstance(state_str, str):
            try:
                return CircuitState(state_str)
            except ValueError:
                return CircuitState.CLOSED
        return self._local_state

    async def _set_state(self, state: CircuitState) -> None:
        """Set circuit state."""
        self._local_state = state
        await self._set_in_store(self._get_key("state"), state.value)

        logger.info(
            "circuit_breaker_state_change",
            provider=self.provider,
            new_state=state.value,
        )

    async def get_metrics(self) -> CircuitMetrics:
        """Get current metrics."""
        metrics_dict = await self._get_from_store(self._get_key("metrics"))
        if metrics_dict and isinstance(metrics_dict, dict):
            return CircuitMetrics.from_dict(metrics_dict)
        return self._local_metrics

    async def _set_metrics(self, metrics: CircuitMetrics) -> None:
        """Set metrics."""
        self._local_metrics = metrics
        await self._set_in_store(self._get_key("metrics"), metrics.to_dict())

    async def can_execute(self) -> tuple[bool, str]:
        """
        Check if a request can be executed.

        Returns:
            Tuple of (allowed, reason)
        """
        async with self._lock:
            state = await self.get_state()
            metrics = await self.get_metrics()

            if state == CircuitState.CLOSED:
                return True, "circuit_closed"

            if state == CircuitState.OPEN:
                # Check if recovery timeout has passed
                time_since_open = time.time() - metrics.state_changed_at
                if time_since_open >= self.config.recovery_timeout_seconds:
                    # Transition to half-open
                    metrics.state_changed_at = time.time()
                    metrics.half_open_requests = 0
                    await self._set_state(CircuitState.HALF_OPEN)
                    await self._set_metrics(metrics)
                    return True, "circuit_half_open_probe"
                else:
                    remaining = self.config.recovery_timeout_seconds - time_since_open
                    return False, f"circuit_open_retry_in_{remaining:.1f}s"

            if state == CircuitState.HALF_OPEN:
                if metrics.half_open_requests < self.config.half_open_max_requests:
                    return True, "circuit_half_open_probe"
                else:
                    return False, "circuit_half_open_max_probes"

            return True, "unknown_state_allow"

    async def record_success(self) -> None:
        """Record a successful request."""
        async with self._lock:
            state = await self.get_state()
            metrics = await self.get_metrics()

            metrics.total_requests += 1
            metrics.successful_requests += 1
            metrics.consecutive_successes += 1
            metrics.consecutive_failures = 0
            metrics.last_success_time = time.time()

            if state == CircuitState.HALF_OPEN:
                metrics.half_open_requests += 1

                # Check if we should close the circuit
                if metrics.consecutive_successes >= self.config.success_threshold:
                    metrics.state_changed_at = time.time()
                    metrics.half_open_requests = 0
                    await self._set_state(CircuitState.CLOSED)
                    logger.info(
                        "circuit_breaker_closed",
                        provider=self.provider,
                        consecutive_successes=metrics.consecutive_successes,
                    )

            await self._set_metrics(metrics)

    async def record_failure(self, error: Exception | None = None) -> None:
        """
        Record a failed request.

        Args:
            error: The exception that caused the failure
        """
        async with self._lock:
            state = await self.get_state()
            metrics = await self.get_metrics()

            metrics.total_requests += 1
            metrics.failed_requests += 1
            metrics.consecutive_failures += 1
            metrics.consecutive_successes = 0
            metrics.last_failure_time = time.time()

            # Determine if error is retryable
            is_retryable = True
            if isinstance(error, LLMProviderError):
                is_retryable = error.retryable

            if state == CircuitState.CLOSED:
                # Check if we should open the circuit
                should_open = False

                # Check consecutive failures
                if metrics.consecutive_failures >= self.config.failure_threshold:
                    should_open = True

                # Check failure rate (only if minimum requests met)
                if (
                    metrics.total_requests >= self.config.minimum_requests
                    and metrics.failure_rate >= self.config.failure_rate_threshold
                ):
                    should_open = True

                if should_open and is_retryable:
                    metrics.state_changed_at = time.time()
                    await self._set_state(CircuitState.OPEN)
                    logger.warning(
                        "circuit_breaker_opened",
                        provider=self.provider,
                        consecutive_failures=metrics.consecutive_failures,
                        failure_rate=metrics.failure_rate,
                        error_type=type(error).__name__ if error else None,
                    )

            elif state == CircuitState.HALF_OPEN:
                metrics.half_open_requests += 1
                # Any failure in half-open reopens the circuit
                metrics.state_changed_at = time.time()
                metrics.half_open_requests = 0
                await self._set_state(CircuitState.OPEN)
                logger.warning(
                    "circuit_breaker_reopened",
                    provider=self.provider,
                    error_type=type(error).__name__ if error else None,
                )

            await self._set_metrics(metrics)

    async def reset(self) -> None:
        """Manually reset the circuit breaker to closed state."""
        async with self._lock:
            self._local_state = CircuitState.CLOSED
            self._local_metrics = CircuitMetrics()

            await self._set_state(CircuitState.CLOSED)
            await self._set_metrics(self._local_metrics)

            logger.info(
                "circuit_breaker_reset",
                provider=self.provider,
            )

    async def force_open(self) -> None:
        """Manually force the circuit open."""
        async with self._lock:
            metrics = await self.get_metrics()
            metrics.state_changed_at = time.time()
            await self._set_state(CircuitState.OPEN)
            await self._set_metrics(metrics)

            logger.info(
                "circuit_breaker_forced_open",
                provider=self.provider,
            )

    async def get_status(self) -> dict[str, Any]:
        """Get full status of the circuit breaker."""
        state = await self.get_state()
        metrics = await self.get_metrics()

        status = {
            "provider": self.provider,
            "state": state.value,
            "metrics": metrics.to_dict(),
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "failure_rate_threshold": self.config.failure_rate_threshold,
                "recovery_timeout_seconds": self.config.recovery_timeout_seconds,
                "half_open_max_requests": self.config.half_open_max_requests,
                "success_threshold": self.config.success_threshold,
            },
            "redis_available": self._redis_available,
        }

        # Add time until recovery for open circuit
        if state == CircuitState.OPEN:
            time_since_open = time.time() - metrics.state_changed_at
            time_until_half_open = max(
                0,
                self.config.recovery_timeout_seconds - time_since_open,
            )
            status["time_until_half_open_seconds"] = round(time_until_half_open, 1)

        return status


class CircuitBreakerRegistry:
    """
    Registry for managing circuit breakers across providers.

    Provides a centralized way to access and manage circuit breakers.
    """

    def __init__(self, redis: RedisCache | None = None):
        """
        Initialize the registry.

        Args:
            redis: Redis cache client (optional)
        """
        self._redis = redis
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        self._default_config = CircuitBreakerConfig()
        self._provider_configs: dict[str, CircuitBreakerConfig] = {}
        self._lock = asyncio.Lock()

    def set_provider_config(
        self,
        provider: str,
        config: CircuitBreakerConfig,
    ) -> None:
        """Set custom configuration for a specific provider."""
        self._provider_configs[provider] = config

    async def get(self, provider: str) -> CircuitBreaker:
        """
        Get or create a circuit breaker for a provider.

        Args:
            provider: Provider name

        Returns:
            CircuitBreaker instance
        """
        async with self._lock:
            if provider not in self._circuit_breakers:
                config = self._provider_configs.get(provider, self._default_config)
                self._circuit_breakers[provider] = CircuitBreaker(
                    provider=provider,
                    config=config,
                    redis=self._redis,
                )
            return self._circuit_breakers[provider]

    async def get_all_statuses(self) -> dict[str, dict[str, Any]]:
        """Get status of all circuit breakers."""
        statuses = {}
        for provider, cb in self._circuit_breakers.items():
            statuses[provider] = await cb.get_status()
        return statuses

    async def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for cb in self._circuit_breakers.values():
            await cb.reset()

    async def reset(self, provider: str) -> bool:
        """Reset a specific provider's circuit breaker."""
        if provider in self._circuit_breakers:
            await self._circuit_breakers[provider].reset()
            return True
        return False
