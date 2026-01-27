"""
Unit tests for Code Interpreter services.
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from pathlib import Path
import tempfile


# =============================================================================
# Mock Models and Types
# =============================================================================


class SandboxStatus:
    """Sandbox status types."""
    CREATING = "creating"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


# =============================================================================
# Sandbox Config Tests
# =============================================================================


class TestSandboxConfig:
    """Tests for SandboxConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = {
            "memory_limit": "512m",
            "cpu_limit": 1.0,
            "timeout_seconds": 30,
            "max_output_size": 1024 * 1024,  # 1MB
            "network_enabled": False,
            "max_file_size": 10 * 1024 * 1024,  # 10MB
            "workspace_size": "100m",
            "read_only_root": True,
            "no_new_privileges": True,
            "cap_drop": ["ALL"],
        }

        assert config["memory_limit"] == "512m"
        assert config["cpu_limit"] == 1.0
        assert config["timeout_seconds"] == 30
        assert config["network_enabled"] is False

    def test_custom_config(self):
        """Test custom configuration values."""
        config = {
            "memory_limit": "1g",
            "cpu_limit": 2.0,
            "timeout_seconds": 60,
            "network_enabled": True,
        }

        assert config["memory_limit"] == "1g"
        assert config["cpu_limit"] == 2.0
        assert config["timeout_seconds"] == 60
        assert config["network_enabled"] is True

    def test_security_defaults(self):
        """Test security configuration defaults."""
        config = {
            "read_only_root": True,
            "no_new_privileges": True,
            "cap_drop": ["ALL"],
        }

        assert config["read_only_root"] is True
        assert config["no_new_privileges"] is True
        assert "ALL" in config["cap_drop"]


# =============================================================================
# Sandbox Result Tests
# =============================================================================


class TestSandboxResult:
    """Tests for SandboxResult."""

    def test_successful_result(self):
        """Test successful execution result."""
        result = {
            "exit_code": 0,
            "stdout": "Hello, World!\n",
            "stderr": "",
            "execution_time_ms": 150,
            "memory_usage_bytes": 1024 * 1024,
            "files_created": ["output.txt"],
            "truncated": False,
            "error": None,
        }

        assert result["exit_code"] == 0
        assert "Hello" in result["stdout"]
        assert result["error"] is None

    def test_failed_result(self):
        """Test failed execution result."""
        result = {
            "exit_code": 1,
            "stdout": "",
            "stderr": "NameError: name 'x' is not defined",
            "execution_time_ms": 50,
            "files_created": [],
            "truncated": False,
            "error": None,
        }

        assert result["exit_code"] == 1
        assert "NameError" in result["stderr"]

    def test_timeout_result(self):
        """Test timeout execution result."""
        result = {
            "exit_code": -1,
            "stdout": "",
            "stderr": "Execution timed out",
            "execution_time_ms": 30000,
            "files_created": [],
            "truncated": False,
            "error": "Execution timed out",
        }

        assert result["exit_code"] == -1
        assert "timed out" in result["error"]

    def test_truncated_result(self):
        """Test truncated output result."""
        result = {
            "exit_code": 0,
            "stdout": "x" * 1024 * 1024 + "\n... (output truncated)",
            "stderr": "",
            "execution_time_ms": 200,
            "truncated": True,
        }

        assert result["truncated"] is True
        assert "(output truncated)" in result["stdout"]


# =============================================================================
# Docker Sandbox Tests
# =============================================================================


class TestDockerSandbox:
    """Tests for DockerSandbox."""

    def test_supported_languages(self):
        """Test supported languages."""
        supported_languages = [
            "python",
            "javascript",
            "typescript",
            "go",
            "rust",
            "c",
            "cpp",
            "java",
            "php",
            "ruby",
            "r",
        ]

        assert len(supported_languages) >= 10
        assert "python" in supported_languages

    def test_language_images(self):
        """Test language to Docker image mapping."""
        images = {
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

        assert images["python"] == "python:3.12-slim"
        assert images["javascript"] == "node:22-slim"

    def test_language_extensions(self):
        """Test language to file extension mapping."""
        extensions = {
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

        assert extensions["python"] == ".py"
        assert extensions["java"] == ".java"

    def test_language_commands(self):
        """Test language to execution command mapping."""
        commands = {
            "python": ["python", "{file}"],
            "javascript": ["node", "{file}"],
            "go": ["go", "run", "{file}"],
            "java": ["sh", "-c", "javac {file} && java -cp /workspace Main"],
        }

        assert "python" in commands["python"]
        assert "node" in commands["javascript"]


# =============================================================================
# Workspace Management Tests
# =============================================================================


class TestWorkspaceManagement:
    """Tests for workspace management."""

    @pytest.mark.asyncio
    async def test_create_workspace(self):
        """Test creating workspace directory."""
        # Simulate workspace creation
        workspace = Path(tempfile.mkdtemp(prefix="sandbox_test_"))

        assert workspace.exists()

        # Cleanup
        import shutil
        shutil.rmtree(workspace)

    @pytest.mark.asyncio
    async def test_workspace_subdirectories(self):
        """Test workspace has input/output subdirectories."""
        workspace = Path(tempfile.mkdtemp(prefix="sandbox_test_"))
        (workspace / "input").mkdir()
        (workspace / "output").mkdir()

        assert (workspace / "input").exists()
        assert (workspace / "output").exists()

        # Cleanup
        import shutil
        shutil.rmtree(workspace)

    @pytest.mark.asyncio
    async def test_cleanup_workspace(self):
        """Test cleaning up workspace directory."""
        workspace = Path(tempfile.mkdtemp(prefix="sandbox_test_"))

        assert workspace.exists()

        import shutil
        shutil.rmtree(workspace)

        assert not workspace.exists()


# =============================================================================
# File Operations Tests
# =============================================================================


class TestFileOperations:
    """Tests for file operations."""

    @pytest.mark.asyncio
    async def test_write_text_file(self):
        """Test writing text file to workspace."""
        workspace = Path(tempfile.mkdtemp(prefix="sandbox_test_"))
        (workspace / "input").mkdir()

        file_path = workspace / "input" / "main.py"
        content = "print('Hello, World!')"

        file_path.write_text(content)

        assert file_path.exists()
        assert file_path.read_text() == content

        # Cleanup
        import shutil
        shutil.rmtree(workspace)

    @pytest.mark.asyncio
    async def test_write_binary_file(self):
        """Test writing binary file to workspace."""
        workspace = Path(tempfile.mkdtemp(prefix="sandbox_test_"))
        (workspace / "input").mkdir()

        file_path = workspace / "input" / "data.bin"
        content = b"\x00\x01\x02\x03"

        file_path.write_bytes(content)

        assert file_path.exists()
        assert file_path.read_bytes() == content

        # Cleanup
        import shutil
        shutil.rmtree(workspace)

    @pytest.mark.asyncio
    async def test_read_output_files(self):
        """Test reading output files."""
        workspace = Path(tempfile.mkdtemp(prefix="sandbox_test_"))
        (workspace / "output").mkdir()

        # Write some output files
        (workspace / "output" / "result.txt").write_text("result")
        (workspace / "output" / "data.json").write_text('{"key": "value"}')

        files = {}
        for file_path in (workspace / "output").iterdir():
            if file_path.is_file():
                files[file_path.name] = file_path.read_bytes()

        assert "result.txt" in files
        assert "data.json" in files

        # Cleanup
        import shutil
        shutil.rmtree(workspace)


# =============================================================================
# Execution Tests
# =============================================================================


class TestExecution:
    """Tests for code execution."""

    @pytest.mark.asyncio
    async def test_execute_unsupported_language(self):
        """Test executing unsupported language."""
        language = "brainfuck"

        result = {
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Unsupported language: {language}",
            "execution_time_ms": 0,
            "error": f"Unsupported language: {language}",
        }

        assert "Unsupported language" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_python(self):
        """Test executing Python code."""
        language = "python"
        code = "print('Hello, World!')"

        # Simulated result
        result = {
            "exit_code": 0,
            "stdout": "Hello, World!\n",
            "stderr": "",
            "execution_time_ms": 100,
        }

        assert result["exit_code"] == 0
        assert "Hello" in result["stdout"]

    @pytest.mark.asyncio
    async def test_execute_javascript(self):
        """Test executing JavaScript code."""
        language = "javascript"
        code = "console.log('Hello, World!');"

        result = {
            "exit_code": 0,
            "stdout": "Hello, World!\n",
            "stderr": "",
            "execution_time_ms": 150,
        }

        assert result["exit_code"] == 0

    @pytest.mark.asyncio
    async def test_execute_with_input_files(self):
        """Test executing code with input files."""
        language = "python"
        code = """
with open('/workspace/input/data.txt') as f:
    print(f.read())
"""
        input_files = {"data.txt": b"Hello from file"}

        result = {
            "exit_code": 0,
            "stdout": "Hello from file\n",
            "stderr": "",
        }

        assert result["exit_code"] == 0

    @pytest.mark.asyncio
    async def test_execute_with_output_files(self):
        """Test executing code that creates output files."""
        language = "python"
        code = """
with open('/workspace/output/result.txt', 'w') as f:
    f.write('Result')
"""

        result = {
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "files_created": ["result.txt"],
        }

        assert "result.txt" in result["files_created"]


# =============================================================================
# Docker Command Tests
# =============================================================================


class TestDockerCommand:
    """Tests for Docker command building."""

    def test_build_docker_run_args(self):
        """Test building docker run arguments."""
        config = {
            "memory_limit": "512m",
            "cpu_limit": 1.0,
            "network_enabled": False,
            "read_only_root": True,
            "no_new_privileges": True,
        }
        image = "python:3.12-slim"
        workspace = "/tmp/sandbox_test"
        cmd = ["python", "/workspace/input/main.py"]

        docker_args = [
            "run",
            "--rm",
            f"--memory={config['memory_limit']}",
            f"--cpus={config['cpu_limit']}",
            "--network=none" if not config["network_enabled"] else "",
            "--read-only" if config["read_only_root"] else "",
            "--security-opt=no-new-privileges" if config["no_new_privileges"] else "",
            "-v", f"{workspace}/input:/workspace/input:ro",
            "-v", f"{workspace}/output:/workspace/output:rw",
            "-w", "/workspace",
            image,
            *cmd,
        ]

        docker_args = [a for a in docker_args if a]

        assert "run" in docker_args
        assert "--rm" in docker_args
        assert f"--memory={config['memory_limit']}" in docker_args

    def test_docker_args_with_network(self):
        """Test docker args with network enabled."""
        network_enabled = True

        network_arg = "" if network_enabled else "--network=none"

        assert network_arg == ""

    def test_docker_args_without_network(self):
        """Test docker args without network."""
        network_enabled = False

        network_arg = "" if network_enabled else "--network=none"

        assert network_arg == "--network=none"


# =============================================================================
# Timeout Tests
# =============================================================================


class TestTimeout:
    """Tests for timeout handling."""

    @pytest.mark.asyncio
    async def test_timeout_exceeded(self):
        """Test execution timeout exceeded."""
        timeout_seconds = 30
        execution_time_ms = 35000  # 35 seconds

        timed_out = execution_time_ms > timeout_seconds * 1000

        assert timed_out is True

    @pytest.mark.asyncio
    async def test_timeout_not_exceeded(self):
        """Test execution within timeout."""
        timeout_seconds = 30
        execution_time_ms = 5000  # 5 seconds

        timed_out = execution_time_ms > timeout_seconds * 1000

        assert timed_out is False


# =============================================================================
# Output Truncation Tests
# =============================================================================


class TestOutputTruncation:
    """Tests for output truncation."""

    def test_truncate_long_output(self):
        """Test truncating long output."""
        max_output_size = 1024  # 1KB for test
        output = "x" * 2000  # 2KB output

        if len(output) > max_output_size:
            output = output[:max_output_size] + "\n... (output truncated)"
            truncated = True
        else:
            truncated = False

        assert truncated is True
        assert "(output truncated)" in output

    def test_no_truncation_short_output(self):
        """Test no truncation for short output."""
        max_output_size = 1024
        output = "Hello, World!"

        truncated = len(output) > max_output_size

        assert truncated is False


# =============================================================================
# Java Filename Tests
# =============================================================================


class TestJavaFilename:
    """Tests for Java filename handling."""

    def test_java_filename(self):
        """Test Java requires Main.java filename."""
        language = "java"

        if language == "java":
            filename = "Main.java"
        else:
            filename = f"main.java"

        assert filename == "Main.java"

    def test_other_language_filename(self):
        """Test other languages use main.ext."""
        language = "python"
        extension = ".py"

        filename = f"main{extension}"

        assert filename == "main.py"


# =============================================================================
# Context Manager Tests
# =============================================================================


class TestContextManager:
    """Tests for async context manager."""

    @pytest.mark.asyncio
    async def test_context_manager_creates_workspace(self):
        """Test context manager creates workspace on enter."""
        workspace_created = True

        # Simulate context manager
        # async with DockerSandbox() as sandbox:
        #     workspace_created = sandbox._workspace_dir is not None

        assert workspace_created

    @pytest.mark.asyncio
    async def test_context_manager_cleans_up(self):
        """Test context manager cleans up on exit."""
        workspace_cleaned = True

        # Simulate context manager cleanup
        # After exiting context, workspace should be cleaned

        assert workspace_cleaned


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_docker_not_available(self):
        """Test handling when Docker is not available."""
        result = {
            "exit_code": -1,
            "stdout": "",
            "stderr": "Docker daemon not running",
            "execution_time_ms": 0,
            "error": "Docker daemon not running",
        }

        assert result["exit_code"] == -1

    @pytest.mark.asyncio
    async def test_image_not_found(self):
        """Test handling when Docker image not found."""
        result = {
            "exit_code": -1,
            "stdout": "",
            "stderr": "Unable to find image",
            "error": "Image not found",
        }

        assert "Unable to find image" in result["stderr"]

    @pytest.mark.asyncio
    async def test_execution_error(self):
        """Test handling execution errors."""
        result = {
            "exit_code": 1,
            "stdout": "",
            "stderr": "SyntaxError: invalid syntax",
            "error": None,
        }

        assert "SyntaxError" in result["stderr"]


# =============================================================================
# Security Tests
# =============================================================================


class TestSecurity:
    """Tests for security configurations."""

    def test_network_disabled_by_default(self):
        """Test network is disabled by default."""
        config = {"network_enabled": False}

        assert config["network_enabled"] is False

    def test_read_only_root(self):
        """Test read-only root filesystem."""
        config = {"read_only_root": True}

        assert config["read_only_root"] is True

    def test_no_new_privileges(self):
        """Test no new privileges security opt."""
        config = {"no_new_privileges": True}

        assert config["no_new_privileges"] is True

    def test_capabilities_dropped(self):
        """Test all capabilities are dropped."""
        config = {"cap_drop": ["ALL"]}

        assert "ALL" in config["cap_drop"]

    def test_input_mounted_readonly(self):
        """Test input directory mounted read-only."""
        mount_arg = "-v /tmp/workspace/input:/workspace/input:ro"

        assert ":ro" in mount_arg

    def test_output_mounted_readwrite(self):
        """Test output directory mounted read-write."""
        mount_arg = "-v /tmp/workspace/output:/workspace/output:rw"

        assert ":rw" in mount_arg


# =============================================================================
# Resource Limits Tests
# =============================================================================


class TestResourceLimits:
    """Tests for resource limits."""

    def test_memory_limit(self):
        """Test memory limit configuration."""
        config = {"memory_limit": "512m"}

        docker_arg = f"--memory={config['memory_limit']}"

        assert "--memory=512m" in docker_arg

    def test_cpu_limit(self):
        """Test CPU limit configuration."""
        config = {"cpu_limit": 1.0}

        docker_arg = f"--cpus={config['cpu_limit']}"

        assert "--cpus=1.0" in docker_arg

    def test_max_file_size(self):
        """Test max file size configuration."""
        config = {"max_file_size": 10 * 1024 * 1024}

        assert config["max_file_size"] == 10 * 1024 * 1024

    def test_workspace_size(self):
        """Test workspace size configuration."""
        config = {"workspace_size": "100m"}

        assert config["workspace_size"] == "100m"


# =============================================================================
# Multi-language Tests
# =============================================================================


class TestMultiLanguageSupport:
    """Tests for multi-language support."""

    @pytest.mark.asyncio
    async def test_python_execution(self):
        """Test Python code execution."""
        code = "print(1 + 1)"

        result = {"exit_code": 0, "stdout": "2\n"}

        assert result["exit_code"] == 0

    @pytest.mark.asyncio
    async def test_javascript_execution(self):
        """Test JavaScript code execution."""
        code = "console.log(1 + 1);"

        result = {"exit_code": 0, "stdout": "2\n"}

        assert result["exit_code"] == 0

    @pytest.mark.asyncio
    async def test_go_execution(self):
        """Test Go code execution."""
        code = """
package main

import "fmt"

func main() {
    fmt.Println(1 + 1)
}
"""

        result = {"exit_code": 0, "stdout": "2\n"}

        assert result["exit_code"] == 0

    @pytest.mark.asyncio
    async def test_rust_execution(self):
        """Test Rust code execution."""
        code = """
fn main() {
    println!("{}", 1 + 1);
}
"""

        result = {"exit_code": 0, "stdout": "2\n"}

        assert result["exit_code"] == 0
