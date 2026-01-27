"""Agent service for managing and executing agents."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.agents.models import (
    Agent,
    AgentCapability,
    AgentCreate,
    AgentExecution,
    AgentStatus,
    AgentTool,
    AgentUpdate,
    ExecutionStatus,
)
from app.services.agents.tools import tool_registry, ToolResult
from app.services.agents.mcp import MCPClient, MCPServerConfig, mcp_manager

logger = structlog.get_logger()


class AgentService:
    """Service for managing agents."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_agent(
        self,
        user_id: str,
        data: AgentCreate,
        organization_id: str | None = None,
    ) -> Agent:
        """Create a new agent."""
        agent = Agent(
            creator_id=user_id,
            organization_id=organization_id,
            name=data.name,
            description=data.description,
            system_prompt=data.system_prompt,
            model_provider=data.model_provider,
            model_name=data.model_name,
            capabilities=[c.value for c in data.capabilities],
            tools_config=data.tools_config,
            mcp_servers=data.mcp_servers,
            is_public=data.is_public,
            tags=data.tags,
            status=AgentStatus.DRAFT.value,
        )

        self.db.add(agent)
        await self.db.flush()

        logger.info("Agent created", agent_id=agent.id, name=agent.name)
        return agent

    async def get_agent(self, agent_id: str) -> Agent | None:
        """Get an agent by ID."""
        result = await self.db.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        return result.scalar_one_or_none()

    async def list_agents(
        self,
        user_id: str | None = None,
        organization_id: str | None = None,
        include_public: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Agent]:
        """List agents with optional filters."""
        query = select(Agent)

        conditions = []

        if user_id:
            conditions.append(Agent.creator_id == user_id)

        if organization_id:
            conditions.append(Agent.organization_id == organization_id)

        if include_public:
            # Include user's agents OR public agents
            if conditions:
                from sqlalchemy import or_
                query = query.where(or_(*conditions, Agent.is_public == True))
            else:
                query = query.where(Agent.is_public == True)
        elif conditions:
            from sqlalchemy import and_
            query = query.where(and_(*conditions))

        query = query.order_by(Agent.updated_at.desc()).offset(offset).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_agent(
        self,
        agent_id: str,
        user_id: str,
        data: AgentUpdate,
    ) -> Agent | None:
        """Update an agent."""
        agent = await self.get_agent(agent_id)

        if not agent or agent.creator_id != user_id:
            return None

        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if field == "capabilities" and value is not None:
                value = [c.value for c in value]
            if field == "status" and value is not None:
                value = value.value
            setattr(agent, field, value)

        agent.updated_at = datetime.now(UTC)
        await self.db.flush()

        logger.info("Agent updated", agent_id=agent_id)
        return agent

    async def delete_agent(self, agent_id: str, user_id: str) -> bool:
        """Delete an agent."""
        agent = await self.get_agent(agent_id)

        if not agent or agent.creator_id != user_id:
            return False

        await self.db.delete(agent)
        await self.db.flush()

        logger.info("Agent deleted", agent_id=agent_id)
        return True

    async def add_tool(
        self,
        agent_id: str,
        name: str,
        description: str,
        tool_type: str,
        schema_definition: dict[str, Any],
        config: dict[str, Any] | None = None,
    ) -> AgentTool:
        """Add a tool to an agent."""
        tool = AgentTool(
            agent_id=agent_id,
            name=name,
            description=description,
            tool_type=tool_type,
            schema_definition=schema_definition,
            config=config or {},
        )

        self.db.add(tool)
        await self.db.flush()

        logger.info("Tool added to agent", agent_id=agent_id, tool=name)
        return tool

    async def execute_agent(
        self,
        agent_id: str,
        user_id: str,
        input_message: str,
        conversation_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> AgentExecution | None:
        """Execute an agent with a message."""
        agent = await self.get_agent(agent_id)

        if not agent:
            logger.error("Agent not found", agent_id=agent_id)
            return None

        # Create execution record
        execution = AgentExecution(
            agent_id=agent_id,
            user_id=user_id,
            conversation_id=conversation_id,
            input_message=input_message,
            status=ExecutionStatus.RUNNING.value,
            start_time=datetime.now(UTC),
        )

        self.db.add(execution)
        await self.db.flush()

        try:
            # Build messages
            from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

            messages = []

            if agent.system_prompt:
                messages.append(SystemMessage(content=agent.system_prompt))

            messages.append(HumanMessage(content=input_message))

            # Get LLM
            llm = self._get_llm(agent)

            # Check if we need to use tools
            tools = await self._get_agent_tools(agent, user_id)

            if tools:
                # Use function calling
                response = await self._execute_with_tools(
                    llm, messages, tools, agent, execution, user_id
                )
            else:
                # Simple invocation
                response = await llm.ainvoke(messages)

            # Extract response content
            output_message = response.content if hasattr(response, "content") else str(response)

            # Update execution
            execution.status = ExecutionStatus.COMPLETED.value
            execution.output_message = output_message
            execution.end_time = datetime.now(UTC)
            execution.execution_time_ms = int(
                (execution.end_time - execution.start_time).total_seconds() * 1000
            )

            # Update token usage
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                execution.total_tokens = response.usage_metadata.get("total_tokens", 0)

            # Increment usage count
            agent.usage_count += 1

            await self.db.flush()

            logger.info(
                "Agent execution completed",
                execution_id=execution.id,
                agent_id=agent_id,
                execution_time_ms=execution.execution_time_ms,
            )

            return execution

        except Exception as e:
            logger.error("Agent execution failed", error=str(e), agent_id=agent_id)

            execution.status = ExecutionStatus.FAILED.value
            execution.error = str(e)
            execution.end_time = datetime.now(UTC)
            execution.execution_time_ms = int(
                (execution.end_time - execution.start_time).total_seconds() * 1000
            )

            await self.db.flush()
            return execution

    def _get_llm(self, agent: Agent) -> Any:
        """Get LLM instance for the agent."""
        model_config = agent.model_config or {}
        temperature = model_config.get("temperature", 0.7)
        max_tokens = model_config.get("max_tokens", 4096)

        if agent.model_provider == "anthropic":
            from langchain_anthropic import ChatAnthropic

            return ChatAnthropic(
                model=agent.model_name,
                api_key=settings.ANTHROPIC_API_KEY,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        else:
            # Default to OpenAI
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=agent.model_name,
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_API_BASE,
                temperature=temperature,
                max_tokens=max_tokens,
            )

    async def _get_agent_tools(
        self,
        agent: Agent,
        user_id: str,
    ) -> list[dict[str, Any]]:
        """Get tools available to the agent."""
        tools = []

        # Get built-in tools based on capabilities
        if AgentCapability.FUNCTION_CALLING.value in agent.capabilities:
            # Add registered tools
            for tool_def in tool_registry.list_tools():
                tools.append(tool_def.to_openai_schema())

        # Get custom tools from agent
        agent_tools = await self.db.execute(
            select(AgentTool)
            .where(AgentTool.agent_id == agent.id, AgentTool.is_enabled == True)
        )

        for tool in agent_tools.scalars().all():
            if tool.tool_type == "function":
                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.schema_definition,
                    },
                })

        # Get MCP tools
        if AgentCapability.MCP_SERVER.value in agent.capabilities:
            for mcp_config in agent.mcp_servers:
                server_name = mcp_config.get("name")
                client = mcp_manager.get_client(user_id, server_name)

                if client and client.is_connected:
                    for mcp_tool in client.list_tools():
                        tools.append({
                            "type": "function",
                            "function": {
                                "name": f"mcp_{server_name}_{mcp_tool.name}",
                                "description": mcp_tool.description,
                                "parameters": mcp_tool.input_schema,
                            },
                        })

        return tools

    async def _execute_with_tools(
        self,
        llm: ChatOpenAI | ChatAnthropic,
        messages: list,
        tools: list[dict[str, Any]],
        agent: Agent,
        execution: AgentExecution,
        user_id: str,
    ):
        """Execute agent with tool calling."""
        # Bind tools to LLM
        llm_with_tools = llm.bind_tools(tools)

        # Initial invocation
        response = await llm_with_tools.ainvoke(messages)

        # Check for tool calls
        tool_calls_made = []

        while hasattr(response, "tool_calls") and response.tool_calls:
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                logger.info("Executing tool", tool=tool_name, args=tool_args)

                # Execute the tool
                tool_result = await self._execute_tool(
                    tool_name, tool_args, agent, user_id
                )

                tool_calls_made.append({
                    "name": tool_name,
                    "arguments": tool_args,
                    "result": tool_result.output if tool_result.success else tool_result.error,
                    "success": tool_result.success,
                })

                # Add tool result to messages
                messages.append(response)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.get("id", str(uuid4())),
                    "content": str(tool_result.output) if tool_result.success else f"Error: {tool_result.error}",
                })

            # Get next response
            response = await llm_with_tools.ainvoke(messages)

        # Record tool calls in execution
        execution.tool_calls = tool_calls_made

        return response

    async def _execute_tool(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        agent: Agent,
        user_id: str,
    ) -> ToolResult:
        """Execute a specific tool."""
        # Check for MCP tool
        if tool_name.startswith("mcp_"):
            parts = tool_name.split("_", 2)
            if len(parts) >= 3:
                server_name = parts[1]
                actual_tool_name = parts[2]

                result = await mcp_manager.call_tool(
                    user_id, server_name, actual_tool_name, tool_args
                )

                if result:
                    return ToolResult(success=True, output=result)
                else:
                    return ToolResult(success=False, output=None, error="MCP tool call failed")

        # Check for code execution
        if tool_name == "execute_code" and AgentCapability.CODE_EXECUTION.value in agent.capabilities:
            from app.services.code_interpreter import CodeExecutor, ExecutionRequest, SupportedLanguage

            executor = CodeExecutor()
            request = ExecutionRequest(
                language=SupportedLanguage(tool_args.get("language", "python")),
                code=tool_args.get("code", ""),
            )

            exec_result = await executor.execute(request)
            return ToolResult(
                success=exec_result.status.value == "completed",
                output={
                    "stdout": exec_result.stdout,
                    "stderr": exec_result.stderr,
                    "exit_code": exec_result.exit_code,
                },
                error=exec_result.error,
            )

        # Use tool registry
        return await tool_registry.execute(tool_name, **tool_args)

    async def list_marketplace_agents(
        self,
        category: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Agent]:
        """List agents in the marketplace."""
        query = select(Agent).where(
            Agent.is_marketplace_listed == True,
            Agent.status == AgentStatus.ACTIVE.value,
        )

        if category:
            query = query.where(Agent.marketplace_category == category)

        query = query.order_by(Agent.usage_count.desc()).offset(offset).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def rate_agent(
        self,
        agent_id: str,
        user_id: str,
        rating: float,
    ) -> Agent | None:
        """Rate an agent."""
        agent = await self.get_agent(agent_id)

        if not agent:
            return None

        # Update rating (simple average for now)
        current_total = (agent.rating or 0) * agent.rating_count
        agent.rating_count += 1
        agent.rating = (current_total + rating) / agent.rating_count

        await self.db.flush()

        logger.info("Agent rated", agent_id=agent_id, rating=rating)
        return agent

    async def publish_to_marketplace(
        self,
        agent_id: str,
        user_id: str,
        category: str,
    ) -> Agent | None:
        """Publish an agent to the marketplace."""
        agent = await self.get_agent(agent_id)

        if not agent or agent.creator_id != user_id:
            return None

        agent.is_marketplace_listed = True
        agent.marketplace_category = category
        agent.status = AgentStatus.ACTIVE.value

        await self.db.flush()

        logger.info("Agent published to marketplace", agent_id=agent_id, category=category)
        return agent


# Global service instance factory
def get_agent_service(db: AsyncSession) -> AgentService:
    """Get agent service instance."""
    return AgentService(db)
