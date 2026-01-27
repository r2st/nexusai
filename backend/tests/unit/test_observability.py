"""Unit tests for Observability Services.

Tests for:
- Langfuse trace creation and management
- Span management
- Generation tracking
- Cost calculation
- Prometheus metrics export
- LLM, RAG, and Agent metrics
- ObservabilityService integration
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from uuid import uuid4

import pytest
import pytest_asyncio

from app.services.observability.config import ObservabilityConfig, get_observability_config
from app.services.observability.langfuse_client import (
    LangfuseClient,
    TraceContext,
    SpanContext,
    get_langfuse_client,
    LANGFUSE_AVAILABLE,
)
from app.services.observability.metrics import (
    MetricsCollector,
    LLMMetrics,
    get_metrics_collector,
    PROMETHEUS_AVAILABLE,
)
from app.services.observability.service import (
    ObservabilityService,
    get_observability_service,
    close_observability_service,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def observability_config():
    """Create a test observability config."""
    return ObservabilityConfig(
        langfuse_enabled=True,
        langfuse_public_key="test-public-key",
        langfuse_secret_key="test-secret-key",
        langfuse_host="https://test.langfuse.com",
        prometheus_enabled=True,
        prometheus_port=9090,
        metrics_prefix="nexusai_test",
        track_costs=True,
        cost_alert_threshold=100.0,
        sample_rate=1.0,
    )


@pytest.fixture
def disabled_config():
    """Create a config with observability disabled."""
    return ObservabilityConfig(
        langfuse_enabled=False,
        prometheus_enabled=False,
    )


@pytest.fixture
def langfuse_client(observability_config):
    """Create a Langfuse client for testing."""
    return LangfuseClient(config=observability_config)


@pytest.fixture
def metrics_collector(observability_config):
    """Create a metrics collector for testing."""
    # Disable Prometheus for unit tests (mock it)
    with patch.object(MetricsCollector, '_init_prometheus_metrics'):
        collector = MetricsCollector(config=observability_config)
        collector._enabled = False  # Use local metrics only
        return collector


@pytest.fixture
def sample_llm_metrics():
    """Create sample LLM metrics."""
    return LLMMetrics(
        model="gpt-4o-mini",
        provider="openai",
        operation="chat",
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
        latency_ms=250.0,
        success=True,
        error=None,
        cost_usd=0.00015,
        cached=False,
    )


@pytest.fixture
def sample_trace_context():
    """Create a sample trace context."""
    return TraceContext(
        trace_id=str(uuid4()),
        name="test-trace",
        user_id="user_123",
        session_id="session_456",
        metadata={"env": "test"},
        tags=["test", "unit"],
    )


@pytest.fixture
def sample_span_context(sample_trace_context):
    """Create a sample span context."""
    return SpanContext(
        span_id=str(uuid4()),
        trace_id=sample_trace_context.trace_id,
        name="test-span",
        start_time=datetime.now(timezone.utc),
        metadata={"operation": "test"},
        input_data={"query": "test query"},
    )


# =============================================================================
# ObservabilityConfig Tests
# =============================================================================


class TestObservabilityConfig:
    """Tests for ObservabilityConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ObservabilityConfig()

        assert config.langfuse_enabled is True
        assert config.prometheus_enabled is True
        assert config.metrics_prefix == "nexusai"
        assert config.track_costs is True
        assert config.sample_rate == 1.0

    def test_custom_config(self, observability_config):
        """Test custom configuration values."""
        assert observability_config.langfuse_public_key == "test-public-key"
        assert observability_config.langfuse_secret_key == "test-secret-key"
        assert observability_config.langfuse_host == "https://test.langfuse.com"
        assert observability_config.metrics_prefix == "nexusai_test"

    def test_get_observability_config_from_env(self):
        """Test getting config from environment variables."""
        with patch.dict('os.environ', {
            'LANGFUSE_ENABLED': 'true',
            'LANGFUSE_PUBLIC_KEY': 'env-public-key',
            'LANGFUSE_SECRET_KEY': 'env-secret-key',
            'PROMETHEUS_ENABLED': 'true',
            'TRACE_SAMPLE_RATE': '0.5',
        }):
            config = get_observability_config()

            assert config.langfuse_enabled is True
            assert config.langfuse_public_key == 'env-public-key'
            assert config.sample_rate == 0.5

    def test_disabled_config(self):
        """Test disabled configuration."""
        with patch.dict('os.environ', {
            'LANGFUSE_ENABLED': 'false',
            'PROMETHEUS_ENABLED': 'false',
        }):
            config = get_observability_config()

            assert config.langfuse_enabled is False
            assert config.prometheus_enabled is False


# =============================================================================
# TraceContext and SpanContext Tests
# =============================================================================


class TestTraceContext:
    """Tests for TraceContext dataclass."""

    def test_create_trace_context(self):
        """Test creating a trace context."""
        context = TraceContext(
            trace_id="trace_123",
            name="test-trace",
            user_id="user_456",
            session_id="session_789",
        )

        assert context.trace_id == "trace_123"
        assert context.name == "test-trace"
        assert context.user_id == "user_456"
        assert context.session_id == "session_789"
        assert context.metadata == {}
        assert context.tags == []

    def test_add_tag(self, sample_trace_context):
        """Test adding a tag to trace context."""
        sample_trace_context.add_tag("new-tag")

        assert "new-tag" in sample_trace_context.tags

    def test_add_metadata(self, sample_trace_context):
        """Test adding metadata to trace context."""
        sample_trace_context.add_metadata("key", "value")

        assert sample_trace_context.metadata["key"] == "value"

    def test_trace_context_defaults(self):
        """Test trace context default values."""
        context = TraceContext(
            trace_id="id",
            name="name",
        )

        assert context.user_id is None
        assert context.session_id is None
        assert context.metadata == {}
        assert context.tags == []
        assert context._trace is None
        assert context._spans == []


class TestSpanContext:
    """Tests for SpanContext dataclass."""

    def test_create_span_context(self):
        """Test creating a span context."""
        context = SpanContext(
            span_id="span_123",
            trace_id="trace_456",
            name="test-span",
            start_time=datetime.now(timezone.utc),
        )

        assert context.span_id == "span_123"
        assert context.trace_id == "trace_456"
        assert context.name == "test-span"
        assert context.metadata == {}
        assert context.input_data is None
        assert context.output_data is None

    def test_set_output(self, sample_span_context):
        """Test setting span output."""
        output = {"result": "success", "data": [1, 2, 3]}
        sample_span_context.set_output(output)

        assert sample_span_context.output_data == output

    def test_add_metadata(self, sample_span_context):
        """Test adding metadata to span context."""
        sample_span_context.add_metadata("custom_key", "custom_value")

        assert sample_span_context.metadata["custom_key"] == "custom_value"


# =============================================================================
# LangfuseClient Tests
# =============================================================================


class TestLangfuseClient:
    """Tests for LangfuseClient."""

    @pytest.mark.asyncio
    async def test_initialize_disabled(self, disabled_config):
        """Test initializing with Langfuse disabled."""
        client = LangfuseClient(config=disabled_config)
        await client.initialize()

        assert client._enabled is False
        assert client._client is None

    @pytest.mark.asyncio
    async def test_initialize_without_credentials(self):
        """Test initializing without credentials."""
        config = ObservabilityConfig(
            langfuse_enabled=True,
            langfuse_public_key="",
            langfuse_secret_key="",
        )
        client = LangfuseClient(config=config)
        await client.initialize()

        assert client._enabled is False

    @pytest.mark.asyncio
    async def test_initialize_with_mock_langfuse(self, observability_config):
        """Test initializing with mocked Langfuse."""
        with patch('app.services.observability.langfuse_client.LANGFUSE_AVAILABLE', True):
            with patch('app.services.observability.langfuse_client.Langfuse') as mock_langfuse:
                mock_client = MagicMock()
                mock_langfuse.return_value = mock_client

                client = LangfuseClient(config=observability_config)
                await client.initialize()

                assert client._enabled is True
                mock_langfuse.assert_called_once()

    def test_create_trace(self, langfuse_client):
        """Test creating a trace."""
        trace = langfuse_client.create_trace(
            name="test-trace",
            user_id="user_123",
            session_id="session_456",
            metadata={"test": True},
            tags=["tag1", "tag2"],
        )

        assert trace.name == "test-trace"
        assert trace.user_id == "user_123"
        assert trace.session_id == "session_456"
        assert trace.metadata == {"test": True}
        assert trace.tags == ["tag1", "tag2"]
        assert trace.trace_id is not None
        assert trace.trace_id in langfuse_client._traces

    def test_create_trace_minimal(self, langfuse_client):
        """Test creating a trace with minimal parameters."""
        trace = langfuse_client.create_trace(name="minimal-trace")

        assert trace.name == "minimal-trace"
        assert trace.user_id is None
        assert trace.session_id is None
        assert trace.metadata == {}
        assert trace.tags == []

    def test_start_span(self, langfuse_client):
        """Test starting a span."""
        trace = langfuse_client.create_trace(name="parent-trace")
        span = langfuse_client.start_span(
            trace=trace,
            name="test-span",
            input_data={"query": "test"},
            metadata={"type": "test"},
        )

        assert span.name == "test-span"
        assert span.trace_id == trace.trace_id
        assert span.input_data == {"query": "test"}
        assert span.metadata == {"type": "test"}
        assert span in trace._spans

    def test_end_span(self, langfuse_client):
        """Test ending a span."""
        trace = langfuse_client.create_trace(name="parent-trace")
        span = langfuse_client.start_span(trace=trace, name="test-span")

        langfuse_client.end_span(
            span=span,
            output={"result": "success"},
            status="success",
        )

        assert span.output_data == {"result": "success"}
        # Check that span was recorded in metrics
        assert len(langfuse_client._metrics["spans"]) > 0

    def test_end_span_with_error(self, langfuse_client):
        """Test ending a span with an error."""
        trace = langfuse_client.create_trace(name="parent-trace")
        span = langfuse_client.start_span(trace=trace, name="test-span")

        langfuse_client.end_span(
            span=span,
            status="error",
            error="Test error message",
        )

        # Verify the error was recorded
        span_metrics = langfuse_client._metrics["spans"][-1]
        assert span_metrics["status"] == "error"
        assert span_metrics["error"] == "Test error message"

    def test_log_generation(self, langfuse_client):
        """Test logging an LLM generation."""
        trace = langfuse_client.create_trace(name="llm-trace")

        langfuse_client.log_generation(
            trace=trace,
            name="openai-chat",
            model="gpt-4o-mini",
            input_messages=[{"role": "user", "content": "Hello"}],
            output="Hello! How can I help?",
            usage={"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18},
            model_parameters={"temperature": 0.7},
            latency_ms=150,
        )

        generations = langfuse_client._metrics["generations"]
        assert len(generations) > 0

        gen = generations[-1]
        assert gen["model"] == "gpt-4o-mini"
        assert gen["input_tokens"] == 10
        assert gen["output_tokens"] == 8
        assert gen["total_tokens"] == 18
        assert gen["latency_ms"] == 150

    def test_log_generation_without_usage(self, langfuse_client):
        """Test logging generation without usage stats."""
        trace = langfuse_client.create_trace(name="llm-trace")

        langfuse_client.log_generation(
            trace=trace,
            name="test-gen",
            model="test-model",
            input_messages=[],
            output="test",
            usage=None,
        )

        gen = langfuse_client._metrics["generations"][-1]
        assert gen["input_tokens"] == 0
        assert gen["output_tokens"] == 0
        assert gen["total_tokens"] == 0

    def test_end_trace(self, langfuse_client):
        """Test ending a trace."""
        trace = langfuse_client.create_trace(name="test-trace")
        langfuse_client.end_trace(trace, output="completed", status="success")

        # Find the trace in metrics and verify status
        trace_metrics = next(
            (t for t in langfuse_client._metrics["traces"] if t["trace_id"] == trace.trace_id),
            None
        )
        assert trace_metrics is not None
        assert trace_metrics["status"] == "success"

    def test_end_trace_with_error(self, langfuse_client):
        """Test ending a trace with an error."""
        trace = langfuse_client.create_trace(name="failed-trace")
        langfuse_client.end_trace(
            trace,
            status="error",
            error="Something went wrong",
        )

        trace_metrics = next(
            (t for t in langfuse_client._metrics["traces"] if t["trace_id"] == trace.trace_id),
            None
        )
        assert trace_metrics["status"] == "error"
        assert trace_metrics["error"] == "Something went wrong"

    @pytest.mark.asyncio
    async def test_trace_context_manager_success(self, langfuse_client):
        """Test trace context manager with success."""
        async with langfuse_client.trace(
            name="context-trace",
            user_id="user_123",
        ) as trace:
            trace.add_metadata("key", "value")

        # Verify trace was created and ended
        assert trace.trace_id in langfuse_client._traces
        trace_metrics = next(
            (t for t in langfuse_client._metrics["traces"] if t["trace_id"] == trace.trace_id),
            None
        )
        assert trace_metrics["status"] == "success"

    @pytest.mark.asyncio
    async def test_trace_context_manager_error(self, langfuse_client):
        """Test trace context manager with error."""
        with pytest.raises(ValueError):
            async with langfuse_client.trace(name="error-trace") as trace:
                raise ValueError("Test error")

        trace_metrics = next(
            (t for t in langfuse_client._metrics["traces"] if t["trace_id"] == trace.trace_id),
            None
        )
        assert trace_metrics["status"] == "error"

    @pytest.mark.asyncio
    async def test_span_context_manager_success(self, langfuse_client):
        """Test span context manager with success."""
        trace = langfuse_client.create_trace(name="parent-trace")

        async with langfuse_client.span(trace, "test-span", {"input": "data"}) as span:
            span.set_output({"result": "success"})

        # Verify span was ended
        span_metrics = langfuse_client._metrics["spans"]
        assert len(span_metrics) > 0

    @pytest.mark.asyncio
    async def test_span_context_manager_error(self, langfuse_client):
        """Test span context manager with error."""
        trace = langfuse_client.create_trace(name="parent-trace")

        with pytest.raises(RuntimeError):
            async with langfuse_client.span(trace, "error-span") as span:
                raise RuntimeError("Span error")

        span_metrics = langfuse_client._metrics["spans"][-1]
        assert span_metrics["status"] == "error"

    def test_get_metrics(self, langfuse_client):
        """Test getting metrics summary."""
        # Create some data
        trace = langfuse_client.create_trace(name="metrics-trace")
        langfuse_client.log_generation(
            trace=trace,
            name="test-gen",
            model="gpt-4o",
            input_messages=[],
            output="test",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )

        metrics = langfuse_client.get_metrics()

        assert metrics["traces"] >= 1
        assert metrics["generations"] >= 1
        assert metrics["total_tokens"] >= 150
        assert "recent_traces" in metrics
        assert "recent_generations" in metrics

    def test_flush(self, langfuse_client):
        """Test flushing the client."""
        # Should not raise even without a client
        langfuse_client.flush()

    @pytest.mark.asyncio
    async def test_close(self, langfuse_client):
        """Test closing the client."""
        await langfuse_client.close()
        # Should complete without error


# =============================================================================
# Cost Calculation Tests
# =============================================================================


class TestCostCalculation:
    """Tests for cost calculation in LangfuseClient."""

    def test_calculate_cost_gpt4o(self, langfuse_client):
        """Test cost calculation for GPT-4o."""
        langfuse_client.config.track_costs = True

        cost = langfuse_client._calculate_cost(
            model="gpt-4o",
            usage={"prompt_tokens": 1000, "completion_tokens": 500},
        )

        # GPT-4o: $0.005/1K input, $0.015/1K output
        expected = (1000 / 1000) * 0.005 + (500 / 1000) * 0.015
        assert cost == round(expected, 6)

    def test_calculate_cost_gpt4o_mini(self, langfuse_client):
        """Test cost calculation for GPT-4o-mini."""
        langfuse_client.config.track_costs = True

        cost = langfuse_client._calculate_cost(
            model="gpt-4o-mini",
            usage={"prompt_tokens": 1000, "completion_tokens": 500},
        )

        # GPT-4o-mini: $0.00015/1K input, $0.0006/1K output
        expected = (1000 / 1000) * 0.00015 + (500 / 1000) * 0.0006
        assert cost == round(expected, 6)

    def test_calculate_cost_claude3_opus(self, langfuse_client):
        """Test cost calculation for Claude 3 Opus."""
        langfuse_client.config.track_costs = True

        cost = langfuse_client._calculate_cost(
            model="claude-3-opus",
            usage={"prompt_tokens": 1000, "completion_tokens": 500},
        )

        # Claude 3 Opus: $0.015/1K input, $0.075/1K output
        expected = (1000 / 1000) * 0.015 + (500 / 1000) * 0.075
        assert cost == round(expected, 6)

    def test_calculate_cost_claude3_sonnet(self, langfuse_client):
        """Test cost calculation for Claude 3 Sonnet."""
        langfuse_client.config.track_costs = True

        cost = langfuse_client._calculate_cost(
            model="claude-3-sonnet",
            usage={"prompt_tokens": 1000, "completion_tokens": 500},
        )

        # Claude 3 Sonnet: $0.003/1K input, $0.015/1K output
        expected = (1000 / 1000) * 0.003 + (500 / 1000) * 0.015
        assert cost == round(expected, 6)

    def test_calculate_cost_claude3_haiku(self, langfuse_client):
        """Test cost calculation for Claude 3 Haiku."""
        langfuse_client.config.track_costs = True

        cost = langfuse_client._calculate_cost(
            model="claude-3-haiku",
            usage={"prompt_tokens": 1000, "completion_tokens": 500},
        )

        # Claude 3 Haiku: $0.00025/1K input, $0.00125/1K output
        expected = (1000 / 1000) * 0.00025 + (500 / 1000) * 0.00125
        assert cost == round(expected, 6)

    def test_calculate_cost_gemini_pro(self, langfuse_client):
        """Test cost calculation for Gemini Pro."""
        langfuse_client.config.track_costs = True

        cost = langfuse_client._calculate_cost(
            model="gemini-pro",
            usage={"prompt_tokens": 1000, "completion_tokens": 500},
        )

        # Gemini Pro: $0.00025/1K input, $0.0005/1K output
        expected = (1000 / 1000) * 0.00025 + (500 / 1000) * 0.0005
        assert cost == round(expected, 6)

    def test_calculate_cost_unknown_model(self, langfuse_client):
        """Test cost calculation for unknown model."""
        langfuse_client.config.track_costs = True

        cost = langfuse_client._calculate_cost(
            model="unknown-model-xyz",
            usage={"prompt_tokens": 1000, "completion_tokens": 500},
        )

        assert cost == 0.0

    def test_calculate_cost_zero_tokens(self, langfuse_client):
        """Test cost calculation with zero tokens."""
        langfuse_client.config.track_costs = True

        cost = langfuse_client._calculate_cost(
            model="gpt-4o",
            usage={"prompt_tokens": 0, "completion_tokens": 0},
        )

        assert cost == 0.0


# =============================================================================
# LLMMetrics Tests
# =============================================================================


class TestLLMMetrics:
    """Tests for LLMMetrics dataclass."""

    def test_create_llm_metrics(self, sample_llm_metrics):
        """Test creating LLM metrics."""
        assert sample_llm_metrics.model == "gpt-4o-mini"
        assert sample_llm_metrics.provider == "openai"
        assert sample_llm_metrics.operation == "chat"
        assert sample_llm_metrics.total_tokens == 150
        assert sample_llm_metrics.success is True

    def test_llm_metrics_to_dict(self, sample_llm_metrics):
        """Test converting LLM metrics to dictionary."""
        data = sample_llm_metrics.to_dict()

        assert data["model"] == "gpt-4o-mini"
        assert data["provider"] == "openai"
        assert data["input_tokens"] == 100
        assert data["output_tokens"] == 50
        assert data["total_tokens"] == 150
        assert data["latency_ms"] == 250.0
        assert data["success"] is True
        assert "timestamp" in data

    def test_llm_metrics_defaults(self):
        """Test LLM metrics default values."""
        metrics = LLMMetrics(
            model="test",
            provider="test",
            operation="test",
        )

        assert metrics.input_tokens == 0
        assert metrics.output_tokens == 0
        assert metrics.total_tokens == 0
        assert metrics.latency_ms == 0
        assert metrics.success is True
        assert metrics.error is None
        assert metrics.cost_usd == 0
        assert metrics.cached is False

    def test_llm_metrics_with_error(self):
        """Test LLM metrics with error."""
        metrics = LLMMetrics(
            model="gpt-4o",
            provider="openai",
            operation="chat",
            success=False,
            error="Rate limit exceeded",
        )

        assert metrics.success is False
        assert metrics.error == "Rate limit exceeded"


# =============================================================================
# MetricsCollector Tests
# =============================================================================


class TestMetricsCollector:
    """Tests for MetricsCollector."""

    def test_create_metrics_collector(self, metrics_collector):
        """Test creating a metrics collector."""
        assert metrics_collector is not None
        assert metrics_collector._local_metrics == []

    def test_create_metrics_collector_disabled(self, disabled_config):
        """Test creating a disabled metrics collector."""
        collector = MetricsCollector(config=disabled_config)

        assert collector._enabled is False

    def test_record_llm_request(self, metrics_collector, sample_llm_metrics):
        """Test recording an LLM request."""
        metrics_collector.record_llm_request(sample_llm_metrics)

        assert len(metrics_collector._local_metrics) == 1
        recorded = metrics_collector._local_metrics[0]
        assert recorded["model"] == "gpt-4o-mini"
        assert recorded["total_tokens"] == 150

    def test_record_llm_request_error(self, metrics_collector):
        """Test recording a failed LLM request."""
        metrics = LLMMetrics(
            model="gpt-4o",
            provider="openai",
            operation="chat",
            success=False,
            error="Connection timeout",
            latency_ms=5000,
        )

        metrics_collector.record_llm_request(metrics)

        recorded = metrics_collector._local_metrics[-1]
        assert recorded["success"] is False
        assert recorded["error"] == "Connection timeout"

    def test_record_cache_hit(self, metrics_collector):
        """Test recording a cache hit."""
        # Should not raise even with Prometheus disabled
        metrics_collector.record_cache_hit("llm")

    def test_record_cache_miss(self, metrics_collector):
        """Test recording a cache miss."""
        metrics_collector.record_cache_miss("llm")

    def test_set_cache_entries(self, metrics_collector):
        """Test setting cache entries."""
        metrics_collector.set_cache_entries("llm", 100)

    def test_record_rag_query_success(self, metrics_collector):
        """Test recording a successful RAG query."""
        metrics_collector.record_rag_query(
            success=True,
            documents_retrieved=5,
            latency_ms=150.0,
        )

    def test_record_rag_query_failure(self, metrics_collector):
        """Test recording a failed RAG query."""
        metrics_collector.record_rag_query(
            success=False,
            documents_retrieved=0,
            latency_ms=50.0,
        )

    def test_record_agent_execution_success(self, metrics_collector):
        """Test recording a successful agent execution."""
        metrics_collector.record_agent_execution(
            agent_type="rag_agent",
            success=True,
            execution_time_ms=1000.0,
            tool_calls=["search", "summarize"],
        )

    def test_record_agent_execution_failure(self, metrics_collector):
        """Test recording a failed agent execution."""
        metrics_collector.record_agent_execution(
            agent_type="planning_agent",
            success=False,
            execution_time_ms=500.0,
            tool_calls=None,
        )

    def test_record_http_request(self, metrics_collector):
        """Test recording an HTTP request."""
        metrics_collector.record_http_request(
            method="POST",
            endpoint="/api/v1/chat",
            status=200,
            duration_ms=150.0,
        )

    def test_record_guardrails_check_pass(self, metrics_collector):
        """Test recording a passed guardrails check."""
        metrics_collector.record_guardrails_check(
            check_type="content_safety",
            passed=True,
        )

    def test_record_guardrails_check_fail(self, metrics_collector):
        """Test recording a failed guardrails check."""
        metrics_collector.record_guardrails_check(
            check_type="pii_detection",
            passed=False,
            blocked_reason="PII detected in output",
        )

    def test_set_active_conversations(self, metrics_collector):
        """Test setting active conversation count."""
        metrics_collector.set_active_conversations(42)

    def test_set_active_users(self, metrics_collector):
        """Test setting active user count."""
        metrics_collector.set_active_users(15)

    def test_get_prometheus_metrics_disabled(self, metrics_collector):
        """Test getting Prometheus metrics when disabled."""
        content, content_type = metrics_collector.get_prometheus_metrics()

        assert content == b"# Prometheus not enabled"
        assert content_type == "text/plain"

    def test_get_local_metrics_empty(self):
        """Test getting local metrics when empty."""
        with patch.object(MetricsCollector, '_init_prometheus_metrics'):
            collector = MetricsCollector()
            collector._enabled = False

        metrics = collector.get_local_metrics()

        assert metrics["llm_requests"] == 0
        assert metrics["total_tokens"] == 0
        assert metrics["total_cost_usd"] == 0
        assert metrics["avg_latency_ms"] == 0

    def test_get_local_metrics_with_data(self, metrics_collector, sample_llm_metrics):
        """Test getting local metrics with data."""
        # Add some metrics
        metrics_collector.record_llm_request(sample_llm_metrics)
        metrics_collector.record_llm_request(sample_llm_metrics)

        metrics = metrics_collector.get_local_metrics()

        assert metrics["llm_requests"] == 2
        assert metrics["total_tokens"] == 300
        assert metrics["avg_latency_ms"] == 250.0
        assert "recent_requests" in metrics

    def test_local_metrics_trimming(self, metrics_collector):
        """Test that local metrics are trimmed when exceeding limit."""
        # Add more than 10000 metrics
        for i in range(10100):
            metrics = LLMMetrics(
                model="test",
                provider="test",
                operation="test",
                total_tokens=1,
            )
            metrics_collector.record_llm_request(metrics)

        # After 10001 items, it trims to 5000, then adds 99 more = 5099
        # The trimming happens once when exceeding 10000, not on every add
        assert len(metrics_collector._local_metrics) == 5099


# =============================================================================
# Prometheus Metrics Tests (Mocked)
# =============================================================================


class TestPrometheusMetrics:
    """Tests for Prometheus metrics with mocking."""

    @pytest.fixture
    def prometheus_collector(self, observability_config):
        """Create a collector with mocked Prometheus."""
        with patch('app.services.observability.metrics.PROMETHEUS_AVAILABLE', True):
            with patch('app.services.observability.metrics.Counter') as mock_counter:
                with patch('app.services.observability.metrics.Histogram') as mock_histogram:
                    with patch('app.services.observability.metrics.Gauge') as mock_gauge:
                        mock_counter.return_value = MagicMock()
                        mock_histogram.return_value = MagicMock()
                        mock_gauge.return_value = MagicMock()

                        collector = MetricsCollector(config=observability_config)
                        return collector

    def test_prometheus_metrics_initialized(self, prometheus_collector):
        """Test that Prometheus metrics are initialized."""
        assert prometheus_collector._enabled is True
        assert hasattr(prometheus_collector, 'llm_requests_total')
        assert hasattr(prometheus_collector, 'llm_tokens_total')
        assert hasattr(prometheus_collector, 'llm_latency_seconds')

    def test_prometheus_llm_request_recording(self, prometheus_collector, sample_llm_metrics):
        """Test recording LLM request with Prometheus."""
        prometheus_collector.record_llm_request(sample_llm_metrics)

        # Verify counters were called
        prometheus_collector.llm_requests_total.labels.assert_called()
        prometheus_collector.llm_tokens_total.labels.assert_called()
        prometheus_collector.llm_latency_seconds.labels.assert_called()

    def test_prometheus_cost_recording(self, prometheus_collector):
        """Test recording cost with Prometheus."""
        metrics = LLMMetrics(
            model="gpt-4o",
            provider="openai",
            operation="chat",
            cost_usd=0.05,
        )

        prometheus_collector.record_llm_request(metrics)
        prometheus_collector.llm_cost_usd_total.labels.assert_called()


# =============================================================================
# ObservabilityService Tests
# =============================================================================


class TestObservabilityService:
    """Tests for ObservabilityService."""

    @pytest.fixture
    def observability_service(self, observability_config):
        """Create an observability service for testing."""
        with patch.object(LangfuseClient, '__init__', return_value=None):
            with patch.object(MetricsCollector, '__init__', return_value=None):
                service = ObservabilityService.__new__(ObservabilityService)
                service.config = observability_config
                service.langfuse = MagicMock(spec=LangfuseClient)
                service.metrics = MagicMock(spec=MetricsCollector)
                service._initialized = False
                return service

    @pytest.mark.asyncio
    async def test_initialize(self, observability_service):
        """Test initializing the service."""
        observability_service.langfuse.initialize = AsyncMock()

        await observability_service.initialize()

        assert observability_service._initialized is True
        observability_service.langfuse.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_already_initialized(self, observability_service):
        """Test that initialization is skipped if already done."""
        observability_service._initialized = True
        observability_service.langfuse.initialize = AsyncMock()

        await observability_service.initialize()

        observability_service.langfuse.initialize.assert_not_called()

    @pytest.mark.asyncio
    async def test_close(self, observability_service):
        """Test closing the service."""
        observability_service._initialized = True
        observability_service.langfuse.close = AsyncMock()

        await observability_service.close()

        assert observability_service._initialized is False
        observability_service.langfuse.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_trace_context_manager(self, observability_service):
        """Test trace context manager."""
        mock_trace = MagicMock()
        observability_service.langfuse.trace = MagicMock()
        observability_service.langfuse.trace.return_value.__aenter__ = AsyncMock(return_value=mock_trace)
        observability_service.langfuse.trace.return_value.__aexit__ = AsyncMock()

        async with observability_service.trace(
            name="test",
            user_id="user",
            session_id="session",
        ) as trace:
            pass

        observability_service.langfuse.trace.assert_called_once()

    @pytest.mark.asyncio
    async def test_span_context_manager(self, observability_service):
        """Test span context manager."""
        mock_trace = MagicMock()
        mock_span = MagicMock()
        observability_service.langfuse.span = MagicMock()
        observability_service.langfuse.span.return_value.__aenter__ = AsyncMock(return_value=mock_span)
        observability_service.langfuse.span.return_value.__aexit__ = AsyncMock()

        async with observability_service.span(
            trace=mock_trace,
            name="test-span",
            input_data={"key": "value"},
        ) as span:
            pass

        observability_service.langfuse.span.assert_called_once()

    def test_record_llm_request_with_trace(self, observability_service):
        """Test recording LLM request with trace."""
        mock_trace = MagicMock()

        observability_service.record_llm_request(
            trace=mock_trace,
            model="gpt-4o",
            provider="openai",
            operation="chat",
            input_messages=[{"role": "user", "content": "Hello"}],
            output="Hi there!",
            input_tokens=10,
            output_tokens=5,
            latency_ms=150.0,
            success=True,
            cached=False,
        )

        # Verify Langfuse generation was logged
        observability_service.langfuse.log_generation.assert_called_once()

        # Verify metrics were recorded
        observability_service.metrics.record_llm_request.assert_called_once()
        observability_service.metrics.record_cache_miss.assert_called_once_with("llm")

    def test_record_llm_request_cached(self, observability_service):
        """Test recording cached LLM request."""
        mock_trace = MagicMock()

        observability_service.record_llm_request(
            trace=mock_trace,
            model="gpt-4o",
            provider="openai",
            operation="chat",
            input_messages=[],
            output="cached response",
            cached=True,
        )

        observability_service.metrics.record_cache_hit.assert_called_once_with("llm")

    def test_record_llm_request_without_trace(self, observability_service):
        """Test recording LLM request without trace."""
        observability_service.record_llm_request(
            trace=None,
            model="gpt-4o",
            provider="openai",
            operation="chat",
            input_messages=[],
            output="response",
        )

        # Should not call langfuse
        observability_service.langfuse.log_generation.assert_not_called()
        # Should still record metrics
        observability_service.metrics.record_llm_request.assert_called_once()

    def test_record_rag_query_with_trace(self, observability_service):
        """Test recording RAG query with trace."""
        mock_trace = MagicMock()

        observability_service.record_rag_query(
            trace=mock_trace,
            query="What is AI?",
            documents_retrieved=5,
            latency_ms=200.0,
            success=True,
            reranked=True,
        )

        observability_service.langfuse.start_span.assert_called_once()
        observability_service.metrics.record_rag_query.assert_called_once_with(
            success=True,
            documents_retrieved=5,
            latency_ms=200.0,
        )

    def test_record_rag_query_without_trace(self, observability_service):
        """Test recording RAG query without trace."""
        observability_service.record_rag_query(
            trace=None,
            query="test query",
            documents_retrieved=3,
            latency_ms=100.0,
        )

        observability_service.langfuse.start_span.assert_not_called()
        observability_service.metrics.record_rag_query.assert_called_once()

    def test_record_agent_execution_with_trace(self, observability_service):
        """Test recording agent execution with trace."""
        mock_trace = MagicMock()
        mock_span = MagicMock()
        observability_service.langfuse.start_span.return_value = mock_span

        observability_service.record_agent_execution(
            trace=mock_trace,
            agent_type="rag_agent",
            input_message="Find information about AI",
            output_message="Here is the information...",
            execution_time_ms=2000.0,
            success=True,
            tool_calls=["search", "summarize", "format"],
        )

        observability_service.langfuse.start_span.assert_called_once()
        observability_service.langfuse.end_span.assert_called_once()
        observability_service.metrics.record_agent_execution.assert_called_once()

    def test_record_agent_execution_failure(self, observability_service):
        """Test recording failed agent execution."""
        mock_trace = MagicMock()
        mock_span = MagicMock()
        observability_service.langfuse.start_span.return_value = mock_span

        observability_service.record_agent_execution(
            trace=mock_trace,
            agent_type="planning_agent",
            input_message="Plan a project",
            output_message="",
            execution_time_ms=500.0,
            success=False,
            error="Planning failed due to timeout",
        )

        # Verify error status was passed
        call_args = observability_service.langfuse.end_span.call_args
        assert call_args[1]["status"] == "error"
        assert call_args[1]["error"] == "Planning failed due to timeout"

    def test_record_guardrails_check_with_trace(self, observability_service):
        """Test recording guardrails check with trace."""
        mock_trace = MagicMock()

        observability_service.record_guardrails_check(
            trace=mock_trace,
            check_type="content_safety",
            passed=True,
            details={"score": 0.95},
        )

        mock_trace.add_metadata.assert_called_once()
        observability_service.metrics.record_guardrails_check.assert_called_once()

    def test_record_guardrails_check_blocked(self, observability_service):
        """Test recording blocked guardrails check."""
        mock_trace = MagicMock()

        observability_service.record_guardrails_check(
            trace=mock_trace,
            check_type="pii_detection",
            passed=False,
            blocked_reason="PII found in response",
        )

        observability_service.metrics.record_guardrails_check.assert_called_once_with(
            check_type="pii_detection",
            passed=False,
            blocked_reason="PII found in response",
        )

    def test_record_http_request(self, observability_service):
        """Test recording HTTP request."""
        observability_service.record_http_request(
            method="POST",
            endpoint="/api/v1/chat",
            status=200,
            duration_ms=150.0,
            user_id="user_123",
        )

        observability_service.metrics.record_http_request.assert_called_once_with(
            method="POST",
            endpoint="/api/v1/chat",
            status=200,
            duration_ms=150.0,
        )

    @pytest.mark.asyncio
    async def test_get_dashboard_data(self, observability_service):
        """Test getting dashboard data."""
        observability_service.langfuse.get_metrics.return_value = {
            "traces": 100,
            "generations": 500,
            "total_tokens": 50000,
            "total_cost_usd": 2.50,
        }
        observability_service.metrics.get_local_metrics.return_value = {
            "llm_requests": 500,
            "avg_latency_ms": 200.0,
        }

        data = await observability_service.get_dashboard_data()

        assert "langfuse" in data
        assert "prometheus" in data
        assert "summary" in data
        assert data["summary"]["total_traces"] == 100
        assert data["summary"]["total_generations"] == 500
        assert data["summary"]["llm_requests"] == 500

    def test_get_prometheus_metrics(self, observability_service):
        """Test getting Prometheus metrics."""
        observability_service.metrics.get_prometheus_metrics.return_value = (
            b"# metrics data",
            "text/plain"
        )

        content, content_type = observability_service.get_prometheus_metrics()

        assert content == b"# metrics data"
        observability_service.metrics.get_prometheus_metrics.assert_called_once()

    def test_flush(self, observability_service):
        """Test flushing the service."""
        observability_service.flush()

        observability_service.langfuse.flush.assert_called_once()


# =============================================================================
# Global Service Instance Tests
# =============================================================================


class TestGlobalServiceInstances:
    """Tests for global service instances and factories."""

    @pytest.mark.asyncio
    async def test_get_langfuse_client_creates_instance(self):
        """Test that get_langfuse_client creates and returns an instance."""
        with patch('app.services.observability.langfuse_client._langfuse_client', None):
            with patch.object(LangfuseClient, 'initialize', new_callable=AsyncMock):
                client = await get_langfuse_client()

                assert client is not None
                assert isinstance(client, LangfuseClient)

    def test_get_metrics_collector_creates_instance(self):
        """Test that get_metrics_collector creates and returns an instance."""
        with patch('app.services.observability.metrics._metrics_collector', None):
            with patch.object(MetricsCollector, '_init_prometheus_metrics'):
                collector = get_metrics_collector()

                assert collector is not None
                assert isinstance(collector, MetricsCollector)

    @pytest.mark.asyncio
    async def test_get_observability_service_creates_instance(self):
        """Test that get_observability_service creates and returns an instance."""
        with patch('app.services.observability.service._observability_service', None):
            with patch.object(ObservabilityService, 'initialize', new_callable=AsyncMock):
                with patch.object(LangfuseClient, '__init__', return_value=None):
                    with patch.object(MetricsCollector, '__init__', return_value=None):
                        service = await get_observability_service()

                        assert service is not None
                        assert isinstance(service, ObservabilityService)

    @pytest.mark.asyncio
    async def test_close_observability_service(self):
        """Test closing the global observability service."""
        mock_service = MagicMock(spec=ObservabilityService)
        mock_service.close = AsyncMock()

        with patch('app.services.observability.service._observability_service', mock_service):
            await close_observability_service()

            mock_service.close.assert_called_once()


# =============================================================================
# Edge Cases and Error Handling Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_langfuse_client_exception_handling_create_trace(self, observability_config):
        """Test Langfuse client handles exceptions in create_trace."""
        with patch('app.services.observability.langfuse_client.LANGFUSE_AVAILABLE', True):
            client = LangfuseClient(config=observability_config)
            client._enabled = True
            client._client = MagicMock()
            # In Langfuse v3, create_trace uses start_span with trace_context
            client._client.start_span.side_effect = Exception("API Error")

            # Should not raise, but log error
            trace = client.create_trace(name="test")

            assert trace is not None
            assert trace._trace is None  # Langfuse object not set due to error

    def test_langfuse_client_exception_handling_log_generation(self, langfuse_client):
        """Test Langfuse client handles exceptions in log_generation."""
        trace = langfuse_client.create_trace(name="test")
        trace._trace = MagicMock()
        trace._trace.generation.side_effect = Exception("API Error")
        langfuse_client._enabled = True

        # Should not raise
        langfuse_client.log_generation(
            trace=trace,
            name="test-gen",
            model="test",
            input_messages=[],
            output="test",
        )

        # Generation should still be recorded locally
        assert len(langfuse_client._metrics["generations"]) > 0

    def test_metrics_collector_handles_missing_values(self, metrics_collector):
        """Test metrics collector handles missing/None values."""
        metrics = LLMMetrics(
            model="test",
            provider="test",
            operation="test",
            cost_usd=None,  # type: ignore - testing edge case
        )

        # Should not raise
        metrics_collector.record_llm_request(metrics)

    def test_cost_calculation_with_missing_usage_keys(self, langfuse_client):
        """Test cost calculation with missing usage keys."""
        langfuse_client.config.track_costs = True

        # Missing keys
        cost = langfuse_client._calculate_cost(
            model="gpt-4o",
            usage={},  # Empty usage dict
        )

        assert cost == 0.0

    @pytest.mark.asyncio
    async def test_span_duration_calculation(self, langfuse_client):
        """Test span duration is calculated correctly."""
        trace = langfuse_client.create_trace(name="duration-test")
        span = langfuse_client.start_span(trace, "timed-span")

        # Simulate some work
        await asyncio.sleep(0.1)

        langfuse_client.end_span(span, output="done")

        span_metrics = langfuse_client._metrics["spans"][-1]
        assert span_metrics["duration_ms"] >= 100  # At least 100ms

    def test_observability_service_llm_request_calculates_total_tokens(self):
        """Test that total tokens are calculated correctly."""
        with patch.object(LangfuseClient, '__init__', return_value=None):
            with patch.object(MetricsCollector, '__init__', return_value=None):
                service = ObservabilityService.__new__(ObservabilityService)
                service.config = ObservabilityConfig()
                service.langfuse = MagicMock(spec=LangfuseClient)
                service.metrics = MagicMock(spec=MetricsCollector)

                mock_trace = MagicMock()

                service.record_llm_request(
                    trace=mock_trace,
                    model="gpt-4o",
                    provider="openai",
                    operation="chat",
                    input_messages=[],
                    output="test",
                    input_tokens=100,
                    output_tokens=50,
                )

                # Verify log_generation was called with correct total
                call_args = service.langfuse.log_generation.call_args
                usage = call_args[1]["usage"]
                assert usage["total_tokens"] == 150

    def test_trace_context_span_tracking(self, langfuse_client):
        """Test that spans are tracked in parent trace."""
        trace = langfuse_client.create_trace(name="parent")

        span1 = langfuse_client.start_span(trace, "span1")
        span2 = langfuse_client.start_span(trace, "span2")
        span3 = langfuse_client.start_span(trace, "span3")

        assert len(trace._spans) == 3
        assert span1 in trace._spans
        assert span2 in trace._spans
        assert span3 in trace._spans


# =============================================================================
# Integration-like Tests
# =============================================================================


class TestObservabilityIntegration:
    """Integration-like tests for the observability stack."""

    @pytest.mark.asyncio
    async def test_full_request_tracing_flow(self):
        """Test a complete request tracing flow."""
        # Create service with real LangfuseClient (without patching __init__)
        service = ObservabilityService.__new__(ObservabilityService)
        service.config = ObservabilityConfig()
        service.langfuse = LangfuseClient(config=service.config)
        service.metrics = MagicMock(spec=MetricsCollector)
        service._initialized = True

        # Create a trace
        trace = service.langfuse.create_trace(
            name="chat-request",
            user_id="user_123",
            session_id="session_456",
        )

        # Record RAG retrieval
        service.langfuse.start_span(
            trace=trace,
            name="rag-retrieval",
            input_data={"query": "What is AI?"},
        )

        # Log LLM generation
        service.langfuse.log_generation(
            trace=trace,
            name="openai-chat",
            model="gpt-4o",
            input_messages=[{"role": "user", "content": "What is AI?"}],
            output="AI is artificial intelligence...",
            usage={"prompt_tokens": 50, "completion_tokens": 100, "total_tokens": 150},
        )

        # End trace
        service.langfuse.end_trace(trace, status="success")

        # Verify trace was recorded
        metrics = service.langfuse.get_metrics()
        assert metrics["traces"] >= 1
        assert metrics["generations"] >= 1
        assert metrics["total_tokens"] >= 150

    @pytest.mark.asyncio
    async def test_error_tracing_flow(self):
        """Test error tracing flow."""
        # Create service with real LangfuseClient (without patching __init__)
        service = ObservabilityService.__new__(ObservabilityService)
        service.config = ObservabilityConfig()
        service.langfuse = LangfuseClient(config=service.config)
        service.metrics = MagicMock(spec=MetricsCollector)

        trace = service.langfuse.create_trace(name="error-request")

        # Simulate error during LLM call
        service.langfuse.end_trace(
            trace,
            status="error",
            error="Rate limit exceeded",
        )

        # Verify error was recorded
        trace_data = next(
            (t for t in service.langfuse._metrics["traces"] if t["trace_id"] == trace.trace_id),
            None
        )
        assert trace_data["status"] == "error"
        assert trace_data["error"] == "Rate limit exceeded"


# =============================================================================
# Langfuse v3 API Tests
# =============================================================================


class TestLangfuseV3API:
    """Tests specific to Langfuse v3 API changes."""

    def test_create_trace_uses_start_span_with_trace_context(self, observability_config):
        """Test that create_trace uses start_span with trace_context dict in v3."""
        with patch('app.services.observability.langfuse_client.LANGFUSE_AVAILABLE', True):
            client = LangfuseClient(config=observability_config)
            client._enabled = True
            client._client = MagicMock()
            client._client.create_trace_id.return_value = "trace-123"

            trace = client.create_trace(
                name="test-trace",
                user_id="user-1",
                session_id="session-1",
                metadata={"key": "value"},
                tags=["tag1", "tag2"],
            )

            # Verify start_span was called with trace_context dict
            client._client.start_span.assert_called_once()
            call_kwargs = client._client.start_span.call_args[1]
            assert "trace_context" in call_kwargs
            assert call_kwargs["trace_context"]["trace_id"] == "trace-123"
            assert call_kwargs["name"] == "test-trace"

    def test_start_span_uses_trace_context_with_parent(self, observability_config):
        """Test that start_span includes parent_span_id in trace_context."""
        with patch('app.services.observability.langfuse_client.LANGFUSE_AVAILABLE', True):
            client = LangfuseClient(config=observability_config)
            client._enabled = True
            client._client = MagicMock()

            # Create trace context with mock span
            trace = TraceContext(
                trace_id="trace-123",
                name="test-trace",
            )
            trace._trace = MagicMock()
            trace._trace.id = "root-span-id"

            span = client.start_span(
                trace=trace,
                name="child-span",
                input_data={"input": "test"},
            )

            # Verify start_span was called with parent_span_id
            call_kwargs = client._client.start_span.call_args[1]
            assert call_kwargs["trace_context"]["trace_id"] == "trace-123"
            assert call_kwargs["trace_context"]["parent_span_id"] == "root-span-id"

    def test_log_generation_uses_start_generation_and_end(self, observability_config):
        """Test that log_generation uses start_generation and .end() pattern."""
        with patch('app.services.observability.langfuse_client.LANGFUSE_AVAILABLE', True):
            client = LangfuseClient(config=observability_config)
            client._enabled = True
            client._client = MagicMock()

            trace = TraceContext(trace_id="trace-123", name="test-trace")
            mock_generation = MagicMock()
            client._client.start_generation.return_value = mock_generation

            client.log_generation(
                trace=trace,
                name="llm-call",
                model="gpt-4o",
                input_messages=[{"role": "user", "content": "Hello"}],
                output="Hi there!",
                usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
                model_parameters={"temperature": 0.7},
            )

            # Verify start_generation was called
            client._client.start_generation.assert_called_once()
            call_kwargs = client._client.start_generation.call_args[1]
            assert "trace_context" in call_kwargs
            assert call_kwargs["name"] == "llm-call"
            assert call_kwargs["model"] == "gpt-4o"

            # Verify .end() was called on generation
            mock_generation.end.assert_called_once()
            end_kwargs = mock_generation.end.call_args[1]
            assert end_kwargs["output"] == "Hi there!"
            assert end_kwargs["usage_details"] == {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}

    def test_end_trace_calls_end_on_root_span(self, observability_config):
        """Test that end_trace calls .end() on the root span."""
        with patch('app.services.observability.langfuse_client.LANGFUSE_AVAILABLE', True):
            client = LangfuseClient(config=observability_config)
            client._enabled = True

            trace = TraceContext(trace_id="trace-123", name="test-trace")
            trace._trace = MagicMock()

            client._metrics["traces"].append({
                "trace_id": "trace-123",
                "name": "test-trace",
                "user_id": None,
                "start_time": datetime.now().isoformat(),
            })

            client.end_trace(trace, output={"result": "success"}, status="success")

            # Verify .end() was called on root span
            trace._trace.end.assert_called_once()
            end_kwargs = trace._trace.end.call_args[1]
            assert end_kwargs["output"] == {"result": "success"}

    def test_end_span_calls_end_on_span_object(self, observability_config):
        """Test that end_span calls .end() on the span object."""
        from datetime import UTC
        with patch('app.services.observability.langfuse_client.LANGFUSE_AVAILABLE', True):
            client = LangfuseClient(config=observability_config)
            client._enabled = True

            span = SpanContext(
                span_id="span-123",
                trace_id="trace-123",
                name="test-span",
                start_time=datetime.now(UTC),
            )
            span._span = MagicMock()

            client.end_span(span, output="result data", status="success")

            # Verify .end() was called
            span._span.end.assert_called_once()
            end_kwargs = span._span.end.call_args[1]
            assert end_kwargs["output"] == "result data"

    def test_end_span_with_error_sets_status_message(self, observability_config):
        """Test that end_span passes error as status_message."""
        from datetime import UTC
        with patch('app.services.observability.langfuse_client.LANGFUSE_AVAILABLE', True):
            client = LangfuseClient(config=observability_config)
            client._enabled = True

            span = SpanContext(
                span_id="span-123",
                trace_id="trace-123",
                name="test-span",
                start_time=datetime.now(UTC),
            )
            span._span = MagicMock()

            client.end_span(span, status="error", error="Something went wrong")

            # Verify error was passed as status_message
            end_kwargs = span._span.end.call_args[1]
            assert end_kwargs["status_message"] == "Something went wrong"

    def test_create_trace_id_uses_client_method(self, observability_config):
        """Test that trace ID is created using Langfuse client's create_trace_id method."""
        with patch('app.services.observability.langfuse_client.LANGFUSE_AVAILABLE', True):
            client = LangfuseClient(config=observability_config)
            client._enabled = True
            client._client = MagicMock()
            client._client.create_trace_id.return_value = "langfuse-trace-id-123"

            trace = client.create_trace(name="test")

            # Verify create_trace_id was called
            client._client.create_trace_id.assert_called_once()
            assert trace.trace_id == "langfuse-trace-id-123"

    def test_create_trace_fallback_to_uuid_when_disabled(self, observability_config):
        """Test that trace ID falls back to UUID when Langfuse is disabled."""
        client = LangfuseClient(config=observability_config)
        client._enabled = False

        trace = client.create_trace(name="test")

        # Verify trace_id is a valid UUID
        import uuid
        try:
            uuid.UUID(trace.trace_id)
        except ValueError:
            pytest.fail("trace_id should be a valid UUID when Langfuse is disabled")

    def test_span_context_tracks_in_trace(self, observability_config):
        """Test that spans are tracked in the trace's _spans list."""
        client = LangfuseClient(config=observability_config)
        client._enabled = False

        trace = client.create_trace(name="test-trace")
        span1 = client.start_span(trace, name="span1")
        span2 = client.start_span(trace, name="span2")

        assert len(trace._spans) == 2
        assert trace._spans[0].name == "span1"
        assert trace._spans[1].name == "span2"

    def test_trace_context_add_tag(self):
        """Test TraceContext.add_tag method."""
        trace = TraceContext(trace_id="test", name="test")
        trace.add_tag("important")
        trace.add_tag("production")

        assert "important" in trace.tags
        assert "production" in trace.tags

    def test_trace_context_add_metadata(self):
        """Test TraceContext.add_metadata method."""
        trace = TraceContext(trace_id="test", name="test")
        trace.add_metadata("user_type", "premium")
        trace.add_metadata("region", "us-west")

        assert trace.metadata["user_type"] == "premium"
        assert trace.metadata["region"] == "us-west"

    def test_span_context_set_output(self):
        """Test SpanContext.set_output method."""
        span = SpanContext(
            span_id="span-1",
            trace_id="trace-1",
            name="test",
            start_time=datetime.now(),
        )
        span.set_output({"result": "success"})

        assert span.output_data == {"result": "success"}

    def test_span_context_add_metadata(self):
        """Test SpanContext.add_metadata method."""
        span = SpanContext(
            span_id="span-1",
            trace_id="trace-1",
            name="test",
            start_time=datetime.now(),
        )
        span.add_metadata("step", 1)
        span.add_metadata("status", "processing")

        assert span.metadata["step"] == 1
        assert span.metadata["status"] == "processing"
