"""DevLake API endpoints.

Provides endpoints for querying DevLake pipeline status and metrics.
These endpoints proxy requests to the DevLake service for frontend polling.
"""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.devlake.service import devlake_service


def _calculate_spent_seconds(began_at: str | None, finished_at: str | None) -> int:
    """Calculate spent seconds from beganAt timestamp.

    If the pipeline is still running (finishedAt is None), calculate
    elapsed time from beganAt to now. Otherwise calculate the difference
    between beganAt and finishedAt.
    """
    if not began_at:
        return 0

    try:
        # Parse the beganAt timestamp (DevLake uses ISO format)
        # Handle both with and without timezone info
        began_at_clean = began_at.replace("Z", "+00:00")
        start_time = datetime.fromisoformat(began_at_clean)

        if finished_at:
            # Pipeline completed - calculate total duration
            finished_at_clean = finished_at.replace("Z", "+00:00")
            end_time = datetime.fromisoformat(finished_at_clean)
        else:
            # Pipeline still running - calculate time until now
            end_time = datetime.now(timezone.utc)

        # Make sure start_time is timezone-aware
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)

        elapsed = end_time - start_time
        return max(0, int(elapsed.total_seconds()))
    except (ValueError, TypeError) as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to parse beganAt timestamp '{began_at}': {e}")
        return 0

router = APIRouter(prefix="/devlake", tags=["devlake"])


class PipelineStatusResponse(BaseModel):
    """Pipeline status response for frontend polling."""

    id: int
    name: str
    status: str
    progress: int
    totalTasks: int
    finishedTasks: int
    spentSeconds: int
    message: str | None = None
    errorName: str | None = None
    beganAt: str | None = None
    finishedAt: str | None = None


@router.get("/pipelines/{pipeline_id}", response_model=PipelineStatusResponse)
async def get_pipeline_status(pipeline_id: int) -> dict[str, Any]:
    """Get pipeline status for progress tracking.

    This endpoint is used by the frontend to poll for pipeline progress updates.
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        pipeline = await devlake_service.get_pipeline(pipeline_id)
        logger.debug(f"Pipeline {pipeline_id} data: {pipeline}")

        # Calculate progress percentage
        total_tasks = pipeline.get("totalTasks", 1)
        finished_tasks = pipeline.get("finishedTasks", 0)
        progress = int((finished_tasks / total_tasks * 100) if total_tasks > 0 else 0)

        # Get spentSeconds from DevLake, or calculate it from beganAt if not provided
        began_at = pipeline.get("beganAt")
        finished_at = pipeline.get("finishedAt")
        spent_seconds = pipeline.get("spentSeconds")

        # If DevLake doesn't provide spentSeconds, calculate from timestamps
        if spent_seconds is None or spent_seconds == 0:
            spent_seconds = _calculate_spent_seconds(began_at, finished_at)

        result = {
            "id": pipeline.get("id"),
            "name": pipeline.get("name", ""),
            "status": pipeline.get("status", "TASK_CREATED"),
            "progress": progress,
            "totalTasks": total_tasks,
            "finishedTasks": finished_tasks,
            "spentSeconds": spent_seconds,
            "message": pipeline.get("message"),
            "errorName": pipeline.get("errorName"),
            "beganAt": began_at,
            "finishedAt": finished_at,
        }
        logger.debug(f"Pipeline {pipeline_id} response: {result}")
        return result
    except Exception as e:
        logger.error(f"Failed to get pipeline {pipeline_id} status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get pipeline status: {str(e)}",
        )


@router.get("/pipelines/{pipeline_id}/tasks")
async def get_pipeline_tasks(pipeline_id: int) -> dict[str, Any]:
    """Get pipeline tasks for detailed progress information."""
    try:
        # Use the DevLake service to get task details
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{devlake_service.base_url}/pipelines/{pipeline_id}/tasks"
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get pipeline tasks: {str(e)}",
        )


@router.get("/health")
async def devlake_health() -> dict[str, Any]:
    """Check DevLake service health."""
    try:
        is_healthy = await devlake_service.health_check()
        return {
            "healthy": is_healthy,
            "base_url": devlake_service.base_url,
        }
    except Exception as e:
        return {
            "healthy": False,
            "base_url": devlake_service.base_url,
            "error": str(e),
        }
