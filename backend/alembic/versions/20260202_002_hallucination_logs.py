"""Add hallucination detection log tables.

Revision ID: 20260202_002
Revises: 20260202_001
Create Date: 2026-02-02

This migration adds:
- hallucination_logs table for tracking detection results
- hallucination_metrics table for pre-aggregated dashboard metrics
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "20260202_002"
down_revision = "20260202_001"
branch_labels = None
depends_on = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists."""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    # Create hallucination_logs table
    if not table_exists("hallucination_logs"):
        op.create_table(
            "hallucination_logs",
            sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
            # Tenant
            sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False),
            # Trace linkage
            sa.Column("trace_id", sa.String(255), nullable=True),
            sa.Column("span_id", sa.String(255), nullable=True),
            sa.Column("request_id", sa.String(255), nullable=True),
            # Hashed content for privacy
            sa.Column("query_hash", sa.String(64), nullable=False),
            sa.Column("response_hash", sa.String(64), nullable=False),
            sa.Column("context_hash", sa.String(64), nullable=True),
            # Model info
            sa.Column("model", sa.String(100), nullable=True),
            sa.Column("provider", sa.String(50), nullable=True),
            # Check type
            sa.Column("check_type", sa.String(50), nullable=False, server_default="standard"),
            # Scores
            sa.Column("hallucination_score", sa.Float(), nullable=False),
            sa.Column("grounding_score", sa.Float(), nullable=True),
            sa.Column("relevance_score", sa.Float(), nullable=True),
            sa.Column("factuality_score", sa.Float(), nullable=True),
            sa.Column("consistency_score", sa.Float(), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column("scores", postgresql.JSONB(), nullable=True),
            # Detection result
            sa.Column("is_hallucination", sa.Boolean(), nullable=False),
            sa.Column("threshold_used", sa.Float(), nullable=False, server_default="0.7"),
            # Issues
            sa.Column("issues", postgresql.ARRAY(sa.String()), nullable=True),
            sa.Column("issue_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("explanation", sa.Text(), nullable=True),
            # Detection method
            sa.Column("detection_method", sa.String(50), nullable=False, server_default="phoenix"),
            # Performance
            sa.Column("duration_ms", sa.Integer(), nullable=True),
            # RAG-specific
            sa.Column("context_document_count", sa.Integer(), nullable=True),
            sa.Column("context_token_count", sa.Integer(), nullable=True),
            # Metadata
            sa.Column("log_metadata", postgresql.JSONB(), nullable=True),
            # Timestamps
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

        # Create indexes
        op.create_index("ix_hallucination_logs_tenant_id", "hallucination_logs", ["tenant_id"])
        op.create_index("ix_hallucination_logs_trace_id", "hallucination_logs", ["trace_id"])
        op.create_index("ix_hallucination_logs_request_id", "hallucination_logs", ["request_id"])
        op.create_index("ix_hallucination_logs_created_at", "hallucination_logs", ["created_at"])
        op.create_index(
            "ix_hallucination_logs_tenant_created",
            "hallucination_logs",
            ["tenant_id", "created_at"],
        )
        op.create_index("ix_hallucination_logs_is_hallucination", "hallucination_logs", ["is_hallucination"])
        op.create_index("ix_hallucination_logs_check_type", "hallucination_logs", ["check_type"])
        op.create_index("ix_hallucination_logs_model", "hallucination_logs", ["model"])
        op.create_index(
            "ix_hallucination_logs_tenant_type_created",
            "hallucination_logs",
            ["tenant_id", "check_type", "created_at"],
        )
        # Partial index for hallucinations only
        op.create_index(
            "ix_hallucination_logs_detected",
            "hallucination_logs",
            ["tenant_id", "created_at"],
            postgresql_where=sa.text("is_hallucination = true"),
        )

    # Create hallucination_metrics table
    if not table_exists("hallucination_metrics"):
        op.create_table(
            "hallucination_metrics",
            sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False),
            # Time period
            sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
            sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
            sa.Column("granularity", sa.String(20), nullable=False, server_default="daily"),
            # Dimensions
            sa.Column("model", sa.String(100), nullable=True),
            sa.Column("provider", sa.String(50), nullable=True),
            sa.Column("check_type", sa.String(50), nullable=True),
            # Counts
            sa.Column("total_checks", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("hallucination_count", sa.Integer(), nullable=False, server_default="0"),
            # Rates
            sa.Column("hallucination_rate", sa.Float(), nullable=False, server_default="0.0"),
            # Score statistics
            sa.Column("avg_hallucination_score", sa.Float(), nullable=True),
            sa.Column("avg_grounding_score", sa.Float(), nullable=True),
            sa.Column("avg_confidence", sa.Float(), nullable=True),
            # Performance
            sa.Column("avg_duration_ms", sa.Float(), nullable=True),
            # Issue breakdown
            sa.Column("issue_counts", postgresql.JSONB(), nullable=True),
            # Timestamps
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

        op.create_index("ix_hallucination_metrics_tenant_id", "hallucination_metrics", ["tenant_id"])
        op.create_index(
            "ix_hallucination_metrics_period",
            "hallucination_metrics",
            ["period_start", "period_end"],
        )
        op.create_index(
            "ix_hallucination_metrics_tenant_period",
            "hallucination_metrics",
            ["tenant_id", "period_start", "granularity"],
        )


def downgrade() -> None:
    # Drop hallucination_metrics table
    if table_exists("hallucination_metrics"):
        op.drop_index("ix_hallucination_metrics_tenant_period", table_name="hallucination_metrics")
        op.drop_index("ix_hallucination_metrics_period", table_name="hallucination_metrics")
        op.drop_index("ix_hallucination_metrics_tenant_id", table_name="hallucination_metrics")
        op.drop_table("hallucination_metrics")

    # Drop hallucination_logs table
    if table_exists("hallucination_logs"):
        op.drop_index("ix_hallucination_logs_detected", table_name="hallucination_logs")
        op.drop_index("ix_hallucination_logs_tenant_type_created", table_name="hallucination_logs")
        op.drop_index("ix_hallucination_logs_model", table_name="hallucination_logs")
        op.drop_index("ix_hallucination_logs_check_type", table_name="hallucination_logs")
        op.drop_index("ix_hallucination_logs_is_hallucination", table_name="hallucination_logs")
        op.drop_index("ix_hallucination_logs_tenant_created", table_name="hallucination_logs")
        op.drop_index("ix_hallucination_logs_created_at", table_name="hallucination_logs")
        op.drop_index("ix_hallucination_logs_request_id", table_name="hallucination_logs")
        op.drop_index("ix_hallucination_logs_trace_id", table_name="hallucination_logs")
        op.drop_index("ix_hallucination_logs_tenant_id", table_name="hallucination_logs")
        op.drop_table("hallucination_logs")
