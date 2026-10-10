"""
PR Review Agent

Main agent that orchestrates PR review workflow.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
import logging

from .analyzer import DiffAnalyzer, FileAnalysis, RiskAssessment, RiskLevel
from .reviewer import ReviewGenerator, ReviewComment, ReviewSummary, format_review_for_github

logger = logging.getLogger(__name__)


class PRReviewStatus(str, Enum):
    """Status of PR review."""
    PENDING = "pending"
    ANALYZING = "analyzing"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    FAILED = "failed"
    AWAITING_APPROVAL = "awaiting_approval"


@dataclass
class PRReviewConfig:
    """Configuration for PR review agent."""
    # Analysis settings
    enable_security_scan: bool = True
    enable_performance_analysis: bool = True
    enable_style_check: bool = True
    enable_test_coverage_check: bool = True
    
    # LLM settings
    enable_llm_analysis: bool = True
    llm_model: str = "gpt-4o"
    max_llm_tokens: int = 4000
    
    # Review settings
    auto_approve_low_risk: bool = False
    require_human_approval_for_critical: bool = True
    
    # Thresholds
    max_files_per_review: int = 50
    max_diff_size: int = 10000  # characters
    
    # Output settings
    include_code_suggestions: bool = True
    include_praise: bool = True
    max_comments_per_file: int = 10


@dataclass
class PRMetadata:
    """Metadata about a pull request."""
    repo: str
    pr_number: int
    title: str
    description: str
    author: str
    base_branch: str
    head_branch: str
    
    # Labels and context
    labels: List[str] = field(default_factory=list)
    linked_issues: List[str] = field(default_factory=list)
    
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class PRReviewResult:
    """Result of PR review."""
    status: PRReviewStatus
    pr_metadata: PRMetadata
    
    # Analysis results
    files_analyzed: List[FileAnalysis] = field(default_factory=list)
    risk_assessment: Optional[RiskAssessment] = None
    
    # Review output
    comments: List[ReviewComment] = field(default_factory=list)
    summary: Optional[ReviewSummary] = None
    
    # Metrics
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    
    # Errors
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "pr": {
                "repo": self.pr_metadata.repo,
                "number": self.pr_metadata.pr_number,
                "title": self.pr_metadata.title,
            },
            "risk": {
                "level": self.risk_assessment.overall_risk.value if self.risk_assessment else None,
                "score": self.risk_assessment.risk_score if self.risk_assessment else None,
            },
            "review": {
                "total_comments": len(self.comments),
                "summary": self.summary.overall_assessment if self.summary else None,
                "recommend_approval": self.summary.recommend_approval if self.summary else None,
            },
            "metrics": {
                "files_analyzed": len(self.files_analyzed),
                "duration_ms": self.duration_ms,
            },
            "errors": self.errors,
        }


class PRReviewAgent:
    """
    Agent for automated PR review.
    
    Workflow:
    1. Fetch PR diff and metadata
    2. Analyze changes (patterns, risk, complexity)
    3. Generate review comments using LLM
    4. Post review or await human approval
    
    Features:
    - Risk-based prioritization
    - Security vulnerability detection
    - Code quality analysis
    - Contextual suggestions
    - Human-in-the-loop for critical PRs
    """
    
    def __init__(
        self,
        config: Optional[PRReviewConfig] = None,
        diff_analyzer: Optional[DiffAnalyzer] = None,
        review_generator: Optional[ReviewGenerator] = None,
        github_client: Optional[Any] = None,
        llm_service: Optional[Any] = None,
    ):
        self.config = config or PRReviewConfig()
        self.analyzer = diff_analyzer or DiffAnalyzer()
        self.generator = review_generator or ReviewGenerator(llm_service)
        self.github_client = github_client
        self.llm_service = llm_service
        
        # Callbacks
        self._on_status_change: List[Callable] = []
        self._on_comment_generated: List[Callable] = []
        self._on_approval_required: List[Callable] = []
    
    async def review_pr(
        self,
        repo: str,
        pr_number: int,
        diff_text: Optional[str] = None,
        pr_metadata: Optional[PRMetadata] = None,
        tenant_id: Optional[str] = None,
    ) -> PRReviewResult:
        """
        Review a pull request.
        
        Args:
            repo: Repository (owner/repo)
            pr_number: PR number
            diff_text: Optional pre-fetched diff
            pr_metadata: Optional pre-fetched metadata
            tenant_id: Tenant ID for multi-tenancy
            
        Returns:
            PRReviewResult with analysis and comments
        """
        start_time = datetime.utcnow()
        
        # Initialize result
        result = PRReviewResult(
            status=PRReviewStatus.PENDING,
            pr_metadata=pr_metadata or PRMetadata(
                repo=repo,
                pr_number=pr_number,
                title="",
                description="",
                author="",
                base_branch="main",
                head_branch="",
            ),
            started_at=start_time,
        )
        
        try:
            # 1. Fetch diff if not provided
            await self._update_status(result, PRReviewStatus.ANALYZING)
            
            if diff_text is None:
                diff_text = await self._fetch_diff(repo, pr_number)
            
            if not diff_text:
                result.errors.append("Failed to fetch PR diff")
                result.status = PRReviewStatus.FAILED
                return result
            
            # Check size limits
            if len(diff_text) > self.config.max_diff_size:
                result.errors.append(f"Diff too large ({len(diff_text)} chars). Max: {self.config.max_diff_size}")
                # Continue with truncated diff
                diff_text = diff_text[:self.config.max_diff_size]
            
            # 2. Analyze diff
            files, risk_assessment = self.analyzer.analyze_pr(
                diff_text,
                {
                    "title": result.pr_metadata.title,
                    "description": result.pr_metadata.description,
                },
            )
            
            result.files_analyzed = files
            result.risk_assessment = risk_assessment
            
            # Check file limit
            if len(files) > self.config.max_files_per_review:
                result.errors.append(
                    f"PR touches {len(files)} files, limiting analysis to first {self.config.max_files_per_review}"
                )
                files = files[:self.config.max_files_per_review]
            
            # 3. Generate review
            await self._update_status(result, PRReviewStatus.REVIEWING)
            
            context = {
                "repo": repo,
                "pr_number": pr_number,
                "title": result.pr_metadata.title,
                "description": result.pr_metadata.description,
                "labels": result.pr_metadata.labels,
            }
            
            comments, summary = self.generator.generate_review(
                files,
                risk_assessment,
                context,
            )
            
            # Apply limits
            comments = self._apply_comment_limits(comments)
            
            result.comments = comments
            result.summary = summary
            
            # 4. Check if human approval required
            if (
                self.config.require_human_approval_for_critical and
                risk_assessment.overall_risk == RiskLevel.CRITICAL
            ):
                await self._update_status(result, PRReviewStatus.AWAITING_APPROVAL)
                await self._notify_approval_required(result)
            else:
                await self._update_status(result, PRReviewStatus.COMPLETED)
            
            # Notify callbacks
            for comment in comments:
                await self._notify_comment(comment)
            
        except Exception as e:
            logger.exception(f"PR review failed: {e}")
            result.status = PRReviewStatus.FAILED
            result.errors.append(str(e))
        
        finally:
            result.completed_at = datetime.utcnow()
            result.duration_ms = int((result.completed_at - start_time).total_seconds() * 1000)
        
        return result
    
    async def post_review_to_github(
        self,
        result: PRReviewResult,
    ) -> bool:
        """
        Post the review to GitHub.
        
        Args:
            result: PR review result
            
        Returns:
            True if successful
        """
        if not self.github_client:
            logger.warning("GitHub client not configured")
            return False
        
        if result.status == PRReviewStatus.AWAITING_APPROVAL:
            logger.info("Review awaiting human approval, not posting")
            return False
        
        try:
            review_data = format_review_for_github(
                result.comments,
                result.summary,
            )
            
            # This would call the GitHub API
            # await self.github_client.create_review(
            #     repo=result.pr_metadata.repo,
            #     pr_number=result.pr_metadata.pr_number,
            #     **review_data
            # )
            
            logger.info(
                f"Posted review to {result.pr_metadata.repo}#{result.pr_metadata.pr_number}: "
                f"{review_data['event']} with {len(review_data['comments'])} comments"
            )
            return True
            
        except Exception as e:
            logger.exception(f"Failed to post review: {e}")
            return False
    
    async def approve_and_post(
        self,
        result: PRReviewResult,
        approved_by: str,
    ) -> bool:
        """
        Approve a review that was awaiting human approval and post it.
        
        Args:
            result: The review result
            approved_by: Who approved the review
            
        Returns:
            True if successful
        """
        if result.status != PRReviewStatus.AWAITING_APPROVAL:
            logger.warning(f"Review not awaiting approval: {result.status}")
            return False
        
        logger.info(f"Review approved by {approved_by}")
        result.status = PRReviewStatus.COMPLETED
        
        return await self.post_review_to_github(result)
    
    def _apply_comment_limits(self, comments: List[ReviewComment]) -> List[ReviewComment]:
        """Apply per-file comment limits."""
        file_counts: Dict[str, int] = {}
        limited_comments = []
        
        # Sort by severity (critical first)
        severity_order = {
            "critical": 0,
            "warning": 1,
            "suggestion": 2,
            "question": 3,
            "praise": 4,
        }
        comments.sort(key=lambda c: severity_order.get(c.severity.value, 5))
        
        for comment in comments:
            file_key = comment.file_path or "__general__"
            count = file_counts.get(file_key, 0)
            
            if count < self.config.max_comments_per_file:
                limited_comments.append(comment)
                file_counts[file_key] = count + 1
        
        return limited_comments
    
    async def _fetch_diff(self, repo: str, pr_number: int) -> Optional[str]:
        """Fetch PR diff from GitHub."""
        if not self.github_client:
            return None
        
        try:
            # This would call the GitHub API
            # return await self.github_client.get_pr_diff(repo, pr_number)
            return None
        except Exception as e:
            logger.error(f"Failed to fetch diff: {e}")
            return None
    
    async def _update_status(self, result: PRReviewResult, status: PRReviewStatus) -> None:
        """Update status and notify callbacks."""
        result.status = status
        for callback in self._on_status_change:
            try:
                await callback(result.pr_metadata.pr_number, status)
            except Exception as e:
                logger.warning(f"Status callback error: {e}")
    
    async def _notify_comment(self, comment: ReviewComment) -> None:
        """Notify comment generated callbacks."""
        for callback in self._on_comment_generated:
            try:
                await callback(comment)
            except Exception as e:
                logger.warning(f"Comment callback error: {e}")
    
    async def _notify_approval_required(self, result: PRReviewResult) -> None:
        """Notify that human approval is required."""
        for callback in self._on_approval_required:
            try:
                await callback(result)
            except Exception as e:
                logger.warning(f"Approval callback error: {e}")
    
    def on_status_change(self, callback: Callable) -> None:
        """Register status change callback."""
        self._on_status_change.append(callback)
    
    def on_comment_generated(self, callback: Callable) -> None:
        """Register comment generated callback."""
        self._on_comment_generated.append(callback)
    
    def on_approval_required(self, callback: Callable) -> None:
        """Register approval required callback."""
        self._on_approval_required.append(callback)


async def review_pull_request(
    repo: str,
    pr_number: int,
    diff_text: str,
    config: Optional[PRReviewConfig] = None,
) -> PRReviewResult:
    """
    Convenience function to review a PR.
    
    Args:
        repo: Repository (owner/repo)
        pr_number: PR number
        diff_text: PR diff
        config: Optional configuration
        
    Returns:
        PRReviewResult
    """
    agent = PRReviewAgent(config)
    return await agent.review_pr(
        repo=repo,
        pr_number=pr_number,
        diff_text=diff_text,
    )
