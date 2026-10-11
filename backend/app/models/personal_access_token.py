"""Personal Access Token (PAT) Model.

Personal Access Tokens provide API access for:
- CI/CD automation
- CLI tools
- Third-party integrations
- Service accounts
"""

import secrets
from datetime import UTC, datetime, timedelta
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.security import get_password_hash, verify_password


class TokenScope(str, Enum):
    """Available PAT scopes."""

    # Read scopes
    READ_PROJECTS = "read:projects"
    READ_ANALYTICS = "read:analytics"
    READ_METRICS = "read:metrics"
    READ_CONNECTIONS = "read:connections"
    READ_BLUEPRINTS = "read:blueprints"

    # Write scopes
    WRITE_PROJECTS = "write:projects"
    WRITE_CONNECTIONS = "write:connections"
    WRITE_BLUEPRINTS = "write:blueprints"

    # Admin scopes
    ADMIN_ORGANIZATION = "admin:organization"
    ADMIN_MEMBERS = "admin:members"

    # Full access
    FULL_ACCESS = "*"


class PersonalAccessToken(Base):
    """Personal Access Token model."""

    __tablename__ = "personal_access_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Token identification
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Token value (hashed - only shown once on creation)
    token_hash = Column(String(255), nullable=False)
    token_prefix = Column(String(20), nullable=False)  # First 8 chars for identification

    # Scopes
    scopes = Column(ARRAY(String), default=list)

    # Expiration
    expires_at = Column(DateTime, nullable=True)  # None = never expires

    # Usage tracking
    last_used_at = Column(DateTime)
    last_used_ip = Column(String(45))
    use_count = Column(Integer, default=0)

    # Status
    is_active = Column(Boolean, default=True)
    revoked_at = Column(DateTime)
    revoked_reason = Column(String(255))

    # Token metadata (renamed from 'metadata' which is reserved in SQLAlchemy)
    token_metadata = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # Relationships
    user = relationship("User", back_populates="personal_access_tokens")


class PATCreateRequest(BaseModel):
    """Request to create a PAT."""

    name: str
    description: str | None = None
    scopes: list[str] = [TokenScope.READ_PROJECTS]
    expires_in_days: int | None = 90  # None = never expires


class PATCreateResponse(BaseModel):
    """Response after creating a PAT (only time token is shown)."""

    id: str
    name: str
    token: str  # Full token - only shown once!
    token_prefix: str
    scopes: list[str]
    expires_at: datetime | None
    created_at: datetime


class PATInfo(BaseModel):
    """Public PAT information (without token value)."""

    id: str
    name: str
    description: str | None
    token_prefix: str
    scopes: list[str]
    expires_at: datetime | None
    last_used_at: datetime | None
    is_active: bool
    created_at: datetime


class PersonalAccessTokenService:
    """Service for managing Personal Access Tokens."""

    # Token format: nxa_{random_40_chars}
    TOKEN_PREFIX = "nxa_"
    TOKEN_LENGTH = 40

    async def create_token(
        self,
        session: AsyncSession,
        tenant_id: str,
        user_id: str,
        request: PATCreateRequest,
    ) -> PATCreateResponse:
        """Create a new Personal Access Token.

        Args:
            session: Database session
            tenant_id: Tenant ID
            user_id: User ID creating the token
            request: Token creation request

        Returns:
            PATCreateResponse with the token (shown only once)
        """
        # Generate secure random token
        random_part = secrets.token_urlsafe(self.TOKEN_LENGTH)
        full_token = f"{self.TOKEN_PREFIX}{random_part}"
        token_prefix = full_token[:12]  # "nxa_" + 8 chars

        # Hash the token for storage
        token_hash = get_password_hash(full_token)

        # Calculate expiration
        expires_at = None
        if request.expires_in_days:
            expires_at = datetime.now(UTC) + timedelta(days=request.expires_in_days)

        # Validate scopes
        valid_scopes = [s.value for s in TokenScope]
        scopes = [s for s in request.scopes if s in valid_scopes]

        # Create token record
        pat = PersonalAccessToken(
            tenant_id=tenant_id,
            user_id=user_id,
            name=request.name,
            description=request.description,
            token_hash=token_hash,
            token_prefix=token_prefix,
            scopes=scopes,
            expires_at=expires_at,
        )

        session.add(pat)
        await session.commit()
        await session.refresh(pat)

        return PATCreateResponse(
            id=str(pat.id),
            name=pat.name,
            token=full_token,  # Only time the full token is returned!
            token_prefix=token_prefix,
            scopes=scopes,
            expires_at=expires_at,
            created_at=pat.created_at,
        )

    async def validate_token(
        self,
        session: AsyncSession,
        token: str,
        required_scopes: list[str] | None = None,
    ) -> tuple[PersonalAccessToken | None, str | None]:
        """Validate a PAT and check scopes.

        Args:
            session: Database session
            token: Full token string
            required_scopes: Required scopes (optional)

        Returns:
            Tuple of (token_record, error_message)
        """
        from sqlalchemy import select

        # Extract prefix for lookup
        if not token.startswith(self.TOKEN_PREFIX):
            return None, "Invalid token format"

        token_prefix = token[:12]

        # Find matching tokens by prefix
        result = await session.execute(
            select(PersonalAccessToken).where(
                PersonalAccessToken.token_prefix == token_prefix,
                PersonalAccessToken.is_active == True,
            )
        )
        candidates = list(result.scalars().all())

        # Verify hash for each candidate
        valid_token = None
        for candidate in candidates:
            if verify_password(token, candidate.token_hash):
                valid_token = candidate
                break

        if not valid_token:
            return None, "Invalid token"

        # Check expiration
        if valid_token.expires_at and valid_token.expires_at < datetime.now(UTC):
            return None, "Token expired"

        # Check scopes
        if required_scopes:
            token_scopes = set(valid_token.scopes)

            # Full access grants all scopes
            if TokenScope.FULL_ACCESS.value not in token_scopes:
                missing_scopes = set(required_scopes) - token_scopes
                if missing_scopes:
                    return None, f"Missing scopes: {', '.join(missing_scopes)}"

        return valid_token, None

    async def record_usage(
        self,
        session: AsyncSession,
        token_id: str,
        ip_address: str | None = None,
    ) -> None:
        """Record token usage for analytics.

        Args:
            session: Database session
            token_id: Token ID
            ip_address: Client IP address
        """
        from sqlalchemy import select

        result = await session.execute(
            select(PersonalAccessToken).where(PersonalAccessToken.id == token_id)
        )
        token = result.scalar_one_or_none()

        if token:
            token.last_used_at = datetime.now(UTC)
            token.last_used_ip = ip_address
            token.use_count = PersonalAccessToken.use_count + 1
            await session.commit()

    async def revoke_token(
        self,
        session: AsyncSession,
        token_id: str,
        user_id: str,
        reason: str | None = None,
    ) -> bool:
        """Revoke a Personal Access Token.

        Args:
            session: Database session
            token_id: Token ID to revoke
            user_id: User performing revocation
            reason: Revocation reason

        Returns:
            True if revoked successfully
        """
        from sqlalchemy import select

        result = await session.execute(
            select(PersonalAccessToken).where(
                PersonalAccessToken.id == token_id,
                PersonalAccessToken.user_id == user_id,
            )
        )
        token = result.scalar_one_or_none()

        if not token:
            return False

        token.is_active = False
        token.revoked_at = datetime.now(UTC)
        token.revoked_reason = reason

        await session.commit()
        return True

    async def list_user_tokens(
        self,
        session: AsyncSession,
        tenant_id: str,
        user_id: str,
        include_revoked: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[PATInfo]:
        """List all PATs for a user.

        Args:
            session: Database session
            tenant_id: Tenant ID
            user_id: User ID
            include_revoked: Include revoked tokens
            limit: Max tokens to return
            offset: Pagination offset

        Returns:
            List of PATInfo
        """
        from sqlalchemy import select

        query = select(PersonalAccessToken).where(
            PersonalAccessToken.tenant_id == tenant_id,
            PersonalAccessToken.user_id == user_id,
        )

        if not include_revoked:
            query = query.where(PersonalAccessToken.is_active == True)

        query = query.order_by(PersonalAccessToken.created_at.desc()).offset(offset).limit(limit)

        result = await session.execute(query)
        tokens = result.scalars().all()

        return [
            PATInfo(
                id=str(t.id),
                name=t.name,
                description=t.description,
                token_prefix=t.token_prefix,
                scopes=t.scopes or [],
                expires_at=t.expires_at,
                last_used_at=t.last_used_at,
                is_active=t.is_active,
                created_at=t.created_at,
            )
            for t in tokens
        ]

    async def rotate_token(
        self,
        session: AsyncSession,
        token_id: str,
        user_id: str,
    ) -> PATCreateResponse | None:
        """Rotate a PAT (revoke old, create new with same settings).

        Args:
            session: Database session
            token_id: Token ID to rotate
            user_id: User performing rotation

        Returns:
            New PATCreateResponse or None if failed
        """
        from sqlalchemy import select

        # Get old token
        result = await session.execute(
            select(PersonalAccessToken).where(
                PersonalAccessToken.id == token_id,
                PersonalAccessToken.user_id == user_id,
                PersonalAccessToken.is_active == True,
            )
        )
        old_token = result.scalar_one_or_none()

        if not old_token:
            return None

        # Create new token with same settings
        request = PATCreateRequest(
            name=f"{old_token.name} (rotated)",
            description=old_token.description,
            scopes=old_token.scopes or [],
            expires_in_days=None,  # Calculate from old expiration
        )

        # Calculate remaining days if old token had expiration
        if old_token.expires_at:
            remaining = old_token.expires_at - datetime.now(UTC)
            request.expires_in_days = max(1, remaining.days)

        # Create new token
        new_token = await self.create_token(
            session,
            str(old_token.tenant_id),
            str(old_token.user_id),
            request,
        )

        # Revoke old token
        await self.revoke_token(
            session,
            token_id,
            user_id,
            reason="Rotated",
        )

        return new_token

    async def cleanup_expired_tokens(
        self,
        session: AsyncSession,
        days_after_expiry: int = 30,
    ) -> int:
        """Clean up expired tokens.

        Args:
            session: Database session
            days_after_expiry: Days after expiry to delete

        Returns:
            Number of tokens deleted
        """
        from sqlalchemy import delete

        cutoff = datetime.now(UTC) - timedelta(days=days_after_expiry)

        result = await session.execute(
            delete(PersonalAccessToken).where(
                PersonalAccessToken.expires_at < cutoff,
                PersonalAccessToken.is_active == False,
            )
        )

        await session.commit()
        return result.rowcount


# Singleton instance
pat_service = PersonalAccessTokenService()
