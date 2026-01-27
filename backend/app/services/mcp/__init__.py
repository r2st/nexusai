"""
MCP (Model Context Protocol) Integration Layer

Implements MCP to expose NexusAI capabilities to external LLM clients
and consume external MCP servers.

MCP Servers (expose capabilities):
- DevLake: DORA metrics, connections, pipelines, blueprints, PR-Issue correlations
- Policy: RBAC, data redaction, audit logging
- CI/CD: Build logs, test results, flaky tests, failure patterns
- Repository: Code search, file access, git diffs, blame
- Jira: Ticket management, sprints, project stats
- Observability: Distributed traces, logs, metrics, alerts

MCP Client (consume external tools):
- Connect to any MCP server
- Discover and use tools
- Route through NexusAI's tool system
"""

from .server import MCPServer, MCPServerConfig
from .client import MCPClient, MCPClientConfig
from .protocol import (
    MCPRequest,
    MCPResponse,
    MCPTool,
    MCPResource,
    MCPPrompt,
)
from .setup import (
    create_nexusai_mcp_server,
    get_mcp_server,
    list_available_tools,
    get_devlake_tools_summary,
    get_all_tools_summary,
)
from .devlake_tools import get_all_devlake_tool_handlers
from .policy_tools import get_all_policy_tool_handlers
from .ci_tools import get_all_ci_tool_handlers
from .repo_tools import get_all_repo_tool_handlers
from .jira_tools import get_all_jira_tool_handlers
from .observability_tools import get_all_observability_tool_handlers
from .rag_tools import get_all_rag_tool_handlers
from .errors import (
    ToolErrorResponse,
    ErrorCategory,
    ErrorSeverity,
    service_unavailable_error,
    not_found_error,
    auth_required_error,
    invalid_input_error,
    rate_limit_error,
    connection_error,
    configuration_error,
    timeout_error,
    internal_error,
    safe_tool_execute,
)
from .gateway import (
    MCPGateway,
    get_mcp_gateway,
    reset_mcp_gateway,
    RateLimitConfig,
    RateLimiter,
    ToolPolicy,
    ApprovalRequest,
    ApprovalStatus,
    AuditLogEntry,
    CircuitBreaker,
    CircuitState,
)
from .permissions import (
    Permission,
    PermissionChecker,
    ToolPermissionRequirement,
    get_permission_checker,
    reset_permission_checker,
)
from .governance import (
    ToolGovernanceRegistry,
    ToolRegistration,
    OrganizationToolConfig,
    ToolRiskLevel,
    ToolStatus,
    ToolAccessLevel,
    get_governance_registry,
    reset_governance_registry,
    auto_register_tools,
)
from .http_transport import (
    MCPHTTPTransport,
    HTTPTransportConfig,
    MCPSession,
    SessionManager,
    TransportType,
    get_mcp_http_transport,
    create_mcp_http_transport,
    reset_mcp_http_transport,
)

__all__ = [
    # Server
    "MCPServer",
    "MCPServerConfig",
    # Client
    "MCPClient",
    "MCPClientConfig",
    # Protocol
    "MCPRequest",
    "MCPResponse",
    "MCPTool",
    "MCPResource",
    "MCPPrompt",
    # Setup
    "create_nexusai_mcp_server",
    "get_mcp_server",
    "list_available_tools",
    "get_devlake_tools_summary",
    "get_all_tools_summary",
    # Tool handlers
    "get_all_devlake_tool_handlers",
    "get_all_policy_tool_handlers",
    "get_all_ci_tool_handlers",
    "get_all_repo_tool_handlers",
    "get_all_jira_tool_handlers",
    "get_all_observability_tool_handlers",
    "get_all_rag_tool_handlers",
    # Error handling
    "ToolErrorResponse",
    "ErrorCategory",
    "ErrorSeverity",
    "service_unavailable_error",
    "not_found_error",
    "auth_required_error",
    "invalid_input_error",
    "rate_limit_error",
    "connection_error",
    "configuration_error",
    "timeout_error",
    "internal_error",
    "safe_tool_execute",
    # Gateway
    "MCPGateway",
    "get_mcp_gateway",
    "reset_mcp_gateway",
    "RateLimitConfig",
    "RateLimiter",
    "ToolPolicy",
    "ApprovalRequest",
    "ApprovalStatus",
    "AuditLogEntry",
    "CircuitBreaker",
    "CircuitState",
    # Permissions
    "Permission",
    "PermissionChecker",
    "ToolPermissionRequirement",
    "get_permission_checker",
    "reset_permission_checker",
    # Governance
    "ToolGovernanceRegistry",
    "ToolRegistration",
    "OrganizationToolConfig",
    "ToolRiskLevel",
    "ToolStatus",
    "ToolAccessLevel",
    "get_governance_registry",
    "reset_governance_registry",
    "auto_register_tools",
    # HTTP Transport
    "MCPHTTPTransport",
    "HTTPTransportConfig",
    "MCPSession",
    "SessionManager",
    "TransportType",
    "get_mcp_http_transport",
    "create_mcp_http_transport",
    "reset_mcp_http_transport",
]
