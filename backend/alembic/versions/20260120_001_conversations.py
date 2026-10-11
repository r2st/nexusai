"""Create conversations and messages tables.

Revision ID: 20260120_001
Revises: e196f9b2d0b4
Create Date: 2026-01-20

This migration creates:
- conversations table for chat sessions
- messages table for chat messages
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260120_001"
down_revision = "e196f9b2d0b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create conversations table
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        # Metadata
        sa.Column("title", sa.String(500), server_default="New Conversation"),
        sa.Column("summary", sa.Text(), nullable=True),
        # Model configuration
        sa.Column("model_provider", sa.String(50), server_default="openai"),
        sa.Column("model_name", sa.String(100), server_default="gpt-4o"),
        sa.Column("model_config", postgresql.JSONB(), server_default="{}"),
        sa.Column("system_prompt", sa.Text(), nullable=True),
        # Settings
        sa.Column("settings", postgresql.JSONB(), server_default="{}"),
        # Statistics
        sa.Column("message_count", sa.Integer(), server_default="0"),
        sa.Column("total_tokens", sa.Integer(), server_default="0"),
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

    # Create index for user conversations ordered by update time
    op.create_index(
        "ix_conversations_user_updated",
        "conversations",
        ["user_id", "updated_at"],
    )

    # Create messages table
    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        # Message content
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        # For assistant messages
        sa.Column("model_name", sa.String(100), nullable=True),
        sa.Column("tokens_prompt", sa.Integer(), server_default="0"),
        sa.Column("tokens_completion", sa.Integer(), server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        # Tool calls (if any)
        sa.Column("tool_calls", postgresql.JSONB(), nullable=True),
        sa.Column("tool_call_id", sa.String(100), nullable=True),
        # Metadata
        sa.Column("metadata", postgresql.JSONB(), server_default="{}"),
        # User feedback
        sa.Column("feedback_rating", sa.Integer(), nullable=True),
        sa.Column("feedback_text", sa.Text(), nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # Create index for conversation messages ordered by time
    op.create_index(
        "ix_messages_conversation_created",
        "messages",
        ["conversation_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_messages_conversation_created")
    op.drop_index("ix_conversations_user_updated")
    op.drop_table("messages")
    op.drop_table("conversations")
