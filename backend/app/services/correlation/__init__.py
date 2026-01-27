"""Correlation Services.

Services for finding relationships between different entities:
- PR-Issue correlation
- Commit-Issue correlation
- Cross-repository dependencies
"""

from app.services.correlation.pr_issue import (
    pr_issue_correlation_service,
    PRIssueCorrelation,
    CorrelationResult,
    CorrelationType,
)

__all__ = [
    "pr_issue_correlation_service",
    "PRIssueCorrelation",
    "CorrelationResult",
    "CorrelationType",
]
