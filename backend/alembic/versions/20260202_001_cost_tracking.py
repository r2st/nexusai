"""Add cost tracking tables for LLM cost analytics.

Revision ID: 20260202_001
Revises: 20260120_004
Create Date: 2026-02-02

This migration adds:
- cost_entries table for granular LLM cost tracking
- cost_budgets table for budget configuration
- cost_alerts table for budget alert notifications
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "20260202_001"
down_revision = "20260120_004"
branch_labels = None
depends_on = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists."""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    # Create cost_entries table
    if not table_exists("cost_entries"):
        op.create_table(
            "cost_entries",
            sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
            # Tenant and user identification
            sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=True),
            # Request identification
            sa.Column("request_id", sa.String(255), nullable=False, unique=True),
            sa.Column("conversation_id", postgresql.UUID(as_uuid=False), nullable=True),
            # Provider and model
            sa.Column("provider", sa.String(50), nullable=False),
            sa.Column("model", sa.String(100), nullable=False),
            # Token usage
            sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
            # Cost in USD
            sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0.0"),
            # Request type
            sa.Column("request_type", sa.String(50), nullable=False, server_default="chat"),
            # Performance
            sa.Column("latency_ms", sa.Integer(), nullable=True),
            # Success tracking
            sa.Column("success", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("error_type", sa.String(100), nullable=True),
            # Metadata
            sa.Column("entry_metadata", postgresql.JSONB(), nullable=True),
            # Timestamps
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

        # Create indexes for cost_entries
        op.create_index("ix_cost_entries_tenant_id", "cost_entries", ["tenant_id"])
        op.create_index("ix_cost_entries_user_id", "cost_entries", ["user_id"])
        op.create_index("ix_cost_entries_request_id", "cost_entries", ["request_id"])
        op.create_index("ix_cost_entries_created_at", "cost_entries", ["created_at"])
        op.create_index("ix_cost_entries_tenant_created", "cost_entries", ["tenant_id", "created_at"])
        op.create_index("ix_cost_entries_provider", "cost_entries", ["provider"])
        op.create_index("ix_cost_entries_model", "cost_entries", ["model"])
        op.create_index("ix_cost_entries_tenant_provider", "cost_entries", ["tenant_id", "provider"])
        op.create_index("ix_cost_entries_tenant_model", "cost_entries", ["tenant_id", "model"])
        op.create_index(
            "ix_cost_entries_tenant_time_model",
            "cost_entries",
            ["tenant_id", "created_at", "model"],
        )

    # Create cost_budgets table
    if not table_exists("cost_budgets"):
        op.create_table(
            "cost_budgets",
            sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False),
            # Scope
            sa.Column("scope", sa.String(50), nullable=False, server_default="tenant"),
            sa.Column("scope_id", postgresql.UUID(as_uuid=False), nullable=True),
            # Budget limits
            sa.Column("daily_limit", sa.Float(), nullable=True),
            sa.Column("monthly_limit", sa.Float(), nullable=True),
            # Alert thresholds
            sa.Column("alert_threshold", sa.Integer(), nullable=False, server_default="80"),
            sa.Column("critical_threshold", sa.Integer(), nullable=False, server_default="95"),
            # Status
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
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

        op.create_index("ix_cost_budgets_tenant_id", "cost_budgets", ["tenant_id"])
        op.create_index("ix_cost_budgets_scope", "cost_budgets", ["scope", "scope_id"])

    # Create cost_alerts table
    if not table_exists("cost_alerts"):
        op.create_table(
            "cost_alerts",
            sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False),
            sa.Column("budget_id", postgresql.UUID(as_uuid=False), nullable=False),
            # Alert details
            sa.Column("alert_type", sa.String(50), nullable=False),
            sa.Column("threshold_percent", sa.Integer(), nullable=False),
            sa.Column("current_spend", sa.Float(), nullable=False),
            sa.Column("budget_limit", sa.Float(), nullable=False),
            # Period
            sa.Column("period_type", sa.String(20), nullable=False),
            sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
            # Status
            sa.Column("acknowledged", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("acknowledged_by", postgresql.UUID(as_uuid=False), nullable=True),
            # Timestamps
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

        op.create_index("ix_cost_alerts_tenant_id", "cost_alerts", ["tenant_id"])
        op.create_index("ix_cost_alerts_budget_id", "cost_alerts", ["budget_id"])
        op.create_index("ix_cost_alerts_created_at", "cost_alerts", ["created_at"])
        op.create_index("ix_cost_alerts_unacknowledged", "cost_alerts", ["tenant_id", "acknowledged"])


def downgrade() -> None:
    # Drop cost_alerts table
    if table_exists("cost_alerts"):
        op.drop_index("ix_cost_alerts_unacknowledged", table_name="cost_alerts")
        op.drop_index("ix_cost_alerts_created_at", table_name="cost_alerts")
        op.drop_index("ix_cost_alerts_budget_id", table_name="cost_alerts")
        op.drop_index("ix_cost_alerts_tenant_id", table_name="cost_alerts")
        op.drop_table("cost_alerts")

    # Drop cost_budgets table
    if table_exists("cost_budgets"):
        op.drop_index("ix_cost_budgets_scope", table_name="cost_budgets")
        op.drop_index("ix_cost_budgets_tenant_id", table_name="cost_budgets")
        op.drop_table("cost_budgets")

    # Drop cost_entries table
    if table_exists("cost_entries"):
        op.drop_index("ix_cost_entries_tenant_time_model", table_name="cost_entries")
        op.drop_index("ix_cost_entries_tenant_model", table_name="cost_entries")
        op.drop_index("ix_cost_entries_tenant_provider", table_name="cost_entries")
        op.drop_index("ix_cost_entries_model", table_name="cost_entries")
        op.drop_index("ix_cost_entries_provider", table_name="cost_entries")
        op.drop_index("ix_cost_entries_tenant_created", table_name="cost_entries")
        op.drop_index("ix_cost_entries_created_at", table_name="cost_entries")
        op.drop_index("ix_cost_entries_request_id", table_name="cost_entries")
        op.drop_index("ix_cost_entries_user_id", table_name="cost_entries")
        op.drop_index("ix_cost_entries_tenant_id", table_name="cost_entries")
        op.drop_table("cost_entries")
