"""Observability configuration."""

import os
from dataclasses import dataclass, field


@dataclass
class ObservabilityConfig:
    """Configuration for observability services."""

    # Langfuse configuration
    langfuse_enabled: bool = True
    langfuse_public_key: str = field(
        default_factory=lambda: os.getenv("LANGFUSE_PUBLIC_KEY", "")
    )
    langfuse_secret_key: str = field(
        default_factory=lambda: os.getenv("LANGFUSE_SECRET_KEY", "")
    )
    langfuse_host: str = field(
        default_factory=lambda: os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    )
    # Optional: Project and Organization IDs for reference (not used by SDK, but useful for logging)
    langfuse_project_id: str = field(
        default_factory=lambda: os.getenv("LANGFUSE_PROJECT_ID", "")
    )
    langfuse_org_id: str = field(
        default_factory=lambda: os.getenv("LANGFUSE_ORG_ID", "")
    )

    # Phoenix (Arize AI) configuration
    phoenix_enabled: bool = False
    phoenix_endpoint: str = field(
        default_factory=lambda: os.getenv("PHOENIX_ENDPOINT", "")
    )
    phoenix_api_key: str = field(
        default_factory=lambda: os.getenv("PHOENIX_API_KEY", "")
    )
    phoenix_project_name: str = field(
        default_factory=lambda: os.getenv("PHOENIX_PROJECT_NAME", "nexusai")
    )
    phoenix_collect_traces: bool = True

    # Hallucination detection configuration
    hallucination_detection_enabled: bool = True
    hallucination_score_threshold: float = 0.7
    hallucination_check_rag_responses: bool = True
    hallucination_eval_model: str = field(
        default_factory=lambda: os.getenv("HALLUCINATION_EVAL_MODEL", "")
    )

    # Prometheus configuration
    prometheus_enabled: bool = True
    prometheus_port: int = 9090
    metrics_prefix: str = "nexusai"

    # OpenTelemetry configuration
    otel_enabled: bool = False
    otel_endpoint: str = field(
        default_factory=lambda: os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    )
    otel_service_name: str = "nexusai-backend"

    # Trace sampling
    sample_rate: float = 1.0  # 100% by default
    always_sample_errors: bool = True

    # Cost tracking
    track_costs: bool = True
    cost_alert_threshold: float = 100.0  # USD

    # Audit logging
    audit_log_enabled: bool = True
    audit_log_retention_days: int = 90

    # Dashboard refresh
    dashboard_refresh_interval: int = 60  # seconds


def get_observability_config() -> ObservabilityConfig:
    """Get observability configuration from environment."""
    return ObservabilityConfig(
        langfuse_enabled=os.getenv("LANGFUSE_ENABLED", "true").lower() == "true",
        langfuse_public_key=os.getenv("LANGFUSE_PUBLIC_KEY", ""),
        langfuse_secret_key=os.getenv("LANGFUSE_SECRET_KEY", ""),
        langfuse_host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        langfuse_project_id=os.getenv("LANGFUSE_PROJECT_ID", ""),
        langfuse_org_id=os.getenv("LANGFUSE_ORG_ID", ""),
        phoenix_enabled=os.getenv("PHOENIX_ENABLED", "false").lower() == "true",
        phoenix_endpoint=os.getenv("PHOENIX_ENDPOINT", ""),
        phoenix_api_key=os.getenv("PHOENIX_API_KEY", ""),
        phoenix_project_name=os.getenv("PHOENIX_PROJECT_NAME", "nexusai"),
        phoenix_collect_traces=os.getenv("PHOENIX_COLLECT_TRACES", "true").lower() == "true",
        hallucination_detection_enabled=os.getenv("HALLUCINATION_DETECTION_ENABLED", "true").lower() == "true",
        hallucination_score_threshold=float(os.getenv("HALLUCINATION_SCORE_THRESHOLD", "0.7")),
        hallucination_check_rag_responses=os.getenv("HALLUCINATION_CHECK_RAG_RESPONSES", "true").lower() == "true",
        hallucination_eval_model=os.getenv("HALLUCINATION_EVAL_MODEL", ""),
        prometheus_enabled=os.getenv("PROMETHEUS_ENABLED", "true").lower() == "true",
        otel_enabled=os.getenv("OTEL_ENABLED", "false").lower() == "true",
        sample_rate=float(os.getenv("TRACE_SAMPLE_RATE", "1.0")),
    )
