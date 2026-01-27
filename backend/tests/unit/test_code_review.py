"""Unit tests for Code Review service."""

import pytest
from datetime import datetime

from app.services.code_review.analyzer import PRAnalyzer, LANGUAGE_EXTENSIONS
from app.services.code_review.smells import CodeSmellDetector
from app.services.code_review.reviewer import ReviewGenerator
from app.services.code_review.models import (
    CodeSmell,
    DiffHunk,
    FileChange,
    HunkLine,
    PRInfo,
    ReviewConfig,
    SmellSeverity,
    SmellType,
)


class TestPRAnalyzer:
    """Tests for PR Analyzer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = PRAnalyzer()
        self.pr_info = PRInfo(
            number=123,
            title="Test PR",
            description="Test description",
            author="testuser",
            base_branch="main",
            head_branch="feature/test",
            repository="owner/repo",
            url="https://github.com/owner/repo/pull/123",
        )

    def test_detect_language_python(self):
        """Test Python language detection."""
        assert self.analyzer._detect_language("app/main.py") == "python"
        assert self.analyzer._detect_language("tests/test_main.py") == "python"

    def test_detect_language_javascript(self):
        """Test JavaScript language detection."""
        assert self.analyzer._detect_language("src/index.js") == "javascript"
        assert self.analyzer._detect_language("components/App.jsx") == "javascript"

    def test_detect_language_typescript(self):
        """Test TypeScript language detection."""
        assert self.analyzer._detect_language("src/index.ts") == "typescript"
        assert self.analyzer._detect_language("components/App.tsx") == "typescript"

    def test_detect_language_unknown(self):
        """Test unknown file extension."""
        assert self.analyzer._detect_language("data.xyz") is None

    def test_parse_files_from_api(self):
        """Test parsing files from API response."""
        files = [
            {
                "filename": "app/main.py",
                "status": "modified",
                "additions": 10,
                "deletions": 5,
                "patch": "@@ -1,5 +1,10 @@\n+new line",
            }
        ]
        result = self.analyzer._parse_files(files)
        assert len(result) == 1
        assert result[0].filename == "app/main.py"
        assert result[0].additions == 10
        assert result[0].deletions == 5
        assert result[0].language == "python"

    def test_parse_diff_files(self):
        """Test parsing files from diff content."""
        diff = """diff --git a/app/main.py b/app/main.py
--- a/app/main.py
+++ b/app/main.py
@@ -1,5 +1,10 @@
+import os
+import sys
-old line
"""
        result = self.analyzer._parse_diff_files(diff)
        assert len(result) == 1
        assert result[0].filename == "app/main.py"
        assert result[0].additions == 2
        assert result[0].deletions == 1

    def test_calculate_complexity(self):
        """Test complexity calculation."""
        files = [
            FileChange(filename="a.py", additions=100, deletions=50),
            FileChange(filename="b.py", additions=200, deletions=100),
        ]
        hunks = {"a.py": [DiffHunk(old_start=1, old_count=5, new_start=1, new_count=10, header="")]}

        complexity = self.analyzer._calculate_complexity(files, hunks, 300, 150)
        assert complexity > 0
        assert complexity <= 10

    def test_calculate_risk_high_risk_files(self):
        """Test risk calculation for sensitive files."""
        files = [
            FileChange(filename="auth/login.py", additions=10, deletions=0),
            FileChange(filename="config/secrets.py", additions=5, deletions=0),
        ]
        risk = self.analyzer._calculate_risk(files, ["python"])
        assert risk > 0  # Should have some risk due to auth/secrets

    def test_analyze_diff(self):
        """Test full diff analysis."""
        diff = """diff --git a/app/main.py b/app/main.py
@@ -1,5 +1,10 @@
+import os
"""
        files = [{"filename": "app/main.py", "additions": 1, "deletions": 0, "status": "modified"}]

        result = self.analyzer.analyze_diff(self.pr_info, diff, files)
        assert result.pr_info.number == 123
        assert len(result.files) == 1
        assert result.total_additions == 1


class TestCodeSmellDetector:
    """Tests for Code Smell Detector."""

    def setup_method(self):
        """Set up test fixtures."""
        self.detector = CodeSmellDetector()

    def _create_file_and_hunk(self, filename: str, language: str, line_content: str):
        """Helper to create file and hunk for testing."""
        file = FileChange(filename=filename, language=language, additions=1, deletions=0)
        hunk = DiffHunk(
            old_start=1,
            old_count=1,
            new_start=1,
            new_count=1,
            header="",
            lines=[HunkLine(content=line_content, type="addition")],
        )
        return file, [hunk]

    def test_detect_hardcoded_secret(self):
        """Test detection of hardcoded secrets."""
        file, hunks = self._create_file_and_hunk(
            "config.py", "python", 'API_KEY = "sk-1234567890abcdef"'
        )
        smells = self.detector.detect_smells(file, hunks)

        secret_smells = [s for s in smells if s.type == SmellType.HARDCODED_SECRET]
        assert len(secret_smells) > 0
        assert secret_smells[0].severity == SmellSeverity.CRITICAL

    def test_detect_mutable_default(self):
        """Test detection of mutable default arguments."""
        file, hunks = self._create_file_and_hunk(
            "utils.py", "python", "def process(items=[]):"
        )
        smells = self.detector.detect_smells(file, hunks)

        mutable_smells = [s for s in smells if s.type == SmellType.MUTABLE_DEFAULT]
        assert len(mutable_smells) > 0

    def test_detect_bare_except(self):
        """Test detection of bare except clauses."""
        file, hunks = self._create_file_and_hunk(
            "handler.py", "python", "except:"
        )
        smells = self.detector.detect_smells(file, hunks)

        bare_except = [s for s in smells if s.type == SmellType.BARE_EXCEPT]
        assert len(bare_except) > 0

    def test_detect_complex_condition(self):
        """Test detection of complex conditions."""
        file, hunks = self._create_file_and_hunk(
            "logic.py", "python", "if a and b and c and d:"
        )
        smells = self.detector.detect_smells(file, hunks)

        complex_smells = [s for s in smells if s.type == SmellType.COMPLEX_CONDITION]
        assert len(complex_smells) > 0

    def test_detect_js_var_usage(self):
        """Test detection of var in JavaScript."""
        file, hunks = self._create_file_and_hunk(
            "app.js", "javascript", "var count = 0;"
        )
        smells = self.detector.detect_smells(file, hunks)
        assert len(smells) > 0

    def test_detect_console_log(self):
        """Test detection of console.log statements."""
        file, hunks = self._create_file_and_hunk(
            "app.js", "javascript", "console.log('debug');"
        )
        smells = self.detector.detect_smells(file, hunks)
        assert len(smells) > 0

    def test_skip_comments(self):
        """Test that comments are skipped."""
        file, hunks = self._create_file_and_hunk(
            "config.py", "python", "# API_KEY = 'secret'"
        )
        smells = self.detector.detect_smells(file, hunks)

        # Should not detect secret in comment
        secret_smells = [s for s in smells if s.type == SmellType.HARDCODED_SECRET]
        assert len(secret_smells) == 0


class TestReviewGenerator:
    """Tests for Review Generator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = ReviewGenerator(config=ReviewConfig())

    def test_smells_to_comments(self):
        """Test converting smells to review comments."""
        smells = [
            CodeSmell(
                type=SmellType.HARDCODED_SECRET,
                severity=SmellSeverity.CRITICAL,
                file="config.py",
                line_start=10,
                message="Hardcoded secret detected",
                suggestion="Use environment variables",
            )
        ]

        comments = self.generator._smells_to_comments(smells)
        assert len(comments) == 1
        assert comments[0].file == "config.py"
        assert comments[0].line == 10
        assert comments[0].priority.value == "critical"

    def test_calculate_quality_perfect(self):
        """Test quality calculation with no issues."""
        from app.services.code_review.models import DiffAnalysis

        analysis = DiffAnalysis(
            pr_info=PRInfo(
                number=1,
                title="Test",
                author="user",
                base_branch="main",
                head_branch="feature",
                repository="owner/repo",
                url="https://example.com",
            ),
            complexity_score=2.0,
            risk_score=1.0,
        )

        quality = self.generator._calculate_quality(analysis, [], [])
        assert quality >= 8.0

    def test_calculate_quality_with_issues(self):
        """Test quality calculation with issues."""
        from app.services.code_review.models import DiffAnalysis

        analysis = DiffAnalysis(
            pr_info=PRInfo(
                number=1,
                title="Test",
                author="user",
                base_branch="main",
                head_branch="feature",
                repository="owner/repo",
                url="https://example.com",
            ),
            complexity_score=8.0,
            risk_score=7.0,
        )

        smells = [
            CodeSmell(
                type=SmellType.HARDCODED_SECRET,
                severity=SmellSeverity.CRITICAL,
                file="a.py",
                line_start=1,
                message="test",
            )
        ]

        quality = self.generator._calculate_quality(analysis, smells, [])
        assert quality < 8.0

    def test_determine_recommendation_approve(self):
        """Test approval recommendation."""
        recommendation = self.generator._determine_recommendation(9.0, [], [])
        assert recommendation == "approve"

    def test_determine_recommendation_changes(self):
        """Test request changes recommendation."""
        smells = [
            CodeSmell(
                type=SmellType.HARDCODED_SECRET,
                severity=SmellSeverity.CRITICAL,
                file="a.py",
                line_start=1,
                message="test",
            )
        ]
        recommendation = self.generator._determine_recommendation(5.0, smells, [])
        assert recommendation == "request_changes"


class TestLanguageExtensions:
    """Test language extension mapping."""

    def test_common_extensions(self):
        """Test common language extensions are mapped."""
        assert LANGUAGE_EXTENSIONS[".py"] == "python"
        assert LANGUAGE_EXTENSIONS[".js"] == "javascript"
        assert LANGUAGE_EXTENSIONS[".ts"] == "typescript"
        assert LANGUAGE_EXTENSIONS[".go"] == "go"
        assert LANGUAGE_EXTENSIONS[".rs"] == "rust"
        assert LANGUAGE_EXTENSIONS[".java"] == "java"
