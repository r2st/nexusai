"""
CI/CD Insights MCP Tool Handlers

Provides tools for accessing build logs, test results, pipeline failures,
and CI/CD analytics through MCP for AI assistant integration.
"""

import json
import logging
import re
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from .server import MCPToolHandler
from .protocol import MCPTool
from .errors import (
    service_unavailable_error,
    not_found_error,
    connection_error,
    internal_error,
    ToolErrorResponse,
    ErrorCategory,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Data Models
# =============================================================================

class BuildStatus(str, Enum):
    """CI build status."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class TestStatus(str, Enum):
    """Test result status."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    FLAKY = "flaky"
    ERROR = "error"


@dataclass
class Build:
    """CI build record."""

    id: str
    project_name: str
    branch: str
    commit_sha: str
    commit_message: str
    author: str
    status: BuildStatus
    started_at: datetime
    finished_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    trigger: str = "push"  # push, pr, manual, schedule
    pipeline_name: str = "default"
    stages: List[Dict] = field(default_factory=list)
    artifacts: List[str] = field(default_factory=list)
    logs_url: Optional[str] = None


@dataclass
class TestResult:
    """Test execution result."""

    id: str
    build_id: str
    test_name: str
    test_suite: str
    status: TestStatus
    duration_ms: int
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    retry_count: int = 0
    flaky_history: List[bool] = field(default_factory=list)


@dataclass
class TestSummary:
    """Summary of test results for a build."""

    build_id: str
    total: int
    passed: int
    failed: int
    skipped: int
    flaky: int
    duration_seconds: float
    coverage_percent: Optional[float] = None


# =============================================================================
# CI Service (Mock Implementation)
# =============================================================================

class CIService:
    """Service for CI/CD insights and analytics."""

    def __init__(self):
        # In a real implementation, this would connect to Jenkins, GitHub Actions, etc.
        self._builds: Dict[str, Build] = {}
        self._test_results: Dict[str, List[TestResult]] = {}
        self._generate_sample_data()

    def _generate_sample_data(self):
        """Generate sample CI data for demonstration."""
        import random
        from uuid import uuid4

        projects = ["nexusai-backend", "nexusai-frontend", "nexusai-worker"]
        branches = ["main", "develop", "feature/auth", "fix/bug-123"]
        authors = ["alice", "bob", "charlie", "diana"]

        for i in range(20):
            build_id = str(uuid4())[:8]
            project = random.choice(projects)
            branch = random.choice(branches)
            author = random.choice(authors)

            status = random.choices(
                [BuildStatus.SUCCESS, BuildStatus.FAILED, BuildStatus.RUNNING],
                weights=[70, 25, 5],
            )[0]

            started = datetime.now(UTC) - timedelta(hours=random.randint(1, 168))
            duration = random.randint(60, 900) if status != BuildStatus.RUNNING else None
            finished = started + timedelta(seconds=duration) if duration else None

            build = Build(
                id=build_id,
                project_name=project,
                branch=branch,
                commit_sha=f"{uuid4().hex[:7]}",
                commit_message=f"{'Fix' if 'fix' in branch else 'Add'} {random.choice(['feature', 'bug', 'test', 'docs'])}",
                author=author,
                status=status,
                started_at=started,
                finished_at=finished,
                duration_seconds=duration,
                trigger=random.choice(["push", "pr", "manual"]),
                stages=[
                    {"name": "build", "status": "success", "duration": random.randint(30, 120)},
                    {"name": "test", "status": "success" if status == BuildStatus.SUCCESS else "failed", "duration": random.randint(60, 300)},
                    {"name": "deploy", "status": "success" if status == BuildStatus.SUCCESS else "skipped", "duration": random.randint(30, 60)},
                ],
            )
            self._builds[build_id] = build

            # Generate test results
            test_count = random.randint(50, 200)
            test_results = []
            for j in range(test_count):
                test_status = random.choices(
                    [TestStatus.PASSED, TestStatus.FAILED, TestStatus.SKIPPED, TestStatus.FLAKY],
                    weights=[85, 10, 3, 2] if status == BuildStatus.SUCCESS else [60, 30, 5, 5],
                )[0]

                test_results.append(TestResult(
                    id=f"{build_id}-test-{j}",
                    build_id=build_id,
                    test_name=f"test_{random.choice(['auth', 'api', 'db', 'ui', 'integration'])}_{j}",
                    test_suite=random.choice(["unit", "integration", "e2e"]),
                    status=test_status,
                    duration_ms=random.randint(10, 5000),
                    error_message=f"AssertionError: expected {random.randint(1,100)} but got {random.randint(1,100)}" if test_status == TestStatus.FAILED else None,
                    stack_trace="at test_file.py:42\nat runner.py:100" if test_status == TestStatus.FAILED else None,
                    retry_count=random.randint(0, 2) if test_status == TestStatus.FLAKY else 0,
                ))

            self._test_results[build_id] = test_results

    async def health_check(self) -> bool:
        """Check if CI service is available."""
        return True

    async def get_build(self, build_id: str) -> Optional[Build]:
        """Get a specific build."""
        return self._builds.get(build_id)

    async def list_builds(
        self,
        project_name: Optional[str] = None,
        branch: Optional[str] = None,
        status: Optional[BuildStatus] = None,
        limit: int = 20,
    ) -> List[Build]:
        """List builds with optional filters."""
        builds = list(self._builds.values())

        if project_name:
            builds = [b for b in builds if b.project_name == project_name]
        if branch:
            builds = [b for b in builds if b.branch == branch]
        if status:
            builds = [b for b in builds if b.status == status]

        # Sort by start time (newest first)
        builds.sort(key=lambda b: b.started_at, reverse=True)
        return builds[:limit]

    async def get_build_logs(
        self,
        build_id: str,
        stage: Optional[str] = None,
        log_type: str = "all",  # all, failed, errors
    ) -> Optional[Dict]:
        """Get build logs."""
        build = self._builds.get(build_id)
        if not build:
            return None

        # Generate mock logs based on build status
        logs = []
        for stage_info in build.stages:
            stage_name = stage_info["name"]
            if stage and stage_name != stage:
                continue

            stage_logs = [
                f"[{stage_name}] Starting stage...",
                f"[{stage_name}] Running commands...",
            ]

            if stage_info["status"] == "failed":
                stage_logs.extend([
                    f"[{stage_name}] ERROR: Command failed with exit code 1",
                    f"[{stage_name}] Error: Test assertions failed",
                    f"[{stage_name}] See test report for details",
                ])
            else:
                stage_logs.append(f"[{stage_name}] Stage completed successfully")

            logs.extend(stage_logs)

        if log_type == "failed":
            logs = [l for l in logs if "ERROR" in l or "failed" in l.lower()]
        elif log_type == "errors":
            logs = [l for l in logs if "ERROR" in l]

        return {
            "build_id": build_id,
            "log_type": log_type,
            "stage_filter": stage,
            "logs": logs,
        }

    async def get_test_results(
        self,
        build_id: str,
        status_filter: Optional[TestStatus] = None,
        suite_filter: Optional[str] = None,
    ) -> List[TestResult]:
        """Get test results for a build."""
        results = self._test_results.get(build_id, [])

        if status_filter:
            results = [r for r in results if r.status == status_filter]
        if suite_filter:
            results = [r for r in results if r.test_suite == suite_filter]

        return results

    async def get_test_summary(self, build_id: str) -> Optional[TestSummary]:
        """Get test summary for a build."""
        results = self._test_results.get(build_id, [])
        if not results:
            return None

        return TestSummary(
            build_id=build_id,
            total=len(results),
            passed=sum(1 for r in results if r.status == TestStatus.PASSED),
            failed=sum(1 for r in results if r.status == TestStatus.FAILED),
            skipped=sum(1 for r in results if r.status == TestStatus.SKIPPED),
            flaky=sum(1 for r in results if r.status == TestStatus.FLAKY),
            duration_seconds=sum(r.duration_ms for r in results) / 1000,
            coverage_percent=round(70 + (len(results) % 20), 1),  # Mock coverage
        )

    async def get_flaky_tests(
        self,
        project_name: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict]:
        """Get flaky tests across recent builds."""
        flaky_tests = []

        for build_id, results in self._test_results.items():
            build = self._builds.get(build_id)
            if not build:
                continue
            if project_name and build.project_name != project_name:
                continue

            for result in results:
                if result.status == TestStatus.FLAKY or result.retry_count > 0:
                    flaky_tests.append({
                        "test_name": result.test_name,
                        "test_suite": result.test_suite,
                        "build_id": build_id,
                        "project": build.project_name,
                        "retry_count": result.retry_count,
                        "flaky_rate": f"{(result.retry_count / 3) * 100:.0f}%" if result.retry_count else "N/A",
                    })

        # Sort by retry count
        flaky_tests.sort(key=lambda t: t["retry_count"], reverse=True)
        return flaky_tests[:limit]

    async def get_failure_patterns(
        self,
        project_name: Optional[str] = None,
        days: int = 7,
    ) -> Dict:
        """Analyze failure patterns in recent builds."""
        cutoff = datetime.now(UTC) - timedelta(days=days)
        failure_reasons = {}
        stage_failures = {}
        author_failures = {}

        for build in self._builds.values():
            if build.started_at < cutoff:
                continue
            if project_name and build.project_name != project_name:
                continue
            if build.status != BuildStatus.FAILED:
                continue

            # Track failed stages
            for stage in build.stages:
                if stage["status"] == "failed":
                    stage_name = stage["name"]
                    stage_failures[stage_name] = stage_failures.get(stage_name, 0) + 1

            # Track author failures
            author_failures[build.author] = author_failures.get(build.author, 0) + 1

        # Get test failure reasons
        for build_id, results in self._test_results.items():
            build = self._builds.get(build_id)
            if not build or build.started_at < cutoff:
                continue
            if project_name and build.project_name != project_name:
                continue

            for result in results:
                if result.status == TestStatus.FAILED and result.error_message:
                    # Extract error type
                    error_type = result.error_message.split(":")[0] if ":" in result.error_message else "Unknown"
                    failure_reasons[error_type] = failure_reasons.get(error_type, 0) + 1

        return {
            "time_range_days": days,
            "project": project_name or "all",
            "failure_reasons": sorted(failure_reasons.items(), key=lambda x: x[1], reverse=True)[:10],
            "stage_failures": sorted(stage_failures.items(), key=lambda x: x[1], reverse=True),
            "author_failures": sorted(author_failures.items(), key=lambda x: x[1], reverse=True)[:5],
        }


# Global CI service instance
ci_service = CIService()


# =============================================================================
# CI Tools
# =============================================================================

class CIHealthCheckHandler(MCPToolHandler):
    """Check CI service health."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="ci_health_check",
            description="Check if the CI/CD service is available and healthy",
            input_schema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        try:
            is_healthy = await ci_service.health_check()
            return {
                "success": True,
                "healthy": is_healthy,
                "status": "available" if is_healthy else "unavailable",
                "message": "CI service is running and ready to use." if is_healthy else "CI service is not available.",
                "next_steps": [
                    "Use 'ci_list_builds' to see recent builds",
                    "Use 'ci_get_failed_tests' to find failing tests",
                ],
            }
        except Exception as e:
            return connection_error(
                target="CI Service",
                original_error=str(e),
            ).to_dict()


class CIListBuildsHandler(MCPToolHandler):
    """List CI builds."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="ci_list_builds",
            description="List CI/CD builds with optional filters for project, branch, and status",
            input_schema={
                "type": "object",
                "properties": {
                    "project_name": {
                        "type": "string",
                        "description": "Filter by project name",
                    },
                    "branch": {
                        "type": "string",
                        "description": "Filter by branch name",
                    },
                    "status": {
                        "type": "string",
                        "description": "Filter by build status",
                        "enum": [s.value for s in BuildStatus],
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of builds to return (default: 20)",
                        "default": 20,
                    },
                },
                "required": [],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        project_name = arguments.get("project_name")
        branch = arguments.get("branch")
        status_str = arguments.get("status")
        limit = arguments.get("limit", 20)

        status = BuildStatus(status_str) if status_str else None

        try:
            builds = await ci_service.list_builds(
                project_name=project_name,
                branch=branch,
                status=status,
                limit=limit,
            )

            return {
                "success": True,
                "count": len(builds),
                "filters": {
                    "project": project_name,
                    "branch": branch,
                    "status": status_str,
                },
                "builds": [
                    {
                        "id": b.id,
                        "project": b.project_name,
                        "branch": b.branch,
                        "status": b.status.value,
                        "author": b.author,
                        "commit_sha": b.commit_sha[:7],
                        "commit_message": b.commit_message[:50],
                        "trigger": b.trigger,
                        "started_at": b.started_at.isoformat(),
                        "duration_seconds": b.duration_seconds,
                    }
                    for b in builds
                ],
            }
        except Exception as e:
            return internal_error(
                operation="list_builds",
                error_message=str(e),
            ).to_dict()


class CIGetBuildHandler(MCPToolHandler):
    """Get detailed build information."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="ci_get_build",
            description="Get detailed information about a specific CI build including stages and artifacts",
            input_schema={
                "type": "object",
                "properties": {
                    "build_id": {
                        "type": "string",
                        "description": "Build ID to retrieve",
                    },
                },
                "required": ["build_id"],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        build_id = arguments["build_id"]

        try:
            build = await ci_service.get_build(build_id)
            if not build:
                return not_found_error(
                    resource_type="build",
                    resource_name=build_id,
                ).to_dict()

            return {
                "success": True,
                "build": {
                    "id": build.id,
                    "project": build.project_name,
                    "branch": build.branch,
                    "commit_sha": build.commit_sha,
                    "commit_message": build.commit_message,
                    "author": build.author,
                    "status": build.status.value,
                    "trigger": build.trigger,
                    "pipeline": build.pipeline_name,
                    "started_at": build.started_at.isoformat(),
                    "finished_at": build.finished_at.isoformat() if build.finished_at else None,
                    "duration_seconds": build.duration_seconds,
                    "stages": build.stages,
                    "artifacts": build.artifacts,
                },
            }
        except Exception as e:
            return internal_error(
                operation="get_build",
                error_message=str(e),
            ).to_dict()


class CIGetBuildLogsHandler(MCPToolHandler):
    """Get build logs."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="ci_get_build_logs",
            description="Get logs from a CI build, optionally filtered by stage or log type",
            input_schema={
                "type": "object",
                "properties": {
                    "build_id": {
                        "type": "string",
                        "description": "Build ID to get logs for",
                    },
                    "stage": {
                        "type": "string",
                        "description": "Filter by stage name (e.g., 'build', 'test', 'deploy')",
                    },
                    "log_type": {
                        "type": "string",
                        "description": "Type of logs to retrieve",
                        "enum": ["all", "failed", "errors"],
                        "default": "all",
                    },
                },
                "required": ["build_id"],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        build_id = arguments["build_id"]
        stage = arguments.get("stage")
        log_type = arguments.get("log_type", "all")

        try:
            result = await ci_service.get_build_logs(build_id, stage, log_type)
            if not result:
                return not_found_error(
                    resource_type="build",
                    resource_name=build_id,
                ).to_dict()

            return {
                "success": True,
                **result,
                "log_count": len(result["logs"]),
            }
        except Exception as e:
            return internal_error(
                operation="get_build_logs",
                error_message=str(e),
            ).to_dict()


class CIGetTestResultsHandler(MCPToolHandler):
    """Get test results for a build."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="ci_get_test_results",
            description="Get test results for a specific build with optional filtering",
            input_schema={
                "type": "object",
                "properties": {
                    "build_id": {
                        "type": "string",
                        "description": "Build ID to get test results for",
                    },
                    "status": {
                        "type": "string",
                        "description": "Filter by test status",
                        "enum": [s.value for s in TestStatus],
                    },
                    "suite": {
                        "type": "string",
                        "description": "Filter by test suite (unit, integration, e2e)",
                    },
                },
                "required": ["build_id"],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        build_id = arguments["build_id"]
        status_str = arguments.get("status")
        suite = arguments.get("suite")

        status = TestStatus(status_str) if status_str else None

        try:
            results = await ci_service.get_test_results(
                build_id=build_id,
                status_filter=status,
                suite_filter=suite,
            )

            return {
                "success": True,
                "build_id": build_id,
                "count": len(results),
                "filters": {
                    "status": status_str,
                    "suite": suite,
                },
                "tests": [
                    {
                        "test_name": r.test_name,
                        "suite": r.test_suite,
                        "status": r.status.value,
                        "duration_ms": r.duration_ms,
                        "error_message": r.error_message,
                        "retry_count": r.retry_count,
                    }
                    for r in results[:50]  # Limit to 50 for readability
                ],
            }
        except Exception as e:
            return internal_error(
                operation="get_test_results",
                error_message=str(e),
            ).to_dict()


class CIGetFailedTestsHandler(MCPToolHandler):
    """Get failed tests for a build."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="ci_get_failed_tests",
            description="Get detailed information about failed tests in a build, including error messages and stack traces",
            input_schema={
                "type": "object",
                "properties": {
                    "build_id": {
                        "type": "string",
                        "description": "Build ID to get failed tests for",
                    },
                },
                "required": ["build_id"],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        build_id = arguments["build_id"]

        try:
            results = await ci_service.get_test_results(
                build_id=build_id,
                status_filter=TestStatus.FAILED,
            )

            return {
                "success": True,
                "build_id": build_id,
                "failed_count": len(results),
                "failed_tests": [
                    {
                        "test_name": r.test_name,
                        "suite": r.test_suite,
                        "duration_ms": r.duration_ms,
                        "error_message": r.error_message,
                        "stack_trace": r.stack_trace,
                    }
                    for r in results
                ],
                "next_steps": [
                    "Review the error messages to understand failures",
                    "Check if tests are flaky using 'ci_get_flaky_tests'",
                    "View full build logs with 'ci_get_build_logs'",
                ] if results else ["All tests passed!"],
            }
        except Exception as e:
            return internal_error(
                operation="get_failed_tests",
                error_message=str(e),
            ).to_dict()


class CIGetTestSummaryHandler(MCPToolHandler):
    """Get test summary for a build."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="ci_get_test_summary",
            description="Get a summary of test results for a build including pass/fail counts and coverage",
            input_schema={
                "type": "object",
                "properties": {
                    "build_id": {
                        "type": "string",
                        "description": "Build ID to get test summary for",
                    },
                },
                "required": ["build_id"],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        build_id = arguments["build_id"]

        try:
            summary = await ci_service.get_test_summary(build_id)
            if not summary:
                return not_found_error(
                    resource_type="build",
                    resource_name=build_id,
                ).to_dict()

            pass_rate = (summary.passed / summary.total * 100) if summary.total > 0 else 0

            return {
                "success": True,
                "build_id": build_id,
                "summary": {
                    "total_tests": summary.total,
                    "passed": summary.passed,
                    "failed": summary.failed,
                    "skipped": summary.skipped,
                    "flaky": summary.flaky,
                    "pass_rate": f"{pass_rate:.1f}%",
                    "duration_seconds": round(summary.duration_seconds, 2),
                    "coverage_percent": summary.coverage_percent,
                },
                "status": "healthy" if pass_rate >= 80 else "needs_attention" if pass_rate >= 50 else "critical",
            }
        except Exception as e:
            return internal_error(
                operation="get_test_summary",
                error_message=str(e),
            ).to_dict()


class CIGetFlakyTestsHandler(MCPToolHandler):
    """Get flaky tests."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="ci_get_flaky_tests",
            description="Get a list of flaky tests that intermittently fail across builds",
            input_schema={
                "type": "object",
                "properties": {
                    "project_name": {
                        "type": "string",
                        "description": "Filter by project name",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of flaky tests to return",
                        "default": 20,
                    },
                },
                "required": [],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        project_name = arguments.get("project_name")
        limit = arguments.get("limit", 20)

        try:
            flaky_tests = await ci_service.get_flaky_tests(
                project_name=project_name,
                limit=limit,
            )

            return {
                "success": True,
                "project": project_name or "all",
                "count": len(flaky_tests),
                "flaky_tests": flaky_tests,
                "recommendations": [
                    "Investigate tests with high retry counts",
                    "Consider adding retries or fixing test isolation",
                    "Check for timing-dependent assertions",
                ] if flaky_tests else ["No flaky tests detected!"],
            }
        except Exception as e:
            return internal_error(
                operation="get_flaky_tests",
                error_message=str(e),
            ).to_dict()


class CIGetFailurePatternsHandler(MCPToolHandler):
    """Analyze failure patterns."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="ci_get_failure_patterns",
            description="Analyze patterns in CI/CD failures to identify common issues and problematic areas",
            input_schema={
                "type": "object",
                "properties": {
                    "project_name": {
                        "type": "string",
                        "description": "Filter by project name",
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of days to analyze (default: 7)",
                        "default": 7,
                    },
                },
                "required": [],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        project_name = arguments.get("project_name")
        days = arguments.get("days", 7)

        try:
            patterns = await ci_service.get_failure_patterns(
                project_name=project_name,
                days=days,
            )

            return {
                "success": True,
                **patterns,
                "analysis": {
                    "most_common_failure": patterns["failure_reasons"][0] if patterns["failure_reasons"] else None,
                    "most_failing_stage": patterns["stage_failures"][0] if patterns["stage_failures"] else None,
                },
                "recommendations": self._generate_recommendations(patterns),
            }
        except Exception as e:
            return internal_error(
                operation="get_failure_patterns",
                error_message=str(e),
            ).to_dict()

    def _generate_recommendations(self, patterns: Dict) -> List[str]:
        """Generate recommendations based on failure patterns."""
        recommendations = []

        if patterns["stage_failures"]:
            top_stage = patterns["stage_failures"][0][0]
            if top_stage == "test":
                recommendations.append("Focus on improving test stability and coverage")
            elif top_stage == "build":
                recommendations.append("Review build configuration and dependencies")
            elif top_stage == "deploy":
                recommendations.append("Check deployment scripts and environment configuration")

        if patterns["failure_reasons"]:
            top_reason = patterns["failure_reasons"][0][0]
            if "Assert" in top_reason:
                recommendations.append("Review test assertions for flaky behavior")
            if "Timeout" in top_reason:
                recommendations.append("Investigate timeout issues - may need to increase limits")

        if patterns["author_failures"]:
            recommendations.append("Consider pair programming or code review for developers with frequent failures")

        if not recommendations:
            recommendations.append("CI/CD pipeline is running smoothly!")

        return recommendations


class CIGetBuildStatsHandler(MCPToolHandler):
    """Get build statistics."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="ci_get_build_stats",
            description="Get overall CI/CD statistics including success rates, average build times, and trends",
            input_schema={
                "type": "object",
                "properties": {
                    "project_name": {
                        "type": "string",
                        "description": "Filter by project name",
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of days to analyze (default: 7)",
                        "default": 7,
                    },
                },
                "required": [],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        project_name = arguments.get("project_name")
        days = arguments.get("days", 7)

        try:
            builds = await ci_service.list_builds(
                project_name=project_name,
                limit=1000,
            )

            cutoff = datetime.now(UTC) - timedelta(days=days)
            recent_builds = [b for b in builds if b.started_at >= cutoff]

            if not recent_builds:
                return {
                    "success": True,
                    "message": "No builds found in the specified time range",
                }

            total = len(recent_builds)
            succeeded = sum(1 for b in recent_builds if b.status == BuildStatus.SUCCESS)
            failed = sum(1 for b in recent_builds if b.status == BuildStatus.FAILED)
            running = sum(1 for b in recent_builds if b.status == BuildStatus.RUNNING)

            durations = [b.duration_seconds for b in recent_builds if b.duration_seconds]
            avg_duration = sum(durations) / len(durations) if durations else 0

            return {
                "success": True,
                "time_range_days": days,
                "project": project_name or "all",
                "stats": {
                    "total_builds": total,
                    "succeeded": succeeded,
                    "failed": failed,
                    "running": running,
                    "success_rate": f"{(succeeded / total * 100):.1f}%" if total > 0 else "N/A",
                    "failure_rate": f"{(failed / total * 100):.1f}%" if total > 0 else "N/A",
                    "avg_duration_seconds": round(avg_duration, 1),
                    "avg_duration_formatted": f"{int(avg_duration // 60)}m {int(avg_duration % 60)}s",
                },
                "builds_per_day": round(total / days, 1),
            }
        except Exception as e:
            return internal_error(
                operation="get_build_stats",
                error_message=str(e),
            ).to_dict()


# =============================================================================
# Helper function to get all CI tool handlers
# =============================================================================

def get_all_ci_tool_handlers() -> list[MCPToolHandler]:
    """Return all CI/CD MCP tool handlers."""
    return [
        # Health
        CIHealthCheckHandler(),

        # Builds
        CIListBuildsHandler(),
        CIGetBuildHandler(),
        CIGetBuildLogsHandler(),
        CIGetBuildStatsHandler(),

        # Tests
        CIGetTestResultsHandler(),
        CIGetFailedTestsHandler(),
        CIGetTestSummaryHandler(),
        CIGetFlakyTestsHandler(),

        # Analysis
        CIGetFailurePatternsHandler(),
    ]
