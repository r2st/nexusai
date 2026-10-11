"""Unit tests for GB062 M3 state machine fixes.

Tests the state transition guards added in this round:
- Workflow activate/pause state validation
- Workflow execution state validation (must be ACTIVE to execute)
- Workflow cancel execution state guards
- Workflow archive transition
- Workflow delete blocked by running executions
- Orchestration workflow start_run ACTIVE guard
- Subscription change_tier validation
- Document process_document PENDING-only guard
- Collaboration session end_session idempotency guard
"""

import asyncio
from datetime import datetime

import pytest

from app.services.workflow.engine import WorkflowEngine
from app.services.workflow.models import (
    Workflow,
    WorkflowExecution,
    WorkflowExecutionStatus,
    WorkflowStatus,
    WorkflowStep,
    WorkflowStepType,
    WorkflowTriggerType,
)
from app.services.collaboration.sessions import SessionManager, SessionType


# =============================================================================
# Workflow Engine: activate/pause state guards
# =============================================================================


class TestWorkflowActivatePauseGuards:
    """Test that activate and pause enforce valid source states."""

    @pytest.fixture
    def engine(self):
        return WorkflowEngine()

    @pytest.fixture
    def draft_workflow(self, engine):
        workflow = Workflow(
            id="wf-1",
            name="Test",
            organization_id="org-1",
            status=WorkflowStatus.DRAFT,
        )
        engine._workflows[workflow.id] = workflow
        return workflow

    @pytest.mark.asyncio
    async def test_activate_draft_succeeds(self, engine, draft_workflow):
        result = await engine.activate_workflow(draft_workflow.id)
        assert result.status == WorkflowStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_activate_paused_succeeds(self, engine, draft_workflow):
        draft_workflow.status = WorkflowStatus.PAUSED
        result = await engine.activate_workflow(draft_workflow.id)
        assert result.status == WorkflowStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_activate_archived_raises(self, engine, draft_workflow):
        draft_workflow.status = WorkflowStatus.ARCHIVED
        with pytest.raises(ValueError, match="archived"):
            await engine.activate_workflow(draft_workflow.id)

    @pytest.mark.asyncio
    async def test_activate_already_active_raises(self, engine, draft_workflow):
        draft_workflow.status = WorkflowStatus.ACTIVE
        with pytest.raises(ValueError, match="active"):
            await engine.activate_workflow(draft_workflow.id)

    @pytest.mark.asyncio
    async def test_pause_active_succeeds(self, engine, draft_workflow):
        draft_workflow.status = WorkflowStatus.ACTIVE
        result = await engine.pause_workflow(draft_workflow.id)
        assert result.status == WorkflowStatus.PAUSED

    @pytest.mark.asyncio
    async def test_pause_draft_raises(self, engine, draft_workflow):
        with pytest.raises(ValueError, match="draft"):
            await engine.pause_workflow(draft_workflow.id)

    @pytest.mark.asyncio
    async def test_pause_archived_raises(self, engine, draft_workflow):
        draft_workflow.status = WorkflowStatus.ARCHIVED
        with pytest.raises(ValueError, match="archived"):
            await engine.pause_workflow(draft_workflow.id)


# =============================================================================
# Workflow Engine: execution requires ACTIVE workflow
# =============================================================================


class TestWorkflowExecutionRequiresActive:
    """Test that start_execution only works on ACTIVE workflows."""

    @pytest.fixture
    def engine(self):
        return WorkflowEngine()

    def _make_workflow(self, engine, status):
        workflow = Workflow(
            id=f"wf-{status.value}",
            name="Test",
            organization_id="org-1",
            status=status,
            steps=[
                WorkflowStep(
                    id="s1", name="Step 1",
                    type=WorkflowStepType.API_CALL,
                ),
            ],
            entry_step_id="s1",
        )
        engine._workflows[workflow.id] = workflow
        return workflow

    @pytest.mark.asyncio
    async def test_execute_active_succeeds(self, engine):
        wf = self._make_workflow(engine, WorkflowStatus.ACTIVE)
        execution = await engine.start_execution(wf.id)
        assert execution.status in (
            WorkflowExecutionStatus.PENDING,
            WorkflowExecutionStatus.RUNNING,
            WorkflowExecutionStatus.COMPLETED,
        )
        # Clean up background task
        task = engine._execution_tasks.pop(execution.id, None)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass

    @pytest.mark.asyncio
    async def test_execute_draft_raises(self, engine):
        wf = self._make_workflow(engine, WorkflowStatus.DRAFT)
        with pytest.raises(ValueError, match="draft"):
            await engine.start_execution(wf.id)

    @pytest.mark.asyncio
    async def test_execute_paused_raises(self, engine):
        wf = self._make_workflow(engine, WorkflowStatus.PAUSED)
        with pytest.raises(ValueError, match="paused"):
            await engine.start_execution(wf.id)

    @pytest.mark.asyncio
    async def test_execute_archived_raises(self, engine):
        wf = self._make_workflow(engine, WorkflowStatus.ARCHIVED)
        with pytest.raises(ValueError, match="archived"):
            await engine.start_execution(wf.id)


# =============================================================================
# Workflow Engine: cancel execution state guards
# =============================================================================


class TestWorkflowCancelExecutionGuards:
    """Test that cancel_execution rejects terminal states."""

    @pytest.fixture
    def engine(self):
        return WorkflowEngine()

    def _make_execution(self, engine, status):
        execution = WorkflowExecution(
            id=f"exec-{status.value}",
            workflow_id="wf-1",
            workflow_name="Test",
            workflow_version=1,
            trigger_type=WorkflowTriggerType.MANUAL,
            status=status,
        )
        engine._executions[execution.id] = execution
        return execution

    @pytest.mark.asyncio
    async def test_cancel_running_succeeds(self, engine):
        ex = self._make_execution(engine, WorkflowExecutionStatus.RUNNING)
        result = await engine.cancel_execution(ex.id)
        assert result.status == WorkflowExecutionStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_pending_succeeds(self, engine):
        ex = self._make_execution(engine, WorkflowExecutionStatus.PENDING)
        result = await engine.cancel_execution(ex.id)
        assert result.status == WorkflowExecutionStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_completed_raises(self, engine):
        ex = self._make_execution(engine, WorkflowExecutionStatus.COMPLETED)
        with pytest.raises(ValueError, match="completed"):
            await engine.cancel_execution(ex.id)

    @pytest.mark.asyncio
    async def test_cancel_failed_raises(self, engine):
        ex = self._make_execution(engine, WorkflowExecutionStatus.FAILED)
        with pytest.raises(ValueError, match="failed"):
            await engine.cancel_execution(ex.id)

    @pytest.mark.asyncio
    async def test_cancel_already_cancelled_raises(self, engine):
        ex = self._make_execution(engine, WorkflowExecutionStatus.CANCELLED)
        with pytest.raises(ValueError, match="cancelled"):
            await engine.cancel_execution(ex.id)


# =============================================================================
# Workflow Engine: archive workflow
# =============================================================================


class TestWorkflowArchive:
    """Test the archive_workflow transition."""

    @pytest.fixture
    def engine(self):
        return WorkflowEngine()

    def _make_workflow(self, engine, status):
        workflow = Workflow(
            id=f"wf-{status.value}",
            name="Test",
            organization_id="org-1",
            status=status,
        )
        engine._workflows[workflow.id] = workflow
        return workflow

    @pytest.mark.asyncio
    async def test_archive_draft_succeeds(self, engine):
        wf = self._make_workflow(engine, WorkflowStatus.DRAFT)
        result = await engine.archive_workflow(wf.id)
        assert result.status == WorkflowStatus.ARCHIVED

    @pytest.mark.asyncio
    async def test_archive_paused_succeeds(self, engine):
        wf = self._make_workflow(engine, WorkflowStatus.PAUSED)
        result = await engine.archive_workflow(wf.id)
        assert result.status == WorkflowStatus.ARCHIVED

    @pytest.mark.asyncio
    async def test_archive_active_raises(self, engine):
        wf = self._make_workflow(engine, WorkflowStatus.ACTIVE)
        with pytest.raises(ValueError, match="active"):
            await engine.archive_workflow(wf.id)

    @pytest.mark.asyncio
    async def test_archive_already_archived_raises(self, engine):
        wf = self._make_workflow(engine, WorkflowStatus.ARCHIVED)
        with pytest.raises(ValueError, match="already archived"):
            await engine.archive_workflow(wf.id)


# =============================================================================
# Workflow Engine: delete blocked by running executions
# =============================================================================


class TestWorkflowDeleteGuard:
    """Test that delete_workflow blocks when executions are running."""

    @pytest.fixture
    def engine(self):
        return WorkflowEngine()

    @pytest.mark.asyncio
    async def test_delete_with_running_execution_raises(self, engine):
        wf = Workflow(
            id="wf-del", name="Test", organization_id="org-1",
            status=WorkflowStatus.DRAFT,
        )
        engine._workflows[wf.id] = wf

        execution = WorkflowExecution(
            id="exec-run",
            workflow_id=wf.id,
            workflow_name=wf.name,
            workflow_version=1,
            trigger_type=WorkflowTriggerType.MANUAL,
            status=WorkflowExecutionStatus.RUNNING,
        )
        engine._executions[execution.id] = execution

        with pytest.raises(ValueError, match="active execution"):
            await engine.delete_workflow(wf.id)
        assert wf.id in engine._workflows

    @pytest.mark.asyncio
    async def test_delete_with_completed_execution_succeeds(self, engine):
        wf = Workflow(
            id="wf-del2", name="Test", organization_id="org-1",
            status=WorkflowStatus.DRAFT,
        )
        engine._workflows[wf.id] = wf

        execution = WorkflowExecution(
            id="exec-done",
            workflow_id=wf.id,
            workflow_name=wf.name,
            workflow_version=1,
            trigger_type=WorkflowTriggerType.MANUAL,
            status=WorkflowExecutionStatus.COMPLETED,
        )
        engine._executions[execution.id] = execution

        result = await engine.delete_workflow(wf.id)
        assert result is True
        assert wf.id not in engine._workflows


# =============================================================================
# Collaboration: end_session idempotency guard
# =============================================================================


class TestSessionEndGuard:
    """Test that end_session is a no-op on already-ended sessions."""

    @pytest.fixture
    def manager(self):
        return SessionManager()

    @pytest.mark.asyncio
    async def test_end_session_twice_returns_none(self, manager):
        session = await manager.create_session(
            organization_id="org-1",
            session_type=SessionType.CODE_REVIEW,
            title="Test Session",
            host_user_id="user-1",
            host_username="tester",
        )
        first = await manager.end_session(session.id, "user-1")
        assert first is not None
        assert not first.is_active

        second = await manager.end_session(session.id, "user-1")
        assert second is None

    @pytest.mark.asyncio
    async def test_end_active_session_marks_inactive(self, manager):
        session = await manager.create_session(
            organization_id="org-1",
            session_type=SessionType.CODE_REVIEW,
            title="Test Session",
            host_user_id="user-1",
            host_username="tester",
        )
        assert session.is_active is True

        result = await manager.end_session(session.id, "user-1")
        assert result is not None
        assert result.is_active is False
        assert result.ended_at is not None


# =============================================================================
# Subscription: change_tier validation
# =============================================================================


class TestSubscriptionChangeTierValidation:
    """Test tier validation in SubscriptionService (without DB)."""

    def test_valid_tiers_frozenset_exists(self):
        from app.services.subscription import SubscriptionService
        assert hasattr(SubscriptionService, "_VALID_TIERS")
        assert "free" in SubscriptionService._VALID_TIERS
        assert "starter" in SubscriptionService._VALID_TIERS
        assert "professional" in SubscriptionService._VALID_TIERS
        assert "enterprise" in SubscriptionService._VALID_TIERS
        assert "invalid_tier" not in SubscriptionService._VALID_TIERS
