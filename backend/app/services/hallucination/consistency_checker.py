"""Consistency checker for hallucination detection.

Verifies response consistency by generating multiple samples
and comparing them. Runs asynchronously in background to avoid
adding latency to the main response flow.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Callable
from uuid import uuid4

import structlog

logger = structlog.get_logger()


@dataclass
class ConsistencyResult:
    """Result of a consistency check."""

    task_id: str
    is_consistent: bool
    consistency_score: float  # 0-1, higher is more consistent
    samples_generated: int
    sample_similarities: list[float]
    avg_similarity: float
    min_similarity: float
    max_similarity: float
    duration_ms: int
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class PendingCheck:
    """A pending consistency check task."""

    task_id: str
    query: str
    original_response: str
    num_samples: int
    created_at: datetime
    callback: Callable[[ConsistencyResult], Any] | None = None
    result: ConsistencyResult | None = None
    completed: bool = False
    error: str | None = None


class ConsistencyChecker:
    """
    Consistency checker for LLM responses.

    Generates multiple response samples for the same query
    and compares them to detect potential hallucinations.
    Inconsistent responses across samples suggest unreliable content.

    Runs asynchronously in background to avoid blocking the main response.
    """

    # Hard cap to prevent unbounded memory growth
    MAX_STORED_RESULTS = 1000

    def __init__(
        self,
        llm_gateway: Any,  # Type hint avoided for circular import
        consistency_threshold: float = 0.7,
        max_concurrent_checks: int = 5,
        semantic_checker: Any | None = None,  # SemanticSimilarityChecker
    ):
        """
        Initialize the consistency checker.

        Args:
            llm_gateway: LLM gateway service for generating samples
            consistency_threshold: Minimum similarity for consistency (0-1)
            max_concurrent_checks: Maximum concurrent background checks
            semantic_checker: Optional SemanticSimilarityChecker for embedding-based
                comparison. Falls back to word overlap if not provided.
        """
        self.llm_gateway = llm_gateway
        self.consistency_threshold = consistency_threshold
        self.max_concurrent_checks = max_concurrent_checks
        self.semantic_checker = semantic_checker

        # Task tracking
        self._pending_checks: dict[str, PendingCheck] = {}
        self._completed_checks: dict[str, ConsistencyResult] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent_checks)

        # Keep results for 1 hour
        self._result_ttl_seconds = 3600

    async def schedule_consistency_check(
        self,
        request_id: str,
        query: str,
        response: str,
        num_samples: int = 3,
        callback: Callable[[ConsistencyResult], Any] | None = None,
        model: str | None = None,
    ) -> str:
        """
        Schedule an async background consistency check.

        Args:
            request_id: Original request ID for correlation
            query: The original query
            response: The original response to check
            num_samples: Number of additional samples to generate
            callback: Optional callback when check completes
            model: Optional model override for samples

        Returns:
            Task ID for retrieving results later
        """
        task_id = f"consistency_{request_id}_{uuid4().hex[:8]}"

        pending = PendingCheck(
            task_id=task_id,
            query=query,
            original_response=response,
            num_samples=num_samples,
            created_at=datetime.now(UTC),
            callback=callback,
        )

        self._pending_checks[task_id] = pending

        # Start background task
        asyncio.create_task(
            self._run_check(pending, model=model),
            name=f"consistency_check_{task_id}",
        )

        logger.info(
            "consistency_check_scheduled",
            task_id=task_id,
            request_id=request_id,
            num_samples=num_samples,
        )

        return task_id

    async def _run_check(
        self,
        pending: PendingCheck,
        model: str | None = None,
    ) -> None:
        """Run the consistency check in background."""
        start_time = datetime.now(UTC)

        async with self._semaphore:
            try:
                result = await self._perform_check(
                    pending.query,
                    pending.original_response,
                    pending.num_samples,
                    model=model,
                )

                result.task_id = pending.task_id
                result.duration_ms = int(
                    (datetime.now(UTC) - start_time).total_seconds() * 1000
                )

                pending.result = result
                pending.completed = True
                self._completed_checks[pending.task_id] = result

                logger.info(
                    "consistency_check_completed",
                    task_id=pending.task_id,
                    is_consistent=result.is_consistent,
                    consistency_score=result.consistency_score,
                    duration_ms=result.duration_ms,
                )

                # Execute callback if provided
                if pending.callback:
                    try:
                        await self._execute_callback(pending.callback, result)
                    except Exception as e:
                        logger.error(
                            "consistency_check_callback_error",
                            task_id=pending.task_id,
                            error=str(e),
                        )

            except Exception as e:
                pending.error = str(e)
                pending.completed = True

                logger.error(
                    "consistency_check_failed",
                    task_id=pending.task_id,
                    error=str(e),
                )

            finally:
                # Clean up old results periodically
                await self._cleanup_old_results()

    async def _perform_check(
        self,
        query: str,
        original_response: str,
        num_samples: int,
        model: str | None = None,
    ) -> ConsistencyResult:
        """
        Perform the actual consistency check.

        Generates multiple samples and compares them.
        """
        samples: list[str] = []

        # Generate additional samples with lower temperature for comparison
        for i in range(num_samples):
            try:
                # Use a slightly lower temperature for comparison samples
                sample = await self._generate_sample(
                    query,
                    temperature=0.3,  # Lower temperature for more deterministic output
                    model=model,
                )
                if sample:
                    samples.append(sample)
            except Exception as e:
                logger.warning(
                    "consistency_sample_generation_failed",
                    sample_index=i,
                    error=str(e),
                )

        if not samples:
            # Distinguish generation failure from actual inconsistency
            return ConsistencyResult(
                task_id="",
                is_consistent=False,
                consistency_score=0.0,
                samples_generated=0,
                sample_similarities=[],
                avg_similarity=0.0,
                min_similarity=0.0,
                max_similarity=0.0,
                duration_ms=0,
                details={
                    "error": "No samples generated",
                    "generation_failure": True,
                    "samples_requested": num_samples,
                },
            )

        # Calculate similarities — prefer embeddings, fall back to word overlap
        similarities = await self._calculate_similarities(original_response, samples)

        avg_similarity = sum(similarities) / len(similarities)
        min_similarity = min(similarities)
        max_similarity = max(similarities)

        is_consistent = avg_similarity >= self.consistency_threshold

        return ConsistencyResult(
            task_id="",
            is_consistent=is_consistent,
            consistency_score=round(avg_similarity, 4),
            samples_generated=len(samples),
            sample_similarities=[round(s, 4) for s in similarities],
            avg_similarity=round(avg_similarity, 4),
            min_similarity=round(min_similarity, 4),
            max_similarity=round(max_similarity, 4),
            duration_ms=0,
            details={
                "threshold": self.consistency_threshold,
                "samples_requested": num_samples,
                "similarity_method": "semantic" if self.semantic_checker else "word_overlap",
            },
        )

    async def _generate_sample(
        self,
        query: str,
        temperature: float = 0.3,
        model: str | None = None,
    ) -> str | None:
        """Generate a sample response for the query."""
        try:
            # Build request for the LLM gateway
            from app.services.llm_gateway.models import LLMRequest, Message

            request = LLMRequest(
                messages=[Message(role="user", content=query)],
                model=model,
                temperature=temperature,
                max_tokens=1000,  # Limit for efficiency
            )

            response = await self.llm_gateway.complete(request)
            return response.content if response else None

        except Exception as e:
            logger.warning("sample_generation_error", error=str(e))
            return None

    async def _calculate_similarities(
        self, original: str, samples: list[str]
    ) -> list[float]:
        """Calculate similarity between original and each sample.

        Uses semantic embeddings when a SemanticSimilarityChecker is available,
        otherwise falls back to word-overlap Jaccard similarity.
        """
        if self.semantic_checker:
            try:
                pairs = [(original, sample) for sample in samples]
                scores = await self.semantic_checker.batch_similarity(pairs)
                # Clamp to [0, 1]
                return [max(0.0, min(1.0, s)) for s in scores]
            except Exception as e:
                logger.warning(
                    "semantic_similarity_fallback",
                    error=str(e),
                    reason="Falling back to word overlap",
                )

        # Fallback: word overlap
        return [self._calculate_similarity(original, s) for s in samples]

    @staticmethod
    def _calculate_similarity(text1: str, text2: str) -> float:
        """
        Calculate text similarity using word overlap.

        This is a simple heuristic - for production, consider using
        embeddings via SemanticSimilarityChecker.
        """
        if not text1 or not text2:
            return 0.0

        # Tokenize (simple word-based)
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        # Remove common stop words for better comparison
        stop_words = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "shall",
            "can",
            "need",
            "dare",
            "ought",
            "used",
            "to",
            "of",
            "in",
            "for",
            "on",
            "with",
            "at",
            "by",
            "from",
            "as",
            "into",
            "through",
            "during",
            "before",
            "after",
            "above",
            "below",
            "between",
            "under",
            "again",
            "further",
            "then",
            "once",
            "and",
            "but",
            "or",
            "nor",
            "so",
            "yet",
            "both",
            "either",
            "neither",
            "not",
            "only",
            "own",
            "same",
            "than",
            "too",
            "very",
            "just",
            "i",
            "you",
            "he",
            "she",
            "it",
            "we",
            "they",
            "me",
            "him",
            "her",
            "us",
            "them",
            "my",
            "your",
            "his",
            "its",
            "our",
            "their",
            "this",
            "that",
            "these",
            "those",
        }

        words1 = words1 - stop_words
        words2 = words2 - stop_words

        if not words1 or not words2:
            return 0.0

        # Jaccard similarity
        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    async def _execute_callback(
        self,
        callback: Callable[[ConsistencyResult], Any],
        result: ConsistencyResult,
    ) -> None:
        """Execute the callback, handling both sync and async."""
        if asyncio.iscoroutinefunction(callback):
            await callback(result)
        else:
            callback(result)

    async def get_result(self, task_id: str) -> ConsistencyResult | None:
        """
        Get the result of a consistency check.

        Args:
            task_id: The task ID returned from schedule_consistency_check

        Returns:
            ConsistencyResult if completed, None if still pending or not found
        """
        # Check completed
        if task_id in self._completed_checks:
            return self._completed_checks[task_id]

        # Check pending
        if task_id in self._pending_checks:
            pending = self._pending_checks[task_id]
            if pending.completed and pending.result:
                return pending.result

        return None

    async def get_status(self, task_id: str) -> dict[str, Any]:
        """
        Get the status of a consistency check.

        Args:
            task_id: The task ID

        Returns:
            Status dictionary
        """
        if task_id in self._completed_checks:
            result = self._completed_checks[task_id]
            return {
                "status": "completed",
                "task_id": task_id,
                "is_consistent": result.is_consistent,
                "consistency_score": result.consistency_score,
            }

        if task_id in self._pending_checks:
            pending = self._pending_checks[task_id]
            if pending.error:
                return {
                    "status": "failed",
                    "task_id": task_id,
                    "error": pending.error,
                }
            if pending.completed:
                return {
                    "status": "completed",
                    "task_id": task_id,
                }
            return {
                "status": "pending",
                "task_id": task_id,
                "created_at": pending.created_at.isoformat(),
            }

        return {
            "status": "not_found",
            "task_id": task_id,
        }

    async def _cleanup_old_results(self) -> None:
        """Remove old results to prevent memory leaks.

        Two eviction strategies:
        1. TTL-based: remove anything older than _result_ttl_seconds.
        2. Size-based: if still over MAX_STORED_RESULTS, evict oldest first (LRU).
        """
        now = datetime.now(UTC)
        cutoff = now.timestamp() - self._result_ttl_seconds

        # ---- TTL eviction ----
        to_remove = []
        for task_id, pending in self._pending_checks.items():
            if pending.created_at.timestamp() < cutoff:
                to_remove.append(task_id)

        for task_id in to_remove:
            self._pending_checks.pop(task_id, None)
            self._completed_checks.pop(task_id, None)

        # ---- Size eviction (LRU) ----
        if len(self._completed_checks) > self.MAX_STORED_RESULTS:
            # Sort by creation time, evict oldest
            sorted_tasks = sorted(
                (
                    (tid, self._pending_checks[tid].created_at)
                    for tid in self._completed_checks
                    if tid in self._pending_checks
                ),
                key=lambda x: x[1],
            )
            excess = len(self._completed_checks) - self.MAX_STORED_RESULTS
            for tid, _ in sorted_tasks[:excess]:
                self._pending_checks.pop(tid, None)
                self._completed_checks.pop(tid, None)

            logger.info(
                "consistency_checker_size_eviction",
                evicted=excess,
                remaining=len(self._completed_checks),
            )
