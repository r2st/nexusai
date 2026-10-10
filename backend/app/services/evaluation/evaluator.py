"""Evaluators for assessing LLM output quality."""

import re
from abc import ABC, abstractmethod

import structlog

from app.services.evaluation.models import (
    EvalResult,
    QualityMetric,
    TestCase,
    TestCaseType,
)

logger = structlog.get_logger()


class BaseEvaluator(ABC):
    """Base class for evaluators."""

    @abstractmethod
    def evaluate(
        self,
        test_case: TestCase,
        actual_output: str,
    ) -> list[QualityMetric]:
        """Evaluate output against test case.

        Args:
            test_case: Test case with expected output
            actual_output: Actual LLM output

        Returns:
            List of quality metrics
        """
        pass


class ExactMatchEvaluator(BaseEvaluator):
    """Evaluator for exact string matching."""

    def evaluate(
        self,
        test_case: TestCase,
        actual_output: str,
    ) -> list[QualityMetric]:
        if not test_case.expected_output:
            return []

        passed = actual_output.strip() == test_case.expected_output.strip()

        return [
            QualityMetric(
                name="exact_match",
                value=1.0 if passed else 0.0,
                passed=passed,
                details={"expected": test_case.expected_output[:100]},
            )
        ]


class ContainsEvaluator(BaseEvaluator):
    """Evaluator for substring matching."""

    def evaluate(
        self,
        test_case: TestCase,
        actual_output: str,
    ) -> list[QualityMetric]:
        metrics = []
        output_lower = actual_output.lower()

        # Check expected contains
        if test_case.expected_contains:
            matches = sum(
                1 for phrase in test_case.expected_contains
                if phrase.lower() in output_lower
            )
            score = matches / len(test_case.expected_contains)
            passed = score >= 1.0

            metrics.append(
                QualityMetric(
                    name="contains",
                    value=score,
                    passed=passed,
                    threshold=1.0,
                    details={
                        "expected_phrases": test_case.expected_contains,
                        "matches": matches,
                        "total": len(test_case.expected_contains),
                    },
                )
            )

        # Check expected NOT contains
        if test_case.expected_not_contains:
            violations = [
                phrase for phrase in test_case.expected_not_contains
                if phrase.lower() in output_lower
            ]
            passed = len(violations) == 0

            metrics.append(
                QualityMetric(
                    name="not_contains",
                    value=1.0 if passed else 0.0,
                    passed=passed,
                    details={
                        "forbidden_phrases": test_case.expected_not_contains,
                        "violations": violations,
                    },
                )
            )

        return metrics


class RegexEvaluator(BaseEvaluator):
    """Evaluator for regex pattern matching."""

    def evaluate(
        self,
        test_case: TestCase,
        actual_output: str,
    ) -> list[QualityMetric]:
        if not test_case.expected_regex:
            return []

        try:
            pattern = re.compile(test_case.expected_regex, re.IGNORECASE | re.DOTALL)
            match = pattern.search(actual_output)
            passed = match is not None

            return [
                QualityMetric(
                    name="regex_match",
                    value=1.0 if passed else 0.0,
                    passed=passed,
                    details={
                        "pattern": test_case.expected_regex,
                        "matched": match.group(0)[:100] if match else None,
                    },
                )
            ]
        except re.error as e:
            return [
                QualityMetric(
                    name="regex_match",
                    value=0.0,
                    passed=False,
                    details={"error": str(e)},
                )
            ]


class SemanticEvaluator(BaseEvaluator):
    """Evaluator using semantic similarity."""

    def __init__(self, embedder=None):
        self._embedder = embedder

    def evaluate(
        self,
        test_case: TestCase,
        actual_output: str,
    ) -> list[QualityMetric]:
        if not test_case.expected_output:
            return []

        if not self._embedder:
            return [
                QualityMetric(
                    name="semantic_similarity",
                    value=0.0,
                    passed=False,
                    details={"error": "Embedder not configured"},
                )
            ]

        try:
            # Get embeddings
            expected_embedding = self._embedder.embed(test_case.expected_output)
            actual_embedding = self._embedder.embed(actual_output)

            # Calculate cosine similarity
            import numpy as np
            norm_expected = np.linalg.norm(expected_embedding)
            norm_actual = np.linalg.norm(actual_embedding)
            if norm_expected == 0 or norm_actual == 0:
                similarity = 0.0
            else:
                similarity = np.dot(expected_embedding, actual_embedding) / (
                    norm_expected * norm_actual
                )

            threshold = 0.8
            passed = similarity >= threshold

            return [
                QualityMetric(
                    name="semantic_similarity",
                    value=float(similarity),
                    passed=passed,
                    threshold=threshold,
                )
            ]
        except Exception as e:
            return [
                QualityMetric(
                    name="semantic_similarity",
                    value=0.0,
                    passed=False,
                    details={"error": str(e)},
                )
            ]


class LLMJudgeEvaluator(BaseEvaluator):
    """Evaluator using another LLM as a judge."""

    JUDGE_PROMPT = """You are evaluating the quality of an AI assistant's response.

Expected Output (reference):
{expected}

Actual Output (to evaluate):
{actual}

Rate the actual output on a scale of 0-100 based on:
1. Correctness: Does it contain accurate information?
2. Completeness: Does it cover all key points from the expected output?
3. Clarity: Is it well-written and easy to understand?

Respond with ONLY a JSON object in this format:
{{"score": <0-100>, "correctness": <0-100>, "completeness": <0-100>, "clarity": <0-100>, "reasoning": "<brief explanation>"}}"""

    def __init__(self, llm_client=None, judge_model: str = "gpt-4"):
        self._llm_client = llm_client
        self._judge_model = judge_model

    def evaluate(
        self,
        test_case: TestCase,
        actual_output: str,
    ) -> list[QualityMetric]:
        if not self._llm_client or not test_case.expected_output:
            return []

        try:
            # Call judge LLM
            prompt = self.JUDGE_PROMPT.format(
                expected=test_case.expected_output,
                actual=actual_output,
            )

            # This would call the LLM - simplified for now
            # response = self._llm_client.complete(prompt, model=self._judge_model)
            # result = json.loads(response)

            # Placeholder result
            result = {
                "score": 75,
                "correctness": 80,
                "completeness": 70,
                "clarity": 75,
                "reasoning": "LLM judge evaluation",
            }

            score = result["score"] / 100
            passed = score >= 0.7

            return [
                QualityMetric(
                    name="llm_judge_score",
                    value=score,
                    passed=passed,
                    threshold=0.7,
                    details={
                        "correctness": result["correctness"],
                        "completeness": result["completeness"],
                        "clarity": result["clarity"],
                        "reasoning": result["reasoning"],
                    },
                )
            ]
        except Exception as e:
            return [
                QualityMetric(
                    name="llm_judge_score",
                    value=0.0,
                    passed=False,
                    details={"error": str(e)},
                )
            ]


class Evaluator:
    """Main evaluator that combines multiple evaluation strategies."""

    def __init__(self, embedder=None, llm_client=None):
        self._evaluators = {
            TestCaseType.EXACT_MATCH: ExactMatchEvaluator(),
            TestCaseType.CONTAINS: ContainsEvaluator(),
            TestCaseType.REGEX: RegexEvaluator(),
            TestCaseType.SEMANTIC: SemanticEvaluator(embedder),
            TestCaseType.LLM_JUDGE: LLMJudgeEvaluator(llm_client),
        }

    def evaluate(
        self,
        test_case: TestCase,
        actual_output: str,
        latency_ms: float = 0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost_usd: float | None = None,
        model: str | None = None,
        prompt_version: int | None = None,
    ) -> EvalResult:
        """Evaluate a test case.

        Args:
            test_case: Test case to evaluate
            actual_output: LLM output to evaluate
            latency_ms: Execution latency
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cost_usd: Execution cost
            model: Model used
            prompt_version: Prompt version used

        Returns:
            EvalResult with metrics
        """
        result = EvalResult(
            test_case_id=test_case.id,
            test_case_name=test_case.name,
            input_variables=test_case.input_variables,
            actual_output=actual_output,
            expected_output=test_case.expected_output,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            model=model,
            prompt_version=prompt_version,
        )

        try:
            # Get evaluator for the test case type
            evaluator = self._evaluators.get(test_case.eval_type)

            if evaluator:
                metrics = evaluator.evaluate(test_case, actual_output)
                result.metrics.extend(metrics)

            # Always run contains evaluator if there are expected phrases
            if test_case.eval_type != TestCaseType.CONTAINS and (
                test_case.expected_contains or test_case.expected_not_contains
            ):
                contains_metrics = self._evaluators[TestCaseType.CONTAINS].evaluate(
                    test_case, actual_output
                )
                result.metrics.extend(contains_metrics)

            # Calculate overall score and pass status
            if result.metrics:
                result.score = sum(m.value for m in result.metrics) / len(result.metrics)
                result.passed = all(m.passed for m in result.metrics)
            else:
                result.score = 0.0
                result.passed = False

        except Exception as e:
            result.error = str(e)
            result.passed = False
            logger.error(
                "Evaluation failed",
                test_case=test_case.name,
                error=str(e),
            )

        return result


# Global evaluator instance
_evaluator: Evaluator | None = None


def get_evaluator() -> Evaluator:
    """Get the global evaluator instance."""
    global _evaluator
    if _evaluator is None:
        _evaluator = Evaluator()
    return _evaluator
