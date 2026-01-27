"""Workflow Automation Engine."""

import asyncio
import logging
import re
import uuid
from datetime import datetime
from typing import Any, Callable

from app.services.workflow.models import (
    StepExecution,
    StepExecutionStatus,
    Workflow,
    WorkflowCondition,
    WorkflowExecution,
    WorkflowExecutionStatus,
    WorkflowStatus,
    WorkflowStep,
    WorkflowStepType,
    WorkflowTrigger,
    WorkflowTriggerType,
    WORKFLOW_TEMPLATES,
)

logger = logging.getLogger(__name__)

# Singleton instance
_workflow_engine: "WorkflowEngine | None" = None


class WorkflowEngine:
    """Engine for executing automated workflows.

    Handles:
    - Workflow definition management
    - Trigger registration and matching
    - Step execution and orchestration
    - Context and variable management
    - Error handling and retries
    """

    def __init__(self):
        # Storage (replace with database in production)
        self._workflows: dict[str, Workflow] = {}
        self._executions: dict[str, WorkflowExecution] = {}

        # Step executors
        self._step_executors: dict[WorkflowStepType, Callable] = {}
        self._register_default_executors()

        # Trigger handlers
        self._trigger_handlers: dict[str, list[str]] = {}  # trigger_key -> workflow_ids

    def _register_default_executors(self) -> None:
        """Register default step executors."""
        self._step_executors[WorkflowStepType.NOTIFICATION] = self._execute_notification
        self._step_executors[WorkflowStepType.WEBHOOK] = self._execute_webhook
        self._step_executors[WorkflowStepType.API_CALL] = self._execute_api_call
        self._step_executors[WorkflowStepType.CONDITION] = self._execute_condition
        self._step_executors[WorkflowStepType.WAIT] = self._execute_wait
        self._step_executors[WorkflowStepType.TRANSFORM] = self._execute_transform
        self._step_executors[WorkflowStepType.CODE_ANALYSIS] = self._execute_code_analysis
        self._step_executors[WorkflowStepType.SLACK_MESSAGE] = self._execute_slack_message
        self._step_executors[WorkflowStepType.GITHUB_COMMENT] = self._execute_github_comment
        self._step_executors[WorkflowStepType.JIRA_CREATE] = self._execute_jira_create

    # --- Workflow Management ---

    async def create_workflow(
        self,
        name: str,
        organization_id: str,
        description: str | None = None,
        triggers: list[dict[str, Any]] | None = None,
        steps: list[dict[str, Any]] | None = None,
        created_by: str | None = None,
    ) -> Workflow:
        """Create a new workflow."""
        workflow_id = str(uuid.uuid4())

        # Build triggers
        workflow_triggers = []
        if triggers:
            for t in triggers:
                trigger = WorkflowTrigger(
                    id=str(uuid.uuid4()),
                    type=WorkflowTriggerType(t.get("type", "manual")),
                    enabled=t.get("enabled", True),
                    filters=t.get("filters", {}),
                    schedule=t.get("schedule"),
                )
                workflow_triggers.append(trigger)

        # Build steps
        workflow_steps = []
        entry_step_id = None
        if steps:
            for i, s in enumerate(steps):
                step = WorkflowStep(
                    id=s.get("id", str(uuid.uuid4())),
                    name=s.get("name", f"Step {i + 1}"),
                    type=WorkflowStepType(s.get("type", "api_call")),
                    description=s.get("description"),
                    config=s.get("config", {}),
                    conditions=[
                        WorkflowCondition(**c) for c in s.get("conditions", [])
                    ],
                    on_success=s.get("on_success"),
                    on_failure=s.get("on_failure"),
                    retry_count=s.get("retry_count", 0),
                    timeout_seconds=s.get("timeout_seconds", 300),
                )
                workflow_steps.append(step)
                if i == 0:
                    entry_step_id = step.id

        workflow = Workflow(
            id=workflow_id,
            name=name,
            description=description,
            organization_id=organization_id,
            triggers=workflow_triggers,
            steps=workflow_steps,
            entry_step_id=entry_step_id,
            created_by=created_by,
        )

        self._workflows[workflow_id] = workflow

        # Register triggers
        await self._register_workflow_triggers(workflow)

        logger.info(f"Workflow created: {workflow_id} name={name}")
        return workflow

    async def create_from_template(
        self,
        template_name: str,
        organization_id: str,
        created_by: str | None = None,
        overrides: dict[str, Any] | None = None,
    ) -> Workflow:
        """Create a workflow from a template."""
        template = WORKFLOW_TEMPLATES.get(template_name)
        if not template:
            raise ValueError(f"Template not found: {template_name}")

        config = {**template}
        if overrides:
            config.update(overrides)

        return await self.create_workflow(
            name=config.get("name", template_name),
            description=config.get("description"),
            organization_id=organization_id,
            triggers=config.get("triggers"),
            steps=config.get("steps"),
            created_by=created_by,
        )

    async def get_workflow(self, workflow_id: str) -> Workflow | None:
        """Get a workflow by ID."""
        return self._workflows.get(workflow_id)

    async def list_workflows(
        self,
        organization_id: str | None = None,
        status: WorkflowStatus | None = None,
    ) -> list[Workflow]:
        """List workflows with optional filters."""
        workflows = list(self._workflows.values())

        if organization_id:
            workflows = [w for w in workflows if w.organization_id == organization_id]
        if status:
            workflows = [w for w in workflows if w.status == status]

        return sorted(workflows, key=lambda w: w.created_at, reverse=True)

    async def activate_workflow(self, workflow_id: str) -> Workflow | None:
        """Activate a workflow."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return None

        workflow.status = WorkflowStatus.ACTIVE
        workflow.updated_at = datetime.utcnow()

        await self._register_workflow_triggers(workflow)
        return workflow

    async def pause_workflow(self, workflow_id: str) -> Workflow | None:
        """Pause a workflow."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return None

        workflow.status = WorkflowStatus.PAUSED
        workflow.updated_at = datetime.utcnow()

        await self._unregister_workflow_triggers(workflow)
        return workflow

    async def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return False

        await self._unregister_workflow_triggers(workflow)
        del self._workflows[workflow_id]
        return True

    # --- Trigger Management ---

    async def _register_workflow_triggers(self, workflow: Workflow) -> None:
        """Register workflow triggers."""
        if workflow.status != WorkflowStatus.ACTIVE:
            return

        for trigger in workflow.triggers:
            if not trigger.enabled:
                continue

            trigger_key = self._get_trigger_key(trigger)
            if trigger_key not in self._trigger_handlers:
                self._trigger_handlers[trigger_key] = []
            if workflow.id not in self._trigger_handlers[trigger_key]:
                self._trigger_handlers[trigger_key].append(workflow.id)

    async def _unregister_workflow_triggers(self, workflow: Workflow) -> None:
        """Unregister workflow triggers."""
        for trigger_key, workflow_ids in self._trigger_handlers.items():
            if workflow.id in workflow_ids:
                workflow_ids.remove(workflow.id)

    def _get_trigger_key(self, trigger: WorkflowTrigger) -> str:
        """Generate a key for trigger matching."""
        return f"{trigger.type.value}"

    async def handle_trigger(
        self,
        trigger_type: WorkflowTriggerType,
        event_data: dict[str, Any],
        triggered_by: str | None = None,
    ) -> list[WorkflowExecution]:
        """Handle an incoming trigger and start matching workflows."""
        trigger_key = trigger_type.value
        workflow_ids = self._trigger_handlers.get(trigger_key, [])

        executions = []
        for workflow_id in workflow_ids:
            workflow = self._workflows.get(workflow_id)
            if not workflow or workflow.status != WorkflowStatus.ACTIVE:
                continue

            # Find matching trigger
            matching_trigger = None
            for trigger in workflow.triggers:
                if trigger.type == trigger_type and trigger.enabled:
                    if self._matches_filters(trigger.filters, event_data):
                        matching_trigger = trigger
                        break

            if matching_trigger:
                execution = await self.start_execution(
                    workflow_id=workflow_id,
                    trigger_type=trigger_type,
                    trigger_id=matching_trigger.id,
                    input_data=event_data,
                    triggered_by=triggered_by,
                )
                executions.append(execution)

        return executions

    def _matches_filters(self, filters: dict[str, Any], data: dict[str, Any]) -> bool:
        """Check if data matches trigger filters."""
        if not filters:
            return True

        for key, value in filters.items():
            data_value = self._get_nested_value(data, key)
            if data_value != value:
                return False

        return True

    # --- Execution ---

    async def start_execution(
        self,
        workflow_id: str,
        trigger_type: WorkflowTriggerType = WorkflowTriggerType.MANUAL,
        trigger_id: str | None = None,
        input_data: dict[str, Any] | None = None,
        triggered_by: str | None = None,
    ) -> WorkflowExecution:
        """Start a workflow execution."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")

        execution = WorkflowExecution(
            id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            workflow_name=workflow.name,
            workflow_version=workflow.version,
            trigger_type=trigger_type,
            trigger_id=trigger_id,
            input_data=input_data or {},
            context={"input": input_data or {}},
            triggered_by=triggered_by,
        )

        self._executions[execution.id] = execution

        # Start execution in background
        asyncio.create_task(self._run_execution(execution, workflow))

        return execution

    async def _run_execution(
        self,
        execution: WorkflowExecution,
        workflow: Workflow,
    ) -> None:
        """Run a workflow execution."""
        execution.status = WorkflowExecutionStatus.RUNNING
        execution.started_at = datetime.utcnow()

        try:
            # Build step map
            step_map = {step.id: step for step in workflow.steps}

            # Start from entry step
            current_step_id = workflow.entry_step_id
            while current_step_id:
                step = step_map.get(current_step_id)
                if not step:
                    break

                execution.current_step_id = current_step_id

                # Execute step
                step_result = await self._execute_step(execution, step)
                execution.step_executions.append(step_result)

                # Determine next step
                if step_result.status == StepExecutionStatus.COMPLETED:
                    current_step_id = step.on_success
                elif step_result.status == StepExecutionStatus.FAILED:
                    if step.on_failure:
                        current_step_id = step.on_failure
                    else:
                        raise Exception(f"Step failed: {step.name}")
                elif step_result.status == StepExecutionStatus.SKIPPED:
                    current_step_id = step.on_skip or step.on_success
                else:
                    break

            # Mark completed
            execution.status = WorkflowExecutionStatus.COMPLETED
            execution.completed_at = datetime.utcnow()
            execution.duration_ms = int(
                (execution.completed_at - execution.started_at).total_seconds() * 1000
            )

        except Exception as e:
            logger.error(f"Workflow execution failed: {execution.id} error={e}")
            execution.status = WorkflowExecutionStatus.FAILED
            execution.error = str(e)
            execution.completed_at = datetime.utcnow()

    async def _execute_step(
        self,
        execution: WorkflowExecution,
        step: WorkflowStep,
    ) -> StepExecution:
        """Execute a single workflow step."""
        step_execution = StepExecution(
            id=str(uuid.uuid4()),
            step_id=step.id,
            step_name=step.name,
            step_type=step.type,
            input_data=dict(execution.context),
        )

        step_execution.started_at = datetime.utcnow()
        step_execution.status = StepExecutionStatus.RUNNING

        try:
            # Check conditions
            if step.conditions:
                should_run = self._evaluate_conditions(step.conditions, execution.context)
                if not should_run:
                    step_execution.status = StepExecutionStatus.SKIPPED
                    step_execution.completed_at = datetime.utcnow()
                    return step_execution

            # Get executor
            executor = self._step_executors.get(step.type)
            if not executor:
                raise ValueError(f"No executor for step type: {step.type}")

            # Execute with timeout
            result = await asyncio.wait_for(
                executor(step, execution.context),
                timeout=step.timeout_seconds,
            )

            # Update context with result
            execution.context[f"steps.{step.id}"] = result
            step_execution.output_data = result

            step_execution.status = StepExecutionStatus.COMPLETED

        except asyncio.TimeoutError:
            step_execution.status = StepExecutionStatus.FAILED
            step_execution.error = f"Step timed out after {step.timeout_seconds}s"

        except Exception as e:
            logger.error(f"Step execution failed: {step.id} error={e}")

            # Retry if configured
            if step_execution.attempt <= step.retry_count:
                step_execution.attempt += 1
                await asyncio.sleep(step.retry_delay_seconds)
                return await self._execute_step(execution, step)

            step_execution.status = StepExecutionStatus.FAILED
            step_execution.error = str(e)

        step_execution.completed_at = datetime.utcnow()
        step_execution.duration_ms = int(
            (step_execution.completed_at - step_execution.started_at).total_seconds() * 1000
        )

        return step_execution

    def _evaluate_conditions(
        self,
        conditions: list[WorkflowCondition],
        context: dict[str, Any],
    ) -> bool:
        """Evaluate workflow conditions."""
        for condition in conditions:
            value = self._get_nested_value(context, condition.field)

            if condition.operator == "eq":
                if value != condition.value:
                    return False
            elif condition.operator == "ne":
                if value == condition.value:
                    return False
            elif condition.operator == "gt":
                if not (value > condition.value):
                    return False
            elif condition.operator == "lt":
                if not (value < condition.value):
                    return False
            elif condition.operator == "gte":
                if not (value >= condition.value):
                    return False
            elif condition.operator == "lte":
                if not (value <= condition.value):
                    return False
            elif condition.operator == "contains":
                if condition.value not in value:
                    return False
            elif condition.operator == "regex":
                if not re.match(condition.value, str(value)):
                    return False

        return True

    def _get_nested_value(self, data: dict[str, Any], path: str) -> Any:
        """Get a nested value from a dict using dot notation."""
        keys = path.split(".")
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value

    # --- Step Executors ---

    async def _execute_notification(
        self,
        step: WorkflowStep,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a notification step."""
        config = step.config
        channels = config.get("channels", ["slack"])
        message = self._interpolate(config.get("message", "Workflow notification"), context)

        # In production, integrate with NotificationService
        logger.info(f"Sending notification to {channels}: {message}")

        return {"sent": True, "channels": channels, "message": message}

    async def _execute_webhook(
        self,
        step: WorkflowStep,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a webhook step."""
        config = step.config
        url = self._interpolate(config.get("url", ""), context)
        method = config.get("method", "POST")
        headers = config.get("headers", {})
        body = config.get("body", {})

        # Interpolate body values
        if isinstance(body, dict):
            body = {k: self._interpolate(str(v), context) for k, v in body.items()}

        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                json=body,
            )
            return {
                "status_code": response.status_code,
                "body": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
            }

    async def _execute_api_call(
        self,
        step: WorkflowStep,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute an internal API call."""
        config = step.config
        endpoint = config.get("endpoint", "")
        method = config.get("method", "GET")

        # Placeholder - in production, call actual internal endpoints
        logger.info(f"API call: {method} {endpoint}")

        return {"endpoint": endpoint, "method": method, "success": True}

    async def _execute_condition(
        self,
        step: WorkflowStep,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a condition step (evaluation happens in _execute_step)."""
        return {"evaluated": True}

    async def _execute_wait(
        self,
        step: WorkflowStep,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a wait step."""
        duration = step.config.get("duration_seconds", 60)
        await asyncio.sleep(duration)
        return {"waited_seconds": duration}

    async def _execute_transform(
        self,
        step: WorkflowStep,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a data transformation step."""
        template = step.config.get("template", "")
        # Placeholder for template rendering
        return {"template": template, "transformed": True}

    async def _execute_code_analysis(
        self,
        step: WorkflowStep,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a code analysis step."""
        # Placeholder - integrate with code analysis service
        return {"analysis": {"passed": True, "issues": []}}

    async def _execute_slack_message(
        self,
        step: WorkflowStep,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a Slack message step."""
        channel = step.config.get("channel", "#general")
        message = self._interpolate(step.config.get("message", ""), context)

        # Placeholder - integrate with Slack
        logger.info(f"Slack message to {channel}: {message}")
        return {"channel": channel, "sent": True}

    async def _execute_github_comment(
        self,
        step: WorkflowStep,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a GitHub comment step."""
        body = self._interpolate(step.config.get("body", ""), context)

        # Placeholder - integrate with GitHub
        logger.info(f"GitHub comment: {body}")
        return {"commented": True}

    async def _execute_jira_create(
        self,
        step: WorkflowStep,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a JIRA ticket creation step."""
        project = step.config.get("project", "")
        issue_type = step.config.get("issue_type", "Task")
        summary = self._interpolate(step.config.get("summary", ""), context)

        # Placeholder - integrate with JIRA
        logger.info(f"Creating JIRA ticket in {project}: {summary}")
        return {"project": project, "issue_type": issue_type, "created": True}

    def _interpolate(self, template: str, context: dict[str, Any]) -> str:
        """Interpolate variables in a template string."""
        def replace(match):
            path = match.group(1)
            value = self._get_nested_value(context, path)
            return str(value) if value is not None else match.group(0)

        return re.sub(r"\{\{([^}]+)\}\}", replace, template)

    # --- Execution Management ---

    async def get_execution(self, execution_id: str) -> WorkflowExecution | None:
        """Get an execution by ID."""
        return self._executions.get(execution_id)

    async def list_executions(
        self,
        workflow_id: str | None = None,
        status: WorkflowExecutionStatus | None = None,
        limit: int = 100,
    ) -> list[WorkflowExecution]:
        """List executions with optional filters."""
        executions = list(self._executions.values())

        if workflow_id:
            executions = [e for e in executions if e.workflow_id == workflow_id]
        if status:
            executions = [e for e in executions if e.status == status]

        return sorted(executions, key=lambda e: e.created_at, reverse=True)[:limit]

    async def cancel_execution(self, execution_id: str) -> WorkflowExecution | None:
        """Cancel a running execution."""
        execution = self._executions.get(execution_id)
        if not execution:
            return None

        if execution.status in (WorkflowExecutionStatus.RUNNING, WorkflowExecutionStatus.PENDING):
            execution.status = WorkflowExecutionStatus.CANCELLED
            execution.completed_at = datetime.utcnow()

        return execution

    def get_available_templates(self) -> list[dict[str, Any]]:
        """Get available workflow templates."""
        return [
            {
                "name": name,
                "description": template.get("description", ""),
                "triggers": [t.get("type") for t in template.get("triggers", [])],
                "steps_count": len(template.get("steps", [])),
            }
            for name, template in WORKFLOW_TEMPLATES.items()
        ]


def get_workflow_engine() -> WorkflowEngine:
    """Get or create the workflow engine singleton."""
    global _workflow_engine

    if _workflow_engine is None:
        _workflow_engine = WorkflowEngine()

    return _workflow_engine
