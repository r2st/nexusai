"""
MCP Server Setup and Initialization

Factory functions for creating and configuring MCP servers with all available tools.

Available MCP Tool Categories:
- DevLake: DORA metrics, connections, pipelines, blueprints, PR-Issue correlations
- Policy: RBAC, data redaction, audit logging
- CI/CD: Build logs, test results, flaky tests, failure patterns
- Repository: Code search, file access, git diffs, blame
- Jira: Ticket management, sprints, project stats
- Observability: Distributed traces, logs, metrics, alerts
- RAG: Semantic search, hybrid retrieval, context building
"""

import logging
from typing import Optional

from .server import MCPServer, MCPServerConfig
from .devlake_tools import get_all_devlake_tool_handlers
from .policy_tools import get_all_policy_tool_handlers
from .ci_tools import get_all_ci_tool_handlers
from .repo_tools import get_all_repo_tool_handlers
from .jira_tools import get_all_jira_tool_handlers
from .observability_tools import get_all_observability_tool_handlers
from .rag_tools import get_all_rag_tool_handlers

logger = logging.getLogger(__name__)


def create_nexusai_mcp_server(
    config: Optional[MCPServerConfig] = None,
    enable_devlake: bool = True,
    enable_policy: bool = True,
    enable_ci: bool = True,
    enable_repo: bool = True,
    enable_jira: bool = True,
    enable_observability: bool = True,
    enable_rag: bool = True,
) -> MCPServer:
    """
    Create a fully configured NexusAI MCP server with all tools registered.

    Args:
        config: Optional server configuration
        enable_devlake: Whether to enable DevLake tools (default: True)
        enable_policy: Whether to enable Policy/RBAC tools (default: True)
        enable_ci: Whether to enable CI/CD tools (default: True)
        enable_repo: Whether to enable Repository tools (default: True)
        enable_jira: Whether to enable Jira tools (default: True)
        enable_observability: Whether to enable Observability tools (default: True)
        enable_rag: Whether to enable RAG tools (default: True)

    Returns:
        Configured MCPServer instance
    """
    if config is None:
        config = MCPServerConfig(
            name="NexusAI",
            version="1.0.0",
            enable_tools=True,
            enable_resources=True,
            enable_prompts=True,
            enable_logging=True,
        )

    server = MCPServer(config)
    registered_counts = {}

    # Register DevLake tools
    if enable_devlake:
        devlake_handlers = get_all_devlake_tool_handlers()
        for handler in devlake_handlers:
            server.register_tool(handler)
        registered_counts["devlake"] = len(devlake_handlers)
        logger.info(f"Registered {len(devlake_handlers)} DevLake MCP tools")

    # Register Policy/RBAC tools
    if enable_policy:
        policy_handlers = get_all_policy_tool_handlers()
        for handler in policy_handlers:
            server.register_tool(handler)
        registered_counts["policy"] = len(policy_handlers)
        logger.info(f"Registered {len(policy_handlers)} Policy MCP tools")

    # Register CI/CD tools
    if enable_ci:
        ci_handlers = get_all_ci_tool_handlers()
        for handler in ci_handlers:
            server.register_tool(handler)
        registered_counts["ci"] = len(ci_handlers)
        logger.info(f"Registered {len(ci_handlers)} CI/CD MCP tools")

    # Register Repository tools
    if enable_repo:
        repo_handlers = get_all_repo_tool_handlers()
        for handler in repo_handlers:
            server.register_tool(handler)
        registered_counts["repo"] = len(repo_handlers)
        logger.info(f"Registered {len(repo_handlers)} Repository MCP tools")

    # Register Jira tools
    if enable_jira:
        jira_handlers = get_all_jira_tool_handlers()
        for handler in jira_handlers:
            server.register_tool(handler)
        registered_counts["jira"] = len(jira_handlers)
        logger.info(f"Registered {len(jira_handlers)} Jira MCP tools")

    # Register Observability tools
    if enable_observability:
        obs_handlers = get_all_observability_tool_handlers()
        for handler in obs_handlers:
            server.register_tool(handler)
        registered_counts["observability"] = len(obs_handlers)
        logger.info(f"Registered {len(obs_handlers)} Observability MCP tools")

    # Register RAG tools
    if enable_rag:
        rag_handlers = get_all_rag_tool_handlers()
        for handler in rag_handlers:
            server.register_tool(handler)
        registered_counts["rag"] = len(rag_handlers)
        logger.info(f"Registered {len(rag_handlers)} RAG MCP tools")

    # Log summary
    tool_count = len(server._tools)
    logger.info(
        f"NexusAI MCP server initialized with {tool_count} tools",
        extra={
            "server_name": config.name,
            "server_version": config.version,
            "tool_count": tool_count,
            "tool_breakdown": registered_counts,
        },
    )

    return server


def list_available_tools() -> dict:
    """
    List all available MCP tools and their descriptions.

    Returns:
        Dictionary mapping tool names to their descriptions and input schemas
    """
    server = create_nexusai_mcp_server()

    tools = {}
    for name, handler in server._tools.items():
        tool = handler.tool
        tools[name] = {
            "description": tool.description,
            "input_schema": tool.input_schema,
        }

    return tools


def get_devlake_tools_summary() -> dict:
    """
    Get a summary of all DevLake MCP tools organized by category.

    Returns:
        Dictionary with tool categories and their tools
    """
    handlers = get_all_devlake_tool_handlers()

    categories = {
        "health": [],
        "projects": [],
        "connections": [],
        "plugins": [],
        "blueprints": [],
        "pipelines": [],
        "metrics": [],
        "statistics": [],
        "correlations": [],
    }

    for handler in handlers:
        tool = handler.tool
        tool_info = {
            "name": tool.name,
            "description": tool.description,
        }

        # Categorize based on name prefix
        name = tool.name
        if "health" in name:
            categories["health"].append(tool_info)
        elif "project" in name and "stats" not in name and "contributors" not in name:
            categories["projects"].append(tool_info)
        elif "connection" in name:
            categories["connections"].append(tool_info)
        elif "plugin" in name:
            categories["plugins"].append(tool_info)
        elif "blueprint" in name:
            categories["blueprints"].append(tool_info)
        elif "pipeline" in name:
            categories["pipelines"].append(tool_info)
        elif "dora" in name or "metrics" in name:
            categories["metrics"].append(tool_info)
        elif "stats" in name or "contributors" in name:
            categories["statistics"].append(tool_info)
        elif "correlation" in name or "pr_issue" in name:
            categories["correlations"].append(tool_info)

    # Remove empty categories
    categories = {k: v for k, v in categories.items() if v}

    return {
        "total_tools": len(handlers),
        "categories": categories,
    }


def get_all_tools_summary() -> dict:
    """
    Get a summary of ALL available MCP tools organized by service.

    Returns:
        Dictionary with service categories and their tools
    """
    all_handlers = {
        "devlake": get_all_devlake_tool_handlers(),
        "policy": get_all_policy_tool_handlers(),
        "ci": get_all_ci_tool_handlers(),
        "repo": get_all_repo_tool_handlers(),
        "jira": get_all_jira_tool_handlers(),
        "observability": get_all_observability_tool_handlers(),
        "rag": get_all_rag_tool_handlers(),
    }

    services = {}
    total_tools = 0

    for service_name, handlers in all_handlers.items():
        tools = []
        for handler in handlers:
            tool = handler.tool
            tools.append({
                "name": tool.name,
                "description": tool.description,
            })
        services[service_name] = {
            "tool_count": len(tools),
            "tools": tools,
        }
        total_tools += len(tools)

    return {
        "total_tools": total_tools,
        "services": services,
        "service_descriptions": {
            "devlake": "DORA metrics, pipelines, connections, blueprints, PR-Issue correlations",
            "policy": "RBAC, data redaction, audit logging",
            "ci": "Build logs, test results, flaky tests, failure patterns",
            "repo": "Code search, file access, git diffs, blame",
            "jira": "Ticket management, sprints, project stats",
            "observability": "Distributed traces, logs, metrics, alerts",
            "rag": "Semantic search, hybrid retrieval, context building, document indexing",
        },
    }


# Global MCP server instance (lazy initialized)
_mcp_server: Optional[MCPServer] = None


def get_mcp_server() -> MCPServer:
    """
    Get the global MCP server instance, creating it if necessary.

    Returns:
        The global MCPServer instance
    """
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = create_nexusai_mcp_server()
    return _mcp_server


def reset_mcp_server() -> None:
    """Reset the global MCP server instance."""
    global _mcp_server
    _mcp_server = None
