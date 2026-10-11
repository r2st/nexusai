"""Cost entry model for persistent LLM cost tracking.

Stores individual cost entries for analytics, reporting, and budget management.
"""

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RequestType(str, Enum):
    """Types of LLM requests."""

    CHAT = "chat"
    COMPLETION = "completion"
    EMBEDDING = "embedding"
    IMAGE = "image"
    AUDIO = "audio"
    MODERATION = "moderation"


class CostEntry(Base):
    """Individual LLM cost entry for tracking and analytics.

    Captures granular cost data from LLM requests for budgeting,
    reporting, and optimization.
    """

    __tablename__ = "cost_entries"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Tenant and user identification
    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("organizations.tenant_id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Request identification
    request_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )
    conversation_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Provider and model
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # Token usage
    prompt_tokens: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    completion_tokens: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    total_tokens: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Cost in USD (stored with 6 decimal precision)
    cost_usd: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    # Request type
    request_type: Mapped[str] = mapped_column(
        String(50),
        default=RequestType.CHAT.value,
        nullable=False,
    )

    # Performance metrics
    latency_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Success tracking
    success: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
    )
    error_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # Additional metadata
    entry_metadata: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint("cost_usd >= 0", name="ck_cost_entries_cost_non_negative"),
        CheckConstraint("total_tokens >= 0", name="ck_cost_entries_tokens_non_negative"),
        CheckConstraint(
            "request_type IN ('chat', 'completion', 'embedding', 'image', 'audio', 'moderation')",
            name="ck_cost_entries_request_type",
        ),
        # Primary lookup indexes
        Index("ix_cost_entries_tenant_id", "tenant_id"),
        Index("ix_cost_entries_user_id", "user_id"),
        Index("ix_cost_entries_request_id", "request_id"),
        # Time-series queries
        Index("ix_cost_entries_created_at", "created_at"),
        Index("ix_cost_entries_tenant_created", "tenant_id", "created_at"),
        # Breakdown queries
        Index("ix_cost_entries_provider", "provider"),
        Index("ix_cost_entries_model", "model"),
        Index("ix_cost_entries_tenant_provider", "tenant_id", "provider"),
        Index("ix_cost_entries_tenant_model", "tenant_id", "model"),
        # Composite for common dashboard queries
        Index(
            "ix_cost_entries_tenant_time_model",
            "tenant_id",
            "created_at",
            "model",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<CostEntry(id={self.id}, "
            f"provider={self.provider}, "
            f"model={self.model}, "
            f"cost_usd={self.cost_usd:.6f})>"
        )


class CostBudget(Base):
    """Budget configuration for cost management.

    Defines spending limits at tenant, user, or project level.
    """

    __tablename__ = "cost_budgets"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("organizations.tenant_id", ondelete="CASCADE"),
        nullable=False,
    )

    # Scope (tenant, user, or project level)
    scope: Mapped[str] = mapped_column(
        String(50),
        default="tenant",
        nullable=False,
    )  # "tenant", "user", "project"
    scope_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
    )  # user_id or project_id if scoped

    # Budget limits (USD)
    daily_limit: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    monthly_limit: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # Alert thresholds (percentage, 0-100)
    alert_threshold: Mapped[int] = mapped_column(
        Integer,
        default=80,
        nullable=False,
    )
    critical_threshold: Mapped[int] = mapped_column(
        Integer,
        default=95,
        nullable=False,
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "scope IN ('tenant', 'user', 'project')",
            name="ck_cost_budgets_scope",
        ),
        CheckConstraint(
            "alert_threshold BETWEEN 0 AND 100",
            name="ck_cost_budgets_alert_threshold_range",
        ),
        CheckConstraint(
            "critical_threshold BETWEEN 0 AND 100",
            name="ck_cost_budgets_critical_threshold_range",
        ),
        Index("ix_cost_budgets_tenant_id", "tenant_id"),
        Index("ix_cost_budgets_scope", "scope", "scope_id"),
    )


class CostAlert(Base):
    """Cost alert records for budget notifications.

    Tracks when budget thresholds are crossed.
    """

    __tablename__ = "cost_alerts"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("organizations.tenant_id", ondelete="CASCADE"),
        nullable=False,
    )

    budget_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("cost_budgets.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Alert details
    alert_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # "warning", "critical", "exceeded"
    threshold_percent: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    current_spend: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    budget_limit: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    # Period
    period_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )  # "daily", "monthly"
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Status
    acknowledged: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    acknowledged_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_cost_alerts_tenant_id", "tenant_id"),
        Index("ix_cost_alerts_budget_id", "budget_id"),
        Index("ix_cost_alerts_created_at", "created_at"),
        Index("ix_cost_alerts_unacknowledged", "tenant_id", "acknowledged"),
    )
