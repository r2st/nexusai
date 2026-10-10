"""AI Analytics API endpoints.

Provides endpoints for:
- AI tool usage tracking
- Productivity metrics and ROI
- AI-generated summaries
- Plugin management
"""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

logger = structlog.get_logger()

from app.api.deps import get_current_user, get_db
from app.core.multitenancy import get_current_tenant_id, set_tenant_context
from app.models.user import User
from app.services.ai_analytics import (
    CursorPlugin,
    ClaudeCodePlugin,
    GitHubCopilotPlugin,
    QDevPlugin,
    AISummaryService,
    AIROIService,
)

router = APIRouter()


# Request/Response Models
class AIToolConnectionCreate(BaseModel):
    """Create AI tool connection request."""

    tool_type: str
    name: str
    description: str | None = None
    endpoint: str | None = None
    config: dict[str, Any] = {}


class AIToolConnectionResponse(BaseModel):
    """AI tool connection response."""

    id: str
    tool_type: str
    name: str
    status: str
    last_collected_at: datetime | None = None


class AIMetricsResponse(BaseModel):
    """AI metrics response."""

    tool_type: str
    period_start: datetime
    period_end: datetime
    total_events: int
    total_lines_generated: int
    total_lines_accepted: int
    acceptance_rate: float
    unique_users: int
    total_tokens: int
    estimated_cost: float


class ROIResponse(BaseModel):
    """ROI metrics response."""

    period_start: datetime
    period_end: datetime
    total_license_cost: float
    total_api_cost: float
    estimated_time_saved_hours: float
    estimated_value_generated: float
    roi_percentage: float
    adoption_rate: float
    tool_breakdown: dict[str, Any]


class SummaryRequest(BaseModel):
    """Summary generation request."""

    summary_type: str  # sprint, metrics, pr, incident
    project_id: str | None = None
    target_id: str | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    data: dict[str, Any] = {}


class SummaryResponse(BaseModel):
    """Summary response."""

    id: str
    summary_type: str
    title: str | None
    summary: str
    key_points: list[str]
    recommendations: list[str]
    created_at: datetime


# Plugin registry
PLUGINS = {
    "cursor": CursorPlugin(),
    "claude_code": ClaudeCodePlugin(),
    "github_copilot": GitHubCopilotPlugin(),
    "q_dev": QDevPlugin(),
}


@router.get("/plugins")
async def list_plugins() -> list[dict[str, Any]]:
    """List available AI analytics plugins."""
    return [
        {
            "id": plugin_id,
            "name": plugin.name,
            "description": plugin.description,
            "version": plugin.version,
            "schema": plugin.get_schema(),
        }
        for plugin_id, plugin in PLUGINS.items()
    ]


@router.get("/plugins/{plugin_id}")
async def get_plugin(plugin_id: str) -> dict[str, Any]:
    """Get plugin details."""
    plugin = PLUGINS.get(plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")

    return {
        "id": plugin_id,
        "name": plugin.name,
        "description": plugin.description,
        "version": plugin.version,
        "schema": plugin.get_schema(),
    }


@router.post("/connections", status_code=status.HTTP_201_CREATED)
async def create_connection(
    request: AIToolConnectionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIToolConnectionResponse:
    """Create a new AI tool connection."""
    from app.models.ai_analytics import AIToolConnection

    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context required")

    # Validate plugin exists
    if request.tool_type not in PLUGINS:
        raise HTTPException(status_code=400, detail=f"Unknown tool type: {request.tool_type}")

    # Create connection
    connection = AIToolConnection(
        tenant_id=tenant_id,
        project_id=request.config.get("project_id"),
        tool_type=request.tool_type,
        name=request.name,
        description=request.description,
        endpoint=request.endpoint,
        config=request.config,
    )

    db.add(connection)
    await db.commit()
    await db.refresh(connection)

    return AIToolConnectionResponse(
        id=connection.id,
        tool_type=connection.tool_type,
        name=connection.name,
        status=connection.status,
        last_collected_at=connection.last_collected_at,
    )


@router.post("/connections/{connection_id}/test")
async def test_connection(
    connection_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Test an AI tool connection."""
    from sqlalchemy import select
    from app.models.ai_analytics import AIToolConnection
    from app.core.secrets import get_connection_secret

    tenant_id = get_current_tenant_id()

    # Get connection
    result = await db.execute(
        select(AIToolConnection).where(
            AIToolConnection.id == connection_id,
            AIToolConnection.tenant_id == tenant_id,
        )
    )
    connection = result.scalar_one_or_none()

    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")

    # Get plugin
    plugin = PLUGINS.get(connection.tool_type)
    if not plugin:
        raise HTTPException(status_code=400, detail="Plugin not found")

    # Get secrets if available
    secrets = {}
    if connection.secret_ref:
        secrets = await get_connection_secret(
            tenant_id, connection_id, connection.tool_type
        ) or {}

    # Merge config with secrets
    config = {**connection.config, **secrets}
    if connection.endpoint:
        config["endpoint"] = connection.endpoint

    # Test connection
    success, message = await plugin.test_connection(config)

    # Update status
    connection.status = "online" if success else "error"
    connection.status_message = message
    await db.commit()

    return {
        "success": success,
        "message": message,
    }


@router.post("/connections/{connection_id}/collect")
async def collect_data(
    connection_id: str,
    since: datetime | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Trigger data collection for an AI tool connection."""
    from sqlalchemy import select
    from app.models.ai_analytics import AIToolConnection
    from app.core.secrets import get_connection_secret

    tenant_id = get_current_tenant_id()

    # Get connection
    result = await db.execute(
        select(AIToolConnection).where(
            AIToolConnection.id == connection_id,
            AIToolConnection.tenant_id == tenant_id,
        )
    )
    connection = result.scalar_one_or_none()

    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")

    # Get plugin
    plugin = PLUGINS.get(connection.tool_type)
    if not plugin:
        raise HTTPException(status_code=400, detail="Plugin not found")

    # Get secrets
    secrets = {}
    if connection.secret_ref:
        secrets = await get_connection_secret(
            tenant_id, connection_id, connection.tool_type
        ) or {}

    # Merge config
    config = {**connection.config, **secrets}
    if connection.endpoint:
        config["endpoint"] = connection.endpoint

    # Collect data
    since = since or connection.last_collected_at
    events = await plugin.collect(
        db, tenant_id, connection.project_id, config, since
    )

    # Save events
    saved = await plugin.save_events(db, tenant_id, connection.project_id, events)

    # Update last collected
    connection.last_collected_at = datetime.now()
    await db.commit()

    return {
        "events_collected": len(events),
        "events_saved": saved,
    }


@router.get("/metrics")
async def get_metrics(
    tool_type: str | None = None,
    project_id: str | None = None,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AIMetricsResponse]:
    """Get AI usage metrics."""
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context required")

    # Default to last 30 days
    period_end = period_end or datetime.now()
    period_start = period_start or (period_end - timedelta(days=30))

    metrics = []

    # Get metrics for each tool or specific tool
    tools = [tool_type] if tool_type else list(PLUGINS.keys())

    for tool in tools:
        plugin = PLUGINS.get(tool)
        if not plugin:
            continue

        tool_metrics = await plugin.aggregate_metrics(
            db, tenant_id, project_id, period_start, period_end
        )

        metrics.append(AIMetricsResponse(
            tool_type=tool_metrics.tool_type,
            period_start=tool_metrics.period_start,
            period_end=tool_metrics.period_end,
            total_events=tool_metrics.total_events,
            total_lines_generated=tool_metrics.total_lines_generated,
            total_lines_accepted=tool_metrics.total_lines_accepted,
            acceptance_rate=tool_metrics.acceptance_rate,
            unique_users=tool_metrics.unique_users,
            total_tokens=tool_metrics.total_tokens,
            estimated_cost=tool_metrics.estimated_cost,
        ))

    return metrics


@router.get("/roi")
async def get_roi(
    project_id: str | None = None,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ROIResponse:
    """Get AI ROI metrics."""
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context required")

    # Default to last 30 days
    period_end = period_end or datetime.now()
    period_start = period_start or (period_end - timedelta(days=30))

    roi_service = AIROIService()
    roi = await roi_service.calculate_roi(
        db, tenant_id, project_id, period_start, period_end
    )

    return ROIResponse(
        period_start=roi.period_start,
        period_end=roi.period_end,
        total_license_cost=roi.total_license_cost,
        total_api_cost=roi.total_api_cost,
        estimated_time_saved_hours=roi.estimated_time_saved_hours,
        estimated_value_generated=roi.estimated_value_generated,
        roi_percentage=roi.roi_percentage,
        adoption_rate=roi.adoption_rate,
        tool_breakdown=roi.tool_breakdown,
    )


@router.get("/roi/trend")
async def get_roi_trend(
    project_id: str | None = None,
    periods: int = Query(default=6, ge=1, le=12),
    granularity: str = Query(default="monthly", pattern="^(weekly|monthly|quarterly)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Get ROI trend over time."""
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context required")

    roi_service = AIROIService()
    return await roi_service.get_roi_trend(
        db, tenant_id, project_id, periods, granularity
    )


@router.get("/productivity")
async def get_productivity(
    project_id: str | None = None,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get detailed productivity metrics."""
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context required")

    # Default to last 30 days
    period_end = period_end or datetime.now()
    period_start = period_start or (period_end - timedelta(days=30))

    roi_service = AIROIService()
    return await roi_service.get_productivity_metrics(
        db, tenant_id, project_id, period_start, period_end
    )


@router.post("/summaries")
async def generate_summary(
    request: SummaryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SummaryResponse:
    """Generate an AI summary."""
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context required")

    summary_service = AISummaryService()

    # Default period
    period_end = request.period_end or datetime.now()
    period_start = request.period_start or (period_end - timedelta(days=14))

    if request.summary_type == "sprint":
        summary = await summary_service.generate_sprint_summary(
            db,
            tenant_id,
            request.project_id,
            period_start,
            period_end,
            request.data.get("sprint_name"),
        )
    elif request.summary_type == "metrics":
        summary = await summary_service.generate_metrics_summary(
            db,
            tenant_id,
            request.project_id,
            period_start,
            period_end,
        )
    elif request.summary_type == "pr":
        summary = await summary_service.generate_pr_summary(
            db,
            tenant_id,
            request.project_id,
            request.data,
        )
    elif request.summary_type == "incident":
        summary = await summary_service.generate_incident_postmortem(
            db,
            tenant_id,
            request.project_id,
            request.data,
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown summary type: {request.summary_type}"
        )

    return SummaryResponse(
        id=summary.id,
        summary_type=summary.summary_type,
        title=summary.title,
        summary=summary.summary,
        key_points=summary.key_points,
        recommendations=summary.recommendations,
        created_at=summary.created_at,
    )


@router.get("/summaries")
async def list_summaries(
    project_id: str | None = None,
    summary_type: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SummaryResponse]:
    """List AI summaries."""
    from sqlalchemy import select
    from app.models.ai_analytics import AISummary

    tenant_id = get_current_tenant_id()

    query = select(AISummary).where(AISummary.tenant_id == tenant_id)

    if project_id:
        query = query.where(AISummary.project_id == project_id)
    if summary_type:
        query = query.where(AISummary.summary_type == summary_type)

    query = query.order_by(AISummary.created_at.desc()).limit(limit)

    result = await db.execute(query)
    summaries = result.scalars().all()

    return [
        SummaryResponse(
            id=s.id,
            summary_type=s.summary_type,
            title=s.title,
            summary=s.summary,
            key_points=s.key_points,
            recommendations=s.recommendations,
            created_at=s.created_at,
        )
        for s in summaries
    ]
