"""PR Analyzer - Analyzes pull request diffs."""

import re
from pathlib import Path
from typing import Any

from app.services.code_review.models import (
    DiffAnalysis,
    DiffHunk,
    FileChange,
    HunkLine,
    PRInfo,
)


# Language detection based on file extension
LANGUAGE_EXTENSIONS: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".kt": "kotlin",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".cpp": "cpp",
    ".c": "c",
    ".h": "c",
    ".hpp": "cpp",
    ".swift": "swift",
    ".scala": "scala",
    ".sql": "sql",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "zsh",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".json": "json",
    ".xml": "xml",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".sass": "sass",
    ".less": "less",
    ".md": "markdown",
    ".rst": "restructuredtext",
    ".vue": "vue",
    ".svelte": "svelte",
}


class PRAnalyzer:
    """Analyzes pull request diffs for review."""

    def __init__(self):
        """Initialize PR analyzer."""
        self._complexity_weights = {
            "additions": 1.0,
            "deletions": 0.5,
            "files": 2.0,
            "hunks": 0.5,
        }

    def analyze_diff(
        self,
        pr_info: PRInfo,
        diff_content: str,
        files: list[dict[str, Any]] | None = None,
    ) -> DiffAnalysis:
        """Analyze a PR diff.

        Args:
            pr_info: Pull request information
            diff_content: Raw diff content (unified diff format)
            files: Optional list of file change info from API

        Returns:
            DiffAnalysis with parsed diff information
        """
        # Parse files from API response or diff
        file_changes = self._parse_files(files) if files else self._parse_diff_files(diff_content)

        # Parse hunks from diff
        hunks_by_file = self._parse_hunks(diff_content)

        # Detect languages
        languages = self._detect_languages(file_changes)

        # Calculate totals
        total_additions = sum(f.additions for f in file_changes)
        total_deletions = sum(f.deletions for f in file_changes)

        # Calculate complexity score
        complexity_score = self._calculate_complexity(
            file_changes, hunks_by_file, total_additions, total_deletions
        )

        # Calculate risk score
        risk_score = self._calculate_risk(file_changes, languages)

        return DiffAnalysis(
            pr_info=pr_info,
            files=file_changes,
            hunks_by_file=hunks_by_file,
            total_additions=total_additions,
            total_deletions=total_deletions,
            languages=languages,
            complexity_score=complexity_score,
            risk_score=risk_score,
        )

    def _parse_files(self, files: list[dict[str, Any]]) -> list[FileChange]:
        """Parse file changes from API response."""
        changes = []
        for f in files:
            change = FileChange(
                filename=f.get("filename", ""),
                old_path=f.get("previous_filename"),
                new_path=f.get("filename"),
                status=f.get("status", "modified"),
                additions=f.get("additions", 0),
                deletions=f.get("deletions", 0),
                patch=f.get("patch", ""),
                language=self._detect_language(f.get("filename", "")),
            )
            changes.append(change)
        return changes

    def _parse_diff_files(self, diff_content: str) -> list[FileChange]:
        """Parse file changes from unified diff content."""
        changes = []
        current_file = None
        additions = 0
        deletions = 0

        for line in diff_content.split("\n"):
            if line.startswith("diff --git"):
                # Save previous file if exists
                if current_file:
                    changes.append(FileChange(
                        filename=current_file,
                        additions=additions,
                        deletions=deletions,
                        language=self._detect_language(current_file),
                    ))
                # Parse new file
                match = re.search(r"b/(.+)$", line)
                current_file = match.group(1) if match else None
                additions = 0
                deletions = 0
            elif line.startswith("+") and not line.startswith("+++"):
                additions += 1
            elif line.startswith("-") and not line.startswith("---"):
                deletions += 1

        # Don't forget last file
        if current_file:
            changes.append(FileChange(
                filename=current_file,
                additions=additions,
                deletions=deletions,
                language=self._detect_language(current_file),
            ))

        return changes

    def _parse_hunks(self, diff_content: str) -> dict[str, list[DiffHunk]]:
        """Parse diff hunks by file."""
        hunks_by_file: dict[str, list[DiffHunk]] = {}
        current_file = None
        current_hunk = None

        for line in diff_content.split("\n"):
            if line.startswith("diff --git"):
                match = re.search(r"b/(.+)$", line)
                current_file = match.group(1) if match else None
                if current_file and current_file not in hunks_by_file:
                    hunks_by_file[current_file] = []
            elif line.startswith("@@") and current_file:
                # Parse hunk header
                # Format: @@ -old_start,old_count +new_start,new_count @@
                match = re.match(
                    r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)",
                    line
                )
                if match:
                    if current_hunk:
                        hunks_by_file[current_file].append(current_hunk)
                    current_hunk = DiffHunk(
                        old_start=int(match.group(1)),
                        old_count=int(match.group(2) or 1),
                        new_start=int(match.group(3)),
                        new_count=int(match.group(4) or 1),
                        header=match.group(5).strip(),
                        lines=[],
                    )
            elif current_hunk:
                # Parse hunk lines
                if line.startswith("+"):
                    current_hunk.lines.append(HunkLine(
                        content=line[1:],
                        type="addition",
                    ))
                elif line.startswith("-"):
                    current_hunk.lines.append(HunkLine(
                        content=line[1:],
                        type="deletion",
                    ))
                else:
                    current_hunk.lines.append(HunkLine(
                        content=line[1:] if line.startswith(" ") else line,
                        type="context",
                    ))

        # Save last hunk
        if current_file and current_hunk:
            hunks_by_file[current_file].append(current_hunk)

        return hunks_by_file

    def _detect_language(self, filename: str) -> str | None:
        """Detect programming language from filename."""
        ext = Path(filename).suffix.lower()
        return LANGUAGE_EXTENSIONS.get(ext)

    def _detect_languages(self, files: list[FileChange]) -> list[str]:
        """Get unique languages from file changes."""
        languages = set()
        for f in files:
            if f.language:
                languages.add(f.language)
        return sorted(languages)

    def _calculate_complexity(
        self,
        files: list[FileChange],
        hunks: dict[str, list[DiffHunk]],
        additions: int,
        deletions: int,
    ) -> float:
        """Calculate complexity score for the diff.

        Higher score = more complex to review.
        """
        # Base complexity from size
        size_complexity = (
            additions * self._complexity_weights["additions"] +
            deletions * self._complexity_weights["deletions"]
        )

        # File count complexity
        file_complexity = len(files) * self._complexity_weights["files"]

        # Hunk fragmentation complexity
        total_hunks = sum(len(h) for h in hunks.values())
        hunk_complexity = total_hunks * self._complexity_weights["hunks"]

        # Normalize to 0-10 scale
        raw_score = size_complexity + file_complexity + hunk_complexity
        normalized = min(10.0, raw_score / 100)

        return round(normalized, 2)

    def _calculate_risk(
        self,
        files: list[FileChange],
        languages: list[str],
    ) -> float:
        """Calculate risk score based on files changed.

        Higher score = higher risk.
        """
        risk = 0.0

        # High-risk file patterns
        high_risk_patterns = [
            r"auth", r"security", r"crypto", r"password",
            r"secret", r"config", r"\.env", r"migration",
            r"database", r"payment", r"billing",
        ]

        # Check each file
        for f in files:
            filename_lower = f.filename.lower()

            # Check high-risk patterns
            for pattern in high_risk_patterns:
                if re.search(pattern, filename_lower):
                    risk += 2.0
                    break

            # Infrastructure files
            if any(x in filename_lower for x in ["dockerfile", "docker-compose", "kubernetes", "helm"]):
                risk += 1.5

            # CI/CD configuration
            if any(x in filename_lower for x in [".github/workflows", ".gitlab-ci", "jenkinsfile"]):
                risk += 1.0

        # Normalize to 0-10 scale
        normalized = min(10.0, risk)

        return round(normalized, 2)

    def get_changed_functions(self, file: FileChange, hunks: list[DiffHunk]) -> list[str]:
        """Extract function names from changed hunks (for context)."""
        functions = []

        # Patterns for function definitions
        patterns = {
            "python": r"def\s+(\w+)\s*\(",
            "javascript": r"(?:function\s+(\w+)|(\w+)\s*(?:=|:)\s*(?:async\s*)?\([^)]*\)\s*=>)",
            "typescript": r"(?:function\s+(\w+)|(\w+)\s*(?:=|:)\s*(?:async\s*)?\([^)]*\)\s*=>)",
            "java": r"(?:public|private|protected)?\s*\w+\s+(\w+)\s*\(",
            "go": r"func\s+(?:\([^)]*\)\s*)?(\w+)\s*\(",
        }

        pattern = patterns.get(file.language or "", "")
        if not pattern:
            return functions

        for hunk in hunks:
            # Check hunk header (often contains function name)
            if hunk.header:
                match = re.search(pattern, hunk.header)
                if match:
                    func_name = match.group(1) or match.group(2) if match.lastindex and match.lastindex > 1 else match.group(1)
                    if func_name and func_name not in functions:
                        functions.append(func_name)

            # Check added lines
            for line in hunk.lines:
                if line.type == "addition":
                    match = re.search(pattern, line.content)
                    if match:
                        func_name = match.group(1) or (match.group(2) if match.lastindex and match.lastindex > 1 else None)
                        if func_name and func_name not in functions:
                            functions.append(func_name)

        return functions
