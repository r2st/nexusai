"""DevLake API Service.

Client for interacting with Apache DevLake REST API.
Provides methods for managing projects, connections, pipelines, and DORA metrics.
"""

from typing import Any
import logging

import httpx
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)


class DORAMetrics(BaseModel):
    """DORA metrics model.

    DevOps Research and Assessment metrics for measuring software delivery performance.
    """

    # Deployment Frequency - How often code is deployed to production
    deployment_frequency: float = Field(
        default=0.0,
        description="Average number of deployments per day",
    )
    deployment_frequency_rating: str = Field(
        default="unknown",
        description="Rating: elite (daily+), high (weekly), medium (monthly), low (yearly+)",
    )

    # Lead Time for Changes - Time from commit to production
    lead_time_for_changes_hours: float = Field(
        default=0.0,
        description="Average hours from commit to production deployment",
    )
    lead_time_rating: str = Field(
        default="unknown",
        description="Rating: elite (<1hr), high (<1day), medium (<1week), low (>1week)",
    )

    # Mean Time to Recovery - Time to restore service after incident
    mean_time_to_recovery_hours: float = Field(
        default=0.0,
        description="Average hours to recover from a failure",
    )
    mttr_rating: str = Field(
        default="unknown",
        description="Rating: elite (<1hr), high (<1day), medium (<1week), low (>1week)",
    )

    # Change Failure Rate - Percentage of deployments causing failures
    change_failure_rate: float = Field(
        default=0.0,
        description="Percentage of deployments that cause failures (0-100)",
    )
    cfr_rating: str = Field(
        default="unknown",
        description="Rating: elite (<15%), high (<30%), medium (<45%), low (>45%)",
    )

    # Overall performance level
    overall_rating: str = Field(
        default="unknown",
        description="Overall DORA performance rating",
    )

    # Time range for metrics
    time_range: str = Field(
        default="past_6_months",
        description="Time range for the metrics",
    )

    # Project info
    project_name: str = Field(
        default="",
        description="Name of the project",
    )


class DevLakeService:
    """Service for interacting with DevLake API."""

    def __init__(self) -> None:
        """Initialize DevLake service."""
        base = settings.DEVLAKE_API_URL
        # DevLake API endpoints are at the root URL, NOT under /api
        # Health check: /ping, /health
        # Main API: /projects, /plugins/github/connections, /blueprints, /pipelines
        self.root_url = base.rstrip('/')
        # base_url is the same as root_url for DevLake v1.x API
        self.base_url = self.root_url
        self.timeout = 30.0
        logger.info(f"DevLakeService initialized with base_url: {self.base_url}")

    def _get_client(self) -> httpx.AsyncClient:
        """Get HTTP client for DevLake API."""
        logger.debug(f"Creating HTTP client for DevLake API at {self.base_url}")
        return httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={"Content-Type": "application/json"},
        )

    async def health_check(self) -> bool:
        """Check if DevLake is available.

        Note: The /ping endpoint is at the root URL, not under /api.
        """
        ping_url = f"{self.root_url}/ping"
        logger.info(f"Performing health check on DevLake at {ping_url}")
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.debug(f"Sending GET request to {ping_url}")
                response = await client.get(ping_url)
                logger.info(f"DevLake health check response: status={response.status_code}, body={response.text[:200] if response.text else 'empty'}")
                return response.status_code == 200
        except httpx.ConnectError as e:
            logger.error(f"DevLake connection error: {e}. Is DevLake running at {self.root_url}?")
            return False
        except httpx.TimeoutException as e:
            logger.error(f"DevLake timeout error: {e}")
            return False
        except Exception as e:
            logger.error(f"DevLake health check failed with unexpected error: {type(e).__name__}: {e}")
            return False

    # ======================
    # Projects
    # ======================

    async def list_projects(self) -> list[dict[str, Any]]:
        """List all DevLake projects."""
        async with self._get_client() as client:
            response = await client.get("/projects")
            response.raise_for_status()
            data = response.json()
            return data.get("projects", []) if isinstance(data, dict) else data

    async def get_project(self, project_name: str) -> dict[str, Any] | None:
        """Get a specific project by name."""
        async with self._get_client() as client:
            response = await client.get(f"/projects/{project_name}")
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()

    async def create_project(
        self,
        name: str,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Create a new project in DevLake."""
        async with self._get_client() as client:
            payload = {
                "name": name,
                "description": description or "",
            }
            response = await client.post("/projects", json=payload)

            # Try to parse response body for error details
            try:
                result = response.json()
            except Exception:
                result = None

            # DevLake may return 200 or 4xx with success=false for errors
            if isinstance(result, dict) and result.get("success") is False:
                error_msg = result.get("message", "Unknown error")
                if "already exists" in error_msg.lower():
                    raise ValueError(f"Project already exists: {error_msg}")
                raise ValueError(f"DevLake returned error: {error_msg}")

            # Now raise for HTTP errors if no DevLake-specific error was found
            response.raise_for_status()

            return result if result else response.json()

    # ======================
    # DORA Metrics
    # ======================

    async def get_dora_metrics(
        self,
        project_name: str,
        time_range: str = "past_6_months",
    ) -> DORAMetrics:
        """Get DORA metrics for a project.

        Args:
            project_name: Name of the project
            time_range: Time range (past_6_months, past_3_months, past_month, etc.)

        Returns:
            DORAMetrics with deployment frequency, lead time, MTTR, and CFR
        """
        try:
            async with self._get_client() as client:
                # DevLake DORA metrics endpoint
                response = await client.get(
                    f"/projects/{project_name}/dora",
                    params={"time_range": time_range},
                )
                response.raise_for_status()
                data = response.json()

                return DORAMetrics(
                    deployment_frequency=data.get("deployment_frequency", 0.0),
                    deployment_frequency_rating=self._rate_deployment_frequency(
                        data.get("deployment_frequency", 0.0)
                    ),
                    lead_time_for_changes_hours=data.get("lead_time_for_changes_hours", 0.0),
                    lead_time_rating=self._rate_lead_time(
                        data.get("lead_time_for_changes_hours", 0.0)
                    ),
                    mean_time_to_recovery_hours=data.get("mean_time_to_recovery_hours", 0.0),
                    mttr_rating=self._rate_mttr(
                        data.get("mean_time_to_recovery_hours", 0.0)
                    ),
                    change_failure_rate=data.get("change_failure_rate", 0.0),
                    cfr_rating=self._rate_cfr(data.get("change_failure_rate", 0.0)),
                    overall_rating=data.get("overall_rating", "unknown"),
                    time_range=time_range,
                    project_name=project_name,
                )
        except httpx.HTTPStatusError as e:
            logger.warning(f"DORA metrics API returned {e.response.status_code} for project {project_name}")
            # Fall back to calculating metrics from PR data
            return await self._calculate_dora_from_prs(project_name, time_range)
        except Exception as e:
            logger.error(f"Error fetching DORA metrics for {project_name}: {e}")
            # Fall back to calculating metrics from PR data
            return await self._calculate_dora_from_prs(project_name, time_range)

    async def _calculate_dora_from_prs(
        self,
        project_name: str,
        time_range: str = "past_6_months",
    ) -> DORAMetrics:
        """Calculate DORA metrics from Pull Request data as a fallback.

        Uses merged PRs as proxy for deployments when CI/CD deployment data
        is not available.

        Args:
            project_name: Name of the project
            time_range: Time range for metrics calculation

        Returns:
            DORAMetrics calculated from PR data
        """
        try:
            # Get project to find the associated GitHub repo
            project = await self.get_project(project_name)
            if not project:
                logger.warning(f"Project {project_name} not found for DORA calculation")
                return DORAMetrics(time_range=time_range, project_name=project_name)

            # Map time_range to days
            time_range_days = {
                "past_month": 30,
                "past_3_months": 90,
                "past_6_months": 180,
                "past_year": 365,
            }
            days = time_range_days.get(time_range, 180)

            # Query the DevLake database for PR metrics
            # We need to connect to the MySQL database
            metrics = await self._query_pr_metrics(project_name, days)

            if metrics:
                deployment_freq = metrics.get("deploys_per_day", 0.0)
                lead_time = metrics.get("avg_lead_time_hours", 0.0)

                # Determine overall rating based on deployment frequency and lead time
                df_rating = self._rate_deployment_frequency(deployment_freq)
                lt_rating = self._rate_lead_time(lead_time)

                # Overall rating is the lower of the two (most conservative)
                rating_order = ["low", "medium", "high", "elite"]
                overall_rating = rating_order[
                    min(rating_order.index(df_rating), rating_order.index(lt_rating))
                ]

                return DORAMetrics(
                    deployment_frequency=round(deployment_freq, 4),
                    deployment_frequency_rating=df_rating,
                    lead_time_for_changes_hours=round(lead_time, 1),
                    lead_time_rating=lt_rating,
                    mean_time_to_recovery_hours=0.0,  # Not calculable from PR data
                    mttr_rating="unknown",
                    change_failure_rate=0.0,  # Not calculable from PR data
                    cfr_rating="unknown",
                    overall_rating=overall_rating,
                    time_range=time_range,
                    project_name=project_name,
                )
        except Exception as e:
            logger.error(f"Error calculating DORA from PRs for {project_name}: {e}")

        return DORAMetrics(time_range=time_range, project_name=project_name)

    async def _query_pr_metrics(
        self,
        project_name: str,
        days: int,
    ) -> dict[str, float] | None:
        """Query PR metrics from DevLake MySQL database.

        Uses docker exec to query the MySQL container since the database
        may not be exposed to the host network.

        Args:
            project_name: Name of the project
            days: Number of days to look back

        Returns:
            Dict with deploys_per_day and avg_lead_time_hours, or None if error
        """
        import asyncio
        import json
        import os

        try:
            # Try to find GitHub repo ID from project scope
            github_id = None
            try:
                project = await self.get_project(project_name)
                blueprint = project.get("blueprint", {})
                connections = blueprint.get("connections", [])
                for conn in connections:
                    if conn.get("pluginName") == "github":
                        scopes = conn.get("scopes", [])
                        if scopes:
                            scope_id = scopes[0].get("scopeId")
                            if scope_id:
                                github_id = scope_id
                                break
            except Exception as e:
                logger.debug(f"Could not get project scopes: {e}")

            if not github_id:
                logger.warning(f"No GitHub repo ID found for project {project_name}")
                return None

            # Query via docker exec to the DevLake MySQL container
            mysql_container = os.getenv("DEVLAKE_MYSQL_CONTAINER", "nexusai-devlake-mysql")

            # Build the SQL query
            query = f"""
            SELECT
                COUNT(*) as merged_prs,
                ROUND(COUNT(*) / {days}, 4) as deploys_per_day,
                ROUND(AVG(hours_to_merge), 1) as avg_lead_time_hours
            FROM (
                SELECT
                    TIMESTAMPDIFF(HOUR, created_date, merged_date) as hours_to_merge
                FROM pull_requests
                WHERE base_repo_id LIKE '%{github_id}%'
                AND merged_date IS NOT NULL
                AND merged_date > DATE_SUB(NOW(), INTERVAL {days} DAY)
                AND TIMESTAMPDIFF(DAY, created_date, merged_date) < 30
            ) subq
            """

            # Execute via docker exec
            cmd = [
                "docker", "exec", mysql_container,
                "sh", "-c",
                f'mysql -uroot -p$MYSQL_ROOT_PASSWORD lake -N -e "{query}"'
            ]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                logger.warning(f"MySQL query failed: {stderr.decode()}")
                return None

            # Parse the result (tab-separated values)
            output = stdout.decode().strip()
            if not output:
                return None

            parts = output.split('\t')
            if len(parts) >= 3:
                merged_prs = int(parts[0]) if parts[0] and parts[0] != 'NULL' else 0
                deploys_per_day = float(parts[1]) if parts[1] and parts[1] != 'NULL' else 0.0
                avg_lead_time = float(parts[2]) if parts[2] and parts[2] != 'NULL' else 0.0

                if merged_prs > 0:
                    return {
                        "deploys_per_day": deploys_per_day,
                        "avg_lead_time_hours": avg_lead_time,
                        "merged_prs": merged_prs,
                    }

        except Exception as e:
            logger.error(f"Error querying DevLake MySQL for PR metrics: {e}")

        return None

    async def _query_weekly_pr_metrics(
        self,
        project_name: str,
        days: int,
    ) -> list[dict[str, Any]] | None:
        """Query weekly PR metrics from DevLake MySQL database for chart data.

        Returns a list of weekly data points with deployment frequency and lead time.

        Args:
            project_name: Name of the project
            days: Number of days to look back

        Returns:
            List of dicts with date, deploymentFrequency, leadTimeForChanges, or None
        """
        import asyncio
        import os

        try:
            # Find GitHub repo ID from project scope
            github_id = None
            try:
                project = await self.get_project(project_name)
                blueprint = project.get("blueprint", {})
                connections = blueprint.get("connections", [])
                for conn in connections:
                    if conn.get("pluginName") == "github":
                        scopes = conn.get("scopes", [])
                        if scopes:
                            scope_id = scopes[0].get("scopeId")
                            if scope_id:
                                github_id = scope_id
                                break
            except Exception as e:
                logger.debug(f"Could not get project scopes for chart data: {e}")

            if not github_id:
                return None

            mysql_container = os.getenv("DEVLAKE_MYSQL_CONTAINER", "nexusai-devlake-mysql")

            # Query weekly aggregated metrics
            query = f"""
            SELECT
                DATE_FORMAT(week_start, '%Y-%m-%d') as week_date,
                deploys_count,
                ROUND(deploys_count / 7, 4) as deploys_per_day,
                ROUND(avg_lead_time, 1) as avg_lead_time_hours
            FROM (
                SELECT
                    DATE(DATE_SUB(merged_date, INTERVAL WEEKDAY(merged_date) DAY)) as week_start,
                    COUNT(*) as deploys_count,
                    AVG(TIMESTAMPDIFF(HOUR, created_date, merged_date)) as avg_lead_time
                FROM pull_requests
                WHERE base_repo_id LIKE '%{github_id}%'
                AND merged_date IS NOT NULL
                AND merged_date > DATE_SUB(NOW(), INTERVAL {days} DAY)
                AND TIMESTAMPDIFF(DAY, created_date, merged_date) < 30
                GROUP BY week_start
                ORDER BY week_start ASC
            ) subq
            """

            cmd = [
                "docker", "exec", mysql_container,
                "sh", "-c",
                f'mysql -uroot -p$MYSQL_ROOT_PASSWORD lake -N -e "{query}"'
            ]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                logger.warning(f"Weekly metrics query failed: {stderr.decode()}")
                return None

            output = stdout.decode().strip()
            if not output:
                return None

            data_points = []
            for line in output.split('\n'):
                parts = line.strip().split('\t')
                if len(parts) >= 4:
                    week_date = parts[0] if parts[0] and parts[0] != 'NULL' else None
                    deploys_per_day = float(parts[2]) if parts[2] and parts[2] != 'NULL' else 0.0
                    avg_lead_time = float(parts[3]) if parts[3] and parts[3] != 'NULL' else 0.0

                    if week_date:
                        data_points.append({
                            "date": week_date,
                            "deploymentFrequency": deploys_per_day,
                            "leadTimeForChanges": avg_lead_time,
                        })

            return data_points if data_points else None

        except Exception as e:
            logger.error(f"Error querying weekly PR metrics: {e}")

        return None

    def _rate_deployment_frequency(self, freq: float) -> str:
        """Rate deployment frequency (deployments per day)."""
        if freq >= 1.0:
            return "elite"
        elif freq >= 0.14:  # ~weekly
            return "high"
        elif freq >= 0.033:  # ~monthly
            return "medium"
        return "low"

    def _rate_lead_time(self, hours: float) -> str:
        """Rate lead time for changes (hours)."""
        if hours <= 1:
            return "elite"
        elif hours <= 24:
            return "high"
        elif hours <= 168:  # 1 week
            return "medium"
        return "low"

    def _rate_mttr(self, hours: float) -> str:
        """Rate mean time to recovery (hours)."""
        if hours <= 1:
            return "elite"
        elif hours <= 24:
            return "high"
        elif hours <= 168:  # 1 week
            return "medium"
        return "low"

    def _rate_cfr(self, rate: float) -> str:
        """Rate change failure rate (percentage)."""
        if rate <= 15:
            return "elite"
        elif rate <= 30:
            return "high"
        elif rate <= 45:
            return "medium"
        return "low"

    # ======================
    # Connections
    # ======================

    async def list_connections(self, plugin: str | None = None) -> list[dict[str, Any]]:
        """List all connections, optionally filtered by plugin."""
        try:
            async with self._get_client() as client:
                if plugin:
                    # Try plugin-specific endpoint
                    endpoints_to_try = [
                        f"/plugins/{plugin}/connections",
                        f"/api/plugins/{plugin}/connections",
                    ]
                else:
                    # List all connections from all plugins
                    endpoints_to_try = [
                        "/connections",
                        "/api/connections",
                    ]
                
                last_error = None
                for endpoint in endpoints_to_try:
                    try:
                        logger.debug(f"Trying DevLake endpoint: {endpoint}")
                        response = await client.get(endpoint)
                        response.raise_for_status()
                        data = response.json()
                        logger.debug(f"Successfully got connections from {endpoint}")
                        return data if isinstance(data, list) else data.get("connections", [])
                    except httpx.HTTPStatusError as e:
                        last_error = e
                        if e.response.status_code == 404 and endpoint != endpoints_to_try[-1]:
                            # Try next endpoint
                            logger.debug(f"Endpoint {endpoint} returned 404, trying next...")
                            continue
                        # If it's the last endpoint or not a 404, raise
                        raise
                
                # Should not reach here, but handle gracefully
                if last_error:
                    raise last_error
                return []
                
        except httpx.ConnectError as e:
            logger.error(f"Failed to connect to DevLake at {self.base_url}: {e}")
            raise ConnectionError(f"Cannot connect to DevLake API at {self.base_url}. Is DevLake running?") from e
        except httpx.TimeoutException as e:
            logger.error(f"DevLake request timeout: {e}")
            raise TimeoutError(f"DevLake API request timed out after {self.timeout}s") from e
        except httpx.HTTPStatusError as e:
            logger.error(f"DevLake API error: {e.response.status_code} - {e.response.text[:500]}")
            raise RuntimeError(f"DevLake API returned {e.response.status_code}: {e.response.text[:200]}") from e

    async def get_connection(self, plugin: str, connection_id: int) -> dict[str, Any]:
        """Get a specific connection."""
        async with self._get_client() as client:
            response = await client.get(f"/plugins/{plugin}/connections/{connection_id}")
            response.raise_for_status()
            return response.json()

    async def create_connection(
        self,
        plugin: str,
        name: str,
        endpoint: str,
        token: str | None = None,
        auth_method: str | None = None,
    ) -> dict[str, Any]:
        """Create a new connection for a plugin.

        Args:
            plugin: Plugin name (e.g., 'github', 'gitlab', 'jira')
            name: Connection name
            endpoint: API endpoint URL
            token: Authentication token (for token-based auth)
            auth_method: Authentication method (e.g., 'AccessToken', 'AppKey')
                        Required for GitHub plugin in DevLake v1.x
        """
        async with self._get_client() as client:
            payload: dict[str, Any] = {
                "name": name,
                "endpoint": endpoint,
            }
            if token:
                payload["token"] = token
            # DevLake v1.x requires authMethod for GitHub connections
            if auth_method:
                payload["authMethod"] = auth_method
            elif plugin == "github" and token:
                # Default to AccessToken for GitHub if token is provided
                payload["authMethod"] = "AccessToken"

            logger.debug(f"Creating {plugin} connection with payload: {list(payload.keys())}")
            response = await client.post(f"/plugins/{plugin}/connections", json=payload)

            # Try to parse response body for error details
            try:
                result = response.json()
            except Exception:
                result = None

            # Check for DevLake error response (may be 200 or 4xx/5xx)
            if isinstance(result, dict) and result.get("success") is False:
                error_msg = result.get("message", "Unknown error")
                if "duplicated" in error_msg.lower() or "already exists" in error_msg.lower():
                    raise ValueError(f"Connection already exists: {error_msg}")
                raise ValueError(f"DevLake returned error: {error_msg}")

            # Now raise for HTTP errors if no DevLake-specific error was found
            response.raise_for_status()

            return result if result else response.json()

    async def test_connection(self, plugin: str, connection_id: int) -> dict[str, Any]:
        """Test a connection."""
        async with self._get_client() as client:
            response = await client.post(
                f"/plugins/{plugin}/connections/{connection_id}/test"
            )
            response.raise_for_status()
            return response.json()

    # ======================
    # Blueprints
    # ======================

    async def list_blueprints(self) -> list[dict[str, Any]]:
        """List all blueprints."""
        async with self._get_client() as client:
            response = await client.get("/blueprints")
            response.raise_for_status()
            data = response.json()
            return data.get("blueprints", []) if isinstance(data, dict) else data

    async def get_blueprint(self, blueprint_id: int) -> dict[str, Any]:
        """Get a specific blueprint."""
        async with self._get_client() as client:
            response = await client.get(f"/blueprints/{blueprint_id}")
            response.raise_for_status()
            return response.json()

    async def create_blueprint(
        self,
        name: str,
        project_name: str,
        connections: list[dict[str, Any]],
        mode: str = "NORMAL",
        cron_config: str | None = None,
        skip_on_fail: bool = True,
        labels: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new blueprint for data collection.

        Args:
            name: Blueprint name
            project_name: Project name to associate the blueprint with
            connections: List of connection configurations with scopes
                Each connection should have:
                - plugin: Plugin name (e.g., 'github', 'gitlab')
                - connectionId: Connection ID
                - scopes: List of scopes (repos/projects) to sync
            mode: Blueprint mode (NORMAL or ADVANCED)
            cron_config: Cron schedule (e.g., "0 0 * * *" for daily)
            skip_on_fail: Whether to skip failed tasks
            labels: Optional list of labels for organization

        Returns:
            Created blueprint data
        """
        async with self._get_client() as client:
            payload = {
                "name": name,
                "projectName": project_name,
                "mode": mode,
                "enable": True,
                "cronConfig": cron_config or "",
                "isManual": cron_config is None,
                "skipOnFail": skip_on_fail,
                "settings": {
                    "version": "2.0.0",
                    "connections": connections,
                },
                "labels": labels or [],
            }

            logger.info(f"Creating blueprint '{name}' for project '{project_name}'")
            logger.debug(f"Blueprint payload: {payload}")

            response = await client.post("/blueprints", json=payload)
            response.raise_for_status()
            return response.json()

    async def update_blueprint(
        self,
        blueprint_id: int,
        name: str | None = None,
        connections: list[dict[str, Any]] | None = None,
        cron_config: str | None = None,
        enable: bool | None = None,
        skip_on_fail: bool | None = None,
    ) -> dict[str, Any]:
        """Update an existing blueprint.

        Args:
            blueprint_id: Blueprint ID to update
            name: New blueprint name (optional)
            connections: Updated connection configurations (optional)
            cron_config: New cron schedule (optional)
            enable: Enable/disable the blueprint (optional)
            skip_on_fail: Whether to skip failed tasks (optional)

        Returns:
            Updated blueprint data
        """
        async with self._get_client() as client:
            # Get existing blueprint first
            existing = await self.get_blueprint(blueprint_id)

            payload = {
                "name": name if name is not None else existing.get("name"),
                "enable": enable if enable is not None else existing.get("enable", True),
                "cronConfig": cron_config if cron_config is not None else existing.get("cronConfig", ""),
                "isManual": (cron_config is None) if cron_config is not None else existing.get("isManual", True),
                "skipOnFail": skip_on_fail if skip_on_fail is not None else existing.get("skipOnFail", True),
            }

            if connections is not None:
                payload["settings"] = {
                    "version": "2.0.0",
                    "connections": connections,
                }
            else:
                payload["settings"] = existing.get("settings", {})

            logger.info(f"Updating blueprint {blueprint_id}")
            response = await client.patch(f"/blueprints/{blueprint_id}", json=payload)
            response.raise_for_status()
            return response.json()

    async def delete_blueprint(self, blueprint_id: int) -> bool:
        """Delete a blueprint.

        Args:
            blueprint_id: Blueprint ID to delete

        Returns:
            True if deleted successfully
        """
        async with self._get_client() as client:
            logger.info(f"Deleting blueprint {blueprint_id}")
            response = await client.delete(f"/blueprints/{blueprint_id}")
            response.raise_for_status()
            return True

    async def trigger_blueprint(self, blueprint_id: int) -> dict[str, Any]:
        """Trigger a blueprint to run."""
        async with self._get_client() as client:
            response = await client.post(f"/blueprints/{blueprint_id}/trigger")
            response.raise_for_status()
            return response.json()

    # ======================
    # Scopes (for discovering repos/projects)
    # ======================

    async def list_scopes(
        self,
        plugin: str,
        connection_id: int,
        page: int = 1,
        page_size: int = 100,
    ) -> dict[str, Any]:
        """List available scopes (repos/projects) for a connection.

        Args:
            plugin: Plugin name (e.g., 'github', 'gitlab')
            connection_id: Connection ID
            page: Page number for pagination
            page_size: Number of items per page

        Returns:
            Dict with scopes list and pagination info
        """
        async with self._get_client() as client:
            response = await client.get(
                f"/plugins/{plugin}/connections/{connection_id}/scopes",
                params={"page": page, "pageSize": page_size},
            )
            response.raise_for_status()
            return response.json()

    async def search_remote_scopes(
        self,
        plugin: str,
        connection_id: int,
        search: str = "",
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        """Search for remote scopes (repos/projects) from the source.

        This searches the remote data source (e.g., GitHub API) for repos
        that can be added to DevLake.

        Args:
            plugin: Plugin name (e.g., 'github', 'gitlab')
            connection_id: Connection ID
            search: Search query (e.g., repo name)
            page: Page number for pagination
            page_size: Number of items per page

        Returns:
            Dict with remote scopes list
        """
        async with self._get_client() as client:
            response = await client.get(
                f"/plugins/{plugin}/connections/{connection_id}/remote-scopes",
                params={
                    "search": search,
                    "page": page,
                    "pageSize": page_size,
                },
            )
            response.raise_for_status()
            return response.json()

    async def add_scope(
        self,
        plugin: str,
        connection_id: int,
        scope_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Add a scope (repo/project) to a connection.

        Args:
            plugin: Plugin name (e.g., 'github', 'gitlab')
            connection_id: Connection ID
            scope_data: Scope data (e.g., repo info from remote-scopes)

        Returns:
            Added scope data
        """
        async with self._get_client() as client:
            response = await client.put(
                f"/plugins/{plugin}/connections/{connection_id}/scopes",
                json=[scope_data],  # API expects array
            )
            response.raise_for_status()
            data = response.json()
            # Return first item if array, otherwise return as-is
            return data[0] if isinstance(data, list) and data else data

    # ======================
    # Pipelines
    # ======================

    async def list_pipelines(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List pipelines with pagination."""
        async with self._get_client() as client:
            response = await client.get(
                "/pipelines",
                params={"page": page, "pageSize": page_size},
            )
            response.raise_for_status()
            return response.json()

    async def get_pipeline(self, pipeline_id: int) -> dict[str, Any]:
        """Get a specific pipeline."""
        async with self._get_client() as client:
            response = await client.get(f"/pipelines/{pipeline_id}")
            response.raise_for_status()
            return response.json()

    async def cancel_pipeline(self, pipeline_id: int) -> dict[str, Any]:
        """Cancel a running pipeline."""
        async with self._get_client() as client:
            response = await client.delete(f"/pipelines/{pipeline_id}")
            response.raise_for_status()
            return response.json()

    async def create_pipeline(
        self,
        name: str,
        plan: list[list[dict[str, Any]]],
        labels: list[str] | None = None,
        skip_on_fail: bool = True,
    ) -> dict[str, Any]:
        """Create and run a pipeline directly (without blueprint).

        This is useful for one-time data syncs or when blueprint creation fails.

        Args:
            name: Pipeline name
            plan: Pipeline plan - list of stages, each stage is list of tasks
                Example: [[{"plugin": "github", "options": {...}}]]
            labels: Optional labels for organization
            skip_on_fail: Whether to skip failed tasks

        Returns:
            Created pipeline data including ID and status
        """
        async with self._get_client() as client:
            payload = {
                "name": name,
                "plan": plan,
                "labels": labels or [],
                "skipOnFail": skip_on_fail,
            }

            logger.info(f"Creating pipeline '{name}'")
            logger.debug(f"Pipeline payload: {payload}")

            response = await client.post("/pipelines", json=payload)
            response.raise_for_status()
            return response.json()

    # ======================
    # Plugins
    # ======================

    async def list_plugins(self) -> list[dict[str, Any]]:
        """List all available DevLake plugins."""
        async with self._get_client() as client:
            response = await client.get("/plugins")
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else data.get("plugins", [])

    async def get_plugin(self, plugin: str) -> dict[str, Any]:
        """Get details about a specific plugin."""
        async with self._get_client() as client:
            response = await client.get(f"/plugins/{plugin}")
            response.raise_for_status()
            return response.json()

    async def get_developer_stats(
        self,
        developer_id: str,
        period_start: Any = None,
        period_end: Any = None,
    ) -> dict[str, Any] | None:
        """Get statistics for a specific developer.

        Args:
            developer_id: The developer's ID
            period_start: Start of the period
            period_end: End of the period

        Returns:
            Developer statistics or None if not found
        """
        try:
            async with self._get_client() as client:
                params = {"developer_id": developer_id}
                if period_start:
                    params["start"] = period_start.isoformat() if hasattr(period_start, 'isoformat') else str(period_start)
                if period_end:
                    params["end"] = period_end.isoformat() if hasattr(period_end, 'isoformat') else str(period_end)

                response = await client.get("/developers/stats", params=params)
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                return response.json()
        except Exception:
            return None

    async def get_project_stats(
        self,
        project_name: str,
        period_start: Any = None,
        period_end: Any = None,
    ) -> dict[str, Any] | None:
        """Get statistics for a project.

        Args:
            project_name: The project name
            period_start: Start of the period
            period_end: End of the period

        Returns:
            Project statistics or None if not found
        """
        try:
            async with self._get_client() as client:
                params = {}
                if period_start:
                    params["start"] = period_start.isoformat() if hasattr(period_start, 'isoformat') else str(period_start)
                if period_end:
                    params["end"] = period_end.isoformat() if hasattr(period_end, 'isoformat') else str(period_end)

                response = await client.get(f"/projects/{project_name}/stats", params=params)
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                return response.json()
        except Exception:
            return None

    async def get_project_contributors(
        self,
        project_name: str,
    ) -> list[dict[str, Any]]:
        """Get contributors for a project.

        Args:
            project_name: The project name

        Returns:
            List of contributors
        """
        try:
            async with self._get_client() as client:
                response = await client.get(f"/projects/{project_name}/contributors")
                if response.status_code == 404:
                    return []
                response.raise_for_status()
                data = response.json()
                return data if isinstance(data, list) else data.get("contributors", [])
        except Exception:
            return []


# Singleton instance
devlake_service = DevLakeService()
