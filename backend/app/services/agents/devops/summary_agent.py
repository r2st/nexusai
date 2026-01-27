"""Executive Summary Agent for generating business-focused reports."""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger()


class AudienceLevel(str, Enum):
    """Target audience for the summary."""

    EXECUTIVE = "executive"  # C-level, VPs
    MANAGER = "manager"      # Engineering managers, directors
    TEAM = "team"            # Individual contributors, tech leads


class SummaryFormat(str, Enum):
    """Output format for the summary."""

    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"
    SLACK = "slack"
    EMAIL = "email"


@dataclass
class SummarySection:
    """A section of the executive summary."""

    title: str
    content: str
    priority: int = 0  # Higher = more important
    icon: str | None = None
    metrics: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ExecutiveSummary:
    """Complete executive summary."""

    title: str
    subtitle: str
    generated_at: datetime
    period_description: str
    audience: AudienceLevel
    sections: list[SummarySection]
    key_metrics: list[dict[str, Any]]
    action_items: list[str]
    attachments: list[str] = field(default_factory=list)


class ExecutiveSummaryAgent:
    """Agent specialized in creating executive summaries.

    This agent:
    - Receives analysis and visualization data from upstream agents
    - Synthesizes information into business-focused narratives
    - Adapts language for different audience levels
    - Generates actionable recommendations
    - Formats output for various delivery channels
    """

    def __init__(self, llm_client=None):
        self.llm = llm_client
        self.agent_id = "executive-summary-agent"
        self.agent_name = "Executive Summary Writer"
        self.capabilities = [
            "narrative_synthesis",
            "audience_adaptation",
            "action_generation",
            "multi_format_output",
        ]

    async def generate_dora_summary(
        self,
        dora_data: dict[str, Any],
        dashboard_data: dict[str, Any] | None = None,
        audience: AudienceLevel = AudienceLevel.EXECUTIVE,
    ) -> ExecutiveSummary:
        """Generate executive summary from DORA analysis."""
        logger.info("Generating DORA executive summary", audience=audience.value)

        project_id = dora_data.get("project_id", "Unknown")
        period = dora_data.get("period", {})
        overall_performance = dora_data.get("overall_performance", "unknown")
        metrics = dora_data.get("metrics", [])
        recommendations = dora_data.get("recommendations", [])
        insights = dora_data.get("insights", [])

        # Build sections based on audience
        sections = []

        # 1. Performance Overview
        sections.append(self._create_performance_section(overall_performance, metrics, audience))

        # 2. Key Findings
        sections.append(self._create_findings_section(metrics, insights, audience))

        # 3. Recommendations
        sections.append(self._create_recommendations_section(recommendations, audience))

        # 4. Dashboard Link (if available)
        if dashboard_data:
            sections.append(SummarySection(
                title="Interactive Dashboard",
                content=f"View the full interactive dashboard at: {dashboard_data.get('grafana_url', 'N/A')}",
                priority=1,
                icon="📊",
            ))

        # Extract key metrics for highlight
        key_metrics = [
            {
                "name": m["name"].replace("_", " ").title(),
                "value": f"{m['value']} {m['unit']}",
                "status": self._get_status_emoji(m["performance"]),
            }
            for m in metrics
        ]

        # Generate action items
        action_items = self._generate_action_items(metrics, recommendations, audience)

        # Build period description
        period_desc = "Last 30 days"
        if period:
            start = period.get("start", "")[:10]
            end = period.get("end", "")[:10]
            period_desc = f"{start} to {end}"

        summary = ExecutiveSummary(
            title=f"Engineering Performance Report: {project_id}",
            subtitle=self._generate_subtitle(overall_performance, audience),
            generated_at=datetime.now(UTC),
            period_description=period_desc,
            audience=audience,
            sections=sorted(sections, key=lambda s: -s.priority),
            key_metrics=key_metrics,
            action_items=action_items,
        )

        logger.info("Executive summary generated", sections=len(sections))

        return summary

    async def generate_adoption_summary(
        self,
        adoption_data: dict[str, Any],
        audience: AudienceLevel = AudienceLevel.MANAGER,
    ) -> ExecutiveSummary:
        """Generate executive summary for AI adoption metrics."""
        logger.info("Generating AI adoption summary", audience=audience.value)

        sections = []

        # 1. Adoption Overview
        adoption_rate = adoption_data.get("adoption_rate", 0)
        active_users = adoption_data.get("active_users", 0)
        total_users = adoption_data.get("total_users", 0)

        if audience == AudienceLevel.EXECUTIVE:
            overview_content = f"""
**AI Tool Adoption: {adoption_rate:.1f}%**

Your engineering organization has achieved {adoption_rate:.1f}% adoption of AI-powered development tools.
{active_users} out of {total_users} developers are actively using AI assistants to accelerate their work.

{"✅ This exceeds industry benchmarks." if adoption_rate > 50 else "📈 There's significant room for growth."}
"""
        else:
            overview_content = f"""
**Current Adoption Rate: {adoption_rate:.1f}%**

- Active Users: {active_users}/{total_users}
- Acceptance Rate: {adoption_data.get('acceptance_rate', 0):.1f}%
- Most Used Tool: {adoption_data.get('top_tool', 'GitHub Copilot')}
"""

        sections.append(SummarySection(
            title="Adoption Overview",
            content=overview_content,
            priority=10,
            icon="🚀",
        ))

        # 2. ROI Analysis
        roi = adoption_data.get("roi", {})
        if roi:
            sections.append(SummarySection(
                title="Return on Investment",
                content=f"""
**Estimated Annual Savings: ${roi.get('annual_savings', 0):,.0f}**

- Time saved per developer: {roi.get('hours_saved_per_dev', 0):.1f} hours/week
- Productivity improvement: {roi.get('productivity_gain', 0):.0f}%
- Cost per user: ${roi.get('cost_per_user', 0):.2f}/month
""",
                priority=9,
                icon="💰",
                metrics=[
                    {"name": "Annual Savings", "value": f"${roi.get('annual_savings', 0):,.0f}"},
                    {"name": "ROI", "value": f"{roi.get('roi_percentage', 0):.0f}%"},
                ],
            ))

        # Key metrics
        key_metrics = [
            {"name": "Adoption Rate", "value": f"{adoption_rate:.1f}%", "status": "✅" if adoption_rate > 50 else "📈"},
            {"name": "Active Users", "value": str(active_users), "status": "👥"},
            {"name": "Acceptance Rate", "value": f"{adoption_data.get('acceptance_rate', 0):.1f}%", "status": "🎯"},
        ]

        action_items = [
            "Schedule training sessions for non-adopters",
            "Share success stories from power users",
            "Monitor acceptance rate improvements",
        ]

        return ExecutiveSummary(
            title="AI SDLC Adoption Report",
            subtitle=f"{adoption_rate:.0f}% of developers using AI tools",
            generated_at=datetime.now(UTC),
            period_description="Last 30 days",
            audience=audience,
            sections=sections,
            key_metrics=key_metrics,
            action_items=action_items,
        )

    def _create_performance_section(
        self,
        overall: str,
        metrics: list[dict[str, Any]],
        audience: AudienceLevel,
    ) -> SummarySection:
        """Create the performance overview section."""
        emoji = self._get_status_emoji(overall)

        if audience == AudienceLevel.EXECUTIVE:
            content = f"""
**Overall Performance: {overall.title()}** {emoji}

Your engineering team is performing at the **{overall}** level according to DORA metrics,
{'placing you among industry leaders.' if overall in ('elite', 'high') else 'with opportunities for improvement.'}

This assessment is based on four key metrics that correlate with software delivery performance
and organizational outcomes.
"""
        else:
            metric_lines = "\n".join([
                f"- {m['name'].replace('_', ' ').title()}: {m['value']} {m['unit']} ({m['performance']})"
                for m in metrics
            ])
            content = f"""
**Overall: {overall.title()}** {emoji}

{metric_lines}
"""

        return SummarySection(
            title="Performance Summary",
            content=content,
            priority=10,
            icon=emoji,
        )

    def _create_findings_section(
        self,
        metrics: list[dict[str, Any]],
        insights: list[str],
        audience: AudienceLevel,
    ) -> SummarySection:
        """Create the key findings section."""
        # Identify strengths and areas for improvement
        strengths = [m for m in metrics if m.get("performance") in ("elite", "high")]
        improvements = [m for m in metrics if m.get("performance") in ("medium", "low")]

        if audience == AudienceLevel.EXECUTIVE:
            content = "### Key Findings\n\n"

            if strengths:
                content += "**Strengths:**\n"
                for m in strengths:
                    content += f"- {m['name'].replace('_', ' ').title()} is at {m['performance']} performance\n"

            if improvements:
                content += "\n**Areas for Improvement:**\n"
                for m in improvements:
                    content += f"- {m['name'].replace('_', ' ').title()} needs attention\n"

            if insights:
                content += "\n**Insights:**\n"
                for insight in insights[:3]:
                    content += f"- {insight}\n"
        else:
            content = "### Detailed Findings\n\n"
            for m in metrics:
                trend_arrow = "↑" if m.get("trend") == "improving" else "↓" if m.get("trend") == "declining" else "→"
                content += f"**{m['name'].replace('_', ' ').title()}**\n"
                content += f"- Value: {m['value']} {m['unit']}\n"
                content += f"- Performance: {m['performance']}\n"
                content += f"- Trend: {trend_arrow} ({m.get('trend', 'stable')})\n\n"

        return SummarySection(
            title="Key Findings",
            content=content,
            priority=8,
            icon="🔍",
        )

    def _create_recommendations_section(
        self,
        recommendations: list[str],
        audience: AudienceLevel,
    ) -> SummarySection:
        """Create the recommendations section."""
        if audience == AudienceLevel.EXECUTIVE:
            # Summarize to top 3 strategic recommendations
            content = "### Strategic Recommendations\n\n"
            for i, rec in enumerate(recommendations[:3], 1):
                content += f"{i}. {rec}\n\n"
        else:
            content = "### Recommendations\n\n"
            for rec in recommendations:
                content += f"- {rec}\n"

        return SummarySection(
            title="Recommendations",
            content=content,
            priority=7,
            icon="💡",
        )

    def _generate_action_items(
        self,
        metrics: list[dict[str, Any]],
        recommendations: list[str],
        audience: AudienceLevel,
    ) -> list[str]:
        """Generate concrete action items."""
        actions = []

        # Add actions based on poor-performing metrics
        for m in metrics:
            if m.get("performance") == "low":
                name = m["name"].replace("_", " ")
                if audience == AudienceLevel.EXECUTIVE:
                    actions.append(f"Review {name} with engineering leadership")
                else:
                    actions.append(f"Create improvement plan for {name}")

            if m.get("trend") == "declining":
                name = m["name"].replace("_", " ")
                actions.append(f"Investigate declining {name}")

        # Add first recommendation as action
        if recommendations:
            actions.append(recommendations[0].split(".")[0] + ".")

        return actions[:5]  # Max 5 action items

    def _generate_subtitle(self, overall: str, audience: AudienceLevel) -> str:
        """Generate appropriate subtitle based on performance."""
        if overall == "elite":
            return "World-class engineering performance"
        elif overall == "high":
            return "Strong performance with room for excellence"
        elif overall == "medium":
            return "Solid foundation with improvement opportunities"
        else:
            return "Significant improvement opportunities identified"

    def _get_status_emoji(self, performance: str) -> str:
        """Get emoji based on performance level."""
        emojis = {
            "elite": "🌟",
            "high": "✅",
            "medium": "📈",
            "low": "⚠️",
        }
        return emojis.get(performance.lower(), "❓")

    def format_as_markdown(self, summary: ExecutiveSummary) -> str:
        """Format summary as Markdown."""
        lines = [
            f"# {summary.title}",
            f"*{summary.subtitle}*",
            "",
            f"**Period:** {summary.period_description}",
            f"**Generated:** {summary.generated_at.strftime('%Y-%m-%d %H:%M UTC')}",
            "",
            "---",
            "",
            "## Key Metrics",
            "",
        ]

        for metric in summary.key_metrics:
            lines.append(f"- **{metric['name']}**: {metric['value']} {metric['status']}")

        lines.append("")
        lines.append("---")
        lines.append("")

        for section in summary.sections:
            icon = f"{section.icon} " if section.icon else ""
            lines.append(f"## {icon}{section.title}")
            lines.append("")
            lines.append(section.content)
            lines.append("")

        if summary.action_items:
            lines.append("## Action Items")
            lines.append("")
            for i, action in enumerate(summary.action_items, 1):
                lines.append(f"- [ ] {action}")

        return "\n".join(lines)

    def format_as_slack(self, summary: ExecutiveSummary) -> dict[str, Any]:
        """Format summary as Slack message blocks."""
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": summary.title},
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"*{summary.subtitle}*"},
                    {"type": "mrkdwn", "text": f"| {summary.period_description}"},
                ],
            },
            {"type": "divider"},
        ]

        # Key metrics
        metric_text = " | ".join([
            f"*{m['name']}*: {m['value']} {m['status']}"
            for m in summary.key_metrics
        ])
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": metric_text},
        })

        # Sections
        for section in summary.sections[:3]:  # Limit for Slack
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*{section.icon} {section.title}*\n{section.content[:500]}"},
            })

        return {"blocks": blocks}

    def format_for_handoff(self, summary: ExecutiveSummary) -> dict[str, Any]:
        """Format summary for handoff (end of chain)."""
        return {
            "agent": self.agent_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "title": summary.title,
            "audience": summary.audience.value,
            "key_metrics": summary.key_metrics,
            "action_items": summary.action_items,
            "markdown": self.format_as_markdown(summary),
            "slack": self.format_as_slack(summary),
            "handoff_context": "Executive summary complete. End of agent workflow.",
        }
