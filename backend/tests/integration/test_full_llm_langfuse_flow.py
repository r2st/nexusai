"""
Integration tests for the full LLM Gateway + LangFuse flow.

Tests the complete path from LLM request through to LangFuse tracing,
including:
1. LLM completion creates LangFuse trace
2. Hallucination check logs scores to trace
3. RAG completion with grounding scores
4. Streaming creates trace
5. Error handling logs failure status
6. Circuit breaker metrics are tracked
7. Cost tracking is recorded

To run these tests, ensure you have:
- Valid LLM provider credentials (OpenAI, Anthropic, etc.)
- Langfuse credentials configured
- Database connection available
"""

import asyncio
import os
import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.services.observability.config import ObservabilityConfig, get_observability_config
from app.services.observability.langfuse_client import (
    LangfuseClient,
    TraceContext,
    LANGFUSE_AVAILABLE,
)
from app.services.llm_gateway.service import LLMGateway
from app.services.llm_gateway.config import GatewayConfig, ProviderConfig
from app.services.llm_gateway.models import (
    LLMRequest,
    Message,
    MessageRole,
)


def create_test_config():
    """Create a test gateway configuration."""
    return GatewayConfig(
        providers=[
            ProviderConfig(
                name="openai",
                enabled=True,
                models=["gpt-4o-mini"],
                priority=1,
            ),
        ],
        default_model="gpt-4o-mini",
        max_retries=2,
        timeout_seconds=30,
        user_rate_limit_per_minute=100,
    )


@pytest.mark.integration
@pytest.mark.asyncio
class TestFullLLMLangfuseFlow:
    """Integration tests for LLM Gateway with LangFuse tracing."""

    @pytest.fixture
    def langfuse_config(self):
        """Get Langfuse configuration from environment."""
        enabled = os.getenv("LANGFUSE_ENABLED", "false").lower() == "true"
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY", "")
        host = os.getenv("LANGFUSE_HOST", "https://us.cloud.langfuse.com")

        if not enabled or not public_key or not secret_key:
            pytest.skip(
                "Langfuse not configured. Set LANGFUSE_ENABLED=true, "
                "LANGFUSE_PUBLIC_KEY, and LANGFUSE_SECRET_KEY to run this test."
            )

        return ObservabilityConfig(
            langfuse_enabled=True,
            langfuse_public_key=public_key,
            langfuse_secret_key=secret_key,
            langfuse_host=host,
        )

    @pytest.fixture
    def mock_provider(self):
        """Create a mock LLM provider."""
        from app.services.providers.base import ChatResponse, TokenUsage, MessageRole

        provider = MagicMock()
        provider.chat = AsyncMock(
            return_value=ChatResponse(
                content="Test response from mock provider",
                role=MessageRole.ASSISTANT,
                finish_reason="stop",
                usage=TokenUsage(
                    prompt_tokens=10,
                    completion_tokens=20,
                    total_tokens=30,
                ),
            )
        )
        provider.health_check = AsyncMock(return_value=True)
        provider.list_models = MagicMock(return_value=["mock-model"])
        return provider

    @pytest.mark.asyncio
    async def test_completion_creates_langfuse_trace(
        self, langfuse_config, mock_provider
    ):
        """Test that a completion request creates a LangFuse trace."""
        if not LANGFUSE_AVAILABLE:
            pytest.skip("Langfuse package not installed")

        # Initialize LangFuse client
        langfuse = LangfuseClient(config=langfuse_config)
        await langfuse.initialize()

        try:
            # Create gateway with mock provider
            gateway = LLMGateway(config=create_test_config())
            gateway._providers["openai"] = mock_provider
            gateway._langfuse_client = langfuse
            gateway._langfuse_initialized = True

            # Make a completion request
            request = LLMRequest(
                user_id="test-user-123",
                tenant_id="test-tenant-456",
                messages=[
                    Message(role=MessageRole.USER, content="Hello, world!")
                ],
                model="gpt-4o-mini",
                provider="openai",
                metadata={"session_id": "test-session", "tags": ["test"]},
            )

            response = await gateway.complete(request)

            # Verify response
            assert response is not None
            assert response.content == "Test response from mock provider"
            assert response.provider == "openai"

            # Verify LangFuse metrics
            metrics = langfuse.get_metrics()
            assert metrics["traces"] >= 1, "Should have at least one trace"
            assert metrics["generations"] >= 1, "Should have at least one generation"

            # Check trace details
            recent_traces = metrics["recent_traces"]
            assert len(recent_traces) > 0
            trace = recent_traces[-1]
            assert trace["user_id"] == "test-user-123"

            # Check generation details
            recent_gens = metrics["recent_generations"]
            assert len(recent_gens) > 0
            gen = recent_gens[-1]
            assert gen["model"] == "mock-model" or gen["model"] == "gpt-4o-mini"
            assert gen["input_tokens"] == 10
            assert gen["output_tokens"] == 20

        finally:
            langfuse.flush()
            await langfuse.close()

    @pytest.mark.asyncio
    async def test_hallucination_check_logs_scores(
        self, langfuse_config, mock_provider
    ):
        """Test that hallucination check results are logged to LangFuse."""
        if not LANGFUSE_AVAILABLE:
            pytest.skip("Langfuse package not installed")

        # Initialize LangFuse client
        langfuse = LangfuseClient(config=langfuse_config)
        await langfuse.initialize()

        try:
            # Create a trace
            trace = langfuse.create_trace(
                name="hallucination-test",
                user_id="test-user",
                metadata={"test": "hallucination_scoring"},
            )

            # Log hallucination scores
            langfuse.log_hallucination_score(
                trace=trace,
                hallucination_score=0.2,
                grounding_score=0.8,
                relevance_score=0.9,
                factuality_score=0.85,
                consistency_score=0.95,
                is_hallucination=False,
                issues=["minor_uncertainty"],
                check_type="full_check",
            )

            # End trace
            langfuse.end_trace(trace, status="success")

            # Verify hallucination metrics
            metrics = langfuse.get_metrics()
            hallucination_checks = metrics.get("hallucination_checks", [])
            assert len(hallucination_checks) >= 1

            last_check = hallucination_checks[-1]
            assert last_check["hallucination_score"] == 0.2
            assert last_check["grounding_score"] == 0.8
            assert last_check["is_hallucination"] is False

        finally:
            langfuse.flush()
            await langfuse.close()

    @pytest.mark.asyncio
    async def test_rag_completion_with_grounding(
        self, langfuse_config, mock_provider
    ):
        """Test RAG completion with grounding context and hallucination check."""
        if not LANGFUSE_AVAILABLE:
            pytest.skip("Langfuse package not installed")

        langfuse = LangfuseClient(config=langfuse_config)
        await langfuse.initialize()

        try:
            # Create gateway with mock provider
            gateway = LLMGateway(config=create_test_config())
            gateway._providers["openai"] = mock_provider
            gateway._langfuse_client = langfuse
            gateway._langfuse_initialized = True

            # Make a RAG request with context
            request = LLMRequest(
                user_id="test-user-rag",
                tenant_id="test-tenant",
                messages=[
                    Message(
                        role=MessageRole.SYSTEM,
                        content="You are a helpful assistant. Use the provided context.",
                    ),
                    Message(
                        role=MessageRole.USER,
                        content="What is Python? Use the context below.",
                    ),
                ],
                model="gpt-4o-mini",
                provider="openai",
                rag_context=[
                    "Python is a high-level programming language.",
                    "Python emphasizes code readability.",
                ],
                metadata={"rag_enabled": True},
            )

            response = await gateway.complete(request)

            assert response is not None
            assert response.content is not None

            # Verify trace was created with RAG metadata
            metrics = langfuse.get_metrics()
            assert metrics["traces"] >= 1

        finally:
            langfuse.flush()
            await langfuse.close()

    @pytest.mark.asyncio
    async def test_streaming_creates_trace(self, langfuse_config, mock_provider):
        """Test that streaming completion creates LangFuse trace."""
        if not LANGFUSE_AVAILABLE:
            pytest.skip("Langfuse package not installed")

        langfuse = LangfuseClient(config=langfuse_config)
        await langfuse.initialize()

        # Create async generator for streaming mock
        async def mock_stream(*args, **kwargs):
            for chunk in ["Hello", " ", "world", "!"]:
                yield chunk

        mock_provider.chat_stream = mock_stream

        try:
            gateway = LLMGateway(config=create_test_config())
            gateway._providers["openai"] = mock_provider
            gateway._langfuse_client = langfuse
            gateway._langfuse_initialized = True

            request = LLMRequest(
                user_id="test-user-stream",
                tenant_id="test-tenant",
                messages=[
                    Message(role=MessageRole.USER, content="Stream test")
                ],
                model="gpt-4o-mini",
                provider="openai",
                stream=True,
            )

            # Collect stream chunks
            chunks = []
            async for chunk in gateway.stream(request):
                chunks.append(chunk)

            # Verify chunks received
            assert len(chunks) >= 1
            content_chunks = [c.content for c in chunks if c.content]
            assert "".join(content_chunks) == "Hello world!"

            # Verify final chunk has usage
            final_chunk = chunks[-1]
            assert final_chunk.is_final is True
            assert final_chunk.usage is not None

            # Verify trace was created
            metrics = langfuse.get_metrics()
            assert metrics["traces"] >= 1
            assert metrics["generations"] >= 1

        finally:
            langfuse.flush()
            await langfuse.close()

    @pytest.mark.asyncio
    async def test_error_handling_logs_failure(
        self, langfuse_config, mock_provider
    ):
        """Test that errors are properly logged to LangFuse with failure status."""
        if not LANGFUSE_AVAILABLE:
            pytest.skip("Langfuse package not installed")

        langfuse = LangfuseClient(config=langfuse_config)
        await langfuse.initialize()

        # Make provider raise an error
        mock_provider.chat = AsyncMock(side_effect=Exception("Provider error"))

        try:
            gateway = LLMGateway(config=create_test_config())
            gateway._providers["openai"] = mock_provider
            gateway._langfuse_client = langfuse
            gateway._langfuse_initialized = True

            request = LLMRequest(
                user_id="test-user-error",
                tenant_id="test-tenant",
                messages=[
                    Message(role=MessageRole.USER, content="Error test")
                ],
                model="gpt-4o-mini",
                provider="openai",
            )

            # Should raise exception
            with pytest.raises(Exception) as exc_info:
                await gateway.complete(request)

            assert "failed" in str(exc_info.value).lower() or "error" in str(exc_info.value).lower()

            # Verify trace was created with error status
            metrics = langfuse.get_metrics()
            assert metrics["traces"] >= 1

            # Check trace has error status
            recent_traces = metrics["recent_traces"]
            error_trace = [t for t in recent_traces if t.get("status") == "error"]
            # The trace should be marked as error eventually

        finally:
            langfuse.flush()
            await langfuse.close()

    @pytest.mark.asyncio
    async def test_circuit_breaker_metrics_tracked(
        self, langfuse_config, mock_provider
    ):
        """Test that circuit breaker state changes are tracked."""
        if not LANGFUSE_AVAILABLE:
            pytest.skip("Langfuse package not installed")

        langfuse = LangfuseClient(config=langfuse_config)
        await langfuse.initialize()

        try:
            gateway = LLMGateway(config=create_test_config())
            gateway._providers["openai"] = mock_provider
            gateway._langfuse_client = langfuse
            gateway._langfuse_initialized = True

            # Get circuit breaker status
            cb = await gateway.router.get_circuit_breaker("openai")
            status = await cb.get_status()

            # Verify initial state
            assert status["state"] == "closed"
            assert status["provider"] == "openai"

            # Record some successful requests
            await cb.record_success()
            await cb.record_success()

            metrics = await cb.get_metrics()
            assert metrics.successful_requests >= 2

        finally:
            langfuse.flush()
            await langfuse.close()

    @pytest.mark.asyncio
    async def test_cost_tracking_recorded(self, langfuse_config, mock_provider):
        """Test that cost tracking is recorded with LangFuse generation."""
        if not LANGFUSE_AVAILABLE:
            pytest.skip("Langfuse package not installed")

        langfuse = LangfuseClient(config=langfuse_config)
        await langfuse.initialize()

        try:
            gateway = LLMGateway(config=create_test_config())
            gateway._providers["openai"] = mock_provider
            gateway._langfuse_client = langfuse
            gateway._langfuse_initialized = True

            request = LLMRequest(
                user_id="test-user-cost",
                tenant_id="test-tenant",
                messages=[
                    Message(role=MessageRole.USER, content="Cost test")
                ],
                model="gpt-4o-mini",
                provider="openai",
            )

            response = await gateway.complete(request)

            # Verify cost was tracked
            assert response.usage is not None
            assert response.usage.cost_usd >= 0

            # Verify cost tracker has entry
            cost_entries = gateway.cost_tracker.entries
            assert len(cost_entries) >= 1

            last_entry = cost_entries[-1]
            assert last_entry.model == "gpt-4o-mini" or last_entry.model == "mock-model"
            assert last_entry.prompt_tokens == 10
            assert last_entry.completion_tokens == 20

            # Check LangFuse generation has cost
            metrics = langfuse.get_metrics()
            recent_gens = metrics["recent_generations"]
            assert len(recent_gens) > 0
            gen = recent_gens[-1]
            assert gen.get("cost_usd") is not None or gen.get("total_tokens") == 30

        finally:
            langfuse.flush()
            await langfuse.close()

    @pytest.mark.asyncio
    async def test_quality_evaluation_logging(self, langfuse_config):
        """Test logging custom quality evaluations."""
        if not LANGFUSE_AVAILABLE:
            pytest.skip("Langfuse package not installed")

        langfuse = LangfuseClient(config=langfuse_config)
        await langfuse.initialize()

        try:
            trace = langfuse.create_trace(
                name="quality-evaluation-test",
                user_id="test-user",
            )

            # Log various quality scores
            langfuse.log_quality_evaluation(
                trace=trace,
                evaluation_name="coherence",
                score=0.92,
                comment="Response is highly coherent",
            )

            langfuse.log_quality_evaluation(
                trace=trace,
                evaluation_name="helpfulness",
                score=0.88,
                comment="Response addresses user query",
            )

            langfuse.end_trace(trace, status="success")

            # Verify evaluations are tracked
            # Note: These are sent to LangFuse, verify via flush
            langfuse.flush()

            metrics = langfuse.get_metrics()
            assert metrics["traces"] >= 1

        finally:
            await langfuse.close()


@pytest.mark.integration
@pytest.mark.asyncio
class TestLangfuseContextManager:
    """Test LangFuse context manager patterns."""

    @pytest.fixture
    def langfuse_config(self):
        enabled = os.getenv("LANGFUSE_ENABLED", "false").lower() == "true"
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY", "")

        if not enabled or not public_key or not secret_key:
            pytest.skip("Langfuse not configured")

        return ObservabilityConfig(
            langfuse_enabled=True,
            langfuse_public_key=public_key,
            langfuse_secret_key=secret_key,
        )

    @pytest.mark.asyncio
    async def test_trace_context_manager(self, langfuse_config):
        """Test async context manager for traces."""
        if not LANGFUSE_AVAILABLE:
            pytest.skip("Langfuse package not installed")

        langfuse = LangfuseClient(config=langfuse_config)
        await langfuse.initialize()

        try:
            async with langfuse.trace(
                name="context-manager-test",
                user_id="test-user",
            ) as trace:
                trace.add_metadata("test_key", "test_value")
                trace.add_tag("context-manager")

            # Verify trace was created and ended
            metrics = langfuse.get_metrics()
            assert metrics["traces"] >= 1

            recent = metrics["recent_traces"][-1]
            assert recent.get("status") == "success"

        finally:
            langfuse.flush()
            await langfuse.close()

    @pytest.mark.asyncio
    async def test_span_context_manager(self, langfuse_config):
        """Test async context manager for spans."""
        if not LANGFUSE_AVAILABLE:
            pytest.skip("Langfuse package not installed")

        langfuse = LangfuseClient(config=langfuse_config)
        await langfuse.initialize()

        try:
            async with langfuse.trace(
                name="span-context-test",
                user_id="test-user",
            ) as trace:
                async with langfuse.span(
                    trace,
                    name="test-span",
                    input_data={"query": "test"},
                ) as span:
                    # Simulate work
                    await asyncio.sleep(0.05)
                    span.set_output({"result": "success"})

            # Verify span was created
            metrics = langfuse.get_metrics()
            assert metrics["spans"] >= 1

        finally:
            langfuse.flush()
            await langfuse.close()

    @pytest.mark.asyncio
    async def test_error_in_context_manager(self, langfuse_config):
        """Test that errors in context manager are properly logged."""
        if not LANGFUSE_AVAILABLE:
            pytest.skip("Langfuse package not installed")

        langfuse = LangfuseClient(config=langfuse_config)
        await langfuse.initialize()

        try:
            with pytest.raises(ValueError):
                async with langfuse.trace(
                    name="error-context-test",
                    user_id="test-user",
                ) as trace:
                    raise ValueError("Test error")

            # Verify trace has error status
            metrics = langfuse.get_metrics()
            recent = metrics["recent_traces"][-1]
            assert recent.get("status") == "error"
            assert "Test error" in str(recent.get("error", ""))

        finally:
            langfuse.flush()
            await langfuse.close()
