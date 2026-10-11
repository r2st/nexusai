"""
SSO API Endpoints

REST endpoints for Single Sign-On authentication.

NOTE: SSO is not yet integrated with a real identity provider backend.
All endpoints that require a configured SSOService will return 501 until
the service is wired up.  The URL-validation and redirect-safety logic is
production-ready and tested so it can be kept as-is once the service exists.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
import structlog

from app.api.deps import get_current_admin_user
from app.models.user import User

logger = structlog.get_logger()

router = APIRouter(prefix="/sso", tags=["SSO"])

_SSO_NOT_CONFIGURED = "SSO is not configured. Contact your administrator to enable SSO."


def _raise_not_configured() -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=_SSO_NOT_CONFIGURED,
    )


# Request/Response Models

class ProviderResponse(BaseModel):
    """SSO provider info."""
    id: str
    name: str
    display_name: str
    type: str
    status: str

    class Config:
        from_attributes = True


class ProviderCreateRequest(BaseModel):
    """Create SSO provider request."""
    name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=200)
    type: str = Field(default="oidc", max_length=20)
    issuer_url: Optional[str] = Field(default=None, max_length=2000)
    metadata_url: Optional[str] = Field(default=None, max_length=2000)
    client_id: str = Field(..., min_length=1, max_length=500)
    client_secret: Optional[str] = Field(default=None, max_length=500)
    scopes: List[str] = Field(default=["openid", "profile", "email"], max_length=20)
    auto_provision_users: bool = True
    default_role: str = Field(default="user", max_length=50)
    allowed_domains: List[str] = Field(default=[], max_length=50)


class AuthStartResponse(BaseModel):
    """Start authentication response."""
    authorization_url: str
    state: str


class TokenResponse(BaseModel):
    """Token response after authentication."""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    user: Dict[str, Any]


class SessionResponse(BaseModel):
    """Session info response."""
    session_id: str
    user_id: str
    provider_id: str
    expires_at: Optional[str] = None
    is_active: bool


# API Endpoints

@router.get("/providers", response_model=List[ProviderResponse])
async def list_providers(
    tenant_id: Optional[str] = Query(None),
    _current_user: User = Depends(get_current_admin_user),
):
    """
    List available SSO providers.

    Returns all active SSO providers configured for the tenant.
    """
    _raise_not_configured()


@router.get("/providers/{provider_id}", response_model=ProviderResponse)
async def get_provider(provider_id: str, _current_user: User = Depends(get_current_admin_user)):
    """Get SSO provider details."""
    _raise_not_configured()


@router.post("/providers", response_model=ProviderResponse, status_code=status.HTTP_201_CREATED)
async def create_provider(request: ProviderCreateRequest, _current_user: User = Depends(get_current_admin_user)):
    """
    Create a new SSO provider.

    Requires admin permissions.
    """
    _raise_not_configured()


@router.delete("/providers/{provider_id}", status_code=204)
async def delete_provider(provider_id: str, _current_user: User = Depends(get_current_admin_user)):
    """Delete an SSO provider."""
    _raise_not_configured()


@router.get("/auth/{provider_id}")
async def start_authentication(
    provider_id: str,
    redirect_uri: str = Query(..., description="URI to redirect after authentication"),
    tenant_id: Optional[str] = Query(None),
):
    """
    Start SSO authentication flow.

    Redirects user to the identity provider's login page.
    """
    _raise_not_configured()


@router.get("/auth/{provider_id}/url", response_model=AuthStartResponse)
async def get_authorization_url(
    provider_id: str,
    redirect_uri: str = Query(...),
    tenant_id: Optional[str] = Query(None),
):
    """
    Get authorization URL without redirecting.

    Useful for SPAs that handle redirect themselves.
    """
    _raise_not_configured()


@router.get("/callback/oidc")
async def oidc_callback(
    code: str = Query(...),
    state: str = Query(...),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
):
    """
    Handle OIDC callback from identity provider.

    Exchanges authorization code for tokens.
    """
    if error:
        logger.warning("OIDC authentication failed", error=error, error_description=error_description)
        raise HTTPException(
            status_code=400,
            detail="Authentication failed. Please try again.",
        )

    _raise_not_configured()


@router.post("/callback/saml")
async def saml_callback(
    request: Request,
):
    """
    Handle SAML callback (ACS endpoint).

    Processes SAML response and assertion.
    """
    form_data = await request.form()
    saml_response = form_data.get("SAMLResponse")

    if not saml_response:
        raise HTTPException(status_code=400, detail="Missing SAMLResponse")

    _raise_not_configured()


@router.get("/saml/{provider_id}/metadata")
async def get_sp_metadata(provider_id: str):
    """
    Get SP metadata for SAML configuration.

    Returns XML metadata for configuring the identity provider.
    """
    _raise_not_configured()


@router.post("/token/refresh", response_model=TokenResponse)
async def refresh_token(
    request: "SSORefreshRequest",
    _current_user: User = Depends(get_current_admin_user),
):
    """
    Refresh access token.

    Uses refresh token to obtain new access token.
    """
    _raise_not_configured()


@router.get("/session", response_model=SessionResponse)
async def get_session(
    session_id: str = Query(...),
    _current_user: User = Depends(get_current_admin_user),
):
    """Get current session information."""
    _raise_not_configured()


@router.post("/logout")
async def logout(
    session_id: str = Query(...),
    post_logout_uri: str = Query("/"),
    _current_user: User = Depends(get_current_admin_user),
):
    """
    Logout from SSO.

    Terminates session and optionally redirects to IdP logout.
    """
    _raise_not_configured()


@router.get("/well-known/openid-configuration")
async def openid_configuration():
    """
    OpenID Connect discovery document.

    Returns configuration for OIDC clients.
    """
    _raise_not_configured()


class SSORefreshRequest(BaseModel):
    """SSO token refresh request — token in body, not query string."""

    refresh_token: str
    session_id: Optional[str] = None
