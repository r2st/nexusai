"""Langfuse integration for LLM observability."""

import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, AsyncGenerator
from uuid import uuid4

import structlog

from app.services.observability.config import ObservabilityConfig

logger = structlog.get_logger()

# Try to import langfuse, but don't fail if not installed
try:
    from langfuse import Langfuse
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    Langfuse = None


@dataclass
class SpanContext:
    """Context for a Langfuse span."""

    span_id: str
    trace_id: str
    name: str
    start_time: datetime
    metadata: dict[str, Any] = field(default_factory=dict)
    input_data: Any = None
    output_data: Any = None
    _span: Any = None  # Langfuse span object

    def set_output(self, output: Any) -> None:
        """Set the span output."""
        self.output_data = output

    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to the span."""
        self.metadata[key] = value


@dataclass
class TraceContext:
    """Context for a Langfuse trace."""

    trace_id: str
    name: str
    user_id: str | None = None
    session_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    start_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    _trace: Any = None  # Langfuse trace object
    _spans: list[SpanContext] = field(default_factory=list)

    def add_tag(self, tag: str) -> None:
        """Add a tag to the trace."""
        self.tags.append(tag)

    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to the trace."""
        self.metadata[key] = value


class LangfuseClient:
    """
    Langfuse client for LLM observability.

    Provides:
    - Trace and span management
    - LLM call logging with input/output
    - Cost and latency tracking
    - User and session association
    """

    def __init__(self, config: ObservabilityConfig | None = None):
        """
        Initialize Langfuse client.

        Args:
            config: Observability configuration
        """
        self.config = config or ObservabilityConfig()
        self._client: Langfuse | None = None
        self._enabled = False

        # Local tracking when Langfuse is not available
        self._traces: dict[str, TraceContext] = {}
        self._metrics: dict[str, list[dict[str, Any]]] = {
            "traces": [],
            "generations": [],
            "spans": [],
        }

    async def initialize(self) -> None:
        """Initialize the Langfuse client."""
        if not self.config.langfuse_enabled:
            logger.info("Langfuse disabled by configuration")
            return

        if not LANGFUSE_AVAILABLE:
            logger.warning("Langfuse package not installed, using local tracking")
            return

        if not self.config.langfuse_public_key or not self.config.langfuse_secret_key:
            logger.warning("Langfuse credentials not configured")
            return

        try:
            self._client = Langfuse(
                public_key=self.config.langfuse_public_key,
                secret_key=self.config.langfuse_secret_key,
                host=self.config.langfuse_host,
            )
            self._enabled = True
            log_data = {
                "host": self.config.langfuse_host,
            }
            if self.config.langfuse_project_id:
                log_data["project_id"] = self.config.langfuse_project_id
            if self.config.langfuse_org_id:
                log_data["org_id"] = self.config.langfuse_org_id
            logger.info("Langfuse client initialized", **log_data)

        except Exception as e:
            logger.error("Failed to initialize Langfuse", error=str(e))

    async def close(self) -> None:
        """Flush and close the Langfuse client."""
        if self._client:
            try:
                self._client.flush()
            except Exception as e:
                logger.error("Failed to flush Langfuse", error=str(e))

        logger.info("Langfuse client closed")

    def create_trace(
        self,
        name: str,
        user_id: str | None = None,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> TraceContext:
        """
        Create a new trace.

        In Langfuse v3, traces are created implicitly via spans.
        We create a root span to represent the trace.

        Args:
            name: Trace name
            user_id: User identifier
            session_id: Session identifier
            metadata: Additional metadata
            tags: Tags for filtering

        Returns:
            TraceContext object
        """
        trace_id = self._client.create_trace_id() if self._enabled and self._client else str(uuid4())

        context = TraceContext(
            trace_id=trace_id,
            name=name,
            user_id=user_id,
            session_id=session_id,
            metadata=metadata or {},
            tags=tags or [],
        )

        if self._enabled and self._client:
            try:
                # In Langfuse v3, we use start_span with trace_context dict
                # trace_context contains trace_id and optionally parent_span_id
                langfuse_trace_ctx = {"trace_id": trace_id}
                span = self._client.start_span(
                    trace_context=langfuse_trace_ctx,
                    name=name,
                    metadata={
                        **(metadata or {}),
                        "user_id": user_id,
                        "session_id": session_id,
                        "tags": tags,
                    },
                )
                context._trace = span  # Store the root span as the "trace"
            except Exception as e:
                logger.error("Failed to create Langfuse trace", error=str(e))

        self._traces[trace_id] = context
        self._metrics["traces"].append({
            "trace_id": trace_id,
            "name": name,
            "user_id": user_id,
            "start_time": context.start_time.isoformat(),
        })

        logger.debug("Trace created", trace_id=trace_id, name=name)
        return context

    def start_span(
        self,
        trace: TraceContext,
        name: str,
        input_data: Any = None,
        metadata: dict[str, Any] | None = None,
    ) -> SpanContext:
        """
        Start a new span within a trace.

        Args:
            trace: Parent trace context
            name: Span name
            input_data: Input data for the span
            metadata: Additional metadata

        Returns:
            SpanContext object
        """
        span_id = str(uuid4())

        context = SpanContext(
            span_id=span_id,
            trace_id=trace.trace_id,
            name=name,
            start_time=datetime.now(UTC),
            metadata=metadata or {},
            input_data=input_data,
        )

        if self._enabled and self._client:
            try:
                # In Langfuse v3, create span using trace_context dict
                langfuse_trace_ctx = {"trace_id": trace.trace_id}
                if trace._trace and hasattr(trace._trace, 'id'):
                    langfuse_trace_ctx["parent_span_id"] = trace._trace.id
                span = self._client.start_span(
                    trace_context=langfuse_trace_ctx,
                    name=name,
                    input=input_data,
                    metadata=metadata,
                )
                context._span = span
            except Exception as e:
                logger.error("Failed to create Langfuse span", error=str(e))

        trace._spans.append(context)
        return context

    def end_span(
        self,
        span: SpanContext,
        output: Any = None,
        status: str = "success",
        error: str | None = None,
    ) -> None:
        """
        End a span.

        Args:
            span: Span context
            output: Output data
            status: Span status
            error: Error message if failed
        """
        span.output_data = output
        end_time = datetime.now(UTC)
        duration_ms = int((end_time - span.start_time).total_seconds() * 1000)

        if span._span:
            try:
                span._span.end(
                    output=output,
                    status_message=error if error else None,
                )
            except Exception as e:
                logger.error("Failed to end Langfuse span", error=str(e))

        self._metrics["spans"].append({
            "span_id": span.span_id,
            "trace_id": span.trace_id,
            "name": span.name,
            "duration_ms": duration_ms,
            "status": status,
            "error": error,
        })

    def log_generation(
        self,
        trace: TraceContext,
        name: str,
        model: str,
        input_messages: list[dict[str, Any]],
        output: str,
        usage: dict[str, int] | None = None,
        model_parameters: dict[str, Any] | None = None,
        latency_ms: int | None = None,
    ) -> None:
        """
        Log an LLM generation.

        Args:
            trace: Parent trace context
            name: Generation name
            model: Model identifier
            input_messages: Input messages
            output: Model output
            usage: Token usage stats
            model_parameters: Model parameters (temperature, etc.)
            latency_ms: Latency in milliseconds
        """
        generation_id = str(uuid4())

        if self._enabled and self._client:
            try:
                # In Langfuse v3, use start_generation with trace_context dict
                langfuse_trace_ctx = {"trace_id": trace.trace_id}
                if trace._trace and hasattr(trace._trace, 'id'):
                    langfuse_trace_ctx["parent_span_id"] = trace._trace.id
                generation = self._client.start_generation(
                    trace_context=langfuse_trace_ctx,
                    name=name,
                    model=model,
                    input=input_messages,
                    model_parameters=model_parameters,
                )
                # End the generation immediately with output and usage
                generation.end(
                    output=output,
                    usage_details=usage,
                )
            except Exception as e:
                logger.error("Failed to log Langfuse generation", error=str(e))

        # Calculate cost if usage provided
        cost = None
        if usage and self.config.track_costs:
            cost = self._calculate_cost(model, usage)

        self._metrics["generations"].append({
            "generation_id": generation_id,
            "trace_id": trace.trace_id,
            "name": name,
            "model": model,
            "input_tokens": usage.get("prompt_tokens", 0) if usage else 0,
            "output_tokens": usage.get("completion_tokens", 0) if usage else 0,
            "total_tokens": usage.get("total_tokens", 0) if usage else 0,
            "latency_ms": latency_ms,
            "cost_usd": cost,
            "timestamp": datetime.now(UTC).isoformat(),
        })

        logger.debug(
            "Generation logged",
            generation_id=generation_id,
            model=model,
            tokens=usage.get("total_tokens", 0) if usage else 0,
        )

    def _calculate_cost(
        self,
        model: str,
        usage: dict[str, int],
    ) -> float:
        """Calculate cost based on model and usage."""
        # Cost per 1K tokens (approximate)
        costs = {
            # OpenAI
            "gpt-4o": {"input": 0.005, "output": 0.015},
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
            # Anthropic
            "claude-3-opus": {"input": 0.015, "output": 0.075},
            "claude-3-sonnet": {"input": 0.003, "output": 0.015},
            "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
            # Google
            "gemini-pro": {"input": 0.00025, "output": 0.0005},
            "gemini-1.5-pro": {"input": 0.0025, "output": 0.0075},
        }

        # Find matching model - try exact match first, then partial
        model_costs = None
        model_lower = model.lower()

        # First try exact match
        if model_lower in costs:
            model_costs = costs[model_lower]
        else:
            # Then try partial match, preferring longer (more specific) matches
            matches = [(key, info) for key, info in costs.items() if key in model_lower]
            if matches:
                # Sort by key length descending to get most specific match
                matches.sort(key=lambda x: len(x[0]), reverse=True)
                model_costs = matches[0][1]

        if not model_costs:
            return 0.0

        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        cost = (
            (input_tokens / 1000) * model_costs["input"] +
            (output_tokens / 1000) * model_costs["output"]
        )

        return round(cost, 6)

    def end_trace(
        self,
        trace: TraceContext,
        output: Any = None,
        status: str = "success",
        error: str | None = None,
    ) -> None:
        """
        End a trace.

        Args:
            trace: Trace context
            output: Final output
            status: Trace status
            error: Error message if failed
        """
        if trace._trace:
            try:
                # In Langfuse v3, end the root span that represents the trace
                trace._trace.end(
                    output=output,
                    status_message=error if error else None,
                )
            except Exception as e:
                logger.error("Failed to end Langfuse trace", error=str(e))

        # Update metrics
        for t in self._metrics["traces"]:
            if t["trace_id"] == trace.trace_id:
                t["status"] = status
                t["error"] = error
                t["end_time"] = datetime.now(UTC).isoformat()
                break

        logger.debug("Trace ended", trace_id=trace.trace_id, status=status)

    @asynccontextmanager
    async def trace(
        self,
        name: str,
        user_id: str | None = None,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AsyncGenerator[TraceContext, None]:
        """
        Context manager for tracing.

        Usage:
            async with langfuse.trace("my-operation") as trace:
                # Do work
                trace.add_metadata("key", "value")
        """
        context = self.create_trace(
            name=name,
            user_id=user_id,
            session_id=session_id,
            metadata=metadata,
        )

        try:
            yield context
            self.end_trace(context, status="success")
        except Exception as e:
            self.end_trace(context, status="error", error=str(e))
            raise

    @asynccontextmanager
    async def span(
        self,
        trace: TraceContext,
        name: str,
        input_data: Any = None,
    ) -> AsyncGenerator[SpanContext, None]:
        """
        Context manager for spans.

        Usage:
            async with langfuse.span(trace, "my-span") as span:
                result = await do_work()
                span.set_output(result)
        """
        context = self.start_span(trace, name, input_data)

        try:
            yield context
            self.end_span(context, output=context.output_data, status="success")
        except Exception as e:
            self.end_span(context, status="error", error=str(e))
            raise

    def get_metrics(self) -> dict[str, Any]:
        """Get collected metrics."""
        total_tokens = sum(g.get("total_tokens", 0) for g in self._metrics["generations"])
        total_cost = sum(g.get("cost_usd", 0) or 0 for g in self._metrics["generations"])

        return {
            "traces": len(self._metrics["traces"]),
            "generations": len(self._metrics["generations"]),
            "spans": len(self._metrics["spans"]),
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost,
            "recent_traces": self._metrics["traces"][-10:],
            "recent_generations": self._metrics["generations"][-10:],
        }

    def flush(self) -> None:
        """Flush pending events to Langfuse."""
        if self._client:
            try:
                self._client.flush()
            except Exception as e:
                logger.error("Failed to flush Langfuse", error=str(e))


# Global client instance
_langfuse_client: LangfuseClient | None = None


async def get_langfuse_client(
    config: ObservabilityConfig | None = None,
) -> LangfuseClient:
    """Get or create the global Langfuse client."""
    global _langfuse_client

    if _langfuse_client is None:
        _langfuse_client = LangfuseClient(config=config)
        await _langfuse_client.initialize()

    return _langfuse_client
