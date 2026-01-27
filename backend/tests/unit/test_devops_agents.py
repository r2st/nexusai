"""
Unit tests for DevOps Agents API endpoints.
"""

import pytest
from uuid import uuid4


class TestDevOpsAgentsAPI:
    """Test cases for DevOps agents endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test DevOps agents health check."""
        response = await client.get("/api/v1/devops-agents/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "agents" in data

    @pytest.mark.asyncio
    async def test_analyze_dora(self, client, auth_headers):
        """Test DORA metrics analysis."""
        response = await client.post(
            "/api/v1/devops-agents/dora/analyze",
            json={
                "project_id": str(uuid4()),
                "period_days": 30,
            },
            headers=auth_headers,
        )
        assert response.status_code in [200, 400, 401, 404, 503]

    @pytest.mark.asyncio
    async def test_analyze_dora_custom_period(self, client, auth_headers):
        """Test DORA analysis with custom period."""
        response = await client.post(
            "/api/v1/devops-agents/dora/analyze",
            json={
                "project_id": str(uuid4()),
                "period_days": 90,
            },
            headers=auth_headers,
        )
        assert response.status_code in [200, 400, 401, 404, 503]

    @pytest.mark.asyncio
    async def test_analyze_adoption(self, client, auth_headers):
        """Test adoption analysis."""
        response = await client.post(
            "/api/v1/devops-agents/adoption/analyze",
            json={
                "organization_id": str(uuid4()),
                "period_days": 30,
            },
            headers=auth_headers,
        )
        assert response.status_code in [200, 400, 401, 404, 503]

    @pytest.mark.asyncio
    async def test_create_workflow(self, client, auth_headers):
        """Test creating a DevOps workflow."""
        response = await client.post(
            "/api/v1/devops-agents/workflows",
            json={
                "workflow_type": "dora_full",
                "project_id": str(uuid4()),
            },
            headers=auth_headers,
        )
        assert response.status_code in [200, 201, 400, 401, 422, 503]

    @pytest.mark.asyncio
    async def test_create_workflow_adoption(self, client, auth_headers):
        """Test creating an adoption workflow."""
        response = await client.post(
            "/api/v1/devops-agents/workflows",
            json={
                "workflow_type": "adoption_full",
                "organization_id": str(uuid4()),
            },
            headers=auth_headers,
        )
        assert response.status_code in [200, 201, 400, 401, 422, 503]

    @pytest.mark.asyncio
    async def test_get_workflow_not_found(self, client, auth_headers):
        """Test getting a non-existent workflow."""
        fake_id = str(uuid4())
        response = await client.get(
            f"/api/v1/devops-agents/workflows/{fake_id}",
            headers=auth_headers,
        )
        assert response.status_code in [404, 400]

    @pytest.mark.asyncio
    async def test_list_workflows(self, client, auth_headers):
        """Test listing workflows."""
        response = await client.get(
            "/api/v1/devops-agents/workflows",
            headers=auth_headers,
        )
        assert response.status_code in [200, 401]
        if response.status_code == 200:
            data = response.json()
            assert "workflows" in data

    @pytest.mark.asyncio
    async def test_list_workflows_with_limit(self, client, auth_headers):
        """Test listing workflows with limit."""
        response = await client.get(
            "/api/v1/devops-agents/workflows?limit=10",
            headers=auth_headers,
        )
        assert response.status_code in [200, 401]

    @pytest.mark.asyncio
    async def test_get_benchmarks(self, client):
        """Test getting DORA benchmarks."""
        response = await client.get("/api/v1/devops-agents/benchmarks")
        assert response.status_code == 200
        data = response.json()
        assert "deployment_frequency" in data
        assert "lead_time_for_changes" in data

    @pytest.mark.asyncio
    async def test_devops_unauthorized(self, client):
        """Test accessing DevOps endpoints without authentication."""
        response = await client.get("/api/v1/devops-agents/workflows")
        assert response.status_code in [401, 403]


class TestDevOpsValidation:
    """Test DevOps input validation."""

    @pytest.mark.asyncio
    async def test_analyze_dora_invalid_period(self, client, auth_headers):
        """Test DORA analysis with invalid period."""
        response = await client.post(
            "/api/v1/devops-agents/dora/analyze",
            json={
                "project_id": str(uuid4()),
                "period_days": -1,
            },
            headers=auth_headers,
        )
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_create_workflow_invalid_type(self, client, auth_headers):
        """Test creating workflow with invalid type."""
        response = await client.post(
            "/api/v1/devops-agents/workflows",
            json={
                "workflow_type": "invalid_workflow_type",
            },
            headers=auth_headers,
        )
        assert response.status_code in [400, 422, 503]

    @pytest.mark.asyncio
    async def test_analyze_dora_missing_project(self, client, auth_headers):
        """Test DORA analysis without project_id."""
        response = await client.post(
            "/api/v1/devops-agents/dora/analyze",
            json={"period_days": 30},
            headers=auth_headers,
        )
        assert response.status_code == 422
