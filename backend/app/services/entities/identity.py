"""Identity resolution service for cross-source entity mapping.

Handles mapping identities across different sources (e.g., same developer
with different usernames on GitHub and GitLab).
"""

from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.entities.models import (
    EntityType,
    IdentityMapping,
)

logger = structlog.get_logger()


class IdentityResolver:
    """Resolves identities across multiple sources.

    Uses email matching, username similarity, and manual verification
    to map identities across sources to a canonical identity.
    """

    # Confidence thresholds
    EMAIL_MATCH_CONFIDENCE = 0.95
    USERNAME_MATCH_CONFIDENCE = 0.7
    MANUAL_VERIFICATION_CONFIDENCE = 1.0

    async def resolve(
        self,
        session: AsyncSession,
        tenant_id: str,
        source: str,
        source_id: str,
        entity_type: EntityType,
        hints: dict[str, Any] | None = None,
    ) -> str:
        """Resolve a source identity to a canonical identity.

        Args:
            session: Database session
            tenant_id: Tenant ID
            source: Source system (github, gitlab, etc)
            source_id: ID in source system
            entity_type: Type of entity
            hints: Additional hints for matching (email, username, name)

        Returns:
            Canonical identity ID
        """
        hints = hints or {}

        # Check for existing mapping
        existing = await self.get_mapping(
            session, tenant_id, source, source_id, entity_type
        )
        if existing:
            return existing["canonical_id"]

        # Try to find matching identity
        canonical_id = await self._find_matching_identity(
            session, tenant_id, entity_type, hints
        )

        if canonical_id:
            # Create mapping to existing identity
            await self.create_mapping(
                session,
                tenant_id=tenant_id,
                canonical_id=canonical_id,
                entity_type=entity_type,
                source=source,
                source_id=source_id,
                source_username=hints.get("username"),
                source_email=hints.get("email"),
                confidence=self._calculate_confidence(hints),
            )
            return canonical_id

        # Create new canonical identity
        from uuid import uuid4
        canonical_id = str(uuid4())

        await self.create_mapping(
            session,
            tenant_id=tenant_id,
            canonical_id=canonical_id,
            entity_type=entity_type,
            source=source,
            source_id=source_id,
            source_username=hints.get("username"),
            source_email=hints.get("email"),
            confidence=1.0,  # First mapping is definitive
        )

        logger.info(
            "Created new canonical identity",
            canonical_id=canonical_id,
            source=source,
            source_id=source_id,
        )

        return canonical_id

    async def _find_matching_identity(
        self,
        session: AsyncSession,
        tenant_id: str,
        entity_type: EntityType,
        hints: dict[str, Any],
    ) -> str | None:
        """Find an existing canonical identity that matches the hints.

        Priority:
        1. Email match (highest confidence)
        2. Username match across sources
        3. Name similarity (lower confidence)
        """
        # Try email match first
        email = hints.get("email")
        if email:
            result = await session.execute(
                text("""
                    SELECT canonical_id FROM identity_mappings
                    WHERE tenant_id = :tenant_id
                    AND entity_type = :entity_type
                    AND source_email = :email
                    AND confidence >= :threshold
                    LIMIT 1
                """),
                {
                    "tenant_id": tenant_id,
                    "entity_type": entity_type.value,
                    "email": email.lower(),
                    "threshold": self.EMAIL_MATCH_CONFIDENCE,
                },
            )
            row = result.fetchone()
            if row:
                return row.canonical_id

        # Try username match
        username = hints.get("username")
        if username:
            result = await session.execute(
                text("""
                    SELECT canonical_id FROM identity_mappings
                    WHERE tenant_id = :tenant_id
                    AND entity_type = :entity_type
                    AND LOWER(source_username) = :username
                    AND confidence >= :threshold
                    LIMIT 1
                """),
                {
                    "tenant_id": tenant_id,
                    "entity_type": entity_type.value,
                    "username": username.lower(),
                    "threshold": self.USERNAME_MATCH_CONFIDENCE,
                },
            )
            row = result.fetchone()
            if row:
                return row.canonical_id

        return None

    def _calculate_confidence(self, hints: dict[str, Any]) -> float:
        """Calculate confidence score based on available hints."""
        if hints.get("email"):
            return self.EMAIL_MATCH_CONFIDENCE
        elif hints.get("username"):
            return self.USERNAME_MATCH_CONFIDENCE
        return 0.5

    async def get_mapping(
        self,
        session: AsyncSession,
        tenant_id: str,
        source: str,
        source_id: str,
        entity_type: EntityType,
    ) -> dict[str, Any] | None:
        """Get existing identity mapping.

        Args:
            session: Database session
            tenant_id: Tenant ID
            source: Source system
            source_id: ID in source system
            entity_type: Type of entity

        Returns:
            Mapping data or None
        """
        result = await session.execute(
            text("""
                SELECT * FROM identity_mappings
                WHERE tenant_id = :tenant_id
                AND source = :source
                AND source_id = :source_id
                AND entity_type = :entity_type
            """),
            {
                "tenant_id": tenant_id,
                "source": source,
                "source_id": source_id,
                "entity_type": entity_type.value,
            },
        )
        row = result.fetchone()

        if not row:
            return None

        return {
            "id": row.id,
            "tenant_id": row.tenant_id,
            "canonical_id": row.canonical_id,
            "entity_type": row.entity_type,
            "source": row.source,
            "source_id": row.source_id,
            "source_username": row.source_username,
            "source_email": row.source_email,
            "confidence": row.confidence,
            "verified": row.verified,
        }

    async def create_mapping(
        self,
        session: AsyncSession,
        tenant_id: str,
        canonical_id: str,
        entity_type: EntityType,
        source: str,
        source_id: str,
        source_username: str | None = None,
        source_email: str | None = None,
        confidence: float = 1.0,
    ) -> IdentityMapping:
        """Create a new identity mapping.

        Args:
            session: Database session
            tenant_id: Tenant ID
            canonical_id: Canonical identity ID
            entity_type: Type of entity
            source: Source system
            source_id: ID in source system
            source_username: Username in source system
            source_email: Email in source system
            confidence: Confidence score (0-1)

        Returns:
            Created mapping
        """
        mapping = IdentityMapping(
            tenant_id=tenant_id,
            canonical_id=canonical_id,
            entity_type=entity_type,
            source=source,
            source_id=source_id,
            source_username=source_username,
            source_email=source_email.lower() if source_email else None,
            confidence=confidence,
        )

        await session.execute(
            text("""
                INSERT INTO identity_mappings (
                    id, tenant_id, canonical_id, entity_type, source, source_id,
                    source_username, source_email, confidence, verified,
                    created_at, updated_at
                ) VALUES (
                    :id, :tenant_id, :canonical_id, :entity_type, :source, :source_id,
                    :source_username, :source_email, :confidence, :verified,
                    :created_at, :updated_at
                )
                ON CONFLICT (tenant_id, source, source_id, entity_type)
                DO UPDATE SET
                    canonical_id = EXCLUDED.canonical_id,
                    source_username = EXCLUDED.source_username,
                    source_email = EXCLUDED.source_email,
                    confidence = GREATEST(identity_mappings.confidence, EXCLUDED.confidence),
                    updated_at = EXCLUDED.updated_at
            """),
            {
                "id": mapping.id,
                "tenant_id": mapping.tenant_id,
                "canonical_id": mapping.canonical_id,
                "entity_type": mapping.entity_type.value,
                "source": mapping.source,
                "source_id": mapping.source_id,
                "source_username": mapping.source_username,
                "source_email": mapping.source_email,
                "confidence": mapping.confidence,
                "verified": mapping.verified,
                "created_at": mapping.created_at,
                "updated_at": mapping.updated_at,
            },
        )
        await session.flush()

        return mapping

    async def merge_identities(
        self,
        session: AsyncSession,
        tenant_id: str,
        source_canonical_id: str,
        target_canonical_id: str,
        verified_by: str | None = None,
    ) -> int:
        """Merge two canonical identities.

        All mappings from source_canonical_id are moved to target_canonical_id.

        Args:
            session: Database session
            tenant_id: Tenant ID
            source_canonical_id: ID to merge from
            target_canonical_id: ID to merge into
            verified_by: User who verified the merge

        Returns:
            Number of mappings updated
        """
        result = await session.execute(
            text("""
                UPDATE identity_mappings
                SET canonical_id = :target_id,
                    verified = true,
                    verified_by = :verified_by,
                    verified_at = :verified_at,
                    updated_at = :updated_at
                WHERE tenant_id = :tenant_id
                AND canonical_id = :source_id
            """),
            {
                "tenant_id": tenant_id,
                "source_id": source_canonical_id,
                "target_id": target_canonical_id,
                "verified_by": verified_by,
                "verified_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            },
        )
        await session.flush()

        count = result.rowcount
        logger.info(
            "Merged identities",
            source=source_canonical_id,
            target=target_canonical_id,
            mappings_updated=count,
        )

        return count

    async def split_identity(
        self,
        session: AsyncSession,
        mapping_id: str,
        verified_by: str | None = None,
    ) -> str:
        """Split a mapping to a new canonical identity.

        Creates a new canonical ID for this specific mapping.

        Args:
            session: Database session
            mapping_id: Mapping to split
            verified_by: User who verified the split

        Returns:
            New canonical ID
        """
        from uuid import uuid4
        new_canonical_id = str(uuid4())

        await session.execute(
            text("""
                UPDATE identity_mappings
                SET canonical_id = :new_canonical_id,
                    verified = true,
                    verified_by = :verified_by,
                    verified_at = :verified_at,
                    updated_at = :updated_at
                WHERE id = :mapping_id
            """),
            {
                "mapping_id": mapping_id,
                "new_canonical_id": new_canonical_id,
                "verified_by": verified_by,
                "verified_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            },
        )
        await session.flush()

        logger.info(
            "Split identity",
            mapping_id=mapping_id,
            new_canonical_id=new_canonical_id,
        )

        return new_canonical_id

    async def get_all_mappings(
        self,
        session: AsyncSession,
        tenant_id: str,
        canonical_id: str,
    ) -> list[dict[str, Any]]:
        """Get all mappings for a canonical identity.

        Args:
            session: Database session
            tenant_id: Tenant ID
            canonical_id: Canonical identity ID

        Returns:
            List of mappings
        """
        result = await session.execute(
            text("""
                SELECT * FROM identity_mappings
                WHERE tenant_id = :tenant_id
                AND canonical_id = :canonical_id
                ORDER BY confidence DESC, created_at ASC
            """),
            {
                "tenant_id": tenant_id,
                "canonical_id": canonical_id,
            },
        )
        rows = result.fetchall()

        return [
            {
                "id": row.id,
                "source": row.source,
                "source_id": row.source_id,
                "source_username": row.source_username,
                "source_email": row.source_email,
                "confidence": row.confidence,
                "verified": row.verified,
                "verified_by": row.verified_by,
                "verified_at": row.verified_at,
                "created_at": row.created_at,
            }
            for row in rows
        ]

    async def suggest_merges(
        self,
        session: AsyncSession,
        tenant_id: str,
        entity_type: EntityType,
        min_confidence: float = 0.7,
    ) -> list[dict[str, Any]]:
        """Suggest potential identity merges based on similarity.

        Args:
            session: Database session
            tenant_id: Tenant ID
            entity_type: Entity type to analyze
            min_confidence: Minimum confidence threshold

        Returns:
            List of suggested merges
        """
        # Find potential duplicates by email
        result = await session.execute(
            text("""
                SELECT
                    m1.canonical_id as canonical_id_1,
                    m2.canonical_id as canonical_id_2,
                    m1.source_email as email,
                    :email_confidence as confidence,
                    'email_match' as reason
                FROM identity_mappings m1
                JOIN identity_mappings m2 ON (
                    m1.tenant_id = m2.tenant_id
                    AND m1.entity_type = m2.entity_type
                    AND m1.source_email = m2.source_email
                    AND m1.canonical_id < m2.canonical_id
                )
                WHERE m1.tenant_id = :tenant_id
                AND m1.entity_type = :entity_type
                AND m1.source_email IS NOT NULL
            """),
            {
                "tenant_id": tenant_id,
                "entity_type": entity_type.value,
                "email_confidence": self.EMAIL_MATCH_CONFIDENCE,
            },
        )
        suggestions = []

        for row in result.fetchall():
            if row.confidence >= min_confidence:
                suggestions.append({
                    "canonical_id_1": row.canonical_id_1,
                    "canonical_id_2": row.canonical_id_2,
                    "match_value": row.email,
                    "confidence": row.confidence,
                    "reason": row.reason,
                })

        return suggestions


# Global resolver instance
_identity_resolver: IdentityResolver | None = None


def get_identity_resolver() -> IdentityResolver:
    """Get the global identity resolver instance."""
    global _identity_resolver
    if _identity_resolver is None:
        _identity_resolver = IdentityResolver()
    return _identity_resolver
