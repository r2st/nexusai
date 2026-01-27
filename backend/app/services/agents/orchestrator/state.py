"""State management for the agent orchestrator."""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Annotated, Union, TYPE_CHECKING
from uuid import uuid4

from pydantic import BaseModel, Field
from langgraph.graph import add_messages
if TYPE_CHECKING:
    from langchain_core.messages import BaseMessage
else:
    BaseMessage = Any  # type: ignore


class WorkflowStatus(str, Enum):
    """Status of the workflow execution."""

    PENDING = "pending"
    ROUTING = "routing"
    EXECUTING = "executing"
    WAITING_INPUT = "waiting_input"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentNode(str, Enum):
    """Available agent nodes in the workflow."""

    ROUTER = "router"
    SETUP = "setup"
    METRICS = "metrics"
    QUERY = "query"
    INSIGHTS = "insights"
    CODE_ANALYSIS = "code_analysis"
    SUPERVISOR = "supervisor"
    HUMAN = "human"
    END = "end"


@dataclass
class TaskResult:
    """Result from an agent task execution."""

    success: bool
    output: str
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    agent: AgentNode | None = None
    execution_time_ms: int = 0
    tool_calls: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "output": self.output,
            "data": self.data,
            "error": self.error,
            "agent": self.agent.value if self.agent else None,
            "execution_time_ms": self.execution_time_ms,
            "tool_calls": self.tool_calls,
        }


class Message(BaseModel):
    """A message in the conversation."""

    role: str  # user, assistant, system, tool
    content: str
    name: str | None = None
    tool_call_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class OrchestratorState(BaseModel):
    """
    State object for the agent orchestrator.

    This is passed through the LangGraph workflow and maintains
    all context needed for multi-agent collaboration.
    """

    # Workflow identification
    workflow_id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str | None = None
    user_id: str | None = None
    tenant_id: str | None = None

    # Current status
    status: WorkflowStatus = WorkflowStatus.PENDING
    current_node: AgentNode = AgentNode.ROUTER
    previous_node: AgentNode | None = None

    # Messages - uses LangGraph's message accumulator
    # Accept both dict and BaseMessage types for compatibility
    messages: Annotated[list[Union[dict[str, Any], BaseMessage]], add_messages] = Field(default_factory=list)

    # Current task
    current_input: str = ""
    current_intent: str | None = None
    intent_confidence: float = 0.0

    # Task results from agents
    task_results: list[dict[str, Any]] = Field(default_factory=list)
    final_response: str | None = None

    # Context for agents
    context: dict[str, Any] = Field(default_factory=dict)

    # DevLake specific context
    devlake_config: dict[str, Any] | None = None
    available_metrics: list[str] = Field(default_factory=list)

    # Human-in-the-loop
    requires_human_input: bool = False
    human_input_prompt: str | None = None
    human_input_options: list[str] = Field(default_factory=list)

    # Tool execution
    pending_tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    tool_results: list[dict[str, Any]] = Field(default_factory=list)

    # Execution tracking
    iteration_count: int = 0
    max_iterations: int = 10
    start_time: datetime = Field(default_factory=lambda: datetime.now(UTC))
    errors: list[str] = Field(default_factory=list)

    # Memory and retrieval
    retrieved_documents: list[dict[str, Any]] = Field(default_factory=list)
    memory_context: dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True

    def add_message(self, role: str, content: str, **kwargs) -> None:
        """Add a message to the conversation."""
        self.messages.append({
            "role": role,
            "content": content,
            **kwargs,
        })

    def add_task_result(self, result: TaskResult) -> None:
        """Add a task result."""
        self.task_results.append(result.to_dict())

    def add_error(self, error: str) -> None:
        """Add an error."""
        self.errors.append(error)

    def get_conversation_history(self) -> list[dict[str, Any]]:
        """Get the conversation history in a standard format."""
        return self.messages

    def should_continue(self) -> bool:
        """Check if the workflow should continue."""
        if self.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED]:
            return False
        if self.iteration_count >= self.max_iterations:
            return False
        return True

    def to_langchain_messages(self) -> list:
        """Convert messages to LangChain format."""
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

        lc_messages = []
        for msg in self.messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "user" or role == "human":
                lc_messages.append(HumanMessage(content=content))
            elif role == "assistant" or role == "ai":
                lc_messages.append(AIMessage(content=content))
            elif role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "tool":
                lc_messages.append(ToolMessage(
                    content=content,
                    tool_call_id=msg.get("tool_call_id", ""),
                ))

        return lc_messages


def create_initial_state(
    user_input: str,
    user_id: str | None = None,
    tenant_id: str | None = None,
    session_id: str | None = None,
    context: dict[str, Any] | None = None,
) -> OrchestratorState:
    """Create initial state for a new workflow."""
    state = OrchestratorState(
        user_id=user_id,
        tenant_id=tenant_id,
        session_id=session_id,
        current_input=user_input,
        context=context or {},
    )

    # Add the initial user message
    state.add_message("user", user_input)

    return state
