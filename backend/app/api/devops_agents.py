"""API endpoints for DevOps agents (DORA, Dashboard, Summary, Adoption)."""

from datetime import datetime, UTC
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.config import settings

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.agents.devops import (
    DORAMetricsAgent,
    DashboardVisualizationAgent,
    ExecutiveSummaryAgent,
    AISDLCAdoptionAgent,
    DevOpsAgentWorkflow,
)
from app.services.agents.devops.summary_agent import AudienceLevel
from app.services.agents.devops.workflow import WorkflowType, WorkflowStatus

logger = structlog.get_logger()

router = APIRouter(prefix="/devops-agents", tags=["devops-agents"])


# ======================
# Request/Response Models
# ======================

class DORAAnalysisRequest(BaseModel):
    """Request for DORA metrics analysis."""

    project_id: str
    period_days: int = Field(default=30, ge=1, le=365)
    compare_to_previous: bool = True


class AdoptionAnalysisRequest(BaseModel):
    """Request for AI adoption analysis."""

    organization_id: str
    period_days: int = Field(default=30, ge=1, le=365)


class WorkflowCreateRequest(BaseModel):
    """Request to create a workflow execution."""

    workflow_type: str = Field(..., description="dora_full, dora_quick, adoption_full, adoption_quick, combined")
    project_id: str | None = None
    organization_id: str | None = None
    period_days: int = Field(default=30, ge=1, le=365)
    audience: str = Field(default="executive", description="executive, manager, team")
    include_dashboard: bool = True


class DashboardCreateRequest(BaseModel):
    """Request to create a dashboard."""

    dashboard_type: str = Field(..., description="dora or adoption")
    data: dict[str, Any]
    title: str | None = None


class SummaryCreateRequest(BaseModel):
    """Request to create an executive summary."""

    data_type: str = Field(..., description="dora or adoption")
    data: dict[str, Any]
    audience: str = Field(default="executive")


class MetricResponse(BaseModel):
    """Response for a single metric."""

    name: str
    value: float
    unit: str
    performance_level: str
    trend: str
    trend_percentage: float
    benchmark_comparison: str


class DORAAnalysisResponse(BaseModel):
    """Response for DORA analysis."""

    project_id: str
    period_start: datetime
    period_end: datetime
    overall_performance: str
    metrics: list[MetricResponse]
    recommendations: list[str]
    insights: list[str]


class WorkflowResponse(BaseModel):
    """Response for a workflow execution."""

    workflow_id: str
    workflow_type: str
    status: str
    started_at: datetime
    completed_at: datetime | None
    steps: list[dict[str, Any]]
    final_output: dict[str, Any] | None


# ======================
# Endpoints
# ======================

@router.get("/health")
async def health_check():
    """Check DevOps agents service health."""
    return {
        "status": "healthy" if settings.DEVOPS_AGENTS_ENABLED else "disabled",
        "agents": [
            "dora-metrics-agent",
            "dashboard-visualization-agent",
            "executive-summary-agent",
            "ai-sdlc-adoption-agent",
        ],
    }


@router.post("/dora/analyze", response_model=DORAAnalysisResponse)
async def analyze_dora_metrics(
    request: DORAAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run DORA metrics analysis for a project."""
    if not settings.DEVOPS_AGENTS_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DevOps agents are disabled",
        )

    agent = DORAMetricsAgent(db_session=db)

    result = await agent.analyze(
        project_id=request.project_id,
        period_days=request.period_days,
        compare_to_previous=request.compare_to_previous,
    )

    return DORAAnalysisResponse(
        project_id=result.project_id,
        period_start=result.period_start,
        period_end=result.period_end,
        overall_performance=result.overall_performance.value,
        metrics=[
            MetricResponse(
                name=m.metric.value,
                value=m.value,
                unit=m.unit,
                performance_level=m.performance_level.value,
                trend=m.trend,
                trend_percentage=m.trend_percentage,
                benchmark_comparison=m.benchmark_comparison,
            )
            for m in result.metrics
        ],
        recommendations=result.recommendations,
        insights=result.insights,
    )


@router.post("/adoption/analyze")
async def analyze_adoption(
    request: AdoptionAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run AI SDLC adoption analysis."""
    if not settings.DEVOPS_AGENTS_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DevOps agents are disabled",
        )

    agent = AISDLCAdoptionAgent(db_session=db)

    result = await agent.analyze(
        organization_id=request.organization_id,
        period_days=request.period_days,
    )

    return {
        "organization_id": result.organization_id,
        "period_start": result.period_start.isoformat(),
        "period_end": result.period_end.isoformat(),
        "overall_adoption_rate": result.overall_adoption_rate,
        "total_users": result.total_users,
        "active_users": result.active_users,
        "teams": [
            {
                "team_id": t.team_id,
                "team_name": t.team_name,
                "adoption_rate": t.adoption_rate,
                "avg_acceptance_rate": t.avg_acceptance_rate,
                "top_tool": t.top_tool.value if t.top_tool else None,
            }
            for t in result.teams
        ],
        "roi_analysis": result.roi_analysis,
        "recommendations": result.recommendations,
        "insights": result.insights,
    }


@router.post("/dashboard/create", status_code=status.HTTP_201_CREATED)
async def create_dashboard(
    request: DashboardCreateRequest,
    current_user: User = Depends(get_current_user),
):
    """Create a visualization dashboard."""
    agent = DashboardVisualizationAgent()

    if request.dashboard_type == "dora":
        result = await agent.create_dora_dashboard(
            dora_data=request.data,
            dashboard_title=request.title or "DORA Metrics Dashboard",
        )
    elif request.dashboard_type == "adoption":
        result = await agent.create_adoption_dashboard(
            adoption_data=request.data,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid dashboard type: {request.dashboard_type}",
        )

    return {
        "success": result.success,
        "dashboard_id": result.dashboard.dashboard_id if result.dashboard else None,
        "dashboard_title": result.dashboard.title if result.dashboard else None,
        "chart_count": len(result.chart_specs),
        "charts": result.chart_specs,
        "grafana_json": result.grafana_json,
        "error": result.error,
    }


@router.post("/summary/create", status_code=status.HTTP_201_CREATED)
async def create_summary(
    request: SummaryCreateRequest,
    current_user: User = Depends(get_current_user),
):
    """Create an executive summary."""
    agent = ExecutiveSummaryAgent()

    # Map audience string to enum
    audience_map = {
        "executive": AudienceLevel.EXECUTIVE,
        "manager": AudienceLevel.MANAGER,
        "team": AudienceLevel.TEAM,
    }
    audience = audience_map.get(request.audience.lower(), AudienceLevel.EXECUTIVE)

    if request.data_type == "dora":
        summary = await agent.generate_dora_summary(
            dora_data=request.data,
            audience=audience,
        )
    elif request.data_type == "adoption":
        summary = await agent.generate_adoption_summary(
            adoption_data=request.data,
            audience=audience,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid data type: {request.data_type}",
        )

    return {
        "title": summary.title,
        "subtitle": summary.subtitle,
        "period_description": summary.period_description,
        "audience": summary.audience.value,
        "sections": [
            {
                "title": s.title,
                "content": s.content,
                "icon": s.icon,
                "priority": s.priority,
            }
            for s in summary.sections
        ],
        "key_metrics": summary.key_metrics,
        "action_items": summary.action_items,
        "markdown": agent.format_as_markdown(summary),
        "slack": agent.format_as_slack(summary),
    }


@router.post("/workflows", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    request: WorkflowCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create and execute a DevOps agent workflow."""
    if not settings.DEVOPS_AGENTS_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DevOps agents are disabled",
        )

    # Map audience
    audience_map = {
        "executive": AudienceLevel.EXECUTIVE,
        "manager": AudienceLevel.MANAGER,
        "team": AudienceLevel.TEAM,
    }
    audience = audience_map.get(request.audience.lower(), AudienceLevel.EXECUTIVE)

    # Create workflow
    workflow = DevOpsAgentWorkflow()

    if request.workflow_type in ("dora_full", "dora_quick"):
        if not request.project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="project_id is required for DORA workflows",
            )

        execution = await workflow.execute_dora_workflow(
            project_id=request.project_id,
            period_days=request.period_days,
            audience=audience,
            include_dashboard=request.include_dashboard and request.workflow_type == "dora_full",
        )

    elif request.workflow_type in ("adoption_full", "adoption_quick"):
        if not request.organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="organization_id is required for adoption workflows",
            )

        execution = await workflow.execute_adoption_workflow(
            organization_id=request.organization_id,
            period_days=request.period_days,
            audience=audience,
            include_dashboard=request.include_dashboard and request.workflow_type == "adoption_full",
        )

    elif request.workflow_type == "combined":
        if not request.project_id or not request.organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Both project_id and organization_id required for combined workflow",
            )

        execution = await workflow.execute_combined_workflow(
            project_id=request.project_id,
            organization_id=request.organization_id,
            period_days=request.period_days,
            audience=audience,
        )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid workflow type: {request.workflow_type}",
        )

    return WorkflowResponse(
        workflow_id=execution.workflow_id,
        workflow_type=execution.workflow_type.value,
        status=execution.status.value,
        started_at=execution.started_at,
        completed_at=execution.completed_at,
        steps=[
            {
                "step_number": s.step_number,
                "agent_id": s.agent_id,
                "agent_name": s.agent_name,
                "status": s.status.value,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                "error": s.error,
            }
            for s in execution.steps
        ],
        final_output=execution.final_output,
    )


@router.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get workflow execution status."""
    workflow = DevOpsAgentWorkflow()
    execution = workflow.get_execution(workflow_id)

    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    return WorkflowResponse(
        workflow_id=execution.workflow_id,
        workflow_type=execution.workflow_type.value,
        status=execution.status.value,
        started_at=execution.started_at,
        completed_at=execution.completed_at,
        steps=[
            {
                "step_number": s.step_number,
                "agent_id": s.agent_id,
                "agent_name": s.agent_name,
                "status": s.status.value,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                "error": s.error,
            }
            for s in execution.steps
        ],
        final_output=execution.final_output,
    )


@router.get("/workflows")
async def list_workflows(
    workflow_type: str | None = None,
    status: str | None = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
):
    """List workflow executions."""
    workflow = DevOpsAgentWorkflow()

    wf_type = None
    if workflow_type:
        try:
            wf_type = WorkflowType(workflow_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid workflow_type: {workflow_type!r}. Valid values: {[e.value for e in WorkflowType]}",
            )

    wf_status = None
    if status:
        try:
            wf_status = WorkflowStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {status!r}. Valid values: {[e.value for e in WorkflowStatus]}",
            )

    executions = workflow.list_executions(
        workflow_type=wf_type,
        status=wf_status,
        limit=limit,
    )

    return {
        "workflows": [
            {
                "workflow_id": e.workflow_id,
                "workflow_type": e.workflow_type.value,
                "status": e.status.value,
                "started_at": e.started_at.isoformat(),
                "completed_at": e.completed_at.isoformat() if e.completed_at else None,
                "step_count": len(e.steps),
            }
            for e in executions
        ],
        "count": len(executions),
    }


@router.post("/workflows/{workflow_id}/cancel")
async def cancel_workflow(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
):
    """Cancel a running workflow."""
    workflow = DevOpsAgentWorkflow()
    execution = workflow.get_execution(workflow_id)

    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    if execution.status != WorkflowStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel workflow in {execution.status.value} status",
        )

    # Mark as cancelled
    execution.status = WorkflowStatus.CANCELLED
    execution.completed_at = datetime.now(UTC)

    return {"status": "cancelled", "workflow_id": workflow_id}


@router.get("/benchmarks")
async def get_dora_benchmarks():
    """Get DORA performance benchmarks."""
    return {
        "deployment_frequency": {
            "elite": "Multiple deploys per day",
            "high": "Between once per day and once per week",
            "medium": "Between once per week and once per month",
            "low": "Less than once per month",
        },
        "lead_time_for_changes": {
            "elite": "Less than one day",
            "high": "Between one day and one week",
            "medium": "Between one week and one month",
            "low": "More than one month",
        },
        "time_to_restore": {
            "elite": "Less than one hour",
            "high": "Less than one day",
            "medium": "Less than one week",
            "low": "More than one week",
        },
        "change_failure_rate": {
            "elite": "0-5%",
            "high": "5-10%",
            "medium": "10-15%",
            "low": "15%+",
        },
    }
