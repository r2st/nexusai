"""Quality Gate service for CI/CD integration."""

import logging
import time
from datetime import datetime
from typing import Any

from app.core.config import settings
from app.services.quality_gate.models import (
    QualityGateConfig,
    QualityGateResult,
    QualityGateStatus,
    QualityMetric,
    MetricThreshold,
    ThresholdOperator,
    ConditionResult,
)
from app.services.code_review.models import CodeReview, ReviewPriority, ReviewCategory
from app.services.extensions.models import AnalysisResult, IssueSeverity, IssueCategory

logger = logging.getLogger(__name__)

# Singleton instance
_quality_gate_service: "QualityGateService | None" = None


class QualityGateService:
    """Service for evaluating quality gates in CI/CD pipelines.

    Provides configurable quality gates that can pass/fail based on
    code analysis results, enforcing quality standards in PRs.
    """

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or settings.BACKEND_URL
        self._configs: dict[str, QualityGateConfig] = {
            "default": QualityGateConfig.default(),
        }

    def register_config(self, config: QualityGateConfig) -> None:
        """Register a quality gate configuration."""
        self._configs[config.name] = config

    def get_config(self, name: str = "default") -> QualityGateConfig:
        """Get a quality gate configuration by name."""
        return self._configs.get(name, QualityGateConfig.default())

    async def evaluate(
        self,
        analysis_result: AnalysisResult | None = None,
        code_review: CodeReview | None = None,
        config: QualityGateConfig | None = None,
        base_metrics: dict[str, float] | None = None,
    ) -> QualityGateResult:
        """Evaluate quality gate based on analysis results.

        Args:
            analysis_result: Result from extension analysis
            code_review: Result from code review service
            config: Quality gate configuration (uses default if not provided)
            base_metrics: Metrics from base branch for comparison

        Returns:
            QualityGateResult with pass/fail status and details
        """
        start_time = time.time()
        config = config or self.get_config()

        if not config.enabled:
            return QualityGateResult(
                status=QualityGateStatus.SKIPPED,
                gate_name=config.name,
                passed=True,
                summary="Quality gate is disabled",
            )

        # Collect metrics from inputs
        metrics = self._collect_metrics(analysis_result, code_review, base_metrics)

        # Evaluate conditions
        condition_results: list[ConditionResult] = []
        required_failed = False
        warning_count = 0

        for condition in config.conditions:
            result = self._evaluate_condition(condition, metrics)
            condition_results.append(result)

            if not result.passed:
                if condition.required:
                    required_failed = True
                else:
                    warning_count += 1

        # Determine overall status
        if required_failed:
            status = QualityGateStatus.FAILED
            passed = False
        elif warning_count > 0:
            status = QualityGateStatus.WARNING
            passed = True  # Warnings don't block
        else:
            status = QualityGateStatus.PASSED
            passed = True

        # Calculate summary
        passed_count = sum(1 for cr in condition_results if cr.passed)
        failed_count = len(condition_results) - passed_count

        summary = self._generate_summary(status, passed_count, failed_count, metrics)

        duration_ms = (time.time() - start_time) * 1000

        # Generate badge
        badge_url, badge_markdown = self._generate_badge(status, metrics, config)

        result = QualityGateResult(
            status=status,
            gate_name=config.name,
            passed=passed,
            summary=summary,
            conditions_passed=passed_count,
            conditions_failed=failed_count,
            conditions_warning=warning_count,
            condition_results=condition_results,
            metrics={name: QualityMetric(name=name, value=value) for name, value in metrics.items()},
            files_analyzed=int(metrics.get("files_analyzed", 0)),
            total_issues=int(metrics.get("total_issues", 0)),
            critical_issues=int(metrics.get("critical_issues", 0)),
            security_issues=int(metrics.get("security_issues", 0)),
            new_issues=int(metrics.get("new_issues", 0)),
            quality_score=metrics.get("quality_score", 0.0),
            completed_at=datetime.utcnow(),
            duration_ms=duration_ms,
            badge_url=badge_url,
            badge_markdown=badge_markdown,
        )

        return result

    def _collect_metrics(
        self,
        analysis_result: AnalysisResult | None,
        code_review: CodeReview | None,
        base_metrics: dict[str, float] | None,
    ) -> dict[str, float]:
        """Collect metrics from analysis results."""
        metrics: dict[str, float] = {}

        if analysis_result:
            metrics["total_issues"] = len(analysis_result.issues)
            metrics["error_count"] = analysis_result.error_count
            metrics["warning_count"] = analysis_result.warning_count

            # Count by category
            metrics["security_issues"] = len([
                i for i in analysis_result.issues
                if i.category == IssueCategory.SECURITY
            ])

            # Count by severity
            metrics["critical_issues"] = len([
                i for i in analysis_result.issues
                if i.severity == IssueSeverity.ERROR
            ])

            # Get from analysis metrics
            if analysis_result.metrics:
                metrics["files_analyzed"] = analysis_result.metrics.get("files_analyzed", 1)
                metrics["code_lines"] = analysis_result.metrics.get("code_lines", 0)

        if code_review:
            metrics["review_quality_score"] = code_review.overall_quality
            metrics["review_comments"] = len(code_review.comments)
            metrics["review_smells"] = len(code_review.smells)

            # Count security issues from review
            security_comments = len([
                c for c in code_review.comments
                if c.category == ReviewCategory.SECURITY
            ])
            metrics["security_issues"] = max(
                metrics.get("security_issues", 0),
                security_comments
            )

            # Count critical from review
            critical_comments = len([
                c for c in code_review.comments
                if c.priority == ReviewPriority.CRITICAL
            ])
            metrics["critical_issues"] = max(
                metrics.get("critical_issues", 0),
                critical_comments
            )

        # Calculate quality score if not provided
        if "quality_score" not in metrics:
            metrics["quality_score"] = self._calculate_quality_score(metrics)

        # Calculate new issues if base provided
        if base_metrics:
            base_total = base_metrics.get("total_issues", 0)
            current_total = metrics.get("total_issues", 0)
            metrics["new_issues"] = max(0, current_total - base_total)
        else:
            metrics["new_issues"] = metrics.get("total_issues", 0)

        return metrics

    def _calculate_quality_score(self, metrics: dict[str, float]) -> float:
        """Calculate a quality score from 0-10 based on metrics."""
        score = 10.0

        # Deduct for issues
        total_issues = metrics.get("total_issues", 0)
        if total_issues > 0:
            score -= min(3.0, total_issues * 0.1)

        # Heavy deduction for critical/security
        critical = metrics.get("critical_issues", 0)
        security = metrics.get("security_issues", 0)
        score -= critical * 1.0
        score -= security * 1.5

        # Use review score if available
        review_score = metrics.get("review_quality_score")
        if review_score is not None:
            score = (score + review_score) / 2

        return max(0.0, min(10.0, score))

    def _evaluate_condition(
        self,
        condition: Any,  # GateCondition
        metrics: dict[str, float],
    ) -> ConditionResult:
        """Evaluate a single condition against metrics."""
        all_passed = True
        messages: list[str] = []

        for threshold in condition.thresholds:
            metric_value = metrics.get(threshold.metric, 0)
            passed = self._check_threshold(metric_value, threshold)

            if not passed:
                all_passed = False
                msg = threshold.message or f"{threshold.metric} threshold breached"
                messages.append(f"{msg} (actual: {metric_value}, threshold: {threshold.operator.value} {threshold.value})")

        if all_passed:
            message = f"{condition.name}: All thresholds met"
        else:
            message = "; ".join(messages)

        return ConditionResult(
            condition_name=condition.name,
            passed=all_passed,
            required=condition.required,
            message=message,
        )

    def _check_threshold(self, value: float, threshold: MetricThreshold) -> bool:
        """Check if a value meets a threshold."""
        ops = {
            ThresholdOperator.LESS_THAN: lambda v, t: v < t,
            ThresholdOperator.LESS_THAN_OR_EQUAL: lambda v, t: v <= t,
            ThresholdOperator.GREATER_THAN: lambda v, t: v > t,
            ThresholdOperator.GREATER_THAN_OR_EQUAL: lambda v, t: v >= t,
            ThresholdOperator.EQUAL: lambda v, t: v == t,
            ThresholdOperator.NOT_EQUAL: lambda v, t: v != t,
        }

        check_fn = ops.get(threshold.operator)
        if check_fn:
            return check_fn(value, threshold.value)
        return True

    def _generate_summary(
        self,
        status: QualityGateStatus,
        passed: int,
        failed: int,
        metrics: dict[str, float],
    ) -> str:
        """Generate a human-readable summary."""
        if status == QualityGateStatus.PASSED:
            return f"Quality gate passed! All {passed} conditions met."
        elif status == QualityGateStatus.WARNING:
            return f"Quality gate passed with warnings. {passed} conditions passed, {failed} warnings."
        elif status == QualityGateStatus.FAILED:
            critical = int(metrics.get("critical_issues", 0))
            security = int(metrics.get("security_issues", 0))
            parts = [f"Quality gate failed. {failed} conditions not met."]
            if critical > 0:
                parts.append(f"{critical} critical issues found.")
            if security > 0:
                parts.append(f"{security} security issues found.")
            return " ".join(parts)
        else:
            return f"Quality gate {status.value}."

    def _generate_badge(
        self,
        status: QualityGateStatus,
        metrics: dict[str, float],
        config: QualityGateConfig,
    ) -> tuple[str | None, str | None]:
        """Generate badge URL and markdown."""
        if not config.generate_badge:
            return None, None

        # Status badge
        color = {
            QualityGateStatus.PASSED: "brightgreen",
            QualityGateStatus.WARNING: "yellow",
            QualityGateStatus.FAILED: "red",
            QualityGateStatus.ERROR: "red",
            QualityGateStatus.SKIPPED: "lightgrey",
        }.get(status, "lightgrey")

        score = metrics.get("quality_score", 0)
        label = "NexusAI"
        message = f"{score:.1f}/10"

        # Using shields.io
        style = config.badge_style
        badge_url = f"https://img.shields.io/badge/{label}-{message}-{color}?style={style}"
        badge_markdown = f"![NexusAI Quality Gate]({badge_url})"

        return badge_url, badge_markdown

    async def evaluate_pr(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        config: QualityGateConfig | None = None,
    ) -> QualityGateResult:
        """Evaluate quality gate for a PR (fetches data from services).

        This would integrate with the code review service to get PR analysis.
        """
        # This would be implemented to:
        # 1. Fetch PR diff using code_review service
        # 2. Run analysis
        # 3. Evaluate quality gate
        # For now, return a placeholder that indicates the PR needs to be analyzed

        return QualityGateResult(
            status=QualityGateStatus.ERROR,
            gate_name=config.name if config else "default",
            passed=False,
            summary=f"PR {owner}/{repo}#{pr_number} needs to be analyzed first. Use the analyze endpoint.",
        )


def get_quality_gate_service(base_url: str | None = None) -> QualityGateService:
    """Get or create the quality gate service singleton."""
    global _quality_gate_service

    if _quality_gate_service is None:
        _quality_gate_service = QualityGateService(base_url=base_url)

    return _quality_gate_service
