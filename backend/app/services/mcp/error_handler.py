"""
MCP Error Handler Service

Provides intelligent error handling with LLM-driven recovery actions.
When a tool fails, this service analyzes the error and suggests/executes
recovery actions autonomously.
"""

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable, Optional

from .errors import (
    ErrorCategory,
    ToolErrorResponse,
    service_unavailable_error,
    connection_error,
    not_found_error,
    auth_required_error,
    internal_error,
)

logger = logging.getLogger(__name__)


class RecoveryAction(str, Enum):
    """Types of recovery actions the system can take."""
    HEALTH_CHECK = "health_check"
    RETRY = "retry"
    LIST_RESOURCES = "list_resources"
    SUGGEST_ALTERNATIVE = "suggest_alternative"
    REQUEST_AUTH = "request_auth"
    NONE = "none"


@dataclass
class RecoveryPlan:
    """Plan for recovering from an error."""
    action: RecoveryAction
    tool_to_run: Optional[str] = None
    tool_arguments: dict = field(default_factory=dict)
    user_message: str = ""
    auto_execute: bool = False  # Whether to auto-execute or ask user first


@dataclass
class ErrorContext:
    """Context about an error for intelligent handling."""
    tool_name: str
    error_category: ErrorCategory
    error_message: str
    http_status: Optional[int] = None
    original_arguments: dict = field(default_factory=dict)
    retry_count: int = 0


class MCPErrorHandler:
    """
    Intelligent error handler that determines recovery actions.

    This handler analyzes tool execution errors and decides:
    1. What recovery action to take
    2. Whether to auto-execute recovery or ask the user
    3. What tools to call for recovery (e.g., health_check)
    """

    # Map of tool prefixes to their health check tools
    HEALTH_CHECK_TOOLS = {
        "devlake_": "devlake_health_check",
        "jira_": "jira_health_check",
        "ci_": "ci_health_check",
        "obs_": "obs_health_check",
        "repo_": "repo_health_check",
    }

    # Map of tool prefixes to their list tools
    LIST_TOOLS = {
        "devlake_": {
            "project": "devlake_list_projects",
            "connection": "devlake_list_connections",
            "blueprint": "devlake_list_blueprints",
            "pipeline": "devlake_list_pipelines",
        },
        "jira_": {
            "issue": "jira_search_issues",
            "project": "jira_list_projects",
        },
    }

    def __init__(
        self,
        tool_executor: Optional[Callable[[str, dict], Awaitable[str]]] = None,
        available_tools: Optional[dict] = None,
        auto_execute_recovery: Optional[bool] = None,
        max_recovery_depth: Optional[int] = None,
    ):
        """
        Initialize the error handler.

        Args:
            tool_executor: Function to execute MCP tools
            available_tools: Dict of available tool names -> (server_name, MCPTool)
            auto_execute_recovery: Whether to auto-execute recovery actions (from settings if None)
            max_recovery_depth: Maximum recovery depth (from settings if None)
        """
        from app.core.config import settings

        self.tool_executor = tool_executor
        self.available_tools = available_tools or {}
        self.auto_execute_recovery = (
            auto_execute_recovery if auto_execute_recovery is not None
            else settings.MCP_AUTO_EXECUTE_RECOVERY
        )
        self.max_recovery_depth = (
            max_recovery_depth if max_recovery_depth is not None
            else settings.MCP_MAX_RECOVERY_DEPTH
        )

    def analyze_error(self, context: ErrorContext) -> RecoveryPlan:
        """
        Analyze an error and determine the best recovery plan.

        Args:
            context: Error context with all relevant information

        Returns:
            RecoveryPlan with recommended action
        """
        logger.info(
            "Analyzing error for recovery",
            tool_name=context.tool_name,
            error_category=context.error_category.value,
            http_status=context.http_status,
        )

        # Service unavailable or connection errors -> health check
        if context.error_category in (
            ErrorCategory.SERVICE_UNAVAILABLE,
            ErrorCategory.TRANSIENT,
        ) or context.http_status in (502, 503, 504):
            return self._plan_health_check(context)

        # Not found errors -> list available resources
        if context.error_category == ErrorCategory.NOT_FOUND or context.http_status == 404:
            return self._plan_list_resources(context)

        # Auth errors -> request credentials
        if context.error_category == ErrorCategory.AUTH_REQUIRED or context.http_status == 401:
            return self._plan_auth_request(context)

        # Permission denied
        if context.error_category == ErrorCategory.PERMISSION_DENIED or context.http_status == 403:
            return RecoveryPlan(
                action=RecoveryAction.NONE,
                user_message="You don't have permission to perform this action. Please contact your administrator.",
            )

        # Configuration errors
        if context.error_category == ErrorCategory.CONFIGURATION:
            return RecoveryPlan(
                action=RecoveryAction.NONE,
                user_message=f"Configuration error: {context.error_message}. Please check your setup.",
            )

        # Default: no automatic recovery
        return RecoveryPlan(
            action=RecoveryAction.NONE,
            user_message=f"Error: {context.error_message}",
        )

    def _plan_health_check(self, context: ErrorContext) -> RecoveryPlan:
        """Plan a health check recovery action."""
        health_tool = self._get_health_check_tool(context.tool_name)

        if health_tool and health_tool in self.available_tools:
            return RecoveryPlan(
                action=RecoveryAction.HEALTH_CHECK,
                tool_to_run=health_tool,
                tool_arguments={},
                user_message=f"The service appears to be unavailable. Let me check its health status...",
                auto_execute=self.auto_execute_recovery,  # Use setting for auto-execution
            )

        return RecoveryPlan(
            action=RecoveryAction.RETRY,
            user_message="The service is temporarily unavailable. Please try again in a moment.",
        )

    def _plan_list_resources(self, context: ErrorContext) -> RecoveryPlan:
        """Plan a list resources recovery action."""
        list_tool = self._get_list_tool(context)

        if list_tool and list_tool in self.available_tools:
            return RecoveryPlan(
                action=RecoveryAction.LIST_RESOURCES,
                tool_to_run=list_tool,
                tool_arguments={},
                user_message=f"The requested resource was not found. Let me show you what's available...",
                auto_execute=self.auto_execute_recovery,  # Use setting for auto-execution
            )

        return RecoveryPlan(
            action=RecoveryAction.SUGGEST_ALTERNATIVE,
            user_message="The requested resource was not found. Please check the name and try again.",
        )

    def _plan_auth_request(self, context: ErrorContext) -> RecoveryPlan:
        """Plan an authentication request."""
        service_name = self._get_service_name(context.tool_name)

        return RecoveryPlan(
            action=RecoveryAction.REQUEST_AUTH,
            user_message=f"Authentication is required for {service_name}. Please provide your credentials.",
            auto_execute=False,
        )

    def _get_health_check_tool(self, tool_name: str) -> Optional[str]:
        """Get the health check tool for a given tool."""
        for prefix, health_tool in self.HEALTH_CHECK_TOOLS.items():
            if tool_name.startswith(prefix):
                return health_tool
        return None

    def _get_list_tool(self, context: ErrorContext) -> Optional[str]:
        """Get the appropriate list tool based on the error context."""
        for prefix, tools in self.LIST_TOOLS.items():
            if context.tool_name.startswith(prefix):
                # Try to determine resource type from tool name
                for resource_type, list_tool in tools.items():
                    if resource_type in context.tool_name.lower():
                        return list_tool
                # Default to first list tool for the service
                return list(tools.values())[0] if tools else None
        return None

    def _get_service_name(self, tool_name: str) -> str:
        """Extract service name from tool name."""
        if tool_name.startswith("devlake_"):
            return "DevLake"
        elif tool_name.startswith("jira_"):
            return "Jira"
        elif tool_name.startswith("ci_"):
            return "CI/CD"
        elif tool_name.startswith("obs_"):
            return "Observability"
        elif tool_name.startswith("repo_"):
            return "Repository"
        return "the service"

    async def execute_recovery(
        self,
        plan: RecoveryPlan,
    ) -> Optional[str]:
        """
        Execute a recovery plan if it has an auto-executable action.

        Args:
            plan: The recovery plan to execute

        Returns:
            Tool execution result if recovery was executed, None otherwise
        """
        if not plan.auto_execute or not plan.tool_to_run:
            return None

        if not self.tool_executor:
            logger.warning("No tool executor provided for recovery action")
            return None

        if plan.tool_to_run not in self.available_tools:
            logger.warning(f"Recovery tool {plan.tool_to_run} not available")
            return None

        logger.info(
            "Executing recovery action",
            action=plan.action.value,
            tool=plan.tool_to_run,
        )

        try:
            result = await self.tool_executor(plan.tool_to_run, plan.tool_arguments)
            return result
        except Exception as e:
            logger.error(f"Recovery action failed: {e}")
            return None

    def parse_error_from_result(
        self,
        tool_name: str,
        result: str,
        original_arguments: dict,
    ) -> Optional[ErrorContext]:
        """
        Parse a tool result to extract error context if it's an error.

        Args:
            tool_name: Name of the tool that was executed
            result: The tool result string (may be JSON)
            original_arguments: Arguments passed to the tool

        Returns:
            ErrorContext if the result is an error, None otherwise
        """
        try:
            result_dict = json.loads(result)
        except json.JSONDecodeError:
            # If it's not JSON, check for error patterns in text
            if "error" in result.lower() or "failed" in result.lower():
                return ErrorContext(
                    tool_name=tool_name,
                    error_category=ErrorCategory.INTERNAL,
                    error_message=result[:200],
                    original_arguments=original_arguments,
                )
            return None

        # Check for success flag
        if result_dict.get("success", True):
            return None

        # Extract error information
        error_info = result_dict.get("error", {})

        # Handle string error (legacy format)
        if isinstance(error_info, str):
            return ErrorContext(
                tool_name=tool_name,
                error_category=ErrorCategory.INTERNAL,
                error_message=error_info,
                original_arguments=original_arguments,
            )

        # Handle structured error
        category_str = error_info.get("category", "internal")
        try:
            category = ErrorCategory(category_str)
        except ValueError:
            category = ErrorCategory.INTERNAL

        # Try to extract HTTP status from details
        details = result_dict.get("details", {})
        http_status = details.get("status_code") or details.get("http_status")

        return ErrorContext(
            tool_name=tool_name,
            error_category=category,
            error_message=error_info.get("message", "Unknown error"),
            http_status=http_status,
            original_arguments=original_arguments,
        )

    def format_recovery_response(
        self,
        original_error: str,
        recovery_plan: RecoveryPlan,
        recovery_result: Optional[str] = None,
    ) -> str:
        """
        Format a response that includes the error and recovery information.

        Args:
            original_error: The original error message/result
            recovery_plan: The recovery plan that was determined
            recovery_result: Result of recovery action if executed

        Returns:
            Formatted response string
        """
        lines = []

        # Add recovery message
        if recovery_plan.user_message:
            lines.append(f"\n{recovery_plan.user_message}")

        # Add recovery result if available
        if recovery_result:
            lines.append(f"\n**Recovery Action Result:**")
            try:
                result_dict = json.loads(recovery_result)
                if result_dict.get("success"):
                    if result_dict.get("healthy"):
                        lines.append("Service is **healthy** and available.")
                    elif "count" in result_dict:
                        lines.append(f"Found {result_dict['count']} available resources.")
                    if result_dict.get("message"):
                        lines.append(result_dict["message"])
                else:
                    lines.append("Recovery check also failed - service may be down.")
            except json.JSONDecodeError:
                lines.append(recovery_result[:300])

        # Add suggested next steps based on recovery plan
        if recovery_plan.action == RecoveryAction.HEALTH_CHECK:
            lines.append("\n**Suggested Actions:**")
            lines.append("1. Wait a moment and try again")
            lines.append("2. Check if the service is running")
            lines.append("3. Contact your administrator if the issue persists")
        elif recovery_plan.action == RecoveryAction.LIST_RESOURCES:
            lines.append("\n**Tip:** Use the list above to find the correct resource name.")
        elif recovery_plan.action == RecoveryAction.REQUEST_AUTH:
            lines.append("\n**To authenticate:**")
            lines.append("1. Obtain an API token from the service")
            lines.append("2. Create a connection: `devlake_create_connection(plugin='...', name='...', token='...')`")

        return "\n".join(lines)


# Singleton instance for use across the application
_error_handler: Optional[MCPErrorHandler] = None


def get_error_handler() -> MCPErrorHandler:
    """Get or create the global error handler instance."""
    global _error_handler
    if _error_handler is None:
        _error_handler = MCPErrorHandler()
    return _error_handler


def set_error_handler(handler: MCPErrorHandler) -> None:
    """Set the global error handler instance."""
    global _error_handler
    _error_handler = handler
