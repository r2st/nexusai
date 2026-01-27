"""Bottleneck Detector - Identifies process bottlenecks."""

from datetime import datetime, timedelta
from typing import Any

from app.services.predictive.models import (
    Bottleneck,
    BottleneckType,
    RiskLevel,
    TimeSeries,
)


class BottleneckDetector:
    """Detects bottlenecks in the development process.

    Analyzes various metrics to identify slowdowns and constraints.
    """

    def __init__(self):
        """Initialize bottleneck detector."""
        # Thresholds for bottleneck detection
        self._thresholds = {
            "code_review_time_hours": 24,
            "pr_size_lines": 500,
            "deployment_frequency_days": 7,
            "test_coverage_min": 60,
            "merge_conflict_rate": 0.2,
            "build_failure_rate": 0.1,
            "incident_frequency_per_week": 2,
        }

    def detect_all(
        self,
        metrics: dict[str, Any],
        time_series: dict[str, TimeSeries] | None = None,
    ) -> list[Bottleneck]:
        """Detect all bottlenecks from available metrics.

        Args:
            metrics: Current metric values
            time_series: Historical time series for trend analysis

        Returns:
            List of detected bottlenecks
        """
        bottlenecks = []

        # Check each bottleneck type
        bottlenecks.extend(self._detect_code_review_bottleneck(metrics))
        bottlenecks.extend(self._detect_deployment_bottleneck(metrics))
        bottlenecks.extend(self._detect_testing_bottleneck(metrics))
        bottlenecks.extend(self._detect_merge_conflicts(metrics))
        bottlenecks.extend(self._detect_resource_bottleneck(metrics))
        bottlenecks.extend(self._detect_technical_debt(metrics))

        # Sort by impact score
        bottlenecks.sort(key=lambda b: b.impact_score, reverse=True)

        return bottlenecks

    def _detect_code_review_bottleneck(
        self,
        metrics: dict[str, Any],
    ) -> list[Bottleneck]:
        """Detect code review bottlenecks."""
        bottlenecks = []

        # Long review times
        review_time = metrics.get("avg_review_time_hours", 0)
        if review_time > self._thresholds["code_review_time_hours"]:
            severity = self._calculate_severity(
                review_time,
                self._thresholds["code_review_time_hours"],
                [48, 72, 96],
            )

            bottlenecks.append(Bottleneck(
                type=BottleneckType.CODE_REVIEW,
                severity=severity,
                location="Pull Request Reviews",
                description=f"Average code review time is {review_time:.1f} hours, "
                           f"exceeding the {self._thresholds['code_review_time_hours']} hour threshold",
                impact_score=self._severity_to_score(severity),
                affected_metrics=["lead_time", "cycle_time", "developer_velocity"],
                root_causes=[
                    "Limited reviewer availability",
                    "Large PR sizes requiring extensive review",
                    "Unclear code ownership",
                    "No SLAs for review turnaround",
                ],
                suggested_actions=[
                    "Implement reviewer rotation schedule",
                    "Set maximum PR size guidelines (< 500 lines)",
                    "Define clear CODEOWNERS file",
                    "Establish review SLAs (24-48 hours)",
                ],
                evidence={"avg_review_time_hours": review_time},
            ))

        # Large PRs
        avg_pr_size = metrics.get("avg_pr_size_lines", 0)
        if avg_pr_size > self._thresholds["pr_size_lines"]:
            severity = self._calculate_severity(
                avg_pr_size,
                self._thresholds["pr_size_lines"],
                [750, 1000, 1500],
            )

            bottlenecks.append(Bottleneck(
                type=BottleneckType.CODE_REVIEW,
                severity=severity,
                location="Pull Request Size",
                description=f"Average PR size is {avg_pr_size} lines, making reviews difficult",
                impact_score=self._severity_to_score(severity) * 0.8,
                affected_metrics=["review_time", "review_quality", "defect_escape_rate"],
                root_causes=[
                    "Infrequent commits",
                    "Lack of feature flags for incremental releases",
                    "Monolithic architecture",
                ],
                suggested_actions=[
                    "Encourage smaller, focused PRs",
                    "Use feature flags for partial implementations",
                    "Implement stacked PRs workflow",
                    "Break down tasks during planning",
                ],
                evidence={"avg_pr_size_lines": avg_pr_size},
            ))

        # Review queue depth
        pending_reviews = metrics.get("pending_review_count", 0)
        if pending_reviews > 10:
            bottlenecks.append(Bottleneck(
                type=BottleneckType.CODE_REVIEW,
                severity=RiskLevel.MEDIUM if pending_reviews < 20 else RiskLevel.HIGH,
                location="Review Queue",
                description=f"{pending_reviews} PRs waiting for review",
                impact_score=min(10, pending_reviews / 2),
                affected_metrics=["lead_time", "developer_satisfaction"],
                root_causes=["Insufficient reviewers", "Review paralysis"],
                suggested_actions=[
                    "Allocate dedicated review time slots",
                    "Use async code review tools",
                    "Prioritize reviews by urgency",
                ],
                evidence={"pending_review_count": pending_reviews},
            ))

        return bottlenecks

    def _detect_deployment_bottleneck(
        self,
        metrics: dict[str, Any],
    ) -> list[Bottleneck]:
        """Detect deployment bottlenecks."""
        bottlenecks = []

        # Low deployment frequency
        deploy_freq_days = metrics.get("deployment_frequency_days", 0)
        if deploy_freq_days > self._thresholds["deployment_frequency_days"]:
            severity = self._calculate_severity(
                deploy_freq_days,
                self._thresholds["deployment_frequency_days"],
                [14, 30, 60],
            )

            bottlenecks.append(Bottleneck(
                type=BottleneckType.DEPLOYMENT,
                severity=severity,
                location="Release Pipeline",
                description=f"Deployments occur only every {deploy_freq_days:.1f} days on average",
                impact_score=self._severity_to_score(severity),
                affected_metrics=["deployment_frequency", "change_lead_time", "time_to_market"],
                root_causes=[
                    "Manual deployment processes",
                    "Lack of CI/CD automation",
                    "Change approval bottlenecks",
                    "Fear of deployments",
                ],
                suggested_actions=[
                    "Implement continuous deployment",
                    "Automate deployment pipeline",
                    "Use blue-green or canary deployments",
                    "Reduce deployment ceremony",
                ],
                evidence={"deployment_frequency_days": deploy_freq_days},
            ))

        # Build failures
        build_failure_rate = metrics.get("build_failure_rate", 0)
        if build_failure_rate > self._thresholds["build_failure_rate"]:
            severity = self._calculate_severity(
                build_failure_rate,
                self._thresholds["build_failure_rate"],
                [0.2, 0.3, 0.5],
            )

            bottlenecks.append(Bottleneck(
                type=BottleneckType.DEPLOYMENT,
                severity=severity,
                location="Build Pipeline",
                description=f"Build failure rate is {build_failure_rate:.1%}",
                impact_score=self._severity_to_score(severity),
                affected_metrics=["deployment_frequency", "developer_productivity"],
                root_causes=[
                    "Flaky tests",
                    "Environment inconsistencies",
                    "Missing pre-commit checks",
                ],
                suggested_actions=[
                    "Fix or quarantine flaky tests",
                    "Use containerized builds",
                    "Implement pre-commit hooks",
                    "Monitor and alert on build health",
                ],
                evidence={"build_failure_rate": build_failure_rate},
            ))

        return bottlenecks

    def _detect_testing_bottleneck(
        self,
        metrics: dict[str, Any],
    ) -> list[Bottleneck]:
        """Detect testing bottlenecks."""
        bottlenecks = []

        # Low test coverage
        test_coverage = metrics.get("test_coverage_percent", 100)
        if test_coverage < self._thresholds["test_coverage_min"]:
            severity = self._calculate_severity(
                self._thresholds["test_coverage_min"] - test_coverage,
                0,
                [10, 25, 40],
            )

            bottlenecks.append(Bottleneck(
                type=BottleneckType.TESTING,
                severity=severity,
                location="Test Coverage",
                description=f"Test coverage is only {test_coverage}%, below the {self._thresholds['test_coverage_min']}% threshold",
                impact_score=self._severity_to_score(severity),
                affected_metrics=["change_failure_rate", "defect_density", "confidence_level"],
                root_causes=[
                    "Pressure to ship quickly",
                    "Legacy code without tests",
                    "Lack of testing culture",
                ],
                suggested_actions=[
                    "Enforce coverage requirements on new code",
                    "Add tests when fixing bugs",
                    "Set incremental coverage targets",
                    "Invest in testing infrastructure",
                ],
                evidence={"test_coverage_percent": test_coverage},
            ))

        # Long test execution times
        test_duration_mins = metrics.get("test_suite_duration_mins", 0)
        if test_duration_mins > 30:
            severity = RiskLevel.MEDIUM if test_duration_mins < 60 else RiskLevel.HIGH

            bottlenecks.append(Bottleneck(
                type=BottleneckType.TESTING,
                severity=severity,
                location="Test Execution",
                description=f"Test suite takes {test_duration_mins} minutes to run",
                impact_score=self._severity_to_score(severity) * 0.7,
                affected_metrics=["ci_duration", "developer_feedback_time"],
                root_causes=[
                    "Slow integration tests",
                    "No test parallelization",
                    "Excessive test data setup",
                ],
                suggested_actions=[
                    "Parallelize test execution",
                    "Use test containers for faster setup",
                    "Split tests into tiers (unit, integration, e2e)",
                    "Run slow tests on schedule, not per-commit",
                ],
                evidence={"test_suite_duration_mins": test_duration_mins},
            ))

        return bottlenecks

    def _detect_merge_conflicts(
        self,
        metrics: dict[str, Any],
    ) -> list[Bottleneck]:
        """Detect merge conflict bottlenecks."""
        bottlenecks = []

        conflict_rate = metrics.get("merge_conflict_rate", 0)
        if conflict_rate > self._thresholds["merge_conflict_rate"]:
            severity = self._calculate_severity(
                conflict_rate,
                self._thresholds["merge_conflict_rate"],
                [0.3, 0.4, 0.5],
            )

            bottlenecks.append(Bottleneck(
                type=BottleneckType.MERGE_CONFLICTS,
                severity=severity,
                location="Branch Management",
                description=f"{conflict_rate:.1%} of PRs have merge conflicts",
                impact_score=self._severity_to_score(severity),
                affected_metrics=["lead_time", "developer_productivity", "code_integration_time"],
                root_causes=[
                    "Long-lived feature branches",
                    "High code coupling",
                    "Multiple developers on same files",
                ],
                suggested_actions=[
                    "Encourage frequent merges from main",
                    "Use trunk-based development",
                    "Improve module boundaries",
                    "Coordinate work on shared files",
                ],
                evidence={"merge_conflict_rate": conflict_rate},
            ))

        return bottlenecks

    def _detect_resource_bottleneck(
        self,
        metrics: dict[str, Any],
    ) -> list[Bottleneck]:
        """Detect resource-related bottlenecks."""
        bottlenecks = []

        # High WIP (work in progress)
        wip_per_dev = metrics.get("wip_per_developer", 0)
        if wip_per_dev > 3:
            severity = RiskLevel.MEDIUM if wip_per_dev < 5 else RiskLevel.HIGH

            bottlenecks.append(Bottleneck(
                type=BottleneckType.RESOURCE,
                severity=severity,
                location="Work Distribution",
                description=f"Average WIP per developer is {wip_per_dev:.1f} items",
                impact_score=self._severity_to_score(severity),
                affected_metrics=["cycle_time", "focus_time", "quality"],
                root_causes=[
                    "Context switching",
                    "Blocked work accumulating",
                    "Overcommitment",
                ],
                suggested_actions=[
                    "Implement WIP limits",
                    "Focus on finishing over starting",
                    "Address blockers immediately",
                    "Improve sprint planning",
                ],
                evidence={"wip_per_developer": wip_per_dev},
            ))

        return bottlenecks

    def _detect_technical_debt(
        self,
        metrics: dict[str, Any],
    ) -> list[Bottleneck]:
        """Detect technical debt bottlenecks."""
        bottlenecks = []

        # High complexity
        avg_complexity = metrics.get("avg_cyclomatic_complexity", 0)
        if avg_complexity > 15:
            severity = self._calculate_severity(avg_complexity, 15, [20, 30, 40])

            bottlenecks.append(Bottleneck(
                type=BottleneckType.TECHNICAL_DEBT,
                severity=severity,
                location="Code Complexity",
                description=f"Average cyclomatic complexity is {avg_complexity:.1f}",
                impact_score=self._severity_to_score(severity),
                affected_metrics=["maintainability", "defect_density", "onboarding_time"],
                root_causes=[
                    "Accumulated technical debt",
                    "Lack of refactoring time",
                    "Complex business logic",
                ],
                suggested_actions=[
                    "Allocate time for refactoring",
                    "Apply boy scout rule",
                    "Extract complex logic into smaller functions",
                    "Add complexity checks to CI",
                ],
                evidence={"avg_cyclomatic_complexity": avg_complexity},
            ))

        # High duplication
        duplication_percent = metrics.get("code_duplication_percent", 0)
        if duplication_percent > 10:
            severity = self._calculate_severity(duplication_percent, 10, [15, 25, 40])

            bottlenecks.append(Bottleneck(
                type=BottleneckType.TECHNICAL_DEBT,
                severity=severity,
                location="Code Duplication",
                description=f"Code duplication is at {duplication_percent:.1f}%",
                impact_score=self._severity_to_score(severity) * 0.7,
                affected_metrics=["maintainability", "bug_fix_time"],
                root_causes=[
                    "Copy-paste programming",
                    "Lack of shared utilities",
                    "Time pressure",
                ],
                suggested_actions=[
                    "Extract shared code to libraries",
                    "Use code analysis tools",
                    "Review for duplication in PRs",
                ],
                evidence={"code_duplication_percent": duplication_percent},
            ))

        return bottlenecks

    def _calculate_severity(
        self,
        value: float,
        threshold: float,
        escalation_points: list[float],
    ) -> RiskLevel:
        """Calculate severity level based on escalation points."""
        if value <= threshold:
            return RiskLevel.MINIMAL

        if value < escalation_points[0]:
            return RiskLevel.LOW
        elif value < escalation_points[1]:
            return RiskLevel.MEDIUM
        elif value < escalation_points[2]:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL

    def _severity_to_score(self, severity: RiskLevel) -> float:
        """Convert severity to numeric score."""
        mapping = {
            RiskLevel.MINIMAL: 2,
            RiskLevel.LOW: 4,
            RiskLevel.MEDIUM: 6,
            RiskLevel.HIGH: 8,
            RiskLevel.CRITICAL: 10,
        }
        return mapping.get(severity, 5)
