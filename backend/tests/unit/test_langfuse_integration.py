"""
Unit tests for Langfuse integration in ChatService.

Tests the observability/tracing functionality added to the chat service.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, UTC


class TestLangfuseClientInitialization:
    """Test Langfuse client initialization."""

    @pytest.mark.asyncio
    async def test_langfuse_client_disabled_by_config(self):
        """Test that Langfuse client is disabled when config says so."""
        from app.services.observability.config import ObservabilityConfig
        from app.services.observability.langfuse_client import LangfuseClient

        config = ObservabilityConfig(langfuse_enabled=False)
        client = LangfuseClient(config=config)
        await client.initialize()

        assert client._enabled is False
        assert client._client is None

    @pytest.mark.asyncio
    async def test_langfuse_client_missing_credentials(self):
        """Test Langfuse client handles missing credentials gracefully."""
        from app.services.observability.config import ObservabilityConfig
        from app.services.observability.langfuse_client import LangfuseClient

        config = ObservabilityConfig(
            langfuse_enabled=True,
            langfuse_public_key="",
            langfuse_secret_key="",
        )
        client = LangfuseClient(config=config)
        await client.initialize()

        assert client._enabled is False


class TestTraceContext:
    """Test trace context creation and management."""

    def test_trace_context_creation(self):
        """Test creating a trace context."""
        from app.services.observability.langfuse_client import TraceContext

        trace = TraceContext(
            trace_id="test-trace-123",
            name="test-trace",
            user_id="user-1",
            session_id="session-1",
        )

        assert trace.trace_id == "test-trace-123"
        assert trace.name == "test-trace"
        assert trace.user_id == "user-1"
        assert trace.session_id == "session-1"
        assert trace.metadata == {}
        assert trace.tags == []

    def test_trace_context_add_metadata(self):
        """Test adding metadata to trace context."""
        from app.services.observability.langfuse_client import TraceContext

        trace = TraceContext(trace_id="test", name="test")
        trace.add_metadata("model", "gpt-4")
        trace.add_metadata("temperature", 0.7)

        assert trace.metadata == {"model": "gpt-4", "temperature": 0.7}

    def test_trace_context_add_tag(self):
        """Test adding tags to trace context."""
        from app.services.observability.langfuse_client import TraceContext

        trace = TraceContext(trace_id="test", name="test")
        trace.add_tag("chat")
        trace.add_tag("streaming")

        assert trace.tags == ["chat", "streaming"]


class TestSpanContext:
    """Test span context creation and management."""

    def test_span_context_creation(self):
        """Test creating a span context."""
        from app.services.observability.langfuse_client import SpanContext

        span = SpanContext(
            span_id="span-123",
            trace_id="trace-123",
            name="tool:devlake_get_pipeline",
            start_time=datetime.now(UTC),
        )

        assert span.span_id == "span-123"
        assert span.trace_id == "trace-123"
        assert span.name == "tool:devlake_get_pipeline"
        assert span.output_data is None

    def test_span_context_set_output(self):
        """Test setting output on span context."""
        from app.services.observability.langfuse_client import SpanContext

        span = SpanContext(
            span_id="span-123",
            trace_id="trace-123",
            name="test-span",
            start_time=datetime.now(UTC),
        )
        span.set_output({"result": "success", "count": 42})

        assert span.output_data == {"result": "success", "count": 42}


class TestLangfuseClientOperations:
    """Test Langfuse client trace and span operations."""

    def test_create_trace_local_tracking(self):
        """Test trace creation with local tracking (when Langfuse is disabled)."""
        from app.services.observability.config import ObservabilityConfig
        from app.services.observability.langfuse_client import LangfuseClient

        config = ObservabilityConfig(langfuse_enabled=False)
        client = LangfuseClient(config=config)

        trace = client.create_trace(
            name="test-trace",
            user_id="user-1",
            metadata={"test": True},
            tags=["unit-test"],
        )

        assert trace.name == "test-trace"
        assert trace.user_id == "user-1"
        assert trace.metadata == {"test": True}
        assert trace.tags == ["unit-test"]
        assert trace.trace_id in client._traces

    def test_start_span_local_tracking(self):
        """Test span creation with local tracking."""
        from app.services.observability.config import ObservabilityConfig
        from app.services.observability.langfuse_client import LangfuseClient

        config = ObservabilityConfig(langfuse_enabled=False)
        client = LangfuseClient(config=config)

        trace = client.create_trace(name="test-trace")
        span = client.start_span(
            trace=trace,
            name="test-span",
            input_data={"query": "test"},
        )

        assert span.name == "test-span"
        assert span.trace_id == trace.trace_id
        assert span.input_data == {"query": "test"}
        assert span in trace._spans

    def test_end_span_local_tracking(self):
        """Test ending a span with local tracking."""
        from app.services.observability.config import ObservabilityConfig
        from app.services.observability.langfuse_client import LangfuseClient

        config = ObservabilityConfig(langfuse_enabled=False)
        client = LangfuseClient(config=config)

        trace = client.create_trace(name="test-trace")
        span = client.start_span(trace=trace, name="test-span")
        client.end_span(span, output={"result": "ok"}, status="success")

        assert span.output_data == {"result": "ok"}
        # Check metrics were recorded
        assert len(client._metrics["spans"]) == 1
        assert client._metrics["spans"][0]["status"] == "success"

    def test_log_generation(self):
        """Test logging an LLM generation."""
        from app.services.observability.config import ObservabilityConfig
        from app.services.observability.langfuse_client import LangfuseClient

        config = ObservabilityConfig(langfuse_enabled=False, track_costs=True)
        client = LangfuseClient(config=config)

        trace = client.create_trace(name="test-trace")
        client.log_generation(
            trace=trace,
            name="chat-completion",
            model="gpt-4o",
            input_messages=[{"role": "user", "content": "Hello"}],
            output="Hello! How can I help you?",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            latency_ms=150,
        )

        assert len(client._metrics["generations"]) == 1
        gen = client._metrics["generations"][0]
        assert gen["model"] == "gpt-4o"
        assert gen["input_tokens"] == 10
        assert gen["output_tokens"] == 20
        assert gen["latency_ms"] == 150

    def test_end_trace(self):
        """Test ending a trace."""
        from app.services.observability.config import ObservabilityConfig
        from app.services.observability.langfuse_client import LangfuseClient

        config = ObservabilityConfig(langfuse_enabled=False)
        client = LangfuseClient(config=config)

        trace = client.create_trace(name="test-trace")
        client.end_trace(trace, status="success")

        # Find the trace in metrics and verify status
        trace_metrics = [t for t in client._metrics["traces"] if t["trace_id"] == trace.trace_id]
        assert len(trace_metrics) == 1
        assert trace_metrics[0]["status"] == "success"

    def test_end_trace_with_error(self):
        """Test ending a trace with error."""
        from app.services.observability.config import ObservabilityConfig
        from app.services.observability.langfuse_client import LangfuseClient

        config = ObservabilityConfig(langfuse_enabled=False)
        client = LangfuseClient(config=config)

        trace = client.create_trace(name="test-trace")
        client.end_trace(trace, status="error", error="Something went wrong")

        trace_metrics = [t for t in client._metrics["traces"] if t["trace_id"] == trace.trace_id]
        assert len(trace_metrics) == 1
        assert trace_metrics[0]["status"] == "error"
        assert trace_metrics[0]["error"] == "Something went wrong"


class TestCostCalculation:
    """Test cost calculation for different models."""

    def test_calculate_cost_gpt4o(self):
        """Test cost calculation for GPT-4o."""
        from app.services.observability.config import ObservabilityConfig
        from app.services.observability.langfuse_client import LangfuseClient

        config = ObservabilityConfig(track_costs=True)
        client = LangfuseClient(config=config)

        usage = {"prompt_tokens": 1000, "completion_tokens": 500}
        cost = client._calculate_cost("gpt-4o", usage)

        # GPT-4o: $0.005/1K input, $0.015/1K output
        expected = (1000 / 1000 * 0.005) + (500 / 1000 * 0.015)
        assert abs(cost - expected) < 0.0001

    def test_calculate_cost_claude(self):
        """Test cost calculation for Claude model."""
        from app.services.observability.config import ObservabilityConfig
        from app.services.observability.langfuse_client import LangfuseClient

        config = ObservabilityConfig(track_costs=True)
        client = LangfuseClient(config=config)

        usage = {"prompt_tokens": 1000, "completion_tokens": 500}
        cost = client._calculate_cost("claude-3-sonnet", usage)

        # Claude 3 Sonnet: $0.003/1K input, $0.015/1K output
        expected = (1000 / 1000 * 0.003) + (500 / 1000 * 0.015)
        assert abs(cost - expected) < 0.0001

    def test_calculate_cost_unknown_model(self):
        """Test cost calculation for unknown model returns 0."""
        from app.services.observability.config import ObservabilityConfig
        from app.services.observability.langfuse_client import LangfuseClient

        config = ObservabilityConfig(track_costs=True)
        client = LangfuseClient(config=config)

        usage = {"prompt_tokens": 1000, "completion_tokens": 500}
        cost = client._calculate_cost("unknown-model-xyz", usage)

        assert cost == 0.0


class TestObservabilityService:
    """Test the unified observability service."""

    @pytest.mark.asyncio
    async def test_service_initialization(self):
        """Test observability service initialization."""
        from app.services.observability.config import ObservabilityConfig
        from app.services.observability.service import ObservabilityService

        config = ObservabilityConfig(langfuse_enabled=False, prometheus_enabled=False)
        service = ObservabilityService(config=config)
        await service.initialize()

        assert service._initialized is True

    def test_record_llm_request(self):
        """Test recording an LLM request via langfuse client directly."""
        from app.services.observability.config import ObservabilityConfig
        from app.services.observability.langfuse_client import LangfuseClient

        # Test with LangfuseClient directly to avoid Prometheus registry collision
        config = ObservabilityConfig(langfuse_enabled=False)
        langfuse = LangfuseClient(config=config)

        trace = langfuse.create_trace(name="test")
        langfuse.log_generation(
            trace=trace,
            name="openai-chat",
            model="gpt-4o",
            input_messages=[{"role": "user", "content": "Hello"}],
            output="Hi there!",
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            latency_ms=100,
        )

        # Verify generation was logged
        assert len(langfuse._metrics["generations"]) == 1
        gen = langfuse._metrics["generations"][0]
        assert gen["model"] == "gpt-4o"
        assert gen["input_tokens"] == 10


class TestChatServiceObservabilityIntegration:
    """Test ChatService integration with observability."""

    @pytest.mark.asyncio
    async def test_chat_service_initializes_observability(self):
        """Test that ChatService initializes observability service."""
        from unittest.mock import patch, AsyncMock

        with patch("app.services.chat.get_observability_service") as mock_get_obs:
            mock_obs_service = MagicMock()
            mock_get_obs.return_value = mock_obs_service

            # Import after patching
            from app.services.chat import ChatService

            # Create a mock db session
            mock_db = AsyncMock()

            service = ChatService(db=mock_db, user_id="test-user")
            await service.initialize_mcp()

            # Verify observability was initialized
            mock_get_obs.assert_called_once()
            assert service._observability is not None


class TestGetMetrics:
    """Test metrics retrieval."""

    def test_get_metrics_summary(self):
        """Test getting metrics summary."""
        from app.services.observability.config import ObservabilityConfig
        from app.services.observability.langfuse_client import LangfuseClient

        config = ObservabilityConfig(langfuse_enabled=False, track_costs=True)
        client = LangfuseClient(config=config)

        # Create some traces and generations
        trace1 = client.create_trace(name="trace-1")
        trace2 = client.create_trace(name="trace-2")

        client.log_generation(
            trace=trace1,
            name="gen-1",
            model="gpt-4o",
            input_messages=[],
            output="response",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )

        metrics = client.get_metrics()

        assert metrics["traces"] == 2
        assert metrics["generations"] == 1
        assert metrics["total_tokens"] == 150
