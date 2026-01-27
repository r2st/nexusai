"""
Tool Permissions

RBAC-based permission checking for tool execution.
"""

from enum import Enum
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
import logging

from .base import Tool, ToolMetadata, ExecutionContext

logger = logging.getLogger(__name__)


class PermissionLevel(str, Enum):
    """Permission levels for tools."""
    PUBLIC = "public"  # Anyone can use
    USER = "user"  # Authenticated users
    MEMBER = "member"  # Organization members
    ADMIN = "admin"  # Admins only
    SUPERUSER = "superuser"  # Superusers only


@dataclass
class RolePermissions:
    """Permissions associated with a role."""
    role: str
    level: PermissionLevel
    permissions: Set[str] = field(default_factory=set)
    allowed_tools: Optional[Set[str]] = None  # None = all allowed at level
    denied_tools: Set[str] = field(default_factory=set)


# Default role hierarchy
DEFAULT_ROLE_HIERARCHY: Dict[str, PermissionLevel] = {
    "viewer": PermissionLevel.USER,
    "user": PermissionLevel.USER,
    "member": PermissionLevel.MEMBER,
    "admin": PermissionLevel.ADMIN,
    "superuser": PermissionLevel.SUPERUSER,
}

# Default permissions per role
DEFAULT_ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    "viewer": {
        "tools.read",
        "tools.search",
    },
    "user": {
        "tools.read",
        "tools.search",
        "tools.execute.basic",
    },
    "member": {
        "tools.read",
        "tools.search",
        "tools.execute.basic",
        "tools.execute.integration",
    },
    "admin": {
        "tools.read",
        "tools.search",
        "tools.execute.basic",
        "tools.execute.integration",
        "tools.execute.admin",
        "tools.manage",
    },
    "superuser": {
        "tools.*",  # All permissions
    },
}


class ToolPermissions:
    """
    Manages tool permissions and access control.
    
    Features:
    - Role-based access control
    - Per-tool permission requirements
    - Tenant-level overrides
    - Permission caching
    """
    
    def __init__(
        self,
        role_hierarchy: Optional[Dict[str, PermissionLevel]] = None,
        role_permissions: Optional[Dict[str, Set[str]]] = None,
    ):
        self.role_hierarchy = role_hierarchy or DEFAULT_ROLE_HIERARCHY
        self.role_permissions = role_permissions or DEFAULT_ROLE_PERMISSIONS
        
        # Tenant-specific overrides
        self._tenant_overrides: Dict[str, Dict[str, RolePermissions]] = {}
        
        # Tool-specific restrictions
        self._tool_restrictions: Dict[str, Set[str]] = {}  # tool -> required permissions
    
    def get_level_for_role(self, role: str) -> PermissionLevel:
        """Get the permission level for a role."""
        return self.role_hierarchy.get(role, PermissionLevel.USER)
    
    def get_permissions_for_role(self, role: str) -> Set[str]:
        """Get all permissions for a role."""
        return self.role_permissions.get(role, set()).copy()
    
    def check_permission(
        self,
        context: ExecutionContext,
        tool: Tool,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if the user can execute the tool.
        
        Returns:
            Tuple of (allowed, reason_if_denied)
        """
        metadata = tool.get_metadata()
        
        # Get user's effective permissions
        user_permissions = self._get_effective_permissions(context)
        user_level = self.get_level_for_role(context.user_role)
        
        # Check minimum role level
        min_role = metadata.min_role
        min_level = self.get_level_for_role(min_role)
        
        level_order = [
            PermissionLevel.PUBLIC,
            PermissionLevel.USER,
            PermissionLevel.MEMBER,
            PermissionLevel.ADMIN,
            PermissionLevel.SUPERUSER,
        ]
        
        if level_order.index(user_level) < level_order.index(min_level):
            return False, f"Requires minimum role: {min_role}"
        
        # Check required permissions
        required_permissions = set(metadata.required_permissions)
        
        # Add any tool-specific restrictions
        if metadata.name in self._tool_restrictions:
            required_permissions.update(self._tool_restrictions[metadata.name])
        
        if required_permissions:
            # Check for wildcard permission
            if "tools.*" in user_permissions:
                return True, None
            
            missing = required_permissions - user_permissions
            if missing:
                return False, f"Missing permissions: {', '.join(missing)}"
        
        # Check tenant-level overrides
        tenant_override = self._check_tenant_override(context, metadata.name)
        if tenant_override is not None:
            return tenant_override
        
        return True, None
    
    def _get_effective_permissions(self, context: ExecutionContext) -> Set[str]:
        """Get effective permissions considering role and explicit grants."""
        # Start with role-based permissions
        permissions = self.get_permissions_for_role(context.user_role)
        
        # Add any explicitly granted permissions
        permissions.update(context.user_permissions)
        
        # Check for tenant-specific role overrides
        if context.tenant_id in self._tenant_overrides:
            tenant_roles = self._tenant_overrides[context.tenant_id]
            if context.user_role in tenant_roles:
                permissions.update(tenant_roles[context.user_role].permissions)
        
        return permissions
    
    def _check_tenant_override(
        self,
        context: ExecutionContext,
        tool_name: str,
    ) -> Optional[tuple[bool, Optional[str]]]:
        """Check tenant-specific tool overrides."""
        if context.tenant_id not in self._tenant_overrides:
            return None
        
        tenant_roles = self._tenant_overrides[context.tenant_id]
        if context.user_role not in tenant_roles:
            return None
        
        role_config = tenant_roles[context.user_role]
        
        # Check explicit denials
        if tool_name in role_config.denied_tools:
            return False, f"Tool '{tool_name}' is disabled for your role in this tenant"
        
        # Check explicit allowlist
        if role_config.allowed_tools is not None:
            if tool_name not in role_config.allowed_tools:
                return False, f"Tool '{tool_name}' is not enabled for your role"
        
        return None
    
    def set_tenant_role_config(
        self,
        tenant_id: str,
        role: str,
        config: RolePermissions,
    ) -> None:
        """Set tenant-specific role configuration."""
        if tenant_id not in self._tenant_overrides:
            self._tenant_overrides[tenant_id] = {}
        self._tenant_overrides[tenant_id][role] = config
    
    def add_tool_restriction(self, tool_name: str, permission: str) -> None:
        """Add a permission requirement to a tool."""
        if tool_name not in self._tool_restrictions:
            self._tool_restrictions[tool_name] = set()
        self._tool_restrictions[tool_name].add(permission)
    
    def remove_tool_restriction(self, tool_name: str, permission: str) -> None:
        """Remove a permission requirement from a tool."""
        if tool_name in self._tool_restrictions:
            self._tool_restrictions[tool_name].discard(permission)
    
    def get_allowed_tools(
        self,
        context: ExecutionContext,
        tool_names: List[str],
    ) -> List[str]:
        """Filter tool names to only those the user can access."""
        from .registry import tool_registry
        
        allowed = []
        for name in tool_names:
            registered = tool_registry.get(name)
            if not registered:
                continue
            
            tool = registered.tool_class()
            allowed_result, _ = self.check_permission(context, tool)
            if allowed_result:
                allowed.append(name)
        
        return allowed


# Global permissions instance
tool_permissions = ToolPermissions()
