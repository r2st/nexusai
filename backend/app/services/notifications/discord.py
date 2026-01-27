"""Discord notification integration."""

import logging
from typing import Any

import httpx

from app.services.notifications.models import (
    DiscordConfig,
    NotificationMessage,
    NotificationResult,
    NotificationChannel,
    NotificationPriority,
    NotificationType,
)

logger = logging.getLogger(__name__)


class DiscordNotifier:
    """Send notifications to Discord via webhooks."""

    def __init__(self, config: DiscordConfig):
        self.config = config
        self._client = httpx.AsyncClient(timeout=30.0)

    async def send(self, message: NotificationMessage) -> NotificationResult:
        """Send a notification to Discord.

        Args:
            message: The notification message to send

        Returns:
            NotificationResult indicating success or failure
        """
        try:
            payload = self._build_payload(message)

            response = await self._client.post(
                self.config.webhook_url,
                json=payload,
            )

            if response.status_code in (200, 204):
                return NotificationResult(
                    success=True,
                    channel=NotificationChannel.DISCORD,
                    message_id=None,
                )
            else:
                return NotificationResult(
                    success=False,
                    channel=NotificationChannel.DISCORD,
                    error=f"Discord API error: {response.status_code} - {response.text}",
                )

        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")
            return NotificationResult(
                success=False,
                channel=NotificationChannel.DISCORD,
                error=str(e),
            )

    def _build_payload(self, message: NotificationMessage) -> dict[str, Any]:
        """Build Discord webhook payload with embed."""
        color = self._get_color_int(message)

        # Build embed
        embed: dict[str, Any] = {
            "title": message.title,
            "description": message.body,
            "color": color,
            "timestamp": message.timestamp.isoformat(),
            "footer": {
                "text": f"{message.source} | Priority: {message.priority.value}",
            },
        }

        if message.footer:
            embed["footer"]["text"] = f"{embed['footer']['text']} | {message.footer}"

        # Add fields from data
        if message.data:
            embed["fields"] = [
                {
                    "name": str(k),
                    "value": str(v)[:1024],  # Discord field value limit
                    "inline": True,
                }
                for k, v in list(message.data.items())[:25]  # Discord field limit
            ]

        payload: dict[str, Any] = {
            "embeds": [embed],
        }

        if self.config.username:
            payload["username"] = self.config.username

        if self.config.avatar_url:
            payload["avatar_url"] = self.config.avatar_url

        return payload

    def _get_color_int(self, message: NotificationMessage) -> int:
        """Get color as integer based on message type and priority."""
        if message.color:
            # Convert hex string to int
            return int(message.color.lstrip("#"), 16)

        if message.priority == NotificationPriority.CRITICAL:
            return 0xFF0000  # Red
        elif message.priority == NotificationPriority.HIGH:
            return 0xFFA500  # Orange

        type_colors = {
            NotificationType.QUALITY_GATE_PASSED: 0x36A64F,  # Green
            NotificationType.QUALITY_GATE_FAILED: 0xFF0000,  # Red
            NotificationType.SECURITY_ISSUE_FOUND: 0xFF0000,  # Red
            NotificationType.CRITICAL_ISSUE_FOUND: 0xFF0000,  # Red
            NotificationType.ANALYSIS_COMPLETE: 0x36A64F,  # Green
            NotificationType.DORA_METRICS_UPDATE: 0x0076D7,  # Blue
            NotificationType.WEEKLY_SUMMARY: 0x0076D7,  # Blue
        }

        return type_colors.get(message.type, 0x0076D7)  # Default blue

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()


async def send_discord_message(
    webhook_url: str,
    message: NotificationMessage,
    **config_overrides,
) -> NotificationResult:
    """Convenience function to send a single Discord message.

    Args:
        webhook_url: Discord webhook URL
        message: Message to send
        **config_overrides: Override default config options

    Returns:
        NotificationResult
    """
    config = DiscordConfig(webhook_url=webhook_url, **config_overrides)
    notifier = DiscordNotifier(config)

    try:
        return await notifier.send(message)
    finally:
        await notifier.close()
