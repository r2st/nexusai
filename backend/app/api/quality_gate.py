"""Quality Gate API endpoints for CI/CD integration."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
import structlog

from app.api.deps import get_current_user

logger = structlog.get_logger()
from app.models.user import User
from app.services.quality_gate import (
    QualityGateService,
    get_quality_gate_service,
    QualityGateConfig,
    QualityGateResult,
    QualityGateStatus,
)
from app.services.extensions import (
    ExtensionService,
    get_extension_service,
    AnalysisRequest,
)

router = APIRouter(prefix="/quality-gate", tags=["quality-gate"])


# Request/Response Models
class EvaluateRequest(BaseModel):
    """Request to evaluate quality gate."""

    file_uri: str = Field(..., description="URI of file to analyze")
    content: str = Field(..., description="File content")
    language_id: str = Field(..., description="Language identifier")
    config_name: str = Field("default", description="Quality gate config name")
    base_metrics: dict[str, float] | None = Field(None, description="Base branch metrics for comparison")


class EvaluatePRRequest(BaseModel):
    """Request to evaluate quality gate for a PR."""

    owner: str = Field(..., description="Repository owner")
    repo: str = Field(..., description="Repository name")
    pr_number: int = Field(..., description="Pull request number")
    config_name: str = Field("default", description="Quality gate config name")


class BatchEvaluateRequest(BaseModel):
    """Request to evaluate multiple files."""

    files: list[dict[str, str]] = Field(..., description="List of {file_uri, content, language_id}")
    config_name: str = Field("default", description="Quality gate config name")
    base_metrics: dict[str, float] | None = Field(None, description="Base branch metrics")


class GateResultResponse(BaseModel):
    """Quality gate result response."""

    status: QualityGateStatus
    passed: bool
    summary: str
    total_issues: int
    critical_issues: int
    security_issues: int
    quality_score: float
    conditions_passed: int
    conditions_failed: int
    badge_url: str | None
    markdown_summary: str
    github_output: dict[str, Any]


# Dependencies
async def get_gate_service() -> QualityGateService:
    """Get quality gate service instance."""
    return get_quality_gate_service()


async def get_ext_service() -> ExtensionService:
    """Get extension service instance."""
    return get_extension_service()


# Endpoints
@router.post("/evaluate", response_model=GateResultResponse)
async def evaluate_quality_gate(
    request: EvaluateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    gate_service: Annotated[QualityGateService, Depends(get_gate_service)],
    ext_service: Annotated[ExtensionService, Depends(get_ext_service)],
) -> GateResultResponse:
    """Evaluate quality gate for a single file.

    Analyzes the file and checks against configured quality gate thresholds.
    Returns pass/fail status suitable for CI/CD integration.
    """
    try:
        # Run analysis
        analysis_request = AnalysisRequest(
            file_uri=request.file_uri,
            content=request.content,
            language_id=request.language_id,
            analysis_types=["diagnostics", "smells", "security"],
        )
        analysis_result = await ext_service.analyze(analysis_request)

        # Get config
        config = gate_service.get_config(request.config_name)

        # Evaluate gate
        result = await gate_service.evaluate(
            analysis_result=analysis_result,
            config=config,
            base_metrics=request.base_metrics,
        )

        return GateResultResponse(
            status=result.status,
            passed=result.passed,
            summary=result.summary,
            total_issues=result.total_issues,
            critical_issues=result.critical_issues,
            security_issues=result.security_issues,
            quality_score=result.quality_score,
            conditions_passed=result.conditions_passed,
            conditions_failed=result.conditions_failed,
            badge_url=result.badge_url,
            markdown_summary=result.to_markdown_summary(),
            github_output=result.to_github_output(),
        )

    except Exception as e:
        logger.error("Quality gate evaluation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Quality gate evaluation failed. Please try again later.",
        )


@router.post("/evaluate/batch", response_model=GateResultResponse)
async def evaluate_batch(
    request: BatchEvaluateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    gate_service: Annotated[QualityGateService, Depends(get_gate_service)],
    ext_service: Annotated[ExtensionService, Depends(get_ext_service)],
) -> GateResultResponse:
    """Evaluate quality gate for multiple files.

    Aggregates analysis results from all files and evaluates against
    the quality gate configuration.
    """
    try:
        # Analyze all files
        all_issues = []
        total_metrics: dict[str, float] = {
            "files_analyzed": 0,
            "total_issues": 0,
            "critical_issues": 0,
            "security_issues": 0,
            "error_count": 0,
            "warning_count": 0,
        }

        for file_info in request.files:
            analysis_request = AnalysisRequest(
                file_uri=file_info["file_uri"],
                content=file_info["content"],
                language_id=file_info["language_id"],
                analysis_types=["diagnostics", "smells", "security"],
            )
            result = await ext_service.analyze(analysis_request)

            all_issues.extend(result.issues)
            total_metrics["files_analyzed"] += 1
            total_metrics["total_issues"] += len(result.issues)
            total_metrics["critical_issues"] += result.error_count
            total_metrics["error_count"] += result.error_count
            total_metrics["warning_count"] += result.warning_count
            total_metrics["security_issues"] += len(result.security_issues)

        # Create aggregated analysis result
        from app.services.extensions.models import AnalysisResult as ExtAnalysisResult

        aggregated = ExtAnalysisResult(
            file_uri="batch://multiple",
            version=1,
            issues=all_issues,
            metrics=total_metrics,
        )

        # Get config and evaluate
        config = gate_service.get_config(request.config_name)
        result = await gate_service.evaluate(
            analysis_result=aggregated,
            config=config,
            base_metrics=request.base_metrics,
        )

        result.files_analyzed = int(total_metrics["files_analyzed"])

        return GateResultResponse(
            status=result.status,
            passed=result.passed,
            summary=result.summary,
            total_issues=result.total_issues,
            critical_issues=result.critical_issues,
            security_issues=result.security_issues,
            quality_score=result.quality_score,
            conditions_passed=result.conditions_passed,
            conditions_failed=result.conditions_failed,
            badge_url=result.badge_url,
            markdown_summary=result.to_markdown_summary(),
            github_output=result.to_github_output(),
        )

    except Exception as e:
        logger.error("Batch quality gate evaluation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Batch evaluation failed. Please try again later.",
        )


@router.post("/evaluate/pr", response_model=GateResultResponse)
async def evaluate_pr(
    request: EvaluatePRRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    gate_service: Annotated[QualityGateService, Depends(get_gate_service)],
) -> GateResultResponse:
    """Evaluate quality gate for a GitHub/GitLab PR.

    Fetches PR data, runs analysis, and evaluates against quality gate.
    """
    try:
        config = gate_service.get_config(request.config_name)

        result = await gate_service.evaluate_pr(
            owner=request.owner,
            repo=request.repo,
            pr_number=request.pr_number,
            config=config,
        )

        return GateResultResponse(
            status=result.status,
            passed=result.passed,
            summary=result.summary,
            total_issues=result.total_issues,
            critical_issues=result.critical_issues,
            security_issues=result.security_issues,
            quality_score=result.quality_score,
            conditions_passed=result.conditions_passed,
            conditions_failed=result.conditions_failed,
            badge_url=result.badge_url,
            markdown_summary=result.to_markdown_summary(),
            github_output=result.to_github_output(),
        )

    except Exception as e:
        logger.error("PR quality gate evaluation failed", owner=request.owner, repo=request.repo, pr=request.pr_number, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PR evaluation failed. Please try again later.",
        )


@router.get("/config/{name}", response_model=QualityGateConfig)
async def get_config(
    name: str,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[QualityGateService, Depends(get_gate_service)],
) -> QualityGateConfig:
    """Get a quality gate configuration by name."""
    return service.get_config(name)


@router.put("/config", response_model=QualityGateConfig)
async def update_config(
    config: QualityGateConfig,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[QualityGateService, Depends(get_gate_service)],
) -> QualityGateConfig:
    """Create or update a quality gate configuration."""
    service.register_config(config)
    return config


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Check quality gate service health."""
    return {"status": "healthy", "service": "quality-gate"}
