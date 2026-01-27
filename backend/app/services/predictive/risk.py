"""Risk Scorer - Deployment and change risk assessment."""

from datetime import datetime, timedelta
from typing import Any

from app.services.predictive.models import (
    RiskAssessment,
    RiskFactor,
    RiskLevel,
)


class RiskScorer:
    """Scores risk for deployments and changes.

    Analyzes various factors to provide a comprehensive risk assessment.
    """

    def __init__(self):
        """Initialize risk scorer."""
        # Factor weights (should sum to ~1.0)
        self._weights = {
            "change_size": 0.15,
            "change_type": 0.15,
            "test_coverage": 0.15,
            "author_experience": 0.10,
            "time_of_day": 0.05,
            "recent_incidents": 0.15,
            "affected_services": 0.10,
            "rollback_capability": 0.10,
            "monitoring_coverage": 0.05,
        }

    def assess_deployment_risk(
        self,
        deployment: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> RiskAssessment:
        """Assess risk for a deployment.

        Args:
            deployment: Deployment information
            context: Additional context (team metrics, history, etc.)

        Returns:
            Risk assessment with factors and recommendations
        """
        context = context or {}
        factors = []

        # Assess each risk factor
        factors.append(self._assess_change_size(deployment))
        factors.append(self._assess_change_type(deployment))
        factors.append(self._assess_test_coverage(deployment, context))
        factors.append(self._assess_author_experience(deployment, context))
        factors.append(self._assess_timing(deployment))
        factors.append(self._assess_recent_incidents(context))
        factors.append(self._assess_affected_services(deployment))
        factors.append(self._assess_rollback_capability(deployment, context))
        factors.append(self._assess_monitoring(deployment, context))

        # Calculate weighted overall score
        overall_score = sum(
            f.score * self._weights.get(f.name, 0.1)
            for f in factors
        ) / sum(self._weights.get(f.name, 0.1) for f in factors)

        # Determine risk level
        level = self._score_to_level(overall_score)

        # Generate recommendations
        recommendations = self._generate_recommendations(factors, level)

        # Create summary
        summary = self._generate_summary(deployment, level, factors)

        return RiskAssessment(
            overall_score=round(overall_score, 1),
            level=level,
            factors=factors,
            summary=summary,
            recommendations=recommendations,
            context={
                "deployment_id": deployment.get("id"),
                "commit": deployment.get("commit"),
                "target_environment": deployment.get("environment"),
            },
        )

    def assess_pr_risk(
        self,
        pr: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> RiskAssessment:
        """Assess risk for merging a pull request.

        Args:
            pr: Pull request information
            context: Additional context

        Returns:
            Risk assessment
        """
        context = context or {}
        factors = []

        # PR-specific factors
        factors.append(self._assess_pr_size(pr))
        factors.append(self._assess_pr_complexity(pr))
        factors.append(self._assess_pr_coverage(pr, context))
        factors.append(self._assess_pr_reviews(pr))
        factors.append(self._assess_pr_conflicts(pr))
        factors.append(self._assess_pr_age(pr))

        # Calculate score
        overall_score = sum(f.score for f in factors) / len(factors)
        level = self._score_to_level(overall_score)

        return RiskAssessment(
            overall_score=round(overall_score, 1),
            level=level,
            factors=factors,
            summary=self._generate_pr_summary(pr, level),
            recommendations=self._generate_pr_recommendations(factors),
            context={"pr_number": pr.get("number")},
        )

    def _assess_change_size(self, deployment: dict[str, Any]) -> RiskFactor:
        """Assess risk from change size."""
        lines_changed = deployment.get("lines_changed", 0)
        files_changed = deployment.get("files_changed", 0)

        # Score based on size
        if lines_changed < 100 and files_changed < 5:
            score = 2
            desc = "Small change with minimal footprint"
        elif lines_changed < 500 and files_changed < 15:
            score = 4
            desc = "Medium-sized change"
        elif lines_changed < 1000 and files_changed < 30:
            score = 6
            desc = "Large change requiring careful review"
        elif lines_changed < 2000:
            score = 8
            desc = "Very large change with high risk"
        else:
            score = 10
            desc = "Massive change, consider breaking down"

        return RiskFactor(
            name="change_size",
            category="change",
            score=score,
            weight=self._weights["change_size"],
            description=desc,
            mitigations=[
                "Break into smaller deployments",
                "Deploy incrementally with feature flags",
            ] if score > 5 else [],
        )

    def _assess_change_type(self, deployment: dict[str, Any]) -> RiskFactor:
        """Assess risk from type of change."""
        change_types = deployment.get("change_types", [])

        # Risk levels for different change types
        high_risk = {"database", "security", "authentication", "payment", "infrastructure"}
        medium_risk = {"api", "configuration", "integration"}

        has_high_risk = any(t in high_risk for t in change_types)
        has_medium_risk = any(t in medium_risk for t in change_types)

        if has_high_risk:
            score = 8
            desc = f"High-risk change types: {[t for t in change_types if t in high_risk]}"
        elif has_medium_risk:
            score = 5
            desc = f"Medium-risk change types: {[t for t in change_types if t in medium_risk]}"
        else:
            score = 2
            desc = "Low-risk change type"

        return RiskFactor(
            name="change_type",
            category="change",
            score=score,
            weight=self._weights["change_type"],
            description=desc,
            mitigations=[
                "Ensure thorough testing of affected areas",
                "Have incident response ready",
                "Consider staged rollout",
            ] if score > 5 else [],
        )

    def _assess_test_coverage(
        self,
        deployment: dict[str, Any],
        context: dict[str, Any],
    ) -> RiskFactor:
        """Assess risk from test coverage."""
        coverage = deployment.get("test_coverage", context.get("test_coverage", 0))
        tests_passed = deployment.get("tests_passed", True)

        if not tests_passed:
            return RiskFactor(
                name="test_coverage",
                category="quality",
                score=10,
                weight=self._weights["test_coverage"],
                description="Tests are failing - deployment blocked",
                mitigations=["Fix failing tests before deploying"],
            )

        if coverage >= 80:
            score = 2
            desc = f"Good test coverage ({coverage}%)"
        elif coverage >= 60:
            score = 4
            desc = f"Acceptable test coverage ({coverage}%)"
        elif coverage >= 40:
            score = 6
            desc = f"Low test coverage ({coverage}%)"
        else:
            score = 8
            desc = f"Insufficient test coverage ({coverage}%)"

        return RiskFactor(
            name="test_coverage",
            category="quality",
            score=score,
            weight=self._weights["test_coverage"],
            description=desc,
            mitigations=[
                "Add tests for new code",
                "Run manual testing for uncovered areas",
            ] if score > 4 else [],
        )

    def _assess_author_experience(
        self,
        deployment: dict[str, Any],
        context: dict[str, Any],
    ) -> RiskFactor:
        """Assess risk based on author's experience."""
        author = deployment.get("author", "")
        author_stats = context.get("author_stats", {}).get(author, {})

        commits_last_90_days = author_stats.get("commits_90d", 50)
        incident_rate = author_stats.get("incident_rate", 0)

        if commits_last_90_days > 100 and incident_rate < 0.05:
            score = 2
            desc = "Experienced author with good track record"
        elif commits_last_90_days > 30:
            score = 4
            desc = "Author has moderate experience"
        elif commits_last_90_days > 10:
            score = 6
            desc = "Author is relatively new"
        else:
            score = 7
            desc = "Author has limited history in codebase"

        return RiskFactor(
            name="author_experience",
            category="team",
            score=score,
            weight=self._weights["author_experience"],
            description=desc,
            mitigations=[
                "Ensure senior review",
                "Pair with experienced team member",
            ] if score > 5 else [],
        )

    def _assess_timing(self, deployment: dict[str, Any]) -> RiskFactor:
        """Assess risk from deployment timing."""
        deploy_time = deployment.get("scheduled_time", datetime.utcnow())
        if isinstance(deploy_time, str):
            deploy_time = datetime.fromisoformat(deploy_time)

        hour = deploy_time.hour
        day = deploy_time.weekday()

        # Friday afternoon/evening and weekends are higher risk
        is_friday_pm = day == 4 and hour >= 14
        is_weekend = day >= 5
        is_after_hours = hour < 9 or hour >= 18

        if is_friday_pm or is_weekend:
            score = 8
            desc = "Deploying on Friday evening or weekend is risky"
        elif is_after_hours:
            score = 6
            desc = "After-hours deployment with limited support availability"
        elif hour >= 14:
            score = 4
            desc = "Afternoon deployment"
        else:
            score = 2
            desc = "Optimal deployment window (morning on weekday)"

        return RiskFactor(
            name="time_of_day",
            category="operational",
            score=score,
            weight=self._weights["time_of_day"],
            description=desc,
            mitigations=[
                "Reschedule to business hours",
                "Ensure on-call coverage",
            ] if score > 5 else [],
        )

    def _assess_recent_incidents(self, context: dict[str, Any]) -> RiskFactor:
        """Assess risk from recent incident history."""
        incidents_7d = context.get("incidents_last_7_days", 0)
        active_incidents = context.get("active_incidents", 0)

        if active_incidents > 0:
            score = 9
            desc = f"Active incident in progress ({active_incidents} open)"
        elif incidents_7d >= 3:
            score = 7
            desc = f"Multiple recent incidents ({incidents_7d} in last 7 days)"
        elif incidents_7d >= 1:
            score = 5
            desc = f"Recent incident activity ({incidents_7d} in last 7 days)"
        else:
            score = 2
            desc = "No recent incidents"

        return RiskFactor(
            name="recent_incidents",
            category="operational",
            score=score,
            weight=self._weights["recent_incidents"],
            description=desc,
            mitigations=[
                "Resolve active incidents before deploying",
                "Conduct post-mortem before new changes",
            ] if score > 5 else [],
        )

    def _assess_affected_services(self, deployment: dict[str, Any]) -> RiskFactor:
        """Assess risk from number of affected services."""
        services = deployment.get("affected_services", [])
        critical_services = deployment.get("critical_services", [])

        has_critical = any(s in critical_services for s in services)
        count = len(services)

        if has_critical:
            score = 8
            desc = f"Affects critical services: {[s for s in services if s in critical_services]}"
        elif count > 5:
            score = 7
            desc = f"Affects many services ({count})"
        elif count > 2:
            score = 5
            desc = f"Affects multiple services ({count})"
        else:
            score = 2
            desc = f"Limited service impact ({count} services)"

        return RiskFactor(
            name="affected_services",
            category="blast_radius",
            score=score,
            weight=self._weights["affected_services"],
            description=desc,
            mitigations=[
                "Deploy to non-critical services first",
                "Use canary deployment",
            ] if score > 5 else [],
        )

    def _assess_rollback_capability(
        self,
        deployment: dict[str, Any],
        context: dict[str, Any],
    ) -> RiskFactor:
        """Assess rollback readiness."""
        has_rollback = deployment.get("rollback_ready", True)
        db_migration = deployment.get("has_db_migration", False)
        migration_reversible = deployment.get("migration_reversible", True)

        if not has_rollback:
            score = 9
            desc = "No rollback mechanism available"
        elif db_migration and not migration_reversible:
            score = 8
            desc = "Includes irreversible database migration"
        elif db_migration:
            score = 5
            desc = "Includes reversible database migration"
        else:
            score = 2
            desc = "Clean rollback available"

        return RiskFactor(
            name="rollback_capability",
            category="safety",
            score=score,
            weight=self._weights["rollback_capability"],
            description=desc,
            mitigations=[
                "Create rollback plan",
                "Test rollback procedure",
                "Consider blue-green deployment",
            ] if score > 5 else [],
        )

    def _assess_monitoring(
        self,
        deployment: dict[str, Any],
        context: dict[str, Any],
    ) -> RiskFactor:
        """Assess monitoring and alerting coverage."""
        has_monitoring = deployment.get("monitoring_enabled", True)
        has_alerts = context.get("alerts_configured", True)

        if not has_monitoring:
            score = 8
            desc = "No monitoring for affected services"
        elif not has_alerts:
            score = 6
            desc = "Monitoring exists but alerts not configured"
        else:
            score = 2
            desc = "Monitoring and alerts in place"

        return RiskFactor(
            name="monitoring_coverage",
            category="observability",
            score=score,
            weight=self._weights["monitoring_coverage"],
            description=desc,
            mitigations=[
                "Set up dashboards for key metrics",
                "Configure alerts for error rates and latency",
            ] if score > 4 else [],
        )

    # PR-specific assessments

    def _assess_pr_size(self, pr: dict[str, Any]) -> RiskFactor:
        """Assess PR size risk."""
        additions = pr.get("additions", 0)
        deletions = pr.get("deletions", 0)
        total = additions + deletions

        if total < 200:
            score = 2
        elif total < 500:
            score = 4
        elif total < 1000:
            score = 6
        else:
            score = 8

        return RiskFactor(
            name="pr_size",
            category="change",
            score=score,
            description=f"PR has {total} lines changed (+{additions}/-{deletions})",
        )

    def _assess_pr_complexity(self, pr: dict[str, Any]) -> RiskFactor:
        """Assess PR complexity."""
        files_changed = pr.get("files_changed", 0)
        commits = pr.get("commit_count", 1)

        complexity = files_changed / max(commits, 1)

        if complexity < 3:
            score = 2
        elif complexity < 5:
            score = 4
        elif complexity < 10:
            score = 6
        else:
            score = 8

        return RiskFactor(
            name="pr_complexity",
            category="change",
            score=score,
            description=f"Complexity score: {complexity:.1f} files per commit",
        )

    def _assess_pr_coverage(
        self,
        pr: dict[str, Any],
        context: dict[str, Any],
    ) -> RiskFactor:
        """Assess test coverage of PR changes."""
        coverage_delta = pr.get("coverage_delta", 0)
        new_code_coverage = pr.get("new_code_coverage", context.get("test_coverage", 70))

        if coverage_delta < -5:
            score = 7
            desc = f"Coverage decreased by {abs(coverage_delta)}%"
        elif new_code_coverage < 50:
            score = 6
            desc = f"New code has low coverage ({new_code_coverage}%)"
        elif coverage_delta > 0:
            score = 2
            desc = f"Coverage improved by {coverage_delta}%"
        else:
            score = 4
            desc = "Coverage is stable"

        return RiskFactor(
            name="pr_coverage",
            category="quality",
            score=score,
            description=desc,
        )

    def _assess_pr_reviews(self, pr: dict[str, Any]) -> RiskFactor:
        """Assess review status."""
        approvals = pr.get("approvals", 0)
        changes_requested = pr.get("changes_requested", 0)

        if changes_requested > 0:
            score = 8
            desc = f"Changes requested by {changes_requested} reviewer(s)"
        elif approvals == 0:
            score = 6
            desc = "No approvals yet"
        elif approvals == 1:
            score = 4
            desc = "One approval received"
        else:
            score = 2
            desc = f"{approvals} approvals received"

        return RiskFactor(
            name="pr_reviews",
            category="quality",
            score=score,
            description=desc,
        )

    def _assess_pr_conflicts(self, pr: dict[str, Any]) -> RiskFactor:
        """Assess merge conflict status."""
        has_conflicts = pr.get("has_conflicts", False)

        if has_conflicts:
            return RiskFactor(
                name="pr_conflicts",
                category="integration",
                score=9,
                description="Has merge conflicts that must be resolved",
            )

        return RiskFactor(
            name="pr_conflicts",
            category="integration",
            score=1,
            description="No merge conflicts",
        )

    def _assess_pr_age(self, pr: dict[str, Any]) -> RiskFactor:
        """Assess PR age."""
        created_at = pr.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

        if created_at:
            age_days = (datetime.utcnow() - created_at.replace(tzinfo=None)).days
        else:
            age_days = 0

        if age_days > 30:
            score = 7
            desc = f"PR is {age_days} days old - may be stale"
        elif age_days > 14:
            score = 5
            desc = f"PR is {age_days} days old"
        else:
            score = 2
            desc = f"PR is {age_days} days old - relatively fresh"

        return RiskFactor(
            name="pr_age",
            category="freshness",
            score=score,
            description=desc,
        )

    def _score_to_level(self, score: float) -> RiskLevel:
        """Convert numeric score to risk level."""
        if score >= 8:
            return RiskLevel.CRITICAL
        elif score >= 6:
            return RiskLevel.HIGH
        elif score >= 4:
            return RiskLevel.MEDIUM
        elif score >= 2:
            return RiskLevel.LOW
        else:
            return RiskLevel.MINIMAL

    def _generate_recommendations(
        self,
        factors: list[RiskFactor],
        level: RiskLevel,
    ) -> list[str]:
        """Generate recommendations based on risk factors."""
        recommendations = []

        # Collect mitigations from high-risk factors
        for factor in sorted(factors, key=lambda f: f.score, reverse=True):
            if factor.score >= 6:
                recommendations.extend(factor.mitigations)

        # Add general recommendations based on level
        if level == RiskLevel.CRITICAL:
            recommendations.insert(0, "Consider postponing this deployment")
            recommendations.append("Ensure incident response team is available")
        elif level == RiskLevel.HIGH:
            recommendations.insert(0, "Proceed with caution and close monitoring")
            recommendations.append("Have rollback plan ready")

        # Deduplicate
        return list(dict.fromkeys(recommendations))[:10]

    def _generate_summary(
        self,
        deployment: dict[str, Any],
        level: RiskLevel,
        factors: list[RiskFactor],
    ) -> str:
        """Generate risk assessment summary."""
        high_risk_factors = [f for f in factors if f.score >= 7]

        if level == RiskLevel.CRITICAL:
            summary = "This deployment carries critical risk. "
        elif level == RiskLevel.HIGH:
            summary = "This deployment has elevated risk. "
        elif level == RiskLevel.MEDIUM:
            summary = "This deployment has moderate risk. "
        else:
            summary = "This deployment appears to be low risk. "

        if high_risk_factors:
            concerns = ", ".join(f.name.replace("_", " ") for f in high_risk_factors[:3])
            summary += f"Main concerns: {concerns}."

        return summary

    def _generate_pr_summary(self, pr: dict[str, Any], level: RiskLevel) -> str:
        """Generate PR risk summary."""
        title = pr.get("title", "Unknown PR")

        level_text = {
            RiskLevel.CRITICAL: "critical risk",
            RiskLevel.HIGH: "high risk",
            RiskLevel.MEDIUM: "moderate risk",
            RiskLevel.LOW: "low risk",
            RiskLevel.MINIMAL: "minimal risk",
        }

        return f"PR '{title}' has {level_text.get(level, 'unknown')} for merging."

    def _generate_pr_recommendations(self, factors: list[RiskFactor]) -> list[str]:
        """Generate PR-specific recommendations."""
        recommendations = []

        for factor in factors:
            if factor.score >= 6:
                if factor.name == "pr_size":
                    recommendations.append("Consider breaking into smaller PRs")
                elif factor.name == "pr_reviews":
                    recommendations.append("Request additional reviews")
                elif factor.name == "pr_coverage":
                    recommendations.append("Add tests for new code")
                elif factor.name == "pr_conflicts":
                    recommendations.append("Resolve merge conflicts")
                elif factor.name == "pr_age":
                    recommendations.append("Rebase and update the branch")

        return recommendations
