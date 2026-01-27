"""
Test Generation Service

Main service for automated test generation.
"""

import logging
import time
from typing import Optional, Any
from functools import lru_cache

from .models import (
    TestFramework,
    TestType,
    TestCase,
    TestSuite,
    TestGenerationConfig,
    TestGenerationResult,
    FunctionAnalysis,
)
from .generators import (
    UnitTestGenerator,
    IntegrationTestGenerator,
    PropertyTestGenerator,
)

logger = logging.getLogger(__name__)


class TestGenerationService:
    """
    Service for automated test generation.
    
    Capabilities:
    - Unit test generation
    - Integration test generation
    - Property-based test generation
    - Edge case and error case generation
    - Multi-framework support (pytest, Jest, JUnit, etc.)
    """
    
    def __init__(self, llm_service: Optional[Any] = None):
        self.llm_service = llm_service
        self.unit_generator = UnitTestGenerator()
        self.integration_generator = IntegrationTestGenerator()
        self.property_generator = PropertyTestGenerator()
    
    async def generate_tests(
        self,
        analysis_result: dict,
        config: TestGenerationConfig,
    ) -> TestGenerationResult:
        """
        Generate tests from code analysis.
        
        Args:
            analysis_result: Results from code analysis
            config: Test generation configuration
            
        Returns:
            TestGenerationResult with generated tests
        """
        start_time = time.time()
        
        result = TestGenerationResult(
            project_name=analysis_result.get("name", "Project"),
            framework=config.framework,
        )
        
        # Process each module
        for module_data in analysis_result.get("modules", []):
            suite = await self._generate_module_tests(module_data, config)
            if suite.test_cases:
                result.suites.append(suite)
        
        # Calculate statistics
        result.total_tests = sum(len(s.test_cases) for s in result.suites)
        result.tests_by_type = self._count_by_type(result.suites)
        result.estimated_coverage = self._estimate_coverage(result, config)
        
        # Generate output files
        result.files = self._generate_files(result, config)
        
        result.generation_time_ms = (time.time() - start_time) * 1000
        
        logger.info(
            f"Generated {result.total_tests} tests for {result.project_name} "
            f"in {result.generation_time_ms:.2f}ms"
        )
        
        return result
    
    async def _generate_module_tests(
        self,
        module_data: dict,
        config: TestGenerationConfig,
    ) -> TestSuite:
        """Generate tests for a module."""
        suite = TestSuite(
            name=f"Test{module_data.get('name', 'Module')}",
            description=f"Tests for {module_data.get('name', 'module')}",
            framework=config.framework,
            language=module_data.get("language", "python"),
            imports=self._get_imports(module_data, config),
        )
        
        # Generate tests for each function
        for func_data in module_data.get("functions", []):
            analysis = self._analyze_function(func_data)
            
            if TestType.UNIT in config.test_types:
                suite.test_cases.extend(
                    self.unit_generator.generate(analysis, config)
                )
            
            if TestType.INTEGRATION in config.test_types:
                suite.test_cases.extend(
                    self.integration_generator.generate(analysis, config)
                )
            
            if TestType.PROPERTY in config.test_types:
                suite.test_cases.extend(
                    self.property_generator.generate(analysis, config)
                )
        
        # Generate tests for each class
        for cls_data in module_data.get("classes", []):
            class_tests = await self._generate_class_tests(cls_data, config)
            suite.test_cases.extend(class_tests)
        
        # LLM enhancement
        if config.use_llm and self.llm_service:
            suite = await self._llm_enhance_tests(suite, config)
        
        # Generate suite code
        suite.code = self._render_suite(suite, config)
        
        return suite
    
    async def _generate_class_tests(
        self,
        cls_data: dict,
        config: TestGenerationConfig,
    ) -> list[TestCase]:
        """Generate tests for a class."""
        tests = []
        class_name = cls_data.get("name", "Class")
        
        # Test __init__ if present
        init_data = None
        for method in cls_data.get("methods", []):
            if method.get("name") == "__init__":
                init_data = method
                break
        
        if init_data:
            analysis = self._analyze_function(init_data)
            analysis.name = f"{class_name}.__init__"
            tests.extend(self.unit_generator.generate(analysis, config))
        
        # Test other methods
        for method_data in cls_data.get("methods", []):
            if method_data.get("name", "").startswith("_"):
                continue
            
            analysis = self._analyze_function(method_data)
            analysis.name = f"{class_name}.{method_data.get('name', 'method')}"
            tests.extend(self.unit_generator.generate(analysis, config))
        
        return tests
    
    def _analyze_function(self, func_data: dict) -> FunctionAnalysis:
        """Analyze a function for test generation."""
        return FunctionAnalysis(
            name=func_data.get("name", "function"),
            signature=func_data.get("signature", ""),
            parameters=func_data.get("parameters", []),
            return_type=func_data.get("return_type"),
            raises=func_data.get("raises", []),
            complexity=func_data.get("complexity", 1),
            branches=func_data.get("branches", 0),
            calls=func_data.get("calls", []),
            uses_io=func_data.get("uses_io", False),
            uses_database=func_data.get("uses_database", False),
            uses_network=func_data.get("uses_network", False),
            edge_cases=func_data.get("edge_cases", []),
            boundary_values=func_data.get("boundary_values", []),
        )
    
    def _get_imports(self, module_data: dict, config: TestGenerationConfig) -> list[str]:
        """Get required imports for the test file."""
        imports = []
        language = module_data.get("language", "python")
        
        if language == "python":
            if config.framework == TestFramework.PYTEST:
                imports.append("import pytest")
                if config.generate_mocks:
                    imports.append("from unittest.mock import Mock, patch, MagicMock")
                if config.generate_property_tests:
                    imports.append("from hypothesis import given, strategies as st")
            elif config.framework == TestFramework.UNITTEST:
                imports.append("import unittest")
                if config.generate_mocks:
                    imports.append("from unittest.mock import Mock, patch")
            
            # Import the module being tested
            module_name = module_data.get("name", "module")
            imports.append(f"from {module_name} import *")
        
        return imports
    
    def _render_suite(self, suite: TestSuite, config: TestGenerationConfig) -> str:
        """Render a test suite to code."""
        lines = []
        
        # File header
        lines.append('"""')
        lines.append(f"{suite.name}")
        if suite.description:
            lines.append(f"\n{suite.description}")
        lines.append('"""')
        lines.append("")
        
        # Imports
        for imp in suite.imports:
            lines.append(imp)
        lines.append("")
        
        # Fixtures (pytest)
        if config.framework == TestFramework.PYTEST and suite.fixtures:
            for fixture in suite.fixtures:
                lines.append(fixture)
                lines.append("")
        
        # Setup module
        if suite.setup_module:
            lines.append(suite.setup_module)
            lines.append("")
        
        # Test class (for unittest) or functions (for pytest)
        if config.framework == TestFramework.UNITTEST:
            lines.append(f"class {suite.name}(unittest.TestCase):")
            lines.append('    """Test suite for the module."""')
            lines.append("")
            
            for test in suite.test_cases:
                for line in test.code.split("\n"):
                    lines.append(f"    {line}")
                lines.append("")
        else:
            for test in suite.test_cases:
                lines.append(test.code)
                lines.append("")
        
        # Teardown module
        if suite.teardown_module:
            lines.append(suite.teardown_module)
        
        return "\n".join(lines)
    
    def _count_by_type(self, suites: list[TestSuite]) -> dict[str, int]:
        """Count tests by type."""
        counts: dict[str, int] = {}
        for suite in suites:
            for test in suite.test_cases:
                type_name = test.test_type.value
                counts[type_name] = counts.get(type_name, 0) + 1
        return counts
    
    def _estimate_coverage(
        self,
        result: TestGenerationResult,
        config: TestGenerationConfig,
    ) -> float:
        """Estimate test coverage based on generated tests."""
        # Simple heuristic: assume each test covers some percentage
        base_coverage = min(result.total_tests * 5, 80)
        
        # Bonus for edge case tests
        edge_case_count = sum(
            1 for s in result.suites for t in s.test_cases 
            if "edge_case" in t.tags
        )
        edge_bonus = min(edge_case_count * 2, 10)
        
        # Bonus for property tests
        property_count = sum(
            1 for s in result.suites for t in s.test_cases 
            if t.test_type == TestType.PROPERTY
        )
        property_bonus = min(property_count * 5, 10)
        
        return min(base_coverage + edge_bonus + property_bonus, 95)
    
    def _generate_files(
        self,
        result: TestGenerationResult,
        config: TestGenerationConfig,
    ) -> dict[str, str]:
        """Generate output files."""
        files = {}
        
        for suite in result.suites:
            filename = config.file_pattern.format(
                module=suite.name.replace("Test", "").lower()
            )
            filepath = f"{config.output_dir}/{filename}"
            files[filepath] = suite.code
        
        # Generate conftest.py for pytest
        if config.framework == TestFramework.PYTEST:
            files[f"{config.output_dir}/conftest.py"] = self._generate_conftest(result)
        
        return files
    
    def _generate_conftest(self, result: TestGenerationResult) -> str:
        """Generate pytest conftest.py."""
        return '''"""
Pytest configuration and shared fixtures.
"""

import pytest


@pytest.fixture
def sample_data():
    """Provide sample data for tests."""
    return {"key": "value", "number": 42}


@pytest.fixture
def mock_api_response():
    """Provide mock API response."""
    return {"status": "success", "data": []}


@pytest.fixture(autouse=True)
def reset_state():
    """Reset state before each test."""
    yield
    # Cleanup after test
'''
    
    async def _llm_enhance_tests(
        self,
        suite: TestSuite,
        config: TestGenerationConfig,
    ) -> TestSuite:
        """Enhance tests using LLM."""
        if not self.llm_service:
            return suite
        
        # This would call the LLM to improve test assertions and add more tests
        return suite
    
    async def generate_tests_for_function(
        self,
        code: str,
        language: str,
        config: TestGenerationConfig,
    ) -> list[TestCase]:
        """
        Generate tests for a single function.
        
        Args:
            code: The function code
            language: Programming language
            config: Generation configuration
            
        Returns:
            List of generated test cases
        """
        # Parse the function code to extract analysis
        # This would use language-specific parsing in real implementation
        analysis = FunctionAnalysis(
            name="function",
            signature=code.split("\n")[0],
            parameters=[],
        )
        
        tests = []
        tests.extend(self.unit_generator.generate(analysis, config))
        
        return tests


@lru_cache()
def get_test_generation_service() -> TestGenerationService:
    """Get the test generation service singleton."""
    return TestGenerationService()
