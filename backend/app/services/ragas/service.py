"""RAGAS evaluation service.

Provides RAG evaluation using the RAGAS framework with support for:
- Core metrics: Faithfulness, Answer Relevancy, Context Precision, Context Recall
- LLM-based evaluation with multiple provider support
- Langfuse integration for observability
- Async batch processing
"""

import asyncio
from datetime import datetime, UTC
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ragas.config import RAGASConfig, get_ragas_config
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
from app.services.observability.langfuse_client import LangfuseClient

logger = structlog.get_logger()

# Try to import ragas, provide fallback if not installed
try:
    from ragas import EvaluationDataset as RagasDataset
    from ragas import evaluate
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper
    from ragas.metrics import (
        Faithfulness,
        ResponseRelevancy,
        LLMContextPrecisionWithReference,
        LLMContextRecall,
        FactualCorrectness,
        SemanticSimilarity,
        AnswerCorrectness,
    )

    RAGAS_AVAILABLE = True
except ImportError:
    RAGAS_AVAILABLE = False
    logger.warning("RAGAS package not installed, using fallback implementation")


class RAGASService:
    """
    RAGAS evaluation service.

    Provides comprehensive RAG pipeline evaluation with:
    - Multiple metric support (faithfulness, relevancy, precision, recall)
    - Multi-provider LLM support (OpenAI, Anthropic, Google, Ollama)
    - Langfuse observability integration
    - Async batch processing
    - Result persistence
    """

    def __init__(
        self,
        config: RAGASConfig | None = None,
        langfuse_client: LangfuseClient | None = None,
    ):
        """
        Initialize RAGAS service.

        Args:
            config: RAGAS configuration
            langfuse_client: Optional Langfuse client for observability
        """
        self.config = config or get_ragas_config()
        self._langfuse = langfuse_client
        self._llm = None
        self._embeddings = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize LLM and embeddings for evaluation."""
        if self._initialized:
            return

        if not RAGAS_AVAILABLE:
            logger.warning("RAGAS not available, using fallback implementation")
            self._initialized = True
            return

        try:
            # Initialize LLM based on provider
            self._llm = await self._create_llm()
            self._embeddings = await self._create_embeddings()
            self._initialized = True
            logger.info(
                "RAGAS service initialized",
                llm_provider=self.config.llm_provider,
                llm_model=self.config.llm_model,
                embeddings_model=self.config.embeddings_model,
            )
        except Exception as e:
            logger.error("Failed to initialize RAGAS service", error=str(e))
            raise

    async def _create_llm(self) -> Any:
        """Create LLM wrapper based on provider."""
        provider = self.config.llm_provider.lower()
        model = self.config.llm_model

        if provider == "openai":
            from langchain_openai import ChatOpenAI

            llm = ChatOpenAI(
                model=model,
                temperature=self.config.llm_temperature,
            )
            return LangchainLLMWrapper(llm)

        elif provider == "anthropic":
            from langchain_anthropic import ChatAnthropic

            llm = ChatAnthropic(
                model=model,
                temperature=self.config.llm_temperature,
            )
            return LangchainLLMWrapper(llm)

        elif provider == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI

            llm = ChatGoogleGenerativeAI(
                model=model,
                temperature=self.config.llm_temperature,
            )
            return LangchainLLMWrapper(llm)

        elif provider == "ollama":
            from langchain_ollama import ChatOllama

            llm = ChatOllama(
                model=model,
                temperature=self.config.llm_temperature,
            )
            return LangchainLLMWrapper(llm)

        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    async def _create_embeddings(self) -> Any:
        """Create embeddings wrapper based on provider."""
        provider = self.config.embeddings_provider.lower()
        model = self.config.embeddings_model

        if provider == "openai":
            from langchain_openai import OpenAIEmbeddings

            embeddings = OpenAIEmbeddings(model=model)
            return LangchainEmbeddingsWrapper(embeddings)

        elif provider == "ollama":
            from langchain_ollama import OllamaEmbeddings

            embeddings = OllamaEmbeddings(model=model)
            return LangchainEmbeddingsWrapper(embeddings)

        else:
            # Default to OpenAI
            from langchain_openai import OpenAIEmbeddings

            embeddings = OpenAIEmbeddings(model=model)
            return LangchainEmbeddingsWrapper(embeddings)

    def _get_metric_instance(self, metric_type: RAGASMetricType) -> Any:
        """Get RAGAS metric instance by type."""
        if not RAGAS_AVAILABLE:
            return None

        metric_map = {
            RAGASMetricType.FAITHFULNESS: Faithfulness,
            RAGASMetricType.ANSWER_RELEVANCY: ResponseRelevancy,
            RAGASMetricType.CONTEXT_PRECISION: LLMContextPrecisionWithReference,
            RAGASMetricType.CONTEXT_RECALL: LLMContextRecall,
            RAGASMetricType.FACTUAL_CORRECTNESS: FactualCorrectness,
            RAGASMetricType.SEMANTIC_SIMILARITY: SemanticSimilarity,
            RAGASMetricType.ANSWER_CORRECTNESS: AnswerCorrectness,
        }

        metric_class = metric_map.get(metric_type)
        if metric_class:
            return metric_class()
        return None

    async def evaluate(
        self,
        request: RAGASEvaluationRequest,
        db: AsyncSession | None = None,
        tenant_id: str | None = None,
    ) -> RAGASEvaluationResult:
        """
        Run RAGAS evaluation on samples.

        Args:
            request: Evaluation request with samples and configuration
            db: Optional database session for persistence
            tenant_id: Optional tenant ID for multi-tenancy

        Returns:
            RAGASEvaluationResult with all metrics and scores
        """
        await self.initialize()

        result = RAGASEvaluationResult(
            tenant_id=tenant_id,
            metrics_evaluated=[m.value for m in request.metrics],
            model_used=request.llm_model,
            embeddings_model=request.embeddings_model,
            started_at=datetime.now(UTC),
        )

        try:
            result.status = EvaluationStatus.RUNNING

            if RAGAS_AVAILABLE:
                # Use native RAGAS evaluation
                result = await self._evaluate_with_ragas(request, result)
            else:
                # Use fallback implementation
                result = await self._evaluate_fallback(request, result)

            result.status = EvaluationStatus.COMPLETED
            result.completed_at = datetime.now(UTC)
            result.total_duration_ms = (
                result.completed_at - result.started_at
            ).total_seconds() * 1000

            # Compute aggregate scores
            result.compute_aggregates()

            # Log to Langfuse
            if request.log_to_langfuse and self._langfuse:
                await self._log_to_langfuse(result)

            # Persist results
            if request.persist_results and db:
                await self._persist_result(db, result)

            logger.info(
                "RAGAS evaluation completed",
                evaluation_id=result.id,
                total_samples=result.total_samples,
                overall_score=result.overall_score,
                pass_rate=result.pass_rate,
            )

        except Exception as e:
            result.status = EvaluationStatus.FAILED
            result.metadata["error"] = str(e)
            logger.error("RAGAS evaluation failed", error=str(e))
            raise

        return result

    async def _evaluate_with_ragas(
        self,
        request: RAGASEvaluationRequest,
        result: RAGASEvaluationResult,
    ) -> RAGASEvaluationResult:
        """Evaluate using native RAGAS library."""
        # Prepare metrics
        metrics = []
        for metric_type in request.metrics:
            metric = self._get_metric_instance(metric_type)
            if metric:
                metrics.append(metric)

        if not metrics:
            raise ValueError("No valid metrics specified")

        # Convert samples to RAGAS format
        ragas_data = []
        for sample in request.samples:
            ragas_data.append({
                "user_input": sample.user_input,
                "response": sample.response,
                "retrieved_contexts": sample.retrieved_contexts,
                "reference": sample.reference or "",
            })

        # Create RAGAS dataset
        ragas_dataset = RagasDataset.from_list(ragas_data)

        # Run evaluation
        eval_result = evaluate(
            dataset=ragas_dataset,
            metrics=metrics,
            llm=self._llm,
            embeddings=self._embeddings,
        )

        # Convert results
        for idx, sample in enumerate(request.samples):
            sample_metrics = []

            for metric_type in request.metrics:
                metric_name = metric_type.value
                score = eval_result.get(metric_name, 0.0)

                # Handle per-sample scores if available
                if isinstance(score, list) and idx < len(score):
                    score = score[idx]
                elif isinstance(score, dict) and str(idx) in score:
                    score = score[str(idx)]

                threshold = request.thresholds.get(metric_name, 0.7)
                passed = score >= threshold

                sample_metrics.append(
                    MetricResult(
                        name=metric_name,
                        score=float(score) if score else 0.0,
                        passed=passed,
                        threshold=threshold,
                    )
                )

            # Calculate overall sample score
            valid_scores = [m.score for m in sample_metrics if m.error is None]
            overall_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0.0
            all_passed = all(m.passed for m in sample_metrics)

            sample_result = SampleResult(
                sample_id=sample.id,
                metrics=sample_metrics,
                overall_score=overall_score,
                passed=all_passed,
            )

            result.add_sample_result(sample_result)

        return result

    async def _evaluate_fallback(
        self,
        request: RAGASEvaluationRequest,
        result: RAGASEvaluationResult,
    ) -> RAGASEvaluationResult:
        """Fallback evaluation when RAGAS is not available."""
        logger.warning("Using fallback RAGAS evaluation (limited metrics)")

        for sample in request.samples:
            sample_metrics = []
            start_time = datetime.now(UTC)

            for metric_type in request.metrics:
                try:
                    score = await self._compute_fallback_metric(
                        metric_type, sample
                    )
                    threshold = request.thresholds.get(metric_type.value, 0.7)

                    sample_metrics.append(
                        MetricResult(
                            name=metric_type.value,
                            score=score,
                            passed=score >= threshold,
                            threshold=threshold,
                            details={"method": "fallback"},
                        )
                    )
                except Exception as e:
                    sample_metrics.append(
                        MetricResult(
                            name=metric_type.value,
                            score=0.0,
                            passed=False,
                            error=str(e),
                        )
                    )

            # Calculate overall sample score
            valid_scores = [m.score for m in sample_metrics if m.error is None]
            overall_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0.0
            all_passed = all(m.passed for m in sample_metrics if m.error is None)

            duration_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

            sample_result = SampleResult(
                sample_id=sample.id,
                metrics=sample_metrics,
                overall_score=overall_score,
                passed=all_passed,
                duration_ms=duration_ms,
            )

            result.add_sample_result(sample_result)

        return result

    async def _compute_fallback_metric(
        self,
        metric_type: RAGASMetricType,
        sample: EvaluationSample,
    ) -> float:
        """Compute metric using fallback implementation."""
        if metric_type == RAGASMetricType.FAITHFULNESS:
            return await self._compute_faithfulness_fallback(sample)
        elif metric_type == RAGASMetricType.ANSWER_RELEVANCY:
            return await self._compute_relevancy_fallback(sample)
        elif metric_type == RAGASMetricType.CONTEXT_PRECISION:
            return await self._compute_context_precision_fallback(sample)
        elif metric_type == RAGASMetricType.CONTEXT_RECALL:
            return await self._compute_context_recall_fallback(sample)
        else:
            # Default to a moderate score for unsupported metrics
            return 0.5

    async def _compute_faithfulness_fallback(
        self, sample: EvaluationSample
    ) -> float:
        """
        Compute faithfulness using simple heuristics.

        Faithfulness measures if the response is grounded in the context.
        """
        if not sample.retrieved_contexts:
            return 0.0

        response_lower = sample.response.lower()
        context_text = " ".join(sample.retrieved_contexts).lower()

        # Simple word overlap check
        response_words = set(response_lower.split())
        context_words = set(context_text.split())

        # Remove common stop words
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                      "being", "have", "has", "had", "do", "does", "did", "will",
                      "would", "could", "should", "may", "might", "must", "shall",
                      "to", "of", "in", "for", "on", "with", "at", "by", "from",
                      "as", "into", "through", "during", "before", "after", "above",
                      "below", "between", "under", "again", "further", "then", "once",
                      "here", "there", "when", "where", "why", "how", "all", "each",
                      "few", "more", "most", "other", "some", "such", "no", "nor",
                      "not", "only", "own", "same", "so", "than", "too", "very",
                      "can", "just", "should", "now", "and", "but", "or", "if", "it"}

        response_words = response_words - stop_words
        context_words = context_words - stop_words

        if not response_words:
            return 0.5

        overlap = response_words.intersection(context_words)
        overlap_ratio = len(overlap) / len(response_words)

        return min(overlap_ratio * 1.2, 1.0)  # Slight boost, cap at 1.0

    async def _compute_relevancy_fallback(
        self, sample: EvaluationSample
    ) -> float:
        """
        Compute answer relevancy using simple heuristics.

        Answer relevancy measures if the response addresses the question.
        """
        query_lower = sample.user_input.lower()
        response_lower = sample.response.lower()

        # Extract key terms from query
        query_words = set(query_lower.split())
        response_words = set(response_lower.split())

        stop_words = {"what", "where", "when", "who", "why", "how", "is", "are",
                      "the", "a", "an", "can", "could", "would", "should", "do",
                      "does", "did", "will", "have", "has", "had", "?"}

        query_terms = query_words - stop_words
        response_terms = response_words - stop_words

        if not query_terms:
            return 0.5

        overlap = query_terms.intersection(response_terms)
        overlap_ratio = len(overlap) / len(query_terms)

        # Check if response is not empty and has reasonable length
        length_factor = min(len(sample.response) / 100, 1.0)

        return (overlap_ratio * 0.7 + length_factor * 0.3)

    async def _compute_context_precision_fallback(
        self, sample: EvaluationSample
    ) -> float:
        """
        Compute context precision using simple heuristics.

        Context precision measures if retrieved contexts are relevant.
        """
        if not sample.retrieved_contexts:
            return 0.0

        query_lower = sample.user_input.lower()
        query_words = set(query_lower.split())

        stop_words = {"what", "where", "when", "who", "why", "how", "is", "are",
                      "the", "a", "an", "?"}
        query_terms = query_words - stop_words

        if not query_terms:
            return 0.5

        relevant_count = 0
        for ctx in sample.retrieved_contexts:
            ctx_lower = ctx.lower()
            ctx_words = set(ctx_lower.split())

            overlap = query_terms.intersection(ctx_words)
            if len(overlap) >= len(query_terms) * 0.3:  # 30% overlap threshold
                relevant_count += 1

        return relevant_count / len(sample.retrieved_contexts)

    async def _compute_context_recall_fallback(
        self, sample: EvaluationSample
    ) -> float:
        """
        Compute context recall using simple heuristics.

        Context recall measures if contexts cover the reference answer.
        """
        if not sample.reference:
            # Without reference, assume moderate recall
            return 0.5

        if not sample.retrieved_contexts:
            return 0.0

        reference_lower = sample.reference.lower()
        context_text = " ".join(sample.retrieved_contexts).lower()

        reference_words = set(reference_lower.split())
        context_words = set(context_text.split())

        stop_words = {"the", "a", "an", "is", "are", "was", "were", "to", "of",
                      "in", "for", "on", "with", "at", "by", "from", "and", "or"}

        reference_terms = reference_words - stop_words
        context_terms = context_words - stop_words

        if not reference_terms:
            return 0.5

        overlap = reference_terms.intersection(context_terms)
        return len(overlap) / len(reference_terms)

    async def quick_evaluate(
        self,
        request: RAGASQuickEvalRequest,
    ) -> SampleResult:
        """
        Quick evaluation of a single sample.

        Args:
            request: Quick evaluation request

        Returns:
            SampleResult with metrics
        """
        await self.initialize()

        sample = EvaluationSample(
            user_input=request.user_input,
            response=request.response,
            retrieved_contexts=request.retrieved_contexts,
            reference=request.reference,
        )

        full_request = RAGASEvaluationRequest(
            samples=[sample],
            metrics=request.metrics,
            llm_model=request.llm_model,
            log_to_langfuse=False,
            persist_results=False,
        )

        result = await self.evaluate(full_request)

        if result.sample_results:
            return result.sample_results[0]

        return SampleResult(
            sample_id=sample.id,
            error="Evaluation failed",
        )

    async def evaluate_dataset(
        self,
        dataset: EvaluationDataset,
        metrics: list[RAGASMetricType] | None = None,
        db: AsyncSession | None = None,
    ) -> RAGASEvaluationResult:
        """
        Evaluate a dataset.

        Args:
            dataset: Dataset to evaluate
            metrics: Optional metrics override (uses dataset defaults if None)
            db: Optional database session

        Returns:
            RAGASEvaluationResult
        """
        request = RAGASEvaluationRequest(
            samples=dataset.samples,
            metrics=metrics or dataset.default_metrics,
            thresholds=dataset.metric_thresholds,
        )

        return await self.evaluate(
            request,
            db=db,
            tenant_id=dataset.tenant_id,
        )

    async def _log_to_langfuse(self, result: RAGASEvaluationResult) -> None:
        """Log evaluation result to Langfuse."""
        if not self._langfuse:
            return

        try:
            trace = self._langfuse.create_trace(
                name=self.config.langfuse_trace_name,
                metadata={
                    "evaluation_id": result.id,
                    "metrics_evaluated": result.metrics_evaluated,
                    "total_samples": result.total_samples,
                    "overall_score": result.overall_score,
                    "pass_rate": result.pass_rate,
                },
                tags=["ragas", "evaluation"],
            )

            # Log aggregate scores
            for metric_name, score in result.aggregate_scores.items():
                self._langfuse.log_quality_evaluation(
                    trace=trace,
                    evaluation_name=f"ragas_{metric_name}",
                    score=score,
                    comment=f"RAGAS {metric_name} aggregate score",
                )

            self._langfuse.end_trace(trace, status="success")
            self._langfuse.flush()

            logger.debug(
                "Logged RAGAS evaluation to Langfuse",
                evaluation_id=result.id,
            )

        except Exception as e:
            logger.warning("Failed to log to Langfuse", error=str(e))

    async def _persist_result(
        self,
        db: AsyncSession,
        result: RAGASEvaluationResult,
    ) -> None:
        """Persist evaluation result to database."""
        # Implementation depends on database model
        # For now, just log
        logger.debug(
            "Would persist RAGAS result",
            evaluation_id=result.id,
            total_samples=result.total_samples,
        )


# Global service instance
_ragas_service: RAGASService | None = None


async def get_ragas_service(
    config: RAGASConfig | None = None,
    langfuse_client: LangfuseClient | None = None,
) -> RAGASService:
    """Get or create the global RAGAS service."""
    global _ragas_service

    if _ragas_service is None:
        _ragas_service = RAGASService(
            config=config,
            langfuse_client=langfuse_client,
        )
        await _ragas_service.initialize()

    return _ragas_service
