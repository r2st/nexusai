"""
Documentation Models

Data models for documentation generation.
"""

from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field


class DocFormat(str, Enum):
    """Output formats for documentation."""
    MARKDOWN = "markdown"
    HTML = "html"
    RST = "rst"
    ASCIIDOC = "asciidoc"
    OPENAPI = "openapi"
    ASYNCAPI = "asyncapi"


class DocStyle(str, Enum):
    """Documentation styles."""
    GOOGLE = "google"
    NUMPY = "numpy"
    SPHINX = "sphinx"
    JSDOC = "jsdoc"
    JAVADOC = "javadoc"
    KOTLIN_DOC = "kdoc"
    RUSTDOC = "rustdoc"
    GODOC = "godoc"


class DocSection(str, Enum):
    """Documentation sections."""
    OVERVIEW = "overview"
    INSTALLATION = "installation"
    QUICKSTART = "quickstart"
    API_REFERENCE = "api_reference"
    EXAMPLES = "examples"
    ARCHITECTURE = "architecture"
    CONTRIBUTING = "contributing"
    CHANGELOG = "changelog"
    FAQ = "faq"


class ParameterDoc(BaseModel):
    """Documentation for a parameter."""
    name: str
    type: Optional[str] = None
    description: str
    default: Optional[str] = None
    required: bool = True
    examples: list[str] = Field(default_factory=list)


class ReturnDoc(BaseModel):
    """Documentation for return value."""
    type: Optional[str] = None
    description: str
    examples: list[str] = Field(default_factory=list)


class ExceptionDoc(BaseModel):
    """Documentation for an exception."""
    type: str
    description: str
    conditions: Optional[str] = None


class ExampleDoc(BaseModel):
    """Documentation example."""
    title: Optional[str] = None
    description: Optional[str] = None
    code: str
    language: str = "python"
    output: Optional[str] = None


class FunctionDocumentation(BaseModel):
    """Documentation for a function/method."""
    name: str
    signature: str
    summary: str
    description: Optional[str] = None
    parameters: list[ParameterDoc] = Field(default_factory=list)
    returns: Optional[ReturnDoc] = None
    raises: list[ExceptionDoc] = Field(default_factory=list)
    examples: list[ExampleDoc] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    see_also: list[str] = Field(default_factory=list)
    deprecated: Optional[str] = None
    since: Optional[str] = None


class ClassDocumentation(BaseModel):
    """Documentation for a class."""
    name: str
    summary: str
    description: Optional[str] = None
    bases: list[str] = Field(default_factory=list)
    attributes: list[ParameterDoc] = Field(default_factory=list)
    methods: list[FunctionDocumentation] = Field(default_factory=list)
    examples: list[ExampleDoc] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    see_also: list[str] = Field(default_factory=list)


class ModuleDocumentation(BaseModel):
    """Documentation for a module/file."""
    name: str
    path: str
    summary: str
    description: Optional[str] = None
    classes: list[ClassDocumentation] = Field(default_factory=list)
    functions: list[FunctionDocumentation] = Field(default_factory=list)
    constants: list[ParameterDoc] = Field(default_factory=list)
    exports: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    examples: list[ExampleDoc] = Field(default_factory=list)


class EndpointDoc(BaseModel):
    """Documentation for an API endpoint."""
    method: str
    path: str
    summary: str
    description: Optional[str] = None
    parameters: list[ParameterDoc] = Field(default_factory=list)
    request_body: Optional[dict[str, Any]] = None
    responses: dict[str, dict[str, Any]] = Field(default_factory=dict)
    examples: list[ExampleDoc] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    security: list[str] = Field(default_factory=list)
    deprecated: bool = False


class APIDocumentation(BaseModel):
    """Documentation for an API."""
    title: str
    version: str
    description: Optional[str] = None
    base_url: Optional[str] = None
    endpoints: list[EndpointDoc] = Field(default_factory=list)
    schemas: dict[str, Any] = Field(default_factory=dict)
    security_schemes: dict[str, Any] = Field(default_factory=dict)
    tags: list[dict[str, str]] = Field(default_factory=list)


class OnboardingSection(BaseModel):
    """Section of an onboarding guide."""
    title: str
    content: str
    code_snippets: list[ExampleDoc] = Field(default_factory=list)
    links: list[dict[str, str]] = Field(default_factory=list)
    estimated_time: Optional[str] = None


class OnboardingGuide(BaseModel):
    """Complete onboarding guide for a project."""
    project_name: str
    overview: str
    prerequisites: list[str] = Field(default_factory=list)
    sections: list[OnboardingSection] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    resources: list[dict[str, str]] = Field(default_factory=list)
    total_estimated_time: Optional[str] = None


class DocumentationConfig(BaseModel):
    """Configuration for documentation generation."""
    format: DocFormat = DocFormat.MARKDOWN
    style: DocStyle = DocStyle.GOOGLE
    sections: list[DocSection] = Field(default_factory=list)
    
    # Filtering
    include_private: bool = False
    include_internal: bool = False
    min_complexity: int = 0
    
    # Generation options
    generate_examples: bool = True
    generate_types: bool = True
    infer_types: bool = True
    include_source_links: bool = True
    
    # LLM options
    use_llm: bool = True
    llm_enhance_descriptions: bool = True
    llm_generate_examples: bool = True
    
    # Output options
    single_file: bool = False
    output_dir: Optional[str] = None


class DocumentationResult(BaseModel):
    """Result of documentation generation."""
    project_name: str
    format: DocFormat
    modules: list[ModuleDocumentation] = Field(default_factory=list)
    api: Optional[APIDocumentation] = None
    onboarding: Optional[OnboardingGuide] = None
    
    # Output
    content: str = ""
    files: dict[str, str] = Field(default_factory=dict)
    
    # Metadata
    generation_time_ms: float = 0
    warnings: list[str] = Field(default_factory=list)
    stats: dict[str, int] = Field(default_factory=dict)
