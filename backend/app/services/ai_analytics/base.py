"""Base class for AI Analytics plugins."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_analytics import AIToolType, AIUsageLog


class AIUsageEvent(BaseModel):
    """Standard AI usage event format."""

    tool_type: str
    tool_version: str | None = None
    event_type: str
    event_timestamp: datetime
    user_id: str | None = None
    user_hash: str | None = None
    language: str | None = None
    file_extension: str | None = None
    lines_generated: int = 0
    lines_accepted: int = 0
    tokens_used: int = 0
    latency_ms: int | None = None
    metadata: dict[str, Any] = {}


class AIToolMetrics(BaseModel):
    """Aggregated metrics for an AI tool."""

    tool_type: str
    period_start: datetime
    period_end: datetime

    # Usage counts
    total_events: int = 0
    total_completions: int = 0
    accepted_completions: int = 0
    rejected_completions: int = 0

    # Code metrics
    total_lines_generated: int = 0
    total_lines_accepted: int = 0
    acceptance_rate: float = 0.0

    # User metrics
    unique_users: int = 0
    active_users: int = 0

    # Performance metrics
    avg_latency_ms: float | None = None
    p95_latency_ms: float | None = None

    # Token usage
    total_tokens: int = 0
    estimated_cost: float = 0.0


class AIAnalyticsPlugin(ABC):
    """Base class for AI analytics plugins.

    Each plugin implements data collection from a specific AI tool.
    """

    def __init__(self, tool_type: AIToolType):
        self.tool_type = tool_type

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Plugin description."""
        pass

    @property
    def version(self) -> str:
        """Plugin version."""
        return "1.0.0"

    @abstractmethod
    async def collect(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_id: str | None,
        connection_config: dict[str, Any],
        since: datetime | None = None,
    ) -> list[AIUsageEvent]:
        """Collect usage data from the AI tool.

        Args:
            session: Database session
            tenant_id: Tenant ID for data isolation
            project_id: Optional project ID
            connection_config: Tool-specific connection configuration
            since: Only collect events after this timestamp

        Returns:
            List of usage events
        """
        pass

    @abstractmethod
    async def test_connection(
        self,
        connection_config: dict[str, Any],
    ) -> tuple[bool, str]:
        """Test the connection to the AI tool.

        Args:
            connection_config: Tool-specific connection configuration

        Returns:
            Tuple of (success, message)
        """
        pass

    async def save_events(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_id: str | None,
        events: list[AIUsageEvent],
    ) -> int:
        """Save usage events to the database.

        Args:
            session: Database session
            tenant_id: Tenant ID
            project_id: Optional project ID
            events: List of events to save

        Returns:
            Number of events saved
        """
        saved = 0
        for event in events:
            log = AIUsageLog(
                tenant_id=tenant_id,
                project_id=project_id,
                tool_type=event.tool_type,
                tool_version=event.tool_version,
                user_id=event.user_id,
                user_hash=event.user_hash,
                event_type=event.event_type,
                event_timestamp=event.event_timestamp,
                language=event.language,
                file_extension=event.file_extension,
                lines_generated=event.lines_generated,
                lines_accepted=event.lines_accepted,
                tokens_used=event.tokens_used,
                latency_ms=event.latency_ms,
                metadata=event.metadata,
            )
            session.add(log)
            saved += 1

        await session.commit()
        return saved

    @abstractmethod
    async def aggregate_metrics(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_id: str | None,
        period_start: datetime,
        period_end: datetime,
    ) -> AIToolMetrics:
        """Aggregate metrics for a time period.

        Args:
            session: Database session
            tenant_id: Tenant ID
            project_id: Optional project ID
            period_start: Start of period
            period_end: End of period

        Returns:
            Aggregated metrics
        """
        pass

    def get_schema(self) -> dict[str, Any]:
        """Get the configuration schema for this plugin."""
        return {
            "type": "object",
            "properties": {},
            "required": [],
        }
