"""RAGAS evaluation models.

RAGAS (Retrieval-Augmented Generation Assessment) provides metrics to evaluate
RAG pipelines on both component and end-to-end levels.
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class RAGASMetricType(str, Enum):
    """Available RAGAS metrics."""

    # Core RAG Metrics
    FAITHFULNESS = "faithfulness"
    ANSWER_RELEVANCY = "answer_relevancy"
    CONTEXT_PRECISION = "context_precision"
    CONTEXT_RECALL = "context_recall"
    CONTEXT_ENTITIES_RECALL = "context_entities_recall"

    # Additional Metrics
    ANSWER_CORRECTNESS = "answer_correctness"
    ANSWER_SIMILARITY = "answer_similarity"
    FACTUAL_CORRECTNESS = "factual_correctness"
    NOISE_SENSITIVITY = "noise_sensitivity"

    # Semantic Metrics
    SEMANTIC_SIMILARITY = "semantic_similarity"

    # Custom/Composite
    HARMFULNESS = "harmfulness"
    COHERENCE = "coherence"


class EvaluationStatus(str, Enum):
    """Status of an evaluation."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EvaluationSample(BaseModel):
    """
    A single sample for RAGAS evaluation.

    This represents one query-response pair with its context.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))

    # Core fields (required for most metrics)
    user_input: str = Field(..., description="The user query/question")
    response: str = Field(..., description="The generated response from RAG")
    retrieved_contexts: list[str] = Field(
        default_factory=list,
        description="List of retrieved context documents"
    )

    # Optional fields for specific metrics
    reference: str | None = Field(
        None,
        description="Ground truth/expected answer (for answer_correctness)"
    )
    reference_contexts: list[str] = Field(
        default_factory=list,
        description="Ground truth contexts (for context_recall)"
    )

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MetricResult(BaseModel):
    """Result for a single metric evaluation."""

    name: str = Field(..., description="Metric name")
    score: float = Field(..., ge=0.0, le=1.0, description="Score between 0 and 1")
    passed: bool = Field(default=True, description="Whether score meets threshold")
    threshold: float | None = Field(None, description="Pass/fail threshold")
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metric-specific details"
    )
    error: str | None = Field(None, description="Error if metric failed to compute")


class SampleResult(BaseModel):
    """Evaluation results for a single sample."""

    sample_id: str
    metrics: list[MetricResult] = Field(default_factory=list)
    overall_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Weighted average of all metrics"
    )
    passed: bool = Field(default=False, description="All metrics passed thresholds")

    # Timing
    duration_ms: float = 0.0

    # Errors
    error: str | None = None


class RAGASEvaluationResult(BaseModel):
    """Complete RAGAS evaluation result."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str | None = None

    # Status
    status: EvaluationStatus = EvaluationStatus.PENDING

    # Configuration
    metrics_evaluated: list[str] = Field(default_factory=list)
    model_used: str | None = None
    embeddings_model: str | None = None

    # Results
    sample_results: list[SampleResult] = Field(default_factory=list)

    # Aggregate Metrics
    aggregate_scores: dict[str, float] = Field(
        default_factory=dict,
        description="Average score per metric across all samples"
    )
    overall_score: float = Field(
        default=0.0,
        description="Overall average score"
    )
    pass_rate: float = Field(
        default=0.0,
        description="Percentage of samples that passed all thresholds"
    )

    # Statistics
    total_samples: int = 0
    passed_samples: int = 0
    failed_samples: int = 0
    error_samples: int = 0

    # Timing
    started_at: datetime | None = None
    completed_at: datetime | None = None
    total_duration_ms: float = 0.0

    # Cost tracking
    total_tokens_used: int = 0
    total_cost_usd: float = 0.0

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def add_sample_result(self, result: SampleResult) -> None:
        """Add a sample result and update aggregates."""
        self.sample_results.append(result)
        self.total_samples += 1

        if result.error:
            self.error_samples += 1
        elif result.passed:
            self.passed_samples += 1
        else:
            self.failed_samples += 1

        # Update pass rate
        if self.total_samples > 0:
            self.pass_rate = self.passed_samples / self.total_samples

    def compute_aggregates(self) -> None:
        """Compute aggregate scores from sample results."""
        if not self.sample_results:
            return

        # Collect scores by metric
        metric_scores: dict[str, list[float]] = {}
        overall_scores: list[float] = []

        for sample in self.sample_results:
            if sample.error:
                continue

            overall_scores.append(sample.overall_score)

            for metric in sample.metrics:
                if metric.error:
                    continue
                if metric.name not in metric_scores:
                    metric_scores[metric.name] = []
                metric_scores[metric.name].append(metric.score)

        # Compute averages
        for metric_name, scores in metric_scores.items():
            if scores:
                self.aggregate_scores[metric_name] = sum(scores) / len(scores)

        if overall_scores:
            self.overall_score = sum(overall_scores) / len(overall_scores)


class EvaluationDataset(BaseModel):
    """A dataset of samples for evaluation."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str | None = None

    name: str
    description: str | None = None
    samples: list[EvaluationSample] = Field(default_factory=list)

    # Configuration
    default_metrics: list[RAGASMetricType] = Field(
        default_factory=lambda: [
            RAGASMetricType.FAITHFULNESS,
            RAGASMetricType.ANSWER_RELEVANCY,
            RAGASMetricType.CONTEXT_PRECISION,
            RAGASMetricType.CONTEXT_RECALL,
        ]
    )

    # Thresholds
    metric_thresholds: dict[str, float] = Field(
        default_factory=lambda: {
            "faithfulness": 0.7,
            "answer_relevancy": 0.7,
            "context_precision": 0.7,
            "context_recall": 0.7,
            "answer_correctness": 0.7,
        }
    )

    # Metadata
    version: int = 1
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_by: str | None = None

    def add_sample(self, sample: EvaluationSample) -> None:
        """Add a sample to the dataset."""
        self.samples.append(sample)
        self.updated_at = datetime.now(UTC)

    @classmethod
    def from_list(cls, data: list[dict[str, Any]], **kwargs) -> "EvaluationDataset":
        """Create dataset from list of dictionaries."""
        samples = [EvaluationSample(**item) for item in data]
        return cls(samples=samples, **kwargs)


@dataclass
class RAGASMetricConfig:
    """Configuration for individual RAGAS metrics."""

    name: RAGASMetricType
    enabled: bool = True
    threshold: float = 0.7
    weight: float = 1.0
    llm_model: str | None = None  # Override default LLM for this metric
    embeddings_model: str | None = None  # Override default embeddings


@dataclass
class BatchEvaluationConfig:
    """Configuration for batch evaluation."""

    batch_size: int = 10
    max_concurrent: int = 5
    timeout_seconds: int = 300
    retry_on_failure: bool = True
    max_retries: int = 2


class RAGASEvaluationRequest(BaseModel):
    """Request to run RAGAS evaluation."""

    # Samples to evaluate
    samples: list[EvaluationSample] = Field(
        default_factory=list,
        min_length=1,
    )

    # Or use a dataset
    dataset_id: str | None = None

    # Metrics to compute
    metrics: list[RAGASMetricType] = Field(
        default_factory=lambda: [
            RAGASMetricType.FAITHFULNESS,
            RAGASMetricType.ANSWER_RELEVANCY,
            RAGASMetricType.CONTEXT_PRECISION,
            RAGASMetricType.CONTEXT_RECALL,
        ]
    )

    # Thresholds
    thresholds: dict[str, float] = Field(
        default_factory=lambda: {
            "faithfulness": 0.7,
            "answer_relevancy": 0.7,
            "context_precision": 0.7,
            "context_recall": 0.7,
        }
    )

    # Model configuration
    llm_model: str = "gpt-4o"
    llm_provider: str = "openai"
    embeddings_model: str = "text-embedding-3-small"

    # Execution options
    async_execution: bool = False
    log_to_langfuse: bool = True
    persist_results: bool = True

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)


class RAGASQuickEvalRequest(BaseModel):
    """Quick single-sample evaluation request."""

    user_input: str
    response: str
    retrieved_contexts: list[str]
    reference: str | None = None

    metrics: list[RAGASMetricType] = Field(
        default_factory=lambda: [
            RAGASMetricType.FAITHFULNESS,
            RAGASMetricType.ANSWER_RELEVANCY,
        ]
    )

    llm_model: str = "gpt-4o"
