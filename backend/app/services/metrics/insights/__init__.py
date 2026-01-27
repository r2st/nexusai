"""AI-powered insights generation for engineering metrics."""

from datetime import datetime
from typing import Any

import structlog
from pydantic import BaseModel

from app.services.metrics.dora import DORAMetrics, DORAMetricsService

logger = structlog.get_logger()


class MetricsInsight(BaseModel):
    """A single insight about metrics."""

    title: str
    description: str
    severity: str = "info"  # info, warning, critical, success
    metric: str | None = None
    recommendations: list[str] = []
    data: dict[str, Any] = {}

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


class AIInsightsGenerator:
    """
    AI-powered insights generator for engineering metrics.

    Uses LLM to generate natural language insights and recommendations
    based on DORA, SPACE, and business metrics.
    """

    def __init__(self, llm_gateway=None):
        """
        Initialize insights generator.

        Args:
            llm_gateway: Optional LLM gateway for AI-powered insights
        """
        self.llm_gateway = llm_gateway

    async def generate_dora_insights(
        self,
        metrics: DORAMetrics,
        trends: list[DORAMetrics] | None = None,
    ) -> list[MetricsInsight]:
        """
        Generate insights from DORA metrics.

        Args:
            metrics: Current DORA metrics
            trends: Historical metrics for trend analysis

        Returns:
            List of insights
        """
        insights = []

        # Deployment Frequency insights
        if metrics.deployment_frequency is not None:
            df_insight = self._analyze_deployment_frequency(metrics, trends)
            if df_insight:
                insights.append(df_insight)

        # Lead Time insights
        if metrics.lead_time_for_changes is not None:
            lt_insight = self._analyze_lead_time(metrics, trends)
            if lt_insight:
                insights.append(lt_insight)

        # Change Failure Rate insights
        if metrics.change_failure_rate is not None:
            cfr_insight = self._analyze_change_failure_rate(metrics, trends)
            if cfr_insight:
                insights.append(cfr_insight)

        # MTTR insights
        if metrics.mean_time_to_recovery is not None:
            mttr_insight = self._analyze_mttr(metrics, trends)
            if mttr_insight:
                insights.append(mttr_insight)

        # Overall performance insight
        overall_insight = self._analyze_overall_performance(metrics)
        if overall_insight:
            insights.append(overall_insight)

        # Trend-based insights
        if trends and len(trends) >= 3:
            trend_insights = self._analyze_trends(trends)
            insights.extend(trend_insights)

        return insights

    def _analyze_deployment_frequency(
        self,
        metrics: DORAMetrics,
        trends: list[DORAMetrics] | None,
    ) -> MetricsInsight | None:
        """Analyze deployment frequency and generate insight."""
        df = metrics.deployment_frequency
        level = metrics.deployment_frequency_level

        if level == "elite":
            return MetricsInsight(
                title="Excellent Deployment Frequency",
                description=f"Your team deploys {df:.2f} times per day, achieving elite-level performance. "
                           "This enables rapid iteration and quick feedback loops.",
                severity="success",
                metric="deployment_frequency",
                recommendations=[
                    "Maintain current CI/CD practices",
                    "Consider trunk-based development if not already using it",
                    "Ensure monitoring keeps pace with deployment frequency",
                ],
                data={"value": df, "level": level, "threshold": 1.0},
            )
        elif level == "high":
            return MetricsInsight(
                title="Strong Deployment Frequency",
                description=f"Your team deploys {df:.2f} times per day (about {df*7:.1f} per week). "
                           "To reach elite level, aim for multiple deployments per day.",
                severity="info",
                metric="deployment_frequency",
                recommendations=[
                    "Reduce batch sizes to enable more frequent deployments",
                    "Automate more of your testing pipeline",
                    "Consider feature flags for safer continuous deployment",
                ],
                data={"value": df, "level": level, "target": 1.0},
            )
        elif level == "medium":
            return MetricsInsight(
                title="Deployment Frequency Needs Improvement",
                description=f"Your team deploys about {df*30:.1f} times per month. "
                           "Infrequent deployments often lead to larger, riskier releases.",
                severity="warning",
                metric="deployment_frequency",
                recommendations=[
                    "Break down large changes into smaller, deployable increments",
                    "Invest in automated testing to build deployment confidence",
                    "Reduce manual approval gates where possible",
                    "Consider implementing continuous integration first",
                ],
                data={"value": df, "level": level, "target": 0.14},
            )
        else:
            return MetricsInsight(
                title="Low Deployment Frequency",
                description=f"Your team deploys less than once per month ({df:.3f}/day). "
                           "This significantly increases deployment risk and slows feedback.",
                severity="critical",
                metric="deployment_frequency",
                recommendations=[
                    "Start with weekly deployments as an initial goal",
                    "Identify and remove deployment bottlenecks",
                    "Implement basic CI/CD if not present",
                    "Focus on reducing the fear of deploying",
                ],
                data={"value": df, "level": level, "target": 0.03},
            )

    def _analyze_lead_time(
        self,
        metrics: DORAMetrics,
        trends: list[DORAMetrics] | None,
    ) -> MetricsInsight | None:
        """Analyze lead time and generate insight."""
        lt = metrics.lead_time_for_changes
        level = metrics.lead_time_level

        if level == "elite":
            return MetricsInsight(
                title="Exceptional Lead Time",
                description=f"Changes reach production in {lt:.1f} hours on average. "
                           "This rapid cycle time enables quick experimentation and learning.",
                severity="success",
                metric="lead_time",
                recommendations=[
                    "Document and share your efficient practices",
                    "Monitor for any degradation as team scales",
                    "Consider A/B testing more frequently",
                ],
                data={"value": lt, "level": level, "unit": "hours"},
            )
        elif level == "high":
            return MetricsInsight(
                title="Good Lead Time Performance",
                description=f"Lead time is {lt:.1f} hours (about {lt/24:.1f} days). "
                           "To reach elite level, aim for under 24 hours.",
                severity="info",
                metric="lead_time",
                recommendations=[
                    "Analyze where time is spent in your pipeline",
                    "Reduce code review wait times",
                    "Parallelize test execution where possible",
                ],
                data={"value": lt, "level": level, "target": 24},
            )
        elif level == "medium":
            return MetricsInsight(
                title="Lead Time Could Be Faster",
                description=f"Changes take {lt/24:.1f} days to reach production. "
                           "Long lead times delay feedback and reduce agility.",
                severity="warning",
                metric="lead_time",
                recommendations=[
                    "Map your value stream to identify bottlenecks",
                    "Consider async code reviews with SLA",
                    "Automate manual testing steps",
                    "Reduce PR sizes for faster reviews",
                ],
                data={"value": lt, "level": level, "target": 168},
            )
        else:
            return MetricsInsight(
                title="Lead Time Needs Significant Improvement",
                description=f"Changes take over {lt/24:.0f} days to reach production. "
                           "This severely limits your ability to respond to market changes.",
                severity="critical",
                metric="lead_time",
                recommendations=[
                    "Conduct a value stream mapping exercise",
                    "Identify and eliminate waiting times",
                    "Consider reorganizing around smaller teams",
                    "Invest in automated testing infrastructure",
                ],
                data={"value": lt, "level": level, "target": 720},
            )

    def _analyze_change_failure_rate(
        self,
        metrics: DORAMetrics,
        trends: list[DORAMetrics] | None,
    ) -> MetricsInsight | None:
        """Analyze change failure rate and generate insight."""
        cfr = metrics.change_failure_rate
        level = metrics.change_failure_rate_level

        if level == "elite":
            return MetricsInsight(
                title="Low Change Failure Rate",
                description=f"Only {cfr:.1f}% of changes cause production issues. "
                           "Your quality practices are highly effective.",
                severity="success",
                metric="change_failure_rate",
                recommendations=[
                    "Continue investing in testing",
                    "Share your quality practices across teams",
                    "Consider chaos engineering to find edge cases",
                ],
                data={"value": cfr, "level": level, "unit": "percent"},
            )
        elif level in ["high", "medium"]:
            severity = "info" if level == "high" else "warning"
            return MetricsInsight(
                title="Moderate Change Failure Rate",
                description=f"{cfr:.1f}% of changes cause issues. "
                           "Focus on shifting quality left to reduce failures.",
                severity=severity,
                metric="change_failure_rate",
                recommendations=[
                    "Increase test coverage, especially integration tests",
                    "Implement feature flags for safer rollouts",
                    "Add production-like staging environments",
                    "Review failed changes for patterns",
                ],
                data={"value": cfr, "level": level, "target": 5},
            )
        else:
            return MetricsInsight(
                title="High Change Failure Rate",
                description=f"{cfr:.1f}% of changes cause production issues. "
                           "This indicates significant quality or process gaps.",
                severity="critical",
                metric="change_failure_rate",
                recommendations=[
                    "Implement mandatory code reviews",
                    "Add automated testing gates before deployment",
                    "Use canary deployments to limit blast radius",
                    "Conduct post-mortems on each failure",
                    "Consider slowing deployments until quality improves",
                ],
                data={"value": cfr, "level": level, "target": 15},
            )

    def _analyze_mttr(
        self,
        metrics: DORAMetrics,
        trends: list[DORAMetrics] | None,
    ) -> MetricsInsight | None:
        """Analyze MTTR and generate insight."""
        mttr = metrics.mean_time_to_recovery
        level = metrics.mttr_level

        if level == "elite":
            return MetricsInsight(
                title="Rapid Recovery Capability",
                description=f"Average recovery time is {mttr:.1f} hours. "
                           "Your team can quickly restore service when issues occur.",
                severity="success",
                metric="mttr",
                recommendations=[
                    "Document your incident response playbooks",
                    "Continue practicing incident response",
                    "Consider automated rollback capabilities",
                ],
                data={"value": mttr, "level": level, "unit": "hours"},
            )
        elif level == "high":
            return MetricsInsight(
                title="Good Recovery Time",
                description=f"Recovery takes {mttr:.1f} hours on average. "
                           "To reach elite, aim for under 1 hour.",
                severity="info",
                metric="mttr",
                recommendations=[
                    "Improve observability and alerting",
                    "Create runbooks for common issues",
                    "Practice with game days or chaos engineering",
                ],
                data={"value": mttr, "level": level, "target": 1},
            )
        elif level == "medium":
            return MetricsInsight(
                title="Recovery Time Needs Improvement",
                description=f"Recovery takes {mttr/24:.1f} days on average. "
                           "Extended outages impact users and business.",
                severity="warning",
                metric="mttr",
                recommendations=[
                    "Implement comprehensive monitoring",
                    "Establish on-call rotations",
                    "Create automated health checks",
                    "Document common failure modes",
                ],
                data={"value": mttr, "level": level, "target": 24},
            )
        else:
            return MetricsInsight(
                title="Long Recovery Times",
                description=f"Recovery takes over {mttr/24:.0f} days on average. "
                           "This represents significant availability risk.",
                severity="critical",
                metric="mttr",
                recommendations=[
                    "Establish formal incident response process",
                    "Invest in monitoring and alerting tools",
                    "Create disaster recovery plans",
                    "Train team on incident management",
                    "Consider breaking down monolithic systems",
                ],
                data={"value": mttr, "level": level, "target": 168},
            )

    def _analyze_overall_performance(
        self,
        metrics: DORAMetrics,
    ) -> MetricsInsight:
        """Generate overall performance insight."""
        level = metrics.overall_level

        level_descriptions = {
            "elite": (
                "Your team is performing at elite level across DORA metrics. "
                "You're among the top performers in the industry.",
                "success"
            ),
            "high": (
                "Your team shows strong performance across DORA metrics. "
                "Focus on specific areas to reach elite level.",
                "info"
            ),
            "medium": (
                "Your team's DORA performance has room for improvement. "
                "Prioritize the weakest metrics for targeted improvement.",
                "warning"
            ),
            "low": (
                "Your team's DORA metrics indicate significant challenges. "
                "Focus on foundational improvements in CI/CD and testing.",
                "warning"
            ),
            "unknown": (
                "Unable to calculate overall DORA performance. "
                "Ensure data sources are properly connected.",
                "info"
            ),
        }

        desc, severity = level_descriptions.get(level, level_descriptions["unknown"])

        return MetricsInsight(
            title=f"Overall DORA Performance: {level.capitalize()}",
            description=desc,
            severity=severity,
            metric="overall",
            data={
                "level": level,
                "deployment_frequency_level": metrics.deployment_frequency_level,
                "lead_time_level": metrics.lead_time_level,
                "change_failure_rate_level": metrics.change_failure_rate_level,
                "mttr_level": metrics.mttr_level,
            },
        )

    def _analyze_trends(
        self,
        trends: list[DORAMetrics],
    ) -> list[MetricsInsight]:
        """Analyze metric trends over time."""
        insights = []

        if len(trends) < 3:
            return insights

        # Check deployment frequency trend
        df_values = [t.deployment_frequency for t in trends if t.deployment_frequency]
        if len(df_values) >= 3:
            trend_dir = self._calculate_trend_direction(df_values)
            if trend_dir == "improving":
                insights.append(MetricsInsight(
                    title="Deployment Frequency Improving",
                    description="Your deployment frequency has been trending upward. Keep it up!",
                    severity="success",
                    metric="deployment_frequency",
                    data={"trend": "improving", "values": df_values[-3:]},
                ))
            elif trend_dir == "declining":
                insights.append(MetricsInsight(
                    title="Deployment Frequency Declining",
                    description="Your deployment frequency has been decreasing. Consider investigating blockers.",
                    severity="warning",
                    metric="deployment_frequency",
                    data={"trend": "declining", "values": df_values[-3:]},
                ))

        # Check lead time trend
        lt_values = [t.lead_time_for_changes for t in trends if t.lead_time_for_changes]
        if len(lt_values) >= 3:
            # For lead time, decreasing is good
            trend_dir = self._calculate_trend_direction(lt_values)
            if trend_dir == "declining":
                insights.append(MetricsInsight(
                    title="Lead Time Improving",
                    description="Your lead time has been decreasing. Great progress!",
                    severity="success",
                    metric="lead_time",
                    data={"trend": "improving", "values": lt_values[-3:]},
                ))
            elif trend_dir == "improving":
                insights.append(MetricsInsight(
                    title="Lead Time Increasing",
                    description="Your lead time has been growing. Look for new bottlenecks.",
                    severity="warning",
                    metric="lead_time",
                    data={"trend": "declining", "values": lt_values[-3:]},
                ))

        return insights

    def _calculate_trend_direction(
        self,
        values: list[float],
    ) -> str:
        """Calculate trend direction from values."""
        if len(values) < 2:
            return "stable"

        # Simple linear trend
        first_half_avg = sum(values[:len(values)//2]) / (len(values)//2)
        second_half_avg = sum(values[len(values)//2:]) / (len(values) - len(values)//2)

        change_pct = (second_half_avg - first_half_avg) / first_half_avg if first_half_avg > 0 else 0

        if change_pct > 0.1:  # 10% improvement
            return "improving"
        elif change_pct < -0.1:  # 10% decline
            return "declining"
        else:
            return "stable"

    async def generate_ai_summary(
        self,
        metrics: DORAMetrics,
        insights: list[MetricsInsight],
    ) -> str:
        """
        Generate AI-powered natural language summary.

        Uses LLM if available, otherwise returns a template-based summary.
        """
        if self.llm_gateway:
            return await self._generate_llm_summary(metrics, insights)

        return self._generate_template_summary(metrics, insights)

    async def _generate_llm_summary(
        self,
        metrics: DORAMetrics,
        insights: list[MetricsInsight],
    ) -> str:
        """Generate summary using LLM."""
        prompt = f"""Summarize the following engineering team metrics in 2-3 sentences:

DORA Metrics:
- Deployment Frequency: {metrics.deployment_frequency:.2f}/day ({metrics.deployment_frequency_level})
- Lead Time: {metrics.lead_time_for_changes:.1f} hours ({metrics.lead_time_level})
- Change Failure Rate: {metrics.change_failure_rate:.1f}% ({metrics.change_failure_rate_level})
- MTTR: {metrics.mean_time_to_recovery:.1f} hours ({metrics.mttr_level})
- Overall: {metrics.overall_level}

Key insights:
{chr(10).join([f'- {i.title}: {i.description}' for i in insights[:3]])}

Provide a brief, actionable summary for an engineering leader."""

        try:
            response = await self.llm_gateway.complete(
                messages=[{"role": "user", "content": prompt}],
                model="gpt-4o-mini",
                temperature=0.7,
                max_tokens=200,
            )
            return response.content
        except Exception as e:
            logger.error("Failed to generate LLM summary", error=str(e))
            return self._generate_template_summary(metrics, insights)

    def _generate_template_summary(
        self,
        metrics: DORAMetrics,
        insights: list[MetricsInsight],
    ) -> str:
        """Generate template-based summary."""
        level = metrics.overall_level

        if level == "elite":
            return (
                f"Your team is performing at elite level with {metrics.deployment_frequency:.1f} "
                f"deployments per day and {metrics.lead_time_for_changes:.1f}h lead time. "
                f"Maintain these excellent practices."
            )
        elif level == "high":
            weakest = self._find_weakest_metric(metrics)
            return (
                f"Strong overall performance at high level. "
                f"Focus on improving {weakest} to reach elite status."
            )
        elif level == "medium":
            return (
                f"Your team has opportunities for improvement. "
                f"Consider prioritizing deployment automation and testing to improve cycle time."
            )
        else:
            return (
                f"Foundational improvements needed. "
                f"Start with establishing basic CI/CD practices and automated testing."
            )

    def _find_weakest_metric(self, metrics: DORAMetrics) -> str:
        """Find the weakest DORA metric."""
        level_scores = {"elite": 4, "high": 3, "medium": 2, "low": 1, "unknown": 0}

        metric_levels = {
            "deployment frequency": level_scores.get(metrics.deployment_frequency_level, 0),
            "lead time": level_scores.get(metrics.lead_time_level, 0),
            "change failure rate": level_scores.get(metrics.change_failure_rate_level, 0),
            "recovery time": level_scores.get(metrics.mttr_level, 0),
        }

        return min(metric_levels, key=metric_levels.get)


    async def answer_question(
        self,
        question: str,
        dora_metrics: DORAMetrics | None = None,
        flow_metrics: Any = None,
        productivity_metrics: Any = None,
    ) -> str:
        """
        Answer a natural language question about metrics.

        Args:
            question: The user's question
            dora_metrics: Current DORA metrics
            flow_metrics: Current flow metrics
            productivity_metrics: Current productivity metrics

        Returns:
            Natural language answer
        """
        # Build context from available metrics
        context_parts = []

        if dora_metrics:
            context_parts.append(f"""DORA Metrics:
- Deployment Frequency: {dora_metrics.deployment_frequency:.2f}/day ({dora_metrics.deployment_frequency_level or 'unknown'})
- Lead Time: {dora_metrics.lead_time_for_changes:.1f} hours ({dora_metrics.lead_time_level or 'unknown'})
- Change Failure Rate: {dora_metrics.change_failure_rate:.1f}% ({dora_metrics.change_failure_rate_level or 'unknown'})
- MTTR: {dora_metrics.mean_time_to_recovery:.1f} hours ({dora_metrics.mttr_level or 'unknown'})
- Overall Performance: {dora_metrics.overall_level or 'unknown'}""")

        if flow_metrics:
            context_parts.append(f"""Flow Metrics:
- Current WIP: {getattr(flow_metrics, 'current_wip', 'N/A')}
- Flow Efficiency: {getattr(flow_metrics, 'flow_efficiency', 'N/A')}%
- Cycle Time: {getattr(flow_metrics, 'total_cycle_time', 'N/A')} hours
- Issues Completed: {getattr(flow_metrics, 'issues_completed', 'N/A')}""")

        if productivity_metrics:
            context_parts.append(f"""Team Productivity:
- Velocity Trend: {getattr(productivity_metrics, 'velocity_trend', 'N/A')}
- Active Members: {getattr(productivity_metrics, 'active_members', 'N/A')}
- Code Review Coverage: {getattr(productivity_metrics, 'code_review_coverage', 'N/A')}%
- Collaboration Index: {getattr(productivity_metrics, 'collaboration_index', 'N/A')}""")

        context = "\n\n".join(context_parts) if context_parts else "No metrics data available."

        # If LLM is available, use it
        if self.llm_gateway:
            prompt = f"""You are an engineering metrics expert. Answer the following question based on the metrics data provided.

{context}

Question: {question}

Provide a helpful, specific answer based on the metrics. If the data doesn't directly answer the question, explain what the metrics suggest and what additional information might help."""

            try:
                response = await self.llm_gateway.complete(
                    messages=[{"role": "user", "content": prompt}],
                    model="gpt-4o-mini",
                    temperature=0.7,
                    max_tokens=500,
                )
                return response.content
            except Exception as e:
                logger.error("Failed to generate LLM answer", error=str(e))
                return self._generate_template_answer(question, dora_metrics)

        return self._generate_template_answer(question, dora_metrics)

    def _generate_template_answer(
        self,
        question: str,
        dora_metrics: DORAMetrics | None,
    ) -> str:
        """Generate template-based answer when LLM is not available."""
        question_lower = question.lower()

        if not dora_metrics:
            return "I don't have enough metrics data to answer that question. Please ensure DevLake integration is configured."

        # Deployment frequency questions
        if any(term in question_lower for term in ["deployment", "deploy", "release"]):
            level = dora_metrics.deployment_frequency_level or "unknown"
            freq = dora_metrics.deployment_frequency or 0
            if level in ["low", "medium"]:
                return (
                    f"Your current deployment frequency is {freq:.2f} per day ({level} level). "
                    f"To improve, consider: reducing batch sizes, automating more tests, "
                    f"and implementing feature flags for safer frequent deployments."
                )
            else:
                return (
                    f"Your deployment frequency is {freq:.2f} per day ({level} level). "
                    f"This is good performance. Focus on maintaining this while ensuring quality."
                )

        # Lead time questions
        if any(term in question_lower for term in ["lead time", "cycle time", "how long", "time to"]):
            lt = dora_metrics.lead_time_for_changes or 0
            level = dora_metrics.lead_time_level or "unknown"
            return (
                f"Your lead time is currently {lt:.1f} hours ({level} level). "
                f"This measures the time from code commit to production deployment. "
                f"To reduce it, focus on code review SLAs, automated testing, and reducing manual gates."
            )

        # Failure rate questions
        if any(term in question_lower for term in ["fail", "error", "bug", "quality"]):
            cfr = dora_metrics.change_failure_rate or 0
            level = dora_metrics.change_failure_rate_level or "unknown"
            return (
                f"Your change failure rate is {cfr:.1f}% ({level} level). "
                f"This indicates the percentage of deployments causing production issues. "
                f"To improve, invest in automated testing, code reviews, and staging environments."
            )

        # Recovery questions
        if any(term in question_lower for term in ["recover", "mttr", "incident", "outage"]):
            mttr = dora_metrics.mean_time_to_recovery or 0
            level = dora_metrics.mttr_level or "unknown"
            return (
                f"Your mean time to recovery is {mttr:.1f} hours ({level} level). "
                f"This measures how quickly you restore service after an incident. "
                f"To improve, focus on observability, runbooks, and incident response training."
            )

        # General performance questions
        if any(term in question_lower for term in ["overall", "performance", "doing", "status"]):
            level = dora_metrics.overall_level or "unknown"
            return (
                f"Your overall DORA performance level is '{level}'. "
                f"This is based on four key metrics: deployment frequency, lead time, "
                f"change failure rate, and mean time to recovery. "
                f"Elite performers deploy frequently with low failure rates and quick recovery."
            )

        # Default response
        return (
            f"Based on your metrics, your team is performing at '{dora_metrics.overall_level or 'unknown'}' level. "
            f"For specific insights, try asking about deployment frequency, lead time, "
            f"change failure rate, or recovery time."
        )


# Singleton instance
insights_generator = AIInsightsGenerator()


def get_insights_generator(llm_gateway=None) -> AIInsightsGenerator:
    """Get insights generator instance."""
    global insights_generator
    if llm_gateway:
        insights_generator = AIInsightsGenerator(llm_gateway=llm_gateway)
    return insights_generator
