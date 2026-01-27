"""Docker-based sandboxed execution environment for code interpreter."""

import asyncio
import os
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

import aiofiles
import structlog

logger = structlog.get_logger()


class SandboxStatus(str, Enum):
    """Sandbox container status."""
    CREATING = "creating"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class SandboxConfig:
    """Configuration for sandbox environment."""

    # Resource limits
    memory_limit: str = "512m"
    cpu_limit: float = 1.0
    timeout_seconds: int = 30
    max_output_size: int = 1024 * 1024  # 1MB

    # Network
    network_enabled: bool = False

    # File system
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    workspace_size: str = "100m"

    # Security
    read_only_root: bool = True
    no_new_privileges: bool = True
    cap_drop: list[str] = field(default_factory=lambda: ["ALL"])


@dataclass
class SandboxResult:
    """Result from sandbox execution."""

    exit_code: int
    stdout: str
    stderr: str
    execution_time_ms: int
    memory_usage_bytes: int | None = None
    files_created: list[str] = field(default_factory=list)
    truncated: bool = False
    error: str | None = None


class DockerSandbox:
    """Docker-based sandboxed execution environment."""

    # Docker images for each language
    LANGUAGE_IMAGES = {
        "python": "python:3.12-slim",
        "javascript": "node:22-slim",
        "typescript": "node:22-slim",
        "go": "golang:1.23-alpine",
        "rust": "rust:1.83-slim",
        "c": "gcc:14",
        "cpp": "gcc:14",
        "java": "openjdk:21-slim",
        "php": "php:8.4-cli",
        "ruby": "ruby:3.3-slim",
        "r": "r-base:4.4.2",
    }

    # File extensions for each language
    LANGUAGE_EXTENSIONS = {
        "python": ".py",
        "javascript": ".js",
        "typescript": ".ts",
        "go": ".go",
        "rust": ".rs",
        "c": ".c",
        "cpp": ".cpp",
        "java": ".java",
        "php": ".php",
        "ruby": ".rb",
        "r": ".R",
    }

    # Execution commands for each language
    LANGUAGE_COMMANDS = {
        "python": ["python", "{file}"],
        "javascript": ["node", "{file}"],
        "typescript": ["npx", "ts-node", "{file}"],
        "go": ["go", "run", "{file}"],
        "rust": ["sh", "-c", "rustc {file} -o /tmp/out && /tmp/out"],
        "c": ["sh", "-c", "gcc {file} -o /tmp/out && /tmp/out"],
        "cpp": ["sh", "-c", "g++ {file} -o /tmp/out && /tmp/out"],
        "java": ["sh", "-c", "javac {file} && java -cp /workspace Main"],
        "php": ["php", "{file}"],
        "ruby": ["ruby", "{file}"],
        "r": ["Rscript", "{file}"],
    }

    def __init__(self, config: SandboxConfig | None = None):
        self.config = config or SandboxConfig()
        self._container_id: str | None = None
        self._workspace_dir: Path | None = None
        self._session_id: str = str(uuid.uuid4())
        self._status = SandboxStatus.STOPPED

    async def _run_docker_command(
        self,
        args: list[str],
        timeout: int | None = None,
    ) -> tuple[int, str, str]:
        """Run a docker command and return exit code, stdout, stderr."""
        timeout = timeout or self.config.timeout_seconds

        try:
            process = await asyncio.create_subprocess_exec(
                "docker",
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )

            return (
                process.returncode or 0,
                stdout.decode("utf-8", errors="replace"),
                stderr.decode("utf-8", errors="replace"),
            )

        except asyncio.TimeoutError:
            if process:
                process.kill()
                await process.wait()
            return -1, "", "Execution timed out"
        except Exception as e:
            logger.error("Docker command failed", error=str(e), args=args)
            return -1, "", str(e)

    async def create_workspace(self) -> Path:
        """Create a temporary workspace directory."""
        self._workspace_dir = Path(tempfile.mkdtemp(prefix=f"sandbox_{self._session_id}_"))

        # Create subdirectories
        (self._workspace_dir / "input").mkdir(exist_ok=True)
        (self._workspace_dir / "output").mkdir(exist_ok=True)

        logger.info("Created sandbox workspace", path=str(self._workspace_dir))
        return self._workspace_dir

    async def cleanup_workspace(self) -> None:
        """Clean up the workspace directory."""
        if self._workspace_dir and self._workspace_dir.exists():
            import shutil
            shutil.rmtree(self._workspace_dir, ignore_errors=True)
            logger.info("Cleaned up sandbox workspace", path=str(self._workspace_dir))
            self._workspace_dir = None

    async def write_file(self, filename: str, content: str | bytes) -> Path:
        """Write a file to the workspace."""
        if not self._workspace_dir:
            await self.create_workspace()

        file_path = self._workspace_dir / "input" / filename

        if isinstance(content, str):
            async with aiofiles.open(file_path, "w") as f:
                await f.write(content)
        else:
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(content)

        return file_path

    async def read_output_files(self) -> dict[str, bytes]:
        """Read all files from the output directory."""
        if not self._workspace_dir:
            return {}

        output_dir = self._workspace_dir / "output"
        files = {}

        for file_path in output_dir.iterdir():
            if file_path.is_file():
                async with aiofiles.open(file_path, "rb") as f:
                    files[file_path.name] = await f.read()

        return files

    async def execute(
        self,
        language: str,
        code: str,
        input_files: dict[str, bytes] | None = None,
        stdin: str | None = None,
    ) -> SandboxResult:
        """Execute code in a sandboxed Docker container."""
        start_time = datetime.now(UTC)

        # Validate language
        if language not in self.LANGUAGE_IMAGES:
            return SandboxResult(
                exit_code=-1,
                stdout="",
                stderr=f"Unsupported language: {language}",
                execution_time_ms=0,
                error=f"Unsupported language: {language}",
            )

        # Create workspace
        if not self._workspace_dir:
            await self.create_workspace()

        try:
            # Write code file
            extension = self.LANGUAGE_EXTENSIONS[language]
            filename = f"main{extension}"
            if language == "java":
                filename = "Main.java"

            await self.write_file(filename, code)

            # Write input files
            if input_files:
                for name, content in input_files.items():
                    await self.write_file(name, content)

            # Build docker command
            image = self.LANGUAGE_IMAGES[language]
            cmd_template = self.LANGUAGE_COMMANDS[language]
            cmd = [c.replace("{file}", f"/workspace/input/{filename}") for c in cmd_template]

            docker_args = [
                "run",
                "--rm",
                f"--memory={self.config.memory_limit}",
                f"--cpus={self.config.cpu_limit}",
                "--network=none" if not self.config.network_enabled else "",
                "--read-only" if self.config.read_only_root else "",
                "--security-opt=no-new-privileges" if self.config.no_new_privileges else "",
                "-v", f"{self._workspace_dir}/input:/workspace/input:ro",
                "-v", f"{self._workspace_dir}/output:/workspace/output:rw",
                "-w", "/workspace",
                image,
                *cmd,
            ]

            # Remove empty strings
            docker_args = [a for a in docker_args if a]

            # Execute
            exit_code, stdout, stderr = await self._run_docker_command(
                docker_args,
                timeout=self.config.timeout_seconds,
            )

            # Calculate execution time
            execution_time_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)

            # Truncate output if needed
            truncated = False
            if len(stdout) > self.config.max_output_size:
                stdout = stdout[:self.config.max_output_size] + "\n... (output truncated)"
                truncated = True
            if len(stderr) > self.config.max_output_size:
                stderr = stderr[:self.config.max_output_size] + "\n... (output truncated)"
                truncated = True

            # Get created files
            output_files = await self.read_output_files()

            return SandboxResult(
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                execution_time_ms=execution_time_ms,
                files_created=list(output_files.keys()),
                truncated=truncated,
            )

        except Exception as e:
            logger.error("Sandbox execution failed", error=str(e))
            return SandboxResult(
                exit_code=-1,
                stdout="",
                stderr=str(e),
                execution_time_ms=int((datetime.now(UTC) - start_time).total_seconds() * 1000),
                error=str(e),
            )
        finally:
            # Always cleanup
            await self.cleanup_workspace()

    async def __aenter__(self) -> "DockerSandbox":
        """Async context manager entry."""
        await self.create_workspace()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.cleanup_workspace()
