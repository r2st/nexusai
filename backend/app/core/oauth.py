"""OAuth2/OIDC Authentication with Keycloak Support.

Supports multiple identity providers:
- Keycloak (primary enterprise SSO)
- Google OAuth2
- GitHub OAuth2
- Microsoft Azure AD
- Okta
- Generic OIDC providers
"""

import secrets
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import settings


class OAuthProvider(BaseModel):
    """OAuth provider configuration."""

    name: str
    client_id: str
    client_secret: str
    authorization_url: str
    token_url: str
    userinfo_url: str
    jwks_uri: str | None = None
    scopes: list[str] = ["openid", "profile", "email"]

    # OIDC specific
    issuer: str | None = None

    # Provider-specific
    extra_params: dict[str, str] = {}


class OAuthToken(BaseModel):
    """OAuth token response."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int | None = None
    refresh_token: str | None = None
    id_token: str | None = None
    scope: str | None = None


class OAuthUserInfo(BaseModel):
    """Standardized user info from OAuth providers."""

    sub: str  # Subject (unique user ID from provider)
    email: str | None = None
    email_verified: bool = False
    name: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    picture: str | None = None
    locale: str | None = None

    # Provider-specific
    provider: str | None = None
    raw_data: dict[str, Any] = {}


class OAuthService:
    """OAuth2/OIDC service for authentication."""

    # Built-in provider configurations
    PROVIDERS = {
        "keycloak": {
            "authorization_url": "{base_url}/realms/{realm}/protocol/openid-connect/auth",
            "token_url": "{base_url}/realms/{realm}/protocol/openid-connect/token",
            "userinfo_url": "{base_url}/realms/{realm}/protocol/openid-connect/userinfo",
            "jwks_uri": "{base_url}/realms/{realm}/protocol/openid-connect/certs",
            "scopes": ["openid", "profile", "email", "roles"],
        },
        "google": {
            "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "userinfo_url": "https://openidconnect.googleapis.com/v1/userinfo",
            "jwks_uri": "https://www.googleapis.com/oauth2/v3/certs",
            "scopes": ["openid", "profile", "email"],
        },
        "github": {
            "authorization_url": "https://github.com/login/oauth/authorize",
            "token_url": "https://github.com/login/oauth/access_token",
            "userinfo_url": "https://api.github.com/user",
            "scopes": ["read:user", "user:email"],
        },
        "microsoft": {
            "authorization_url": "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize",
            "token_url": "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
            "userinfo_url": "https://graph.microsoft.com/oidc/userinfo",
            "jwks_uri": "https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys",
            "scopes": ["openid", "profile", "email"],
        },
        "okta": {
            "authorization_url": "https://{domain}/oauth2/v1/authorize",
            "token_url": "https://{domain}/oauth2/v1/token",
            "userinfo_url": "https://{domain}/oauth2/v1/userinfo",
            "jwks_uri": "https://{domain}/oauth2/v1/keys",
            "scopes": ["openid", "profile", "email"],
        },
    }

    def __init__(self):
        self._providers: dict[str, OAuthProvider] = {}
        # State storage moved to Redis via OAuthStateStore in cache.py

    def register_provider(
        self,
        name: str,
        client_id: str,
        client_secret: str,
        provider_type: str = "oidc",
        **kwargs,
    ) -> OAuthProvider:
        """Register an OAuth provider.

        Args:
            name: Unique provider name
            client_id: OAuth client ID
            client_secret: OAuth client secret
            provider_type: Provider type (keycloak, google, github, etc.)
            **kwargs: Additional provider-specific config

        Returns:
            Registered OAuthProvider
        """
        base_config = self.PROVIDERS.get(provider_type, {})

        # Apply template substitutions
        authorization_url = base_config.get("authorization_url", kwargs.get("authorization_url", ""))
        token_url = base_config.get("token_url", kwargs.get("token_url", ""))
        userinfo_url = base_config.get("userinfo_url", kwargs.get("userinfo_url", ""))
        jwks_uri = base_config.get("jwks_uri", kwargs.get("jwks_uri"))

        # Substitute placeholders
        for placeholder in ["base_url", "realm", "tenant", "domain"]:
            if placeholder in kwargs:
                value = kwargs[placeholder]
                authorization_url = authorization_url.replace(f"{{{placeholder}}}", value)
                token_url = token_url.replace(f"{{{placeholder}}}", value)
                userinfo_url = userinfo_url.replace(f"{{{placeholder}}}", value)
                if jwks_uri:
                    jwks_uri = jwks_uri.replace(f"{{{placeholder}}}", value)

        provider = OAuthProvider(
            name=name,
            client_id=client_id,
            client_secret=client_secret,
            authorization_url=authorization_url,
            token_url=token_url,
            userinfo_url=userinfo_url,
            jwks_uri=jwks_uri,
            scopes=kwargs.get("scopes", base_config.get("scopes", ["openid", "profile", "email"])),
            issuer=kwargs.get("issuer"),
            extra_params=kwargs.get("extra_params", {}),
        )

        self._providers[name] = provider
        return provider

    def get_authorization_url(
        self,
        provider_name: str,
        redirect_uri: str,
        state: str | None = None,
        nonce: str | None = None,
        extra_params: dict[str, str] | None = None,
    ) -> tuple[str, str]:
        """Generate authorization URL for OAuth flow.

        Args:
            provider_name: Registered provider name
            redirect_uri: Callback URL after authorization
            state: CSRF protection state (generated if not provided)
            nonce: OIDC nonce for ID token validation
            extra_params: Additional URL parameters

        Returns:
            Tuple of (authorization_url, state)
        """
        provider = self._providers.get(provider_name)
        if not provider:
            raise ValueError(f"Unknown provider: {provider_name}")

        state = state or secrets.token_urlsafe(32)
        nonce = nonce or secrets.token_urlsafe(16)

        # Store state in Redis for validation (will be done async by caller)
        # State data to be stored via OAuthStateStore.create_state()
        self._pending_state = {
            "state": state,
            "data": {
                "provider": provider_name,
                "redirect_uri": redirect_uri,
                "nonce": nonce,
                "created_at": datetime.utcnow().isoformat(),
            }
        }

        params = {
            "client_id": provider.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(provider.scopes),
            "state": state,
            **provider.extra_params,
            **(extra_params or {}),
        }

        # Add nonce for OIDC
        if "openid" in provider.scopes:
            params["nonce"] = nonce

        url = f"{provider.authorization_url}?{urlencode(params)}"
        return url, state

    async def exchange_code(
        self,
        provider_name: str,
        code: str,
        redirect_uri: str,
        state: str | None = None,
    ) -> OAuthToken:
        """Exchange authorization code for tokens.

        Args:
            provider_name: Provider name
            code: Authorization code from callback
            redirect_uri: Original redirect URI
            state: State parameter for validation

        Returns:
            OAuthToken with access token and optionally refresh/ID tokens
        """
        provider = self._providers.get(provider_name)
        if not provider:
            raise ValueError(f"Unknown provider: {provider_name}")

        # Validate state
        if state:
            stored_state = self._state_store.pop(state, None)
            if not stored_state:
                raise ValueError("Invalid state parameter")
            if stored_state["provider"] != provider_name:
                raise ValueError("State provider mismatch")

        # Exchange code for token
        async with httpx.AsyncClient() as client:
            response = await client.post(
                provider.token_url,
                data={
                    "grant_type": "authorization_code",
                    "client_id": provider.client_id,
                    "client_secret": provider.client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                headers={"Accept": "application/json"},
            )

            if response.status_code != 200:
                raise ValueError(f"Token exchange failed: {response.text}")

            data = response.json()

        return OAuthToken(
            access_token=data["access_token"],
            token_type=data.get("token_type", "Bearer"),
            expires_in=data.get("expires_in"),
            refresh_token=data.get("refresh_token"),
            id_token=data.get("id_token"),
            scope=data.get("scope"),
        )

    async def get_user_info(
        self,
        provider_name: str,
        access_token: str,
    ) -> OAuthUserInfo:
        """Get user information from OAuth provider.

        Args:
            provider_name: Provider name
            access_token: Valid access token

        Returns:
            Standardized OAuthUserInfo
        """
        provider = self._providers.get(provider_name)
        if not provider:
            raise ValueError(f"Unknown provider: {provider_name}")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                provider.userinfo_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
            )

            if response.status_code != 200:
                raise ValueError(f"Failed to get user info: {response.text}")

            data = response.json()

        # Normalize based on provider
        return self._normalize_user_info(provider_name, data)

    def _normalize_user_info(
        self,
        provider_name: str,
        data: dict[str, Any],
    ) -> OAuthUserInfo:
        """Normalize user info from different providers."""
        # GitHub has different field names
        if provider_name == "github":
            return OAuthUserInfo(
                sub=str(data.get("id", "")),
                email=data.get("email"),
                email_verified=True if data.get("email") else False,
                name=data.get("name"),
                picture=data.get("avatar_url"),
                provider=provider_name,
                raw_data=data,
            )

        # Standard OIDC claims
        return OAuthUserInfo(
            sub=data.get("sub", ""),
            email=data.get("email"),
            email_verified=data.get("email_verified", False),
            name=data.get("name"),
            given_name=data.get("given_name"),
            family_name=data.get("family_name"),
            picture=data.get("picture"),
            locale=data.get("locale"),
            provider=provider_name,
            raw_data=data,
        )

    async def refresh_token(
        self,
        provider_name: str,
        refresh_token: str,
    ) -> OAuthToken:
        """Refresh an access token.

        Args:
            provider_name: Provider name
            refresh_token: Valid refresh token

        Returns:
            New OAuthToken
        """
        provider = self._providers.get(provider_name)
        if not provider:
            raise ValueError(f"Unknown provider: {provider_name}")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                provider.token_url,
                data={
                    "grant_type": "refresh_token",
                    "client_id": provider.client_id,
                    "client_secret": provider.client_secret,
                    "refresh_token": refresh_token,
                },
                headers={"Accept": "application/json"},
            )

            if response.status_code != 200:
                raise ValueError(f"Token refresh failed: {response.text}")

            data = response.json()

        return OAuthToken(
            access_token=data["access_token"],
            token_type=data.get("token_type", "Bearer"),
            expires_in=data.get("expires_in"),
            refresh_token=data.get("refresh_token", refresh_token),
            id_token=data.get("id_token"),
            scope=data.get("scope"),
        )

    async def validate_id_token(
        self,
        provider_name: str,
        id_token: str,
        nonce: str | None = None,
    ) -> dict[str, Any]:
        """Validate and decode an OIDC ID token.

        Args:
            provider_name: Provider name
            id_token: ID token to validate
            nonce: Expected nonce value

        Returns:
            Decoded token claims
        """
        provider = self._providers.get(provider_name)
        if not provider:
            raise ValueError(f"Unknown provider: {provider_name}")

        if not provider.jwks_uri:
            raise ValueError(f"Provider {provider_name} doesn't support ID tokens")

        # Get JWKS
        async with httpx.AsyncClient() as client:
            response = await client.get(provider.jwks_uri)
            jwks = response.json()

        # Decode and validate token
        try:
            # In production, properly validate with jose library
            unverified_header = jwt.get_unverified_header(id_token)

            # Find matching key
            key = None
            for k in jwks.get("keys", []):
                if k.get("kid") == unverified_header.get("kid"):
                    key = k
                    break

            if not key:
                raise ValueError("No matching key found")

            claims = jwt.decode(
                id_token,
                key,
                algorithms=["RS256"],
                audience=provider.client_id,
                issuer=provider.issuer,
            )

            # Validate nonce
            if nonce and claims.get("nonce") != nonce:
                raise ValueError("Invalid nonce")

            return claims

        except JWTError as e:
            raise ValueError(f"Invalid ID token: {e}")

    def list_providers(self) -> list[str]:
        """List registered provider names."""
        return list(self._providers.keys())


class KeycloakService(OAuthService):
    """Specialized Keycloak service with additional features."""

    def __init__(
        self,
        base_url: str | None = None,
        realm: str = "master",
        client_id: str | None = None,
        client_secret: str | None = None,
    ):
        super().__init__()
        self.base_url = base_url or settings.KEYCLOAK_URL
        self.realm = realm

        if client_id and client_secret:
            self.register_provider(
                name="keycloak",
                client_id=client_id,
                client_secret=client_secret,
                provider_type="keycloak",
                base_url=self.base_url,
                realm=realm,
                issuer=f"{self.base_url}/realms/{realm}",
            )

    async def get_realm_roles(self, access_token: str) -> list[str]:
        """Get user's realm roles from Keycloak."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("realm_access", {}).get("roles", [])

        return []

    async def get_client_roles(
        self,
        access_token: str,
        client_id: str,
    ) -> list[str]:
        """Get user's client-specific roles from Keycloak."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("resource_access", {}).get(client_id, {}).get("roles", [])

        return []

    async def logout(
        self,
        refresh_token: str,
    ) -> bool:
        """Logout user from Keycloak session."""
        provider = self._providers.get("keycloak")
        if not provider:
            return False

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/logout",
                data={
                    "client_id": provider.client_id,
                    "client_secret": provider.client_secret,
                    "refresh_token": refresh_token,
                },
            )

            return response.status_code == 204


# Singleton instances
oauth_service = OAuthService()
keycloak_service = KeycloakService()
