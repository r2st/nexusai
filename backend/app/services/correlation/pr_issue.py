"""PR-Issue Semantic Similarity Correlation.

Automatically correlates Pull Requests with Issues using:
- Semantic text similarity (embeddings)
- Pattern matching (issue references)
- Temporal proximity
- Author matching
"""

import re
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Float, ForeignKey, String, Text, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship

from app.core.database import Base


class CorrelationType(str):
    """Types of PR-Issue correlations."""
    EXPLICIT = "explicit"  # PR explicitly mentions issue (e.g., "fixes #123")
    SEMANTIC = "semantic"  # Semantic similarity match
    AUTHOR = "author"  # Same author, similar time
    BRANCH = "branch"  # Branch name contains issue number
    COMBINED = "combined"  # Multiple correlation signals


class PRIssueCorrelation(Base):
    """PR-Issue correlation model."""

    __tablename__ = "pr_issue_correlations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # PR information
    pr_id = Column(String(255), nullable=False, index=True)
    pr_number = Column(String(20))
    pr_title = Column(Text)
    pr_description = Column(Text)
    pr_author = Column(String(255))
    pr_created_at = Column(DateTime)

    # Issue information
    issue_id = Column(String(255), nullable=False, index=True)
    issue_number = Column(String(20))
    issue_title = Column(Text)
    issue_description = Column(Text)
    issue_author = Column(String(255))
    issue_created_at = Column(DateTime)

    # Correlation details
    correlation_type = Column(String(50), default=CorrelationType.SEMANTIC)
    confidence_score = Column(Float, default=0.0)  # 0-1
    is_verified = Column(Boolean, default=False)  # Human verified

    # Similarity scores breakdown
    title_similarity = Column(Float, default=0.0)
    description_similarity = Column(Float, default=0.0)
    semantic_similarity = Column(Float, default=0.0)

    # Signals used
    signals = Column(ARRAY(String), default=list)  # ['explicit', 'semantic', 'author', 'branch']
    metadata = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CorrelationResult(BaseModel):
    """Result of correlation analysis."""

    pr_id: str
    issue_id: str
    correlation_type: str
    confidence_score: float
    title_similarity: float
    description_similarity: float
    semantic_similarity: float
    signals: list[str]
    metadata: dict[str, Any] = {}


class PRIssueCorrelationService:
    """Service for correlating PRs with Issues."""

    # Issue reference patterns
    ISSUE_PATTERNS = [
        r"(?:fix(?:es)?|close(?:s)?|resolve(?:s)?)\s+#(\d+)",  # fixes #123
        r"(?:fix(?:es)?|close(?:s)?|resolve(?:s)?)\s+(\w+/\w+)#(\d+)",  # fixes org/repo#123
        r"#(\d+)",  # Simple #123
        r"(?:issue|bug|ticket)\s*[:#]?\s*(\d+)",  # issue: 123
        r"([A-Z]+-\d+)",  # JIRA-style: ABC-123
    ]

    # Branch name patterns
    BRANCH_PATTERNS = [
        r"(?:feature|fix|bugfix|hotfix)[/-](\d+)",  # feature/123 or fix-123
        r"(?:issue)[/-](\d+)",  # issue/123
        r"([A-Z]+-\d+)",  # JIRA-style in branch
    ]

    # Similarity thresholds
    SEMANTIC_THRESHOLD = 0.75
    TITLE_THRESHOLD = 0.6
    COMBINED_THRESHOLD = 0.7

    def __init__(self):
        self._embedding_service = None

    async def _get_embedding_service(self):
        """Lazy load embedding service."""
        if self._embedding_service is None:
            from app.services.similarity.service import code_similarity_service
            self._embedding_service = code_similarity_service
        return self._embedding_service

    async def find_correlations(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_id: str,
        pr: dict[str, Any],
        issues: list[dict[str, Any]],
        threshold: float = 0.5,
    ) -> list[CorrelationResult]:
        """Find correlations between a PR and candidate issues.

        Args:
            session: Database session
            tenant_id: Tenant ID
            project_id: Project ID
            pr: Pull request data
            issues: List of candidate issues
            threshold: Minimum confidence threshold

        Returns:
            List of CorrelationResults above threshold
        """
        correlations = []

        pr_title = pr.get("title", "")
        pr_description = pr.get("description", "")
        pr_author = pr.get("author", "")
        pr_branch = pr.get("branch", "")
        pr_full_text = f"{pr_title} {pr_description}"

        for issue in issues:
            signals = []
            scores = {
                "title": 0.0,
                "description": 0.0,
                "semantic": 0.0,
            }

            issue_number = issue.get("number", "")
            issue_title = issue.get("title", "")
            issue_description = issue.get("description", "")
            issue_author = issue.get("author", "")

            # 1. Check explicit references
            if self._check_explicit_reference(pr_full_text, issue_number):
                signals.append("explicit")
                scores["title"] = 1.0  # Explicit match is definitive

            # 2. Check branch name
            if pr_branch and self._check_branch_reference(pr_branch, issue_number):
                signals.append("branch")
                scores["title"] = max(scores["title"], 0.9)

            # 3. Check author match
            if pr_author and pr_author == issue_author:
                # Check temporal proximity (issue before PR, within reasonable time)
                pr_time = pr.get("created_at")
                issue_time = issue.get("created_at")
                if pr_time and issue_time:
                    if isinstance(pr_time, str):
                        pr_time = datetime.fromisoformat(pr_time.replace("Z", "+00:00"))
                    if isinstance(issue_time, str):
                        issue_time = datetime.fromisoformat(issue_time.replace("Z", "+00:00"))

                    if issue_time < pr_time and (pr_time - issue_time) < timedelta(days=30):
                        signals.append("author")
                        scores["title"] = max(scores["title"], 0.5)

            # 4. Calculate text similarity
            scores["title"] = max(
                scores["title"],
                self._calculate_text_similarity(pr_title, issue_title)
            )
            scores["description"] = self._calculate_text_similarity(
                pr_description, issue_description
            )

            # 5. Calculate semantic similarity (if no explicit match)
            if "explicit" not in signals and "branch" not in signals:
                try:
                    embedding_service = await self._get_embedding_service()
                    semantic_score = await embedding_service.calculate_similarity(
                        pr_full_text,
                        f"{issue_title} {issue_description}"
                    )
                    scores["semantic"] = semantic_score
                    if semantic_score >= self.SEMANTIC_THRESHOLD:
                        signals.append("semantic")
                except Exception:
                    pass

            # Calculate combined confidence
            confidence = self._calculate_confidence(signals, scores)

            if confidence >= threshold:
                correlation_type = self._determine_correlation_type(signals)

                correlations.append(CorrelationResult(
                    pr_id=pr.get("id", ""),
                    issue_id=issue.get("id", ""),
                    correlation_type=correlation_type,
                    confidence_score=confidence,
                    title_similarity=scores["title"],
                    description_similarity=scores["description"],
                    semantic_similarity=scores["semantic"],
                    signals=signals,
                    metadata={
                        "pr_number": pr.get("number"),
                        "issue_number": issue_number,
                        "pr_title": pr_title[:100],
                        "issue_title": issue_title[:100],
                    },
                ))

        # Sort by confidence
        correlations.sort(key=lambda x: x.confidence_score, reverse=True)
        return correlations

    def _check_explicit_reference(self, text: str, issue_number: str) -> bool:
        """Check if text explicitly references an issue number."""
        for pattern in self.ISSUE_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    # For patterns with multiple groups
                    if any(str(issue_number) == str(m) for m in match if m):
                        return True
                elif str(issue_number) == str(match):
                    return True
        return False

    def _check_branch_reference(self, branch: str, issue_number: str) -> bool:
        """Check if branch name references an issue number."""
        for pattern in self.BRANCH_PATTERNS:
            matches = re.findall(pattern, branch, re.IGNORECASE)
            for match in matches:
                if str(issue_number) == str(match):
                    return True
        return False

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity using token overlap."""
        if not text1 or not text2:
            return 0.0

        # Tokenize
        tokens1 = set(text1.lower().split())
        tokens2 = set(text2.lower().split())

        # Remove common stop words
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                      "being", "have", "has", "had", "do", "does", "did", "will",
                      "would", "could", "should", "may", "might", "can", "and",
                      "or", "but", "if", "then", "else", "for", "on", "in", "to",
                      "with", "as", "at", "by", "from", "of", "this", "that"}

        tokens1 = tokens1 - stop_words
        tokens2 = tokens2 - stop_words

        if not tokens1 or not tokens2:
            return 0.0

        # Calculate Jaccard similarity
        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)

        return intersection / union if union > 0 else 0.0

    def _calculate_confidence(
        self,
        signals: list[str],
        scores: dict[str, float],
    ) -> float:
        """Calculate overall confidence score."""
        # Explicit reference is highest confidence
        if "explicit" in signals:
            return 0.95 + (0.05 * scores["description"])

        # Branch reference is also high confidence
        if "branch" in signals:
            return 0.85 + (0.1 * scores["semantic"])

        # Combined signals boost confidence
        base_score = 0.0

        # Weight different scores
        if scores["semantic"] > 0:
            base_score = max(base_score, scores["semantic"] * 0.8)

        if scores["title"] > 0:
            base_score = max(base_score, scores["title"] * 0.7)

        if scores["description"] > 0:
            base_score += scores["description"] * 0.2

        # Author match bonus
        if "author" in signals:
            base_score = min(1.0, base_score + 0.15)

        return min(1.0, base_score)

    def _determine_correlation_type(self, signals: list[str]) -> str:
        """Determine the primary correlation type from signals."""
        if "explicit" in signals:
            return CorrelationType.EXPLICIT
        elif "branch" in signals:
            return CorrelationType.BRANCH
        elif len(signals) > 1:
            return CorrelationType.COMBINED
        elif "semantic" in signals:
            return CorrelationType.SEMANTIC
        elif "author" in signals:
            return CorrelationType.AUTHOR
        else:
            return CorrelationType.SEMANTIC

    async def save_correlation(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_id: str,
        pr: dict[str, Any],
        issue: dict[str, Any],
        result: CorrelationResult,
    ) -> PRIssueCorrelation:
        """Save a correlation to the database.

        Args:
            session: Database session
            tenant_id: Tenant ID
            project_id: Project ID
            pr: PR data
            issue: Issue data
            result: Correlation result

        Returns:
            Saved PRIssueCorrelation
        """
        correlation = PRIssueCorrelation(
            tenant_id=tenant_id,
            project_id=project_id,
            pr_id=pr.get("id", ""),
            pr_number=str(pr.get("number", "")),
            pr_title=pr.get("title", "")[:500],
            pr_description=pr.get("description", "")[:2000],
            pr_author=pr.get("author", ""),
            pr_created_at=pr.get("created_at"),
            issue_id=issue.get("id", ""),
            issue_number=str(issue.get("number", "")),
            issue_title=issue.get("title", "")[:500],
            issue_description=issue.get("description", "")[:2000],
            issue_author=issue.get("author", ""),
            issue_created_at=issue.get("created_at"),
            correlation_type=result.correlation_type,
            confidence_score=result.confidence_score,
            title_similarity=result.title_similarity,
            description_similarity=result.description_similarity,
            semantic_similarity=result.semantic_similarity,
            signals=result.signals,
            metadata=result.metadata,
        )

        session.add(correlation)
        await session.commit()
        await session.refresh(correlation)

        return correlation

    async def get_pr_issues(
        self,
        session: AsyncSession,
        tenant_id: str,
        pr_id: str,
        min_confidence: float = 0.5,
    ) -> list[PRIssueCorrelation]:
        """Get issues correlated with a PR.

        Args:
            session: Database session
            tenant_id: Tenant ID
            pr_id: Pull request ID
            min_confidence: Minimum confidence threshold

        Returns:
            List of correlations
        """
        from sqlalchemy import select

        result = await session.execute(
            select(PRIssueCorrelation)
            .where(
                PRIssueCorrelation.tenant_id == tenant_id,
                PRIssueCorrelation.pr_id == pr_id,
                PRIssueCorrelation.confidence_score >= min_confidence,
            )
            .order_by(PRIssueCorrelation.confidence_score.desc())
        )

        return list(result.scalars().all())

    async def get_issue_prs(
        self,
        session: AsyncSession,
        tenant_id: str,
        issue_id: str,
        min_confidence: float = 0.5,
    ) -> list[PRIssueCorrelation]:
        """Get PRs correlated with an issue.

        Args:
            session: Database session
            tenant_id: Tenant ID
            issue_id: Issue ID
            min_confidence: Minimum confidence threshold

        Returns:
            List of correlations
        """
        from sqlalchemy import select

        result = await session.execute(
            select(PRIssueCorrelation)
            .where(
                PRIssueCorrelation.tenant_id == tenant_id,
                PRIssueCorrelation.issue_id == issue_id,
                PRIssueCorrelation.confidence_score >= min_confidence,
            )
            .order_by(PRIssueCorrelation.confidence_score.desc())
        )

        return list(result.scalars().all())

    async def verify_correlation(
        self,
        session: AsyncSession,
        correlation_id: str,
        is_correct: bool,
    ) -> bool:
        """Mark a correlation as human-verified.

        Args:
            session: Database session
            correlation_id: Correlation ID
            is_correct: Whether the correlation is correct

        Returns:
            True if updated
        """
        from sqlalchemy import select

        result = await session.execute(
            select(PRIssueCorrelation).where(PRIssueCorrelation.id == correlation_id)
        )
        correlation = result.scalar_one_or_none()

        if correlation:
            correlation.is_verified = True
            if not is_correct:
                correlation.confidence_score = 0.0  # Mark as incorrect
            await session.commit()
            return True

        return False


# Singleton instance
pr_issue_correlation_service = PRIssueCorrelationService()
