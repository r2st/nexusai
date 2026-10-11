"""OpenBao integration for secret management.

OpenBao is an open-source fork of HashiCorp Vault that provides:
- Secure secret storage
- Dynamic secrets generation
- Encryption as a service
- Secret rotation

This replaces AES encryption with proper secret management.
"""

import base64
import hashlib
from typing import Any

import httpx
from cryptography.fernet import Fernet
from pydantic import BaseModel

from app.core.config import settings


class SecretData(BaseModel):
    """Secret data model."""

    key: str
    value: str
    metadata: dict[str, Any] = {}


class OpenBaoClient:
    """Client for OpenBao secret management."""

    def __init__(self):
        self.base_url = settings.OPENBAO_URL
        self.token = settings.OPENBAO_TOKEN
        self.namespace = settings.OPENBAO_NAMESPACE
        self.timeout = 30.0

        # Fallback encryption key for local development
        self._local_key = self._derive_local_key()

    def _derive_local_key(self) -> bytes:
        """Derive a local encryption key from the secret key."""
        key_bytes = settings.SECRET_KEY.encode()
        # Use SHA256 to get 32 bytes, then base64 encode for Fernet
        derived = hashlib.sha256(key_bytes).digest()
        return base64.urlsafe_b64encode(derived)

    @property
    def _headers(self) -> dict[str, str]:
        """Get headers for OpenBao requests."""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["X-Vault-Token"] = self.token
        if self.namespace:
            headers["X-Vault-Namespace"] = self.namespace
        return headers

    async def is_available(self) -> bool:
        """Check if OpenBao is available."""
        if not self.base_url or not self.token:
            return False

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.base_url}/v1/sys/health",
                    headers=self._headers,
                )
                return response.status_code == 200
        except Exception:
            return False

    async def store_secret(
        self,
        path: str,
        data: dict[str, Any],
        tenant_id: str | None = None,
    ) -> str:
        """Store a secret in OpenBao.

        Args:
            path: The secret path (e.g., "connections/github/token")
            data: The secret data to store
            tenant_id: Optional tenant ID for isolation

        Returns:
            The full secret reference path
        """
        # Build full path with tenant isolation
        if tenant_id:
            full_path = f"secret/data/tenants/{tenant_id}/{path}"
        else:
            full_path = f"secret/data/{path}"

        # Try OpenBao first
        if await self.is_available():
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/v1/{full_path}",
                    headers=self._headers,
                    json={"data": data},
                )
                response.raise_for_status()
                return full_path
        else:
            # Fallback to local encrypted storage
            return await self._store_local_secret(full_path, data)

    async def get_secret(
        self,
        path: str,
        tenant_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Retrieve a secret from OpenBao.

        Args:
            path: The secret path
            tenant_id: Optional tenant ID for isolation

        Returns:
            The secret data or None if not found
        """
        # Build full path with tenant isolation
        if tenant_id:
            full_path = f"secret/data/tenants/{tenant_id}/{path}"
        else:
            full_path = f"secret/data/{path}"

        # Try OpenBao first
        if await self.is_available():
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/v1/{full_path}",
                    headers=self._headers,
                )
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                result = response.json()
                return result.get("data", {}).get("data")
        else:
            # Fallback to local encrypted storage
            return await self._get_local_secret(full_path)

    async def delete_secret(
        self,
        path: str,
        tenant_id: str | None = None,
    ) -> bool:
        """Delete a secret from OpenBao.

        Args:
            path: The secret path
            tenant_id: Optional tenant ID for isolation

        Returns:
            True if deleted successfully
        """
        # Build full path with tenant isolation
        if tenant_id:
            full_path = f"secret/metadata/tenants/{tenant_id}/{path}"
        else:
            full_path = f"secret/metadata/{path}"

        if await self.is_available():
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.delete(
                    f"{self.base_url}/v1/{full_path}",
                    headers=self._headers,
                )
                return response.status_code in (200, 204, 404)
        else:
            return await self._delete_local_secret(full_path)

    async def encrypt(self, plaintext: str, key_name: str = "default") -> str:
        """Encrypt data using OpenBao's transit engine.

        Args:
            plaintext: The data to encrypt
            key_name: The encryption key name

        Returns:
            The encrypted ciphertext
        """
        if await self.is_available():
            encoded = base64.b64encode(plaintext.encode()).decode()
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/v1/transit/encrypt/{key_name}",
                    headers=self._headers,
                    json={"plaintext": encoded},
                )
                response.raise_for_status()
                return response.json()["data"]["ciphertext"]
        else:
            # Fallback to local Fernet encryption
            f = Fernet(self._local_key)
            return f.encrypt(plaintext.encode()).decode()

    async def decrypt(self, ciphertext: str, key_name: str = "default") -> str:
        """Decrypt data using OpenBao's transit engine.

        Args:
            ciphertext: The encrypted data
            key_name: The encryption key name

        Returns:
            The decrypted plaintext
        """
        if await self.is_available():
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/v1/transit/decrypt/{key_name}",
                    headers=self._headers,
                    json={"ciphertext": ciphertext},
                )
                response.raise_for_status()
                encoded = response.json()["data"]["plaintext"]
                return base64.b64decode(encoded).decode()
        else:
            # Fallback to local Fernet decryption
            f = Fernet(self._local_key)
            return f.decrypt(ciphertext.encode()).decode()

    # Local fallback methods for development
    _local_secrets: dict[str, bytes] = {}

    async def _store_local_secret(self, path: str, data: dict[str, Any]) -> str:
        """Store secret locally (development fallback)."""
        import json
        f = Fernet(self._local_key)
        encrypted = f.encrypt(json.dumps(data).encode())
        self._local_secrets[path] = encrypted
        return path

    async def _get_local_secret(self, path: str) -> dict[str, Any] | None:
        """Get secret from local storage (development fallback)."""
        import json
        if path not in self._local_secrets:
            return None
        f = Fernet(self._local_key)
        decrypted = f.decrypt(self._local_secrets[path])
        return json.loads(decrypted.decode())

    async def _delete_local_secret(self, path: str) -> bool:
        """Delete secret from local storage (development fallback)."""
        if path in self._local_secrets:
            del self._local_secrets[path]
        return True


# Singleton instance
openbao_client = OpenBaoClient()


# Convenience functions
async def store_connection_secret(
    tenant_id: str,
    connection_id: str,
    plugin: str,
    credentials: dict[str, Any],
) -> str:
    """Store connection credentials securely."""
    path = f"connections/{plugin}/{connection_id}"
    return await openbao_client.store_secret(path, credentials, tenant_id)


async def get_connection_secret(
    tenant_id: str,
    connection_id: str,
    plugin: str,
) -> dict[str, Any] | None:
    """Retrieve connection credentials."""
    path = f"connections/{plugin}/{connection_id}"
    return await openbao_client.get_secret(path, tenant_id)


async def delete_connection_secret(
    tenant_id: str,
    connection_id: str,
    plugin: str,
) -> bool:
    """Delete connection credentials."""
    path = f"connections/{plugin}/{connection_id}"
    return await openbao_client.delete_secret(path, tenant_id)
