"""
Specialized Runners

Pre-configured runners for common tasks.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging

from .executor import SandboxExecutor, ExecutionConfig, ExecutionResult

logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Result of test execution."""
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    total: int = 0
    
    test_cases: List[Dict[str, Any]] = field(default_factory=list)
    coverage_percent: Optional[float] = None
    
    raw_output: str = ""
    duration_ms: int = 0
    
    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 1.0
        return self.passed / self.total


@dataclass
class LintResult:
    """Result of linting."""
    issues: List[Dict[str, Any]] = field(default_factory=list)
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    
    raw_output: str = ""
    
    @property
    def is_clean(self) -> bool:
        return self.error_count == 0


@dataclass
class BuildResult:
    """Result of building."""
    success: bool = False
    artifacts: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    raw_output: str = ""
    duration_ms: int = 0


class TestRunner:
    """
    Run tests in a sandbox.
    
    Features:
    - Multi-framework support
    - Coverage collection
    - Result parsing
    """
    
    def __init__(self, executor: SandboxExecutor):
        self.executor = executor
    
    async def run_pytest(
        self,
        test_files: Dict[str, str],
        source_files: Optional[Dict[str, str]] = None,
        tenant_id: str = "",
        timeout: int = 120,
        coverage: bool = False,
    ) -> TestResult:
        """
        Run pytest tests.
        
        Args:
            test_files: Dict of test filename to content
            source_files: Optional source files to include
            tenant_id: Tenant ID
            timeout: Timeout in seconds
            coverage: Whether to collect coverage
            
        Returns:
            TestResult
        """
        result = TestResult()
        
        # Combine all files
        all_files = {}
        if source_files:
            all_files.update(source_files)
        all_files.update(test_files)
        
        # Configure
        packages = ["pytest"]
        if coverage:
            packages.append("pytest-cov")
        
        config = ExecutionConfig(
            language="python",
            timeout_seconds=timeout,
            packages=packages,
            memory_mb=512,
        )
        
        # Build command
        command = ["python", "-m", "pytest", "-v", "--tb=short"]
        if coverage:
            command.extend(["--cov=.", "--cov-report=term"])
        command.append("/workspace")
        
        # Execute
        exec_result = await self.executor.execute_tests(
            all_files,
            config,
            tenant_id,
            test_command=command,
        )
        
        result.raw_output = exec_result.stdout + exec_result.stderr
        result.duration_ms = exec_result.duration_ms or 0
        
        # Parse results
        self._parse_pytest_output(result, exec_result.stdout)
        
        return result
    
    async def run_jest(
        self,
        test_files: Dict[str, str],
        source_files: Optional[Dict[str, str]] = None,
        tenant_id: str = "",
        timeout: int = 120,
    ) -> TestResult:
        """Run Jest tests for JavaScript/TypeScript."""
        result = TestResult()
        
        all_files = {}
        if source_files:
            all_files.update(source_files)
        all_files.update(test_files)
        
        # Add package.json if not present
        if "package.json" not in all_files:
            all_files["package.json"] = '{"scripts": {"test": "jest"}}'
        
        config = ExecutionConfig(
            language="javascript",
            timeout_seconds=timeout,
            packages=["jest"],
            memory_mb=512,
        )
        
        exec_result = await self.executor.execute_tests(
            all_files,
            config,
            tenant_id,
            test_command=["npx", "jest", "--verbose"],
        )
        
        result.raw_output = exec_result.stdout + exec_result.stderr
        result.duration_ms = exec_result.duration_ms or 0
        
        # Parse Jest output
        self._parse_jest_output(result, exec_result.stdout)
        
        return result
    
    def _parse_pytest_output(self, result: TestResult, output: str) -> None:
        """Parse pytest output."""
        import re
        
        # Look for summary line: "X passed, Y failed, Z skipped"
        summary_match = re.search(
            r"(\d+) passed.*?(\d+) failed.*?(\d+) skipped",
            output,
            re.IGNORECASE,
        )
        if summary_match:
            result.passed = int(summary_match.group(1))
            result.failed = int(summary_match.group(2))
            result.skipped = int(summary_match.group(3))
        else:
            # Try simpler patterns
            passed_match = re.search(r"(\d+) passed", output)
            if passed_match:
                result.passed = int(passed_match.group(1))
            
            failed_match = re.search(r"(\d+) failed", output)
            if failed_match:
                result.failed = int(failed_match.group(1))
        
        result.total = result.passed + result.failed + result.skipped
        
        # Extract coverage if present
        cov_match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", output)
        if cov_match:
            result.coverage_percent = float(cov_match.group(1))
    
    def _parse_jest_output(self, result: TestResult, output: str) -> None:
        """Parse Jest output."""
        import re
        
        # Look for "Tests: X passed, Y failed"
        tests_match = re.search(r"Tests:\s+(\d+) passed.*?(\d+) failed", output)
        if tests_match:
            result.passed = int(tests_match.group(1))
            result.failed = int(tests_match.group(2))
        
        result.total = result.passed + result.failed


class LinterRunner:
    """
    Run linters in a sandbox.
    
    Supports multiple linters per language.
    """
    
    def __init__(self, executor: SandboxExecutor):
        self.executor = executor
    
    async def run_ruff(
        self,
        files: Dict[str, str],
        tenant_id: str = "",
        fix: bool = False,
    ) -> LintResult:
        """Run Ruff linter for Python."""
        result = LintResult()
        
        config = ExecutionConfig(
            language="python",
            timeout_seconds=30,
            packages=["ruff"],
        )
        
        command = ["ruff", "check", "/workspace"]
        if fix:
            command.append("--fix")
        command.append("--output-format=json")
        
        exec_result = await self.executor.execute_tests(
            files,
            config,
            tenant_id,
            test_command=command,
        )
        
        result.raw_output = exec_result.stdout
        
        # Parse JSON output
        self._parse_ruff_output(result, exec_result.stdout)
        
        return result
    
    async def run_eslint(
        self,
        files: Dict[str, str],
        tenant_id: str = "",
    ) -> LintResult:
        """Run ESLint for JavaScript/TypeScript."""
        result = LintResult()
        
        # Add eslint config if not present
        if ".eslintrc.json" not in files:
            files[".eslintrc.json"] = '{"env": {"node": true, "es2021": true}}'
        
        config = ExecutionConfig(
            language="javascript",
            timeout_seconds=30,
            packages=["eslint"],
        )
        
        exec_result = await self.executor.execute_tests(
            files,
            config,
            tenant_id,
            test_command=["npx", "eslint", "--format", "json", "/workspace"],
        )
        
        result.raw_output = exec_result.stdout
        self._parse_eslint_output(result, exec_result.stdout)
        
        return result
    
    def _parse_ruff_output(self, result: LintResult, output: str) -> None:
        """Parse Ruff JSON output."""
        import json
        
        try:
            issues = json.loads(output) if output.strip() else []
            result.issues = issues
            
            for issue in issues:
                severity = issue.get("severity", "warning")
                if severity == "error":
                    result.error_count += 1
                elif severity == "warning":
                    result.warning_count += 1
                else:
                    result.info_count += 1
                    
        except json.JSONDecodeError:
            # Count lines as issues
            result.warning_count = len(output.strip().split("\n")) if output.strip() else 0
    
    def _parse_eslint_output(self, result: LintResult, output: str) -> None:
        """Parse ESLint JSON output."""
        import json
        
        try:
            data = json.loads(output) if output.strip() else []
            
            for file_result in data:
                for message in file_result.get("messages", []):
                    result.issues.append({
                        "file": file_result.get("filePath"),
                        "line": message.get("line"),
                        "column": message.get("column"),
                        "message": message.get("message"),
                        "rule": message.get("ruleId"),
                        "severity": "error" if message.get("severity") == 2 else "warning",
                    })
                    
                    if message.get("severity") == 2:
                        result.error_count += 1
                    else:
                        result.warning_count += 1
                        
        except json.JSONDecodeError:
            pass


class BuildRunner:
    """
    Run builds in a sandbox.
    """
    
    def __init__(self, executor: SandboxExecutor):
        self.executor = executor
    
    async def build_python_package(
        self,
        files: Dict[str, str],
        tenant_id: str = "",
    ) -> BuildResult:
        """Build a Python package."""
        result = BuildResult()
        
        config = ExecutionConfig(
            language="python",
            timeout_seconds=120,
            packages=["build", "setuptools", "wheel"],
            capture_files=["dist/*"],
        )
        
        exec_result = await self.executor.execute_tests(
            files,
            config,
            tenant_id,
            test_command=["python", "-m", "build"],
        )
        
        result.raw_output = exec_result.stdout + exec_result.stderr
        result.duration_ms = exec_result.duration_ms or 0
        result.success = exec_result.exit_code == 0
        
        if exec_result.artifacts:
            result.artifacts = list(exec_result.artifacts.keys())
        
        return result
    
    async def build_npm_package(
        self,
        files: Dict[str, str],
        tenant_id: str = "",
    ) -> BuildResult:
        """Build an npm package."""
        result = BuildResult()
        
        config = ExecutionConfig(
            language="javascript",
            timeout_seconds=120,
            capture_files=["dist/*", "build/*"],
        )
        
        # Install deps then build
        exec_result = await self.executor.execute_tests(
            files,
            config,
            tenant_id,
            test_command=["sh", "-c", "npm install && npm run build"],
        )
        
        result.raw_output = exec_result.stdout + exec_result.stderr
        result.duration_ms = exec_result.duration_ms or 0
        result.success = exec_result.exit_code == 0
        
        if exec_result.artifacts:
            result.artifacts = list(exec_result.artifacts.keys())
        
        return result


class REPLRunner:
    """
    Interactive REPL-style execution.
    """
    
    def __init__(self, executor: SandboxExecutor):
        self.executor = executor
    
    async def evaluate(
        self,
        expression: str,
        language: str = "python",
        tenant_id: str = "",
        context: Optional[Dict[str, str]] = None,
    ) -> ExecutionResult:
        """
        Evaluate an expression and return the result.
        
        Args:
            expression: Expression to evaluate
            language: Programming language
            tenant_id: Tenant ID
            context: Optional context (setup code)
            
        Returns:
            ExecutionResult
        """
        # Wrap expression to print result
        if language == "python":
            code = f"print(repr({expression}))"
            if context:
                code = "\n".join(context.values()) + "\n" + code
        elif language in ("javascript", "node"):
            code = f"console.log({expression})"
            if context:
                code = "\n".join(context.values()) + "\n" + code
        else:
            code = expression
        
        config = ExecutionConfig(
            language=language,
            timeout_seconds=10,
            memory_mb=128,
        )
        
        return await self.executor.execute_code(
            code,
            config,
            tenant_id,
        )
