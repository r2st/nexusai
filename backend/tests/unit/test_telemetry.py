"""
Unit tests for OpenTelemetry integration module.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from app.core.telemetry import (
    TelemetryService,
    NoOpTracer,
    NoOpMeter,
    NoOpSpan,
    NoOpMetric,
    telemetry,
    traced,
    AppMetrics,
    app_metrics,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def telemetry_service():
    """Create a fresh TelemetryService instance."""
    return TelemetryService()


@pytest.fixture
def app_metrics_instance():
    """Create a fresh AppMetrics instance."""
    return AppMetrics()


# =============================================================================
# TelemetryService Initialization Tests
# =============================================================================


class TestTelemetryServiceInit:
    """Tests for TelemetryService initialization."""

    def test_initial_state(self, telemetry_service):
        """Test initial state of telemetry service."""
        assert telemetry_service._initialized is False
        assert telemetry_service._tracer is None
        assert telemetry_service._meter is None

    def test_initialize_when_disabled(self, telemetry_service):
        """Test initialization when OTEL is disabled."""
        with patch("app.core.telemetry.settings") as mock_settings:
            mock_settings.OTEL_ENABLED = False

            telemetry_service.initialize()

            assert telemetry_service._initialized is False

    def test_initialize_idempotent(self, telemetry_service):
        """Test that initialization is idempotent."""
        telemetry_service._initialized = True

        with patch("app.core.telemetry.settings") as mock_settings:
            mock_settings.OTEL_ENABLED = True

            # Should return early
            telemetry_service.initialize()

            # Should still be True, not re-initialized
            assert telemetry_service._initialized is True


# =============================================================================
# TelemetryService Property Tests
# =============================================================================


class TestTelemetryServiceProperties:
    """Tests for TelemetryService properties."""

    def test_tracer_returns_noop_when_disabled(self, telemetry_service):
        """Test tracer property returns NoOp when OTEL disabled."""
        with patch("app.core.telemetry.settings") as mock_settings:
            mock_settings.OTEL_ENABLED = False

            tracer = telemetry_service.tracer

            assert isinstance(tracer, NoOpTracer)

    def test_meter_returns_noop_when_disabled(self, telemetry_service):
        """Test meter property returns NoOp when OTEL disabled."""
        with patch("app.core.telemetry.settings") as mock_settings:
            mock_settings.OTEL_ENABLED = False

            meter = telemetry_service.meter

            assert isinstance(meter, NoOpMeter)

    def test_create_span_returns_noop_when_disabled(self, telemetry_service):
        """Test create_span returns NoOp when OTEL disabled."""
        with patch("app.core.telemetry.settings") as mock_settings:
            mock_settings.OTEL_ENABLED = False

            span = telemetry_service.create_span("test_span")

            assert isinstance(span, NoOpSpan)


# =============================================================================
# TelemetryService Metric Creation Tests
# =============================================================================


class TestTelemetryServiceMetrics:
    """Tests for TelemetryService metric creation."""

    def test_create_counter(self, telemetry_service):
        """Test creating a counter metric."""
        mock_meter = MagicMock()
        mock_counter = MagicMock()
        mock_meter.create_counter.return_value = mock_counter
        telemetry_service._meter = mock_meter

        with patch("app.core.telemetry.settings") as mock_settings:
            mock_settings.OTEL_ENABLED = True

            counter = telemetry_service.create_counter(
                name="test_counter",
                description="Test counter",
                unit="1",
            )

            mock_meter.create_counter.assert_called_once_with(
                name="test_counter",
                description="Test counter",
                unit="1",
            )

    def test_create_histogram(self, telemetry_service):
        """Test creating a histogram metric."""
        mock_meter = MagicMock()
        mock_histogram = MagicMock()
        mock_meter.create_histogram.return_value = mock_histogram
        telemetry_service._meter = mock_meter

        with patch("app.core.telemetry.settings") as mock_settings:
            mock_settings.OTEL_ENABLED = True

            histogram = telemetry_service.create_histogram(
                name="test_histogram",
                description="Test histogram",
                unit="ms",
            )

            mock_meter.create_histogram.assert_called_once()

    def test_create_gauge(self, telemetry_service):
        """Test creating a gauge metric."""
        mock_meter = MagicMock()
        mock_gauge = MagicMock()
        mock_meter.create_observable_gauge.return_value = mock_gauge
        telemetry_service._meter = mock_meter

        with patch("app.core.telemetry.settings") as mock_settings:
            mock_settings.OTEL_ENABLED = True

            gauge = telemetry_service.create_gauge(
                name="test_gauge",
                description="Test gauge",
            )

            mock_meter.create_observable_gauge.assert_called_once()


# =============================================================================
# NoOpTracer Tests
# =============================================================================


class TestNoOpTracer:
    """Tests for NoOpTracer class."""

    def test_start_as_current_span_returns_noop_span(self):
        """Test that start_as_current_span returns NoOpSpan."""
        tracer = NoOpTracer()

        span = tracer.start_as_current_span("test")

        assert isinstance(span, NoOpSpan)

    def test_start_as_current_span_with_kwargs(self):
        """Test start_as_current_span accepts kwargs."""
        tracer = NoOpTracer()

        # Should not raise
        span = tracer.start_as_current_span(
            "test",
            attributes={"key": "value"},
        )

        assert isinstance(span, NoOpSpan)


# =============================================================================
# NoOpMeter Tests
# =============================================================================


class TestNoOpMeter:
    """Tests for NoOpMeter class."""

    def test_create_counter_returns_noop_metric(self):
        """Test that create_counter returns NoOpMetric."""
        meter = NoOpMeter()

        metric = meter.create_counter(name="test")

        assert isinstance(metric, NoOpMetric)

    def test_create_histogram_returns_noop_metric(self):
        """Test that create_histogram returns NoOpMetric."""
        meter = NoOpMeter()

        metric = meter.create_histogram(name="test")

        assert isinstance(metric, NoOpMetric)

    def test_create_observable_gauge_returns_noop_metric(self):
        """Test that create_observable_gauge returns NoOpMetric."""
        meter = NoOpMeter()

        metric = meter.create_observable_gauge(name="test")

        assert isinstance(metric, NoOpMetric)


# =============================================================================
# NoOpSpan Tests
# =============================================================================


class TestNoOpSpan:
    """Tests for NoOpSpan class."""

    def test_context_manager(self):
        """Test NoOpSpan as context manager."""
        span = NoOpSpan()

        with span as s:
            assert s is span

    def test_set_attribute(self):
        """Test set_attribute does nothing."""
        span = NoOpSpan()

        # Should not raise
        span.set_attribute("key", "value")

    def test_set_status(self):
        """Test set_status does nothing."""
        span = NoOpSpan()

        # Should not raise
        span.set_status("OK")

    def test_add_event(self):
        """Test add_event does nothing."""
        span = NoOpSpan()

        # Should not raise
        span.add_event("event", {"key": "value"})

    def test_record_exception(self):
        """Test record_exception does nothing."""
        span = NoOpSpan()

        # Should not raise
        span.record_exception(ValueError("test"))


# =============================================================================
# NoOpMetric Tests
# =============================================================================


class TestNoOpMetric:
    """Tests for NoOpMetric class."""

    def test_add(self):
        """Test add does nothing."""
        metric = NoOpMetric()

        # Should not raise
        metric.add(1, {"key": "value"})

    def test_record(self):
        """Test record does nothing."""
        metric = NoOpMetric()

        # Should not raise
        metric.record(1.5, {"key": "value"})


# =============================================================================
# traced Decorator Tests
# =============================================================================


class TestTracedDecorator:
    """Tests for traced decorator."""

    @pytest.mark.asyncio
    async def test_traced_async_function(self):
        """Test traced decorator on async function."""
        with patch("app.core.telemetry.settings") as mock_settings:
            mock_settings.OTEL_ENABLED = False

            @traced("test_operation")
            async def async_func():
                return "result"

            result = await async_func()

            assert result == "result"

    def test_traced_sync_function(self):
        """Test traced decorator on sync function."""
        with patch("app.core.telemetry.settings") as mock_settings:
            mock_settings.OTEL_ENABLED = False

            @traced("test_operation")
            def sync_func():
                return "result"

            result = sync_func()

            assert result == "result"

    @pytest.mark.asyncio
    async def test_traced_async_with_attributes(self):
        """Test traced decorator with attributes on async function."""
        with patch("app.core.telemetry.settings") as mock_settings:
            mock_settings.OTEL_ENABLED = False

            @traced("operation", attributes={"key": "value"})
            async def async_func(x):
                return x * 2

            result = await async_func(5)

            assert result == 10

    def test_traced_default_name(self):
        """Test traced decorator uses default name from function."""
        with patch("app.core.telemetry.settings") as mock_settings:
            mock_settings.OTEL_ENABLED = False

            @traced()
            def my_function():
                return "result"

            result = my_function()

            assert result == "result"

    @pytest.mark.asyncio
    async def test_traced_async_exception_handling(self):
        """Test traced decorator handles async exceptions."""
        with patch("app.core.telemetry.settings") as mock_settings:
            mock_settings.OTEL_ENABLED = False

            @traced("failing_operation")
            async def failing_func():
                raise ValueError("test error")

            with pytest.raises(ValueError):
                await failing_func()

    def test_traced_sync_exception_handling(self):
        """Test traced decorator handles sync exceptions."""
        with patch("app.core.telemetry.settings") as mock_settings:
            mock_settings.OTEL_ENABLED = False

            @traced("failing_operation")
            def failing_func():
                raise ValueError("test error")

            with pytest.raises(ValueError):
                failing_func()

    @pytest.mark.asyncio
    async def test_traced_preserves_function_metadata(self):
        """Test traced decorator preserves function metadata."""
        with patch("app.core.telemetry.settings") as mock_settings:
            mock_settings.OTEL_ENABLED = False

            @traced()
            async def documented_function():
                """This is a docstring."""
                return "result"

            assert documented_function.__name__ == "documented_function"
            assert "docstring" in documented_function.__doc__


# =============================================================================
# AppMetrics Tests
# =============================================================================


class TestAppMetrics:
    """Tests for AppMetrics class."""

    def test_initial_state(self, app_metrics_instance):
        """Test initial state of AppMetrics."""
        assert app_metrics_instance._initialized is False
        assert app_metrics_instance._request_counter is None
        assert app_metrics_instance._request_duration is None

    def test_initialize_when_disabled(self, app_metrics_instance):
        """Test initialization when OTEL is disabled."""
        with patch("app.core.telemetry.settings") as mock_settings:
            mock_settings.OTEL_ENABLED = False

            app_metrics_instance.initialize()

            assert app_metrics_instance._initialized is False

    def test_initialize_idempotent(self, app_metrics_instance):
        """Test that initialization is idempotent."""
        app_metrics_instance._initialized = True

        # Should return early
        app_metrics_instance.initialize()

        # Counters should still be None (not re-initialized)
        assert app_metrics_instance._request_counter is None

    def test_record_request_when_not_initialized(self, app_metrics_instance):
        """Test record_request does nothing when not initialized."""
        # Should not raise
        app_metrics_instance.record_request(
            method="GET",
            path="/api/test",
            status_code=200,
            duration_ms=50.0,
        )

    def test_record_ai_request_when_not_initialized(self, app_metrics_instance):
        """Test record_ai_request does nothing when not initialized."""
        # Should not raise
        app_metrics_instance.record_ai_request(
            provider="openai",
            model="gpt-4",
            tokens=100,
            duration_ms=1000.0,
        )

    def test_record_request_when_initialized(self, app_metrics_instance):
        """Test record_request records metrics when initialized."""
        mock_counter = MagicMock()
        mock_histogram = MagicMock()

        app_metrics_instance._initialized = True
        app_metrics_instance._request_counter = mock_counter
        app_metrics_instance._request_duration = mock_histogram

        app_metrics_instance.record_request(
            method="POST",
            path="/api/users",
            status_code=201,
            duration_ms=75.5,
        )

        mock_counter.add.assert_called_once()
        mock_histogram.record.assert_called_once_with(
            75.5,
            {"method": "POST", "path": "/api/users", "status_code": 201},
        )

    def test_record_ai_request_when_initialized(self, app_metrics_instance):
        """Test record_ai_request records metrics when initialized."""
        mock_requests = MagicMock()
        mock_tokens = MagicMock()

        app_metrics_instance._initialized = True
        app_metrics_instance._ai_requests = mock_requests
        app_metrics_instance._ai_tokens = mock_tokens

        app_metrics_instance.record_ai_request(
            provider="anthropic",
            model="claude-3",
            tokens=500,
            duration_ms=2000.0,
        )

        mock_requests.add.assert_called_once_with(
            1,
            {"provider": "anthropic", "model": "claude-3"},
        )
        mock_tokens.add.assert_called_once_with(
            500,
            {"provider": "anthropic", "model": "claude-3"},
        )


# =============================================================================
# Singleton Instance Tests
# =============================================================================


class TestSingletonInstances:
    """Tests for singleton instances."""

    def test_telemetry_singleton_exists(self):
        """Test telemetry singleton is available."""
        assert telemetry is not None
        assert isinstance(telemetry, TelemetryService)

    def test_app_metrics_singleton_exists(self):
        """Test app_metrics singleton is available."""
        assert app_metrics is not None
        assert isinstance(app_metrics, AppMetrics)


# =============================================================================
# Integration-style Tests
# =============================================================================


class TestTelemetryIntegration:
    """Integration-style tests for telemetry module."""

    @pytest.mark.asyncio
    async def test_traced_function_with_span(self):
        """Test traced function creates span context."""
        execution_count = 0

        with patch("app.core.telemetry.settings") as mock_settings:
            mock_settings.OTEL_ENABLED = False

            @traced("integration_test")
            async def test_operation():
                nonlocal execution_count
                execution_count += 1
                return "done"

            result = await test_operation()

            assert result == "done"
            assert execution_count == 1

    def test_noop_span_as_context_manager_full_flow(self):
        """Test NoOpSpan full context manager flow."""
        span = NoOpSpan()

        with span as s:
            s.set_attribute("key1", "value1")
            s.set_attribute("key2", 123)
            s.add_event("event1", {"detail": "info"})
            s.set_status("OK")

        # Should complete without errors

    def test_noop_metric_operations(self):
        """Test NoOpMetric all operations."""
        metric = NoOpMetric()

        metric.add(1)
        metric.add(5, {"label": "test"})
        metric.record(1.5)
        metric.record(2.5, {"label": "test"})

        # Should complete without errors

    def test_telemetry_service_span_context_manager(self, telemetry_service):
        """Test TelemetryService create_span as context manager."""
        with patch("app.core.telemetry.settings") as mock_settings:
            mock_settings.OTEL_ENABLED = False

            with telemetry_service.create_span("test_span", {"key": "value"}) as span:
                span.set_attribute("result", "success")

        # Should complete without errors


# =============================================================================
# Edge Cases Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""

    def test_noop_span_record_exception_with_various_types(self):
        """Test recording different exception types."""
        span = NoOpSpan()

        span.record_exception(ValueError("value error"))
        span.record_exception(TypeError("type error"))
        span.record_exception(RuntimeError("runtime error"))
        span.record_exception(Exception("generic error"))

    def test_noop_span_add_event_with_none_attributes(self):
        """Test add_event with None attributes."""
        span = NoOpSpan()

        span.add_event("event", None)

    @pytest.mark.asyncio
    async def test_traced_async_with_args_and_kwargs(self):
        """Test traced async function with various arguments."""
        with patch("app.core.telemetry.settings") as mock_settings:
            mock_settings.OTEL_ENABLED = False

            @traced()
            async def complex_func(a, b, c=10, d=20):
                return a + b + c + d

            result = await complex_func(1, 2, c=3, d=4)

            assert result == 10

    def test_traced_sync_with_args_and_kwargs(self):
        """Test traced sync function with various arguments."""
        with patch("app.core.telemetry.settings") as mock_settings:
            mock_settings.OTEL_ENABLED = False

            @traced()
            def complex_func(a, b, *args, **kwargs):
                return a + b + sum(args) + sum(kwargs.values())

            result = complex_func(1, 2, 3, 4, x=5, y=6)

            assert result == 21

    def test_app_metrics_record_with_edge_values(self, app_metrics_instance):
        """Test AppMetrics with edge case values."""
        mock_counter = MagicMock()
        mock_histogram = MagicMock()

        app_metrics_instance._initialized = True
        app_metrics_instance._request_counter = mock_counter
        app_metrics_instance._request_duration = mock_histogram

        # Very small duration
        app_metrics_instance.record_request("GET", "/", 200, 0.001)

        # Very large duration
        app_metrics_instance.record_request("GET", "/slow", 200, 99999.9)

        # Edge status codes
        app_metrics_instance.record_request("GET", "/", 100, 10.0)
        app_metrics_instance.record_request("GET", "/", 599, 10.0)

        assert mock_counter.add.call_count == 4
        assert mock_histogram.record.call_count == 4
