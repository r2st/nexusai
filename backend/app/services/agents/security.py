"""Agent security: domain restrictions and access control."""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any
from urllib.parse import urlparse
import re

import structlog

logger = structlog.get_logger()


class DomainRestrictionMode(str, Enum):
    """Mode for domain restriction enforcement."""

    ALLOW_LIST = "allow_list"  # Only allow specified domains
    BLOCK_LIST = "block_list"  # Block specified domains
    DISABLED = "disabled"      # No restrictions


class ActionType(str, Enum):
    """Types of agent actions that can be restricted."""

    HTTP_REQUEST = "http_request"
    MCP_CALL = "mcp_call"
    TOOL_CALL = "tool_call"
    FILE_ACCESS = "file_access"
    DATABASE_QUERY = "database_query"
    CODE_EXECUTION = "code_execution"


@dataclass
class DomainPolicy:
    """Policy for domain-based access control."""

    policy_id: str
    name: str
    mode: DomainRestrictionMode
    domains: list[str]  # List of domain patterns
    action_types: list[ActionType]  # Which actions this applies to
    enabled: bool = True
    priority: int = 0  # Higher = evaluated first
    tenant_id: str | None = None  # None = global
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AccessDecision:
    """Result of an access control decision."""

    allowed: bool
    reason: str
    policy_id: str | None = None
    domain: str | None = None
    action_type: ActionType | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class DomainRestrictionEnforcer:
    """Enforces domain restrictions for agent actions.

    Implements the NexusChat pattern of restricting which domains
    agents can access for HTTP requests, MCP calls, etc.
    """

    # Default allowed domains (global)
    DEFAULT_ALLOWED_DOMAINS = [
        "*.anthropic.com",
        "*.openai.com",
        "*.google.com",
        "*.googleapis.com",
        "*.azure.com",
        "*.microsoft.com",
    ]

    # Always blocked domains
    BLOCKED_DOMAINS = [
        "*.onion",
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "*.local",
        "*.internal",
    ]

    def __init__(self):
        self._policies: dict[str, DomainPolicy] = {}
        self._default_policy = DomainPolicy(
            policy_id="default",
            name="Default Policy",
            mode=DomainRestrictionMode.ALLOW_LIST,
            domains=self.DEFAULT_ALLOWED_DOMAINS,
            action_types=list(ActionType),
        )

    def add_policy(self, policy: DomainPolicy) -> None:
        """Add a domain restriction policy."""
        self._policies[policy.policy_id] = policy
        logger.info("Domain policy added", policy_id=policy.policy_id, name=policy.name)

    def remove_policy(self, policy_id: str) -> bool:
        """Remove a domain restriction policy."""
        if policy_id in self._policies:
            del self._policies[policy_id]
            logger.info("Domain policy removed", policy_id=policy_id)
            return True
        return False

    def get_policies(
        self,
        tenant_id: str | None = None,
        action_type: ActionType | None = None,
    ) -> list[DomainPolicy]:
        """Get applicable policies."""
        policies = list(self._policies.values())

        # Filter by tenant
        if tenant_id:
            policies = [p for p in policies if p.tenant_id is None or p.tenant_id == tenant_id]
        else:
            policies = [p for p in policies if p.tenant_id is None]

        # Filter by action type
        if action_type:
            policies = [p for p in policies if action_type in p.action_types]

        # Filter by enabled
        policies = [p for p in policies if p.enabled]

        # Sort by priority
        policies.sort(key=lambda p: -p.priority)

        return policies

    def check_access(
        self,
        url_or_domain: str,
        action_type: ActionType,
        tenant_id: str | None = None,
    ) -> AccessDecision:
        """Check if access to a domain is allowed."""
        # Extract domain from URL if needed
        domain = self._extract_domain(url_or_domain)

        # Check always-blocked domains first
        for blocked in self.BLOCKED_DOMAINS:
            if self._matches_pattern(domain, blocked):
                return AccessDecision(
                    allowed=False,
                    reason=f"Domain '{domain}' is in the global blocklist",
                    domain=domain,
                    action_type=action_type,
                )

        # Get applicable policies
        policies = self.get_policies(tenant_id, action_type)

        # If no custom policies, use default
        if not policies:
            policies = [self._default_policy]

        # Evaluate policies in priority order
        for policy in policies:
            decision = self._evaluate_policy(policy, domain, action_type)
            if decision is not None:
                return decision

        # Default deny if no policy matched
        return AccessDecision(
            allowed=False,
            reason="No policy matched - default deny",
            domain=domain,
            action_type=action_type,
        )

    def _extract_domain(self, url_or_domain: str) -> str:
        """Extract domain from URL or return as-is if already a domain."""
        if "://" in url_or_domain:
            parsed = urlparse(url_or_domain)
            return parsed.netloc.lower()
        return url_or_domain.lower()

    def _matches_pattern(self, domain: str, pattern: str) -> bool:
        """Check if domain matches a pattern (supports wildcards)."""
        # Convert pattern to regex
        regex_pattern = pattern.replace(".", r"\.")
        regex_pattern = regex_pattern.replace("*", ".*")
        regex_pattern = f"^{regex_pattern}$"

        try:
            return bool(re.match(regex_pattern, domain, re.IGNORECASE))
        except re.error:
            return False

    def _evaluate_policy(
        self,
        policy: DomainPolicy,
        domain: str,
        action_type: ActionType,
    ) -> AccessDecision | None:
        """Evaluate a single policy against a domain."""
        # Check if action type is covered
        if action_type not in policy.action_types:
            return None

        # Check domain against patterns
        matches = any(self._matches_pattern(domain, pattern) for pattern in policy.domains)

        if policy.mode == DomainRestrictionMode.ALLOW_LIST:
            if matches:
                return AccessDecision(
                    allowed=True,
                    reason=f"Domain '{domain}' allowed by policy '{policy.name}'",
                    policy_id=policy.policy_id,
                    domain=domain,
                    action_type=action_type,
                )
            else:
                return AccessDecision(
                    allowed=False,
                    reason=f"Domain '{domain}' not in allow list of policy '{policy.name}'",
                    policy_id=policy.policy_id,
                    domain=domain,
                    action_type=action_type,
                )

        elif policy.mode == DomainRestrictionMode.BLOCK_LIST:
            if matches:
                return AccessDecision(
                    allowed=False,
                    reason=f"Domain '{domain}' blocked by policy '{policy.name}'",
                    policy_id=policy.policy_id,
                    domain=domain,
                    action_type=action_type,
                )
            else:
                return AccessDecision(
                    allowed=True,
                    reason=f"Domain '{domain}' not in block list of policy '{policy.name}'",
                    policy_id=policy.policy_id,
                    domain=domain,
                    action_type=action_type,
                )

        return None


class AgentSecurityContext:
    """Security context for agent execution."""

    def __init__(
        self,
        agent_id: str,
        tenant_id: str,
        user_id: str,
        domain_enforcer: DomainRestrictionEnforcer | None = None,
        allowed_domains: list[str] | None = None,
        blocked_domains: list[str] | None = None,
        allowed_tools: list[str] | None = None,
        allowed_mcp_servers: list[str] | None = None,
        max_requests_per_minute: int = 60,
        max_code_execution_time: int = 30,
    ):
        self.agent_id = agent_id
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.domain_enforcer = domain_enforcer or DomainRestrictionEnforcer()

        # Set up custom policy if domains provided
        if allowed_domains:
            self._setup_custom_policy(allowed_domains, blocked_domains)

        self.allowed_tools = set(allowed_tools) if allowed_tools else None
        self.allowed_mcp_servers = set(allowed_mcp_servers) if allowed_mcp_servers else None
        self.max_requests_per_minute = max_requests_per_minute
        self.max_code_execution_time = max_code_execution_time

        # Rate limiting state
        self._request_timestamps: list[datetime] = []

    def _setup_custom_policy(
        self,
        allowed_domains: list[str],
        blocked_domains: list[str] | None,
    ) -> None:
        """Set up custom domain policy for this context."""
        # Add allow policy
        allow_policy = DomainPolicy(
            policy_id=f"agent-{self.agent_id}-allow",
            name=f"Agent {self.agent_id} Allow List",
            mode=DomainRestrictionMode.ALLOW_LIST,
            domains=allowed_domains,
            action_types=[ActionType.HTTP_REQUEST, ActionType.MCP_CALL],
            tenant_id=self.tenant_id,
            priority=100,
        )
        self.domain_enforcer.add_policy(allow_policy)

        # Add block policy if provided
        if blocked_domains:
            block_policy = DomainPolicy(
                policy_id=f"agent-{self.agent_id}-block",
                name=f"Agent {self.agent_id} Block List",
                mode=DomainRestrictionMode.BLOCK_LIST,
                domains=blocked_domains,
                action_types=[ActionType.HTTP_REQUEST, ActionType.MCP_CALL],
                tenant_id=self.tenant_id,
                priority=110,  # Higher priority than allow
            )
            self.domain_enforcer.add_policy(block_policy)

    def check_domain_access(
        self,
        url: str,
        action_type: ActionType = ActionType.HTTP_REQUEST,
    ) -> AccessDecision:
        """Check if the agent can access a domain."""
        return self.domain_enforcer.check_access(
            url_or_domain=url,
            action_type=action_type,
            tenant_id=self.tenant_id,
        )

    def check_tool_access(self, tool_name: str) -> bool:
        """Check if the agent can use a tool."""
        if self.allowed_tools is None:
            return True  # No restrictions
        return tool_name in self.allowed_tools

    def check_mcp_server_access(self, server_name: str) -> bool:
        """Check if the agent can access an MCP server."""
        if self.allowed_mcp_servers is None:
            return True  # No restrictions
        return server_name in self.allowed_mcp_servers

    def check_rate_limit(self) -> bool:
        """Check if the agent is within rate limits."""
        now = datetime.now(UTC)
        cutoff = now.replace(second=0, microsecond=0)

        # Remove old timestamps
        self._request_timestamps = [
            ts for ts in self._request_timestamps
            if ts >= cutoff
        ]

        if len(self._request_timestamps) >= self.max_requests_per_minute:
            return False

        self._request_timestamps.append(now)
        return True

    def validate_action(
        self,
        action_type: ActionType,
        target: str,
    ) -> AccessDecision:
        """Validate an agent action against security policies."""
        # Check rate limit
        if not self.check_rate_limit():
            return AccessDecision(
                allowed=False,
                reason="Rate limit exceeded",
                action_type=action_type,
            )

        # Check domain for HTTP/MCP actions
        if action_type in (ActionType.HTTP_REQUEST, ActionType.MCP_CALL):
            return self.check_domain_access(target, action_type)

        # Check tool access
        if action_type == ActionType.TOOL_CALL:
            if self.check_tool_access(target):
                return AccessDecision(
                    allowed=True,
                    reason=f"Tool '{target}' is allowed",
                    action_type=action_type,
                )
            else:
                return AccessDecision(
                    allowed=False,
                    reason=f"Tool '{target}' is not in allowed list",
                    action_type=action_type,
                )

        # Default allow for other action types
        return AccessDecision(
            allowed=True,
            reason="Action type not restricted",
            action_type=action_type,
        )


def create_tenant_domain_policy(
    tenant_id: str,
    allowed_domains: list[str],
    policy_name: str = "Tenant Custom Policy",
) -> DomainPolicy:
    """Create a domain policy for a specific tenant."""
    import uuid

    return DomainPolicy(
        policy_id=str(uuid.uuid4()),
        name=policy_name,
        mode=DomainRestrictionMode.ALLOW_LIST,
        domains=allowed_domains,
        action_types=[ActionType.HTTP_REQUEST, ActionType.MCP_CALL],
        tenant_id=tenant_id,
        priority=50,
    )


# Pre-configured policies for common use cases
ENTERPRISE_POLICY = DomainPolicy(
    policy_id="enterprise-default",
    name="Enterprise Default Policy",
    mode=DomainRestrictionMode.ALLOW_LIST,
    domains=[
        "*.anthropic.com",
        "*.openai.com",
        "*.google.com",
        "*.googleapis.com",
        "*.azure.com",
        "*.microsoft.com",
        "*.github.com",
        "*.githubusercontent.com",
        "*.atlassian.com",
        "*.jira.com",
        "*.slack.com",
    ],
    action_types=[ActionType.HTTP_REQUEST, ActionType.MCP_CALL],
    priority=10,
)

NEXUS_POLICY = DomainPolicy(
    policy_id="nexus-default",
    name="Nexus AI Policy",
    mode=DomainRestrictionMode.ALLOW_LIST,
    domains=[
        "*.nexus.ai",
        "*.google.com",
        "*.googleapis.com",
        "*.anthropic.com",
        "*.openai.com",
    ],
    action_types=[ActionType.HTTP_REQUEST, ActionType.MCP_CALL],
    priority=20,
)
