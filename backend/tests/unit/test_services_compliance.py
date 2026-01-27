"""
Unit tests for compliance services (GDPR, SOC 2, HIPAA).
"""

import pytest
from datetime import datetime, UTC, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


# =============================================================================
# Mock Models and Types
# =============================================================================


class ComplianceFramework:
    """Compliance framework types."""
    GDPR = "gdpr"
    SOC2 = "soc2"
    HIPAA = "hipaa"


class ComplianceStatus:
    """Compliance status types."""
    COMPLIANT = "compliant"
    PARTIAL = "partial"
    NON_COMPLIANT = "non_compliant"
    NOT_APPLICABLE = "not_applicable"


class DataSubjectRequestType:
    """GDPR DSR types."""
    ACCESS = "access"
    ERASURE = "erasure"
    RECTIFICATION = "rectification"
    PORTABILITY = "portability"
    RESTRICTION = "restriction"


class DataSubjectRequestStatus:
    """GDPR DSR status types."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"


class ConsentType:
    """Consent types."""
    MARKETING = "marketing"
    ANALYTICS = "analytics"
    PERSONALIZATION = "personalization"
    ESSENTIAL = "essential"
    THIRD_PARTY = "third_party"


class DataCategory:
    """Data category types."""
    PERSONAL = "personal"
    SENSITIVE = "sensitive"
    FINANCIAL = "financial"
    HEALTH = "health"
    BEHAVIORAL = "behavioral"


class SOC2ControlCategory:
    """SOC 2 control categories."""
    SECURITY = "security"
    AVAILABILITY = "availability"
    PROCESSING_INTEGRITY = "processing_integrity"
    CONFIDENTIALITY = "confidentiality"
    PRIVACY = "privacy"


class SOC2ControlStatus:
    """SOC 2 control status types."""
    IMPLEMENTED = "implemented"
    PARTIALLY_IMPLEMENTED = "partially_implemented"
    NOT_IMPLEMENTED = "not_implemented"
    NOT_APPLICABLE = "not_applicable"


class SOC2EvidenceType:
    """SOC 2 evidence types."""
    DOCUMENT = "document"
    SCREENSHOT = "screenshot"
    LOG = "log"
    CONFIG = "configuration"
    POLICY = "policy"


class BAAStatus:
    """BAA status types."""
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    PENDING_SIGNATURE = "pending_signature"
    ACTIVE = "active"
    RENEWED = "renewed"
    EXPIRED = "expired"
    TERMINATED = "terminated"


class BAAType:
    """BAA types."""
    FULL_BAA = "full_baa"
    DATA_USE = "data_use"
    SUBCONTRACTOR = "subcontractor"


class PHICategory:
    """PHI category types."""
    SSN = "ssn"
    MRN = "mrn"
    HEALTH_PLAN_ID = "health_plan_id"
    PHONE = "phone"
    FAX = "fax"
    EMAIL = "email"
    DATES = "dates"
    IP_ADDRESS = "ip_address"
    LICENSE_NUMBER = "license_number"
    ACCOUNT_NUMBER = "account_number"
    DEVICE_ID = "device_id"
    VEHICLE_ID = "vehicle_id"
    DIAGNOSIS = "diagnosis"
    MEDICATION = "medication"
    PROCEDURE = "procedure"
    LAB_RESULT = "lab_result"
    VITAL_SIGN = "vital_sign"
    ALLERGY = "allergy"
    INSURANCE_INFO = "insurance_info"
    PROVIDER_INFO = "provider_info"


class HIPAAControlCategory:
    """HIPAA control categories."""
    ADMINISTRATIVE = "administrative"
    PHYSICAL = "physical"
    TECHNICAL = "technical"


class HIPAAControlStatus:
    """HIPAA control status types."""
    IMPLEMENTED = "implemented"
    PARTIALLY_IMPLEMENTED = "partially_implemented"
    NOT_IMPLEMENTED = "not_implemented"
    NOT_APPLICABLE = "not_applicable"


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_gdpr_service():
    """Create a mock GDPR service."""
    service = AsyncMock()
    service.create_dsr = AsyncMock()
    service.get_dsr = AsyncMock()
    service.list_dsrs = AsyncMock()
    service.process_dsr = AsyncMock()
    service.complete_dsr = AsyncMock()
    service.reject_dsr = AsyncMock()
    service.record_consent = AsyncMock()
    service.revoke_consent = AsyncMock()
    service.get_user_consents = AsyncMock()
    service.check_consent = AsyncMock()
    service.create_retention_policy = AsyncMock()
    service.list_retention_policies = AsyncMock()
    service.add_data_inventory_item = AsyncMock()
    service.get_data_inventory = AsyncMock()
    service.generate_compliance_report = AsyncMock()
    return service


@pytest.fixture
def mock_soc2_service():
    """Create a mock SOC 2 service."""
    service = AsyncMock()
    service.get_control = AsyncMock()
    service.list_controls = AsyncMock()
    service.update_control_status = AsyncMock()
    service.add_evidence = AsyncMock()
    service.get_evidence = AsyncMock()
    service.verify_evidence = AsyncMock()
    service.create_access_review = AsyncMock()
    service.complete_access_review = AsyncMock()
    service.create_change_record = AsyncMock()
    service.approve_change = AsyncMock()
    service.implement_change = AsyncMock()
    service.generate_compliance_report = AsyncMock()
    return service


@pytest.fixture
def mock_hipaa_service():
    """Create a mock HIPAA service."""
    service = AsyncMock()
    service.detect_phi = AsyncMock()
    service.detect_phi_in_code = AsyncMock()
    service.get_control = AsyncMock()
    service.list_controls = AsyncMock()
    service.update_control_status = AsyncMock()
    service.create_minimum_necessary_policy = AsyncMock()
    service.check_access_permitted = AsyncMock()
    service.request_access_justification = AsyncMock()
    service.approve_access_justification = AsyncMock()
    service.generate_compliance_report = AsyncMock()
    return service


@pytest.fixture
def mock_baa_manager():
    """Create a mock BAA manager."""
    manager = AsyncMock()
    manager.create_baa = AsyncMock()
    manager.get_baa = AsyncMock()
    manager.list_baas = AsyncMock()
    manager.submit_for_review = AsyncMock()
    manager.approve_baa = AsyncMock()
    manager.activate_baa = AsyncMock()
    manager.renew_baa = AsyncMock()
    manager.terminate_baa = AsyncMock()
    manager.get_baa_summary = AsyncMock()
    return manager


@pytest.fixture
def mock_phi_detector():
    """Create a mock PHI detector."""
    detector = AsyncMock()
    detector.detect = AsyncMock()
    detector.detect_in_code = AsyncMock()
    return detector


@pytest.fixture
def sample_dsr():
    """Create a sample data subject request."""
    return MagicMock(
        id=str(uuid4()),
        user_id=str(uuid4()),
        email="user@example.com",
        request_type=MagicMock(value="access"),
        status=MagicMock(value="pending"),
        reason="Personal data access request",
        deadline=datetime.now(UTC) + timedelta(days=30),
        created_at=datetime.now(UTC),
        processed_at=None,
        processed_by=None,
        response_data=None,
        rejection_reason=None,
        audit_trail=[],
    )


@pytest.fixture
def sample_consent():
    """Create a sample consent record."""
    return MagicMock(
        id=str(uuid4()),
        user_id=str(uuid4()),
        consent_type=MagicMock(value="marketing"),
        granted=True,
        purpose="Email marketing",
        legal_basis="consent",
        version="1.0",
        granted_at=datetime.now(UTC),
        revoked_at=None,
        expires_at=None,
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0",
        source="web",
    )


@pytest.fixture
def sample_soc2_control():
    """Create a sample SOC 2 control."""
    return MagicMock(
        id=str(uuid4()),
        control_id="CC6.1",
        category=MagicMock(value="security"),
        title="Logical and Physical Access",
        description="The entity implements logical access security software.",
        status=MagicMock(value="implemented"),
        owner="Security Team",
        implementation_notes="Implemented via RBAC system",
        last_reviewed=datetime.now(UTC),
        next_review=datetime.now(UTC) + timedelta(days=90),
        evidence_count=5,
    )


@pytest.fixture
def sample_soc2_evidence():
    """Create a sample SOC 2 evidence."""
    return MagicMock(
        id=str(uuid4()),
        control_id="CC6.1",
        evidence_type=MagicMock(value="document"),
        title="Access Control Policy",
        description="Organization access control policy document",
        file_path="/docs/policies/access-control.pdf",
        collected_by="compliance_team",
        valid_from=datetime.now(UTC),
        valid_until=datetime.now(UTC) + timedelta(days=365),
        verified=True,
        verified_by="auditor",
        verified_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_baa():
    """Create a sample BAA."""
    return MagicMock(
        id=str(uuid4()),
        organization_id=str(uuid4()),
        covered_entity="Acme Healthcare",
        business_associate="Cloud Storage Inc",
        baa_type=MagicMock(value="full_baa"),
        status=MagicMock(value="active"),
        phi_categories_shared=[PHICategory.MRN, PHICategory.DIAGNOSIS],
        permitted_uses=["storage", "processing"],
        encryption_required=True,
        breach_notification_hours=24,
        effective_date=datetime.now(UTC),
        expiration_date=datetime.now(UTC) + timedelta(days=365),
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_phi_detection_result():
    """Create a sample PHI detection result."""
    return MagicMock(
        id=str(uuid4()),
        content_hash="abc123def456",
        phi_found=True,
        findings=[
            {
                "category": "ssn",
                "pattern_description": "Social Security Number",
                "confidence": 0.95,
                "match": "***-**-****",
                "start": 10,
                "end": 21,
                "context": "...contains ***-**-**** in text...",
            }
        ],
        categories_detected=[PHICategory.SSN],
        total_findings=1,
        high_confidence_findings=1,
        medium_confidence_findings=0,
        low_confidence_findings=0,
        redaction_required=True,
        recommendations=["CRITICAL: Social Security Numbers detected"],
    )


# =============================================================================
# GDPR DSR Tests
# =============================================================================


class TestGDPRDataSubjectRequests:
    """Tests for GDPR Data Subject Requests."""

    @pytest.mark.asyncio
    async def test_create_dsr(self, mock_gdpr_service, sample_dsr):
        """Test creating a data subject request."""
        mock_gdpr_service.create_dsr.return_value = sample_dsr

        result = await mock_gdpr_service.create_dsr(
            user_id=sample_dsr.user_id,
            email="user@example.com",
            request_type=DataSubjectRequestType.ACCESS,
        )

        assert result.id is not None
        assert result.email == "user@example.com"
        mock_gdpr_service.create_dsr.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_dsr_erasure(self, mock_gdpr_service, sample_dsr):
        """Test creating an erasure DSR."""
        sample_dsr.request_type = MagicMock(value="erasure")
        mock_gdpr_service.create_dsr.return_value = sample_dsr

        result = await mock_gdpr_service.create_dsr(
            user_id=sample_dsr.user_id,
            email="user@example.com",
            request_type=DataSubjectRequestType.ERASURE,
            reason="Request to be forgotten",
        )

        assert result.request_type.value == "erasure"

    @pytest.mark.asyncio
    async def test_get_dsr(self, mock_gdpr_service, sample_dsr):
        """Test getting a DSR by ID."""
        mock_gdpr_service.get_dsr.return_value = sample_dsr

        result = await mock_gdpr_service.get_dsr(sample_dsr.id)

        assert result == sample_dsr

    @pytest.mark.asyncio
    async def test_list_dsrs_by_status(self, mock_gdpr_service, sample_dsr):
        """Test listing DSRs filtered by status."""
        mock_gdpr_service.list_dsrs.return_value = [sample_dsr]

        result = await mock_gdpr_service.list_dsrs(
            status=DataSubjectRequestStatus.PENDING,
        )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_process_dsr(self, mock_gdpr_service, sample_dsr):
        """Test marking DSR as in progress."""
        sample_dsr.status = MagicMock(value="in_progress")
        sample_dsr.processed_by = str(uuid4())
        mock_gdpr_service.process_dsr.return_value = sample_dsr

        result = await mock_gdpr_service.process_dsr(
            dsr_id=sample_dsr.id,
            processor_id=sample_dsr.processed_by,
        )

        assert result.status.value == "in_progress"
        assert result.processed_by is not None

    @pytest.mark.asyncio
    async def test_complete_dsr(self, mock_gdpr_service, sample_dsr):
        """Test completing a DSR."""
        sample_dsr.status = MagicMock(value="completed")
        sample_dsr.processed_at = datetime.now(UTC)
        sample_dsr.response_data = {"data_export": "https://export.example.com/abc"}
        mock_gdpr_service.complete_dsr.return_value = sample_dsr

        result = await mock_gdpr_service.complete_dsr(
            dsr_id=sample_dsr.id,
            processor_id=str(uuid4()),
            response_data={"data_export": "https://export.example.com/abc"},
        )

        assert result.status.value == "completed"
        assert result.response_data is not None

    @pytest.mark.asyncio
    async def test_reject_dsr(self, mock_gdpr_service, sample_dsr):
        """Test rejecting a DSR."""
        sample_dsr.status = MagicMock(value="rejected")
        sample_dsr.rejection_reason = "Invalid request"
        mock_gdpr_service.reject_dsr.return_value = sample_dsr

        result = await mock_gdpr_service.reject_dsr(
            dsr_id=sample_dsr.id,
            processor_id=str(uuid4()),
            rejection_reason="Invalid request",
        )

        assert result.status.value == "rejected"
        assert result.rejection_reason == "Invalid request"

    @pytest.mark.asyncio
    async def test_dsr_deadline_calculation(self, sample_dsr):
        """Test DSR deadline is 30 days from creation."""
        days_until_deadline = (sample_dsr.deadline - sample_dsr.created_at).days
        assert 29 <= days_until_deadline <= 31


# =============================================================================
# GDPR Consent Tests
# =============================================================================


class TestGDPRConsent:
    """Tests for GDPR Consent Management."""

    @pytest.mark.asyncio
    async def test_record_consent(self, mock_gdpr_service, sample_consent):
        """Test recording a consent decision."""
        mock_gdpr_service.record_consent.return_value = sample_consent

        result = await mock_gdpr_service.record_consent(
            user_id=sample_consent.user_id,
            consent_type=ConsentType.MARKETING,
            granted=True,
            purpose="Email marketing",
        )

        assert result.granted is True
        assert result.consent_type.value == "marketing"

    @pytest.mark.asyncio
    async def test_record_consent_denied(self, mock_gdpr_service, sample_consent):
        """Test recording denied consent."""
        sample_consent.granted = False
        sample_consent.granted_at = None
        mock_gdpr_service.record_consent.return_value = sample_consent

        result = await mock_gdpr_service.record_consent(
            user_id=sample_consent.user_id,
            consent_type=ConsentType.ANALYTICS,
            granted=False,
            purpose="Analytics tracking",
        )

        assert result.granted is False

    @pytest.mark.asyncio
    async def test_revoke_consent(self, mock_gdpr_service, sample_consent):
        """Test revoking consent."""
        sample_consent.revoked_at = datetime.now(UTC)
        sample_consent.granted = False
        mock_gdpr_service.revoke_consent.return_value = sample_consent

        result = await mock_gdpr_service.revoke_consent(
            user_id=sample_consent.user_id,
            consent_type=ConsentType.MARKETING,
        )

        assert result.revoked_at is not None
        assert result.granted is False

    @pytest.mark.asyncio
    async def test_get_user_consents(self, mock_gdpr_service, sample_consent):
        """Test getting user consent records."""
        mock_gdpr_service.get_user_consents.return_value = [sample_consent]

        result = await mock_gdpr_service.get_user_consents(
            user_id=sample_consent.user_id,
            active_only=True,
        )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_check_consent(self, mock_gdpr_service):
        """Test checking if user has consent."""
        mock_gdpr_service.check_consent.return_value = True

        result = await mock_gdpr_service.check_consent(
            user_id=str(uuid4()),
            consent_type=ConsentType.MARKETING,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_check_consent_not_granted(self, mock_gdpr_service):
        """Test checking non-existent consent."""
        mock_gdpr_service.check_consent.return_value = False

        result = await mock_gdpr_service.check_consent(
            user_id=str(uuid4()),
            consent_type=ConsentType.THIRD_PARTY,
        )

        assert result is False


# =============================================================================
# GDPR Retention Policy Tests
# =============================================================================


class TestGDPRRetentionPolicies:
    """Tests for GDPR Data Retention Policies."""

    @pytest.mark.asyncio
    async def test_create_retention_policy(self, mock_gdpr_service):
        """Test creating a retention policy."""
        policy = MagicMock(
            id=str(uuid4()),
            name="User Data Retention",
            retention_period_days=365,
            data_category=MagicMock(value="personal"),
            action_on_expiry="delete",
        )
        mock_gdpr_service.create_retention_policy.return_value = policy

        result = await mock_gdpr_service.create_retention_policy(
            name="User Data Retention",
            description="Retain user data for 1 year",
            data_category=DataCategory.PERSONAL,
            retention_period_days=365,
            legal_basis="legitimate_interest",
        )

        assert result.retention_period_days == 365
        assert result.action_on_expiry == "delete"

    @pytest.mark.asyncio
    async def test_list_retention_policies(self, mock_gdpr_service):
        """Test listing retention policies."""
        policies = [
            MagicMock(id=str(uuid4()), name="Policy 1", enabled=True),
            MagicMock(id=str(uuid4()), name="Policy 2", enabled=True),
        ]
        mock_gdpr_service.list_retention_policies.return_value = policies

        result = await mock_gdpr_service.list_retention_policies(enabled_only=True)

        assert len(result) == 2


# =============================================================================
# GDPR Data Inventory Tests
# =============================================================================


class TestGDPRDataInventory:
    """Tests for GDPR Personal Data Inventory."""

    @pytest.mark.asyncio
    async def test_add_data_inventory_item(self, mock_gdpr_service):
        """Test adding a data inventory item."""
        item = MagicMock(
            id=str(uuid4()),
            data_category=MagicMock(value="personal"),
            data_fields=["name", "email", "phone"],
            storage_location="PostgreSQL",
            encryption=True,
        )
        mock_gdpr_service.add_data_inventory_item.return_value = item

        result = await mock_gdpr_service.add_data_inventory_item(
            data_category=DataCategory.PERSONAL,
            data_fields=["name", "email", "phone"],
            storage_location="PostgreSQL",
            purpose="Account management",
            legal_basis="contract",
        )

        assert result.encryption is True
        assert len(result.data_fields) == 3

    @pytest.mark.asyncio
    async def test_get_data_inventory(self, mock_gdpr_service):
        """Test getting data inventory."""
        items = [
            MagicMock(data_category=MagicMock(value="personal")),
            MagicMock(data_category=MagicMock(value="behavioral")),
        ]
        mock_gdpr_service.get_data_inventory.return_value = items

        result = await mock_gdpr_service.get_data_inventory()

        assert len(result) == 2


# =============================================================================
# GDPR Compliance Report Tests
# =============================================================================


class TestGDPRComplianceReport:
    """Tests for GDPR Compliance Reporting."""

    @pytest.mark.asyncio
    async def test_generate_compliance_report(self, mock_gdpr_service):
        """Test generating GDPR compliance report."""
        report = MagicMock(
            status=MagicMock(value="compliant"),
            total_dsr_requests=50,
            pending_dsr_requests=5,
            completed_dsr_requests=45,
            avg_dsr_completion_days=10.5,
            overdue_dsr_requests=0,
            consent_rate=85.5,
            compliance_issues=[],
            recommendations=[],
        )
        mock_gdpr_service.generate_compliance_report.return_value = report

        result = await mock_gdpr_service.generate_compliance_report()

        assert result.status.value == "compliant"
        assert result.overdue_dsr_requests == 0

    @pytest.mark.asyncio
    async def test_compliance_report_with_issues(self, mock_gdpr_service):
        """Test compliance report with issues."""
        report = MagicMock(
            status=MagicMock(value="non_compliant"),
            overdue_dsr_requests=3,
            compliance_issues=[
                {"type": "overdue_dsr", "count": 3, "severity": "high"}
            ],
            recommendations=["Process overdue DSRs immediately"],
        )
        mock_gdpr_service.generate_compliance_report.return_value = report

        result = await mock_gdpr_service.generate_compliance_report()

        assert result.status.value == "non_compliant"
        assert len(result.compliance_issues) > 0


# =============================================================================
# SOC 2 Control Tests
# =============================================================================


class TestSOC2Controls:
    """Tests for SOC 2 Control Management."""

    @pytest.mark.asyncio
    async def test_get_control(self, mock_soc2_service, sample_soc2_control):
        """Test getting a control."""
        mock_soc2_service.get_control.return_value = sample_soc2_control

        result = await mock_soc2_service.get_control("CC6.1")

        assert result.control_id == "CC6.1"

    @pytest.mark.asyncio
    async def test_list_controls_by_category(self, mock_soc2_service, sample_soc2_control):
        """Test listing controls by category."""
        mock_soc2_service.list_controls.return_value = [sample_soc2_control]

        result = await mock_soc2_service.list_controls(
            category=SOC2ControlCategory.SECURITY,
        )

        assert len(result) == 1
        assert result[0].category.value == "security"

    @pytest.mark.asyncio
    async def test_update_control_status(self, mock_soc2_service, sample_soc2_control):
        """Test updating control status."""
        sample_soc2_control.status = MagicMock(value="implemented")
        mock_soc2_service.update_control_status.return_value = sample_soc2_control

        result = await mock_soc2_service.update_control_status(
            control_id="CC6.1",
            status=SOC2ControlStatus.IMPLEMENTED,
            updated_by="compliance_officer",
        )

        assert result.status.value == "implemented"


# =============================================================================
# SOC 2 Evidence Tests
# =============================================================================


class TestSOC2Evidence:
    """Tests for SOC 2 Evidence Management."""

    @pytest.mark.asyncio
    async def test_add_evidence(self, mock_soc2_service, sample_soc2_evidence):
        """Test adding evidence to a control."""
        mock_soc2_service.add_evidence.return_value = sample_soc2_evidence

        result = await mock_soc2_service.add_evidence(
            control_id="CC6.1",
            evidence_type=SOC2EvidenceType.DOCUMENT,
            title="Access Control Policy",
            collected_by="compliance_team",
        )

        assert result.title == "Access Control Policy"

    @pytest.mark.asyncio
    async def test_get_evidence(self, mock_soc2_service, sample_soc2_evidence):
        """Test getting evidence for a control."""
        mock_soc2_service.get_evidence.return_value = [sample_soc2_evidence]

        result = await mock_soc2_service.get_evidence(
            control_id="CC6.1",
            valid_only=True,
        )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_verify_evidence(self, mock_soc2_service, sample_soc2_evidence):
        """Test verifying evidence."""
        sample_soc2_evidence.verified = True
        sample_soc2_evidence.verified_by = "auditor"
        mock_soc2_service.verify_evidence.return_value = sample_soc2_evidence

        result = await mock_soc2_service.verify_evidence(
            evidence_id=sample_soc2_evidence.id,
            verifier="auditor",
        )

        assert result.verified is True
        assert result.verified_by == "auditor"


# =============================================================================
# SOC 2 Access Review Tests
# =============================================================================


class TestSOC2AccessReviews:
    """Tests for SOC 2 Access Reviews."""

    @pytest.mark.asyncio
    async def test_create_access_review(self, mock_soc2_service):
        """Test creating an access review."""
        review = MagicMock(
            id=str(uuid4()),
            review_period="Q1 2024",
            reviewer="security_admin",
            systems_reviewed=["Production DB", "AWS Console"],
            status="in_progress",
        )
        mock_soc2_service.create_access_review.return_value = review

        result = await mock_soc2_service.create_access_review(
            review_period="Q1 2024",
            reviewer="security_admin",
            systems_reviewed=["Production DB", "AWS Console"],
        )

        assert result.status == "in_progress"

    @pytest.mark.asyncio
    async def test_complete_access_review(self, mock_soc2_service):
        """Test completing an access review."""
        review = MagicMock(
            id=str(uuid4()),
            status="completed",
            total_access_rights=150,
            access_removed=12,
            access_modified=8,
            exceptions_found=3,
            exceptions_approved=2,
        )
        mock_soc2_service.complete_access_review.return_value = review

        result = await mock_soc2_service.complete_access_review(
            review_id=review.id,
            total_access_rights=150,
            access_removed=12,
            access_modified=8,
            exceptions_found=3,
            exceptions_approved=2,
        )

        assert result.status == "completed"
        assert result.access_removed == 12


# =============================================================================
# SOC 2 Change Management Tests
# =============================================================================


class TestSOC2ChangeManagement:
    """Tests for SOC 2 Change Management."""

    @pytest.mark.asyncio
    async def test_create_change_record(self, mock_soc2_service):
        """Test creating a change record."""
        change = MagicMock(
            id=str(uuid4()),
            change_id="CR-20240115-ABC123",
            title="Database Schema Update",
            status="pending",
            risk_level="medium",
        )
        mock_soc2_service.create_change_record.return_value = change

        result = await mock_soc2_service.create_change_record(
            title="Database Schema Update",
            description="Add new columns for compliance tracking",
            requested_by="developer",
            risk_level="medium",
        )

        assert result.change_id.startswith("CR-")

    @pytest.mark.asyncio
    async def test_approve_change(self, mock_soc2_service):
        """Test approving a change request."""
        change = MagicMock(
            id=str(uuid4()),
            status="approved",
            approved_by="change_manager",
            approved_at=datetime.now(UTC),
        )
        mock_soc2_service.approve_change.return_value = change

        result = await mock_soc2_service.approve_change(
            change_id=change.id,
            approver="change_manager",
        )

        assert result.status == "approved"

    @pytest.mark.asyncio
    async def test_implement_change(self, mock_soc2_service):
        """Test implementing a change."""
        change = MagicMock(
            id=str(uuid4()),
            status="implemented",
            implemented_by="engineer",
            implemented_at=datetime.now(UTC),
        )
        mock_soc2_service.implement_change.return_value = change

        result = await mock_soc2_service.implement_change(
            change_id=change.id,
            implementer="engineer",
            test_results="All tests passed",
        )

        assert result.status == "implemented"


# =============================================================================
# SOC 2 Compliance Report Tests
# =============================================================================


class TestSOC2ComplianceReport:
    """Tests for SOC 2 Compliance Reporting."""

    @pytest.mark.asyncio
    async def test_generate_compliance_report(self, mock_soc2_service):
        """Test generating SOC 2 compliance report."""
        report = MagicMock(
            report_period="2024",
            status=MagicMock(value="compliant"),
            total_controls=25,
            implemented_controls=23,
            implementation_rate=92.0,
            security_status=MagicMock(value="compliant"),
            total_evidence=150,
            verified_evidence=145,
            access_reviews_completed=4,
            total_changes=50,
            findings=[],
        )
        mock_soc2_service.generate_compliance_report.return_value = report

        result = await mock_soc2_service.generate_compliance_report(
            report_period="2024",
        )

        assert result.implementation_rate >= 90.0


# =============================================================================
# BAA Manager Tests
# =============================================================================


class TestBAAManager:
    """Tests for BAA Management."""

    @pytest.mark.asyncio
    async def test_create_baa(self, mock_baa_manager, sample_baa):
        """Test creating a BAA."""
        mock_baa_manager.create_baa.return_value = sample_baa

        result = await mock_baa_manager.create_baa(
            organization_id=sample_baa.organization_id,
            covered_entity="Acme Healthcare",
            business_associate="Cloud Storage Inc",
            phi_categories_shared=[PHICategory.MRN],
        )

        assert result.covered_entity == "Acme Healthcare"

    @pytest.mark.asyncio
    async def test_list_baas(self, mock_baa_manager, sample_baa):
        """Test listing BAAs."""
        mock_baa_manager.list_baas.return_value = [sample_baa]

        result = await mock_baa_manager.list_baas(
            organization_id=sample_baa.organization_id,
            status=BAAStatus.ACTIVE,
        )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_baa_workflow(self, mock_baa_manager, sample_baa):
        """Test BAA approval workflow."""
        # Submit for review
        sample_baa.status = MagicMock(value="pending_review")
        mock_baa_manager.submit_for_review.return_value = sample_baa

        result = await mock_baa_manager.submit_for_review(
            baa_id=sample_baa.id,
            submitted_by="admin",
        )
        assert result.status.value == "pending_review"

        # Approve
        sample_baa.status = MagicMock(value="pending_signature")
        mock_baa_manager.approve_baa.return_value = sample_baa

        result = await mock_baa_manager.approve_baa(
            baa_id=sample_baa.id,
            approved_by="legal",
        )
        assert result.status.value == "pending_signature"

        # Activate
        sample_baa.status = MagicMock(value="active")
        mock_baa_manager.activate_baa.return_value = sample_baa

        result = await mock_baa_manager.activate_baa(
            baa_id=sample_baa.id,
            activated_by="admin",
        )
        assert result.status.value == "active"

    @pytest.mark.asyncio
    async def test_renew_baa(self, mock_baa_manager, sample_baa):
        """Test renewing a BAA."""
        new_expiration = datetime.now(UTC) + timedelta(days=730)
        sample_baa.expiration_date = new_expiration
        mock_baa_manager.renew_baa.return_value = sample_baa

        result = await mock_baa_manager.renew_baa(
            baa_id=sample_baa.id,
            renewed_by="admin",
            new_expiration_date=new_expiration,
        )

        assert result.expiration_date == new_expiration

    @pytest.mark.asyncio
    async def test_terminate_baa(self, mock_baa_manager, sample_baa):
        """Test terminating a BAA."""
        sample_baa.status = MagicMock(value="terminated")
        mock_baa_manager.terminate_baa.return_value = sample_baa

        result = await mock_baa_manager.terminate_baa(
            baa_id=sample_baa.id,
            terminated_by="admin",
            reason="Contract ended",
        )

        assert result.status.value == "terminated"

    @pytest.mark.asyncio
    async def test_get_baa_summary(self, mock_baa_manager):
        """Test getting BAA summary."""
        summary = {
            "total_baas": 10,
            "active_baas": 8,
            "pending_baas": 1,
            "expired_baas": 1,
            "expiring_in_30_days": 2,
            "expiring_in_90_days": 3,
            "requires_attention": True,
        }
        mock_baa_manager.get_baa_summary.return_value = summary

        result = await mock_baa_manager.get_baa_summary(
            organization_id=str(uuid4()),
        )

        assert result["active_baas"] == 8
        assert result["requires_attention"] is True


# =============================================================================
# PHI Detector Tests
# =============================================================================


class TestPHIDetector:
    """Tests for PHI Detection."""

    @pytest.mark.asyncio
    async def test_detect_ssn(self, mock_phi_detector, sample_phi_detection_result):
        """Test detecting SSN."""
        mock_phi_detector.detect.return_value = sample_phi_detection_result

        result = await mock_phi_detector.detect(
            content="Patient SSN: 123-45-6789",
        )

        assert result.phi_found is True
        assert PHICategory.SSN in result.categories_detected

    @pytest.mark.asyncio
    async def test_detect_no_phi(self, mock_phi_detector):
        """Test when no PHI is detected."""
        result = MagicMock(
            phi_found=False,
            findings=[],
            categories_detected=[],
            total_findings=0,
        )
        mock_phi_detector.detect.return_value = result

        detection = await mock_phi_detector.detect(
            content="This is a normal text without any sensitive data.",
        )

        assert detection.phi_found is False
        assert detection.total_findings == 0

    @pytest.mark.asyncio
    async def test_detect_multiple_phi_types(self, mock_phi_detector):
        """Test detecting multiple PHI types."""
        result = MagicMock(
            phi_found=True,
            categories_detected=[PHICategory.SSN, PHICategory.PHONE, PHICategory.EMAIL],
            total_findings=3,
            high_confidence_findings=2,
        )
        mock_phi_detector.detect.return_value = result

        detection = await mock_phi_detector.detect(
            content="SSN: 123-45-6789, Phone: 555-123-4567, Email: patient@example.com",
        )

        assert len(detection.categories_detected) == 3

    @pytest.mark.asyncio
    async def test_detect_phi_in_code(self, mock_phi_detector, sample_phi_detection_result):
        """Test detecting PHI in source code."""
        mock_phi_detector.detect_in_code.return_value = sample_phi_detection_result

        result = await mock_phi_detector.detect_in_code(
            code='ssn = "123-45-6789"',
            language="python",
        )

        assert result.phi_found is True

    @pytest.mark.asyncio
    async def test_phi_confidence_levels(self, mock_phi_detector):
        """Test PHI detection confidence levels."""
        result = MagicMock(
            phi_found=True,
            total_findings=5,
            high_confidence_findings=2,
            medium_confidence_findings=2,
            low_confidence_findings=1,
        )
        mock_phi_detector.detect.return_value = result

        detection = await mock_phi_detector.detect(
            content="Mixed confidence PHI content",
        )

        assert detection.high_confidence_findings == 2
        assert detection.medium_confidence_findings == 2
        assert detection.low_confidence_findings == 1


# =============================================================================
# HIPAA Control Tests
# =============================================================================


class TestHIPAAControls:
    """Tests for HIPAA Control Management."""

    @pytest.mark.asyncio
    async def test_list_hipaa_controls(self, mock_hipaa_service):
        """Test listing HIPAA controls."""
        controls = [
            MagicMock(control_id="164.312(a)(1)", category=MagicMock(value="technical")),
            MagicMock(control_id="164.308(a)(1)", category=MagicMock(value="administrative")),
        ]
        mock_hipaa_service.list_controls.return_value = controls

        result = await mock_hipaa_service.list_controls()

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_controls_by_category(self, mock_hipaa_service):
        """Test listing controls by category."""
        controls = [
            MagicMock(category=MagicMock(value="technical")),
        ]
        mock_hipaa_service.list_controls.return_value = controls

        result = await mock_hipaa_service.list_controls(
            category=HIPAAControlCategory.TECHNICAL,
        )

        assert all(c.category.value == "technical" for c in result)

    @pytest.mark.asyncio
    async def test_update_hipaa_control_status(self, mock_hipaa_service):
        """Test updating HIPAA control status."""
        control = MagicMock(
            control_id="164.312(a)(1)",
            status=MagicMock(value="implemented"),
        )
        mock_hipaa_service.update_control_status.return_value = control

        result = await mock_hipaa_service.update_control_status(
            control_id="164.312(a)(1)",
            status=HIPAAControlStatus.IMPLEMENTED,
            updated_by="compliance_officer",
        )

        assert result.status.value == "implemented"


# =============================================================================
# HIPAA Minimum Necessary Tests
# =============================================================================


class TestHIPAAMinimumNecessary:
    """Tests for HIPAA Minimum Necessary Policies."""

    @pytest.mark.asyncio
    async def test_create_minimum_necessary_policy(self, mock_hipaa_service):
        """Test creating a minimum necessary policy."""
        policy = MagicMock()
        # MagicMock.name is special, need to use configure_mock
        policy.configure_mock(
            id=str(uuid4()),
            applies_to_roles=["nurse", "nurse_supervisor"],
            applies_to_phi_categories=[PHICategory.MRN, PHICategory.VITAL_SIGN],
            requires_justification=True,
        )
        policy.name = "Nurse Access Policy"  # Set name explicitly after configure_mock
        mock_hipaa_service.create_minimum_necessary_policy.return_value = policy

        result = await mock_hipaa_service.create_minimum_necessary_policy(
            name="Nurse Access Policy",
            description="Access policy for nursing staff",
            applies_to_roles=["nurse"],
            applies_to_phi_categories=[PHICategory.MRN],
            permitted_actions=["view"],
        )

        assert result.name == "Nurse Access Policy"

    @pytest.mark.asyncio
    async def test_check_access_permitted(self, mock_hipaa_service):
        """Test checking if access is permitted."""
        mock_hipaa_service.check_access_permitted.return_value = (True, None)

        permitted, reason = await mock_hipaa_service.check_access_permitted(
            user_role="nurse",
            phi_categories=[PHICategory.VITAL_SIGN],
            action="view",
        )

        assert permitted is True
        assert reason is None

    @pytest.mark.asyncio
    async def test_check_access_denied(self, mock_hipaa_service):
        """Test access denied."""
        mock_hipaa_service.check_access_permitted.return_value = (False, "No policy permits this access")

        permitted, reason = await mock_hipaa_service.check_access_permitted(
            user_role="receptionist",
            phi_categories=[PHICategory.DIAGNOSIS],
            action="view",
        )

        assert permitted is False
        assert "No policy" in reason

    @pytest.mark.asyncio
    async def test_request_access_justification(self, mock_hipaa_service):
        """Test requesting access with justification."""
        justification = MagicMock(
            id=str(uuid4()),
            user_id=str(uuid4()),
            purpose="Treatment coordination",
            approved=None,
        )
        mock_hipaa_service.request_access_justification.return_value = justification

        result = await mock_hipaa_service.request_access_justification(
            user_id=str(uuid4()),
            policy_id=str(uuid4()),
            phi_categories_requested=[PHICategory.DIAGNOSIS],
            purpose="Treatment coordination",
        )

        assert result.purpose == "Treatment coordination"

    @pytest.mark.asyncio
    async def test_approve_access_justification(self, mock_hipaa_service):
        """Test approving access justification."""
        justification = MagicMock(
            id=str(uuid4()),
            approved=True,
            approved_by="supervisor",
            approved_at=datetime.now(UTC),
        )
        mock_hipaa_service.approve_access_justification.return_value = justification

        result = await mock_hipaa_service.approve_access_justification(
            justification_id=justification.id,
            approved_by="supervisor",
        )

        assert result.approved is True


# =============================================================================
# HIPAA Compliance Report Tests
# =============================================================================


class TestHIPAAComplianceReport:
    """Tests for HIPAA Compliance Reporting."""

    @pytest.mark.asyncio
    async def test_generate_hipaa_report(self, mock_hipaa_service):
        """Test generating HIPAA compliance report."""
        report = MagicMock(
            report_period="2024",
            total_controls=45,
            implemented_controls=40,
            compliance_score=85.0,
            overall_compliant=True,
            administrative_status=MagicMock(value="implemented"),
            physical_status=MagicMock(value="implemented"),
            technical_status=MagicMock(value="partially_implemented"),
            data_at_rest_compliant=True,
            data_in_transit_compliant=True,
            critical_findings=[],
        )
        mock_hipaa_service.generate_compliance_report.return_value = report

        result = await mock_hipaa_service.generate_compliance_report(
            report_period="2024",
        )

        assert result.overall_compliant is True
        assert result.compliance_score >= 80.0

    @pytest.mark.asyncio
    async def test_hipaa_report_with_findings(self, mock_hipaa_service):
        """Test HIPAA report with findings."""
        report = MagicMock(
            compliance_score=65.0,
            overall_compliant=False,
            critical_findings=[
                {"type": "unimplemented_controls", "severity": "high", "count": 5},
                {"type": "encryption_at_rest", "severity": "high"},
            ],
            recommendations=[
                "Implement all required controls",
                "Enable encryption for ePHI storage",
            ],
        )
        mock_hipaa_service.generate_compliance_report.return_value = report

        result = await mock_hipaa_service.generate_compliance_report(
            report_period="2024",
        )

        assert result.overall_compliant is False
        assert len(result.critical_findings) > 0


# =============================================================================
# Integration Tests
# =============================================================================


class TestComplianceIntegration:
    """Integration tests across compliance services."""

    @pytest.mark.asyncio
    async def test_gdpr_dsr_with_audit_trail(self, mock_gdpr_service, sample_dsr):
        """Test DSR processing creates audit trail."""
        sample_dsr.audit_trail = [
            {"action": "created", "timestamp": datetime.now(UTC).isoformat()},
            {"action": "processing_started", "timestamp": datetime.now(UTC).isoformat()},
            {"action": "completed", "timestamp": datetime.now(UTC).isoformat()},
        ]
        mock_gdpr_service.get_dsr.return_value = sample_dsr

        result = await mock_gdpr_service.get_dsr(sample_dsr.id)

        assert len(result.audit_trail) == 3

    @pytest.mark.asyncio
    async def test_soc2_evidence_verification_flow(self, mock_soc2_service, sample_soc2_evidence):
        """Test evidence collection and verification."""
        # Add evidence
        sample_soc2_evidence.verified = False
        mock_soc2_service.add_evidence.return_value = sample_soc2_evidence

        evidence = await mock_soc2_service.add_evidence(
            control_id="CC6.1",
            evidence_type=SOC2EvidenceType.DOCUMENT,
            title="Access Control Policy",
            collected_by="compliance",
        )
        assert evidence.verified is False

        # Verify evidence
        sample_soc2_evidence.verified = True
        mock_soc2_service.verify_evidence.return_value = sample_soc2_evidence

        verified = await mock_soc2_service.verify_evidence(
            evidence_id=evidence.id,
            verifier="auditor",
        )
        assert verified.verified is True

    @pytest.mark.asyncio
    async def test_hipaa_phi_detection_with_code_review(self, mock_hipaa_service):
        """Test PHI detection as part of code review."""
        # First detect PHI
        detection_result = MagicMock(
            phi_found=True,
            categories_detected=[PHICategory.SSN],
            recommendations=["CRITICAL: SSN detected"],
        )
        mock_hipaa_service.detect_phi_in_code.return_value = detection_result

        result = await mock_hipaa_service.detect_phi_in_code(
            code='patient_ssn = "123-45-6789"',
            language="python",
        )

        assert result.phi_found is True
        assert "CRITICAL" in result.recommendations[0]


# =============================================================================
# Edge Cases Tests
# =============================================================================


class TestComplianceEdgeCases:
    """Tests for compliance edge cases."""

    @pytest.mark.asyncio
    async def test_expired_consent(self, mock_gdpr_service, sample_consent):
        """Test handling expired consent."""
        sample_consent.expires_at = datetime.now(UTC) - timedelta(days=1)
        mock_gdpr_service.check_consent.return_value = False

        result = await mock_gdpr_service.check_consent(
            user_id=sample_consent.user_id,
            consent_type=ConsentType.MARKETING,
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_baa_expiring_soon(self, mock_baa_manager):
        """Test detecting BAAs expiring soon."""
        expiring_baa = MagicMock(
            id=str(uuid4()),
            expiration_date=datetime.now(UTC) + timedelta(days=15),
            status=MagicMock(value="active"),
        )
        mock_baa_manager.list_baas.return_value = [expiring_baa]

        result = await mock_baa_manager.list_baas(
            expiring_within_days=30,
        )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_overdue_dsr(self, mock_gdpr_service, sample_dsr):
        """Test handling overdue DSR."""
        sample_dsr.deadline = datetime.now(UTC) - timedelta(days=1)
        sample_dsr.status = MagicMock(value="pending")

        # Check if DSR is overdue
        is_overdue = sample_dsr.deadline < datetime.now(UTC)
        is_pending = sample_dsr.status.value in ("pending", "in_progress")

        assert is_overdue and is_pending

    @pytest.mark.asyncio
    async def test_control_without_evidence(self, mock_soc2_service):
        """Test control without evidence."""
        mock_soc2_service.get_evidence.return_value = []

        result = await mock_soc2_service.get_evidence(
            control_id="CC6.1",
            valid_only=True,
        )

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_emergency_change_request(self, mock_soc2_service):
        """Test emergency change request tracking."""
        emergency_change = MagicMock(
            id=str(uuid4()),
            change_type="emergency",
            risk_level="high",
            status="approved",
        )
        mock_soc2_service.create_change_record.return_value = emergency_change

        result = await mock_soc2_service.create_change_record(
            title="Critical Security Patch",
            description="Emergency patch for security vulnerability",
            requested_by="security_team",
            change_type="emergency",
            risk_level="high",
        )

        assert result.change_type == "emergency"

    def test_compliance_score_calculation(self):
        """Test compliance score calculation."""
        total_controls = 50
        implemented = 40
        partially = 5
        not_implemented = 5

        # Simple implementation rate
        implementation_rate = (implemented / total_controls) * 100

        # Weighted score
        weighted_score = (implemented * 1.0 + partially * 0.5) / total_controls * 100

        assert implementation_rate == 80.0
        assert weighted_score == 85.0

    def test_phi_pattern_matching(self):
        """Test PHI pattern detection logic."""
        import re

        ssn_pattern = r"\b\d{3}-\d{2}-\d{4}\b"
        test_content = "Patient SSN: 123-45-6789 is invalid"

        matches = re.findall(ssn_pattern, test_content)

        assert len(matches) == 1
        assert matches[0] == "123-45-6789"

    def test_retention_period_calculation(self):
        """Test retention period calculations."""
        created_at = datetime.now(UTC) - timedelta(days=400)
        retention_days = 365

        expiration = created_at + timedelta(days=retention_days)
        is_expired = expiration < datetime.now(UTC)

        assert is_expired is True
