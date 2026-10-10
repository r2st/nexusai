"""GB053: M18 testing — SubscriptionService and TrialService error paths and boundaries."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.organization import Organization, OrganizationTier
from app.models.subscription import SubscriptionStatus, TrialStatus
from app.services.subscription import SubscriptionService
from app.services.trial import TrialService


def _make_org(**overrides):
    defaults = dict(
        id=str(uuid4()),
        tenant_id=str(uuid4()),
        name="Test Org",
        slug="test-org",
        tier=OrganizationTier.FREE.value,
        trial_status=TrialStatus.NONE.value,
        subscription_status=SubscriptionStatus.NONE.value,
        max_members=5,
        max_projects=3,
        current_member_count=1,
        current_project_count=0,
        subscription_cancel_at_period_end=False,
        trial_started_at=None,
        trial_ends_at=None,
        trial_extended_by=None,
        trial_extension_reason=None,
        subscription_started_at=None,
    )
    defaults.update(overrides)
    org = MagicMock(spec=Organization)
    for k, v in defaults.items():
        setattr(org, k, v)
    org.is_trial_active = defaults["trial_status"] == TrialStatus.ACTIVE.value
    org.has_active_subscription = defaults["subscription_status"] == SubscriptionStatus.ACTIVE.value
    org.can_access_features = org.is_trial_active or org.has_active_subscription
    org.is_at_member_limit = defaults["current_member_count"] >= defaults["max_members"]
    org.is_at_project_limit = defaults["current_project_count"] >= defaults["max_projects"]
    org.member_usage_percentage = (defaults["current_member_count"] / defaults["max_members"]) * 100 if defaults["max_members"] > 0 else 100.0
    org.project_usage_percentage = (defaults["current_project_count"] / defaults["max_projects"]) * 100 if defaults["max_projects"] > 0 else 100.0
    return org


class TestSubscriptionServiceCheckLimits:
    @pytest.fixture
    def service(self):
        db = AsyncMock()
        return SubscriptionService(db)

    @pytest.mark.asyncio
    async def test_member_limit_not_reached(self, service):
        org = _make_org(current_member_count=3, max_members=10)
        ok, msg = await service.check_member_limit(org)
        assert ok is True
        assert msg == ""

    @pytest.mark.asyncio
    async def test_member_limit_reached(self, service):
        org = _make_org(current_member_count=10, max_members=10)
        ok, msg = await service.check_member_limit(org)
        assert ok is False
        assert "maximum of 10" in msg

    @pytest.mark.asyncio
    async def test_member_limit_exceeded(self, service):
        org = _make_org(current_member_count=11, max_members=10)
        ok, msg = await service.check_member_limit(org)
        assert ok is False

    @pytest.mark.asyncio
    async def test_project_limit_not_reached(self, service):
        org = _make_org(current_project_count=1, max_projects=5)
        ok, msg = await service.check_project_limit(org)
        assert ok is True

    @pytest.mark.asyncio
    async def test_project_limit_reached(self, service):
        org = _make_org(current_project_count=5, max_projects=5)
        ok, msg = await service.check_project_limit(org)
        assert ok is False
        assert "maximum of 5" in msg

    @pytest.mark.asyncio
    async def test_zero_member_limit_always_blocked(self, service):
        org = _make_org(current_member_count=0, max_members=0)
        ok, msg = await service.check_member_limit(org)
        assert ok is False
        assert "maximum of 0" in msg


class TestSubscriptionServiceCancelResume:
    @pytest.fixture
    def service(self):
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        return SubscriptionService(db)

    @pytest.mark.asyncio
    async def test_cancel_active_at_period_end(self, service):
        org = _make_org(subscription_status=SubscriptionStatus.ACTIVE.value)
        result = await service.cancel_subscription(org, at_period_end=True, triggered_by="user-1")
        assert result.subscription_cancel_at_period_end is True
        assert result.subscription_status == SubscriptionStatus.ACTIVE.value

    @pytest.mark.asyncio
    async def test_cancel_active_immediate(self, service):
        org = _make_org(subscription_status=SubscriptionStatus.ACTIVE.value)
        result = await service.cancel_subscription(org, at_period_end=False, triggered_by="user-1")
        assert result.subscription_status == SubscriptionStatus.CANCELED.value
        assert result.tier == OrganizationTier.FREE.value

    @pytest.mark.asyncio
    async def test_cancel_past_due(self, service):
        org = _make_org(subscription_status=SubscriptionStatus.PAST_DUE.value)
        result = await service.cancel_subscription(org, at_period_end=False, triggered_by="user-1")
        assert result.subscription_status == SubscriptionStatus.CANCELED.value

    @pytest.mark.asyncio
    async def test_cancel_paused(self, service):
        org = _make_org(subscription_status=SubscriptionStatus.PAUSED.value)
        result = await service.cancel_subscription(org, at_period_end=False, triggered_by="user-1")
        assert result.subscription_status == SubscriptionStatus.CANCELED.value

    @pytest.mark.asyncio
    async def test_cancel_none_raises(self, service):
        org = _make_org(subscription_status=SubscriptionStatus.NONE.value)
        with pytest.raises(ValueError, match="active, past_due, or paused"):
            await service.cancel_subscription(org, at_period_end=False, triggered_by="user-1")

    @pytest.mark.asyncio
    async def test_cancel_already_canceled_raises(self, service):
        org = _make_org(subscription_status=SubscriptionStatus.CANCELED.value)
        with pytest.raises(ValueError):
            await service.cancel_subscription(org, at_period_end=False, triggered_by="user-1")

    @pytest.mark.asyncio
    async def test_resume_cancel_at_period_end(self, service):
        org = _make_org(
            subscription_status=SubscriptionStatus.ACTIVE.value,
            subscription_cancel_at_period_end=True,
        )
        result = await service.resume_subscription(org, triggered_by="user-1")
        assert result.subscription_cancel_at_period_end is False

    @pytest.mark.asyncio
    async def test_resume_paused(self, service):
        org = _make_org(subscription_status=SubscriptionStatus.PAUSED.value)
        result = await service.resume_subscription(org, triggered_by="user-1")
        assert result.subscription_status == SubscriptionStatus.ACTIVE.value

    @pytest.mark.asyncio
    async def test_resume_past_due(self, service):
        org = _make_org(subscription_status=SubscriptionStatus.PAST_DUE.value)
        result = await service.resume_subscription(org, triggered_by="user-1")
        assert result.subscription_status == SubscriptionStatus.ACTIVE.value

    @pytest.mark.asyncio
    async def test_resume_none_raises(self, service):
        org = _make_org(subscription_status=SubscriptionStatus.NONE.value)
        with pytest.raises(ValueError, match="not in a resumable state"):
            await service.resume_subscription(org, triggered_by="user-1")

    @pytest.mark.asyncio
    async def test_resume_canceled_raises(self, service):
        org = _make_org(subscription_status=SubscriptionStatus.CANCELED.value)
        with pytest.raises(ValueError):
            await service.resume_subscription(org, triggered_by="user-1")


class TestSubscriptionServiceTierLimits:
    def test_free_tier_limits(self):
        db = AsyncMock()
        svc = SubscriptionService(db)
        limits = svc._get_tier_limits(OrganizationTier.FREE.value)
        assert "max_members" in limits
        assert "max_projects" in limits

    def test_unknown_tier_defaults_to_free(self):
        db = AsyncMock()
        svc = SubscriptionService(db)
        limits = svc._get_tier_limits("nonexistent_tier")
        free_limits = svc._get_tier_limits(OrganizationTier.FREE.value)
        assert limits == free_limits

    def test_enterprise_tier_has_higher_limits(self):
        db = AsyncMock()
        svc = SubscriptionService(db)
        free = svc._get_tier_limits(OrganizationTier.FREE.value)
        enterprise = svc._get_tier_limits(OrganizationTier.ENTERPRISE.value)
        assert enterprise["max_members"] >= free["max_members"]
        assert enterprise["max_projects"] >= free["max_projects"]


class TestTrialServiceLifecycle:
    @pytest.fixture
    def service(self):
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        return TrialService(db)

    @pytest.mark.asyncio
    async def test_start_trial_success(self, service):
        org = _make_org()
        result = await service.start_trial(org, triggered_by="user-1")
        assert result.trial_status == TrialStatus.ACTIVE.value
        assert result.trial_started_at is not None
        assert result.trial_ends_at is not None

    @pytest.mark.asyncio
    async def test_start_trial_already_started_raises(self, service):
        org = _make_org(trial_status=TrialStatus.ACTIVE.value)
        with pytest.raises(ValueError, match="already started"):
            await service.start_trial(org)

    @pytest.mark.asyncio
    async def test_start_trial_expired_raises(self, service):
        org = _make_org(trial_status=TrialStatus.EXPIRED.value)
        with pytest.raises(ValueError, match="already started"):
            await service.start_trial(org)

    @pytest.mark.asyncio
    async def test_start_trial_active_subscription_raises(self, service):
        org = _make_org(subscription_status=SubscriptionStatus.ACTIVE.value)
        with pytest.raises(ValueError, match="active subscription"):
            await service.start_trial(org)

    @pytest.mark.asyncio
    async def test_extend_trial_success(self, service):
        now = datetime.now(UTC)
        end = now + timedelta(days=7)
        org = _make_org(
            trial_status=TrialStatus.ACTIVE.value,
            trial_ends_at=end,
        )
        result = await service.extend_trial(org, days=7, reason="Demo", extended_by="admin-1")
        assert result.trial_ends_at == end + timedelta(days=7)
        assert result.trial_extended_by == "admin-1"
        assert result.trial_extension_reason == "Demo"

    @pytest.mark.asyncio
    async def test_extend_trial_not_active_raises(self, service):
        org = _make_org(trial_status=TrialStatus.NONE.value)
        with pytest.raises(ValueError, match="does not have an active trial"):
            await service.extend_trial(org, days=7, reason="test", extended_by="admin")

    @pytest.mark.asyncio
    async def test_extend_trial_no_end_date_raises(self, service):
        org = _make_org(trial_status=TrialStatus.ACTIVE.value, trial_ends_at=None)
        with pytest.raises(ValueError, match="end date is not set"):
            await service.extend_trial(org, days=7, reason="test", extended_by="admin")

    @pytest.mark.asyncio
    async def test_expire_trial_success(self, service):
        org = _make_org(trial_status=TrialStatus.ACTIVE.value, tier="professional")
        result = await service.expire_trial(org)
        assert result.trial_status == TrialStatus.EXPIRED.value
        assert result.tier == OrganizationTier.FREE.value

    @pytest.mark.asyncio
    async def test_expire_trial_not_active_raises(self, service):
        org = _make_org(trial_status=TrialStatus.NONE.value)
        with pytest.raises(ValueError, match="does not have an active trial"):
            await service.expire_trial(org)

    @pytest.mark.asyncio
    async def test_expire_already_expired_raises(self, service):
        org = _make_org(trial_status=TrialStatus.EXPIRED.value)
        with pytest.raises(ValueError):
            await service.expire_trial(org)

    @pytest.mark.asyncio
    async def test_convert_active_trial(self, service):
        org = _make_org(trial_status=TrialStatus.ACTIVE.value)
        result = await service.convert_trial_to_subscription(
            org, tier=OrganizationTier.PROFESSIONAL.value, triggered_by="user-1"
        )
        assert result.trial_status == TrialStatus.CONVERTED.value
        assert result.subscription_status == SubscriptionStatus.ACTIVE.value
        assert result.tier == OrganizationTier.PROFESSIONAL.value

    @pytest.mark.asyncio
    async def test_convert_expired_trial(self, service):
        org = _make_org(trial_status=TrialStatus.EXPIRED.value)
        result = await service.convert_trial_to_subscription(
            org, tier=OrganizationTier.STARTER.value, triggered_by="user-1"
        )
        assert result.trial_status == TrialStatus.CONVERTED.value

    @pytest.mark.asyncio
    async def test_convert_no_trial_raises(self, service):
        org = _make_org(trial_status=TrialStatus.NONE.value)
        with pytest.raises(ValueError, match="active or expired trial"):
            await service.convert_trial_to_subscription(
                org, tier="pro", triggered_by="user-1"
            )

    @pytest.mark.asyncio
    async def test_convert_already_converted_raises(self, service):
        org = _make_org(trial_status=TrialStatus.CONVERTED.value)
        with pytest.raises(ValueError):
            await service.convert_trial_to_subscription(
                org, tier="pro", triggered_by="user-1"
            )


class TestTrialServiceTierLimits:
    def test_unknown_tier_defaults_to_free(self):
        db = AsyncMock()
        svc = TrialService(db)
        limits = svc._get_tier_limits("bogus_tier")
        free_limits = svc._get_tier_limits(OrganizationTier.FREE.value)
        assert limits == free_limits


class TestOrganizationProperties:
    def test_is_trial_active_with_future_end(self):
        org = Organization()
        org.trial_status = TrialStatus.ACTIVE.value
        org.trial_ends_at = datetime.now(UTC) + timedelta(days=5)
        assert org.is_trial_active is True

    def test_is_trial_active_with_past_end(self):
        org = Organization()
        org.trial_status = TrialStatus.ACTIVE.value
        org.trial_ends_at = datetime.now(UTC) - timedelta(days=1)
        assert org.is_trial_active is False

    def test_is_trial_active_not_active_status(self):
        org = Organization()
        org.trial_status = TrialStatus.NONE.value
        assert org.is_trial_active is False

    def test_is_trial_active_no_end_date(self):
        org = Organization()
        org.trial_status = TrialStatus.ACTIVE.value
        org.trial_ends_at = None
        assert org.is_trial_active is False

    def test_trial_days_remaining_active(self):
        org = Organization()
        org.trial_status = TrialStatus.ACTIVE.value
        org.trial_ends_at = datetime.now(UTC) + timedelta(days=5, hours=12)
        assert org.trial_days_remaining >= 5

    def test_trial_days_remaining_expired(self):
        org = Organization()
        org.trial_status = TrialStatus.ACTIVE.value
        org.trial_ends_at = datetime.now(UTC) - timedelta(days=1)
        assert org.trial_days_remaining == 0

    def test_trial_days_remaining_not_active(self):
        org = Organization()
        org.trial_status = TrialStatus.NONE.value
        assert org.trial_days_remaining == 0

    def test_has_active_subscription(self):
        org = Organization()
        org.subscription_status = SubscriptionStatus.ACTIVE.value
        assert org.has_active_subscription is True

    def test_no_active_subscription(self):
        org = Organization()
        org.subscription_status = SubscriptionStatus.CANCELED.value
        assert org.has_active_subscription is False

    def test_can_access_features_via_trial(self):
        org = Organization()
        org.trial_status = TrialStatus.ACTIVE.value
        org.trial_ends_at = datetime.now(UTC) + timedelta(days=5)
        org.subscription_status = SubscriptionStatus.NONE.value
        assert org.can_access_features is True

    def test_can_access_features_via_subscription(self):
        org = Organization()
        org.trial_status = TrialStatus.NONE.value
        org.subscription_status = SubscriptionStatus.ACTIVE.value
        assert org.can_access_features is True

    def test_cannot_access_features_free(self):
        org = Organization()
        org.trial_status = TrialStatus.NONE.value
        org.subscription_status = SubscriptionStatus.NONE.value
        assert org.can_access_features is False

    def test_member_usage_percentage(self):
        org = Organization()
        org.current_member_count = 3
        org.max_members = 10
        assert org.member_usage_percentage == pytest.approx(30.0)

    def test_member_usage_percentage_zero_max(self):
        org = Organization()
        org.current_member_count = 1
        org.max_members = 0
        assert org.member_usage_percentage == 100.0

    def test_project_usage_percentage_zero_max(self):
        org = Organization()
        org.current_project_count = 0
        org.max_projects = 0
        assert org.project_usage_percentage == 100.0

    def test_is_at_member_limit(self):
        org = Organization()
        org.current_member_count = 5
        org.max_members = 5
        assert org.is_at_member_limit is True

    def test_not_at_member_limit(self):
        org = Organization()
        org.current_member_count = 3
        org.max_members = 5
        assert org.is_at_member_limit is False
