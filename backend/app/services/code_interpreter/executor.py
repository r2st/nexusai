"""Code execution service with multi-language support."""

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

import structlog
from pydantic import BaseModel

from app.services.code_interpreter.sandbox import DockerSandbox, SandboxConfig, SandboxResult

logger = structlog.get_logger()


class SupportedLanguage(str, Enum):
    """Supported programming languages for code execution."""

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    GO = "go"
    RUST = "rust"
    C = "c"
    CPP = "cpp"
    JAVA = "java"
    PHP = "php"
    RUBY = "ruby"
    R = "r"


class ExecutionStatus(str, Enum):
    """Execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class ExecutionResult:
    """Result of code execution."""

    id: str
    language: SupportedLanguage
    status: ExecutionStatus
    exit_code: int
    stdout: str
    stderr: str
    execution_time_ms: int
    created_at: datetime
    completed_at: datetime | None = None
    files_created: list[str] = field(default_factory=list)
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "language": self.language.value,
            "status": self.status.value,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "execution_time_ms": self.execution_time_ms,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "files_created": self.files_created,
            "error": self.error,
            "metadata": self.metadata,
        }


class ExecutionRequest(BaseModel):
    """Request to execute code."""

    language: SupportedLanguage
    code: str
    input_files: dict[str, str] | None = None  # filename -> base64 content
    stdin: str | None = None
    timeout_seconds: int = 30
    memory_limit_mb: int = 512


class CodeExecutor:
    """Service for executing code in sandboxed environments."""

    # Language detection patterns
    LANGUAGE_PATTERNS = {
        SupportedLanguage.PYTHON: [
            r"^import\s+\w+",
            r"^from\s+\w+\s+import",
            r"^def\s+\w+\s*\(",
            r"^class\s+\w+[\(:]",
            r"print\s*\(",
        ],
        SupportedLanguage.JAVASCRIPT: [
            r"^const\s+\w+\s*=",
            r"^let\s+\w+\s*=",
            r"^var\s+\w+\s*=",
            r"^function\s+\w+\s*\(",
            r"console\.log\s*\(",
            r"^import\s+.*\s+from\s+['\"]",
            r"require\s*\(['\"]",
        ],
        SupportedLanguage.TYPESCRIPT: [
            r":\s*(string|number|boolean|any)\s*[;=]",
            r"interface\s+\w+\s*\{",
            r"type\s+\w+\s*=",
            r"<[A-Z]\w*>",
        ],
        SupportedLanguage.GO: [
            r"^package\s+\w+",
            r"^func\s+\w+\s*\(",
            r"^import\s+\(",
            r"fmt\.Print",
        ],
        SupportedLanguage.RUST: [
            r"^fn\s+\w+\s*\(",
            r"^use\s+\w+::",
            r"^let\s+mut\s+",
            r"println!\s*\(",
            r"^struct\s+\w+",
        ],
        SupportedLanguage.C: [
            r"^#include\s*<\w+\.h>",
            r"^int\s+main\s*\(",
            r"printf\s*\(",
            r"^void\s+\w+\s*\(",
        ],
        SupportedLanguage.CPP: [
            r"^#include\s*<iostream>",
            r"^#include\s*<\w+>",
            r"std::\w+",
            r"cout\s*<<",
            r"^class\s+\w+\s*\{",
        ],
        SupportedLanguage.JAVA: [
            r"^public\s+class\s+\w+",
            r"^import\s+java\.",
            r"System\.out\.print",
            r"public\s+static\s+void\s+main",
        ],
        SupportedLanguage.PHP: [
            r"^<\?php",
            r"^\$\w+\s*=",
            r"^function\s+\w+\s*\(",
            r"echo\s+",
        ],
        SupportedLanguage.RUBY: [
            r"^def\s+\w+",
            r"^class\s+\w+",
            r"puts\s+",
            r"^require\s+['\"]",
            r"\.each\s+do\s*\|",
        ],
        SupportedLanguage.R: [
            r"<-\s*function\s*\(",
            r"library\s*\(",
            r"print\s*\(",
            r"c\s*\(",
            r"data\.frame\s*\(",
        ],
    }

    def __init__(self, default_config: SandboxConfig | None = None):
        self.default_config = default_config or SandboxConfig()
        self._execution_history: dict[str, ExecutionResult] = {}

    def detect_language(self, code: str) -> SupportedLanguage | None:
        """Detect the programming language from code content."""
        scores: dict[SupportedLanguage, int] = {lang: 0 for lang in SupportedLanguage}

        for language, patterns in self.LANGUAGE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, code, re.MULTILINE):
                    scores[language] += 1

        # Get the language with highest score
        max_score = max(scores.values())
        if max_score > 0:
            for lang, score in scores.items():
                if score == max_score:
                    return lang

        # Default to Python if no match
        return SupportedLanguage.PYTHON

    async def execute(
        self,
        request: ExecutionRequest,
        session_id: str | None = None,
    ) -> ExecutionResult:
        """Execute code and return the result."""
        execution_id = str(uuid4())
        created_at = datetime.now(UTC)

        logger.info(
            "Starting code execution",
            execution_id=execution_id,
            language=request.language.value,
            code_length=len(request.code),
        )

        # Create sandbox config
        config = SandboxConfig(
            timeout_seconds=request.timeout_seconds,
            memory_limit=f"{request.memory_limit_mb}m",
        )

        # Execute in sandbox
        sandbox = DockerSandbox(config)

        try:
            # Decode input files if present
            input_files: dict[str, bytes] | None = None
            if request.input_files:
                import base64
                input_files = {
                    name: base64.b64decode(content)
                    for name, content in request.input_files.items()
                }

            result = await sandbox.execute(
                language=request.language.value,
                code=request.code,
                input_files=input_files,
                stdin=request.stdin,
            )

            # Determine status
            if result.error:
                status = ExecutionStatus.FAILED
            elif result.exit_code == -1 and "timed out" in result.stderr.lower():
                status = ExecutionStatus.TIMEOUT
            elif result.exit_code == 0:
                status = ExecutionStatus.COMPLETED
            else:
                status = ExecutionStatus.FAILED

            execution_result = ExecutionResult(
                id=execution_id,
                language=request.language,
                status=status,
                exit_code=result.exit_code,
                stdout=result.stdout,
                stderr=result.stderr,
                execution_time_ms=result.execution_time_ms,
                created_at=created_at,
                completed_at=datetime.now(UTC),
                files_created=result.files_created,
                error=result.error,
                metadata={
                    "truncated": result.truncated,
                    "session_id": session_id,
                },
            )

        except Exception as e:
            logger.error("Code execution failed", error=str(e), execution_id=execution_id)
            execution_result = ExecutionResult(
                id=execution_id,
                language=request.language,
                status=ExecutionStatus.FAILED,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                execution_time_ms=int((datetime.now(UTC) - created_at).total_seconds() * 1000),
                created_at=created_at,
                completed_at=datetime.now(UTC),
                error=str(e),
            )

        # Store in history
        self._execution_history[execution_id] = execution_result

        logger.info(
            "Code execution completed",
            execution_id=execution_id,
            status=execution_result.status.value,
            execution_time_ms=execution_result.execution_time_ms,
        )

        return execution_result

    def get_execution(self, execution_id: str) -> ExecutionResult | None:
        """Get execution result by ID."""
        return self._execution_history.get(execution_id)

    def get_supported_languages(self) -> list[dict[str, str]]:
        """Get list of supported languages with details."""
        return [
            {
                "id": lang.value,
                "name": lang.value.title(),
                "extension": DockerSandbox.LANGUAGE_EXTENSIONS.get(lang.value, ""),
                "image": DockerSandbox.LANGUAGE_IMAGES.get(lang.value, ""),
            }
            for lang in SupportedLanguage
        ]


# Global executor instance
code_executor = CodeExecutor()
