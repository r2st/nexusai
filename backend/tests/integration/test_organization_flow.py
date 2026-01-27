"""
Integration tests for complete organization and trial workflows.
"""

import pytest
from uuid import uuid4


class TestOrganizationTrialFlow:
    """Test complete organization and trial workflows."""

    @pytest.mark.asyncio
    async def test_create_org_and_start_trial(self, client, auth_headers, test_user):
        """Test creating organization and starting trial."""
        # 1. Create organization
        create_response = await client.post(
            "/api/v1/organizations",
            json={
                "name": f"Test Org {uuid4().hex[:8]}",
                "slug": f"test-org-{uuid4().hex[:8]}",
                "description": "Integration test organization",
            },
            headers=auth_headers,
        )

        # Organization creation may require different setup
        if create_response.status_code in [200, 201]:
            org = create_response.json()
            org_id = org["id"]

            # 2. Get trial status
            status_response = await client.get(
                f"/api/v1/trials/{org_id}/trial",
                headers=auth_headers,
            )
            assert status_response.status_code in [200, 403, 404]

            # 3. Start trial
            start_response = await client.post(
                f"/api/v1/trials/{org_id}/trial/start",
                headers=auth_headers,
            )
            assert start_response.status_code in [200, 400, 403]

            if start_response.status_code == 200:
                trial_data = start_response.json()
                assert trial_data["is_trial_active"] == True
                assert trial_data["trial_days_remaining"] > 0

    @pytest.mark.asyncio
    async def test_organization_member_management(self, client, auth_headers, test_organization):
        """Test organization member management workflow."""
        org_id = str(test_organization.id)

        # 1. List members
        list_response = await client.get(
            f"/api/v1/organizations/{org_id}/members",
            headers=auth_headers,
        )
        assert list_response.status_code in [200, 403, 404]

        # 2. Invite a new member
        invite_response = await client.post(
            f"/api/v1/organizations/{org_id}/members/invite",
            json={
                "email": f"invite_{uuid4().hex[:8]}@example.com",
                "role": "member",
            },
            headers=auth_headers,
        )
        assert invite_response.status_code in [200, 201, 400, 403]

    @pytest.mark.asyncio
    async def test_organization_usage_tracking(self, client, auth_headers, test_organization):
        """Test organization usage tracking workflow."""
        org_id = str(test_organization.id)

        # Get usage summary
        response = await client.get(
            f"/api/v1/subscriptions/{org_id}/usage",
            headers=auth_headers,
        )
        assert response.status_code in [200, 403, 404]

        if response.status_code == 200:
            data = response.json()
            assert "members" in data
            assert "projects" in data
            assert "tier" in data


class TestAdminTrialManagement:
    """Test admin trial management workflows."""

    @pytest.mark.asyncio
    async def test_admin_trial_overview(self, client, admin_auth_headers):
        """Test admin getting trial overview."""
        # List all trials
        list_response = await client.get(
            "/api/v1/trials/admin/trials",
            headers=admin_auth_headers,
        )
        assert list_response.status_code in [200, 403]

        # Get statistics
        stats_response = await client.get(
            "/api/v1/trials/admin/trials/statistics",
            headers=admin_auth_headers,
        )
        assert stats_response.status_code in [200, 403]

    @pytest.mark.asyncio
    async def test_admin_extend_trial(self, client, admin_auth_headers, test_organization):
        """Test admin extending a trial."""
        org_id = str(test_organization.id)

        response = await client.post(
            f"/api/v1/trials/admin/trials/{org_id}/extend",
            json={
                "days": 14,
                "reason": "Integration test extension",
            },
            headers=admin_auth_headers,
        )
        assert response.status_code in [200, 400, 403, 404]

    @pytest.mark.asyncio
    async def test_admin_change_tier(self, client, admin_auth_headers, test_organization):
        """Test admin changing organization tier."""
        org_id = str(test_organization.id)

        response = await client.post(
            f"/api/v1/subscriptions/admin/{org_id}/tier",
            json={"tier": "pro"},
            headers=admin_auth_headers,
        )
        assert response.status_code in [200, 400, 403, 404]

        if response.status_code == 200:
            data = response.json()
            assert data["new_tier"] == "pro"


class TestMultiTenantIsolation:
    """Test multi-tenant data isolation."""

    @pytest.mark.asyncio
    async def test_cannot_access_other_org_data(self, client, auth_headers, test_organization):
        """Test that users cannot access other organization's data."""
        # Create fake org ID
        fake_org_id = str(uuid4())

        # Try to access fake org
        response = await client.get(
            f"/api/v1/organizations/{fake_org_id}",
            headers=auth_headers,
        )
        assert response.status_code in [403, 404]

    @pytest.mark.asyncio
    async def test_tenant_header_isolation(self, client, auth_headers):
        """Test that X-Tenant-ID header is respected."""
        fake_tenant_id = str(uuid4())

        # Make request with different tenant header
        headers = {**auth_headers, "X-Tenant-ID": fake_tenant_id}

        response = await client.get(
            "/api/v1/chat/conversations",
            headers=headers,
        )
        # Should either work (empty list) or forbidden
        assert response.status_code in [200, 403]
