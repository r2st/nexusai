"""Hallucination detection service.

Orchestrates semantic similarity checking, consistency checking, and citation
verification to provide comprehensive hallucination detection.
"""

import asyncio
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import structlog

from app.models.hallucination_log import HallucinationLog, HallucinationMetric, CheckType
from app.services.hallucination.semantic_checker import (
    SemanticSimilarityChecker,
    GroundingResult,
)
from app.services.hallucination.consistency_checker import (
    ConsistencyChecker,
    ConsistencyResult,
)
from app.services.hallucination.citation_verifier import (
    CitationVerifier,
    CitationResult,
    Document,
)
from app.services.observability.langfuse_client import LangfuseClient
from app.services.observability.phoenix_client import PhoenixClient
from app.services.rag.embeddings import EmbeddingsService

logger = structlog.get_logger()


@dataclass
class HallucinationIssue:
    """A detected hallucination issue."""

    type: str  # "low_grounding", "inconsistent", "uncited_claim", etc.
    severity: str  # "low", "medium", "high"
    description: str
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class HallucinationResult:
    """Result of hallucination detection."""

    is_hallucination: bool
    confidence: float  # 0-1, how confident we are in the detection
    hallucination_score: float  # 0-1, likelihood of hallucination
    grounding_score: float | None  # 0-1, how well grounded in context
    consistency_score: float | None  # 0-1, how consistent across generations
    relevance_score: float | None  # 0-1, how relevant to query
    factuality_score: float | None  # 0-1, estimated factual accuracy
    issues: list[HallucinationIssue] = field(default_factory=list)
    check_types_performed: list[str] = field(default_factory=list)
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "is_hallucination": self.is_hallucination,
            "confidence": self.confidence,
            "hallucination_score": self.hallucination_score,
            "grounding_score": self.grounding_score,
            "consistency_score": self.consistency_score,
            "relevance_score": self.relevance_score,
            "factuality_score": self.factuality_score,
            "issues": [
                {
                    "type": i.type,
                    "severity": i.severity,
                    "description": i.description,
                    "evidence": i.evidence,
                }
                for i in self.issues
            ],
            "check_types_performed": self.check_types_performed,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }


@dataclass
class HallucinationConfig:
    """Configuration for hallucination detection."""

    # Thresholds
    grounding_threshold: float = 0.7  # Below this is considered poorly grounded
    consistency_threshold: float = 0.8  # Below this is considered inconsistent
    hallucination_threshold: float = 0.5  # Above this is considered hallucination

    # Weights for combined scoring
    grounding_weight: float = 0.4
    consistency_weight: float = 0.3
    citation_weight: float = 0.3

    # Consistency checker settings
    consistency_samples: int = 3
    consistency_temperature: float = 0.7

    # Feature flags
    enable_grounding_check: bool = True
    enable_consistency_check: bool = True
    enable_citation_check: bool = True


class HallucinationDetectionService:
    """
    Service for detecting hallucinations in LLM responses.

    Combines multiple detection methods:
    - Semantic similarity checking (grounding)
    - Response consistency checking
    - Citation verification for RAG
    """

    def __init__(
        self,
        embedding_service: EmbeddingsService | None = None,
        langfuse_client: LangfuseClient | None = None,
        phoenix_client: PhoenixClient | None = None,
        config: HallucinationConfig | None = None,
    ):
        """
        Initialize hallucination detection service.

        Args:
            embedding_service: Service for computing embeddings
            langfuse_client: LangFuse client for logging
            phoenix_client: Phoenix client for evaluation
            config: Detection configuration
        """
        self.config = config or HallucinationConfig()
        self._embedding_service = embedding_service
        self._langfuse = langfuse_client
        self._phoenix = phoenix_client

        # Initialize checkers
        self._semantic_checker: SemanticSimilarityChecker | None = None
        self._consistency_checker: ConsistencyChecker | None = None
        self._citation_verifier = CitationVerifier()

        if embedding_service:
            self._semantic_checker = SemanticSimilarityChecker(embedding_service)

    def set_consistency_checker(self, checker: ConsistencyChecker) -> None:
        """Set the consistency checker (requires LLM gateway)."""
        self._consistency_checker = checker

    async def check(
        self,
        query: str,
        response: str,
        context: list[str] | None = None,
        sources: list[Document] | None = None,
        check_consistency: bool = False,
        log_to_observability: bool = True,
        trace_context: dict[str, Any] | None = None,
        db: AsyncSession | None = None,
        tenant_id: str | None = None,
    ) -> HallucinationResult:
        """
        Check response for hallucinations.

        Args:
            query: The original query/prompt
            response: The LLM response to check
            context: Optional context documents for grounding check
            sources: Optional source documents for citation verification
            check_consistency: Whether to run consistency check (background)
            log_to_observability: Whether to log to LangFuse/Phoenix
            trace_context: Optional trace context for observability
            db: Database session for persistence
            tenant_id: Tenant ID for multi-tenancy

        Returns:
            HallucinationResult with scores and issues
        """
        start_time = datetime.now(UTC)
        issues: list[HallucinationIssue] = []
        check_types: list[str] = []

        grounding_score: float | None = None
        consistency_score: float | None = None
        relevance_score: float | None = None
        factuality_score: float | None = None

        try:
            # Run checks in parallel where possible
            tasks = []

            # Grounding check (if context provided and enabled)
            if (
                context
                and self.config.enable_grounding_check
                and self._semantic_checker
            ):
                tasks.append(self._check_grounding(response, context))
                check_types.append("grounding")

            # Citation check (if sources provided and enabled)
            if sources and self.config.enable_citation_check:
                tasks.append(self._check_citations(response, sources))
                check_types.append("citation")

            # Relevance check (query vs response)
            if self._semantic_checker:
                tasks.append(self._check_relevance(query, response))
                check_types.append("relevance")

            # Execute parallel checks
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Process results
                result_idx = 0

                # Grounding result
                if (
                    context
                    and self.config.enable_grounding_check
                    and self._semantic_checker
                ):
                    grounding_result = results[result_idx]
                    result_idx += 1
                    if isinstance(grounding_result, GroundingResult):
                        grounding_score = grounding_result.grounding_score
                        if grounding_score < self.config.grounding_threshold:
                            issues.append(
                                HallucinationIssue(
                                    type="low_grounding",
                                    severity=self._severity_from_score(
                                        1 - grounding_score
                                    ),
                                    description=f"Response has low grounding in provided context ({grounding_score:.2f})",
                                    evidence={
                                        "grounding_score": grounding_score,
                                        "overall_similarity": grounding_result.details.get("overall_similarity", 0),
                                    },
                                )
                            )
                    elif isinstance(grounding_result, Exception):
                        logger.warning(
                            "Grounding check failed", error=str(grounding_result)
                        )

                # Citation result
                if sources and self.config.enable_citation_check:
                    citation_result = results[result_idx]
                    result_idx += 1
                    if isinstance(citation_result, CitationResult):
                        for claim in citation_result.orphan_claims:
                            issues.append(
                                HallucinationIssue(
                                    type="uncited_claim",
                                    severity="medium",
                                    description=f"Uncited claim: {claim[:100]}...",
                                    evidence={"claim": claim},
                                )
                            )
                        for invalid in [
                            c.source_reference
                            for c in citation_result.citations
                            if not c.verified
                        ]:
                            issues.append(
                                HallucinationIssue(
                                    type="invalid_citation",
                                    severity="high",
                                    description=f"Invalid citation reference: {invalid}",
                                    evidence={"citation": invalid},
                                )
                            )
                    elif isinstance(citation_result, Exception):
                        logger.warning(
                            "Citation check failed", error=str(citation_result)
                        )

                # Relevance result
                if self._semantic_checker:
                    relevance_result = results[result_idx]
                    result_idx += 1
                    if isinstance(relevance_result, float):
                        relevance_score = relevance_result
                        if relevance_score < 0.5:
                            issues.append(
                                HallucinationIssue(
                                    type="low_relevance",
                                    severity=self._severity_from_score(
                                        1 - relevance_score
                                    ),
                                    description=f"Response has low relevance to query ({relevance_score:.2f})",
                                    evidence={"relevance_score": relevance_score},
                                )
                            )
                    elif isinstance(relevance_result, Exception):
                        logger.warning(
                            "Relevance check failed", error=str(relevance_result)
                        )

            # Schedule consistency check in background (no await)
            consistency_task_id: str | None = None
            if (
                check_consistency
                and self.config.enable_consistency_check
                and self._consistency_checker
            ):
                check_types.append("consistency_scheduled")
                try:
                    consistency_task_id = (
                        await self._consistency_checker.schedule_consistency_check(
                            request_id=hashlib.sha256(
                                f"{query}{response}".encode()
                            ).hexdigest()[:16],
                            query=query,
                            response=response,
                            num_samples=self.config.consistency_samples,
                        )
                    )
                except Exception as e:
                    logger.warning("Failed to schedule consistency check", error=str(e))

            # Calculate combined hallucination score
            hallucination_score = self._calculate_hallucination_score(
                grounding_score=grounding_score,
                consistency_score=consistency_score,
                citation_issues=len([i for i in issues if "citation" in i.type]),
                relevance_score=relevance_score,
            )

            # Estimate factuality based on other scores
            factuality_score = self._estimate_factuality(
                grounding_score, relevance_score, len(issues)
            )

            # Determine if hallucination
            is_hallucination = (
                hallucination_score > self.config.hallucination_threshold
            )

            # Calculate confidence
            confidence = self._calculate_confidence(check_types, issues)

            # Calculate duration
            duration_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

            result = HallucinationResult(
                is_hallucination=is_hallucination,
                confidence=confidence,
                hallucination_score=hallucination_score,
                grounding_score=grounding_score,
                consistency_score=consistency_score,
                relevance_score=relevance_score,
                factuality_score=factuality_score,
                issues=issues,
                check_types_performed=check_types,
                duration_ms=duration_ms,
                metadata={
                    "consistency_task_id": consistency_task_id,
                    "context_count": len(context) if context else 0,
                    "source_count": len(sources) if sources else 0,
                },
            )

            # Log to observability platforms
            if log_to_observability:
                await self._log_to_observability(
                    result, query, response, trace_context
                )

            # Persist to database
            if db and tenant_id:
                await self._persist_result(db, tenant_id, query, response, result)

            return result

        except Exception as e:
            logger.error("Hallucination detection failed", error=str(e))
            # Return safe default
            return HallucinationResult(
                is_hallucination=False,
                confidence=0.0,
                hallucination_score=0.0,
                grounding_score=None,
                consistency_score=None,
                relevance_score=None,
                factuality_score=None,
                issues=[],
                check_types_performed=[],
                duration_ms=(datetime.now(UTC) - start_time).total_seconds() * 1000,
                metadata={"error": str(e)},
            )

    async def _check_grounding(
        self, response: str, context: list[str]
    ) -> GroundingResult:
        """Check how well response is grounded in context."""
        if not self._semantic_checker:
            raise ValueError("Semantic checker not initialized")
        return await self._semantic_checker.check_grounding(response, context)

    async def _check_citations(
        self, response: str, sources: list[Document]
    ) -> CitationResult:
        """Verify citations in response."""
        return await self._citation_verifier.verify_citations(response, sources)

    async def _check_relevance(self, query: str, response: str) -> float:
        """Check relevance of response to query."""
        if not self._semantic_checker:
            raise ValueError("Semantic checker not initialized")
        result = await self._semantic_checker.compute_similarity(query, response)
        return result.similarity

    def _calculate_hallucination_score(
        self,
        grounding_score: float | None,
        consistency_score: float | None,
        citation_issues: int,
        relevance_score: float | None,
    ) -> float:
        """Calculate combined hallucination score."""
        scores = []
        weights = []

        # Grounding (inverted - lower grounding = higher hallucination)
        if grounding_score is not None:
            scores.append(1 - grounding_score)
            weights.append(self.config.grounding_weight)

        # Consistency (inverted)
        if consistency_score is not None:
            scores.append(1 - consistency_score)
            weights.append(self.config.consistency_weight)

        # Citation issues (normalized)
        if citation_issues > 0:
            citation_score = min(citation_issues / 5, 1.0)  # Cap at 5 issues
            scores.append(citation_score)
            weights.append(self.config.citation_weight)

        # Relevance (inverted)
        if relevance_score is not None:
            scores.append(1 - relevance_score)
            weights.append(0.2)  # Lower weight for relevance

        if not scores:
            return 0.0

        # Weighted average
        total_weight = sum(weights)
        return sum(s * w for s, w in zip(scores, weights)) / total_weight

    def _estimate_factuality(
        self,
        grounding_score: float | None,
        relevance_score: float | None,
        issue_count: int,
    ) -> float:
        """Estimate factuality score based on available metrics."""
        base_score = 0.7  # Assume moderate factuality by default

        if grounding_score is not None:
            base_score = (base_score + grounding_score) / 2

        if relevance_score is not None:
            base_score = (base_score + relevance_score) / 2

        # Penalize for issues
        penalty = min(issue_count * 0.1, 0.5)
        return max(0.0, base_score - penalty)

    def _calculate_confidence(
        self, check_types: list[str], issues: list[HallucinationIssue]
    ) -> float:
        """Calculate confidence in the detection result."""
        # Base confidence on number of checks performed
        base_confidence = min(len(check_types) * 0.25, 0.75)

        # Increase confidence if we found issues
        if issues:
            base_confidence += 0.15

        # Higher confidence with more severe issues
        high_severity = sum(1 for i in issues if i.severity == "high")
        if high_severity > 0:
            base_confidence += 0.1

        return min(base_confidence, 1.0)

    def _severity_from_score(self, score: float) -> str:
        """Convert score to severity level."""
        if score > 0.7:
            return "high"
        elif score > 0.4:
            return "medium"
        return "low"

    async def _log_to_observability(
        self,
        result: HallucinationResult,
        query: str,
        response: str,
        trace_context: dict[str, Any] | None,
    ) -> None:
        """Log result to LangFuse and Phoenix."""
        try:
            # Log to LangFuse
            if self._langfuse and trace_context:
                self._langfuse.log_hallucination_score(trace_context, result.to_dict())

            # Log to Phoenix
            if self._phoenix:
                await self._phoenix.log_evaluation(
                    trace_id=trace_context.get("trace_id") if trace_context else None,
                    name="hallucination_detection",
                    score=result.hallucination_score,
                    metadata={
                        "is_hallucination": result.is_hallucination,
                        "grounding_score": result.grounding_score,
                        "issues": [i.type for i in result.issues],
                    },
                )
        except Exception as e:
            logger.warning("Failed to log to observability", error=str(e))

    async def _persist_result(
        self,
        db: AsyncSession,
        tenant_id: str,
        query: str,
        response: str,
        result: HallucinationResult,
    ) -> None:
        """Persist result to database."""
        try:
            log_entry = HallucinationLog(
                tenant_id=tenant_id,
                query_hash=hashlib.sha256(query.encode()).hexdigest(),
                response_hash=hashlib.sha256(response.encode()).hexdigest(),
                hallucination_score=result.hallucination_score,
                grounding_score=result.grounding_score,
                relevance_score=result.relevance_score,
                factuality_score=result.factuality_score,
                consistency_score=result.consistency_score,
                is_hallucination=result.is_hallucination,
                confidence=result.confidence,
                issues=[i.__dict__ for i in result.issues],
                check_type=CheckType.COMBINED,
                duration_ms=result.duration_ms,
                metadata=result.metadata,
            )
            db.add(log_entry)
            await db.commit()
        except Exception as e:
            logger.warning("Failed to persist hallucination result", error=str(e))
            await db.rollback()

    async def get_analytics(
        self,
        db: AsyncSession,
        tenant_id: str,
        days: int = 30,
    ) -> dict[str, Any]:
        """Get hallucination analytics for a tenant."""
        from datetime import timedelta

        start_time = datetime.now(UTC) - timedelta(days=days)

        # Get aggregate metrics
        result = await db.execute(
            select(
                func.count(HallucinationLog.id).label("total_checks"),
                func.sum(
                    func.cast(HallucinationLog.is_hallucination, Integer)
                ).label("hallucination_count"),
                func.avg(HallucinationLog.hallucination_score).label(
                    "avg_hallucination_score"
                ),
                func.avg(HallucinationLog.grounding_score).label("avg_grounding_score"),
                func.avg(HallucinationLog.relevance_score).label("avg_relevance_score"),
                func.avg(HallucinationLog.confidence).label("avg_confidence"),
            ).where(
                HallucinationLog.tenant_id == tenant_id,
                HallucinationLog.created_at >= start_time,
            )
        )

        row = result.fetchone()
        if not row:
            return {
                "total_checks": 0,
                "hallucination_count": 0,
                "hallucination_rate": 0.0,
                "avg_hallucination_score": 0.0,
                "avg_grounding_score": 0.0,
                "avg_relevance_score": 0.0,
                "avg_confidence": 0.0,
            }

        total = row.total_checks or 0
        hallucinations = row.hallucination_count or 0

        return {
            "total_checks": total,
            "hallucination_count": hallucinations,
            "hallucination_rate": hallucinations / total if total > 0 else 0.0,
            "avg_hallucination_score": float(row.avg_hallucination_score or 0),
            "avg_grounding_score": float(row.avg_grounding_score or 0),
            "avg_relevance_score": float(row.avg_relevance_score or 0),
            "avg_confidence": float(row.avg_confidence or 0),
        }

    async def get_trends(
        self,
        db: AsyncSession,
        tenant_id: str,
        days: int = 30,
        granularity: str = "daily",
    ) -> list[dict[str, Any]]:
        """Get hallucination trends over time."""
        from datetime import timedelta
        from sqlalchemy import case

        start_time = datetime.now(UTC) - timedelta(days=days)

        # Determine date truncation based on granularity
        if granularity == "hourly":
            date_trunc = func.date_trunc("hour", HallucinationLog.created_at)
        elif granularity == "weekly":
            date_trunc = func.date_trunc("week", HallucinationLog.created_at)
        else:
            date_trunc = func.date_trunc("day", HallucinationLog.created_at)

        result = await db.execute(
            select(
                date_trunc.label("period"),
                func.count(HallucinationLog.id).label("total_checks"),
                func.sum(
                    case((HallucinationLog.is_hallucination == True, 1), else_=0)
                ).label("hallucination_count"),
                func.avg(HallucinationLog.hallucination_score).label(
                    "avg_hallucination_score"
                ),
            )
            .where(
                HallucinationLog.tenant_id == tenant_id,
                HallucinationLog.created_at >= start_time,
            )
            .group_by(date_trunc)
            .order_by(date_trunc)
        )

        trends = []
        for row in result.fetchall():
            total = row.total_checks or 0
            hallucinations = row.hallucination_count or 0
            trends.append(
                {
                    "period": row.period.isoformat() if row.period else None,
                    "total_checks": total,
                    "hallucination_count": hallucinations,
                    "hallucination_rate": hallucinations / total if total > 0 else 0.0,
                    "avg_hallucination_score": float(row.avg_hallucination_score or 0),
                }
            )

        return trends

    async def get_recent_logs(
        self,
        db: AsyncSession,
        tenant_id: str,
        limit: int = 50,
        only_hallucinations: bool = False,
    ) -> list[dict[str, Any]]:
        """Get recent hallucination logs."""
        conditions = [HallucinationLog.tenant_id == tenant_id]

        if only_hallucinations:
            conditions.append(HallucinationLog.is_hallucination == True)

        query = (
            select(HallucinationLog)
            .where(*conditions)
            .order_by(HallucinationLog.created_at.desc())
            .limit(limit)
        )

        result = await db.execute(query)
        logs = result.scalars().all()

        return [
            {
                "id": str(log.id),
                "trace_id": log.trace_id,
                "hallucination_score": log.hallucination_score,
                "grounding_score": log.grounding_score,
                "is_hallucination": log.is_hallucination,
                "confidence": log.confidence,
                "issues": log.issues,
                "check_type": log.check_type.value if log.check_type else None,
                "duration_ms": log.duration_ms,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ]


# Import Integer for type casting in analytics
from sqlalchemy import Integer
