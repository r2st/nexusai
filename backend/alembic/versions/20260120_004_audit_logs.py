"""Add audit logs and approval records tables.

Revision ID: 20260120_004
Revises: 20260120_003
Create Date: 2026-01-20

This migration adds:
- audit_logs table for tracking MCP tool invocations and security events
- approval_records table for tracking approval requests for sensitive operations
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "20260120_004"
down_revision = "20260120_003"
branch_labels = None
depends_on = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists."""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # Create audit_logs table OR add missing columns if it was created
    # by the earlier 20240401 migration with fewer columns
    if not table_exists("audit_logs"):
        op.create_table(
            "audit_logs",
            sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
            # Event identification
            sa.Column("event_type", sa.String(50), nullable=False, index=True),
            sa.Column("severity", sa.String(20), nullable=False, server_default="info", index=True),
            # Actor information
            sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=True, index=True),
            sa.Column("organization_id", postgresql.UUID(as_uuid=False), nullable=True, index=True),
            sa.Column("session_id", sa.String(255), nullable=True, index=True),
            sa.Column("ip_address", sa.String(45), nullable=True),
            sa.Column("user_agent", sa.Text(), nullable=True),
            # Tool information
            sa.Column("tool_name", sa.String(255), nullable=True, index=True),
            sa.Column("service_name", sa.String(100), nullable=True, index=True),
            sa.Column("tool_category", sa.String(50), nullable=True),
            # Request/Response
            sa.Column("request_id", sa.String(255), nullable=True, index=True),
            sa.Column("input_params", postgresql.JSONB(), nullable=True),
            sa.Column("output_summary", sa.Text(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("error_code", sa.String(50), nullable=True),
            # Performance
            sa.Column("duration_ms", sa.Float(), nullable=True),
            sa.Column("tokens_used", sa.Integer(), nullable=True),
            # Status
            sa.Column("success", sa.Boolean(), server_default="true", nullable=False),
            sa.Column("was_cached", sa.Boolean(), server_default="false", nullable=False),
            sa.Column("required_approval", sa.Boolean(), server_default="false", nullable=False),
            sa.Column("approval_id", postgresql.UUID(as_uuid=False), nullable=True),
            # Context
            sa.Column("conversation_id", postgresql.UUID(as_uuid=False), nullable=True),
            sa.Column("message_id", postgresql.UUID(as_uuid=False), nullable=True),
            # Additional metadata
            sa.Column("metadata", postgresql.JSONB(), nullable=True),
            sa.Column("tags", postgresql.JSONB(), nullable=True),
            # Timestamps
            sa.Column(
                "timestamp",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )
    else:
        # Table exists from 20240401 migration — add columns it doesn't have
        new_columns = [
            ("organization_id", sa.Column("organization_id", postgresql.UUID(as_uuid=False), nullable=True)),
            ("session_id", sa.Column("session_id", sa.String(255), nullable=True)),
            ("tool_name", sa.Column("tool_name", sa.String(255), nullable=True)),
            ("service_name", sa.Column("service_name", sa.String(100), nullable=True)),
            ("tool_category", sa.Column("tool_category", sa.String(50), nullable=True)),
            ("input_params", sa.Column("input_params", postgresql.JSONB(), nullable=True)),
            ("output_summary", sa.Column("output_summary", sa.Text(), nullable=True)),
            ("error_message", sa.Column("error_message", sa.Text(), nullable=True)),
            ("error_code", sa.Column("error_code", sa.String(50), nullable=True)),
            ("duration_ms", sa.Column("duration_ms", sa.Float(), nullable=True)),
            ("tokens_used", sa.Column("tokens_used", sa.Integer(), nullable=True)),
            ("success", sa.Column("success", sa.Boolean(), server_default="true", nullable=False)),
            ("was_cached", sa.Column("was_cached", sa.Boolean(), server_default="false", nullable=False)),
            ("required_approval", sa.Column("required_approval", sa.Boolean(), server_default="false", nullable=False)),
            ("approval_id", sa.Column("approval_id", postgresql.UUID(as_uuid=False), nullable=True)),
            ("conversation_id", sa.Column("conversation_id", postgresql.UUID(as_uuid=False), nullable=True)),
            ("message_id", sa.Column("message_id", postgresql.UUID(as_uuid=False), nullable=True)),
            ("metadata", sa.Column("metadata", postgresql.JSONB(), nullable=True)),
            ("tags", sa.Column("tags", postgresql.JSONB(), nullable=True)),
            ("timestamp", sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True)),
        ]
        for col_name, col_def in new_columns:
            if not column_exists("audit_logs", col_name):
                op.add_column("audit_logs", col_def)

    # Create composite indexes for common queries (IF NOT EXISTS via execute)
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_user_timestamp ON audit_logs (user_id, timestamp)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_org_timestamp ON audit_logs (organization_id, timestamp)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_tool_timestamp ON audit_logs (tool_name, timestamp)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_service_timestamp ON audit_logs (service_name, timestamp)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_event_severity ON audit_logs (event_type, severity)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_failures ON audit_logs (timestamp, tool_name) WHERE success = false")

    # Create approval_records table
    if not table_exists("approval_records"):
        op.create_table(
            "approval_records",
            sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
            # Request details
            sa.Column("tool_name", sa.String(255), nullable=False, index=True),
            sa.Column("service_name", sa.String(100), nullable=False),
            sa.Column("input_params", postgresql.JSONB(), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            # Requester
            sa.Column("requester_user_id", postgresql.UUID(as_uuid=False), nullable=False, index=True),
            sa.Column("requester_organization_id", postgresql.UUID(as_uuid=False), nullable=True),
            # Approver
            sa.Column("approver_user_id", postgresql.UUID(as_uuid=False), nullable=True),
            sa.Column("approver_comment", sa.Text(), nullable=True),
            # Status
            sa.Column("status", sa.String(20), server_default="pending", nullable=False, index=True),
            # Timing
            sa.Column(
                "requested_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            # Metadata
            sa.Column("metadata", postgresql.JSONB(), nullable=True),
        )

        # Create indexes for approval records
        op.create_index(
            "ix_approval_records_requester_status",
            "approval_records",
            ["requester_user_id", "status"],
        )
        op.create_index(
            "ix_approval_records_pending",
            "approval_records",
            ["status", "expires_at"],
        )


def downgrade() -> None:
    # Drop approval_records table
    if table_exists("approval_records"):
        op.drop_index("ix_approval_records_pending", table_name="approval_records")
        op.drop_index("ix_approval_records_requester_status", table_name="approval_records")
        op.drop_table("approval_records")

    # Drop audit_logs table
    if table_exists("audit_logs"):
        op.drop_index("ix_audit_logs_failures", table_name="audit_logs")
        op.drop_index("ix_audit_logs_event_severity", table_name="audit_logs")
        op.drop_index("ix_audit_logs_service_timestamp", table_name="audit_logs")
        op.drop_index("ix_audit_logs_tool_timestamp", table_name="audit_logs")
        op.drop_index("ix_audit_logs_org_timestamp", table_name="audit_logs")
        op.drop_index("ix_audit_logs_user_timestamp", table_name="audit_logs")
        op.drop_table("audit_logs")
