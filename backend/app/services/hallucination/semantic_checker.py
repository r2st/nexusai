"""Semantic similarity checker for hallucination detection.

Uses embeddings to compute semantic similarity between texts
and check if responses are grounded in provided context.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import structlog

from app.services.rag.embeddings import EmbeddingsService, EmbeddingResult

logger = structlog.get_logger()


@dataclass
class GroundingResult:
    """Result of a grounding check."""

    grounding_score: float  # 0-1, higher is better grounded
    ungrounded_sentences: list[str]  # Sentences not grounded in context
    context_coverage: float  # How much of context was used
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class SimilarityResult:
    """Result of a similarity computation."""

    similarity: float  # Cosine similarity -1 to 1
    text1_embedding: list[float] | None = None
    text2_embedding: list[float] | None = None


class SemanticSimilarityChecker:
    """
    Semantic similarity checker using embeddings.

    Provides:
    - Cosine similarity between texts
    - Grounding checks for RAG responses
    - Sentence-level analysis
    """

    def __init__(
        self,
        embedding_service: EmbeddingsService,
        grounding_threshold: float = 0.6,
        sentence_threshold: float = 0.5,
    ):
        """
        Initialize the semantic similarity checker.

        Args:
            embedding_service: Service for generating embeddings
            grounding_threshold: Minimum similarity for grounded response (0-1)
            sentence_threshold: Minimum similarity for grounded sentence (0-1)
        """
        self.embedding_service = embedding_service
        self.grounding_threshold = grounding_threshold
        self.sentence_threshold = sentence_threshold

    @staticmethod
    def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        a = np.array(vec1)
        b = np.array(vec2)

        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(dot_product / (norm_a * norm_b))

    async def compute_similarity(
        self,
        text1: str,
        text2: str,
        return_embeddings: bool = False,
    ) -> SimilarityResult:
        """
        Compute semantic similarity between two texts.

        Args:
            text1: First text
            text2: Second text
            return_embeddings: Whether to include embeddings in result

        Returns:
            SimilarityResult with cosine similarity score
        """
        try:
            # Get embeddings for both texts
            results = await self.embedding_service.embed_batch([text1, text2])

            if len(results) < 2:
                logger.warning("semantic_checker_embedding_failed", texts_requested=2)
                return SimilarityResult(similarity=0.0)

            vec1 = results[0].embedding
            vec2 = results[1].embedding

            similarity = self.cosine_similarity(vec1, vec2)

            return SimilarityResult(
                similarity=similarity,
                text1_embedding=vec1 if return_embeddings else None,
                text2_embedding=vec2 if return_embeddings else None,
            )

        except Exception as e:
            logger.error("semantic_similarity_error", error=str(e))
            return SimilarityResult(similarity=0.0)

    async def check_grounding(
        self,
        response: str,
        context: list[str],
        check_sentences: bool = True,
    ) -> GroundingResult:
        """
        Check how well a response is grounded in provided context.

        Args:
            response: The LLM response to check
            context: List of context documents/passages
            check_sentences: Whether to check individual sentences

        Returns:
            GroundingResult with grounding score and details
        """
        if not context:
            return GroundingResult(
                grounding_score=0.0,
                ungrounded_sentences=[response] if response else [],
                context_coverage=0.0,
                details={"error": "No context provided"},
            )

        try:
            # Combine context into single text for overall comparison
            combined_context = " ".join(context)

            # Get overall grounding score
            overall_result = await self.compute_similarity(response, combined_context)
            overall_score = max(0.0, overall_result.similarity)  # Clamp to 0-1

            ungrounded_sentences: list[str] = []
            sentence_scores: list[dict[str, Any]] = []

            if check_sentences:
                # Split response into sentences
                sentences = self._split_into_sentences(response)

                if sentences:
                    # Get embeddings for all sentences and context docs
                    all_texts = sentences + context
                    embeddings = await self.embedding_service.embed_batch(all_texts)

                    sentence_embeddings = embeddings[: len(sentences)]
                    context_embeddings = embeddings[len(sentences) :]

                    # Check each sentence against context
                    for i, (sentence, sent_emb) in enumerate(
                        zip(sentences, sentence_embeddings)
                    ):
                        if not sentence.strip():
                            continue

                        # Find max similarity to any context document
                        max_similarity = 0.0
                        for ctx_emb in context_embeddings:
                            sim = self.cosine_similarity(
                                sent_emb.embedding, ctx_emb.embedding
                            )
                            max_similarity = max(max_similarity, sim)

                        sentence_scores.append(
                            {
                                "sentence": sentence,
                                "similarity": max_similarity,
                                "grounded": max_similarity >= self.sentence_threshold,
                            }
                        )

                        if max_similarity < self.sentence_threshold:
                            ungrounded_sentences.append(sentence)

            # Calculate context coverage
            # This measures how much of the context is actually used
            context_coverage = await self._calculate_context_coverage(
                response, context
            )

            # Adjust grounding score based on sentence analysis
            if sentence_scores:
                grounded_count = sum(
                    1 for s in sentence_scores if s.get("grounded", False)
                )
                sentence_grounding_rate = grounded_count / len(sentence_scores)
                # Weighted average of overall and sentence-level grounding
                final_score = (overall_score * 0.4) + (sentence_grounding_rate * 0.6)
            else:
                final_score = overall_score

            return GroundingResult(
                grounding_score=round(final_score, 4),
                ungrounded_sentences=ungrounded_sentences,
                context_coverage=round(context_coverage, 4),
                details={
                    "overall_similarity": overall_score,
                    "sentence_scores": sentence_scores,
                    "sentences_analyzed": len(sentence_scores),
                    "grounded_sentences": len(sentence_scores)
                    - len(ungrounded_sentences),
                },
            )

        except Exception as e:
            logger.error("grounding_check_error", error=str(e))
            return GroundingResult(
                grounding_score=0.0,
                ungrounded_sentences=[],
                context_coverage=0.0,
                details={"error": str(e)},
            )

    async def _calculate_context_coverage(
        self,
        response: str,
        context: list[str],
    ) -> float:
        """
        Calculate how much of the context is covered by the response.

        Returns a score 0-1 indicating context utilization.
        """
        if not context:
            return 0.0

        try:
            # Get response embedding
            response_result = await self.embedding_service.embed_single(response)
            response_embedding = response_result.embedding

            # Get context embeddings
            context_results = await self.embedding_service.embed_batch(context)

            # Calculate similarity to each context document
            total_similarity = 0.0
            for ctx_result in context_results:
                sim = self.cosine_similarity(response_embedding, ctx_result.embedding)
                total_similarity += max(0, sim)

            # Average similarity across all context documents
            avg_coverage = total_similarity / len(context_results)
            return min(1.0, avg_coverage)

        except Exception as e:
            logger.error("context_coverage_error", error=str(e))
            return 0.0

    @staticmethod
    def _split_into_sentences(text: str) -> list[str]:
        """Split text into sentences.

        Handles common edge cases:
        - Abbreviations (Dr., Mr., Mrs., e.g., i.e., etc., vs., fig., no.)
        - Decimal numbers (3.14, $99.99)
        - URLs (https://example.com)
        - Ellipses (...)
        - Code-like content (func(), file.py)
        """
        import re

        if not text or not text.strip():
            return []

        # Protect known abbreviations from being split
        _ABBREVS = (
            r"(?:Mr|Mrs|Ms|Dr|Prof|Sr|Jr|St|vs|fig|Fig|no|No|vol|Vol"
            r"|etc|approx|dept|est|govt|inc|corp|ltd|assn"
            r"|e\.g|i\.e|a\.m|p\.m|U\.S|U\.K)"
        )

        working = text

        # Protect abbreviations: replace "Dr." with "Dr\x00"
        working = re.sub(
            rf"({_ABBREVS})\.\s",
            lambda m: m.group(1) + "\x00 ",
            working,
        )

        # Protect decimal numbers: "3.14" → "3<PH>14"
        working = re.sub(
            r"(\d)\.(\d)",
            lambda m: m.group(1) + "\x00" + m.group(2),
            working,
        )

        # Protect URLs
        working = re.sub(
            r"(https?://\S+)",
            lambda m: m.group(0).replace(".", "\x00"),
            working,
        )

        # Protect ellipses
        working = working.replace("...", "\x01\x01\x01")

        # Protect file extensions (.py, .js, .ts, .json, etc.)
        working = re.sub(
            r"(\w)\.(py|js|ts|tsx|jsx|json|yaml|yml|md|html|css|go|rs|java|rb|sh|sql|csv|txt|pdf|png|jpg)\b",
            lambda m: m.group(1) + "\x00" + m.group(2),
            working,
        )

        # Now split on sentence-ending punctuation followed by space + uppercase
        # or end-of-string
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z\"\'\(\[]|$)", working)

        # Restore protected characters
        result = []
        for s in sentences:
            s = s.replace("\x00", ".").replace("\x01\x01\x01", "...")
            s = s.strip()
            if s:
                result.append(s)

        return result

    async def batch_similarity(
        self,
        pairs: list[tuple[str, str]],
    ) -> list[float]:
        """
        Compute similarity for multiple pairs efficiently.

        Args:
            pairs: List of (text1, text2) tuples

        Returns:
            List of similarity scores
        """
        if not pairs:
            return []

        try:
            # Flatten all texts for batch embedding
            all_texts = []
            for t1, t2 in pairs:
                all_texts.extend([t1, t2])

            # Get all embeddings in one batch
            embeddings = await self.embedding_service.embed_batch(all_texts)

            # Compute similarities
            similarities = []
            for i in range(0, len(embeddings), 2):
                if i + 1 < len(embeddings):
                    sim = self.cosine_similarity(
                        embeddings[i].embedding, embeddings[i + 1].embedding
                    )
                    similarities.append(sim)
                else:
                    similarities.append(0.0)

            return similarities

        except Exception as e:
            logger.error("batch_similarity_error", error=str(e))
            return [0.0] * len(pairs)

    async def find_most_similar(
        self,
        query: str,
        candidates: list[str],
        top_k: int = 5,
    ) -> list[tuple[str, float]]:
        """
        Find the most similar texts to a query.

        Args:
            query: Query text
            candidates: List of candidate texts
            top_k: Number of results to return

        Returns:
            List of (text, similarity) tuples sorted by similarity
        """
        if not candidates:
            return []

        try:
            # Get all embeddings
            all_texts = [query] + candidates
            embeddings = await self.embedding_service.embed_batch(all_texts)

            query_embedding = embeddings[0].embedding
            candidate_embeddings = embeddings[1:]

            # Calculate similarities
            similarities = []
            for i, cand_emb in enumerate(candidate_embeddings):
                sim = self.cosine_similarity(query_embedding, cand_emb.embedding)
                similarities.append((candidates[i], sim))

            # Sort by similarity and return top_k
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:top_k]

        except Exception as e:
            logger.error("find_most_similar_error", error=str(e))
            return []
