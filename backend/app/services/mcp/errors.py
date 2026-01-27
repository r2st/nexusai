"""
MCP Tool Error Handling

Provides structured error responses that guide the LLM to take appropriate action.
Errors are categorized to enable automatic retry for transient failures
and helpful user guidance for permanent failures.
"""

from enum import Enum
from typing import Any
from dataclasses import dataclass, field


class ErrorCategory(str, Enum):
    """Categories of errors for different handling strategies."""
    
    # Transient errors - can be retried
    TRANSIENT = "transient"  # Network issues, timeouts, rate limits
    
    # User-fixable errors - need user action
    AUTH_REQUIRED = "auth_required"  # Missing token/credentials
    INVALID_INPUT = "invalid_input"  # Bad parameters from user
    NOT_FOUND = "not_found"  # Resource doesn't exist
    PERMISSION_DENIED = "permission_denied"  # User lacks access
    
    # System errors - need admin/developer action
    CONFIGURATION = "configuration"  # Missing config, service not set up
    SERVICE_UNAVAILABLE = "service_unavailable"  # External service down
    INTERNAL = "internal"  # Unexpected errors


class ErrorSeverity(str, Enum):
    """Severity levels for error handling."""
    
    INFO = "info"  # Not really an error, just informational
    WARNING = "warning"  # Partial success or degraded result
    ERROR = "error"  # Operation failed but recoverable
    CRITICAL = "critical"  # System-level failure


@dataclass
class ToolErrorResponse:
    """Structured error response from an MCP tool."""
    
    success: bool = False
    error_category: ErrorCategory = ErrorCategory.INTERNAL
    error_code: str = "UNKNOWN_ERROR"
    error_message: str = "An unknown error occurred"
    severity: ErrorSeverity = ErrorSeverity.ERROR
    
    # User-facing guidance
    user_message: str = ""
    suggestions: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)
    
    # Technical details (for debugging)
    details: dict[str, Any] = field(default_factory=dict)
    
    # Retry information
    retryable: bool = False
    retry_after_seconds: int | None = None
    
    # Related resources
    related_tools: list[str] = field(default_factory=list)
    documentation_url: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "error": {
                "category": self.error_category.value,
                "code": self.error_code,
                "message": self.error_message,
                "severity": self.severity.value,
            },
            "guidance": {
                "user_message": self.user_message,
                "suggestions": self.suggestions,
                "next_steps": self.next_steps,
            },
            "retry": {
                "retryable": self.retryable,
                "retry_after_seconds": self.retry_after_seconds,
            },
            "help": {
                "related_tools": self.related_tools,
                "documentation_url": self.documentation_url,
            },
            "details": self.details,
        }

    def to_llm_context(self) -> str:
        """Format error for LLM context with actionable guidance."""
        lines = [
            f"❌ **Error**: {self.error_message}",
            f"   Category: {self.error_category.value}",
        ]
        
        if self.user_message:
            lines.append(f"\n📝 **What this means**: {self.user_message}")
        
        if self.suggestions:
            lines.append("\n💡 **Suggestions**:")
            for suggestion in self.suggestions:
                lines.append(f"   - {suggestion}")
        
        if self.next_steps:
            lines.append("\n🔧 **Next steps**:")
            for i, step in enumerate(self.next_steps, 1):
                lines.append(f"   {i}. {step}")
        
        if self.related_tools:
            lines.append(f"\n🔗 **Related tools**: {', '.join(self.related_tools)}")
        
        if self.retryable:
            retry_msg = f"after {self.retry_after_seconds}s" if self.retry_after_seconds else "now"
            lines.append(f"\n🔄 **Retryable**: Yes, can retry {retry_msg}")
        
        return "\n".join(lines)


# ============================================================================
# Pre-built error responses for common scenarios
# ============================================================================

def service_unavailable_error(
    service_name: str,
    details: dict[str, Any] | None = None,
) -> ToolErrorResponse:
    """Error when an external service (e.g., DevLake) is not available."""
    base_url = details.get("base_url", "unknown") if details else "unknown"
    return ToolErrorResponse(
        error_category=ErrorCategory.SERVICE_UNAVAILABLE,
        error_code="SERVICE_UNAVAILABLE",
        error_message=f"{service_name} service is not available at {base_url}",
        severity=ErrorSeverity.ERROR,
        user_message=f"The {service_name} service is currently unavailable at {base_url}. This might be temporary.",
        suggestions=[
            f"Check if {service_name} is running at {base_url}",
            f"Try: curl {base_url}/ping to verify connectivity",
            "Wait a moment and try again",
            "Contact your administrator if the problem persists",
        ],
        next_steps=[
            f"Use 'devlake_health_check' to verify {service_name} status",
            "Check the service logs for errors",
            f"Ensure {service_name} container is running: docker ps | grep devlake",
        ],
        retryable=True,
        retry_after_seconds=5,
        related_tools=["devlake_health_check"],
        details=details or {},
    )


def not_found_error(
    resource_type: str,
    resource_name: str,
    available_resources: list[str] | None = None,
) -> ToolErrorResponse:
    """Error when a requested resource doesn't exist."""
    suggestions = [f"Check the {resource_type} name for typos"]
    next_steps = []
    
    if available_resources:
        if available_resources:
            suggestions.append(f"Available {resource_type}s: {', '.join(available_resources[:5])}")
            next_steps.append(f"Use one of the available {resource_type}s")
        else:
            suggestions.append(f"No {resource_type}s are configured yet")
            next_steps.append(f"Create a new {resource_type} first")
    
    return ToolErrorResponse(
        error_category=ErrorCategory.NOT_FOUND,
        error_code="RESOURCE_NOT_FOUND",
        error_message=f"{resource_type.title()} '{resource_name}' not found",
        severity=ErrorSeverity.WARNING,
        user_message=f"The {resource_type} '{resource_name}' doesn't exist in the system.",
        suggestions=suggestions,
        next_steps=next_steps,
        related_tools=[f"devlake_list_{resource_type}s", f"devlake_create_{resource_type}"],
        details={
            "resource_type": resource_type,
            "resource_name": resource_name,
            "available": available_resources or [],
        },
    )


def auth_required_error(
    service_name: str,
    token_type: str = "API token",
    how_to_get_token: str | None = None,
) -> ToolErrorResponse:
    """Error when authentication is required but not provided."""
    next_steps = [
        f"Obtain a {token_type} for {service_name}",
        "Provide the token to create a connection",
    ]
    
    return ToolErrorResponse(
        error_category=ErrorCategory.AUTH_REQUIRED,
        error_code="AUTH_REQUIRED",
        error_message=f"Authentication required for {service_name}",
        severity=ErrorSeverity.WARNING,
        user_message=f"To access {service_name}, you need to provide a {token_type}.",
        suggestions=[
            how_to_get_token or f"Generate a {token_type} from {service_name} settings",
            "Keep your token secure and don't share it",
        ],
        next_steps=next_steps,
        related_tools=["devlake_create_connection"],
        details={
            "service": service_name,
            "token_type": token_type,
        },
    )


def invalid_input_error(
    parameter_name: str,
    expected: str,
    received: Any = None,
) -> ToolErrorResponse:
    """Error when user provides invalid input."""
    return ToolErrorResponse(
        error_category=ErrorCategory.INVALID_INPUT,
        error_code="INVALID_INPUT",
        error_message=f"Invalid value for '{parameter_name}'",
        severity=ErrorSeverity.WARNING,
        user_message=f"The value provided for '{parameter_name}' is not valid.",
        suggestions=[
            f"Expected: {expected}",
            f"Received: {received}" if received is not None else "No value provided",
        ],
        next_steps=[
            "Provide a valid value and try again",
        ],
        details={
            "parameter": parameter_name,
            "expected": expected,
            "received": str(received) if received is not None else None,
        },
    )


def rate_limit_error(
    retry_after: int = 60,
) -> ToolErrorResponse:
    """Error when rate limited by an external service."""
    return ToolErrorResponse(
        error_category=ErrorCategory.TRANSIENT,
        error_code="RATE_LIMITED",
        error_message="Rate limit exceeded",
        severity=ErrorSeverity.WARNING,
        user_message="Too many requests. Please wait before trying again.",
        suggestions=[
            f"Wait {retry_after} seconds before retrying",
            "Consider batching your requests",
        ],
        retryable=True,
        retry_after_seconds=retry_after,
    )


def connection_error(
    target: str,
    original_error: str | None = None,
) -> ToolErrorResponse:
    """Error when cannot connect to an external service."""
    return ToolErrorResponse(
        error_category=ErrorCategory.TRANSIENT,
        error_code="CONNECTION_ERROR",
        error_message=f"Cannot connect to {target}",
        severity=ErrorSeverity.ERROR,
        user_message=f"Unable to establish connection to {target}. This might be a temporary network issue.",
        suggestions=[
            "Check if the service is running",
            "Verify network connectivity",
            "Try again in a few moments",
        ],
        retryable=True,
        retry_after_seconds=3,
        details={
            "target": target,
            "original_error": original_error,
        },
    )


def configuration_error(
    what_is_missing: str,
    how_to_fix: str,
) -> ToolErrorResponse:
    """Error when system configuration is incomplete."""
    return ToolErrorResponse(
        error_category=ErrorCategory.CONFIGURATION,
        error_code="CONFIGURATION_ERROR",
        error_message=f"Configuration missing: {what_is_missing}",
        severity=ErrorSeverity.ERROR,
        user_message="The system is not fully configured for this operation.",
        suggestions=[
            how_to_fix,
            "Contact your administrator if you don't have access to configuration",
        ],
        next_steps=[
            how_to_fix,
        ],
        details={
            "missing": what_is_missing,
        },
    )


def timeout_error(
    operation: str,
    timeout_seconds: int,
) -> ToolErrorResponse:
    """Error when an operation times out."""
    return ToolErrorResponse(
        error_category=ErrorCategory.TRANSIENT,
        error_code="TIMEOUT",
        error_message=f"Operation '{operation}' timed out after {timeout_seconds}s",
        severity=ErrorSeverity.WARNING,
        user_message="The operation took too long to complete. This might be due to heavy load.",
        suggestions=[
            "Try again - the service might be temporarily slow",
            "If the problem persists, try a simpler query",
        ],
        retryable=True,
        retry_after_seconds=2,
        details={
            "operation": operation,
            "timeout_seconds": timeout_seconds,
        },
    )


def internal_error(
    operation: str,
    error_message: str,
    details: dict[str, Any] | None = None,
) -> ToolErrorResponse:
    """Generic internal error for unexpected failures."""
    return ToolErrorResponse(
        error_category=ErrorCategory.INTERNAL,
        error_code="INTERNAL_ERROR",
        error_message=f"Internal error during '{operation}': {error_message}",
        severity=ErrorSeverity.ERROR,
        user_message="An unexpected error occurred. Our team has been notified.",
        suggestions=[
            "Try the operation again",
            "If the problem persists, contact support",
        ],
        details={
            "operation": operation,
            "error": error_message,
            **(details or {}),
        },
    )


# ============================================================================
# Helper for wrapping tool execution with error handling
# ============================================================================

async def safe_tool_execute(
    tool_name: str,
    execute_fn,
    *args,
    **kwargs,
) -> dict[str, Any]:
    """
    Wrapper that executes a tool function with standardized error handling.
    
    Usage:
        result = await safe_tool_execute(
            "devlake_get_dora_metrics",
            lambda: devlake_service.get_dora_metrics(project_name),
        )
    """
    import httpx
    import asyncio
    
    try:
        result = await execute_fn(*args, **kwargs)
        return {"success": True, "result": result}
    
    except httpx.ConnectError as e:
        return connection_error(
            target="DevLake API",
            original_error=str(e),
        ).to_dict()
    
    except httpx.TimeoutException as e:
        return timeout_error(
            operation=tool_name,
            timeout_seconds=30,
        ).to_dict()
    
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            return rate_limit_error(retry_after=60).to_dict()
        elif e.response.status_code == 401:
            return auth_required_error(service_name="DevLake").to_dict()
        elif e.response.status_code == 403:
            return ToolErrorResponse(
                error_category=ErrorCategory.PERMISSION_DENIED,
                error_code="FORBIDDEN",
                error_message="Permission denied",
                user_message="You don't have permission to perform this action.",
            ).to_dict()
        elif e.response.status_code == 404:
            return not_found_error(
                resource_type="resource",
                resource_name="requested",
            ).to_dict()
        else:
            return internal_error(
                operation=tool_name,
                error_message=f"HTTP {e.response.status_code}: {e.response.text}",
            ).to_dict()
    
    except asyncio.TimeoutError:
        return timeout_error(
            operation=tool_name,
            timeout_seconds=30,
        ).to_dict()
    
    except Exception as e:
        return internal_error(
            operation=tool_name,
            error_message=str(e),
        ).to_dict()
