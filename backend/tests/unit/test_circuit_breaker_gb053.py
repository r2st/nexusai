"""GB053: M18 testing — Circuit breaker state transitions, edge cases, and registry."""

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest

from app.services.llm_gateway.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerRegistry,
    CircuitMetrics,
    CircuitState,
)
from app.services.llm_gateway.exceptions import (
    AuthenticationError,
    LLMProviderError,
    RateLimitError,
)


class TestCircuitMetrics:
    def test_failure_rate_zero_requests(self):
        m = CircuitMetrics()
        assert m.failure_rate == 0.0

    def test_failure_rate_calculation(self):
        m = CircuitMetrics(total_requests=10, failed_requests=3)
        assert m.failure_rate == pytest.approx(0.3)

    def test_failure_rate_all_failures(self):
        m = CircuitMetrics(total_requests=5, failed_requests=5)
        assert m.failure_rate == pytest.approx(1.0)

    def test_to_dict_roundtrip(self):
        m = CircuitMetrics(
            total_requests=10,
            successful_requests=7,
            failed_requests=3,
            consecutive_failures=2,
            consecutive_successes=0,
            last_failure_time=1000.0,
            last_success_time=999.0,
            half_open_requests=1,
        )
        d = m.to_dict()
        m2 = CircuitMetrics.from_dict(d)
        assert m2.total_requests == 10
        assert m2.failed_requests == 3
        assert m2.consecutive_failures == 2
        assert m2.last_failure_time == 1000.0
        assert m2.half_open_requests == 1
        assert d["failure_rate"] == pytest.approx(0.3)

    def test_from_dict_empty(self):
        m = CircuitMetrics.from_dict({})
        assert m.total_requests == 0
        assert m.failed_requests == 0
        assert m.last_failure_time is None


class TestCircuitBreakerStates:
    @pytest.fixture
    def cb(self):
        return CircuitBreaker(
            provider="test",
            config=CircuitBreakerConfig(
                failure_threshold=3,
                failure_rate_threshold=0.5,
                minimum_requests=3,
                recovery_timeout_seconds=0.1,
                half_open_max_requests=2,
                success_threshold=2,
            ),
        )

    @pytest.mark.asyncio
    async def test_starts_closed(self, cb):
        state = await cb.get_state()
        assert state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_can_execute_when_closed(self, cb):
        allowed, reason = await cb.can_execute()
        assert allowed is True
        assert reason == "circuit_closed"

    @pytest.mark.asyncio
    async def test_opens_after_consecutive_failures(self, cb):
        for _ in range(3):
            await cb.record_failure()
        state = await cb.get_state()
        assert state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_rejects_when_open(self, cb):
        for _ in range(3):
            await cb.record_failure()
        allowed, reason = await cb.can_execute()
        assert allowed is False
        assert "circuit_open" in reason

    @pytest.mark.asyncio
    async def test_transitions_to_half_open_after_timeout(self, cb):
        for _ in range(3):
            await cb.record_failure()
        await asyncio.sleep(0.15)
        allowed, reason = await cb.can_execute()
        assert allowed is True
        assert reason == "circuit_half_open_probe"
        state = await cb.get_state()
        assert state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_half_open_closes_after_successes(self, cb):
        for _ in range(3):
            await cb.record_failure()
        await asyncio.sleep(0.15)
        await cb.can_execute()
        await cb.record_success()
        await cb.record_success()
        state = await cb.get_state()
        assert state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_reopens_on_failure(self, cb):
        for _ in range(3):
            await cb.record_failure()
        await asyncio.sleep(0.15)
        await cb.can_execute()
        await cb.record_failure()
        state = await cb.get_state()
        assert state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_half_open_max_probes_rejects(self, cb):
        for _ in range(3):
            await cb.record_failure()
        await asyncio.sleep(0.15)
        await cb.can_execute()
        metrics = await cb.get_metrics()
        metrics.half_open_requests = 2
        await cb._set_metrics(metrics)
        allowed, reason = await cb.can_execute()
        assert allowed is False
        assert reason == "circuit_half_open_max_probes"

    @pytest.mark.asyncio
    async def test_success_resets_consecutive_failures(self, cb):
        await cb.record_failure()
        await cb.record_failure()
        await cb.record_success()
        metrics = await cb.get_metrics()
        assert metrics.consecutive_failures == 0
        assert metrics.consecutive_successes == 1
        state = await cb.get_state()
        assert state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_non_retryable_error_does_not_open(self, cb):
        err = AuthenticationError("bad key", provider="test")
        for _ in range(5):
            await cb.record_failure(error=err)
        state = await cb.get_state()
        assert state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_retryable_error_opens(self, cb):
        err = RateLimitError("too many", provider="test")
        for _ in range(3):
            await cb.record_failure(error=err)
        state = await cb.get_state()
        assert state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_failure_rate_opens_circuit(self):
        cb = CircuitBreaker(
            provider="test",
            config=CircuitBreakerConfig(
                failure_threshold=100,
                failure_rate_threshold=0.5,
                minimum_requests=4,
            ),
        )
        await cb.record_success()
        await cb.record_success()
        await cb.record_failure()
        await cb.record_failure()
        await cb.record_failure()
        state = await cb.get_state()
        assert state == CircuitState.OPEN


class TestCircuitBreakerOperations:
    @pytest.mark.asyncio
    async def test_reset(self):
        cb = CircuitBreaker(
            provider="test",
            config=CircuitBreakerConfig(failure_threshold=2),
        )
        await cb.record_failure()
        await cb.record_failure()
        assert await cb.get_state() == CircuitState.OPEN
        await cb.reset()
        assert await cb.get_state() == CircuitState.CLOSED
        metrics = await cb.get_metrics()
        assert metrics.total_requests == 0

    @pytest.mark.asyncio
    async def test_force_open(self):
        cb = CircuitBreaker(provider="test")
        await cb.force_open()
        assert await cb.get_state() == CircuitState.OPEN
        allowed, _ = await cb.can_execute()
        assert allowed is False

    @pytest.mark.asyncio
    async def test_get_status_closed(self):
        cb = CircuitBreaker(provider="test-provider")
        status = await cb.get_status()
        assert status["provider"] == "test-provider"
        assert status["state"] == "closed"
        assert "time_until_half_open_seconds" not in status

    @pytest.mark.asyncio
    async def test_get_status_open_shows_recovery_time(self):
        cb = CircuitBreaker(
            provider="test",
            config=CircuitBreakerConfig(
                failure_threshold=1,
                recovery_timeout_seconds=60,
            ),
        )
        await cb.record_failure()
        status = await cb.get_status()
        assert status["state"] == "open"
        assert "time_until_half_open_seconds" in status
        assert status["time_until_half_open_seconds"] > 0

    @pytest.mark.asyncio
    async def test_invalid_state_string_defaults_to_closed(self):
        cb = CircuitBreaker(provider="test")
        cb._local_state = CircuitState.CLOSED
        with patch.object(cb, "_get_from_store", return_value="invalid_state"):
            state = await cb.get_state()
            assert state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_non_string_state_returns_local(self):
        cb = CircuitBreaker(provider="test")
        with patch.object(cb, "_get_from_store", return_value=42):
            state = await cb.get_state()
            assert state == CircuitState.CLOSED


class TestCircuitBreakerRedisFailover:
    @pytest.mark.asyncio
    async def test_redis_error_falls_back_to_local(self):
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = Exception("Redis down")
        cb = CircuitBreaker(provider="test", redis=mock_redis)
        state = await cb.get_state()
        assert state == CircuitState.CLOSED
        assert cb._redis_available is False

    @pytest.mark.asyncio
    async def test_redis_set_error_falls_back(self):
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        mock_redis.set.side_effect = Exception("Redis write fail")
        cb = CircuitBreaker(provider="test", redis=mock_redis)
        result = await cb._set_in_store("key", "value")
        assert result is False
        assert cb._redis_available is False

    @pytest.mark.asyncio
    async def test_no_redis_returns_defaults(self):
        cb = CircuitBreaker(provider="test", redis=None)
        result = await cb._get_from_store("key", default="fallback")
        assert result == "fallback"
        result = await cb._set_in_store("key", "val")
        assert result is False


class TestCircuitBreakerRegistry:
    @pytest.mark.asyncio
    async def test_get_creates_new_breaker(self):
        registry = CircuitBreakerRegistry()
        cb = await registry.get("openai")
        assert cb.provider == "openai"

    @pytest.mark.asyncio
    async def test_get_returns_same_instance(self):
        registry = CircuitBreakerRegistry()
        cb1 = await registry.get("openai")
        cb2 = await registry.get("openai")
        assert cb1 is cb2

    @pytest.mark.asyncio
    async def test_custom_provider_config(self):
        registry = CircuitBreakerRegistry()
        custom = CircuitBreakerConfig(failure_threshold=10)
        registry.set_provider_config("openai", custom)
        cb = await registry.get("openai")
        assert cb.config.failure_threshold == 10

    @pytest.mark.asyncio
    async def test_get_all_statuses(self):
        registry = CircuitBreakerRegistry()
        await registry.get("openai")
        await registry.get("anthropic")
        statuses = await registry.get_all_statuses()
        assert "openai" in statuses
        assert "anthropic" in statuses
        assert statuses["openai"]["state"] == "closed"

    @pytest.mark.asyncio
    async def test_reset_all(self):
        registry = CircuitBreakerRegistry()
        cb = await registry.get("openai")
        await cb.force_open()
        assert await cb.get_state() == CircuitState.OPEN
        await registry.reset_all()
        assert await cb.get_state() == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_reset_specific_provider(self):
        registry = CircuitBreakerRegistry()
        cb = await registry.get("openai")
        await cb.force_open()
        result = await registry.reset("openai")
        assert result is True
        assert await cb.get_state() == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_reset_nonexistent_provider(self):
        registry = CircuitBreakerRegistry()
        result = await registry.reset("nonexistent")
        assert result is False
