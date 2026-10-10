"""Secret Rotation Service."""

import asyncio
import logging
import secrets
import string
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable

from pydantic import BaseModel, Field

from app.services.security.secrets.storage import SecretStorage, EncryptedSecret

logger = logging.getLogger(__name__)


class SecretType(str, Enum):
    """Type of secret for rotation policy."""

    API_KEY = "api_key"
    DATABASE_PASSWORD = "database_password"
    JWT_SECRET = "jwt_secret"
    ENCRYPTION_KEY = "encryption_key"
    OAUTH_SECRET = "oauth_secret"
    WEBHOOK_SECRET = "webhook_secret"
    SERVICE_TOKEN = "service_token"
    CUSTOM = "custom"


class RotationPolicy(BaseModel):
    """Policy for secret rotation."""

    secret_type: SecretType
    rotation_interval_days: int = 90
    min_length: int = 32
    max_length: int = 64
    require_special_chars: bool = True
    require_numbers: bool = True
    notify_before_days: int = 7
    auto_rotate: bool = True
    custom_generator: str | None = None  # Name of custom generator function


class SecretMetadata(BaseModel):
    """Extended metadata for rotatable secrets."""

    name: str
    secret_type: SecretType
    policy: RotationPolicy
    last_rotated: datetime | None = None
    next_rotation: datetime | None = None
    rotation_count: int = 0
    is_active: bool = True
    notify_emails: list[str] = Field(default_factory=list)
    tags: dict[str, str] = Field(default_factory=dict)


class RotationResult(BaseModel):
    """Result of a rotation operation."""

    secret_name: str
    success: bool
    old_version: int
    new_version: int
    error: str | None = None
    rotated_at: datetime = Field(default_factory=datetime.utcnow)


class SecretRotationService:
    """Service for automatic secret rotation.

    Manages secret lifecycle including:
    - Automatic rotation based on policies
    - Secure secret generation
    - Notification before expiration
    - Audit logging
    """

    def __init__(
        self,
        storage: SecretStorage | None = None,
        notification_callback: Callable | None = None,
    ):
        """Initialize rotation service.

        Args:
            storage: Secret storage backend
            notification_callback: Async callback for notifications
        """
        self._storage = storage or SecretStorage()
        self._notify = notification_callback
        self._metadata: dict[str, SecretMetadata] = {}
        self._custom_generators: dict[str, Callable[[], str]] = {}
        self._rotation_lock = asyncio.Lock()

    def register_secret(
        self,
        name: str,
        initial_value: str | None = None,
        secret_type: SecretType = SecretType.CUSTOM,
        policy: RotationPolicy | None = None,
        notify_emails: list[str] | None = None,
        tags: dict[str, str] | None = None,
    ) -> SecretMetadata:
        """Register a secret for rotation management.

        Args:
            name: Secret name
            initial_value: Initial secret value (generated if not provided)
            secret_type: Type of secret
            policy: Rotation policy (uses defaults for type if not provided)
            notify_emails: Emails to notify before rotation
            tags: Metadata tags

        Returns:
            Secret metadata
        """
        # Get or create policy
        if policy is None:
            policy = self._default_policy(secret_type)

        # Calculate next rotation
        next_rotation = datetime.utcnow() + timedelta(days=policy.rotation_interval_days)

        # Create metadata
        metadata = SecretMetadata(
            name=name,
            secret_type=secret_type,
            policy=policy,
            last_rotated=datetime.utcnow() if initial_value else None,
            next_rotation=next_rotation,
            notify_emails=notify_emails or [],
            tags=tags or {},
        )

        # Store initial value if provided
        if initial_value is None:
            initial_value = self.generate_secret(policy)

        self._storage.store(
            name=name,
            value=initial_value,
            expires_in=timedelta(days=policy.rotation_interval_days),
            tags=tags,
        )

        # Store metadata
        self._metadata[name] = metadata

        logger.info("Registered secret for rotation", secret_name=name, next_rotation=str(next_rotation))

        return metadata

    def register_custom_generator(
        self,
        name: str,
        generator: Callable[[], str],
    ) -> None:
        """Register a custom secret generator.

        Args:
            name: Generator name
            generator: Function that returns a new secret value
        """
        self._custom_generators[name] = generator

    def generate_secret(self, policy: RotationPolicy) -> str:
        """Generate a new secret based on policy.

        Args:
            policy: Rotation policy with requirements

        Returns:
            Generated secret string
        """
        # Check for custom generator
        if policy.custom_generator and policy.custom_generator in self._custom_generators:
            return self._custom_generators[policy.custom_generator]()

        # Build character set
        chars = string.ascii_letters

        if policy.require_numbers:
            chars += string.digits

        if policy.require_special_chars:
            chars += "!@#$%^&*()_+-=[]{}|;:,.<>?"

        # Generate random length within bounds
        length = secrets.randbelow(policy.max_length - policy.min_length + 1) + policy.min_length

        # Generate secret ensuring requirements are met
        while True:
            secret = "".join(secrets.choice(chars) for _ in range(length))

            # Validate requirements
            has_letter = any(c.isalpha() for c in secret)
            has_number = any(c.isdigit() for c in secret) if policy.require_numbers else True
            has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in secret) if policy.require_special_chars else True

            if has_letter and has_number and has_special:
                return secret

    async def rotate_secret(
        self,
        name: str,
        new_value: str | None = None,
    ) -> RotationResult:
        """Rotate a specific secret.

        Args:
            name: Secret name
            new_value: Optional new value (generated if not provided)

        Returns:
            Rotation result
        """
        async with self._rotation_lock:
            metadata = self._metadata.get(name)
            if not metadata:
                return RotationResult(
                    secret_name=name,
                    success=False,
                    old_version=0,
                    new_version=0,
                    error="Secret not registered for rotation",
                )

            # Get current version
            current = self._storage.get_metadata(name)
            old_version = current.version if current else 0

            # Generate new value if not provided
            if new_value is None:
                new_value = self.generate_secret(metadata.policy)

            try:
                # Rotate in storage
                updated = self._storage.rotate(name, new_value)

                if updated is None:
                    return RotationResult(
                        secret_name=name,
                        success=False,
                        old_version=old_version,
                        new_version=old_version,
                        error="Secret not found in storage",
                    )

                # Update metadata
                metadata.last_rotated = datetime.utcnow()
                metadata.next_rotation = datetime.utcnow() + timedelta(
                    days=metadata.policy.rotation_interval_days
                )
                metadata.rotation_count += 1

                logger.info(
                    f"Rotated secret '{name}' from v{old_version} to v{updated.version}"
                )

                return RotationResult(
                    secret_name=name,
                    success=True,
                    old_version=old_version,
                    new_version=updated.version,
                )

            except Exception as e:
                logger.error("Failed to rotate secret", secret_name=name, error=str(e))
                return RotationResult(
                    secret_name=name,
                    success=False,
                    old_version=old_version,
                    new_version=old_version,
                    error=str(e),
                )

    async def check_and_rotate_all(self) -> list[RotationResult]:
        """Check all secrets and rotate those due.

        Returns:
            List of rotation results
        """
        results = []
        now = datetime.utcnow()

        for name, metadata in self._metadata.items():
            if not metadata.is_active:
                continue

            if not metadata.policy.auto_rotate:
                continue

            if metadata.next_rotation and now >= metadata.next_rotation:
                result = await self.rotate_secret(name)
                results.append(result)

        return results

    async def check_expiring_secrets(self) -> list[SecretMetadata]:
        """Check for secrets expiring soon.

        Returns:
            List of secrets needing rotation soon
        """
        expiring = []
        now = datetime.utcnow()

        for metadata in self._metadata.values():
            if not metadata.is_active:
                continue

            if metadata.next_rotation:
                days_until = (metadata.next_rotation - now).days
                if days_until <= metadata.policy.notify_before_days:
                    expiring.append(metadata)

                    # Send notification if callback registered
                    if self._notify and metadata.notify_emails:
                        await self._send_notification(metadata, days_until)

        return expiring

    async def _send_notification(
        self,
        metadata: SecretMetadata,
        days_until: int,
    ) -> None:
        """Send rotation notification."""
        if not self._notify:
            return

        try:
            await self._notify(
                emails=metadata.notify_emails,
                secret_name=metadata.name,
                days_until_rotation=days_until,
                next_rotation=metadata.next_rotation,
            )
        except Exception as e:
            logger.error(f"Failed to send notification for '{metadata.name}': {e}")

    def get_secret(self, name: str) -> str | None:
        """Get a secret value.

        Args:
            name: Secret name

        Returns:
            Decrypted secret value or None
        """
        return self._storage.retrieve(name)

    def get_metadata(self, name: str) -> SecretMetadata | None:
        """Get secret metadata.

        Args:
            name: Secret name

        Returns:
            Secret metadata or None
        """
        return self._metadata.get(name)

    def needs_rotation(self, name: str) -> bool:
        """Check if a secret needs rotation.

        Args:
            name: Secret name

        Returns:
            True if secret needs rotation
        """
        metadata = self._metadata.get(name)
        if not metadata:
            return False

        if not metadata.is_active:
            return False

        now = datetime.utcnow()
        if metadata.next_rotation and now >= metadata.next_rotation:
            return True

        return False

    def list_secrets(
        self,
        include_inactive: bool = False,
    ) -> list[SecretMetadata]:
        """List all managed secrets.

        Args:
            include_inactive: Include inactive secrets

        Returns:
            List of secret metadata
        """
        secrets = []
        for metadata in self._metadata.values():
            if not include_inactive and not metadata.is_active:
                continue
            secrets.append(metadata)
        return secrets

    def deactivate_secret(self, name: str) -> bool:
        """Deactivate a secret (stop rotation).

        Args:
            name: Secret name

        Returns:
            True if deactivated
        """
        metadata = self._metadata.get(name)
        if metadata:
            metadata.is_active = False
            return True
        return False

    def reactivate_secret(self, name: str) -> bool:
        """Reactivate a secret.

        Args:
            name: Secret name

        Returns:
            True if reactivated
        """
        metadata = self._metadata.get(name)
        if metadata:
            metadata.is_active = True
            # Reset next rotation
            metadata.next_rotation = datetime.utcnow() + timedelta(
                days=metadata.policy.rotation_interval_days
            )
            return True
        return False

    def _default_policy(self, secret_type: SecretType) -> RotationPolicy:
        """Get default policy for secret type."""
        policies = {
            SecretType.API_KEY: RotationPolicy(
                secret_type=SecretType.API_KEY,
                rotation_interval_days=90,
                min_length=32,
                max_length=48,
            ),
            SecretType.DATABASE_PASSWORD: RotationPolicy(
                secret_type=SecretType.DATABASE_PASSWORD,
                rotation_interval_days=60,
                min_length=24,
                max_length=32,
                require_special_chars=True,
            ),
            SecretType.JWT_SECRET: RotationPolicy(
                secret_type=SecretType.JWT_SECRET,
                rotation_interval_days=30,
                min_length=64,
                max_length=64,
            ),
            SecretType.ENCRYPTION_KEY: RotationPolicy(
                secret_type=SecretType.ENCRYPTION_KEY,
                rotation_interval_days=180,
                min_length=32,
                max_length=32,
                require_special_chars=False,
                require_numbers=True,
            ),
            SecretType.OAUTH_SECRET: RotationPolicy(
                secret_type=SecretType.OAUTH_SECRET,
                rotation_interval_days=90,
                min_length=32,
                max_length=64,
            ),
            SecretType.WEBHOOK_SECRET: RotationPolicy(
                secret_type=SecretType.WEBHOOK_SECRET,
                rotation_interval_days=90,
                min_length=32,
                max_length=48,
            ),
            SecretType.SERVICE_TOKEN: RotationPolicy(
                secret_type=SecretType.SERVICE_TOKEN,
                rotation_interval_days=30,
                min_length=48,
                max_length=64,
            ),
            SecretType.CUSTOM: RotationPolicy(
                secret_type=SecretType.CUSTOM,
                rotation_interval_days=90,
                min_length=32,
                max_length=64,
            ),
        }
        return policies.get(secret_type, policies[SecretType.CUSTOM])


# Factory function
def get_secret_rotation_service(
    storage: SecretStorage | None = None,
) -> SecretRotationService:
    """Create a secret rotation service instance.

    Args:
        storage: Optional secret storage backend

    Returns:
        Configured SecretRotationService
    """
    return SecretRotationService(storage=storage)
