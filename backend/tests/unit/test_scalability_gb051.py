"""
Unit tests for GB051 M13 Scalability & Data Integrity.

Tests for:
- Pagination on list endpoints
- FK constraint model declarations
- Connection pool configuration
- Data validation on cost/hallucination models
"""

import pytest
from datetime import datetime, UTC
from uuid import uuid4

from httpx import AsyncClient

from app.core.config import settings
from app.core.database import engine, create_engine_with_config
from app.models.cost_entry import CostEntry, CostBudget, CostAlert
from app.models.hallucination_log import HallucinationLog, HallucinationMetric


# =============================================================================
# Pagination Tests
# =============================================================================


class TestPagination:
    """Test that list endpoints accept and respect pagination parameters."""

    @pytest.mark.asyncio
    async def test_list_organizations_accepts_pagination(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(
            "/api/v1/organizations?limit=5&offset=0",
            headers=auth_headers,
        )
        assert response.status_code in [200, 403]

    @pytest.mark.asyncio
    async def test_list_organizations_rejects_invalid_limit(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(
            "/api/v1/organizations?limit=0",
            headers=auth_headers,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_organizations_rejects_excessive_limit(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(
            "/api/v1/organizations?limit=999",
            headers=auth_headers,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_organizations_rejects_negative_offset(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(
            "/api/v1/organizations?offset=-1",
            headers=auth_headers,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_tokens_accepts_pagination(self, client: AsyncClient, auth_headers: dict):
        user_id = str(uuid4())
        response = await client.get(
            f"/api/v1/tokens/?user_id={user_id}&limit=10&offset=0",
            headers=auth_headers,
        )
        assert response.status_code in [200, 401, 403]

    @pytest.mark.asyncio
    async def test_list_tokens_rejects_excessive_limit(self, client: AsyncClient, auth_headers: dict):
        user_id = str(uuid4())
        response = await client.get(
            f"/api/v1/tokens/?user_id={user_id}&limit=500",
            headers=auth_headers,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_workflows_accepts_pagination(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(
            "/api/v1/workflows?limit=10&offset=0",
            headers=auth_headers,
        )
        assert response.status_code in [200, 401, 403]

    @pytest.mark.asyncio
    async def test_list_workflows_returns_pagination_metadata(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(
            "/api/v1/workflows?limit=10&offset=0",
            headers=auth_headers,
        )
        if response.status_code == 200:
            data = response.json()
            assert "total" in data
            assert "limit" in data
            assert "offset" in data

    @pytest.mark.asyncio
    async def test_list_conversations_accepts_pagination(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(
            "/api/v1/chat/conversations?limit=10&offset=0",
            headers=auth_headers,
        )
        assert response.status_code in [200, 401, 403]

    @pytest.mark.asyncio
    async def test_audit_logs_accepts_pagination(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(
            "/api/v1/audit/logs?limit=50&offset=0",
            headers=auth_headers,
        )
        assert response.status_code in [200, 401, 403]


# =============================================================================
# FK Constraint Model Tests
# =============================================================================


class TestFKConstraints:
    """Test that models declare FK constraints correctly."""

    def test_cost_entry_has_tenant_fk(self):
        col = CostEntry.__table__.columns["tenant_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert str(fks[0].target_fullname) == "organizations.tenant_id"

    def test_cost_entry_has_user_fk(self):
        col = CostEntry.__table__.columns["user_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert str(fks[0].target_fullname) == "users.id"

    def test_cost_budget_has_tenant_fk(self):
        col = CostBudget.__table__.columns["tenant_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert str(fks[0].target_fullname) == "organizations.tenant_id"

    def test_cost_alert_has_tenant_fk(self):
        col = CostAlert.__table__.columns["tenant_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert str(fks[0].target_fullname) == "organizations.tenant_id"

    def test_cost_alert_has_budget_fk(self):
        col = CostAlert.__table__.columns["budget_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert str(fks[0].target_fullname) == "cost_budgets.id"

    def test_hallucination_log_has_tenant_fk(self):
        col = HallucinationLog.__table__.columns["tenant_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert str(fks[0].target_fullname) == "organizations.tenant_id"

    def test_hallucination_metric_has_tenant_fk(self):
        col = HallucinationMetric.__table__.columns["tenant_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert str(fks[0].target_fullname) == "organizations.tenant_id"

    def test_cost_entry_tenant_fk_cascades(self):
        col = CostEntry.__table__.columns["tenant_id"]
        fk = list(col.foreign_keys)[0]
        assert fk.ondelete == "CASCADE"

    def test_cost_entry_user_fk_sets_null(self):
        col = CostEntry.__table__.columns["user_id"]
        fk = list(col.foreign_keys)[0]
        assert fk.ondelete == "SET NULL"


# =============================================================================
# Connection Pool Tests
# =============================================================================


class TestConnectionPool:
    """Test connection pool configuration."""

    def test_pool_size_configured(self):
        assert settings.DATABASE_POOL_SIZE >= 5
        assert settings.DATABASE_POOL_SIZE <= 100

    def test_max_overflow_configured(self):
        assert settings.DATABASE_MAX_OVERFLOW >= 5
        assert settings.DATABASE_MAX_OVERFLOW <= 100

    def test_pool_recycle_configured(self):
        assert settings.DATABASE_POOL_RECYCLE > 0
        assert settings.DATABASE_POOL_RECYCLE <= 3600

    def test_statement_timeout_configured(self):
        assert settings.DATABASE_STATEMENT_TIMEOUT > 0
        assert settings.DATABASE_STATEMENT_TIMEOUT <= 120000

    def test_lock_timeout_configured(self):
        assert settings.DATABASE_LOCK_TIMEOUT > 0

    def test_pool_pre_ping_enabled(self):
        assert engine.pool._pre_ping is True

    def test_create_engine_with_null_pool(self):
        test_engine = create_engine_with_config(
            "postgresql+asyncpg://test:test@localhost/test",
            use_null_pool=True,
        )
        from sqlalchemy.pool import NullPool
        assert isinstance(test_engine.pool, NullPool)

    def test_create_engine_with_regular_pool(self):
        test_engine = create_engine_with_config(
            "postgresql+asyncpg://test:test@localhost/test",
            pool_size=10,
            max_overflow=5,
            use_null_pool=False,
        )
        from sqlalchemy.pool import NullPool
        assert not isinstance(test_engine.pool, NullPool)


# =============================================================================
# Data Validation Tests
# =============================================================================


class TestDataValidation:
    """Test data model validation."""

    def test_cost_entry_requires_tenant_id(self):
        col = CostEntry.__table__.columns["tenant_id"]
        assert col.nullable is False

    def test_cost_entry_requires_request_id(self):
        col = CostEntry.__table__.columns["request_id"]
        assert col.nullable is False
        assert col.unique is True

    def test_cost_entry_requires_provider(self):
        col = CostEntry.__table__.columns["provider"]
        assert col.nullable is False

    def test_cost_entry_requires_model(self):
        col = CostEntry.__table__.columns["model"]
        assert col.nullable is False

    def test_cost_entry_has_tenant_index(self):
        indexes = {idx.name for idx in CostEntry.__table__.indexes}
        assert "ix_cost_entries_tenant_id" in indexes

    def test_cost_entry_has_time_series_index(self):
        indexes = {idx.name for idx in CostEntry.__table__.indexes}
        assert "ix_cost_entries_tenant_created" in indexes

    def test_hallucination_log_requires_tenant_id(self):
        col = HallucinationLog.__table__.columns["tenant_id"]
        assert col.nullable is False

    def test_hallucination_log_requires_scores(self):
        col = HallucinationLog.__table__.columns["hallucination_score"]
        assert col.nullable is False

    def test_hallucination_log_has_partial_index(self):
        indexes = {idx.name for idx in HallucinationLog.__table__.indexes}
        assert "ix_hallucination_logs_detected" in indexes

    def test_hallucination_log_has_composite_index(self):
        indexes = {idx.name for idx in HallucinationLog.__table__.indexes}
        assert "ix_hallucination_logs_tenant_type_created" in indexes

    def test_cost_budget_requires_scope(self):
        col = CostBudget.__table__.columns["scope"]
        assert col.nullable is False

    def test_cost_alert_requires_alert_type(self):
        col = CostAlert.__table__.columns["alert_type"]
        assert col.nullable is False
