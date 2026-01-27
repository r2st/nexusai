"""
Technical Debt Service

Main service for technical debt quantification and reporting.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Any
from functools import lru_cache

from .models import (
    DebtCategory,
    DebtSeverity,
    DebtItem,
    DebtMetrics,
    DebtTrend,
    DebtReport,
    RefactoringRecommendation,
    DebtConfig,
    QualityGateResult,
)
from .analyzers import (
    ComplexityAnalyzer,
    DuplicationAnalyzer,
    CoverageAnalyzer,
    DependencyAnalyzer,
)

logger = logging.getLogger(__name__)


class TechnicalDebtService:
    """
    Service for technical debt quantification and management.
    
    Capabilities:
    - Debt quantification across multiple categories
    - Trend tracking over time
    - Quality gate enforcement
    - AI-powered refactoring recommendations
    - Cost estimation
    """
    
    def __init__(self, llm_service: Optional[Any] = None):
        self.llm_service = llm_service
        self.analyzers = [
            ComplexityAnalyzer(),
            DuplicationAnalyzer(),
            CoverageAnalyzer(),
            DependencyAnalyzer(),
        ]
    
    async def analyze_debt(
        self,
        code_data: dict,
        config: DebtConfig,
    ) -> DebtReport:
        """
        Analyze technical debt in a codebase.
        
        Args:
            code_data: Code analysis data
            config: Analysis configuration
            
        Returns:
            Comprehensive debt report
        """
        start_time = time.time()
        
        # Collect all debt items
        all_items: list[DebtItem] = []
        
        for analyzer in self.analyzers:
            if analyzer.category in config.categories:
                try:
                    items = analyzer.analyze(code_data, config)
                    all_items.extend(items)
                except Exception as e:
                    logger.error(f"Analyzer {analyzer.category} failed: {e}")
        
        # Filter by exclusions
        all_items = self._filter_items(all_items, config)
        
        # Calculate metrics
        metrics = self._calculate_metrics(all_items, code_data, config)
        
        # Get quality gate result
        quality_gate = self._check_quality_gate(metrics, config)
        
        # Generate recommendations
        recommendations = await self._generate_recommendations(all_items, code_data, config)
        
        # Build report
        report = DebtReport(
            project_id=code_data.get("project_id", ""),
            project_name=code_data.get("name", "Project"),
            metrics=metrics,
            debt_items=all_items,
            top_critical_items=sorted(
                [i for i in all_items if i.severity in [DebtSeverity.CRITICAL, DebtSeverity.HIGH]],
                key=lambda x: x.impact_score,
                reverse=True,
            )[:10],
            hotspot_files=self._identify_hotspots(all_items),
            recommendations=recommendations,
            quality_gate=quality_gate,
        )
        
        # Generate executive summary
        report.executive_summary = self._generate_summary(report)
        report.action_items = self._generate_action_items(report)
        
        analysis_time = (time.time() - start_time) * 1000
        logger.info(
            f"Analyzed technical debt for {report.project_name}: "
            f"{metrics.total_items} items, health score {metrics.health_score:.1f} "
            f"in {analysis_time:.2f}ms"
        )
        
        return report
    
    def _filter_items(self, items: list[DebtItem], config: DebtConfig) -> list[DebtItem]:
        """Filter debt items based on configuration."""
        filtered = []
        for item in items:
            # Check exclusion patterns
            excluded = any(
                pattern in item.file_path 
                for pattern in config.exclude_patterns
            )
            if excluded:
                continue
            
            # Exclude test files if configured
            if not config.include_tests and "/test" in item.file_path.lower():
                continue
            
            # Exclude generated files if configured
            if not config.include_generated and any(
                gen in item.file_path.lower() 
                for gen in ["generated", "auto_", ".gen."]
            ):
                continue
            
            filtered.append(item)
        
        return filtered
    
    def _calculate_metrics(
        self,
        items: list[DebtItem],
        code_data: dict,
        config: DebtConfig,
    ) -> DebtMetrics:
        """Calculate aggregated debt metrics."""
        metrics = DebtMetrics(developer_hourly_rate=config.developer_hourly_rate)
        
        # Count items
        metrics.total_items = len(items)
        
        for item in items:
            metrics.total_debt_hours += item.effort_hours
            
            # Count by severity
            if item.severity == DebtSeverity.CRITICAL:
                metrics.critical_count += 1
            elif item.severity == DebtSeverity.HIGH:
                metrics.high_count += 1
            elif item.severity == DebtSeverity.MEDIUM:
                metrics.medium_count += 1
            else:
                metrics.low_count += 1
            
            # Count by category
            cat = item.category.value
            metrics.debt_by_category[cat] = metrics.debt_by_category.get(cat, 0) + item.effort_hours
            metrics.items_by_category[cat] = metrics.items_by_category.get(cat, 0) + 1
        
        # Get code metrics
        metrics.average_complexity = code_data.get("average_complexity", 0)
        metrics.duplication_percentage = code_data.get("duplication_percentage", 0)
        metrics.test_coverage = code_data.get("test_coverage", 0)
        metrics.documentation_coverage = code_data.get("documentation_coverage", 0)
        
        # Calculate health score (0-100)
        metrics.health_score = self._calculate_health_score(metrics, config)
        
        # Calculate maintainability index
        metrics.maintainability_index = self._calculate_maintainability_index(metrics, code_data)
        
        # SQALE metrics
        metrics.sqale_rating = self._get_sqale_rating(metrics)
        metrics.sqale_debt_ratio = self._calculate_sqale_ratio(metrics, code_data)
        
        # Cost estimation
        metrics.estimated_cost_usd = metrics.total_debt_hours * config.developer_hourly_rate
        
        return metrics
    
    def _calculate_health_score(self, metrics: DebtMetrics, config: DebtConfig) -> float:
        """Calculate overall health score (0-100)."""
        score = 100.0
        
        # Penalize for critical issues
        score -= metrics.critical_count * 10
        
        # Penalize for high issues
        score -= metrics.high_count * 5
        
        # Penalize for medium issues
        score -= metrics.medium_count * 2
        
        # Penalize for low coverage
        if metrics.test_coverage < config.coverage_threshold:
            coverage_gap = config.coverage_threshold - metrics.test_coverage
            score -= coverage_gap * 0.3
        
        # Penalize for high duplication
        if metrics.duplication_percentage > config.duplication_threshold:
            dup_excess = metrics.duplication_percentage - config.duplication_threshold
            score -= dup_excess * 0.5
        
        # Penalize for high complexity
        if metrics.average_complexity > config.complexity_threshold:
            complexity_excess = metrics.average_complexity - config.complexity_threshold
            score -= complexity_excess * 0.5
        
        return max(0, min(100, score))
    
    def _calculate_maintainability_index(
        self,
        metrics: DebtMetrics,
        code_data: dict,
    ) -> float:
        """Calculate maintainability index (0-100)."""
        # Based on Microsoft's maintainability index formula
        volume = code_data.get("halstead_volume", 100)
        complexity = metrics.average_complexity
        loc = code_data.get("total_lines", 100)
        
        # Simplified version
        mi = 171 - 5.2 * (volume / 1000) - 0.23 * complexity - 16.2 * (loc / 1000)
        
        # Normalize to 0-100
        return max(0, min(100, mi * 100 / 171))
    
    def _get_sqale_rating(self, metrics: DebtMetrics) -> str:
        """Get SQALE rating (A-E)."""
        debt_ratio = metrics.sqale_debt_ratio
        
        if debt_ratio <= 5:
            return "A"
        elif debt_ratio <= 10:
            return "B"
        elif debt_ratio <= 20:
            return "C"
        elif debt_ratio <= 50:
            return "D"
        else:
            return "E"
    
    def _calculate_sqale_ratio(self, metrics: DebtMetrics, code_data: dict) -> float:
        """Calculate SQALE debt ratio."""
        total_lines = code_data.get("total_lines", 1)
        # Debt ratio = (remediation cost / development cost) * 100
        # Assume 1 minute per line for development
        development_time = total_lines / 60  # hours
        
        if development_time == 0:
            return 0
        
        return (metrics.total_debt_hours / development_time) * 100
    
    def _check_quality_gate(
        self,
        metrics: DebtMetrics,
        config: DebtConfig,
    ) -> QualityGateResult:
        """Check if metrics pass quality gate."""
        conditions = []
        failed = []
        
        # Check critical issues
        conditions.append({
            "name": "Critical Issues",
            "actual": metrics.critical_count,
            "threshold": config.max_critical_issues,
            "passed": metrics.critical_count <= config.max_critical_issues,
        })
        if metrics.critical_count > config.max_critical_issues:
            failed.append(f"Too many critical issues: {metrics.critical_count}")
        
        # Check high issues
        conditions.append({
            "name": "High Issues",
            "actual": metrics.high_count,
            "threshold": config.max_high_issues,
            "passed": metrics.high_count <= config.max_high_issues,
        })
        if metrics.high_count > config.max_high_issues:
            failed.append(f"Too many high issues: {metrics.high_count}")
        
        # Check health score
        conditions.append({
            "name": "Health Score",
            "actual": metrics.health_score,
            "threshold": config.min_health_score,
            "passed": metrics.health_score >= config.min_health_score,
        })
        if metrics.health_score < config.min_health_score:
            failed.append(f"Health score too low: {metrics.health_score:.1f}")
        
        # Check debt ratio
        conditions.append({
            "name": "Debt Ratio",
            "actual": metrics.sqale_debt_ratio,
            "threshold": config.max_debt_ratio,
            "passed": metrics.sqale_debt_ratio <= config.max_debt_ratio,
        })
        if metrics.sqale_debt_ratio > config.max_debt_ratio:
            failed.append(f"Debt ratio too high: {metrics.sqale_debt_ratio:.1f}%")
        
        passed = len(failed) == 0
        
        recommendations = []
        if not passed:
            recommendations.append("Address critical and high severity issues first")
            recommendations.append("Focus on reducing code complexity")
            recommendations.append("Increase test coverage")
        
        return QualityGateResult(
            passed=passed,
            gate_name="Standard Quality Gate",
            conditions=conditions,
            failed_conditions=failed,
            metrics=metrics,
            recommendations=recommendations,
        )
    
    def _identify_hotspots(self, items: list[DebtItem]) -> list[dict[str, Any]]:
        """Identify files with most debt."""
        file_debt: dict[str, dict] = {}
        
        for item in items:
            if item.file_path not in file_debt:
                file_debt[item.file_path] = {
                    "path": item.file_path,
                    "total_debt_hours": 0,
                    "item_count": 0,
                    "critical_count": 0,
                    "high_count": 0,
                }
            
            file_debt[item.file_path]["total_debt_hours"] += item.effort_hours
            file_debt[item.file_path]["item_count"] += 1
            
            if item.severity == DebtSeverity.CRITICAL:
                file_debt[item.file_path]["critical_count"] += 1
            elif item.severity == DebtSeverity.HIGH:
                file_debt[item.file_path]["high_count"] += 1
        
        # Sort by total debt and return top 10
        hotspots = sorted(
            file_debt.values(),
            key=lambda x: x["total_debt_hours"],
            reverse=True,
        )[:10]
        
        return hotspots
    
    async def _generate_recommendations(
        self,
        items: list[DebtItem],
        code_data: dict,
        config: DebtConfig,
    ) -> list[RefactoringRecommendation]:
        """Generate refactoring recommendations."""
        recommendations = []
        
        # Group items by file
        file_items: dict[str, list[DebtItem]] = {}
        for item in items:
            if item.file_path not in file_items:
                file_items[item.file_path] = []
            file_items[item.file_path].append(item)
        
        # Generate recommendations for high-debt files
        for file_path, file_debt_items in sorted(
            file_items.items(),
            key=lambda x: sum(i.effort_hours for i in x[1]),
            reverse=True,
        )[:5]:
            total_effort = sum(i.effort_hours for i in file_debt_items)
            categories = set(i.category for i in file_debt_items)
            
            import uuid
            rec = RefactoringRecommendation(
                id=str(uuid.uuid4()),
                title=f"Refactor {file_path.split('/')[-1]}",
                description=(
                    f"This file has {len(file_debt_items)} debt items "
                    f"totaling {total_effort:.1f} hours of remediation effort."
                ),
                category=file_debt_items[0].category,
                target_files=[file_path],
                debt_reduction_hours=total_effort * 0.7,  # Estimate 70% reduction
                estimated_effort_hours=total_effort,
                priority_score=total_effort,
                steps=self._generate_refactoring_steps(file_debt_items, categories),
            )
            recommendations.append(rec)
        
        # LLM-enhanced recommendations
        if self.llm_service:
            recommendations = await self._llm_enhance_recommendations(
                recommendations, items, code_data
            )
        
        # Sort by priority
        recommendations.sort(key=lambda x: x.priority_score, reverse=True)
        
        return recommendations[:10]
    
    def _generate_refactoring_steps(
        self,
        items: list[DebtItem],
        categories: set[DebtCategory],
    ) -> list[str]:
        """Generate refactoring steps based on debt categories."""
        steps = []
        
        if DebtCategory.COMPLEXITY in categories:
            steps.append("Extract complex methods into smaller, focused functions")
            steps.append("Reduce nested conditionals using early returns")
        
        if DebtCategory.DUPLICATION in categories:
            steps.append("Identify and extract common code into shared utilities")
            steps.append("Apply DRY principle with inheritance or composition")
        
        if DebtCategory.COVERAGE in categories:
            steps.append("Add unit tests for uncovered code paths")
            steps.append("Focus on edge cases and error handling")
        
        if DebtCategory.DEPENDENCY in categories:
            steps.append("Update outdated dependencies")
            steps.append("Reduce coupling by introducing interfaces")
        
        steps.append("Review and test changes thoroughly")
        
        return steps
    
    async def _llm_enhance_recommendations(
        self,
        recommendations: list[RefactoringRecommendation],
        items: list[DebtItem],
        code_data: dict,
    ) -> list[RefactoringRecommendation]:
        """Enhance recommendations using LLM."""
        # This would call the LLM to improve recommendations
        return recommendations
    
    def _generate_summary(self, report: DebtReport) -> str:
        """Generate executive summary."""
        metrics = report.metrics
        
        status = "healthy" if metrics.health_score >= 70 else "needs attention"
        
        summary = f"""
Technical Debt Report for {report.project_name}

Overall Status: {status.upper()}
Health Score: {metrics.health_score:.1f}/100 (SQALE Rating: {metrics.sqale_rating})

Key Metrics:
- Total Debt Items: {metrics.total_items}
- Estimated Remediation: {metrics.total_debt_hours:.1f} hours (${metrics.estimated_cost_usd:,.0f})
- Test Coverage: {metrics.test_coverage:.1f}%
- Code Duplication: {metrics.duplication_percentage:.1f}%
- Average Complexity: {metrics.average_complexity:.1f}

Critical Issues: {metrics.critical_count}
High Priority Issues: {metrics.high_count}

Quality Gate: {'PASSED' if report.quality_gate and report.quality_gate.passed else 'FAILED'}
"""
        return summary.strip()
    
    def _generate_action_items(self, report: DebtReport) -> list[str]:
        """Generate prioritized action items."""
        actions = []
        
        if report.metrics.critical_count > 0:
            actions.append(f"Immediately address {report.metrics.critical_count} critical issues")
        
        if report.metrics.test_coverage < 50:
            actions.append("Improve test coverage to at least 50%")
        
        if report.metrics.duplication_percentage > 10:
            actions.append("Reduce code duplication below 10%")
        
        if report.recommendations:
            top_rec = report.recommendations[0]
            actions.append(f"Priority refactoring: {top_rec.title}")
        
        if report.quality_gate and not report.quality_gate.passed:
            actions.extend(report.quality_gate.recommendations)
        
        return actions[:5]
    
    async def get_debt_trend(
        self,
        project_id: str,
        days: int = 30,
    ) -> list[DebtTrend]:
        """Get debt trend for a project over time."""
        # This would fetch historical data from database
        # Returning mock data for now
        trends = []
        base_score = 75.0
        base_debt = 100.0
        base_items = 50
        
        for i in range(days):
            date = datetime.utcnow() - timedelta(days=days - i)
            
            # Simulate some variation
            score_delta = (i % 7 - 3) * 0.5
            debt_delta = (i % 5 - 2) * 2
            items_delta = (i % 3 - 1)
            
            trends.append(DebtTrend(
                date=date,
                health_score=base_score + score_delta * i / 10,
                total_debt_hours=base_debt + debt_delta * i / 5,
                total_items=base_items + items_delta * i // 10,
                score_delta=score_delta,
                debt_delta=debt_delta,
                items_delta=items_delta,
            ))
        
        return trends


@lru_cache()
def get_technical_debt_service() -> TechnicalDebtService:
    """Get the technical debt service singleton."""
    return TechnicalDebtService()
