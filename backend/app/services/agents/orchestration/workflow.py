"""
Workflow Engine

High-level workflow management and execution.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import asyncio
import logging
import uuid

from .graph import AgentGraph, GraphConfig
from .state import AgentState, StateStore, CheckpointManager, StateStatus

logger = logging.getLogger(__name__)


class WorkflowStatus(str, Enum):
    """Status of a workflow definition."""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


@dataclass
class WorkflowDefinition:
    """
    Definition of a reusable workflow.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    status: WorkflowStatus = WorkflowStatus.DRAFT
    
    # The graph
    graph: Optional[AgentGraph] = None
    
    # Configuration
    config: GraphConfig = field(default_factory=GraphConfig)
    
    # Input/output schema
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = ""
    
    # Tags for discovery
    tags: List[str] = field(default_factory=list)


@dataclass
class WorkflowRun:
    """
    A single execution of a workflow.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str = ""
    workflow_name: str = ""
    
    # State
    state: Optional[AgentState] = None
    
    # Execution info
    tenant_id: str = ""
    user_id: str = ""
    triggered_by: str = ""  # user, webhook, schedule, api
    
    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Results
    success: bool = False
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "status": self.state.status.value if self.state else "unknown",
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "triggered_by": self.triggered_by,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "success": self.success,
            "error": self.error,
        }


class WorkflowEngine:
    """
    Engine for managing and executing workflows.
    
    Features:
    - Workflow registration
    - Run management
    - Streaming progress
    - Resume from checkpoint
    """
    
    def __init__(
        self,
        state_store: Optional[StateStore] = None,
        checkpoint_manager: Optional[CheckpointManager] = None,
    ):
        self.state_store = state_store or StateStore()
        self.checkpoint_manager = checkpoint_manager or CheckpointManager(self.state_store)
        
        # Registered workflows
        self._workflows: Dict[str, WorkflowDefinition] = {}
        
        # Active runs
        self._runs: Dict[str, WorkflowRun] = {}
        
        # Event callbacks
        self._on_start: List[Callable] = []
        self._on_complete: List[Callable] = []
        self._on_error: List[Callable] = []
        self._on_progress: List[Callable] = []
    
    def register_workflow(self, workflow: WorkflowDefinition) -> None:
        """Register a workflow definition."""
        self._workflows[workflow.id] = workflow
        logger.info(f"Registered workflow: {workflow.name} (v{workflow.version})")
    
    def get_workflow(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """Get a workflow by ID."""
        return self._workflows.get(workflow_id)
    
    def list_workflows(
        self,
        status: Optional[WorkflowStatus] = None,
        tags: Optional[List[str]] = None,
    ) -> List[WorkflowDefinition]:
        """List workflows with optional filtering."""
        workflows = list(self._workflows.values())
        
        if status:
            workflows = [w for w in workflows if w.status == status]
        
        if tags:
            workflows = [
                w for w in workflows
                if any(t in w.tags for t in tags)
            ]
        
        return workflows
    
    async def start_run(
        self,
        workflow_id: str,
        input_data: Dict[str, Any],
        tenant_id: str,
        user_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> WorkflowRun:
        """
        Start a new workflow run.
        
        Args:
            workflow_id: Workflow definition ID
            input_data: Input data for the workflow
            tenant_id: Tenant ID
            user_id: User ID
            context: Execution context (tools, LLM service, etc.)
            
        Returns:
            WorkflowRun instance
        """
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Unknown workflow: {workflow_id}")
        
        if not workflow.graph:
            raise ValueError(f"Workflow has no graph: {workflow_id}")
        
        # Create run
        run = WorkflowRun(
            workflow_id=workflow_id,
            workflow_name=workflow.name,
            tenant_id=tenant_id,
            user_id=user_id,
            triggered_by="api",
        )
        
        # Create state
        state = AgentState(
            workflow_id=workflow_id,
            input_data=input_data,
            tenant_id=tenant_id,
            user_id=user_id,
        )
        run.state = state
        
        # Track run
        self._runs[run.id] = run
        
        # Notify start
        for callback in self._on_start:
            try:
                await callback(run)
            except Exception as e:
                logger.warning(f"Start callback error: {e}")
        
        # Execute
        run.started_at = datetime.utcnow()
        
        try:
            context = context or {}
            context["run_id"] = run.id
            
            await workflow.graph.execute(state, context)
            
            run.success = state.status == StateStatus.COMPLETED
            
        except Exception as e:
            logger.exception(f"Workflow execution error: {e}")
            run.error = str(e)
            run.success = False
            state.fail(str(e))
            
            for callback in self._on_error:
                try:
                    await callback(run, e)
                except Exception:
                    pass
        
        finally:
            run.completed_at = datetime.utcnow()
            
            # Notify complete
            for callback in self._on_complete:
                try:
                    await callback(run)
                except Exception as e:
                    logger.warning(f"Complete callback error: {e}")
        
        return run
    
    async def resume_run(
        self,
        run_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[WorkflowRun]:
        """
        Resume a paused or waiting run.
        
        Args:
            run_id: Run ID
            context: Execution context
            
        Returns:
            Updated WorkflowRun or None
        """
        run = self._runs.get(run_id)
        if not run or not run.state:
            return None
        
        if run.state.status not in (StateStatus.PAUSED, StateStatus.WAITING):
            logger.warning(f"Cannot resume run in status: {run.state.status}")
            return run
        
        workflow = self._workflows.get(run.workflow_id)
        if not workflow or not workflow.graph:
            return None
        
        # Resume execution
        run.state.status = StateStatus.RUNNING
        
        try:
            context = context or {}
            context["run_id"] = run.id
            
            await workflow.graph.execute(run.state, context)
            run.success = run.state.status == StateStatus.COMPLETED
            
        except Exception as e:
            logger.exception(f"Resume error: {e}")
            run.error = str(e)
            run.success = False
        
        finally:
            if run.state.status in (StateStatus.COMPLETED, StateStatus.FAILED):
                run.completed_at = datetime.utcnow()
        
        return run
    
    async def cancel_run(self, run_id: str, reason: str = "") -> bool:
        """Cancel a running workflow."""
        run = self._runs.get(run_id)
        if not run or not run.state:
            return False
        
        if run.state.status in (StateStatus.COMPLETED, StateStatus.FAILED, StateStatus.CANCELLED):
            return False
        
        run.state.status = StateStatus.CANCELLED
        run.state.add_error(f"Cancelled: {reason}")
        run.completed_at = datetime.utcnow()
        run.error = reason
        
        logger.info(f"Cancelled run {run_id}: {reason}")
        return True
    
    async def approve_human_step(
        self,
        run_id: str,
        approved: bool,
        approved_by: str,
        comments: str = "",
    ) -> bool:
        """
        Approve or reject a human-in-the-loop step.
        
        Args:
            run_id: Run ID
            approved: Whether approved
            approved_by: Who approved
            comments: Optional comments
            
        Returns:
            True if approval recorded
        """
        run = self._runs.get(run_id)
        if not run or not run.state:
            return False
        
        if run.state.status != StateStatus.WAITING:
            return False
        
        run.state.record_approval(approved, approved_by, comments)
        
        if approved:
            # Resume the workflow
            await self.resume_run(run_id)
        
        return True
    
    def get_run(self, run_id: str) -> Optional[WorkflowRun]:
        """Get a run by ID."""
        return self._runs.get(run_id)
    
    def list_runs(
        self,
        workflow_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        status: Optional[StateStatus] = None,
    ) -> List[WorkflowRun]:
        """List runs with optional filtering."""
        runs = list(self._runs.values())
        
        if workflow_id:
            runs = [r for r in runs if r.workflow_id == workflow_id]
        
        if tenant_id:
            runs = [r for r in runs if r.tenant_id == tenant_id]
        
        if status:
            runs = [r for r in runs if r.state and r.state.status == status]
        
        return runs
    
    def on_start(self, callback: Callable) -> None:
        """Register start callback."""
        self._on_start.append(callback)
    
    def on_complete(self, callback: Callable) -> None:
        """Register complete callback."""
        self._on_complete.append(callback)
    
    def on_error(self, callback: Callable) -> None:
        """Register error callback."""
        self._on_error.append(callback)
    
    def on_progress(self, callback: Callable) -> None:
        """Register progress callback."""
        self._on_progress.append(callback)
