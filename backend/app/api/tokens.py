"""Personal Access Token API Endpoints.

Provides endpoints for:
- Creating PATs
- Listing user's PATs
- Revoking PATs
- Rotating PATs
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.database import get_db

logger = structlog.get_logger()
from app.core.multitenancy import get_current_tenant_id
from app.models.personal_access_token import (
    pat_service,
    PATCreateRequest,
    PATCreateResponse,
    PATInfo,
    TokenScope,
)

router = APIRouter()


@router.get("/scopes")
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


@router.post("/", response_model=PATCreateResponse)
async def create_token(
    request: PATCreateRequest,
    user_id: str = Query(..., description="Current user ID"),  # In production, from auth
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> PATCreateResponse:
    """Create a new Personal Access Token.

    IMPORTANT: The token value is only returned once in this response.
    Store it securely - it cannot be retrieved again.

    Args:
        request: Token creation request
        user_id: Current user ID

    Returns:
        Token details including the secret token (shown only once)
    """
    return await pat_service.create_token(
        session=session,
        tenant_id=tenant_id,
        user_id=user_id,
        request=request,
    )


@router.get("/", response_model=list[PATInfo])
async def list_tokens(
    user_id: str = Query(..., description="Current user ID"),
    include_revoked: bool = Query(default=False),
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> list[PATInfo]:
    """List all Personal Access Tokens for the current user.

    Note: Token values are never returned after creation.
    """
    return await pat_service.list_user_tokens(
        session=session,
        tenant_id=tenant_id,
        user_id=user_id,
        include_revoked=include_revoked,
    )


@router.delete("/{token_id}")
async def revoke_token(
    token_id: str,
    user_id: str = Query(..., description="Current user ID"),
    reason: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> dict[str, Any]:
    """Revoke a Personal Access Token.

    Once revoked, the token cannot be used for authentication.
    """
    success = await pat_service.revoke_token(
        session=session,
        token_id=token_id,
        user_id=user_id,
        reason=reason,
    )

    if not success:
        raise HTTPException(
            status_code=404,
            detail="Token not found or doesn't belong to user"
        )

    return {"status": "revoked", "token_id": token_id}


@router.post("/{token_id}/rotate", response_model=PATCreateResponse)
async def rotate_token(
    token_id: str,
    user_id: str = Query(..., description="Current user ID"),
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
        user_id=user_id,
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Token not found or doesn't belong to user"
        )

    return result


@router.post("/validate")
async def validate_token(
    token: str = Query(..., description="Token to validate"),
    required_scopes: list[str] = Query(default=[]),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Validate a token and check its scopes.

    This endpoint is typically used by services to verify API tokens.
    """
    pat, error = await pat_service.validate_token(
        session=session,
        token=token,
        required_scopes=required_scopes if required_scopes else None,
    )

    if error:
        raise HTTPException(status_code=401, detail=error)

    return {
        "valid": True,
        "token_id": str(pat.id),
        "scopes": pat.scopes,
        "expires_at": pat.expires_at.isoformat() if pat.expires_at else None,
    }
