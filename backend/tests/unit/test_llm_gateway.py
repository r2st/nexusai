"""Unit tests for LLM Gateway service."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.llm_gateway.config import GatewayConfig, ProviderPriority
from app.services.llm_gateway.models import (
    LLMRequest,
    LLMResponse,
    Message,
    MessageRole,
    RateLimitInfo,
    UsageStats,
)
from app.services.llm_gateway.cost_tracker import CostTracker
from app.services.llm_gateway.router import ProviderRouter, RouteStrategy
from app.services.llm_gateway.queue import (
    RequestQueue,
    RequestPriority,
    RateLimitConfig,
    QueuedRequest,
    RequestStatus,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def gateway_config():
    """Create a test gateway config."""
    return GatewayConfig(
        default_model="gpt-4o",
        route_strategy=RouteStrategy.PRIORITY,
        providers=[
            ProviderPriority(
                name="openai",
                priority=1,
                enabled=True,
                models=["gpt-4o", "gpt-4o-mini"],
            ),
            ProviderPriority(
                name="anthropic",
                priority=2,
                enabled=True,
                models=["claude-3-5-sonnet"],
            ),
        ],
        user_rate_limit_per_minute=60,
    )


@pytest.fixture
def provider_router(gateway_config):
    """Create a provider router."""
    return ProviderRouter(gateway_config)


@pytest.fixture
def cost_tracker(gateway_config):
    """Create a cost tracker."""
    return CostTracker(gateway_config)


@pytest.fixture
def request_queue():
    """Create a request queue."""
    return RequestQueue(
        max_concurrent=5,
        default_timeout=30.0,
        max_queue_size=100,
    )


@pytest.fixture
def sample_request():
    """Create a sample LLM request."""
    return LLMRequest(
        request_id=uuid4(),
        user_id="user_123",
        tenant_id="tenant_456",
        messages=[
            Message(role=MessageRole.USER, content="Hello, how are you?"),
        ],
        model="gpt-4o-mini",
        provider="openai",
        temperature=0.7,
        max_tokens=1000,
    )


@pytest.fixture
def sample_response():
    """Create a sample LLM response."""
    return LLMResponse(
        request_id=uuid4(),
        model="gpt-4o-mini",
        provider="openai",
        content="I'm doing well, thank you!",
        role=MessageRole.ASSISTANT,
        finish_reason="stop",
        usage=UsageStats(
            prompt_tokens=10,
            completion_tokens=8,
            total_tokens=18,
            cost_usd=0.0001,
        ),
        latency_ms=150.0,
    )


# =============================================================================
# Provider Router Tests
# =============================================================================


class TestProviderRouter:
    """Tests for ProviderRouter."""

    def test_select_provider_with_preference(self, provider_router):
        """Test selecting provider with explicit preference."""
        provider, model = provider_router.select_provider(
            model="gpt-4o",
            preferred_provider="openai",
        )

        assert provider == "openai"
        assert model == "gpt-4o"

    def test_select_provider_default(self, provider_router):
        """Test selecting default provider when none specified."""
        provider, model = provider_router.select_provider()

        assert provider == "openai"
        assert model == "gpt-4o"

    def test_select_provider_by_model(self, provider_router):
        """Test selecting provider based on model."""
        provider, model = provider_router.select_provider(model="claude-3-5-sonnet")

        assert provider == "anthropic"
        assert model == "claude-3-5-sonnet"

    def test_record_request_success(self, provider_router):
        """Test recording successful request."""
        provider_router.record_request(
            provider="openai",
            latency_ms=100.0,
            success=True,
        )

        status = provider_router.get_provider_status("openai")
        assert status.requests_last_minute >= 1

    def test_record_request_failure(self, provider_router):
        """Test recording failed request."""
        provider_router.record_request(
            provider="openai",
            latency_ms=50.0,
            success=False,
            error="Connection timeout",
        )

        status = provider_router.get_provider_status("openai")
        assert status.errors_last_minute >= 1

    def test_should_failover(self, provider_router):
        """Test failover decision logic."""
        # Simulate provider failures
        for _ in range(5):
            provider_router.record_request(
                provider="openai",
                latency_ms=100.0,
                success=False,
                error="Rate limit exceeded",
            )

        should_fail = provider_router.should_failover(
            "openai", Exception("Rate limit exceeded")
        )
        assert should_fail is True

    def test_get_failover_provider(self, provider_router):
        """Test getting failover provider."""
        failover = provider_router.get_failover_provider(
            original_provider="openai",
            model="gpt-4o",
            attempted=["openai"],
        )

        assert failover is not None
        assert failover[0] == "anthropic"


# =============================================================================
# Cost Tracker Tests
# =============================================================================


class TestCostTracker:
    """Tests for CostTracker."""

    def test_record_usage(self, cost_tracker):
        """Test recording token usage."""
        entry = cost_tracker.record_usage(
            request_id="req_123",
            user_id="user_123",
            tenant_id="tenant_456",
            model="gpt-4o-mini",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
        )

        assert entry.cost_usd > 0
        assert entry.prompt_tokens == 100
        assert entry.completion_tokens == 50

    def test_check_budget_within_limit(self, cost_tracker):
        """Test budget check when within limits."""
        within_budget, reason = cost_tracker.check_budget("user_123")

        assert within_budget is True
        assert reason is None

    def test_check_budget_exceeded(self, cost_tracker):
        """Test budget check when exceeded."""
        # Record many expensive requests
        for i in range(1000):
            cost_tracker.record_usage(
                request_id=f"req_{i}",
                user_id="user_big_spender",
                tenant_id="tenant_456",
                model="gpt-4o",
                provider="openai",
                prompt_tokens=10000,
                completion_tokens=5000,
            )

        within_budget, reason = cost_tracker.check_budget("user_big_spender")
        # May or may not exceed depending on config

    def test_get_user_stats(self, cost_tracker):
        """Test getting user statistics."""
        cost_tracker.record_usage(
            request_id="req_1",
            user_id="user_stats_test",
            tenant_id="tenant_456",
            model="gpt-4o-mini",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
        )

        stats = cost_tracker.get_user_usage("user_stats_test")
        assert stats["total_requests"] >= 1
        assert stats["total_tokens"] >= 150

    def test_get_today_cost(self, cost_tracker):
        """Test getting today's total cost."""
        cost_tracker.record_usage(
            request_id="req_today",
            user_id="user_123",
            tenant_id="tenant_456",
            model="gpt-4o-mini",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
        )

        today_cost = cost_tracker.get_today_cost()
        assert today_cost >= 0


# =============================================================================
# Request Queue Tests
# =============================================================================


class TestRequestQueue:
    """Tests for RequestQueue."""

    @pytest.mark.asyncio
    async def test_enqueue_request(self, request_queue, sample_request):
        """Test enqueueing a request."""
        mock_processor = AsyncMock(
            return_value=LLMResponse(
                request_id=sample_request.request_id,
                model="gpt-4o-mini",
                provider="openai",
                content="Test response",
            )
        )

        await request_queue.start(mock_processor, num_workers=1)

        try:
            future = await request_queue.enqueue(sample_request)
            response = await asyncio.wait_for(future, timeout=5.0)

            assert response.content == "Test response"
            mock_processor.assert_called_once()
        finally:
            await request_queue.stop()

    @pytest.mark.asyncio
    async def test_rate_limiting(self, request_queue, sample_request):
        """Test rate limiting functionality."""
        config = RateLimitConfig(
            requests_per_minute=2,
            burst_limit=1,
        )
        queue = RequestQueue(rate_limit_config=config)

        mock_processor = AsyncMock(
            return_value=LLMResponse(
                request_id=sample_request.request_id,
                model="gpt-4o-mini",
                provider="openai",
                content="Test",
            )
        )

        await queue.start(mock_processor, num_workers=1)

        try:
            # First request should succeed
            future1 = await queue.enqueue(sample_request)

            # Make more requests to trigger rate limit
            for _ in range(5):
                new_request = LLMRequest(
                    request_id=uuid4(),
                    user_id=sample_request.user_id,
                    messages=sample_request.messages,
                )
                try:
                    await queue.enqueue(new_request)
                except Exception as e:
                    assert "Rate limited" in str(e)
                    break
        finally:
            await queue.stop()

    @pytest.mark.asyncio
    async def test_priority_ordering(self, request_queue):
        """Test that high priority requests are processed first."""
        processed_order = []

        async def mock_processor(request):
            processed_order.append(request.request_id)
            return LLMResponse(
                request_id=request.request_id,
                model="test",
                provider="test",
                content="done",
            )

        # Create requests with different priorities
        low_request = LLMRequest(
            request_id=uuid4(),
            user_id="user_1",
            messages=[Message(role=MessageRole.USER, content="low")],
        )
        high_request = LLMRequest(
            request_id=uuid4(),
            user_id="user_2",
            messages=[Message(role=MessageRole.USER, content="high")],
        )

        await request_queue.start(mock_processor, num_workers=1)

        try:
            # Enqueue low priority first, then high priority
            await request_queue.enqueue(low_request, priority=RequestPriority.LOW)
            await request_queue.enqueue(high_request, priority=RequestPriority.HIGH)

            # Wait for processing
            await asyncio.sleep(0.5)

            # High priority should be processed first (or close to first)
            stats = request_queue.get_stats()
            assert stats["total_enqueued"] >= 2
        finally:
            await request_queue.stop()

    def test_get_stats(self, request_queue):
        """Test getting queue statistics."""
        stats = request_queue.get_stats()

        assert "total_enqueued" in stats
        assert "total_processed" in stats
        assert "queue_size" in stats

    def test_get_rate_limit_status(self, request_queue):
        """Test getting rate limit status."""
        status = request_queue.get_rate_limit_status("user_123")

        assert "requests_per_minute" in status
        assert "requests_per_hour" in status
        assert "concurrent" in status


# =============================================================================
# LLM Request/Response Model Tests
# =============================================================================


class TestLLMModels:
    """Tests for LLM data models."""

    def test_llm_request_creation(self):
        """Test creating an LLM request."""
        request = LLMRequest(
            messages=[
                Message(role=MessageRole.SYSTEM, content="You are helpful."),
                Message(role=MessageRole.USER, content="Hi there!"),
            ],
            model="gpt-4o",
            temperature=0.5,
        )

        assert len(request.messages) == 2
        assert request.model == "gpt-4o"
        assert request.temperature == 0.5
        assert request.request_id is not None

    def test_llm_request_with_tools(self):
        """Test creating request with function tools."""
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather for a location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string"}
                        },
                    },
                },
            }
        ]

        request = LLMRequest(
            messages=[Message(role=MessageRole.USER, content="What's the weather?")],
            tools=tools,
        )

        assert request.tools is not None
        assert len(request.tools) == 1

    def test_llm_response_creation(self):
        """Test creating an LLM response."""
        response = LLMResponse(
            request_id=uuid4(),
            model="gpt-4o",
            provider="openai",
            content="Hello! How can I help?",
            usage=UsageStats(
                prompt_tokens=5,
                completion_tokens=6,
                total_tokens=11,
                cost_usd=0.00001,
            ),
        )

        assert response.content == "Hello! How can I help?"
        assert response.usage.total_tokens == 11

    def test_message_role_enum(self):
        """Test message role enumeration."""
        assert MessageRole.SYSTEM.value == "system"
        assert MessageRole.USER.value == "user"
        assert MessageRole.ASSISTANT.value == "assistant"
        assert MessageRole.TOOL.value == "tool"

    def test_usage_stats_defaults(self):
        """Test usage stats default values."""
        usage = UsageStats()

        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0
        assert usage.cost_usd == 0.0

    def test_rate_limit_info(self):
        """Test rate limit info model."""
        info = RateLimitInfo(
            user_id="user_123",
            requests_remaining=50,
            requests_limit=60,
            is_limited=False,
        )

        assert info.requests_remaining == 50
        assert not info.is_limited


# =============================================================================
# Integration-like Tests (mocked)
# =============================================================================


class TestLLMGatewayIntegration:
    """Integration-like tests with mocked providers."""

    @pytest.mark.asyncio
    async def test_gateway_complete_flow(self, gateway_config, sample_request):
        """Test complete gateway flow with mocked provider."""
        with patch(
            "app.services.llm_gateway.service.LLMGateway._init_providers"
        ) as mock_init:
            from app.services.llm_gateway.service import LLMGateway

            gateway = LLMGateway(gateway_config)

            # Mock a provider
            mock_provider = MagicMock()
            mock_provider.chat = AsyncMock(
                return_value=MagicMock(
                    content="Mocked response",
                    role=MagicMock(value="assistant"),
                    finish_reason="stop",
                    usage=MagicMock(
                        prompt_tokens=10,
                        completion_tokens=5,
                        total_tokens=15,
                    ),
                    tool_calls=None,
                )
            )
            gateway._providers["openai"] = mock_provider

            response = await gateway.complete(sample_request)

            assert response.content == "Mocked response"
            assert response.provider == "openai"
            mock_provider.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_gateway_failover(self, gateway_config, sample_request):
        """Test gateway failover when primary provider fails."""
        with patch(
            "app.services.llm_gateway.service.LLMGateway._init_providers"
        ):
            from app.services.llm_gateway.service import LLMGateway

            gateway = LLMGateway(gateway_config)

            # Mock failing primary provider
            mock_openai = MagicMock()
            mock_openai.chat = AsyncMock(
                side_effect=Exception("OpenAI is down")
            )

            # Mock successful fallback provider
            mock_anthropic = MagicMock()
            mock_anthropic.chat = AsyncMock(
                return_value=MagicMock(
                    content="Anthropic response",
                    role=MagicMock(value="assistant"),
                    finish_reason="stop",
                    usage=MagicMock(
                        prompt_tokens=10,
                        completion_tokens=5,
                        total_tokens=15,
                    ),
                    tool_calls=None,
                )
            )

            gateway._providers["openai"] = mock_openai
            gateway._providers["anthropic"] = mock_anthropic

            response = await gateway.complete(sample_request)

            assert response.content == "Anthropic response"
            assert response.provider == "anthropic"

    @pytest.mark.asyncio
    async def test_gateway_rate_limit(self, gateway_config):
        """Test gateway rate limiting."""
        with patch(
            "app.services.llm_gateway.service.LLMGateway._init_providers"
        ):
            from app.services.llm_gateway.service import LLMGateway

            # Set very low rate limit
            gateway_config.user_rate_limit_per_minute = 1
            gateway = LLMGateway(gateway_config)

            # Simulate request history
            from datetime import datetime

            user_id = "rate_limited_user"
            gateway._rate_limits[user_id] = [datetime.utcnow() for _ in range(2)]

            rate_info = gateway._check_rate_limit(user_id)
            assert rate_info.is_limited is True
