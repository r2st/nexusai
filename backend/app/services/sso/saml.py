"""
SAML 2.0 Provider

SAML authentication implementation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import base64
import logging
import secrets
import zlib
from xml.etree import ElementTree as ET

import httpx

from .config import SSOProvider, ProviderStatus

logger = logging.getLogger(__name__)

# SAML namespaces
NAMESPACES = {
    "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
    "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
    "md": "urn:oasis:names:tc:SAML:2.0:metadata",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
}


@dataclass
class SAMLConfig:
    """SAML-specific configuration."""
    provider: SSOProvider
    
    # SP configuration
    sp_entity_id: str = ""
    sp_acs_url: str = ""
    sp_slo_url: str = ""
    
    # Security
    sign_requests: bool = True
    sign_logout_requests: bool = True
    want_assertions_signed: bool = True
    want_response_signed: bool = False
    
    # Certificate
    sp_certificate: str = ""
    sp_private_key: str = ""
    
    # Name ID format
    name_id_format: str = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"


@dataclass
class SAMLAssertion:
    """Parsed SAML assertion."""
    id: str = ""
    issuer: str = ""
    subject: str = ""
    name_id: str = ""
    name_id_format: str = ""
    
    # Conditions
    not_before: Optional[datetime] = None
    not_on_or_after: Optional[datetime] = None
    audience: str = ""
    
    # Session
    session_index: str = ""
    authn_instant: Optional[datetime] = None
    
    # Attributes
    attributes: Dict[str, List[str]] = field(default_factory=dict)
    
    @property
    def is_valid(self) -> bool:
        now = datetime.utcnow()
        if self.not_before and now < self.not_before:
            return False
        if self.not_on_or_after and now >= self.not_on_or_after:
            return False
        return True


@dataclass
class SAMLState:
    """SAML authentication state."""
    request_id: str = field(default_factory=lambda: f"_{''.join(secrets.token_hex(16))}")
    relay_state: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    provider_id: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    # Original request
    original_url: str = ""
    tenant_id: str = ""


class SAMLProvider:
    """
    SAML 2.0 authentication provider.
    
    Features:
    - SP-initiated SSO
    - Assertion parsing and validation
    - Attribute mapping
    - Single Logout (SLO)
    """
    
    def __init__(
        self,
        config: SAMLConfig,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        self.config = config
        self.provider = config.provider
        self.http_client = http_client
        self._idp_metadata: Optional[Dict[str, Any]] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        if self.http_client is None:
            self.http_client = httpx.AsyncClient(timeout=30.0)
        return self.http_client
    
    async def fetch_idp_metadata(self) -> Dict[str, Any]:
        """Fetch and parse IdP metadata."""
        if self._idp_metadata:
            return self._idp_metadata
        
        if not self.provider.metadata_url:
            return {}
        
        client = await self._get_client()
        response = await client.get(self.provider.metadata_url)
        response.raise_for_status()
        
        self._idp_metadata = self._parse_metadata(response.text)
        
        # Update provider from metadata
        if "sso_url" in self._idp_metadata:
            self.provider.authorization_url = self._idp_metadata["sso_url"]
        if "slo_url" in self._idp_metadata:
            self.provider.logout_url = self._idp_metadata["slo_url"]
        if "entity_id" in self._idp_metadata:
            self.provider.entity_id = self._idp_metadata["entity_id"]
        
        return self._idp_metadata
    
    def _parse_metadata(self, xml_content: str) -> Dict[str, Any]:
        """Parse SAML metadata XML."""
        root = ET.fromstring(xml_content)
        
        metadata = {
            "entity_id": root.get("entityID", ""),
            "certificates": [],
        }
        
        # Find SSO service
        for sso in root.findall(".//md:SingleSignOnService", NAMESPACES):
            if sso.get("Binding") == "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect":
                metadata["sso_url"] = sso.get("Location", "")
                break
        
        # Find SLO service
        for slo in root.findall(".//md:SingleLogoutService", NAMESPACES):
            if slo.get("Binding") == "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect":
                metadata["slo_url"] = slo.get("Location", "")
                break
        
        # Find certificates
        for cert in root.findall(".//ds:X509Certificate", NAMESPACES):
            if cert.text:
                metadata["certificates"].append(cert.text.strip())
        
        return metadata
    
    def create_auth_state(self, tenant_id: str = "") -> SAMLState:
        """Create authentication state."""
        return SAMLState(
            provider_id=self.provider.id,
            tenant_id=tenant_id,
        )
    
    def create_authn_request(self, state: SAMLState) -> str:
        """Create SAML AuthnRequest XML."""
        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        request = f'''<samlp:AuthnRequest
    xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="{state.request_id}"
    Version="2.0"
    IssueInstant="{now}"
    Destination="{self.provider.authorization_url}"
    AssertionConsumerServiceURL="{self.config.sp_acs_url}"
    ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">
    <saml:Issuer>{self.config.sp_entity_id}</saml:Issuer>
    <samlp:NameIDPolicy
        Format="{self.config.name_id_format}"
        AllowCreate="true"/>
</samlp:AuthnRequest>'''
        
        return request
    
    def get_authorization_url(self, state: SAMLState) -> str:
        """Build the SSO redirect URL."""
        authn_request = self.create_authn_request(state)
        
        # Deflate and encode
        compressed = zlib.compress(authn_request.encode())[2:-4]  # Remove zlib header/trailer
        encoded = base64.b64encode(compressed).decode()
        
        # Build URL
        import urllib.parse
        params = {
            "SAMLRequest": encoded,
            "RelayState": state.relay_state,
        }
        
        query = urllib.parse.urlencode(params)
        return f"{self.provider.authorization_url}?{query}"
    
    def parse_response(self, saml_response: str) -> SAMLAssertion:
        """Parse SAML response and extract assertion."""
        # Decode response
        decoded = base64.b64decode(saml_response)
        
        # Parse XML
        root = ET.fromstring(decoded)
        
        # Check status
        status_code = root.find(".//samlp:StatusCode", NAMESPACES)
        if status_code is not None:
            status = status_code.get("Value", "")
            if "Success" not in status:
                raise ValueError(f"SAML authentication failed: {status}")
        
        # Find assertion
        assertion_elem = root.find(".//saml:Assertion", NAMESPACES)
        if assertion_elem is None:
            raise ValueError("No assertion in SAML response")
        
        assertion = SAMLAssertion(
            id=assertion_elem.get("ID", ""),
        )
        
        # Issuer
        issuer = assertion_elem.find("saml:Issuer", NAMESPACES)
        if issuer is not None:
            assertion.issuer = issuer.text or ""
        
        # Subject/NameID
        name_id = assertion_elem.find(".//saml:NameID", NAMESPACES)
        if name_id is not None:
            assertion.name_id = name_id.text or ""
            assertion.name_id_format = name_id.get("Format", "")
        
        # Conditions
        conditions = assertion_elem.find("saml:Conditions", NAMESPACES)
        if conditions is not None:
            not_before = conditions.get("NotBefore")
            if not_before:
                assertion.not_before = datetime.fromisoformat(not_before.replace("Z", "+00:00"))
            
            not_on_or_after = conditions.get("NotOnOrAfter")
            if not_on_or_after:
                assertion.not_on_or_after = datetime.fromisoformat(not_on_or_after.replace("Z", "+00:00"))
            
            audience = conditions.find(".//saml:Audience", NAMESPACES)
            if audience is not None:
                assertion.audience = audience.text or ""
        
        # AuthnStatement
        authn_stmt = assertion_elem.find("saml:AuthnStatement", NAMESPACES)
        if authn_stmt is not None:
            assertion.session_index = authn_stmt.get("SessionIndex", "")
            authn_instant = authn_stmt.get("AuthnInstant")
            if authn_instant:
                assertion.authn_instant = datetime.fromisoformat(authn_instant.replace("Z", "+00:00"))
        
        # Attributes
        for attr_stmt in assertion_elem.findall("saml:AttributeStatement", NAMESPACES):
            for attr in attr_stmt.findall("saml:Attribute", NAMESPACES):
                name = attr.get("Name", "")
                values = []
                for value in attr.findall("saml:AttributeValue", NAMESPACES):
                    if value.text:
                        values.append(value.text)
                if name and values:
                    assertion.attributes[name] = values
        
        return assertion
    
    def validate_assertion(
        self,
        assertion: SAMLAssertion,
        request_id: Optional[str] = None,
    ) -> bool:
        """Validate SAML assertion."""
        # Check validity period
        if not assertion.is_valid:
            logger.warning("Assertion has expired or not yet valid")
            return False
        
        # Check audience
        if assertion.audience and assertion.audience != self.config.sp_entity_id:
            logger.warning(f"Audience mismatch: {assertion.audience}")
            return False
        
        # Check issuer
        if assertion.issuer and assertion.issuer != self.provider.entity_id:
            logger.warning(f"Issuer mismatch: {assertion.issuer}")
            return False
        
        return True
    
    def create_logout_request(self, name_id: str, session_index: str) -> str:
        """Create SAML LogoutRequest XML."""
        request_id = f"_{''.join(secrets.token_hex(16))}"
        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        request = f'''<samlp:LogoutRequest
    xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="{request_id}"
    Version="2.0"
    IssueInstant="{now}"
    Destination="{self.provider.logout_url}">
    <saml:Issuer>{self.config.sp_entity_id}</saml:Issuer>
    <saml:NameID>{name_id}</saml:NameID>
    <samlp:SessionIndex>{session_index}</samlp:SessionIndex>
</samlp:LogoutRequest>'''
        
        return request
    
    def get_logout_url(self, name_id: str, session_index: str) -> str:
        """Build the SLO redirect URL."""
        if not self.provider.logout_url:
            return ""
        
        logout_request = self.create_logout_request(name_id, session_index)
        
        # Deflate and encode
        compressed = zlib.compress(logout_request.encode())[2:-4]
        encoded = base64.b64encode(compressed).decode()
        
        import urllib.parse
        params = {"SAMLRequest": encoded}
        query = urllib.parse.urlencode(params)
        
        return f"{self.provider.logout_url}?{query}"
    
    def map_attributes_to_user(self, assertion: SAMLAssertion) -> Dict[str, Any]:
        """Map SAML attributes to user attributes."""
        mappings = self.provider.claim_mappings or {
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress": "email",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name": "name",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname": "first_name",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname": "last_name",
            "http://schemas.microsoft.com/ws/2008/06/identity/claims/groups": "groups",
            "email": "email",
            "firstName": "first_name",
            "lastName": "last_name",
            "displayName": "name",
        }
        
        user_data = {
            "external_id": assertion.name_id,
        }
        
        for attr_name, values in assertion.attributes.items():
            if attr_name in mappings and values:
                user_attr = mappings[attr_name]
                user_data[user_attr] = values[0] if len(values) == 1 else values
        
        return user_data
    
    def generate_sp_metadata(self) -> str:
        """Generate SP metadata XML."""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<md:EntityDescriptor
    xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
    xmlns:ds="http://www.w3.org/2000/09/xmldsig#"
    entityID="{self.config.sp_entity_id}">
    <md:SPSSODescriptor
        AuthnRequestsSigned="{str(self.config.sign_requests).lower()}"
        WantAssertionsSigned="{str(self.config.want_assertions_signed).lower()}"
        protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
        <md:NameIDFormat>{self.config.name_id_format}</md:NameIDFormat>
        <md:AssertionConsumerService
            Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
            Location="{self.config.sp_acs_url}"
            index="0"
            isDefault="true"/>
        <md:SingleLogoutService
            Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
            Location="{self.config.sp_slo_url}"/>
    </md:SPSSODescriptor>
</md:EntityDescriptor>'''
