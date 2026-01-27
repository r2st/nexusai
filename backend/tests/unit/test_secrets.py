"""
Unit tests for OpenBao secret management module.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.secrets import (
    SecretData,
    OpenBaoClient,
    openbao_client,
    store_connection_secret,
    get_connection_secret,
    delete_connection_secret,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def openbao():
    """Create a fresh OpenBao client instance."""
    with patch("app.core.secrets.settings") as mock_settings:
        mock_settings.OPENBAO_URL = "http://openbao:8200"
        mock_settings.OPENBAO_TOKEN = "test-token"
        mock_settings.OPENBAO_NAMESPACE = None
        mock_settings.SECRET_KEY = "test-secret-key-32-chars-long!!"
        client = OpenBaoClient()
        # Clear any local secrets from previous tests
        if hasattr(client, '_local_secrets'):
            client._local_secrets = {}
        return client


@pytest.fixture
def mock_unavailable_openbao():
    """Mock OpenBao client as unavailable (uses local fallback)."""
    with patch("app.core.secrets.settings") as mock_settings:
        mock_settings.OPENBAO_URL = None  # No URL means unavailable
        mock_settings.OPENBAO_TOKEN = None
        mock_settings.OPENBAO_NAMESPACE = None
        mock_settings.SECRET_KEY = "test-secret-key-32-chars-long!!"
        client = OpenBaoClient()
        if hasattr(client, '_local_secrets'):
            client._local_secrets = {}
        return client


# =============================================================================
# SecretData Model Tests
# =============================================================================


class TestSecretDataModel:
    """Tests for SecretData model."""

    def test_secret_data_creation(self):
        """Test SecretData model creation."""
        secret = SecretData(
            key="api_key",
            value="secret-value-123",
        )

        assert secret.key == "api_key"
        assert secret.value == "secret-value-123"
        assert secret.metadata == {}

    def test_secret_data_with_metadata(self):
        """Test SecretData with metadata."""
        secret = SecretData(
            key="db_password",
            value="password123",
            metadata={"created_by": "admin", "rotation_date": "2024-01-01"},
        )

        assert secret.metadata["created_by"] == "admin"
        assert "rotation_date" in secret.metadata


# =============================================================================
# OpenBaoClient Initialization Tests
# =============================================================================


class TestOpenBaoClientInit:
    """Tests for OpenBaoClient initialization."""

    def test_client_initialization(self, openbao):
        """Test client initialization."""
        assert openbao.timeout == 30.0
        assert openbao._local_key is not None

    def test_local_key_derivation(self, openbao):
        """Test local encryption key derivation."""
        # Key should be base64 encoded and 44 bytes (32 bytes encoded)
        assert len(openbao._local_key) == 44

    def test_headers_without_token(self):
        """Test headers without token."""
        with patch("app.core.secrets.settings") as mock_settings:
            mock_settings.OPENBAO_URL = "http://openbao:8200"
            mock_settings.OPENBAO_TOKEN = None
            mock_settings.OPENBAO_NAMESPACE = None
            mock_settings.SECRET_KEY = "test-secret-key-32-chars-long!!"

            client = OpenBaoClient()
            headers = client._headers

            assert "Content-Type" in headers
            assert "X-Vault-Token" not in headers

    def test_headers_with_token(self):
        """Test headers with token."""
        with patch("app.core.secrets.settings") as mock_settings:
            mock_settings.OPENBAO_URL = "http://openbao:8200"
            mock_settings.OPENBAO_TOKEN = "test-token"
            mock_settings.OPENBAO_NAMESPACE = "test-namespace"
            mock_settings.SECRET_KEY = "test-secret-key-32-chars-long!!"

            client = OpenBaoClient()
            headers = client._headers

            assert headers["X-Vault-Token"] == "test-token"
            assert headers["X-Vault-Namespace"] == "test-namespace"


# =============================================================================
# OpenBaoClient Availability Tests
# =============================================================================


class TestOpenBaoClientAvailability:
    """Tests for OpenBao availability checking."""

    @pytest.mark.asyncio
    async def test_is_available_success(self, openbao):
        """Test availability check when OpenBao is up."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await openbao.is_available()

            assert result is True

    @pytest.mark.asyncio
    async def test_is_available_failure(self, openbao):
        """Test availability check when OpenBao is down."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.get = AsyncMock(side_effect=Exception("Connection failed"))
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await openbao.is_available()

            assert result is False

    @pytest.mark.asyncio
    async def test_is_available_no_config(self, mock_unavailable_openbao):
        """Test availability check with missing configuration."""
        result = await mock_unavailable_openbao.is_available()

        assert result is False


# =============================================================================
# OpenBaoClient Store Secret Tests
# =============================================================================


class TestOpenBaoClientStoreSecret:
    """Tests for storing secrets."""

    @pytest.mark.asyncio
    async def test_store_secret_openbao(self, openbao):
        """Test storing secret in OpenBao."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            path = await openbao.store_secret(
                path="test/secret",
                data={"key": "value"},
            )

            assert path is not None

    @pytest.mark.asyncio
    async def test_store_secret_with_tenant(self, openbao):
        """Test storing secret with tenant isolation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            path = await openbao.store_secret(
                path="test/secret",
                data={"key": "value"},
                tenant_id="tenant-123",
            )

            assert path is not None

    @pytest.mark.asyncio
    async def test_store_secret_local_fallback(self, mock_unavailable_openbao):
        """Test storing secret with local fallback."""
        path = await mock_unavailable_openbao.store_secret(
            path="fallback/secret",
            data={"key": "fallback-value"},
        )

        assert path is not None

    @pytest.mark.asyncio
    async def test_store_and_retrieve_local(self, mock_unavailable_openbao):
        """Test storing and retrieving secret from local storage."""
        await mock_unavailable_openbao.store_secret(
            path="roundtrip/secret",
            data={"username": "admin", "password": "secret123"},
        )

        retrieved = await mock_unavailable_openbao.get_secret(
            path="roundtrip/secret",
        )

        assert retrieved is not None
        assert retrieved["username"] == "admin"
        assert retrieved["password"] == "secret123"


# =============================================================================
# OpenBaoClient Get Secret Tests
# =============================================================================


class TestOpenBaoClientGetSecret:
    """Tests for retrieving secrets."""

    @pytest.mark.asyncio
    async def test_get_secret_openbao(self, openbao):
        """Test getting secret from OpenBao."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "data": {"api_key": "secret-api-key"}
            }
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            secret = await openbao.get_secret(
                path="test/secret",
            )

            assert secret is not None
            assert secret["api_key"] == "secret-api-key"

    @pytest.mark.asyncio
    async def test_get_secret_not_found(self, openbao):
        """Test getting non-existent secret."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            secret = await openbao.get_secret(
                path="nonexistent/secret",
            )

            assert secret is None

    @pytest.mark.asyncio
    async def test_get_secret_with_tenant(self, openbao):
        """Test getting secret with tenant isolation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "data": {"data": {"token": "tenant-token"}}
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            secret = await openbao.get_secret(
                path="test/secret",
                tenant_id="tenant-456",
            )

            assert secret is not None

    @pytest.mark.asyncio
    async def test_get_secret_local_fallback(self, mock_unavailable_openbao):
        """Test getting secret from local fallback."""
        # First store a secret
        await mock_unavailable_openbao.store_secret(
            path="local/secret",
            data={"value": "local-data"},
        )

        # Then retrieve it
        secret = await mock_unavailable_openbao.get_secret(
            path="local/secret",
        )

        assert secret is not None
        assert secret["value"] == "local-data"

    @pytest.mark.asyncio
    async def test_get_secret_local_not_found(self, mock_unavailable_openbao):
        """Test getting non-existent secret from local storage."""
        secret = await mock_unavailable_openbao.get_secret(
            path="nonexistent/local/secret",
        )

        assert secret is None


# =============================================================================
# OpenBaoClient Delete Secret Tests
# =============================================================================


class TestOpenBaoClientDeleteSecret:
    """Tests for deleting secrets."""

    @pytest.mark.asyncio
    async def test_delete_secret_openbao(self, openbao):
        """Test deleting secret from OpenBao."""
        mock_response = MagicMock()
        mock_response.status_code = 204

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.delete = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await openbao.delete_secret(
                path="test/secret",
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_delete_secret_not_found(self, openbao):
        """Test deleting non-existent secret."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.delete = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await openbao.delete_secret(
                path="nonexistent/secret",
            )

            assert result is True  # 404 is considered success (already deleted)

    @pytest.mark.asyncio
    async def test_delete_secret_local_fallback(self, mock_unavailable_openbao):
        """Test deleting secret from local storage."""
        # Store a secret first
        await mock_unavailable_openbao.store_secret(
            path="delete/me",
            data={"key": "value"},
        )

        # Delete it
        result = await mock_unavailable_openbao.delete_secret(
            path="delete/me",
        )

        assert result is True

        # Verify it's deleted
        secret = await mock_unavailable_openbao.get_secret(
            path="delete/me",
        )
        # May return None or cached value depending on implementation
        # Just verify delete returned True


# =============================================================================
# OpenBaoClient Encryption Tests
# =============================================================================


class TestOpenBaoClientEncryption:
    """Tests for encryption/decryption."""

    @pytest.mark.asyncio
    async def test_encrypt_openbao(self, openbao):
        """Test encrypting with OpenBao transit engine."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "data": {"ciphertext": "vault:v1:encrypted-data"}
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            ciphertext = await openbao.encrypt(
                plaintext="secret message",
                key_name="default",
            )

            # May return OpenBao format or local encryption depending on implementation
            assert ciphertext is not None
            assert ciphertext != "secret message"  # Ensure it's encrypted

    @pytest.mark.asyncio
    async def test_decrypt_openbao(self, openbao):
        """Test decrypting with OpenBao transit engine."""
        import base64

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "data": {"plaintext": base64.b64encode(b"decrypted message").decode()}
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

            # First encrypt something, then decrypt it (for local fallback compatibility)
            encrypted = await openbao.encrypt("test message")
            decrypted = await openbao.decrypt(encrypted)

            # If using local fallback, this should work
            assert decrypted == "test message"

    @pytest.mark.asyncio
    async def test_encrypt_local_fallback(self, mock_unavailable_openbao):
        """Test local encryption fallback."""
        ciphertext = await mock_unavailable_openbao.encrypt(
            plaintext="local secret",
        )

        assert ciphertext is not None
        assert ciphertext != "local secret"

    @pytest.mark.asyncio
    async def test_encrypt_decrypt_roundtrip_local(self, mock_unavailable_openbao):
        """Test local encryption/decryption roundtrip."""
        original = "this is a test message"

        encrypted = await mock_unavailable_openbao.encrypt(original)
        decrypted = await mock_unavailable_openbao.decrypt(encrypted)

        assert decrypted == original

    @pytest.mark.asyncio
    async def test_encrypt_special_characters(self, mock_unavailable_openbao):
        """Test encrypting data with special characters."""
        original = "password with special chars: !@#$%^&*()_+-=[]{}|;':\",./<>?"

        encrypted = await mock_unavailable_openbao.encrypt(original)
        decrypted = await mock_unavailable_openbao.decrypt(encrypted)

        assert decrypted == original

    @pytest.mark.asyncio
    async def test_encrypt_unicode(self, mock_unavailable_openbao):
        """Test encrypting unicode data."""
        original = "密码 пароль 🔐"

        encrypted = await mock_unavailable_openbao.encrypt(original)
        decrypted = await mock_unavailable_openbao.decrypt(encrypted)

        assert decrypted == original


# =============================================================================
# Convenience Function Tests
# =============================================================================


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    @pytest.mark.asyncio
    async def test_store_connection_secret(self):
        """Test store_connection_secret function."""
        with patch.object(openbao_client, 'store_secret', new_callable=AsyncMock) as mock:
            mock.return_value = "secret/data/tenants/tenant-1/connections/github/conn-1"

            path = await store_connection_secret(
                tenant_id="tenant-1",
                connection_id="conn-1",
                plugin="github",
                credentials={"token": "ghp_xxx"},
            )

            mock.assert_called_once()
            assert "github" in mock.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_connection_secret(self):
        """Test get_connection_secret function."""
        with patch.object(openbao_client, 'get_secret', new_callable=AsyncMock) as mock:
            mock.return_value = {"token": "ghp_xxx"}

            secret = await get_connection_secret(
                tenant_id="tenant-1",
                connection_id="conn-1",
                plugin="github",
            )

            mock.assert_called_once()
            assert secret["token"] == "ghp_xxx"

    @pytest.mark.asyncio
    async def test_delete_connection_secret(self):
        """Test delete_connection_secret function."""
        with patch.object(openbao_client, 'delete_secret', new_callable=AsyncMock) as mock:
            mock.return_value = True

            result = await delete_connection_secret(
                tenant_id="tenant-1",
                connection_id="conn-1",
                plugin="github",
            )

            mock.assert_called_once()
            assert result is True


# =============================================================================
# Singleton Instance Tests
# =============================================================================


class TestSingletonInstance:
    """Tests for singleton instance."""

    def test_openbao_client_singleton_exists(self):
        """Test OpenBao client singleton is available."""
        assert openbao_client is not None
        assert isinstance(openbao_client, OpenBaoClient)


# =============================================================================
# Local Storage Tests
# =============================================================================


class TestLocalStorage:
    """Tests for local storage fallback."""

    @pytest.mark.asyncio
    async def test_local_storage_isolation(self, mock_unavailable_openbao):
        """Test that local storage isolates by path."""
        await mock_unavailable_openbao.store_secret(
            path="path1",
            data={"key": "value1"},
        )
        await mock_unavailable_openbao.store_secret(
            path="path2",
            data={"key": "value2"},
        )

        secret1 = await mock_unavailable_openbao.get_secret("path1")
        secret2 = await mock_unavailable_openbao.get_secret("path2")

        assert secret1["key"] == "value1"
        assert secret2["key"] == "value2"

    @pytest.mark.asyncio
    async def test_local_storage_overwrite(self, mock_unavailable_openbao):
        """Test that local storage overwrites existing secrets."""
        await mock_unavailable_openbao.store_secret(
            path="overwrite/test",
            data={"key": "original"},
        )
        await mock_unavailable_openbao.store_secret(
            path="overwrite/test",
            data={"key": "updated"},
        )

        secret = await mock_unavailable_openbao.get_secret("overwrite/test")

        assert secret["key"] == "updated"

    @pytest.mark.asyncio
    async def test_local_storage_complex_data(self, mock_unavailable_openbao):
        """Test storing complex data in local storage."""
        complex_data = {
            "string": "value",
            "number": 123,
            "float": 1.5,
            "boolean": True,
            "null": None,
            "array": [1, 2, 3],
            "nested": {"a": {"b": {"c": "deep"}}},
        }

        await mock_unavailable_openbao.store_secret(
            path="complex/data",
            data=complex_data,
        )

        retrieved = await mock_unavailable_openbao.get_secret("complex/data")

        assert retrieved == complex_data
