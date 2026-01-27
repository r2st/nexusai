"""Code Review Service - Main service orchestrating code review automation."""

import logging
from typing import Any

from app.services.code_review.analyzer import PRAnalyzer
from app.services.code_review.models import (
    CodeReview,
    DiffAnalysis,
    PRInfo,
    ReviewConfig,
    WebhookEvent,
)
from app.services.code_review.reviewer import ReviewGenerator
from app.services.code_review.smells import CodeSmellDetector
from app.services.code_review.webhooks import (
    GitHubClient,
    GitLabClient,
    WebhookConfig,
    WebhookHandler,
)

logger = logging.getLogger(__name__)


class CodeReviewService:
    """Main service for automated code reviews.

    Orchestrates PR analysis, code smell detection, and review generation.
    Integrates with GitHub and GitLab via webhooks.
    """

    def __init__(
        self,
        llm_gateway: Any | None = None,
        github_token: str | None = None,
        gitlab_token: str | None = None,
        review_config: ReviewConfig | None = None,
        webhook_config: WebhookConfig | None = None,
    ):
        """Initialize code review service.

        Args:
            llm_gateway: LLM gateway for review generation
            github_token: GitHub API token
            gitlab_token: GitLab API token
            review_config: Review configuration
            webhook_config: Webhook configuration
        """
        self._llm_gateway = llm_gateway
        self._config = review_config or ReviewConfig()

        # Initialize components
        self._analyzer = PRAnalyzer()
        self._smell_detector = CodeSmellDetector()
        self._reviewer = ReviewGenerator(llm_gateway, review_config)
        self._webhook_handler = WebhookHandler(webhook_config)

        # Initialize API clients
        self._github = GitHubClient(github_token) if github_token else None
        self._gitlab = GitLabClient(gitlab_token) if gitlab_token else None

    async def review_github_pr(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        post_review: bool = True,
        context: dict[str, Any] | None = None,
    ) -> CodeReview:
        """Review a GitHub pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            post_review: Whether to post review to GitHub
            context: Additional context for review

        Returns:
            Generated code review
        """
        if not self._github:
            raise ValueError("GitHub client not configured")

        logger.info(f"Reviewing GitHub PR: {owner}/{repo}#{pr_number}")

        # Fetch PR data
        pr_data = await self._github.get_pr_diff(owner, repo, pr_number)

        # Build PR info
        pr_info = PRInfo(
            number=pr_number,
            title=pr_data.get("title", ""),
            description=pr_data.get("body"),
            author=pr_data.get("user", {}).get("login", ""),
            base_branch=pr_data.get("base", {}).get("ref", ""),
            head_branch=pr_data.get("head", {}).get("ref", ""),
            repository=f"{owner}/{repo}",
            url=pr_data.get("html_url", ""),
            additions=pr_data.get("additions", 0),
            deletions=pr_data.get("deletions", 0),
            files_changed=pr_data.get("changed_files", 0),
        )

        # Generate review
        review = await self._review_pr(pr_info, pr_data.get("files", []), context)

        # Post review if requested
        if post_review:
            await self._post_github_review(owner, repo, pr_number, review)

        return review

    async def review_gitlab_mr(
        self,
        project: str,
        mr_iid: int,
        post_review: bool = True,
        context: dict[str, Any] | None = None,
    ) -> CodeReview:
        """Review a GitLab merge request.

        Args:
            project: Project path or ID
            mr_iid: Merge request IID
            post_review: Whether to post review to GitLab
            context: Additional context for review

        Returns:
            Generated code review
        """
        if not self._gitlab:
            raise ValueError("GitLab client not configured")

        logger.info(f"Reviewing GitLab MR: {project}!{mr_iid}")

        # Fetch MR data
        mr_data = await self._gitlab.get_mr_diff(project, mr_iid)

        # Build PR info
        pr_info = PRInfo(
            number=mr_iid,
            title=mr_data.get("title", ""),
            description=mr_data.get("description"),
            author=mr_data.get("author", {}).get("username", ""),
            base_branch=mr_data.get("target_branch", ""),
            head_branch=mr_data.get("source_branch", ""),
            repository=project,
            url=mr_data.get("web_url", ""),
        )

        # Convert GitLab changes format to GitHub-like format
        files = self._convert_gitlab_changes(mr_data.get("changes", []))

        # Generate review
        review = await self._review_pr(pr_info, files, context)

        # Post review if requested
        if post_review:
            await self._post_gitlab_review(project, mr_iid, review)

        return review

    async def handle_webhook(
        self,
        provider: str,
        event_type: str,
        payload: dict[str, Any],
        signature: str | None = None,
    ) -> CodeReview | None:
        """Handle incoming webhook from GitHub or GitLab.

        Args:
            provider: 'github' or 'gitlab'
            event_type: Event type header
            payload: Webhook payload
            signature: Webhook signature/token

        Returns:
            Generated review if applicable, None otherwise
        """
        if provider == "github":
            event = self._webhook_handler.parse_github_webhook(event_type, payload, signature)
        elif provider == "gitlab":
            event = self._webhook_handler.parse_gitlab_webhook(payload, signature)
        else:
            raise ValueError(f"Unknown provider: {provider}")

        # Check if we should process this event
        if not self._webhook_handler.should_process_event(event):
            logger.debug(f"Skipping event: {event.event_type}.{event.action}")
            return None

        logger.info(f"Processing webhook event: {event.event_type}.{event.action}")

        # Extract PR info and review
        if provider == "github":
            pr_info = self._webhook_handler.extract_pr_info_github(payload)
            if pr_info:
                parts = pr_info.repository.split("/")
                if len(parts) == 2:
                    return await self.review_github_pr(parts[0], parts[1], pr_info.number)
        else:
            pr_info = self._webhook_handler.extract_pr_info_gitlab(payload)
            if pr_info:
                return await self.review_gitlab_mr(pr_info.repository, pr_info.number)

        return None

    async def _review_pr(
        self,
        pr_info: PRInfo,
        files: list[dict[str, Any]],
        context: dict[str, Any] | None = None,
    ) -> CodeReview:
        """Internal method to generate a review.

        Args:
            pr_info: Pull request information
            files: List of file changes
            context: Additional context

        Returns:
            Generated code review
        """
        # Check if we should review based on config
        if not self._should_review(files):
            logger.info(f"Skipping review for PR #{pr_info.number} based on config")
            return CodeReview(
                pr_number=pr_info.number,
                repository=pr_info.repository,
                summary="Review skipped based on configuration",
                overall_quality=10.0,
                approval_recommendation="comment",
            )

        # Build diff content from patches
        diff_content = self._build_diff_content(files)

        # Analyze the diff
        analysis = self._analyzer.analyze_diff(pr_info, diff_content, files)

        # Detect code smells
        all_smells = []
        for file in analysis.files:
            hunks = analysis.hunks_by_file.get(file.filename, [])
            smells = self._smell_detector.detect_smells(file, hunks)
            all_smells.extend(smells)

        # Generate review
        review = await self._reviewer.generate_review(analysis, all_smells, context)

        logger.info(
            f"Review generated for PR #{pr_info.number}: "
            f"quality={review.overall_quality}, "
            f"comments={len(review.comments)}, "
            f"recommendation={review.approval_recommendation}"
        )

        return review

    def _should_review(self, files: list[dict[str, Any]]) -> bool:
        """Check if PR should be reviewed based on config."""
        if not self._config.enabled:
            return False

        file_count = len(files)

        if file_count < self._config.min_file_changes:
            return False

        if file_count > self._config.max_file_changes:
            logger.warning(f"PR has too many files ({file_count}), skipping detailed review")
            return False

        # Check if all files match ignore patterns
        import fnmatch

        reviewable_files = []
        for f in files:
            filename = f.get("filename", "")
            ignored = any(
                fnmatch.fnmatch(filename, pattern)
                for pattern in self._config.ignore_patterns
            )
            if not ignored:
                reviewable_files.append(f)

        return len(reviewable_files) > 0

    def _build_diff_content(self, files: list[dict[str, Any]]) -> str:
        """Build unified diff content from file patches."""
        parts = []
        for f in files:
            filename = f.get("filename", "")
            patch = f.get("patch", "")
            if patch:
                parts.append(f"diff --git a/{filename} b/{filename}")
                parts.append(patch)
        return "\n".join(parts)

    def _convert_gitlab_changes(self, changes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert GitLab changes format to GitHub-like format."""
        files = []
        for change in changes:
            files.append({
                "filename": change.get("new_path", change.get("old_path", "")),
                "previous_filename": change.get("old_path"),
                "status": self._map_gitlab_status(change),
                "additions": 0,  # GitLab doesn't provide this directly
                "deletions": 0,
                "patch": change.get("diff", ""),
            })
        return files

    def _map_gitlab_status(self, change: dict[str, Any]) -> str:
        """Map GitLab change status to GitHub-like status."""
        if change.get("new_file"):
            return "added"
        elif change.get("deleted_file"):
            return "removed"
        elif change.get("renamed_file"):
            return "renamed"
        else:
            return "modified"

    async def _post_github_review(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        review: CodeReview,
    ) -> None:
        """Post review to GitHub PR."""
        if not self._github:
            return

        # Build review body
        body = self._format_review_body(review)

        # Map recommendation to GitHub event
        event_map = {
            "approve": "APPROVE",
            "request_changes": "REQUEST_CHANGES",
            "comment": "COMMENT",
        }
        event = event_map.get(review.approval_recommendation, "COMMENT")

        # Build inline comments
        comments = []
        for comment in review.comments[:20]:  # GitHub limits inline comments
            comments.append({
                "path": comment.file,
                "line": comment.line,
                "body": self._format_comment(comment),
            })

        try:
            await self._github.post_review(
                owner, repo, pr_number,
                body=body,
                event=event,
                comments=comments if comments else None,
            )
            logger.info(f"Posted review to GitHub PR {owner}/{repo}#{pr_number}")
        except Exception as e:
            logger.error(f"Failed to post GitHub review: {e}")

    async def _post_gitlab_review(
        self,
        project: str,
        mr_iid: int,
        review: CodeReview,
    ) -> None:
        """Post review to GitLab MR."""
        if not self._gitlab:
            return

        # Build review body
        body = self._format_review_body(review)

        try:
            # Post main review as note
            await self._gitlab.post_note(project, mr_iid, body)

            # Post inline comments as discussions
            for comment in review.comments[:10]:  # Limit inline comments
                await self._gitlab.post_discussion(
                    project, mr_iid,
                    body=self._format_comment(comment),
                    position={
                        "position_type": "text",
                        "new_path": comment.file,
                        "new_line": comment.line,
                    },
                )

            logger.info(f"Posted review to GitLab MR {project}!{mr_iid}")
        except Exception as e:
            logger.error(f"Failed to post GitLab review: {e}")

    def _format_review_body(self, review: CodeReview) -> str:
        """Format review body for posting."""
        lines = [
            "## 🤖 Automated Code Review",
            "",
            f"**Overall Quality:** {review.overall_quality}/10",
            f"**Recommendation:** {review.approval_recommendation.replace('_', ' ').title()}",
            "",
            "### Summary",
            review.summary,
            "",
        ]

        # Add metrics
        if review.metrics:
            lines.append("### Metrics")
            lines.append(f"- Files reviewed: {review.metrics.get('files_reviewed', 0)}")
            lines.append(f"- Total changes: {review.metrics.get('total_changes', 0)}")
            lines.append(f"- Complexity score: {review.metrics.get('complexity_score', 0)}/10")
            lines.append(f"- Risk score: {review.metrics.get('risk_score', 0)}/10")
            lines.append("")

        # Add issue summary
        if review.smells:
            critical = len([s for s in review.smells if s.severity.value == "critical"])
            major = len([s for s in review.smells if s.severity.value == "major"])
            if critical or major:
                lines.append("### Issues Found")
                if critical:
                    lines.append(f"- 🔴 Critical: {critical}")
                if major:
                    lines.append(f"- 🟠 Major: {major}")
                lines.append("")

        lines.append("---")
        lines.append("*Generated by NexusAI Code Review*")

        return "\n".join(lines)

    def _format_comment(self, comment) -> str:
        """Format a single comment for posting."""
        priority_emoji = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🔵",
            "info": "ℹ️",
        }

        emoji = priority_emoji.get(comment.priority.value, "💡")
        lines = [f"{emoji} **{comment.category.value.title()}**: {comment.body}"]

        if comment.suggestion:
            lines.append(f"\n💡 Suggestion: {comment.suggestion}")

        if comment.code_suggestion:
            lines.append(f"\n```suggestion\n{comment.code_suggestion}\n```")

        return "\n".join(lines)


# Factory function
def get_code_review_service(
    llm_gateway: Any | None = None,
    github_token: str | None = None,
    gitlab_token: str | None = None,
) -> CodeReviewService:
    """Create a code review service instance.

    Args:
        llm_gateway: LLM gateway service
        github_token: GitHub API token
        gitlab_token: GitLab API token

    Returns:
        Configured CodeReviewService
    """
    from app.core.config import settings

    return CodeReviewService(
        llm_gateway=llm_gateway,
        github_token=github_token or getattr(settings, "GITHUB_TOKEN", None),
        gitlab_token=gitlab_token or getattr(settings, "GITLAB_TOKEN", None),
    )
