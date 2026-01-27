"""
PolicyServer MCP Tool Handlers

Provides RBAC (Role-Based Access Control), data redaction, and audit logging
functionality through MCP tools for secure AI assistant integration.
"""

import json
import logging
import re
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from .server import MCPToolHandler
from .protocol import MCPTool
from .errors import (
    service_unavailable_error,
    not_found_error,
    auth_required_error,
    invalid_input_error,
    internal_error,
    ToolErrorResponse,
    ErrorCategory,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Data Models
# =============================================================================

class Permission(str, Enum):
    """Available permissions in the system."""

    # Resource permissions
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"

    # Specific capabilities
    VIEW_METRICS = "view_metrics"
    VIEW_CONNECTIONS = "view_connections"
    MANAGE_CONNECTIONS = "manage_connections"
    VIEW_PIPELINES = "view_pipelines"
    RUN_PIPELINES = "run_pipelines"
    VIEW_LOGS = "view_logs"
    VIEW_AUDIT = "view_audit"
    MANAGE_USERS = "manage_users"
    MANAGE_POLICIES = "manage_policies"


class ResourceType(str, Enum):
    """Types of resources that can be protected."""

    PROJECT = "project"
    CONNECTION = "connection"
    PIPELINE = "pipeline"
    BLUEPRINT = "blueprint"
    METRICS = "metrics"
    LOGS = "logs"
    USERS = "users"
    AUDIT = "audit"


@dataclass
class RedactionRule:
    """Rule for redacting sensitive data."""

    name: str
    pattern: str
    replacement: str = "[REDACTED]"
    description: str = ""
    enabled: bool = True

    def apply(self, text: str) -> tuple[str, int]:
        """Apply the redaction rule to text. Returns (redacted_text, count)."""
        if not self.enabled:
            return text, 0

        try:
            compiled = re.compile(self.pattern, re.IGNORECASE)
            redacted, count = compiled.subn(self.replacement, text)
            return redacted, count
        except re.error as e:
            logger.warning(f"Invalid redaction pattern '{self.pattern}': {e}")
            return text, 0


@dataclass
class AuditEntry:
    """Audit log entry."""

    id: str
    timestamp: datetime
    user_id: str
    action: str
    resource_type: str
    resource_id: Optional[str]
    details: Dict[str, Any]
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None


# =============================================================================
# Built-in Redaction Rules
# =============================================================================

DEFAULT_REDACTION_RULES = [
    RedactionRule(
        name="api_key",
        pattern=r'(?:api[_-]?key|apikey)["\s:=]+["\']?([a-zA-Z0-9_\-]{20,})["\']?',
        replacement="[API_KEY_REDACTED]",
        description="Redacts API keys",
    ),
    RedactionRule(
        name="password",
        pattern=r'(?:password|passwd|pwd)["\s:=]+["\']?([^\s"\']{8,})["\']?',
        replacement="[PASSWORD_REDACTED]",
        description="Redacts passwords",
    ),
    RedactionRule(
        name="bearer_token",
        pattern=r'Bearer\s+([a-zA-Z0-9_\-\.]+)',
        replacement="Bearer [TOKEN_REDACTED]",
        description="Redacts Bearer tokens",
    ),
    RedactionRule(
        name="jwt",
        pattern=r'eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*',
        replacement="[JWT_REDACTED]",
        description="Redacts JWT tokens",
    ),
    RedactionRule(
        name="github_token",
        pattern=r'(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{22,})',
        replacement="[GITHUB_TOKEN_REDACTED]",
        description="Redacts GitHub tokens",
    ),
    RedactionRule(
        name="aws_key",
        pattern=r'(AKIA[0-9A-Z]{16})',
        replacement="[AWS_KEY_REDACTED]",
        description="Redacts AWS access keys",
    ),
    RedactionRule(
        name="aws_secret",
        pattern=r'(?:aws_secret|secret_access_key)["\s:=]+["\']?([a-zA-Z0-9/+=]{40})["\']?',
        replacement="[AWS_SECRET_REDACTED]",
        description="Redacts AWS secret keys",
    ),
    RedactionRule(
        name="private_key",
        pattern=r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
        replacement="[PRIVATE_KEY_REDACTED]",
        description="Redacts private keys",
    ),
    RedactionRule(
        name="email",
        pattern=r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        replacement="[EMAIL_REDACTED]",
        description="Redacts email addresses",
        enabled=False,  # Disabled by default, enable if needed
    ),
    RedactionRule(
        name="ip_address",
        pattern=r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b',
        replacement="[IP_REDACTED]",
        description="Redacts IP addresses",
        enabled=False,  # Disabled by default
    ),
    RedactionRule(
        name="connection_string",
        pattern=r'(?:mongodb|postgresql|mysql|redis|amqp)://[^\s]+',
        replacement="[CONNECTION_STRING_REDACTED]",
        description="Redacts database connection strings",
    ),
]


# =============================================================================
# Role Definitions
# =============================================================================

# Default permissions for each role
ROLE_PERMISSIONS = {
    "owner": [p.value for p in Permission],  # All permissions
    "admin": [
        Permission.READ.value,
        Permission.WRITE.value,
        Permission.VIEW_METRICS.value,
        Permission.VIEW_CONNECTIONS.value,
        Permission.MANAGE_CONNECTIONS.value,
        Permission.VIEW_PIPELINES.value,
        Permission.RUN_PIPELINES.value,
        Permission.VIEW_LOGS.value,
        Permission.VIEW_AUDIT.value,
        Permission.MANAGE_USERS.value,
    ],
    "member": [
        Permission.READ.value,
        Permission.VIEW_METRICS.value,
        Permission.VIEW_CONNECTIONS.value,
        Permission.VIEW_PIPELINES.value,
        Permission.RUN_PIPELINES.value,
        Permission.VIEW_LOGS.value,
    ],
    "developer": [
        Permission.READ.value,
        Permission.VIEW_METRICS.value,
        Permission.VIEW_CONNECTIONS.value,
        Permission.VIEW_PIPELINES.value,
        Permission.VIEW_LOGS.value,
    ],
    "viewer": [
        Permission.READ.value,
        Permission.VIEW_METRICS.value,
    ],
}


# =============================================================================
# Policy Service (In-Memory for Demo)
# =============================================================================

class PolicyService:
    """Service for managing policies, RBAC, and redaction rules."""

    def __init__(self):
        self._redaction_rules = {r.name: r for r in DEFAULT_REDACTION_RULES}
        self._audit_log: List[AuditEntry] = []
        self._custom_policies: Dict[str, Dict] = {}

    def check_permission(
        self,
        user_role: str,
        permission: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> tuple[bool, str]:
        """
        Check if a role has a specific permission.

        Returns:
            (allowed, reason)
        """
        role_perms = ROLE_PERMISSIONS.get(user_role.lower(), [])

        if permission in role_perms:
            return True, f"Permission '{permission}' granted via role '{user_role}'"

        # Check for admin permission (grants all)
        if Permission.ADMIN.value in role_perms:
            return True, f"Permission '{permission}' granted via admin role"

        return False, f"Role '{user_role}' does not have permission '{permission}'"

    def get_role_permissions(self, role: str) -> List[str]:
        """Get all permissions for a role."""
        return ROLE_PERMISSIONS.get(role.lower(), [])

    def apply_redaction(
        self,
        text: str,
        rule_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Apply redaction rules to text.

        Args:
            text: Text to redact
            rule_names: Specific rules to apply (None = all enabled rules)

        Returns:
            Dictionary with redacted text and statistics
        """
        if not text:
            return {
                "original_length": 0,
                "redacted_text": "",
                "redactions_applied": 0,
                "rules_matched": [],
            }

        rules_to_apply = []
        if rule_names:
            for name in rule_names:
                if name in self._redaction_rules:
                    rules_to_apply.append(self._redaction_rules[name])
        else:
            rules_to_apply = [r for r in self._redaction_rules.values() if r.enabled]

        redacted = text
        total_redactions = 0
        matched_rules = []

        for rule in rules_to_apply:
            redacted, count = rule.apply(redacted)
            if count > 0:
                total_redactions += count
                matched_rules.append({
                    "rule": rule.name,
                    "count": count,
                    "description": rule.description,
                })

        return {
            "original_length": len(text),
            "redacted_length": len(redacted),
            "redacted_text": redacted,
            "redactions_applied": total_redactions,
            "rules_matched": matched_rules,
        }

    def add_audit_entry(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> AuditEntry:
        """Add an entry to the audit log."""
        from uuid import uuid4

        entry = AuditEntry(
            id=str(uuid4()),
            timestamp=datetime.now(UTC),
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            success=success,
            error_message=error_message,
        )

        self._audit_log.append(entry)

        # Keep only last 1000 entries in memory
        if len(self._audit_log) > 1000:
            self._audit_log = self._audit_log[-1000:]

        return entry

    def get_audit_log(
        self,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[AuditEntry]:
        """Query the audit log."""
        results = self._audit_log

        if user_id:
            results = [e for e in results if e.user_id == user_id]
        if action:
            results = [e for e in results if e.action == action]
        if resource_type:
            results = [e for e in results if e.resource_type == resource_type]

        # Return most recent first
        return sorted(results, key=lambda e: e.timestamp, reverse=True)[:limit]

    def list_redaction_rules(self) -> List[Dict]:
        """List all redaction rules."""
        return [
            {
                "name": r.name,
                "pattern": r.pattern,
                "replacement": r.replacement,
                "description": r.description,
                "enabled": r.enabled,
            }
            for r in self._redaction_rules.values()
        ]

    def toggle_redaction_rule(self, rule_name: str, enabled: bool) -> bool:
        """Enable or disable a redaction rule."""
        if rule_name in self._redaction_rules:
            self._redaction_rules[rule_name].enabled = enabled
            return True
        return False

    def add_redaction_rule(
        self,
        name: str,
        pattern: str,
        replacement: str = "[REDACTED]",
        description: str = "",
    ) -> bool:
        """Add a custom redaction rule."""
        # Validate pattern
        try:
            re.compile(pattern)
        except re.error:
            return False

        self._redaction_rules[name] = RedactionRule(
            name=name,
            pattern=pattern,
            replacement=replacement,
            description=description,
            enabled=True,
        )
        return True


# Global policy service instance
policy_service = PolicyService()


# =============================================================================
# RBAC Tools
# =============================================================================

class PolicyCheckPermissionHandler(MCPToolHandler):
    """Check if a user has a specific permission."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="policy_check_permission",
            description="Check if a user role has permission to perform an action. Returns whether the action is allowed and the reason.",
            input_schema={
                "type": "object",
                "properties": {
                    "role": {
                        "type": "string",
                        "description": "User role (owner, admin, member, developer, viewer)",
                        "enum": ["owner", "admin", "member", "developer", "viewer"],
                    },
                    "permission": {
                        "type": "string",
                        "description": "Permission to check",
                        "enum": [p.value for p in Permission],
                    },
                    "resource_type": {
                        "type": "string",
                        "description": "Optional resource type for context",
                        "enum": [r.value for r in ResourceType],
                    },
                    "resource_id": {
                        "type": "string",
                        "description": "Optional resource ID for context",
                    },
                },
                "required": ["role", "permission"],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        role = arguments["role"]
        permission = arguments["permission"]
        resource_type = arguments.get("resource_type")
        resource_id = arguments.get("resource_id")

        allowed, reason = policy_service.check_permission(
            user_role=role,
            permission=permission,
            resource_type=resource_type,
            resource_id=resource_id,
        )

        # Log the check
        policy_service.add_audit_entry(
            user_id=context.get("user_id", "unknown"),
            action="permission_check",
            resource_type=resource_type or "system",
            resource_id=resource_id,
            details={
                "role": role,
                "permission": permission,
                "allowed": allowed,
            },
        )

        return {
            "success": True,
            "allowed": allowed,
            "reason": reason,
            "role": role,
            "permission": permission,
            "resource_type": resource_type,
            "resource_id": resource_id,
        }


class PolicyListRolePermissionsHandler(MCPToolHandler):
    """List all permissions for a role."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="policy_list_role_permissions",
            description="List all permissions granted to a specific role",
            input_schema={
                "type": "object",
                "properties": {
                    "role": {
                        "type": "string",
                        "description": "Role to list permissions for",
                        "enum": ["owner", "admin", "member", "developer", "viewer"],
                    },
                },
                "required": ["role"],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        role = arguments["role"]
        permissions = policy_service.get_role_permissions(role)

        return {
            "success": True,
            "role": role,
            "permission_count": len(permissions),
            "permissions": permissions,
            "all_available_permissions": [p.value for p in Permission],
        }


class PolicyListAllRolesHandler(MCPToolHandler):
    """List all available roles and their permissions."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="policy_list_all_roles",
            description="List all available roles in the system with their permission summaries",
            input_schema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        roles = []
        for role_name, permissions in ROLE_PERMISSIONS.items():
            roles.append({
                "role": role_name,
                "permission_count": len(permissions),
                "has_admin": Permission.ADMIN.value in permissions,
                "can_write": Permission.WRITE.value in permissions,
                "can_manage_users": Permission.MANAGE_USERS.value in permissions,
            })

        return {
            "success": True,
            "role_count": len(roles),
            "roles": roles,
            "hierarchy": ["owner", "admin", "member", "developer", "viewer"],
            "description": "Roles are hierarchical. Higher roles include most permissions of lower roles.",
        }


# =============================================================================
# Redaction Tools
# =============================================================================

class PolicyApplyRedactionHandler(MCPToolHandler):
    """Apply redaction rules to text."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="policy_apply_redaction",
            description="Apply data redaction rules to text to remove sensitive information like API keys, passwords, and tokens",
            input_schema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to apply redaction to",
                    },
                    "rules": {
                        "type": "array",
                        "description": "Specific rule names to apply (omit for all enabled rules)",
                        "items": {"type": "string"},
                    },
                },
                "required": ["text"],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        text = arguments["text"]
        rules = arguments.get("rules")

        result = policy_service.apply_redaction(text, rules)

        # Log the redaction
        if result["redactions_applied"] > 0:
            policy_service.add_audit_entry(
                user_id=context.get("user_id", "unknown"),
                action="apply_redaction",
                resource_type="text",
                details={
                    "original_length": result["original_length"],
                    "redactions_applied": result["redactions_applied"],
                    "rules_matched": [r["rule"] for r in result["rules_matched"]],
                },
            )

        return {
            "success": True,
            **result,
        }


class PolicyListRedactionRulesHandler(MCPToolHandler):
    """List all available redaction rules."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="policy_list_redaction_rules",
            description="List all available data redaction rules, including built-in and custom rules",
            input_schema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        rules = policy_service.list_redaction_rules()
        enabled_count = sum(1 for r in rules if r["enabled"])

        return {
            "success": True,
            "total_rules": len(rules),
            "enabled_rules": enabled_count,
            "disabled_rules": len(rules) - enabled_count,
            "rules": rules,
        }


class PolicyToggleRedactionRuleHandler(MCPToolHandler):
    """Enable or disable a redaction rule."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="policy_toggle_redaction_rule",
            description="Enable or disable a specific redaction rule",
            input_schema={
                "type": "object",
                "properties": {
                    "rule_name": {
                        "type": "string",
                        "description": "Name of the redaction rule",
                    },
                    "enabled": {
                        "type": "boolean",
                        "description": "Whether to enable (true) or disable (false) the rule",
                    },
                },
                "required": ["rule_name", "enabled"],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        rule_name = arguments["rule_name"]
        enabled = arguments["enabled"]

        success = policy_service.toggle_redaction_rule(rule_name, enabled)

        if not success:
            return not_found_error(
                resource_type="redaction_rule",
                resource_name=rule_name,
                available_resources=[r["name"] for r in policy_service.list_redaction_rules()],
            ).to_dict()

        # Log the change
        policy_service.add_audit_entry(
            user_id=context.get("user_id", "unknown"),
            action="toggle_redaction_rule",
            resource_type="redaction_rule",
            resource_id=rule_name,
            details={"enabled": enabled},
        )

        return {
            "success": True,
            "rule_name": rule_name,
            "enabled": enabled,
            "message": f"Redaction rule '{rule_name}' {'enabled' if enabled else 'disabled'}",
        }


class PolicyAddRedactionRuleHandler(MCPToolHandler):
    """Add a custom redaction rule."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="policy_add_redaction_rule",
            description="Add a custom data redaction rule with a regex pattern",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Unique name for the rule",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Regex pattern to match sensitive data",
                    },
                    "replacement": {
                        "type": "string",
                        "description": "Text to replace matches with (default: [REDACTED])",
                        "default": "[REDACTED]",
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of what the rule redacts",
                    },
                },
                "required": ["name", "pattern"],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        name = arguments["name"]
        pattern = arguments["pattern"]
        replacement = arguments.get("replacement", "[REDACTED]")
        description = arguments.get("description", "")

        # Validate pattern
        try:
            re.compile(pattern)
        except re.error as e:
            return invalid_input_error(
                parameter_name="pattern",
                expected="Valid regex pattern",
                received=f"Invalid pattern: {e}",
            ).to_dict()

        success = policy_service.add_redaction_rule(
            name=name,
            pattern=pattern,
            replacement=replacement,
            description=description,
        )

        if not success:
            return internal_error(
                operation="add_redaction_rule",
                error_message="Failed to add redaction rule",
            ).to_dict()

        # Log the addition
        policy_service.add_audit_entry(
            user_id=context.get("user_id", "unknown"),
            action="add_redaction_rule",
            resource_type="redaction_rule",
            resource_id=name,
            details={
                "pattern": pattern,
                "replacement": replacement,
            },
        )

        return {
            "success": True,
            "message": f"Redaction rule '{name}' added successfully",
            "rule": {
                "name": name,
                "pattern": pattern,
                "replacement": replacement,
                "description": description,
                "enabled": True,
            },
        }


# =============================================================================
# Audit Tools
# =============================================================================

class PolicyGetAuditLogHandler(MCPToolHandler):
    """Query the audit log."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="policy_get_audit_log",
            description="Query the security audit log for user actions and system events",
            input_schema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "Filter by user ID",
                    },
                    "action": {
                        "type": "string",
                        "description": "Filter by action type",
                    },
                    "resource_type": {
                        "type": "string",
                        "description": "Filter by resource type",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of entries to return (default: 50)",
                        "default": 50,
                    },
                },
                "required": [],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        user_id = arguments.get("user_id")
        action = arguments.get("action")
        resource_type = arguments.get("resource_type")
        limit = arguments.get("limit", 50)

        entries = policy_service.get_audit_log(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            limit=limit,
        )

        return {
            "success": True,
            "count": len(entries),
            "filters": {
                "user_id": user_id,
                "action": action,
                "resource_type": resource_type,
            },
            "entries": [
                {
                    "id": e.id,
                    "timestamp": e.timestamp.isoformat(),
                    "user_id": e.user_id,
                    "action": e.action,
                    "resource_type": e.resource_type,
                    "resource_id": e.resource_id,
                    "success": e.success,
                    "details": e.details,
                }
                for e in entries
            ],
        }


class PolicyLogActionHandler(MCPToolHandler):
    """Log a custom action to the audit log."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="policy_log_action",
            description="Log a custom action to the audit trail for compliance tracking",
            input_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Action being performed (e.g., 'view_metrics', 'export_data')",
                    },
                    "resource_type": {
                        "type": "string",
                        "description": "Type of resource being acted upon",
                    },
                    "resource_id": {
                        "type": "string",
                        "description": "ID of the specific resource",
                    },
                    "details": {
                        "type": "object",
                        "description": "Additional details about the action",
                    },
                    "success": {
                        "type": "boolean",
                        "description": "Whether the action succeeded",
                        "default": True,
                    },
                },
                "required": ["action", "resource_type"],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        action = arguments["action"]
        resource_type = arguments["resource_type"]
        resource_id = arguments.get("resource_id")
        details = arguments.get("details", {})
        success = arguments.get("success", True)

        entry = policy_service.add_audit_entry(
            user_id=context.get("user_id", "unknown"),
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            success=success,
        )

        return {
            "success": True,
            "message": "Action logged to audit trail",
            "entry_id": entry.id,
            "timestamp": entry.timestamp.isoformat(),
        }


class PolicyGetAuditSummaryHandler(MCPToolHandler):
    """Get a summary of audit log activity."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="policy_get_audit_summary",
            description="Get a summary of recent audit log activity including action counts and user activity",
            input_schema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        entries = policy_service.get_audit_log(limit=1000)

        if not entries:
            return {
                "success": True,
                "total_entries": 0,
                "message": "No audit entries found",
            }

        # Count by action
        action_counts: Dict[str, int] = {}
        user_counts: Dict[str, int] = {}
        resource_counts: Dict[str, int] = {}
        success_count = 0
        failure_count = 0

        for entry in entries:
            action_counts[entry.action] = action_counts.get(entry.action, 0) + 1
            user_counts[entry.user_id] = user_counts.get(entry.user_id, 0) + 1
            resource_counts[entry.resource_type] = resource_counts.get(entry.resource_type, 0) + 1
            if entry.success:
                success_count += 1
            else:
                failure_count += 1

        return {
            "success": True,
            "total_entries": len(entries),
            "success_rate": f"{(success_count / len(entries) * 100):.1f}%",
            "failures": failure_count,
            "top_actions": sorted(action_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            "top_users": sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            "resource_breakdown": resource_counts,
            "time_range": {
                "oldest": entries[-1].timestamp.isoformat() if entries else None,
                "newest": entries[0].timestamp.isoformat() if entries else None,
            },
        }


# =============================================================================
# Helper function to get all policy tool handlers
# =============================================================================

def get_all_policy_tool_handlers() -> list[MCPToolHandler]:
    """Return all Policy MCP tool handlers."""
    return [
        # RBAC tools
        PolicyCheckPermissionHandler(),
        PolicyListRolePermissionsHandler(),
        PolicyListAllRolesHandler(),

        # Redaction tools
        PolicyApplyRedactionHandler(),
        PolicyListRedactionRulesHandler(),
        PolicyToggleRedactionRuleHandler(),
        PolicyAddRedactionRuleHandler(),

        # Audit tools
        PolicyGetAuditLogHandler(),
        PolicyLogActionHandler(),
        PolicyGetAuditSummaryHandler(),
    ]
