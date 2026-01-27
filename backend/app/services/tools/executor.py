"""
Tool Executor

Safe tool execution with timeouts, rate limiting, and audit logging.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass
import logging
import time

from redis.asyncio import Redis

from .base import (
    Tool,
    ToolResult,
    ToolResultStatus,
    ExecutionContext,
)
from .registry import ToolRegistry, tool_registry
from .permissions import ToolPermissions, tool_permissions
from .audit import ToolAuditLogger, AuditEntry

logger = logging.getLogger(__name__)


@dataclass
class ExecutionConfig:
    """Configuration for tool execution."""
    default_timeout: int = 30  # seconds
    max_timeout: int = 300  # seconds
    enable_rate_limiting: bool = True
    enable_audit_logging: bool = True
    enable_permission_check: bool = True
    max_concurrent_per_user: int = 10
    max_retries: int = 3
    retry_delay: float = 1.0  # seconds


class RateLimiter:
    """Token bucket rate limiter using Redis."""
    
    def __init__(self, redis: Redis):
        self.redis = redis
    
    async def check_and_consume(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        """
        Check rate limit and consume a token if allowed.
        
        Returns:
            Tuple of (allowed, remaining_tokens)
        """
        now = time.time()
        window_start = now - window_seconds
        
        pipe = self.redis.pipeline()
        
        # Remove old entries
        pipe.zremrangebyscore(key, 0, window_start)
        
        # Count current entries
        pipe.zcard(key)
        
        # Add new entry
        pipe.zadd(key, {str(now): now})
        
        # Set expiry
        pipe.expire(key, window_seconds)
        
        results = await pipe.execute()
        current_count = results[1]
        
        if current_count >= limit:
            return False, 0
        
        return True, limit - current_count - 1
    
    async def get_remaining(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> int:
        """Get remaining tokens without consuming."""
        now = time.time()
        window_start = now - window_seconds
        
        await self.redis.zremrangebyscore(key, 0, window_start)
        current_count = await self.redis.zcard(key)
        
        return max(0, limit - current_count)


class ToolExecutor:
    """
    Executes tools with full safety guarantees.
    
    Features:
    - Permission checking
    - Rate limiting
    - Timeout enforcement
    - Audit logging
    - Error handling
    - Retry logic
    """
    
    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        permissions: Optional[ToolPermissions] = None,
        audit_logger: Optional[ToolAuditLogger] = None,
        redis: Optional[Redis] = None,
        config: Optional[ExecutionConfig] = None,
    ):
        self.registry = registry or tool_registry
        self.permissions = permissions or tool_permissions
        self.audit_logger = audit_logger
        self.rate_limiter = RateLimiter(redis) if redis else None
        self.config = config or ExecutionConfig()
        
        # Hooks for extensibility
        self._pre_execute_hooks: List[Callable] = []
        self._post_execute_hooks: List[Callable] = []
    
    async def execute(
        self,
        tool_name: str,
        params: Dict[str, Any],
        context: ExecutionContext,
        timeout: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> ToolResult:
        """
        Execute a tool with all safety checks.
        
        Args:
            tool_name: Name of the tool to execute
            params: Parameters to pass to the tool
            context: Execution context with tenant/user info
            timeout: Optional timeout override
            ip_address: Client IP for audit
            user_agent: Client user agent for audit
            
        Returns:
            ToolResult with execution outcome
        """
        start_time = datetime.utcnow()
        audit_entry: Optional[AuditEntry] = None
        
        try:
            # 1. Get tool from registry
            registered = self.registry.get(tool_name)
            if not registered:
                return ToolResult.error(
                    tool_name=tool_name,
                    error=f"Tool '{tool_name}' not found",
                    error_code="TOOL_NOT_FOUND",
                )
            
            if not registered.is_enabled:
                return ToolResult.error(
                    tool_name=tool_name,
                    error=f"Tool '{tool_name}' is disabled",
                    error_code="TOOL_DISABLED",
                )
            
            tool = registered.tool_class()
            metadata = registered.metadata
            
            # 2. Check permissions
            if self.config.enable_permission_check:
                allowed, reason = self.permissions.check_permission(context, tool)
                if not allowed:
                    if self.audit_logger:
                        await self.audit_logger.log_permission_denied(
                            tool_name=tool_name,
                            context=context,
                            reason=reason or "Permission denied",
                        )
                    return ToolResult(
                        tool_name=tool_name,
                        status=ToolResultStatus.PERMISSION_DENIED,
                        error=reason or "Permission denied",
                        error_code="PERMISSION_DENIED",
                    )
            
            # 3. Check rate limits
            if self.config.enable_rate_limiting and self.rate_limiter:
                rate_ok = await self._check_rate_limits(tool_name, metadata, context)
                if not rate_ok:
                    if self.audit_logger:
                        await self.audit_logger.log_rate_limited(
                            tool_name=tool_name,
                            context=context,
                            limit_type="per_minute",
                        )
                    return ToolResult(
                        tool_name=tool_name,
                        status=ToolResultStatus.RATE_LIMITED,
                        error="Rate limit exceeded",
                        error_code="RATE_LIMITED",
                    )
            
            # 4. Validate parameters
            validation_error = tool.validate_params(params)
            if validation_error:
                return ToolResult(
                    tool_name=tool_name,
                    status=ToolResultStatus.VALIDATION_ERROR,
                    error=validation_error,
                    error_code="VALIDATION_ERROR",
                )
            
            # 5. Check if approval is required
            if metadata.requires_confirmation and not context.dry_run:
                # Log approval request
                if self.audit_logger:
                    audit_entry = await self.audit_logger.log_call(
                        tool_name=tool_name,
                        params=params,
                        context=context,
                        ip_address=ip_address,
                        user_agent=user_agent,
                    )
                    audit_entry.requires_approval = True
                
                return ToolResult(
                    tool_name=tool_name,
                    status=ToolResultStatus.PENDING_APPROVAL,
                    data={"execution_id": audit_entry.execution_id if audit_entry else None},
                    error="Tool requires approval before execution",
                )
            
            # 6. Log the call (if not already logged)
            if self.config.enable_audit_logging and self.audit_logger:
                audit_entry = await self.audit_logger.log_call(
                    tool_name=tool_name,
                    params=params,
                    context=context,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
            
            # 7. Run pre-execute hooks
            for hook in self._pre_execute_hooks:
                await hook(tool_name, params, context)
            
            # 8. Execute with timeout
            effective_timeout = min(
                timeout or metadata.timeout_seconds,
                self.config.max_timeout,
            )
            
            if context.dry_run:
                # Dry run - don't actually execute
                result = ToolResult.success(
                    tool_name=tool_name,
                    data={"dry_run": True, "would_execute": True},
                )
            else:
                result = await self._execute_with_timeout(
                    tool=tool,
                    params=params,
                    context=context,
                    timeout=effective_timeout,
                )
            
            # 9. Calculate duration
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            result.duration_ms = duration_ms
            result.completed_at = end_time
            
            # 10. Run post-execute hooks
            for hook in self._post_execute_hooks:
                await hook(tool_name, params, context, result)
            
            # 11. Log result
            if self.config.enable_audit_logging and self.audit_logger and audit_entry:
                await self.audit_logger.log_result(audit_entry, result)
            
            return result
            
        except asyncio.TimeoutError:
            return ToolResult(
                tool_name=tool_name,
                status=ToolResultStatus.TIMEOUT,
                error="Tool execution timed out",
                error_code="TIMEOUT",
            )
        except Exception as e:
            logger.exception(f"Tool execution failed: {tool_name}")
            result = ToolResult.error(
                tool_name=tool_name,
                error=str(e),
                error_code="EXECUTION_ERROR",
            )
            
            if self.config.enable_audit_logging and self.audit_logger and audit_entry:
                await self.audit_logger.log_result(audit_entry, result)
            
            return result
    
    async def execute_with_retry(
        self,
        tool_name: str,
        params: Dict[str, Any],
        context: ExecutionContext,
        max_retries: Optional[int] = None,
    ) -> ToolResult:
        """Execute a tool with automatic retries on failure."""
        retries = max_retries or self.config.max_retries
        
        for attempt in range(retries + 1):
            result = await self.execute(tool_name, params, context)
            
            # Don't retry on these statuses
            if result.status in [
                ToolResultStatus.SUCCESS,
                ToolResultStatus.PERMISSION_DENIED,
                ToolResultStatus.VALIDATION_ERROR,
                ToolResultStatus.RATE_LIMITED,
                ToolResultStatus.PENDING_APPROVAL,
            ]:
                return result
            
            # Retry on errors and timeouts
            if attempt < retries:
                delay = self.config.retry_delay * (2 ** attempt)  # Exponential backoff
                logger.warning(
                    f"Tool {tool_name} failed (attempt {attempt + 1}/{retries + 1}), "
                    f"retrying in {delay}s"
                )
                await asyncio.sleep(delay)
        
        return result
    
    async def execute_batch(
        self,
        calls: List[Dict[str, Any]],
        context: ExecutionContext,
        parallel: bool = False,
    ) -> List[ToolResult]:
        """
        Execute multiple tool calls.
        
        Args:
            calls: List of {"tool_name": str, "params": dict}
            context: Execution context
            parallel: Whether to execute in parallel
            
        Returns:
            List of results in same order as calls
        """
        if parallel:
            tasks = [
                self.execute(call["tool_name"], call.get("params", {}), context)
                for call in calls
            ]
            return await asyncio.gather(*tasks)
        else:
            results = []
            for call in calls:
                result = await self.execute(
                    call["tool_name"],
                    call.get("params", {}),
                    context,
                )
                results.append(result)
            return results
    
    async def _execute_with_timeout(
        self,
        tool: Tool,
        params: Dict[str, Any],
        context: ExecutionContext,
        timeout: int,
    ) -> ToolResult:
        """Execute tool with timeout."""
        return await asyncio.wait_for(
            tool.execute(params, context),
            timeout=timeout,
        )
    
    async def _check_rate_limits(
        self,
        tool_name: str,
        metadata: Any,
        context: ExecutionContext,
    ) -> bool:
        """Check all applicable rate limits."""
        if not self.rate_limiter:
            return True
        
        # Per-minute limit
        if metadata.rate_limit_per_minute:
            key = f"rate:tool:{tool_name}:user:{context.user_id}:min"
            allowed, _ = await self.rate_limiter.check_and_consume(
                key,
                metadata.rate_limit_per_minute,
                60,
            )
            if not allowed:
                return False
        
        # Per-hour limit
        if metadata.rate_limit_per_hour:
            key = f"rate:tool:{tool_name}:user:{context.user_id}:hour"
            allowed, _ = await self.rate_limiter.check_and_consume(
                key,
                metadata.rate_limit_per_hour,
                3600,
            )
            if not allowed:
                return False
        
        return True
    
    def add_pre_execute_hook(self, hook: Callable) -> None:
        """Add a hook that runs before tool execution."""
        self._pre_execute_hooks.append(hook)
    
    def add_post_execute_hook(self, hook: Callable) -> None:
        """Add a hook that runs after tool execution."""
        self._post_execute_hooks.append(hook)
    
    def remove_pre_execute_hook(self, hook: Callable) -> None:
        """Remove a pre-execute hook."""
        self._pre_execute_hooks.remove(hook)
    
    def remove_post_execute_hook(self, hook: Callable) -> None:
        """Remove a post-execute hook."""
        self._post_execute_hooks.remove(hook)


# Convenience function for executing tools
async def execute_tool(
    tool_name: str,
    params: Dict[str, Any],
    context: ExecutionContext,
    executor: Optional[ToolExecutor] = None,
) -> ToolResult:
    """Execute a tool using the default or provided executor."""
    if executor is None:
        executor = ToolExecutor()
    return await executor.execute(tool_name, params, context)
