"""Audit API endpoints for querying audit logs and managing approvals."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.services.audit import AuditService

router = APIRouter()


# ======================
# Response Models
# ======================


class AuditLogResponse(BaseModel):
    """Audit log response model."""

    id: str
    event_type: str
    severity: str
    user_id: str | None
    organization_id: str | None
    tool_name: str | None
    service_name: str | None
    request_id: str | None
    input_params: dict | None
    output_summary: str | None
    error_message: str | None
    error_code: str | None
    duration_ms: float | None
    success: bool
    was_cached: bool
    required_approval: bool
    approval_id: str | None
    metadata: dict | None
    timestamp: str

    class Config:
        from_attributes = True


class AuditStatsResponse(BaseModel):
    """Audit statistics response."""

    total_invocations: int
    success_count: int
    failure_count: int
    success_rate: float
    rate_limit_count: int
    avg_duration_ms: float
    top_tools: list[dict[str, Any]]


class TimelinePoint(BaseModel):
    """Timeline data point."""

    timestamp: str | None
    count: int


class ApprovalResponse(BaseModel):
    """Approval record response."""

    id: str
    tool_name: str
    service_name: str
    input_params: dict
    reason: str
    requester_user_id: str
    status: str
    requested_at: str
    expires_at: str
    resolved_at: str | None
    approver_user_id: str | None
    approver_comment: str | None

    class Config:
        from_attributes = True


class ApprovalActionRequest(BaseModel):
    """Request model for approval actions."""

    comment: str | None = None


# ======================
# Audit Log Endpoints
# ======================


@router.get("/logs", response_model=list[AuditLogResponse])
async def get_audit_logs(
    user_id: str | None = None,
    organization_id: str | None = None,
    tool_name: str | None = None,
    service_name: str | None = None,
    event_types: str | None = Query(
        None, description="Comma-separated list of event types"
    ),
    severity: str | None = None,
    success: bool | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AuditLogResponse]:
    """
    Query audit logs with filters.

    Requires admin role to view logs for other users.
    """
    # Non-admins can only view their own logs
    if not current_user.is_admin and user_id and user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view audit logs for other users",
        )

    # Default to current user's logs for non-admins
    if not current_user.is_admin:
        user_id = current_user.id

    event_types_list = event_types.split(",") if event_types else None

    audit_service = AuditService(db)
    logs = await audit_service.get_audit_logs(
        user_id=user_id,
        organization_id=organization_id,
        tool_name=tool_name,
        service_name=service_name,
        event_types=event_types_list,
        severity=severity,
        success=success,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
    )

    return [
        AuditLogResponse(
            id=log.id,
            event_type=log.event_type,
            severity=log.severity,
            user_id=log.user_id,
            organization_id=log.organization_id,
            tool_name=log.tool_name,
            service_name=log.service_name,
            request_id=log.request_id,
            input_params=log.input_params,
            output_summary=log.output_summary,
            error_message=log.error_message,
            error_code=log.error_code,
            duration_ms=log.duration_ms,
            success=log.success,
            was_cached=log.was_cached,
            required_approval=log.required_approval,
            approval_id=log.approval_id,
            metadata=log.metadata,
            timestamp=log.timestamp.isoformat(),
        )
        for log in logs
    ]


@router.get("/logs/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AuditLogResponse:
    """Get a specific audit log entry."""
    audit_service = AuditService(db)
    log = await audit_service.get_audit_log_by_id(log_id)

    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log not found",
        )

    # Non-admins can only view their own logs
    if not current_user.is_admin and log.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view this audit log",
        )

    return AuditLogResponse(
        id=log.id,
        event_type=log.event_type,
        severity=log.severity,
        user_id=log.user_id,
        organization_id=log.organization_id,
        tool_name=log.tool_name,
        service_name=log.service_name,
        request_id=log.request_id,
        input_params=log.input_params,
        output_summary=log.output_summary,
        error_message=log.error_message,
        error_code=log.error_code,
        duration_ms=log.duration_ms,
        success=log.success,
        was_cached=log.was_cached,
        required_approval=log.required_approval,
        approval_id=log.approval_id,
        metadata=log.metadata,
        timestamp=log.timestamp.isoformat(),
    )


@router.get("/stats", response_model=AuditStatsResponse)
async def get_audit_stats(
    user_id: str | None = None,
    organization_id: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AuditStatsResponse:
    """Get audit statistics."""
    # Non-admins can only view their own stats
    if not current_user.is_admin:
        user_id = current_user.id

    audit_service = AuditService(db)
    stats = await audit_service.get_audit_stats(
        user_id=user_id,
        organization_id=organization_id,
        start_time=start_time,
        end_time=end_time,
    )

    return AuditStatsResponse(**stats)


@router.get("/timeline", response_model=list[TimelinePoint])
async def get_usage_timeline(
    tool_name: str | None = None,
    organization_id: str | None = None,
    hours: int = Query(24, le=168),  # Max 1 week
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TimelinePoint]:
    """Get tool usage timeline data."""
    # Non-admins can only see org-level data, not all data
    if not current_user.is_admin and not organization_id:
        # Get user's organization if they have one
        pass  # Allow without org filter for now

    audit_service = AuditService(db)
    timeline = await audit_service.get_tool_usage_timeline(
        tool_name=tool_name,
        organization_id=organization_id,
        hours=hours,
    )

    return [TimelinePoint(**point) for point in timeline]


# ======================
# Approval Endpoints
# ======================


@router.get("/approvals/pending", response_model=list[ApprovalResponse])
async def get_pending_approvals(
    organization_id: str | None = None,
    limit: int = Query(50, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ApprovalResponse]:
    """Get pending approval requests."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view approval requests",
        )

    audit_service = AuditService(db)
    approvals = await audit_service.get_pending_approvals(
        organization_id=organization_id,
        limit=limit,
    )

    return [
        ApprovalResponse(
            id=a.id,
            tool_name=a.tool_name,
            service_name=a.service_name,
            input_params=a.input_params,
            reason=a.reason,
            requester_user_id=a.requester_user_id,
            status=a.status,
            requested_at=a.requested_at.isoformat(),
            expires_at=a.expires_at.isoformat(),
            resolved_at=a.resolved_at.isoformat() if a.resolved_at else None,
            approver_user_id=a.approver_user_id,
            approver_comment=a.approver_comment,
        )
        for a in approvals
    ]


@router.post("/approvals/{approval_id}/approve", response_model=ApprovalResponse)
async def approve_request(
    approval_id: str,
    request: ApprovalActionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApprovalResponse:
    """Approve a pending request."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can approve requests",
        )

    audit_service = AuditService(db)
    approval = await audit_service.approve_request(
        approval_id=approval_id,
        approver_user_id=current_user.id,
        comment=request.comment,
    )

    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval request not found",
        )

    await db.commit()

    return ApprovalResponse(
        id=approval.id,
        tool_name=approval.tool_name,
        service_name=approval.service_name,
        input_params=approval.input_params,
        reason=approval.reason,
        requester_user_id=approval.requester_user_id,
        status=approval.status,
        requested_at=approval.requested_at.isoformat(),
        expires_at=approval.expires_at.isoformat(),
        resolved_at=approval.resolved_at.isoformat() if approval.resolved_at else None,
        approver_user_id=approval.approver_user_id,
        approver_comment=approval.approver_comment,
    )


@router.post("/approvals/{approval_id}/deny", response_model=ApprovalResponse)
async def deny_request(
    approval_id: str,
    request: ApprovalActionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApprovalResponse:
    """Deny a pending request."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can deny requests",
        )

    audit_service = AuditService(db)
    approval = await audit_service.deny_request(
        approval_id=approval_id,
        approver_user_id=current_user.id,
        comment=request.comment,
    )

    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval request not found",
        )

    await db.commit()

    return ApprovalResponse(
        id=approval.id,
        tool_name=approval.tool_name,
        service_name=approval.service_name,
        input_params=approval.input_params,
        reason=approval.reason,
        requester_user_id=approval.requester_user_id,
        status=approval.status,
        requested_at=approval.requested_at.isoformat(),
        expires_at=approval.expires_at.isoformat(),
        resolved_at=approval.resolved_at.isoformat() if approval.resolved_at else None,
        approver_user_id=approval.approver_user_id,
        approver_comment=approval.approver_comment,
    )
