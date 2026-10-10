"""AI Analytics models for tracking AI tool usage and productivity metrics.

Supports the following AI tools:
- ai_analytics: Overall ROI and productivity metrics
- aisummary: AI-generated summaries
- cursor: Cursor IDE telemetry
- claude_code: Claude Code usage tracking
- github_copilot: GitHub Copilot metrics
- q_dev: Amazon Q Developer integration
"""

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

class AIToolType(str, Enum):
    """Types of AI development tools."""

    CURSOR = "cursor"
    CLAUDE_CODE = "claude_code"
    GITHUB_COPILOT = "github_copilot"
    Q_DEV = "q_dev"
    CHATGPT = "chatgpt"
    GEMINI = "gemini"
    CODY = "cody"
    TABNINE = "tabnine"
    OTHER = "other"


class MetricType(str, Enum):
    """Types of AI productivity metrics."""

    # Usage metrics
    COMPLETIONS_ACCEPTED = "completions_accepted"
    COMPLETIONS_REJECTED = "completions_rejected"
    CHAT_MESSAGES = "chat_messages"
    CODE_GENERATED = "code_generated"
    CODE_EDITED = "code_edited"

    # Time metrics
    TIME_SAVED = "time_saved"
    SESSION_DURATION = "session_duration"

    # Quality metrics
    BUGS_CAUGHT = "bugs_caught"
    TESTS_GENERATED = "tests_generated"
    DOCS_GENERATED = "docs_generated"

    # Cost metrics
    TOKENS_USED = "tokens_used"
    API_COST = "api_cost"


class AIUsageLog(Base):
    """Individual AI tool usage events.

    Captures granular usage data from AI development tools.
    """

    __tablename__ = "ai_usage_logs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
    )

    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
    )

    # Tool identification
    tool_type: Mapped[str] = mapped_column(String(50), nullable=False)
    tool_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # User info (anonymized)
    user_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    user_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)  # SHA256 for privacy

    # Event details
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Language/file context
    language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    file_extension: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Metrics
    lines_generated: Mapped[int] = mapped_column(Integer, default=0)
    lines_accepted: Mapped[int] = mapped_column(Integer, default=0)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Additional data (renamed from 'metadata' which is reserved in SQLAlchemy)
    event_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index("ix_ai_usage_logs_tenant_id", "tenant_id"),
        Index("ix_ai_usage_logs_project_id", "project_id"),
        Index("ix_ai_usage_logs_tool_type", "tool_type"),
        Index("ix_ai_usage_logs_event_timestamp", "event_timestamp"),
    )


class AIAnalyticsMetric(Base):
    """Aggregated AI analytics metrics.

    Pre-computed metrics for dashboards and reporting.
    """

    __tablename__ = "ai_analytics_metrics"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
    )

    project_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
    )

    # Metric identification
    metric_type: Mapped[str] = mapped_column(String(100), nullable=False)
    tool_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Time period
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    granularity: Mapped[str] = mapped_column(String(20), default="daily")  # hourly, daily, weekly, monthly

    # Values
    value: Mapped[float] = mapped_column(Float, nullable=False)
    count: Mapped[int] = mapped_column(Integer, default=0)
    min_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_value: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Dimensions
    dimensions: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index("ix_ai_metrics_tenant_id", "tenant_id"),
        Index("ix_ai_metrics_project_id", "project_id"),
        Index("ix_ai_metrics_period", "period_start", "period_end"),
        Index("ix_ai_metrics_type", "metric_type"),
    )


class AISummary(Base):
    """AI-generated summaries for projects, PRs, and metrics.

    Provides automated insights and summaries powered by LLMs.
    """

    __tablename__ = "ai_summaries"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
    )

    project_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
    )

    # Summary type
    summary_type: Mapped[str] = mapped_column(String(100), nullable=False)  # sprint, pr, metrics, incident
    target_id: Mapped[str | None] = mapped_column(String(255), nullable=True)  # e.g., PR number, sprint ID
    target_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Content
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    key_points: Mapped[list] = mapped_column(JSONB, default=list)
    recommendations: Mapped[list] = mapped_column(JSONB, default=list)

    # Generation metadata
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    generation_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Time period covered
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Status
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index("ix_ai_summaries_tenant_id", "tenant_id"),
        Index("ix_ai_summaries_project_id", "project_id"),
        Index("ix_ai_summaries_type", "summary_type"),
    )


class AIToolConnection(Base):
    """Configuration for AI tool data collection.

    Stores connection settings for each AI development tool.
    """

    __tablename__ = "ai_tool_connections"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
    )

    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="CASCADE"),
    )

    # Tool info
    tool_type: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Connection details (secret stored in OpenBao)
    endpoint: Mapped[str | None] = mapped_column(Text, nullable=True)
    secret_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Collection settings
    collection_interval: Mapped[int] = mapped_column(Integer, default=3600)  # seconds
    last_collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    status_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Configuration
    config: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index("ix_ai_tool_connections_tenant_id", "tenant_id"),
        Index("ix_ai_tool_connections_project_id", "project_id"),
        Index("ix_ai_tool_connections_tool_type", "tool_type"),
    )


class AIROIMetric(Base):
    """AI Return on Investment calculations.

    Tracks the business value and ROI of AI tool adoption.
    """

    __tablename__ = "ai_roi_metrics"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
    )

    project_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
    )

    # Time period
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Cost metrics
    total_license_cost: Mapped[float] = mapped_column(Float, default=0.0)
    total_api_cost: Mapped[float] = mapped_column(Float, default=0.0)
    total_infrastructure_cost: Mapped[float] = mapped_column(Float, default=0.0)

    # Value metrics
    estimated_time_saved_hours: Mapped[float] = mapped_column(Float, default=0.0)
    hourly_developer_cost: Mapped[float] = mapped_column(Float, default=100.0)
    estimated_value_generated: Mapped[float] = mapped_column(Float, default=0.0)

    # ROI calculation
    roi_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    payback_period_days: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Usage stats
    total_users: Mapped[int] = mapped_column(Integer, default=0)
    active_users: Mapped[int] = mapped_column(Integer, default=0)
    adoption_rate: Mapped[float] = mapped_column(Float, default=0.0)

    # Productivity metrics
    lines_of_code_generated: Mapped[int] = mapped_column(Integer, default=0)
    acceptance_rate: Mapped[float] = mapped_column(Float, default=0.0)
    bugs_prevented: Mapped[int] = mapped_column(Integer, default=0)

    # Breakdown by tool
    tool_breakdown: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index("ix_ai_roi_metrics_tenant_id", "tenant_id"),
        Index("ix_ai_roi_metrics_project_id", "project_id"),
        Index("ix_ai_roi_metrics_period", "period_start", "period_end"),
    )
