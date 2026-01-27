"""Microsoft Teams notification integration."""

import logging
from typing import Any

import httpx

from app.services.notifications.models import (
    TeamsConfig,
    NotificationMessage,
    NotificationResult,
    NotificationChannel,
    NotificationPriority,
    NotificationType,
)

logger = logging.getLogger(__name__)


class TeamsNotifier:
    """Send notifications to Microsoft Teams via incoming webhooks."""

    def __init__(self, config: TeamsConfig):
        self.config = config
        self._client = httpx.AsyncClient(timeout=30.0)

    async def send(self, message: NotificationMessage) -> NotificationResult:
        """Send a notification to Microsoft Teams.

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

            # Teams returns "1" on success
            if response.status_code == 200:
                return NotificationResult(
                    success=True,
                    channel=NotificationChannel.TEAMS,
                    message_id=None,
                )
            else:
                return NotificationResult(
                    success=False,
                    channel=NotificationChannel.TEAMS,
                    error=f"Teams API error: {response.status_code} - {response.text}",
                )

        except Exception as e:
            logger.error(f"Failed to send Teams notification: {e}")
            return NotificationResult(
                success=False,
                channel=NotificationChannel.TEAMS,
                error=str(e),
            )

    def _build_payload(self, message: NotificationMessage) -> dict[str, Any]:
        """Build Microsoft Teams Adaptive Card payload."""
        color = message.color or self._get_color(message)

        # Build Adaptive Card
        card = {
            "type": "AdaptiveCard",
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "text": message.title,
                    "weight": "Bolder",
                    "size": "Large",
                    "wrap": True,
                },
                {
                    "type": "TextBlock",
                    "text": message.body,
                    "wrap": True,
                },
            ],
        }

        # Add facts/data if present
        if message.data:
            facts = [
                {"title": str(k), "value": str(v)}
                for k, v in list(message.data.items())[:10]
            ]
            card["body"].append({
                "type": "FactSet",
                "facts": facts,
            })

        # Add separator and metadata
        card["body"].extend([
            {
                "type": "TextBlock",
                "text": f"Source: {message.source} | Priority: {message.priority.value}",
                "isSubtle": True,
                "size": "Small",
                "wrap": True,
            },
        ])

        if message.footer:
            card["body"].append({
                "type": "TextBlock",
                "text": message.footer,
                "isSubtle": True,
                "size": "Small",
                "wrap": True,
            })

        # Add actions if present
        if message.actions:
            card["actions"] = [
                {
                    "type": "Action.OpenUrl",
                    "title": action.get("text", "Action"),
                    "url": action.get("url", "#"),
                }
                for action in message.actions[:5]
            ]

        # Build the message card wrapper
        payload = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "contentUrl": None,
                    "content": card,
                }
            ],
        }

        return payload

    def _get_color(self, message: NotificationMessage) -> str:
        """Get color based on message type and priority."""
        if message.priority == NotificationPriority.CRITICAL:
            return "FF0000"
        elif message.priority == NotificationPriority.HIGH:
            return "FFA500"

        type_colors = {
            NotificationType.QUALITY_GATE_PASSED: "36A64F",
            NotificationType.QUALITY_GATE_FAILED: "FF0000",
            NotificationType.SECURITY_ISSUE_FOUND: "FF0000",
            NotificationType.CRITICAL_ISSUE_FOUND: "FF0000",
            NotificationType.ANALYSIS_COMPLETE: "36A64F",
            NotificationType.DORA_METRICS_UPDATE: "0076D7",
            NotificationType.WEEKLY_SUMMARY: "0076D7",
        }

        return type_colors.get(message.type, self.config.theme_color)

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()


async def send_teams_message(
    webhook_url: str,
    message: NotificationMessage,
    **config_overrides,
) -> NotificationResult:
    """Convenience function to send a single Teams message.

    Args:
        webhook_url: Teams webhook URL
        message: Message to send
        **config_overrides: Override default config options

    Returns:
        NotificationResult
    """
    config = TeamsConfig(webhook_url=webhook_url, **config_overrides)
    notifier = TeamsNotifier(config)

    try:
        return await notifier.send(message)
    finally:
        await notifier.close()
