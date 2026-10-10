"""
Integration tests for DevLake tools execution via WebSocket chat.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch


class TestDevLakeToolsIntegration:
    """Integration tests for DevLake tool execution."""

    @pytest.mark.asyncio
    async def test_health_check_direct_execution(self):
        """Test direct execution of DevLake health check handler."""
        from app.services.mcp.devlake_tools import DevLakeHealthCheckHandler

        handler = DevLakeHealthCheckHandler()

        with patch("app.services.mcp.devlake_tools.devlake_service") as mock_service:
            mock_service.health_check = AsyncMock(return_value=True)
            mock_service.base_url = "http://localhost:8080/api"
            mock_service.root_url = "http://localhost:8080"

            result = await handler.execute({}, {})

            assert result["success"] is True
            assert result["healthy"] is True
            assert "base_url" in result
            mock_service.health_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_when_service_down(self):
        """Test health check when DevLake is not running."""
        from app.services.mcp.devlake_tools import DevLakeHealthCheckHandler

        handler = DevLakeHealthCheckHandler()

        with patch("app.services.mcp.devlake_tools.devlake_service") as mock_service:
            mock_service.health_check = AsyncMock(return_value=False)
            mock_service.base_url = "http://localhost:8080/api"
            mock_service.root_url = "http://localhost:8080"

            result = await handler.execute({}, {})

            # Should indicate unhealthy
            assert result.get("success") is False or result.get("healthy") is False

    @pytest.mark.asyncio
    async def test_create_project_success(self):
        """Test successful project creation."""
        from app.services.mcp.devlake_tools import DevLakeCreateProjectHandler

        handler = DevLakeCreateProjectHandler()

        with patch("app.services.mcp.devlake_tools.devlake_service") as mock_service:
            mock_service.create_project = AsyncMock(return_value={
                "name": "test-project",
                "description": "Test project",
            })
            mock_service.base_url = "http://localhost:8080/api"

            result = await handler.execute({"name": "test-project"}, {})

            assert result["success"] is True
            assert "test-project" in result["message"]
            mock_service.create_project.assert_called_once_with("test-project", None)

    @pytest.mark.asyncio
    async def test_create_project_with_connection_error(self):
        """Test project creation when DevLake is unreachable."""
        import httpx
        from app.services.mcp.devlake_tools import DevLakeCreateProjectHandler

        handler = DevLakeCreateProjectHandler()

        with patch("app.services.mcp.devlake_tools.devlake_service") as mock_service:
            mock_service.create_project = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )
            mock_service.base_url = "http://localhost:8080/api"

            result = await handler.execute({"name": "test-project"}, {})

            # Should return structured error
            assert result.get("success") is False
            assert "error" in result

    @pytest.mark.asyncio
    async def test_create_connection_success(self):
        """Test successful connection creation."""
        from app.services.mcp.devlake_tools import DevLakeCreateConnectionHandler

        handler = DevLakeCreateConnectionHandler()

        with patch("app.services.mcp.devlake_tools.devlake_service") as mock_service:
            mock_service.create_connection = AsyncMock(return_value={
                "id": 1,
                "name": "my-github",
                "plugin": "github",
            })
            mock_service.base_url = "http://localhost:8080/api"

            result = await handler.execute({
                "plugin": "github",
                "name": "my-github",
                "token": "ghp_test123",
            }, {})

            assert result["success"] is True
            mock_service.create_connection.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_connection_missing_token(self):
        """Test connection creation without token."""
        from app.services.mcp.devlake_tools import DevLakeCreateConnectionHandler

        handler = DevLakeCreateConnectionHandler()

        result = await handler.execute({
            "plugin": "github",
            "name": "my-github",
            # No token provided
        }, {})

        # Should indicate token is required
        assert result.get("success") is False
        assert "token" in str(result).lower()

    @pytest.mark.asyncio
    async def test_quick_start_when_healthy(self):
        """Test quick start tool when DevLake is healthy."""
        from app.services.mcp.devlake_tools import DevLakeQuickStartHandler

        handler = DevLakeQuickStartHandler()

        with patch("app.services.mcp.devlake_tools.devlake_service") as mock_service:
            mock_service.health_check = AsyncMock(return_value=True)
            mock_service.list_connections = AsyncMock(return_value=[])
            mock_service.list_projects = AsyncMock(return_value=[])
            mock_service.base_url = "http://localhost:8080/api"
            mock_service.root_url = "http://localhost:8080"

            result = await handler.execute({}, {})

            assert result["success"] is True
            assert result["devlake_status"] == "running"
            # Should suggest creating a connection since none exist
            assert len(result["what_you_need"]) > 0

    @pytest.mark.asyncio
    async def test_quick_start_when_unreachable(self):
        """Test quick start tool when DevLake is unreachable."""
        from app.services.mcp.devlake_tools import DevLakeQuickStartHandler

        handler = DevLakeQuickStartHandler()

        with patch("app.services.mcp.devlake_tools.devlake_service") as mock_service:
            mock_service.health_check = AsyncMock(side_effect=Exception("Connection refused"))
            mock_service.base_url = "http://localhost:8080/api"

            result = await handler.execute({}, {})

            assert result["success"] is False
            assert "unreachable" in result.get("devlake_status", "")


class TestMCPToolExecution:
    """Test MCP tool execution flow."""

    @pytest.mark.asyncio
    async def test_execute_mcp_tool_builtin(self):
        """Test executing a built-in tool through ChatService."""
        from app.services.chat import ChatService
        from sqlalchemy.ext.asyncio import AsyncSession

        mock_db = MagicMock(spec=AsyncSession)
        service = ChatService(mock_db)

        # Initialize built-in tools
        with patch("app.services.mcp.devlake_tools.devlake_service") as mock_devlake:
            mock_devlake.health_check = AsyncMock(return_value=True)
            mock_devlake.base_url = "http://localhost:8080/api"
            mock_devlake.root_url = "http://localhost:8080"

            await service.initialize_mcp()

            # Execute the health check tool
            result = await service._execute_mcp_tool("devlake_health_check", {})

            # Parse result
            result_data = json.loads(result)
            assert result_data["success"] is True
            assert result_data["healthy"] is True

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self):
        """Test executing an unknown tool returns error."""
        from app.services.chat import ChatService
        from sqlalchemy.ext.asyncio import AsyncSession

        mock_db = MagicMock(spec=AsyncSession)
        service = ChatService(mock_db)

        await service.initialize_mcp()

        # Try to execute unknown tool
        result = await service._execute_mcp_tool("unknown_tool_xyz", {})

        # Should return error
        result_data = json.loads(result)
        assert "error" in result_data or result_data.get("success") is False


class TestChatServiceWithTools:
    """Test ChatService tool integration."""

    @pytest.mark.asyncio
    async def test_chat_stream_parses_tool_calls(self):
        """Test that chat stream properly parses and executes tool calls."""
        from app.services.chat import ChatService
        from app.models.conversation import Conversation, ModelProvider
        from sqlalchemy.ext.asyncio import AsyncSession
        from unittest.mock import PropertyMock

        mock_db = MagicMock(spec=AsyncSession)
        service = ChatService(mock_db)

        # Mock conversation
        mock_conversation = MagicMock(spec=Conversation)
        mock_conversation.id = "test-conv-id"
        mock_conversation.model_provider = ModelProvider.GOOGLE.value
        mock_conversation.model_name = "gemini-2.5-flash"
        mock_conversation.system_prompt = None

        with patch("app.services.mcp.devlake_tools.devlake_service") as mock_devlake:
            mock_devlake.health_check = AsyncMock(return_value=True)
            mock_devlake.base_url = "http://localhost:8080/api"
            mock_devlake.root_url = "http://localhost:8080"

            await service.initialize_mcp()

            # Simulate parsing tool calls from content
            content = "Let me check the health: devlake_health_check()"
            results = await service._parse_and_execute_tool_calls(content)

            assert len(results) == 1
            tool_name, tool_result = results[0]
            assert tool_name == "devlake_health_check"

            result_data = json.loads(tool_result)
            assert result_data["success"] is True


class TestErrorRecovery:
    """Test error recovery functionality."""

    @pytest.mark.asyncio
    async def test_error_handler_plans_health_check(self):
        """Test that error handler plans health check for service unavailable errors."""
        from app.services.mcp.error_handler import (
            MCPErrorHandler,
            ErrorContext,
            ErrorCategory,
            RecoveryAction,
        )

        # Create handler with mock tools
        mock_tool = MagicMock()
        mock_tool.input_schema = {"type": "object", "properties": {}, "required": []}

        handler = MCPErrorHandler(
            available_tools={"devlake_health_check": ("builtin", mock_tool)},
            auto_execute_recovery=True,
        )

        # Create error context for service unavailable
        context = ErrorContext(
            tool_name="devlake_create_project",
            error_category=ErrorCategory.SERVICE_UNAVAILABLE,
            error_message="Connection refused",
        )

        # Get recovery plan
        plan = handler.analyze_error(context)

        assert plan.action == RecoveryAction.HEALTH_CHECK
        assert plan.tool_to_run == "devlake_health_check"
        assert plan.auto_execute is True

    @pytest.mark.asyncio
    async def test_error_handler_plans_list_for_not_found(self):
        """Test that error handler plans list resources for not found errors."""
        from app.services.mcp.error_handler import (
            MCPErrorHandler,
            ErrorContext,
            ErrorCategory,
            RecoveryAction,
        )

        mock_tool = MagicMock()
        mock_tool.input_schema = {"type": "object", "properties": {}, "required": []}

        handler = MCPErrorHandler(
            available_tools={"devlake_list_projects": ("builtin", mock_tool)},
            auto_execute_recovery=True,
        )

        context = ErrorContext(
            tool_name="devlake_get_project",
            error_category=ErrorCategory.NOT_FOUND,
            error_message="Project 'xyz' not found",
        )

        plan = handler.analyze_error(context)

        assert plan.action == RecoveryAction.LIST_RESOURCES
        assert plan.tool_to_run == "devlake_list_projects"
