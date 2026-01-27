"""Prometheus metrics for observability."""

import time
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any

import structlog

from app.services.observability.config import ObservabilityConfig

logger = structlog.get_logger()

# Try to import prometheus_client
try:
    from prometheus_client import Counter, Histogram, Gauge, Info, REGISTRY
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    Counter = None
    Histogram = None
    Gauge = None
    Info = None


@dataclass
class LLMMetrics:
    """Metrics for LLM operations."""

    model: str
    provider: str
    operation: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0
    success: bool = True
    error: str | None = None
    cost_usd: float = 0
    cached: bool = False
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "model": self.model,
            "provider": self.provider,
            "operation": self.operation,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "latency_ms": self.latency_ms,
            "success": self.success,
            "error": self.error,
            "cost_usd": self.cost_usd,
            "cached": self.cached,
            "timestamp": self.timestamp.isoformat(),
        }


class MetricsCollector:
    """
    Prometheus metrics collector for NexusAI.

    Collects metrics for:
    - LLM requests (tokens, latency, cost)
    - RAG operations
    - Agent executions
    - Cache hit rates
    - API requests
    """

    def __init__(self, config: ObservabilityConfig | None = None):
        """
        Initialize metrics collector.

        Args:
            config: Observability configuration
        """
        self.config = config or ObservabilityConfig()
        self._enabled = self.config.prometheus_enabled and PROMETHEUS_AVAILABLE
        self._prefix = self.config.metrics_prefix

        # Local storage for when Prometheus is not available
        self._local_metrics: list[dict[str, Any]] = []

        if self._enabled:
            self._init_prometheus_metrics()
        else:
            logger.info("Prometheus metrics disabled or not available")

    def _init_prometheus_metrics(self) -> None:
        """Initialize Prometheus metrics."""
        # LLM metrics
        self.llm_requests_total = Counter(
            f"{self._prefix}_llm_requests_total",
            "Total LLM requests",
            ["model", "provider", "operation", "status"],
        )

        self.llm_tokens_total = Counter(
            f"{self._prefix}_llm_tokens_total",
            "Total tokens processed",
            ["model", "provider", "token_type"],
        )

        self.llm_latency_seconds = Histogram(
            f"{self._prefix}_llm_latency_seconds",
            "LLM request latency",
            ["model", "provider", "operation"],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
        )

        self.llm_cost_usd_total = Counter(
            f"{self._prefix}_llm_cost_usd_total",
            "Total LLM cost in USD",
            ["model", "provider"],
        )

        # Cache metrics
        self.cache_hits_total = Counter(
            f"{self._prefix}_cache_hits_total",
            "Total cache hits",
            ["cache_type"],
        )

        self.cache_misses_total = Counter(
            f"{self._prefix}_cache_misses_total",
            "Total cache misses",
            ["cache_type"],
        )

        self.cache_entries = Gauge(
            f"{self._prefix}_cache_entries",
            "Current cache entries",
            ["cache_type"],
        )

        # RAG metrics
        self.rag_queries_total = Counter(
            f"{self._prefix}_rag_queries_total",
            "Total RAG queries",
            ["status"],
        )

        self.rag_documents_retrieved = Histogram(
            f"{self._prefix}_rag_documents_retrieved",
            "Documents retrieved per query",
            buckets=[1, 3, 5, 10, 15, 20],
        )

        self.rag_latency_seconds = Histogram(
            f"{self._prefix}_rag_latency_seconds",
            "RAG query latency",
            buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
        )

        # Agent metrics
        self.agent_executions_total = Counter(
            f"{self._prefix}_agent_executions_total",
            "Total agent executions",
            ["agent_type", "status"],
        )

        self.agent_execution_time_seconds = Histogram(
            f"{self._prefix}_agent_execution_time_seconds",
            "Agent execution time",
            ["agent_type"],
            buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0],
        )

        self.agent_tool_calls_total = Counter(
            f"{self._prefix}_agent_tool_calls_total",
            "Total agent tool calls",
            ["agent_type", "tool_name"],
        )

        # API metrics
        self.http_requests_total = Counter(
            f"{self._prefix}_http_requests_total",
            "Total HTTP requests",
            ["method", "endpoint", "status"],
        )

        self.http_request_duration_seconds = Histogram(
            f"{self._prefix}_http_request_duration_seconds",
            "HTTP request duration",
            ["method", "endpoint"],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
        )

        # Guardrails metrics
        self.guardrails_checks_total = Counter(
            f"{self._prefix}_guardrails_checks_total",
            "Total guardrails checks",
            ["check_type", "result"],
        )

        self.guardrails_blocked_total = Counter(
            f"{self._prefix}_guardrails_blocked_total",
            "Total blocked requests",
            ["reason"],
        )

        # System metrics
        self.active_conversations = Gauge(
            f"{self._prefix}_active_conversations",
            "Number of active conversations",
        )

        self.active_users = Gauge(
            f"{self._prefix}_active_users",
            "Number of active users",
        )

        logger.info("Prometheus metrics initialized")

    def record_llm_request(self, metrics: LLMMetrics) -> None:
        """Record an LLM request."""
        status = "success" if metrics.success else "error"

        if self._enabled:
            # Request count
            self.llm_requests_total.labels(
                model=metrics.model,
                provider=metrics.provider,
                operation=metrics.operation,
                status=status,
            ).inc()

            # Tokens
            self.llm_tokens_total.labels(
                model=metrics.model,
                provider=metrics.provider,
                token_type="input",
            ).inc(metrics.input_tokens)

            self.llm_tokens_total.labels(
                model=metrics.model,
                provider=metrics.provider,
                token_type="output",
            ).inc(metrics.output_tokens)

            # Latency
            self.llm_latency_seconds.labels(
                model=metrics.model,
                provider=metrics.provider,
                operation=metrics.operation,
            ).observe(metrics.latency_ms / 1000)

            # Cost
            if metrics.cost_usd > 0:
                self.llm_cost_usd_total.labels(
                    model=metrics.model,
                    provider=metrics.provider,
                ).inc(metrics.cost_usd)

        # Always store locally for aggregation
        self._local_metrics.append(metrics.to_dict())

        # Trim old metrics
        if len(self._local_metrics) > 10000:
            self._local_metrics = self._local_metrics[-5000:]

    def record_cache_hit(self, cache_type: str) -> None:
        """Record a cache hit."""
        if self._enabled:
            self.cache_hits_total.labels(cache_type=cache_type).inc()

    def record_cache_miss(self, cache_type: str) -> None:
        """Record a cache miss."""
        if self._enabled:
            self.cache_misses_total.labels(cache_type=cache_type).inc()

    def set_cache_entries(self, cache_type: str, count: int) -> None:
        """Set current cache entry count."""
        if self._enabled:
            self.cache_entries.labels(cache_type=cache_type).set(count)

    def record_rag_query(
        self,
        success: bool,
        documents_retrieved: int,
        latency_ms: float,
    ) -> None:
        """Record a RAG query."""
        if self._enabled:
            status = "success" if success else "error"
            self.rag_queries_total.labels(status=status).inc()
            self.rag_documents_retrieved.observe(documents_retrieved)
            self.rag_latency_seconds.observe(latency_ms / 1000)

    def record_agent_execution(
        self,
        agent_type: str,
        success: bool,
        execution_time_ms: float,
        tool_calls: list[str] | None = None,
    ) -> None:
        """Record an agent execution."""
        if self._enabled:
            status = "success" if success else "error"
            self.agent_executions_total.labels(
                agent_type=agent_type,
                status=status,
            ).inc()

            self.agent_execution_time_seconds.labels(
                agent_type=agent_type,
            ).observe(execution_time_ms / 1000)

            if tool_calls:
                for tool in tool_calls:
                    self.agent_tool_calls_total.labels(
                        agent_type=agent_type,
                        tool_name=tool,
                    ).inc()

    def record_http_request(
        self,
        method: str,
        endpoint: str,
        status: int,
        duration_ms: float,
    ) -> None:
        """Record an HTTP request."""
        if self._enabled:
            self.http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=str(status),
            ).inc()

            self.http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint,
            ).observe(duration_ms / 1000)

    def record_guardrails_check(
        self,
        check_type: str,
        passed: bool,
        blocked_reason: str | None = None,
    ) -> None:
        """Record a guardrails check."""
        if self._enabled:
            result = "pass" if passed else "fail"
            self.guardrails_checks_total.labels(
                check_type=check_type,
                result=result,
            ).inc()

            if not passed and blocked_reason:
                self.guardrails_blocked_total.labels(
                    reason=blocked_reason,
                ).inc()

    def set_active_conversations(self, count: int) -> None:
        """Set active conversation count."""
        if self._enabled:
            self.active_conversations.set(count)

    def set_active_users(self, count: int) -> None:
        """Set active user count."""
        if self._enabled:
            self.active_users.set(count)

    def get_prometheus_metrics(self) -> tuple[bytes, str]:
        """Get Prometheus metrics in text format."""
        if not self._enabled:
            return b"# Prometheus not enabled", "text/plain"

        return generate_latest(REGISTRY), CONTENT_TYPE_LATEST

    def get_local_metrics(self) -> dict[str, Any]:
        """Get locally stored metrics."""
        if not self._local_metrics:
            return {
                "llm_requests": 0,
                "total_tokens": 0,
                "total_cost_usd": 0,
                "avg_latency_ms": 0,
            }

        total_tokens = sum(m.get("total_tokens", 0) for m in self._local_metrics)
        total_cost = sum(m.get("cost_usd", 0) or 0 for m in self._local_metrics)
        latencies = [m.get("latency_ms", 0) for m in self._local_metrics if m.get("latency_ms")]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0

        return {
            "llm_requests": len(self._local_metrics),
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost,
            "avg_latency_ms": avg_latency,
            "recent_requests": self._local_metrics[-20:],
        }


# Global metrics collector
_metrics_collector: MetricsCollector | None = None


def get_metrics_collector(
    config: ObservabilityConfig | None = None,
) -> MetricsCollector:
    """Get or create the global metrics collector."""
    global _metrics_collector

    if _metrics_collector is None:
        _metrics_collector = MetricsCollector(config=config)

    return _metrics_collector
