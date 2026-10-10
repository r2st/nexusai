"""
Variable Injection Service

Safe variable substitution for prompt templates with:
- Type validation
- Injection prevention
- Default values
- Conditional sections
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
import re
import logging
import json

logger = logging.getLogger(__name__)


class VariableType(str, Enum):
    """Types of template variables."""
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    LIST = "list"
    OBJECT = "object"
    DATE = "date"
    CODE = "code"  # Special handling for code blocks
    MARKDOWN = "markdown"


@dataclass
class VariableDefinition:
    """Definition of a template variable."""
    name: str
    type: VariableType = VariableType.STRING
    required: bool = True
    default: Any = None
    description: str = ""
    
    # Validation
    max_length: Optional[int] = None
    min_length: Optional[int] = None
    pattern: Optional[str] = None  # Regex pattern
    allowed_values: Optional[List[Any]] = None
    
    # Sanitization
    sanitize: bool = True
    escape_html: bool = True
    strip_whitespace: bool = True
    
    # For lists
    max_items: Optional[int] = None
    item_type: Optional[VariableType] = None


@dataclass
class InjectionResult:
    """Result of variable injection."""
    success: bool
    output: str
    variables_used: Set[str] = field(default_factory=set)
    variables_missing: Set[str] = field(default_factory=set)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class VariableInjector:
    """
    Safe variable injection for prompt templates.
    
    Features:
    - Type validation
    - Injection attack prevention
    - Default values
    - Conditional sections
    - Loop expansion
    """
    
    # Patterns for variable syntax
    VAR_PATTERN = re.compile(r'\{\{\s*(\w+)(?:\s*\|\s*(\w+))?\s*\}\}')  # {{var}} or {{var|filter}}
    CONDITIONAL_PATTERN = re.compile(r'\{%\s*if\s+(\w+)\s*%\}(.*?)\{%\s*endif\s*%\}', re.DOTALL)
    LOOP_PATTERN = re.compile(r'\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}(.*?)\{%\s*endfor\s*%\}', re.DOTALL)
    
    # Dangerous patterns to block
    INJECTION_PATTERNS = [
        re.compile(r'<script', re.IGNORECASE),
        re.compile(r'javascript:', re.IGNORECASE),
        re.compile(r'on\w+\s*=', re.IGNORECASE),  # Event handlers
        re.compile(r'\{\{.*?\}\}'),  # Nested template syntax
        re.compile(r'\{%.*?%\}'),  # Nested control syntax
    ]
    
    # Built-in filters
    FILTERS: Dict[str, Callable[[Any], str]] = {
        'upper': lambda x: str(x).upper(),
        'lower': lambda x: str(x).lower(),
        'title': lambda x: str(x).title(),
        'trim': lambda x: str(x).strip(),
        'json': lambda x: json.dumps(x),
        'length': lambda x: str(len(x) if hasattr(x, '__len__') else 0),
        'first': lambda x: str(x[0]) if x else '',
        'last': lambda x: str(x[-1]) if x else '',
        'default': lambda x: str(x) if x else '',
        'escape': lambda x: _escape_html(str(x)),
        'code': lambda x: f"```\n{x}\n```",
        'truncate': lambda x: str(x)[:100] + '...' if len(str(x)) > 100 else str(x),
    }
    
    def __init__(
        self,
        definitions: Optional[Dict[str, VariableDefinition]] = None,
        strict_mode: bool = True,
        custom_filters: Optional[Dict[str, Callable]] = None,
    ):
        """
        Initialize the variable injector.
        
        Args:
            definitions: Variable definitions for validation
            strict_mode: Fail on missing required variables
            custom_filters: Additional filter functions
        """
        self.definitions = definitions or {}
        self.strict_mode = strict_mode
        self.filters = {**self.FILTERS}
        if custom_filters:
            self.filters.update(custom_filters)
    
    def inject(
        self,
        template: str,
        variables: Dict[str, Any],
        extra_definitions: Optional[Dict[str, VariableDefinition]] = None,
    ) -> InjectionResult:
        """
        Inject variables into a template.
        
        Args:
            template: Template string with {{variable}} placeholders
            variables: Variable values to inject
            extra_definitions: Additional variable definitions
            
        Returns:
            InjectionResult with processed template
        """
        result = InjectionResult(success=True, output=template)
        
        # Merge definitions
        definitions = {**self.definitions}
        if extra_definitions:
            definitions.update(extra_definitions)
        
        # Validate and sanitize variables
        validated_vars = {}
        for name, value in variables.items():
            definition = definitions.get(name)
            
            valid, sanitized, error = self._validate_and_sanitize(
                name, value, definition
            )
            
            if not valid:
                result.errors.append(error)
                if self.strict_mode:
                    result.success = False
                    return result
            else:
                validated_vars[name] = sanitized
        
        # Check for missing required variables
        for name, definition in definitions.items():
            if definition.required and name not in validated_vars:
                if definition.default is not None:
                    validated_vars[name] = definition.default
                else:
                    result.variables_missing.add(name)
                    if self.strict_mode:
                        result.errors.append(f"Missing required variable: {name}")
                        result.success = False
                        return result
        
        # Process template
        output = template
        
        # 1. Process conditionals first
        output = self._process_conditionals(output, validated_vars, result)
        
        # 2. Process loops
        output = self._process_loops(output, validated_vars, result)
        
        # 3. Process variable substitutions
        output = self._process_variables(output, validated_vars, result)
        
        # Check for injection attempts in final output
        for pattern in self.INJECTION_PATTERNS:
            if pattern.search(output):
                result.warnings.append("Potential injection pattern detected in output")
        
        result.output = output
        return result
    
    def _validate_and_sanitize(
        self,
        name: str,
        value: Any,
        definition: Optional[VariableDefinition],
    ) -> tuple[bool, Any, str]:
        """Validate and sanitize a variable value."""
        if definition is None:
            # No definition, basic sanitization only
            if isinstance(value, str):
                return True, _escape_html(value), ""
            return True, value, ""
        
        # Type checking
        expected_type = definition.type
        
        if expected_type == VariableType.STRING:
            if not isinstance(value, str):
                value = str(value)
        elif expected_type == VariableType.NUMBER:
            if not isinstance(value, (int, float)):
                try:
                    value = float(value)
                except (ValueError, TypeError):
                    return False, None, f"{name}: expected number, got {type(value).__name__}"
        elif expected_type == VariableType.BOOLEAN:
            if not isinstance(value, bool):
                value = bool(value)
        elif expected_type == VariableType.LIST:
            if not isinstance(value, (list, tuple)):
                return False, None, f"{name}: expected list, got {type(value).__name__}"
            if definition.max_items and len(value) > definition.max_items:
                value = value[:definition.max_items]
        elif expected_type == VariableType.OBJECT:
            if not isinstance(value, dict):
                return False, None, f"{name}: expected object, got {type(value).__name__}"
        elif expected_type == VariableType.DATE:
            if isinstance(value, str):
                try:
                    value = datetime.fromisoformat(value)
                except ValueError:
                    return False, None, f"{name}: invalid date format"
            if isinstance(value, datetime):
                value = value.isoformat()
        elif expected_type == VariableType.CODE:
            # Code blocks get special handling - less sanitization
            if not isinstance(value, str):
                value = str(value)
        elif expected_type == VariableType.MARKDOWN:
            # Markdown allows some formatting
            if not isinstance(value, str):
                value = str(value)
        
        # String-specific validation
        if isinstance(value, str):
            if definition.strip_whitespace:
                value = value.strip()
            
            if definition.min_length and len(value) < definition.min_length:
                return False, None, f"{name}: minimum length is {definition.min_length}"
            
            if definition.max_length and len(value) > definition.max_length:
                value = value[:definition.max_length]
            
            if definition.pattern:
                if not re.match(definition.pattern, value):
                    return False, None, f"{name}: does not match required pattern"
            
            # Check for injection attempts
            if definition.sanitize:
                for pattern in self.INJECTION_PATTERNS:
                    if pattern.search(value):
                        return False, None, f"{name}: contains disallowed content"
            
            if definition.escape_html and expected_type not in (VariableType.CODE, VariableType.MARKDOWN):
                value = _escape_html(value)
        
        # Allowed values check
        if definition.allowed_values and value not in definition.allowed_values:
            return False, None, f"{name}: value not in allowed list"
        
        return True, value, ""
    
    def _process_conditionals(
        self,
        template: str,
        variables: Dict[str, Any],
        result: InjectionResult,
    ) -> str:
        """Process {% if var %}...{% endif %} blocks."""
        
        def replace_conditional(match):
            var_name = match.group(1)
            content = match.group(2)
            
            value = variables.get(var_name)
            
            # Check truthiness
            if value:
                result.variables_used.add(var_name)
                return content
            return ""
        
        return self.CONDITIONAL_PATTERN.sub(replace_conditional, template)
    
    def _process_loops(
        self,
        template: str,
        variables: Dict[str, Any],
        result: InjectionResult,
    ) -> str:
        """Process {% for item in items %}...{% endfor %} blocks."""
        
        def replace_loop(match):
            item_var = match.group(1)
            list_var = match.group(2)
            content = match.group(3)
            
            items = variables.get(list_var, [])
            if not isinstance(items, (list, tuple)):
                result.warnings.append(f"Loop variable {list_var} is not iterable")
                return ""
            
            result.variables_used.add(list_var)
            
            output_parts = []
            for item in items:
                # Replace {{item_var}} in content
                item_content = content.replace(f'{{{{{item_var}}}}}', str(item))
                output_parts.append(item_content)
            
            return ''.join(output_parts)
        
        return self.LOOP_PATTERN.sub(replace_loop, template)
    
    def _process_variables(
        self,
        template: str,
        variables: Dict[str, Any],
        result: InjectionResult,
    ) -> str:
        """Process {{variable}} and {{variable|filter}} substitutions."""
        
        def replace_var(match):
            var_name = match.group(1)
            filter_name = match.group(2)
            
            if var_name not in variables:
                result.variables_missing.add(var_name)
                if self.strict_mode:
                    return match.group(0)  # Keep original
                return ""
            
            value = variables[var_name]
            result.variables_used.add(var_name)
            
            # Apply filter if specified
            if filter_name and filter_name in self.filters:
                try:
                    value = self.filters[filter_name](value)
                except Exception as e:
                    result.warnings.append(f"Filter {filter_name} failed on {var_name}: {e}")
            
            return str(value)
        
        return self.VAR_PATTERN.sub(replace_var, template)
    
    def get_variables(self, template: str) -> Set[str]:
        """Extract all variable names from a template."""
        variables = set()
        
        # Variables
        for match in self.VAR_PATTERN.finditer(template):
            variables.add(match.group(1))
        
        # Conditionals
        for match in self.CONDITIONAL_PATTERN.finditer(template):
            variables.add(match.group(1))
        
        # Loops
        for match in self.LOOP_PATTERN.finditer(template):
            variables.add(match.group(2))
        
        return variables
    
    def validate_template(self, template: str) -> List[str]:
        """Validate a template for syntax errors."""
        errors = []
        
        # Check for balanced conditionals
        if_count = len(re.findall(r'\{%\s*if\s+', template))
        endif_count = len(re.findall(r'\{%\s*endif\s*%\}', template))
        if if_count != endif_count:
            errors.append(f"Unbalanced if/endif: {if_count} if, {endif_count} endif")
        
        # Check for balanced loops
        for_count = len(re.findall(r'\{%\s*for\s+', template))
        endfor_count = len(re.findall(r'\{%\s*endfor\s*%\}', template))
        if for_count != endfor_count:
            errors.append(f"Unbalanced for/endfor: {for_count} for, {endfor_count} endfor")
        
        # Check for unknown filters
        for match in self.VAR_PATTERN.finditer(template):
            filter_name = match.group(2)
            if filter_name and filter_name not in self.filters:
                errors.append(f"Unknown filter: {filter_name}")
        
        return errors


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
        .replace("'", '&#x27;')
    )


# Convenience function
def inject_variables(
    template: str,
    variables: Dict[str, Any],
    strict: bool = True,
) -> str:
    """
    Simple variable injection.
    
    Args:
        template: Template with {{variable}} placeholders
        variables: Values to inject
        strict: Fail on missing variables
        
    Returns:
        Processed template string
    """
    injector = VariableInjector(strict_mode=strict)
    result = injector.inject(template, variables)
    
    if not result.success:
        raise ValueError(f"Variable injection failed: {result.errors}")
    
    return result.output
