"""Add performance indexes for hot query paths.

Revision ID: 20261010_001
Revises: 20260203_001
Create Date: 2026-10-10

Adds indexes for:
- messages: conversation_id + created_at (sorted message fetch)
- organization_members: organization_id (member lookups)
- hallucination_logs: conversation_id (log queries)
- cost_entries: user_id + created_at (user cost history)
"""

from alembic import op

revision = "20261010_001"
down_revision = "20260203_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_messages_conversation_created",
        "messages",
        ["conversation_id", "created_at"],
    )
    op.create_index(
        "ix_org_members_organization_id",
        "organization_members",
        ["organization_id"],
    )
    op.create_index(
        "ix_cost_entries_user_created",
        "cost_entries",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_cost_entries_user_created", table_name="cost_entries")
    op.drop_index("ix_org_members_organization_id", table_name="organization_members")
    op.drop_index("ix_messages_conversation_created", table_name="messages")
