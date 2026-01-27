"""
Documentation Generators

Specialized generators for different documentation types.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, Any

from .models import (
    DocFormat,
    DocStyle,
    DocumentationConfig,
    FunctionDocumentation,
    ClassDocumentation,
    ModuleDocumentation,
    APIDocumentation,
    EndpointDoc,
    OnboardingGuide,
    OnboardingSection,
    ExampleDoc,
    ParameterDoc,
    ReturnDoc,
)

logger = logging.getLogger(__name__)


class BaseDocGenerator(ABC):
    """Base class for documentation generators."""
    
    @abstractmethod
    def generate(self, data: Any, config: DocumentationConfig) -> str:
        """Generate documentation content."""
        pass


class DocstringGenerator(BaseDocGenerator):
    """Generates docstrings for functions and classes."""
    
    def generate(self, data: Any, config: DocumentationConfig) -> str:
        """Generate docstring based on style."""
        if isinstance(data, FunctionDocumentation):
            return self._generate_function_docstring(data, config)
        elif isinstance(data, ClassDocumentation):
            return self._generate_class_docstring(data, config)
        return ""
    
    def _generate_function_docstring(
        self, 
        func: FunctionDocumentation, 
        config: DocumentationConfig
    ) -> str:
        """Generate function docstring."""
        if config.style == DocStyle.GOOGLE:
            return self._google_function(func)
        elif config.style == DocStyle.NUMPY:
            return self._numpy_function(func)
        elif config.style == DocStyle.SPHINX:
            return self._sphinx_function(func)
        elif config.style == DocStyle.JSDOC:
            return self._jsdoc_function(func)
        elif config.style == DocStyle.JAVADOC:
            return self._javadoc_function(func)
        else:
            return self._google_function(func)
    
    def _google_function(self, func: FunctionDocumentation) -> str:
        """Generate Google-style docstring."""
        lines = [f'"""{func.summary}']
        
        if func.description:
            lines.append("")
            lines.append(func.description)
        
        if func.parameters:
            lines.append("")
            lines.append("Args:")
            for param in func.parameters:
                type_hint = f" ({param.type})" if param.type else ""
                default = f" Defaults to {param.default}." if param.default else ""
                lines.append(f"    {param.name}{type_hint}: {param.description}{default}")
        
        if func.returns:
            lines.append("")
            lines.append("Returns:")
            type_hint = f"{func.returns.type}: " if func.returns.type else ""
            lines.append(f"    {type_hint}{func.returns.description}")
        
        if func.raises:
            lines.append("")
            lines.append("Raises:")
            for exc in func.raises:
                lines.append(f"    {exc.type}: {exc.description}")
        
        if func.examples:
            lines.append("")
            lines.append("Example:")
            for example in func.examples:
                lines.append(f"    >>> {example.code}")
                if example.output:
                    lines.append(f"    {example.output}")
        
        if func.notes:
            lines.append("")
            lines.append("Note:")
            for note in func.notes:
                lines.append(f"    {note}")
        
        lines.append('"""')
        return "\n".join(lines)
    
    def _numpy_function(self, func: FunctionDocumentation) -> str:
        """Generate NumPy-style docstring."""
        lines = [f'"""{func.summary}']
        
        if func.description:
            lines.append("")
            lines.append(func.description)
        
        if func.parameters:
            lines.append("")
            lines.append("Parameters")
            lines.append("----------")
            for param in func.parameters:
                type_hint = f" : {param.type}" if param.type else ""
                lines.append(f"{param.name}{type_hint}")
                lines.append(f"    {param.description}")
        
        if func.returns:
            lines.append("")
            lines.append("Returns")
            lines.append("-------")
            type_hint = func.returns.type if func.returns.type else "object"
            lines.append(type_hint)
            lines.append(f"    {func.returns.description}")
        
        if func.raises:
            lines.append("")
            lines.append("Raises")
            lines.append("------")
            for exc in func.raises:
                lines.append(exc.type)
                lines.append(f"    {exc.description}")
        
        if func.examples:
            lines.append("")
            lines.append("Examples")
            lines.append("--------")
            for example in func.examples:
                lines.append(f">>> {example.code}")
                if example.output:
                    lines.append(example.output)
        
        lines.append('"""')
        return "\n".join(lines)
    
    def _sphinx_function(self, func: FunctionDocumentation) -> str:
        """Generate Sphinx-style docstring."""
        lines = [f'"""{func.summary}']
        
        if func.description:
            lines.append("")
            lines.append(func.description)
        
        if func.parameters:
            lines.append("")
            for param in func.parameters:
                lines.append(f":param {param.name}: {param.description}")
                if param.type:
                    lines.append(f":type {param.name}: {param.type}")
        
        if func.returns:
            lines.append(f":returns: {func.returns.description}")
            if func.returns.type:
                lines.append(f":rtype: {func.returns.type}")
        
        if func.raises:
            for exc in func.raises:
                lines.append(f":raises {exc.type}: {exc.description}")
        
        lines.append('"""')
        return "\n".join(lines)
    
    def _jsdoc_function(self, func: FunctionDocumentation) -> str:
        """Generate JSDoc-style docstring."""
        lines = ["/**", f" * {func.summary}"]
        
        if func.description:
            lines.append(" *")
            lines.append(f" * {func.description}")
        
        if func.parameters:
            lines.append(" *")
            for param in func.parameters:
                type_hint = f"{{{param.type}}} " if param.type else ""
                lines.append(f" * @param {type_hint}{param.name} - {param.description}")
        
        if func.returns:
            type_hint = f"{{{func.returns.type}}} " if func.returns.type else ""
            lines.append(f" * @returns {type_hint}{func.returns.description}")
        
        if func.raises:
            for exc in func.raises:
                lines.append(f" * @throws {{{exc.type}}} {exc.description}")
        
        if func.examples:
            lines.append(" *")
            lines.append(" * @example")
            for example in func.examples:
                lines.append(f" * {example.code}")
        
        lines.append(" */")
        return "\n".join(lines)
    
    def _javadoc_function(self, func: FunctionDocumentation) -> str:
        """Generate Javadoc-style docstring."""
        lines = ["/**", f" * {func.summary}"]
        
        if func.description:
            lines.append(" * <p>")
            lines.append(f" * {func.description}")
            lines.append(" * </p>")
        
        if func.parameters:
            lines.append(" *")
            for param in func.parameters:
                lines.append(f" * @param {param.name} {param.description}")
        
        if func.returns:
            lines.append(f" * @return {func.returns.description}")
        
        if func.raises:
            for exc in func.raises:
                lines.append(f" * @throws {exc.type} {exc.description}")
        
        if func.since:
            lines.append(f" * @since {func.since}")
        
        if func.deprecated:
            lines.append(f" * @deprecated {func.deprecated}")
        
        lines.append(" */")
        return "\n".join(lines)
    
    def _generate_class_docstring(
        self, 
        cls: ClassDocumentation, 
        config: DocumentationConfig
    ) -> str:
        """Generate class docstring."""
        if config.style in [DocStyle.GOOGLE, DocStyle.NUMPY]:
            return self._google_class(cls, config)
        elif config.style == DocStyle.JSDOC:
            return self._jsdoc_class(cls)
        else:
            return self._google_class(cls, config)
    
    def _google_class(self, cls: ClassDocumentation, config: DocumentationConfig) -> str:
        """Generate Google-style class docstring."""
        lines = [f'"""{cls.summary}']
        
        if cls.description:
            lines.append("")
            lines.append(cls.description)
        
        if cls.attributes:
            lines.append("")
            lines.append("Attributes:")
            for attr in cls.attributes:
                type_hint = f" ({attr.type})" if attr.type else ""
                lines.append(f"    {attr.name}{type_hint}: {attr.description}")
        
        if cls.examples:
            lines.append("")
            lines.append("Example:")
            for example in cls.examples:
                for line in example.code.split("\n"):
                    lines.append(f"    {line}")
        
        lines.append('"""')
        return "\n".join(lines)
    
    def _jsdoc_class(self, cls: ClassDocumentation) -> str:
        """Generate JSDoc-style class docstring."""
        lines = ["/**", f" * {cls.summary}"]
        
        if cls.description:
            lines.append(" *")
            lines.append(f" * {cls.description}")
        
        lines.append(" *")
        lines.append(" * @class")
        
        if cls.bases:
            for base in cls.bases:
                lines.append(f" * @extends {base}")
        
        lines.append(" */")
        return "\n".join(lines)


class APIDocGenerator(BaseDocGenerator):
    """Generates API documentation (OpenAPI, etc.)."""
    
    def generate(self, data: APIDocumentation, config: DocumentationConfig) -> str:
        """Generate API documentation."""
        if config.format == DocFormat.OPENAPI:
            return self._to_openapi(data)
        elif config.format == DocFormat.MARKDOWN:
            return self._to_markdown(data)
        else:
            return self._to_markdown(data)
    
    def _to_openapi(self, api: APIDocumentation) -> str:
        """Generate OpenAPI 3.0 specification."""
        import json
        
        spec = {
            "openapi": "3.0.3",
            "info": {
                "title": api.title,
                "version": api.version,
                "description": api.description or "",
            },
            "servers": [{"url": api.base_url}] if api.base_url else [],
            "paths": {},
            "components": {
                "schemas": api.schemas,
                "securitySchemes": api.security_schemes,
            },
            "tags": api.tags,
        }
        
        for endpoint in api.endpoints:
            path = endpoint.path
            if path not in spec["paths"]:
                spec["paths"][path] = {}
            
            operation = {
                "summary": endpoint.summary,
                "description": endpoint.description or "",
                "tags": endpoint.tags,
                "parameters": [
                    {
                        "name": p.name,
                        "in": "query",  # Could be path, header, cookie
                        "required": p.required,
                        "description": p.description,
                        "schema": {"type": p.type or "string"},
                    }
                    for p in endpoint.parameters
                ],
                "responses": endpoint.responses,
            }
            
            if endpoint.request_body:
                operation["requestBody"] = endpoint.request_body
            
            if endpoint.security:
                operation["security"] = [{s: [] for s in endpoint.security}]
            
            if endpoint.deprecated:
                operation["deprecated"] = True
            
            spec["paths"][path][endpoint.method.lower()] = operation
        
        return json.dumps(spec, indent=2)
    
    def _to_markdown(self, api: APIDocumentation) -> str:
        """Generate Markdown API documentation."""
        lines = [
            f"# {api.title}",
            "",
            f"**Version:** {api.version}",
            "",
        ]
        
        if api.description:
            lines.extend([api.description, ""])
        
        if api.base_url:
            lines.extend([f"**Base URL:** `{api.base_url}`", ""])
        
        lines.extend(["## Endpoints", ""])
        
        # Group endpoints by tag
        tagged_endpoints: dict[str, list[EndpointDoc]] = {}
        for endpoint in api.endpoints:
            tag = endpoint.tags[0] if endpoint.tags else "Other"
            if tag not in tagged_endpoints:
                tagged_endpoints[tag] = []
            tagged_endpoints[tag].append(endpoint)
        
        for tag, endpoints in tagged_endpoints.items():
            lines.extend([f"### {tag}", ""])
            
            for endpoint in endpoints:
                lines.extend([
                    f"#### {endpoint.method.upper()} {endpoint.path}",
                    "",
                    endpoint.summary,
                    "",
                ])
                
                if endpoint.description:
                    lines.extend([endpoint.description, ""])
                
                if endpoint.parameters:
                    lines.extend(["**Parameters:**", ""])
                    lines.append("| Name | Type | Required | Description |")
                    lines.append("|------|------|----------|-------------|")
                    for param in endpoint.parameters:
                        req = "Yes" if param.required else "No"
                        lines.append(f"| {param.name} | {param.type or 'string'} | {req} | {param.description} |")
                    lines.append("")
                
                if endpoint.responses:
                    lines.extend(["**Responses:**", ""])
                    for status, response in endpoint.responses.items():
                        desc = response.get("description", "")
                        lines.append(f"- `{status}`: {desc}")
                    lines.append("")
                
                if endpoint.examples:
                    lines.extend(["**Example:**", ""])
                    for example in endpoint.examples:
                        lines.append(f"```{example.language}")
                        lines.append(example.code)
                        lines.append("```")
                        lines.append("")
        
        return "\n".join(lines)


class ReadmeGenerator(BaseDocGenerator):
    """Generates README documentation."""
    
    def generate(self, data: ModuleDocumentation, config: DocumentationConfig) -> str:
        """Generate README for a module/project."""
        lines = [
            f"# {data.name}",
            "",
            data.summary,
            "",
        ]
        
        if data.description:
            lines.extend([data.description, ""])
        
        # Installation
        lines.extend([
            "## Installation",
            "",
            "```bash",
            f"pip install {data.name.lower().replace(' ', '-')}",
            "```",
            "",
        ])
        
        # Quick Start
        if data.examples:
            lines.extend(["## Quick Start", ""])
            for example in data.examples[:3]:
                if example.title:
                    lines.append(f"### {example.title}")
                if example.description:
                    lines.append(example.description)
                lines.append(f"```{example.language}")
                lines.append(example.code)
                lines.append("```")
                lines.append("")
        
        # API Reference
        if data.classes or data.functions:
            lines.extend(["## API Reference", ""])
            
            if data.classes:
                lines.extend(["### Classes", ""])
                for cls in data.classes:
                    lines.append(f"#### `{cls.name}`")
                    lines.append(cls.summary)
                    lines.append("")
            
            if data.functions:
                lines.extend(["### Functions", ""])
                for func in data.functions:
                    lines.append(f"#### `{func.name}`")
                    lines.append(f"```python\n{func.signature}\n```")
                    lines.append(func.summary)
                    lines.append("")
        
        # Dependencies
        if data.dependencies:
            lines.extend(["## Dependencies", ""])
            for dep in data.dependencies:
                lines.append(f"- {dep}")
            lines.append("")
        
        return "\n".join(lines)


class OnboardingGenerator(BaseDocGenerator):
    """Generates onboarding guides for new developers."""
    
    def generate(self, data: dict, config: DocumentationConfig) -> OnboardingGuide:
        """Generate an onboarding guide."""
        project_name = data.get("name", "Project")
        
        sections = [
            OnboardingSection(
                title="Environment Setup",
                content=self._generate_setup_content(data),
                estimated_time="15 minutes",
            ),
            OnboardingSection(
                title="Project Structure",
                content=self._generate_structure_content(data),
                estimated_time="10 minutes",
            ),
            OnboardingSection(
                title="Core Concepts",
                content=self._generate_concepts_content(data),
                estimated_time="20 minutes",
            ),
            OnboardingSection(
                title="Development Workflow",
                content=self._generate_workflow_content(data),
                estimated_time="15 minutes",
            ),
            OnboardingSection(
                title="Running Tests",
                content=self._generate_testing_content(data),
                estimated_time="10 minutes",
            ),
        ]
        
        return OnboardingGuide(
            project_name=project_name,
            overview=data.get("description", f"Welcome to {project_name}!"),
            prerequisites=self._get_prerequisites(data),
            sections=sections,
            next_steps=[
                "Explore the codebase",
                "Pick up a starter issue",
                "Join the team chat",
                "Review the architecture docs",
            ],
            resources=[
                {"title": "Documentation", "url": "/docs"},
                {"title": "API Reference", "url": "/api"},
                {"title": "Contributing Guide", "url": "/CONTRIBUTING.md"},
            ],
            total_estimated_time="1-2 hours",
        )
    
    def _generate_setup_content(self, data: dict) -> str:
        """Generate environment setup section."""
        language = data.get("language", "python")
        
        if language == "python":
            return """
1. Clone the repository:
   ```bash
   git clone <repo-url>
   cd <project>
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # or `.venv\\Scripts\\activate` on Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -e ".[dev]"
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. Initialize the database:
   ```bash
   python -m app.db.init
   ```
"""
        elif language in ["javascript", "typescript"]:
            return """
1. Clone the repository:
   ```bash
   git clone <repo-url>
   cd <project>
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. Start the development server:
   ```bash
   npm run dev
   ```
"""
        return "Follow the project-specific setup instructions in the README."
    
    def _generate_structure_content(self, data: dict) -> str:
        """Generate project structure section."""
        return """
```
project/
├── src/                 # Source code
│   ├── api/            # API endpoints
│   ├── services/       # Business logic
│   ├── models/         # Data models
│   └── utils/          # Utilities
├── tests/              # Test files
├── docs/               # Documentation
├── scripts/            # Helper scripts
└── config/             # Configuration files
```

Key files:
- `src/main.py` - Application entry point
- `src/config.py` - Configuration settings
- `src/api/routes.py` - API route definitions
"""
    
    def _generate_concepts_content(self, data: dict) -> str:
        """Generate core concepts section."""
        return """
### Architecture Overview

The project follows a layered architecture:

1. **API Layer** - Handles HTTP requests and responses
2. **Service Layer** - Contains business logic
3. **Data Layer** - Manages data persistence

### Key Components

- **Services** - Encapsulate business logic and are the main way to interact with the system
- **Models** - Define data structures and validation
- **Repositories** - Handle data access and storage

### Design Patterns

- Dependency Injection for loose coupling
- Repository pattern for data access
- Service pattern for business logic
"""
    
    def _generate_workflow_content(self, data: dict) -> str:
        """Generate development workflow section."""
        return """
### Branch Strategy

- `main` - Production-ready code
- `develop` - Integration branch
- `feature/*` - New features
- `fix/*` - Bug fixes

### Making Changes

1. Create a feature branch:
   ```bash
   git checkout -b feature/my-feature
   ```

2. Make your changes and commit:
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

3. Push and create a pull request:
   ```bash
   git push origin feature/my-feature
   ```

### Code Review

- All changes require review before merging
- Ensure tests pass and coverage is maintained
- Follow the project's coding standards
"""
    
    def _generate_testing_content(self, data: dict) -> str:
        """Generate testing section."""
        return """
### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_service.py

# Run tests matching a pattern
pytest -k "test_user"
```

### Writing Tests

```python
def test_example():
    # Arrange
    service = MyService()
    
    # Act
    result = service.do_something()
    
    # Assert
    assert result == expected
```

### Test Categories

- Unit tests: Test individual components
- Integration tests: Test component interactions
- E2E tests: Test complete workflows
"""
    
    def _get_prerequisites(self, data: dict) -> list[str]:
        """Get prerequisites for the project."""
        language = data.get("language", "python")
        
        prereqs = ["Git installed", "Code editor (VS Code recommended)"]
        
        if language == "python":
            prereqs.extend([
                "Python 3.10 or higher",
                "pip package manager",
            ])
        elif language in ["javascript", "typescript"]:
            prereqs.extend([
                "Node.js 18 or higher",
                "npm or yarn",
            ])
        
        return prereqs
