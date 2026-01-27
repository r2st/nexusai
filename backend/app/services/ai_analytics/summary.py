"""AI Summary service for generating insights and reports.

Provides automated AI-generated summaries for:
- Sprint retrospectives
- Pull request summaries
- Metrics analysis
- Incident postmortems
"""

from datetime import datetime, timedelta
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.ai_analytics import AISummary, AIUsageLog


class AISummaryService:
    """Service for generating AI-powered summaries and insights."""

    def __init__(self):
        from langchain_openai import ChatOpenAI

        self.model = ChatOpenAI(
            model=settings.OPENAI_DEFAULT_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0.3,
        )

    async def generate_sprint_summary(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_id: str,
        sprint_start: datetime,
        sprint_end: datetime,
        sprint_name: str | None = None,
    ) -> AISummary:
        """Generate a summary of sprint performance including AI tool usage."""
        from langchain_core.messages import HumanMessage, SystemMessage

        # Gather sprint data
        data = await self._gather_sprint_data(
            session, tenant_id, project_id, sprint_start, sprint_end
        )

        # Generate summary using LLM
        prompt = self._build_sprint_summary_prompt(data, sprint_name)

        messages = [
            SystemMessage(content="""You are a technical project manager providing sprint retrospective summaries.
Analyze the data provided and create a concise, actionable summary.
Focus on:
1. Key accomplishments
2. AI tool adoption and productivity gains
3. Areas for improvement
4. Recommendations for next sprint

Format the output with clear sections and bullet points."""),
            HumanMessage(content=prompt),
        ]

        response = await self.model.ainvoke(messages)

        # Parse response into structured format
        summary_text = response.content
        key_points = self._extract_key_points(summary_text)
        recommendations = self._extract_recommendations(summary_text)

        # Create and save summary
        summary = AISummary(
            tenant_id=tenant_id,
            project_id=project_id,
            summary_type="sprint",
            target_id=sprint_name,
            target_type="sprint",
            title=f"Sprint Summary: {sprint_name or 'Sprint'}",
            summary=summary_text,
            key_points=key_points,
            recommendations=recommendations,
            model_used=settings.OPENAI_DEFAULT_MODEL,
            tokens_used=response.response_metadata.get("token_usage", {}).get("total_tokens", 0),
            period_start=sprint_start,
            period_end=sprint_end,
        )

        session.add(summary)
        await session.commit()

        return summary

    async def generate_metrics_summary(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_id: str | None,
        period_start: datetime,
        period_end: datetime,
    ) -> AISummary:
        """Generate a summary of AI analytics metrics."""
        from langchain_core.messages import HumanMessage, SystemMessage

        # Gather metrics data
        data = await self._gather_metrics_data(
            session, tenant_id, project_id, period_start, period_end
        )

        prompt = f"""Analyze the following AI tool usage metrics and provide insights:

Period: {period_start.strftime('%Y-%m-%d')} to {period_end.strftime('%Y-%m-%d')}

Metrics:
{self._format_metrics_data(data)}

Provide:
1. Executive summary (2-3 sentences)
2. Key trends and patterns
3. ROI assessment
4. Recommendations for improving AI tool adoption"""

        messages = [
            SystemMessage(content="""You are an AI analytics expert providing insights on developer tool usage.
Focus on actionable insights and quantifiable impacts.
Be specific about trends and their implications."""),
            HumanMessage(content=prompt),
        ]

        response = await self.model.ainvoke(messages)

        summary = AISummary(
            tenant_id=tenant_id,
            project_id=project_id,
            summary_type="metrics",
            title="AI Analytics Summary",
            summary=response.content,
            key_points=self._extract_key_points(response.content),
            recommendations=self._extract_recommendations(response.content),
            model_used=settings.OPENAI_DEFAULT_MODEL,
            tokens_used=response.response_metadata.get("token_usage", {}).get("total_tokens", 0),
            period_start=period_start,
            period_end=period_end,
        )

        session.add(summary)
        await session.commit()

        return summary

    async def generate_pr_summary(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_id: str,
        pr_data: dict[str, Any],
    ) -> AISummary:
        """Generate a summary of a pull request with AI insights."""
        from langchain_core.messages import HumanMessage, SystemMessage

        prompt = f"""Analyze this pull request and provide a comprehensive summary:

PR Title: {pr_data.get('title')}
Description: {pr_data.get('description', 'No description')}
Author: {pr_data.get('author')}
Files Changed: {pr_data.get('files_changed', 0)}
Additions: {pr_data.get('additions', 0)}
Deletions: {pr_data.get('deletions', 0)}

Changes:
{pr_data.get('diff_summary', 'No diff available')}

Provide:
1. What this PR does (2-3 sentences)
2. Key changes by category (features, fixes, refactors)
3. Potential risks or concerns
4. Review recommendations"""

        messages = [
            SystemMessage(content="""You are a senior software engineer reviewing pull requests.
Provide clear, constructive feedback focused on:
- Code quality and best practices
- Potential bugs or edge cases
- Performance implications
- Testing coverage"""),
            HumanMessage(content=prompt),
        ]

        response = await self.model.ainvoke(messages)

        summary = AISummary(
            tenant_id=tenant_id,
            project_id=project_id,
            summary_type="pr",
            target_id=str(pr_data.get("pr_number")),
            target_type="pull_request",
            title=f"PR Summary: {pr_data.get('title', 'Untitled')}",
            summary=response.content,
            key_points=self._extract_key_points(response.content),
            recommendations=self._extract_recommendations(response.content),
            model_used=settings.OPENAI_DEFAULT_MODEL,
            tokens_used=response.response_metadata.get("token_usage", {}).get("total_tokens", 0),
        )

        session.add(summary)
        await session.commit()

        return summary

    async def generate_incident_postmortem(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_id: str,
        incident_data: dict[str, Any],
    ) -> AISummary:
        """Generate an incident postmortem summary."""
        from langchain_core.messages import HumanMessage, SystemMessage

        prompt = f"""Generate a blameless incident postmortem based on the following:

Incident: {incident_data.get('title')}
Severity: {incident_data.get('severity', 'Unknown')}
Duration: {incident_data.get('duration_minutes', 'Unknown')} minutes
Impact: {incident_data.get('impact', 'Unknown')}

Timeline:
{incident_data.get('timeline', 'No timeline available')}

Root Cause: {incident_data.get('root_cause', 'Under investigation')}

Provide:
1. Executive Summary
2. Impact Assessment
3. Root Cause Analysis
4. What went well
5. What could be improved
6. Action Items with owners"""

        messages = [
            SystemMessage(content="""You are a Site Reliability Engineer writing an incident postmortem.
Follow blameless postmortem principles:
- Focus on systems, not individuals
- Identify process improvements
- Provide actionable recommendations
- Be specific about timelines and impacts"""),
            HumanMessage(content=prompt),
        ]

        response = await self.model.ainvoke(messages)

        summary = AISummary(
            tenant_id=tenant_id,
            project_id=project_id,
            summary_type="incident",
            target_id=incident_data.get("incident_id"),
            target_type="incident",
            title=f"Postmortem: {incident_data.get('title', 'Incident')}",
            summary=response.content,
            key_points=self._extract_key_points(response.content),
            recommendations=self._extract_recommendations(response.content),
            model_used=settings.OPENAI_DEFAULT_MODEL,
            tokens_used=response.response_metadata.get("token_usage", {}).get("total_tokens", 0),
        )

        session.add(summary)
        await session.commit()

        return summary

    async def _gather_sprint_data(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_id: str,
        sprint_start: datetime,
        sprint_end: datetime,
    ) -> dict[str, Any]:
        """Gather data for sprint summary."""
        from sqlalchemy import func

        # Get AI usage during sprint
        result = await session.execute(
            select(
                AIUsageLog.tool_type,
                func.count(AIUsageLog.id).label("events"),
                func.sum(AIUsageLog.lines_generated).label("lines_generated"),
                func.sum(AIUsageLog.lines_accepted).label("lines_accepted"),
                func.count(func.distinct(AIUsageLog.user_hash)).label("users"),
            )
            .where(
                AIUsageLog.tenant_id == tenant_id,
                AIUsageLog.project_id == project_id,
                AIUsageLog.event_timestamp >= sprint_start,
                AIUsageLog.event_timestamp < sprint_end,
            )
            .group_by(AIUsageLog.tool_type)
        )

        tool_usage = {}
        for row in result:
            tool_usage[row.tool_type] = {
                "events": row.events,
                "lines_generated": row.lines_generated or 0,
                "lines_accepted": row.lines_accepted or 0,
                "users": row.users,
            }

        return {
            "sprint_start": sprint_start,
            "sprint_end": sprint_end,
            "tool_usage": tool_usage,
        }

    async def _gather_metrics_data(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_id: str | None,
        period_start: datetime,
        period_end: datetime,
    ) -> dict[str, Any]:
        """Gather metrics data for analysis."""
        from sqlalchemy import func

        query = select(
            AIUsageLog.tool_type,
            func.count(AIUsageLog.id).label("total_events"),
            func.sum(AIUsageLog.lines_generated).label("lines_generated"),
            func.sum(AIUsageLog.lines_accepted).label("lines_accepted"),
            func.sum(AIUsageLog.tokens_used).label("tokens"),
            func.count(func.distinct(AIUsageLog.user_hash)).label("unique_users"),
        ).where(
            AIUsageLog.tenant_id == tenant_id,
            AIUsageLog.event_timestamp >= period_start,
            AIUsageLog.event_timestamp < period_end,
        )

        if project_id:
            query = query.where(AIUsageLog.project_id == project_id)

        query = query.group_by(AIUsageLog.tool_type)
        result = await session.execute(query)

        return {
            "period": {"start": period_start, "end": period_end},
            "by_tool": {
                row.tool_type: {
                    "events": row.total_events,
                    "lines_generated": row.lines_generated or 0,
                    "lines_accepted": row.lines_accepted or 0,
                    "tokens": row.tokens or 0,
                    "users": row.unique_users,
                }
                for row in result
            },
        }

    def _build_sprint_summary_prompt(
        self,
        data: dict[str, Any],
        sprint_name: str | None,
    ) -> str:
        """Build prompt for sprint summary."""
        prompt = f"Sprint: {sprint_name or 'Current Sprint'}\n"
        prompt += f"Period: {data['sprint_start'].strftime('%Y-%m-%d')} to {data['sprint_end'].strftime('%Y-%m-%d')}\n\n"
        prompt += "AI Tool Usage:\n"

        for tool, usage in data.get("tool_usage", {}).items():
            prompt += f"- {tool}:\n"
            prompt += f"  - Events: {usage['events']}\n"
            prompt += f"  - Lines Generated: {usage['lines_generated']}\n"
            prompt += f"  - Lines Accepted: {usage['lines_accepted']}\n"
            prompt += f"  - Active Users: {usage['users']}\n"

        return prompt

    def _format_metrics_data(self, data: dict[str, Any]) -> str:
        """Format metrics data for prompt."""
        lines = []
        for tool, metrics in data.get("by_tool", {}).items():
            lines.append(f"\n{tool}:")
            lines.append(f"  Events: {metrics['events']}")
            lines.append(f"  Lines Generated: {metrics['lines_generated']}")
            lines.append(f"  Lines Accepted: {metrics['lines_accepted']}")
            lines.append(f"  Tokens Used: {metrics['tokens']}")
            lines.append(f"  Unique Users: {metrics['users']}")

        return "\n".join(lines)

    def _extract_key_points(self, text: str) -> list[str]:
        """Extract key points from summary text."""
        lines = text.split("\n")
        points = []
        for line in lines:
            line = line.strip()
            if line.startswith("- ") or line.startswith("• "):
                points.append(line[2:])
            elif line.startswith("* "):
                points.append(line[2:])
        return points[:10]  # Limit to 10 points

    def _extract_recommendations(self, text: str) -> list[str]:
        """Extract recommendations from summary text."""
        # Look for recommendations section
        recommendations = []
        in_recommendations = False

        for line in text.split("\n"):
            line = line.strip()
            if "recommendation" in line.lower() or "action item" in line.lower():
                in_recommendations = True
                continue
            if in_recommendations:
                if line.startswith(("- ", "• ", "* ", "1.", "2.", "3.")):
                    # Clean up the line
                    cleaned = line.lstrip("-•* 0123456789.")
                    if cleaned:
                        recommendations.append(cleaned.strip())

        return recommendations[:5]  # Limit to 5 recommendations


_ai_summary_service: AISummaryService | None = None


def get_ai_summary_service() -> AISummaryService:
    """Get or create the AI summary service singleton."""
    global _ai_summary_service
    if _ai_summary_service is None:
        _ai_summary_service = AISummaryService()
    return _ai_summary_service
