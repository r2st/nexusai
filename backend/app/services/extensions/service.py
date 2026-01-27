"""Extension service for IDE integrations."""

import hashlib
import logging
import time
import uuid
from typing import Any

from app.services.extensions.models import (
    AnalysisRequest,
    AnalysisResult,
    AnalysisIssue,
    IssueSeverity,
    IssueCategory,
    QuickFix,
    CodeSuggestion,
    ChatRequest,
    ChatResponse,
    HoverInfo,
    CompletionItem,
    CompletionRequest,
    DiagnosticRequest,
    DiagnosticResult,
    ExtensionConfig,
    ExtensionCapabilities,
    Position,
    Range,
)
from app.services.code_review.smells import CodeSmellDetector
from app.services.code_review.models import SmellSeverity, SmellType

logger = logging.getLogger(__name__)

# Singleton instance
_extension_service: "ExtensionService | None" = None


class ExtensionService:
    """Service for IDE extension integration.

    Provides code analysis, diagnostics, completions, and chat
    functionality for IDE extensions like VS Code.
    """

    def __init__(
        self,
        config: ExtensionConfig | None = None,
        llm_service: Any | None = None,
        chat_service: Any | None = None,
    ):
        self.config = config or ExtensionConfig()
        self.llm_service = llm_service
        self.chat_service = chat_service
        self.smell_detector = CodeSmellDetector()
        self._analysis_cache: dict[str, AnalysisResult] = {}
        self._cache_ttl = 60  # seconds

    def get_capabilities(self) -> ExtensionCapabilities:
        """Get extension capabilities."""
        return ExtensionCapabilities(
            diagnostics=True,
            code_actions=True,
            completion=self.llm_service is not None,
            hover=True,
            document_symbols=True,
            workspace_symbols=True,
            formatting=False,
            rename=False,
            references=False,
            definition=False,
            chat=self.chat_service is not None,
            inline_suggestions=self.llm_service is not None,
        )

    async def analyze(self, request: AnalysisRequest) -> AnalysisResult:
        """Perform full code analysis on a file.

        Args:
            request: Analysis request with file content and options

        Returns:
            AnalysisResult with issues, suggestions, and metrics
        """
        start_time = time.time()

        # Check cache
        cache_key = self._get_cache_key(request)
        if cache_key in self._analysis_cache:
            cached = self._analysis_cache[cache_key]
            if (time.time() - cached.analyzed_at.timestamp()) < self._cache_ttl:
                return cached

        issues: list[AnalysisIssue] = []
        suggestions: list[CodeSuggestion] = []
        metrics: dict[str, Any] = {}

        # Run smell detection
        if "smells" in request.analysis_types or "diagnostics" in request.analysis_types:
            smell_issues = await self._detect_smells(
                request.content,
                request.language_id,
                request.file_uri,
            )
            issues.extend(smell_issues)

        # Run security analysis
        if "security" in request.analysis_types:
            security_issues = await self._analyze_security(
                request.content,
                request.language_id,
                request.file_uri,
            )
            issues.extend(security_issues)

        # Calculate metrics
        metrics = self._calculate_metrics(request.content, request.language_id, issues)

        # Generate AI suggestions if LLM available and issues found
        if self.llm_service and issues:
            suggestions = await self._generate_suggestions(
                request.content,
                request.language_id,
                issues[:5],  # Limit to top 5 issues
            )

        analysis_time = (time.time() - start_time) * 1000

        result = AnalysisResult(
            file_uri=request.file_uri,
            version=request.version,
            issues=issues,
            suggestions=suggestions,
            metrics=metrics,
            analysis_time_ms=analysis_time,
        )

        # Cache result
        self._analysis_cache[cache_key] = result

        return result

    async def get_diagnostics(self, request: DiagnosticRequest) -> DiagnosticResult:
        """Get quick diagnostics for a file (lightweight analysis).

        Args:
            request: Diagnostic request

        Returns:
            DiagnosticResult with issues
        """
        # Use smell detection for quick diagnostics
        issues = await self._detect_smells(
            request.content,
            request.language_id,
            request.file_uri,
        )

        # Filter to only errors and warnings for quick diagnostics
        filtered = [
            i for i in issues
            if i.severity in (IssueSeverity.ERROR, IssueSeverity.WARNING)
        ]

        return DiagnosticResult(
            file_uri=request.file_uri,
            version=request.version,
            diagnostics=filtered,
        )

    async def get_completions(self, request: CompletionRequest) -> list[CompletionItem]:
        """Get code completions at a position.

        Args:
            request: Completion request with position

        Returns:
            List of completion items
        """
        if not self.llm_service:
            return []

        # Extract context around cursor
        lines = request.content.split("\n")
        current_line = lines[request.position.line] if request.position.line < len(lines) else ""
        prefix = current_line[:request.position.character]

        # Get context window (5 lines before, current line)
        start_line = max(0, request.position.line - 5)
        context_lines = lines[start_line:request.position.line + 1]
        context = "\n".join(context_lines)

        try:
            # Generate completions using LLM
            completions = await self._generate_completions(
                context=context,
                prefix=prefix,
                language=request.language_id,
                max_results=request.max_results,
            )
            return completions
        except Exception as e:
            logger.error(f"Error generating completions: {e}")
            return []

    async def get_hover_info(
        self,
        content: str,
        position: Position,
        language_id: str,
    ) -> HoverInfo | None:
        """Get hover information at a position.

        Args:
            content: File content
            position: Cursor position
            language_id: Language identifier

        Returns:
            HoverInfo or None
        """
        # Extract word at position
        lines = content.split("\n")
        if position.line >= len(lines):
            return None

        line = lines[position.line]
        word = self._extract_word_at_position(line, position.character)

        if not word:
            return None

        # Generate hover info (could use LLM for documentation)
        hover_content = f"**{word}**\n\n"

        # Add basic type info based on patterns
        if word.startswith("_"):
            hover_content += "_Private member_\n"
        elif word.isupper():
            hover_content += "_Constant_\n"

        return HoverInfo(
            contents=hover_content,
            range=Range(
                start=Position(line=position.line, character=position.character - len(word) // 2),
                end=Position(line=position.line, character=position.character + len(word) // 2),
            ),
        )

    async def chat(self, request: ChatRequest, user_id: str) -> ChatResponse:
        """Handle chat/assistant interaction.

        Args:
            request: Chat request
            user_id: User identifier

        Returns:
            ChatResponse with assistant message
        """
        if not self.chat_service:
            return ChatResponse(
                message="Chat service is not available. Please configure LLM settings.",
                conversation_id=request.conversation_id or str(uuid.uuid4()),
            )

        # Build context from file and selection
        context_parts = []
        if request.file_context:
            context_parts.append(f"Current file: {request.file_context.get('uri', 'unknown')}")
            if request.file_context.get("language"):
                context_parts.append(f"Language: {request.file_context['language']}")

        if request.selection:
            context_parts.append(f"\nSelected code:\n```\n{request.selection}\n```")

        # Handle explicit commands
        prompt = request.message
        if request.command:
            command_prompts = {
                "explain": "Explain the following code in detail:",
                "fix": "Fix any issues in the following code and explain the changes:",
                "refactor": "Refactor the following code to improve readability and maintainability:",
                "document": "Add documentation/comments to the following code:",
                "test": "Write unit tests for the following code:",
                "optimize": "Optimize the following code for performance:",
            }
            if request.command in command_prompts:
                prompt = f"{command_prompts[request.command]}\n\n{request.selection or request.message}"

        # Add context to prompt
        if context_parts:
            full_prompt = "\n".join(context_parts) + "\n\n" + prompt
        else:
            full_prompt = prompt

        try:
            # Use chat service
            response = await self.chat_service.send_message(
                message=full_prompt,
                conversation_id=request.conversation_id,
                user_id=user_id,
            )

            return ChatResponse(
                message=response.get("content", ""),
                conversation_id=response.get("conversation_id", str(uuid.uuid4())),
                code_blocks=self._extract_code_blocks(response.get("content", "")),
                suggested_edits=[],
                references=[],
                follow_up_questions=response.get("follow_up_questions", []),
            )

        except Exception as e:
            logger.error(f"Chat error: {e}")
            return ChatResponse(
                message=f"Error processing request: {str(e)}",
                conversation_id=request.conversation_id or str(uuid.uuid4()),
            )

    async def get_quick_fixes(
        self,
        issue: AnalysisIssue,
        content: str,
        language_id: str,
    ) -> list[QuickFix]:
        """Get quick fix actions for an issue.

        Args:
            issue: The issue to fix
            content: File content
            language_id: Language identifier

        Returns:
            List of quick fix actions
        """
        fixes: list[QuickFix] = []

        # Category-specific fixes
        if issue.category == IssueCategory.SECURITY:
            fixes.append(QuickFix(
                title="Show security documentation",
                kind="quickfix",
                command="nexusai.showSecurityDocs",
                arguments=[issue.code],
            ))

        if issue.category == IssueCategory.DEPRECATED:
            fixes.append(QuickFix(
                title="Show migration guide",
                kind="quickfix",
                command="nexusai.showMigrationGuide",
                arguments=[issue.code],
            ))

        # Generate AI fix if LLM available
        if self.llm_service and issue.severity in (IssueSeverity.ERROR, IssueSeverity.WARNING):
            try:
                ai_fix = await self._generate_fix(issue, content, language_id)
                if ai_fix:
                    fixes.insert(0, ai_fix)
            except Exception as e:
                logger.error(f"Error generating AI fix: {e}")

        return fixes

    # Private helper methods

    def _get_cache_key(self, request: AnalysisRequest) -> str:
        """Generate cache key for analysis request."""
        content_hash = hashlib.md5(request.content.encode()).hexdigest()
        return f"{request.file_uri}:{content_hash}:{request.version}"

    async def _detect_smells(
        self,
        content: str,
        language_id: str,
        file_uri: str,
    ) -> list[AnalysisIssue]:
        """Detect code smells and convert to issues."""
        issues: list[AnalysisIssue] = []

        # Map language ID to code review language
        language_map = {
            "python": "python",
            "typescript": "typescript",
            "javascript": "javascript",
            "typescriptreact": "typescript",
            "javascriptreact": "javascript",
            "go": "go",
            "java": "java",
        }
        lang = language_map.get(language_id, language_id)

        # Detect smells
        smells = self.smell_detector.detect(content, lang, file_uri)

        # Convert smells to issues
        for smell in smells:
            severity = self._map_smell_severity(smell.severity)
            category = self._map_smell_category(smell.type)

            issue = AnalysisIssue(
                id=f"smell-{smell.type.value}-{smell.line_start}",
                message=smell.message,
                severity=severity,
                category=category,
                range=Range(
                    start=Position(line=smell.line_start - 1, character=0),
                    end=Position(line=(smell.line_end or smell.line_start) - 1, character=100),
                ),
                source="nexusai",
                code=smell.type.value,
                code_description=smell.suggestion,
                quick_fixes=[],
            )

            # Add quick fix if suggestion available
            if smell.suggestion:
                issue.quick_fixes.append(QuickFix(
                    title=smell.suggestion[:50] + "..." if len(smell.suggestion) > 50 else smell.suggestion,
                    kind="quickfix",
                    command="nexusai.applySuggestion",
                    arguments=[smell.suggestion],
                ))

            issues.append(issue)

        return issues

    async def _analyze_security(
        self,
        content: str,
        language_id: str,
        file_uri: str,
    ) -> list[AnalysisIssue]:
        """Analyze code for security issues."""
        issues: list[AnalysisIssue] = []
        lines = content.split("\n")

        # Security patterns to detect
        security_patterns = [
            # Hardcoded secrets
            (r"(password|secret|api_key|apikey|token)\s*=\s*['\"][^'\"]+['\"]", "hardcoded_secret", "Hardcoded secret detected"),
            # SQL injection
            (r"execute\([^)]*%s|execute\([^)]*\+|f\".*SELECT.*{", "sql_injection", "Potential SQL injection"),
            # Eval usage
            (r"\beval\s*\(", "dangerous_eval", "Use of eval() is dangerous"),
            # Pickle with untrusted data
            (r"pickle\.loads?\(", "insecure_deserialization", "Insecure deserialization with pickle"),
        ]

        import re
        for line_num, line in enumerate(lines):
            for pattern, code, message in security_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(AnalysisIssue(
                        id=f"security-{code}-{line_num}",
                        message=message,
                        severity=IssueSeverity.ERROR,
                        category=IssueCategory.SECURITY,
                        range=Range(
                            start=Position(line=line_num, character=0),
                            end=Position(line=line_num, character=len(line)),
                        ),
                        source="nexusai",
                        code=code,
                        tags=["security"],
                    ))

        return issues

    def _calculate_metrics(
        self,
        content: str,
        language_id: str,
        issues: list[AnalysisIssue],
    ) -> dict[str, Any]:
        """Calculate code metrics."""
        lines = content.split("\n")
        non_empty_lines = [l for l in lines if l.strip()]

        return {
            "total_lines": len(lines),
            "code_lines": len(non_empty_lines),
            "issue_count": len(issues),
            "error_count": len([i for i in issues if i.severity == IssueSeverity.ERROR]),
            "warning_count": len([i for i in issues if i.severity == IssueSeverity.WARNING]),
            "security_issue_count": len([i for i in issues if i.category == IssueCategory.SECURITY]),
            "issues_per_100_lines": round(len(issues) / max(len(non_empty_lines), 1) * 100, 2),
        }

    async def _generate_suggestions(
        self,
        content: str,
        language_id: str,
        issues: list[AnalysisIssue],
    ) -> list[CodeSuggestion]:
        """Generate AI-powered code suggestions."""
        # This would use the LLM service to generate suggestions
        # For now, return empty list - implement when LLM integration is ready
        return []

    async def _generate_completions(
        self,
        context: str,
        prefix: str,
        language: str,
        max_results: int,
    ) -> list[CompletionItem]:
        """Generate AI-powered completions."""
        # This would use the LLM service to generate completions
        # For now, return empty list - implement when LLM integration is ready
        return []

    async def _generate_fix(
        self,
        issue: AnalysisIssue,
        content: str,
        language_id: str,
    ) -> QuickFix | None:
        """Generate an AI-powered fix for an issue."""
        # This would use the LLM service to generate a fix
        # For now, return None - implement when LLM integration is ready
        return None

    def _extract_word_at_position(self, line: str, character: int) -> str:
        """Extract the word at a given position in a line."""
        if character >= len(line):
            return ""

        # Find word boundaries
        start = character
        end = character

        while start > 0 and (line[start - 1].isalnum() or line[start - 1] == "_"):
            start -= 1

        while end < len(line) and (line[end].isalnum() or line[end] == "_"):
            end += 1

        return line[start:end]

    def _extract_code_blocks(self, content: str) -> list[dict[str, Any]]:
        """Extract code blocks from markdown content."""
        import re
        blocks = []
        pattern = r"```(\w+)?\n(.*?)```"
        matches = re.findall(pattern, content, re.DOTALL)

        for i, (lang, code) in enumerate(matches):
            blocks.append({
                "id": i,
                "language": lang or "text",
                "code": code.strip(),
            })

        return blocks

    def _map_smell_severity(self, severity: SmellSeverity) -> IssueSeverity:
        """Map smell severity to issue severity."""
        mapping = {
            SmellSeverity.CRITICAL: IssueSeverity.ERROR,
            SmellSeverity.MAJOR: IssueSeverity.WARNING,
            SmellSeverity.MINOR: IssueSeverity.INFO,
            SmellSeverity.INFO: IssueSeverity.HINT,
        }
        return mapping.get(severity, IssueSeverity.INFO)

    def _map_smell_category(self, smell_type: SmellType) -> IssueCategory:
        """Map smell type to issue category."""
        security_smells = {
            SmellType.HARDCODED_SECRET,
            SmellType.SQL_INJECTION,
            SmellType.XSS_VULNERABILITY,
            SmellType.INSECURE_RANDOM,
        }
        performance_smells = {
            SmellType.N_PLUS_ONE,
            SmellType.MEMORY_LEAK,
            SmellType.INEFFICIENT_LOOP,
        }
        complexity_smells = {
            SmellType.LONG_METHOD,
            SmellType.COMPLEX_CONDITION,
            SmellType.DEEP_NESTING,
            SmellType.GOD_CLASS,
        }

        if smell_type in security_smells:
            return IssueCategory.SECURITY
        elif smell_type in performance_smells:
            return IssueCategory.PERFORMANCE
        elif smell_type in complexity_smells:
            return IssueCategory.COMPLEXITY
        else:
            return IssueCategory.MAINTAINABILITY


def get_extension_service(
    config: ExtensionConfig | None = None,
    llm_service: Any | None = None,
    chat_service: Any | None = None,
) -> ExtensionService:
    """Get or create the extension service singleton."""
    global _extension_service

    if _extension_service is None:
        _extension_service = ExtensionService(
            config=config,
            llm_service=llm_service,
            chat_service=chat_service,
        )

    return _extension_service
