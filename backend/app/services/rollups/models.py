"""Models for precomputed metric rollups."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class RollupGranularity(str, Enum):
    """Rollup time granularity."""

    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class MetricRollup(BaseModel):
    """Base class for metric rollups."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str
    granularity: RollupGranularity

    # Time period
    period_start: datetime
    period_end: datetime

    # Scope
    project_id: str | None = None
    team_id: str | None = None
    service_id: str | None = None
    environment: str | None = None

    # Computation metadata
    computed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    data_points: int = 0
    is_partial: bool = False  # True if period is incomplete

    # Raw data
    metrics: dict[str, Any] = Field(default_factory=dict)


class DORArollup(MetricRollup):
    """DORA metrics rollup."""

    # Deployment Frequency
    deployment_count: int = 0
    deployment_frequency: float = 0.0  # per day
    deployment_frequency_level: str = "unknown"

    # Lead Time for Changes
    lead_time_hours: float | None = None
    lead_time_p50: float | None = None
    lead_time_p95: float | None = None
    lead_time_level: str = "unknown"

    # Mean Time to Recovery
    incident_count: int = 0
    mttr_hours: float | None = None
    mttr_p50: float | None = None
    mttr_p95: float | None = None
    mttr_level: str = "unknown"

    # Change Failure Rate
    failed_deployment_count: int = 0
    change_failure_rate: float = 0.0  # percentage
    cfr_level: str = "unknown"

    # Overall
    overall_level: str = "unknown"

    # Supporting metrics
    commits_count: int = 0
    prs_merged: int = 0
    incidents_resolved: int = 0


class SPACERollup(MetricRollup):
    """SPACE framework metrics rollup."""

    # Satisfaction
    satisfaction_score: float | None = None
    burnout_risk: float | None = None
    work_life_balance: float | None = None

    # Performance
    code_review_quality: float | None = None
    bug_fix_rate: float | None = None
    feature_completion_rate: float | None = None

    # Activity
    commits_per_developer: float = 0.0
    prs_per_developer: float = 0.0
    reviews_per_developer: float = 0.0
    active_days_ratio: float = 0.0

    # Communication
    review_participation_rate: float = 0.0
    cross_team_collaboration: float = 0.0
    documentation_ratio: float = 0.0

    # Efficiency
    pr_cycle_time_hours: float | None = None
    time_to_first_review_hours: float | None = None
    rework_ratio: float = 0.0
    flow_efficiency: float | None = None

    # Dimension scores (0-100)
    satisfaction_dimension: float | None = None
    performance_dimension: float | None = None
    activity_dimension: float | None = None
    communication_dimension: float | None = None
    efficiency_dimension: float | None = None

    # Overall
    overall_score: float | None = None

    # Developer counts
    active_developers: int = 0
    total_developers: int = 0


class RollupQuery(BaseModel):
    """Query parameters for rollup retrieval."""

    tenant_id: str
    granularity: RollupGranularity = RollupGranularity.DAILY
    metric_type: str = "dora"  # dora, space

    # Time range
    start_date: datetime
    end_date: datetime

    # Scope filters
    project_id: str | None = None
    team_id: str | None = None
    service_id: str | None = None
    environment: str | None = None

    # Options
    include_partial: bool = False
    fill_gaps: bool = True  # Fill missing periods with zeros


class RollupStats(BaseModel):
    """Statistics about rollup computation."""

    tenant_id: str
    metric_type: str
    total_rollups: int = 0
    latest_rollup_at: datetime | None = None
    oldest_rollup_at: datetime | None = None
    coverage: dict[str, int] = Field(default_factory=dict)  # granularity -> count
