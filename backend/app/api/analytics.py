"""Analytics API endpoints - DevLake integration."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import structlog

from app.api.deps import get_current_user
from app.models.user import User
from app.services.devlake import DORAMetrics, devlake_service

logger = structlog.get_logger()

router = APIRouter()


# ======================
# Response Models
# ======================


class HealthResponse(BaseModel):
    """DevLake health check response."""

    devlake_available: bool
    message: str


class ProjectResponse(BaseModel):
    """Project response model."""

    name: str
    description: str | None = None


class ConnectionResponse(BaseModel):
    """Connection response model."""

    id: int
    name: str
    plugin: str
    endpoint: str | None = None


class PipelineResponse(BaseModel):
    """Pipeline response model."""

    id: int
    name: str
    status: str
    message: str | None = None
    created_at: str | None = None


class PluginResponse(BaseModel):
    """Plugin response model."""

    name: str
    description: str | None = None


# ======================
# Request Models
# ======================


class CreateProjectRequest(BaseModel):
    """Create project request."""

    name: str
    description: str | None = None


class CreateConnectionRequest(BaseModel):
    """Create connection request."""

    name: str
    endpoint: str
    token: str | None = None


# ======================
# Endpoints
# ======================


@router.get("/health", response_model=HealthResponse)
async def check_devlake_health(
    _: User = Depends(get_current_user),
) -> HealthResponse:
    """Check if DevLake is available."""
    is_healthy = await devlake_service.health_check()

    return HealthResponse(
        devlake_available=is_healthy,
        message="DevLake is running" if is_healthy else "DevLake is not available",
    )


# ======================
# Projects
# ======================


@router.get("/projects")
async def list_projects(
    _: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List all DevLake projects."""
    try:
        return await devlake_service.list_projects()
    except Exception as e:
        logger.error("Failed to fetch projects from DevLake", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analytics service is temporarily unavailable. Please try again later.",
        )


@router.get("/projects/{project_name}")
async def get_project(
    project_name: str,
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get a specific project."""
    try:
        project = await devlake_service.get_project(project_name)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_name}' not found",
            )
        return project
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to fetch project from DevLake", project=project_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analytics service is temporarily unavailable. Please try again later.",
        )


@router.post("/projects", status_code=status.HTTP_201_CREATED)
async def create_project(
    request: CreateProjectRequest,
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Create a new project in DevLake."""
    try:
        return await devlake_service.create_project(
            name=request.name,
            description=request.description,
        )
    except Exception as e:
        logger.error("Failed to create project in DevLake", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analytics service is temporarily unavailable. Please try again later.",
        )


# ======================
# DORA Metrics
# ======================


@router.get("/projects/{project_name}/dora", response_model=DORAMetrics)
async def get_dora_metrics(
    project_name: str,
    time_range: str = "past_6_months",
    _: User = Depends(get_current_user),
) -> DORAMetrics:
    """
    Get DORA metrics for a project.

    DORA metrics include:
    - Deployment Frequency: How often code is deployed to production
    - Lead Time for Changes: Time from commit to production
    - Mean Time to Recovery: Time to restore service after an incident
    - Change Failure Rate: Percentage of deployments causing failures
    """
    try:
        return await devlake_service.get_dora_metrics(project_name, time_range)
    except Exception as e:
        logger.error("Failed to fetch DORA metrics", project=project_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analytics service is temporarily unavailable. Please try again later.",
        )


# ======================
# Connections
# ======================


@router.get("/connections")
async def list_connections(
    plugin: str | None = None,
    _: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List all connections, optionally filtered by plugin."""
    try:
        return await devlake_service.list_connections(plugin)
    except Exception as e:
        logger.error("Failed to fetch connections", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analytics service is temporarily unavailable. Please try again later.",
        )


@router.get("/plugins/{plugin}/connections/{connection_id}")
async def get_connection(
    plugin: str,
    connection_id: int,
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get a specific connection."""
    try:
        return await devlake_service.get_connection(plugin, connection_id)
    except Exception as e:
        logger.error("Failed to fetch connection", plugin=plugin, connection_id=connection_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analytics service is temporarily unavailable. Please try again later.",
        )


@router.post("/plugins/{plugin}/connections", status_code=status.HTTP_201_CREATED)
async def create_connection(
    plugin: str,
    request: CreateConnectionRequest,
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Create a new connection for a plugin."""
    try:
        return await devlake_service.create_connection(
            plugin=plugin,
            name=request.name,
            endpoint=request.endpoint,
            token=request.token,
        )
    except Exception as e:
        logger.error("Failed to create connection", plugin=plugin, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analytics service is temporarily unavailable. Please try again later.",
        )


@router.post("/plugins/{plugin}/connections/{connection_id}/test")
async def test_connection(
    plugin: str,
    connection_id: int,
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Test a connection."""
    try:
        return await devlake_service.test_connection(plugin, connection_id)
    except Exception as e:
        logger.error("Failed to test connection", plugin=plugin, connection_id=connection_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Connection test failed. Please verify the connection settings and try again.",
        )


# ======================
# Blueprints
# ======================


@router.get("/blueprints")
async def list_blueprints(
    _: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List all blueprints."""
    try:
        return await devlake_service.list_blueprints()
    except Exception as e:
        logger.error("Failed to fetch blueprints", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analytics service is temporarily unavailable. Please try again later.",
        )


@router.get("/blueprints/{blueprint_id}")
async def get_blueprint(
    blueprint_id: int,
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get a specific blueprint."""
    try:
        return await devlake_service.get_blueprint(blueprint_id)
    except Exception as e:
        logger.error("Failed to fetch blueprint", blueprint_id=blueprint_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analytics service is temporarily unavailable. Please try again later.",
        )


@router.post("/blueprints/{blueprint_id}/trigger")
async def trigger_blueprint(
    blueprint_id: int,
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Trigger a blueprint to run."""
    try:
        return await devlake_service.trigger_blueprint(blueprint_id)
    except Exception as e:
        logger.error("Failed to trigger blueprint", blueprint_id=blueprint_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analytics service is temporarily unavailable. Please try again later.",
        )


# ======================
# Pipelines
# ======================


@router.get("/pipelines")
async def list_pipelines(
    page: int = 1,
    page_size: int = 20,
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    """List pipelines with pagination."""
    try:
        return await devlake_service.list_pipelines(page, page_size)
    except Exception as e:
        logger.error("Failed to fetch pipelines", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analytics service is temporarily unavailable. Please try again later.",
        )


@router.get("/pipelines/{pipeline_id}")
async def get_pipeline(
    pipeline_id: int,
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get a specific pipeline."""
    try:
        return await devlake_service.get_pipeline(pipeline_id)
    except Exception as e:
        logger.error("Failed to fetch pipeline", pipeline_id=pipeline_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analytics service is temporarily unavailable. Please try again later.",
        )


@router.delete("/pipelines/{pipeline_id}")
async def cancel_pipeline(
    pipeline_id: int,
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Cancel a running pipeline."""
    try:
        return await devlake_service.cancel_pipeline(pipeline_id)
    except Exception as e:
        logger.error("Failed to cancel pipeline", pipeline_id=pipeline_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analytics service is temporarily unavailable. Please try again later.",
        )


# ======================
# Plugins
# ======================


@router.get("/plugins")
async def list_plugins(
    _: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List all available DevLake plugins."""
    try:
        return await devlake_service.list_plugins()
    except Exception as e:
        logger.error("Failed to fetch plugins", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analytics service is temporarily unavailable. Please try again later.",
        )


@router.get("/plugins/{plugin}")
async def get_plugin(
    plugin: str,
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get details about a specific plugin."""
    try:
        return await devlake_service.get_plugin(plugin)
    except Exception as e:
        logger.error("Failed to fetch plugin details", plugin=plugin, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analytics service is temporarily unavailable. Please try again later.",
        )
