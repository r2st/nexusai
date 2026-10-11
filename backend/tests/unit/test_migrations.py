"""Tests for Alembic migration safety and consistency.

These tests validate migration structure without requiring a database connection.
They check revision chain integrity, downgrade presence, naming conventions,
and common migration anti-patterns.
"""

import importlib
import importlib.util
import re
import sys
from pathlib import Path

import pytest

VERSIONS_DIR = Path(__file__).parent.parent.parent / "alembic" / "versions"


def _load_migration(path: Path):
    """Load a migration module from file path."""
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = mod
    # Don't execute the module — just parse the source for static analysis
    return path.read_text()


def _get_migration_files():
    """Get all migration .py files sorted by name."""
    return sorted(VERSIONS_DIR.glob("*.py"))


def _extract_revision_info(source: str):
    """Extract revision and down_revision from migration source."""
    rev_match = re.search(r"^revision[:\s].*?=\s*['\"](.+?)['\"]", source, re.MULTILINE)
    down_match = re.search(r"^down_revision[:\s].*?=\s*(.+?)$", source, re.MULTILINE)

    revision = rev_match.group(1) if rev_match else None

    down_raw = down_match.group(1).strip() if down_match else None
    if down_raw and down_raw != "None":
        down_revision = re.search(r"['\"](.+?)['\"]", down_raw)
        down_revision = down_revision.group(1) if down_revision else None
    else:
        down_revision = None

    return revision, down_revision


class TestRevisionChain:
    """Tests for Alembic revision chain integrity."""

    def test_all_migrations_have_revisions(self):
        """Every migration must declare a revision ID."""
        for path in _get_migration_files():
            source = path.read_text()
            revision, _ = _extract_revision_info(source)
            assert revision is not None, f"{path.name} missing revision ID"

    def test_single_head(self):
        """Revision chain must have exactly one head (no branches)."""
        revisions = {}
        for path in _get_migration_files():
            source = path.read_text()
            rev, down_rev = _extract_revision_info(source)
            if rev:
                revisions[rev] = down_rev

        children: dict[str | None, list[str]] = {}
        for rev, parent in revisions.items():
            children.setdefault(parent, []).append(rev)

        heads = [r for r in revisions if r not in children]
        assert len(heads) == 1, f"Expected 1 head, found {len(heads)}: {heads}"

    def test_no_orphaned_revisions(self):
        """Every non-initial revision must reference a valid parent."""
        revisions = set()
        parents = {}
        for path in _get_migration_files():
            source = path.read_text()
            rev, down_rev = _extract_revision_info(source)
            if rev:
                revisions.add(rev)
                parents[rev] = down_rev

        for rev, parent in parents.items():
            if parent is not None:
                assert parent in revisions, (
                    f"Revision {rev} references non-existent parent {parent}"
                )

    def test_exactly_one_initial_migration(self):
        """Exactly one migration should have down_revision = None."""
        initials = []
        for path in _get_migration_files():
            source = path.read_text()
            rev, down_rev = _extract_revision_info(source)
            if rev and down_rev is None:
                initials.append(rev)

        assert len(initials) == 1, (
            f"Expected 1 initial migration, found {len(initials)}: {initials}"
        )


class TestMigrationSafety:
    """Tests for migration safety patterns."""

    def test_all_migrations_have_downgrade(self):
        """Every migration must have a downgrade function."""
        for path in _get_migration_files():
            source = path.read_text()
            assert "def downgrade()" in source, (
                f"{path.name} missing downgrade() function"
            )

    def test_no_bare_drop_column_in_upgrade(self):
        """DROP COLUMN in upgrade should preserve data (check for backup pattern)."""
        for path in _get_migration_files():
            source = path.read_text()
            upgrade_section = source.split("def upgrade()")[1].split("def downgrade()")[0] if "def upgrade()" in source else ""

            if "drop_column" in upgrade_section:
                assert (
                    "message_metadata" in upgrade_section
                    or "backup" in upgrade_section.lower()
                    or "_migrated_" in upgrade_section
                    or "JSONB" in upgrade_section
                ), f"{path.name} drops columns in upgrade without data preservation"

    def test_no_python_only_defaults(self):
        """Columns with defaults should use server_default, not default."""
        for path in _get_migration_files():
            source = path.read_text()
            upgrade_section = source.split("def upgrade()")[1].split("def downgrade()")[0] if "def upgrade()" in source else ""

            lines = upgrade_section.split("\n")
            for i, line in enumerate(lines):
                if "sa.Column(" in line and "default=" in line and "server_default" not in line:
                    col_match = re.search(r'sa\.Column\(["\'](\w+)["\']', line)
                    col_name = col_match.group(1) if col_match else "unknown"
                    assert False, (
                        f"{path.name}:{i+1} column '{col_name}' uses default= "
                        f"instead of server_default= (DB-level default won't be set)"
                    )

    def test_no_string_type_for_numeric_columns(self):
        """Columns storing numbers or booleans should not use String type."""
        suspect_patterns = [
            (r"Column\(['\"]use_count['\"].*String", "use_count should be Integer"),
            (r"Column\(['\"]stage_index['\"].*String", "stage_index should be Integer"),
            (r"Column\(['\"]finished_tasks['\"].*String", "finished_tasks should be Integer"),
            (r"Column\(['\"]total_tasks['\"].*String", "total_tasks should be Integer"),
            (r"Column\(['\"]is_manual['\"].*String", "is_manual should be Boolean"),
            (r"Column\(['\"]skip_on_fail['\"].*String", "skip_on_fail should be Boolean"),
        ]
        for path in _get_migration_files():
            source = path.read_text()
            for pattern, msg in suspect_patterns:
                assert not re.search(pattern, source), f"{path.name}: {msg}"
