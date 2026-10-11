"""GB067: API contract tests for subscription/trial endpoints — request/response validation."""

import pytest
from pydantic import ValidationError

from app.api.subscriptions import (
    CancelSubscriptionRequest,
    ChangeTierRequest,
    ChangeTierResponse,
    UsageSummaryResponse,
)
from app.api.trials import (
    ExtendTrialRequest,
    ExtendTrialResponse,
    TrialStatusResponse,
    TrialStatisticsResponse,
)


# ---------------------------------------------------------------------------
# Subscription request models
# ---------------------------------------------------------------------------

class TestCancelSubscriptionRequest:
    def test_default_at_period_end(self):
        req = CancelSubscriptionRequest()
        assert req.at_period_end is True

    def test_explicit_false(self):
        req = CancelSubscriptionRequest(at_period_end=False)
        assert req.at_period_end is False


class TestChangeTierRequest:
    def test_valid(self):
        req = ChangeTierRequest(tier="professional")
        assert req.tier == "professional"

    def test_tier_required(self):
        with pytest.raises(ValidationError):
            ChangeTierRequest()


class TestChangeTierResponse:
    def test_all_fields(self):
        resp = ChangeTierResponse(
            message="Tier changed",
            previous_tier="free",
            new_tier="starter",
            new_max_members=15,
            new_max_projects=25,
        )
        assert resp.previous_tier == "free"
        assert resp.new_max_members == 15


# ---------------------------------------------------------------------------
# Usage summary response
# ---------------------------------------------------------------------------

class TestUsageSummaryResponse:
    def test_full_response(self):
        resp = UsageSummaryResponse(
            members=UsageSummaryResponse.UsageDetail(
                current=5, max=10, percentage=50.0, at_limit=False
            ),
            projects=UsageSummaryResponse.UsageDetail(
                current=3, max=5, percentage=60.0, at_limit=False
            ),
            tier="professional",
            can_access_features=True,
            trial_active=False,
            subscription_active=True,
        )
        assert resp.members.current == 5
        assert resp.tier == "professional"

    def test_usage_detail_at_limit(self):
        detail = UsageSummaryResponse.UsageDetail(
            current=10, max=10, percentage=100.0, at_limit=True
        )
        assert detail.at_limit is True


# ---------------------------------------------------------------------------
# Trial request/response models
# ---------------------------------------------------------------------------

class TestExtendTrialRequest:
    def test_valid(self):
        req = ExtendTrialRequest(days=14, reason="Sales demo")
        assert req.days == 14
        assert req.reason == "Sales demo"

    def test_days_required(self):
        with pytest.raises(ValidationError):
            ExtendTrialRequest(reason="test")

    def test_reason_required(self):
        with pytest.raises(ValidationError):
            ExtendTrialRequest(days=7)


class TestExtendTrialResponse:
    def test_all_fields(self):
        resp = ExtendTrialResponse(
            message="Trial extended by 14 days",
            new_end_date="2026-11-01T00:00:00Z",
            days_added=14,
        )
        assert resp.days_added == 14


class TestTrialStatusResponse:
    def test_full_response(self):
        resp = TrialStatusResponse(
            trial_status="active",
            is_trial_active=True,
            trial_started_at="2026-10-01T00:00:00Z",
            trial_ends_at="2026-10-15T00:00:00Z",
            trial_days_remaining=5,
            can_access_features=True,
            current_tier="professional",
            max_members=25,
            max_projects=50,
            was_extended=False,
        )
        assert resp.is_trial_active is True
        assert resp.trial_days_remaining == 5

    def test_no_trial(self):
        resp = TrialStatusResponse(
            trial_status="none",
            is_trial_active=False,
            trial_started_at=None,
            trial_ends_at=None,
            trial_days_remaining=0,
            can_access_features=False,
            current_tier="free",
            max_members=5,
            max_projects=3,
            was_extended=False,
        )
        assert resp.trial_started_at is None


class TestTrialStatisticsResponse:
    def test_all_fields(self):
        resp = TrialStatisticsResponse(
            active=10,
            expired=5,
            converted=3,
            expiring_soon=2,
            conversion_rate=37.5,
            total_trials=18,
        )
        assert resp.conversion_rate == 37.5
        assert resp.total_trials == 18

    def test_zero_values(self):
        resp = TrialStatisticsResponse(
            active=0,
            expired=0,
            converted=0,
            expiring_soon=0,
            conversion_rate=0.0,
            total_trials=0,
        )
        assert resp.active == 0
