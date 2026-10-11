"""Project-scoped connections model."""

from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.project import Project


class ConnectionStatus(str, Enum):
    """Connection status."""

    PENDING = "pending"
    TESTING = "testing"
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"


class Connection(Base):
    """Project-scoped connection model.

    Connections are now scoped to projects instead of being global.
    This enables multi-tenant data isolation at the connection level.
    """

    __tablename__ = "connections"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
    )

    # Project scope
    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="CASCADE"),
    )

    # Plugin info
    plugin: Mapped[str] = mapped_column(String(100), nullable=False)  # github, jira, etc.
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Connection details (encrypted via OpenBao)
    endpoint: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Secret reference - points to OpenBao path
    secret_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Rate limiting
    rate_limit: Mapped[int] = mapped_column(Integer, default=0)  # requests per hour
    rate_limit_remaining: Mapped[int] = mapped_column(Integer, default=0)

    # Proxy configuration
    proxy: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(50), default=ConnectionStatus.PENDING.value
    )
    status_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Scopes (repositories, projects, boards configured for this connection)
    scopes: Mapped[dict] = mapped_column(JSONB, default=dict)

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
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="connections",
    )
    scopes_list: Mapped[list["ConnectionScope"]] = relationship(
        "ConnectionScope",
        back_populates="connection",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'testing', 'online', 'offline', 'error')",
            name="ck_connections_status",
        ),
        Index("ix_connections_tenant_id", "tenant_id"),
        Index("ix_connections_project_id", "project_id"),
        Index("ix_connections_plugin", "plugin"),
    )

    def __repr__(self) -> str:
        return f"<Connection {self.plugin}:{self.name}>"

    @property
    def domain_id_prefix(self) -> str:
        """Get the domain ID prefix for this connection's scopes."""
        return f"{self.tenant_id}:{self.plugin}:{self.id}"


class ConnectionScope(Base):
    """Scope within a connection (e.g., repository, project, board).

    Uses 5-segment domain ID format:
    {tenant_id}:{plugin}:{connection_id}:{scope_type}:{scope_id}
    """

    __tablename__ = "connection_scopes"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
    )

    # 5-segment domain ID
    domain_id: Mapped[str] = mapped_column(String(500), unique=True)

    connection_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("connections.id", ondelete="CASCADE"),
    )

    # Scope info
    scope_type: Mapped[str] = mapped_column(String(100), nullable=False)  # repo, project, board
    scope_id: Mapped[str] = mapped_column(String(255), nullable=False)
    scope_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Full path/URL
    full_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Configuration for this scope
    config: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Transformation rules
    transformation_rule_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), nullable=True
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

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
    connection: Mapped["Connection"] = relationship(
        "Connection",
        back_populates="scopes_list",
    )

    __table_args__ = (
        UniqueConstraint("connection_id", "scope_type", "scope_id", name="uq_connection_scope"),
        Index("ix_connection_scopes_tenant_id", "tenant_id"),
        Index("ix_connection_scopes_domain_id", "domain_id"),
    )

    def __repr__(self) -> str:
        return f"<ConnectionScope {self.domain_id}>"
