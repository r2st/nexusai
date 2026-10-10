"""GB053: M18 testing — CostTracker budget enforcement, edge cases, and reporting."""

from datetime import datetime, timedelta, UTC

import pytest

from app.services.llm_gateway.config import (
    CostConfig,
    GatewayConfig,
    ModelConfig,
    AllowlistConfig,
)
from app.services.llm_gateway.cost_tracker import CostTracker, CostEntry, CostReport


def _make_config(models=None, cost_enabled=True, budget_daily=100.0,
                 budget_user_daily=10.0, budget_user_monthly=100.0,
                 alert_threshold=0.8):
    return GatewayConfig(
        models=models or [
            ModelConfig(
                name="gpt-4",
                provider="openai",
                input_cost_per_1k=0.03,
                output_cost_per_1k=0.06,
            ),
            ModelConfig(
                name="gpt-3.5-turbo",
                provider="openai",
                input_cost_per_1k=0.0005,
                output_cost_per_1k=0.0015,
            ),
        ],
        cost=CostConfig(
            enabled=cost_enabled,
            budget_total_daily=budget_daily,
            budget_per_user_daily=budget_user_daily,
            budget_per_user_monthly=budget_user_monthly,
            alert_threshold=alert_threshold,
        ),
    )


class TestCalculateCost:
    def test_known_model_cost(self):
        ct = CostTracker(_make_config())
        cost = ct.calculate_cost("gpt-4", 1000, 500)
        expected = (1000 / 1000 * 0.03) + (500 / 1000 * 0.06)
        assert cost == pytest.approx(expected, abs=1e-6)

    def test_unknown_model_uses_defaults(self):
        ct = CostTracker(_make_config())
        cost = ct.calculate_cost("unknown-model", 1000, 1000)
        expected = (1000 / 1000 * 0.0005) + (1000 / 1000 * 0.0015)
        assert cost == pytest.approx(expected, abs=1e-6)

    def test_zero_tokens(self):
        ct = CostTracker(_make_config())
        cost = ct.calculate_cost("gpt-4", 0, 0)
        assert cost == 0.0

    def test_negative_tokens_clamped_to_zero(self):
        ct = CostTracker(_make_config())
        cost = ct.calculate_cost("gpt-4", -100, -50)
        assert cost == 0.0

    def test_free_model_zero_cost(self):
        config = _make_config(models=[
            ModelConfig(name="llama3", provider="ollama",
                        input_cost_per_1k=0.0, output_cost_per_1k=0.0),
        ])
        ct = CostTracker(config)
        cost = ct.calculate_cost("llama3", 10000, 5000)
        assert cost == 0.0


class TestRecordUsage:
    def test_record_creates_entry(self):
        ct = CostTracker(_make_config())
        entry = ct.record_usage(
            request_id="req-1",
            user_id="user-1",
            tenant_id="tenant-1",
            model="gpt-4",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
        )
        assert entry.request_id == "req-1"
        assert entry.total_tokens == 150
        assert entry.cost_usd > 0
        assert len(ct.entries) == 1

    def test_record_with_metadata(self):
        ct = CostTracker(_make_config())
        entry = ct.record_usage(
            request_id="req-2",
            user_id="user-1",
            tenant_id="tenant-1",
            model="gpt-4",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
            metadata={"conversation_id": "conv-1"},
        )
        assert entry.metadata["conversation_id"] == "conv-1"

    def test_record_without_user_id(self):
        ct = CostTracker(_make_config())
        entry = ct.record_usage(
            request_id="req-3",
            user_id=None,
            tenant_id="tenant-1",
            model="gpt-4",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
        )
        assert entry.user_id is None


class TestCheckBudget:
    def test_within_budget(self):
        ct = CostTracker(_make_config(budget_daily=100.0))
        ct.record_usage("r1", "u1", "t1", "gpt-3.5-turbo", "openai", 100, 50)
        ok, reason = ct.check_budget(user_id="u1")
        assert ok is True
        assert reason is None

    def test_disabled_always_passes(self):
        ct = CostTracker(_make_config(cost_enabled=False))
        ok, reason = ct.check_budget()
        assert ok is True

    def test_total_daily_exceeded(self):
        ct = CostTracker(_make_config(budget_daily=0.001))
        ct.record_usage("r1", "u1", "t1", "gpt-4", "openai", 10000, 5000)
        ok, reason = ct.check_budget()
        assert ok is False
        assert "Total daily budget" in reason

    def test_user_daily_exceeded(self):
        ct = CostTracker(_make_config(budget_user_daily=0.001))
        ct.record_usage("r1", "u1", "t1", "gpt-4", "openai", 10000, 5000)
        ok, reason = ct.check_budget(user_id="u1")
        assert ok is False
        assert "User daily budget" in reason

    def test_user_monthly_exceeded(self):
        ct = CostTracker(_make_config(budget_user_monthly=0.001))
        ct.record_usage("r1", "u1", "t1", "gpt-4", "openai", 10000, 5000)
        ok, reason = ct.check_budget(user_id="u1")
        assert ok is False
        assert "User monthly budget" in reason

    def test_additional_cost_considered(self):
        ct = CostTracker(_make_config(budget_daily=0.10))
        ok, reason = ct.check_budget(additional_cost=1.0)
        assert ok is False

    def test_no_user_skips_user_checks(self):
        ct = CostTracker(_make_config(budget_user_daily=0.0001))
        ct.record_usage("r1", "u1", "t1", "gpt-4", "openai", 10000, 5000)
        ok, reason = ct.check_budget(user_id=None)
        assert ok is True or "Total" in (reason or "")


class TestBudgetAlerts:
    def test_no_alerts_under_threshold(self):
        ct = CostTracker(_make_config(alert_threshold=0.8, budget_daily=1000.0))
        ct.record_usage("r1", "u1", "t1", "gpt-3.5-turbo", "openai", 100, 50)
        alerts = ct.check_budget_alert(user_id="u1")
        assert alerts == []

    def test_alert_when_approaching_daily_limit(self):
        ct = CostTracker(_make_config(
            alert_threshold=0.5,
            budget_daily=0.01,
        ))
        ct.record_usage("r1", "u1", "t1", "gpt-4", "openai", 1000, 500)
        alerts = ct.check_budget_alert()
        assert any("Total daily" in a for a in alerts)

    def test_user_daily_alert(self):
        ct = CostTracker(_make_config(
            alert_threshold=0.5,
            budget_user_daily=0.01,
        ))
        ct.record_usage("r1", "u1", "t1", "gpt-4", "openai", 1000, 500)
        alerts = ct.check_budget_alert(user_id="u1")
        assert any("User daily" in a for a in alerts)

    def test_user_monthly_alert(self):
        ct = CostTracker(_make_config(
            alert_threshold=0.5,
            budget_user_monthly=0.01,
        ))
        ct.record_usage("r1", "u1", "t1", "gpt-4", "openai", 1000, 500)
        alerts = ct.check_budget_alert(user_id="u1")
        assert any("User monthly" in a for a in alerts)


class TestReporting:
    def test_get_user_usage(self):
        ct = CostTracker(_make_config())
        ct.record_usage("r1", "u1", "t1", "gpt-4", "openai", 100, 50)
        ct.record_usage("r2", "u1", "t1", "gpt-3.5-turbo", "openai", 200, 100)
        ct.record_usage("r3", "u2", "t1", "gpt-4", "openai", 300, 150)
        usage = ct.get_user_usage("u1", days=30)
        assert usage["user_id"] == "u1"
        assert usage["total_requests"] == 2
        assert "gpt-4" in usage["by_model"]

    def test_get_user_usage_no_entries(self):
        ct = CostTracker(_make_config())
        usage = ct.get_user_usage("nonexistent")
        assert usage["total_requests"] == 0
        assert usage["total_cost_usd"] == 0

    def test_get_report_filters_by_time(self):
        ct = CostTracker(_make_config())
        ct.record_usage("r1", "u1", "t1", "gpt-4", "openai", 100, 50)
        now = datetime.now(UTC)
        report = ct.get_report(
            start_time=now - timedelta(hours=1),
            end_time=now + timedelta(hours=1),
        )
        assert report.total_requests == 1
        assert report.total_cost_usd > 0

    def test_get_report_defaults(self):
        ct = CostTracker(_make_config())
        ct.record_usage("r1", "u1", "t1", "gpt-4", "openai", 100, 50)
        report = ct.get_report()
        assert isinstance(report, CostReport)
        assert report.total_requests == 1

    def test_get_report_by_provider(self):
        ct = CostTracker(_make_config())
        ct.record_usage("r1", "u1", "t1", "gpt-4", "openai", 100, 50)
        report = ct.get_report()
        assert "openai" in report.by_provider

    def test_get_report_top_users(self):
        ct = CostTracker(_make_config())
        for i in range(3):
            ct.record_usage(f"r{i}", "u1", "t1", "gpt-4", "openai", 1000, 500)
        ct.record_usage("r99", "u2", "t1", "gpt-4", "openai", 100, 50)
        report = ct.get_report()
        assert len(report.top_users) >= 2
        assert report.top_users[0][0] == "u1"

    def test_get_today_cost(self):
        ct = CostTracker(_make_config())
        ct.record_usage("r1", "u1", "t1", "gpt-4", "openai", 1000, 500)
        today_cost = ct.get_today_cost()
        assert today_cost > 0

    def test_estimate_cost(self):
        ct = CostTracker(_make_config())
        estimate = ct.estimate_cost("gpt-4", 1000, 500)
        assert estimate == ct.calculate_cost("gpt-4", 1000, 500)

    def test_get_report_no_user_entries_excluded_from_by_user(self):
        ct = CostTracker(_make_config())
        ct.record_usage("r1", None, "t1", "gpt-4", "openai", 100, 50)
        report = ct.get_report()
        assert report.by_user == {}


class TestPruning:
    def test_prune_removes_old_entries(self):
        ct = CostTracker(_make_config())
        old_entry = CostEntry(
            request_id="old",
            user_id="u1",
            tenant_id="t1",
            model="gpt-4",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            cost_usd=0.01,
            timestamp=datetime.now(UTC) - timedelta(days=8),
        )
        ct.entries.append(old_entry)
        ct._prune_old_entries()
        assert len(ct.entries) == 0

    def test_prune_keeps_recent_entries(self):
        ct = CostTracker(_make_config())
        ct.record_usage("r1", "u1", "t1", "gpt-4", "openai", 100, 50)
        ct._prune_old_entries()
        assert len(ct.entries) == 1


class TestAllowlistConfig:
    def test_empty_allowlist_allows_all(self):
        al = AllowlistConfig()
        assert al.is_provider_allowed("openai") is True
        assert al.is_model_allowed("gpt-4") is True

    def test_blocked_provider_rejected(self):
        al = AllowlistConfig(blocked_providers=["badprovider"])
        assert al.is_provider_allowed("badprovider") is False
        assert al.is_provider_allowed("openai") is True

    def test_blocked_model_rejected(self):
        al = AllowlistConfig(blocked_models=["dangerous-model"])
        assert al.is_model_allowed("dangerous-model") is False
        assert al.is_model_allowed("gpt-4") is True

    def test_allowed_providers_restricts(self):
        al = AllowlistConfig(allowed_providers=["openai"])
        assert al.is_provider_allowed("openai") is True
        assert al.is_provider_allowed("anthropic") is False

    def test_allowed_models_restricts(self):
        al = AllowlistConfig(allowed_models=["gpt-4", "gpt-3.5-turbo"])
        assert al.is_model_allowed("gpt-4") is True
        assert al.is_model_allowed("claude-3") is False

    def test_blocked_overrides_allowed(self):
        al = AllowlistConfig(
            allowed_providers=["openai", "badprovider"],
            blocked_providers=["badprovider"],
        )
        assert al.is_provider_allowed("badprovider") is False

    def test_blocked_model_overrides_allowed(self):
        al = AllowlistConfig(
            allowed_models=["gpt-4", "dangerous-model"],
            blocked_models=["dangerous-model"],
        )
        assert al.is_model_allowed("dangerous-model") is False
