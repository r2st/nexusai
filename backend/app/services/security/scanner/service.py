"""Security Scanner Service - Main service for security scanning."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.services.security.scanner.vulnerability import (
    VulnerabilityScanner,
    Vulnerability,
    ScanResult,
)
from app.services.security.scanner.code_security import (
    CodeSecurityScanner,
    SecurityIssue,
)
from app.services.security.scanner.config_checker import (
    ConfigSecurityChecker,
    ConfigIssue,
)

logger = logging.getLogger(__name__)


class SecurityReport(BaseModel):
    """Comprehensive security scan report."""

    scan_id: str
    scanned_at: datetime = Field(default_factory=datetime.utcnow)
    project_path: str | None = None

    # Vulnerability scan results
    dependency_scan: ScanResult | None = None

    # Code security issues
    code_issues: list[SecurityIssue] = Field(default_factory=list)

    # Configuration issues
    config_issues: list[ConfigIssue] = Field(default_factory=list)

    # Summary
    total_issues: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0

    # Overall risk score (0-100)
    risk_score: float = 0.0

    # Pass/fail based on thresholds
    passed: bool = True
    failure_reasons: list[str] = Field(default_factory=list)

    @property
    def has_critical_issues(self) -> bool:
        return self.critical_count > 0


class ScanThresholds(BaseModel):
    """Thresholds for pass/fail determination."""

    max_critical: int = 0
    max_high: int = 5
    max_medium: int = 20
    max_risk_score: float = 70.0


class SecurityScannerService:
    """Main service for comprehensive security scanning.

    Orchestrates:
    - Dependency vulnerability scanning
    - Source code security analysis
    - Configuration security checking
    """

    def __init__(
        self,
        thresholds: ScanThresholds | None = None,
    ):
        """Initialize security scanner service.

        Args:
            thresholds: Pass/fail thresholds
        """
        self._thresholds = thresholds or ScanThresholds()
        self._vulnerability_scanner = VulnerabilityScanner()
        self._code_scanner = CodeSecurityScanner()
        self._config_checker = ConfigSecurityChecker()

    def scan_project(
        self,
        project_path: str | Path,
        scan_dependencies: bool = True,
        scan_code: bool = True,
        scan_config: bool = True,
        file_extensions: list[str] | None = None,
    ) -> SecurityReport:
        """Perform comprehensive security scan of a project.

        Args:
            project_path: Path to project root
            scan_dependencies: Scan for dependency vulnerabilities
            scan_code: Scan source code for security issues
            scan_config: Check configuration files

        Returns:
            Complete security report
        """
        import uuid

        path = Path(project_path)
        scan_id = str(uuid.uuid4())[:8]

        logger.info(f"Starting security scan {scan_id} for {path}")

        report = SecurityReport(
            scan_id=scan_id,
            project_path=str(path),
        )

        # Scan dependencies
        if scan_dependencies:
            report.dependency_scan = self._scan_dependencies(path)

        # Scan code
        if scan_code:
            report.code_issues = self._code_scanner.scan_directory(
                path,
                extensions=file_extensions,
            )

        # Check configuration
        if scan_config:
            report.config_issues = self._config_checker.check_all(path)

        # Calculate totals and scores
        self._calculate_summary(report)

        # Determine pass/fail
        self._evaluate_thresholds(report)

        logger.info(
            f"Security scan {scan_id} complete: "
            f"critical={report.critical_count}, high={report.high_count}, "
            f"risk_score={report.risk_score:.1f}, passed={report.passed}"
        )

        return report

    def scan_diff(
        self,
        diff_content: str,
        base_path: str = "",
    ) -> SecurityReport:
        """Scan only changed code in a diff.

        Args:
            diff_content: Unified diff content
            base_path: Base path for file references

        Returns:
            Security report for changed code
        """
        import uuid

        scan_id = str(uuid.uuid4())[:8]

        report = SecurityReport(
            scan_id=scan_id,
            project_path=base_path or "diff",
        )

        # Scan diff for code issues
        report.code_issues = self._code_scanner.scan_diff(diff_content, base_path)

        # Calculate summary
        self._calculate_summary(report)
        self._evaluate_thresholds(report)

        return report

    def scan_dependencies_only(
        self,
        project_path: str | Path,
    ) -> ScanResult:
        """Scan only dependencies for vulnerabilities.

        Args:
            project_path: Path to project

        Returns:
            Vulnerability scan result
        """
        return self._scan_dependencies(Path(project_path))

    def scan_code_only(
        self,
        project_path: str | Path,
        extensions: list[str] | None = None,
    ) -> list[SecurityIssue]:
        """Scan only source code for security issues.

        Args:
            project_path: Path to project
            extensions: File extensions to scan

        Returns:
            List of code security issues
        """
        return self._code_scanner.scan_directory(
            project_path,
            extensions=extensions,
        )

    def scan_config_only(
        self,
        project_path: str | Path,
    ) -> list[ConfigIssue]:
        """Check only configuration files.

        Args:
            project_path: Path to project

        Returns:
            List of configuration issues
        """
        return self._config_checker.check_all(project_path)

    def _scan_dependencies(self, path: Path) -> ScanResult:
        """Scan for dependency vulnerabilities."""
        # Check for Python
        if (path / "requirements.txt").exists():
            return self._vulnerability_scanner.scan_python_dependencies(
                requirements_file=path / "requirements.txt"
            )
        elif (path / "pyproject.toml").exists():
            return self._vulnerability_scanner.scan_python_dependencies(
                project_dir=path
            )

        # Check for Node.js
        if (path / "package.json").exists():
            return self._vulnerability_scanner.scan_npm_dependencies(path)

        return ScanResult(
            scan_type="none",
            error="No supported dependency files found",
        )

    def _calculate_summary(self, report: SecurityReport) -> None:
        """Calculate summary statistics for report."""
        critical = 0
        high = 0
        medium = 0
        low = 0

        # Count vulnerabilities
        if report.dependency_scan:
            for vuln in report.dependency_scan.vulnerabilities:
                if vuln.severity.value == "critical":
                    critical += 1
                elif vuln.severity.value == "high":
                    high += 1
                elif vuln.severity.value == "medium":
                    medium += 1
                elif vuln.severity.value == "low":
                    low += 1

        # Count code issues
        for issue in report.code_issues:
            if issue.severity == "critical":
                critical += 1
            elif issue.severity == "high":
                high += 1
            elif issue.severity == "medium":
                medium += 1
            elif issue.severity == "low":
                low += 1

        # Count config issues
        for issue in report.config_issues:
            if issue.severity == "critical":
                critical += 1
            elif issue.severity == "high":
                high += 1
            elif issue.severity == "medium":
                medium += 1
            elif issue.severity == "low":
                low += 1

        report.critical_count = critical
        report.high_count = high
        report.medium_count = medium
        report.low_count = low
        report.total_issues = critical + high + medium + low

        # Calculate risk score (0-100)
        # Weighted by severity
        weighted_score = (
            critical * 40 +
            high * 15 +
            medium * 5 +
            low * 1
        )
        # Normalize to 0-100 scale (cap at 100)
        report.risk_score = min(100.0, weighted_score)

    def _evaluate_thresholds(self, report: SecurityReport) -> None:
        """Evaluate report against thresholds."""
        report.passed = True
        report.failure_reasons = []

        if report.critical_count > self._thresholds.max_critical:
            report.passed = False
            report.failure_reasons.append(
                f"Critical issues ({report.critical_count}) exceed threshold ({self._thresholds.max_critical})"
            )

        if report.high_count > self._thresholds.max_high:
            report.passed = False
            report.failure_reasons.append(
                f"High issues ({report.high_count}) exceed threshold ({self._thresholds.max_high})"
            )

        if report.medium_count > self._thresholds.max_medium:
            report.passed = False
            report.failure_reasons.append(
                f"Medium issues ({report.medium_count}) exceed threshold ({self._thresholds.max_medium})"
            )

        if report.risk_score > self._thresholds.max_risk_score:
            report.passed = False
            report.failure_reasons.append(
                f"Risk score ({report.risk_score:.1f}) exceeds threshold ({self._thresholds.max_risk_score})"
            )

    def generate_sarif_report(
        self,
        report: SecurityReport,
    ) -> dict[str, Any]:
        """Generate SARIF format report for CI/CD integration.

        Args:
            report: Security report

        Returns:
            SARIF formatted report
        """
        results = []

        # Add code issues
        for issue in report.code_issues:
            results.append({
                "ruleId": issue.id,
                "level": self._severity_to_sarif_level(issue.severity),
                "message": {"text": issue.message},
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {"uri": issue.file},
                        "region": {"startLine": issue.line},
                    }
                }],
            })

        # Add config issues
        for issue in report.config_issues:
            results.append({
                "ruleId": issue.id,
                "level": self._severity_to_sarif_level(issue.severity),
                "message": {"text": issue.message},
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {"uri": issue.file},
                    }
                }],
            })

        return {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [{
                "tool": {
                    "driver": {
                        "name": "NexusAI Security Scanner",
                        "version": "1.0.0",
                    }
                },
                "results": results,
            }],
        }

    def _severity_to_sarif_level(self, severity: str) -> str:
        """Convert severity to SARIF level."""
        mapping = {
            "critical": "error",
            "high": "error",
            "medium": "warning",
            "low": "note",
            "info": "note",
        }
        return mapping.get(severity, "warning")


# Factory function
def get_security_scanner_service(
    thresholds: ScanThresholds | None = None,
) -> SecurityScannerService:
    """Create a security scanner service instance.

    Args:
        thresholds: Optional pass/fail thresholds

    Returns:
        Configured SecurityScannerService
    """
    return SecurityScannerService(thresholds=thresholds)
