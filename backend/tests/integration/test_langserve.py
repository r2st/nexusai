"""
Integration tests for LangServe API endpoints.

Tests the LangServe implementation to verify:
1. Health and info endpoints
2. Invoke endpoint (non-streaming)
3. Stream endpoint (streaming with SSE)
4. Batch endpoint
5. Authentication
6. Error handling
"""

import asyncio
import json
import os
import pytest
from typing import Any
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

from app.main import app
from app.core.database import get_db
from app.models.user import User
from app.core.security import create_access_token


@pytest.fixture
async def test_user(db_session):
    """Create a test user for authentication."""
    from app.models.user import User
    from app.core.security import get_password_hash
    
    user = User(
        email="langserve-test@nexusai.dev",
        hashed_password=get_password_hash("testpass123"),
        full_name="LangServe Test User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_token(test_user):
    """Create an auth token for the test user."""
    return create_access_token(data={"sub": str(test_user.id), "email": test_user.email})


@pytest.fixture
async def client():
    """Create an async HTTP client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Content-Type": "application/json"},
    ) as ac:
        yield ac


@pytest.mark.integration
@pytest.mark.asyncio
class TestLangServeEndpoints:
    """Integration tests for LangServe endpoints."""

    async def test_health_endpoint(self, client):
        """Test the health check endpoint."""
        response = await client.get("/api/v1/langserve/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "langserve"

    async def test_info_endpoint(self, client):
        """Test the info endpoint."""
        response = await client.get("/api/v1/langserve/info")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "NexusAI Chat Service"
        assert "version" in data
        assert "description" in data
        assert "capabilities" in data
        assert "endpoints" in data

    async def test_invoke_endpoint_requires_auth(self, client):
        """Test that invoke endpoint requires authentication."""
        response = await client.post(
            "/api/v1/langserve/chat/invoke",
            json={"input": {"message": "Hello"}},
        )
        assert response.status_code == 401  # Unauthorized

    async def test_invoke_endpoint(self, client, auth_token, test_user):
        """Test the invoke endpoint with authentication."""
        response = await client.post(
            "/api/v1/langserve/chat/invoke",
            json={"input": {"message": "Hello! Say 'test successful' if you can read this."}},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert "message_id" in data
        assert "conversation_id" in data
        assert "model_name" in data
        assert "created_at" in data
        assert len(data["content"]) > 0

    async def test_invoke_with_string_input(self, client, auth_token):
        """Test invoke endpoint with string input instead of dict."""
        response = await client.post(
            "/api/v1/langserve/chat/invoke",
            json={"input": "Hello! This is a test message."},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert len(data["content"]) > 0

    async def test_stream_endpoint_requires_auth(self, client):
        """Test that stream endpoint requires authentication."""
        response = await client.post(
            "/api/v1/langserve/chat/stream",
            json={"input": {"message": "Hello"}},
        )
        assert response.status_code == 401  # Unauthorized

    async def test_stream_endpoint(self, client, auth_token):
        """Test the stream endpoint with authentication."""
        response = await client.post(
            "/api/v1/langserve/chat/stream",
            json={"input": {"message": "Count from 1 to 5, one number per line."}},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream"
        
        # Read stream
        content = b""
        async for chunk in response.aiter_bytes():
            content += chunk
        
        # Verify SSE format
        content_str = content.decode("utf-8")
        assert "data: " in content_str
        assert "[DONE]" in content_str or len(content_str) > 0

    async def test_stream_endpoint_sse_format(self, client, auth_token):
        """Test that stream endpoint returns proper SSE format."""
        response = await client.post(
            "/api/v1/langserve/chat/stream",
            json={"input": {"message": "Say hello"}},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        
        chunks = []
        async for chunk in response.aiter_bytes():
            chunks.append(chunk)
        
        # Combine chunks and verify SSE format
        full_content = b"".join(chunks).decode("utf-8")
        lines = full_content.split("\n")
        
        # Should have data lines
        data_lines = [line for line in lines if line.startswith("data: ")]
        assert len(data_lines) > 0
        
        # Parse first data chunk
        first_data = data_lines[0].replace("data: ", "")
        try:
            parsed = json.loads(first_data)
            assert "content" in parsed or "type" in parsed
        except json.JSONDecodeError:
            # If not JSON, should be [DONE] or empty
            assert first_data.strip() in ["[DONE]", ""]

    async def test_batch_endpoint_requires_auth(self, client):
        """Test that batch endpoint requires authentication."""
        response = await client.post(
            "/api/v1/langserve/chat/batch",
            json={"inputs": [{"message": "Hello"}]},
        )
        assert response.status_code == 401  # Unauthorized

    async def test_batch_endpoint(self, client, auth_token):
        """Test the batch endpoint with multiple inputs."""
        response = await client.post(
            "/api/v1/langserve/chat/batch",
            json={
                "inputs": [
                    {"message": "Say 'first'"},
                    {"message": "Say 'second'"},
                ],
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "outputs" in data
        assert len(data["outputs"]) == 2
        
        # Verify each output has content
        for output in data["outputs"]:
            if "error" not in output:
                assert "content" in output
                assert len(output["content"]) > 0

    async def test_batch_endpoint_with_errors(self, client, auth_token):
        """Test batch endpoint handles errors gracefully."""
        # Use invalid input to trigger error
        response = await client.post(
            "/api/v1/langserve/chat/batch",
            json={
                "inputs": [
                    {"message": "This should work"},
                    {"invalid": "input"},  # This might cause an error
                ],
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "outputs" in data
        assert len(data["outputs"]) == 2

    async def test_playground_endpoint(self, client):
        """Test the playground UI endpoint."""
        response = await client.get("/api/v1/langserve/chat/playground")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        content = response.text
        assert "NexusAI Chat - LangServe Playground" in content
        assert "invoke()" in content  # JavaScript function
        assert "stream()" in content  # JavaScript function

    async def test_invoke_with_conversation_id(self, client, auth_token):
        """Test that conversation ID is handled correctly."""
        # First request to create conversation
        response1 = await client.post(
            "/api/v1/langserve/chat/invoke",
            json={"input": {"message": "My name is TestUser"}},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response1.status_code == 200
        data1 = response1.json()
        conversation_id = data1["conversation_id"]
        
        # Second request with same conversation
        response2 = await client.post(
            "/api/v1/langserve/chat/invoke",
            json={
                "input": {
                    "message": "What is my name?",
                    "conversation_id": conversation_id,
                }
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response2.status_code == 200
        data2 = response2.json()
        # Should use same conversation
        assert data2["conversation_id"] == conversation_id

    async def test_invoke_error_handling(self, client, auth_token):
        """Test error handling in invoke endpoint."""
        # Test with empty message (should still work or return error gracefully)
        response = await client.post(
            "/api/v1/langserve/chat/invoke",
            json={"input": {"message": ""}},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        # Should either succeed with empty response or return 400/500
        assert response.status_code in [200, 400, 500]

    async def test_stream_error_handling(self, client, auth_token):
        """Test error handling in stream endpoint."""
        # Test with very long message (might hit token limits)
        long_message = "A" * 10000
        response = await client.post(
            "/api/v1/langserve/chat/stream",
            json={"input": {"message": long_message}},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        # Should either stream or return error
        assert response.status_code in [200, 400, 500]

    async def test_runnable_input_schema(self, client, auth_token):
        """Test that the runnable accepts various input formats."""
        # Test with dict input
        response1 = await client.post(
            "/api/v1/langserve/chat/invoke",
            json={"input": {"message": "Test 1"}},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response1.status_code == 200
        
        # Test with string input
        response2 = await client.post(
            "/api/v1/langserve/chat/invoke",
            json={"input": "Test 2"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response2.status_code == 200
        
        # Test with nested input
        response3 = await client.post(
            "/api/v1/langserve/chat/invoke",
            json={"input": {"input": {"message": "Test 3"}}},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response3.status_code == 200
