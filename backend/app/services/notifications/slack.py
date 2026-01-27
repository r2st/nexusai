"""Slack notification integration."""

import logging
from typing import Any

import httpx

from app.services.notifications.models import (
    SlackConfig,
    NotificationMessage,
    NotificationResult,
    NotificationChannel,
    NotificationPriority,
    NotificationType,
)

logger = logging.getLogger(__name__)


class SlackNotifier:
    """Send notifications to Slack via incoming webhooks."""

    def __init__(self, config: SlackConfig):
        self.config = config
        self._client = httpx.AsyncClient(timeout=30.0)

    async def send(self, message: NotificationMessage) -> NotificationResult:
        """Send a notification to Slack.

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

            if response.status_code == 200:
                return NotificationResult(
                    success=True,
                    channel=NotificationChannel.SLACK,
                    message_id=None,  # Webhooks don't return message IDs
                )
            else:
                return NotificationResult(
                    success=False,
                    channel=NotificationChannel.SLACK,
                    error=f"Slack API error: {response.status_code} - {response.text}",
                )

        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return NotificationResult(
                success=False,
                channel=NotificationChannel.SLACK,
                error=str(e),
            )

    def _build_payload(self, message: NotificationMessage) -> dict[str, Any]:
        """Build Slack message payload."""
        # Determine color based on priority/type
        color = message.color or self._get_color(message)

        # Build blocks for rich formatting
        blocks = []

        # Header block
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": message.title,
                "emoji": True,
            }
        })

        # Body section
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": message.body,
            }
        })

        # Add data fields if present
        if message.data:
            fields = []
            for key, value in list(message.data.items())[:10]:  # Limit to 10 fields
                fields.append({
                    "type": "mrkdwn",
                    "text": f"*{key}*\n{value}",
                })

            if fields:
                blocks.append({
                    "type": "section",
                    "fields": fields[:10],  # Slack limits to 10 fields
                })

        # Add actions if present
        if message.actions:
            action_elements = []
            for action in message.actions[:5]:  # Limit to 5 actions
                action_elements.append({
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": action.get("text", "Action"),
                        "emoji": True,
                    },
                    "url": action.get("url", "#"),
                    "style": action.get("style", "primary"),
                })

            blocks.append({
                "type": "actions",
                "elements": action_elements,
            })

        # Divider
        blocks.append({"type": "divider"})

        # Context/footer
        context_elements = [
            {
                "type": "mrkdwn",
                "text": f"*Source:* {message.source}",
            },
            {
                "type": "mrkdwn",
                "text": f"*Priority:* {message.priority.value}",
            },
        ]

        if message.footer:
            context_elements.append({
                "type": "mrkdwn",
                "text": message.footer,
            })

        blocks.append({
            "type": "context",
            "elements": context_elements,
        })

        payload: dict[str, Any] = {
            "blocks": blocks,
            "username": self.config.username,
        }

        # Add attachment for color bar
        payload["attachments"] = [{
            "color": color,
            "blocks": [],
        }]

        if self.config.channel:
            payload["channel"] = self.config.channel

        if self.config.icon_emoji:
            payload["icon_emoji"] = self.config.icon_emoji
        elif self.config.icon_url:
            payload["icon_url"] = self.config.icon_url

        return payload

    def _get_color(self, message: NotificationMessage) -> str:
        """Get color based on message type and priority."""
        # Priority-based colors
        if message.priority == NotificationPriority.CRITICAL:
            return "#FF0000"  # Red
        elif message.priority == NotificationPriority.HIGH:
            return "#FFA500"  # Orange

        # Type-based colors
        type_colors = {
            NotificationType.QUALITY_GATE_PASSED: "#36A64F",  # Green
            NotificationType.QUALITY_GATE_FAILED: "#FF0000",  # Red
            NotificationType.SECURITY_ISSUE_FOUND: "#FF0000",  # Red
            NotificationType.CRITICAL_ISSUE_FOUND: "#FF0000",  # Red
            NotificationType.ANALYSIS_COMPLETE: "#36A64F",  # Green
            NotificationType.PR_REVIEW_COMPLETE: "#36A64F",  # Green
            NotificationType.DORA_METRICS_UPDATE: "#0076D7",  # Blue
            NotificationType.TECH_DEBT_REPORT: "#FFA500",  # Orange
            NotificationType.WEEKLY_SUMMARY: "#0076D7",  # Blue
            NotificationType.SYSTEM_ALERT: "#FFA500",  # Orange
        }

        return type_colors.get(message.type, "#0076D7")  # Default blue

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()


async def send_slack_message(
    webhook_url: str,
    message: NotificationMessage,
    **config_overrides,
) -> NotificationResult:
    """Convenience function to send a single Slack message.

    Args:
        webhook_url: Slack webhook URL
        message: Message to send
        **config_overrides: Override default config options

    Returns:
        NotificationResult
    """
    config = SlackConfig(webhook_url=webhook_url, **config_overrides)
    notifier = SlackNotifier(config)

    try:
        return await notifier.send(message)
    finally:
        await notifier.close()
