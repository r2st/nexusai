"""Recommendation Engine - Generates actionable improvement recommendations."""

import logging
import uuid
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

from app.services.predictive.models import (
    Bottleneck,
    Recommendation,
    RecommendationType,
    RiskAssessment,
    RiskLevel,
    TrendPrediction,
    TrendDirection,
)


class RecommendationEngine:
    """Generates actionable recommendations based on analytics.

    Analyzes trends, bottlenecks, and risks to provide prioritized
    improvement suggestions.
    """

    def __init__(self, llm_gateway: Any | None = None):
        """Initialize recommendation engine.

        Args:
            llm_gateway: Optional LLM gateway for AI-powered recommendations
        """
        self._llm_gateway = llm_gateway

    def generate_recommendations(
        self,
        trends: list[TrendPrediction] | None = None,
        bottlenecks: list[Bottleneck] | None = None,
        risk_assessment: RiskAssessment | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> list[Recommendation]:
        """Generate recommendations from various inputs.

        Args:
            trends: Trend predictions
            bottlenecks: Detected bottlenecks
            risk_assessment: Risk assessment
            metrics: Current metric values

        Returns:
            Prioritized list of recommendations
        """
        recommendations = []

        # Generate recommendations from each source
        if trends:
            recommendations.extend(self._from_trends(trends))

        if bottlenecks:
            recommendations.extend(self._from_bottlenecks(bottlenecks))

        if risk_assessment:
            recommendations.extend(self._from_risk_assessment(risk_assessment))

        if metrics:
            recommendations.extend(self._from_metrics(metrics))

        # Deduplicate and prioritize
        recommendations = self._deduplicate(recommendations)
        recommendations = self._prioritize(recommendations)

        return recommendations[:20]  # Return top 20

    def _from_trends(self, trends: list[TrendPrediction]) -> list[Recommendation]:
        """Generate recommendations from trend predictions."""
        recommendations = []

        for trend in trends:
            if trend.direction == TrendDirection.DECLINING:
                rec = self._create_trend_recommendation(trend)
                if rec:
                    recommendations.append(rec)
            elif trend.direction == TrendDirection.VOLATILE:
                recommendations.append(self._create_volatility_recommendation(trend))

        return recommendations

    def _create_trend_recommendation(
        self,
        trend: TrendPrediction,
    ) -> Recommendation | None:
        """Create recommendation for a declining trend."""
        # Map metrics to recommendations
        metric_recommendations = {
            "deployment_frequency": Recommendation(
                id=str(uuid.uuid4()),
                type=RecommendationType.PROCESS,
                title="Increase Deployment Frequency",
                description="Deployment frequency is declining, which may indicate process issues or increasing deployment complexity.",
                priority=RiskLevel.HIGH,
                effort="medium",
                impact="high",
                category="DORA",
                metrics_affected=["deployment_frequency", "lead_time"],
                implementation_steps=[
                    "Analyze recent deployment blockers",
                    "Identify manual steps that can be automated",
                    "Implement continuous deployment pipeline",
                    "Set up automatic deployments for low-risk changes",
                ],
                expected_improvement="30-50% increase in deployment frequency within 30 days",
            ),
            "lead_time": Recommendation(
                id=str(uuid.uuid4()),
                type=RecommendationType.PROCESS,
                title="Reduce Lead Time",
                description="Lead time is increasing, meaning it takes longer to get changes to production.",
                priority=RiskLevel.HIGH,
                effort="medium",
                impact="high",
                category="DORA",
                metrics_affected=["lead_time", "cycle_time"],
                implementation_steps=[
                    "Map the value stream to identify delays",
                    "Reduce PR review wait times",
                    "Automate testing and deployment",
                    "Implement WIP limits",
                ],
                expected_improvement="20-40% reduction in lead time",
            ),
            "change_failure_rate": Recommendation(
                id=str(uuid.uuid4()),
                type=RecommendationType.TECHNICAL,
                title="Reduce Change Failure Rate",
                description="Change failure rate is increasing, indicating quality issues in deployments.",
                priority=RiskLevel.CRITICAL,
                effort="high",
                impact="high",
                category="DORA",
                metrics_affected=["change_failure_rate", "mttr"],
                implementation_steps=[
                    "Increase test coverage for critical paths",
                    "Implement canary deployments",
                    "Add pre-deployment health checks",
                    "Review recent failures for patterns",
                ],
                expected_improvement="50% reduction in change failure rate",
            ),
            "mttr": Recommendation(
                id=str(uuid.uuid4()),
                type=RecommendationType.PROCESS,
                title="Improve Mean Time to Recovery",
                description="MTTR is increasing, meaning incident recovery is taking longer.",
                priority=RiskLevel.CRITICAL,
                effort="medium",
                impact="high",
                category="DORA",
                metrics_affected=["mttr"],
                implementation_steps=[
                    "Create runbooks for common incidents",
                    "Improve monitoring and alerting",
                    "Practice incident response drills",
                    "Implement automatic rollback",
                ],
                expected_improvement="40% reduction in MTTR",
            ),
            "test_coverage": Recommendation(
                id=str(uuid.uuid4()),
                type=RecommendationType.TECHNICAL,
                title="Improve Test Coverage",
                description="Test coverage is declining, increasing risk of undetected bugs.",
                priority=RiskLevel.MEDIUM,
                effort="medium",
                impact="medium",
                category="Quality",
                metrics_affected=["test_coverage", "change_failure_rate"],
                implementation_steps=[
                    "Set coverage requirements for new code",
                    "Add tests when fixing bugs",
                    "Implement coverage gates in CI",
                    "Focus on critical path coverage",
                ],
                expected_improvement="10-20% coverage increase per quarter",
            ),
        }

        return metric_recommendations.get(trend.metric_name.lower().replace(" ", "_"))

    def _create_volatility_recommendation(
        self,
        trend: TrendPrediction,
    ) -> Recommendation:
        """Create recommendation for volatile metrics."""
        return Recommendation(
            id=str(uuid.uuid4()),
            type=RecommendationType.PROCESS,
            title=f"Stabilize {trend.metric_name}",
            description=f"{trend.metric_name} shows high volatility ({trend.volatility:.1%}), making planning difficult.",
            priority=RiskLevel.MEDIUM,
            effort="medium",
            impact="medium",
            category="Stability",
            metrics_affected=[trend.metric_name],
            implementation_steps=[
                "Investigate causes of variability",
                "Identify external factors affecting the metric",
                "Implement controls to reduce variance",
                "Set up alerts for unusual changes",
            ],
            expected_improvement="50% reduction in metric volatility",
        )

    def _from_bottlenecks(self, bottlenecks: list[Bottleneck]) -> list[Recommendation]:
        """Generate recommendations from bottlenecks."""
        recommendations = []

        for bottleneck in bottlenecks:
            rec = Recommendation(
                id=str(uuid.uuid4()),
                type=self._bottleneck_to_rec_type(bottleneck.type),
                title=f"Address {bottleneck.location} Bottleneck",
                description=bottleneck.description,
                priority=bottleneck.severity,
                effort=self._estimate_effort(bottleneck.severity),
                impact=self._estimate_impact(bottleneck.impact_score),
                category="Bottleneck",
                metrics_affected=bottleneck.affected_metrics,
                implementation_steps=bottleneck.suggested_actions,
                expected_improvement=f"Reduce {bottleneck.location.lower()} delays by 30-50%",
                evidence=bottleneck.evidence,
            )
            recommendations.append(rec)

        return recommendations

    def _bottleneck_to_rec_type(self, bottleneck_type) -> RecommendationType:
        """Map bottleneck type to recommendation type."""
        mapping = {
            "code_review": RecommendationType.PROCESS,
            "deployment": RecommendationType.TOOLING,
            "testing": RecommendationType.TECHNICAL,
            "merge_conflicts": RecommendationType.PROCESS,
            "resource": RecommendationType.RESOURCE,
            "process": RecommendationType.PROCESS,
            "communication": RecommendationType.TEAM,
            "technical_debt": RecommendationType.TECHNICAL,
        }
        return mapping.get(bottleneck_type.value, RecommendationType.PROCESS)

    def _from_risk_assessment(
        self,
        risk: RiskAssessment,
    ) -> list[Recommendation]:
        """Generate recommendations from risk assessment."""
        if risk.level in (RiskLevel.LOW, RiskLevel.MINIMAL):
            return []

        recommendations = []

        # Convert risk recommendations to Recommendation objects
        for i, rec_text in enumerate(risk.recommendations[:5]):
            recommendations.append(Recommendation(
                id=str(uuid.uuid4()),
                type=RecommendationType.PROCESS,
                title=rec_text,
                description=f"Based on risk assessment (score: {risk.overall_score}/10)",
                priority=risk.level,
                effort="low" if i < 2 else "medium",
                impact="high" if risk.level == RiskLevel.CRITICAL else "medium",
                category="Risk Mitigation",
                metrics_affected=[],
                implementation_steps=[rec_text],
                expected_improvement="Reduce deployment risk",
            ))

        return recommendations

    def _from_metrics(self, metrics: dict[str, Any]) -> list[Recommendation]:
        """Generate recommendations from current metrics."""
        recommendations = []

        # Check for specific metric thresholds
        if metrics.get("test_coverage_percent", 100) < 60:
            recommendations.append(Recommendation(
                id=str(uuid.uuid4()),
                type=RecommendationType.TECHNICAL,
                title="Improve Test Coverage",
                description=f"Test coverage is at {metrics['test_coverage_percent']}%, below recommended 60%",
                priority=RiskLevel.MEDIUM,
                effort="medium",
                impact="high",
                category="Quality",
                metrics_affected=["test_coverage", "defect_rate"],
                implementation_steps=[
                    "Identify critical untested paths",
                    "Add unit tests for core business logic",
                    "Implement integration tests for APIs",
                    "Set coverage gates in CI pipeline",
                ],
                expected_improvement="Reach 60% coverage within 1-2 sprints",
            ))

        if metrics.get("avg_review_time_hours", 0) > 48:
            recommendations.append(Recommendation(
                id=str(uuid.uuid4()),
                type=RecommendationType.PROCESS,
                title="Reduce Code Review Turnaround",
                description=f"Average review time is {metrics['avg_review_time_hours']:.0f} hours",
                priority=RiskLevel.HIGH,
                effort="low",
                impact="high",
                category="Velocity",
                metrics_affected=["lead_time", "developer_satisfaction"],
                implementation_steps=[
                    "Set review SLAs (24-48 hours)",
                    "Implement reviewer rotation",
                    "Use async review tools",
                    "Break large PRs into smaller ones",
                ],
                expected_improvement="Reduce review time to under 24 hours",
            ))

        if metrics.get("deployment_frequency_days", 0) > 7:
            recommendations.append(Recommendation(
                id=str(uuid.uuid4()),
                type=RecommendationType.TOOLING,
                title="Increase Deployment Frequency",
                description=f"Deploying every {metrics['deployment_frequency_days']:.0f} days is below industry standard",
                priority=RiskLevel.HIGH,
                effort="high",
                impact="high",
                category="DORA",
                metrics_affected=["deployment_frequency", "lead_time"],
                implementation_steps=[
                    "Implement CI/CD pipeline",
                    "Automate testing and deployment",
                    "Use feature flags for gradual rollout",
                    "Remove manual approval gates where possible",
                ],
                expected_improvement="Deploy multiple times per week",
            ))

        if metrics.get("wip_per_developer", 0) > 3:
            recommendations.append(Recommendation(
                id=str(uuid.uuid4()),
                type=RecommendationType.PROCESS,
                title="Reduce Work in Progress",
                description=f"WIP per developer ({metrics['wip_per_developer']:.1f}) is too high",
                priority=RiskLevel.MEDIUM,
                effort="low",
                impact="medium",
                category="Flow",
                metrics_affected=["cycle_time", "throughput"],
                implementation_steps=[
                    "Implement WIP limits on kanban board",
                    "Focus on finishing before starting new work",
                    "Address blockers immediately",
                    "Improve sprint planning",
                ],
                expected_improvement="Reduce WIP to 2 or fewer items per person",
            ))

        return recommendations

    def _estimate_effort(self, severity: RiskLevel) -> str:
        """Estimate effort based on severity."""
        if severity in (RiskLevel.CRITICAL, RiskLevel.HIGH):
            return "high"
        elif severity == RiskLevel.MEDIUM:
            return "medium"
        else:
            return "low"

    def _estimate_impact(self, score: float) -> str:
        """Estimate impact from score."""
        if score >= 7:
            return "high"
        elif score >= 4:
            return "medium"
        else:
            return "low"

    def _deduplicate(
        self,
        recommendations: list[Recommendation],
    ) -> list[Recommendation]:
        """Remove duplicate recommendations."""
        seen_titles = set()
        unique = []

        for rec in recommendations:
            # Normalize title for comparison
            normalized = rec.title.lower().strip()
            if normalized not in seen_titles:
                seen_titles.add(normalized)
                unique.append(rec)

        return unique

    def _prioritize(
        self,
        recommendations: list[Recommendation],
    ) -> list[Recommendation]:
        """Prioritize recommendations by impact and effort."""
        def score(rec: Recommendation) -> tuple:
            # Priority order: Critical > High > Medium > Low > Minimal
            priority_order = {
                RiskLevel.CRITICAL: 0,
                RiskLevel.HIGH: 1,
                RiskLevel.MEDIUM: 2,
                RiskLevel.LOW: 3,
                RiskLevel.MINIMAL: 4,
            }

            # Impact order (higher is better)
            impact_order = {"high": 0, "medium": 1, "low": 2}

            # Effort order (lower is better)
            effort_order = {"low": 0, "medium": 1, "high": 2}

            return (
                priority_order.get(rec.priority, 5),
                impact_order.get(rec.impact, 3),
                effort_order.get(rec.effort, 3),
            )

        return sorted(recommendations, key=score)

    async def generate_ai_recommendations(
        self,
        context: dict[str, Any],
    ) -> list[Recommendation]:
        """Generate AI-powered recommendations using LLM.

        Args:
            context: Full context including metrics, trends, bottlenecks

        Returns:
            AI-generated recommendations
        """
        if not self._llm_gateway:
            return []

        prompt = self._build_recommendation_prompt(context)

        try:
            response = await self._llm_gateway.chat(
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
            )

            return self._parse_ai_recommendations(response.content)

        except Exception as e:
            logger.error("Failed to generate AI recommendations", error=str(e))
            return []

    def _get_system_prompt(self) -> str:
        """Get system prompt for AI recommendations."""
        return """You are an expert engineering metrics analyst and coach.

Your task is to analyze engineering metrics and provide actionable recommendations
to improve team performance, quality, and delivery velocity.

Focus on:
1. DORA metrics improvement
2. Process bottleneck resolution
3. Technical debt reduction
4. Team efficiency optimization

Provide specific, actionable recommendations with clear implementation steps."""

    def _build_recommendation_prompt(self, context: dict[str, Any]) -> str:
        """Build prompt for AI recommendations."""
        return f"""Analyze the following engineering metrics and provide recommendations:

## Current Metrics
{context.get('metrics', {})}

## Trend Analysis
{context.get('trends', [])}

## Detected Bottlenecks
{context.get('bottlenecks', [])}

Please provide 3-5 specific recommendations in JSON format:
[{{"title": "...", "description": "...", "steps": ["..."], "impact": "high/medium/low"}}]"""

    def _parse_ai_recommendations(self, content: str) -> list[Recommendation]:
        """Parse AI response into recommendations."""
        import json

        try:
            # Extract JSON from response
            if "```json" in content:
                start = content.index("```json") + 7
                end = content.index("```", start)
                content = content[start:end]

            data = json.loads(content)

            recommendations = []
            for item in data:
                recommendations.append(Recommendation(
                    id=str(uuid.uuid4()),
                    type=RecommendationType.PROCESS,
                    title=item.get("title", "AI Recommendation"),
                    description=item.get("description", ""),
                    priority=RiskLevel.MEDIUM,
                    effort="medium",
                    impact=item.get("impact", "medium"),
                    category="AI-Generated",
                    implementation_steps=item.get("steps", []),
                ))

            return recommendations

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("Failed to parse AI recommendations response", error=str(e))
            return []
