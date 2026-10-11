"""Create prompts, prompt_versions, prompt_experiments, and prompt_performance tables.

Revision ID: 20260119_004
Revises: 20260119_003
Create Date: 2026-01-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260119_004"
down_revision = "20260119_003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create prompts table
    op.create_table(
        "prompts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("template", sa.Text(), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("variables", postgresql.ARRAY(sa.String(100)), server_default="{}"),
        sa.Column("default_model", sa.String(100), nullable=True),
        sa.Column("default_temperature", sa.Float(), server_default="0.7"),
        sa.Column("default_max_tokens", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(50), server_default="draft"),
        sa.Column("current_version", sa.Integer(), server_default="1"),
        sa.Column("tags", postgresql.ARRAY(sa.String(100)), server_default="{}"),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_by", sa.String(36), nullable=True),
    )

    op.create_unique_constraint("uq_prompts_tenant_slug", "prompts", ["tenant_id", "slug"])
    op.create_index("ix_prompts_tenant_id", "prompts", ["tenant_id"])
    op.create_index("ix_prompts_tenant_category", "prompts", ["tenant_id", "category"])

    # RLS for prompts
    op.execute("ALTER TABLE prompts ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE prompts FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_policy ON prompts
        FOR ALL
        USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
    """)

    # Create prompt_versions table
    op.create_table(
        "prompt_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("prompt_id", sa.String(36), sa.ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("template", sa.Text(), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=True),
        sa.Column("variables", postgresql.ARRAY(sa.String(100)), server_default="{}"),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("temperature", sa.Float(), server_default="0.7"),
        sa.Column("max_tokens", sa.Integer(), nullable=True),
        sa.Column("change_description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("usage_count", sa.Integer(), server_default="0"),
        sa.Column("avg_latency_ms", sa.Float(), nullable=True),
        sa.Column("avg_tokens", sa.Float(), nullable=True),
        sa.Column("success_rate", sa.Float(), nullable=True),
    )

    op.create_unique_constraint("uq_prompt_versions", "prompt_versions", ["prompt_id", "version"])
    op.create_index("ix_prompt_versions_prompt_id", "prompt_versions", ["prompt_id"])

    # Create prompt_experiments table
    op.create_table(
        "prompt_experiments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("prompt_id", sa.String(36), sa.ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("control_version", sa.Integer(), nullable=False),
        sa.Column("treatment_versions", postgresql.ARRAY(sa.Integer()), server_default="{}"),
        sa.Column("traffic_percentage", sa.Float(), server_default="10.0"),
        sa.Column("variant_weights", postgresql.JSONB(), server_default="{}"),
        sa.Column("target_users", postgresql.ARRAY(sa.String(36)), nullable=True),
        sa.Column("target_percentage", sa.Float(), server_default="100.0"),
        sa.Column("primary_metric", sa.String(100), server_default="success_rate"),
        sa.Column("secondary_metrics", postgresql.ARRAY(sa.String(100)), server_default="{}"),
        sa.Column("status", sa.String(50), server_default="draft"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("winner_version", sa.Integer(), nullable=True),
        sa.Column("statistical_significance", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_by", sa.String(36), nullable=True),
    )

    op.create_index("ix_prompt_experiments_tenant_id", "prompt_experiments", ["tenant_id"])
    op.create_index("ix_prompt_experiments_prompt_id", "prompt_experiments", ["prompt_id"])
    op.create_index("ix_prompt_experiments_status", "prompt_experiments", ["status"])

    # RLS for experiments
    op.execute("ALTER TABLE prompt_experiments ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE prompt_experiments FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_policy ON prompt_experiments
        FOR ALL
        USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
    """)

    # Create prompt_assignments table
    op.create_table(
        "prompt_assignments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("experiment_id", sa.String(36), sa.ForeignKey("prompt_experiments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("assigned_version", sa.Integer(), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("assignment_hash", sa.String(64), nullable=True),
    )

    op.create_unique_constraint("uq_prompt_assignments", "prompt_assignments", ["experiment_id", "user_id"])
    op.create_index("ix_prompt_assignments_experiment_id", "prompt_assignments", ["experiment_id"])

    # Create prompt_performance table
    op.create_table(
        "prompt_performance",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("prompt_id", sa.String(36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=True),
        sa.Column("session_id", sa.String(36), nullable=True),
        sa.Column("experiment_id", sa.String(36), nullable=True),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("input_tokens", sa.Integer(), server_default="0"),
        sa.Column("output_tokens", sa.Integer(), server_default="0"),
        sa.Column("latency_ms", sa.Float(), server_default="0"),
        sa.Column("success", sa.Boolean(), server_default="true"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("ix_prompt_performance_tenant_id", "prompt_performance", ["tenant_id"])
    op.create_index("ix_prompt_performance_prompt_version", "prompt_performance", ["prompt_id", "version"])
    op.create_index("ix_prompt_performance_executed_at", "prompt_performance", ["executed_at"])

    # RLS for performance
    op.execute("ALTER TABLE prompt_performance ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE prompt_performance FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_policy ON prompt_performance
        FOR ALL
        USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON prompt_performance")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON prompt_experiments")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON prompts")

    op.drop_table("prompt_performance")
    op.drop_table("prompt_assignments")
    op.drop_table("prompt_experiments")
    op.drop_table("prompt_versions")
    op.drop_table("prompts")
