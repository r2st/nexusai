"""
Unit tests for application configuration.
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from app.core.config import Settings, get_settings


class TestSettingsBasic:
    """Tests for basic Settings functionality."""

    def test_settings_loads_from_environment(self):
        """Test that settings loads from environment variables."""
        settings = get_settings()

        # Basic settings should be available
        assert settings.APP_NAME == "NexusAI"
        assert settings.API_PREFIX == "/api/v1"

    def test_settings_has_required_fields(self):
        """Test that required fields are present."""
        settings = get_settings()

        assert hasattr(settings, 'SECRET_KEY')
        assert hasattr(settings, 'DATABASE_HOST')
        assert hasattr(settings, 'REDIS_HOST')

    def test_settings_default_values(self):
        """Test that default values are set correctly."""
        settings = get_settings()

        assert settings.DEBUG is False or settings.DEBUG is True
        assert settings.PORT == 8000
        assert settings.WORKERS == 4
        assert settings.ALGORITHM == "HS256"

    def test_settings_cors_origins(self):
        """Test CORS configuration."""
        settings = get_settings()

        assert isinstance(settings.CORS_ORIGINS, list)
        assert settings.CORS_ALLOW_CREDENTIALS is True


class TestSettingsDatabaseConfiguration:
    """Tests for database configuration."""

    def test_database_url_built_from_components(self):
        """Test DATABASE_URL is built from components."""
        settings = get_settings()

        if settings.DATABASE_URL:
            assert "postgresql" in settings.DATABASE_URL
            assert settings.DATABASE_HOST in settings.DATABASE_URL

    def test_database_pool_settings(self):
        """Test database pool settings."""
        settings = get_settings()

        assert settings.DATABASE_POOL_SIZE > 0
        assert settings.DATABASE_MAX_OVERFLOW >= 0


class TestSettingsRedisConfiguration:
    """Tests for Redis configuration."""

    def test_redis_url_built_from_components(self):
        """Test REDIS_URL is built from components."""
        settings = get_settings()

        if settings.REDIS_URL:
            assert "redis://" in settings.REDIS_URL
            assert str(settings.REDIS_PORT) in settings.REDIS_URL

    def test_redis_default_db(self):
        """Test Redis default database."""
        settings = get_settings()

        assert settings.REDIS_DB >= 0


class TestSettingsAuthConfiguration:
    """Tests for authentication configuration."""

    def test_access_token_expiry(self):
        """Test access token expiry settings."""
        settings = get_settings()

        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES > 0
        assert settings.REFRESH_TOKEN_EXPIRE_DAYS > 0

    def test_oauth_providers_optional(self):
        """Test OAuth providers are optional."""
        settings = get_settings()

        # These should be None or strings
        assert settings.GOOGLE_CLIENT_ID is None or isinstance(settings.GOOGLE_CLIENT_ID, str)
        assert settings.GITHUB_CLIENT_ID is None or isinstance(settings.GITHUB_CLIENT_ID, str)


class TestSettingsAIProviders:
    """Tests for AI provider configuration."""

    def test_ai_providers_optional(self):
        """Test AI provider keys are optional."""
        settings = get_settings()

        assert settings.OPENAI_API_KEY is None or isinstance(settings.OPENAI_API_KEY, str)
        assert settings.ANTHROPIC_API_KEY is None or isinstance(settings.ANTHROPIC_API_KEY, str)

    def test_default_models(self):
        """Test default model settings."""
        settings = get_settings()

        assert settings.OPENAI_DEFAULT_MODEL is not None
        assert settings.ANTHROPIC_DEFAULT_MODEL is not None


class TestSettingsFileUpload:
    """Tests for file upload configuration."""

    def test_max_upload_size(self):
        """Test max upload size setting."""
        settings = get_settings()

        assert settings.MAX_UPLOAD_SIZE > 0
        assert settings.MAX_UPLOAD_SIZE == 50 * 1024 * 1024  # 50MB

    def test_allowed_extensions(self):
        """Test allowed file extensions."""
        settings = get_settings()

        assert isinstance(settings.ALLOWED_EXTENSIONS, list)
        assert ".pdf" in settings.ALLOWED_EXTENSIONS
        assert ".docx" in settings.ALLOWED_EXTENSIONS


class TestSettingsRateLimiting:
    """Tests for rate limiting configuration."""

    def test_rate_limit_settings(self):
        """Test rate limit settings."""
        settings = get_settings()

        assert settings.RATE_LIMIT_PER_MINUTE > 0
        assert settings.RATE_LIMIT_PER_HOUR > 0
        assert settings.PER_TENANT_RATE_LIMIT > 0


class TestSettingsTierLimits:
    """Tests for subscription tier limits."""

    def test_tier_limits_ordered(self):
        """Test that tier limits are ordered correctly."""
        settings = get_settings()

        # Higher tiers should have more resources
        assert settings.FREE_TIER_MAX_MEMBERS <= settings.STARTER_TIER_MAX_MEMBERS
        assert settings.STARTER_TIER_MAX_MEMBERS <= settings.PROFESSIONAL_TIER_MAX_MEMBERS
        assert settings.PROFESSIONAL_TIER_MAX_MEMBERS <= settings.ENTERPRISE_TIER_MAX_MEMBERS


class TestSettingsFeatureFlags:
    """Tests for feature flag configuration."""

    def test_feature_flags_are_booleans(self):
        """Test feature flags are boolean values."""
        settings = get_settings()

        assert isinstance(settings.FEATURE_AI_ANALYTICS, bool)
        assert isinstance(settings.FEATURE_CODE_SIMILARITY, bool)
        assert isinstance(settings.FEATURE_CODE_INTERPRETER, bool)


class TestSettingsEnvironmentHelpers:
    """Tests for environment helper properties."""

    def test_is_development_property(self):
        """Test is_development property."""
        settings = get_settings()

        if settings.ENVIRONMENT == "development":
            assert settings.is_development is True
            assert settings.is_production is False

    def test_is_production_property(self):
        """Test is_production property."""
        settings = get_settings()

        if settings.ENVIRONMENT == "production":
            assert settings.is_production is True
            assert settings.is_development is False


class TestGetSettingsCaching:
    """Tests for settings caching."""

    def test_get_settings_returns_same_instance(self):
        """Test that get_settings returns cached instance."""
        settings1 = get_settings()
        settings2 = get_settings()

        # Should be the same object due to lru_cache
        assert settings1 is settings2

    def test_settings_cache_can_be_cleared(self):
        """Test that settings cache can be cleared."""
        get_settings.cache_clear()

        # Should not raise
        settings = get_settings()
        assert settings is not None


class TestSettingsValidation:
    """Tests for settings validation."""

    def test_database_url_validator(self):
        """Test database URL is properly formatted."""
        settings = get_settings()

        if settings.DATABASE_URL:
            # Should be a valid PostgreSQL URL
            assert settings.DATABASE_URL.startswith("postgresql")

    def test_redis_url_validator(self):
        """Test Redis URL is properly formatted."""
        settings = get_settings()

        if settings.REDIS_URL:
            # Should be a valid Redis URL
            assert settings.REDIS_URL.startswith("redis://")


class TestSettingsSecurityConfiguration:
    """Tests for security-related configuration."""

    def test_secret_key_exists(self):
        """Test that SECRET_KEY is set."""
        settings = get_settings()

        assert settings.SECRET_KEY is not None
        assert len(settings.SECRET_KEY) >= 32

    def test_algorithm_is_valid(self):
        """Test JWT algorithm is valid."""
        settings = get_settings()

        valid_algorithms = ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"]
        assert settings.ALGORITHM in valid_algorithms


class TestSettingsCloudStorage:
    """Tests for cloud storage configuration."""

    def test_s3_settings_optional(self):
        """Test S3 settings are optional."""
        settings = get_settings()

        assert settings.S3_BUCKET_NAME is None or isinstance(settings.S3_BUCKET_NAME, str)
        assert settings.S3_URL_EXPIRY_SECONDS > 0

    def test_azure_storage_settings_optional(self):
        """Test Azure storage settings are optional."""
        settings = get_settings()

        assert settings.AZURE_STORAGE_CONNECTION_STRING is None or isinstance(
            settings.AZURE_STORAGE_CONNECTION_STRING, str
        )

    def test_gcs_settings_optional(self):
        """Test GCS settings are optional."""
        settings = get_settings()

        assert settings.GCS_BUCKET_NAME is None or isinstance(settings.GCS_BUCKET_NAME, str)


class TestSettingsAgentConfiguration:
    """Tests for agent configuration."""

    def test_agent_settings(self):
        """Test agent configuration settings."""
        settings = get_settings()

        assert isinstance(settings.AGENTS_ENABLED, bool)
        assert settings.AGENT_MAX_EXECUTION_TIME > 0
        assert settings.AGENT_MAX_STEPS > 0


class TestSettingsObservability:
    """Tests for observability configuration."""

    def test_otel_settings(self):
        """Test OpenTelemetry settings."""
        settings = get_settings()

        assert isinstance(settings.OTEL_ENABLED, bool)
        assert settings.OTEL_SERVICE_NAME is not None

    def test_log_settings(self):
        """Test logging settings."""
        settings = get_settings()

        assert settings.LOG_LEVEL.upper() in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        assert settings.LOG_FORMAT in ["json", "text"]
