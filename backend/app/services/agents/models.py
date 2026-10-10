"""Agent data models."""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AgentCapability(str, Enum):
    """Agent capabilities."""

    CODE_EXECUTION = "code_execution"
    FILE_SEARCH = "file_search"
    WEB_SEARCH = "web_search"
    IMAGE_GENERATION = "image_generation"
    IMAGE_VISION = "image_vision"
    SPEECH_TO_TEXT = "speech_to_text"
    TEXT_TO_SPEECH = "text_to_speech"
    FUNCTION_CALLING = "function_calling"
    MCP_SERVER = "mcp_server"
    RETRIEVAL = "retrieval"
    ACTIONS = "actions"


class AgentStatus(str, Enum):
    """Agent status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"
    ARCHIVED = "archived"


class Agent(Base):
    """Agent model for custom AI assistants."""

    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Ownership
    creator_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    organization_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Basic info
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default=AgentStatus.DRAFT.value)

    # Configuration
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_provider: Mapped[str] = mapped_column(String(50), default="openai")
    model_name: Mapped[str] = mapped_column(String(100), default="gpt-4o")
    model_config: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Capabilities
    capabilities: Mapped[list] = mapped_column(ARRAY(String), default=list)

    # Tools and MCP
    tools_config: Mapped[dict] = mapped_column(JSONB, default=dict)
    mcp_servers: Mapped[list] = mapped_column(JSONB, default=list)
    actions_config: Mapped[list] = mapped_column(JSONB, default=list)

    # Sharing
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    shared_with_users: Mapped[list] = mapped_column(ARRAY(UUID(as_uuid=False)), default=list)
    shared_with_groups: Mapped[list] = mapped_column(ARRAY(UUID(as_uuid=False)), default=list)

    # Marketplace
    is_marketplace_listed: Mapped[bool] = mapped_column(Boolean, default=False)
    marketplace_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    rating: Mapped[float | None] = mapped_column(default=None)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)

    # Extra data (note: 'metadata' is reserved by SQLAlchemy)
    agent_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    tags: Mapped[list] = mapped_column(ARRAY(String), default=list)

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
    tools: Mapped[list["AgentTool"]] = relationship(
        "AgentTool",
        back_populates="agent",
        cascade="all, delete-orphan",
    )
    executions: Mapped[list["AgentExecution"]] = relationship(
        "AgentExecution",
        back_populates="agent",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Agent {self.id}: {self.name}>"


class AgentTool(Base):
    """Custom tool for an agent."""

    __tablename__ = "agent_tools"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    agent_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("agents.id", ondelete="CASCADE"),
        index=True,
    )

    # Tool definition
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tool_type: Mapped[str] = mapped_column(String(50))  # function, mcp, action

    # Configuration
    schema_definition: Mapped[dict] = mapped_column(JSONB, default=dict)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Status
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    # Relationships
    agent: Mapped["Agent"] = relationship("Agent", back_populates="tools")

    def __repr__(self) -> str:
        return f"<AgentTool {self.id}: {self.name}>"


class ExecutionStatus(str, Enum):
    """Execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentExecution(Base):
    """Agent execution record."""

    __tablename__ = "agent_executions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    agent_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("agents.id", ondelete="CASCADE"),
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    conversation_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Execution details
    status: Mapped[str] = mapped_column(String(50), default=ExecutionStatus.PENDING.value)
    input_message: Mapped[str] = mapped_column(Text)
    output_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Tool calls
    tool_calls: Mapped[list] = mapped_column(JSONB, default=list)
    tool_results: Mapped[list] = mapped_column(JSONB, default=list)

    # Handoff
    handoff_to_agent_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
    )
    handoff_context: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Metrics
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    execution_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Error handling
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    # Relationships
    agent: Mapped["Agent"] = relationship("Agent", back_populates="executions")

    def __repr__(self) -> str:
        return f"<AgentExecution {self.id}: {self.status}>"


# Pydantic models for API
class AgentCreate(BaseModel):
    """Schema for creating an agent."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    system_prompt: str | None = None
    model_provider: str = "openai"
    model_name: str = "gpt-4o"
    capabilities: list[AgentCapability] = []
    tools_config: dict[str, Any] = {}
    mcp_servers: list[dict[str, Any]] = []
    is_public: bool = False
    tags: list[str] = []


class AgentUpdate(BaseModel):
    """Schema for updating an agent."""

    name: str | None = None
    description: str | None = None
    system_prompt: str | None = None
    model_provider: str | None = None
    model_name: str | None = None
    capabilities: list[AgentCapability] | None = None
    tools_config: dict[str, Any] | None = None
    mcp_servers: list[dict[str, Any]] | None = None
    is_public: bool | None = None
    status: AgentStatus | None = None
    tags: list[str] | None = None


class AgentResponse(BaseModel):
    """Schema for agent response."""

    id: str
    name: str
    description: str | None
    avatar_url: str | None
    status: str
    system_prompt: str | None
    model_provider: str
    model_name: str
    capabilities: list[str]
    is_public: bool
    is_marketplace_listed: bool
    usage_count: int
    rating: float | None
    rating_count: int
    tags: list[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
