"""AWS S3 storage backend."""

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


class S3StorageBackend(StorageBackend):
    """AWS S3 storage backend."""

    storage_type = StorageType.S3

    def __init__(self, config: StorageConfig):
        super().__init__(config)
        self.bucket_name = config.bucket_name
        self.region = config.region or "us-east-1"
        self._client = None

    def _get_client(self):
        """Get or create S3 client."""
        if self._client is None:
            try:
                import boto3
                from botocore.config import Config

                boto_config = Config(
                    region_name=self.region,
                    signature_version="s3v4",
                )

                kwargs = {
                    "config": boto_config,
                }

                if self.config.access_key:
                    kwargs["aws_access_key_id"] = self.config.access_key
                    kwargs["aws_secret_access_key"] = self.config.secret_key

                if self.config.endpoint_url:
                    kwargs["endpoint_url"] = self.config.endpoint_url

                self._client = boto3.client("s3", **kwargs)

            except ImportError:
                logger.error("boto3 not installed")
                raise

        return self._client

    async def upload(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        category: FileCategory = FileCategory.DOCUMENT,
        metadata: dict[str, Any] | None = None,
    ) -> StoredFile:
        """Upload a file to S3."""
        import asyncio

        client = self._get_client()

        # Get content type from extension if not provided
        if content_type == "application/octet-stream":
            guessed_type, _ = mimetypes.guess_type(key)
            if guessed_type:
                content_type = guessed_type

        extra_args: dict[str, Any] = {
            "ContentType": content_type,
        }

        if metadata:
            extra_args["Metadata"] = {k: str(v) for k, v in metadata.items()}

        # Run in executor to not block
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=data,
                **extra_args,
            ),
        )

        # Generate signed URL
        url = await self.get_url(key)

        logger.info("File uploaded to S3", bucket=self.bucket_name, key=key)

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
        """Download a file from S3."""
        import asyncio

        client = self._get_client()

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.get_object(Bucket=self.bucket_name, Key=key),
            )
            return response["Body"].read()
        except client.exceptions.NoSuchKey:
            logger.warning("File not found in S3", key=key)
            return None
        except Exception as e:
            logger.error("Failed to download from S3", key=key, error=str(e))
            return None

    async def delete(self, key: str) -> bool:
        """Delete a file from S3."""
        import asyncio

        client = self._get_client()

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: client.delete_object(Bucket=self.bucket_name, Key=key),
            )
            logger.info("File deleted from S3", key=key)
            return True
        except Exception as e:
            logger.error("Failed to delete from S3", key=key, error=str(e))
            return False

    async def exists(self, key: str) -> bool:
        """Check if a file exists in S3."""
        import asyncio

        client = self._get_client()

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: client.head_object(Bucket=self.bucket_name, Key=key),
            )
            return True
        except client.exceptions.ClientError as e:
            if e.response.get("Error", {}).get("Code") == "404":
                return False
            raise

    async def get_url(
        self,
        key: str,
        expires_in: int | None = None,
    ) -> str | None:
        """Get a presigned URL for the file."""
        import asyncio

        client = self._get_client()
        expires_in = expires_in or self.config.url_expiry_seconds

        try:
            loop = asyncio.get_event_loop()
            url = await loop.run_in_executor(
                None,
                lambda: client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self.bucket_name, "Key": key},
                    ExpiresIn=expires_in,
                ),
            )
            return url
        except Exception as e:
            logger.error("Failed to generate presigned URL", key=key, error=str(e))
            return None

    async def list_files(
        self,
        prefix: str = "",
        max_results: int = 1000,
    ) -> list[StoredFile]:
        """List files in S3 with optional prefix."""
        import asyncio

        client = self._get_client()
        files = []

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.list_objects_v2(
                    Bucket=self.bucket_name,
                    Prefix=prefix,
                    MaxKeys=max_results,
                ),
            )

            for obj in response.get("Contents", []):
                key = obj["Key"]
                content_type, _ = mimetypes.guess_type(key)

                files.append(StoredFile(
                    key=key,
                    filename=key.split("/")[-1],
                    content_type=content_type or "application/octet-stream",
                    size_bytes=obj["Size"],
                    category=FileCategory.DOCUMENT,
                    storage_type=self.storage_type,
                    etag=obj.get("ETag", "").strip('"'),
                    created_at=obj.get("LastModified"),
                ))

        except Exception as e:
            logger.error("Failed to list S3 objects", error=str(e))

        return files

    async def get_upload_url(
        self,
        key: str,
        content_type: str = "application/octet-stream",
        expires_in: int = 3600,
    ) -> str | None:
        """Get a presigned URL for uploading."""
        import asyncio

        client = self._get_client()

        try:
            loop = asyncio.get_event_loop()
            url = await loop.run_in_executor(
                None,
                lambda: client.generate_presigned_url(
                    "put_object",
                    Params={
                        "Bucket": self.bucket_name,
                        "Key": key,
                        "ContentType": content_type,
                    },
                    ExpiresIn=expires_in,
                ),
            )
            return url
        except Exception as e:
            logger.error("Failed to generate upload URL", key=key, error=str(e))
            return None
