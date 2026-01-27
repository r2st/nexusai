"""Phoenix (Arize AI) integration for hallucination detection and LLM observability."""

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, AsyncGenerator
from uuid import uuid4

import structlog

from app.services.observability.config import ObservabilityConfig

logger = structlog.get_logger()

# Try to import Phoenix, but don't fail if not installed
try:
    import phoenix as px
    from phoenix.otel import register
    from opentelemetry import trace as otel_trace
    from opentelemetry.sdk.trace import TracerProvider
    PHOENIX_AVAILABLE = True
except ImportError:
    PHOENIX_AVAILABLE = False
    px = None
    register = None
    otel_trace = None
    TracerProvider = None

# Try to import Phoenix evals
try:
    from phoenix.evals import (
        HallucinationEvaluator,
        QAEvaluator,
        RelevanceEvaluator,
        llm_classify,
        run_evals,
    )
    from phoenix.evals.models import OpenAIModel, AnthropicModel
    PHOENIX_EVALS_AVAILABLE = True
except ImportError:
    PHOENIX_EVALS_AVAILABLE = False
    HallucinationEvaluator = None
    QAEvaluator = None
    RelevanceEvaluator = None
    llm_classify = None
    run_evals = None
    OpenAIModel = None
    AnthropicModel = None


@dataclass
class HallucinationResult:
    """Result of a hallucination check."""

    id: str = field(default_factory=lambda: str(uuid4()))
    is_hallucination: bool = False
    hallucination_score: float = 0.0  # 0.0 = no hallucination, 1.0 = full hallucination
    confidence: float = 0.0
    explanation: str = ""
    grounding_score: float = 1.0  # How well grounded in context (1.0 = fully grounded)
    factuality_score: float = 1.0  # Factual accuracy score
    relevance_score: float = 1.0  # Relevance to the query
    detected_issues: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def passed(self) -> bool:
        """Check if the response passed hallucination detection."""
        return not self.is_hallucination

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "is_hallucination": self.is_hallucination,
            "hallucination_score": self.hallucination_score,
            "confidence": self.confidence,
            "explanation": self.explanation,
            "grounding_score": self.grounding_score,
            "factuality_score": self.factuality_score,
            "relevance_score": self.relevance_score,
            "detected_issues": self.detected_issues,
            "passed": self.passed,
            "evaluated_at": self.evaluated_at.isoformat(),
        }


@dataclass
class RAGContext:
    """Context for RAG-based hallucination detection."""

    query: str
    response: str
    retrieved_documents: list[str] = field(default_factory=list)
    document_metadata: list[dict[str, Any]] = field(default_factory=list)


class PhoenixClient:
    """
    Phoenix client for hallucination detection and LLM observability.

    Provides:
    - Hallucination detection for LLM responses
    - RAG response grounding verification
    - QA evaluation
    - Relevance scoring
    - Trace collection and analysis
    """

    def __init__(self, config: ObservabilityConfig | None = None):
        """
        Initialize Phoenix client.

        Args:
            config: Observability configuration
        """
        self.config = config or ObservabilityConfig()
        self._enabled = False
        self._tracer = None
        self._eval_model = None
        self._local_metrics: dict[str, list[dict[str, Any]]] = {
            "hallucination_checks": [],
            "qa_evaluations": [],
            "relevance_checks": [],
        }

    async def initialize(self) -> None:
        """Initialize the Phoenix client."""
        if not self.config.phoenix_enabled:
            logger.info("Phoenix disabled by configuration")
            return

        if not PHOENIX_AVAILABLE:
            logger.warning("Phoenix package not installed, hallucination detection will use fallback")
            return

        try:
            # Configure Phoenix endpoint if provided
            if self.config.phoenix_endpoint:
                # Register with Phoenix cloud or self-hosted
                tracer_provider = register(
                    project_name=self.config.phoenix_project_name,
                    endpoint=self.config.phoenix_endpoint,
                    headers={"api_key": self.config.phoenix_api_key} if self.config.phoenix_api_key else None,
                )
            else:
                # Start local Phoenix session for development
                px.launch_app()
                tracer_provider = register(project_name=self.config.phoenix_project_name)

            self._tracer = otel_trace.get_tracer(__name__)
            self._enabled = True

            # Initialize evaluation model if evals are available
            if PHOENIX_EVALS_AVAILABLE and self.config.hallucination_detection_enabled:
                await self._initialize_eval_model()

            logger.info(
                "Phoenix client initialized",
                endpoint=self.config.phoenix_endpoint or "local",
                project=self.config.phoenix_project_name,
                hallucination_detection=self.config.hallucination_detection_enabled,
            )

        except Exception as e:
            logger.error("Failed to initialize Phoenix", error=str(e))

    async def _initialize_eval_model(self) -> None:
        """Initialize the model used for evaluations."""
        if not PHOENIX_EVALS_AVAILABLE:
            return

        try:
            model_name = self.config.hallucination_eval_model

            # Auto-detect based on available API keys
            if not model_name:
                import os
                if os.getenv("OPENAI_API_KEY"):
                    model_name = "openai"
                elif os.getenv("ANTHROPIC_API_KEY"):
                    model_name = "anthropic"

            if model_name == "openai" or model_name.startswith("gpt"):
                self._eval_model = OpenAIModel(
                    model=model_name if model_name.startswith("gpt") else "gpt-4o-mini"
                )
            elif model_name == "anthropic" or model_name.startswith("claude"):
                self._eval_model = AnthropicModel(
                    model=model_name if model_name.startswith("claude") else "claude-3-haiku-20240307"
                )

            logger.info("Phoenix eval model initialized", model=model_name)

        except Exception as e:
            logger.warning("Failed to initialize Phoenix eval model", error=str(e))

    async def close(self) -> None:
        """Close the Phoenix client."""
        if self._enabled:
            try:
                # Flush any pending traces
                if PHOENIX_AVAILABLE:
                    pass  # Phoenix handles cleanup automatically
            except Exception as e:
                logger.error("Failed to close Phoenix", error=str(e))

        logger.info("Phoenix client closed")

    async def check_hallucination(
        self,
        query: str,
        response: str,
        context: list[str] | None = None,
        reference: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> HallucinationResult:
        """
        Check if an LLM response contains hallucinations.

        Args:
            query: The user's query/question
            response: The LLM's response to check
            context: Retrieved documents/context used for RAG
            reference: Ground truth reference (if available)
            metadata: Additional metadata

        Returns:
            HallucinationResult with detection details
        """
        result = HallucinationResult(
            metadata=metadata or {},
        )

        try:
            if self._enabled and PHOENIX_EVALS_AVAILABLE and self._eval_model:
                # Use Phoenix evals for hallucination detection
                result = await self._phoenix_hallucination_check(
                    query, response, context, reference, result
                )
            else:
                # Fallback to heuristic-based detection
                result = await self._heuristic_hallucination_check(
                    query, response, context, reference, result
                )

            # Log the check
            self._local_metrics["hallucination_checks"].append({
                "id": result.id,
                "is_hallucination": result.is_hallucination,
                "hallucination_score": result.hallucination_score,
                "grounding_score": result.grounding_score,
                "timestamp": result.evaluated_at.isoformat(),
            })

            logger.debug(
                "Hallucination check completed",
                result_id=result.id,
                is_hallucination=result.is_hallucination,
                score=result.hallucination_score,
            )

        except Exception as e:
            logger.error("Hallucination check failed", error=str(e))
            result.detected_issues.append(f"Check failed: {str(e)}")

        return result

    async def _phoenix_hallucination_check(
        self,
        query: str,
        response: str,
        context: list[str] | None,
        reference: str | None,
        result: HallucinationResult,
    ) -> HallucinationResult:
        """Perform hallucination check using Phoenix evals."""
        import pandas as pd

        # Prepare data for evaluation
        combined_context = "\n\n".join(context) if context else ""

        eval_data = pd.DataFrame([{
            "input": query,
            "output": response,
            "context": combined_context,
            "reference": reference or "",
        }])

        # Run hallucination evaluation
        hallucination_evaluator = HallucinationEvaluator(self._eval_model)
        hallucination_results = await asyncio.to_thread(
            run_evals,
            dataframe=eval_data,
            evaluators=[hallucination_evaluator],
            provide_explanation=True,
        )

        # Parse hallucination result
        if not hallucination_results.empty:
            hal_row = hallucination_results.iloc[0]
            hal_label = hal_row.get("label", "")
            hal_score = hal_row.get("score", 0.0)
            hal_explanation = hal_row.get("explanation", "")

            result.is_hallucination = hal_label.lower() in ["hallucinated", "factual"]
            result.hallucination_score = 1.0 - hal_score if hal_score else 0.5
            result.explanation = hal_explanation
            result.confidence = abs(hal_score - 0.5) * 2 if hal_score else 0.5

        # Run relevance evaluation if context is provided
        if context:
            relevance_evaluator = RelevanceEvaluator(self._eval_model)
            relevance_results = await asyncio.to_thread(
                run_evals,
                dataframe=eval_data,
                evaluators=[relevance_evaluator],
                provide_explanation=True,
            )

            if not relevance_results.empty:
                rel_row = relevance_results.iloc[0]
                result.relevance_score = rel_row.get("score", 1.0)

        # Run QA evaluation if reference is provided
        if reference:
            qa_evaluator = QAEvaluator(self._eval_model)
            qa_results = await asyncio.to_thread(
                run_evals,
                dataframe=eval_data,
                evaluators=[qa_evaluator],
                provide_explanation=True,
            )

            if not qa_results.empty:
                qa_row = qa_results.iloc[0]
                result.factuality_score = qa_row.get("score", 1.0)

        # Calculate grounding score based on context overlap
        if context:
            result.grounding_score = self._calculate_grounding_score(response, context)

        # Determine if hallucination based on threshold
        result.is_hallucination = (
            result.hallucination_score > (1 - self.config.hallucination_score_threshold)
        )

        # Add detected issues
        if result.is_hallucination:
            result.detected_issues.append("Response may contain hallucinated content")
        if result.grounding_score < 0.5:
            result.detected_issues.append("Response poorly grounded in provided context")
        if result.relevance_score < 0.5:
            result.detected_issues.append("Response may not be relevant to the query")

        return result

    async def _heuristic_hallucination_check(
        self,
        query: str,
        response: str,
        context: list[str] | None,
        reference: str | None,
        result: HallucinationResult,
    ) -> HallucinationResult:
        """Perform heuristic-based hallucination check when Phoenix evals are unavailable."""
        issues = []

        # Check for common hallucination patterns
        hallucination_indicators = [
            # Uncertainty markers that might indicate fabrication
            ("I think", 0.1),
            ("I believe", 0.1),
            ("probably", 0.05),
            ("might be", 0.1),
            ("could be", 0.05),
            # Over-specific claims without context
            ("exactly", 0.1),
            ("precisely", 0.1),
            # Citation patterns without actual citations
            ("according to studies", 0.15),
            ("research shows", 0.1),
            ("experts say", 0.1),
        ]

        hallucination_score = 0.0
        for pattern, weight in hallucination_indicators:
            if pattern.lower() in response.lower():
                hallucination_score += weight
                if weight >= 0.1:
                    issues.append(f"Contains potentially unsupported claim marker: '{pattern}'")

        # Cap the score
        hallucination_score = min(hallucination_score, 1.0)

        # Check grounding against context
        grounding_score = 1.0
        if context:
            grounding_score = self._calculate_grounding_score(response, context)
            if grounding_score < 0.3:
                issues.append("Response contains significant content not found in context")
                hallucination_score = max(hallucination_score, 0.5)

        # Check against reference if available
        factuality_score = 1.0
        if reference:
            factuality_score = self._calculate_similarity(response, reference)
            if factuality_score < 0.3:
                issues.append("Response significantly differs from reference")
                hallucination_score = max(hallucination_score, 0.4)

        # Calculate relevance
        relevance_score = self._calculate_similarity(query, response)

        result.hallucination_score = hallucination_score
        result.grounding_score = grounding_score
        result.factuality_score = factuality_score
        result.relevance_score = relevance_score
        result.confidence = 0.5  # Lower confidence for heuristic method
        result.detected_issues = issues
        result.is_hallucination = hallucination_score > (1 - self.config.hallucination_score_threshold)
        result.explanation = (
            "Heuristic-based detection (Phoenix evals unavailable). "
            f"Found {len(issues)} potential issues."
        )

        return result

    def _calculate_grounding_score(self, response: str, context: list[str]) -> float:
        """Calculate how well the response is grounded in the context."""
        if not context:
            return 1.0

        response_lower = response.lower()
        combined_context = " ".join(context).lower()

        # Simple word overlap scoring
        response_words = set(response_lower.split())
        context_words = set(combined_context.split())

        # Remove common stop words
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "must", "shall", "can", "need", "dare",
            "ought", "used", "to", "of", "in", "for", "on", "with", "at", "by",
            "from", "as", "into", "through", "during", "before", "after", "above",
            "below", "between", "under", "again", "further", "then", "once",
            "and", "but", "or", "nor", "so", "yet", "both", "either", "neither",
            "not", "only", "own", "same", "than", "too", "very", "just",
        }

        response_words = response_words - stop_words
        context_words = context_words - stop_words

        if not response_words:
            return 1.0

        overlap = len(response_words & context_words)
        score = overlap / len(response_words)

        return min(score, 1.0)

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity."""
        if not text1 or not text2:
            return 1.0

        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 1.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    async def check_rag_response(
        self,
        rag_context: RAGContext,
        metadata: dict[str, Any] | None = None,
    ) -> HallucinationResult:
        """
        Check a RAG response for hallucinations and grounding.

        Args:
            rag_context: RAG context with query, response, and documents
            metadata: Additional metadata

        Returns:
            HallucinationResult with grounding verification
        """
        return await self.check_hallucination(
            query=rag_context.query,
            response=rag_context.response,
            context=rag_context.retrieved_documents,
            metadata={
                **(metadata or {}),
                "document_count": len(rag_context.retrieved_documents),
                "check_type": "rag_grounding",
            },
        )

    async def evaluate_qa_pair(
        self,
        question: str,
        answer: str,
        expected_answer: str | None = None,
        context: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Evaluate a question-answer pair.

        Args:
            question: The question
            answer: The generated answer
            expected_answer: Expected/reference answer
            context: Supporting context

        Returns:
            Evaluation results with scores
        """
        result = {
            "question": question,
            "answer": answer,
            "scores": {},
            "passed": True,
            "issues": [],
        }

        # Run hallucination check
        hal_result = await self.check_hallucination(
            query=question,
            response=answer,
            context=context,
            reference=expected_answer,
        )

        result["scores"]["hallucination"] = 1.0 - hal_result.hallucination_score
        result["scores"]["grounding"] = hal_result.grounding_score
        result["scores"]["relevance"] = hal_result.relevance_score
        result["scores"]["factuality"] = hal_result.factuality_score

        result["passed"] = not hal_result.is_hallucination
        result["issues"] = hal_result.detected_issues
        result["explanation"] = hal_result.explanation

        # Log evaluation
        self._local_metrics["qa_evaluations"].append({
            "question": question[:100],
            "passed": result["passed"],
            "scores": result["scores"],
            "timestamp": datetime.now(UTC).isoformat(),
        })

        return result

    @asynccontextmanager
    async def trace_llm_call(
        self,
        name: str,
        model: str,
        metadata: dict[str, Any] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Context manager for tracing LLM calls with Phoenix.

        Args:
            name: Name of the operation
            model: Model being used
            metadata: Additional metadata

        Yields:
            Trace context dictionary
        """
        trace_context = {
            "trace_id": str(uuid4()),
            "name": name,
            "model": model,
            "start_time": datetime.now(UTC),
            "metadata": metadata or {},
        }

        if self._enabled and self._tracer:
            with self._tracer.start_as_current_span(name) as span:
                span.set_attribute("model", model)
                if metadata:
                    for key, value in metadata.items():
                        span.set_attribute(f"metadata.{key}", str(value))

                try:
                    yield trace_context
                    span.set_attribute("status", "success")
                except Exception as e:
                    span.set_attribute("status", "error")
                    span.set_attribute("error", str(e))
                    raise
        else:
            yield trace_context

    def get_metrics(self) -> dict[str, Any]:
        """Get collected metrics."""
        hallucination_checks = self._local_metrics["hallucination_checks"]
        qa_evaluations = self._local_metrics["qa_evaluations"]

        total_checks = len(hallucination_checks)
        hallucinations_found = sum(1 for c in hallucination_checks if c["is_hallucination"])

        return {
            "total_hallucination_checks": total_checks,
            "hallucinations_detected": hallucinations_found,
            "hallucination_rate": hallucinations_found / total_checks if total_checks > 0 else 0.0,
            "avg_hallucination_score": (
                sum(c["hallucination_score"] for c in hallucination_checks) / total_checks
                if total_checks > 0 else 0.0
            ),
            "avg_grounding_score": (
                sum(c["grounding_score"] for c in hallucination_checks) / total_checks
                if total_checks > 0 else 0.0
            ),
            "qa_evaluations": len(qa_evaluations),
            "qa_pass_rate": (
                sum(1 for e in qa_evaluations if e["passed"]) / len(qa_evaluations)
                if qa_evaluations else 0.0
            ),
            "recent_checks": hallucination_checks[-10:],
            "recent_evaluations": qa_evaluations[-10:],
        }


# Global client instance
_phoenix_client: PhoenixClient | None = None


async def get_phoenix_client(
    config: ObservabilityConfig | None = None,
) -> PhoenixClient:
    """Get or create the global Phoenix client."""
    global _phoenix_client

    if _phoenix_client is None:
        _phoenix_client = PhoenixClient(config=config)
        await _phoenix_client.initialize()

    return _phoenix_client
