"""Security Scanner API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
import structlog

from app.api.deps import get_current_user
from app.models.user import User
from app.services.security.scanner import (
    SecurityScannerService,
    get_security_scanner_service,
)
from app.services.security.secrets import (
    SecretRotationService,
    get_secret_rotation_service,
    SecretType,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/security", tags=["security"])


# Request/Response Models
class ScanProjectRequest(BaseModel):
    """Request to scan a project."""

    project_path: str = Field(..., min_length=1, max_length=1024, description="Path to project root")
    scan_dependencies: bool = Field(True, description="Scan dependencies")
    scan_code: bool = Field(True, description="Scan source code")
    scan_config: bool = Field(True, description="Check configuration")
    file_extensions: list[str] | None = Field(None, max_length=50, description="Extensions to scan")

    @field_validator("project_path")
    @classmethod
    def validate_project_path(cls, v: str) -> str:
        if ".." in v or "\x00" in v:
            raise ValueError("Invalid project_path: path traversal not allowed")
        return v


class ScanDiffRequest(BaseModel):
    """Request to scan a diff."""

    diff_content: str = Field(..., min_length=1, max_length=5000000, description="Unified diff content")
    base_path: str = Field("", max_length=1024, description="Base path for files")

    @field_validator("base_path")
    @classmethod
    def validate_base_path(cls, v: str) -> str:
        if ".." in v or "\x00" in v:
            raise ValueError("Invalid base_path: path traversal not allowed")
        return v


class ScanResponse(BaseModel):
    """Security scan response."""

    scan_id: str
    passed: bool
    risk_score: float
    total_issues: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    failure_reasons: list[str]


class VulnerabilityResponse(BaseModel):
    """Vulnerability scan response."""

    scan_type: str
    packages_scanned: int
    vulnerabilities_count: int
    critical_count: int
    high_count: int
    has_critical: bool
    error: str | None


class CodeIssueResponse(BaseModel):
    """Code security issue."""

    id: str
    category: str
    severity: str
    file: str
    line: int
    message: str
    recommendation: str
    cwe_id: str | None


class ConfigIssueResponse(BaseModel):
    """Configuration issue."""

    id: str
    category: str
    severity: str
    file: str
    setting: str
    message: str
    recommendation: str


class SecretRegisterRequest(BaseModel):
    """Request to register a secret for rotation."""

    name: str = Field(..., description="Secret name")
    initial_value: str | None = Field(None, description="Initial value")
    secret_type: str = Field("custom", description="Type of secret")
    rotation_days: int = Field(90, ge=1, le=365, description="Rotation interval")
    notify_emails: list[str] = Field(default_factory=list)


class SecretResponse(BaseModel):
    """Secret metadata response."""

    name: str
    secret_type: str
    rotation_count: int
    last_rotated: str | None
    next_rotation: str | None
    is_active: bool


class RotationResponse(BaseModel):
    """Secret rotation response."""

    secret_name: str
    success: bool
    old_version: int
    new_version: int
    error: str | None


# Dependencies
async def get_scanner_service() -> SecurityScannerService:
    """Get security scanner service."""
    return get_security_scanner_service()


async def get_rotation_service() -> SecretRotationService:
    """Get secret rotation service."""
    return get_secret_rotation_service()


# Scanner Endpoints
@router.post("/scan/project", response_model=ScanResponse)
async def scan_project(
    request: ScanProjectRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SecurityScannerService, Depends(get_scanner_service)],
) -> ScanResponse:
    """Scan a project for security issues.

    Performs comprehensive security scanning including:
    - Dependency vulnerability scanning
    - Source code security analysis
    - Configuration security checking
    """
    try:
        report = service.scan_project(
            project_path=request.project_path,
            scan_dependencies=request.scan_dependencies,
            scan_code=request.scan_code,
            scan_config=request.scan_config,
            file_extensions=request.file_extensions,
        )

        return ScanResponse(
            scan_id=report.scan_id,
            passed=report.passed,
            risk_score=report.risk_score,
            total_issues=report.total_issues,
            critical_count=report.critical_count,
            high_count=report.high_count,
            medium_count=report.medium_count,
            low_count=report.low_count,
            failure_reasons=report.failure_reasons,
        )

    except Exception as e:
        logger.error("Failed to scan project", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Security scan failed. Please try again later.",
        )


@router.post("/scan/diff", response_model=ScanResponse)
async def scan_diff(
    request: ScanDiffRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SecurityScannerService, Depends(get_scanner_service)],
) -> ScanResponse:
    """Scan a diff for security issues.

    Analyzes only changed code for security vulnerabilities.
    Useful for PR/MR security checks.
    """
    try:
        report = service.scan_diff(
            diff_content=request.diff_content,
            base_path=request.base_path,
        )

        return ScanResponse(
            scan_id=report.scan_id,
            passed=report.passed,
            risk_score=report.risk_score,
            total_issues=report.total_issues,
            critical_count=report.critical_count,
            high_count=report.high_count,
            medium_count=report.medium_count,
            low_count=report.low_count,
            failure_reasons=report.failure_reasons,
        )

    except Exception as e:
        logger.error("Failed to scan diff", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Security scan failed. Please try again later.",
        )


@router.post("/scan/dependencies", response_model=VulnerabilityResponse)
async def scan_dependencies(
    project_path: str,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SecurityScannerService, Depends(get_scanner_service)],
) -> VulnerabilityResponse:
    """Scan project dependencies for vulnerabilities."""
    try:
        result = service.scan_dependencies_only(project_path)

        return VulnerabilityResponse(
            scan_type=result.scan_type,
            packages_scanned=result.packages_scanned,
            vulnerabilities_count=len(result.vulnerabilities),
            critical_count=result.critical_count,
            high_count=result.high_count,
            has_critical=result.has_critical,
            error=result.error,
        )

    except Exception as e:
        logger.error("Failed to scan dependencies", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Dependency scan failed. Please try again later.",
        )


@router.post("/scan/code", response_model=list[CodeIssueResponse])
async def scan_code(
    project_path: str,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SecurityScannerService, Depends(get_scanner_service)],
    extensions: list[str] | None = None,
) -> list[CodeIssueResponse]:
    """Scan source code for security issues."""
    try:
        issues = service.scan_code_only(project_path, extensions)

        return [
            CodeIssueResponse(
                id=i.id,
                category=i.category.value,
                severity=i.severity,
                file=i.file,
                line=i.line,
                message=i.message,
                recommendation=i.recommendation,
                cwe_id=i.cwe_id,
            )
            for i in issues
        ]

    except Exception as e:
        logger.error("Failed to scan code", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Code scan failed. Please try again later.",
        )


@router.post("/scan/config", response_model=list[ConfigIssueResponse])
async def scan_config(
    project_path: str,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SecurityScannerService, Depends(get_scanner_service)],
) -> list[ConfigIssueResponse]:
    """Check configuration files for security issues."""
    try:
        issues = service.scan_config_only(project_path)

        return [
            ConfigIssueResponse(
                id=i.id,
                category=i.category,
                severity=i.severity,
                file=i.file,
                setting=i.setting,
                message=i.message,
                recommendation=i.recommendation,
            )
            for i in issues
        ]

    except Exception as e:
        logger.error("Failed to scan config", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Configuration scan failed. Please try again later.",
        )


# Secret Rotation Endpoints
@router.post("/secrets/register", response_model=SecretResponse, status_code=status.HTTP_201_CREATED)
async def register_secret(
    request: SecretRegisterRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SecretRotationService, Depends(get_rotation_service)],
) -> SecretResponse:
    """Register a secret for rotation management."""
    try:
        # Map string to enum
        secret_type = SecretType(request.secret_type)

        metadata = service.register_secret(
            name=request.name,
            initial_value=request.initial_value,
            secret_type=secret_type,
            notify_emails=request.notify_emails,
        )

        return SecretResponse(
            name=metadata.name,
            secret_type=metadata.secret_type.value,
            rotation_count=metadata.rotation_count,
            last_rotated=metadata.last_rotated.isoformat() if metadata.last_rotated else None,
            next_rotation=metadata.next_rotation.isoformat() if metadata.next_rotation else None,
            is_active=metadata.is_active,
        )

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid secret type. Supported types: api_key, database, oauth, certificate, custom.",
        )
    except Exception as e:
        logger.error("Failed to register secret", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register secret. Please try again later.",
        )


@router.post("/secrets/{name}/rotate", response_model=RotationResponse)
async def rotate_secret(
    name: str,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SecretRotationService, Depends(get_rotation_service)],
    new_value: str | None = None,
) -> RotationResponse:
    """Rotate a secret to a new value."""
    try:
        result = await service.rotate_secret(name, new_value)

        return RotationResponse(
            secret_name=result.secret_name,
            success=result.success,
            old_version=result.old_version,
            new_version=result.new_version,
            error=result.error,
        )

    except Exception as e:
        logger.error("Failed to rotate secret", secret_name=name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to rotate secret. Please try again later.",
        )


@router.get("/secrets", response_model=list[SecretResponse])
async def list_secrets(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SecretRotationService, Depends(get_rotation_service)],
    include_inactive: bool = False,
) -> list[SecretResponse]:
    """List all managed secrets."""
    secrets = service.list_secrets(include_inactive=include_inactive)

    return [
        SecretResponse(
            name=s.name,
            secret_type=s.secret_type.value,
            rotation_count=s.rotation_count,
            last_rotated=s.last_rotated.isoformat() if s.last_rotated else None,
            next_rotation=s.next_rotation.isoformat() if s.next_rotation else None,
            is_active=s.is_active,
        )
        for s in secrets
    ]


@router.get("/secrets/expiring", response_model=list[SecretResponse])
async def get_expiring_secrets(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SecretRotationService, Depends(get_rotation_service)],
) -> list[SecretResponse]:
    """Get secrets that are expiring soon."""
    expiring = await service.check_expiring_secrets()

    return [
        SecretResponse(
            name=s.name,
            secret_type=s.secret_type.value,
            rotation_count=s.rotation_count,
            last_rotated=s.last_rotated.isoformat() if s.last_rotated else None,
            next_rotation=s.next_rotation.isoformat() if s.next_rotation else None,
            is_active=s.is_active,
        )
        for s in expiring
    ]


@router.post("/secrets/rotate-all", response_model=list[RotationResponse])
async def rotate_all_due(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SecretRotationService, Depends(get_rotation_service)],
) -> list[RotationResponse]:
    """Rotate all secrets that are due for rotation."""
    results = await service.check_and_rotate_all()

    return [
        RotationResponse(
            secret_name=r.secret_name,
            success=r.success,
            old_version=r.old_version,
            new_version=r.new_version,
            error=r.error,
        )
        for r in results
    ]


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Check security service health."""
    return {"status": "healthy", "service": "security-scanner"}
