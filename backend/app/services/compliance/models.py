"""Data models for Compliance services."""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# Common Enums
class ComplianceFramework(str, Enum):
    """Compliance framework types."""

    GDPR = "gdpr"
    SOC2 = "soc2"
    HIPAA = "hipaa"
    ISO27001 = "iso27001"
    PCI_DSS = "pci_dss"


class ComplianceStatus(str, Enum):
    """Overall compliance status."""

    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIAL = "partial"
    PENDING_REVIEW = "pending_review"
    NOT_APPLICABLE = "not_applicable"


# GDPR Models
class DataSubjectRequestType(str, Enum):
    """Types of data subject requests under GDPR."""

    ACCESS = "access"  # Right to access
    RECTIFICATION = "rectification"  # Right to rectification
    ERASURE = "erasure"  # Right to be forgotten
    PORTABILITY = "portability"  # Data portability
    RESTRICTION = "restriction"  # Restriction of processing
    OBJECTION = "objection"  # Right to object


class DataSubjectRequestStatus(str, Enum):
    """Status of a data subject request."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ConsentType(str, Enum):
    """Types of consent."""

    MARKETING = "marketing"
    ANALYTICS = "analytics"
    THIRD_PARTY = "third_party"
    DATA_PROCESSING = "data_processing"
    COOKIES = "cookies"
    COMMUNICATION = "communication"


class DataCategory(str, Enum):
    """Categories of personal data."""

    IDENTITY = "identity"  # Name, ID numbers
    CONTACT = "contact"  # Email, phone, address
    FINANCIAL = "financial"  # Payment info
    TECHNICAL = "technical"  # IP, device info
    BEHAVIORAL = "behavioral"  # Usage patterns
    PREFERENCES = "preferences"  # Settings, choices
    CONTENT = "content"  # User-generated content
    SENSITIVE = "sensitive"  # Special category data


class DataSubjectRequest(BaseModel):
    """A data subject request (DSR) under GDPR."""

    id: str
    user_id: str
    email: str
    request_type: DataSubjectRequestType
    status: DataSubjectRequestStatus = DataSubjectRequestStatus.PENDING
    reason: str | None = None

    # Processing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    deadline: datetime | None = None  # 30 days from creation
    processed_at: datetime | None = None
    processed_by: str | None = None

    # Response
    response_data: dict[str, Any] | None = None
    rejection_reason: str | None = None

    # Audit
    audit_trail: list[dict[str, Any]] = Field(default_factory=list)

    def __init__(self, **data):
        super().__init__(**data)
        if self.deadline is None:
            self.deadline = self.created_at + timedelta(days=30)


class ConsentRecord(BaseModel):
    """Record of user consent."""

    id: str
    user_id: str
    consent_type: ConsentType
    granted: bool
    version: str = "1.0"  # Policy version

    # Details
    purpose: str
    legal_basis: str = "consent"  # consent, contract, legal_obligation, etc.

    # Timestamps
    granted_at: datetime | None = None
    revoked_at: datetime | None = None
    expires_at: datetime | None = None

    # Audit
    ip_address: str | None = None
    user_agent: str | None = None
    source: str = "web"  # web, mobile, api


class DataRetentionPolicy(BaseModel):
    """Data retention policy configuration."""

    id: str
    name: str
    description: str
    data_category: DataCategory
    retention_period_days: int
    legal_basis: str

    # Actions
    action_on_expiry: str = "delete"  # delete, anonymize, archive
    requires_review: bool = False
    auto_execute: bool = True

    # Scope
    applies_to_tables: list[str] = Field(default_factory=list)
    applies_to_fields: list[str] = Field(default_factory=list)
    exceptions: list[str] = Field(default_factory=list)

    # Status
    enabled: bool = True
    last_executed: datetime | None = None
    next_execution: datetime | None = None


class PersonalDataInventory(BaseModel):
    """Inventory of personal data stored."""

    id: str
    data_category: DataCategory
    data_fields: list[str]
    storage_location: str  # Database, service name
    encryption: bool = True
    purpose: str
    legal_basis: str
    retention_period_days: int | None = None
    third_party_sharing: bool = False
    third_parties: list[str] = Field(default_factory=list)
    cross_border_transfer: bool = False
    transfer_countries: list[str] = Field(default_factory=list)


class GDPRComplianceReport(BaseModel):
    """GDPR compliance status report."""

    generated_at: datetime = Field(default_factory=datetime.utcnow)
    status: ComplianceStatus

    # DSR Metrics
    total_dsr_requests: int = 0
    pending_dsr_requests: int = 0
    completed_dsr_requests: int = 0
    avg_dsr_completion_days: float = 0.0
    overdue_dsr_requests: int = 0

    # Consent Metrics
    total_users: int = 0
    users_with_consent: int = 0
    consent_rate: float = 0.0

    # Retention Metrics
    retention_policies_count: int = 0
    retention_policies_executed: int = 0
    data_deleted_count: int = 0

    # Data Inventory
    data_categories_tracked: int = 0
    third_party_processors: int = 0
    cross_border_transfers: int = 0

    # Issues
    compliance_issues: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


# SOC 2 Models
class SOC2ControlCategory(str, Enum):
    """SOC 2 Trust Service Categories."""

    SECURITY = "security"  # CC (Common Criteria)
    AVAILABILITY = "availability"  # A
    PROCESSING_INTEGRITY = "processing_integrity"  # PI
    CONFIDENTIALITY = "confidentiality"  # C
    PRIVACY = "privacy"  # P


class SOC2ControlStatus(str, Enum):
    """Status of a SOC 2 control."""

    IMPLEMENTED = "implemented"
    PARTIALLY_IMPLEMENTED = "partially_implemented"
    NOT_IMPLEMENTED = "not_implemented"
    NOT_APPLICABLE = "not_applicable"
    UNDER_REVIEW = "under_review"


class SOC2EvidenceType(str, Enum):
    """Types of SOC 2 evidence."""

    POLICY = "policy"
    PROCEDURE = "procedure"
    SCREENSHOT = "screenshot"
    LOG = "log"
    REPORT = "report"
    CONFIGURATION = "configuration"
    ATTESTATION = "attestation"
    TRAINING_RECORD = "training_record"


class SOC2Control(BaseModel):
    """A SOC 2 control point."""

    id: str
    control_id: str  # e.g., CC1.1, A1.2
    category: SOC2ControlCategory
    title: str
    description: str
    status: SOC2ControlStatus = SOC2ControlStatus.NOT_IMPLEMENTED

    # Implementation
    implementation_notes: str | None = None
    owner: str | None = None
    last_reviewed: datetime | None = None
    next_review: datetime | None = None

    # Testing
    test_procedure: str | None = None
    test_frequency: str = "annual"  # annual, quarterly, monthly, continuous
    last_tested: datetime | None = None
    test_result: str | None = None

    # Risk
    risk_level: str = "medium"  # low, medium, high, critical
    compensating_controls: list[str] = Field(default_factory=list)


class SOC2Evidence(BaseModel):
    """Evidence for SOC 2 controls."""

    id: str
    control_id: str
    evidence_type: SOC2EvidenceType
    title: str
    description: str | None = None

    # Content
    file_path: str | None = None
    file_hash: str | None = None
    content: str | None = None
    url: str | None = None

    # Metadata
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    collected_by: str | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None

    # Status
    verified: bool = False
    verified_by: str | None = None
    verified_at: datetime | None = None


class AccessReviewRecord(BaseModel):
    """Record of access review for SOC 2."""

    id: str
    review_period: str  # e.g., "Q1 2024"
    reviewer: str
    review_date: datetime

    # Scope
    systems_reviewed: list[str] = Field(default_factory=list)
    users_reviewed: int = 0

    # Findings
    total_access_rights: int = 0
    access_removed: int = 0
    access_modified: int = 0
    exceptions_found: int = 0
    exceptions_approved: int = 0

    # Status
    status: str = "completed"  # in_progress, completed, pending_approval
    approved_by: str | None = None
    approved_at: datetime | None = None

    # Notes
    findings: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class ChangeRecord(BaseModel):
    """Change management record for SOC 2."""

    id: str
    change_id: str  # Ticket/CR number
    title: str
    description: str

    # Classification
    change_type: str = "standard"  # standard, emergency, normal
    risk_level: str = "low"  # low, medium, high
    category: str = "application"  # application, infrastructure, security, database

    # Workflow
    requested_by: str
    requested_at: datetime
    approved_by: str | None = None
    approved_at: datetime | None = None
    implemented_by: str | None = None
    implemented_at: datetime | None = None

    # Testing
    test_plan: str | None = None
    test_results: str | None = None
    tested_by: str | None = None

    # Rollback
    rollback_plan: str | None = None
    rollback_executed: bool = False

    # Status
    status: str = "pending"  # pending, approved, rejected, implemented, rolled_back


class SOC2ComplianceReport(BaseModel):
    """SOC 2 compliance status report."""

    generated_at: datetime = Field(default_factory=datetime.utcnow)
    report_period: str
    status: ComplianceStatus

    # Control Metrics
    total_controls: int = 0
    implemented_controls: int = 0
    partially_implemented: int = 0
    not_implemented: int = 0
    implementation_rate: float = 0.0

    # By Category
    security_status: ComplianceStatus = ComplianceStatus.PENDING_REVIEW
    availability_status: ComplianceStatus = ComplianceStatus.PENDING_REVIEW
    processing_integrity_status: ComplianceStatus = ComplianceStatus.PENDING_REVIEW
    confidentiality_status: ComplianceStatus = ComplianceStatus.PENDING_REVIEW
    privacy_status: ComplianceStatus = ComplianceStatus.PENDING_REVIEW

    # Evidence
    total_evidence: int = 0
    verified_evidence: int = 0
    expired_evidence: int = 0

    # Access Reviews
    access_reviews_completed: int = 0
    access_reviews_pending: int = 0

    # Change Management
    total_changes: int = 0
    approved_changes: int = 0
    emergency_changes: int = 0

    # Issues
    open_findings: int = 0
    findings: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


# Common Models
class AuditLogEntry(BaseModel):
    """Audit log entry for compliance tracking."""

    id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    framework: ComplianceFramework
    action: str
    actor: str
    actor_type: str = "user"  # user, system, automated
    resource_type: str
    resource_id: str
    details: dict[str, Any] = Field(default_factory=dict)
    ip_address: str | None = None
    user_agent: str | None = None
    outcome: str = "success"  # success, failure, partial
