"""Create events_index table for event ingestion service.

Revision ID: 20260119_001
Revises:
Create Date: 2026-01-19

This migration creates:
- events_index table for fast event queries
- RLS policies for tenant isolation
- Indexes for common query patterns
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260119_001"
down_revision = "20240401_000001"  # Chain from documents/embeddings migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create events_index table
    op.create_table(
        "events_index",
        # Primary key
        sa.Column("id", sa.String(36), primary_key=True),

        # Tenant isolation
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False),

        # Event metadata
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("source_event_type", sa.String(100), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),

        # Source references
        sa.Column("source_id", sa.String(255), nullable=True),
        sa.Column("source_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("connection_id", sa.String(36), nullable=True),

        # Storage
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("schema_version", sa.String(10), default="1.0"),

        # Processing state
        sa.Column("processed", sa.Boolean(), default=False, nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_error", sa.Text(), nullable=True),

        # Timestamps
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
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

    # Create indexes for common query patterns
    op.create_index(
        "ix_events_index_tenant_id",
        "events_index",
        ["tenant_id"],
    )
    op.create_index(
        "ix_events_index_tenant_source",
        "events_index",
        ["tenant_id", "source"],
    )
    op.create_index(
        "ix_events_index_tenant_event_type",
        "events_index",
        ["tenant_id", "event_type"],
    )
    op.create_index(
        "ix_events_index_tenant_received_at",
        "events_index",
        ["tenant_id", "received_at"],
    )
    op.create_index(
        "ix_events_index_tenant_connection",
        "events_index",
        ["tenant_id", "connection_id"],
    )
    op.create_index(
        "ix_events_index_processed",
        "events_index",
        ["processed"],
        postgresql_where=sa.text("processed = false"),
    )
    op.create_index(
        "ix_events_index_source_id",
        "events_index",
        ["source_id"],
    )

    # Enable Row Level Security
    op.execute("ALTER TABLE events_index ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE events_index FORCE ROW LEVEL SECURITY")

    # Create RLS policy for tenant isolation
    op.execute("""
        CREATE POLICY tenant_isolation_policy ON events_index
        FOR ALL
        USING (
            tenant_id = current_setting('app.current_tenant_id', true)::uuid
        )
        WITH CHECK (
            tenant_id = current_setting('app.current_tenant_id', true)::uuid
        )
    """)

    # Note: connections table is already created in 001_initial migration
    # Just add RLS policy if not exists
    op.execute("ALTER TABLE connections ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE connections FORCE ROW LEVEL SECURITY")
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_policies 
                WHERE tablename = 'connections' 
                AND policyname = 'tenant_isolation_policy'
            ) THEN
                CREATE POLICY tenant_isolation_policy ON connections
                FOR ALL
                USING (
                    tenant_id = current_setting('app.current_tenant_id', true)::uuid
                )
                WITH CHECK (
                    tenant_id = current_setting('app.current_tenant_id', true)::uuid
                );
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # Drop RLS policies
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON events_index")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON connections")

    # Disable RLS on connections (but don't drop the table - it's from 001_initial)
    op.execute("ALTER TABLE connections DISABLE ROW LEVEL SECURITY")

    # Drop indexes for events_index
    op.drop_index("ix_events_index_tenant_id")
    op.drop_index("ix_events_index_tenant_source")
    op.drop_index("ix_events_index_tenant_event_type")
    op.drop_index("ix_events_index_tenant_received_at")
    op.drop_index("ix_events_index_tenant_connection")
    op.drop_index("ix_events_index_processed")
    op.drop_index("ix_events_index_source_id")

    # Drop events_index table only (connections is from 001_initial)
    op.drop_table("events_index")
