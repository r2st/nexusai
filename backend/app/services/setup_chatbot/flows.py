"""Setup Flows - State machine based conversation flows."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from app.services.setup_chatbot.schemas import (
    ActionType,
    ChatMessage,
    ConnectionConfig,
    PLUGIN_CONFIGS,
    PluginConfig,
    QuickReply,
    SetupAction,
    SetupSession,
)


class FlowState(str, Enum):
    """States for setup flows."""

    # Common states
    INIT = "init"
    WAITING_INPUT = "waiting_input"
    VALIDATING = "validating"
    PROCESSING = "processing"
    CONFIRMING = "confirming"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class FlowStep:
    """A step in a setup flow."""

    name: str
    prompt: str
    field_name: str | None = None
    field_type: str = "text"  # text, select, multiselect, password, number, boolean
    options: list[dict[str, Any]] | None = None
    required: bool = True
    default: Any = None
    validator: Callable[[Any], tuple[bool, str | None]] | None = None
    help_text: str | None = None
    examples: list[str] | None = None
    next_step: str | None = None
    conditional_next: Callable[[dict[str, Any]], str] | None = None


class SetupFlow(ABC):
    """Base class for setup flows."""

    def __init__(self):
        self.steps: dict[str, FlowStep] = {}
        self.initial_step: str = ""
        self._build_steps()

    @abstractmethod
    def _build_steps(self) -> None:
        """Build the flow steps."""
        pass

    @abstractmethod
    def get_intro_message(self) -> ChatMessage:
        """Get the introduction message for this flow."""
        pass

    def get_step(self, step_name: str) -> FlowStep | None:
        """Get a step by name."""
        return self.steps.get(step_name)

    def get_next_step(self, current_step: str, data: dict[str, Any]) -> str | None:
        """Get the next step based on current state and data."""
        step = self.steps.get(current_step)
        if not step:
            return None

        if step.conditional_next:
            return step.conditional_next(data)
        return step.next_step

    def validate_step(
        self, step_name: str, value: Any
    ) -> tuple[bool, str | None]:
        """Validate input for a step."""
        step = self.steps.get(step_name)
        if not step:
            return False, f"Unknown step: {step_name}"

        # Check required
        if step.required and (value is None or value == ""):
            return False, f"{step.field_name or step_name} is required"

        # Run custom validator
        if step.validator:
            return step.validator(value)

        return True, None

    def create_step_message(
        self,
        step: FlowStep,
        step_number: int,
        total_steps: int,
        collected_data: dict[str, Any],
    ) -> ChatMessage:
        """Create a message for a step."""
        content = step.prompt

        # Add help text
        if step.help_text:
            content += f"\n\n💡 {step.help_text}"

        # Add examples
        if step.examples:
            examples_text = ", ".join(f"`{e}`" for e in step.examples[:3])
            content += f"\n\n📝 Examples: {examples_text}"

        # Create quick replies for select fields
        quick_replies = []
        if step.field_type == "select" and step.options:
            for opt in step.options:
                quick_replies.append(
                    QuickReply(
                        label=opt.get("label", opt.get("value")),
                        value=opt.get("value"),
                        icon=opt.get("icon"),
                        description=opt.get("description"),
                    )
                )

        # Add cancel option
        quick_replies.append(
            QuickReply(
                label="Cancel",
                value="__cancel__",
                icon="❌",
                description="Cancel this setup",
            )
        )

        return ChatMessage(
            role="assistant",
            content=content,
            quick_replies=quick_replies,
            step_number=step_number,
            total_steps=total_steps,
            progress_percent=(step_number / total_steps) * 100,
        )


class ConnectionSetupFlow(SetupFlow):
    """Flow for setting up a data source connection."""

    def __init__(self, plugin: str | None = None):
        self.selected_plugin = plugin
        super().__init__()

    def _build_steps(self) -> None:
        """Build connection setup steps."""

        # Step 1: Select plugin (if not pre-selected)
        if not self.selected_plugin:
            plugin_options = [
                {
                    "value": key,
                    "label": config.display_name,
                    "icon": config.icon,
                    "description": config.description,
                }
                for key, config in PLUGIN_CONFIGS.items()
            ]

            self.steps["select_plugin"] = FlowStep(
                name="select_plugin",
                prompt="Which data source would you like to connect?",
                field_name="plugin",
                field_type="select",
                options=plugin_options,
                next_step="enter_name",
            )
            self.initial_step = "select_plugin"
        else:
            self.initial_step = "enter_name"

        # Step 2: Connection name
        self.steps["enter_name"] = FlowStep(
            name="enter_name",
            prompt="What would you like to name this connection?",
            field_name="name",
            field_type="text",
            help_text="Choose a descriptive name to identify this connection",
            examples=["Production GitHub", "Dev Jira", "Main Jenkins"],
            validator=self._validate_name,
            next_step="enter_credentials",
        )

        # Step 3: Enter credentials (dynamic based on plugin)
        self.steps["enter_credentials"] = FlowStep(
            name="enter_credentials",
            prompt=self._get_credentials_prompt,
            field_name="credentials",
            field_type="text",
            next_step="enter_endpoint",
            conditional_next=self._next_after_credentials,
        )

        # Step 4: Enter endpoint (if required)
        self.steps["enter_endpoint"] = FlowStep(
            name="enter_endpoint",
            prompt=self._get_endpoint_prompt,
            field_name="endpoint",
            field_type="text",
            required=False,
            conditional_next=self._next_after_endpoint,
        )

        # Step 5: Test connection
        self.steps["test_connection"] = FlowStep(
            name="test_connection",
            prompt="Would you like me to test the connection now?",
            field_name="do_test",
            field_type="select",
            options=[
                {"value": "yes", "label": "Yes, test it", "icon": "✅"},
                {"value": "no", "label": "Skip test", "icon": "⏭️"},
            ],
            next_step="confirm",
        )

        # Step 6: Confirm and create
        self.steps["confirm"] = FlowStep(
            name="confirm",
            prompt=self._get_confirmation_prompt,
            field_name="confirmed",
            field_type="select",
            options=[
                {"value": "yes", "label": "Create connection", "icon": "✅"},
                {"value": "edit", "label": "Edit details", "icon": "✏️"},
                {"value": "no", "label": "Cancel", "icon": "❌"},
            ],
            conditional_next=self._next_after_confirm,
        )

        # Step 7: Success / select scopes
        self.steps["select_scopes"] = FlowStep(
            name="select_scopes",
            prompt="Would you like to add data scopes (repositories, projects, etc.) now?",
            field_name="add_scopes",
            field_type="select",
            options=[
                {"value": "yes", "label": "Add scopes now", "icon": "📦"},
                {"value": "later", "label": "Do it later", "icon": "⏰"},
            ],
            next_step="complete",
        )

        # Complete
        self.steps["complete"] = FlowStep(
            name="complete",
            prompt="🎉 Connection created successfully!",
            field_name=None,
            field_type="text",
            required=False,
        )

    def _validate_name(self, value: str) -> tuple[bool, str | None]:
        """Validate connection name."""
        if not value or len(value.strip()) < 2:
            return False, "Name must be at least 2 characters"
        if len(value) > 100:
            return False, "Name must be less than 100 characters"
        return True, None

    def _get_credentials_prompt(self, data: dict[str, Any]) -> str:
        """Get credentials prompt based on selected plugin."""
        plugin = data.get("plugin", self.selected_plugin)
        config = PLUGIN_CONFIGS.get(plugin)

        if not config:
            return "Please enter your authentication credentials:"

        prompts = []
        for field in config.required_fields:
            desc = config.field_descriptions.get(field, field)
            example = config.field_examples.get(field, "")
            prompt = f"• **{field.replace('_', ' ').title()}**: {desc}"
            if example:
                prompt += f"\n  Example: `{example}`"
            prompts.append(prompt)

        return f"Please provide the following credentials for {config.display_name}:\n\n" + "\n\n".join(prompts)

    def _get_endpoint_prompt(self, data: dict[str, Any]) -> str:
        """Get endpoint prompt based on selected plugin."""
        plugin = data.get("plugin", self.selected_plugin)
        config = PLUGIN_CONFIGS.get(plugin)

        if not config:
            return "Enter the API endpoint URL:"

        if not config.endpoint_required:
            return f"Enter a custom API endpoint (optional, uses default {plugin} API):"

        desc = config.field_descriptions.get("endpoint", "API endpoint URL")
        example = config.field_examples.get("endpoint", "")
        prompt = f"{desc}"
        if example:
            prompt += f"\n\n📝 Example: `{example}`"
        return prompt

    def _next_after_credentials(self, data: dict[str, Any]) -> str:
        """Determine next step after credentials."""
        plugin = data.get("plugin", self.selected_plugin)
        config = PLUGIN_CONFIGS.get(plugin)

        if config and not config.endpoint_required:
            return "test_connection"
        return "enter_endpoint"

    def _next_after_endpoint(self, data: dict[str, Any]) -> str:
        """Determine next step after endpoint."""
        return "test_connection"

    def _get_confirmation_prompt(self, data: dict[str, Any]) -> str:
        """Get confirmation prompt with summary."""
        plugin = data.get("plugin", self.selected_plugin)
        config = PLUGIN_CONFIGS.get(plugin)
        name = data.get("name", "Unnamed")

        summary = f"""
Please confirm the connection details:

📦 **Connection Type**: {config.display_name if config else plugin}
📝 **Name**: {name}
"""
        if data.get("endpoint"):
            summary += f"🔗 **Endpoint**: {data['endpoint']}\n"

        summary += "\nWould you like to create this connection?"
        return summary

    def _next_after_confirm(self, data: dict[str, Any]) -> str:
        """Determine next step after confirmation."""
        confirmed = data.get("confirmed")
        if confirmed == "yes":
            return "select_scopes"
        elif confirmed == "edit":
            return "enter_name"  # Go back to start
        return "cancelled"

    def get_intro_message(self) -> ChatMessage:
        """Get intro message for connection setup."""
        if self.selected_plugin:
            config = PLUGIN_CONFIGS.get(self.selected_plugin)
            content = f"Let's set up a new **{config.display_name if config else self.selected_plugin}** connection! I'll guide you through the process step by step."
        else:
            content = "Let's set up a new data source connection! I'll help you connect to your development tools like GitHub, Jira, Jenkins, and more."

        return ChatMessage(
            role="assistant",
            content=content,
            quick_replies=[
                QuickReply(
                    label="Let's start",
                    value="__start__",
                    icon="🚀",
                ),
                QuickReply(
                    label="Show all options",
                    value="__show_options__",
                    icon="📋",
                ),
            ],
        )


class ProjectSetupFlow(SetupFlow):
    """Flow for setting up a DevLake project."""

    def _build_steps(self) -> None:
        """Build project setup steps."""

        # Step 1: Project name
        self.steps["enter_name"] = FlowStep(
            name="enter_name",
            prompt="What would you like to name this project?",
            field_name="name",
            field_type="text",
            help_text="This will be the main identifier for your project in DevLake",
            examples=["my-app", "platform-team", "e-commerce-backend"],
            validator=self._validate_name,
            next_step="enter_description",
        )
        self.initial_step = "enter_name"

        # Step 2: Description
        self.steps["enter_description"] = FlowStep(
            name="enter_description",
            prompt="Add a description for this project (optional):",
            field_name="description",
            field_type="text",
            required=False,
            help_text="A brief description to help identify this project",
            next_step="select_connections",
        )

        # Step 3: Select connections
        self.steps["select_connections"] = FlowStep(
            name="select_connections",
            prompt="Would you like to add data source connections to this project?",
            field_name="add_connections",
            field_type="select",
            options=[
                {"value": "new", "label": "Create new connection", "icon": "➕"},
                {"value": "existing", "label": "Use existing connections", "icon": "🔗"},
                {"value": "later", "label": "Set up later", "icon": "⏰"},
            ],
            conditional_next=self._next_after_connections,
        )

        # Step 4: Select DORA metrics
        self.steps["configure_dora"] = FlowStep(
            name="configure_dora",
            prompt="Would you like to enable DORA metrics tracking for this project?",
            field_name="enable_dora",
            field_type="select",
            options=[
                {"value": "yes", "label": "Yes, enable DORA metrics", "icon": "📊"},
                {"value": "no", "label": "Not now", "icon": "⏭️"},
            ],
            next_step="confirm",
        )

        # Step 5: Confirm
        self.steps["confirm"] = FlowStep(
            name="confirm",
            prompt=self._get_confirmation_prompt,
            field_name="confirmed",
            field_type="select",
            options=[
                {"value": "yes", "label": "Create project", "icon": "✅"},
                {"value": "edit", "label": "Edit details", "icon": "✏️"},
                {"value": "no", "label": "Cancel", "icon": "❌"},
            ],
            conditional_next=self._next_after_confirm,
        )

        # Complete
        self.steps["complete"] = FlowStep(
            name="complete",
            prompt="🎉 Project created successfully!",
            field_name=None,
            field_type="text",
            required=False,
        )

    def _validate_name(self, value: str) -> tuple[bool, str | None]:
        """Validate project name."""
        if not value or len(value.strip()) < 2:
            return False, "Name must be at least 2 characters"
        if len(value) > 100:
            return False, "Name must be less than 100 characters"
        # Check for valid characters
        import re
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9\-_]*$', value):
            return False, "Name must start with a letter/number and contain only letters, numbers, hyphens, and underscores"
        return True, None

    def _next_after_connections(self, data: dict[str, Any]) -> str:
        """Determine next step after connection selection."""
        choice = data.get("add_connections")
        if choice == "new":
            return "__start_connection_flow__"  # Special marker to start nested flow
        return "configure_dora"

    def _get_confirmation_prompt(self, data: dict[str, Any]) -> str:
        """Get confirmation prompt with summary."""
        name = data.get("name", "Unnamed")
        description = data.get("description", "No description")
        enable_dora = data.get("enable_dora") == "yes"

        return f"""
Please confirm the project details:

📦 **Name**: {name}
📝 **Description**: {description}
📊 **DORA Metrics**: {'Enabled' if enable_dora else 'Disabled'}

Would you like to create this project?
"""

    def _next_after_confirm(self, data: dict[str, Any]) -> str:
        """Determine next step after confirmation."""
        confirmed = data.get("confirmed")
        if confirmed == "yes":
            return "complete"
        elif confirmed == "edit":
            return "enter_name"
        return "cancelled"

    def get_intro_message(self) -> ChatMessage:
        """Get intro message for project setup."""
        return ChatMessage(
            role="assistant",
            content="Let's create a new DevLake project! A project helps you organize your data sources and track metrics across your development workflow.",
            quick_replies=[
                QuickReply(
                    label="Let's start",
                    value="__start__",
                    icon="🚀",
                ),
                QuickReply(
                    label="What's a project?",
                    value="__explain_project__",
                    icon="❓",
                ),
            ],
        )


class PipelineSetupFlow(SetupFlow):
    """Flow for setting up a data collection pipeline."""

    def _build_steps(self) -> None:
        """Build pipeline setup steps."""

        # Step 1: Select project
        self.steps["select_project"] = FlowStep(
            name="select_project",
            prompt="Which project should this pipeline collect data for?",
            field_name="project_id",
            field_type="select",
            options=[],  # Populated dynamically
            next_step="select_connections",
        )
        self.initial_step = "select_project"

        # Step 2: Select connections/scopes
        self.steps["select_connections"] = FlowStep(
            name="select_connections",
            prompt="Which data sources should be included in this pipeline?",
            field_name="connections",
            field_type="multiselect",
            options=[],  # Populated dynamically
            next_step="configure_schedule",
        )

        # Step 3: Configure schedule
        self.steps["configure_schedule"] = FlowStep(
            name="configure_schedule",
            prompt="How often should this pipeline run?",
            field_name="schedule",
            field_type="select",
            options=[
                {"value": "manual", "label": "Manual only", "icon": "👆"},
                {"value": "0 * * * *", "label": "Every hour", "icon": "⏰"},
                {"value": "0 */4 * * *", "label": "Every 4 hours", "icon": "🕓"},
                {"value": "0 0 * * *", "label": "Daily (midnight)", "icon": "📅"},
                {"value": "0 0 * * 0", "label": "Weekly (Sunday)", "icon": "📆"},
                {"value": "custom", "label": "Custom schedule", "icon": "⚙️"},
            ],
            conditional_next=self._next_after_schedule,
        )

        # Step 4: Custom cron (if selected)
        self.steps["enter_cron"] = FlowStep(
            name="enter_cron",
            prompt="Enter a custom cron expression:",
            field_name="custom_cron",
            field_type="text",
            help_text="Format: minute hour day-of-month month day-of-week",
            examples=["0 6 * * 1-5", "0 0 1 * *"],
            validator=self._validate_cron,
            next_step="configure_options",
        )

        # Step 5: Configure options
        self.steps["configure_options"] = FlowStep(
            name="configure_options",
            prompt="Configure collection options:",
            field_name="options",
            field_type="select",
            options=[
                {"value": "incremental", "label": "Incremental sync (faster)", "icon": "🔄"},
                {"value": "full", "label": "Full sync (complete)", "icon": "📥"},
            ],
            next_step="confirm",
        )

        # Step 6: Confirm
        self.steps["confirm"] = FlowStep(
            name="confirm",
            prompt=self._get_confirmation_prompt,
            field_name="confirmed",
            field_type="select",
            options=[
                {"value": "yes", "label": "Create pipeline", "icon": "✅"},
                {"value": "run_now", "label": "Create and run now", "icon": "▶️"},
                {"value": "no", "label": "Cancel", "icon": "❌"},
            ],
            conditional_next=self._next_after_confirm,
        )

        # Complete
        self.steps["complete"] = FlowStep(
            name="complete",
            prompt="🎉 Pipeline created successfully!",
            field_name=None,
            field_type="text",
            required=False,
        )

    def _validate_cron(self, value: str) -> tuple[bool, str | None]:
        """Validate cron expression."""
        if not value:
            return False, "Cron expression is required"

        parts = value.split()
        if len(parts) != 5:
            return False, "Cron expression must have 5 parts: minute hour day month weekday"

        return True, None

    def _next_after_schedule(self, data: dict[str, Any]) -> str:
        """Determine next step after schedule selection."""
        if data.get("schedule") == "custom":
            return "enter_cron"
        return "configure_options"

    def _get_confirmation_prompt(self, data: dict[str, Any]) -> str:
        """Get confirmation prompt with summary."""
        schedule = data.get("schedule", "manual")
        if schedule == "custom":
            schedule = data.get("custom_cron", schedule)

        schedule_labels = {
            "manual": "Manual only",
            "0 * * * *": "Every hour",
            "0 */4 * * *": "Every 4 hours",
            "0 0 * * *": "Daily",
            "0 0 * * 0": "Weekly",
        }

        options = data.get("options", "incremental")

        return f"""
Please confirm the pipeline configuration:

📦 **Project**: {data.get('project_name', 'Selected project')}
🔗 **Connections**: {len(data.get('connections', []))} data sources
⏰ **Schedule**: {schedule_labels.get(schedule, schedule)}
🔄 **Sync Mode**: {options.title()}

Would you like to create this pipeline?
"""

    def _next_after_confirm(self, data: dict[str, Any]) -> str:
        """Determine next step after confirmation."""
        confirmed = data.get("confirmed")
        if confirmed in ["yes", "run_now"]:
            return "complete"
        return "cancelled"

    def get_intro_message(self) -> ChatMessage:
        """Get intro message for pipeline setup."""
        return ChatMessage(
            role="assistant",
            content="Let's set up a data collection pipeline! Pipelines automatically sync data from your connected sources into DevLake for analysis.",
            quick_replies=[
                QuickReply(
                    label="Let's start",
                    value="__start__",
                    icon="🚀",
                ),
                QuickReply(
                    label="What's a pipeline?",
                    value="__explain_pipeline__",
                    icon="❓",
                ),
            ],
        )


class MetricsQueryFlow(SetupFlow):
    """Flow for querying and viewing metrics through conversation."""

    def _build_steps(self) -> None:
        """Build metrics query steps."""

        # Step 1: Select what to view
        self.steps["select_metric_type"] = FlowStep(
            name="select_metric_type",
            prompt="What would you like to see?",
            field_name="metric_type",
            field_type="select",
            options=[
                {"value": "dora", "label": "DORA Metrics", "icon": "📊", "description": "Deployment frequency, lead time, MTTR, change failure rate"},
                {"value": "overview", "label": "Project Overview", "icon": "📈", "description": "Summary of all projects and connections"},
                {"value": "connections", "label": "Connection Status", "icon": "🔗", "description": "Health and sync status of data sources"},
                {"value": "pipelines", "label": "Pipeline Status", "icon": "⚙️", "description": "Data collection pipeline runs"},
                {"value": "commits", "label": "Commit Activity", "icon": "💻", "description": "Code commit statistics"},
                {"value": "prs", "label": "Pull Requests", "icon": "🔀", "description": "PR metrics and review times"},
            ],
            conditional_next=self._next_after_metric_type,
        )
        self.initial_step = "select_metric_type"

        # Step 2: Select project (for project-specific metrics)
        self.steps["select_project"] = FlowStep(
            name="select_project",
            prompt="Which project would you like to see metrics for?",
            field_name="project",
            field_type="select",
            options=[],  # Populated dynamically
            next_step="select_time_range",
        )

        # Step 3: Select time range
        self.steps["select_time_range"] = FlowStep(
            name="select_time_range",
            prompt="What time period would you like to analyze?",
            field_name="time_range",
            field_type="select",
            options=[
                {"value": "7d", "label": "Last 7 days", "icon": "📅"},
                {"value": "30d", "label": "Last 30 days", "icon": "📆"},
                {"value": "90d", "label": "Last 90 days", "icon": "🗓️"},
                {"value": "1y", "label": "Last year", "icon": "📊"},
            ],
            next_step="show_metrics",
        )

        # Step 4: Show metrics (this is handled specially)
        self.steps["show_metrics"] = FlowStep(
            name="show_metrics",
            prompt="",  # Dynamic
            field_name="action",
            field_type="select",
            options=[
                {"value": "details", "label": "Show more details", "icon": "🔍"},
                {"value": "different", "label": "View different metrics", "icon": "🔄"},
                {"value": "export", "label": "Export data", "icon": "📤"},
                {"value": "done", "label": "Done", "icon": "✅"},
            ],
            conditional_next=self._next_after_action,
        )

        # Complete
        self.steps["complete"] = FlowStep(
            name="complete",
            prompt="Is there anything else you'd like to know about your metrics?",
            field_name=None,
            field_type="text",
            required=False,
        )

    def _next_after_metric_type(self, data: dict[str, Any]) -> str:
        """Determine next step after metric type selection."""
        metric_type = data.get("metric_type")
        # Overview and connections don't need project selection
        if metric_type in ["overview", "connections", "pipelines"]:
            return "show_metrics"
        return "select_project"

    def _next_after_action(self, data: dict[str, Any]) -> str:
        """Determine next step after viewing metrics."""
        action = data.get("action")
        if action == "different":
            return "select_metric_type"
        if action == "details":
            return "show_metrics"  # Will show more details
        return "complete"

    def get_intro_message(self) -> ChatMessage:
        """Get intro message for metrics query."""
        return ChatMessage(
            role="assistant",
            content="""📊 **Metrics Dashboard**

I can help you explore your engineering metrics. Here's what I can show you:

• **DORA Metrics** - Deployment frequency, lead time, MTTR, change failure rate
• **Project Overview** - Summary of all projects and their health
• **Connection Status** - Data source health and sync status
• **Pipeline Status** - Data collection job status
• **Code Activity** - Commits, PRs, and review metrics

What would you like to see?""",
            quick_replies=[
                QuickReply(label="DORA Metrics", value="dora", icon="📊"),
                QuickReply(label="Overview", value="overview", icon="📈"),
                QuickReply(label="Connections", value="connections", icon="🔗"),
                QuickReply(label="Pipelines", value="pipelines", icon="⚙️"),
            ],
        )


class OnboardingFlow(SetupFlow):
    """Flow for initial onboarding - guides through complete setup."""

    def _build_steps(self) -> None:
        """Build onboarding steps."""

        # Welcome
        self.steps["welcome"] = FlowStep(
            name="welcome",
            prompt="""
Welcome to NexusAI! 👋

I'm your setup assistant, and I'll help you get everything configured to start tracking your development metrics and DORA performance.

Here's what we'll set up:
1. 📦 **Create a Project** - Organize your metrics
2. 🔗 **Connect Data Sources** - GitHub, Jira, Jenkins, etc.
3. 📊 **Configure Dashboards** - Visualize your data
4. ⏰ **Set Up Pipelines** - Automate data collection

Ready to get started?
""",
            field_name="ready",
            field_type="select",
            options=[
                {"value": "yes", "label": "Let's go!", "icon": "🚀"},
                {"value": "skip", "label": "I'll explore first", "icon": "👀"},
                {"value": "help", "label": "I have questions", "icon": "❓"},
            ],
            conditional_next=self._next_after_welcome,
        )
        self.initial_step = "welcome"

        # Create project
        self.steps["create_project"] = FlowStep(
            name="create_project",
            prompt="First, let's create a project to organize your data. What's your project name?",
            field_name="project_name",
            field_type="text",
            help_text="Choose a name that represents your team or application",
            next_step="project_description",
        )

        # Project description
        self.steps["project_description"] = FlowStep(
            name="project_description",
            prompt="Add a brief description (optional):",
            field_name="project_description",
            field_type="text",
            required=False,
            next_step="select_source",
        )

        # Select primary data source
        self.steps["select_source"] = FlowStep(
            name="select_source",
            prompt="Now let's connect your first data source. Which tool does your team use most?",
            field_name="primary_source",
            field_type="select",
            options=[
                {"value": "github", "label": "GitHub", "icon": "🐙"},
                {"value": "gitlab", "label": "GitLab", "icon": "🦊"},
                {"value": "jira", "label": "Jira", "icon": "📋"},
                {"value": "jenkins", "label": "Jenkins", "icon": "🔧"},
                {"value": "other", "label": "Something else", "icon": "🔌"},
            ],
            conditional_next=self._next_after_source,
        )

        # Connection setup will be handled by nested ConnectionSetupFlow

        # Setup complete
        self.steps["setup_complete"] = FlowStep(
            name="setup_complete",
            prompt=self._get_completion_message,
            field_name="next_action",
            field_type="select",
            options=[
                {"value": "add_more", "label": "Add more connections", "icon": "➕"},
                {"value": "dashboard", "label": "View dashboard", "icon": "📊"},
                {"value": "done", "label": "I'm done", "icon": "✅"},
            ],
            conditional_next=self._next_after_complete,
        )

        self.steps["complete"] = FlowStep(
            name="complete",
            prompt="🎉 Setup complete! You're all set to start tracking your development metrics.",
            field_name=None,
            field_type="text",
            required=False,
        )

    def _next_after_welcome(self, data: dict[str, Any]) -> str:
        """Determine next step after welcome."""
        choice = data.get("ready")
        if choice == "yes":
            return "create_project"
        elif choice == "help":
            return "__show_help__"
        return "complete"

    def _next_after_source(self, data: dict[str, Any]) -> str:
        """Determine next step after source selection."""
        source = data.get("primary_source")
        if source == "other":
            return "__show_all_sources__"
        return "__start_connection_flow__"

    def _get_completion_message(self, data: dict[str, Any]) -> str:
        """Get completion message."""
        project_name = data.get("project_name", "Your project")
        connections = data.get("connections_created", [])

        message = f"""
🎉 Great progress! Here's what we've set up:

📦 **Project**: {project_name}
"""
        if connections:
            message += f"🔗 **Connections**: {len(connections)} data source(s)\n"

        message += """
Your first data sync will start automatically. You can view your metrics once the initial sync completes (usually within a few minutes).

What would you like to do next?
"""
        return message

    def _next_after_complete(self, data: dict[str, Any]) -> str:
        """Determine next step after completion options."""
        action = data.get("next_action")
        if action == "add_more":
            return "__start_connection_flow__"
        elif action == "dashboard":
            return "__navigate_dashboard__"
        return "complete"

    def get_intro_message(self) -> ChatMessage:
        """Get intro message for onboarding."""
        return ChatMessage(
            role="assistant",
            content="👋 Welcome! I'm here to help you set up your development analytics platform. Let me guide you through the process!",
            quick_replies=[
                QuickReply(
                    label="Start setup",
                    value="__start__",
                    icon="🚀",
                ),
                QuickReply(
                    label="What can you do?",
                    value="__capabilities__",
                    icon="❓",
                ),
            ],
        )
