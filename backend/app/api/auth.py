"""Authentication API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, field_validator
import re
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.database import get_db
from app.core.security import Token
from app.services.auth import AuthService

router = APIRouter()
logger = structlog.get_logger()


class RegisterRequest(BaseModel):
    """User registration request."""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=200)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Username must contain only alphanumeric characters, hyphens, or underscores")
        return v


class LoginRequest(BaseModel):
    """User login request."""

    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """Token refresh request."""

    refresh_token: str


class UserResponse(BaseModel):
    """User response model."""

    id: str
    email: str
    username: str
    full_name: str | None
    role: str
    is_verified: bool
    organization_id: str | None = None

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    """Authentication response with user and tokens."""

    user: UserResponse
    tokens: Token


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """Register a new user."""
    auth_service = AuthService(db)

    # Check if email exists
    existing_user = await auth_service.get_user_by_email(request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Check if username exists
    existing_username = await auth_service.get_user_by_username(request.username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    user = await auth_service.create_user(
        email=request.email,
        username=request.username,
        password=request.password,
        full_name=request.full_name,
    )

    logger.info("User registered", user_id=str(user.id), email=user.email)

    tokens = await auth_service.login(request.email, request.password)

    return AuthResponse(
        user=UserResponse.model_validate(user),
        tokens=tokens,
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """Login with email and password."""
    from sqlalchemy import select
    from app.models.organization import OrganizationMember

    auth_service = AuthService(db)

    tokens = await auth_service.login(request.email, request.password)
    if not tokens:
        logger.warning("Login failed", email=request.email, reason="invalid_credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    user = await auth_service.get_user_by_email(request.email)
    logger.info("Login successful", user_id=str(user.id), email=user.email)

    organization_id = None
    try:
        result = await db.execute(
            select(OrganizationMember.organization_id)
            .where(OrganizationMember.user_id == str(user.id))
            .limit(1)
        )
        org_member = result.scalar_one_or_none()
        if org_member:
            organization_id = org_member
    except Exception as e:
        logger.warning("Organization lookup failed during login", user_id=str(user.id), error=str(e))

    user_response = UserResponse(
        id=str(user.id),
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        is_verified=user.is_verified,
        organization_id=organization_id,
    )

    return AuthResponse(
        user=user_response,
        tokens=tokens,
    )


@router.post("/refresh", response_model=Token)
async def refresh_tokens(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> Token:
    """Refresh access token."""
    auth_service = AuthService(db)

    tokens = await auth_service.refresh_tokens(request.refresh_token)
    if not tokens:
        logger.warning("Token refresh failed", reason="invalid_or_expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    logger.info("Token refreshed successfully")
    return tokens
