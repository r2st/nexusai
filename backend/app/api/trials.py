"""Trial management API endpoints.

Provides endpoints for:
- Starting and managing trials
- Admin trial management (extend, expire, view all)
- Trial statistics
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.api.deps import get_current_user, get_db

from app.models.organization import Organization, OrganizationMember, MemberRole
from app.models.user import User, UserRole
from app.services.trial import TrialService


logger = structlog.get_logger()

router = APIRouter()


# Request/Response Models
class TrialStatusResponse(BaseModel):
    """Trial status response."""

    trial_status: str
    is_trial_active: bool
    trial_started_at: str | None
    trial_ends_at: str | None
    trial_days_remaining: int
    can_access_features: bool
    current_tier: str
    max_members: int
    max_projects: int
    was_extended: bool


class ExtendTrialRequest(BaseModel):
    """Extend trial request."""

    days: int
    reason: str


class ExtendTrialResponse(BaseModel):
    """Extend trial response."""

    message: str
    new_end_date: str
    days_added: int


class TrialStatisticsResponse(BaseModel):
    """Trial statistics response."""

    active: int
    expired: int
    converted: int
    expiring_soon: int
    conversion_rate: float
    total_trials: int


class OrganizationTrialResponse(BaseModel):
    """Organization with trial info response."""

    id: str
    name: str
    slug: str
    tier: str
    trial_status: str
    trial_started_at: datetime | None
    trial_ends_at: datetime | None
    trial_days_remaining: int
    current_member_count: int
    current_project_count: int

    class Config:
        from_attributes = True


# Helper functions
async def get_org_with_membership(
    org_id: str,
    db: AsyncSession,
    current_user: User,
) -> Organization:
    """Get organization if user is a member."""
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.is_active == True,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a member of this organization")

    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    return org


async def get_org_with_admin_role(
    org_id: str,
    db: AsyncSession,
    current_user: User,
) -> Organization:
    """Get organization if user is an admin or owner."""
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.role.in_([MemberRole.OWNER.value, MemberRole.ADMIN.value]),
            OrganizationMember.is_active == True,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=403,
            detail="Not authorized to manage trials for this organization"
        )

    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    return org


def require_admin(current_user: User) -> None:
    """Check if user is a system admin."""
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )


# Public endpoints
@router.get("/{org_id}/trial", response_model=TrialStatusResponse)
async def get_trial_status(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get the trial status for an organization."""
    org = await get_org_with_membership(org_id, db, current_user)

    trial_service = TrialService(db)
    return await trial_service.get_organization_trial_status(org)


@router.post("/{org_id}/trial/start", response_model=TrialStatusResponse)
async def start_trial(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Start a trial for an organization."""
    org = await get_org_with_admin_role(org_id, db, current_user)

    trial_service = TrialService(db)

    try:
        await trial_service.start_trial(org, triggered_by=current_user.id)
        await db.commit()
        await db.refresh(org)
        return await trial_service.get_organization_trial_status(org)
    except ValueError as e:
        logger.warning("Trial start failed", org_id=org_id, error=str(e))
        raise HTTPException(status_code=400, detail="Unable to start trial. The organization may already have an active or expired trial.")


# Admin endpoints
@router.get("/admin/trials", response_model=list[OrganizationTrialResponse])
async def list_all_trials(
    status: str | None = Query(None, description="Filter by trial status"),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Organization]:
    """List all organizations with trials (admin only)."""
    require_admin(current_user)

    from app.services.subscription import SubscriptionService

    subscription_service = SubscriptionService(db)
    orgs = await subscription_service.get_all_trials(
        status=status,
        limit=limit,
        offset=offset,
    )

    # Add computed property for response
    result = []
    for org in orgs:
        result.append({
            "id": org.id,
            "name": org.name,
            "slug": org.slug,
            "tier": org.tier,
            "trial_status": org.trial_status,
            "trial_started_at": org.trial_started_at,
            "trial_ends_at": org.trial_ends_at,
            "trial_days_remaining": org.trial_days_remaining,
            "current_member_count": org.current_member_count,
            "current_project_count": org.current_project_count,
        })
    return result


@router.get("/admin/trials/statistics", response_model=TrialStatisticsResponse)
async def get_trial_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get aggregated trial statistics (admin only)."""
    require_admin(current_user)

    from app.services.subscription import SubscriptionService

    subscription_service = SubscriptionService(db)
    return await subscription_service.get_trial_statistics()


@router.post("/admin/trials/{org_id}/extend", response_model=ExtendTrialResponse)
async def extend_trial(
    org_id: str,
    request: ExtendTrialRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Extend an organization's trial (admin only)."""
    require_admin(current_user)

    # Get organization
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    trial_service = TrialService(db)

    try:
        await trial_service.extend_trial(
            org,
            days=request.days,
            reason=request.reason,
            extended_by=current_user.id,
        )
        await db.commit()
        await db.refresh(org)

        return {
            "message": f"Trial extended by {request.days} days",
            "new_end_date": org.trial_ends_at.isoformat() if org.trial_ends_at else "",
            "days_added": request.days,
        }
    except ValueError as e:
        logger.warning("Trial extension failed", org_id=org_id, error=str(e))
        raise HTTPException(status_code=400, detail="Unable to extend trial. Please check the organization's trial status.")


@router.post("/admin/trials/{org_id}/expire")
async def force_expire_trial(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Force expire an organization's trial (admin only)."""
    require_admin(current_user)

    # Get organization
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    trial_service = TrialService(db)

    try:
        await trial_service.expire_trial(org, triggered_by=current_user.id)
        await db.commit()

        return {
            "message": "Trial expired and organization downgraded to free tier",
            "organization_id": org_id,
        }
    except ValueError as e:
        logger.warning("Trial expiration failed", org_id=org_id, error=str(e))
        raise HTTPException(status_code=400, detail="Unable to expire trial. Please check the organization's trial status.")
