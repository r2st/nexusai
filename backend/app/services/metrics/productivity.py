"""Productivity Metrics Service.

Individual and team productivity metrics:
- Code velocity
- Review efficiency
- Focus time
- Collaboration patterns
"""

from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.services.devlake import devlake_service

logger = structlog.get_logger()


class IndividualProductivity(BaseModel):
    """Individual developer productivity metrics."""

    developer_id: str | None = None
    developer_name: str | None = None

    # Code metrics
    commits_count: int = 0
    lines_added: int = 0
    lines_deleted: int = 0
    net_lines: int = 0

    # PR metrics
    prs_created: int = 0
    prs_merged: int = 0
    prs_reviewed: int = 0
    avg_pr_size: float = 0.0
    avg_pr_cycle_time: float = 0.0  # Hours

    # Review metrics
    review_comments_given: int = 0
    review_comments_received: int = 0
    avg_review_turnaround: float = 0.0  # Hours

    # Issue metrics
    issues_created: int = 0
    issues_resolved: int = 0
    avg_issue_resolution_time: float = 0.0  # Hours

    # Collaboration
    unique_collaborators: int = 0
    cross_team_contributions: int = 0

    # Derived scores (0-100)
    velocity_score: float = 0.0
    quality_score: float = 0.0
    collaboration_score: float = 0.0
    overall_score: float = 0.0

    # Period
    period_start: datetime | None = None
    period_end: datetime | None = None


class TeamProductivity(BaseModel):
    """Team productivity metrics."""

    team_id: str | None = None
    team_name: str | None = None

    # Aggregate metrics
    total_commits: int = 0
    total_prs: int = 0
    total_reviews: int = 0
    total_issues_resolved: int = 0

    # Throughput
    commits_per_developer: float = 0.0
    prs_per_developer: float = 0.0
    story_points_per_sprint: float = 0.0

    # Quality
    code_review_coverage: float = 0.0  # Percentage of PRs reviewed
    avg_review_depth: float = 0.0  # Comments per review
    defect_density: float = 0.0  # Bugs per 1000 lines

    # Velocity trends
    velocity_trend: str = "stable"  # improving, stable, declining
    velocity_change_percent: float = 0.0

    # Team health indicators
    bus_factor: int = 0  # Min developers to lose to halt work
    knowledge_silos: int = 0  # Files touched by only 1 dev
    collaboration_index: float = 0.0  # Cross-contribution rate

    # Member breakdown
    member_count: int = 0
    active_members: int = 0
    top_contributors: list[dict[str, Any]] = []

    # Period
    period_start: datetime | None = None
    period_end: datetime | None = None


class ProductivityMetricsService:
    """Service for calculating productivity metrics."""

    # Scoring weights
    VELOCITY_WEIGHTS = {
        "commits": 0.2,
        "prs_merged": 0.3,
        "lines_net": 0.1,
        "issues_resolved": 0.4,
    }

    QUALITY_WEIGHTS = {
        "review_participation": 0.3,
        "pr_approval_rate": 0.3,
        "bug_rate": 0.2,
        "test_coverage": 0.2,
    }

    COLLABORATION_WEIGHTS = {
        "reviews_given": 0.3,
        "unique_collaborators": 0.3,
        "cross_team": 0.2,
        "mentoring": 0.2,
    }

    async def calculate_individual_productivity(
        self,
        session: AsyncSession,
        tenant_id: str,
        developer_id: str,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
    ) -> IndividualProductivity:
        """Calculate productivity metrics for an individual developer.

        Args:
            session: Database session
            tenant_id: Tenant ID
            developer_id: Developer/user ID
            period_start: Start of measurement period
            period_end: End of measurement period

        Returns:
            IndividualProductivity metrics
        """
        period_end = period_end or datetime.now()
        period_start = period_start or (period_end - timedelta(days=30))

        metrics = IndividualProductivity(
            developer_id=developer_id,
            period_start=period_start,
            period_end=period_end,
        )

        try:
            # Get developer stats from DevLake
            dev_stats = await devlake_service.get_developer_stats(
                developer_id, period_start, period_end
            )

            if dev_stats:
                metrics.developer_name = dev_stats.get("name", "Unknown")
                metrics.commits_count = dev_stats.get("commits", 0)
                metrics.lines_added = dev_stats.get("lines_added", 0)
                metrics.lines_deleted = dev_stats.get("lines_deleted", 0)
                metrics.net_lines = metrics.lines_added - metrics.lines_deleted

                metrics.prs_created = dev_stats.get("prs_created", 0)
                metrics.prs_merged = dev_stats.get("prs_merged", 0)
                metrics.prs_reviewed = dev_stats.get("prs_reviewed", 0)
                metrics.avg_pr_size = dev_stats.get("avg_pr_size", 0.0)
                metrics.avg_pr_cycle_time = dev_stats.get("avg_pr_cycle_time", 0.0)

                metrics.review_comments_given = dev_stats.get("review_comments_given", 0)
                metrics.review_comments_received = dev_stats.get("review_comments_received", 0)
                metrics.avg_review_turnaround = dev_stats.get("avg_review_turnaround", 0.0)

                metrics.issues_created = dev_stats.get("issues_created", 0)
                metrics.issues_resolved = dev_stats.get("issues_resolved", 0)
                metrics.avg_issue_resolution_time = dev_stats.get("avg_resolution_time", 0.0)

                metrics.unique_collaborators = dev_stats.get("unique_collaborators", 0)
                metrics.cross_team_contributions = dev_stats.get("cross_team", 0)

            # Calculate scores
            metrics.velocity_score = self._calculate_velocity_score(metrics)
            metrics.quality_score = self._calculate_quality_score(metrics)
            metrics.collaboration_score = self._calculate_collaboration_score(metrics)
            metrics.overall_score = (
                metrics.velocity_score * 0.4
                + metrics.quality_score * 0.35
                + metrics.collaboration_score * 0.25
            )

        except Exception as e:
            print(f"Error calculating individual productivity: {e}")

        return metrics

    async def calculate_team_productivity(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_name: str,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
    ) -> TeamProductivity:
        """Calculate productivity metrics for a team/project.

        Args:
            session: Database session
            tenant_id: Tenant ID
            project_name: DevLake project name
            period_start: Start of measurement period
            period_end: End of measurement period

        Returns:
            TeamProductivity metrics
        """
        period_end = period_end or datetime.now()
        period_start = period_start or (period_end - timedelta(days=30))

        metrics = TeamProductivity(
            team_name=project_name,
            period_start=period_start,
            period_end=period_end,
        )

        try:
            # Get team stats from DevLake
            team_stats = await devlake_service.get_project_stats(
                project_name, period_start, period_end
            )

            if team_stats:
                metrics.total_commits = team_stats.get("total_commits", 0)
                metrics.total_prs = team_stats.get("total_prs", 0)
                metrics.total_reviews = team_stats.get("total_reviews", 0)
                metrics.total_issues_resolved = team_stats.get("issues_resolved", 0)

                metrics.member_count = team_stats.get("member_count", 0)
                metrics.active_members = team_stats.get("active_members", 0)

                if metrics.active_members > 0:
                    metrics.commits_per_developer = (
                        metrics.total_commits / metrics.active_members
                    )
                    metrics.prs_per_developer = (
                        metrics.total_prs / metrics.active_members
                    )

                metrics.story_points_per_sprint = team_stats.get("story_points", 0.0)
                metrics.code_review_coverage = team_stats.get("review_coverage", 0.0)
                metrics.avg_review_depth = team_stats.get("avg_review_depth", 0.0)
                metrics.defect_density = team_stats.get("defect_density", 0.0)

                # Health indicators
                metrics.bus_factor = team_stats.get("bus_factor", 0)
                metrics.knowledge_silos = team_stats.get("knowledge_silos", 0)
                metrics.collaboration_index = team_stats.get("collaboration_index", 0.0)

                metrics.top_contributors = team_stats.get("top_contributors", [])[:5]

            # Calculate velocity trend
            metrics.velocity_trend, metrics.velocity_change_percent = (
                await self._calculate_velocity_trend(
                    session, tenant_id, project_name, period_start, period_end
                )
            )

        except Exception as e:
            print(f"Error calculating team productivity: {e}")

        return metrics

    def _calculate_velocity_score(self, metrics: IndividualProductivity) -> float:
        """Calculate velocity score (0-100)."""
        # Normalize each component (assuming reasonable maximums)
        commit_score = min(metrics.commits_count / 50, 1.0) * 100
        pr_score = min(metrics.prs_merged / 10, 1.0) * 100
        lines_score = min(abs(metrics.net_lines) / 2000, 1.0) * 100
        issues_score = min(metrics.issues_resolved / 15, 1.0) * 100

        return (
            commit_score * self.VELOCITY_WEIGHTS["commits"]
            + pr_score * self.VELOCITY_WEIGHTS["prs_merged"]
            + lines_score * self.VELOCITY_WEIGHTS["lines_net"]
            + issues_score * self.VELOCITY_WEIGHTS["issues_resolved"]
        )

    def _calculate_quality_score(self, metrics: IndividualProductivity) -> float:
        """Calculate quality score (0-100)."""
        # Review participation (giving reviews shows quality awareness)
        review_score = min(metrics.prs_reviewed / 10, 1.0) * 100

        # PR approval rate (assume high if merged)
        approval_score = (
            min(metrics.prs_merged / max(metrics.prs_created, 1), 1.0) * 100
        )

        # Review depth
        depth_score = min(metrics.review_comments_given / 20, 1.0) * 100

        return (
            review_score * 0.4
            + approval_score * 0.4
            + depth_score * 0.2
        )

    def _calculate_collaboration_score(self, metrics: IndividualProductivity) -> float:
        """Calculate collaboration score (0-100)."""
        # Reviews given
        review_score = min(metrics.prs_reviewed / 10, 1.0) * 100

        # Unique collaborators
        collab_score = min(metrics.unique_collaborators / 10, 1.0) * 100

        # Cross-team work
        cross_score = min(metrics.cross_team_contributions / 5, 1.0) * 100

        return (
            review_score * self.COLLABORATION_WEIGHTS["reviews_given"]
            + collab_score * self.COLLABORATION_WEIGHTS["unique_collaborators"]
            + cross_score * self.COLLABORATION_WEIGHTS["cross_team"]
            + 50 * self.COLLABORATION_WEIGHTS["mentoring"]  # Default if no data
        )

    async def _calculate_velocity_trend(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_name: str,
        period_start: datetime,
        period_end: datetime,
    ) -> tuple[str, float]:
        """Calculate velocity trend by comparing with previous period."""
        try:
            period_length = period_end - period_start
            prev_start = period_start - period_length
            prev_end = period_start

            # Get current and previous period stats
            current = await devlake_service.get_project_stats(
                project_name, period_start, period_end
            )
            previous = await devlake_service.get_project_stats(
                project_name, prev_start, prev_end
            )

            if not current or not previous:
                return "stable", 0.0

            # Calculate velocity as composite of commits + PRs + issues
            current_velocity = (
                current.get("total_commits", 0)
                + current.get("total_prs", 0) * 2
                + current.get("issues_resolved", 0) * 3
            )
            previous_velocity = (
                previous.get("total_commits", 0)
                + previous.get("total_prs", 0) * 2
                + previous.get("issues_resolved", 0) * 3
            )

            if previous_velocity == 0:
                return "stable", 0.0

            change = ((current_velocity - previous_velocity) / previous_velocity) * 100

            if change > 10:
                return "improving", change
            elif change < -10:
                return "declining", change
            else:
                return "stable", change

        except Exception as e:
            logger.debug("Trend calculation failed, defaulting to stable", error=str(e))
            return "stable", 0.0

    async def get_productivity_leaderboard(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_name: str,
        metric: str = "overall",
        limit: int = 10,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
    ) -> list[IndividualProductivity]:
        """Get top contributors by productivity metric.

        Args:
            session: Database session
            tenant_id: Tenant ID
            project_name: DevLake project name
            metric: Metric to rank by (overall, velocity, quality, collaboration)
            limit: Number of results
            period_start: Start of period
            period_end: End of period

        Returns:
            List of IndividualProductivity sorted by metric
        """
        period_end = period_end or datetime.now()
        period_start = period_start or (period_end - timedelta(days=30))

        results = []

        try:
            # Get all contributors
            contributors = await devlake_service.get_project_contributors(project_name)

            for contributor in contributors[:50]:  # Limit to avoid timeout
                metrics = await self.calculate_individual_productivity(
                    session,
                    tenant_id,
                    contributor["id"],
                    period_start,
                    period_end,
                )
                results.append(metrics)

            # Sort by requested metric
            sort_key = {
                "overall": lambda m: m.overall_score,
                "velocity": lambda m: m.velocity_score,
                "quality": lambda m: m.quality_score,
                "collaboration": lambda m: m.collaboration_score,
            }.get(metric, lambda m: m.overall_score)

            results.sort(key=sort_key, reverse=True)

        except Exception as e:
            print(f"Error getting leaderboard: {e}")

        return results[:limit]

    async def get_productivity_insights(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_name: str,
    ) -> dict[str, Any]:
        """Generate actionable productivity insights.

        Returns insights like:
        - Bottlenecks in review process
        - Knowledge silos to address
        - Underutilized team members
        - Areas for improvement
        """
        insights = {
            "bottlenecks": [],
            "risks": [],
            "opportunities": [],
            "recommendations": [],
        }

        try:
            team_metrics = await self.calculate_team_productivity(
                session, tenant_id, project_name
            )

            # Identify bottlenecks
            if team_metrics.code_review_coverage < 80:
                insights["bottlenecks"].append({
                    "type": "review_coverage",
                    "message": f"Only {team_metrics.code_review_coverage:.1f}% of PRs are reviewed",
                    "severity": "medium",
                })

            # Identify risks
            if team_metrics.bus_factor < 3:
                insights["risks"].append({
                    "type": "bus_factor",
                    "message": f"Bus factor is {team_metrics.bus_factor} - knowledge concentration risk",
                    "severity": "high",
                })

            if team_metrics.knowledge_silos > 10:
                insights["risks"].append({
                    "type": "knowledge_silos",
                    "message": f"{team_metrics.knowledge_silos} files are single-maintainer",
                    "severity": "medium",
                })

            # Opportunities
            if team_metrics.velocity_trend == "improving":
                insights["opportunities"].append({
                    "type": "momentum",
                    "message": f"Team velocity up {team_metrics.velocity_change_percent:.1f}%",
                })

            # Recommendations
            if team_metrics.collaboration_index < 0.5:
                insights["recommendations"].append({
                    "action": "increase_pairing",
                    "message": "Consider pair programming to improve collaboration",
                    "impact": "medium",
                })

            if team_metrics.avg_review_depth < 2:
                insights["recommendations"].append({
                    "action": "review_quality",
                    "message": "Encourage more thorough code reviews",
                    "impact": "high",
                })

        except Exception as e:
            print(f"Error generating insights: {e}")

        return insights


# Singleton instance
productivity_metrics_service = ProductivityMetricsService()
