"""Blueprint Pipeline API Endpoints.

Provides endpoints for:
- Creating and managing blueprints
- Running pipelines
- Monitoring pipeline status
"""

from datetime import datetime
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

logger = structlog.get_logger()

from app.core.database import get_db
from app.core.multitenancy import get_current_tenant_id
from app.services.devlake.blueprints import (
    blueprint_service,
    Blueprint,
    BlueprintMode,
    BlueprintStatus,
)

router = APIRouter()


# ============= Request/Response Models =============

class BlueprintCreateRequest(BaseModel):
    """Request to create a blueprint."""

    name: str
    project_id: str
    description: str | None = None
    mode: str = "NORMAL"
    cron_config: str | None = None  # e.g., "0 0 * * *" for daily
    connections: list[dict[str, Any]]


class BlueprintResponse(BaseModel):
    """Blueprint response model."""

    id: str
    name: str
    description: str | None
    mode: str
    status: str
    cron_config: str | None
    is_manual: str
    created_at: datetime
    updated_at: datetime


class BlueprintDetailResponse(BlueprintResponse):
    """Blueprint detail response with plan and settings."""

    settings: dict[str, Any] | None = None
    plan: list[list[dict[str, Any]]] | None = None
    labels: list[str] | None = None


class BlueprintStatusUpdate(BaseModel):
    """Response after updating blueprint status."""

    status: str
    new_status: str


class PipelineRunResponse(BaseModel):
    """Pipeline run response model."""

    id: str
    blueprint_id: str | None
    name: str | None
    status: str
    stage_index: str
    finished_tasks: str
    total_tasks: str
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


class PipelineCancelResponse(BaseModel):
    """Response after cancelling a pipeline."""

    status: str
    pipeline_id: str


# ============= Blueprint Endpoints =============

@router.post("/blueprints", response_model=BlueprintResponse, status_code=status.HTTP_201_CREATED)
async def create_blueprint(
    request: BlueprintCreateRequest,
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> BlueprintResponse:
    """Create a new blueprint for data collection.

    A blueprint defines:
    - Which connections/plugins to sync
    - Which scopes (repos, projects, etc.) to include
    - Scheduling (cron or manual)
    - Transformation rules
    """
    mode = BlueprintMode.ADVANCED if request.mode == "ADVANCED" else BlueprintMode.NORMAL

    blueprint = await blueprint_service.create_blueprint(
        session=session,
        tenant_id=tenant_id,
        project_id=request.project_id,
        name=request.name,
        connections=request.connections,
        cron_config=request.cron_config,
        description=request.description,
        mode=mode,
    )

    return BlueprintResponse(
        id=str(blueprint.id),
        name=blueprint.name,
        description=blueprint.description,
        mode=blueprint.mode.value,
        status=blueprint.status.value,
        cron_config=blueprint.cron_config,
        is_manual=blueprint.is_manual,
        created_at=blueprint.created_at,
        updated_at=blueprint.updated_at,
    )


@router.get("/blueprints", response_model=list[BlueprintResponse])
async def list_blueprints(
    project_id: str | None = None,
    status: str | None = None,
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> list[BlueprintResponse]:
    """List all blueprints for the tenant."""
    status_filter = None
    if status:
        try:
            status_filter = BlueprintStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {status!r}. Valid values: {[e.value for e in BlueprintStatus]}",
            )

    blueprints = await blueprint_service.list_blueprints(
        session=session,
        tenant_id=tenant_id,
        project_id=project_id,
        status=status_filter,
    )

    return [
        BlueprintResponse(
            id=str(b.id),
            name=b.name,
            description=b.description,
            mode=b.mode.value,
            status=b.status.value,
            cron_config=b.cron_config,
            is_manual=b.is_manual,
            created_at=b.created_at,
            updated_at=b.updated_at,
        )
        for b in blueprints
    ]


@router.get("/blueprints/{blueprint_id}", response_model=BlueprintDetailResponse)
async def get_blueprint(
    blueprint_id: str,
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> BlueprintDetailResponse:
    """Get a blueprint by ID with full details including plan."""
    from sqlalchemy import select

    result = await session.execute(
        select(Blueprint).where(
            Blueprint.id == blueprint_id,
            Blueprint.tenant_id == tenant_id,
        )
    )
    blueprint = result.scalar_one_or_none()

    if not blueprint:
        raise HTTPException(status_code=404, detail="Blueprint not found")

    return BlueprintDetailResponse(
        id=str(blueprint.id),
        name=blueprint.name,
        description=blueprint.description,
        mode=blueprint.mode.value,
        status=blueprint.status.value,
        cron_config=blueprint.cron_config,
        is_manual=blueprint.is_manual,
        settings=blueprint.settings,
        plan=blueprint.plan,
        labels=blueprint.labels,
        created_at=blueprint.created_at,
        updated_at=blueprint.updated_at,
    )


@router.patch("/blueprints/{blueprint_id}/status", response_model=BlueprintStatusUpdate)
async def update_blueprint_status(
    blueprint_id: str,
    new_status: str = Query(..., alias="status", pattern="^(ACTIVE|PAUSED|DISABLED)$"),
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> BlueprintStatusUpdate:
    """Update blueprint status (ACTIVE, PAUSED, DISABLED)."""
    from sqlalchemy import select

    result = await session.execute(
        select(Blueprint).where(
            Blueprint.id == blueprint_id,
            Blueprint.tenant_id == tenant_id,
        )
    )
    blueprint = result.scalar_one_or_none()

    if not blueprint:
        raise HTTPException(status_code=404, detail="Blueprint not found")

    blueprint.status = BlueprintStatus(new_status)
    blueprint.updated_at = datetime.utcnow()
    await session.commit()

    return BlueprintStatusUpdate(status="updated", new_status=new_status)


@router.delete("/blueprints/{blueprint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_blueprint(
    blueprint_id: str,
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> Response:
    """Delete a blueprint."""
    from sqlalchemy import select

    result = await session.execute(
        select(Blueprint).where(
            Blueprint.id == blueprint_id,
            Blueprint.tenant_id == tenant_id,
        )
    )
    blueprint = result.scalar_one_or_none()

    if not blueprint:
        raise HTTPException(status_code=404, detail="Blueprint not found")

    await session.delete(blueprint)
    await session.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============= Pipeline Run Endpoints =============

@router.post("/blueprints/{blueprint_id}/run", response_model=PipelineRunResponse)
async def run_blueprint(
    blueprint_id: str,
    full_sync: bool = Query(default=False),
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> PipelineRunResponse:
    """Trigger a pipeline run from a blueprint.

    Args:
        blueprint_id: Blueprint to run
        full_sync: Whether to do a full sync (vs incremental)
    """
    try:
        pipeline_run = await blueprint_service.run_blueprint(
            session=session,
            blueprint_id=blueprint_id,
            full_sync=full_sync,
        )

        return PipelineRunResponse(
            id=str(pipeline_run.id),
            blueprint_id=str(pipeline_run.blueprint_id) if pipeline_run.blueprint_id else None,
            name=pipeline_run.name,
            status=pipeline_run.status.value,
            stage_index=pipeline_run.stage_index,
            finished_tasks=pipeline_run.finished_tasks,
            total_tasks=pipeline_run.total_tasks,
            error_message=pipeline_run.error_message,
            started_at=pipeline_run.started_at,
            finished_at=pipeline_run.finished_at,
            created_at=pipeline_run.created_at,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Pipeline not found or invalid configuration.")


@router.get("/pipelines/{pipeline_id}", response_model=PipelineRunResponse)
async def get_pipeline_status(
    pipeline_id: str,
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> PipelineRunResponse:
    """Get pipeline run status."""
    pipeline = await blueprint_service.get_pipeline_status(
        session=session,
        pipeline_id=pipeline_id,
    )

    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    return PipelineRunResponse(
        id=str(pipeline.id),
        blueprint_id=str(pipeline.blueprint_id) if pipeline.blueprint_id else None,
        name=pipeline.name,
        status=pipeline.status.value,
        stage_index=pipeline.stage_index,
        finished_tasks=pipeline.finished_tasks,
        total_tasks=pipeline.total_tasks,
        error_message=pipeline.error_message,
        started_at=pipeline.started_at,
        finished_at=pipeline.finished_at,
        created_at=pipeline.created_at,
    )


@router.post("/pipelines/{pipeline_id}/cancel", response_model=PipelineCancelResponse)
async def cancel_pipeline(
    pipeline_id: str,
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> PipelineCancelResponse:
    """Cancel a running pipeline."""
    success = await blueprint_service.cancel_pipeline(
        session=session,
        pipeline_id=pipeline_id,
    )

    if not success:
        raise HTTPException(
            status_code=400,
            detail="Pipeline not found or not in running state"
        )

    return PipelineCancelResponse(status="cancelled", pipeline_id=pipeline_id)


@router.get("/blueprints/{blueprint_id}/history", response_model=list[PipelineRunResponse])
async def get_pipeline_history(
    blueprint_id: str,
    limit: int = Query(default=10, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> list[PipelineRunResponse]:
    """Get pipeline run history for a blueprint."""
    pipelines = await blueprint_service.get_pipeline_history(
        session=session,
        blueprint_id=blueprint_id,
        limit=limit,
    )

    return [
        PipelineRunResponse(
            id=str(p.id),
            blueprint_id=str(p.blueprint_id) if p.blueprint_id else None,
            name=p.name,
            status=p.status.value,
            stage_index=p.stage_index,
            finished_tasks=p.finished_tasks,
            total_tasks=p.total_tasks,
            error_message=p.error_message,
            started_at=p.started_at,
            finished_at=p.finished_at,
            created_at=p.created_at,
        )
        for p in pipelines
    ]
