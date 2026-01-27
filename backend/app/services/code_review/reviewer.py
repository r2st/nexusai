"""Review Generator - LLM-powered code review generation."""

import json
from typing import Any

from app.core.config import settings
from app.services.code_review.models import (
    CodeReview,
    CodeSmell,
    DiffAnalysis,
    DiffHunk,
    FileChange,
    ReviewCategory,
    ReviewComment,
    ReviewConfig,
    ReviewPriority,
)


class ReviewGenerator:
    """Generates code reviews using LLM."""

    def __init__(
        self,
        llm_gateway: Any | None = None,
        config: ReviewConfig | None = None,
    ):
        """Initialize the review generator.

        Args:
            llm_gateway: LLM gateway service for generating reviews
            config: Review configuration
        """
        self._gateway = llm_gateway
        self._config = config or ReviewConfig()

    async def generate_review(
        self,
        analysis: DiffAnalysis,
        smells: list[CodeSmell],
        context: dict[str, Any] | None = None,
    ) -> CodeReview:
        """Generate a comprehensive code review.

        Args:
            analysis: PR diff analysis
            smells: Detected code smells
            context: Additional context (e.g., project guidelines)

        Returns:
            Complete code review
        """
        # Build context for LLM
        review_context = self._build_context(analysis, smells, context)

        # Generate review using LLM
        if self._gateway:
            llm_review = await self._generate_llm_review(review_context)
        else:
            llm_review = self._generate_fallback_review(analysis, smells)

        # Combine LLM review with detected smells
        comments = llm_review.get("comments", [])
        smell_comments = self._smells_to_comments(smells)

        # Merge and deduplicate comments
        all_comments = self._merge_comments(comments, smell_comments)

        # Calculate overall quality
        quality = self._calculate_quality(analysis, smells, all_comments)

        # Determine approval recommendation
        recommendation = self._determine_recommendation(quality, smells, all_comments)

        return CodeReview(
            pr_number=analysis.pr_info.number,
            repository=analysis.pr_info.repository,
            summary=llm_review.get("summary", self._generate_summary(analysis)),
            overall_quality=quality,
            comments=all_comments,
            smells=smells,
            approval_recommendation=recommendation,
            metrics={
                "complexity_score": analysis.complexity_score,
                "risk_score": analysis.risk_score,
                "files_reviewed": len(analysis.files),
                "total_changes": analysis.total_changes,
                "languages": analysis.languages,
            },
        )

    def _build_context(
        self,
        analysis: DiffAnalysis,
        smells: list[CodeSmell],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build context for LLM review."""
        # Select most important files (by changes)
        top_files = sorted(
            analysis.files,
            key=lambda f: f.additions + f.deletions,
            reverse=True,
        )[:10]

        # Build file summaries
        file_summaries = []
        for f in top_files:
            hunks = analysis.hunks_by_file.get(f.filename, [])
            file_summaries.append({
                "filename": f.filename,
                "language": f.language,
                "additions": f.additions,
                "deletions": f.deletions,
                "status": f.status,
                "hunks": len(hunks),
                "patch_preview": f.patch[:500] if f.patch else None,
            })

        # Group smells by severity
        smell_summary = {
            "critical": len([s for s in smells if s.severity.value == "critical"]),
            "major": len([s for s in smells if s.severity.value == "major"]),
            "minor": len([s for s in smells if s.severity.value == "minor"]),
            "info": len([s for s in smells if s.severity.value == "info"]),
        }

        return {
            "pr": {
                "number": analysis.pr_info.number,
                "title": analysis.pr_info.title,
                "description": analysis.pr_info.description,
                "author": analysis.pr_info.author,
                "base_branch": analysis.pr_info.base_branch,
                "head_branch": analysis.pr_info.head_branch,
            },
            "metrics": {
                "total_additions": analysis.total_additions,
                "total_deletions": analysis.total_deletions,
                "files_changed": len(analysis.files),
                "languages": analysis.languages,
                "complexity_score": analysis.complexity_score,
                "risk_score": analysis.risk_score,
            },
            "files": file_summaries,
            "smells": smell_summary,
            "guidelines": context.get("guidelines") if context else None,
        }

    async def _generate_llm_review(
        self,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate review using LLM."""
        prompt = self._build_review_prompt(context)

        try:
            response = await self._gateway.chat(
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt},
                ],
                model=self._config.llm_model,
                temperature=0.3,  # Lower temperature for more consistent reviews
            )

            # Parse LLM response
            return self._parse_llm_response(response.content)

        except Exception as e:
            # Fallback on error
            return {
                "summary": f"Unable to generate LLM review: {e}",
                "comments": [],
            }

    def _get_system_prompt(self) -> str:
        """Get the system prompt for code review."""
        return """You are an expert code reviewer with deep knowledge of software engineering best practices.

Your task is to review code changes and provide constructive, actionable feedback.

Focus on:
1. Security vulnerabilities and risks
2. Performance issues and optimizations
3. Code maintainability and readability
4. Potential bugs and edge cases
5. Adherence to best practices

Guidelines:
- Be constructive and educational
- Prioritize issues by severity
- Provide specific suggestions with code examples when helpful
- Consider the context and purpose of changes
- Acknowledge good patterns and improvements

Respond in JSON format with:
{
  "summary": "Brief overall assessment",
  "comments": [
    {
      "file": "path/to/file.py",
      "line": 42,
      "priority": "high|medium|low|info",
      "category": "security|performance|maintainability|bug|style",
      "body": "Detailed comment",
      "suggestion": "Optional specific suggestion",
      "code_suggestion": "Optional code fix"
    }
  ]
}"""

    def _build_review_prompt(self, context: dict[str, Any]) -> str:
        """Build the review prompt from context."""
        pr = context["pr"]
        metrics = context["metrics"]

        prompt = f"""Please review this pull request:

## PR Information
- Title: {pr['title']}
- Author: {pr['author']}
- Branch: {pr['head_branch']} → {pr['base_branch']}

## Description
{pr['description'] or 'No description provided.'}

## Metrics
- Files changed: {metrics['files_changed']}
- Lines added: {metrics['total_additions']}
- Lines removed: {metrics['total_deletions']}
- Languages: {', '.join(metrics['languages']) or 'Unknown'}
- Complexity score: {metrics['complexity_score']}/10
- Risk score: {metrics['risk_score']}/10

## Detected Issues (by automated analysis)
- Critical: {context['smells']['critical']}
- Major: {context['smells']['major']}
- Minor: {context['smells']['minor']}
- Info: {context['smells']['info']}

## Files Changed
"""
        for f in context["files"]:
            prompt += f"\n### {f['filename']} ({f['language'] or 'unknown'})\n"
            prompt += f"Status: {f['status']} | +{f['additions']} -{f['deletions']}\n"
            if f.get("patch_preview"):
                prompt += f"\n```diff\n{f['patch_preview']}\n...\n```\n"

        if context.get("guidelines"):
            prompt += f"\n## Project Guidelines\n{context['guidelines']}\n"

        prompt += "\nProvide your review in JSON format."

        return prompt

    def _parse_llm_response(self, content: str) -> dict[str, Any]:
        """Parse LLM response to extract review data."""
        try:
            # Try to extract JSON from response
            # Handle markdown code blocks
            if "```json" in content:
                start = content.index("```json") + 7
                end = content.index("```", start)
                content = content[start:end].strip()
            elif "```" in content:
                start = content.index("```") + 3
                end = content.index("```", start)
                content = content[start:end].strip()

            data = json.loads(content)

            # Convert comments to proper format
            comments = []
            for c in data.get("comments", []):
                comments.append(ReviewComment(
                    file=c.get("file", ""),
                    line=c.get("line", 1),
                    end_line=c.get("end_line"),
                    body=c.get("body", ""),
                    priority=ReviewPriority(c.get("priority", "medium")),
                    category=ReviewCategory(c.get("category", "best_practice")),
                    suggestion=c.get("suggestion"),
                    code_suggestion=c.get("code_suggestion"),
                ))

            return {
                "summary": data.get("summary", ""),
                "comments": comments,
            }

        except (json.JSONDecodeError, ValueError, KeyError):
            # Return raw content as summary if parsing fails
            return {
                "summary": content[:500] if content else "Review generated",
                "comments": [],
            }

    def _generate_fallback_review(
        self,
        analysis: DiffAnalysis,
        smells: list[CodeSmell],
    ) -> dict[str, Any]:
        """Generate a basic review without LLM."""
        summary_parts = [
            f"PR changes {len(analysis.files)} files with {analysis.total_additions} additions and {analysis.total_deletions} deletions.",
        ]

        if smells:
            critical = len([s for s in smells if s.severity.value == "critical"])
            if critical:
                summary_parts.append(f"Found {critical} critical issues that need attention.")

        if analysis.is_large_pr:
            summary_parts.append("This is a large PR - consider breaking it into smaller changes.")

        return {
            "summary": " ".join(summary_parts),
            "comments": [],
        }

    def _smells_to_comments(self, smells: list[CodeSmell]) -> list[ReviewComment]:
        """Convert code smells to review comments."""
        comments = []

        severity_to_priority = {
            "critical": ReviewPriority.CRITICAL,
            "major": ReviewPriority.HIGH,
            "minor": ReviewPriority.MEDIUM,
            "info": ReviewPriority.INFO,
        }

        type_to_category = {
            "hardcoded_secret": ReviewCategory.SECURITY,
            "sql_injection": ReviewCategory.SECURITY,
            "xss_vulnerability": ReviewCategory.SECURITY,
            "insecure_random": ReviewCategory.SECURITY,
            "n_plus_one": ReviewCategory.PERFORMANCE,
            "memory_leak": ReviewCategory.PERFORMANCE,
            "inefficient_loop": ReviewCategory.PERFORMANCE,
            "long_method": ReviewCategory.MAINTAINABILITY,
            "complex_condition": ReviewCategory.MAINTAINABILITY,
            "deep_nesting": ReviewCategory.MAINTAINABILITY,
            "duplicated_code": ReviewCategory.MAINTAINABILITY,
            "magic_number": ReviewCategory.READABILITY,
            "bad_naming": ReviewCategory.READABILITY,
        }

        for smell in smells:
            comments.append(ReviewComment(
                file=smell.file,
                line=smell.line_start,
                end_line=smell.line_end,
                body=smell.message,
                priority=severity_to_priority.get(smell.severity.value, ReviewPriority.MEDIUM),
                category=type_to_category.get(smell.type.value, ReviewCategory.BEST_PRACTICE),
                suggestion=smell.suggestion,
            ))

        return comments

    def _merge_comments(
        self,
        llm_comments: list[ReviewComment],
        smell_comments: list[ReviewComment],
    ) -> list[ReviewComment]:
        """Merge and deduplicate comments from different sources."""
        # Use (file, line) as key for deduplication
        seen: dict[tuple[str, int], ReviewComment] = {}

        # Add LLM comments first (higher priority)
        for c in llm_comments:
            key = (c.file, c.line)
            seen[key] = c

        # Add smell comments if not duplicate
        for c in smell_comments:
            key = (c.file, c.line)
            if key not in seen:
                seen[key] = c
            else:
                # If same location, keep higher priority
                existing = seen[key]
                if self._priority_rank(c.priority) < self._priority_rank(existing.priority):
                    seen[key] = c

        # Sort by priority then file/line
        comments = list(seen.values())
        comments.sort(key=lambda c: (
            self._priority_rank(c.priority),
            c.file,
            c.line,
        ))

        # Apply max comments limit per file
        if self._config.max_comments_per_file:
            file_counts: dict[str, int] = {}
            filtered = []
            for c in comments:
                count = file_counts.get(c.file, 0)
                if count < self._config.max_comments_per_file:
                    filtered.append(c)
                    file_counts[c.file] = count + 1
            comments = filtered

        return comments

    def _priority_rank(self, priority: ReviewPriority) -> int:
        """Get numeric rank for priority (lower = higher priority)."""
        ranks = {
            ReviewPriority.CRITICAL: 0,
            ReviewPriority.HIGH: 1,
            ReviewPriority.MEDIUM: 2,
            ReviewPriority.LOW: 3,
            ReviewPriority.INFO: 4,
        }
        return ranks.get(priority, 5)

    def _calculate_quality(
        self,
        analysis: DiffAnalysis,
        smells: list[CodeSmell],
        comments: list[ReviewComment],
    ) -> float:
        """Calculate overall code quality score (0-10)."""
        # Start with perfect score
        score = 10.0

        # Deduct for smells
        for smell in smells:
            if smell.severity.value == "critical":
                score -= 2.0
            elif smell.severity.value == "major":
                score -= 1.0
            elif smell.severity.value == "minor":
                score -= 0.3
            else:
                score -= 0.1

        # Deduct for high-priority comments
        for comment in comments:
            if comment.priority == ReviewPriority.CRITICAL:
                score -= 1.5
            elif comment.priority == ReviewPriority.HIGH:
                score -= 0.5

        # Complexity penalty
        if analysis.complexity_score > 7:
            score -= 1.0
        elif analysis.complexity_score > 5:
            score -= 0.5

        # Risk penalty
        if analysis.risk_score > 7:
            score -= 1.0
        elif analysis.risk_score > 5:
            score -= 0.5

        # Normalize to 0-10
        return max(0.0, min(10.0, round(score, 1)))

    def _determine_recommendation(
        self,
        quality: float,
        smells: list[CodeSmell],
        comments: list[ReviewComment],
    ) -> str:
        """Determine approval recommendation."""
        # Check for blockers
        has_critical_smell = any(s.severity.value == "critical" for s in smells)
        has_critical_comment = any(c.priority == ReviewPriority.CRITICAL for c in comments)
        has_security_issue = any(c.category == ReviewCategory.SECURITY for c in comments)

        if has_critical_smell or has_critical_comment or has_security_issue:
            return "request_changes"

        if quality >= 8.0:
            return "approve"
        elif quality >= 5.0:
            return "comment"
        else:
            return "request_changes"

    def _generate_summary(self, analysis: DiffAnalysis) -> str:
        """Generate a basic summary."""
        return (
            f"Review of PR #{analysis.pr_info.number}: {analysis.pr_info.title}. "
            f"Changes span {len(analysis.files)} files with {analysis.total_changes} modifications."
        )
