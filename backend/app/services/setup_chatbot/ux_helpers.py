"""UX Helpers - Typing indicators, error recovery, and contextual help."""

import random
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Callable
import logging

logger = logging.getLogger(__name__)


# ===================
# Typing Indicators
# ===================

class TypingState(str, Enum):
    """States for typing indicator."""
    IDLE = "idle"
    TYPING = "typing"
    PROCESSING = "processing"
    THINKING = "thinking"
    ERROR = "error"


@dataclass
class TypingIndicator:
    """Represents a typing indicator state."""
    state: TypingState = TypingState.IDLE
    message: str | None = None
    started_at: datetime | None = None
    estimated_duration_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "state": self.state.value,
            "message": self.message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "estimated_duration_ms": self.estimated_duration_ms,
        }


class TypingIndicatorManager:
    """Manages typing indicators for sessions."""

    # Messages for different states
    STATE_MESSAGES = {
        TypingState.TYPING: [
            "Typing...",
            "Composing response...",
        ],
        TypingState.PROCESSING: [
            "Processing your request...",
            "Working on it...",
            "Just a moment...",
        ],
        TypingState.THINKING: [
            "Thinking...",
            "Analyzing...",
            "Considering options...",
        ],
        TypingState.ERROR: [
            "Something went wrong...",
            "Oops, let me try again...",
        ],
    }

    # Estimated durations (ms) for different operations
    OPERATION_DURATIONS = {
        "simple_response": 500,
        "api_call": 2000,
        "connection_test": 5000,
        "data_sync": 10000,
        "llm_response": 3000,
    }

    def __init__(self):
        self._indicators: dict[str, TypingIndicator] = {}
        self._callbacks: dict[str, list[Callable]] = {}

    def start_typing(
        self,
        session_id: str,
        state: TypingState = TypingState.TYPING,
        operation: str = "simple_response",
        custom_message: str | None = None,
    ) -> TypingIndicator:
        """Start a typing indicator for a session."""
        message = custom_message or random.choice(self.STATE_MESSAGES.get(state, ["..."]))
        duration = self.OPERATION_DURATIONS.get(operation, 1000)

        indicator = TypingIndicator(
            state=state,
            message=message,
            started_at=datetime.now(UTC),
            estimated_duration_ms=duration,
        )

        self._indicators[session_id] = indicator
        self._notify_callbacks(session_id, indicator)

        return indicator

    def update_state(
        self,
        session_id: str,
        state: TypingState,
        message: str | None = None,
    ) -> TypingIndicator | None:
        """Update the typing indicator state."""
        indicator = self._indicators.get(session_id)
        if not indicator:
            return None

        indicator.state = state
        if message:
            indicator.message = message
        elif state in self.STATE_MESSAGES:
            indicator.message = random.choice(self.STATE_MESSAGES[state])

        self._notify_callbacks(session_id, indicator)
        return indicator

    def stop_typing(self, session_id: str) -> None:
        """Stop the typing indicator for a session."""
        indicator = TypingIndicator(state=TypingState.IDLE)
        self._indicators[session_id] = indicator
        self._notify_callbacks(session_id, indicator)

    def get_indicator(self, session_id: str) -> TypingIndicator:
        """Get the current typing indicator for a session."""
        return self._indicators.get(session_id, TypingIndicator())

    def register_callback(
        self,
        session_id: str,
        callback: Callable[[TypingIndicator], None],
    ) -> None:
        """Register a callback for typing indicator updates."""
        if session_id not in self._callbacks:
            self._callbacks[session_id] = []
        self._callbacks[session_id].append(callback)

    def unregister_callbacks(self, session_id: str) -> None:
        """Remove all callbacks for a session."""
        self._callbacks.pop(session_id, None)

    def _notify_callbacks(self, session_id: str, indicator: TypingIndicator) -> None:
        """Notify all registered callbacks."""
        for callback in self._callbacks.get(session_id, []):
            try:
                callback(indicator)
            except Exception as e:
                logger.error(f"Typing indicator callback error: {e}")


# Singleton typing indicator manager
typing_indicator_manager = TypingIndicatorManager()


# ===================
# Error Recovery
# ===================

class ErrorType(str, Enum):
    """Types of errors that can occur."""
    NETWORK = "network"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    PERMISSION = "permission"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    SERVER = "server"
    UNKNOWN = "unknown"


@dataclass
class RecoveryAction:
    """A suggested action for error recovery."""
    action_type: str  # retry, redirect, reset, contact_support, etc.
    label: str
    description: str
    value: str  # Quick reply value
    icon: str = "🔄"
    is_recommended: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "action_type": self.action_type,
            "label": self.label,
            "description": self.description,
            "value": self.value,
            "icon": self.icon,
            "is_recommended": self.is_recommended,
        }


@dataclass
class ErrorRecoveryInfo:
    """Error recovery information."""
    error_type: ErrorType
    message: str
    user_friendly_message: str
    recovery_actions: list[RecoveryAction] = field(default_factory=list)
    retry_after_seconds: int = 0
    is_retryable: bool = True
    technical_details: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "error_type": self.error_type.value,
            "message": self.message,
            "user_friendly_message": self.user_friendly_message,
            "recovery_actions": [a.to_dict() for a in self.recovery_actions],
            "retry_after_seconds": self.retry_after_seconds,
            "is_retryable": self.is_retryable,
        }


class ErrorRecoveryHelper:
    """Helps with error recovery and user-friendly error messages."""

    # User-friendly messages for error types
    ERROR_MESSAGES = {
        ErrorType.NETWORK: "We're having trouble connecting. Please check your internet connection.",
        ErrorType.TIMEOUT: "The operation took too long. Let's try again.",
        ErrorType.RATE_LIMIT: "You're moving too fast! Please wait a moment before trying again.",
        ErrorType.VALIDATION: "Some of the information provided isn't quite right.",
        ErrorType.AUTHENTICATION: "There was an issue with your credentials. Please verify them and try again.",
        ErrorType.PERMISSION: "You don't have permission to perform this action.",
        ErrorType.NOT_FOUND: "We couldn't find what you're looking for.",
        ErrorType.CONFLICT: "This conflicts with existing data. Let's resolve this.",
        ErrorType.SERVER: "Something went wrong on our end. We're working on it!",
        ErrorType.UNKNOWN: "Something unexpected happened. Let's try again.",
    }

    # Default recovery actions for each error type
    DEFAULT_RECOVERY_ACTIONS = {
        ErrorType.NETWORK: [
            RecoveryAction(
                action_type="retry",
                label="Try Again",
                description="Retry the last action",
                value="__retry__",
                icon="🔄",
                is_recommended=True,
            ),
            RecoveryAction(
                action_type="reset",
                label="Start Over",
                description="Reset and start fresh",
                value="__reset__",
                icon="🔁",
            ),
        ],
        ErrorType.TIMEOUT: [
            RecoveryAction(
                action_type="retry",
                label="Try Again",
                description="Retry the operation",
                value="__retry__",
                icon="🔄",
                is_recommended=True,
            ),
            RecoveryAction(
                action_type="skip",
                label="Skip This Step",
                description="Continue without this step",
                value="__skip__",
                icon="⏭️",
            ),
        ],
        ErrorType.RATE_LIMIT: [
            RecoveryAction(
                action_type="wait",
                label="Wait and Retry",
                description="Wait briefly and try again",
                value="__wait_retry__",
                icon="⏳",
                is_recommended=True,
            ),
        ],
        ErrorType.VALIDATION: [
            RecoveryAction(
                action_type="edit",
                label="Edit Input",
                description="Correct the input and try again",
                value="__edit__",
                icon="✏️",
                is_recommended=True,
            ),
            RecoveryAction(
                action_type="help",
                label="Get Help",
                description="Show format requirements",
                value="__show_format_help__",
                icon="❓",
            ),
        ],
        ErrorType.AUTHENTICATION: [
            RecoveryAction(
                action_type="re_enter",
                label="Re-enter Credentials",
                description="Enter your credentials again",
                value="__re_enter_credentials__",
                icon="🔑",
                is_recommended=True,
            ),
            RecoveryAction(
                action_type="help",
                label="Get Help",
                description="Learn how to generate credentials",
                value="__credential_help__",
                icon="❓",
            ),
        ],
        ErrorType.PERMISSION: [
            RecoveryAction(
                action_type="help",
                label="Learn More",
                description="Understand required permissions",
                value="__permission_help__",
                icon="📖",
                is_recommended=True,
            ),
            RecoveryAction(
                action_type="cancel",
                label="Cancel",
                description="Cancel this operation",
                value="__cancel__",
                icon="❌",
            ),
        ],
        ErrorType.NOT_FOUND: [
            RecoveryAction(
                action_type="retry",
                label="Try Again",
                description="Search again",
                value="__retry__",
                icon="🔍",
            ),
            RecoveryAction(
                action_type="create",
                label="Create New",
                description="Create what you're looking for",
                value="__create_new__",
                icon="➕",
                is_recommended=True,
            ),
        ],
        ErrorType.CONFLICT: [
            RecoveryAction(
                action_type="rename",
                label="Use Different Name",
                description="Choose a different name",
                value="__rename__",
                icon="✏️",
                is_recommended=True,
            ),
            RecoveryAction(
                action_type="replace",
                label="Replace Existing",
                description="Replace the existing item",
                value="__replace__",
                icon="🔄",
            ),
        ],
        ErrorType.SERVER: [
            RecoveryAction(
                action_type="retry",
                label="Try Again",
                description="Retry the operation",
                value="__retry__",
                icon="🔄",
                is_recommended=True,
            ),
            RecoveryAction(
                action_type="contact",
                label="Contact Support",
                description="Get help from support",
                value="__contact_support__",
                icon="💬",
            ),
        ],
        ErrorType.UNKNOWN: [
            RecoveryAction(
                action_type="retry",
                label="Try Again",
                description="Retry the operation",
                value="__retry__",
                icon="🔄",
                is_recommended=True,
            ),
            RecoveryAction(
                action_type="reset",
                label="Start Over",
                description="Reset and start fresh",
                value="__reset__",
                icon="🔁",
            ),
        ],
    }

    def classify_error(self, error: Exception) -> ErrorType:
        """Classify an exception into an error type."""
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()

        # Network errors
        if any(x in error_str for x in ["connection", "network", "dns", "socket"]):
            return ErrorType.NETWORK

        # Timeout errors
        if "timeout" in error_str or "timed out" in error_str:
            return ErrorType.TIMEOUT

        # Rate limit errors
        if "rate" in error_str and "limit" in error_str:
            return ErrorType.RATE_LIMIT

        # Validation errors
        if any(x in error_str for x in ["validation", "invalid", "format", "required"]):
            return ErrorType.VALIDATION

        # Authentication errors
        if any(x in error_str for x in ["auth", "credential", "unauthorized", "401"]):
            return ErrorType.AUTHENTICATION

        # Permission errors
        if any(x in error_str for x in ["permission", "forbidden", "403", "access denied"]):
            return ErrorType.PERMISSION

        # Not found errors
        if any(x in error_str for x in ["not found", "404", "does not exist"]):
            return ErrorType.NOT_FOUND

        # Conflict errors
        if any(x in error_str for x in ["conflict", "409", "already exists", "duplicate"]):
            return ErrorType.CONFLICT

        # Server errors
        if any(x in error_str for x in ["server", "500", "502", "503", "internal"]):
            return ErrorType.SERVER

        return ErrorType.UNKNOWN

    def get_recovery_info(
        self,
        error: Exception,
        context: dict[str, Any] | None = None,
    ) -> ErrorRecoveryInfo:
        """Get recovery information for an error."""
        error_type = self.classify_error(error)

        user_message = self.ERROR_MESSAGES.get(error_type, self.ERROR_MESSAGES[ErrorType.UNKNOWN])
        recovery_actions = self.DEFAULT_RECOVERY_ACTIONS.get(
            error_type,
            self.DEFAULT_RECOVERY_ACTIONS[ErrorType.UNKNOWN]
        ).copy()

        # Customize based on context
        if context:
            if context.get("step") and error_type == ErrorType.VALIDATION:
                user_message = f"{user_message} Please check the {context['step']} field."

            if context.get("retry_after"):
                return ErrorRecoveryInfo(
                    error_type=error_type,
                    message=str(error),
                    user_friendly_message=user_message,
                    recovery_actions=recovery_actions,
                    retry_after_seconds=context["retry_after"],
                    is_retryable=True,
                    technical_details=str(error),
                )

        is_retryable = error_type not in (ErrorType.PERMISSION, ErrorType.CONFLICT)

        return ErrorRecoveryInfo(
            error_type=error_type,
            message=str(error),
            user_friendly_message=user_message,
            recovery_actions=recovery_actions,
            is_retryable=is_retryable,
            technical_details=str(error),
        )

    def format_error_message(
        self,
        recovery_info: ErrorRecoveryInfo,
        include_actions: bool = True,
    ) -> str:
        """Format an error message for display."""
        message = f"⚠️ {recovery_info.user_friendly_message}"

        if recovery_info.retry_after_seconds > 0:
            message += f"\n\n⏳ Please wait {recovery_info.retry_after_seconds} seconds before trying again."

        if include_actions and recovery_info.recovery_actions:
            message += "\n\nHere's what you can do:"
            for action in recovery_info.recovery_actions:
                recommended = " (recommended)" if action.is_recommended else ""
                message += f"\n• {action.icon} **{action.label}**{recommended}: {action.description}"

        return message


# Singleton error recovery helper
error_recovery_helper = ErrorRecoveryHelper()


# ===================
# Contextual Help
# ===================

@dataclass
class HelpTopic:
    """A help topic."""
    topic_id: str
    title: str
    summary: str
    content: str
    keywords: list[str] = field(default_factory=list)
    related_topics: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)


class ContextualHelpSystem:
    """Provides contextual help based on user actions and state."""

    def __init__(self):
        self._topics: dict[str, HelpTopic] = {}
        self._load_default_topics()

    def _load_default_topics(self) -> None:
        """Load default help topics."""
        topics = [
            HelpTopic(
                topic_id="github_token",
                title="GitHub Personal Access Token",
                summary="How to create and use a GitHub Personal Access Token",
                content="""
A **Personal Access Token (PAT)** is like a password that lets DevLake access your GitHub data.

**How to create one:**
1. Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Give it a name like "DevLake Integration"
4. Select these scopes: `repo`, `read:org`, `read:user`
5. Click "Generate token"
6. Copy the token immediately (you won't see it again!)

**Security tips:**
• Never share your token with anyone
• Set an expiration date
• Use the minimum required scopes
• Revoke tokens you no longer need
                """,
                keywords=["github", "token", "pat", "access", "authentication", "credentials"],
                related_topics=["github_scopes", "connection_testing"],
                examples=["ghp_example_token"],
            ),
            HelpTopic(
                topic_id="github_scopes",
                title="GitHub Token Scopes",
                summary="Understanding GitHub token permissions",
                content="""
**Required scopes for DevLake:**

• **repo** - Access to private repositories and their data
• **read:org** - Read organization membership and team data
• **read:user** - Read user profile data

**Optional scopes:**
• **admin:repo_hook** - Needed if you want webhook-based updates
• **workflow** - Access to GitHub Actions workflow data

**Tip:** Only grant the minimum permissions needed!
                """,
                keywords=["github", "scope", "permission", "access"],
                related_topics=["github_token"],
            ),
            HelpTopic(
                topic_id="jira_token",
                title="Jira API Token",
                summary="How to create and use a Jira API Token",
                content="""
**Creating a Jira API Token:**

1. Go to Atlassian Account → Security → Create and manage API tokens
2. Click "Create API token"
3. Enter a label like "DevLake Integration"
4. Copy the generated token

**What you'll need:**
• Your Jira Cloud URL (e.g., `https://yourcompany.atlassian.net`)
• Your email address
• The API token you just created

**Note:** For Jira Server/Data Center, the process may be different.
                """,
                keywords=["jira", "token", "api", "atlassian", "authentication"],
                related_topics=["jira_cloud_vs_server"],
            ),
            HelpTopic(
                topic_id="connection_testing",
                title="Testing Connections",
                summary="How connection testing works",
                content="""
**Why test connections?**

Testing verifies that:
• Your credentials are correct
• DevLake can reach your data source
• You have the right permissions

**What happens during a test:**
1. DevLake attempts to connect using your credentials
2. It makes a simple API call to verify access
3. You'll see success ✅ or failure ❌ with details

**If the test fails:**
• Check your credentials are correct
• Verify the endpoint URL (if applicable)
• Ensure your token has the required permissions
• Check your network connection
                """,
                keywords=["test", "connection", "verify", "check"],
                related_topics=["github_token", "jira_token"],
            ),
            HelpTopic(
                topic_id="dora_metrics",
                title="DORA Metrics Explained",
                summary="Understanding the four key DORA metrics",
                content="""
**DORA metrics** measure software delivery performance:

📊 **Deployment Frequency**
How often you deploy to production. Elite teams deploy multiple times per day.

⏱️ **Lead Time for Changes**
Time from code commit to production. Elite teams achieve less than 1 hour.

🔄 **Mean Time to Recovery (MTTR)**
How quickly you recover from failures. Elite teams recover in less than 1 hour.

❌ **Change Failure Rate**
Percentage of deployments causing failures. Elite teams have less than 15%.

**Why track these?**
These metrics help you identify bottlenecks and measure improvement over time.
                """,
                keywords=["dora", "metrics", "devops", "performance", "deployment"],
                related_topics=["project_setup"],
            ),
            HelpTopic(
                topic_id="project_setup",
                title="Setting Up a Project",
                summary="How to create and configure a DevLake project",
                content="""
**What is a DevLake Project?**

A project organizes your data sources and metrics. Think of it as a container for:
• Data source connections
• DORA metrics tracking
• Dashboards and reports

**Best practices:**
• Create one project per product or team
• Use descriptive names (e.g., "Mobile App", "Backend Services")
• Enable DORA metrics tracking for visibility

**After creating a project:**
1. Add data source connections
2. Configure data scopes (repos, projects, etc.)
3. Set up automated data collection
                """,
                keywords=["project", "setup", "create", "configure"],
                related_topics=["dora_metrics", "pipeline_setup"],
            ),
            HelpTopic(
                topic_id="pipeline_setup",
                title="Data Collection Pipelines",
                summary="How to set up automated data collection",
                content="""
**What is a Pipeline?**

A pipeline automatically syncs data from your connected sources.

**Schedule options:**
• Manual - Run on demand
• Hourly - Every hour
• Daily - Once per day (recommended)
• Weekly - Once per week
• Custom - Use cron expressions

**Sync modes:**
• **Incremental** - Only fetch new data (faster)
• **Full Sync** - Re-fetch everything (more complete)

**Tips:**
• Start with daily incremental syncs
• Use full sync occasionally to ensure data consistency
• Monitor sync duration and adjust as needed
                """,
                keywords=["pipeline", "sync", "schedule", "data", "collection", "cron"],
                related_topics=["project_setup"],
            ),
        ]

        for topic in topics:
            self._topics[topic.topic_id] = topic

    def get_topic(self, topic_id: str) -> HelpTopic | None:
        """Get a help topic by ID."""
        return self._topics.get(topic_id)

    def search_topics(self, query: str, limit: int = 5) -> list[HelpTopic]:
        """Search help topics by keyword."""
        query_lower = query.lower()
        scored_topics = []

        for topic in self._topics.values():
            score = 0

            # Title match (highest weight)
            if query_lower in topic.title.lower():
                score += 10

            # Summary match
            if query_lower in topic.summary.lower():
                score += 5

            # Keyword match
            for keyword in topic.keywords:
                if query_lower in keyword.lower() or keyword.lower() in query_lower:
                    score += 3

            # Content match
            if query_lower in topic.content.lower():
                score += 1

            if score > 0:
                scored_topics.append((score, topic))

        # Sort by score and return top results
        scored_topics.sort(key=lambda x: x[0], reverse=True)
        return [topic for _, topic in scored_topics[:limit]]

    def get_contextual_help(
        self,
        current_step: str | None = None,
        plugin: str | None = None,
        error_type: ErrorType | None = None,
    ) -> list[HelpTopic]:
        """Get help topics based on current context."""
        topics = []

        # Help based on current step
        step_to_topics = {
            "enter_credentials": ["github_token", "jira_token"],
            "test_connection": ["connection_testing"],
            "configure_dora": ["dora_metrics"],
            "select_project": ["project_setup"],
            "configure_schedule": ["pipeline_setup"],
        }

        if current_step and current_step in step_to_topics:
            for topic_id in step_to_topics[current_step]:
                topic = self._topics.get(topic_id)
                if topic:
                    topics.append(topic)

        # Plugin-specific help
        plugin_to_topics = {
            "github": ["github_token", "github_scopes"],
            "jira": ["jira_token"],
        }

        if plugin and plugin in plugin_to_topics:
            for topic_id in plugin_to_topics[plugin]:
                topic = self._topics.get(topic_id)
                if topic and topic not in topics:
                    topics.append(topic)

        # Error-specific help
        error_to_topics = {
            ErrorType.AUTHENTICATION: ["github_token", "jira_token", "connection_testing"],
            ErrorType.VALIDATION: ["github_token", "jira_token"],
        }

        if error_type and error_type in error_to_topics:
            for topic_id in error_to_topics[error_type]:
                topic = self._topics.get(topic_id)
                if topic and topic not in topics:
                    topics.append(topic)

        return topics[:3]  # Limit to 3 topics

    def format_help_message(
        self,
        topic: HelpTopic,
        include_examples: bool = True,
        include_related: bool = True,
    ) -> str:
        """Format a help topic for display."""
        message = f"## {topic.title}\n\n{topic.content}"

        if include_examples and topic.examples:
            message += "\n\n**Examples:**"
            for example in topic.examples:
                message += f"\n• `{example}`"

        if include_related and topic.related_topics:
            related = [
                self._topics.get(tid)
                for tid in topic.related_topics
                if tid in self._topics
            ]
            if related:
                message += "\n\n**Related topics:**"
                for r in related:
                    if r:
                        message += f"\n• {r.title}"

        return message

    def get_quick_tip(self, context: dict[str, Any]) -> str | None:
        """Get a quick tip based on context."""
        tips = {
            "credential_entry": "💡 Tip: Never share your tokens with anyone. They're like passwords!",
            "connection_test": "💡 Tip: If the test fails, double-check your credentials and network connection.",
            "project_naming": "💡 Tip: Use descriptive names like 'Mobile Team' or 'Backend Services'.",
            "schedule_selection": "💡 Tip: Daily syncs are a good balance between freshness and system load.",
            "first_connection": "💡 Tip: Start with your primary source control (like GitHub) first.",
        }

        step = context.get("step")
        if step:
            tip_key = {
                "enter_credentials": "credential_entry",
                "test_connection": "connection_test",
                "enter_name": "project_naming",
                "configure_schedule": "schedule_selection",
            }.get(step)

            if tip_key:
                return tips.get(tip_key)

        if context.get("is_first_connection"):
            return tips["first_connection"]

        return None


# Singleton contextual help system
contextual_help = ContextualHelpSystem()


# ===================
# Progress Tracking
# ===================

@dataclass
class ProgressInfo:
    """Progress information for multi-step flows."""
    current_step: int
    total_steps: int
    step_name: str
    completed_steps: list[str] = field(default_factory=list)
    remaining_steps: list[str] = field(default_factory=list)
    estimated_time_remaining_seconds: int = 0

    @property
    def percentage(self) -> float:
        """Get completion percentage."""
        if self.total_steps == 0:
            return 0
        return (self.current_step / self.total_steps) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "step_name": self.step_name,
            "percentage": self.percentage,
            "completed_steps": self.completed_steps,
            "remaining_steps": self.remaining_steps,
            "estimated_time_remaining_seconds": self.estimated_time_remaining_seconds,
        }


def calculate_progress(
    flow_steps: list[str],
    current_step: str,
    step_durations: dict[str, int] | None = None,
) -> ProgressInfo:
    """Calculate progress information for a flow."""
    try:
        current_index = flow_steps.index(current_step)
    except ValueError:
        current_index = 0

    completed = flow_steps[:current_index]
    remaining = flow_steps[current_index + 1:]

    # Estimate remaining time
    estimated_time = 0
    if step_durations:
        for step in remaining:
            estimated_time += step_durations.get(step, 30)  # Default 30s per step

    return ProgressInfo(
        current_step=current_index + 1,
        total_steps=len(flow_steps),
        step_name=current_step,
        completed_steps=completed,
        remaining_steps=remaining,
        estimated_time_remaining_seconds=estimated_time,
    )
