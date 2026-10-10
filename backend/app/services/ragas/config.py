"""RAGAS configuration."""

import os
from dataclasses import dataclass, field

from app.services.ragas.models import RAGASMetricType


@dataclass
class RAGASConfig:
    """
    Configuration for RAGAS evaluation service.

    Supports multiple LLM providers and embeddings configurations.
    """

    # LLM Configuration
    llm_provider: str = field(
        default_factory=lambda: os.getenv("DEFAULT_AI_PROVIDER", "openai")
    )
    llm_model: str = field(
        default_factory=lambda: os.getenv("RAGAS_LLM_MODEL", "gpt-4o")
    )
    llm_temperature: float = 0.1  # Low temperature for consistent evaluation

    # Embeddings Configuration
    embeddings_provider: str = field(
        default_factory=lambda: os.getenv("RAGAS_EMBEDDINGS_PROVIDER", "openai")
    )
    embeddings_model: str = field(
        default_factory=lambda: os.getenv(
            "RAGAS_EMBEDDINGS_MODEL", "text-embedding-3-small"
        )
    )

    # Default Metrics
    default_metrics: list[RAGASMetricType] = field(
        default_factory=lambda: [
            RAGASMetricType.FAITHFULNESS,
            RAGASMetricType.ANSWER_RELEVANCY,
            RAGASMetricType.CONTEXT_PRECISION,
            RAGASMetricType.CONTEXT_RECALL,
        ]
    )

    # Default Thresholds (score must be >= threshold to pass)
    default_thresholds: dict[str, float] = field(
        default_factory=lambda: {
            "faithfulness": 0.7,
            "answer_relevancy": 0.7,
            "context_precision": 0.7,
            "context_recall": 0.7,
            "context_entities_recall": 0.6,
            "answer_correctness": 0.7,
            "answer_similarity": 0.8,
            "factual_correctness": 0.7,
            "semantic_similarity": 0.8,
        }
    )

    # Metric Weights (for composite scoring)
    metric_weights: dict[str, float] = field(
        default_factory=lambda: {
            "faithfulness": 1.0,
            "answer_relevancy": 1.0,
            "context_precision": 1.0,
            "context_recall": 1.0,
            "context_entities_recall": 0.8,
            "answer_correctness": 1.0,
            "answer_similarity": 0.8,
            "factual_correctness": 1.0,
        }
    )

    # Batch Processing
    batch_size: int = 10
    max_concurrent_evaluations: int = 5
    timeout_seconds: int = 300

    # Retry Configuration
    retry_on_failure: bool = True
    max_retries: int = 2
    retry_delay_seconds: float = 1.0

    # Observability
    langfuse_enabled: bool = field(
        default_factory=lambda: os.getenv("LANGFUSE_ENABLED", "false").lower() == "true"
    )
    log_to_langfuse: bool = True
    langfuse_trace_name: str = "ragas-evaluation"

    # Caching
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600  # 1 hour

    # Feature Flags
    enable_async_evaluation: bool = True
    enable_cost_tracking: bool = True
    persist_results: bool = True

    def get_threshold(self, metric: str) -> float:
        """Get threshold for a metric."""
        return self.default_thresholds.get(metric, 0.7)

    def get_weight(self, metric: str) -> float:
        """Get weight for a metric."""
        return self.metric_weights.get(metric, 1.0)


@dataclass
class ProviderConfig:
    """Provider-specific configuration."""

    # OpenAI
    openai_api_key: str = field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY", "")
    )
    openai_api_base: str | None = field(
        default_factory=lambda: os.getenv("OPENAI_API_BASE", None)
    )

    # Anthropic
    anthropic_api_key: str = field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", "")
    )

    # Google
    google_api_key: str = field(
        default_factory=lambda: os.getenv("GOOGLE_API_KEY", "")
    )

    # Ollama (local)
    ollama_base_url: str = field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    )


def get_ragas_config() -> RAGASConfig:
    """Get RAGAS configuration from environment."""
    return RAGASConfig()


def get_provider_config() -> ProviderConfig:
    """Get provider configuration from environment."""
    return ProviderConfig()
