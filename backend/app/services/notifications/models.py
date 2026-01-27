"""Data models for Notification service."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class NotificationChannel(str, Enum):
    """Notification delivery channel."""

    SLACK = "slack"
    TEAMS = "teams"
    DISCORD = "discord"
    EMAIL = "email"
    WEBHOOK = "webhook"


class NotificationPriority(str, Enum):
    """Priority level for notifications."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class NotificationType(str, Enum):
    """Type of notification event."""

    # Code Quality
    QUALITY_GATE_PASSED = "quality_gate_passed"
    QUALITY_GATE_FAILED = "quality_gate_failed"
    SECURITY_ISSUE_FOUND = "security_issue_found"
    CRITICAL_ISSUE_FOUND = "critical_issue_found"

    # Analysis
    ANALYSIS_COMPLETE = "analysis_complete"
    PR_REVIEW_COMPLETE = "pr_review_complete"

    # Metrics
    DORA_METRICS_UPDATE = "dora_metrics_update"
    TECH_DEBT_REPORT = "tech_debt_report"
    WEEKLY_SUMMARY = "weekly_summary"

    # System
    SYSTEM_ALERT = "system_alert"
    API_ERROR = "api_error"

    # Custom
    CUSTOM = "custom"


class SlackConfig(BaseModel):
    """Configuration for Slack notifications."""

    webhook_url: str = Field(..., description="Slack incoming webhook URL")
    channel: str | None = Field(None, description="Override channel")
    username: str = Field("NexusAI", description="Bot username")
    icon_emoji: str = Field(":robot_face:", description="Bot icon emoji")
    icon_url: str | None = Field(None, description="Bot icon URL")


class TeamsConfig(BaseModel):
    """Configuration for Microsoft Teams notifications."""

    webhook_url: str = Field(..., description="Teams incoming webhook URL")
    theme_color: str = Field("0076D7", description="Message theme color (hex)")


class DiscordConfig(BaseModel):
    """Configuration for Discord notifications."""

    webhook_url: str = Field(..., description="Discord webhook URL")
    username: str = Field("NexusAI", description="Bot username")
    avatar_url: str | None = Field(None, description="Bot avatar URL")


class EmailConfig(BaseModel):
    """Configuration for email notifications."""

    smtp_host: str = Field(..., description="SMTP server host")
    smtp_port: int = Field(587, description="SMTP server port")
    smtp_user: str | None = Field(None, description="SMTP username")
    smtp_password: str | None = Field(None, description="SMTP password")
    use_tls: bool = Field(True, description="Use TLS encryption")
    from_email: str = Field(..., description="Sender email address")
    from_name: str = Field("NexusAI", description="Sender name")
    reply_to: str | None = Field(None, description="Reply-to address")


class NotificationConfig(BaseModel):
    """Overall notification configuration."""

    enabled: bool = True
    slack: SlackConfig | None = None
    teams: TeamsConfig | None = None
    discord: DiscordConfig | None = None
    email: EmailConfig | None = None

    # Default channels for notification types
    default_channels: dict[NotificationType, list[NotificationChannel]] = Field(
        default_factory=lambda: {
            NotificationType.SECURITY_ISSUE_FOUND: [NotificationChannel.SLACK, NotificationChannel.EMAIL],
            NotificationType.CRITICAL_ISSUE_FOUND: [NotificationChannel.SLACK],
            NotificationType.QUALITY_GATE_FAILED: [NotificationChannel.SLACK],
            NotificationType.WEEKLY_SUMMARY: [NotificationChannel.EMAIL],
        }
    )


class NotificationPreferences(BaseModel):
    """User notification preferences."""

    user_id: str
    enabled: bool = True

    # Per-channel preferences
    channels: dict[NotificationChannel, bool] = Field(
        default_factory=lambda: {
            NotificationChannel.SLACK: True,
            NotificationChannel.EMAIL: True,
        }
    )

    # Per-type preferences
    types: dict[NotificationType, bool] = Field(
        default_factory=lambda: {
            NotificationType.SECURITY_ISSUE_FOUND: True,
            NotificationType.CRITICAL_ISSUE_FOUND: True,
            NotificationType.QUALITY_GATE_FAILED: True,
            NotificationType.WEEKLY_SUMMARY: True,
        }
    )

    # Minimum priority to receive
    min_priority: NotificationPriority = NotificationPriority.MEDIUM

    # Email settings
    email: str | None = None
    email_digest: bool = False  # Group notifications into digest


class NotificationMessage(BaseModel):
    """A notification message to send."""

    type: NotificationType
    priority: NotificationPriority = NotificationPriority.MEDIUM
    title: str
    body: str
    data: dict[str, Any] = Field(default_factory=dict)

    # Targeting
    channels: list[NotificationChannel] | None = None  # Override default channels
    user_ids: list[str] | None = None  # Target specific users
    team_id: str | None = None  # Target entire team

    # Formatting
    color: str | None = None  # Message color (hex)
    icon: str | None = None  # Icon emoji or URL
    footer: str | None = None

    # Actions
    actions: list[dict[str, str]] = Field(default_factory=list)  # Buttons/links

    # Metadata
    source: str = "nexusai"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: str | None = None  # For tracking related notifications


class NotificationResult(BaseModel):
    """Result of sending a notification."""

    success: bool
    channel: NotificationChannel
    message_id: str | None = None
    error: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class NotificationBatchResult(BaseModel):
    """Result of sending notifications to multiple channels."""

    total_channels: int
    successful: int
    failed: int
    results: list[NotificationResult] = Field(default_factory=list)

    @property
    def all_success(self) -> bool:
        return self.failed == 0
