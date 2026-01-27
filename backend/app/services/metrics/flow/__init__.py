"""Flow metrics for developer experience and work throughput."""

from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel


class FlowMetrics(BaseModel):
    """Flow metrics model measuring work throughput and efficiency."""

    # Throughput metrics
    issues_completed: int = 0
    story_points_completed: float = 0
    prs_merged: int = 0
    commits_count: int = 0

    # Cycle time breakdown (in hours)
    avg_coding_time: float | None = None
    avg_review_time: float | None = None
    avg_deploy_time: float | None = None
    total_cycle_time: float | None = None

    # Work in Progress
    current_wip: int = 0
    avg_wip: float = 0
    wip_limit: int | None = None
    wip_compliance: float | None = None  # % time under WIP limit

    # Flow efficiency
    flow_efficiency: float | None = None  # Active time / Total time
    wait_time_ratio: float | None = None  # Wait time / Total time

    # Throughput variability
    throughput_mean: float = 0
    throughput_std: float = 0
    coefficient_of_variation: float | None = None

    # Aging work
    avg_age_wip_days: float = 0
    items_over_sla: int = 0

    # Period
    period_start: datetime | None = None
    period_end: datetime | None = None


class FlowMetricsService:
    """Service for calculating flow metrics."""

    async def calculate_metrics(
        self,
        project_id: str | None,
        period_start: datetime,
        period_end: datetime,
    ) -> FlowMetrics:
        """
        Calculate flow metrics for a project.

        Args:
            project_id: Project identifier
            period_start: Start of measurement period
            period_end: End of measurement period

        Returns:
            FlowMetrics with calculated values
        """
        metrics = FlowMetrics(
            period_start=period_start,
            period_end=period_end,
        )

        # Calculate throughput metrics
        throughput_data = await self._get_throughput_data(
            project_id, period_start, period_end
        )
        metrics.issues_completed = throughput_data.get("issues_completed", 0)
        metrics.story_points_completed = throughput_data.get("story_points", 0)
        metrics.prs_merged = throughput_data.get("prs_merged", 0)
        metrics.commits_count = throughput_data.get("commits", 0)

        # Calculate cycle time breakdown
        cycle_data = await self._get_cycle_time_breakdown(
            project_id, period_start, period_end
        )
        metrics.avg_coding_time = cycle_data.get("coding_time")
        metrics.avg_review_time = cycle_data.get("review_time")
        metrics.avg_deploy_time = cycle_data.get("deploy_time")

        if all([metrics.avg_coding_time, metrics.avg_review_time, metrics.avg_deploy_time]):
            metrics.total_cycle_time = (
                metrics.avg_coding_time +
                metrics.avg_review_time +
                metrics.avg_deploy_time
            )

        # Calculate WIP metrics
        wip_data = await self._get_wip_metrics(project_id, period_start, period_end)
        metrics.current_wip = wip_data.get("current_wip", 0)
        metrics.avg_wip = wip_data.get("avg_wip", 0)
        metrics.wip_limit = wip_data.get("wip_limit")
        if metrics.wip_limit:
            metrics.wip_compliance = wip_data.get("compliance", 0)

        # Calculate flow efficiency
        if metrics.total_cycle_time and metrics.avg_coding_time:
            active_time = metrics.avg_coding_time
            metrics.flow_efficiency = (active_time / metrics.total_cycle_time) * 100
            metrics.wait_time_ratio = (
                (metrics.total_cycle_time - active_time) / metrics.total_cycle_time
            ) * 100

        # Calculate throughput variability
        throughput_history = await self._get_throughput_history(
            project_id, period_start, period_end
        )
        if throughput_history:
            metrics.throughput_mean = sum(throughput_history) / len(throughput_history)
            if len(throughput_history) > 1:
                variance = sum((x - metrics.throughput_mean) ** 2 for x in throughput_history) / len(throughput_history)
                metrics.throughput_std = variance ** 0.5
                if metrics.throughput_mean > 0:
                    metrics.coefficient_of_variation = metrics.throughput_std / metrics.throughput_mean

        # Calculate aging metrics
        aging_data = await self._get_aging_metrics(project_id)
        metrics.avg_age_wip_days = aging_data.get("avg_age", 0)
        metrics.items_over_sla = aging_data.get("over_sla", 0)

        return metrics

    async def _get_throughput_data(
        self,
        project_id: str | None,
        period_start: datetime,
        period_end: datetime,
    ) -> dict[str, Any]:
        """Get throughput data from DevLake."""
        # This would query DevLake for completed work
        return {
            "issues_completed": 0,
            "story_points": 0,
            "prs_merged": 0,
            "commits": 0,
        }

    async def _get_cycle_time_breakdown(
        self,
        project_id: str | None,
        period_start: datetime,
        period_end: datetime,
    ) -> dict[str, float]:
        """Get cycle time breakdown from DevLake."""
        return {
            "coding_time": 0,
            "review_time": 0,
            "deploy_time": 0,
        }

    async def _get_wip_metrics(
        self,
        project_id: str | None,
        period_start: datetime,
        period_end: datetime,
    ) -> dict[str, Any]:
        """Get WIP metrics."""
        return {
            "current_wip": 0,
            "avg_wip": 0,
            "wip_limit": None,
            "compliance": 0,
        }

    async def _get_throughput_history(
        self,
        project_id: str | None,
        period_start: datetime,
        period_end: datetime,
    ) -> list[float]:
        """Get historical throughput for variability calculation."""
        return []

    async def _get_aging_metrics(
        self,
        project_id: str | None,
    ) -> dict[str, Any]:
        """Get aging work metrics."""
        return {
            "avg_age": 0,
            "over_sla": 0,
        }

    async def get_cumulative_flow_diagram_data(
        self,
        project_id: str | None,
        period_start: datetime,
        period_end: datetime,
    ) -> list[dict[str, Any]]:
        """
        Get data for Cumulative Flow Diagram.

        Returns daily counts for each workflow state.
        """
        # This would return data like:
        # [
        #     {"date": "2024-01-01", "backlog": 50, "in_progress": 10, "review": 5, "done": 100},
        #     ...
        # ]
        return []

    async def get_cycle_time_histogram(
        self,
        project_id: str | None,
        period_start: datetime,
        period_end: datetime,
    ) -> dict[str, Any]:
        """
        Get cycle time distribution data.

        Returns histogram data and percentiles.
        """
        return {
            "buckets": [],
            "percentiles": {
                "p50": 0,
                "p85": 0,
                "p95": 0,
            },
        }

    async def get_throughput_run_chart(
        self,
        project_id: str | None,
        period_start: datetime,
        period_end: datetime,
        granularity: str = "weekly",
    ) -> list[dict[str, Any]]:
        """
        Get throughput over time for run chart.

        Returns weekly/daily throughput with trend line.
        """
        return []


# Singleton instance
flow_metrics_service = FlowMetricsService()
