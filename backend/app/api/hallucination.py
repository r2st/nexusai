"""Hallucination Detection API endpoints.

Provides endpoints for:
- Manual hallucination checking
- Analytics and trends
- Recent detection logs
"""

from datetime import datetime, timedelta, UTC
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.api.deps import get_current_user, get_db
from app.core.multitenancy import get_current_tenant_id
from app.models.user import User
from app.services.hallucination.service import (
    HallucinationDetectionService,
    HallucinationConfig,
)
from app.services.hallucination.citation_verifier import Document
from app.services.rag.embeddings import get_embeddings_service, EmbeddingsService
from app.services.observability.langfuse_client import get_langfuse_client, LangfuseClient

logger = structlog.get_logger()

router = APIRouter(prefix="/hallucination", tags=["hallucination"])


# =============================================================================
# Request/Response Models
# =============================================================================


class HallucinationCheckRequest(BaseModel):
    """Request for hallucination check."""

    query: str = Field(..., description="The original query/prompt")
    response: str = Field(..., description="The LLM response to check")
    context: list[str] | None = Field(
        None, description="Optional context documents for grounding check"
    )
    sources: list[dict[str, str]] | None = Field(
        None, description="Optional source documents for citation verification"
    )
    check_consistency: bool = Field(
        False, description="Whether to run consistency check (background)"
    )


class HallucinationIssueResponse(BaseModel):
    """A detected hallucination issue."""

    type: str = Field(..., description="Issue type")
    severity: str = Field(..., description="Severity: low, medium, high")
    description: str = Field(..., description="Issue description")
    evidence: dict[str, Any] = Field(default_factory=dict, description="Supporting evidence")


class HallucinationCheckResponse(BaseModel):
    """Response from hallucination check."""

    is_hallucination: bool = Field(..., description="Whether hallucination was detected")
    confidence: float = Field(..., description="Confidence in the detection (0-1)")
    hallucination_score: float = Field(..., description="Hallucination likelihood (0-1)")
    grounding_score: float | None = Field(None, description="Grounding in context (0-1)")
    consistency_score: float | None = Field(None, description="Consistency score (0-1)")
    relevance_score: float | None = Field(None, description="Relevance to query (0-1)")
    factuality_score: float | None = Field(None, description="Estimated factuality (0-1)")
    issues: list[HallucinationIssueResponse] = Field(
        default_factory=list, description="Detected issues"
    )
    check_types_performed: list[str] = Field(
        default_factory=list, description="Types of checks performed"
    )
    duration_ms: float = Field(..., description="Detection duration in milliseconds")


class HallucinationAnalyticsResponse(BaseModel):
    """Hallucination analytics summary."""

    total_checks: int = Field(..., description="Total number of checks")
    hallucination_count: int = Field(..., description="Number of hallucinations detected")
    hallucination_rate: float = Field(..., description="Rate of hallucinations (0-1)")
    avg_hallucination_score: float = Field(..., description="Average hallucination score")
    avg_grounding_score: float = Field(..., description="Average grounding score")
    avg_relevance_score: float = Field(..., description="Average relevance score")
    avg_confidence: float = Field(..., description="Average detection confidence")
    period_days: int = Field(..., description="Period in days")


class TrendDataPoint(BaseModel):
    """A single trend data point."""

    period: str = Field(..., description="Time period (ISO format)")
    total_checks: int = Field(..., description="Total checks in period")
    hallucination_count: int = Field(..., description="Hallucinations in period")
    hallucination_rate: float = Field(..., description="Rate for period")
    avg_hallucination_score: float = Field(..., description="Average score for period")


class HallucinationTrendsResponse(BaseModel):
    """Hallucination trends over time."""

    data: list[TrendDataPoint] = Field(..., description="Trend data points")
    granularity: str = Field(..., description="Data granularity")
    period_start: datetime = Field(..., description="Start of period")
    period_end: datetime = Field(..., description="End of period")


class LogEntry(BaseModel):
    """A hallucination log entry."""

    id: str = Field(..., description="Log entry ID")
    trace_id: str | None = Field(None, description="Trace ID")
    hallucination_score: float | None = Field(None, description="Hallucination score")
    grounding_score: float | None = Field(None, description="Grounding score")
    is_hallucination: bool = Field(..., description="Whether hallucination detected")
    confidence: float | None = Field(None, description="Detection confidence")
    issues: list[dict[str, Any]] | None = Field(None, description="Detected issues")
    check_type: str | None = Field(None, description="Type of check performed")
    duration_ms: float | None = Field(None, description="Check duration")
    created_at: str | None = Field(None, description="Creation timestamp")


class HallucinationLogsResponse(BaseModel):
    """Recent hallucination logs."""

    logs: list[LogEntry] = Field(..., description="Log entries")
    total: int = Field(..., description="Total number of entries")


# =============================================================================
# Dependencies
# =============================================================================


async def get_hallucination_service(
    embeddings: Annotated[EmbeddingsService | None, Depends(get_embeddings_service)] = None,
    langfuse: Annotated[LangfuseClient | None, Depends(get_langfuse_client)] = None,
) -> HallucinationDetectionService:
    """Get hallucination detection service."""
    return HallucinationDetectionService(
        embedding_service=embeddings,
        langfuse_client=langfuse,
        config=HallucinationConfig(),
    )


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/check",
    response_model=HallucinationCheckResponse,
    summary="Check for hallucinations",
    description="Check an LLM response for hallucinations.",
)
async def check_hallucination(
    request: HallucinationCheckRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[HallucinationDetectionService, Depends(get_hallucination_service)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> HallucinationCheckResponse:
    """Check response for hallucinations."""
    try:
        tenant_id = get_current_tenant_id()

        # Convert sources to Document objects if provided
        sources: list[Document] | None = None
        if request.sources:
            sources = [
                Document(
                    id=s.get("id", ""),
                    content=s.get("content", ""),
                    title=s.get("title"),
                    url=s.get("url"),
                )
                for s in request.sources
            ]

        result = await service.check(
            query=request.query,
            response=request.response,
            context=request.context,
            sources=sources,
            check_consistency=request.check_consistency,
            log_to_observability=True,
            db=db,
            tenant_id=tenant_id,
        )

        return HallucinationCheckResponse(
            is_hallucination=result.is_hallucination,
            confidence=result.confidence,
            hallucination_score=result.hallucination_score,
            grounding_score=result.grounding_score,
            consistency_score=result.consistency_score,
            relevance_score=result.relevance_score,
            factuality_score=result.factuality_score,
            issues=[
                HallucinationIssueResponse(
                    type=i.type,
                    severity=i.severity,
                    description=i.description,
                    evidence=i.evidence,
                )
                for i in result.issues
            ],
            check_types_performed=result.check_types_performed,
            duration_ms=result.duration_ms,
        )

    except Exception as e:
        logger.error("Hallucination check failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Hallucination check failed. Please try again later.",
        )


@router.get(
    "/analytics",
    response_model=HallucinationAnalyticsResponse,
    summary="Get hallucination analytics",
    description="Get aggregate hallucination metrics for a period.",
)
async def get_analytics(
    db: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[HallucinationDetectionService, Depends(get_hallucination_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
) -> HallucinationAnalyticsResponse:
    """Get hallucination analytics."""
    try:
        tenant_id = get_current_tenant_id()

        analytics = await service.get_analytics(
            db=db,
            tenant_id=tenant_id,
            days=days,
        )

        return HallucinationAnalyticsResponse(
            total_checks=analytics["total_checks"],
            hallucination_count=analytics["hallucination_count"],
            hallucination_rate=analytics["hallucination_rate"],
            avg_hallucination_score=analytics["avg_hallucination_score"],
            avg_grounding_score=analytics["avg_grounding_score"],
            avg_relevance_score=analytics["avg_relevance_score"],
            avg_confidence=analytics["avg_confidence"],
            period_days=days,
        )

    except Exception as e:
        logger.error("Failed to get hallucination analytics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analytics. Please try again later.",
        )


@router.get(
    "/trends",
    response_model=HallucinationTrendsResponse,
    summary="Get hallucination trends",
    description="Get hallucination trends over time.",
)
async def get_trends(
    db: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[HallucinationDetectionService, Depends(get_hallucination_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    days: int = Query(30, ge=1, le=365, description="Number of days"),
    granularity: str = Query(
        "daily", description="Granularity: hourly, daily, weekly"
    ),
) -> HallucinationTrendsResponse:
    """Get hallucination trends over time."""
    try:
        if granularity not in ["hourly", "daily", "weekly"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid granularity. Must be: hourly, daily, or weekly",
            )

        tenant_id = get_current_tenant_id()
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(days=days)

        trends = await service.get_trends(
            db=db,
            tenant_id=tenant_id,
            days=days,
            granularity=granularity,
        )

        return HallucinationTrendsResponse(
            data=[
                TrendDataPoint(
                    period=t["period"] or "",
                    total_checks=t["total_checks"],
                    hallucination_count=t["hallucination_count"],
                    hallucination_rate=t["hallucination_rate"],
                    avg_hallucination_score=t["avg_hallucination_score"],
                )
                for t in trends
            ],
            granularity=granularity,
            period_start=start_time,
            period_end=end_time,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get hallucination trends", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve trends. Please try again later.",
        )


@router.get(
    "/logs",
    response_model=HallucinationLogsResponse,
    summary="Get hallucination logs",
    description="Get recent hallucination detection logs.",
)
async def get_logs(
    db: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[HallucinationDetectionService, Depends(get_hallucination_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(50, ge=1, le=500, description="Maximum logs to return"),
    only_hallucinations: bool = Query(
        False, description="Only return detected hallucinations"
    ),
) -> HallucinationLogsResponse:
    """Get recent hallucination logs."""
    try:
        tenant_id = get_current_tenant_id()

        logs = await service.get_recent_logs(
            db=db,
            tenant_id=tenant_id,
            limit=limit,
            only_hallucinations=only_hallucinations,
        )

        return HallucinationLogsResponse(
            logs=[
                LogEntry(
                    id=log["id"],
                    trace_id=log.get("trace_id"),
                    hallucination_score=log.get("hallucination_score"),
                    grounding_score=log.get("grounding_score"),
                    is_hallucination=log["is_hallucination"],
                    confidence=log.get("confidence"),
                    issues=log.get("issues"),
                    check_type=log.get("check_type"),
                    duration_ms=log.get("duration_ms"),
                    created_at=log.get("created_at"),
                )
                for log in logs
            ],
            total=len(logs),
        )

    except Exception as e:
        logger.error("Failed to get hallucination logs", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve logs. Please try again later.",
        )
