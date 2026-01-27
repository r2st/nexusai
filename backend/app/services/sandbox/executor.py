"""
Sandbox Executor

High-level interface for safe code execution.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import asyncio
import logging
import uuid

from .containers import (
    ContainerManager,
    ContainerConfig,
    SandboxContainer,
    RuntimeEnvironment,
)

logger = logging.getLogger(__name__)


class ExecutionStatus(str, Enum):
    """Status of code execution."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class ExecutionConfig:
    """Configuration for code execution."""
    # Language/runtime
    language: str = "python"
    runtime: Optional[RuntimeEnvironment] = None
    
    # Limits
    timeout_seconds: int = 30
    memory_mb: int = 256
    
    # Options
    capture_stdout: bool = True
    capture_stderr: bool = True
    capture_files: List[str] = field(default_factory=list)
    
    # Environment
    environment: Dict[str, str] = field(default_factory=dict)
    packages: List[str] = field(default_factory=list)
    
    # Security
    network_enabled: bool = False


@dataclass
class ExecutionResult:
    """Result of code execution."""
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: ExecutionStatus = ExecutionStatus.PENDING
    
    # Output
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    
    # Artifacts
    artifacts: Dict[str, bytes] = field(default_factory=dict)
    
    # Metrics
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    memory_used_mb: Optional[float] = None
    
    # Error info
    error_message: Optional[str] = None
    
    @property
    def is_success(self) -> bool:
        return self.status == ExecutionStatus.SUCCESS and self.exit_code == 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "status": self.status.value,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_ms": self.duration_ms,
            "error": self.error_message,
        }


# Language to runtime mapping
LANGUAGE_RUNTIMES = {
    "python": RuntimeEnvironment.PYTHON_3_12,
    "python3": RuntimeEnvironment.PYTHON_3_12,
    "javascript": RuntimeEnvironment.NODE_22,
    "typescript": RuntimeEnvironment.NODE_22,
    "node": RuntimeEnvironment.NODE_22,
    "go": RuntimeEnvironment.GO_1_21,
    "golang": RuntimeEnvironment.GO_1_21,
    "rust": RuntimeEnvironment.RUST_1_75,
    "java": RuntimeEnvironment.JAVA_21,
    "ruby": RuntimeEnvironment.RUBY_3_3,
}

# Language execution commands
LANGUAGE_COMMANDS = {
    "python": ["python", "-c"],
    "python3": ["python3", "-c"],
    "javascript": ["node", "-e"],
    "typescript": ["npx", "ts-node", "-e"],
    "node": ["node", "-e"],
    "go": ["go", "run"],  # Requires file
    "rust": ["rustc", "--edition", "2021", "-o", "/tmp/out"],  # Requires file
    "java": ["java"],  # Requires file
    "ruby": ["ruby", "-e"],
}


class SandboxExecutor:
    """
    High-level sandbox executor for agents.
    
    Features:
    - Multi-language support
    - Automatic container management
    - Code and file execution
    - Artifact retrieval
    - Usage tracking
    """
    
    def __init__(
        self,
        container_manager: Optional[ContainerManager] = None,
    ):
        self.container_manager = container_manager or ContainerManager()
        
        # Execution tracking
        self._executions: Dict[str, ExecutionResult] = {}
    
    async def execute_code(
        self,
        code: str,
        config: ExecutionConfig,
        tenant_id: str,
        request_id: str = "",
    ) -> ExecutionResult:
        """
        Execute code in a sandbox.
        
        Args:
            code: Code to execute
            config: Execution configuration
            tenant_id: Tenant ID
            request_id: Optional request ID
            
        Returns:
            ExecutionResult
        """
        result = ExecutionResult()
        result.started_at = datetime.utcnow()
        
        container: Optional[SandboxContainer] = None
        
        try:
            # Determine runtime
            runtime = config.runtime or LANGUAGE_RUNTIMES.get(config.language)
            if not runtime:
                result.status = ExecutionStatus.ERROR
                result.error_message = f"Unsupported language: {config.language}"
                return result
            
            # Create container
            container_config = ContainerConfig(
                runtime=runtime,
                memory_mb=config.memory_mb,
                timeout_seconds=config.timeout_seconds,
                network_enabled=config.network_enabled,
                environment=config.environment,
            )
            
            container = await self.container_manager.create(
                container_config,
                tenant_id=tenant_id,
                request_id=request_id,
            )
            
            # Install packages if needed
            if config.packages:
                await self._install_packages(container, config.language, config.packages)
            
            result.status = ExecutionStatus.RUNNING
            
            # Execute code
            if config.language in ("go", "rust", "java"):
                # Languages that need files
                exit_code, stdout, stderr = await self._execute_file_based(
                    container, code, config.language
                )
            else:
                # Languages that support inline execution
                command = LANGUAGE_COMMANDS.get(config.language, ["python", "-c"])
                exit_code, stdout, stderr = await self.container_manager.execute(
                    container.id,
                    command + [code],
                    timeout=config.timeout_seconds,
                )
            
            result.exit_code = exit_code
            result.stdout = stdout
            result.stderr = stderr
            
            # Retrieve artifacts
            if config.capture_files:
                result.artifacts = await self.container_manager.get_artifacts(
                    container.id,
                    config.capture_files,
                )
            
            # Set status
            if exit_code == 0:
                result.status = ExecutionStatus.SUCCESS
            elif exit_code == -1:
                result.status = ExecutionStatus.TIMEOUT
            else:
                result.status = ExecutionStatus.FAILURE
            
        except Exception as e:
            logger.exception(f"Execution error: {e}")
            result.status = ExecutionStatus.ERROR
            result.error_message = str(e)
            
        finally:
            result.completed_at = datetime.utcnow()
            if result.started_at:
                result.duration_ms = int(
                    (result.completed_at - result.started_at).total_seconds() * 1000
                )
            
            # Cleanup container
            if container:
                await self.container_manager.destroy(container.id)
            
            # Track execution
            self._executions[result.execution_id] = result
        
        return result
    
    async def execute_file(
        self,
        filename: str,
        content: str,
        config: ExecutionConfig,
        tenant_id: str,
        args: Optional[List[str]] = None,
    ) -> ExecutionResult:
        """
        Execute a file in a sandbox.
        
        Args:
            filename: Filename to create
            content: File content
            config: Execution configuration
            tenant_id: Tenant ID
            args: Optional command-line arguments
            
        Returns:
            ExecutionResult
        """
        result = ExecutionResult()
        result.started_at = datetime.utcnow()
        
        container: Optional[SandboxContainer] = None
        
        try:
            # Determine runtime
            runtime = config.runtime or LANGUAGE_RUNTIMES.get(config.language)
            if not runtime:
                result.status = ExecutionStatus.ERROR
                result.error_message = f"Unsupported language: {config.language}"
                return result
            
            # Create container
            container_config = ContainerConfig(
                runtime=runtime,
                memory_mb=config.memory_mb,
                timeout_seconds=config.timeout_seconds,
                network_enabled=config.network_enabled,
                environment=config.environment,
            )
            
            container = await self.container_manager.create(
                container_config,
                tenant_id=tenant_id,
            )
            
            # Write file
            filepath = f"/workspace/{filename}"
            await self.container_manager.write_file(container.id, filepath, content)
            
            # Install packages
            if config.packages:
                await self._install_packages(container, config.language, config.packages)
            
            result.status = ExecutionStatus.RUNNING
            
            # Build command
            command = self._build_run_command(config.language, filepath, args)
            
            # Execute
            exit_code, stdout, stderr = await self.container_manager.execute(
                container.id,
                command,
                timeout=config.timeout_seconds,
            )
            
            result.exit_code = exit_code
            result.stdout = stdout
            result.stderr = stderr
            
            # Retrieve artifacts
            if config.capture_files:
                result.artifacts = await self.container_manager.get_artifacts(
                    container.id,
                    config.capture_files,
                )
            
            # Set status
            if exit_code == 0:
                result.status = ExecutionStatus.SUCCESS
            elif exit_code == -1:
                result.status = ExecutionStatus.TIMEOUT
            else:
                result.status = ExecutionStatus.FAILURE
            
        except Exception as e:
            logger.exception(f"File execution error: {e}")
            result.status = ExecutionStatus.ERROR
            result.error_message = str(e)
            
        finally:
            result.completed_at = datetime.utcnow()
            if result.started_at:
                result.duration_ms = int(
                    (result.completed_at - result.started_at).total_seconds() * 1000
                )
            
            if container:
                await self.container_manager.destroy(container.id)
            
            self._executions[result.execution_id] = result
        
        return result
    
    async def execute_tests(
        self,
        test_files: Dict[str, str],
        config: ExecutionConfig,
        tenant_id: str,
        test_command: Optional[List[str]] = None,
    ) -> ExecutionResult:
        """
        Execute test files in a sandbox.
        
        Args:
            test_files: Dict mapping filename to content
            config: Execution configuration
            tenant_id: Tenant ID
            test_command: Optional custom test command
            
        Returns:
            ExecutionResult
        """
        result = ExecutionResult()
        result.started_at = datetime.utcnow()
        
        container: Optional[SandboxContainer] = None
        
        try:
            runtime = config.runtime or LANGUAGE_RUNTIMES.get(config.language)
            
            container_config = ContainerConfig(
                runtime=runtime,
                memory_mb=config.memory_mb,
                timeout_seconds=config.timeout_seconds,
                network_enabled=config.network_enabled,
            )
            
            container = await self.container_manager.create(
                container_config,
                tenant_id=tenant_id,
            )
            
            # Write all test files
            for filename, content in test_files.items():
                filepath = f"/workspace/{filename}"
                await self.container_manager.write_file(container.id, filepath, content)
            
            # Install test frameworks + dependencies
            packages = config.packages.copy()
            if config.language == "python" and "pytest" not in packages:
                packages.append("pytest")
            
            if packages:
                await self._install_packages(container, config.language, packages)
            
            result.status = ExecutionStatus.RUNNING
            
            # Build test command
            if test_command:
                command = test_command
            else:
                command = self._build_test_command(config.language)
            
            # Execute tests
            exit_code, stdout, stderr = await self.container_manager.execute(
                container.id,
                command,
                timeout=config.timeout_seconds,
            )
            
            result.exit_code = exit_code
            result.stdout = stdout
            result.stderr = stderr
            
            if exit_code == 0:
                result.status = ExecutionStatus.SUCCESS
            elif exit_code == -1:
                result.status = ExecutionStatus.TIMEOUT
            else:
                result.status = ExecutionStatus.FAILURE
            
        except Exception as e:
            logger.exception(f"Test execution error: {e}")
            result.status = ExecutionStatus.ERROR
            result.error_message = str(e)
            
        finally:
            result.completed_at = datetime.utcnow()
            if result.started_at:
                result.duration_ms = int(
                    (result.completed_at - result.started_at).total_seconds() * 1000
                )
            
            if container:
                await self.container_manager.destroy(container.id)
            
            self._executions[result.execution_id] = result
        
        return result
    
    async def _install_packages(
        self,
        container: SandboxContainer,
        language: str,
        packages: List[str],
    ) -> None:
        """Install packages in the container."""
        if not packages:
            return
        
        if language in ("python", "python3"):
            command = ["pip", "install", "--quiet"] + packages
        elif language in ("javascript", "typescript", "node"):
            command = ["npm", "install", "--silent"] + packages
        elif language == "ruby":
            command = ["gem", "install", "--silent"] + packages
        elif language == "go":
            # Go uses modules, packages installed via go.mod
            return
        elif language == "rust":
            # Rust uses Cargo.toml
            return
        else:
            return
        
        await self.container_manager.execute(
            container.id,
            command,
            timeout=60,
        )
    
    async def _execute_file_based(
        self,
        container: SandboxContainer,
        code: str,
        language: str,
    ) -> tuple[int, str, str]:
        """Execute code that requires file-based execution."""
        # Determine filename
        extensions = {
            "go": "main.go",
            "rust": "main.rs",
            "java": "Main.java",
        }
        filename = extensions.get(language, "main.txt")
        filepath = f"/workspace/{filename}"
        
        # Write code
        await self.container_manager.write_file(container.id, filepath, code)
        
        # Execute
        command = self._build_run_command(language, filepath)
        return await self.container_manager.execute(
            container.id,
            command,
            timeout=container.config.timeout_seconds,
        )
    
    def _build_run_command(
        self,
        language: str,
        filepath: str,
        args: Optional[List[str]] = None,
    ) -> List[str]:
        """Build command to run a file."""
        commands = {
            "python": ["python", filepath],
            "python3": ["python3", filepath],
            "javascript": ["node", filepath],
            "typescript": ["npx", "ts-node", filepath],
            "node": ["node", filepath],
            "go": ["go", "run", filepath],
            "rust": ["sh", "-c", f"rustc {filepath} -o /tmp/out && /tmp/out"],
            "java": ["sh", "-c", f"javac {filepath} && java -cp /workspace Main"],
            "ruby": ["ruby", filepath],
        }
        
        command = commands.get(language, ["python", filepath])
        if args:
            command.extend(args)
        
        return command
    
    def _build_test_command(self, language: str) -> List[str]:
        """Build command to run tests."""
        commands = {
            "python": ["python", "-m", "pytest", "-v", "/workspace"],
            "javascript": ["npm", "test"],
            "typescript": ["npm", "test"],
            "go": ["go", "test", "./..."],
            "rust": ["cargo", "test"],
            "java": ["mvn", "test"],
            "ruby": ["ruby", "-Itest", "-e", "Dir.glob('test/**/*_test.rb').each{|f| require f}"],
        }
        return commands.get(language, ["echo", "No test runner configured"])
    
    def get_execution(self, execution_id: str) -> Optional[ExecutionResult]:
        """Get an execution result by ID."""
        return self._executions.get(execution_id)
