"""
Visualization Models

Data models for architecture diagrams and visualizations.
"""

from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field


class DiagramType(str, Enum):
    """Types of diagrams that can be generated."""
    DEPENDENCY = "dependency"
    CLASS = "class"
    SEQUENCE = "sequence"
    FLOWCHART = "flowchart"
    COMPONENT = "component"
    DEPLOYMENT = "deployment"
    ENTITY_RELATIONSHIP = "er"
    STATE = "state"
    CALL_GRAPH = "call_graph"
    MODULE_STRUCTURE = "module_structure"


class DiagramFormat(str, Enum):
    """Output formats for diagrams."""
    MERMAID = "mermaid"
    PLANTUML = "plantuml"
    DOT = "dot"
    SVG = "svg"
    PNG = "png"
    JSON = "json"
    D2 = "d2"


class NodeType(str, Enum):
    """Types of nodes in architecture graphs."""
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    FILE = "file"
    PACKAGE = "package"
    SERVICE = "service"
    DATABASE = "database"
    API = "api"
    EXTERNAL = "external"


class EdgeType(str, Enum):
    """Types of relationships between nodes."""
    IMPORTS = "imports"
    EXTENDS = "extends"
    IMPLEMENTS = "implements"
    CALLS = "calls"
    USES = "uses"
    DEPENDS_ON = "depends_on"
    CONTAINS = "contains"
    ASSOCIATED = "associated"


class NodeData(BaseModel):
    """Data for a node in the architecture graph."""
    id: str
    label: str
    type: NodeType
    path: Optional[str] = None
    language: Optional[str] = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    
    # Visual properties
    color: Optional[str] = None
    size: Optional[int] = None
    group: Optional[str] = None


class EdgeData(BaseModel):
    """Data for an edge in the architecture graph."""
    source: str
    target: str
    type: EdgeType
    weight: float = 1.0
    label: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    
    # Visual properties
    color: Optional[str] = None
    style: Optional[str] = None  # solid, dashed, dotted


class ArchitectureGraph(BaseModel):
    """Complete architecture graph with nodes and edges."""
    nodes: list[NodeData] = Field(default_factory=list)
    edges: list[EdgeData] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    
    def add_node(self, node: NodeData) -> None:
        """Add a node to the graph."""
        if not any(n.id == node.id for n in self.nodes):
            self.nodes.append(node)
    
    def add_edge(self, edge: EdgeData) -> None:
        """Add an edge to the graph."""
        self.edges.append(edge)
    
    def get_node(self, node_id: str) -> Optional[NodeData]:
        """Get a node by ID."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None
    
    def get_connected_nodes(self, node_id: str) -> list[NodeData]:
        """Get all nodes connected to a given node."""
        connected_ids = set()
        for edge in self.edges:
            if edge.source == node_id:
                connected_ids.add(edge.target)
            elif edge.target == node_id:
                connected_ids.add(edge.source)
        return [n for n in self.nodes if n.id in connected_ids]


class DiagramConfig(BaseModel):
    """Configuration for diagram generation."""
    type: DiagramType
    format: DiagramFormat = DiagramFormat.MERMAID
    title: Optional[str] = None
    description: Optional[str] = None
    
    # Filtering
    include_patterns: list[str] = Field(default_factory=list)
    exclude_patterns: list[str] = Field(default_factory=list)
    max_depth: Optional[int] = None
    min_connections: int = 0
    
    # Layout
    direction: str = "TB"  # TB, BT, LR, RL
    node_spacing: int = 50
    rank_spacing: int = 50
    
    # Styling
    theme: str = "default"
    show_labels: bool = True
    show_metrics: bool = False
    highlight_hotspots: bool = True
    color_by: Optional[str] = None  # complexity, coverage, type
    
    # Grouping
    group_by: Optional[str] = None  # module, package, directory


class DiagramResult(BaseModel):
    """Result of diagram generation."""
    diagram_type: DiagramType
    format: DiagramFormat
    content: str
    graph: Optional[ArchitectureGraph] = None
    
    # Metadata
    node_count: int = 0
    edge_count: int = 0
    generation_time_ms: float = 0
    
    # Optional rendered output
    svg_content: Optional[str] = None
    png_base64: Optional[str] = None


class HotspotInfo(BaseModel):
    """Information about code hotspots."""
    node_id: str
    path: str
    score: float
    reasons: list[str] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)


class VisualizationRequest(BaseModel):
    """Request for visualization generation."""
    project_id: str
    config: DiagramConfig
    source_paths: list[str] = Field(default_factory=list)
    branch: str = "main"
    commit_sha: Optional[str] = None


class VisualizationResponse(BaseModel):
    """Response containing visualization results."""
    request_id: str
    status: str
    diagrams: list[DiagramResult] = Field(default_factory=list)
    hotspots: list[HotspotInfo] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
