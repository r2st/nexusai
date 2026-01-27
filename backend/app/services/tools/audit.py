"""
Tool Audit Logging

Complete audit trail for all tool executions.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import json
import hashlib
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Column, String, Text, DateTime, Integer, Float, Boolean, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base

from .base import ToolResult, ToolResultStatus, ExecutionContext

logger = logging.getLogger(__name__)

Base = declarative_base()


class AuditEventType(str, Enum):
    """Types of audit events."""
    TOOL_CALLED = "tool_called"
    TOOL_SUCCESS = "tool_success"
    TOOL_ERROR = "tool_error"
    TOOL_TIMEOUT = "tool_timeout"
    PERMISSION_DENIED = "permission_denied"
    RATE_LIMITED = "rate_limited"
    VALIDATION_ERROR = "validation_error"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_DENIED = "approval_denied"


@dataclass
class AuditEntry:
    """A single audit log entry."""
    
    # Identity
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # Event details
    event_type: AuditEventType = AuditEventType.TOOL_CALLED
    tool_name: str = ""
    
    # Context
    tenant_id: str = ""
    user_id: str = ""
    organization_id: Optional[str] = None
    session_id: Optional[str] = None
    conversation_id: Optional[str] = None
    request_id: Optional[str] = None
    
    # Execution details
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # Input/Output (may be redacted)
    input_params: Dict[str, Any] = field(default_factory=dict)
    input_hash: Optional[str] = None  # Hash of original input
    output_data: Optional[Any] = None
    output_redacted: bool = False
    
    # Result
    status: str = "pending"
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    
    # Metrics
    duration_ms: Optional[int] = None
    tokens_used: int = 0
    cost_incurred: float = 0.0
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    # Source
    source: str = "api"
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Approval workflow
    requires_approval: bool = False
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["event_type"] = self.event_type.value
        data["created_at"] = self.created_at.isoformat()
        if self.completed_at:
            data["completed_at"] = self.completed_at.isoformat()
        if self.approved_at:
            data["approved_at"] = self.approved_at.isoformat()
        return data
    
    @staticmethod
    def hash_params(params: Dict[str, Any]) -> str:
        """Create a hash of parameters for integrity checking."""
        content = json.dumps(params, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()


class ToolAuditLog(Base):
    """SQLAlchemy model for tool audit logs."""
    
    __tablename__ = "tool_audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Event
    event_type = Column(String(50), nullable=False, index=True)
    tool_name = Column(String(100), nullable=False, index=True)
    
    # Context
    tenant_id = Column(String(50), nullable=False, index=True)
    user_id = Column(String(50), nullable=False, index=True)
    organization_id = Column(String(50), nullable=True, index=True)
    session_id = Column(String(50), nullable=True)
    conversation_id = Column(String(50), nullable=True, index=True)
    request_id = Column(String(50), nullable=True)
    execution_id = Column(String(50), nullable=False, index=True)
    
    # Input/Output
    input_params = Column(JSON, nullable=True)
    input_hash = Column(String(64), nullable=True)
    output_data = Column(JSON, nullable=True)
    output_redacted = Column(Boolean, default=False)
    
    # Result
    status = Column(String(20), nullable=False, index=True)
    error_message = Column(Text, nullable=True)
    error_code = Column(String(50), nullable=True)
    
    # Metrics
    duration_ms = Column(Integer, nullable=True)
    tokens_used = Column(Integer, default=0)
    cost_incurred = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Source
    source = Column(String(20), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Approval
    requires_approval = Column(Boolean, default=False)
    approved_by = Column(String(50), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index("ix_audit_tenant_created", "tenant_id", "created_at"),
        Index("ix_audit_user_tool", "user_id", "tool_name"),
        Index("ix_audit_org_tool", "organization_id", "tool_name"),
    )


class ToolAuditLogger:
    """
    Handles audit logging for tool executions.
    
    Features:
    - Full execution trace logging
    - Input/output capture (with optional redaction)
    - Metrics tracking
    - Async database persistence
    - Query interface for audit logs
    """
    
    def __init__(
        self,
        db_session: Optional[AsyncSession] = None,
        redact_sensitive: bool = True,
        log_outputs: bool = True,
    ):
        self.db_session = db_session
        self.redact_sensitive = redact_sensitive
        self.log_outputs = log_outputs
        
        # Patterns for sensitive data
        self._sensitive_keys = {
            "password", "secret", "token", "api_key", "apikey",
            "credential", "private_key", "auth", "bearer",
        }
    
    async def log_call(
        self,
        tool_name: str,
        params: Dict[str, Any],
        context: ExecutionContext,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditEntry:
        """Log a tool call (before execution)."""
        
        # Redact sensitive params if needed
        logged_params = self._redact_params(params) if self.redact_sensitive else params
        
        entry = AuditEntry(
            event_type=AuditEventType.TOOL_CALLED,
            tool_name=tool_name,
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            organization_id=context.organization_id,
            session_id=context.session_id,
            conversation_id=context.conversation_id,
            request_id=context.request_id,
            input_params=logged_params,
            input_hash=AuditEntry.hash_params(params),
            source=context.source,
            ip_address=ip_address,
            user_agent=user_agent,
            status="pending",
        )
        
        await self._persist(entry)
        logger.info(f"Audit: Tool call initiated - {tool_name} by user {context.user_id}")
        
        return entry
    
    async def log_result(
        self,
        entry: AuditEntry,
        result: ToolResult,
    ) -> AuditEntry:
        """Log the result of a tool execution."""
        
        # Update entry with result
        entry.completed_at = datetime.utcnow()
        entry.status = result.status.value
        entry.duration_ms = result.duration_ms
        entry.tokens_used = result.tokens_used
        entry.cost_incurred = result.cost_incurred
        
        # Map result status to event type
        status_to_event = {
            ToolResultStatus.SUCCESS: AuditEventType.TOOL_SUCCESS,
            ToolResultStatus.ERROR: AuditEventType.TOOL_ERROR,
            ToolResultStatus.TIMEOUT: AuditEventType.TOOL_TIMEOUT,
            ToolResultStatus.RATE_LIMITED: AuditEventType.RATE_LIMITED,
            ToolResultStatus.PERMISSION_DENIED: AuditEventType.PERMISSION_DENIED,
            ToolResultStatus.VALIDATION_ERROR: AuditEventType.VALIDATION_ERROR,
            ToolResultStatus.PENDING_APPROVAL: AuditEventType.APPROVAL_REQUESTED,
        }
        entry.event_type = status_to_event.get(result.status, AuditEventType.TOOL_ERROR)
        
        if result.error:
            entry.error_message = result.error
            entry.error_code = result.error_code
        
        if self.log_outputs and result.data is not None:
            entry.output_data = self._redact_output(result.data) if self.redact_sensitive else result.data
            entry.output_redacted = self.redact_sensitive
        
        await self._persist(entry)
        
        log_level = logging.INFO if result.status == ToolResultStatus.SUCCESS else logging.WARNING
        logger.log(
            log_level,
            f"Audit: Tool execution completed - {entry.tool_name} "
            f"status={result.status.value} duration={result.duration_ms}ms"
        )
        
        return entry
    
    async def log_permission_denied(
        self,
        tool_name: str,
        context: ExecutionContext,
        reason: str,
    ) -> AuditEntry:
        """Log a permission denied event."""
        
        entry = AuditEntry(
            event_type=AuditEventType.PERMISSION_DENIED,
            tool_name=tool_name,
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            organization_id=context.organization_id,
            session_id=context.session_id,
            request_id=context.request_id,
            status="denied",
            error_message=reason,
            completed_at=datetime.utcnow(),
        )
        
        await self._persist(entry)
        logger.warning(f"Audit: Permission denied - {tool_name} for user {context.user_id}: {reason}")
        
        return entry
    
    async def log_rate_limited(
        self,
        tool_name: str,
        context: ExecutionContext,
        limit_type: str,
    ) -> AuditEntry:
        """Log a rate limit event."""
        
        entry = AuditEntry(
            event_type=AuditEventType.RATE_LIMITED,
            tool_name=tool_name,
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            organization_id=context.organization_id,
            status="rate_limited",
            error_message=f"Rate limit exceeded: {limit_type}",
            completed_at=datetime.utcnow(),
        )
        
        await self._persist(entry)
        logger.warning(f"Audit: Rate limited - {tool_name} for user {context.user_id}")
        
        return entry
    
    async def log_approval(
        self,
        entry: AuditEntry,
        approved: bool,
        approved_by: str,
    ) -> AuditEntry:
        """Log an approval decision."""
        
        entry.event_type = AuditEventType.APPROVAL_GRANTED if approved else AuditEventType.APPROVAL_DENIED
        entry.approved_by = approved_by
        entry.approved_at = datetime.utcnow()
        entry.status = "approved" if approved else "rejected"
        
        await self._persist(entry)
        logger.info(f"Audit: Approval {'granted' if approved else 'denied'} for {entry.tool_name}")
        
        return entry
    
    def _redact_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Redact sensitive values from parameters."""
        redacted = {}
        
        for key, value in params.items():
            key_lower = key.lower()
            
            if any(sensitive in key_lower for sensitive in self._sensitive_keys):
                redacted[key] = "[REDACTED]"
            elif isinstance(value, dict):
                redacted[key] = self._redact_params(value)
            elif isinstance(value, list):
                redacted[key] = [
                    self._redact_params(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                redacted[key] = value
        
        return redacted
    
    def _redact_output(self, data: Any) -> Any:
        """Redact sensitive values from output."""
        if isinstance(data, dict):
            return self._redact_params(data)
        elif isinstance(data, list):
            return [self._redact_output(item) for item in data]
        return data
    
    async def _persist(self, entry: AuditEntry) -> None:
        """Persist entry to database."""
        if not self.db_session:
            return
        
        try:
            log_record = ToolAuditLog(
                id=uuid.UUID(entry.id),
                event_type=entry.event_type.value,
                tool_name=entry.tool_name,
                tenant_id=entry.tenant_id,
                user_id=entry.user_id,
                organization_id=entry.organization_id,
                session_id=entry.session_id,
                conversation_id=entry.conversation_id,
                request_id=entry.request_id,
                execution_id=entry.execution_id,
                input_params=entry.input_params,
                input_hash=entry.input_hash,
                output_data=entry.output_data,
                output_redacted=entry.output_redacted,
                status=entry.status,
                error_message=entry.error_message,
                error_code=entry.error_code,
                duration_ms=entry.duration_ms,
                tokens_used=entry.tokens_used,
                cost_incurred=entry.cost_incurred,
                created_at=entry.created_at,
                completed_at=entry.completed_at,
                source=entry.source,
                ip_address=entry.ip_address,
                user_agent=entry.user_agent,
                requires_approval=entry.requires_approval,
                approved_by=entry.approved_by,
                approved_at=entry.approved_at,
            )
            
            self.db_session.add(log_record)
            await self.db_session.commit()
            
        except Exception as e:
            logger.error(f"Failed to persist audit entry: {e}")
            # Don't raise - audit logging should not block execution


# Query interface for audit logs
class AuditQuery:
    """Query interface for audit logs."""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
    
    async def get_by_execution_id(self, execution_id: str) -> Optional[AuditEntry]:
        """Get audit entry by execution ID."""
        from sqlalchemy import select
        
        result = await self.db_session.execute(
            select(ToolAuditLog).where(ToolAuditLog.execution_id == execution_id)
        )
        record = result.scalar_one_or_none()
        
        if record:
            return self._to_entry(record)
        return None
    
    async def list_by_user(
        self,
        tenant_id: str,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditEntry]:
        """List audit entries for a user."""
        from sqlalchemy import select
        
        result = await self.db_session.execute(
            select(ToolAuditLog)
            .where(
                ToolAuditLog.tenant_id == tenant_id,
                ToolAuditLog.user_id == user_id,
            )
            .order_by(ToolAuditLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        
        return [self._to_entry(r) for r in result.scalars()]
    
    async def list_by_tool(
        self,
        tenant_id: str,
        tool_name: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditEntry]:
        """List audit entries for a tool."""
        from sqlalchemy import select
        
        result = await self.db_session.execute(
            select(ToolAuditLog)
            .where(
                ToolAuditLog.tenant_id == tenant_id,
                ToolAuditLog.tool_name == tool_name,
            )
            .order_by(ToolAuditLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        
        return [self._to_entry(r) for r in result.scalars()]
    
    def _to_entry(self, record: ToolAuditLog) -> AuditEntry:
        """Convert database record to AuditEntry."""
        return AuditEntry(
            id=str(record.id),
            event_type=AuditEventType(record.event_type),
            tool_name=record.tool_name,
            tenant_id=record.tenant_id,
            user_id=record.user_id,
            organization_id=record.organization_id,
            session_id=record.session_id,
            conversation_id=record.conversation_id,
            request_id=record.request_id,
            execution_id=record.execution_id,
            input_params=record.input_params or {},
            input_hash=record.input_hash,
            output_data=record.output_data,
            output_redacted=record.output_redacted,
            status=record.status,
            error_message=record.error_message,
            error_code=record.error_code,
            duration_ms=record.duration_ms,
            tokens_used=record.tokens_used,
            cost_incurred=record.cost_incurred,
            created_at=record.created_at,
            completed_at=record.completed_at,
            source=record.source,
            ip_address=record.ip_address,
            user_agent=record.user_agent,
            requires_approval=record.requires_approval,
            approved_by=record.approved_by,
            approved_at=record.approved_at,
        )
