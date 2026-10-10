"""
Background Agent Scheduler

Handles scheduling and execution of autonomous agent tasks:
- Periodic DORA metrics collection
- Scheduled code quality scans
- Automated report generation
- Alert-triggered analysis
- Data sync jobs
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from enum import Enum
from typing import Any, Callable, Coroutine, Optional
from uuid import uuid4
import structlog
from croniter import croniter

logger = structlog.get_logger()


class TaskStatus(str, Enum):
    """Status of a scheduled task."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class TaskPriority(str, Enum):
    """Priority levels for tasks."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class TaskTriggerType(str, Enum):
    """How a task is triggered."""

    CRON = "cron"
    INTERVAL = "interval"
    EVENT = "event"
    MANUAL = "manual"
    ONE_TIME = "one_time"


@dataclass
class ScheduledTask:
    """A scheduled background task."""

    id: str
    name: str
    description: str
    task_type: str  # e.g., "dora_metrics", "code_scan", "report_generation"
    trigger_type: TaskTriggerType
    priority: TaskPriority = TaskPriority.NORMAL
    enabled: bool = True

    # Scheduling configuration
    cron_expression: Optional[str] = None  # For cron-based scheduling
    interval_seconds: Optional[int] = None  # For interval-based scheduling
    event_trigger: Optional[str] = None  # For event-based triggering
    scheduled_time: Optional[datetime] = None  # For one-time tasks

    # Execution configuration
    handler: Optional[str] = None  # Handler function name
    arguments: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 300  # 5 minutes default
    max_retries: int = 3
    retry_delay_seconds: int = 60

    # Context
    organization_id: Optional[str] = None
    user_id: Optional[str] = None
    tags: list[str] = field(default_factory=list)

    # State
    status: TaskStatus = TaskStatus.PENDING
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    run_count: int = 0
    failure_count: int = 0
    last_error: Optional[str] = None

    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskExecution:
    """Record of a task execution."""

    id: str
    task_id: str
    status: TaskStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0


class BackgroundAgentScheduler:
    """
    Scheduler for background agent tasks.

    Features:
    - Cron-based scheduling
    - Interval-based scheduling
    - Event-triggered tasks
    - Priority queue
    - Retry logic
    - Concurrent execution limits
    """

    def __init__(
        self,
        max_concurrent_tasks: int = 5,
        check_interval_seconds: int = 10,
    ):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.check_interval_seconds = check_interval_seconds

        # Task storage
        self._tasks: dict[str, ScheduledTask] = {}
        self._executions: dict[str, TaskExecution] = {}
        self._task_handlers: dict[str, Callable[..., Coroutine[Any, Any, dict]]] = {}

        # State
        self._running = False
        self._current_executions: dict[str, asyncio.Task] = {}
        self._scheduler_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

        # Register built-in handlers
        self._register_builtin_handlers()

    def _register_builtin_handlers(self) -> None:
        """Register built-in task handlers."""
        self.register_handler("dora_metrics_collection", self._handle_dora_metrics)
        self.register_handler("code_quality_scan", self._handle_code_quality_scan)
        self.register_handler("report_generation", self._handle_report_generation)
        self.register_handler("data_sync", self._handle_data_sync)
        self.register_handler("alert_analysis", self._handle_alert_analysis)
        self.register_handler("approval_expiry", self._handle_approval_expiry)

    def register_handler(
        self,
        handler_name: str,
        handler: Callable[..., Coroutine[Any, Any, dict]],
    ) -> None:
        """Register a task handler."""
        self._task_handlers[handler_name] = handler
        logger.info(f"Registered task handler: {handler_name}")

    async def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._running = True
        self._scheduler_task = asyncio.create_task(self._run_scheduler())
        logger.info("Background agent scheduler started")

    async def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False

        # Cancel all running tasks
        for task_id, task in self._current_executions.items():
            task.cancel()
            logger.info(f"Cancelled running task: {task_id}")

        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass

        logger.info("Background agent scheduler stopped")

    async def _run_scheduler(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                await self._process_due_tasks()
                await asyncio.sleep(self.check_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(self.check_interval_seconds)

    async def _process_due_tasks(self) -> None:
        """Process tasks that are due for execution."""
        now = datetime.now(UTC)
        due_tasks: list[ScheduledTask] = []

        async with self._lock:
            for task in self._tasks.values():
                if not task.enabled:
                    continue
                if task.status in [TaskStatus.RUNNING, TaskStatus.PAUSED]:
                    continue
                if task.next_run_at and task.next_run_at <= now:
                    due_tasks.append(task)

        # Sort by priority
        priority_order = {
            TaskPriority.CRITICAL: 0,
            TaskPriority.HIGH: 1,
            TaskPriority.NORMAL: 2,
            TaskPriority.LOW: 3,
        }
        due_tasks.sort(key=lambda t: priority_order.get(t.priority, 2))

        # Execute tasks up to concurrent limit
        available_slots = self.max_concurrent_tasks - len(self._current_executions)

        for task in due_tasks[:available_slots]:
            asyncio.create_task(self._execute_task(task))

    async def _execute_task(self, task: ScheduledTask) -> None:
        """Execute a single task."""
        execution_id = str(uuid4())
        execution = TaskExecution(
            id=execution_id,
            task_id=task.id,
            status=TaskStatus.RUNNING,
            started_at=datetime.now(UTC),
        )
        self._executions[execution_id] = execution

        task.status = TaskStatus.RUNNING
        task.last_run_at = execution.started_at
        task.run_count += 1

        needs_retry = False

        logger.info(
            f"Starting task execution",
            task_id=task.id,
            task_name=task.name,
            execution_id=execution_id,
        )

        try:
            handler = self._task_handlers.get(task.handler or task.task_type)
            if not handler:
                raise ValueError(f"No handler found for task type: {task.task_type}")

            async_task = asyncio.create_task(
                handler(task.arguments, task=task)
            )
            self._current_executions[execution_id] = async_task

            try:
                result = await asyncio.wait_for(
                    async_task,
                    timeout=task.timeout_seconds,
                )
                execution.result = result
                execution.status = TaskStatus.COMPLETED
                task.failure_count = 0
                task.last_error = None

                logger.info(
                    f"Task completed successfully",
                    task_id=task.id,
                    execution_id=execution_id,
                    duration_ms=execution.duration_ms,
                )

            except asyncio.TimeoutError:
                execution.status = TaskStatus.FAILED
                execution.error = f"Task timed out after {task.timeout_seconds}s"
                task.failure_count += 1
                task.last_error = execution.error
                needs_retry = task.failure_count < task.max_retries

                logger.error(
                    f"Task timed out",
                    task_id=task.id,
                    execution_id=execution_id,
                )

        except Exception as e:
            execution.status = TaskStatus.FAILED
            execution.error = str(e)
            task.failure_count += 1
            task.last_error = str(e)
            needs_retry = task.failure_count < task.max_retries

            logger.error(
                f"Task failed",
                task_id=task.id,
                execution_id=execution_id,
                error=str(e),
            )

        finally:
            execution.completed_at = datetime.now(UTC)
            execution.duration_ms = (
                execution.completed_at - execution.started_at
            ).total_seconds() * 1000

            if execution_id in self._current_executions:
                del self._current_executions[execution_id]

            if needs_retry:
                task.next_run_at = datetime.now(UTC) + timedelta(
                    seconds=task.retry_delay_seconds
                )
                task.status = TaskStatus.PENDING
                logger.info(
                    f"Task scheduled for retry",
                    task_id=task.id,
                    retry_count=task.failure_count,
                )
            elif execution.status == TaskStatus.COMPLETED:
                self._update_next_run_time(task)
                task.status = TaskStatus.PENDING if task.next_run_at else TaskStatus.COMPLETED
            else:
                self._update_next_run_time(task)
                task.status = TaskStatus.FAILED

            task.updated_at = datetime.now(UTC)

    def _update_next_run_time(self, task: ScheduledTask) -> None:
        """Update the next run time for a task."""
        now = datetime.now(UTC)

        if task.trigger_type == TaskTriggerType.CRON and task.cron_expression:
            cron = croniter(task.cron_expression, now)
            task.next_run_at = cron.get_next(datetime)

        elif task.trigger_type == TaskTriggerType.INTERVAL and task.interval_seconds:
            task.next_run_at = now + timedelta(seconds=task.interval_seconds)

        elif task.trigger_type == TaskTriggerType.ONE_TIME:
            task.next_run_at = None
            task.enabled = False

    # =========================================================================
    # Task Management
    # =========================================================================

    def schedule_task(self, task: ScheduledTask) -> ScheduledTask:
        """Schedule a new task."""
        if task.id in self._tasks:
            raise ValueError(f"Task with ID {task.id} already exists")

        # Calculate initial next_run_at
        self._update_next_run_time(task)
        if task.trigger_type == TaskTriggerType.ONE_TIME and task.scheduled_time:
            task.next_run_at = task.scheduled_time

        self._tasks[task.id] = task
        logger.info(
            f"Task scheduled",
            task_id=task.id,
            task_name=task.name,
            next_run=task.next_run_at,
        )

        return task

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get a task by ID."""
        return self._tasks.get(task_id)

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        organization_id: Optional[str] = None,
        task_type: Optional[str] = None,
    ) -> list[ScheduledTask]:
        """List tasks with optional filters."""
        tasks = list(self._tasks.values())

        if status:
            tasks = [t for t in tasks if t.status == status]
        if organization_id:
            tasks = [t for t in tasks if t.organization_id == organization_id]
        if task_type:
            tasks = [t for t in tasks if t.task_type == task_type]

        return tasks

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled task. No-op for already-terminal tasks."""
        task = self._tasks.get(task_id)
        if not task:
            return False

        if task.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
            return False

        task.status = TaskStatus.CANCELLED
        task.enabled = False
        task.updated_at = datetime.now(UTC)

        # Cancel if currently running
        for exec_id, async_task in list(self._current_executions.items()):
            exec_record = self._executions.get(exec_id)
            if exec_record and exec_record.task_id == task_id:
                async_task.cancel()
                del self._current_executions[exec_id]

        logger.info(f"Task cancelled", task_id=task_id)
        return True

    def pause_task(self, task_id: str) -> bool:
        """Pause a scheduled task. Only PENDING tasks can be paused."""
        task = self._tasks.get(task_id)
        if not task:
            return False

        if task.status not in (TaskStatus.PENDING,):
            return False

        task.status = TaskStatus.PAUSED
        task.updated_at = datetime.now(UTC)
        logger.info(f"Task paused", task_id=task_id)
        return True

    def resume_task(self, task_id: str) -> bool:
        """Resume a paused task."""
        task = self._tasks.get(task_id)
        if not task:
            return False

        if task.status != TaskStatus.PAUSED:
            return False

        task.status = TaskStatus.PENDING
        self._update_next_run_time(task)
        task.updated_at = datetime.now(UTC)
        logger.info(f"Task resumed", task_id=task_id)
        return True

    def trigger_task(self, task_id: str) -> bool:
        """Manually trigger a task to run now."""
        task = self._tasks.get(task_id)
        if not task:
            return False

        if task.status in (TaskStatus.CANCELLED, TaskStatus.RUNNING):
            return False

        task.next_run_at = datetime.now(UTC)
        task.status = TaskStatus.PENDING
        task.enabled = True
        logger.info(f"Task triggered manually", task_id=task_id)
        return True

    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        if task_id not in self._tasks:
            return False

        # Cancel if running
        self.cancel_task(task_id)
        del self._tasks[task_id]
        logger.info(f"Task deleted", task_id=task_id)
        return True

    def get_task_executions(
        self, task_id: str, limit: int = 10
    ) -> list[TaskExecution]:
        """Get execution history for a task."""
        executions = [
            e for e in self._executions.values() if e.task_id == task_id
        ]
        executions.sort(key=lambda e: e.started_at, reverse=True)
        return executions[:limit]

    # =========================================================================
    # Event Triggering
    # =========================================================================

    async def trigger_event(self, event_name: str, event_data: dict[str, Any]) -> int:
        """Trigger tasks based on an event."""
        triggered_count = 0

        async with self._lock:
            for task in self._tasks.values():
                if (
                    task.trigger_type == TaskTriggerType.EVENT
                    and task.event_trigger == event_name
                    and task.enabled
                ):
                    task.arguments = {**task.arguments, "event_data": event_data}
                    task.next_run_at = datetime.now(UTC)
                    task.status = TaskStatus.PENDING
                    triggered_count += 1

        if triggered_count:
            logger.info(
                f"Event triggered {triggered_count} tasks",
                event_name=event_name,
            )

        return triggered_count

    # =========================================================================
    # Built-in Handlers
    # =========================================================================

    async def _handle_dora_metrics(
        self, arguments: dict, task: ScheduledTask
    ) -> dict:
        """Handle DORA metrics collection task."""
        from app.services.mcp import get_mcp_gateway

        gateway = get_mcp_gateway()

        context = {
            "user_id": task.user_id or "system",
            "organization_id": task.organization_id,
            "roles": ["system"],
        }

        result = await gateway.invoke_tool(
            tool_name="devlake_get_dora_metrics",
            arguments={
                "time_range": arguments.get("time_range", "30d"),
                "project": arguments.get("project"),
            },
            context=context,
        )

        return {
            "success": result.get("success", False),
            "metrics": result.get("result", {}),
        }

    async def _handle_code_quality_scan(
        self, arguments: dict, task: ScheduledTask
    ) -> dict:
        """Handle code quality scan task."""
        # Placeholder - would integrate with code analysis service
        return {
            "success": True,
            "scanned_files": 0,
            "issues_found": 0,
        }

    async def _handle_report_generation(
        self, arguments: dict, task: ScheduledTask
    ) -> dict:
        """Handle report generation task."""
        # Placeholder - would generate and send reports
        return {
            "success": True,
            "report_type": arguments.get("report_type"),
            "generated_at": datetime.now(UTC).isoformat(),
        }

    async def _handle_data_sync(self, arguments: dict, task: ScheduledTask) -> dict:
        """Handle data synchronization task."""
        from app.services.mcp import get_mcp_gateway

        gateway = get_mcp_gateway()

        context = {
            "user_id": task.user_id or "system",
            "organization_id": task.organization_id,
            "roles": ["system"],
        }

        result = await gateway.invoke_tool(
            tool_name="devlake_run_pipeline",
            arguments={
                "blueprint_id": arguments.get("blueprint_id"),
            },
            context=context,
        )

        return {
            "success": result.get("success", False),
            "pipeline_result": result.get("result", {}),
        }

    async def _handle_alert_analysis(
        self, arguments: dict, task: ScheduledTask
    ) -> dict:
        """Handle alert analysis task."""
        # Placeholder - would analyze alerts and trigger follow-up
        return {
            "success": True,
            "alerts_processed": 0,
            "actions_taken": [],
        }

    async def _handle_approval_expiry(
        self, arguments: dict, task: ScheduledTask
    ) -> dict:
        """Handle expiry of pending approvals."""
        # This would be called periodically to expire old approvals
        from app.services.audit import AuditService
        from app.core.database import async_session_maker

        async with async_session_maker() as session:
            audit_service = AuditService(session)
            expired_count = await audit_service.expire_old_approvals()
            await session.commit()

        return {
            "success": True,
            "expired_count": expired_count,
        }

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_statistics(self) -> dict[str, Any]:
        """Get scheduler statistics."""
        now = datetime.now(UTC)

        total_tasks = len(self._tasks)
        enabled_tasks = sum(1 for t in self._tasks.values() if t.enabled)
        running_tasks = len(self._current_executions)

        recent_executions = [
            e for e in self._executions.values()
            if e.completed_at and (now - e.completed_at) < timedelta(hours=24)
        ]
        success_count = sum(1 for e in recent_executions if e.status == TaskStatus.COMPLETED)
        failure_count = sum(1 for e in recent_executions if e.status == TaskStatus.FAILED)

        return {
            "scheduler_running": self._running,
            "total_tasks": total_tasks,
            "enabled_tasks": enabled_tasks,
            "running_tasks": running_tasks,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "last_24h": {
                "total_executions": len(recent_executions),
                "successful": success_count,
                "failed": failure_count,
                "success_rate": (
                    success_count / len(recent_executions) * 100
                    if recent_executions else 0
                ),
            },
        }


# Global scheduler instance
_scheduler: Optional[BackgroundAgentScheduler] = None


def get_agent_scheduler() -> BackgroundAgentScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundAgentScheduler()
    return _scheduler


def reset_agent_scheduler() -> None:
    """Reset the global scheduler instance."""
    global _scheduler
    if _scheduler:
        asyncio.create_task(_scheduler.stop())
    _scheduler = None
