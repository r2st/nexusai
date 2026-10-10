"""Compliance API endpoints for GDPR and SOC 2."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
import structlog

from app.services.compliance.gdpr import get_gdpr_service
from app.api.deps import get_current_user
from app.models.user import User

logger = structlog.get_logger()
from app.services.compliance.soc2 import get_soc2_service
from app.services.compliance.models import (
    ComplianceStatus,
    ConsentType,
    DataCategory,
    DataSubjectRequestStatus,
    DataSubjectRequestType,
    SOC2ControlCategory,
    SOC2ControlStatus,
    SOC2EvidenceType,
)

router = APIRouter(prefix="/compliance", tags=["compliance"])


# --- Request/Response Models ---

class CreateDSRRequest(BaseModel):
    """Request to create a Data Subject Request."""
    user_id: str
    email: str
    request_type: DataSubjectRequestType
    reason: str | None = None


class ProcessDSRRequest(BaseModel):
    """Request to process/complete a DSR."""
    processor_id: str
    response_data: dict[str, Any] | None = None


class RejectDSRRequest(BaseModel):
    """Request to reject a DSR."""
    processor_id: str
    rejection_reason: str


class RecordConsentRequest(BaseModel):
    """Request to record consent."""
    user_id: str
    consent_type: ConsentType
    granted: bool
    purpose: str
    legal_basis: str = "consent"
    version: str = "1.0"
    ip_address: str | None = None
    user_agent: str | None = None
    source: str = "web"


class RevokeConsentRequest(BaseModel):
    """Request to revoke consent."""
    user_id: str
    consent_type: ConsentType


class CreateRetentionPolicyRequest(BaseModel):
    """Request to create a retention policy."""
    name: str
    description: str
    data_category: DataCategory
    retention_period_days: int
    legal_basis: str
    action_on_expiry: str = "delete"
    applies_to_tables: list[str] = Field(default_factory=list)
    applies_to_fields: list[str] = Field(default_factory=list)


class AddDataInventoryRequest(BaseModel):
    """Request to add data inventory item."""
    data_category: DataCategory
    data_fields: list[str]
    storage_location: str
    purpose: str
    legal_basis: str
    encryption: bool = True
    retention_period_days: int | None = None
    third_party_sharing: bool = False
    third_parties: list[str] = Field(default_factory=list)
    cross_border_transfer: bool = False
    transfer_countries: list[str] = Field(default_factory=list)


class UpdateControlStatusRequest(BaseModel):
    """Request to update control status."""
    status: SOC2ControlStatus
    updated_by: str
    implementation_notes: str | None = None


class RecordControlTestRequest(BaseModel):
    """Request to record control test."""
    tester: str
    test_result: str
    test_procedure: str | None = None


class AddEvidenceRequest(BaseModel):
    """Request to add evidence."""
    control_id: str = Field(..., min_length=1, max_length=200)
    evidence_type: SOC2EvidenceType
    title: str = Field(..., min_length=1, max_length=500)
    collected_by: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    file_path: str | None = Field(default=None, max_length=1024)
    content: str | None = Field(default=None, max_length=100000)
    url: str | None = Field(default=None, max_length=2000)
    valid_until: datetime | None = None

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v: str | None) -> str | None:
        if v is not None and (".." in v or v.startswith("/") or "\x00" in v):
            raise ValueError("Invalid file_path: path traversal not allowed")
        return v


class CreateAccessReviewRequest(BaseModel):
    """Request to create access review."""
    review_period: str
    reviewer: str
    systems_reviewed: list[str]


class CompleteAccessReviewRequest(BaseModel):
    """Request to complete access review."""
    total_access_rights: int
    access_removed: int
    access_modified: int
    exceptions_found: int
    exceptions_approved: int
    findings: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class CreateChangeRecordRequest(BaseModel):
    """Request to create change record."""
    title: str
    description: str
    requested_by: str
    change_type: str = "standard"
    risk_level: str = "low"
    category: str = "application"
    test_plan: str | None = None
    rollback_plan: str | None = None


# --- GDPR Endpoints ---

@router.post("/gdpr/dsr", status_code=status.HTTP_201_CREATED)
async def create_dsr(request: CreateDSRRequest, _current_user: User = Depends(get_current_user)):
    """Create a new Data Subject Request."""
    service = get_gdpr_service()
    dsr = await service.create_dsr(
        user_id=request.user_id,
        email=request.email,
        request_type=request.request_type,
        reason=request.reason,
    )
    return {"dsr": dsr.model_dump()}


@router.get("/gdpr/dsr/{dsr_id}")
async def get_dsr(dsr_id: str, _current_user: User = Depends(get_current_user)):
    """Get a Data Subject Request by ID."""
    service = get_gdpr_service()
    dsr = await service.get_dsr(dsr_id)
    if not dsr:
        raise HTTPException(status_code=404, detail="DSR not found")
    return {"dsr": dsr.model_dump()}


@router.get("/gdpr/dsr")
async def list_dsrs(
    user_id: str | None = None,
    status: DataSubjectRequestStatus | None = None,
    request_type: DataSubjectRequestType | None = None,
    _current_user: User = Depends(get_current_user),
):
    """List Data Subject Requests with optional filters."""
    service = get_gdpr_service()
    dsrs = await service.list_dsrs(
        user_id=user_id,
        status=status,
        request_type=request_type,
    )
    return {"dsrs": [d.model_dump() for d in dsrs]}


@router.post("/gdpr/dsr/{dsr_id}/process")
async def process_dsr(dsr_id: str, request: ProcessDSRRequest, _current_user: User = Depends(get_current_user)):
    """Mark a DSR as in progress."""
    service = get_gdpr_service()
    dsr = await service.process_dsr(
        dsr_id=dsr_id,
        processor_id=request.processor_id,
        response_data=request.response_data,
    )
    if not dsr:
        raise HTTPException(status_code=404, detail="DSR not found")
    return {"dsr": dsr.model_dump()}


@router.post("/gdpr/dsr/{dsr_id}/complete")
async def complete_dsr(dsr_id: str, request: ProcessDSRRequest, _current_user: User = Depends(get_current_user)):
    """Complete a Data Subject Request."""
    service = get_gdpr_service()
    dsr = await service.complete_dsr(
        dsr_id=dsr_id,
        processor_id=request.processor_id,
        response_data=request.response_data,
    )
    if not dsr:
        raise HTTPException(status_code=404, detail="DSR not found")
    return {"dsr": dsr.model_dump()}


@router.post("/gdpr/dsr/{dsr_id}/reject")
async def reject_dsr(dsr_id: str, request: RejectDSRRequest, _current_user: User = Depends(get_current_user)):
    """Reject a Data Subject Request."""
    service = get_gdpr_service()
    dsr = await service.reject_dsr(
        dsr_id=dsr_id,
        processor_id=request.processor_id,
        rejection_reason=request.rejection_reason,
    )
    if not dsr:
        raise HTTPException(status_code=404, detail="DSR not found")
    return {"dsr": dsr.model_dump()}


@router.get("/gdpr/dsr/overdue")
async def get_overdue_dsrs(_current_user: User = Depends(get_current_user)):
    """Get overdue Data Subject Requests."""
    service = get_gdpr_service()
    dsrs = await service.get_overdue_dsrs()
    return {"dsrs": [d.model_dump() for d in dsrs]}


@router.post("/gdpr/consent")
async def record_consent(request: RecordConsentRequest, _current_user: User = Depends(get_current_user)):
    """Record a consent decision."""
    service = get_gdpr_service()
    record = await service.record_consent(
        user_id=request.user_id,
        consent_type=request.consent_type,
        granted=request.granted,
        purpose=request.purpose,
        legal_basis=request.legal_basis,
        version=request.version,
        ip_address=request.ip_address,
        user_agent=request.user_agent,
        source=request.source,
    )
    return {"consent": record.model_dump()}


@router.post("/gdpr/consent/revoke")
async def revoke_consent(request: RevokeConsentRequest, _current_user: User = Depends(get_current_user)):
    """Revoke consent."""
    service = get_gdpr_service()
    record = await service.revoke_consent(
        user_id=request.user_id,
        consent_type=request.consent_type,
    )
    if not record:
        raise HTTPException(status_code=404, detail="Active consent not found")
    return {"consent": record.model_dump()}


@router.get("/gdpr/consent/{user_id}")
async def get_user_consents(
    user_id: str,
    _current_user: User = Depends(get_current_user),
    active_only: bool = Query(default=True),
):
    """Get consent records for a user."""
    service = get_gdpr_service()
    records = await service.get_user_consents(user_id, active_only)
    return {"consents": [r.model_dump() for r in records]}


@router.get("/gdpr/consent/{user_id}/check/{consent_type}")
async def check_consent(user_id: str, consent_type: ConsentType, _current_user: User = Depends(get_current_user)):
    """Check if user has active consent for a type."""
    service = get_gdpr_service()
    has_consent = await service.check_consent(user_id, consent_type)
    return {"has_consent": has_consent}


@router.post("/gdpr/retention-policy", status_code=status.HTTP_201_CREATED)
async def create_retention_policy(request: CreateRetentionPolicyRequest, _current_user: User = Depends(get_current_user)):
    """Create a data retention policy."""
    service = get_gdpr_service()
    policy = await service.create_retention_policy(
        name=request.name,
        description=request.description,
        data_category=request.data_category,
        retention_period_days=request.retention_period_days,
        legal_basis=request.legal_basis,
        action_on_expiry=request.action_on_expiry,
        applies_to_tables=request.applies_to_tables,
        applies_to_fields=request.applies_to_fields,
    )
    return {"policy": policy.model_dump()}


@router.get("/gdpr/retention-policy")
async def list_retention_policies(enabled_only: bool = Query(default=True), _current_user: User = Depends(get_current_user)):
    """List data retention policies."""
    service = get_gdpr_service()
    policies = await service.list_retention_policies(enabled_only)
    return {"policies": [p.model_dump() for p in policies]}


@router.post("/gdpr/retention-policy/{policy_id}/execute")
async def execute_retention_policy(policy_id: str, _current_user: User = Depends(get_current_user)):
    """Execute a data retention policy."""
    service = get_gdpr_service()
    result = await service.execute_retention_policy(policy_id)
    return result


@router.post("/gdpr/data-inventory", status_code=status.HTTP_201_CREATED)
async def add_data_inventory(request: AddDataInventoryRequest, _current_user: User = Depends(get_current_user)):
    """Add an item to the personal data inventory."""
    service = get_gdpr_service()
    item = await service.add_data_inventory_item(
        data_category=request.data_category,
        data_fields=request.data_fields,
        storage_location=request.storage_location,
        purpose=request.purpose,
        legal_basis=request.legal_basis,
        encryption=request.encryption,
        retention_period_days=request.retention_period_days,
        third_party_sharing=request.third_party_sharing,
        third_parties=request.third_parties,
        cross_border_transfer=request.cross_border_transfer,
        transfer_countries=request.transfer_countries,
    )
    return {"item": item.model_dump()}


@router.get("/gdpr/data-inventory")
async def get_data_inventory(category: DataCategory | None = None, _current_user: User = Depends(get_current_user)):
    """Get the personal data inventory."""
    service = get_gdpr_service()
    items = await service.get_data_inventory(category)
    return {"items": [i.model_dump() for i in items]}


@router.get("/gdpr/report")
async def get_gdpr_compliance_report(_current_user: User = Depends(get_current_user)):
    """Generate GDPR compliance report."""
    service = get_gdpr_service()
    report = await service.generate_compliance_report()
    return {"report": report.model_dump()}


@router.get("/gdpr/audit-log")
async def get_gdpr_audit_log(
    resource_type: str | None = None,
    resource_id: str | None = None,
    actor: str | None = None,
    _current_user: User = Depends(get_current_user),
    limit: int = Query(default=100, le=500),
):
    """Get GDPR audit log entries."""
    service = get_gdpr_service()
    entries = await service.get_audit_log(
        resource_type=resource_type,
        resource_id=resource_id,
        actor=actor,
        limit=limit,
    )
    return {"entries": [e.model_dump() for e in entries]}


# --- SOC 2 Endpoints ---

@router.get("/soc2/controls")
async def list_controls(
    category: SOC2ControlCategory | None = None,
    status: SOC2ControlStatus | None = None,
    _current_user: User = Depends(get_current_user),
):
    """List SOC 2 controls."""
    service = get_soc2_service()
    controls = await service.list_controls(category, status)
    return {"controls": [c.model_dump() for c in controls]}


@router.get("/soc2/controls/{control_id}")
async def get_control(control_id: str, _current_user: User = Depends(get_current_user)):
    """Get a SOC 2 control by ID."""
    service = get_soc2_service()
    control = await service.get_control(control_id)
    if not control:
        raise HTTPException(status_code=404, detail="Control not found")
    return {"control": control.model_dump()}


@router.put("/soc2/controls/{control_id}/status")
async def update_control_status(control_id: str, request: UpdateControlStatusRequest, _current_user: User = Depends(get_current_user)):
    """Update a control's status."""
    service = get_soc2_service()
    control = await service.update_control_status(
        control_id=control_id,
        status=request.status,
        updated_by=request.updated_by,
        implementation_notes=request.implementation_notes,
    )
    if not control:
        raise HTTPException(status_code=404, detail="Control not found")
    return {"control": control.model_dump()}


@router.post("/soc2/controls/{control_id}/test")
async def record_control_test(control_id: str, request: RecordControlTestRequest, _current_user: User = Depends(get_current_user)):
    """Record a control test result."""
    service = get_soc2_service()
    control = await service.record_control_test(
        control_id=control_id,
        tester=request.tester,
        test_result=request.test_result,
        test_procedure=request.test_procedure,
    )
    if not control:
        raise HTTPException(status_code=404, detail="Control not found")
    return {"control": control.model_dump()}


@router.post("/soc2/evidence", status_code=status.HTTP_201_CREATED)
async def add_evidence(request: AddEvidenceRequest, _current_user: User = Depends(get_current_user)):
    """Add evidence for a control."""
    service = get_soc2_service()
    evidence = await service.add_evidence(
        control_id=request.control_id,
        evidence_type=request.evidence_type,
        title=request.title,
        collected_by=request.collected_by,
        description=request.description,
        file_path=request.file_path,
        content=request.content,
        url=request.url,
        valid_until=request.valid_until,
    )
    return {"evidence": evidence.model_dump()}


@router.get("/soc2/evidence/{control_id}")
async def get_evidence(control_id: str, valid_only: bool = Query(default=True), _current_user: User = Depends(get_current_user)):
    """Get evidence for a control."""
    service = get_soc2_service()
    evidence = await service.get_evidence(control_id, valid_only)
    return {"evidence": [e.model_dump() for e in evidence]}


@router.post("/soc2/evidence/{evidence_id}/verify")
async def verify_evidence(evidence_id: str, verifier: str, _current_user: User = Depends(get_current_user)):
    """Verify evidence."""
    service = get_soc2_service()
    evidence = await service.verify_evidence(evidence_id, verifier)
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return {"evidence": evidence.model_dump()}


@router.post("/soc2/access-review", status_code=status.HTTP_201_CREATED)
async def create_access_review(request: CreateAccessReviewRequest, _current_user: User = Depends(get_current_user)):
    """Create a new access review."""
    service = get_soc2_service()
    review = await service.create_access_review(
        review_period=request.review_period,
        reviewer=request.reviewer,
        systems_reviewed=request.systems_reviewed,
    )
    return {"review": review.model_dump()}


@router.post("/soc2/access-review/{review_id}/complete")
async def complete_access_review(review_id: str, request: CompleteAccessReviewRequest, _current_user: User = Depends(get_current_user)):
    """Complete an access review."""
    service = get_soc2_service()
    review = await service.complete_access_review(
        review_id=review_id,
        total_access_rights=request.total_access_rights,
        access_removed=request.access_removed,
        access_modified=request.access_modified,
        exceptions_found=request.exceptions_found,
        exceptions_approved=request.exceptions_approved,
        findings=request.findings,
        recommendations=request.recommendations,
    )
    if not review:
        raise HTTPException(status_code=404, detail="Access review not found")
    return {"review": review.model_dump()}


@router.post("/soc2/access-review/{review_id}/approve")
async def approve_access_review(review_id: str, approver: str, _current_user: User = Depends(get_current_user)):
    """Approve an access review."""
    service = get_soc2_service()
    review = await service.approve_access_review(review_id, approver)
    if not review:
        raise HTTPException(status_code=404, detail="Access review not found or not completed")
    return {"review": review.model_dump()}


@router.get("/soc2/access-review")
async def list_access_reviews(status: str | None = None, _current_user: User = Depends(get_current_user)):
    """List access reviews."""
    service = get_soc2_service()
    reviews = await service.list_access_reviews(status)
    return {"reviews": [r.model_dump() for r in reviews]}


@router.post("/soc2/change", status_code=status.HTTP_201_CREATED)
async def create_change_record(request: CreateChangeRecordRequest, _current_user: User = Depends(get_current_user)):
    """Create a change management record."""
    service = get_soc2_service()
    change = await service.create_change_record(
        title=request.title,
        description=request.description,
        requested_by=request.requested_by,
        change_type=request.change_type,
        risk_level=request.risk_level,
        category=request.category,
        test_plan=request.test_plan,
        rollback_plan=request.rollback_plan,
    )
    return {"change": change.model_dump()}


@router.post("/soc2/change/{change_id}/approve")
async def approve_change(change_id: str, approver: str, _current_user: User = Depends(get_current_user)):
    """Approve a change request."""
    service = get_soc2_service()
    change = await service.approve_change(change_id, approver)
    if not change:
        raise HTTPException(status_code=404, detail="Change record not found")
    return {"change": change.model_dump()}


@router.post("/soc2/change/{change_id}/implement")
async def implement_change(
    change_id: str,
    implementer: str,
    test_results: str | None = None,
    _current_user: User = Depends(get_current_user),
):
    """Record change implementation."""
    service = get_soc2_service()
    change = await service.implement_change(
        change_id=change_id,
        implementer=implementer,
        test_results=test_results,
    )
    if not change:
        raise HTTPException(status_code=404, detail="Change not found or not approved")
    return {"change": change.model_dump()}


@router.get("/soc2/change")
async def list_changes(
    status: str | None = None,
    change_type: str | None = None,
    _current_user: User = Depends(get_current_user),
):
    """List change records."""
    service = get_soc2_service()
    changes = await service.list_changes(status, change_type)
    return {"changes": [c.model_dump() for c in changes]}


@router.get("/soc2/report")
async def get_soc2_compliance_report(
    _current_user: User = Depends(get_current_user),
    report_period: str = Query(default="Q1 2024"),
):
    """Generate SOC 2 compliance report."""
    service = get_soc2_service()
    report = await service.generate_compliance_report(report_period)
    return {"report": report.model_dump()}


@router.get("/soc2/audit-log")
async def get_soc2_audit_log(
    resource_type: str | None = None,
    _current_user: User = Depends(get_current_user),
    limit: int = Query(default=100, le=500),
):
    """Get SOC 2 audit log entries."""
    service = get_soc2_service()
    entries = await service.get_audit_log(resource_type, limit)
    return {"entries": [e.model_dump() for e in entries]}


# --- Combined Dashboard Endpoint ---

@router.get("/dashboard")
async def get_compliance_dashboard(_current_user: User = Depends(get_current_user)):
    """Get combined compliance dashboard data."""
    gdpr_service = get_gdpr_service()
    soc2_service = get_soc2_service()

    gdpr_report = await gdpr_service.generate_compliance_report()
    soc2_report = await soc2_service.generate_compliance_report("Current Period")

    return {
        "gdpr": {
            "status": gdpr_report.status.value,
            "dsr_pending": gdpr_report.pending_dsr_requests,
            "dsr_overdue": gdpr_report.overdue_dsr_requests,
            "consent_rate": gdpr_report.consent_rate,
            "issues_count": len(gdpr_report.compliance_issues),
        },
        "soc2": {
            "status": soc2_report.status.value,
            "implementation_rate": soc2_report.implementation_rate,
            "controls_implemented": soc2_report.implemented_controls,
            "controls_total": soc2_report.total_controls,
            "open_findings": soc2_report.open_findings,
        },
        "overall_status": _calculate_overall_status(gdpr_report.status, soc2_report.status),
    }


def _calculate_overall_status(
    gdpr_status: ComplianceStatus,
    soc2_status: ComplianceStatus,
) -> str:
    """Calculate overall compliance status."""
    if gdpr_status == ComplianceStatus.NON_COMPLIANT or soc2_status == ComplianceStatus.NON_COMPLIANT:
        return "non_compliant"
    if gdpr_status == ComplianceStatus.PARTIAL or soc2_status == ComplianceStatus.PARTIAL:
        return "partial"
    if gdpr_status == ComplianceStatus.COMPLIANT and soc2_status == ComplianceStatus.COMPLIANT:
        return "compliant"
    return "pending_review"
