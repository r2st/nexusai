"""Microsoft Teams Bot Integration."""

import uuid
from datetime import datetime
from typing import Any

from app.services.chatbot.models import (
    ChatPlatform,
    MessageType,
    BotCommand,
    BotMessage,
    BotUser,
    BotConversation,
    DEFAULT_COMMANDS,
)


class TeamsBot:
    """Microsoft Teams bot integration service."""

    def __init__(
        self,
        app_id: str | None = None,
        app_password: str | None = None,
        tenant_id: str | None = None,
    ):
        self._app_id = app_id
        self._app_password = app_password
        self._tenant_id = tenant_id

        # In-memory storage - replace with database in production
        self._users: dict[str, BotUser] = {}
        self._conversations: dict[str, BotConversation] = {}
        self._commands: dict[str, BotCommand] = {
            cmd.name: cmd for cmd in DEFAULT_COMMANDS
        }
        self._subscriptions: dict[str, list[str]] = {}  # channel_id -> event_types

    async def handle_activity(
        self,
        activity: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Handle incoming Teams activity."""
        activity_type = activity.get("type")

        if activity_type == "message":
            return await self._handle_message(activity)
        elif activity_type == "invoke":
            return await self._handle_invoke(activity)
        elif activity_type == "conversationUpdate":
            return await self._handle_conversation_update(activity)

        return None

    async def _handle_message(
        self,
        activity: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Handle message activity."""
        text = activity.get("text", "")
        from_user = activity.get("from", {})
        conversation = activity.get("conversation", {})
        channel_data = activity.get("channelData", {})

        # Get or create user
        user = await self._get_or_create_user(
            platform_user_id=from_user.get("id"),
            username=from_user.get("name"),
            tenant_id=channel_data.get("tenant", {}).get("id"),
        )

        # Create message
        message = BotMessage(
            id=str(uuid.uuid4()),
            platform=ChatPlatform.TEAMS,
            message_type=MessageType.TEXT,
            user_id=user.id,
            channel_id=conversation.get("id"),
            text=text,
            platform_message_id=activity.get("id"),
            platform_channel_id=conversation.get("id"),
            platform_team_id=channel_data.get("team", {}).get("id"),
        )

        # Remove bot mention if present
        entities = activity.get("entities", [])
        for entity in entities:
            if entity.get("type") == "mention":
                mentioned = entity.get("mentioned", {})
                if mentioned.get("id") == self._app_id:
                    mention_text = entity.get("text", "")
                    text = text.replace(mention_text, "").strip()
                    message.text = text

        # Check if this is a command
        if text.startswith("/") or text.startswith("!") or text.lower().startswith("nexus"):
            return await self._handle_command(message, user)

        # Check if in a conversation flow
        conv_key = conversation.get("id")
        if conv_key in self._conversations:
            conv = self._conversations[conv_key]
            if conv.current_flow:
                return await self._handle_flow_response(message, user, conv)

        return None

    async def _handle_invoke(
        self,
        activity: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Handle invoke activity (card actions, etc.)."""
        invoke_name = activity.get("name")
        value = activity.get("value", {})

        if invoke_name == "adaptiveCard/action":
            return await self._handle_card_action(activity, value)
        elif invoke_name == "composeExtension/query":
            return await self._handle_compose_extension(activity, value)

        return None

    async def _handle_conversation_update(
        self,
        activity: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Handle conversation update (member added/removed, etc.)."""
        members_added = activity.get("membersAdded", [])
        conversation = activity.get("conversation", {})

        for member in members_added:
            if member.get("id") == activity.get("recipient", {}).get("id"):
                # Bot was added to the conversation
                return await self._send_welcome_card(conversation.get("id"))

        return None

    async def _handle_command(
        self,
        message: BotMessage,
        user: BotUser,
    ) -> dict[str, Any]:
        """Handle a command message."""
        text = message.text or ""

        # Parse command
        text = text.lower().replace("nexus", "").replace("/", "").replace("!", "").strip()
        parts = text.split()
        command_name = parts[0] if parts else "help"
        args = parts[1:] if len(parts) > 1 else []

        message.command = command_name
        message.command_args = args

        return await self._execute_command(command_name, message, user)

    async def _execute_command(
        self,
        command_name: str,
        message: BotMessage,
        user: BotUser,
    ) -> dict[str, Any]:
        """Execute a command and return response."""
        command = self._commands.get(command_name)

        if not command:
            return self._create_text_response(
                f"Unknown command: '{command_name}'. Type 'help' to see available commands."
            )

        # Check authorization
        if command.requires_auth and not user.nexus_user_id:
            return await self._get_link_account_card()

        if command.admin_only and not user.is_admin:
            return self._create_text_response(
                "This command requires admin permissions."
            )

        # Execute command
        if command_name == "help":
            return await self._cmd_help(message, user)
        elif command_name == "metrics":
            return await self._cmd_metrics(message, user)
        elif command_name == "status":
            return await self._cmd_status(message, user)
        elif command_name == "projects":
            return await self._cmd_projects(message, user)
        elif command_name == "alerts":
            return await self._cmd_alerts(message, user)
        elif command_name == "prs":
            return await self._cmd_prs(message, user)
        elif command_name == "deploy":
            return await self._cmd_deploy(message, user)
        elif command_name == "quality":
            return await self._cmd_quality(message, user)
        elif command_name == "subscribe":
            return await self._cmd_subscribe(message, user)
        elif command_name == "unsubscribe":
            return await self._cmd_unsubscribe(message, user)
        elif command_name == "link":
            return await self._cmd_link(message, user)
        elif command_name == "unlink":
            return await self._cmd_unlink(message, user)

        return self._create_text_response(
            f"Command '{command_name}' is not yet implemented."
        )

    def _create_text_response(self, text: str) -> dict[str, Any]:
        """Create a simple text response."""
        return {
            "type": "message",
            "text": text,
        }

    def _create_adaptive_card(
        self,
        body: list[dict[str, Any]],
        actions: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Create an adaptive card response."""
        card = {
            "type": "AdaptiveCard",
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.4",
            "body": body,
        }

        if actions:
            card["actions"] = actions

        return {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": card,
                }
            ],
        }

    async def _cmd_help(
        self,
        message: BotMessage,
        user: BotUser,
    ) -> dict[str, Any]:
        """Handle help command."""
        args = message.command_args

        if args:
            cmd_name = args[0]
            command = self._commands.get(cmd_name)
            if command:
                return self._create_adaptive_card(
                    body=[
                        {
                            "type": "TextBlock",
                            "text": f"**{cmd_name}**",
                            "size": "Large",
                            "weight": "Bolder",
                        },
                        {
                            "type": "TextBlock",
                            "text": command.description,
                            "wrap": True,
                        },
                        {
                            "type": "TextBlock",
                            "text": f"**Usage:** `{command.usage}`",
                            "wrap": True,
                        },
                        {
                            "type": "TextBlock",
                            "text": "**Examples:**",
                            "weight": "Bolder",
                        },
                        {
                            "type": "TextBlock",
                            "text": "\n".join(f"- `{ex}`" for ex in command.examples),
                            "wrap": True,
                        },
                    ]
                )

        commands_list = [
            {
                "type": "FactSet",
                "facts": [
                    {"title": cmd.name, "value": cmd.description}
                    for cmd in self._commands.values()
                    if ChatPlatform.TEAMS in cmd.platforms
                ],
            }
        ]

        return self._create_adaptive_card(
            body=[
                {
                    "type": "TextBlock",
                    "text": "NexusAI Bot Commands",
                    "size": "Large",
                    "weight": "Bolder",
                },
                *commands_list,
                {
                    "type": "TextBlock",
                    "text": "Type 'help [command]' for more details.",
                    "size": "Small",
                    "isSubtle": True,
                },
            ]
        )

    async def _cmd_metrics(
        self,
        message: BotMessage,
        user: BotUser,
    ) -> dict[str, Any]:
        """Handle metrics command."""
        args = message.command_args
        metric_type = args[0] if args else "dora"
        period = args[1] if len(args) > 1 else "7d"

        if metric_type == "dora":
            return self._create_adaptive_card(
                body=[
                    {
                        "type": "TextBlock",
                        "text": f"DORA Metrics ({period})",
                        "size": "Large",
                        "weight": "Bolder",
                    },
                    {
                        "type": "ColumnSet",
                        "columns": [
                            {
                                "type": "Column",
                                "width": "stretch",
                                "items": [
                                    {"type": "TextBlock", "text": "Deployment Frequency", "weight": "Bolder"},
                                    {"type": "TextBlock", "text": "2.3/day ✓", "color": "Good"},
                                ],
                            },
                            {
                                "type": "Column",
                                "width": "stretch",
                                "items": [
                                    {"type": "TextBlock", "text": "Lead Time", "weight": "Bolder"},
                                    {"type": "TextBlock", "text": "4.2 hours ✓", "color": "Good"},
                                ],
                            },
                        ],
                    },
                    {
                        "type": "ColumnSet",
                        "columns": [
                            {
                                "type": "Column",
                                "width": "stretch",
                                "items": [
                                    {"type": "TextBlock", "text": "Change Failure Rate", "weight": "Bolder"},
                                    {"type": "TextBlock", "text": "3.2% ✓", "color": "Good"},
                                ],
                            },
                            {
                                "type": "Column",
                                "width": "stretch",
                                "items": [
                                    {"type": "TextBlock", "text": "MTTR", "weight": "Bolder"},
                                    {"type": "TextBlock", "text": "1.5 hours ✓", "color": "Good"},
                                ],
                            },
                        ],
                    },
                ]
            )

        return self._create_text_response(
            f"Unknown metric type: '{metric_type}'. Use 'dora' or 'space'."
        )

    async def _cmd_status(
        self,
        message: BotMessage,
        user: BotUser,
    ) -> dict[str, Any]:
        """Handle status command."""
        return self._create_adaptive_card(
            body=[
                {
                    "type": "TextBlock",
                    "text": "System Status",
                    "size": "Large",
                    "weight": "Bolder",
                },
                {
                    "type": "FactSet",
                    "facts": [
                        {"title": "API", "value": "🟢 Operational"},
                        {"title": "Database", "value": "🟢 Operational"},
                        {"title": "Analytics", "value": "🟢 Operational"},
                        {"title": "Webhooks", "value": "🟢 Operational"},
                    ],
                },
                {
                    "type": "TextBlock",
                    "text": f"Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC",
                    "size": "Small",
                    "isSubtle": True,
                },
            ]
        )

    async def _cmd_projects(
        self,
        message: BotMessage,
        user: BotUser,
    ) -> dict[str, Any]:
        """Handle projects command."""
        return self._create_adaptive_card(
            body=[
                {
                    "type": "TextBlock",
                    "text": "Your Projects",
                    "size": "Large",
                    "weight": "Bolder",
                },
                {
                    "type": "FactSet",
                    "facts": [
                        {"title": "frontend-app", "value": "React web application"},
                        {"title": "backend-api", "value": "Python FastAPI service"},
                        {"title": "mobile-app", "value": "React Native mobile app"},
                    ],
                },
            ]
        )

    async def _cmd_alerts(
        self,
        message: BotMessage,
        user: BotUser,
    ) -> dict[str, Any]:
        """Handle alerts command."""
        return self._create_adaptive_card(
            body=[
                {
                    "type": "TextBlock",
                    "text": "Active Alerts",
                    "size": "Large",
                    "weight": "Bolder",
                },
                {
                    "type": "TextBlock",
                    "text": "⚠️ **High CPU usage** on `prod-api-1`",
                    "wrap": True,
                },
                {
                    "type": "TextBlock",
                    "text": "🔴 **Failed deployment** to `staging`",
                    "wrap": True,
                },
            ],
            actions=[
                {
                    "type": "Action.Submit",
                    "title": "Acknowledge All",
                    "data": {"action": "ack_all_alerts"},
                },
            ],
        )

    async def _cmd_prs(
        self,
        message: BotMessage,
        user: BotUser,
    ) -> dict[str, Any]:
        """Handle PRs command."""
        return self._create_adaptive_card(
            body=[
                {
                    "type": "TextBlock",
                    "text": "Open Pull Requests",
                    "size": "Large",
                    "weight": "Bolder",
                },
                {
                    "type": "TextBlock",
                    "text": "- **#123** Add user authentication - 2 hours ago",
                    "wrap": True,
                },
                {
                    "type": "TextBlock",
                    "text": "- **#124** Fix payment bug - 5 hours ago",
                    "wrap": True,
                },
                {
                    "type": "TextBlock",
                    "text": "- **#125** Update dependencies - 1 day ago",
                    "wrap": True,
                },
            ]
        )

    async def _cmd_deploy(
        self,
        message: BotMessage,
        user: BotUser,
    ) -> dict[str, Any]:
        """Handle deploy command."""
        return self._create_adaptive_card(
            body=[
                {
                    "type": "TextBlock",
                    "text": "Deployment Status",
                    "size": "Large",
                    "weight": "Bolder",
                },
                {
                    "type": "ColumnSet",
                    "columns": [
                        {
                            "type": "Column",
                            "width": "stretch",
                            "items": [
                                {"type": "TextBlock", "text": "Production", "weight": "Bolder"},
                                {"type": "TextBlock", "text": "🟢 v2.3.1 - 2h ago", "color": "Good"},
                            ],
                        },
                        {
                            "type": "Column",
                            "width": "stretch",
                            "items": [
                                {"type": "TextBlock", "text": "Staging", "weight": "Bolder"},
                                {"type": "TextBlock", "text": "🟢 v2.3.2 - 30m ago", "color": "Good"},
                            ],
                        },
                    ],
                },
            ]
        )

    async def _cmd_quality(
        self,
        message: BotMessage,
        user: BotUser,
    ) -> dict[str, Any]:
        """Handle quality command."""
        return self._create_adaptive_card(
            body=[
                {
                    "type": "TextBlock",
                    "text": "Code Quality Metrics",
                    "size": "Large",
                    "weight": "Bolder",
                },
                {
                    "type": "ColumnSet",
                    "columns": [
                        {
                            "type": "Column",
                            "width": "stretch",
                            "items": [
                                {"type": "TextBlock", "text": "Test Coverage", "weight": "Bolder"},
                                {"type": "TextBlock", "text": "87% ✓", "color": "Good"},
                            ],
                        },
                        {
                            "type": "Column",
                            "width": "stretch",
                            "items": [
                                {"type": "TextBlock", "text": "Code Smells", "weight": "Bolder"},
                                {"type": "TextBlock", "text": "12 ⚠️", "color": "Warning"},
                            ],
                        },
                    ],
                },
                {
                    "type": "ColumnSet",
                    "columns": [
                        {
                            "type": "Column",
                            "width": "stretch",
                            "items": [
                                {"type": "TextBlock", "text": "Security Issues", "weight": "Bolder"},
                                {"type": "TextBlock", "text": "0 🛡️", "color": "Good"},
                            ],
                        },
                        {
                            "type": "Column",
                            "width": "stretch",
                            "items": [
                                {"type": "TextBlock", "text": "Technical Debt", "weight": "Bolder"},
                                {"type": "TextBlock", "text": "4.2 days"},
                            ],
                        },
                    ],
                },
            ]
        )

    async def _cmd_subscribe(
        self,
        message: BotMessage,
        user: BotUser,
    ) -> dict[str, Any]:
        """Handle subscribe command."""
        args = message.command_args
        if not args:
            return self._create_text_response(
                "Usage: 'subscribe [event-type]'\nAvailable: pr-merged, deploy-failed, alert, metrics-report"
            )

        event_type = args[0]
        channel_id = message.channel_id

        if channel_id not in self._subscriptions:
            self._subscriptions[channel_id] = []

        if event_type not in self._subscriptions[channel_id]:
            self._subscriptions[channel_id].append(event_type)

        return self._create_text_response(
            f"✓ Subscribed to '{event_type}' notifications in this channel."
        )

    async def _cmd_unsubscribe(
        self,
        message: BotMessage,
        user: BotUser,
    ) -> dict[str, Any]:
        """Handle unsubscribe command."""
        args = message.command_args
        if not args:
            return self._create_text_response("Usage: 'unsubscribe [event-type]'")

        event_type = args[0]
        channel_id = message.channel_id

        if channel_id in self._subscriptions:
            if event_type in self._subscriptions[channel_id]:
                self._subscriptions[channel_id].remove(event_type)

        return self._create_text_response(
            f"✓ Unsubscribed from '{event_type}' notifications."
        )

    async def _cmd_link(
        self,
        message: BotMessage,
        user: BotUser,
    ) -> dict[str, Any]:
        """Handle link account command."""
        return await self._get_link_account_card()

    async def _get_link_account_card(self) -> dict[str, Any]:
        """Get card for linking account."""
        return self._create_adaptive_card(
            body=[
                {
                    "type": "TextBlock",
                    "text": "Link Your Account",
                    "size": "Large",
                    "weight": "Bolder",
                },
                {
                    "type": "TextBlock",
                    "text": "To use NexusAI commands, please link your Teams account.",
                    "wrap": True,
                },
            ],
            actions=[
                {
                    "type": "Action.OpenUrl",
                    "title": "Link Account",
                    "url": "https://app.nexusai.dev/settings/integrations/teams",
                },
            ],
        )

    async def _cmd_unlink(
        self,
        message: BotMessage,
        user: BotUser,
    ) -> dict[str, Any]:
        """Handle unlink account command."""
        user.nexus_user_id = None
        user.organization_id = None

        return self._create_text_response(
            "✓ Your Teams account has been unlinked from NexusAI."
        )

    async def _get_or_create_user(
        self,
        platform_user_id: str,
        username: str | None,
        tenant_id: str | None,
    ) -> BotUser:
        """Get or create a bot user."""
        user_key = f"{tenant_id}:{platform_user_id}"

        if user_key not in self._users:
            self._users[user_key] = BotUser(
                id=str(uuid.uuid4()),
                platform=ChatPlatform.TEAMS,
                platform_user_id=platform_user_id,
                username=username or platform_user_id,
            )

        user = self._users[user_key]
        user.last_seen = datetime.utcnow()

        return user

    async def _handle_card_action(
        self,
        activity: dict[str, Any],
        value: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Handle adaptive card action."""
        action = value.get("action")

        if action == "ack_all_alerts":
            return self._create_text_response("✓ All alerts acknowledged.")

        return None

    async def _handle_compose_extension(
        self,
        activity: dict[str, Any],
        value: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Handle compose extension query."""
        # Handle search in compose extension
        return None

    async def _handle_flow_response(
        self,
        message: BotMessage,
        user: BotUser,
        conversation: BotConversation,
    ) -> dict[str, Any] | None:
        """Handle response in a conversation flow."""
        return None

    async def _send_welcome_card(
        self,
        conversation_id: str,
    ) -> dict[str, Any]:
        """Send welcome card when bot is added."""
        return self._create_adaptive_card(
            body=[
                {
                    "type": "TextBlock",
                    "text": "Welcome to NexusAI! 🚀",
                    "size": "Large",
                    "weight": "Bolder",
                },
                {
                    "type": "TextBlock",
                    "text": "I can help you with engineering metrics, deployments, alerts, and more.",
                    "wrap": True,
                },
                {
                    "type": "TextBlock",
                    "text": "Type 'help' to see available commands.",
                    "wrap": True,
                },
            ],
            actions=[
                {
                    "type": "Action.Submit",
                    "title": "Get Started",
                    "data": {"action": "help"},
                },
            ],
        )

    async def send_message(
        self,
        conversation_id: str,
        text: str | None = None,
        card: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Send a message to a Teams conversation."""
        # In production, use Bot Framework SDK
        return {
            "conversation_id": conversation_id,
            "text": text,
            "card": card,
        }

    async def send_notification(
        self,
        conversation_ids: list[str],
        event_type: str,
        title: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[str]:
        """Send notification to subscribed conversations."""
        sent_to = []

        for conv_id in conversation_ids:
            subscriptions = self._subscriptions.get(conv_id, [])
            if event_type in subscriptions or "all" in subscriptions:
                await self.send_message(
                    conversation_id=conv_id,
                    card=self._create_adaptive_card(
                        body=[
                            {
                                "type": "TextBlock",
                                "text": title,
                                "size": "Medium",
                                "weight": "Bolder",
                            },
                            {
                                "type": "TextBlock",
                                "text": message,
                                "wrap": True,
                            },
                        ]
                    ),
                )
                sent_to.append(conv_id)

        return sent_to


# Singleton instance
_teams_bot: TeamsBot | None = None


def get_teams_bot() -> TeamsBot:
    """Get the Teams bot singleton."""
    global _teams_bot
    if _teams_bot is None:
        _teams_bot = TeamsBot()
    return _teams_bot
