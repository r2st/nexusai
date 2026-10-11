"""API endpoints for precomputed metric rollups."""

from datetime import UTC, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.services.rollups import (
    RollupGranularity,
    RollupQuery,
    get_rollup_service,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/rollups", tags=["rollups"])


# Request/Response models
class RollupQueryRequest(BaseModel):
    """Request for querying rollups."""

    metric_type: str = Field(default="dora", description="dora or space")
    granularity: RollupGranularity = Field(default=RollupGranularity.DAILY)
    start_date: datetime
    end_date: datetime
    project_id: str | None = None
    team_id: str | None = None
    include_partial: bool = False


class ComputeRollupRequest(BaseModel):
    """Request for computing rollups on demand."""

    granularity: RollupGranularity = Field(default=RollupGranularity.DAILY)
    project_id: str | None = None


class BackfillRequest(BaseModel):
    """Request for backfilling rollups."""

    start_date: datetime
    end_date: datetime
    granularities: list[RollupGranularity] = Field(
        default=[RollupGranularity.DAILY, RollupGranularity.WEEKLY]
    )


@router.get(
    "/dora",
    summary="Get DORA metric rollups",
)
async def get_dora_rollups(
    granularity: RollupGranularity = RollupGranularity.DAILY,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    project_id: str | None = None,
    team_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get precomputed DORA metric rollups.

    Returns deployment frequency, lead time, MTTR, and change failure rate
    aggregated at the specified granularity.
    """
    tenant_id = str(current_user.organization_id) if current_user.organization_id else str(current_user.id)

    # Default to last 30 days
    end_date = end_date or datetime.now(UTC)
    start_date = start_date or (end_date - timedelta(days=30))

    query = RollupQuery(
        tenant_id=tenant_id,
        metric_type="dora",
        granularity=granularity,
        start_date=start_date,
        end_date=end_date,
        project_id=project_id,
        team_id=team_id,
    )

    service = get_rollup_service()
    rollups = await service.query_rollups(db, query)

    return {
        "metric_type": "dora",
        "granularity": granularity.value,
        "period": {
            "start": start_date,
            "end": end_date,
        },
        "data": rollups,
    }


@router.get(
    "/space",
    summary="Get SPACE metric rollups",
)
async def get_space_rollups(
    granularity: RollupGranularity = RollupGranularity.DAILY,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    project_id: str | None = None,
    team_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get precomputed SPACE framework metric rollups.

    Returns satisfaction, performance, activity, communication, and
    efficiency metrics aggregated at the specified granularity.
    """
    tenant_id = str(current_user.organization_id) if current_user.organization_id else str(current_user.id)

    end_date = end_date or datetime.now(UTC)
    start_date = start_date or (end_date - timedelta(days=30))

    query = RollupQuery(
        tenant_id=tenant_id,
        metric_type="space",
        granularity=granularity,
        start_date=start_date,
        end_date=end_date,
        project_id=project_id,
        team_id=team_id,
    )

    service = get_rollup_service()
    rollups = await service.query_rollups(db, query)

    return {
        "metric_type": "space",
        "granularity": granularity.value,
        "period": {
            "start": start_date,
            "end": end_date,
        },
        "data": rollups,
    }


@router.post(
    "/compute",
    summary="Compute rollups on demand",
)
async def compute_rollups(
    request: ComputeRollupRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> result:
    """Compute rollups for the current period on demand.

    Useful for getting fresh metrics without waiting for the scheduled
    computation.
    """
    tenant_id = str(current_user.organization_id) if current_user.organization_id else str(current_user.id)

    from app.services.rollups.worker import RollupWorker
    from app.core.database import async_session_factory

    worker = RollupWorker(get_session=async_session_factory)
    result = await worker.compute_now(
        tenant_id=tenant_id,
        granularity=request.granularity,
        project_id=request.project_id,
    )

    return result


@router.post(
    "/backfill",
    summary="Backfill historical rollups",
)
async def backfill_rollups(
    request: BackfillRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> result:
    """Backfill rollups for a historical time range.

    Use this to compute rollups for past periods after initial setup
    or to recover from missing data.
    """
    tenant_id = str(current_user.organization_id) if current_user.organization_id else str(current_user.id)

    # Validate date range
    if request.end_date <= request.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date must be after start_date",
        )

    max_range = timedelta(days=365)
    if request.end_date - request.start_date > max_range:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum backfill range is 365 days",
        )

    from app.services.rollups.worker import RollupWorker
    from app.core.database import async_session_factory

    worker = RollupWorker(get_session=async_session_factory)
    result = await worker.backfill(
        tenant_id=tenant_id,
        start_date=request.start_date,
        end_date=request.end_date,
        granularities=request.granularities,
    )

    return result


@router.get(
    "/stats",
    summary="Get rollup statistics",
)
async def get_rollup_stats(
    metric_type: str = "dora",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get statistics about available rollups.

    Returns counts and date ranges for stored rollups.
    """
    tenant_id = str(current_user.organization_id) if current_user.organization_id else str(current_user.id)

    service = get_rollup_service()
    stats = await service.get_stats(db, tenant_id, metric_type)

    return {
        "tenant_id": stats.tenant_id,
        "metric_type": stats.metric_type,
        "total_rollups": stats.total_rollups,
        "latest_rollup_at": stats.latest_rollup_at,
        "oldest_rollup_at": stats.oldest_rollup_at,
        "coverage": stats.coverage,
    }


@router.get(
    "/latest",
    summary="Get latest rollup values",
)
async def get_latest_rollups(
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get the most recent DORA and SPACE rollup values.

    Useful for dashboard summary cards.
    """
    tenant_id = str(current_user.organization_id) if current_user.organization_id else str(current_user.id)

    service = get_rollup_service()
    now = datetime.now(UTC)

    # Get latest daily rollups
    dora_query = RollupQuery(
        tenant_id=tenant_id,
        metric_type="dora",
        granularity=RollupGranularity.DAILY,
        start_date=now - timedelta(days=7),
        end_date=now,
        project_id=project_id,
        include_partial=True,
    )
    space_query = RollupQuery(
        tenant_id=tenant_id,
        metric_type="space",
        granularity=RollupGranularity.DAILY,
        start_date=now - timedelta(days=7),
        end_date=now,
        project_id=project_id,
        include_partial=True,
    )

    dora_rollups = await service.query_rollups(db, dora_query)
    space_rollups = await service.query_rollups(db, space_query)

    # Get the most recent non-empty rollup
    latest_dora = next(
        (r for r in reversed(dora_rollups) if not r.get("no_data")),
        None,
    )
    latest_space = next(
        (r for r in reversed(space_rollups) if not r.get("no_data")),
        None,
    )

    return {
        "dora": latest_dora,
        "space": latest_space,
        "as_of": now,
    }
