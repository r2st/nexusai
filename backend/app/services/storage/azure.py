"""Azure Blob Storage backend."""

import mimetypes
from datetime import UTC, datetime, timedelta
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


class AzureBlobStorageBackend(StorageBackend):
    """Azure Blob Storage backend."""

    storage_type = StorageType.AZURE_BLOB

    def __init__(self, config: StorageConfig):
        super().__init__(config)
        self.container_name = config.container_name or "nexusai"
        self._client = None
        self._container_client = None

    def _get_client(self):
        """Get or create Azure Blob client."""
        if self._client is None:
            try:
                from azure.storage.blob import BlobServiceClient

                if self.config.connection_string:
                    self._client = BlobServiceClient.from_connection_string(
                        self.config.connection_string
                    )
                else:
                    account_url = self.config.endpoint_url or f"https://{self.config.extra.get('account_name')}.blob.core.windows.net"
                    self._client = BlobServiceClient(
                        account_url=account_url,
                        credential=self.config.access_key,
                    )

                self._container_client = self._client.get_container_client(
                    self.container_name
                )

                # Create container if it doesn't exist
                if not self._container_client.exists():
                    self._container_client.create_container()

            except ImportError:
                logger.error("azure-storage-blob not installed")
                raise

        return self._client, self._container_client

    async def upload(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        category: FileCategory = FileCategory.DOCUMENT,
        metadata: dict[str, Any] | None = None,
    ) -> StoredFile:
        """Upload a file to Azure Blob Storage."""
        import asyncio

        _, container_client = self._get_client()

        # Get content type from extension if not provided
        if content_type == "application/octet-stream":
            guessed_type, _ = mimetypes.guess_type(key)
            if guessed_type:
                content_type = guessed_type

        blob_client = container_client.get_blob_client(key)

        # Run in executor
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: blob_client.upload_blob(
                data,
                overwrite=True,
                content_settings={"content_type": content_type},
                metadata=metadata,
            ),
        )

        url = blob_client.url

        logger.info("File uploaded to Azure Blob", container=self.container_name, key=key)

        return StoredFile(
            key=key,
            filename=key.split("/")[-1],
            content_type=content_type,
            size_bytes=len(data),
            category=category,
            storage_type=self.storage_type,
            url=url,
            metadata=metadata or {},
        )

    async def download(self, key: str) -> bytes | None:
        """Download a file from Azure Blob Storage."""
        import asyncio

        _, container_client = self._get_client()
        blob_client = container_client.get_blob_client(key)

        try:
            loop = asyncio.get_event_loop()
            download_stream = await loop.run_in_executor(
                None,
                blob_client.download_blob,
            )
            return await loop.run_in_executor(None, download_stream.readall)
        except Exception as e:
            logger.error("Failed to download from Azure Blob", key=key, error=str(e))
            return None

    async def delete(self, key: str) -> bool:
        """Delete a file from Azure Blob Storage."""
        import asyncio

        _, container_client = self._get_client()
        blob_client = container_client.get_blob_client(key)

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, blob_client.delete_blob)
            logger.info("File deleted from Azure Blob", key=key)
            return True
        except Exception as e:
            logger.error("Failed to delete from Azure Blob", key=key, error=str(e))
            return False

    async def exists(self, key: str) -> bool:
        """Check if a file exists in Azure Blob Storage."""
        import asyncio

        _, container_client = self._get_client()
        blob_client = container_client.get_blob_client(key)

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, blob_client.exists)

    async def get_url(
        self,
        key: str,
        expires_in: int | None = None,
    ) -> str | None:
        """Get a SAS URL for the file."""
        import asyncio
        from datetime import timezone

        try:
            from azure.storage.blob import generate_blob_sas, BlobSasPermissions

            _, container_client = self._get_client()
            blob_client = container_client.get_blob_client(key)

            expires_in = expires_in or self.config.url_expiry_seconds
            expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

            # Get account info
            account_name = self._client.account_name
            account_key = self.config.access_key

            if account_key:
                loop = asyncio.get_event_loop()
                sas_token = await loop.run_in_executor(
                    None,
                    lambda: generate_blob_sas(
                        account_name=account_name,
                        container_name=self.container_name,
                        blob_name=key,
                        account_key=account_key,
                        permission=BlobSasPermissions(read=True),
                        expiry=expiry,
                    ),
                )
                return f"{blob_client.url}?{sas_token}"

            return blob_client.url

        except Exception as e:
            logger.error("Failed to generate SAS URL", key=key, error=str(e))
            return None

    async def list_files(
        self,
        prefix: str = "",
        max_results: int = 1000,
    ) -> list[StoredFile]:
        """List files in Azure Blob Storage with optional prefix."""
        import asyncio

        _, container_client = self._get_client()
        files = []

        try:
            loop = asyncio.get_event_loop()
            blobs = await loop.run_in_executor(
                None,
                lambda: list(container_client.list_blobs(
                    name_starts_with=prefix,
                    results_per_page=max_results,
                )),
            )

            for blob in blobs[:max_results]:
                content_type, _ = mimetypes.guess_type(blob.name)

                files.append(StoredFile(
                    key=blob.name,
                    filename=blob.name.split("/")[-1],
                    content_type=content_type or blob.content_settings.content_type or "application/octet-stream",
                    size_bytes=blob.size,
                    category=FileCategory.DOCUMENT,
                    storage_type=self.storage_type,
                    etag=blob.etag,
                    created_at=blob.creation_time,
                    metadata=blob.metadata or {},
                ))

        except Exception as e:
            logger.error("Failed to list Azure Blob objects", error=str(e))

        return files
