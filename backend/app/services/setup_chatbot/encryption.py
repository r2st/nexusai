"""Encryption - Secure credential storage and encryption utilities."""

import base64
import hashlib
import hmac
import os
import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta, UTC
from typing import Any
import logging

logger = logging.getLogger(__name__)

# Try to import cryptography, fall back to simpler methods if not available
try:
    from cryptography.fernet import Fernet, InvalidToken
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.backends import default_backend
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    logger.warning("cryptography package not installed - using fallback encryption")


# ===================
# Key Management
# ===================

@dataclass
class EncryptionKey:
    """Represents an encryption key with metadata."""
    key_id: str
    key: bytes
    created_at: datetime
    expires_at: datetime | None = None
    algorithm: str = "fernet"
    is_active: bool = True

    def is_expired(self) -> bool:
        """Check if the key has expired."""
        if not self.expires_at:
            return False
        return datetime.now(UTC) > self.expires_at


class KeyManager:
    """Manages encryption keys with rotation support."""

    def __init__(self, master_key: str | None = None):
        self._master_key = master_key or os.environ.get("ENCRYPTION_MASTER_KEY")
        self._keys: dict[str, EncryptionKey] = {}
        self._active_key_id: str | None = None

        if not self._master_key:
            # Generate a new master key (in production, this should be from secure storage)
            self._master_key = secrets.token_hex(32)
            # Only log at debug level - this is expected in development
            logger.debug("Generated new master key - set ENCRYPTION_MASTER_KEY for persistence")

    def _derive_key(self, key_id: str) -> bytes:
        """Derive an encryption key from the master key."""
        if CRYPTOGRAPHY_AVAILABLE:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=key_id.encode(),
                iterations=100000,
                backend=default_backend(),
            )
            derived = kdf.derive(self._master_key.encode())
            return base64.urlsafe_b64encode(derived)
        else:
            # Fallback: simple HMAC-based key derivation
            derived = hmac.new(
                self._master_key.encode(),
                key_id.encode(),
                hashlib.sha256
            ).digest()
            return base64.urlsafe_b64encode(derived)

    def create_key(
        self,
        key_id: str | None = None,
        lifetime_days: int = 365,
    ) -> EncryptionKey:
        """Create a new encryption key."""
        if not key_id:
            key_id = f"key_{secrets.token_hex(8)}"

        key_bytes = self._derive_key(key_id)

        encryption_key = EncryptionKey(
            key_id=key_id,
            key=key_bytes,
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(days=lifetime_days),
        )

        self._keys[key_id] = encryption_key
        if not self._active_key_id:
            self._active_key_id = key_id

        return encryption_key

    def get_key(self, key_id: str) -> EncryptionKey | None:
        """Get a key by ID."""
        return self._keys.get(key_id)

    def get_active_key(self) -> EncryptionKey:
        """Get the currently active key, creating one if needed."""
        if self._active_key_id and self._active_key_id in self._keys:
            key = self._keys[self._active_key_id]
            if not key.is_expired():
                return key

        # Create a new key
        return self.create_key()

    def rotate_key(self) -> EncryptionKey:
        """Rotate to a new encryption key."""
        # Mark current key as inactive
        if self._active_key_id and self._active_key_id in self._keys:
            self._keys[self._active_key_id].is_active = False

        # Create new key
        new_key = self.create_key()
        self._active_key_id = new_key.key_id

        logger.info(f"Rotated encryption key to {new_key.key_id}")
        return new_key

    def cleanup_expired(self) -> int:
        """Remove expired keys."""
        expired = [
            key_id for key_id, key in self._keys.items()
            if key.is_expired() and not key.is_active
        ]
        for key_id in expired:
            del self._keys[key_id]
        return len(expired)


# Singleton key manager
key_manager = KeyManager()


# ===================
# Encryption Interface
# ===================

class Encryptor(ABC):
    """Abstract encryption interface."""

    @abstractmethod
    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext to ciphertext."""
        pass

    @abstractmethod
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext to plaintext."""
        pass

    @abstractmethod
    def can_decrypt(self, ciphertext: str) -> bool:
        """Check if we can decrypt the ciphertext."""
        pass


class FernetEncryptor(Encryptor):
    """Fernet-based encryption (symmetric, authenticated)."""

    def __init__(self, key_manager_instance: KeyManager | None = None):
        if not CRYPTOGRAPHY_AVAILABLE:
            raise RuntimeError("cryptography package required for FernetEncryptor")
        self._key_manager = key_manager_instance or key_manager
        self._ciphers: dict[str, Any] = {}  # key_id -> Fernet instance

    def _get_cipher(self, key: EncryptionKey) -> Any:
        """Get or create a Fernet cipher for a key."""
        if key.key_id not in self._ciphers:
            self._ciphers[key.key_id] = Fernet(key.key)
        return self._ciphers[key.key_id]

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext using the active key."""
        key = self._key_manager.get_active_key()
        cipher = self._get_cipher(key)

        ciphertext = cipher.encrypt(plaintext.encode())

        # Prepend key ID for decryption
        return f"{key.key_id}:{base64.urlsafe_b64encode(ciphertext).decode()}"

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext."""
        try:
            # Extract key ID
            if ":" not in ciphertext:
                raise ValueError("Invalid ciphertext format")

            key_id, encoded_data = ciphertext.split(":", 1)
            key = self._key_manager.get_key(key_id)

            if not key:
                raise ValueError(f"Key {key_id} not found")

            cipher = self._get_cipher(key)
            data = base64.urlsafe_b64decode(encoded_data)

            return cipher.decrypt(data).decode()
        except InvalidToken:
            raise ValueError("Invalid or corrupted ciphertext")

    def can_decrypt(self, ciphertext: str) -> bool:
        """Check if we have the key to decrypt."""
        if ":" not in ciphertext:
            return False
        key_id = ciphertext.split(":")[0]
        return self._key_manager.get_key(key_id) is not None


class FallbackEncryptor(Encryptor):
    """Fallback encryptor using XOR and HMAC (less secure, but no dependencies)."""

    def __init__(self, key_manager_instance: KeyManager | None = None):
        self._key_manager = key_manager_instance or key_manager

    def _xor_bytes(self, data: bytes, key: bytes) -> bytes:
        """XOR data with key (repeating key if necessary)."""
        key_len = len(key)
        return bytes(d ^ key[i % key_len] for i, d in enumerate(data))

    def encrypt(self, plaintext: str) -> str:
        """Encrypt using XOR and HMAC."""
        key = self._key_manager.get_active_key()

        # Generate random IV
        iv = secrets.token_bytes(16)

        # Derive encryption key from stored key + IV
        enc_key = hashlib.sha256(key.key + iv).digest()

        # XOR encrypt
        plaintext_bytes = plaintext.encode()
        ciphertext = self._xor_bytes(plaintext_bytes, enc_key)

        # Create HMAC for authentication
        mac = hmac.new(key.key, iv + ciphertext, hashlib.sha256).digest()

        # Combine: key_id:iv:ciphertext:mac
        combined = iv + ciphertext + mac
        return f"{key.key_id}:{base64.urlsafe_b64encode(combined).decode()}"

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt using XOR and HMAC verification."""
        if ":" not in ciphertext:
            raise ValueError("Invalid ciphertext format")

        key_id, encoded_data = ciphertext.split(":", 1)
        key = self._key_manager.get_key(key_id)

        if not key:
            raise ValueError(f"Key {key_id} not found")

        combined = base64.urlsafe_b64decode(encoded_data)

        # Extract components
        iv = combined[:16]
        mac = combined[-32:]
        encrypted = combined[16:-32]

        # Verify HMAC
        expected_mac = hmac.new(key.key, iv + encrypted, hashlib.sha256).digest()
        if not hmac.compare_digest(mac, expected_mac):
            raise ValueError("Invalid or tampered ciphertext")

        # Decrypt
        enc_key = hashlib.sha256(key.key + iv).digest()
        plaintext_bytes = self._xor_bytes(encrypted, enc_key)

        return plaintext_bytes.decode()

    def can_decrypt(self, ciphertext: str) -> bool:
        """Check if we have the key to decrypt."""
        if ":" not in ciphertext:
            return False
        key_id = ciphertext.split(":")[0]
        return self._key_manager.get_key(key_id) is not None


def get_encryptor() -> Encryptor:
    """Get the appropriate encryptor based on available libraries."""
    if CRYPTOGRAPHY_AVAILABLE:
        return FernetEncryptor()
    return FallbackEncryptor()


# ===================
# Credential Store
# ===================

@dataclass
class StoredCredential:
    """A stored credential with metadata."""
    credential_id: str
    encrypted_value: str
    credential_type: str  # token, password, api_key, etc.
    created_at: datetime
    last_used_at: datetime | None = None
    expires_at: datetime | None = None
    metadata: dict[str, Any] | None = None

    def is_expired(self) -> bool:
        """Check if the credential has expired."""
        if not self.expires_at:
            return False
        return datetime.now(UTC) > self.expires_at


class SecureCredentialStore:
    """Secure storage for credentials with encryption."""

    def __init__(self, encryptor: Encryptor | None = None):
        self._encryptor = encryptor or get_encryptor()
        self._credentials: dict[str, StoredCredential] = {}

    def store(
        self,
        credential_id: str,
        value: str,
        credential_type: str = "token",
        expires_in_days: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> StoredCredential:
        """Store a credential securely."""
        encrypted = self._encryptor.encrypt(value)

        credential = StoredCredential(
            credential_id=credential_id,
            encrypted_value=encrypted,
            credential_type=credential_type,
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(days=expires_in_days) if expires_in_days else None,
            metadata=metadata,
        )

        self._credentials[credential_id] = credential
        logger.debug(f"Stored credential {credential_id}")

        return credential

    def retrieve(self, credential_id: str) -> str | None:
        """Retrieve and decrypt a credential."""
        credential = self._credentials.get(credential_id)

        if not credential:
            return None

        if credential.is_expired():
            logger.warning(f"Credential {credential_id} has expired")
            del self._credentials[credential_id]
            return None

        try:
            value = self._encryptor.decrypt(credential.encrypted_value)
            credential.last_used_at = datetime.now(UTC)
            return value
        except Exception as e:
            logger.error(f"Failed to decrypt credential {credential_id}: {e}")
            return None

    def exists(self, credential_id: str) -> bool:
        """Check if a credential exists."""
        credential = self._credentials.get(credential_id)
        if not credential:
            return False
        if credential.is_expired():
            del self._credentials[credential_id]
            return False
        return True

    def delete(self, credential_id: str) -> bool:
        """Delete a credential."""
        if credential_id in self._credentials:
            del self._credentials[credential_id]
            logger.debug(f"Deleted credential {credential_id}")
            return True
        return False

    def list_credentials(
        self,
        credential_type: str | None = None,
    ) -> list[StoredCredential]:
        """List stored credentials (without decrypted values)."""
        credentials = list(self._credentials.values())

        # Filter out expired
        credentials = [c for c in credentials if not c.is_expired()]

        if credential_type:
            credentials = [c for c in credentials if c.credential_type == credential_type]

        return credentials

    def cleanup_expired(self) -> int:
        """Remove expired credentials."""
        expired = [
            cid for cid, cred in self._credentials.items()
            if cred.is_expired()
        ]
        for cid in expired:
            del self._credentials[cid]
        return len(expired)

    def rotate_encryption(self) -> int:
        """Re-encrypt all credentials with a new key."""
        # Rotate the key
        key_manager.rotate_key()

        # Re-encrypt all credentials
        count = 0
        for credential_id, credential in self._credentials.items():
            try:
                # Decrypt with old key
                value = self._encryptor.decrypt(credential.encrypted_value)

                # Re-encrypt with new key
                credential.encrypted_value = self._encryptor.encrypt(value)
                count += 1
            except Exception as e:
                logger.error(f"Failed to rotate credential {credential_id}: {e}")

        logger.info(f"Rotated encryption for {count} credentials")
        return count


# Singleton credential store
credential_store = SecureCredentialStore()


# ===================
# Utility Functions
# ===================

def mask_credential(value: str, visible_chars: int = 4) -> str:
    """Mask a credential for display."""
    if not value:
        return "***"
    if len(value) <= visible_chars:
        return "*" * len(value)
    return value[:visible_chars] + "*" * (len(value) - visible_chars)


def generate_credential_id(
    tenant_id: str,
    connection_id: str,
    field_name: str,
) -> str:
    """Generate a unique credential ID."""
    combined = f"{tenant_id}:{connection_id}:{field_name}"
    return hashlib.sha256(combined.encode()).hexdigest()[:24]


def hash_credential_for_comparison(value: str, salt: str = "") -> str:
    """Create a hash of a credential for comparison (not storage)."""
    data = f"{salt}{value}".encode()
    return hashlib.sha256(data).hexdigest()


# ===================
# Connection Credential Helper
# ===================

class ConnectionCredentialManager:
    """Helper for managing connection credentials."""

    def __init__(self, credential_store_instance: SecureCredentialStore | None = None):
        self._store = credential_store_instance or credential_store

    def store_connection_credentials(
        self,
        tenant_id: str,
        connection_id: str,
        credentials: dict[str, str],
        expires_in_days: int = 365,
    ) -> list[str]:
        """Store all credentials for a connection."""
        stored_ids = []

        for field_name, value in credentials.items():
            if value:  # Only store non-empty values
                cred_id = generate_credential_id(tenant_id, connection_id, field_name)
                self._store.store(
                    credential_id=cred_id,
                    value=value,
                    credential_type=field_name,
                    expires_in_days=expires_in_days,
                    metadata={
                        "tenant_id": tenant_id,
                        "connection_id": connection_id,
                        "field_name": field_name,
                    },
                )
                stored_ids.append(cred_id)

        return stored_ids

    def retrieve_connection_credentials(
        self,
        tenant_id: str,
        connection_id: str,
        field_names: list[str],
    ) -> dict[str, str | None]:
        """Retrieve credentials for a connection."""
        credentials = {}

        for field_name in field_names:
            cred_id = generate_credential_id(tenant_id, connection_id, field_name)
            credentials[field_name] = self._store.retrieve(cred_id)

        return credentials

    def delete_connection_credentials(
        self,
        tenant_id: str,
        connection_id: str,
        field_names: list[str],
    ) -> int:
        """Delete credentials for a connection."""
        deleted = 0

        for field_name in field_names:
            cred_id = generate_credential_id(tenant_id, connection_id, field_name)
            if self._store.delete(cred_id):
                deleted += 1

        return deleted


# Singleton credential manager
connection_credential_manager = ConnectionCredentialManager()
