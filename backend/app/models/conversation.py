"""Conversation and Message models for chat functionality."""

from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.config import settings


def _get_default_provider() -> str:
    """Get default AI provider from settings."""
    return settings.DEFAULT_AI_PROVIDER


def _get_default_model() -> str:
    """Get default model name from settings based on default provider."""
    provider = settings.DEFAULT_AI_PROVIDER.lower()
    if provider == "google":
        return settings.GOOGLE_DEFAULT_MODEL
    elif provider == "anthropic":
        return settings.ANTHROPIC_DEFAULT_MODEL
    elif provider == "openai":
        return settings.OPENAI_DEFAULT_MODEL
    return settings.GOOGLE_DEFAULT_MODEL

if TYPE_CHECKING:
    from app.models.user import User


class MessageRole(str, Enum):
    """Message roles in a conversation."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ModelProvider(str, Enum):
    """AI model providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"


class Conversation(Base):
    """Conversation model for chat sessions."""

    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    # Metadata
    title: Mapped[str] = mapped_column(String(500), default="New Conversation")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Model configuration
    model_provider: Mapped[str] = mapped_column(
        String(50),
        default=_get_default_provider,
    )
    model_name: Mapped[str] = mapped_column(String(100), default=_get_default_model)
    model_config: Mapped[dict] = mapped_column(JSONB, default=dict)

    # System prompt
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Settings
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Statistics
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

    __table_args__ = (
        Index("ix_conversations_user_updated", "user_id", "updated_at"),
    )

    def __repr__(self) -> str:
        return f"<Conversation {self.id}: {self.title[:30]}>"


class Message(Base):
    """Message model for chat messages."""

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    conversation_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
    )

    # Message content
    role: Mapped[str] = mapped_column(String(50))
    content: Mapped[str] = mapped_column(Text)

    # For assistant messages
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Token usage
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Tool calls (for function calling)
    tool_calls: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    tool_call_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Attachments (files, images)
    attachments: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Message metadata (renamed from 'metadata' which is reserved in SQLAlchemy)
    message_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Parent message (for branching/editing)
    parent_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Position in conversation
    position: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="messages",
    )
    parent: Mapped["Message | None"] = relationship(
        "Message",
        remote_side=[id],
        backref="children",
    )

    __table_args__ = (
        Index("ix_messages_conversation_position", "conversation_id", "position"),
        Index("ix_messages_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Message {self.id}: {self.role}>"
