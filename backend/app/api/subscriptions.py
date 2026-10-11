"""Subscription and usage management API endpoints.

Provides endpoints for:
- Usage tracking and limits
- Tier changes
- Subscription management
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.api.deps import get_current_user, get_db

from app.models.organization import Organization, OrganizationMember, MemberRole
from app.models.user import User, UserRole
from app.services.subscription import SubscriptionService

logger = structlog.get_logger()

router = APIRouter()


# Request/Response Models
class UsageSummaryResponse(BaseModel):
    """Usage summary response."""

    class UsageDetail(BaseModel):
        current: int
        max: int
        percentage: float
        at_limit: bool

    members: UsageDetail
    projects: UsageDetail
    tier: str
    can_access_features: bool
    trial_active: bool
    subscription_active: bool


class ChangeTierRequest(BaseModel):
    """Change tier request."""

    tier: str


class ChangeTierResponse(BaseModel):
    """Change tier response."""

    message: str
    previous_tier: str
    new_tier: str
    new_max_members: int
    new_max_projects: int


class CancelSubscriptionRequest(BaseModel):
    """Cancel subscription request."""

    at_period_end: bool = True


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


async def get_org_with_owner_role(
    org_id: str,
    db: AsyncSession,
    current_user: User,
) -> Organization:
    """Get organization if user is an owner."""
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.role == MemberRole.OWNER.value,
            OrganizationMember.is_active == True,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=403,
            detail="Only owners can manage subscriptions"
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
@router.get("/{org_id}/usage", response_model=UsageSummaryResponse)
async def get_usage_summary(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get usage summary for an organization."""
    org = await get_org_with_membership(org_id, db, current_user)

    subscription_service = SubscriptionService(db)

    # Update counts first to ensure accuracy
    await subscription_service.update_usage_counts(org)

    return await subscription_service.get_usage_summary(org)


@router.post("/{org_id}/subscription/cancel")
async def cancel_subscription(
    org_id: str,
    request: CancelSubscriptionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Cancel an organization's subscription."""
    org = await get_org_with_owner_role(org_id, db, current_user)

    subscription_service = SubscriptionService(db)

    try:
        await subscription_service.cancel_subscription(
            org,
            at_period_end=request.at_period_end,
            triggered_by=current_user.id,
        )
        await db.commit()

        if request.at_period_end:
            return {
                "message": "Subscription scheduled for cancellation at end of billing period",
                "cancel_at": org.subscription_ends_at.isoformat() if org.subscription_ends_at else None,
            }
        else:
            return {
                "message": "Subscription canceled immediately",
                "new_tier": org.tier,
            }
    except ValueError as e:
        logger.warning("Subscription cancellation failed", org_id=org_id, error=str(e))
        raise HTTPException(status_code=400, detail="Unable to cancel subscription. Please check the subscription status.")


@router.post("/{org_id}/subscription/resume")
async def resume_subscription(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Resume a subscription scheduled for cancellation."""
    org = await get_org_with_owner_role(org_id, db, current_user)

    subscription_service = SubscriptionService(db)

    try:
        await subscription_service.resume_subscription(
            org,
            triggered_by=current_user.id,
        )
        await db.commit()

        return {
            "message": "Subscription resumed",
            "tier": org.tier,
        }
    except ValueError as e:
        logger.warning("Subscription resume failed", org_id=org_id, error=str(e))
        raise HTTPException(status_code=400, detail="Unable to resume subscription. Please check the subscription status.")


# Admin endpoints
@router.post("/admin/{org_id}/tier", response_model=ChangeTierResponse)
async def change_organization_tier(
    org_id: str,
    request: ChangeTierRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Change an organization's tier (admin only)."""
    require_admin(current_user)

    # Get organization
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    previous_tier = org.tier

    subscription_service = SubscriptionService(db)
    try:
        await subscription_service.change_tier(
            org,
            new_tier=request.tier,
            triggered_by=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
    await db.refresh(org)

    return {
        "message": f"Tier changed from {previous_tier} to {request.tier}",
        "previous_tier": previous_tier,
        "new_tier": org.tier,
        "new_max_members": org.max_members,
        "new_max_projects": org.max_projects,
    }


@router.post("/admin/{org_id}/refresh-usage")
async def refresh_usage_counts(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Refresh cached usage counts for an organization (admin only)."""
    require_admin(current_user)

    # Get organization
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    subscription_service = SubscriptionService(db)
    await subscription_service.update_usage_counts(org)
    await db.commit()
    await db.refresh(org)

    return {
        "message": "Usage counts refreshed",
        "current_member_count": org.current_member_count,
        "current_project_count": org.current_project_count,
    }
