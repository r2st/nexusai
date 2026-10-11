"""
GB068: End-to-end data flow fidelity tests for compliance scores.

Traces user-facing outputs (compliance_score, implementation_rate,
consent_rate, avg_dsr_completion_days) backwards through every
transformation to verify no mutation, fabrication, staleness,
or rounding error accumulates.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# HIPAA compliance_score fidelity
# ---------------------------------------------------------------------------


class TestHIPAAComplianceScoreFidelity:
    """Verify HIPAA compliance_score is computed correctly from source data."""

    @pytest.fixture
    def hipaa_service(self):
        from app.services.compliance.hipaa.service import HIPAAService
        from app.services.compliance.hipaa.baa_manager import BAAManager
        from app.services.compliance.hipaa.encryption_auditor import EncryptionAuditor

        baa = BAAManager()
        enc = EncryptionAuditor()
        svc = HIPAAService(baa_manager=baa, encryption_auditor=enc)
        return svc

    @pytest.mark.asyncio
    async def test_score_zero_when_nothing_implemented(self, hipaa_service):
        """All controls NOT_IMPLEMENTED, no encryption audited, no BAAs, no policies => 10.

        Only 10 points come from the BAA term (total_baas == 0 means no
        BAAs are required, which counts as compliant).
        """
        report = await hipaa_service.generate_compliance_report("Q1 2024")
        assert report.compliance_score == 10.0
        assert report.overall_compliant is False
        assert report.implemented_controls == 0
        assert report.data_at_rest_compliant is False
        assert report.data_in_transit_compliant is False

    @pytest.mark.asyncio
    async def test_score_components_are_additive(self, hipaa_service):
        """Each component contributes independently to the score."""
        from app.services.compliance.hipaa.models import HIPAAControlStatus

        # Implement all controls => 40 points
        for ctrl in hipaa_service._controls.values():
            ctrl.status = HIPAAControlStatus.IMPLEMENTED

        report = await hipaa_service.generate_compliance_report("Q1 2024")
        # 40 (controls) + 0 (rest enc not audited) + 0 (transit enc not audited) + 10 (no BAAs needed) + 0 (no policies)
        assert report.compliance_score == 50.0

    @pytest.mark.asyncio
    async def test_score_with_policy_adds_10(self, hipaa_service):
        """Adding a minimum necessary policy adds 10 points."""
        from app.services.compliance.hipaa.models import PHICategory

        await hipaa_service.create_minimum_necessary_policy(
            name="Test Policy",
            description="Test",
            applies_to_roles=["nurse"],
            applies_to_phi_categories=[PHICategory.MRN],
            permitted_actions=["read"],
        )

        report = await hipaa_service.generate_compliance_report("Q1 2024")
        # 0 (controls) + 0 (enc not audited) + 0 (enc not audited) + 10 (no BAAs needed) + 10 (has policy)
        assert report.compliance_score == 20.0

    @pytest.mark.asyncio
    async def test_score_is_rounded_to_2_decimals(self, hipaa_service):
        """Score with fractional control ratio is rounded to 2 decimal places."""
        from app.services.compliance.hipaa.models import HIPAAControlStatus

        # Implement exactly 1 out of N controls
        controls = list(hipaa_service._controls.values())
        controls[0].status = HIPAAControlStatus.IMPLEMENTED
        total = len(controls)

        report = await hipaa_service.generate_compliance_report("Q1 2024")
        # Control component + 10 (no BAAs needed)
        raw = (1 / total) * 40 + 10
        assert report.compliance_score == round(raw, 2)
        # Verify it's actually rounded (not a long float)
        score_str = str(report.compliance_score)
        if "." in score_str:
            assert len(score_str.split(".")[1]) <= 2

    @pytest.mark.asyncio
    async def test_score_max_is_100(self, hipaa_service):
        """Full compliance yields score of 100."""
        from app.services.compliance.hipaa.models import HIPAAControlStatus, PHICategory

        for ctrl in hipaa_service._controls.values():
            ctrl.status = HIPAAControlStatus.IMPLEMENTED

        # Register compliant encryption with approved algorithm names
        enc = hipaa_service._encryption_auditor
        await enc.register_storage_location("db", "postgresql", "aes-256-gcm", True)
        await enc.register_endpoint("api", "https", "1.3", "aes-256-gcm")

        # Add a policy
        await hipaa_service.create_minimum_necessary_policy(
            name="Full",
            description="Full access",
            applies_to_roles=["admin"],
            applies_to_phi_categories=[PHICategory.MRN],
            permitted_actions=["read"],
        )

        report = await hipaa_service.generate_compliance_report("Q1 2024")
        assert report.compliance_score == 100.0
        assert report.overall_compliant is True

    @pytest.mark.asyncio
    async def test_overall_compliant_threshold_is_80(self, hipaa_service):
        """overall_compliant is True iff score >= 80."""
        from app.services.compliance.hipaa.models import HIPAAControlStatus, PHICategory

        for ctrl in hipaa_service._controls.values():
            ctrl.status = HIPAAControlStatus.IMPLEMENTED

        # Add policy for 10 more points
        await hipaa_service.create_minimum_necessary_policy(
            name="P",
            description="D",
            applies_to_roles=["r"],
            applies_to_phi_categories=[PHICategory.MRN],
            permitted_actions=["read"],
        )

        report = await hipaa_service.generate_compliance_report("Q1 2024")
        # 40 (controls) + 0 + 0 (enc not audited) + 10 (no BAAs) + 10 (policy) = 60
        assert report.compliance_score == 60.0
        assert report.overall_compliant is False

    @pytest.mark.asyncio
    async def test_unaudited_encryption_does_not_inflate_score(self, hipaa_service):
        """Encryption not audited should NOT report as compliant."""
        from app.services.compliance.hipaa.models import EncryptionStatus

        report = await hipaa_service.generate_compliance_report("Q1 2024")
        assert report.data_at_rest_compliant is False
        assert report.data_in_transit_compliant is False
        assert report.encryption_audit_status != EncryptionStatus.COMPLIANT


# ---------------------------------------------------------------------------
# HIPAA valid_until bug fix verification
# ---------------------------------------------------------------------------


class TestHIPAAAccessJustificationValidUntil:
    """Verify valid_until is correctly calculated using timedelta."""

    @pytest.fixture
    def hipaa_service(self):
        from app.services.compliance.hipaa.service import HIPAAService
        return HIPAAService()

    @pytest.mark.asyncio
    async def test_valid_until_with_24_hours(self, hipaa_service):
        """24-hour window should not crash and should be ~24 hours ahead."""
        from app.services.compliance.hipaa.models import PHICategory

        policy = await hipaa_service.create_minimum_necessary_policy(
            name="Test",
            description="Test",
            applies_to_roles=["nurse"],
            applies_to_phi_categories=[PHICategory.MRN],
            permitted_actions=["read"],
        )

        justification = await hipaa_service.request_access_justification(
            user_id="user1",
            policy_id=policy.id,
            phi_categories_requested=[PHICategory.MRN],
            purpose="Treatment",
        )

        result = await hipaa_service.approve_access_justification(
            justification_id=justification.id,
            approved_by="supervisor",
            valid_hours=24,
        )

        assert result is not None
        delta = result.valid_until - result.valid_from
        assert 23 <= delta.total_seconds() / 3600 <= 25

    @pytest.mark.asyncio
    async def test_valid_until_with_48_hours_no_crash(self, hipaa_service):
        """48-hour window previously crashed with ValueError (hour > 23)."""
        from app.services.compliance.hipaa.models import PHICategory

        policy = await hipaa_service.create_minimum_necessary_policy(
            name="Test",
            description="Test",
            applies_to_roles=["nurse"],
            applies_to_phi_categories=[PHICategory.MRN],
            permitted_actions=["read"],
        )

        justification = await hipaa_service.request_access_justification(
            user_id="user1",
            policy_id=policy.id,
            phi_categories_requested=[PHICategory.MRN],
            purpose="Treatment",
        )

        result = await hipaa_service.approve_access_justification(
            justification_id=justification.id,
            approved_by="supervisor",
            valid_hours=48,
        )

        assert result is not None
        delta = result.valid_until - result.valid_from
        assert 47 <= delta.total_seconds() / 3600 <= 49

    @pytest.mark.asyncio
    async def test_valid_until_with_168_hours(self, hipaa_service):
        """One week (168 hours) should work correctly."""
        from app.services.compliance.hipaa.models import PHICategory

        policy = await hipaa_service.create_minimum_necessary_policy(
            name="Test",
            description="Test",
            applies_to_roles=["nurse"],
            applies_to_phi_categories=[PHICategory.MRN],
            permitted_actions=["read"],
        )

        justification = await hipaa_service.request_access_justification(
            user_id="user1",
            policy_id=policy.id,
            phi_categories_requested=[PHICategory.MRN],
            purpose="Treatment",
        )

        result = await hipaa_service.approve_access_justification(
            justification_id=justification.id,
            approved_by="supervisor",
            valid_hours=168,
        )

        assert result is not None
        delta = result.valid_until - result.valid_from
        assert 167 <= delta.total_seconds() / 3600 <= 169


# ---------------------------------------------------------------------------
# SOC2 implementation_rate fidelity
# ---------------------------------------------------------------------------


class TestSOC2ImplementationRateFidelity:
    """Verify SOC2 implementation_rate accounts for partial controls."""

    @pytest.fixture
    def soc2_service(self):
        from app.services.compliance.soc2 import SOC2Service
        return SOC2Service(initialize_defaults=False)

    def _add_controls(self, service, statuses):
        """Helper to add controls with given statuses."""
        import uuid
        from app.services.compliance.models import SOC2Control, SOC2ControlCategory
        for i, status in enumerate(statuses):
            ctrl = SOC2Control(
                id=str(uuid.uuid4()),
                control_id=f"TEST.{i}",
                category=SOC2ControlCategory.SECURITY,
                title=f"Test Control {i}",
                description=f"Test {i}",
                status=status,
            )
            service._controls[ctrl.id] = ctrl

    @pytest.mark.asyncio
    async def test_all_implemented_yields_100(self, soc2_service):
        from app.services.compliance.models import SOC2ControlStatus
        self._add_controls(soc2_service, [SOC2ControlStatus.IMPLEMENTED] * 10)
        report = await soc2_service.generate_compliance_report("Q1")
        assert report.implementation_rate == 100.0

    @pytest.mark.asyncio
    async def test_all_not_implemented_yields_0(self, soc2_service):
        from app.services.compliance.models import SOC2ControlStatus
        self._add_controls(soc2_service, [SOC2ControlStatus.NOT_IMPLEMENTED] * 10)
        report = await soc2_service.generate_compliance_report("Q1")
        assert report.implementation_rate == 0.0

    @pytest.mark.asyncio
    async def test_partial_controls_contribute_half(self, soc2_service):
        """10 controls: 5 implemented + 5 partially => (5 + 2.5)/10 * 100 = 75%."""
        from app.services.compliance.models import SOC2ControlStatus
        statuses = (
            [SOC2ControlStatus.IMPLEMENTED] * 5
            + [SOC2ControlStatus.PARTIALLY_IMPLEMENTED] * 5
        )
        self._add_controls(soc2_service, statuses)
        report = await soc2_service.generate_compliance_report("Q1")
        assert report.implementation_rate == 75.0

    @pytest.mark.asyncio
    async def test_mixed_statuses(self, soc2_service):
        """4 impl + 2 partial + 4 not_impl => (4 + 1)/10 * 100 = 50%."""
        from app.services.compliance.models import SOC2ControlStatus
        statuses = (
            [SOC2ControlStatus.IMPLEMENTED] * 4
            + [SOC2ControlStatus.PARTIALLY_IMPLEMENTED] * 2
            + [SOC2ControlStatus.NOT_IMPLEMENTED] * 4
        )
        self._add_controls(soc2_service, statuses)
        report = await soc2_service.generate_compliance_report("Q1")
        assert report.implementation_rate == 50.0

    @pytest.mark.asyncio
    async def test_no_controls_yields_0(self, soc2_service):
        """Empty control set should yield 0 without ZeroDivisionError."""
        report = await soc2_service.generate_compliance_report("Q1")
        assert report.implementation_rate == 0.0

    @pytest.mark.asyncio
    async def test_rate_is_rounded(self, soc2_service):
        """3 controls: 1 impl + 1 partial => (1 + 0.5)/3 * 100 = 50.0."""
        from app.services.compliance.models import SOC2ControlStatus
        statuses = [
            SOC2ControlStatus.IMPLEMENTED,
            SOC2ControlStatus.PARTIALLY_IMPLEMENTED,
            SOC2ControlStatus.NOT_IMPLEMENTED,
        ]
        self._add_controls(soc2_service, statuses)
        report = await soc2_service.generate_compliance_report("Q1")
        assert report.implementation_rate == 50.0

    @pytest.mark.asyncio
    async def test_compliance_status_thresholds(self, soc2_service):
        """Status is COMPLIANT at 95%+, PARTIAL at 70-95%, NON_COMPLIANT below."""
        from app.services.compliance.models import SOC2ControlStatus, ComplianceStatus

        # 96% => COMPLIANT (need 20 controls: 19 impl + 1 partial = (19+0.5)/20 = 97.5%)
        self._add_controls(soc2_service, [SOC2ControlStatus.IMPLEMENTED] * 19 + [SOC2ControlStatus.PARTIALLY_IMPLEMENTED])
        report = await soc2_service.generate_compliance_report("Q1")
        assert report.status == ComplianceStatus.COMPLIANT
        assert report.implementation_rate == 97.5


# ---------------------------------------------------------------------------
# GDPR consent_rate and avg_dsr_completion_days fidelity
# ---------------------------------------------------------------------------


class TestGDPRReportFidelity:
    """Verify GDPR report fields are computed from actual source data."""

    @pytest.fixture
    def gdpr_service(self):
        from app.services.compliance.gdpr import GDPRService
        return GDPRService()

    @pytest.mark.asyncio
    async def test_consent_rate_no_users(self, gdpr_service):
        """No users => consent_rate is 0, no crash."""
        report = await gdpr_service.generate_compliance_report()
        assert report.consent_rate == 0.0
        assert report.total_users == 0

    @pytest.mark.asyncio
    async def test_consent_rate_computation(self, gdpr_service):
        from app.services.compliance.models import ConsentType

        # User A grants marketing consent
        await gdpr_service.record_consent(
            user_id="A", consent_type=ConsentType.MARKETING,
            granted=True, purpose="marketing",
        )
        # User B denies consent
        await gdpr_service.record_consent(
            user_id="B", consent_type=ConsentType.MARKETING,
            granted=False, purpose="marketing",
        )

        report = await gdpr_service.generate_compliance_report()
        assert report.total_users == 2
        assert report.users_with_consent == 1
        assert report.consent_rate == 50.0

    @pytest.mark.asyncio
    async def test_avg_dsr_completion_days(self, gdpr_service):
        from app.services.compliance.models import DataSubjectRequestType

        dsr = await gdpr_service.create_dsr(
            user_id="U1", email="u@e.com",
            request_type=DataSubjectRequestType.ACCESS,
        )
        # Manually set created_at to 10 days ago
        dsr.created_at = datetime.utcnow() - timedelta(days=10)
        await gdpr_service.complete_dsr(
            dsr_id=dsr.id, processor_id="processor1",
        )

        report = await gdpr_service.generate_compliance_report()
        assert report.completed_dsr_requests == 1
        assert 9 <= report.avg_dsr_completion_days <= 11

    @pytest.mark.asyncio
    async def test_avg_dsr_completion_no_completed(self, gdpr_service):
        """No completed DSRs => avg is 0."""
        from app.services.compliance.models import DataSubjectRequestType

        await gdpr_service.create_dsr(
            user_id="U1", email="u@e.com",
            request_type=DataSubjectRequestType.ACCESS,
        )

        report = await gdpr_service.generate_compliance_report()
        assert report.avg_dsr_completion_days == 0.0

    @pytest.mark.asyncio
    async def test_overdue_dsr_marks_non_compliant(self, gdpr_service):
        from app.services.compliance.models import (
            DataSubjectRequestType, ComplianceStatus,
        )

        dsr = await gdpr_service.create_dsr(
            user_id="U1", email="u@e.com",
            request_type=DataSubjectRequestType.ACCESS,
        )
        # Make it overdue
        dsr.deadline = datetime.utcnow() - timedelta(days=1)

        report = await gdpr_service.generate_compliance_report()
        assert report.status == ComplianceStatus.NON_COMPLIANT
        assert report.overdue_dsr_requests == 1


# ---------------------------------------------------------------------------
# Compliance dashboard endpoint fidelity
# ---------------------------------------------------------------------------


class TestComplianceDashboardEndpoint:
    """Verify the /compliance/dashboard aggregation is faithful."""

    @pytest.mark.asyncio
    async def test_dashboard_overall_status_non_compliant_propagates(self):
        from app.api.compliance import _calculate_overall_status
        from app.services.compliance.models import ComplianceStatus

        result = _calculate_overall_status(
            ComplianceStatus.NON_COMPLIANT,
            ComplianceStatus.COMPLIANT,
        )
        assert result == "non_compliant"

    @pytest.mark.asyncio
    async def test_dashboard_overall_status_partial(self):
        from app.api.compliance import _calculate_overall_status
        from app.services.compliance.models import ComplianceStatus

        result = _calculate_overall_status(
            ComplianceStatus.PARTIAL,
            ComplianceStatus.COMPLIANT,
        )
        assert result == "partial"

    @pytest.mark.asyncio
    async def test_dashboard_overall_status_compliant(self):
        from app.api.compliance import _calculate_overall_status
        from app.services.compliance.models import ComplianceStatus

        result = _calculate_overall_status(
            ComplianceStatus.COMPLIANT,
            ComplianceStatus.COMPLIANT,
        )
        assert result == "compliant"

    @pytest.mark.asyncio
    async def test_dashboard_overall_status_pending(self):
        from app.api.compliance import _calculate_overall_status
        from app.services.compliance.models import ComplianceStatus

        result = _calculate_overall_status(
            ComplianceStatus.COMPLIANT,
            ComplianceStatus.PENDING_REVIEW,
        )
        assert result == "pending_review"
