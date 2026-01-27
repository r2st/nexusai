"""
Technical Debt Analyzers

Specialized analyzers for different types of technical debt.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

from .models import (
    DebtCategory,
    DebtSeverity,
    DebtItem,
    DebtConfig,
)

logger = logging.getLogger(__name__)


class BaseDebtAnalyzer(ABC):
    """Base class for debt analyzers."""
    
    category: DebtCategory
    
    @abstractmethod
    def analyze(self, code_data: dict, config: DebtConfig) -> list[DebtItem]:
        """Analyze code for technical debt."""
        pass
    
    def _create_debt_item(
        self,
        title: str,
        description: str,
        file_path: str,
        severity: DebtSeverity,
        effort_hours: float,
        **kwargs,
    ) -> DebtItem:
        """Create a debt item with common fields."""
        import uuid
        return DebtItem(
            id=str(uuid.uuid4()),
            category=self.category,
            severity=severity,
            title=title,
            description=description,
            file_path=file_path,
            effort_hours=effort_hours,
            **kwargs,
        )


class ComplexityAnalyzer(BaseDebtAnalyzer):
    """Analyzes code complexity debt."""
    
    category = DebtCategory.COMPLEXITY
    
    def analyze(self, code_data: dict, config: DebtConfig) -> list[DebtItem]:
        """Analyze complexity-related debt."""
        items = []
        
        for module in code_data.get("modules", []):
            file_path = module.get("path", "")
            
            for func in module.get("functions", []):
                complexity = func.get("complexity", 0)
                
                if complexity > config.complexity_threshold:
                    severity = self._get_complexity_severity(complexity, config)
                    effort = self._estimate_complexity_effort(complexity, config)
                    
                    items.append(self._create_debt_item(
                        title=f"High complexity in {func.get('name', 'function')}",
                        description=(
                            f"Function has cyclomatic complexity of {complexity}, "
                            f"which exceeds threshold of {config.complexity_threshold}. "
                            f"Consider breaking into smaller functions."
                        ),
                        file_path=file_path,
                        severity=severity,
                        effort_hours=effort,
                        line_start=func.get("line_start"),
                        line_end=func.get("line_end"),
                        impact_score=min(complexity * 3, 100),
                        fix_suggestion=(
                            "Extract complex logic into separate functions, "
                            "reduce nested conditions, and simplify control flow."
                        ),
                        tags=["complexity", "refactor"],
                    ))
            
            # Check class complexity
            for cls in module.get("classes", []):
                methods = cls.get("methods", [])
                total_complexity = sum(m.get("complexity", 0) for m in methods)
                
                if total_complexity > config.complexity_threshold * 3:
                    items.append(self._create_debt_item(
                        title=f"Complex class: {cls.get('name', 'Class')}",
                        description=(
                            f"Class has total complexity of {total_complexity}. "
                            f"Consider splitting into smaller, focused classes."
                        ),
                        file_path=file_path,
                        severity=DebtSeverity.HIGH,
                        effort_hours=total_complexity * 0.5,
                        line_start=cls.get("line_start"),
                        impact_score=min(total_complexity, 100),
                        fix_suggestion="Apply Single Responsibility Principle.",
                        tags=["complexity", "class", "refactor"],
                    ))
        
        return items
    
    def _get_complexity_severity(self, complexity: int, config: DebtConfig) -> DebtSeverity:
        """Map complexity to severity."""
        threshold = config.complexity_threshold
        if complexity > threshold * 3:
            return DebtSeverity.CRITICAL
        elif complexity > threshold * 2:
            return DebtSeverity.HIGH
        elif complexity > threshold * 1.5:
            return DebtSeverity.MEDIUM
        else:
            return DebtSeverity.LOW
    
    def _estimate_complexity_effort(self, complexity: int, config: DebtConfig) -> float:
        """Estimate hours to reduce complexity."""
        threshold = config.complexity_threshold
        excess = complexity - threshold
        return max(excess * 0.5, 0.5)  # At least 30 minutes


class DuplicationAnalyzer(BaseDebtAnalyzer):
    """Analyzes code duplication debt."""
    
    category = DebtCategory.DUPLICATION
    
    def analyze(self, code_data: dict, config: DebtConfig) -> list[DebtItem]:
        """Analyze duplication-related debt."""
        items = []
        
        for dup in code_data.get("duplications", []):
            lines = dup.get("lines", 0)
            occurrences = dup.get("occurrences", 2)
            files = dup.get("files", [])
            
            # Calculate duplication percentage
            total_lines = code_data.get("total_lines", 1)
            dup_percentage = (lines * occurrences / total_lines) * 100
            
            if dup_percentage > config.duplication_threshold:
                severity = self._get_duplication_severity(dup_percentage)
                
                items.append(self._create_debt_item(
                    title=f"Code duplication ({occurrences} occurrences)",
                    description=(
                        f"Found {lines} lines duplicated across {occurrences} locations. "
                        f"Files: {', '.join(files[:3])}"
                    ),
                    file_path=files[0] if files else "",
                    severity=severity,
                    effort_hours=lines * 0.1,  # 6 minutes per line
                    impact_score=min(dup_percentage * 2, 100),
                    fix_suggestion=(
                        "Extract duplicated code into a shared function or class. "
                        "Consider using inheritance or composition patterns."
                    ),
                    affected_components=files,
                    tags=["duplication", "dry"],
                ))
        
        # Check overall duplication
        overall_dup = code_data.get("duplication_percentage", 0)
        if overall_dup > config.duplication_threshold:
            items.append(self._create_debt_item(
                title=f"High overall code duplication: {overall_dup:.1f}%",
                description=(
                    f"Project has {overall_dup:.1f}% code duplication, "
                    f"exceeding threshold of {config.duplication_threshold}%."
                ),
                file_path="project",
                severity=DebtSeverity.HIGH if overall_dup > 10 else DebtSeverity.MEDIUM,
                effort_hours=overall_dup * 2,  # Rough estimate
                impact_score=min(overall_dup * 5, 100),
                tags=["duplication", "project-wide"],
            ))
        
        return items
    
    def _get_duplication_severity(self, percentage: float) -> DebtSeverity:
        """Map duplication percentage to severity."""
        if percentage > 20:
            return DebtSeverity.CRITICAL
        elif percentage > 10:
            return DebtSeverity.HIGH
        elif percentage > 5:
            return DebtSeverity.MEDIUM
        else:
            return DebtSeverity.LOW


class CoverageAnalyzer(BaseDebtAnalyzer):
    """Analyzes test coverage debt."""
    
    category = DebtCategory.COVERAGE
    
    def analyze(self, code_data: dict, config: DebtConfig) -> list[DebtItem]:
        """Analyze coverage-related debt."""
        items = []
        
        overall_coverage = code_data.get("test_coverage", 100)
        
        if overall_coverage < config.coverage_threshold:
            gap = config.coverage_threshold - overall_coverage
            
            items.append(self._create_debt_item(
                title=f"Low test coverage: {overall_coverage:.1f}%",
                description=(
                    f"Test coverage is {overall_coverage:.1f}%, "
                    f"which is {gap:.1f}% below the threshold of {config.coverage_threshold}%."
                ),
                file_path="project",
                severity=self._get_coverage_severity(overall_coverage),
                effort_hours=gap * 0.5,  # Rough: 30 min per percentage point
                impact_score=gap,
                fix_suggestion="Add unit tests for uncovered code paths.",
                tags=["coverage", "testing"],
            ))
        
        # Check individual files
        for file_data in code_data.get("file_coverage", []):
            file_coverage = file_data.get("coverage", 100)
            file_path = file_data.get("path", "")
            
            if file_coverage < config.coverage_threshold * 0.5:  # Very low
                items.append(self._create_debt_item(
                    title=f"Very low coverage in {file_path.split('/')[-1]}",
                    description=(
                        f"File has only {file_coverage:.1f}% test coverage. "
                        f"This is a high-risk area for bugs."
                    ),
                    file_path=file_path,
                    severity=DebtSeverity.HIGH,
                    effort_hours=(100 - file_coverage) * 0.1,
                    impact_score=100 - file_coverage,
                    fix_suggestion="Prioritize adding tests for this file.",
                    tags=["coverage", "high-risk"],
                ))
        
        return items
    
    def _get_coverage_severity(self, coverage: float) -> DebtSeverity:
        """Map coverage percentage to severity."""
        if coverage < 30:
            return DebtSeverity.CRITICAL
        elif coverage < 50:
            return DebtSeverity.HIGH
        elif coverage < 70:
            return DebtSeverity.MEDIUM
        else:
            return DebtSeverity.LOW


class DependencyAnalyzer(BaseDebtAnalyzer):
    """Analyzes dependency-related debt."""
    
    category = DebtCategory.DEPENDENCY
    
    def analyze(self, code_data: dict, config: DebtConfig) -> list[DebtItem]:
        """Analyze dependency-related debt."""
        items = []
        
        # Check for outdated dependencies
        for dep in code_data.get("dependencies", []):
            name = dep.get("name", "")
            current = dep.get("current_version", "")
            latest = dep.get("latest_version", "")
            
            if dep.get("outdated", False):
                severity = DebtSeverity.HIGH if dep.get("has_security_issues") else DebtSeverity.MEDIUM
                
                items.append(self._create_debt_item(
                    title=f"Outdated dependency: {name}",
                    description=(
                        f"{name} is at version {current}, but {latest} is available. "
                        f"{'Security issues found!' if dep.get('has_security_issues') else ''}"
                    ),
                    file_path="requirements.txt",
                    severity=severity,
                    effort_hours=0.5,  # 30 minutes to update and test
                    impact_score=50 if dep.get("has_security_issues") else 20,
                    fix_suggestion=f"Update {name} to version {latest}",
                    tags=["dependency", "outdated"],
                ))
        
        # Check for circular dependencies
        for circular in code_data.get("circular_dependencies", []):
            items.append(self._create_debt_item(
                title=f"Circular dependency detected",
                description=f"Circular import: {' -> '.join(circular)}",
                file_path=circular[0] if circular else "",
                severity=DebtSeverity.HIGH,
                effort_hours=2.0,
                impact_score=70,
                fix_suggestion="Refactor to break the circular dependency.",
                affected_components=circular,
                tags=["dependency", "circular"],
            ))
        
        # Check coupling
        for module in code_data.get("modules", []):
            coupling = module.get("afferent_coupling", 0)  # Incoming dependencies
            if coupling > 10:
                items.append(self._create_debt_item(
                    title=f"High coupling: {module.get('name', 'module')}",
                    description=f"Module has {coupling} incoming dependencies.",
                    file_path=module.get("path", ""),
                    severity=DebtSeverity.MEDIUM,
                    effort_hours=coupling * 0.3,
                    impact_score=min(coupling * 5, 100),
                    fix_suggestion="Consider splitting this module or using interfaces.",
                    tags=["coupling", "architecture"],
                ))
        
        return items
