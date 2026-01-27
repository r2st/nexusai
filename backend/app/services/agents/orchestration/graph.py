"""
Agent Graph

Graph-based workflow definition for agent orchestration.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
import asyncio
import logging

from .state import AgentState, StateStatus

logger = logging.getLogger(__name__)


class NodeType(str, Enum):
    """Types of graph nodes."""
    START = "start"
    END = "end"
    ACTION = "action"  # Execute a function
    TOOL = "tool"  # Call a tool
    LLM = "llm"  # Call an LLM
    CONDITIONAL = "conditional"  # Branch based on condition
    PARALLEL = "parallel"  # Execute multiple branches
    HUMAN = "human"  # Require human approval
    SUBGRAPH = "subgraph"  # Execute a nested graph


@dataclass
class GraphNode:
    """
    A node in the agent graph.
    """
    id: str
    type: NodeType
    
    # Action/function to execute
    action: Optional[Callable] = None
    
    # For tool nodes
    tool_name: Optional[str] = None
    
    # For LLM nodes
    prompt_template: Optional[str] = None
    model: Optional[str] = None
    
    # For conditional nodes
    condition: Optional[Callable] = None
    branches: Dict[str, str] = field(default_factory=dict)  # condition_result -> next_node
    
    # For parallel nodes
    parallel_branches: List[str] = field(default_factory=list)
    
    # For human nodes
    approval_message: Optional[str] = None
    
    # For subgraph nodes
    subgraph: Optional["AgentGraph"] = None
    
    # Metadata
    description: str = ""
    retry_on_failure: bool = True
    timeout_seconds: int = 60


@dataclass
class GraphEdge:
    """
    An edge connecting two nodes.
    """
    source: str
    target: str
    condition: Optional[str] = None  # For conditional edges


@dataclass
class GraphConfig:
    """Configuration for graph execution."""
    max_iterations: int = 100
    checkpoint_every: int = 5  # Checkpoint every N steps
    timeout_seconds: int = 3600  # Overall timeout
    enable_streaming: bool = True


class AgentGraph:
    """
    Graph-based agent workflow.
    
    Features:
    - Declarative workflow definition
    - Conditional branching
    - Parallel execution
    - Human-in-the-loop nodes
    - Subgraph composition
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[GraphConfig] = None,
    ):
        self.name = name
        self.config = config or GraphConfig()
        
        self._nodes: Dict[str, GraphNode] = {}
        self._edges: List[GraphEdge] = []
        self._start_node: Optional[str] = None
        self._end_nodes: List[str] = []
    
    def add_node(self, node: GraphNode) -> "AgentGraph":
        """Add a node to the graph."""
        self._nodes[node.id] = node
        
        if node.type == NodeType.START:
            self._start_node = node.id
        elif node.type == NodeType.END:
            self._end_nodes.append(node.id)
        
        return self
    
    def add_edge(
        self,
        source: str,
        target: str,
        condition: Optional[str] = None,
    ) -> "AgentGraph":
        """Add an edge between nodes."""
        self._edges.append(GraphEdge(source, target, condition))
        return self
    
    def set_entry(self, node_id: str) -> "AgentGraph":
        """Set the entry point."""
        self._start_node = node_id
        return self
    
    def get_next_nodes(
        self,
        current: str,
        condition_result: Optional[str] = None,
    ) -> List[str]:
        """Get the next nodes from current node."""
        next_nodes = []
        
        for edge in self._edges:
            if edge.source == current:
                if edge.condition is None or edge.condition == condition_result:
                    next_nodes.append(edge.target)
        
        return next_nodes
    
    def validate(self) -> List[str]:
        """
        Validate the graph structure.
        
        Returns:
            List of validation errors
        """
        errors = []
        
        if not self._start_node:
            errors.append("No start node defined")
        
        if not self._end_nodes:
            errors.append("No end nodes defined")
        
        # Check all edges reference valid nodes
        for edge in self._edges:
            if edge.source not in self._nodes:
                errors.append(f"Edge references unknown source: {edge.source}")
            if edge.target not in self._nodes:
                errors.append(f"Edge references unknown target: {edge.target}")
        
        # Check for unreachable nodes
        reachable = set()
        to_visit = [self._start_node] if self._start_node else []
        while to_visit:
            node = to_visit.pop()
            if node in reachable:
                continue
            reachable.add(node)
            for edge in self._edges:
                if edge.source == node:
                    to_visit.append(edge.target)
        
        unreachable = set(self._nodes.keys()) - reachable
        for node_id in unreachable:
            if node_id != self._start_node:
                errors.append(f"Unreachable node: {node_id}")
        
        return errors
    
    async def execute(
        self,
        state: AgentState,
        context: Dict[str, Any],
    ) -> AgentState:
        """
        Execute the graph.
        
        Args:
            state: Initial state
            context: Execution context (tools, LLM service, etc.)
            
        Returns:
            Final state
        """
        # Validate
        errors = self.validate()
        if errors:
            state.fail(f"Graph validation failed: {errors}")
            return state
        
        state.workflow_id = self.name
        state.status = StateStatus.RUNNING
        
        iteration = 0
        current_node = self._start_node
        
        while iteration < self.config.max_iterations:
            iteration += 1
            
            # Check status
            if state.status in (StateStatus.COMPLETED, StateStatus.FAILED, StateStatus.CANCELLED):
                break
            
            if state.status == StateStatus.WAITING:
                # Waiting for human approval
                logger.info(f"Workflow {state.run_id} waiting for approval")
                break
            
            # Get current node
            node = self._nodes.get(current_node)
            if not node:
                state.fail(f"Unknown node: {current_node}")
                break
            
            logger.debug(f"Executing node: {node.id} (type={node.type})")
            state.set_node(node.id)
            
            # Execute node
            try:
                result = await self._execute_node(node, state, context)
                
                # Determine next node
                if node.type == NodeType.END:
                    state.complete(state.output_data)
                    break
                elif node.type == NodeType.CONDITIONAL:
                    next_nodes = self.get_next_nodes(current_node, result)
                else:
                    next_nodes = self.get_next_nodes(current_node)
                
                if not next_nodes:
                    state.fail(f"No outgoing edges from node: {current_node}")
                    break
                
                current_node = next_nodes[0]  # Take first for now
                
            except Exception as e:
                logger.exception(f"Node execution error: {e}")
                state.add_error(str(e), node.id)
                
                if state.retry_count >= state.max_retries:
                    state.fail(f"Max retries exceeded: {e}")
                    break
                
                # Retry logic
                if node.retry_on_failure:
                    await asyncio.sleep(1)  # Brief pause before retry
                    continue
                else:
                    state.fail(str(e))
                    break
            
            # Checkpoint periodically
            if iteration % self.config.checkpoint_every == 0:
                # Would save checkpoint here
                pass
        
        if iteration >= self.config.max_iterations:
            state.fail("Max iterations exceeded")
        
        return state
    
    async def _execute_node(
        self,
        node: GraphNode,
        state: AgentState,
        context: Dict[str, Any],
    ) -> Optional[str]:
        """Execute a single node."""
        
        if node.type == NodeType.START:
            return None
        
        elif node.type == NodeType.END:
            return None
        
        elif node.type == NodeType.ACTION:
            if node.action:
                result = await node.action(state, context)
                if result:
                    state.intermediate_data[f"{node.id}_result"] = result
                return None
        
        elif node.type == NodeType.TOOL:
            if node.tool_name:
                tool_executor = context.get("tool_executor")
                if tool_executor:
                    # Get tool arguments from state
                    args = state.intermediate_data.get(f"{node.id}_args", {})
                    call_id = state.add_tool_call(node.tool_name, args)
                    
                    result = await tool_executor.execute(
                        node.tool_name,
                        args,
                        context.get("execution_context"),
                    )
                    
                    state.add_tool_result(call_id, result.data if result else None)
            return None
        
        elif node.type == NodeType.LLM:
            llm_service = context.get("llm_service")
            if llm_service and node.prompt_template:
                # Format prompt with state data
                prompt = node.prompt_template.format(**state.intermediate_data)
                
                response = await llm_service.generate(
                    prompt,
                    model=node.model,
                )
                
                state.add_message("assistant", response)
                state.intermediate_data[f"{node.id}_response"] = response
            return None
        
        elif node.type == NodeType.CONDITIONAL:
            if node.condition:
                result = await node.condition(state, context)
                return str(result)
            return None
        
        elif node.type == NodeType.PARALLEL:
            # Execute branches in parallel
            tasks = []
            for branch_node_id in node.parallel_branches:
                branch_node = self._nodes.get(branch_node_id)
                if branch_node:
                    tasks.append(self._execute_node(branch_node, state, context))
            
            await asyncio.gather(*tasks)
            return None
        
        elif node.type == NodeType.HUMAN:
            # Request human approval
            approval_id = f"approval_{node.id}_{state.run_id[:8]}"
            state.request_approval(
                approval_id,
                {
                    "node": node.id,
                    "message": node.approval_message,
                    "context": state.intermediate_data,
                },
            )
            return None
        
        elif node.type == NodeType.SUBGRAPH:
            if node.subgraph:
                # Execute nested graph
                await node.subgraph.execute(state, context)
            return None
        
        return None


def create_simple_workflow(
    name: str,
    steps: List[Dict[str, Any]],
) -> AgentGraph:
    """
    Create a simple linear workflow from a list of steps.
    
    Each step is a dict with:
    - name: Step name
    - type: "action", "tool", "llm", "human"
    - action/tool_name/prompt/message: Depending on type
    """
    graph = AgentGraph(name)
    
    # Add start node
    graph.add_node(GraphNode(id="start", type=NodeType.START))
    
    prev_node = "start"
    
    for i, step in enumerate(steps):
        node_id = step.get("name", f"step_{i}")
        step_type = step.get("type", "action")
        
        if step_type == "action":
            node = GraphNode(
                id=node_id,
                type=NodeType.ACTION,
                action=step.get("action"),
                description=step.get("description", ""),
            )
        elif step_type == "tool":
            node = GraphNode(
                id=node_id,
                type=NodeType.TOOL,
                tool_name=step.get("tool_name"),
                description=step.get("description", ""),
            )
        elif step_type == "llm":
            node = GraphNode(
                id=node_id,
                type=NodeType.LLM,
                prompt_template=step.get("prompt"),
                model=step.get("model"),
                description=step.get("description", ""),
            )
        elif step_type == "human":
            node = GraphNode(
                id=node_id,
                type=NodeType.HUMAN,
                approval_message=step.get("message"),
                description=step.get("description", ""),
            )
        else:
            continue
        
        graph.add_node(node)
        graph.add_edge(prev_node, node_id)
        prev_node = node_id
    
    # Add end node
    graph.add_node(GraphNode(id="end", type=NodeType.END))
    graph.add_edge(prev_node, "end")
    
    return graph
