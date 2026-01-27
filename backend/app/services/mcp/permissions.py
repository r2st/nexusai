"""
MCP Permission Enforcement System

Provides fine-grained permission control for MCP tools:
- Role-based access control (RBAC)
- Organization-level permissions
- Tool-specific permissions
- Resource-based permissions (e.g., specific repos, projects)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
import structlog

logger = structlog.get_logger()


class Permission(str, Enum):
    """Available permissions for MCP tools."""

    # DevLake permissions
    DEVLAKE_READ = "devlake:read"
    DEVLAKE_WRITE = "devlake:write"
    DEVLAKE_ADMIN = "devlake:admin"

    # Repository permissions
    REPO_READ = "repo:read"
    REPO_WRITE = "repo:write"
    REPO_ADMIN = "repo:admin"

    # CI/CD permissions
    CI_READ = "ci:read"
    CI_TRIGGER = "ci:trigger"
    CI_ADMIN = "ci:admin"

    # Jira permissions
    JIRA_READ = "jira:read"
    JIRA_WRITE = "jira:write"
    JIRA_ADMIN = "jira:admin"

    # Observability permissions
    OBS_READ = "observability:read"
    OBS_WRITE = "observability:write"
    OBS_ADMIN = "observability:admin"

    # Policy permissions
    POLICY_READ = "policy:read"
    POLICY_WRITE = "policy:write"
    POLICY_ADMIN = "policy:admin"

    # Admin permissions
    TOOL_ADMIN = "tool:admin"
    APPROVAL_ADMIN = "approval:admin"
    AUDIT_READ = "audit:read"


@dataclass
class ToolPermissionRequirement:
    """Permission requirements for a tool."""

    tool_name: str
    required_permissions: list[Permission] = field(default_factory=list)
    any_of_permissions: list[Permission] = field(default_factory=list)  # OR condition
    resource_permission: Optional[str] = None  # e.g., "repo:{repo_name}:read"


# Default permission mappings for tool categories
DEFAULT_TOOL_PERMISSIONS: dict[str, ToolPermissionRequirement] = {
    # DevLake tools
    "devlake_get_dora_metrics": ToolPermissionRequirement(
        tool_name="devlake_get_dora_metrics",
        required_permissions=[Permission.DEVLAKE_READ],
    ),
    "devlake_list_connections": ToolPermissionRequirement(
        tool_name="devlake_list_connections",
        required_permissions=[Permission.DEVLAKE_READ],
    ),
    "devlake_create_connection": ToolPermissionRequirement(
        tool_name="devlake_create_connection",
        required_permissions=[Permission.DEVLAKE_WRITE],
    ),
    "devlake_delete_connection": ToolPermissionRequirement(
        tool_name="devlake_delete_connection",
        required_permissions=[Permission.DEVLAKE_ADMIN],
    ),
    "devlake_run_pipeline": ToolPermissionRequirement(
        tool_name="devlake_run_pipeline",
        required_permissions=[Permission.DEVLAKE_WRITE],
    ),
    "devlake_setup_github": ToolPermissionRequirement(
        tool_name="devlake_setup_github",
        required_permissions=[Permission.DEVLAKE_WRITE],
    ),
    # Repository tools
    "repo_search_code": ToolPermissionRequirement(
        tool_name="repo_search_code",
        required_permissions=[Permission.REPO_READ],
    ),
    "repo_get_file": ToolPermissionRequirement(
        tool_name="repo_get_file",
        required_permissions=[Permission.REPO_READ],
    ),
    "repo_list_commits": ToolPermissionRequirement(
        tool_name="repo_list_commits",
        required_permissions=[Permission.REPO_READ],
    ),
    "repo_get_diff": ToolPermissionRequirement(
        tool_name="repo_get_diff",
        required_permissions=[Permission.REPO_READ],
    ),
    # CI/CD tools
    "ci_get_build_logs": ToolPermissionRequirement(
        tool_name="ci_get_build_logs",
        required_permissions=[Permission.CI_READ],
    ),
    "ci_get_test_results": ToolPermissionRequirement(
        tool_name="ci_get_test_results",
        required_permissions=[Permission.CI_READ],
    ),
    "ci_trigger_build": ToolPermissionRequirement(
        tool_name="ci_trigger_build",
        required_permissions=[Permission.CI_TRIGGER],
    ),
    "ci_cancel_build": ToolPermissionRequirement(
        tool_name="ci_cancel_build",
        required_permissions=[Permission.CI_TRIGGER],
    ),
    # Jira tools
    "jira_search_issues": ToolPermissionRequirement(
        tool_name="jira_search_issues",
        required_permissions=[Permission.JIRA_READ],
    ),
    "jira_get_issue": ToolPermissionRequirement(
        tool_name="jira_get_issue",
        required_permissions=[Permission.JIRA_READ],
    ),
    "jira_create_issue": ToolPermissionRequirement(
        tool_name="jira_create_issue",
        required_permissions=[Permission.JIRA_WRITE],
    ),
    "jira_update_issue": ToolPermissionRequirement(
        tool_name="jira_update_issue",
        required_permissions=[Permission.JIRA_WRITE],
    ),
    # Observability tools
    "obs_get_traces": ToolPermissionRequirement(
        tool_name="obs_get_traces",
        required_permissions=[Permission.OBS_READ],
    ),
    "obs_get_logs": ToolPermissionRequirement(
        tool_name="obs_get_logs",
        required_permissions=[Permission.OBS_READ],
    ),
    "obs_get_metrics": ToolPermissionRequirement(
        tool_name="obs_get_metrics",
        required_permissions=[Permission.OBS_READ],
    ),
    "obs_create_alert": ToolPermissionRequirement(
        tool_name="obs_create_alert",
        required_permissions=[Permission.OBS_WRITE],
    ),
    # Policy tools
    "policy_check_access": ToolPermissionRequirement(
        tool_name="policy_check_access",
        required_permissions=[Permission.POLICY_READ],
    ),
    "policy_get_audit_log": ToolPermissionRequirement(
        tool_name="policy_get_audit_log",
        required_permissions=[Permission.AUDIT_READ],
    ),
}


# Role to permissions mapping
ROLE_PERMISSIONS: dict[str, list[Permission]] = {
    "admin": [
        Permission.DEVLAKE_ADMIN,
        Permission.REPO_ADMIN,
        Permission.CI_ADMIN,
        Permission.JIRA_ADMIN,
        Permission.OBS_ADMIN,
        Permission.POLICY_ADMIN,
        Permission.TOOL_ADMIN,
        Permission.APPROVAL_ADMIN,
        Permission.AUDIT_READ,
    ],
    "developer": [
        Permission.DEVLAKE_READ,
        Permission.DEVLAKE_WRITE,
        Permission.REPO_READ,
        Permission.REPO_WRITE,
        Permission.CI_READ,
        Permission.CI_TRIGGER,
        Permission.JIRA_READ,
        Permission.JIRA_WRITE,
        Permission.OBS_READ,
        Permission.POLICY_READ,
    ],
    "user": [
        Permission.DEVLAKE_READ,
        Permission.REPO_READ,
        Permission.CI_READ,
        Permission.JIRA_READ,
        Permission.OBS_READ,
        Permission.POLICY_READ,
    ],
    "viewer": [
        Permission.DEVLAKE_READ,
        Permission.REPO_READ,
        Permission.CI_READ,
        Permission.JIRA_READ,
        Permission.OBS_READ,
    ],
}


class PermissionChecker:
    """
    Permission checker for MCP tool invocations.

    Supports:
    - Role-based access control
    - Organization-level permissions
    - Resource-based permissions
    - Custom permission overrides
    """

    def __init__(
        self,
        tool_permissions: Optional[dict[str, ToolPermissionRequirement]] = None,
        role_permissions: Optional[dict[str, list[Permission]]] = None,
    ):
        self.tool_permissions = tool_permissions or DEFAULT_TOOL_PERMISSIONS
        self.role_permissions = role_permissions or ROLE_PERMISSIONS
        self._permission_overrides: dict[str, dict[str, list[Permission]]] = {}  # user_id -> permissions
        self._org_permissions: dict[str, dict[str, list[Permission]]] = {}  # org_id -> user_id -> permissions

    def get_user_permissions(
        self,
        user_id: str,
        roles: list[str],
        organization_id: Optional[str] = None,
    ) -> set[Permission]:
        """Get all permissions for a user based on their roles and overrides."""
        permissions: set[Permission] = set()

        # Add role-based permissions
        for role in roles:
            if role in self.role_permissions:
                permissions.update(self.role_permissions[role])

        # Add user-specific overrides
        if user_id in self._permission_overrides:
            permissions.update(self._permission_overrides[user_id].get("grant", []))
            # Remove denied permissions
            for perm in self._permission_overrides[user_id].get("deny", []):
                permissions.discard(perm)

        # Add organization-level permissions
        if organization_id and organization_id in self._org_permissions:
            if user_id in self._org_permissions[organization_id]:
                permissions.update(self._org_permissions[organization_id][user_id])

        return permissions

    def check_permission(
        self,
        user_id: str,
        tool_name: str,
        roles: list[str],
        organization_id: Optional[str] = None,
        resource_context: Optional[dict[str, Any]] = None,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if a user has permission to use a tool.

        Args:
            user_id: The user's ID
            tool_name: The tool being invoked
            roles: The user's roles
            organization_id: Optional organization context
            resource_context: Optional resource-specific context (e.g., repo name)

        Returns:
            Tuple of (has_permission, error_message)
        """
        # Get user's effective permissions
        user_permissions = self.get_user_permissions(user_id, roles, organization_id)

        # Check for admin override
        if Permission.TOOL_ADMIN in user_permissions:
            return True, None

        # Get tool's permission requirements
        tool_req = self.tool_permissions.get(tool_name)

        # If no specific requirements, allow for any authenticated user
        if tool_req is None:
            # Infer requirements from tool name pattern
            tool_req = self._infer_tool_permissions(tool_name)
            if tool_req is None:
                logger.warning(f"No permission requirements found for tool: {tool_name}")
                return True, None

        # Check required permissions (AND condition)
        for required_perm in tool_req.required_permissions:
            if required_perm not in user_permissions:
                # Check for admin version of the permission
                admin_perm = self._get_admin_permission(required_perm)
                if admin_perm not in user_permissions:
                    return False, f"Missing required permission: {required_perm.value}"

        # Check any_of permissions (OR condition)
        if tool_req.any_of_permissions:
            has_any = any(perm in user_permissions for perm in tool_req.any_of_permissions)
            if not has_any:
                perm_list = ", ".join(p.value for p in tool_req.any_of_permissions)
                return False, f"Missing one of required permissions: {perm_list}"

        # Check resource-specific permission
        if tool_req.resource_permission and resource_context:
            resource_perm = self._resolve_resource_permission(
                tool_req.resource_permission, resource_context
            )
            if resource_perm and resource_perm not in user_permissions:
                return False, f"Missing resource permission: {resource_perm}"

        return True, None

    def _infer_tool_permissions(self, tool_name: str) -> Optional[ToolPermissionRequirement]:
        """Infer permission requirements from tool name pattern."""
        parts = tool_name.lower().split("_")
        if not parts:
            return None

        service = parts[0]

        # Map service to permission category
        service_permission_map = {
            "devlake": Permission.DEVLAKE_READ,
            "repo": Permission.REPO_READ,
            "ci": Permission.CI_READ,
            "jira": Permission.JIRA_READ,
            "obs": Permission.OBS_READ,
            "policy": Permission.POLICY_READ,
        }

        base_perm = service_permission_map.get(service)
        if not base_perm:
            return None

        # Check if it's a write operation
        write_keywords = ["create", "update", "delete", "trigger", "run", "setup", "configure"]
        is_write = any(kw in parts for kw in write_keywords)

        if is_write:
            # Get write permission
            base_perm = Permission(base_perm.value.replace(":read", ":write"))

        # Check if it's an admin operation
        admin_keywords = ["delete", "admin", "remove", "drop"]
        is_admin = any(kw in parts for kw in admin_keywords)

        if is_admin:
            base_perm = Permission(base_perm.value.replace(":read", ":admin").replace(":write", ":admin"))

        return ToolPermissionRequirement(
            tool_name=tool_name,
            required_permissions=[base_perm],
        )

    def _get_admin_permission(self, permission: Permission) -> Permission:
        """Get the admin version of a permission."""
        perm_str = permission.value
        if ":read" in perm_str:
            return Permission(perm_str.replace(":read", ":admin"))
        elif ":write" in perm_str:
            return Permission(perm_str.replace(":write", ":admin"))
        return permission

    def _resolve_resource_permission(
        self, permission_template: str, resource_context: dict[str, Any]
    ) -> Optional[str]:
        """Resolve a resource permission template with context."""
        try:
            return permission_template.format(**resource_context)
        except KeyError:
            return None

    def grant_permission(
        self,
        user_id: str,
        permission: Permission,
        organization_id: Optional[str] = None,
    ) -> None:
        """Grant a permission to a user."""
        if organization_id:
            if organization_id not in self._org_permissions:
                self._org_permissions[organization_id] = {}
            if user_id not in self._org_permissions[organization_id]:
                self._org_permissions[organization_id][user_id] = []
            self._org_permissions[organization_id][user_id].append(permission)
        else:
            if user_id not in self._permission_overrides:
                self._permission_overrides[user_id] = {"grant": [], "deny": []}
            self._permission_overrides[user_id]["grant"].append(permission)

    def revoke_permission(
        self,
        user_id: str,
        permission: Permission,
        organization_id: Optional[str] = None,
    ) -> None:
        """Revoke a permission from a user."""
        if organization_id:
            if (
                organization_id in self._org_permissions
                and user_id in self._org_permissions[organization_id]
            ):
                perms = self._org_permissions[organization_id][user_id]
                if permission in perms:
                    perms.remove(permission)
        else:
            if user_id not in self._permission_overrides:
                self._permission_overrides[user_id] = {"grant": [], "deny": []}
            self._permission_overrides[user_id]["deny"].append(permission)

    def set_tool_permissions(self, tool_name: str, requirement: ToolPermissionRequirement) -> None:
        """Set or update permission requirements for a tool."""
        self.tool_permissions[tool_name] = requirement

    def list_user_permissions(
        self,
        user_id: str,
        roles: list[str],
        organization_id: Optional[str] = None,
    ) -> list[str]:
        """List all permissions for a user."""
        permissions = self.get_user_permissions(user_id, roles, organization_id)
        return [p.value for p in permissions]


# Global permission checker instance
_permission_checker: Optional[PermissionChecker] = None


def get_permission_checker() -> PermissionChecker:
    """Get or create the global permission checker instance."""
    global _permission_checker
    if _permission_checker is None:
        _permission_checker = PermissionChecker()
    return _permission_checker


def reset_permission_checker() -> None:
    """Reset the global permission checker instance."""
    global _permission_checker
    _permission_checker = None
