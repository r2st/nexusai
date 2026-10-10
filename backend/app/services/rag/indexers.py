"""
Document Indexers

Specialized indexers for different content types.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
import logging
import re

from .vector_store import Document, VectorStore
from .embeddings import EmbeddingsService
from .chunking_strategy import CodeChunker, ChunkingConfig, ChunkingStrategy, get_chunker

logger = logging.getLogger(__name__)


@dataclass
class IndexingResult:
    """Result of an indexing operation."""
    documents_processed: int
    chunks_created: int
    chunks_indexed: int
    errors: List[str]
    duration_ms: int


class BaseIndexer(ABC):
    """Base class for document indexers."""
    
    def __init__(
        self,
        vector_store: VectorStore,
        embeddings: EmbeddingsService,
    ):
        self.vector_store = vector_store
        self.embeddings = embeddings
    
    @abstractmethod
    async def index(
        self,
        source: Any,
        tenant_id: str,
        **kwargs,
    ) -> IndexingResult:
        """Index content from the source."""
        pass
    
    async def _embed_and_store(
        self,
        documents: List[Document],
        collection: Optional[str] = None,
    ) -> int:
        """Embed documents and store in vector DB."""
        if not documents:
            return 0
        
        # Generate embeddings
        texts = [doc.content for doc in documents]
        results = await self.embeddings.embed_batch(texts)
        
        # Attach embeddings
        for doc, result in zip(documents, results):
            doc.embedding = result.embedding
        
        # Store in vector DB
        return await self.vector_store.index_documents(documents, collection)


class CodeIndexer(BaseIndexer):
    """
    Index code files from repositories.
    
    Features:
    - AST-aware chunking
    - Symbol extraction
    - Language detection
    - Incremental updates
    """
    
    LANGUAGE_EXTENSIONS = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".jsx": "javascript",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".rb": "ruby",
        ".php": "php",
        ".cs": "csharp",
        ".cpp": "cpp",
        ".c": "c",
        ".h": "c",
        ".hpp": "cpp",
    }
    
    def __init__(
        self,
        vector_store: VectorStore,
        embeddings: EmbeddingsService,
        chunking_config: Optional[ChunkingConfig] = None,
    ):
        super().__init__(vector_store, embeddings)
        self.chunker = CodeChunker()
        self.chunking_config = chunking_config or ChunkingConfig()
    
    async def index(
        self,
        source: Dict[str, Any],
        tenant_id: str,
        **kwargs,
    ) -> IndexingResult:
        """
        Index code from a source.
        
        Expected source format:
        {
            "repo": "owner/repo",
            "branch": "main",
            "files": [
                {"path": "src/main.py", "content": "..."},
                ...
            ]
        }
        """
        import time
        start_time = time.time()
        
        repo = source.get("repo", "unknown")
        branch = source.get("branch", "main")
        files = source.get("files", [])
        
        all_documents: List[Document] = []
        errors: List[str] = []
        chunks_created = 0
        
        for file_info in files:
            try:
                path = file_info["path"]
                content = file_info["content"]
                
                # Detect language
                language = self._detect_language(path)
                
                # Chunk the file
                chunks = self.chunker.chunk(
                    content,
                    self.chunking_config,
                    language,
                )
                chunks_created += len(chunks)
                
                # Create documents
                for i, chunk in enumerate(chunks):
                    doc = Document(
                        content=chunk.content,
                        source_type="code",
                        source_id=f"{repo}:{branch}:{path}:{i}",
                        source_url=f"https://github.com/{repo}/blob/{branch}/{path}#L{chunk.start_line}-L{chunk.end_line}",
                        tenant_id=tenant_id,
                        metadata={
                            "repo": repo,
                            "branch": branch,
                            "path": path,
                            "language": language,
                            "start_line": chunk.start_line,
                            "end_line": chunk.end_line,
                            "chunk_type": chunk.chunk_type,
                            "symbol_name": chunk.symbol_name,
                        },
                    )
                    all_documents.append(doc)
                    
            except Exception as e:
                errors.append(f"Error indexing {file_info.get('path', 'unknown')}: {str(e)}")
                logger.error(f"Indexing error: {e}")
        
        # Index in batches
        indexed = await self._embed_and_store(all_documents, kwargs.get("collection"))
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        return IndexingResult(
            documents_processed=len(files),
            chunks_created=chunks_created,
            chunks_indexed=indexed,
            errors=errors,
            duration_ms=elapsed_ms,
        )
    
    def _detect_language(self, path: str) -> Optional[str]:
        """Detect language from file extension."""
        for ext, lang in self.LANGUAGE_EXTENSIONS.items():
            if path.endswith(ext):
                return lang
        return None


class DocumentIndexer(BaseIndexer):
    """
    Index documentation files.
    
    Supports:
    - Markdown
    - RST
    - Plain text
    - ADRs
    - READMEs
    """
    
    def __init__(
        self,
        vector_store: VectorStore,
        embeddings: EmbeddingsService,
    ):
        super().__init__(vector_store, embeddings)
        self.chunker = get_chunker(ChunkingStrategy.SEMANTIC)
    
    async def index(
        self,
        source: Dict[str, Any],
        tenant_id: str,
        **kwargs,
    ) -> IndexingResult:
        """
        Index documentation.
        
        Expected source format:
        {
            "docs": [
                {"path": "README.md", "content": "...", "type": "readme"},
                {"path": "docs/adr/001.md", "content": "...", "type": "adr"},
            ]
        }
        """
        import time
        start_time = time.time()
        
        docs = source.get("docs", [])
        all_documents: List[Document] = []
        errors: List[str] = []
        chunks_created = 0
        
        config = ChunkingConfig(
            max_chunk_size=2000,
            min_chunk_size=200,
            chunk_overlap=100,
        )
        
        for doc_info in docs:
            try:
                path = doc_info["path"]
                content = doc_info["content"]
                doc_type = doc_info.get("type", "doc")
                
                # Parse markdown/RST
                processed = self._process_document(content, path)
                
                # Chunk
                chunks = self.chunker.chunk(processed, config)
                chunks_created += len(chunks)
                
                for i, chunk in enumerate(chunks):
                    doc = Document(
                        content=chunk.content,
                        source_type="doc",
                        source_id=f"doc:{path}:{i}",
                        source_url=doc_info.get("url"),
                        tenant_id=tenant_id,
                        metadata={
                            "path": path,
                            "doc_type": doc_type,
                            "title": self._extract_title(content),
                        },
                    )
                    all_documents.append(doc)
                    
            except Exception as e:
                errors.append(f"Error indexing doc {doc_info.get('path')}: {str(e)}")
        
        indexed = await self._embed_and_store(all_documents, kwargs.get("collection"))
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        return IndexingResult(
            documents_processed=len(docs),
            chunks_created=chunks_created,
            chunks_indexed=indexed,
            errors=errors,
            duration_ms=elapsed_ms,
        )
    
    def _process_document(self, content: str, path: str) -> str:
        """Process markdown/RST content."""
        # Remove code blocks for cleaner indexing
        # Keep headings and text
        processed = re.sub(r"```[\s\S]*?```", "[code block]", content)
        processed = re.sub(r"`[^`]+`", "", processed)
        return processed.strip()
    
    def _extract_title(self, content: str) -> Optional[str]:
        """Extract title from document."""
        # Look for # heading
        match = re.match(r"^#\s+(.+)$", content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return None


class TicketIndexer(BaseIndexer):
    """
    Index tickets from issue trackers (Jira, GitHub Issues, Linear).
    
    Indexes:
    - Title and description
    - Comments
    - Labels and metadata
    """
    
    async def index(
        self,
        source: Dict[str, Any],
        tenant_id: str,
        **kwargs,
    ) -> IndexingResult:
        """
        Index tickets.
        
        Expected source format:
        {
            "source": "jira",
            "tickets": [
                {
                    "key": "PROJ-123",
                    "summary": "...",
                    "description": "...",
                    "status": "Open",
                    "labels": ["bug"],
                    "comments": [{"body": "...", "author": "..."}],
                }
            ]
        }
        """
        import time
        start_time = time.time()
        
        source_system = source.get("source", "unknown")
        tickets = source.get("tickets", [])
        
        all_documents: List[Document] = []
        errors: List[str] = []
        
        for ticket in tickets:
            try:
                key = ticket["key"]
                
                # Index main ticket
                content = f"# {ticket['summary']}\n\n{ticket.get('description', '')}"
                
                doc = Document(
                    content=content,
                    source_type="ticket",
                    source_id=f"{source_system}:{key}",
                    source_url=ticket.get("url"),
                    tenant_id=tenant_id,
                    metadata={
                        "source_system": source_system,
                        "key": key,
                        "status": ticket.get("status"),
                        "priority": ticket.get("priority"),
                        "labels": ticket.get("labels", []),
                        "assignee": ticket.get("assignee"),
                    },
                )
                all_documents.append(doc)
                
                # Index comments
                for i, comment in enumerate(ticket.get("comments", [])):
                    comment_doc = Document(
                        content=comment["body"],
                        source_type="ticket_comment",
                        source_id=f"{source_system}:{key}:comment:{i}",
                        tenant_id=tenant_id,
                        metadata={
                            "ticket_key": key,
                            "author": comment.get("author"),
                            "created": comment.get("created"),
                        },
                    )
                    all_documents.append(comment_doc)
                    
            except Exception as e:
                errors.append(f"Error indexing ticket {ticket.get('key')}: {str(e)}")
        
        indexed = await self._embed_and_store(all_documents, kwargs.get("collection"))
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        return IndexingResult(
            documents_processed=len(tickets),
            chunks_created=len(all_documents),
            chunks_indexed=indexed,
            errors=errors,
            duration_ms=elapsed_ms,
        )


class IncidentIndexer(BaseIndexer):
    """
    Index incidents and postmortems.
    
    Indexes:
    - Incident timeline
    - Root cause analysis
    - Remediation steps
    - Related alerts/logs
    """
    
    async def index(
        self,
        source: Dict[str, Any],
        tenant_id: str,
        **kwargs,
    ) -> IndexingResult:
        """
        Index incidents.
        
        Expected source format:
        {
            "incidents": [
                {
                    "id": "INC-001",
                    "title": "...",
                    "description": "...",
                    "timeline": [...],
                    "root_cause": "...",
                    "remediation": "...",
                    "severity": "P1",
                }
            ]
        }
        """
        import time
        start_time = time.time()
        
        incidents = source.get("incidents", [])
        all_documents: List[Document] = []
        errors: List[str] = []
        
        for incident in incidents:
            try:
                inc_id = incident["id"]
                
                # Build comprehensive incident document
                content_parts = [
                    f"# {incident['title']}",
                    f"\n## Description\n{incident.get('description', '')}",
                ]
                
                if incident.get("root_cause"):
                    content_parts.append(f"\n## Root Cause\n{incident['root_cause']}")
                
                if incident.get("remediation"):
                    content_parts.append(f"\n## Remediation\n{incident['remediation']}")
                
                if incident.get("timeline"):
                    timeline_text = "\n".join(
                        f"- {event.get('time', 'N/A')}: {event.get('description', '')}"
                        for event in incident["timeline"]
                    )
                    content_parts.append(f"\n## Timeline\n{timeline_text}")
                
                content = "\n".join(content_parts)
                
                doc = Document(
                    content=content,
                    source_type="incident",
                    source_id=f"incident:{inc_id}",
                    source_url=incident.get("url"),
                    tenant_id=tenant_id,
                    metadata={
                        "incident_id": inc_id,
                        "severity": incident.get("severity"),
                        "status": incident.get("status"),
                        "services_affected": incident.get("services", []),
                        "duration_minutes": incident.get("duration_minutes"),
                    },
                )
                all_documents.append(doc)
                
            except Exception as e:
                errors.append(f"Error indexing incident {incident.get('id')}: {str(e)}")
        
        indexed = await self._embed_and_store(all_documents, kwargs.get("collection"))
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        return IndexingResult(
            documents_processed=len(incidents),
            chunks_created=len(all_documents),
            chunks_indexed=indexed,
            errors=errors,
            duration_ms=elapsed_ms,
        )
