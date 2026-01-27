"""Business Associate Agreement (BAA) Management Service."""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

from app.services.compliance.hipaa.models import (
    BAA,
    BAAStatus,
    BAAType,
    PHICategory,
)

logger = logging.getLogger(__name__)

# Singleton instance
_baa_manager: "BAAManager | None" = None


class BAAManager:
    """Service for managing Business Associate Agreements.

    Tracks BAAs with vendors, subcontractors, and other business associates
    as required by HIPAA.
    """

    def __init__(self):
        # In-memory storage (replace with database in production)
        self._baas: dict[str, BAA] = {}
        self._audit_log: list[dict[str, Any]] = []

    async def create_baa(
        self,
        organization_id: str,
        covered_entity: str,
        business_associate: str,
        baa_type: BAAType = BAAType.FULL_BAA,
        ba_contact_name: str | None = None,
        ba_contact_email: str | None = None,
        phi_categories_shared: list[PHICategory] | None = None,
        permitted_uses: list[str] | None = None,
        permitted_disclosures: list[str] | None = None,
        encryption_required: bool = True,
        breach_notification_hours: int = 24,
        created_by: str | None = None,
    ) -> BAA:
        """Create a new BAA record."""
        baa = BAA(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            covered_entity=covered_entity,
            business_associate=business_associate,
            baa_type=baa_type,
            ba_contact_name=ba_contact_name,
            ba_contact_email=ba_contact_email,
            phi_categories_shared=phi_categories_shared or [],
            permitted_uses=permitted_uses or [],
            permitted_disclosures=permitted_disclosures or [],
            encryption_required=encryption_required,
            breach_notification_hours=breach_notification_hours,
            created_by=created_by,
        )

        self._baas[baa.id] = baa

        await self._log_action(
            action="baa_created",
            baa_id=baa.id,
            actor=created_by or "system",
            details={"business_associate": business_associate},
        )

        logger.info(f"BAA created: {baa.id} for {business_associate}")
        return baa

    async def get_baa(self, baa_id: str) -> BAA | None:
        """Get a BAA by ID."""
        return self._baas.get(baa_id)

    async def list_baas(
        self,
        organization_id: str | None = None,
        status: BAAStatus | None = None,
        baa_type: BAAType | None = None,
        expiring_within_days: int | None = None,
    ) -> list[BAA]:
        """List BAAs with optional filters."""
        baas = list(self._baas.values())

        if organization_id:
            baas = [b for b in baas if b.organization_id == organization_id]
        if status:
            baas = [b for b in baas if b.status == status]
        if baa_type:
            baas = [b for b in baas if b.baa_type == baa_type]
        if expiring_within_days:
            cutoff = datetime.utcnow() + timedelta(days=expiring_within_days)
            baas = [
                b for b in baas
                if b.expiration_date and b.expiration_date <= cutoff
                and b.status == BAAStatus.ACTIVE
            ]

        return sorted(baas, key=lambda b: b.created_at, reverse=True)

    async def update_baa(
        self,
        baa_id: str,
        updated_by: str,
        **updates,
    ) -> BAA | None:
        """Update a BAA record."""
        baa = self._baas.get(baa_id)
        if not baa:
            return None

        # Track changes for audit
        changes = {}
        for key, value in updates.items():
            if hasattr(baa, key):
                old_value = getattr(baa, key)
                if old_value != value:
                    changes[key] = {"old": old_value, "new": value}
                    setattr(baa, key, value)

        baa.updated_at = datetime.utcnow()

        await self._log_action(
            action="baa_updated",
            baa_id=baa_id,
            actor=updated_by,
            details={"changes": changes},
        )

        return baa

    async def submit_for_review(
        self,
        baa_id: str,
        submitted_by: str,
    ) -> BAA | None:
        """Submit BAA for review."""
        baa = self._baas.get(baa_id)
        if not baa or baa.status != BAAStatus.DRAFT:
            return None

        baa.status = BAAStatus.PENDING_REVIEW
        baa.updated_at = datetime.utcnow()

        await self._log_action(
            action="baa_submitted_for_review",
            baa_id=baa_id,
            actor=submitted_by,
        )

        return baa

    async def approve_baa(
        self,
        baa_id: str,
        approved_by: str,
    ) -> BAA | None:
        """Approve BAA and move to pending signature."""
        baa = self._baas.get(baa_id)
        if not baa or baa.status != BAAStatus.PENDING_REVIEW:
            return None

        baa.status = BAAStatus.PENDING_SIGNATURE
        baa.updated_at = datetime.utcnow()
        baa.reviewed_by = approved_by
        baa.last_reviewed = datetime.utcnow()

        await self._log_action(
            action="baa_approved",
            baa_id=baa_id,
            actor=approved_by,
        )

        return baa

    async def activate_baa(
        self,
        baa_id: str,
        activated_by: str,
        effective_date: datetime | None = None,
        expiration_date: datetime | None = None,
        signed_document_path: str | None = None,
    ) -> BAA | None:
        """Activate a signed BAA."""
        baa = self._baas.get(baa_id)
        if not baa or baa.status != BAAStatus.PENDING_SIGNATURE:
            return None

        baa.status = BAAStatus.ACTIVE
        baa.signed_date = datetime.utcnow()
        baa.effective_date = effective_date or datetime.utcnow()
        baa.expiration_date = expiration_date or (datetime.utcnow() + timedelta(days=365))
        baa.signed_document_path = signed_document_path
        baa.updated_at = datetime.utcnow()

        await self._log_action(
            action="baa_activated",
            baa_id=baa_id,
            actor=activated_by,
            details={
                "effective_date": baa.effective_date.isoformat(),
                "expiration_date": baa.expiration_date.isoformat() if baa.expiration_date else None,
            },
        )

        logger.info(f"BAA activated: {baa_id}")
        return baa

    async def renew_baa(
        self,
        baa_id: str,
        renewed_by: str,
        new_expiration_date: datetime,
        new_version: str | None = None,
    ) -> BAA | None:
        """Renew an active BAA."""
        baa = self._baas.get(baa_id)
        if not baa or baa.status != BAAStatus.ACTIVE:
            return None

        old_expiration = baa.expiration_date
        baa.expiration_date = new_expiration_date
        baa.status = BAAStatus.RENEWED
        baa.updated_at = datetime.utcnow()

        if new_version:
            baa.version = new_version

        await self._log_action(
            action="baa_renewed",
            baa_id=baa_id,
            actor=renewed_by,
            details={
                "old_expiration": old_expiration.isoformat() if old_expiration else None,
                "new_expiration": new_expiration_date.isoformat(),
            },
        )

        # Set status back to active after renewal
        baa.status = BAAStatus.ACTIVE

        logger.info(f"BAA renewed: {baa_id}")
        return baa

    async def terminate_baa(
        self,
        baa_id: str,
        terminated_by: str,
        reason: str | None = None,
    ) -> BAA | None:
        """Terminate a BAA."""
        baa = self._baas.get(baa_id)
        if not baa:
            return None

        baa.status = BAAStatus.TERMINATED
        baa.termination_date = datetime.utcnow()
        baa.updated_at = datetime.utcnow()

        if reason:
            baa.notes = f"{baa.notes or ''}\nTermination reason: {reason}".strip()

        await self._log_action(
            action="baa_terminated",
            baa_id=baa_id,
            actor=terminated_by,
            details={"reason": reason},
        )

        logger.info(f"BAA terminated: {baa_id}")
        return baa

    async def check_expiring_baas(
        self,
        organization_id: str,
        days_ahead: int = 90,
    ) -> list[BAA]:
        """Get BAAs expiring within specified days."""
        return await self.list_baas(
            organization_id=organization_id,
            status=BAAStatus.ACTIVE,
            expiring_within_days=days_ahead,
        )

    async def get_baa_summary(
        self,
        organization_id: str,
    ) -> dict[str, Any]:
        """Get BAA summary statistics."""
        baas = await self.list_baas(organization_id=organization_id)

        active = len([b for b in baas if b.status == BAAStatus.ACTIVE])
        expiring_90 = len(await self.check_expiring_baas(organization_id, 90))
        expiring_30 = len(await self.check_expiring_baas(organization_id, 30))
        pending = len([b for b in baas if b.status in (BAAStatus.PENDING_REVIEW, BAAStatus.PENDING_SIGNATURE)])
        expired = len([b for b in baas if b.status == BAAStatus.EXPIRED])

        # PHI categories shared across all active BAAs
        phi_categories: set[PHICategory] = set()
        for baa in baas:
            if baa.status == BAAStatus.ACTIVE:
                phi_categories.update(baa.phi_categories_shared)

        return {
            "total_baas": len(baas),
            "active_baas": active,
            "pending_baas": pending,
            "expired_baas": expired,
            "expiring_in_30_days": expiring_30,
            "expiring_in_90_days": expiring_90,
            "phi_categories_shared": [c.value for c in phi_categories],
            "requires_attention": expiring_30 > 0 or pending > 0,
        }

    async def _log_action(
        self,
        action: str,
        baa_id: str,
        actor: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Log an audit entry."""
        entry = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "baa_id": baa_id,
            "actor": actor,
            "details": details or {},
        }
        self._audit_log.append(entry)

    async def get_audit_log(
        self,
        baa_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get audit log entries."""
        entries = self._audit_log

        if baa_id:
            entries = [e for e in entries if e.get("baa_id") == baa_id]

        return sorted(entries, key=lambda e: e["timestamp"], reverse=True)[:limit]


def get_baa_manager() -> BAAManager:
    """Get or create the BAA manager singleton."""
    global _baa_manager

    if _baa_manager is None:
        _baa_manager = BAAManager()

    return _baa_manager
