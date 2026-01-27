"""DevLake integration service for engineering analytics."""

from typing import Any

import httpx
from pydantic import BaseModel

from app.core.config import settings


class DevLakeProject(BaseModel):
    """DevLake project model."""

    name: str
    description: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class DevLakeConnection(BaseModel):
    """DevLake connection model."""

    id: int
    name: str
    plugin: str
    endpoint: str | None = None
    created_at: str | None = None


class DORAMetrics(BaseModel):
    """DORA metrics model."""

    deployment_frequency: float | None = None
    lead_time_for_changes: float | None = None  # in hours
    mean_time_to_recovery: float | None = None  # in hours
    change_failure_rate: float | None = None  # percentage


class DevLakeService:
    """Service for interacting with Apache DevLake API."""

    def __init__(self):
        self.base_url = settings.DEVLAKE_API_URL
        self.timeout = 30.0

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any] | list[Any]:
        """Make an HTTP request to DevLake API."""
        url = f"{self.base_url}{path}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()

    async def health_check(self) -> bool:
        """Check if DevLake is healthy."""
        try:
            await self._request("GET", "/api/ping")
            return True
        except Exception:
            return False

    # ======================
    # Projects
    # ======================

    async def list_projects(self) -> list[dict[str, Any]]:
        """List all DevLake projects."""
        result = await self._request("GET", "/api/projects")
        return result if isinstance(result, list) else result.get("projects", [])

    async def get_project(self, project_name: str) -> dict[str, Any]:
        """Get a specific project by name."""
        result = await self._request("GET", f"/api/projects/{project_name}")
        return result if isinstance(result, dict) else {}

    async def create_project(
        self,
        name: str,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Create a new project."""
        data = {"name": name}
        if description:
            data["description"] = description

        result = await self._request("POST", "/api/projects", json=data)
        return result if isinstance(result, dict) else {}

    # ======================
    # Connections
    # ======================

    async def list_connections(self, plugin: str | None = None) -> list[dict[str, Any]]:
        """List all connections, optionally filtered by plugin."""
        if plugin:
            result = await self._request("GET", f"/api/plugins/{plugin}/connections")
        else:
            result = await self._request("GET", "/api/connections")
        return result if isinstance(result, list) else []

    async def get_connection(self, plugin: str, connection_id: int) -> dict[str, Any]:
        """Get a specific connection."""
        result = await self._request(
            "GET", f"/api/plugins/{plugin}/connections/{connection_id}"
        )
        return result if isinstance(result, dict) else {}

    async def create_connection(
        self,
        plugin: str,
        name: str,
        endpoint: str,
        token: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Create a new connection for a plugin."""
        data = {
            "name": name,
            "endpoint": endpoint,
            **kwargs,
        }
        if token:
            data["token"] = token

        result = await self._request(
            "POST", f"/api/plugins/{plugin}/connections", json=data
        )
        return result if isinstance(result, dict) else {}

    async def test_connection(self, plugin: str, connection_id: int) -> dict[str, Any]:
        """Test a connection."""
        result = await self._request(
            "POST", f"/api/plugins/{plugin}/connections/{connection_id}/test"
        )
        return result if isinstance(result, dict) else {}

    # ======================
    # Blueprints
    # ======================

    async def list_blueprints(self) -> list[dict[str, Any]]:
        """List all blueprints."""
        result = await self._request("GET", "/api/blueprints")
        return result if isinstance(result, list) else result.get("blueprints", [])

    async def get_blueprint(self, blueprint_id: int) -> dict[str, Any]:
        """Get a specific blueprint."""
        result = await self._request("GET", f"/api/blueprints/{blueprint_id}")
        return result if isinstance(result, dict) else {}

    async def trigger_blueprint(self, blueprint_id: int) -> dict[str, Any]:
        """Trigger a blueprint to run."""
        result = await self._request("POST", f"/api/blueprints/{blueprint_id}/trigger")
        return result if isinstance(result, dict) else {}

    # ======================
    # Pipelines
    # ======================

    async def list_pipelines(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List pipelines with pagination."""
        result = await self._request(
            "GET",
            "/api/pipelines",
            params={"page": page, "pageSize": page_size},
        )
        return result if isinstance(result, dict) else {"pipelines": [], "count": 0}

    async def get_pipeline(self, pipeline_id: int) -> dict[str, Any]:
        """Get a specific pipeline."""
        result = await self._request("GET", f"/api/pipelines/{pipeline_id}")
        return result if isinstance(result, dict) else {}

    async def cancel_pipeline(self, pipeline_id: int) -> dict[str, Any]:
        """Cancel a running pipeline."""
        result = await self._request("DELETE", f"/api/pipelines/{pipeline_id}")
        return result if isinstance(result, dict) else {}

    # ======================
    # Plugins
    # ======================

    async def list_plugins(self) -> list[dict[str, Any]]:
        """List all available plugins."""
        result = await self._request("GET", "/api/plugins")
        return result if isinstance(result, list) else []

    async def get_plugin(self, plugin: str) -> dict[str, Any]:
        """Get plugin details."""
        result = await self._request("GET", f"/api/plugins/{plugin}")
        return result if isinstance(result, dict) else {}

    # ======================
    # DORA Metrics
    # ======================

    async def get_dora_metrics(
        self,
        project_name: str,
        time_range: str = "past_6_months",
    ) -> DORAMetrics:
        """
        Get DORA metrics for a project.

        Note: DevLake stores DORA metrics in the database.
        This queries the Grafana-style API or database directly.
        """
        # DevLake stores metrics in tables like:
        # - dora_benchmarks
        # - dora_deployment_frequency
        # - dora_lead_time_for_changes
        # - dora_mean_time_to_recovery
        # - dora_change_failure_rate

        try:
            # Try to get metrics from DevLake API
            result = await self._request(
                "GET",
                f"/api/projects/{project_name}/metrics/dora",
                params={"timeRange": time_range},
            )

            if isinstance(result, dict):
                return DORAMetrics(
                    deployment_frequency=result.get("deploymentFrequency"),
                    lead_time_for_changes=result.get("leadTimeForChanges"),
                    mean_time_to_recovery=result.get("meanTimeToRecovery"),
                    change_failure_rate=result.get("changeFailureRate"),
                )
        except Exception:
            pass

        # Return empty metrics if not available
        return DORAMetrics()

    # ======================
    # Scopes
    # ======================

    async def list_scopes(
        self,
        plugin: str,
        connection_id: int,
    ) -> list[dict[str, Any]]:
        """List scopes for a connection (e.g., repositories, projects)."""
        result = await self._request(
            "GET", f"/api/plugins/{plugin}/connections/{connection_id}/scopes"
        )
        return result if isinstance(result, list) else []

    async def add_scope(
        self,
        plugin: str,
        connection_id: int,
        scope_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Add a scope to a connection."""
        result = await self._request(
            "PUT",
            f"/api/plugins/{plugin}/connections/{connection_id}/scopes",
            json=scope_data,
        )
        return result if isinstance(result, dict) else {}


# Singleton instance
devlake_service = DevLakeService()
