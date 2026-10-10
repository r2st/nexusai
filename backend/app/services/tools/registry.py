"""
Tool Registry

Central registry for discovering and managing tools.
"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
import logging

from .base import Tool, ToolMetadata, ToolCategory, ToolClass

logger = logging.getLogger(__name__)


@dataclass
class RegisteredTool:
    """A tool registered in the registry."""
    tool_class: ToolClass
    metadata: ToolMetadata
    is_enabled: bool = True
    tags: Set[str] = field(default_factory=set)


class ToolRegistry:
    """
    Central registry for tool discovery and management.
    
    Features:
    - Register tools by class
    - Discover tools by category, tags, or permissions
    - Enable/disable tools dynamically
    - Get tool instances for execution
    """
    
    def __init__(self):
        self._tools: Dict[str, RegisteredTool] = {}
        self._by_category: Dict[ToolCategory, Set[str]] = {cat: set() for cat in ToolCategory}
        self._by_tag: Dict[str, Set[str]] = {}
    
    def register(
        self,
        tool_class: ToolClass,
        tags: Optional[Set[str]] = None,
        enabled: bool = True,
    ) -> None:
        """
        Register a tool class.
        
        Args:
            tool_class: The tool class to register
            tags: Optional tags for discovery
            enabled: Whether the tool is enabled by default
        """
        metadata = tool_class.get_metadata()
        name = metadata.name
        
        if name in self._tools:
            logger.warning(f"Tool '{name}' is already registered, overwriting")
        
        registered = RegisteredTool(
            tool_class=tool_class,
            metadata=metadata,
            is_enabled=enabled,
            tags=tags or set(),
        )
        
        self._tools[name] = registered
        self._by_category[metadata.category].add(name)
        
        for tag in registered.tags:
            if tag not in self._by_tag:
                self._by_tag[tag] = set()
            self._by_tag[tag].add(name)
        
        logger.info(f"Registered tool: {name} (category={metadata.category.value})")
    
    def unregister(self, name: str) -> bool:
        """Unregister a tool by name."""
        if name not in self._tools:
            return False
        
        registered = self._tools[name]
        
        # Remove from category index
        self._by_category[registered.metadata.category].discard(name)
        
        # Remove from tag indices
        for tag in registered.tags:
            if tag in self._by_tag:
                self._by_tag[tag].discard(name)
        
        del self._tools[name]
        logger.info(f"Unregistered tool: {name}")
        return True
    
    def get(self, name: str) -> Optional[RegisteredTool]:
        """Get a registered tool by name."""
        return self._tools.get(name)
    
    def get_tool_class(self, name: str) -> Optional[ToolClass]:
        """Get a tool class by name."""
        registered = self._tools.get(name)
        return registered.tool_class if registered else None
    
    def get_instance(self, name: str) -> Optional[Tool]:
        """Get a new instance of a tool."""
        tool_class = self.get_tool_class(name)
        return tool_class() if tool_class else None
    
    def list_all(self, enabled_only: bool = True) -> List[RegisteredTool]:
        """List all registered tools."""
        tools = list(self._tools.values())
        if enabled_only:
            tools = [t for t in tools if t.is_enabled]
        return tools
    
    def list_names(self, enabled_only: bool = True) -> List[str]:
        """List all tool names."""
        if enabled_only:
            return [name for name, t in self._tools.items() if t.is_enabled]
        return list(self._tools.keys())
    
    def list_by_category(
        self,
        category: ToolCategory,
        enabled_only: bool = True,
    ) -> List[RegisteredTool]:
        """List tools by category."""
        names = self._by_category.get(category, set())
        tools = [self._tools[name] for name in names if name in self._tools]
        if enabled_only:
            tools = [t for t in tools if t.is_enabled]
        return tools
    
    def list_by_tag(self, tag: str, enabled_only: bool = True) -> List[RegisteredTool]:
        """List tools by tag."""
        names = self._by_tag.get(tag, set())
        tools = [self._tools[name] for name in names if name in self._tools]
        if enabled_only:
            tools = [t for t in tools if t.is_enabled]
        return tools
    
    def list_by_permission(
        self,
        user_permissions: List[str],
        enabled_only: bool = True,
    ) -> List[RegisteredTool]:
        """List tools the user has permission to use."""
        result = []
        for tool in self._tools.values():
            if enabled_only and not tool.is_enabled:
                continue
            
            # Check if user has all required permissions
            required = set(tool.metadata.required_permissions)
            if required.issubset(set(user_permissions)):
                result.append(tool)
        
        return result
    
    def enable(self, name: str) -> bool:
        """Enable a tool."""
        if name not in self._tools:
            return False
        self._tools[name].is_enabled = True
        return True
    
    def disable(self, name: str) -> bool:
        """Disable a tool."""
        if name not in self._tools:
            return False
        self._tools[name].is_enabled = False
        return True
    
    def add_tag(self, name: str, tag: str) -> bool:
        """Add a tag to a tool."""
        if name not in self._tools:
            return False
        
        self._tools[name].tags.add(tag)
        
        if tag not in self._by_tag:
            self._by_tag[tag] = set()
        self._by_tag[tag].add(name)
        
        return True
    
    def remove_tag(self, name: str, tag: str) -> bool:
        """Remove a tag from a tool."""
        if name not in self._tools:
            return False
        
        self._tools[name].tags.discard(tag)
        
        if tag in self._by_tag:
            self._by_tag[tag].discard(name)
        
        return True
    
    def get_openai_functions(
        self,
        names: Optional[List[str]] = None,
        enabled_only: bool = True,
    ) -> List[Dict]:
        """Get tools in OpenAI function calling format."""
        tools = []
        
        for name, registered in self._tools.items():
            if names and name not in names:
                continue
            if enabled_only and not registered.is_enabled:
                continue
            
            instance = registered.tool_class()
            tools.append(instance.to_openai_function())
        
        return tools
    
    def get_anthropic_tools(
        self,
        names: Optional[List[str]] = None,
        enabled_only: bool = True,
    ) -> List[Dict]:
        """Get tools in Anthropic tool calling format."""
        tools = []
        
        for name, registered in self._tools.items():
            if names and name not in names:
                continue
            if enabled_only and not registered.is_enabled:
                continue
            
            instance = registered.tool_class()
            tools.append(instance.to_anthropic_tool())
        
        return tools
    
    def search(
        self,
        query: str,
        enabled_only: bool = True,
    ) -> List[RegisteredTool]:
        """Search tools by name or description."""
        query_lower = query.lower()
        results = []
        
        for registered in self._tools.values():
            if enabled_only and not registered.is_enabled:
                continue
            
            # Search in name and description
            if (
                query_lower in registered.metadata.name.lower() or
                query_lower in registered.metadata.description.lower()
            ):
                results.append(registered)
        
        return results
    
    def get_stats(self) -> Dict:
        """Get registry statistics."""
        total = len(self._tools)
        enabled = sum(1 for t in self._tools.values() if t.is_enabled)
        
        by_category = {
            cat.value: len(names)
            for cat, names in self._by_category.items()
        }
        
        return {
            "total_tools": total,
            "enabled_tools": enabled,
            "disabled_tools": total - enabled,
            "by_category": by_category,
            "tags": list(self._by_tag.keys()),
        }


# Global registry instance
tool_registry = ToolRegistry()


def register_tool(
    tags: Optional[Set[str]] = None,
    enabled: bool = True,
):
    """Decorator to register a tool class."""
    def decorator(cls: ToolClass) -> ToolClass:
        tool_registry.register(cls, tags=tags, enabled=enabled)
        return cls
    return decorator
