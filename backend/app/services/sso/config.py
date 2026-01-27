"""
SSO Configuration

Configuration models for SSO providers.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class ProviderType(str, Enum):
    """SSO provider types."""
    OIDC = "oidc"
    SAML = "saml"
    OAUTH2 = "oauth2"


class ProviderStatus(str, Enum):
    """Provider status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    ERROR = "error"


@dataclass
class SSOProvider:
    """SSO provider configuration."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    name: str = ""
    display_name: str = ""
    type: ProviderType = ProviderType.OIDC
    status: ProviderStatus = ProviderStatus.PENDING
    
    # Provider URLs
    issuer_url: str = ""
    authorization_url: str = ""
    token_url: str = ""
    userinfo_url: str = ""
    jwks_url: str = ""
    logout_url: str = ""
    
    # SAML-specific
    metadata_url: str = ""
    entity_id: str = ""
    acs_url: str = ""
    slo_url: str = ""
    
    # Client credentials
    client_id: str = ""
    client_secret: str = ""
    
    # Scopes and claims
    scopes: List[str] = field(default_factory=lambda: ["openid", "profile", "email"])
    claim_mappings: Dict[str, str] = field(default_factory=dict)
    
    # Options
    auto_provision_users: bool = True
    default_role: str = "user"
    allowed_domains: List[str] = field(default_factory=list)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_used_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "display_name": self.display_name,
            "type": self.type.value,
            "status": self.status.value,
            "issuer_url": self.issuer_url,
            "scopes": self.scopes,
            "auto_provision_users": self.auto_provision_users,
            "default_role": self.default_role,
            "allowed_domains": self.allowed_domains,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class SSOConfig:
    """Global SSO configuration."""
    enabled: bool = True
    
    # Default provider
    default_provider_id: Optional[str] = None
    
    # Session settings
    session_lifetime_hours: int = 24
    refresh_token_lifetime_days: int = 30
    
    # Security
    require_https: bool = True
    validate_nonce: bool = True
    validate_state: bool = True
    
    # User provisioning
    auto_create_users: bool = True
    sync_user_attributes: bool = True
    sync_group_membership: bool = True
    
    # Callbacks
    callback_base_url: str = ""
    
    # Providers
    providers: Dict[str, SSOProvider] = field(default_factory=dict)
    
    def get_provider(self, provider_id: str) -> Optional[SSOProvider]:
        return self.providers.get(provider_id)
    
    def get_active_providers(self) -> List[SSOProvider]:
        return [p for p in self.providers.values() if p.status == ProviderStatus.ACTIVE]


# Well-known provider configurations
WELL_KNOWN_PROVIDERS = {
    "google": {
        "name": "google",
        "display_name": "Google Workspace",
        "type": ProviderType.OIDC,
        "issuer_url": "https://accounts.google.com",
        "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://openidconnect.googleapis.com/v1/userinfo",
        "jwks_url": "https://www.googleapis.com/oauth2/v3/certs",
        "scopes": ["openid", "profile", "email"],
    },
    "microsoft": {
        "name": "microsoft",
        "display_name": "Microsoft Entra ID",
        "type": ProviderType.OIDC,
        "issuer_url": "https://login.microsoftonline.com/{tenant_id}/v2.0",
        "authorization_url": "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
        "userinfo_url": "https://graph.microsoft.com/oidc/userinfo",
        "jwks_url": "https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys",
        "scopes": ["openid", "profile", "email", "User.Read"],
    },
    "okta": {
        "name": "okta",
        "display_name": "Okta",
        "type": ProviderType.OIDC,
        "issuer_url": "https://{domain}.okta.com",
        "authorization_url": "https://{domain}.okta.com/oauth2/v1/authorize",
        "token_url": "https://{domain}.okta.com/oauth2/v1/token",
        "userinfo_url": "https://{domain}.okta.com/oauth2/v1/userinfo",
        "jwks_url": "https://{domain}.okta.com/oauth2/v1/keys",
        "scopes": ["openid", "profile", "email", "groups"],
    },
    "auth0": {
        "name": "auth0",
        "display_name": "Auth0",
        "type": ProviderType.OIDC,
        "issuer_url": "https://{domain}.auth0.com/",
        "authorization_url": "https://{domain}.auth0.com/authorize",
        "token_url": "https://{domain}.auth0.com/oauth/token",
        "userinfo_url": "https://{domain}.auth0.com/userinfo",
        "jwks_url": "https://{domain}.auth0.com/.well-known/jwks.json",
        "scopes": ["openid", "profile", "email"],
    },
}
