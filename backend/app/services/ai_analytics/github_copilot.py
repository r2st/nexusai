"""GitHub Copilot metrics plugin.

Collects AI usage data from GitHub Copilot including:
- Code completions acceptance rates
- Chat interactions
- Per-user and per-repo metrics
- Enterprise usage analytics
"""

from datetime import datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_analytics import AIToolType, AIUsageLog
from app.services.ai_analytics.base import (
    AIAnalyticsPlugin,
    AIToolMetrics,
    AIUsageEvent,
)


class GitHubCopilotPlugin(AIAnalyticsPlugin):
    """Plugin for collecting GitHub Copilot usage metrics."""

    def __init__(self):
        super().__init__(AIToolType.GITHUB_COPILOT)
        self.github_api_base = "https://api.github.com"

    @property
    def name(self) -> str:
        return "GitHub Copilot"

    @property
    def description(self) -> str:
        return "Collect AI coding assistant metrics from GitHub Copilot"

    async def collect(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_id: str | None,
        connection_config: dict[str, Any],
        since: datetime | None = None,
    ) -> list[AIUsageEvent]:
        """Collect usage data from GitHub Copilot API.

        Uses the GitHub Copilot for Business API:
        https://docs.github.com/en/rest/copilot/copilot-metrics
        """
        events: list[AIUsageEvent] = []

        token = connection_config.get("github_token")
        org = connection_config.get("organization")
        enterprise = connection_config.get("enterprise")

        if not token:
            return events

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Get Copilot usage metrics
                if enterprise:
                    url = f"{self.github_api_base}/enterprises/{enterprise}/copilot/usage"
                elif org:
                    url = f"{self.github_api_base}/orgs/{org}/copilot/usage"
                else:
                    return events

                params: dict[str, Any] = {}
                if since:
                    params["since"] = since.strftime("%Y-%m-%d")

                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()

                # Parse daily usage data
                for day_data in data:
                    events.extend(self._parse_day_metrics(day_data))

                # Also get per-user metrics if available
                if org:
                    user_url = f"{self.github_api_base}/orgs/{org}/copilot/billing/seats"
                    user_response = await client.get(user_url, headers=headers)
                    if user_response.status_code == 200:
                        seats_data = user_response.json()
                        for seat in seats_data.get("seats", []):
                            events.extend(self._parse_seat_data(seat))

        except Exception as e:
            print(f"Error collecting GitHub Copilot metrics: {e}")

        return events

    def _parse_day_metrics(self, data: dict[str, Any]) -> list[AIUsageEvent]:
        """Parse daily aggregated metrics."""
        events = []

        day = data.get("day", datetime.now().strftime("%Y-%m-%d"))
        timestamp = datetime.strptime(day, "%Y-%m-%d")

        # Create events for each breakdown
        for breakdown in data.get("breakdown", []):
            language = breakdown.get("language")
            editor = breakdown.get("editor")

            events.append(AIUsageEvent(
                tool_type=self.tool_type.value,
                event_type="daily_aggregate",
                event_timestamp=timestamp,
                language=language,
                lines_generated=breakdown.get("suggestions_count", 0),
                lines_accepted=breakdown.get("acceptances_count", 0),
                metadata={
                    "editor": editor,
                    "active_users": breakdown.get("active_users", 0),
                    "lines_suggested": breakdown.get("lines_suggested", 0),
                    "lines_accepted": breakdown.get("lines_accepted", 0),
                },
            ))

        return events

    def _parse_seat_data(self, data: dict[str, Any]) -> list[AIUsageEvent]:
        """Parse per-seat/user metrics."""
        events = []

        assignee = data.get("assignee", {})
        user_login = assignee.get("login")

        if not user_login:
            return events

        # Hash the username for privacy
        import hashlib
        user_hash = hashlib.sha256(user_login.encode()).hexdigest()

        last_activity = data.get("last_activity_at")
        if last_activity:
            timestamp = datetime.fromisoformat(last_activity.replace("Z", "+00:00"))
        else:
            timestamp = datetime.now()

        events.append(AIUsageEvent(
            tool_type=self.tool_type.value,
            event_type="seat_activity",
            event_timestamp=timestamp,
            user_hash=user_hash,
            metadata={
                "last_activity_editor": data.get("last_activity_editor"),
                "created_at": data.get("created_at"),
                "pending_cancellation_date": data.get("pending_cancellation_date"),
            },
        ))

        return events

    async def test_connection(
        self,
        connection_config: dict[str, Any],
    ) -> tuple[bool, str]:
        """Test connection to GitHub Copilot API."""
        token = connection_config.get("github_token")
        org = connection_config.get("organization")
        enterprise = connection_config.get("enterprise")

        if not token:
            return False, "GitHub token is required"

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Test API access
                response = await client.get(
                    f"{self.github_api_base}/user",
                    headers=headers,
                )
                if response.status_code != 200:
                    return False, f"GitHub authentication failed: {response.status_code}"

                # Test Copilot access
                if enterprise:
                    url = f"{self.github_api_base}/enterprises/{enterprise}/copilot/billing"
                elif org:
                    url = f"{self.github_api_base}/orgs/{org}/copilot/billing"
                else:
                    return False, "Organization or enterprise name required"

                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    return True, "Connection successful"
                elif response.status_code == 404:
                    return False, "Copilot not enabled for this organization"
                else:
                    return False, f"Copilot API error: {response.status_code}"

        except Exception as e:
            return False, f"Connection error: {str(e)}"

    async def aggregate_metrics(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_id: str | None,
        period_start: datetime,
        period_end: datetime,
    ) -> AIToolMetrics:
        """Aggregate GitHub Copilot metrics for a time period."""
        query = select(
            func.count(AIUsageLog.id).label("total_events"),
            func.sum(AIUsageLog.lines_generated).label("total_lines_generated"),
            func.sum(AIUsageLog.lines_accepted).label("total_lines_accepted"),
            func.count(func.distinct(AIUsageLog.user_hash)).label("unique_users"),
        ).where(
            AIUsageLog.tenant_id == tenant_id,
            AIUsageLog.tool_type == self.tool_type.value,
            AIUsageLog.event_timestamp >= period_start,
            AIUsageLog.event_timestamp < period_end,
        )

        if project_id:
            query = query.where(AIUsageLog.project_id == project_id)

        result = await session.execute(query)
        row = result.first()

        if not row:
            return AIToolMetrics(
                tool_type=self.tool_type.value,
                period_start=period_start,
                period_end=period_end,
            )

        total_lines_generated = row.total_lines_generated or 0
        total_lines_accepted = row.total_lines_accepted or 0

        # Estimate cost based on Copilot pricing ($19/user/month for Business)
        # This is a rough estimate based on active users
        unique_users = row.unique_users or 0
        months = max(1, (period_end - period_start).days / 30)
        estimated_cost = unique_users * 19.0 * months

        return AIToolMetrics(
            tool_type=self.tool_type.value,
            period_start=period_start,
            period_end=period_end,
            total_events=row.total_events or 0,
            total_completions=total_lines_generated,
            accepted_completions=total_lines_accepted,
            total_lines_generated=total_lines_generated,
            total_lines_accepted=total_lines_accepted,
            acceptance_rate=(
                total_lines_accepted / total_lines_generated
                if total_lines_generated > 0
                else 0.0
            ),
            unique_users=unique_users,
            estimated_cost=estimated_cost,
        )

    def get_schema(self) -> dict[str, Any]:
        """Get configuration schema for GitHub Copilot plugin."""
        return {
            "type": "object",
            "properties": {
                "github_token": {
                    "type": "string",
                    "description": "GitHub personal access token with copilot scope",
                },
                "organization": {
                    "type": "string",
                    "description": "GitHub organization name",
                },
                "enterprise": {
                    "type": "string",
                    "description": "GitHub Enterprise name (for enterprise accounts)",
                },
            },
            "required": ["github_token"],
            "oneOf": [
                {"required": ["organization"]},
                {"required": ["enterprise"]},
            ],
        }
