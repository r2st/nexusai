"""DevOps Agent Workflow orchestrating specialized agents.

Implements the NexusChat pattern of agent handoffs:
DORA Metrics Agent -> Dashboard Visualization Agent -> Executive Summary Agent
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any

import structlog

from app.services.agents.devops.dora_agent import DORAMetricsAgent, DORAAnalysisResult
from app.services.agents.devops.dashboard_agent import DashboardVisualizationAgent, VisualizationResult
from app.services.agents.devops.summary_agent import (
    ExecutiveSummaryAgent,
    ExecutiveSummary,
    AudienceLevel,
)
from app.services.agents.devops.adoption_agent import AISDLCAdoptionAgent, AdoptionAnalysisResult

logger = structlog.get_logger()


class WorkflowType(str, Enum):
    """Types of DevOps agent workflows."""

    DORA_FULL = "dora_full"  # DORA -> Dashboard -> Summary
    DORA_QUICK = "dora_quick"  # DORA -> Summary (no dashboard)
    ADOPTION_FULL = "adoption_full"  # Adoption -> Dashboard -> Summary
    ADOPTION_QUICK = "adoption_quick"  # Adoption -> Summary
    COMBINED = "combined"  # Both DORA and Adoption


class WorkflowStatus(str, Enum):
    """Status of workflow execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowStep:
    """A single step in the workflow."""

    step_number: int
    agent_id: str
    agent_name: str
    status: WorkflowStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    input_data: dict[str, Any] | None = None
    output_data: dict[str, Any] | None = None
    error: str | None = None


@dataclass
class WorkflowExecution:
    """Complete workflow execution record."""

    workflow_id: str
    workflow_type: WorkflowType
    status: WorkflowStatus
    steps: list[WorkflowStep]
    started_at: datetime
    completed_at: datetime | None = None
    final_output: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class DevOpsAgentWorkflow:
    """Orchestrates DevOps agent workflows with handoffs.

    This implements the NexusChat agent handoff pattern where:
    1. DORA/Adoption agent performs analysis
    2. Results are handed off to Dashboard agent for visualization
    3. Dashboard hands off to Summary agent for executive reporting

    Each agent receives the previous agent's output and can:
    - Use the data directly
    - Transform it as needed
    - Add its own analysis
    """

    def __init__(
        self,
        dora_agent: DORAMetricsAgent | None = None,
        adoption_agent: AISDLCAdoptionAgent | None = None,
        dashboard_agent: DashboardVisualizationAgent | None = None,
        summary_agent: ExecutiveSummaryAgent | None = None,
    ):
        self.dora_agent = dora_agent or DORAMetricsAgent()
        self.adoption_agent = adoption_agent or AISDLCAdoptionAgent()
        self.dashboard_agent = dashboard_agent or DashboardVisualizationAgent()
        self.summary_agent = summary_agent or ExecutiveSummaryAgent()

        self._executions: dict[str, WorkflowExecution] = {}

    async def execute_dora_workflow(
        self,
        project_id: str,
        period_days: int = 30,
        audience: AudienceLevel = AudienceLevel.EXECUTIVE,
        include_dashboard: bool = True,
        workflow_id: str | None = None,
    ) -> WorkflowExecution:
        """Execute the full DORA metrics workflow.

        Flow: DORA Agent -> Dashboard Agent -> Summary Agent
        """
        import uuid

        workflow_id = workflow_id or str(uuid.uuid4())
        workflow_type = WorkflowType.DORA_FULL if include_dashboard else WorkflowType.DORA_QUICK

        execution = WorkflowExecution(
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            status=WorkflowStatus.RUNNING,
            steps=[],
            started_at=datetime.now(UTC),
            metadata={
                "project_id": project_id,
                "period_days": period_days,
                "audience": audience.value,
            },
        )

        self._executions[workflow_id] = execution

        logger.info(
            "Starting DORA workflow",
            workflow_id=workflow_id,
            project_id=project_id,
        )

        try:
            # Step 1: DORA Analysis
            step1 = WorkflowStep(
                step_number=1,
                agent_id=self.dora_agent.agent_id,
                agent_name=self.dora_agent.agent_name,
                status=WorkflowStatus.RUNNING,
                started_at=datetime.now(UTC),
            )
            execution.steps.append(step1)

            dora_result = await self.dora_agent.analyze(
                project_id=project_id,
                period_days=period_days,
            )

            step1.status = WorkflowStatus.COMPLETED
            step1.completed_at = datetime.now(UTC)
            step1.output_data = self.dora_agent.format_for_handoff(dora_result)

            logger.info("DORA analysis completed", workflow_id=workflow_id)

            # Prepare handoff data
            handoff_data = step1.output_data

            # Step 2: Dashboard Visualization (optional)
            dashboard_result = None
            if include_dashboard:
                step2 = WorkflowStep(
                    step_number=2,
                    agent_id=self.dashboard_agent.agent_id,
                    agent_name=self.dashboard_agent.agent_name,
                    status=WorkflowStatus.RUNNING,
                    started_at=datetime.now(UTC),
                    input_data=handoff_data,
                )
                execution.steps.append(step2)

                dashboard_result = await self.dashboard_agent.create_dora_dashboard(
                    dora_data=handoff_data,
                )

                step2.status = WorkflowStatus.COMPLETED
                step2.completed_at = datetime.now(UTC)
                step2.output_data = self.dashboard_agent.format_for_handoff(dashboard_result)

                handoff_data = {**handoff_data, **step2.output_data}

                logger.info("Dashboard created", workflow_id=workflow_id)

            # Step 3: Executive Summary
            step3 = WorkflowStep(
                step_number=len(execution.steps) + 1,
                agent_id=self.summary_agent.agent_id,
                agent_name=self.summary_agent.agent_name,
                status=WorkflowStatus.RUNNING,
                started_at=datetime.now(UTC),
                input_data=handoff_data,
            )
            execution.steps.append(step3)

            summary = await self.summary_agent.generate_dora_summary(
                dora_data=handoff_data,
                dashboard_data=step2.output_data if include_dashboard and step2 else None,
                audience=audience,
            )

            step3.status = WorkflowStatus.COMPLETED
            step3.completed_at = datetime.now(UTC)
            step3.output_data = self.summary_agent.format_for_handoff(summary)

            logger.info("Summary generated", workflow_id=workflow_id)

            # Complete workflow
            execution.status = WorkflowStatus.COMPLETED
            execution.completed_at = datetime.now(UTC)
            execution.final_output = {
                "dora_analysis": step1.output_data,
                "dashboard": step2.output_data if include_dashboard else None,
                "summary": step3.output_data,
                "markdown": self.summary_agent.format_as_markdown(summary),
            }

            logger.info(
                "DORA workflow completed",
                workflow_id=workflow_id,
                duration_ms=(execution.completed_at - execution.started_at).total_seconds() * 1000,
            )

        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.completed_at = datetime.now(UTC)

            # Mark current step as failed
            for step in execution.steps:
                if step.status == WorkflowStatus.RUNNING:
                    step.status = WorkflowStatus.FAILED
                    step.error = str(e)

            logger.error("DORA workflow failed", workflow_id=workflow_id, error=str(e))

        return execution

    async def execute_adoption_workflow(
        self,
        organization_id: str,
        period_days: int = 30,
        audience: AudienceLevel = AudienceLevel.MANAGER,
        include_dashboard: bool = True,
        workflow_id: str | None = None,
    ) -> WorkflowExecution:
        """Execute the AI adoption analysis workflow.

        Flow: Adoption Agent -> Dashboard Agent -> Summary Agent
        """
        import uuid

        workflow_id = workflow_id or str(uuid.uuid4())
        workflow_type = WorkflowType.ADOPTION_FULL if include_dashboard else WorkflowType.ADOPTION_QUICK

        execution = WorkflowExecution(
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            status=WorkflowStatus.RUNNING,
            steps=[],
            started_at=datetime.now(UTC),
            metadata={
                "organization_id": organization_id,
                "period_days": period_days,
                "audience": audience.value,
            },
        )

        self._executions[workflow_id] = execution

        logger.info(
            "Starting adoption workflow",
            workflow_id=workflow_id,
            organization_id=organization_id,
        )

        try:
            # Step 1: Adoption Analysis
            step1 = WorkflowStep(
                step_number=1,
                agent_id=self.adoption_agent.agent_id,
                agent_name=self.adoption_agent.agent_name,
                status=WorkflowStatus.RUNNING,
                started_at=datetime.now(UTC),
            )
            execution.steps.append(step1)

            adoption_result = await self.adoption_agent.analyze(
                organization_id=organization_id,
                period_days=period_days,
            )

            step1.status = WorkflowStatus.COMPLETED
            step1.completed_at = datetime.now(UTC)
            step1.output_data = self.adoption_agent.format_for_handoff(adoption_result)

            handoff_data = step1.output_data

            # Step 2: Dashboard (optional)
            if include_dashboard:
                step2 = WorkflowStep(
                    step_number=2,
                    agent_id=self.dashboard_agent.agent_id,
                    agent_name=self.dashboard_agent.agent_name,
                    status=WorkflowStatus.RUNNING,
                    started_at=datetime.now(UTC),
                    input_data=handoff_data,
                )
                execution.steps.append(step2)

                dashboard_result = await self.dashboard_agent.create_adoption_dashboard(
                    adoption_data=handoff_data,
                )

                step2.status = WorkflowStatus.COMPLETED
                step2.completed_at = datetime.now(UTC)
                step2.output_data = self.dashboard_agent.format_for_handoff(dashboard_result)

                handoff_data = {**handoff_data, **step2.output_data}

            # Step 3: Summary
            step3 = WorkflowStep(
                step_number=len(execution.steps) + 1,
                agent_id=self.summary_agent.agent_id,
                agent_name=self.summary_agent.agent_name,
                status=WorkflowStatus.RUNNING,
                started_at=datetime.now(UTC),
                input_data=handoff_data,
            )
            execution.steps.append(step3)

            summary = await self.summary_agent.generate_adoption_summary(
                adoption_data=handoff_data,
                audience=audience,
            )

            step3.status = WorkflowStatus.COMPLETED
            step3.completed_at = datetime.now(UTC)
            step3.output_data = self.summary_agent.format_for_handoff(summary)

            # Complete
            execution.status = WorkflowStatus.COMPLETED
            execution.completed_at = datetime.now(UTC)
            execution.final_output = {
                "adoption_analysis": step1.output_data,
                "dashboard": step2.output_data if include_dashboard else None,
                "summary": step3.output_data,
                "markdown": self.summary_agent.format_as_markdown(summary),
            }

        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.completed_at = datetime.now(UTC)
            for step in execution.steps:
                if step.status == WorkflowStatus.RUNNING:
                    step.status = WorkflowStatus.FAILED
                    step.error = str(e)
            logger.error("Adoption workflow failed", workflow_id=workflow_id, error=str(e))

        return execution

    async def execute_combined_workflow(
        self,
        project_id: str,
        organization_id: str,
        period_days: int = 30,
        audience: AudienceLevel = AudienceLevel.EXECUTIVE,
    ) -> WorkflowExecution:
        """Execute combined DORA + Adoption workflow."""
        import uuid

        workflow_id = str(uuid.uuid4())

        execution = WorkflowExecution(
            workflow_id=workflow_id,
            workflow_type=WorkflowType.COMBINED,
            status=WorkflowStatus.RUNNING,
            steps=[],
            started_at=datetime.now(UTC),
        )

        try:
            # Run DORA and Adoption in parallel (conceptually)
            # Step 1: DORA
            dora_result = await self.dora_agent.analyze(project_id, period_days)
            dora_data = self.dora_agent.format_for_handoff(dora_result)

            # Step 2: Adoption
            adoption_result = await self.adoption_agent.analyze(organization_id, period_days)
            adoption_data = self.adoption_agent.format_for_handoff(adoption_result)

            # Step 3: Combined Dashboard
            dashboard_result = await self.dashboard_agent.create_dora_dashboard(dora_data)

            # Step 4: Combined Summary
            combined_data = {
                "dora": dora_data,
                "adoption": adoption_data,
                "project_id": project_id,
                "organization_id": organization_id,
            }

            # Generate summary with both datasets
            summary = await self.summary_agent.generate_dora_summary(
                dora_data=combined_data,
                dashboard_data=self.dashboard_agent.format_for_handoff(dashboard_result),
                audience=audience,
            )

            execution.status = WorkflowStatus.COMPLETED
            execution.completed_at = datetime.now(UTC)
            execution.final_output = {
                "dora": dora_data,
                "adoption": adoption_data,
                "dashboard": self.dashboard_agent.format_for_handoff(dashboard_result),
                "summary": self.summary_agent.format_for_handoff(summary),
            }

        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.completed_at = datetime.now(UTC)
            logger.error("Combined workflow failed", error=str(e))

        return execution

    def get_execution(self, workflow_id: str) -> WorkflowExecution | None:
        """Get workflow execution by ID."""
        return self._executions.get(workflow_id)

    def list_executions(
        self,
        workflow_type: WorkflowType | None = None,
        status: WorkflowStatus | None = None,
        limit: int = 100,
    ) -> list[WorkflowExecution]:
        """List workflow executions with optional filters."""
        executions = list(self._executions.values())

        if workflow_type:
            executions = [e for e in executions if e.workflow_type == workflow_type]

        if status:
            executions = [e for e in executions if e.status == status]

        # Sort by started_at descending
        executions.sort(key=lambda e: e.started_at, reverse=True)

        return executions[:limit]
