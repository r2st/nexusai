"""Models for the Prompt Registry."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class PromptStatus(str, Enum):
    """Status of a prompt."""

    DRAFT = "draft"
    ACTIVE = "active"
    TESTING = "testing"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class ExperimentStatus(str, Enum):
    """Status of an A/B experiment."""

    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Prompt(BaseModel):
    """A prompt template."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str

    # Identity
    name: str = Field(..., description="Unique name within tenant")
    slug: str = Field(..., description="URL-friendly identifier")
    description: str | None = None
    category: str | None = None  # insights, metrics, code_review, etc.

    # Template
    template: str = Field(..., description="Prompt template with variables")
    system_prompt: str | None = None
    variables: list[str] = Field(
        default_factory=list,
        description="List of variable names in template",
    )

    # Model settings
    default_model: str | None = None
    default_temperature: float = 0.7
    default_max_tokens: int | None = None

    # Status
    status: PromptStatus = PromptStatus.DRAFT
    current_version: int = 1

    # Metadata
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_by: str | None = None


class PromptVersion(BaseModel):
    """A specific version of a prompt."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    prompt_id: str
    version: int

    # Template
    template: str
    system_prompt: str | None = None
    variables: list[str] = Field(default_factory=list)

    # Model settings
    model: str | None = None
    temperature: float = 0.7
    max_tokens: int | None = None

    # Change info
    change_description: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_by: str | None = None

    # Performance
    usage_count: int = 0
    avg_latency_ms: float | None = None
    avg_tokens: float | None = None
    success_rate: float | None = None


class PromptExperiment(BaseModel):
    """A/B test experiment for prompts."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str
    name: str
    description: str | None = None

    # Variants
    prompt_id: str
    control_version: int
    treatment_versions: list[int] = Field(default_factory=list)

    # Traffic allocation
    traffic_percentage: float = 10.0  # % of traffic to experiment
    variant_weights: dict[int, float] = Field(
        default_factory=dict,
        description="Version -> weight mapping",
    )

    # Targeting
    target_users: list[str] | None = None  # Specific users
    target_percentage: float = 100.0  # % of eligible users

    # Metrics
    primary_metric: str = "success_rate"  # What to optimize
    secondary_metrics: list[str] = Field(default_factory=list)

    # Status
    status: ExperimentStatus = ExperimentStatus.DRAFT
    started_at: datetime | None = None
    ended_at: datetime | None = None

    # Results
    winner_version: int | None = None
    statistical_significance: float | None = None

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_by: str | None = None


class PromptAssignment(BaseModel):
    """Assignment of a user to an experiment variant."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    experiment_id: str
    user_id: str
    assigned_version: int
    assigned_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Sticky assignment hash for consistency
    assignment_hash: str | None = None


class PromptPerformance(BaseModel):
    """Performance metrics for a prompt execution."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str
    prompt_id: str
    version: int

    # Execution context
    user_id: str | None = None
    session_id: str | None = None
    experiment_id: str | None = None

    # Request
    model: str
    input_tokens: int = 0
    input_variables: dict[str, Any] = Field(default_factory=dict)

    # Response
    output_tokens: int = 0
    latency_ms: float = 0
    success: bool = True
    error: str | None = None

    # Quality (optional, from evaluation)
    quality_score: float | None = None
    feedback: str | None = None

    # Cost
    cost_usd: float | None = None

    # Timestamp
    executed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PromptStats(BaseModel):
    """Aggregated statistics for a prompt."""

    prompt_id: str
    version: int | None = None  # None for all versions

    # Usage
    total_executions: int = 0
    unique_users: int = 0

    # Performance
    avg_latency_ms: float | None = None
    p50_latency_ms: float | None = None
    p95_latency_ms: float | None = None
    avg_input_tokens: float | None = None
    avg_output_tokens: float | None = None

    # Quality
    success_rate: float | None = None
    avg_quality_score: float | None = None

    # Cost
    total_cost_usd: float = 0

    # Time range
    period_start: datetime | None = None
    period_end: datetime | None = None
