"""GitHub connector for syncing data from GitHub."""

import hashlib
import hmac
from datetime import UTC, datetime
from typing import Any

import httpx
import structlog

from app.services.connectors.base import (
    BaseConnector,
    ConnectorConfig,
    ConnectorStatus,
    DEFAULT_HTTP_TIMEOUT,
    SyncResult,
)

logger = structlog.get_logger()


class GitHubConnector(BaseConnector):
    """Connector for GitHub API and webhooks."""

    API_BASE_URL = "https://api.github.com"
    WEBHOOK_EVENTS = [
        "push",
        "pull_request",
        "pull_request_review",
        "check_run",
        "workflow_run",
        "deployment",
        "deployment_status",
        "issues",
        "issue_comment",
        "release",
    ]

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._client: httpx.AsyncClient | None = None

    @property
    def source(self) -> str:
        return "github"

    @property
    def api_url(self) -> str:
        return self.config.endpoint or self.API_BASE_URL

    @property
    def token(self) -> str | None:
        if self.config.oauth_access_token:
            return self.config.oauth_access_token
        return self.config.credentials.get("token")

    async def connect(self) -> bool:
        """Connect to GitHub API."""
        if self._client:
            return True

        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        self._client = httpx.AsyncClient(
            base_url=self.api_url,
            headers=headers,
            timeout=DEFAULT_HTTP_TIMEOUT,
        )

        # Test connection
        success, message = await self.test_connection()
        if success:
            self.update_status(ConnectorStatus.ACTIVE, message)
        else:
            self.update_status(ConnectorStatus.ERROR, message)

        return success

    async def disconnect(self) -> None:
        """Close GitHub API client."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self.update_status(ConnectorStatus.DISCONNECTED)

    async def test_connection(self) -> tuple[bool, str]:
        """Test GitHub API connection."""
        try:
            await self.ensure_connected()
            response = await self._client.get("/user")

            if response.status_code == 200:
                user = response.json()
                return True, f"Connected as {user.get('login')}"
            elif response.status_code == 401:
                return False, "Authentication failed"
            else:
                return False, f"API error: {response.status_code}"

        except Exception as e:
            logger.error("GitHub connection test failed", error=str(e))
            return False, "Connection failed. Please check your credentials and try again."

    async def sync(
        self,
        full_sync: bool = False,
        since: datetime | None = None,
    ) -> SyncResult:
        """Sync data from GitHub."""
        result = SyncResult(
            success=False,
            connector_id=self.connector_id,
            source=self.source,
        )

        try:
            await self.ensure_connected()

            # Get list of repositories to sync
            repos = await self._get_repositories()
            result.events_fetched = 0

            for repo in repos:
                # Sync commits
                commits = await self._sync_commits(repo, since)
                result.events_fetched += len(commits)

                # Sync pull requests
                prs = await self._sync_pull_requests(repo, since)
                result.events_fetched += len(prs)

                # Sync workflow runs
                workflows = await self._sync_workflows(repo, since)
                result.events_fetched += len(workflows)

            result.success = True
            result.completed_at = datetime.now(UTC)
            result.duration_seconds = (
                result.completed_at - result.started_at
            ).total_seconds()

            self.config.last_sync_at = datetime.now(UTC)
            self.update_status(ConnectorStatus.ACTIVE, f"Synced {result.events_fetched} events")

        except Exception as e:
            result.error_message = "Sync failed. Please try again later."
            logger.error("GitHub sync failed", error=str(e))
            self.update_status(ConnectorStatus.ERROR, "Sync failed")

        return result

    async def sync_entity(
        self,
        entity_type: str,
        entity_id: str,
    ) -> SyncResult:
        """Sync a specific GitHub entity."""
        result = SyncResult(
            success=False,
            connector_id=self.connector_id,
            source=self.source,
        )

        try:
            await self.ensure_connected()

            if entity_type == "repository":
                data = await self._get_repository(entity_id)
                result.events_fetched = 1 if data else 0

            elif entity_type == "pull_request":
                # entity_id format: owner/repo/number
                parts = entity_id.split("/")
                if len(parts) >= 3:
                    owner, repo = parts[0], parts[1]
                    number = parts[2]
                    data = await self._get_pull_request(f"{owner}/{repo}", int(number))
                    result.events_fetched = 1 if data else 0

            result.success = True
            result.completed_at = datetime.now(UTC)

        except Exception as e:
            result.error_message = "Entity sync failed. Please try again later."
            logger.error("GitHub entity sync failed", error=str(e))

        return result

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        headers: dict[str, str],
    ) -> bool:
        """Verify GitHub webhook signature."""
        secret = self.config.credentials.get("webhook_secret")
        if not secret:
            # No secret configured - allow in dev
            return True

        if not signature or not signature.startswith("sha256="):
            return False

        expected_sig = signature[7:]
        computed = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(computed, expected_sig)

    async def setup_webhooks(
        self,
        webhook_url: str,
        events: list[str] | None = None,
    ) -> dict[str, Any]:
        """Set up GitHub webhooks."""
        await self.ensure_connected()

        events = events or self.WEBHOOK_EVENTS

        # Get repositories to configure webhooks for
        repos = await self._get_repositories()
        configured = []
        errors = []

        for repo in repos:
            try:
                response = await self._client.post(
                    f"/repos/{repo['full_name']}/hooks",
                    json={
                        "name": "web",
                        "active": True,
                        "events": events,
                        "config": {
                            "url": webhook_url,
                            "content_type": "json",
                            "secret": self.config.credentials.get("webhook_secret", ""),
                            "insecure_ssl": "0",
                        },
                    },
                )

                if response.status_code in (200, 201):
                    configured.append(repo["full_name"])
                else:
                    errors.append({
                        "repo": repo["full_name"],
                        "error": response.text,
                    })

            except Exception as e:
                errors.append({
                    "repo": repo["full_name"],
                    "error": str(e),
                })

        return {
            "configured": configured,
            "errors": errors,
            "events": events,
        }

    # Private methods for API calls

    async def _get_repositories(self) -> list[dict[str, Any]]:
        """Get list of repositories."""
        repos = []
        page = 1

        while True:
            response = await self._client.get(
                "/user/repos",
                params={
                    "per_page": 100,
                    "page": page,
                    "sort": "updated",
                },
            )
            self._update_rate_limit_from_response(response)

            if response.status_code != 200:
                break

            data = response.json()
            if not data:
                break

            repos.extend(data)
            page += 1

            if len(data) < 100:
                break

        return repos

    async def _get_repository(self, full_name: str) -> dict[str, Any] | None:
        """Get repository details."""
        response = await self._client.get(f"/repos/{full_name}")
        self._update_rate_limit_from_response(response)

        if response.status_code == 200:
            return response.json()
        return None

    async def _sync_commits(
        self,
        repo: dict[str, Any],
        since: datetime | None,
    ) -> list[dict[str, Any]]:
        """Sync commits for a repository."""
        commits = []
        params: dict[str, Any] = {"per_page": 100}

        if since:
            params["since"] = since.isoformat()

        response = await self._client.get(
            f"/repos/{repo['full_name']}/commits",
            params=params,
        )
        self._update_rate_limit_from_response(response)

        if response.status_code == 200:
            commits = response.json()

        return commits

    async def _sync_pull_requests(
        self,
        repo: dict[str, Any],
        since: datetime | None,
    ) -> list[dict[str, Any]]:
        """Sync pull requests for a repository."""
        prs = []
        params: dict[str, Any] = {
            "per_page": 100,
            "state": "all",
            "sort": "updated",
            "direction": "desc",
        }

        response = await self._client.get(
            f"/repos/{repo['full_name']}/pulls",
            params=params,
        )
        self._update_rate_limit_from_response(response)

        if response.status_code == 200:
            all_prs = response.json()

            # Filter by since if provided
            if since:
                for pr in all_prs:
                    updated_at = datetime.fromisoformat(
                        pr["updated_at"].replace("Z", "+00:00")
                    )
                    if updated_at >= since:
                        prs.append(pr)
            else:
                prs = all_prs

        return prs

    async def _get_pull_request(
        self,
        repo_full_name: str,
        number: int,
    ) -> dict[str, Any] | None:
        """Get pull request details."""
        response = await self._client.get(
            f"/repos/{repo_full_name}/pulls/{number}"
        )
        self._update_rate_limit_from_response(response)

        if response.status_code == 200:
            return response.json()
        return None

    async def _sync_workflows(
        self,
        repo: dict[str, Any],
        since: datetime | None,
    ) -> list[dict[str, Any]]:
        """Sync workflow runs for a repository."""
        runs = []
        params: dict[str, Any] = {"per_page": 100}

        response = await self._client.get(
            f"/repos/{repo['full_name']}/actions/runs",
            params=params,
        )
        self._update_rate_limit_from_response(response)

        if response.status_code == 200:
            data = response.json()
            all_runs = data.get("workflow_runs", [])

            # Filter by since if provided
            if since:
                for run in all_runs:
                    updated_at = datetime.fromisoformat(
                        run["updated_at"].replace("Z", "+00:00")
                    )
                    if updated_at >= since:
                        runs.append(run)
            else:
                runs = all_runs

        return runs

    def _update_rate_limit_from_response(self, response: httpx.Response) -> None:
        """Update rate limit from API response headers."""
        remaining = response.headers.get("x-ratelimit-remaining")
        reset = response.headers.get("x-ratelimit-reset")

        if remaining is not None:
            try:
                remaining_int = int(remaining)
                reset_dt = None
                if reset:
                    reset_dt = datetime.fromtimestamp(int(reset), tz=UTC)
                self.update_rate_limit(remaining_int, reset_dt)
            except ValueError:
                pass
