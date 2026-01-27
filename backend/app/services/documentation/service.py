"""
Documentation Service

Main service for automated documentation generation.
"""

import logging
import time
from typing import Optional, Any
from functools import lru_cache

from .models import (
    DocFormat,
    DocStyle,
    DocumentationConfig,
    DocumentationResult,
    ModuleDocumentation,
    ClassDocumentation,
    FunctionDocumentation,
    APIDocumentation,
    OnboardingGuide,
    ParameterDoc,
    ReturnDoc,
    ExampleDoc,
)
from .generators import (
    DocstringGenerator,
    APIDocGenerator,
    ReadmeGenerator,
    OnboardingGenerator,
)

logger = logging.getLogger(__name__)


class DocumentationService:
    """
    Service for automated documentation generation.
    
    Capabilities:
    - Docstring generation for functions and classes
    - API documentation (OpenAPI, Markdown)
    - README generation
    - Onboarding guide generation
    - LLM-enhanced descriptions
    """
    
    def __init__(self, llm_service: Optional[Any] = None):
        self.llm_service = llm_service
        self.docstring_generator = DocstringGenerator()
        self.api_generator = APIDocGenerator()
        self.readme_generator = ReadmeGenerator()
        self.onboarding_generator = OnboardingGenerator()
    
    async def generate_documentation(
        self,
        analysis_result: dict,
        config: DocumentationConfig,
    ) -> DocumentationResult:
        """
        Generate comprehensive documentation from code analysis.
        
        Args:
            analysis_result: Results from code analysis
            config: Documentation configuration
            
        Returns:
            DocumentationResult with generated documentation
        """
        start_time = time.time()
        
        result = DocumentationResult(
            project_name=analysis_result.get("name", "Project"),
            format=config.format,
        )
        
        # Process modules
        for module_data in analysis_result.get("modules", []):
            module_doc = await self._process_module(module_data, config)
            result.modules.append(module_doc)
        
        # Generate API docs if endpoints exist
        if analysis_result.get("endpoints"):
            result.api = await self._generate_api_docs(analysis_result, config)
        
        # Generate onboarding guide
        if config.sections and any("onboarding" in s.value for s in config.sections):
            result.onboarding = await self._generate_onboarding(analysis_result, config)
        
        # Render final output
        if config.single_file:
            result.content = await self._render_single_file(result, config)
        else:
            result.files = await self._render_multiple_files(result, config)
        
        # Calculate stats
        result.stats = {
            "modules": len(result.modules),
            "classes": sum(len(m.classes) for m in result.modules),
            "functions": sum(len(m.functions) for m in result.modules),
            "endpoints": len(result.api.endpoints) if result.api else 0,
        }
        
        result.generation_time_ms = (time.time() - start_time) * 1000
        
        logger.info(
            f"Generated documentation for {result.project_name}: "
            f"{result.stats['modules']} modules, "
            f"{result.stats['classes']} classes, "
            f"{result.stats['functions']} functions "
            f"in {result.generation_time_ms:.2f}ms"
        )
        
        return result
    
    async def _process_module(
        self,
        module_data: dict,
        config: DocumentationConfig,
    ) -> ModuleDocumentation:
        """Process a module and generate documentation."""
        module_doc = ModuleDocumentation(
            name=module_data.get("name", "module"),
            path=module_data.get("path", ""),
            summary=module_data.get("summary", ""),
            description=module_data.get("description"),
            dependencies=module_data.get("dependencies", []),
            exports=module_data.get("exports", []),
        )
        
        # Process classes
        for cls_data in module_data.get("classes", []):
            if not config.include_private and cls_data.get("name", "").startswith("_"):
                continue
            
            cls_doc = await self._process_class(cls_data, config)
            module_doc.classes.append(cls_doc)
        
        # Process functions
        for func_data in module_data.get("functions", []):
            if not config.include_private and func_data.get("name", "").startswith("_"):
                continue
            
            func_doc = await self._process_function(func_data, config)
            module_doc.functions.append(func_doc)
        
        # Enhance with LLM if configured
        if config.use_llm and config.llm_enhance_descriptions and self.llm_service:
            module_doc = await self._llm_enhance_module(module_doc, config)
        
        return module_doc
    
    async def _process_class(
        self,
        cls_data: dict,
        config: DocumentationConfig,
    ) -> ClassDocumentation:
        """Process a class and generate documentation."""
        cls_doc = ClassDocumentation(
            name=cls_data.get("name", "Class"),
            summary=cls_data.get("summary", cls_data.get("docstring", "").split("\n")[0]),
            description=cls_data.get("description"),
            bases=cls_data.get("bases", []),
        )
        
        # Process attributes
        for attr in cls_data.get("attributes", []):
            cls_doc.attributes.append(ParameterDoc(
                name=attr.get("name", ""),
                type=attr.get("type"),
                description=attr.get("description", ""),
            ))
        
        # Process methods
        for method_data in cls_data.get("methods", []):
            if not config.include_private and method_data.get("name", "").startswith("_"):
                if method_data.get("name") != "__init__":
                    continue
            
            method_doc = await self._process_function(method_data, config)
            cls_doc.methods.append(method_doc)
        
        return cls_doc
    
    async def _process_function(
        self,
        func_data: dict,
        config: DocumentationConfig,
    ) -> FunctionDocumentation:
        """Process a function and generate documentation."""
        func_doc = FunctionDocumentation(
            name=func_data.get("name", "function"),
            signature=func_data.get("signature", ""),
            summary=func_data.get("summary", func_data.get("docstring", "").split("\n")[0]),
            description=func_data.get("description"),
            deprecated=func_data.get("deprecated"),
            since=func_data.get("since"),
        )
        
        # Process parameters
        for param in func_data.get("parameters", []):
            param_type = param.get("type")
            if not param_type and config.infer_types:
                param_type = self._infer_type(param.get("default"))
            
            func_doc.parameters.append(ParameterDoc(
                name=param.get("name", ""),
                type=param_type,
                description=param.get("description", ""),
                default=param.get("default"),
                required=param.get("required", param.get("default") is None),
            ))
        
        # Process return
        if func_data.get("returns"):
            ret = func_data["returns"]
            func_doc.returns = ReturnDoc(
                type=ret.get("type"),
                description=ret.get("description", ""),
            )
        
        # Generate examples if configured
        if config.generate_examples and config.llm_generate_examples and self.llm_service:
            func_doc.examples = await self._llm_generate_examples(func_doc, config)
        
        return func_doc
    
    async def _generate_api_docs(
        self,
        analysis_result: dict,
        config: DocumentationConfig,
    ) -> APIDocumentation:
        """Generate API documentation."""
        api_doc = APIDocumentation(
            title=f"{analysis_result.get('name', 'API')} API",
            version=analysis_result.get("version", "1.0.0"),
            description=analysis_result.get("api_description"),
            base_url=analysis_result.get("base_url"),
        )
        
        # Process endpoints
        for endpoint_data in analysis_result.get("endpoints", []):
            from .models import EndpointDoc
            
            endpoint = EndpointDoc(
                method=endpoint_data.get("method", "GET"),
                path=endpoint_data.get("path", "/"),
                summary=endpoint_data.get("summary", ""),
                description=endpoint_data.get("description"),
                tags=endpoint_data.get("tags", []),
                deprecated=endpoint_data.get("deprecated", False),
            )
            
            # Process parameters
            for param in endpoint_data.get("parameters", []):
                endpoint.parameters.append(ParameterDoc(
                    name=param.get("name", ""),
                    type=param.get("type", "string"),
                    description=param.get("description", ""),
                    required=param.get("required", False),
                ))
            
            endpoint.responses = endpoint_data.get("responses", {"200": {"description": "Success"}})
            
            api_doc.endpoints.append(endpoint)
        
        return api_doc
    
    async def _generate_onboarding(
        self,
        analysis_result: dict,
        config: DocumentationConfig,
    ) -> OnboardingGuide:
        """Generate onboarding guide."""
        return self.onboarding_generator.generate(analysis_result, config)
    
    async def _render_single_file(
        self,
        result: DocumentationResult,
        config: DocumentationConfig,
    ) -> str:
        """Render documentation as a single file."""
        lines = [f"# {result.project_name} Documentation", ""]
        
        # Table of contents
        lines.extend(["## Table of Contents", ""])
        for module in result.modules:
            lines.append(f"- [{module.name}](#{module.name.lower().replace(' ', '-')})")
        if result.api:
            lines.append("- [API Reference](#api-reference)")
        lines.append("")
        
        # Modules
        for module in result.modules:
            lines.extend([f"## {module.name}", "", module.summary, ""])
            if module.description:
                lines.extend([module.description, ""])
            
            if module.classes:
                lines.extend(["### Classes", ""])
                for cls in module.classes:
                    lines.extend([f"#### {cls.name}", "", cls.summary, ""])
            
            if module.functions:
                lines.extend(["### Functions", ""])
                for func in module.functions:
                    lines.extend([
                        f"#### `{func.name}`",
                        "",
                        f"```python\n{func.signature}\n```",
                        "",
                        func.summary,
                        "",
                    ])
        
        # API Reference
        if result.api:
            lines.append(self.api_generator._to_markdown(result.api))
        
        return "\n".join(lines)
    
    async def _render_multiple_files(
        self,
        result: DocumentationResult,
        config: DocumentationConfig,
    ) -> dict[str, str]:
        """Render documentation as multiple files."""
        files = {}
        
        # Index/README
        files["index.md"] = self._render_index(result)
        
        # Module files
        for module in result.modules:
            filename = f"modules/{module.name.lower().replace(' ', '_')}.md"
            files[filename] = self._render_module(module, config)
        
        # API reference
        if result.api:
            files["api/index.md"] = self.api_generator._to_markdown(result.api)
            if config.format == DocFormat.OPENAPI:
                files["api/openapi.json"] = self.api_generator._to_openapi(result.api)
        
        # Onboarding guide
        if result.onboarding:
            files["onboarding.md"] = self._render_onboarding(result.onboarding)
        
        return files
    
    def _render_index(self, result: DocumentationResult) -> str:
        """Render index page."""
        lines = [
            f"# {result.project_name}",
            "",
            "## Documentation",
            "",
            "### Modules",
            "",
        ]
        
        for module in result.modules:
            filename = f"modules/{module.name.lower().replace(' ', '_')}.md"
            lines.append(f"- [{module.name}]({filename}) - {module.summary}")
        
        if result.api:
            lines.extend([
                "",
                "### API Reference",
                "",
                "- [API Documentation](api/index.md)",
            ])
        
        return "\n".join(lines)
    
    def _render_module(self, module: ModuleDocumentation, config: DocumentationConfig) -> str:
        """Render a module documentation file."""
        lines = [f"# {module.name}", "", module.summary, ""]
        
        if module.description:
            lines.extend([module.description, ""])
        
        if module.classes:
            lines.extend(["## Classes", ""])
            for cls in module.classes:
                lines.extend([
                    f"### {cls.name}",
                    "",
                    cls.summary,
                    "",
                ])
                
                if cls.attributes:
                    lines.extend(["**Attributes:**", ""])
                    for attr in cls.attributes:
                        lines.append(f"- `{attr.name}` ({attr.type}): {attr.description}")
                    lines.append("")
                
                if cls.methods:
                    lines.extend(["**Methods:**", ""])
                    for method in cls.methods:
                        lines.append(f"- `{method.name}()`: {method.summary}")
                    lines.append("")
        
        if module.functions:
            lines.extend(["## Functions", ""])
            for func in module.functions:
                lines.extend([
                    f"### {func.name}",
                    "",
                    f"```python\n{func.signature}\n```",
                    "",
                    func.summary,
                    "",
                ])
                
                if func.parameters:
                    lines.extend(["**Parameters:**", ""])
                    for param in func.parameters:
                        lines.append(f"- `{param.name}` ({param.type}): {param.description}")
                    lines.append("")
                
                if func.returns:
                    lines.extend([
                        "**Returns:**",
                        "",
                        f"- `{func.returns.type}`: {func.returns.description}",
                        "",
                    ])
        
        return "\n".join(lines)
    
    def _render_onboarding(self, guide: OnboardingGuide) -> str:
        """Render onboarding guide."""
        lines = [
            f"# {guide.project_name} Onboarding Guide",
            "",
            guide.overview,
            "",
            f"**Estimated Time:** {guide.total_estimated_time}",
            "",
            "## Prerequisites",
            "",
        ]
        
        for prereq in guide.prerequisites:
            lines.append(f"- {prereq}")
        lines.append("")
        
        for i, section in enumerate(guide.sections, 1):
            lines.extend([
                f"## {i}. {section.title}",
                "",
                f"*Estimated time: {section.estimated_time}*" if section.estimated_time else "",
                "",
                section.content,
                "",
            ])
        
        lines.extend(["## Next Steps", ""])
        for step in guide.next_steps:
            lines.append(f"- {step}")
        
        lines.extend(["", "## Resources", ""])
        for resource in guide.resources:
            lines.append(f"- [{resource['title']}]({resource['url']})")
        
        return "\n".join(lines)
    
    def _infer_type(self, default_value: Any) -> Optional[str]:
        """Infer type from default value."""
        if default_value is None:
            return None
        if isinstance(default_value, bool):
            return "bool"
        if isinstance(default_value, int):
            return "int"
        if isinstance(default_value, float):
            return "float"
        if isinstance(default_value, str):
            return "str"
        if isinstance(default_value, list):
            return "list"
        if isinstance(default_value, dict):
            return "dict"
        return None
    
    async def _llm_enhance_module(
        self,
        module: ModuleDocumentation,
        config: DocumentationConfig,
    ) -> ModuleDocumentation:
        """Enhance module documentation with LLM."""
        if not self.llm_service:
            return module
        
        # This would call the LLM service to enhance descriptions
        # For now, return as-is
        return module
    
    async def _llm_generate_examples(
        self,
        func: FunctionDocumentation,
        config: DocumentationConfig,
    ) -> list[ExampleDoc]:
        """Generate examples using LLM."""
        if not self.llm_service:
            return []
        
        # This would call the LLM service to generate examples
        # For now, return empty list
        return []
    
    async def generate_docstring(
        self,
        code: str,
        language: str,
        style: DocStyle = DocStyle.GOOGLE,
    ) -> str:
        """
        Generate a docstring for a code snippet.
        
        Args:
            code: The code to document
            language: Programming language
            style: Docstring style
            
        Returns:
            Generated docstring
        """
        # Parse the code to extract function/class info
        # Then generate docstring using the appropriate generator
        
        # Placeholder - in real implementation would parse code
        func_doc = FunctionDocumentation(
            name="function",
            signature=code.split("\n")[0],
            summary="Function description",
        )
        
        config = DocumentationConfig(style=style)
        return self.docstring_generator.generate(func_doc, config)


@lru_cache()
def get_documentation_service() -> DocumentationService:
    """Get the documentation service singleton."""
    return DocumentationService()
