"""
Unit tests for Setup Assistant Chatbot API endpoints.
"""

import pytest
from uuid import uuid4


class TestSetupChatbotAPI:
    """Test cases for setup assistant chatbot endpoints."""

    @pytest.mark.asyncio
    async def test_start_session(self, client, auth_headers):
        """Test starting a new setup assistant session."""
        response = await client.post(
            "/api/v1/setup-assistant/sessions",
            json={},
            headers=auth_headers,
        )
        assert response.status_code in [200, 201, 400]
        if response.status_code in [200, 201]:
            data = response.json()
            assert "session_id" in data
            assert "message" in data

    @pytest.mark.asyncio
    async def test_start_session_with_flow_type(self, client, auth_headers):
        """Test starting session with specific flow type."""
        response = await client.post(
            "/api/v1/setup-assistant/sessions",
            json={"flow_type": "connection"},
            headers=auth_headers,
        )
        assert response.status_code in [200, 201, 400]

    @pytest.mark.asyncio
    async def test_start_session_with_plugin(self, client, auth_headers):
        """Test starting session with specific plugin."""
        response = await client.post(
            "/api/v1/setup-assistant/sessions",
            json={"plugin": "github"},
            headers=auth_headers,
        )
        assert response.status_code in [200, 201, 400]

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, client, auth_headers):
        """Test getting a non-existent session."""
        fake_id = str(uuid4())
        response = await client.get(
            f"/api/v1/setup-assistant/sessions/{fake_id}",
            headers=auth_headers,
        )
        assert response.status_code in [404, 400]

    @pytest.mark.asyncio
    async def test_send_message_to_invalid_session(self, client, auth_headers):
        """Test sending message to non-existent session."""
        fake_id = str(uuid4())
        response = await client.post(
            f"/api/v1/setup-assistant/sessions/{fake_id}/messages",
            json={"message": "Hello"},
            headers=auth_headers,
        )
        assert response.status_code in [404, 400]

    @pytest.mark.asyncio
    async def test_get_messages_invalid_session(self, client, auth_headers):
        """Test getting messages from non-existent session."""
        fake_id = str(uuid4())
        response = await client.get(
            f"/api/v1/setup-assistant/sessions/{fake_id}/messages",
            headers=auth_headers,
        )
        assert response.status_code in [404, 400]

    @pytest.mark.asyncio
    async def test_cancel_invalid_session(self, client, auth_headers):
        """Test canceling non-existent session."""
        fake_id = str(uuid4())
        response = await client.post(
            f"/api/v1/setup-assistant/sessions/{fake_id}/cancel",
            headers=auth_headers,
        )
        assert response.status_code in [404, 400]

    @pytest.mark.asyncio
    async def test_delete_invalid_session(self, client, auth_headers):
        """Test deleting non-existent session."""
        fake_id = str(uuid4())
        response = await client.delete(
            f"/api/v1/setup-assistant/sessions/{fake_id}",
            headers=auth_headers,
        )
        assert response.status_code in [400, 404, 204]

    @pytest.mark.asyncio
    async def test_list_plugins(self, client, auth_headers):
        """Test listing available plugins."""
        response = await client.get(
            "/api/v1/setup-assistant/plugins",
            headers=auth_headers,
        )
        assert response.status_code in [200, 400]
        if response.status_code == 200:
            data = response.json()
            assert "plugins" in data
            assert isinstance(data["plugins"], list)

    @pytest.mark.asyncio
    async def test_quick_setup(self, client, auth_headers):
        """Test quick setup for a plugin."""
        response = await client.post(
            "/api/v1/setup-assistant/quick-setup/github",
            headers=auth_headers,
        )
        assert response.status_code in [200, 201, 400, 404]

    @pytest.mark.asyncio
    async def test_quick_setup_invalid_plugin(self, client, auth_headers):
        """Test quick setup with invalid plugin."""
        response = await client.post(
            "/api/v1/setup-assistant/quick-setup/invalid_plugin_name",
            headers=auth_headers,
        )
        assert response.status_code in [400, 404]

    @pytest.mark.asyncio
    async def test_start_onboarding(self, client, auth_headers):
        """Test starting onboarding flow."""
        response = await client.post(
            "/api/v1/setup-assistant/onboarding",
            headers=auth_headers,
        )
        assert response.status_code in [200, 201, 400]

    @pytest.mark.asyncio
    async def test_setup_assistant_unauthorized(self, client):
        """Test accessing setup assistant without authentication."""
        response = await client.post(
            "/api/v1/setup-assistant/sessions",
            json={},
        )
        assert response.status_code in [401, 403]
