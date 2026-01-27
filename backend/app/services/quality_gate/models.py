"""Data models for Quality Gate service."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class QualityGateStatus(str, Enum):
    """Status of a quality gate check."""

    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    ERROR = "error"
    SKIPPED = "skipped"


class ThresholdOperator(str, Enum):
    """Operator for threshold comparison."""

    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "lte"
    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUAL = "gte"
    EQUAL = "eq"
    NOT_EQUAL = "ne"


class MetricThreshold(BaseModel):
    """Threshold configuration for a metric."""

    metric: str = Field(..., description="Metric name")
    operator: ThresholdOperator = Field(..., description="Comparison operator")
    value: float = Field(..., description="Threshold value")
    level: str = Field("error", description="Severity level if threshold is breached")
    message: str | None = Field(None, description="Custom message on breach")


class GateCondition(BaseModel):
    """A condition that must be met for the gate to pass."""

    name: str
    description: str | None = None
    thresholds: list[MetricThreshold] = Field(default_factory=list)
    required: bool = True  # If False, failure only produces warning


class QualityGateConfig(BaseModel):
    """Configuration for quality gate checks."""

    name: str = "default"
    description: str | None = None
    enabled: bool = True

    # Conditions to evaluate
    conditions: list[GateCondition] = Field(default_factory=list)

    # Default thresholds
    max_critical_issues: int = 0
    max_high_issues: int = 5
    max_security_issues: int = 0
    max_new_issues: int = 10
    min_code_quality_score: float = 7.0

    # Analysis options
    analyze_new_code_only: bool = True
    fail_on_security_issues: bool = True
    fail_on_critical_issues: bool = True

    # Badge generation
    generate_badge: bool = True
    badge_style: str = "flat"  # flat, flat-square, for-the-badge, plastic

    @classmethod
    def default(cls) -> "QualityGateConfig":
        """Create default quality gate configuration."""
        return cls(
            name="default",
            conditions=[
                GateCondition(
                    name="No Critical Issues",
                    description="No critical severity issues allowed",
                    thresholds=[
                        MetricThreshold(
                            metric="critical_issues",
                            operator=ThresholdOperator.EQUAL,
                            value=0,
                            level="error",
                            message="Critical issues must be fixed before merge",
                        )
                    ],
                    required=True,
                ),
                GateCondition(
                    name="No Security Vulnerabilities",
                    description="No security vulnerabilities allowed",
                    thresholds=[
                        MetricThreshold(
                            metric="security_issues",
                            operator=ThresholdOperator.EQUAL,
                            value=0,
                            level="error",
                            message="Security vulnerabilities must be fixed",
                        )
                    ],
                    required=True,
                ),
                GateCondition(
                    name="Limited New Issues",
                    description="Maximum 10 new issues per PR",
                    thresholds=[
                        MetricThreshold(
                            metric="new_issues",
                            operator=ThresholdOperator.LESS_THAN_OR_EQUAL,
                            value=10,
                            level="warning",
                            message="Consider fixing some issues",
                        )
                    ],
                    required=False,
                ),
                GateCondition(
                    name="Code Quality Score",
                    description="Minimum code quality score of 7.0",
                    thresholds=[
                        MetricThreshold(
                            metric="quality_score",
                            operator=ThresholdOperator.GREATER_THAN_OR_EQUAL,
                            value=7.0,
                            level="warning",
                            message="Code quality could be improved",
                        )
                    ],
                    required=False,
                ),
            ],
        )


class QualityMetric(BaseModel):
    """A quality metric measurement."""

    name: str
    value: float
    unit: str | None = None
    description: str | None = None
    trend: str | None = None  # up, down, stable


class ConditionResult(BaseModel):
    """Result of evaluating a single condition."""

    condition_name: str
    passed: bool
    required: bool
    message: str
    metrics: list[QualityMetric] = Field(default_factory=list)


class QualityGateResult(BaseModel):
    """Result of a quality gate evaluation."""

    status: QualityGateStatus
    gate_name: str
    passed: bool
    summary: str

    # Detailed results
    conditions_passed: int = 0
    conditions_failed: int = 0
    conditions_warning: int = 0
    condition_results: list[ConditionResult] = Field(default_factory=list)

    # Metrics
    metrics: dict[str, QualityMetric] = Field(default_factory=dict)

    # Analysis info
    files_analyzed: int = 0
    total_issues: int = 0
    critical_issues: int = 0
    security_issues: int = 0
    new_issues: int = 0
    quality_score: float = 0.0

    # Timing
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    duration_ms: float = 0.0

    # Badge
    badge_url: str | None = None
    badge_markdown: str | None = None

    # Details for CI output
    details: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_blocking(self) -> bool:
        """Whether this result should block the pipeline."""
        return self.status in (QualityGateStatus.FAILED, QualityGateStatus.ERROR)

    def to_github_output(self) -> dict[str, Any]:
        """Format result for GitHub Actions output."""
        return {
            "status": self.status.value,
            "passed": self.passed,
            "summary": self.summary,
            "total_issues": self.total_issues,
            "critical_issues": self.critical_issues,
            "security_issues": self.security_issues,
            "quality_score": self.quality_score,
            "conditions_passed": self.conditions_passed,
            "conditions_failed": self.conditions_failed,
            "badge_url": self.badge_url,
        }

    def to_markdown_summary(self) -> str:
        """Generate markdown summary for PR comment."""
        status_emoji = {
            QualityGateStatus.PASSED: "✅",
            QualityGateStatus.FAILED: "❌",
            QualityGateStatus.WARNING: "⚠️",
            QualityGateStatus.ERROR: "🔴",
            QualityGateStatus.SKIPPED: "⏭️",
        }

        emoji = status_emoji.get(self.status, "❓")
        lines = [
            f"## {emoji} NexusAI Quality Gate: {self.status.value.upper()}",
            "",
            self.summary,
            "",
            "### Metrics",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Files Analyzed | {self.files_analyzed} |",
            f"| Total Issues | {self.total_issues} |",
            f"| Critical Issues | {self.critical_issues} |",
            f"| Security Issues | {self.security_issues} |",
            f"| New Issues | {self.new_issues} |",
            f"| Quality Score | {self.quality_score:.1f}/10 |",
            "",
        ]

        if self.condition_results:
            lines.extend([
                "### Conditions",
                "",
                "| Condition | Status | Message |",
                "|-----------|--------|---------|",
            ])
            for cr in self.condition_results:
                status = "✅" if cr.passed else ("⚠️" if not cr.required else "❌")
                lines.append(f"| {cr.condition_name} | {status} | {cr.message} |")
            lines.append("")

        if self.badge_markdown:
            lines.extend([
                "### Badge",
                "",
                self.badge_markdown,
                "",
            ])

        lines.extend([
            "---",
            f"*Analysis completed in {self.duration_ms:.0f}ms*",
        ])

        return "\n".join(lines)
