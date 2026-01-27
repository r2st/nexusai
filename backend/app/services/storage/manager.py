"""Storage manager for unified file storage access."""

from typing import Any

import structlog

from app.core.config import settings
from app.services.storage.base import (
    FileCategory,
    StorageBackend,
    StorageConfig,
    StorageType,
    StoredFile,
)
from app.services.storage.local import LocalStorageBackend
from app.services.storage.s3 import S3StorageBackend
from app.services.storage.azure import AzureBlobStorageBackend
from app.services.storage.gcs import GCSStorageBackend

logger = structlog.get_logger()


class StorageManager:
    """Manager for multiple storage backends."""

    # Backend class mapping
    BACKEND_CLASSES: dict[StorageType, type[StorageBackend]] = {
        StorageType.LOCAL: LocalStorageBackend,
        StorageType.S3: S3StorageBackend,
        StorageType.AZURE_BLOB: AzureBlobStorageBackend,
        StorageType.GCS: GCSStorageBackend,
    }

    def __init__(self):
        self._backends: dict[str, StorageBackend] = {}
        self._default_backend: str | None = None
        self._category_backends: dict[FileCategory, str] = {}
        self._initialize_backends()

    def _initialize_backends(self) -> None:
        """Initialize storage backends from configuration."""
        # Always add local storage
        local_config = StorageConfig(
            storage_type=StorageType.LOCAL,
            base_path=settings.UPLOAD_DIR,
            extra={"public_base_url": "/api/v1/files"},
        )
        self._backends["local"] = LocalStorageBackend(local_config)
        self._default_backend = "local"

        # S3 storage
        if settings.S3_BUCKET_NAME:
            s3_config = StorageConfig(
                storage_type=StorageType.S3,
                bucket_name=settings.S3_BUCKET_NAME,
                region=settings.S3_REGION,
                access_key=settings.S3_ACCESS_KEY,
                secret_key=settings.S3_SECRET_KEY,
                endpoint_url=settings.S3_ENDPOINT_URL,
                url_expiry_seconds=settings.S3_URL_EXPIRY_SECONDS,
            )
            self._backends["s3"] = S3StorageBackend(s3_config)

            if settings.S3_DEFAULT:
                self._default_backend = "s3"

        # Azure Blob Storage
        if settings.AZURE_STORAGE_CONNECTION_STRING or settings.AZURE_STORAGE_ACCOUNT_NAME:
            azure_config = StorageConfig(
                storage_type=StorageType.AZURE_BLOB,
                connection_string=settings.AZURE_STORAGE_CONNECTION_STRING,
                container_name=settings.AZURE_STORAGE_CONTAINER,
                access_key=settings.AZURE_STORAGE_ACCOUNT_KEY,
                extra={"account_name": settings.AZURE_STORAGE_ACCOUNT_NAME},
            )
            self._backends["azure"] = AzureBlobStorageBackend(azure_config)

            if settings.AZURE_STORAGE_DEFAULT:
                self._default_backend = "azure"

        # Google Cloud Storage
        if settings.GCS_BUCKET_NAME:
            gcs_config = StorageConfig(
                storage_type=StorageType.GCS,
                bucket_name=settings.GCS_BUCKET_NAME,
                project_id=settings.GCS_PROJECT_ID,
                credentials_path=settings.GCS_CREDENTIALS_PATH,
                region=settings.GCS_REGION,
            )
            self._backends["gcs"] = GCSStorageBackend(gcs_config)

            if settings.GCS_DEFAULT:
                self._default_backend = "gcs"

        # Set up category-specific backends
        self._setup_category_backends()

        logger.info(
            "Storage backends initialized",
            backends=list(self._backends.keys()),
            default=self._default_backend,
        )

    def _setup_category_backends(self) -> None:
        """Set up category-specific storage backends."""
        # Use settings to map categories to backends
        # Default: all categories use default backend

        # Example: avatars might use S3, exports might use local
        if "s3" in self._backends:
            self._category_backends[FileCategory.AVATAR] = "s3"
            self._category_backends[FileCategory.IMAGE] = "s3"
            self._category_backends[FileCategory.GENERATED] = "s3"

        # Exports stay local by default
        self._category_backends[FileCategory.EXPORT] = "local"

    def get_backend(
        self,
        name: str | None = None,
        category: FileCategory | None = None,
    ) -> StorageBackend:
        """Get a storage backend."""
        # First check category-specific backend
        if category and category in self._category_backends:
            backend_name = self._category_backends[category]
            if backend_name in self._backends:
                return self._backends[backend_name]

        # Then check explicit name
        if name and name in self._backends:
            return self._backends[name]

        # Fall back to default
        return self._backends[self._default_backend]

    async def upload(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        category: FileCategory = FileCategory.DOCUMENT,
        backend: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> StoredFile:
        """Upload a file using the appropriate backend."""
        storage = self.get_backend(backend, category)
        return await storage.upload(key, data, content_type, category, metadata)

    async def download(
        self,
        key: str,
        backend: str | None = None,
    ) -> bytes | None:
        """Download a file."""
        storage = self.get_backend(backend)
        return await storage.download(key)

    async def delete(
        self,
        key: str,
        backend: str | None = None,
    ) -> bool:
        """Delete a file."""
        storage = self.get_backend(backend)
        return await storage.delete(key)

    async def exists(
        self,
        key: str,
        backend: str | None = None,
    ) -> bool:
        """Check if a file exists."""
        storage = self.get_backend(backend)
        return await storage.exists(key)

    async def get_url(
        self,
        key: str,
        backend: str | None = None,
        expires_in: int | None = None,
    ) -> str | None:
        """Get a URL for a file."""
        storage = self.get_backend(backend)
        return await storage.get_url(key, expires_in)

    async def refresh_url(
        self,
        stored_file: StoredFile,
        expires_in: int | None = None,
    ) -> StoredFile:
        """Refresh the URL for a stored file."""
        storage = self.get_backend(stored_file.storage_type.value)
        new_url = await storage.get_url(stored_file.key, expires_in)

        if new_url:
            stored_file.url = new_url

        return stored_file

    def list_backends(self) -> list[str]:
        """List available backends."""
        return list(self._backends.keys())

    def get_backend_info(self) -> list[dict[str, Any]]:
        """Get information about all backends."""
        return [
            {
                "name": name,
                "type": backend.storage_type.value,
                "is_default": name == self._default_backend,
            }
            for name, backend in self._backends.items()
        ]


# Global storage manager
_storage_manager: StorageManager | None = None


def get_storage_manager() -> StorageManager:
    """Get the global storage manager."""
    global _storage_manager
    if _storage_manager is None:
        _storage_manager = StorageManager()
    return _storage_manager
