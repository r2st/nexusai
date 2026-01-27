"""Audit logging service for persisting and querying audit events."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.models.audit_log import (
    ApprovalRecord,
    AuditEventType,
    AuditLog,
    AuditSeverity,
)

logger = structlog.get_logger()


class AuditService:
    """Service for audit log persistence and querying."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # Audit Log Creation
    # =========================================================================

    async def log_tool_invocation(
        self,
        tool_name: str,
        service_name: str,
        user_id: str | None = None,
        organization_id: str | None = None,
        input_params: dict | None = None,
        request_id: str | None = None,
        session_id: str | None = None,
        ip_address: str | None = None,
        conversation_id: str | None = None,
        metadata: dict | None = None,
    ) -> AuditLog:
        """Log a tool invocation event."""
        log_entry = AuditLog(
            id=str(uuid4()),
            event_type=AuditEventType.TOOL_INVOCATION.value,
            severity=AuditSeverity.INFO.value,
            tool_name=tool_name,
            service_name=service_name,
            user_id=user_id,
            organization_id=organization_id,
            input_params=self._sanitize_params(input_params),
            request_id=request_id or str(uuid4()),
            session_id=session_id,
            ip_address=ip_address,
            conversation_id=conversation_id,
            metadata=metadata,
            success=True,  # Will be updated on completion
        )
        self.db.add(log_entry)
        await self.db.flush()
        return log_entry

    async def log_tool_success(
        self,
        tool_name: str,
        service_name: str,
        duration_ms: float,
        user_id: str | None = None,
        organization_id: str | None = None,
        output_summary: str | None = None,
        tokens_used: int | None = None,
        was_cached: bool = False,
        request_id: str | None = None,
        metadata: dict | None = None,
    ) -> AuditLog:
        """Log a successful tool execution."""
        log_entry = AuditLog(
            id=str(uuid4()),
            event_type=AuditEventType.TOOL_SUCCESS.value,
            severity=AuditSeverity.INFO.value,
            tool_name=tool_name,
            service_name=service_name,
            user_id=user_id,
            organization_id=organization_id,
            output_summary=output_summary[:1000] if output_summary else None,
            duration_ms=duration_ms,
            tokens_used=tokens_used,
            was_cached=was_cached,
            request_id=request_id,
            metadata=metadata,
            success=True,
        )
        self.db.add(log_entry)
        await self.db.flush()
        return log_entry

    async def log_tool_failure(
        self,
        tool_name: str,
        service_name: str,
        error_message: str,
        error_code: str | None = None,
        duration_ms: float | None = None,
        user_id: str | None = None,
        organization_id: str | None = None,
        input_params: dict | None = None,
        request_id: str | None = None,
        metadata: dict | None = None,
    ) -> AuditLog:
        """Log a failed tool execution."""
        log_entry = AuditLog(
            id=str(uuid4()),
            event_type=AuditEventType.TOOL_FAILURE.value,
            severity=AuditSeverity.ERROR.value,
            tool_name=tool_name,
            service_name=service_name,
            user_id=user_id,
            organization_id=organization_id,
            input_params=self._sanitize_params(input_params),
            error_message=error_message,
            error_code=error_code,
            duration_ms=duration_ms,
            request_id=request_id,
            metadata=metadata,
            success=False,
        )
        self.db.add(log_entry)
        await self.db.flush()
        return log_entry

    async def log_rate_limit_exceeded(
        self,
        tool_name: str,
        user_id: str | None = None,
        organization_id: str | None = None,
        limit_type: str = "user",
        current_count: int = 0,
        limit: int = 0,
        metadata: dict | None = None,
    ) -> AuditLog:
        """Log a rate limit exceeded event."""
        log_entry = AuditLog(
            id=str(uuid4()),
            event_type=AuditEventType.RATE_LIMIT_EXCEEDED.value,
            severity=AuditSeverity.WARNING.value,
            tool_name=tool_name,
            user_id=user_id,
            organization_id=organization_id,
            metadata={
                **(metadata or {}),
                "limit_type": limit_type,
                "current_count": current_count,
                "limit": limit,
            },
            success=False,
        )
        self.db.add(log_entry)
        await self.db.flush()
        return log_entry

    async def log_permission_denied(
        self,
        tool_name: str,
        user_id: str | None = None,
        organization_id: str | None = None,
        required_permission: str | None = None,
        reason: str | None = None,
        metadata: dict | None = None,
    ) -> AuditLog:
        """Log a permission denied event."""
        log_entry = AuditLog(
            id=str(uuid4()),
            event_type=AuditEventType.PERMISSION_DENIED.value,
            severity=AuditSeverity.WARNING.value,
            tool_name=tool_name,
            user_id=user_id,
            organization_id=organization_id,
            error_message=reason or "Permission denied",
            metadata={
                **(metadata or {}),
                "required_permission": required_permission,
            },
            success=False,
        )
        self.db.add(log_entry)
        await self.db.flush()
        return log_entry

    async def log_approval_requested(
        self,
        tool_name: str,
        approval_id: str,
        user_id: str,
        reason: str,
        organization_id: str | None = None,
        metadata: dict | None = None,
    ) -> AuditLog:
        """Log an approval request event."""
        log_entry = AuditLog(
            id=str(uuid4()),
            event_type=AuditEventType.APPROVAL_REQUESTED.value,
            severity=AuditSeverity.INFO.value,
            tool_name=tool_name,
            user_id=user_id,
            organization_id=organization_id,
            approval_id=approval_id,
            required_approval=True,
            metadata={**(metadata or {}), "reason": reason},
            success=True,
        )
        self.db.add(log_entry)
        await self.db.flush()
        return log_entry

    async def log_circuit_breaker_event(
        self,
        service_name: str,
        is_open: bool,
        failure_count: int | None = None,
        metadata: dict | None = None,
    ) -> AuditLog:
        """Log a circuit breaker state change."""
        event_type = (
            AuditEventType.CIRCUIT_BREAKER_OPEN
            if is_open
            else AuditEventType.CIRCUIT_BREAKER_CLOSED
        )
        log_entry = AuditLog(
            id=str(uuid4()),
            event_type=event_type.value,
            severity=AuditSeverity.WARNING.value if is_open else AuditSeverity.INFO.value,
            service_name=service_name,
            metadata={**(metadata or {}), "failure_count": failure_count},
            success=not is_open,
        )
        self.db.add(log_entry)
        await self.db.flush()
        return log_entry

    async def log_data_redaction(
        self,
        tool_name: str,
        user_id: str | None = None,
        redacted_fields: list[str] | None = None,
        metadata: dict | None = None,
    ) -> AuditLog:
        """Log a data redaction event."""
        log_entry = AuditLog(
            id=str(uuid4()),
            event_type=AuditEventType.DATA_REDACTION.value,
            severity=AuditSeverity.INFO.value,
            tool_name=tool_name,
            user_id=user_id,
            metadata={**(metadata or {}), "redacted_fields": redacted_fields or []},
            success=True,
        )
        self.db.add(log_entry)
        await self.db.flush()
        return log_entry

    # =========================================================================
    # Approval Records
    # =========================================================================

    async def create_approval_request(
        self,
        tool_name: str,
        service_name: str,
        requester_user_id: str,
        input_params: dict,
        reason: str,
        organization_id: str | None = None,
        expires_in_minutes: int = 60,
        metadata: dict | None = None,
    ) -> ApprovalRecord:
        """Create a new approval request."""
        approval = ApprovalRecord(
            id=str(uuid4()),
            tool_name=tool_name,
            service_name=service_name,
            requester_user_id=requester_user_id,
            requester_organization_id=organization_id,
            input_params=self._sanitize_params(input_params),
            reason=reason,
            status="pending",
            expires_at=datetime.now(UTC) + timedelta(minutes=expires_in_minutes),
            metadata=metadata,
        )
        self.db.add(approval)
        await self.db.flush()

        # Log the approval request
        await self.log_approval_requested(
            tool_name=tool_name,
            approval_id=approval.id,
            user_id=requester_user_id,
            reason=reason,
            organization_id=organization_id,
        )

        return approval

    async def approve_request(
        self,
        approval_id: str,
        approver_user_id: str,
        comment: str | None = None,
    ) -> ApprovalRecord | None:
        """Approve a pending request."""
        result = await self.db.execute(
            select(ApprovalRecord).where(ApprovalRecord.id == approval_id)
        )
        approval = result.scalar_one_or_none()

        if not approval:
            return None

        if approval.status != "pending":
            return approval

        if approval.expires_at < datetime.now(UTC):
            approval.status = "expired"
            await self.db.flush()
            return approval

        approval.status = "approved"
        approval.approver_user_id = approver_user_id
        approval.approver_comment = comment
        approval.resolved_at = datetime.now(UTC)
        await self.db.flush()

        # Log the approval
        await self._log_approval_resolution(approval, "approved")

        return approval

    async def deny_request(
        self,
        approval_id: str,
        approver_user_id: str,
        comment: str | None = None,
    ) -> ApprovalRecord | None:
        """Deny a pending request."""
        result = await self.db.execute(
            select(ApprovalRecord).where(ApprovalRecord.id == approval_id)
        )
        approval = result.scalar_one_or_none()

        if not approval:
            return None

        if approval.status != "pending":
            return approval

        approval.status = "denied"
        approval.approver_user_id = approver_user_id
        approval.approver_comment = comment
        approval.resolved_at = datetime.now(UTC)
        await self.db.flush()

        # Log the denial
        await self._log_approval_resolution(approval, "denied")

        return approval

    async def get_pending_approvals(
        self,
        organization_id: str | None = None,
        limit: int = 50,
    ) -> list[ApprovalRecord]:
        """Get pending approval requests."""
        query = select(ApprovalRecord).where(
            and_(
                ApprovalRecord.status == "pending",
                ApprovalRecord.expires_at > datetime.now(UTC),
            )
        )

        if organization_id:
            query = query.where(ApprovalRecord.requester_organization_id == organization_id)

        query = query.order_by(desc(ApprovalRecord.requested_at)).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def expire_old_approvals(self) -> int:
        """Expire approval requests that have passed their expiration time."""
        from sqlalchemy import update

        result = await self.db.execute(
            update(ApprovalRecord)
            .where(
                and_(
                    ApprovalRecord.status == "pending",
                    ApprovalRecord.expires_at < datetime.now(UTC),
                )
            )
            .values(status="expired", resolved_at=datetime.now(UTC))
        )
        await self.db.flush()
        return result.rowcount

    # =========================================================================
    # Audit Log Queries
    # =========================================================================

    async def get_audit_logs(
        self,
        user_id: str | None = None,
        organization_id: str | None = None,
        tool_name: str | None = None,
        service_name: str | None = None,
        event_types: list[str] | None = None,
        severity: str | None = None,
        success: bool | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        """Query audit logs with filters."""
        query = select(AuditLog)
        conditions = []

        if user_id:
            conditions.append(AuditLog.user_id == user_id)
        if organization_id:
            conditions.append(AuditLog.organization_id == organization_id)
        if tool_name:
            conditions.append(AuditLog.tool_name == tool_name)
        if service_name:
            conditions.append(AuditLog.service_name == service_name)
        if event_types:
            conditions.append(AuditLog.event_type.in_(event_types))
        if severity:
            conditions.append(AuditLog.severity == severity)
        if success is not None:
            conditions.append(AuditLog.success == success)
        if start_time:
            conditions.append(AuditLog.timestamp >= start_time)
        if end_time:
            conditions.append(AuditLog.timestamp <= end_time)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(desc(AuditLog.timestamp)).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_audit_log_by_id(self, log_id: str) -> AuditLog | None:
        """Get a specific audit log entry."""
        result = await self.db.execute(select(AuditLog).where(AuditLog.id == log_id))
        return result.scalar_one_or_none()

    async def get_audit_stats(
        self,
        user_id: str | None = None,
        organization_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]:
        """Get audit statistics."""
        conditions = []
        if user_id:
            conditions.append(AuditLog.user_id == user_id)
        if organization_id:
            conditions.append(AuditLog.organization_id == organization_id)
        if start_time:
            conditions.append(AuditLog.timestamp >= start_time)
        if end_time:
            conditions.append(AuditLog.timestamp <= end_time)

        where_clause = and_(*conditions) if conditions else True

        # Total invocations
        total_query = select(func.count(AuditLog.id)).where(
            and_(where_clause, AuditLog.event_type == AuditEventType.TOOL_INVOCATION.value)
        )
        total_result = await self.db.execute(total_query)
        total_invocations = total_result.scalar() or 0

        # Success count
        success_query = select(func.count(AuditLog.id)).where(
            and_(where_clause, AuditLog.event_type == AuditEventType.TOOL_SUCCESS.value)
        )
        success_result = await self.db.execute(success_query)
        success_count = success_result.scalar() or 0

        # Failure count
        failure_query = select(func.count(AuditLog.id)).where(
            and_(where_clause, AuditLog.event_type == AuditEventType.TOOL_FAILURE.value)
        )
        failure_result = await self.db.execute(failure_query)
        failure_count = failure_result.scalar() or 0

        # Rate limit count
        rate_limit_query = select(func.count(AuditLog.id)).where(
            and_(
                where_clause, AuditLog.event_type == AuditEventType.RATE_LIMIT_EXCEEDED.value
            )
        )
        rate_limit_result = await self.db.execute(rate_limit_query)
        rate_limit_count = rate_limit_result.scalar() or 0

        # Average duration
        avg_duration_query = select(func.avg(AuditLog.duration_ms)).where(
            and_(
                where_clause,
                AuditLog.event_type == AuditEventType.TOOL_SUCCESS.value,
                AuditLog.duration_ms.isnot(None),
            )
        )
        avg_duration_result = await self.db.execute(avg_duration_query)
        avg_duration = avg_duration_result.scalar() or 0

        # Top tools by usage
        top_tools_query = (
            select(AuditLog.tool_name, func.count(AuditLog.id).label("count"))
            .where(
                and_(
                    where_clause,
                    AuditLog.event_type == AuditEventType.TOOL_INVOCATION.value,
                    AuditLog.tool_name.isnot(None),
                )
            )
            .group_by(AuditLog.tool_name)
            .order_by(desc("count"))
            .limit(10)
        )
        top_tools_result = await self.db.execute(top_tools_query)
        top_tools = [{"tool": row[0], "count": row[1]} for row in top_tools_result.all()]

        return {
            "total_invocations": total_invocations,
            "success_count": success_count,
            "failure_count": failure_count,
            "success_rate": (
                success_count / total_invocations * 100 if total_invocations > 0 else 0
            ),
            "rate_limit_count": rate_limit_count,
            "avg_duration_ms": round(avg_duration, 2),
            "top_tools": top_tools,
        }

    async def get_tool_usage_timeline(
        self,
        tool_name: str | None = None,
        organization_id: str | None = None,
        hours: int = 24,
        bucket_minutes: int = 60,
    ) -> list[dict[str, Any]]:
        """Get tool usage over time in buckets."""
        start_time = datetime.now(UTC) - timedelta(hours=hours)

        conditions = [
            AuditLog.timestamp >= start_time,
            AuditLog.event_type == AuditEventType.TOOL_INVOCATION.value,
        ]

        if tool_name:
            conditions.append(AuditLog.tool_name == tool_name)
        if organization_id:
            conditions.append(AuditLog.organization_id == organization_id)

        # Use date_trunc for PostgreSQL
        bucket = func.date_trunc("hour", AuditLog.timestamp)

        query = (
            select(bucket.label("bucket"), func.count(AuditLog.id).label("count"))
            .where(and_(*conditions))
            .group_by(bucket)
            .order_by(bucket)
        )

        result = await self.db.execute(query)
        return [
            {"timestamp": row[0].isoformat() if row[0] else None, "count": row[1]}
            for row in result.all()
        ]

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _sanitize_params(self, params: dict | None) -> dict | None:
        """Remove sensitive data from parameters before logging."""
        if not params:
            return None

        sensitive_keys = {
            "password",
            "token",
            "api_key",
            "secret",
            "credential",
            "auth",
            "authorization",
            "private_key",
            "access_token",
            "refresh_token",
        }

        sanitized = {}
        for key, value in params.items():
            key_lower = key.lower()
            if any(s in key_lower for s in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_params(value)
            elif isinstance(value, str) and len(value) > 500:
                sanitized[key] = value[:500] + "...[TRUNCATED]"
            else:
                sanitized[key] = value

        return sanitized

    async def _log_approval_resolution(
        self, approval: ApprovalRecord, status: str
    ) -> None:
        """Log approval resolution event."""
        event_type = (
            AuditEventType.APPROVAL_GRANTED
            if status == "approved"
            else AuditEventType.APPROVAL_DENIED
        )
        log_entry = AuditLog(
            id=str(uuid4()),
            event_type=event_type.value,
            severity=AuditSeverity.INFO.value,
            tool_name=approval.tool_name,
            user_id=approval.requester_user_id,
            organization_id=approval.requester_organization_id,
            approval_id=approval.id,
            required_approval=True,
            metadata={
                "approver_id": approval.approver_user_id,
                "approver_comment": approval.approver_comment,
            },
            success=status == "approved",
        )
        self.db.add(log_entry)
        await self.db.flush()
