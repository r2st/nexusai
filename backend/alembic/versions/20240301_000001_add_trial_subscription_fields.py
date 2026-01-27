"""Add trial and subscription fields to organizations.

Revision ID: 20240301_000001
Revises: 20240201_000001
Create Date: 2024-03-01 00:00:01.000000

This migration adds:
- Trial tracking fields to organizations table
- Subscription tracking fields to organizations table
- Stripe integration fields (nullable, for future use)
- Usage tracking fields
- subscription_events audit table
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20240301_000001"
down_revision = "20240201_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add trial tracking fields to organizations table
    op.add_column(
        "organizations",
        sa.Column(
            "trial_status",
            sa.String(50),
            nullable=False,
            server_default="none",
        ),
    )
    op.add_column(
        "organizations",
        sa.Column("trial_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column(
            "trial_extended_by",
            postgresql.UUID(as_uuid=False),
            nullable=True,
        ),
    )
    op.add_column(
        "organizations",
        sa.Column("trial_extension_reason", sa.Text, nullable=True),
    )

    # Add subscription tracking fields
    op.add_column(
        "organizations",
        sa.Column(
            "subscription_status",
            sa.String(50),
            nullable=False,
            server_default="none",
        ),
    )
    op.add_column(
        "organizations",
        sa.Column("subscription_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("subscription_ends_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column(
            "subscription_cancel_at_period_end",
            sa.Boolean,
            nullable=False,
            server_default="false",
        ),
    )

    # Add Stripe integration fields (nullable, for Phase 2)
    op.add_column(
        "organizations",
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("stripe_subscription_id", sa.String(255), nullable=True),
    )

    # Add usage tracking fields
    op.add_column(
        "organizations",
        sa.Column(
            "current_member_count",
            sa.Integer,
            nullable=False,
            server_default="1",
        ),
    )
    op.add_column(
        "organizations",
        sa.Column(
            "current_project_count",
            sa.Integer,
            nullable=False,
            server_default="0",
        ),
    )

    # Add tier column for subscription tier
    op.add_column(
        "organizations",
        sa.Column(
            "tier",
            sa.String(50),
            nullable=False,
            server_default="free",
        ),
    )

    # Create indexes for common queries
    op.create_index(
        "ix_organizations_trial_status",
        "organizations",
        ["trial_status"],
    )
    op.create_index(
        "ix_organizations_trial_ends_at",
        "organizations",
        ["trial_ends_at"],
    )
    op.create_index(
        "ix_organizations_subscription_status",
        "organizations",
        ["subscription_status"],
    )
    op.create_index(
        "ix_organizations_tier",
        "organizations",
        ["tier"],
    )

    # Create subscription_events table for audit logging
    op.create_table(
        "subscription_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("previous_tier", sa.String(50), nullable=True),
        sa.Column("new_tier", sa.String(50), nullable=True),
        sa.Column("previous_status", sa.String(50), nullable=True),
        sa.Column("new_status", sa.String(50), nullable=True),
        sa.Column(
            "triggered_by",
            postgresql.UUID(as_uuid=False),
            nullable=True,
        ),
        sa.Column(
            "event_metadata",
            postgresql.JSONB,
            nullable=True,
            server_default="{}",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
        ),
    )

    op.create_index(
        "ix_subscription_events_organization_id",
        "subscription_events",
        ["organization_id"],
    )
    op.create_index(
        "ix_subscription_events_event_type",
        "subscription_events",
        ["event_type"],
    )
    op.create_index(
        "ix_subscription_events_created_at",
        "subscription_events",
        ["created_at"],
    )


def downgrade() -> None:
    # Drop subscription_events table
    op.drop_index("ix_subscription_events_created_at")
    op.drop_index("ix_subscription_events_event_type")
    op.drop_index("ix_subscription_events_organization_id")
    op.drop_table("subscription_events")

    # Drop indexes on organizations
    op.drop_index("ix_organizations_tier")
    op.drop_index("ix_organizations_subscription_status")
    op.drop_index("ix_organizations_trial_ends_at")
    op.drop_index("ix_organizations_trial_status")

    # Drop columns from organizations
    op.drop_column("organizations", "tier")
    op.drop_column("organizations", "current_project_count")
    op.drop_column("organizations", "current_member_count")
    op.drop_column("organizations", "stripe_subscription_id")
    op.drop_column("organizations", "stripe_customer_id")
    op.drop_column("organizations", "subscription_cancel_at_period_end")
    op.drop_column("organizations", "subscription_ends_at")
    op.drop_column("organizations", "subscription_started_at")
    op.drop_column("organizations", "subscription_status")
    op.drop_column("organizations", "trial_extension_reason")
    op.drop_column("organizations", "trial_extended_by")
    op.drop_column("organizations", "trial_ends_at")
    op.drop_column("organizations", "trial_started_at")
    op.drop_column("organizations", "trial_status")
