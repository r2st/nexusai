"""
Pytest configuration and fixtures for NexusAI backend tests.
"""

import asyncio
import os
import warnings
from collections.abc import AsyncGenerator, Generator
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Set test environment BEFORE any app imports
os.environ["ENVIRONMENT"] = "test"
os.environ["DEBUG"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only-32chars"

# Detect if running inside Docker container
def _is_running_in_docker() -> bool:
    """Check if we're running inside a Docker container."""
    return os.path.exists("/.dockerenv") or os.environ.get("DOCKER_CONTAINER") == "true"

# Get test database URL - use TEST_DATABASE_URL if provided, otherwise build default
# Inside Docker: connect to postgres:5432 (Docker network)
# Outside Docker: connect to localhost:5434 (host port mapping)
if _is_running_in_docker():
    _default_db_url = "postgresql+asyncpg://postgres:postgres@postgres:5432/nexusai_test"
    _default_redis_url = "redis://redis:6379/1"
else:
    _default_db_url = "postgresql+asyncpg://postgres:postgres@localhost:5434/nexusai_test"
    _default_redis_url = "redis://localhost:6379/1"

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", _default_db_url)
TEST_REDIS_URL = os.environ.get("TEST_REDIS_URL", _default_redis_url)

# Set DATABASE_URL and REDIS_URL BEFORE importing app.core.config
# because the import triggers module-level settings = get_settings() validation
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["REDIS_URL"] = TEST_REDIS_URL

# Also set individual database components in case DATABASE_URL is built from them
# Parse the URL to set components (for Settings that builds URL from components)
# Format: postgresql+asyncpg://user:password@host:port/database
import re
db_match = re.match(r'postgresql\+asyncpg://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', TEST_DATABASE_URL)
if db_match:
    os.environ["DATABASE_USER"] = db_match.group(1)
    os.environ["DATABASE_PASSWORD"] = db_match.group(2)
    os.environ["DATABASE_HOST"] = db_match.group(3)
    os.environ["DATABASE_PORT"] = db_match.group(4)
    os.environ["DATABASE_NAME"] = db_match.group(5)

# Parse Redis URL too
redis_match = re.match(r'redis://(?::([^@]+)@)?([^:]+):(\d+)/(\d+)', TEST_REDIS_URL)
if redis_match:
    os.environ["REDIS_PASSWORD"] = redis_match.group(1) or ""
    os.environ["REDIS_HOST"] = redis_match.group(2)
    os.environ["REDIS_PORT"] = redis_match.group(3)
    os.environ["REDIS_DB"] = redis_match.group(4)

from app.core.config import get_settings
get_settings.cache_clear()

from app.main import app
from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.core.multitenancy import get_current_tenant_id
from app.models.user import User
from app.models.organization import Organization

# Global test tenant ID - will be set by test_organization fixture
_test_tenant_id: str | None = None


# =============================================================================
# Database Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def event_loop():
    """Create an instance of the default event loop for each test function."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create a test database engine for each test function."""
    db_url = TEST_DATABASE_URL
    print(f"\n[TEST] Creating test engine with URL: {db_url}")

    engine = create_async_engine(
        db_url,
        echo=False,
        pool_pre_ping=True,
    )

    # Verify we're connected to the right database
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT current_database()"))
            current_db = result.scalar()
            print(f"[TEST] Connected to database: {current_db}")
    except Exception as exc:
        await engine.dispose()
        pytest.skip(f"Test database unavailable at {db_url}: {exc}")

    # Step 1: Drop and recreate public schema in its own transaction
    async with engine.begin() as conn:
        print("[TEST] Dropping and recreating public schema...")
        await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
        # Enable required extensions
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\""))

    # Step 2: Create all tables
    async with engine.begin() as conn:
        print("[TEST] Creating tables...")
        await conn.run_sync(Base.metadata.create_all)
        print("[TEST] Tables created successfully")

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a new database session for a test."""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with database session override."""
    global _test_tenant_id

    async def override_get_db():
        yield db_session

    def override_get_tenant_id() -> str | None:
        return _test_tenant_id

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_tenant_id] = override_get_tenant_id

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# =============================================================================
# User Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    from app.core.security import get_password_hash
    user = User(
        id=uuid4(),
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash("test_password"),
        full_name="Test User",
        is_active=True,
        is_superuser=False,
        created_at=datetime.utcnow(),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create an admin user."""
    from app.core.security import get_password_hash
    user = User(
        id=uuid4(),
        email="admin@example.com",
        username="adminuser",
        hashed_password=get_password_hash("admin_password"),
        full_name="Admin User",
        is_active=True,
        is_superuser=True,
        created_at=datetime.utcnow(),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def test_user_token(test_user: User) -> str:
    """Generate a JWT token for the test user."""
    return create_access_token(
        data={"sub": str(test_user.id), "email": test_user.email}
    )


@pytest.fixture
def admin_user_token(admin_user: User) -> str:
    """Generate a JWT token for the admin user."""
    return create_access_token(
        data={"sub": str(admin_user.id), "email": admin_user.email}
    )


@pytest.fixture
def auth_headers(test_user_token: str) -> dict[str, str]:
    """Return authorization headers for a regular user."""
    return {"Authorization": f"Bearer {test_user_token}"}


@pytest.fixture
def admin_auth_headers(admin_user_token: str) -> dict[str, str]:
    """Return authorization headers for an admin user."""
    return {"Authorization": f"Bearer {admin_user_token}"}


# =============================================================================
# Organization Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def test_organization(db_session: AsyncSession, test_user: User) -> Organization:
    """Create a test organization."""
    global _test_tenant_id
    from app.models.organization import OrganizationMember, MemberRole

    tenant_id = str(uuid4())
    org = Organization(
        id=str(uuid4()),
        tenant_id=tenant_id,
        name="Test Organization",
        slug="test-org",
        created_at=datetime.utcnow(),
    )
    db_session.add(org)
    await db_session.flush()

    # Add test user as owner member
    member = OrganizationMember(
        id=str(uuid4()),
        tenant_id=org.tenant_id,
        organization_id=org.id,
        user_id=str(test_user.id),
        role=MemberRole.OWNER.value,
    )
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(org)

    # Set the global tenant_id for dependency override
    _test_tenant_id = tenant_id

    return org


# =============================================================================
# Mock Data Fixtures
# =============================================================================

@pytest.fixture
def mock_chat_message() -> dict[str, Any]:
    """Return a mock chat message payload."""
    return {
        "messages": [
            {"role": "user", "content": "Hello, how are you?"}
        ],
        "model": "gpt-4",
        "stream": False,
    }


@pytest.fixture
def mock_document_content() -> bytes:
    """Return mock document content."""
    return b"This is a test document content for NexusAI testing."


@pytest.fixture
def mock_user_registration() -> dict[str, str]:
    """Return mock user registration data."""
    unique_id = uuid4().hex[:8]
    return {
        "email": f"newuser_{unique_id}@example.com",
        "username": f"newuser_{unique_id}",
        "password": "SecurePassword123!",
        "full_name": "New Test User",
    }


# =============================================================================
# Utility Functions
# =============================================================================

def assert_datetime_recent(dt: datetime, seconds: int = 60) -> None:
    """Assert that a datetime is within the last N seconds."""
    assert dt is not None
    assert datetime.utcnow() - dt < timedelta(seconds=seconds)
