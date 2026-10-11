"""Add missing columns to organizations and organization_members tables.

Revision ID: 20260120_002
Revises: 20260120_001
Create Date: 2026-01-20

This migration adds:
- tenant_id to organizations table
- Additional subscription/trial fields to organizations
- tenant_id and is_active to organization_members
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "20260120_002"
down_revision = "20260120_001"
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def index_exists(index_name: str) -> bool:
    """Check if an index exists."""
    bind = op.get_bind()
    inspector = inspect(bind)
    # Check all tables for the index
    for table in inspector.get_table_names():
        indexes = inspector.get_indexes(table)
        if any(idx['name'] == index_name for idx in indexes):
            return True
    return False


def upgrade() -> None:
    # Add missing columns to organizations table
    if not column_exists("organizations", "tenant_id"):
        op.add_column(
            "organizations",
            sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=True),
        )
        # Update tenant_id to match id for existing rows
        op.execute("UPDATE organizations SET tenant_id = id WHERE tenant_id IS NULL")
        # Make tenant_id non-nullable after populating
        op.alter_column("organizations", "tenant_id", nullable=False)
    
    # Add tier column
    if not column_exists("organizations", "tier"):
        op.add_column(
            "organizations",
            sa.Column("tier", sa.String(50), server_default="free", nullable=False),
        )
    
    # Add max_members and max_projects
    if not column_exists("organizations", "max_members"):
        op.add_column(
            "organizations",
            sa.Column("max_members", sa.Integer(), server_default="5", nullable=False),
        )
    if not column_exists("organizations", "max_projects"):
        op.add_column(
            "organizations",
            sa.Column("max_projects", sa.Integer(), server_default="3", nullable=False),
        )
    
    # Add trial fields
    if not column_exists("organizations", "trial_status"):
        op.add_column(
            "organizations",
            sa.Column("trial_status", sa.String(50), server_default="none", nullable=False),
        )
    if not column_exists("organizations", "trial_started_at"):
        op.add_column(
            "organizations",
            sa.Column("trial_started_at", sa.DateTime(timezone=True), nullable=True),
        )
    if not column_exists("organizations", "trial_ends_at"):
        op.add_column(
            "organizations",
            sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
        )
    if not column_exists("organizations", "trial_extended_by"):
        op.add_column(
            "organizations",
            sa.Column("trial_extended_by", postgresql.UUID(as_uuid=False), nullable=True),
        )
    if not column_exists("organizations", "trial_extension_reason"):
        op.add_column(
            "organizations",
            sa.Column("trial_extension_reason", sa.Text(), nullable=True),
        )
    
    # Add subscription fields
    if not column_exists("organizations", "subscription_status"):
        op.add_column(
            "organizations",
            sa.Column("subscription_status", sa.String(50), server_default="none", nullable=False),
        )
    if not column_exists("organizations", "subscription_started_at"):
        op.add_column(
            "organizations",
            sa.Column("subscription_started_at", sa.DateTime(timezone=True), nullable=True),
        )
    if not column_exists("organizations", "subscription_ends_at"):
        op.add_column(
            "organizations",
            sa.Column("subscription_ends_at", sa.DateTime(timezone=True), nullable=True),
        )
    if not column_exists("organizations", "subscription_cancel_at_period_end"):
        op.add_column(
            "organizations",
            sa.Column("subscription_cancel_at_period_end", sa.Boolean(), server_default="false", nullable=False),
        )
    
    # Add Stripe fields
    if not column_exists("organizations", "stripe_customer_id"):
        op.add_column(
            "organizations",
            sa.Column("stripe_customer_id", sa.String(255), nullable=True),
        )
    if not column_exists("organizations", "stripe_subscription_id"):
        op.add_column(
            "organizations",
            sa.Column("stripe_subscription_id", sa.String(255), nullable=True),
        )
    
    # Add usage tracking
    if not column_exists("organizations", "current_member_count"):
        op.add_column(
            "organizations",
            sa.Column("current_member_count", sa.Integer(), server_default="0", nullable=False),
        )
    if not column_exists("organizations", "current_project_count"):
        op.add_column(
            "organizations",
            sa.Column("current_project_count", sa.Integer(), server_default="0", nullable=False),
        )
    
    # Add IDP fields
    if not column_exists("organizations", "idp_provider"):
        op.add_column(
            "organizations",
            sa.Column("idp_provider", sa.String(50), nullable=True),
        )
    if not column_exists("organizations", "idp_config"):
        op.add_column(
            "organizations",
            sa.Column("idp_config", postgresql.JSONB(), nullable=True),
        )
    if not column_exists("organizations", "idp_last_sync"):
        op.add_column(
            "organizations",
            sa.Column("idp_last_sync", sa.DateTime(timezone=True), nullable=True),
        )
    
    # Create index on tenant_id if not exists
    if not index_exists("ix_organizations_tenant_id"):
        op.create_index("ix_organizations_tenant_id", "organizations", ["tenant_id"])
    
    # Add missing columns to organization_members table
    if not column_exists("organization_members", "tenant_id"):
        op.add_column(
            "organization_members",
            sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=True),
        )
        # Update tenant_id from organization
        op.execute("""
            UPDATE organization_members om
            SET tenant_id = o.tenant_id
            FROM organizations o
            WHERE om.organization_id = o.id AND om.tenant_id IS NULL
        """)
        op.alter_column("organization_members", "tenant_id", nullable=False)
    
    # Add is_active column with default true
    if not column_exists("organization_members", "is_active"):
        op.add_column(
            "organization_members",
            sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        )
    
    # Create index on tenant_id for organization_members if not exists
    if not index_exists("ix_org_members_tenant_id"):
        op.create_index("ix_org_members_tenant_id", "organization_members", ["tenant_id"])


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_org_members_tenant_id", table_name="organization_members")
    op.drop_index("ix_organizations_tenant_id", table_name="organizations")
    
    # Drop columns from organization_members
    op.drop_column("organization_members", "is_active")
    op.drop_column("organization_members", "tenant_id")
    
    # Drop columns from organizations
    op.drop_column("organizations", "idp_last_sync")
    op.drop_column("organizations", "idp_config")
    op.drop_column("organizations", "idp_provider")
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
    op.drop_column("organizations", "max_projects")
    op.drop_column("organizations", "max_members")
    op.drop_column("organizations", "tier")
    op.drop_column("organizations", "tenant_id")
