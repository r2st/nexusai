"""AI ROI (Return on Investment) calculation service.

Calculates the business value and ROI of AI tool adoption including:
- Cost tracking (licenses, API usage, infrastructure)
- Value estimation (time saved, productivity gains)
- ROI metrics and trends
"""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_analytics import (
    AIROIMetric,
    AIToolType,
    AIUsageLog,
    AIAnalyticsMetric,
)


class AIROIService:
    """Service for calculating AI tool ROI and productivity metrics."""

    # Default pricing for AI tools (monthly per user)
    DEFAULT_PRICING = {
        AIToolType.CURSOR.value: 20.0,  # Cursor Pro
        AIToolType.CLAUDE_CODE.value: 20.0,  # Claude Pro
        AIToolType.GITHUB_COPILOT.value: 19.0,  # Copilot Business
        AIToolType.Q_DEV.value: 19.0,  # Q Developer Pro
        AIToolType.CHATGPT.value: 20.0,  # ChatGPT Plus
        AIToolType.CODY.value: 9.0,  # Sourcegraph Cody
        AIToolType.TABNINE.value: 12.0,  # TabNine Pro
    }

    # Estimated time saved per accepted line of code (in seconds)
    TIME_SAVED_PER_LINE = 30  # Conservative estimate

    # Default hourly developer cost
    DEFAULT_HOURLY_COST = 75.0

    async def calculate_roi(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_id: str | None,
        period_start: datetime,
        period_end: datetime,
        pricing_overrides: dict[str, float] | None = None,
        hourly_cost: float | None = None,
    ) -> AIROIMetric:
        """Calculate ROI metrics for a given period.

        Args:
            session: Database session
            tenant_id: Tenant ID
            project_id: Optional project ID
            period_start: Start of period
            period_end: End of period
            pricing_overrides: Custom pricing per tool
            hourly_cost: Custom hourly developer cost

        Returns:
            AIROIMetric with calculated values
        """
        pricing = {**self.DEFAULT_PRICING, **(pricing_overrides or {})}
        developer_cost = hourly_cost or self.DEFAULT_HOURLY_COST

        # Get usage data by tool
        usage_data = await self._get_usage_by_tool(
            session, tenant_id, project_id, period_start, period_end
        )

        # Calculate costs
        total_license_cost = 0.0
        total_api_cost = 0.0
        tool_breakdown = {}

        for tool_type, data in usage_data.items():
            # License cost (per user per month)
            months = max(1, (period_end - period_start).days / 30)
            license_cost = pricing.get(tool_type, 15.0) * data["unique_users"] * months

            # API cost (estimated based on tokens)
            # Using average of $0.01 per 1K tokens
            api_cost = (data["tokens"] / 1000) * 0.01

            tool_breakdown[tool_type] = {
                "users": data["unique_users"],
                "events": data["events"],
                "lines_generated": data["lines_generated"],
                "lines_accepted": data["lines_accepted"],
                "tokens": data["tokens"],
                "license_cost": license_cost,
                "api_cost": api_cost,
                "acceptance_rate": (
                    data["lines_accepted"] / data["lines_generated"]
                    if data["lines_generated"] > 0
                    else 0.0
                ),
            }

            total_license_cost += license_cost
            total_api_cost += api_cost

        # Calculate time saved
        total_lines_accepted = sum(d["lines_accepted"] for d in usage_data.values())
        time_saved_seconds = total_lines_accepted * self.TIME_SAVED_PER_LINE
        time_saved_hours = time_saved_seconds / 3600

        # Calculate value generated
        value_generated = time_saved_hours * developer_cost

        # Calculate ROI
        total_cost = total_license_cost + total_api_cost
        roi_percentage = (
            ((value_generated - total_cost) / total_cost * 100)
            if total_cost > 0
            else 0.0
        )

        # Calculate payback period
        daily_value = value_generated / max(1, (period_end - period_start).days)
        daily_cost = total_cost / max(1, (period_end - period_start).days)
        payback_days = total_cost / daily_value if daily_value > 0 else None

        # Get user stats
        total_users = await self._get_total_users(session, tenant_id, project_id)
        active_users = sum(d["unique_users"] for d in usage_data.values())
        adoption_rate = (active_users / total_users * 100) if total_users > 0 else 0.0

        # Calculate acceptance rate across all tools
        total_generated = sum(d["lines_generated"] for d in usage_data.values())
        overall_acceptance_rate = (
            total_lines_accepted / total_generated if total_generated > 0 else 0.0
        )

        # Create ROI metric
        roi_metric = AIROIMetric(
            tenant_id=tenant_id,
            project_id=project_id,
            period_start=period_start,
            period_end=period_end,
            total_license_cost=total_license_cost,
            total_api_cost=total_api_cost,
            total_infrastructure_cost=0.0,  # Would be calculated separately
            estimated_time_saved_hours=time_saved_hours,
            hourly_developer_cost=developer_cost,
            estimated_value_generated=value_generated,
            roi_percentage=roi_percentage,
            payback_period_days=payback_days,
            total_users=total_users,
            active_users=active_users,
            adoption_rate=adoption_rate,
            lines_of_code_generated=total_generated,
            acceptance_rate=overall_acceptance_rate,
            bugs_prevented=0,  # Would need additional data
            tool_breakdown=tool_breakdown,
        )

        session.add(roi_metric)
        await session.commit()

        return roi_metric

    async def get_roi_trend(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_id: str | None,
        periods: int = 6,
        granularity: str = "monthly",
    ) -> list[dict[str, Any]]:
        """Get ROI trend over multiple periods.

        Args:
            session: Database session
            tenant_id: Tenant ID
            project_id: Optional project ID
            periods: Number of periods to include
            granularity: 'weekly', 'monthly', or 'quarterly'

        Returns:
            List of ROI data points
        """
        trend = []
        now = datetime.now()

        # Determine period length
        if granularity == "weekly":
            delta = timedelta(weeks=1)
        elif granularity == "quarterly":
            delta = timedelta(days=90)
        else:
            delta = timedelta(days=30)

        for i in range(periods):
            period_end = now - (delta * i)
            period_start = period_end - delta

            # Get or calculate ROI for this period
            result = await session.execute(
                select(AIROIMetric)
                .where(
                    AIROIMetric.tenant_id == tenant_id,
                    AIROIMetric.period_start >= period_start,
                    AIROIMetric.period_end <= period_end,
                )
                .order_by(AIROIMetric.created_at.desc())
                .limit(1)
            )
            roi = result.scalar_one_or_none()

            if roi:
                trend.append({
                    "period_start": period_start.isoformat(),
                    "period_end": period_end.isoformat(),
                    "roi_percentage": roi.roi_percentage,
                    "value_generated": roi.estimated_value_generated,
                    "total_cost": roi.total_license_cost + roi.total_api_cost,
                    "time_saved_hours": roi.estimated_time_saved_hours,
                    "active_users": roi.active_users,
                    "adoption_rate": roi.adoption_rate,
                })
            else:
                # Calculate on the fly if no cached data
                roi = await self.calculate_roi(
                    session, tenant_id, project_id, period_start, period_end
                )
                trend.append({
                    "period_start": period_start.isoformat(),
                    "period_end": period_end.isoformat(),
                    "roi_percentage": roi.roi_percentage,
                    "value_generated": roi.estimated_value_generated,
                    "total_cost": roi.total_license_cost + roi.total_api_cost,
                    "time_saved_hours": roi.estimated_time_saved_hours,
                    "active_users": roi.active_users,
                    "adoption_rate": roi.adoption_rate,
                })

        return list(reversed(trend))  # Oldest first

    async def get_productivity_metrics(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_id: str | None,
        period_start: datetime,
        period_end: datetime,
    ) -> dict[str, Any]:
        """Get detailed productivity metrics.

        Returns comprehensive productivity analysis including:
        - Efficiency gains
        - Code quality indicators
        - Tool effectiveness
        """
        usage_data = await self._get_usage_by_tool(
            session, tenant_id, project_id, period_start, period_end
        )

        # Calculate productivity metrics
        total_events = sum(d["events"] for d in usage_data.values())
        total_generated = sum(d["lines_generated"] for d in usage_data.values())
        total_accepted = sum(d["lines_accepted"] for d in usage_data.values())
        total_tokens = sum(d["tokens"] for d in usage_data.values())

        # Time calculations
        time_saved_hours = (total_accepted * self.TIME_SAVED_PER_LINE) / 3600
        period_days = max(1, (period_end - period_start).days)

        # Per-tool effectiveness
        tool_effectiveness = {}
        for tool, data in usage_data.items():
            if data["events"] > 0:
                tool_effectiveness[tool] = {
                    "acceptance_rate": (
                        data["lines_accepted"] / data["lines_generated"]
                        if data["lines_generated"] > 0
                        else 0.0
                    ),
                    "lines_per_event": data["lines_generated"] / data["events"],
                    "tokens_per_event": data["tokens"] / data["events"],
                    "efficiency_score": self._calculate_efficiency_score(data),
                }

        return {
            "period": {
                "start": period_start.isoformat(),
                "end": period_end.isoformat(),
                "days": period_days,
            },
            "totals": {
                "events": total_events,
                "lines_generated": total_generated,
                "lines_accepted": total_accepted,
                "tokens_used": total_tokens,
                "time_saved_hours": time_saved_hours,
            },
            "averages": {
                "events_per_day": total_events / period_days,
                "lines_per_day": total_generated / period_days,
                "time_saved_per_day_hours": time_saved_hours / period_days,
            },
            "rates": {
                "overall_acceptance_rate": (
                    total_accepted / total_generated if total_generated > 0 else 0.0
                ),
                "tokens_per_line": (
                    total_tokens / total_generated if total_generated > 0 else 0.0
                ),
            },
            "by_tool": tool_effectiveness,
        }

    async def _get_usage_by_tool(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_id: str | None,
        period_start: datetime,
        period_end: datetime,
    ) -> dict[str, dict[str, Any]]:
        """Get usage data grouped by tool type."""
        query = select(
            AIUsageLog.tool_type,
            func.count(AIUsageLog.id).label("events"),
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
            row.tool_type: {
                "events": row.events or 0,
                "lines_generated": row.lines_generated or 0,
                "lines_accepted": row.lines_accepted or 0,
                "tokens": row.tokens or 0,
                "unique_users": row.unique_users or 0,
            }
            for row in result
        }

    async def _get_total_users(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_id: str | None,
    ) -> int:
        """Get total number of users in the organization/project."""
        from app.models.organization import OrganizationMember
        from app.models.project import ProjectMember

        if project_id:
            result = await session.execute(
                select(func.count(ProjectMember.id)).where(
                    ProjectMember.tenant_id == tenant_id,
                    ProjectMember.project_id == project_id,
                    ProjectMember.is_active == True,
                )
            )
        else:
            result = await session.execute(
                select(func.count(OrganizationMember.id)).where(
                    OrganizationMember.tenant_id == tenant_id,
                    OrganizationMember.is_active == True,
                )
            )

        return result.scalar() or 0

    def _calculate_efficiency_score(self, data: dict[str, Any]) -> float:
        """Calculate an efficiency score (0-100) for a tool.

        Factors:
        - Acceptance rate (40%)
        - Lines per event (30%)
        - Token efficiency (30%)
        """
        acceptance_rate = (
            data["lines_accepted"] / data["lines_generated"]
            if data["lines_generated"] > 0
            else 0.0
        )
        lines_per_event = data["lines_generated"] / max(1, data["events"])
        tokens_per_line = (
            data["tokens"] / max(1, data["lines_generated"])
        )

        # Normalize each factor to 0-1 range
        acceptance_score = min(1.0, acceptance_rate)
        lines_score = min(1.0, lines_per_event / 20)  # 20 lines per event is max
        token_efficiency = max(0.0, min(1.0, 1 - (tokens_per_line / 500)))

        # Weighted average
        score = (
            acceptance_score * 0.4 +
            lines_score * 0.3 +
            token_efficiency * 0.3
        ) * 100

        return round(score, 2)


# Singleton instance
ai_roi_service = AIROIService()
