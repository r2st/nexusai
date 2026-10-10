"""Rollup service for computing and querying metric rollups."""

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.rollups.models import (
    DORArollup,
    MetricRollup,
    RollupGranularity,
    RollupQuery,
    RollupStats,
    SPACERollup,
)

logger = structlog.get_logger()


class RollupService:
    """Service for managing and computing metric rollups."""

    # DORA performance thresholds
    DORA_THRESHOLDS = {
        "deployment_frequency": {
            "elite": 1.0,  # Multiple per day
            "high": 0.14,  # Weekly
            "medium": 0.03,  # Monthly
        },
        "lead_time": {
            "elite": 24,  # < 1 day
            "high": 168,  # < 1 week
            "medium": 720,  # < 1 month
        },
        "mttr": {
            "elite": 1,  # < 1 hour
            "high": 24,  # < 1 day
            "medium": 168,  # < 1 week
        },
        "cfr": {
            "elite": 5,  # < 5%
            "high": 10,  # < 10%
            "medium": 15,  # < 15%
        },
    }

    async def compute_dora_rollup(
        self,
        session: AsyncSession,
        tenant_id: str,
        period_start: datetime,
        period_end: datetime,
        granularity: RollupGranularity,
        project_id: str | None = None,
        team_id: str | None = None,
    ) -> DORArollup:
        """Compute DORA metrics rollup for a time period.

        Args:
            session: Database session
            tenant_id: Tenant ID
            period_start: Start of period
            period_end: End of period
            granularity: Time granularity
            project_id: Optional project filter
            team_id: Optional team filter

        Returns:
            Computed DORA rollup
        """
        rollup = DORArollup(
            tenant_id=tenant_id,
            granularity=granularity,
            period_start=period_start,
            period_end=period_end,
            project_id=project_id,
            team_id=team_id,
        )

        # Calculate period duration in days
        period_days = (period_end - period_start).total_seconds() / 86400

        try:
            # Get deployment data
            deployments = await self._get_deployments(
                session, tenant_id, period_start, period_end, project_id
            )
            rollup.deployment_count = len(deployments)
            rollup.deployment_frequency = rollup.deployment_count / max(period_days, 1)

            # Calculate lead time
            lead_times = await self._get_lead_times(
                session, tenant_id, period_start, period_end, project_id
            )
            if lead_times:
                rollup.lead_time_hours = sum(lead_times) / len(lead_times)
                sorted_times = sorted(lead_times)
                rollup.lead_time_p50 = sorted_times[len(sorted_times) // 2]
                rollup.lead_time_p95 = sorted_times[min(int(len(sorted_times) * 0.95), len(sorted_times) - 1)]
                rollup.data_points += len(lead_times)

            # Get incident data for MTTR
            incidents = await self._get_incidents(
                session, tenant_id, period_start, period_end, project_id
            )
            rollup.incident_count = len(incidents)

            recovery_times = [
                i["recovery_time_hours"]
                for i in incidents
                if i.get("recovery_time_hours")
            ]
            if recovery_times:
                rollup.mttr_hours = sum(recovery_times) / len(recovery_times)
                sorted_times = sorted(recovery_times)
                rollup.mttr_p50 = sorted_times[len(sorted_times) // 2]
                rollup.mttr_p95 = sorted_times[min(int(len(sorted_times) * 0.95), len(sorted_times) - 1)]
                rollup.incidents_resolved = len(recovery_times)

            # Calculate change failure rate
            failed = sum(1 for d in deployments if d.get("failed", False))
            rollup.failed_deployment_count = failed
            if rollup.deployment_count > 0:
                rollup.change_failure_rate = (failed / rollup.deployment_count) * 100

            # Get supporting metrics
            rollup.commits_count = await self._count_commits(
                session, tenant_id, period_start, period_end, project_id
            )
            rollup.prs_merged = await self._count_merged_prs(
                session, tenant_id, period_start, period_end, project_id
            )

            # Determine performance levels
            rollup.deployment_frequency_level = self._get_level(
                "deployment_frequency", rollup.deployment_frequency, higher_is_better=True
            )
            rollup.lead_time_level = self._get_level(
                "lead_time", rollup.lead_time_hours, higher_is_better=False
            )
            rollup.mttr_level = self._get_level(
                "mttr", rollup.mttr_hours, higher_is_better=False
            )
            rollup.cfr_level = self._get_level(
                "cfr", rollup.change_failure_rate, higher_is_better=False
            )
            rollup.overall_level = self._calculate_overall_level(rollup)

            # Check if period is partial
            rollup.is_partial = period_end > datetime.now(UTC)

        except Exception as e:
            logger.error(
                "Failed to compute DORA rollup",
                tenant_id=tenant_id,
                error=str(e),
            )

        return rollup

    async def compute_space_rollup(
        self,
        session: AsyncSession,
        tenant_id: str,
        period_start: datetime,
        period_end: datetime,
        granularity: RollupGranularity,
        project_id: str | None = None,
        team_id: str | None = None,
    ) -> SPACERollup:
        """Compute SPACE metrics rollup for a time period.

        Args:
            session: Database session
            tenant_id: Tenant ID
            period_start: Start of period
            period_end: End of period
            granularity: Time granularity
            project_id: Optional project filter
            team_id: Optional team filter

        Returns:
            Computed SPACE rollup
        """
        rollup = SPACERollup(
            tenant_id=tenant_id,
            granularity=granularity,
            period_start=period_start,
            period_end=period_end,
            project_id=project_id,
            team_id=team_id,
        )

        try:
            # Get developer activity
            developer_stats = await self._get_developer_activity(
                session, tenant_id, period_start, period_end, project_id, team_id
            )

            if developer_stats:
                rollup.active_developers = developer_stats["active_count"]
                rollup.total_developers = developer_stats["total_count"]
                rollup.commits_per_developer = developer_stats.get("commits_per_dev", 0)
                rollup.prs_per_developer = developer_stats.get("prs_per_dev", 0)
                rollup.reviews_per_developer = developer_stats.get("reviews_per_dev", 0)

            # Get review metrics
            review_stats = await self._get_review_stats(
                session, tenant_id, period_start, period_end, project_id
            )

            if review_stats:
                rollup.review_participation_rate = review_stats.get("participation_rate", 0)
                rollup.cross_team_collaboration = review_stats.get("cross_team_rate", 0)

            # Get cycle time metrics
            cycle_stats = await self._get_cycle_time_stats(
                session, tenant_id, period_start, period_end, project_id
            )

            if cycle_stats:
                rollup.pr_cycle_time_hours = cycle_stats.get("avg_cycle_time")
                rollup.time_to_first_review_hours = cycle_stats.get("avg_first_review_time")
                rollup.rework_ratio = cycle_stats.get("rework_ratio", 0)

            # Calculate dimension scores
            rollup.activity_dimension = self._calculate_activity_score(rollup)
            rollup.communication_dimension = self._calculate_communication_score(rollup)
            rollup.efficiency_dimension = self._calculate_efficiency_score(rollup)

            # Calculate overall score
            dimensions = [
                rollup.activity_dimension,
                rollup.communication_dimension,
                rollup.efficiency_dimension,
            ]
            valid_dims = [d for d in dimensions if d is not None]
            if valid_dims:
                rollup.overall_score = sum(valid_dims) / len(valid_dims)

            rollup.is_partial = period_end > datetime.now(UTC)

        except Exception as e:
            logger.error(
                "Failed to compute SPACE rollup",
                tenant_id=tenant_id,
                error=str(e),
            )

        return rollup

    async def save_rollup(
        self,
        session: AsyncSession,
        rollup: MetricRollup,
    ) -> None:
        """Save a computed rollup to the database.

        Args:
            session: Database session
            rollup: Rollup to save
        """
        metric_type = "dora" if isinstance(rollup, DORArollup) else "space"

        await session.execute(
            text("""
                INSERT INTO metric_rollups (
                    id, tenant_id, metric_type, granularity,
                    period_start, period_end, project_id, team_id,
                    computed_at, data_points, is_partial, data
                ) VALUES (
                    :id, :tenant_id, :metric_type, :granularity,
                    :period_start, :period_end, :project_id, :team_id,
                    :computed_at, :data_points, :is_partial, :data
                )
                ON CONFLICT (tenant_id, metric_type, granularity, period_start, project_id)
                DO UPDATE SET
                    computed_at = EXCLUDED.computed_at,
                    data_points = EXCLUDED.data_points,
                    is_partial = EXCLUDED.is_partial,
                    data = EXCLUDED.data
            """),
            {
                "id": rollup.id,
                "tenant_id": rollup.tenant_id,
                "metric_type": metric_type,
                "granularity": rollup.granularity.value,
                "period_start": rollup.period_start,
                "period_end": rollup.period_end,
                "project_id": rollup.project_id,
                "team_id": rollup.team_id,
                "computed_at": rollup.computed_at,
                "data_points": rollup.data_points,
                "is_partial": rollup.is_partial,
                "data": rollup.model_dump(exclude={
                    "id", "tenant_id", "granularity", "period_start",
                    "period_end", "project_id", "team_id", "computed_at",
                    "data_points", "is_partial",
                }),
            },
        )
        await session.flush()

    async def query_rollups(
        self,
        session: AsyncSession,
        query: RollupQuery,
    ) -> list[dict[str, Any]]:
        """Query rollups from the database.

        Args:
            session: Database session
            query: Query parameters

        Returns:
            List of rollup data
        """
        sql = """
            SELECT * FROM metric_rollups
            WHERE tenant_id = :tenant_id
            AND metric_type = :metric_type
            AND granularity = :granularity
            AND period_start >= :start_date
            AND period_end <= :end_date
        """
        params: dict[str, Any] = {
            "tenant_id": query.tenant_id,
            "metric_type": query.metric_type,
            "granularity": query.granularity.value,
            "start_date": query.start_date,
            "end_date": query.end_date,
        }

        if query.project_id:
            sql += " AND (project_id = :project_id OR project_id IS NULL)"
            params["project_id"] = query.project_id

        if query.team_id:
            sql += " AND (team_id = :team_id OR team_id IS NULL)"
            params["team_id"] = query.team_id

        if not query.include_partial:
            sql += " AND is_partial = false"

        sql += " ORDER BY period_start ASC"

        result = await session.execute(text(sql), params)
        rows = result.fetchall()

        rollups = []
        for row in rows:
            rollup_data = {
                "id": row.id,
                "period_start": row.period_start,
                "period_end": row.period_end,
                "computed_at": row.computed_at,
                "is_partial": row.is_partial,
                **(row.data or {}),
            }
            rollups.append(rollup_data)

        # Fill gaps if requested
        if query.fill_gaps:
            rollups = self._fill_time_gaps(
                rollups, query.start_date, query.end_date, query.granularity
            )

        return rollups

    async def get_stats(
        self,
        session: AsyncSession,
        tenant_id: str,
        metric_type: str = "dora",
    ) -> RollupStats:
        """Get rollup statistics for a tenant.

        Args:
            session: Database session
            tenant_id: Tenant ID
            metric_type: Type of metrics

        Returns:
            RollupStats
        """
        stats = RollupStats(tenant_id=tenant_id, metric_type=metric_type)

        result = await session.execute(
            text("""
                SELECT
                    COUNT(*) as total,
                    MIN(period_start) as oldest,
                    MAX(period_end) as latest,
                    granularity,
                    COUNT(*) as count
                FROM metric_rollups
                WHERE tenant_id = :tenant_id AND metric_type = :metric_type
                GROUP BY granularity
            """),
            {"tenant_id": tenant_id, "metric_type": metric_type},
        )

        for row in result.fetchall():
            stats.total_rollups += row.total
            stats.coverage[row.granularity] = row.count
            if row.oldest:
                stats.oldest_rollup_at = row.oldest
            if row.latest:
                stats.latest_rollup_at = row.latest

        return stats

    # Helper methods

    def _get_level(
        self,
        metric: str,
        value: float | None,
        higher_is_better: bool = True,
    ) -> str:
        """Determine performance level for a metric."""
        if value is None:
            return "unknown"

        thresholds = self.DORA_THRESHOLDS.get(metric, {})

        if higher_is_better:
            if value >= thresholds.get("elite", float("inf")):
                return "elite"
            elif value >= thresholds.get("high", float("inf")):
                return "high"
            elif value >= thresholds.get("medium", float("inf")):
                return "medium"
            return "low"
        else:
            if value <= thresholds.get("elite", 0):
                return "elite"
            elif value <= thresholds.get("high", 0):
                return "high"
            elif value <= thresholds.get("medium", 0):
                return "medium"
            return "low"

    def _calculate_overall_level(self, rollup: DORArollup) -> str:
        """Calculate overall DORA level."""
        levels = [
            rollup.deployment_frequency_level,
            rollup.lead_time_level,
            rollup.mttr_level,
            rollup.cfr_level,
        ]
        levels = [l for l in levels if l != "unknown"]

        if not levels:
            return "unknown"

        level_scores = {"elite": 4, "high": 3, "medium": 2, "low": 1}
        avg = sum(level_scores.get(l, 0) for l in levels) / len(levels)

        if avg >= 3.5:
            return "elite"
        elif avg >= 2.5:
            return "high"
        elif avg >= 1.5:
            return "medium"
        return "low"

    def _calculate_activity_score(self, rollup: SPACERollup) -> float | None:
        """Calculate activity dimension score (0-100)."""
        scores = []
        if rollup.commits_per_developer > 0:
            scores.append(min(100, rollup.commits_per_developer * 10))
        if rollup.prs_per_developer > 0:
            scores.append(min(100, rollup.prs_per_developer * 20))
        if rollup.active_days_ratio > 0:
            scores.append(rollup.active_days_ratio * 100)
        return sum(scores) / len(scores) if scores else None

    def _calculate_communication_score(self, rollup: SPACERollup) -> float | None:
        """Calculate communication dimension score (0-100)."""
        scores = []
        if rollup.review_participation_rate > 0:
            scores.append(rollup.review_participation_rate * 100)
        if rollup.cross_team_collaboration > 0:
            scores.append(rollup.cross_team_collaboration * 100)
        return sum(scores) / len(scores) if scores else None

    def _calculate_efficiency_score(self, rollup: SPACERollup) -> float | None:
        """Calculate efficiency dimension score (0-100)."""
        scores = []
        if rollup.pr_cycle_time_hours is not None:
            score = max(0, 100 - (rollup.pr_cycle_time_hours / 168 * 100))
            scores.append(score)
        if rollup.time_to_first_review_hours is not None:
            score = max(0, 100 - (rollup.time_to_first_review_hours / 24 * 100))
            scores.append(score)
        if rollup.rework_ratio > 0:
            score = max(0, 100 - (rollup.rework_ratio * 200))
            scores.append(score)
        return sum(scores) / len(scores) if scores else None

    def _fill_time_gaps(
        self,
        rollups: list[dict[str, Any]],
        start_date: datetime,
        end_date: datetime,
        granularity: RollupGranularity,
    ) -> list[dict[str, Any]]:
        """Fill gaps in rollup data with empty values."""
        if not rollups:
            return []

        # Determine step size
        if granularity == RollupGranularity.HOURLY:
            step = timedelta(hours=1)
        elif granularity == RollupGranularity.DAILY:
            step = timedelta(days=1)
        elif granularity == RollupGranularity.WEEKLY:
            step = timedelta(weeks=1)
        else:
            step = timedelta(days=30)

        # Build lookup
        existing = {r["period_start"]: r for r in rollups}

        filled = []
        current = start_date
        while current < end_date:
            if current in existing:
                filled.append(existing[current])
            else:
                # Add empty rollup
                filled.append({
                    "period_start": current,
                    "period_end": current + step,
                    "is_partial": False,
                    "no_data": True,
                })
            current += step

        return filled

    # Data fetching methods (simplified - would query entities table)

    async def _get_deployments(
        self,
        session: AsyncSession,
        tenant_id: str,
        start: datetime,
        end: datetime,
        project_id: str | None,
    ) -> list[dict[str, Any]]:
        """Get deployments in time range."""
        sql = """
            SELECT data FROM entities
            WHERE tenant_id = :tenant_id
            AND entity_type = 'deployment'
            AND source_created_at >= :start
            AND source_created_at < :end
        """
        params = {"tenant_id": tenant_id, "start": start, "end": end}
        if project_id:
            sql += " AND data->>'repository_id' = :project_id"
            params["project_id"] = project_id

        result = await session.execute(text(sql), params)
        return [{"data": row.data, "failed": row.data.get("status") == "failed"}
                for row in result.fetchall()]

    async def _get_lead_times(
        self,
        session: AsyncSession,
        tenant_id: str,
        start: datetime,
        end: datetime,
        project_id: str | None,
    ) -> list[float]:
        """Get lead times for merged PRs."""
        # In production, this would calculate time from first commit to deployment
        return []

    async def _get_incidents(
        self,
        session: AsyncSession,
        tenant_id: str,
        start: datetime,
        end: datetime,
        project_id: str | None,
    ) -> list[dict[str, Any]]:
        """Get incidents in time range."""
        return []

    async def _count_commits(
        self,
        session: AsyncSession,
        tenant_id: str,
        start: datetime,
        end: datetime,
        project_id: str | None,
    ) -> int:
        """Count commits in time range."""
        sql = """
            SELECT COUNT(*) FROM entities
            WHERE tenant_id = :tenant_id
            AND entity_type = 'commit'
            AND source_created_at >= :start
            AND source_created_at < :end
        """
        result = await session.execute(
            text(sql), {"tenant_id": tenant_id, "start": start, "end": end}
        )
        return result.scalar() or 0

    async def _count_merged_prs(
        self,
        session: AsyncSession,
        tenant_id: str,
        start: datetime,
        end: datetime,
        project_id: str | None,
    ) -> int:
        """Count merged PRs in time range."""
        sql = """
            SELECT COUNT(*) FROM entities
            WHERE tenant_id = :tenant_id
            AND entity_type = 'pull_request'
            AND data->>'merged' = 'true'
            AND source_updated_at >= :start
            AND source_updated_at < :end
        """
        result = await session.execute(
            text(sql), {"tenant_id": tenant_id, "start": start, "end": end}
        )
        return result.scalar() or 0

    async def _get_developer_activity(
        self,
        session: AsyncSession,
        tenant_id: str,
        start: datetime,
        end: datetime,
        project_id: str | None,
        team_id: str | None,
    ) -> dict[str, Any]:
        """Get developer activity statistics."""
        return {
            "active_count": 0,
            "total_count": 0,
            "commits_per_dev": 0,
            "prs_per_dev": 0,
            "reviews_per_dev": 0,
        }

    async def _get_review_stats(
        self,
        session: AsyncSession,
        tenant_id: str,
        start: datetime,
        end: datetime,
        project_id: str | None,
    ) -> dict[str, Any]:
        """Get code review statistics."""
        return {
            "participation_rate": 0,
            "cross_team_rate": 0,
        }

    async def _get_cycle_time_stats(
        self,
        session: AsyncSession,
        tenant_id: str,
        start: datetime,
        end: datetime,
        project_id: str | None,
    ) -> dict[str, Any]:
        """Get cycle time statistics."""
        return {
            "avg_cycle_time": None,
            "avg_first_review_time": None,
            "rework_ratio": 0,
        }


# Global service instance
_rollup_service: RollupService | None = None


def get_rollup_service() -> RollupService:
    """Get the global rollup service instance."""
    global _rollup_service
    if _rollup_service is None:
        _rollup_service = RollupService()
    return _rollup_service
