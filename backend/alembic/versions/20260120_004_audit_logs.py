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


def upgrade() -> None:
    # Create audit_logs table
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

        # Create composite indexes for common queries
        op.create_index(
            "ix_audit_logs_user_timestamp",
            "audit_logs",
            ["user_id", "timestamp"],
        )
        op.create_index(
            "ix_audit_logs_org_timestamp",
            "audit_logs",
            ["organization_id", "timestamp"],
        )
        op.create_index(
            "ix_audit_logs_tool_timestamp",
            "audit_logs",
            ["tool_name", "timestamp"],
        )
        op.create_index(
            "ix_audit_logs_service_timestamp",
            "audit_logs",
            ["service_name", "timestamp"],
        )
        op.create_index(
            "ix_audit_logs_event_severity",
            "audit_logs",
            ["event_type", "severity"],
        )
        # Partial index for failures only
        op.create_index(
            "ix_audit_logs_failures",
            "audit_logs",
            ["timestamp", "tool_name"],
            postgresql_where=sa.text("success = false"),
        )

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
