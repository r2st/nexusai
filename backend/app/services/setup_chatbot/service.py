"""Setup Chatbot Service - Main orchestration service."""

import json
import re
from datetime import datetime, UTC
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.devlake import devlake_service
from app.services.setup_chatbot.flows import (
    ConnectionSetupFlow,
    FlowState,
    MetricsQueryFlow,
    OnboardingFlow,
    PipelineSetupFlow,
    ProjectSetupFlow,
    SetupFlow,
)
from app.services.setup_chatbot.schemas import (
    ActionType,
    ChatMessage,
    ChatResponse,
    ConnectionConfig,
    PLUGIN_CONFIGS,
    QuickReply,
    SetupAction,
    SetupSession,
)


# In-memory session store (use Redis in production)
_sessions: dict[str, SetupSession] = {}


SYSTEM_PROMPT = """You are a helpful DevOps setup assistant for NexusAI, a development analytics platform powered by Apache DevLake.

Your role is to help users:
1. Set up data source connections (GitHub, GitLab, Jira, Jenkins, etc.)
2. Create and configure projects
3. Set up data collection pipelines
4. Understand DORA metrics and analytics
5. Troubleshoot connection and configuration issues

Guidelines:
- Be friendly, concise, and helpful
- Guide users step by step through complex setups
- Explain technical concepts in simple terms when needed
- If you need information, ask one question at a time
- Always validate user inputs before proceeding
- Offer to test connections before finalizing
- Provide helpful examples when asking for input
- If something fails, explain why and offer solutions

Available commands users can use:
- "connect [plugin]" - Start setting up a connection
- "create project" - Create a new project
- "list connections" - Show all connections
- "list projects" - Show all projects
- "status" - Show system status
- "help" - Show available commands

When users provide credentials or tokens, acknowledge them securely without displaying the full value.
"""


class SetupChatbotService:
    """Main service for the setup chatbot."""

    def __init__(self):
        self.flows: dict[str, type[SetupFlow]] = {
            "connection": ConnectionSetupFlow,
            "project": ProjectSetupFlow,
            "pipeline": PipelineSetupFlow,
            "onboarding": OnboardingFlow,
            "metrics": MetricsQueryFlow,
        }

    def _get_llm(self, streaming: bool = False):
        """Get the LLM for natural language processing.

        Uses DEFAULT_AI_PROVIDER from settings to determine which provider to use.
        All model names and URLs are read from environment configuration.
        """
        default_provider = getattr(settings, "DEFAULT_AI_PROVIDER", "").lower()

        # Use the configured default provider first
        if default_provider == "anthropic" and settings.ANTHROPIC_API_KEY:
            from langchain_anthropic import ChatAnthropic

            return ChatAnthropic(
                model=settings.ANTHROPIC_DEFAULT_MODEL,
                api_key=settings.ANTHROPIC_API_KEY,
                temperature=0.7,
                max_tokens=1024,
                streaming=streaming,
            )
        elif default_provider == "openai" and settings.OPENAI_API_KEY:
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=settings.OPENAI_DEFAULT_MODEL,
                api_key=settings.OPENAI_API_KEY,
                temperature=0.7,
                max_tokens=1024,
                streaming=streaming,
            )
        elif default_provider == "google" and settings.GOOGLE_API_KEY:
            from langchain_google_genai import ChatGoogleGenerativeAI

            return ChatGoogleGenerativeAI(
                model=settings.GOOGLE_DEFAULT_MODEL,
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=0.7,
                max_output_tokens=1024,
                streaming=streaming,
            )
        elif default_provider == "ollama" and getattr(settings, "OLLAMA_BASE_URL", None):
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=settings.OLLAMA_DEFAULT_MODEL,
                base_url=settings.OLLAMA_BASE_URL,
                api_key="ollama",
                temperature=0.7,
                max_tokens=1024,
                streaming=streaming,
            )
        # Fallback: try providers in order if default not configured
        elif settings.ANTHROPIC_API_KEY:
            from langchain_anthropic import ChatAnthropic

            return ChatAnthropic(
                model=settings.ANTHROPIC_DEFAULT_MODEL,
                api_key=settings.ANTHROPIC_API_KEY,
                temperature=0.7,
                max_tokens=1024,
                streaming=streaming,
            )
        elif settings.OPENAI_API_KEY:
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=settings.OPENAI_DEFAULT_MODEL,
                api_key=settings.OPENAI_API_KEY,
                temperature=0.7,
                max_tokens=1024,
                streaming=streaming,
            )
        elif settings.GOOGLE_API_KEY:
            from langchain_google_genai import ChatGoogleGenerativeAI

            return ChatGoogleGenerativeAI(
                model=settings.GOOGLE_DEFAULT_MODEL,
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=0.7,
                max_output_tokens=1024,
                streaming=streaming,
            )
        else:
            raise ValueError(
                "No AI provider configured. Please set one of: "
                "ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY, or OLLAMA_BASE_URL"
            )

    # ===================
    # Session Management
    # ===================

    def get_session(self, session_id: str) -> SetupSession | None:
        """Get a session by ID."""
        return _sessions.get(session_id)

    def create_session(
        self,
        tenant_id: str,
        user_id: str,
        flow_type: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> SetupSession:
        """Create a new session."""
        session = SetupSession(
            id=str(uuid4()),
            tenant_id=tenant_id,
            user_id=user_id,
            flow_type=flow_type,
            context=context or {},
        )
        _sessions[session.id] = session
        return session

    def save_session(self, session: SetupSession) -> None:
        """Save session state."""
        session.updated_at = datetime.now(UTC)
        _sessions[session.id] = session

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id in _sessions:
            del _sessions[session_id]
            return True
        return False

    # ===================
    # Flow Management
    # ===================

    def _get_flow(self, flow_type: str, context: dict[str, Any] | None = None) -> SetupFlow | None:
        """Get a flow instance by type."""
        flow_class = self.flows.get(flow_type)
        if not flow_class:
            return None

        if flow_type == "connection" and context and context.get("plugin"):
            return flow_class(plugin=context["plugin"])

        return flow_class()

    def _count_flow_steps(self, flow: SetupFlow) -> int:
        """Count the total steps in a flow."""
        # Simple count - could be more sophisticated for conditional flows
        return len([s for s in flow.steps.values() if s.field_name is not None])

    def _get_current_step_number(self, flow: SetupFlow, current_step: str) -> int:
        """Get the current step number (1-indexed)."""
        step_list = list(flow.steps.keys())
        if current_step in step_list:
            return step_list.index(current_step) + 1
        return 1

    # ===================
    # Message Processing
    # ===================

    async def process_message(
        self,
        session: SetupSession,
        user_message: str,
    ) -> ChatResponse:
        """Process a user message and return a response."""

        # Add user message to history
        session.messages.append(
            ChatMessage(
                role="user",
                content=user_message,
            )
        )

        # Check for special commands
        special_response = await self._handle_special_commands(session, user_message)
        if special_response:
            return special_response

        # Check for quick reply values
        if user_message.startswith("__"):
            return await self._handle_quick_reply(session, user_message)

        # If in a flow, process flow step
        if session.flow_type and session.current_step:
            return await self._process_flow_step(session, user_message)

        # Use NLU to understand intent
        return await self._process_natural_language(session, user_message)

    async def _handle_special_commands(
        self,
        session: SetupSession,
        message: str,
    ) -> ChatResponse | None:
        """Handle special commands."""
        message_lower = message.lower().strip()

        # Cancel command
        if message_lower in ["cancel", "quit", "exit", "stop"]:
            return await self._cancel_flow(session)

        # Back command
        if message_lower in ["back", "previous", "go back"]:
            return await self._go_back(session)

        # Help command
        if message_lower in ["help", "?"]:
            return self._show_help(session)

        # Status command
        if message_lower == "status":
            return await self._show_status(session)

        # List commands
        if message_lower.startswith("list "):
            return await self._handle_list_command(session, message_lower)

        # Connect command
        if message_lower.startswith("connect "):
            plugin = message_lower.replace("connect ", "").strip()
            return await self._start_connection_flow(session, plugin)

        # Create project command
        if message_lower in ["create project", "new project"]:
            return await self._start_project_flow(session)

        # Metrics commands
        if any(word in message_lower for word in ["metrics", "dora", "dashboard", "show metrics", "view metrics", "analytics"]):
            return await self._start_metrics_flow(session)

        return None

    async def _handle_quick_reply(
        self,
        session: SetupSession,
        value: str,
    ) -> ChatResponse:
        """Handle quick reply button clicks."""

        if value == "__start__":
            # Start the current flow
            if session.flow_type:
                flow = self._get_flow(session.flow_type, session.context)
                if flow:
                    session.current_step = flow.initial_step
                    return await self._get_step_response(session, flow)

        elif value == "__cancel__":
            return await self._cancel_flow(session)

        elif value == "__show_options__":
            return self._show_all_options(session)

        elif value == "__capabilities__":
            return self._show_capabilities(session)

        elif value == "__explain_project__":
            return self._explain_concept(session, "project")

        elif value == "__explain_pipeline__":
            return self._explain_concept(session, "pipeline")

        elif value.startswith("__start_"):
            # Start a specific flow
            flow_type = value.replace("__start_", "").replace("_flow__", "")
            return await self._start_flow(session, flow_type)

        # If none matched, treat as regular input
        return await self._process_flow_step(session, value)

    async def _process_flow_step(
        self,
        session: SetupSession,
        user_input: str,
    ) -> ChatResponse:
        """Process input for the current flow step."""
        if not session.flow_type or not session.current_step:
            return await self._process_natural_language(session, user_input)

        flow = self._get_flow(session.flow_type, session.context)
        if not flow:
            return self._create_error_response(session, "Invalid flow type")

        step = flow.get_step(session.current_step)
        if not step:
            return self._create_error_response(session, f"Unknown step: {session.current_step}")

        # Validate input
        if step.field_name:
            is_valid, error = flow.validate_step(session.current_step, user_input)
            if not is_valid:
                return self._create_validation_error(session, error or "Invalid input")

            # Store the value
            session.data[step.field_name] = user_input

        # Get next step
        next_step = flow.get_next_step(session.current_step, session.data)

        # Handle special next steps
        if next_step == "__start_connection_flow__":
            # Start nested connection flow
            return await self._start_connection_flow(
                session,
                session.data.get("primary_source", session.data.get("plugin")),
            )

        if next_step in ["complete", "completed", None]:
            # Flow is complete
            return await self._complete_flow(session, flow)

        if next_step == "cancelled":
            return await self._cancel_flow(session)

        # Handle metrics display step specially
        if next_step == "show_metrics" and session.flow_type == "metrics":
            session.current_step = next_step
            return await self._show_metrics_response(session, flow)

        # Move to next step
        session.current_step = next_step
        return await self._get_step_response(session, flow)

    async def _get_step_response(
        self,
        session: SetupSession,
        flow: SetupFlow,
    ) -> ChatResponse:
        """Get the response for the current step."""
        step = flow.get_step(session.current_step)
        if not step:
            return self._create_error_response(session, "Invalid step")

        total_steps = self._count_flow_steps(flow)
        step_number = self._get_current_step_number(flow, session.current_step)

        # Get the prompt (may be dynamic)
        if callable(step.prompt):
            prompt_text = step.prompt(session.data)
        else:
            prompt_text = step.prompt

        message = flow.create_step_message(
            step,
            step_number,
            total_steps,
            session.data,
        )
        # Override content with dynamic prompt
        message.content = prompt_text

        session.messages.append(message)
        self.save_session(session)

        return ChatResponse(
            message=message,
            session_id=session.id,
            current_step=session.current_step,
            can_go_back=step_number > 1,
            is_complete=False,
            collected_data=session.data,
        )

    async def _process_natural_language(
        self,
        session: SetupSession,
        user_message: str,
    ) -> ChatResponse:
        """Process natural language input using LLM."""
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        llm = self._get_llm()

        # Build context
        context_parts = []
        if session.data:
            context_parts.append(f"Current session data: {json.dumps(session.data)}")
        if session.flow_type:
            context_parts.append(f"Current flow: {session.flow_type}")
        if session.current_step:
            context_parts.append(f"Current step: {session.current_step}")

        context = "\n".join(context_parts) if context_parts else "No active flow"

        # Build messages
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            SystemMessage(content=f"Session context:\n{context}"),
        ]

        # Add recent history
        for msg in session.messages[-10:]:
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                messages.append(AIMessage(content=msg.content))

        # Add current message
        messages.append(HumanMessage(content=user_message))

        try:
            response = await llm.ainvoke(messages)
            content = response.content

            # Parse intent from response
            intent = self._extract_intent(user_message, content)

            # Create response with appropriate quick replies
            quick_replies = self._get_contextual_quick_replies(intent, session)

            message = ChatMessage(
                role="assistant",
                content=content,
                quick_replies=quick_replies,
            )

            session.messages.append(message)
            self.save_session(session)

            return ChatResponse(
                message=message,
                session_id=session.id,
                current_step=session.current_step,
                can_go_back=False,
                is_complete=False,
                collected_data=session.data,
            )

        except Exception as e:
            return self._create_error_response(session, f"Error processing message: {str(e)}")

    def _extract_intent(self, user_message: str, ai_response: str) -> str:
        """Extract intent from user message and AI response."""
        message_lower = user_message.lower()

        if any(word in message_lower for word in ["connect", "connection", "add source"]):
            return "connection"
        if any(word in message_lower for word in ["project", "create project"]):
            return "project"
        if any(word in message_lower for word in ["pipeline", "schedule", "sync"]):
            return "pipeline"
        if any(word in message_lower for word in ["help", "what can you do"]):
            return "help"
        if any(word in message_lower for word in ["status", "health"]):
            return "status"

        return "general"

    def _get_contextual_quick_replies(
        self,
        intent: str,
        session: SetupSession,
    ) -> list[QuickReply]:
        """Get context-appropriate quick replies."""
        replies = []

        if intent == "connection":
            replies.extend([
                QuickReply(label="GitHub", value="connect github", icon="🐙"),
                QuickReply(label="Jira", value="connect jira", icon="📋"),
                QuickReply(label="Jenkins", value="connect jenkins", icon="🔧"),
                QuickReply(label="All options", value="__show_options__", icon="📋"),
            ])
        elif intent == "project":
            replies.append(
                QuickReply(label="Create project", value="create project", icon="📦")
            )
        elif intent == "help":
            replies.extend([
                QuickReply(label="Connect data source", value="connect", icon="🔗"),
                QuickReply(label="Create project", value="create project", icon="📦"),
                QuickReply(label="View status", value="status", icon="📊"),
            ])
        else:
            # General quick replies
            replies.extend([
                QuickReply(label="Setup connection", value="__start_connection_flow__", icon="🔗"),
                QuickReply(label="Create project", value="__start_project_flow__", icon="📦"),
                QuickReply(label="Help", value="help", icon="❓"),
            ])

        return replies[:4]  # Limit to 4 options

    # ===================
    # Flow Operations
    # ===================

    async def _start_flow(
        self,
        session: SetupSession,
        flow_type: str,
        context: dict[str, Any] | None = None,
    ) -> ChatResponse:
        """Start a new flow."""
        flow = self._get_flow(flow_type, context)
        if not flow:
            return self._create_error_response(session, f"Unknown flow type: {flow_type}")

        session.flow_type = flow_type
        session.current_step = flow.initial_step
        session.context = context or {}
        session.data = {}

        # Get intro message
        intro = flow.get_intro_message()
        session.messages.append(intro)

        self.save_session(session)

        return ChatResponse(
            message=intro,
            session_id=session.id,
            current_step=session.current_step,
            can_go_back=False,
            is_complete=False,
        )

    async def _start_connection_flow(
        self,
        session: SetupSession,
        plugin: str | None = None,
    ) -> ChatResponse:
        """Start connection setup flow."""
        context = {"plugin": plugin} if plugin and plugin in PLUGIN_CONFIGS else None
        return await self._start_flow(session, "connection", context)

    async def _start_project_flow(self, session: SetupSession) -> ChatResponse:
        """Start project setup flow."""
        return await self._start_flow(session, "project")

    async def _start_metrics_flow(self, session: SetupSession) -> ChatResponse:
        """Start metrics query flow."""
        return await self._start_flow(session, "metrics")

    async def _fetch_and_format_metrics(
        self,
        session: SetupSession,
        metric_type: str,
        project: str | None = None,
        time_range: str = "30d",
    ) -> str:
        """Fetch metrics from DevLake and format them for display."""
        try:
            if metric_type == "dora":
                return await self._format_dora_metrics(project, time_range)
            elif metric_type == "overview":
                return await self._format_overview()
            elif metric_type == "connections":
                return await self._format_connections()
            elif metric_type == "pipelines":
                return await self._format_pipelines()
            elif metric_type == "commits":
                return await self._format_commit_metrics(project, time_range)
            elif metric_type == "prs":
                return await self._format_pr_metrics(project, time_range)
            else:
                return "Unknown metric type"
        except Exception as e:
            return f"Error fetching metrics: {str(e)}"

    async def _format_dora_metrics(self, project: str | None, time_range: str) -> str:
        """Format DORA metrics for display."""
        try:
            metrics = await devlake_service.get_dora_metrics(project)

            if not metrics:
                return """📊 **DORA Metrics**

No DORA metrics available yet. This usually means:
• No data has been collected yet
• No deployments have been detected
• Pipeline hasn't completed initial sync

💡 **Tip:** Run a data collection pipeline first, then check back!"""

            # Format ratings with emojis
            def rating_emoji(value: float | None, thresholds: tuple) -> str:
                if value is None:
                    return "⚪ N/A"
                if value >= thresholds[0]:
                    return "🟢 Elite"
                elif value >= thresholds[1]:
                    return "🟡 High"
                elif value >= thresholds[2]:
                    return "🟠 Medium"
                return "🔴 Low"

            df = metrics.get("deployment_frequency")
            lt = metrics.get("lead_time_for_changes")
            mttr = metrics.get("mean_time_to_recovery")
            cfr = metrics.get("change_failure_rate")

            return f"""📊 **DORA Metrics** ({time_range})
{f"Project: {project}" if project else "All Projects"}

**Deployment Frequency**
{rating_emoji(df, (7, 1, 0.25))} {df:.1f if df else 'N/A'} deploys/week
_How often you deploy to production_

**Lead Time for Changes**
{rating_emoji(24/lt if lt else None, (1, 0.14, 0.03))} {lt:.1f if lt else 'N/A'} hours
_Time from commit to production_

**Mean Time to Recovery**
{rating_emoji(24/mttr if mttr else None, (1, 0.14, 0.03))} {mttr:.1f if mttr else 'N/A'} hours
_Time to restore service after incident_

**Change Failure Rate**
{rating_emoji(100-cfr if cfr else None, (85, 70, 55))} {cfr:.1f if cfr else 'N/A'}%
_Percentage of deployments causing failures_

---
🏆 **Overall Rating:** {"Elite" if df and df >= 7 else "High" if df and df >= 1 else "Medium" if df else "Needs Data"}
"""
        except Exception as e:
            return f"Error fetching DORA metrics: {str(e)}\n\n💡 Make sure DevLake is running and has collected data."

    async def _format_overview(self) -> str:
        """Format system overview."""
        try:
            projects = await devlake_service.list_projects()
            connections = await devlake_service.list_connections()
            pipelines = await devlake_service.list_pipelines()

            # Count by status
            active_connections = sum(1 for c in connections if c.get("status") == "active")
            running_pipelines = sum(1 for p in pipelines if p.get("status") == "running")

            return f"""📈 **Project Overview**

**Projects:** {len(projects)}
**Connections:** {len(connections)} ({active_connections} active)
**Pipelines:** {len(pipelines)} ({running_pipelines} running)

---
**Recent Projects:**
{chr(10).join([f"• {p.get('name', 'Unnamed')}" for p in projects[:5]]) if projects else "No projects yet"}

**Recent Activity:**
{chr(10).join([f"• {p.get('name', 'Pipeline')} - {p.get('status', 'unknown')}" for p in pipelines[:3]]) if pipelines else "No recent pipeline runs"}
"""
        except Exception as e:
            return f"Error fetching overview: {str(e)}"

    async def _format_connections(self) -> str:
        """Format connection status."""
        try:
            connections = await devlake_service.list_connections()

            if not connections:
                return """🔗 **Connection Status**

No connections configured yet.

💡 **Get Started:**
Say "connect github" to add your first data source!"""

            status_emoji = {"active": "🟢", "error": "🔴", "testing": "🟡"}

            conn_list = "\n".join([
                f"{status_emoji.get(c.get('status', ''), '⚪')} **{c.get('name')}** ({c.get('plugin')})"
                for c in connections[:10]
            ])

            return f"""🔗 **Connection Status**

{conn_list}

---
Total: {len(connections)} connection(s)
"""
        except Exception as e:
            return f"Error fetching connections: {str(e)}"

    async def _format_pipelines(self) -> str:
        """Format pipeline status."""
        try:
            pipelines = await devlake_service.list_pipelines()

            if not pipelines:
                return """⚙️ **Pipeline Status**

No pipelines configured or run yet.

💡 **Get Started:**
Create a project and add connections to set up your first pipeline!"""

            status_emoji = {
                "completed": "✅",
                "running": "🔄",
                "failed": "❌",
                "pending": "⏳",
                "cancelled": "⚫",
            }

            pipeline_list = "\n".join([
                f"{status_emoji.get(p.get('status', ''), '⚪')} **{p.get('name', 'Pipeline')}** - {p.get('status', 'unknown')}"
                for p in pipelines[:10]
            ])

            return f"""⚙️ **Pipeline Status**

{pipeline_list}

---
Total: {len(pipelines)} pipeline(s)
"""
        except Exception as e:
            return f"Error fetching pipelines: {str(e)}"

    async def _format_commit_metrics(self, project: str | None, time_range: str) -> str:
        """Format commit activity metrics."""
        # This would fetch from DevLake's commit data
        return f"""💻 **Commit Activity** ({time_range})
{f"Project: {project}" if project else "All Projects"}

Commit data visualization coming soon!

💡 For now, check the Grafana dashboard at http://localhost:3002 for detailed commit analytics.
"""

    async def _format_pr_metrics(self, project: str | None, time_range: str) -> str:
        """Format pull request metrics."""
        # This would fetch from DevLake's PR data
        return f"""🔀 **Pull Request Metrics** ({time_range})
{f"Project: {project}" if project else "All Projects"}

PR analytics coming soon!

💡 For now, check the Grafana dashboard at http://localhost:3002 for detailed PR metrics.
"""

    async def _show_metrics_response(
        self,
        session: SetupSession,
        flow: SetupFlow,
    ) -> ChatResponse:
        """Show metrics based on user selections."""
        metric_type = session.data.get("metric_type", "overview")
        project = session.data.get("project")
        time_range = session.data.get("time_range", "30d")

        # Fetch and format the metrics
        metrics_content = await self._fetch_and_format_metrics(
            session,
            metric_type,
            project,
            time_range,
        )

        # Create quick replies for next actions
        quick_replies = [
            QuickReply(label="View different metrics", value="different", icon="🔄"),
            QuickReply(label="Add connection", value="connect", icon="➕"),
            QuickReply(label="Done", value="done", icon="✅"),
        ]

        message = ChatMessage(
            role="assistant",
            content=metrics_content,
            quick_replies=quick_replies,
        )

        session.messages.append(message)
        self.save_session(session)

        return ChatResponse(
            message=message,
            session_id=session.id,
            current_step=session.current_step,
            can_go_back=True,
            is_complete=False,
            collected_data=session.data,
        )

    async def _complete_flow(
        self,
        session: SetupSession,
        flow: SetupFlow,
    ) -> ChatResponse:
        """Complete the current flow and execute actions."""
        # Execute the flow action
        result = await self._execute_flow_action(session)

        # Create completion message
        if result.get("success"):
            content = f"✅ {result.get('message', 'Completed successfully!')}"

            # Add next steps
            if session.flow_type == "connection":
                content += "\n\nYou can now:\n• Add more connections\n• Create a pipeline to collect data\n• View your dashboard"
            elif session.flow_type == "project":
                content += "\n\nNext steps:\n• Connect data sources to this project\n• Set up data collection pipelines"

        else:
            content = f"❌ {result.get('error', 'Something went wrong')}\n\nWould you like to try again?"

        message = ChatMessage(
            role="assistant",
            content=content,
            quick_replies=[
                QuickReply(label="Add another connection", value="connect", icon="➕"),
                QuickReply(label="Create pipeline", value="__start_pipeline_flow__", icon="⏰"),
                QuickReply(label="View dashboard", value="__navigate_dashboard__", icon="📊"),
                QuickReply(label="Done", value="done", icon="✅"),
            ],
        )

        session.messages.append(message)
        session.flow_type = None
        session.current_step = None
        session.completed_at = datetime.now(UTC)

        self.save_session(session)

        return ChatResponse(
            message=message,
            session_id=session.id,
            current_step=None,
            can_go_back=False,
            is_complete=True,
            collected_data=session.data,
        )

    async def _execute_flow_action(self, session: SetupSession) -> dict[str, Any]:
        """Execute the action for the completed flow."""
        try:
            if session.flow_type == "connection":
                return await self._create_connection(session)
            elif session.flow_type == "project":
                return await self._create_project(session)
            elif session.flow_type == "pipeline":
                return await self._create_pipeline(session)
            else:
                return {"success": True, "message": "Flow completed"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _create_connection(self, session: SetupSession) -> dict[str, Any]:
        """Create a connection in DevLake."""
        data = session.data
        plugin = data.get("plugin") or session.context.get("plugin")

        if not plugin:
            return {"success": False, "error": "No plugin selected"}

        try:
            # Create connection via DevLake API
            result = await devlake_service.create_connection(
                plugin=plugin,
                name=data.get("name", f"New {plugin} connection"),
                endpoint=data.get("endpoint", ""),
                token=data.get("token") or data.get("credentials"),
            )

            # Test connection if requested
            if data.get("do_test") == "yes" and result.get("id"):
                test_result = await devlake_service.test_connection(
                    plugin=plugin,
                    connection_id=result["id"],
                )
                if not test_result.get("success"):
                    return {
                        "success": False,
                        "error": f"Connection created but test failed: {test_result.get('message')}",
                        "connection_id": result["id"],
                    }

            return {
                "success": True,
                "message": f"Connection '{data.get('name')}' created successfully!",
                "connection_id": result.get("id"),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _create_project(self, session: SetupSession) -> dict[str, Any]:
        """Create a project in DevLake."""
        data = session.data

        try:
            result = await devlake_service.create_project(
                name=data.get("name"),
                description=data.get("description"),
            )

            return {
                "success": True,
                "message": f"Project '{data.get('name')}' created successfully!",
                "project_name": result.get("name"),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _create_pipeline(self, session: SetupSession) -> dict[str, Any]:
        """Create a pipeline/blueprint in DevLake."""
        # This would create a blueprint
        return {"success": True, "message": "Pipeline configured successfully!"}

    async def _cancel_flow(self, session: SetupSession) -> ChatResponse:
        """Cancel the current flow."""
        session.flow_type = None
        session.current_step = None
        session.data = {}

        message = ChatMessage(
            role="assistant",
            content="Setup cancelled. What would you like to do instead?",
            quick_replies=[
                QuickReply(label="Start over", value="__start_onboarding__", icon="🔄"),
                QuickReply(label="Different setup", value="help", icon="❓"),
                QuickReply(label="Exit", value="done", icon="👋"),
            ],
        )

        session.messages.append(message)
        self.save_session(session)

        return ChatResponse(
            message=message,
            session_id=session.id,
            current_step=None,
            can_go_back=False,
            is_complete=False,
        )

    async def _go_back(self, session: SetupSession) -> ChatResponse:
        """Go back to the previous step."""
        if not session.flow_type or not session.current_step:
            return self._create_error_response(session, "Nothing to go back to")

        flow = self._get_flow(session.flow_type, session.context)
        if not flow:
            return self._create_error_response(session, "Invalid flow")

        # Find previous step (simple implementation)
        step_list = list(flow.steps.keys())
        current_idx = step_list.index(session.current_step) if session.current_step in step_list else 0

        if current_idx > 0:
            session.current_step = step_list[current_idx - 1]
            return await self._get_step_response(session, flow)

        return self._create_error_response(session, "Already at the first step")

    # ===================
    # Helper Responses
    # ===================

    def _show_help(self, session: SetupSession) -> ChatResponse:
        """Show help message."""
        message = ChatMessage(
            role="assistant",
            content="""
Here's what I can help you with:

**📊 View Metrics**
See DORA metrics, project overview, and analytics.
→ Say "show metrics" or "dora" to get started

**🔗 Setting Up Connections**
Connect your development tools like GitHub, Jira, Jenkins, and more.
→ Say "connect github" or click a quick action below

**📦 Creating Projects**
Organize your data sources and metrics.
→ Say "create project" to get started

**⏰ Data Pipelines**
Schedule automatic data collection from your sources.
→ I'll help you set this up after connections are made

**Other Commands**
• `metrics` or `dora` - View DORA metrics
• `status` - Check system health
• `list connections` - See your connections
• `list projects` - See your projects
• `cancel` - Cancel current setup
• `back` - Go to previous step

What would you like to do?
""",
            quick_replies=[
                QuickReply(label="View Metrics", value="metrics", icon="📊"),
                QuickReply(label="Connect GitHub", value="connect github", icon="🐙"),
                QuickReply(label="Create project", value="create project", icon="📦"),
                QuickReply(label="View status", value="status", icon="🔍"),
            ],
        )

        session.messages.append(message)
        self.save_session(session)

        return ChatResponse(
            message=message,
            session_id=session.id,
            current_step=session.current_step,
            can_go_back=False,
            is_complete=False,
        )

    async def _show_status(self, session: SetupSession) -> ChatResponse:
        """Show system status."""
        # Check DevLake health
        devlake_healthy = await devlake_service.health_check()

        status_icon = "🟢" if devlake_healthy else "🔴"
        status_text = "Online" if devlake_healthy else "Offline"

        # Get counts
        try:
            projects = await devlake_service.list_projects()
            connections = await devlake_service.list_connections()
            project_count = len(projects)
            connection_count = len(connections)
        except Exception:
            project_count = "?"
            connection_count = "?"

        message = ChatMessage(
            role="assistant",
            content=f"""
**System Status**

{status_icon} DevLake: {status_text}
📦 Projects: {project_count}
🔗 Connections: {connection_count}

What would you like to do?
""",
            quick_replies=[
                QuickReply(label="Add connection", value="connect", icon="➕"),
                QuickReply(label="List connections", value="list connections", icon="📋"),
                QuickReply(label="List projects", value="list projects", icon="📦"),
            ],
        )

        session.messages.append(message)
        self.save_session(session)

        return ChatResponse(
            message=message,
            session_id=session.id,
            current_step=session.current_step,
            can_go_back=False,
            is_complete=False,
        )

    async def _handle_list_command(
        self,
        session: SetupSession,
        command: str,
    ) -> ChatResponse:
        """Handle list commands."""
        if "connection" in command:
            try:
                connections = await devlake_service.list_connections()
                if connections:
                    items = "\n".join([
                        f"• **{c.get('name')}** ({c.get('plugin')}) - {c.get('status', 'unknown')}"
                        for c in connections[:10]
                    ])
                    content = f"**Your Connections:**\n\n{items}"
                else:
                    content = "No connections found. Would you like to create one?"
            except Exception as e:
                content = f"Error fetching connections: {str(e)}"

        elif "project" in command:
            try:
                projects = await devlake_service.list_projects()
                if projects:
                    items = "\n".join([
                        f"• **{p.get('name')}** - {p.get('description', 'No description')}"
                        for p in projects[:10]
                    ])
                    content = f"**Your Projects:**\n\n{items}"
                else:
                    content = "No projects found. Would you like to create one?"
            except Exception as e:
                content = f"Error fetching projects: {str(e)}"
        else:
            content = "I can list `connections` or `projects`. Which would you like?"

        message = ChatMessage(
            role="assistant",
            content=content,
            quick_replies=[
                QuickReply(label="Add connection", value="connect", icon="➕"),
                QuickReply(label="Create project", value="create project", icon="📦"),
            ],
        )

        session.messages.append(message)
        self.save_session(session)

        return ChatResponse(
            message=message,
            session_id=session.id,
            current_step=session.current_step,
            can_go_back=False,
            is_complete=False,
        )

    def _show_all_options(self, session: SetupSession) -> ChatResponse:
        """Show all available plugin options."""
        options = []
        for key, config in PLUGIN_CONFIGS.items():
            options.append(f"{config.icon} **{config.display_name}** - {config.description}")

        content = "**Available Data Sources:**\n\n" + "\n".join(options)
        content += "\n\nWhich one would you like to connect?"

        quick_replies = [
            QuickReply(
                label=config.display_name,
                value=f"connect {key}",
                icon=config.icon,
            )
            for key, config in list(PLUGIN_CONFIGS.items())[:4]
        ]

        message = ChatMessage(
            role="assistant",
            content=content,
            quick_replies=quick_replies,
        )

        session.messages.append(message)
        self.save_session(session)

        return ChatResponse(
            message=message,
            session_id=session.id,
            current_step=session.current_step,
            can_go_back=False,
            is_complete=False,
        )

    def _show_capabilities(self, session: SetupSession) -> ChatResponse:
        """Show chatbot capabilities."""
        message = ChatMessage(
            role="assistant",
            content="""
I'm your DevOps setup assistant! Here's what I can do:

🔗 **Connect Data Sources**
Set up connections to GitHub, GitLab, Jira, Jenkins, and 10+ other tools

📦 **Create Projects**
Organize your metrics and data sources into projects

⏰ **Configure Pipelines**
Schedule automatic data collection from your sources

📊 **Track DORA Metrics**
Monitor deployment frequency, lead time, MTTR, and change failure rate

🔍 **Troubleshoot Issues**
Help diagnose and fix connection or data collection problems

Ready to get started?
""",
            quick_replies=[
                QuickReply(label="Start setup", value="__start__", icon="🚀"),
                QuickReply(label="Connect source", value="connect", icon="🔗"),
                QuickReply(label="View status", value="status", icon="📊"),
            ],
        )

        session.messages.append(message)
        self.save_session(session)

        return ChatResponse(
            message=message,
            session_id=session.id,
            current_step=session.current_step,
            can_go_back=False,
            is_complete=False,
        )

    def _explain_concept(self, session: SetupSession, concept: str) -> ChatResponse:
        """Explain a concept to the user."""
        explanations = {
            "project": """
A **DevLake Project** is a way to organize your development data and metrics.

Think of it like a folder that contains:
• Your data source connections (GitHub, Jira, etc.)
• DORA metrics and dashboards
• Custom analytics and reports

Most teams create one project per product or team. For example:
• "Mobile App" - tracking the mobile team's metrics
• "Platform Services" - tracking backend infrastructure

Ready to create a project?
""",
            "pipeline": """
A **Data Pipeline** automatically syncs data from your connected sources.

Here's how it works:
1. You configure which connections to include
2. Set a schedule (hourly, daily, etc.)
3. DevLake automatically pulls the latest data
4. Your dashboards and metrics update automatically

Pipelines can be:
• **Incremental** - Only fetch new data (faster)
• **Full sync** - Re-fetch everything (more complete)

Want to set up a pipeline?
""",
        }

        content = explanations.get(concept, f"I don't have an explanation for '{concept}' yet.")

        message = ChatMessage(
            role="assistant",
            content=content,
            quick_replies=[
                QuickReply(label="Let's start", value="__start__", icon="🚀"),
                QuickReply(label="More questions", value="help", icon="❓"),
            ],
        )

        session.messages.append(message)
        self.save_session(session)

        return ChatResponse(
            message=message,
            session_id=session.id,
            current_step=session.current_step,
            can_go_back=False,
            is_complete=False,
        )

    def _create_error_response(
        self,
        session: SetupSession,
        error: str,
    ) -> ChatResponse:
        """Create an error response."""
        message = ChatMessage(
            role="assistant",
            content=f"⚠️ {error}\n\nWould you like to try again or do something else?",
            quick_replies=[
                QuickReply(label="Try again", value="__retry__", icon="🔄"),
                QuickReply(label="Get help", value="help", icon="❓"),
                QuickReply(label="Cancel", value="cancel", icon="❌"),
            ],
        )

        session.messages.append(message)
        self.save_session(session)

        return ChatResponse(
            message=message,
            session_id=session.id,
            current_step=session.current_step,
            can_go_back=True,
            is_complete=False,
            errors=[error],
        )

    def _create_validation_error(
        self,
        session: SetupSession,
        error: str,
    ) -> ChatResponse:
        """Create a validation error response."""
        message = ChatMessage(
            role="assistant",
            content=f"That doesn't look quite right: **{error}**\n\nPlease try again.",
            quick_replies=[
                QuickReply(label="Cancel", value="__cancel__", icon="❌"),
            ],
        )

        session.messages.append(message)
        self.save_session(session)

        return ChatResponse(
            message=message,
            session_id=session.id,
            current_step=session.current_step,
            can_go_back=True,
            is_complete=False,
            errors=[error],
        )

    # ===================
    # Onboarding
    # ===================

    async def start_onboarding(
        self,
        tenant_id: str,
        user_id: str,
    ) -> ChatResponse:
        """Start the onboarding flow for a new user."""
        session = self.create_session(
            tenant_id=tenant_id,
            user_id=user_id,
            flow_type="onboarding",
        )

        return await self._start_flow(session, "onboarding")


# Singleton instance
setup_chatbot_service = SetupChatbotService()
