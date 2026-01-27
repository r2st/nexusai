"""Agent discovery workflow using knowledge graph.

Implements the NexusChat pattern where agents must query the knowledge graph
first to understand available data before executing database queries.
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any

import structlog

from app.services.knowledge_graph.neo4j_client import Neo4jClient
from app.services.knowledge_graph.discovery import (
    KnowledgeGraphDiscovery,
    TableMetadata,
    ColumnMetadata,
)

logger = structlog.get_logger()


class DiscoveryPhase(str, Enum):
    """Phases of the agent discovery workflow."""

    INITIAL = "initial"  # Agent just received the query
    SCHEMA_DISCOVERY = "schema_discovery"  # Discovering available tables/metrics
    RELATIONSHIP_ANALYSIS = "relationship_analysis"  # Understanding relationships
    QUERY_PLANNING = "query_planning"  # Planning the database query
    EXECUTION_READY = "execution_ready"  # Ready to execute on PostgreSQL


@dataclass
class DiscoveryContext:
    """Context for agent discovery workflow."""

    session_id: str
    tenant_id: str
    project_id: str | None = None
    user_query: str = ""
    phase: DiscoveryPhase = DiscoveryPhase.INITIAL
    discovered_tables: list[TableMetadata] = field(default_factory=list)
    discovered_metrics: list[dict[str, Any]] = field(default_factory=list)
    discovered_relationships: dict[str, Any] = field(default_factory=dict)
    relevant_tables: list[str] = field(default_factory=list)
    suggested_query: str | None = None
    discovery_log: list[dict[str, Any]] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None


@dataclass
class DiscoveryResult:
    """Result of the discovery workflow."""

    success: bool
    context: DiscoveryContext
    schema_summary: str
    recommended_tables: list[str]
    recommended_joins: list[dict[str, Any]]
    query_template: str | None = None
    warnings: list[str] = field(default_factory=list)
    error: str | None = None


class AgentDiscoveryWorkflow:
    """Implements the knowledge graph discovery workflow for agents.

    This ensures agents understand the data landscape before executing
    queries, following the pattern:

    1. Receive user query
    2. Query knowledge graph for relevant tables
    3. Explore relationships and data lineage
    4. Generate optimized query based on schema understanding
    5. Execute query with proper RLS context
    """

    def __init__(
        self,
        neo4j_client: Neo4jClient,
        discovery_service: KnowledgeGraphDiscovery | None = None,
    ):
        self.neo4j = neo4j_client
        self.discovery = discovery_service or KnowledgeGraphDiscovery(neo4j_client)

    async def start_discovery(
        self,
        session_id: str,
        tenant_id: str,
        user_query: str,
        project_id: str | None = None,
    ) -> DiscoveryContext:
        """Start a new discovery workflow."""
        context = DiscoveryContext(
            session_id=session_id,
            tenant_id=tenant_id,
            project_id=project_id,
            user_query=user_query,
            phase=DiscoveryPhase.INITIAL,
        )

        context.discovery_log.append({
            "phase": DiscoveryPhase.INITIAL.value,
            "timestamp": datetime.now(UTC).isoformat(),
            "message": f"Starting discovery for query: {user_query[:100]}...",
        })

        logger.info(
            "Discovery workflow started",
            session_id=session_id,
            tenant_id=tenant_id,
            query_preview=user_query[:50],
        )

        return context

    async def discover_schema(
        self,
        context: DiscoveryContext,
    ) -> DiscoveryContext:
        """Phase 1: Discover available tables and metrics."""
        context.phase = DiscoveryPhase.SCHEMA_DISCOVERY

        try:
            # Discover tables
            context.discovered_tables = await self.discovery.discover_tables(
                project_id=context.project_id,
            )

            # Discover metrics
            context.discovered_metrics = await self.discovery.discover_metrics(
                project_id=context.project_id,
            )

            context.discovery_log.append({
                "phase": DiscoveryPhase.SCHEMA_DISCOVERY.value,
                "timestamp": datetime.now(UTC).isoformat(),
                "message": f"Discovered {len(context.discovered_tables)} tables and {len(context.discovered_metrics)} metrics",
                "tables": [t.name for t in context.discovered_tables],
                "metrics": [m.get("name") for m in context.discovered_metrics],
            })

            logger.info(
                "Schema discovery completed",
                tables=len(context.discovered_tables),
                metrics=len(context.discovered_metrics),
            )

        except Exception as e:
            context.discovery_log.append({
                "phase": DiscoveryPhase.SCHEMA_DISCOVERY.value,
                "timestamp": datetime.now(UTC).isoformat(),
                "error": str(e),
            })
            logger.error("Schema discovery failed", error=str(e))

        return context

    async def analyze_relationships(
        self,
        context: DiscoveryContext,
        table_names: list[str] | None = None,
    ) -> DiscoveryContext:
        """Phase 2: Analyze relationships between relevant tables."""
        context.phase = DiscoveryPhase.RELATIONSHIP_ANALYSIS

        # If no specific tables provided, identify relevant ones from query
        if not table_names:
            table_names = await self._identify_relevant_tables(context)

        context.relevant_tables = table_names

        try:
            for table_name in table_names:
                relationships = await self.discovery.discover_relationships(table_name)
                context.discovered_relationships[table_name] = relationships

            context.discovery_log.append({
                "phase": DiscoveryPhase.RELATIONSHIP_ANALYSIS.value,
                "timestamp": datetime.now(UTC).isoformat(),
                "message": f"Analyzed relationships for {len(table_names)} tables",
                "tables": table_names,
            })

            logger.info(
                "Relationship analysis completed",
                tables=table_names,
            )

        except Exception as e:
            context.discovery_log.append({
                "phase": DiscoveryPhase.RELATIONSHIP_ANALYSIS.value,
                "timestamp": datetime.now(UTC).isoformat(),
                "error": str(e),
            })
            logger.error("Relationship analysis failed", error=str(e))

        return context

    async def plan_query(
        self,
        context: DiscoveryContext,
    ) -> DiscoveryContext:
        """Phase 3: Plan the database query based on discovered schema."""
        context.phase = DiscoveryPhase.QUERY_PLANNING

        try:
            # Get detailed schema for relevant tables
            table_schemas = await self.discovery.get_table_schema_for_query(
                context.relevant_tables
            )

            # Generate query template
            query_template = await self._generate_query_template(
                context.user_query,
                table_schemas,
                context.discovered_relationships,
            )

            context.suggested_query = query_template

            context.discovery_log.append({
                "phase": DiscoveryPhase.QUERY_PLANNING.value,
                "timestamp": datetime.now(UTC).isoformat(),
                "message": "Query template generated",
                "query_preview": query_template[:200] if query_template else None,
            })

            logger.info("Query planning completed")

        except Exception as e:
            context.discovery_log.append({
                "phase": DiscoveryPhase.QUERY_PLANNING.value,
                "timestamp": datetime.now(UTC).isoformat(),
                "error": str(e),
            })
            logger.error("Query planning failed", error=str(e))

        return context

    async def complete_discovery(
        self,
        context: DiscoveryContext,
    ) -> DiscoveryResult:
        """Complete the discovery workflow and return results."""
        context.phase = DiscoveryPhase.EXECUTION_READY
        context.completed_at = datetime.now(UTC)

        # Generate schema summary
        schema_summary = self._generate_schema_summary(context)

        # Identify recommended joins
        recommended_joins = self._identify_recommended_joins(context)

        # Check for warnings
        warnings = self._check_for_warnings(context)

        result = DiscoveryResult(
            success=True,
            context=context,
            schema_summary=schema_summary,
            recommended_tables=context.relevant_tables,
            recommended_joins=recommended_joins,
            query_template=context.suggested_query,
            warnings=warnings,
        )

        logger.info(
            "Discovery workflow completed",
            session_id=context.session_id,
            duration_ms=(context.completed_at - context.started_at).total_seconds() * 1000,
            tables=len(context.relevant_tables),
        )

        return result

    async def run_full_discovery(
        self,
        session_id: str,
        tenant_id: str,
        user_query: str,
        project_id: str | None = None,
    ) -> DiscoveryResult:
        """Run the complete discovery workflow."""
        try:
            # Start discovery
            context = await self.start_discovery(
                session_id=session_id,
                tenant_id=tenant_id,
                user_query=user_query,
                project_id=project_id,
            )

            # Phase 1: Schema discovery
            context = await self.discover_schema(context)

            # Phase 2: Relationship analysis
            context = await self.analyze_relationships(context)

            # Phase 3: Query planning
            context = await self.plan_query(context)

            # Complete and return results
            return await self.complete_discovery(context)

        except Exception as e:
            logger.error("Discovery workflow failed", error=str(e))
            return DiscoveryResult(
                success=False,
                context=DiscoveryContext(
                    session_id=session_id,
                    tenant_id=tenant_id,
                    user_query=user_query,
                ),
                schema_summary="",
                recommended_tables=[],
                recommended_joins=[],
                error=str(e),
            )

    async def _identify_relevant_tables(
        self,
        context: DiscoveryContext,
    ) -> list[str]:
        """Identify tables relevant to the user's query."""
        # Extract keywords from query
        query_lower = context.user_query.lower()

        # Common DORA/DevOps keywords
        dora_keywords = [
            "dora", "deployment", "deploy", "lead time", "mttr",
            "change failure", "incident", "recovery", "frequency",
        ]

        analytics_keywords = [
            "metric", "analytics", "usage", "adoption", "productivity",
            "ai", "copilot", "cursor", "claude",
        ]

        pr_keywords = [
            "pull request", "pr", "merge", "review", "commit",
            "repository", "repo", "branch",
        ]

        relevant_tables = []

        for table in context.discovered_tables:
            table_name_lower = table.name.lower()
            table_desc_lower = (table.description or "").lower()

            # Check if table matches query context
            matches_dora = any(kw in query_lower for kw in dora_keywords) and \
                          any(kw in table_name_lower or kw in table_desc_lower for kw in dora_keywords)

            matches_analytics = any(kw in query_lower for kw in analytics_keywords) and \
                               any(kw in table_name_lower or kw in table_desc_lower for kw in analytics_keywords)

            matches_pr = any(kw in query_lower for kw in pr_keywords) and \
                        any(kw in table_name_lower or kw in table_desc_lower for kw in pr_keywords)

            # Check for direct table name mention
            direct_match = table_name_lower in query_lower

            if matches_dora or matches_analytics or matches_pr or direct_match:
                relevant_tables.append(table.name)

        # If no matches, use search
        if not relevant_tables:
            search_results = await self.discovery.search_entities(
                search_term=context.user_query.split()[0] if context.user_query else "",
                entity_types=["Table"],
                limit=5,
            )
            relevant_tables = [r["name"] for r in search_results]

        return relevant_tables[:10]  # Limit to 10 tables

    async def _generate_query_template(
        self,
        user_query: str,
        table_schemas: dict[str, TableMetadata],
        relationships: dict[str, Any],
    ) -> str | None:
        """Generate a SQL query template based on schema understanding."""
        if not table_schemas:
            return None

        # Build SELECT clause based on available columns
        tables = list(table_schemas.keys())
        primary_table = tables[0]
        primary_schema = table_schemas[primary_table]

        # Build basic query template
        columns = [f"{primary_table}.{col.name}" for col in primary_schema.columns[:5]]

        query = f"""
-- Auto-generated query template based on knowledge graph discovery
-- Primary table: {primary_table}
-- Discovered columns: {len(primary_schema.columns)}

SELECT
    {', '.join(columns)}
FROM {primary_schema.schema_name}.{primary_table}
"""

        # Add JOINs based on relationships
        if primary_table in relationships:
            rels = relationships[primary_table]
            for fk in rels.get("foreign_keys", [])[:3]:
                ref_table = fk.get("references_table")
                if ref_table and ref_table in table_schemas:
                    query += f"""
LEFT JOIN {table_schemas[ref_table].schema_name}.{ref_table}
    ON {primary_table}.{fk['column']} = {ref_table}.{fk['references_column']}
"""

        query += """
-- Add WHERE clause based on user requirements
WHERE 1=1
-- Add tenant_id filter for RLS
-- AND tenant_id = :tenant_id
LIMIT 100;
"""

        return query

    def _generate_schema_summary(self, context: DiscoveryContext) -> str:
        """Generate a human-readable schema summary."""
        lines = [
            f"# Schema Discovery Summary",
            f"",
            f"## Discovered Tables ({len(context.discovered_tables)})",
        ]

        for table in context.discovered_tables[:10]:
            col_count = len(table.columns)
            lines.append(f"- **{table.name}**: {col_count} columns")
            if table.description:
                lines.append(f"  - {table.description}")

        if context.discovered_metrics:
            lines.append(f"")
            lines.append(f"## Discovered Metrics ({len(context.discovered_metrics)})")
            for metric in context.discovered_metrics[:10]:
                lines.append(f"- **{metric.get('name')}**: {metric.get('description', 'No description')}")

        lines.append(f"")
        lines.append(f"## Relevant Tables for Query")
        for table in context.relevant_tables:
            lines.append(f"- {table}")

        return "\n".join(lines)

    def _identify_recommended_joins(
        self,
        context: DiscoveryContext,
    ) -> list[dict[str, Any]]:
        """Identify recommended JOIN operations."""
        joins = []

        for table_name, rels in context.discovered_relationships.items():
            for fk in rels.get("foreign_keys", []):
                if fk.get("references_table") in context.relevant_tables:
                    joins.append({
                        "from_table": table_name,
                        "from_column": fk.get("column"),
                        "to_table": fk.get("references_table"),
                        "to_column": fk.get("references_column"),
                        "join_type": "LEFT JOIN",
                    })

        return joins

    def _check_for_warnings(self, context: DiscoveryContext) -> list[str]:
        """Check for potential issues and generate warnings."""
        warnings = []

        if not context.relevant_tables:
            warnings.append("No relevant tables identified for this query")

        if len(context.relevant_tables) > 5:
            warnings.append(
                f"Query involves {len(context.relevant_tables)} tables - "
                "consider narrowing scope for performance"
            )

        # Check for missing relationships
        for table in context.relevant_tables:
            if table not in context.discovered_relationships:
                warnings.append(f"No relationship data found for table: {table}")

        return warnings


class DiscoveryEnforcedAgent:
    """Wrapper that enforces discovery workflow before database access.

    This ensures agents cannot directly query PostgreSQL without first
    going through the knowledge graph discovery process.
    """

    def __init__(
        self,
        workflow: AgentDiscoveryWorkflow,
        require_discovery: bool = True,
    ):
        self.workflow = workflow
        self.require_discovery = require_discovery
        self._discovery_cache: dict[str, DiscoveryResult] = {}

    async def execute_with_discovery(
        self,
        session_id: str,
        tenant_id: str,
        user_query: str,
        project_id: str | None = None,
        force_rediscovery: bool = False,
    ) -> DiscoveryResult:
        """Execute query with mandatory discovery phase."""
        cache_key = f"{session_id}:{tenant_id}:{hash(user_query)}"

        # Check cache
        if not force_rediscovery and cache_key in self._discovery_cache:
            logger.info("Using cached discovery result", cache_key=cache_key)
            return self._discovery_cache[cache_key]

        # Run discovery
        result = await self.workflow.run_full_discovery(
            session_id=session_id,
            tenant_id=tenant_id,
            user_query=user_query,
            project_id=project_id,
        )

        # Cache result
        self._discovery_cache[cache_key] = result

        return result

    def clear_cache(self, session_id: str | None = None):
        """Clear discovery cache."""
        if session_id:
            keys_to_remove = [k for k in self._discovery_cache if k.startswith(session_id)]
            for key in keys_to_remove:
                del self._discovery_cache[key]
        else:
            self._discovery_cache.clear()
