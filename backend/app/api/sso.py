"""
SSO API Endpoints

REST endpoints for Single Sign-On authentication.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field, field_validator
from urllib.parse import urlparse as _urlparse
import structlog

from app.api.deps import get_current_admin_user
from app.models.user import User

logger = structlog.get_logger()

router = APIRouter(prefix="/sso", tags=["SSO"])


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
    # In production, inject SSOService
    # sso_service = get_sso_service()
    # providers = sso_service.list_providers(tenant_id)
    
    # Mock response
    return [
        ProviderResponse(
            id="google-workspace",
            name="google",
            display_name="Google Workspace",
            type="oidc",
            status="active",
        ),
        ProviderResponse(
            id="azure-ad",
            name="microsoft",
            display_name="Microsoft Entra ID",
            type="oidc",
            status="active",
        ),
    ]


@router.get("/providers/{provider_id}", response_model=ProviderResponse)
async def get_provider(provider_id: str, _current_user: User = Depends(get_current_admin_user)):
    """Get SSO provider details."""
    # sso_service = get_sso_service()
    # provider = sso_service.get_provider(provider_id)
    
    return ProviderResponse(
        id=provider_id,
        name="google",
        display_name="Google Workspace",
        type="oidc",
        status="active",
    )


@router.post("/providers", response_model=ProviderResponse, status_code=status.HTTP_201_CREATED)
async def create_provider(request: ProviderCreateRequest, _current_user: User = Depends(get_current_admin_user)):
    """
    Create a new SSO provider.

    Requires admin permissions.
    """
    # sso_service = get_sso_service()
    # provider = await sso_service.create_provider(request)
    
    return ProviderResponse(
        id="new-provider-id",
        name=request.name,
        display_name=request.display_name,
        type=request.type,
        status="pending",
    )


@router.delete("/providers/{provider_id}", status_code=204)
async def delete_provider(provider_id: str, _current_user: User = Depends(get_current_admin_user)):
    """Delete an SSO provider."""
    # sso_service = get_sso_service()
    # await sso_service.delete_provider(provider_id)

    return Response(status_code=204)


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
    # sso_service = get_sso_service()
    # auth_url = await sso_service.start_authentication(
    #     provider_id, redirect_uri, tenant_id
    # )
    
    parsed = _urlparse(redirect_uri)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise HTTPException(status_code=400, detail="Invalid redirect_uri")

    from app.core.config import settings
    allowed_origins = settings.CORS_ORIGINS
    origin = f"{parsed.scheme}://{parsed.netloc}"
    if allowed_origins and origin not in allowed_origins:
        raise HTTPException(status_code=400, detail="redirect_uri not in allowed origins")

    # For now, return mock URL
    from urllib.parse import urlencode as _urlencode
    params = _urlencode({
        "response_type": "code",
        "client_id": "xxx",
        "redirect_uri": redirect_uri,
        "scope": "openid email profile",
        "state": "mock_state",
    })
    auth_url = f"https://accounts.google.com/o/oauth2/auth?{params}"

    return RedirectResponse(url=auth_url)


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
    from app.core.config import settings

    parsed = _urlparse(redirect_uri)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise HTTPException(status_code=400, detail="Invalid redirect_uri")
    origin = f"{parsed.scheme}://{parsed.netloc}"
    if settings.CORS_ORIGINS and origin not in settings.CORS_ORIGINS:
        raise HTTPException(status_code=400, detail="redirect_uri not in allowed origins")

    return AuthStartResponse(
        authorization_url=f"https://accounts.google.com/o/oauth2/auth?...",
        state="mock_state",
    )


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
    
    # sso_service = get_sso_service()
    # user, session = await sso_service.handle_oidc_callback(code, state)
    
    # In production, set session cookie and redirect
    # return RedirectResponse(url="/dashboard")
    
    return {
        "status": "authenticated",
        "message": "OIDC callback processed successfully",
    }


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
    relay_state = form_data.get("RelayState")
    
    if not saml_response:
        raise HTTPException(status_code=400, detail="Missing SAMLResponse")
    
    # sso_service = get_sso_service()
    # user, session = await sso_service.handle_saml_callback(
    #     saml_response, relay_state
    # )
    
    return {
        "status": "authenticated",
        "message": "SAML callback processed successfully",
    }


@router.get("/saml/{provider_id}/metadata")
async def get_sp_metadata(provider_id: str):
    """
    Get SP metadata for SAML configuration.
    
    Returns XML metadata for configuring the identity provider.
    """
    # sso_service = get_sso_service()
    # metadata = sso_service.get_sp_metadata(provider_id)
    
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata" entityID="https://nexusai.example.com/saml/metadata">
    <md:SPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
        <md:AssertionConsumerService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST" Location="https://nexusai.example.com/api/sso/callback/saml" index="0"/>
    </md:SPSSODescriptor>
</md:EntityDescriptor>"""
    
    return Response(content=metadata, media_type="application/xml")


class SSORefreshRequest(BaseModel):
    """SSO token refresh request — token in body, not query string."""

    refresh_token: str
    session_id: Optional[str] = None


@router.post("/token/refresh", response_model=TokenResponse)
async def refresh_token(
    request: SSORefreshRequest,
    _current_user: User = Depends(get_current_admin_user),
):
    """
    Refresh access token.

    Uses refresh token to obtain new access token.
    """
    return TokenResponse(
        access_token="new_access_token",
        token_type="Bearer",
        expires_in=3600,
        refresh_token="new_refresh_token",
        user={"id": "user-123", "email": "user@example.com"},
    )


@router.get("/session", response_model=SessionResponse)
async def get_session(
    session_id: str = Query(...),
    _current_user: User = Depends(get_current_admin_user),
):
    """Get current session information."""
    return SessionResponse(
        session_id=session_id,
        user_id="user-123",
        provider_id="google-workspace",
        expires_at="2026-01-20T12:00:00Z",
        is_active=True,
    )


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
    if post_logout_uri.startswith("/") and not post_logout_uri.startswith("//"):
        safe_uri = post_logout_uri
    else:
        from app.core.config import settings
        parsed = _urlparse(post_logout_uri)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if parsed.scheme not in ("http", "https") or origin not in (settings.CORS_ORIGINS or []):
            safe_uri = "/"
        else:
            safe_uri = post_logout_uri

    return {"status": "logged_out", "redirect_uri": safe_uri}


@router.get("/well-known/openid-configuration")
async def openid_configuration():
    """
    OpenID Connect discovery document.
    
    Returns configuration for OIDC clients.
    """
    base_url = "https://nexusai.example.com"
    
    return {
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}/api/sso/auth",
        "token_endpoint": f"{base_url}/api/sso/token",
        "userinfo_endpoint": f"{base_url}/api/sso/userinfo",
        "jwks_uri": f"{base_url}/.well-known/jwks.json",
        "end_session_endpoint": f"{base_url}/api/sso/logout",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ["RS256"],
        "scopes_supported": ["openid", "profile", "email"],
        "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post"],
    }
