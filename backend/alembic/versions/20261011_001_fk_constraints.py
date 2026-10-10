"""Add foreign key constraints for data integrity.

Revision ID: 20261011_001
Revises: 20261010_001
Create Date: 2026-10-11

Adds FK constraints to tables that reference organizations, users,
conversations, and budgets but were missing database-level enforcement:
- cost_entries: tenant_id -> organizations, user_id -> users
- cost_budgets: tenant_id -> organizations
- cost_alerts: tenant_id -> organizations, budget_id -> cost_budgets
- hallucination_logs: tenant_id -> organizations
- hallucination_metrics: tenant_id -> organizations
"""

from alembic import op

revision = "20261011_001"
down_revision = "20261010_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # cost_entries FK constraints
    op.create_foreign_key(
        "fk_cost_entries_tenant_id_organizations",
        "cost_entries",
        "organizations",
        ["tenant_id"],
        ["tenant_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_cost_entries_user_id_users",
        "cost_entries",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # cost_budgets FK constraints
    op.create_foreign_key(
        "fk_cost_budgets_tenant_id_organizations",
        "cost_budgets",
        "organizations",
        ["tenant_id"],
        ["tenant_id"],
        ondelete="CASCADE",
    )

    # cost_alerts FK constraints
    op.create_foreign_key(
        "fk_cost_alerts_tenant_id_organizations",
        "cost_alerts",
        "organizations",
        ["tenant_id"],
        ["tenant_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_cost_alerts_budget_id_cost_budgets",
        "cost_alerts",
        "cost_budgets",
        ["budget_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # hallucination_logs FK constraints
    op.create_foreign_key(
        "fk_hallucination_logs_tenant_id_organizations",
        "hallucination_logs",
        "organizations",
        ["tenant_id"],
        ["tenant_id"],
        ondelete="CASCADE",
    )

    # hallucination_metrics FK constraints
    op.create_foreign_key(
        "fk_hallucination_metrics_tenant_id_organizations",
        "hallucination_metrics",
        "organizations",
        ["tenant_id"],
        ["tenant_id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_hallucination_metrics_tenant_id_organizations",
        "hallucination_metrics",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_hallucination_logs_tenant_id_organizations",
        "hallucination_logs",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_cost_alerts_budget_id_cost_budgets",
        "cost_alerts",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_cost_alerts_tenant_id_organizations",
        "cost_alerts",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_cost_budgets_tenant_id_organizations",
        "cost_budgets",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_cost_entries_user_id_users",
        "cost_entries",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_cost_entries_tenant_id_organizations",
        "cost_entries",
        type_="foreignkey",
    )
