"""GB063: M6 Adversarial Input Audit tests.

Tests for:
- Pickle deserialization replaced with JSON in cache
- ClickHouse SQL injection prevented via parameterized queries
- Path traversal blocked in local storage backend
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest


# ============================================================================
# 1. Cache: pickle.loads replaced with json.loads
# ============================================================================

class TestCacheJSONSerialization:
    """Verify cache uses JSON instead of pickle for (de)serialization."""

    def test_cache_module_does_not_import_pickle(self):
        import importlib
        import app.core.cache as cache_mod
        importlib.reload(cache_mod)
        source = Path(cache_mod.__file__).read_text()
        assert "pickle.loads" not in source
        assert "pickle.dumps" not in source

    @pytest.mark.asyncio
    async def test_cache_set_serializes_as_json(self):
        from app.core.cache import RedisCache
        cache = RedisCache()
        mock_client = AsyncMock()
        cache._client = mock_client
        cache._initialized = True

        await cache.set("test_key", {"foo": "bar"}, ttl=60)
        mock_client.setex.assert_awaited_once()
        _, args, _ = mock_client.setex.mock_calls[0]
        stored = args[2] if len(args) > 2 else mock_client.setex.call_args[0][2]
        parsed = json.loads(stored)
        assert parsed == {"foo": "bar"}

    @pytest.mark.asyncio
    async def test_cache_get_deserializes_json(self):
        from app.core.cache import RedisCache
        cache = RedisCache()
        mock_client = AsyncMock()
        mock_client.get.return_value = json.dumps({"hello": "world"}).encode()
        cache._client = mock_client
        cache._initialized = True

        result = await cache.get("test_key")
        assert result == {"hello": "world"}

    @pytest.mark.asyncio
    async def test_cache_rejects_pickle_payload(self):
        """If someone put a pickle payload in Redis, JSON deserialization fails safely."""
        import pickle
        from app.core.cache import RedisCache
        cache = RedisCache()
        mock_client = AsyncMock()
        mock_client.get.return_value = pickle.dumps({"evil": True})
        cache._client = mock_client
        cache._initialized = True

        result = await cache.get("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_set_handles_non_json_types(self):
        """datetime and other types are serialized via default=str."""
        from datetime import datetime, timezone
        from app.core.cache import RedisCache
        cache = RedisCache()
        mock_client = AsyncMock()
        cache._client = mock_client
        cache._initialized = True

        now = datetime.now(timezone.utc)
        result = await cache.set("dt_key", {"ts": now}, ttl=60)
        assert result is True
        stored = mock_client.setex.call_args[0][2]
        parsed = json.loads(stored)
        assert parsed["ts"] == str(now)


# ============================================================================
# 2. ClickHouse: SQL injection prevented via parameterized queries
# ============================================================================

class TestClickHouseSQLInjection:
    """Verify ClickHouse queries use parameterized placeholders."""

    def test_insert_api_request_uses_params(self):
        import inspect
        from app.services.analytics.clickhouse import ClickHouseService
        source = inspect.getsource(ClickHouseService.insert_api_request)
        assert "'{tenant_id}'" not in source
        assert "'{endpoint}'" not in source
        assert "'{user_agent}'" not in source
        assert "{tenant_id:UUID}" in source
        assert "{endpoint:String}" in source

    def test_insert_ai_usage_uses_params(self):
        import inspect
        from app.services.analytics.clickhouse import ClickHouseService
        source = inspect.getsource(ClickHouseService.insert_ai_usage)
        assert "'{tenant_id}'" not in source
        assert "'{tool}'" not in source
        assert "{tenant_id:UUID}" in source
        assert "{tool:String}" in source

    def test_insert_metrics_uses_params(self):
        import inspect
        from app.services.analytics.clickhouse import ClickHouseService
        source = inspect.getsource(ClickHouseService.insert_metrics)
        assert "'{tenant_id}'" not in source
        assert "{tenant_id:UUID}" in source

    def test_get_api_stats_uses_params(self):
        import inspect
        from app.services.analytics.clickhouse import ClickHouseService
        source = inspect.getsource(ClickHouseService.get_api_stats)
        assert "'{tenant_id}'" not in source
        assert "{tenant_id:UUID}" in source

    def test_get_dora_trend_uses_params(self):
        import inspect
        from app.services.analytics.clickhouse import ClickHouseService
        source = inspect.getsource(ClickHouseService.get_dora_trend)
        assert "'{tenant_id}'" not in source
        assert "{tenant_id:UUID}" in source

    def test_get_pipeline_stats_uses_params(self):
        import inspect
        from app.services.analytics.clickhouse import ClickHouseService
        source = inspect.getsource(ClickHouseService.get_pipeline_stats)
        assert "'{tenant_id}'" not in source
        assert "{tenant_id:UUID}" in source

    @pytest.mark.asyncio
    async def test_insert_api_request_passes_params_to_execute(self):
        from app.services.analytics.clickhouse import ClickHouseService
        service = ClickHouseService()
        service.execute = AsyncMock()

        await service.insert_api_request(
            tenant_id="550e8400-e29b-41d4-a716-446655440000",
            user_id="660e8400-e29b-41d4-a716-446655440000",
            endpoint="/api/v1/test'; DROP TABLE api_requests;--",
            method="GET",
            status_code=200,
            response_time_ms=42,
            user_agent="evil<script>alert(1)</script>",
            ip_address="127.0.0.1",
        )

        service.execute.assert_awaited_once()
        call_args = service.execute.call_args
        query = call_args[0][0]
        params = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("params")

        assert "'{endpoint}'" not in query
        assert params["param_endpoint"] == "/api/v1/test'; DROP TABLE api_requests;--"
        assert params["param_user_agent"] == "evil<script>alert(1)</script>"


# ============================================================================
# 3. Local storage: path traversal blocked
# ============================================================================

class TestLocalStoragePathTraversal:
    """Verify local storage rejects path traversal keys."""

    def test_rejects_dot_dot_traversal(self):
        from app.services.storage.local import LocalStorageBackend
        from app.services.storage.base import StorageConfig, StorageType

        config = StorageConfig(
            storage_type=StorageType.LOCAL,
            base_path="/tmp/test-uploads",
        )
        backend = LocalStorageBackend(config)

        with pytest.raises(ValueError, match="traversal"):
            backend._get_full_path("../../etc/passwd")

    def test_rejects_absolute_escape(self):
        from app.services.storage.local import LocalStorageBackend
        from app.services.storage.base import StorageConfig, StorageType

        config = StorageConfig(
            storage_type=StorageType.LOCAL,
            base_path="/tmp/test-uploads",
        )
        backend = LocalStorageBackend(config)

        with pytest.raises(ValueError, match="traversal"):
            backend._get_full_path("../../../etc/shadow")

    def test_accepts_valid_key(self):
        from app.services.storage.local import LocalStorageBackend
        from app.services.storage.base import StorageConfig, StorageType

        config = StorageConfig(
            storage_type=StorageType.LOCAL,
            base_path="/tmp/test-uploads",
        )
        backend = LocalStorageBackend(config)

        result = backend._get_full_path("user123/document.pdf")
        assert result.name == "document.pdf"
        assert "user123" in str(result)

    def test_rejects_encoded_traversal(self):
        from app.services.storage.local import LocalStorageBackend
        from app.services.storage.base import StorageConfig, StorageType

        config = StorageConfig(
            storage_type=StorageType.LOCAL,
            base_path="/tmp/test-uploads",
        )
        backend = LocalStorageBackend(config)

        with pytest.raises(ValueError, match="traversal"):
            backend._get_full_path("subdir/../../etc/passwd")
