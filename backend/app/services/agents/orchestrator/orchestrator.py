"""Main agent orchestrator using LangGraph."""

from typing import Any, Literal

import structlog
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.services.agents.orchestrator.state import (
    AgentNode,
    OrchestratorState,
    WorkflowStatus,
    create_initial_state,
)
from app.services.agents.orchestrator.router import IntentRouter, IntentClassification
from app.services.agents.orchestrator.nodes import (
    get_agent_node,
    SupervisorNode,
    SetupAgentNode,
    MetricsAgentNode,
    QueryAgentNode,
    InsightsAgentNode,
    CodeAnalysisNode,
    HumanInputNode,
)

logger = structlog.get_logger()


class AgentOrchestrator:
    """
    Multi-agent orchestrator using LangGraph.

    Coordinates multiple specialized agents to handle user requests,
    maintaining state across the workflow and supporting human-in-the-loop.
    """

    def __init__(self, llm_gateway=None, checkpointer=None):
        """
        Initialize the orchestrator.

        Args:
            llm_gateway: LLM gateway service for model calls
            checkpointer: LangGraph checkpointer for persistence
        """
        self.llm_gateway = llm_gateway
        self.intent_router = IntentRouter(use_llm=llm_gateway is not None)
        self.checkpointer = checkpointer or MemorySaver()

        # Initialize agent nodes
        self.nodes = {
            AgentNode.SUPERVISOR: SupervisorNode(llm_gateway=llm_gateway),
            AgentNode.SETUP: SetupAgentNode(llm_gateway=llm_gateway),
            AgentNode.METRICS: MetricsAgentNode(llm_gateway=llm_gateway),
            AgentNode.QUERY: QueryAgentNode(llm_gateway=llm_gateway),
            AgentNode.INSIGHTS: InsightsAgentNode(llm_gateway=llm_gateway),
            AgentNode.CODE_ANALYSIS: CodeAnalysisNode(llm_gateway=llm_gateway),
            AgentNode.HUMAN: HumanInputNode(llm_gateway=llm_gateway),
        }

        # Build the workflow graph
        self.graph = self._build_graph()
        self.compiled_graph = self.graph.compile(checkpointer=self.checkpointer)

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        # Create the state graph
        workflow = StateGraph(OrchestratorState)

        # Add nodes
        workflow.add_node("router", self._route_node)
        workflow.add_node("supervisor", self._supervisor_node)
        workflow.add_node("setup", self._setup_node)
        workflow.add_node("metrics", self._metrics_node)
        workflow.add_node("query", self._query_node)
        workflow.add_node("insights", self._insights_node)
        workflow.add_node("code_analysis", self._code_analysis_node)
        workflow.add_node("human", self._human_node)

        # Set entry point
        workflow.set_entry_point("router")

        # Add conditional edges from router
        workflow.add_conditional_edges(
            "router",
            self._decide_next_node,
            {
                "supervisor": "supervisor",
                "setup": "setup",
                "metrics": "metrics",
                "query": "query",
                "insights": "insights",
                "code_analysis": "code_analysis",
                "human": "human",
                "end": END,
            },
        )

        # Add edges from agent nodes back to router or end
        for node_name in ["supervisor", "setup", "metrics", "query", "insights", "code_analysis"]:
            workflow.add_conditional_edges(
                node_name,
                self._should_continue,
                {
                    "continue": "router",
                    "human": "human",
                    "end": END,
                },
            )

        # Human node can continue or end
        workflow.add_conditional_edges(
            "human",
            self._after_human_input,
            {
                "continue": "router",
                "end": END,
            },
        )

        return workflow

    async def _route_node(self, state: OrchestratorState) -> OrchestratorState:
        """Router node that classifies intent and determines next agent."""
        logger.debug("Routing request", input=state.current_input[:100])

        state.status = WorkflowStatus.ROUTING
        state.previous_node = state.current_node
        state.current_node = AgentNode.ROUTER

        # Classify intent
        classification = self.intent_router.classify(
            state.current_input,
            context=state.context,
        )

        state.current_intent = classification.intent.value
        state.intent_confidence = classification.confidence
        state.context["extracted_entities"] = classification.extracted_entities

        logger.info(
            "Intent classified",
            intent=classification.intent.value,
            confidence=classification.confidence,
            target_agent=classification.target_agent.value,
        )

        return state

    async def _supervisor_node(self, state: OrchestratorState) -> OrchestratorState:
        """Execute supervisor agent."""
        return await self.nodes[AgentNode.SUPERVISOR].execute(state)

    async def _setup_node(self, state: OrchestratorState) -> OrchestratorState:
        """Execute setup agent."""
        return await self.nodes[AgentNode.SETUP].execute(state)

    async def _metrics_node(self, state: OrchestratorState) -> OrchestratorState:
        """Execute metrics agent."""
        return await self.nodes[AgentNode.METRICS].execute(state)

    async def _query_node(self, state: OrchestratorState) -> OrchestratorState:
        """Execute query agent."""
        return await self.nodes[AgentNode.QUERY].execute(state)

    async def _insights_node(self, state: OrchestratorState) -> OrchestratorState:
        """Execute insights agent."""
        return await self.nodes[AgentNode.INSIGHTS].execute(state)

    async def _code_analysis_node(self, state: OrchestratorState) -> OrchestratorState:
        """Execute code analysis agent."""
        return await self.nodes[AgentNode.CODE_ANALYSIS].execute(state)

    async def _human_node(self, state: OrchestratorState) -> OrchestratorState:
        """Execute human input node."""
        return await self.nodes[AgentNode.HUMAN].execute(state)

    def _decide_next_node(
        self, state: OrchestratorState
    ) -> Literal["supervisor", "setup", "metrics", "query", "insights", "code_analysis", "human", "end"]:
        """Decide which node to route to based on classified intent."""
        # Check if we should end
        if not state.should_continue():
            return "end"

        # Check if human input is required
        if state.requires_human_input:
            return "human"

        # Route based on classified intent
        target = self.intent_router.route(state)

        node_mapping = {
            AgentNode.SUPERVISOR: "supervisor",
            AgentNode.SETUP: "setup",
            AgentNode.METRICS: "metrics",
            AgentNode.QUERY: "query",
            AgentNode.INSIGHTS: "insights",
            AgentNode.CODE_ANALYSIS: "code_analysis",
            AgentNode.HUMAN: "human",
        }

        return node_mapping.get(target, "supervisor")

    def _should_continue(
        self, state: OrchestratorState
    ) -> Literal["continue", "human", "end"]:
        """Determine if workflow should continue after an agent execution."""
        # If completed or failed, end
        if state.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED]:
            return "end"

        # If waiting for human input, go to human node
        if state.requires_human_input or state.status == WorkflowStatus.WAITING_INPUT:
            return "human"

        # If we've exceeded max iterations, end
        if state.iteration_count >= state.max_iterations:
            logger.warning("Max iterations reached", iterations=state.iteration_count)
            return "end"

        # If there's a final response and no pending work, end
        if state.final_response and not state.pending_tool_calls:
            return "end"

        # Continue the workflow
        return "continue"

    def _after_human_input(
        self, state: OrchestratorState
    ) -> Literal["continue", "end"]:
        """Determine next step after human input."""
        # If human input was provided, continue processing
        if not state.requires_human_input:
            return "continue"

        # Still waiting for input - end (will resume when input provided)
        return "end"

    async def run(
        self,
        user_input: str,
        user_id: str | None = None,
        tenant_id: str | None = None,
        session_id: str | None = None,
        context: dict[str, Any] | None = None,
        thread_id: str | None = None,
    ) -> OrchestratorState:
        """
        Run the orchestrator with user input.

        Args:
            user_input: The user's message
            user_id: Optional user identifier
            tenant_id: Optional tenant identifier
            session_id: Optional session identifier
            context: Optional additional context
            thread_id: Optional thread ID for conversation continuity

        Returns:
            Final orchestrator state
        """
        # Create initial state
        state = create_initial_state(
            user_input=user_input,
            user_id=user_id,
            tenant_id=tenant_id,
            session_id=session_id,
            context=context,
        )

        # Configure thread for checkpointing
        config = {"configurable": {"thread_id": thread_id or state.workflow_id}}

        logger.info(
            "Starting orchestrator",
            workflow_id=state.workflow_id,
            user_id=user_id,
            input_length=len(user_input),
        )

        try:
            # Run the graph
            result = await self.compiled_graph.ainvoke(state, config=config)

            # Convert result back to OrchestratorState if it's a dict
            if isinstance(result, dict):
                final_state = OrchestratorState(**result)
            else:
                final_state = result

            logger.info(
                "Orchestrator completed",
                workflow_id=final_state.workflow_id,
                status=final_state.status.value,
                iterations=final_state.iteration_count,
            )

            return final_state

        except Exception as e:
            logger.error(
                "Orchestrator failed",
                workflow_id=state.workflow_id,
                error=str(e),
            )

            state.status = WorkflowStatus.FAILED
            state.add_error(str(e))
            state.final_response = "I encountered an error processing your request. Please try again or contact support if the issue persists."

            return state

    async def resume(
        self,
        thread_id: str,
        human_input: str | None = None,
    ) -> OrchestratorState:
        """
        Resume a workflow that was waiting for human input.

        Args:
            thread_id: The thread ID to resume
            human_input: The human's response

        Returns:
            Updated orchestrator state
        """
        config = {"configurable": {"thread_id": thread_id}}

        # Get current state from checkpoint
        state_snapshot = await self.compiled_graph.aget_state(config)

        if not state_snapshot.values:
            raise ValueError(f"No workflow found for thread {thread_id}")

        state = OrchestratorState(**state_snapshot.values)

        # Add human input
        if human_input:
            state.add_message("user", human_input)
            state.current_input = human_input
            state.requires_human_input = False
            state.status = WorkflowStatus.EXECUTING

        logger.info(
            "Resuming orchestrator",
            thread_id=thread_id,
            workflow_id=state.workflow_id,
        )

        # Continue the graph
        result = await self.compiled_graph.ainvoke(state, config=config)

        # Convert result back to OrchestratorState if it's a dict
        if isinstance(result, dict):
            final_state = OrchestratorState(**result)
        else:
            final_state = result

        return final_state

    async def get_state(self, thread_id: str) -> OrchestratorState | None:
        """
        Get the current state of a workflow.

        Args:
            thread_id: The thread ID

        Returns:
            Current orchestrator state or None if not found
        """
        config = {"configurable": {"thread_id": thread_id}}

        try:
            state_snapshot = await self.compiled_graph.aget_state(config)

            if state_snapshot.values:
                return OrchestratorState(**state_snapshot.values)

            return None

        except Exception as e:
            logger.error("Failed to get state", thread_id=thread_id, error=str(e))
            return None

    def get_available_agents(self) -> list[dict[str, Any]]:
        """Get information about available agents."""
        return [
            {
                "type": node_type.value,
                "name": node.name,
                "description": node.description,
            }
            for node_type, node in self.nodes.items()
        ]


# Global orchestrator instance
_orchestrator: AgentOrchestrator | None = None


def get_orchestrator(llm_gateway=None) -> AgentOrchestrator:
    """Get or create the global orchestrator instance."""
    global _orchestrator

    if _orchestrator is None:
        _orchestrator = AgentOrchestrator(llm_gateway=llm_gateway)

    return _orchestrator


async def create_orchestrator(llm_gateway=None, checkpointer=None) -> AgentOrchestrator:
    """Create a new orchestrator instance with custom configuration."""
    return AgentOrchestrator(
        llm_gateway=llm_gateway,
        checkpointer=checkpointer,
    )
