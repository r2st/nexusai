"""GitLab connector for syncing data from GitLab."""

import hmac
from datetime import UTC, datetime
from typing import Any

import httpx
import structlog

from app.services.connectors.base import (
    BaseConnector,
    ConnectorConfig,
    ConnectorStatus,
    SyncResult,
)

logger = structlog.get_logger()


class GitLabConnector(BaseConnector):
    """Connector for GitLab API and webhooks."""

    API_BASE_URL = "https://gitlab.com/api/v4"
    WEBHOOK_EVENTS = [
        "push_events",
        "tag_push_events",
        "merge_requests_events",
        "pipeline_events",
        "job_events",
        "deployment_events",
        "issues_events",
        "note_events",
        "releases_events",
    ]

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._client: httpx.AsyncClient | None = None

    @property
    def source(self) -> str:
        return "gitlab"

    @property
    def api_url(self) -> str:
        return self.config.endpoint or self.API_BASE_URL

    @property
    def token(self) -> str | None:
        if self.config.oauth_access_token:
            return self.config.oauth_access_token
        return self.config.credentials.get("token")

    async def connect(self) -> bool:
        """Connect to GitLab API."""
        if self._client:
            return True

        headers = {"Accept": "application/json"}

        if self.token:
            headers["PRIVATE-TOKEN"] = self.token

        self._client = httpx.AsyncClient(
            base_url=self.api_url,
            headers=headers,
            timeout=30.0,
        )

        # Test connection
        success, message = await self.test_connection()
        if success:
            self.update_status(ConnectorStatus.ACTIVE, message)
        else:
            self.update_status(ConnectorStatus.ERROR, message)

        return success

    async def disconnect(self) -> None:
        """Close GitLab API client."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self.update_status(ConnectorStatus.DISCONNECTED)

    async def test_connection(self) -> tuple[bool, str]:
        """Test GitLab API connection."""
        try:
            await self.ensure_connected()
            response = await self._client.get("/user")

            if response.status_code == 200:
                user = response.json()
                return True, f"Connected as {user.get('username')}"
            elif response.status_code == 401:
                return False, "Authentication failed"
            else:
                return False, f"API error: {response.status_code}"

        except Exception as e:
            return False, f"Connection error: {str(e)}"

    async def sync(
        self,
        full_sync: bool = False,
        since: datetime | None = None,
    ) -> SyncResult:
        """Sync data from GitLab."""
        result = SyncResult(
            success=False,
            connector_id=self.connector_id,
            source=self.source,
        )

        try:
            await self.ensure_connected()

            # Get list of projects to sync
            projects = await self._get_projects()
            result.events_fetched = 0

            for project in projects:
                # Sync commits
                commits = await self._sync_commits(project, since)
                result.events_fetched += len(commits)

                # Sync merge requests
                mrs = await self._sync_merge_requests(project, since)
                result.events_fetched += len(mrs)

                # Sync pipelines
                pipelines = await self._sync_pipelines(project, since)
                result.events_fetched += len(pipelines)

            result.success = True
            result.completed_at = datetime.now(UTC)
            result.duration_seconds = (
                result.completed_at - result.started_at
            ).total_seconds()

            self.config.last_sync_at = datetime.now(UTC)
            self.update_status(ConnectorStatus.ACTIVE, f"Synced {result.events_fetched} events")

        except Exception as e:
            result.error_message = str(e)
            logger.error("GitLab sync failed", error=str(e))
            self.update_status(ConnectorStatus.ERROR, str(e))

        return result

    async def sync_entity(
        self,
        entity_type: str,
        entity_id: str,
    ) -> SyncResult:
        """Sync a specific GitLab entity."""
        result = SyncResult(
            success=False,
            connector_id=self.connector_id,
            source=self.source,
        )

        try:
            await self.ensure_connected()

            if entity_type == "project":
                data = await self._get_project(entity_id)
                result.events_fetched = 1 if data else 0

            elif entity_type == "merge_request":
                # entity_id format: project_id/mr_iid
                parts = entity_id.split("/")
                if len(parts) >= 2:
                    project_id = parts[0]
                    mr_iid = parts[1]
                    data = await self._get_merge_request(project_id, int(mr_iid))
                    result.events_fetched = 1 if data else 0

            result.success = True
            result.completed_at = datetime.now(UTC)

        except Exception as e:
            result.error_message = str(e)
            logger.error("GitLab entity sync failed", error=str(e))

        return result

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        headers: dict[str, str],
    ) -> bool:
        """Verify GitLab webhook token."""
        secret = self.config.credentials.get("webhook_secret")
        if not secret:
            return True

        token = headers.get("x-gitlab-token", "")
        return hmac.compare_digest(token, secret)

    async def setup_webhooks(
        self,
        webhook_url: str,
        events: list[str] | None = None,
    ) -> dict[str, Any]:
        """Set up GitLab webhooks."""
        await self.ensure_connected()

        # Get projects to configure webhooks for
        projects = await self._get_projects()
        configured = []
        errors = []

        # Build event flags
        event_flags = {}
        for event in (events or self.WEBHOOK_EVENTS):
            event_flags[event] = True

        for project in projects:
            try:
                response = await self._client.post(
                    f"/projects/{project['id']}/hooks",
                    json={
                        "url": webhook_url,
                        "token": self.config.credentials.get("webhook_secret", ""),
                        "enable_ssl_verification": True,
                        **event_flags,
                    },
                )

                if response.status_code in (200, 201):
                    configured.append(project["path_with_namespace"])
                else:
                    errors.append({
                        "project": project["path_with_namespace"],
                        "error": response.text,
                    })

            except Exception as e:
                errors.append({
                    "project": project["path_with_namespace"],
                    "error": str(e),
                })

        return {
            "configured": configured,
            "errors": errors,
            "events": list(event_flags.keys()),
        }

    # Private methods for API calls

    async def _get_projects(self) -> list[dict[str, Any]]:
        """Get list of projects."""
        projects = []
        page = 1

        while True:
            response = await self._client.get(
                "/projects",
                params={
                    "per_page": 100,
                    "page": page,
                    "membership": True,
                    "order_by": "last_activity_at",
                },
            )
            self._update_rate_limit_from_response(response)

            if response.status_code != 200:
                break

            data = response.json()
            if not data:
                break

            projects.extend(data)
            page += 1

            if len(data) < 100:
                break

        return projects

    async def _get_project(self, project_id: str) -> dict[str, Any] | None:
        """Get project details."""
        response = await self._client.get(f"/projects/{project_id}")
        self._update_rate_limit_from_response(response)

        if response.status_code == 200:
            return response.json()
        return None

    async def _sync_commits(
        self,
        project: dict[str, Any],
        since: datetime | None,
    ) -> list[dict[str, Any]]:
        """Sync commits for a project."""
        commits = []
        params: dict[str, Any] = {"per_page": 100}

        if since:
            params["since"] = since.isoformat()

        response = await self._client.get(
            f"/projects/{project['id']}/repository/commits",
            params=params,
        )
        self._update_rate_limit_from_response(response)

        if response.status_code == 200:
            commits = response.json()

        return commits

    async def _sync_merge_requests(
        self,
        project: dict[str, Any],
        since: datetime | None,
    ) -> list[dict[str, Any]]:
        """Sync merge requests for a project."""
        mrs = []
        params: dict[str, Any] = {
            "per_page": 100,
            "state": "all",
            "order_by": "updated_at",
            "sort": "desc",
        }

        if since:
            params["updated_after"] = since.isoformat()

        response = await self._client.get(
            f"/projects/{project['id']}/merge_requests",
            params=params,
        )
        self._update_rate_limit_from_response(response)

        if response.status_code == 200:
            mrs = response.json()

        return mrs

    async def _get_merge_request(
        self,
        project_id: str,
        mr_iid: int,
    ) -> dict[str, Any] | None:
        """Get merge request details."""
        response = await self._client.get(
            f"/projects/{project_id}/merge_requests/{mr_iid}"
        )
        self._update_rate_limit_from_response(response)

        if response.status_code == 200:
            return response.json()
        return None

    async def _sync_pipelines(
        self,
        project: dict[str, Any],
        since: datetime | None,
    ) -> list[dict[str, Any]]:
        """Sync pipelines for a project."""
        pipelines = []
        params: dict[str, Any] = {
            "per_page": 100,
            "order_by": "updated_at",
            "sort": "desc",
        }

        if since:
            params["updated_after"] = since.isoformat()

        response = await self._client.get(
            f"/projects/{project['id']}/pipelines",
            params=params,
        )
        self._update_rate_limit_from_response(response)

        if response.status_code == 200:
            pipelines = response.json()

        return pipelines

    def _update_rate_limit_from_response(self, response: httpx.Response) -> None:
        """Update rate limit from API response headers."""
        remaining = response.headers.get("ratelimit-remaining")
        reset = response.headers.get("ratelimit-reset")

        if remaining is not None:
            try:
                remaining_int = int(remaining)
                reset_dt = None
                if reset:
                    reset_dt = datetime.fromtimestamp(int(reset), tz=UTC)
                self.update_rate_limit(remaining_int, reset_dt)
            except ValueError:
                pass
