"""Project model for multi-tenant project isolation."""

from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User
    from app.models.connection import Connection


class ProjectRole(str, Enum):
    """Project-level roles."""

    ADMIN = "admin"
    MAINTAINER = "maintainer"
    DEVELOPER = "developer"
    VIEWER = "viewer"


class Project(Base):
    """Project model for isolating data within an organization.

    Projects group connections, blueprints, and analytics data.
    Each project has its own set of DORA metrics and dashboards.
    """

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
    )

    organization_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("organizations.id", ondelete="CASCADE"),
    )

    # Basic info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key: Mapped[str] = mapped_column(String(50), nullable=False)  # Short key like "PROJ"
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Settings
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)

    # DORA configuration
    dora_config: Mapped[dict] = mapped_column(JSONB, default=lambda: {
        "deployment_detection": "branch",  # branch, tag, or deployment
        "deployment_branch": "main",
        "incident_detection": "label",  # label or linked
        "incident_label": "incident",
    })

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)

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
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="projects",
    )
    members: Mapped[list["ProjectMember"]] = relationship(
        "ProjectMember",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    connections: Mapped[list["Connection"]] = relationship(
        "Connection",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    blueprints = relationship(
        "Blueprint",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "key", name="uq_project_org_key"),
        Index("ix_projects_tenant_id", "tenant_id"),
        Index("ix_projects_org_id", "organization_id"),
    )

    def __repr__(self) -> str:
        return f"<Project {self.key}: {self.name}>"


class ProjectMember(Base):
    """Project membership model for fine-grained access control."""

    __tablename__ = "project_members"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
    )

    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="CASCADE"),
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
    )

    # Role
    role: Mapped[str] = mapped_column(
        String(50), default=ProjectRole.DEVELOPER.value
    )

    # Permissions
    permissions: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

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
        back_populates="members",
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="project_memberships",
    )

    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_member"),
        Index("ix_project_members_tenant_id", "tenant_id"),
        Index("ix_project_members_user_id", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<ProjectMember project={self.project_id} user={self.user_id}>"
