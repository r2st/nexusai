"""Code Similarity Service implementation.

Provides multiple similarity matching strategies:
1. Semantic similarity using embeddings
2. Structural similarity using AST comparison
3. Token-based similarity using n-grams
4. Hybrid similarity combining all methods
"""

import hashlib
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

import httpx
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings


class SimilarityMethod(str, Enum):
    """Similarity calculation methods."""

    SEMANTIC = "semantic"  # Embedding-based
    STRUCTURAL = "structural"  # AST-based
    TOKEN = "token"  # N-gram based
    HYBRID = "hybrid"  # Combined


@dataclass
class SimilarityResult:
    """Result of a similarity comparison."""

    source_id: str
    target_id: str
    score: float  # 0.0 to 1.0
    method: SimilarityMethod
    details: dict[str, Any]


@dataclass
class CodeSnippet:
    """A code snippet for similarity analysis."""

    id: str
    content: str
    language: str
    file_path: str | None = None
    metadata: dict[str, Any] | None = None


class SimilarityService:
    """Service for code similarity matching."""

    def __init__(self):
        self.external_service_url = settings.SIMILARITY_SERVICE_URL
        self.enabled = settings.SIMILARITY_ENABLED

    async def calculate_similarity(
        self,
        source: CodeSnippet,
        target: CodeSnippet,
        method: SimilarityMethod = SimilarityMethod.HYBRID,
    ) -> SimilarityResult:
        """Calculate similarity between two code snippets.

        Args:
            source: Source code snippet
            target: Target code snippet
            method: Similarity calculation method

        Returns:
            SimilarityResult with score and details
        """
        if method == SimilarityMethod.SEMANTIC:
            return await self._semantic_similarity(source, target)
        elif method == SimilarityMethod.STRUCTURAL:
            return await self._structural_similarity(source, target)
        elif method == SimilarityMethod.TOKEN:
            return await self._token_similarity(source, target)
        else:
            return await self._hybrid_similarity(source, target)

    async def find_similar(
        self,
        session: AsyncSession,
        snippet: CodeSnippet,
        tenant_id: str,
        project_id: str | None = None,
        min_score: float = 0.7,
        limit: int = 10,
    ) -> list[SimilarityResult]:
        """Find similar code snippets in the database.

        Uses vector similarity search with pgvector.

        Args:
            session: Database session
            snippet: Code snippet to match
            tenant_id: Tenant ID for isolation
            project_id: Optional project ID filter
            min_score: Minimum similarity score (0.0 to 1.0)
            limit: Maximum number of results

        Returns:
            List of similar snippets with scores
        """
        # Get embedding for the snippet
        embedding = await self._get_embedding(snippet.content)

        if not embedding:
            return []

        # Query using pgvector similarity
        # Uses cosine similarity: 1 - (embedding <=> stored_embedding)
        query = text("""
            SELECT
                id,
                content,
                language,
                file_path,
                1 - (embedding <=> :embedding::vector) as score
            FROM code_snippets
            WHERE tenant_id = :tenant_id
            AND 1 - (embedding <=> :embedding::vector) >= :min_score
            {}
            ORDER BY embedding <=> :embedding::vector
            LIMIT :limit
        """.format("AND project_id = :project_id" if project_id else ""))

        params = {
            "tenant_id": tenant_id,
            "embedding": str(embedding),
            "min_score": min_score,
            "limit": limit,
        }
        if project_id:
            params["project_id"] = project_id

        result = await session.execute(query, params)

        results = []
        for row in result:
            results.append(SimilarityResult(
                source_id=snippet.id,
                target_id=row.id,
                score=float(row.score),
                method=SimilarityMethod.SEMANTIC,
                details={
                    "language": row.language,
                    "file_path": row.file_path,
                },
            ))

        return results

    async def index_snippet(
        self,
        session: AsyncSession,
        snippet: CodeSnippet,
        tenant_id: str,
        project_id: str | None = None,
    ) -> bool:
        """Index a code snippet for similarity search.

        Args:
            session: Database session
            snippet: Code snippet to index
            tenant_id: Tenant ID
            project_id: Optional project ID

        Returns:
            True if indexed successfully
        """
        # Get embedding
        embedding = await self._get_embedding(snippet.content)

        if not embedding:
            return False

        # Calculate content hash for deduplication
        content_hash = hashlib.sha256(snippet.content.encode()).hexdigest()

        # Insert or update
        await session.execute(text("""
            INSERT INTO code_snippets (
                id, tenant_id, project_id, content, content_hash,
                language, file_path, embedding, metadata
            )
            VALUES (
                :id, :tenant_id, :project_id, :content, :content_hash,
                :language, :file_path, :embedding::vector, :metadata
            )
            ON CONFLICT (content_hash, tenant_id)
            DO UPDATE SET
                content = EXCLUDED.content,
                language = EXCLUDED.language,
                file_path = EXCLUDED.file_path,
                embedding = EXCLUDED.embedding,
                updated_at = NOW()
        """), {
            "id": snippet.id,
            "tenant_id": tenant_id,
            "project_id": project_id,
            "content": snippet.content,
            "content_hash": content_hash,
            "language": snippet.language,
            "file_path": snippet.file_path,
            "embedding": str(embedding),
            "metadata": snippet.metadata or {},
        })

        await session.commit()
        return True

    async def _semantic_similarity(
        self,
        source: CodeSnippet,
        target: CodeSnippet,
    ) -> SimilarityResult:
        """Calculate semantic similarity using embeddings."""
        # Get embeddings for both snippets
        source_embedding = await self._get_embedding(source.content)
        target_embedding = await self._get_embedding(target.content)

        if not source_embedding or not target_embedding:
            return SimilarityResult(
                source_id=source.id,
                target_id=target.id,
                score=0.0,
                method=SimilarityMethod.SEMANTIC,
                details={"error": "Could not generate embeddings"},
            )

        # Calculate cosine similarity
        score = self._cosine_similarity(source_embedding, target_embedding)

        return SimilarityResult(
            source_id=source.id,
            target_id=target.id,
            score=score,
            method=SimilarityMethod.SEMANTIC,
            details={
                "embedding_dim": len(source_embedding),
            },
        )

    async def _structural_similarity(
        self,
        source: CodeSnippet,
        target: CodeSnippet,
    ) -> SimilarityResult:
        """Calculate structural similarity using AST comparison."""
        # Normalize code structure
        source_structure = self._extract_structure(source.content, source.language)
        target_structure = self._extract_structure(target.content, target.language)

        # Calculate structure similarity
        if not source_structure or not target_structure:
            return SimilarityResult(
                source_id=source.id,
                target_id=target.id,
                score=0.0,
                method=SimilarityMethod.STRUCTURAL,
                details={"error": "Could not parse structure"},
            )

        # Use sequence matching on structure tokens
        score = self._sequence_similarity(source_structure, target_structure)

        return SimilarityResult(
            source_id=source.id,
            target_id=target.id,
            score=score,
            method=SimilarityMethod.STRUCTURAL,
            details={
                "source_nodes": len(source_structure),
                "target_nodes": len(target_structure),
            },
        )

    async def _token_similarity(
        self,
        source: CodeSnippet,
        target: CodeSnippet,
    ) -> SimilarityResult:
        """Calculate token-based similarity using n-grams."""
        # Tokenize code
        source_tokens = self._tokenize(source.content)
        target_tokens = self._tokenize(target.content)

        # Calculate n-gram similarity
        n = 3  # Trigrams
        source_ngrams = set(self._ngrams(source_tokens, n))
        target_ngrams = set(self._ngrams(target_tokens, n))

        # Jaccard similarity
        intersection = len(source_ngrams & target_ngrams)
        union = len(source_ngrams | target_ngrams)

        score = intersection / union if union > 0 else 0.0

        return SimilarityResult(
            source_id=source.id,
            target_id=target.id,
            score=score,
            method=SimilarityMethod.TOKEN,
            details={
                "source_tokens": len(source_tokens),
                "target_tokens": len(target_tokens),
                "ngram_size": n,
                "common_ngrams": intersection,
            },
        )

    async def _hybrid_similarity(
        self,
        source: CodeSnippet,
        target: CodeSnippet,
    ) -> SimilarityResult:
        """Calculate hybrid similarity combining all methods."""
        # Calculate all similarities
        semantic = await self._semantic_similarity(source, target)
        structural = await self._structural_similarity(source, target)
        token = await self._token_similarity(source, target)

        # Weighted average
        weights = {
            "semantic": 0.5,
            "structural": 0.3,
            "token": 0.2,
        }

        score = (
            semantic.score * weights["semantic"] +
            structural.score * weights["structural"] +
            token.score * weights["token"]
        )

        return SimilarityResult(
            source_id=source.id,
            target_id=target.id,
            score=score,
            method=SimilarityMethod.HYBRID,
            details={
                "semantic_score": semantic.score,
                "structural_score": structural.score,
                "token_score": token.score,
                "weights": weights,
            },
        )

    async def _get_embedding(self, content: str) -> list[float] | None:
        """Get embedding for code content."""
        # Try external service first
        if self.external_service_url:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{self.external_service_url}/embed",
                        json={"text": content},
                    )
                    if response.status_code == 200:
                        return response.json().get("embedding")
            except Exception:
                pass

        # Fallback to OpenAI embeddings
        if settings.OPENAI_API_KEY:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        "https://api.openai.com/v1/embeddings",
                        headers={
                            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": settings.EMBEDDING_MODEL,
                            "input": content[:8000],  # Truncate to limit
                        },
                    )
                    if response.status_code == 200:
                        data = response.json()
                        return data["data"][0]["embedding"]
            except Exception:
                pass

        return None

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        import math

        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    def _extract_structure(self, content: str, language: str) -> list[str]:
        """Extract structural tokens from code.

        This is a simplified version that extracts key patterns.
        A full implementation would use language-specific AST parsers.
        """
        # Remove strings and comments
        content = re.sub(r'(["\']).*?\1', '""', content)
        content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        content = re.sub(r'#.*$', '', content, flags=re.MULTILINE)

        # Extract structural patterns
        patterns = {
            "function": r'\b(?:def|function|func|fn)\s+\w+',
            "class": r'\b(?:class|struct|interface)\s+\w+',
            "loop": r'\b(?:for|while|loop)\b',
            "condition": r'\b(?:if|else|elif|switch|case)\b',
            "return": r'\breturn\b',
            "import": r'\b(?:import|from|require|use)\b',
            "assignment": r'\w+\s*[=:]=',
            "call": r'\w+\s*\(',
        }

        structure = []
        for pattern_type, pattern in patterns.items():
            matches = re.findall(pattern, content)
            structure.extend([pattern_type] * len(matches))

        return structure

    def _tokenize(self, content: str) -> list[str]:
        """Tokenize code into words and symbols."""
        # Remove strings and comments
        content = re.sub(r'(["\']).*?\1', '', content)
        content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

        # Split on word boundaries and symbols
        tokens = re.findall(r'\w+|[{}()\[\];,.<>+\-*/=!&|]', content)

        return [t.lower() for t in tokens]

    def _ngrams(self, tokens: list[str], n: int) -> list[tuple]:
        """Generate n-grams from tokens."""
        if len(tokens) < n:
            return [tuple(tokens)]
        return [tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]

    def _sequence_similarity(self, a: list[str], b: list[str]) -> float:
        """Calculate sequence similarity using LCS."""
        if not a or not b:
            return 0.0

        # Longest common subsequence
        m, n = len(a), len(b)
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if a[i - 1] == b[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

        lcs_length = dp[m][n]
        return (2.0 * lcs_length) / (m + n)


# Singleton instance
similarity_service = SimilarityService()
