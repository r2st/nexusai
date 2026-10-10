"""Code Smell Detector - Detects common code smells and anti-patterns."""

import re

from app.services.code_review.models import (
    CodeSmell,
    DiffHunk,
    FileChange,
    SmellSeverity,
    SmellType,
)


class CodeSmellDetector:
    """Detects code smells and anti-patterns in code changes."""

    _SECRET_PATTERNS_CONTENT: list[tuple[re.Pattern, str]] = [
        (re.compile(r'(password|passwd|pwd)\s*=\s*["\'][^"\']+["\']', re.IGNORECASE), "Hardcoded password"),
        (re.compile(r'(secret|api_key|apikey|api-key)\s*=\s*["\'][^"\']+["\']', re.IGNORECASE), "Hardcoded API key/secret"),
        (re.compile(r'(token|auth_token)\s*=\s*["\'][^"\']+["\']', re.IGNORECASE), "Hardcoded token"),
        (re.compile(r'["\']sk-[a-zA-Z0-9]{20,}["\']', re.IGNORECASE), "Hardcoded OpenAI API key"),
        (re.compile(r'["\']ghp_[a-zA-Z0-9]{36,}["\']', re.IGNORECASE), "Hardcoded GitHub token"),
    ]
    _FUNC_PATTERN_PY: re.Pattern = re.compile(r'^\s*def\s+\w+\s*\(')
    _FUNC_PATTERN_JS: re.Pattern = re.compile(r'^\s*(async\s+)?function\s+\w+|^\s*\w+\s*[=:]\s*(async\s+)?\(')
    _TODO_PATTERN: re.Pattern = re.compile(r'\b(TODO|FIXME|HACK|XXX)\b', re.IGNORECASE)
    _MUTABLE_DEFAULT_PY: re.Pattern = re.compile(r'def\s+\w+\([^)]*=\s*(\[\]|\{\}|\[\s*\]|\{\s*\})')
    _BARE_EXCEPT_PY: re.Pattern = re.compile(r'except\s*:')
    _STAR_IMPORT_PY: re.Pattern = re.compile(r'from\s+\S+\s+import\s+\*')
    _EVAL_PY: re.Pattern = re.compile(r'\beval\s*\(')
    _VAR_JS: re.Pattern = re.compile(r'\bvar\s+\w+')
    _CONSOLE_JS: re.Pattern = re.compile(r'\bconsole\.(log|debug|info)\s*\(')
    _ANY_TS: re.Pattern = re.compile(r':\s*any\b')
    _BOOLEAN_OPS: re.Pattern = re.compile(r'(?:and|or|&&|\|\|)')
    _MAGIC_NUMBER: re.Pattern = re.compile(r"(?<!['\"\w])(\d+(?:\.\d+)?)(?!['\"\w])")
    _SECRET_PATTERNS_HUNK: list[tuple[re.Pattern, str]] = [
        (re.compile(r"(?i)(api[_-]?key|apikey)\s*[=:]\s*['\"][^'\"]{10,}['\"]"), "API key"),
        (re.compile(r"(?i)(secret|password|passwd|pwd)\s*[=:]\s*['\"][^'\"]{6,}['\"]"), "password/secret"),
        (re.compile(r"(?i)(token|auth[_-]?token)\s*[=:]\s*['\"][^'\"]{10,}['\"]"), "token"),
        (re.compile(r"(?i)(private[_-]?key)\s*[=:]\s*['\"][^'\"]{20,}['\"]"), "private key"),
        (re.compile(r"sk-[a-zA-Z0-9]{20,}"), "OpenAI API key"),
        (re.compile(r"sk-ant-[a-zA-Z0-9]{20,}"), "Anthropic API key"),
        (re.compile(r"ghp_[a-zA-Z0-9]{36,}"), "GitHub PAT"),
        (re.compile(r"gho_[a-zA-Z0-9]{36,}"), "GitHub OAuth token"),
        (re.compile(r"xox[baprs]-[a-zA-Z0-9-]{10,}"), "Slack token"),
    ]
    _TODO_FIXME_HUNK: re.Pattern = re.compile(r"\b(TODO|FIXME|HACK|XXX|BUG)\b", re.IGNORECASE)
    _MUTABLE_DEFAULT_HUNK: re.Pattern = re.compile(r"def\s+\w+\s*\([^)]*=\s*(\[\]|\{\}|\bset\(\)|\bdict\(\)|\blist\(\))")
    _BARE_EXCEPT_HUNK: re.Pattern = re.compile(r"^\s*except\s*:")
    _STAR_IMPORT_HUNK: re.Pattern = re.compile(r"from\s+\S+\s+import\s+\*")
    _IMPORT_HUNK: re.Pattern = re.compile(r"^\s*(?:from\s+\S+\s+)?import\s+(.+)")
    _IMPORT_NAMES: re.Pattern = re.compile(r"(\w+)(?:\s+as\s+(\w+))?")
    _VAR_HUNK: re.Pattern = re.compile(r"\bvar\s+\w+")
    _CONSOLE_HUNK: re.Pattern = re.compile(r"console\.(log|debug|info|warn|error)\s*\(")
    _ANY_HUNK: re.Pattern = re.compile(r":\s*any\b")

    def __init__(self):
        """Initialize the detector with patterns."""
        self._detectors: dict[str, list[callable]] = {
            "python": [
                self._detect_python_mutable_default,
                self._detect_python_bare_except,
                self._detect_python_star_import,
                self._detect_python_unused_import,
            ],
            "javascript": [
                self._detect_js_var_usage,
                self._detect_js_console_log,
            ],
            "typescript": [
                self._detect_ts_any_type,
                self._detect_js_console_log,
            ],
            "_common": [
                self._detect_long_method,
                self._detect_complex_condition,
                self._detect_deep_nesting,
                self._detect_magic_numbers,
                self._detect_hardcoded_secrets,
                self._detect_todo_fixme,
                self._detect_duplicated_code,
            ],
        }

        # Thresholds
        self.max_method_lines = 50
        self.max_condition_length = 100
        self.max_nesting_depth = 4

    def detect(
        self,
        content: str,
        language: str,
        file_uri: str,
    ) -> list[CodeSmell]:
        """Detect code smells in raw content (for extension service).

        This is a simplified interface for analyzing raw file content
        without needing FileChange/DiffHunk objects.

        Args:
            content: The raw file content
            language: Programming language (e.g., 'python', 'typescript')
            file_uri: File URI for reporting

        Returns:
            List of detected code smells
        """
        smells: list[CodeSmell] = []
        lines = content.split("\n")

        # Detect hardcoded secrets
        smells.extend(self._detect_secrets_in_content(content, file_uri, lines))

        # Detect long methods
        smells.extend(self._detect_long_methods_in_content(content, file_uri, language, lines))

        # Detect complex conditions
        smells.extend(self._detect_complex_conditions_in_content(content, file_uri, lines))

        # Detect deep nesting
        smells.extend(self._detect_deep_nesting_in_content(content, file_uri, language, lines))

        # Detect TODO/FIXME comments
        smells.extend(self._detect_todos_in_content(content, file_uri, lines))

        # Language-specific detections
        if language == "python":
            smells.extend(self._detect_python_issues_in_content(content, file_uri, lines))
        elif language in ("javascript", "typescript"):
            smells.extend(self._detect_js_issues_in_content(content, file_uri, language, lines))

        return smells

    def _detect_secrets_in_content(
        self,
        content: str,
        file_uri: str,
        lines: list[str],
    ) -> list[CodeSmell]:
        """Detect hardcoded secrets in content."""
        smells = []

        for line_num, line in enumerate(lines, 1):
            for pattern, message in self._SECRET_PATTERNS_CONTENT:
                if pattern.search(line):
                    smells.append(CodeSmell(
                        type=SmellType.HARDCODED_SECRET,
                        severity=SmellSeverity.CRITICAL,
                        file=file_uri,
                        line_start=line_num,
                        line_end=line_num,
                        message=message,
                        suggestion="Use environment variables or a secrets manager instead.",
                    ))
                    break  # One issue per line

        return smells

    def _detect_long_methods_in_content(
        self,
        content: str,
        file_uri: str,
        language: str,
        lines: list[str],
    ) -> list[CodeSmell]:
        """Detect long methods in content."""
        smells = []

        # Detect function/method starts based on language
        if language == "python":
            func_re = self._FUNC_PATTERN_PY
        elif language in ("javascript", "typescript"):
            func_re = self._FUNC_PATTERN_JS
        else:
            return smells

        current_func_start = None
        current_indent = 0

        for line_num, line in enumerate(lines, 1):
            if func_re.match(line):
                # Check if previous function was too long
                if current_func_start:
                    func_length = line_num - current_func_start
                    if func_length > self.max_method_lines:
                        smells.append(CodeSmell(
                            type=SmellType.LONG_METHOD,
                            severity=SmellSeverity.MAJOR,
                            file=file_uri,
                            line_start=current_func_start,
                            line_end=line_num - 1,
                            message=f"Method is {func_length} lines long (max {self.max_method_lines})",
                            suggestion="Consider breaking this method into smaller, focused methods.",
                        ))

                current_func_start = line_num
                current_indent = len(line) - len(line.lstrip())

        return smells

    def _detect_complex_conditions_in_content(
        self,
        content: str,
        file_uri: str,
        lines: list[str],
    ) -> list[CodeSmell]:
        """Detect overly complex conditions in content."""
        smells = []

        for line_num, line in enumerate(lines, 1):
            # Count logical operators
            and_count = line.lower().count(' and ') + line.count('&&')
            or_count = line.lower().count(' or ') + line.count('||')

            if and_count + or_count >= 3:
                smells.append(CodeSmell(
                    type=SmellType.COMPLEX_CONDITION,
                    severity=SmellSeverity.MINOR,
                    file=file_uri,
                    line_start=line_num,
                    line_end=line_num,
                    message=f"Complex condition with {and_count + or_count} logical operators",
                    suggestion="Consider extracting conditions into well-named boolean variables or methods.",
                ))

        return smells

    def _detect_deep_nesting_in_content(
        self,
        content: str,
        file_uri: str,
        language: str,
        lines: list[str],
    ) -> list[CodeSmell]:
        """Detect deeply nested code in content."""
        smells = []

        for line_num, line in enumerate(lines, 1):
            if not line.strip():
                continue

            # Calculate nesting level by indentation
            stripped = line.lstrip()
            if not stripped:
                continue

            indent = len(line) - len(stripped)
            # Assume 4 spaces or 1 tab per level
            nesting_level = indent // 4

            if nesting_level > self.max_nesting_depth:
                smells.append(CodeSmell(
                    type=SmellType.DEEP_NESTING,
                    severity=SmellSeverity.MINOR,
                    file=file_uri,
                    line_start=line_num,
                    line_end=line_num,
                    message=f"Code is nested {nesting_level} levels deep (max {self.max_nesting_depth})",
                    suggestion="Consider using early returns, guard clauses, or extracting nested logic.",
                ))

        return smells

    def _detect_todos_in_content(
        self,
        content: str,
        file_uri: str,
        lines: list[str],
    ) -> list[CodeSmell]:
        """Detect TODO and FIXME comments in content."""
        smells = []

        for line_num, line in enumerate(lines, 1):
            match = self._TODO_PATTERN.search(line)
            if match:
                smells.append(CodeSmell(
                    type=SmellType.TODO_COMMENT,
                    severity=SmellSeverity.INFO,
                    file=file_uri,
                    line_start=line_num,
                    line_end=line_num,
                    message=f"{match.group(1)} comment found",
                    suggestion="Track this in your issue tracker and remove the comment.",
                ))

        return smells

    def _detect_python_issues_in_content(
        self,
        content: str,
        file_uri: str,
        lines: list[str],
    ) -> list[CodeSmell]:
        """Detect Python-specific issues in content."""
        smells = []

        for line_num, line in enumerate(lines, 1):
            # Mutable default arguments
            if self._MUTABLE_DEFAULT_PY.search(line):
                smells.append(CodeSmell(
                    type=SmellType.MUTABLE_DEFAULT,
                    severity=SmellSeverity.MAJOR,
                    file=file_uri,
                    line_start=line_num,
                    line_end=line_num,
                    message="Mutable default argument detected",
                    suggestion="Use None as default and initialize inside the function.",
                ))

            # Bare except
            if self._BARE_EXCEPT_PY.search(line):
                smells.append(CodeSmell(
                    type=SmellType.BARE_EXCEPT,
                    severity=SmellSeverity.MAJOR,
                    file=file_uri,
                    line_start=line_num,
                    line_end=line_num,
                    message="Bare except clause catches all exceptions",
                    suggestion="Catch specific exceptions instead.",
                ))

            # Star imports
            if self._STAR_IMPORT_PY.search(line):
                smells.append(CodeSmell(
                    type=SmellType.STAR_IMPORT,
                    severity=SmellSeverity.MINOR,
                    file=file_uri,
                    line_start=line_num,
                    line_end=line_num,
                    message="Star import pollutes namespace",
                    suggestion="Import only what you need explicitly.",
                ))

            # eval() usage
            if self._EVAL_PY.search(line):
                smells.append(CodeSmell(
                    type=SmellType.DANGEROUS_EVAL,
                    severity=SmellSeverity.CRITICAL,
                    file=file_uri,
                    line_start=line_num,
                    line_end=line_num,
                    message="Use of eval() is dangerous",
                    suggestion="Avoid eval(). Use ast.literal_eval() for safe evaluation of literals.",
                ))

        return smells

    def _detect_js_issues_in_content(
        self,
        content: str,
        file_uri: str,
        language: str,
        lines: list[str],
    ) -> list[CodeSmell]:
        """Detect JavaScript/TypeScript-specific issues in content."""
        smells = []

        for line_num, line in enumerate(lines, 1):
            # var usage (prefer let/const)
            if self._VAR_JS.search(line):
                smells.append(CodeSmell(
                    type=SmellType.VAR_USAGE,
                    severity=SmellSeverity.MINOR,
                    file=file_uri,
                    line_start=line_num,
                    line_end=line_num,
                    message="Use of 'var' instead of 'let' or 'const'",
                    suggestion="Use 'const' for values that don't change, 'let' otherwise.",
                ))

            # console.log (should be removed)
            if self._CONSOLE_JS.search(line):
                smells.append(CodeSmell(
                    type=SmellType.CONSOLE_LOG,
                    severity=SmellSeverity.INFO,
                    file=file_uri,
                    line_start=line_num,
                    line_end=line_num,
                    message="console.log statement found",
                    suggestion="Remove console.log before committing or use a proper logger.",
                ))

            # TypeScript 'any' type
            if language == "typescript" and self._ANY_TS.search(line):
                smells.append(CodeSmell(
                    type=SmellType.ANY_TYPE,
                    severity=SmellSeverity.MINOR,
                    file=file_uri,
                    line_start=line_num,
                    line_end=line_num,
                    message="Use of 'any' type reduces type safety",
                    suggestion="Use a more specific type or 'unknown' for truly unknown types.",
                ))

        return smells

    def detect_smells(
        self,
        file: FileChange,
        hunks: list[DiffHunk],
        full_content: str | None = None,
    ) -> list[CodeSmell]:
        """Detect code smells in a file's changes.

        Args:
            file: The file change information
            hunks: Diff hunks for the file
            full_content: Optional full file content for deeper analysis

        Returns:
            List of detected code smells
        """
        smells = []

        # Run common detectors
        for detector in self._detectors["_common"]:
            smells.extend(detector(file, hunks))

        # Run language-specific detectors
        if file.language and file.language in self._detectors:
            for detector in self._detectors[file.language]:
                smells.extend(detector(file, hunks))

        return smells

    # ========== Common Detectors ==========

    def _detect_long_method(
        self,
        file: FileChange,
        hunks: list[DiffHunk],
    ) -> list[CodeSmell]:
        """Detect methods that are too long."""
        smells = []

        # Simple heuristic: check if a hunk introduces many consecutive additions
        for hunk in hunks:
            consecutive_additions = 0
            start_line = hunk.new_start

            for i, line in enumerate(hunk.lines):
                if line.type == "addition":
                    consecutive_additions += 1
                else:
                    if consecutive_additions > self.max_method_lines:
                        smells.append(CodeSmell(
                            type=SmellType.LONG_METHOD,
                            severity=SmellSeverity.MAJOR,
                            file=file.filename,
                            line_start=start_line + i - consecutive_additions,
                            line_end=start_line + i,
                            message=f"Method appears to be very long ({consecutive_additions}+ lines). Consider breaking it down.",
                            suggestion="Extract smaller, focused methods with single responsibilities.",
                        ))
                    consecutive_additions = 0

        return smells

    def _detect_complex_condition(
        self,
        file: FileChange,
        hunks: list[DiffHunk],
    ) -> list[CodeSmell]:
        """Detect overly complex conditional statements."""
        smells = []

        for hunk in hunks:
            for i, line in enumerate(hunk.lines):
                if line.type != "addition":
                    continue

                operators = len(self._BOOLEAN_OPS.findall(line.content))
                if operators >= 3:
                    smells.append(CodeSmell(
                        type=SmellType.COMPLEX_CONDITION,
                        severity=SmellSeverity.MINOR,
                        file=file.filename,
                        line_start=hunk.new_start + i,
                        message=f"Complex condition with {operators} boolean operators.",
                        suggestion="Extract condition into a well-named boolean variable or method.",
                        code_snippet=line.content.strip()[:100],
                    ))

        return smells

    def _detect_deep_nesting(
        self,
        file: FileChange,
        hunks: list[DiffHunk],
    ) -> list[CodeSmell]:
        """Detect deeply nested code blocks."""
        smells = []

        for hunk in hunks:
            for i, line in enumerate(hunk.lines):
                if line.type != "addition":
                    continue

                # Count leading whitespace (indentation)
                content = line.content
                indent = len(content) - len(content.lstrip())

                # Estimate nesting level (assuming 4 spaces or 1 tab per level)
                nesting = indent // 4 if "    " in content[:indent] else indent

                if nesting > self.max_nesting_depth:
                    smells.append(CodeSmell(
                        type=SmellType.DEEP_NESTING,
                        severity=SmellSeverity.MINOR,
                        file=file.filename,
                        line_start=hunk.new_start + i,
                        message=f"Code is nested {nesting} levels deep.",
                        suggestion="Consider early returns, guard clauses, or extracting nested logic.",
                    ))

        return smells

    def _detect_magic_numbers(
        self,
        file: FileChange,
        hunks: list[DiffHunk],
    ) -> list[CodeSmell]:
        """Detect magic numbers in code."""
        smells = []

        # Allowed numbers
        allowed = {"0", "1", "-1", "2", "100", "1000"}

        for hunk in hunks:
            for i, line in enumerate(hunk.lines):
                if line.type != "addition":
                    continue

                content = line.content

                # Skip if it's a comment or string-heavy line
                if content.strip().startswith(("#", "//", "*", "/*")):
                    continue

                matches = self._MAGIC_NUMBER.findall(content)
                for num in matches:
                    if num not in allowed and len(num) > 1:  # Skip single digits
                        smells.append(CodeSmell(
                            type=SmellType.MAGIC_NUMBER,
                            severity=SmellSeverity.INFO,
                            file=file.filename,
                            line_start=hunk.new_start + i,
                            message=f"Magic number '{num}' found.",
                            suggestion="Consider defining a named constant.",
                            code_snippet=content.strip()[:80],
                            confidence=0.7,
                        ))
                        break  # One smell per line is enough

        return smells

    def _detect_hardcoded_secrets(
        self,
        file: FileChange,
        hunks: list[DiffHunk],
    ) -> list[CodeSmell]:
        """Detect potential hardcoded secrets."""
        smells = []

        for hunk in hunks:
            for i, line in enumerate(hunk.lines):
                if line.type != "addition":
                    continue

                for pattern, secret_type in self._SECRET_PATTERNS_HUNK:
                    if pattern.search(line.content):
                        smells.append(CodeSmell(
                            type=SmellType.HARDCODED_SECRET,
                            severity=SmellSeverity.CRITICAL,
                            file=file.filename,
                            line_start=hunk.new_start + i,
                            message=f"Potential hardcoded {secret_type} detected.",
                            suggestion="Use environment variables or a secret manager.",
                            confidence=0.9,
                        ))
                        break  # One critical issue per line

        return smells

    def _detect_todo_fixme(
        self,
        file: FileChange,
        hunks: list[DiffHunk],
    ) -> list[CodeSmell]:
        """Detect TODO/FIXME comments being added."""
        smells = []

        for hunk in hunks:
            for i, line in enumerate(hunk.lines):
                if line.type != "addition":
                    continue

                match = self._TODO_FIXME_HUNK.search(line.content)
                if match:
                    smells.append(CodeSmell(
                        type=SmellType.BAD_NAMING,  # Using as general marker
                        severity=SmellSeverity.INFO,
                        file=file.filename,
                        line_start=hunk.new_start + i,
                        message=f"New {match.group(1)} comment added.",
                        suggestion="Consider addressing this before merging or create a tracking issue.",
                        code_snippet=line.content.strip()[:100],
                    ))

        return smells

    def _detect_duplicated_code(
        self,
        file: FileChange,
        hunks: list[DiffHunk],
    ) -> list[CodeSmell]:
        """Detect potential duplicated code within the same file."""
        smells = []

        # Collect all added lines (normalized)
        added_lines: list[tuple[int, str]] = []
        for hunk in hunks:
            for i, line in enumerate(hunk.lines):
                if line.type == "addition" and line.content.strip():
                    normalized = line.content.strip().lower()
                    # Skip short lines and common patterns
                    if len(normalized) > 20 and not normalized.startswith(("#", "//", "import", "from")):
                        added_lines.append((hunk.new_start + i, normalized))

        # Check for duplicates
        seen: dict[str, int] = {}
        for line_num, content in added_lines:
            if content in seen:
                smells.append(CodeSmell(
                    type=SmellType.DUPLICATED_CODE,
                    severity=SmellSeverity.MINOR,
                    file=file.filename,
                    line_start=line_num,
                    message=f"Potential duplicate of line {seen[content]}.",
                    suggestion="Consider extracting common code into a shared function.",
                    confidence=0.6,
                ))
            else:
                seen[content] = line_num

        return smells

    # ========== Python-Specific Detectors ==========

    def _detect_python_mutable_default(
        self,
        file: FileChange,
        hunks: list[DiffHunk],
    ) -> list[CodeSmell]:
        """Detect mutable default arguments in Python."""
        smells = []

        for hunk in hunks:
            for i, line in enumerate(hunk.lines):
                if line.type != "addition":
                    continue

                if self._MUTABLE_DEFAULT_HUNK.search(line.content):
                    smells.append(CodeSmell(
                        type=SmellType.MUTABLE_DEFAULT,
                        severity=SmellSeverity.MAJOR,
                        file=file.filename,
                        line_start=hunk.new_start + i,
                        message="Mutable default argument detected.",
                        suggestion="Use None as default and initialize inside the function.",
                        code_snippet=line.content.strip()[:100],
                    ))

        return smells

    def _detect_python_bare_except(
        self,
        file: FileChange,
        hunks: list[DiffHunk],
    ) -> list[CodeSmell]:
        """Detect bare except clauses in Python."""
        smells = []

        for hunk in hunks:
            for i, line in enumerate(hunk.lines):
                if line.type != "addition":
                    continue

                if self._BARE_EXCEPT_HUNK.match(line.content):
                    smells.append(CodeSmell(
                        type=SmellType.BARE_EXCEPT,
                        severity=SmellSeverity.MAJOR,
                        file=file.filename,
                        line_start=hunk.new_start + i,
                        message="Bare except clause catches all exceptions including KeyboardInterrupt.",
                        suggestion="Catch specific exceptions: except Exception: or except (TypeError, ValueError):",
                    ))

        return smells

    def _detect_python_star_import(
        self,
        file: FileChange,
        hunks: list[DiffHunk],
    ) -> list[CodeSmell]:
        """Detect star imports in Python."""
        smells = []

        for hunk in hunks:
            for i, line in enumerate(hunk.lines):
                if line.type != "addition":
                    continue

                if self._STAR_IMPORT_HUNK.search(line.content):
                    smells.append(CodeSmell(
                        type=SmellType.STAR_IMPORT,
                        severity=SmellSeverity.MINOR,
                        file=file.filename,
                        line_start=hunk.new_start + i,
                        message="Star import pollutes namespace and makes dependencies unclear.",
                        suggestion="Import specific names: from module import name1, name2",
                    ))

        return smells

    def _detect_python_unused_import(
        self,
        file: FileChange,
        hunks: list[DiffHunk],
    ) -> list[CodeSmell]:
        """Detect potentially unused imports."""
        # This is a simplified check - real detection needs full file analysis
        smells = []

        # Collect imports and their usage
        imports: dict[str, int] = {}

        for hunk in hunks:
            for i, line in enumerate(hunk.lines):
                if line.type != "addition":
                    continue

                # Check for import statement
                import_match = self._IMPORT_HUNK.match(line.content)
                if import_match:
                    # Extract imported names
                    names = import_match.group(1)
                    for name in self._IMPORT_NAMES.findall(names):
                        actual_name = name[1] if name[1] else name[0]
                        imports[actual_name] = hunk.new_start + i

        # Note: Full unused import detection would require analyzing the entire file
        # This is just a placeholder for the pattern

        return smells

    # ========== JavaScript/TypeScript-Specific Detectors ==========

    def _detect_js_var_usage(
        self,
        file: FileChange,
        hunks: list[DiffHunk],
    ) -> list[CodeSmell]:
        """Detect var keyword usage in JavaScript."""
        smells = []

        for hunk in hunks:
            for i, line in enumerate(hunk.lines):
                if line.type != "addition":
                    continue

                if self._VAR_HUNK.search(line.content):
                    smells.append(CodeSmell(
                        type=SmellType.BAD_NAMING,
                        severity=SmellSeverity.MINOR,
                        file=file.filename,
                        line_start=hunk.new_start + i,
                        message="'var' keyword has function scope and can cause issues.",
                        suggestion="Use 'const' for constants or 'let' for variables.",
                    ))

        return smells

    def _detect_js_console_log(
        self,
        file: FileChange,
        hunks: list[DiffHunk],
    ) -> list[CodeSmell]:
        """Detect console.log statements."""
        smells = []

        for hunk in hunks:
            for i, line in enumerate(hunk.lines):
                if line.type != "addition":
                    continue

                if self._CONSOLE_HUNK.search(line.content):
                    smells.append(CodeSmell(
                        type=SmellType.BAD_NAMING,
                        severity=SmellSeverity.INFO,
                        file=file.filename,
                        line_start=hunk.new_start + i,
                        message="console statement found - consider removing before production.",
                        suggestion="Use a proper logging library or remove debug statements.",
                        confidence=0.8,
                    ))

        return smells

    def _detect_ts_any_type(
        self,
        file: FileChange,
        hunks: list[DiffHunk],
    ) -> list[CodeSmell]:
        """Detect 'any' type usage in TypeScript."""
        smells = []

        for hunk in hunks:
            for i, line in enumerate(hunk.lines):
                if line.type != "addition":
                    continue

                if self._ANY_HUNK.search(line.content):
                    smells.append(CodeSmell(
                        type=SmellType.PRIMITIVE_OBSESSION,
                        severity=SmellSeverity.MINOR,
                        file=file.filename,
                        line_start=hunk.new_start + i,
                        message="'any' type bypasses TypeScript's type checking.",
                        suggestion="Use a specific type, 'unknown', or a generic type.",
                    ))

        return smells
