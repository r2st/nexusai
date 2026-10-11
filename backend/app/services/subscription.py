"""Subscription management service."""

from datetime import UTC, datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.organization import (
    Organization,
    OrganizationMember,
    OrganizationTier,
)
from app.models.subscription import (
    SubscriptionEvent,
    SubscriptionEventType,
    SubscriptionStatus,
    TrialStatus,
)


class SubscriptionService:
    """Service for managing organization subscriptions and usage."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_member_limit(
        self,
        organization: Organization,
    ) -> tuple[bool, str]:
        """Check if organization can add more members.

        Args:
            organization: The organization to check

        Returns:
            Tuple of (can_add, message)
        """
        if organization.current_member_count >= organization.max_members:
            return (
                False,
                f"Organization has reached the maximum of {organization.max_members} members. "
                f"Upgrade your plan to add more members.",
            )
        return (True, "")

    async def check_project_limit(
        self,
        organization: Organization,
    ) -> tuple[bool, str]:
        """Check if organization can create more projects.

        Args:
            organization: The organization to check

        Returns:
            Tuple of (can_create, message)
        """
        if organization.current_project_count >= organization.max_projects:
            return (
                False,
                f"Organization has reached the maximum of {organization.max_projects} projects. "
                f"Upgrade your plan to create more projects.",
            )
        return (True, "")

    async def update_usage_counts(
        self,
        organization: Organization,
    ) -> Organization:
        """Update cached usage counts for an organization.

        Args:
            organization: The organization to update

        Returns:
            Updated organization with correct counts
        """
        # Count active members
        member_count = await self.db.scalar(
            select(func.count(OrganizationMember.id)).where(
                and_(
                    OrganizationMember.organization_id == organization.id,
                    OrganizationMember.is_active == True,
                )
            )
        )

        # Count projects (lazy import to avoid circular dependency)
        from app.models.project import Project

        project_count = await self.db.scalar(
            select(func.count(Project.id)).where(
                Project.organization_id == organization.id
            )
        )

        organization.current_member_count = member_count or 0
        organization.current_project_count = project_count or 0

        await self.db.flush()
        return organization

    async def get_usage_summary(
        self,
        organization: Organization,
    ) -> dict:
        """Get usage summary for an organization.

        Args:
            organization: The organization to get summary for

        Returns:
            Dictionary with usage details
        """
        return {
            "members": {
                "current": organization.current_member_count,
                "max": organization.max_members,
                "percentage": organization.member_usage_percentage,
                "at_limit": organization.is_at_member_limit,
            },
            "projects": {
                "current": organization.current_project_count,
                "max": organization.max_projects,
                "percentage": organization.project_usage_percentage,
                "at_limit": organization.is_at_project_limit,
            },
            "tier": organization.tier,
            "can_access_features": organization.can_access_features,
            "trial_active": organization.is_trial_active,
            "subscription_active": organization.has_active_subscription,
        }

    _VALID_TIERS = frozenset({
        OrganizationTier.FREE.value,
        OrganizationTier.STARTER.value,
        OrganizationTier.PROFESSIONAL.value,
        OrganizationTier.ENTERPRISE.value,
    })

    async def change_tier(
        self,
        organization: Organization,
        new_tier: str,
        triggered_by: str,
    ) -> Organization:
        """Change an organization's tier.

        Args:
            organization: The organization to change
            new_tier: The new tier to set
            triggered_by: User ID who made the change

        Returns:
            Updated organization
        """
        if new_tier not in self._VALID_TIERS:
            raise ValueError(
                f"Invalid tier '{new_tier}'. "
                f"Must be one of: {', '.join(sorted(self._VALID_TIERS))}"
            )

        previous_tier = organization.tier

        if previous_tier == new_tier:
            raise ValueError(f"Organization is already on the '{new_tier}' tier")

        # Update tier
        organization.tier = new_tier

        # Update limits based on tier
        tier_limits = self._get_tier_limits(new_tier)
        organization.max_members = tier_limits["max_members"]
        organization.max_projects = tier_limits["max_projects"]

        # Log the event
        event = SubscriptionEvent(
            organization_id=organization.id,
            event_type=SubscriptionEventType.TIER_CHANGED.value,
            previous_tier=previous_tier,
            new_tier=new_tier,
            triggered_by=triggered_by,
            event_metadata={
                "changed_at": datetime.now(UTC).isoformat(),
            },
        )
        self.db.add(event)
        await self.db.flush()

        return organization

    async def get_all_trials(
        self,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Organization]:
        """Get all organizations with trials, optionally filtered by status.

        Args:
            status: Optional trial status filter
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of organizations
        """
        query = select(Organization).where(
            Organization.trial_status != TrialStatus.NONE.value
        )

        if status:
            query = query.where(Organization.trial_status == status)

        query = query.order_by(Organization.trial_started_at.desc())
        query = query.limit(limit).offset(offset)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_trial_statistics(self) -> dict:
        """Get aggregated trial statistics.

        Returns:
            Dictionary with trial statistics
        """
        # Count trials by status
        active_count = await self.db.scalar(
            select(func.count(Organization.id)).where(
                Organization.trial_status == TrialStatus.ACTIVE.value
            )
        )

        expired_count = await self.db.scalar(
            select(func.count(Organization.id)).where(
                Organization.trial_status == TrialStatus.EXPIRED.value
            )
        )

        converted_count = await self.db.scalar(
            select(func.count(Organization.id)).where(
                Organization.trial_status == TrialStatus.CONVERTED.value
            )
        )

        # Count expiring soon (within TRIAL_REMINDER_DAYS)
        from datetime import timedelta

        now = datetime.now(UTC)
        expiring_threshold = now + timedelta(days=settings.TRIAL_REMINDER_DAYS)

        expiring_soon_count = await self.db.scalar(
            select(func.count(Organization.id)).where(
                and_(
                    Organization.trial_status == TrialStatus.ACTIVE.value,
                    Organization.trial_ends_at <= expiring_threshold,
                    Organization.trial_ends_at > now,
                )
            )
        )

        # Calculate conversion rate
        total_ended = (expired_count or 0) + (converted_count or 0)
        conversion_rate = (
            ((converted_count or 0) / total_ended * 100) if total_ended > 0 else 0.0
        )

        return {
            "active": active_count or 0,
            "expired": expired_count or 0,
            "converted": converted_count or 0,
            "expiring_soon": expiring_soon_count or 0,
            "conversion_rate": round(conversion_rate, 2),
            "total_trials": (active_count or 0)
            + (expired_count or 0)
            + (converted_count or 0),
        }

    async def cancel_subscription(
        self,
        organization: Organization,
        at_period_end: bool,
        triggered_by: str,
    ) -> Organization:
        """Cancel an organization's subscription.

        Args:
            organization: The organization to cancel subscription for
            at_period_end: Whether to cancel at end of current period
            triggered_by: User ID who triggered cancellation

        Returns:
            Updated organization
        """
        cancellable_statuses = {
            SubscriptionStatus.ACTIVE.value,
            SubscriptionStatus.PAST_DUE.value,
            SubscriptionStatus.PAUSED.value,
        }
        if organization.subscription_status not in cancellable_statuses:
            raise ValueError(
                "Subscription must be active, past_due, or paused to cancel"
            )

        previous_status = organization.subscription_status

        if at_period_end and organization.subscription_status == SubscriptionStatus.ACTIVE.value:
            organization.subscription_cancel_at_period_end = True
        else:
            organization.subscription_status = SubscriptionStatus.CANCELED.value
            # Downgrade to free tier immediately
            organization.tier = OrganizationTier.FREE.value
            organization.max_members = settings.FREE_TIER_MAX_MEMBERS
            organization.max_projects = settings.FREE_TIER_MAX_PROJECTS

        # Log the event
        event = SubscriptionEvent(
            organization_id=organization.id,
            event_type=SubscriptionEventType.SUBSCRIPTION_CANCELED.value,
            previous_status=previous_status,
            new_status=organization.subscription_status,
            triggered_by=triggered_by,
            event_metadata={
                "at_period_end": at_period_end,
                "canceled_at": datetime.now(UTC).isoformat(),
            },
        )
        self.db.add(event)
        await self.db.flush()

        return organization

    async def resume_subscription(
        self,
        organization: Organization,
        triggered_by: str,
    ) -> Organization:
        """Resume a paused or pending-cancel subscription.

        Handles two cases:
        1. Subscription scheduled for cancellation at period end
        2. Subscription in PAUSED state
        """
        resumable_statuses = {
            SubscriptionStatus.PAUSED.value,
            SubscriptionStatus.PAST_DUE.value,
        }

        previous_status = organization.subscription_status

        if organization.subscription_cancel_at_period_end:
            organization.subscription_cancel_at_period_end = False
        elif organization.subscription_status in resumable_statuses:
            organization.subscription_status = SubscriptionStatus.ACTIVE.value
        else:
            raise ValueError(
                "Subscription is not in a resumable state "
                "(must be paused, past_due, or scheduled for cancellation)"
            )

        # Log the event
        event = SubscriptionEvent(
            organization_id=organization.id,
            event_type=SubscriptionEventType.SUBSCRIPTION_RESUMED.value,
            previous_status=previous_status,
            new_status=organization.subscription_status,
            triggered_by=triggered_by,
            event_metadata={
                "resumed_at": datetime.now(UTC).isoformat(),
                "was_cancel_at_period_end": previous_status == SubscriptionStatus.ACTIVE.value,
            },
        )
        self.db.add(event)
        await self.db.flush()

        return organization

    def _get_tier_limits(self, tier: str) -> dict:
        """Get member and project limits for a tier."""
        tier_limits = {
            OrganizationTier.FREE.value: {
                "max_members": settings.FREE_TIER_MAX_MEMBERS,
                "max_projects": settings.FREE_TIER_MAX_PROJECTS,
            },
            OrganizationTier.STARTER.value: {
                "max_members": settings.STARTER_TIER_MAX_MEMBERS,
                "max_projects": settings.STARTER_TIER_MAX_PROJECTS,
            },
            OrganizationTier.PROFESSIONAL.value: {
                "max_members": settings.PROFESSIONAL_TIER_MAX_MEMBERS,
                "max_projects": settings.PROFESSIONAL_TIER_MAX_PROJECTS,
            },
            OrganizationTier.ENTERPRISE.value: {
                "max_members": settings.ENTERPRISE_TIER_MAX_MEMBERS,
                "max_projects": settings.ENTERPRISE_TIER_MAX_PROJECTS,
            },
        }
        return tier_limits.get(
            tier,
            tier_limits[OrganizationTier.FREE.value],
        )
