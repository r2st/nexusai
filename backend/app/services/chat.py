"""Chat service for AI conversations with MCP tool support."""

from __future__ import annotations

import json
import time
from collections.abc import AsyncGenerator
from typing import Any, TYPE_CHECKING
from pydantic import create_model
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.config import settings
from app.core.multitenancy import get_current_tenant_id
from app.models.conversation import Conversation, Message, MessageRole, ModelProvider
from app.services.agents.mcp import MCPClient, MCPServerConfig, MCPTool, mcp_manager
from app.services.mcp import get_mcp_server, get_devlake_tools_summary
from app.services.providers.base import (
    ChatMessage as ProviderChatMessage,
    MessageRole as ProviderMessageRole,
    ProviderConfig,
)
from app.services.mcp.server import MCPToolHandler
from app.services.mcp.errors import ToolErrorResponse, ErrorCategory
from app.services.mcp.error_handler import MCPErrorHandler, ErrorContext, RecoveryAction
from app.services.observability.service import ObservabilityService, get_observability_service
from app.services.observability.langfuse_client import TraceContext
from app.services.guardrails.models import GuardrailConfig, GuardrailResult
from app.services.guardrails.nemo import (
    NeMoGuardrailsAdapter,
    get_nemo_guardrails_adapter,
)
from app.services.guardrails.service import GuardrailsService, get_guardrails_service

if TYPE_CHECKING:
    from langchain_anthropic import ChatAnthropic
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
    from langchain_core.tools import StructuredTool
logger = structlog.get_logger()

# Default system prompt for NexusAI chat
NEXUSAI_SYSTEM_PROMPT = """You are NexusAI, an intelligent DevOps assistant that helps engineering teams understand and improve their software delivery performance.

## CRITICAL: You Have Tools - USE THEM!
You have access to many tools that can fetch REAL DATA. When users ask questions:
1. **USE THE TOOLS** to get actual data - don't just explain concepts
2. Check health first with `*_health_check` tools to verify services are available
3. Use list/search tools to explore available resources

## Your Capabilities:

### 1. DORA Metrics & DevLake (devlake_* tools)
- Fetch DORA metrics: Deployment Frequency, Lead Time, MTTR, Change Failure Rate
- Manage projects, connections, pipelines, and blueprints
- Analyze PR-Issue correlations
- DORA Benchmarks: Elite (multiple deploys/day), High (weekly), Medium (monthly), Low (monthly+)

### 2. Policy & Security (policy_* tools)
- Check user permissions with RBAC
- Apply data redaction to remove sensitive info (API keys, passwords, tokens)
- Query audit logs for compliance tracking

### 3. CI/CD Insights (ci_* tools)
- View build status and logs
- Analyze test results and failures
- Identify flaky tests
- Understand failure patterns

### 4. Repository & Code (repo_* tools)
- Search code across repositories
- Get file contents and blame information
- View git diffs and commits
- Find function/class definitions

### 5. Jira Integration (jira_* tools)
- Search and view issues
- Create and update tickets
- Track sprints
- Get project statistics

### 6. Observability (obs_* tools)
- Search distributed traces
- Query application logs
- View metrics (CPU, memory, error rate, etc.)
- Monitor and acknowledge alerts

## Error Handling - IMPORTANT!
Tool responses include structured error information. When you receive an error:

1. **Check the `success` field** - If `false`, there was an error
2. **Read the error category** to understand what went wrong:
   - `service_unavailable`: Service is down - suggest checking health
   - `not_found`: Resource doesn't exist - show available alternatives
   - `auth_required`: Missing credentials - guide user to provide token
   - `invalid_input`: Bad parameters - explain what's needed
   - `transient`: Temporary issue - the system will auto-retry

3. **Follow the guidance** in the error response:
   - `user_message`: Explain this to the user
   - `suggestions`: Offer these as options
   - `next_steps`: Guide the user through these steps

## Workflow Examples:
- "Show me DORA metrics" → `devlake_list_projects` then `devlake_get_dora_metrics`
- "Why did the build fail?" → `ci_list_builds` then `ci_get_failed_tests`
- "Search for auth code" → `repo_search_code`
- "What alerts are firing?" → `obs_list_alerts`
- "Create a bug ticket" → `jira_create_issue`
- "Who can access this project?" → `policy_check_permission`

## GitHub/DevLake Setup - IMPORTANT!
When a user wants to:
- Set up a GitHub project for DORA metrics
- Create a GitHub connection with a token
- Track a repository with DevLake
- Create a project from a GitHub repo

ALWAYS use `devlake_setup_github` - it handles everything in one step:
- Creates the GitHub connection (if not exists)
- Creates the DevLake project
- Sets up automatic data collection

Example: User says "connection name: abc token: ghp_xxx create github project with project name my-project and repo my-org/my-repo"
→ `devlake_setup_github(token="ghp_xxx", repo="my-org/my-repo", project_name="my-project")`

Only use `devlake_create_connection` for advanced cases where users ONLY want to create a connection without a project.

## CRITICAL: Tool Calling Format
When a user asks you to execute a tool or provides tool parameters:
1. You MUST call the tool using the function calling interface (if available)
2. If function calling is NOT available, output the tool call in this EXACT format:
   TOOL_CALL: tool_name(arg1="value1", arg2="value2")
   Example: TOOL_CALL: devlake_create_project(name="my-project", description="My awesome project")
3. DO NOT just describe what you would do - actually CALL the tool!
4. DO NOT say "I will call..." or "Let me execute..." - just output the TOOL_CALL directly
5. If the user provides: `devlake_create_connection --plugin=github --name=abc --token=xxx`
   Output: TOOL_CALL: devlake_create_connection(plugin="github", name="abc", token="xxx")
6. Wait for the tool result before responding to the user
7. For creating a GitHub project with token, use: TOOL_CALL: devlake_setup_github(token="ghp_xxx", repo="owner/repo", project_name="my-project")

## Response Style:
- Be concise and action-oriented
- Show actual data when available (use tools!)
- When errors occur, be helpful not apologetic - guide users to solutions
- Use bullet points and tables for clarity
- Provide specific recommendations based on data

Remember: **USE YOUR TOOLS** - users expect real data, not just explanations!"""


class ChatService:
    """Service for chat operations with MCP tool support."""

    def __init__(
        self,
        db: AsyncSession,
        user_id: str | None = None,
        mcp_servers: list[MCPServerConfig] | None = None,
        enable_builtin_tools: bool = True,
    ):
        self.db = db
        self.user_id = user_id
        self.mcp_servers = mcp_servers or []
        self.enable_builtin_tools = enable_builtin_tools
        self._mcp_tools: dict[str, tuple[str, MCPTool]] = {}  # tool_name -> (server_name, MCPTool)
        self._builtin_handlers: dict[str, MCPToolHandler] = {}  # tool_name -> handler
        self._error_handler: MCPErrorHandler | None = None  # Initialized after tools are loaded
        self._observability: ObservabilityService | None = None  # Langfuse tracing
        self._current_trace: TraceContext | None = None  # Current active trace
        self._langfuse_system_prompt: Any | None = None  # Langfuse PromptClient for system prompt
        self._guardrails: GuardrailsService | None = (
            get_guardrails_service() if settings.GUARDRAILS_ENABLED else None
        )
        self._nemo_guardrails: NeMoGuardrailsAdapter | None = (
            get_nemo_guardrails_adapter() if settings.NEMO_GUARDRAILS_ENABLED else None
        )
        self._stream_holdback_chars = max(0, int(settings.GUARDRAILS_STREAM_HOLDBACK_CHARS))

    async def initialize_mcp(self) -> None:
        """Initialize MCP server connections and discover tools."""
        # Initialize observability (Langfuse)
        try:
            self._observability = await get_observability_service()
            logger.info("Observability service initialized for chat")
        except Exception as e:
            logger.warning("Failed to initialize observability", error=str(e))
            self._observability = None

        # Fetch system prompt from Langfuse (with hardcoded fallback)
        try:
            from app.services.prompts.langfuse_manager import get_langfuse_prompt_manager

            manager = await get_langfuse_prompt_manager()
            if manager.enabled:
                self._langfuse_system_prompt = await manager.get_prompt(
                    "nexusai-system-prompt",
                    type="text",
                    fallback=NEXUSAI_SYSTEM_PROMPT,
                )
                if self._langfuse_system_prompt:
                    logger.info(
                        "System prompt loaded from Langfuse",
                        version=self._langfuse_system_prompt.version,
                        is_fallback=self._langfuse_system_prompt.is_fallback,
                    )
        except Exception as e:
            logger.debug("Langfuse prompt fetch skipped", error=str(e))

        # Initialize built-in DevLake tools
        if self.enable_builtin_tools:
            await self._initialize_builtin_tools()

        # Initialize external MCP servers
        if not self.user_id or not self.mcp_servers:
            pass  # Continue to initialize error handler
        else:
            for server_config in self.mcp_servers:
                try:
                    success = await mcp_manager.connect_server(self.user_id, server_config)
                    if success:
                        client = mcp_manager.get_client(self.user_id, server_config.name)
                        if client:
                            # Cache available tools
                            for tool in client.list_tools():
                                # Prefix tool name with server name to avoid collisions
                                full_name = f"{server_config.name}__{tool.name}"
                                self._mcp_tools[full_name] = (server_config.name, tool)
                            logger.info(
                                "MCP server connected for chat",
                                server=server_config.name,
                                tools=len(client.list_tools()),
                            )
                except Exception as e:
                    logger.error(
                        "Failed to connect MCP server for chat",
                        server=server_config.name,
                        error=str(e),
                    )

        # Initialize error handler with tool executor and available tools
        self._error_handler = MCPErrorHandler(
            tool_executor=self._execute_mcp_tool,
            available_tools=self._mcp_tools,
        )

    async def _initialize_builtin_tools(self) -> None:
        """Initialize built-in DevLake MCP tools."""
        try:
            mcp_server = get_mcp_server()
            for name, handler in mcp_server._tools.items():
                self._builtin_handlers[name] = handler
                # Also add to _mcp_tools for unified tool listing
                self._mcp_tools[name] = ("builtin", handler.tool)
            
            logger.info(
                "Built-in DevLake tools initialized",
                tool_count=len(self._builtin_handlers),
            )
        except Exception as e:
            logger.error("Failed to initialize built-in tools", error=str(e))

    async def cleanup_mcp(self) -> None:
        """Cleanup MCP connections."""
        if self.user_id:
            await mcp_manager.disconnect_all(self.user_id)
        # Built-in handlers don't need cleanup

    def _get_tenant_guardrail_policy_overrides(
        self,
        conversation: Conversation | None = None,
    ) -> tuple[str | None, dict[str, Any]]:
        """Resolve tenant-scoped guardrail overrides from settings and conversation."""
        tenant_id = get_current_tenant_id()
        overrides: dict[str, Any] = {}

        # Global per-tenant map from configuration JSON
        try:
            policies = json.loads(settings.GUARDRAILS_TENANT_POLICIES or "{}")
            if isinstance(policies, dict) and tenant_id and isinstance(policies.get(tenant_id), dict):
                overrides.update(policies.get(tenant_id, {}))
        except json.JSONDecodeError:
            logger.warning("Invalid GUARDRAILS_TENANT_POLICIES JSON; ignoring overrides")

        # Optional conversation-level policy (takes precedence over tenant map)
        if conversation and isinstance(conversation.settings, dict):
            conv_policy = conversation.settings.get("guardrails")
            if isinstance(conv_policy, dict):
                overrides.update(conv_policy)

            if not tenant_id:
                conv_tenant = conversation.settings.get("tenant_id")
                if isinstance(conv_tenant, str) and conv_tenant.strip():
                    tenant_id = conv_tenant

        return tenant_id, overrides

    def _resolve_guardrails_service(
        self,
        conversation: Conversation | None = None,
    ) -> tuple[GuardrailsService | None, str | None]:
        """Resolve effective guardrails service and tenant context for the request."""
        if not self._guardrails:
            return None, None

        tenant_id, overrides = self._get_tenant_guardrail_policy_overrides(conversation)
        if not overrides:
            return self._guardrails, tenant_id

        base = self._guardrails.config.model_dump()
        allowed_keys = set(GuardrailConfig.model_fields.keys())
        sanitized = {k: v for k, v in overrides.items() if k in allowed_keys}
        effective = GuardrailConfig(**(base | sanitized))
        return GuardrailsService(config=effective), tenant_id

    def _record_guardrails_observation(
        self,
        check_type: str,
        result: GuardrailResult,
    ) -> None:
        """Record guardrail outcomes in observability when available."""
        if not self._observability:
            return
        self._observability.record_guardrails_check(
            trace=self._current_trace,
            check_type=check_type,
            passed=not result.blocked,
            details={
                "modified": result.modified,
                "threat_level": result.threat_level.value,
                "threats_detected": result.threats_detected[:5],
                "check_time_ms": result.check_time_ms,
            },
            blocked_reason=result.message,
        )

    async def _apply_input_guardrails(
        self,
        text: str,
        conversation: Conversation | None = None,
    ) -> GuardrailResult | None:
        """Run input guardrails when enabled."""
        service, tenant_id = self._resolve_guardrails_service(conversation)
        if not service:
            return None
        result = await service.check_input(
            text=text,
            user_id=self.user_id,
            tenant_id=tenant_id,
        )
        self._record_guardrails_observation("input", result)
        return result

    async def _apply_output_guardrails(
        self,
        text: str,
        conversation: Conversation | None = None,
    ) -> GuardrailResult | None:
        """Run output guardrails when enabled."""
        service, tenant_id = self._resolve_guardrails_service(conversation)
        if not service:
            return None
        result = await service.check_output(
            text=text,
            user_id=self.user_id,
            tenant_id=tenant_id,
        )
        self._record_guardrails_observation("output", result)
        return result

    async def _apply_stream_output_guardrails(
        self,
        text: str,
        conversation: Conversation | None = None,
    ) -> GuardrailResult | None:
        """Run lightweight stream-time output guardrails."""
        service, tenant_id = self._resolve_guardrails_service(conversation)
        if not service:
            return None
        result = await service.check_stream_output(
            text=text,
            user_id=self.user_id,
            tenant_id=tenant_id,
        )
        self._record_guardrails_observation("stream_output", result)
        return result

    async def _stream_guardrail_gate(
        self,
        raw_text: str,
        emitted_chars: int,
        conversation: Conversation,
    ) -> tuple[str, int, bool]:
        """
        Gate incremental stream output through lightweight guardrails.

        Returns:
            (text_to_emit, new_emitted_chars, blocked)
        """
        if not self._guardrails:
            if emitted_chars >= len(raw_text):
                return "", emitted_chars, False
            return raw_text[emitted_chars:], len(raw_text), False

        stream_guard = await self._apply_stream_output_guardrails(
            raw_text,
            conversation=conversation,
        )
        if stream_guard and stream_guard.blocked:
            blocked_text = (
                stream_guard.message
                or "The response was blocked by safety guardrails."
            )
            return blocked_text, emitted_chars, True

        # Keep a holdback tail to reduce risk of leaking partially unsafe content.
        safe_upto = max(0, len(raw_text) - self._stream_holdback_chars)
        if safe_upto <= emitted_chars:
            return "", emitted_chars, False
        return raw_text[emitted_chars:safe_upto], safe_upto, False

    def _to_nemo_messages(
        self,
        messages: list[Message],
        system_prompt: str | None,
    ) -> list[dict[str, str]]:
        """Convert stored conversation messages to NeMo message format."""
        nemo_messages: list[dict[str, str]] = []

        if system_prompt:
            effective_prompt = system_prompt
        elif self._langfuse_system_prompt and not self._langfuse_system_prompt.is_fallback:
            effective_prompt = self._langfuse_system_prompt.compile()
        else:
            effective_prompt = NEXUSAI_SYSTEM_PROMPT
        if effective_prompt:
            nemo_messages.append({"role": "system", "content": effective_prompt})

        for msg in messages:
            if msg.role not in (
                MessageRole.SYSTEM.value,
                MessageRole.USER.value,
                MessageRole.ASSISTANT.value,
            ):
                continue
            if not msg.content:
                continue
            nemo_messages.append({"role": msg.role, "content": msg.content})

        return nemo_messages

    async def _generate_with_nemo(
        self,
        messages: list[Message],
        system_prompt: str | None,
    ) -> str | None:
        """Generate response with NeMo Guardrails when configured."""
        if not self._nemo_guardrails:
            return None
        nemo_messages = self._to_nemo_messages(messages, system_prompt)
        return await self._nemo_guardrails.generate(nemo_messages)

    def _create_langchain_tools(self) -> list[StructuredTool]:
        """Convert MCP tools to LangChain StructuredTool format."""
        from langchain_core.tools import StructuredTool

        lc_tools = []

        for full_name, (server_name, mcp_tool) in self._mcp_tools.items():
            # Create a Pydantic model from the JSON schema
            input_schema = mcp_tool.input_schema
            properties = input_schema.get("properties", {})
            required = input_schema.get("required", [])

            # Build field definitions for Pydantic model
            field_definitions = {}
            for prop_name, prop_schema in properties.items():
                prop_type = prop_schema.get("type", "string")
                # Map JSON schema types to Python types
                type_map = {
                    "string": str,
                    "integer": int,
                    "number": float,
                    "boolean": bool,
                    "array": list,
                    "object": dict,
                }
                python_type = type_map.get(prop_type, str)

                # If not required, make it optional
                if prop_name in required:
                    field_definitions[prop_name] = (python_type, ...)
                else:
                    field_definitions[prop_name] = (python_type | None, None)

            # Create dynamic Pydantic model
            if field_definitions:
                args_model = create_model(f"{full_name}_Args", **field_definitions)
            else:
                args_model = None

            # Capture variables for closure
            _server = server_name
            _tool_name = mcp_tool.name if server_name == "builtin" else full_name

            # Create async tool function
            async def _call_tool(
                _srv=_server,
                _tn=_tool_name,
                **kwargs,
            ) -> str:
                return await self._execute_tool(_srv, _tn, kwargs)

            # Create LangChain tool
            tool = StructuredTool.from_function(
                func=_call_tool,
                name=full_name,
                description=mcp_tool.description,
                args_schema=args_model,
                coroutine=_call_tool,
            )
            lc_tools.append(tool)

        return lc_tools

    async def _format_tool_result_with_recovery(
        self,
        tool_name: str,
        result: str,
        original_arguments: dict | None = None,
        _recovery_depth: int = 0,
    ) -> AsyncGenerator[str, None]:
        """Format a tool result with intelligent error recovery.

        When an error is detected, uses the error handler to determine and
        execute recovery actions (like health checks) automatically.

        Yields formatted output chunks for streaming.

        Args:
            tool_name: Name of the tool that was executed
            result: The tool result string (may be JSON)
            original_arguments: Arguments passed to the tool
            _recovery_depth: Internal counter to prevent infinite recovery loops
        """
        from app.core.config import settings

        # Prevent infinite recovery loops - use configured max depth
        max_recovery_depth = settings.MCP_MAX_RECOVERY_DEPTH

        try:
            result_dict = json.loads(result)
        except json.JSONDecodeError:
            # Not JSON, just return raw result with preview
            preview = result[:500] + "..." if len(result) > 500 else result
            yield f"\n\n**[Tool: {tool_name}]**\n{preview}\n"
            return

        # Check for success/error structure
        is_success = result_dict.get("success", True)

        if is_success:
            # Format successful result
            yield self._format_success_result(tool_name, result_dict)
            return

        # Error detected - use error handler for intelligent recovery
        if self._error_handler:
            error_context = self._error_handler.parse_error_from_result(
                tool_name=tool_name,
                result=result,
                original_arguments=original_arguments or {},
            )

            if error_context:
                # Analyze error and get recovery plan
                recovery_plan = self._error_handler.analyze_error(error_context)

                # Format the error message
                yield self._format_error_result(tool_name, result_dict)

                # Execute recovery action if available (only if we haven't exceeded max depth)
                if recovery_plan.auto_execute and recovery_plan.tool_to_run and _recovery_depth < max_recovery_depth:
                    yield f"\n\n**🔄 Automatic Recovery: {recovery_plan.user_message}**\n"

                    try:
                        recovery_result = await self._error_handler.execute_recovery(recovery_plan)
                        if recovery_result:
                            # Format the recovery result (with incremented depth to prevent loops)
                            yield f"\n**Recovery Result ({recovery_plan.tool_to_run}):**\n"
                            async for chunk in self._format_tool_result_with_recovery(
                                recovery_plan.tool_to_run,
                                recovery_result,
                                _recovery_depth=_recovery_depth + 1,
                            ):
                                yield chunk
                    except Exception as e:
                        logger.error(f"Recovery action failed: {e}")
                        yield f"\n*Recovery action failed: {e}*\n"

                # Add recovery suggestions even if not auto-executing
                elif recovery_plan.user_message:
                    yield f"\n\n**💡 Suggestion:** {recovery_plan.user_message}\n"

                return

        # Fallback to basic error formatting if no error handler
        yield self._format_error_result(tool_name, result_dict)

    def _format_success_result(self, tool_name: str, result_dict: dict) -> str:
        """Format a successful tool result."""
        lines = [f"\n\n**✅ {tool_name}**"]

        # Include widget block if present (for rich UI rendering)
        if "widget" in result_dict and result_dict["widget"]:
            lines.append(f"\n{result_dict['widget']}")

        # Extract key information based on common patterns
        if "message" in result_dict:
            lines.append(f"\n{result_dict['message']}")

        if "count" in result_dict:
            lines.append(f"Found: {result_dict['count']} item(s)")

        # Health check results
        if "healthy" in result_dict:
            status = "healthy" if result_dict["healthy"] else "unhealthy"
            lines.append(f"\nStatus: **{status}**")
            if "base_url" in result_dict:
                lines.append(f"URL: {result_dict['base_url']}")

        # DORA metrics formatting - support both 'metrics' and 'summary' structures
        dora_summary = result_dict.get("summary") or result_dict.get("metrics")
        if dora_summary and isinstance(dora_summary, dict):
            # Check if it looks like DORA data
            dora_keys = ["deployment_frequency", "lead_time_for_changes", "mean_time_to_recovery", "change_failure_rate", "overall_rating"]
            if any(key in dora_summary for key in dora_keys):
                lines.append("\n**DORA Metrics Summary:**")

                if "overall_rating" in dora_summary:
                    lines.append(f"  - Overall Rating: **{dora_summary['overall_rating']}**")

                if "deployment_frequency" in dora_summary:
                    df = dora_summary["deployment_frequency"]
                    if isinstance(df, dict):
                        lines.append(f"  - Deployment Frequency: {df.get('value', 'N/A')}/day ({df.get('rating', 'N/A')})")
                        if df.get("explanation"):
                            lines.append(f"    {df['explanation']}")

                if "lead_time_for_changes" in dora_summary:
                    lt = dora_summary["lead_time_for_changes"]
                    if isinstance(lt, dict):
                        lines.append(f"  - Lead Time for Changes: {lt.get('value', 'N/A')} hours ({lt.get('rating', 'N/A')})")
                        if lt.get("explanation"):
                            lines.append(f"    {lt['explanation']}")

                if "mean_time_to_recovery" in dora_summary:
                    mttr = dora_summary["mean_time_to_recovery"]
                    if isinstance(mttr, dict):
                        lines.append(f"  - Mean Time to Recovery: {mttr.get('value', 'N/A')} hours ({mttr.get('rating', 'N/A')})")
                        if mttr.get("explanation"):
                            lines.append(f"    {mttr['explanation']}")

                if "change_failure_rate" in dora_summary:
                    cfr = dora_summary["change_failure_rate"]
                    if isinstance(cfr, dict):
                        lines.append(f"  - Change Failure Rate: {cfr.get('value', 'N/A')}% ({cfr.get('rating', 'N/A')})")
                        if cfr.get("explanation"):
                            lines.append(f"    {cfr['explanation']}")

        # Projects listing
        if "projects" in result_dict and result_dict["projects"]:
            projects = result_dict["projects"][:5]
            lines.append("\n**Projects:**")
            for p in projects:
                name = p.get("name", p) if isinstance(p, dict) else p
                lines.append(f"  - {name}")
            if len(result_dict["projects"]) > 5:
                lines.append(f"  ... and {len(result_dict['projects']) - 5} more")

        # Connections listing
        if "connections" in result_dict and result_dict["connections"]:
            conns = result_dict["connections"][:5]
            lines.append("\n**Connections:**")
            for c in conns:
                name = c.get("name", c) if isinstance(c, dict) else c
                plugin = c.get("plugin", "") if isinstance(c, dict) else ""
                lines.append(f"  - {name}" + (f" ({plugin})" if plugin else ""))
            if len(result_dict["connections"]) > 5:
                lines.append(f"  ... and {len(result_dict['connections']) - 5} more")

        # Blueprints listing
        if "blueprints" in result_dict and result_dict["blueprints"]:
            blueprints = result_dict["blueprints"][:5]
            lines.append("\n**Blueprints:**")
            for b in blueprints:
                name = b.get("name", b) if isinstance(b, dict) else b
                lines.append(f"  - {name}")

        # Pipeline status
        if "pipeline" in result_dict:
            pipeline = result_dict["pipeline"]
            lines.append("\n**Pipeline:**")
            lines.append(f"  - Status: {pipeline.get('status', 'N/A')}")
            if "id" in pipeline:
                lines.append(f"  - ID: {pipeline['id']}")

        # Next steps suggestions
        if "next_steps" in result_dict:
            lines.append("\n**Next steps:**")
            for step in result_dict["next_steps"][:3]:
                lines.append(f"  - {step}")

        return "\n".join(lines) + "\n"

    def _format_error_result(self, tool_name: str, result_dict: dict) -> str:
        """Format an error tool result."""
        error_info = result_dict.get("error", {})
        guidance = result_dict.get("guidance", {})
        retry_info = result_dict.get("retry", {})

        # Handle string error format
        if isinstance(error_info, str):
            return f"\n\n**❌ {tool_name} - Error**\nMessage: {error_info}\n"

        category = error_info.get("category", "internal")
        message = error_info.get("message", "Unknown error")

        lines = [f"\n\n**❌ {tool_name} - Error**"]
        lines.append(f"Category: `{category}`")
        lines.append(f"Message: {message}")

        # Add user-friendly guidance
        if guidance.get("user_message"):
            lines.append(f"\n**What this means:** {guidance['user_message']}")

        if guidance.get("suggestions"):
            lines.append("\n**Suggestions:**")
            for suggestion in guidance["suggestions"][:4]:
                lines.append(f"  - {suggestion}")

        if guidance.get("next_steps"):
            lines.append("\n**Next steps:**")
            for i, step in enumerate(guidance["next_steps"][:3], 1):
                lines.append(f"  {i}. {step}")

        # Add retry info if available
        if retry_info.get("retryable"):
            retry_after = retry_info.get("retry_after_seconds", "a moment")
            lines.append(f"\n*This error is temporary - try again in {retry_after}s*")

        # Add related tools
        help_info = result_dict.get("help", {})
        if help_info.get("related_tools"):
            lines.append(f"\n**Related tools:** {', '.join(help_info['related_tools'])}")

        return "\n".join(lines) + "\n"

    async def _execute_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any],
        max_retries: int = 2,
    ) -> str:
        """Execute a tool with retry logic for transient errors."""
        import asyncio
        
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                result = await self._execute_tool_once(server_name, tool_name, arguments)
                
                # Check if result indicates a retryable error
                if isinstance(result, str):
                    try:
                        result_dict = json.loads(result)
                        if (
                            result_dict.get("success") is False
                            and result_dict.get("retry", {}).get("retryable")
                            and attempt < max_retries
                        ):
                            retry_after = result_dict.get("retry", {}).get("retry_after_seconds", 2)
                            logger.info(
                                f"Tool {tool_name} returned retryable error, retrying in {retry_after}s",
                                attempt=attempt + 1,
                                max_retries=max_retries,
                            )
                            await asyncio.sleep(retry_after)
                            continue
                    except json.JSONDecodeError:
                        pass  # Not JSON, return as-is
                
                return result
                
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    logger.warning(
                        f"Tool {tool_name} failed, retrying",
                        attempt=attempt + 1,
                        error=str(e),
                    )
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                raise
        
        # Should not reach here, but handle gracefully
        logger.error("Tool execution failed after retries", tool=tool_name, error=str(last_error))
        return json.dumps({
            "success": False,
            "error": {
                "category": "internal",
                "message": f"Tool execution failed after {max_retries} retries: {last_error}",
            },
        })

    async def _execute_tool_once(self, server_name: str, tool_name: str, arguments: dict[str, Any]) -> str:
        """Execute a tool once without retry logic."""
        logger.info(
            "Executing tool",
            server_name=server_name,
            tool_name=tool_name,
            argument_keys=list(arguments.keys()),
        )
        logger.debug("Tool arguments", tool_name=tool_name, arguments=arguments)

        try:
            # Check if it's a built-in tool
            if server_name == "builtin" and tool_name in self._builtin_handlers:
                handler = self._builtin_handlers[tool_name]
                context = {"user_id": self.user_id}
                result = await handler.execute(arguments, context)
                return json.dumps(result, indent=2, default=str)

            # External MCP server
            if not self.user_id:
                return json.dumps({
                    "success": False,
                    "error": {
                        "category": "auth_required",
                        "message": "No user context for MCP call",
                    },
                })

            result = await mcp_manager.call_tool(
                self.user_id, server_name, tool_name, arguments
            )
            if result is None:
                return json.dumps({
                    "success": False,
                    "error": {
                        "category": "internal",
                        "message": "Tool call returned no result",
                    },
                })

            # Extract content from MCP response
            if isinstance(result, dict):
                content = result.get("content", [])
                if content and isinstance(content, list):
                    texts = [c.get("text", "") for c in content if c.get("type") == "text"]
                    return "\n".join(texts) if texts else json.dumps(result, default=str)
                return json.dumps(result, indent=2, default=str)
            return str(result)

        except Exception as e:
            logger.error("Tool execution failed", tool=tool_name, error=str(e))
            return json.dumps({
                "success": False,
                "error": {
                    "category": "internal",
                    "message": "Tool execution failed. Please try again.",
                },
                "guidance": {
                    "suggestions": ["Try the operation again", "Check if the service is available"],
                },
            })

    def _get_mcp_tools_description(self) -> str:
        """Get a description of available MCP tools for the system prompt."""
        if not self._mcp_tools:
            return ""

        # Group tools by service category
        categories = {
            # DevLake tools
            "devlake_health": {"title": "DevLake - Health & Status", "tools": []},
            "devlake_projects": {"title": "DevLake - Projects", "tools": []},
            "devlake_connections": {"title": "DevLake - Connections", "tools": []},
            "devlake_blueprints": {"title": "DevLake - Blueprints", "tools": []},
            "devlake_pipelines": {"title": "DevLake - Pipelines", "tools": []},
            "devlake_dora": {"title": "DevLake - DORA Metrics", "tools": []},
            "devlake_stats": {"title": "DevLake - Statistics", "tools": []},
            "devlake_correlation": {"title": "DevLake - PR-Issue Correlation", "tools": []},
            # Policy tools
            "policy": {"title": "Policy & Security (RBAC, Redaction, Audit)", "tools": []},
            # CI/CD tools
            "ci": {"title": "CI/CD (Builds, Tests, Analysis)", "tools": []},
            # Repository tools
            "repo": {"title": "Repository (Code Search, Files, Git)", "tools": []},
            # Jira tools
            "jira": {"title": "Jira (Issues, Sprints, Projects)", "tools": []},
            # Observability tools
            "obs": {"title": "Observability (Traces, Logs, Metrics, Alerts)", "tools": []},
            # Other
            "other": {"title": "Other Tools", "tools": []},
        }

        for full_name, (server_name, mcp_tool) in self._mcp_tools.items():
            # Build parameter info from input_schema
            params_info = ""
            input_schema = mcp_tool.input_schema
            if input_schema and input_schema.get("properties"):
                required = input_schema.get("required", [])
                param_list = []
                for param_name, param_schema in input_schema.get("properties", {}).items():
                    param_type = param_schema.get("type", "string")
                    is_required = param_name in required
                    param_desc = param_schema.get("description", "")
                    # Truncate long descriptions
                    if len(param_desc) > 60:
                        param_desc = param_desc[:57] + "..."
                    req_marker = "*" if is_required else ""
                    param_list.append(f"{param_name}{req_marker}")
                if param_list:
                    params_info = f" (params: {', '.join(param_list)})"

            tool_info = f"- **{mcp_tool.name}**: {mcp_tool.description}{params_info}"
            name = mcp_tool.name.lower()

            # Categorize by prefix/pattern
            if name.startswith("devlake_"):
                if "health" in name:
                    categories["devlake_health"]["tools"].append(tool_info)
                elif "project" in name and "stats" not in name and "contributors" not in name:
                    categories["devlake_projects"]["tools"].append(tool_info)
                elif "connection" in name:
                    categories["devlake_connections"]["tools"].append(tool_info)
                elif "blueprint" in name:
                    categories["devlake_blueprints"]["tools"].append(tool_info)
                elif "pipeline" in name:
                    categories["devlake_pipelines"]["tools"].append(tool_info)
                elif "dora" in name:
                    categories["devlake_dora"]["tools"].append(tool_info)
                elif "stats" in name or "contributors" in name:
                    categories["devlake_stats"]["tools"].append(tool_info)
                elif "correlation" in name or "pr_issue" in name:
                    categories["devlake_correlation"]["tools"].append(tool_info)
                else:
                    categories["other"]["tools"].append(tool_info)
            elif name.startswith("policy_"):
                categories["policy"]["tools"].append(tool_info)
            elif name.startswith("ci_"):
                categories["ci"]["tools"].append(tool_info)
            elif name.startswith("repo_"):
                categories["repo"]["tools"].append(tool_info)
            elif name.startswith("jira_"):
                categories["jira"]["tools"].append(tool_info)
            elif name.startswith("obs_"):
                categories["obs"]["tools"].append(tool_info)
            else:
                categories["other"]["tools"].append(tool_info)

        # Build description
        tool_desc = "\n\n## Available Tools (use these to help users!):\n"
        tool_desc += "You have access to the following tools. USE THEM when users ask questions.\n"

        for cat_key, cat_data in categories.items():
            if cat_data["tools"]:
                tool_desc += f"\n### {cat_data['title']}\n"
                tool_desc += "\n".join(cat_data["tools"]) + "\n"

        tool_desc += """

## TOOL EXECUTION - YOU MUST FOLLOW THIS FORMAT EXACTLY:

When a user asks about DevLake, data connections, projects, or metrics, you MUST output a tool call.

### REQUIRED FORMAT - Output this EXACT syntax:

TOOL_CALL: tool_name(arg='value')

### EXAMPLES OF CORRECT OUTPUT:

User: "check if devlake is running"
You output: TOOL_CALL: devlake_health_check()

User: "list my projects"
You output: TOOL_CALL: devlake_list_projects()

User: "create a project called test"
You output: TOOL_CALL: devlake_create_project(name='test')

User: "show my github connections"
You output: TOOL_CALL: devlake_list_connections()

### CRITICAL RULES:

1. ALWAYS start with "TOOL_CALL: " prefix (with the colon and space)
2. Output the tool call IMMEDIATELY - do not explain first
3. Use single quotes for string values: name='value'
4. For tools with no arguments, use empty parentheses: devlake_health_check()
5. The system will execute your tool call and show the results
6. If you encounter any error, first run: TOOL_CALL: devlake_health_check()

### WRONG vs RIGHT:

WRONG: "I'll check the health of DevLake for you."
RIGHT: TOOL_CALL: devlake_health_check()

WRONG: "Let me run the health check tool"
RIGHT: TOOL_CALL: devlake_health_check()

WRONG: "The devlake_health_check() function will verify..."
RIGHT: TOOL_CALL: devlake_health_check()

OUTPUT THE TOOL_CALL NOW - DO NOT DESCRIBE IT!
"""

        return tool_desc

    def _get_fallback_provider_and_model(self) -> tuple[ModelProvider, str]:
        """Get a fallback provider and model when the requested one is unavailable.

        Uses DEFAULT_AI_PROVIDER from settings if available, otherwise checks
        for any provider with a valid API key.
        """
        default_provider = getattr(settings, "DEFAULT_AI_PROVIDER", "").lower()

        # Try the configured default provider first
        if default_provider == "google" and settings.GOOGLE_API_KEY:
            return ModelProvider.GOOGLE, settings.GOOGLE_DEFAULT_MODEL
        if default_provider == "anthropic" and settings.ANTHROPIC_API_KEY:
            return ModelProvider.ANTHROPIC, settings.ANTHROPIC_DEFAULT_MODEL
        if default_provider == "openai" and settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("sk-your"):
            return ModelProvider.OPENAI, settings.OPENAI_DEFAULT_MODEL
        if default_provider == "ollama" and getattr(settings, "OLLAMA_BASE_URL", None):
            return ModelProvider.OLLAMA, settings.OLLAMA_DEFAULT_MODEL

        # Check any available provider
        if settings.GOOGLE_API_KEY:
            return ModelProvider.GOOGLE, settings.GOOGLE_DEFAULT_MODEL
        if settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("sk-your"):
            return ModelProvider.OPENAI, settings.OPENAI_DEFAULT_MODEL
        if settings.ANTHROPIC_API_KEY:
            return ModelProvider.ANTHROPIC, settings.ANTHROPIC_DEFAULT_MODEL
        if getattr(settings, "OLLAMA_BASE_URL", None):
            return ModelProvider.OLLAMA, settings.OLLAMA_DEFAULT_MODEL

        # Ultimate fallback to Ollama (may fail if not running)
        return ModelProvider.OLLAMA, settings.OLLAMA_DEFAULT_MODEL

    def _get_llm(
        self,
        provider: ModelProvider,
        model_name: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        streaming: bool = True,
    ) -> Any:
        """Get LLM instance based on provider.

        If the requested provider's API key is not available, falls back to
        an available provider based on DEFAULT_AI_PROVIDER or key availability.
        """
        common_kwargs = {
            "temperature": temperature,
            "max_tokens": max_tokens,
            "streaming": streaming,
        }

        # ALWAYS use DEFAULT_AI_PROVIDER if set and different from requested provider
        # This ensures environment configuration takes precedence over stored conversation settings
        original_provider = provider
        default_provider_str = getattr(settings, "DEFAULT_AI_PROVIDER", "").lower()

        # Map string to ModelProvider enum
        default_provider_map = {
            "google": ModelProvider.GOOGLE,
            "anthropic": ModelProvider.ANTHROPIC,
            "openai": ModelProvider.OPENAI,
            "ollama": ModelProvider.OLLAMA,
        }
        configured_default = default_provider_map.get(default_provider_str)

        # If DEFAULT_AI_PROVIDER is set and is different from requested, use the default
        if configured_default and configured_default != provider:
            logger.info(
                "Overriding conversation provider with DEFAULT_AI_PROVIDER from environment",
                conversation_provider=provider.value,
                default_provider=default_provider_str,
            )
            provider, model_name = self._get_fallback_provider_and_model()
        else:
            # Always use model from settings to avoid stale database values
            if provider == ModelProvider.GOOGLE:
                model_name = settings.GOOGLE_DEFAULT_MODEL
            elif provider == ModelProvider.ANTHROPIC:
                model_name = settings.ANTHROPIC_DEFAULT_MODEL
            elif provider == ModelProvider.OPENAI:
                model_name = settings.OPENAI_DEFAULT_MODEL
            elif provider == ModelProvider.OLLAMA:
                model_name = settings.OLLAMA_DEFAULT_MODEL

        # Also validate that the requested provider has a valid API key
        if provider == ModelProvider.ANTHROPIC and not settings.ANTHROPIC_API_KEY:
            logger.warning(
                "Requested Anthropic provider but ANTHROPIC_API_KEY not set, falling back",
                original_provider=provider.value,
            )
            provider, model_name = self._get_fallback_provider_and_model()
        elif provider == ModelProvider.OPENAI and (not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY.startswith("sk-your")):
            logger.warning(
                "Requested OpenAI provider but OPENAI_API_KEY not set, falling back",
                original_provider=provider.value,
            )
            provider, model_name = self._get_fallback_provider_and_model()
        elif provider == ModelProvider.GOOGLE and not settings.GOOGLE_API_KEY:
            logger.warning(
                "Requested Google provider but GOOGLE_API_KEY not set, falling back",
                original_provider=provider.value,
            )
            provider, model_name = self._get_fallback_provider_and_model()
        elif provider == ModelProvider.OLLAMA and not getattr(settings, "OLLAMA_BASE_URL", None):
            logger.warning(
                "Requested Ollama provider but OLLAMA_BASE_URL not set, falling back",
                original_provider=provider.value,
            )
            provider, model_name = self._get_fallback_provider_and_model()

        if original_provider != provider:
            logger.info(
                "Provider fallback occurred",
                original=original_provider.value,
                fallback=provider.value,
                model=model_name,
            )

        if provider == ModelProvider.OPENAI:
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=model_name,
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_API_BASE,
                **common_kwargs,
            )
        elif provider == ModelProvider.ANTHROPIC:
            from langchain_anthropic import ChatAnthropic

            return ChatAnthropic(
                model=model_name,
                api_key=settings.ANTHROPIC_API_KEY,
                **common_kwargs,
            )
        elif provider == ModelProvider.GOOGLE:
            from langchain_google_genai import ChatGoogleGenerativeAI

            return ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=settings.GOOGLE_API_KEY,
                convert_system_message_to_human=True,  # Google doesn't natively support system messages
                **common_kwargs,
            )
        else:
            # Default to OpenAI-compatible (Ollama)
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=model_name,
                base_url=settings.OLLAMA_BASE_URL + "/v1",
                api_key="ollama",
                **common_kwargs,
            )

    def _convert_messages(
        self,
        messages: list[Message],
        system_prompt: str | None = None,
        include_mcp_tools: bool = True,
    ) -> list[SystemMessage | HumanMessage | AIMessage]:
        """Convert database messages to LangChain messages.

        Note: Google's Gemini API requires alternating user/model messages.
        This function merges consecutive messages of the same role to ensure
        compatibility with all providers.
        """
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        lc_messages = []

        # Use custom system prompt, or Langfuse-managed prompt, or hardcoded default
        if system_prompt:
            effective_prompt = system_prompt
        elif self._langfuse_system_prompt and not self._langfuse_system_prompt.is_fallback:
            effective_prompt = self._langfuse_system_prompt.compile()
        else:
            effective_prompt = NEXUSAI_SYSTEM_PROMPT

        # Add MCP tools description to system prompt if available
        if include_mcp_tools and self._mcp_tools:
            effective_prompt += self._get_mcp_tools_description()

        lc_messages.append(SystemMessage(content=effective_prompt))

        # Track the last role to merge consecutive messages of the same role
        # This is required for Google Gemini which requires alternating user/model messages
        last_role = None

        for msg in messages:
            if msg.role == MessageRole.SYSTEM.value:
                # System messages are typically at the start, merge with existing
                if lc_messages and isinstance(lc_messages[-1], SystemMessage):
                    lc_messages[-1] = SystemMessage(
                        content=lc_messages[-1].content + "\n\n" + msg.content
                    )
                else:
                    lc_messages.append(SystemMessage(content=msg.content))
                last_role = "system"
            elif msg.role == MessageRole.USER.value:
                # Merge consecutive user messages
                if last_role == "user" and lc_messages and isinstance(lc_messages[-1], HumanMessage):
                    lc_messages[-1] = HumanMessage(
                        content=lc_messages[-1].content + "\n\n" + msg.content
                    )
                else:
                    lc_messages.append(HumanMessage(content=msg.content))
                last_role = "user"
            elif msg.role == MessageRole.ASSISTANT.value:
                # Merge consecutive assistant messages
                if last_role == "assistant" and lc_messages and isinstance(lc_messages[-1], AIMessage):
                    lc_messages[-1] = AIMessage(
                        content=lc_messages[-1].content + "\n\n" + msg.content
                    )
                else:
                    lc_messages.append(AIMessage(content=msg.content))
                last_role = "assistant"

        return lc_messages

    def _convert_provider_messages(
        self,
        messages: list[Message],
        system_prompt: str | None = None,
        include_mcp_tools: bool = True,
    ) -> list[ProviderChatMessage]:
        """Convert database messages to provider messages."""
        provider_messages: list[ProviderChatMessage] = []

        if system_prompt:
            effective_prompt = system_prompt
        elif self._langfuse_system_prompt and not self._langfuse_system_prompt.is_fallback:
            effective_prompt = self._langfuse_system_prompt.compile()
        else:
            effective_prompt = NEXUSAI_SYSTEM_PROMPT
        if include_mcp_tools and self._mcp_tools:
            effective_prompt += self._get_mcp_tools_description()

        provider_messages.append(
            ProviderChatMessage(role=ProviderMessageRole.SYSTEM, content=effective_prompt)
        )

        for msg in messages:
            if msg.role == MessageRole.SYSTEM.value:
                provider_messages.append(
                    ProviderChatMessage(role=ProviderMessageRole.SYSTEM, content=msg.content)
                )
            elif msg.role == MessageRole.USER.value:
                provider_messages.append(
                    ProviderChatMessage(role=ProviderMessageRole.USER, content=msg.content)
                )
            elif msg.role == MessageRole.ASSISTANT.value:
                provider_messages.append(
                    ProviderChatMessage(role=ProviderMessageRole.ASSISTANT, content=msg.content)
                )

        return provider_messages

    async def create_conversation(
        self,
        user_id: str,
        title: str = "New Conversation",
        model_provider: ModelProvider = ModelProvider.OPENAI,
        model_name: str | None = None,
        system_prompt: str | None = None,
    ) -> Conversation:
        """Create a new conversation."""
        if model_name is None:
            if model_provider == ModelProvider.OPENAI:
                model_name = settings.OPENAI_DEFAULT_MODEL
            elif model_provider == ModelProvider.ANTHROPIC:
                model_name = settings.ANTHROPIC_DEFAULT_MODEL
            elif model_provider == ModelProvider.GOOGLE:
                model_name = settings.GOOGLE_DEFAULT_MODEL
            else:
                model_name = settings.OLLAMA_DEFAULT_MODEL

        conversation = Conversation(
            user_id=user_id,
            title=title,
            model_provider=model_provider.value,
            model_name=model_name,
            system_prompt=system_prompt,
        )
        self.db.add(conversation)
        await self.db.flush()
        return conversation

    async def get_conversation(
        self,
        conversation_id: str,
        user_id: str,
    ) -> Conversation | None:
        """Get a conversation by ID."""
        result = await self.db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_conversations(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Conversation]:
        """List user's conversations."""
        result = await self.db.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_conversations(self, user_id: str) -> int:
        """Count total conversations for a user."""
        from sqlalchemy import func
        result = await self.db.execute(
            select(func.count()).select_from(Conversation).where(Conversation.user_id == user_id)
        )
        return result.scalar() or 0

    async def add_message(
        self,
        conversation: Conversation,
        role: MessageRole,
        content: str,
        model_name: str | None = None,
        token_usage: dict[str, int] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        """Add a message to a conversation."""
        position = conversation.message_count

        message = Message(
            conversation_id=conversation.id,
            role=role.value,
            content=content,
            model_name=model_name,
            position=position,
            metadata=metadata or {},
        )

        if token_usage:
            message.prompt_tokens = token_usage.get("prompt_tokens")
            message.completion_tokens = token_usage.get("completion_tokens")
            message.total_tokens = token_usage.get("total_tokens")
            conversation.total_tokens += token_usage.get("total_tokens", 0)

        conversation.message_count += 1
        self.db.add(message)
        await self.db.flush()

        return message

    async def get_messages(
        self,
        conversation_id: str,
        limit: int | None = None,
    ) -> list[Message]:
        """Get messages for a conversation."""
        query = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.position)
        )
        if limit:
            query = query.limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def chat(
        self,
        conversation: Conversation,
        user_message: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Message:
        """Send a message and get AI response (non-streaming)."""
        start_time = time.time()
        trace = None
        error_msg = None

        # Start Langfuse trace
        if self._observability:
            trace = self._observability.langfuse.create_trace(
                name="chat",
                user_id=self.user_id,
                session_id=str(conversation.id),
                metadata={
                    "model": conversation.model_name,
                    "provider": conversation.model_provider,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                tags=["chat", conversation.model_provider],
            )
            self._current_trace = trace

        try:
            # Apply input guardrails before persisting/sending user text
            message_to_store = user_message
            input_guard = await self._apply_input_guardrails(
                user_message,
                conversation=conversation,
            )
            if input_guard:
                if input_guard.blocked:
                    blocked_text = (
                        input_guard.message
                        or "Your message was blocked by safety guardrails."
                    )
                    await self.add_message(
                        conversation=conversation,
                        role=MessageRole.USER,
                        content=user_message,
                    )
                    return await self.add_message(
                        conversation=conversation,
                        role=MessageRole.ASSISTANT,
                        content=blocked_text,
                        model_name=conversation.model_name,
                    )
                if input_guard.modified and input_guard.modified_content:
                    message_to_store = input_guard.modified_content

            # Add user message
            await self.add_message(conversation, MessageRole.USER, message_to_store)

            # Get conversation history
            messages = await self.get_messages(conversation.id)

            token_usage = {}
            response_content = await self._generate_with_nemo(
                messages=messages,
                system_prompt=conversation.system_prompt,
            )

            # Fallback to existing provider flow if NeMo is disabled/unavailable
            if response_content is None:
                # Convert to LangChain format
                lc_messages = self._convert_messages(messages, conversation.system_prompt)

                # Get LLM
                llm = self._get_llm(
                    provider=ModelProvider(conversation.model_provider),
                    model_name=conversation.model_name,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    streaming=False,
                )

                # Generate response
                response = await llm.ainvoke(lc_messages)
                response_content = response.content

                # Extract token usage
                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    token_usage = {
                        "prompt_tokens": response.usage_metadata.get("input_tokens", 0),
                        "completion_tokens": response.usage_metadata.get("output_tokens", 0),
                        "total_tokens": response.usage_metadata.get("total_tokens", 0),
                    }

            # Apply output guardrails before persisting/returning assistant text
            assistant_content = response_content or ""
            output_guard = await self._apply_output_guardrails(
                assistant_content,
                conversation=conversation,
            )
            if output_guard:
                if output_guard.blocked:
                    assistant_content = (
                        output_guard.message
                        or "The response was blocked by safety guardrails."
                    )
                elif output_guard.modified and output_guard.modified_content:
                    assistant_content = output_guard.modified_content

            # Log LLM generation to Langfuse
            latency_ms = int((time.time() - start_time) * 1000)
            if self._observability and trace:
                # Format messages for logging
                input_messages = [{"role": m.role, "content": m.content[:500]} for m in messages[-5:]]
                self._observability.record_llm_request(
                    trace=trace,
                    model=conversation.model_name,
                    provider=conversation.model_provider,
                    operation="chat",
                    input_messages=input_messages,
                    output=assistant_content[:1000],
                    input_tokens=token_usage.get("prompt_tokens", 0),
                    output_tokens=token_usage.get("completion_tokens", 0),
                    latency_ms=latency_ms,
                    success=True,
                )

            # Add assistant message
            assistant_message = await self.add_message(
                conversation=conversation,
                role=MessageRole.ASSISTANT,
                content=assistant_content,
                model_name=conversation.model_name,
                token_usage=token_usage,
            )

            return assistant_message

        except Exception as e:
            error_msg = str(e)
            logger.error("Chat error", error=error_msg, conversation_id=str(conversation.id))
            raise
        finally:
            # End trace
            if self._observability and trace:
                self._observability.langfuse.end_trace(
                    trace,
                    status="success" if not error_msg else "error",
                    error=error_msg,
                )
                self._observability.langfuse.flush()
            self._current_trace = None

    async def _parse_and_execute_tool_calls(self, content: str) -> list[tuple[str, str]]:
        """Parse tool calls from model text output and execute them.

        Looks for patterns like:
        - TOOL_CALL: tool_name(arg1='value', arg2='value')
        - tool_name(arg1='value', arg2='value')
        Returns list of (tool_name, result) tuples.
        """
        import re
        import ast

        results = []

        # Pattern 1: Match explicit TOOL_CALL: prefix format (preferred)
        # Example: TOOL_CALL: devlake_create_project(name="my-project")
        # Also matches tools with no arguments: TOOL_CALL: devlake_health_check()
        explicit_pattern = r"TOOL_CALL:\s*(\w+)\(([^)]*)\)"

        # Pattern 2: Match tool calls like: devlake_create_connection(plugin='github', name='abc')
        # Also matches tools with no arguments: devlake_health_check()
        # This handles both single and double quotes
        implicit_pattern = r"(\w+)\(([^)]*)\)"

        # Try explicit pattern first
        tool_call_pattern = explicit_pattern
        matches = list(re.finditer(tool_call_pattern, content))

        # If no explicit matches, fall back to implicit pattern
        if not matches:
            tool_call_pattern = implicit_pattern
            matches = list(re.finditer(tool_call_pattern, content))

        logger.info(
            "Parsing tool calls from content",
            content_preview=content[:200] if content else "",
            explicit_matches=len(list(re.finditer(explicit_pattern, content))),
            implicit_matches=len(list(re.finditer(implicit_pattern, content))),
            pattern_used="explicit" if tool_call_pattern == explicit_pattern else "implicit",
        )

        for match in matches:
            tool_name = match.group(1)
            args_str = match.group(2)

            # Check if this is a known tool
            if tool_name not in self._mcp_tools:
                continue

            logger.info(
                "Parsing tool call from text",
                tool_name=tool_name,
                args_str=args_str[:100],
            )

            try:
                # Parse the arguments
                # Convert "plugin='github', name='abc'" to {"plugin": "github", "name": "abc"}
                arguments = {}

                # Handle empty arguments case (e.g., devlake_health_check())
                args_str_stripped = args_str.strip()
                if args_str_stripped:
                    # Split by comma, but be careful with commas inside strings
                    # Use a simple approach: convert to dict literal and parse
                    # e.g., "plugin='github', name='abc'" -> "{'plugin': 'github', 'name': 'abc'}"
                    dict_str = "{" + args_str + "}"
                    # Replace single-quoted strings with double-quoted for JSON compatibility
                    # But we'll use ast.literal_eval which handles both

                    try:
                        arguments = ast.literal_eval(dict_str)
                    except (ValueError, SyntaxError):
                        # Try a different parsing approach for keyword arguments
                        # First try string values: key='value' or key="value"
                        for arg in re.findall(r"(\w+)\s*=\s*['\"]([^'\"]*)['\"]", args_str):
                            key, value = arg
                            arguments[key] = value

                        # Also handle integer/numeric values: key=123
                        for arg in re.findall(r"(\w+)\s*=\s*(\d+(?:\.\d+)?)", args_str):
                            key, value = arg
                            # Don't overwrite if already parsed as string
                            if key not in arguments:
                                # Try to parse as int or float
                                try:
                                    if '.' in value:
                                        arguments[key] = float(value)
                                    else:
                                        arguments[key] = int(value)
                                except ValueError:
                                    arguments[key] = value

                        # Handle boolean values: key=True, key=False
                        for arg in re.findall(r"(\w+)\s*=\s*(True|False)", args_str):
                            key, value = arg
                            if key not in arguments:
                                arguments[key] = value == "True"

                # Execute tool even with empty arguments (for tools like health_check)
                logger.info(
                    "Executing parsed tool call",
                    tool_name=tool_name,
                    argument_keys=list(arguments.keys()),
                )

                # Execute the tool
                result = await self._execute_mcp_tool(tool_name, arguments)
                results.append((tool_name, result))

            except Exception as e:
                # Provide structured error for execution failure
                from app.services.mcp.errors import internal_error
                error_response = internal_error(
                    operation=f"execute_{tool_name}",
                    error_message=str(e),
                    details={"args_str": args_str[:100] if args_str else None},
                )
                results.append((tool_name, json.dumps(error_response.to_dict())))
                logger.error(
                    "Error parsing/executing tool call",
                    tool_name=tool_name,
                    error=str(e),
                )

        return results

    async def _chat_stream_google(
        self,
        conversation: Conversation,
        messages: list[Message],
        temperature: float,
        max_tokens: int,
        use_mcp_tools: bool,
        model_name: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream chat response using Google's native SDK.

        This method bypasses LangChain's ChatGoogleGenerativeAI due to
        compatibility issues with async streaming in langchain-google-genai.
        """
        import asyncio
        import google.generativeai as genai

        # Use provided model_name or fall back to conversation's model
        effective_model_name = model_name or conversation.model_name

        logger.info(
            "Starting Google native chat_stream",
            model_name=effective_model_name,
            use_mcp_tools=use_mcp_tools,
            tool_count=len(self._mcp_tools) if self._mcp_tools else 0,
        )

        # Build the system instruction with MCP tools if available
        if conversation.system_prompt:
            effective_prompt = conversation.system_prompt
        elif self._langfuse_system_prompt and not self._langfuse_system_prompt.is_fallback:
            effective_prompt = self._langfuse_system_prompt.compile()
        else:
            effective_prompt = NEXUSAI_SYSTEM_PROMPT
        if use_mcp_tools and self._mcp_tools:
            effective_prompt += self._get_mcp_tools_description()

        # Configure the genai library with API key
        genai.configure(api_key=settings.GOOGLE_API_KEY)

        # Convert messages to Google format (chat history)
        # Google expects: [{"role": "user", "parts": ["..."]}, {"role": "model", "parts": ["..."]}]
        google_history = []
        last_role = None

        for msg in messages[:-1]:  # Exclude the last message (will be sent separately)
            # Map roles to Google's expected format
            if msg.role == MessageRole.USER.value:
                role = "user"
            elif msg.role == MessageRole.ASSISTANT.value:
                role = "model"
            else:
                # Skip system messages - they go in system_instruction
                continue

            # Merge consecutive messages of the same role (required by Gemini)
            if role == last_role and google_history:
                # Append to the last message's parts
                google_history[-1]["parts"][0] += "\n\n" + msg.content
            else:
                google_history.append({
                    "role": role,
                    "parts": [msg.content]
                })
            last_role = role

        # Get the last user message to send
        last_message = messages[-1].content if messages else ""

        logger.debug(
            "Google native messages prepared",
            history_count=len(google_history),
            roles=[c["role"] for c in google_history],
        )

        # Create the model with system instruction
        model = genai.GenerativeModel(
            model_name=effective_model_name,
            system_instruction=effective_prompt,
            generation_config=genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            ),
        )

        # Start chat with history
        chat = model.start_chat(history=google_history)

        full_content = ""

        try:
            # Use streaming response - run in thread pool since genai is synchronous
            def _generate_stream():
                return chat.send_message(last_message, stream=True)

            response_stream = await asyncio.to_thread(_generate_stream)

            for chunk in response_stream:
                if chunk.text:
                    full_content += chunk.text
                    yield chunk.text
        except Exception as e:
            logger.error(
                "Google native streaming error",
                error=str(e),
                error_type=type(e).__name__,
                model_name=effective_model_name,
            )
            raise

        # Log the full LLM output for debugging tool parsing
        logger.info(
            "Google native streaming completed - checking for tool calls",
            full_content_length=len(full_content),
            full_content_preview=full_content[:500] if full_content else "",
            has_tool_call_prefix="TOOL_CALL:" in full_content,
            has_parentheses="(" in full_content and ")" in full_content,
        )

        # Check if the response contains tool calls and execute them
        # Google models output tool calls as text like: TOOL_CALL: tool_name(arg1='value', arg2='value')
        if use_mcp_tools and self._mcp_tools:
            tool_results = await self._parse_and_execute_tool_calls(full_content)
            logger.info(
                "Tool parsing completed",
                tool_results_count=len(tool_results),
                tool_names=[name for name, _ in tool_results] if tool_results else [],
            )
            if tool_results:
                # Yield tool execution results with intelligent error recovery
                for tool_name, result in tool_results:
                    async for chunk in self._format_tool_result_with_recovery(tool_name, result):
                        yield chunk
                        full_content += chunk

        # Note: add_message is NOT called here - it's called in the main chat_stream() method
        # to ensure single responsibility. The caller (chat_stream) is responsible for
        # persisting the message after all streaming is complete.

    async def chat_stream(
        self,
        conversation: Conversation,
        user_message: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        use_mcp_tools: bool = True,
    ) -> AsyncGenerator[str, None]:
        """Send a message and stream AI response with optional MCP tool support."""
        start_time = time.time()
        trace = None
        error_msg = None
        total_tokens = 0

        # Start Langfuse trace for streaming
        if self._observability:
            trace = self._observability.langfuse.create_trace(
                name="chat_stream",
                user_id=self.user_id,
                session_id=str(conversation.id),
                metadata={
                    "model": conversation.model_name,
                    "provider": conversation.model_provider,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "use_mcp_tools": use_mcp_tools,
                },
                tags=["chat_stream", conversation.model_provider],
            )
            self._current_trace = trace

        # Apply input guardrails before persisting/sending user text
        message_to_store = user_message
        input_guard = await self._apply_input_guardrails(
            user_message,
            conversation=conversation,
        )
        if input_guard:
            if input_guard.blocked:
                blocked_text = (
                    input_guard.message
                    or "Your message was blocked by safety guardrails."
                )
                await self.add_message(conversation, MessageRole.USER, user_message)
                await self.add_message(
                    conversation=conversation,
                    role=MessageRole.ASSISTANT,
                    content=blocked_text,
                    model_name=conversation.model_name,
                )
                yield blocked_text
                if self._observability and trace:
                    self._observability.langfuse.end_trace(trace, status="success")
                    self._observability.langfuse.flush()
                    self._current_trace = None
                return
            if input_guard.modified and input_guard.modified_content:
                message_to_store = input_guard.modified_content

        # Add user message
        await self.add_message(conversation, MessageRole.USER, message_to_store)

        # Get conversation history
        messages = await self.get_messages(conversation.id)

        # Determine the actual provider to use
        # Apply same override logic as _get_llm() - DEFAULT_AI_PROVIDER takes precedence
        provider = ModelProvider(conversation.model_provider)
        model_name = conversation.model_name

        # Check if DEFAULT_AI_PROVIDER overrides the conversation's provider
        default_provider_str = getattr(settings, "DEFAULT_AI_PROVIDER", "").lower()
        default_provider_map = {
            "google": ModelProvider.GOOGLE,
            "anthropic": ModelProvider.ANTHROPIC,
            "openai": ModelProvider.OPENAI,
            "ollama": ModelProvider.OLLAMA,
        }
        configured_default = default_provider_map.get(default_provider_str)

        if configured_default and configured_default != provider:
            logger.info(
                "Overriding conversation provider with DEFAULT_AI_PROVIDER",
                conversation_provider=provider.value,
                default_provider=default_provider_str,
            )
            provider = configured_default

        # Always use the model from settings for the current provider
        # This ensures we use the configured model, not stale database values
        if provider == ModelProvider.GOOGLE:
            model_name = settings.GOOGLE_DEFAULT_MODEL
        elif provider == ModelProvider.ANTHROPIC:
            model_name = settings.ANTHROPIC_DEFAULT_MODEL
        elif provider == ModelProvider.OPENAI:
            model_name = settings.OPENAI_DEFAULT_MODEL
        elif provider == ModelProvider.OLLAMA:
            model_name = settings.OLLAMA_DEFAULT_MODEL

        # Use native Google SDK for Google models due to LangChain compatibility issues
        stream_blocked = False
        emitted_chars = 0

        if provider == ModelProvider.GOOGLE:
            full_content = ""
            async for chunk in self._chat_stream_google(
                conversation, messages, temperature, max_tokens, use_mcp_tools, model_name
            ):
                full_content += chunk
                emit_text, emitted_chars, blocked = await self._stream_guardrail_gate(
                    raw_text=full_content,
                    emitted_chars=emitted_chars,
                    conversation=conversation,
                )
                if emit_text:
                    yield emit_text
                if blocked:
                    stream_blocked = True
                    break

            # Flush any holdback content when stream was not blocked.
            if not stream_blocked and emitted_chars < len(full_content):
                yield full_content[emitted_chars:]
                emitted_chars = len(full_content)

            guarded_full_content = full_content
            output_guard = await self._apply_output_guardrails(
                full_content,
                conversation=conversation,
            )
            if output_guard:
                if output_guard.blocked:
                    guarded_full_content = (
                        output_guard.message
                        or "The response was blocked by safety guardrails."
                    )
                elif output_guard.modified and output_guard.modified_content:
                    guarded_full_content = output_guard.modified_content

            # Add assistant message after streaming completes (single point of persistence)
            await self.add_message(
                conversation=conversation,
                role=MessageRole.ASSISTANT,
                content=guarded_full_content,
                model_name=model_name,
            )
            # Log generation to Langfuse
            if self._observability and trace:
                latency_ms = int((time.time() - start_time) * 1000)
                input_messages = [{"role": m.role, "content": m.content[:500]} for m in messages[-5:]]
                self._observability.record_llm_request(
                    trace=trace,
                    model=model_name,
                    provider=provider.value,
                    operation="chat_stream",
                    input_messages=input_messages,
                    output=guarded_full_content[:1000] if guarded_full_content else "",
                    latency_ms=latency_ms,
                    success=True,
                )
                self._observability.langfuse.end_trace(trace, status="success")
                self._observability.langfuse.flush()
                self._current_trace = None
            return

        # Disable tool binding for Google models due to SDK compatibility issue
        # (FunctionDeclaration type mismatch between LangChain and google-generativeai)
        # Google models will still see tool descriptions in the system prompt
        enable_tool_binding = use_mcp_tools and provider != ModelProvider.GOOGLE
        full_content = ""

        logger.info(
            "Starting chat_stream",
            provider=provider.value,
            model_name=conversation.model_name,
            use_mcp_tools=use_mcp_tools,
            enable_tool_binding=enable_tool_binding,
            tool_count=len(self._mcp_tools) if self._mcp_tools else 0,
        )

        # Convert to LangChain format
        # Always include tool descriptions in system prompt when use_mcp_tools is enabled
        # (even for Google models that can't use tool binding)
        lc_messages = self._convert_messages(
            messages, conversation.system_prompt, include_mcp_tools=use_mcp_tools
        )

        logger.debug(
            "Converted messages for LLM",
            provider=provider.value,
            original_count=len(messages),
            converted_count=len(lc_messages),
            message_types=[type(m).__name__ for m in lc_messages],
        )

        # Get LLM
        llm = self._get_llm(
            provider=provider,
            model_name=conversation.model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=True,
        )

        # Bind MCP tools if available and enabled (not for Google due to SDK compatibility)
        if enable_tool_binding and self._mcp_tools:
            lc_tools = self._create_langchain_tools()
            if lc_tools:
                llm = llm.bind_tools(lc_tools)
                logger.info(
                    "Bound MCP tools to LLM",
                    provider=provider.value,
                    tool_count=len(lc_tools),
                    tool_names=[t.name for t in lc_tools[:5]],  # Log first 5 tool names
                )

        # Stream response with tool calling loop
        tool_calls_made = 0
        max_tool_iterations = 5  # Prevent infinite tool loops

        while tool_calls_made < max_tool_iterations:
            tool_call_detected = False
            current_tool_calls = []

            # Log messages being sent for debugging
            logger.debug(
                "Sending messages to LLM",
                provider=provider.value,
                message_count=len(lc_messages),
                message_types=[type(m).__name__ for m in lc_messages],
            )

            try:
                async for chunk in llm.astream(lc_messages):
                    # Check for tool calls in the chunk
                    if hasattr(chunk, "tool_calls") and chunk.tool_calls:
                        tool_call_detected = True
                        current_tool_calls.extend(chunk.tool_calls)
                    elif chunk.content:
                        full_content += chunk.content
                        emit_text, emitted_chars, blocked = await self._stream_guardrail_gate(
                            raw_text=full_content,
                            emitted_chars=emitted_chars,
                            conversation=conversation,
                        )
                        if emit_text:
                            yield emit_text
                        if blocked:
                            stream_blocked = True
                            break
            except Exception as stream_error:
                logger.error(
                    "LLM streaming error",
                    provider=provider.value,
                    error=str(stream_error),
                    error_type=type(stream_error).__name__,
                    message_count=len(lc_messages),
                    message_types=[type(m).__name__ for m in lc_messages],
                )
                raise

            if stream_blocked:
                break

            # If tool calls were made, execute them and continue
            if tool_call_detected and current_tool_calls:
                tool_calls_made += 1
                logger.info(
                    "Processing MCP tool calls",
                    count=len(current_tool_calls),
                    iteration=tool_calls_made,
                    tool_names=[tc.get("name") for tc in current_tool_calls],
                )
                for tc in current_tool_calls:
                    logger.info(
                        "Tool call details",
                        tool_name=tc.get("name"),
                        tool_args=tc.get("args"),
                        tool_id=tc.get("id"),
                    )

                # Add AI message with tool calls to context
                from langchain_core.messages import AIMessage, ToolMessage

                ai_message = AIMessage(content="", tool_calls=current_tool_calls)
                lc_messages.append(ai_message)

                # Execute each tool and add results
                for tool_call in current_tool_calls:
                    tool_name = tool_call.get("name", "")
                    tool_args = tool_call.get("args", {})
                    tool_id = tool_call.get("id", "")

                    # Yield tool call indicator
                    yield f"\n[Calling tool: {tool_name}...]\n"

                    # Execute the tool
                    tool_result = await self._execute_mcp_tool(tool_name, tool_args)

                    # Add tool result to messages
                    lc_messages.append(
                        ToolMessage(content=tool_result, tool_call_id=tool_id)
                    )

                    # Yield tool result with intelligent error recovery
                    async for chunk in self._format_tool_result_with_recovery(
                        tool_name, tool_result, tool_args
                    ):
                        yield chunk

                # Continue to next iteration to process tool results
                continue

            # No tool calls, we're done
            break

        # Flush any holdback content when stream was not blocked.
        if not stream_blocked and emitted_chars < len(full_content):
            yield full_content[emitted_chars:]
            emitted_chars = len(full_content)

        # Add assistant message after streaming completes
        guarded_full_content = full_content
        output_guard = await self._apply_output_guardrails(
            full_content,
            conversation=conversation,
        )
        if output_guard:
            if output_guard.blocked:
                guarded_full_content = (
                    output_guard.message
                    or "The response was blocked by safety guardrails."
                )
            elif output_guard.modified and output_guard.modified_content:
                guarded_full_content = output_guard.modified_content

        await self.add_message(
            conversation=conversation,
            role=MessageRole.ASSISTANT,
            content=guarded_full_content,
            model_name=conversation.model_name,
        )

        # Log generation to Langfuse after streaming completes
        if self._observability and trace:
            latency_ms = int((time.time() - start_time) * 1000)
            input_messages = [{"role": m.role, "content": m.content[:500]} for m in messages[-5:]]
            self._observability.record_llm_request(
                trace=trace,
                model=conversation.model_name,
                provider=conversation.model_provider,
                operation="chat_stream",
                input_messages=input_messages,
                output=guarded_full_content[:1000] if guarded_full_content else "",
                latency_ms=latency_ms,
                success=True,
            )
            self._observability.langfuse.end_trace(trace, status="success")
            self._observability.langfuse.flush()
            self._current_trace = None

    async def _execute_mcp_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """Execute an MCP tool and return the result."""
        from app.services.mcp.errors import not_found_error

        start_time = time.time()
        span = None
        error_msg = None

        # Start Langfuse span for tool execution
        if self._observability and self._current_trace:
            span = self._observability.langfuse.start_span(
                trace=self._current_trace,
                name=f"tool:{tool_name}",
                input_data={"tool_name": tool_name, "arguments": arguments},
                metadata={"tool_type": "mcp"},
            )

        try:
            if tool_name not in self._mcp_tools:
                # Return structured error with available tools suggestion
                available_tools = list(self._mcp_tools.keys())[:10]
                error_response = not_found_error(
                    resource_type="tool",
                    resource_name=tool_name,
                    available_resources=available_tools,
                )
                result = json.dumps(error_response.to_dict())
                error_msg = f"Tool not found: {tool_name}"
                return result

            server_name, mcp_tool = self._mcp_tools[tool_name]
            actual_tool_name = mcp_tool.name if server_name == "builtin" else tool_name

            result = await self._execute_tool(server_name, actual_tool_name, arguments)
            return result

        except Exception as e:
            error_msg = str(e)
            raise
        finally:
            # End Langfuse span
            if self._observability and span:
                latency_ms = int((time.time() - start_time) * 1000)
                # Try to parse result for logging (truncate if too long)
                output_preview = result[:500] if 'result' in dir() and result else None
                self._observability.langfuse.end_span(
                    span,
                    output={"result_preview": output_preview, "latency_ms": latency_ms},
                    status="success" if not error_msg else "error",
                    error=error_msg,
                )

    async def update_conversation_title(
        self,
        conversation: Conversation,
        title: str,
    ) -> Conversation:
        """Update conversation title."""
        conversation.title = title
        await self.db.flush()
        return conversation

    async def delete_conversation(
        self,
        conversation: Conversation,
    ) -> bool:
        """Delete a conversation."""
        await self.db.delete(conversation)
        await self.db.flush()
        return True
