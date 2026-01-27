"""Unified Chatbot Service."""

from typing import Any

from app.services.chatbot.models import (
    ChatPlatform,
    BotCommand,
    BotUser,
    DEFAULT_COMMANDS,
)
from app.services.chatbot.slack import SlackBot, get_slack_bot
from app.services.chatbot.teams import TeamsBot, get_teams_bot


class ChatbotService:
    """
    Unified service for Slack/Teams chatbot integration.

    Provides a common interface for both platforms.
    """

    def __init__(self):
        self._slack = get_slack_bot()
        self._teams = get_teams_bot()

        # Platform configurations
        self._platform_configs: dict[str, dict[str, Any]] = {}

        # User mappings (platform_user -> nexus_user)
        self._user_mappings: dict[str, str] = {}

    # Configuration

    def configure_slack(
        self,
        bot_token: str,
        signing_secret: str,
        app_id: str | None = None,
    ) -> None:
        """Configure Slack bot."""
        self._slack._bot_token = bot_token
        self._slack._signing_secret = signing_secret
        self._slack._app_id = app_id

        self._platform_configs["slack"] = {
            "configured": True,
            "app_id": app_id,
        }

    def configure_teams(
        self,
        app_id: str,
        app_password: str,
        tenant_id: str | None = None,
    ) -> None:
        """Configure Teams bot."""
        self._teams._app_id = app_id
        self._teams._app_password = app_password
        self._teams._tenant_id = tenant_id

        self._platform_configs["teams"] = {
            "configured": True,
            "app_id": app_id,
        }

    # Slack Handlers

    async def handle_slack_event(
        self,
        event_data: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Handle incoming Slack event."""
        return await self._slack.handle_event(event_data)

    async def handle_slack_command(
        self,
        command_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle Slack slash command."""
        return await self._slack.handle_slash_command(command_data)

    async def handle_slack_interaction(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Handle Slack interactive component."""
        return await self._slack.handle_interaction(payload)

    def verify_slack_signature(
        self,
        timestamp: str,
        signature: str,
        body: bytes,
    ) -> bool:
        """Verify Slack request signature."""
        return self._slack.verify_signature(timestamp, signature, body)

    # Teams Handlers

    async def handle_teams_activity(
        self,
        activity: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Handle incoming Teams activity."""
        return await self._teams.handle_activity(activity)

    # User Linking

    async def link_user(
        self,
        platform: ChatPlatform,
        platform_user_id: str,
        nexus_user_id: str,
        organization_id: str,
    ) -> bool:
        """Link a platform user to a NexusAI user."""
        user_key = f"{platform.value}:{platform_user_id}"
        self._user_mappings[user_key] = nexus_user_id

        # Update user in platform-specific storage
        if platform == ChatPlatform.SLACK:
            for user in self._slack._users.values():
                if user.platform_user_id == platform_user_id:
                    user.nexus_user_id = nexus_user_id
                    user.organization_id = organization_id
                    return True
        elif platform == ChatPlatform.TEAMS:
            for user in self._teams._users.values():
                if user.platform_user_id == platform_user_id:
                    user.nexus_user_id = nexus_user_id
                    user.organization_id = organization_id
                    return True

        return False

    async def unlink_user(
        self,
        platform: ChatPlatform,
        platform_user_id: str,
    ) -> bool:
        """Unlink a platform user from NexusAI."""
        user_key = f"{platform.value}:{platform_user_id}"

        if user_key in self._user_mappings:
            del self._user_mappings[user_key]

        if platform == ChatPlatform.SLACK:
            for user in self._slack._users.values():
                if user.platform_user_id == platform_user_id:
                    user.nexus_user_id = None
                    user.organization_id = None
                    return True
        elif platform == ChatPlatform.TEAMS:
            for user in self._teams._users.values():
                if user.platform_user_id == platform_user_id:
                    user.nexus_user_id = None
                    user.organization_id = None
                    return True

        return False

    async def get_linked_user(
        self,
        platform: ChatPlatform,
        platform_user_id: str,
    ) -> BotUser | None:
        """Get linked user info."""
        if platform == ChatPlatform.SLACK:
            for user in self._slack._users.values():
                if user.platform_user_id == platform_user_id:
                    return user
        elif platform == ChatPlatform.TEAMS:
            for user in self._teams._users.values():
                if user.platform_user_id == platform_user_id:
                    return user

        return None

    # Notifications

    async def send_notification(
        self,
        platform: ChatPlatform,
        channel_ids: list[str],
        event_type: str,
        title: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[str]:
        """Send notification to subscribed channels."""
        if platform == ChatPlatform.SLACK:
            return await self._slack.send_notification(
                channel_ids, event_type, title, message, metadata
            )
        elif platform == ChatPlatform.TEAMS:
            return await self._teams.send_notification(
                channel_ids, event_type, title, message, metadata
            )

        return []

    async def broadcast_notification(
        self,
        event_type: str,
        title: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, list[str]]:
        """Broadcast notification to all platforms."""
        results = {}

        # Get all subscribed channels
        slack_channels = list(self._slack._subscriptions.keys())
        teams_channels = list(self._teams._subscriptions.keys())

        if slack_channels:
            results["slack"] = await self._slack.send_notification(
                slack_channels, event_type, title, message, metadata
            )

        if teams_channels:
            results["teams"] = await self._teams.send_notification(
                teams_channels, event_type, title, message, metadata
            )

        return results

    # Direct Messages

    async def send_slack_message(
        self,
        channel_id: str,
        text: str,
        blocks: list[dict[str, Any]] | None = None,
        thread_ts: str | None = None,
    ) -> dict[str, Any] | None:
        """Send a message to Slack."""
        return await self._slack.send_message(channel_id, text, blocks, thread_ts)

    async def send_teams_message(
        self,
        conversation_id: str,
        text: str | None = None,
        card: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Send a message to Teams."""
        return await self._teams.send_message(conversation_id, text, card)

    # Commands

    def get_commands(self) -> list[BotCommand]:
        """Get all registered commands."""
        return DEFAULT_COMMANDS

    def get_platform_commands(
        self,
        platform: ChatPlatform,
    ) -> list[BotCommand]:
        """Get commands for a specific platform."""
        return [
            cmd for cmd in DEFAULT_COMMANDS
            if platform in cmd.platforms
        ]

    # Subscriptions

    async def subscribe_channel(
        self,
        platform: ChatPlatform,
        channel_id: str,
        event_types: list[str],
    ) -> bool:
        """Subscribe a channel to event types."""
        if platform == ChatPlatform.SLACK:
            if channel_id not in self._slack._subscriptions:
                self._slack._subscriptions[channel_id] = []
            for event_type in event_types:
                if event_type not in self._slack._subscriptions[channel_id]:
                    self._slack._subscriptions[channel_id].append(event_type)
            return True
        elif platform == ChatPlatform.TEAMS:
            if channel_id not in self._teams._subscriptions:
                self._teams._subscriptions[channel_id] = []
            for event_type in event_types:
                if event_type not in self._teams._subscriptions[channel_id]:
                    self._teams._subscriptions[channel_id].append(event_type)
            return True

        return False

    async def unsubscribe_channel(
        self,
        platform: ChatPlatform,
        channel_id: str,
        event_types: list[str] | None = None,
    ) -> bool:
        """Unsubscribe a channel from event types."""
        if platform == ChatPlatform.SLACK:
            if channel_id in self._slack._subscriptions:
                if event_types:
                    for event_type in event_types:
                        if event_type in self._slack._subscriptions[channel_id]:
                            self._slack._subscriptions[channel_id].remove(event_type)
                else:
                    del self._slack._subscriptions[channel_id]
            return True
        elif platform == ChatPlatform.TEAMS:
            if channel_id in self._teams._subscriptions:
                if event_types:
                    for event_type in event_types:
                        if event_type in self._teams._subscriptions[channel_id]:
                            self._teams._subscriptions[channel_id].remove(event_type)
                else:
                    del self._teams._subscriptions[channel_id]
            return True

        return False

    async def get_subscriptions(
        self,
        platform: ChatPlatform,
        channel_id: str,
    ) -> list[str]:
        """Get subscriptions for a channel."""
        if platform == ChatPlatform.SLACK:
            return self._slack._subscriptions.get(channel_id, [])
        elif platform == ChatPlatform.TEAMS:
            return self._teams._subscriptions.get(channel_id, [])

        return []

    # Dashboard

    async def get_chatbot_dashboard(self) -> dict[str, Any]:
        """Get chatbot dashboard data."""
        return {
            "platforms": {
                "slack": {
                    "configured": self._platform_configs.get("slack", {}).get("configured", False),
                    "users": len(self._slack._users),
                    "subscribed_channels": len(self._slack._subscriptions),
                },
                "teams": {
                    "configured": self._platform_configs.get("teams", {}).get("configured", False),
                    "users": len(self._teams._users),
                    "subscribed_channels": len(self._teams._subscriptions),
                },
            },
            "commands": len(DEFAULT_COMMANDS),
            "linked_users": len(self._user_mappings),
        }


# Singleton instance
_chatbot_service: ChatbotService | None = None


def get_chatbot_service() -> ChatbotService:
    """Get the chatbot service singleton."""
    global _chatbot_service
    if _chatbot_service is None:
        _chatbot_service = ChatbotService()
    return _chatbot_service
