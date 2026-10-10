"""
MCP Tool Governance Registry

Provides centralized management for tool governance:
- Tool whitelisting/blacklisting
- Organization-level tool access
- Tool versioning and deprecation
- Usage quotas
- Risk classification
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Optional
import structlog

logger = structlog.get_logger()


class ToolRiskLevel(str, Enum):
    """Risk classification for tools."""

    CRITICAL = "critical"  # Can cause data loss, security risks
    HIGH = "high"  # Modifies production systems
    MEDIUM = "medium"  # Read-write operations
    LOW = "low"  # Read-only operations
    MINIMAL = "minimal"  # Safe operations


class ToolStatus(str, Enum):
    """Status of a tool in the registry."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"
    BETA = "beta"
    EXPERIMENTAL = "experimental"


class ToolAccessLevel(str, Enum):
    """Access levels for tools."""

    PUBLIC = "public"  # Available to all
    INTERNAL = "internal"  # Available to org members
    RESTRICTED = "restricted"  # Requires specific permission
    ADMIN = "admin"  # Admin only


@dataclass
class ToolRegistration:
    """Registration entry for a tool."""

    tool_name: str
    service_name: str
    version: str = "1.0.0"

    # Classification
    risk_level: ToolRiskLevel = ToolRiskLevel.MEDIUM
    access_level: ToolAccessLevel = ToolAccessLevel.PUBLIC
    status: ToolStatus = ToolStatus.ACTIVE

    # Description
    display_name: str = ""
    description: str = ""
    category: str = ""
    tags: list[str] = field(default_factory=list)

    # Governance
    requires_approval: bool = False
    max_calls_per_minute: int = 60
    max_calls_per_hour: int = 1000
    max_calls_per_day: int = 10000

    # Whitelisting
    whitelisted_organizations: list[str] = field(default_factory=list)
    blacklisted_organizations: list[str] = field(default_factory=list)
    whitelisted_users: list[str] = field(default_factory=list)
    blacklisted_users: list[str] = field(default_factory=list)

    # Deprecation
    deprecated_at: Optional[datetime] = None
    deprecation_message: str = ""
    replacement_tool: Optional[str] = None

    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    created_by: Optional[str] = None


@dataclass
class OrganizationToolConfig:
    """Organization-specific tool configuration."""

    organization_id: str
    tool_name: str

    # Access
    enabled: bool = True
    access_level_override: Optional[ToolAccessLevel] = None

    # Quotas
    max_calls_per_minute: Optional[int] = None
    max_calls_per_hour: Optional[int] = None
    max_calls_per_day: Optional[int] = None

    # Restrictions
    allowed_users: list[str] = field(default_factory=list)  # If set, only these users can access
    blocked_users: list[str] = field(default_factory=list)

    # Metadata
    custom_config: dict[str, Any] = field(default_factory=dict)
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class ToolGovernanceRegistry:
    """
    Central registry for tool governance.

    Features:
    - Tool registration and discovery
    - Access control management
    - Quota enforcement
    - Risk-based classification
    - Organization-level customization
    """

    def __init__(self):
        self._tools: dict[str, ToolRegistration] = {}
        self._org_configs: dict[str, dict[str, OrganizationToolConfig]] = {}  # org_id -> tool_name -> config
        self._tool_aliases: dict[str, str] = {}

    # =========================================================================
    # Tool Registration
    # =========================================================================

    def register_tool(self, registration: ToolRegistration) -> ToolRegistration:
        """Register a tool in the governance registry."""
        self._tools[registration.tool_name] = registration
        logger.info(
            f"Tool registered",
            tool_name=registration.tool_name,
            service=registration.service_name,
            risk_level=registration.risk_level.value,
        )
        return registration

    def register_tool_simple(
        self,
        tool_name: str,
        service_name: str,
        description: str = "",
        risk_level: ToolRiskLevel = ToolRiskLevel.MEDIUM,
        access_level: ToolAccessLevel = ToolAccessLevel.PUBLIC,
        requires_approval: bool = False,
    ) -> ToolRegistration:
        """Simple tool registration helper."""
        registration = ToolRegistration(
            tool_name=tool_name,
            service_name=service_name,
            display_name=tool_name.replace("_", " ").title(),
            description=description,
            risk_level=risk_level,
            access_level=access_level,
            requires_approval=requires_approval,
        )
        return self.register_tool(registration)

    def get_tool(self, tool_name: str) -> Optional[ToolRegistration]:
        """Get a tool registration."""
        # Check alias first
        actual_name = self._tool_aliases.get(tool_name, tool_name)
        return self._tools.get(actual_name)

    def list_tools(
        self,
        service: Optional[str] = None,
        status: Optional[ToolStatus] = None,
        risk_level: Optional[ToolRiskLevel] = None,
        access_level: Optional[ToolAccessLevel] = None,
        category: Optional[str] = None,
    ) -> list[ToolRegistration]:
        """List tools with optional filters."""
        tools = list(self._tools.values())

        if service:
            tools = [t for t in tools if t.service_name == service]
        if status:
            tools = [t for t in tools if t.status == status]
        if risk_level:
            tools = [t for t in tools if t.risk_level == risk_level]
        if access_level:
            tools = [t for t in tools if t.access_level == access_level]
        if category:
            tools = [t for t in tools if t.category == category]

        return tools

    def update_tool(
        self,
        tool_name: str,
        **updates: Any,
    ) -> Optional[ToolRegistration]:
        """Update a tool registration."""
        tool = self._tools.get(tool_name)
        if not tool:
            return None

        for key, value in updates.items():
            if hasattr(tool, key):
                setattr(tool, key, value)

        tool.updated_at = datetime.now(UTC)
        return tool

    def deprecate_tool(
        self,
        tool_name: str,
        message: str = "",
        replacement: Optional[str] = None,
    ) -> bool:
        """Mark a tool as deprecated."""
        tool = self._tools.get(tool_name)
        if not tool:
            return False

        tool.status = ToolStatus.DEPRECATED
        tool.deprecated_at = datetime.now(UTC)
        tool.deprecation_message = message
        tool.replacement_tool = replacement
        tool.updated_at = datetime.now(UTC)

        logger.info(
            f"Tool deprecated",
            tool_name=tool_name,
            replacement=replacement,
        )
        return True

    def disable_tool(self, tool_name: str) -> bool:
        """Disable a tool."""
        tool = self._tools.get(tool_name)
        if not tool:
            return False

        tool.status = ToolStatus.DISABLED
        tool.updated_at = datetime.now(UTC)

        logger.info(f"Tool disabled", tool_name=tool_name)
        return True

    def enable_tool(self, tool_name: str) -> bool:
        """Enable a tool."""
        tool = self._tools.get(tool_name)
        if not tool:
            return False

        tool.status = ToolStatus.ACTIVE
        tool.updated_at = datetime.now(UTC)

        logger.info(f"Tool enabled", tool_name=tool_name)
        return True

    def create_alias(self, alias: str, tool_name: str) -> bool:
        """Create an alias for a tool."""
        if tool_name not in self._tools:
            return False

        self._tool_aliases[alias] = tool_name
        logger.info(f"Tool alias created", alias=alias, tool_name=tool_name)
        return True

    # =========================================================================
    # Access Control
    # =========================================================================

    def check_access(
        self,
        tool_name: str,
        user_id: str,
        organization_id: Optional[str] = None,
        user_roles: Optional[list[str]] = None,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if a user has access to a tool.

        Returns (allowed, reason) tuple.
        """
        tool = self.get_tool(tool_name)
        if not tool:
            return False, f"Tool {tool_name} not found in registry"

        # Check tool status
        if tool.status == ToolStatus.DISABLED:
            return False, f"Tool {tool_name} is disabled"

        # Check user blacklist
        if user_id in tool.blacklisted_users:
            return False, f"User is blacklisted from using {tool_name}"

        # Check organization blacklist
        if organization_id and organization_id in tool.blacklisted_organizations:
            return False, f"Organization is blacklisted from using {tool_name}"

        # Check whitelists (if set, only whitelisted can access)
        if tool.whitelisted_users and user_id not in tool.whitelisted_users:
            return False, f"User is not whitelisted for {tool_name}"

        if (
            tool.whitelisted_organizations
            and organization_id
            and organization_id not in tool.whitelisted_organizations
        ):
            return False, f"Organization is not whitelisted for {tool_name}"

        # Check organization-level config
        if organization_id:
            org_config = self.get_org_config(organization_id, tool_name)
            if org_config:
                if not org_config.enabled:
                    return False, f"Tool {tool_name} is disabled for this organization"

                if org_config.blocked_users and user_id in org_config.blocked_users:
                    return False, f"User is blocked from using {tool_name} in this organization"

                if (
                    org_config.allowed_users
                    and user_id not in org_config.allowed_users
                ):
                    return False, f"User is not in the allowed list for {tool_name}"

        # Check access level
        roles = user_roles or []

        if tool.access_level == ToolAccessLevel.ADMIN:
            if "admin" not in roles:
                return False, f"Tool {tool_name} requires admin access"

        elif tool.access_level == ToolAccessLevel.RESTRICTED:
            if not any(r in ["admin", "developer"] for r in roles):
                return False, f"Tool {tool_name} requires restricted access"

        elif tool.access_level == ToolAccessLevel.INTERNAL:
            if not organization_id:
                return False, f"Tool {tool_name} requires organization membership"

        return True, None

    def get_effective_quota(
        self,
        tool_name: str,
        organization_id: Optional[str] = None,
    ) -> dict[str, int]:
        """Get the effective quota for a tool, considering org overrides."""
        tool = self.get_tool(tool_name)
        if not tool:
            return {"per_minute": 60, "per_hour": 1000, "per_day": 10000}

        quotas = {
            "per_minute": tool.max_calls_per_minute,
            "per_hour": tool.max_calls_per_hour,
            "per_day": tool.max_calls_per_day,
        }

        # Apply org overrides
        if organization_id:
            org_config = self.get_org_config(organization_id, tool_name)
            if org_config:
                if org_config.max_calls_per_minute:
                    quotas["per_minute"] = org_config.max_calls_per_minute
                if org_config.max_calls_per_hour:
                    quotas["per_hour"] = org_config.max_calls_per_hour
                if org_config.max_calls_per_day:
                    quotas["per_day"] = org_config.max_calls_per_day

        return quotas

    # =========================================================================
    # Organization Configuration
    # =========================================================================

    def set_org_config(self, config: OrganizationToolConfig) -> OrganizationToolConfig:
        """Set organization-specific tool configuration."""
        if config.organization_id not in self._org_configs:
            self._org_configs[config.organization_id] = {}

        self._org_configs[config.organization_id][config.tool_name] = config

        logger.info(
            f"Organization tool config set",
            organization_id=config.organization_id,
            tool_name=config.tool_name,
        )
        return config

    def get_org_config(
        self, organization_id: str, tool_name: str
    ) -> Optional[OrganizationToolConfig]:
        """Get organization-specific tool configuration."""
        org_configs = self._org_configs.get(organization_id, {})
        return org_configs.get(tool_name)

    def list_org_configs(
        self, organization_id: str
    ) -> list[OrganizationToolConfig]:
        """List all tool configurations for an organization."""
        return list(self._org_configs.get(organization_id, {}).values())

    def delete_org_config(self, organization_id: str, tool_name: str) -> bool:
        """Delete organization-specific tool configuration."""
        if organization_id not in self._org_configs:
            return False

        if tool_name not in self._org_configs[organization_id]:
            return False

        del self._org_configs[organization_id][tool_name]
        return True

    # =========================================================================
    # Whitelisting
    # =========================================================================

    def whitelist_organization(self, tool_name: str, organization_id: str) -> bool:
        """Add an organization to a tool's whitelist."""
        tool = self._tools.get(tool_name)
        if not tool:
            return False

        if organization_id not in tool.whitelisted_organizations:
            tool.whitelisted_organizations.append(organization_id)
            tool.updated_at = datetime.now(UTC)

        # Remove from blacklist if present
        if organization_id in tool.blacklisted_organizations:
            tool.blacklisted_organizations.remove(organization_id)

        return True

    def blacklist_organization(self, tool_name: str, organization_id: str) -> bool:
        """Add an organization to a tool's blacklist."""
        tool = self._tools.get(tool_name)
        if not tool:
            return False

        if organization_id not in tool.blacklisted_organizations:
            tool.blacklisted_organizations.append(organization_id)
            tool.updated_at = datetime.now(UTC)

        # Remove from whitelist if present
        if organization_id in tool.whitelisted_organizations:
            tool.whitelisted_organizations.remove(organization_id)

        return True

    def whitelist_user(self, tool_name: str, user_id: str) -> bool:
        """Add a user to a tool's whitelist."""
        tool = self._tools.get(tool_name)
        if not tool:
            return False

        if user_id not in tool.whitelisted_users:
            tool.whitelisted_users.append(user_id)
            tool.updated_at = datetime.now(UTC)

        if user_id in tool.blacklisted_users:
            tool.blacklisted_users.remove(user_id)

        return True

    def blacklist_user(self, tool_name: str, user_id: str) -> bool:
        """Add a user to a tool's blacklist."""
        tool = self._tools.get(tool_name)
        if not tool:
            return False

        if user_id not in tool.blacklisted_users:
            tool.blacklisted_users.append(user_id)
            tool.updated_at = datetime.now(UTC)

        if user_id in tool.whitelisted_users:
            tool.whitelisted_users.remove(user_id)

        return True

    # =========================================================================
    # Discovery
    # =========================================================================

    def get_available_tools(
        self,
        user_id: str,
        organization_id: Optional[str] = None,
        user_roles: Optional[list[str]] = None,
    ) -> list[ToolRegistration]:
        """Get tools available to a user."""
        available = []

        for tool in self._tools.values():
            allowed, _ = self.check_access(
                tool.tool_name,
                user_id,
                organization_id,
                user_roles,
            )
            if allowed:
                available.append(tool)

        return available

    def get_tool_summary(self) -> dict[str, Any]:
        """Get a summary of all registered tools."""
        by_service: dict[str, int] = {}
        by_status: dict[str, int] = {}
        by_risk: dict[str, int] = {}
        by_access: dict[str, int] = {}

        for tool in self._tools.values():
            by_service[tool.service_name] = by_service.get(tool.service_name, 0) + 1
            by_status[tool.status.value] = by_status.get(tool.status.value, 0) + 1
            by_risk[tool.risk_level.value] = by_risk.get(tool.risk_level.value, 0) + 1
            by_access[tool.access_level.value] = by_access.get(tool.access_level.value, 0) + 1

        return {
            "total_tools": len(self._tools),
            "by_service": by_service,
            "by_status": by_status,
            "by_risk_level": by_risk,
            "by_access_level": by_access,
        }


# Global registry instance
_governance_registry: Optional[ToolGovernanceRegistry] = None


def get_governance_registry() -> ToolGovernanceRegistry:
    """Get or create the global governance registry instance."""
    global _governance_registry
    if _governance_registry is None:
        _governance_registry = ToolGovernanceRegistry()
    return _governance_registry


def reset_governance_registry() -> None:
    """Reset the global governance registry instance."""
    global _governance_registry
    _governance_registry = None


def auto_register_tools(registry: ToolGovernanceRegistry) -> None:
    """Auto-register tools from MCP setup with default governance."""
    from .setup import get_all_tools_summary

    summary = get_all_tools_summary()

    # Risk levels by service
    service_risk_mapping = {
        "devlake": ToolRiskLevel.MEDIUM,
        "policy": ToolRiskLevel.HIGH,
        "ci": ToolRiskLevel.MEDIUM,
        "repo": ToolRiskLevel.LOW,
        "jira": ToolRiskLevel.MEDIUM,
        "observability": ToolRiskLevel.LOW,
        "rag": ToolRiskLevel.LOW,
    }

    # Tools that require approval
    approval_patterns = ["delete", "deploy", "execute", "remove", "drop", "trigger"]

    for service_name, service_info in summary["services"].items():
        risk_level = service_risk_mapping.get(service_name, ToolRiskLevel.MEDIUM)

        for tool_info in service_info["tools"]:
            tool_name = tool_info["name"]
            description = tool_info["description"]

            # Check if approval required
            requires_approval = any(
                pattern in tool_name.lower() for pattern in approval_patterns
            )

            # Adjust risk level for specific operations
            tool_risk = risk_level
            if any(pattern in tool_name.lower() for pattern in ["delete", "remove", "drop"]):
                tool_risk = ToolRiskLevel.CRITICAL
            elif "deploy" in tool_name.lower():
                tool_risk = ToolRiskLevel.HIGH

            registry.register_tool_simple(
                tool_name=tool_name,
                service_name=service_name,
                description=description,
                risk_level=tool_risk,
                requires_approval=requires_approval,
            )
