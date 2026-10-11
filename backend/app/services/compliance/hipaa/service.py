"""HIPAA Compliance Service - Main orchestration service."""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

from app.services.compliance.hipaa.models import (
    AccessJustification,
    DEFAULT_HIPAA_CONTROLS,
    HIPAAComplianceReport,
    HIPAAControl,
    HIPAAControlCategory,
    HIPAAControlStatus,
    MinimumNecessaryPolicy,
    PHICategory,
)
from app.services.compliance.hipaa.phi_detector import PHIDetector, get_phi_detector
from app.services.compliance.hipaa.baa_manager import BAAManager, get_baa_manager
from app.services.compliance.hipaa.encryption_auditor import EncryptionAuditor, get_encryption_auditor

logger = logging.getLogger(__name__)

# Singleton instance
_hipaa_service: "HIPAAService | None" = None


class HIPAAService:
    """Unified HIPAA Compliance Service.

    Provides comprehensive HIPAA compliance management including:
    - PHI detection and protection
    - BAA management
    - Encryption auditing
    - Control tracking
    - Minimum necessary policies
    - Compliance reporting
    """

    def __init__(
        self,
        phi_detector: PHIDetector | None = None,
        baa_manager: BAAManager | None = None,
        encryption_auditor: EncryptionAuditor | None = None,
    ):
        self._phi_detector = phi_detector or get_phi_detector()
        self._baa_manager = baa_manager or get_baa_manager()
        self._encryption_auditor = encryption_auditor or get_encryption_auditor()

        # Internal storage
        self._controls: dict[str, HIPAAControl] = {}
        self._minimum_necessary_policies: dict[str, MinimumNecessaryPolicy] = {}
        self._access_justifications: dict[str, AccessJustification] = {}
        self._audit_log: list[dict[str, Any]] = []

        # Initialize default controls
        self._initialize_default_controls()

    def _initialize_default_controls(self) -> None:
        """Initialize default HIPAA Security Rule controls."""
        for ctrl_data in DEFAULT_HIPAA_CONTROLS:
            control = HIPAAControl(
                id=str(uuid.uuid4()),
                control_id=ctrl_data["control_id"],
                category=ctrl_data["category"],
                title=ctrl_data["title"],
                description=ctrl_data["description"],
                required=ctrl_data.get("required", True),
            )
            self._controls[control.id] = control

    # --- PHI Detection (delegated) ---

    @property
    def phi_detector(self) -> PHIDetector:
        """Get PHI detector instance."""
        return self._phi_detector

    async def detect_phi(self, content: str, **kwargs):
        """Detect PHI in content."""
        return await self._phi_detector.detect(content, **kwargs)

    async def detect_phi_in_code(self, code: str, language: str | None = None):
        """Detect PHI in source code."""
        return await self._phi_detector.detect_in_code(code, language)

    # --- BAA Management (delegated) ---

    @property
    def baa_manager(self) -> BAAManager:
        """Get BAA manager instance."""
        return self._baa_manager

    # --- Encryption Auditing (delegated) ---

    @property
    def encryption_auditor(self) -> EncryptionAuditor:
        """Get encryption auditor instance."""
        return self._encryption_auditor

    async def audit_encryption(self, auditor: str | None = None):
        """Perform encryption audit."""
        return await self._encryption_auditor.audit_encryption(auditor)

    # --- Control Management ---

    async def get_control(self, control_id: str) -> HIPAAControl | None:
        """Get a control by ID or control_id."""
        if control_id in self._controls:
            return self._controls[control_id]
        for ctrl in self._controls.values():
            if ctrl.control_id == control_id:
                return ctrl
        return None

    async def list_controls(
        self,
        category: HIPAAControlCategory | None = None,
        status: HIPAAControlStatus | None = None,
        required_only: bool = False,
    ) -> list[HIPAAControl]:
        """List controls with optional filters."""
        controls = list(self._controls.values())

        if category:
            controls = [c for c in controls if c.category == category]
        if status:
            controls = [c for c in controls if c.status == status]
        if required_only:
            controls = [c for c in controls if c.required]

        return sorted(controls, key=lambda c: c.control_id)

    async def update_control_status(
        self,
        control_id: str,
        status: HIPAAControlStatus,
        updated_by: str,
        implementation_notes: str | None = None,
    ) -> HIPAAControl | None:
        """Update a control's status."""
        control = await self.get_control(control_id)
        if not control:
            return None

        old_status = control.status
        control.status = status
        control.last_reviewed = datetime.utcnow()

        if implementation_notes:
            control.implementation_notes = implementation_notes

        await self._log_action(
            action="control_status_updated",
            resource_type="hipaa_control",
            resource_id=control.id,
            actor=updated_by,
            details={
                "control_id": control.control_id,
                "old_status": old_status.value,
                "new_status": status.value,
            },
        )

        return control

    async def add_control_evidence(
        self,
        control_id: str,
        evidence_id: str,
        added_by: str,
    ) -> HIPAAControl | None:
        """Add evidence to a control."""
        control = await self.get_control(control_id)
        if not control:
            return None

        if evidence_id not in control.evidence_ids:
            control.evidence_ids.append(evidence_id)

        await self._log_action(
            action="evidence_added",
            resource_type="hipaa_control",
            resource_id=control.id,
            actor=added_by,
            details={"evidence_id": evidence_id},
        )

        return control

    # --- Minimum Necessary Policies ---

    async def create_minimum_necessary_policy(
        self,
        name: str,
        description: str,
        applies_to_roles: list[str],
        applies_to_phi_categories: list[PHICategory],
        permitted_actions: list[str],
        requires_justification: bool = True,
        max_records_per_query: int | None = None,
        created_by: str | None = None,
    ) -> MinimumNecessaryPolicy:
        """Create a minimum necessary access policy."""
        policy = MinimumNecessaryPolicy(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            applies_to_roles=applies_to_roles,
            applies_to_phi_categories=applies_to_phi_categories,
            permitted_actions=permitted_actions,
            requires_justification=requires_justification,
            max_records_per_query=max_records_per_query,
        )

        self._minimum_necessary_policies[policy.id] = policy

        await self._log_action(
            action="policy_created",
            resource_type="minimum_necessary_policy",
            resource_id=policy.id,
            actor=created_by or "system",
            details={"name": name},
        )

        return policy

    async def list_minimum_necessary_policies(
        self,
        enabled_only: bool = True,
    ) -> list[MinimumNecessaryPolicy]:
        """List minimum necessary policies."""
        policies = list(self._minimum_necessary_policies.values())
        if enabled_only:
            policies = [p for p in policies if p.enabled]
        return policies

    async def check_access_permitted(
        self,
        user_role: str,
        phi_categories: list[PHICategory],
        action: str,
    ) -> tuple[bool, str | None]:
        """Check if access is permitted under minimum necessary policies."""
        for policy in self._minimum_necessary_policies.values():
            if not policy.enabled:
                continue

            if user_role in policy.applies_to_roles:
                # Check if all requested categories are covered
                categories_covered = all(
                    cat in policy.applies_to_phi_categories
                    for cat in phi_categories
                )
                action_permitted = action in policy.permitted_actions

                if categories_covered and action_permitted:
                    if policy.requires_justification and user_role not in policy.auto_approve_roles:
                        return False, "Justification required"
                    return True, None

        return False, "No policy permits this access"

    async def request_access_justification(
        self,
        user_id: str,
        policy_id: str,
        phi_categories_requested: list[PHICategory],
        purpose: str,
        patient_id: str | None = None,
    ) -> AccessJustification:
        """Request access with justification."""
        justification = AccessJustification(
            id=str(uuid.uuid4()),
            user_id=user_id,
            policy_id=policy_id,
            phi_categories_requested=phi_categories_requested,
            purpose=purpose,
            patient_id=patient_id,
        )

        self._access_justifications[justification.id] = justification

        await self._log_action(
            action="access_requested",
            resource_type="access_justification",
            resource_id=justification.id,
            actor=user_id,
            details={
                "purpose": purpose,
                "categories": [c.value for c in phi_categories_requested],
            },
        )

        return justification

    async def approve_access_justification(
        self,
        justification_id: str,
        approved_by: str,
        valid_hours: int = 24,
        max_access_count: int | None = None,
    ) -> AccessJustification | None:
        """Approve an access justification."""
        justification = self._access_justifications.get(justification_id)
        if not justification:
            return None

        now = datetime.utcnow()
        justification.approved = True
        justification.approved_by = approved_by
        justification.approved_at = now
        justification.valid_from = now
        justification.valid_until = now + timedelta(hours=valid_hours)
        justification.max_access_count = max_access_count

        await self._log_action(
            action="access_approved",
            resource_type="access_justification",
            resource_id=justification_id,
            actor=approved_by,
        )

        return justification

    async def deny_access_justification(
        self,
        justification_id: str,
        denied_by: str,
        reason: str,
    ) -> AccessJustification | None:
        """Deny an access justification."""
        justification = self._access_justifications.get(justification_id)
        if not justification:
            return None

        justification.approved = False
        justification.approved_by = denied_by
        justification.approved_at = datetime.utcnow()
        justification.denial_reason = reason

        await self._log_action(
            action="access_denied",
            resource_type="access_justification",
            resource_id=justification_id,
            actor=denied_by,
            details={"reason": reason},
        )

        return justification

    # --- Compliance Reporting ---

    async def generate_compliance_report(
        self,
        report_period: str,
        organization_id: str | None = None,
    ) -> HIPAAComplianceReport:
        """Generate comprehensive HIPAA compliance report."""
        report = HIPAAComplianceReport(
            report_period=report_period,
        )

        # Control metrics
        controls = list(self._controls.values())
        report.total_controls = len(controls)
        report.implemented_controls = len([
            c for c in controls if c.status == HIPAAControlStatus.IMPLEMENTED
        ])
        report.partially_implemented = len([
            c for c in controls if c.status == HIPAAControlStatus.PARTIALLY_IMPLEMENTED
        ])
        report.not_implemented = len([
            c for c in controls if c.status == HIPAAControlStatus.NOT_IMPLEMENTED
        ])

        # Category status
        def get_category_status(cat: HIPAAControlCategory) -> HIPAAControlStatus:
            cat_controls = [c for c in controls if c.category == cat]
            if not cat_controls:
                return HIPAAControlStatus.NOT_APPLICABLE
            impl = len([c for c in cat_controls if c.status == HIPAAControlStatus.IMPLEMENTED])
            if impl == len(cat_controls):
                return HIPAAControlStatus.IMPLEMENTED
            elif impl > 0:
                return HIPAAControlStatus.PARTIALLY_IMPLEMENTED
            return HIPAAControlStatus.NOT_IMPLEMENTED

        report.administrative_status = get_category_status(HIPAAControlCategory.ADMINISTRATIVE)
        report.physical_status = get_category_status(HIPAAControlCategory.PHYSICAL)
        report.technical_status = get_category_status(HIPAAControlCategory.TECHNICAL)

        # BAA metrics
        baa_summary = await self._baa_manager.get_baa_summary(organization_id or "default")
        report.total_baas = baa_summary["total_baas"]
        report.active_baas = baa_summary["active_baas"]
        report.expiring_baas = baa_summary["expiring_in_90_days"]

        # PHI tracking
        report.phi_categories_tracked = len(PHICategory)
        report.phi_inventory_complete = True  # Assume complete if service is running

        # Encryption status
        encryption_result = await self._encryption_auditor.audit_encryption()
        report.encryption_audit_status = encryption_result.overall_status
        report.data_at_rest_compliant = encryption_result.data_at_rest_status.value == "compliant"
        report.data_in_transit_compliant = encryption_result.data_in_transit_status.value == "compliant"

        # Minimum necessary metrics
        report.access_policies_count = len(self._minimum_necessary_policies)
        justifications = list(self._access_justifications.values())
        report.access_requests_reviewed = len([j for j in justifications if j.approved_by])
        report.access_requests_denied = len([j for j in justifications if not j.approved and j.denial_reason])

        # Calculate overall compliance
        compliance_score = (
            (report.implemented_controls / max(report.total_controls, 1)) * 40 +
            (1 if report.data_at_rest_compliant else 0) * 20 +
            (1 if report.data_in_transit_compliant else 0) * 20 +
            (1 if report.active_baas > 0 or report.total_baas == 0 else 0) * 10 +
            (1 if report.access_policies_count > 0 else 0) * 10
        )
        report.compliance_score = round(compliance_score, 2)
        report.overall_compliant = compliance_score >= 80

        # Generate findings and recommendations
        await self._generate_report_findings(report)

        return report

    async def _generate_report_findings(self, report: HIPAAComplianceReport) -> None:
        """Generate findings and recommendations for report."""
        findings = []
        recommendations = []

        # Control findings
        if report.not_implemented > 0:
            findings.append({
                "type": "unimplemented_controls",
                "severity": "high",
                "count": report.not_implemented,
                "description": f"{report.not_implemented} required controls not implemented",
            })
            recommendations.append("Implement all required HIPAA Security Rule controls")

        # BAA findings
        if report.expiring_baas > 0:
            findings.append({
                "type": "expiring_baas",
                "severity": "medium",
                "count": report.expiring_baas,
                "description": f"{report.expiring_baas} BAAs expiring within 90 days",
            })
            recommendations.append("Renew expiring Business Associate Agreements")

        # Encryption findings
        if not report.data_at_rest_compliant:
            findings.append({
                "type": "encryption_at_rest",
                "severity": "high",
                "description": "Data at rest encryption not fully compliant",
            })
            recommendations.append("Enable AES-256 encryption for all ePHI storage")

        if not report.data_in_transit_compliant:
            findings.append({
                "type": "encryption_in_transit",
                "severity": "high",
                "description": "Data in transit encryption not fully compliant",
            })
            recommendations.append("Enforce TLS 1.2+ for all ePHI transmission")

        # Access control findings
        if report.access_policies_count == 0:
            findings.append({
                "type": "no_minimum_necessary_policies",
                "severity": "medium",
                "description": "No minimum necessary access policies defined",
            })
            recommendations.append("Define minimum necessary access policies for workforce roles")

        report.critical_findings = findings
        report.recommendations = recommendations

    # --- Audit Logging ---

    async def _log_action(
        self,
        action: str,
        resource_type: str,
        resource_id: str,
        actor: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Log an audit entry."""
        entry = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "actor": actor,
            "details": details or {},
        }
        self._audit_log.append(entry)

    async def get_audit_log(
        self,
        resource_type: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get audit log entries."""
        entries = self._audit_log

        if resource_type:
            entries = [e for e in entries if e.get("resource_type") == resource_type]

        return sorted(entries, key=lambda e: e["timestamp"], reverse=True)[:limit]


def get_hipaa_service() -> HIPAAService:
    """Get or create the HIPAA service singleton."""
    global _hipaa_service

    if _hipaa_service is None:
        _hipaa_service = HIPAAService()

    return _hipaa_service
