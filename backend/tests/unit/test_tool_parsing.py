"""
Unit tests for tool call parsing and execution in chat service.
"""

import pytest
import json
import re
from unittest.mock import AsyncMock, MagicMock, patch


class TestToolCallParsing:
    """Test tool call parsing from LLM output text."""

    def test_regex_pattern_matches_empty_args(self):
        """Test that regex pattern matches tool calls with empty arguments."""
        # This is the pattern from chat.py after our fix
        implicit_pattern = r"(\w+)\(([^)]*)\)"

        # Test cases
        test_cases = [
            ("devlake_health_check()", "devlake_health_check", ""),
            ("devlake_list_projects()", "devlake_list_projects", ""),
            ("test_tool(arg='value')", "test_tool", "arg='value'"),
            ("multi_args(a='1', b='2')", "multi_args", "a='1', b='2'"),
        ]

        for content, expected_name, expected_args in test_cases:
            match = re.search(implicit_pattern, content)
            assert match is not None, f"Pattern should match: {content}"
            assert match.group(1) == expected_name, f"Tool name should be {expected_name}"
            assert match.group(2) == expected_args, f"Args should be '{expected_args}'"

    def test_regex_pattern_matches_tool_in_sentence(self):
        """Test that regex finds tool calls embedded in text."""
        implicit_pattern = r"(\w+)\(([^)]*)\)"

        content = "I'll run the health check: devlake_health_check() to verify the service."
        matches = list(re.finditer(implicit_pattern, content))

        # Should find devlake_health_check
        tool_names = [m.group(1) for m in matches]
        assert "devlake_health_check" in tool_names

    def test_regex_pattern_finds_multiple_tools(self):
        """Test that regex finds multiple tool calls in content."""
        implicit_pattern = r"(\w+)\(([^)]*)\)"

        content = """
        First, I'll check the health: devlake_health_check()
        Then list projects: devlake_list_projects()
        Finally create one: devlake_create_project(name='test')
        """

        matches = list(re.finditer(implicit_pattern, content))
        tool_names = [m.group(1) for m in matches]

        assert "devlake_health_check" in tool_names
        assert "devlake_list_projects" in tool_names
        assert "devlake_create_project" in tool_names

    def test_explicit_tool_call_pattern(self):
        """Test explicit TOOL_CALL: prefix pattern."""
        explicit_pattern = r"TOOL_CALL:\s*(\w+)\(([^)]*)\)"

        test_cases = [
            ("TOOL_CALL: devlake_health_check()", "devlake_health_check", ""),
            ("TOOL_CALL: create_project(name='test')", "create_project", "name='test'"),
            ("TOOL_CALL:no_space()", "no_space", ""),
        ]

        for content, expected_name, expected_args in test_cases:
            match = re.search(explicit_pattern, content)
            assert match is not None, f"Pattern should match: {content}"
            assert match.group(1) == expected_name
            assert match.group(2) == expected_args


class TestArgumentParsing:
    """Test parsing of tool arguments."""

    def test_parse_empty_arguments(self):
        """Test parsing empty argument string."""
        import ast

        args_str = ""
        args_str_stripped = args_str.strip()

        # Empty args should result in empty dict
        arguments = {}
        if args_str_stripped:
            dict_str = "{" + args_str + "}"
            arguments = ast.literal_eval(dict_str)

        assert arguments == {}

    def test_parse_single_argument(self):
        """Test parsing single keyword argument using regex fallback."""
        # ast.literal_eval fails on {name='test'} so regex fallback is used
        args_str = "name='test'"

        # This is how the ChatService actually parses it
        arguments = {}
        for arg in re.findall(r"(\w+)\s*=\s*['\"]([^'\"]*)['\"]", args_str):
            key, value = arg
            arguments[key] = value

        assert arguments == {"name": "test"}

    def test_parse_multiple_arguments(self):
        """Test parsing multiple keyword arguments using regex fallback."""
        args_str = "plugin='github', name='my-connection', token='abc123'"

        arguments = {}
        for arg in re.findall(r"(\w+)\s*=\s*['\"]([^'\"]*)['\"]", args_str):
            key, value = arg
            arguments[key] = value

        assert arguments == {
            "plugin": "github",
            "name": "my-connection",
            "token": "abc123",
        }

    def test_parse_double_quoted_arguments(self):
        """Test parsing arguments with double quotes using regex."""
        args_str = 'name="test", value="hello"'

        arguments = {}
        for arg in re.findall(r"(\w+)\s*=\s*['\"]([^'\"]*)['\"]", args_str):
            key, value = arg
            arguments[key] = value

        assert arguments == {"name": "test", "value": "hello"}

    def test_parse_numeric_arguments(self):
        """Test parsing numeric arguments - note: regex only captures string values."""
        # The regex fallback only captures quoted string values
        # Numeric values without quotes aren't captured by the current regex
        args_str = "count='10', ratio='0.5'"

        arguments = {}
        for arg in re.findall(r"(\w+)\s*=\s*['\"]([^'\"]*)['\"]", args_str):
            key, value = arg
            arguments[key] = value

        # Values are strings, not numbers (regex limitation)
        assert arguments == {"count": "10", "ratio": "0.5"}

    def test_fallback_regex_parsing(self):
        """Test fallback regex parsing when ast.literal_eval fails."""
        # Simulate the fallback parsing
        args_str = "key=value_without_quotes"

        # This would fail ast.literal_eval, so use regex fallback
        arguments = {}
        for arg in re.findall(r"(\w+)\s*=\s*['\"]([^'\"]*)['\"]", args_str):
            key, value = arg
            arguments[key] = value

        # The fallback only works for quoted values, so this returns empty
        assert arguments == {}

        # But with quotes it works
        args_str = "key='value'"
        for arg in re.findall(r"(\w+)\s*=\s*['\"]([^'\"]*)['\"]", args_str):
            key, value = arg
            arguments[key] = value

        assert arguments == {"key": "value"}


class TestChatServiceToolParsing:
    """Integration tests for ChatService tool parsing."""

    @pytest.mark.asyncio
    async def test_parse_and_execute_health_check(self):
        """Test parsing and executing health check with empty args."""
        from app.services.chat import ChatService
        from sqlalchemy.ext.asyncio import AsyncSession

        # Mock the database session
        mock_db = MagicMock(spec=AsyncSession)

        # Create service with mocked tools
        service = ChatService(mock_db)

        # Add a mock health check tool
        mock_tool = MagicMock()
        mock_tool.input_schema = {"type": "object", "properties": {}, "required": []}
        service._mcp_tools["devlake_health_check"] = ("builtin", mock_tool)

        # Mock the tool executor
        service._execute_mcp_tool = AsyncMock(return_value='{"success": true, "healthy": true}')

        # Test content with empty-arg tool call
        content = "I'll check the health: devlake_health_check()"

        # Parse and execute
        results = await service._parse_and_execute_tool_calls(content)

        # Should have found and executed the tool
        assert len(results) == 1
        assert results[0][0] == "devlake_health_check"

        # Verify executor was called with empty dict
        service._execute_mcp_tool.assert_called_once_with("devlake_health_check", {})

    @pytest.mark.asyncio
    async def test_parse_and_execute_with_arguments(self):
        """Test parsing and executing tool with arguments."""
        from app.services.chat import ChatService
        from sqlalchemy.ext.asyncio import AsyncSession

        mock_db = MagicMock(spec=AsyncSession)
        service = ChatService(mock_db)

        # Add mock tool
        mock_tool = MagicMock()
        mock_tool.input_schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }
        service._mcp_tools["devlake_create_project"] = ("builtin", mock_tool)

        # Mock executor
        service._execute_mcp_tool = AsyncMock(return_value='{"success": true}')

        content = "Creating project: devlake_create_project(name='test-project')"
        results = await service._parse_and_execute_tool_calls(content)

        assert len(results) == 1
        assert results[0][0] == "devlake_create_project"

        # Verify arguments were parsed correctly
        service._execute_mcp_tool.assert_called_once_with(
            "devlake_create_project",
            {"name": "test-project"}
        )

    @pytest.mark.asyncio
    async def test_ignores_unknown_tools(self):
        """Test that unknown tool names are ignored."""
        from app.services.chat import ChatService
        from sqlalchemy.ext.asyncio import AsyncSession

        mock_db = MagicMock(spec=AsyncSession)
        service = ChatService(mock_db)

        # No tools registered
        service._mcp_tools = {}

        content = "Let me call unknown_tool() and another_unknown(arg='val')"
        results = await service._parse_and_execute_tool_calls(content)

        # Should return empty - no known tools
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_handles_common_function_names(self):
        """Test that common programming function calls are not mistaken for tools."""
        from app.services.chat import ChatService
        from sqlalchemy.ext.asyncio import AsyncSession

        mock_db = MagicMock(spec=AsyncSession)
        service = ChatService(mock_db)

        # Register only our actual tool
        mock_tool = MagicMock()
        mock_tool.input_schema = {"type": "object", "properties": {}, "required": []}
        service._mcp_tools["devlake_health_check"] = ("builtin", mock_tool)
        service._execute_mcp_tool = AsyncMock(return_value='{"success": true}')

        # Content with common function names that should be ignored
        content = """
        Here's how you can use it:
        ```python
        print("Hello")
        result = calculate(x, y)
        data = fetch_data()
        ```

        Now let me check health: devlake_health_check()
        """

        results = await service._parse_and_execute_tool_calls(content)

        # Should only execute the registered tool
        assert len(results) == 1
        assert results[0][0] == "devlake_health_check"


class TestDevLakeToolExecution:
    """Test DevLake tool execution specifically."""

    @pytest.mark.asyncio
    async def test_health_check_tool_handler(self):
        """Test DevLake health check handler execution."""
        from app.services.mcp.devlake_tools import DevLakeHealthCheckHandler
        from unittest.mock import patch

        handler = DevLakeHealthCheckHandler()

        # Mock the devlake_service.health_check method
        with patch("app.services.mcp.devlake_tools.devlake_service") as mock_service:
            # Test healthy response
            mock_service.health_check = AsyncMock(return_value=True)
            mock_service.base_url = "http://localhost:8080/api"
            mock_service.root_url = "http://localhost:8080"

            result = await handler.execute({}, {})

            assert result["success"] is True
            assert result["healthy"] is True

    @pytest.mark.asyncio
    async def test_health_check_tool_handler_unhealthy(self):
        """Test DevLake health check handler when service is unhealthy."""
        from app.services.mcp.devlake_tools import DevLakeHealthCheckHandler
        from unittest.mock import patch

        handler = DevLakeHealthCheckHandler()

        with patch("app.services.mcp.devlake_tools.devlake_service") as mock_service:
            mock_service.health_check = AsyncMock(return_value=False)
            mock_service.base_url = "http://localhost:8080/api"
            mock_service.root_url = "http://localhost:8080"

            result = await handler.execute({}, {})

            # Should return error structure
            assert "error" in result or result.get("success") is False

    @pytest.mark.asyncio
    async def test_create_project_tool_handler(self):
        """Test DevLake create project handler."""
        from app.services.mcp.devlake_tools import DevLakeCreateProjectHandler
        from unittest.mock import patch

        handler = DevLakeCreateProjectHandler()

        with patch("app.services.mcp.devlake_tools.devlake_service") as mock_service:
            mock_service.create_project = AsyncMock(return_value={
                "name": "test-project",
                "description": "Test",
            })
            mock_service.base_url = "http://localhost:8080/api"

            result = await handler.execute({"name": "test-project"}, {})

            assert result["success"] is True
            assert "test-project" in result["message"]


class TestBuiltinToolRegistration:
    """Test that built-in tools are properly registered."""

    def test_devlake_tools_registered(self):
        """Test that DevLake tools are registered in MCP server."""
        from app.services.mcp import get_mcp_server

        mcp_server = get_mcp_server()

        # Check key tools are registered
        expected_tools = [
            "devlake_health_check",
            "devlake_list_projects",
            "devlake_create_project",
            "devlake_list_connections",
            "devlake_create_connection",
        ]

        for tool_name in expected_tools:
            assert tool_name in mcp_server._tools, f"Tool {tool_name} should be registered"

    def test_health_check_tool_schema(self):
        """Test that health check tool has correct schema."""
        from app.services.mcp import get_mcp_server

        mcp_server = get_mcp_server()
        handler = mcp_server._tools.get("devlake_health_check")

        assert handler is not None

        tool = handler.tool
        assert tool.name == "devlake_health_check"

        # Health check should have no required arguments
        schema = tool.input_schema
        assert schema.get("required", []) == []
