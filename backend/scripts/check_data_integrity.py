"""Data integrity checker for orphan records and constraint violations.

Run: python -m scripts.check_data_integrity
Requires DATABASE_URL env var pointing to the target database.
"""

import asyncio
import os
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


ORPHAN_CHECKS = [
    {
        "name": "cost_entries with invalid tenant_id",
        "query": """
            SELECT COUNT(*) FROM cost_entries ce
            LEFT JOIN organizations o ON ce.tenant_id = o.tenant_id
            WHERE o.tenant_id IS NULL
        """,
    },
    {
        "name": "cost_entries with invalid user_id",
        "query": """
            SELECT COUNT(*) FROM cost_entries ce
            LEFT JOIN users u ON ce.user_id = u.id
            WHERE ce.user_id IS NOT NULL AND u.id IS NULL
        """,
    },
    {
        "name": "cost_budgets with invalid tenant_id",
        "query": """
            SELECT COUNT(*) FROM cost_budgets cb
            LEFT JOIN organizations o ON cb.tenant_id = o.tenant_id
            WHERE o.tenant_id IS NULL
        """,
    },
    {
        "name": "cost_alerts with invalid budget_id",
        "query": """
            SELECT COUNT(*) FROM cost_alerts ca
            LEFT JOIN cost_budgets cb ON ca.budget_id = cb.id
            WHERE cb.id IS NULL
        """,
    },
    {
        "name": "hallucination_logs with invalid tenant_id",
        "query": """
            SELECT COUNT(*) FROM hallucination_logs hl
            LEFT JOIN organizations o ON hl.tenant_id = o.tenant_id
            WHERE o.tenant_id IS NULL
        """,
    },
    {
        "name": "hallucination_metrics with invalid tenant_id",
        "query": """
            SELECT COUNT(*) FROM hallucination_metrics hm
            LEFT JOIN organizations o ON hm.tenant_id = o.tenant_id
            WHERE o.tenant_id IS NULL
        """,
    },
    {
        "name": "conversations with invalid user_id",
        "query": """
            SELECT COUNT(*) FROM conversations c
            LEFT JOIN users u ON c.user_id = u.id
            WHERE u.id IS NULL
        """,
    },
    {
        "name": "documents with invalid user_id",
        "query": """
            SELECT COUNT(*) FROM documents d
            LEFT JOIN users u ON d.user_id = u.id
            WHERE u.id IS NULL
        """,
    },
    {
        "name": "organization_members with invalid user_id",
        "query": """
            SELECT COUNT(*) FROM organization_members om
            LEFT JOIN users u ON om.user_id = u.id
            WHERE u.id IS NULL
        """,
    },
    {
        "name": "project_members with invalid user_id",
        "query": """
            SELECT COUNT(*) FROM project_members pm
            LEFT JOIN users u ON pm.user_id = u.id
            WHERE u.id IS NULL
        """,
    },
    {
        "name": "messages with invalid conversation_id",
        "query": """
            SELECT COUNT(*) FROM messages m
            LEFT JOIN conversations c ON m.conversation_id = c.id
            WHERE c.id IS NULL
        """,
    },
    {
        "name": "document_chunks with invalid document_id",
        "query": """
            SELECT COUNT(*) FROM document_chunks dc
            LEFT JOIN documents d ON dc.document_id = d.id
            WHERE d.id IS NULL
        """,
    },
]


async def check_integrity(database_url: str) -> dict:
    engine = create_async_engine(database_url, echo=False)

    results = {"orphans": [], "clean": [], "errors": []}

    async with engine.begin() as conn:
        for check in ORPHAN_CHECKS:
            try:
                result = await conn.execute(text(check["query"]))
                count = result.scalar()
                if count and count > 0:
                    results["orphans"].append({"name": check["name"], "count": count})
                    print(f"  ORPHAN: {check['name']} — {count} records")
                else:
                    results["clean"].append(check["name"])
                    print(f"  OK: {check['name']}")
            except Exception as e:
                err_msg = str(e).split("\n")[0]
                results["errors"].append({"name": check["name"], "error": err_msg})
                print(f"  SKIP: {check['name']} — {err_msg}")

    await engine.dispose()
    return results


async def main():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable is required")
        sys.exit(1)

    print("=== Data Integrity Check ===\n")
    results = await check_integrity(database_url)

    print(f"\nSummary:")
    print(f"  Clean: {len(results['clean'])}")
    print(f"  Orphans: {len(results['orphans'])}")
    print(f"  Skipped: {len(results['errors'])}")

    if results["orphans"]:
        print("\nOrphan records found — run FK migration to prevent future orphans.")
        sys.exit(1)

    print("\nAll checks passed.")


if __name__ == "__main__":
    asyncio.run(main())
