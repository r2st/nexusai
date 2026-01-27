"""
Documentation Generation Service

Automated documentation generation from code analysis.
"""

from .service import (
    DocumentationService,
    get_documentation_service,
)
from .models import (
    DocFormat,
    DocStyle,
    DocSection,
    DocumentationConfig,
    DocumentationResult,
    APIDocumentation,
    ModuleDocumentation,
    ClassDocumentation,
    FunctionDocumentation,
    OnboardingGuide,
)
from .generators import (
    DocstringGenerator,
    APIDocGenerator,
    ReadmeGenerator,
    OnboardingGenerator,
)

__all__ = [
    # Service
    "DocumentationService",
    "get_documentation_service",
    # Models
    "DocFormat",
    "DocStyle",
    "DocSection",
    "DocumentationConfig",
    "DocumentationResult",
    "APIDocumentation",
    "ModuleDocumentation",
    "ClassDocumentation",
    "FunctionDocumentation",
    "OnboardingGuide",
    # Generators
    "DocstringGenerator",
    "APIDocGenerator",
    "ReadmeGenerator",
    "OnboardingGenerator",
]
