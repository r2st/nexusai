"""Data models for Data Residency Controls."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RegionStatus(str, Enum):
    """Status of a data region."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    DEPRECATED = "deprecated"


class DataClassification(str, Enum):
    """Data classification levels."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    PII = "pii"
    PHI = "phi"
    FINANCIAL = "financial"


class TransferStatus(str, Enum):
    """Status of a data transfer request."""

    PENDING = "pending"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ViolationSeverity(str, Enum):
    """Severity of residency violations."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DataRegion(BaseModel):
    """A data storage region."""

    id: str
    name: str
    code: str  # e.g., "us-east-1", "eu-west-1"
    display_name: str

    # Location
    country: str
    country_code: str  # ISO 3166-1 alpha-2
    continent: str

    # Provider info
    provider: str  # aws, gcp, azure, on-premise
    provider_region: str

    # Status
    status: RegionStatus = RegionStatus.ACTIVE

    # Capabilities
    supports_encryption_at_rest: bool = True
    supports_encryption_in_transit: bool = True
    supports_key_management: bool = True
    compliance_certifications: list[str] = Field(default_factory=list)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DataResidencyRequirement(BaseModel):
    """A specific residency requirement."""

    id: str
    name: str
    description: str

    # Scope
    data_classifications: list[DataClassification] = Field(default_factory=list)

    # Allowed regions
    allowed_regions: list[str] = Field(default_factory=list)  # Region IDs
    allowed_countries: list[str] = Field(default_factory=list)  # Country codes
    allowed_continents: list[str] = Field(default_factory=list)

    # Prohibited regions
    prohibited_regions: list[str] = Field(default_factory=list)
    prohibited_countries: list[str] = Field(default_factory=list)

    # Transfer rules
    allow_cross_border_transfer: bool = False
    require_adequacy_decision: bool = True  # EU adequacy decisions
    require_sccs: bool = False  # Standard Contractual Clauses

    # Encryption requirements
    require_encryption_at_rest: bool = True
    require_encryption_in_transit: bool = True
    minimum_encryption_strength: int = 256  # bits

    # Regulatory reference
    regulation: str | None = None  # GDPR, CCPA, etc.
    regulation_article: str | None = None

    # Status
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DataResidencyPolicy(BaseModel):
    """A data residency policy for an organization."""

    id: str
    organization_id: str
    name: str
    description: str | None = None

    # Requirements
    requirements: list[DataResidencyRequirement] = Field(default_factory=list)

    # Default region
    default_region_id: str | None = None

    # Policy settings
    enforce_on_upload: bool = True
    enforce_on_processing: bool = True
    enforce_on_backup: bool = True

    # Exceptions
    exception_approvers: list[str] = Field(default_factory=list)  # User IDs
    allow_temporary_exceptions: bool = False
    max_exception_days: int = 30

    # Audit
    audit_all_transfers: bool = True
    alert_on_violations: bool = True

    # Status
    is_active: bool = True
    version: int = 1

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str | None = None


class StorageLocation(BaseModel):
    """A registered data storage location."""

    id: str
    organization_id: str
    name: str
    description: str | None = None

    # Location
    region_id: str
    storage_type: str  # database, object_storage, file_system, cache

    # Provider details
    provider: str
    provider_identifier: str  # bucket name, database name, etc.
    endpoint: str | None = None

    # Data classification
    data_classifications: list[DataClassification] = Field(default_factory=list)

    # Encryption
    encryption_enabled: bool = True
    encryption_key_id: str | None = None
    encryption_algorithm: str | None = None

    # Compliance
    policy_id: str | None = None
    compliant: bool = True
    last_compliance_check: datetime | None = None
    compliance_issues: list[str] = Field(default_factory=list)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    registered_by: str | None = None


class DataTransferRequest(BaseModel):
    """A request to transfer data between regions."""

    id: str
    organization_id: str

    # Source and destination
    source_region_id: str
    source_location_id: str | None = None
    destination_region_id: str
    destination_location_id: str | None = None

    # Transfer details
    data_classification: DataClassification
    data_description: str
    estimated_size_bytes: int | None = None

    # Justification
    purpose: str
    business_justification: str
    requestor_id: str
    requestor_username: str

    # Legal basis (for GDPR)
    legal_basis: str | None = None  # consent, contract, legitimate_interest, etc.
    sccs_reference: str | None = None  # Standard Contractual Clauses reference

    # Status
    status: TransferStatus = TransferStatus.PENDING

    # Approval
    approved_by: str | None = None
    approved_at: datetime | None = None
    rejection_reason: str | None = None

    # Execution
    started_at: datetime | None = None
    completed_at: datetime | None = None
    transfer_method: str | None = None
    bytes_transferred: int | None = None

    # Audit
    audit_log: list[dict[str, Any]] = Field(default_factory=list)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None  # Transfer must complete by this time


class ResidencyViolation(BaseModel):
    """A data residency violation."""

    id: str
    organization_id: str

    # Violation details
    violation_type: str  # unauthorized_region, missing_encryption, invalid_transfer
    severity: ViolationSeverity
    description: str

    # Context
    policy_id: str | None = None
    requirement_id: str | None = None
    storage_location_id: str | None = None
    transfer_request_id: str | None = None

    # Data involved
    data_classification: DataClassification | None = None
    region_id: str | None = None
    country_code: str | None = None

    # Detection
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    detected_by: str  # system, audit, manual
    detection_method: str | None = None

    # Resolution
    resolved: bool = False
    resolved_at: datetime | None = None
    resolved_by: str | None = None
    resolution_notes: str | None = None

    # Remediation
    remediation_required: bool = True
    remediation_deadline: datetime | None = None
    remediation_actions: list[str] = Field(default_factory=list)

    # Notifications
    notifications_sent: list[dict[str, Any]] = Field(default_factory=list)


# Default regions
DEFAULT_REGIONS = [
    {
        "id": "us-east-1",
        "name": "US East (N. Virginia)",
        "code": "us-east-1",
        "display_name": "US East",
        "country": "United States",
        "country_code": "US",
        "continent": "North America",
        "provider": "aws",
        "provider_region": "us-east-1",
        "compliance_certifications": ["SOC 2", "ISO 27001", "HIPAA", "FedRAMP"],
    },
    {
        "id": "us-west-2",
        "name": "US West (Oregon)",
        "code": "us-west-2",
        "display_name": "US West",
        "country": "United States",
        "country_code": "US",
        "continent": "North America",
        "provider": "aws",
        "provider_region": "us-west-2",
        "compliance_certifications": ["SOC 2", "ISO 27001", "HIPAA"],
    },
    {
        "id": "eu-west-1",
        "name": "EU (Ireland)",
        "code": "eu-west-1",
        "display_name": "EU Ireland",
        "country": "Ireland",
        "country_code": "IE",
        "continent": "Europe",
        "provider": "aws",
        "provider_region": "eu-west-1",
        "compliance_certifications": ["SOC 2", "ISO 27001", "GDPR"],
    },
    {
        "id": "eu-central-1",
        "name": "EU (Frankfurt)",
        "code": "eu-central-1",
        "display_name": "EU Frankfurt",
        "country": "Germany",
        "country_code": "DE",
        "continent": "Europe",
        "provider": "aws",
        "provider_region": "eu-central-1",
        "compliance_certifications": ["SOC 2", "ISO 27001", "GDPR", "C5"],
    },
    {
        "id": "ap-northeast-1",
        "name": "Asia Pacific (Tokyo)",
        "code": "ap-northeast-1",
        "display_name": "Asia Pacific Tokyo",
        "country": "Japan",
        "country_code": "JP",
        "continent": "Asia",
        "provider": "aws",
        "provider_region": "ap-northeast-1",
        "compliance_certifications": ["SOC 2", "ISO 27001", "ISMAP"],
    },
    {
        "id": "ap-southeast-1",
        "name": "Asia Pacific (Singapore)",
        "code": "ap-southeast-1",
        "display_name": "Asia Pacific Singapore",
        "country": "Singapore",
        "country_code": "SG",
        "continent": "Asia",
        "provider": "aws",
        "provider_region": "ap-southeast-1",
        "compliance_certifications": ["SOC 2", "ISO 27001", "MTCS"],
    },
    {
        "id": "ap-south-1",
        "name": "Asia Pacific (Mumbai)",
        "code": "ap-south-1",
        "display_name": "Asia Pacific Mumbai",
        "country": "India",
        "country_code": "IN",
        "continent": "Asia",
        "provider": "aws",
        "provider_region": "ap-south-1",
        "compliance_certifications": ["SOC 2", "ISO 27001"],
    },
    {
        "id": "sa-east-1",
        "name": "South America (São Paulo)",
        "code": "sa-east-1",
        "display_name": "South America",
        "country": "Brazil",
        "country_code": "BR",
        "continent": "South America",
        "provider": "aws",
        "provider_region": "sa-east-1",
        "compliance_certifications": ["SOC 2", "ISO 27001"],
    },
    {
        "id": "ca-central-1",
        "name": "Canada (Central)",
        "code": "ca-central-1",
        "display_name": "Canada",
        "country": "Canada",
        "country_code": "CA",
        "continent": "North America",
        "provider": "aws",
        "provider_region": "ca-central-1",
        "compliance_certifications": ["SOC 2", "ISO 27001", "PIPEDA"],
    },
    {
        "id": "ap-southeast-2",
        "name": "Asia Pacific (Sydney)",
        "code": "ap-southeast-2",
        "display_name": "Australia",
        "country": "Australia",
        "country_code": "AU",
        "continent": "Oceania",
        "provider": "aws",
        "provider_region": "ap-southeast-2",
        "compliance_certifications": ["SOC 2", "ISO 27001", "IRAP"],
    },
]

# GDPR EU adequacy countries
EU_ADEQUACY_COUNTRIES = [
    "AD", "AR", "CA", "FO", "GG", "IL", "IM", "JP", "JE", "NZ",
    "KR", "CH", "GB", "UY",
]

# EU/EEA member states
EU_EEA_COUNTRIES = [
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
    "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
    "PL", "PT", "RO", "SK", "SI", "ES", "SE",
    # EEA
    "IS", "LI", "NO",
]

# Default GDPR requirement
DEFAULT_GDPR_REQUIREMENT = {
    "id": "gdpr-default",
    "name": "GDPR Data Residency",
    "description": "Default GDPR data residency requirements for EU personal data",
    "data_classifications": [DataClassification.PII, DataClassification.CONFIDENTIAL],
    "allowed_countries": EU_EEA_COUNTRIES + EU_ADEQUACY_COUNTRIES,
    "allow_cross_border_transfer": True,
    "require_adequacy_decision": True,
    "require_sccs": True,
    "require_encryption_at_rest": True,
    "require_encryption_in_transit": True,
    "minimum_encryption_strength": 256,
    "regulation": "GDPR",
    "regulation_article": "Chapter V",
}
