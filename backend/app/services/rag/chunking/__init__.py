"""Document chunking strategies."""

import re
from abc import ABC, abstractmethod
from typing import Any

import structlog

from app.services.rag.config import ChunkingConfig
from app.services.rag.models import DocumentChunk, DocumentType

logger = structlog.get_logger()


class BaseChunker(ABC):
    """Base class for chunking strategies."""

    @abstractmethod
    def chunk(self, text: str, metadata: dict[str, Any] | None = None) -> list[DocumentChunk]:
        """Split text into chunks."""
        pass


class TextChunker(BaseChunker):
    """General text chunker with semantic awareness."""

    def __init__(self, config: ChunkingConfig):
        self.config = config

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (roughly 4 chars per token)."""
        return len(text) // 4

    def _split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        # Simple sentence splitter
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _split_into_paragraphs(self, text: str) -> list[str]:
        """Split text into paragraphs."""
        paragraphs = re.split(r'\n\s*\n', text)
        return [p.strip() for p in paragraphs if p.strip()]

    def chunk(self, text: str, metadata: dict[str, Any] | None = None) -> list[DocumentChunk]:
        """Split text into semantic chunks."""
        from uuid import uuid4

        chunks = []
        metadata = metadata or {}
        document_id = metadata.get("document_id", uuid4())

        # Split by paragraphs first
        paragraphs = self._split_into_paragraphs(text)

        current_chunk = ""
        current_start = 0
        chunk_index = 0

        for para in paragraphs:
            para_tokens = self._estimate_tokens(para)

            # If paragraph itself is too large, split by sentences
            if para_tokens > self.config.max_chunk_size:
                # Flush current chunk if any
                if current_chunk:
                    chunks.append(self._create_chunk(
                        content=current_chunk.strip(),
                        document_id=document_id,
                        chunk_index=chunk_index,
                        start_char=current_start,
                        end_char=current_start + len(current_chunk),
                        metadata=metadata,
                    ))
                    chunk_index += 1
                    current_chunk = ""

                # Split paragraph by sentences
                sentences = self._split_into_sentences(para)
                sentence_chunk = ""
                sentence_start = current_start

                for sentence in sentences:
                    sentence_tokens = self._estimate_tokens(sentence)

                    if self._estimate_tokens(sentence_chunk + " " + sentence) > self.config.chunk_size:
                        if sentence_chunk:
                            chunks.append(self._create_chunk(
                                content=sentence_chunk.strip(),
                                document_id=document_id,
                                chunk_index=chunk_index,
                                start_char=sentence_start,
                                end_char=sentence_start + len(sentence_chunk),
                                metadata=metadata,
                            ))
                            chunk_index += 1
                            sentence_chunk = sentence
                            sentence_start += len(sentence_chunk)
                        else:
                            # Single sentence too long, force add
                            chunks.append(self._create_chunk(
                                content=sentence.strip(),
                                document_id=document_id,
                                chunk_index=chunk_index,
                                start_char=sentence_start,
                                end_char=sentence_start + len(sentence),
                                metadata=metadata,
                            ))
                            chunk_index += 1
                            sentence_start += len(sentence)
                    else:
                        sentence_chunk += " " + sentence if sentence_chunk else sentence

                if sentence_chunk:
                    current_chunk = sentence_chunk
                    current_start = sentence_start

            # Check if adding paragraph exceeds chunk size
            elif self._estimate_tokens(current_chunk + "\n\n" + para) > self.config.chunk_size:
                # Save current chunk
                if current_chunk:
                    chunks.append(self._create_chunk(
                        content=current_chunk.strip(),
                        document_id=document_id,
                        chunk_index=chunk_index,
                        start_char=current_start,
                        end_char=current_start + len(current_chunk),
                        metadata=metadata,
                    ))
                    chunk_index += 1

                current_chunk = para
                current_start = text.find(para)
            else:
                current_chunk += "\n\n" + para if current_chunk else para

        # Add final chunk
        if current_chunk:
            chunks.append(self._create_chunk(
                content=current_chunk.strip(),
                document_id=document_id,
                chunk_index=chunk_index,
                start_char=current_start,
                end_char=current_start + len(current_chunk),
                metadata=metadata,
            ))

        return chunks

    def _create_chunk(
        self,
        content: str,
        document_id,
        chunk_index: int,
        start_char: int,
        end_char: int,
        metadata: dict[str, Any],
    ) -> DocumentChunk:
        """Create a document chunk."""
        from uuid import uuid4

        return DocumentChunk(
            id=uuid4(),
            document_id=document_id,
            content=content,
            chunk_index=chunk_index,
            start_char=start_char,
            end_char=end_char,
            token_count=self._estimate_tokens(content),
            metadata=metadata,
        )


class CodeChunker(BaseChunker):
    """Code-aware chunker that respects function/class boundaries."""

    LANGUAGE_PATTERNS = {
        "python": {
            "function": r'^(async\s+)?def\s+(\w+)\s*\(',
            "class": r'^class\s+(\w+)',
        },
        "javascript": {
            "function": r'^(async\s+)?function\s+(\w+)\s*\(|^const\s+(\w+)\s*=\s*(async\s+)?\(|^(\w+)\s*:\s*(async\s+)?function',
            "class": r'^class\s+(\w+)',
        },
        "typescript": {
            "function": r'^(async\s+)?function\s+(\w+)\s*\(|^(export\s+)?(const|let)\s+(\w+)\s*=',
            "class": r'^(export\s+)?class\s+(\w+)',
        },
    }

    def __init__(self, config: ChunkingConfig):
        self.config = config

    def _detect_language(self, text: str, metadata: dict | None = None) -> str:
        """Detect programming language."""
        if metadata and "language" in metadata:
            return metadata["language"]

        # Simple heuristics
        if "def " in text and ":" in text:
            return "python"
        if "function " in text or "const " in text or "=>" in text:
            return "javascript"
        if "interface " in text or ": " in text:
            return "typescript"

        return "unknown"

    def chunk(self, text: str, metadata: dict[str, Any] | None = None) -> list[DocumentChunk]:
        """Split code into semantic chunks."""
        from uuid import uuid4

        chunks = []
        metadata = metadata or {}
        document_id = metadata.get("document_id", uuid4())
        language = self._detect_language(text, metadata)

        # For now, fall back to line-based chunking for code
        lines = text.split("\n")
        current_chunk = []
        current_start = 0
        chunk_index = 0
        char_pos = 0

        for line in lines:
            current_chunk.append(line)
            chunk_text = "\n".join(current_chunk)

            if len(chunk_text) // 4 > self.config.chunk_size:
                # Save chunk
                if len(current_chunk) > 1:
                    content = "\n".join(current_chunk[:-1])
                    chunks.append(DocumentChunk(
                        id=uuid4(),
                        document_id=document_id,
                        content=content,
                        chunk_index=chunk_index,
                        start_char=current_start,
                        end_char=current_start + len(content),
                        token_count=len(content) // 4,
                        language=language,
                        metadata=metadata,
                    ))
                    chunk_index += 1
                    current_start += len(content) + 1
                    current_chunk = [line]

            char_pos += len(line) + 1

        # Final chunk
        if current_chunk:
            content = "\n".join(current_chunk)
            chunks.append(DocumentChunk(
                id=uuid4(),
                document_id=document_id,
                content=content,
                chunk_index=chunk_index,
                start_char=current_start,
                end_char=current_start + len(content),
                token_count=len(content) // 4,
                language=language,
                metadata=metadata,
            ))

        return chunks


def get_chunker(doc_type: DocumentType, config: ChunkingConfig) -> BaseChunker:
    """Get appropriate chunker for document type."""
    if doc_type == DocumentType.CODE:
        return CodeChunker(config)
    else:
        return TextChunker(config)
