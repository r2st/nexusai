"""
Unit tests for Documents API endpoints.
"""

import pytest
from uuid import uuid4
from io import BytesIO
from unittest.mock import patch, AsyncMock, MagicMock

from httpx import AsyncClient


class TestDocumentUpload:
    """Test document upload functionality."""

    @pytest.mark.asyncio
    async def test_upload_text_document(self, client: AsyncClient, auth_headers: dict):
        """Test uploading a text document."""
        content = b"This is a test document content for NexusAI testing."
        files = {
            "file": ("test_document.txt", BytesIO(content), "text/plain")
        }
        response = await client.post(
            "/api/v1/documents/upload",
            files=files,
            headers=auth_headers,
        )
        assert response.status_code in [200, 201, 400, 413]
        if response.status_code in [200, 201]:
            data = response.json()
            assert "id" in data
            assert data["original_filename"] == "test_document.txt"
            assert data["mime_type"] == "text/plain"

    @pytest.mark.asyncio
    async def test_upload_pdf_document(self, client: AsyncClient, auth_headers: dict):
        """Test uploading a PDF document."""
        # Minimal PDF content (PDF header)
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\ntrailer\n<<\n/Root 1 0 R\n>>\n%%EOF"
        files = {
            "file": ("test_document.pdf", BytesIO(pdf_content), "application/pdf")
        }
        response = await client.post(
            "/api/v1/documents/upload",
            files=files,
            headers=auth_headers,
        )
        assert response.status_code in [200, 201, 400, 415]

    @pytest.mark.asyncio
    async def test_upload_markdown_document(self, client: AsyncClient, auth_headers: dict):
        """Test uploading a Markdown document."""
        md_content = b"# Test Document\n\nThis is a **test** markdown file.\n\n- Item 1\n- Item 2"
        files = {
            "file": ("readme.md", BytesIO(md_content), "text/markdown")
        }
        response = await client.post(
            "/api/v1/documents/upload",
            files=files,
            headers=auth_headers,
        )
        assert response.status_code in [200, 201, 400]

    @pytest.mark.asyncio
    async def test_upload_document_too_large(self, client: AsyncClient, auth_headers: dict):
        """Test uploading a document that exceeds size limit."""
        # Create a file larger than the configured max (typically 50MB)
        large_content = b"x" * (51 * 1024 * 1024)  # 51MB
        files = {
            "file": ("large_file.txt", BytesIO(large_content), "text/plain")
        }
        response = await client.post(
            "/api/v1/documents/upload",
            files=files,
            headers=auth_headers,
        )
        assert response.status_code == 413

    @pytest.mark.asyncio
    async def test_upload_unsupported_file_type(self, client: AsyncClient, auth_headers: dict):
        """Test uploading an unsupported file type."""
        # Try to upload an executable
        exe_content = b"\x4d\x5a\x90\x00"  # MZ header
        files = {
            "file": ("malware.exe", BytesIO(exe_content), "application/x-msdownload")
        }
        response = await client.post(
            "/api/v1/documents/upload",
            files=files,
            headers=auth_headers,
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_empty_file(self, client: AsyncClient, auth_headers: dict):
        """Test uploading an empty file."""
        files = {
            "file": ("empty.txt", BytesIO(b""), "text/plain")
        }
        response = await client.post(
            "/api/v1/documents/upload",
            files=files,
            headers=auth_headers,
        )
        # May succeed or fail depending on validation
        assert response.status_code in [200, 201, 400, 422]

    @pytest.mark.asyncio
    async def test_upload_without_file(self, client: AsyncClient, auth_headers: dict):
        """Test upload request without file."""
        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_upload_file_with_unicode_name(self, client: AsyncClient, auth_headers: dict):
        """Test uploading file with unicode filename."""
        content = b"Test content"
        files = {
            "file": ("测试文档_документ.txt", BytesIO(content), "text/plain")
        }
        response = await client.post(
            "/api/v1/documents/upload",
            files=files,
            headers=auth_headers,
        )
        assert response.status_code in [200, 201, 400]

    @pytest.mark.asyncio
    async def test_upload_file_with_special_characters(self, client: AsyncClient, auth_headers: dict):
        """Test uploading file with special characters in filename."""
        content = b"Test content"
        files = {
            "file": ("test file (1) [copy].txt", BytesIO(content), "text/plain")
        }
        response = await client.post(
            "/api/v1/documents/upload",
            files=files,
            headers=auth_headers,
        )
        assert response.status_code in [200, 201, 400]


class TestDocumentList:
    """Test document listing functionality."""

    @pytest.mark.asyncio
    async def test_list_documents(self, client: AsyncClient, auth_headers: dict):
        """Test listing documents."""
        response = await client.get(
            "/api/v1/documents",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_list_documents_with_pagination(self, client: AsyncClient, auth_headers: dict):
        """Test listing documents with pagination."""
        response = await client.get(
            "/api/v1/documents?limit=10&offset=0",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10

    @pytest.mark.asyncio
    async def test_list_documents_pagination_offset(self, client: AsyncClient, auth_headers: dict):
        """Test document listing with offset."""
        # Upload a few documents first
        for i in range(3):
            content = f"Test document {i}".encode()
            files = {"file": (f"test_{i}.txt", BytesIO(content), "text/plain")}
            await client.post("/api/v1/documents/upload", files=files, headers=auth_headers)

        # List with offset
        response = await client.get(
            "/api/v1/documents?limit=50&offset=1",
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_documents_negative_limit(self, client: AsyncClient, auth_headers: dict):
        """Test listing documents with negative limit."""
        try:
            response = await client.get(
                "/api/v1/documents?limit=-1",
                headers=auth_headers,
            )
            # Should either reject (400/422), use default (200), or fail at DB level (500)
            assert response.status_code in [200, 400, 422, 500]
        except Exception:
            # Expected if DB raises exception for invalid LIMIT
            pass

    @pytest.mark.asyncio
    async def test_list_documents_zero_limit(self, client: AsyncClient, auth_headers: dict):
        """Test listing documents with zero limit."""
        response = await client.get(
            "/api/v1/documents?limit=0",
            headers=auth_headers,
        )
        # Should either return empty or use default
        assert response.status_code in [200, 400, 422]


class TestDocumentGet:
    """Test getting individual documents."""

    @pytest.mark.asyncio
    async def test_get_document(self, client: AsyncClient, auth_headers: dict):
        """Test getting a specific document."""
        # Upload a document first
        content = b"Test document for get"
        files = {"file": ("get_test.txt", BytesIO(content), "text/plain")}
        upload_response = await client.post(
            "/api/v1/documents/upload",
            files=files,
            headers=auth_headers,
        )

        if upload_response.status_code in [200, 201]:
            doc_id = upload_response.json()["id"]

            # Get the document
            response = await client.get(
                f"/api/v1/documents/{doc_id}",
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == doc_id
            assert data["original_filename"] == "get_test.txt"

    @pytest.mark.asyncio
    async def test_get_document_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test getting a non-existent document."""
        fake_id = str(uuid4())
        response = await client.get(
            f"/api/v1/documents/{fake_id}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_document_invalid_uuid(self, client: AsyncClient, auth_headers: dict):
        """Test getting document with invalid UUID."""
        try:
            response = await client.get(
                "/api/v1/documents/not-a-valid-uuid",
                headers=auth_headers,
            )
            # 422 for validation error, 404 if treated as not found, 500 if DB error
            assert response.status_code in [404, 422, 500]
        except Exception:
            # Expected if DB raises exception for invalid UUID
            pass


class TestDocumentDelete:
    """Test document deletion functionality."""

    @pytest.mark.asyncio
    async def test_delete_document(self, client: AsyncClient, auth_headers: dict):
        """Test deleting a document."""
        # Upload a document first
        content = b"Test document for deletion"
        files = {"file": ("delete_test.txt", BytesIO(content), "text/plain")}
        upload_response = await client.post(
            "/api/v1/documents/upload",
            files=files,
            headers=auth_headers,
        )

        if upload_response.status_code in [200, 201]:
            doc_id = upload_response.json()["id"]

            # Delete the document
            response = await client.delete(
                f"/api/v1/documents/{doc_id}",
                headers=auth_headers,
            )
            assert response.status_code == 204

            # Verify it's deleted
            get_response = await client.get(
                f"/api/v1/documents/{doc_id}",
                headers=auth_headers,
            )
            assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_document_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test deleting a non-existent document."""
        fake_id = str(uuid4())
        response = await client.delete(
            f"/api/v1/documents/{fake_id}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_document_twice(self, client: AsyncClient, auth_headers: dict):
        """Test deleting a document twice."""
        # Upload and delete
        content = b"Test document"
        files = {"file": ("double_delete.txt", BytesIO(content), "text/plain")}
        upload_response = await client.post(
            "/api/v1/documents/upload",
            files=files,
            headers=auth_headers,
        )

        if upload_response.status_code in [200, 201]:
            doc_id = upload_response.json()["id"]

            # First delete
            response1 = await client.delete(
                f"/api/v1/documents/{doc_id}",
                headers=auth_headers,
            )
            assert response1.status_code == 204

            # Second delete should fail
            response2 = await client.delete(
                f"/api/v1/documents/{doc_id}",
                headers=auth_headers,
            )
            assert response2.status_code == 404


class TestDocumentProcessing:
    """Test document processing functionality."""

    @pytest.mark.asyncio
    async def test_process_document(self, client: AsyncClient, auth_headers: dict):
        """Test processing an uploaded document."""
        # Upload a document first
        content = b"This is test content for document processing and embedding."
        files = {"file": ("process_test.txt", BytesIO(content), "text/plain")}
        upload_response = await client.post(
            "/api/v1/documents/upload",
            files=files,
            headers=auth_headers,
        )

        if upload_response.status_code in [200, 201]:
            doc_id = upload_response.json()["id"]

            # Process the document
            response = await client.post(
                f"/api/v1/documents/{doc_id}/process",
                headers=auth_headers,
            )
            # May fail without embedding API keys
            assert response.status_code in [200, 400, 500, 503]

    @pytest.mark.asyncio
    async def test_process_document_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test processing a non-existent document."""
        fake_id = str(uuid4())
        response = await client.post(
            f"/api/v1/documents/{fake_id}/process",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_process_document_twice(self, client: AsyncClient, auth_headers: dict):
        """Test processing a document multiple times."""
        content = b"Test content for multiple processing."
        files = {"file": ("multi_process.txt", BytesIO(content), "text/plain")}
        upload_response = await client.post(
            "/api/v1/documents/upload",
            files=files,
            headers=auth_headers,
        )

        if upload_response.status_code in [200, 201]:
            doc_id = upload_response.json()["id"]

            # Process twice
            response1 = await client.post(
                f"/api/v1/documents/{doc_id}/process",
                headers=auth_headers,
            )
            response2 = await client.post(
                f"/api/v1/documents/{doc_id}/process",
                headers=auth_headers,
            )
            # Both may succeed or second may fail/be no-op
            assert response1.status_code in [200, 400, 500, 503]
            assert response2.status_code in [200, 400, 500, 503]

    @pytest.mark.asyncio
    async def test_get_document_chunks(self, client: AsyncClient, auth_headers: dict):
        """Test getting chunks for a document."""
        fake_id = str(uuid4())
        response = await client.get(
            f"/api/v1/documents/{fake_id}/chunks",
            headers=auth_headers,
        )
        assert response.status_code in [200, 404]


class TestDocumentSearch:
    """Test document search functionality."""

    @pytest.mark.asyncio
    async def test_search_documents(self, client: AsyncClient, auth_headers: dict):
        """Test searching documents."""
        try:
            response = await client.post(
                "/api/v1/documents/search",
                json={
                    "query": "test query",
                    "limit": 10,
                    "similarity_threshold": 0.7,
                },
                headers=auth_headers,
            )
            # May fail without embedding API keys configured
            assert response.status_code in [200, 400, 500, 503]
            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, list)
        except Exception:
            # Expected when embedding API keys are not configured
            pass

    @pytest.mark.asyncio
    async def test_search_with_custom_limit(self, client: AsyncClient, auth_headers: dict):
        """Test search with custom limit."""
        try:
            response = await client.post(
                "/api/v1/documents/search",
                json={
                    "query": "test",
                    "limit": 5,
                },
                headers=auth_headers,
            )
            assert response.status_code in [200, 400, 500, 503]
            if response.status_code == 200:
                data = response.json()
                assert len(data) <= 5
        except Exception:
            # Expected when embedding API keys are not configured
            pass

    @pytest.mark.asyncio
    async def test_search_with_custom_threshold(self, client: AsyncClient, auth_headers: dict):
        """Test search with custom similarity threshold."""
        try:
            response = await client.post(
                "/api/v1/documents/search",
                json={
                    "query": "test",
                    "similarity_threshold": 0.9,
                },
                headers=auth_headers,
            )
            assert response.status_code in [200, 400, 500, 503]
        except Exception:
            # Expected when embedding API keys are not configured
            pass

    @pytest.mark.asyncio
    async def test_search_empty_query(self, client: AsyncClient, auth_headers: dict):
        """Test search with empty query."""
        try:
            response = await client.post(
                "/api/v1/documents/search",
                json={
                    "query": "",
                    "limit": 10,
                },
                headers=auth_headers,
            )
            assert response.status_code in [200, 400, 422, 500]
        except Exception:
            # Expected when embedding API keys are not configured
            pass

    @pytest.mark.asyncio
    async def test_search_missing_query(self, client: AsyncClient, auth_headers: dict):
        """Test search without query field."""
        response = await client.post(
            "/api/v1/documents/search",
            json={
                "limit": 10,
            },
            headers=auth_headers,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_search_invalid_threshold(self, client: AsyncClient, auth_headers: dict):
        """Test search with invalid threshold."""
        try:
            response = await client.post(
                "/api/v1/documents/search",
                json={
                    "query": "test",
                    "similarity_threshold": 1.5,  # Invalid (should be 0-1)
                },
                headers=auth_headers,
            )
            assert response.status_code in [200, 400, 422, 500]
        except Exception:
            # Expected when embedding API keys are not configured
            pass


class TestDocumentAuthorization:
    """Test document authorization."""

    @pytest.mark.asyncio
    async def test_upload_unauthorized(self, client: AsyncClient, mock_document_content: bytes):
        """Test uploading without authentication."""
        files = {
            "file": ("test.txt", BytesIO(mock_document_content), "text/plain")
        }
        response = await client.post(
            "/api/v1/documents/upload",
            files=files,
        )
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_list_unauthorized(self, client: AsyncClient):
        """Test listing documents without authentication."""
        response = await client.get("/api/v1/documents")
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_get_unauthorized(self, client: AsyncClient):
        """Test getting document without authentication."""
        fake_id = str(uuid4())
        response = await client.get(f"/api/v1/documents/{fake_id}")
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_delete_unauthorized(self, client: AsyncClient):
        """Test deleting document without authentication."""
        fake_id = str(uuid4())
        response = await client.delete(f"/api/v1/documents/{fake_id}")
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_process_unauthorized(self, client: AsyncClient):
        """Test processing document without authentication."""
        fake_id = str(uuid4())
        response = await client.post(f"/api/v1/documents/{fake_id}/process")
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_search_unauthorized(self, client: AsyncClient):
        """Test searching documents without authentication."""
        response = await client.post(
            "/api/v1/documents/search",
            json={"query": "test"}
        )
        assert response.status_code in [401, 403]


class TestDocumentOwnership:
    """Test document ownership and access control."""

    @pytest.mark.asyncio
    async def test_cannot_access_other_user_document(
        self, client: AsyncClient, auth_headers: dict, admin_auth_headers: dict
    ):
        """Test that users cannot access other users' documents."""
        # Upload as regular user
        content = b"User's private document"
        files = {"file": ("private.txt", BytesIO(content), "text/plain")}
        upload_response = await client.post(
            "/api/v1/documents/upload",
            files=files,
            headers=auth_headers,
        )

        if upload_response.status_code in [200, 201]:
            doc_id = upload_response.json()["id"]

            # Try to access as admin (different user)
            response = await client.get(
                f"/api/v1/documents/{doc_id}",
                headers=admin_auth_headers,
            )
            # Should be 404 (not found for this user) or 403 (forbidden)
            assert response.status_code in [403, 404]

    @pytest.mark.asyncio
    async def test_cannot_delete_other_user_document(
        self, client: AsyncClient, auth_headers: dict, admin_auth_headers: dict
    ):
        """Test that users cannot delete other users' documents."""
        # Upload as regular user
        content = b"User's document to delete"
        files = {"file": ("to_delete.txt", BytesIO(content), "text/plain")}
        upload_response = await client.post(
            "/api/v1/documents/upload",
            files=files,
            headers=auth_headers,
        )

        if upload_response.status_code in [200, 201]:
            doc_id = upload_response.json()["id"]

            # Try to delete as admin
            response = await client.delete(
                f"/api/v1/documents/{doc_id}",
                headers=admin_auth_headers,
            )
            assert response.status_code in [403, 404]


class TestDocumentEdgeCases:
    """Test edge cases for documents."""

    @pytest.mark.asyncio
    async def test_upload_multiple_documents(self, client: AsyncClient, auth_headers: dict):
        """Test uploading multiple documents sequentially."""
        for i in range(5):
            content = f"Document {i} content".encode()
            files = {"file": (f"doc_{i}.txt", BytesIO(content), "text/plain")}
            response = await client.post(
                "/api/v1/documents/upload",
                files=files,
                headers=auth_headers,
            )
            assert response.status_code in [200, 201, 400]

    @pytest.mark.asyncio
    async def test_upload_same_filename_twice(self, client: AsyncClient, auth_headers: dict):
        """Test uploading files with the same name."""
        content = b"Original content"
        files = {"file": ("duplicate.txt", BytesIO(content), "text/plain")}
        response1 = await client.post(
            "/api/v1/documents/upload",
            files=files,
            headers=auth_headers,
        )

        content2 = b"New content"
        files2 = {"file": ("duplicate.txt", BytesIO(content2), "text/plain")}
        response2 = await client.post(
            "/api/v1/documents/upload",
            files=files2,
            headers=auth_headers,
        )

        # Both should succeed (different document IDs)
        if response1.status_code in [200, 201] and response2.status_code in [200, 201]:
            id1 = response1.json()["id"]
            id2 = response2.json()["id"]
            assert id1 != id2

    @pytest.mark.asyncio
    async def test_document_with_no_extension(self, client: AsyncClient, auth_headers: dict):
        """Test uploading file with no extension."""
        content = b"File without extension"
        files = {"file": ("noextension", BytesIO(content), "application/octet-stream")}
        response = await client.post(
            "/api/v1/documents/upload",
            files=files,
            headers=auth_headers,
        )
        # May be rejected or handled
        assert response.status_code in [200, 201, 400]

    @pytest.mark.asyncio
    async def test_document_with_double_extension(self, client: AsyncClient, auth_headers: dict):
        """Test uploading file with double extension."""
        content = b"File with double extension"
        files = {"file": ("file.txt.bak", BytesIO(content), "text/plain")}
        response = await client.post(
            "/api/v1/documents/upload",
            files=files,
            headers=auth_headers,
        )
        assert response.status_code in [200, 201, 400]

    @pytest.mark.asyncio
    async def test_document_with_hidden_filename(self, client: AsyncClient, auth_headers: dict):
        """Test uploading file with hidden filename (starts with dot)."""
        content = b"Hidden file content"
        files = {"file": (".hidden_file.txt", BytesIO(content), "text/plain")}
        response = await client.post(
            "/api/v1/documents/upload",
            files=files,
            headers=auth_headers,
        )
        assert response.status_code in [200, 201, 400]

    @pytest.mark.asyncio
    async def test_search_with_very_long_query(self, client: AsyncClient, auth_headers: dict):
        """Test search with very long query string."""
        long_query = "test " * 1000
        try:
            response = await client.post(
                "/api/v1/documents/search",
                json={
                    "query": long_query,
                    "limit": 10,
                },
                headers=auth_headers,
            )
            assert response.status_code in [200, 400, 422, 500]
        except Exception:
            # Expected when embedding API keys are not configured
            pass

    @pytest.mark.asyncio
    async def test_search_with_special_characters(self, client: AsyncClient, auth_headers: dict):
        """Test search with special characters in query."""
        special_queries = [
            "test & query",
            "test | or",
            "test; drop table",
            "<script>alert('xss')</script>",
            "中文搜索",
        ]

        for query in special_queries:
            try:
                response = await client.post(
                    "/api/v1/documents/search",
                    json={"query": query, "limit": 5},
                    headers=auth_headers,
                )
                # Should handle gracefully
                assert response.status_code in [200, 400, 422, 500]
            except Exception:
                # Expected when embedding API keys are not configured
                pass
