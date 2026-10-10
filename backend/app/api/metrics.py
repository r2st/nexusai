"""Metrics API Endpoints.

Provides endpoints for:
- DORA metrics
- SPACE framework metrics
- Business metrics
- Productivity metrics
- Flow metrics
- Unified metrics with AI insights
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.database import get_db

logger = structlog.get_logger()
from app.api.deps import get_current_user
from app.core.multitenancy import get_current_tenant_id
from app.models.user import User
from app.services.metrics import (
    dora_metrics_service,
    space_metrics_service,
    business_metrics_service,
    productivity_metrics_service,
)
from app.services.metrics.flow import flow_metrics_service
from app.services.metrics.unified import unified_metrics_service
from app.services.metrics.insights import insights_generator

router = APIRouter()


# ============= DORA Metrics =============

@router.get("/dora/{project_name}")
async def get_dora_metrics(
    project_name: str,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    _current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get DORA metrics for a project.

    Returns:
        - deployment_frequency: Deployments per day
        - lead_time_for_changes: Hours from commit to production
        - mean_time_to_recovery: Hours to recover from failures
        - change_failure_rate: Percentage of failed deployments
        - Performance levels (Elite/High/Medium/Low)
    """
    metrics = await dora_metrics_service.calculate_metrics(
        session, tenant_id, project_name, period_start, period_end
    )
    return metrics.model_dump()


@router.get("/dora/{project_name}/trend")
async def get_dora_trend(
    project_name: str,
    periods: int = Query(default=6, ge=1, le=24),
    granularity: str = Query(default="monthly", pattern="^(weekly|monthly|quarterly)$"),
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    _current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Get DORA metrics trend over time."""
    trends = await dora_metrics_service.get_trend(
        session, tenant_id, project_name, periods, granularity
    )
    return [t.model_dump() for t in trends]


@router.get("/dora/{project_name}/benchmark")
async def get_dora_benchmark(
    project_name: str,
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    _current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Compare project DORA metrics against industry benchmarks."""
    metrics = await dora_metrics_service.calculate_metrics(
        session, tenant_id, project_name
    )
    return await dora_metrics_service.get_benchmark_comparison(metrics)


# ============= SPACE Framework =============

@router.get("/space/{project_name}")
async def get_space_metrics(
    project_name: str,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    _current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get SPACE framework metrics for a project.

    SPACE dimensions:
        - Satisfaction: Developer satisfaction and wellbeing
        - Performance: Code quality and reliability
        - Activity: Development activity levels
        - Communication: Team collaboration
        - Efficiency: Workflow efficiency
    """
    metrics = await space_metrics_service.calculate_metrics(
        session, tenant_id, project_name, period_start, period_end
    )
    return metrics.model_dump()


@router.get("/space/{project_name}/trend")
async def get_space_trend(
    project_name: str,
    periods: int = Query(default=6, ge=1, le=24),
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    _current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Get SPACE metrics trend over time."""
    trends = await space_metrics_service.get_trend(
        session, tenant_id, project_name, periods
    )
    return [t.model_dump() for t in trends]


@router.get("/space/{project_name}/recommendations")
async def get_space_recommendations(
    project_name: str,
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    _current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Get recommendations for improving SPACE metrics."""
    return await space_metrics_service.get_recommendations(
        session, tenant_id, project_name
    )


# ============= Business Metrics =============

@router.get("/business/{project_name}")
async def get_business_metrics(
    project_name: str,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    _current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get business metrics for a project.

    Novel metrics:
        - ELS: Engineering Leverage Score
        - DPI: Delivery Predictability Index
        - IQ: Innovation Quotient
        - VSE: Value Stream Efficiency
        - THC: Team Health Composite
        - KDS: Knowledge Distribution Score
    """
    metrics = await business_metrics_service.calculate_metrics(
        session, tenant_id, project_name, period_start, period_end
    )
    return metrics.model_dump()


@router.get("/business/{project_name}/trend")
async def get_business_trend(
    project_name: str,
    periods: int = Query(default=6, ge=1, le=24),
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    _current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Get business metrics trend over time."""
    trends = await business_metrics_service.get_trend(
        session, tenant_id, project_name, periods
    )
    return [t.model_dump() for t in trends]


@router.get("/business/{project_name}/executive-summary")
async def get_executive_summary(
    project_name: str,
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    _current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get executive summary of business metrics."""
    return await business_metrics_service.get_executive_summary(
        session, tenant_id, project_name
    )


# ============= Productivity =============

@router.get("/productivity/team/{project_name}")
async def get_team_productivity(
    project_name: str,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    _current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get team productivity metrics."""
    metrics = await productivity_metrics_service.calculate_team_productivity(
        session, tenant_id, project_name, period_start, period_end
    )
    return metrics.model_dump()


@router.get("/productivity/individual/{developer_id}")
async def get_individual_productivity(
    developer_id: str,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    _current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get individual developer productivity metrics."""
    metrics = await productivity_metrics_service.calculate_individual_productivity(
        session, tenant_id, developer_id, period_start, period_end
    )
    return metrics.model_dump()


@router.get("/productivity/leaderboard/{project_name}")
async def get_productivity_leaderboard(
    project_name: str,
    metric: str = Query(default="overall", pattern="^(overall|velocity|quality|collaboration)$"),
    limit: int = Query(default=10, ge=1, le=50),
    period_start: datetime | None = None,
    period_end: datetime | None = None,
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    _current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Get productivity leaderboard for a project."""
    results = await productivity_metrics_service.get_productivity_leaderboard(
        session, tenant_id, project_name, metric, limit, period_start, period_end
    )
    return [r.model_dump() for r in results]


@router.get("/productivity/insights/{project_name}")
async def get_productivity_insights(
    project_name: str,
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    _current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get actionable productivity insights for a project."""
    return await productivity_metrics_service.get_productivity_insights(
        session, tenant_id, project_name
    )


# ============= Combined Dashboard =============

@router.get("/dashboard/{project_name}")
async def get_metrics_dashboard(
    project_name: str,
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    _current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get combined metrics dashboard for a project.

    Returns all metrics in a single response for dashboard rendering.
    """
    # Fetch all metrics in parallel would be ideal, but sequential for simplicity
    dora = await dora_metrics_service.calculate_metrics(
        session, tenant_id, project_name
    )
    space = await space_metrics_service.calculate_metrics(
        session, tenant_id, project_name
    )
    business = await business_metrics_service.calculate_metrics(
        session, tenant_id, project_name
    )
    team = await productivity_metrics_service.calculate_team_productivity(
        session, tenant_id, project_name
    )

    return {
        "project_name": project_name,
        "timestamp": datetime.utcnow().isoformat(),
        "dora": dora.model_dump(),
        "space": space.model_dump(),
        "business": business.model_dump(),
        "team_productivity": team.model_dump(),
    }


# ============= Flow Metrics =============

@router.get("/flow/{project_name}")
async def get_flow_metrics(
    project_name: str,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    _current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get Flow metrics for a project.

    Returns:
        - issues_completed: Number of issues completed
        - story_points_completed: Story points delivered
        - prs_merged: Pull requests merged
        - avg_coding_time: Average time in coding phase (hours)
        - avg_review_time: Average time in review phase (hours)
        - avg_deploy_time: Average time to deploy (hours)
        - total_cycle_time: Total end-to-end cycle time (hours)
        - current_wip: Current work in progress count
        - flow_efficiency: Percentage of active vs wait time
    """
    metrics = await flow_metrics_service.calculate_metrics(
        project_name, period_start, period_end
    )
    return metrics.model_dump()


@router.get("/flow/{project_name}/cfd")
async def get_cumulative_flow_diagram(
    project_name: str,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    _current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Get Cumulative Flow Diagram data.

    Returns daily counts for each workflow state for visualization.
    """
    return await flow_metrics_service.get_cumulative_flow_diagram_data(
        project_name, period_start, period_end
    )


@router.get("/flow/{project_name}/cycle-time-histogram")
async def get_cycle_time_histogram(
    project_name: str,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    _current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get cycle time distribution data.

    Returns histogram buckets and percentiles (p50, p85, p95).
    """
    return await flow_metrics_service.get_cycle_time_histogram(
        project_name, period_start, period_end
    )


@router.get("/flow/{project_name}/throughput")
async def get_throughput_chart(
    project_name: str,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
    granularity: str = Query(default="weekly", pattern="^(daily|weekly|monthly)$"),
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    _current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Get throughput run chart data.

    Returns throughput over time with trend line.
    """
    return await flow_metrics_service.get_throughput_run_chart(
        project_name, period_start, period_end, granularity
    )


# ============= Unified Metrics with AI Insights =============

@router.get("/unified/{project_name}")
async def get_unified_metrics(
    project_name: str,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
    include_insights: bool = Query(default=True),
    include_ai_summary: bool = Query(default=True),
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    _current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get unified metrics combining DORA, Flow, and Productivity.

    Includes AI-generated insights and natural language summary.

    Returns:
        - dora: DORA metrics with performance levels
        - flow: Flow metrics (WIP, cycle time, throughput)
        - team_productivity: Team productivity metrics
        - insights: AI-generated actionable insights
        - ai_summary: Natural language summary of metrics state
        - overall_health_score: Composite health score (0-100)
        - delivery_score: Delivery performance score (0-100)
        - quality_score: Quality score (0-100)
        - velocity_score: Velocity score (0-100)
    """
    metrics = await unified_metrics_service.get_unified_metrics(
        session, tenant_id, project_name, period_start, period_end,
        include_insights, include_ai_summary
    )
    return metrics.model_dump()


@router.get("/unified/{project_name}/summary")
async def get_metrics_summary(
    project_name: str,
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    _current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get a quick summary of current metrics state.

    Lightweight endpoint for dashboards and status checks.
    """
    return await unified_metrics_service.get_metrics_summary(
        session, tenant_id, project_name
    )


@router.get("/unified/{project_name}/dashboard")
async def get_unified_dashboard(
    project_name: str,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    _current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get complete dashboard data for metrics visualization.

    Returns all data needed for the unified metrics dashboard:
        - current: Current unified metrics
        - dora_trend: Historical DORA metrics
        - benchmark_comparison: Industry benchmark comparison
        - cumulative_flow_diagram: CFD chart data
        - cycle_time_histogram: Cycle time distribution
        - throughput_chart: Throughput over time
        - top_contributors: Leaderboard data
        - period_comparison: Current vs previous period
    """
    dashboard = await unified_metrics_service.get_dashboard_data(
        session, tenant_id, project_name, period_start, period_end
    )

    # Convert models to dicts for JSON response
    result = {
        "current": dashboard.current.model_dump() if dashboard.current else None,
        "dora_trend": [m.model_dump() for m in dashboard.dora_trend],
        "flow_trend": dashboard.flow_trend,
        "period_comparison": dashboard.period_comparison,
        "benchmark_comparison": dashboard.benchmark_comparison,
        "cumulative_flow_diagram": dashboard.cumulative_flow_diagram,
        "cycle_time_histogram": dashboard.cycle_time_histogram,
        "throughput_chart": dashboard.throughput_chart,
        "top_contributors": dashboard.top_contributors,
    }
    return result


# ============= AI Insights =============

@router.get("/insights/{project_name}")
async def get_ai_insights(
    project_name: str,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    _current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get AI-generated insights for a project.

    Analyzes metrics and generates:
        - Actionable insights with severity levels
        - Recommendations for improvement
        - Natural language summary
    """
    # Get DORA metrics
    dora = await dora_metrics_service.calculate_metrics(
        session, tenant_id, project_name, period_start, period_end
    )

    # Get trend data for context
    trends = await dora_metrics_service.get_trend(
        session, tenant_id, project_name, periods=6, granularity="weekly"
    )

    # Generate insights
    insights = await insights_generator.generate_dora_insights(dora, trends)

    # Generate AI summary
    summary = await insights_generator.generate_ai_summary(dora, insights)

    return {
        "project_name": project_name,
        "insights": [i.model_dump() for i in insights],
        "summary": summary,
        "metrics_snapshot": {
            "dora_level": dora.overall_level,
            "deployment_frequency": dora.deployment_frequency,
            "lead_time_hours": dora.lead_time_for_changes,
            "change_failure_rate": dora.change_failure_rate,
            "mttr_hours": dora.mean_time_to_recovery,
        },
        "generated_at": datetime.utcnow().isoformat(),
    }


@router.post("/insights/{project_name}/chat")
async def chat_about_metrics(
    project_name: str,
    question: str = Query(..., min_length=5, max_length=500),
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
    _current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Ask questions about metrics in natural language.

    Allows users to ask questions like:
        - "Why is our deployment frequency low?"
        - "What can we do to improve lead time?"
        - "Compare our metrics to industry standards"
    """
    # Get current metrics
    dora = await dora_metrics_service.calculate_metrics(
        session, tenant_id, project_name
    )
    flow = await flow_metrics_service.calculate_metrics(project_name)
    team = await productivity_metrics_service.calculate_team_productivity(
        session, tenant_id, project_name
    )

    # Generate contextual answer using insights generator
    # This would use the LLM gateway for a conversational response
    answer = await insights_generator.answer_question(
        question=question,
        dora_metrics=dora,
        flow_metrics=flow,
        productivity_metrics=team,
    )

    return {
        "question": question,
        "answer": answer,
        "project_name": project_name,
        "generated_at": datetime.utcnow().isoformat(),
    }


# ============= Health Check =============

@router.get("/health")
async def metrics_health_check() -> dict[str, str]:
    """Check metrics service health."""
    return {
        "status": "healthy",
        "service": "metrics",
        "timestamp": datetime.utcnow().isoformat(),
    }
