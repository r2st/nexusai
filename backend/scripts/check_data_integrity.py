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
    {
        "name": "cost_entries with invalid conversation_id",
        "query": """
            SELECT COUNT(*) FROM cost_entries ce
            LEFT JOIN conversations c ON ce.conversation_id = c.id
            WHERE ce.conversation_id IS NOT NULL AND c.id IS NULL
        """,
    },
    {
        "name": "ai_usage_logs with invalid user_id",
        "query": """
            SELECT COUNT(*) FROM ai_usage_logs aul
            LEFT JOIN users u ON aul.user_id = u.id
            WHERE aul.user_id IS NOT NULL AND u.id IS NULL
        """,
    },
    {
        "name": "personal_access_tokens with invalid user_id",
        "query": """
            SELECT COUNT(*) FROM personal_access_tokens pat
            LEFT JOIN users u ON pat.user_id = u.id
            WHERE u.id IS NULL
        """,
    },
]

CONSISTENCY_CHECKS = [
    {
        "name": "organizations with stale current_member_count",
        "query": """
            SELECT COUNT(*) FROM organizations o
            WHERE o.current_member_count != (
                SELECT COUNT(*) FROM organization_members om
                WHERE om.organization_id = o.id AND om.is_active = true
            )
        """,
    },
    {
        "name": "organizations with stale current_project_count",
        "query": """
            SELECT COUNT(*) FROM organizations o
            WHERE o.current_project_count != (
                SELECT COUNT(*) FROM projects p
                WHERE p.organization_id = o.id
            )
        """,
    },
    {
        "name": "conversations with stale message_count",
        "query": """
            SELECT COUNT(*) FROM conversations c
            WHERE c.message_count != (
                SELECT COUNT(*) FROM messages m
                WHERE m.conversation_id = c.id
            )
        """,
    },
    {
        "name": "documents with stale chunk_count",
        "query": """
            SELECT COUNT(*) FROM documents d
            WHERE d.status = 'completed' AND d.chunk_count != (
                SELECT COUNT(*) FROM document_chunks dc
                WHERE dc.document_id = d.id
            )
        """,
    },
]


async def check_integrity(database_url: str) -> dict:
    engine = create_async_engine(database_url, echo=False)

    results = {"orphans": [], "inconsistencies": [], "clean": [], "errors": []}

    async with engine.begin() as conn:
        print("--- Orphan Record Checks ---")
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

        print("\n--- Consistency Checks ---")
        for check in CONSISTENCY_CHECKS:
            try:
                result = await conn.execute(text(check["query"]))
                count = result.scalar()
                if count and count > 0:
                    results["inconsistencies"].append({"name": check["name"], "count": count})
                    print(f"  STALE: {check['name']} — {count} records")
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
    print(f"  Inconsistencies: {len(results['inconsistencies'])}")
    print(f"  Skipped: {len(results['errors'])}")

    has_issues = results["orphans"] or results["inconsistencies"]

    if results["orphans"]:
        print("\nOrphan records found — run FK migration to prevent future orphans.")
    if results["inconsistencies"]:
        print("\nStale counters found — run a reconciliation to fix cached counts.")

    if has_issues:
        sys.exit(1)

    print("\nAll checks passed.")


if __name__ == "__main__":
    asyncio.run(main())
