"""Webhook Handler - GitHub/GitLab webhook integration."""

import hashlib
import hmac
import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.services.code_review.models import PRInfo, WebhookEvent


class WebhookConfig(BaseModel):
    """Webhook configuration."""

    github_secret: str | None = None
    gitlab_secret: str | None = None
    enabled_events: list[str] = Field(default_factory=lambda: [
        "pull_request.opened",
        "pull_request.synchronize",
        "pull_request.reopened",
        "merge_request.open",
        "merge_request.update",
        "merge_request.reopen",
    ])
    auto_review: bool = True


class WebhookHandler:
    """Handles webhooks from GitHub and GitLab."""

    def __init__(self, config: WebhookConfig | None = None):
        """Initialize webhook handler.

        Args:
            config: Webhook configuration
        """
        self._config = config or WebhookConfig()

    def verify_github_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        """Verify GitHub webhook signature.

        Args:
            payload: Raw request body
            signature: X-Hub-Signature-256 header value

        Returns:
            True if signature is valid
        """
        if not self._config.github_secret:
            return True  # No secret configured, skip verification

        if not signature or not signature.startswith("sha256="):
            return False

        expected = "sha256=" + hmac.new(
            self._config.github_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    def verify_gitlab_token(self, token: str) -> bool:
        """Verify GitLab webhook token.

        Args:
            token: X-Gitlab-Token header value

        Returns:
            True if token is valid
        """
        if not self._config.gitlab_secret:
            return True  # No secret configured, skip verification

        return hmac.compare_digest(self._config.gitlab_secret, token)

    def parse_github_webhook(
        self,
        event_type: str,
        payload: dict[str, Any],
        signature: str | None = None,
    ) -> WebhookEvent:
        """Parse a GitHub webhook event.

        Args:
            event_type: X-GitHub-Event header value
            payload: Parsed JSON payload
            signature: Optional signature for verification

        Returns:
            Parsed webhook event
        """
        action = payload.get("action")

        return WebhookEvent(
            event_type=event_type,
            action=action,
            repository=payload.get("repository", {}).get("full_name", ""),
            sender=payload.get("sender", {}).get("login", ""),
            payload=payload,
            signature=signature,
        )

    def parse_gitlab_webhook(
        self,
        payload: dict[str, Any],
        token: str | None = None,
    ) -> WebhookEvent:
        """Parse a GitLab webhook event.

        Args:
            payload: Parsed JSON payload
            token: Optional token for verification

        Returns:
            Parsed webhook event
        """
        object_kind = payload.get("object_kind", "")
        action = payload.get("object_attributes", {}).get("action")

        return WebhookEvent(
            event_type=object_kind,
            action=action,
            repository=payload.get("project", {}).get("path_with_namespace", ""),
            sender=payload.get("user", {}).get("username", ""),
            payload=payload,
            signature=token,
        )

    def should_process_event(self, event: WebhookEvent) -> bool:
        """Check if event should be processed for review.

        Args:
            event: Webhook event

        Returns:
            True if event should trigger a review
        """
        if not self._config.auto_review:
            return False

        event_key = f"{event.event_type}.{event.action}" if event.action else event.event_type

        return event_key in self._config.enabled_events

    def extract_pr_info_github(self, payload: dict[str, Any]) -> PRInfo | None:
        """Extract PR info from GitHub webhook payload.

        Args:
            payload: GitHub webhook payload

        Returns:
            PRInfo if available
        """
        pr = payload.get("pull_request")
        if not pr:
            return None

        repo = payload.get("repository", {})

        return PRInfo(
            number=pr.get("number", 0),
            title=pr.get("title", ""),
            description=pr.get("body"),
            author=pr.get("user", {}).get("login", ""),
            base_branch=pr.get("base", {}).get("ref", ""),
            head_branch=pr.get("head", {}).get("ref", ""),
            repository=repo.get("full_name", ""),
            url=pr.get("html_url", ""),
            created_at=self._parse_datetime(pr.get("created_at")),
            updated_at=self._parse_datetime(pr.get("updated_at")),
            labels=[l.get("name", "") for l in pr.get("labels", [])],
            files_changed=pr.get("changed_files", 0),
            additions=pr.get("additions", 0),
            deletions=pr.get("deletions", 0),
        )

    def extract_pr_info_gitlab(self, payload: dict[str, Any]) -> PRInfo | None:
        """Extract PR (merge request) info from GitLab webhook payload.

        Args:
            payload: GitLab webhook payload

        Returns:
            PRInfo if available
        """
        mr = payload.get("object_attributes")
        if not mr:
            return None

        project = payload.get("project", {})

        return PRInfo(
            number=mr.get("iid", 0),
            title=mr.get("title", ""),
            description=mr.get("description"),
            author=payload.get("user", {}).get("username", ""),
            base_branch=mr.get("target_branch", ""),
            head_branch=mr.get("source_branch", ""),
            repository=project.get("path_with_namespace", ""),
            url=mr.get("url", ""),
            created_at=self._parse_datetime(mr.get("created_at")),
            updated_at=self._parse_datetime(mr.get("updated_at")),
            labels=[l.get("title", "") for l in payload.get("labels", [])],
        )

    def _parse_datetime(self, dt_str: str | None) -> datetime | None:
        """Parse ISO datetime string."""
        if not dt_str:
            return None
        try:
            # Handle GitHub format
            if dt_str.endswith("Z"):
                dt_str = dt_str[:-1] + "+00:00"
            return datetime.fromisoformat(dt_str)
        except ValueError:
            return None

    def get_diff_url_github(self, pr_info: PRInfo) -> str:
        """Get URL to fetch PR diff from GitHub.

        Args:
            pr_info: Pull request info

        Returns:
            API URL for diff
        """
        return f"https://api.github.com/repos/{pr_info.repository}/pulls/{pr_info.number}"

    def get_diff_url_gitlab(self, pr_info: PRInfo) -> str:
        """Get URL to fetch MR diff from GitLab.

        Args:
            pr_info: Pull request info

        Returns:
            API URL for diff
        """
        # GitLab uses project ID or URL-encoded path
        project_path = pr_info.repository.replace("/", "%2F")
        return f"https://gitlab.com/api/v4/projects/{project_path}/merge_requests/{pr_info.number}/changes"


class GitHubClient:
    """Client for GitHub API interactions."""

    def __init__(self, token: str | None = None):
        """Initialize GitHub client.

        Args:
            token: GitHub personal access token or app token
        """
        self._token = token
        self._base_url = "https://api.github.com"

    def _get_headers(self) -> dict[str, str]:
        """Get API headers."""
        headers = {
            "Accept": "application/vnd.github.v3+json",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def get_pr_diff(
        self,
        owner: str,
        repo: str,
        pr_number: int,
    ) -> dict[str, Any]:
        """Get PR diff from GitHub.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number

        Returns:
            PR data with diff
        """
        import httpx

        url = f"{self._base_url}/repos/{owner}/{repo}/pulls/{pr_number}"

        async with httpx.AsyncClient() as client:
            # Get PR info
            response = await client.get(url, headers=self._get_headers())
            response.raise_for_status()
            pr_data = response.json()

            # Get files
            files_response = await client.get(
                f"{url}/files",
                headers=self._get_headers(),
            )
            files_response.raise_for_status()
            pr_data["files"] = files_response.json()

        return pr_data

    async def post_review(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        body: str,
        event: str = "COMMENT",
        comments: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Post a review to a PR.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            body: Review body
            event: APPROVE, REQUEST_CHANGES, or COMMENT
            comments: Line comments

        Returns:
            Created review data
        """
        import httpx

        url = f"{self._base_url}/repos/{owner}/{repo}/pulls/{pr_number}/reviews"

        data = {
            "body": body,
            "event": event,
        }
        if comments:
            data["comments"] = comments

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=self._get_headers(),
                json=data,
            )
            response.raise_for_status()
            return response.json()


class GitLabClient:
    """Client for GitLab API interactions."""

    def __init__(self, token: str | None = None, base_url: str = "https://gitlab.com"):
        """Initialize GitLab client.

        Args:
            token: GitLab personal access token
            base_url: GitLab instance URL
        """
        self._token = token
        self._base_url = base_url.rstrip("/")

    def _get_headers(self) -> dict[str, str]:
        """Get API headers."""
        headers = {
            "Accept": "application/json",
        }
        if self._token:
            headers["PRIVATE-TOKEN"] = self._token
        return headers

    async def get_mr_diff(
        self,
        project_id: str | int,
        mr_iid: int,
    ) -> dict[str, Any]:
        """Get MR diff from GitLab.

        Args:
            project_id: Project ID or URL-encoded path
            mr_iid: Merge request IID

        Returns:
            MR data with changes
        """
        import httpx

        if isinstance(project_id, str):
            project_id = project_id.replace("/", "%2F")

        url = f"{self._base_url}/api/v4/projects/{project_id}/merge_requests/{mr_iid}"

        async with httpx.AsyncClient() as client:
            # Get MR info
            response = await client.get(url, headers=self._get_headers())
            response.raise_for_status()
            mr_data = response.json()

            # Get changes
            changes_response = await client.get(
                f"{url}/changes",
                headers=self._get_headers(),
            )
            changes_response.raise_for_status()
            changes_data = changes_response.json()
            mr_data["changes"] = changes_data.get("changes", [])

        return mr_data

    async def post_note(
        self,
        project_id: str | int,
        mr_iid: int,
        body: str,
    ) -> dict[str, Any]:
        """Post a note (comment) to an MR.

        Args:
            project_id: Project ID or URL-encoded path
            mr_iid: Merge request IID
            body: Note body

        Returns:
            Created note data
        """
        import httpx

        if isinstance(project_id, str):
            project_id = project_id.replace("/", "%2F")

        url = f"{self._base_url}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/notes"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=self._get_headers(),
                json={"body": body},
            )
            response.raise_for_status()
            return response.json()

    async def post_discussion(
        self,
        project_id: str | int,
        mr_iid: int,
        body: str,
        position: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Post a discussion (inline comment) to an MR.

        Args:
            project_id: Project ID or URL-encoded path
            mr_iid: Merge request IID
            body: Discussion body
            position: Line position for inline comment

        Returns:
            Created discussion data
        """
        import httpx

        if isinstance(project_id, str):
            project_id = project_id.replace("/", "%2F")

        url = f"{self._base_url}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/discussions"

        data = {"body": body}
        if position:
            data["position"] = position

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=self._get_headers(),
                json=data,
            )
            response.raise_for_status()
            return response.json()
