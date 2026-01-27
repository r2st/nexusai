"""File storage services with multiple backend support."""

from app.services.storage.base import (
    StorageBackend,
    StorageConfig,
    StoredFile,
)
from app.services.storage.local import LocalStorageBackend
from app.services.storage.s3 import S3StorageBackend
from app.services.storage.azure import AzureBlobStorageBackend
from app.services.storage.gcs import GCSStorageBackend
from app.services.storage.manager import (
    StorageManager,
    get_storage_manager,
)

__all__ = [
    "StorageBackend",
    "StorageConfig",
    "StoredFile",
    "LocalStorageBackend",
    "S3StorageBackend",
    "AzureBlobStorageBackend",
    "GCSStorageBackend",
    "StorageManager",
    "get_storage_manager",
]
