"""GDPR Compliance Service."""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

from app.services.compliance.models import (
    ComplianceFramework,
    ComplianceStatus,
    ConsentRecord,
    ConsentType,
    DataCategory,
    DataRetentionPolicy,
    DataSubjectRequest,
    DataSubjectRequestStatus,
    DataSubjectRequestType,
    GDPRComplianceReport,
    PersonalDataInventory,
    AuditLogEntry,
)

logger = logging.getLogger(__name__)

# Singleton instance
_gdpr_service: "GDPRService | None" = None


class GDPRService:
    """Service for managing GDPR compliance requirements.

    Handles:
    - Data Subject Requests (DSR)
    - Consent management
    - Data retention policies
    - Personal data inventory
    - Compliance reporting
    """

    def __init__(self):
        # In-memory storage (replace with database in production)
        self._dsr_requests: dict[str, DataSubjectRequest] = {}
        self._consent_records: dict[str, list[ConsentRecord]] = {}  # user_id -> records
        self._retention_policies: dict[str, DataRetentionPolicy] = {}
        self._data_inventory: dict[str, PersonalDataInventory] = {}
        self._audit_log: list[AuditLogEntry] = []

    # --- Data Subject Requests ---

    async def create_dsr(
        self,
        user_id: str,
        email: str,
        request_type: DataSubjectRequestType,
        reason: str | None = None,
    ) -> DataSubjectRequest:
        """Create a new Data Subject Request.

        Args:
            user_id: ID of the user making the request
            email: Email address of the data subject
            request_type: Type of DSR (access, erasure, etc.)
            reason: Optional reason for the request

        Returns:
            The created DataSubjectRequest
        """
        dsr = DataSubjectRequest(
            id=str(uuid.uuid4()),
            user_id=user_id,
            email=email,
            request_type=request_type,
            reason=reason,
        )

        self._dsr_requests[dsr.id] = dsr

        # Log the action
        await self._log_action(
            action="dsr_created",
            actor=user_id,
            resource_type="data_subject_request",
            resource_id=dsr.id,
            details={"request_type": request_type.value},
        )

        logger.info(f"DSR created: {dsr.id} type={request_type.value}")
        return dsr

    async def get_dsr(self, dsr_id: str) -> DataSubjectRequest | None:
        """Get a DSR by ID."""
        return self._dsr_requests.get(dsr_id)

    async def list_dsrs(
        self,
        user_id: str | None = None,
        status: DataSubjectRequestStatus | None = None,
        request_type: DataSubjectRequestType | None = None,
    ) -> list[DataSubjectRequest]:
        """List DSRs with optional filters."""
        dsrs = list(self._dsr_requests.values())

        if user_id:
            dsrs = [d for d in dsrs if d.user_id == user_id]
        if status:
            dsrs = [d for d in dsrs if d.status == status]
        if request_type:
            dsrs = [d for d in dsrs if d.request_type == request_type]

        return sorted(dsrs, key=lambda d: d.created_at, reverse=True)

    async def process_dsr(
        self,
        dsr_id: str,
        processor_id: str,
        response_data: dict[str, Any] | None = None,
    ) -> DataSubjectRequest | None:
        """Mark a DSR as in progress."""
        dsr = self._dsr_requests.get(dsr_id)
        if not dsr:
            return None

        dsr.status = DataSubjectRequestStatus.IN_PROGRESS
        dsr.processed_by = processor_id
        dsr.audit_trail.append({
            "action": "processing_started",
            "timestamp": datetime.utcnow().isoformat(),
            "actor": processor_id,
        })

        await self._log_action(
            action="dsr_processing_started",
            actor=processor_id,
            resource_type="data_subject_request",
            resource_id=dsr_id,
        )

        return dsr

    async def complete_dsr(
        self,
        dsr_id: str,
        processor_id: str,
        response_data: dict[str, Any] | None = None,
    ) -> DataSubjectRequest | None:
        """Complete a DSR."""
        dsr = self._dsr_requests.get(dsr_id)
        if not dsr:
            return None

        dsr.status = DataSubjectRequestStatus.COMPLETED
        dsr.processed_at = datetime.utcnow()
        dsr.processed_by = processor_id
        dsr.response_data = response_data
        dsr.audit_trail.append({
            "action": "completed",
            "timestamp": datetime.utcnow().isoformat(),
            "actor": processor_id,
            "response_data_keys": list(response_data.keys()) if response_data else [],
        })

        await self._log_action(
            action="dsr_completed",
            actor=processor_id,
            resource_type="data_subject_request",
            resource_id=dsr_id,
            details={"request_type": dsr.request_type.value},
        )

        logger.info(f"DSR completed: {dsr_id}")
        return dsr

    async def reject_dsr(
        self,
        dsr_id: str,
        processor_id: str,
        rejection_reason: str,
    ) -> DataSubjectRequest | None:
        """Reject a DSR."""
        dsr = self._dsr_requests.get(dsr_id)
        if not dsr:
            return None

        dsr.status = DataSubjectRequestStatus.REJECTED
        dsr.processed_at = datetime.utcnow()
        dsr.processed_by = processor_id
        dsr.rejection_reason = rejection_reason
        dsr.audit_trail.append({
            "action": "rejected",
            "timestamp": datetime.utcnow().isoformat(),
            "actor": processor_id,
            "reason": rejection_reason,
        })

        await self._log_action(
            action="dsr_rejected",
            actor=processor_id,
            resource_type="data_subject_request",
            resource_id=dsr_id,
            details={"reason": rejection_reason},
        )

        return dsr

    async def get_overdue_dsrs(self) -> list[DataSubjectRequest]:
        """Get DSRs that are past their deadline."""
        now = datetime.utcnow()
        return [
            dsr for dsr in self._dsr_requests.values()
            if dsr.deadline and dsr.deadline < now
            and dsr.status in (DataSubjectRequestStatus.PENDING, DataSubjectRequestStatus.IN_PROGRESS)
        ]

    # --- Consent Management ---

    async def record_consent(
        self,
        user_id: str,
        consent_type: ConsentType,
        granted: bool,
        purpose: str,
        legal_basis: str = "consent",
        version: str = "1.0",
        ip_address: str | None = None,
        user_agent: str | None = None,
        source: str = "web",
    ) -> ConsentRecord:
        """Record a consent decision."""
        record = ConsentRecord(
            id=str(uuid.uuid4()),
            user_id=user_id,
            consent_type=consent_type,
            granted=granted,
            purpose=purpose,
            legal_basis=legal_basis,
            version=version,
            granted_at=datetime.utcnow() if granted else None,
            ip_address=ip_address,
            user_agent=user_agent,
            source=source,
        )

        if user_id not in self._consent_records:
            self._consent_records[user_id] = []
        self._consent_records[user_id].append(record)

        await self._log_action(
            action="consent_recorded",
            actor=user_id,
            resource_type="consent_record",
            resource_id=record.id,
            details={
                "consent_type": consent_type.value,
                "granted": granted,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return record

    async def revoke_consent(
        self,
        user_id: str,
        consent_type: ConsentType,
    ) -> ConsentRecord | None:
        """Revoke a specific consent type."""
        records = self._consent_records.get(user_id, [])

        # Find active consent of this type
        for record in reversed(records):
            if record.consent_type == consent_type and record.granted and not record.revoked_at:
                record.revoked_at = datetime.utcnow()
                record.granted = False

                await self._log_action(
                    action="consent_revoked",
                    actor=user_id,
                    resource_type="consent_record",
                    resource_id=record.id,
                    details={"consent_type": consent_type.value},
                )

                return record

        return None

    async def get_user_consents(
        self,
        user_id: str,
        active_only: bool = True,
    ) -> list[ConsentRecord]:
        """Get consent records for a user."""
        records = self._consent_records.get(user_id, [])

        if active_only:
            records = [
                r for r in records
                if r.granted and not r.revoked_at
                and (not r.expires_at or r.expires_at > datetime.utcnow())
            ]

        return records

    async def check_consent(
        self,
        user_id: str,
        consent_type: ConsentType,
    ) -> bool:
        """Check if user has active consent for a type."""
        consents = await self.get_user_consents(user_id, active_only=True)
        return any(c.consent_type == consent_type for c in consents)

    # --- Data Retention Policies ---

    async def create_retention_policy(
        self,
        name: str,
        description: str,
        data_category: DataCategory,
        retention_period_days: int,
        legal_basis: str,
        action_on_expiry: str = "delete",
        applies_to_tables: list[str] | None = None,
        applies_to_fields: list[str] | None = None,
    ) -> DataRetentionPolicy:
        """Create a data retention policy."""
        policy = DataRetentionPolicy(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            data_category=data_category,
            retention_period_days=retention_period_days,
            legal_basis=legal_basis,
            action_on_expiry=action_on_expiry,
            applies_to_tables=applies_to_tables or [],
            applies_to_fields=applies_to_fields or [],
        )

        self._retention_policies[policy.id] = policy

        await self._log_action(
            action="retention_policy_created",
            actor="system",
            actor_type="system",
            resource_type="retention_policy",
            resource_id=policy.id,
            details={"name": name, "retention_days": retention_period_days},
        )

        return policy

    async def list_retention_policies(
        self,
        enabled_only: bool = True,
    ) -> list[DataRetentionPolicy]:
        """List all retention policies."""
        policies = list(self._retention_policies.values())
        if enabled_only:
            policies = [p for p in policies if p.enabled]
        return policies

    async def execute_retention_policy(
        self,
        policy_id: str,
    ) -> dict[str, Any]:
        """Execute a retention policy (placeholder - implement actual deletion logic)."""
        policy = self._retention_policies.get(policy_id)
        if not policy:
            return {"success": False, "error": "Policy not found"}

        # This is a placeholder - actual implementation would:
        # 1. Query data older than retention period
        # 2. Delete/anonymize/archive based on action_on_expiry
        # 3. Update statistics

        policy.last_executed = datetime.utcnow()
        policy.next_execution = datetime.utcnow() + timedelta(days=1)

        await self._log_action(
            action="retention_policy_executed",
            actor="system",
            actor_type="automated",
            resource_type="retention_policy",
            resource_id=policy_id,
            details={"policy_name": policy.name},
        )

        return {
            "success": True,
            "policy_id": policy_id,
            "records_processed": 0,  # Placeholder
            "executed_at": policy.last_executed.isoformat(),
        }

    # --- Personal Data Inventory ---

    async def add_data_inventory_item(
        self,
        data_category: DataCategory,
        data_fields: list[str],
        storage_location: str,
        purpose: str,
        legal_basis: str,
        encryption: bool = True,
        retention_period_days: int | None = None,
        third_party_sharing: bool = False,
        third_parties: list[str] | None = None,
        cross_border_transfer: bool = False,
        transfer_countries: list[str] | None = None,
    ) -> PersonalDataInventory:
        """Add an item to the personal data inventory."""
        item = PersonalDataInventory(
            id=str(uuid.uuid4()),
            data_category=data_category,
            data_fields=data_fields,
            storage_location=storage_location,
            purpose=purpose,
            legal_basis=legal_basis,
            encryption=encryption,
            retention_period_days=retention_period_days,
            third_party_sharing=third_party_sharing,
            third_parties=third_parties or [],
            cross_border_transfer=cross_border_transfer,
            transfer_countries=transfer_countries or [],
        )

        self._data_inventory[item.id] = item
        return item

    async def get_data_inventory(
        self,
        category: DataCategory | None = None,
    ) -> list[PersonalDataInventory]:
        """Get the personal data inventory."""
        items = list(self._data_inventory.values())
        if category:
            items = [i for i in items if i.data_category == category]
        return items

    # --- Compliance Reporting ---

    async def generate_compliance_report(self) -> GDPRComplianceReport:
        """Generate a GDPR compliance report."""
        dsrs = list(self._dsr_requests.values())
        overdue_dsrs = await self.get_overdue_dsrs()

        # Calculate DSR metrics
        pending_dsrs = [d for d in dsrs if d.status == DataSubjectRequestStatus.PENDING]
        completed_dsrs = [d for d in dsrs if d.status == DataSubjectRequestStatus.COMPLETED]

        avg_completion_days = 0.0
        if completed_dsrs:
            dsrs_with_dates = [
                d for d in completed_dsrs if d.processed_at
            ]
            if dsrs_with_dates:
                total_days = sum(
                    (d.processed_at - d.created_at).days
                    for d in dsrs_with_dates
                )
                avg_completion_days = round(total_days / len(dsrs_with_dates), 2)

        # Count users with consent
        users_with_consent = len([
            uid for uid, records in self._consent_records.items()
            if any(r.granted and not r.revoked_at for r in records)
        ])
        total_users = len(self._consent_records)
        consent_rate = (users_with_consent / total_users * 100) if total_users > 0 else 0.0

        # Data inventory metrics
        inventory = list(self._data_inventory.values())
        third_party_processors = len(set(
            tp for item in inventory for tp in item.third_parties
        ))
        cross_border_transfers = len([i for i in inventory if i.cross_border_transfer])

        # Determine overall status
        status = ComplianceStatus.COMPLIANT
        issues: list[dict[str, Any]] = []
        recommendations: list[str] = []

        if overdue_dsrs:
            status = ComplianceStatus.NON_COMPLIANT
            issues.append({
                "type": "overdue_dsr",
                "count": len(overdue_dsrs),
                "severity": "high",
                "description": f"{len(overdue_dsrs)} DSRs are past their 30-day deadline",
            })
            recommendations.append("Process overdue Data Subject Requests immediately")

        if consent_rate < 80:
            if status == ComplianceStatus.COMPLIANT:
                status = ComplianceStatus.PARTIAL
            recommendations.append("Improve consent collection rate")

        if any(not i.encryption for i in inventory):
            issues.append({
                "type": "unencrypted_data",
                "severity": "medium",
                "description": "Some personal data storage locations are not encrypted",
            })
            recommendations.append("Enable encryption for all personal data storage")

        return GDPRComplianceReport(
            status=status,
            total_dsr_requests=len(dsrs),
            pending_dsr_requests=len(pending_dsrs),
            completed_dsr_requests=len(completed_dsrs),
            avg_dsr_completion_days=avg_completion_days,
            overdue_dsr_requests=len(overdue_dsrs),
            total_users=total_users,
            users_with_consent=users_with_consent,
            consent_rate=consent_rate,
            retention_policies_count=len(self._retention_policies),
            retention_policies_executed=len([
                p for p in self._retention_policies.values() if p.last_executed
            ]),
            data_categories_tracked=len(set(i.data_category for i in inventory)),
            third_party_processors=third_party_processors,
            cross_border_transfers=cross_border_transfers,
            compliance_issues=issues,
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
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Log an audit entry."""
        entry = AuditLogEntry(
            id=str(uuid.uuid4()),
            framework=ComplianceFramework.GDPR,
            action=action,
            actor=actor,
            actor_type=actor_type,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._audit_log.append(entry)

    async def get_audit_log(
        self,
        resource_type: str | None = None,
        resource_id: str | None = None,
        actor: str | None = None,
        limit: int = 100,
    ) -> list[AuditLogEntry]:
        """Get audit log entries."""
        entries = self._audit_log

        if resource_type:
            entries = [e for e in entries if e.resource_type == resource_type]
        if resource_id:
            entries = [e for e in entries if e.resource_id == resource_id]
        if actor:
            entries = [e for e in entries if e.actor == actor]

        return sorted(entries, key=lambda e: e.timestamp, reverse=True)[:limit]


def get_gdpr_service() -> GDPRService:
    """Get or create the GDPR service singleton."""
    global _gdpr_service

    if _gdpr_service is None:
        _gdpr_service = GDPRService()

    return _gdpr_service
