"""
Integration tests for newly implemented backend services.

Tests cover:
- Event Ingestion Service
- Entity Service
- Message Queue
- Connectors
- Rollups
- Query Gateway
- Prompt Registry
- Evaluation Framework
"""

import pytest
from datetime import UTC, datetime, timedelta
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.user import User, UserRole


@pytest.fixture
async def test_user_with_org(db_session: AsyncSession):
    """Create a test user with organization for testing new services."""
    from app.models.organization import Organization, OrganizationMember, MemberRole

    # Create user
    user = User(
        id=uuid4(),
        email="testservices@nexusai.dev",
        username="testservices",
        hashed_password=get_password_hash("test123"),
        full_name="Test Services User",
        role=UserRole.USER.value,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.flush()

    # Create organization
    tenant_id = str(uuid4())
    org = Organization(
        id=str(uuid4()),
        tenant_id=tenant_id,
        name="Test Services Org",
        slug="test-services-org",
    )
    db_session.add(org)
    await db_session.flush()

    # Add user to organization
    member = OrganizationMember(
        id=str(uuid4()),
        tenant_id=tenant_id,
        organization_id=org.id,
        user_id=str(user.id),
        role=MemberRole.OWNER.value,
    )
    db_session.add(member)

    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(org)

    return {"user": user, "organization": org, "tenant_id": tenant_id}


@pytest.fixture
async def auth_token(client: AsyncClient, test_user_with_org) -> str:
    """Get authentication token for test user."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "testservices@nexusai.dev",
            "password": "test123",
        },
    )
    if response.status_code != 200:
        pytest.skip("Could not authenticate test user")
    return response.json()["tokens"]["access_token"]


class TestEventIngestionService:
    """Tests for the Event Ingestion Service."""

    @pytest.mark.asyncio
    async def test_event_models_import(self):
        """Test event models can be imported."""
        from app.services.events.models import (
            RawEvent,
            EventEnvelope,
            EventSource,
            EventType,
            WebhookPayload,
        )

        # Create a raw event
        event = RawEvent(
            tenant_id="test-tenant",
            source=EventSource.GITHUB,
            source_event_type="push",
            event_type=EventType.PUSH,
            payload={"ref": "refs/heads/main"},
        )

        assert event.id is not None
        assert event.source == EventSource.GITHUB
        assert event.event_type == EventType.PUSH
        assert event.processed is False

    @pytest.mark.asyncio
    async def test_webhook_handler_normalization(self):
        """Test webhook handler normalizes events correctly."""
        from app.services.events.webhooks import WebhookHandler
        from app.services.events.models import EventSource, EventType, WebhookPayload
        from unittest.mock import AsyncMock

        handler = WebhookHandler()
        handler.event_store = AsyncMock()
        handler.event_store.store.return_value = "path/to/event.json"
        handler._publisher = AsyncMock()

        # Test GitHub push normalization
        event_type = handler._normalize_event_type(
            EventSource.GITHUB,
            "push",
            {"ref": "refs/heads/main"},
        )
        assert event_type == EventType.PUSH

        # Test GitHub PR opened
        event_type = handler._normalize_event_type(
            EventSource.GITHUB,
            "pull_request",
            {"action": "opened"},
        )
        assert event_type == EventType.PR_OPENED

        # Test GitHub PR merged
        event_type = handler._normalize_event_type(
            EventSource.GITHUB,
            "pull_request",
            {"action": "closed", "pull_request": {"merged": True}},
        )
        assert event_type == EventType.PR_MERGED

    @pytest.mark.asyncio
    async def test_event_sources_coverage(self):
        """Test all major event sources are defined."""
        from app.services.events.models import EventSource

        expected_sources = [
            "github", "gitlab", "jira", "slack",
            "pagerduty", "jenkins", "kubernetes",
        ]

        source_values = [s.value for s in EventSource]
        for source in expected_sources:
            assert source in source_values, f"Missing source: {source}"


class TestEntityService:
    """Tests for the Entity Service."""

    @pytest.mark.asyncio
    async def test_entity_models_import(self):
        """Test entity models can be imported."""
        from app.services.entities.models import (
            Entity,
            EntityType,
            Repository,
            Commit,
            PullRequest,
            Build,
            Deployment,
            Incident,
            Developer,
        )

        # Create a repository entity
        repo = Repository(
            tenant_id="test-tenant",
            source="github",
            source_id="12345",
            name="test-repo",
            full_name="org/test-repo",
        )

        assert repo.entity_type == EntityType.REPOSITORY
        assert repo.name == "test-repo"

    @pytest.mark.asyncio
    async def test_entity_domain_id_generation(self):
        """Test domain ID generation for entities."""
        from app.services.entities.models import Repository, EntityType

        repo = Repository(
            tenant_id="tenant-123",
            source="github",
            source_id="repo-456",
            connection_id="conn-789",
            name="test-repo",
            full_name="org/test-repo",
        )

        domain_id = repo.generate_domain_id()

        assert "tenant-123" in domain_id
        assert "github" in domain_id
        assert "repo-456" in domain_id
        assert "repository" in domain_id

    @pytest.mark.asyncio
    async def test_github_normalizer(self):
        """Test GitHub event normalization."""
        from app.services.entities.normalizers.github import GitHubNormalizer
        from app.services.entities.models import EntityType

        normalizer = GitHubNormalizer()

        # Test push event normalization
        entities = normalizer.normalize(
            event_type="push",
            payload={
                "repository": {
                    "id": 123,
                    "name": "test-repo",
                    "full_name": "org/test-repo",
                },
                "commits": [
                    {
                        "id": "abc123",
                        "message": "Test commit",
                        "author": {"name": "Test Author", "email": "test@example.com"},
                    }
                ],
                "ref": "refs/heads/main",
            },
            tenant_id="test-tenant",
        )

        # Should have repository and commit entities
        entity_types = [e.entity_type for e in entities]
        assert EntityType.REPOSITORY in entity_types
        assert EntityType.COMMIT in entity_types


class TestMessageQueue:
    """Tests for the Message Queue service."""

    @pytest.mark.asyncio
    async def test_queue_config(self):
        """Test queue configuration."""
        from app.services.queue.config import QueueConfig, get_queue_config

        config = get_queue_config()

        assert config.url is not None
        assert config.events_stream is not None
        assert config.events_stream.name == "EVENTS"

    @pytest.mark.asyncio
    async def test_event_publisher_memory_mode(self):
        """Test event publisher in memory mode."""
        from app.services.events.publisher import EventPublisher
        from app.services.events.models import RawEvent, EventSource, EventType

        publisher = EventPublisher()
        publisher._use_nats = False  # Force memory mode

        # Create and publish an event
        event = RawEvent(
            tenant_id="test-tenant",
            source=EventSource.GITHUB,
            source_event_type="push",
            event_type=EventType.PUSH,
            payload={"test": "data"},
        )

        msg_id = await publisher.publish(event, "path/to/event.json")

        assert msg_id is not None
        assert publisher._memory_queue.qsize() == 1


class TestConnectorFramework:
    """Tests for the Connector Framework."""

    @pytest.mark.asyncio
    async def test_connector_base_class(self):
        """Test base connector interface."""
        from app.services.connectors.base import (
            BaseConnector,
            ConnectorConfig,
            ConnectorStatus,
        )

        config = ConnectorConfig(
            id="test-connector",
            tenant_id="test-tenant",
            source="github",
            name="Test GitHub Connector",
        )

        assert config.status == ConnectorStatus.PENDING
        assert config.source == "github"

    @pytest.mark.asyncio
    async def test_connector_registry(self):
        """Test connector registry."""
        from app.services.connectors.registry import get_connector_registry

        registry = get_connector_registry()

        # Check registered connectors
        supported = registry.list_supported_sources()
        assert "github" in supported
        assert "gitlab" in supported

    @pytest.mark.asyncio
    async def test_github_connector_init(self):
        """Test GitHub connector initialization."""
        from app.services.connectors.github import GitHubConnector
        from app.services.connectors.base import ConnectorConfig

        config = ConnectorConfig(
            id="test-github",
            tenant_id="test-tenant",
            source="github",
            name="Test GitHub",
            credentials={"token": "test-token"},
        )

        connector = GitHubConnector(config)

        assert connector.source == "github"
        assert connector.token == "test-token"


class TestRollupService:
    """Tests for the Precomputed Rollups service."""

    @pytest.mark.asyncio
    async def test_rollup_models(self):
        """Test rollup models."""
        from app.services.rollups.models import (
            DORArollup,
            SPACERollup,
            RollupGranularity,
        )

        now = datetime.now(UTC)
        dora = DORArollup(
            tenant_id="test-tenant",
            granularity=RollupGranularity.DAILY,
            period_start=now - timedelta(days=1),
            period_end=now,
            deployment_count=10,
            deployment_frequency=1.5,
        )

        assert dora.deployment_count == 10
        assert dora.granularity == RollupGranularity.DAILY

    @pytest.mark.asyncio
    async def test_rollup_service_level_calculation(self):
        """Test DORA performance level calculation."""
        from app.services.rollups.service import RollupService

        service = RollupService()

        # Test deployment frequency levels
        elite = service._get_level("deployment_frequency", 2.0, higher_is_better=True)
        assert elite == "elite"

        high = service._get_level("deployment_frequency", 0.5, higher_is_better=True)
        assert high == "high"

        # Test lead time levels (lower is better)
        elite_lt = service._get_level("lead_time", 12, higher_is_better=False)
        assert elite_lt == "elite"

        low_lt = service._get_level("lead_time", 1000, higher_is_better=False)
        assert low_lt == "low"


class TestQueryGateway:
    """Tests for the Query Gateway service."""

    @pytest.mark.asyncio
    async def test_query_models(self):
        """Test query gateway models."""
        from app.services.query.models import (
            QueryRequest,
            DataSource,
            DASHBOARD_QUERIES,
        )

        # Test query request
        request = QueryRequest(
            sources=[DataSource.METRICS, DataSource.ENTITIES],
            include_trends=True,
        )

        assert DataSource.METRICS in request.sources
        assert request.limit == 100

        # Test pre-defined dashboards
        assert "overview" in DASHBOARD_QUERIES
        assert "team_health" in DASHBOARD_QUERIES

    @pytest.mark.asyncio
    async def test_query_gateway_dashboard_list(self):
        """Test listing available dashboards."""
        from app.services.query.gateway import get_query_gateway

        gateway = get_query_gateway()
        dashboards = gateway.list_dashboards()

        assert len(dashboards) > 0
        assert any(d["name"] == "Overview Dashboard" for d in dashboards)


class TestPromptRegistry:
    """Tests for the Prompt Registry service."""

    @pytest.mark.asyncio
    async def test_prompt_models(self):
        """Test prompt models."""
        from app.services.prompts.models import (
            Prompt,
            PromptVersion,
            PromptExperiment,
            PromptStatus,
        )

        prompt = Prompt(
            tenant_id="test-tenant",
            name="Test Prompt",
            slug="test-prompt",
            template="Hello {{name}}, how can I help you with {{topic}}?",
            variables=["name", "topic"],
        )

        assert prompt.status == PromptStatus.DRAFT
        assert "name" in prompt.variables
        assert "topic" in prompt.variables

    @pytest.mark.asyncio
    async def test_prompt_registry_variable_extraction(self):
        """Test variable extraction from templates."""
        from app.services.prompts.registry import PromptRegistry

        registry = PromptRegistry()

        # Test variable extraction
        template = "Hello {{user}}, your project {{project}} has {{count}} issues."
        variables = registry._extract_variables(template)

        assert "user" in variables
        assert "project" in variables
        assert "count" in variables
        assert len(variables) == 3

    @pytest.mark.asyncio
    async def test_prompt_registry_template_rendering(self):
        """Test template rendering."""
        from app.services.prompts.registry import PromptRegistry

        registry = PromptRegistry()

        template = "Hello {{name}}, welcome to {{app}}!"
        rendered = registry._render_template(template, {
            "name": "John",
            "app": "NexusAI",
        })

        assert rendered == "Hello John, welcome to NexusAI!"


class TestEvaluationFramework:
    """Tests for the Evaluation Framework."""

    @pytest.mark.asyncio
    async def test_evaluation_models(self):
        """Test evaluation models."""
        from app.services.evaluation.models import (
            TestCase,
            TestSet,
            EvalRun,
            TestCaseType,
            EvalStatus,
        )

        test_case = TestCase(
            name="Test greeting",
            input_variables={"user": "John"},
            expected_contains=["hello", "john"],
            eval_type=TestCaseType.CONTAINS,
        )

        assert test_case.eval_type == TestCaseType.CONTAINS
        assert "hello" in test_case.expected_contains

    @pytest.mark.asyncio
    async def test_contains_evaluator(self):
        """Test contains evaluator."""
        from app.services.evaluation.evaluator import ContainsEvaluator
        from app.services.evaluation.models import TestCase, TestCaseType

        evaluator = ContainsEvaluator()

        test_case = TestCase(
            name="Test contains",
            input_variables={},
            expected_contains=["hello", "world"],
            expected_not_contains=["error", "fail"],
            eval_type=TestCaseType.CONTAINS,
        )

        # Test passing case
        metrics = evaluator.evaluate(test_case, "Hello World! Everything is working.")

        assert len(metrics) == 2
        contains_metric = next(m for m in metrics if m.name == "contains")
        not_contains_metric = next(m for m in metrics if m.name == "not_contains")

        assert contains_metric.passed is True
        assert not_contains_metric.passed is True

        # Test failing case
        metrics = evaluator.evaluate(test_case, "This has an error!")

        not_contains_metric = next(m for m in metrics if m.name == "not_contains")
        assert not_contains_metric.passed is False

    @pytest.mark.asyncio
    async def test_evaluator_integration(self):
        """Test full evaluator with multiple strategies."""
        from app.services.evaluation.evaluator import Evaluator
        from app.services.evaluation.models import TestCase, TestCaseType

        evaluator = Evaluator()

        test_case = TestCase(
            name="Integration test",
            input_variables={"query": "test"},
            expected_contains=["answer", "response"],
            eval_type=TestCaseType.CONTAINS,
        )

        result = evaluator.evaluate(
            test_case,
            "Here is the answer to your question. This response should help.",
            latency_ms=150,
            model="gpt-4",
        )

        assert result.test_case_name == "Integration test"
        assert result.latency_ms == 150
        assert result.model == "gpt-4"
        assert result.passed is True
