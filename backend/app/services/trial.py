"""Trial management service."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.organization import Organization, OrganizationTier
from app.models.subscription import (
    SubscriptionEvent,
    SubscriptionEventType,
    SubscriptionStatus,
    TrialStatus,
)


class TrialService:
    """Service for managing organization trials."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def start_trial(
        self,
        organization: Organization,
        triggered_by: str | None = None,
    ) -> Organization:
        """Start a trial for an organization.

        Args:
            organization: The organization to start trial for
            triggered_by: User ID who triggered the trial start

        Returns:
            Updated organization with trial active

        Raises:
            ValueError: If organization already has/had a trial or active subscription
        """
        # Check if org already has a trial or subscription
        if organization.trial_status != TrialStatus.NONE.value:
            raise ValueError("Organization has already started a trial")
        if organization.subscription_status == SubscriptionStatus.ACTIVE.value:
            raise ValueError("Organization already has an active subscription")

        now = datetime.now(UTC)
        trial_end = now + timedelta(days=settings.TRIAL_DURATION_DAYS)

        # Update organization with trial info
        organization.trial_status = TrialStatus.ACTIVE.value
        organization.trial_started_at = now
        organization.trial_ends_at = trial_end

        # Set trial tier limits
        organization.tier = settings.TRIAL_TIER
        organization.max_members = settings.TRIAL_MAX_MEMBERS
        organization.max_projects = settings.TRIAL_MAX_PROJECTS

        # Log the event
        event = SubscriptionEvent(
            organization_id=organization.id,
            event_type=SubscriptionEventType.TRIAL_STARTED.value,
            previous_tier=OrganizationTier.FREE.value,
            new_tier=settings.TRIAL_TIER,
            previous_status=TrialStatus.NONE.value,
            new_status=TrialStatus.ACTIVE.value,
            triggered_by=triggered_by,
            event_metadata={
                "trial_duration_days": settings.TRIAL_DURATION_DAYS,
                "trial_ends_at": trial_end.isoformat(),
            },
        )
        self.db.add(event)
        await self.db.flush()

        return organization

    async def extend_trial(
        self,
        organization: Organization,
        days: int,
        reason: str,
        extended_by: str,
    ) -> Organization:
        """Extend an organization's trial period.

        Args:
            organization: The organization to extend trial for
            days: Number of days to extend
            reason: Reason for extension
            extended_by: User ID who authorized the extension

        Returns:
            Updated organization with extended trial

        Raises:
            ValueError: If organization doesn't have an active trial
        """
        if organization.trial_status != TrialStatus.ACTIVE.value:
            raise ValueError("Organization does not have an active trial")
        if organization.trial_ends_at is None:
            raise ValueError("Trial end date is not set")

        # Extend the trial
        old_end = organization.trial_ends_at
        new_end = old_end + timedelta(days=days)

        organization.trial_ends_at = new_end
        organization.trial_extended_by = extended_by
        organization.trial_extension_reason = reason

        # Log the event
        event = SubscriptionEvent(
            organization_id=organization.id,
            event_type=SubscriptionEventType.TRIAL_EXTENDED.value,
            triggered_by=extended_by,
            event_metadata={
                "extension_days": days,
                "reason": reason,
                "previous_end_date": old_end.isoformat(),
                "new_end_date": new_end.isoformat(),
            },
        )
        self.db.add(event)
        await self.db.flush()

        return organization

    async def expire_trial(
        self,
        organization: Organization,
        triggered_by: str | None = None,
    ) -> Organization:
        """Expire an organization's trial and downgrade to free tier.

        Args:
            organization: The organization to expire trial for
            triggered_by: User ID who triggered expiration (None for system)

        Returns:
            Updated organization with expired trial
        """
        if organization.trial_status != TrialStatus.ACTIVE.value:
            raise ValueError("Organization does not have an active trial")

        previous_tier = organization.tier

        # Expire the trial
        organization.trial_status = TrialStatus.EXPIRED.value

        # Downgrade to free tier
        organization.tier = OrganizationTier.FREE.value
        organization.max_members = settings.FREE_TIER_MAX_MEMBERS
        organization.max_projects = settings.FREE_TIER_MAX_PROJECTS

        # Log the event
        event = SubscriptionEvent(
            organization_id=organization.id,
            event_type=SubscriptionEventType.TRIAL_EXPIRED.value,
            previous_tier=previous_tier,
            new_tier=OrganizationTier.FREE.value,
            previous_status=TrialStatus.ACTIVE.value,
            new_status=TrialStatus.EXPIRED.value,
            triggered_by=triggered_by,
            event_metadata={
                "expired_at": datetime.now(UTC).isoformat(),
                "auto_downgraded": triggered_by is None,
            },
        )
        self.db.add(event)
        await self.db.flush()

        return organization

    async def convert_trial_to_subscription(
        self,
        organization: Organization,
        tier: str,
        triggered_by: str,
    ) -> Organization:
        """Convert a trial to a paid subscription.

        Args:
            organization: The organization to convert
            tier: The tier to subscribe to
            triggered_by: User ID who triggered the conversion

        Returns:
            Updated organization with active subscription
        """
        if organization.trial_status not in [
            TrialStatus.ACTIVE.value,
            TrialStatus.EXPIRED.value,
        ]:
            raise ValueError("Organization must have an active or expired trial")

        previous_tier = organization.tier
        previous_trial_status = organization.trial_status
        now = datetime.now(UTC)

        # Mark trial as converted
        organization.trial_status = TrialStatus.CONVERTED.value

        # Activate subscription
        organization.subscription_status = SubscriptionStatus.ACTIVE.value
        organization.subscription_started_at = now
        organization.tier = tier

        # Set tier limits based on tier
        tier_limits = self._get_tier_limits(tier)
        organization.max_members = tier_limits["max_members"]
        organization.max_projects = tier_limits["max_projects"]

        # Log the event
        event = SubscriptionEvent(
            organization_id=organization.id,
            event_type=SubscriptionEventType.TRIAL_CONVERTED.value,
            previous_tier=previous_tier,
            new_tier=tier,
            previous_status=previous_trial_status,
            new_status=SubscriptionStatus.ACTIVE.value,
            triggered_by=triggered_by,
            event_metadata={
                "converted_at": now.isoformat(),
            },
        )
        self.db.add(event)
        await self.db.flush()

        return organization

    async def get_expiring_trials(
        self,
        days_until_expiry: int = 3,
    ) -> list[Organization]:
        """Get organizations with trials expiring within given days.

        Args:
            days_until_expiry: Number of days from now to check

        Returns:
            List of organizations with expiring trials
        """
        now = datetime.now(UTC)
        expiry_threshold = now + timedelta(days=days_until_expiry)

        result = await self.db.execute(
            select(Organization).where(
                and_(
                    Organization.trial_status == TrialStatus.ACTIVE.value,
                    Organization.trial_ends_at <= expiry_threshold,
                    Organization.trial_ends_at > now,
                )
            )
        )
        return list(result.scalars().all())

    async def get_expired_trials(self, lock: bool = False) -> list[Organization]:
        """Get organizations with trials that have expired but not been processed.

        Args:
            lock: If True, use SELECT FOR UPDATE SKIP LOCKED to prevent
                  concurrent workers from processing the same org.

        Returns:
            List of organizations with expired trials needing processing
        """
        now = datetime.now(UTC)

        query = select(Organization).where(
            and_(
                Organization.trial_status == TrialStatus.ACTIVE.value,
                Organization.trial_ends_at <= now,
            )
        )
        if lock:
            query = query.with_for_update(skip_locked=True)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_organization_trial_status(
        self,
        organization: Organization,
    ) -> dict:
        """Get detailed trial status for an organization.

        Args:
            organization: The organization to get status for

        Returns:
            Dictionary with trial status details
        """
        return {
            "trial_status": organization.trial_status,
            "is_trial_active": organization.is_trial_active,
            "trial_started_at": (
                organization.trial_started_at.isoformat()
                if organization.trial_started_at
                else None
            ),
            "trial_ends_at": (
                organization.trial_ends_at.isoformat()
                if organization.trial_ends_at
                else None
            ),
            "trial_days_remaining": organization.trial_days_remaining,
            "can_access_features": organization.can_access_features,
            "current_tier": organization.tier,
            "max_members": organization.max_members,
            "max_projects": organization.max_projects,
            "was_extended": organization.trial_extended_by is not None,
        }

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
