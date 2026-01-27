"""
Unit tests for chat service tool call argument parsing.

Tests the _parse_and_execute_tool_calls method to ensure it correctly parses:
- String arguments: key='value' or key="value"
- Integer arguments: key=123
- Float arguments: key=3.14
- Boolean arguments: key=True, key=False
- Mixed arguments: combinations of the above
"""

import pytest
import re
import ast
from typing import Any


def parse_tool_call_arguments(args_str: str) -> dict[str, Any]:
    """
    Parse tool call arguments from a string.

    This is a standalone version of the parsing logic from ChatService._parse_and_execute_tool_calls
    for isolated unit testing.
    """
    arguments = {}

    # Handle empty arguments case
    args_str_stripped = args_str.strip()
    if not args_str_stripped:
        return arguments

    # Try ast.literal_eval first (works for dict-like syntax)
    dict_str = "{" + args_str + "}"
    try:
        arguments = ast.literal_eval(dict_str)
        return arguments
    except (ValueError, SyntaxError):
        pass

    # Fallback: Parse different argument types

    # String values: key='value' or key="value"
    for arg in re.findall(r"(\w+)\s*=\s*['\"]([^'\"]*)['\"]", args_str):
        key, value = arg
        arguments[key] = value

    # Integer/numeric values: key=123 or key=3.14
    for arg in re.findall(r"(\w+)\s*=\s*(\d+(?:\.\d+)?)", args_str):
        key, value = arg
        # Don't overwrite if already parsed as string
        if key not in arguments:
            try:
                if '.' in value:
                    arguments[key] = float(value)
                else:
                    arguments[key] = int(value)
            except ValueError:
                arguments[key] = value

    # Boolean values: key=True, key=False
    for arg in re.findall(r"(\w+)\s*=\s*(True|False)", args_str):
        key, value = arg
        if key not in arguments:
            arguments[key] = value == "True"

    return arguments


class TestToolCallArgumentParsing:
    """Test parsing of tool call arguments."""

    def test_parse_empty_arguments(self):
        """Test parsing empty argument string."""
        result = parse_tool_call_arguments("")
        assert result == {}

    def test_parse_whitespace_only(self):
        """Test parsing whitespace-only argument string."""
        result = parse_tool_call_arguments("   ")
        assert result == {}

    # Integer argument tests
    def test_parse_single_integer_argument(self):
        """Test parsing a single integer argument."""
        result = parse_tool_call_arguments("pipeline_id=5")
        assert result == {"pipeline_id": 5}
        assert isinstance(result["pipeline_id"], int)

    def test_parse_large_integer(self):
        """Test parsing a large integer argument."""
        result = parse_tool_call_arguments("count=1000000")
        assert result == {"count": 1000000}
        assert isinstance(result["count"], int)

    def test_parse_zero_integer(self):
        """Test parsing zero as integer."""
        result = parse_tool_call_arguments("offset=0")
        assert result == {"offset": 0}
        assert isinstance(result["offset"], int)

    # Float argument tests
    def test_parse_float_argument(self):
        """Test parsing a float argument."""
        result = parse_tool_call_arguments("temperature=0.7")
        assert result == {"temperature": 0.7}
        assert isinstance(result["temperature"], float)

    def test_parse_float_with_integer_part(self):
        """Test parsing a float with integer part."""
        result = parse_tool_call_arguments("score=3.14159")
        assert result == {"score": 3.14159}
        assert isinstance(result["score"], float)

    # String argument tests
    def test_parse_single_quoted_string(self):
        """Test parsing a single-quoted string argument."""
        result = parse_tool_call_arguments("name='my-project'")
        assert result == {"name": "my-project"}
        assert isinstance(result["name"], str)

    def test_parse_double_quoted_string(self):
        """Test parsing a double-quoted string argument."""
        result = parse_tool_call_arguments('name="my-project"')
        assert result == {"name": "my-project"}
        assert isinstance(result["name"], str)

    def test_parse_string_with_spaces(self):
        """Test parsing a string argument with spaces."""
        result = parse_tool_call_arguments("title='My Project Name'")
        assert result == {"title": "My Project Name"}

    def test_parse_empty_string(self):
        """Test parsing an empty string argument."""
        result = parse_tool_call_arguments("description=''")
        assert result == {"description": ""}

    # Boolean argument tests
    def test_parse_true_boolean(self):
        """Test parsing True boolean argument."""
        result = parse_tool_call_arguments("enabled=True")
        assert result == {"enabled": True}
        assert isinstance(result["enabled"], bool)

    def test_parse_false_boolean(self):
        """Test parsing False boolean argument."""
        result = parse_tool_call_arguments("enabled=False")
        assert result == {"enabled": False}
        assert isinstance(result["enabled"], bool)

    # Mixed argument tests
    def test_parse_string_and_integer(self):
        """Test parsing mixed string and integer arguments."""
        result = parse_tool_call_arguments("name='bmv', pipeline_id=5")
        assert result == {"name": "bmv", "pipeline_id": 5}
        assert isinstance(result["name"], str)
        assert isinstance(result["pipeline_id"], int)

    def test_parse_multiple_integers(self):
        """Test parsing multiple integer arguments."""
        result = parse_tool_call_arguments("page=1, limit=10, offset=0")
        assert result == {"page": 1, "limit": 10, "offset": 0}

    def test_parse_all_types_mixed(self):
        """Test parsing all argument types together."""
        result = parse_tool_call_arguments(
            "name='test', count=42, rate=0.95, active=True"
        )
        assert result == {
            "name": "test",
            "count": 42,
            "rate": 0.95,
            "active": True,
        }

    def test_parse_with_extra_spaces(self):
        """Test parsing arguments with extra spaces."""
        result = parse_tool_call_arguments("name = 'test' , count = 5")
        assert result["name"] == "test"
        assert result["count"] == 5

    # Edge cases
    def test_parse_string_containing_number(self):
        """Test that strings containing numbers stay as strings."""
        result = parse_tool_call_arguments("version='1.0.0'")
        assert result == {"version": "1.0.0"}
        assert isinstance(result["version"], str)

    def test_parse_url_string(self):
        """Test parsing a URL string argument."""
        result = parse_tool_call_arguments("repo='https://github.com/org/repo'")
        assert result == {"repo": "https://github.com/org/repo"}

    def test_parse_path_string(self):
        """Test parsing a path string argument."""
        result = parse_tool_call_arguments("path='/api/v1/devlake/pipelines'")
        assert result == {"path": "/api/v1/devlake/pipelines"}


class TestToolCallPatternMatching:
    """Test the regex patterns used for tool call detection."""

    def test_explicit_pattern_with_integer(self):
        """Test TOOL_CALL pattern with integer argument."""
        content = "TOOL_CALL: devlake_get_pipeline(pipeline_id=5)"
        explicit_pattern = r"TOOL_CALL:\s*(\w+)\(([^)]*)\)"
        match = re.search(explicit_pattern, content)

        assert match is not None
        assert match.group(1) == "devlake_get_pipeline"
        assert match.group(2) == "pipeline_id=5"

    def test_explicit_pattern_with_string(self):
        """Test TOOL_CALL pattern with string argument."""
        content = "TOOL_CALL: devlake_get_dora_metrics(project_name='bmv')"
        explicit_pattern = r"TOOL_CALL:\s*(\w+)\(([^)]*)\)"
        match = re.search(explicit_pattern, content)

        assert match is not None
        assert match.group(1) == "devlake_get_dora_metrics"
        assert match.group(2) == "project_name='bmv'"

    def test_explicit_pattern_no_arguments(self):
        """Test TOOL_CALL pattern with no arguments."""
        content = "TOOL_CALL: devlake_health_check()"
        explicit_pattern = r"TOOL_CALL:\s*(\w+)\(([^)]*)\)"
        match = re.search(explicit_pattern, content)

        assert match is not None
        assert match.group(1) == "devlake_health_check"
        assert match.group(2) == ""

    def test_explicit_pattern_multiple_arguments(self):
        """Test TOOL_CALL pattern with multiple arguments."""
        content = "TOOL_CALL: create_project(name='test', description='A test project', active=True)"
        explicit_pattern = r"TOOL_CALL:\s*(\w+)\(([^)]*)\)"
        match = re.search(explicit_pattern, content)

        assert match is not None
        assert match.group(1) == "create_project"
        args_str = match.group(2)
        assert "name='test'" in args_str
        assert "description='A test project'" in args_str
        assert "active=True" in args_str


class TestRealWorldToolCalls:
    """Test real-world tool call scenarios."""

    def test_devlake_get_pipeline(self):
        """Test the actual failing case: devlake_get_pipeline(pipeline_id=5)."""
        args_str = "pipeline_id=5"
        result = parse_tool_call_arguments(args_str)

        assert "pipeline_id" in result
        assert result["pipeline_id"] == 5
        assert isinstance(result["pipeline_id"], int)

    def test_devlake_setup_github(self):
        """Test devlake_setup_github with mixed arguments."""
        args_str = "token='ghp_xxx', repo='org/repo', project_name='my-project'"
        result = parse_tool_call_arguments(args_str)

        assert result == {
            "token": "ghp_xxx",
            "repo": "org/repo",
            "project_name": "my-project",
        }

    def test_devlake_create_connection(self):
        """Test devlake_create_connection arguments."""
        args_str = "plugin='github', name='my-conn', token='ghp_123'"
        result = parse_tool_call_arguments(args_str)

        assert result == {
            "plugin": "github",
            "name": "my-conn",
            "token": "ghp_123",
        }

    def test_pagination_arguments(self):
        """Test common pagination arguments."""
        args_str = "page=1, limit=20, offset=0"
        result = parse_tool_call_arguments(args_str)

        assert result == {"page": 1, "limit": 20, "offset": 0}
        assert all(isinstance(v, int) for v in result.values())

    def test_llm_parameters(self):
        """Test LLM parameter arguments."""
        args_str = "temperature=0.7, max_tokens=4096, top_p=0.9"
        result = parse_tool_call_arguments(args_str)

        assert result["temperature"] == 0.7
        assert result["max_tokens"] == 4096
        assert result["top_p"] == 0.9


class TestAstLiteralEvalFallback:
    """Test cases where ast.literal_eval works directly."""

    def test_dict_style_string_args(self):
        """Test dict-style arguments that ast.literal_eval can handle."""
        # This format works with ast.literal_eval: {'key': 'value'}
        args_str = "'name': 'test', 'count': 42"
        result = parse_tool_call_arguments(args_str)

        assert result["name"] == "test"
        assert result["count"] == 42

    def test_python_dict_format(self):
        """Test pure Python dict format."""
        args_str = "'key': 'value'"
        result = parse_tool_call_arguments(args_str)
        assert result == {"key": "value"}
