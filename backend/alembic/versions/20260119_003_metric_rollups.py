"""Create metric_rollups table for precomputed analytics.

Revision ID: 20260119_003
Revises: 20260119_002
Create Date: 2026-01-19

This migration creates the metric_rollups table for storing
precomputed DORA and SPACE metric aggregations.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260119_003"
down_revision = "20260119_002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create metric_rollups table
    op.create_table(
        "metric_rollups",
        # Primary key
        sa.Column("id", sa.String(36), primary_key=True),

        # Tenant isolation
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False),

        # Metric info
        sa.Column("metric_type", sa.String(50), nullable=False),  # dora, space
        sa.Column("granularity", sa.String(50), nullable=False),  # hourly, daily, weekly, monthly

        # Time period
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),

        # Scope
        sa.Column("project_id", sa.String(36), nullable=True),
        sa.Column("team_id", sa.String(36), nullable=True),
        sa.Column("service_id", sa.String(36), nullable=True),
        sa.Column("environment", sa.String(100), nullable=True),

        # Computation metadata
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("data_points", sa.Integer(), default=0),
        sa.Column("is_partial", sa.Boolean(), default=False),

        # Flexible data storage
        sa.Column("data", postgresql.JSONB(), default=dict),

        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    # Unique constraint for deduplication
    op.create_unique_constraint(
        "uq_metric_rollups",
        "metric_rollups",
        ["tenant_id", "metric_type", "granularity", "period_start", "project_id"],
    )

    # Indexes for queries
    op.create_index(
        "ix_metric_rollups_tenant_id",
        "metric_rollups",
        ["tenant_id"],
    )
    op.create_index(
        "ix_metric_rollups_tenant_type_granularity",
        "metric_rollups",
        ["tenant_id", "metric_type", "granularity"],
    )
    op.create_index(
        "ix_metric_rollups_period",
        "metric_rollups",
        ["tenant_id", "period_start", "period_end"],
    )
    op.create_index(
        "ix_metric_rollups_project",
        "metric_rollups",
        ["tenant_id", "project_id"],
    )

    # Enable RLS
    op.execute("ALTER TABLE metric_rollups ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE metric_rollups FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_policy ON metric_rollups
        FOR ALL
        USING (
            tenant_id = current_setting('app.current_tenant_id', true)::uuid
        )
        WITH CHECK (
            tenant_id = current_setting('app.current_tenant_id', true)::uuid
        )
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON metric_rollups")
    op.drop_table("metric_rollups")
