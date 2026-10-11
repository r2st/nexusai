"""Local filesystem storage backend."""

import mimetypes
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiofiles
import aiofiles.os
import structlog

from app.services.storage.base import (
    FileCategory,
    StorageBackend,
    StorageConfig,
    StorageType,
    StoredFile,
)

logger = structlog.get_logger()


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage backend."""

    storage_type = StorageType.LOCAL

    def __init__(self, config: StorageConfig):
        super().__init__(config)
        self.base_path = Path(config.base_path or "./uploads")
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.public_base_url = config.extra.get("public_base_url", "/files")

    def _get_full_path(self, key: str) -> Path:
        """Get the full filesystem path for a key, rejecting traversal."""
        full = (self.base_path / key).resolve()
        if not full.is_relative_to(self.base_path.resolve()):
            raise ValueError(f"Path traversal denied: {key}")
        return full

    async def upload(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        category: FileCategory = FileCategory.DOCUMENT,
        metadata: dict[str, Any] | None = None,
    ) -> StoredFile:
        """Upload a file to local storage."""
        file_path = self._get_full_path(key)

        # Create directory if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(data)

        # Get content type from extension if not provided
        if content_type == "application/octet-stream":
            guessed_type, _ = mimetypes.guess_type(key)
            if guessed_type:
                content_type = guessed_type

        filename = Path(key).name

        logger.info("File uploaded to local storage", key=key, size=len(data))

        return StoredFile(
            key=key,
            filename=filename,
            content_type=content_type,
            size_bytes=len(data),
            category=category,
            storage_type=self.storage_type,
            url=f"{self.public_base_url}/{key}",
            public_url=f"{self.public_base_url}/{key}",
            metadata=metadata or {},
        )

    async def download(self, key: str) -> bytes | None:
        """Download a file from local storage."""
        file_path = self._get_full_path(key)

        if not file_path.exists():
            logger.warning("File not found", key=key)
            return None

        try:
            async with aiofiles.open(file_path, "rb") as f:
                return await f.read()
        except Exception as e:
            logger.error("Failed to download file", key=key, error=str(e))
            return None

    async def delete(self, key: str) -> bool:
        """Delete a file from local storage."""
        file_path = self._get_full_path(key)

        if not file_path.exists():
            return False

        try:
            await aiofiles.os.remove(file_path)
            logger.info("File deleted from local storage", key=key)
            return True
        except Exception as e:
            logger.error("Failed to delete file", key=key, error=str(e))
            return False

    async def exists(self, key: str) -> bool:
        """Check if a file exists."""
        file_path = self._get_full_path(key)
        return file_path.exists()

    async def get_url(
        self,
        key: str,
        expires_in: int | None = None,
    ) -> str | None:
        """Get a URL for the file."""
        if not await self.exists(key):
            return None

        return f"{self.public_base_url}/{key}"

    async def list_files(
        self,
        prefix: str = "",
        max_results: int = 1000,
    ) -> list[StoredFile]:
        """List files with optional prefix."""
        search_path = self._get_full_path(prefix) if prefix else self.base_path
        files = []

        if not search_path.exists():
            return files

        count = 0
        for root, _, filenames in os.walk(search_path):
            for filename in filenames:
                if count >= max_results:
                    break

                file_path = Path(root) / filename
                relative_path = file_path.relative_to(self.base_path)
                key = str(relative_path)

                stat = file_path.stat()
                content_type, _ = mimetypes.guess_type(filename)

                files.append(StoredFile(
                    key=key,
                    filename=filename,
                    content_type=content_type or "application/octet-stream",
                    size_bytes=stat.st_size,
                    category=FileCategory.DOCUMENT,
                    storage_type=self.storage_type,
                    url=f"{self.public_base_url}/{key}",
                    created_at=datetime.fromtimestamp(stat.st_ctime, tz=UTC),
                ))

                count += 1

        return files

    async def get_stats(self) -> dict[str, Any]:
        """Get storage statistics."""
        total_size = 0
        file_count = 0

        for root, _, filenames in os.walk(self.base_path):
            for filename in filenames:
                file_path = Path(root) / filename
                total_size += file_path.stat().st_size
                file_count += 1

        return {
            "storage_type": self.storage_type.value,
            "base_path": str(self.base_path),
            "total_size_bytes": total_size,
            "file_count": file_count,
        }
