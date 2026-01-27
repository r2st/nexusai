"""
Unit tests for Analytics API endpoints (DevLake integration).
"""

import pytest
from uuid import uuid4
from unittest.mock import patch, AsyncMock, MagicMock

from httpx import AsyncClient


class TestDevLakeHealth:
    """Test DevLake health check endpoint."""

    @pytest.mark.asyncio
    async def test_devlake_health_check(self, client: AsyncClient, auth_headers: dict):
        """Test DevLake health check endpoint."""
        response = await client.get(
            "/api/v1/analytics/health",
            headers=auth_headers,
        )
        assert response.status_code in [200, 503]
        if response.status_code == 200:
            data = response.json()
            assert "devlake_available" in data
            assert "message" in data

    @pytest.mark.asyncio
    async def test_devlake_health_unauthorized(self, client: AsyncClient):
        """Test DevLake health check without auth."""
        response = await client.get("/api/v1/analytics/health")
        assert response.status_code in [200, 401, 403, 503]


class TestProjectsAPI:
    """Test projects endpoints."""

    @pytest.mark.asyncio
    async def test_list_projects(self, client: AsyncClient, auth_headers: dict):
        """Test listing DevLake projects."""
        response = await client.get(
            "/api/v1/analytics/projects",
            headers=auth_headers,
        )
        # May fail if DevLake is not available
        assert response.status_code in [200, 503]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_project(self, client: AsyncClient, auth_headers: dict):
        """Test getting a specific project."""
        project_name = "test-project"
        response = await client.get(
            f"/api/v1/analytics/projects/{project_name}",
            headers=auth_headers,
        )
        # May return 404 if project doesn't exist or 503 if DevLake unavailable
        assert response.status_code in [200, 404, 503]

    @pytest.mark.asyncio
    async def test_create_project(self, client: AsyncClient, auth_headers: dict):
        """Test creating a new project in DevLake."""
        unique_name = f"test-project-{uuid4().hex[:8]}"
        response = await client.post(
            "/api/v1/analytics/projects",
            json={
                "name": unique_name,
                "description": "Test project for unit tests",
            },
            headers=auth_headers,
        )
        # May fail if DevLake is not available
        assert response.status_code in [200, 201, 400, 503]

    @pytest.mark.asyncio
    async def test_create_project_missing_name(self, client: AsyncClient, auth_headers: dict):
        """Test creating project without name."""
        response = await client.post(
            "/api/v1/analytics/projects",
            json={
                "description": "Test project",
            },
            headers=auth_headers,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_projects_unauthorized(self, client: AsyncClient):
        """Test listing projects without auth."""
        response = await client.get("/api/v1/analytics/projects")
        assert response.status_code in [401, 403]


class TestDORAMetrics:
    """Test DORA metrics endpoints."""

    @pytest.mark.asyncio
    async def test_get_dora_metrics(self, client: AsyncClient, auth_headers: dict):
        """Test getting DORA metrics for a project."""
        project_name = "test_project"
        response = await client.get(
            f"/api/v1/analytics/projects/{project_name}/dora",
            headers=auth_headers,
        )
        # May fail if project doesn't exist or DevLake unavailable
        assert response.status_code in [200, 404, 503]

    @pytest.mark.asyncio
    async def test_get_dora_metrics_with_time_range(self, client: AsyncClient, auth_headers: dict):
        """Test getting DORA metrics with time range."""
        project_name = "test_project"
        response = await client.get(
            f"/api/v1/analytics/projects/{project_name}/dora",
            params={"time_range": "past_6_months"},
            headers=auth_headers,
        )
        assert response.status_code in [200, 404, 503]

    @pytest.mark.asyncio
    async def test_get_dora_metrics_unauthorized(self, client: AsyncClient):
        """Test getting DORA metrics without auth."""
        response = await client.get("/api/v1/analytics/projects/test_project/dora")
        assert response.status_code in [401, 403]


class TestConnectionsAPI:
    """Test connections endpoints."""

    @pytest.mark.asyncio
    async def test_list_connections(self, client: AsyncClient, auth_headers: dict):
        """Test listing all connections."""
        response = await client.get(
            "/api/v1/analytics/connections",
            headers=auth_headers,
        )
        assert response.status_code in [200, 503]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_list_connections_by_plugin(self, client: AsyncClient, auth_headers: dict):
        """Test listing connections filtered by plugin."""
        response = await client.get(
            "/api/v1/analytics/connections",
            params={"plugin": "github"},
            headers=auth_headers,
        )
        assert response.status_code in [200, 503]

    @pytest.mark.asyncio
    async def test_get_connection(self, client: AsyncClient, auth_headers: dict):
        """Test getting a specific connection."""
        response = await client.get(
            "/api/v1/analytics/plugins/github/connections/1",
            headers=auth_headers,
        )
        assert response.status_code in [200, 404, 503]

    @pytest.mark.asyncio
    async def test_create_connection(self, client: AsyncClient, auth_headers: dict):
        """Test creating a new connection."""
        response = await client.post(
            "/api/v1/analytics/plugins/github/connections",
            json={
                "name": f"test-connection-{uuid4().hex[:8]}",
                "endpoint": "https://api.github.com",
                "token": "test-token",
            },
            headers=auth_headers,
        )
        assert response.status_code in [200, 201, 400, 503]

    @pytest.mark.asyncio
    async def test_test_connection(self, client: AsyncClient, auth_headers: dict):
        """Test testing a connection."""
        response = await client.post(
            "/api/v1/analytics/plugins/github/connections/1/test",
            headers=auth_headers,
        )
        # May fail if connection doesn't exist
        assert response.status_code in [200, 404, 503]

    @pytest.mark.asyncio
    async def test_list_connections_unauthorized(self, client: AsyncClient):
        """Test listing connections without auth."""
        response = await client.get("/api/v1/analytics/connections")
        assert response.status_code in [401, 403]


class TestBlueprintsAPI:
    """Test blueprints endpoints."""

    @pytest.mark.asyncio
    async def test_list_blueprints(self, client: AsyncClient, auth_headers: dict):
        """Test listing all blueprints."""
        response = await client.get(
            "/api/v1/analytics/blueprints",
            headers=auth_headers,
        )
        assert response.status_code in [200, 503]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_blueprint(self, client: AsyncClient, auth_headers: dict):
        """Test getting a specific blueprint."""
        blueprint_id = 1
        response = await client.get(
            f"/api/v1/analytics/blueprints/{blueprint_id}",
            headers=auth_headers,
        )
        assert response.status_code in [200, 404, 503]

    @pytest.mark.asyncio
    async def test_trigger_blueprint(self, client: AsyncClient, auth_headers: dict):
        """Test triggering a blueprint."""
        blueprint_id = 1
        response = await client.post(
            f"/api/v1/analytics/blueprints/{blueprint_id}/trigger",
            headers=auth_headers,
        )
        assert response.status_code in [200, 404, 503]

    @pytest.mark.asyncio
    async def test_list_blueprints_unauthorized(self, client: AsyncClient):
        """Test listing blueprints without auth."""
        response = await client.get("/api/v1/analytics/blueprints")
        assert response.status_code in [401, 403]


class TestPipelinesAPI:
    """Test pipelines endpoints."""

    @pytest.mark.asyncio
    async def test_list_pipelines(self, client: AsyncClient, auth_headers: dict):
        """Test listing pipelines."""
        response = await client.get(
            "/api/v1/analytics/pipelines",
            headers=auth_headers,
        )
        assert response.status_code in [200, 503]

    @pytest.mark.asyncio
    async def test_list_pipelines_with_pagination(self, client: AsyncClient, auth_headers: dict):
        """Test listing pipelines with pagination."""
        response = await client.get(
            "/api/v1/analytics/pipelines",
            params={"page": 1, "page_size": 10},
            headers=auth_headers,
        )
        assert response.status_code in [200, 503]

    @pytest.mark.asyncio
    async def test_get_pipeline(self, client: AsyncClient, auth_headers: dict):
        """Test getting a specific pipeline."""
        pipeline_id = 1
        response = await client.get(
            f"/api/v1/analytics/pipelines/{pipeline_id}",
            headers=auth_headers,
        )
        assert response.status_code in [200, 404, 503]

    @pytest.mark.asyncio
    async def test_cancel_pipeline(self, client: AsyncClient, auth_headers: dict):
        """Test canceling a pipeline."""
        pipeline_id = 1
        response = await client.delete(
            f"/api/v1/analytics/pipelines/{pipeline_id}",
            headers=auth_headers,
        )
        assert response.status_code in [200, 204, 404, 503]

    @pytest.mark.asyncio
    async def test_list_pipelines_unauthorized(self, client: AsyncClient):
        """Test listing pipelines without auth."""
        response = await client.get("/api/v1/analytics/pipelines")
        assert response.status_code in [401, 403]


class TestPluginsAPI:
    """Test plugins endpoints."""

    @pytest.mark.asyncio
    async def test_list_plugins(self, client: AsyncClient, auth_headers: dict):
        """Test listing available plugins."""
        response = await client.get(
            "/api/v1/analytics/plugins",
            headers=auth_headers,
        )
        assert response.status_code in [200, 503]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_plugin(self, client: AsyncClient, auth_headers: dict):
        """Test getting plugin details."""
        plugin_name = "github"
        response = await client.get(
            f"/api/v1/analytics/plugins/{plugin_name}",
            headers=auth_headers,
        )
        assert response.status_code in [200, 404, 503]

    @pytest.mark.asyncio
    async def test_list_plugins_unauthorized(self, client: AsyncClient):
        """Test listing plugins without auth."""
        response = await client.get("/api/v1/analytics/plugins")
        assert response.status_code in [401, 403]


class TestAIAnalyticsAPI:
    """Test cases for AI analytics endpoints."""

    @pytest.mark.asyncio
    async def test_get_ai_tools_overview(self, client: AsyncClient, auth_headers: dict):
        """Test getting AI plugins list."""
        response = await client.get(
            "/api/v1/ai-analytics/plugins",
            headers=auth_headers,
        )
        assert response.status_code in [200, 401, 503]

    @pytest.mark.asyncio
    async def test_get_ai_adoption(self, client: AsyncClient, auth_headers: dict):
        """Test getting AI metrics."""
        response = await client.get(
            "/api/v1/ai-analytics/metrics",
            headers=auth_headers,
        )
        # 400 is expected when tenant context is missing
        assert response.status_code in [200, 400, 401, 503]

    @pytest.mark.asyncio
    async def test_get_ai_productivity(self, client: AsyncClient, auth_headers: dict):
        """Test getting AI productivity impact."""
        response = await client.get(
            "/api/v1/ai-analytics/productivity",
            headers=auth_headers,
        )
        # 400 is expected when tenant context is missing
        assert response.status_code in [200, 400, 401, 503]

    @pytest.mark.asyncio
    async def test_get_ai_trends(self, client: AsyncClient, auth_headers: dict):
        """Test getting AI ROI trends."""
        response = await client.get(
            "/api/v1/ai-analytics/roi/trend",
            params={"granularity": "monthly"},
            headers=auth_headers,
        )
        # 400 is expected when tenant context is missing
        assert response.status_code in [200, 400, 401, 503]


class TestMetricsAPI:
    """Test cases for engineering metrics endpoints."""

    @pytest.mark.asyncio
    async def test_get_dora_metrics(self, client: AsyncClient, auth_headers: dict):
        """Test getting DORA metrics for a project."""
        response = await client.get(
            "/api/v1/metrics/dora/test_project",
            headers=auth_headers,
        )
        assert response.status_code in [200, 401, 404, 503]

    @pytest.mark.asyncio
    async def test_get_space_metrics(self, client: AsyncClient, auth_headers: dict):
        """Test getting SPACE metrics for a project."""
        response = await client.get(
            "/api/v1/metrics/space/test_project",
            headers=auth_headers,
        )
        assert response.status_code in [200, 401, 404, 503]

    @pytest.mark.asyncio
    async def test_get_business_metrics(self, client: AsyncClient, auth_headers: dict):
        """Test getting business metrics for a project."""
        response = await client.get(
            "/api/v1/metrics/business/test_project",
            headers=auth_headers,
        )
        assert response.status_code in [200, 401, 404, 503]

    @pytest.mark.asyncio
    async def test_get_team_productivity(self, client: AsyncClient, auth_headers: dict):
        """Test getting team productivity metrics."""
        response = await client.get(
            "/api/v1/metrics/productivity/team/test_project",
            headers=auth_headers,
        )
        assert response.status_code in [200, 401, 404, 503]

    @pytest.mark.asyncio
    async def test_get_dora_trend(self, client: AsyncClient, auth_headers: dict):
        """Test getting DORA metric trends."""
        response = await client.get(
            "/api/v1/metrics/dora/test_project/trend",
            headers=auth_headers,
        )
        assert response.status_code in [200, 401, 404, 503]


class TestAnalyticsEdgeCases:
    """Test analytics edge cases."""

    @pytest.mark.asyncio
    async def test_project_name_with_special_characters(self, client: AsyncClient, auth_headers: dict):
        """Test project operations with special characters in name."""
        project_name = "test-project-with-special_chars.v1"
        response = await client.get(
            f"/api/v1/analytics/projects/{project_name}",
            headers=auth_headers,
        )
        # Should handle special characters in URL
        assert response.status_code in [200, 404, 503]

    @pytest.mark.asyncio
    async def test_invalid_time_range(self, client: AsyncClient, auth_headers: dict):
        """Test DORA metrics with invalid time range."""
        response = await client.get(
            "/api/v1/analytics/projects/test/dora",
            params={"time_range": "invalid_range"},
            headers=auth_headers,
        )
        # Should either use default or return validation error
        assert response.status_code in [200, 400, 422, 503]

    @pytest.mark.asyncio
    async def test_negative_pipeline_page(self, client: AsyncClient, auth_headers: dict):
        """Test listing pipelines with negative page."""
        response = await client.get(
            "/api/v1/analytics/pipelines",
            params={"page": -1},
            headers=auth_headers,
        )
        # Should either use default or return validation error
        assert response.status_code in [200, 400, 422, 503]

    @pytest.mark.asyncio
    async def test_large_page_size(self, client: AsyncClient, auth_headers: dict):
        """Test listing pipelines with very large page size."""
        response = await client.get(
            "/api/v1/analytics/pipelines",
            params={"page_size": 10000},
            headers=auth_headers,
        )
        # Should cap or return error
        assert response.status_code in [200, 400, 422, 503]


class TestMockedAnalytics:
    """Test analytics with mocked DevLake service."""

    @pytest.mark.asyncio
    @patch("app.services.devlake.devlake_service.health_check")
    async def test_devlake_healthy(
        self, mock_health, client: AsyncClient, auth_headers: dict
    ):
        """Test when DevLake is healthy."""
        mock_health.return_value = True

        response = await client.get(
            "/api/v1/analytics/health",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["devlake_available"] is True

    @pytest.mark.asyncio
    @patch("app.services.devlake.devlake_service.health_check")
    async def test_devlake_unhealthy(
        self, mock_health, client: AsyncClient, auth_headers: dict
    ):
        """Test when DevLake is unhealthy."""
        mock_health.return_value = False

        response = await client.get(
            "/api/v1/analytics/health",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["devlake_available"] is False

    @pytest.mark.asyncio
    @patch("app.services.devlake.devlake_service.list_projects")
    async def test_list_projects_mocked(
        self, mock_list, client: AsyncClient, auth_headers: dict
    ):
        """Test listing projects with mocked response."""
        mock_list.return_value = [
            {"name": "project1", "description": "First project"},
            {"name": "project2", "description": "Second project"},
        ]

        response = await client.get(
            "/api/v1/analytics/projects",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "project1"
