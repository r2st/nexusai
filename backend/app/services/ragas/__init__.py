"""RAGAS evaluation service.

RAGAS (Retrieval-Augmented Generation Assessment) provides metrics to evaluate
RAG pipelines on both component and end-to-end levels.

Metrics included:
- Faithfulness: How well the response is grounded in the context
- Answer Relevancy: How relevant the response is to the question
- Context Precision: How precise the retrieved contexts are
- Context Recall: How well the contexts cover the reference answer
- Answer Correctness: Similarity to ground truth answer
- Factual Correctness: Accuracy of facts in the response

Usage:
    from app.services.ragas import RAGASService, EvaluationSample

    service = await get_ragas_service()

    sample = EvaluationSample(
        user_input="What is Python?",
        response="Python is a programming language.",
        retrieved_contexts=["Python is a high-level programming language."],
    )

    result = await service.quick_evaluate(
        RAGASQuickEvalRequest(
            user_input=sample.user_input,
            response=sample.response,
            retrieved_contexts=sample.retrieved_contexts,
        )
    )
"""

from app.services.ragas.models import (
    EvaluationDataset,
    EvaluationSample,
    EvaluationStatus,
    MetricResult,
    RAGASEvaluationRequest,
    RAGASEvaluationResult,
    RAGASMetricType,
    RAGASQuickEvalRequest,
    SampleResult,
)
from app.services.ragas.config import (
    RAGASConfig,
    get_ragas_config,
)
from app.services.ragas.service import (
    RAGASService,
    get_ragas_service,
    RAGAS_AVAILABLE,
)

__all__ = [
    # Models
    "EvaluationDataset",
    "EvaluationSample",
    "EvaluationStatus",
    "MetricResult",
    "RAGASEvaluationRequest",
    "RAGASEvaluationResult",
    "RAGASMetricType",
    "RAGASQuickEvalRequest",
    "SampleResult",
    # Config
    "RAGASConfig",
    "get_ragas_config",
    # Service
    "RAGASService",
    "get_ragas_service",
    "RAGAS_AVAILABLE",
]
