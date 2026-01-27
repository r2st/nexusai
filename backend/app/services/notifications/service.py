"""Unified Notification service."""

import logging
from typing import Any

from app.services.notifications.models import (
    NotificationChannel,
    NotificationConfig,
    NotificationMessage,
    NotificationResult,
    NotificationBatchResult,
    NotificationPreferences,
    NotificationType,
)
from app.services.notifications.slack import SlackNotifier
from app.services.notifications.teams import TeamsNotifier
from app.services.notifications.discord import DiscordNotifier
from app.services.notifications.email import EmailNotifier

logger = logging.getLogger(__name__)

# Singleton instance
_notification_service: "NotificationService | None" = None


class NotificationService:
    """Unified service for sending notifications across multiple channels.

    Manages notification routing, user preferences, and delivery to
    Slack, Teams, Discord, and Email.
    """

    def __init__(self, config: NotificationConfig):
        self.config = config
        self._notifiers: dict[NotificationChannel, Any] = {}
        self._user_preferences: dict[str, NotificationPreferences] = {}

        # Initialize notifiers based on config
        self._init_notifiers()

    def _init_notifiers(self):
        """Initialize channel notifiers based on configuration."""
        if self.config.slack:
            self._notifiers[NotificationChannel.SLACK] = SlackNotifier(self.config.slack)
            logger.info("Slack notifier initialized")

        if self.config.teams:
            self._notifiers[NotificationChannel.TEAMS] = TeamsNotifier(self.config.teams)
            logger.info("Teams notifier initialized")

        if self.config.discord:
            self._notifiers[NotificationChannel.DISCORD] = DiscordNotifier(self.config.discord)
            logger.info("Discord notifier initialized")

        if self.config.email:
            self._notifiers[NotificationChannel.EMAIL] = EmailNotifier(self.config.email)
            logger.info("Email notifier initialized")

    async def send(
        self,
        message: NotificationMessage,
        user_emails: dict[str, str] | None = None,
    ) -> NotificationBatchResult:
        """Send a notification to all appropriate channels.

        Args:
            message: The notification message to send
            user_emails: Mapping of user_id to email for email notifications

        Returns:
            NotificationBatchResult with results from each channel
        """
        if not self.config.enabled:
            return NotificationBatchResult(
                total_channels=0,
                successful=0,
                failed=0,
                results=[],
            )

        # Determine which channels to use
        channels = message.channels or self._get_default_channels(message.type)

        # Filter channels based on user preferences if targeting specific users
        if message.user_ids:
            channels = self._filter_channels_by_preferences(channels, message)

        results: list[NotificationResult] = []

        for channel in channels:
            notifier = self._notifiers.get(channel)
            if not notifier:
                logger.warning(f"No notifier configured for channel: {channel}")
                continue

            try:
                if channel == NotificationChannel.EMAIL:
                    # Email needs recipients
                    recipients = self._get_email_recipients(message, user_emails)
                    if recipients:
                        result = await notifier.send(message, recipients)
                        results.append(result)
                else:
                    result = await notifier.send(message)
                    results.append(result)

            except Exception as e:
                logger.error(f"Error sending to {channel}: {e}")
                results.append(NotificationResult(
                    success=False,
                    channel=channel,
                    error=str(e),
                ))

        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful

        return NotificationBatchResult(
            total_channels=len(results),
            successful=successful,
            failed=failed,
            results=results,
        )

    async def send_to_channel(
        self,
        channel: NotificationChannel,
        message: NotificationMessage,
        recipients: list[str] | None = None,
    ) -> NotificationResult:
        """Send a notification to a specific channel.

        Args:
            channel: The channel to send to
            message: The notification message
            recipients: Email recipients (only for email channel)

        Returns:
            NotificationResult
        """
        notifier = self._notifiers.get(channel)
        if not notifier:
            return NotificationResult(
                success=False,
                channel=channel,
                error=f"Channel {channel} not configured",
            )

        try:
            if channel == NotificationChannel.EMAIL:
                if not recipients:
                    return NotificationResult(
                        success=False,
                        channel=channel,
                        error="No email recipients provided",
                    )
                return await notifier.send(message, recipients)
            else:
                return await notifier.send(message)

        except Exception as e:
            logger.error(f"Error sending to {channel}: {e}")
            return NotificationResult(
                success=False,
                channel=channel,
                error=str(e),
            )

    def _get_default_channels(
        self,
        notification_type: NotificationType,
    ) -> list[NotificationChannel]:
        """Get default channels for a notification type."""
        defaults = self.config.default_channels.get(notification_type, [])

        # Filter to only configured channels
        return [ch for ch in defaults if ch in self._notifiers]

    def _filter_channels_by_preferences(
        self,
        channels: list[NotificationChannel],
        message: NotificationMessage,
    ) -> list[NotificationChannel]:
        """Filter channels based on user preferences."""
        if not message.user_ids:
            return channels

        # Get union of enabled channels across all target users
        enabled_channels: set[NotificationChannel] = set()

        for user_id in message.user_ids:
            prefs = self._user_preferences.get(user_id)
            if not prefs or not prefs.enabled:
                continue

            # Check notification type preference
            if not prefs.types.get(message.type, True):
                continue

            # Check priority threshold
            priority_order = ["critical", "high", "medium", "low"]
            if priority_order.index(message.priority.value) > priority_order.index(prefs.min_priority.value):
                continue

            # Add enabled channels for this user
            for ch in channels:
                if prefs.channels.get(ch, True):
                    enabled_channels.add(ch)

        return list(enabled_channels) if enabled_channels else channels

    def _get_email_recipients(
        self,
        message: NotificationMessage,
        user_emails: dict[str, str] | None,
    ) -> list[str]:
        """Get email recipients for a message."""
        if not message.user_ids:
            return []

        if not user_emails:
            # Try to get from preferences
            recipients = []
            for user_id in message.user_ids:
                prefs = self._user_preferences.get(user_id)
                if prefs and prefs.email:
                    recipients.append(prefs.email)
            return recipients

        return [
            user_emails[uid]
            for uid in message.user_ids
            if uid in user_emails
        ]

    def set_user_preferences(self, preferences: NotificationPreferences) -> None:
        """Set notification preferences for a user."""
        self._user_preferences[preferences.user_id] = preferences

    def get_user_preferences(self, user_id: str) -> NotificationPreferences | None:
        """Get notification preferences for a user."""
        return self._user_preferences.get(user_id)

    def get_available_channels(self) -> list[NotificationChannel]:
        """Get list of configured and available channels."""
        return list(self._notifiers.keys())

    async def close(self):
        """Close all notifier connections."""
        for notifier in self._notifiers.values():
            if hasattr(notifier, "close"):
                await notifier.close()


def get_notification_service(
    config: NotificationConfig | None = None,
) -> NotificationService:
    """Get or create the notification service singleton."""
    global _notification_service

    if _notification_service is None:
        if config is None:
            config = NotificationConfig()
        _notification_service = NotificationService(config)

    return _notification_service
