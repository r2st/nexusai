"""Organization and multi-tenancy models."""

import math
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import (
    Boolean,
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
from app.models.subscription import TrialStatus, SubscriptionStatus

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.project import Project


class OrganizationTier(str, Enum):
    """Organization subscription tiers."""

    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class MemberRole(str, Enum):
    """Member roles within an organization."""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class Organization(Base):
    """Organization model for multi-tenancy.

    This is the top-level tenant entity that owns all resources.
    """

    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        default=lambda: str(uuid4()),
    )

    # Basic info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Subscription
    tier: Mapped[str] = mapped_column(
        String(50), default=OrganizationTier.FREE.value
    )
    max_members: Mapped[int] = mapped_column(Integer, default=5)
    max_projects: Mapped[int] = mapped_column(Integer, default=3)

    # Settings
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Trial tracking
    trial_status: Mapped[str] = mapped_column(
        String(50), default=TrialStatus.NONE.value
    )
    trial_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    trial_ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    trial_extended_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), nullable=True
    )
    trial_extension_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Subscription tracking
    subscription_status: Mapped[str] = mapped_column(
        String(50), default=SubscriptionStatus.NONE.value
    )
    subscription_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    subscription_ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    subscription_cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean, default=False
    )

    # Stripe integration (for future payment gateway)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Usage tracking (cached counts for quick limit checks)
    current_member_count: Mapped[int] = mapped_column(Integer, default=1)
    current_project_count: Mapped[int] = mapped_column(Integer, default=0)

    # External identity provider sync
    idp_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)  # okta, azure_ad, ldap
    idp_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    idp_last_sync: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

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
    members: Mapped[list["OrganizationMember"]] = relationship(
        "OrganizationMember",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    projects: Mapped[list["Project"]] = relationship(
        "Project",
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_organizations_tenant_id", "tenant_id"),
        Index("ix_organizations_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Organization {self.name}>"

    # Trial and subscription helper properties
    @property
    def is_trial_active(self) -> bool:
        """Check if the organization has an active trial."""
        if self.trial_status != TrialStatus.ACTIVE.value:
            return False
        if self.trial_ends_at is None:
            return False
        return datetime.now(UTC) < self.trial_ends_at

    @property
    def trial_days_remaining(self) -> int:
        """Get the number of days remaining in the trial."""
        if not self.is_trial_active or self.trial_ends_at is None:
            return 0
        remaining = self.trial_ends_at - datetime.now(UTC)
        remaining_seconds = remaining.total_seconds()
        if remaining_seconds <= 0:
            return 0
        return max(1, math.ceil(remaining_seconds / 86400))

    @property
    def has_active_subscription(self) -> bool:
        """Check if the organization has an active paid subscription."""
        return self.subscription_status == SubscriptionStatus.ACTIVE.value

    @property
    def can_access_features(self) -> bool:
        """Check if the organization can access premium features.

        Returns True if org has active trial OR active subscription.
        """
        return self.is_trial_active or self.has_active_subscription

    @property
    def is_at_member_limit(self) -> bool:
        """Check if the organization is at its member limit."""
        return self.current_member_count >= self.max_members

    @property
    def is_at_project_limit(self) -> bool:
        """Check if the organization is at its project limit."""
        return self.current_project_count >= self.max_projects

    @property
    def member_usage_percentage(self) -> float:
        """Get the percentage of member slots used."""
        if self.max_members <= 0:
            return 100.0
        return (self.current_member_count / self.max_members) * 100

    @property
    def project_usage_percentage(self) -> float:
        """Get the percentage of project slots used."""
        if self.max_projects <= 0:
            return 100.0
        return (self.current_project_count / self.max_projects) * 100


class OrganizationMember(Base):
    """Organization membership model."""

    __tablename__ = "organization_members"

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
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
    )

    # Role
    role: Mapped[str] = mapped_column(
        String(50), default=MemberRole.MEMBER.value
    )

    # Team/Department (for org hierarchy)
    team: Mapped[str | None] = mapped_column(String(255), nullable=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Permissions override
    permissions: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    invited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

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
        back_populates="members",
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="organization_memberships",
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_org_member"),
        Index("ix_org_members_tenant_id", "tenant_id"),
        Index("ix_org_members_user_id", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<OrganizationMember org={self.organization_id} user={self.user_id}>"


class OrganizationInvite(Base):
    """Pending organization invitations."""

    __tablename__ = "organization_invites"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        index=True,
    )

    organization_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("organizations.id", ondelete="CASCADE"),
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default=MemberRole.MEMBER.value)
    invited_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"))

    # Token for accepting invite
    token: Mapped[str] = mapped_column(String(255), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # Status
    is_accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index("ix_org_invites_email", "email"),
        Index("ix_org_invites_token", "token"),
    )
