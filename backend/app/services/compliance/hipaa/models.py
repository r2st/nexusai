"""Data models for HIPAA Compliance services."""

import re
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class PHICategory(str, Enum):
    """Categories of Protected Health Information (PHI)."""

    # Direct Identifiers (18 HIPAA identifiers)
    NAME = "name"
    ADDRESS = "address"
    DATES = "dates"  # Dates related to individual (DOB, admission, discharge, death)
    PHONE = "phone"
    FAX = "fax"
    EMAIL = "email"
    SSN = "ssn"
    MRN = "mrn"  # Medical Record Number
    HEALTH_PLAN_ID = "health_plan_id"
    ACCOUNT_NUMBER = "account_number"
    LICENSE_NUMBER = "license_number"
    VEHICLE_ID = "vehicle_id"
    DEVICE_ID = "device_id"
    URL = "url"
    IP_ADDRESS = "ip_address"
    BIOMETRIC = "biometric"
    PHOTO = "photo"
    OTHER_UNIQUE_ID = "other_unique_id"

    # Clinical Data
    DIAGNOSIS = "diagnosis"
    PROCEDURE = "procedure"
    MEDICATION = "medication"
    LAB_RESULT = "lab_result"
    VITAL_SIGN = "vital_sign"
    ALLERGY = "allergy"
    IMMUNIZATION = "immunization"

    # Administrative
    INSURANCE_INFO = "insurance_info"
    PROVIDER_INFO = "provider_info"
    FACILITY_INFO = "facility_info"


class PHIPattern(BaseModel):
    """A pattern for detecting PHI."""

    category: PHICategory
    pattern: str  # Regex pattern
    description: str
    confidence: float = 0.9  # Default confidence
    enabled: bool = True


class PHIDetectionResult(BaseModel):
    """Result of PHI detection in content."""

    id: str
    content_hash: str
    scan_timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Findings
    phi_found: bool = False
    findings: list[dict[str, Any]] = Field(default_factory=list)
    categories_detected: list[PHICategory] = Field(default_factory=list)

    # Statistics
    total_findings: int = 0
    high_confidence_findings: int = 0
    medium_confidence_findings: int = 0
    low_confidence_findings: int = 0

    # Recommendations
    redaction_required: bool = False
    recommendations: list[str] = Field(default_factory=list)


class BAAStatus(str, Enum):
    """Status of a Business Associate Agreement."""

    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    PENDING_SIGNATURE = "pending_signature"
    ACTIVE = "active"
    EXPIRED = "expired"
    TERMINATED = "terminated"
    RENEWED = "renewed"


class BAAType(str, Enum):
    """Types of Business Associate Agreements."""

    FULL_BAA = "full_baa"
    SUBCONTRACTOR_BAA = "subcontractor_baa"
    AMENDMENT = "amendment"
    ADDENDUM = "addendum"


class BAA(BaseModel):
    """Business Associate Agreement record."""

    id: str
    organization_id: str

    # Parties
    covered_entity: str  # Your organization or client
    business_associate: str  # The third party
    ba_contact_name: str | None = None
    ba_contact_email: str | None = None

    # Agreement Details
    baa_type: BAAType = BAAType.FULL_BAA
    status: BAAStatus = BAAStatus.DRAFT
    version: str = "1.0"

    # Dates
    effective_date: datetime | None = None
    expiration_date: datetime | None = None
    signed_date: datetime | None = None
    termination_date: datetime | None = None

    # Scope
    phi_categories_shared: list[PHICategory] = Field(default_factory=list)
    permitted_uses: list[str] = Field(default_factory=list)
    permitted_disclosures: list[str] = Field(default_factory=list)

    # Security Requirements
    encryption_required: bool = True
    minimum_security_standards: list[str] = Field(default_factory=list)
    breach_notification_hours: int = 24

    # Documents
    document_path: str | None = None
    signed_document_path: str | None = None

    # Audit
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str | None = None
    last_reviewed: datetime | None = None
    reviewed_by: str | None = None

    # Notes
    notes: str | None = None
    risk_assessment: str | None = None


class EncryptionStatus(str, Enum):
    """Encryption compliance status."""

    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIAL = "partial"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


class EncryptionAuditResult(BaseModel):
    """Result of encryption compliance audit."""

    id: str
    audit_timestamp: datetime = Field(default_factory=datetime.utcnow)
    auditor: str | None = None

    # Overall Status
    overall_status: EncryptionStatus = EncryptionStatus.UNKNOWN

    # Data at Rest
    data_at_rest_status: EncryptionStatus = EncryptionStatus.UNKNOWN
    data_at_rest_findings: list[dict[str, Any]] = Field(default_factory=list)
    storage_locations_audited: int = 0
    storage_locations_compliant: int = 0

    # Data in Transit
    data_in_transit_status: EncryptionStatus = EncryptionStatus.UNKNOWN
    data_in_transit_findings: list[dict[str, Any]] = Field(default_factory=list)
    endpoints_audited: int = 0
    endpoints_compliant: int = 0

    # Key Management
    key_management_status: EncryptionStatus = EncryptionStatus.UNKNOWN
    key_rotation_compliant: bool = False
    key_storage_compliant: bool = False

    # Algorithms
    algorithms_in_use: list[str] = Field(default_factory=list)
    weak_algorithms_found: list[str] = Field(default_factory=list)

    # Recommendations
    critical_issues: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class HIPAAControlCategory(str, Enum):
    """HIPAA Security Rule control categories."""

    ADMINISTRATIVE = "administrative"
    PHYSICAL = "physical"
    TECHNICAL = "technical"


class HIPAAControlStatus(str, Enum):
    """Status of a HIPAA control."""

    IMPLEMENTED = "implemented"
    PARTIALLY_IMPLEMENTED = "partially_implemented"
    NOT_IMPLEMENTED = "not_implemented"
    NOT_APPLICABLE = "not_applicable"


class HIPAAControl(BaseModel):
    """A HIPAA Security Rule control."""

    id: str
    control_id: str  # e.g., 164.308(a)(1)
    category: HIPAAControlCategory
    title: str
    description: str
    required: bool = True  # Required vs Addressable

    # Implementation
    status: HIPAAControlStatus = HIPAAControlStatus.NOT_IMPLEMENTED
    implementation_notes: str | None = None
    owner: str | None = None

    # Evidence
    evidence_ids: list[str] = Field(default_factory=list)
    last_reviewed: datetime | None = None

    # Risk
    risk_if_not_implemented: str = "high"
    compensating_controls: list[str] = Field(default_factory=list)


class MinimumNecessaryPolicy(BaseModel):
    """Minimum Necessary access policy."""

    id: str
    name: str
    description: str

    # Scope
    applies_to_roles: list[str] = Field(default_factory=list)
    applies_to_phi_categories: list[PHICategory] = Field(default_factory=list)

    # Access Rules
    permitted_actions: list[str] = Field(default_factory=list)  # read, write, delete
    max_records_per_query: int | None = None
    time_restriction: str | None = None  # e.g., "business_hours"

    # Justification
    requires_justification: bool = True
    auto_approve_roles: list[str] = Field(default_factory=list)

    # Status
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AccessJustification(BaseModel):
    """Justification for PHI access under Minimum Necessary."""

    id: str
    user_id: str
    policy_id: str

    # Request Details
    phi_categories_requested: list[PHICategory]
    purpose: str
    patient_id: str | None = None

    # Approval
    approved: bool = False
    approved_by: str | None = None
    approved_at: datetime | None = None
    denial_reason: str | None = None

    # Access Window
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    access_count: int = 0
    max_access_count: int | None = None

    # Audit
    created_at: datetime = Field(default_factory=datetime.utcnow)


class HIPAAComplianceReport(BaseModel):
    """HIPAA compliance status report."""

    generated_at: datetime = Field(default_factory=datetime.utcnow)
    report_period: str

    # Overall Status
    overall_compliant: bool = False
    compliance_score: float = 0.0

    # Controls
    total_controls: int = 0
    implemented_controls: int = 0
    partially_implemented: int = 0
    not_implemented: int = 0

    # By Category
    administrative_status: HIPAAControlStatus = HIPAAControlStatus.NOT_IMPLEMENTED
    physical_status: HIPAAControlStatus = HIPAAControlStatus.NOT_IMPLEMENTED
    technical_status: HIPAAControlStatus = HIPAAControlStatus.NOT_IMPLEMENTED

    # PHI Protection
    phi_inventory_complete: bool = False
    phi_categories_tracked: int = 0

    # BAA Status
    total_baas: int = 0
    active_baas: int = 0
    expiring_baas: int = 0  # Expiring within 90 days

    # Encryption
    encryption_audit_status: EncryptionStatus = EncryptionStatus.UNKNOWN
    data_at_rest_compliant: bool = False
    data_in_transit_compliant: bool = False

    # Minimum Necessary
    access_policies_count: int = 0
    access_requests_reviewed: int = 0
    access_requests_denied: int = 0

    # Issues
    critical_findings: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


# Default HIPAA Security Rule Controls
DEFAULT_HIPAA_CONTROLS = [
    # Administrative Safeguards (164.308)
    {"control_id": "164.308(a)(1)(i)", "category": HIPAAControlCategory.ADMINISTRATIVE, "title": "Security Management Process", "description": "Implement policies and procedures to prevent, detect, contain, and correct security violations.", "required": True},
    {"control_id": "164.308(a)(1)(ii)(A)", "category": HIPAAControlCategory.ADMINISTRATIVE, "title": "Risk Analysis", "description": "Conduct an accurate and thorough assessment of potential risks and vulnerabilities.", "required": True},
    {"control_id": "164.308(a)(1)(ii)(B)", "category": HIPAAControlCategory.ADMINISTRATIVE, "title": "Risk Management", "description": "Implement security measures sufficient to reduce risks and vulnerabilities.", "required": True},
    {"control_id": "164.308(a)(1)(ii)(C)", "category": HIPAAControlCategory.ADMINISTRATIVE, "title": "Sanction Policy", "description": "Apply appropriate sanctions against workforce members who fail to comply.", "required": True},
    {"control_id": "164.308(a)(1)(ii)(D)", "category": HIPAAControlCategory.ADMINISTRATIVE, "title": "Information System Activity Review", "description": "Implement procedures to regularly review records of system activity.", "required": True},
    {"control_id": "164.308(a)(2)", "category": HIPAAControlCategory.ADMINISTRATIVE, "title": "Assigned Security Responsibility", "description": "Identify the security official responsible for developing and implementing policies.", "required": True},
    {"control_id": "164.308(a)(3)(i)", "category": HIPAAControlCategory.ADMINISTRATIVE, "title": "Workforce Security", "description": "Implement policies and procedures to ensure appropriate access for workforce members.", "required": True},
    {"control_id": "164.308(a)(4)(i)", "category": HIPAAControlCategory.ADMINISTRATIVE, "title": "Information Access Management", "description": "Implement policies and procedures for authorizing access to ePHI.", "required": True},
    {"control_id": "164.308(a)(5)(i)", "category": HIPAAControlCategory.ADMINISTRATIVE, "title": "Security Awareness and Training", "description": "Implement a security awareness and training program for all workforce members.", "required": False},
    {"control_id": "164.308(a)(6)(i)", "category": HIPAAControlCategory.ADMINISTRATIVE, "title": "Security Incident Procedures", "description": "Implement policies and procedures to address security incidents.", "required": True},
    {"control_id": "164.308(a)(7)(i)", "category": HIPAAControlCategory.ADMINISTRATIVE, "title": "Contingency Plan", "description": "Establish policies and procedures for responding to emergencies.", "required": True},
    {"control_id": "164.308(a)(8)", "category": HIPAAControlCategory.ADMINISTRATIVE, "title": "Evaluation", "description": "Perform periodic technical and non-technical evaluation.", "required": True},
    {"control_id": "164.308(b)(1)", "category": HIPAAControlCategory.ADMINISTRATIVE, "title": "Business Associate Contracts", "description": "Obtain satisfactory assurances from business associates.", "required": True},

    # Physical Safeguards (164.310)
    {"control_id": "164.310(a)(1)", "category": HIPAAControlCategory.PHYSICAL, "title": "Facility Access Controls", "description": "Implement policies to limit physical access to electronic information systems.", "required": True},
    {"control_id": "164.310(b)", "category": HIPAAControlCategory.PHYSICAL, "title": "Workstation Use", "description": "Implement policies specifying proper functions and physical attributes of workstations.", "required": True},
    {"control_id": "164.310(c)", "category": HIPAAControlCategory.PHYSICAL, "title": "Workstation Security", "description": "Implement physical safeguards for workstations that access ePHI.", "required": True},
    {"control_id": "164.310(d)(1)", "category": HIPAAControlCategory.PHYSICAL, "title": "Device and Media Controls", "description": "Implement policies governing the receipt and removal of hardware and electronic media.", "required": True},

    # Technical Safeguards (164.312)
    {"control_id": "164.312(a)(1)", "category": HIPAAControlCategory.TECHNICAL, "title": "Access Control", "description": "Implement technical policies to allow access only to authorized persons.", "required": True},
    {"control_id": "164.312(a)(2)(i)", "category": HIPAAControlCategory.TECHNICAL, "title": "Unique User Identification", "description": "Assign a unique name and/or number for identifying and tracking user identity.", "required": True},
    {"control_id": "164.312(a)(2)(ii)", "category": HIPAAControlCategory.TECHNICAL, "title": "Emergency Access Procedure", "description": "Establish procedures for obtaining necessary ePHI during an emergency.", "required": True},
    {"control_id": "164.312(a)(2)(iii)", "category": HIPAAControlCategory.TECHNICAL, "title": "Automatic Logoff", "description": "Implement electronic procedures that terminate sessions after inactivity.", "required": False},
    {"control_id": "164.312(a)(2)(iv)", "category": HIPAAControlCategory.TECHNICAL, "title": "Encryption and Decryption", "description": "Implement a mechanism to encrypt and decrypt ePHI.", "required": False},
    {"control_id": "164.312(b)", "category": HIPAAControlCategory.TECHNICAL, "title": "Audit Controls", "description": "Implement hardware, software, and procedures to record and examine activity.", "required": True},
    {"control_id": "164.312(c)(1)", "category": HIPAAControlCategory.TECHNICAL, "title": "Integrity", "description": "Implement policies to protect ePHI from improper alteration or destruction.", "required": True},
    {"control_id": "164.312(d)", "category": HIPAAControlCategory.TECHNICAL, "title": "Person or Entity Authentication", "description": "Implement procedures to verify that a person seeking access is the one claimed.", "required": True},
    {"control_id": "164.312(e)(1)", "category": HIPAAControlCategory.TECHNICAL, "title": "Transmission Security", "description": "Implement technical security measures to guard against unauthorized access during transmission.", "required": True},
]
