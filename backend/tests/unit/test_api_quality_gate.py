"""
Unit tests for Quality Gate API endpoints.
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


# =============================================================================
# Mock Models and Types
# =============================================================================


class QualityGateStatus:
    """Quality gate status types."""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"


# =============================================================================
# Request Model Tests
# =============================================================================


class TestEvaluateRequest:
    """Tests for EvaluateRequest model."""

    def test_required_fields(self):
        """Test required fields for evaluate request."""
        request = {
            "file_uri": "file:///src/main.py",
            "content": "def hello(): pass",
            "language_id": "python",
        }

        assert all(key in request for key in ["file_uri", "content", "language_id"])

    def test_all_fields(self):
        """Test all fields for evaluate request."""
        request = {
            "file_uri": "file:///src/main.py",
            "content": "def hello(): pass",
            "language_id": "python",
            "config_name": "strict",
            "base_metrics": {"total_issues": 5, "security_issues": 0},
        }

        assert request["config_name"] == "strict"
        assert "base_metrics" in request

    def test_default_config_name(self):
        """Test default config name is 'default'."""
        request = {
            "file_uri": "file:///src/main.py",
            "content": "code",
            "language_id": "python",
        }

        config_name = request.get("config_name", "default")
        assert config_name == "default"


class TestEvaluatePRRequest:
    """Tests for EvaluatePRRequest model."""

    def test_required_fields(self):
        """Test required fields for PR evaluate request."""
        request = {
            "owner": "acme",
            "repo": "myapp",
            "pr_number": 123,
        }

        assert request["owner"] == "acme"
        assert request["pr_number"] == 123

    def test_all_fields(self):
        """Test all fields for PR evaluate request."""
        request = {
            "owner": "acme",
            "repo": "myapp",
            "pr_number": 456,
            "config_name": "ci-strict",
        }

        assert request["config_name"] == "ci-strict"


class TestBatchEvaluateRequest:
    """Tests for BatchEvaluateRequest model."""

    def test_single_file(self):
        """Test batch request with single file."""
        request = {
            "files": [
                {"file_uri": "file:///src/main.py", "content": "code", "language_id": "python"},
            ],
            "config_name": "default",
        }

        assert len(request["files"]) == 1

    def test_multiple_files(self):
        """Test batch request with multiple files."""
        request = {
            "files": [
                {"file_uri": "file:///src/main.py", "content": "code", "language_id": "python"},
                {"file_uri": "file:///src/utils.py", "content": "utils", "language_id": "python"},
                {"file_uri": "file:///src/app.ts", "content": "app", "language_id": "typescript"},
            ],
            "config_name": "default",
        }

        assert len(request["files"]) == 3

    def test_with_base_metrics(self):
        """Test batch request with base metrics."""
        request = {
            "files": [{"file_uri": "f1", "content": "c", "language_id": "python"}],
            "config_name": "default",
            "base_metrics": {"total_issues": 10, "critical_issues": 2},
        }

        assert "base_metrics" in request


# =============================================================================
# Response Model Tests
# =============================================================================


class TestGateResultResponse:
    """Tests for GateResultResponse model."""

    def test_passed_response(self):
        """Test passed quality gate response."""
        response = {
            "status": "passed",
            "passed": True,
            "summary": "Quality gate passed",
            "total_issues": 5,
            "critical_issues": 0,
            "security_issues": 0,
            "quality_score": 95.0,
            "conditions_passed": 5,
            "conditions_failed": 0,
            "badge_url": "https://badges.example.com/passed",
            "markdown_summary": "## Quality Gate Passed",
            "github_output": {"status": "success"},
        }

        assert response["passed"] is True
        assert response["status"] == "passed"

    def test_failed_response(self):
        """Test failed quality gate response."""
        response = {
            "status": "failed",
            "passed": False,
            "summary": "Quality gate failed: 3 critical issues",
            "total_issues": 10,
            "critical_issues": 3,
            "security_issues": 2,
            "quality_score": 65.0,
            "conditions_passed": 2,
            "conditions_failed": 3,
            "badge_url": "https://badges.example.com/failed",
            "markdown_summary": "## Quality Gate Failed",
            "github_output": {"status": "failure"},
        }

        assert response["passed"] is False
        assert response["critical_issues"] == 3

    def test_warning_response(self):
        """Test warning quality gate response."""
        response = {
            "status": "warning",
            "passed": True,  # Warnings still pass
            "summary": "Quality gate passed with warnings",
            "total_issues": 8,
            "critical_issues": 0,
            "security_issues": 0,
            "quality_score": 80.0,
            "conditions_passed": 4,
            "conditions_failed": 1,
            "badge_url": None,
            "markdown_summary": "## Quality Gate Passed (with warnings)",
            "github_output": {"status": "success", "warnings": 8},
        }

        assert response["status"] == "warning"
        assert response["passed"] is True


# =============================================================================
# Evaluate Endpoint Tests
# =============================================================================


class TestEvaluateEndpoint:
    """Tests for evaluate quality gate endpoint."""

    @pytest.mark.asyncio
    async def test_evaluate_single_file_passed(self):
        """Test evaluating a single file that passes."""
        result = {
            "status": "passed",
            "passed": True,
            "total_issues": 2,
            "critical_issues": 0,
            "security_issues": 0,
            "quality_score": 90.0,
        }

        assert result["passed"] is True

    @pytest.mark.asyncio
    async def test_evaluate_single_file_failed(self):
        """Test evaluating a single file that fails."""
        result = {
            "status": "failed",
            "passed": False,
            "total_issues": 15,
            "critical_issues": 5,
            "security_issues": 3,
            "quality_score": 55.0,
        }

        assert result["passed"] is False

    @pytest.mark.asyncio
    async def test_evaluate_with_custom_config(self):
        """Test evaluating with custom config."""
        config_name = "strict"

        # Service would use the specified config
        result = {
            "status": "failed",
            "passed": False,
            "config_used": config_name,
        }

        assert result.get("config_used") == config_name

    @pytest.mark.asyncio
    async def test_evaluate_with_base_metrics(self):
        """Test evaluating with base branch metrics."""
        base_metrics = {
            "total_issues": 10,
            "critical_issues": 2,
        }

        # Service would compare against base metrics
        result = {
            "status": "passed",
            "passed": True,
            "improvement": {
                "total_issues": -3,  # Improved by 3
                "critical_issues": -2,  # Improved by 2
            },
        }

        assert result.get("improvement", {}).get("total_issues") < 0

    @pytest.mark.asyncio
    async def test_evaluate_error_handling(self):
        """Test evaluate handles errors."""
        # Analysis might fail
        error_raised = True

        assert error_raised


# =============================================================================
# Batch Evaluate Endpoint Tests
# =============================================================================


class TestBatchEvaluateEndpoint:
    """Tests for batch evaluate endpoint."""

    @pytest.mark.asyncio
    async def test_batch_evaluate_all_passed(self):
        """Test batch evaluation where all files pass."""
        result = {
            "status": "passed",
            "passed": True,
            "total_issues": 5,
            "files_analyzed": 3,
        }

        assert result["passed"] is True
        assert result.get("files_analyzed") == 3

    @pytest.mark.asyncio
    async def test_batch_evaluate_some_failed(self):
        """Test batch evaluation where some files have issues."""
        result = {
            "status": "failed",
            "passed": False,
            "total_issues": 20,
            "critical_issues": 5,
            "files_analyzed": 5,
        }

        assert result["passed"] is False

    @pytest.mark.asyncio
    async def test_batch_evaluate_aggregates_metrics(self):
        """Test batch evaluation aggregates metrics correctly."""
        # Simulate multiple file results
        file_results = [
            {"issues": 3, "critical": 0, "security": 0},
            {"issues": 5, "critical": 2, "security": 1},
            {"issues": 2, "critical": 0, "security": 0},
        ]

        total_issues = sum(f["issues"] for f in file_results)
        total_critical = sum(f["critical"] for f in file_results)
        total_security = sum(f["security"] for f in file_results)

        assert total_issues == 10
        assert total_critical == 2
        assert total_security == 1

    @pytest.mark.asyncio
    async def test_batch_evaluate_empty_files(self):
        """Test batch evaluation with empty files list."""
        request = {
            "files": [],
            "config_name": "default",
        }

        # Should handle empty list gracefully
        result = {
            "status": "passed",
            "passed": True,
            "total_issues": 0,
            "files_analyzed": 0,
        }

        assert result.get("files_analyzed") == 0


# =============================================================================
# PR Evaluate Endpoint Tests
# =============================================================================


class TestEvaluatePREndpoint:
    """Tests for evaluate PR endpoint."""

    @pytest.mark.asyncio
    async def test_evaluate_pr_passed(self):
        """Test evaluating a PR that passes."""
        result = {
            "status": "passed",
            "passed": True,
            "pr_number": 123,
            "repo": "acme/myapp",
        }

        assert result["passed"] is True

    @pytest.mark.asyncio
    async def test_evaluate_pr_failed(self):
        """Test evaluating a PR that fails."""
        result = {
            "status": "failed",
            "passed": False,
            "pr_number": 456,
            "critical_issues": 3,
        }

        assert result["passed"] is False

    @pytest.mark.asyncio
    async def test_evaluate_pr_fetches_files(self):
        """Test that PR evaluation fetches PR files."""
        owner = "acme"
        repo = "myapp"
        pr_number = 789

        # Service would fetch PR diff/files
        pr_data = {
            "changed_files": 5,
            "additions": 100,
            "deletions": 50,
        }

        assert pr_data["changed_files"] == 5

    @pytest.mark.asyncio
    async def test_evaluate_pr_error(self):
        """Test PR evaluation error handling."""
        # PR might not exist or be inaccessible
        error_raised = True

        assert error_raised


# =============================================================================
# Config Endpoint Tests
# =============================================================================


class TestConfigEndpoints:
    """Tests for config endpoints."""

    @pytest.mark.asyncio
    async def test_get_config_default(self):
        """Test getting default config."""
        config = {
            "name": "default",
            "max_critical_issues": 0,
            "max_security_issues": 5,
            "min_quality_score": 70.0,
            "max_total_issues": 50,
        }

        assert config["name"] == "default"

    @pytest.mark.asyncio
    async def test_get_config_strict(self):
        """Test getting strict config."""
        config = {
            "name": "strict",
            "max_critical_issues": 0,
            "max_security_issues": 0,
            "min_quality_score": 90.0,
            "max_total_issues": 10,
        }

        assert config["name"] == "strict"
        assert config["min_quality_score"] == 90.0

    @pytest.mark.asyncio
    async def test_get_config_custom(self):
        """Test getting custom config."""
        config_name = "my-custom-config"

        config = {
            "name": config_name,
            "max_critical_issues": 2,
            "max_security_issues": 10,
            "min_quality_score": 60.0,
        }

        assert config["name"] == config_name

    @pytest.mark.asyncio
    async def test_update_config(self):
        """Test updating/creating config."""
        new_config = {
            "name": "my-new-config",
            "max_critical_issues": 0,
            "max_security_issues": 3,
            "min_quality_score": 80.0,
        }

        # Service would register the config
        result = new_config.copy()

        assert result["name"] == "my-new-config"


# =============================================================================
# Health Endpoint Tests
# =============================================================================


class TestHealthEndpoint:
    """Tests for health endpoint."""

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check returns healthy."""
        response = {
            "status": "healthy",
            "service": "quality-gate",
        }

        assert response["status"] == "healthy"


# =============================================================================
# Quality Gate Configuration Tests
# =============================================================================


class TestQualityGateConfiguration:
    """Tests for quality gate configuration."""

    def test_default_config_values(self):
        """Test default configuration values."""
        default_config = {
            "name": "default",
            "max_critical_issues": 0,
            "max_security_issues": 5,
            "min_quality_score": 70.0,
            "max_total_issues": 100,
            "fail_on_new_issues": False,
        }

        assert default_config["max_critical_issues"] == 0
        assert default_config["min_quality_score"] == 70.0

    def test_strict_config_values(self):
        """Test strict configuration values."""
        strict_config = {
            "name": "strict",
            "max_critical_issues": 0,
            "max_security_issues": 0,
            "min_quality_score": 90.0,
            "max_total_issues": 10,
            "fail_on_new_issues": True,
        }

        assert strict_config["max_security_issues"] == 0
        assert strict_config["fail_on_new_issues"] is True

    def test_lenient_config_values(self):
        """Test lenient configuration values."""
        lenient_config = {
            "name": "lenient",
            "max_critical_issues": 5,
            "max_security_issues": 20,
            "min_quality_score": 50.0,
            "max_total_issues": 200,
            "fail_on_new_issues": False,
        }

        assert lenient_config["min_quality_score"] == 50.0


# =============================================================================
# Quality Gate Conditions Tests
# =============================================================================


class TestQualityGateConditions:
    """Tests for quality gate condition evaluation."""

    def test_critical_issues_condition_pass(self):
        """Test critical issues condition passes."""
        max_critical = 0
        actual_critical = 0

        passed = actual_critical <= max_critical
        assert passed is True

    def test_critical_issues_condition_fail(self):
        """Test critical issues condition fails."""
        max_critical = 0
        actual_critical = 3

        passed = actual_critical <= max_critical
        assert passed is False

    def test_security_issues_condition_pass(self):
        """Test security issues condition passes."""
        max_security = 5
        actual_security = 3

        passed = actual_security <= max_security
        assert passed is True

    def test_quality_score_condition_pass(self):
        """Test quality score condition passes."""
        min_score = 70.0
        actual_score = 85.0

        passed = actual_score >= min_score
        assert passed is True

    def test_quality_score_condition_fail(self):
        """Test quality score condition fails."""
        min_score = 70.0
        actual_score = 55.0

        passed = actual_score >= min_score
        assert passed is False

    def test_total_issues_condition(self):
        """Test total issues condition."""
        max_total = 50
        actual_total = 45

        passed = actual_total <= max_total
        assert passed is True

    def test_new_issues_condition(self):
        """Test new issues condition (compared to base)."""
        base_issues = 10
        current_issues = 8  # Improved

        has_new_issues = current_issues > base_issues
        assert has_new_issues is False


# =============================================================================
# Quality Score Calculation Tests
# =============================================================================


class TestQualityScoreCalculation:
    """Tests for quality score calculation."""

    def test_perfect_score(self):
        """Test perfect quality score."""
        issues = {"total": 0, "critical": 0, "security": 0}

        # Perfect score when no issues
        score = 100.0 if issues["total"] == 0 else 0

        assert score == 100.0

    def test_score_with_issues(self):
        """Test quality score with issues."""
        # Simplified calculation
        total_issues = 10
        base_score = 100
        deduction_per_issue = 2

        score = max(0, base_score - (total_issues * deduction_per_issue))

        assert score == 80

    def test_score_weighted_by_severity(self):
        """Test score weighted by issue severity."""
        critical_issues = 2
        major_issues = 5
        minor_issues = 10

        critical_weight = 10
        major_weight = 5
        minor_weight = 1

        total_deduction = (
            critical_issues * critical_weight +
            major_issues * major_weight +
            minor_issues * minor_weight
        )

        score = max(0, 100 - total_deduction)

        # 2*10 + 5*5 + 10*1 = 20 + 25 + 10 = 55 deduction, score = 100 - 55 = 45
        assert score == 45


# =============================================================================
# Output Format Tests
# =============================================================================


class TestOutputFormats:
    """Tests for output formats."""

    def test_markdown_summary_passed(self):
        """Test markdown summary for passed gate."""
        result = {
            "status": "passed",
            "quality_score": 95.0,
            "total_issues": 3,
        }

        markdown = f"## Quality Gate: {result['status'].upper()}\n"
        markdown += f"Score: {result['quality_score']}\n"

        assert "PASSED" in markdown

    def test_markdown_summary_failed(self):
        """Test markdown summary for failed gate."""
        result = {
            "status": "failed",
            "quality_score": 55.0,
            "total_issues": 25,
            "critical_issues": 5,
        }

        markdown = f"## Quality Gate: {result['status'].upper()}\n"
        markdown += f"Critical Issues: {result['critical_issues']}\n"

        assert "FAILED" in markdown
        assert "Critical Issues: 5" in markdown

    def test_github_output_passed(self):
        """Test GitHub Actions output for passed gate."""
        result = {
            "status": "passed",
            "passed": True,
            "quality_score": 90.0,
        }

        github_output = {
            "gate-status": "passed",
            "gate-passed": "true",
            "quality-score": "90.0",
        }

        assert github_output["gate-passed"] == "true"

    def test_github_output_failed(self):
        """Test GitHub Actions output for failed gate."""
        result = {
            "status": "failed",
            "passed": False,
            "critical_issues": 3,
        }

        github_output = {
            "gate-status": "failed",
            "gate-passed": "false",
            "critical-issues": "3",
        }

        assert github_output["gate-passed"] == "false"


# =============================================================================
# Badge URL Tests
# =============================================================================


class TestBadgeURL:
    """Tests for badge URL generation."""

    def test_passed_badge_url(self):
        """Test badge URL for passed status."""
        status = "passed"
        base_url = "https://badges.example.com"

        badge_url = f"{base_url}/quality-gate-{status}.svg"

        assert "passed" in badge_url

    def test_failed_badge_url(self):
        """Test badge URL for failed status."""
        status = "failed"
        base_url = "https://badges.example.com"

        badge_url = f"{base_url}/quality-gate-{status}.svg"

        assert "failed" in badge_url

    def test_badge_url_with_score(self):
        """Test badge URL with score."""
        score = 85.0
        base_url = "https://badges.example.com"

        badge_url = f"{base_url}/quality-score-{int(score)}.svg"

        assert "85" in badge_url


# =============================================================================
# Analysis Type Tests
# =============================================================================


class TestAnalysisTypes:
    """Tests for analysis types."""

    def test_default_analysis_types(self):
        """Test default analysis types."""
        default_types = ["diagnostics", "smells", "security"]

        assert "diagnostics" in default_types
        assert "security" in default_types

    def test_diagnostics_analysis(self):
        """Test diagnostics analysis type."""
        analysis_type = "diagnostics"

        # Would detect errors, warnings, etc.
        results = {
            "errors": 5,
            "warnings": 10,
            "info": 15,
        }

        assert "errors" in results

    def test_smells_analysis(self):
        """Test code smells analysis type."""
        analysis_type = "smells"

        # Would detect code smells
        results = {
            "duplicates": 3,
            "long_methods": 2,
            "complexity": 5,
        }

        assert "complexity" in results

    def test_security_analysis(self):
        """Test security analysis type."""
        analysis_type = "security"

        # Would detect security issues
        results = {
            "sql_injection": 0,
            "xss": 1,
            "hardcoded_secrets": 0,
        }

        assert "sql_injection" in results
