"""Personal Access Token API Endpoints.

Provides endpoints for:
- Creating PATs
- Listing user's PATs
- Revoking PATs
- Rotating PATs
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.database import get_db

from app.core.multitenancy import get_current_tenant_id
from app.api.deps import get_current_user
from app.models.user import User
from app.models.personal_access_token import (
    pat_service,
    PATCreateRequest,
    PATCreateResponse,
    PATInfo,
    TokenScope,
)

logger = structlog.get_logger()

router = APIRouter()


@router.get("/scopes", summary="List all available token scopes with descriptions")
async def list_available_scopes() -> list[dict[str, str]]:
    """List all available token scopes with descriptions."""
    scope_descriptions = {
        TokenScope.READ_PROJECTS.value: "Read access to projects",
        TokenScope.READ_ANALYTICS.value: "Read access to analytics data",
        TokenScope.READ_METRICS.value: "Read access to metrics",
        TokenScope.READ_CONNECTIONS.value: "Read access to connections",
        TokenScope.READ_BLUEPRINTS.value: "Read access to blueprints",
        TokenScope.WRITE_PROJECTS.value: "Create and modify projects",
        TokenScope.WRITE_CONNECTIONS.value: "Create and modify connections",
        TokenScope.WRITE_BLUEPRINTS.value: "Create and modify blueprints",
        TokenScope.ADMIN_ORGANIZATION.value: "Full organization admin access",
        TokenScope.ADMIN_MEMBERS.value: "Manage organization members",
        TokenScope.FULL_ACCESS.value: "Full access to all resources",
    }

    return [
        {"scope": scope, "description": desc}
        for scope, desc in scope_descriptions.items()
    ]


@router.post("/", response_model=PATCreateResponse, status_code=status.HTTP_201_CREATED, summary="Create a new Personal Access Token")
async def create_token(
    request: PATCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> PATCreateResponse:
    """Create a new Personal Access Token.

    IMPORTANT: The token value is only returned once in this response.
    Store it securely - it cannot be retrieved again.
    """
    return await pat_service.create_token(
        session=session,
        tenant_id=tenant_id,
        user_id=str(current_user.id),
        request=request,
    )


@router.get("/", response_model=list[PATInfo], summary="List all Personal Access Tokens for the current user")
async def list_tokens(
    include_revoked: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> list[PATInfo]:
    """List all Personal Access Tokens for the current user.

    Note: Token values are never returned after creation.
    """
    return await pat_service.list_user_tokens(
        session=session,
        tenant_id=tenant_id,
        user_id=str(current_user.id),
        include_revoked=include_revoked,
        limit=limit,
        offset=offset,
    )


@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Revoke a Personal Access Token")
async def revoke_token(
    token_id: str,
    reason: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> Response:
    """Revoke a Personal Access Token.

    Once revoked, the token cannot be used for authentication.
    """
    success = await pat_service.revoke_token(
        session=session,
        token_id=token_id,
        user_id=str(current_user.id),
        reason=reason,
    )

    if not success:
        raise HTTPException(
            status_code=404,
            detail="Token not found or doesn't belong to user"
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{token_id}/rotate", response_model=PATCreateResponse, summary="Rotate a Personal Access Token")
async def rotate_token(
    token_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> PATCreateResponse:
    """Rotate a Personal Access Token.

    This revokes the old token and creates a new one with the same settings.
    Use this for regular security rotation or if you suspect a token leak.

    IMPORTANT: The new token value is only returned once in this response.
    """
    result = await pat_service.rotate_token(
        session=session,
        token_id=token_id,
        user_id=str(current_user.id),
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Token not found or doesn't belong to user"
        )

    return result


class ValidateTokenRequest(BaseModel):
    """Token validation request — accepts token in body, not query string."""

    token: str = Field(..., min_length=1)
    required_scopes: list[str] = Field(default=[])


@router.post("/validate", summary="Validate a token and check its scopes")
async def validate_token(
    request: ValidateTokenRequest,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Validate a token and check its scopes.

    This endpoint is typically used by services to verify API tokens.
    """
    pat, error = await pat_service.validate_token(
        session=session,
        token=request.token,
        required_scopes=request.required_scopes if request.required_scopes else None,
    )

    if error:
        raise HTTPException(status_code=401, detail=error)

    return {
        "valid": True,
        "token_id": str(pat.id),
        "scopes": pat.scopes,
        "expires_at": pat.expires_at.isoformat() if pat.expires_at else None,
    }
