"""Cursor IDE telemetry plugin.

Collects AI usage data from Cursor IDE including:
- Code completions (Tab/Ghost text)
- Chat interactions
- Code edits and generations
- Composer usage
"""

from datetime import datetime
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


class CursorPlugin(AIAnalyticsPlugin):
    """Plugin for collecting Cursor IDE telemetry."""

    def __init__(self):
        super().__init__(AIToolType.CURSOR)

    @property
    def name(self) -> str:
        return "Cursor IDE"

    @property
    def description(self) -> str:
        return "Collect AI code completion and chat metrics from Cursor IDE"

    async def collect(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_id: str | None,
        connection_config: dict[str, Any],
        since: datetime | None = None,
    ) -> list[AIUsageEvent]:
        """Collect usage data from Cursor telemetry endpoint.

        Cursor can export telemetry data via:
        1. Local SQLite database
        2. Telemetry API (enterprise)
        3. Webhook exports
        """
        events: list[AIUsageEvent] = []

        # Get configuration
        endpoint = connection_config.get("endpoint")
        api_key = connection_config.get("api_key")
        workspace_id = connection_config.get("workspace_id")

        if not endpoint:
            # Use local collection method (parse local telemetry)
            return await self._collect_local(connection_config, since)

        # Collect from API endpoint
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

                params: dict[str, Any] = {"workspace_id": workspace_id}
                if since:
                    params["since"] = since.isoformat()

                response = await client.get(
                    f"{endpoint}/api/v1/telemetry/events",
                    headers=headers,
                    params=params,
                )
                response.raise_for_status()
                data = response.json()

                for event_data in data.get("events", []):
                    events.append(self._parse_event(event_data))

        except Exception as e:
            # Log error but don't fail
            print(f"Error collecting Cursor telemetry: {e}")

        return events

    async def _collect_local(
        self,
        connection_config: dict[str, Any],
        since: datetime | None = None,
    ) -> list[AIUsageEvent]:
        """Collect from local Cursor telemetry.

        Cursor stores telemetry in SQLite at:
        - macOS: ~/Library/Application Support/Cursor/telemetry/
        - Linux: ~/.config/Cursor/telemetry/
        - Windows: %APPDATA%/Cursor/telemetry/
        """
        # This would parse local SQLite files in production
        # For now, return empty list
        return []

    def _parse_event(self, data: dict[str, Any]) -> AIUsageEvent:
        """Parse a Cursor telemetry event."""
        return AIUsageEvent(
            tool_type=self.tool_type.value,
            tool_version=data.get("cursor_version"),
            event_type=data.get("event_type", "completion"),
            event_timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
            user_hash=data.get("user_hash"),
            language=data.get("language"),
            file_extension=data.get("file_extension"),
            lines_generated=data.get("lines_generated", 0),
            lines_accepted=data.get("lines_accepted", 0),
            tokens_used=data.get("tokens_used", 0),
            latency_ms=data.get("latency_ms"),
            metadata={
                "model": data.get("model"),
                "completion_type": data.get("completion_type"),  # tab, ghost, composer
                "accepted": data.get("accepted", False),
            },
        )

    async def test_connection(
        self,
        connection_config: dict[str, Any],
    ) -> tuple[bool, str]:
        """Test connection to Cursor telemetry endpoint."""
        endpoint = connection_config.get("endpoint")

        if not endpoint:
            # Local collection mode
            return True, "Local collection mode enabled"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                api_key = connection_config.get("api_key")
                headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

                response = await client.get(
                    f"{endpoint}/api/v1/health",
                    headers=headers,
                )
                if response.status_code == 200:
                    return True, "Connection successful"
                else:
                    return False, f"Connection failed: {response.status_code}"
        except Exception as e:
            return False, "Connection failed. Please check your credentials and try again."

    async def aggregate_metrics(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_id: str | None,
        period_start: datetime,
        period_end: datetime,
    ) -> AIToolMetrics:
        """Aggregate Cursor metrics for a time period."""
        # Base query
        query = select(
            func.count(AIUsageLog.id).label("total_events"),
            func.sum(AIUsageLog.lines_generated).label("total_lines_generated"),
            func.sum(AIUsageLog.lines_accepted).label("total_lines_accepted"),
            func.sum(AIUsageLog.tokens_used).label("total_tokens"),
            func.avg(AIUsageLog.latency_ms).label("avg_latency"),
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

        return AIToolMetrics(
            tool_type=self.tool_type.value,
            period_start=period_start,
            period_end=period_end,
            total_events=row.total_events or 0,
            total_lines_generated=total_lines_generated,
            total_lines_accepted=total_lines_accepted,
            acceptance_rate=(
                total_lines_accepted / total_lines_generated
                if total_lines_generated > 0
                else 0.0
            ),
            unique_users=row.unique_users or 0,
            avg_latency_ms=float(row.avg_latency) if row.avg_latency else None,
            total_tokens=row.total_tokens or 0,
        )

    def get_schema(self) -> dict[str, Any]:
        """Get configuration schema for Cursor plugin."""
        return {
            "type": "object",
            "properties": {
                "endpoint": {
                    "type": "string",
                    "description": "Cursor telemetry API endpoint (optional for local collection)",
                },
                "api_key": {
                    "type": "string",
                    "description": "API key for Cursor telemetry (enterprise)",
                },
                "workspace_id": {
                    "type": "string",
                    "description": "Cursor workspace ID",
                },
                "local_path": {
                    "type": "string",
                    "description": "Path to local Cursor telemetry database",
                },
            },
            "required": [],
        }
