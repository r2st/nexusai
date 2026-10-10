"""Unit tests for GB047 M3 state machine verification.

Tests state transition guards, side effects, and idempotency across:
- AgentState (orchestration state)
- BackgroundAgentScheduler (task lifecycle)
- MCP Gateway CircuitBreaker (circuit state tracking)
- DocumentService (processing pipeline)
"""

import pytest

from app.services.agents.orchestration.state import AgentState, StateStatus
from app.services.agents.scheduler import (
    BackgroundAgentScheduler,
    ScheduledTask,
    TaskStatus,
    TaskTriggerType,
)


# =============================================================================
# AgentState: Terminal state guards
# =============================================================================


class TestAgentStateTerminalGuards:
    """Verify that complete() and fail() are no-ops on terminal states."""

    def test_complete_on_completed_is_noop(self):
        state = AgentState()
        state.status = StateStatus.RUNNING
        state.complete({"result": "first"})
        version_after_first = state.checkpoint_version

        state.complete({"result": "second"})

        assert state.output_data == {"result": "first"}
        assert state.checkpoint_version == version_after_first

    def test_complete_on_failed_is_noop(self):
        state = AgentState()
        state.status = StateStatus.RUNNING
        state.fail("something broke")
        assert state.status == StateStatus.FAILED

        state.complete({"result": "override attempt"})

        assert state.status == StateStatus.FAILED
        assert state.output_data == {}

    def test_complete_on_cancelled_is_noop(self):
        state = AgentState()
        state.status = StateStatus.CANCELLED

        state.complete({"result": "override attempt"})

        assert state.status == StateStatus.CANCELLED

    def test_fail_on_completed_is_noop(self):
        state = AgentState()
        state.status = StateStatus.RUNNING
        state.complete({"result": "done"})
        error_count = len(state.errors)

        state.fail("late error")

        assert state.status == StateStatus.COMPLETED
        assert len(state.errors) == error_count

    def test_fail_on_failed_is_noop(self):
        state = AgentState()
        state.status = StateStatus.RUNNING
        state.fail("first error")
        error_count = len(state.errors)

        state.fail("second error")

        assert len(state.errors) == error_count

    def test_fail_on_cancelled_is_noop(self):
        state = AgentState()
        state.status = StateStatus.CANCELLED

        state.fail("late error")

        assert state.status == StateStatus.CANCELLED

    def test_complete_from_running_works(self):
        state = AgentState()
        state.status = StateStatus.RUNNING

        state.complete({"result": "ok"})

        assert state.status == StateStatus.COMPLETED
        assert state.output_data == {"result": "ok"}
        assert state.completed_at is not None

    def test_fail_from_running_works(self):
        state = AgentState()
        state.status = StateStatus.RUNNING

        state.fail("oops")

        assert state.status == StateStatus.FAILED
        assert state.completed_at is not None
        assert len(state.errors) == 1


# =============================================================================
# AgentState: Rejection sets completed_at
# =============================================================================


class TestAgentStateApprovalRejection:
    """Verify that rejected approval sets completed_at."""

    def test_rejection_sets_completed_at(self):
        state = AgentState()
        state.status = StateStatus.RUNNING
        state.request_approval("approval-1", {"action": "deploy"})
        assert state.status == StateStatus.WAITING

        state.record_approval(approved=False, approved_by="admin")

        assert state.status == StateStatus.CANCELLED
        assert state.completed_at is not None

    def test_approval_does_not_set_completed_at(self):
        state = AgentState()
        state.status = StateStatus.RUNNING
        state.request_approval("approval-1", {"action": "deploy"})

        state.record_approval(approved=True, approved_by="admin")

        assert state.status == StateStatus.RUNNING
        assert state.completed_at is None


# =============================================================================
# Scheduler: pause_task guard
# =============================================================================


class TestSchedulerPauseGuard:
    """Verify that only PENDING tasks can be paused."""

    def _make_scheduler_with_task(self, status: TaskStatus) -> tuple:
        scheduler = BackgroundAgentScheduler()
        task = ScheduledTask(
            id="test-1",
            name="Test",
            description="Test",
            task_type="test",
            trigger_type=TaskTriggerType.MANUAL,
            status=status,
        )
        scheduler._tasks[task.id] = task
        return scheduler, task

    def test_pause_pending_succeeds(self):
        scheduler, task = self._make_scheduler_with_task(TaskStatus.PENDING)
        assert scheduler.pause_task(task.id) is True
        assert task.status == TaskStatus.PAUSED

    def test_pause_completed_fails(self):
        scheduler, task = self._make_scheduler_with_task(TaskStatus.COMPLETED)
        assert scheduler.pause_task(task.id) is False
        assert task.status == TaskStatus.COMPLETED

    def test_pause_failed_fails(self):
        scheduler, task = self._make_scheduler_with_task(TaskStatus.FAILED)
        assert scheduler.pause_task(task.id) is False
        assert task.status == TaskStatus.FAILED

    def test_pause_cancelled_fails(self):
        scheduler, task = self._make_scheduler_with_task(TaskStatus.CANCELLED)
        assert scheduler.pause_task(task.id) is False
        assert task.status == TaskStatus.CANCELLED

    def test_pause_running_fails(self):
        scheduler, task = self._make_scheduler_with_task(TaskStatus.RUNNING)
        assert scheduler.pause_task(task.id) is False
        assert task.status == TaskStatus.RUNNING


# =============================================================================
# Scheduler: cancel_task guard
# =============================================================================


class TestSchedulerCancelGuard:
    """Verify that terminal tasks cannot be cancelled."""

    def _make_scheduler_with_task(self, status: TaskStatus) -> tuple:
        scheduler = BackgroundAgentScheduler()
        task = ScheduledTask(
            id="test-1",
            name="Test",
            description="Test",
            task_type="test",
            trigger_type=TaskTriggerType.MANUAL,
            status=status,
        )
        scheduler._tasks[task.id] = task
        return scheduler, task

    def test_cancel_completed_fails(self):
        scheduler, task = self._make_scheduler_with_task(TaskStatus.COMPLETED)
        assert scheduler.cancel_task(task.id) is False
        assert task.status == TaskStatus.COMPLETED

    def test_cancel_already_cancelled_fails(self):
        scheduler, task = self._make_scheduler_with_task(TaskStatus.CANCELLED)
        assert scheduler.cancel_task(task.id) is False

    def test_cancel_pending_succeeds(self):
        scheduler, task = self._make_scheduler_with_task(TaskStatus.PENDING)
        assert scheduler.cancel_task(task.id) is True
        assert task.status == TaskStatus.CANCELLED

    def test_cancel_paused_succeeds(self):
        scheduler, task = self._make_scheduler_with_task(TaskStatus.PAUSED)
        assert scheduler.cancel_task(task.id) is True
        assert task.status == TaskStatus.CANCELLED


# =============================================================================
# Scheduler: trigger_task guard
# =============================================================================


class TestSchedulerTriggerGuard:
    """Verify that running tasks cannot be manually triggered."""

    def test_trigger_running_task_fails(self):
        scheduler = BackgroundAgentScheduler()
        task = ScheduledTask(
            id="test-1",
            name="Test",
            description="Test",
            task_type="test",
            trigger_type=TaskTriggerType.MANUAL,
            status=TaskStatus.RUNNING,
        )
        scheduler._tasks[task.id] = task

        assert scheduler.trigger_task(task.id) is False
        assert task.status == TaskStatus.RUNNING

    def test_trigger_completed_task_succeeds(self):
        scheduler = BackgroundAgentScheduler()
        task = ScheduledTask(
            id="test-1",
            name="Test",
            description="Test",
            task_type="test",
            trigger_type=TaskTriggerType.MANUAL,
            status=TaskStatus.COMPLETED,
            enabled=False,
        )
        scheduler._tasks[task.id] = task

        assert scheduler.trigger_task(task.id) is True
        assert task.status == TaskStatus.PENDING
        assert task.enabled is True


# =============================================================================
# MCP Gateway CircuitBreaker: half_open_calls tracking
# =============================================================================


class TestMCPCircuitBreakerHalfOpen:
    """Verify circuit breaker tracks half-open calls properly.

    Reads the gateway source directly to verify the dataclass has
    the half_open_calls field, avoiding the heavy import chain.
    """

    def test_gateway_circuit_breaker_has_half_open_calls_field(self):
        """The CircuitBreaker dataclass must have a half_open_calls field."""
        import ast
        from pathlib import Path

        gateway_path = Path(__file__).resolve().parents[2] / "app" / "services" / "mcp" / "gateway.py"
        tree = ast.parse(gateway_path.read_text())

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "CircuitBreaker":
                field_names = []
                for item in node.body:
                    if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                        field_names.append(item.target.id)
                assert "half_open_calls" in field_names, (
                    f"CircuitBreaker missing half_open_calls field. Fields: {field_names}"
                )
                assert "success_count" in field_names
                return

        pytest.fail("CircuitBreaker class not found in gateway.py")

    def test_check_circuit_breaker_uses_half_open_calls_not_success_count(self):
        """_check_circuit_breaker should compare half_open_calls, not success_count."""
        from pathlib import Path

        gateway_path = Path(__file__).resolve().parents[2] / "app" / "services" / "mcp" / "gateway.py"
        source = gateway_path.read_text()

        in_method = False
        method_body = []
        for line in source.splitlines():
            if "_check_circuit_breaker" in line and "def " in line:
                in_method = True
            elif in_method and line.strip().startswith("def "):
                break
            elif in_method:
                method_body.append(line)

        body_text = "\n".join(method_body)
        assert "half_open_calls" in body_text, (
            "_check_circuit_breaker should use cb.half_open_calls for half-open gating"
        )
        assert "success_count >= cb.half_open_max_calls" not in body_text, (
            "_check_circuit_breaker should NOT use success_count for gating probes"
        )

    def test_record_circuit_result_increments_half_open_calls(self):
        """_record_circuit_result should increment half_open_calls on success."""
        from pathlib import Path

        gateway_path = Path(__file__).resolve().parents[2] / "app" / "services" / "mcp" / "gateway.py"
        source = gateway_path.read_text()

        in_method = False
        found_increment = False
        for line in source.splitlines():
            if "_record_circuit_result" in line and "def " in line:
                in_method = True
            elif in_method and line.strip().startswith("def "):
                break
            elif in_method and "half_open_calls += 1" in line:
                found_increment = True

        assert found_increment, (
            "_record_circuit_result should increment half_open_calls"
        )
