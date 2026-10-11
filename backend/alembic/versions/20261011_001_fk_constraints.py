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
- entity_relations: from_entity_id -> entities, to_entity_id -> entities
- pr_issue_correlations: project_id -> projects
- agent_executions: conversation_id -> conversations

Also adds missing FK column indexes for query performance.
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

    # entity_relations FK constraints (from/to entity references)
    op.create_foreign_key(
        "fk_entity_relations_from_entity_id_entities",
        "entity_relations",
        "entities",
        ["from_entity_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_entity_relations_to_entity_id_entities",
        "entity_relations",
        "entities",
        ["to_entity_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # pr_issue_correlations FK constraint (project_id -> projects)
    op.create_foreign_key(
        "fk_pr_issue_correlations_project_id_projects",
        "pr_issue_correlations",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # agent_executions FK constraint (conversation_id -> conversations)
    op.create_foreign_key(
        "fk_agent_executions_conversation_id_conversations",
        "agent_executions",
        "conversations",
        ["conversation_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Missing FK column indexes for query performance
    op.create_index(
        "ix_cost_alerts_budget_id_idx",
        "cost_alerts",
        ["budget_id"],
    )
    op.create_index(
        "ix_ragas_samples_tenant_run",
        "ragas_evaluation_samples",
        ["tenant_id", "run_id"],
    )


def downgrade() -> None:
    # Drop new indexes
    op.drop_index("ix_ragas_samples_tenant_run", table_name="ragas_evaluation_samples")
    op.drop_index("ix_cost_alerts_budget_id_idx", table_name="cost_alerts")

    # Drop new FK constraints
    op.drop_constraint(
        "fk_agent_executions_conversation_id_conversations",
        "agent_executions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_pr_issue_correlations_project_id_projects",
        "pr_issue_correlations",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_entity_relations_to_entity_id_entities",
        "entity_relations",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_entity_relations_from_entity_id_entities",
        "entity_relations",
        type_="foreignkey",
    )

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
