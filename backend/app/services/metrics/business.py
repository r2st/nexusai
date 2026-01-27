"""Business Metrics Service.

Novel business metrics for engineering organizations:
- Engineering Leverage Score (ELS)
- Delivery Predictability Index (DPI)
- Innovation Quotient (IQ)
- Value Stream Efficiency (VSE)
- Team Health Composite (THC)
- Knowledge Distribution Score (KDS)
"""

from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession


class BusinessMetrics(BaseModel):
    """Business metrics model with 6 novel metrics."""

    # Engineering Leverage Score (ELS)
    # Measures how effectively engineering effort translates to business value
    engineering_leverage_score: float | None = None
    els_components: dict[str, float] = {}

    # Delivery Predictability Index (DPI)
    # Measures consistency of delivery against commitments
    delivery_predictability_index: float | None = None
    dpi_components: dict[str, float] = {}

    # Innovation Quotient (IQ)
    # Measures innovation vs maintenance balance
    innovation_quotient: float | None = None
    iq_components: dict[str, float] = {}

    # Value Stream Efficiency (VSE)
    # Measures flow efficiency from idea to production
    value_stream_efficiency: float | None = None
    vse_components: dict[str, float] = {}

    # Team Health Composite (THC)
    # Aggregates team health indicators
    team_health_composite: float | None = None
    thc_components: dict[str, float] = {}

    # Knowledge Distribution Score (KDS)
    # Measures knowledge sharing and bus factor
    knowledge_distribution_score: float | None = None
    kds_components: dict[str, float] = {}

    # Period
    period_start: datetime | None = None
    period_end: datetime | None = None


class BusinessMetricsService:
    """Service for calculating novel business metrics."""

    async def calculate_metrics(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_id: str | None,
        period_start: datetime,
        period_end: datetime,
    ) -> BusinessMetrics:
        """Calculate all business metrics for a project/organization.

        Args:
            session: Database session
            tenant_id: Tenant ID
            project_id: Optional project ID
            period_start: Start of measurement period
            period_end: End of measurement period

        Returns:
            BusinessMetrics with calculated values
        """
        metrics = BusinessMetrics(
            period_start=period_start,
            period_end=period_end,
        )

        # Calculate each metric
        metrics.engineering_leverage_score, metrics.els_components = \
            await self._calculate_els(session, tenant_id, project_id, period_start, period_end)

        metrics.delivery_predictability_index, metrics.dpi_components = \
            await self._calculate_dpi(session, tenant_id, project_id, period_start, period_end)

        metrics.innovation_quotient, metrics.iq_components = \
            await self._calculate_iq(session, tenant_id, project_id, period_start, period_end)

        metrics.value_stream_efficiency, metrics.vse_components = \
            await self._calculate_vse(session, tenant_id, project_id, period_start, period_end)

        metrics.team_health_composite, metrics.thc_components = \
            await self._calculate_thc(session, tenant_id, project_id, period_start, period_end)

        metrics.knowledge_distribution_score, metrics.kds_components = \
            await self._calculate_kds(session, tenant_id, project_id, period_start, period_end)

        return metrics

    async def _calculate_els(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_id: str | None,
        period_start: datetime,
        period_end: datetime,
    ) -> tuple[float, dict[str, float]]:
        """Calculate Engineering Leverage Score.

        ELS = (Business Value Delivered) / (Engineering Effort)

        Components:
        - Feature velocity (story points / sprint)
        - Customer impact score (from feature flags, usage metrics)
        - Revenue impact (if tracked)
        - Cost efficiency (value per engineering hour)
        """
        components = {
            "feature_velocity": 0.0,
            "customer_impact": 0.0,
            "cost_efficiency": 0.0,
            "automation_ratio": 0.0,
        }

        # Feature velocity: story points completed per developer per sprint
        # Higher is better, normalized to 0-100
        components["feature_velocity"] = 70.0  # Placeholder

        # Customer impact: features adopted / features shipped
        components["customer_impact"] = 80.0  # Placeholder

        # Cost efficiency: value delivered per engineering dollar
        components["cost_efficiency"] = 75.0  # Placeholder

        # Automation ratio: automated tests / manual tests, CI time saved
        components["automation_ratio"] = 85.0  # Placeholder

        # Weighted average
        weights = {
            "feature_velocity": 0.3,
            "customer_impact": 0.35,
            "cost_efficiency": 0.2,
            "automation_ratio": 0.15,
        }

        score = sum(components[k] * weights[k] for k in components)
        return score, components

    async def _calculate_dpi(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_id: str | None,
        period_start: datetime,
        period_end: datetime,
    ) -> tuple[float, dict[str, float]]:
        """Calculate Delivery Predictability Index.

        DPI measures how consistently teams deliver against commitments.

        Components:
        - Sprint commitment accuracy (planned vs delivered)
        - Release date accuracy
        - Scope change frequency
        - Estimation accuracy
        """
        components = {
            "sprint_accuracy": 0.0,
            "release_accuracy": 0.0,
            "scope_stability": 0.0,
            "estimation_accuracy": 0.0,
        }

        # Sprint accuracy: % of committed items delivered
        components["sprint_accuracy"] = 85.0  # Placeholder

        # Release accuracy: % of releases on time
        components["release_accuracy"] = 75.0  # Placeholder

        # Scope stability: 100 - (% scope changes mid-sprint)
        components["scope_stability"] = 80.0  # Placeholder

        # Estimation accuracy: actual vs estimated (normalized)
        components["estimation_accuracy"] = 70.0  # Placeholder

        # Weighted average
        weights = {
            "sprint_accuracy": 0.35,
            "release_accuracy": 0.25,
            "scope_stability": 0.2,
            "estimation_accuracy": 0.2,
        }

        score = sum(components[k] * weights[k] for k in components)
        return score, components

    async def _calculate_iq(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_id: str | None,
        period_start: datetime,
        period_end: datetime,
    ) -> tuple[float, dict[str, float]]:
        """Calculate Innovation Quotient.

        IQ measures the balance between innovation and maintenance.

        Components:
        - New feature ratio (new features / total work)
        - Tech debt ratio (time spent on tech debt)
        - Experimentation rate (experiments run)
        - Innovation time allocation (% time for innovation)
        """
        components = {
            "new_feature_ratio": 0.0,
            "tech_debt_management": 0.0,
            "experimentation_rate": 0.0,
            "innovation_allocation": 0.0,
        }

        # New feature ratio: new features / total items
        components["new_feature_ratio"] = 60.0  # Placeholder

        # Tech debt: inverse of tech debt accumulation
        components["tech_debt_management"] = 70.0  # Placeholder

        # Experimentation: experiments per quarter
        components["experimentation_rate"] = 50.0  # Placeholder

        # Innovation time: % time on innovation vs maintenance
        components["innovation_allocation"] = 40.0  # Placeholder

        # Weighted average
        weights = {
            "new_feature_ratio": 0.3,
            "tech_debt_management": 0.25,
            "experimentation_rate": 0.25,
            "innovation_allocation": 0.2,
        }

        score = sum(components[k] * weights[k] for k in components)
        return score, components

    async def _calculate_vse(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_id: str | None,
        period_start: datetime,
        period_end: datetime,
    ) -> tuple[float, dict[str, float]]:
        """Calculate Value Stream Efficiency.

        VSE measures flow efficiency from idea to production.

        Components:
        - Lead time efficiency (value-add time / total time)
        - Deployment frequency (from DORA)
        - Batch size (smaller is better)
        - Work in progress limits
        """
        components = {
            "lead_time_efficiency": 0.0,
            "deployment_frequency": 0.0,
            "batch_size": 0.0,
            "wip_management": 0.0,
        }

        # Lead time efficiency: coding time / total lead time
        components["lead_time_efficiency"] = 65.0  # Placeholder

        # Deployment frequency: normalized (daily = 100)
        components["deployment_frequency"] = 70.0  # Placeholder

        # Batch size: inverse of PR size (smaller is better)
        components["batch_size"] = 80.0  # Placeholder

        # WIP management: items in progress vs capacity
        components["wip_management"] = 75.0  # Placeholder

        # Weighted average
        weights = {
            "lead_time_efficiency": 0.3,
            "deployment_frequency": 0.3,
            "batch_size": 0.2,
            "wip_management": 0.2,
        }

        score = sum(components[k] * weights[k] for k in components)
        return score, components

    async def _calculate_thc(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_id: str | None,
        period_start: datetime,
        period_end: datetime,
    ) -> tuple[float, dict[str, float]]:
        """Calculate Team Health Composite.

        THC aggregates team health indicators.

        Components:
        - Work distribution balance
        - Collaboration score
        - Burnout risk (inverse)
        - Retention indicators
        """
        components = {
            "work_distribution": 0.0,
            "collaboration_score": 0.0,
            "burnout_risk": 0.0,
            "engagement": 0.0,
        }

        # Work distribution: how evenly work is distributed
        components["work_distribution"] = 75.0  # Placeholder

        # Collaboration: cross-team reviews, pair programming
        components["collaboration_score"] = 80.0  # Placeholder

        # Burnout risk: inverse (100 = low risk)
        components["burnout_risk"] = 85.0  # Placeholder

        # Engagement: activity patterns, response times
        components["engagement"] = 78.0  # Placeholder

        # Weighted average
        weights = {
            "work_distribution": 0.25,
            "collaboration_score": 0.25,
            "burnout_risk": 0.25,
            "engagement": 0.25,
        }

        score = sum(components[k] * weights[k] for k in components)
        return score, components

    async def _calculate_kds(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_id: str | None,
        period_start: datetime,
        period_end: datetime,
    ) -> tuple[float, dict[str, float]]:
        """Calculate Knowledge Distribution Score.

        KDS measures knowledge sharing and bus factor.

        Components:
        - Bus factor (how many people know each area)
        - Documentation coverage
        - Cross-training rate
        - Knowledge sharing activities
        """
        components = {
            "bus_factor": 0.0,
            "documentation_coverage": 0.0,
            "cross_training": 0.0,
            "knowledge_sharing": 0.0,
        }

        # Bus factor: min people per code area (normalized)
        # 1 = risky (0), 3+ = good (100)
        components["bus_factor"] = 60.0  # Placeholder

        # Documentation: % of code with docs
        components["documentation_coverage"] = 55.0  # Placeholder

        # Cross-training: developers who've touched multiple areas
        components["cross_training"] = 70.0  # Placeholder

        # Knowledge sharing: reviews, pair sessions, demos
        components["knowledge_sharing"] = 65.0  # Placeholder

        # Weighted average
        weights = {
            "bus_factor": 0.35,
            "documentation_coverage": 0.2,
            "cross_training": 0.25,
            "knowledge_sharing": 0.2,
        }

        score = sum(components[k] * weights[k] for k in components)
        return score, components

    async def get_trend(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_id: str | None,
        periods: int = 6,
        granularity: str = "monthly",
    ) -> list[BusinessMetrics]:
        """Get business metrics trend over multiple periods."""
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
                session, tenant_id, project_id, period_start, period_end
            )
            trends.append(metrics)

        return list(reversed(trends))

    async def get_benchmarks(
        self,
        metric_name: str,
    ) -> dict[str, float]:
        """Get industry benchmarks for a metric."""
        benchmarks = {
            "engineering_leverage_score": {
                "poor": 40,
                "average": 60,
                "good": 75,
                "excellent": 90,
            },
            "delivery_predictability_index": {
                "poor": 50,
                "average": 70,
                "good": 85,
                "excellent": 95,
            },
            "innovation_quotient": {
                "poor": 30,
                "average": 50,
                "good": 65,
                "excellent": 80,
            },
            "value_stream_efficiency": {
                "poor": 35,
                "average": 55,
                "good": 70,
                "excellent": 85,
            },
            "team_health_composite": {
                "poor": 45,
                "average": 65,
                "good": 80,
                "excellent": 90,
            },
            "knowledge_distribution_score": {
                "poor": 40,
                "average": 60,
                "good": 75,
                "excellent": 90,
            },
        }
        return benchmarks.get(metric_name, {})


# Singleton instance
business_metrics_service = BusinessMetricsService()
