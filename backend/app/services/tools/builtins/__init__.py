"""
Built-in Tools

Core platform tools available to all LLM agents.
"""

from .code_search import CodeSearchTool
from .diff_viewer import DiffViewerTool
from .file_reader import FileReaderTool
from .static_analysis import StaticAnalysisTool
from .ci_logs import CILogsTool
from .create_pr import CreatePRTool
from .jira_tools import (
    JiraSearchTool,
    JiraCreateTicketTool,
    JiraUpdateTicketTool,
)

# Register all built-in tools
from ..registry import tool_registry

BUILTIN_TOOLS = [
    CodeSearchTool,
    DiffViewerTool,
    FileReaderTool,
    StaticAnalysisTool,
    CILogsTool,
    CreatePRTool,
    JiraSearchTool,
    JiraCreateTicketTool,
    JiraUpdateTicketTool,
]


def register_builtin_tools():
    """Register all built-in tools with the registry."""
    for tool_class in BUILTIN_TOOLS:
        tool_registry.register(tool_class)


__all__ = [
    "CodeSearchTool",
    "DiffViewerTool",
    "FileReaderTool",
    "StaticAnalysisTool",
    "CILogsTool",
    "CreatePRTool",
    "JiraSearchTool",
    "JiraCreateTicketTool",
    "JiraUpdateTicketTool",
    "register_builtin_tools",
]
