"""Permissions Service.

Provides role-based access control (RBAC) for:
- User permissions
- Tool execution permissions
- Agent capabilities
- Resource access control
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger()


class Permission(str, Enum):
    """System permissions."""

    # Organization permissions
    ORG_READ = "org:read"
    ORG_WRITE = "org:write"
    ORG_ADMIN = "org:admin"
    ORG_DELETE = "org:delete"

    # Project permissions
    PROJECT_READ = "project:read"
    PROJECT_WRITE = "project:write"
    PROJECT_ADMIN = "project:admin"
    PROJECT_DELETE = "project:delete"

    # Metrics permissions
    METRICS_READ = "metrics:read"
    METRICS_EXPORT = "metrics:export"

    # Agent permissions
    AGENT_READ = "agent:read"
    AGENT_EXECUTE = "agent:execute"
    AGENT_ADMIN = "agent:admin"

    # Tool permissions
    TOOL_READ = "tool:read"
    TOOL_EXECUTE = "tool:execute"
    TOOL_ADMIN = "tool:admin"

    # DevLake permissions
    DEVLAKE_READ = "devlake:read"
    DEVLAKE_CONFIGURE = "devlake:configure"

    # Document permissions
    DOCUMENT_READ = "document:read"
    DOCUMENT_WRITE = "document:write"
    DOCUMENT_DELETE = "document:delete"

    # Settings permissions
    SETTINGS_READ = "settings:read"
    SETTINGS_WRITE = "settings:write"

    # API Key permissions
    API_KEY_CREATE = "api_key:create"
    API_KEY_REVOKE = "api_key:revoke"

    # Audit permissions
    AUDIT_READ = "audit:read"


class Role(str, Enum):
    """Predefined roles with permission sets."""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"
    GUEST = "guest"


# Role permission mappings
ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.OWNER: {
        Permission.ORG_READ,
        Permission.ORG_WRITE,
        Permission.ORG_ADMIN,
        Permission.ORG_DELETE,
        Permission.PROJECT_READ,
        Permission.PROJECT_WRITE,
        Permission.PROJECT_ADMIN,
        Permission.PROJECT_DELETE,
        Permission.METRICS_READ,
        Permission.METRICS_EXPORT,
        Permission.AGENT_READ,
        Permission.AGENT_EXECUTE,
        Permission.AGENT_ADMIN,
        Permission.TOOL_READ,
        Permission.TOOL_EXECUTE,
        Permission.TOOL_ADMIN,
        Permission.DEVLAKE_READ,
        Permission.DEVLAKE_CONFIGURE,
        Permission.DOCUMENT_READ,
        Permission.DOCUMENT_WRITE,
        Permission.DOCUMENT_DELETE,
        Permission.SETTINGS_READ,
        Permission.SETTINGS_WRITE,
        Permission.API_KEY_CREATE,
        Permission.API_KEY_REVOKE,
        Permission.AUDIT_READ,
    },
    Role.ADMIN: {
        Permission.ORG_READ,
        Permission.ORG_WRITE,
        Permission.ORG_ADMIN,
        Permission.PROJECT_READ,
        Permission.PROJECT_WRITE,
        Permission.PROJECT_ADMIN,
        Permission.METRICS_READ,
        Permission.METRICS_EXPORT,
        Permission.AGENT_READ,
        Permission.AGENT_EXECUTE,
        Permission.AGENT_ADMIN,
        Permission.TOOL_READ,
        Permission.TOOL_EXECUTE,
        Permission.TOOL_ADMIN,
        Permission.DEVLAKE_READ,
        Permission.DEVLAKE_CONFIGURE,
        Permission.DOCUMENT_READ,
        Permission.DOCUMENT_WRITE,
        Permission.DOCUMENT_DELETE,
        Permission.SETTINGS_READ,
        Permission.SETTINGS_WRITE,
        Permission.API_KEY_CREATE,
        Permission.AUDIT_READ,
    },
    Role.MEMBER: {
        Permission.ORG_READ,
        Permission.PROJECT_READ,
        Permission.PROJECT_WRITE,
        Permission.METRICS_READ,
        Permission.AGENT_READ,
        Permission.AGENT_EXECUTE,
        Permission.TOOL_READ,
        Permission.TOOL_EXECUTE,
        Permission.DEVLAKE_READ,
        Permission.DOCUMENT_READ,
        Permission.DOCUMENT_WRITE,
        Permission.SETTINGS_READ,
    },
    Role.VIEWER: {
        Permission.ORG_READ,
        Permission.PROJECT_READ,
        Permission.METRICS_READ,
        Permission.AGENT_READ,
        Permission.TOOL_READ,
        Permission.DEVLAKE_READ,
        Permission.DOCUMENT_READ,
        Permission.SETTINGS_READ,
    },
    Role.GUEST: {
        Permission.ORG_READ,
        Permission.PROJECT_READ,
        Permission.METRICS_READ,
    },
}


@dataclass
class ToolPermission:
    """Permission configuration for a tool."""

    tool_name: str
    allowed_roles: set[Role] = field(default_factory=lambda: {Role.OWNER, Role.ADMIN})
    requires_confirmation: bool = False
    max_executions_per_hour: int = 100
    allowed_parameters: set[str] | None = None  # None = all allowed
    blocked_parameters: set[str] = field(default_factory=set)

    def is_allowed(self, role: Role) -> bool:
        """Check if role is allowed to use this tool."""
        return role in self.allowed_roles

    def is_parameter_allowed(self, param: str) -> bool:
        """Check if a parameter is allowed."""
        if param in self.blocked_parameters:
            return False
        if self.allowed_parameters is not None:
            return param in self.allowed_parameters
        return True


# Default tool permissions
DEFAULT_TOOL_PERMISSIONS: dict[str, ToolPermission] = {
    # Safe tools - all members can use
    "get_metrics": ToolPermission(
        tool_name="get_metrics",
        allowed_roles={Role.OWNER, Role.ADMIN, Role.MEMBER, Role.VIEWER},
    ),
    "search_documents": ToolPermission(
        tool_name="search_documents",
        allowed_roles={Role.OWNER, Role.ADMIN, Role.MEMBER, Role.VIEWER},
    ),
    "analyze_code": ToolPermission(
        tool_name="analyze_code",
        allowed_roles={Role.OWNER, Role.ADMIN, Role.MEMBER},
    ),

    # Moderate risk - members and above
    "create_blueprint": ToolPermission(
        tool_name="create_blueprint",
        allowed_roles={Role.OWNER, Role.ADMIN, Role.MEMBER},
        requires_confirmation=True,
    ),
    "run_pipeline": ToolPermission(
        tool_name="run_pipeline",
        allowed_roles={Role.OWNER, Role.ADMIN, Role.MEMBER},
        requires_confirmation=True,
        max_executions_per_hour=10,
    ),
    "create_issue": ToolPermission(
        tool_name="create_issue",
        allowed_roles={Role.OWNER, Role.ADMIN, Role.MEMBER},
    ),

    # High risk - admin only
    "delete_connection": ToolPermission(
        tool_name="delete_connection",
        allowed_roles={Role.OWNER, Role.ADMIN},
        requires_confirmation=True,
    ),
    "configure_devlake": ToolPermission(
        tool_name="configure_devlake",
        allowed_roles={Role.OWNER, Role.ADMIN},
        requires_confirmation=True,
    ),
    "manage_api_keys": ToolPermission(
        tool_name="manage_api_keys",
        allowed_roles={Role.OWNER, Role.ADMIN},
        requires_confirmation=True,
    ),

    # Owner only
    "delete_organization": ToolPermission(
        tool_name="delete_organization",
        allowed_roles={Role.OWNER},
        requires_confirmation=True,
        max_executions_per_hour=1,
    ),
    "transfer_ownership": ToolPermission(
        tool_name="transfer_ownership",
        allowed_roles={Role.OWNER},
        requires_confirmation=True,
    ),
}


@dataclass
class UserPermissions:
    """User's effective permissions."""

    user_id: str
    tenant_id: str
    role: Role
    permissions: set[Permission]
    custom_permissions: set[Permission] = field(default_factory=set)
    denied_permissions: set[Permission] = field(default_factory=set)
    tool_overrides: dict[str, ToolPermission] = field(default_factory=dict)

    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a specific permission."""
        if permission in self.denied_permissions:
            return False
        return (
            permission in self.permissions
            or permission in self.custom_permissions
        )

    def can_use_tool(self, tool_name: str) -> bool:
        """Check if user can use a specific tool."""
        # Check for tool-specific override
        if tool_name in self.tool_overrides:
            return self.tool_overrides[tool_name].is_allowed(self.role)

        # Check default permissions
        if tool_name in DEFAULT_TOOL_PERMISSIONS:
            return DEFAULT_TOOL_PERMISSIONS[tool_name].is_allowed(self.role)

        # Default: members can use unknown tools
        return self.role in {Role.OWNER, Role.ADMIN, Role.MEMBER}


class PermissionsService:
    """
    Service for managing user and tool permissions.

    Provides:
    - Role-based permission checking
    - Tool execution authorization
    - Permission caching
    - Custom permission overrides
    """

    def __init__(self):
        self._permission_cache: dict[str, UserPermissions] = {}
        self._tool_permissions = DEFAULT_TOOL_PERMISSIONS.copy()

    def get_role_permissions(self, role: Role) -> set[Permission]:
        """Get all permissions for a role."""
        return ROLE_PERMISSIONS.get(role, set())

    def create_user_permissions(
        self,
        user_id: str,
        tenant_id: str,
        role: Role,
        custom_permissions: set[Permission] | None = None,
        denied_permissions: set[Permission] | None = None,
    ) -> UserPermissions:
        """Create a UserPermissions object for a user."""
        permissions = self.get_role_permissions(role)

        return UserPermissions(
            user_id=user_id,
            tenant_id=tenant_id,
            role=role,
            permissions=permissions,
            custom_permissions=custom_permissions or set(),
            denied_permissions=denied_permissions or set(),
        )

    def check_permission(
        self,
        user_permissions: UserPermissions,
        required_permission: Permission,
    ) -> bool:
        """
        Check if user has a required permission.

        Args:
            user_permissions: User's permission set
            required_permission: Permission to check

        Returns:
            True if permission is granted

        Raises:
            PermissionError if permission is denied
        """
        if user_permissions.has_permission(required_permission):
            return True

        logger.warning(
            "Permission denied",
            user_id=user_permissions.user_id,
            required=required_permission.value,
            role=user_permissions.role.value,
        )
        raise PermissionError(
            f"Permission denied: {required_permission.value} required"
        )

    def check_tool_permission(
        self,
        user_permissions: UserPermissions,
        tool_name: str,
        parameters: dict[str, Any] | None = None,
    ) -> tuple[bool, bool]:
        """
        Check if user can execute a tool.

        Args:
            user_permissions: User's permission set
            tool_name: Name of the tool
            parameters: Tool parameters to validate

        Returns:
            Tuple of (allowed, requires_confirmation)

        Raises:
            PermissionError if tool execution is denied
        """
        # Get tool permission config
        tool_perm = self._tool_permissions.get(tool_name)

        if tool_perm is None:
            # Unknown tool - use default behavior
            if not user_permissions.can_use_tool(tool_name):
                raise PermissionError(f"Not authorized to use tool: {tool_name}")
            return True, False

        # Check role
        if not tool_perm.is_allowed(user_permissions.role):
            logger.warning(
                "Tool permission denied",
                user_id=user_permissions.user_id,
                tool=tool_name,
                role=user_permissions.role.value,
            )
            raise PermissionError(
                f"Role {user_permissions.role.value} not authorized for tool: {tool_name}"
            )

        # Check parameters
        if parameters:
            for param in parameters.keys():
                if not tool_perm.is_parameter_allowed(param):
                    raise PermissionError(
                        f"Parameter '{param}' not allowed for tool: {tool_name}"
                    )

        return True, tool_perm.requires_confirmation

    def register_tool_permission(self, tool_permission: ToolPermission) -> None:
        """Register a custom tool permission."""
        self._tool_permissions[tool_permission.tool_name] = tool_permission
        logger.info(
            "Registered tool permission",
            tool=tool_permission.tool_name,
            roles=[r.value for r in tool_permission.allowed_roles],
        )

    def get_tool_permission(self, tool_name: str) -> ToolPermission | None:
        """Get permission config for a tool."""
        return self._tool_permissions.get(tool_name)

    def list_available_tools(
        self,
        user_permissions: UserPermissions,
    ) -> list[dict[str, Any]]:
        """List all tools available to a user."""
        available = []

        for tool_name, tool_perm in self._tool_permissions.items():
            if tool_perm.is_allowed(user_permissions.role):
                available.append({
                    "name": tool_name,
                    "requires_confirmation": tool_perm.requires_confirmation,
                    "max_per_hour": tool_perm.max_executions_per_hour,
                })

        return available

    def can_access_resource(
        self,
        user_permissions: UserPermissions,
        resource_type: str,
        resource_id: str,
        action: str = "read",
    ) -> bool:
        """
        Check if user can access a specific resource.

        Args:
            user_permissions: User's permission set
            resource_type: Type of resource (project, document, etc.)
            resource_id: ID of the resource
            action: Action to perform (read, write, delete)

        Returns:
            True if access is allowed
        """
        # Map resource type and action to permission
        permission_map = {
            ("project", "read"): Permission.PROJECT_READ,
            ("project", "write"): Permission.PROJECT_WRITE,
            ("project", "delete"): Permission.PROJECT_DELETE,
            ("document", "read"): Permission.DOCUMENT_READ,
            ("document", "write"): Permission.DOCUMENT_WRITE,
            ("document", "delete"): Permission.DOCUMENT_DELETE,
            ("metrics", "read"): Permission.METRICS_READ,
            ("metrics", "export"): Permission.METRICS_EXPORT,
            ("agent", "read"): Permission.AGENT_READ,
            ("agent", "execute"): Permission.AGENT_EXECUTE,
            ("settings", "read"): Permission.SETTINGS_READ,
            ("settings", "write"): Permission.SETTINGS_WRITE,
        }

        required = permission_map.get((resource_type, action))
        if required is None:
            # Unknown resource/action - deny by default
            logger.warning(
                "Unknown resource access attempt",
                resource_type=resource_type,
                action=action,
            )
            return False

        return user_permissions.has_permission(required)


# Singleton instance
permissions_service = PermissionsService()
