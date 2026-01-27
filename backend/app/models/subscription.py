"""Subscription and trial event logging models."""

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TrialStatus(str, Enum):
    """Trial status states."""

    NONE = "none"  # Never started a trial
    ACTIVE = "active"  # Trial in progress
    EXPIRED = "expired"  # Trial ended without conversion
    CONVERTED = "converted"  # Trial converted to paid


class SubscriptionStatus(str, Enum):
    """Subscription status states."""

    NONE = "none"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    PAUSED = "paused"


class SubscriptionEventType(str, Enum):
    """Types of subscription events."""

    TRIAL_STARTED = "trial_started"
    TRIAL_EXTENDED = "trial_extended"
    TRIAL_EXPIRED = "trial_expired"
    TRIAL_CONVERTED = "trial_converted"
    SUBSCRIPTION_CREATED = "subscription_created"
    SUBSCRIPTION_UPDATED = "subscription_updated"
    SUBSCRIPTION_CANCELED = "subscription_canceled"
    SUBSCRIPTION_RESUMED = "subscription_resumed"
    TIER_CHANGED = "tier_changed"
    PAYMENT_SUCCEEDED = "payment_succeeded"
    PAYMENT_FAILED = "payment_failed"


class SubscriptionEvent(Base):
    """Audit log for subscription and trial events.

    Tracks all changes to organization trials and subscriptions
    for debugging, analytics, and compliance purposes.
    """

    __tablename__ = "subscription_events"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    organization_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Event details
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    previous_tier: Mapped[str | None] = mapped_column(String(50), nullable=True)
    new_tier: Mapped[str | None] = mapped_column(String(50), nullable=True)
    previous_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    new_status: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Who triggered the event (null for system-triggered events)
    triggered_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
    )

    # Additional event data (e.g., extension reason, payment details)
    event_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index("ix_subscription_events_organization_id", "organization_id"),
        Index("ix_subscription_events_event_type", "event_type"),
        Index("ix_subscription_events_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<SubscriptionEvent {self.event_type} org={self.organization_id}>"
