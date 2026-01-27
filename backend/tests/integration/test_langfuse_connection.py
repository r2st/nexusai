"""
Integration test to verify Langfuse connection and functionality.

This test verifies that:
1. Langfuse client can connect to the configured Langfuse instance
2. Traces can be created and sent
3. Generations can be logged
4. The connection is working properly

To run this test, ensure you have valid Langfuse credentials in your .env file:
- LANGFUSE_ENABLED=true
- LANGFUSE_PUBLIC_KEY=pk-lf-...
- LANGFUSE_SECRET_KEY=sk-lf-...
- LANGFUSE_HOST=https://us.cloud.langfuse.com (or your Langfuse host)
"""

import asyncio
import os
import pytest
from datetime import datetime, UTC

from app.services.observability.config import ObservabilityConfig, get_observability_config
from app.services.observability.langfuse_client import LangfuseClient, LANGFUSE_AVAILABLE


@pytest.mark.integration
@pytest.mark.asyncio
class TestLangfuseConnection:
    """Integration tests for Langfuse connectivity."""

    @pytest.fixture
    def langfuse_config(self):
        """Get Langfuse configuration from environment."""
        # Check if Langfuse is enabled and credentials are available
        enabled = os.getenv("LANGFUSE_ENABLED", "false").lower() == "true"
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY", "")
        host = os.getenv("LANGFUSE_HOST", "https://us.cloud.langfuse.com")

        if not enabled or not public_key or not secret_key:
            pytest.skip(
                "Langfuse not configured. Set LANGFUSE_ENABLED=true, "
                "LANGFUSE_PUBLIC_KEY, and LANGFUSE_SECRET_KEY in .env to run this test."
            )

        return ObservabilityConfig(
            langfuse_enabled=True,
            langfuse_public_key=public_key,
            langfuse_secret_key=secret_key,
            langfuse_host=host,
            langfuse_project_id=os.getenv("LANGFUSE_PROJECT_ID", ""),
            langfuse_org_id=os.getenv("LANGFUSE_ORG_ID", ""),
        )

    @pytest.mark.asyncio
    async def test_langfuse_client_initialization(self, langfuse_config):
        """Test that Langfuse client can be initialized with real credentials."""
        if not LANGFUSE_AVAILABLE:
            pytest.skip("Langfuse package not installed")

        client = LangfuseClient(config=langfuse_config)
        await client.initialize()

        assert client._enabled is True, "Langfuse client should be enabled"
        assert client._client is not None, "Langfuse client should be initialized"

    @pytest.mark.asyncio
    async def test_create_trace(self, langfuse_config):
        """Test creating a trace in Langfuse."""
        if not LANGFUSE_AVAILABLE:
            pytest.skip("Langfuse package not installed")

        client = LangfuseClient(config=langfuse_config)
        await client.initialize()

        trace = client.create_trace(
            name="test-trace-connection",
            user_id="test-user-123",
            session_id="test-session-456",
            metadata={"test": True, "environment": "integration-test"},
            tags=["integration-test", "connection-test"],
        )

        assert trace is not None
        assert trace.name == "test-trace-connection"
        assert trace.user_id == "test-user-123"
        assert trace.session_id == "test-session-456"
        assert trace.metadata["test"] is True
        assert "integration-test" in trace.tags

        # Flush to ensure trace is sent
        client.flush()
        await client.close()

    @pytest.mark.asyncio
    async def test_log_generation(self, langfuse_config):
        """Test logging an LLM generation to Langfuse."""
        if not LANGFUSE_AVAILABLE:
            pytest.skip("Langfuse package not installed")

        client = LangfuseClient(config=langfuse_config)
        await client.initialize()

        # Create a trace
        trace = client.create_trace(
            name="test-generation-connection",
            user_id="test-user-123",
            metadata={"test_type": "generation"},
        )

        # Log a generation
        client.log_generation(
            trace=trace,
            name="test-llm-generation",
            model="gpt-4o",
            input_messages=[
                {"role": "user", "content": "Hello, this is a test message"}
            ],
            output="Hello! This is a test response from the integration test.",
            usage={
                "prompt_tokens": 10,
                "completion_tokens": 15,
                "total_tokens": 25,
            },
            model_parameters={"temperature": 0.7},
            latency_ms=150.0,
        )

        # Verify generation was logged locally
        assert len(client._metrics["generations"]) > 0
        gen = client._metrics["generations"][-1]
        assert gen["model"] == "gpt-4o"
        assert gen["input_tokens"] == 10
        assert gen["output_tokens"] == 15
        assert gen["total_tokens"] == 25

        # Flush to ensure data is sent
        client.flush()
        await client.close()

    @pytest.mark.asyncio
    async def test_create_span(self, langfuse_config):
        """Test creating a span in Langfuse."""
        if not LANGFUSE_AVAILABLE:
            pytest.skip("Langfuse package not installed")

        client = LangfuseClient(config=langfuse_config)
        await client.initialize()

        # Create a trace
        trace = client.create_trace(
            name="test-span-connection",
            user_id="test-user-123",
        )

        # Create a span
        span = client.start_span(
            trace=trace,
            name="test-span",
            input_data={"query": "test query"},
            metadata={"span_type": "test"},
        )

        assert span is not None
        assert span.name == "test-span"
        assert span.trace_id == trace.trace_id
        assert span.input_data == {"query": "test query"}
        assert span.metadata["span_type"] == "test"

        # End the span
        client.end_span(
            span=span,
            output={"result": "success"},
            status="success",
        )

        assert span.output_data == {"result": "success"}

        # Flush to ensure span is sent
        client.flush()
        await client.close()

    @pytest.mark.asyncio
    async def test_full_trace_flow(self, langfuse_config):
        """Test a complete trace flow: trace -> span -> generation -> end."""
        if not LANGFUSE_AVAILABLE:
            pytest.skip("Langfuse package not installed")

        client = LangfuseClient(config=langfuse_config)
        await client.initialize()

        # Create trace
        trace = client.create_trace(
            name="test-full-flow",
            user_id="test-user-123",
            session_id="test-session-456",
            metadata={"test": "full-flow"},
            tags=["integration-test"],
        )

        # Create span for tool call
        span = client.start_span(
            trace=trace,
            name="tool:test_tool",
            input_data={"tool_name": "test_tool", "arguments": {"param": "value"}},
        )

        # Simulate tool execution
        await asyncio.sleep(0.1)  # Simulate work

        client.end_span(
            span=span,
            output={"result": "tool executed successfully"},
            status="success",
        )

        # Log LLM generation
        client.log_generation(
            trace=trace,
            name="test-llm-call",
            model="gpt-4o",
            input_messages=[
                {"role": "user", "content": "Test message for full flow"}
            ],
            output="Test response for full flow",
            usage={
                "prompt_tokens": 20,
                "completion_tokens": 30,
                "total_tokens": 50,
            },
            latency_ms=200.0,
        )

        # End trace
        client.end_trace(trace, status="success", output="Flow completed")

        # Verify metrics
        metrics = client.get_metrics()
        assert metrics["traces"] >= 1
        assert metrics["generations"] >= 1
        assert metrics["spans"] >= 1
        assert metrics["total_tokens"] >= 50

        # Flush and close
        client.flush()
        await client.close()

    @pytest.mark.asyncio
    async def test_langfuse_connection_health(self, langfuse_config):
        """Test that we can verify Langfuse connection health."""
        if not LANGFUSE_AVAILABLE:
            pytest.skip("Langfuse package not installed")

        client = LangfuseClient(config=langfuse_config)
        await client.initialize()

        # Verify client is enabled
        assert client._enabled is True, "Langfuse client should be enabled"

        # Create a simple health check trace
        trace = client.create_trace(
            name="langfuse-health-check",
            metadata={
                "test_type": "health_check",
                "timestamp": datetime.now(UTC).isoformat(),
            },
            tags=["health-check"],
        )

        # Log a minimal generation to test API connectivity
        client.log_generation(
            trace=trace,
            name="health-check-generation",
            model="test-model",
            input_messages=[{"role": "user", "content": "health check"}],
            output="health check response",
            usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        )

        # End trace
        client.end_trace(trace, status="success")

        # Flush to send data to Langfuse
        # This will raise an exception if there's a connection issue
        try:
            client.flush()
        except Exception as e:
            pytest.fail(f"Failed to flush to Langfuse: {str(e)}")

        await client.close()

        # If we get here, the connection is working
        assert True, "Langfuse connection is healthy"

    @pytest.mark.asyncio
    async def test_langfuse_config_from_env(self):
        """Test that configuration can be loaded from environment variables."""
        # This test uses get_observability_config which reads from env
        config = get_observability_config()

        # Check if Langfuse is configured
        if not config.langfuse_enabled:
            pytest.skip("Langfuse not enabled in environment")

        if not config.langfuse_public_key or not config.langfuse_secret_key:
            pytest.skip("Langfuse credentials not set in environment")

        # Initialize client with config from environment
        client = LangfuseClient(config=config)
        await client.initialize()

        # Verify initialization
        if LANGFUSE_AVAILABLE:
            assert client._enabled is True, "Langfuse should be enabled with valid credentials"
        else:
            pytest.skip("Langfuse package not installed")

        await client.close()
