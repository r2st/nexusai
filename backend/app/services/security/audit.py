"""Audit Logging Service.

Provides:
- Security event logging
- Action audit trails
- Compliance logging
- Forensic capabilities
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any
from uuid import uuid4

import structlog

logger = structlog.get_logger()


class AuditEventType(str, Enum):
    """Types of audit events."""

    # Authentication events
    LOGIN_SUCCESS = "auth.login.success"
    LOGIN_FAILURE = "auth.login.failure"
    LOGOUT = "auth.logout"
    PASSWORD_CHANGE = "auth.password.change"
    PASSWORD_RESET = "auth.password.reset"
    MFA_ENABLED = "auth.mfa.enabled"
    MFA_DISABLED = "auth.mfa.disabled"
    TOKEN_CREATED = "auth.token.created"
    TOKEN_REVOKED = "auth.token.revoked"

    # Authorization events
    PERMISSION_GRANTED = "authz.permission.granted"
    PERMISSION_DENIED = "authz.permission.denied"
    ROLE_ASSIGNED = "authz.role.assigned"
    ROLE_REMOVED = "authz.role.removed"

    # Data access events
    DATA_READ = "data.read"
    DATA_CREATED = "data.created"
    DATA_UPDATED = "data.updated"
    DATA_DELETED = "data.deleted"
    DATA_EXPORTED = "data.exported"

    # Agent events
    AGENT_EXECUTED = "agent.executed"
    TOOL_EXECUTED = "tool.executed"
    AGENT_CREATED = "agent.created"
    AGENT_MODIFIED = "agent.modified"

    # DevLake events
    CONNECTION_CREATED = "devlake.connection.created"
    CONNECTION_DELETED = "devlake.connection.deleted"
    BLUEPRINT_CREATED = "devlake.blueprint.created"
    PIPELINE_EXECUTED = "devlake.pipeline.executed"

    # Organization events
    ORG_CREATED = "org.created"
    ORG_UPDATED = "org.updated"
    ORG_DELETED = "org.deleted"
    MEMBER_INVITED = "org.member.invited"
    MEMBER_REMOVED = "org.member.removed"

    # Security events
    RATE_LIMIT_EXCEEDED = "security.ratelimit.exceeded"
    SUSPICIOUS_ACTIVITY = "security.suspicious"
    INJECTION_ATTEMPT = "security.injection"
    CROSS_TENANT_ATTEMPT = "security.cross_tenant"

    # System events
    CONFIG_CHANGED = "system.config.changed"
    INTEGRATION_ERROR = "system.integration.error"
    BACKUP_CREATED = "system.backup.created"


class AuditSeverity(str, Enum):
    """Severity levels for audit events."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """An audit event record."""

    event_type: AuditEventType
    timestamp: datetime
    tenant_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    action: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    severity: AuditSeverity = AuditSeverity.INFO
    ip_address: str | None = None
    user_agent: str | None = None
    success: bool = True
    error_message: str | None = None

    # Generated fields
    event_id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "action": self.action,
            "details": self.details,
            "severity": self.severity.value,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "success": self.success,
            "error_message": self.error_message,
        }


class AuditLogger:
    """
    Audit logging service for security and compliance.

    Provides:
    - Structured audit event logging
    - Severity-based filtering
    - Multiple output destinations
    - Query capabilities
    """

    def __init__(
        self,
        log_to_db: bool = True,
        log_to_file: bool = False,
        min_severity: AuditSeverity = AuditSeverity.INFO,
    ):
        """
        Initialize audit logger.

        Args:
            log_to_db: Whether to log to database
            log_to_file: Whether to log to file
            min_severity: Minimum severity to log
        """
        self.log_to_db = log_to_db
        self.log_to_file = log_to_file
        self.min_severity = min_severity

        # In-memory buffer for batch writes
        self._buffer: list[AuditEvent] = []
        self._buffer_size = 100

        # Severity ordering for filtering
        self._severity_order = {
            AuditSeverity.DEBUG: 0,
            AuditSeverity.INFO: 1,
            AuditSeverity.WARNING: 2,
            AuditSeverity.ERROR: 3,
            AuditSeverity.CRITICAL: 4,
        }

    def _should_log(self, severity: AuditSeverity) -> bool:
        """Check if event should be logged based on severity."""
        return self._severity_order[severity] >= self._severity_order[self.min_severity]

    async def log(self, event: AuditEvent) -> None:
        """
        Log an audit event.

        Args:
            event: The audit event to log
        """
        if not self._should_log(event.severity):
            return

        # Add to buffer
        self._buffer.append(event)

        # Log to structlog
        log_method = getattr(logger, event.severity.value)
        log_method(
            event.event_type.value,
            event_id=event.event_id,
            tenant_id=event.tenant_id,
            user_id=event.user_id,
            resource_type=event.resource_type,
            resource_id=event.resource_id,
            success=event.success,
            **event.details,
        )

        # Flush if buffer is full
        if len(self._buffer) >= self._buffer_size:
            await self.flush()

    async def log_auth_event(
        self,
        event_type: AuditEventType,
        user_id: str,
        tenant_id: str | None = None,
        success: bool = True,
        ip_address: str | None = None,
        user_agent: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Log an authentication event."""
        severity = AuditSeverity.INFO if success else AuditSeverity.WARNING

        await self.log(AuditEvent(
            event_type=event_type,
            timestamp=datetime.now(UTC),
            tenant_id=tenant_id,
            user_id=user_id,
            severity=severity,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            details=details or {},
        ))

    async def log_data_access(
        self,
        event_type: AuditEventType,
        tenant_id: str,
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str | None = None,
        success: bool = True,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Log a data access event."""
        await self.log(AuditEvent(
            event_type=event_type,
            timestamp=datetime.now(UTC),
            tenant_id=tenant_id,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            severity=AuditSeverity.INFO,
            success=success,
            details=details or {},
        ))

    async def log_security_event(
        self,
        event_type: AuditEventType,
        tenant_id: str | None = None,
        user_id: str | None = None,
        ip_address: str | None = None,
        details: dict[str, Any] | None = None,
        severity: AuditSeverity = AuditSeverity.WARNING,
    ) -> None:
        """Log a security event."""
        await self.log(AuditEvent(
            event_type=event_type,
            timestamp=datetime.now(UTC),
            tenant_id=tenant_id,
            user_id=user_id,
            ip_address=ip_address,
            severity=severity,
            success=False,
            details=details or {},
        ))

    async def log_agent_execution(
        self,
        tenant_id: str,
        user_id: str,
        agent_id: str,
        agent_type: str,
        input_summary: str,
        output_summary: str,
        tools_used: list[str] | None = None,
        success: bool = True,
        execution_time_ms: float = 0,
    ) -> None:
        """Log an agent execution event."""
        await self.log(AuditEvent(
            event_type=AuditEventType.AGENT_EXECUTED,
            timestamp=datetime.now(UTC),
            tenant_id=tenant_id,
            user_id=user_id,
            resource_type="agent",
            resource_id=agent_id,
            action="execute",
            severity=AuditSeverity.INFO,
            success=success,
            details={
                "agent_type": agent_type,
                "input_summary": input_summary[:500],  # Truncate
                "output_summary": output_summary[:500],
                "tools_used": tools_used or [],
                "execution_time_ms": execution_time_ms,
            },
        ))

    async def log_tool_execution(
        self,
        tenant_id: str,
        user_id: str,
        tool_name: str,
        parameters: dict[str, Any],
        success: bool = True,
        required_confirmation: bool = False,
        execution_time_ms: float = 0,
    ) -> None:
        """Log a tool execution event."""
        # Redact sensitive parameters
        safe_params = self._redact_sensitive(parameters)

        await self.log(AuditEvent(
            event_type=AuditEventType.TOOL_EXECUTED,
            timestamp=datetime.now(UTC),
            tenant_id=tenant_id,
            user_id=user_id,
            resource_type="tool",
            resource_id=tool_name,
            action="execute",
            severity=AuditSeverity.INFO,
            success=success,
            details={
                "parameters": safe_params,
                "required_confirmation": required_confirmation,
                "execution_time_ms": execution_time_ms,
            },
        ))

    def _redact_sensitive(self, data: dict[str, Any]) -> dict[str, Any]:
        """Redact sensitive values from data."""
        sensitive_keys = {
            "password", "secret", "token", "api_key", "apikey",
            "credential", "auth", "key", "private",
        }

        result = {}
        for key, value in data.items():
            key_lower = key.lower()
            if any(s in key_lower for s in sensitive_keys):
                result[key] = "[REDACTED]"
            elif isinstance(value, dict):
                result[key] = self._redact_sensitive(value)
            else:
                result[key] = value

        return result

    async def flush(self) -> None:
        """Flush buffered events to storage."""
        if not self._buffer:
            return

        events_to_flush = self._buffer.copy()
        self._buffer.clear()

        if self.log_to_db:
            await self._flush_to_db(events_to_flush)

        if self.log_to_file:
            await self._flush_to_file(events_to_flush)

        logger.debug(f"Flushed {len(events_to_flush)} audit events")

    async def _flush_to_db(self, events: list[AuditEvent]) -> None:
        """Flush events to database."""
        # This would insert into audit_logs table
        # For now, we just log (actual DB integration would go here)
        pass

    async def _flush_to_file(self, events: list[AuditEvent]) -> None:
        """Flush events to file."""
        # This would append to audit log file
        # For now, we just log (actual file integration would go here)
        pass

    async def query(
        self,
        tenant_id: str | None = None,
        user_id: str | None = None,
        event_types: list[AuditEventType] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        min_severity: AuditSeverity = AuditSeverity.INFO,
        limit: int = 100,
    ) -> list[AuditEvent]:
        """
        Query audit events.

        Args:
            tenant_id: Filter by tenant
            user_id: Filter by user
            event_types: Filter by event types
            start_time: Filter by start time
            end_time: Filter by end time
            min_severity: Minimum severity
            limit: Maximum events to return

        Returns:
            List of matching audit events
        """
        # This would query from database
        # For now, return from buffer
        results = []

        for event in reversed(self._buffer):
            if tenant_id and event.tenant_id != tenant_id:
                continue
            if user_id and event.user_id != user_id:
                continue
            if event_types and event.event_type not in event_types:
                continue
            if start_time and event.timestamp < start_time:
                continue
            if end_time and event.timestamp > end_time:
                continue
            if self._severity_order[event.severity] < self._severity_order[min_severity]:
                continue

            results.append(event)

            if len(results) >= limit:
                break

        return results

    async def get_recent_security_events(
        self,
        tenant_id: str,
        limit: int = 20,
    ) -> list[AuditEvent]:
        """Get recent security-related events for a tenant."""
        security_types = [
            AuditEventType.LOGIN_FAILURE,
            AuditEventType.PERMISSION_DENIED,
            AuditEventType.RATE_LIMIT_EXCEEDED,
            AuditEventType.SUSPICIOUS_ACTIVITY,
            AuditEventType.INJECTION_ATTEMPT,
            AuditEventType.CROSS_TENANT_ATTEMPT,
        ]

        return await self.query(
            tenant_id=tenant_id,
            event_types=security_types,
            min_severity=AuditSeverity.WARNING,
            limit=limit,
        )

    async def get_user_activity(
        self,
        tenant_id: str,
        user_id: str,
        start_time: datetime | None = None,
        limit: int = 50,
    ) -> list[AuditEvent]:
        """Get activity log for a specific user."""
        return await self.query(
            tenant_id=tenant_id,
            user_id=user_id,
            start_time=start_time,
            limit=limit,
        )


# Singleton instance
audit_logger = AuditLogger()
