"""
Container Manager

Manages ephemeral sandbox containers for code execution.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
import asyncio
import logging
import os
import uuid

logger = logging.getLogger(__name__)


class ContainerStatus(str, Enum):
    """Container lifecycle status."""
    CREATING = "creating"
    READY = "ready"
    RUNNING = "running"
    STOPPED = "stopped"
    DESTROYED = "destroyed"
    ERROR = "error"


class RuntimeEnvironment(str, Enum):
    """Supported runtime environments."""
    PYTHON_3_11 = "python:3.11-slim"
    PYTHON_3_12 = "python:3.12-slim"
    NODE_20 = "node:20-slim"
    NODE_22 = "node:22-slim"
    GO_1_21 = "golang:1.21-alpine"
    RUST_1_75 = "rust:1.75-slim"
    JAVA_21 = "eclipse-temurin:21-jdk"
    RUBY_3_3 = "ruby:3.3-slim"
    MULTI = "ubuntu:22.04"  # Multi-language


@dataclass
class ContainerConfig:
    """Configuration for sandbox containers."""
    # Runtime
    runtime: RuntimeEnvironment = RuntimeEnvironment.PYTHON_3_11
    working_dir: str = "/workspace"
    
    # Resource limits
    memory_mb: int = 512
    cpu_shares: int = 1024  # Relative CPU weight
    cpu_period: int = 100000  # CPU period in microseconds
    cpu_quota: int = 50000  # CPU quota (50% of one core)
    
    # Time limits
    timeout_seconds: int = 30
    max_lifetime_seconds: int = 300
    
    # Network
    network_enabled: bool = False
    allowed_hosts: List[str] = field(default_factory=list)
    
    # Storage
    temp_storage_mb: int = 100
    read_only_root: bool = True
    
    # Security
    drop_capabilities: List[str] = field(default_factory=lambda: [
        "ALL",  # Drop all capabilities
    ])
    add_capabilities: List[str] = field(default_factory=list)
    seccomp_profile: str = "default"
    
    # Environment
    environment: Dict[str, str] = field(default_factory=dict)


@dataclass
class SandboxContainer:
    """A sandbox container instance."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    config: ContainerConfig = field(default_factory=ContainerConfig)
    status: ContainerStatus = ContainerStatus.CREATING
    
    # Docker/container info
    container_id: Optional[str] = None
    image: str = ""
    
    # Lifecycle
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    
    # Resource usage
    peak_memory_mb: float = 0
    cpu_time_ms: int = 0
    
    # Tenant info
    tenant_id: str = ""
    request_id: str = ""
    
    @property
    def is_active(self) -> bool:
        return self.status in (ContainerStatus.READY, ContainerStatus.RUNNING)
    
    @property
    def age_seconds(self) -> float:
        return (datetime.utcnow() - self.created_at).total_seconds()


class ContainerManager:
    """
    Manages sandbox container lifecycle.
    
    Features:
    - Create isolated containers
    - Resource enforcement
    - Automatic cleanup
    - Pool management
    """
    
    def __init__(
        self,
        docker_client: Optional[Any] = None,
        max_containers_per_tenant: int = 10,
        cleanup_interval_seconds: int = 60,
    ):
        self.docker_client = docker_client
        self.max_containers_per_tenant = max_containers_per_tenant
        self.cleanup_interval = cleanup_interval_seconds
        
        # Active containers
        self._containers: Dict[str, SandboxContainer] = {}
        self._tenant_containers: Dict[str, List[str]] = {}
        
        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start the container manager."""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Container manager started")
    
    async def stop(self) -> None:
        """Stop the container manager and cleanup all containers."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Destroy all active containers
        for container_id in list(self._containers.keys()):
            await self.destroy(container_id)
        
        logger.info("Container manager stopped")
    
    async def create(
        self,
        config: ContainerConfig,
        tenant_id: str,
        request_id: str = "",
    ) -> SandboxContainer:
        """
        Create a new sandbox container.
        
        Args:
            config: Container configuration
            tenant_id: Tenant ID
            request_id: Optional request ID for tracking
            
        Returns:
            SandboxContainer instance
        """
        # Check tenant limits
        tenant_containers = self._tenant_containers.get(tenant_id, [])
        active_count = sum(
            1 for cid in tenant_containers
            if cid in self._containers and self._containers[cid].is_active
        )
        
        if active_count >= self.max_containers_per_tenant:
            raise RuntimeError(
                f"Tenant {tenant_id} has reached max container limit ({self.max_containers_per_tenant})"
            )
        
        # Create container
        container = SandboxContainer(
            config=config,
            image=config.runtime.value,
            tenant_id=tenant_id,
            request_id=request_id,
        )
        
        try:
            # Create actual container
            await self._create_container(container)
            container.status = ContainerStatus.READY
            
            # Track
            self._containers[container.id] = container
            if tenant_id not in self._tenant_containers:
                self._tenant_containers[tenant_id] = []
            self._tenant_containers[tenant_id].append(container.id)
            
            logger.info(f"Created sandbox container {container.id} for tenant {tenant_id}")
            return container
            
        except Exception as e:
            container.status = ContainerStatus.ERROR
            logger.error(f"Failed to create container: {e}")
            raise
    
    async def execute(
        self,
        container_id: str,
        command: List[str],
        stdin: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> tuple[int, str, str]:
        """
        Execute a command in a container.
        
        Args:
            container_id: Container ID
            command: Command and arguments
            stdin: Optional stdin data
            timeout: Optional timeout override
            
        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        container = self._containers.get(container_id)
        if not container:
            raise ValueError(f"Container not found: {container_id}")
        
        if not container.is_active:
            raise RuntimeError(f"Container not active: {container.status}")
        
        container.status = ContainerStatus.RUNNING
        container.started_at = datetime.utcnow()
        
        effective_timeout = timeout or container.config.timeout_seconds
        
        try:
            exit_code, stdout, stderr = await asyncio.wait_for(
                self._execute_in_container(container, command, stdin),
                timeout=effective_timeout,
            )
            
            return exit_code, stdout, stderr
            
        except asyncio.TimeoutError:
            logger.warning(f"Container {container_id} execution timed out")
            await self._kill_processes(container)
            return -1, "", "Execution timed out"
            
        finally:
            container.status = ContainerStatus.READY
    
    async def write_file(
        self,
        container_id: str,
        path: str,
        content: str,
    ) -> None:
        """Write a file to the container's workspace."""
        container = self._containers.get(container_id)
        if not container:
            raise ValueError(f"Container not found: {container_id}")
        
        await self._write_file_to_container(container, path, content)
    
    async def read_file(
        self,
        container_id: str,
        path: str,
    ) -> str:
        """Read a file from the container's workspace."""
        container = self._containers.get(container_id)
        if not container:
            raise ValueError(f"Container not found: {container_id}")
        
        return await self._read_file_from_container(container, path)
    
    async def get_artifacts(
        self,
        container_id: str,
        paths: List[str],
    ) -> Dict[str, bytes]:
        """
        Retrieve artifacts (files) from the container.
        
        Args:
            container_id: Container ID
            paths: List of file paths to retrieve
            
        Returns:
            Dict mapping path to file contents
        """
        container = self._containers.get(container_id)
        if not container:
            raise ValueError(f"Container not found: {container_id}")
        
        artifacts = {}
        for path in paths:
            try:
                content = await self._read_file_from_container(container, path)
                artifacts[path] = content.encode()
            except Exception as e:
                logger.warning(f"Failed to read artifact {path}: {e}")
        
        return artifacts
    
    async def destroy(self, container_id: str) -> None:
        """Destroy a container."""
        container = self._containers.get(container_id)
        if not container:
            return
        
        try:
            await self._destroy_container(container)
            container.status = ContainerStatus.DESTROYED
            container.stopped_at = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Error destroying container {container_id}: {e}")
            container.status = ContainerStatus.ERROR
            
        finally:
            # Remove from tracking
            del self._containers[container_id]
            if container.tenant_id in self._tenant_containers:
                self._tenant_containers[container.tenant_id].remove(container_id)
        
        logger.info(f"Destroyed container {container_id}")
    
    async def _cleanup_loop(self) -> None:
        """Periodically cleanup expired containers."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
    
    async def _cleanup_expired(self) -> None:
        """Cleanup containers that have exceeded their lifetime."""
        now = datetime.utcnow()
        expired = []
        
        for container_id, container in self._containers.items():
            if container.age_seconds > container.config.max_lifetime_seconds:
                expired.append(container_id)
        
        for container_id in expired:
            logger.info(f"Cleaning up expired container {container_id}")
            await self.destroy(container_id)
    
    # Docker implementation methods (would use docker-py or similar)
    
    async def _create_container(self, container: SandboxContainer) -> None:
        """Create the actual Docker container."""
        if not self.docker_client:
            # Mock implementation for testing
            container.container_id = f"mock-{container.id}"
            return
        
        # Real implementation would use docker-py:
        # container.container_id = self.docker_client.containers.create(
        #     image=container.image,
        #     working_dir=container.config.working_dir,
        #     mem_limit=f"{container.config.memory_mb}m",
        #     cpu_period=container.config.cpu_period,
        #     cpu_quota=container.config.cpu_quota,
        #     network_disabled=not container.config.network_enabled,
        #     read_only=container.config.read_only_root,
        #     cap_drop=container.config.drop_capabilities,
        #     cap_add=container.config.add_capabilities,
        #     environment=container.config.environment,
        #     tmpfs={"/tmp": f"size={container.config.temp_storage_mb}m"},
        # ).id
        pass
    
    async def _execute_in_container(
        self,
        container: SandboxContainer,
        command: List[str],
        stdin: Optional[str],
    ) -> tuple[int, str, str]:
        """Execute command in container."""
        if not self.docker_client:
            # Mock implementation
            return 0, f"Mock output for: {' '.join(command)}", ""
        
        # Real implementation would use docker exec
        pass
        return 0, "", ""
    
    async def _write_file_to_container(
        self,
        container: SandboxContainer,
        path: str,
        content: str,
    ) -> None:
        """Write file to container."""
        pass
    
    async def _read_file_from_container(
        self,
        container: SandboxContainer,
        path: str,
    ) -> str:
        """Read file from container."""
        return ""
    
    async def _kill_processes(self, container: SandboxContainer) -> None:
        """Kill all processes in container."""
        pass
    
    async def _destroy_container(self, container: SandboxContainer) -> None:
        """Destroy the Docker container."""
        if not self.docker_client:
            return
        
        # Real implementation would use docker-py:
        # docker_container = self.docker_client.containers.get(container.container_id)
        # docker_container.remove(force=True)
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get container manager statistics."""
        active = sum(1 for c in self._containers.values() if c.is_active)
        
        return {
            "total_containers": len(self._containers),
            "active_containers": active,
            "tenants": len(self._tenant_containers),
            "containers_by_status": {
                status.value: sum(1 for c in self._containers.values() if c.status == status)
                for status in ContainerStatus
            },
        }
