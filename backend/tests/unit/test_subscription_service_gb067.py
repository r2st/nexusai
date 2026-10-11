"""GB067: Tests for services/subscription.py — tier changes, cancellation, and resumption state machine."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.config import settings
from app.models.organization import Organization, OrganizationTier
from app.models.subscription import SubscriptionStatus, TrialStatus
from app.services.subscription import SubscriptionService


def _make_org(**overrides) -> Organization:
    defaults = {
        "id": str(uuid4()),
        "tenant_id": str(uuid4()),
        "name": "Test Org",
        "slug": "test-org",
        "tier": OrganizationTier.PROFESSIONAL.value,
        "max_members": 25,
        "max_projects": 50,
        "current_member_count": 5,
        "current_project_count": 3,
        "subscription_status": SubscriptionStatus.ACTIVE.value,
        "subscription_cancel_at_period_end": False,
        "subscription_started_at": datetime.now(UTC) - timedelta(days=30),
        "subscription_ends_at": datetime.now(UTC) + timedelta(days=30),
        "trial_status": TrialStatus.NONE.value,
        "trial_started_at": None,
        "trial_ends_at": None,
        "trial_extended_by": None,
        "trial_extension_reason": None,
    }
    defaults.update(overrides)
    org = MagicMock(spec=Organization)
    for k, v in defaults.items():
        setattr(org, k, v)
    return org


def _make_service() -> SubscriptionService:
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    return SubscriptionService(db)


# ---------------------------------------------------------------------------
# check_member_limit / check_project_limit
# ---------------------------------------------------------------------------

class TestLimitChecks:
    @pytest.mark.asyncio
    async def test_member_limit_not_reached(self):
        svc = _make_service()
        org = _make_org(current_member_count=3, max_members=10)
        can, msg = await svc.check_member_limit(org)
        assert can is True
        assert msg == ""

    @pytest.mark.asyncio
    async def test_member_limit_reached(self):
        svc = _make_service()
        org = _make_org(current_member_count=10, max_members=10)
        can, msg = await svc.check_member_limit(org)
        assert can is False
        assert "maximum" in msg.lower()

    @pytest.mark.asyncio
    async def test_member_limit_exceeded(self):
        svc = _make_service()
        org = _make_org(current_member_count=15, max_members=10)
        can, msg = await svc.check_member_limit(org)
        assert can is False

    @pytest.mark.asyncio
    async def test_project_limit_not_reached(self):
        svc = _make_service()
        org = _make_org(current_project_count=1, max_projects=5)
        can, msg = await svc.check_project_limit(org)
        assert can is True

    @pytest.mark.asyncio
    async def test_project_limit_reached(self):
        svc = _make_service()
        org = _make_org(current_project_count=5, max_projects=5)
        can, msg = await svc.check_project_limit(org)
        assert can is False


# ---------------------------------------------------------------------------
# change_tier
# ---------------------------------------------------------------------------

class TestChangeTier:
    @pytest.mark.asyncio
    async def test_change_to_valid_tier(self):
        svc = _make_service()
        org = _make_org(tier=OrganizationTier.FREE.value)
        result = await svc.change_tier(org, new_tier="starter", triggered_by="admin-1")
        assert org.tier == "starter"
        assert org.max_members == settings.STARTER_TIER_MAX_MEMBERS
        assert org.max_projects == settings.STARTER_TIER_MAX_PROJECTS
        svc.db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_change_to_invalid_tier_raises(self):
        svc = _make_service()
        org = _make_org(tier=OrganizationTier.FREE.value)
        with pytest.raises(ValueError, match="Invalid tier"):
            await svc.change_tier(org, new_tier="platinum", triggered_by="admin-1")

    @pytest.mark.asyncio
    async def test_change_to_same_tier_raises(self):
        svc = _make_service()
        org = _make_org(tier=OrganizationTier.PROFESSIONAL.value)
        with pytest.raises(ValueError, match="already on"):
            await svc.change_tier(
                org, new_tier=OrganizationTier.PROFESSIONAL.value, triggered_by="admin-1"
            )

    @pytest.mark.asyncio
    async def test_change_tier_enterprise_limits(self):
        svc = _make_service()
        org = _make_org(tier=OrganizationTier.FREE.value)
        await svc.change_tier(org, new_tier="enterprise", triggered_by="admin-1")
        assert org.max_members == settings.ENTERPRISE_TIER_MAX_MEMBERS
        assert org.max_projects == settings.ENTERPRISE_TIER_MAX_PROJECTS

    @pytest.mark.asyncio
    async def test_change_tier_downgrade(self):
        svc = _make_service()
        org = _make_org(tier=OrganizationTier.ENTERPRISE.value)
        await svc.change_tier(org, new_tier="free", triggered_by="admin-1")
        assert org.tier == "free"
        assert org.max_members == settings.FREE_TIER_MAX_MEMBERS


# ---------------------------------------------------------------------------
# cancel_subscription
# ---------------------------------------------------------------------------

class TestCancelSubscription:
    @pytest.mark.asyncio
    async def test_cancel_at_period_end(self):
        svc = _make_service()
        org = _make_org(subscription_status=SubscriptionStatus.ACTIVE.value)
        await svc.cancel_subscription(org, at_period_end=True, triggered_by="user-1")
        assert org.subscription_cancel_at_period_end is True
        assert org.subscription_status == SubscriptionStatus.ACTIVE.value

    @pytest.mark.asyncio
    async def test_cancel_immediately(self):
        svc = _make_service()
        org = _make_org(subscription_status=SubscriptionStatus.ACTIVE.value)
        await svc.cancel_subscription(org, at_period_end=False, triggered_by="user-1")
        assert org.subscription_status == SubscriptionStatus.CANCELED.value
        assert org.tier == OrganizationTier.FREE.value

    @pytest.mark.asyncio
    async def test_cancel_past_due(self):
        svc = _make_service()
        org = _make_org(subscription_status=SubscriptionStatus.PAST_DUE.value)
        await svc.cancel_subscription(org, at_period_end=False, triggered_by="user-1")
        assert org.subscription_status == SubscriptionStatus.CANCELED.value

    @pytest.mark.asyncio
    async def test_cancel_paused(self):
        svc = _make_service()
        org = _make_org(subscription_status=SubscriptionStatus.PAUSED.value)
        await svc.cancel_subscription(org, at_period_end=False, triggered_by="user-1")
        assert org.subscription_status == SubscriptionStatus.CANCELED.value

    @pytest.mark.asyncio
    async def test_cancel_already_canceled_raises(self):
        svc = _make_service()
        org = _make_org(subscription_status=SubscriptionStatus.CANCELED.value)
        with pytest.raises(ValueError, match="active, past_due, or paused"):
            await svc.cancel_subscription(org, at_period_end=True, triggered_by="user-1")

    @pytest.mark.asyncio
    async def test_cancel_none_status_raises(self):
        svc = _make_service()
        org = _make_org(subscription_status=SubscriptionStatus.NONE.value)
        with pytest.raises(ValueError):
            await svc.cancel_subscription(org, at_period_end=True, triggered_by="user-1")

    @pytest.mark.asyncio
    async def test_immediate_cancel_downgrades_limits(self):
        svc = _make_service()
        org = _make_org(
            subscription_status=SubscriptionStatus.ACTIVE.value,
            tier=OrganizationTier.ENTERPRISE.value,
        )
        await svc.cancel_subscription(org, at_period_end=False, triggered_by="user-1")
        assert org.max_members == settings.FREE_TIER_MAX_MEMBERS
        assert org.max_projects == settings.FREE_TIER_MAX_PROJECTS


# ---------------------------------------------------------------------------
# resume_subscription
# ---------------------------------------------------------------------------

class TestResumeSubscription:
    @pytest.mark.asyncio
    async def test_resume_cancel_at_period_end(self):
        svc = _make_service()
        org = _make_org(
            subscription_status=SubscriptionStatus.ACTIVE.value,
            subscription_cancel_at_period_end=True,
        )
        await svc.resume_subscription(org, triggered_by="user-1")
        assert org.subscription_cancel_at_period_end is False

    @pytest.mark.asyncio
    async def test_resume_paused(self):
        svc = _make_service()
        org = _make_org(
            subscription_status=SubscriptionStatus.PAUSED.value,
            subscription_cancel_at_period_end=False,
        )
        await svc.resume_subscription(org, triggered_by="user-1")
        assert org.subscription_status == SubscriptionStatus.ACTIVE.value

    @pytest.mark.asyncio
    async def test_resume_past_due(self):
        svc = _make_service()
        org = _make_org(
            subscription_status=SubscriptionStatus.PAST_DUE.value,
            subscription_cancel_at_period_end=False,
        )
        await svc.resume_subscription(org, triggered_by="user-1")
        assert org.subscription_status == SubscriptionStatus.ACTIVE.value

    @pytest.mark.asyncio
    async def test_resume_active_not_pending_cancel_raises(self):
        svc = _make_service()
        org = _make_org(
            subscription_status=SubscriptionStatus.ACTIVE.value,
            subscription_cancel_at_period_end=False,
        )
        with pytest.raises(ValueError, match="not in a resumable state"):
            await svc.resume_subscription(org, triggered_by="user-1")

    @pytest.mark.asyncio
    async def test_resume_canceled_raises(self):
        svc = _make_service()
        org = _make_org(
            subscription_status=SubscriptionStatus.CANCELED.value,
            subscription_cancel_at_period_end=False,
        )
        with pytest.raises(ValueError, match="not in a resumable state"):
            await svc.resume_subscription(org, triggered_by="user-1")


# ---------------------------------------------------------------------------
# _get_tier_limits (private helper)
# ---------------------------------------------------------------------------

class TestTierLimits:
    def test_free_tier(self):
        svc = _make_service()
        limits = svc._get_tier_limits("free")
        assert limits["max_members"] == settings.FREE_TIER_MAX_MEMBERS
        assert limits["max_projects"] == settings.FREE_TIER_MAX_PROJECTS

    def test_enterprise_tier(self):
        svc = _make_service()
        limits = svc._get_tier_limits("enterprise")
        assert limits["max_members"] == settings.ENTERPRISE_TIER_MAX_MEMBERS

    def test_unknown_tier_defaults_to_free(self):
        svc = _make_service()
        limits = svc._get_tier_limits("nonexistent")
        assert limits == svc._get_tier_limits("free")


# ---------------------------------------------------------------------------
# get_usage_summary
# ---------------------------------------------------------------------------

class TestGetUsageSummary:
    @pytest.mark.asyncio
    async def test_returns_expected_keys(self):
        svc = _make_service()
        org = _make_org()
        org.member_usage_percentage = 50.0
        org.project_usage_percentage = 30.0
        org.is_at_member_limit = False
        org.is_at_project_limit = False
        org.can_access_features = True
        org.is_trial_active = False
        org.has_active_subscription = True
        result = await svc.get_usage_summary(org)
        assert "members" in result
        assert "projects" in result
        assert "tier" in result
        assert result["subscription_active"] is True
        assert result["trial_active"] is False
