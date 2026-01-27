"""Models for the Evaluation Framework."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class TestCaseType(str, Enum):
    """Types of test cases."""

    EXACT_MATCH = "exact_match"
    CONTAINS = "contains"
    REGEX = "regex"
    SEMANTIC = "semantic"
    CUSTOM = "custom"
    LLM_JUDGE = "llm_judge"


class EvalStatus(str, Enum):
    """Status of an evaluation run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TestCase(BaseModel):
    """A single test case for evaluation."""

    id: str = Field(default_factory=lambda: str(uuid4()))

    # Input
    name: str = Field(..., description="Test case name")
    description: str | None = None
    input_variables: dict[str, Any] = Field(
        ..., description="Variables to pass to prompt"
    )

    # Expected output
    expected_output: str | None = None
    expected_contains: list[str] = Field(default_factory=list)
    expected_not_contains: list[str] = Field(default_factory=list)
    expected_regex: str | None = None

    # Evaluation type
    eval_type: TestCaseType = TestCaseType.CONTAINS
    custom_eval_fn: str | None = None  # Python code for custom eval

    # Scoring
    weight: float = 1.0
    tags: list[str] = Field(default_factory=list)

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)


class TestSet(BaseModel):
    """A collection of test cases."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str

    # Identity
    name: str
    description: str | None = None
    prompt_id: str | None = None  # Optional association with a prompt

    # Test cases
    test_cases: list[TestCase] = Field(default_factory=list)

    # Configuration
    default_eval_type: TestCaseType = TestCaseType.CONTAINS
    pass_threshold: float = 0.8  # Minimum pass rate

    # Status
    is_active: bool = True
    version: int = 1

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_by: str | None = None


class QualityMetric(BaseModel):
    """A quality metric result."""

    name: str
    value: float
    passed: bool
    threshold: float | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class EvalResult(BaseModel):
    """Result of evaluating a single test case."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    test_case_id: str
    test_case_name: str

    # Execution
    input_variables: dict[str, Any] = Field(default_factory=dict)
    actual_output: str = ""
    expected_output: str | None = None

    # Result
    passed: bool = False
    score: float = 0.0  # 0.0 to 1.0
    metrics: list[QualityMetric] = Field(default_factory=list)

    # Performance
    latency_ms: float = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float | None = None

    # Errors
    error: str | None = None

    # Metadata
    model: str | None = None
    prompt_version: int | None = None
    executed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EvalRun(BaseModel):
    """An evaluation run across a test set."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str

    # Association
    test_set_id: str
    test_set_name: str | None = None
    prompt_id: str | None = None
    prompt_version: int | None = None

    # Configuration
    model: str
    temperature: float = 0.7
    max_tokens: int | None = None

    # Results
    results: list[EvalResult] = Field(default_factory=list)
    status: EvalStatus = EvalStatus.PENDING

    # Metrics
    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0
    error_cases: int = 0
    pass_rate: float = 0.0
    avg_score: float = 0.0
    avg_latency_ms: float = 0.0
    total_cost_usd: float = 0.0

    # Comparison (for regression detection)
    baseline_run_id: str | None = None
    regression_detected: bool = False
    regression_details: dict[str, Any] = Field(default_factory=dict)

    # Timing
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float | None = None

    # Metadata
    triggered_by: str | None = None  # manual, ci, schedule
    git_commit: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EvalComparison(BaseModel):
    """Comparison between two evaluation runs."""

    run_a_id: str
    run_b_id: str

    # Metrics comparison
    pass_rate_delta: float = 0.0
    avg_score_delta: float = 0.0
    latency_delta_ms: float = 0.0
    cost_delta_usd: float = 0.0

    # Test case comparison
    improved_cases: list[str] = Field(default_factory=list)
    regressed_cases: list[str] = Field(default_factory=list)
    unchanged_cases: list[str] = Field(default_factory=list)

    # Statistical significance
    is_significant: bool = False
    p_value: float | None = None
