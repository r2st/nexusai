"""
Review Generator

Generates PR review comments using LLM.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import logging

from .analyzer import FileAnalysis, RiskAssessment, CodeChange, RiskLevel

logger = logging.getLogger(__name__)


class ReviewSeverity(str, Enum):
    """Severity of review comments."""
    PRAISE = "praise"
    SUGGESTION = "suggestion"
    WARNING = "warning"
    CRITICAL = "critical"
    QUESTION = "question"


class ReviewCategory(str, Enum):
    """Category of review comments."""
    SECURITY = "security"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    STYLE = "style"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    LOGIC = "logic"
    BEST_PRACTICE = "best_practice"


@dataclass
class ReviewComment:
    """A single review comment."""
    file_path: str
    line_number: Optional[int] = None
    line_end: Optional[int] = None
    
    severity: ReviewSeverity = ReviewSeverity.SUGGESTION
    category: ReviewCategory = ReviewCategory.BEST_PRACTICE
    
    title: str = ""
    body: str = ""
    suggestion: Optional[str] = None  # Code suggestion
    
    # Metadata
    confidence: float = 0.8
    auto_generated: bool = True


@dataclass
class ReviewSummary:
    """Summary of the entire review."""
    overall_assessment: str = ""
    risk_level: RiskLevel = RiskLevel.LOW
    
    # Counts
    total_comments: int = 0
    critical_count: int = 0
    warning_count: int = 0
    suggestion_count: int = 0
    praise_count: int = 0
    
    # Key points
    key_concerns: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    
    # Recommendations
    must_fix: List[str] = field(default_factory=list)
    should_consider: List[str] = field(default_factory=list)
    
    # Approval recommendation
    recommend_approval: bool = True
    approval_conditions: List[str] = field(default_factory=list)


class ReviewGenerator:
    """
    Generates comprehensive PR reviews.
    
    Features:
    - LLM-powered code analysis
    - Pattern-based issue detection
    - Contextual suggestions
    - Review summary generation
    """
    
    # Common patterns for generating comments
    PATTERN_COMMENTS = {
        "SECURITY: Hardcoded password detected": {
            "title": "Hardcoded Credentials",
            "body": "Credentials should not be hardcoded in source code. Use environment variables or a secrets manager.",
            "category": ReviewCategory.SECURITY,
            "severity": ReviewSeverity.CRITICAL,
        },
        "SECURITY: Hardcoded API key detected": {
            "title": "Exposed API Key",
            "body": "API keys should be stored securely, not in source code. Consider using environment variables or a vault.",
            "category": ReviewCategory.SECURITY,
            "severity": ReviewSeverity.CRITICAL,
        },
        "SECURITY: Use of eval()": {
            "title": "Dangerous eval() Usage",
            "body": "eval() can execute arbitrary code and is a security risk. Consider using safer alternatives like ast.literal_eval() for Python or JSON.parse() for JavaScript.",
            "category": ReviewCategory.SECURITY,
            "severity": ReviewSeverity.CRITICAL,
        },
        "SECURITY: Shell=True in subprocess": {
            "title": "Shell Injection Risk",
            "body": "Using shell=True in subprocess can lead to command injection. Pass arguments as a list instead.",
            "category": ReviewCategory.SECURITY,
            "severity": ReviewSeverity.WARNING,
        },
        "PERFORMANCE: SELECT * - specify columns": {
            "title": "Inefficient SQL Query",
            "body": "SELECT * retrieves all columns, which can be inefficient. Specify only the columns you need.",
            "category": ReviewCategory.PERFORMANCE,
            "severity": ReviewSeverity.SUGGESTION,
        },
        "MAINTAINABILITY: Bare except clause": {
            "title": "Overly Broad Exception Handler",
            "body": "Bare except clauses catch all exceptions including KeyboardInterrupt and SystemExit. Catch specific exceptions instead.",
            "category": ReviewCategory.MAINTAINABILITY,
            "severity": ReviewSeverity.WARNING,
        },
        "MAINTAINABILITY: Print statement": {
            "title": "Debug Print Statement",
            "body": "Consider using a logging framework instead of print statements for production code.",
            "category": ReviewCategory.MAINTAINABILITY,
            "severity": ReviewSeverity.SUGGESTION,
        },
    }
    
    def __init__(self, llm_service=None):
        """
        Initialize the review generator.
        
        Args:
            llm_service: Optional LLM service for advanced analysis
        """
        self.llm_service = llm_service
    
    def generate_review(
        self,
        files: List[FileAnalysis],
        risk_assessment: RiskAssessment,
        context: Optional[Dict[str, Any]] = None,
    ) -> tuple[List[ReviewComment], ReviewSummary]:
        """
        Generate a complete PR review.
        
        Args:
            files: Analyzed file changes
            risk_assessment: Risk assessment results
            context: Additional context (PR description, commit messages, etc.)
            
        Returns:
            Tuple of (comments, summary)
        """
        comments: List[ReviewComment] = []
        
        # Generate comments from pattern detection
        for file_analysis in files:
            file_comments = self._generate_file_comments(file_analysis)
            comments.extend(file_comments)
        
        # Generate comments from risk assessment
        risk_comments = self._generate_risk_comments(risk_assessment)
        comments.extend(risk_comments)
        
        # Use LLM for deeper analysis if available
        if self.llm_service:
            llm_comments = self._generate_llm_comments(files, context)
            comments.extend(llm_comments)
        
        # Generate praise for good practices
        praise_comments = self._generate_praise(files, risk_assessment)
        comments.extend(praise_comments)
        
        # Create summary
        summary = self._generate_summary(files, risk_assessment, comments)
        
        return comments, summary
    
    def _generate_file_comments(self, file_analysis: FileAnalysis) -> List[ReviewComment]:
        """Generate comments for a single file."""
        comments = []
        
        for change in file_analysis.changes:
            for indicator in change.risk_indicators:
                # Look up pattern comment
                for pattern_key, comment_template in self.PATTERN_COMMENTS.items():
                    if pattern_key in indicator:
                        comments.append(ReviewComment(
                            file_path=file_analysis.path,
                            line_number=change.start_line,
                            line_end=change.end_line,
                            severity=comment_template["severity"],
                            category=comment_template["category"],
                            title=comment_template["title"],
                            body=comment_template["body"],
                        ))
                        break
                else:
                    # Generic comment for unrecognized patterns
                    severity = ReviewSeverity.WARNING if "SECURITY" in indicator else ReviewSeverity.SUGGESTION
                    category = (
                        ReviewCategory.SECURITY if "SECURITY" in indicator
                        else ReviewCategory.PERFORMANCE if "PERFORMANCE" in indicator
                        else ReviewCategory.MAINTAINABILITY
                    )
                    comments.append(ReviewComment(
                        file_path=file_analysis.path,
                        line_number=change.start_line,
                        severity=severity,
                        category=category,
                        title="Potential Issue Detected",
                        body=indicator,
                    ))
        
        return comments
    
    def _generate_risk_comments(self, risk_assessment: RiskAssessment) -> List[ReviewComment]:
        """Generate comments based on risk assessment."""
        comments = []
        
        # Security risks
        for risk in risk_assessment.security_risks:
            comments.append(ReviewComment(
                file_path="",  # General comment
                severity=ReviewSeverity.CRITICAL,
                category=ReviewCategory.SECURITY,
                title="Security Risk",
                body=risk,
                confidence=0.9,
            ))
        
        # Breaking change risks
        for risk in risk_assessment.breaking_change_risks:
            comments.append(ReviewComment(
                file_path="",
                severity=ReviewSeverity.WARNING,
                category=ReviewCategory.LOGIC,
                title="Potential Breaking Change",
                body=risk,
            ))
        
        return comments
    
    def _generate_llm_comments(
        self,
        files: List[FileAnalysis],
        context: Optional[Dict[str, Any]],
    ) -> List[ReviewComment]:
        """Generate comments using LLM analysis."""
        comments = []
        
        # This would integrate with the LLM service
        # For now, return empty list
        # In production, this would:
        # 1. Build a prompt with code changes
        # 2. Ask LLM to identify issues
        # 3. Parse LLM response into ReviewComments
        
        return comments
    
    def _generate_praise(
        self,
        files: List[FileAnalysis],
        risk_assessment: RiskAssessment,
    ) -> List[ReviewComment]:
        """Generate positive feedback for good practices."""
        comments = []
        
        # Praise for test files
        test_files = [f for f in files if f.is_test_file]
        if test_files:
            comments.append(ReviewComment(
                file_path=test_files[0].path,
                severity=ReviewSeverity.PRAISE,
                category=ReviewCategory.TESTING,
                title="Good: Tests Included",
                body=f"Thanks for including {len(test_files)} test file(s) with this change! This helps ensure the code works as expected.",
            ))
        
        # Praise for documentation
        doc_files = [f for f in files if f.path.endswith(".md") or "docs/" in f.path]
        if doc_files:
            comments.append(ReviewComment(
                file_path=doc_files[0].path,
                severity=ReviewSeverity.PRAISE,
                category=ReviewCategory.DOCUMENTATION,
                title="Good: Documentation Updated",
                body="Thanks for keeping documentation in sync with code changes!",
            ))
        
        # Praise for small, focused PRs
        total_changes = sum(f.total_additions + f.total_deletions for f in files)
        if len(files) <= 5 and total_changes <= 200:
            comments.append(ReviewComment(
                file_path="",
                severity=ReviewSeverity.PRAISE,
                category=ReviewCategory.BEST_PRACTICE,
                title="Good: Focused Change",
                body="This PR is well-scoped and focused, making it easier to review. Thank you!",
            ))
        
        return comments
    
    def _generate_summary(
        self,
        files: List[FileAnalysis],
        risk_assessment: RiskAssessment,
        comments: List[ReviewComment],
    ) -> ReviewSummary:
        """Generate the overall review summary."""
        summary = ReviewSummary()
        
        # Count comments by severity
        summary.total_comments = len(comments)
        summary.critical_count = sum(1 for c in comments if c.severity == ReviewSeverity.CRITICAL)
        summary.warning_count = sum(1 for c in comments if c.severity == ReviewSeverity.WARNING)
        summary.suggestion_count = sum(1 for c in comments if c.severity == ReviewSeverity.SUGGESTION)
        summary.praise_count = sum(1 for c in comments if c.severity == ReviewSeverity.PRAISE)
        
        # Set risk level
        summary.risk_level = risk_assessment.overall_risk
        
        # Extract key concerns
        critical_comments = [c for c in comments if c.severity == ReviewSeverity.CRITICAL]
        summary.key_concerns = [c.title for c in critical_comments[:5]]
        
        # Extract strengths
        praise_comments = [c for c in comments if c.severity == ReviewSeverity.PRAISE]
        summary.strengths = [c.title for c in praise_comments]
        
        # Must fix items
        summary.must_fix = [c.body for c in critical_comments]
        
        # Should consider items
        warning_comments = [c for c in comments if c.severity == ReviewSeverity.WARNING]
        summary.should_consider = [c.body for c in warning_comments[:5]]
        
        # Approval recommendation
        if summary.critical_count > 0:
            summary.recommend_approval = False
            summary.approval_conditions = ["Address critical security issues"]
        elif summary.warning_count > 5:
            summary.recommend_approval = False
            summary.approval_conditions = ["Review and address warnings"]
        else:
            summary.recommend_approval = True
        
        # Generate overall assessment
        total_changes = sum(f.total_additions + f.total_deletions for f in files)
        summary.overall_assessment = self._write_assessment(
            files_count=len(files),
            total_changes=total_changes,
            risk_level=risk_assessment.overall_risk,
            critical_count=summary.critical_count,
            warning_count=summary.warning_count,
            has_tests=any(f.is_test_file for f in files),
        )
        
        return summary
    
    def _write_assessment(
        self,
        files_count: int,
        total_changes: int,
        risk_level: RiskLevel,
        critical_count: int,
        warning_count: int,
        has_tests: bool,
    ) -> str:
        """Write the overall assessment text."""
        parts = []
        
        # Size summary
        parts.append(f"This PR changes {files_count} file(s) with {total_changes} line changes.")
        
        # Risk assessment
        if risk_level == RiskLevel.CRITICAL:
            parts.append("🚨 **Critical issues found** that must be addressed before merging.")
        elif risk_level == RiskLevel.HIGH:
            parts.append("⚠️ **High risk change** - careful review recommended.")
        elif risk_level == RiskLevel.MEDIUM:
            parts.append("⚡ **Moderate complexity** - some areas need attention.")
        else:
            parts.append("✅ **Low risk** - straightforward changes.")
        
        # Issues summary
        if critical_count > 0:
            parts.append(f"\n\n**Issues:** {critical_count} critical, {warning_count} warnings")
        elif warning_count > 0:
            parts.append(f"\n\n**Issues:** {warning_count} warning(s) to review")
        
        # Test status
        if has_tests:
            parts.append("\n\n✓ Includes test coverage")
        elif total_changes > 100:
            parts.append("\n\n⚠️ No tests included - consider adding test coverage")
        
        return " ".join(parts)


def format_review_for_github(
    comments: List[ReviewComment],
    summary: ReviewSummary,
) -> Dict[str, Any]:
    """Format review for GitHub PR Review API."""
    
    # Build event type
    if not summary.recommend_approval:
        event = "REQUEST_CHANGES"
    elif summary.critical_count > 0 or summary.warning_count > 0:
        event = "COMMENT"
    else:
        event = "APPROVE"
    
    # Format inline comments
    inline_comments = []
    for comment in comments:
        if comment.file_path and comment.line_number:
            inline_comments.append({
                "path": comment.file_path,
                "line": comment.line_number,
                "body": f"**{comment.title}**\n\n{comment.body}",
            })
    
    return {
        "event": event,
        "body": summary.overall_assessment,
        "comments": inline_comments,
    }
