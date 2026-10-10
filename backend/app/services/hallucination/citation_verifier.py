"""Citation verifier for RAG responses.

Verifies that citations in responses actually support the claims being made.
"""

import re
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class Citation:
    """A citation found in a response."""

    text: str  # The cited text/claim
    source_reference: str  # How the source was referenced (e.g., "[1]", "Source A")
    source_index: int | None = None  # Index into source documents if identified
    verified: bool = False
    verification_score: float = 0.0
    matched_source_text: str | None = None


@dataclass
class CitationResult:
    """Result of citation verification."""

    total_citations: int
    verified_citations: int
    unverified_citations: int
    verification_rate: float  # 0-1
    citations: list[Citation]
    orphan_claims: list[str]  # Claims made without citations
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class Document:
    """A source document for citation verification."""

    content: str
    title: str | None = None
    source_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class CitationVerifier:
    """
    Verifier for citations in RAG responses.

    Checks if cited sources actually support the claims being made.
    Can detect:
    - Unsupported citations
    - Misattributed information
    - Claims without citations (potential hallucinations)
    """

    # Common citation patterns (ordered by specificity)
    CITATION_PATTERNS = [
        r"\[(\d+)\s*[-–]\s*(\d+)\]",  # [1-3], [1–3] (ranges)
        r"\[(\d+(?:\s*,\s*\d+)+)\]",  # [1,2,3] or [1, 2, 3] (comma-separated)
        r"\[(\d+)\]",  # [1], [2], etc.
        r"\[Source (\w+)\]",  # [Source A], [Source B]
        r"\((\d+)\)",  # (1), (2), etc.
        r"according to (?:source |document )?(\d+|[A-Z])",  # "according to source 1"
        r"(?:from|per|via) (?:source |document )?(\d+|[A-Z])",  # "from source 1"
    ]

    # Patterns that are range or comma-separated (indices into CITATION_PATTERNS)
    _RANGE_PATTERN_IDX = 0
    _COMMA_PATTERN_IDX = 1

    def __init__(
        self,
        similarity_threshold: float = 0.5,
        semantic_checker: Any | None = None,  # SemanticSimilarityChecker
    ):
        """
        Initialize the citation verifier.

        Args:
            similarity_threshold: Minimum similarity for verified citation
            semantic_checker: Optional semantic similarity checker for advanced verification
        """
        self.similarity_threshold = similarity_threshold
        self.semantic_checker = semantic_checker

    async def verify_citations(
        self,
        response: str,
        sources: list[Document],
    ) -> CitationResult:
        """
        Verify citations in a response against source documents.

        Args:
            response: The LLM response containing citations
            sources: List of source documents

        Returns:
            CitationResult with verification details
        """
        if not response or not sources:
            return CitationResult(
                total_citations=0,
                verified_citations=0,
                unverified_citations=0,
                verification_rate=0.0,
                citations=[],
                orphan_claims=[],
                details={"error": "Empty response or no sources"},
            )

        # Extract citations from response
        citations = self._extract_citations(response)

        # Extract claims that might need citations
        orphan_claims = self._find_uncited_claims(response, citations)

        # Verify each citation against sources
        verified_count = 0
        for citation in citations:
            verified, score, matched_text = await self._verify_citation(
                citation, sources
            )
            citation.verified = verified
            citation.verification_score = score
            citation.matched_source_text = matched_text

            if verified:
                verified_count += 1

        verification_rate = verified_count / len(citations) if citations else 0.0

        return CitationResult(
            total_citations=len(citations),
            verified_citations=verified_count,
            unverified_citations=len(citations) - verified_count,
            verification_rate=round(verification_rate, 4),
            citations=citations,
            orphan_claims=orphan_claims,
            details={
                "sources_count": len(sources),
                "similarity_threshold": self.similarity_threshold,
            },
        )

    def _extract_citations(self, text: str) -> list[Citation]:
        """Extract citations from text.

        Handles:
        - Simple numeric: [1], [2]
        - Ranges: [1-3] → expanded to [1], [2], [3]
        - Comma-separated: [1,2,3] → expanded to individual citations
        - Source labels: [Source A]
        - Parenthetical: (1), (2)
        - Natural language: "according to source 1"
        """
        citations: list[Citation] = []
        seen_references: set[str] = set()

        sentences = self._split_sentences(text)

        for sentence in sentences:
            for pat_idx, pattern in enumerate(self.CITATION_PATTERNS):
                matches = re.finditer(pattern, sentence, re.IGNORECASE)
                for match in matches:
                    reference = match.group(0)

                    # Expand ranges [1-3] → individual citations
                    if pat_idx == self._RANGE_PATTERN_IDX and match.lastindex and match.lastindex >= 2:
                        try:
                            start = int(match.group(1))
                            end = int(match.group(2))
                            for idx in range(start, end + 1):
                                ref = f"[{idx}]"
                                key = f"{sentence}:{ref}"
                                if key not in seen_references:
                                    seen_references.add(key)
                                    citations.append(
                                        Citation(
                                            text=sentence,
                                            source_reference=ref,
                                            source_index=idx - 1,
                                        )
                                    )
                        except (ValueError, TypeError):
                            pass
                        continue

                    # Expand comma-separated [1,2,3] → individual citations
                    if pat_idx == self._COMMA_PATTERN_IDX:
                        source_ref = match.group(1)
                        try:
                            indices = [int(x.strip()) for x in source_ref.split(",")]
                            for idx in indices:
                                ref = f"[{idx}]"
                                key = f"{sentence}:{ref}"
                                if key not in seen_references:
                                    seen_references.add(key)
                                    citations.append(
                                        Citation(
                                            text=sentence,
                                            source_reference=ref,
                                            source_index=idx - 1,
                                        )
                                    )
                        except (ValueError, TypeError):
                            pass
                        continue

                    # Standard single citation
                    source_ref = match.group(1) if match.groups() else reference
                    citation_key = f"{sentence}:{reference}"
                    if citation_key in seen_references:
                        continue
                    seen_references.add(citation_key)

                    try:
                        source_index = int(source_ref) - 1
                    except (ValueError, TypeError):
                        source_index = None

                    citations.append(
                        Citation(
                            text=sentence,
                            source_reference=reference,
                            source_index=source_index,
                        )
                    )

        return citations

    def _find_uncited_claims(
        self,
        text: str,
        citations: list[Citation],
    ) -> list[str]:
        """Find claims that might need citations but don't have them.

        Uses two tiers of indicators:
        - Strong: phrases that almost always introduce factual claims
        - Weak: patterns that may or may not be claims depending on context;
                 require a minimum sentence length to avoid false positives.
        """
        orphan_claims: list[str] = []

        # Strong indicators — nearly always a factual claim
        strong_indicators = [
            r"\bresearch\s+(?:shows?|indicates?|suggests?|demonstrates?|confirms?)\b",
            r"\bstudies?\s+(?:shows?|indicates?|suggests?|found|reveals?)\b",
            r"\bexperts?\s+(?:says?|believes?|recommends?|warns?|agrees?)\b",
            r"\bdata\s+(?:shows?|suggests?|indicates?|reveals?|confirms?)\b",
            r"\bstatistics?\s+(?:shows?|indicates?|reveals?)\b",
            r"\bsurveys?\s+(?:shows?|found|indicates?|reveals?)\b",
            r"\breports?\s+(?:shows?|found|indicates?|confirms?)\b",
            r"\bit\s+is\s+(?:known|established|documented|proven)\s+that\b",
            r"\bhas\s+been\s+(?:shown|proven|demonstrated|established)\b",
        ]

        # Weak indicators — need more context (min sentence length) to flag
        weak_indicators = [
            (r"\d+(?:\.\d+)?%", 30),  # Percentages, but only in substantial sentences
            (r"\b(?:in|since|from)\s+\d{4}\b", 40),  # Years in longer sentences
            (r"\bapproximately\s+\d+", 20),  # "approximately N"
            (r"\b(?:more|less|over|under|about|nearly|almost)\s+\d+\s+(?:million|billion|thousand|hundred)\b", 20),
            (r"\bincreased?\s+(?:by|to)\s+\d+", 25),  # "increased by N"
            (r"\bdecreased?\s+(?:by|to)\s+\d+", 25),  # "decreased by N"
            (r"\b\d+(?:\.\d+)?x\s+(?:faster|slower|more|less|better|worse)\b", 20),  # "3x faster"
        ]

        cited_sentences = {c.text for c in citations}
        sentences = self._split_sentences(text)

        for sentence in sentences:
            if sentence in cited_sentences:
                continue

            flagged = False

            # Check strong indicators (always flag)
            for pattern in strong_indicators:
                if re.search(pattern, sentence, re.IGNORECASE):
                    orphan_claims.append(sentence)
                    flagged = True
                    break

            if flagged:
                continue

            # Check weak indicators (only flag if sentence is long enough)
            for pattern, min_len in weak_indicators:
                if len(sentence) >= min_len and re.search(
                    pattern, sentence, re.IGNORECASE
                ):
                    orphan_claims.append(sentence)
                    break

        return orphan_claims

    async def _verify_citation(
        self,
        citation: Citation,
        sources: list[Document],
    ) -> tuple[bool, float, str | None]:
        """
        Verify a citation against source documents.

        Returns:
            Tuple of (is_verified, score, matched_source_text)
        """
        best_score = 0.0
        best_match: str | None = None

        # If source index is specified, prioritize that source
        if citation.source_index is not None and 0 <= citation.source_index < len(
            sources
        ):
            source = sources[citation.source_index]
            score = await self._compute_support_score(citation.text, source.content)
            if score >= self.similarity_threshold:
                return True, score, self._find_matching_passage(
                    citation.text, source.content
                )
            best_score = score

        # Check all sources
        for source in sources:
            score = await self._compute_support_score(citation.text, source.content)
            if score > best_score:
                best_score = score
                best_match = self._find_matching_passage(citation.text, source.content)

        return best_score >= self.similarity_threshold, best_score, best_match

    async def _compute_support_score(
        self,
        claim: str,
        source_text: str,
    ) -> float:
        """Compute how well a source supports a claim."""
        # Use semantic similarity if available
        if self.semantic_checker:
            try:
                result = await self.semantic_checker.compute_similarity(
                    claim, source_text
                )
                return max(0.0, result.similarity)
            except Exception as e:
                logger.warning("semantic_verification_failed", error=str(e))

        # Fallback to word overlap
        return self._word_overlap_score(claim, source_text)

    @staticmethod
    def _word_overlap_score(text1: str, text2: str) -> float:
        """Calculate word overlap score."""
        if not text1 or not text2:
            return 0.0

        # Simple stop words to filter
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "have", "has", "had", "do", "does", "did", "will", "would",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "and", "but", "or", "not", "this", "that", "it", "i", "you",
        }

        words1 = set(text1.lower().split()) - stop_words
        words2 = set(text2.lower().split()) - stop_words

        if not words1 or not words2:
            return 0.0

        # Use Jaccard similarity with a boost for exact phrase matches
        intersection = len(words1 & words2)
        union = len(words1 | words2)

        jaccard = intersection / union if union > 0 else 0.0

        # Boost if significant word overlap (suggests direct support)
        if intersection >= 3:
            jaccard = min(1.0, jaccard * 1.2)

        return jaccard

    @staticmethod
    def _find_matching_passage(
        claim: str,
        source_text: str,
        context_chars: int = 200,
    ) -> str | None:
        """Find the passage in source that best matches the claim."""
        if not claim or not source_text:
            return None

        # Extract key words from claim
        claim_words = set(claim.lower().split())
        stop_words = {"the", "a", "an", "is", "are", "to", "of", "in", "for", "and"}
        key_words = claim_words - stop_words

        if not key_words:
            return None

        # Find sentences in source with most key word matches
        sentences = re.split(r"[.!?]+", source_text)
        best_sentence = None
        best_match_count = 0

        for sentence in sentences:
            sentence_words = set(sentence.lower().split())
            match_count = len(key_words & sentence_words)
            if match_count > best_match_count:
                best_match_count = match_count
                best_sentence = sentence.strip()

        if best_sentence and best_match_count >= 2:
            # Return with some context
            if len(best_sentence) > context_chars:
                return best_sentence[:context_chars] + "..."
            return best_sentence

        return None

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        """Split text into sentences."""
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in sentences if s.strip()]
