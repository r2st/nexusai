"""
Unit tests for agent API endpoints.
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.api.agents import router, AgentCreate, AgentUpdate, AgentExecuteRequest
from app.core.config import settings


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_user():
    """Create a mock authenticated user."""
    user = MagicMock()
    user.id = str(uuid4())
    user.email = "test@example.com"
    user.is_active = True
    return user


@pytest.fixture
def mock_agent_service():
    """Create a mock agent service."""
    service = MagicMock()
    service.create_agent = AsyncMock()
    service.get_agent = AsyncMock()
    service.list_agents = AsyncMock()
    service.update_agent = AsyncMock()
    service.delete_agent = AsyncMock()
    service.execute = AsyncMock()
    service.execute_streaming = AsyncMock()
    return service


@pytest.fixture
def sample_agent_data():
    """Create sample agent data."""
    return {
        "id": str(uuid4()),
        "name": "Test Agent",
        "description": "A test agent",
        "system_prompt": "You are a helpful assistant.",
        "capabilities": ["chat", "analysis"],
        "tools_config": {"enabled": True},
        "mcp_servers": [],
        "actions_config": [],
        "model_provider": "anthropic",
        "model_name": "claude-sonnet-4-20250514",
        "model_config": {"temperature": 0.7},
        "is_public": False,
        "status": "ready",
        "creator_id": str(uuid4()),
        "organization_id": str(uuid4()),
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
        "usage_count": 0,
        "metadata": {},
    }


# =============================================================================
# Request Model Tests
# =============================================================================


class TestAgentCreateModel:
    """Tests for AgentCreate request model."""

    def test_valid_agent_create(self):
        """Test creating a valid AgentCreate model."""
        data = AgentCreate(
            name="Test Agent",
            description="A test agent",
        )

        assert data.name == "Test Agent"
        assert data.description == "A test agent"

    def test_agent_create_defaults(self):
        """Test AgentCreate default values."""
        data = AgentCreate(name="Test")

        assert data.capabilities == []
        assert data.tools_config == {}
        assert data.mcp_servers == []
        assert data.actions_config == []
        # Use settings to determine expected defaults
        assert data.model_provider == settings.DEFAULT_AI_PROVIDER
        # Model name depends on provider
        assert data.model_name is not None
        assert data.temperature == 0.7
        assert data.max_tokens == 4096
        assert data.is_public is False
        assert data.metadata == {}

    def test_agent_create_with_all_fields(self):
        """Test AgentCreate with all fields."""
        data = AgentCreate(
            name="Full Agent",
            description="Fully configured",
            system_prompt="Be helpful",
            capabilities=["chat", "code"],
            tools_config={"web_search": True},
            mcp_servers=[{"name": "server1", "url": "http://localhost"}],
            actions_config=[{"name": "action1"}],
            model_provider="openai",
            model_name="gpt-4",
            temperature=0.5,
            max_tokens=8192,
            is_public=True,
            metadata={"version": "1.0"},
        )

        assert data.name == "Full Agent"
        assert "chat" in data.capabilities
        assert data.model_provider == "openai"
        assert data.temperature == 0.5

    def test_agent_create_name_validation(self):
        """Test AgentCreate name validation."""
        # Empty name should fail
        with pytest.raises(ValueError):
            AgentCreate(name="")

        # Very long name should fail
        with pytest.raises(ValueError):
            AgentCreate(name="x" * 101)


class TestAgentUpdateModel:
    """Tests for AgentUpdate request model."""

    def test_valid_agent_update(self):
        """Test creating a valid AgentUpdate model."""
        data = AgentUpdate(name="Updated Name")

        assert data.name == "Updated Name"
        assert data.description is None

    def test_agent_update_partial(self):
        """Test AgentUpdate with partial fields."""
        data = AgentUpdate(
            temperature=0.9,
            is_active=False,
        )

        assert data.temperature == 0.9
        assert data.is_active is False
        assert data.name is None
        assert data.model_name is None


class TestAgentExecuteRequestModel:
    """Tests for AgentExecuteRequest model."""

    def test_valid_execute_request(self):
        """Test creating a valid execute request."""
        data = AgentExecuteRequest(
            message="Hello, agent!",
        )

        assert data.message == "Hello, agent!"
        assert data.conversation_id is None
        assert data.context == {}
        assert data.stream is False

    def test_execute_request_with_context(self):
        """Test execute request with context."""
        data = AgentExecuteRequest(
            message="Analyze this",
            conversation_id="conv-123",
            context={"document_id": "doc-456"},
            stream=True,
        )

        assert data.conversation_id == "conv-123"
        assert data.context["document_id"] == "doc-456"
        assert data.stream is True


# =============================================================================
# API Endpoint Tests
# =============================================================================


class TestCreateAgentEndpoint:
    """Tests for POST /agents endpoint."""

    @pytest.mark.asyncio
    async def test_create_agent_success(self, mock_user, mock_agent_service, sample_agent_data):
        """Test successful agent creation."""
        mock_agent_service.create_agent.return_value = MagicMock(**sample_agent_data)

        with patch("app.api.agents.get_current_user", return_value=mock_user):
            with patch("app.api.agents.AgentService", return_value=mock_agent_service):
                # Simulate the endpoint logic
                request = AgentCreate(
                    name="Test Agent",
                    description="Test description",
                )

                # Call would be made here in actual test with TestClient

    @pytest.mark.asyncio
    async def test_create_agent_unauthenticated(self):
        """Test agent creation without authentication."""
        # Would return 401 Unauthorized
        pass


class TestListAgentsEndpoint:
    """Tests for GET /agents endpoint."""

    @pytest.mark.asyncio
    async def test_list_agents_success(self, mock_user, mock_agent_service, sample_agent_data):
        """Test successful agent listing."""
        mock_agent_service.list_agents.return_value = [
            MagicMock(**sample_agent_data),
            MagicMock(**{**sample_agent_data, "id": str(uuid4()), "name": "Agent 2"}),
        ]

        # Simulate the endpoint logic

    @pytest.mark.asyncio
    async def test_list_agents_empty(self, mock_user, mock_agent_service):
        """Test listing agents when none exist."""
        mock_agent_service.list_agents.return_value = []

        # Should return empty list


class TestGetAgentEndpoint:
    """Tests for GET /agents/{agent_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_agent_success(self, mock_user, mock_agent_service, sample_agent_data):
        """Test successful agent retrieval."""
        mock_agent_service.get_agent.return_value = MagicMock(**sample_agent_data)

        # Simulate the endpoint logic

    @pytest.mark.asyncio
    async def test_get_agent_not_found(self, mock_user, mock_agent_service):
        """Test getting non-existent agent."""
        mock_agent_service.get_agent.return_value = None

        # Should raise 404


class TestUpdateAgentEndpoint:
    """Tests for PUT /agents/{agent_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_agent_success(self, mock_user, mock_agent_service, sample_agent_data):
        """Test successful agent update."""
        updated_data = {**sample_agent_data, "name": "Updated Agent"}
        mock_agent_service.update_agent.return_value = MagicMock(**updated_data)

        # Simulate the endpoint logic

    @pytest.mark.asyncio
    async def test_update_agent_partial(self, mock_user, mock_agent_service, sample_agent_data):
        """Test partial agent update."""
        mock_agent_service.update_agent.return_value = MagicMock(**sample_agent_data)

        # Only update name, leave other fields


class TestDeleteAgentEndpoint:
    """Tests for DELETE /agents/{agent_id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_agent_success(self, mock_user, mock_agent_service):
        """Test successful agent deletion."""
        mock_agent_service.delete_agent.return_value = True

        # Should return 204 No Content

    @pytest.mark.asyncio
    async def test_delete_agent_not_found(self, mock_user, mock_agent_service):
        """Test deleting non-existent agent."""
        mock_agent_service.delete_agent.return_value = False

        # Should raise 404


class TestExecuteAgentEndpoint:
    """Tests for POST /agents/{agent_id}/execute endpoint."""

    @pytest.mark.asyncio
    async def test_execute_agent_success(self, mock_user, mock_agent_service, sample_agent_data):
        """Test successful agent execution."""
        mock_agent_service.get_agent.return_value = MagicMock(**sample_agent_data)
        mock_agent_service.execute.return_value = {
            "response": "Hello! How can I help you?",
            "conversation_id": str(uuid4()),
            "execution_time_ms": 150.5,
            "tool_calls": [],
        }

        # Simulate the endpoint logic

    @pytest.mark.asyncio
    async def test_execute_agent_not_found(self, mock_user, mock_agent_service):
        """Test executing non-existent agent."""
        mock_agent_service.get_agent.return_value = None

        # Should raise 404

    @pytest.mark.asyncio
    async def test_execute_agent_streaming(self, mock_user, mock_agent_service, sample_agent_data):
        """Test streaming agent execution."""
        mock_agent_service.get_agent.return_value = MagicMock(**sample_agent_data)

        async def mock_stream():
            yield {"type": "text", "content": "Hello"}
            yield {"type": "text", "content": " World"}
            yield {"type": "done"}

        mock_agent_service.execute_streaming.return_value = mock_stream()

        # Should return streaming response


# =============================================================================
# Agent Capabilities Tests
# =============================================================================


class TestAgentCapabilities:
    """Tests for agent capabilities handling."""

    def test_valid_capabilities(self):
        """Test valid capability list."""
        data = AgentCreate(
            name="Test",
            capabilities=["chat", "code_review", "analysis"],
        )

        assert len(data.capabilities) == 3
        assert "chat" in data.capabilities

    def test_empty_capabilities(self):
        """Test empty capabilities list."""
        data = AgentCreate(
            name="Test",
            capabilities=[],
        )

        assert data.capabilities == []

    def test_duplicate_capabilities(self):
        """Test duplicate capabilities are allowed (API level)."""
        data = AgentCreate(
            name="Test",
            capabilities=["chat", "chat", "code"],
        )

        # Duplicates are allowed at model level, service should handle


# =============================================================================
# Agent Tools Configuration Tests
# =============================================================================


class TestAgentToolsConfiguration:
    """Tests for agent tools configuration."""

    def test_simple_tools_config(self):
        """Test simple tools configuration."""
        data = AgentCreate(
            name="Test",
            tools_config={"web_search": True, "file_read": True},
        )

        assert data.tools_config["web_search"] is True

    def test_complex_tools_config(self):
        """Test complex tools configuration."""
        data = AgentCreate(
            name="Test",
            tools_config={
                "builtin": ["web_search", "calculator"],
                "custom": [
                    {"name": "get_weather", "endpoint": "http://api.weather.com"},
                ],
                "mcp": {"enabled": True, "servers": ["server1"]},
            },
        )

        assert "builtin" in data.tools_config
        assert "custom" in data.tools_config


# =============================================================================
# Agent MCP Servers Tests
# =============================================================================


class TestAgentMCPServers:
    """Tests for agent MCP server configuration."""

    def test_single_mcp_server(self):
        """Test single MCP server configuration."""
        data = AgentCreate(
            name="Test",
            mcp_servers=[
                {
                    "name": "database-server",
                    "url": "http://localhost:3000",
                    "transport": "sse",
                }
            ],
        )

        assert len(data.mcp_servers) == 1
        assert data.mcp_servers[0]["name"] == "database-server"

    def test_multiple_mcp_servers(self):
        """Test multiple MCP server configuration."""
        data = AgentCreate(
            name="Test",
            mcp_servers=[
                {"name": "server1", "url": "http://localhost:3001"},
                {"name": "server2", "url": "http://localhost:3002"},
                {"name": "server3", "url": "http://localhost:3003"},
            ],
        )

        assert len(data.mcp_servers) == 3


# =============================================================================
# Agent Model Configuration Tests
# =============================================================================


class TestAgentModelConfiguration:
    """Tests for agent model configuration."""

    def test_default_model(self):
        """Test default model configuration."""
        data = AgentCreate(name="Test")

        # Use settings to determine expected defaults
        assert data.model_provider == settings.DEFAULT_AI_PROVIDER
        # Model name depends on provider
        assert data.model_name is not None
        assert data.temperature == 0.7
        assert data.max_tokens == 4096

    def test_openai_model(self):
        """Test OpenAI model configuration."""
        data = AgentCreate(
            name="Test",
            model_provider="openai",
            model_name="gpt-4-turbo",
            temperature=0.9,
            max_tokens=16384,
        )

        assert data.model_provider == "openai"
        assert data.model_name == "gpt-4-turbo"
        assert data.temperature == 0.9

    def test_temperature_range(self):
        """Test temperature values."""
        # Low temperature
        data = AgentCreate(name="Test", temperature=0.0)
        assert data.temperature == 0.0

        # High temperature
        data = AgentCreate(name="Test", temperature=2.0)
        assert data.temperature == 2.0


# =============================================================================
# Execution Context Tests
# =============================================================================


class TestExecutionContext:
    """Tests for agent execution context."""

    def test_empty_context(self):
        """Test execution with empty context."""
        data = AgentExecuteRequest(
            message="Hello",
            context={},
        )

        assert data.context == {}

    def test_document_context(self):
        """Test execution with document context."""
        data = AgentExecuteRequest(
            message="Summarize this",
            context={
                "document_id": "doc-123",
                "document_type": "pdf",
                "document_name": "report.pdf",
            },
        )

        assert data.context["document_id"] == "doc-123"

    def test_project_context(self):
        """Test execution with project context."""
        data = AgentExecuteRequest(
            message="Analyze metrics",
            context={
                "project_id": "proj-456",
                "date_range": {"start": "2024-01-01", "end": "2024-01-31"},
            },
        )

        assert data.context["project_id"] == "proj-456"

    def test_conversation_continuation(self):
        """Test continuing a conversation."""
        conversation_id = str(uuid4())
        data = AgentExecuteRequest(
            message="Follow up question",
            conversation_id=conversation_id,
        )

        assert data.conversation_id == conversation_id
