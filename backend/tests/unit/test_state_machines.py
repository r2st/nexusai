"""Unit tests for state machine fixes (GB043 M3)."""

import asyncio
from datetime import datetime, timedelta, UTC

import pytest

from app.services.workflow.engine import WorkflowEngine
from app.services.workflow.models import (
    StepExecutionStatus,
    Workflow,
    WorkflowExecution,
    WorkflowExecutionStatus,
    WorkflowStatus,
    WorkflowStep,
    WorkflowStepType,
    WorkflowTriggerType,
)
from app.services.agents.scheduler import (
    BackgroundAgentScheduler,
    ScheduledTask,
    TaskStatus,
    TaskTriggerType,
)


# =============================================================================
# Workflow Engine: Step Retry Tests
# =============================================================================


class TestWorkflowStepRetry:
    """Test that step retries work correctly without infinite recursion."""

    @pytest.fixture
    def engine(self):
        return WorkflowEngine()

    @pytest.mark.asyncio
    async def test_step_retry_terminates(self, engine):
        """Step with retries should eventually fail, not recurse infinitely."""
        call_count = 0

        async def failing_executor(step, context):
            nonlocal call_count
            call_count += 1
            raise ValueError("always fails")

        engine._step_executors[WorkflowStepType.API_CALL] = failing_executor

        step = WorkflowStep(
            id="test-step",
            name="Failing Step",
            type=WorkflowStepType.API_CALL,
            retry_count=2,
            retry_delay_seconds=0,
        )

        execution = WorkflowExecution(
            id="exec-1",
            workflow_id="wf-1",
            workflow_name="Test",
            workflow_version=1,
            trigger_type=WorkflowTriggerType.MANUAL,
            context={},
        )

        result = await engine._execute_step(execution, step)

        assert result.status == StepExecutionStatus.FAILED
        assert call_count == 3  # 1 initial + 2 retries
        assert result.attempt == 3
        assert "always fails" in result.error

    @pytest.mark.asyncio
    async def test_step_retry_succeeds_on_second_attempt(self, engine):
        """Step should succeed if retry works."""
        call_count = 0

        async def flaky_executor(step, context):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("temporary failure")
            return {"success": True}

        engine._step_executors[WorkflowStepType.API_CALL] = flaky_executor

        step = WorkflowStep(
            id="test-step",
            name="Flaky Step",
            type=WorkflowStepType.API_CALL,
            retry_count=3,
            retry_delay_seconds=0,
        )

        execution = WorkflowExecution(
            id="exec-1",
            workflow_id="wf-1",
            workflow_name="Test",
            workflow_version=1,
            trigger_type=WorkflowTriggerType.MANUAL,
            context={},
        )

        result = await engine._execute_step(execution, step)

        assert result.status == StepExecutionStatus.COMPLETED
        assert call_count == 2
        assert result.output_data == {"success": True}

    @pytest.mark.asyncio
    async def test_step_no_retry_when_zero(self, engine):
        """Step with retry_count=0 should fail immediately."""
        call_count = 0

        async def failing_executor(step, context):
            nonlocal call_count
            call_count += 1
            raise ValueError("no retries")

        engine._step_executors[WorkflowStepType.API_CALL] = failing_executor

        step = WorkflowStep(
            id="test-step",
            name="No Retry Step",
            type=WorkflowStepType.API_CALL,
            retry_count=0,
            retry_delay_seconds=0,
        )

        execution = WorkflowExecution(
            id="exec-1",
            workflow_id="wf-1",
            workflow_name="Test",
            workflow_version=1,
            trigger_type=WorkflowTriggerType.MANUAL,
            context={},
        )

        result = await engine._execute_step(execution, step)

        assert result.status == StepExecutionStatus.FAILED
        assert call_count == 1


# =============================================================================
# Workflow Engine: Timeout Tests
# =============================================================================


class TestWorkflowTimeout:
    """Test that workflow-level timeout is enforced."""

    @pytest.fixture
    def engine(self):
        return WorkflowEngine()

    @pytest.mark.asyncio
    async def test_workflow_timeout_sets_timed_out_status(self, engine):
        """Workflow exceeding timeout should get TIMED_OUT status."""
        async def slow_executor(step, context):
            await asyncio.sleep(10)
            return {"done": True}

        engine._step_executors[WorkflowStepType.WAIT] = slow_executor

        workflow = Workflow(
            id="wf-timeout",
            name="Slow Workflow",
            organization_id="org-1",
            status=WorkflowStatus.ACTIVE,
            steps=[
                WorkflowStep(
                    id="slow-step",
                    name="Slow",
                    type=WorkflowStepType.WAIT,
                    timeout_seconds=30,
                ),
            ],
            entry_step_id="slow-step",
            timeout_seconds=1,
        )

        execution = WorkflowExecution(
            id="exec-timeout",
            workflow_id=workflow.id,
            workflow_name=workflow.name,
            workflow_version=workflow.version,
            trigger_type=WorkflowTriggerType.MANUAL,
        )
        engine._executions[execution.id] = execution

        await engine._run_execution(execution, workflow)

        assert execution.status == WorkflowExecutionStatus.TIMED_OUT
        assert execution.error is not None
        assert "timed out" in execution.error.lower()
        assert execution.completed_at is not None


# =============================================================================
# Scheduler: Retry Tests
# =============================================================================


class TestSchedulerRetry:
    """Test scheduler task retry logic."""

    @pytest.fixture
    def scheduler(self):
        return BackgroundAgentScheduler()

    @pytest.mark.asyncio
    async def test_one_time_task_can_retry(self, scheduler):
        """Failed ONE_TIME task should stay enabled for retry."""
        async def failing_handler(arguments, task=None):
            raise ValueError("one-time failure")

        scheduler.register_handler("test_task", failing_handler)

        task = ScheduledTask(
            id="one-time-1",
            name="One Time Task",
            description="Test",
            task_type="test_task",
            trigger_type=TaskTriggerType.ONE_TIME,
            max_retries=3,
            retry_delay_seconds=0,
            timeout_seconds=5,
            scheduled_time=datetime.now(UTC),
        )
        task.next_run_at = datetime.now(UTC)
        scheduler._tasks[task.id] = task

        await scheduler._execute_task(task)

        assert task.status == TaskStatus.PENDING
        assert task.enabled is True
        assert task.next_run_at is not None

    @pytest.mark.asyncio
    async def test_cron_task_retry_timing_not_overwritten(self, scheduler):
        """Failed CRON task retry should use retry delay, not cron schedule."""
        async def failing_handler(arguments, task=None):
            raise ValueError("cron failure")

        scheduler.register_handler("test_task", failing_handler)

        task = ScheduledTask(
            id="cron-1",
            name="Cron Task",
            description="Test",
            task_type="test_task",
            trigger_type=TaskTriggerType.CRON,
            cron_expression="0 0 * * *",
            max_retries=3,
            retry_delay_seconds=120,
            timeout_seconds=5,
        )
        task.next_run_at = datetime.now(UTC)
        scheduler._tasks[task.id] = task

        before = datetime.now(UTC)
        await scheduler._execute_task(task)

        assert task.status == TaskStatus.PENDING
        expected_retry = before + timedelta(seconds=120)
        assert task.next_run_at is not None
        assert abs((task.next_run_at - expected_retry).total_seconds()) < 5

    @pytest.mark.asyncio
    async def test_successful_recurring_task_resets_to_pending(self, scheduler):
        """Successful recurring task should have PENDING status for next run."""
        async def success_handler(arguments, task=None):
            return {"ok": True}

        scheduler.register_handler("test_task", success_handler)

        task = ScheduledTask(
            id="interval-1",
            name="Interval Task",
            description="Test",
            task_type="test_task",
            trigger_type=TaskTriggerType.INTERVAL,
            interval_seconds=60,
            timeout_seconds=5,
        )
        task.next_run_at = datetime.now(UTC)
        scheduler._tasks[task.id] = task

        await scheduler._execute_task(task)

        assert task.status == TaskStatus.PENDING
        assert task.next_run_at is not None
        assert task.failure_count == 0


# =============================================================================
# Scheduler: trigger_task Tests
# =============================================================================


class TestSchedulerTriggerTask:
    """Test trigger_task state checks."""

    def test_trigger_cancelled_task_returns_false(self):
        """Cannot manually trigger a cancelled task."""
        scheduler = BackgroundAgentScheduler()

        task = ScheduledTask(
            id="cancelled-1",
            name="Cancelled Task",
            description="Test",
            task_type="test_task",
            trigger_type=TaskTriggerType.MANUAL,
            status=TaskStatus.CANCELLED,
            enabled=False,
        )
        scheduler._tasks[task.id] = task

        result = scheduler.trigger_task(task.id)

        assert result is False
        assert task.status == TaskStatus.CANCELLED

    def test_trigger_paused_task_succeeds(self):
        """Can manually trigger a paused task."""
        scheduler = BackgroundAgentScheduler()

        task = ScheduledTask(
            id="paused-1",
            name="Paused Task",
            description="Test",
            task_type="test_task",
            trigger_type=TaskTriggerType.MANUAL,
            status=TaskStatus.PAUSED,
        )
        scheduler._tasks[task.id] = task

        result = scheduler.trigger_task(task.id)

        assert result is True
        assert task.status == TaskStatus.PENDING
        assert task.enabled is True

    def test_trigger_nonexistent_task_returns_false(self):
        """Triggering non-existent task returns False."""
        scheduler = BackgroundAgentScheduler()
        assert scheduler.trigger_task("does-not-exist") is False
