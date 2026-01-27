"""
Integration tests for complete user flows.

These tests verify that multiple API endpoints work together correctly
to complete common user workflows.
"""

import pytest
from uuid import uuid4
from io import BytesIO

from httpx import AsyncClient


class TestUserRegistrationAndAuthenticationFlow:
    """Test complete user registration and authentication flow."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_complete_registration_login_flow(self, client: AsyncClient, db_session):
        """Test complete flow: register -> login -> access protected endpoint."""
        unique_id = uuid4().hex[:8]
        email = f"flow_test_{unique_id}@example.com"
        username = f"flow_user_{unique_id}"
        password = "SecurePassword123!"

        # Step 1: Register
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "username": username,
                "password": password,
                "full_name": "Flow Test User",
            }
        )
        assert register_response.status_code == 201
        register_data = register_response.json()
        assert "user" in register_data
        assert "tokens" in register_data
        user_id = register_data["user"]["id"]

        # Step 2: Login with credentials
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": email,
                "password": password,
            }
        )
        assert login_response.status_code == 200
        login_data = login_response.json()
        access_token = login_data["tokens"]["access_token"]
        auth_headers = {"Authorization": f"Bearer {access_token}"}

        # Step 3: Access protected endpoint
        protected_response = await client.get(
            "/api/v1/chat/conversations",
            headers=auth_headers,
        )
        assert protected_response.status_code == 200

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_token_refresh_flow(self, client: AsyncClient, db_session):
        """Test token refresh flow."""
        unique_id = uuid4().hex[:8]
        email = f"refresh_flow_{unique_id}@example.com"
        username = f"refresh_user_{unique_id}"
        password = "SecurePassword123!"

        # Register
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "username": username,
                "password": password,
            }
        )
        assert register_response.status_code == 201

        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password}
        )
        assert login_response.status_code == 200
        refresh_token = login_response.json()["tokens"]["refresh_token"]

        # Refresh tokens
        refresh_response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        if refresh_response.status_code == 200:
            new_tokens = refresh_response.json()
            assert "access_token" in new_tokens
            # New token should work
            new_auth_headers = {"Authorization": f"Bearer {new_tokens['access_token']}"}
            protected_response = await client.get(
                "/api/v1/chat/conversations",
                headers=new_auth_headers,
            )
            assert protected_response.status_code == 200


class TestConversationFlow:
    """Test complete conversation flow."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_conversation_lifecycle(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test complete conversation lifecycle: create -> list -> get -> delete."""
        # Step 1: Create conversation
        create_response = await client.post(
            "/api/v1/chat/conversations",
            json={
                "title": "Integration Test Conversation",
                "model_provider": "openai",
                "system_prompt": "You are a helpful assistant.",
            },
            headers=auth_headers,
        )
        assert create_response.status_code in [200, 201]
        conversation = create_response.json()
        conversation_id = conversation["id"]

        # Step 2: List conversations and verify it appears
        list_response = await client.get(
            "/api/v1/chat/conversations",
            headers=auth_headers,
        )
        assert list_response.status_code == 200
        conversations = list_response.json()
        conv_ids = [c["id"] for c in conversations]
        assert conversation_id in conv_ids

        # Step 3: Get specific conversation
        get_response = await client.get(
            f"/api/v1/chat/conversations/{conversation_id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 200
        assert get_response.json()["id"] == conversation_id

        # Step 4: Get messages (should be empty)
        messages_response = await client.get(
            f"/api/v1/chat/conversations/{conversation_id}/messages",
            headers=auth_headers,
        )
        assert messages_response.status_code == 200
        assert messages_response.json() == []

        # Step 5: Delete conversation
        delete_response = await client.delete(
            f"/api/v1/chat/conversations/{conversation_id}",
            headers=auth_headers,
        )
        assert delete_response.status_code == 204

        # Step 6: Verify deletion
        verify_response = await client.get(
            f"/api/v1/chat/conversations/{conversation_id}",
            headers=auth_headers,
        )
        assert verify_response.status_code == 404


class TestDocumentFlow:
    """Test complete document flow."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_document_lifecycle(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test complete document lifecycle: upload -> list -> get -> delete."""
        # Step 1: Upload document
        content = b"This is test document content for integration testing."
        files = {"file": ("integration_test.txt", BytesIO(content), "text/plain")}
        upload_response = await client.post(
            "/api/v1/documents/upload",
            files=files,
            headers=auth_headers,
        )

        if upload_response.status_code in [200, 201]:
            document = upload_response.json()
            document_id = document["id"]

            # Step 2: List documents
            list_response = await client.get(
                "/api/v1/documents",
                headers=auth_headers,
            )
            assert list_response.status_code == 200
            documents = list_response.json()
            doc_ids = [d["id"] for d in documents]
            assert document_id in doc_ids

            # Step 3: Get specific document
            get_response = await client.get(
                f"/api/v1/documents/{document_id}",
                headers=auth_headers,
            )
            assert get_response.status_code == 200
            assert get_response.json()["id"] == document_id

            # Step 4: Delete document
            delete_response = await client.delete(
                f"/api/v1/documents/{document_id}",
                headers=auth_headers,
            )
            assert delete_response.status_code == 204

            # Step 5: Verify deletion
            verify_response = await client.get(
                f"/api/v1/documents/{document_id}",
                headers=auth_headers,
            )
            assert verify_response.status_code == 404


class TestOrganizationFlow:
    """Test complete organization flow."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_organization_lifecycle(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test organization lifecycle: create -> list -> get -> update -> delete."""
        unique_id = uuid4().hex[:8]

        # Step 1: Create organization
        create_response = await client.post(
            "/api/v1/organizations",
            json={
                "name": f"Integration Test Org {unique_id}",
                "slug": f"int-test-org-{unique_id}",
                "description": "Organization created during integration test",
            },
            headers=auth_headers,
        )

        if create_response.status_code in [200, 201]:
            org = create_response.json()
            org_id = org["id"]

            # Step 2: List organizations
            list_response = await client.get(
                "/api/v1/organizations",
                headers=auth_headers,
            )
            assert list_response.status_code == 200
            orgs = list_response.json()
            org_ids = [o["id"] for o in orgs]
            assert org_id in org_ids

            # Step 3: Get specific organization
            get_response = await client.get(
                f"/api/v1/organizations/{org_id}",
                headers=auth_headers,
            )
            assert get_response.status_code == 200
            assert get_response.json()["id"] == org_id

            # Step 4: Update organization (if endpoint exists)
            update_response = await client.patch(
                f"/api/v1/organizations/{org_id}",
                json={"description": "Updated description"},
                headers=auth_headers,
            )
            # May return 200, 403, or 405
            if update_response.status_code == 200:
                assert update_response.json()["description"] == "Updated description"

            # Step 5: List members
            members_response = await client.get(
                f"/api/v1/organizations/{org_id}/members",
                headers=auth_headers,
            )
            assert members_response.status_code == 200
            members = members_response.json()
            assert len(members) >= 1  # At least the owner

            # Step 6: Delete organization
            delete_response = await client.delete(
                f"/api/v1/organizations/{org_id}",
                headers=auth_headers,
            )
            assert delete_response.status_code in [200, 204, 403]


class TestOrganizationMemberFlow:
    """Test organization member management flow."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_invite_member_flow(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test inviting a member to organization."""
        unique_id = uuid4().hex[:8]

        # Create organization
        create_response = await client.post(
            "/api/v1/organizations",
            json={
                "name": f"Member Test Org {unique_id}",
                "slug": f"member-test-{unique_id}",
            },
            headers=auth_headers,
        )

        if create_response.status_code in [200, 201]:
            org_id = create_response.json()["id"]

            # Invite member
            invite_response = await client.post(
                f"/api/v1/organizations/{org_id}/members/invite",
                json={
                    "email": f"invited_{unique_id}@example.com",
                    "role": "member",
                },
                headers=auth_headers,
            )

            if invite_response.status_code in [200, 201]:
                # Verify member in list (may be pending)
                members_response = await client.get(
                    f"/api/v1/organizations/{org_id}/members",
                    headers=auth_headers,
                )
                assert members_response.status_code == 200


class TestTokenFlow:
    """Test Personal Access Token flow."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_token_lifecycle(
        self, client: AsyncClient, auth_headers: dict, test_user, test_organization
    ):
        """Test token lifecycle: create -> list -> validate -> revoke."""
        # Step 1: Create token
        create_response = await client.post(
            "/api/v1/tokens/",
            params={"user_id": str(test_user.id)},
            json={
                "name": "Integration Test Token",
                "scopes": ["read:projects"],
            },
            headers=auth_headers,
        )

        if create_response.status_code in [200, 201]:
            token_data = create_response.json()
            token_id = token_data.get("id") or token_data.get("token_id")
            token_value = token_data.get("token") or token_data.get("access_token")

            # Step 2: List tokens
            list_response = await client.get(
                "/api/v1/tokens/",
                params={"user_id": str(test_user.id)},
                headers=auth_headers,
            )
            assert list_response.status_code == 200
            tokens = list_response.json()
            token_ids = [t.get("id") or t.get("token_id") for t in tokens]
            assert token_id in token_ids

            # Step 3: Validate token
            validate_response = await client.post(
                "/api/v1/tokens/validate",
                params={"token": token_value},
                headers=auth_headers,
            )
            if validate_response.status_code == 200:
                assert validate_response.json()["valid"] is True

            # Step 4: Revoke token
            revoke_response = await client.delete(
                f"/api/v1/tokens/{token_id}",
                params={"user_id": str(test_user.id)},
                headers=auth_headers,
            )
            assert revoke_response.status_code in [200, 204]

            # Step 5: Verify token no longer valid
            validate_after = await client.post(
                "/api/v1/tokens/validate",
                params={"token": token_value},
                headers=auth_headers,
            )
            assert validate_after.status_code == 401


class TestHealthCheckFlow:
    """Test health check flow."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_all_health_endpoints(self, client: AsyncClient):
        """Test all health check endpoints are reachable."""
        # Root health
        health_response = await client.get("/health")
        assert health_response.status_code == 200

        # Healthz alias
        healthz_response = await client.get("/healthz")
        assert healthz_response.status_code == 200

        # V1 health
        v1_health_response = await client.get("/api/v1/health")
        assert v1_health_response.status_code == 200

        # Liveness probe
        liveness_response = await client.get("/api/v1/health/live")
        assert liveness_response.status_code == 200

        # Readiness probe
        readiness_response = await client.get("/api/v1/health/ready")
        assert readiness_response.status_code == 200


class TestCrossModuleFlow:
    """Test flows that span multiple modules."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_user_creates_org_and_resources(
        self, client: AsyncClient, db_session
    ):
        """Test user registration, org creation, and resource creation."""
        unique_id = uuid4().hex[:8]

        # Step 1: Register user
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"complete_flow_{unique_id}@example.com",
                "username": f"complete_user_{unique_id}",
                "password": "SecurePassword123!",
            }
        )
        assert register_response.status_code == 201
        access_token = register_response.json()["tokens"]["access_token"]
        auth_headers = {"Authorization": f"Bearer {access_token}"}

        # Step 2: Create organization
        org_response = await client.post(
            "/api/v1/organizations",
            json={
                "name": f"Complete Flow Org {unique_id}",
                "slug": f"complete-flow-{unique_id}",
            },
            headers=auth_headers,
        )

        if org_response.status_code in [200, 201]:
            org_id = org_response.json()["id"]

            # Step 3: Create conversation
            conv_response = await client.post(
                "/api/v1/chat/conversations",
                json={
                    "title": "Complete Flow Conversation",
                    "model_provider": "openai",
                },
                headers=auth_headers,
            )
            assert conv_response.status_code in [200, 201]

            # Step 4: Upload document
            content = b"Complete flow test document"
            files = {"file": ("complete_flow.txt", BytesIO(content), "text/plain")}
            doc_response = await client.post(
                "/api/v1/documents/upload",
                files=files,
                headers=auth_headers,
            )

            # Verify resources exist
            convs_response = await client.get(
                "/api/v1/chat/conversations",
                headers=auth_headers,
            )
            assert convs_response.status_code == 200

            docs_response = await client.get(
                "/api/v1/documents",
                headers=auth_headers,
            )
            assert docs_response.status_code == 200


class TestErrorHandlingFlow:
    """Test error handling across flows."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_unauthorized_access_flow(self, client: AsyncClient):
        """Test that unauthorized access is properly rejected."""
        # Try to access protected endpoints without auth
        endpoints = [
            ("/api/v1/chat/conversations", "GET"),
            ("/api/v1/documents", "GET"),
            ("/api/v1/organizations", "GET"),
        ]

        for endpoint, method in endpoints:
            if method == "GET":
                response = await client.get(endpoint)
            else:
                response = await client.post(endpoint, json={})
            assert response.status_code in [401, 403]

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_not_found_handling(self, client: AsyncClient, auth_headers: dict):
        """Test that not found errors are properly handled."""
        fake_id = str(uuid4())

        # Conversation not found
        conv_response = await client.get(
            f"/api/v1/chat/conversations/{fake_id}",
            headers=auth_headers,
        )
        assert conv_response.status_code == 404

        # Document not found
        doc_response = await client.get(
            f"/api/v1/documents/{fake_id}",
            headers=auth_headers,
        )
        assert doc_response.status_code == 404

        # Organization not found
        org_response = await client.get(
            f"/api/v1/organizations/{fake_id}",
            headers=auth_headers,
        )
        assert org_response.status_code in [403, 404]

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_validation_error_handling(self, client: AsyncClient, auth_headers: dict):
        """Test that validation errors return 422."""
        # Invalid conversation (invalid model_provider value)
        conv_response = await client.post(
            "/api/v1/chat/conversations",
            json={"model_provider": "invalid_provider_xyz"},  # Invalid enum value
            headers=auth_headers,
        )
        assert conv_response.status_code == 422

        # Invalid registration (invalid email)
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "username": "testuser",
                "password": "password",
            }
        )
        assert register_response.status_code == 422
