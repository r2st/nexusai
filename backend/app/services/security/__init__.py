"""Advanced Security Services.

Provides:
- Tenant isolation and data separation
- Tool and agent permissions
- Rate limiting
- API key management
- Audit logging
- Security scanning (code, config, vulnerabilities)
- Secret rotation and storage
"""

from app.services.security.tenant_isolation import (
    TenantIsolationService,
    TenantScope,
    tenant_isolation_service,
)
from app.services.security.permissions import (
    PermissionsService,
    Permission,
    Role,
    ToolPermission,
    permissions_service,
)
from app.services.security.rate_limiter import (
    RateLimiter,
    RateLimitConfig,
    rate_limiter,
)
from app.services.security.audit import (
    AuditLogger,
    AuditEvent,
    audit_logger,
)
from app.services.security.scanner.service import (
    SecurityScannerService,
    SecurityReport,
    ScanThresholds,
    get_security_scanner_service,
)
from app.services.security.scanner.code_security import (
    CodeSecurityScanner,
    SecurityIssue,
    SecurityCategory,
)
from app.services.security.scanner.config_checker import (
    ConfigSecurityChecker,
    ConfigIssue,
)
from app.services.security.scanner.vulnerability import (
    VulnerabilityScanner,
    Vulnerability,
    VulnerabilitySeverity,
    ScanResult,
)
from app.services.security.secrets.storage import (
    SecretStorage,
    EncryptedSecret,
)
from app.services.security.secrets.rotation import (
    SecretRotationService,
    RotationPolicy,
    SecretType,
    SecretMetadata,
    RotationResult,
)

__all__ = [
    # Tenant Isolation
    "TenantIsolationService",
    "TenantScope",
    "tenant_isolation_service",
    # Permissions
    "PermissionsService",
    "Permission",
    "Role",
    "ToolPermission",
    "permissions_service",
    # Rate Limiting
    "RateLimiter",
    "RateLimitConfig",
    "rate_limiter",
    # Audit
    "AuditLogger",
    "AuditEvent",
    "audit_logger",
    # Security Scanner
    "SecurityScannerService",
    "SecurityReport",
    "ScanThresholds",
    "get_security_scanner_service",
    "CodeSecurityScanner",
    "SecurityIssue",
    "SecurityCategory",
    "ConfigSecurityChecker",
    "ConfigIssue",
    "VulnerabilityScanner",
    "Vulnerability",
    "VulnerabilitySeverity",
    "ScanResult",
    # Secret Rotation
    "SecretStorage",
    "EncryptedSecret",
    "SecretRotationService",
    "RotationPolicy",
    "SecretType",
    "SecretMetadata",
    "RotationResult",
]
