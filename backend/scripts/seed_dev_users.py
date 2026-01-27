#!/usr/bin/env python3
"""
Seed script for development users.

This script creates default users for testing in development mode.
Run with: python -m scripts.seed_dev_users

Default users created:
- admin@nexusai.dev (password: admin123) - Admin user
- user@nexusai.dev (password: user123) - Regular user
- viewer@nexusai.dev (password: viewer123) - Viewer user
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.core.database import async_session_factory, init_db
from app.core.security import get_password_hash
from app.core.config import settings
from app.models.user import User, UserRole


# Default development users
DEV_USERS = [
    {
        "email": "admin@nexusai.dev",
        "username": "admin",
        "password": "admin123",
        "full_name": "Admin User",
        "role": UserRole.ADMIN.value,
        "is_verified": True,
        "is_active": True,
        "is_superuser": True,
    },
    {
        "email": "user@nexusai.dev",
        "username": "devuser",
        "password": "user123",
        "full_name": "Dev User",
        "role": UserRole.USER.value,
        "is_verified": True,
        "is_active": True,
        "is_superuser": False,
    },
    {
        "email": "viewer@nexusai.dev",
        "username": "viewer",
        "password": "viewer123",
        "full_name": "Viewer User",
        "role": UserRole.VIEWER.value,
        "is_verified": True,
        "is_active": True,
        "is_superuser": False,
    },
    {
        "email": "unverified@nexusai.dev",
        "username": "unverified",
        "password": "test123",
        "full_name": "Unverified User",
        "role": UserRole.USER.value,
        "is_verified": False,
        "is_active": True,
        "is_superuser": False,
    },
    {
        "email": "inactive@nexusai.dev",
        "username": "inactive",
        "password": "test123",
        "full_name": "Inactive User",
        "role": UserRole.USER.value,
        "is_verified": True,
        "is_active": False,
        "is_superuser": False,
    },
]


async def seed_users() -> None:
    """Create development users if they don't exist."""
    # Initialize database
    await init_db()

    async with async_session_factory() as session:
        created_count = 0
        skipped_count = 0

        for user_data in DEV_USERS:
            # Check if user already exists
            result = await session.execute(
                select(User).where(User.email == user_data["email"])
            )
            existing_user = result.scalar_one_or_none()

            if existing_user:
                print(f"⏭️  User already exists: {user_data['email']}")
                skipped_count += 1
                continue

            # Create new user
            password = user_data.pop("password")
            user = User(
                **user_data,
                hashed_password=get_password_hash(password),
            )
            session.add(user)
            print(f"✅ Created user: {user_data['email']} (password: {password})")
            created_count += 1

        await session.commit()

        print(f"\n{'=' * 50}")
        print(f"Development users seeding complete!")
        print(f"Created: {created_count} | Skipped: {skipped_count}")
        print(f"{'=' * 50}")


async def delete_dev_users() -> None:
    """Delete all development users."""
    async with async_session_factory() as session:
        deleted_count = 0

        for user_data in DEV_USERS:
            result = await session.execute(
                select(User).where(User.email == user_data["email"])
            )
            user = result.scalar_one_or_none()

            if user:
                await session.delete(user)
                print(f"🗑️  Deleted user: {user_data['email']}")
                deleted_count += 1

        await session.commit()
        print(f"\nDeleted {deleted_count} development users.")


def print_usage():
    """Print usage information."""
    print("""
Development Users Seed Script
==============================

Usage:
    python -m scripts.seed_dev_users [command]

Commands:
    seed    - Create development users (default)
    delete  - Delete development users
    reset   - Delete and recreate development users

Default Users:
    Email                      Password     Role
    ─────────────────────────────────────────────
    admin@nexusai.dev         admin123     admin (superuser)
    user@nexusai.dev          user123      user
    viewer@nexusai.dev        viewer123    viewer
    unverified@nexusai.dev    test123      user (unverified)
    inactive@nexusai.dev      test123      user (inactive)
""")


async def main():
    """Main entry point."""
    # Check if running in development
    if not settings.is_development:
        print("⚠️  WARNING: This script should only be run in development mode!")
        print(f"Current environment: {settings.ENVIRONMENT}")
        response = input("Continue anyway? (yes/no): ")
        if response.lower() != "yes":
            print("Aborted.")
            return

    command = sys.argv[1] if len(sys.argv) > 1 else "seed"

    if command == "seed":
        await seed_users()
    elif command == "delete":
        await delete_dev_users()
    elif command == "reset":
        await delete_dev_users()
        await seed_users()
    elif command in ("help", "-h", "--help"):
        print_usage()
    else:
        print(f"Unknown command: {command}")
        print_usage()


if __name__ == "__main__":
    asyncio.run(main())
