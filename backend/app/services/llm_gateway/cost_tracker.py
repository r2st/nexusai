"""Cost tracking for LLM usage."""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import structlog

from app.services.llm_gateway.config import GatewayConfig, ModelConfig

logger = structlog.get_logger()


@dataclass
class CostEntry:
    """A single cost entry."""

    request_id: str
    user_id: str | None
    tenant_id: str | None
    model: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CostReport:
    """Cost report for a time period."""

    start_time: datetime
    end_time: datetime
    total_cost_usd: float
    total_tokens: int
    total_requests: int
    by_user: dict[str, float] = field(default_factory=dict)
    by_model: dict[str, float] = field(default_factory=dict)
    by_provider: dict[str, float] = field(default_factory=dict)
    top_users: list[tuple[str, float]] = field(default_factory=list)


class CostTracker:
    """Tracks costs for LLM usage."""

    def __init__(self, config: GatewayConfig):
        self.config = config
        self.entries: list[CostEntry] = []
        self._user_daily_costs: dict[str, dict[str, float]] = defaultdict(
            lambda: defaultdict(float)
        )
        self._user_monthly_costs: dict[str, dict[str, float]] = defaultdict(
            lambda: defaultdict(float)
        )
        self._total_daily_costs: dict[str, float] = defaultdict(float)
        self._model_configs: dict[str, ModelConfig] = {
            m.name: m for m in config.models
        }

    def calculate_cost(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """Calculate cost for token usage."""
        model_config = self._model_configs.get(model)

        if not model_config:
            # Unknown model, estimate based on similar models
            logger.warning("Unknown model for cost calculation", model=model)
            # Default to GPT-3.5 pricing as a reasonable estimate
            input_cost = 0.0005
            output_cost = 0.0015
        else:
            input_cost = model_config.input_cost_per_1k
            output_cost = model_config.output_cost_per_1k

        cost = (prompt_tokens / 1000 * input_cost) + (
            completion_tokens / 1000 * output_cost
        )
        return round(cost, 6)

    def record_usage(
        self,
        request_id: str,
        user_id: str | None,
        tenant_id: str | None,
        model: str,
        provider: str,
        prompt_tokens: int,
        completion_tokens: int,
        metadata: dict[str, Any] | None = None,
    ) -> CostEntry:
        """Record token usage and calculate cost."""
        cost = self.calculate_cost(model, prompt_tokens, completion_tokens)
        total_tokens = prompt_tokens + completion_tokens

        entry = CostEntry(
            request_id=request_id,
            user_id=user_id,
            tenant_id=tenant_id,
            model=model,
            provider=provider,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost,
            metadata=metadata or {},
        )

        self.entries.append(entry)
        self._update_aggregates(entry)

        # Prune old entries (keep last 7 days)
        self._prune_old_entries()

        return entry

    def _update_aggregates(self, entry: CostEntry):
        """Update aggregate cost tracking."""
        date_key = entry.timestamp.strftime("%Y-%m-%d")
        month_key = entry.timestamp.strftime("%Y-%m")

        # Daily totals
        self._total_daily_costs[date_key] += entry.cost_usd

        # User costs
        if entry.user_id:
            self._user_daily_costs[entry.user_id][date_key] += entry.cost_usd
            self._user_monthly_costs[entry.user_id][month_key] += entry.cost_usd

    def _prune_old_entries(self):
        """Remove entries older than 7 days."""
        cutoff = datetime.utcnow() - timedelta(days=7)
        self.entries = [e for e in self.entries if e.timestamp > cutoff]

    def check_budget(
        self,
        user_id: str | None = None,
        additional_cost: float = 0.0,
    ) -> tuple[bool, str | None]:
        """
        Check if usage is within budget.

        Returns:
            Tuple of (is_within_budget, reason_if_exceeded)
        """
        if not self.config.cost.enabled:
            return True, None

        today = datetime.utcnow().strftime("%Y-%m-%d")
        month = datetime.utcnow().strftime("%Y-%m")

        # Check total daily budget
        total_today = self._total_daily_costs.get(today, 0.0) + additional_cost
        if total_today > self.config.cost.budget_total_daily:
            return False, f"Total daily budget exceeded (${total_today:.2f}/${self.config.cost.budget_total_daily:.2f})"

        # Check user budgets
        if user_id:
            user_today = self._user_daily_costs[user_id].get(today, 0.0) + additional_cost
            if user_today > self.config.cost.budget_per_user_daily:
                return False, f"User daily budget exceeded (${user_today:.2f}/${self.config.cost.budget_per_user_daily:.2f})"

            user_month = self._user_monthly_costs[user_id].get(month, 0.0) + additional_cost
            if user_month > self.config.cost.budget_per_user_monthly:
                return False, f"User monthly budget exceeded (${user_month:.2f}/${self.config.cost.budget_per_user_monthly:.2f})"

        return True, None

    def check_budget_alert(self, user_id: str | None = None) -> list[str]:
        """Check if any budget thresholds are approaching."""
        alerts = []
        threshold = self.config.cost.alert_threshold

        today = datetime.utcnow().strftime("%Y-%m-%d")
        month = datetime.utcnow().strftime("%Y-%m")

        # Total daily
        total_today = self._total_daily_costs.get(today, 0.0)
        if total_today > self.config.cost.budget_total_daily * threshold:
            alerts.append(
                f"Total daily budget at {total_today / self.config.cost.budget_total_daily * 100:.1f}%"
            )

        # User budgets
        if user_id:
            user_today = self._user_daily_costs[user_id].get(today, 0.0)
            if user_today > self.config.cost.budget_per_user_daily * threshold:
                alerts.append(
                    f"User daily budget at {user_today / self.config.cost.budget_per_user_daily * 100:.1f}%"
                )

            user_month = self._user_monthly_costs[user_id].get(month, 0.0)
            if user_month > self.config.cost.budget_per_user_monthly * threshold:
                alerts.append(
                    f"User monthly budget at {user_month / self.config.cost.budget_per_user_monthly * 100:.1f}%"
                )

        return alerts

    def get_user_usage(
        self,
        user_id: str,
        days: int = 30,
    ) -> dict[str, Any]:
        """Get usage statistics for a user."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        user_entries = [
            e for e in self.entries
            if e.user_id == user_id and e.timestamp > cutoff
        ]

        total_cost = sum(e.cost_usd for e in user_entries)
        total_tokens = sum(e.total_tokens for e in user_entries)

        by_model: dict[str, float] = defaultdict(float)
        by_day: dict[str, float] = defaultdict(float)

        for entry in user_entries:
            by_model[entry.model] += entry.cost_usd
            by_day[entry.timestamp.strftime("%Y-%m-%d")] += entry.cost_usd

        return {
            "user_id": user_id,
            "period_days": days,
            "total_cost_usd": total_cost,
            "total_tokens": total_tokens,
            "total_requests": len(user_entries),
            "by_model": dict(by_model),
            "by_day": dict(by_day),
        }

    def get_report(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> CostReport:
        """Generate a cost report."""
        if end_time is None:
            end_time = datetime.utcnow()
        if start_time is None:
            start_time = end_time - timedelta(days=1)

        entries = [
            e for e in self.entries
            if start_time <= e.timestamp <= end_time
        ]

        by_user: dict[str, float] = defaultdict(float)
        by_model: dict[str, float] = defaultdict(float)
        by_provider: dict[str, float] = defaultdict(float)

        for entry in entries:
            if entry.user_id:
                by_user[entry.user_id] += entry.cost_usd
            by_model[entry.model] += entry.cost_usd
            by_provider[entry.provider] += entry.cost_usd

        # Top users
        top_users = sorted(by_user.items(), key=lambda x: x[1], reverse=True)[:10]

        return CostReport(
            start_time=start_time,
            end_time=end_time,
            total_cost_usd=sum(e.cost_usd for e in entries),
            total_tokens=sum(e.total_tokens for e in entries),
            total_requests=len(entries),
            by_user=dict(by_user),
            by_model=dict(by_model),
            by_provider=dict(by_provider),
            top_users=top_users,
        )

    def get_today_cost(self) -> float:
        """Get total cost for today."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        return self._total_daily_costs.get(today, 0.0)

    def estimate_cost(
        self,
        model: str,
        estimated_prompt_tokens: int,
        estimated_completion_tokens: int,
    ) -> float:
        """Estimate cost before making a request."""
        return self.calculate_cost(
            model, estimated_prompt_tokens, estimated_completion_tokens
        )
