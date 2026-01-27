"""Data models for Predictive Analytics service."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TrendDirection(str, Enum):
    """Direction of a trend."""

    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"
    VOLATILE = "volatile"


class RiskLevel(str, Enum):
    """Risk level classification."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MINIMAL = "minimal"


class BottleneckType(str, Enum):
    """Type of bottleneck detected."""

    CODE_REVIEW = "code_review"
    DEPLOYMENT = "deployment"
    TESTING = "testing"
    MERGE_CONFLICTS = "merge_conflicts"
    RESOURCE = "resource"
    PROCESS = "process"
    COMMUNICATION = "communication"
    TECHNICAL_DEBT = "technical_debt"


class RecommendationType(str, Enum):
    """Type of recommendation."""

    PROCESS = "process"
    TOOLING = "tooling"
    TEAM = "team"
    TECHNICAL = "technical"
    RESOURCE = "resource"
    TRAINING = "training"


class TimeSeriesPoint(BaseModel):
    """A single point in a time series."""

    timestamp: datetime
    value: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class TimeSeries(BaseModel):
    """A time series of data points."""

    name: str
    unit: str = ""
    points: list[TimeSeriesPoint] = Field(default_factory=list)

    @property
    def values(self) -> list[float]:
        return [p.value for p in self.points]

    @property
    def timestamps(self) -> list[datetime]:
        return [p.timestamp for p in self.points]

    def last_n(self, n: int) -> "TimeSeries":
        """Get last n points."""
        return TimeSeries(
            name=self.name,
            unit=self.unit,
            points=self.points[-n:] if self.points else [],
        )


class TrendPrediction(BaseModel):
    """Prediction for a metric trend."""

    metric_name: str
    direction: TrendDirection
    current_value: float
    predicted_value: float
    confidence: float = Field(ge=0, le=1)
    prediction_horizon: str = "7d"  # e.g., "7d", "30d", "90d"
    trend_slope: float = 0.0
    volatility: float = 0.0
    seasonality_detected: bool = False
    historical_data: list[TimeSeriesPoint] = Field(default_factory=list)
    forecast_data: list[TimeSeriesPoint] = Field(default_factory=list)
    insights: list[str] = Field(default_factory=list)


class Bottleneck(BaseModel):
    """Detected bottleneck in the development process."""

    type: BottleneckType
    severity: RiskLevel
    location: str
    description: str
    impact_score: float = Field(ge=0, le=10)
    affected_metrics: list[str] = Field(default_factory=list)
    root_causes: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    evidence: dict[str, Any] = Field(default_factory=dict)


class RiskFactor(BaseModel):
    """A single risk factor contributing to overall risk."""

    name: str
    category: str
    score: float = Field(ge=0, le=10)
    weight: float = 1.0
    description: str
    mitigations: list[str] = Field(default_factory=list)


class RiskAssessment(BaseModel):
    """Risk assessment for a deployment or change."""

    overall_score: float = Field(ge=0, le=10)
    level: RiskLevel
    factors: list[RiskFactor] = Field(default_factory=list)
    summary: str
    recommendations: list[str] = Field(default_factory=list)
    assessed_at: datetime = Field(default_factory=datetime.utcnow)
    context: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_safe_to_deploy(self) -> bool:
        return self.level in (RiskLevel.LOW, RiskLevel.MINIMAL)


class Recommendation(BaseModel):
    """Actionable recommendation for improvement."""

    id: str
    type: RecommendationType
    title: str
    description: str
    priority: RiskLevel
    effort: str = "medium"  # low, medium, high
    impact: str = "medium"  # low, medium, high
    category: str
    metrics_affected: list[str] = Field(default_factory=list)
    implementation_steps: list[str] = Field(default_factory=list)
    expected_improvement: str = ""
    evidence: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PredictiveInsight(BaseModel):
    """Combined predictive insight."""

    trends: list[TrendPrediction] = Field(default_factory=list)
    bottlenecks: list[Bottleneck] = Field(default_factory=list)
    risk_assessment: RiskAssessment | None = None
    recommendations: list[Recommendation] = Field(default_factory=list)
    summary: str = ""
    generated_at: datetime = Field(default_factory=datetime.utcnow)
