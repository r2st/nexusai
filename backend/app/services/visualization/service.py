"""
Visualization Service

Main service for generating architecture diagrams and visualizations.
"""

import logging
import time
from functools import lru_cache

from .models import (
    DiagramType,
    DiagramConfig,
    DiagramResult,
    DiagramFormat,
    ArchitectureGraph,
    NodeData,
    EdgeData,
    NodeType,
    EdgeType,
    HotspotInfo,
    VisualizationRequest,
    VisualizationResponse,
)
from .generators import (
    DependencyDiagramGenerator,
    ClassDiagramGenerator,
    SequenceDiagramGenerator,
    FlowchartGenerator,
)

logger = logging.getLogger(__name__)


class VisualizationService:
    """
    Service for generating architecture diagrams and visualizations.
    
    Supports multiple diagram types and output formats:
    - Dependency diagrams (imports, modules)
    - Class diagrams (UML)
    - Sequence diagrams (call flows)
    - Flowcharts (control flow)
    - Component diagrams
    - Deployment diagrams
    """
    
    def __init__(self):
        self.generators = {
            DiagramType.DEPENDENCY: DependencyDiagramGenerator(),
            DiagramType.CLASS: ClassDiagramGenerator(),
            DiagramType.SEQUENCE: SequenceDiagramGenerator(),
            DiagramType.FLOWCHART: FlowchartGenerator(),
            DiagramType.COMPONENT: DependencyDiagramGenerator(),
            DiagramType.MODULE_STRUCTURE: DependencyDiagramGenerator(),
            DiagramType.CALL_GRAPH: SequenceDiagramGenerator(),
        }
    
    async def generate_diagram(
        self,
        graph: ArchitectureGraph,
        config: DiagramConfig,
    ) -> DiagramResult:
        """
        Generate a diagram from an architecture graph.
        
        Args:
            graph: The architecture graph to visualize
            config: Configuration for diagram generation
            
        Returns:
            DiagramResult with the generated diagram
        """
        start_time = time.time()
        
        generator = self.generators.get(config.type)
        if not generator:
            logger.warning(f"No generator for diagram type: {config.type}, using dependency")
            generator = self.generators[DiagramType.DEPENDENCY]
        
        result = generator.generate(graph, config)
        result.generation_time_ms = (time.time() - start_time) * 1000
        
        logger.info(
            f"Generated {config.type.value} diagram with {result.node_count} nodes, "
            f"{result.edge_count} edges in {result.generation_time_ms:.2f}ms"
        )
        
        return result
    
    async def generate_from_code_analysis(
        self,
        analysis_result: dict,
        config: DiagramConfig,
    ) -> DiagramResult:
        """
        Generate a diagram from code analysis results.
        
        Args:
            analysis_result: Results from code analysis service
            config: Configuration for diagram generation
            
        Returns:
            DiagramResult with the generated diagram
        """
        graph = self._build_graph_from_analysis(analysis_result, config)
        return await self.generate_diagram(graph, config)
    
    def _build_graph_from_analysis(
        self,
        analysis: dict,
        config: DiagramConfig,
    ) -> ArchitectureGraph:
        """Build an architecture graph from analysis results."""
        graph = ArchitectureGraph()
        
        # Process modules/files
        for module in analysis.get("modules", []):
            node = NodeData(
                id=module["path"],
                label=module.get("name", module["path"].split("/")[-1]),
                type=NodeType.MODULE,
                path=module["path"],
                language=module.get("language"),
                metrics={
                    "complexity": module.get("complexity", 0),
                    "lines": module.get("lines", 0),
                    "coverage": module.get("coverage", 0),
                },
            )
            
            # Color by complexity if configured
            if config.color_by == "complexity":
                complexity = module.get("complexity", 0)
                node.color = self._complexity_to_color(complexity)
            elif config.color_by == "coverage":
                coverage = module.get("coverage", 100)
                node.color = self._coverage_to_color(coverage)
            
            graph.add_node(node)
        
        # Process classes
        for cls in analysis.get("classes", []):
            node = NodeData(
                id=cls["name"],
                label=cls["name"],
                type=NodeType.CLASS,
                path=cls.get("file"),
                metadata={
                    "attributes": cls.get("attributes", []),
                    "methods": cls.get("methods", []),
                },
            )
            graph.add_node(node)
        
        # Process functions
        for func in analysis.get("functions", []):
            node = NodeData(
                id=f"{func.get('module', 'unknown')}.{func['name']}",
                label=func["name"],
                type=NodeType.FUNCTION,
                path=func.get("file"),
                metrics={
                    "complexity": func.get("complexity", 0),
                    "lines": func.get("lines", 0),
                },
            )
            graph.add_node(node)
        
        # Process dependencies/imports
        for dep in analysis.get("dependencies", []):
            edge = EdgeData(
                source=dep["source"],
                target=dep["target"],
                type=EdgeType.IMPORTS,
                weight=dep.get("weight", 1.0),
            )
            graph.add_edge(edge)
        
        # Process inheritance
        for inheritance in analysis.get("inheritance", []):
            edge = EdgeData(
                source=inheritance["child"],
                target=inheritance["parent"],
                type=EdgeType.EXTENDS,
            )
            graph.add_edge(edge)
        
        # Process calls
        for call in analysis.get("calls", []):
            edge = EdgeData(
                source=call["caller"],
                target=call["callee"],
                type=EdgeType.CALLS,
                label=call.get("method"),
            )
            graph.add_edge(edge)
        
        return graph
    
    def _complexity_to_color(self, complexity: float) -> str:
        """Map complexity score to color."""
        if complexity <= 5:
            return "#4CAF50"  # Green
        elif complexity <= 10:
            return "#8BC34A"  # Light Green
        elif complexity <= 15:
            return "#FFC107"  # Amber
        elif complexity <= 20:
            return "#FF9800"  # Orange
        else:
            return "#F44336"  # Red
    
    def _coverage_to_color(self, coverage: float) -> str:
        """Map coverage percentage to color."""
        if coverage >= 80:
            return "#4CAF50"  # Green
        elif coverage >= 60:
            return "#8BC34A"  # Light Green
        elif coverage >= 40:
            return "#FFC107"  # Amber
        elif coverage >= 20:
            return "#FF9800"  # Orange
        else:
            return "#F44336"  # Red
    
    async def identify_hotspots(
        self,
        graph: ArchitectureGraph,
        threshold: float = 0.7,
    ) -> list[HotspotInfo]:
        """
        Identify code hotspots from the architecture graph.
        
        Hotspots are nodes with high complexity, many connections,
        or other indicators of risk.
        """
        hotspots = []
        
        # Calculate connection counts
        connection_counts = {}
        for edge in graph.edges:
            connection_counts[edge.source] = connection_counts.get(edge.source, 0) + 1
            connection_counts[edge.target] = connection_counts.get(edge.target, 0) + 1
        
        max_connections = max(connection_counts.values()) if connection_counts else 1
        
        for node in graph.nodes:
            score = 0.0
            reasons = []
            
            # Factor 1: Complexity
            complexity = node.metrics.get("complexity", 0)
            if complexity > 15:
                score += 0.3
                reasons.append(f"High complexity: {complexity}")
            elif complexity > 10:
                score += 0.15
                reasons.append(f"Moderate complexity: {complexity}")
            
            # Factor 2: Connection count (coupling)
            connections = connection_counts.get(node.id, 0)
            coupling_score = connections / max_connections
            if coupling_score > 0.5:
                score += 0.3
                reasons.append(f"High coupling: {connections} connections")
            elif coupling_score > 0.25:
                score += 0.15
                reasons.append(f"Moderate coupling: {connections} connections")
            
            # Factor 3: Low coverage
            coverage = node.metrics.get("coverage", 100)
            if coverage < 50:
                score += 0.2
                reasons.append(f"Low coverage: {coverage}%")
            elif coverage < 70:
                score += 0.1
                reasons.append(f"Moderate coverage: {coverage}%")
            
            # Factor 4: Large file
            lines = node.metrics.get("lines", 0)
            if lines > 500:
                score += 0.2
                reasons.append(f"Large file: {lines} lines")
            elif lines > 300:
                score += 0.1
                reasons.append(f"Moderately large: {lines} lines")
            
            if score >= threshold:
                hotspots.append(HotspotInfo(
                    node_id=node.id,
                    path=node.path or node.id,
                    score=min(score, 1.0),
                    reasons=reasons,
                    metrics={
                        "complexity": complexity,
                        "connections": connections,
                        "coverage": coverage,
                        "lines": lines,
                    },
                ))
        
        # Sort by score descending
        hotspots.sort(key=lambda h: h.score, reverse=True)
        
        return hotspots
    
    async def process_visualization_request(
        self,
        request: VisualizationRequest,
    ) -> VisualizationResponse:
        """
        Process a complete visualization request.
        
        This is the main entry point for the API.
        """
        import uuid
        
        request_id = str(uuid.uuid4())
        diagrams = []
        errors = []
        
        try:
            # In a real implementation, we would:
            # 1. Fetch the repository content
            # 2. Run code analysis
            # 3. Build the architecture graph
            # 4. Generate the diagram
            
            # For now, create a placeholder graph
            graph = ArchitectureGraph(
                metadata={
                    "project_id": request.project_id,
                    "branch": request.branch,
                }
            )
            
            # Generate the diagram
            diagram = await self.generate_diagram(graph, request.config)
            diagrams.append(diagram)
            
            # Identify hotspots
            hotspots = await self.identify_hotspots(graph)
            
            return VisualizationResponse(
                request_id=request_id,
                status="success",
                diagrams=diagrams,
                hotspots=hotspots,
            )
            
        except Exception as e:
            logger.error(f"Visualization request failed: {e}")
            return VisualizationResponse(
                request_id=request_id,
                status="error",
                errors=[str(e)],
            )


@lru_cache()
def get_visualization_service() -> VisualizationService:
    """Get the visualization service singleton."""
    return VisualizationService()
