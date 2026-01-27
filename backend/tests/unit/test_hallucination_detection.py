"""Unit tests for Hallucination Detection using Phoenix.

Tests for:
- Phoenix client initialization and configuration
- Hallucination detection logic
- RAG response grounding verification
- Heuristic-based fallback detection
- Integration with LLM Gateway
- Hallucination evaluators
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.observability.config import ObservabilityConfig, get_observability_config
from app.services.observability.phoenix_client import (
    PhoenixClient,
    HallucinationResult,
    RAGContext,
    get_phoenix_client,
    PHOENIX_AVAILABLE,
    PHOENIX_EVALS_AVAILABLE,
)
from app.services.evaluation.hallucination_evaluator import (
    HallucinationEvaluator,
    RAGGroundingEvaluator,
    FactualityEvaluator,
    HallucinationTestCaseType,
    get_hallucination_evaluator,
)
from app.services.evaluation.models import TestCase, TestCaseType, QualityMetric
from app.services.llm_gateway.models import HallucinationCheckResult


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def phoenix_config():
    """Create a test Phoenix configuration."""
    return ObservabilityConfig(
        phoenix_enabled=True,
        phoenix_endpoint="http://localhost:6006",
        phoenix_api_key="test-api-key",
        phoenix_project_name="test-project",
        phoenix_collect_traces=True,
        hallucination_detection_enabled=True,
        hallucination_score_threshold=0.7,
        hallucination_check_rag_responses=True,
    )


@pytest.fixture
def disabled_phoenix_config():
    """Create a config with Phoenix disabled."""
    return ObservabilityConfig(
        phoenix_enabled=False,
        hallucination_detection_enabled=False,
    )


@pytest.fixture
def phoenix_client(phoenix_config):
    """Create a Phoenix client for testing."""
    return PhoenixClient(config=phoenix_config)


@pytest.fixture
def sample_hallucination_result():
    """Create a sample hallucination result."""
    return HallucinationResult(
        is_hallucination=False,
        hallucination_score=0.2,
        confidence=0.85,
        grounding_score=0.9,
        relevance_score=0.95,
        factuality_score=0.88,
        explanation="Response is well-grounded in the provided context.",
        detected_issues=[],
    )


@pytest.fixture
def sample_rag_context():
    """Create a sample RAG context."""
    return RAGContext(
        query="What is the capital of France?",
        response="The capital of France is Paris.",
        retrieved_documents=[
            "France is a country in Western Europe. Its capital city is Paris.",
            "Paris is the largest city and capital of France.",
        ],
    )


@pytest.fixture
def sample_test_case():
    """Create a sample test case for hallucination evaluation."""
    return TestCase(
        name="test-hallucination-check",
        input_variables={
            "query": "What is the capital of France?",
            "context": ["Paris is the capital of France."],
        },
        expected_output="The capital of France is Paris.",
        eval_type=TestCaseType.CUSTOM,
    )


# =============================================================================
# HallucinationResult Tests
# =============================================================================


class TestHallucinationResult:
    """Tests for HallucinationResult dataclass."""

    def test_create_hallucination_result(self, sample_hallucination_result):
        """Test creating a hallucination result."""
        assert sample_hallucination_result.is_hallucination is False
        assert sample_hallucination_result.hallucination_score == 0.2
        assert sample_hallucination_result.confidence == 0.85
        assert sample_hallucination_result.grounding_score == 0.9

    def test_passed_property_true(self, sample_hallucination_result):
        """Test passed property when not a hallucination."""
        assert sample_hallucination_result.passed is True

    def test_passed_property_false(self):
        """Test passed property when is a hallucination."""
        result = HallucinationResult(is_hallucination=True, hallucination_score=0.8)
        assert result.passed is False

    def test_to_dict(self, sample_hallucination_result):
        """Test converting result to dictionary."""
        data = sample_hallucination_result.to_dict()

        assert data["is_hallucination"] is False
        assert data["hallucination_score"] == 0.2
        assert data["grounding_score"] == 0.9
        assert data["passed"] is True
        assert "evaluated_at" in data

    def test_default_values(self):
        """Test default values for HallucinationResult."""
        result = HallucinationResult()

        assert result.is_hallucination is False
        assert result.hallucination_score == 0.0
        assert result.grounding_score == 1.0
        assert result.relevance_score == 1.0
        assert result.factuality_score == 1.0
        assert result.detected_issues == []


# =============================================================================
# RAGContext Tests
# =============================================================================


class TestRAGContext:
    """Tests for RAGContext dataclass."""

    def test_create_rag_context(self, sample_rag_context):
        """Test creating a RAG context."""
        assert sample_rag_context.query == "What is the capital of France?"
        assert sample_rag_context.response == "The capital of France is Paris."
        assert len(sample_rag_context.retrieved_documents) == 2

    def test_empty_documents(self):
        """Test RAG context with empty documents."""
        context = RAGContext(
            query="test query",
            response="test response",
        )

        assert context.retrieved_documents == []
        assert context.document_metadata == []


# =============================================================================
# PhoenixClient Tests
# =============================================================================


class TestPhoenixClient:
    """Tests for PhoenixClient."""

    @pytest.mark.asyncio
    async def test_initialize_disabled(self, disabled_phoenix_config):
        """Test initializing with Phoenix disabled."""
        client = PhoenixClient(config=disabled_phoenix_config)
        await client.initialize()

        assert client._enabled is False

    @pytest.mark.asyncio
    async def test_initialize_without_package(self, phoenix_config):
        """Test initializing without Phoenix package installed."""
        with patch('app.services.observability.phoenix_client.PHOENIX_AVAILABLE', False):
            client = PhoenixClient(config=phoenix_config)
            await client.initialize()

            assert client._enabled is False

    @pytest.mark.asyncio
    async def test_check_hallucination_basic(self, phoenix_client):
        """Test basic hallucination check."""
        result = await phoenix_client.check_hallucination(
            query="What is 2 + 2?",
            response="2 + 2 equals 4.",
        )

        assert isinstance(result, HallucinationResult)
        assert result.id is not None

    @pytest.mark.asyncio
    async def test_check_hallucination_with_context(self, phoenix_client):
        """Test hallucination check with context."""
        result = await phoenix_client.check_hallucination(
            query="What is the capital of France?",
            response="The capital of France is Paris.",
            context=["Paris is the capital city of France."],
        )

        assert isinstance(result, HallucinationResult)
        # Should have good grounding score with matching context
        assert result.grounding_score > 0

    @pytest.mark.asyncio
    async def test_check_hallucination_with_reference(self, phoenix_client):
        """Test hallucination check with reference answer."""
        result = await phoenix_client.check_hallucination(
            query="What color is the sky?",
            response="The sky is blue during the day.",
            reference="The sky appears blue due to Rayleigh scattering.",
        )

        assert isinstance(result, HallucinationResult)

    @pytest.mark.asyncio
    async def test_check_hallucination_detects_issues(self, phoenix_client):
        """Test that hallucination check detects potential issues."""
        # Response with hallucination indicators
        result = await phoenix_client.check_hallucination(
            query="What is AI?",
            response="According to studies, I think AI might be probably a technology that experts say could be exactly what research shows.",
        )

        # Heuristic detection should flag this
        assert len(result.detected_issues) > 0 or result.hallucination_score > 0

    @pytest.mark.asyncio
    async def test_check_rag_response(self, phoenix_client, sample_rag_context):
        """Test RAG response grounding check."""
        result = await phoenix_client.check_rag_response(
            rag_context=sample_rag_context,
            metadata={"test": True},
        )

        assert isinstance(result, HallucinationResult)
        assert "document_count" in result.metadata
        assert result.metadata["document_count"] == 2

    @pytest.mark.asyncio
    async def test_evaluate_qa_pair(self, phoenix_client):
        """Test QA pair evaluation."""
        result = await phoenix_client.evaluate_qa_pair(
            question="What is Python?",
            answer="Python is a programming language.",
            expected_answer="Python is a high-level programming language.",
            context=["Python is a popular programming language used for various applications."],
        )

        assert "scores" in result
        assert "passed" in result
        assert "hallucination" in result["scores"]

    def test_calculate_grounding_score(self, phoenix_client):
        """Test grounding score calculation."""
        response = "Paris is the capital of France and is known for the Eiffel Tower."
        context = [
            "Paris is the capital of France.",
            "The Eiffel Tower is located in Paris.",
        ]

        score = phoenix_client._calculate_grounding_score(response, context)

        assert 0 <= score <= 1
        assert score > 0.5  # Should have good overlap

    def test_calculate_grounding_score_no_context(self, phoenix_client):
        """Test grounding score with no context."""
        score = phoenix_client._calculate_grounding_score("test response", [])

        assert score == 1.0

    def test_calculate_similarity(self, phoenix_client):
        """Test text similarity calculation."""
        text1 = "The quick brown fox"
        text2 = "The quick brown dog"

        similarity = phoenix_client._calculate_similarity(text1, text2)

        assert 0 <= similarity <= 1
        assert similarity > 0.5  # Should be similar

    def test_calculate_similarity_empty(self, phoenix_client):
        """Test similarity with empty text."""
        assert phoenix_client._calculate_similarity("", "test") == 1.0
        assert phoenix_client._calculate_similarity("test", "") == 1.0

    def test_get_metrics(self, phoenix_client):
        """Test getting metrics."""
        metrics = phoenix_client.get_metrics()

        assert "total_hallucination_checks" in metrics
        assert "hallucinations_detected" in metrics
        assert "hallucination_rate" in metrics

    @pytest.mark.asyncio
    async def test_trace_llm_call_context_manager(self, phoenix_client):
        """Test trace LLM call context manager."""
        async with phoenix_client.trace_llm_call(
            name="test-call",
            model="gpt-4o",
            metadata={"test": True},
        ) as trace_ctx:
            assert trace_ctx["name"] == "test-call"
            assert trace_ctx["model"] == "gpt-4o"
            assert "trace_id" in trace_ctx

    @pytest.mark.asyncio
    async def test_close(self, phoenix_client):
        """Test closing the client."""
        await phoenix_client.close()
        # Should complete without error


# =============================================================================
# Heuristic Detection Tests
# =============================================================================


class TestHeuristicDetection:
    """Tests for heuristic-based hallucination detection."""

    @pytest.mark.asyncio
    async def test_heuristic_detects_uncertainty_markers(self, phoenix_client):
        """Test that heuristic detection flags uncertainty markers."""
        result = await phoenix_client._heuristic_hallucination_check(
            query="What is the answer?",
            response="I think it might be probably something.",
            context=None,
            reference=None,
            result=HallucinationResult(),
        )

        assert result.hallucination_score > 0

    @pytest.mark.asyncio
    async def test_heuristic_detects_unsupported_claims(self, phoenix_client):
        """Test that heuristic detection flags unsupported claims."""
        result = await phoenix_client._heuristic_hallucination_check(
            query="What do experts say?",
            response="According to studies, research shows that experts say this is exactly correct.",
            context=None,
            reference=None,
            result=HallucinationResult(),
        )

        assert result.hallucination_score > 0
        assert len(result.detected_issues) > 0

    @pytest.mark.asyncio
    async def test_heuristic_with_good_response(self, phoenix_client):
        """Test heuristic detection with a clean response."""
        result = await phoenix_client._heuristic_hallucination_check(
            query="What is 2 + 2?",
            response="The answer is 4.",
            context=None,
            reference=None,
            result=HallucinationResult(),
        )

        assert result.hallucination_score == 0 or result.hallucination_score < 0.3

    @pytest.mark.asyncio
    async def test_heuristic_poor_grounding(self, phoenix_client):
        """Test heuristic detection with poor context grounding."""
        result = await phoenix_client._heuristic_hallucination_check(
            query="What is the capital?",
            response="The capital is definitely XYZ which is famous for ABC.",
            context=["Paris is the capital of France."],
            reference=None,
            result=HallucinationResult(),
        )

        # Should detect poor grounding
        assert result.grounding_score < 0.5 or result.hallucination_score > 0.3


# =============================================================================
# HallucinationCheckResult Model Tests
# =============================================================================


class TestHallucinationCheckResultModel:
    """Tests for HallucinationCheckResult Pydantic model."""

    def test_create_result(self):
        """Test creating a hallucination check result."""
        result = HallucinationCheckResult(
            checked=True,
            is_hallucination=False,
            hallucination_score=0.15,
            grounding_score=0.92,
        )

        assert result.checked is True
        assert result.is_hallucination is False
        assert result.hallucination_score == 0.15

    def test_passed_property(self):
        """Test passed property."""
        result1 = HallucinationCheckResult(checked=True, is_hallucination=False)
        assert result1.passed is True

        result2 = HallucinationCheckResult(checked=True, is_hallucination=True)
        assert result2.passed is False

        result3 = HallucinationCheckResult(checked=False, is_hallucination=False)
        assert result3.passed is False  # Not checked

    def test_default_values(self):
        """Test default values."""
        result = HallucinationCheckResult()

        assert result.checked is False
        assert result.is_hallucination is False
        assert result.hallucination_score == 0.0
        assert result.grounding_score == 1.0
        assert result.issues == []


# =============================================================================
# Hallucination Evaluator Tests
# =============================================================================


class TestHallucinationEvaluator:
    """Tests for HallucinationEvaluator."""

    @pytest.fixture
    def evaluator(self, phoenix_client):
        """Create a hallucination evaluator."""
        return HallucinationEvaluator(phoenix_client=phoenix_client)

    @pytest.mark.asyncio
    async def test_evaluate_async(self, evaluator, sample_test_case):
        """Test async evaluation."""
        metrics = await evaluator.evaluate_async(
            test_case=sample_test_case,
            actual_output="The capital of France is Paris.",
            context=["Paris is the capital of France."],
        )

        assert len(metrics) > 0
        assert any(m.name == "hallucination_score" for m in metrics)

    @pytest.mark.asyncio
    async def test_evaluate_returns_multiple_metrics(self, evaluator, sample_test_case):
        """Test that evaluation returns multiple metrics."""
        metrics = await evaluator.evaluate_async(
            test_case=sample_test_case,
            actual_output="The capital of France is Paris.",
            context=["Paris is the capital of France."],
        )

        metric_names = [m.name for m in metrics]
        assert "hallucination_score" in metric_names
        assert "relevance_score" in metric_names

    @pytest.mark.asyncio
    async def test_evaluate_with_expected_output(self, evaluator):
        """Test evaluation with expected output for factuality."""
        test_case = TestCase(
            name="factuality-test",
            input_variables={"query": "What is Python?"},
            expected_output="Python is a programming language.",
        )

        metrics = await evaluator.evaluate_async(
            test_case=test_case,
            actual_output="Python is a high-level programming language.",
        )

        metric_names = [m.name for m in metrics]
        assert "factuality_score" in metric_names


class TestRAGGroundingEvaluator:
    """Tests for RAGGroundingEvaluator."""

    @pytest.fixture
    def evaluator(self, phoenix_client):
        """Create a RAG grounding evaluator."""
        return RAGGroundingEvaluator(phoenix_client=phoenix_client)

    @pytest.mark.asyncio
    async def test_evaluate_with_documents(self, evaluator):
        """Test evaluation with documents."""
        test_case = TestCase(
            name="rag-test",
            input_variables={
                "query": "What is AI?",
                "documents": [
                    "AI stands for Artificial Intelligence.",
                    "AI is a branch of computer science.",
                ],
            },
        )

        metrics = await evaluator.evaluate_async(
            test_case=test_case,
            actual_output="AI stands for Artificial Intelligence and is a computer science field.",
        )

        assert any(m.name == "rag_grounding" for m in metrics)

    @pytest.mark.asyncio
    async def test_evaluate_without_context(self, evaluator):
        """Test evaluation without context skips grounding check."""
        test_case = TestCase(
            name="no-context-test",
            input_variables={"query": "What is AI?"},
        )

        metrics = await evaluator.evaluate_async(
            test_case=test_case,
            actual_output="AI is artificial intelligence.",
        )

        # Should return a metric indicating skip
        assert len(metrics) == 1
        assert metrics[0].passed is True
        assert "No context provided" in metrics[0].details.get("note", "")


class TestFactualityEvaluator:
    """Tests for FactualityEvaluator."""

    @pytest.fixture
    def evaluator(self, phoenix_client):
        """Create a factuality evaluator."""
        return FactualityEvaluator(phoenix_client=phoenix_client)

    @pytest.mark.asyncio
    async def test_evaluate_with_reference(self, evaluator):
        """Test evaluation with reference answer."""
        test_case = TestCase(
            name="factuality-test",
            input_variables={"query": "What is 2+2?"},
            expected_output="4",
        )

        metrics = await evaluator.evaluate_async(
            test_case=test_case,
            actual_output="The answer is 4.",
        )

        assert any(m.name == "factuality" for m in metrics)

    @pytest.mark.asyncio
    async def test_evaluate_without_reference(self, evaluator):
        """Test evaluation without reference skips factuality check."""
        test_case = TestCase(
            name="no-ref-test",
            input_variables={"query": "What is AI?"},
            expected_output=None,
        )

        metrics = await evaluator.evaluate_async(
            test_case=test_case,
            actual_output="AI is artificial intelligence.",
        )

        assert len(metrics) == 1
        assert metrics[0].passed is True
        assert "No reference answer" in metrics[0].details.get("note", "")


# =============================================================================
# Evaluator Factory Tests
# =============================================================================


class TestEvaluatorFactory:
    """Tests for evaluator factory function."""

    def test_get_hallucination_evaluator(self):
        """Test getting hallucination evaluator."""
        evaluator = get_hallucination_evaluator(HallucinationTestCaseType.HALLUCINATION)
        assert isinstance(evaluator, HallucinationEvaluator)

    def test_get_rag_grounding_evaluator(self):
        """Test getting RAG grounding evaluator."""
        evaluator = get_hallucination_evaluator(HallucinationTestCaseType.RAG_GROUNDING)
        assert isinstance(evaluator, RAGGroundingEvaluator)

    def test_get_factuality_evaluator(self):
        """Test getting factuality evaluator."""
        evaluator = get_hallucination_evaluator(HallucinationTestCaseType.FACTUALITY)
        assert isinstance(evaluator, FactualityEvaluator)

    def test_get_unknown_evaluator(self):
        """Test getting unknown evaluator type returns None."""
        evaluator = get_hallucination_evaluator("unknown_type")
        assert evaluator is None

    def test_get_evaluator_with_custom_client(self, phoenix_client):
        """Test getting evaluator with custom Phoenix client."""
        evaluator = get_hallucination_evaluator(
            HallucinationTestCaseType.HALLUCINATION,
            phoenix_client=phoenix_client,
        )
        assert evaluator._phoenix_client is phoenix_client


# =============================================================================
# Configuration Tests
# =============================================================================


class TestPhoenixConfiguration:
    """Tests for Phoenix configuration."""

    def test_config_defaults(self):
        """Test default configuration values."""
        config = ObservabilityConfig()

        assert config.phoenix_enabled is False
        assert config.hallucination_detection_enabled is True
        assert config.hallucination_score_threshold == 0.7

    def test_config_custom_values(self, phoenix_config):
        """Test custom configuration values."""
        assert phoenix_config.phoenix_enabled is True
        assert phoenix_config.phoenix_endpoint == "http://localhost:6006"
        assert phoenix_config.phoenix_project_name == "test-project"

    def test_get_config_from_env(self):
        """Test getting config from environment variables."""
        with patch.dict('os.environ', {
            'PHOENIX_ENABLED': 'true',
            'PHOENIX_ENDPOINT': 'http://phoenix:6006',
            'PHOENIX_API_KEY': 'test-key',
            'HALLUCINATION_DETECTION_ENABLED': 'true',
            'HALLUCINATION_SCORE_THRESHOLD': '0.8',
        }):
            config = get_observability_config()

            assert config.phoenix_enabled is True
            assert config.phoenix_endpoint == 'http://phoenix:6006'
            assert config.hallucination_score_threshold == 0.8


# =============================================================================
# Global Client Instance Tests
# =============================================================================


class TestGlobalClientInstance:
    """Tests for global Phoenix client instance."""

    @pytest.mark.asyncio
    async def test_get_phoenix_client_creates_instance(self, phoenix_config):
        """Test that get_phoenix_client creates and returns an instance."""
        with patch('app.services.observability.phoenix_client._phoenix_client', None):
            client = await get_phoenix_client(phoenix_config)

            assert client is not None
            assert isinstance(client, PhoenixClient)

    @pytest.mark.asyncio
    async def test_get_phoenix_client_returns_same_instance(self, phoenix_config):
        """Test that get_phoenix_client returns the same instance."""
        with patch('app.services.observability.phoenix_client._phoenix_client', None):
            client1 = await get_phoenix_client(phoenix_config)

            # Patch the global to use the created client
            with patch('app.services.observability.phoenix_client._phoenix_client', client1):
                client2 = await get_phoenix_client()

                assert client1 is client2


# =============================================================================
# Integration Tests
# =============================================================================


class TestHallucinationDetectionIntegration:
    """Integration tests for hallucination detection flow."""

    @pytest.mark.asyncio
    async def test_full_hallucination_check_flow(self, phoenix_client):
        """Test complete hallucination check flow."""
        # Create RAG context
        rag_context = RAGContext(
            query="What programming language is Python?",
            response="Python is a high-level, interpreted programming language known for its readability.",
            retrieved_documents=[
                "Python is a high-level, general-purpose programming language.",
                "Python emphasizes code readability with significant indentation.",
            ],
        )

        # Check RAG response
        result = await phoenix_client.check_rag_response(rag_context)

        # Verify result
        assert result.checked or not result.is_hallucination  # Either checked or not detected
        assert result.grounding_score >= 0

        # Get metrics
        metrics = phoenix_client.get_metrics()
        assert metrics["total_hallucination_checks"] >= 1

    @pytest.mark.asyncio
    async def test_evaluator_integration(self, phoenix_client):
        """Test evaluator integration with Phoenix client."""
        evaluator = HallucinationEvaluator(phoenix_client=phoenix_client, threshold=0.7)

        test_case = TestCase(
            name="integration-test",
            input_variables={
                "query": "What is machine learning?",
                "context": [
                    "Machine learning is a subset of artificial intelligence.",
                    "ML algorithms learn from data to make predictions.",
                ],
            },
            expected_output="Machine learning is a type of AI that learns from data.",
        )

        metrics = await evaluator.evaluate_async(
            test_case=test_case,
            actual_output="Machine learning is a subset of AI that uses algorithms to learn from data.",
            context=test_case.input_variables.get("context"),
        )

        # Should return metrics
        assert len(metrics) > 0

        # Check that metrics have expected structure
        for metric in metrics:
            assert isinstance(metric, QualityMetric)
            assert metric.name is not None
            assert 0 <= metric.value <= 1


# =============================================================================
# Edge Cases Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases in hallucination detection."""

    @pytest.mark.asyncio
    async def test_empty_response(self, phoenix_client):
        """Test handling of empty response."""
        result = await phoenix_client.check_hallucination(
            query="What is AI?",
            response="",
        )

        assert isinstance(result, HallucinationResult)

    @pytest.mark.asyncio
    async def test_very_long_response(self, phoenix_client):
        """Test handling of very long response."""
        long_response = "AI is artificial intelligence. " * 1000

        result = await phoenix_client.check_hallucination(
            query="What is AI?",
            response=long_response,
        )

        assert isinstance(result, HallucinationResult)

    @pytest.mark.asyncio
    async def test_special_characters_in_response(self, phoenix_client):
        """Test handling of special characters."""
        result = await phoenix_client.check_hallucination(
            query="What are code symbols?",
            response="Common symbols include: <, >, &, &&, ||, ==, !=, +=, -=",
        )

        assert isinstance(result, HallucinationResult)

    @pytest.mark.asyncio
    async def test_unicode_in_response(self, phoenix_client):
        """Test handling of unicode characters."""
        result = await phoenix_client.check_hallucination(
            query="How do you say hello in different languages?",
            response="Hello: English, Hola: Spanish, Bonjour: French, \u4f60\u597d: Chinese, \u3053\u3093\u306b\u3061\u306f: Japanese",
        )

        assert isinstance(result, HallucinationResult)

    @pytest.mark.asyncio
    async def test_numerical_response(self, phoenix_client):
        """Test handling of numerical response."""
        result = await phoenix_client.check_hallucination(
            query="What is 15 * 23?",
            response="345",
            reference="345",
        )

        assert isinstance(result, HallucinationResult)

    def test_grounding_score_with_stop_words_only(self, phoenix_client):
        """Test grounding score when response is mostly stop words."""
        score = phoenix_client._calculate_grounding_score(
            "The is a an of to and but or",
            ["Some actual content here."],
        )

        # After removing stop words, there's minimal overlap
        assert score <= 1.0

    @pytest.mark.asyncio
    async def test_check_with_none_metadata(self, phoenix_client):
        """Test check with None metadata."""
        result = await phoenix_client.check_hallucination(
            query="Test",
            response="Test response",
            metadata=None,
        )

        assert result.metadata == {}
