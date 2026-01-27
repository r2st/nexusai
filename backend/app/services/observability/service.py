"""Unified observability service."""

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import structlog

from app.services.observability.config import ObservabilityConfig, get_observability_config
from app.services.observability.langfuse_client import (
    LangfuseClient,
    TraceContext,
    SpanContext,
)
from app.services.observability.metrics import (
    MetricsCollector,
    LLMMetrics,
)

logger = structlog.get_logger()


class ObservabilityService:
    """
    Unified observability service for NexusAI.

    Combines:
    - Langfuse for LLM tracing
    - Prometheus for metrics
    - Structured logging
    """

    def __init__(self, config: ObservabilityConfig | None = None):
        """
        Initialize the observability service.

        Args:
            config: Observability configuration
        """
        self.config = config or get_observability_config()

        self.langfuse = LangfuseClient(config=self.config)
        self.metrics = MetricsCollector(config=self.config)

        self._initialized = False

    async def initialize(self) -> None:
        """Initialize all observability components."""
        if self._initialized:
            return

        await self.langfuse.initialize()
        self._initialized = True

        logger.info("Observability service initialized")

    async def close(self) -> None:
        """Close all observability connections."""
        await self.langfuse.close()
        self._initialized = False

        logger.info("Observability service closed")

    # Trace management

    @asynccontextmanager
    async def trace(
        self,
        name: str,
        user_id: str | None = None,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AsyncGenerator[TraceContext, None]:
        """
        Create a trace context.

        Usage:
            async with observability.trace("chat-request", user_id="123") as trace:
                # Do work
                pass
        """
        async with self.langfuse.trace(
            name=name,
            user_id=user_id,
            session_id=session_id,
            metadata=metadata,
        ) as trace:
            yield trace

    @asynccontextmanager
    async def span(
        self,
        trace: TraceContext,
        name: str,
        input_data: Any = None,
    ) -> AsyncGenerator[SpanContext, None]:
        """
        Create a span within a trace.

        Usage:
            async with observability.span(trace, "llm-call") as span:
                result = await call_llm()
                span.set_output(result)
        """
        async with self.langfuse.span(trace, name, input_data) as span:
            yield span

    # LLM observability

    def record_llm_request(
        self,
        trace: TraceContext | None,
        model: str,
        provider: str,
        operation: str,
        input_messages: list[dict[str, Any]],
        output: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        latency_ms: float = 0,
        success: bool = True,
        error: str | None = None,
        cost_usd: float = 0,
        cached: bool = False,
    ) -> None:
        """
        Record an LLM request to both Langfuse and Prometheus.

        Args:
            trace: Optional trace context
            model: Model identifier
            provider: Provider name
            operation: Operation type (chat, completion, etc.)
            input_messages: Input messages
            output: Model output
            input_tokens: Input token count
            output_tokens: Output token count
            latency_ms: Request latency
            success: Whether request succeeded
            error: Error message if failed
            cost_usd: Request cost
            cached: Whether response was cached
        """
        # Log to Langfuse
        if trace:
            self.langfuse.log_generation(
                trace=trace,
                name=f"{provider}-{operation}",
                model=model,
                input_messages=input_messages,
                output=output,
                usage={
                    "prompt_tokens": input_tokens,
                    "completion_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                },
                model_parameters={"cached": cached},
                latency_ms=int(latency_ms),
            )

        # Record Prometheus metrics
        metrics = LLMMetrics(
            model=model,
            provider=provider,
            operation=operation,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            latency_ms=latency_ms,
            success=success,
            error=error,
            cost_usd=cost_usd,
            cached=cached,
        )
        self.metrics.record_llm_request(metrics)

        # Record cache metrics
        if cached:
            self.metrics.record_cache_hit("llm")
        else:
            self.metrics.record_cache_miss("llm")

        # Log for debugging
        logger.debug(
            "LLM request recorded",
            model=model,
            provider=provider,
            tokens=input_tokens + output_tokens,
            latency_ms=latency_ms,
            cached=cached,
        )

    # RAG observability

    def record_rag_query(
        self,
        trace: TraceContext | None,
        query: str,
        documents_retrieved: int,
        latency_ms: float,
        success: bool = True,
        reranked: bool = False,
        error: str | None = None,
    ) -> None:
        """Record a RAG query."""
        # Log to Langfuse as a span
        if trace:
            span = self.langfuse.start_span(
                trace=trace,
                name="rag-retrieval",
                input_data={"query": query},
                metadata={
                    "documents_retrieved": documents_retrieved,
                    "reranked": reranked,
                },
            )
            # End the span immediately with the results
            self.langfuse.end_span(
                span,
                output={"documents_retrieved": documents_retrieved},
                status="success" if success else "error",
                error=error,
            )

        # Record metrics
        self.metrics.record_rag_query(
            success=success,
            documents_retrieved=documents_retrieved,
            latency_ms=latency_ms,
        )

    # Agent observability

    def record_agent_execution(
        self,
        trace: TraceContext | None,
        agent_type: str,
        input_message: str,
        output_message: str,
        execution_time_ms: float,
        success: bool = True,
        tool_calls: list[str] | None = None,
        error: str | None = None,
    ) -> None:
        """Record an agent execution."""
        # Log to Langfuse
        if trace:
            span = self.langfuse.start_span(
                trace=trace,
                name=f"agent-{agent_type}",
                input_data=input_message,
                metadata={
                    "tool_calls": tool_calls,
                },
            )
            self.langfuse.end_span(
                span,
                output=output_message,
                status="success" if success else "error",
                error=error,
            )

        # Record metrics
        self.metrics.record_agent_execution(
            agent_type=agent_type,
            success=success,
            execution_time_ms=execution_time_ms,
            tool_calls=tool_calls,
        )

    # Guardrails observability

    def record_guardrails_check(
        self,
        trace: TraceContext | None,
        check_type: str,
        passed: bool,
        details: dict[str, Any] | None = None,
        blocked_reason: str | None = None,
    ) -> None:
        """Record a guardrails check."""
        # Log to trace
        if trace:
            trace.add_metadata(f"guardrails_{check_type}", {
                "passed": passed,
                "details": details,
                "blocked_reason": blocked_reason,
            })

        # Record metrics
        self.metrics.record_guardrails_check(
            check_type=check_type,
            passed=passed,
            blocked_reason=blocked_reason,
        )

        if not passed:
            logger.warning(
                "Guardrails check failed",
                check_type=check_type,
                blocked_reason=blocked_reason,
            )

    # HTTP observability

    def record_http_request(
        self,
        method: str,
        endpoint: str,
        status: int,
        duration_ms: float,
        user_id: str | None = None,
    ) -> None:
        """Record an HTTP request."""
        self.metrics.record_http_request(
            method=method,
            endpoint=endpoint,
            status=status,
            duration_ms=duration_ms,
        )

    # Dashboard data

    async def get_dashboard_data(self) -> dict[str, Any]:
        """Get aggregated data for dashboard."""
        langfuse_metrics = self.langfuse.get_metrics()
        local_metrics = self.metrics.get_local_metrics()

        return {
            "langfuse": langfuse_metrics,
            "prometheus": local_metrics,
            "summary": {
                "total_traces": langfuse_metrics.get("traces", 0),
                "total_generations": langfuse_metrics.get("generations", 0),
                "total_tokens": langfuse_metrics.get("total_tokens", 0),
                "total_cost_usd": langfuse_metrics.get("total_cost_usd", 0),
                "llm_requests": local_metrics.get("llm_requests", 0),
                "avg_latency_ms": local_metrics.get("avg_latency_ms", 0),
            },
        }

    def get_prometheus_metrics(self) -> tuple[bytes, str]:
        """Get Prometheus metrics endpoint data."""
        return self.metrics.get_prometheus_metrics()

    def flush(self) -> None:
        """Flush all pending data."""
        self.langfuse.flush()


# Global service instance
_observability_service: ObservabilityService | None = None


async def get_observability_service(
    config: ObservabilityConfig | None = None,
) -> ObservabilityService:
    """Get or create the global observability service."""
    global _observability_service

    if _observability_service is None:
        _observability_service = ObservabilityService(config=config)
        await _observability_service.initialize()

    return _observability_service


async def close_observability_service() -> None:
    """Close the global observability service."""
    global _observability_service

    if _observability_service is not None:
        await _observability_service.close()
        _observability_service = None
