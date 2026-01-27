"""Create entities and identity_mappings tables.

Revision ID: 20260119_002
Revises: 20260119_001
Create Date: 2026-01-19

This migration creates:
- entities table for canonical domain entities
- entity_relations table for entity relationships
- identity_mappings table for cross-source identity resolution
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260119_002"
down_revision = "20260119_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create entities table
    op.create_table(
        "entities",
        # Primary key
        sa.Column("id", sa.String(36), primary_key=True),

        # Tenant isolation
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False),

        # Entity type and source
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("source_id", sa.String(255), nullable=False),
        sa.Column("connection_id", sa.String(36), nullable=True),

        # Domain ID for cross-source identity
        sa.Column("domain_id", sa.String(500), nullable=True),

        # Source timestamps
        sa.Column("source_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),

        # Raw event references
        sa.Column("raw_event_ids", postgresql.ARRAY(sa.String(36)), default=[]),

        # Flexible data storage
        sa.Column("data", postgresql.JSONB(), default=dict),
        sa.Column("metadata", postgresql.JSONB(), default=dict),
        sa.Column("tags", postgresql.ARRAY(sa.String(100)), default=[]),

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
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    # Unique constraint on domain_id within tenant
    op.create_unique_constraint(
        "uq_entities_tenant_domain_id",
        "entities",
        ["tenant_id", "domain_id"],
    )

    # Indexes for entities
    op.create_index("ix_entities_tenant_id", "entities", ["tenant_id"])
    op.create_index("ix_entities_tenant_type", "entities", ["tenant_id", "entity_type"])
    op.create_index("ix_entities_tenant_source", "entities", ["tenant_id", "source"])
    op.create_index("ix_entities_domain_id", "entities", ["domain_id"])
    op.create_index(
        "ix_entities_tenant_source_source_id",
        "entities",
        ["tenant_id", "source", "source_id"],
    )
    op.create_index("ix_entities_updated_at", "entities", ["updated_at"])
    op.create_index(
        "ix_entities_tags",
        "entities",
        ["tags"],
        postgresql_using="gin",
    )

    # Enable RLS for entities
    op.execute("ALTER TABLE entities ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE entities FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_policy ON entities
        FOR ALL
        USING (
            tenant_id = current_setting('app.current_tenant_id', true)::uuid
        )
        WITH CHECK (
            tenant_id = current_setting('app.current_tenant_id', true)::uuid
        )
    """)

    # Create entity_relations table
    op.create_table(
        "entity_relations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False),

        # From entity
        sa.Column("from_entity_id", sa.String(36), nullable=False),
        sa.Column("from_entity_type", sa.String(50), nullable=False),

        # To entity
        sa.Column("to_entity_id", sa.String(36), nullable=False),
        sa.Column("to_entity_type", sa.String(50), nullable=False),

        # Relation
        sa.Column("relation_type", sa.String(50), nullable=False),
        sa.Column("properties", postgresql.JSONB(), default=dict),

        # Validity period
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),

        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # Unique constraint for relations
    op.create_unique_constraint(
        "uq_entity_relations",
        "entity_relations",
        ["tenant_id", "from_entity_id", "to_entity_id", "relation_type"],
    )

    # Indexes for relations
    op.create_index("ix_entity_relations_tenant", "entity_relations", ["tenant_id"])
    op.create_index("ix_entity_relations_from", "entity_relations", ["from_entity_id"])
    op.create_index("ix_entity_relations_to", "entity_relations", ["to_entity_id"])
    op.create_index(
        "ix_entity_relations_type",
        "entity_relations",
        ["relation_type"],
    )

    # RLS for relations
    op.execute("ALTER TABLE entity_relations ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE entity_relations FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_policy ON entity_relations
        FOR ALL
        USING (
            tenant_id = current_setting('app.current_tenant_id', true)::uuid
        )
        WITH CHECK (
            tenant_id = current_setting('app.current_tenant_id', true)::uuid
        )
    """)

    # Create identity_mappings table
    op.create_table(
        "identity_mappings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False),

        # Canonical identity
        sa.Column("canonical_id", sa.String(36), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),

        # Source identity
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("source_id", sa.String(255), nullable=False),
        sa.Column("source_username", sa.String(255), nullable=True),
        sa.Column("source_email", sa.String(255), nullable=True),

        # Confidence
        sa.Column("confidence", sa.Float(), default=1.0),
        sa.Column("verified", sa.Boolean(), default=False),
        sa.Column("verified_by", sa.String(36), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),

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

    # Unique constraint for identity mappings
    op.create_unique_constraint(
        "uq_identity_mappings",
        "identity_mappings",
        ["tenant_id", "source", "source_id", "entity_type"],
    )

    # Indexes for identity mappings
    op.create_index("ix_identity_mappings_tenant", "identity_mappings", ["tenant_id"])
    op.create_index(
        "ix_identity_mappings_canonical",
        "identity_mappings",
        ["tenant_id", "canonical_id"],
    )
    op.create_index(
        "ix_identity_mappings_email",
        "identity_mappings",
        ["tenant_id", "entity_type", "source_email"],
    )
    op.create_index(
        "ix_identity_mappings_username",
        "identity_mappings",
        ["tenant_id", "entity_type", "source_username"],
    )

    # RLS for identity mappings
    op.execute("ALTER TABLE identity_mappings ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE identity_mappings FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_policy ON identity_mappings
        FOR ALL
        USING (
            tenant_id = current_setting('app.current_tenant_id', true)::uuid
        )
        WITH CHECK (
            tenant_id = current_setting('app.current_tenant_id', true)::uuid
        )
    """)


def downgrade() -> None:
    # Drop RLS policies
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON entities")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON entity_relations")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON identity_mappings")

    # Drop tables
    op.drop_table("identity_mappings")
    op.drop_table("entity_relations")
    op.drop_table("entities")
