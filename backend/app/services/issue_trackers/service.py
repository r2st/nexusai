"""
Issue Tracker Service

Unified service for interacting with multiple issue trackers.
"""

import logging
from typing import Optional
from functools import lru_cache

from .models import (
    IssueTrackerType,
    Issue,
    IssueCreate,
    IssueUpdate,
    IssueComment,
    Sprint,
    Board,
    IssueTrackerConfig,
    IssueSearchQuery,
    IssueSearchResult,
)
from .providers import (
    BaseIssueTracker,
    JiraProvider,
    AzureBoardsProvider,
    LinearProvider,
    GitHubIssuesProvider,
)

logger = logging.getLogger(__name__)


class IssueTrackerService:
    """
    Unified service for issue tracker integrations.
    
    Provides a consistent interface across:
    - Jira
    - Azure Boards
    - Linear
    - GitHub Issues
    - GitLab Issues
    """
    
    def __init__(self):
        self.providers: dict[str, BaseIssueTracker] = {}
    
    def register_provider(self, name: str, config: IssueTrackerConfig) -> None:
        """Register a new issue tracker provider."""
        provider = self._create_provider(config)
        self.providers[name] = provider
        logger.info(f"Registered issue tracker provider: {name} ({config.tracker_type})")
    
    def _create_provider(self, config: IssueTrackerConfig) -> BaseIssueTracker:
        """Create a provider instance based on type."""
        providers_map = {
            IssueTrackerType.JIRA: JiraProvider,
            IssueTrackerType.AZURE_BOARDS: AzureBoardsProvider,
            IssueTrackerType.LINEAR: LinearProvider,
            IssueTrackerType.GITHUB: GitHubIssuesProvider,
        }
        
        provider_class = providers_map.get(config.tracker_type)
        if not provider_class:
            raise ValueError(f"Unsupported tracker type: {config.tracker_type}")
        
        return provider_class(config)
    
    def get_provider(self, name: str) -> BaseIssueTracker:
        """Get a registered provider by name."""
        if name not in self.providers:
            raise KeyError(f"Provider not found: {name}")
        return self.providers[name]
    
    async def get_issue(self, provider_name: str, issue_key: str) -> Issue:
        """Get an issue from a provider."""
        provider = self.get_provider(provider_name)
        return await provider.get_issue(issue_key)
    
    async def create_issue(self, provider_name: str, data: IssueCreate) -> Issue:
        """Create an issue in a provider."""
        provider = self.get_provider(provider_name)
        issue = await provider.create_issue(data)
        logger.info(f"Created issue {issue.key} in {provider_name}")
        return issue
    
    async def update_issue(
        self, 
        provider_name: str, 
        issue_key: str, 
        data: IssueUpdate
    ) -> Issue:
        """Update an issue in a provider."""
        provider = self.get_provider(provider_name)
        issue = await provider.update_issue(issue_key, data)
        logger.info(f"Updated issue {issue_key} in {provider_name}")
        return issue
    
    async def search_issues(
        self, 
        provider_name: str, 
        query: IssueSearchQuery
    ) -> IssueSearchResult:
        """Search issues in a provider."""
        provider = self.get_provider(provider_name)
        return await provider.search_issues(query)
    
    async def add_comment(
        self, 
        provider_name: str, 
        issue_key: str, 
        body: str
    ) -> IssueComment:
        """Add a comment to an issue."""
        provider = self.get_provider(provider_name)
        comment = await provider.add_comment(issue_key, body)
        logger.info(f"Added comment to {issue_key} in {provider_name}")
        return comment
    
    async def sync_issue_from_analysis(
        self,
        provider_name: str,
        analysis_result: dict,
        project_key: str,
    ) -> list[Issue]:
        """
        Create issues from code analysis results.
        
        Automatically creates issues for:
        - Critical bugs
        - Security vulnerabilities
        - High-priority technical debt
        """
        created_issues = []
        
        # Create issues for critical findings
        for finding in analysis_result.get("critical_findings", []):
            issue_data = IssueCreate(
                title=finding["title"],
                description=self._format_finding_description(finding),
                issue_type=self._map_finding_type(finding["type"]),
                priority=self._map_finding_priority(finding["severity"]),
                project_key=project_key,
                labels=["nexusai", "auto-generated", finding["type"]],
            )
            
            try:
                issue = await self.create_issue(provider_name, issue_data)
                created_issues.append(issue)
            except Exception as e:
                logger.error(f"Failed to create issue for finding: {e}")
        
        return created_issues
    
    def _format_finding_description(self, finding: dict) -> str:
        """Format a finding as issue description."""
        lines = [
            "## Description",
            finding.get("description", ""),
            "",
            "## Details",
            f"- **File**: {finding.get('file', 'Unknown')}",
            f"- **Line**: {finding.get('line', 'N/A')}",
            f"- **Severity**: {finding.get('severity', 'Unknown')}",
            "",
            "## Recommendation",
            finding.get("recommendation", "Review and fix as appropriate."),
            "",
            "---",
            "*This issue was automatically created by NexusAI*",
        ]
        return "\n".join(lines)
    
    def _map_finding_type(self, finding_type: str) -> "IssueType":
        """Map finding type to issue type."""
        from .models import IssueType
        
        mapping = {
            "bug": IssueType.BUG,
            "security": IssueType.SECURITY,
            "vulnerability": IssueType.SECURITY,
            "tech_debt": IssueType.TECH_DEBT,
            "complexity": IssueType.TECH_DEBT,
            "duplication": IssueType.TECH_DEBT,
        }
        return mapping.get(finding_type.lower(), IssueType.TASK)
    
    def _map_finding_priority(self, severity: str) -> "IssuePriority":
        """Map finding severity to priority."""
        from .models import IssuePriority
        
        mapping = {
            "critical": IssuePriority.CRITICAL,
            "high": IssuePriority.HIGH,
            "medium": IssuePriority.MEDIUM,
            "low": IssuePriority.LOW,
        }
        return mapping.get(severity.lower(), IssuePriority.MEDIUM)
    
    async def link_pr_to_issue(
        self,
        provider_name: str,
        issue_key: str,
        pr_url: str,
        pr_title: str,
    ) -> None:
        """Link a PR to an issue via comment."""
        body = f"Pull Request linked: [{pr_title}]({pr_url})"
        await self.add_comment(provider_name, issue_key, body)
    
    async def close_all(self):
        """Close all provider connections."""
        for provider in self.providers.values():
            await provider.close()


# Singleton instance
_service: Optional[IssueTrackerService] = None


def get_issue_tracker_service() -> IssueTrackerService:
    """Get the issue tracker service singleton."""
    global _service
    if _service is None:
        _service = IssueTrackerService()
    return _service
