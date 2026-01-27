"""
Diff Analyzer

Analyzes pull request diffs for risk assessment.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import re
import logging

logger = logging.getLogger(__name__)


class ChangeType(str, Enum):
    """Types of code changes."""
    ADDITION = "addition"
    DELETION = "deletion"
    MODIFICATION = "modification"
    RENAME = "rename"
    PERMISSION_CHANGE = "permission_change"


class RiskLevel(str, Enum):
    """Risk levels for changes."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CodeChange:
    """A single code change in a diff."""
    file_path: str
    change_type: ChangeType
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    start_line: int = 0
    end_line: int = 0
    additions: int = 0
    deletions: int = 0
    
    # Analysis results
    affected_functions: List[str] = field(default_factory=list)
    affected_classes: List[str] = field(default_factory=list)
    imports_changed: List[str] = field(default_factory=list)
    
    # Risk indicators
    risk_indicators: List[str] = field(default_factory=list)
    complexity_delta: int = 0


@dataclass
class FileAnalysis:
    """Analysis of a changed file."""
    path: str
    language: Optional[str] = None
    is_test_file: bool = False
    is_config_file: bool = False
    is_infrastructure: bool = False
    
    changes: List[CodeChange] = field(default_factory=list)
    total_additions: int = 0
    total_deletions: int = 0
    
    # Metrics
    complexity_before: Optional[int] = None
    complexity_after: Optional[int] = None
    test_coverage_impact: Optional[str] = None


@dataclass
class RiskAssessment:
    """Risk assessment for a pull request."""
    overall_risk: RiskLevel = RiskLevel.LOW
    risk_score: float = 0.0  # 0-100
    
    # Risk factors
    risk_factors: List[Dict[str, Any]] = field(default_factory=list)
    
    # Categories
    security_risks: List[str] = field(default_factory=list)
    performance_risks: List[str] = field(default_factory=list)
    maintainability_risks: List[str] = field(default_factory=list)
    breaking_change_risks: List[str] = field(default_factory=list)
    
    # Positive indicators
    positive_indicators: List[str] = field(default_factory=list)
    
    # Summary
    summary: str = ""
    recommendations: List[str] = field(default_factory=list)


class DiffAnalyzer:
    """
    Analyzes pull request diffs for risk and quality.
    
    Features:
    - Parse unified diff format
    - Detect risky patterns
    - Assess complexity changes
    - Identify affected components
    """
    
    # Risky patterns to detect
    SECURITY_PATTERNS = [
        (r"password\s*=\s*['\"][^'\"]+['\"]", "Hardcoded password detected"),
        (r"api[_-]?key\s*=\s*['\"][^'\"]+['\"]", "Hardcoded API key detected"),
        (r"secret\s*=\s*['\"][^'\"]+['\"]", "Hardcoded secret detected"),
        (r"eval\s*\(", "Use of eval() - potential code injection"),
        (r"exec\s*\(", "Use of exec() - potential code injection"),
        (r"subprocess\.call\s*\([^)]*shell\s*=\s*True", "Shell=True in subprocess - command injection risk"),
        (r"os\.system\s*\(", "os.system() - prefer subprocess"),
        (r"pickle\.loads?\s*\(", "Pickle deserialization - potential RCE"),
        (r"yaml\.load\s*\([^)]*Loader\s*=\s*None", "Unsafe YAML loading"),
        (r"\.innerHtml\s*=", "innerHTML assignment - XSS risk"),
        (r"dangerouslySetInnerHTML", "dangerouslySetInnerHTML - XSS risk"),
        (r"SELECT\s+.*\s+FROM\s+.*\s+WHERE\s+.*\+", "String concatenation in SQL - injection risk"),
    ]
    
    PERFORMANCE_PATTERNS = [
        (r"for\s+.*\s+in\s+range\s*\(\s*len\s*\(", "Iterating with range(len()) - prefer enumerate"),
        (r"\.append\s*\([^)]+\)\s*$", "Multiple appends in loop - consider list comprehension"),
        (r"time\.sleep\s*\(\s*\d{2,}\s*\)", "Long sleep detected"),
        (r"SELECT\s+\*\s+FROM", "SELECT * - specify columns for performance"),
        (r"N\+1", "Potential N+1 query pattern mentioned"),
    ]
    
    MAINTAINABILITY_PATTERNS = [
        (r"#\s*TODO\s*:", "TODO comment added"),
        (r"#\s*FIXME\s*:", "FIXME comment added"),
        (r"#\s*HACK\s*:", "HACK comment added"),
        (r"except\s*:\s*$", "Bare except clause - catch specific exceptions"),
        (r"except\s+Exception\s*:", "Catching broad Exception"),
        (r"pass\s*$", "Empty pass statement"),
        (r"print\s*\(", "Print statement - use logging instead"),
    ]
    
    # File type detection
    TEST_FILE_PATTERNS = [
        r"test_.*\.py$",
        r".*_test\.py$",
        r".*\.test\.(ts|js|tsx|jsx)$",
        r".*\.spec\.(ts|js|tsx|jsx)$",
        r"__tests__/",
    ]
    
    CONFIG_FILE_PATTERNS = [
        r"\.env",
        r"config\.",
        r"settings\.",
        r"\.yaml$",
        r"\.yml$",
        r"\.json$",
        r"\.toml$",
    ]
    
    INFRASTRUCTURE_PATTERNS = [
        r"Dockerfile",
        r"docker-compose",
        r"\.tf$",
        r"kubernetes/",
        r"k8s/",
        r"helm/",
        r"\.github/workflows/",
        r"Jenkinsfile",
    ]
    
    def __init__(self):
        self._compiled_security = [(re.compile(p, re.IGNORECASE), m) for p, m in self.SECURITY_PATTERNS]
        self._compiled_performance = [(re.compile(p, re.IGNORECASE), m) for p, m in self.PERFORMANCE_PATTERNS]
        self._compiled_maintainability = [(re.compile(p, re.IGNORECASE), m) for p, m in self.MAINTAINABILITY_PATTERNS]
    
    def analyze_pr(
        self,
        diff_text: str,
        pr_metadata: Optional[Dict[str, Any]] = None,
    ) -> tuple[List[FileAnalysis], RiskAssessment]:
        """
        Analyze a pull request diff.
        
        Args:
            diff_text: Unified diff format text
            pr_metadata: Optional PR metadata (title, description, etc.)
            
        Returns:
            Tuple of (file analyses, risk assessment)
        """
        # Parse diff into file changes
        file_analyses = self._parse_diff(diff_text)
        
        # Analyze each file
        for analysis in file_analyses:
            self._analyze_file(analysis)
        
        # Generate risk assessment
        risk = self._assess_risk(file_analyses, pr_metadata)
        
        return file_analyses, risk
    
    def _parse_diff(self, diff_text: str) -> List[FileAnalysis]:
        """Parse unified diff format into structured data."""
        files: List[FileAnalysis] = []
        current_file: Optional[FileAnalysis] = None
        current_change: Optional[CodeChange] = None
        
        lines = diff_text.split("\n")
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # New file header
            if line.startswith("diff --git"):
                if current_file:
                    files.append(current_file)
                
                # Extract file path
                match = re.search(r"b/(.+)$", line)
                path = match.group(1) if match else "unknown"
                
                current_file = FileAnalysis(
                    path=path,
                    language=self._detect_language(path),
                    is_test_file=self._is_test_file(path),
                    is_config_file=self._is_config_file(path),
                    is_infrastructure=self._is_infrastructure_file(path),
                )
                current_change = None
            
            # Hunk header
            elif line.startswith("@@") and current_file:
                match = re.match(r"@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@", line)
                if match:
                    if current_change:
                        current_file.changes.append(current_change)
                    
                    current_change = CodeChange(
                        file_path=current_file.path,
                        change_type=ChangeType.MODIFICATION,
                        start_line=int(match.group(3)),
                        end_line=int(match.group(3)),
                    )
            
            # Addition
            elif line.startswith("+") and not line.startswith("+++") and current_change:
                current_change.additions += 1
                current_file.total_additions += 1
                if current_change.new_content is None:
                    current_change.new_content = ""
                current_change.new_content += line[1:] + "\n"
            
            # Deletion
            elif line.startswith("-") and not line.startswith("---") and current_change:
                current_change.deletions += 1
                current_file.total_deletions += 1
                if current_change.old_content is None:
                    current_change.old_content = ""
                current_change.old_content += line[1:] + "\n"
            
            i += 1
        
        # Don't forget the last file
        if current_file:
            if current_change:
                current_file.changes.append(current_change)
            files.append(current_file)
        
        return files
    
    def _analyze_file(self, analysis: FileAnalysis) -> None:
        """Analyze a single file's changes."""
        for change in analysis.changes:
            content = (change.new_content or "") + (change.old_content or "")
            
            # Check for risky patterns in new content only
            new_content = change.new_content or ""
            
            # Security patterns
            for pattern, message in self._compiled_security:
                if pattern.search(new_content):
                    change.risk_indicators.append(f"SECURITY: {message}")
            
            # Performance patterns
            for pattern, message in self._compiled_performance:
                if pattern.search(new_content):
                    change.risk_indicators.append(f"PERFORMANCE: {message}")
            
            # Maintainability patterns
            for pattern, message in self._compiled_maintainability:
                if pattern.search(new_content):
                    change.risk_indicators.append(f"MAINTAINABILITY: {message}")
            
            # Extract affected functions/classes
            change.affected_functions = self._extract_functions(content, analysis.language)
            change.affected_classes = self._extract_classes(content, analysis.language)
            change.imports_changed = self._extract_imports(content, analysis.language)
    
    def _assess_risk(
        self,
        files: List[FileAnalysis],
        pr_metadata: Optional[Dict[str, Any]],
    ) -> RiskAssessment:
        """Generate overall risk assessment."""
        assessment = RiskAssessment()
        
        total_additions = sum(f.total_additions for f in files)
        total_deletions = sum(f.total_deletions for f in files)
        total_files = len(files)
        
        # Collect all risk indicators
        all_indicators = []
        for f in files:
            for change in f.changes:
                all_indicators.extend(change.risk_indicators)
        
        # Categorize risks
        for indicator in all_indicators:
            if indicator.startswith("SECURITY:"):
                assessment.security_risks.append(indicator.replace("SECURITY: ", ""))
            elif indicator.startswith("PERFORMANCE:"):
                assessment.performance_risks.append(indicator.replace("PERFORMANCE: ", ""))
            elif indicator.startswith("MAINTAINABILITY:"):
                assessment.maintainability_risks.append(indicator.replace("MAINTAINABILITY: ", ""))
        
        # Calculate risk score
        score = 0.0
        
        # Size-based risk
        if total_additions + total_deletions > 1000:
            score += 20
            assessment.risk_factors.append({
                "factor": "Large change size",
                "details": f"{total_additions} additions, {total_deletions} deletions",
                "weight": 20,
            })
        elif total_additions + total_deletions > 500:
            score += 10
        elif total_additions + total_deletions > 200:
            score += 5
        
        # Files changed risk
        if total_files > 20:
            score += 15
            assessment.risk_factors.append({
                "factor": "Many files changed",
                "details": f"{total_files} files",
                "weight": 15,
            })
        elif total_files > 10:
            score += 8
        
        # Security risks (highest weight)
        if assessment.security_risks:
            score += len(assessment.security_risks) * 15
            assessment.risk_factors.append({
                "factor": "Security concerns",
                "details": assessment.security_risks,
                "weight": len(assessment.security_risks) * 15,
            })
        
        # Infrastructure/config changes
        infra_files = [f for f in files if f.is_infrastructure or f.is_config_file]
        if infra_files:
            score += len(infra_files) * 10
            assessment.risk_factors.append({
                "factor": "Infrastructure/config changes",
                "details": [f.path for f in infra_files],
                "weight": len(infra_files) * 10,
            })
        
        # Check for tests
        test_files = [f for f in files if f.is_test_file]
        if test_files:
            assessment.positive_indicators.append(f"Includes {len(test_files)} test file(s)")
            score -= 10  # Reduce risk if tests included
        elif total_additions > 100:
            assessment.recommendations.append("Consider adding tests for new code")
            score += 5
        
        # Performance risks
        if assessment.performance_risks:
            score += len(assessment.performance_risks) * 5
        
        # Maintainability
        if assessment.maintainability_risks:
            score += len(assessment.maintainability_risks) * 3
        
        # Clamp score
        assessment.risk_score = max(0, min(100, score))
        
        # Determine overall level
        if assessment.risk_score >= 70 or assessment.security_risks:
            assessment.overall_risk = RiskLevel.CRITICAL if assessment.security_risks else RiskLevel.HIGH
        elif assessment.risk_score >= 40:
            assessment.overall_risk = RiskLevel.MEDIUM
        else:
            assessment.overall_risk = RiskLevel.LOW
        
        # Generate summary
        assessment.summary = self._generate_summary(assessment, files)
        
        # Add recommendations
        if assessment.security_risks:
            assessment.recommendations.insert(0, "Address security concerns before merging")
        if not test_files and total_additions > 50:
            assessment.recommendations.append("Add unit tests for new functionality")
        if total_files > 15:
            assessment.recommendations.append("Consider splitting into smaller PRs")
        
        return assessment
    
    def _generate_summary(self, assessment: RiskAssessment, files: List[FileAnalysis]) -> str:
        """Generate human-readable summary."""
        total_additions = sum(f.total_additions for f in files)
        total_deletions = sum(f.total_deletions for f in files)
        
        summary_parts = [
            f"This PR modifies {len(files)} file(s) with +{total_additions}/-{total_deletions} lines.",
        ]
        
        if assessment.overall_risk == RiskLevel.CRITICAL:
            summary_parts.append("⚠️ CRITICAL: Security issues detected that require immediate attention.")
        elif assessment.overall_risk == RiskLevel.HIGH:
            summary_parts.append("⚠️ HIGH RISK: Significant changes that warrant careful review.")
        elif assessment.overall_risk == RiskLevel.MEDIUM:
            summary_parts.append("⚡ MEDIUM RISK: Some areas need attention during review.")
        else:
            summary_parts.append("✅ LOW RISK: Straightforward changes.")
        
        if assessment.positive_indicators:
            summary_parts.append(f"Positive: {', '.join(assessment.positive_indicators)}")
        
        return " ".join(summary_parts)
    
    def _detect_language(self, path: str) -> Optional[str]:
        """Detect programming language from file path."""
        extensions = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".jsx": "javascript",
            ".go": "go",
            ".rs": "rust",
            ".java": "java",
            ".rb": "ruby",
            ".php": "php",
            ".cs": "csharp",
            ".cpp": "cpp",
            ".c": "c",
        }
        for ext, lang in extensions.items():
            if path.endswith(ext):
                return lang
        return None
    
    def _is_test_file(self, path: str) -> bool:
        """Check if file is a test file."""
        return any(re.search(p, path) for p in self.TEST_FILE_PATTERNS)
    
    def _is_config_file(self, path: str) -> bool:
        """Check if file is a config file."""
        return any(re.search(p, path, re.IGNORECASE) for p in self.CONFIG_FILE_PATTERNS)
    
    def _is_infrastructure_file(self, path: str) -> bool:
        """Check if file is infrastructure-related."""
        return any(re.search(p, path, re.IGNORECASE) for p in self.INFRASTRUCTURE_PATTERNS)
    
    def _extract_functions(self, content: str, language: Optional[str]) -> List[str]:
        """Extract function names from content."""
        functions = []
        
        if language == "python":
            functions = re.findall(r"def\s+(\w+)\s*\(", content)
        elif language in ("javascript", "typescript"):
            functions = re.findall(r"(?:function\s+(\w+)|(\w+)\s*=\s*(?:async\s+)?(?:function|\([^)]*\)\s*=>))", content)
            functions = [f[0] or f[1] for f in functions if f[0] or f[1]]
        elif language == "go":
            functions = re.findall(r"func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(", content)
        
        return functions
    
    def _extract_classes(self, content: str, language: Optional[str]) -> List[str]:
        """Extract class names from content."""
        if language == "python":
            return re.findall(r"class\s+(\w+)", content)
        elif language in ("javascript", "typescript"):
            return re.findall(r"class\s+(\w+)", content)
        elif language == "java":
            return re.findall(r"class\s+(\w+)", content)
        return []
    
    def _extract_imports(self, content: str, language: Optional[str]) -> List[str]:
        """Extract import statements from content."""
        imports = []
        
        if language == "python":
            imports = re.findall(r"(?:from\s+(\S+)\s+import|import\s+(\S+))", content)
            imports = [i[0] or i[1] for i in imports]
        elif language in ("javascript", "typescript"):
            imports = re.findall(r"import\s+.*?from\s+['\"]([^'\"]+)['\"]", content)
        elif language == "go":
            imports = re.findall(r"import\s+['\"]([^'\"]+)['\"]", content)
        
        return imports
