"""
Agent State Management

Manages state persistence and checkpointing for long-running agents.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, TypeVar, Generic
import asyncio
import json
import logging
import uuid

logger = logging.getLogger(__name__)

T = TypeVar("T")


class StateStatus(str, Enum):
    """Status of agent state."""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING = "waiting"  # Waiting for human input
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentState(Generic[T]):
    """
    State container for an agent workflow.
    
    Tracks:
    - Current node/step
    - Accumulated data
    - Execution history
    - Errors and retries
    """
    # Identity
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str = ""
    
    # Current position
    current_node: str = "start"
    previous_nodes: List[str] = field(default_factory=list)
    
    # Status
    status: StateStatus = StateStatus.CREATED
    
    # Data
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    intermediate_data: Dict[str, Any] = field(default_factory=dict)
    
    # Messages (for chat-style agents)
    messages: List[Dict[str, Any]] = field(default_factory=list)
    
    # Tool calls
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: Dict[str, Any] = field(default_factory=dict)
    
    # Errors
    errors: List[Dict[str, Any]] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3
    
    # Human-in-the-loop
    pending_approval: Optional[str] = None
    approvals: List[Dict[str, Any]] = field(default_factory=list)
    
    # Metadata
    tenant_id: str = ""
    user_id: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    # Checkpointing
    checkpoint_version: int = 0
    
    def update(self) -> None:
        """Update timestamp and version."""
        self.updated_at = datetime.utcnow()
        self.checkpoint_version += 1
    
    def set_node(self, node: str) -> None:
        """Move to a new node."""
        if self.current_node:
            self.previous_nodes.append(self.current_node)
        self.current_node = node
        self.update()
    
    def add_message(self, role: str, content: str) -> None:
        """Add a message to history."""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        })
        self.update()
    
    def add_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        call_id: Optional[str] = None,
    ) -> str:
        """Record a tool call."""
        call_id = call_id or str(uuid.uuid4())[:8]
        self.tool_calls.append({
            "id": call_id,
            "tool": tool_name,
            "arguments": arguments,
            "timestamp": datetime.utcnow().isoformat(),
        })
        self.update()
        return call_id
    
    def add_tool_result(self, call_id: str, result: Any) -> None:
        """Record a tool result."""
        self.tool_results[call_id] = {
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.update()
    
    def add_error(self, error: str, node: Optional[str] = None) -> None:
        """Record an error."""
        self.errors.append({
            "error": error,
            "node": node or self.current_node,
            "timestamp": datetime.utcnow().isoformat(),
        })
        self.retry_count += 1
        self.update()
    
    def request_approval(self, approval_id: str, details: Dict[str, Any]) -> None:
        """Request human approval."""
        self.pending_approval = approval_id
        self.status = StateStatus.WAITING
        self.intermediate_data["pending_approval_details"] = details
        self.update()
    
    def record_approval(self, approved: bool, approved_by: str, comments: str = "") -> None:
        """Record approval decision."""
        self.approvals.append({
            "approval_id": self.pending_approval,
            "approved": approved,
            "approved_by": approved_by,
            "comments": comments,
            "timestamp": datetime.utcnow().isoformat(),
        })
        self.pending_approval = None
        self.status = StateStatus.RUNNING if approved else StateStatus.CANCELLED
        self.update()
    
    def complete(self, output: Dict[str, Any]) -> None:
        """Mark as completed."""
        self.output_data = output
        self.status = StateStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.update()
    
    def fail(self, error: str) -> None:
        """Mark as failed."""
        self.add_error(error)
        self.status = StateStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.update()
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "run_id": self.run_id,
            "workflow_id": self.workflow_id,
            "current_node": self.current_node,
            "previous_nodes": self.previous_nodes,
            "status": self.status.value,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "intermediate_data": self.intermediate_data,
            "messages": self.messages,
            "tool_calls": self.tool_calls,
            "tool_results": self.tool_results,
            "errors": self.errors,
            "retry_count": self.retry_count,
            "pending_approval": self.pending_approval,
            "approvals": self.approvals,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "checkpoint_version": self.checkpoint_version,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentState":
        """Deserialize from dictionary."""
        state = cls(
            run_id=data["run_id"],
            workflow_id=data["workflow_id"],
            current_node=data["current_node"],
            previous_nodes=data["previous_nodes"],
            status=StateStatus(data["status"]),
            input_data=data["input_data"],
            output_data=data["output_data"],
            intermediate_data=data["intermediate_data"],
            messages=data["messages"],
            tool_calls=data["tool_calls"],
            tool_results=data["tool_results"],
            errors=data["errors"],
            retry_count=data["retry_count"],
            pending_approval=data.get("pending_approval"),
            approvals=data["approvals"],
            tenant_id=data["tenant_id"],
            user_id=data["user_id"],
            checkpoint_version=data["checkpoint_version"],
        )
        state.created_at = datetime.fromisoformat(data["created_at"])
        state.updated_at = datetime.fromisoformat(data["updated_at"])
        if data.get("completed_at"):
            state.completed_at = datetime.fromisoformat(data["completed_at"])
        return state


class StateStore:
    """
    Persistent state storage.
    
    Stores agent state for durability and recovery.
    """
    
    def __init__(self, backend: Optional[Any] = None):
        """
        Initialize state store.
        
        Args:
            backend: Storage backend (Redis, PostgreSQL, etc.)
        """
        self.backend = backend
        self._local_store: Dict[str, AgentState] = {}
    
    async def save(self, state: AgentState) -> None:
        """Save state."""
        if self.backend:
            try:
                key = f"agent_state:{state.run_id}"
                await self.backend.set(key, json.dumps(state.to_dict()))
            except Exception as e:
                logger.error(f"Failed to save state: {e}")
        
        # Always keep local copy
        self._local_store[state.run_id] = state
    
    async def load(self, run_id: str) -> Optional[AgentState]:
        """Load state by run ID."""
        # Try backend first
        if self.backend:
            try:
                key = f"agent_state:{run_id}"
                data = await self.backend.get(key)
                if data:
                    return AgentState.from_dict(json.loads(data))
            except Exception as e:
                logger.error(f"Failed to load state: {e}")
        
        # Fall back to local
        return self._local_store.get(run_id)
    
    async def delete(self, run_id: str) -> None:
        """Delete state."""
        if self.backend:
            try:
                key = f"agent_state:{run_id}"
                await self.backend.delete(key)
            except Exception:
                pass
        
        if run_id in self._local_store:
            del self._local_store[run_id]
    
    async def list_by_status(
        self,
        status: StateStatus,
        tenant_id: Optional[str] = None,
    ) -> List[AgentState]:
        """List states by status."""
        results = []
        for state in self._local_store.values():
            if state.status == status:
                if tenant_id is None or state.tenant_id == tenant_id:
                    results.append(state)
        return results


class CheckpointManager:
    """
    Manages checkpoints for workflow recovery.
    
    Features:
    - Version-based checkpointing
    - Rollback capability
    - Checkpoint pruning
    """
    
    def __init__(
        self,
        state_store: StateStore,
        max_checkpoints: int = 10,
    ):
        self.state_store = state_store
        self.max_checkpoints = max_checkpoints
        self._checkpoints: Dict[str, List[Dict[str, Any]]] = {}
    
    async def checkpoint(self, state: AgentState) -> int:
        """
        Create a checkpoint.
        
        Returns:
            Checkpoint version
        """
        run_id = state.run_id
        
        if run_id not in self._checkpoints:
            self._checkpoints[run_id] = []
        
        # Add checkpoint
        checkpoint = {
            "version": state.checkpoint_version,
            "data": state.to_dict(),
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._checkpoints[run_id].append(checkpoint)
        
        # Prune old checkpoints
        if len(self._checkpoints[run_id]) > self.max_checkpoints:
            self._checkpoints[run_id] = self._checkpoints[run_id][-self.max_checkpoints:]
        
        # Save current state
        await self.state_store.save(state)
        
        logger.debug(f"Created checkpoint v{state.checkpoint_version} for {run_id}")
        return state.checkpoint_version
    
    async def restore(
        self,
        run_id: str,
        version: Optional[int] = None,
    ) -> Optional[AgentState]:
        """
        Restore from checkpoint.
        
        Args:
            run_id: Run ID
            version: Specific version, or None for latest
            
        Returns:
            Restored state or None
        """
        checkpoints = self._checkpoints.get(run_id, [])
        if not checkpoints:
            # Try loading from store
            return await self.state_store.load(run_id)
        
        if version is not None:
            # Find specific version
            for cp in checkpoints:
                if cp["version"] == version:
                    return AgentState.from_dict(cp["data"])
            return None
        
        # Return latest
        return AgentState.from_dict(checkpoints[-1]["data"])
    
    async def get_history(self, run_id: str) -> List[Dict[str, Any]]:
        """Get checkpoint history for a run."""
        checkpoints = self._checkpoints.get(run_id, [])
        return [
            {
                "version": cp["version"],
                "timestamp": cp["timestamp"],
                "node": cp["data"]["current_node"],
                "status": cp["data"]["status"],
            }
            for cp in checkpoints
        ]
    
    async def rollback(self, run_id: str, to_version: int) -> Optional[AgentState]:
        """
        Rollback to a specific version.
        
        This restores the state and removes later checkpoints.
        """
        state = await self.restore(run_id, to_version)
        if not state:
            return None
        
        # Remove checkpoints after this version
        if run_id in self._checkpoints:
            self._checkpoints[run_id] = [
                cp for cp in self._checkpoints[run_id]
                if cp["version"] <= to_version
            ]
        
        # Save restored state
        state.update()
        await self.state_store.save(state)
        
        logger.info(f"Rolled back {run_id} to version {to_version}")
        return state
