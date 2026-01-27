"""
SSO Integration Service

Enterprise Single Sign-On support:
- OpenID Connect (OIDC)
- SAML 2.0
- Provider configuration
- Session management
"""

from .config import SSOConfig, SSOProvider, ProviderType
from .oidc import OIDCProvider, OIDCConfig, OIDCTokens
from .saml import SAMLProvider, SAMLConfig, SAMLAssertion
from .service import SSOService, SSOSession, SSOUser

__all__ = [
    # Config
    "SSOConfig",
    "SSOProvider", 
    "ProviderType",
    # OIDC
    "OIDCProvider",
    "OIDCConfig",
    "OIDCTokens",
    # SAML
    "SAMLProvider",
    "SAMLConfig",
    "SAMLAssertion",
    # Service
    "SSOService",
    "SSOSession",
    "SSOUser",
]
