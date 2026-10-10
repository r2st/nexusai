"""DevLake Blueprint Pipeline Configuration.

Blueprint-based pipeline system for configuring and running
data collection pipelines across multiple plugins and connections.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, Enum as SQLEnum, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.multitenancy import generate_domain_id


class BlueprintMode(str, Enum):
    """Blueprint execution modes."""
    NORMAL = "NORMAL"
    ADVANCED = "ADVANCED"


class BlueprintStatus(str, Enum):
    """Blueprint status."""
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    DISABLED = "DISABLED"


class PipelineStatus(str, Enum):
    """Pipeline run status."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    PARTIAL = "PARTIAL"


class SyncPolicy(BaseModel):
    """Sync policy for blueprint scheduling."""

    plugin: str
    connection_id: str
    scope_id: str
    scope_type: str = "repo"

    # Sync settings
    full_sync: bool = False
    time_after: datetime | None = None

    # Transformation rules
    transformation_rule_id: str | None = None


class BlueprintSettings(BaseModel):
    """Blueprint configuration settings."""

    version: str = "2.0.0"
    time_after: datetime | None = None
    skip_on_fail: bool = False

    # Connections to sync
    connections: list[dict[str, Any]] = []

    # Sync policies per scope
    sync_policies: list[SyncPolicy] = []


class Blueprint(Base):
    """Blueprint model for pipeline configuration."""

    __tablename__ = "blueprints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)

    name = Column(String(255), nullable=False)
    description = Column(Text)

    mode = Column(SQLEnum(BlueprintMode), default=BlueprintMode.NORMAL)
    status = Column(SQLEnum(BlueprintStatus), default=BlueprintStatus.ACTIVE)

    # Cron schedule (e.g., "0 0 * * *" for daily)
    cron_config = Column(String(100))
    is_manual = Column(String(10), default="false")

    # Blueprint settings (connections, sync policies, etc.)
    settings = Column(JSON, default=dict)

    # Plan - the actual pipeline stages
    plan = Column(JSON, default=list)

    # Labels for organization
    labels = Column(JSON, default=list)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="blueprints")
    pipeline_runs = relationship("PipelineRun", back_populates="blueprint")


class PipelineRun(Base):
    """Pipeline run execution record."""

    __tablename__ = "pipeline_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    blueprint_id = Column(UUID(as_uuid=True), ForeignKey("blueprints.id"))

    name = Column(String(255))
    status = Column(SQLEnum(PipelineStatus), default=PipelineStatus.PENDING)

    # Execution details
    plan = Column(JSON, default=list)  # Stages to execute
    stages = Column(JSON, default=list)  # Stage results

    # Progress tracking
    stage_index = Column(String(10), default="0")
    finished_tasks = Column(String(10), default="0")
    total_tasks = Column(String(10), default="0")

    # Error handling
    error_message = Column(Text)
    skip_on_fail = Column(String(10), default="false")

    # Timing
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    blueprint = relationship("Blueprint", back_populates="pipeline_runs")


class BlueprintService:
    """Service for managing blueprints and pipelines."""

    async def create_blueprint(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_id: str,
        name: str,
        connections: list[dict[str, Any]],
        cron_config: str | None = None,
        description: str | None = None,
        mode: BlueprintMode = BlueprintMode.NORMAL,
    ) -> Blueprint:
        """Create a new blueprint for data collection.

        Args:
            session: Database session
            tenant_id: Tenant ID
            project_id: Project ID
            name: Blueprint name
            connections: List of connection configs
            cron_config: Cron schedule (optional)
            description: Blueprint description
            mode: Blueprint mode (NORMAL or ADVANCED)

        Returns:
            Created Blueprint
        """
        # Build settings
        settings = BlueprintSettings(
            connections=connections,
        )

        # Generate execution plan from connections
        plan = self._generate_plan(connections)

        blueprint = Blueprint(
            tenant_id=tenant_id,
            project_id=project_id,
            name=name,
            description=description,
            mode=mode,
            cron_config=cron_config,
            is_manual="true" if not cron_config else "false",
            settings=settings.model_dump(),
            plan=plan,
        )

        session.add(blueprint)
        await session.commit()
        await session.refresh(blueprint)

        return blueprint

    def _generate_plan(self, connections: list[dict[str, Any]]) -> list[list[dict]]:
        """Generate pipeline plan from connection configs.

        Plan is a 2D array: [[stage1_tasks], [stage2_tasks], ...]
        Tasks in the same stage run in parallel.
        Stages run sequentially.
        """
        plan = []

        # Stage 1: Collect data from all sources (parallel)
        collect_stage = []
        for conn in connections:
            plugin = conn.get("plugin", "")
            connection_id = conn.get("connectionId")
            scopes = conn.get("scopes", [])

            for scope in scopes:
                task = {
                    "plugin": plugin,
                    "subtasks": self._get_plugin_subtasks(plugin, "collect"),
                    "options": {
                        "connectionId": connection_id,
                        "scopeId": scope.get("id"),
                        "scopeType": scope.get("type", "repo"),
                        **scope.get("options", {}),
                    },
                }
                collect_stage.append(task)

        if collect_stage:
            plan.append(collect_stage)

        # Stage 2: Extract/Transform (parallel)
        extract_stage = []
        for conn in connections:
            plugin = conn.get("plugin", "")
            connection_id = conn.get("connectionId")
            scopes = conn.get("scopes", [])

            for scope in scopes:
                task = {
                    "plugin": plugin,
                    "subtasks": self._get_plugin_subtasks(plugin, "extract"),
                    "options": {
                        "connectionId": connection_id,
                        "scopeId": scope.get("id"),
                        "transformationRuleId": scope.get("transformationRuleId"),
                    },
                }
                extract_stage.append(task)

        if extract_stage:
            plan.append(extract_stage)

        # Stage 3: Convert to domain models (parallel)
        convert_stage = []
        for conn in connections:
            plugin = conn.get("plugin", "")
            connection_id = conn.get("connectionId")
            scopes = conn.get("scopes", [])

            for scope in scopes:
                task = {
                    "plugin": plugin,
                    "subtasks": self._get_plugin_subtasks(plugin, "convert"),
                    "options": {
                        "connectionId": connection_id,
                        "scopeId": scope.get("id"),
                    },
                }
                convert_stage.append(task)

        if convert_stage:
            plan.append(convert_stage)

        # Stage 4: Calculate DORA metrics (sequential - needs all data)
        dora_stage = [{
            "plugin": "dora",
            "subtasks": [
                "calculateDeploymentFrequency",
                "calculateLeadTime",
                "calculateChangeFailureRate",
                "calculateMTTR",
            ],
            "options": {},
        }]
        plan.append(dora_stage)

        return plan

    def _get_plugin_subtasks(self, plugin: str, phase: str) -> list[str]:
        """Get subtasks for a plugin based on execution phase."""
        subtask_map = {
            "github": {
                "collect": [
                    "collectRepos",
                    "collectCommits",
                    "collectPullRequests",
                    "collectIssues",
                    "collectDeployments",
                    "collectWorkflows",
                ],
                "extract": [
                    "extractRepos",
                    "extractCommits",
                    "extractPullRequests",
                    "extractIssues",
                    "extractDeployments",
                ],
                "convert": [
                    "convertRepos",
                    "convertCommits",
                    "convertPullRequests",
                    "convertIssues",
                    "convertDeployments",
                ],
            },
            "gitlab": {
                "collect": [
                    "collectProjects",
                    "collectCommits",
                    "collectMergeRequests",
                    "collectIssues",
                    "collectPipelines",
                ],
                "extract": [
                    "extractProjects",
                    "extractCommits",
                    "extractMergeRequests",
                    "extractIssues",
                ],
                "convert": [
                    "convertProjects",
                    "convertCommits",
                    "convertMergeRequests",
                    "convertIssues",
                ],
            },
            "jira": {
                "collect": [
                    "collectBoards",
                    "collectSprints",
                    "collectIssues",
                    "collectWorklogs",
                ],
                "extract": [
                    "extractBoards",
                    "extractSprints",
                    "extractIssues",
                ],
                "convert": [
                    "convertBoards",
                    "convertSprints",
                    "convertIssues",
                ],
            },
            "jenkins": {
                "collect": [
                    "collectJobs",
                    "collectBuilds",
                    "collectStages",
                ],
                "extract": [
                    "extractJobs",
                    "extractBuilds",
                ],
                "convert": [
                    "convertJobs",
                    "convertBuilds",
                ],
            },
            "bitbucket": {
                "collect": [
                    "collectRepos",
                    "collectCommits",
                    "collectPullRequests",
                    "collectPipelines",
                ],
                "extract": [
                    "extractRepos",
                    "extractCommits",
                    "extractPullRequests",
                ],
                "convert": [
                    "convertRepos",
                    "convertCommits",
                    "convertPullRequests",
                ],
            },
            "sonarqube": {
                "collect": [
                    "collectProjects",
                    "collectIssues",
                    "collectMetrics",
                ],
                "extract": [
                    "extractProjects",
                    "extractIssues",
                ],
                "convert": [
                    "convertProjects",
                    "convertIssues",
                ],
            },
            "pagerduty": {
                "collect": [
                    "collectServices",
                    "collectIncidents",
                ],
                "extract": [
                    "extractServices",
                    "extractIncidents",
                ],
                "convert": [
                    "convertServices",
                    "convertIncidents",
                ],
            },
            "argocd": {
                "collect": [
                    "collectApplications",
                    "collectDeployments",
                ],
                "extract": [
                    "extractApplications",
                    "extractDeployments",
                ],
                "convert": [
                    "convertApplications",
                    "convertDeployments",
                ],
            },
        }

        return subtask_map.get(plugin, {}).get(phase, [])

    async def run_blueprint(
        self,
        session: AsyncSession,
        blueprint_id: str,
        full_sync: bool = False,
    ) -> PipelineRun:
        """Trigger a pipeline run from a blueprint.

        Args:
            session: Database session
            blueprint_id: Blueprint ID to run
            full_sync: Whether to do a full sync

        Returns:
            Created PipelineRun
        """
        from sqlalchemy import select

        # Get blueprint
        result = await session.execute(
            select(Blueprint).where(Blueprint.id == blueprint_id)
        )
        blueprint = result.scalar_one_or_none()

        if not blueprint:
            raise ValueError(f"Blueprint {blueprint_id} not found")

        # Create pipeline run
        pipeline_run = PipelineRun(
            tenant_id=blueprint.tenant_id,
            blueprint_id=blueprint.id,
            name=f"{blueprint.name} - {datetime.utcnow().isoformat()}",
            status=PipelineStatus.PENDING,
            plan=blueprint.plan,
            total_tasks=str(sum(len(stage) for stage in blueprint.plan)),
        )

        session.add(pipeline_run)
        await session.commit()
        await session.refresh(pipeline_run)

        # TODO: Trigger actual DevLake pipeline execution
        # This would call the DevLake API to start the pipeline

        return pipeline_run

    async def get_pipeline_status(
        self,
        session: AsyncSession,
        pipeline_id: str,
    ) -> PipelineRun | None:
        """Get pipeline run status.

        Args:
            session: Database session
            pipeline_id: Pipeline run ID

        Returns:
            PipelineRun or None
        """
        from sqlalchemy import select

        result = await session.execute(
            select(PipelineRun).where(PipelineRun.id == pipeline_id)
        )
        return result.scalar_one_or_none()

    async def cancel_pipeline(
        self,
        session: AsyncSession,
        pipeline_id: str,
    ) -> bool:
        """Cancel a running pipeline.

        Args:
            session: Database session
            pipeline_id: Pipeline run ID

        Returns:
            True if cancelled successfully
        """
        from sqlalchemy import select

        result = await session.execute(
            select(PipelineRun).where(PipelineRun.id == pipeline_id)
        )
        pipeline = result.scalar_one_or_none()

        if not pipeline:
            return False

        if pipeline.status == PipelineStatus.RUNNING:
            pipeline.status = PipelineStatus.CANCELLED
            pipeline.finished_at = datetime.utcnow()
            await session.commit()
            return True

        return False

    async def list_blueprints(
        self,
        session: AsyncSession,
        tenant_id: str,
        project_id: str | None = None,
        status: BlueprintStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Blueprint]:
        """List blueprints for a tenant.

        Args:
            session: Database session
            tenant_id: Tenant ID
            project_id: Optional project filter
            status: Optional status filter
            limit: Max results to return
            offset: Pagination offset

        Returns:
            List of Blueprints
        """
        from sqlalchemy import select

        query = select(Blueprint).where(Blueprint.tenant_id == tenant_id)

        if project_id:
            query = query.where(Blueprint.project_id == project_id)

        if status:
            query = query.where(Blueprint.status == status)

        query = query.order_by(Blueprint.created_at.desc()).offset(offset).limit(limit)

        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_pipeline_history(
        self,
        session: AsyncSession,
        blueprint_id: str,
        limit: int = 10,
    ) -> list[PipelineRun]:
        """Get pipeline run history for a blueprint.

        Args:
            session: Database session
            blueprint_id: Blueprint ID
            limit: Max results

        Returns:
            List of PipelineRuns
        """
        from sqlalchemy import select

        result = await session.execute(
            select(PipelineRun)
            .where(PipelineRun.blueprint_id == blueprint_id)
            .order_by(PipelineRun.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


# Singleton instance
blueprint_service = BlueprintService()
