"""Cost tracking for LLM usage with database persistence."""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from typing import Any, TYPE_CHECKING
from uuid import uuid4

import structlog
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm_gateway.config import GatewayConfig, ModelConfig

if TYPE_CHECKING:
    from app.models.cost_entry import CostEntry as CostEntryModel

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
        self._last_prune: datetime = datetime.utcnow()
        self._prune_interval: timedelta = timedelta(minutes=5)

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

        now = datetime.utcnow()
        if now - self._last_prune > self._prune_interval:
            self._prune_old_entries()
            self._last_prune = now

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
        budget_daily = self.config.cost.budget_total_daily
        if budget_daily > 0 and total_today > budget_daily * threshold:
            alerts.append(
                f"Total daily budget at {total_today / budget_daily * 100:.1f}%"
            )

        # User budgets
        if user_id:
            user_today = self._user_daily_costs[user_id].get(today, 0.0)
            budget_user_daily = self.config.cost.budget_per_user_daily
            if budget_user_daily > 0 and user_today > budget_user_daily * threshold:
                alerts.append(
                    f"User daily budget at {user_today / budget_user_daily * 100:.1f}%"
                )

            user_month = self._user_monthly_costs[user_id].get(month, 0.0)
            budget_user_monthly = self.config.cost.budget_per_user_monthly
            if budget_user_monthly > 0 and user_month > budget_user_monthly * threshold:
                alerts.append(
                    f"User monthly budget at {user_month / budget_user_monthly * 100:.1f}%"
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

    # =========================================================================
    # DATABASE PERSISTENCE METHODS
    # =========================================================================

    async def persist_entry(
        self,
        entry: CostEntry,
        db: AsyncSession,
        conversation_id: str | None = None,
        request_type: str = "chat",
        latency_ms: int | None = None,
        success: bool = True,
        error_type: str | None = None,
    ) -> "CostEntryModel":
        """
        Persist a cost entry to the database.

        Args:
            entry: The in-memory CostEntry to persist
            db: Database session
            conversation_id: Optional conversation ID
            request_type: Type of request (chat, completion, embedding, etc.)
            latency_ms: Request latency in milliseconds
            success: Whether the request was successful
            error_type: Error type if failed

        Returns:
            The persisted CostEntry model
        """
        from app.models.cost_entry import CostEntry as CostEntryModel

        db_entry = CostEntryModel(
            id=str(uuid4()),
            tenant_id=entry.tenant_id or "default",
            user_id=entry.user_id,
            request_id=entry.request_id,
            conversation_id=conversation_id,
            provider=entry.provider,
            model=entry.model,
            prompt_tokens=entry.prompt_tokens,
            completion_tokens=entry.completion_tokens,
            total_tokens=entry.total_tokens,
            cost_usd=entry.cost_usd,
            request_type=request_type,
            latency_ms=latency_ms,
            success=success,
            error_type=error_type,
            entry_metadata=entry.metadata,
            created_at=entry.timestamp.replace(tzinfo=UTC) if entry.timestamp.tzinfo is None else entry.timestamp,
        )

        db.add(db_entry)
        await db.commit()
        await db.refresh(db_entry)

        logger.debug(
            "cost_entry_persisted",
            request_id=entry.request_id,
            cost_usd=entry.cost_usd,
            model=entry.model,
        )

        return db_entry

    async def get_time_series(
        self,
        db: AsyncSession,
        tenant_id: str,
        start_time: datetime,
        end_time: datetime,
        granularity: str = "daily",
        user_id: str | None = None,
        model: str | None = None,
        provider: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get cost time-series data from the database.

        Args:
            db: Database session
            tenant_id: Tenant ID to filter by
            start_time: Start of the time range
            end_time: End of the time range
            granularity: Time grouping (hourly, daily, weekly, monthly)
            user_id: Optional user filter
            model: Optional model filter
            provider: Optional provider filter

        Returns:
            List of time-series data points
        """
        from app.models.cost_entry import CostEntry as CostEntryModel

        # Build date truncation based on granularity
        if granularity == "hourly":
            date_trunc = func.date_trunc("hour", CostEntryModel.created_at)
        elif granularity == "weekly":
            date_trunc = func.date_trunc("week", CostEntryModel.created_at)
        elif granularity == "monthly":
            date_trunc = func.date_trunc("month", CostEntryModel.created_at)
        else:  # daily
            date_trunc = func.date_trunc("day", CostEntryModel.created_at)

        # Build query
        query = (
            select(
                date_trunc.label("period"),
                func.sum(CostEntryModel.cost_usd).label("total_cost"),
                func.sum(CostEntryModel.total_tokens).label("total_tokens"),
                func.count(CostEntryModel.id).label("request_count"),
            )
            .where(
                and_(
                    CostEntryModel.tenant_id == tenant_id,
                    CostEntryModel.created_at >= start_time,
                    CostEntryModel.created_at <= end_time,
                )
            )
            .group_by(date_trunc)
            .order_by(date_trunc)
        )

        # Apply optional filters
        if user_id:
            query = query.where(CostEntryModel.user_id == user_id)
        if model:
            query = query.where(CostEntryModel.model == model)
        if provider:
            query = query.where(CostEntryModel.provider == provider)

        result = await db.execute(query)
        rows = result.fetchall()

        return [
            {
                "period": row.period.isoformat() if row.period else None,
                "total_cost": float(row.total_cost or 0),
                "total_tokens": int(row.total_tokens or 0),
                "request_count": int(row.request_count or 0),
            }
            for row in rows
        ]

    async def get_breakdown_by_model(
        self,
        db: AsyncSession,
        tenant_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> list[dict[str, Any]]:
        """Get cost breakdown by model."""
        from app.models.cost_entry import CostEntry as CostEntryModel

        query = (
            select(
                CostEntryModel.model,
                func.sum(CostEntryModel.cost_usd).label("total_cost"),
                func.sum(CostEntryModel.total_tokens).label("total_tokens"),
                func.count(CostEntryModel.id).label("request_count"),
                func.avg(CostEntryModel.latency_ms).label("avg_latency_ms"),
            )
            .where(
                and_(
                    CostEntryModel.tenant_id == tenant_id,
                    CostEntryModel.created_at >= start_time,
                    CostEntryModel.created_at <= end_time,
                )
            )
            .group_by(CostEntryModel.model)
            .order_by(func.sum(CostEntryModel.cost_usd).desc())
        )

        result = await db.execute(query)
        rows = result.fetchall()

        return [
            {
                "model": row.model,
                "total_cost": float(row.total_cost or 0),
                "total_tokens": int(row.total_tokens or 0),
                "request_count": int(row.request_count or 0),
                "avg_latency_ms": float(row.avg_latency_ms or 0) if row.avg_latency_ms else None,
            }
            for row in rows
        ]

    async def get_breakdown_by_provider(
        self,
        db: AsyncSession,
        tenant_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> list[dict[str, Any]]:
        """Get cost breakdown by provider."""
        from app.models.cost_entry import CostEntry as CostEntryModel

        query = (
            select(
                CostEntryModel.provider,
                func.sum(CostEntryModel.cost_usd).label("total_cost"),
                func.sum(CostEntryModel.total_tokens).label("total_tokens"),
                func.count(CostEntryModel.id).label("request_count"),
                func.avg(CostEntryModel.latency_ms).label("avg_latency_ms"),
            )
            .where(
                and_(
                    CostEntryModel.tenant_id == tenant_id,
                    CostEntryModel.created_at >= start_time,
                    CostEntryModel.created_at <= end_time,
                )
            )
            .group_by(CostEntryModel.provider)
            .order_by(func.sum(CostEntryModel.cost_usd).desc())
        )

        result = await db.execute(query)
        rows = result.fetchall()

        return [
            {
                "provider": row.provider,
                "total_cost": float(row.total_cost or 0),
                "total_tokens": int(row.total_tokens or 0),
                "request_count": int(row.request_count or 0),
                "avg_latency_ms": float(row.avg_latency_ms or 0) if row.avg_latency_ms else None,
            }
            for row in rows
        ]

    async def get_summary(
        self,
        db: AsyncSession,
        tenant_id: str,
        start_time: datetime,
        end_time: datetime,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Get cost summary for a period."""
        from app.models.cost_entry import CostEntry as CostEntryModel

        conditions = [
            CostEntryModel.tenant_id == tenant_id,
            CostEntryModel.created_at >= start_time,
            CostEntryModel.created_at <= end_time,
        ]
        if user_id:
            conditions.append(CostEntryModel.user_id == user_id)

        query = select(
            func.sum(CostEntryModel.cost_usd).label("total_cost"),
            func.sum(CostEntryModel.total_tokens).label("total_tokens"),
            func.sum(CostEntryModel.prompt_tokens).label("prompt_tokens"),
            func.sum(CostEntryModel.completion_tokens).label("completion_tokens"),
            func.count(CostEntryModel.id).label("request_count"),
            func.avg(CostEntryModel.latency_ms).label("avg_latency_ms"),
            func.count(CostEntryModel.id).filter(CostEntryModel.success == True).label("successful_requests"),
        ).where(and_(*conditions))

        result = await db.execute(query)
        row = result.fetchone()

        if not row:
            return {
                "total_cost": 0.0,
                "total_tokens": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "request_count": 0,
                "avg_latency_ms": None,
                "success_rate": 0.0,
            }

        request_count = int(row.request_count or 0)
        successful_requests = int(row.successful_requests or 0)

        return {
            "total_cost": float(row.total_cost or 0),
            "total_tokens": int(row.total_tokens or 0),
            "prompt_tokens": int(row.prompt_tokens or 0),
            "completion_tokens": int(row.completion_tokens or 0),
            "request_count": request_count,
            "avg_latency_ms": float(row.avg_latency_ms or 0) if row.avg_latency_ms else None,
            "success_rate": successful_requests / request_count if request_count > 0 else 0.0,
        }

    async def forecast_monthly_cost(
        self,
        db: AsyncSession,
        tenant_id: str,
    ) -> dict[str, Any]:
        """
        Forecast monthly cost based on recent trends.

        Uses last 7 days of data to project monthly spend.
        """
        from app.models.cost_entry import CostEntry as CostEntryModel

        now = datetime.now(UTC)
        seven_days_ago = now - timedelta(days=7)

        # Get last 7 days of cost data with actual day count
        query = select(
            func.sum(CostEntryModel.cost_usd).label("total_cost"),
            func.count(CostEntryModel.id).label("request_count"),
            func.min(CostEntryModel.created_at).label("earliest_entry"),
        ).where(
            and_(
                CostEntryModel.tenant_id == tenant_id,
                CostEntryModel.created_at >= seven_days_ago,
                CostEntryModel.created_at <= now,
            )
        )

        result = await db.execute(query)
        row = result.fetchone()

        if not row or not row.total_cost:
            return {
                "projected_monthly_cost": 0.0,
                "daily_average": 0.0,
                "confidence": "low",
                "basis_days": 0,
            }

        actual_days = max(1, (now - row.earliest_entry).total_seconds() / 86400)
        basis_days = min(7, actual_days)
        daily_average = float(row.total_cost) / basis_days
        projected_monthly = daily_average * 30

        return {
            "projected_monthly_cost": round(projected_monthly, 2),
            "daily_average": round(daily_average, 4),
            "confidence": "medium" if row.request_count >= 10 and basis_days >= 3 else "low",
            "basis_days": round(basis_days, 1),
            "basis_cost": float(row.total_cost),
            "basis_requests": int(row.request_count),
        }
