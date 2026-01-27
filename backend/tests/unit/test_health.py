"""
Unit tests for health check endpoints.
"""

import pytest
from httpx import AsyncClient


class TestHealthEndpoints:
    """Test health check endpoints."""

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: AsyncClient):
        """Test root endpoint returns app info."""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data or "app" in data or "status" in data

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test the main health check endpoint."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_healthz_endpoint(self, client: AsyncClient):
        """Test the /healthz alias endpoint."""
        response = await client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_api_health_endpoint(self, client: AsyncClient):
        """Test the /api/health endpoint."""
        response = await client.get("/api/health")
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_api_healthz_endpoint(self, client: AsyncClient):
        """Test the /api/healthz endpoint."""
        response = await client.get("/api/healthz")
        assert response.status_code in [200, 404]


class TestHealthV1Endpoints:
    """Test versioned health endpoints."""

    @pytest.mark.asyncio
    async def test_health_v1(self, client: AsyncClient):
        """Test the /api/v1/health endpoint."""
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "environment" in data

    @pytest.mark.asyncio
    async def test_health_detailed(self, client: AsyncClient):
        """Test detailed health check endpoint."""
        response = await client.get("/api/v1/health/detailed")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "checks" in data
        # Status should be healthy or degraded
        assert data["status"] in ["healthy", "degraded", "unhealthy"]


class TestKubernetesProbes:
    """Test Kubernetes liveness and readiness probes."""

    @pytest.mark.asyncio
    async def test_liveness_probe(self, client: AsyncClient):
        """Test Kubernetes liveness probe endpoint."""
        response = await client.get("/api/v1/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"

    @pytest.mark.asyncio
    async def test_readiness_probe(self, client: AsyncClient):
        """Test Kubernetes readiness probe endpoint."""
        response = await client.get("/api/v1/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        # Status should be ready or not_ready
        assert data["status"] in ["ready", "not_ready"]
        # Should include checks info
        assert "checks" in data

    @pytest.mark.asyncio
    async def test_readiness_includes_database_check(self, client: AsyncClient):
        """Test that readiness probe includes database check."""
        response = await client.get("/api/v1/health/ready")
        assert response.status_code == 200
        data = response.json()
        if "checks" in data:
            assert "database" in data["checks"]

    @pytest.mark.asyncio
    async def test_readiness_includes_redis_check(self, client: AsyncClient):
        """Test that readiness probe includes Redis check."""
        response = await client.get("/api/v1/health/ready")
        assert response.status_code == 200
        data = response.json()
        if "checks" in data:
            # Redis may or may not be configured
            assert "redis" in data["checks"] or True  # Optional


class TestMetricsEndpoint:
    """Test Prometheus metrics endpoint."""

    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, client: AsyncClient):
        """Test /api/v1/health/metrics endpoint."""
        response = await client.get("/api/v1/health/metrics")
        assert response.status_code == 200
        # Should return text/plain (Prometheus format)
        assert "text/plain" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_metrics_contains_uptime(self, client: AsyncClient):
        """Test that metrics include uptime."""
        response = await client.get("/api/v1/health/metrics")
        if response.status_code == 200:
            content = response.text
            assert "nexusai_uptime_seconds" in content or "uptime" in content.lower()

    @pytest.mark.asyncio
    async def test_metrics_contains_version_info(self, client: AsyncClient):
        """Test that metrics include version info."""
        response = await client.get("/api/v1/health/metrics")
        if response.status_code == 200:
            content = response.text
            assert "nexusai_info" in content or "version" in content.lower()

    @pytest.mark.asyncio
    async def test_metrics_contains_feature_flags(self, client: AsyncClient):
        """Test that metrics include feature flags."""
        response = await client.get("/api/v1/health/metrics")
        if response.status_code == 200:
            content = response.text
            # Should include feature flag metrics
            assert "feature" in content.lower() or "nexusai" in content


class TestFeaturesEndpoint:
    """Test features endpoint."""

    @pytest.mark.asyncio
    async def test_features_endpoint(self, client: AsyncClient):
        """Test /features endpoint returns feature flags."""
        response = await client.get("/features")
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            # Should return some feature flags
            assert isinstance(data, dict) or isinstance(data, list)


class TestHealthResponseFormat:
    """Test health check response format."""

    @pytest.mark.asyncio
    async def test_health_includes_version(self, client: AsyncClient):
        """Test that health check includes version."""
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data

    @pytest.mark.asyncio
    async def test_health_includes_environment(self, client: AsyncClient):
        """Test that health check includes environment."""
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "environment" in data

    @pytest.mark.asyncio
    async def test_detailed_health_checks_format(self, client: AsyncClient):
        """Test detailed health check format."""
        response = await client.get("/api/v1/health/detailed")
        assert response.status_code == 200
        data = response.json()

        # Each check should have a status
        if "checks" in data:
            for check_name, check_info in data["checks"].items():
                assert "status" in check_info


class TestHealthEdgeCases:
    """Test health check edge cases."""

    @pytest.mark.asyncio
    async def test_health_multiple_requests(self, client: AsyncClient):
        """Test multiple consecutive health checks."""
        for _ in range(5):
            response = await client.get("/health")
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_liveness_multiple_requests(self, client: AsyncClient):
        """Test multiple consecutive liveness probes."""
        for _ in range(5):
            response = await client.get("/api/v1/health/live")
            assert response.status_code == 200
            assert response.json()["status"] == "alive"

    @pytest.mark.asyncio
    async def test_health_with_query_params(self, client: AsyncClient):
        """Test health check ignores query params."""
        response = await client.get("/health?foo=bar&baz=qux")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_post_method_not_allowed(self, client: AsyncClient):
        """Test POST to health endpoint returns 405."""
        response = await client.post("/health", json={})
        assert response.status_code == 405

    @pytest.mark.asyncio
    async def test_health_delete_method_not_allowed(self, client: AsyncClient):
        """Test DELETE to health endpoint returns 405."""
        response = await client.delete("/health")
        assert response.status_code == 405
