"""Google Cloud Storage backend."""

import mimetypes
from datetime import datetime, timedelta
from typing import Any

import structlog

from app.services.storage.base import (
    FileCategory,
    StorageBackend,
    StorageConfig,
    StorageType,
    StoredFile,
)

logger = structlog.get_logger()


class GCSStorageBackend(StorageBackend):
    """Google Cloud Storage backend."""

    storage_type = StorageType.GCS

    def __init__(self, config: StorageConfig):
        super().__init__(config)
        self.bucket_name = config.bucket_name
        self.project_id = config.project_id
        self._client = None
        self._bucket = None

    def _get_client(self):
        """Get or create GCS client."""
        if self._client is None:
            try:
                from google.cloud import storage

                if self.config.credentials_path:
                    self._client = storage.Client.from_service_account_json(
                        self.config.credentials_path
                    )
                else:
                    self._client = storage.Client(project=self.project_id)

                self._bucket = self._client.bucket(self.bucket_name)

                # Create bucket if it doesn't exist
                if not self._bucket.exists():
                    self._bucket = self._client.create_bucket(
                        self.bucket_name,
                        location=self.config.region or "US",
                    )

            except ImportError:
                logger.error("google-cloud-storage not installed")
                raise

        return self._client, self._bucket

    async def upload(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        category: FileCategory = FileCategory.DOCUMENT,
        metadata: dict[str, Any] | None = None,
    ) -> StoredFile:
        """Upload a file to GCS."""
        import asyncio

        _, bucket = self._get_client()

        # Get content type from extension if not provided
        if content_type == "application/octet-stream":
            guessed_type, _ = mimetypes.guess_type(key)
            if guessed_type:
                content_type = guessed_type

        blob = bucket.blob(key)
        blob.content_type = content_type

        if metadata:
            blob.metadata = metadata

        # Run in executor
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: blob.upload_from_string(data, content_type=content_type),
        )

        url = await self.get_url(key)

        logger.info("File uploaded to GCS", bucket=self.bucket_name, key=key)

        return StoredFile(
            key=key,
            filename=key.split("/")[-1],
            content_type=content_type,
            size_bytes=len(data),
            category=category,
            storage_type=self.storage_type,
            url=url,
            public_url=f"https://storage.googleapis.com/{self.bucket_name}/{key}",
            metadata=metadata or {},
        )

    async def download(self, key: str) -> bytes | None:
        """Download a file from GCS."""
        import asyncio

        _, bucket = self._get_client()
        blob = bucket.blob(key)

        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, blob.download_as_bytes)
        except Exception as e:
            logger.error("Failed to download from GCS", key=key, error=str(e))
            return None

    async def delete(self, key: str) -> bool:
        """Delete a file from GCS."""
        import asyncio

        _, bucket = self._get_client()
        blob = bucket.blob(key)

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, blob.delete)
            logger.info("File deleted from GCS", key=key)
            return True
        except Exception as e:
            logger.error("Failed to delete from GCS", key=key, error=str(e))
            return False

    async def exists(self, key: str) -> bool:
        """Check if a file exists in GCS."""
        import asyncio

        _, bucket = self._get_client()
        blob = bucket.blob(key)

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, blob.exists)

    async def get_url(
        self,
        key: str,
        expires_in: int | None = None,
    ) -> str | None:
        """Get a signed URL for the file."""
        import asyncio

        _, bucket = self._get_client()
        blob = bucket.blob(key)

        expires_in = expires_in or self.config.url_expiry_seconds

        try:
            loop = asyncio.get_event_loop()
            url = await loop.run_in_executor(
                None,
                lambda: blob.generate_signed_url(
                    expiration=timedelta(seconds=expires_in),
                    method="GET",
                ),
            )
            return url
        except Exception as e:
            logger.error("Failed to generate signed URL", key=key, error=str(e))
            # Return public URL as fallback
            return f"https://storage.googleapis.com/{self.bucket_name}/{key}"

    async def list_files(
        self,
        prefix: str = "",
        max_results: int = 1000,
    ) -> list[StoredFile]:
        """List files in GCS with optional prefix."""
        import asyncio

        _, bucket = self._get_client()
        files = []

        try:
            loop = asyncio.get_event_loop()
            blobs = await loop.run_in_executor(
                None,
                lambda: list(bucket.list_blobs(prefix=prefix, max_results=max_results)),
            )

            for blob in blobs:
                content_type, _ = mimetypes.guess_type(blob.name)

                files.append(StoredFile(
                    key=blob.name,
                    filename=blob.name.split("/")[-1],
                    content_type=content_type or blob.content_type or "application/octet-stream",
                    size_bytes=blob.size or 0,
                    category=FileCategory.DOCUMENT,
                    storage_type=self.storage_type,
                    etag=blob.etag,
                    created_at=blob.time_created,
                    metadata=blob.metadata or {},
                ))

        except Exception as e:
            logger.error("Failed to list GCS objects", error=str(e))

        return files

    async def make_public(self, key: str) -> str | None:
        """Make a file publicly accessible."""
        import asyncio

        _, bucket = self._get_client()
        blob = bucket.blob(key)

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, blob.make_public)
            return f"https://storage.googleapis.com/{self.bucket_name}/{key}"
        except Exception as e:
            logger.error("Failed to make file public", key=key, error=str(e))
            return None
