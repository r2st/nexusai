"""DORA Metrics Agent for analyzing engineering performance."""

from dataclasses import dataclass, field
from datetime import datetime, UTC, timedelta
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger()


class DORAMetric(str, Enum):
    """The four key DORA metrics."""

    DEPLOYMENT_FREQUENCY = "deployment_frequency"
    LEAD_TIME_FOR_CHANGES = "lead_time_for_changes"
    TIME_TO_RESTORE = "time_to_restore"
    CHANGE_FAILURE_RATE = "change_failure_rate"


class PerformanceLevel(str, Enum):
    """DORA performance levels based on industry benchmarks."""

    ELITE = "elite"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class DORAMetricResult:
    """Result for a single DORA metric."""

    metric: DORAMetric
    value: float
    unit: str
    performance_level: PerformanceLevel
    trend: str  # "improving", "stable", "declining"
    trend_percentage: float
    benchmark_comparison: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class DORAAnalysisResult:
    """Complete DORA analysis result."""

    project_id: str
    period_start: datetime
    period_end: datetime
    metrics: list[DORAMetricResult]
    overall_performance: PerformanceLevel
    recommendations: list[str]
    insights: list[str]
    raw_data: dict[str, Any] = field(default_factory=dict)


class DORAMetricsAgent:
    """Agent specialized in DORA metrics analysis.

    This agent provides:
    - DORA metric calculations (DF, LT, MTTR, CFR)
    - Performance level classification against industry benchmarks
    - Trend analysis over time
    - Actionable recommendations for improvement
    - Natural language explanations of metrics
    """

    # DORA benchmarks from DORA State of DevOps reports
    BENCHMARKS = {
        DORAMetric.DEPLOYMENT_FREQUENCY: {
            PerformanceLevel.ELITE: ("multiple_per_day", "Multiple deploys per day"),
            PerformanceLevel.HIGH: ("daily_to_weekly", "Between once per day and once per week"),
            PerformanceLevel.MEDIUM: ("weekly_to_monthly", "Between once per week and once per month"),
            PerformanceLevel.LOW: ("monthly_plus", "Less than once per month"),
        },
        DORAMetric.LEAD_TIME_FOR_CHANGES: {
            PerformanceLevel.ELITE: (1, "Less than one day"),
            PerformanceLevel.HIGH: (7, "Between one day and one week"),
            PerformanceLevel.MEDIUM: (30, "Between one week and one month"),
            PerformanceLevel.LOW: (180, "More than one month"),
        },
        DORAMetric.TIME_TO_RESTORE: {
            PerformanceLevel.ELITE: (1, "Less than one hour"),
            PerformanceLevel.HIGH: (24, "Less than one day"),
            PerformanceLevel.MEDIUM: (168, "Less than one week"),
            PerformanceLevel.LOW: (720, "More than one week"),
        },
        DORAMetric.CHANGE_FAILURE_RATE: {
            PerformanceLevel.ELITE: (5, "0-5%"),
            PerformanceLevel.HIGH: (10, "5-10%"),
            PerformanceLevel.MEDIUM: (15, "10-15%"),
            PerformanceLevel.LOW: (100, "15%+"),
        },
    }

    def __init__(
        self,
        db_session=None,
        knowledge_graph_client=None,
    ):
        self.db = db_session
        self.kg = knowledge_graph_client
        self.agent_id = "dora-metrics-agent"
        self.agent_name = "DORA Metrics Analyst"
        self.capabilities = [
            "dora_metric_calculation",
            "performance_classification",
            "trend_analysis",
            "benchmark_comparison",
            "recommendation_generation",
        ]

    async def analyze(
        self,
        project_id: str,
        period_days: int = 30,
        compare_to_previous: bool = True,
    ) -> DORAAnalysisResult:
        """Perform complete DORA metrics analysis."""
        period_end = datetime.now(UTC)
        period_start = period_end - timedelta(days=period_days)

        logger.info(
            "Starting DORA analysis",
            project_id=project_id,
            period_days=period_days,
        )

        # Calculate each metric
        metrics = []

        # Deployment Frequency
        df_result = await self._calculate_deployment_frequency(
            project_id, period_start, period_end
        )
        metrics.append(df_result)

        # Lead Time for Changes
        lt_result = await self._calculate_lead_time(
            project_id, period_start, period_end
        )
        metrics.append(lt_result)

        # Time to Restore
        mttr_result = await self._calculate_time_to_restore(
            project_id, period_start, period_end
        )
        metrics.append(mttr_result)

        # Change Failure Rate
        cfr_result = await self._calculate_change_failure_rate(
            project_id, period_start, period_end
        )
        metrics.append(cfr_result)

        # Determine overall performance
        overall = self._calculate_overall_performance(metrics)

        # Generate recommendations
        recommendations = self._generate_recommendations(metrics)

        # Generate insights
        insights = self._generate_insights(metrics)

        result = DORAAnalysisResult(
            project_id=project_id,
            period_start=period_start,
            period_end=period_end,
            metrics=metrics,
            overall_performance=overall,
            recommendations=recommendations,
            insights=insights,
        )

        logger.info(
            "DORA analysis completed",
            project_id=project_id,
            overall_performance=overall.value,
        )

        return result

    async def _calculate_deployment_frequency(
        self,
        project_id: str,
        start: datetime,
        end: datetime,
    ) -> DORAMetricResult:
        """Calculate deployment frequency metric."""
        # In production, this would query the database
        # For now, return mock data structure

        # Query would look like:
        # SELECT COUNT(*) as deployments
        # FROM deployments
        # WHERE project_id = :project_id
        #   AND deployed_at BETWEEN :start AND :end
        #   AND status = 'success'

        days = (end - start).days
        deployments = 45  # Mock value - would come from DB

        daily_rate = deployments / days if days > 0 else 0

        # Classify performance
        if daily_rate >= 1:
            level = PerformanceLevel.ELITE
        elif daily_rate >= 1/7:
            level = PerformanceLevel.HIGH
        elif daily_rate >= 1/30:
            level = PerformanceLevel.MEDIUM
        else:
            level = PerformanceLevel.LOW

        return DORAMetricResult(
            metric=DORAMetric.DEPLOYMENT_FREQUENCY,
            value=daily_rate,
            unit="deployments/day",
            performance_level=level,
            trend="improving",
            trend_percentage=12.5,
            benchmark_comparison=self.BENCHMARKS[DORAMetric.DEPLOYMENT_FREQUENCY][level][1],
            details={
                "total_deployments": deployments,
                "period_days": days,
                "successful_deployments": deployments,
            },
        )

    async def _calculate_lead_time(
        self,
        project_id: str,
        start: datetime,
        end: datetime,
    ) -> DORAMetricResult:
        """Calculate lead time for changes metric."""
        # Query would look like:
        # SELECT AVG(EXTRACT(EPOCH FROM (deployed_at - commit_timestamp)) / 3600) as lead_time_hours
        # FROM deployments d
        # JOIN commits c ON d.commit_sha = c.sha
        # WHERE d.project_id = :project_id
        #   AND d.deployed_at BETWEEN :start AND :end

        lead_time_hours = 18.5  # Mock value - would come from DB

        # Classify performance (in days)
        lead_time_days = lead_time_hours / 24

        if lead_time_days < 1:
            level = PerformanceLevel.ELITE
        elif lead_time_days < 7:
            level = PerformanceLevel.HIGH
        elif lead_time_days < 30:
            level = PerformanceLevel.MEDIUM
        else:
            level = PerformanceLevel.LOW

        return DORAMetricResult(
            metric=DORAMetric.LEAD_TIME_FOR_CHANGES,
            value=lead_time_hours,
            unit="hours",
            performance_level=level,
            trend="stable",
            trend_percentage=-2.3,
            benchmark_comparison=self.BENCHMARKS[DORAMetric.LEAD_TIME_FOR_CHANGES][level][1],
            details={
                "median_lead_time": lead_time_hours * 0.8,
                "p90_lead_time": lead_time_hours * 1.5,
                "sample_size": 45,
            },
        )

    async def _calculate_time_to_restore(
        self,
        project_id: str,
        start: datetime,
        end: datetime,
    ) -> DORAMetricResult:
        """Calculate mean time to restore metric."""
        # Query would look like:
        # SELECT AVG(EXTRACT(EPOCH FROM (resolved_at - created_at)) / 3600) as mttr_hours
        # FROM incidents
        # WHERE project_id = :project_id
        #   AND created_at BETWEEN :start AND :end
        #   AND resolved_at IS NOT NULL

        mttr_hours = 4.2  # Mock value - would come from DB

        # Classify performance
        if mttr_hours < 1:
            level = PerformanceLevel.ELITE
        elif mttr_hours < 24:
            level = PerformanceLevel.HIGH
        elif mttr_hours < 168:
            level = PerformanceLevel.MEDIUM
        else:
            level = PerformanceLevel.LOW

        return DORAMetricResult(
            metric=DORAMetric.TIME_TO_RESTORE,
            value=mttr_hours,
            unit="hours",
            performance_level=level,
            trend="improving",
            trend_percentage=-15.0,
            benchmark_comparison=self.BENCHMARKS[DORAMetric.TIME_TO_RESTORE][level][1],
            details={
                "incidents_count": 8,
                "median_restore_time": mttr_hours * 0.7,
                "max_restore_time": mttr_hours * 3.5,
            },
        )

    async def _calculate_change_failure_rate(
        self,
        project_id: str,
        start: datetime,
        end: datetime,
    ) -> DORAMetricResult:
        """Calculate change failure rate metric."""
        # Query would look like:
        # SELECT
        #   COUNT(CASE WHEN caused_incident THEN 1 END)::float /
        #   NULLIF(COUNT(*), 0) * 100 as cfr_percentage
        # FROM deployments
        # WHERE project_id = :project_id
        #   AND deployed_at BETWEEN :start AND :end

        cfr_percentage = 8.5  # Mock value - would come from DB

        # Classify performance
        if cfr_percentage <= 5:
            level = PerformanceLevel.ELITE
        elif cfr_percentage <= 10:
            level = PerformanceLevel.HIGH
        elif cfr_percentage <= 15:
            level = PerformanceLevel.MEDIUM
        else:
            level = PerformanceLevel.LOW

        return DORAMetricResult(
            metric=DORAMetric.CHANGE_FAILURE_RATE,
            value=cfr_percentage,
            unit="%",
            performance_level=level,
            trend="declining",
            trend_percentage=5.2,
            benchmark_comparison=self.BENCHMARKS[DORAMetric.CHANGE_FAILURE_RATE][level][1],
            details={
                "total_deployments": 45,
                "failed_deployments": 4,
                "rollbacks": 2,
            },
        )

    def _calculate_overall_performance(
        self,
        metrics: list[DORAMetricResult],
    ) -> PerformanceLevel:
        """Calculate overall performance level from individual metrics."""
        level_scores = {
            PerformanceLevel.ELITE: 4,
            PerformanceLevel.HIGH: 3,
            PerformanceLevel.MEDIUM: 2,
            PerformanceLevel.LOW: 1,
        }

        total_score = sum(level_scores[m.performance_level] for m in metrics)
        avg_score = total_score / len(metrics)

        if avg_score >= 3.5:
            return PerformanceLevel.ELITE
        elif avg_score >= 2.5:
            return PerformanceLevel.HIGH
        elif avg_score >= 1.5:
            return PerformanceLevel.MEDIUM
        else:
            return PerformanceLevel.LOW

    def _generate_recommendations(
        self,
        metrics: list[DORAMetricResult],
    ) -> list[str]:
        """Generate actionable recommendations based on metrics."""
        recommendations = []

        for metric in metrics:
            if metric.performance_level in (PerformanceLevel.LOW, PerformanceLevel.MEDIUM):
                if metric.metric == DORAMetric.DEPLOYMENT_FREQUENCY:
                    recommendations.append(
                        "Consider implementing trunk-based development and smaller batch sizes "
                        "to increase deployment frequency. Automate more of your CI/CD pipeline."
                    )
                elif metric.metric == DORAMetric.LEAD_TIME_FOR_CHANGES:
                    recommendations.append(
                        "Reduce lead time by implementing feature flags, automated testing, "
                        "and streamlining code review processes. Consider pair programming."
                    )
                elif metric.metric == DORAMetric.TIME_TO_RESTORE:
                    recommendations.append(
                        "Improve MTTR by implementing better observability, runbooks, "
                        "and on-call procedures. Practice incident response through game days."
                    )
                elif metric.metric == DORAMetric.CHANGE_FAILURE_RATE:
                    recommendations.append(
                        "Reduce change failure rate by improving test coverage, "
                        "implementing canary deployments, and conducting thorough code reviews."
                    )

            if metric.trend == "declining":
                recommendations.append(
                    f"⚠️ {metric.metric.value.replace('_', ' ').title()} is trending negatively "
                    f"({metric.trend_percentage:+.1f}%). Investigate recent changes."
                )

        return recommendations

    def _generate_insights(
        self,
        metrics: list[DORAMetricResult],
    ) -> list[str]:
        """Generate insights from the metrics analysis."""
        insights = []

        # Performance distribution
        elite_count = sum(1 for m in metrics if m.performance_level == PerformanceLevel.ELITE)
        high_count = sum(1 for m in metrics if m.performance_level == PerformanceLevel.HIGH)

        if elite_count >= 3:
            insights.append(
                "🌟 Your team is performing at an elite level across most DORA metrics, "
                "placing you in the top tier of engineering organizations globally."
            )
        elif elite_count + high_count >= 3:
            insights.append(
                "✅ Your team shows strong DevOps performance. Focus on the metrics "
                "that aren't yet at elite level to achieve world-class status."
            )

        # Trend analysis
        improving = [m for m in metrics if m.trend == "improving"]
        declining = [m for m in metrics if m.trend == "declining"]

        if len(improving) > len(declining):
            insights.append(
                f"📈 Positive momentum: {len(improving)} out of 4 metrics are improving."
            )
        elif len(declining) > len(improving):
            insights.append(
                f"📉 Attention needed: {len(declining)} out of 4 metrics are declining."
            )

        return insights

    def format_for_handoff(self, result: DORAAnalysisResult) -> dict[str, Any]:
        """Format analysis result for handoff to next agent."""
        return {
            "agent": self.agent_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "project_id": result.project_id,
            "period": {
                "start": result.period_start.isoformat(),
                "end": result.period_end.isoformat(),
            },
            "overall_performance": result.overall_performance.value,
            "metrics": [
                {
                    "name": m.metric.value,
                    "value": m.value,
                    "unit": m.unit,
                    "performance": m.performance_level.value,
                    "trend": m.trend,
                }
                for m in result.metrics
            ],
            "recommendations": result.recommendations,
            "insights": result.insights,
            "handoff_context": "DORA analysis complete. Ready for visualization or executive summary.",
        }
