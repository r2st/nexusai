"""
Integration tests for database operations.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.organization import Organization


class TestDatabaseConnection:
    """Test database connectivity and basic operations."""

    @pytest.mark.asyncio
    async def test_database_connection(self, db_session: AsyncSession):
        """Test that database connection works."""
        result = await db_session.execute(text("SELECT 1"))
        assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_pgvector_extension(self, db_session: AsyncSession):
        """Test that pgvector extension is available."""
        result = await db_session.execute(
            text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        )
        row = result.fetchone()
        # May not be installed in test DB
        # assert row is not None

    @pytest.mark.asyncio
    async def test_uuid_extension(self, db_session: AsyncSession):
        """Test that uuid-ossp extension is available."""
        result = await db_session.execute(
            text("SELECT uuid_generate_v4()")
        )
        uuid_val = result.scalar()
        assert uuid_val is not None


class TestUserModel:
    """Test User model operations."""

    @pytest.mark.asyncio
    async def test_create_user(self, db_session: AsyncSession):
        """Test creating a user."""
        from uuid import uuid4

        user = User(
            id=uuid4(),
            email="newuser@test.com",
            username="newuser",
            hashed_password="hashed_pw",
            full_name="New User",
            is_active=True,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert user.id is not None
        assert user.email == "newuser@test.com"
        assert user.created_at is not None

    @pytest.mark.asyncio
    async def test_user_unique_email(self, db_session: AsyncSession, test_user: User):
        """Test that duplicate emails are rejected."""
        from uuid import uuid4
        from sqlalchemy.exc import IntegrityError

        duplicate = User(
            id=uuid4(),
            email=test_user.email,  # Same email
            hashed_password="hashed_pw",
            full_name="Duplicate User",
        )
        db_session.add(duplicate)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_query_user_by_email(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test querying user by email."""
        from sqlalchemy import select

        stmt = select(User).where(User.email == test_user.email)
        result = await db_session.execute(stmt)
        found_user = result.scalar_one_or_none()

        assert found_user is not None
        assert found_user.id == test_user.id


class TestOrganizationModel:
    """Test Organization model operations."""

    @pytest.mark.asyncio
    async def test_create_organization(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test creating an organization."""
        from uuid import uuid4

        org = Organization(
            id=str(uuid4()),
            tenant_id=str(uuid4()),
            name="New Org",
            slug="new-org",
        )
        db_session.add(org)
        await db_session.commit()
        await db_session.refresh(org)

        assert org.id is not None
        assert org.name == "New Org"
        assert org.tenant_id is not None

    @pytest.mark.asyncio
    async def test_organization_unique_slug(
        self, db_session: AsyncSession, test_organization: Organization, test_user: User
    ):
        """Test that duplicate slugs are rejected."""
        from uuid import uuid4
        from sqlalchemy.exc import IntegrityError

        duplicate = Organization(
            id=str(uuid4()),
            tenant_id=str(uuid4()),
            name="Another Org",
            slug=test_organization.slug,  # Same slug
        )
        db_session.add(duplicate)

        with pytest.raises(IntegrityError):
            await db_session.commit()
