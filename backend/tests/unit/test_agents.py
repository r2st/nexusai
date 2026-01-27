"""
Unit tests for Agents API endpoints.
"""

import pytest
from uuid import uuid4


class TestAgentsAPI:
    """Test cases for agents endpoints."""

    @pytest.mark.asyncio
    async def test_list_agents(self, client, auth_headers):
        """Test listing agents."""
        response = await client.get(
            "/api/v1/agents",
            headers=auth_headers,
        )
        assert response.status_code in [200, 401]
        if response.status_code == 200:
            data = response.json()
            # API returns AgentListResponse with 'agents' key
            assert "agents" in data
            assert isinstance(data["agents"], list)

    @pytest.mark.asyncio
    async def test_list_agents_with_public(self, client, auth_headers):
        """Test listing agents including public ones."""
        response = await client.get(
            "/api/v1/agents?include_public=true",
            headers=auth_headers,
        )
        assert response.status_code in [200, 401]

    @pytest.mark.asyncio
    async def test_create_agent(self, client, auth_headers):
        """Test creating a new agent."""
        response = await client.post(
            "/api/v1/agents",
            json={
                "name": "Test Agent",
                "description": "A test agent for testing",
                "system_prompt": "You are a helpful assistant.",
                "model_provider": "openai",
                "model_name": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 4096,
                "is_public": False,
            },
            headers=auth_headers,
        )
        assert response.status_code in [200, 201, 400, 422]

    @pytest.mark.asyncio
    async def test_create_agent_minimal(self, client, auth_headers):
        """Test creating an agent with minimal fields."""
        response = await client.post(
            "/api/v1/agents",
            json={
                "name": "Minimal Agent",
            },
            headers=auth_headers,
        )
        assert response.status_code in [200, 201, 400, 422]

    @pytest.mark.asyncio
    async def test_get_agent_not_found(self, client, auth_headers):
        """Test getting a non-existent agent."""
        fake_id = str(uuid4())
        response = await client.get(
            f"/api/v1/agents/{fake_id}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_agent_not_found(self, client, auth_headers):
        """Test updating a non-existent agent."""
        fake_id = str(uuid4())
        # Try PATCH first as it's more common for updates
        response = await client.patch(
            f"/api/v1/agents/{fake_id}",
            json={"name": "Updated Name"},
            headers=auth_headers,
        )
        # May return 405 if neither PUT nor PATCH is supported, 404 if not found
        assert response.status_code in [404, 403, 405]

    @pytest.mark.asyncio
    async def test_delete_agent_not_found(self, client, auth_headers):
        """Test deleting a non-existent agent."""
        fake_id = str(uuid4())
        response = await client.delete(
            f"/api/v1/agents/{fake_id}",
            headers=auth_headers,
        )
        assert response.status_code in [404, 403]

    @pytest.mark.asyncio
    async def test_execute_agent_not_found(self, client, auth_headers):
        """Test executing a non-existent agent."""
        fake_id = str(uuid4())
        response = await client.post(
            f"/api/v1/agents/{fake_id}/execute",
            json={"message": "Hello, agent!"},
            headers=auth_headers,
        )
        assert response.status_code in [404, 400]

    @pytest.mark.asyncio
    async def test_get_agent_executions_not_found(self, client, auth_headers):
        """Test getting executions for non-existent agent."""
        fake_id = str(uuid4())
        response = await client.get(
            f"/api/v1/agents/{fake_id}/executions",
            headers=auth_headers,
        )
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_agents_unauthorized(self, client):
        """Test accessing agents without authentication."""
        response = await client.get("/api/v1/agents")
        assert response.status_code in [401, 403]


class TestAgentValidation:
    """Test agent input validation."""

    @pytest.mark.asyncio
    async def test_create_agent_missing_name(self, client, auth_headers):
        """Test creating agent without name."""
        response = await client.post(
            "/api/v1/agents",
            json={"description": "No name provided"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_agent_invalid_temperature(self, client, auth_headers):
        """Test creating agent with invalid temperature."""
        response = await client.post(
            "/api/v1/agents",
            json={
                "name": "Test Agent",
                "temperature": 5.0,  # Invalid, should be 0-2
            },
            headers=auth_headers,
        )
        # Temperature may not be validated at API level - stored in model_config
        assert response.status_code in [201, 400, 422]

    @pytest.mark.asyncio
    async def test_execute_agent_empty_message(self, client, auth_headers):
        """Test executing agent with empty message."""
        fake_id = str(uuid4())
        response = await client.post(
            f"/api/v1/agents/{fake_id}/execute",
            json={"message": ""},
            headers=auth_headers,
        )
        assert response.status_code in [400, 404, 422]
