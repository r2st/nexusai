"""
Test Generators

Specialized generators for different test types.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, Any

from .models import (
    TestFramework,
    TestType,
    TestCase,
    TestSuite,
    TestGenerationConfig,
    TestAssertion,
    AssertionType,
    FunctionAnalysis,
)

logger = logging.getLogger(__name__)


class BaseTestGenerator(ABC):
    """Base class for test generators."""
    
    @abstractmethod
    def generate(
        self,
        analysis: FunctionAnalysis,
        config: TestGenerationConfig,
    ) -> list[TestCase]:
        """Generate test cases for a function."""
        pass
    
    def _generate_test_name(self, func_name: str, scenario: str, config: TestGenerationConfig) -> str:
        """Generate a test name."""
        scenario_clean = scenario.lower().replace(" ", "_").replace("-", "_")
        return f"{config.test_prefix}{func_name}_{scenario_clean}"


class UnitTestGenerator(BaseTestGenerator):
    """Generates unit tests."""
    
    def generate(
        self,
        analysis: FunctionAnalysis,
        config: TestGenerationConfig,
    ) -> list[TestCase]:
        """Generate unit tests for a function."""
        tests = []
        
        # Basic happy path test
        tests.append(self._generate_happy_path(analysis, config))
        
        # Edge case tests
        if config.generate_edge_cases:
            tests.extend(self._generate_edge_cases(analysis, config))
        
        # Error case tests
        if config.generate_error_cases:
            tests.extend(self._generate_error_cases(analysis, config))
        
        # Generate code for each test
        for test in tests:
            test.code = self._render_test(test, config)
        
        return tests
    
    def _generate_happy_path(
        self,
        analysis: FunctionAnalysis,
        config: TestGenerationConfig,
    ) -> TestCase:
        """Generate a happy path test."""
        inputs = self._generate_sample_inputs(analysis)
        
        return TestCase(
            name=self._generate_test_name(analysis.name, "returns_expected", config),
            description=f"Test that {analysis.name} returns expected result with valid inputs",
            test_type=TestType.UNIT,
            target_function=analysis.name,
            inputs=inputs,
            assertions=[
                TestAssertion(
                    type=AssertionType.IS_NOT_NONE,
                    actual="result",
                    message="Function should return a value",
                )
            ],
            tags=["happy_path"],
        )
    
    def _generate_edge_cases(
        self,
        analysis: FunctionAnalysis,
        config: TestGenerationConfig,
    ) -> list[TestCase]:
        """Generate edge case tests."""
        tests = []
        
        for param in analysis.parameters:
            param_name = param.get("name", "param")
            param_type = param.get("type", "")
            
            # Empty/None tests
            if "Optional" in param_type or param.get("default") is not None:
                tests.append(TestCase(
                    name=self._generate_test_name(analysis.name, f"{param_name}_none", config),
                    description=f"Test {analysis.name} with {param_name}=None",
                    test_type=TestType.UNIT,
                    target_function=analysis.name,
                    inputs={param_name: None},
                    edge_cases=[f"{param_name} is None"],
                    tags=["edge_case", "null_input"],
                ))
            
            # Empty string/list tests
            if "str" in param_type.lower():
                tests.append(TestCase(
                    name=self._generate_test_name(analysis.name, f"{param_name}_empty", config),
                    description=f"Test {analysis.name} with empty {param_name}",
                    test_type=TestType.UNIT,
                    target_function=analysis.name,
                    inputs={param_name: ""},
                    edge_cases=[f"{param_name} is empty string"],
                    tags=["edge_case", "empty_input"],
                ))
            
            if "list" in param_type.lower() or "List" in param_type:
                tests.append(TestCase(
                    name=self._generate_test_name(analysis.name, f"{param_name}_empty_list", config),
                    description=f"Test {analysis.name} with empty {param_name}",
                    test_type=TestType.UNIT,
                    target_function=analysis.name,
                    inputs={param_name: []},
                    edge_cases=[f"{param_name} is empty list"],
                    tags=["edge_case", "empty_input"],
                ))
            
            # Boundary values for numeric types
            if "int" in param_type.lower():
                tests.append(TestCase(
                    name=self._generate_test_name(analysis.name, f"{param_name}_zero", config),
                    description=f"Test {analysis.name} with {param_name}=0",
                    test_type=TestType.UNIT,
                    target_function=analysis.name,
                    inputs={param_name: 0},
                    edge_cases=[f"{param_name} is zero"],
                    tags=["edge_case", "boundary"],
                ))
                tests.append(TestCase(
                    name=self._generate_test_name(analysis.name, f"{param_name}_negative", config),
                    description=f"Test {analysis.name} with negative {param_name}",
                    test_type=TestType.UNIT,
                    target_function=analysis.name,
                    inputs={param_name: -1},
                    edge_cases=[f"{param_name} is negative"],
                    tags=["edge_case", "boundary"],
                ))
        
        return tests
    
    def _generate_error_cases(
        self,
        analysis: FunctionAnalysis,
        config: TestGenerationConfig,
    ) -> list[TestCase]:
        """Generate error case tests."""
        tests = []
        
        for exc in analysis.raises:
            tests.append(TestCase(
                name=self._generate_test_name(analysis.name, f"raises_{exc.lower()}", config),
                description=f"Test that {analysis.name} raises {exc} on invalid input",
                test_type=TestType.UNIT,
                target_function=analysis.name,
                assertions=[
                    TestAssertion(
                        type=AssertionType.RAISES,
                        actual=f"{analysis.name}(invalid_input)",
                        expected=exc,
                    )
                ],
                tags=["error_case"],
            ))
        
        return tests
    
    def _generate_sample_inputs(self, analysis: FunctionAnalysis) -> dict[str, Any]:
        """Generate sample inputs based on parameter types."""
        inputs = {}
        
        for param in analysis.parameters:
            param_name = param.get("name", "param")
            param_type = param.get("type", "str").lower()
            default = param.get("default")
            
            if default is not None:
                inputs[param_name] = default
            elif "str" in param_type:
                inputs[param_name] = "test_value"
            elif "int" in param_type:
                inputs[param_name] = 42
            elif "float" in param_type:
                inputs[param_name] = 3.14
            elif "bool" in param_type:
                inputs[param_name] = True
            elif "list" in param_type:
                inputs[param_name] = [1, 2, 3]
            elif "dict" in param_type:
                inputs[param_name] = {"key": "value"}
            else:
                inputs[param_name] = None
        
        return inputs
    
    def _render_test(self, test: TestCase, config: TestGenerationConfig) -> str:
        """Render test case to code."""
        if config.framework == TestFramework.PYTEST:
            return self._render_pytest(test, config)
        elif config.framework == TestFramework.UNITTEST:
            return self._render_unittest(test, config)
        elif config.framework == TestFramework.JEST:
            return self._render_jest(test, config)
        elif config.framework == TestFramework.JUNIT:
            return self._render_junit(test, config)
        else:
            return self._render_pytest(test, config)
    
    def _render_pytest(self, test: TestCase, config: TestGenerationConfig) -> str:
        """Render as pytest test."""
        lines = [
            f"def {test.name}():",
            f'    """',
            f"    {test.description}",
        ]
        
        if test.edge_cases:
            lines.append(f"    Edge cases: {', '.join(test.edge_cases)}")
        
        lines.append('    """')
        
        # Setup
        for step in test.setup:
            lines.append(f"    # {step.description}")
            for line in step.code.split("\n"):
                lines.append(f"    {line}")
        
        # Arrange
        if test.inputs:
            lines.append("    # Arrange")
            for name, value in test.inputs.items():
                lines.append(f"    {name} = {repr(value)}")
        
        # Act
        lines.append("    # Act")
        if test.target_function:
            args = ", ".join(f"{k}={k}" for k in test.inputs.keys())
            lines.append(f"    result = {test.target_function}({args})")
        
        # Assert
        lines.append("    # Assert")
        for assertion in test.assertions:
            lines.append(f"    {self._render_pytest_assertion(assertion)}")
        
        # Teardown
        for step in test.teardown:
            lines.append(f"    # {step.description}")
            for line in step.code.split("\n"):
                lines.append(f"    {line}")
        
        return "\n".join(lines)
    
    def _render_pytest_assertion(self, assertion: TestAssertion) -> str:
        """Render a pytest assertion."""
        msg = f', "{assertion.message}"' if assertion.message else ""
        
        if assertion.type == AssertionType.EQUALS:
            return f"assert {assertion.actual} == {assertion.expected}{msg}"
        elif assertion.type == AssertionType.NOT_EQUALS:
            return f"assert {assertion.actual} != {assertion.expected}{msg}"
        elif assertion.type == AssertionType.TRUE:
            return f"assert {assertion.actual}{msg}"
        elif assertion.type == AssertionType.FALSE:
            return f"assert not {assertion.actual}{msg}"
        elif assertion.type == AssertionType.IS_NONE:
            return f"assert {assertion.actual} is None{msg}"
        elif assertion.type == AssertionType.IS_NOT_NONE:
            return f"assert {assertion.actual} is not None{msg}"
        elif assertion.type == AssertionType.RAISES:
            return f"with pytest.raises({assertion.expected}):\n        {assertion.actual}"
        elif assertion.type == AssertionType.CONTAINS:
            return f"assert {assertion.expected} in {assertion.actual}{msg}"
        elif assertion.type == AssertionType.INSTANCE_OF:
            return f"assert isinstance({assertion.actual}, {assertion.expected}){msg}"
        elif assertion.type == AssertionType.APPROX_EQUALS:
            tol = assertion.tolerance or 0.001
            return f"assert {assertion.actual} == pytest.approx({assertion.expected}, abs={tol}){msg}"
        else:
            return f"assert {assertion.actual}"
    
    def _render_unittest(self, test: TestCase, config: TestGenerationConfig) -> str:
        """Render as unittest test."""
        lines = [
            f"def {test.name}(self):",
            f'    """',
            f"    {test.description}",
            '    """',
        ]
        
        if test.inputs:
            lines.append("    # Arrange")
            for name, value in test.inputs.items():
                lines.append(f"    {name} = {repr(value)}")
        
        lines.append("    # Act")
        if test.target_function:
            args = ", ".join(f"{k}={k}" for k in test.inputs.keys())
            lines.append(f"    result = {test.target_function}({args})")
        
        lines.append("    # Assert")
        for assertion in test.assertions:
            lines.append(f"    {self._render_unittest_assertion(assertion)}")
        
        return "\n".join(lines)
    
    def _render_unittest_assertion(self, assertion: TestAssertion) -> str:
        """Render a unittest assertion."""
        msg = f', "{assertion.message}"' if assertion.message else ""
        
        if assertion.type == AssertionType.EQUALS:
            return f"self.assertEqual({assertion.actual}, {assertion.expected}{msg})"
        elif assertion.type == AssertionType.NOT_EQUALS:
            return f"self.assertNotEqual({assertion.actual}, {assertion.expected}{msg})"
        elif assertion.type == AssertionType.TRUE:
            return f"self.assertTrue({assertion.actual}{msg})"
        elif assertion.type == AssertionType.FALSE:
            return f"self.assertFalse({assertion.actual}{msg})"
        elif assertion.type == AssertionType.IS_NONE:
            return f"self.assertIsNone({assertion.actual}{msg})"
        elif assertion.type == AssertionType.IS_NOT_NONE:
            return f"self.assertIsNotNone({assertion.actual}{msg})"
        elif assertion.type == AssertionType.RAISES:
            return f"with self.assertRaises({assertion.expected}):\n            {assertion.actual}"
        else:
            return f"self.assertTrue({assertion.actual})"
    
    def _render_jest(self, test: TestCase, config: TestGenerationConfig) -> str:
        """Render as Jest test."""
        lines = [
            f"test('{test.description}', () => {{",
        ]
        
        if test.inputs:
            lines.append("  // Arrange")
            for name, value in test.inputs.items():
                lines.append(f"  const {name} = {self._to_js_value(value)};")
        
        lines.append("  // Act")
        if test.target_function:
            args = ", ".join(test.inputs.keys())
            lines.append(f"  const result = {test.target_function}({args});")
        
        lines.append("  // Assert")
        for assertion in test.assertions:
            lines.append(f"  {self._render_jest_assertion(assertion)}")
        
        lines.append("});")
        return "\n".join(lines)
    
    def _render_jest_assertion(self, assertion: TestAssertion) -> str:
        """Render a Jest assertion."""
        if assertion.type == AssertionType.EQUALS:
            return f"expect({assertion.actual}).toBe({assertion.expected});"
        elif assertion.type == AssertionType.NOT_EQUALS:
            return f"expect({assertion.actual}).not.toBe({assertion.expected});"
        elif assertion.type == AssertionType.TRUE:
            return f"expect({assertion.actual}).toBeTruthy();"
        elif assertion.type == AssertionType.FALSE:
            return f"expect({assertion.actual}).toBeFalsy();"
        elif assertion.type == AssertionType.IS_NONE:
            return f"expect({assertion.actual}).toBeNull();"
        elif assertion.type == AssertionType.IS_NOT_NONE:
            return f"expect({assertion.actual}).not.toBeNull();"
        elif assertion.type == AssertionType.RAISES:
            return f"expect(() => {assertion.actual}).toThrow({assertion.expected});"
        else:
            return f"expect({assertion.actual}).toBeDefined();"
    
    def _render_junit(self, test: TestCase, config: TestGenerationConfig) -> str:
        """Render as JUnit test."""
        lines = [
            "@Test",
            f"public void {test.name}() {{",
        ]
        
        if test.inputs:
            lines.append("    // Arrange")
            for name, value in test.inputs.items():
                lines.append(f"    var {name} = {self._to_java_value(value)};")
        
        lines.append("    // Act")
        if test.target_function:
            args = ", ".join(test.inputs.keys())
            lines.append(f"    var result = {test.target_function}({args});")
        
        lines.append("    // Assert")
        for assertion in test.assertions:
            lines.append(f"    {self._render_junit_assertion(assertion)}")
        
        lines.append("}")
        return "\n".join(lines)
    
    def _render_junit_assertion(self, assertion: TestAssertion) -> str:
        """Render a JUnit assertion."""
        if assertion.type == AssertionType.EQUALS:
            return f"assertEquals({assertion.expected}, {assertion.actual});"
        elif assertion.type == AssertionType.NOT_EQUALS:
            return f"assertNotEquals({assertion.expected}, {assertion.actual});"
        elif assertion.type == AssertionType.TRUE:
            return f"assertTrue({assertion.actual});"
        elif assertion.type == AssertionType.FALSE:
            return f"assertFalse({assertion.actual});"
        elif assertion.type == AssertionType.IS_NONE:
            return f"assertNull({assertion.actual});"
        elif assertion.type == AssertionType.IS_NOT_NONE:
            return f"assertNotNull({assertion.actual});"
        else:
            return f"assertNotNull({assertion.actual});"
    
    def _to_js_value(self, value: Any) -> str:
        """Convert Python value to JavaScript."""
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, str):
            return f'"{value}"'
        return repr(value)
    
    def _to_java_value(self, value: Any) -> str:
        """Convert Python value to Java."""
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, str):
            return f'"{value}"'
        return str(value)


class IntegrationTestGenerator(BaseTestGenerator):
    """Generates integration tests."""
    
    def generate(
        self,
        analysis: FunctionAnalysis,
        config: TestGenerationConfig,
    ) -> list[TestCase]:
        """Generate integration tests."""
        tests = []
        
        # Only generate integration tests for functions with external dependencies
        if analysis.uses_database or analysis.uses_network or analysis.uses_io:
            tests.append(TestCase(
                name=f"{config.test_prefix}{analysis.name}_integration",
                description=f"Integration test for {analysis.name} with external dependencies",
                test_type=TestType.INTEGRATION,
                target_function=analysis.name,
                tags=["integration"],
            ))
        
        return tests


class PropertyTestGenerator(BaseTestGenerator):
    """Generates property-based tests using Hypothesis."""
    
    def generate(
        self,
        analysis: FunctionAnalysis,
        config: TestGenerationConfig,
    ) -> list[TestCase]:
        """Generate property-based tests."""
        if not config.generate_property_tests:
            return []
        
        tests = []
        
        # Generate property test for function
        test = TestCase(
            name=f"{config.test_prefix}{analysis.name}_property",
            description=f"Property-based test for {analysis.name}",
            test_type=TestType.PROPERTY,
            target_function=analysis.name,
            tags=["property"],
        )
        
        # Generate code with Hypothesis
        strategies = self._get_hypothesis_strategies(analysis)
        
        test.code = f'''@given({strategies})
def {test.name}({", ".join(p["name"] for p in analysis.parameters)}):
    """
    Property-based test for {analysis.name}.
    Tests that the function handles arbitrary valid inputs.
    """
    result = {analysis.name}({", ".join(p["name"] for p in analysis.parameters)})
    # Add property assertions here
    assert result is not None
'''
        
        tests.append(test)
        return tests
    
    def _get_hypothesis_strategies(self, analysis: FunctionAnalysis) -> str:
        """Get Hypothesis strategies for parameters."""
        strategies = []
        
        for param in analysis.parameters:
            param_name = param.get("name", "param")
            param_type = param.get("type", "str").lower()
            
            if "str" in param_type:
                strategies.append(f"{param_name}=st.text()")
            elif "int" in param_type:
                strategies.append(f"{param_name}=st.integers()")
            elif "float" in param_type:
                strategies.append(f"{param_name}=st.floats(allow_nan=False)")
            elif "bool" in param_type:
                strategies.append(f"{param_name}=st.booleans()")
            elif "list" in param_type:
                strategies.append(f"{param_name}=st.lists(st.integers())")
            elif "dict" in param_type:
                strategies.append(f"{param_name}=st.dictionaries(st.text(), st.integers())")
            else:
                strategies.append(f"{param_name}=st.none()")
        
        return ", ".join(strategies)
