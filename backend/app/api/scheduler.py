"""Background Agent Scheduler API endpoints."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.api.deps import get_current_user

logger = structlog.get_logger()
from app.core.database import get_db
from app.models.user import User
from app.services.agents.scheduler import (
    BackgroundAgentScheduler,
    ScheduledTask,
    TaskExecution,
    TaskPriority,
    TaskStatus,
    TaskTriggerType,
    get_agent_scheduler,
)

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


# ============================================================================
# Request/Response Models
# ============================================================================


class CreateTaskRequest(BaseModel):
    """Request to create a scheduled task."""

    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., max_length=2000)
    task_type: str = Field(..., min_length=1, max_length=100)
    trigger_type: str = Field(..., min_length=1, max_length=50)
    priority: str = Field(default="normal", max_length=20)

    # Scheduling options
    cron_expression: str | None = Field(default=None, max_length=100)
    interval_seconds: int | None = Field(default=None, ge=1, le=86400)
    event_trigger: str | None = Field(default=None, max_length=200)
    scheduled_time: datetime | None = None

    # Execution options
    handler: str | None = Field(default=None, max_length=500)
    arguments: dict[str, Any] = {}
    timeout_seconds: int = Field(default=300, ge=1, le=3600)
    max_retries: int = Field(default=3, ge=0, le=10)

    # Context
    organization_id: str | None = Field(default=None, max_length=200)
    tags: list[str] = Field(default_factory=list, max_length=20)


class TaskResponse(BaseModel):
    """Response for a scheduled task."""

    id: str
    name: str
    description: str
    task_type: str
    trigger_type: str
    priority: str
    enabled: bool

    cron_expression: str | None
    interval_seconds: int | None
    event_trigger: str | None

    status: str
    last_run_at: str | None
    next_run_at: str | None
    run_count: int
    failure_count: int
    last_error: str | None

    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ExecutionResponse(BaseModel):
    """Response for a task execution."""

    id: str
    task_id: str
    status: str
    started_at: str
    completed_at: str | None
    duration_ms: float | None
    error: str | None

    class Config:
        from_attributes = True


class SchedulerStatsResponse(BaseModel):
    """Scheduler statistics response."""

    scheduler_running: bool
    total_tasks: int
    enabled_tasks: int
    running_tasks: int
    max_concurrent_tasks: int
    last_24h: dict[str, Any]


class TriggerEventRequest(BaseModel):
    """Request to trigger an event."""

    event_name: str
    event_data: dict[str, Any] = {}


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/status", response_model=SchedulerStatsResponse)
async def get_scheduler_status(
    user: User = Depends(get_current_user),
) -> SchedulerStatsResponse:
    """Get scheduler status and statistics."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view scheduler status",
        )

    scheduler = get_agent_scheduler()
    stats = scheduler.get_statistics()
    return SchedulerStatsResponse(**stats)


@router.post("/start")
async def start_scheduler(
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Start the background scheduler."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can start the scheduler",
        )

    scheduler = get_agent_scheduler()
    await scheduler.start()
    return {"status": "started", "message": "Scheduler started successfully"}


@router.post("/stop")
async def stop_scheduler(
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Stop the background scheduler."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can stop the scheduler",
        )

    scheduler = get_agent_scheduler()
    await scheduler.stop()
    return {"status": "stopped", "message": "Scheduler stopped successfully"}


@router.get("/tasks", response_model=list[TaskResponse])
async def list_tasks(
    status_filter: str | None = None,
    task_type: str | None = None,
    user: User = Depends(get_current_user),
) -> list[TaskResponse]:
    """List all scheduled tasks."""
    scheduler = get_agent_scheduler()

    task_status = TaskStatus(status_filter) if status_filter else None

    tasks = scheduler.list_tasks(
        status=task_status,
        task_type=task_type,
    )

    return [
        TaskResponse(
            id=t.id,
            name=t.name,
            description=t.description,
            task_type=t.task_type,
            trigger_type=t.trigger_type.value,
            priority=t.priority.value,
            enabled=t.enabled,
            cron_expression=t.cron_expression,
            interval_seconds=t.interval_seconds,
            event_trigger=t.event_trigger,
            status=t.status.value,
            last_run_at=t.last_run_at.isoformat() if t.last_run_at else None,
            next_run_at=t.next_run_at.isoformat() if t.next_run_at else None,
            run_count=t.run_count,
            failure_count=t.failure_count,
            last_error=t.last_error,
            created_at=t.created_at.isoformat(),
            updated_at=t.updated_at.isoformat(),
        )
        for t in tasks
    ]


@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    request: CreateTaskRequest,
    user: User = Depends(get_current_user),
) -> TaskResponse:
    """Create a new scheduled task."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create scheduled tasks",
        )

    scheduler = get_agent_scheduler()

    from uuid import uuid4

    task = ScheduledTask(
        id=str(uuid4()),
        name=request.name,
        description=request.description,
        task_type=request.task_type,
        trigger_type=TaskTriggerType(request.trigger_type),
        priority=TaskPriority(request.priority),
        cron_expression=request.cron_expression,
        interval_seconds=request.interval_seconds,
        event_trigger=request.event_trigger,
        scheduled_time=request.scheduled_time,
        handler=request.handler,
        arguments=request.arguments,
        timeout_seconds=request.timeout_seconds,
        max_retries=request.max_retries,
        organization_id=request.organization_id,
        user_id=str(user.id),
        tags=request.tags,
    )

    task = scheduler.schedule_task(task)

    return TaskResponse(
        id=task.id,
        name=task.name,
        description=task.description,
        task_type=task.task_type,
        trigger_type=task.trigger_type.value,
        priority=task.priority.value,
        enabled=task.enabled,
        cron_expression=task.cron_expression,
        interval_seconds=task.interval_seconds,
        event_trigger=task.event_trigger,
        status=task.status.value,
        last_run_at=task.last_run_at.isoformat() if task.last_run_at else None,
        next_run_at=task.next_run_at.isoformat() if task.next_run_at else None,
        run_count=task.run_count,
        failure_count=task.failure_count,
        last_error=task.last_error,
        created_at=task.created_at.isoformat(),
        updated_at=task.updated_at.isoformat(),
    )


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    user: User = Depends(get_current_user),
) -> TaskResponse:
    """Get a specific task."""
    scheduler = get_agent_scheduler()
    task = scheduler.get_task(task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    return TaskResponse(
        id=task.id,
        name=task.name,
        description=task.description,
        task_type=task.task_type,
        trigger_type=task.trigger_type.value,
        priority=task.priority.value,
        enabled=task.enabled,
        cron_expression=task.cron_expression,
        interval_seconds=task.interval_seconds,
        event_trigger=task.event_trigger,
        status=task.status.value,
        last_run_at=task.last_run_at.isoformat() if task.last_run_at else None,
        next_run_at=task.next_run_at.isoformat() if task.next_run_at else None,
        run_count=task.run_count,
        failure_count=task.failure_count,
        last_error=task.last_error,
        created_at=task.created_at.isoformat(),
        updated_at=task.updated_at.isoformat(),
    )


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: str,
    user: User = Depends(get_current_user),
) -> None:
    """Delete a scheduled task."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete tasks",
        )

    scheduler = get_agent_scheduler()

    if not scheduler.delete_task(task_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )


@router.post("/tasks/{task_id}/trigger")
async def trigger_task(
    task_id: str,
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Manually trigger a task to run immediately."""
    scheduler = get_agent_scheduler()

    if not scheduler.trigger_task(task_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    return {"status": "triggered", "task_id": task_id}


@router.post("/tasks/{task_id}/pause")
async def pause_task(
    task_id: str,
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Pause a scheduled task."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can pause tasks",
        )

    scheduler = get_agent_scheduler()

    if not scheduler.pause_task(task_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found or not pausable",
        )

    return {"status": "paused", "task_id": task_id}


@router.post("/tasks/{task_id}/resume")
async def resume_task(
    task_id: str,
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Resume a paused task."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can resume tasks",
        )

    scheduler = get_agent_scheduler()

    if not scheduler.resume_task(task_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found or not paused",
        )

    return {"status": "resumed", "task_id": task_id}


@router.get("/tasks/{task_id}/executions", response_model=list[ExecutionResponse])
async def get_task_executions(
    task_id: str,
    limit: int = 10,
    user: User = Depends(get_current_user),
) -> list[ExecutionResponse]:
    """Get execution history for a task."""
    scheduler = get_agent_scheduler()

    if not scheduler.get_task(task_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    executions = scheduler.get_task_executions(task_id, limit=limit)

    return [
        ExecutionResponse(
            id=e.id,
            task_id=e.task_id,
            status=e.status.value,
            started_at=e.started_at.isoformat(),
            completed_at=e.completed_at.isoformat() if e.completed_at else None,
            duration_ms=e.duration_ms,
            error=e.error,
        )
        for e in executions
    ]


@router.post("/events/trigger")
async def trigger_event(
    request: TriggerEventRequest,
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Trigger an event to run event-based tasks."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can trigger events",
        )

    scheduler = get_agent_scheduler()
    triggered_count = await scheduler.trigger_event(
        request.event_name,
        request.event_data,
    )

    return {
        "status": "triggered",
        "event_name": request.event_name,
        "tasks_triggered": triggered_count,
    }
