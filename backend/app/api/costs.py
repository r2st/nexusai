"""Cost Analytics API endpoints.

Provides endpoints for:
- Cost summaries and breakdowns
- Time-series cost data for charts
- Cost forecasting
- Budget alerts
"""

from datetime import datetime, timedelta, UTC
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.api.deps import get_current_user, get_db
from app.core.multitenancy import get_current_tenant_id
from app.models.user import User
from app.services.llm_gateway.service import get_gateway, LLMGateway

logger = structlog.get_logger()

router = APIRouter(prefix="/costs", tags=["costs"])


# =============================================================================
# Request/Response Models
# =============================================================================


class CostSummaryResponse(BaseModel):
    """Cost summary for a period."""

    total_cost: float = Field(..., description="Total cost in USD")
    total_tokens: int = Field(..., description="Total tokens used")
    prompt_tokens: int = Field(..., description="Total prompt/input tokens")
    completion_tokens: int = Field(..., description="Total completion/output tokens")
    request_count: int = Field(..., description="Number of requests")
    avg_latency_ms: float | None = Field(None, description="Average request latency")
    success_rate: float = Field(..., description="Success rate (0-1)")
    period_start: datetime = Field(..., description="Start of the period")
    period_end: datetime = Field(..., description="End of the period")


class TimeSeriesDataPoint(BaseModel):
    """A single time-series data point."""

    period: datetime = Field(..., description="Time period")
    total_cost: float = Field(..., description="Cost for this period")
    total_tokens: int = Field(..., description="Tokens for this period")
    request_count: int = Field(..., description="Requests for this period")


class CostTimeSeriesResponse(BaseModel):
    """Time-series cost data."""

    data: list[TimeSeriesDataPoint] = Field(..., description="Time-series data points")
    granularity: str = Field(..., description="Data granularity (hourly, daily, weekly, monthly)")
    period_start: datetime = Field(..., description="Start of the period")
    period_end: datetime = Field(..., description="End of the period")


class BreakdownItem(BaseModel):
    """A single breakdown item."""

    name: str = Field(..., description="Model or provider name")
    total_cost: float = Field(..., description="Total cost")
    total_tokens: int = Field(..., description="Total tokens")
    request_count: int = Field(..., description="Number of requests")
    avg_latency_ms: float | None = Field(None, description="Average latency")
    percentage: float = Field(..., description="Percentage of total cost")


class CostBreakdownResponse(BaseModel):
    """Cost breakdown by model or provider."""

    items: list[BreakdownItem] = Field(..., description="Breakdown items")
    total_cost: float = Field(..., description="Total cost across all items")
    period_start: datetime = Field(..., description="Start of the period")
    period_end: datetime = Field(..., description="End of the period")


class CostForecastResponse(BaseModel):
    """Cost forecast based on recent trends."""

    projected_monthly_cost: float = Field(..., description="Projected monthly cost")
    daily_average: float = Field(..., description="Average daily cost")
    confidence: str = Field(..., description="Forecast confidence (low, medium, high)")
    basis_days: int = Field(..., description="Number of days used for projection")
    basis_cost: float = Field(..., description="Total cost for basis period")
    basis_requests: int = Field(..., description="Total requests for basis period")


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/summary",
    response_model=CostSummaryResponse,
    summary="Get cost summary",
    description="Get cost summary for a time period.",
)
async def get_cost_summary(
    db: Annotated[AsyncSession, Depends(get_db)],
    gateway: Annotated[LLMGateway, Depends(get_gateway)],
    current_user: Annotated[User, Depends(get_current_user)],
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    user_id: str | None = Query(None, description="Filter by user ID"),
) -> CostSummaryResponse:
    """Get cost summary for the specified period."""
    try:
        tenant_id = get_current_tenant_id()
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(days=days)

        summary = await gateway.cost_tracker.get_summary(
            db=db,
            tenant_id=tenant_id,
            start_time=start_time,
            end_time=end_time,
            user_id=user_id,
        )

        return CostSummaryResponse(
            total_cost=summary["total_cost"],
            total_tokens=summary["total_tokens"],
            prompt_tokens=summary["prompt_tokens"],
            completion_tokens=summary["completion_tokens"],
            request_count=summary["request_count"],
            avg_latency_ms=summary["avg_latency_ms"],
            success_rate=summary["success_rate"],
            period_start=start_time,
            period_end=end_time,
        )

    except Exception as e:
        logger.error("Failed to get cost summary", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cost summary. Please try again later.",
        )


@router.get(
    "/time-series",
    response_model=CostTimeSeriesResponse,
    summary="Get cost time-series",
    description="Get cost data over time for charts.",
)
async def get_cost_time_series(
    db: Annotated[AsyncSession, Depends(get_db)],
    gateway: Annotated[LLMGateway, Depends(get_gateway)],
    current_user: Annotated[User, Depends(get_current_user)],
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    granularity: str = Query("daily", description="Data granularity: hourly, daily, weekly, monthly"),
    user_id: str | None = Query(None, description="Filter by user ID"),
    model: str | None = Query(None, description="Filter by model"),
    provider: str | None = Query(None, description="Filter by provider"),
) -> CostTimeSeriesResponse:
    """Get cost time-series data for charts."""
    try:
        if granularity not in ["hourly", "daily", "weekly", "monthly"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid granularity. Must be: hourly, daily, weekly, or monthly",
            )

        tenant_id = get_current_tenant_id()
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(days=days)

        data = await gateway.cost_tracker.get_time_series(
            db=db,
            tenant_id=tenant_id,
            start_time=start_time,
            end_time=end_time,
            granularity=granularity,
            user_id=user_id,
            model=model,
            provider=provider,
        )

        return CostTimeSeriesResponse(
            data=[
                TimeSeriesDataPoint(
                    period=datetime.fromisoformat(d["period"]) if isinstance(d["period"], str) else d["period"],
                    total_cost=d["total_cost"],
                    total_tokens=d["total_tokens"],
                    request_count=d["request_count"],
                )
                for d in data
            ],
            granularity=granularity,
            period_start=start_time,
            period_end=end_time,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get cost time-series", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cost data. Please try again later.",
        )


@router.get(
    "/breakdown/model",
    response_model=CostBreakdownResponse,
    summary="Get cost breakdown by model",
    description="Get cost breakdown grouped by model.",
)
async def get_cost_breakdown_by_model(
    db: Annotated[AsyncSession, Depends(get_db)],
    gateway: Annotated[LLMGateway, Depends(get_gateway)],
    current_user: Annotated[User, Depends(get_current_user)],
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
) -> CostBreakdownResponse:
    """Get cost breakdown by model."""
    try:
        tenant_id = get_current_tenant_id()
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(days=days)

        breakdown = await gateway.cost_tracker.get_breakdown_by_model(
            db=db,
            tenant_id=tenant_id,
            start_time=start_time,
            end_time=end_time,
        )

        total_cost = sum(item["total_cost"] for item in breakdown)

        return CostBreakdownResponse(
            items=[
                BreakdownItem(
                    name=item["model"],
                    total_cost=item["total_cost"],
                    total_tokens=item["total_tokens"],
                    request_count=item["request_count"],
                    avg_latency_ms=item["avg_latency_ms"],
                    percentage=(item["total_cost"] / total_cost * 100) if total_cost > 0 else 0,
                )
                for item in breakdown
            ],
            total_cost=total_cost,
            period_start=start_time,
            period_end=end_time,
        )

    except Exception as e:
        logger.error("Failed to get cost breakdown by model", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cost breakdown. Please try again later.",
        )


@router.get(
    "/breakdown/provider",
    response_model=CostBreakdownResponse,
    summary="Get cost breakdown by provider",
    description="Get cost breakdown grouped by provider.",
)
async def get_cost_breakdown_by_provider(
    db: Annotated[AsyncSession, Depends(get_db)],
    gateway: Annotated[LLMGateway, Depends(get_gateway)],
    current_user: Annotated[User, Depends(get_current_user)],
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
) -> CostBreakdownResponse:
    """Get cost breakdown by provider."""
    try:
        tenant_id = get_current_tenant_id()
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(days=days)

        breakdown = await gateway.cost_tracker.get_breakdown_by_provider(
            db=db,
            tenant_id=tenant_id,
            start_time=start_time,
            end_time=end_time,
        )

        total_cost = sum(item["total_cost"] for item in breakdown)

        return CostBreakdownResponse(
            items=[
                BreakdownItem(
                    name=item["provider"],
                    total_cost=item["total_cost"],
                    total_tokens=item["total_tokens"],
                    request_count=item["request_count"],
                    avg_latency_ms=item["avg_latency_ms"],
                    percentage=(item["total_cost"] / total_cost * 100) if total_cost > 0 else 0,
                )
                for item in breakdown
            ],
            total_cost=total_cost,
            period_start=start_time,
            period_end=end_time,
        )

    except Exception as e:
        logger.error("Failed to get cost breakdown by provider", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cost breakdown. Please try again later.",
        )


@router.get(
    "/forecast",
    response_model=CostForecastResponse,
    summary="Get cost forecast",
    description="Get projected monthly cost based on recent trends.",
)
async def get_cost_forecast(
    db: Annotated[AsyncSession, Depends(get_db)],
    gateway: Annotated[LLMGateway, Depends(get_gateway)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> CostForecastResponse:
    """Get cost forecast based on recent usage."""
    try:
        tenant_id = get_current_tenant_id()

        forecast = await gateway.cost_tracker.forecast_monthly_cost(
            db=db,
            tenant_id=tenant_id,
        )

        return CostForecastResponse(
            projected_monthly_cost=forecast["projected_monthly_cost"],
            daily_average=forecast["daily_average"],
            confidence=forecast["confidence"],
            basis_days=forecast["basis_days"],
            basis_cost=forecast.get("basis_cost", 0),
            basis_requests=forecast.get("basis_requests", 0),
        )

    except Exception as e:
        logger.error("Failed to get cost forecast", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate cost forecast. Please try again later.",
        )
