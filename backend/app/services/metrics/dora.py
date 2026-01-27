"""DORA Metrics Service.

DevOps Research and Assessment (DORA) metrics:
- Deployment Frequency
- Lead Time for Changes
- Mean Time to Recovery (MTTR)
- Change Failure Rate
"""

from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.devlake import devlake_service


class DORAMetrics(BaseModel):
    """DORA metrics model."""

    # Core metrics
    deployment_frequency: float | None = None  # Deployments per day
    lead_time_for_changes: float | None = None  # Hours from commit to production
    mean_time_to_recovery: float | None = None  # Hours to recover from failures
    change_failure_rate: float | None = None  # Percentage of deployments causing failures

    # Performance levels (Elite, High, Medium, Low)
    deployment_frequency_level: str | None = None
    lead_time_level: str | None = None
    mttr_level: str | None = None
    change_failure_rate_level: str | None = None
    overall_level: str | None = None

    # Period
    period_start: datetime | None = None
    period_end: datetime | None = None

    # Trend data
    trend: list[dict[str, Any]] = []


class DORAMetricsService:
    """Service for calculating DORA metrics."""

    # DORA performance level thresholds (2023 State of DevOps)
    THRESHOLDS = {
        "deployment_frequency": {
            "elite": 1.0,  # Multiple times per day (1+)
            "high": 0.14,  # Weekly (1/7)
            "medium": 0.03,  # Monthly (1/30)
        },
        "lead_time": {
            "elite": 24,  # Less than 1 day
            "high": 168,  # Less than 1 week
            "medium": 720,  # Less than 1 month
        },
        "mttr": {
            "elite": 1,  # Less than 1 hour
            "high": 24,  # Less than 1 day
            "medium": 168,  # Less than 1 week
        },
        "change_failure_rate": {
            "elite": 5,  # 0-5%
            "high": 10,  # 5-10%
            "medium": 15,  # 10-15%
        },
    }

    async def calculate_metrics(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_name: str,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
    ) -> DORAMetrics:
        """Calculate DORA metrics for a project.

        Args:
            session: Database session
            tenant_id: Tenant ID
            project_name: DevLake project name
            period_start: Start of measurement period
            period_end: End of measurement period

        Returns:
            DORAMetrics with calculated values
        """
        period_end = period_end or datetime.now()
        period_start = period_start or (period_end - timedelta(days=30))

        metrics = DORAMetrics(
            period_start=period_start,
            period_end=period_end,
        )

        try:
            # Get DORA metrics from DevLake
            devlake_metrics = await devlake_service.get_dora_metrics(project_name)

            metrics.deployment_frequency = devlake_metrics.deployment_frequency
            metrics.lead_time_for_changes = devlake_metrics.lead_time_for_changes
            metrics.mean_time_to_recovery = devlake_metrics.mean_time_to_recovery
            metrics.change_failure_rate = devlake_metrics.change_failure_rate

            # Calculate performance levels
            metrics.deployment_frequency_level = self._get_level(
                "deployment_frequency",
                metrics.deployment_frequency,
                higher_is_better=True
            )
            metrics.lead_time_level = self._get_level(
                "lead_time",
                metrics.lead_time_for_changes,
                higher_is_better=False
            )
            metrics.mttr_level = self._get_level(
                "mttr",
                metrics.mean_time_to_recovery,
                higher_is_better=False
            )
            metrics.change_failure_rate_level = self._get_level(
                "change_failure_rate",
                metrics.change_failure_rate,
                higher_is_better=False
            )

            # Calculate overall level
            metrics.overall_level = self._calculate_overall_level(metrics)

        except Exception as e:
            print(f"Error calculating DORA metrics: {e}")

        return metrics

    def _get_level(
        self,
        metric: str,
        value: float | None,
        higher_is_better: bool = True,
    ) -> str:
        """Determine performance level for a metric."""
        if value is None:
            return "unknown"

        thresholds = self.THRESHOLDS.get(metric, {})

        if higher_is_better:
            if value >= thresholds.get("elite", float("inf")):
                return "elite"
            elif value >= thresholds.get("high", float("inf")):
                return "high"
            elif value >= thresholds.get("medium", float("inf")):
                return "medium"
            else:
                return "low"
        else:
            if value <= thresholds.get("elite", 0):
                return "elite"
            elif value <= thresholds.get("high", 0):
                return "high"
            elif value <= thresholds.get("medium", 0):
                return "medium"
            else:
                return "low"

    def _calculate_overall_level(self, metrics: DORAMetrics) -> str:
        """Calculate overall DORA performance level."""
        levels = [
            metrics.deployment_frequency_level,
            metrics.lead_time_level,
            metrics.mttr_level,
            metrics.change_failure_rate_level,
        ]

        # Remove unknown levels
        levels = [l for l in levels if l and l != "unknown"]

        if not levels:
            return "unknown"

        # Level scores
        level_scores = {"elite": 4, "high": 3, "medium": 2, "low": 1}

        avg_score = sum(level_scores.get(l, 0) for l in levels) / len(levels)

        if avg_score >= 3.5:
            return "elite"
        elif avg_score >= 2.5:
            return "high"
        elif avg_score >= 1.5:
            return "medium"
        else:
            return "low"

    async def get_trend(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_name: str,
        periods: int = 6,
        granularity: str = "monthly",
    ) -> list[DORAMetrics]:
        """Get DORA metrics trend over multiple periods."""
        trends = []
        now = datetime.now()

        if granularity == "weekly":
            delta = timedelta(weeks=1)
        elif granularity == "quarterly":
            delta = timedelta(days=90)
        else:
            delta = timedelta(days=30)

        for i in range(periods):
            period_end = now - (delta * i)
            period_start = period_end - delta

            metrics = await self.calculate_metrics(
                session, tenant_id, project_name, period_start, period_end
            )
            trends.append(metrics)

        return list(reversed(trends))

    async def get_benchmark_comparison(
        self,
        metrics: DORAMetrics,
    ) -> dict[str, Any]:
        """Compare metrics against industry benchmarks."""
        return {
            "deployment_frequency": {
                "value": metrics.deployment_frequency,
                "level": metrics.deployment_frequency_level,
                "elite_threshold": self.THRESHOLDS["deployment_frequency"]["elite"],
                "high_threshold": self.THRESHOLDS["deployment_frequency"]["high"],
                "description": "Elite performers deploy multiple times per day",
            },
            "lead_time_for_changes": {
                "value": metrics.lead_time_for_changes,
                "level": metrics.lead_time_level,
                "elite_threshold": self.THRESHOLDS["lead_time"]["elite"],
                "high_threshold": self.THRESHOLDS["lead_time"]["high"],
                "description": "Elite performers have lead times under 1 day",
            },
            "mean_time_to_recovery": {
                "value": metrics.mean_time_to_recovery,
                "level": metrics.mttr_level,
                "elite_threshold": self.THRESHOLDS["mttr"]["elite"],
                "high_threshold": self.THRESHOLDS["mttr"]["high"],
                "description": "Elite performers recover in under 1 hour",
            },
            "change_failure_rate": {
                "value": metrics.change_failure_rate,
                "level": metrics.change_failure_rate_level,
                "elite_threshold": self.THRESHOLDS["change_failure_rate"]["elite"],
                "high_threshold": self.THRESHOLDS["change_failure_rate"]["high"],
                "description": "Elite performers have failure rates under 5%",
            },
        }


# Singleton instance
dora_metrics_service = DORAMetricsService()
