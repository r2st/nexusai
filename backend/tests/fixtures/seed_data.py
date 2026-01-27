"""
Seed data for testing and development.
"""

from datetime import datetime, timedelta
from uuid import uuid4
from typing import Any

# =============================================================================
# User Seed Data
# =============================================================================

SEED_USERS = [
    {
        "id": "11111111-1111-1111-1111-111111111111",
        "email": "alice@example.com",
        "full_name": "Alice Johnson",
        "is_active": True,
        "is_superuser": False,
    },
    {
        "id": "22222222-2222-2222-2222-222222222222",
        "email": "bob@example.com",
        "full_name": "Bob Smith",
        "is_active": True,
        "is_superuser": False,
    },
    {
        "id": "33333333-3333-3333-3333-333333333333",
        "email": "admin@nexusai.com",
        "full_name": "System Admin",
        "is_active": True,
        "is_superuser": True,
    },
]

# =============================================================================
# Organization Seed Data
# =============================================================================

SEED_ORGANIZATIONS = [
    {
        "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "name": "Acme Corporation",
        "slug": "acme-corp",
        "owner_id": "11111111-1111-1111-1111-111111111111",
    },
    {
        "id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        "name": "Tech Startup Inc",
        "slug": "tech-startup",
        "owner_id": "22222222-2222-2222-2222-222222222222",
    },
]

# =============================================================================
# Project Seed Data
# =============================================================================

SEED_PROJECTS = [
    {
        "id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
        "name": "AI Assistant",
        "description": "Customer support AI chatbot",
        "organization_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    },
    {
        "id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
        "name": "Code Reviewer",
        "description": "Automated code review agent",
        "organization_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    },
]

# =============================================================================
# Conversation Seed Data
# =============================================================================

SEED_CONVERSATIONS = [
    {
        "id": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
        "title": "Help with Python code",
        "user_id": "11111111-1111-1111-1111-111111111111",
        "project_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
        "messages": [
            {"role": "user", "content": "How do I read a CSV file in Python?"},
            {"role": "assistant", "content": "You can use pandas to read CSV files:\n\n```python\nimport pandas as pd\ndf = pd.read_csv('file.csv')\n```"},
            {"role": "user", "content": "What if I want to filter rows?"},
            {"role": "assistant", "content": "You can filter using boolean indexing:\n\n```python\nfiltered_df = df[df['column'] > value]\n```"},
        ],
    },
    {
        "id": "ffffffff-ffff-ffff-ffff-ffffffffffff",
        "title": "Database design question",
        "user_id": "22222222-2222-2222-2222-222222222222",
        "project_id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
        "messages": [
            {"role": "user", "content": "Should I use PostgreSQL or MongoDB for my app?"},
            {"role": "assistant", "content": "It depends on your use case:\n\n- **PostgreSQL**: Best for structured data, complex queries, ACID compliance\n- **MongoDB**: Best for flexible schemas, document storage, horizontal scaling"},
        ],
    },
]

# =============================================================================
# Agent Seed Data
# =============================================================================

SEED_AGENTS = [
    {
        "id": "agent-001",
        "name": "Code Assistant",
        "description": "Helps with coding tasks, reviews code, and suggests improvements",
        "type": "code",
        "model": "gpt-4",
        "system_prompt": "You are an expert software engineer...",
        "tools": ["code_interpreter", "web_search"],
        "is_public": True,
    },
    {
        "id": "agent-002",
        "name": "DORA Metrics Analyst",
        "description": "Analyzes DevOps performance using DORA metrics",
        "type": "devops",
        "model": "gpt-4",
        "system_prompt": "You are a DevOps expert specializing in DORA metrics...",
        "tools": ["devlake_query", "chart_generator"],
        "is_public": True,
    },
    {
        "id": "agent-003",
        "name": "Document Analyzer",
        "description": "Extracts insights from uploaded documents",
        "type": "analysis",
        "model": "claude-3-sonnet",
        "system_prompt": "You are a document analysis expert...",
        "tools": ["document_search", "summarizer"],
        "is_public": False,
    },
]

# =============================================================================
# Document Seed Data
# =============================================================================

SEED_DOCUMENTS = [
    {
        "id": "doc-001",
        "filename": "quarterly_report.pdf",
        "content_type": "application/pdf",
        "size_bytes": 245000,
        "user_id": "11111111-1111-1111-1111-111111111111",
        "extracted_text": "Q4 2024 Financial Report\n\nRevenue increased by 25%...",
    },
    {
        "id": "doc-002",
        "filename": "api_documentation.md",
        "content_type": "text/markdown",
        "size_bytes": 12500,
        "user_id": "22222222-2222-2222-2222-222222222222",
        "extracted_text": "# API Documentation\n\n## Authentication\n\nAll API requests require...",
    },
]

# =============================================================================
# API Key Seed Data
# =============================================================================

SEED_API_KEYS = [
    {
        "id": "key-001",
        "name": "Production API Key",
        "key_prefix": "nxai_prod_",
        "user_id": "11111111-1111-1111-1111-111111111111",
        "scopes": ["read", "write"],
        "expires_at": datetime.utcnow() + timedelta(days=365),
    },
    {
        "id": "key-002",
        "name": "Development Key",
        "key_prefix": "nxai_dev_",
        "user_id": "22222222-2222-2222-2222-222222222222",
        "scopes": ["read"],
        "expires_at": datetime.utcnow() + timedelta(days=30),
    },
]


# =============================================================================
# Seed Data Loader
# =============================================================================

async def load_seed_data(db_session) -> dict[str, int]:
    """
    Load all seed data into the database.
    Returns counts of inserted records.
    """
    from app.models.user import User
    from app.models.organization import Organization

    counts = {}

    # Load users
    for user_data in SEED_USERS:
        user = User(
            id=user_data["id"],
            email=user_data["email"],
            full_name=user_data["full_name"],
            hashed_password="$2b$12$seed_hashed_password",
            is_active=user_data["is_active"],
            is_superuser=user_data["is_superuser"],
        )
        db_session.add(user)
    counts["users"] = len(SEED_USERS)

    # Load organizations
    for org_data in SEED_ORGANIZATIONS:
        org = Organization(
            id=org_data["id"],
            name=org_data["name"],
            slug=org_data["slug"],
            owner_id=org_data["owner_id"],
        )
        db_session.add(org)
    counts["organizations"] = len(SEED_ORGANIZATIONS)

    await db_session.commit()

    return counts


def get_test_data_summary() -> dict[str, Any]:
    """Return a summary of available test data."""
    return {
        "users": len(SEED_USERS),
        "organizations": len(SEED_ORGANIZATIONS),
        "projects": len(SEED_PROJECTS),
        "conversations": len(SEED_CONVERSATIONS),
        "agents": len(SEED_AGENTS),
        "documents": len(SEED_DOCUMENTS),
        "api_keys": len(SEED_API_KEYS),
    }
