"""Fix messages table schema to match model.

Revision ID: 20260120_003
Revises: 20260120_002
Create Date: 2026-01-20

This migration fixes the messages table schema:
- Rename tokens_prompt -> prompt_tokens
- Rename tokens_completion -> completion_tokens
- Rename metadata -> message_metadata
- Add total_tokens column
- Add attachments column
- Add parent_id column
- Add position column
- Drop latency_ms, feedback_rating, feedback_text columns
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "20260120_003"
down_revision = "20260120_002"
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
    for table in inspector.get_table_names():
        indexes = inspector.get_indexes(table)
        if any(idx['name'] == index_name for idx in indexes):
            return True
    return False


def upgrade() -> None:
    # Rename columns if they exist with old names
    if column_exists("messages", "tokens_prompt") and not column_exists("messages", "prompt_tokens"):
        op.alter_column("messages", "tokens_prompt", new_column_name="prompt_tokens")
    
    if column_exists("messages", "tokens_completion") and not column_exists("messages", "completion_tokens"):
        op.alter_column("messages", "tokens_completion", new_column_name="completion_tokens")
    
    if column_exists("messages", "metadata") and not column_exists("messages", "message_metadata"):
        op.alter_column("messages", "metadata", new_column_name="message_metadata")
    
    # Add missing columns
    if not column_exists("messages", "prompt_tokens"):
        op.add_column(
            "messages",
            sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        )
    
    if not column_exists("messages", "completion_tokens"):
        op.add_column(
            "messages",
            sa.Column("completion_tokens", sa.Integer(), nullable=True),
        )
    
    if not column_exists("messages", "total_tokens"):
        op.add_column(
            "messages",
            sa.Column("total_tokens", sa.Integer(), nullable=True),
        )
    
    if not column_exists("messages", "attachments"):
        op.add_column(
            "messages",
            sa.Column("attachments", postgresql.JSONB(), nullable=True),
        )
    
    if not column_exists("messages", "message_metadata"):
        op.add_column(
            "messages",
            sa.Column("message_metadata", postgresql.JSONB(), server_default="{}", nullable=False),
        )
    
    if not column_exists("messages", "parent_id"):
        op.add_column(
            "messages",
            sa.Column(
                "parent_id",
                postgresql.UUID(as_uuid=False),
                sa.ForeignKey("messages.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
    
    if not column_exists("messages", "position"):
        op.add_column(
            "messages",
            sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        )
    
    # Preserve dropped column data in message_metadata before removing them
    if column_exists("messages", "latency_ms"):
        op.execute("""
            UPDATE messages
            SET message_metadata = COALESCE(message_metadata, '{}'::jsonb)
                || jsonb_build_object('_migrated_latency_ms', latency_ms)
            WHERE latency_ms IS NOT NULL
              AND EXISTS (SELECT 1 FROM information_schema.columns
                          WHERE table_name='messages' AND column_name='message_metadata')
        """)
        op.drop_column("messages", "latency_ms")

    if column_exists("messages", "feedback_rating"):
        op.execute("""
            UPDATE messages
            SET message_metadata = COALESCE(message_metadata, '{}'::jsonb)
                || jsonb_build_object('_migrated_feedback_rating', feedback_rating)
            WHERE feedback_rating IS NOT NULL
              AND EXISTS (SELECT 1 FROM information_schema.columns
                          WHERE table_name='messages' AND column_name='message_metadata')
        """)
        op.drop_column("messages", "feedback_rating")

    if column_exists("messages", "feedback_text"):
        op.execute("""
            UPDATE messages
            SET message_metadata = COALESCE(message_metadata, '{}'::jsonb)
                || jsonb_build_object('_migrated_feedback_text', feedback_text)
            WHERE feedback_text IS NOT NULL
              AND EXISTS (SELECT 1 FROM information_schema.columns
                          WHERE table_name='messages' AND column_name='message_metadata')
        """)
        op.drop_column("messages", "feedback_text")

    # Drop the old metadata column if it still exists after renaming
    if column_exists("messages", "metadata"):
        op.drop_column("messages", "metadata")
    
    # Update indexes
    if index_exists("ix_messages_conversation_created"):
        op.drop_index("ix_messages_conversation_created", table_name="messages")
    
    if not index_exists("ix_messages_conversation_position"):
        op.create_index(
            "ix_messages_conversation_position",
            "messages",
            ["conversation_id", "position"],
        )
    
    if not index_exists("ix_messages_created_at"):
        op.create_index(
            "ix_messages_created_at",
            "messages",
            ["created_at"],
        )


def downgrade() -> None:
    # Drop new indexes
    if index_exists("ix_messages_created_at"):
        op.drop_index("ix_messages_created_at", table_name="messages")
    
    if index_exists("ix_messages_conversation_position"):
        op.drop_index("ix_messages_conversation_position", table_name="messages")
    
    # Recreate old index
    if not index_exists("ix_messages_conversation_created"):
        op.create_index(
            "ix_messages_conversation_created",
            "messages",
            ["conversation_id", "created_at"],
        )
    
    # Drop new columns
    if column_exists("messages", "position"):
        op.drop_column("messages", "position")
    
    if column_exists("messages", "parent_id"):
        op.drop_column("messages", "parent_id")
    
    if column_exists("messages", "attachments"):
        op.drop_column("messages", "attachments")
    
    if column_exists("messages", "total_tokens"):
        op.drop_column("messages", "total_tokens")
    
    # Add back removed columns
    if not column_exists("messages", "latency_ms"):
        op.add_column(
            "messages",
            sa.Column("latency_ms", sa.Integer(), nullable=True),
        )
    
    if not column_exists("messages", "feedback_rating"):
        op.add_column(
            "messages",
            sa.Column("feedback_rating", sa.Integer(), nullable=True),
        )
    
    if not column_exists("messages", "feedback_text"):
        op.add_column(
            "messages",
            sa.Column("feedback_text", sa.Text(), nullable=True),
        )
    
    # Rename columns back
    if column_exists("messages", "message_metadata"):
        op.alter_column("messages", "message_metadata", new_column_name="metadata")
    
    if column_exists("messages", "completion_tokens"):
        op.alter_column("messages", "completion_tokens", new_column_name="tokens_completion")
    
    if column_exists("messages", "prompt_tokens"):
        op.alter_column("messages", "prompt_tokens", new_column_name="tokens_prompt")
