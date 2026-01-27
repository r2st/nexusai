"""Models for the Query Gateway."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DataSource(str, Enum):
    """Available data sources."""

    METRICS = "metrics"  # DORA/SPACE rollups
    ENTITIES = "entities"  # Canonical entities
    EVENTS = "events"  # Raw events
    SEARCH = "search"  # Full-text search
    GRAPH = "graph"  # Knowledge graph


class QueryRequest(BaseModel):
    """Unified query request."""

    # Data sources to query
    sources: list[DataSource] = Field(
        default=[DataSource.METRICS],
        description="Data sources to include",
    )

    # Time range
    start_time: datetime | None = None
    end_time: datetime | None = None

    # Filters
    project_id: str | None = None
    team_id: str | None = None
    service_id: str | None = None
    entity_types: list[str] | None = None

    # Search
    search_query: str | None = None

    # Aggregation
    group_by: list[str] | None = None
    aggregations: list[str] | None = None

    # Pagination
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)

    # Options
    include_metadata: bool = False
    include_trends: bool = False


class QueryResponse(BaseModel):
    """Unified query response."""

    # Request info
    tenant_id: str
    request: QueryRequest

    # Results by source
    data: dict[str, Any] = Field(default_factory=dict)

    # Aggregated results
    summary: dict[str, Any] | None = None

    # Metadata
    total_count: int = 0
    has_more: bool = False
    execution_time_ms: float = 0

    # Warnings/errors
    warnings: list[str] = Field(default_factory=list)


class DashboardQuery(BaseModel):
    """Pre-defined dashboard query."""

    name: str
    description: str | None = None

    # Query config
    sources: list[DataSource]
    time_range: str = "7d"  # 1h, 24h, 7d, 30d, 90d
    granularity: str = "daily"

    # Filters
    filters: dict[str, Any] = Field(default_factory=dict)

    # Metrics to include
    metrics: list[str] = Field(default_factory=list)

    # Caching
    cache_ttl_seconds: int = 300


# Pre-defined dashboard queries
DASHBOARD_QUERIES = {
    "overview": DashboardQuery(
        name="Overview Dashboard",
        description="High-level metrics overview",
        sources=[DataSource.METRICS],
        time_range="30d",
        metrics=[
            "deployment_frequency",
            "lead_time_hours",
            "mttr_hours",
            "change_failure_rate",
            "overall_level",
        ],
    ),
    "team_health": DashboardQuery(
        name="Team Health Dashboard",
        description="SPACE framework team metrics",
        sources=[DataSource.METRICS],
        time_range="30d",
        metrics=[
            "activity_dimension",
            "communication_dimension",
            "efficiency_dimension",
            "overall_score",
        ],
    ),
    "deployments": DashboardQuery(
        name="Deployments Dashboard",
        description="Deployment activity and status",
        sources=[DataSource.ENTITIES],
        time_range="7d",
        filters={"entity_type": "deployment"},
        metrics=["count", "success_rate", "duration_avg"],
    ),
    "incidents": DashboardQuery(
        name="Incidents Dashboard",
        description="Incident tracking and MTTR",
        sources=[DataSource.ENTITIES],
        time_range="30d",
        filters={"entity_type": "incident"},
        metrics=["count", "mttr_avg", "severity_distribution"],
    ),
    "pull_requests": DashboardQuery(
        name="Pull Requests Dashboard",
        description="PR activity and cycle times",
        sources=[DataSource.ENTITIES],
        time_range="7d",
        filters={"entity_type": "pull_request"},
        metrics=["count", "cycle_time_avg", "review_time_avg"],
    ),
}
