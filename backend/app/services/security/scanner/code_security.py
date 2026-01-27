"""Code Security Scanner."""

import re
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class SecurityCategory(str, Enum):
    """Security issue category."""

    INJECTION = "injection"
    XSS = "xss"
    AUTHENTICATION = "authentication"
    CRYPTOGRAPHY = "cryptography"
    SECRETS = "secrets"
    CONFIGURATION = "configuration"
    INPUT_VALIDATION = "input_validation"
    ACCESS_CONTROL = "access_control"
    LOGGING = "logging"
    ERROR_HANDLING = "error_handling"


class SecurityIssue(BaseModel):
    """A security issue found in code."""

    id: str
    category: SecurityCategory
    severity: str  # critical, high, medium, low, info
    file: str
    line: int
    end_line: int | None = None
    code_snippet: str | None = None
    message: str
    recommendation: str
    cwe_id: str | None = None
    confidence: float = 1.0


class CodeSecurityScanner:
    """Scans source code for security issues.

    Detects common security anti-patterns including:
    - SQL injection
    - XSS vulnerabilities
    - Hardcoded secrets
    - Insecure cryptography
    - Missing authentication
    """

    def __init__(self):
        """Initialize code security scanner."""
        # Define security patterns by category
        self._patterns: dict[SecurityCategory, list[dict[str, Any]]] = {
            SecurityCategory.INJECTION: [
                {
                    "pattern": r"execute\s*\(\s*[f'\"].*\{.*\}.*['\"]",
                    "message": "Possible SQL injection via f-string formatting",
                    "severity": "critical",
                    "cwe": "CWE-89",
                    "recommendation": "Use parameterized queries instead of string formatting",
                },
                {
                    "pattern": r"cursor\.execute\s*\(\s*['\"].*%s.*['\"].*%",
                    "message": "Possible SQL injection via string formatting",
                    "severity": "critical",
                    "cwe": "CWE-89",
                    "recommendation": "Use parameterized queries with proper escaping",
                },
                {
                    "pattern": r"subprocess\.(call|run|Popen)\s*\(\s*[f'\"]",
                    "message": "Command injection risk via formatted string",
                    "severity": "critical",
                    "cwe": "CWE-78",
                    "recommendation": "Use list arguments instead of shell strings",
                },
                {
                    "pattern": r"os\.system\s*\(",
                    "message": "os.system is vulnerable to command injection",
                    "severity": "high",
                    "cwe": "CWE-78",
                    "recommendation": "Use subprocess with list arguments",
                },
                {
                    "pattern": r"eval\s*\(",
                    "message": "eval() can execute arbitrary code",
                    "severity": "critical",
                    "cwe": "CWE-95",
                    "recommendation": "Avoid eval(), use ast.literal_eval() for data",
                },
                {
                    "pattern": r"exec\s*\(",
                    "message": "exec() can execute arbitrary code",
                    "severity": "critical",
                    "cwe": "CWE-95",
                    "recommendation": "Avoid exec(), find alternative approaches",
                },
            ],
            SecurityCategory.XSS: [
                {
                    "pattern": r"innerHTML\s*=",
                    "message": "Direct innerHTML assignment can lead to XSS",
                    "severity": "high",
                    "cwe": "CWE-79",
                    "recommendation": "Use textContent or sanitize HTML input",
                },
                {
                    "pattern": r"document\.write\s*\(",
                    "message": "document.write can be vulnerable to XSS",
                    "severity": "medium",
                    "cwe": "CWE-79",
                    "recommendation": "Use DOM manipulation methods instead",
                },
                {
                    "pattern": r"\|\s*safe\s*\}",
                    "message": "Jinja2 safe filter bypasses XSS protection",
                    "severity": "medium",
                    "cwe": "CWE-79",
                    "recommendation": "Ensure content is properly sanitized before using safe",
                },
            ],
            SecurityCategory.SECRETS: [
                {
                    "pattern": r"(?i)(password|passwd|pwd)\s*=\s*['\"][^'\"]{6,}['\"]",
                    "message": "Hardcoded password detected",
                    "severity": "critical",
                    "cwe": "CWE-798",
                    "recommendation": "Use environment variables or secret manager",
                },
                {
                    "pattern": r"(?i)(api[_-]?key|apikey)\s*=\s*['\"][^'\"]{10,}['\"]",
                    "message": "Hardcoded API key detected",
                    "severity": "critical",
                    "cwe": "CWE-798",
                    "recommendation": "Store API keys in environment variables",
                },
                {
                    "pattern": r"(?i)(secret|token)\s*=\s*['\"][^'\"]{10,}['\"]",
                    "message": "Hardcoded secret/token detected",
                    "severity": "critical",
                    "cwe": "CWE-798",
                    "recommendation": "Use secure secret management",
                },
                {
                    "pattern": r"sk-[a-zA-Z0-9]{20,}",
                    "message": "Possible OpenAI API key",
                    "severity": "critical",
                    "cwe": "CWE-798",
                    "recommendation": "Remove and rotate this API key immediately",
                },
                {
                    "pattern": r"ghp_[a-zA-Z0-9]{36,}",
                    "message": "GitHub Personal Access Token detected",
                    "severity": "critical",
                    "cwe": "CWE-798",
                    "recommendation": "Remove and rotate this token immediately",
                },
                {
                    "pattern": r"-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----",
                    "message": "Private key embedded in code",
                    "severity": "critical",
                    "cwe": "CWE-321",
                    "recommendation": "Store private keys in secure key management",
                },
            ],
            SecurityCategory.CRYPTOGRAPHY: [
                {
                    "pattern": r"md5\s*\(",
                    "message": "MD5 is cryptographically broken",
                    "severity": "high",
                    "cwe": "CWE-328",
                    "recommendation": "Use SHA-256 or better for hashing",
                },
                {
                    "pattern": r"sha1\s*\(",
                    "message": "SHA1 is cryptographically weak",
                    "severity": "medium",
                    "cwe": "CWE-328",
                    "recommendation": "Use SHA-256 or better for hashing",
                },
                {
                    "pattern": r"DES\s*\(",
                    "message": "DES encryption is insecure",
                    "severity": "high",
                    "cwe": "CWE-327",
                    "recommendation": "Use AES-256 for encryption",
                },
                {
                    "pattern": r"random\.(random|randint|choice|shuffle)\s*\(",
                    "message": "Using weak random for security-sensitive operation",
                    "severity": "medium",
                    "cwe": "CWE-330",
                    "recommendation": "Use secrets module for cryptographic randomness",
                    "context_check": ["password", "token", "key", "secret", "auth"],
                },
            ],
            SecurityCategory.AUTHENTICATION: [
                {
                    "pattern": r"verify\s*=\s*False",
                    "message": "SSL certificate verification disabled",
                    "severity": "high",
                    "cwe": "CWE-295",
                    "recommendation": "Enable SSL certificate verification",
                },
                {
                    "pattern": r"check_hostname\s*=\s*False",
                    "message": "Hostname verification disabled",
                    "severity": "high",
                    "cwe": "CWE-297",
                    "recommendation": "Enable hostname verification",
                },
            ],
            SecurityCategory.INPUT_VALIDATION: [
                {
                    "pattern": r"pickle\.loads?\s*\(",
                    "message": "Pickle deserialization can execute arbitrary code",
                    "severity": "high",
                    "cwe": "CWE-502",
                    "recommendation": "Use JSON or other safe serialization formats",
                },
                {
                    "pattern": r"yaml\.load\s*\([^)]*\)(?!\s*,\s*Loader\s*=)",
                    "message": "Unsafe YAML loading can execute code",
                    "severity": "high",
                    "cwe": "CWE-502",
                    "recommendation": "Use yaml.safe_load() instead",
                },
            ],
            SecurityCategory.ERROR_HANDLING: [
                {
                    "pattern": r"except\s*:\s*$",
                    "message": "Bare except catches all exceptions including system",
                    "severity": "medium",
                    "cwe": "CWE-755",
                    "recommendation": "Catch specific exceptions",
                },
                {
                    "pattern": r"traceback\.print_exc\s*\(\s*\)",
                    "message": "Printing stack traces may leak sensitive info",
                    "severity": "low",
                    "cwe": "CWE-209",
                    "recommendation": "Log errors securely, don't expose to users",
                },
            ],
            SecurityCategory.LOGGING: [
                {
                    "pattern": r"logging\.(debug|info|warning|error)\s*\([^)]*password",
                    "message": "Possible password in log statement",
                    "severity": "high",
                    "cwe": "CWE-532",
                    "recommendation": "Never log passwords or sensitive data",
                },
                {
                    "pattern": r"print\s*\([^)]*password",
                    "message": "Possible password in print statement",
                    "severity": "medium",
                    "cwe": "CWE-532",
                    "recommendation": "Remove debug prints with sensitive data",
                },
            ],
        }

    def scan_file(
        self,
        file_path: str | Path,
        content: str | None = None,
    ) -> list[SecurityIssue]:
        """Scan a single file for security issues.

        Args:
            file_path: Path to file
            content: Optional file content (reads if not provided)

        Returns:
            List of security issues found
        """
        issues = []
        path = Path(file_path)

        # Read content if not provided
        if content is None:
            try:
                content = path.read_text()
            except Exception:
                return []

        # Get file extension for context
        ext = path.suffix.lower()

        # Skip binary and non-code files
        non_code_extensions = {".pyc", ".pyo", ".so", ".dll", ".exe", ".bin", ".jpg", ".png", ".gif", ".pdf"}
        if ext in non_code_extensions:
            return []

        # Scan each line
        lines = content.split("\n")

        for category, patterns in self._patterns.items():
            for pattern_def in patterns:
                pattern = pattern_def["pattern"]
                context_check = pattern_def.get("context_check")

                for i, line in enumerate(lines, 1):
                    # Skip comments
                    stripped = line.strip()
                    if stripped.startswith("#") or stripped.startswith("//"):
                        continue

                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        # Check context if required
                        if context_check:
                            line_lower = line.lower()
                            if not any(ctx in line_lower for ctx in context_check):
                                continue

                        issues.append(SecurityIssue(
                            id=f"{category.value}-{i}",
                            category=category,
                            severity=pattern_def["severity"],
                            file=str(file_path),
                            line=i,
                            code_snippet=line.strip()[:100],
                            message=pattern_def["message"],
                            recommendation=pattern_def["recommendation"],
                            cwe_id=pattern_def.get("cwe"),
                        ))

        return issues

    def scan_directory(
        self,
        directory: str | Path,
        extensions: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
    ) -> list[SecurityIssue]:
        """Scan all files in a directory.

        Args:
            directory: Directory path
            extensions: File extensions to scan (default: common code files)
            exclude_patterns: Glob patterns to exclude

        Returns:
            List of all security issues found
        """
        issues = []
        dir_path = Path(directory)

        if extensions is None:
            extensions = [".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rb", ".php"]

        exclude_patterns = exclude_patterns or [
            "**/node_modules/**",
            "**/.git/**",
            "**/venv/**",
            "**/__pycache__/**",
            "**/dist/**",
            "**/build/**",
        ]

        for ext in extensions:
            for file_path in dir_path.rglob(f"*{ext}"):
                # Check exclusions
                should_exclude = False
                for pattern in exclude_patterns:
                    if file_path.match(pattern):
                        should_exclude = True
                        break

                if should_exclude:
                    continue

                file_issues = self.scan_file(file_path)
                issues.extend(file_issues)

        return issues

    def scan_diff(
        self,
        diff_content: str,
        base_path: str = "",
    ) -> list[SecurityIssue]:
        """Scan only added lines in a diff.

        Args:
            diff_content: Unified diff content
            base_path: Base path for file references

        Returns:
            List of security issues in added lines
        """
        issues = []
        current_file = None
        line_number = 0

        for line in diff_content.split("\n"):
            if line.startswith("diff --git"):
                match = re.search(r"b/(.+)$", line)
                if match:
                    current_file = match.group(1)
            elif line.startswith("@@"):
                # Parse hunk header for line numbers
                match = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
                if match:
                    line_number = int(match.group(1)) - 1
            elif line.startswith("+") and not line.startswith("+++"):
                line_number += 1
                added_line = line[1:]  # Remove the + prefix

                if current_file:
                    # Scan this single line
                    for category, patterns in self._patterns.items():
                        for pattern_def in patterns:
                            if re.search(pattern_def["pattern"], added_line, re.IGNORECASE):
                                issues.append(SecurityIssue(
                                    id=f"{category.value}-{line_number}",
                                    category=category,
                                    severity=pattern_def["severity"],
                                    file=current_file,
                                    line=line_number,
                                    code_snippet=added_line.strip()[:100],
                                    message=pattern_def["message"],
                                    recommendation=pattern_def["recommendation"],
                                    cwe_id=pattern_def.get("cwe"),
                                ))
                                break  # One issue per line per category
            elif line.startswith("-"):
                pass  # Deleted line, skip
            else:
                line_number += 1

        return issues

    def get_severity_counts(
        self,
        issues: list[SecurityIssue],
    ) -> dict[str, int]:
        """Get count of issues by severity.

        Args:
            issues: List of security issues

        Returns:
            Dict of severity -> count
        """
        counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0,
        }

        for issue in issues:
            if issue.severity in counts:
                counts[issue.severity] += 1

        return counts
