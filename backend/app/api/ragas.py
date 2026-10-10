"""RAGAS Evaluation API endpoints.

Provides endpoints for:
- Running RAGAS evaluations on RAG pipelines
- Quick single-sample evaluation
- Batch evaluation with datasets
- Evaluation analytics and results
"""

from datetime import datetime, timedelta, UTC
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.api.deps import get_current_user, get_db
from app.core.multitenancy import get_current_tenant_id
from app.models.user import User
from app.services.ragas import (
    EvaluationDataset,
    EvaluationSample,
    EvaluationStatus,
    MetricResult,
    RAGASConfig,
    RAGASEvaluationRequest,
    RAGASEvaluationResult,
    RAGASMetricType,
    RAGASQuickEvalRequest,
    RAGASService,
    SampleResult,
    get_ragas_config,
    get_ragas_service,
    RAGAS_AVAILABLE,
)
from app.services.observability.langfuse_client import get_langfuse_client, LangfuseClient

logger = structlog.get_logger()

router = APIRouter(prefix="/ragas", tags=["ragas"])


# =============================================================================
# Request/Response Models
# =============================================================================


class EvaluationSampleRequest(BaseModel):
    """A sample for evaluation."""

    user_input: str = Field(..., description="The user query/question")
    response: str = Field(..., description="The generated response")
    retrieved_contexts: list[str] = Field(
        default_factory=list, description="Retrieved context documents"
    )
    reference: str | None = Field(
        None, description="Ground truth answer (optional)"
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvaluateRequest(BaseModel):
    """Request to run RAGAS evaluation."""

    samples: list[EvaluationSampleRequest] = Field(
        ..., min_length=1, max_length=100, description="Samples to evaluate"
    )
    metrics: list[str] = Field(
        default_factory=lambda: [
            "faithfulness",
            "answer_relevancy",
            "context_precision",
            "context_recall",
        ],
        description="Metrics to compute",
    )
    thresholds: dict[str, float] = Field(
        default_factory=lambda: {
            "faithfulness": 0.7,
            "answer_relevancy": 0.7,
            "context_precision": 0.7,
            "context_recall": 0.7,
        },
        description="Pass/fail thresholds per metric",
    )
    llm_model: str = Field("gpt-4o", description="LLM model for evaluation")
    llm_provider: str = Field("openai", description="LLM provider")
    async_execution: bool = Field(
        False, description="Run evaluation asynchronously"
    )
    log_to_langfuse: bool = Field(True, description="Log results to Langfuse")


class QuickEvaluateRequest(BaseModel):
    """Quick single-sample evaluation request."""

    user_input: str = Field(..., description="The user query")
    response: str = Field(..., description="The generated response")
    retrieved_contexts: list[str] = Field(..., description="Retrieved contexts")
    reference: str | None = Field(None, description="Ground truth (optional)")
    metrics: list[str] = Field(
        default_factory=lambda: ["faithfulness", "answer_relevancy"],
        description="Metrics to compute",
    )


class MetricResultResponse(BaseModel):
    """Result for a single metric."""

    name: str = Field(..., description="Metric name")
    score: float = Field(..., description="Score (0-1)")
    passed: bool = Field(..., description="Whether score meets threshold")
    threshold: float | None = Field(None, description="Pass/fail threshold")
    details: dict[str, Any] = Field(default_factory=dict)
    error: str | None = Field(None, description="Error if computation failed")


class SampleResultResponse(BaseModel):
    """Evaluation result for a single sample."""

    sample_id: str = Field(..., description="Sample ID")
    metrics: list[MetricResultResponse] = Field(default_factory=list)
    overall_score: float = Field(..., description="Overall score (0-1)")
    passed: bool = Field(..., description="All metrics passed")
    duration_ms: float = Field(0.0, description="Evaluation duration")
    error: str | None = None


class EvaluationResultResponse(BaseModel):
    """Complete evaluation result."""

    id: str = Field(..., description="Evaluation ID")
    status: str = Field(..., description="Evaluation status")

    # Configuration
    metrics_evaluated: list[str] = Field(default_factory=list)
    model_used: str | None = None

    # Results
    sample_results: list[SampleResultResponse] = Field(default_factory=list)

    # Aggregate Metrics
    aggregate_scores: dict[str, float] = Field(default_factory=dict)
    overall_score: float = Field(0.0, description="Overall average score")
    pass_rate: float = Field(0.0, description="Percentage of samples passed")

    # Statistics
    total_samples: int = 0
    passed_samples: int = 0
    failed_samples: int = 0
    error_samples: int = 0

    # Timing
    total_duration_ms: float = 0.0
    started_at: datetime | None = None
    completed_at: datetime | None = None


class AsyncEvaluationResponse(BaseModel):
    """Response for async evaluation submission."""

    evaluation_id: str = Field(..., description="Evaluation ID for status checking")
    status: str = Field(..., description="Current status")
    message: str = Field(..., description="Status message")


class RAGASStatusResponse(BaseModel):
    """RAGAS service status."""

    available: bool = Field(..., description="Whether RAGAS is available")
    version: str | None = Field(None, description="RAGAS version if available")
    default_metrics: list[str] = Field(default_factory=list)
    supported_providers: list[str] = Field(default_factory=list)


# =============================================================================
# Dependencies
# =============================================================================


async def get_ragas_service_dep(
    langfuse: Annotated[LangfuseClient | None, Depends(get_langfuse_client)] = None,
) -> RAGASService:
    """Get RAGAS service with Langfuse integration."""
    config = get_ragas_config()
    return await get_ragas_service(config=config, langfuse_client=langfuse)


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/status",
    response_model=RAGASStatusResponse,
    summary="Get RAGAS status",
    description="Check if RAGAS is available and get configuration info.",
)
async def get_status() -> RAGASStatusResponse:
    """Get RAGAS service status."""
    config = get_ragas_config()

    version = None
    if RAGAS_AVAILABLE:
        try:
            import ragas
            version = getattr(ragas, "__version__", "unknown")
        except Exception:
            pass

    return RAGASStatusResponse(
        available=RAGAS_AVAILABLE,
        version=version,
        default_metrics=[m.value for m in config.default_metrics],
        supported_providers=["openai", "anthropic", "google", "ollama"],
    )


@router.post(
    "/evaluate",
    response_model=EvaluationResultResponse,
    summary="Run RAGAS evaluation",
    description="Evaluate RAG pipeline samples using RAGAS metrics.",
)
async def evaluate(
    request: EvaluateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[RAGASService, Depends(get_ragas_service_dep)],
    current_user: Annotated[User, Depends(get_current_user)],
    background_tasks: BackgroundTasks,
) -> EvaluationResultResponse:
    """Run RAGAS evaluation on samples."""
    try:
        tenant_id = get_current_tenant_id()

        # Convert request to internal models
        samples = [
            EvaluationSample(
                user_input=s.user_input,
                response=s.response,
                retrieved_contexts=s.retrieved_contexts,
                reference=s.reference,
                metadata=s.metadata,
            )
            for s in request.samples
        ]

        # Map string metrics to enum
        metrics = []
        for m in request.metrics:
            try:
                metrics.append(RAGASMetricType(m))
            except ValueError:
                logger.warning(f"Unknown metric: {m}, skipping")

        if not metrics:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid metrics specified",
            )

        eval_request = RAGASEvaluationRequest(
            samples=samples,
            metrics=metrics,
            thresholds=request.thresholds,
            llm_model=request.llm_model,
            llm_provider=request.llm_provider,
            async_execution=request.async_execution,
            log_to_langfuse=request.log_to_langfuse,
        )

        # Run evaluation
        result = await service.evaluate(
            request=eval_request,
            db=db,
            tenant_id=tenant_id,
        )

        return _convert_result_to_response(result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("RAGAS evaluation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Evaluation failed. Please check your input data and try again.",
        )


@router.post(
    "/evaluate/quick",
    response_model=SampleResultResponse,
    summary="Quick single-sample evaluation",
    description="Quickly evaluate a single RAG response.",
)
async def quick_evaluate(
    request: QuickEvaluateRequest,
    service: Annotated[RAGASService, Depends(get_ragas_service_dep)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SampleResultResponse:
    """Quick evaluation of a single sample."""
    try:
        # Map string metrics to enum
        metrics = []
        for m in request.metrics:
            try:
                metrics.append(RAGASMetricType(m))
            except ValueError:
                logger.warning(f"Unknown metric: {m}, skipping")

        if not metrics:
            metrics = [
                RAGASMetricType.FAITHFULNESS,
                RAGASMetricType.ANSWER_RELEVANCY,
            ]

        quick_request = RAGASQuickEvalRequest(
            user_input=request.user_input,
            response=request.response,
            retrieved_contexts=request.retrieved_contexts,
            reference=request.reference,
            metrics=metrics,
        )

        result = await service.quick_evaluate(quick_request)

        return SampleResultResponse(
            sample_id=result.sample_id,
            metrics=[
                MetricResultResponse(
                    name=m.name,
                    score=m.score,
                    passed=m.passed,
                    threshold=m.threshold,
                    details=m.details,
                    error=m.error,
                )
                for m in result.metrics
            ],
            overall_score=result.overall_score,
            passed=result.passed,
            duration_ms=result.duration_ms,
            error=result.error,
        )

    except Exception as e:
        logger.error("Quick RAGAS evaluation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Evaluation failed. Please check your input data and try again.",
        )


@router.get(
    "/metrics",
    summary="List available metrics",
    description="Get list of all available RAGAS metrics.",
)
async def list_metrics() -> dict[str, Any]:
    """List all available RAGAS metrics."""
    metrics = []
    for metric in RAGASMetricType:
        metrics.append({
            "name": metric.value,
            "description": _get_metric_description(metric),
            "requires_reference": _metric_requires_reference(metric),
        })

    return {
        "metrics": metrics,
        "default_metrics": [
            "faithfulness",
            "answer_relevancy",
            "context_precision",
            "context_recall",
        ],
    }


@router.post(
    "/datasets",
    summary="Create evaluation dataset",
    description="Create a reusable evaluation dataset.",
)
async def create_dataset(
    name: str,
    samples: list[EvaluationSampleRequest],
    description: str | None = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
) -> dict[str, Any]:
    """Create an evaluation dataset."""
    try:
        tenant_id = get_current_tenant_id()

        dataset = EvaluationDataset(
            tenant_id=tenant_id,
            name=name,
            description=description,
            samples=[
                EvaluationSample(
                    user_input=s.user_input,
                    response=s.response,
                    retrieved_contexts=s.retrieved_contexts,
                    reference=s.reference,
                    metadata=s.metadata,
                )
                for s in samples
            ],
            created_by=str(current_user.id) if current_user else None,
        )

        # In a real implementation, persist to database
        return {
            "id": dataset.id,
            "name": dataset.name,
            "sample_count": len(dataset.samples),
            "created_at": dataset.created_at.isoformat(),
        }

    except Exception as e:
        logger.error("Failed to create dataset", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create dataset. Please try again later.",
        )


# =============================================================================
# Helper Functions
# =============================================================================


def _convert_result_to_response(
    result: RAGASEvaluationResult,
) -> EvaluationResultResponse:
    """Convert internal result to API response."""
    return EvaluationResultResponse(
        id=result.id,
        status=result.status.value,
        metrics_evaluated=result.metrics_evaluated,
        model_used=result.model_used,
        sample_results=[
            SampleResultResponse(
                sample_id=sr.sample_id,
                metrics=[
                    MetricResultResponse(
                        name=m.name,
                        score=m.score,
                        passed=m.passed,
                        threshold=m.threshold,
                        details=m.details,
                        error=m.error,
                    )
                    for m in sr.metrics
                ],
                overall_score=sr.overall_score,
                passed=sr.passed,
                duration_ms=sr.duration_ms,
                error=sr.error,
            )
            for sr in result.sample_results
        ],
        aggregate_scores=result.aggregate_scores,
        overall_score=result.overall_score,
        pass_rate=result.pass_rate,
        total_samples=result.total_samples,
        passed_samples=result.passed_samples,
        failed_samples=result.failed_samples,
        error_samples=result.error_samples,
        total_duration_ms=result.total_duration_ms,
        started_at=result.started_at,
        completed_at=result.completed_at,
    )


def _get_metric_description(metric: RAGASMetricType) -> str:
    """Get description for a metric."""
    descriptions = {
        RAGASMetricType.FAITHFULNESS: "Measures if the response is grounded in the retrieved context",
        RAGASMetricType.ANSWER_RELEVANCY: "Measures if the response addresses the user's question",
        RAGASMetricType.CONTEXT_PRECISION: "Measures if retrieved contexts are relevant to the question",
        RAGASMetricType.CONTEXT_RECALL: "Measures if contexts cover the ground truth answer",
        RAGASMetricType.CONTEXT_ENTITIES_RECALL: "Measures entity overlap between context and reference",
        RAGASMetricType.ANSWER_CORRECTNESS: "Measures similarity to ground truth answer",
        RAGASMetricType.ANSWER_SIMILARITY: "Semantic similarity to reference answer",
        RAGASMetricType.FACTUAL_CORRECTNESS: "Measures factual accuracy of the response",
        RAGASMetricType.NOISE_SENSITIVITY: "Measures response stability with noisy context",
        RAGASMetricType.SEMANTIC_SIMILARITY: "General semantic similarity measure",
        RAGASMetricType.HARMFULNESS: "Detects harmful content in response",
        RAGASMetricType.COHERENCE: "Measures response coherence and fluency",
    }
    return descriptions.get(metric, "No description available")


def _metric_requires_reference(metric: RAGASMetricType) -> bool:
    """Check if metric requires a reference answer."""
    reference_metrics = {
        RAGASMetricType.CONTEXT_RECALL,
        RAGASMetricType.CONTEXT_ENTITIES_RECALL,
        RAGASMetricType.ANSWER_CORRECTNESS,
        RAGASMetricType.ANSWER_SIMILARITY,
        RAGASMetricType.FACTUAL_CORRECTNESS,
    }
    return metric in reference_metrics
