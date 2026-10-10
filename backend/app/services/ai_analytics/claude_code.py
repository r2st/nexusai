"""Claude Code usage tracking plugin.

Collects AI usage data from Claude Code CLI including:
- Code generation sessions
- File edits and creations
- Token usage and costs
- Command history
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


class ClaudeCodePlugin(AIAnalyticsPlugin):
    """Plugin for collecting Claude Code usage metrics."""

    def __init__(self):
        super().__init__(AIToolType.CLAUDE_CODE)

    @property
    def name(self) -> str:
        return "Claude Code"

    @property
    def description(self) -> str:
        return "Collect AI coding assistant metrics from Claude Code CLI"

    async def collect(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_id: str | None,
        connection_config: dict[str, Any],
        since: datetime | None = None,
    ) -> list[AIUsageEvent]:
        """Collect usage data from Claude Code telemetry.

        Claude Code can export telemetry via:
        1. Local JSONL log files
        2. Anthropic Console API (enterprise)
        3. Custom webhook endpoint
        """
        events: list[AIUsageEvent] = []

        # Get configuration
        endpoint = connection_config.get("endpoint")
        api_key = connection_config.get("api_key")
        organization_id = connection_config.get("organization_id")

        if not endpoint:
            # Use local collection method
            return await self._collect_local(connection_config, since)

        # Collect from API endpoint
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {
                    "x-api-key": api_key,
                    "anthropic-version": "2024-01-01",
                }

                params: dict[str, Any] = {}
                if organization_id:
                    params["organization_id"] = organization_id
                if since:
                    params["since"] = since.isoformat()

                response = await client.get(
                    f"{endpoint}/v1/usage/claude-code",
                    headers=headers,
                    params=params,
                )
                response.raise_for_status()
                data = response.json()

                for usage in data.get("usage", []):
                    events.append(self._parse_event(usage))

        except Exception as e:
            print(f"Error collecting Claude Code telemetry: {e}")

        return events

    async def _collect_local(
        self,
        connection_config: dict[str, Any],
        since: datetime | None = None,
    ) -> list[AIUsageEvent]:
        """Collect from local Claude Code logs.

        Claude Code stores session data at:
        - macOS: ~/.claude/sessions/
        - Linux: ~/.claude/sessions/
        - Windows: %USERPROFILE%/.claude/sessions/
        """
        import json
        import os
        from pathlib import Path

        events: list[AIUsageEvent] = []

        # Get log path
        log_path = connection_config.get("log_path")
        if not log_path:
            home = Path.home()
            log_path = home / ".claude" / "sessions"

        log_path = Path(log_path)
        if not log_path.exists():
            return events

        # Parse JSONL session files
        for session_file in log_path.glob("*.jsonl"):
            try:
                with open(session_file) as f:
                    for line in f:
                        try:
                            data = json.loads(line.strip())
                            if data.get("type") == "usage":
                                timestamp = datetime.fromisoformat(
                                    data.get("timestamp", datetime.now().isoformat())
                                )
                                if since and timestamp < since:
                                    continue
                                events.append(self._parse_local_event(data))
                        except json.JSONDecodeError:
                            continue
            except Exception:
                continue

        return events

    def _parse_event(self, data: dict[str, Any]) -> AIUsageEvent:
        """Parse a Claude Code API usage event."""
        return AIUsageEvent(
            tool_type=self.tool_type.value,
            tool_version=data.get("version"),
            event_type=data.get("event_type", "session"),
            event_timestamp=datetime.fromisoformat(
                data.get("timestamp", datetime.now().isoformat())
            ),
            user_hash=data.get("user_hash"),
            language=data.get("primary_language"),
            file_extension=data.get("file_extension"),
            lines_generated=data.get("lines_written", 0),
            lines_accepted=data.get("lines_accepted", 0),
            tokens_used=data.get("total_tokens", 0),
            latency_ms=data.get("response_time_ms"),
            metadata={
                "model": data.get("model", "claude-sonnet-4-20250514"),
                "session_id": data.get("session_id"),
                "input_tokens": data.get("input_tokens", 0),
                "output_tokens": data.get("output_tokens", 0),
                "cost_usd": data.get("cost_usd", 0.0),
                "files_modified": data.get("files_modified", 0),
                "files_created": data.get("files_created", 0),
                "commands_run": data.get("commands_run", 0),
            },
        )

    def _parse_local_event(self, data: dict[str, Any]) -> AIUsageEvent:
        """Parse a local Claude Code log event."""
        return AIUsageEvent(
            tool_type=self.tool_type.value,
            tool_version=data.get("claude_code_version"),
            event_type="session",
            event_timestamp=datetime.fromisoformat(
                data.get("timestamp", datetime.now().isoformat())
            ),
            lines_generated=data.get("lines_written", 0),
            lines_accepted=data.get("lines_accepted", 0),
            tokens_used=(
                data.get("input_tokens", 0) + data.get("output_tokens", 0)
            ),
            latency_ms=data.get("duration_ms"),
            metadata={
                "model": data.get("model"),
                "session_id": data.get("session_id"),
                "input_tokens": data.get("input_tokens", 0),
                "output_tokens": data.get("output_tokens", 0),
                "conversation_turns": data.get("turns", 0),
                "tool_uses": data.get("tool_uses", 0),
            },
        )

    async def test_connection(
        self,
        connection_config: dict[str, Any],
    ) -> tuple[bool, str]:
        """Test connection to Claude Code telemetry."""
        endpoint = connection_config.get("endpoint")

        if not endpoint:
            # Check local logs
            from pathlib import Path

            log_path = connection_config.get("log_path")
            if not log_path:
                log_path = Path.home() / ".claude" / "sessions"
            else:
                log_path = Path(log_path)

            if log_path.exists():
                return True, f"Local logs found at {log_path}"
            else:
                return False, f"No logs found at {log_path}"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                api_key = connection_config.get("api_key")
                headers = {
                    "x-api-key": api_key,
                    "anthropic-version": "2024-01-01",
                }

                response = await client.get(
                    f"{endpoint}/v1/usage/health",
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
        """Aggregate Claude Code metrics for a time period."""
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
        total_tokens = row.total_tokens or 0

        # Estimate cost based on Claude's pricing
        # Input: $3/1M tokens, Output: $15/1M tokens (rough estimate)
        estimated_cost = (total_tokens / 1_000_000) * 9.0  # Average of input/output

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
            total_tokens=total_tokens,
            estimated_cost=estimated_cost,
        )

    def get_schema(self) -> dict[str, Any]:
        """Get configuration schema for Claude Code plugin."""
        return {
            "type": "object",
            "properties": {
                "endpoint": {
                    "type": "string",
                    "description": "Anthropic API endpoint for usage data",
                },
                "api_key": {
                    "type": "string",
                    "description": "Anthropic API key",
                },
                "organization_id": {
                    "type": "string",
                    "description": "Anthropic organization ID",
                },
                "log_path": {
                    "type": "string",
                    "description": "Path to local Claude Code session logs",
                },
            },
            "required": [],
        }
