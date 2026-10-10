"""Workflow Automation API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
import structlog

from app.api.deps import get_current_user
from app.models.user import User
from app.services.workflow.engine import get_workflow_engine

from app.services.workflow.models import (
    WorkflowExecutionStatus,
    WorkflowStatus,
    WorkflowTriggerType,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/workflows", tags=["workflows"])


# --- Request/Response Models ---

class CreateWorkflowRequest(BaseModel):
    """Request to create a workflow."""
    name: str = Field(..., min_length=1, max_length=200)
    organization_id: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    triggers: list[dict[str, Any]] = Field(default_factory=list, max_length=50)
    steps: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    created_by: str | None = Field(default=None, max_length=200)


class CreateFromTemplateRequest(BaseModel):
    """Request to create workflow from template."""
    template_name: str = Field(..., min_length=1, max_length=200)
    organization_id: str = Field(..., min_length=1, max_length=200)
    created_by: str | None = Field(default=None, max_length=200)
    overrides: dict[str, Any] | None = None


class StartExecutionRequest(BaseModel):
    """Request to start workflow execution."""
    input_data: dict[str, Any] = Field(default_factory=dict)
    triggered_by: str | None = None


class HandleTriggerRequest(BaseModel):
    """Request to handle an external trigger."""
    trigger_type: WorkflowTriggerType
    event_data: dict[str, Any] = Field(default_factory=dict)
    triggered_by: str | None = None


# --- Workflow Endpoints ---

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_workflow(request: CreateWorkflowRequest, _current_user: User = Depends(get_current_user)):
    """Create a new workflow."""
    engine = get_workflow_engine()
    workflow = await engine.create_workflow(
        name=request.name,
        organization_id=request.organization_id,
        description=request.description,
        triggers=request.triggers,
        steps=request.steps,
        created_by=request.created_by,
    )
    return {"workflow": workflow.model_dump()}


@router.post("/from-template", status_code=status.HTTP_201_CREATED)
async def create_from_template(request: CreateFromTemplateRequest, _current_user: User = Depends(get_current_user)):
    """Create a workflow from a template."""
    engine = get_workflow_engine()
    try:
        workflow = await engine.create_from_template(
            template_name=request.template_name,
            organization_id=request.organization_id,
            created_by=request.created_by,
            overrides=request.overrides,
        )
        return {"workflow": workflow.model_dump()}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid workflow configuration. Please check the template name and parameters.")


@router.get("/templates")
async def list_templates(_current_user: User = Depends(get_current_user)):
    """List available workflow templates."""
    engine = get_workflow_engine()
    templates = engine.get_available_templates()
    return {"templates": templates}


@router.get("")
async def list_workflows(
    organization_id: str | None = None,
    status: WorkflowStatus | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _current_user: User = Depends(get_current_user),
):
    """List workflows with optional filters."""
    engine = get_workflow_engine()
    workflows = await engine.list_workflows(organization_id, status)
    paginated = workflows[offset:offset + limit]
    return {
        "workflows": [w.model_dump() for w in paginated],
        "total": len(workflows),
        "limit": limit,
        "offset": offset,
    }


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str, _current_user: User = Depends(get_current_user)):
    """Get a workflow by ID."""
    engine = get_workflow_engine()
    workflow = await engine.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"workflow": workflow.model_dump()}


@router.post("/{workflow_id}/activate")
async def activate_workflow(workflow_id: str, _current_user: User = Depends(get_current_user)):
    """Activate a workflow."""
    engine = get_workflow_engine()
    workflow = await engine.activate_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"workflow": workflow.model_dump()}


@router.post("/{workflow_id}/pause")
async def pause_workflow(workflow_id: str, _current_user: User = Depends(get_current_user)):
    """Pause a workflow."""
    engine = get_workflow_engine()
    workflow = await engine.pause_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"workflow": workflow.model_dump()}


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(workflow_id: str, _current_user: User = Depends(get_current_user)) -> None:
    """Delete a workflow."""
    engine = get_workflow_engine()
    deleted = await engine.delete_workflow(workflow_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Workflow not found")


# --- Execution Endpoints ---

@router.post("/{workflow_id}/execute")
async def start_execution(workflow_id: str, request: StartExecutionRequest, _current_user: User = Depends(get_current_user)):
    """Start a workflow execution."""
    engine = get_workflow_engine()
    try:
        execution = await engine.start_execution(
            workflow_id=workflow_id,
            input_data=request.input_data,
            triggered_by=request.triggered_by,
        )
        return {"execution": execution.model_dump()}
    except ValueError:
        raise HTTPException(status_code=404, detail="Workflow not found.")


@router.post("/trigger")
async def handle_trigger(request: HandleTriggerRequest, _current_user: User = Depends(get_current_user)):
    """Handle an external trigger event."""
    engine = get_workflow_engine()
    executions = await engine.handle_trigger(
        trigger_type=request.trigger_type,
        event_data=request.event_data,
        triggered_by=request.triggered_by,
    )
    return {
        "triggered_count": len(executions),
        "executions": [e.model_dump() for e in executions],
    }


@router.get("/executions")
async def list_executions(
    workflow_id: str | None = None,
    status: WorkflowExecutionStatus | None = None,
    limit: int = Query(default=100, le=500),
    _current_user: User = Depends(get_current_user),
):
    """List workflow executions."""
    engine = get_workflow_engine()
    executions = await engine.list_executions(workflow_id, status, limit)
    return {"executions": [e.model_dump() for e in executions]}


@router.get("/executions/{execution_id}")
async def get_execution(execution_id: str, _current_user: User = Depends(get_current_user)):
    """Get an execution by ID."""
    engine = get_workflow_engine()
    execution = await engine.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return {"execution": execution.model_dump()}


@router.post("/executions/{execution_id}/cancel")
async def cancel_execution(execution_id: str, _current_user: User = Depends(get_current_user)):
    """Cancel a running execution."""
    engine = get_workflow_engine()
    execution = await engine.cancel_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return {"execution": execution.model_dump()}


# --- Dashboard Endpoint ---

@router.get("/dashboard")
async def get_workflow_dashboard(organization_id: str, _current_user: User = Depends(get_current_user)):
    """Get workflow dashboard data."""
    engine = get_workflow_engine()

    workflows = await engine.list_workflows(organization_id)
    executions = await engine.list_executions(limit=100)

    # Calculate stats
    active_workflows = len([w for w in workflows if w.status == WorkflowStatus.ACTIVE])
    total_executions = len(executions)
    successful = len([e for e in executions if e.status == WorkflowExecutionStatus.COMPLETED])
    failed = len([e for e in executions if e.status == WorkflowExecutionStatus.FAILED])
    running = len([e for e in executions if e.status == WorkflowExecutionStatus.RUNNING])

    # Recent executions
    recent_executions = [
        {
            "id": e.id,
            "workflow_name": e.workflow_name,
            "status": e.status.value,
            "trigger_type": e.trigger_type.value,
            "started_at": e.started_at.isoformat() if e.started_at else None,
            "duration_ms": e.duration_ms,
        }
        for e in executions[:10]
    ]

    return {
        "summary": {
            "total_workflows": len(workflows),
            "active_workflows": active_workflows,
            "total_executions": total_executions,
            "successful_executions": successful,
            "failed_executions": failed,
            "running_executions": running,
            "success_rate": (successful / total_executions * 100) if total_executions > 0 else 0,
        },
        "recent_executions": recent_executions,
        "workflows": [
            {
                "id": w.id,
                "name": w.name,
                "status": w.status.value,
                "triggers_count": len(w.triggers),
                "steps_count": len(w.steps),
            }
            for w in workflows[:10]
        ],
    }
