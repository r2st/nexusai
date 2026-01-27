"""Authentication service."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    Token,
    create_tokens,
    get_password_hash,
    verify_password,
    verify_token,
)
from app.models.user import AuthProvider, User, UserRole


class AuthService:
    """Service for authentication operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_email(self, email: str) -> User | None:
        """Get user by email."""
        result = await self.db.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: str) -> User | None:
        """Get user by ID."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> User | None:
        """Get user by username."""
        result = await self.db.execute(
            select(User).where(User.username == username.lower())
        )
        return result.scalar_one_or_none()

    async def create_user(
        self,
        email: str,
        username: str,
        password: str | None = None,
        full_name: str | None = None,
        auth_provider: AuthProvider = AuthProvider.LOCAL,
        provider_id: str | None = None,
        is_verified: bool = False,
    ) -> User:
        """Create a new user."""
        user = User(
            email=email.lower(),
            username=username.lower(),
            hashed_password=get_password_hash(password) if password else None,
            full_name=full_name,
            auth_provider=auth_provider.value,
            provider_id=provider_id,
            is_verified=is_verified,
            role=UserRole.USER.value,
        )
        self.db.add(user)
        await self.db.flush()
        return user

    async def authenticate_user(self, email: str, password: str) -> User | None:
        """Authenticate user with email and password."""
        user = await self.get_user_by_email(email)
        if not user:
            return None
        if not user.hashed_password:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        if not user.is_active:
            return None

        # Update last login
        user.last_login_at = datetime.now(UTC)
        await self.db.flush()

        return user

    async def login(self, email: str, password: str) -> Token | None:
        """Login user and return tokens."""
        user = await self.authenticate_user(email, password)
        if not user:
            return None

        return create_tokens(
            user_id=user.id,
            email=user.email,
            scopes=[user.role],
        )

    async def refresh_tokens(self, refresh_token: str) -> Token | None:
        """Refresh access token using refresh token."""
        token_data = verify_token(refresh_token, token_type="refresh")
        if not token_data:
            return None

        user = await self.get_user_by_id(token_data.user_id)
        if not user or not user.is_active:
            return None

        return create_tokens(
            user_id=user.id,
            email=user.email,
            scopes=[user.role],
        )

    async def update_password(
        self,
        user: User,
        new_password: str,
    ) -> bool:
        """Update user password."""
        user.hashed_password = get_password_hash(new_password)
        await self.db.flush()
        return True

    async def verify_email(self, user: User) -> bool:
        """Mark user email as verified."""
        user.is_verified = True
        await self.db.flush()
        return True

    async def update_profile(
        self,
        user: User,
        full_name: str | None = None,
        bio: str | None = None,
        avatar_url: str | None = None,
    ) -> User:
        """Update user profile."""
        if full_name is not None:
            user.full_name = full_name
        if bio is not None:
            user.bio = bio
        if avatar_url is not None:
            user.avatar_url = avatar_url
        await self.db.flush()
        return user
