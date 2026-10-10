"""HIPAA Compliance API endpoints."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
import structlog

from app.services.compliance.hipaa import (
    get_hipaa_service,
    get_baa_manager,
    get_phi_detector,
    get_encryption_auditor,
    PHICategory,
    BAAType,
    BAAStatus,
    HIPAAControlCategory,
    HIPAAControlStatus,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/hipaa", tags=["hipaa"])


# --- Request/Response Models ---

class DetectPHIRequest(BaseModel):
    """Request to detect PHI in content."""
    content: str
    categories: list[PHICategory] | None = None
    min_confidence: float = 0.7


class DetectPHIInCodeRequest(BaseModel):
    """Request to detect PHI in source code."""
    code: str
    language: str | None = None


class CreateBAARequest(BaseModel):
    """Request to create a BAA."""
    organization_id: str
    covered_entity: str
    business_associate: str
    baa_type: BAAType = BAAType.FULL_BAA
    ba_contact_name: str | None = None
    ba_contact_email: str | None = None
    phi_categories_shared: list[PHICategory] = Field(default_factory=list)
    permitted_uses: list[str] = Field(default_factory=list)
    permitted_disclosures: list[str] = Field(default_factory=list)
    encryption_required: bool = True
    breach_notification_hours: int = 24
    created_by: str | None = None


class ActivateBAARequest(BaseModel):
    """Request to activate a BAA."""
    activated_by: str
    effective_date: datetime | None = None
    expiration_date: datetime | None = None
    signed_document_path: str | None = None


class RenewBAARequest(BaseModel):
    """Request to renew a BAA."""
    renewed_by: str
    new_expiration_date: datetime
    new_version: str | None = None


class TerminateBAARequest(BaseModel):
    """Request to terminate a BAA."""
    terminated_by: str
    reason: str | None = None


class UpdateControlStatusRequest(BaseModel):
    """Request to update control status."""
    status: HIPAAControlStatus
    updated_by: str
    implementation_notes: str | None = None


class RegisterStorageRequest(BaseModel):
    """Request to register storage for encryption audit."""
    location_id: str
    storage_type: str
    algorithm: str
    encryption_enabled: bool = True


class RegisterEndpointRequest(BaseModel):
    """Request to register endpoint for encryption audit."""
    endpoint_id: str
    protocol: str
    tls_version: str
    cipher_suite: str


class CreatePolicyRequest(BaseModel):
    """Request to create minimum necessary policy."""
    name: str
    description: str
    applies_to_roles: list[str]
    applies_to_phi_categories: list[PHICategory]
    permitted_actions: list[str]
    requires_justification: bool = True
    max_records_per_query: int | None = None
    created_by: str | None = None


class RequestAccessRequest(BaseModel):
    """Request for access justification."""
    user_id: str
    policy_id: str
    phi_categories_requested: list[PHICategory]
    purpose: str
    patient_id: str | None = None


class ApproveAccessRequest(BaseModel):
    """Request to approve access justification."""
    approved_by: str
    valid_hours: int = 24
    max_access_count: int | None = None


class DenyAccessRequest(BaseModel):
    """Request to deny access justification."""
    denied_by: str
    reason: str


# --- PHI Detection Endpoints ---

@router.post("/phi/detect")
async def detect_phi(request: DetectPHIRequest):
    """Detect PHI in content."""
    detector = get_phi_detector()
    result = await detector.detect(
        content=request.content,
        categories=request.categories,
        min_confidence=request.min_confidence,
    )
    return {"result": result.model_dump()}


@router.post("/phi/detect-in-code")
async def detect_phi_in_code(request: DetectPHIInCodeRequest):
    """Detect PHI in source code."""
    detector = get_phi_detector()
    result = await detector.detect_in_code(
        code=request.code,
        language=request.language,
    )
    return {"result": result.model_dump()}


@router.get("/phi/patterns")
async def get_phi_patterns(category: PHICategory | None = None):
    """Get configured PHI detection patterns."""
    detector = get_phi_detector()
    patterns = detector.get_patterns(category)
    return {"patterns": [p.model_dump() for p in patterns]}


# --- BAA Management Endpoints ---

@router.post("/baa")
async def create_baa(request: CreateBAARequest):
    """Create a new Business Associate Agreement."""
    manager = get_baa_manager()
    baa = await manager.create_baa(
        organization_id=request.organization_id,
        covered_entity=request.covered_entity,
        business_associate=request.business_associate,
        baa_type=request.baa_type,
        ba_contact_name=request.ba_contact_name,
        ba_contact_email=request.ba_contact_email,
        phi_categories_shared=request.phi_categories_shared,
        permitted_uses=request.permitted_uses,
        permitted_disclosures=request.permitted_disclosures,
        encryption_required=request.encryption_required,
        breach_notification_hours=request.breach_notification_hours,
        created_by=request.created_by,
    )
    return {"baa": baa.model_dump()}


@router.get("/baa")
async def list_baas(
    organization_id: str | None = None,
    status: BAAStatus | None = None,
    baa_type: BAAType | None = None,
    expiring_within_days: int | None = None,
):
    """List Business Associate Agreements."""
    manager = get_baa_manager()
    baas = await manager.list_baas(
        organization_id=organization_id,
        status=status,
        baa_type=baa_type,
        expiring_within_days=expiring_within_days,
    )
    return {"baas": [b.model_dump() for b in baas]}


@router.get("/baa/{baa_id}")
async def get_baa(baa_id: str):
    """Get a BAA by ID."""
    manager = get_baa_manager()
    baa = await manager.get_baa(baa_id)
    if not baa:
        raise HTTPException(status_code=404, detail="BAA not found")
    return {"baa": baa.model_dump()}


@router.post("/baa/{baa_id}/submit-for-review")
async def submit_baa_for_review(baa_id: str, submitted_by: str):
    """Submit BAA for review."""
    manager = get_baa_manager()
    baa = await manager.submit_for_review(baa_id, submitted_by)
    if not baa:
        raise HTTPException(status_code=404, detail="BAA not found or not in draft status")
    return {"baa": baa.model_dump()}


@router.post("/baa/{baa_id}/approve")
async def approve_baa(baa_id: str, approved_by: str):
    """Approve a BAA."""
    manager = get_baa_manager()
    baa = await manager.approve_baa(baa_id, approved_by)
    if not baa:
        raise HTTPException(status_code=404, detail="BAA not found or not pending review")
    return {"baa": baa.model_dump()}


@router.post("/baa/{baa_id}/activate")
async def activate_baa(baa_id: str, request: ActivateBAARequest):
    """Activate a signed BAA."""
    manager = get_baa_manager()
    baa = await manager.activate_baa(
        baa_id=baa_id,
        activated_by=request.activated_by,
        effective_date=request.effective_date,
        expiration_date=request.expiration_date,
        signed_document_path=request.signed_document_path,
    )
    if not baa:
        raise HTTPException(status_code=404, detail="BAA not found or not pending signature")
    return {"baa": baa.model_dump()}


@router.post("/baa/{baa_id}/renew")
async def renew_baa(baa_id: str, request: RenewBAARequest):
    """Renew a BAA."""
    manager = get_baa_manager()
    baa = await manager.renew_baa(
        baa_id=baa_id,
        renewed_by=request.renewed_by,
        new_expiration_date=request.new_expiration_date,
        new_version=request.new_version,
    )
    if not baa:
        raise HTTPException(status_code=404, detail="BAA not found or not active")
    return {"baa": baa.model_dump()}


@router.post("/baa/{baa_id}/terminate")
async def terminate_baa(baa_id: str, request: TerminateBAARequest):
    """Terminate a BAA."""
    manager = get_baa_manager()
    baa = await manager.terminate_baa(
        baa_id=baa_id,
        terminated_by=request.terminated_by,
        reason=request.reason,
    )
    if not baa:
        raise HTTPException(status_code=404, detail="BAA not found")
    return {"baa": baa.model_dump()}


@router.get("/baa/summary/{organization_id}")
async def get_baa_summary(organization_id: str):
    """Get BAA summary for organization."""
    manager = get_baa_manager()
    summary = await manager.get_baa_summary(organization_id)
    return {"summary": summary}


# --- Encryption Audit Endpoints ---

@router.post("/encryption/audit")
async def run_encryption_audit(auditor: str | None = None):
    """Run encryption compliance audit."""
    auditor_service = get_encryption_auditor()
    result = await auditor_service.audit_encryption(auditor)
    return {"result": result.model_dump()}


@router.get("/encryption/audit/{audit_id}")
async def get_encryption_audit(audit_id: str):
    """Get encryption audit result."""
    auditor = get_encryption_auditor()
    result = await auditor.get_audit_result(audit_id)
    if not result:
        raise HTTPException(status_code=404, detail="Audit not found")
    return {"result": result.model_dump()}


@router.get("/encryption/audits")
async def list_encryption_audits(limit: int = Query(default=100, le=500)):
    """List encryption audit results."""
    auditor = get_encryption_auditor()
    results = await auditor.list_audits(limit)
    return {"audits": [r.model_dump() for r in results]}


@router.post("/encryption/register-storage")
async def register_storage_location(request: RegisterStorageRequest):
    """Register a storage location for encryption audit."""
    auditor = get_encryption_auditor()
    await auditor.register_storage_location(
        location_id=request.location_id,
        storage_type=request.storage_type,
        algorithm=request.algorithm,
        encryption_enabled=request.encryption_enabled,
    )
    return {"registered": True, "location_id": request.location_id}


@router.post("/encryption/register-endpoint")
async def register_endpoint(request: RegisterEndpointRequest):
    """Register an endpoint for encryption audit."""
    auditor = get_encryption_auditor()
    await auditor.register_endpoint(
        endpoint_id=request.endpoint_id,
        protocol=request.protocol,
        tls_version=request.tls_version,
        cipher_suite=request.cipher_suite,
    )
    return {"registered": True, "endpoint_id": request.endpoint_id}


@router.get("/encryption/algorithms")
async def get_encryption_algorithms():
    """Get approved and weak encryption algorithms."""
    auditor = get_encryption_auditor()
    return {
        "approved": auditor.get_approved_algorithms(),
        "weak": auditor.get_weak_algorithms(),
    }


# --- Control Management Endpoints ---

@router.get("/controls")
async def list_controls(
    category: HIPAAControlCategory | None = None,
    status: HIPAAControlStatus | None = None,
    required_only: bool = False,
):
    """List HIPAA controls."""
    service = get_hipaa_service()
    controls = await service.list_controls(category, status, required_only)
    return {"controls": [c.model_dump() for c in controls]}


@router.get("/controls/{control_id}")
async def get_control(control_id: str):
    """Get a HIPAA control."""
    service = get_hipaa_service()
    control = await service.get_control(control_id)
    if not control:
        raise HTTPException(status_code=404, detail="Control not found")
    return {"control": control.model_dump()}


@router.put("/controls/{control_id}/status")
async def update_control_status(control_id: str, request: UpdateControlStatusRequest):
    """Update a control's status."""
    service = get_hipaa_service()
    control = await service.update_control_status(
        control_id=control_id,
        status=request.status,
        updated_by=request.updated_by,
        implementation_notes=request.implementation_notes,
    )
    if not control:
        raise HTTPException(status_code=404, detail="Control not found")
    return {"control": control.model_dump()}


@router.post("/controls/{control_id}/evidence")
async def add_control_evidence(control_id: str, evidence_id: str, added_by: str):
    """Add evidence to a control."""
    service = get_hipaa_service()
    control = await service.add_control_evidence(control_id, evidence_id, added_by)
    if not control:
        raise HTTPException(status_code=404, detail="Control not found")
    return {"control": control.model_dump()}


# --- Minimum Necessary Policy Endpoints ---

@router.post("/policies/minimum-necessary")
async def create_minimum_necessary_policy(request: CreatePolicyRequest):
    """Create a minimum necessary access policy."""
    service = get_hipaa_service()
    policy = await service.create_minimum_necessary_policy(
        name=request.name,
        description=request.description,
        applies_to_roles=request.applies_to_roles,
        applies_to_phi_categories=request.applies_to_phi_categories,
        permitted_actions=request.permitted_actions,
        requires_justification=request.requires_justification,
        max_records_per_query=request.max_records_per_query,
        created_by=request.created_by,
    )
    return {"policy": policy.model_dump()}


@router.get("/policies/minimum-necessary")
async def list_minimum_necessary_policies(enabled_only: bool = True):
    """List minimum necessary policies."""
    service = get_hipaa_service()
    policies = await service.list_minimum_necessary_policies(enabled_only)
    return {"policies": [p.model_dump() for p in policies]}


@router.post("/access/request")
async def request_access(request: RequestAccessRequest):
    """Request access with justification."""
    service = get_hipaa_service()
    justification = await service.request_access_justification(
        user_id=request.user_id,
        policy_id=request.policy_id,
        phi_categories_requested=request.phi_categories_requested,
        purpose=request.purpose,
        patient_id=request.patient_id,
    )
    return {"justification": justification.model_dump()}


@router.post("/access/{justification_id}/approve")
async def approve_access(justification_id: str, request: ApproveAccessRequest):
    """Approve access justification."""
    service = get_hipaa_service()
    justification = await service.approve_access_justification(
        justification_id=justification_id,
        approved_by=request.approved_by,
        valid_hours=request.valid_hours,
        max_access_count=request.max_access_count,
    )
    if not justification:
        raise HTTPException(status_code=404, detail="Justification not found")
    return {"justification": justification.model_dump()}


@router.post("/access/{justification_id}/deny")
async def deny_access(justification_id: str, request: DenyAccessRequest):
    """Deny access justification."""
    service = get_hipaa_service()
    justification = await service.deny_access_justification(
        justification_id=justification_id,
        denied_by=request.denied_by,
        reason=request.reason,
    )
    if not justification:
        raise HTTPException(status_code=404, detail="Justification not found")
    return {"justification": justification.model_dump()}


# --- Compliance Report Endpoints ---

@router.get("/report")
async def get_hipaa_compliance_report(
    report_period: str = Query(default="Q1 2024"),
    organization_id: str | None = None,
):
    """Generate HIPAA compliance report."""
    service = get_hipaa_service()
    report = await service.generate_compliance_report(report_period, organization_id)
    return {"report": report.model_dump()}


@router.get("/audit-log")
async def get_hipaa_audit_log(
    resource_type: str | None = None,
    limit: int = Query(default=100, le=500),
):
    """Get HIPAA audit log entries."""
    service = get_hipaa_service()
    entries = await service.get_audit_log(resource_type, limit)
    return {"entries": entries}
