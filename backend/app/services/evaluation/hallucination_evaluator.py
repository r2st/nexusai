"""Hallucination evaluators for assessing LLM output quality using Phoenix."""


import structlog

from app.services.evaluation.models import (
    QualityMetric,
    TestCase,
    TestCaseType,
)
from app.services.evaluation.evaluator import BaseEvaluator
from app.services.observability.phoenix_client import (
    PhoenixClient,
    HallucinationResult,
    RAGContext,
    get_phoenix_client,
)
from app.services.observability.config import get_observability_config

logger = structlog.get_logger()


class HallucinationEvaluator(BaseEvaluator):
    """Evaluator for detecting hallucinations in LLM outputs using Phoenix."""

    def __init__(
        self,
        phoenix_client: PhoenixClient | None = None,
        threshold: float | None = None,
    ):
        """
        Initialize the hallucination evaluator.

        Args:
            phoenix_client: Phoenix client instance
            threshold: Score threshold for passing (default from config)
        """
        self._phoenix_client = phoenix_client
        self._threshold = threshold
        self._config = get_observability_config()

    async def _get_client(self) -> PhoenixClient:
        """Get or initialize Phoenix client."""
        if self._phoenix_client is None:
            self._phoenix_client = await get_phoenix_client()
        return self._phoenix_client

    def evaluate(
        self,
        test_case: TestCase,
        actual_output: str,
    ) -> list[QualityMetric]:
        """
        Synchronous evaluate - wraps async implementation.

        For async evaluation, use evaluate_async instead.
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, create a new task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(
                        asyncio.run,
                        self.evaluate_async(test_case, actual_output)
                    )
                    return future.result()
            else:
                return loop.run_until_complete(
                    self.evaluate_async(test_case, actual_output)
                )
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(self.evaluate_async(test_case, actual_output))

    async def evaluate_async(
        self,
        test_case: TestCase,
        actual_output: str,
        context: list[str] | None = None,
    ) -> list[QualityMetric]:
        """
        Evaluate output for hallucinations asynchronously.

        Args:
            test_case: Test case with expected output
            actual_output: Actual LLM output
            context: Optional context documents for RAG grounding

        Returns:
            List of quality metrics
        """
        metrics = []

        try:
            client = await self._get_client()

            # Get query from test case input
            query = test_case.input_variables.get(
                "query",
                test_case.input_variables.get(
                    "question",
                    test_case.input_variables.get("input", "")
                )
            )

            # Get context from test case or parameter
            test_context = context or test_case.input_variables.get("context", [])
            if isinstance(test_context, str):
                test_context = [test_context]

            # Check for hallucinations
            result = await client.check_hallucination(
                query=query,
                response=actual_output,
                context=test_context if test_context else None,
                reference=test_case.expected_output,
                metadata={
                    "test_case_id": test_case.id,
                    "test_case_name": test_case.name,
                },
            )

            threshold = self._threshold or self._config.hallucination_score_threshold

            # Main hallucination metric
            passed = result.hallucination_score <= (1 - threshold)
            metrics.append(
                QualityMetric(
                    name="hallucination_score",
                    value=1.0 - result.hallucination_score,  # Invert so higher is better
                    passed=passed,
                    threshold=threshold,
                    details={
                        "is_hallucination": result.is_hallucination,
                        "raw_score": result.hallucination_score,
                        "confidence": result.confidence,
                        "explanation": result.explanation,
                        "issues": result.detected_issues,
                    },
                )
            )

            # Grounding metric (for RAG responses)
            if test_context:
                metrics.append(
                    QualityMetric(
                        name="grounding_score",
                        value=result.grounding_score,
                        passed=result.grounding_score >= 0.5,
                        threshold=0.5,
                        details={
                            "context_count": len(test_context),
                        },
                    )
                )

            # Relevance metric
            metrics.append(
                QualityMetric(
                    name="relevance_score",
                    value=result.relevance_score,
                    passed=result.relevance_score >= 0.5,
                    threshold=0.5,
                )
            )

            # Factuality metric (when reference is available)
            if test_case.expected_output:
                metrics.append(
                    QualityMetric(
                        name="factuality_score",
                        value=result.factuality_score,
                        passed=result.factuality_score >= 0.5,
                        threshold=0.5,
                    )
                )

        except Exception as e:
            logger.error(
                "Hallucination evaluation failed",
                error=str(e),
                test_case=test_case.name,
            )
            metrics.append(
                QualityMetric(
                    name="hallucination_score",
                    value=0.0,
                    passed=False,
                    details={"error": str(e)},
                )
            )

        return metrics


class RAGGroundingEvaluator(BaseEvaluator):
    """Evaluator specifically for RAG response grounding verification."""

    def __init__(
        self,
        phoenix_client: PhoenixClient | None = None,
        grounding_threshold: float = 0.6,
    ):
        """
        Initialize the RAG grounding evaluator.

        Args:
            phoenix_client: Phoenix client instance
            grounding_threshold: Minimum grounding score to pass
        """
        self._phoenix_client = phoenix_client
        self._grounding_threshold = grounding_threshold

    async def _get_client(self) -> PhoenixClient:
        """Get or initialize Phoenix client."""
        if self._phoenix_client is None:
            self._phoenix_client = await get_phoenix_client()
        return self._phoenix_client

    def evaluate(
        self,
        test_case: TestCase,
        actual_output: str,
    ) -> list[QualityMetric]:
        """Synchronous evaluate - wraps async implementation."""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(
                        asyncio.run,
                        self.evaluate_async(test_case, actual_output)
                    )
                    return future.result()
            else:
                return loop.run_until_complete(
                    self.evaluate_async(test_case, actual_output)
                )
        except RuntimeError:
            return asyncio.run(self.evaluate_async(test_case, actual_output))

    async def evaluate_async(
        self,
        test_case: TestCase,
        actual_output: str,
    ) -> list[QualityMetric]:
        """
        Evaluate RAG response grounding asynchronously.

        Args:
            test_case: Test case with context documents
            actual_output: RAG-generated response

        Returns:
            List of quality metrics
        """
        metrics = []

        try:
            client = await self._get_client()

            # Extract RAG context from test case
            query = test_case.input_variables.get(
                "query",
                test_case.input_variables.get("question", "")
            )
            documents = test_case.input_variables.get("documents", [])
            context = test_case.input_variables.get("context", [])

            # Combine documents and context
            all_context = []
            if isinstance(documents, list):
                all_context.extend(documents)
            elif documents:
                all_context.append(documents)
            if isinstance(context, list):
                all_context.extend(context)
            elif context:
                all_context.append(context)

            if not all_context:
                return [
                    QualityMetric(
                        name="rag_grounding",
                        value=1.0,
                        passed=True,
                        details={"note": "No context provided, skipping grounding check"},
                    )
                ]

            # Create RAG context and check
            rag_context = RAGContext(
                query=query,
                response=actual_output,
                retrieved_documents=all_context,
            )

            result = await client.check_rag_response(
                rag_context=rag_context,
                metadata={
                    "test_case_id": test_case.id,
                    "test_case_name": test_case.name,
                },
            )

            # Grounding metric
            passed = result.grounding_score >= self._grounding_threshold
            metrics.append(
                QualityMetric(
                    name="rag_grounding",
                    value=result.grounding_score,
                    passed=passed,
                    threshold=self._grounding_threshold,
                    details={
                        "document_count": len(all_context),
                        "hallucination_detected": result.is_hallucination,
                        "issues": result.detected_issues,
                    },
                )
            )

            # Context utilization metric
            metrics.append(
                QualityMetric(
                    name="context_utilization",
                    value=result.grounding_score,
                    passed=result.grounding_score >= 0.3,
                    threshold=0.3,
                    details={
                        "explanation": "Measures how well the response uses provided context",
                    },
                )
            )

        except Exception as e:
            logger.error(
                "RAG grounding evaluation failed",
                error=str(e),
                test_case=test_case.name,
            )
            metrics.append(
                QualityMetric(
                    name="rag_grounding",
                    value=0.0,
                    passed=False,
                    details={"error": str(e)},
                )
            )

        return metrics


class FactualityEvaluator(BaseEvaluator):
    """Evaluator for checking factual accuracy against reference answers."""

    def __init__(
        self,
        phoenix_client: PhoenixClient | None = None,
        factuality_threshold: float = 0.7,
    ):
        """
        Initialize the factuality evaluator.

        Args:
            phoenix_client: Phoenix client instance
            factuality_threshold: Minimum factuality score to pass
        """
        self._phoenix_client = phoenix_client
        self._factuality_threshold = factuality_threshold

    async def _get_client(self) -> PhoenixClient:
        """Get or initialize Phoenix client."""
        if self._phoenix_client is None:
            self._phoenix_client = await get_phoenix_client()
        return self._phoenix_client

    def evaluate(
        self,
        test_case: TestCase,
        actual_output: str,
    ) -> list[QualityMetric]:
        """Synchronous evaluate - wraps async implementation."""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(
                        asyncio.run,
                        self.evaluate_async(test_case, actual_output)
                    )
                    return future.result()
            else:
                return loop.run_until_complete(
                    self.evaluate_async(test_case, actual_output)
                )
        except RuntimeError:
            return asyncio.run(self.evaluate_async(test_case, actual_output))

    async def evaluate_async(
        self,
        test_case: TestCase,
        actual_output: str,
    ) -> list[QualityMetric]:
        """
        Evaluate factual accuracy asynchronously.

        Args:
            test_case: Test case with reference answer
            actual_output: LLM-generated response

        Returns:
            List of quality metrics
        """
        if not test_case.expected_output:
            return [
                QualityMetric(
                    name="factuality",
                    value=1.0,
                    passed=True,
                    details={"note": "No reference answer provided, skipping factuality check"},
                )
            ]

        metrics = []

        try:
            client = await self._get_client()

            query = test_case.input_variables.get(
                "query",
                test_case.input_variables.get("question", "")
            )

            # Evaluate QA pair
            eval_result = await client.evaluate_qa_pair(
                question=query,
                answer=actual_output,
                expected_answer=test_case.expected_output,
            )

            factuality_score = eval_result["scores"].get("factuality", 0.0)
            passed = factuality_score >= self._factuality_threshold

            metrics.append(
                QualityMetric(
                    name="factuality",
                    value=factuality_score,
                    passed=passed,
                    threshold=self._factuality_threshold,
                    details={
                        "all_scores": eval_result["scores"],
                        "issues": eval_result.get("issues", []),
                        "explanation": eval_result.get("explanation", ""),
                    },
                )
            )

        except Exception as e:
            logger.error(
                "Factuality evaluation failed",
                error=str(e),
                test_case=test_case.name,
            )
            metrics.append(
                QualityMetric(
                    name="factuality",
                    value=0.0,
                    passed=False,
                    details={"error": str(e)},
                )
            )

        return metrics


# Register new test case type for hallucination checks
class HallucinationTestCaseType:
    """Additional test case types for hallucination detection."""

    HALLUCINATION = "hallucination"
    RAG_GROUNDING = "rag_grounding"
    FACTUALITY = "factuality"


def get_hallucination_evaluator(
    eval_type: str,
    phoenix_client: PhoenixClient | None = None,
) -> BaseEvaluator | None:
    """
    Get the appropriate hallucination evaluator for a test case type.

    Args:
        eval_type: Type of evaluation
        phoenix_client: Optional Phoenix client

    Returns:
        Evaluator instance or None
    """
    evaluators = {
        HallucinationTestCaseType.HALLUCINATION: HallucinationEvaluator,
        HallucinationTestCaseType.RAG_GROUNDING: RAGGroundingEvaluator,
        HallucinationTestCaseType.FACTUALITY: FactualityEvaluator,
    }

    evaluator_class = evaluators.get(eval_type)
    if evaluator_class:
        return evaluator_class(phoenix_client=phoenix_client)

    return None
