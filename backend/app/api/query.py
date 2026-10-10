"""API endpoints for the Query Gateway."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.api.deps import get_current_user, get_db

TIME_RANGE_DELTAS = {
    "1h": timedelta(hours=1),
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
    "90d": timedelta(days=90),
}

logger = structlog.get_logger()
from app.models.user import User
from app.services.query import (
    DataSource,
    QueryRequest,
    get_query_gateway,
)

router = APIRouter(prefix="/query", tags=["query"])


# Request models
class UnifiedQueryRequest(BaseModel):
    """Request for unified query."""

    sources: list[DataSource] = Field(
        default=[DataSource.METRICS],
        description="Data sources to query",
    )
    start_time: datetime | None = None
    end_time: datetime | None = None
    project_id: str | None = None
    team_id: str | None = None
    entity_types: list[str] | None = None
    search_query: str | None = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
    include_trends: bool = False


@router.post(
    "",
    summary="Execute unified query",
)
async def execute_query(
    request: UnifiedQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Execute a unified query across multiple data sources.

    Aggregates data from metrics, entities, events, and search
    into a single response.
    """
    tenant_id = str(current_user.organization_id) if current_user.organization_id else str(current_user.id)

    query_request = QueryRequest(
        sources=request.sources,
        start_time=request.start_time,
        end_time=request.end_time,
        project_id=request.project_id,
        team_id=request.team_id,
        entity_types=request.entity_types,
        search_query=request.search_query,
        limit=request.limit,
        offset=request.offset,
        include_trends=request.include_trends,
    )

    gateway = get_query_gateway()
    response = await gateway.query(db, tenant_id, query_request)

    return {
        "data": response.data,
        "summary": response.summary,
        "total_count": response.total_count,
        "has_more": response.total_count > request.limit + request.offset,
        "execution_time_ms": response.execution_time_ms,
        "warnings": response.warnings,
    }


@router.get(
    "/dashboards",
    summary="List available dashboards",
)
async def list_dashboards(
    current_user: User = Depends(get_current_user),
):
    """List available pre-defined dashboard queries."""
    gateway = get_query_gateway()
    return gateway.list_dashboards()


@router.get(
    "/dashboards/{dashboard_name}",
    summary="Execute dashboard query",
)
async def execute_dashboard_query(
    dashboard_name: str,
    project_id: str | None = None,
    team_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Execute a pre-defined dashboard query.

    Available dashboards:
    - overview: High-level DORA metrics
    - team_health: SPACE framework metrics
    - deployments: Deployment activity
    - incidents: Incident tracking
    - pull_requests: PR activity
    """
    tenant_id = str(current_user.organization_id) if current_user.organization_id else str(current_user.id)

    filters = {}
    if project_id:
        filters["project_id"] = project_id
    if team_id:
        filters["team_id"] = team_id

    gateway = get_query_gateway()

    try:
        response = await gateway.query_dashboard(
            db, tenant_id, dashboard_name, filters
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dashboard '{dashboard_name}' not found. Use GET /query/dashboards to see available dashboards.",
        )

    return {
        "dashboard": dashboard_name,
        "data": response.data,
        "summary": response.summary,
        "execution_time_ms": response.execution_time_ms,
    }


@router.get(
    "/metrics/summary",
    summary="Get metrics summary",
)
async def get_metrics_summary(
    time_range: str = "30d",
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a summary of key metrics for dashboard cards.

    Returns latest DORA levels and SPACE scores.
    """
    tenant_id = str(current_user.organization_id) if current_user.organization_id else str(current_user.id)

    delta = TIME_RANGE_DELTAS.get(time_range, timedelta(days=30))
    end_time = datetime.utcnow()
    start_time = end_time - delta

    query_request = QueryRequest(
        sources=[DataSource.METRICS],
        start_time=start_time,
        end_time=end_time,
        project_id=project_id,
        include_trends=True,
    )

    gateway = get_query_gateway()
    response = await gateway.query(db, tenant_id, query_request)

    # Extract key metrics
    dora = response.data.get("metrics", {}).get("dora", {})
    space = response.data.get("metrics", {}).get("space", {})

    latest_dora = dora.get("latest", {})
    latest_space = space.get("latest", {})

    return {
        "time_range": time_range,
        "dora": {
            "overall_level": latest_dora.get("overall_level", "unknown"),
            "deployment_frequency": {
                "value": latest_dora.get("deployment_frequency"),
                "level": latest_dora.get("deployment_frequency_level"),
            },
            "lead_time": {
                "value": latest_dora.get("lead_time_hours"),
                "level": latest_dora.get("lead_time_level"),
            },
            "mttr": {
                "value": latest_dora.get("mttr_hours"),
                "level": latest_dora.get("mttr_level"),
            },
            "change_failure_rate": {
                "value": latest_dora.get("change_failure_rate"),
                "level": latest_dora.get("cfr_level"),
            },
        },
        "space": {
            "overall_score": latest_space.get("overall_score"),
            "activity": latest_space.get("activity_dimension"),
            "communication": latest_space.get("communication_dimension"),
            "efficiency": latest_space.get("efficiency_dimension"),
        },
    }


@router.get(
    "/entities/summary",
    summary="Get entity summary",
)
async def get_entity_summary(
    time_range: str = "7d",
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a summary of entity counts by type."""
    tenant_id = str(current_user.organization_id) if current_user.organization_id else str(current_user.id)

    delta = TIME_RANGE_DELTAS.get(time_range, timedelta(days=7))
    end_time = datetime.utcnow()
    start_time = end_time - delta

    query_request = QueryRequest(
        sources=[DataSource.ENTITIES],
        start_time=start_time,
        end_time=end_time,
        project_id=project_id,
    )

    gateway = get_query_gateway()
    response = await gateway.query(db, tenant_id, query_request)

    entities = response.data.get("entities", {})

    return {
        "time_range": time_range,
        "total": entities.get("total", 0),
        "by_type": entities.get("by_type", {}),
    }


@router.delete(
    "/cache",
    summary="Clear query cache",
)
async def clear_cache(
    current_user: User = Depends(get_current_user),
):
    """Clear cached query results for the current tenant."""
    tenant_id = str(current_user.organization_id) if current_user.organization_id else str(current_user.id)

    gateway = get_query_gateway()
    cleared = gateway.clear_cache(tenant_id)

    return {
        "cleared": cleared,
        "tenant_id": tenant_id,
    }
