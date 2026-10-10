"""Tests for GB049 M8 performance optimizations."""

from unittest.mock import AsyncMock, MagicMock, patch


class TestDocumentServiceLazyLoading:
    """Verify DocumentService defers heavy imports until needed."""

    def test_init_does_not_import_langchain(self):
        """DocumentService.__init__ should not trigger langchain imports."""
        import sys

        modules_before = set(sys.modules.keys())

        from app.services.document import DocumentService

        mock_db = AsyncMock()
        svc = DocumentService(mock_db)

        modules_after = set(sys.modules.keys())
        new_modules = modules_after - modules_before

        langchain_modules = [m for m in new_modules if "langchain" in m]
        assert langchain_modules == [], (
            f"DocumentService.__init__ eagerly imported: {langchain_modules}"
        )
        assert svc._embeddings is None
        assert svc._text_splitter is None

    def test_embeddings_property_is_lazy(self):
        """embeddings property should import on first access only."""
        from app.services.document import DocumentService

        mock_db = AsyncMock()
        svc = DocumentService(mock_db)

        assert svc._embeddings is None

        with patch("app.services.document.settings") as mock_settings:
            mock_settings.EMBEDDING_MODEL = "text-embedding-3-small"
            mock_settings.OPENAI_API_KEY = "test-key"
            mock_settings.EMBEDDING_DIMENSIONS = 1536
            with patch(
                "langchain_openai.OpenAIEmbeddings"
            ) as mock_embeddings_cls:
                mock_embeddings_cls.return_value = MagicMock()
                result = svc.embeddings
                assert result is not None
                assert svc._embeddings is result
                # Second access should not re-create
                result2 = svc.embeddings
                assert result2 is result
                mock_embeddings_cls.assert_called_once()

    def test_text_splitter_property_is_lazy(self):
        """text_splitter property should import on first access only."""
        from app.services.document import DocumentService

        mock_db = AsyncMock()
        svc = DocumentService(mock_db)

        assert svc._text_splitter is None

        with patch("app.services.document.settings") as mock_settings:
            mock_settings.CHUNK_SIZE = 1000
            mock_settings.CHUNK_OVERLAP = 200
            with patch(
                "langchain_text_splitters.RecursiveCharacterTextSplitter"
            ) as mock_splitter_cls:
                mock_splitter_cls.return_value = MagicMock()
                result = svc.text_splitter
                assert result is not None
                assert svc._text_splitter is result
                result2 = svc.text_splitter
                assert result2 is result
                mock_splitter_cls.assert_called_once()


class TestMiddlewareHealthCheckSkip:
    """Verify ErrorTrackingMiddleware skips health endpoints."""

    def test_skip_paths_defined(self):
        from app.core.middleware import ErrorTrackingMiddleware

        assert "/" in ErrorTrackingMiddleware._SKIP_PATHS
        assert "/health" in ErrorTrackingMiddleware._SKIP_PATHS
        assert "/healthz" in ErrorTrackingMiddleware._SKIP_PATHS
