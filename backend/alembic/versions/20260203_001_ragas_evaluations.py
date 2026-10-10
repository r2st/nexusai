"""Add RAGAS evaluation tables.

Revision ID: 20260203_001
Revises: 20260202_002
Create Date: 2026-02-03

This migration adds:
- ragas_evaluation_datasets: Reusable evaluation datasets
- ragas_evaluation_runs: Evaluation run records
- ragas_evaluation_samples: Individual sample results
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "20260203_001"
down_revision = "20260202_002"
branch_labels = None
depends_on = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists."""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    # Create ragas_evaluation_datasets table
    if not table_exists("ragas_evaluation_datasets"):
        op.create_table(
            "ragas_evaluation_datasets",
            sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False),
            # Dataset info
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            # Configuration
            sa.Column("default_metrics", postgresql.ARRAY(sa.String()), nullable=True),
            sa.Column("metric_thresholds", postgresql.JSONB(), nullable=True),
            # Sample count (denormalized for quick access)
            sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"),
            # Status
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            # Metadata
            sa.Column("dataset_metadata", postgresql.JSONB(), nullable=True),
            sa.Column("created_by", postgresql.UUID(as_uuid=False), nullable=True),
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

        op.create_index(
            "ix_ragas_datasets_tenant_id",
            "ragas_evaluation_datasets",
            ["tenant_id"],
        )
        op.create_index(
            "ix_ragas_datasets_tenant_name",
            "ragas_evaluation_datasets",
            ["tenant_id", "name"],
        )
        op.create_index(
            "ix_ragas_datasets_is_active",
            "ragas_evaluation_datasets",
            ["is_active"],
        )

    # Create ragas_evaluation_runs table
    if not table_exists("ragas_evaluation_runs"):
        op.create_table(
            "ragas_evaluation_runs",
            sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False),
            # Dataset reference (optional)
            sa.Column("dataset_id", postgresql.UUID(as_uuid=False), nullable=True),
            # Status
            sa.Column(
                "status",
                sa.String(20),
                nullable=False,
                server_default="pending",
            ),
            # Configuration
            sa.Column("metrics_evaluated", postgresql.ARRAY(sa.String()), nullable=True),
            sa.Column("thresholds", postgresql.JSONB(), nullable=True),
            sa.Column("llm_model", sa.String(100), nullable=True),
            sa.Column("llm_provider", sa.String(50), nullable=True),
            sa.Column("embeddings_model", sa.String(100), nullable=True),
            # Aggregate Results
            sa.Column("aggregate_scores", postgresql.JSONB(), nullable=True),
            sa.Column("overall_score", sa.Float(), nullable=True),
            sa.Column("pass_rate", sa.Float(), nullable=True),
            # Statistics
            sa.Column("total_samples", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("passed_samples", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("failed_samples", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("error_samples", sa.Integer(), nullable=False, server_default="0"),
            # Cost tracking
            sa.Column("total_tokens_used", sa.Integer(), nullable=True),
            sa.Column("total_cost_usd", sa.Float(), nullable=True),
            # Timing
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("total_duration_ms", sa.Float(), nullable=True),
            # Trace linkage
            sa.Column("trace_id", sa.String(255), nullable=True),
            # Metadata
            sa.Column("run_metadata", postgresql.JSONB(), nullable=True),
            sa.Column("triggered_by", sa.String(50), nullable=True),
            # Timestamps
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

        op.create_index(
            "ix_ragas_runs_tenant_id",
            "ragas_evaluation_runs",
            ["tenant_id"],
        )
        op.create_index(
            "ix_ragas_runs_dataset_id",
            "ragas_evaluation_runs",
            ["dataset_id"],
        )
        op.create_index(
            "ix_ragas_runs_status",
            "ragas_evaluation_runs",
            ["status"],
        )
        op.create_index(
            "ix_ragas_runs_tenant_created",
            "ragas_evaluation_runs",
            ["tenant_id", "created_at"],
        )
        op.create_index(
            "ix_ragas_runs_trace_id",
            "ragas_evaluation_runs",
            ["trace_id"],
        )

        # Foreign key to datasets (if dataset exists)
        op.create_foreign_key(
            "fk_ragas_runs_dataset",
            "ragas_evaluation_runs",
            "ragas_evaluation_datasets",
            ["dataset_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # Create ragas_evaluation_samples table
    if not table_exists("ragas_evaluation_samples"):
        op.create_table(
            "ragas_evaluation_samples",
            sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False),
            # Parent references
            sa.Column("run_id", postgresql.UUID(as_uuid=False), nullable=True),
            sa.Column("dataset_id", postgresql.UUID(as_uuid=False), nullable=True),
            # Sample data (hashed for privacy in some cases)
            sa.Column("user_input_hash", sa.String(64), nullable=True),
            sa.Column("response_hash", sa.String(64), nullable=True),
            # Or store full data (configurable)
            sa.Column("user_input", sa.Text(), nullable=True),
            sa.Column("response", sa.Text(), nullable=True),
            sa.Column("reference", sa.Text(), nullable=True),
            sa.Column("retrieved_contexts", postgresql.ARRAY(sa.Text()), nullable=True),
            # Metric results
            sa.Column("metrics", postgresql.JSONB(), nullable=True),
            sa.Column("overall_score", sa.Float(), nullable=True),
            sa.Column("passed", sa.Boolean(), nullable=False, server_default="false"),
            # Performance
            sa.Column("duration_ms", sa.Float(), nullable=True),
            # Error handling
            sa.Column("error", sa.Text(), nullable=True),
            # Metadata
            sa.Column("sample_metadata", postgresql.JSONB(), nullable=True),
            # Timestamps
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

        op.create_index(
            "ix_ragas_samples_tenant_id",
            "ragas_evaluation_samples",
            ["tenant_id"],
        )
        op.create_index(
            "ix_ragas_samples_run_id",
            "ragas_evaluation_samples",
            ["run_id"],
        )
        op.create_index(
            "ix_ragas_samples_dataset_id",
            "ragas_evaluation_samples",
            ["dataset_id"],
        )
        op.create_index(
            "ix_ragas_samples_passed",
            "ragas_evaluation_samples",
            ["passed"],
        )
        op.create_index(
            "ix_ragas_samples_run_passed",
            "ragas_evaluation_samples",
            ["run_id", "passed"],
        )

        # Foreign keys
        op.create_foreign_key(
            "fk_ragas_samples_run",
            "ragas_evaluation_samples",
            "ragas_evaluation_runs",
            ["run_id"],
            ["id"],
            ondelete="CASCADE",
        )
        op.create_foreign_key(
            "fk_ragas_samples_dataset",
            "ragas_evaluation_samples",
            "ragas_evaluation_datasets",
            ["dataset_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    # Drop ragas_evaluation_samples
    if table_exists("ragas_evaluation_samples"):
        op.drop_constraint("fk_ragas_samples_dataset", "ragas_evaluation_samples", type_="foreignkey")
        op.drop_constraint("fk_ragas_samples_run", "ragas_evaluation_samples", type_="foreignkey")
        op.drop_index("ix_ragas_samples_run_passed", table_name="ragas_evaluation_samples")
        op.drop_index("ix_ragas_samples_passed", table_name="ragas_evaluation_samples")
        op.drop_index("ix_ragas_samples_dataset_id", table_name="ragas_evaluation_samples")
        op.drop_index("ix_ragas_samples_run_id", table_name="ragas_evaluation_samples")
        op.drop_index("ix_ragas_samples_tenant_id", table_name="ragas_evaluation_samples")
        op.drop_table("ragas_evaluation_samples")

    # Drop ragas_evaluation_runs
    if table_exists("ragas_evaluation_runs"):
        op.drop_constraint("fk_ragas_runs_dataset", "ragas_evaluation_runs", type_="foreignkey")
        op.drop_index("ix_ragas_runs_trace_id", table_name="ragas_evaluation_runs")
        op.drop_index("ix_ragas_runs_tenant_created", table_name="ragas_evaluation_runs")
        op.drop_index("ix_ragas_runs_status", table_name="ragas_evaluation_runs")
        op.drop_index("ix_ragas_runs_dataset_id", table_name="ragas_evaluation_runs")
        op.drop_index("ix_ragas_runs_tenant_id", table_name="ragas_evaluation_runs")
        op.drop_table("ragas_evaluation_runs")

    # Drop ragas_evaluation_datasets
    if table_exists("ragas_evaluation_datasets"):
        op.drop_index("ix_ragas_datasets_is_active", table_name="ragas_evaluation_datasets")
        op.drop_index("ix_ragas_datasets_tenant_name", table_name="ragas_evaluation_datasets")
        op.drop_index("ix_ragas_datasets_tenant_id", table_name="ragas_evaluation_datasets")
        op.drop_table("ragas_evaluation_datasets")
