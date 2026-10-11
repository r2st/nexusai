"""Hallucination detection log model for tracking and analytics.

Stores hallucination check results for quality monitoring and analysis.
"""

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CheckType(str, Enum):
    """Types of hallucination checks."""

    STANDARD = "standard"
    RAG = "rag"
    CONSISTENCY = "consistency"
    CITATION = "citation"
    SEMANTIC = "semantic"


class HallucinationLog(Base):
    """Log entry for hallucination detection results.

    Captures hallucination check outcomes for quality monitoring,
    trend analysis, and model evaluation.
    """

    __tablename__ = "hallucination_logs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Tenant identification
    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("organizations.tenant_id", ondelete="CASCADE"),
        nullable=False,
    )

    # Trace linkage (for observability correlation)
    trace_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    span_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    request_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # LLM context (hashed for privacy)
    query_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    response_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    context_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    # Model information
    model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    provider: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # Check type
    check_type: Mapped[str] = mapped_column(
        String(50),
        default=CheckType.STANDARD.value,
        nullable=False,
    )

    # Scores (0.0 to 1.0)
    hallucination_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    grounding_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    relevance_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    factuality_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    consistency_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # All scores as JSONB for flexibility
    scores: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
    )

    # Detection result
    is_hallucination: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )
    threshold_used: Mapped[float] = mapped_column(
        Float,
        default=0.7,
        nullable=False,
    )

    # Issues found
    issues: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        default=list,
    )
    issue_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Explanation
    explanation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Detection method
    detection_method: Mapped[str] = mapped_column(
        String(50),
        default="phoenix",
        nullable=False,
    )  # "phoenix", "heuristic", "semantic", "hybrid"

    # Performance
    duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # RAG-specific fields
    context_document_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    context_token_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Additional metadata
    log_metadata: Mapped[dict] = mapped_column(
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
        CheckConstraint(
            "check_type IN ('standard', 'rag', 'consistency', 'citation', 'semantic')",
            name="ck_hallucination_logs_check_type",
        ),
        CheckConstraint(
            "hallucination_score >= 0.0 AND hallucination_score <= 1.0",
            name="ck_hallucination_logs_score_range",
        ),
        # Primary lookup indexes
        Index("ix_hallucination_logs_tenant_id", "tenant_id"),
        Index("ix_hallucination_logs_trace_id", "trace_id"),
        Index("ix_hallucination_logs_request_id", "request_id"),
        # Time-series queries
        Index("ix_hallucination_logs_created_at", "created_at"),
        Index("ix_hallucination_logs_tenant_created", "tenant_id", "created_at"),
        # Filtering queries
        Index("ix_hallucination_logs_is_hallucination", "is_hallucination"),
        Index("ix_hallucination_logs_check_type", "check_type"),
        Index("ix_hallucination_logs_model", "model"),
        # Composite for dashboard queries
        Index(
            "ix_hallucination_logs_tenant_type_created",
            "tenant_id",
            "check_type",
            "created_at",
        ),
        # Partial index for hallucinations only
        Index(
            "ix_hallucination_logs_detected",
            "tenant_id",
            "created_at",
            postgresql_where="is_hallucination = true",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<HallucinationLog(id={self.id}, "
            f"is_hallucination={self.is_hallucination}, "
            f"score={self.hallucination_score:.3f})>"
        )


class HallucinationMetric(Base):
    """Aggregated hallucination metrics for dashboards.

    Pre-computed metrics for faster dashboard queries.
    """

    __tablename__ = "hallucination_metrics"

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

    # Time period
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    granularity: Mapped[str] = mapped_column(
        String(20),
        default="daily",
        nullable=False,
    )  # "hourly", "daily", "weekly", "monthly"

    # Dimensions
    model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    provider: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    check_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # Counts
    total_checks: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    hallucination_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Rates
    hallucination_rate: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    # Score statistics
    avg_hallucination_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    avg_grounding_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    avg_confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # Performance
    avg_duration_ms: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # Issue breakdown
    issue_counts: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
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
        Index("ix_hallucination_metrics_tenant_id", "tenant_id"),
        Index("ix_hallucination_metrics_period", "period_start", "period_end"),
        Index(
            "ix_hallucination_metrics_tenant_period",
            "tenant_id",
            "period_start",
            "granularity",
        ),
    )
