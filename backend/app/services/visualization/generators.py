"""
Diagram Generators

Specialized generators for different diagram types.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional

from .models import (
    ArchitectureGraph,
    DiagramConfig,
    DiagramResult,
    DiagramType,
    DiagramFormat,
    NodeData,
    EdgeData,
    NodeType,
    EdgeType,
)

logger = logging.getLogger(__name__)


class BaseDiagramGenerator(ABC):
    """Base class for diagram generators."""
    
    @abstractmethod
    def generate(self, graph: ArchitectureGraph, config: DiagramConfig) -> DiagramResult:
        """Generate a diagram from the architecture graph."""
        pass
    
    def _filter_graph(self, graph: ArchitectureGraph, config: DiagramConfig) -> ArchitectureGraph:
        """Apply filters to the graph based on configuration."""
        filtered = ArchitectureGraph(metadata=graph.metadata.copy())
        
        for node in graph.nodes:
            # Apply include/exclude patterns
            if config.include_patterns:
                if not any(p in (node.path or node.id) for p in config.include_patterns):
                    continue
            if config.exclude_patterns:
                if any(p in (node.path or node.id) for p in config.exclude_patterns):
                    continue
            filtered.add_node(node)
        
        # Filter edges to only include those between included nodes
        node_ids = {n.id for n in filtered.nodes}
        for edge in graph.edges:
            if edge.source in node_ids and edge.target in node_ids:
                filtered.add_edge(edge)
        
        # Apply min_connections filter
        if config.min_connections > 0:
            connection_counts = {}
            for edge in filtered.edges:
                connection_counts[edge.source] = connection_counts.get(edge.source, 0) + 1
                connection_counts[edge.target] = connection_counts.get(edge.target, 0) + 1
            
            filtered.nodes = [
                n for n in filtered.nodes 
                if connection_counts.get(n.id, 0) >= config.min_connections
            ]
            node_ids = {n.id for n in filtered.nodes}
            filtered.edges = [
                e for e in filtered.edges 
                if e.source in node_ids and e.target in node_ids
            ]
        
        return filtered


class DependencyDiagramGenerator(BaseDiagramGenerator):
    """Generates dependency/import diagrams."""
    
    def generate(self, graph: ArchitectureGraph, config: DiagramConfig) -> DiagramResult:
        """Generate a dependency diagram in the specified format."""
        filtered = self._filter_graph(graph, config)
        
        if config.format == DiagramFormat.MERMAID:
            content = self._to_mermaid(filtered, config)
        elif config.format == DiagramFormat.PLANTUML:
            content = self._to_plantuml(filtered, config)
        elif config.format == DiagramFormat.DOT:
            content = self._to_dot(filtered, config)
        elif config.format == DiagramFormat.D2:
            content = self._to_d2(filtered, config)
        else:
            content = self._to_mermaid(filtered, config)
        
        return DiagramResult(
            diagram_type=DiagramType.DEPENDENCY,
            format=config.format,
            content=content,
            graph=filtered,
            node_count=len(filtered.nodes),
            edge_count=len(filtered.edges),
        )
    
    def _to_mermaid(self, graph: ArchitectureGraph, config: DiagramConfig) -> str:
        """Convert to Mermaid flowchart format."""
        lines = [f"flowchart {config.direction}"]
        
        if config.title:
            lines.append(f"    %% {config.title}")
        
        # Group nodes if configured
        if config.group_by:
            groups = self._group_nodes(graph.nodes, config.group_by)
            for group_name, nodes in groups.items():
                lines.append(f"    subgraph {self._sanitize_id(group_name)}[\"{group_name}\"]")
                for node in nodes:
                    lines.append(f"        {self._node_to_mermaid(node, config)}")
                lines.append("    end")
        else:
            for node in graph.nodes:
                lines.append(f"    {self._node_to_mermaid(node, config)}")
        
        # Add edges
        for edge in graph.edges:
            arrow = self._get_mermaid_arrow(edge.type)
            label = f"|{edge.label}|" if edge.label and config.show_labels else ""
            lines.append(f"    {self._sanitize_id(edge.source)} {arrow}{label} {self._sanitize_id(edge.target)}")
        
        return "\n".join(lines)
    
    def _node_to_mermaid(self, node: NodeData, config: DiagramConfig) -> str:
        """Convert a node to Mermaid format."""
        node_id = self._sanitize_id(node.id)
        label = node.label
        
        if config.show_metrics and node.metrics:
            metrics_str = ", ".join(f"{k}:{v}" for k, v in node.metrics.items())
            label = f"{label}\\n({metrics_str})"
        
        # Choose shape based on node type
        shape_map = {
            NodeType.MODULE: (f"{node_id}[[\"{label}\"]]"),
            NodeType.CLASS: (f"{node_id}[/\"{label}\"/]"),
            NodeType.FUNCTION: (f"{node_id}((\"{label}\"))"),
            NodeType.FILE: (f"{node_id}[\"{label}\"]"),
            NodeType.PACKAGE: (f"{node_id}[[\"{label}\"]]"),
            NodeType.SERVICE: (f"{node_id}{{\"{label}\"}}"),
            NodeType.DATABASE: (f"{node_id}[(\"{label}\")]"),
            NodeType.API: (f"{node_id}>\"{label}\"]"),
            NodeType.EXTERNAL: (f"{node_id}(\"{label}\")"),
        }
        
        return shape_map.get(node.type, f"{node_id}[\"{label}\"]")
    
    def _get_mermaid_arrow(self, edge_type: EdgeType) -> str:
        """Get Mermaid arrow style for edge type."""
        arrow_map = {
            EdgeType.IMPORTS: "-->",
            EdgeType.EXTENDS: "--|>",
            EdgeType.IMPLEMENTS: "..|>",
            EdgeType.CALLS: "-->",
            EdgeType.USES: "-.->",
            EdgeType.DEPENDS_ON: "-->",
            EdgeType.CONTAINS: "---",
            EdgeType.ASSOCIATED: "-.-",
        }
        return arrow_map.get(edge_type, "-->")
    
    def _to_plantuml(self, graph: ArchitectureGraph, config: DiagramConfig) -> str:
        """Convert to PlantUML format."""
        lines = ["@startuml"]
        
        if config.title:
            lines.append(f"title {config.title}")
        
        lines.append(f"left to right direction" if config.direction in ["LR", "RL"] else "")
        
        for node in graph.nodes:
            node_type = self._get_plantuml_type(node.type)
            lines.append(f'{node_type} "{node.label}" as {self._sanitize_id(node.id)}')
        
        for edge in graph.edges:
            arrow = self._get_plantuml_arrow(edge.type)
            label = f" : {edge.label}" if edge.label else ""
            lines.append(f"{self._sanitize_id(edge.source)} {arrow} {self._sanitize_id(edge.target)}{label}")
        
        lines.append("@enduml")
        return "\n".join(lines)
    
    def _get_plantuml_type(self, node_type: NodeType) -> str:
        """Get PlantUML component type."""
        type_map = {
            NodeType.MODULE: "component",
            NodeType.CLASS: "class",
            NodeType.FUNCTION: "usecase",
            NodeType.FILE: "file",
            NodeType.PACKAGE: "package",
            NodeType.SERVICE: "node",
            NodeType.DATABASE: "database",
            NodeType.API: "interface",
            NodeType.EXTERNAL: "cloud",
        }
        return type_map.get(node_type, "component")
    
    def _get_plantuml_arrow(self, edge_type: EdgeType) -> str:
        """Get PlantUML arrow style."""
        arrow_map = {
            EdgeType.IMPORTS: "-->",
            EdgeType.EXTENDS: "--|>",
            EdgeType.IMPLEMENTS: "..|>",
            EdgeType.CALLS: "->",
            EdgeType.USES: "..>",
            EdgeType.DEPENDS_ON: "-->",
            EdgeType.CONTAINS: "--",
            EdgeType.ASSOCIATED: "..",
        }
        return arrow_map.get(edge_type, "-->")
    
    def _to_dot(self, graph: ArchitectureGraph, config: DiagramConfig) -> str:
        """Convert to Graphviz DOT format."""
        direction = "LR" if config.direction in ["LR", "RL"] else "TB"
        lines = [
            "digraph G {",
            f"    rankdir={direction};",
            f"    nodesep={config.node_spacing / 72};",
            f"    ranksep={config.rank_spacing / 72};",
        ]
        
        if config.title:
            lines.append(f'    label="{config.title}";')
        
        for node in graph.nodes:
            shape = self._get_dot_shape(node.type)
            color = node.color or "#e0e0e0"
            lines.append(f'    {self._sanitize_id(node.id)} [label="{node.label}", shape={shape}, fillcolor="{color}", style=filled];')
        
        for edge in graph.edges:
            style = self._get_dot_style(edge.type)
            label = f', label="{edge.label}"' if edge.label else ""
            lines.append(f'    {self._sanitize_id(edge.source)} -> {self._sanitize_id(edge.target)} [{style}{label}];')
        
        lines.append("}")
        return "\n".join(lines)
    
    def _get_dot_shape(self, node_type: NodeType) -> str:
        """Get DOT shape for node type."""
        shape_map = {
            NodeType.MODULE: "box3d",
            NodeType.CLASS: "record",
            NodeType.FUNCTION: "ellipse",
            NodeType.FILE: "note",
            NodeType.PACKAGE: "folder",
            NodeType.SERVICE: "component",
            NodeType.DATABASE: "cylinder",
            NodeType.API: "cds",
            NodeType.EXTERNAL: "cloud",
        }
        return shape_map.get(node_type, "box")
    
    def _get_dot_style(self, edge_type: EdgeType) -> str:
        """Get DOT edge style."""
        style_map = {
            EdgeType.IMPORTS: "style=solid",
            EdgeType.EXTENDS: "style=solid, arrowhead=empty",
            EdgeType.IMPLEMENTS: "style=dashed, arrowhead=empty",
            EdgeType.CALLS: "style=solid",
            EdgeType.USES: "style=dashed",
            EdgeType.DEPENDS_ON: "style=solid",
            EdgeType.CONTAINS: "style=solid, arrowhead=none",
            EdgeType.ASSOCIATED: "style=dotted",
        }
        return style_map.get(edge_type, "style=solid")
    
    def _to_d2(self, graph: ArchitectureGraph, config: DiagramConfig) -> str:
        """Convert to D2 diagram format."""
        lines = []
        
        if config.title:
            lines.append(f"title: {config.title}")
        
        lines.append(f"direction: {'right' if config.direction == 'LR' else 'down'}")
        lines.append("")
        
        for node in graph.nodes:
            shape = self._get_d2_shape(node.type)
            lines.append(f'{self._sanitize_id(node.id)}: "{node.label}" {{{shape}}}')
        
        lines.append("")
        
        for edge in graph.edges:
            arrow = self._get_d2_arrow(edge.type)
            label = f": {edge.label}" if edge.label else ""
            lines.append(f'{self._sanitize_id(edge.source)} {arrow} {self._sanitize_id(edge.target)}{label}')
        
        return "\n".join(lines)
    
    def _get_d2_shape(self, node_type: NodeType) -> str:
        """Get D2 shape for node type."""
        shape_map = {
            NodeType.MODULE: "shape: package",
            NodeType.CLASS: "shape: class",
            NodeType.FUNCTION: "shape: oval",
            NodeType.FILE: "shape: page",
            NodeType.PACKAGE: "shape: package",
            NodeType.SERVICE: "shape: hexagon",
            NodeType.DATABASE: "shape: cylinder",
            NodeType.API: "shape: diamond",
            NodeType.EXTERNAL: "shape: cloud",
        }
        return shape_map.get(node_type, "shape: rectangle")
    
    def _get_d2_arrow(self, edge_type: EdgeType) -> str:
        """Get D2 arrow style."""
        arrow_map = {
            EdgeType.IMPORTS: "->",
            EdgeType.EXTENDS: "->",
            EdgeType.IMPLEMENTS: "->",
            EdgeType.CALLS: "->",
            EdgeType.USES: "->",
            EdgeType.DEPENDS_ON: "->",
            EdgeType.CONTAINS: "--",
            EdgeType.ASSOCIATED: "<->",
        }
        return arrow_map.get(edge_type, "->")
    
    def _sanitize_id(self, id_str: str) -> str:
        """Sanitize ID for diagram formats."""
        return id_str.replace("/", "_").replace(".", "_").replace("-", "_").replace(" ", "_")
    
    def _group_nodes(self, nodes: list[NodeData], group_by: str) -> dict[str, list[NodeData]]:
        """Group nodes by a field."""
        groups: dict[str, list[NodeData]] = {}
        for node in nodes:
            if group_by == "module":
                group = node.path.rsplit("/", 1)[0] if node.path and "/" in node.path else "root"
            elif group_by == "package":
                group = node.metadata.get("package", "default")
            elif group_by == "directory":
                group = node.path.rsplit("/", 2)[-2] if node.path and "/" in node.path else "root"
            else:
                group = node.group or "default"
            
            if group not in groups:
                groups[group] = []
            groups[group].append(node)
        
        return groups


class ClassDiagramGenerator(BaseDiagramGenerator):
    """Generates UML class diagrams."""
    
    def generate(self, graph: ArchitectureGraph, config: DiagramConfig) -> DiagramResult:
        """Generate a class diagram."""
        filtered = self._filter_graph(graph, config)
        
        if config.format == DiagramFormat.MERMAID:
            content = self._to_mermaid_class(filtered, config)
        elif config.format == DiagramFormat.PLANTUML:
            content = self._to_plantuml_class(filtered, config)
        else:
            content = self._to_mermaid_class(filtered, config)
        
        return DiagramResult(
            diagram_type=DiagramType.CLASS,
            format=config.format,
            content=content,
            graph=filtered,
            node_count=len(filtered.nodes),
            edge_count=len(filtered.edges),
        )
    
    def _to_mermaid_class(self, graph: ArchitectureGraph, config: DiagramConfig) -> str:
        """Generate Mermaid classDiagram."""
        lines = ["classDiagram"]
        
        if config.title:
            lines.append(f"    %% {config.title}")
        
        for node in graph.nodes:
            if node.type == NodeType.CLASS:
                lines.append(f"    class {self._sanitize_id(node.id)} {{")
                
                # Add methods and attributes from metadata
                for attr in node.metadata.get("attributes", []):
                    lines.append(f"        +{attr}")
                for method in node.metadata.get("methods", []):
                    lines.append(f"        +{method}()")
                
                lines.append("    }")
        
        for edge in graph.edges:
            rel = self._get_class_relationship(edge.type)
            lines.append(f"    {self._sanitize_id(edge.source)} {rel} {self._sanitize_id(edge.target)}")
        
        return "\n".join(lines)
    
    def _to_plantuml_class(self, graph: ArchitectureGraph, config: DiagramConfig) -> str:
        """Generate PlantUML class diagram."""
        lines = ["@startuml"]
        
        if config.title:
            lines.append(f"title {config.title}")
        
        for node in graph.nodes:
            if node.type == NodeType.CLASS:
                lines.append(f"class {self._sanitize_id(node.id)} {{")
                for attr in node.metadata.get("attributes", []):
                    lines.append(f"    +{attr}")
                for method in node.metadata.get("methods", []):
                    lines.append(f"    +{method}()")
                lines.append("}")
        
        for edge in graph.edges:
            rel = self._get_plantuml_class_rel(edge.type)
            lines.append(f"{self._sanitize_id(edge.source)} {rel} {self._sanitize_id(edge.target)}")
        
        lines.append("@enduml")
        return "\n".join(lines)
    
    def _get_class_relationship(self, edge_type: EdgeType) -> str:
        """Get Mermaid class relationship."""
        rel_map = {
            EdgeType.EXTENDS: "<|--",
            EdgeType.IMPLEMENTS: "<|..",
            EdgeType.USES: "-->",
            EdgeType.ASSOCIATED: "--",
            EdgeType.DEPENDS_ON: "..>",
        }
        return rel_map.get(edge_type, "-->")
    
    def _get_plantuml_class_rel(self, edge_type: EdgeType) -> str:
        """Get PlantUML class relationship."""
        rel_map = {
            EdgeType.EXTENDS: "<|--",
            EdgeType.IMPLEMENTS: "<|..",
            EdgeType.USES: "-->",
            EdgeType.ASSOCIATED: "--",
            EdgeType.DEPENDS_ON: "..>",
        }
        return rel_map.get(edge_type, "-->")
    
    def _sanitize_id(self, id_str: str) -> str:
        """Sanitize ID."""
        return id_str.replace("/", "_").replace(".", "_").replace("-", "_").replace(" ", "_")


class SequenceDiagramGenerator(BaseDiagramGenerator):
    """Generates sequence diagrams from call flows."""
    
    def generate(self, graph: ArchitectureGraph, config: DiagramConfig) -> DiagramResult:
        """Generate a sequence diagram."""
        if config.format == DiagramFormat.MERMAID:
            content = self._to_mermaid_sequence(graph, config)
        elif config.format == DiagramFormat.PLANTUML:
            content = self._to_plantuml_sequence(graph, config)
        else:
            content = self._to_mermaid_sequence(graph, config)
        
        return DiagramResult(
            diagram_type=DiagramType.SEQUENCE,
            format=config.format,
            content=content,
            graph=graph,
            node_count=len(graph.nodes),
            edge_count=len(graph.edges),
        )
    
    def _to_mermaid_sequence(self, graph: ArchitectureGraph, config: DiagramConfig) -> str:
        """Generate Mermaid sequenceDiagram."""
        lines = ["sequenceDiagram"]
        
        if config.title:
            lines.append(f"    %% {config.title}")
        
        # Declare participants
        for node in graph.nodes:
            participant_type = "participant" if node.type != NodeType.DATABASE else "database"
            lines.append(f"    {participant_type} {self._sanitize_id(node.id)} as {node.label}")
        
        # Add interactions
        for edge in graph.edges:
            arrow = self._get_sequence_arrow(edge.type)
            message = edge.label or edge.type.value
            lines.append(f"    {self._sanitize_id(edge.source)}{arrow}{self._sanitize_id(edge.target)}: {message}")
        
        return "\n".join(lines)
    
    def _to_plantuml_sequence(self, graph: ArchitectureGraph, config: DiagramConfig) -> str:
        """Generate PlantUML sequence diagram."""
        lines = ["@startuml"]
        
        if config.title:
            lines.append(f"title {config.title}")
        
        for node in graph.nodes:
            keyword = "database" if node.type == NodeType.DATABASE else "participant"
            lines.append(f'{keyword} "{node.label}" as {self._sanitize_id(node.id)}')
        
        for edge in graph.edges:
            arrow = "->" if edge.type == EdgeType.CALLS else "-->"
            message = edge.label or ""
            lines.append(f"{self._sanitize_id(edge.source)} {arrow} {self._sanitize_id(edge.target)}: {message}")
        
        lines.append("@enduml")
        return "\n".join(lines)
    
    def _get_sequence_arrow(self, edge_type: EdgeType) -> str:
        """Get Mermaid sequence arrow."""
        arrow_map = {
            EdgeType.CALLS: "->>",
            EdgeType.USES: "->>",
            EdgeType.ASSOCIATED: "-->",
        }
        return arrow_map.get(edge_type, "->>")
    
    def _sanitize_id(self, id_str: str) -> str:
        """Sanitize ID."""
        return id_str.replace("/", "_").replace(".", "_").replace("-", "_").replace(" ", "_")


class FlowchartGenerator(BaseDiagramGenerator):
    """Generates flowcharts from control flow analysis."""
    
    def generate(self, graph: ArchitectureGraph, config: DiagramConfig) -> DiagramResult:
        """Generate a flowchart."""
        if config.format == DiagramFormat.MERMAID:
            content = self._to_mermaid_flowchart(graph, config)
        else:
            content = self._to_mermaid_flowchart(graph, config)
        
        return DiagramResult(
            diagram_type=DiagramType.FLOWCHART,
            format=config.format,
            content=content,
            graph=graph,
            node_count=len(graph.nodes),
            edge_count=len(graph.edges),
        )
    
    def _to_mermaid_flowchart(self, graph: ArchitectureGraph, config: DiagramConfig) -> str:
        """Generate Mermaid flowchart."""
        lines = [f"flowchart {config.direction}"]
        
        if config.title:
            lines.append(f"    %% {config.title}")
        
        for node in graph.nodes:
            shape = self._get_flowchart_shape(node)
            lines.append(f"    {self._sanitize_id(node.id)}{shape}")
        
        for edge in graph.edges:
            label = f"|{edge.label}|" if edge.label else ""
            lines.append(f"    {self._sanitize_id(edge.source)} -->{label} {self._sanitize_id(edge.target)}")
        
        return "\n".join(lines)
    
    def _get_flowchart_shape(self, node: NodeData) -> str:
        """Get flowchart shape based on node metadata."""
        shape_type = node.metadata.get("shape", "process")
        label = node.label
        
        shape_map = {
            "start": f"(({label}))",
            "end": f"(({label}))",
            "process": f"[{label}]",
            "decision": f"{{{label}}}",
            "io": f"[/{label}/]",
            "subprocess": f"[[{label}]]",
            "database": f"[({label})]",
        }
        
        return shape_map.get(shape_type, f"[{label}]")
    
    def _sanitize_id(self, id_str: str) -> str:
        """Sanitize ID."""
        return id_str.replace("/", "_").replace(".", "_").replace("-", "_").replace(" ", "_")
