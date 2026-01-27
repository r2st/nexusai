"""Base storage backend interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class StorageType(str, Enum):
    """Storage backend types."""

    LOCAL = "local"
    S3 = "s3"
    AZURE_BLOB = "azure_blob"
    GCS = "gcs"
    FIREBASE = "firebase"


class FileCategory(str, Enum):
    """Categories of stored files."""

    AVATAR = "avatar"
    DOCUMENT = "document"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    GENERATED = "generated"
    EXPORT = "export"
    ATTACHMENT = "attachment"


@dataclass
class StorageConfig:
    """Configuration for a storage backend."""

    storage_type: StorageType
    base_path: str = ""
    bucket_name: str | None = None
    region: str | None = None
    access_key: str | None = None
    secret_key: str | None = None
    endpoint_url: str | None = None
    connection_string: str | None = None
    container_name: str | None = None
    project_id: str | None = None
    credentials_path: str | None = None
    url_expiry_seconds: int = 3600
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class StoredFile:
    """Metadata for a stored file."""

    key: str  # Storage key/path
    filename: str
    content_type: str
    size_bytes: int
    category: FileCategory
    storage_type: StorageType
    url: str | None = None
    public_url: str | None = None
    etag: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "key": self.key,
            "filename": self.filename,
            "content_type": self.content_type,
            "size_bytes": self.size_bytes,
            "category": self.category.value,
            "storage_type": self.storage_type.value,
            "url": self.url,
            "public_url": self.public_url,
            "etag": self.etag,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


class StorageBackend(ABC):
    """Base class for storage backends."""

    storage_type: StorageType

    def __init__(self, config: StorageConfig):
        self.config = config

    @abstractmethod
    async def upload(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        category: FileCategory = FileCategory.DOCUMENT,
        metadata: dict[str, Any] | None = None,
    ) -> StoredFile:
        """Upload a file."""
        pass

    @abstractmethod
    async def download(self, key: str) -> bytes | None:
        """Download a file."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a file."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a file exists."""
        pass

    @abstractmethod
    async def get_url(
        self,
        key: str,
        expires_in: int | None = None,
    ) -> str | None:
        """Get a URL for the file (signed if applicable)."""
        pass

    @abstractmethod
    async def list_files(
        self,
        prefix: str = "",
        max_results: int = 1000,
    ) -> list[StoredFile]:
        """List files with optional prefix."""
        pass

    def _build_key(
        self,
        filename: str,
        category: FileCategory,
        user_id: str | None = None,
    ) -> str:
        """Build a storage key from components."""
        parts = [category.value]

        if user_id:
            parts.append(user_id[:8])  # Use first 8 chars of user ID

        parts.append(filename)

        return "/".join(parts)
