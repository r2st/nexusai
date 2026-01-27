"""Data Residency API endpoints."""

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.residency import (
    get_data_residency_service,
    RegionStatus,
    DataClassification,
    TransferStatus,
    ViolationSeverity,
)

router = APIRouter(prefix="/residency", tags=["residency"])


# --- Request/Response Models ---

class CreatePolicyRequest(BaseModel):
    """Request to create a residency policy."""
    organization_id: str
    name: str
    description: str | None = None
    default_region_id: str | None = None
    enforce_on_upload: bool = True
    enforce_on_processing: bool = True
    enforce_on_backup: bool = True
    exception_approvers: list[str] = Field(default_factory=list)
    created_by: str | None = None


class UpdatePolicyRequest(BaseModel):
    """Request to update a policy."""
    name: str | None = None
    description: str | None = None
    default_region_id: str | None = None
    enforce_on_upload: bool | None = None
    enforce_on_processing: bool | None = None
    enforce_on_backup: bool | None = None
    exception_approvers: list[str] | None = None
    is_active: bool | None = None


class AddRequirementRequest(BaseModel):
    """Request to add a requirement."""
    name: str
    description: str
    data_classifications: list[DataClassification] = Field(default_factory=list)
    allowed_regions: list[str] = Field(default_factory=list)
    allowed_countries: list[str] = Field(default_factory=list)
    allowed_continents: list[str] = Field(default_factory=list)
    prohibited_regions: list[str] = Field(default_factory=list)
    prohibited_countries: list[str] = Field(default_factory=list)
    allow_cross_border_transfer: bool = False
    require_adequacy_decision: bool = True
    require_encryption_at_rest: bool = True
    require_encryption_in_transit: bool = True
    regulation: str | None = None


class RegisterStorageRequest(BaseModel):
    """Request to register a storage location."""
    organization_id: str
    name: str
    region_id: str
    storage_type: str
    provider: str
    provider_identifier: str
    data_classifications: list[DataClassification] = Field(default_factory=list)
    encryption_enabled: bool = True
    encryption_key_id: str | None = None
    encryption_algorithm: str | None = None
    description: str | None = None
    endpoint: str | None = None
    registered_by: str | None = None


class CreateTransferRequest(BaseModel):
    """Request to create a data transfer."""
    organization_id: str
    source_region_id: str
    destination_region_id: str
    data_classification: DataClassification
    data_description: str
    purpose: str
    business_justification: str
    requestor_id: str
    requestor_username: str
    source_location_id: str | None = None
    destination_location_id: str | None = None
    estimated_size_bytes: int | None = None
    legal_basis: str | None = None
    sccs_reference: str | None = None


class ApproveTransferRequest(BaseModel):
    """Request to approve a transfer."""
    approved_by: str


class RejectTransferRequest(BaseModel):
    """Request to reject a transfer."""
    rejected_by: str
    reason: str


class StartTransferRequest(BaseModel):
    """Request to start a transfer."""
    transfer_method: str


class CompleteTransferRequest(BaseModel):
    """Request to complete a transfer."""
    bytes_transferred: int


class ResolveViolationRequest(BaseModel):
    """Request to resolve a violation."""
    resolved_by: str
    resolution_notes: str


class CheckComplianceRequest(BaseModel):
    """Request to check region compliance."""
    organization_id: str
    region_id: str
    data_classification: DataClassification


# --- Region Endpoints ---

@router.get("/regions")
async def list_regions(
    status: RegionStatus | None = None,
    country_code: str | None = None,
    continent: str | None = None,
    provider: str | None = None,
):
    """List available data regions."""
    service = get_data_residency_service()
    regions = await service.list_regions(
        status=status,
        country_code=country_code,
        continent=continent,
        provider=provider,
    )
    return {"regions": [r.model_dump() for r in regions]}


@router.get("/regions/{region_id}")
async def get_region(region_id: str):
    """Get a region by ID."""
    service = get_data_residency_service()
    region = await service.get_region(region_id)
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")
    return {"region": region.model_dump()}


@router.put("/regions/{region_id}/status")
async def update_region_status(region_id: str, status: RegionStatus):
    """Update region status."""
    service = get_data_residency_service()
    region = await service.update_region_status(region_id, status)
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")
    return {"region": region.model_dump()}


# --- Policy Endpoints ---

@router.post("/policies")
async def create_policy(request: CreatePolicyRequest):
    """Create a data residency policy."""
    service = get_data_residency_service()
    policy = await service.create_policy(
        organization_id=request.organization_id,
        name=request.name,
        description=request.description,
        default_region_id=request.default_region_id,
        enforce_on_upload=request.enforce_on_upload,
        enforce_on_processing=request.enforce_on_processing,
        enforce_on_backup=request.enforce_on_backup,
        exception_approvers=request.exception_approvers,
        created_by=request.created_by,
    )
    return {"policy": policy.model_dump()}


@router.get("/policies/{policy_id}")
async def get_policy(policy_id: str):
    """Get a policy by ID."""
    service = get_data_residency_service()
    policy = await service.get_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return {"policy": policy.model_dump()}


@router.get("/policies/organization/{organization_id}")
async def get_organization_policy(organization_id: str):
    """Get the policy for an organization."""
    service = get_data_residency_service()
    policy = await service.get_organization_policy(organization_id)
    if not policy:
        raise HTTPException(status_code=404, detail="No policy found for organization")
    return {"policy": policy.model_dump()}


@router.put("/policies/{policy_id}")
async def update_policy(policy_id: str, request: UpdatePolicyRequest):
    """Update a policy."""
    service = get_data_residency_service()
    policy = await service.update_policy(
        policy_id=policy_id,
        name=request.name,
        description=request.description,
        default_region_id=request.default_region_id,
        enforce_on_upload=request.enforce_on_upload,
        enforce_on_processing=request.enforce_on_processing,
        enforce_on_backup=request.enforce_on_backup,
        exception_approvers=request.exception_approvers,
        is_active=request.is_active,
    )
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return {"policy": policy.model_dump()}


@router.post("/policies/{policy_id}/requirements")
async def add_requirement(policy_id: str, request: AddRequirementRequest):
    """Add a requirement to a policy."""
    service = get_data_residency_service()
    requirement = await service.add_requirement(
        policy_id=policy_id,
        name=request.name,
        description=request.description,
        data_classifications=request.data_classifications,
        allowed_regions=request.allowed_regions,
        allowed_countries=request.allowed_countries,
        allowed_continents=request.allowed_continents,
        prohibited_regions=request.prohibited_regions,
        prohibited_countries=request.prohibited_countries,
        allow_cross_border_transfer=request.allow_cross_border_transfer,
        require_adequacy_decision=request.require_adequacy_decision,
        require_encryption_at_rest=request.require_encryption_at_rest,
        require_encryption_in_transit=request.require_encryption_in_transit,
        regulation=request.regulation,
    )
    if not requirement:
        raise HTTPException(status_code=404, detail="Policy not found")
    return {"requirement": requirement.model_dump()}


@router.post("/policies/{policy_id}/requirements/gdpr")
async def add_gdpr_requirement(policy_id: str):
    """Add default GDPR requirement to a policy."""
    service = get_data_residency_service()
    requirement = await service.add_gdpr_requirement(policy_id)
    if not requirement:
        raise HTTPException(status_code=404, detail="Policy not found")
    return {"requirement": requirement.model_dump()}


# --- Storage Location Endpoints ---

@router.post("/storage")
async def register_storage_location(request: RegisterStorageRequest):
    """Register a storage location."""
    service = get_data_residency_service()
    try:
        location = await service.register_storage_location(
            organization_id=request.organization_id,
            name=request.name,
            region_id=request.region_id,
            storage_type=request.storage_type,
            provider=request.provider,
            provider_identifier=request.provider_identifier,
            data_classifications=request.data_classifications,
            encryption_enabled=request.encryption_enabled,
            encryption_key_id=request.encryption_key_id,
            encryption_algorithm=request.encryption_algorithm,
            description=request.description,
            endpoint=request.endpoint,
            registered_by=request.registered_by,
        )
        return {"location": location.model_dump()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/storage")
async def list_storage_locations(
    organization_id: str | None = None,
    region_id: str | None = None,
    storage_type: str | None = None,
    compliant: bool | None = None,
):
    """List storage locations."""
    service = get_data_residency_service()
    locations = await service.list_storage_locations(
        organization_id=organization_id,
        region_id=region_id,
        storage_type=storage_type,
        compliant=compliant,
    )
    return {"locations": [l.model_dump() for l in locations]}


@router.get("/storage/{location_id}")
async def get_storage_location(location_id: str):
    """Get a storage location."""
    service = get_data_residency_service()
    location = await service.get_storage_location(location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Storage location not found")
    return {"location": location.model_dump()}


# --- Transfer Endpoints ---

@router.post("/transfers")
async def create_transfer_request(request: CreateTransferRequest):
    """Create a data transfer request."""
    service = get_data_residency_service()
    transfer = await service.create_transfer_request(
        organization_id=request.organization_id,
        source_region_id=request.source_region_id,
        destination_region_id=request.destination_region_id,
        data_classification=request.data_classification,
        data_description=request.data_description,
        purpose=request.purpose,
        business_justification=request.business_justification,
        requestor_id=request.requestor_id,
        requestor_username=request.requestor_username,
        source_location_id=request.source_location_id,
        destination_location_id=request.destination_location_id,
        estimated_size_bytes=request.estimated_size_bytes,
        legal_basis=request.legal_basis,
        sccs_reference=request.sccs_reference,
    )
    return {"transfer": transfer.model_dump()}


@router.get("/transfers")
async def list_transfers(
    organization_id: str | None = None,
    status: TransferStatus | None = None,
    requestor_id: str | None = None,
    limit: int = Query(default=100, le=500),
):
    """List transfer requests."""
    service = get_data_residency_service()
    transfers = await service.list_transfer_requests(
        organization_id=organization_id,
        status=status,
        requestor_id=requestor_id,
        limit=limit,
    )
    return {"transfers": [t.model_dump() for t in transfers]}


@router.get("/transfers/{request_id}")
async def get_transfer(request_id: str):
    """Get a transfer request."""
    service = get_data_residency_service()
    transfer = await service.get_transfer_request(request_id)
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer request not found")
    return {"transfer": transfer.model_dump()}


@router.post("/transfers/{request_id}/approve")
async def approve_transfer(request_id: str, request: ApproveTransferRequest):
    """Approve a transfer request."""
    service = get_data_residency_service()
    transfer = await service.approve_transfer(request_id, request.approved_by)
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found or not pending")
    return {"transfer": transfer.model_dump()}


@router.post("/transfers/{request_id}/reject")
async def reject_transfer(request_id: str, request: RejectTransferRequest):
    """Reject a transfer request."""
    service = get_data_residency_service()
    transfer = await service.reject_transfer(
        request_id, request.rejected_by, request.reason
    )
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found or not pending")
    return {"transfer": transfer.model_dump()}


@router.post("/transfers/{request_id}/start")
async def start_transfer(request_id: str, request: StartTransferRequest):
    """Start an approved transfer."""
    service = get_data_residency_service()
    transfer = await service.start_transfer(request_id, request.transfer_method)
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found or not approved")
    return {"transfer": transfer.model_dump()}


@router.post("/transfers/{request_id}/complete")
async def complete_transfer(request_id: str, request: CompleteTransferRequest):
    """Mark a transfer as complete."""
    service = get_data_residency_service()
    transfer = await service.complete_transfer(request_id, request.bytes_transferred)
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found or not in progress")
    return {"transfer": transfer.model_dump()}


# --- Violation Endpoints ---

@router.get("/violations")
async def list_violations(
    organization_id: str | None = None,
    severity: ViolationSeverity | None = None,
    resolved: bool | None = None,
    limit: int = Query(default=100, le=500),
):
    """List residency violations."""
    service = get_data_residency_service()
    violations = await service.list_violations(
        organization_id=organization_id,
        severity=severity,
        resolved=resolved,
        limit=limit,
    )
    return {"violations": [v.model_dump() for v in violations]}


@router.get("/violations/{violation_id}")
async def get_violation(violation_id: str):
    """Get a violation."""
    service = get_data_residency_service()
    violation = await service.get_violation(violation_id)
    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")
    return {"violation": violation.model_dump()}


@router.post("/violations/{violation_id}/resolve")
async def resolve_violation(violation_id: str, request: ResolveViolationRequest):
    """Resolve a violation."""
    service = get_data_residency_service()
    violation = await service.resolve_violation(
        violation_id, request.resolved_by, request.resolution_notes
    )
    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")
    return {"violation": violation.model_dump()}


# --- Compliance Endpoints ---

@router.post("/compliance/check")
async def check_compliance(request: CheckComplianceRequest):
    """Check if a region is compliant for a data classification."""
    service = get_data_residency_service()
    result = await service.check_region_compliance(
        organization_id=request.organization_id,
        region_id=request.region_id,
        data_classification=request.data_classification,
    )
    return {"result": result}


@router.get("/compliance/allowed-regions/{organization_id}")
async def get_allowed_regions(
    organization_id: str,
    data_classification: DataClassification,
):
    """Get allowed regions for a data classification."""
    service = get_data_residency_service()
    regions = await service.get_allowed_regions(organization_id, data_classification)
    return {"regions": [r.model_dump() for r in regions]}


# --- Dashboard Endpoint ---

@router.get("/dashboard/{organization_id}")
async def get_residency_dashboard(organization_id: str):
    """Get residency dashboard data."""
    service = get_data_residency_service()
    dashboard = await service.get_residency_dashboard(organization_id)
    return {"dashboard": dashboard}
