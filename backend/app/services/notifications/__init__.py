"""Notification service for Slack, Teams, Discord, and Email integrations."""

from app.services.notifications.models import (
    NotificationChannel,
    NotificationPriority,
    NotificationType,
    NotificationConfig,
    NotificationPreferences,
    NotificationMessage,
    NotificationResult,
    SlackConfig,
    TeamsConfig,
    DiscordConfig,
    EmailConfig,
)
from app.services.notifications.service import (
    NotificationService,
    get_notification_service,
)
from app.services.notifications.slack import SlackNotifier
from app.services.notifications.teams import TeamsNotifier
from app.services.notifications.discord import DiscordNotifier
from app.services.notifications.email import EmailNotifier

__all__ = [
    # Models
    "NotificationChannel",
    "NotificationPriority",
    "NotificationType",
    "NotificationConfig",
    "NotificationPreferences",
    "NotificationMessage",
    "NotificationResult",
    "SlackConfig",
    "TeamsConfig",
    "DiscordConfig",
    "EmailConfig",
    # Service
    "NotificationService",
    "get_notification_service",
    # Notifiers
    "SlackNotifier",
    "TeamsNotifier",
    "DiscordNotifier",
    "EmailNotifier",
]
