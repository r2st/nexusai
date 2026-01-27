#!/usr/bin/env python3
"""
Seed script for development test accounts.

Creates the following test users:
- admin@nexusai.dev / admin123 (admin superuser)
- user@nexusai.dev / user123 (regular user)
- viewer@nexusai.dev / viewer123 (viewer role)

Usage:
    python -m scripts.seed_test_accounts
"""

import asyncio
import os
import sys
from datetime import UTC, datetime
from uuid import uuid4

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.organization import Organization, OrganizationMember, MemberRole


# Test accounts to create
TEST_ACCOUNTS = [
    {
        "email": "admin@nexusai.dev",
        "password": "admin123",
        "username": "admin",
        "full_name": "Admin User",
        "role": UserRole.ADMIN,
        "is_superuser": True,
    },
    {
        "email": "user@nexusai.dev",
        "password": "user123",
        "username": "regularuser",
        "full_name": "Regular User",
        "role": UserRole.USER,
        "is_superuser": False,
    },
    {
        "email": "viewer@nexusai.dev",
        "password": "viewer123",
        "username": "viewer",
        "full_name": "Viewer User",
        "role": UserRole.VIEWER,
        "is_superuser": False,
    },
]


async def seed_test_accounts():
    """Seed the database with test accounts."""
    settings = get_settings()

    # Create engine
    engine = create_async_engine(
        settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
        echo=False,
    )

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        # Create a test organization
        org_tenant_id = str(uuid4())
        org = await _get_or_create_organization(session, org_tenant_id)

        created_users = []
        for account in TEST_ACCOUNTS:
            user = await _get_or_create_user(session, account, org)
            created_users.append(user)
            print(f"✓ User ready: {account['email']} ({account['role'].value})")

        await session.commit()

        print("\n" + "=" * 50)
        print("Test accounts ready!")
        print("=" * 50)
        print("\nCredentials:")
        for account in TEST_ACCOUNTS:
            print(f"  {account['email']} / {account['password']} ({account['role'].value})")
        print("\nOrganization: Test Organization (test-org)")
        print("=" * 50)

    await engine.dispose()


async def _get_or_create_organization(
    session: AsyncSession,
    tenant_id: str,
) -> Organization:
    """Get or create the test organization."""
    # Check if org exists
    result = await session.execute(
        select(Organization).where(Organization.slug == "test-org")
    )
    org = result.scalar_one_or_none()

    if org:
        print(f"✓ Organization exists: {org.name}")
        return org

    # Create new organization
    org = Organization(
        id=str(uuid4()),
        tenant_id=tenant_id,
        name="Test Organization",
        slug="test-org",
        tier="enterprise",
        is_active=True,
        created_at=datetime.now(UTC),
    )
    session.add(org)
    await session.flush()
    print(f"✓ Created organization: {org.name}")
    return org


async def _get_or_create_user(
    session: AsyncSession,
    account: dict,
    org: Organization,
) -> User:
    """Get or create a test user."""
    # Check if user exists
    result = await session.execute(
        select(User).where(User.email == account["email"])
    )
    user = result.scalar_one_or_none()

    if user:
        # Update password in case it changed
        user.hashed_password = get_password_hash(account["password"])
        user.role = account["role"].value
        user.is_superuser = account["is_superuser"]
        user.is_active = True
        user.is_verified = True
        await session.flush()
        return user

    # Create new user
    user = User(
        id=uuid4(),
        email=account["email"],
        username=account["username"],
        hashed_password=get_password_hash(account["password"]),
        full_name=account["full_name"],
        role=account["role"].value,
        is_active=True,
        is_superuser=account["is_superuser"],
        is_verified=True,
        created_at=datetime.now(UTC),
    )
    session.add(user)
    await session.flush()

    # Add user to organization
    member = OrganizationMember(
        id=str(uuid4()),
        tenant_id=org.tenant_id,
        organization_id=org.id,
        user_id=str(user.id),
        role=MemberRole.OWNER.value if account["is_superuser"] else MemberRole.MEMBER.value,
        created_at=datetime.now(UTC),
    )
    session.add(member)
    await session.flush()

    return user


if __name__ == "__main__":
    print("Seeding test accounts...")
    asyncio.run(seed_test_accounts())
