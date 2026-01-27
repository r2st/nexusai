"""Audit log model for tracking MCP tool invocations and security events."""

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuditEventType(str, Enum):
    """Types of audit events."""

    TOOL_INVOCATION = "tool_invocation"
    TOOL_SUCCESS = "tool_success"
    TOOL_FAILURE = "tool_failure"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_DENIED = "approval_denied"
    APPROVAL_EXPIRED = "approval_expired"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    PERMISSION_DENIED = "permission_denied"
    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"
    CIRCUIT_BREAKER_CLOSED = "circuit_breaker_closed"
    DATA_REDACTION = "data_redaction"
    SENSITIVE_DATA_ACCESS = "sensitive_data_access"
    AUTHENTICATION_FAILURE = "authentication_failure"
    CONFIGURATION_CHANGE = "configuration_change"


class AuditSeverity(str, Enum):
    """Severity levels for audit events."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditLog(Base):
    """Audit log for tracking all MCP tool invocations and security events."""

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Event identification
    event_type: Mapped[str] = mapped_column(
        String(50),
        index=True,
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(
        String(20),
        default=AuditSeverity.INFO.value,
        index=True,
    )

    # Actor information
    user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        index=True,
        nullable=True,
    )
    organization_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        index=True,
        nullable=True,
    )
    session_id: Mapped[str | None] = mapped_column(
        String(255),
        index=True,
        nullable=True,
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(45),  # IPv6 max length
        nullable=True,
    )
    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Tool information
    tool_name: Mapped[str | None] = mapped_column(
        String(255),
        index=True,
        nullable=True,
    )
    service_name: Mapped[str | None] = mapped_column(
        String(100),
        index=True,
        nullable=True,
    )
    tool_category: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # Request/Response
    request_id: Mapped[str | None] = mapped_column(
        String(255),
        index=True,
        nullable=True,
    )
    input_params: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    output_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    error_code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # Performance
    duration_ms: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    tokens_used: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Status
    success: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )
    was_cached: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )
    required_approval: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )
    approval_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
    )

    # Context
    conversation_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
    )
    message_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
    )

    # Additional metadata
    extra_metadata: Mapped[dict | None] = mapped_column(
        "metadata",  # Keep the column name in DB for backwards compatibility
        JSONB,
        nullable=True,
    )
    tags: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Timestamps
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        # Composite indexes for common queries
        Index("ix_audit_logs_user_timestamp", "user_id", "timestamp"),
        Index("ix_audit_logs_org_timestamp", "organization_id", "timestamp"),
        Index("ix_audit_logs_tool_timestamp", "tool_name", "timestamp"),
        Index("ix_audit_logs_service_timestamp", "service_name", "timestamp"),
        Index("ix_audit_logs_event_severity", "event_type", "severity"),
        # Partial index for failures only
        Index(
            "ix_audit_logs_failures",
            "timestamp",
            "tool_name",
            postgresql_where="success = false",
        ),
    )

    def __repr__(self) -> str:
        return f"<AuditLog {self.event_type} {self.tool_name} at {self.timestamp}>"


class ApprovalRecord(Base):
    """Records of approval requests for sensitive tool operations."""

    __tablename__ = "approval_records"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Request details
    tool_name: Mapped[str] = mapped_column(
        String(255),
        index=True,
        nullable=False,
    )
    service_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    input_params: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Requester
    requester_user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        index=True,
        nullable=False,
    )
    requester_organization_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
    )

    # Approver
    approver_user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
    )
    approver_comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        index=True,
    )  # pending, approved, denied, expired, cancelled

    # Timing
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Metadata
    extra_metadata: Mapped[dict | None] = mapped_column(
        "metadata",  # Keep the column name in DB for backwards compatibility
        JSONB,
        nullable=True,
    )

    __table_args__ = (
        Index("ix_approval_records_requester_status", "requester_user_id", "status"),
        Index("ix_approval_records_pending", "status", "expires_at"),
    )

    def __repr__(self) -> str:
        return f"<ApprovalRecord {self.tool_name} {self.status}>"
