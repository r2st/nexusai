"""Prompt Registry for managing versioned prompts."""

import hashlib
import re
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.prompts.models import (
    ExperimentStatus,
    Prompt,
    PromptAssignment,
    PromptExperiment,
    PromptPerformance,
    PromptStats,
    PromptStatus,
    PromptVersion,
)

logger = structlog.get_logger()


class PromptRegistry:
    """Registry for managing versioned prompts with A/B testing.

    Features:
    - Versioned prompt storage
    - Template variable extraction
    - A/B experiment management
    - Performance tracking
    - Rollback support
    """

    # Variable pattern: {{variable_name}}
    VARIABLE_PATTERN = re.compile(r"\{\{(\w+)\}\}")

    async def create_prompt(
        self,
        session: AsyncSession,
        tenant_id: str,
        name: str,
        template: str,
        system_prompt: str | None = None,
        description: str | None = None,
        category: str | None = None,
        default_model: str | None = None,
        created_by: str | None = None,
    ) -> Prompt:
        """Create a new prompt.

        Args:
            session: Database session
            tenant_id: Tenant ID
            name: Unique name
            template: Prompt template
            system_prompt: Optional system prompt
            description: Optional description
            category: Optional category
            default_model: Optional default model
            created_by: Creator user ID

        Returns:
            Created prompt
        """
        # Generate slug from name
        slug = self._generate_slug(name)

        # Extract variables
        variables = self._extract_variables(template)
        if system_prompt:
            variables.extend(self._extract_variables(system_prompt))
        variables = list(set(variables))

        prompt = Prompt(
            tenant_id=tenant_id,
            name=name,
            slug=slug,
            template=template,
            system_prompt=system_prompt,
            description=description,
            category=category,
            variables=variables,
            default_model=default_model,
            created_by=created_by,
        )

        # Save prompt
        await session.execute(
            text("""
                INSERT INTO prompts (
                    id, tenant_id, name, slug, template, system_prompt,
                    description, category, variables, default_model,
                    default_temperature, default_max_tokens, status,
                    current_version, tags, metadata, created_at, updated_at, created_by
                ) VALUES (
                    :id, :tenant_id, :name, :slug, :template, :system_prompt,
                    :description, :category, :variables, :default_model,
                    :default_temperature, :default_max_tokens, :status,
                    :current_version, :tags, :metadata, :created_at, :updated_at, :created_by
                )
            """),
            {
                "id": prompt.id,
                "tenant_id": prompt.tenant_id,
                "name": prompt.name,
                "slug": prompt.slug,
                "template": prompt.template,
                "system_prompt": prompt.system_prompt,
                "description": prompt.description,
                "category": prompt.category,
                "variables": prompt.variables,
                "default_model": prompt.default_model,
                "default_temperature": prompt.default_temperature,
                "default_max_tokens": prompt.default_max_tokens,
                "status": prompt.status.value,
                "current_version": prompt.current_version,
                "tags": prompt.tags,
                "metadata": prompt.metadata,
                "created_at": prompt.created_at,
                "updated_at": prompt.updated_at,
                "created_by": prompt.created_by,
            },
        )

        # Create initial version
        await self._create_version(session, prompt, "Initial version")
        await session.flush()

        logger.info("Created prompt", prompt_id=prompt.id, name=prompt.name)
        return prompt

    async def get_prompt(
        self,
        session: AsyncSession,
        prompt_id: str | None = None,
        slug: str | None = None,
        tenant_id: str | None = None,
    ) -> Prompt | None:
        """Get a prompt by ID or slug."""
        if prompt_id:
            sql = "SELECT * FROM prompts WHERE id = :id"
            params = {"id": prompt_id}
        elif slug and tenant_id:
            sql = "SELECT * FROM prompts WHERE slug = :slug AND tenant_id = :tenant_id"
            params = {"slug": slug, "tenant_id": tenant_id}
        else:
            return None

        result = await session.execute(text(sql), params)
        row = result.fetchone()

        if not row:
            return None

        return Prompt(
            id=row.id,
            tenant_id=row.tenant_id,
            name=row.name,
            slug=row.slug,
            template=row.template,
            system_prompt=row.system_prompt,
            description=row.description,
            category=row.category,
            variables=row.variables or [],
            default_model=row.default_model,
            default_temperature=row.default_temperature,
            default_max_tokens=row.default_max_tokens,
            status=PromptStatus(row.status),
            current_version=row.current_version,
            tags=row.tags or [],
            metadata=row.metadata or {},
            created_at=row.created_at,
            updated_at=row.updated_at,
            created_by=row.created_by,
        )

    async def update_prompt(
        self,
        session: AsyncSession,
        prompt_id: str,
        template: str | None = None,
        system_prompt: str | None = None,
        change_description: str | None = None,
        **kwargs,
    ) -> Prompt | None:
        """Update a prompt and create a new version.

        Args:
            session: Database session
            prompt_id: Prompt ID
            template: New template
            system_prompt: New system prompt
            change_description: Description of changes
            **kwargs: Other fields to update

        Returns:
            Updated prompt
        """
        prompt = await self.get_prompt(session, prompt_id)
        if not prompt:
            return None

        # Update template if provided
        if template:
            prompt.template = template
            prompt.variables = self._extract_variables(template)

        if system_prompt is not None:
            prompt.system_prompt = system_prompt
            if system_prompt:
                prompt.variables.extend(self._extract_variables(system_prompt))
                prompt.variables = list(set(prompt.variables))

        # Update other fields
        for key, value in kwargs.items():
            if hasattr(prompt, key) and key not in ("id", "tenant_id", "created_at"):
                setattr(prompt, key, value)

        prompt.updated_at = datetime.now(UTC)

        # Create new version if template changed
        version_incremented = bool(template or system_prompt is not None)
        if version_incremented:
            prompt.current_version += 1
            await self._create_version(
                session, prompt, change_description or "Updated template"
            )

        # Update in database — use current_version + 1 in SQL to avoid race conditions
        version_expr = "current_version + 1" if version_incremented else "current_version"
        await session.execute(
            text(f"""
                UPDATE prompts SET
                    template = :template,
                    system_prompt = :system_prompt,
                    variables = :variables,
                    current_version = {version_expr},
                    updated_at = :updated_at,
                    status = :status,
                    description = :description,
                    category = :category
                WHERE id = :id
            """),
            {
                "id": prompt.id,
                "template": prompt.template,
                "system_prompt": prompt.system_prompt,
                "variables": prompt.variables,
                "updated_at": prompt.updated_at,
                "status": prompt.status.value,
                "description": prompt.description,
                "category": prompt.category,
            },
        )
        await session.flush()

        return prompt

    async def _create_version(
        self,
        session: AsyncSession,
        prompt: Prompt,
        change_description: str,
        created_by: str | None = None,
    ) -> PromptVersion:
        """Create a new version of a prompt."""
        version = PromptVersion(
            prompt_id=prompt.id,
            version=prompt.current_version,
            template=prompt.template,
            system_prompt=prompt.system_prompt,
            variables=prompt.variables,
            model=prompt.default_model,
            temperature=prompt.default_temperature,
            max_tokens=prompt.default_max_tokens,
            change_description=change_description,
            created_by=created_by or prompt.created_by,
        )

        await session.execute(
            text("""
                INSERT INTO prompt_versions (
                    id, prompt_id, version, template, system_prompt,
                    variables, model, temperature, max_tokens,
                    change_description, created_at, created_by
                ) VALUES (
                    :id, :prompt_id, :version, :template, :system_prompt,
                    :variables, :model, :temperature, :max_tokens,
                    :change_description, :created_at, :created_by
                )
            """),
            {
                "id": version.id,
                "prompt_id": version.prompt_id,
                "version": version.version,
                "template": version.template,
                "system_prompt": version.system_prompt,
                "variables": version.variables,
                "model": version.model,
                "temperature": version.temperature,
                "max_tokens": version.max_tokens,
                "change_description": version.change_description,
                "created_at": version.created_at,
                "created_by": version.created_by,
            },
        )

        return version

    async def get_version(
        self,
        session: AsyncSession,
        prompt_id: str,
        version: int,
    ) -> PromptVersion | None:
        """Get a specific version of a prompt."""
        result = await session.execute(
            text("""
                SELECT * FROM prompt_versions
                WHERE prompt_id = :prompt_id AND version = :version
            """),
            {"prompt_id": prompt_id, "version": version},
        )
        row = result.fetchone()

        if not row:
            return None

        return PromptVersion(
            id=row.id,
            prompt_id=row.prompt_id,
            version=row.version,
            template=row.template,
            system_prompt=row.system_prompt,
            variables=row.variables or [],
            model=row.model,
            temperature=row.temperature,
            max_tokens=row.max_tokens,
            change_description=row.change_description,
            created_at=row.created_at,
            created_by=row.created_by,
            usage_count=row.usage_count or 0,
        )

    async def list_versions(
        self,
        session: AsyncSession,
        prompt_id: str,
    ) -> list[PromptVersion]:
        """List all versions of a prompt."""
        result = await session.execute(
            text("""
                SELECT * FROM prompt_versions
                WHERE prompt_id = :prompt_id
                ORDER BY version DESC
            """),
            {"prompt_id": prompt_id},
        )

        return [
            PromptVersion(
                id=row.id,
                prompt_id=row.prompt_id,
                version=row.version,
                template=row.template,
                system_prompt=row.system_prompt,
                variables=row.variables or [],
                model=row.model,
                temperature=row.temperature,
                max_tokens=row.max_tokens,
                change_description=row.change_description,
                created_at=row.created_at,
                created_by=row.created_by,
            )
            for row in result.fetchall()
        ]

    async def render_prompt(
        self,
        session: AsyncSession,
        prompt_id: str,
        variables: dict[str, Any],
        version: int | None = None,
        user_id: str | None = None,
    ) -> tuple[str, str | None, int]:
        """Render a prompt with variables.

        Args:
            session: Database session
            prompt_id: Prompt ID
            variables: Variable values
            version: Optional specific version
            user_id: Optional user ID for experiment assignment

        Returns:
            Tuple of (rendered_template, rendered_system_prompt, version)
        """
        # Get version (with experiment assignment if applicable)
        if version is None:
            version = await self._get_assigned_version(
                session, prompt_id, user_id
            )

        prompt_version = await self.get_version(session, prompt_id, version)
        if not prompt_version:
            prompt = await self.get_prompt(session, prompt_id)
            if not prompt:
                raise ValueError(f"Prompt not found: {prompt_id}")
            template = prompt.template
            system_prompt = prompt.system_prompt
        else:
            template = prompt_version.template
            system_prompt = prompt_version.system_prompt

        # Render template
        rendered = self._render_template(template, variables)
        rendered_system = None
        if system_prompt:
            rendered_system = self._render_template(system_prompt, variables)

        return rendered, rendered_system, version

    def _render_template(
        self,
        template: str,
        variables: dict[str, Any],
    ) -> str:
        """Render a template with variables."""
        def replace_var(match):
            var_name = match.group(1)
            value = variables.get(var_name, f"{{{{MISSING:{var_name}}}}}")
            return str(value)

        return self.VARIABLE_PATTERN.sub(replace_var, template)

    async def _get_assigned_version(
        self,
        session: AsyncSession,
        prompt_id: str,
        user_id: str | None,
    ) -> int:
        """Get the assigned version for a user (handling experiments)."""
        # Get active experiment
        result = await session.execute(
            text("""
                SELECT * FROM prompt_experiments
                WHERE prompt_id = :prompt_id
                AND status = 'running'
                LIMIT 1
            """),
            {"prompt_id": prompt_id},
        )
        experiment_row = result.fetchone()

        if not experiment_row or not user_id:
            # No experiment - return current version
            prompt = await self.get_prompt(session, prompt_id)
            return prompt.current_version if prompt else 1

        # Check for existing assignment
        assignment_result = await session.execute(
            text("""
                SELECT assigned_version FROM prompt_assignments
                WHERE experiment_id = :experiment_id AND user_id = :user_id
            """),
            {"experiment_id": experiment_row.id, "user_id": user_id},
        )
        assignment = assignment_result.fetchone()

        if assignment:
            return assignment.assigned_version

        # Create new assignment
        assigned_version = self._assign_variant(
            user_id,
            experiment_row.control_version,
            experiment_row.treatment_versions or [],
            experiment_row.variant_weights or {},
            experiment_row.traffic_percentage,
        )

        # Save assignment
        await session.execute(
            text("""
                INSERT INTO prompt_assignments (
                    id, experiment_id, user_id, assigned_version, assigned_at, assignment_hash
                ) VALUES (
                    :id, :experiment_id, :user_id, :assigned_version, :assigned_at, :assignment_hash
                )
            """),
            {
                "id": str(uuid4()),
                "experiment_id": experiment_row.id,
                "user_id": user_id,
                "assigned_version": assigned_version,
                "assigned_at": datetime.now(UTC),
                "assignment_hash": hashlib.md5(f"{experiment_row.id}:{user_id}".encode()).hexdigest(),
            },
        )
        await session.flush()

        return assigned_version

    def _assign_variant(
        self,
        user_id: str,
        control_version: int,
        treatment_versions: list[int],
        variant_weights: dict[int, float],
        traffic_percentage: float,
    ) -> int:
        """Assign a user to an experiment variant."""
        # Hash user to get consistent assignment
        hash_input = f"experiment:{user_id}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest()[:8], 16)
        bucket = hash_value % 100

        # Check if user is in experiment traffic
        if bucket >= traffic_percentage:
            return control_version

        # Assign to variant based on weights
        all_versions = [control_version] + treatment_versions
        total_weight = sum(variant_weights.get(v, 1.0) for v in all_versions)

        variant_bucket = (hash_value % 1000) / 1000 * total_weight
        cumulative = 0

        for version in all_versions:
            weight = variant_weights.get(version, 1.0)
            cumulative += weight
            if variant_bucket < cumulative:
                return version

        return control_version

    async def record_performance(
        self,
        session: AsyncSession,
        tenant_id: str,
        prompt_id: str,
        version: int,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        success: bool,
        user_id: str | None = None,
        experiment_id: str | None = None,
        error: str | None = None,
        quality_score: float | None = None,
        cost_usd: float | None = None,
    ) -> None:
        """Record prompt execution performance."""
        from uuid import uuid4

        await session.execute(
            text("""
                INSERT INTO prompt_performance (
                    id, tenant_id, prompt_id, version, user_id, experiment_id,
                    model, input_tokens, output_tokens, latency_ms,
                    success, error, quality_score, cost_usd, executed_at
                ) VALUES (
                    :id, :tenant_id, :prompt_id, :version, :user_id, :experiment_id,
                    :model, :input_tokens, :output_tokens, :latency_ms,
                    :success, :error, :quality_score, :cost_usd, :executed_at
                )
            """),
            {
                "id": str(uuid4()),
                "tenant_id": tenant_id,
                "prompt_id": prompt_id,
                "version": version,
                "user_id": user_id,
                "experiment_id": experiment_id,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "latency_ms": latency_ms,
                "success": success,
                "error": error,
                "quality_score": quality_score,
                "cost_usd": cost_usd,
                "executed_at": datetime.now(UTC),
            },
        )

        # Update version stats
        await session.execute(
            text("""
                UPDATE prompt_versions SET usage_count = usage_count + 1
                WHERE prompt_id = :prompt_id AND version = :version
            """),
            {"prompt_id": prompt_id, "version": version},
        )

    async def get_stats(
        self,
        session: AsyncSession,
        prompt_id: str,
        version: int | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> PromptStats:
        """Get performance statistics for a prompt."""
        sql = """
            SELECT
                COUNT(*) as total_executions,
                COUNT(DISTINCT user_id) as unique_users,
                AVG(latency_ms) as avg_latency,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY latency_ms) as p50_latency,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) as p95_latency,
                AVG(input_tokens) as avg_input_tokens,
                AVG(output_tokens) as avg_output_tokens,
                AVG(CASE WHEN success THEN 1.0 ELSE 0.0 END) as success_rate,
                AVG(quality_score) as avg_quality_score,
                SUM(cost_usd) as total_cost
            FROM prompt_performance
            WHERE prompt_id = :prompt_id
        """
        params: dict[str, Any] = {"prompt_id": prompt_id}

        if version:
            sql += " AND version = :version"
            params["version"] = version

        if start_date:
            sql += " AND executed_at >= :start_date"
            params["start_date"] = start_date

        if end_date:
            sql += " AND executed_at < :end_date"
            params["end_date"] = end_date

        result = await session.execute(text(sql), params)
        row = result.fetchone()

        return PromptStats(
            prompt_id=prompt_id,
            version=version,
            total_executions=row.total_executions or 0,
            unique_users=row.unique_users or 0,
            avg_latency_ms=row.avg_latency,
            p50_latency_ms=row.p50_latency,
            p95_latency_ms=row.p95_latency,
            avg_input_tokens=row.avg_input_tokens,
            avg_output_tokens=row.avg_output_tokens,
            success_rate=row.success_rate,
            avg_quality_score=row.avg_quality_score,
            total_cost_usd=row.total_cost or 0,
            period_start=start_date,
            period_end=end_date,
        )

    # -----------------------------------------------------------------
    # Langfuse integration
    # -----------------------------------------------------------------

    async def get_langfuse_prompt(
        self,
        name: str,
        variables: dict[str, Any],
        *,
        label: str | None = None,
        version: int | None = None,
        fallback_template: str | None = None,
    ) -> tuple[str | None, str | None, Any | None]:
        """Fetch a prompt from Langfuse, compile it, and return.

        Falls back to None values if Langfuse is unavailable.

        Args:
            name: Prompt name in Langfuse.
            variables: Template variables for compilation.
            label: Label to fetch (default: "production").
            version: Specific version number.
            fallback_template: Fallback template if Langfuse is unavailable.

        Returns:
            Tuple of (compiled_template, system_prompt_from_config, prompt_client).
            All None if Langfuse is unavailable.
        """
        from app.services.prompts.langfuse_manager import get_langfuse_prompt_manager

        manager = await get_langfuse_prompt_manager()
        if not manager.enabled:
            return None, None, None

        prompt_client = await manager.get_prompt(
            name,
            label=label,
            version=version,
            fallback=fallback_template,
        )
        if prompt_client is None:
            return None, None, None

        try:
            compiled = prompt_client.compile(**variables)

            # Extract system_prompt from config if stored there
            system_prompt = None
            if hasattr(prompt_client, "config") and prompt_client.config:
                system_prompt = prompt_client.config.get("system_prompt")

            return compiled, system_prompt, prompt_client
        except Exception as e:
            logger.warning(
                "langfuse_prompt_compile_failed",
                name=name,
                error=str(e),
            )
            return None, None, prompt_client

    async def render_prompt_with_langfuse(
        self,
        session: AsyncSession,
        prompt_id: str,
        variables: dict[str, Any],
        version: int | None = None,
        user_id: str | None = None,
        langfuse_name: str | None = None,
        langfuse_label: str | None = None,
    ) -> tuple[str, str | None, int, Any | None]:
        """Render a prompt, trying Langfuse first then falling back to local DB.

        Args:
            session: Database session.
            prompt_id: Local prompt ID.
            variables: Template variables.
            version: Specific version.
            user_id: User ID for experiment assignment.
            langfuse_name: Langfuse prompt name. If None, uses prompt slug.
            langfuse_label: Langfuse label to fetch.

        Returns:
            Tuple of (rendered_template, rendered_system_prompt, version, prompt_client).
            prompt_client is the Langfuse PromptClient (or None if local fallback).
        """
        prompt_client = None

        # Try Langfuse first
        if langfuse_name:
            lf_name = langfuse_name
        else:
            # Use the prompt slug as Langfuse name
            prompt = await self.get_prompt(session, prompt_id)
            lf_name = prompt.slug if prompt else None

        if lf_name:
            compiled, system_prompt, prompt_client = await self.get_langfuse_prompt(
                lf_name, variables, label=langfuse_label
            )
            if compiled is not None:
                logger.debug(
                    "prompt_rendered_from_langfuse",
                    name=lf_name,
                    version=prompt_client.version if prompt_client else None,
                )
                return compiled, system_prompt, (prompt_client.version if prompt_client else 1), prompt_client

        # Fall back to local DB
        rendered, rendered_system, ver = await self.render_prompt(
            session, prompt_id, variables, version, user_id
        )
        return rendered, rendered_system, ver, None

    async def sync_to_langfuse(
        self,
        session: AsyncSession,
        prompt_id: str,
        *,
        labels: list[str] | None = None,
        tags: list[str] | None = None,
        commit_message: str | None = None,
    ) -> Any | None:
        """Push a local prompt to Langfuse.

        Creates a new version in Langfuse from the current local prompt data.

        Args:
            session: Database session.
            prompt_id: Local prompt ID.
            labels: Labels to assign (default: ["production"]).
            tags: Tags for organization.
            commit_message: Version description.

        Returns:
            The Langfuse PromptClient if created, None if unavailable.
        """
        from app.services.prompts.langfuse_manager import get_langfuse_prompt_manager

        prompt = await self.get_prompt(session, prompt_id)
        if not prompt:
            logger.warning("sync_to_langfuse_prompt_not_found", prompt_id=prompt_id)
            return None

        manager = await get_langfuse_prompt_manager()
        if not manager.enabled:
            return None

        config: dict[str, Any] = {}
        if prompt.system_prompt:
            config["system_prompt"] = prompt.system_prompt
        if prompt.default_model:
            config["model"] = prompt.default_model
        if prompt.default_temperature is not None:
            config["temperature"] = prompt.default_temperature
        if prompt.default_max_tokens is not None:
            config["max_tokens"] = prompt.default_max_tokens

        return await manager.sync_from_local(
            name=prompt.slug,
            template=prompt.template,
            system_prompt=prompt.system_prompt,
            config=config if config else None,
            labels=labels or ["production"],
            tags=tags or prompt.tags,
            commit_message=commit_message or f"Synced v{prompt.current_version} from local",
        )

    def _extract_variables(self, template: str) -> list[str]:
        """Extract variable names from a template."""
        return list(set(self.VARIABLE_PATTERN.findall(template)))

    def _generate_slug(self, name: str) -> str:
        """Generate a URL-friendly slug from a name."""
        slug = name.lower()
        slug = re.sub(r"[^a-z0-9\s-]", "", slug)
        slug = re.sub(r"[\s_]+", "-", slug)
        slug = re.sub(r"-+", "-", slug)
        return slug.strip("-")


# Import uuid4 for the module
from uuid import uuid4

# Global registry instance
_prompt_registry: PromptRegistry | None = None


def get_prompt_registry() -> PromptRegistry:
    """Get the global prompt registry instance."""
    global _prompt_registry
    if _prompt_registry is None:
        _prompt_registry = PromptRegistry()
    return _prompt_registry
