"""Agent handoff and chain-of-agents (Mixture-of-Agents) support."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

import structlog
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()


class HandoffType(str, Enum):
    """Types of agent handoffs."""

    SEQUENTIAL = "sequential"  # One agent hands off to another
    PARALLEL = "parallel"  # Multiple agents work simultaneously
    CONDITIONAL = "conditional"  # Handoff based on conditions
    FALLBACK = "fallback"  # Fallback to another agent on failure


class HandoffStatus(str, Enum):
    """Handoff execution status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class HandoffContext:
    """Context passed between agents during handoff."""

    original_input: str
    intermediate_results: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    conversation_history: list[dict[str, str]] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)

    def add_result(self, agent_id: str, result: str, metadata: dict[str, Any] | None = None) -> None:
        """Add an intermediate result from an agent."""
        self.intermediate_results.append({
            "agent_id": agent_id,
            "result": result,
            "metadata": metadata or {},
            "timestamp": datetime.now(UTC).isoformat(),
        })

    def get_last_result(self) -> str | None:
        """Get the last intermediate result."""
        if self.intermediate_results:
            return self.intermediate_results[-1]["result"]
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "original_input": self.original_input,
            "intermediate_results": self.intermediate_results,
            "metadata": self.metadata,
            "conversation_history": self.conversation_history,
            "files": self.files,
            "tools_used": self.tools_used,
        }


class AgentHandoff(BaseModel):
    """Definition of an agent handoff."""

    id: str = ""
    from_agent_id: str
    to_agent_id: str
    handoff_type: HandoffType = HandoffType.SEQUENTIAL
    condition: str | None = None  # For conditional handoffs
    priority: int = 0  # For parallel execution ordering
    transform_prompt: str | None = None  # Prompt to transform input for next agent
    enabled: bool = True

    def __init__(self, **data):
        super().__init__(**data)
        if not self.id:
            self.id = str(uuid4())


@dataclass
class HandoffResult:
    """Result of a handoff execution."""

    handoff_id: str
    status: HandoffStatus
    from_agent_id: str
    to_agent_id: str
    input_message: str
    output_message: str | None = None
    error: str | None = None
    execution_time_ms: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class HandoffChain:
    """Chain of agents for Mixture-of-Agents pattern."""

    def __init__(
        self,
        chain_id: str | None = None,
        name: str = "Agent Chain",
        description: str | None = None,
    ):
        self.chain_id = chain_id or str(uuid4())
        self.name = name
        self.description = description
        self._handoffs: list[AgentHandoff] = []
        self._agent_configs: dict[str, dict[str, Any]] = {}

    def add_handoff(self, handoff: AgentHandoff) -> None:
        """Add a handoff to the chain."""
        self._handoffs.append(handoff)

    def add_agent(
        self,
        agent_id: str,
        config: dict[str, Any] | None = None,
    ) -> None:
        """Add an agent configuration to the chain."""
        self._agent_configs[agent_id] = config or {}

    def add_sequential(
        self,
        from_agent_id: str,
        to_agent_id: str,
        transform_prompt: str | None = None,
    ) -> AgentHandoff:
        """Add a sequential handoff."""
        handoff = AgentHandoff(
            from_agent_id=from_agent_id,
            to_agent_id=to_agent_id,
            handoff_type=HandoffType.SEQUENTIAL,
            transform_prompt=transform_prompt,
        )
        self.add_handoff(handoff)
        return handoff

    def add_conditional(
        self,
        from_agent_id: str,
        to_agent_id: str,
        condition: str,
    ) -> AgentHandoff:
        """Add a conditional handoff."""
        handoff = AgentHandoff(
            from_agent_id=from_agent_id,
            to_agent_id=to_agent_id,
            handoff_type=HandoffType.CONDITIONAL,
            condition=condition,
        )
        self.add_handoff(handoff)
        return handoff

    def add_fallback(
        self,
        from_agent_id: str,
        fallback_agent_id: str,
    ) -> AgentHandoff:
        """Add a fallback handoff."""
        handoff = AgentHandoff(
            from_agent_id=from_agent_id,
            to_agent_id=fallback_agent_id,
            handoff_type=HandoffType.FALLBACK,
        )
        self.add_handoff(handoff)
        return handoff

    def get_next_agents(
        self,
        current_agent_id: str,
        context: HandoffContext,
    ) -> list[str]:
        """Get the next agents in the chain."""
        next_agents = []

        for handoff in self._handoffs:
            if handoff.from_agent_id != current_agent_id:
                continue

            if not handoff.enabled:
                continue

            # Check handoff type
            if handoff.handoff_type == HandoffType.SEQUENTIAL:
                next_agents.append(handoff.to_agent_id)

            elif handoff.handoff_type == HandoffType.CONDITIONAL:
                # Evaluate condition (simple keyword matching for now)
                if handoff.condition and self._evaluate_condition(
                    handoff.condition, context
                ):
                    next_agents.append(handoff.to_agent_id)

            elif handoff.handoff_type == HandoffType.PARALLEL:
                next_agents.append(handoff.to_agent_id)

        return next_agents

    def _evaluate_condition(
        self,
        condition: str,
        context: HandoffContext,
    ) -> bool:
        """Evaluate a handoff condition."""
        # Simple keyword-based evaluation
        # Could be extended to use LLM for complex conditions
        last_result = context.get_last_result()
        if not last_result:
            return False

        # Check if condition keywords are in the result
        condition_lower = condition.lower()
        result_lower = last_result.lower()

        # Simple contains check
        if "contains:" in condition_lower:
            keyword = condition_lower.split("contains:")[1].strip()
            return keyword in result_lower

        # Check for specific patterns
        if "error" in condition_lower:
            return "error" in result_lower or "failed" in result_lower

        if "success" in condition_lower:
            return "success" in result_lower or "completed" in result_lower

        return True

    def get_entry_agents(self) -> list[str]:
        """Get agents that can start the chain (not receiving any handoff)."""
        receiving_agents = {h.to_agent_id for h in self._handoffs}
        all_agents = {h.from_agent_id for h in self._handoffs} | receiving_agents

        # Entry agents are those not receiving any handoff
        entry_agents = all_agents - receiving_agents

        # If all agents receive handoffs, use the first one
        if not entry_agents and self._handoffs:
            return [self._handoffs[0].from_agent_id]

        return list(entry_agents)

    def get_exit_agents(self) -> list[str]:
        """Get agents that end the chain (not handing off to anyone)."""
        sending_agents = {h.from_agent_id for h in self._handoffs}
        all_agents = sending_agents | {h.to_agent_id for h in self._handoffs}

        return list(all_agents - sending_agents)

    def to_dict(self) -> dict[str, Any]:
        """Convert chain to dictionary."""
        return {
            "chain_id": self.chain_id,
            "name": self.name,
            "description": self.description,
            "handoffs": [h.model_dump() for h in self._handoffs],
            "agent_configs": self._agent_configs,
            "entry_agents": self.get_entry_agents(),
            "exit_agents": self.get_exit_agents(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HandoffChain":
        """Create chain from dictionary."""
        chain = cls(
            chain_id=data.get("chain_id"),
            name=data.get("name", "Agent Chain"),
            description=data.get("description"),
        )

        for handoff_data in data.get("handoffs", []):
            chain.add_handoff(AgentHandoff(**handoff_data))

        for agent_id, config in data.get("agent_configs", {}).items():
            chain.add_agent(agent_id, config)

        return chain


class ChainExecutor:
    """Executor for agent chains."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute_chain(
        self,
        chain: HandoffChain,
        initial_input: str,
        user_id: str,
        max_steps: int = 10,
    ) -> list[HandoffResult]:
        """Execute an agent chain."""
        results: list[HandoffResult] = []
        context = HandoffContext(original_input=initial_input)

        # Get entry agents
        current_agents = chain.get_entry_agents()
        if not current_agents:
            logger.error("No entry agents found in chain")
            return results

        step = 0
        while current_agents and step < max_steps:
            step += 1

            for agent_id in current_agents:
                start_time = datetime.now(UTC)

                try:
                    # Import here to avoid circular imports
                    from app.services.agents.service import AgentService

                    service = AgentService(self.db)

                    # Get current input (original or last result)
                    current_input = context.get_last_result() or context.original_input

                    # Execute the agent
                    execution = await service.execute_agent(
                        agent_id=agent_id,
                        user_id=user_id,
                        input_message=current_input,
                    )

                    # Record result
                    execution_time = int((datetime.now(UTC) - start_time).total_seconds() * 1000)

                    if execution and execution.output_message:
                        context.add_result(agent_id, execution.output_message)

                        results.append(HandoffResult(
                            handoff_id=str(uuid4()),
                            status=HandoffStatus.COMPLETED,
                            from_agent_id=agent_id,
                            to_agent_id="",  # Will be set in next iteration
                            input_message=current_input,
                            output_message=execution.output_message,
                            execution_time_ms=execution_time,
                        ))
                    else:
                        results.append(HandoffResult(
                            handoff_id=str(uuid4()),
                            status=HandoffStatus.FAILED,
                            from_agent_id=agent_id,
                            to_agent_id="",
                            input_message=current_input,
                            error="Agent execution failed",
                            execution_time_ms=execution_time,
                        ))

                except Exception as e:
                    logger.error(
                        "Chain execution error",
                        agent_id=agent_id,
                        step=step,
                        error=str(e),
                    )
                    results.append(HandoffResult(
                        handoff_id=str(uuid4()),
                        status=HandoffStatus.FAILED,
                        from_agent_id=agent_id,
                        to_agent_id="",
                        input_message=context.get_last_result() or context.original_input,
                        error=str(e),
                    ))

            # Get next agents
            next_agents = []
            for agent_id in current_agents:
                next_agents.extend(chain.get_next_agents(agent_id, context))

            current_agents = list(set(next_agents))  # Remove duplicates

        return results


# Predefined chain templates
class ChainTemplates:
    """Predefined agent chain templates."""

    @staticmethod
    def research_and_write() -> HandoffChain:
        """Research agent -> Writing agent chain."""
        chain = HandoffChain(
            name="Research and Write",
            description="Research a topic and write an article",
        )
        # Would be configured with actual agent IDs
        return chain

    @staticmethod
    def code_review() -> HandoffChain:
        """Code review chain with multiple reviewers."""
        chain = HandoffChain(
            name="Code Review Pipeline",
            description="Multi-stage code review",
        )
        return chain

    @staticmethod
    def customer_support() -> HandoffChain:
        """Customer support escalation chain."""
        chain = HandoffChain(
            name="Customer Support",
            description="Tiered customer support with escalation",
        )
        return chain
