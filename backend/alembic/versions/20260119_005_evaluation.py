"""Create eval_test_sets and eval_runs tables for evaluation framework.

Revision ID: 20260119_005
Revises: 20260119_004
Create Date: 2026-01-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260119_005"
down_revision = "20260119_004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create eval_test_sets table
    op.create_table(
        "eval_test_sets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("prompt_id", sa.String(36), nullable=True),
        sa.Column("test_cases", postgresql.JSONB(), default=[]),
        sa.Column("default_eval_type", sa.String(50), default="contains"),
        sa.Column("pass_threshold", sa.Float(), default=0.8),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("version", sa.Integer(), default=1),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_by", sa.String(36), nullable=True),
    )

    op.create_index("ix_eval_test_sets_tenant_id", "eval_test_sets", ["tenant_id"])
    op.create_index("ix_eval_test_sets_prompt_id", "eval_test_sets", ["prompt_id"])

    # RLS for test sets
    op.execute("ALTER TABLE eval_test_sets ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE eval_test_sets FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_policy ON eval_test_sets
        FOR ALL
        USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
    """)

    # Create eval_runs table
    op.create_table(
        "eval_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("test_set_id", sa.String(36), nullable=False),
        sa.Column("test_set_name", sa.String(255), nullable=True),
        sa.Column("prompt_id", sa.String(36), nullable=True),
        sa.Column("prompt_version", sa.Integer(), nullable=True),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("temperature", sa.Float(), default=0.7),
        sa.Column("max_tokens", sa.Integer(), nullable=True),
        sa.Column("results", postgresql.JSONB(), default=[]),
        sa.Column("status", sa.String(50), default="pending"),
        sa.Column("total_cases", sa.Integer(), default=0),
        sa.Column("passed_cases", sa.Integer(), default=0),
        sa.Column("failed_cases", sa.Integer(), default=0),
        sa.Column("error_cases", sa.Integer(), default=0),
        sa.Column("pass_rate", sa.Float(), default=0.0),
        sa.Column("avg_score", sa.Float(), default=0.0),
        sa.Column("avg_latency_ms", sa.Float(), default=0.0),
        sa.Column("total_cost_usd", sa.Float(), default=0.0),
        sa.Column("baseline_run_id", sa.String(36), nullable=True),
        sa.Column("regression_detected", sa.Boolean(), default=False),
        sa.Column("regression_details", postgresql.JSONB(), default=dict),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("triggered_by", sa.String(50), default="manual"),
        sa.Column("git_commit", sa.String(100), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), default=dict),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("ix_eval_runs_tenant_id", "eval_runs", ["tenant_id"])
    op.create_index("ix_eval_runs_test_set_id", "eval_runs", ["test_set_id"])
    op.create_index("ix_eval_runs_prompt_id", "eval_runs", ["prompt_id"])
    op.create_index("ix_eval_runs_status", "eval_runs", ["status"])
    op.create_index("ix_eval_runs_created_at", "eval_runs", ["created_at"])

    # RLS for eval runs
    op.execute("ALTER TABLE eval_runs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE eval_runs FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_policy ON eval_runs
        FOR ALL
        USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON eval_runs")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON eval_test_sets")

    op.drop_table("eval_runs")
    op.drop_table("eval_test_sets")
