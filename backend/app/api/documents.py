"""Documents API endpoints for RAG."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.api.deps import get_current_user

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.services.document import DocumentService

logger = structlog.get_logger()

router = APIRouter()


class DocumentResponse(BaseModel):
    """Document response model."""

    id: str
    original_filename: str
    file_size: int
    mime_type: str
    document_type: str
    status: str
    chunk_count: int
    created_at: str

    class Config:
        from_attributes = True


class SearchRequest(BaseModel):
    """Document search request."""

    query: str = Field(..., min_length=1, max_length=10000)
    limit: int = Field(default=10, ge=1, le=100)
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class SearchResult(BaseModel):
    """Search result item."""

    id: str
    document_id: str
    content: str
    chunk_index: int
    filename: str
    similarity: float


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Upload a document for RAG."""
    # Validate file size
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE // (1024*1024)}MB",
        )

    # Validate file extension
    if file.filename:
        ext = "." + file.filename.split(".")[-1].lower() if "." in file.filename else ""
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type not allowed. Allowed types: {settings.ALLOWED_EXTENSIONS}",
            )

    doc_service = DocumentService(db)
    document = await doc_service.upload_document(
        user_id=user.id,
        filename=file.filename or "unnamed",
        content=content,
        mime_type=file.content_type or "application/octet-stream",
    )

    return DocumentResponse(
        id=document.id,
        original_filename=document.original_filename,
        file_size=document.file_size,
        mime_type=document.mime_type,
        document_type=document.document_type,
        status=document.status,
        chunk_count=document.chunk_count,
        created_at=document.created_at.isoformat(),
    )


@router.post("/{document_id}/process", response_model=DocumentResponse)
async def process_document(
    document_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Process an uploaded document (extract, chunk, embed)."""
    doc_service = DocumentService(db)

    document = await doc_service.get_document(document_id, user.id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    try:
        document = await doc_service.process_document(document)
    except Exception as e:
        logger.error("Failed to process document", document_id=document_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process document. Please try again later.",
        )

    return DocumentResponse(
        id=document.id,
        original_filename=document.original_filename,
        file_size=document.file_size,
        mime_type=document.mime_type,
        document_type=document.document_type,
        status=document.status,
        chunk_count=document.chunk_count,
        created_at=document.created_at.isoformat(),
    )


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    limit: int = 50,
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentResponse]:
    """List user's documents."""
    doc_service = DocumentService(db)
    documents = await doc_service.list_documents(user.id, limit, offset)

    return [
        DocumentResponse(
            id=d.id,
            original_filename=d.original_filename,
            file_size=d.file_size,
            mime_type=d.mime_type,
            document_type=d.document_type,
            status=d.status,
            chunk_count=d.chunk_count,
            created_at=d.created_at.isoformat(),
        )
        for d in documents
    ]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Get a document by ID."""
    doc_service = DocumentService(db)
    document = await doc_service.get_document(document_id, user.id)

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return DocumentResponse(
        id=document.id,
        original_filename=document.original_filename,
        file_size=document.file_size,
        mime_type=document.mime_type,
        document_type=document.document_type,
        status=document.status,
        chunk_count=document.chunk_count,
        created_at=document.created_at.isoformat(),
    )


@router.post("/search", response_model=list[SearchResult])
async def search_documents(
    request: SearchRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SearchResult]:
    """Search documents using semantic similarity."""
    doc_service = DocumentService(db)

    results = await doc_service.search_documents(
        user_id=user.id,
        query=request.query,
        limit=request.limit,
        similarity_threshold=request.similarity_threshold,
    )

    return [SearchResult(**r) for r in results]


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a document."""
    doc_service = DocumentService(db)

    document = await doc_service.get_document(document_id, user.id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    await doc_service.delete_document(document)
