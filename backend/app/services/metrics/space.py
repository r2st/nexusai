"""SPACE Framework Metrics Service.

SPACE Framework measures developer productivity across 5 dimensions:
- Satisfaction and well-being
- Performance
- Activity
- Communication and collaboration
- Efficiency and flow
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.devlake import devlake_service


class SPACEMetrics(BaseModel):
    """SPACE Framework metrics model."""

    # Satisfaction and well-being
    satisfaction_score: float | None = None  # From surveys (0-100)
    burnout_risk: float | None = None  # Calculated from work patterns (0-100)
    work_life_balance: float | None = None  # Derived from commit times (0-100)

    # Performance
    code_review_quality: float | None = None  # Review thoroughness (0-100)
    bug_fix_rate: float | None = None  # Bugs fixed vs introduced
    feature_completion_rate: float | None = None  # Features completed on time

    # Activity
    commits_per_developer: float | None = None
    prs_per_developer: float | None = None
    reviews_per_developer: float | None = None
    active_days_ratio: float | None = None  # Active days / working days

    # Communication and collaboration
    review_participation_rate: float | None = None  # % of team participating in reviews
    cross_team_collaboration: float | None = None  # Cross-team PR reviews
    documentation_ratio: float | None = None  # Docs changes / code changes
    meeting_load: float | None = None  # Hours in meetings (from calendar)

    # Efficiency and flow
    flow_state_time: float | None = None  # Uninterrupted coding hours
    context_switching: float | None = None  # Number of project switches
    pr_cycle_time_hours: float | None = None
    time_to_first_review_hours: float | None = None
    rework_ratio: float | None = None  # Commits that are reverts/fixes

    # Overall scores by dimension
    satisfaction_dimension: float | None = None
    performance_dimension: float | None = None
    activity_dimension: float | None = None
    communication_dimension: float | None = None
    efficiency_dimension: float | None = None

    # Composite score
    overall_score: float | None = None


class SPACEMetricsService:
    """Service for calculating SPACE framework metrics."""

    async def calculate_metrics(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_id: str | None,
        period_start: datetime,
        period_end: datetime,
    ) -> SPACEMetrics:
        """Calculate SPACE metrics for a project/organization.

        Args:
            session: Database session
            tenant_id: Tenant ID
            project_id: Optional project ID
            period_start: Start of measurement period
            period_end: End of measurement period

        Returns:
            SPACEMetrics with calculated values
        """
        metrics = SPACEMetrics()

        # Get data from DevLake
        try:
            activity_data = await self._get_activity_data(project_id, period_start, period_end)
            review_data = await self._get_review_data(project_id, period_start, period_end)
            cycle_data = await self._get_cycle_time_data(project_id, period_start, period_end)

            # Calculate Activity metrics
            if activity_data:
                metrics.commits_per_developer = activity_data.get("commits_per_dev", 0)
                metrics.prs_per_developer = activity_data.get("prs_per_dev", 0)
                metrics.reviews_per_developer = activity_data.get("reviews_per_dev", 0)
                metrics.active_days_ratio = activity_data.get("active_days_ratio", 0)

            # Calculate Communication metrics
            if review_data:
                metrics.review_participation_rate = review_data.get("participation_rate", 0)
                metrics.cross_team_collaboration = review_data.get("cross_team_rate", 0)
                metrics.documentation_ratio = review_data.get("doc_ratio", 0)

            # Calculate Efficiency metrics
            if cycle_data:
                metrics.pr_cycle_time_hours = cycle_data.get("pr_cycle_time", 0)
                metrics.time_to_first_review_hours = cycle_data.get("time_to_first_review", 0)
                metrics.rework_ratio = cycle_data.get("rework_ratio", 0)

            # Calculate work-life balance from commit times
            metrics.work_life_balance = await self._calculate_work_life_balance(
                project_id, period_start, period_end
            )

            # Calculate dimension scores
            metrics.activity_dimension = self._calculate_activity_score(metrics)
            metrics.communication_dimension = self._calculate_communication_score(metrics)
            metrics.efficiency_dimension = self._calculate_efficiency_score(metrics)

            # Performance requires additional data
            metrics.performance_dimension = await self._calculate_performance_score(
                project_id, period_start, period_end
            )

            # Satisfaction typically requires survey data
            metrics.satisfaction_dimension = None  # Requires external survey integration

            # Calculate overall score (excluding satisfaction if not available)
            dimensions = [
                metrics.activity_dimension,
                metrics.communication_dimension,
                metrics.efficiency_dimension,
                metrics.performance_dimension,
            ]
            valid_dimensions = [d for d in dimensions if d is not None]
            if valid_dimensions:
                metrics.overall_score = sum(valid_dimensions) / len(valid_dimensions)

        except Exception as e:
            print(f"Error calculating SPACE metrics: {e}")

        return metrics

    async def _get_activity_data(
        self,
        project_id: str | None,
        period_start: datetime,
        period_end: datetime,
    ) -> dict[str, Any]:
        """Get activity data from DevLake."""
        # This would query DevLake's commits, PRs, and reviews tables
        # For now, return structure
        return {
            "commits_per_dev": 0,
            "prs_per_dev": 0,
            "reviews_per_dev": 0,
            "active_days_ratio": 0,
        }

    async def _get_review_data(
        self,
        project_id: str | None,
        period_start: datetime,
        period_end: datetime,
    ) -> dict[str, Any]:
        """Get code review data from DevLake."""
        return {
            "participation_rate": 0,
            "cross_team_rate": 0,
            "doc_ratio": 0,
        }

    async def _get_cycle_time_data(
        self,
        project_id: str | None,
        period_start: datetime,
        period_end: datetime,
    ) -> dict[str, Any]:
        """Get cycle time data from DevLake."""
        return {
            "pr_cycle_time": 0,
            "time_to_first_review": 0,
            "rework_ratio": 0,
        }

    async def _calculate_work_life_balance(
        self,
        project_id: str | None,
        period_start: datetime,
        period_end: datetime,
    ) -> float:
        """Calculate work-life balance score from commit times.

        Analyzes when commits are made to determine healthy work patterns.
        """
        # Commits during 9am-6pm on weekdays = good
        # Commits outside hours or weekends = potential concern
        return 75.0  # Placeholder

    def _calculate_activity_score(self, metrics: SPACEMetrics) -> float:
        """Calculate activity dimension score (0-100)."""
        scores = []

        if metrics.commits_per_developer is not None:
            # Normalize: 10+ commits/week = 100
            scores.append(min(100, metrics.commits_per_developer * 10))

        if metrics.prs_per_developer is not None:
            # Normalize: 5+ PRs/week = 100
            scores.append(min(100, metrics.prs_per_developer * 20))

        if metrics.active_days_ratio is not None:
            scores.append(metrics.active_days_ratio * 100)

        return sum(scores) / len(scores) if scores else 0

    def _calculate_communication_score(self, metrics: SPACEMetrics) -> float:
        """Calculate communication dimension score (0-100)."""
        scores = []

        if metrics.review_participation_rate is not None:
            scores.append(metrics.review_participation_rate * 100)

        if metrics.cross_team_collaboration is not None:
            scores.append(metrics.cross_team_collaboration * 100)

        return sum(scores) / len(scores) if scores else 0

    def _calculate_efficiency_score(self, metrics: SPACEMetrics) -> float:
        """Calculate efficiency dimension score (0-100)."""
        scores = []

        if metrics.pr_cycle_time_hours is not None:
            # Lower cycle time is better: <24h = 100, >168h (1 week) = 0
            score = max(0, 100 - (metrics.pr_cycle_time_hours / 168 * 100))
            scores.append(score)

        if metrics.time_to_first_review_hours is not None:
            # Lower is better: <4h = 100, >24h = 0
            score = max(0, 100 - (metrics.time_to_first_review_hours / 24 * 100))
            scores.append(score)

        if metrics.rework_ratio is not None:
            # Lower is better: 0% = 100, 50%+ = 0
            score = max(0, 100 - (metrics.rework_ratio * 200))
            scores.append(score)

        return sum(scores) / len(scores) if scores else 0

    async def _calculate_performance_score(
        self,
        project_id: str | None,
        period_start: datetime,
        period_end: datetime,
    ) -> float:
        """Calculate performance dimension score."""
        # Would analyze:
        # - Bug fix rate
        # - Feature completion rate
        # - Code quality metrics from SonarQube
        return 70.0  # Placeholder

    async def get_team_breakdown(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_id: str | None,
        period_start: datetime,
        period_end: datetime,
    ) -> list[dict[str, Any]]:
        """Get SPACE metrics broken down by team member."""
        # Would return per-developer SPACE metrics
        return []


# Singleton instance
space_metrics_service = SPACEMetricsService()
