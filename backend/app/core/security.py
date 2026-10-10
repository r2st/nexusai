"""Security utilities for authentication and authorization."""

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
import structlog

from app.core.config import settings

logger = structlog.get_logger()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenData(BaseModel):
    """Token payload data."""

    user_id: str
    email: str | None = None
    scopes: list[str] = []
    exp: datetime | None = None


class Token(BaseModel):
    """Token response model."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_tokens(user_id: str, email: str, scopes: list[str] | None = None) -> Token:
    """Create both access and refresh tokens."""
    data = {
        "sub": user_id,
        "email": email,
        "scopes": scopes or [],
    }
    access_token = create_access_token(data)
    refresh_token = create_refresh_token(data)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def decode_token(token: str) -> TokenData | None:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        user_id: str | None = payload.get("sub")
        if user_id is None:
            return None

        return TokenData(
            user_id=user_id,
            email=payload.get("email"),
            scopes=payload.get("scopes", []),
            exp=datetime.fromtimestamp(payload.get("exp", 0), tz=UTC),
        )
    except JWTError as e:
        logger.debug("Token decode failed", error=str(e))
        return None


def verify_token(token: str, token_type: str = "access") -> TokenData | None:
    """Verify a token and check its type."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )

        if payload.get("type") != token_type:
            return None

        user_id: str | None = payload.get("sub")
        if user_id is None:
            return None

        return TokenData(
            user_id=user_id,
            email=payload.get("email"),
            scopes=payload.get("scopes", []),
            exp=datetime.fromtimestamp(payload.get("exp", 0), tz=UTC),
        )
    except JWTError as e:
        logger.debug("Token verification failed", token_type=token_type, error=str(e))
        return None
