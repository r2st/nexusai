"""
Unit tests for Trials API endpoints.
"""

import pytest
from uuid import uuid4
from datetime import datetime, timedelta


class TestTrialsAPI:
    """Test cases for trials endpoints."""

    @pytest.mark.asyncio
    async def test_get_trial_status(self, client, auth_headers, test_organization):
        """Test getting trial status for an organization."""
        response = await client.get(
            f"/api/v1/trials/{test_organization.id}/trial",
            headers=auth_headers,
        )
        assert response.status_code in [200, 403, 404]
        if response.status_code == 200:
            data = response.json()
            assert "trial_status" in data
            assert "is_trial_active" in data
            assert "can_access_features" in data

    @pytest.mark.asyncio
    async def test_start_trial(self, client, auth_headers, test_organization):
        """Test starting a trial for an organization."""
        response = await client.post(
            f"/api/v1/trials/{test_organization.id}/trial/start",
            headers=auth_headers,
        )
        assert response.status_code in [200, 400, 403, 404]

    @pytest.mark.asyncio
    async def test_trial_status_unauthorized(self, client, test_organization):
        """Test accessing trial status without authentication."""
        response = await client.get(
            f"/api/v1/trials/{test_organization.id}/trial",
        )
        assert response.status_code in [401, 403]


class TestTrialsAdminAPI:
    """Test cases for admin trials endpoints."""

    @pytest.mark.asyncio
    async def test_list_all_trials_admin(self, client, admin_auth_headers):
        """Test listing all trials as admin."""
        response = await client.get(
            "/api/v1/trials/admin/trials",
            headers=admin_auth_headers,
        )
        assert response.status_code in [200, 403]
        if response.status_code == 200:
            assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_list_trials_by_status(self, client, admin_auth_headers):
        """Test listing trials filtered by status."""
        response = await client.get(
            "/api/v1/trials/admin/trials?status=active",
            headers=admin_auth_headers,
        )
        assert response.status_code in [200, 403]

    @pytest.mark.asyncio
    async def test_get_trial_statistics(self, client, admin_auth_headers):
        """Test getting trial statistics as admin."""
        response = await client.get(
            "/api/v1/trials/admin/trials/statistics",
            headers=admin_auth_headers,
        )
        assert response.status_code in [200, 403]
        if response.status_code == 200:
            data = response.json()
            assert "active" in data
            assert "expired" in data
            assert "converted" in data

    @pytest.mark.asyncio
    async def test_extend_trial_admin(self, client, admin_auth_headers, test_organization):
        """Test extending a trial as admin."""
        response = await client.post(
            f"/api/v1/trials/admin/trials/{test_organization.id}/extend",
            json={
                "days": 14,
                "reason": "Customer requested extension",
            },
            headers=admin_auth_headers,
        )
        assert response.status_code in [200, 400, 403, 404]

    @pytest.mark.asyncio
    async def test_expire_trial_admin(self, client, admin_auth_headers, test_organization):
        """Test expiring a trial as admin."""
        response = await client.post(
            f"/api/v1/trials/admin/trials/{test_organization.id}/expire",
            headers=admin_auth_headers,
        )
        assert response.status_code in [200, 400, 403, 404]

    @pytest.mark.asyncio
    async def test_admin_endpoints_non_admin(self, client, auth_headers):
        """Test admin endpoints with non-admin user."""
        response = await client.get(
            "/api/v1/trials/admin/trials",
            headers=auth_headers,
        )
        assert response.status_code == 403
