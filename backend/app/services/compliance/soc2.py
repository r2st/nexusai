"""SOC 2 Compliance Service."""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

from app.services.compliance.models import (
    AccessReviewRecord,
    AuditLogEntry,
    ChangeRecord,
    ComplianceFramework,
    ComplianceStatus,
    SOC2ComplianceReport,
    SOC2Control,
    SOC2ControlCategory,
    SOC2ControlStatus,
    SOC2Evidence,
    SOC2EvidenceType,
)

logger = logging.getLogger(__name__)

# Singleton instance
_soc2_service: "SOC2Service | None" = None

# Default SOC 2 controls based on Trust Service Criteria
DEFAULT_CONTROLS = [
    # Security (Common Criteria)
    {"control_id": "CC1.1", "category": SOC2ControlCategory.SECURITY, "title": "COSO Principle 1", "description": "The entity demonstrates a commitment to integrity and ethical values."},
    {"control_id": "CC1.2", "category": SOC2ControlCategory.SECURITY, "title": "COSO Principle 2", "description": "The board of directors demonstrates independence from management and exercises oversight."},
    {"control_id": "CC2.1", "category": SOC2ControlCategory.SECURITY, "title": "COSO Principle 13", "description": "The entity obtains or generates and uses relevant, quality information."},
    {"control_id": "CC3.1", "category": SOC2ControlCategory.SECURITY, "title": "COSO Principle 6", "description": "The entity specifies objectives with sufficient clarity to enable risk identification."},
    {"control_id": "CC4.1", "category": SOC2ControlCategory.SECURITY, "title": "COSO Principle 16", "description": "The entity selects, develops, and performs ongoing evaluations."},
    {"control_id": "CC5.1", "category": SOC2ControlCategory.SECURITY, "title": "COSO Principle 10", "description": "The entity selects and develops control activities."},
    {"control_id": "CC6.1", "category": SOC2ControlCategory.SECURITY, "title": "Logical and Physical Access", "description": "The entity implements logical access security software, infrastructure, and architectures."},
    {"control_id": "CC6.2", "category": SOC2ControlCategory.SECURITY, "title": "User Registration", "description": "Prior to issuing system credentials, the entity registers and authorizes new users."},
    {"control_id": "CC6.3", "category": SOC2ControlCategory.SECURITY, "title": "Role-Based Access", "description": "The entity authorizes, modifies, or removes access to data based on roles."},
    {"control_id": "CC7.1", "category": SOC2ControlCategory.SECURITY, "title": "System Monitoring", "description": "The entity uses detection and monitoring procedures to identify anomalies."},
    {"control_id": "CC7.2", "category": SOC2ControlCategory.SECURITY, "title": "Incident Response", "description": "The entity monitors system components and the operation of those components."},
    {"control_id": "CC8.1", "category": SOC2ControlCategory.SECURITY, "title": "Change Management", "description": "The entity authorizes, designs, develops, configures, and implements changes."},
    {"control_id": "CC9.1", "category": SOC2ControlCategory.SECURITY, "title": "Risk Mitigation", "description": "The entity identifies, selects, and develops risk mitigation activities."},
    # Availability
    {"control_id": "A1.1", "category": SOC2ControlCategory.AVAILABILITY, "title": "Capacity Planning", "description": "The entity maintains, monitors, and evaluates current processing capacity."},
    {"control_id": "A1.2", "category": SOC2ControlCategory.AVAILABILITY, "title": "Environmental Controls", "description": "The entity authorizes, designs, develops environmental protections."},
    {"control_id": "A1.3", "category": SOC2ControlCategory.AVAILABILITY, "title": "Recovery Testing", "description": "The entity tests recovery plan procedures supporting system recovery."},
    # Processing Integrity
    {"control_id": "PI1.1", "category": SOC2ControlCategory.PROCESSING_INTEGRITY, "title": "Processing Accuracy", "description": "The entity implements policies and procedures for processing accuracy."},
    {"control_id": "PI1.2", "category": SOC2ControlCategory.PROCESSING_INTEGRITY, "title": "Data Validation", "description": "The entity implements policies for data validation."},
    # Confidentiality
    {"control_id": "C1.1", "category": SOC2ControlCategory.CONFIDENTIALITY, "title": "Confidential Information", "description": "The entity identifies and maintains confidential information."},
    {"control_id": "C1.2", "category": SOC2ControlCategory.CONFIDENTIALITY, "title": "Disposal Procedures", "description": "The entity disposes of confidential information securely."},
    # Privacy
    {"control_id": "P1.1", "category": SOC2ControlCategory.PRIVACY, "title": "Privacy Notice", "description": "The entity provides notice about its privacy practices."},
    {"control_id": "P2.1", "category": SOC2ControlCategory.PRIVACY, "title": "Choice and Consent", "description": "The entity communicates choices available regarding collection, use, and disclosure."},
    {"control_id": "P3.1", "category": SOC2ControlCategory.PRIVACY, "title": "Data Collection", "description": "Personal information is collected consistent with the entity's objectives."},
    {"control_id": "P4.1", "category": SOC2ControlCategory.PRIVACY, "title": "Data Use", "description": "The entity limits the use of personal information."},
    {"control_id": "P5.1", "category": SOC2ControlCategory.PRIVACY, "title": "Access Rights", "description": "The entity grants identified individuals the ability to access their stored information."},
]


class SOC2Service:
    """Service for managing SOC 2 compliance requirements.

    Handles:
    - Control tracking and status
    - Evidence management
    - Access reviews
    - Change management
    - Compliance reporting
    """

    def __init__(self, initialize_defaults: bool = True):
        # In-memory storage (replace with database in production)
        self._controls: dict[str, SOC2Control] = {}
        self._evidence: dict[str, list[SOC2Evidence]] = {}  # control_id -> evidence
        self._access_reviews: dict[str, AccessReviewRecord] = {}
        self._change_records: dict[str, ChangeRecord] = {}
        self._audit_log: list[AuditLogEntry] = []

        if initialize_defaults:
            self._initialize_default_controls()

    def _initialize_default_controls(self) -> None:
        """Initialize default SOC 2 controls."""
        for ctrl_data in DEFAULT_CONTROLS:
            control = SOC2Control(
                id=str(uuid.uuid4()),
                control_id=ctrl_data["control_id"],
                category=ctrl_data["category"],
                title=ctrl_data["title"],
                description=ctrl_data["description"],
            )
            self._controls[control.id] = control

    # --- Control Management ---

    async def get_control(self, control_id: str) -> SOC2Control | None:
        """Get a control by ID or control_id."""
        # Try by ID first
        if control_id in self._controls:
            return self._controls[control_id]
        # Try by control_id (e.g., "CC6.1")
        for ctrl in self._controls.values():
            if ctrl.control_id == control_id:
                return ctrl
        return None

    async def list_controls(
        self,
        category: SOC2ControlCategory | None = None,
        status: SOC2ControlStatus | None = None,
    ) -> list[SOC2Control]:
        """List controls with optional filters."""
        controls = list(self._controls.values())

        if category:
            controls = [c for c in controls if c.category == category]
        if status:
            controls = [c for c in controls if c.status == status]

        return sorted(controls, key=lambda c: c.control_id)

    async def update_control_status(
        self,
        control_id: str,
        status: SOC2ControlStatus,
        updated_by: str,
        implementation_notes: str | None = None,
    ) -> SOC2Control | None:
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
            actor=updated_by,
            resource_type="soc2_control",
            resource_id=control.id,
            details={
                "control_id": control.control_id,
                "old_status": old_status.value,
                "new_status": status.value,
            },
        )

        return control

    async def set_control_owner(
        self,
        control_id: str,
        owner: str,
    ) -> SOC2Control | None:
        """Set the owner of a control."""
        control = await self.get_control(control_id)
        if not control:
            return None

        control.owner = owner
        return control

    async def schedule_control_review(
        self,
        control_id: str,
        next_review: datetime,
    ) -> SOC2Control | None:
        """Schedule next review for a control."""
        control = await self.get_control(control_id)
        if not control:
            return None

        control.next_review = next_review
        return control

    async def record_control_test(
        self,
        control_id: str,
        tester: str,
        test_result: str,
        test_procedure: str | None = None,
    ) -> SOC2Control | None:
        """Record a control test result."""
        control = await self.get_control(control_id)
        if not control:
            return None

        control.last_tested = datetime.utcnow()
        control.test_result = test_result

        if test_procedure:
            control.test_procedure = test_procedure

        await self._log_action(
            action="control_tested",
            actor=tester,
            resource_type="soc2_control",
            resource_id=control.id,
            details={
                "control_id": control.control_id,
                "result": test_result,
            },
        )

        return control

    # --- Evidence Management ---

    async def add_evidence(
        self,
        control_id: str,
        evidence_type: SOC2EvidenceType,
        title: str,
        collected_by: str,
        description: str | None = None,
        file_path: str | None = None,
        content: str | None = None,
        url: str | None = None,
        valid_from: datetime | None = None,
        valid_until: datetime | None = None,
    ) -> SOC2Evidence:
        """Add evidence for a control."""
        evidence = SOC2Evidence(
            id=str(uuid.uuid4()),
            control_id=control_id,
            evidence_type=evidence_type,
            title=title,
            description=description,
            file_path=file_path,
            content=content,
            url=url,
            collected_by=collected_by,
            valid_from=valid_from or datetime.utcnow(),
            valid_until=valid_until,
        )

        if control_id not in self._evidence:
            self._evidence[control_id] = []
        self._evidence[control_id].append(evidence)

        await self._log_action(
            action="evidence_added",
            actor=collected_by,
            resource_type="soc2_evidence",
            resource_id=evidence.id,
            details={
                "control_id": control_id,
                "evidence_type": evidence_type.value,
            },
        )

        return evidence

    async def get_evidence(
        self,
        control_id: str,
        valid_only: bool = True,
    ) -> list[SOC2Evidence]:
        """Get evidence for a control."""
        evidence_list = self._evidence.get(control_id, [])

        if valid_only:
            now = datetime.utcnow()
            evidence_list = [
                e for e in evidence_list
                if not e.valid_until or e.valid_until > now
            ]

        return evidence_list

    async def verify_evidence(
        self,
        evidence_id: str,
        verifier: str,
    ) -> SOC2Evidence | None:
        """Mark evidence as verified."""
        for evidence_list in self._evidence.values():
            for evidence in evidence_list:
                if evidence.id == evidence_id:
                    evidence.verified = True
                    evidence.verified_by = verifier
                    evidence.verified_at = datetime.utcnow()

                    await self._log_action(
                        action="evidence_verified",
                        actor=verifier,
                        resource_type="soc2_evidence",
                        resource_id=evidence_id,
                    )

                    return evidence
        return None

    # --- Access Reviews ---

    async def create_access_review(
        self,
        review_period: str,
        reviewer: str,
        systems_reviewed: list[str],
    ) -> AccessReviewRecord:
        """Create a new access review."""
        review = AccessReviewRecord(
            id=str(uuid.uuid4()),
            review_period=review_period,
            reviewer=reviewer,
            review_date=datetime.utcnow(),
            systems_reviewed=systems_reviewed,
            status="in_progress",
        )

        self._access_reviews[review.id] = review

        await self._log_action(
            action="access_review_started",
            actor=reviewer,
            resource_type="access_review",
            resource_id=review.id,
            details={"period": review_period},
        )

        return review

    async def complete_access_review(
        self,
        review_id: str,
        total_access_rights: int,
        access_removed: int,
        access_modified: int,
        exceptions_found: int,
        exceptions_approved: int,
        findings: list[dict[str, Any]] | None = None,
        recommendations: list[str] | None = None,
    ) -> AccessReviewRecord | None:
        """Complete an access review."""
        review = self._access_reviews.get(review_id)
        if not review:
            return None

        review.status = "completed"
        review.total_access_rights = total_access_rights
        review.access_removed = access_removed
        review.access_modified = access_modified
        review.exceptions_found = exceptions_found
        review.exceptions_approved = exceptions_approved
        review.findings = findings or []
        review.recommendations = recommendations or []

        await self._log_action(
            action="access_review_completed",
            actor=review.reviewer,
            resource_type="access_review",
            resource_id=review_id,
            details={
                "total_rights": total_access_rights,
                "removed": access_removed,
                "exceptions": exceptions_found,
            },
        )

        return review

    async def approve_access_review(
        self,
        review_id: str,
        approver: str,
    ) -> AccessReviewRecord | None:
        """Approve a completed access review."""
        review = self._access_reviews.get(review_id)
        if not review or review.status != "completed":
            return None

        review.approved_by = approver
        review.approved_at = datetime.utcnow()

        await self._log_action(
            action="access_review_approved",
            actor=approver,
            resource_type="access_review",
            resource_id=review_id,
        )

        return review

    async def list_access_reviews(
        self,
        status: str | None = None,
    ) -> list[AccessReviewRecord]:
        """List access reviews."""
        reviews = list(self._access_reviews.values())
        if status:
            reviews = [r for r in reviews if r.status == status]
        return sorted(reviews, key=lambda r: r.review_date, reverse=True)

    # --- Change Management ---

    async def create_change_record(
        self,
        title: str,
        description: str,
        requested_by: str,
        change_type: str = "standard",
        risk_level: str = "low",
        category: str = "application",
        test_plan: str | None = None,
        rollback_plan: str | None = None,
    ) -> ChangeRecord:
        """Create a change management record."""
        change = ChangeRecord(
            id=str(uuid.uuid4()),
            change_id=f"CR-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
            title=title,
            description=description,
            change_type=change_type,
            risk_level=risk_level,
            category=category,
            requested_by=requested_by,
            requested_at=datetime.utcnow(),
            test_plan=test_plan,
            rollback_plan=rollback_plan,
        )

        self._change_records[change.id] = change

        await self._log_action(
            action="change_requested",
            actor=requested_by,
            resource_type="change_record",
            resource_id=change.id,
            details={
                "change_id": change.change_id,
                "risk_level": risk_level,
            },
        )

        return change

    async def approve_change(
        self,
        change_id: str,
        approver: str,
    ) -> ChangeRecord | None:
        """Approve a change request."""
        change = self._change_records.get(change_id)
        if not change:
            # Try by change_id
            for c in self._change_records.values():
                if c.change_id == change_id:
                    change = c
                    break
        if not change:
            return None

        change.approved_by = approver
        change.approved_at = datetime.utcnow()
        change.status = "approved"

        await self._log_action(
            action="change_approved",
            actor=approver,
            resource_type="change_record",
            resource_id=change.id,
        )

        return change

    async def implement_change(
        self,
        change_id: str,
        implementer: str,
        test_results: str | None = None,
    ) -> ChangeRecord | None:
        """Record change implementation."""
        change = self._change_records.get(change_id)
        if not change:
            for c in self._change_records.values():
                if c.change_id == change_id:
                    change = c
                    break
        if not change or change.status != "approved":
            return None

        change.implemented_by = implementer
        change.implemented_at = datetime.utcnow()
        change.tested_by = implementer
        change.test_results = test_results
        change.status = "implemented"

        await self._log_action(
            action="change_implemented",
            actor=implementer,
            resource_type="change_record",
            resource_id=change.id,
        )

        return change

    async def list_changes(
        self,
        status: str | None = None,
        change_type: str | None = None,
    ) -> list[ChangeRecord]:
        """List change records."""
        changes = list(self._change_records.values())
        if status:
            changes = [c for c in changes if c.status == status]
        if change_type:
            changes = [c for c in changes if c.change_type == change_type]
        return sorted(changes, key=lambda c: c.requested_at, reverse=True)

    # --- Compliance Reporting ---

    async def generate_compliance_report(
        self,
        report_period: str,
    ) -> SOC2ComplianceReport:
        """Generate a SOC 2 compliance report."""
        controls = list(self._controls.values())

        # Control metrics
        implemented = len([c for c in controls if c.status == SOC2ControlStatus.IMPLEMENTED])
        partially = len([c for c in controls if c.status == SOC2ControlStatus.PARTIALLY_IMPLEMENTED])
        not_implemented = len([c for c in controls if c.status == SOC2ControlStatus.NOT_IMPLEMENTED])

        implementation_rate = (implemented / len(controls) * 100) if controls else 0.0

        # Category status
        def get_category_status(cat: SOC2ControlCategory) -> ComplianceStatus:
            cat_controls = [c for c in controls if c.category == cat]
            if not cat_controls:
                return ComplianceStatus.NOT_APPLICABLE
            impl = len([c for c in cat_controls if c.status == SOC2ControlStatus.IMPLEMENTED])
            if impl == len(cat_controls):
                return ComplianceStatus.COMPLIANT
            elif impl > 0:
                return ComplianceStatus.PARTIAL
            return ComplianceStatus.NON_COMPLIANT

        # Evidence metrics
        all_evidence = [e for ev_list in self._evidence.values() for e in ev_list]
        verified_evidence = len([e for e in all_evidence if e.verified])
        expired_evidence = len([
            e for e in all_evidence
            if e.valid_until and e.valid_until < datetime.utcnow()
        ])

        # Access review metrics
        reviews = list(self._access_reviews.values())
        completed_reviews = len([r for r in reviews if r.status == "completed"])
        pending_reviews = len([r for r in reviews if r.status == "in_progress"])

        # Change management metrics
        changes = list(self._change_records.values())
        approved_changes = len([c for c in changes if c.status in ("approved", "implemented")])
        emergency_changes = len([c for c in changes if c.change_type == "emergency"])

        # Determine overall status
        if implementation_rate >= 95:
            status = ComplianceStatus.COMPLIANT
        elif implementation_rate >= 70:
            status = ComplianceStatus.PARTIAL
        else:
            status = ComplianceStatus.NON_COMPLIANT

        # Findings and recommendations
        findings: list[dict[str, Any]] = []
        recommendations: list[str] = []

        if not_implemented > 0:
            findings.append({
                "type": "unimplemented_controls",
                "count": not_implemented,
                "severity": "high",
                "description": f"{not_implemented} controls are not implemented",
            })
            recommendations.append("Implement all required controls")

        if expired_evidence > 0:
            findings.append({
                "type": "expired_evidence",
                "count": expired_evidence,
                "severity": "medium",
                "description": f"{expired_evidence} evidence items have expired",
            })
            recommendations.append("Refresh expired evidence")

        if emergency_changes > len(changes) * 0.1:
            findings.append({
                "type": "high_emergency_changes",
                "count": emergency_changes,
                "severity": "medium",
                "description": "High ratio of emergency changes",
            })
            recommendations.append("Reduce emergency changes through better planning")

        return SOC2ComplianceReport(
            report_period=report_period,
            status=status,
            total_controls=len(controls),
            implemented_controls=implemented,
            partially_implemented=partially,
            not_implemented=not_implemented,
            implementation_rate=implementation_rate,
            security_status=get_category_status(SOC2ControlCategory.SECURITY),
            availability_status=get_category_status(SOC2ControlCategory.AVAILABILITY),
            processing_integrity_status=get_category_status(SOC2ControlCategory.PROCESSING_INTEGRITY),
            confidentiality_status=get_category_status(SOC2ControlCategory.CONFIDENTIALITY),
            privacy_status=get_category_status(SOC2ControlCategory.PRIVACY),
            total_evidence=len(all_evidence),
            verified_evidence=verified_evidence,
            expired_evidence=expired_evidence,
            access_reviews_completed=completed_reviews,
            access_reviews_pending=pending_reviews,
            total_changes=len(changes),
            approved_changes=approved_changes,
            emergency_changes=emergency_changes,
            open_findings=len(findings),
            findings=findings,
            recommendations=recommendations,
        )

    # --- Audit Logging ---

    async def _log_action(
        self,
        action: str,
        actor: str,
        resource_type: str,
        resource_id: str,
        actor_type: str = "user",
        details: dict[str, Any] | None = None,
    ) -> None:
        """Log an audit entry."""
        entry = AuditLogEntry(
            id=str(uuid.uuid4()),
            framework=ComplianceFramework.SOC2,
            action=action,
            actor=actor,
            actor_type=actor_type,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
        )
        self._audit_log.append(entry)

    async def get_audit_log(
        self,
        resource_type: str | None = None,
        limit: int = 100,
    ) -> list[AuditLogEntry]:
        """Get audit log entries."""
        entries = self._audit_log

        if resource_type:
            entries = [e for e in entries if e.resource_type == resource_type]

        return sorted(entries, key=lambda e: e.timestamp, reverse=True)[:limit]


def get_soc2_service() -> SOC2Service:
    """Get or create the SOC 2 service singleton."""
    global _soc2_service

    if _soc2_service is None:
        _soc2_service = SOC2Service()

    return _soc2_service
