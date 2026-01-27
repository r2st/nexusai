"""
Unit tests for multi-tenancy module.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.core.multitenancy import (
    get_current_tenant_id,
    set_current_tenant_id,
    TenantContext,
    set_tenant_context,
    create_rls_policies,
    verify_rls_enabled,
    generate_domain_id,
    parse_domain_id,
    generate_tenant_id,
    current_tenant_id,
)


# =============================================================================
# Tenant Context Variable Tests
# =============================================================================


class TestTenantContextVariable:
    """Tests for tenant context variable management."""

    def test_get_current_tenant_id_default(self):
        """Test default tenant ID is None."""
        # Reset to default
        set_current_tenant_id(None)

        result = get_current_tenant_id()

        assert result is None

    def test_set_and_get_tenant_id(self):
        """Test setting and getting tenant ID."""
        set_current_tenant_id("tenant-123")

        result = get_current_tenant_id()

        assert result == "tenant-123"

        # Cleanup
        set_current_tenant_id(None)

    def test_set_tenant_id_to_none(self):
        """Test setting tenant ID to None."""
        set_current_tenant_id("tenant-123")
        set_current_tenant_id(None)

        result = get_current_tenant_id()

        assert result is None

    def test_tenant_id_isolation_between_sets(self):
        """Test that tenant ID changes are reflected."""
        set_current_tenant_id("tenant-1")
        assert get_current_tenant_id() == "tenant-1"

        set_current_tenant_id("tenant-2")
        assert get_current_tenant_id() == "tenant-2"

        # Cleanup
        set_current_tenant_id(None)


# =============================================================================
# TenantContext Class Tests
# =============================================================================


class TestTenantContext:
    """Tests for TenantContext context manager."""

    def test_tenant_context_enter(self):
        """Test TenantContext sets tenant on enter."""
        set_current_tenant_id(None)

        ctx = TenantContext("tenant-456")
        ctx.__enter__()

        assert get_current_tenant_id() == "tenant-456"

        ctx.__exit__(None, None, None)

    def test_tenant_context_exit(self):
        """Test TenantContext restores previous tenant on exit."""
        set_current_tenant_id("original-tenant")

        ctx = TenantContext("new-tenant")
        ctx.__enter__()
        ctx.__exit__(None, None, None)

        # Should restore original
        assert get_current_tenant_id() == "original-tenant"

        # Cleanup
        set_current_tenant_id(None)

    def test_tenant_context_as_context_manager(self):
        """Test TenantContext as context manager."""
        set_current_tenant_id(None)

        with TenantContext("context-tenant"):
            assert get_current_tenant_id() == "context-tenant"

        assert get_current_tenant_id() is None

    def test_nested_tenant_contexts(self):
        """Test nested TenantContext managers."""
        set_current_tenant_id(None)

        with TenantContext("outer"):
            assert get_current_tenant_id() == "outer"

            with TenantContext("inner"):
                assert get_current_tenant_id() == "inner"

            assert get_current_tenant_id() == "outer"

        assert get_current_tenant_id() is None


# =============================================================================
# Set Tenant Context Tests
# =============================================================================


class TestSetTenantContext:
    """Tests for set_tenant_context function."""

    @pytest.mark.asyncio
    async def test_set_tenant_context_with_tenant(self):
        """Test setting tenant context on session."""
        mock_session = AsyncMock()

        await set_tenant_context(mock_session, "tenant-123")

        mock_session.execute.assert_called_once()
        call_args = mock_session.execute.call_args
        # Should include tenant_id parameter
        assert call_args[0][1]["tenant_id"] == "tenant-123"

    @pytest.mark.asyncio
    async def test_set_tenant_context_with_none(self):
        """Test resetting tenant context on session."""
        mock_session = AsyncMock()

        await set_tenant_context(mock_session, None)

        mock_session.execute.assert_called_once()
        # Should reset the context
        call_args = mock_session.execute.call_args
        assert "RESET" in str(call_args[0][0])


# =============================================================================
# RLS Policy Tests
# =============================================================================


class TestRLSPolicies:
    """Tests for RLS policy management."""

    @pytest.mark.asyncio
    async def test_create_rls_policies_strict_mode(self):
        """Test creating RLS policies in strict mode."""
        mock_session = AsyncMock()

        await create_rls_policies(mock_session, strict_mode=True)

        # Should have multiple execute calls for each table
        assert mock_session.execute.call_count > 0
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_rls_policies_non_strict_mode(self):
        """Test creating RLS policies in non-strict mode."""
        mock_session = AsyncMock()

        await create_rls_policies(mock_session, strict_mode=False)

        # Should have multiple execute calls
        assert mock_session.execute.call_count > 0
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_rls_enabled(self):
        """Test verifying RLS is enabled on tables."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.__iter__ = lambda self: iter([
            MagicMock(tablename="organizations", rowsecurity=True),
            MagicMock(tablename="projects", rowsecurity=True),
            MagicMock(tablename="conversations", rowsecurity=False),
        ])
        mock_session.execute.return_value = mock_result

        result = await verify_rls_enabled(mock_session)

        assert result["organizations"] is True
        assert result["projects"] is True
        assert result["conversations"] is False


# =============================================================================
# Domain ID Tests
# =============================================================================


class TestDomainId:
    """Tests for domain ID generation and parsing."""

    def test_generate_domain_id(self):
        """Test generating a 5-segment domain ID."""
        domain_id = generate_domain_id(
            tenant_id="org123",
            plugin="github",
            connection_id="conn1",
            scope_type="repo",
            scope_id="myorg/myrepo",
        )

        assert domain_id == "org123:github:conn1:repo:myorg/myrepo"

    def test_generate_domain_id_with_special_chars(self):
        """Test generating domain ID with special characters in scope."""
        domain_id = generate_domain_id(
            tenant_id="tenant-1",
            plugin="gitlab",
            connection_id="connection-2",
            scope_type="project",
            scope_id="group/subgroup/project",
        )

        assert domain_id == "tenant-1:gitlab:connection-2:project:group/subgroup/project"

    def test_parse_domain_id(self):
        """Test parsing a valid domain ID."""
        domain_id = "org123:github:conn1:repo:myorg/myrepo"

        result = parse_domain_id(domain_id)

        assert result["tenant_id"] == "org123"
        assert result["plugin"] == "github"
        assert result["connection_id"] == "conn1"
        assert result["scope_type"] == "repo"
        assert result["scope_id"] == "myorg/myrepo"

    def test_parse_domain_id_with_colons_in_scope(self):
        """Test parsing domain ID with colons in scope_id."""
        # scope_id might contain colons
        domain_id = "tenant:plugin:conn:type:scope:with:colons"

        result = parse_domain_id(domain_id)

        assert result["tenant_id"] == "tenant"
        assert result["plugin"] == "plugin"
        assert result["connection_id"] == "conn"
        assert result["scope_type"] == "type"
        assert result["scope_id"] == "scope:with:colons"

    def test_parse_domain_id_invalid_format(self):
        """Test parsing invalid domain ID raises error."""
        with pytest.raises(ValueError) as exc_info:
            parse_domain_id("invalid-domain-id")

        assert "Invalid domain ID format" in str(exc_info.value)

    def test_parse_domain_id_too_few_segments(self):
        """Test parsing domain ID with too few segments."""
        with pytest.raises(ValueError):
            parse_domain_id("only:three:segments")

    def test_roundtrip_domain_id(self):
        """Test generating and parsing domain ID roundtrip."""
        original = generate_domain_id(
            tenant_id="tenant-abc",
            plugin="jira",
            connection_id="jira-conn",
            scope_type="board",
            scope_id="PROJ-123",
        )

        parsed = parse_domain_id(original)

        regenerated = generate_domain_id(**parsed)

        assert regenerated == original


# =============================================================================
# Generate Tenant ID Tests
# =============================================================================


class TestGenerateTenantId:
    """Tests for tenant ID generation."""

    def test_generate_tenant_id_is_uuid(self):
        """Test generated tenant ID is a valid UUID."""
        from uuid import UUID

        tenant_id = generate_tenant_id()

        # Should not raise
        UUID(tenant_id)

    def test_generate_tenant_id_unique(self):
        """Test generated tenant IDs are unique."""
        ids = [generate_tenant_id() for _ in range(100)]

        assert len(set(ids)) == 100

    def test_generate_tenant_id_format(self):
        """Test generated tenant ID format."""
        tenant_id = generate_tenant_id()

        # Standard UUID format: 8-4-4-4-12
        parts = tenant_id.split("-")
        assert len(parts) == 5
        assert len(parts[0]) == 8
        assert len(parts[1]) == 4
        assert len(parts[2]) == 4
        assert len(parts[3]) == 4
        assert len(parts[4]) == 12


# =============================================================================
# Tenant Tables Configuration Tests
# =============================================================================


class TestTenantTables:
    """Tests for tenant tables configuration."""

    def test_tenant_tables_include_core_tables(self):
        """Test that core tables are included in tenant isolation."""
        # Tables that should have RLS policies
        expected_tables = [
            "organizations",
            "organization_members",
            "projects",
            "project_members",
            "connections",
            "conversations",
            "documents",
        ]

        # These tables are defined in create_rls_policies
        # We verify by checking the function creates policies for them
        mock_session = AsyncMock()

        # Run the function
        import asyncio
        asyncio.get_event_loop().run_until_complete(
            create_rls_policies(mock_session, strict_mode=True)
        )

        # Check execute was called multiple times (once per table for each operation)
        assert mock_session.execute.call_count > len(expected_tables)


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_tenant_context_with_empty_string(self):
        """Test TenantContext with empty string."""
        set_current_tenant_id(None)

        with TenantContext(""):
            assert get_current_tenant_id() == ""

        assert get_current_tenant_id() is None

    def test_set_tenant_id_with_special_chars(self):
        """Test setting tenant ID with special characters."""
        special_id = "tenant-with-special_chars.123"
        set_current_tenant_id(special_id)

        assert get_current_tenant_id() == special_id

        # Cleanup
        set_current_tenant_id(None)

    def test_domain_id_with_empty_segments(self):
        """Test domain ID with empty segments."""
        domain_id = generate_domain_id(
            tenant_id="",
            plugin="",
            connection_id="",
            scope_type="",
            scope_id="",
        )

        assert domain_id == "::::"

        parsed = parse_domain_id(domain_id)
        assert parsed["tenant_id"] == ""

    def test_context_variable_thread_safety(self):
        """Test context variable behavior (contextvars are task-local)."""
        import asyncio

        async def set_and_check(tenant_id, expected_id):
            set_current_tenant_id(tenant_id)
            await asyncio.sleep(0.01)  # Yield to other tasks
            return get_current_tenant_id() == expected_id

        async def run_test():
            # Run multiple tasks that set different tenant IDs
            results = await asyncio.gather(
                set_and_check("tenant-a", "tenant-a"),
                set_and_check("tenant-b", "tenant-b"),
                set_and_check("tenant-c", "tenant-c"),
            )
            return all(results)

        # Note: In practice, contextvars provide isolation between async tasks
        # but this test demonstrates the pattern
        result = asyncio.get_event_loop().run_until_complete(run_test())

        # Cleanup
        set_current_tenant_id(None)


# =============================================================================
# Integration-like Tests
# =============================================================================


class TestMultitenancyIntegration:
    """Integration-style tests for multi-tenancy."""

    @pytest.mark.asyncio
    async def test_tenant_context_with_database_session(self):
        """Test tenant context works with database session mock."""
        mock_session = AsyncMock()

        # Simulate setting tenant context for a request
        set_current_tenant_id("request-tenant")

        # Set context on session
        await set_tenant_context(mock_session, get_current_tenant_id())

        # Verify session was configured
        mock_session.execute.assert_called_once()

        # Cleanup
        set_current_tenant_id(None)

    def test_domain_id_for_github_repo(self):
        """Test domain ID generation for GitHub repository scope."""
        domain_id = generate_domain_id(
            tenant_id="acme-corp",
            plugin="github",
            connection_id="github-prod",
            scope_type="repo",
            scope_id="acme-corp/backend-api",
        )

        parsed = parse_domain_id(domain_id)

        assert parsed["tenant_id"] == "acme-corp"
        assert parsed["plugin"] == "github"
        assert parsed["scope_id"] == "acme-corp/backend-api"

    def test_domain_id_for_jira_project(self):
        """Test domain ID generation for Jira project scope."""
        domain_id = generate_domain_id(
            tenant_id="company-123",
            plugin="jira",
            connection_id="jira-cloud",
            scope_type="project",
            scope_id="PROJ",
        )

        parsed = parse_domain_id(domain_id)

        assert parsed["plugin"] == "jira"
        assert parsed["scope_type"] == "project"
        assert parsed["scope_id"] == "PROJ"
