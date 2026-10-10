"""
SSO Service

Unified SSO service managing providers and sessions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import logging
import uuid

from .config import SSOConfig, SSOProvider, ProviderType, ProviderStatus
from .oidc import OIDCProvider, OIDCConfig, OIDCTokens, OIDCState
from .saml import SAMLProvider, SAMLConfig, SAMLAssertion, SAMLState

logger = logging.getLogger(__name__)


@dataclass
class SSOUser:
    """User information from SSO."""
    external_id: str
    provider_id: str
    provider_type: ProviderType
    
    # User attributes
    email: Optional[str] = None
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar_url: Optional[str] = None
    
    # Groups/roles
    groups: List[str] = field(default_factory=list)
    roles: List[str] = field(default_factory=list)
    
    # Raw data
    raw_claims: Dict[str, Any] = field(default_factory=dict)
    
    # Tenant
    tenant_id: str = ""


@dataclass
class SSOSession:
    """SSO session information."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    provider_id: str = ""
    
    # Tokens (OIDC)
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    id_token: Optional[str] = None
    
    # SAML session
    name_id: Optional[str] = None
    session_index: Optional[str] = None
    
    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    last_activity: datetime = field(default_factory=datetime.utcnow)
    
    # Metadata
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    @property
    def is_expired(self) -> bool:
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False


class SSOService:
    """
    Unified SSO service.
    
    Features:
    - Multiple provider management
    - OIDC and SAML support
    - Session management
    - User provisioning
    """
    
    def __init__(
        self,
        config: Optional[SSOConfig] = None,
        session_store: Optional[Any] = None,
        state_store: Optional[Any] = None,
    ):
        self.config = config or SSOConfig()
        self.session_store = session_store
        self.state_store = state_store
        
        # Provider instances
        self._oidc_providers: Dict[str, OIDCProvider] = {}
        self._saml_providers: Dict[str, SAMLProvider] = {}
        
        # In-memory stores (replace with Redis in production)
        self._sessions: Dict[str, SSOSession] = {}
        self._states: Dict[str, Any] = {}
    
    async def initialize(self) -> None:
        """Initialize all configured providers."""
        for provider_id, provider in self.config.providers.items():
            await self._initialize_provider(provider)
    
    async def _initialize_provider(self, provider: SSOProvider) -> None:
        """Initialize a single provider."""
        try:
            if provider.type == ProviderType.OIDC:
                oidc_config = OIDCConfig(provider=provider)
                oidc_provider = OIDCProvider(oidc_config)
                await oidc_provider.discover()
                self._oidc_providers[provider.id] = oidc_provider
                provider.status = ProviderStatus.ACTIVE
                
            elif provider.type == ProviderType.SAML:
                saml_config = SAMLConfig(
                    provider=provider,
                    sp_entity_id=f"{self.config.callback_base_url}/saml/metadata",
                    sp_acs_url=f"{self.config.callback_base_url}/saml/acs",
                    sp_slo_url=f"{self.config.callback_base_url}/saml/slo",
                )
                saml_provider = SAMLProvider(saml_config)
                await saml_provider.fetch_idp_metadata()
                self._saml_providers[provider.id] = saml_provider
                provider.status = ProviderStatus.ACTIVE
            
            logger.info(f"Initialized SSO provider: {provider.name} ({provider.type})")
            
        except Exception as e:
            logger.error(f"Failed to initialize provider {provider.name}: {e}")
            provider.status = ProviderStatus.ERROR
    
    def add_provider(self, provider: SSOProvider) -> None:
        """Add a new provider."""
        self.config.providers[provider.id] = provider
    
    def get_provider(self, provider_id: str) -> Optional[SSOProvider]:
        """Get provider by ID."""
        return self.config.providers.get(provider_id)
    
    def list_providers(self, tenant_id: Optional[str] = None) -> List[SSOProvider]:
        """List available providers."""
        providers = list(self.config.providers.values())
        if tenant_id:
            providers = [p for p in providers if p.tenant_id == tenant_id or not p.tenant_id]
        return [p for p in providers if p.status == ProviderStatus.ACTIVE]
    
    async def start_authentication(
        self,
        provider_id: str,
        redirect_uri: str,
        tenant_id: str = "",
    ) -> str:
        """
        Start SSO authentication flow.
        
        Returns:
            Authorization URL to redirect user to
        """
        provider = self.config.providers.get(provider_id)
        if not provider:
            raise ValueError(f"Unknown provider: {provider_id}")
        
        if provider.type == ProviderType.OIDC:
            oidc = self._oidc_providers.get(provider_id)
            if not oidc:
                raise ValueError(f"OIDC provider not initialized: {provider_id}")
            
            state = oidc.create_auth_state(redirect_uri, tenant_id)
            self._states[state.state] = state
            
            return oidc.get_authorization_url(state)
        
        elif provider.type == ProviderType.SAML:
            saml = self._saml_providers.get(provider_id)
            if not saml:
                raise ValueError(f"SAML provider not initialized: {provider_id}")
            
            state = saml.create_auth_state(tenant_id)
            state.original_url = redirect_uri
            self._states[state.relay_state] = state
            
            return saml.get_authorization_url(state)
        
        raise ValueError(f"Unsupported provider type: {provider.type}")
    
    async def handle_oidc_callback(
        self,
        code: str,
        state: str,
    ) -> tuple[SSOUser, SSOSession]:
        """Handle OIDC callback."""
        # Retrieve state
        auth_state = self._states.pop(state, None)
        if not auth_state or not isinstance(auth_state, OIDCState):
            raise ValueError("Invalid or expired state")
        
        # Get provider
        oidc = self._oidc_providers.get(auth_state.provider_id)
        if not oidc:
            raise ValueError("Provider not found")
        
        # Exchange code for tokens
        tokens = await oidc.exchange_code(code, auth_state)
        
        # Get additional user info if needed
        userinfo = {}
        if oidc.provider.userinfo_url:
            userinfo = await oidc.get_userinfo(tokens.access_token)
        
        # Merge claims
        all_claims = {**tokens.claims, **userinfo}
        
        # Map to user
        user_data = oidc.map_claims_to_user(all_claims)
        
        user = SSOUser(
            external_id=user_data.get("external_id", all_claims.get("sub", "")),
            provider_id=auth_state.provider_id,
            provider_type=ProviderType.OIDC,
            email=user_data.get("email"),
            name=user_data.get("name"),
            first_name=user_data.get("first_name"),
            last_name=user_data.get("last_name"),
            avatar_url=user_data.get("avatar_url"),
            groups=user_data.get("groups", []),
            raw_claims=all_claims,
            tenant_id=auth_state.tenant_id,
        )
        
        # Create session
        session = SSOSession(
            provider_id=auth_state.provider_id,
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            id_token=tokens.id_token,
            expires_at=tokens.expires_at,
        )
        
        self._sessions[session.id] = session
        
        # Update provider last used
        provider = self.config.providers.get(auth_state.provider_id)
        if provider:
            provider.last_used_at = datetime.utcnow()
        
        return user, session
    
    async def handle_saml_callback(
        self,
        saml_response: str,
        relay_state: str,
    ) -> tuple[SSOUser, SSOSession]:
        """Handle SAML callback."""
        # Retrieve state
        auth_state = self._states.pop(relay_state, None)
        if not auth_state or not isinstance(auth_state, SAMLState):
            raise ValueError("Invalid or expired relay state")
        
        # Get provider
        saml = self._saml_providers.get(auth_state.provider_id)
        if not saml:
            raise ValueError("Provider not found")
        
        # Parse response
        assertion = saml.parse_response(saml_response)
        
        # Validate
        if not saml.validate_assertion(assertion, auth_state.request_id):
            raise ValueError("Invalid SAML assertion")
        
        # Map to user
        user_data = saml.map_attributes_to_user(assertion)
        
        user = SSOUser(
            external_id=assertion.name_id,
            provider_id=auth_state.provider_id,
            provider_type=ProviderType.SAML,
            email=user_data.get("email"),
            name=user_data.get("name"),
            first_name=user_data.get("first_name"),
            last_name=user_data.get("last_name"),
            groups=user_data.get("groups", []) if isinstance(user_data.get("groups"), list) else [],
            raw_claims=assertion.attributes,
            tenant_id=auth_state.tenant_id,
        )
        
        # Create session
        session = SSOSession(
            provider_id=auth_state.provider_id,
            name_id=assertion.name_id,
            session_index=assertion.session_index,
            expires_at=assertion.not_on_or_after,
        )
        
        self._sessions[session.id] = session
        
        return user, session
    
    async def refresh_session(self, session_id: str) -> Optional[SSOSession]:
        """Refresh an SSO session."""
        session = self._sessions.get(session_id)
        if not session or not session.refresh_token:
            return None
        
        provider = self.config.providers.get(session.provider_id)
        if not provider or provider.type != ProviderType.OIDC:
            return None
        
        oidc = self._oidc_providers.get(session.provider_id)
        if not oidc:
            return None
        
        try:
            tokens = await oidc.refresh_tokens(session.refresh_token)
            
            session.access_token = tokens.access_token
            session.refresh_token = tokens.refresh_token or session.refresh_token
            session.id_token = tokens.id_token
            session.expires_at = tokens.expires_at
            session.last_activity = datetime.utcnow()
            
            return session
        except Exception as e:
            logger.error(f"Session refresh failed: {e}")
            return None
    
    async def logout(
        self,
        session_id: str,
        post_logout_uri: str,
    ) -> Optional[str]:
        """
        Logout from SSO.
        
        Returns:
            Logout URL to redirect to, or None
        """
        session = self._sessions.pop(session_id, None)
        if not session:
            return None
        
        provider = self.config.providers.get(session.provider_id)
        if not provider:
            return None
        
        if provider.type == ProviderType.OIDC and session.id_token:
            oidc = self._oidc_providers.get(session.provider_id)
            if oidc:
                return oidc.get_logout_url(session.id_token, post_logout_uri)
        
        elif provider.type == ProviderType.SAML and session.name_id:
            saml = self._saml_providers.get(session.provider_id)
            if saml:
                return saml.get_logout_url(session.name_id, session.session_index or "")
        
        return None
    
    def get_session(self, session_id: str) -> Optional[SSOSession]:
        """Get session by ID."""
        session = self._sessions.get(session_id)
        if session and not session.is_expired:
            session.last_activity = datetime.utcnow()
            return session
        return None
    
    def get_sp_metadata(self, provider_id: str) -> Optional[str]:
        """Get SP metadata for a SAML provider."""
        saml = self._saml_providers.get(provider_id)
        if saml:
            return saml.generate_sp_metadata()
        return None
    
    async def provision_user(
        self,
        sso_user: SSOUser,
        user_service: Any,
    ) -> Any:
        """
        Provision or update user from SSO.
        
        This should be overridden or configured per deployment.
        """
        provider = self.config.providers.get(sso_user.provider_id)
        if not provider or not provider.auto_provision_users:
            return None
        
        # Check allowed domains
        if provider.allowed_domains and sso_user.email:
            domain = sso_user.email.split("@")[-1]
            if domain not in provider.allowed_domains:
                raise ValueError(f"Email domain not allowed: {domain}")
        
        # This would integrate with your user service
        # user = await user_service.find_or_create(
        #     external_id=sso_user.external_id,
        #     provider_id=sso_user.provider_id,
        #     email=sso_user.email,
        #     name=sso_user.name,
        #     role=provider.default_role,
        # )
        
        return None
