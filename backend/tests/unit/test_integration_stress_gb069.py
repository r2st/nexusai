"""GB069: Integration Point Stress Testing.

Tests failure modes for external integrations: LLM Gateway (Google/Gemini),
Redis cache, Neo4j knowledge graph, email notifications, S3 storage,
and circuit breaker. Verifies graceful degradation under timeouts, 5xx,
malformed responses, rate limits, expired tokens, and partial success.
"""

import asyncio
import json
import smtplib
import time
from collections import deque
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from uuid import uuid4

import httpx
import pytest

from app.services.llm_gateway.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerRegistry,
    CircuitMetrics,
    CircuitState,
)
from app.services.llm_gateway.config import (
    GatewayConfig,
    ProviderPriority,
    RouteStrategy,
)
from app.services.llm_gateway.exceptions import (
    AuthenticationError,
    CapacityError,
    ConnectionError as LLMConnectionError,
    ContentFilterError,
    ContextLengthError,
    InternalProviderError,
    InvalidRequestError,
    LLMProviderError,
    ModelNotFoundError,
    ProviderTimeoutError,
    RateLimitError,
    ServiceUnavailableError,
    classify_error,
)
from app.services.llm_gateway.models import (
    LLMRequest,
    LLMResponse,
    Message,
    MessageRole,
    UsageStats,
)
from app.services.llm_gateway.router import ProviderRouter
from app.services.llm_gateway.service import LLMGateway
from app.services.cache.redis_cache import RedisCache
from app.services.cache.config import CacheConfig
from app.services.knowledge_graph.neo4j_client import Neo4jClient, Neo4jConfig
from app.services.notifications.email import EmailNotifier
from app.services.notifications.models import (
    EmailConfig,
    NotificationChannel,
    NotificationMessage,
    NotificationPriority,
    NotificationType,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def gateway_config():
    return GatewayConfig(
        default_model="gemini-1.5-flash",
        route_strategy=RouteStrategy.PRIORITY,
        max_retries=3,
        enable_failover=True,
        providers=[
            ProviderPriority(
                name="google",
                priority=1,
                enabled=True,
                models=["gemini-1.5-flash", "gemini-1.5-pro"],
            ),
            ProviderPriority(
                name="openai",
                priority=2,
                enabled=True,
                models=["gpt-4o", "gpt-4o-mini"],
            ),
            ProviderPriority(
                name="anthropic",
                priority=3,
                enabled=True,
                models=["claude-3-5-sonnet"],
            ),
        ],
        user_rate_limit_per_minute=60,
    )


@pytest.fixture
def sample_request():
    return LLMRequest(
        request_id=uuid4(),
        user_id="stress_user",
        tenant_id="stress_tenant",
        messages=[
            Message(role=MessageRole.USER, content="Summarize this document."),
        ],
        model="gemini-1.5-flash",
        provider="google",
        temperature=0.7,
        max_tokens=500,
    )


@pytest.fixture
def mock_successful_response():
    return MagicMock(
        content="Success response",
        role=MagicMock(value="assistant"),
        finish_reason="stop",
        usage=MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        tool_calls=None,
    )


@pytest.fixture
def circuit_config():
    return CircuitBreakerConfig(
        failure_threshold=3,
        failure_rate_threshold=0.5,
        minimum_requests=3,
        recovery_timeout_seconds=1.0,
        half_open_max_requests=2,
        success_threshold=2,
        window_size_seconds=60,
    )


@pytest.fixture
def email_config():
    return EmailConfig(
        smtp_host="smtp.test.local",
        smtp_port=587,
        smtp_user="testuser",
        smtp_password="testpass",
        from_email="noreply@nexusai.test",
        from_name="NexusAI",
        use_tls=True,
    )


@pytest.fixture
def notification_message():
    return NotificationMessage(
        title="Test Alert",
        body="Integration stress test notification.",
        type=NotificationType.ANALYSIS_COMPLETE,
        priority=NotificationPriority.HIGH,
        source="stress_test",
    )


@pytest.fixture
def neo4j_config():
    return Neo4jConfig(
        uri="bolt://localhost:7687",
        username="neo4j",
        password="testpassword",
        database="neo4j",
        connection_timeout=5.0,
    )


# =============================================================================
# 1. LLM Gateway — Google/Gemini Provider Failure Modes
# =============================================================================


class TestGeminiProviderFailures:
    """Test Google Gemini LLM provider failure modes."""

    @pytest.mark.asyncio
    async def test_gemini_timeout_triggers_failover(
        self, gateway_config, sample_request, mock_successful_response
    ):
        """Gemini timeout should trigger failover to next provider."""
        with patch("app.services.llm_gateway.service.LLMGateway._init_providers"):
            gateway = LLMGateway(gateway_config)

            mock_google = MagicMock()
            mock_google.chat = AsyncMock(
                side_effect=httpx.TimeoutException("Request timed out after 30s")
            )
            mock_openai = MagicMock()
            mock_openai.chat = AsyncMock(return_value=mock_successful_response)

            gateway._providers["google"] = mock_google
            gateway._providers["openai"] = mock_openai

            response = await gateway.complete(sample_request)

            assert response.provider == "openai"
            assert response.content == "Success response"
            mock_google.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_gemini_500_internal_error(
        self, gateway_config, sample_request, mock_successful_response
    ):
        """Gemini 500 error should classify as retryable and failover."""
        with patch("app.services.llm_gateway.service.LLMGateway._init_providers"):
            gateway = LLMGateway(gateway_config)

            http_error = httpx.HTTPStatusError(
                "Internal Server Error",
                request=httpx.Request("POST", "https://api.google.com"),
                response=httpx.Response(500),
            )
            mock_google = MagicMock()
            mock_google.chat = AsyncMock(side_effect=http_error)
            mock_openai = MagicMock()
            mock_openai.chat = AsyncMock(return_value=mock_successful_response)

            gateway._providers["google"] = mock_google
            gateway._providers["openai"] = mock_openai

            response = await gateway.complete(sample_request)

            assert response.provider == "openai"

    @pytest.mark.asyncio
    async def test_gemini_503_service_unavailable(
        self, gateway_config, sample_request, mock_successful_response
    ):
        """Gemini 503 should trigger failover to backup provider."""
        with patch("app.services.llm_gateway.service.LLMGateway._init_providers"):
            gateway = LLMGateway(gateway_config)

            mock_google = MagicMock()
            mock_google.chat = AsyncMock(
                side_effect=Exception("Service temporarily unavailable (503)")
            )
            mock_openai = MagicMock()
            mock_openai.chat = AsyncMock(return_value=mock_successful_response)

            gateway._providers["google"] = mock_google
            gateway._providers["openai"] = mock_openai

            response = await gateway.complete(sample_request)

            assert response.provider == "openai"

    @pytest.mark.asyncio
    async def test_gemini_rate_limit_429(
        self, gateway_config, sample_request, mock_successful_response
    ):
        """Gemini 429 rate limit should trigger failover."""
        with patch("app.services.llm_gateway.service.LLMGateway._init_providers"):
            gateway = LLMGateway(gateway_config)

            mock_google = MagicMock()
            mock_google.chat = AsyncMock(
                side_effect=Exception("Rate limit exceeded. Too many requests")
            )
            mock_openai = MagicMock()
            mock_openai.chat = AsyncMock(return_value=mock_successful_response)

            gateway._providers["google"] = mock_google
            gateway._providers["openai"] = mock_openai

            response = await gateway.complete(sample_request)

            assert response.provider == "openai"

    @pytest.mark.asyncio
    async def test_gemini_expired_api_key_401(self, gateway_config, sample_request):
        """Expired/invalid API key (401) should NOT failover (non-retryable)."""
        with patch("app.services.llm_gateway.service.LLMGateway._init_providers"):
            gateway = LLMGateway(gateway_config)

            mock_google = MagicMock()
            mock_google.chat = AsyncMock(
                side_effect=AuthenticationError(
                    "API key invalid or expired",
                    provider="google",
                )
            )

            gateway._providers["google"] = mock_google
            gateway._providers["openai"] = MagicMock()

            with pytest.raises(Exception, match="All providers failed"):
                await gateway.complete(sample_request)

    @pytest.mark.asyncio
    async def test_gemini_malformed_response_missing_candidates(
        self, gateway_config, sample_request
    ):
        """Gemini returning empty candidates should still produce a response."""
        with patch("app.services.llm_gateway.service.LLMGateway._init_providers"):
            gateway = LLMGateway(gateway_config)

            mock_google = MagicMock()
            mock_google.chat = AsyncMock(
                return_value=MagicMock(
                    content="",
                    role=MagicMock(value="assistant"),
                    finish_reason="stop",
                    usage=MagicMock(prompt_tokens=5, completion_tokens=0, total_tokens=5),
                    tool_calls=None,
                )
            )
            gateway._providers["google"] = mock_google

            response = await gateway.complete(sample_request)

            assert response.content == ""
            assert response.provider == "google"

    @pytest.mark.asyncio
    async def test_gemini_all_providers_fail_raises(
        self, gateway_config, sample_request
    ):
        """When all providers fail, gateway raises with last error."""
        with patch("app.services.llm_gateway.service.LLMGateway._init_providers"):
            gateway = LLMGateway(gateway_config)

            for name in ["google", "openai", "anthropic"]:
                mock = MagicMock()
                mock.chat = AsyncMock(
                    side_effect=Exception(f"{name} is down")
                )
                gateway._providers[name] = mock

            with pytest.raises(Exception, match="All providers failed"):
                await gateway.complete(sample_request)

    @pytest.mark.asyncio
    async def test_gemini_partial_stream_error(self, gateway_config, sample_request):
        """Stream that fails midway should propagate the error."""
        with patch("app.services.llm_gateway.service.LLMGateway._init_providers"):
            gateway = LLMGateway(gateway_config)

            async def failing_stream(*args, **kwargs):
                yield "partial "
                yield "content "
                raise httpx.ReadTimeout("Connection dropped mid-stream")

            mock_google = MagicMock()
            mock_google.chat_stream = failing_stream
            gateway._providers["google"] = mock_google

            chunks = []
            with pytest.raises(httpx.ReadTimeout):
                async for chunk in gateway.stream(sample_request):
                    chunks.append(chunk.content)

            assert len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_gateway_records_metrics_on_failure(
        self, gateway_config, sample_request, mock_successful_response
    ):
        """Gateway should record provider failure metrics."""
        with patch("app.services.llm_gateway.service.LLMGateway._init_providers"):
            gateway = LLMGateway(gateway_config)

            mock_google = MagicMock()
            mock_google.chat = AsyncMock(
                side_effect=Exception("Temporary glitch")
            )
            mock_openai = MagicMock()
            mock_openai.chat = AsyncMock(return_value=mock_successful_response)

            gateway._providers["google"] = mock_google
            gateway._providers["openai"] = mock_openai

            await gateway.complete(sample_request)

            google_status = gateway.router.get_provider_status("google")
            assert google_status.errors_last_minute >= 1


# =============================================================================
# 2. Circuit Breaker Stress Tests
# =============================================================================


class TestCircuitBreakerStress:
    """Stress test circuit breaker under rapid failure/recovery cycles."""

    @pytest.mark.asyncio
    async def test_circuit_opens_after_threshold_failures(self, circuit_config):
        """Circuit opens after failure_threshold consecutive failures."""
        cb = CircuitBreaker("test_provider", circuit_config)

        for i in range(circuit_config.failure_threshold):
            await cb.record_failure(ProviderTimeoutError("timeout", provider="test"))

        state = await cb.get_state()
        assert state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_circuit_rejects_requests_when_open(self, circuit_config):
        """Open circuit rejects new requests."""
        cb = CircuitBreaker("test_provider", circuit_config)

        for _ in range(circuit_config.failure_threshold):
            await cb.record_failure(ProviderTimeoutError("timeout", provider="test"))

        allowed, reason = await cb.can_execute()
        assert allowed is False
        assert "circuit_open" in reason

    @pytest.mark.asyncio
    async def test_circuit_transitions_to_half_open(self, circuit_config):
        """Circuit transitions to half-open after recovery timeout."""
        circuit_config.recovery_timeout_seconds = 0.1
        cb = CircuitBreaker("test_provider", circuit_config)

        for _ in range(circuit_config.failure_threshold):
            await cb.record_failure(ProviderTimeoutError("timeout", provider="test"))

        assert await cb.get_state() == CircuitState.OPEN

        await asyncio.sleep(0.15)

        allowed, reason = await cb.can_execute()
        assert allowed is True
        assert "half_open" in reason

    @pytest.mark.asyncio
    async def test_circuit_closes_after_half_open_successes(self, circuit_config):
        """Circuit closes after enough successes in half-open state."""
        circuit_config.recovery_timeout_seconds = 0.1
        cb = CircuitBreaker("test_provider", circuit_config)

        for _ in range(circuit_config.failure_threshold):
            await cb.record_failure(ProviderTimeoutError("timeout", provider="test"))

        await asyncio.sleep(0.15)
        await cb.can_execute()  # triggers half-open

        for _ in range(circuit_config.success_threshold):
            await cb.record_success()

        state = await cb.get_state()
        assert state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_reopens_on_half_open_failure(self, circuit_config):
        """Any failure in half-open reopens the circuit."""
        circuit_config.recovery_timeout_seconds = 0.1
        cb = CircuitBreaker("test_provider", circuit_config)

        for _ in range(circuit_config.failure_threshold):
            await cb.record_failure(ProviderTimeoutError("timeout", provider="test"))

        await asyncio.sleep(0.15)
        await cb.can_execute()

        await cb.record_failure(ProviderTimeoutError("still failing", provider="test"))

        state = await cb.get_state()
        assert state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_non_retryable_error_does_not_open_circuit(self, circuit_config):
        """Non-retryable errors (e.g., auth) shouldn't open the circuit."""
        cb = CircuitBreaker("test_provider", circuit_config)

        for _ in range(circuit_config.failure_threshold + 2):
            await cb.record_failure(
                AuthenticationError("Bad API key", provider="test")
            )

        state = await cb.get_state()
        assert state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_breaker_reset(self, circuit_config):
        """Manual reset returns circuit to closed."""
        cb = CircuitBreaker("test_provider", circuit_config)

        for _ in range(circuit_config.failure_threshold):
            await cb.record_failure(ProviderTimeoutError("timeout", provider="test"))

        assert await cb.get_state() == CircuitState.OPEN

        await cb.reset()

        assert await cb.get_state() == CircuitState.CLOSED
        allowed, _ = await cb.can_execute()
        assert allowed is True

    @pytest.mark.asyncio
    async def test_circuit_metrics_accuracy(self, circuit_config):
        """Metrics should accurately reflect successes and failures."""
        cb = CircuitBreaker("test_provider", circuit_config)

        await cb.record_success()
        await cb.record_success()
        await cb.record_failure(ProviderTimeoutError("t", provider="test"))

        metrics = await cb.get_metrics()
        assert metrics.total_requests == 3
        assert metrics.successful_requests == 2
        assert metrics.failed_requests == 1
        assert metrics.consecutive_failures == 1
        assert metrics.consecutive_successes == 0

    @pytest.mark.asyncio
    async def test_circuit_registry_manages_multiple_providers(self, circuit_config):
        """Registry should maintain separate circuit breakers per provider."""
        registry = CircuitBreakerRegistry()
        registry.set_provider_config("google", circuit_config)
        registry.set_provider_config("openai", circuit_config)

        google_cb = await registry.get("google")
        openai_cb = await registry.get("openai")

        for _ in range(circuit_config.failure_threshold):
            await google_cb.record_failure(ProviderTimeoutError("t", provider="google"))

        assert await google_cb.get_state() == CircuitState.OPEN
        assert await openai_cb.get_state() == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_breaker_falls_back_to_memory_without_redis(self, circuit_config):
        """Circuit breaker should work with in-memory state when Redis unavailable."""
        cb = CircuitBreaker("test_provider", circuit_config, redis=None)

        await cb.record_success()
        await cb.record_failure(ProviderTimeoutError("t", provider="test"))

        metrics = await cb.get_metrics()
        assert metrics.total_requests == 2

        status = await cb.get_status()
        assert status["redis_available"] is False


# =============================================================================
# 3. Error Classification Tests
# =============================================================================


class TestErrorClassification:
    """Test that errors are correctly classified for failover decisions."""

    def test_timeout_classified_as_retryable(self):
        err = classify_error("google", Exception("request timed out"))
        assert isinstance(err, ProviderTimeoutError)
        assert err.retryable is True

    def test_rate_limit_classified_as_retryable(self):
        err = classify_error("google", Exception("rate limit exceeded"))
        assert isinstance(err, RateLimitError)
        assert err.retryable is True

    def test_auth_error_classified_as_non_retryable(self):
        err = classify_error("google", Exception("invalid api key"))
        assert isinstance(err, AuthenticationError)
        assert err.retryable is False

    def test_content_filter_classified_as_non_retryable(self):
        err = classify_error("google", Exception("content blocked by safety filters"))
        assert isinstance(err, ContentFilterError)
        assert err.retryable is False

    def test_context_length_classified_as_non_retryable(self):
        err = classify_error("google", Exception("context length exceeded"))
        assert isinstance(err, ContextLengthError)
        assert err.retryable is False

    def test_capacity_error_classified_as_retryable(self):
        err = classify_error("google", Exception("server overloaded"))
        assert isinstance(err, CapacityError)
        assert err.retryable is True

    def test_connection_error_classified_as_retryable(self):
        err = classify_error("google", Exception("connection refused"))
        assert isinstance(err, LLMConnectionError)
        assert err.retryable is True

    def test_model_not_found_non_retryable(self):
        err = classify_error("google", Exception("model does not exist"))
        assert isinstance(err, ModelNotFoundError)
        assert err.retryable is False

    def test_unknown_error_defaults_to_internal_retryable(self):
        err = classify_error("google", Exception("something weird happened"))
        assert isinstance(err, InternalProviderError)
        assert err.retryable is True

    def test_status_code_401_classifies_auth(self):
        err = classify_error("google", Exception("err"), status_code=401)
        assert isinstance(err, AuthenticationError)

    def test_status_code_429_classifies_rate_limit(self):
        err = classify_error("google", Exception("err"), status_code=429)
        assert isinstance(err, RateLimitError)

    def test_status_code_503_classifies_service_unavailable(self):
        err = classify_error("google", Exception("err"), status_code=503)
        assert isinstance(err, ServiceUnavailableError)

    def test_google_quota_classified(self):
        err = classify_error("google", Exception("quota exceeded for project"))
        assert isinstance(err, RateLimitError)

    def test_google_safety_block_classified(self):
        err = classify_error("google", Exception("blocked by safety settings"))
        assert isinstance(err, ContentFilterError)


# =============================================================================
# 4. Redis Cache Failure Modes
# =============================================================================


class TestRedisCacheFailures:
    """Test Redis cache graceful degradation under failures."""

    @pytest.mark.asyncio
    async def test_redis_get_returns_none_on_connection_error(self):
        """Cache get should return None when Redis is unreachable."""
        from redis.exceptions import ConnectionError as RedisConnError

        cache = RedisCache(CacheConfig(redis_url="redis://unreachable:6379/0"))
        cache._client = MagicMock()
        cache._client.get = AsyncMock(side_effect=RedisConnError("Connection refused"))

        result = await cache.get("some_key")

        assert result is None
        assert cache._errors == 1

    @pytest.mark.asyncio
    async def test_redis_set_returns_false_on_error(self):
        """Cache set should return False on write failure."""
        from redis.exceptions import ConnectionError as RedisConnError

        cache = RedisCache(CacheConfig(redis_url="redis://unreachable:6379/0"))
        cache._client = MagicMock()
        cache._client.set = AsyncMock(side_effect=RedisConnError("Connection refused"))

        result = await cache.set("key", "value")

        assert result is False
        assert cache._errors == 1

    @pytest.mark.asyncio
    async def test_redis_delete_returns_false_on_error(self):
        """Cache delete should return False on failure."""
        from redis.exceptions import TimeoutError as RedisTimeout

        cache = RedisCache(CacheConfig(redis_url="redis://slow:6379/0"))
        cache._client = MagicMock()
        cache._client.delete = AsyncMock(side_effect=RedisTimeout("Command timed out"))

        result = await cache.delete("key")

        assert result is False

    @pytest.mark.asyncio
    async def test_redis_exists_returns_false_on_error(self):
        """Cache exists should return False on failure."""
        from redis.exceptions import RedisError

        cache = RedisCache(CacheConfig(redis_url="redis://localhost:6379/0"))
        cache._client = MagicMock()
        cache._client.exists = AsyncMock(side_effect=RedisError("Unknown error"))

        result = await cache.exists("key")

        assert result is False

    @pytest.mark.asyncio
    async def test_redis_mget_returns_empty_on_error(self):
        """Cache get_many should return empty dict on failure."""
        from redis.exceptions import ConnectionError as RedisConnError

        cache = RedisCache(CacheConfig(redis_url="redis://localhost:6379/0"))
        cache._client = MagicMock()
        cache._client.mget = AsyncMock(side_effect=RedisConnError("Connection lost"))

        result = await cache.get_many(["k1", "k2", "k3"])

        assert result == {}

    @pytest.mark.asyncio
    async def test_redis_mset_returns_zero_on_error(self):
        """Cache set_many should return 0 on failure."""
        from redis.exceptions import RedisError

        cache = RedisCache(CacheConfig(redis_url="redis://localhost:6379/0"))
        cache._client = MagicMock()

        mock_pipe = AsyncMock()
        mock_pipe.__aenter__ = AsyncMock(return_value=mock_pipe)
        mock_pipe.__aexit__ = AsyncMock(return_value=False)
        mock_pipe.set = MagicMock()
        mock_pipe.execute = AsyncMock(side_effect=RedisError("Pipeline failed"))
        cache._client.pipeline = MagicMock(return_value=mock_pipe)

        result = await cache.set_many({"a": 1, "b": 2})

        assert result == 0

    @pytest.mark.asyncio
    async def test_redis_increment_returns_zero_on_error(self):
        """Cache increment should return 0 on failure."""
        from redis.exceptions import RedisError

        cache = RedisCache(CacheConfig(redis_url="redis://localhost:6379/0"))
        cache._client = MagicMock()
        cache._client.incrby = AsyncMock(side_effect=RedisError("Increment failed"))

        result = await cache.increment("counter_key")

        assert result == 0

    @pytest.mark.asyncio
    async def test_redis_rate_limit_fails_open(self):
        """Rate limiting should fail open (allow) when Redis is down."""
        from redis.exceptions import ConnectionError as RedisConnError

        cache = RedisCache(CacheConfig(redis_url="redis://localhost:6379/0"))
        cache._client = MagicMock()
        cache._client.pipeline = MagicMock(
            side_effect=RedisConnError("Connection refused")
        )

        allowed, remaining = await cache.check_rate_limit(
            "user:123", limit=10, window_seconds=60
        )

        assert allowed is True
        assert remaining == 10

    @pytest.mark.asyncio
    async def test_redis_stats_returns_error_info(self):
        """Stats should include error information when Redis fails."""
        from redis.exceptions import ConnectionError as RedisConnError

        cache = RedisCache(CacheConfig(redis_url="redis://localhost:6379/0"))
        cache._client = MagicMock()
        cache._client.info = AsyncMock(side_effect=RedisConnError("Connection lost"))
        cache._hits = 5
        cache._misses = 3
        cache._errors = 2

        stats = await cache.get_stats()

        assert stats["hits"] == 5
        assert stats["misses"] == 3
        assert stats["errors"] >= 2
        assert "error" in stats["redis"]

    @pytest.mark.asyncio
    async def test_redis_serialization_handles_complex_types(self):
        """Serialization should handle all types gracefully."""
        cache = RedisCache()

        assert json.loads(cache._serialize(42))["_value"] == 42
        assert json.loads(cache._serialize("hello"))["_value"] == "hello"
        assert json.loads(cache._serialize({"key": "val"}))["_value"] == {"key": "val"}
        assert json.loads(cache._serialize([1, 2, 3]))["_value"] == [1, 2, 3]

        class Unserializable:
            pass

        result = cache._serialize(Unserializable())
        parsed = json.loads(result)
        assert parsed["_type"] == "string"


# =============================================================================
# 5. Neo4j Knowledge Graph Failure Modes
# =============================================================================


class TestNeo4jFailures:
    """Test Neo4j client graceful degradation."""

    @pytest.mark.asyncio
    async def test_neo4j_connectivity_failure(self, neo4j_config):
        """verify_connectivity returns False when Neo4j is unreachable."""
        client = Neo4jClient(neo4j_config)

        mock_driver = AsyncMock()
        mock_driver.verify_connectivity = AsyncMock(
            side_effect=Exception("Connection refused to bolt://localhost:7687")
        )
        client._async_driver = mock_driver

        result = await client.verify_connectivity()

        assert result is False

    @pytest.mark.asyncio
    async def test_neo4j_query_timeout(self, neo4j_config):
        """Query timeout should propagate as exception."""
        client = Neo4jClient(neo4j_config)

        mock_session = AsyncMock()
        mock_session.run = AsyncMock(
            side_effect=Exception("Transaction timeout after 30000ms")
        )
        mock_session.close = AsyncMock()

        mock_driver = AsyncMock()
        mock_driver.session = MagicMock(return_value=mock_session)
        client._async_driver = mock_driver

        with pytest.raises(Exception, match="Transaction timeout"):
            await client.execute_query("MATCH (n) RETURN n LIMIT 10")

    @pytest.mark.asyncio
    async def test_neo4j_driver_import_error(self, neo4j_config):
        """Missing neo4j package should cause verify_connectivity to return False."""
        client = Neo4jClient(neo4j_config)
        client._async_driver = None

        with patch(
            "app.services.knowledge_graph.neo4j_client.Neo4jClient._get_async_driver",
            side_effect=ImportError("neo4j package not installed"),
        ):
            result = await client.verify_connectivity()
            assert result is False

    @pytest.mark.asyncio
    async def test_neo4j_auth_failure(self, neo4j_config):
        """Wrong credentials should surface auth error."""
        client = Neo4jClient(neo4j_config)

        mock_driver = AsyncMock()
        mock_driver.verify_connectivity = AsyncMock(
            side_effect=Exception("The client is unauthorized due to authentication failure")
        )
        client._async_driver = mock_driver

        result = await client.verify_connectivity()
        assert result is False

    @pytest.mark.asyncio
    async def test_neo4j_write_transaction_failure(self, neo4j_config):
        """Write transaction failure should propagate."""
        client = Neo4jClient(neo4j_config)

        mock_session = AsyncMock()
        mock_session.run = AsyncMock(
            side_effect=Exception("Neo.ClientError.Schema.ConstraintValidationFailed")
        )
        mock_session.close = AsyncMock()

        mock_driver = AsyncMock()
        mock_driver.session = MagicMock(return_value=mock_session)
        client._async_driver = mock_driver

        with pytest.raises(Exception, match="ConstraintValidationFailed"):
            await client.execute_write(
                "CREATE (n:Agent {name: $name})",
                {"name": "duplicate_agent"},
            )

    @pytest.mark.asyncio
    async def test_neo4j_partial_query_results(self, neo4j_config):
        """Node count query should handle empty results."""
        client = Neo4jClient(neo4j_config)

        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.data = AsyncMock(return_value=[])
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.close = AsyncMock()

        mock_driver = AsyncMock()
        mock_driver.session = MagicMock(return_value=mock_session)
        client._async_driver = mock_driver

        count = await client.get_node_count("NonExistentLabel")
        assert count == 0

    @pytest.mark.asyncio
    async def test_neo4j_close_is_idempotent(self, neo4j_config):
        """Closing a client multiple times should not raise."""
        client = Neo4jClient(neo4j_config)
        client._async_driver = AsyncMock()
        client._async_driver.close = AsyncMock()

        await client.close()
        await client.close()


# =============================================================================
# 6. Email Notification Failure Modes
# =============================================================================


class TestEmailNotificationFailures:
    """Test email notification graceful degradation."""

    @pytest.mark.asyncio
    async def test_email_no_recipients_returns_failure(
        self, email_config, notification_message
    ):
        """Sending to empty recipients list should return failure."""
        notifier = EmailNotifier(email_config)
        result = await notifier.send(notification_message, [])

        assert result.success is False
        assert result.channel == NotificationChannel.EMAIL
        assert "No recipients" in result.error

    @pytest.mark.asyncio
    async def test_email_smtp_connection_refused(
        self, email_config, notification_message
    ):
        """SMTP connection refused should return failure result, not raise."""
        notifier = EmailNotifier(email_config)

        with patch.object(
            notifier,
            "_send_smtp",
            new_callable=AsyncMock,
            side_effect=smtplib.SMTPConnectError(
                421, "Connection refused to smtp.test.local:587"
            ),
        ):
            result = await notifier.send(
                notification_message, ["user@example.com"]
            )

        assert result.success is False
        assert result.channel == NotificationChannel.EMAIL
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_email_smtp_auth_failure(
        self, email_config, notification_message
    ):
        """SMTP auth failure should return failure result."""
        notifier = EmailNotifier(email_config)

        with patch.object(
            notifier,
            "_send_smtp",
            new_callable=AsyncMock,
            side_effect=smtplib.SMTPAuthenticationError(
                535, "Authentication credentials invalid"
            ),
        ):
            result = await notifier.send(
                notification_message, ["user@example.com"]
            )

        assert result.success is False
        assert "Authentication" in result.error

    @pytest.mark.asyncio
    async def test_email_smtp_timeout(self, email_config, notification_message):
        """SMTP timeout should return failure result."""
        notifier = EmailNotifier(email_config)

        with patch.object(
            notifier,
            "_send_smtp",
            new_callable=AsyncMock,
            side_effect=smtplib.SMTPServerDisconnected(
                "Connection unexpectedly closed"
            ),
        ):
            result = await notifier.send(
                notification_message, ["user@example.com"]
            )

        assert result.success is False

    @pytest.mark.asyncio
    async def test_email_success_path(self, email_config, notification_message):
        """Successful email send should return success result."""
        notifier = EmailNotifier(email_config)

        with patch.object(
            notifier, "_send_smtp", new_callable=AsyncMock
        ):
            result = await notifier.send(
                notification_message, ["user@example.com"]
            )

        assert result.success is True
        assert result.channel == NotificationChannel.EMAIL

    @pytest.mark.asyncio
    async def test_email_subject_includes_priority(
        self, email_config, notification_message
    ):
        """Critical/high priority emails should have priority prefix."""
        notifier = EmailNotifier(email_config)

        notification_message.priority = NotificationPriority.CRITICAL
        subject = notifier._get_subject(notification_message)
        assert subject.startswith("[CRITICAL]")

        notification_message.priority = NotificationPriority.HIGH
        subject = notifier._get_subject(notification_message)
        assert subject.startswith("[HIGH]")

    @pytest.mark.asyncio
    async def test_email_html_rendering_handles_empty_data(
        self, email_config, notification_message
    ):
        """HTML rendering should handle missing optional fields."""
        notifier = EmailNotifier(email_config)

        notification_message.data = None
        notification_message.actions = None
        notification_message.footer = None

        email = notifier._build_email(notification_message, ["test@test.com"])
        assert email is not None


# =============================================================================
# 7. S3 Storage Failure Modes
# =============================================================================


class TestS3StorageFailures:
    """Test S3 storage backend failure modes."""

    @pytest.mark.asyncio
    async def test_s3_download_missing_key_returns_none(self):
        """Download of non-existent key should return None."""
        from app.services.storage.s3 import S3StorageBackend
        from app.services.storage.base import StorageConfig, StorageType

        config = StorageConfig(
            storage_type=StorageType.S3,
            bucket_name="test-bucket",
            region="us-east-1",
        )
        backend = S3StorageBackend(config)

        mock_client = MagicMock()
        mock_exceptions = MagicMock()
        mock_exceptions.NoSuchKey = type("NoSuchKey", (Exception,), {})
        mock_client.exceptions = mock_exceptions
        mock_client.get_object = MagicMock(
            side_effect=mock_exceptions.NoSuchKey("Not found")
        )
        backend._client = mock_client

        with patch("asyncio.get_event_loop") as mock_loop:
            loop = MagicMock()
            mock_loop.return_value = loop
            loop.run_in_executor = AsyncMock(
                side_effect=mock_exceptions.NoSuchKey("Not found")
            )

            result = await backend.download("nonexistent/file.txt")
            assert result is None

    @pytest.mark.asyncio
    async def test_s3_delete_failure_returns_false(self):
        """Delete failure should return False, not raise."""
        from app.services.storage.s3 import S3StorageBackend
        from app.services.storage.base import StorageConfig, StorageType

        config = StorageConfig(
            storage_type=StorageType.S3,
            bucket_name="test-bucket",
            region="us-east-1",
        )
        backend = S3StorageBackend(config)
        backend._client = MagicMock()

        with patch("asyncio.get_event_loop") as mock_loop:
            loop = MagicMock()
            mock_loop.return_value = loop
            loop.run_in_executor = AsyncMock(
                side_effect=Exception("Access denied: bucket policy violation")
            )

            result = await backend.delete("protected/file.txt")
            assert result is False

    @pytest.mark.asyncio
    async def test_s3_get_url_failure_returns_none(self):
        """URL generation failure should return None."""
        from app.services.storage.s3 import S3StorageBackend
        from app.services.storage.base import StorageConfig, StorageType

        config = StorageConfig(
            storage_type=StorageType.S3,
            bucket_name="test-bucket",
            region="us-east-1",
        )
        backend = S3StorageBackend(config)
        backend._client = MagicMock()

        with patch("asyncio.get_event_loop") as mock_loop:
            loop = MagicMock()
            mock_loop.return_value = loop
            loop.run_in_executor = AsyncMock(
                side_effect=Exception("Credentials expired")
            )

            result = await backend.get_url("some/file.txt")
            assert result is None

    @pytest.mark.asyncio
    async def test_s3_list_files_failure_returns_empty(self):
        """List files failure should return empty list."""
        from app.services.storage.s3 import S3StorageBackend
        from app.services.storage.base import StorageConfig, StorageType

        config = StorageConfig(
            storage_type=StorageType.S3,
            bucket_name="test-bucket",
            region="us-east-1",
        )
        backend = S3StorageBackend(config)
        backend._client = MagicMock()

        with patch("asyncio.get_event_loop") as mock_loop:
            loop = MagicMock()
            mock_loop.return_value = loop
            loop.run_in_executor = AsyncMock(
                side_effect=Exception("Network timeout")
            )

            result = await backend.list_files("prefix/")
            assert result == []


# =============================================================================
# 8. LLM Gateway Rate Limiting Under Load
# =============================================================================


class TestGatewayRateLimiting:
    """Test gateway rate limiting behavior."""

    def test_rate_limit_enforced_for_heavy_user(self, gateway_config):
        """User exceeding rate limit should be blocked."""
        gateway_config.user_rate_limit_per_minute = 5

        with patch("app.services.llm_gateway.service.LLMGateway._init_providers"):
            gateway = LLMGateway(gateway_config)

            user_id = "heavy_user"
            gateway._rate_limits[user_id] = deque(maxlen=500)
            for _ in range(10):
                gateway._rate_limits[user_id].append(datetime.utcnow())

            rate_info = gateway._check_rate_limit(user_id)
            assert rate_info.is_limited is True
            assert rate_info.requests_remaining == 0

    def test_rate_limit_not_enforced_for_light_user(self, gateway_config):
        """User within rate limit should not be blocked."""
        gateway_config.user_rate_limit_per_minute = 60

        with patch("app.services.llm_gateway.service.LLMGateway._init_providers"):
            gateway = LLMGateway(gateway_config)

            rate_info = gateway._check_rate_limit("light_user")
            assert rate_info.is_limited is False

    def test_rate_limit_not_enforced_for_none_user(self, gateway_config):
        """No user ID should bypass rate limiting."""
        with patch("app.services.llm_gateway.service.LLMGateway._init_providers"):
            gateway = LLMGateway(gateway_config)

            rate_info = gateway._check_rate_limit(None)
            assert rate_info.is_limited is False

    @pytest.mark.asyncio
    async def test_rate_limited_user_gets_exception(self, gateway_config):
        """Rate-limited user should get exception on complete()."""
        gateway_config.user_rate_limit_per_minute = 1

        with patch("app.services.llm_gateway.service.LLMGateway._init_providers"):
            gateway = LLMGateway(gateway_config)

            user_id = "rate_limited"
            gateway._rate_limits[user_id] = deque(maxlen=500)
            for _ in range(5):
                gateway._rate_limits[user_id].append(datetime.utcnow())

            request = LLMRequest(
                request_id=uuid4(),
                user_id=user_id,
                tenant_id="t1",
                messages=[Message(role=MessageRole.USER, content="test")],
            )

            with pytest.raises(Exception, match="Rate limit exceeded"):
                await gateway.complete(request)


# =============================================================================
# 9. Provider Router Stress — Failover Chains
# =============================================================================


class TestProviderRouterStress:
    """Test provider router under multi-failure scenarios."""

    def test_failover_excludes_all_attempted(self, gateway_config):
        """Failover should exclude all previously attempted providers."""
        router = ProviderRouter(gateway_config)

        result = router.get_failover_provider(
            "google", "gpt-4o", attempted=["google", "openai"]
        )

        if result:
            assert result[0] not in ["google", "openai"]

    def test_failover_returns_none_when_all_exhausted(self, gateway_config):
        """Failover returns None when all providers have been tried."""
        router = ProviderRouter(gateway_config)

        result = router.get_failover_provider(
            "google", None, attempted=["google", "openai", "anthropic"]
        )

        assert result is None

    def test_failover_triggered_on_connection_error(self, gateway_config):
        """Connection errors should trigger failover."""
        router = ProviderRouter(gateway_config)

        should = router.should_failover(
            "google", Exception("connection refused")
        )
        assert should is True

    def test_failover_triggered_on_timeout(self, gateway_config):
        """Timeouts should trigger failover."""
        router = ProviderRouter(gateway_config)

        should = router.should_failover(
            "google", Exception("request timeout")
        )
        assert should is True

    def test_failover_not_triggered_when_disabled(self, gateway_config):
        """Failover should not trigger when disabled."""
        gateway_config.enable_failover = False
        router = ProviderRouter(gateway_config)

        should = router.should_failover(
            "google", Exception("timeout")
        )
        assert should is False

    def test_non_retryable_error_no_failover_with_circuit(self, gateway_config):
        """Non-retryable errors should skip failover in circuit-aware path."""
        router = ProviderRouter(gateway_config)

        should = router.should_failover_with_circuit(
            "google",
            AuthenticationError("Bad key", provider="google"),
        )
        assert should is False

    @pytest.mark.asyncio
    async def test_circuit_aware_routing_excludes_open_providers(self, gateway_config):
        """Routing with circuit awareness excludes providers with open circuits."""
        router = ProviderRouter(gateway_config)

        google_cb = await router.get_circuit_breaker("google")
        for _ in range(5):
            await google_cb.record_failure(ProviderTimeoutError("t", provider="google"))

        provider, model = await router.select_provider_with_circuit()
        assert provider != "google"

    @pytest.mark.asyncio
    async def test_provider_health_degrades_with_errors(self, gateway_config):
        """Provider health should degrade with accumulated errors."""
        router = ProviderRouter(gateway_config)

        for _ in range(10):
            router.record_request("google", 100.0, success=False, error="timeout")

        status = router.get_provider_status("google")
        assert status.errors_last_minute >= 10


# =============================================================================
# 10. Circuit Breaker with Redis Fallback
# =============================================================================


class TestCircuitBreakerRedisFallback:
    """Test circuit breaker Redis persistence with fallback to memory."""

    @pytest.mark.asyncio
    async def test_redis_get_failure_falls_back_to_local(self, circuit_config):
        """Redis read failure should fall back to local state."""
        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(side_effect=Exception("Redis timeout"))

        cb = CircuitBreaker("test", circuit_config, redis=mock_redis)

        state = await cb.get_state()
        assert state == CircuitState.CLOSED
        assert cb._redis_available is False

    @pytest.mark.asyncio
    async def test_redis_set_failure_falls_back_to_local(self, circuit_config):
        """Redis write failure should fall back to local state."""
        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock(side_effect=Exception("Redis write error"))

        cb = CircuitBreaker("test", circuit_config, redis=mock_redis)

        await cb.record_success()

        metrics = await cb.get_metrics()
        assert metrics.total_requests == 1
        assert metrics.successful_requests == 1

    @pytest.mark.asyncio
    async def test_circuit_breaker_force_open(self, circuit_config):
        """Force open should immediately reject requests."""
        cb = CircuitBreaker("test", circuit_config)

        await cb.force_open()

        state = await cb.get_state()
        assert state == CircuitState.OPEN

        allowed, _ = await cb.can_execute()
        assert allowed is False

    @pytest.mark.asyncio
    async def test_circuit_breaker_status_includes_recovery_time(self, circuit_config):
        """Status of open circuit should include time until half-open."""
        cb = CircuitBreaker("test", circuit_config)

        for _ in range(circuit_config.failure_threshold):
            await cb.record_failure(ProviderTimeoutError("t", provider="test"))

        status = await cb.get_status()
        assert "time_until_half_open_seconds" in status
        assert status["state"] == "open"
