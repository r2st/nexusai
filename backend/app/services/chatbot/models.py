"""Data models for Chatbot Integration."""

from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine

from pydantic import BaseModel, Field


class ChatPlatform(str, Enum):
    """Supported chat platforms."""

    SLACK = "slack"
    TEAMS = "teams"
    DISCORD = "discord"


class MessageType(str, Enum):
    """Types of bot messages."""

    TEXT = "text"
    RICH = "rich"  # With attachments/blocks
    CARD = "card"  # Adaptive card (Teams)
    EPHEMERAL = "ephemeral"  # Only visible to one user
    THREAD_REPLY = "thread_reply"
    DIRECT_MESSAGE = "direct_message"


class BotUser(BaseModel):
    """A user interacting with the bot."""

    id: str
    platform: ChatPlatform
    platform_user_id: str
    username: str
    display_name: str | None = None
    email: str | None = None
    avatar_url: str | None = None

    # Organization mapping
    organization_id: str | None = None
    nexus_user_id: str | None = None

    # Metadata
    is_admin: bool = False
    is_bot: bool = False
    timezone: str | None = None

    # Timestamps
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)


class BotCommand(BaseModel):
    """A command registered with the bot."""

    name: str
    description: str
    usage: str | None = None
    examples: list[str] = Field(default_factory=list)

    # Command configuration
    aliases: list[str] = Field(default_factory=list)
    requires_auth: bool = True
    admin_only: bool = False

    # Supported platforms
    platforms: list[ChatPlatform] = Field(
        default_factory=lambda: [ChatPlatform.SLACK, ChatPlatform.TEAMS]
    )

    # Response configuration
    response_type: MessageType = MessageType.TEXT
    show_typing: bool = True


class BotMessage(BaseModel):
    """A message from or to the bot."""

    id: str
    platform: ChatPlatform
    message_type: MessageType = MessageType.TEXT

    # Sender/Receiver
    user_id: str | None = None
    channel_id: str
    thread_id: str | None = None

    # Content
    text: str | None = None
    blocks: list[dict[str, Any]] = Field(default_factory=list)  # Slack blocks
    attachments: list[dict[str, Any]] = Field(default_factory=list)
    card: dict[str, Any] | None = None  # Teams adaptive card

    # Context
    command: str | None = None
    command_args: list[str] = Field(default_factory=list)
    mentions: list[str] = Field(default_factory=list)

    # Platform-specific IDs
    platform_message_id: str | None = None
    platform_channel_id: str | None = None
    platform_team_id: str | None = None

    # Timestamps
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BotConversation(BaseModel):
    """A conversation with the bot."""

    id: str
    platform: ChatPlatform
    channel_id: str
    thread_id: str | None = None

    # Participants
    user_ids: list[str] = Field(default_factory=list)
    organization_id: str | None = None

    # State
    context: dict[str, Any] = Field(default_factory=dict)
    current_flow: str | None = None
    flow_step: int = 0

    # Messages
    messages: list[BotMessage] = Field(default_factory=list)

    # Timestamps
    started_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)


class InteractiveComponent(BaseModel):
    """An interactive component (button, select, etc.)."""

    id: str
    component_type: str  # button, select, datepicker, etc.
    action_id: str

    # Configuration
    label: str
    value: str | None = None
    options: list[dict[str, str]] = Field(default_factory=list)

    # Callback
    callback_data: dict[str, Any] = Field(default_factory=dict)


class SlashCommandConfig(BaseModel):
    """Configuration for a slash command."""

    command: str  # e.g., "/nexus"
    description: str
    usage_hint: str | None = None

    # Subcommands
    subcommands: list[str] = Field(default_factory=list)

    # Platform registration
    registered_on_slack: bool = False
    registered_on_teams: bool = False


class WebhookEvent(BaseModel):
    """An incoming webhook event."""

    id: str
    platform: ChatPlatform
    event_type: str

    # Event data
    data: dict[str, Any] = Field(default_factory=dict)

    # Context
    team_id: str | None = None
    channel_id: str | None = None
    user_id: str | None = None

    # Timestamp
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Type alias for command handlers
CommandHandler = Callable[
    [BotMessage, BotUser],
    Coroutine[Any, Any, BotMessage | list[BotMessage] | None]
]


# Default bot commands
DEFAULT_COMMANDS = [
    BotCommand(
        name="help",
        description="Show available commands",
        usage="/nexus help [command]",
        examples=["/nexus help", "/nexus help metrics"],
    ),
    BotCommand(
        name="metrics",
        description="Get DORA and SPACE metrics",
        usage="/nexus metrics [dora|space] [period]",
        examples=["/nexus metrics dora 7d", "/nexus metrics space monthly"],
    ),
    BotCommand(
        name="status",
        description="Get system status and health",
        usage="/nexus status [component]",
        examples=["/nexus status", "/nexus status api"],
    ),
    BotCommand(
        name="projects",
        description="List and manage projects",
        usage="/nexus projects [list|info|add]",
        examples=["/nexus projects list", "/nexus projects info my-app"],
    ),
    BotCommand(
        name="alerts",
        description="View and manage alerts",
        usage="/nexus alerts [list|ack|resolve]",
        examples=["/nexus alerts list", "/nexus alerts ack alert-123"],
    ),
    BotCommand(
        name="prs",
        description="View pull request information",
        usage="/nexus prs [open|review|merged]",
        examples=["/nexus prs open", "/nexus prs review me"],
    ),
    BotCommand(
        name="deploy",
        description="Get deployment information",
        usage="/nexus deploy [status|history|trigger]",
        examples=["/nexus deploy status prod", "/nexus deploy history staging"],
        admin_only=True,
    ),
    BotCommand(
        name="quality",
        description="Get code quality metrics",
        usage="/nexus quality [project] [period]",
        examples=["/nexus quality my-app 30d"],
    ),
    BotCommand(
        name="subscribe",
        description="Subscribe to notifications",
        usage="/nexus subscribe [event-type]",
        examples=["/nexus subscribe pr-merged", "/nexus subscribe deploy-failed"],
    ),
    BotCommand(
        name="unsubscribe",
        description="Unsubscribe from notifications",
        usage="/nexus unsubscribe [event-type]",
        examples=["/nexus unsubscribe pr-merged"],
    ),
    BotCommand(
        name="link",
        description="Link Slack/Teams account to NexusAI",
        usage="/nexus link",
        requires_auth=False,
    ),
    BotCommand(
        name="unlink",
        description="Unlink Slack/Teams account from NexusAI",
        usage="/nexus unlink",
    ),
]
