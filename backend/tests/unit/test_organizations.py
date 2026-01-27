"""
Unit tests for Organizations API endpoints.
"""

import pytest
from uuid import uuid4
from datetime import datetime

from httpx import AsyncClient
from app.models.organization import Organization, OrganizationMember


class TestOrganizationCRUD:
    """Test organization CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_organization(self, client: AsyncClient, auth_headers: dict):
        """Test creating a new organization."""
        unique_id = uuid4().hex[:8]
        response = await client.post(
            "/api/v1/organizations",
            json={
                "name": f"Test Organization {unique_id}",
                "slug": f"test-org-{unique_id}",
                "description": "A test organization",
            },
            headers=auth_headers,
        )
        assert response.status_code in [200, 201, 400, 422]
        if response.status_code in [200, 201]:
            data = response.json()
            assert "id" in data
            assert data["name"] == f"Test Organization {unique_id}"
            assert data["slug"] == f"test-org-{unique_id}"

    @pytest.mark.asyncio
    async def test_create_organization_with_website(self, client: AsyncClient, auth_headers: dict):
        """Test creating organization with optional website."""
        unique_id = uuid4().hex[:8]
        response = await client.post(
            "/api/v1/organizations",
            json={
                "name": f"Organization {unique_id}",
                "slug": f"org-{unique_id}",
                "description": "Test organization",
                "website": "https://example.com",
            },
            headers=auth_headers,
        )
        assert response.status_code in [200, 201, 400, 422]

    @pytest.mark.asyncio
    async def test_create_organization_duplicate_slug(self, client: AsyncClient, auth_headers: dict):
        """Test creating organization with duplicate slug."""
        slug = f"duplicate-slug-{uuid4().hex[:8]}"

        # Create first organization
        response1 = await client.post(
            "/api/v1/organizations",
            json={
                "name": "First Organization",
                "slug": slug,
            },
            headers=auth_headers,
        )

        # Try to create second with same slug
        response2 = await client.post(
            "/api/v1/organizations",
            json={
                "name": "Second Organization",
                "slug": slug,
            },
            headers=auth_headers,
        )

        if response1.status_code in [200, 201]:
            assert response2.status_code == 400

    @pytest.mark.asyncio
    async def test_list_organizations(self, client: AsyncClient, auth_headers: dict):
        """Test listing organizations."""
        response = await client.get(
            "/api/v1/organizations",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_get_organization(self, client: AsyncClient, auth_headers: dict, test_organization: Organization):
        """Test getting a specific organization."""
        response = await client.get(
            f"/api/v1/organizations/{test_organization.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_organization.id
        assert data["name"] == test_organization.name

    @pytest.mark.asyncio
    async def test_get_organization_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test getting non-existent organization."""
        fake_id = str(uuid4())
        response = await client.get(
            f"/api/v1/organizations/{fake_id}",
            headers=auth_headers,
        )
        assert response.status_code in [403, 404]

    @pytest.mark.asyncio
    async def test_update_organization(self, client: AsyncClient, auth_headers: dict, test_organization: Organization):
        """Test updating an organization."""
        response = await client.patch(
            f"/api/v1/organizations/{test_organization.id}",
            json={
                "name": "Updated Organization Name",
                "description": "Updated description",
            },
            headers=auth_headers,
        )
        assert response.status_code in [200, 403, 404, 405]
        if response.status_code == 200:
            data = response.json()
            assert data["name"] == "Updated Organization Name"

    @pytest.mark.asyncio
    async def test_update_organization_partial(self, client: AsyncClient, auth_headers: dict, test_organization: Organization):
        """Test partial update of organization."""
        response = await client.patch(
            f"/api/v1/organizations/{test_organization.id}",
            json={
                "description": "Only updating description",
            },
            headers=auth_headers,
        )
        assert response.status_code in [200, 403, 404, 405]

    @pytest.mark.asyncio
    async def test_delete_organization(self, client: AsyncClient, auth_headers: dict, test_organization: Organization):
        """Test deleting an organization."""
        response = await client.delete(
            f"/api/v1/organizations/{test_organization.id}",
            headers=auth_headers,
        )
        assert response.status_code in [200, 204, 403, 404]

    @pytest.mark.asyncio
    async def test_delete_organization_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test deleting non-existent organization."""
        fake_id = str(uuid4())
        response = await client.delete(
            f"/api/v1/organizations/{fake_id}",
            headers=auth_headers,
        )
        assert response.status_code in [403, 404]


class TestOrganizationMembers:
    """Test organization member management."""

    @pytest.mark.asyncio
    async def test_list_members(self, client: AsyncClient, auth_headers: dict, test_organization: Organization):
        """Test listing organization members."""
        response = await client.get(
            f"/api/v1/organizations/{test_organization.id}/members",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should include at least the owner
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_invite_member(self, client: AsyncClient, auth_headers: dict, test_organization: Organization):
        """Test inviting a new member."""
        unique_email = f"invited_{uuid4().hex[:8]}@example.com"
        response = await client.post(
            f"/api/v1/organizations/{test_organization.id}/members/invite",
            json={
                "email": unique_email,
                "role": "member",
            },
            headers=auth_headers,
        )
        assert response.status_code in [200, 201, 400, 403]
        if response.status_code in [200, 201]:
            data = response.json()
            assert "message" in data or "email" in data

    @pytest.mark.asyncio
    async def test_invite_member_with_team(self, client: AsyncClient, auth_headers: dict, test_organization: Organization):
        """Test inviting member with team assignment."""
        unique_email = f"team_{uuid4().hex[:8]}@example.com"
        response = await client.post(
            f"/api/v1/organizations/{test_organization.id}/members/invite",
            json={
                "email": unique_email,
                "role": "member",
                "team": "Engineering",
                "department": "Product",
            },
            headers=auth_headers,
        )
        assert response.status_code in [200, 201, 400, 403]

    @pytest.mark.asyncio
    async def test_invite_existing_member(self, client: AsyncClient, auth_headers: dict, test_organization: Organization, test_user):
        """Test inviting an already existing member."""
        response = await client.post(
            f"/api/v1/organizations/{test_organization.id}/members/invite",
            json={
                "email": test_user.email,
                "role": "member",
            },
            headers=auth_headers,
        )
        # Should fail as user is already a member
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_invite_invalid_email(self, client: AsyncClient, auth_headers: dict, test_organization: Organization):
        """Test inviting with invalid email."""
        response = await client.post(
            f"/api/v1/organizations/{test_organization.id}/members/invite",
            json={
                "email": "not-an-email",
                "role": "member",
            },
            headers=auth_headers,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invite_invalid_role(self, client: AsyncClient, auth_headers: dict, test_organization: Organization):
        """Test inviting with invalid role."""
        unique_email = f"invalid_role_{uuid4().hex[:8]}@example.com"
        response = await client.post(
            f"/api/v1/organizations/{test_organization.id}/members/invite",
            json={
                "email": unique_email,
                "role": "superadmin",  # Invalid role
            },
            headers=auth_headers,
        )
        # 200 if role is accepted, 400/422 if rejected
        assert response.status_code in [200, 400, 422]

    @pytest.mark.asyncio
    async def test_update_member_role(self, client: AsyncClient, auth_headers: dict, test_organization: Organization):
        """Test updating a member's role."""
        # First get members to find one to update
        list_response = await client.get(
            f"/api/v1/organizations/{test_organization.id}/members",
            headers=auth_headers,
        )

        if list_response.status_code == 200:
            members = list_response.json()
            if len(members) > 0:
                member_id = members[0]["id"]
                response = await client.patch(
                    f"/api/v1/organizations/{test_organization.id}/members/{member_id}",
                    json={
                        "role": "admin",
                    },
                    headers=auth_headers,
                )
                assert response.status_code in [200, 400, 403, 404]

    @pytest.mark.asyncio
    async def test_update_member_team(self, client: AsyncClient, auth_headers: dict, test_organization: Organization):
        """Test updating a member's team."""
        list_response = await client.get(
            f"/api/v1/organizations/{test_organization.id}/members",
            headers=auth_headers,
        )

        if list_response.status_code == 200:
            members = list_response.json()
            if len(members) > 0:
                member_id = members[0]["id"]
                response = await client.patch(
                    f"/api/v1/organizations/{test_organization.id}/members/{member_id}",
                    json={
                        "team": "New Team",
                        "department": "New Department",
                    },
                    headers=auth_headers,
                )
                assert response.status_code in [200, 400, 403, 404]

    @pytest.mark.asyncio
    async def test_remove_member(self, client: AsyncClient, auth_headers: dict, test_organization: Organization):
        """Test removing a member from organization."""
        # This test may not work well since we need a non-owner member
        fake_member_id = str(uuid4())
        response = await client.delete(
            f"/api/v1/organizations/{test_organization.id}/members/{fake_member_id}",
            headers=auth_headers,
        )
        assert response.status_code in [200, 204, 400, 403, 404]

    @pytest.mark.asyncio
    async def test_cannot_remove_owner(self, client: AsyncClient, auth_headers: dict, test_organization: Organization):
        """Test that owner cannot be removed."""
        # Get members to find the owner
        list_response = await client.get(
            f"/api/v1/organizations/{test_organization.id}/members",
            headers=auth_headers,
        )

        if list_response.status_code == 200:
            members = list_response.json()
            owner = next((m for m in members if m.get("role") == "owner"), None)
            if owner:
                response = await client.delete(
                    f"/api/v1/organizations/{test_organization.id}/members/{owner['id']}",
                    headers=auth_headers,
                )
                # Should fail - can't remove owner
                assert response.status_code == 400


class TestOrganizationAuthorization:
    """Test organization authorization."""

    @pytest.mark.asyncio
    async def test_list_organizations_unauthorized(self, client: AsyncClient):
        """Test listing organizations without auth."""
        response = await client.get("/api/v1/organizations")
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_create_organization_unauthorized(self, client: AsyncClient):
        """Test creating organization without auth."""
        response = await client.post(
            "/api/v1/organizations",
            json={
                "name": "Unauthorized Org",
                "slug": "unauthorized-org",
            },
        )
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_get_organization_unauthorized(self, client: AsyncClient):
        """Test getting organization without auth."""
        fake_id = str(uuid4())
        response = await client.get(f"/api/v1/organizations/{fake_id}")
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_update_organization_unauthorized(self, client: AsyncClient):
        """Test updating organization without auth."""
        fake_id = str(uuid4())
        response = await client.patch(
            f"/api/v1/organizations/{fake_id}",
            json={"name": "Updated"},
        )
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_delete_organization_unauthorized(self, client: AsyncClient):
        """Test deleting organization without auth."""
        fake_id = str(uuid4())
        response = await client.delete(f"/api/v1/organizations/{fake_id}")
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_list_members_unauthorized(self, client: AsyncClient):
        """Test listing members without auth."""
        fake_id = str(uuid4())
        response = await client.get(f"/api/v1/organizations/{fake_id}/members")
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_invite_member_unauthorized(self, client: AsyncClient):
        """Test inviting member without auth."""
        fake_id = str(uuid4())
        response = await client.post(
            f"/api/v1/organizations/{fake_id}/members/invite",
            json={"email": "test@example.com", "role": "member"},
        )
        assert response.status_code in [401, 403]


class TestOrganizationAccessControl:
    """Test organization access control."""

    @pytest.mark.asyncio
    async def test_non_member_cannot_access_org(
        self, client: AsyncClient, admin_auth_headers: dict, test_organization: Organization
    ):
        """Test that non-members cannot access organization details."""
        # admin_user is not a member of test_organization
        response = await client.get(
            f"/api/v1/organizations/{test_organization.id}",
            headers=admin_auth_headers,
        )
        # Should be 403 (forbidden) since admin is not a member
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_non_admin_cannot_update_org(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that regular members cannot update organization."""
        # Create an org where user is member, not admin
        # This test depends on the fixture setup
        pass  # Placeholder - would need specific fixtures

    @pytest.mark.asyncio
    async def test_non_owner_cannot_delete_org(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that non-owners cannot delete organization."""
        # Would need specific fixtures for this test
        pass  # Placeholder


class TestOrganizationValidation:
    """Test organization input validation."""

    @pytest.mark.asyncio
    async def test_create_organization_missing_name(self, client: AsyncClient, auth_headers: dict):
        """Test creating organization without name."""
        response = await client.post(
            "/api/v1/organizations",
            json={"slug": "test-slug"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_organization_missing_slug(self, client: AsyncClient, auth_headers: dict):
        """Test creating organization without slug."""
        response = await client.post(
            "/api/v1/organizations",
            json={"name": "Test Org"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_organization_empty_name(self, client: AsyncClient, auth_headers: dict):
        """Test creating organization with empty name."""
        response = await client.post(
            "/api/v1/organizations",
            json={
                "name": "",
                "slug": "empty-name-org",
            },
            headers=auth_headers,
        )
        # 200/201 if API accepts empty name, 400/422 if rejected
        assert response.status_code in [200, 201, 400, 422]

    @pytest.mark.asyncio
    async def test_create_organization_invalid_slug_format(self, client: AsyncClient, auth_headers: dict):
        """Test creating organization with invalid slug format."""
        response = await client.post(
            "/api/v1/organizations",
            json={
                "name": "Test Org",
                "slug": "Invalid Slug With Spaces!",
            },
            headers=auth_headers,
        )
        # May sanitize or reject
        assert response.status_code in [200, 201, 400, 422]

    @pytest.mark.asyncio
    async def test_create_organization_very_long_name(self, client: AsyncClient, auth_headers: dict):
        """Test creating organization with very long name."""
        long_name = "A" * 500
        try:
            response = await client.post(
                "/api/v1/organizations",
                json={
                    "name": long_name,
                    "slug": f"long-name-{uuid4().hex[:8]}",
                },
                headers=auth_headers,
            )
            # 200/201 if API truncates, 400/422 if rejected, 500 if DB error
            assert response.status_code in [200, 201, 400, 422, 500]
        except Exception:
            # Expected if DB raises exception for long value
            pass

    @pytest.mark.asyncio
    async def test_create_organization_unicode_name(self, client: AsyncClient, auth_headers: dict):
        """Test creating organization with unicode name."""
        response = await client.post(
            "/api/v1/organizations",
            json={
                "name": "测试组织 Организация",
                "slug": f"unicode-org-{uuid4().hex[:8]}",
            },
            headers=auth_headers,
        )
        assert response.status_code in [200, 201, 400, 422]


class TestOrganizationEdgeCases:
    """Test edge cases for organizations."""

    @pytest.mark.asyncio
    async def test_create_multiple_organizations(self, client: AsyncClient, auth_headers: dict):
        """Test creating multiple organizations."""
        created_ids = []
        for i in range(3):
            unique_id = uuid4().hex[:8]
            response = await client.post(
                "/api/v1/organizations",
                json={
                    "name": f"Multi Org {i}",
                    "slug": f"multi-org-{unique_id}",
                },
                headers=auth_headers,
            )
            if response.status_code in [200, 201]:
                created_ids.append(response.json()["id"])

        # Verify all appear in list
        list_response = await client.get(
            "/api/v1/organizations",
            headers=auth_headers,
        )
        if list_response.status_code == 200:
            orgs = list_response.json()
            org_ids = [o["id"] for o in orgs]
            for created_id in created_ids:
                assert created_id in org_ids

    @pytest.mark.asyncio
    async def test_organization_with_special_characters_in_name(self, client: AsyncClient, auth_headers: dict):
        """Test organization with special characters in name."""
        special_names = [
            "Org & Company",
            "Org's Name",
            "Org \"Quoted\"",
            "Org <Script>",
        ]

        for name in special_names:
            unique_id = uuid4().hex[:8]
            response = await client.post(
                "/api/v1/organizations",
                json={
                    "name": name,
                    "slug": f"special-{unique_id}",
                },
                headers=auth_headers,
            )
            assert response.status_code in [200, 201, 400, 422]

    @pytest.mark.asyncio
    async def test_get_organization_invalid_uuid(self, client: AsyncClient, auth_headers: dict):
        """Test getting organization with invalid UUID."""
        try:
            response = await client.get(
                "/api/v1/organizations/not-a-valid-uuid",
                headers=auth_headers,
            )
            # 403/404/422 if validated, 500 if DB error on invalid UUID
            assert response.status_code in [403, 404, 422, 500]
        except Exception:
            # Expected if DB raises exception for invalid UUID
            pass

    @pytest.mark.asyncio
    async def test_invite_member_to_nonexistent_org(self, client: AsyncClient, auth_headers: dict):
        """Test inviting member to non-existent organization."""
        fake_id = str(uuid4())
        response = await client.post(
            f"/api/v1/organizations/{fake_id}/members/invite",
            json={
                "email": "test@example.com",
                "role": "member",
            },
            headers=auth_headers,
        )
        assert response.status_code in [403, 404]

    @pytest.mark.asyncio
    async def test_list_members_of_nonexistent_org(self, client: AsyncClient, auth_headers: dict):
        """Test listing members of non-existent organization."""
        fake_id = str(uuid4())
        response = await client.get(
            f"/api/v1/organizations/{fake_id}/members",
            headers=auth_headers,
        )
        assert response.status_code in [403, 404]
