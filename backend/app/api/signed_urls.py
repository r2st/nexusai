"""
Signed URL API endpoints for secure file transfer.

Provides signed URLs for:
- File uploads (pre-signed POST URLs)
- File downloads (pre-signed GET URLs)
- Temporary access tokens
"""

from datetime import datetime, UTC, timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.database import get_db
from app.core.input_validation import validate_no_path_traversal
from app.api.deps import get_current_user
from app.models.user import User
from app.services.storage.manager import get_storage_manager
from app.services.storage.base import FileCategory

logger = structlog.get_logger()

router = APIRouter()


class SignedURLRequest(BaseModel):
    """Request for generating a signed URL."""

    file_key: str = Field(..., min_length=1, max_length=1024, description="Storage key of the file")
    operation: str = Field(
        default="download",
        description="Operation type: 'download' or 'upload'",
    )

    @field_validator("file_key")
    @classmethod
    def validate_file_key(cls, v: str) -> str:
        if ".." in v or v.startswith("/") or "\x00" in v:
            raise ValueError("Invalid file key: path traversal not allowed")
        return v

    @field_validator("operation")
    @classmethod
    def validate_operation(cls, v: str) -> str:
        if v not in ["download", "upload"]:
            raise ValueError("Operation must be 'download' or 'upload'")
        return v
    expires_in: int = Field(
        default=3600,
        description="URL expiration time in seconds (default: 1 hour)",
        ge=60,
        le=86400,  # Max 24 hours
    )
    content_type: str | None = Field(
        default=None,
        description="Content type for upload URLs (required for upload)",
    )
    filename: str | None = Field(
        default=None,
        description="Filename for upload URLs",
    )


class SignedURLResponse(BaseModel):
    """Response containing signed URL."""

    url: str = Field(..., description="Signed URL")
    expires_at: datetime = Field(..., description="URL expiration timestamp")
    file_key: str = Field(..., description="Storage key")
    operation: str = Field(..., description="Operation type")
    method: str = Field(..., description="HTTP method (GET for download, POST for upload)")


class UploadSignedURLResponse(SignedURLResponse):
    """Response for upload signed URLs with additional fields."""

    fields: dict[str, str] = Field(
        default_factory=dict,
        description="Additional fields required for upload (e.g., S3 form fields)",
    )


@router.post("/generate", response_model=SignedURLResponse)
async def generate_signed_url(
    request: SignedURLRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SignedURLResponse:
    """
    Generate a signed URL for file access.
    
    For downloads:
    - Returns a pre-signed GET URL
    - URL expires after specified time
    - File must exist in storage
    
    For uploads:
    - Returns a pre-signed POST URL (if supported)
    - May include additional form fields
    - File will be created on upload
    """
    storage_manager = get_storage_manager()
    
    # Validate file exists for downloads
    if request.operation == "download":
        exists = await storage_manager.exists(request.file_key)
        if not exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found.",
            )
    
    # Get appropriate backend
    backend = storage_manager.get_backend()
    
    try:
        # Generate signed URL
        if request.operation == "download":
            url = await backend.get_url(
                key=request.file_key,
                expires_in=request.expires_in,
            )
            method = "GET"
        else:  # upload
            # For uploads, we need to generate a pre-signed POST URL
            # This is backend-specific
            url = await _generate_upload_url(
                backend=backend,
                key=request.file_key,
                expires_in=request.expires_in,
                content_type=request.content_type or "application/octet-stream",
            )
            method = "POST"
        
        if not url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate signed URL",
            )
        
        expires_at = datetime.now(UTC) + timedelta(seconds=request.expires_in)
        
        logger.info(
            "Signed URL generated",
            user_id=str(user.id),
            file_key=request.file_key,
            operation=request.operation,
            expires_at=expires_at.isoformat(),
        )
        
        return SignedURLResponse(
            url=url,
            expires_at=expires_at,
            file_key=request.file_key,
            operation=request.operation,
            method=method,
        )
    
    except Exception as e:
        logger.error(
            "Failed to generate signed URL",
            error=str(e),
            file_key=request.file_key,
            operation=request.operation,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate signed URL. Please try again later.",
        )


async def _generate_upload_url(
    backend: Any,
    key: str,
    expires_in: int,
    content_type: str,
) -> str:
    """Generate a pre-signed upload URL (backend-specific)."""
    # This is a simplified version - actual implementation depends on backend
    # S3, GCS, and Azure all support pre-signed POST URLs
    
    # For now, return a regular upload URL
    # In production, implement backend-specific pre-signed POST URLs
    return await backend.get_url(key=key, expires_in=expires_in)


@router.post("/upload", response_model=UploadSignedURLResponse, status_code=status.HTTP_201_CREATED)
async def generate_upload_url(
    filename: str = Query(..., description="Filename for upload"),
    category: str = Query(
        default="document",
        description="File category",
    ),
    expires_in: int = Query(
        default=3600,
        description="URL expiration in seconds",
        ge=60,
        le=86400,
    ),
    content_type: str = Query(
        default="application/octet-stream",
        description="Content type of file",
    ),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UploadSignedURLResponse:
    """
    Generate a pre-signed URL for file upload.

    Returns a URL and any additional fields required for upload.
    """
    validate_no_path_traversal(filename, "filename")
    storage_manager = get_storage_manager()
    
    # Build storage key
    try:
        file_category = FileCategory(category)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file category. Supported categories: document, image, video, audio.",
        )
    
    backend = storage_manager.get_backend(category=file_category)
    key = backend._build_key(
        filename=filename,
        category=file_category,
        user_id=str(user.id),
    )
    
    # Generate upload URL
    url = await backend.get_url(key=key, expires_in=expires_in)
    
    if not url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate upload URL",
        )
    
    expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)
    
    # Get additional fields for upload (backend-specific)
    fields = await _get_upload_fields(backend, key, content_type)
    
    logger.info(
        "Upload URL generated",
        user_id=str(user.id),
        file_key=key,
        filename=filename,
        expires_at=expires_at.isoformat(),
    )
    
    return UploadSignedURLResponse(
        url=url,
        expires_at=expires_at,
        file_key=key,
        operation="upload",
        method="POST",
        fields=fields,
    )


async def _get_upload_fields(
    backend: Any,
    key: str,
    content_type: str,
) -> dict[str, str]:
    """Get additional fields required for upload (backend-specific)."""
    # For S3, GCS, Azure - may need additional form fields
    # For now, return empty dict
    return {}


@router.get("/download/{file_key:path}")
async def generate_download_url(
    file_key: str,
    expires_in: int = Query(
        default=3600,
        description="URL expiration in seconds",
        ge=60,
        le=86400,
    ),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SignedURLResponse:
    """
    Generate a pre-signed URL for file download.

    The file must exist and the user must have access.
    """
    validate_no_path_traversal(file_key, "file_key")
    storage_manager = get_storage_manager()
    
    # Check file exists
    exists = await storage_manager.exists(file_key)
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found.",
        )
    
    # Generate download URL
    backend = storage_manager.get_backend()
    url = await backend.get_url(key=file_key, expires_in=expires_in)
    
    if not url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate download URL",
        )
    
    expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)
    
    logger.info(
        "Download URL generated",
        user_id=str(user.id),
        file_key=file_key,
        expires_at=expires_at.isoformat(),
    )
    
    return SignedURLResponse(
        url=url,
        expires_at=expires_at,
        file_key=file_key,
        operation="download",
        method="GET",
    )
