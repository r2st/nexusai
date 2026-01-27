"""
Visualization Service

Generates architecture diagrams and visual representations from code analysis.
"""

from .service import (
    VisualizationService,
    get_visualization_service,
)
from .models import (
    DiagramType,
    DiagramConfig,
    DiagramResult,
    NodeData,
    EdgeData,
    ArchitectureGraph,
)
from .generators import (
    DependencyDiagramGenerator,
    ClassDiagramGenerator,
    SequenceDiagramGenerator,
    FlowchartGenerator,
)

__all__ = [
    # Service
    "VisualizationService",
    "get_visualization_service",
    # Models
    "DiagramType",
    "DiagramConfig",
    "DiagramResult",
    "NodeData",
    "EdgeData",
    "ArchitectureGraph",
    # Generators
    "DependencyDiagramGenerator",
    "ClassDiagramGenerator",
    "SequenceDiagramGenerator",
    "FlowchartGenerator",
]
