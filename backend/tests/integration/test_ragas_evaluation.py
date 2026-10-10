"""
Integration tests for RAGAS evaluation service.

Tests the complete RAGAS evaluation flow including:
1. Service initialization with different providers
2. Single sample evaluation (quick eval)
3. Batch evaluation with multiple samples
4. Metric computation (faithfulness, relevancy, precision, recall)
5. Langfuse integration for observability
6. Fallback behavior when RAGAS library is not available

To run these tests, ensure you have:
- Valid LLM provider credentials (OpenAI, Anthropic, etc.)
- Langfuse credentials (optional, for observability tests)
- RAGAS package installed (pip install ragas)
"""

import asyncio
import os
import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch

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
    RAGAS_AVAILABLE,
)
from app.services.observability.langfuse_client import LangfuseClient
from app.services.observability.config import ObservabilityConfig


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def ragas_config():
    """Get RAGAS configuration for tests."""
    return RAGASConfig(
        llm_provider="openai",
        llm_model="gpt-4o-mini",
        embeddings_model="text-embedding-3-small",
        default_thresholds={
            "faithfulness": 0.7,
            "answer_relevancy": 0.7,
            "context_precision": 0.7,
            "context_recall": 0.7,
        },
    )


@pytest.fixture
def sample_data():
    """Sample evaluation data."""
    return [
        EvaluationSample(
            user_input="What is Python?",
            response="Python is a high-level programming language known for its simplicity and readability.",
            retrieved_contexts=[
                "Python is a high-level, general-purpose programming language.",
                "Python emphasizes code readability with significant indentation.",
                "Python supports multiple programming paradigms including procedural, object-oriented, and functional programming.",
            ],
            reference="Python is a high-level programming language.",
        ),
        EvaluationSample(
            user_input="What is machine learning?",
            response="Machine learning is a subset of artificial intelligence that enables computers to learn from data.",
            retrieved_contexts=[
                "Machine learning (ML) is a field of study in artificial intelligence.",
                "ML algorithms build a model based on sample data, known as training data.",
                "Machine learning enables computers to make predictions or decisions without being explicitly programmed.",
            ],
            reference="Machine learning is a type of AI that learns from data.",
        ),
    ]


@pytest.fixture
def langfuse_config():
    """Get Langfuse configuration from environment."""
    enabled = os.getenv("LANGFUSE_ENABLED", "false").lower() == "true"
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY", "")
    host = os.getenv("LANGFUSE_HOST", "https://us.cloud.langfuse.com")

    if not enabled or not public_key or not secret_key:
        return None

    return ObservabilityConfig(
        langfuse_enabled=True,
        langfuse_public_key=public_key,
        langfuse_secret_key=secret_key,
        langfuse_host=host,
    )


# =============================================================================
# Unit Tests (No external dependencies)
# =============================================================================


class TestRAGASModels:
    """Test RAGAS model classes."""

    def test_evaluation_sample_creation(self):
        """Test creating an EvaluationSample."""
        sample = EvaluationSample(
            user_input="What is Python?",
            response="Python is a programming language.",
            retrieved_contexts=["Python is a language."],
        )

        assert sample.user_input == "What is Python?"
        assert sample.response == "Python is a programming language."
        assert len(sample.retrieved_contexts) == 1
        assert sample.reference is None
        assert sample.id is not None

    def test_evaluation_sample_with_reference(self):
        """Test sample with reference answer."""
        sample = EvaluationSample(
            user_input="What is Python?",
            response="Python is a programming language.",
            retrieved_contexts=["Python is a language."],
            reference="Python is a high-level programming language.",
        )

        assert sample.reference == "Python is a high-level programming language."

    def test_evaluation_dataset_creation(self):
        """Test creating an EvaluationDataset."""
        dataset = EvaluationDataset(
            name="Test Dataset",
            description="A test dataset",
            samples=[
                EvaluationSample(
                    user_input="Q1",
                    response="A1",
                    retrieved_contexts=["C1"],
                ),
            ],
        )

        assert dataset.name == "Test Dataset"
        assert len(dataset.samples) == 1
        assert dataset.version == 1
        assert dataset.is_active is True

    def test_dataset_from_list(self):
        """Test creating dataset from list of dicts."""
        data = [
            {
                "user_input": "What is Python?",
                "response": "A programming language.",
                "retrieved_contexts": ["Python is a language."],
            },
            {
                "user_input": "What is JavaScript?",
                "response": "A web programming language.",
                "retrieved_contexts": ["JavaScript runs in browsers."],
            },
        ]

        dataset = EvaluationDataset.from_list(data, name="Test")

        assert len(dataset.samples) == 2
        assert dataset.samples[0].user_input == "What is Python?"
        assert dataset.samples[1].user_input == "What is JavaScript?"

    def test_metric_result(self):
        """Test MetricResult model."""
        result = MetricResult(
            name="faithfulness",
            score=0.85,
            passed=True,
            threshold=0.7,
        )

        assert result.name == "faithfulness"
        assert result.score == 0.85
        assert result.passed is True
        assert result.threshold == 0.7

    def test_sample_result(self):
        """Test SampleResult model."""
        result = SampleResult(
            sample_id="test-123",
            metrics=[
                MetricResult(name="faithfulness", score=0.9, passed=True),
                MetricResult(name="relevancy", score=0.8, passed=True),
            ],
            overall_score=0.85,
            passed=True,
            duration_ms=150.0,
        )

        assert result.sample_id == "test-123"
        assert len(result.metrics) == 2
        assert result.overall_score == 0.85
        assert result.passed is True

    def test_evaluation_result_aggregation(self):
        """Test RAGASEvaluationResult aggregation."""
        result = RAGASEvaluationResult()

        sample1 = SampleResult(
            sample_id="s1",
            metrics=[MetricResult(name="faithfulness", score=0.9, passed=True)],
            overall_score=0.9,
            passed=True,
        )

        sample2 = SampleResult(
            sample_id="s2",
            metrics=[MetricResult(name="faithfulness", score=0.7, passed=True)],
            overall_score=0.7,
            passed=True,
        )

        result.add_sample_result(sample1)
        result.add_sample_result(sample2)

        assert result.total_samples == 2
        assert result.passed_samples == 2
        assert result.pass_rate == 1.0

        result.compute_aggregates()
        assert result.overall_score == 0.8  # (0.9 + 0.7) / 2


class TestRAGASConfig:
    """Test RAGAS configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RAGASConfig()

        assert config.llm_temperature == 0.1
        assert config.batch_size == 10
        assert len(config.default_metrics) == 4
        assert RAGASMetricType.FAITHFULNESS in config.default_metrics

    def test_config_thresholds(self):
        """Test threshold retrieval."""
        config = RAGASConfig()

        assert config.get_threshold("faithfulness") == 0.7
        assert config.get_threshold("unknown_metric") == 0.7  # Default

    def test_config_weights(self):
        """Test weight retrieval."""
        config = RAGASConfig()

        assert config.get_weight("faithfulness") == 1.0
        assert config.get_weight("unknown_metric") == 1.0  # Default


# =============================================================================
# Service Tests (Mock external calls)
# =============================================================================


class TestRAGASServiceFallback:
    """Test RAGAS service fallback implementations."""

    @pytest.mark.asyncio
    async def test_service_initialization(self, ragas_config):
        """Test service initializes correctly."""
        service = RAGASService(config=ragas_config)
        await service.initialize()

        assert service._initialized is True

    @pytest.mark.asyncio
    async def test_fallback_faithfulness(self, ragas_config, sample_data):
        """Test fallback faithfulness computation."""
        service = RAGASService(config=ragas_config)
        await service.initialize()

        sample = sample_data[0]
        score = await service._compute_faithfulness_fallback(sample)

        assert 0.0 <= score <= 1.0
        # Should have good overlap with context
        assert score > 0.3

    @pytest.mark.asyncio
    async def test_fallback_relevancy(self, ragas_config, sample_data):
        """Test fallback relevancy computation."""
        service = RAGASService(config=ragas_config)
        await service.initialize()

        sample = sample_data[0]
        score = await service._compute_relevancy_fallback(sample)

        assert 0.0 <= score <= 1.0

    @pytest.mark.asyncio
    async def test_fallback_context_precision(self, ragas_config, sample_data):
        """Test fallback context precision computation."""
        service = RAGASService(config=ragas_config)
        await service.initialize()

        sample = sample_data[0]
        score = await service._compute_context_precision_fallback(sample)

        assert 0.0 <= score <= 1.0

    @pytest.mark.asyncio
    async def test_fallback_context_recall(self, ragas_config, sample_data):
        """Test fallback context recall computation."""
        service = RAGASService(config=ragas_config)
        await service.initialize()

        sample = sample_data[0]
        score = await service._compute_context_recall_fallback(sample)

        assert 0.0 <= score <= 1.0

    @pytest.mark.asyncio
    async def test_quick_evaluate_fallback(self, ragas_config):
        """Test quick evaluation with fallback."""
        service = RAGASService(config=ragas_config)
        await service.initialize()

        # Temporarily disable RAGAS to force fallback
        with patch("app.services.ragas.service.RAGAS_AVAILABLE", False):
            request = RAGASQuickEvalRequest(
                user_input="What is Python?",
                response="Python is a programming language.",
                retrieved_contexts=["Python is a high-level programming language."],
                metrics=[
                    RAGASMetricType.FAITHFULNESS,
                    RAGASMetricType.ANSWER_RELEVANCY,
                ],
            )

            result = await service.quick_evaluate(request)

            assert result.sample_id is not None
            assert len(result.metrics) == 2
            assert all(0.0 <= m.score <= 1.0 for m in result.metrics)

    @pytest.mark.asyncio
    async def test_batch_evaluate_fallback(self, ragas_config, sample_data):
        """Test batch evaluation with fallback."""
        service = RAGASService(config=ragas_config)
        await service.initialize()

        with patch("app.services.ragas.service.RAGAS_AVAILABLE", False):
            request = RAGASEvaluationRequest(
                samples=sample_data,
                metrics=[
                    RAGASMetricType.FAITHFULNESS,
                    RAGASMetricType.ANSWER_RELEVANCY,
                ],
                log_to_langfuse=False,
                persist_results=False,
            )

            result = await service.evaluate(request)

            assert result.status == EvaluationStatus.COMPLETED
            assert result.total_samples == 2
            assert len(result.sample_results) == 2
            assert result.overall_score > 0


# =============================================================================
# Integration Tests (Require external services)
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestRAGASIntegration:
    """Integration tests requiring LLM API access."""

    @pytest.fixture
    def check_api_key(self):
        """Skip if no API key configured."""
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not configured")

    @pytest.mark.asyncio
    async def test_full_evaluation_with_openai(
        self, ragas_config, sample_data, check_api_key
    ):
        """Test full evaluation using OpenAI."""
        if not RAGAS_AVAILABLE:
            pytest.skip("RAGAS package not installed")

        service = RAGASService(config=ragas_config)
        await service.initialize()

        request = RAGASEvaluationRequest(
            samples=sample_data[:1],  # Just one sample for speed
            metrics=[
                RAGASMetricType.FAITHFULNESS,
                RAGASMetricType.ANSWER_RELEVANCY,
            ],
            llm_model="gpt-4o-mini",
            log_to_langfuse=False,
            persist_results=False,
        )

        result = await service.evaluate(request)

        assert result.status == EvaluationStatus.COMPLETED
        assert result.total_samples == 1
        assert "faithfulness" in result.aggregate_scores
        assert "answer_relevancy" in result.aggregate_scores

    @pytest.mark.asyncio
    async def test_evaluation_with_langfuse(
        self, ragas_config, sample_data, langfuse_config, check_api_key
    ):
        """Test evaluation with Langfuse logging."""
        if not RAGAS_AVAILABLE:
            pytest.skip("RAGAS package not installed")

        if not langfuse_config:
            pytest.skip("Langfuse not configured")

        langfuse = LangfuseClient(config=langfuse_config)
        await langfuse.initialize()

        try:
            service = RAGASService(
                config=ragas_config,
                langfuse_client=langfuse,
            )
            await service.initialize()

            request = RAGASEvaluationRequest(
                samples=sample_data[:1],
                metrics=[RAGASMetricType.FAITHFULNESS],
                log_to_langfuse=True,
                persist_results=False,
            )

            result = await service.evaluate(request)

            assert result.status == EvaluationStatus.COMPLETED

            # Check Langfuse metrics
            metrics = langfuse.get_metrics()
            assert metrics["traces"] >= 1

        finally:
            langfuse.flush()
            await langfuse.close()


@pytest.mark.integration
@pytest.mark.asyncio
class TestRAGASWithDifferentProviders:
    """Test RAGAS with different LLM providers."""

    @pytest.mark.asyncio
    async def test_with_anthropic(self, sample_data):
        """Test with Anthropic Claude."""
        if not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not configured")

        if not RAGAS_AVAILABLE:
            pytest.skip("RAGAS package not installed")

        config = RAGASConfig(
            llm_provider="anthropic",
            llm_model="claude-3-haiku-20240307",
        )

        service = RAGASService(config=config)
        await service.initialize()

        request = RAGASQuickEvalRequest(
            user_input=sample_data[0].user_input,
            response=sample_data[0].response,
            retrieved_contexts=sample_data[0].retrieved_contexts,
            metrics=[RAGASMetricType.FAITHFULNESS],
        )

        result = await service.quick_evaluate(request)
        assert len(result.metrics) == 1

    @pytest.mark.asyncio
    async def test_with_google(self, sample_data):
        """Test with Google Gemini."""
        if not os.getenv("GOOGLE_API_KEY"):
            pytest.skip("GOOGLE_API_KEY not configured")

        if not RAGAS_AVAILABLE:
            pytest.skip("RAGAS package not installed")

        config = RAGASConfig(
            llm_provider="google",
            llm_model="gemini-1.5-flash",
        )

        service = RAGASService(config=config)
        await service.initialize()

        request = RAGASQuickEvalRequest(
            user_input=sample_data[0].user_input,
            response=sample_data[0].response,
            retrieved_contexts=sample_data[0].retrieved_contexts,
            metrics=[RAGASMetricType.FAITHFULNESS],
        )

        result = await service.quick_evaluate(request)
        assert len(result.metrics) == 1


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestRAGASEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_contexts(self, ragas_config):
        """Test with empty retrieved contexts."""
        service = RAGASService(config=ragas_config)
        await service.initialize()

        sample = EvaluationSample(
            user_input="What is Python?",
            response="Python is a programming language.",
            retrieved_contexts=[],  # Empty
        )

        score = await service._compute_faithfulness_fallback(sample)
        assert score == 0.0  # No context = no grounding

    @pytest.mark.asyncio
    async def test_empty_response(self, ragas_config):
        """Test with empty response."""
        service = RAGASService(config=ragas_config)
        await service.initialize()

        sample = EvaluationSample(
            user_input="What is Python?",
            response="",  # Empty
            retrieved_contexts=["Python is a language."],
        )

        score = await service._compute_relevancy_fallback(sample)
        # Empty response should have low score
        assert score < 0.5

    @pytest.mark.asyncio
    async def test_no_reference_for_recall(self, ragas_config):
        """Test context recall without reference."""
        service = RAGASService(config=ragas_config)
        await service.initialize()

        sample = EvaluationSample(
            user_input="What is Python?",
            response="Python is a programming language.",
            retrieved_contexts=["Python is a language."],
            reference=None,  # No reference
        )

        score = await service._compute_context_recall_fallback(sample)
        # Should return moderate score when no reference
        assert score == 0.5

    @pytest.mark.asyncio
    async def test_invalid_metric_type(self, ragas_config, sample_data):
        """Test with invalid metric type handling."""
        service = RAGASService(config=ragas_config)
        await service.initialize()

        with patch("app.services.ragas.service.RAGAS_AVAILABLE", False):
            # This should not raise, just return default score
            score = await service._compute_fallback_metric(
                RAGASMetricType.HARMFULNESS,  # Not implemented in fallback
                sample_data[0],
            )
            assert score == 0.5  # Default for unimplemented

    @pytest.mark.asyncio
    async def test_evaluation_with_errors(self, ragas_config):
        """Test evaluation handles errors gracefully."""
        service = RAGASService(config=ragas_config)
        await service.initialize()

        # Create sample that might cause issues
        sample = EvaluationSample(
            user_input="",  # Empty query
            response="Some response",
            retrieved_contexts=["Context"],
        )

        with patch("app.services.ragas.service.RAGAS_AVAILABLE", False):
            request = RAGASEvaluationRequest(
                samples=[sample],
                metrics=[RAGASMetricType.FAITHFULNESS],
                log_to_langfuse=False,
                persist_results=False,
            )

            result = await service.evaluate(request)

            # Should complete without crashing
            assert result.status == EvaluationStatus.COMPLETED
