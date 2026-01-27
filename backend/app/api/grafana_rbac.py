"""
Grafana RBAC API endpoints.

Provides endpoints for:
- User synchronization
- Role assignment
- Dashboard access control
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.grafana.rbac import get_grafana_rbac_service

logger = structlog.get_logger()

router = APIRouter()


class SyncUserRequest(BaseModel):
    """Request to sync user to Grafana."""

    role: str = "Viewer"  # Admin, Editor, Viewer
    org_id: int = 1


class AssignRoleRequest(BaseModel):
    """Request to assign Grafana role."""

    user_id: int
    role: str
    org_id: int = 1


@router.post("/sync-user")
async def sync_user_to_grafana(
    request: SyncUserRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Sync NexusAI user to Grafana with appropriate role.
    
    Creates or updates Grafana user based on NexusAI user permissions.
    """
    service = get_grafana_rbac_service()
    
    if not await service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Grafana is not available",
        )
    
    grafana_user = await service.sync_user(
        user_id=str(user.id),
        email=user.email,
        name=user.full_name or user.email,
        role=request.role,
        org_id=request.org_id,
    )
    
    if not grafana_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync user to Grafana",
        )
    
    return {
        "success": True,
        "grafana_user_id": grafana_user.id,
        "email": grafana_user.email,
        "role": request.role,
    }


@router.post("/assign-role")
async def assign_grafana_role(
    request: AssignRoleRequest,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Assign role to Grafana user.
    
    Updates user's role in Grafana organization.
    """
    service = get_grafana_rbac_service()
    
    if not await service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Grafana is not available",
        )
    
    success = await service.assign_role(
        user_id=request.user_id,
        role=request.role,
        org_id=request.org_id,
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign role",
        )
    
    return {
        "success": True,
        "user_id": request.user_id,
        "role": request.role,
        "org_id": request.org_id,
    }


@router.post("/sync-permissions")
async def sync_user_permissions(
    project_id: str | None = None,
    organization_id: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Sync user permissions from NexusAI to Grafana.
    
    Checks OpenFGA permissions and assigns appropriate Grafana role.
    """
    service = get_grafana_rbac_service()
    
    if not await service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Grafana is not available",
        )
    
    success = await service.sync_user_permissions(
        nexusai_user_id=str(user.id),
        project_id=project_id,
        organization_id=organization_id,
    )
    
    return {
        "success": success,
        "user_id": str(user.id),
        "project_id": project_id,
        "organization_id": organization_id,
    }


@router.get("/health")
async def grafana_rbac_health(
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Check Grafana RBAC service health."""
    service = get_grafana_rbac_service()
    is_available = await service.is_available()
    
    return {
        "available": is_available,
        "grafana_url": service.base_url,
        "enabled": service._enabled,
    }
