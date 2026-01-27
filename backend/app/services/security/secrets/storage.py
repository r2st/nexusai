"""Encrypted Secret Storage."""

import base64
import hashlib
import json
import os
import secrets
from datetime import datetime, timedelta
from typing import Any

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from pydantic import BaseModel, Field


class EncryptedSecret(BaseModel):
    """An encrypted secret with metadata."""

    id: str
    name: str
    encrypted_value: str
    salt: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None
    version: int = 1
    tags: dict[str, str] = Field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at


class SecretStorage:
    """Secure storage for encrypted secrets.

    Uses Fernet symmetric encryption with PBKDF2 key derivation.
    Can be backed by various storage backends (memory, Redis, DB).
    """

    def __init__(
        self,
        master_key: str | None = None,
        storage_backend: Any | None = None,
    ):
        """Initialize secret storage.

        Args:
            master_key: Master encryption key (uses env var if not provided)
            storage_backend: Optional storage backend (defaults to in-memory)
        """
        self._master_key = master_key or os.environ.get(
            "SECRET_ENCRYPTION_KEY",
            "change-this-in-production-use-strong-key"
        )
        self._storage = storage_backend or {}
        self._fernet_cache: dict[str, Fernet] = {}

    def _derive_key(self, salt: bytes) -> bytes:
        """Derive encryption key from master key and salt."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(
            kdf.derive(self._master_key.encode())
        )
        return key

    def _get_fernet(self, salt: bytes) -> Fernet:
        """Get or create Fernet instance for salt."""
        salt_hex = salt.hex()
        if salt_hex not in self._fernet_cache:
            key = self._derive_key(salt)
            self._fernet_cache[salt_hex] = Fernet(key)
        return self._fernet_cache[salt_hex]

    def encrypt(self, value: str) -> tuple[str, str]:
        """Encrypt a value.

        Args:
            value: Plain text value to encrypt

        Returns:
            Tuple of (encrypted_value, salt) as base64 strings
        """
        salt = os.urandom(16)
        fernet = self._get_fernet(salt)
        encrypted = fernet.encrypt(value.encode())
        return (
            base64.urlsafe_b64encode(encrypted).decode(),
            base64.urlsafe_b64encode(salt).decode(),
        )

    def decrypt(self, encrypted_value: str, salt: str) -> str:
        """Decrypt a value.

        Args:
            encrypted_value: Base64-encoded encrypted value
            salt: Base64-encoded salt

        Returns:
            Decrypted plain text
        """
        salt_bytes = base64.urlsafe_b64decode(salt.encode())
        fernet = self._get_fernet(salt_bytes)
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_value.encode())
        return fernet.decrypt(encrypted_bytes).decode()

    def store(
        self,
        name: str,
        value: str,
        expires_in: timedelta | None = None,
        tags: dict[str, str] | None = None,
    ) -> EncryptedSecret:
        """Store a secret securely.

        Args:
            name: Secret name/identifier
            value: Plain text secret value
            expires_in: Optional expiration duration
            tags: Optional metadata tags

        Returns:
            EncryptedSecret with metadata
        """
        # Generate unique ID
        secret_id = self._generate_id(name)

        # Check for existing secret
        existing = self._storage.get(secret_id)
        version = existing.version + 1 if existing else 1

        # Encrypt the value
        encrypted_value, salt = self.encrypt(value)

        # Calculate expiration
        expires_at = None
        if expires_in:
            expires_at = datetime.utcnow() + expires_in

        # Create secret object
        secret = EncryptedSecret(
            id=secret_id,
            name=name,
            encrypted_value=encrypted_value,
            salt=salt,
            expires_at=expires_at,
            version=version,
            tags=tags or {},
            updated_at=datetime.utcnow(),
        )

        # Store
        self._storage[secret_id] = secret

        return secret

    def retrieve(self, name: str) -> str | None:
        """Retrieve and decrypt a secret.

        Args:
            name: Secret name

        Returns:
            Decrypted value or None if not found
        """
        secret_id = self._generate_id(name)
        secret = self._storage.get(secret_id)

        if not secret:
            return None

        if secret.is_expired:
            return None

        return self.decrypt(secret.encrypted_value, secret.salt)

    def get_metadata(self, name: str) -> EncryptedSecret | None:
        """Get secret metadata without decrypting.

        Args:
            name: Secret name

        Returns:
            Secret metadata or None
        """
        secret_id = self._generate_id(name)
        return self._storage.get(secret_id)

    def delete(self, name: str) -> bool:
        """Delete a secret.

        Args:
            name: Secret name

        Returns:
            True if deleted, False if not found
        """
        secret_id = self._generate_id(name)
        if secret_id in self._storage:
            del self._storage[secret_id]
            return True
        return False

    def list_secrets(
        self,
        prefix: str | None = None,
        include_expired: bool = False,
    ) -> list[EncryptedSecret]:
        """List stored secrets (metadata only).

        Args:
            prefix: Optional name prefix filter
            include_expired: Include expired secrets

        Returns:
            List of secret metadata
        """
        secrets = []
        for secret in self._storage.values():
            if prefix and not secret.name.startswith(prefix):
                continue
            if not include_expired and secret.is_expired:
                continue
            secrets.append(secret)
        return secrets

    def rotate(
        self,
        name: str,
        new_value: str,
    ) -> EncryptedSecret | None:
        """Rotate a secret to a new value.

        Args:
            name: Secret name
            new_value: New secret value

        Returns:
            Updated secret or None if not found
        """
        secret_id = self._generate_id(name)
        existing = self._storage.get(secret_id)

        if not existing:
            return None

        # Re-encrypt with new value
        encrypted_value, salt = self.encrypt(new_value)

        # Update secret
        existing.encrypted_value = encrypted_value
        existing.salt = salt
        existing.version += 1
        existing.updated_at = datetime.utcnow()

        return existing

    def _generate_id(self, name: str) -> str:
        """Generate deterministic ID from name."""
        return hashlib.sha256(name.encode()).hexdigest()[:16]

    def export_secrets(
        self,
        names: list[str] | None = None,
    ) -> dict[str, str]:
        """Export secrets as plaintext (for migration).

        WARNING: Handle with extreme care!

        Args:
            names: Optional list of specific secrets to export

        Returns:
            Dict of name -> plaintext value
        """
        result = {}

        for secret in self._storage.values():
            if names and secret.name not in names:
                continue
            if secret.is_expired:
                continue

            try:
                value = self.decrypt(secret.encrypted_value, secret.salt)
                result[secret.name] = value
            except Exception:
                continue

        return result


class RedisSecretStorage(SecretStorage):
    """Redis-backed secret storage."""

    def __init__(
        self,
        redis_client: Any,
        master_key: str | None = None,
        key_prefix: str = "nexusai:secrets:",
    ):
        """Initialize Redis secret storage.

        Args:
            redis_client: Redis client instance
            master_key: Master encryption key
            key_prefix: Redis key prefix
        """
        super().__init__(master_key=master_key)
        self._redis = redis_client
        self._prefix = key_prefix

    def _redis_key(self, secret_id: str) -> str:
        return f"{self._prefix}{secret_id}"

    def store(
        self,
        name: str,
        value: str,
        expires_in: timedelta | None = None,
        tags: dict[str, str] | None = None,
    ) -> EncryptedSecret:
        """Store secret in Redis."""
        secret_id = self._generate_id(name)

        # Check for existing
        existing_data = self._redis.get(self._redis_key(secret_id))
        version = 1
        if existing_data:
            existing = EncryptedSecret.model_validate_json(existing_data)
            version = existing.version + 1

        # Encrypt
        encrypted_value, salt = self.encrypt(value)

        # Create secret
        expires_at = datetime.utcnow() + expires_in if expires_in else None
        secret = EncryptedSecret(
            id=secret_id,
            name=name,
            encrypted_value=encrypted_value,
            salt=salt,
            expires_at=expires_at,
            version=version,
            tags=tags or {},
        )

        # Store in Redis
        ttl = int(expires_in.total_seconds()) if expires_in else None
        self._redis.set(
            self._redis_key(secret_id),
            secret.model_dump_json(),
            ex=ttl,
        )

        return secret

    def retrieve(self, name: str) -> str | None:
        """Retrieve secret from Redis."""
        secret_id = self._generate_id(name)
        data = self._redis.get(self._redis_key(secret_id))

        if not data:
            return None

        secret = EncryptedSecret.model_validate_json(data)

        if secret.is_expired:
            return None

        return self.decrypt(secret.encrypted_value, secret.salt)

    def get_metadata(self, name: str) -> EncryptedSecret | None:
        """Get metadata from Redis."""
        secret_id = self._generate_id(name)
        data = self._redis.get(self._redis_key(secret_id))

        if not data:
            return None

        return EncryptedSecret.model_validate_json(data)

    def delete(self, name: str) -> bool:
        """Delete secret from Redis."""
        secret_id = self._generate_id(name)
        return self._redis.delete(self._redis_key(secret_id)) > 0

    def list_secrets(
        self,
        prefix: str | None = None,
        include_expired: bool = False,
    ) -> list[EncryptedSecret]:
        """List secrets from Redis."""
        secrets = []
        pattern = f"{self._prefix}*"

        for key in self._redis.scan_iter(pattern):
            data = self._redis.get(key)
            if data:
                secret = EncryptedSecret.model_validate_json(data)
                if prefix and not secret.name.startswith(prefix):
                    continue
                if not include_expired and secret.is_expired:
                    continue
                secrets.append(secret)

        return secrets
