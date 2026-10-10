"""Unified Metrics Service.

Provides a single entry point for all engineering metrics,
combining DORA, SPACE, Flow, Productivity, and Business metrics
with AI-powered insights generation.
"""

from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

logger = structlog.get_logger()

from app.services.metrics.dora import DORAMetrics, DORAMetricsService, dora_metrics_service
from app.services.metrics.space import SPACEMetricsService
from app.services.metrics.business import BusinessMetricsService
from app.services.metrics.productivity import (
    ProductivityMetricsService,
    TeamProductivity,
    IndividualProductivity,
    productivity_metrics_service,
)
from app.services.metrics.flow import FlowMetrics, FlowMetricsService, flow_metrics_service
from app.services.metrics.insights import (
    AIInsightsGenerator,
    MetricsInsight,
    insights_generator,
)


class UnifiedMetrics(BaseModel):
    """Unified metrics model combining all metric types."""

    # DORA Metrics
    dora: DORAMetrics | None = None

    # Flow Metrics
    flow: FlowMetrics | None = None

    # Team Productivity
    team_productivity: TeamProductivity | None = None

    # AI-Generated Insights
    insights: list[MetricsInsight] = []
    ai_summary: str | None = None

    # Performance Scores (0-100)
    overall_health_score: float = 0.0
    delivery_score: float = 0.0
    quality_score: float = 0.0
    velocity_score: float = 0.0

    # Metadata
    project_name: str | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    generated_at: datetime | None = None


class MetricsDashboardData(BaseModel):
    """Data structure for metrics dashboard."""

    # Current metrics
    current: UnifiedMetrics | None = None

    # Trend data (historical)
    dora_trend: list[DORAMetrics] = []
    flow_trend: list[dict[str, Any]] = []

    # Comparisons
    period_comparison: dict[str, Any] = {}
    benchmark_comparison: dict[str, Any] = {}

    # Charts
    cumulative_flow_diagram: list[dict[str, Any]] = []
    cycle_time_histogram: dict[str, Any] = {}
    throughput_chart: list[dict[str, Any]] = []

    # Top contributors
    top_contributors: list[dict[str, Any]] = []


class UnifiedMetricsService:
    """
    Unified service for engineering metrics.

    Aggregates data from:
    - DORA Metrics (DevLake)
    - Flow Metrics (WIP, Cycle Time, Throughput)
    - Productivity Metrics (Individual & Team)
    - Business Metrics
    - AI-Powered Insights
    """

    def __init__(
        self,
        dora_service: DORAMetricsService | None = None,
        flow_service: FlowMetricsService | None = None,
        productivity_service: ProductivityMetricsService | None = None,
        insights_gen: AIInsightsGenerator | None = None,
    ):
        """Initialize the unified metrics service."""
        self.dora_service = dora_service or dora_metrics_service
        self.flow_service = flow_service or flow_metrics_service
        self.productivity_service = productivity_service or productivity_metrics_service
        self.insights_gen = insights_gen or insights_generator

    async def get_unified_metrics(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_name: str,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
        include_insights: bool = True,
        include_ai_summary: bool = True,
    ) -> UnifiedMetrics:
        """
        Get comprehensive unified metrics for a project.

        Args:
            session: Database session
            tenant_id: Tenant identifier
            project_name: Project/team name in DevLake
            period_start: Start of measurement period
            period_end: End of measurement period
            include_insights: Whether to generate AI insights
            include_ai_summary: Whether to generate AI summary

        Returns:
            UnifiedMetrics with all metric types
        """
        period_end = period_end or datetime.now()
        period_start = period_start or (period_end - timedelta(days=30))

        metrics = UnifiedMetrics(
            project_name=project_name,
            period_start=period_start,
            period_end=period_end,
            generated_at=datetime.now(),
        )

        # Fetch DORA metrics
        try:
            metrics.dora = await self.dora_service.calculate_metrics(
                session, tenant_id, project_name, period_start, period_end
            )
        except Exception as e:
            logger.error("Error fetching DORA metrics", error=str(e))

        # Fetch Flow metrics
        try:
            metrics.flow = await self.flow_service.calculate_metrics(
                project_name, period_start, period_end
            )
        except Exception as e:
            logger.error("Error fetching Flow metrics", error=str(e))

        # Fetch Team Productivity
        try:
            metrics.team_productivity = await self.productivity_service.calculate_team_productivity(
                session, tenant_id, project_name, period_start, period_end
            )
        except Exception as e:
            logger.error("Error fetching productivity metrics", error=str(e))

        # Calculate health scores
        metrics.overall_health_score = self._calculate_health_score(metrics)
        metrics.delivery_score = self._calculate_delivery_score(metrics)
        metrics.quality_score = self._calculate_quality_score(metrics)
        metrics.velocity_score = self._calculate_velocity_score(metrics)

        # Generate AI insights
        if include_insights and metrics.dora:
            try:
                # Get historical DORA for trend analysis
                dora_trends = await self.dora_service.get_trend(
                    session, tenant_id, project_name, periods=6, granularity="weekly"
                )
                metrics.insights = await self.insights_gen.generate_dora_insights(
                    metrics.dora, dora_trends
                )
            except Exception as e:
                logger.error("Error generating insights", error=str(e))

        # Generate AI summary
        if include_ai_summary and metrics.dora:
            try:
                metrics.ai_summary = await self.insights_gen.generate_ai_summary(
                    metrics.dora, metrics.insights
                )
            except Exception as e:
                logger.error("Error generating AI summary", error=str(e))

        return metrics

    async def get_dashboard_data(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_name: str,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
    ) -> MetricsDashboardData:
        """
        Get all data needed for the metrics dashboard.

        Returns structured data for charts, trends, and visualizations.
        """
        period_end = period_end or datetime.now()
        period_start = period_start or (period_end - timedelta(days=30))

        dashboard = MetricsDashboardData()

        # Get current metrics
        dashboard.current = await self.get_unified_metrics(
            session, tenant_id, project_name, period_start, period_end
        )

        # Get DORA trend
        try:
            dashboard.dora_trend = await self.dora_service.get_trend(
                session, tenant_id, project_name, periods=12, granularity="weekly"
            )
        except Exception as e:
            logger.error("Error fetching DORA trend", error=str(e))

        # Get benchmark comparison
        if dashboard.current and dashboard.current.dora:
            try:
                dashboard.benchmark_comparison = await self.dora_service.get_benchmark_comparison(
                    dashboard.current.dora
                )
            except Exception as e:
                logger.error("Error fetching benchmark", error=str(e))

        # Get cumulative flow diagram data
        try:
            dashboard.cumulative_flow_diagram = await self.flow_service.get_cumulative_flow_diagram_data(
                project_name, period_start, period_end
            )
        except Exception as e:
            logger.error("Error fetching CFD data", error=str(e))

        # Get cycle time histogram
        try:
            dashboard.cycle_time_histogram = await self.flow_service.get_cycle_time_histogram(
                project_name, period_start, period_end
            )
        except Exception as e:
            logger.error("Error fetching cycle time histogram", error=str(e))

        # Get throughput run chart
        try:
            dashboard.throughput_chart = await self.flow_service.get_throughput_run_chart(
                project_name, period_start, period_end, granularity="weekly"
            )
        except Exception as e:
            logger.error("Error fetching throughput chart", error=str(e))

        # Get top contributors
        try:
            contributors = await self.productivity_service.get_productivity_leaderboard(
                session, tenant_id, project_name, metric="overall", limit=10
            )
            dashboard.top_contributors = [
                {
                    "name": c.developer_name,
                    "overall_score": c.overall_score,
                    "velocity_score": c.velocity_score,
                    "quality_score": c.quality_score,
                    "commits": c.commits_count,
                    "prs_merged": c.prs_merged,
                }
                for c in contributors
            ]
        except Exception as e:
            logger.error("Error fetching top contributors", error=str(e))

        # Period comparison (current vs previous)
        try:
            period_length = period_end - period_start
            prev_start = period_start - period_length
            prev_end = period_start

            previous_metrics = await self.get_unified_metrics(
                session, tenant_id, project_name, prev_start, prev_end,
                include_insights=False, include_ai_summary=False
            )

            dashboard.period_comparison = self._calculate_period_comparison(
                dashboard.current, previous_metrics
            )
        except Exception as e:
            logger.error("Error calculating period comparison", error=str(e))

        return dashboard

    def _calculate_health_score(self, metrics: UnifiedMetrics) -> float:
        """Calculate overall engineering health score (0-100)."""
        scores = []

        # DORA contribution (40%)
        if metrics.dora and metrics.dora.overall_level:
            dora_score = {
                "elite": 100,
                "high": 80,
                "medium": 60,
                "low": 40,
                "unknown": 50,
            }.get(metrics.dora.overall_level, 50)
            scores.append(("dora", dora_score, 0.4))

        # Flow efficiency contribution (20%)
        if metrics.flow and metrics.flow.flow_efficiency:
            # Flow efficiency is already a percentage
            flow_score = min(metrics.flow.flow_efficiency, 100)
            scores.append(("flow", flow_score, 0.2))

        # Team productivity contribution (20%)
        if metrics.team_productivity:
            prod_score = 50.0  # Default
            if metrics.team_productivity.velocity_trend == "improving":
                prod_score = 80
            elif metrics.team_productivity.velocity_trend == "stable":
                prod_score = 60
            elif metrics.team_productivity.velocity_trend == "declining":
                prod_score = 40
            scores.append(("productivity", prod_score, 0.2))

        # Team health indicators (20%)
        if metrics.team_productivity:
            health_score = 50.0
            if metrics.team_productivity.bus_factor >= 3:
                health_score += 25
            if metrics.team_productivity.collaboration_index >= 0.7:
                health_score += 25
            scores.append(("team_health", min(health_score, 100), 0.2))

        if not scores:
            return 0.0

        # Weighted average
        total_weight = sum(s[2] for s in scores)
        return sum(s[1] * s[2] for s in scores) / total_weight if total_weight > 0 else 0

    def _calculate_delivery_score(self, metrics: UnifiedMetrics) -> float:
        """Calculate delivery performance score."""
        if not metrics.dora:
            return 0.0

        scores = []

        # Deployment frequency
        if metrics.dora.deployment_frequency_level:
            df_score = {"elite": 100, "high": 80, "medium": 60, "low": 40}.get(
                metrics.dora.deployment_frequency_level, 50
            )
            scores.append(df_score)

        # Lead time
        if metrics.dora.lead_time_level:
            lt_score = {"elite": 100, "high": 80, "medium": 60, "low": 40}.get(
                metrics.dora.lead_time_level, 50
            )
            scores.append(lt_score)

        return sum(scores) / len(scores) if scores else 0.0

    def _calculate_quality_score(self, metrics: UnifiedMetrics) -> float:
        """Calculate quality score."""
        if not metrics.dora:
            return 0.0

        scores = []

        # Change failure rate
        if metrics.dora.change_failure_rate_level:
            cfr_score = {"elite": 100, "high": 80, "medium": 60, "low": 40}.get(
                metrics.dora.change_failure_rate_level, 50
            )
            scores.append(cfr_score)

        # MTTR
        if metrics.dora.mttr_level:
            mttr_score = {"elite": 100, "high": 80, "medium": 60, "low": 40}.get(
                metrics.dora.mttr_level, 50
            )
            scores.append(mttr_score)

        # Code review coverage from team productivity
        if metrics.team_productivity and metrics.team_productivity.code_review_coverage:
            scores.append(min(metrics.team_productivity.code_review_coverage, 100))

        return sum(scores) / len(scores) if scores else 0.0

    def _calculate_velocity_score(self, metrics: UnifiedMetrics) -> float:
        """Calculate velocity score."""
        scores = []

        # Throughput from flow metrics
        if metrics.flow and metrics.flow.throughput_mean:
            # Normalize: assume 10 issues/week is good
            throughput_score = min((metrics.flow.throughput_mean / 10) * 100, 100)
            scores.append(throughput_score)

        # Issues completed
        if metrics.flow and metrics.flow.issues_completed:
            # Normalize: assume 20 issues/month is good
            issues_score = min((metrics.flow.issues_completed / 20) * 100, 100)
            scores.append(issues_score)

        # Velocity trend
        if metrics.team_productivity:
            trend_score = {
                "improving": 90,
                "stable": 70,
                "declining": 40,
            }.get(metrics.team_productivity.velocity_trend, 50)
            scores.append(trend_score)

        return sum(scores) / len(scores) if scores else 0.0

    def _calculate_period_comparison(
        self,
        current: UnifiedMetrics | None,
        previous: UnifiedMetrics | None,
    ) -> dict[str, Any]:
        """Calculate comparison between current and previous periods."""
        if not current or not previous:
            return {}

        comparison = {}

        # DORA comparisons
        if current.dora and previous.dora:
            if current.dora.deployment_frequency and previous.dora.deployment_frequency:
                if previous.dora.deployment_frequency > 0:
                    change = (
                        (current.dora.deployment_frequency - previous.dora.deployment_frequency)
                        / previous.dora.deployment_frequency
                    ) * 100
                    comparison["deployment_frequency_change"] = round(change, 1)

            if current.dora.lead_time_for_changes and previous.dora.lead_time_for_changes:
                if previous.dora.lead_time_for_changes > 0:
                    change = (
                        (previous.dora.lead_time_for_changes - current.dora.lead_time_for_changes)
                        / previous.dora.lead_time_for_changes
                    ) * 100  # Negative is good for lead time
                    comparison["lead_time_change"] = round(change, 1)

        # Health score comparison
        if current.overall_health_score and previous.overall_health_score:
            comparison["health_score_change"] = round(
                current.overall_health_score - previous.overall_health_score, 1
            )

        # Flow metrics comparison
        if current.flow and previous.flow:
            if current.flow.issues_completed and previous.flow.issues_completed:
                change = current.flow.issues_completed - previous.flow.issues_completed
                comparison["throughput_change"] = change

        return comparison

    async def get_metrics_summary(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_name: str,
    ) -> dict[str, Any]:
        """Get a quick summary of current metrics state."""
        metrics = await self.get_unified_metrics(
            session, tenant_id, project_name,
            include_insights=False, include_ai_summary=False
        )

        return {
            "project": project_name,
            "overall_health": metrics.overall_health_score,
            "delivery_score": metrics.delivery_score,
            "quality_score": metrics.quality_score,
            "velocity_score": metrics.velocity_score,
            "dora_level": metrics.dora.overall_level if metrics.dora else "unknown",
            "deployment_frequency": metrics.dora.deployment_frequency if metrics.dora else None,
            "lead_time_hours": metrics.dora.lead_time_for_changes if metrics.dora else None,
            "change_failure_rate": metrics.dora.change_failure_rate if metrics.dora else None,
            "mttr_hours": metrics.dora.mean_time_to_recovery if metrics.dora else None,
            "current_wip": metrics.flow.current_wip if metrics.flow else None,
            "flow_efficiency": metrics.flow.flow_efficiency if metrics.flow else None,
            "team_velocity_trend": (
                metrics.team_productivity.velocity_trend
                if metrics.team_productivity else None
            ),
            "generated_at": metrics.generated_at,
        }


# Singleton instance
unified_metrics_service = UnifiedMetricsService()
