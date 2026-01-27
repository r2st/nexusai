"""Data Residency Service."""

import uuid
from datetime import datetime, timedelta
from typing import Any

from app.services.residency.models import (
    DataRegion,
    RegionStatus,
    DataClassification,
    DataResidencyPolicy,
    DataResidencyRequirement,
    StorageLocation,
    DataTransferRequest,
    TransferStatus,
    ResidencyViolation,
    ViolationSeverity,
    DEFAULT_REGIONS,
    DEFAULT_GDPR_REQUIREMENT,
    EU_EEA_COUNTRIES,
    EU_ADEQUACY_COUNTRIES,
)


class DataResidencyService:
    """Service for managing data residency controls."""

    def __init__(self):
        # In-memory storage - replace with database in production
        self._regions: dict[str, DataRegion] = {}
        self._policies: dict[str, DataResidencyPolicy] = {}
        self._org_policies: dict[str, str] = {}  # org_id -> policy_id
        self._storage_locations: dict[str, StorageLocation] = {}
        self._transfer_requests: dict[str, DataTransferRequest] = {}
        self._violations: dict[str, ResidencyViolation] = {}

        # Initialize default regions
        self._initialize_default_regions()

    def _initialize_default_regions(self) -> None:
        """Initialize default data regions."""
        for region_data in DEFAULT_REGIONS:
            region = DataRegion(**region_data)
            self._regions[region.id] = region

    # Region Management

    async def get_region(self, region_id: str) -> DataRegion | None:
        """Get a region by ID."""
        return self._regions.get(region_id)

    async def list_regions(
        self,
        status: RegionStatus | None = None,
        country_code: str | None = None,
        continent: str | None = None,
        provider: str | None = None,
    ) -> list[DataRegion]:
        """List regions with optional filters."""
        regions = list(self._regions.values())

        if status:
            regions = [r for r in regions if r.status == status]
        if country_code:
            regions = [r for r in regions if r.country_code == country_code]
        if continent:
            regions = [r for r in regions if r.continent == continent]
        if provider:
            regions = [r for r in regions if r.provider == provider]

        return regions

    async def add_region(
        self,
        name: str,
        code: str,
        display_name: str,
        country: str,
        country_code: str,
        continent: str,
        provider: str,
        provider_region: str,
        compliance_certifications: list[str] | None = None,
    ) -> DataRegion:
        """Add a new region."""
        region_id = code
        if region_id in self._regions:
            region_id = f"{code}-{uuid.uuid4().hex[:8]}"

        region = DataRegion(
            id=region_id,
            name=name,
            code=code,
            display_name=display_name,
            country=country,
            country_code=country_code,
            continent=continent,
            provider=provider,
            provider_region=provider_region,
            compliance_certifications=compliance_certifications or [],
        )
        self._regions[region_id] = region
        return region

    async def update_region_status(
        self,
        region_id: str,
        status: RegionStatus,
    ) -> DataRegion | None:
        """Update region status."""
        region = self._regions.get(region_id)
        if region:
            region.status = status
            region.updated_at = datetime.utcnow()
        return region

    # Policy Management

    async def create_policy(
        self,
        organization_id: str,
        name: str,
        description: str | None = None,
        default_region_id: str | None = None,
        requirements: list[dict[str, Any]] | None = None,
        enforce_on_upload: bool = True,
        enforce_on_processing: bool = True,
        enforce_on_backup: bool = True,
        exception_approvers: list[str] | None = None,
        created_by: str | None = None,
    ) -> DataResidencyPolicy:
        """Create a data residency policy."""
        policy_id = str(uuid.uuid4())

        # Convert requirement dicts to models
        req_models = []
        if requirements:
            for req_data in requirements:
                req = DataResidencyRequirement(
                    id=str(uuid.uuid4()),
                    **req_data,
                )
                req_models.append(req)

        policy = DataResidencyPolicy(
            id=policy_id,
            organization_id=organization_id,
            name=name,
            description=description,
            default_region_id=default_region_id,
            requirements=req_models,
            enforce_on_upload=enforce_on_upload,
            enforce_on_processing=enforce_on_processing,
            enforce_on_backup=enforce_on_backup,
            exception_approvers=exception_approvers or [],
            created_by=created_by,
        )

        self._policies[policy_id] = policy
        self._org_policies[organization_id] = policy_id

        return policy

    async def get_policy(self, policy_id: str) -> DataResidencyPolicy | None:
        """Get a policy by ID."""
        return self._policies.get(policy_id)

    async def get_organization_policy(
        self,
        organization_id: str,
    ) -> DataResidencyPolicy | None:
        """Get the policy for an organization."""
        policy_id = self._org_policies.get(organization_id)
        if policy_id:
            return self._policies.get(policy_id)
        return None

    async def update_policy(
        self,
        policy_id: str,
        name: str | None = None,
        description: str | None = None,
        default_region_id: str | None = None,
        enforce_on_upload: bool | None = None,
        enforce_on_processing: bool | None = None,
        enforce_on_backup: bool | None = None,
        exception_approvers: list[str] | None = None,
        is_active: bool | None = None,
    ) -> DataResidencyPolicy | None:
        """Update a policy."""
        policy = self._policies.get(policy_id)
        if not policy:
            return None

        if name is not None:
            policy.name = name
        if description is not None:
            policy.description = description
        if default_region_id is not None:
            policy.default_region_id = default_region_id
        if enforce_on_upload is not None:
            policy.enforce_on_upload = enforce_on_upload
        if enforce_on_processing is not None:
            policy.enforce_on_processing = enforce_on_processing
        if enforce_on_backup is not None:
            policy.enforce_on_backup = enforce_on_backup
        if exception_approvers is not None:
            policy.exception_approvers = exception_approvers
        if is_active is not None:
            policy.is_active = is_active

        policy.updated_at = datetime.utcnow()
        policy.version += 1

        return policy

    async def add_requirement(
        self,
        policy_id: str,
        name: str,
        description: str,
        data_classifications: list[DataClassification] | None = None,
        allowed_regions: list[str] | None = None,
        allowed_countries: list[str] | None = None,
        allowed_continents: list[str] | None = None,
        prohibited_regions: list[str] | None = None,
        prohibited_countries: list[str] | None = None,
        allow_cross_border_transfer: bool = False,
        require_adequacy_decision: bool = True,
        require_encryption_at_rest: bool = True,
        require_encryption_in_transit: bool = True,
        regulation: str | None = None,
    ) -> DataResidencyRequirement | None:
        """Add a requirement to a policy."""
        policy = self._policies.get(policy_id)
        if not policy:
            return None

        requirement = DataResidencyRequirement(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            data_classifications=data_classifications or [],
            allowed_regions=allowed_regions or [],
            allowed_countries=allowed_countries or [],
            allowed_continents=allowed_continents or [],
            prohibited_regions=prohibited_regions or [],
            prohibited_countries=prohibited_countries or [],
            allow_cross_border_transfer=allow_cross_border_transfer,
            require_adequacy_decision=require_adequacy_decision,
            require_encryption_at_rest=require_encryption_at_rest,
            require_encryption_in_transit=require_encryption_in_transit,
            regulation=regulation,
        )

        policy.requirements.append(requirement)
        policy.updated_at = datetime.utcnow()
        policy.version += 1

        return requirement

    async def add_gdpr_requirement(
        self,
        policy_id: str,
    ) -> DataResidencyRequirement | None:
        """Add default GDPR requirement to a policy."""
        policy = self._policies.get(policy_id)
        if not policy:
            return None

        req_data = DEFAULT_GDPR_REQUIREMENT.copy()
        req_data["id"] = str(uuid.uuid4())
        requirement = DataResidencyRequirement(**req_data)

        policy.requirements.append(requirement)
        policy.updated_at = datetime.utcnow()
        policy.version += 1

        return requirement

    # Storage Location Management

    async def register_storage_location(
        self,
        organization_id: str,
        name: str,
        region_id: str,
        storage_type: str,
        provider: str,
        provider_identifier: str,
        data_classifications: list[DataClassification] | None = None,
        encryption_enabled: bool = True,
        encryption_key_id: str | None = None,
        encryption_algorithm: str | None = None,
        description: str | None = None,
        endpoint: str | None = None,
        registered_by: str | None = None,
    ) -> StorageLocation:
        """Register a storage location."""
        location_id = str(uuid.uuid4())

        # Check region exists
        region = self._regions.get(region_id)
        if not region:
            raise ValueError(f"Region {region_id} not found")

        location = StorageLocation(
            id=location_id,
            organization_id=organization_id,
            name=name,
            description=description,
            region_id=region_id,
            storage_type=storage_type,
            provider=provider,
            provider_identifier=provider_identifier,
            endpoint=endpoint,
            data_classifications=data_classifications or [],
            encryption_enabled=encryption_enabled,
            encryption_key_id=encryption_key_id,
            encryption_algorithm=encryption_algorithm,
            registered_by=registered_by,
        )

        self._storage_locations[location_id] = location

        # Check compliance
        await self._check_location_compliance(location)

        return location

    async def _check_location_compliance(
        self,
        location: StorageLocation,
    ) -> None:
        """Check if a storage location is compliant with policy."""
        policy = await self.get_organization_policy(location.organization_id)
        if not policy or not policy.is_active:
            location.compliant = True
            location.compliance_issues = []
            return

        region = self._regions.get(location.region_id)
        if not region:
            location.compliant = False
            location.compliance_issues = ["Region not found"]
            return

        issues = []

        for requirement in policy.requirements:
            if not requirement.is_active:
                continue

            # Check if this requirement applies to this location's data
            if requirement.data_classifications:
                if not any(
                    dc in requirement.data_classifications
                    for dc in location.data_classifications
                ):
                    continue  # Requirement doesn't apply

            # Check allowed regions
            if requirement.allowed_regions:
                if region.id not in requirement.allowed_regions:
                    issues.append(
                        f"Region {region.id} not in allowed regions for {requirement.name}"
                    )

            # Check allowed countries
            if requirement.allowed_countries:
                if region.country_code not in requirement.allowed_countries:
                    issues.append(
                        f"Country {region.country_code} not in allowed countries for {requirement.name}"
                    )

            # Check prohibited regions
            if region.id in requirement.prohibited_regions:
                issues.append(
                    f"Region {region.id} is prohibited for {requirement.name}"
                )

            # Check prohibited countries
            if region.country_code in requirement.prohibited_countries:
                issues.append(
                    f"Country {region.country_code} is prohibited for {requirement.name}"
                )

            # Check encryption
            if requirement.require_encryption_at_rest and not location.encryption_enabled:
                issues.append(f"Encryption at rest required by {requirement.name}")

        location.compliant = len(issues) == 0
        location.compliance_issues = issues
        location.last_compliance_check = datetime.utcnow()

        # Create violations if not compliant
        if not location.compliant:
            for issue in issues:
                await self._create_violation(
                    organization_id=location.organization_id,
                    violation_type="policy_violation",
                    severity=ViolationSeverity.HIGH,
                    description=issue,
                    policy_id=policy.id,
                    storage_location_id=location.id,
                    region_id=region.id,
                    country_code=region.country_code,
                )

    async def get_storage_location(
        self,
        location_id: str,
    ) -> StorageLocation | None:
        """Get a storage location."""
        return self._storage_locations.get(location_id)

    async def list_storage_locations(
        self,
        organization_id: str | None = None,
        region_id: str | None = None,
        storage_type: str | None = None,
        compliant: bool | None = None,
    ) -> list[StorageLocation]:
        """List storage locations."""
        locations = list(self._storage_locations.values())

        if organization_id:
            locations = [l for l in locations if l.organization_id == organization_id]
        if region_id:
            locations = [l for l in locations if l.region_id == region_id]
        if storage_type:
            locations = [l for l in locations if l.storage_type == storage_type]
        if compliant is not None:
            locations = [l for l in locations if l.compliant == compliant]

        return locations

    # Data Transfer Management

    async def create_transfer_request(
        self,
        organization_id: str,
        source_region_id: str,
        destination_region_id: str,
        data_classification: DataClassification,
        data_description: str,
        purpose: str,
        business_justification: str,
        requestor_id: str,
        requestor_username: str,
        source_location_id: str | None = None,
        destination_location_id: str | None = None,
        estimated_size_bytes: int | None = None,
        legal_basis: str | None = None,
        sccs_reference: str | None = None,
    ) -> DataTransferRequest:
        """Create a data transfer request."""
        request_id = str(uuid.uuid4())
        now = datetime.utcnow()

        request = DataTransferRequest(
            id=request_id,
            organization_id=organization_id,
            source_region_id=source_region_id,
            source_location_id=source_location_id,
            destination_region_id=destination_region_id,
            destination_location_id=destination_location_id,
            data_classification=data_classification,
            data_description=data_description,
            estimated_size_bytes=estimated_size_bytes,
            purpose=purpose,
            business_justification=business_justification,
            requestor_id=requestor_id,
            requestor_username=requestor_username,
            legal_basis=legal_basis,
            sccs_reference=sccs_reference,
            created_at=now,
            expires_at=now + timedelta(days=30),
        )

        # Add audit log entry
        request.audit_log.append({
            "action": "created",
            "timestamp": now.isoformat(),
            "actor": requestor_id,
            "details": "Transfer request created",
        })

        self._transfer_requests[request_id] = request

        # Check if auto-approval is possible
        await self._check_transfer_approval(request)

        return request

    async def _check_transfer_approval(
        self,
        request: DataTransferRequest,
    ) -> None:
        """Check if transfer can be auto-approved based on policy."""
        policy = await self.get_organization_policy(request.organization_id)
        if not policy or not policy.is_active:
            return  # No policy, needs manual review

        source_region = self._regions.get(request.source_region_id)
        dest_region = self._regions.get(request.destination_region_id)

        if not source_region or not dest_region:
            return

        # Check if same country (always allowed)
        if source_region.country_code == dest_region.country_code:
            # Auto-approve same-country transfers
            request.status = TransferStatus.APPROVED
            request.approved_by = "system"
            request.approved_at = datetime.utcnow()
            request.audit_log.append({
                "action": "auto_approved",
                "timestamp": datetime.utcnow().isoformat(),
                "actor": "system",
                "details": "Auto-approved: same country transfer",
            })
            return

        # Check if both in EU/EEA
        if (source_region.country_code in EU_EEA_COUNTRIES and
                dest_region.country_code in EU_EEA_COUNTRIES):
            request.status = TransferStatus.APPROVED
            request.approved_by = "system"
            request.approved_at = datetime.utcnow()
            request.audit_log.append({
                "action": "auto_approved",
                "timestamp": datetime.utcnow().isoformat(),
                "actor": "system",
                "details": "Auto-approved: intra-EU/EEA transfer",
            })
            return

        # Check adequacy decisions for transfers from EU
        if source_region.country_code in EU_EEA_COUNTRIES:
            if dest_region.country_code in EU_ADEQUACY_COUNTRIES:
                request.status = TransferStatus.APPROVED
                request.approved_by = "system"
                request.approved_at = datetime.utcnow()
                request.audit_log.append({
                    "action": "auto_approved",
                    "timestamp": datetime.utcnow().isoformat(),
                    "actor": "system",
                    "details": f"Auto-approved: adequacy decision for {dest_region.country_code}",
                })
                return

    async def get_transfer_request(
        self,
        request_id: str,
    ) -> DataTransferRequest | None:
        """Get a transfer request."""
        return self._transfer_requests.get(request_id)

    async def list_transfer_requests(
        self,
        organization_id: str | None = None,
        status: TransferStatus | None = None,
        requestor_id: str | None = None,
        limit: int = 100,
    ) -> list[DataTransferRequest]:
        """List transfer requests."""
        requests = list(self._transfer_requests.values())

        if organization_id:
            requests = [r for r in requests if r.organization_id == organization_id]
        if status:
            requests = [r for r in requests if r.status == status]
        if requestor_id:
            requests = [r for r in requests if r.requestor_id == requestor_id]

        # Sort by created_at descending
        requests.sort(key=lambda r: r.created_at, reverse=True)

        return requests[:limit]

    async def approve_transfer(
        self,
        request_id: str,
        approved_by: str,
    ) -> DataTransferRequest | None:
        """Approve a transfer request."""
        request = self._transfer_requests.get(request_id)
        if not request or request.status != TransferStatus.PENDING:
            return None

        request.status = TransferStatus.APPROVED
        request.approved_by = approved_by
        request.approved_at = datetime.utcnow()
        request.audit_log.append({
            "action": "approved",
            "timestamp": datetime.utcnow().isoformat(),
            "actor": approved_by,
            "details": "Transfer request approved",
        })

        return request

    async def reject_transfer(
        self,
        request_id: str,
        rejected_by: str,
        reason: str,
    ) -> DataTransferRequest | None:
        """Reject a transfer request."""
        request = self._transfer_requests.get(request_id)
        if not request or request.status != TransferStatus.PENDING:
            return None

        request.status = TransferStatus.REJECTED
        request.rejection_reason = reason
        request.audit_log.append({
            "action": "rejected",
            "timestamp": datetime.utcnow().isoformat(),
            "actor": rejected_by,
            "details": f"Rejected: {reason}",
        })

        return request

    async def start_transfer(
        self,
        request_id: str,
        transfer_method: str,
    ) -> DataTransferRequest | None:
        """Start an approved transfer."""
        request = self._transfer_requests.get(request_id)
        if not request or request.status != TransferStatus.APPROVED:
            return None

        request.status = TransferStatus.IN_PROGRESS
        request.started_at = datetime.utcnow()
        request.transfer_method = transfer_method
        request.audit_log.append({
            "action": "started",
            "timestamp": datetime.utcnow().isoformat(),
            "actor": "system",
            "details": f"Transfer started using {transfer_method}",
        })

        return request

    async def complete_transfer(
        self,
        request_id: str,
        bytes_transferred: int,
    ) -> DataTransferRequest | None:
        """Mark a transfer as complete."""
        request = self._transfer_requests.get(request_id)
        if not request or request.status != TransferStatus.IN_PROGRESS:
            return None

        request.status = TransferStatus.COMPLETED
        request.completed_at = datetime.utcnow()
        request.bytes_transferred = bytes_transferred
        request.audit_log.append({
            "action": "completed",
            "timestamp": datetime.utcnow().isoformat(),
            "actor": "system",
            "details": f"Transfer completed: {bytes_transferred} bytes",
        })

        return request

    # Violation Management

    async def _create_violation(
        self,
        organization_id: str,
        violation_type: str,
        severity: ViolationSeverity,
        description: str,
        policy_id: str | None = None,
        requirement_id: str | None = None,
        storage_location_id: str | None = None,
        transfer_request_id: str | None = None,
        data_classification: DataClassification | None = None,
        region_id: str | None = None,
        country_code: str | None = None,
    ) -> ResidencyViolation:
        """Create a residency violation."""
        violation_id = str(uuid.uuid4())

        violation = ResidencyViolation(
            id=violation_id,
            organization_id=organization_id,
            violation_type=violation_type,
            severity=severity,
            description=description,
            policy_id=policy_id,
            requirement_id=requirement_id,
            storage_location_id=storage_location_id,
            transfer_request_id=transfer_request_id,
            data_classification=data_classification,
            region_id=region_id,
            country_code=country_code,
            detected_by="system",
            detection_method="policy_check",
        )

        self._violations[violation_id] = violation

        return violation

    async def get_violation(
        self,
        violation_id: str,
    ) -> ResidencyViolation | None:
        """Get a violation."""
        return self._violations.get(violation_id)

    async def list_violations(
        self,
        organization_id: str | None = None,
        severity: ViolationSeverity | None = None,
        resolved: bool | None = None,
        limit: int = 100,
    ) -> list[ResidencyViolation]:
        """List violations."""
        violations = list(self._violations.values())

        if organization_id:
            violations = [v for v in violations if v.organization_id == organization_id]
        if severity:
            violations = [v for v in violations if v.severity == severity]
        if resolved is not None:
            violations = [v for v in violations if v.resolved == resolved]

        # Sort by detected_at descending
        violations.sort(key=lambda v: v.detected_at, reverse=True)

        return violations[:limit]

    async def resolve_violation(
        self,
        violation_id: str,
        resolved_by: str,
        resolution_notes: str,
    ) -> ResidencyViolation | None:
        """Resolve a violation."""
        violation = self._violations.get(violation_id)
        if not violation:
            return None

        violation.resolved = True
        violation.resolved_at = datetime.utcnow()
        violation.resolved_by = resolved_by
        violation.resolution_notes = resolution_notes

        return violation

    # Compliance Checking

    async def check_region_compliance(
        self,
        organization_id: str,
        region_id: str,
        data_classification: DataClassification,
    ) -> dict[str, Any]:
        """Check if a region is compliant for a data classification."""
        policy = await self.get_organization_policy(organization_id)
        region = self._regions.get(region_id)

        if not region:
            return {
                "compliant": False,
                "issues": ["Region not found"],
            }

        if not policy or not policy.is_active:
            return {
                "compliant": True,
                "issues": [],
                "note": "No active policy",
            }

        issues = []

        for requirement in policy.requirements:
            if not requirement.is_active:
                continue

            # Check if requirement applies to this data classification
            if requirement.data_classifications:
                if data_classification not in requirement.data_classifications:
                    continue

            # Check allowed regions
            if requirement.allowed_regions:
                if region.id not in requirement.allowed_regions:
                    issues.append(f"Region not in allowed list for {requirement.name}")

            # Check allowed countries
            if requirement.allowed_countries:
                if region.country_code not in requirement.allowed_countries:
                    issues.append(f"Country not in allowed list for {requirement.name}")

            # Check prohibited regions
            if region.id in requirement.prohibited_regions:
                issues.append(f"Region is prohibited by {requirement.name}")

            # Check prohibited countries
            if region.country_code in requirement.prohibited_countries:
                issues.append(f"Country is prohibited by {requirement.name}")

        return {
            "compliant": len(issues) == 0,
            "region": region.model_dump(),
            "issues": issues,
        }

    async def get_allowed_regions(
        self,
        organization_id: str,
        data_classification: DataClassification,
    ) -> list[DataRegion]:
        """Get list of allowed regions for a data classification."""
        policy = await self.get_organization_policy(organization_id)
        all_regions = list(self._regions.values())

        if not policy or not policy.is_active:
            # No policy, all active regions allowed
            return [r for r in all_regions if r.status == RegionStatus.ACTIVE]

        allowed = []

        for region in all_regions:
            if region.status != RegionStatus.ACTIVE:
                continue

            is_allowed = True

            for requirement in policy.requirements:
                if not requirement.is_active:
                    continue

                # Check if requirement applies
                if requirement.data_classifications:
                    if data_classification not in requirement.data_classifications:
                        continue

                # Check if region is prohibited
                if region.id in requirement.prohibited_regions:
                    is_allowed = False
                    break

                if region.country_code in requirement.prohibited_countries:
                    is_allowed = False
                    break

                # Check if region is in allowed list (if specified)
                if requirement.allowed_regions:
                    if region.id not in requirement.allowed_regions:
                        is_allowed = False
                        break

                if requirement.allowed_countries:
                    if region.country_code not in requirement.allowed_countries:
                        is_allowed = False
                        break

            if is_allowed:
                allowed.append(region)

        return allowed

    async def get_residency_dashboard(
        self,
        organization_id: str,
    ) -> dict[str, Any]:
        """Get residency dashboard data."""
        policy = await self.get_organization_policy(organization_id)
        locations = await self.list_storage_locations(organization_id=organization_id)
        transfers = await self.list_transfer_requests(organization_id=organization_id)
        violations = await self.list_violations(organization_id=organization_id, resolved=False)

        # Count by region
        locations_by_region: dict[str, int] = {}
        for location in locations:
            locations_by_region[location.region_id] = locations_by_region.get(
                location.region_id, 0
            ) + 1

        # Transfer stats
        pending_transfers = sum(1 for t in transfers if t.status == TransferStatus.PENDING)
        active_transfers = sum(1 for t in transfers if t.status == TransferStatus.IN_PROGRESS)

        return {
            "policy": policy.model_dump() if policy else None,
            "storage_locations": {
                "total": len(locations),
                "compliant": sum(1 for l in locations if l.compliant),
                "non_compliant": sum(1 for l in locations if not l.compliant),
                "by_region": locations_by_region,
            },
            "transfers": {
                "pending": pending_transfers,
                "active": active_transfers,
                "total_30_days": len(transfers),
            },
            "violations": {
                "unresolved": len(violations),
                "critical": sum(1 for v in violations if v.severity == ViolationSeverity.CRITICAL),
                "high": sum(1 for v in violations if v.severity == ViolationSeverity.HIGH),
            },
            "regions": {
                "total": len(self._regions),
                "active": sum(1 for r in self._regions.values() if r.status == RegionStatus.ACTIVE),
            },
        }


# Singleton instance
_data_residency_service: DataResidencyService | None = None


def get_data_residency_service() -> DataResidencyService:
    """Get the data residency service singleton."""
    global _data_residency_service
    if _data_residency_service is None:
        _data_residency_service = DataResidencyService()
    return _data_residency_service
