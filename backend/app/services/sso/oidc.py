"""
OpenID Connect Provider

OIDC authentication implementation.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import base64
import hashlib
import json
import logging
import secrets
import urllib.parse

import httpx
import jwt
from jwt import PyJWKClient

from .config import SSOProvider, ProviderStatus

logger = logging.getLogger(__name__)


@dataclass
class OIDCConfig:
    """OIDC-specific configuration."""
    provider: SSOProvider
    
    # PKCE
    use_pkce: bool = True
    code_challenge_method: str = "S256"
    
    # Token validation
    validate_at_hash: bool = True
    allowed_algorithms: List[str] = field(default_factory=lambda: ["RS256", "RS384", "RS512"])
    
    # Clock skew tolerance (seconds)
    clock_skew: int = 60


@dataclass
class OIDCTokens:
    """OIDC token response."""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    refresh_token: Optional[str] = None
    id_token: Optional[str] = None
    scope: str = ""
    
    # Parsed claims
    claims: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    issued_at: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def expires_at(self) -> datetime:
        return self.issued_at + timedelta(seconds=self.expires_in)
    
    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at


@dataclass
class OIDCState:
    """OIDC authentication state."""
    state: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    nonce: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    code_verifier: Optional[str] = None
    code_challenge: Optional[str] = None
    redirect_uri: str = ""
    provider_id: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    # Original request info
    original_url: str = ""
    tenant_id: str = ""


class OIDCProvider:
    """
    OpenID Connect authentication provider.
    
    Features:
    - Authorization code flow with PKCE
    - Token validation
    - User info retrieval
    - Token refresh
    - Logout handling
    """
    
    def __init__(
        self,
        config: OIDCConfig,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        self.config = config
        self.provider = config.provider
        self.http_client = http_client
        self._jwks_client: Optional[PyJWKClient] = None
        self._discovery_cache: Optional[Dict[str, Any]] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        if self.http_client is None:
            self.http_client = httpx.AsyncClient(timeout=30.0)
        return self.http_client
    
    async def discover(self) -> Dict[str, Any]:
        """Fetch OIDC discovery document."""
        if self._discovery_cache:
            return self._discovery_cache
        
        discovery_url = f"{self.provider.issuer_url.rstrip('/')}/.well-known/openid-configuration"
        
        client = await self._get_client()
        response = await client.get(discovery_url)
        response.raise_for_status()
        
        self._discovery_cache = response.json()
        
        # Update provider URLs from discovery
        if not self.provider.authorization_url:
            self.provider.authorization_url = self._discovery_cache.get("authorization_endpoint", "")
        if not self.provider.token_url:
            self.provider.token_url = self._discovery_cache.get("token_endpoint", "")
        if not self.provider.userinfo_url:
            self.provider.userinfo_url = self._discovery_cache.get("userinfo_endpoint", "")
        if not self.provider.jwks_url:
            self.provider.jwks_url = self._discovery_cache.get("jwks_uri", "")
        if not self.provider.logout_url:
            self.provider.logout_url = self._discovery_cache.get("end_session_endpoint", "")
        
        return self._discovery_cache
    
    def create_auth_state(self, redirect_uri: str, tenant_id: str = "") -> OIDCState:
        """Create authentication state for authorization request."""
        state = OIDCState(
            redirect_uri=redirect_uri,
            provider_id=self.provider.id,
            tenant_id=tenant_id,
        )
        
        # Generate PKCE if enabled
        if self.config.use_pkce:
            state.code_verifier = secrets.token_urlsafe(64)
            state.code_challenge = self._create_code_challenge(state.code_verifier)
        
        return state
    
    def get_authorization_url(self, state: OIDCState) -> str:
        """Build the authorization URL."""
        params = {
            "response_type": "code",
            "client_id": self.provider.client_id,
            "redirect_uri": state.redirect_uri,
            "scope": " ".join(self.provider.scopes),
            "state": state.state,
            "nonce": state.nonce,
        }
        
        if self.config.use_pkce and state.code_challenge:
            params["code_challenge"] = state.code_challenge
            params["code_challenge_method"] = self.config.code_challenge_method
        
        query = urllib.parse.urlencode(params)
        return f"{self.provider.authorization_url}?{query}"
    
    async def exchange_code(
        self,
        code: str,
        state: OIDCState,
    ) -> OIDCTokens:
        """Exchange authorization code for tokens."""
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": state.redirect_uri,
            "client_id": self.provider.client_id,
        }
        
        # Add client secret if not using PKCE
        if self.provider.client_secret:
            data["client_secret"] = self.provider.client_secret
        
        # Add PKCE verifier
        if self.config.use_pkce and state.code_verifier:
            data["code_verifier"] = state.code_verifier
        
        client = await self._get_client()
        response = await client.post(
            self.provider.token_url,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        
        if response.status_code != 200:
            logger.error(f"Token exchange failed: {response.text}")
            raise ValueError(f"Token exchange failed: {response.status_code}")
        
        token_data = response.json()
        
        tokens = OIDCTokens(
            access_token=token_data["access_token"],
            token_type=token_data.get("token_type", "Bearer"),
            expires_in=token_data.get("expires_in", 3600),
            refresh_token=token_data.get("refresh_token"),
            id_token=token_data.get("id_token"),
            scope=token_data.get("scope", ""),
        )
        
        # Validate and decode ID token
        if tokens.id_token:
            tokens.claims = await self.validate_id_token(tokens.id_token, state.nonce)
        
        return tokens
    
    async def validate_id_token(
        self,
        id_token: str,
        nonce: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Validate and decode ID token."""
        # Get JWKS
        if not self._jwks_client and self.provider.jwks_url:
            self._jwks_client = PyJWKClient(self.provider.jwks_url)
        
        # Get signing key
        signing_key = self._jwks_client.get_signing_key_from_jwt(id_token)
        
        # Decode and validate
        claims = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=self.config.allowed_algorithms,
            audience=self.provider.client_id,
            issuer=self.provider.issuer_url,
            options={
                "verify_exp": True,
                "verify_iat": True,
                "verify_aud": True,
                "verify_iss": True,
                "leeway": self.config.clock_skew,
            },
        )
        
        # Validate nonce
        if nonce and self.config.validate_at_hash:
            if claims.get("nonce") != nonce:
                raise ValueError("Invalid nonce in ID token")
        
        return claims
    
    async def get_userinfo(self, access_token: str) -> Dict[str, Any]:
        """Fetch user info from userinfo endpoint."""
        if not self.provider.userinfo_url:
            return {}
        
        client = await self._get_client()
        response = await client.get(
            self.provider.userinfo_url,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        
        if response.status_code != 200:
            logger.warning(f"Userinfo request failed: {response.status_code}")
            return {}
        
        return response.json()
    
    async def refresh_tokens(self, refresh_token: str) -> OIDCTokens:
        """Refresh access token using refresh token."""
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.provider.client_id,
        }
        
        if self.provider.client_secret:
            data["client_secret"] = self.provider.client_secret
        
        client = await self._get_client()
        response = await client.post(
            self.provider.token_url,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        
        if response.status_code != 200:
            raise ValueError(f"Token refresh failed: {response.status_code}")
        
        token_data = response.json()
        
        return OIDCTokens(
            access_token=token_data["access_token"],
            token_type=token_data.get("token_type", "Bearer"),
            expires_in=token_data.get("expires_in", 3600),
            refresh_token=token_data.get("refresh_token", refresh_token),
            id_token=token_data.get("id_token"),
            scope=token_data.get("scope", ""),
        )
    
    def get_logout_url(self, id_token: str, post_logout_uri: str) -> str:
        """Build the logout URL."""
        if not self.provider.logout_url:
            return post_logout_uri
        
        params = {
            "id_token_hint": id_token,
            "post_logout_redirect_uri": post_logout_uri,
        }
        
        query = urllib.parse.urlencode(params)
        return f"{self.provider.logout_url}?{query}"
    
    def _create_code_challenge(self, verifier: str) -> str:
        """Create PKCE code challenge from verifier."""
        if self.config.code_challenge_method == "S256":
            digest = hashlib.sha256(verifier.encode()).digest()
            return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
        else:
            return verifier  # Plain method
    
    def map_claims_to_user(self, claims: Dict[str, Any]) -> Dict[str, Any]:
        """Map OIDC claims to user attributes."""
        mappings = self.provider.claim_mappings or {
            "sub": "external_id",
            "email": "email",
            "name": "name",
            "given_name": "first_name",
            "family_name": "last_name",
            "picture": "avatar_url",
            "groups": "groups",
        }
        
        user_data = {}
        for claim_name, user_attr in mappings.items():
            if claim_name in claims:
                user_data[user_attr] = claims[claim_name]
        
        return user_data
