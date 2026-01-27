"""Slack Bot Integration."""

import hashlib
import hmac
import time
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
    WebhookEvent,
    DEFAULT_COMMANDS,
)


class SlackBot:
    """Slack bot integration service."""

    def __init__(
        self,
        bot_token: str | None = None,
        signing_secret: str | None = None,
        app_id: str | None = None,
    ):
        self._bot_token = bot_token
        self._signing_secret = signing_secret
        self._app_id = app_id

        # In-memory storage - replace with database in production
        self._users: dict[str, BotUser] = {}
        self._conversations: dict[str, BotConversation] = {}
        self._commands: dict[str, BotCommand] = {
            cmd.name: cmd for cmd in DEFAULT_COMMANDS
        }
        self._subscriptions: dict[str, list[str]] = {}  # channel_id -> event_types

    def verify_signature(
        self,
        timestamp: str,
        signature: str,
        body: bytes,
    ) -> bool:
        """Verify Slack request signature."""
        if not self._signing_secret:
            return False

        # Check timestamp to prevent replay attacks
        current_time = int(time.time())
        if abs(current_time - int(timestamp)) > 60 * 5:
            return False

        # Compute expected signature
        sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
        expected_sig = "v0=" + hmac.new(
            self._signing_secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected_sig, signature)

    async def handle_event(self, event_data: dict[str, Any]) -> dict[str, Any] | None:
        """Handle incoming Slack event."""
        event_type = event_data.get("type")

        # URL verification challenge
        if event_type == "url_verification":
            return {"challenge": event_data.get("challenge")}

        # Event callback
        if event_type == "event_callback":
            event = event_data.get("event", {})
            inner_type = event.get("type")

            if inner_type == "message":
                return await self._handle_message_event(event, event_data)
            elif inner_type == "app_mention":
                return await self._handle_mention_event(event, event_data)
            elif inner_type == "member_joined_channel":
                return await self._handle_member_joined(event, event_data)

        return None

    async def _handle_message_event(
        self,
        event: dict[str, Any],
        event_data: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Handle message event."""
        # Ignore bot messages
        if event.get("bot_id") or event.get("subtype") == "bot_message":
            return None

        user_id = event.get("user")
        channel_id = event.get("channel")
        text = event.get("text", "")
        thread_ts = event.get("thread_ts")

        # Get or create user
        user = await self._get_or_create_user(user_id, event_data.get("team_id"))

        # Create message
        message = BotMessage(
            id=str(uuid.uuid4()),
            platform=ChatPlatform.SLACK,
            message_type=MessageType.TEXT,
            user_id=user.id,
            channel_id=channel_id,
            thread_id=thread_ts,
            text=text,
            platform_message_id=event.get("ts"),
            platform_channel_id=channel_id,
            platform_team_id=event_data.get("team_id"),
        )

        # Check if this is a command (starts with our prefix)
        if text.startswith("/nexus ") or text.startswith("!nexus "):
            return await self._handle_command(message, user)

        # Check if in a conversation flow
        conversation = self._conversations.get(f"{channel_id}:{thread_ts or 'main'}")
        if conversation and conversation.current_flow:
            return await self._handle_flow_response(message, user, conversation)

        return None

    async def _handle_mention_event(
        self,
        event: dict[str, Any],
        event_data: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Handle app mention event."""
        user_id = event.get("user")
        channel_id = event.get("channel")
        text = event.get("text", "")
        thread_ts = event.get("thread_ts")

        # Get or create user
        user = await self._get_or_create_user(user_id, event_data.get("team_id"))

        # Remove the mention from text
        # Format is usually <@BOT_ID> command args
        parts = text.split(">", 1)
        if len(parts) > 1:
            text = parts[1].strip()

        message = BotMessage(
            id=str(uuid.uuid4()),
            platform=ChatPlatform.SLACK,
            message_type=MessageType.TEXT,
            user_id=user.id,
            channel_id=channel_id,
            thread_id=thread_ts,
            text=text,
            platform_message_id=event.get("ts"),
            platform_channel_id=channel_id,
            platform_team_id=event_data.get("team_id"),
        )

        return await self._handle_command(message, user)

    async def _handle_member_joined(
        self,
        event: dict[str, Any],
        event_data: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Handle member joined channel event."""
        # Could send a welcome message
        return None

    async def handle_slash_command(
        self,
        command_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle Slack slash command."""
        command = command_data.get("command", "").lstrip("/")
        text = command_data.get("text", "")
        user_id = command_data.get("user_id")
        channel_id = command_data.get("channel_id")
        team_id = command_data.get("team_id")

        # Get or create user
        user = await self._get_or_create_user(user_id, team_id)

        # Parse command and args
        args = text.split() if text else []
        subcommand = args[0] if args else "help"
        subcommand_args = args[1:] if len(args) > 1 else []

        message = BotMessage(
            id=str(uuid.uuid4()),
            platform=ChatPlatform.SLACK,
            message_type=MessageType.TEXT,
            user_id=user.id,
            channel_id=channel_id,
            text=text,
            command=subcommand,
            command_args=subcommand_args,
            platform_channel_id=channel_id,
            platform_team_id=team_id,
        )

        # Handle the command
        response = await self._execute_command(subcommand, message, user)

        return response

    async def handle_interaction(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Handle Slack interactive component."""
        interaction_type = payload.get("type")

        if interaction_type == "block_actions":
            return await self._handle_block_action(payload)
        elif interaction_type == "view_submission":
            return await self._handle_view_submission(payload)
        elif interaction_type == "shortcut":
            return await self._handle_shortcut(payload)

        return None

    async def _handle_block_action(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Handle block action interaction."""
        actions = payload.get("actions", [])
        user = payload.get("user", {})
        channel = payload.get("channel", {})

        for action in actions:
            action_id = action.get("action_id")
            value = action.get("value")

            # Handle specific actions
            if action_id.startswith("ack_alert_"):
                alert_id = action_id.replace("ack_alert_", "")
                return await self._acknowledge_alert(alert_id, user.get("id"))

            elif action_id.startswith("subscribe_"):
                event_type = action_id.replace("subscribe_", "")
                return await self._subscribe_channel(
                    channel.get("id"), event_type
                )

        return None

    async def _handle_view_submission(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Handle modal view submission."""
        # Handle form submissions from modals
        return None

    async def _handle_shortcut(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Handle global/message shortcut."""
        return None

    async def _handle_command(
        self,
        message: BotMessage,
        user: BotUser,
    ) -> dict[str, Any] | None:
        """Handle a command message."""
        text = message.text or ""

        # Parse command
        parts = text.replace("/nexus ", "").replace("!nexus ", "").strip().split()
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
            return {
                "response_type": "ephemeral",
                "text": f"Unknown command: `{command_name}`. Use `/nexus help` to see available commands.",
            }

        # Check authorization
        if command.requires_auth and not user.nexus_user_id:
            return await self._get_link_account_response()

        if command.admin_only and not user.is_admin:
            return {
                "response_type": "ephemeral",
                "text": "This command requires admin permissions.",
            }

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

        return {
            "response_type": "ephemeral",
            "text": f"Command `{command_name}` is not yet implemented.",
        }

    async def _cmd_help(
        self,
        message: BotMessage,
        user: BotUser,
    ) -> dict[str, Any]:
        """Handle help command."""
        args = message.command_args

        if args:
            # Help for specific command
            cmd_name = args[0]
            command = self._commands.get(cmd_name)
            if command:
                return {
                    "response_type": "ephemeral",
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*/{cmd_name}*\n{command.description}",
                            },
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*Usage:* `{command.usage}`",
                            },
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": "*Examples:*\n" + "\n".join(
                                    f"• `{ex}`" for ex in command.examples
                                ),
                            },
                        },
                    ],
                }
            else:
                return {
                    "response_type": "ephemeral",
                    "text": f"Unknown command: `{cmd_name}`",
                }

        # General help
        commands_text = "\n".join(
            f"• `{cmd.name}` - {cmd.description}"
            for cmd in self._commands.values()
            if ChatPlatform.SLACK in cmd.platforms
        )

        return {
            "response_type": "ephemeral",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "NexusAI Bot Commands",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": commands_text,
                    },
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "Use `/nexus help [command]` for more details on a specific command.",
                        },
                    ],
                },
            ],
        }

    async def _cmd_metrics(
        self,
        message: BotMessage,
        user: BotUser,
    ) -> dict[str, Any]:
        """Handle metrics command."""
        args = message.command_args
        metric_type = args[0] if args else "dora"
        period = args[1] if len(args) > 1 else "7d"

        # In production, fetch actual metrics from the metrics service
        if metric_type == "dora":
            return {
                "response_type": "in_channel",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"DORA Metrics ({period})",
                        },
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Deployment Frequency*\n2.3 per day :white_check_mark:",
                            },
                            {
                                "type": "mrkdwn",
                                "text": "*Lead Time for Changes*\n4.2 hours :white_check_mark:",
                            },
                            {
                                "type": "mrkdwn",
                                "text": "*Change Failure Rate*\n3.2% :white_check_mark:",
                            },
                            {
                                "type": "mrkdwn",
                                "text": "*MTTR*\n1.5 hours :white_check_mark:",
                            },
                        ],
                    },
                ],
            }
        elif metric_type == "space":
            return {
                "response_type": "in_channel",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"SPACE Metrics ({period})",
                        },
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Satisfaction*\n4.2/5 :star:",
                            },
                            {
                                "type": "mrkdwn",
                                "text": "*Performance*\n92% :chart_with_upwards_trend:",
                            },
                            {
                                "type": "mrkdwn",
                                "text": "*Activity*\n156 commits",
                            },
                            {
                                "type": "mrkdwn",
                                "text": "*Efficiency*\n78% :zap:",
                            },
                        ],
                    },
                ],
            }

        return {
            "response_type": "ephemeral",
            "text": f"Unknown metric type: `{metric_type}`. Use `dora` or `space`.",
        }

    async def _cmd_status(
        self,
        message: BotMessage,
        user: BotUser,
    ) -> dict[str, Any]:
        """Handle status command."""
        return {
            "response_type": "in_channel",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "System Status",
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": "*API*\n:large_green_circle: Operational",
                        },
                        {
                            "type": "mrkdwn",
                            "text": "*Database*\n:large_green_circle: Operational",
                        },
                        {
                            "type": "mrkdwn",
                            "text": "*Analytics*\n:large_green_circle: Operational",
                        },
                        {
                            "type": "mrkdwn",
                            "text": "*Webhooks*\n:large_green_circle: Operational",
                        },
                    ],
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC",
                        },
                    ],
                },
            ],
        }

    async def _cmd_projects(
        self,
        message: BotMessage,
        user: BotUser,
    ) -> dict[str, Any]:
        """Handle projects command."""
        args = message.command_args
        action = args[0] if args else "list"

        if action == "list":
            # In production, fetch from project service
            return {
                "response_type": "ephemeral",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "Your Projects",
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "• *frontend-app* - React web application\n• *backend-api* - Python FastAPI service\n• *mobile-app* - React Native mobile app",
                        },
                    },
                ],
            }

        return {
            "response_type": "ephemeral",
            "text": f"Unknown action: `{action}`. Use `list`, `info`, or `add`.",
        }

    async def _cmd_alerts(
        self,
        message: BotMessage,
        user: BotUser,
    ) -> dict[str, Any]:
        """Handle alerts command."""
        args = message.command_args
        action = args[0] if args else "list"

        if action == "list":
            return {
                "response_type": "ephemeral",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "Active Alerts",
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": ":warning: *High CPU usage* on `prod-api-1`\n:red_circle: *Failed deployment* to `staging`",
                        },
                        "accessory": {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Acknowledge All",
                            },
                            "action_id": "ack_all_alerts",
                        },
                    },
                ],
            }

        return {
            "response_type": "ephemeral",
            "text": "Use `/nexus alerts list` to see active alerts.",
        }

    async def _cmd_prs(
        self,
        message: BotMessage,
        user: BotUser,
    ) -> dict[str, Any]:
        """Handle PRs command."""
        args = message.command_args
        filter_type = args[0] if args else "open"

        return {
            "response_type": "ephemeral",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"Pull Requests ({filter_type})",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "• <https://github.com|#123> Add user authentication - *2 hours ago*\n• <https://github.com|#124> Fix payment bug - *5 hours ago*\n• <https://github.com|#125> Update dependencies - *1 day ago*",
                    },
                },
            ],
        }

    async def _cmd_deploy(
        self,
        message: BotMessage,
        user: BotUser,
    ) -> dict[str, Any]:
        """Handle deploy command."""
        args = message.command_args
        action = args[0] if args else "status"

        if action == "status":
            env = args[1] if len(args) > 1 else "all"
            return {
                "response_type": "in_channel",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"Deployment Status ({env})",
                        },
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Production*\n:large_green_circle: v2.3.1 - 2h ago",
                            },
                            {
                                "type": "mrkdwn",
                                "text": "*Staging*\n:large_green_circle: v2.3.2 - 30m ago",
                            },
                        ],
                    },
                ],
            }

        return {
            "response_type": "ephemeral",
            "text": "Use `/nexus deploy status [env]` to see deployment status.",
        }

    async def _cmd_quality(
        self,
        message: BotMessage,
        user: BotUser,
    ) -> dict[str, Any]:
        """Handle quality command."""
        return {
            "response_type": "in_channel",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "Code Quality Metrics",
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": "*Test Coverage*\n87% :white_check_mark:",
                        },
                        {
                            "type": "mrkdwn",
                            "text": "*Code Smells*\n12 :warning:",
                        },
                        {
                            "type": "mrkdwn",
                            "text": "*Security Issues*\n0 :shield:",
                        },
                        {
                            "type": "mrkdwn",
                            "text": "*Technical Debt*\n4.2 days",
                        },
                    ],
                },
            ],
        }

    async def _cmd_subscribe(
        self,
        message: BotMessage,
        user: BotUser,
    ) -> dict[str, Any]:
        """Handle subscribe command."""
        args = message.command_args
        if not args:
            return {
                "response_type": "ephemeral",
                "text": "Usage: `/nexus subscribe [event-type]`\nAvailable: `pr-merged`, `deploy-failed`, `alert`, `metrics-report`",
            }

        event_type = args[0]
        channel_id = message.channel_id

        if channel_id not in self._subscriptions:
            self._subscriptions[channel_id] = []

        if event_type not in self._subscriptions[channel_id]:
            self._subscriptions[channel_id].append(event_type)

        return {
            "response_type": "ephemeral",
            "text": f":white_check_mark: Subscribed to `{event_type}` notifications in this channel.",
        }

    async def _cmd_unsubscribe(
        self,
        message: BotMessage,
        user: BotUser,
    ) -> dict[str, Any]:
        """Handle unsubscribe command."""
        args = message.command_args
        if not args:
            return {
                "response_type": "ephemeral",
                "text": "Usage: `/nexus unsubscribe [event-type]`",
            }

        event_type = args[0]
        channel_id = message.channel_id

        if channel_id in self._subscriptions:
            if event_type in self._subscriptions[channel_id]:
                self._subscriptions[channel_id].remove(event_type)

        return {
            "response_type": "ephemeral",
            "text": f":white_check_mark: Unsubscribed from `{event_type}` notifications.",
        }

    async def _cmd_link(
        self,
        message: BotMessage,
        user: BotUser,
    ) -> dict[str, Any]:
        """Handle link account command."""
        return await self._get_link_account_response()

    async def _get_link_account_response(self) -> dict[str, Any]:
        """Get response for linking account."""
        return {
            "response_type": "ephemeral",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "To use NexusAI commands, please link your Slack account.",
                    },
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Link Account",
                            },
                            "url": "https://app.nexusai.dev/settings/integrations/slack",
                            "action_id": "link_account",
                        },
                    ],
                },
            ],
        }

    async def _cmd_unlink(
        self,
        message: BotMessage,
        user: BotUser,
    ) -> dict[str, Any]:
        """Handle unlink account command."""
        user.nexus_user_id = None
        user.organization_id = None

        return {
            "response_type": "ephemeral",
            "text": ":white_check_mark: Your Slack account has been unlinked from NexusAI.",
        }

    async def _get_or_create_user(
        self,
        platform_user_id: str,
        team_id: str | None,
    ) -> BotUser:
        """Get or create a bot user."""
        user_key = f"{team_id}:{platform_user_id}"

        if user_key not in self._users:
            self._users[user_key] = BotUser(
                id=str(uuid.uuid4()),
                platform=ChatPlatform.SLACK,
                platform_user_id=platform_user_id,
                username=platform_user_id,  # Would fetch from Slack API
            )

        user = self._users[user_key]
        user.last_seen = datetime.utcnow()

        return user

    async def _handle_flow_response(
        self,
        message: BotMessage,
        user: BotUser,
        conversation: BotConversation,
    ) -> dict[str, Any] | None:
        """Handle response in a conversation flow."""
        # Handle multi-step conversations
        return None

    async def _acknowledge_alert(
        self,
        alert_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        """Acknowledge an alert."""
        return {
            "response_type": "ephemeral",
            "text": f":white_check_mark: Alert `{alert_id}` acknowledged.",
        }

    async def _subscribe_channel(
        self,
        channel_id: str,
        event_type: str,
    ) -> dict[str, Any]:
        """Subscribe channel to event type."""
        if channel_id not in self._subscriptions:
            self._subscriptions[channel_id] = []

        if event_type not in self._subscriptions[channel_id]:
            self._subscriptions[channel_id].append(event_type)

        return {
            "response_type": "ephemeral",
            "text": f":white_check_mark: Channel subscribed to `{event_type}`.",
        }

    async def send_message(
        self,
        channel_id: str,
        text: str,
        blocks: list[dict[str, Any]] | None = None,
        thread_ts: str | None = None,
    ) -> dict[str, Any] | None:
        """Send a message to a Slack channel."""
        # In production, use Slack API
        # slack_client.chat_postMessage(...)
        return {
            "channel": channel_id,
            "text": text,
            "blocks": blocks,
            "thread_ts": thread_ts,
        }

    async def send_notification(
        self,
        channel_ids: list[str],
        event_type: str,
        title: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[str]:
        """Send notification to subscribed channels."""
        sent_to = []

        for channel_id in channel_ids:
            subscriptions = self._subscriptions.get(channel_id, [])
            if event_type in subscriptions or "all" in subscriptions:
                await self.send_message(
                    channel_id=channel_id,
                    text=f"*{title}*\n{message}",
                )
                sent_to.append(channel_id)

        return sent_to


# Singleton instance
_slack_bot: SlackBot | None = None


def get_slack_bot() -> SlackBot:
    """Get the Slack bot singleton."""
    global _slack_bot
    if _slack_bot is None:
        _slack_bot = SlackBot()
    return _slack_bot
