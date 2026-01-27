"""
MCP Gateway - Centralized Tool Management, Rate Limiting, and Routing

The MCP Gateway acts as a central control point for all MCP tool calls, providing:
- Rate limiting per user/organization
- Request routing and load balancing
- Audit logging for all tool invocations
- Permission enforcement before tool execution
- Approval workflow for sensitive actions
- Circuit breaker for failing services
"""

import asyncio
import time
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional
from collections import defaultdict
import hashlib
import json

from sqlalchemy.ext.asyncio import AsyncSession

from .server import MCPServer, MCPToolHandler
from .errors import (
    ToolErrorResponse,
    ErrorCategory,
    ErrorSeverity,
    rate_limit_error,
    auth_required_error,
    internal_error,
)
from .permissions import PermissionChecker, get_permission_checker

logger = logging.getLogger(__name__)


class ApprovalStatus(str, Enum):
    """Status of an approval request."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    AUTO_APPROVED = "auto_approved"


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    burst_limit: int = 10  # Max requests in 1 second


@dataclass
class ToolPolicy:
    """Policy configuration for a tool."""
    tool_name: str
    enabled: bool = True
    requires_approval: bool = False
    approval_timeout_seconds: int = 300  # 5 minutes
    allowed_roles: list[str] = field(default_factory=lambda: ["admin", "developer", "user"])
    rate_limit_override: Optional[RateLimitConfig] = None
    audit_level: str = "standard"  # minimal, standard, verbose
    sensitive: bool = False  # If true, redact parameters in logs


@dataclass
class ApprovalRequest:
    """A pending approval request for a tool invocation."""
    request_id: str
    tool_name: str
    user_id: str
    arguments: dict[str, Any]
    context: dict[str, Any]
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    rejection_reason: Optional[str] = None


@dataclass
class AuditLogEntry:
    """Audit log entry for tool invocations."""
    entry_id: str
    timestamp: datetime
    user_id: str
    organization_id: Optional[str]
    tool_name: str
    action: str  # "invoke", "approve", "reject", "complete", "error"
    arguments: dict[str, Any]
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: Optional[float] = None
    approval_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CircuitBreaker:
    """Circuit breaker for a tool/service."""
    tool_name: str
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    failure_threshold: int = 5
    recovery_timeout_seconds: int = 30
    half_open_max_calls: int = 3


class RateLimiter:
    """Token bucket rate limiter with multiple time windows."""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self._buckets: dict[str, dict[str, list[float]]] = defaultdict(
            lambda: {"minute": [], "hour": [], "day": [], "second": []}
        )
        self._lock = asyncio.Lock()

    async def check_and_consume(self, key: str) -> tuple[bool, Optional[str]]:
        """
        Check if request is allowed and consume a token.

        Returns:
            Tuple of (allowed, error_message)
        """
        async with self._lock:
            now = time.time()
            buckets = self._buckets[key]

            # Clean old entries
            buckets["second"] = [t for t in buckets["second"] if now - t < 1]
            buckets["minute"] = [t for t in buckets["minute"] if now - t < 60]
            buckets["hour"] = [t for t in buckets["hour"] if now - t < 3600]
            buckets["day"] = [t for t in buckets["day"] if now - t < 86400]

            # Check limits
            if len(buckets["second"]) >= self.config.burst_limit:
                return False, f"Burst limit exceeded ({self.config.burst_limit}/sec)"

            if len(buckets["minute"]) >= self.config.requests_per_minute:
                return False, f"Rate limit exceeded ({self.config.requests_per_minute}/min)"

            if len(buckets["hour"]) >= self.config.requests_per_hour:
                return False, f"Rate limit exceeded ({self.config.requests_per_hour}/hour)"

            if len(buckets["day"]) >= self.config.requests_per_day:
                return False, f"Rate limit exceeded ({self.config.requests_per_day}/day)"

            # Consume token
            buckets["second"].append(now)
            buckets["minute"].append(now)
            buckets["hour"].append(now)
            buckets["day"].append(now)

            return True, None

    def get_remaining(self, key: str) -> dict[str, int]:
        """Get remaining requests for each time window."""
        now = time.time()
        buckets = self._buckets.get(key, {"minute": [], "hour": [], "day": [], "second": []})

        return {
            "second": max(0, self.config.burst_limit - len([t for t in buckets["second"] if now - t < 1])),
            "minute": max(0, self.config.requests_per_minute - len([t for t in buckets["minute"] if now - t < 60])),
            "hour": max(0, self.config.requests_per_hour - len([t for t in buckets["hour"] if now - t < 3600])),
            "day": max(0, self.config.requests_per_day - len([t for t in buckets["day"] if now - t < 86400])),
        }


class MCPGateway:
    """
    Central gateway for MCP tool invocations.

    Provides:
    - Rate limiting per user/organization
    - Permission enforcement
    - Approval workflows for sensitive tools
    - Audit logging
    - Circuit breakers for failing services
    """

    def __init__(
        self,
        mcp_server: MCPServer,
        default_rate_limit: Optional[RateLimitConfig] = None,
        audit_callback: Optional[Callable[[AuditLogEntry], None]] = None,
        db_session: Optional[AsyncSession] = None,
    ):
        self.mcp_server = mcp_server
        self.default_rate_limit = default_rate_limit or RateLimitConfig()
        self.audit_callback = audit_callback
        self._db_session = db_session
        self._audit_service = None

        # Rate limiters per user/org
        self._user_rate_limiters: dict[str, RateLimiter] = {}
        self._org_rate_limiters: dict[str, RateLimiter] = {}
        self._tool_rate_limiters: dict[str, dict[str, RateLimiter]] = defaultdict(dict)

        # Tool policies
        self._tool_policies: dict[str, ToolPolicy] = {}

        # Pending approvals
        self._pending_approvals: dict[str, ApprovalRequest] = {}

        # Circuit breakers
        self._circuit_breakers: dict[str, CircuitBreaker] = {}

        # Audit log (in-memory for now, should be persisted)
        self._audit_log: list[AuditLogEntry] = []
        self._audit_lock = asyncio.Lock()

        # Permission checker
        self._permission_checker = get_permission_checker()

        # Initialize default policies for all registered tools
        self._initialize_default_policies()

    def set_db_session(self, db_session: AsyncSession) -> None:
        """Set the database session for audit persistence."""
        self._db_session = db_session
        self._audit_service = None  # Reset to create new instance with new session

    def _get_audit_service(self):
        """Get or create the audit service."""
        if self._audit_service is None and self._db_session is not None:
            from app.services.audit import AuditService
            self._audit_service = AuditService(self._db_session)
        return self._audit_service

    def _initialize_default_policies(self) -> None:
        """Initialize default policies for all registered tools."""
        for tool_name in self.mcp_server._tools:
            if tool_name not in self._tool_policies:
                # Set default policy based on tool name patterns
                sensitive = any(
                    pattern in tool_name.lower()
                    for pattern in ["delete", "remove", "drop", "deploy", "execute", "run"]
                )
                requires_approval = any(
                    pattern in tool_name.lower()
                    for pattern in ["deploy", "delete", "production", "execute"]
                )
                self._tool_policies[tool_name] = ToolPolicy(
                    tool_name=tool_name,
                    sensitive=sensitive,
                    requires_approval=requires_approval,
                )

    def set_tool_policy(self, policy: ToolPolicy) -> None:
        """Set or update a tool policy."""
        self._tool_policies[policy.tool_name] = policy
        logger.info(f"Tool policy set for {policy.tool_name}: requires_approval={policy.requires_approval}")

    def get_tool_policy(self, tool_name: str) -> ToolPolicy:
        """Get the policy for a tool."""
        return self._tool_policies.get(tool_name, ToolPolicy(tool_name=tool_name))

    def _get_user_rate_limiter(self, user_id: str, tool_name: Optional[str] = None) -> RateLimiter:
        """Get or create a rate limiter for a user."""
        if tool_name:
            policy = self.get_tool_policy(tool_name)
            if policy.rate_limit_override:
                if user_id not in self._tool_rate_limiters[tool_name]:
                    self._tool_rate_limiters[tool_name][user_id] = RateLimiter(policy.rate_limit_override)
                return self._tool_rate_limiters[tool_name][user_id]

        if user_id not in self._user_rate_limiters:
            self._user_rate_limiters[user_id] = RateLimiter(self.default_rate_limit)
        return self._user_rate_limiters[user_id]

    def _get_circuit_breaker(self, tool_name: str) -> CircuitBreaker:
        """Get or create a circuit breaker for a tool."""
        if tool_name not in self._circuit_breakers:
            self._circuit_breakers[tool_name] = CircuitBreaker(tool_name=tool_name)
        return self._circuit_breakers[tool_name]

    def _check_circuit_breaker(self, tool_name: str) -> tuple[bool, Optional[str]]:
        """Check if circuit breaker allows the request."""
        cb = self._get_circuit_breaker(tool_name)

        if cb.state == CircuitState.CLOSED:
            return True, None

        if cb.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if cb.last_failure_time:
                elapsed = (datetime.utcnow() - cb.last_failure_time).total_seconds()
                if elapsed >= cb.recovery_timeout_seconds:
                    cb.state = CircuitState.HALF_OPEN
                    cb.success_count = 0
                    logger.info(f"Circuit breaker for {tool_name} entering half-open state")
                    return True, None
            return False, f"Service {tool_name} is temporarily unavailable (circuit open)"

        if cb.state == CircuitState.HALF_OPEN:
            if cb.success_count >= cb.half_open_max_calls:
                # Allow limited requests in half-open state
                return False, f"Service {tool_name} is recovering, please retry"
            return True, None

        return True, None

    def _record_circuit_result(self, tool_name: str, success: bool) -> None:
        """Record the result of a tool call for circuit breaker."""
        cb = self._get_circuit_breaker(tool_name)

        if success:
            if cb.state == CircuitState.HALF_OPEN:
                cb.success_count += 1
                if cb.success_count >= cb.half_open_max_calls:
                    cb.state = CircuitState.CLOSED
                    cb.failure_count = 0
                    logger.info(f"Circuit breaker for {tool_name} closed (service recovered)")
            else:
                cb.failure_count = 0
        else:
            cb.failure_count += 1
            cb.last_failure_time = datetime.utcnow()

            if cb.state == CircuitState.HALF_OPEN:
                cb.state = CircuitState.OPEN
                logger.warning(f"Circuit breaker for {tool_name} reopened after failure in half-open")
            elif cb.failure_count >= cb.failure_threshold:
                cb.state = CircuitState.OPEN
                logger.warning(f"Circuit breaker for {tool_name} opened after {cb.failure_count} failures")

    def _generate_request_id(self, user_id: str, tool_name: str, arguments: dict) -> str:
        """Generate a unique request ID."""
        content = f"{user_id}:{tool_name}:{json.dumps(arguments, sort_keys=True)}:{time.time()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    async def _log_audit(
        self,
        user_id: str,
        tool_name: str,
        action: str,
        arguments: dict[str, Any],
        context: dict[str, Any],
        result: Optional[dict[str, Any]] = None,
        error: Optional[str] = None,
        duration_ms: Optional[float] = None,
        approval_id: Optional[str] = None,
    ) -> AuditLogEntry:
        """Log an audit entry."""
        policy = self.get_tool_policy(tool_name)

        # Redact sensitive arguments if needed
        logged_arguments = arguments
        if policy.sensitive:
            logged_arguments = self._redact_sensitive_data(arguments)

        entry = AuditLogEntry(
            entry_id=self._generate_request_id(user_id, tool_name, {"action": action}),
            timestamp=datetime.utcnow(),
            user_id=user_id,
            organization_id=context.get("organization_id"),
            tool_name=tool_name,
            action=action,
            arguments=logged_arguments,
            result=result if policy.audit_level == "verbose" else None,
            error=error,
            duration_ms=duration_ms,
            approval_id=approval_id,
            ip_address=context.get("ip_address"),
            user_agent=context.get("user_agent"),
            metadata={
                "audit_level": policy.audit_level,
                "sensitive": policy.sensitive,
            },
        )

        async with self._audit_lock:
            self._audit_log.append(entry)
            # Keep only last 10000 entries in memory
            if len(self._audit_log) > 10000:
                self._audit_log = self._audit_log[-10000:]

        # Persist to database if audit service is available
        audit_service = self._get_audit_service()
        if audit_service:
            try:
                # Map action to audit event type
                action_map = {
                    "invoke": "tool_invocation",
                    "complete": "tool_success",
                    "error": "tool_failure",
                    "rate_limited": "rate_limit_exceeded",
                    "permission_denied": "permission_denied",
                    "approval_requested": "approval_requested",
                    "approved": "approval_granted",
                    "rejected": "approval_denied",
                    "circuit_open": "circuit_breaker_open",
                }
                event_type = action_map.get(action, action)

                if action == "complete":
                    await audit_service.log_tool_success(
                        tool_name=tool_name,
                        service_name=self._get_service_for_tool(tool_name),
                        duration_ms=duration_ms or 0,
                        user_id=user_id if user_id != "anonymous" else None,
                        organization_id=context.get("organization_id"),
                        output_summary=str(result)[:1000] if result else None,
                        request_id=entry.entry_id,
                        metadata=entry.metadata,
                    )
                elif action == "error":
                    await audit_service.log_tool_failure(
                        tool_name=tool_name,
                        service_name=self._get_service_for_tool(tool_name),
                        error_message=error or "Unknown error",
                        duration_ms=duration_ms,
                        user_id=user_id if user_id != "anonymous" else None,
                        organization_id=context.get("organization_id"),
                        input_params=logged_arguments,
                        request_id=entry.entry_id,
                        metadata=entry.metadata,
                    )
                elif action == "rate_limited":
                    await audit_service.log_rate_limit_exceeded(
                        tool_name=tool_name,
                        user_id=user_id if user_id != "anonymous" else None,
                        organization_id=context.get("organization_id"),
                        metadata=entry.metadata,
                    )
                elif action == "permission_denied":
                    await audit_service.log_permission_denied(
                        tool_name=tool_name,
                        user_id=user_id if user_id != "anonymous" else None,
                        organization_id=context.get("organization_id"),
                        reason=error,
                        metadata=entry.metadata,
                    )
                else:
                    # Generic tool invocation
                    await audit_service.log_tool_invocation(
                        tool_name=tool_name,
                        service_name=self._get_service_for_tool(tool_name),
                        user_id=user_id if user_id != "anonymous" else None,
                        organization_id=context.get("organization_id"),
                        input_params=logged_arguments,
                        request_id=entry.entry_id,
                        session_id=context.get("session_id"),
                        ip_address=context.get("ip_address"),
                        conversation_id=context.get("conversation_id"),
                        metadata=entry.metadata,
                    )
            except Exception as e:
                logger.error(f"Failed to persist audit log to database: {e}")

        # Call external audit callback if provided
        if self.audit_callback:
            try:
                self.audit_callback(entry)
            except Exception as e:
                logger.error(f"Audit callback failed: {e}")

        return entry

    def _get_service_for_tool(self, tool_name: str) -> str:
        """Determine the service name for a tool based on naming convention."""
        # Tool names follow pattern: service_action (e.g., devlake_get_dora_metrics)
        parts = tool_name.split("_")
        if len(parts) >= 2:
            return parts[0]
        return "unknown"

    def _redact_sensitive_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Redact sensitive fields from data."""
        sensitive_keys = {"token", "password", "secret", "key", "credential", "auth", "api_key"}
        redacted = {}

        for key, value in data.items():
            if any(s in key.lower() for s in sensitive_keys):
                redacted[key] = "[REDACTED]"
            elif isinstance(value, dict):
                redacted[key] = self._redact_sensitive_data(value)
            elif isinstance(value, str) and len(value) > 20:
                # Redact long strings that might be tokens
                if any(s in key.lower() for s in sensitive_keys):
                    redacted[key] = "[REDACTED]"
                else:
                    redacted[key] = value
            else:
                redacted[key] = value

        return redacted

    async def check_permission(
        self,
        user_id: str,
        tool_name: str,
        context: dict[str, Any],
    ) -> tuple[bool, Optional[str]]:
        """Check if user has permission to use a tool."""
        policy = self.get_tool_policy(tool_name)

        if not policy.enabled:
            return False, f"Tool {tool_name} is disabled"

        user_roles = context.get("roles", ["user"])

        # First check role-based policy
        if not any(role in policy.allowed_roles for role in user_roles):
            return False, f"User does not have required role for {tool_name}"

        # Then check fine-grained permissions via permission checker
        organization_id = context.get("organization_id")
        resource_context = context.get("resource_context")

        has_permission, error = self._permission_checker.check_permission(
            user_id=user_id,
            tool_name=tool_name,
            roles=user_roles,
            organization_id=organization_id,
            resource_context=resource_context,
        )

        if not has_permission:
            return False, error

        return True, None

    async def request_approval(
        self,
        user_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any],
    ) -> ApprovalRequest:
        """Create an approval request for a sensitive tool invocation."""
        policy = self.get_tool_policy(tool_name)

        request = ApprovalRequest(
            request_id=self._generate_request_id(user_id, tool_name, arguments),
            tool_name=tool_name,
            user_id=user_id,
            arguments=arguments,
            context=context,
            expires_at=datetime.utcnow() + timedelta(seconds=policy.approval_timeout_seconds),
        )

        self._pending_approvals[request.request_id] = request

        await self._log_audit(
            user_id=user_id,
            tool_name=tool_name,
            action="approval_requested",
            arguments=arguments,
            context=context,
            approval_id=request.request_id,
        )

        logger.info(f"Approval requested for {tool_name} by {user_id}: {request.request_id}")
        return request

    async def approve_request(
        self,
        request_id: str,
        approver_id: str,
    ) -> tuple[bool, Optional[str]]:
        """Approve a pending request."""
        request = self._pending_approvals.get(request_id)
        if not request:
            return False, "Approval request not found"

        if request.status != ApprovalStatus.PENDING:
            return False, f"Request already {request.status.value}"

        if request.expires_at and datetime.utcnow() > request.expires_at:
            request.status = ApprovalStatus.EXPIRED
            return False, "Approval request has expired"

        request.status = ApprovalStatus.APPROVED
        request.approved_by = approver_id

        await self._log_audit(
            user_id=approver_id,
            tool_name=request.tool_name,
            action="approved",
            arguments=request.arguments,
            context=request.context,
            approval_id=request_id,
        )

        logger.info(f"Request {request_id} approved by {approver_id}")
        return True, None

    async def reject_request(
        self,
        request_id: str,
        rejector_id: str,
        reason: Optional[str] = None,
    ) -> tuple[bool, Optional[str]]:
        """Reject a pending request."""
        request = self._pending_approvals.get(request_id)
        if not request:
            return False, "Approval request not found"

        if request.status != ApprovalStatus.PENDING:
            return False, f"Request already {request.status.value}"

        request.status = ApprovalStatus.REJECTED
        request.rejection_reason = reason

        await self._log_audit(
            user_id=rejector_id,
            tool_name=request.tool_name,
            action="rejected",
            arguments=request.arguments,
            context=request.context,
            approval_id=request_id,
            error=reason,
        )

        logger.info(f"Request {request_id} rejected by {rejector_id}: {reason}")
        return True, None

    async def invoke_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Invoke a tool through the gateway with all checks and logging.

        This is the main entry point for tool invocations.
        """
        user_id = context.get("user_id", "anonymous")
        start_time = time.time()

        # Check if tool exists
        if tool_name not in self.mcp_server._tools:
            error_msg = f"Tool {tool_name} not found"
            await self._log_audit(
                user_id=user_id,
                tool_name=tool_name,
                action="error",
                arguments=arguments,
                context=context,
                error=error_msg,
            )
            return {
                "success": False,
                "error": {"category": "not_found", "message": error_msg},
            }

        policy = self.get_tool_policy(tool_name)

        # Check circuit breaker
        cb_allowed, cb_error = self._check_circuit_breaker(tool_name)
        if not cb_allowed:
            await self._log_audit(
                user_id=user_id,
                tool_name=tool_name,
                action="circuit_open",
                arguments=arguments,
                context=context,
                error=cb_error,
            )
            return {
                "success": False,
                "error": {"category": "service_unavailable", "message": cb_error},
                "retry": {"retryable": True, "retry_after_seconds": 30},
            }

        # Check rate limit
        rate_limiter = self._get_user_rate_limiter(user_id, tool_name)
        allowed, rate_error = await rate_limiter.check_and_consume(user_id)
        if not allowed:
            await self._log_audit(
                user_id=user_id,
                tool_name=tool_name,
                action="rate_limited",
                arguments=arguments,
                context=context,
                error=rate_error,
            )
            remaining = rate_limiter.get_remaining(user_id)
            return rate_limit_error(
                limit_type="user",
                retry_after=60,
                details={"remaining": remaining},
            ).to_dict()

        # Check permission
        has_permission, perm_error = await self.check_permission(user_id, tool_name, context)
        if not has_permission:
            await self._log_audit(
                user_id=user_id,
                tool_name=tool_name,
                action="permission_denied",
                arguments=arguments,
                context=context,
                error=perm_error,
            )
            return {
                "success": False,
                "error": {"category": "permission_denied", "message": perm_error},
            }

        # Check if approval is required
        if policy.requires_approval:
            # Check if there's an approved request for this invocation
            approval_id = context.get("approval_id")
            if approval_id:
                request = self._pending_approvals.get(approval_id)
                if not request or request.status != ApprovalStatus.APPROVED:
                    return {
                        "success": False,
                        "error": {"category": "approval_required", "message": "Approval not found or not approved"},
                    }
            else:
                # Create approval request
                approval_request = await self.request_approval(user_id, tool_name, arguments, context)
                return {
                    "success": False,
                    "approval_required": True,
                    "approval_id": approval_request.request_id,
                    "expires_at": approval_request.expires_at.isoformat() if approval_request.expires_at else None,
                    "message": f"This action requires approval. Request ID: {approval_request.request_id}",
                }

        # Log invocation
        await self._log_audit(
            user_id=user_id,
            tool_name=tool_name,
            action="invoke",
            arguments=arguments,
            context=context,
        )

        # Execute the tool
        try:
            handler = self.mcp_server._tools[tool_name]
            result = await handler.execute(arguments, context)

            duration_ms = (time.time() - start_time) * 1000
            self._record_circuit_result(tool_name, True)

            await self._log_audit(
                user_id=user_id,
                tool_name=tool_name,
                action="complete",
                arguments=arguments,
                context=context,
                result=result if isinstance(result, dict) else {"result": str(result)},
                duration_ms=duration_ms,
            )

            return {
                "success": True,
                "result": result,
                "duration_ms": duration_ms,
            }

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._record_circuit_result(tool_name, False)

            error_msg = str(e)
            await self._log_audit(
                user_id=user_id,
                tool_name=tool_name,
                action="error",
                arguments=arguments,
                context=context,
                error=error_msg,
                duration_ms=duration_ms,
            )

            logger.error(f"Tool {tool_name} execution failed: {error_msg}")
            return internal_error(
                operation=f"execute {tool_name}",
                error_message=error_msg,
            ).to_dict()

    def get_pending_approvals(self, user_id: Optional[str] = None) -> list[ApprovalRequest]:
        """Get pending approval requests, optionally filtered by user."""
        now = datetime.utcnow()
        pending = []

        for request in self._pending_approvals.values():
            # Check for expiration
            if request.expires_at and now > request.expires_at:
                request.status = ApprovalStatus.EXPIRED
                continue

            if request.status == ApprovalStatus.PENDING:
                if user_id is None or request.user_id == user_id:
                    pending.append(request)

        return pending

    def get_audit_log(
        self,
        user_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        action: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[AuditLogEntry]:
        """Query the audit log with filters."""
        results = []

        for entry in reversed(self._audit_log):
            if user_id and entry.user_id != user_id:
                continue
            if tool_name and entry.tool_name != tool_name:
                continue
            if action and entry.action != action:
                continue
            if since and entry.timestamp < since:
                continue

            results.append(entry)
            if len(results) >= limit:
                break

        return results

    def get_circuit_breaker_status(self) -> dict[str, dict[str, Any]]:
        """Get status of all circuit breakers."""
        return {
            name: {
                "state": cb.state.value,
                "failure_count": cb.failure_count,
                "last_failure": cb.last_failure_time.isoformat() if cb.last_failure_time else None,
            }
            for name, cb in self._circuit_breakers.items()
        }

    def get_rate_limit_status(self, user_id: str) -> dict[str, Any]:
        """Get rate limit status for a user."""
        limiter = self._user_rate_limiters.get(user_id)
        if not limiter:
            return {"remaining": self.default_rate_limit.__dict__}
        return {"remaining": limiter.get_remaining(user_id)}


# Singleton gateway instance
_mcp_gateway: Optional[MCPGateway] = None


def get_mcp_gateway(mcp_server: Optional[MCPServer] = None) -> MCPGateway:
    """Get or create the global MCP gateway instance."""
    global _mcp_gateway
    if _mcp_gateway is None:
        if mcp_server is None:
            from .setup import get_mcp_server
            mcp_server = get_mcp_server()
        _mcp_gateway = MCPGateway(mcp_server)
    return _mcp_gateway


def reset_mcp_gateway() -> None:
    """Reset the global MCP gateway instance."""
    global _mcp_gateway
    _mcp_gateway = None
