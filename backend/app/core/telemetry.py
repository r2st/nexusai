"""OpenTelemetry integration for observability.

Provides:
- Distributed tracing
- Metrics collection
- Log correlation
- Performance monitoring
"""

import logging
from functools import wraps
from typing import Any, Callable

from app.core.config import settings

# Only import OpenTelemetry if enabled
if settings.OTEL_ENABLED:
    from opentelemetry import trace, metrics
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
    from opentelemetry.trace import Status, StatusCode
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator


logger = logging.getLogger(__name__)


class TelemetryService:
    """Service for managing OpenTelemetry instrumentation."""

    def __init__(self):
        self._initialized = False
        self._tracer = None
        self._meter = None

    def initialize(self, app=None) -> None:
        """Initialize OpenTelemetry instrumentation.

        Args:
            app: Optional FastAPI application to instrument
        """
        if not settings.OTEL_ENABLED:
            logger.info("OpenTelemetry is disabled")
            return

        if self._initialized:
            logger.warning("OpenTelemetry already initialized")
            return

        try:
            # Create resource with service info
            resource = Resource.create({
                SERVICE_NAME: settings.OTEL_SERVICE_NAME,
                SERVICE_VERSION: settings.APP_VERSION,
                "deployment.environment": settings.ENVIRONMENT,
            })

            # Initialize tracing
            self._init_tracing(resource)

            # Initialize metrics
            self._init_metrics(resource)

            # Instrument libraries
            self._instrument_libraries(app)

            self._initialized = True
            logger.info("OpenTelemetry initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize OpenTelemetry: {e}")

    def _init_tracing(self, resource: "Resource") -> None:
        """Initialize distributed tracing."""
        # Create OTLP exporter
        exporter = OTLPSpanExporter(
            endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
            insecure=True,  # Use TLS in production
        )

        # Create tracer provider
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(exporter))

        # Set global tracer provider
        trace.set_tracer_provider(provider)

        # Get tracer for this service
        self._tracer = trace.get_tracer(
            settings.OTEL_SERVICE_NAME,
            settings.APP_VERSION,
        )

    def _init_metrics(self, resource: "Resource") -> None:
        """Initialize metrics collection."""
        # Create OTLP metric exporter
        exporter = OTLPMetricExporter(
            endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
            insecure=True,
        )

        # Create metric reader
        reader = PeriodicExportingMetricReader(
            exporter,
            export_interval_millis=60000,  # Export every minute
        )

        # Create meter provider
        provider = MeterProvider(
            resource=resource,
            metric_readers=[reader],
        )

        # Set global meter provider
        metrics.set_meter_provider(provider)

        # Get meter for this service
        self._meter = metrics.get_meter(
            settings.OTEL_SERVICE_NAME,
            settings.APP_VERSION,
        )

    def _instrument_libraries(self, app=None) -> None:
        """Instrument common libraries."""
        # FastAPI
        if app:
            FastAPIInstrumentor.instrument_app(app)

        # HTTPX (for external API calls)
        HTTPXClientInstrumentor().instrument()

        # SQLAlchemy (database)
        SQLAlchemyInstrumentor().instrument()

        # Redis
        RedisInstrumentor().instrument()

    @property
    def tracer(self):
        """Get the tracer instance."""
        if not settings.OTEL_ENABLED:
            return NoOpTracer()
        return self._tracer or trace.get_tracer(settings.OTEL_SERVICE_NAME)

    @property
    def meter(self):
        """Get the meter instance."""
        if not settings.OTEL_ENABLED:
            return NoOpMeter()
        return self._meter or metrics.get_meter(settings.OTEL_SERVICE_NAME)

    def create_span(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
    ):
        """Create a new span.

        Usage:
            with telemetry.create_span("my_operation", {"key": "value"}) as span:
                # do work
                span.set_attribute("result", "success")
        """
        if not settings.OTEL_ENABLED:
            return NoOpSpan()
        return self.tracer.start_as_current_span(name, attributes=attributes)

    def create_counter(
        self,
        name: str,
        description: str = "",
        unit: str = "1",
    ):
        """Create a counter metric."""
        return self.meter.create_counter(
            name=name,
            description=description,
            unit=unit,
        )

    def create_histogram(
        self,
        name: str,
        description: str = "",
        unit: str = "ms",
    ):
        """Create a histogram metric."""
        return self.meter.create_histogram(
            name=name,
            description=description,
            unit=unit,
        )

    def create_gauge(
        self,
        name: str,
        description: str = "",
        unit: str = "1",
    ):
        """Create a gauge metric."""
        return self.meter.create_observable_gauge(
            name=name,
            description=description,
            unit=unit,
        )


class NoOpTracer:
    """No-op tracer when OpenTelemetry is disabled."""

    def start_as_current_span(self, name: str, **kwargs):
        return NoOpSpan()


class NoOpMeter:
    """No-op meter when OpenTelemetry is disabled."""

    def create_counter(self, **kwargs):
        return NoOpMetric()

    def create_histogram(self, **kwargs):
        return NoOpMetric()

    def create_observable_gauge(self, **kwargs):
        return NoOpMetric()


class NoOpSpan:
    """No-op span context manager."""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def set_attribute(self, key: str, value: Any):
        pass

    def set_status(self, status):
        pass

    def add_event(self, name: str, attributes: dict = None):
        pass

    def record_exception(self, exception):
        pass


class NoOpMetric:
    """No-op metric."""

    def add(self, value: int, attributes: dict = None):
        pass

    def record(self, value: float, attributes: dict = None):
        pass


# Singleton instance
telemetry = TelemetryService()


# Decorator for tracing functions
def traced(
    name: str | None = None,
    attributes: dict[str, Any] | None = None,
):
    """Decorator to trace a function.

    Usage:
        @traced("my_operation")
        async def my_function():
            pass

        @traced(attributes={"key": "value"})
        def another_function():
            pass
    """
    def decorator(func: Callable):
        span_name = name or f"{func.__module__}.{func.__name__}"

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with telemetry.create_span(span_name, attributes) as span:
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    if settings.OTEL_ENABLED:
                        span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            with telemetry.create_span(span_name, attributes) as span:
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    if settings.OTEL_ENABLED:
                        span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# Common metrics
class AppMetrics:
    """Pre-defined application metrics."""

    def __init__(self):
        self._initialized = False
        self._request_counter = None
        self._request_duration = None
        self._active_users = None
        self._ai_requests = None
        self._ai_tokens = None

    def initialize(self):
        """Initialize metrics."""
        if self._initialized or not settings.OTEL_ENABLED:
            return

        self._request_counter = telemetry.create_counter(
            "http_requests_total",
            "Total number of HTTP requests",
        )

        self._request_duration = telemetry.create_histogram(
            "http_request_duration_ms",
            "HTTP request duration in milliseconds",
        )

        self._ai_requests = telemetry.create_counter(
            "ai_requests_total",
            "Total number of AI API requests",
        )

        self._ai_tokens = telemetry.create_counter(
            "ai_tokens_total",
            "Total number of AI tokens used",
        )

        self._initialized = True

    def record_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
    ):
        """Record an HTTP request."""
        if not self._initialized:
            return

        attributes = {
            "method": method,
            "path": path,
            "status_code": status_code,
        }

        self._request_counter.add(1, attributes)
        self._request_duration.record(duration_ms, attributes)

    def record_ai_request(
        self,
        provider: str,
        model: str,
        tokens: int,
        duration_ms: float,
    ):
        """Record an AI API request."""
        if not self._initialized:
            return

        attributes = {
            "provider": provider,
            "model": model,
        }

        self._ai_requests.add(1, attributes)
        self._ai_tokens.add(tokens, attributes)


# Singleton metrics instance
app_metrics = AppMetrics()
