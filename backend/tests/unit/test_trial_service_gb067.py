"""GB067: Tests for services/trial.py — trial lifecycle state machine."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.config import settings
from app.models.organization import Organization, OrganizationTier
from app.models.subscription import SubscriptionStatus, TrialStatus
from app.services.trial import TrialService


def _make_org(**overrides) -> Organization:
    defaults = {
        "id": str(uuid4()),
        "tenant_id": str(uuid4()),
        "name": "Test Org",
        "slug": "test-org",
        "tier": OrganizationTier.FREE.value,
        "max_members": 5,
        "max_projects": 3,
        "current_member_count": 1,
        "current_project_count": 0,
        "subscription_status": SubscriptionStatus.NONE.value,
        "subscription_cancel_at_period_end": False,
        "subscription_started_at": None,
        "subscription_ends_at": None,
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


def _make_service() -> TrialService:
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    return TrialService(db)


# ---------------------------------------------------------------------------
# start_trial
# ---------------------------------------------------------------------------

class TestStartTrial:
    @pytest.mark.asyncio
    async def test_start_trial_success(self):
        svc = _make_service()
        org = _make_org()
        result = await svc.start_trial(org, triggered_by="user-1")
        assert org.trial_status == TrialStatus.ACTIVE.value
        assert org.trial_started_at is not None
        assert org.trial_ends_at is not None
        assert org.tier == settings.TRIAL_TIER
        assert org.max_members == settings.TRIAL_MAX_MEMBERS
        svc.db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_trial_already_had_trial_raises(self):
        svc = _make_service()
        org = _make_org(trial_status=TrialStatus.ACTIVE.value)
        with pytest.raises(ValueError, match="already started"):
            await svc.start_trial(org, triggered_by="user-1")

    @pytest.mark.asyncio
    async def test_start_trial_expired_status_raises(self):
        svc = _make_service()
        org = _make_org(trial_status=TrialStatus.EXPIRED.value)
        with pytest.raises(ValueError, match="already started"):
            await svc.start_trial(org, triggered_by="user-1")

    @pytest.mark.asyncio
    async def test_start_trial_converted_status_raises(self):
        svc = _make_service()
        org = _make_org(trial_status=TrialStatus.CONVERTED.value)
        with pytest.raises(ValueError, match="already started"):
            await svc.start_trial(org, triggered_by="user-1")

    @pytest.mark.asyncio
    async def test_start_trial_with_active_subscription_raises(self):
        svc = _make_service()
        org = _make_org(subscription_status=SubscriptionStatus.ACTIVE.value)
        with pytest.raises(ValueError, match="active subscription"):
            await svc.start_trial(org, triggered_by="user-1")

    @pytest.mark.asyncio
    async def test_start_trial_sets_correct_duration(self):
        svc = _make_service()
        org = _make_org()
        await svc.start_trial(org, triggered_by="user-1")
        delta = org.trial_ends_at - org.trial_started_at
        assert abs(delta.days - settings.TRIAL_DURATION_DAYS) <= 1

    @pytest.mark.asyncio
    async def test_start_trial_no_triggered_by(self):
        svc = _make_service()
        org = _make_org()
        await svc.start_trial(org, triggered_by=None)
        assert org.trial_status == TrialStatus.ACTIVE.value


# ---------------------------------------------------------------------------
# extend_trial
# ---------------------------------------------------------------------------

class TestExtendTrial:
    @pytest.mark.asyncio
    async def test_extend_active_trial(self):
        svc = _make_service()
        ends_at = datetime.now(UTC) + timedelta(days=7)
        org = _make_org(
            trial_status=TrialStatus.ACTIVE.value,
            trial_ends_at=ends_at,
        )
        await svc.extend_trial(org, days=14, reason="Sales demo", extended_by="admin-1")
        assert org.trial_ends_at == ends_at + timedelta(days=14)
        assert org.trial_extended_by == "admin-1"
        assert org.trial_extension_reason == "Sales demo"

    @pytest.mark.asyncio
    async def test_extend_inactive_trial_raises(self):
        svc = _make_service()
        org = _make_org(trial_status=TrialStatus.NONE.value)
        with pytest.raises(ValueError, match="does not have an active trial"):
            await svc.extend_trial(org, days=7, reason="test", extended_by="admin")

    @pytest.mark.asyncio
    async def test_extend_expired_trial_raises(self):
        svc = _make_service()
        org = _make_org(trial_status=TrialStatus.EXPIRED.value)
        with pytest.raises(ValueError, match="does not have an active trial"):
            await svc.extend_trial(org, days=7, reason="test", extended_by="admin")

    @pytest.mark.asyncio
    async def test_extend_trial_without_end_date_raises(self):
        svc = _make_service()
        org = _make_org(
            trial_status=TrialStatus.ACTIVE.value,
            trial_ends_at=None,
        )
        with pytest.raises(ValueError, match="end date is not set"):
            await svc.extend_trial(org, days=7, reason="test", extended_by="admin")


# ---------------------------------------------------------------------------
# expire_trial
# ---------------------------------------------------------------------------

class TestExpireTrial:
    @pytest.mark.asyncio
    async def test_expire_active_trial(self):
        svc = _make_service()
        org = _make_org(
            trial_status=TrialStatus.ACTIVE.value,
            tier=OrganizationTier.PROFESSIONAL.value,
        )
        await svc.expire_trial(org, triggered_by="system")
        assert org.trial_status == TrialStatus.EXPIRED.value
        assert org.tier == OrganizationTier.FREE.value
        assert org.max_members == settings.FREE_TIER_MAX_MEMBERS
        assert org.max_projects == settings.FREE_TIER_MAX_PROJECTS

    @pytest.mark.asyncio
    async def test_expire_inactive_trial_raises(self):
        svc = _make_service()
        org = _make_org(trial_status=TrialStatus.NONE.value)
        with pytest.raises(ValueError, match="does not have an active trial"):
            await svc.expire_trial(org, triggered_by="system")

    @pytest.mark.asyncio
    async def test_expire_already_expired_raises(self):
        svc = _make_service()
        org = _make_org(trial_status=TrialStatus.EXPIRED.value)
        with pytest.raises(ValueError):
            await svc.expire_trial(org, triggered_by="system")

    @pytest.mark.asyncio
    async def test_expire_system_triggered(self):
        svc = _make_service()
        org = _make_org(trial_status=TrialStatus.ACTIVE.value)
        await svc.expire_trial(org, triggered_by=None)
        assert org.trial_status == TrialStatus.EXPIRED.value


# ---------------------------------------------------------------------------
# convert_trial_to_subscription
# ---------------------------------------------------------------------------

class TestConvertTrial:
    @pytest.mark.asyncio
    async def test_convert_active_trial(self):
        svc = _make_service()
        org = _make_org(trial_status=TrialStatus.ACTIVE.value)
        await svc.convert_trial_to_subscription(
            org, tier="professional", triggered_by="user-1"
        )
        assert org.trial_status == TrialStatus.CONVERTED.value
        assert org.subscription_status == SubscriptionStatus.ACTIVE.value
        assert org.tier == "professional"
        assert org.subscription_started_at is not None

    @pytest.mark.asyncio
    async def test_convert_expired_trial(self):
        svc = _make_service()
        org = _make_org(trial_status=TrialStatus.EXPIRED.value)
        await svc.convert_trial_to_subscription(
            org, tier="starter", triggered_by="user-1"
        )
        assert org.trial_status == TrialStatus.CONVERTED.value
        assert org.subscription_status == SubscriptionStatus.ACTIVE.value

    @pytest.mark.asyncio
    async def test_convert_none_trial_raises(self):
        svc = _make_service()
        org = _make_org(trial_status=TrialStatus.NONE.value)
        with pytest.raises(ValueError, match="active or expired trial"):
            await svc.convert_trial_to_subscription(
                org, tier="starter", triggered_by="user-1"
            )

    @pytest.mark.asyncio
    async def test_convert_already_converted_raises(self):
        svc = _make_service()
        org = _make_org(trial_status=TrialStatus.CONVERTED.value)
        with pytest.raises(ValueError, match="active or expired trial"):
            await svc.convert_trial_to_subscription(
                org, tier="starter", triggered_by="user-1"
            )

    @pytest.mark.asyncio
    async def test_convert_sets_tier_limits(self):
        svc = _make_service()
        org = _make_org(trial_status=TrialStatus.ACTIVE.value)
        await svc.convert_trial_to_subscription(
            org, tier="enterprise", triggered_by="user-1"
        )
        assert org.max_members == settings.ENTERPRISE_TIER_MAX_MEMBERS
        assert org.max_projects == settings.ENTERPRISE_TIER_MAX_PROJECTS


# ---------------------------------------------------------------------------
# Organization model properties
# ---------------------------------------------------------------------------

class TestOrganizationProperties:
    def test_is_trial_active_true(self):
        org = Organization()
        org.trial_status = TrialStatus.ACTIVE.value
        org.trial_ends_at = datetime.now(UTC) + timedelta(days=5)
        assert org.is_trial_active is True

    def test_is_trial_active_expired_date(self):
        org = Organization()
        org.trial_status = TrialStatus.ACTIVE.value
        org.trial_ends_at = datetime.now(UTC) - timedelta(hours=1)
        assert org.is_trial_active is False

    def test_is_trial_active_wrong_status(self):
        org = Organization()
        org.trial_status = TrialStatus.EXPIRED.value
        org.trial_ends_at = datetime.now(UTC) + timedelta(days=5)
        assert org.is_trial_active is False

    def test_is_trial_active_no_end_date(self):
        org = Organization()
        org.trial_status = TrialStatus.ACTIVE.value
        org.trial_ends_at = None
        assert org.is_trial_active is False

    def test_trial_days_remaining(self):
        org = Organization()
        org.trial_status = TrialStatus.ACTIVE.value
        org.trial_ends_at = datetime.now(UTC) + timedelta(days=3, hours=12)
        assert org.trial_days_remaining == 4  # ceil

    def test_trial_days_remaining_zero_when_not_active(self):
        org = Organization()
        org.trial_status = TrialStatus.NONE.value
        org.trial_ends_at = None
        assert org.trial_days_remaining == 0

    def test_has_active_subscription(self):
        org = Organization()
        org.subscription_status = SubscriptionStatus.ACTIVE.value
        assert org.has_active_subscription is True
        org.subscription_status = SubscriptionStatus.PAUSED.value
        assert org.has_active_subscription is False

    def test_can_access_features_with_trial(self):
        org = Organization()
        org.trial_status = TrialStatus.ACTIVE.value
        org.trial_ends_at = datetime.now(UTC) + timedelta(days=5)
        org.subscription_status = SubscriptionStatus.NONE.value
        assert org.can_access_features is True

    def test_can_access_features_with_subscription(self):
        org = Organization()
        org.trial_status = TrialStatus.NONE.value
        org.trial_ends_at = None
        org.subscription_status = SubscriptionStatus.ACTIVE.value
        assert org.can_access_features is True

    def test_cannot_access_features_free(self):
        org = Organization()
        org.trial_status = TrialStatus.NONE.value
        org.trial_ends_at = None
        org.subscription_status = SubscriptionStatus.NONE.value
        assert org.can_access_features is False

    def test_is_at_member_limit(self):
        org = Organization()
        org.current_member_count = 5
        org.max_members = 5
        assert org.is_at_member_limit is True
        org.current_member_count = 4
        assert org.is_at_member_limit is False

    def test_member_usage_percentage(self):
        org = Organization()
        org.current_member_count = 3
        org.max_members = 10
        assert org.member_usage_percentage == 30.0

    def test_member_usage_percentage_zero_max(self):
        org = Organization()
        org.current_member_count = 0
        org.max_members = 0
        assert org.member_usage_percentage == 100.0

    def test_project_usage_percentage(self):
        org = Organization()
        org.current_project_count = 2
        org.max_projects = 5
        assert org.project_usage_percentage == 40.0
