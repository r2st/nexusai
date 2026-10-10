"""Unit tests for guardrails health reporting."""

from unittest.mock import AsyncMock, patch

import pytest

from app.api.health import detailed_health_check


@pytest.mark.asyncio
async def test_detailed_health_reports_nemo_misconfigured():
    with (
        patch("app.api.health.settings") as mock_settings,
        patch("app.core.database.check_db_health", new=AsyncMock(return_value={"status": "healthy"})),
        patch("app.core.cache.cache") as mock_cache,
    ):
        mock_settings.APP_VERSION = "1.0.0"
        mock_settings.ENVIRONMENT = "test"
        mock_settings.GUARDRAILS_ENABLED = True
        mock_settings.NEMO_GUARDRAILS_ENABLED = True
        mock_settings.NEMO_GUARDRAILS_CONFIG_PATH = None
        mock_cache.health_check = AsyncMock(return_value={"status": "healthy"})

        response = await detailed_health_check()
        guardrails = response.checks["guardrails"]

        assert guardrails["status"] == "degraded"
        assert guardrails["nemo_status"] == "misconfigured"


@pytest.mark.asyncio
async def test_detailed_health_reports_nemo_not_initialized_as_healthy():
    with (
        patch("app.api.health.settings") as mock_settings,
        patch("app.core.database.check_db_health", new=AsyncMock(return_value={"status": "healthy"})),
        patch("app.core.cache.cache") as mock_cache,
    ):
        mock_settings.APP_VERSION = "1.0.0"
        mock_settings.ENVIRONMENT = "test"
        mock_settings.GUARDRAILS_ENABLED = True
        mock_settings.NEMO_GUARDRAILS_ENABLED = True
        mock_settings.NEMO_GUARDRAILS_CONFIG_PATH = "/tmp/guardrails"
        mock_cache.health_check = AsyncMock(return_value={"status": "healthy"})

        with patch("app.api.health.get_nemo_guardrails_adapter") as mock_get_adapter:
            mock_get_adapter.return_value = type("A", (), {"is_ready": False})()
            response = await detailed_health_check()

        guardrails = response.checks["guardrails"]
        assert guardrails["status"] == "healthy"
        assert guardrails["nemo_status"] == "not_initialized"
