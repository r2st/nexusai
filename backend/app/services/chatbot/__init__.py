"""Slack/Teams Chatbot Integration Services."""

from app.services.chatbot.models import (
    ChatPlatform,
    MessageType,
    BotCommand,
    BotMessage,
    BotConversation,
    BotUser,
    CommandHandler,
    InteractiveComponent,
    SlashCommandConfig,
    WebhookEvent,
)
from app.services.chatbot.slack import (
    SlackBot,
    get_slack_bot,
)
from app.services.chatbot.teams import (
    TeamsBot,
    get_teams_bot,
)
from app.services.chatbot.service import (
    ChatbotService,
    get_chatbot_service,
)

__all__ = [
    # Models
    "ChatPlatform",
    "MessageType",
    "BotCommand",
    "BotMessage",
    "BotConversation",
    "BotUser",
    "CommandHandler",
    "InteractiveComponent",
    "SlashCommandConfig",
    "WebhookEvent",
    # Services
    "SlackBot",
    "get_slack_bot",
    "TeamsBot",
    "get_teams_bot",
    "ChatbotService",
    "get_chatbot_service",
]
