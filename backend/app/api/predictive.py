"""Predictive Analytics API endpoints."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.models.user import User
from app.services.predictive import (
    PredictiveAnalyticsService,
    get_predictive_analytics_service,
)

router = APIRouter(prefix="/predictive", tags=["predictive-analytics"])


# Request/Response Models
class TimeSeriesPoint(BaseModel):
    """A point in a time series."""

    timestamp: str
    value: float
    metadata: dict[str, Any] | None = None


class TrendRequest(BaseModel):
    """Request for trend prediction."""

    metric_name: str = Field(..., description="Name of the metric")
    data_points: list[TimeSeriesPoint] = Field(..., description="Historical data")
    horizon_days: int = Field(7, ge=1, le=90, description="Forecast horizon in days")


class TrendResponse(BaseModel):
    """Trend prediction response."""

    metric_name: str
    direction: str
    current_value: float
    predicted_value: float
    confidence: float
    trend_slope: float
    volatility: float
    seasonality_detected: bool
    insights: list[str]


class BottleneckRequest(BaseModel):
    """Request for bottleneck detection."""

    metrics: dict[str, Any] = Field(..., description="Current metric values")


class BottleneckResponse(BaseModel):
    """Detected bottleneck."""

    type: str
    severity: str
    location: str
    description: str
    impact_score: float
    affected_metrics: list[str]
    suggested_actions: list[str]


class RiskAssessmentRequest(BaseModel):
    """Request for risk assessment."""

    deployment: dict[str, Any] | None = Field(None, description="Deployment info")
    pr: dict[str, Any] | None = Field(None, description="PR info")
    context: dict[str, Any] | None = Field(None, description="Additional context")


class RiskResponse(BaseModel):
    """Risk assessment response."""

    overall_score: float
    level: str
    summary: str
    recommendations: list[str]
    is_safe: bool


class InsightsRequest(BaseModel):
    """Request for comprehensive insights."""

    metrics: dict[str, Any] = Field(..., description="Current metrics")
    time_series: dict[str, list[TimeSeriesPoint]] | None = Field(
        None, description="Historical time series"
    )
    context: dict[str, Any] | None = Field(None, description="Additional context")


class InsightsResponse(BaseModel):
    """Comprehensive predictive insights."""

    trends_count: int
    bottlenecks_count: int
    recommendations_count: int
    summary: str
    declining_metrics: list[str]
    critical_bottlenecks: list[str]
    top_recommendations: list[str]


# Dependencies
async def get_analytics_service() -> PredictiveAnalyticsService:
    """Get predictive analytics service instance."""
    return get_predictive_analytics_service()


# Endpoints
@router.post("/trends/predict", response_model=TrendResponse)
async def predict_trend(
    request: TrendRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PredictiveAnalyticsService, Depends(get_analytics_service)],
) -> TrendResponse:
    """Predict future trend for a metric.

    Uses time series analysis to forecast metric values and
    detect patterns like seasonality.
    """
    try:
        data_points = [
            {"timestamp": p.timestamp, "value": p.value, "metadata": p.metadata or {}}
            for p in request.data_points
        ]

        prediction = service.predict_metric_trend(
            metric_name=request.metric_name,
            data_points=data_points,
            horizon_days=request.horizon_days,
        )

        return TrendResponse(
            metric_name=prediction.metric_name,
            direction=prediction.direction.value,
            current_value=prediction.current_value,
            predicted_value=prediction.predicted_value,
            confidence=prediction.confidence,
            trend_slope=prediction.trend_slope,
            volatility=prediction.volatility,
            seasonality_detected=prediction.seasonality_detected,
            insights=prediction.insights,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to predict trend: {e}",
        )


@router.post("/bottlenecks/detect", response_model=list[BottleneckResponse])
async def detect_bottlenecks(
    request: BottleneckRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PredictiveAnalyticsService, Depends(get_analytics_service)],
) -> list[BottleneckResponse]:
    """Detect process bottlenecks.

    Analyzes metrics to identify slowdowns and constraints in
    the development process.
    """
    try:
        bottlenecks = service.detect_bottlenecks(request.metrics)

        return [
            BottleneckResponse(
                type=b.type.value,
                severity=b.severity.value,
                location=b.location,
                description=b.description,
                impact_score=b.impact_score,
                affected_metrics=b.affected_metrics,
                suggested_actions=b.suggested_actions,
            )
            for b in bottlenecks
        ]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detect bottlenecks: {e}",
        )


@router.post("/risk/deployment", response_model=RiskResponse)
async def assess_deployment_risk(
    request: RiskAssessmentRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PredictiveAnalyticsService, Depends(get_analytics_service)],
) -> RiskResponse:
    """Assess deployment risk.

    Evaluates various factors to determine the risk level
    of a deployment.
    """
    if not request.deployment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Deployment info is required",
        )

    try:
        assessment = service.assess_deployment_risk(
            deployment=request.deployment,
            context=request.context,
        )

        return RiskResponse(
            overall_score=assessment.overall_score,
            level=assessment.level.value,
            summary=assessment.summary,
            recommendations=assessment.recommendations,
            is_safe=assessment.is_safe_to_deploy,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assess risk: {e}",
        )


@router.post("/risk/pr", response_model=RiskResponse)
async def assess_pr_risk(
    request: RiskAssessmentRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PredictiveAnalyticsService, Depends(get_analytics_service)],
) -> RiskResponse:
    """Assess pull request risk.

    Evaluates PR characteristics to determine merge risk.
    """
    if not request.pr:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PR info is required",
        )

    try:
        assessment = service.assess_pr_risk(
            pr=request.pr,
            context=request.context,
        )

        return RiskResponse(
            overall_score=assessment.overall_score,
            level=assessment.level.value,
            summary=assessment.summary,
            recommendations=assessment.recommendations,
            is_safe=assessment.is_safe_to_deploy,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assess PR risk: {e}",
        )


@router.post("/insights", response_model=InsightsResponse)
async def get_insights(
    request: InsightsRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PredictiveAnalyticsService, Depends(get_analytics_service)],
) -> InsightsResponse:
    """Get comprehensive predictive insights.

    Combines trend analysis, bottleneck detection, and
    recommendations into a unified view.
    """
    try:
        # Convert time series if provided
        time_series_data = None
        if request.time_series:
            time_series_data = {
                name: [
                    {"timestamp": p.timestamp, "value": p.value}
                    for p in points
                ]
                for name, points in request.time_series.items()
            }

        insights = await service.get_insights(
            metrics=request.metrics,
            time_series_data=time_series_data,
            context=request.context,
        )

        # Extract key information
        declining = [
            t.metric_name for t in insights.trends
            if t.direction.value == "declining"
        ]
        critical_bottlenecks = [
            b.location for b in insights.bottlenecks
            if b.severity.value == "critical"
        ]
        top_recs = [r.title for r in insights.recommendations[:5]]

        return InsightsResponse(
            trends_count=len(insights.trends),
            bottlenecks_count=len(insights.bottlenecks),
            recommendations_count=len(insights.recommendations),
            summary=insights.summary,
            declining_metrics=declining,
            critical_bottlenecks=critical_bottlenecks,
            top_recommendations=top_recs,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get insights: {e}",
        )


@router.post("/anomalies/detect")
async def detect_anomalies(
    request: TrendRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PredictiveAnalyticsService, Depends(get_analytics_service)],
    sensitivity: float = 2.0,
) -> list[TimeSeriesPoint]:
    """Detect anomalies in metric data.

    Uses statistical methods to identify outliers in time series data.
    """
    try:
        data_points = [
            {"timestamp": p.timestamp, "value": p.value}
            for p in request.data_points
        ]

        anomalies = service.detect_anomalies(
            metric_name=request.metric_name,
            data_points=data_points,
            sensitivity=sensitivity,
        )

        return [
            TimeSeriesPoint(
                timestamp=a.timestamp.isoformat(),
                value=a.value,
                metadata=a.metadata,
            )
            for a in anomalies
        ]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detect anomalies: {e}",
        )


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Check predictive analytics service health."""
    return {"status": "healthy", "service": "predictive-analytics"}
