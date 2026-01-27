"""
Test Generation Models

Data models for test generation.
"""

from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field


class TestFramework(str, Enum):
    """Supported test frameworks."""
    # Python
    PYTEST = "pytest"
    UNITTEST = "unittest"
    
    # JavaScript/TypeScript
    JEST = "jest"
    MOCHA = "mocha"
    VITEST = "vitest"
    
    # Java
    JUNIT = "junit"
    TESTNG = "testng"
    
    # Other
    RSPEC = "rspec"  # Ruby
    GOTEST = "gotest"  # Go
    CARGO_TEST = "cargo_test"  # Rust


class TestType(str, Enum):
    """Types of tests."""
    UNIT = "unit"
    INTEGRATION = "integration"
    PROPERTY = "property"
    MUTATION = "mutation"
    SNAPSHOT = "snapshot"
    E2E = "e2e"
    PERFORMANCE = "performance"


class AssertionType(str, Enum):
    """Types of assertions."""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    TRUE = "true"
    FALSE = "false"
    RAISES = "raises"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    IS_NONE = "is_none"
    IS_NOT_NONE = "is_not_none"
    INSTANCE_OF = "instance_of"
    APPROX_EQUALS = "approx_equals"


class TestAssertion(BaseModel):
    """A single test assertion."""
    type: AssertionType
    actual: str
    expected: Optional[str] = None
    message: Optional[str] = None
    tolerance: Optional[float] = None


class TestStep(BaseModel):
    """A step in a test case."""
    description: str
    code: str
    is_setup: bool = False
    is_teardown: bool = False


class TestCase(BaseModel):
    """A single test case."""
    name: str
    description: str
    test_type: TestType = TestType.UNIT
    
    target_function: Optional[str] = None
    target_class: Optional[str] = None
    target_module: str = ""
    
    setup: list[TestStep] = Field(default_factory=list)
    steps: list[TestStep] = Field(default_factory=list)
    assertions: list[TestAssertion] = Field(default_factory=list)
    teardown: list[TestStep] = Field(default_factory=list)
    
    tags: list[str] = Field(default_factory=list)
    priority: int = 1
    timeout: Optional[int] = None
    skip_reason: Optional[str] = None
    
    code: str = ""
    
    inputs: dict[str, Any] = Field(default_factory=dict)
    expected_output: Optional[Any] = None
    
    edge_cases: list[str] = Field(default_factory=list)


class TestSuite(BaseModel):
    """Collection of test cases."""
    name: str
    description: Optional[str] = None
    framework: TestFramework
    language: str
    
    test_cases: list[TestCase] = Field(default_factory=list)
    
    setup_module: Optional[str] = None
    teardown_module: Optional[str] = None
    fixtures: list[str] = Field(default_factory=list)
    
    imports: list[str] = Field(default_factory=list)
    
    code: str = ""
    
    file_path: Optional[str] = None


class CoverageTarget(BaseModel):
    """Target coverage for test generation."""
    line_coverage: float = 80.0
    branch_coverage: float = 70.0
    function_coverage: float = 90.0
    
    critical_paths: list[str] = Field(default_factory=list)
    exclude_patterns: list[str] = Field(default_factory=list)


class TestGenerationConfig(BaseModel):
    """Configuration for test generation."""
    framework: TestFramework = TestFramework.PYTEST
    test_types: list[TestType] = Field(default_factory=lambda: [TestType.UNIT])
    
    coverage: CoverageTarget = Field(default_factory=CoverageTarget)
    
    generate_edge_cases: bool = True
    generate_error_cases: bool = True
    generate_property_tests: bool = False
    generate_mocks: bool = True
    
    use_llm: bool = True
    llm_improve_assertions: bool = True
    
    output_dir: str = "tests"
    file_pattern: str = "test_{module}.py"
    
    test_prefix: str = "test_"
    class_prefix: str = "Test"


class TestGenerationResult(BaseModel):
    """Result of test generation."""
    project_name: str
    framework: TestFramework
    
    suites: list[TestSuite] = Field(default_factory=list)
    
    total_tests: int = 0
    tests_by_type: dict[str, int] = Field(default_factory=dict)
    estimated_coverage: float = 0.0
    
    files: dict[str, str] = Field(default_factory=dict)
    
    generation_time_ms: float = 0
    warnings: list[str] = Field(default_factory=list)


class FunctionAnalysis(BaseModel):
    """Analysis of a function for test generation."""
    name: str
    signature: str
    parameters: list[dict[str, Any]] = Field(default_factory=list)
    return_type: Optional[str] = None
    raises: list[str] = Field(default_factory=list)
    
    complexity: int = 1
    branches: int = 0
    
    calls: list[str] = Field(default_factory=list)
    uses_io: bool = False
    uses_database: bool = False
    uses_network: bool = False
    
    edge_cases: list[str] = Field(default_factory=list)
    boundary_values: list[Any] = Field(default_factory=list)
