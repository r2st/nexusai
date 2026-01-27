"""Comprehensive unit tests for the Agent Orchestrator."""

import asyncio
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio

from app.services.agents.orchestrator.state import (
    AgentNode,
    OrchestratorState,
    TaskResult,
    WorkflowStatus,
    Message,
    create_initial_state,
)
from app.services.agents.orchestrator.router import (
    IntentRouter,
    IntentClassification,
    TaskIntent,
    INTENT_AGENT_MAP,
    INTENT_PATTERNS,
)
from app.services.agents.orchestrator.nodes import (
    BaseAgentNode,
    SupervisorNode,
    SetupAgentNode,
    MetricsAgentNode,
    QueryAgentNode,
    InsightsAgentNode,
    CodeAnalysisNode,
    HumanInputNode,
    get_agent_node,
)
from app.services.agents.orchestrator.orchestrator import (
    AgentOrchestrator,
    get_orchestrator,
    create_orchestrator,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_llm_gateway():
    """Create a mock LLM gateway."""
    gateway = MagicMock()
    gateway.complete = AsyncMock(
        return_value=MagicMock(content="This is a mock LLM response.")
    )
    return gateway


@pytest.fixture
def sample_state():
    """Create a sample orchestrator state."""
    return create_initial_state(
        user_input="Show me my DORA metrics",
        user_id="user_123",
        tenant_id="tenant_456",
        session_id="session_789",
        context={"platform": "github"},
    )


@pytest.fixture
def sample_state_with_results(sample_state):
    """Create a sample state with task results."""
    result = TaskResult(
        success=True,
        output="Metrics fetched successfully",
        data={"deployment_frequency": 5.2},
        agent=AgentNode.METRICS,
        execution_time_ms=150,
    )
    sample_state.add_task_result(result)
    return sample_state


@pytest.fixture
def intent_router():
    """Create an intent router without LLM."""
    return IntentRouter(use_llm=False)


@pytest.fixture
def orchestrator(mock_llm_gateway):
    """Create an orchestrator with mock LLM gateway."""
    return AgentOrchestrator(llm_gateway=mock_llm_gateway)


@pytest.fixture
def orchestrator_no_llm():
    """Create an orchestrator without LLM gateway."""
    return AgentOrchestrator(llm_gateway=None)


# =============================================================================
# State Machine Tests
# =============================================================================


class TestOrchestratorState:
    """Tests for OrchestratorState and state management."""

    def test_create_initial_state(self):
        """Test creating initial orchestrator state."""
        state = create_initial_state(
            user_input="Hello world",
            user_id="user_1",
            tenant_id="tenant_1",
            session_id="session_1",
            context={"key": "value"},
        )

        assert state.current_input == "Hello world"
        assert state.user_id == "user_1"
        assert state.tenant_id == "tenant_1"
        assert state.session_id == "session_1"
        assert state.context == {"key": "value"}
        assert state.status == WorkflowStatus.PENDING
        assert state.current_node == AgentNode.ROUTER
        assert len(state.messages) == 1
        assert state.messages[0]["role"] == "user"
        assert state.messages[0]["content"] == "Hello world"

    def test_state_default_values(self):
        """Test state has proper default values."""
        state = OrchestratorState()

        assert state.workflow_id is not None
        assert state.status == WorkflowStatus.PENDING
        assert state.current_node == AgentNode.ROUTER
        assert state.iteration_count == 0
        assert state.max_iterations == 10
        assert state.messages == []
        assert state.task_results == []
        assert state.errors == []

    def test_add_message(self, sample_state):
        """Test adding messages to state."""
        initial_count = len(sample_state.messages)
        sample_state.add_message("assistant", "Hello from assistant")

        assert len(sample_state.messages) == initial_count + 1
        assert sample_state.messages[-1]["role"] == "assistant"
        assert sample_state.messages[-1]["content"] == "Hello from assistant"

    def test_add_task_result(self, sample_state):
        """Test adding task results."""
        result = TaskResult(
            success=True,
            output="Test output",
            data={"key": "value"},
            agent=AgentNode.QUERY,
            execution_time_ms=100,
        )
        sample_state.add_task_result(result)

        assert len(sample_state.task_results) == 1
        assert sample_state.task_results[0]["success"] is True
        assert sample_state.task_results[0]["output"] == "Test output"
        assert sample_state.task_results[0]["agent"] == "query"

    def test_add_error(self, sample_state):
        """Test adding errors."""
        sample_state.add_error("Something went wrong")

        assert len(sample_state.errors) == 1
        assert sample_state.errors[0] == "Something went wrong"

    def test_should_continue_when_pending(self, sample_state):
        """Test should_continue when status is pending."""
        assert sample_state.should_continue() is True

    def test_should_continue_when_completed(self, sample_state):
        """Test should_continue when status is completed."""
        sample_state.status = WorkflowStatus.COMPLETED
        assert sample_state.should_continue() is False

    def test_should_continue_when_failed(self, sample_state):
        """Test should_continue when status is failed."""
        sample_state.status = WorkflowStatus.FAILED
        assert sample_state.should_continue() is False

    def test_should_continue_when_cancelled(self, sample_state):
        """Test should_continue when status is cancelled."""
        sample_state.status = WorkflowStatus.CANCELLED
        assert sample_state.should_continue() is False

    def test_should_continue_max_iterations(self, sample_state):
        """Test should_continue respects max iterations."""
        sample_state.iteration_count = 10
        sample_state.max_iterations = 10
        assert sample_state.should_continue() is False

    def test_get_conversation_history(self, sample_state):
        """Test getting conversation history."""
        sample_state.add_message("assistant", "Response 1")
        sample_state.add_message("user", "Follow up")

        history = sample_state.get_conversation_history()

        assert len(history) == 3
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"
        assert history[2]["role"] == "user"

    def test_to_langchain_messages(self, sample_state):
        """Test converting to LangChain message format."""
        sample_state.add_message("assistant", "Response")
        sample_state.add_message("system", "System message")

        lc_messages = sample_state.to_langchain_messages()

        assert len(lc_messages) == 3
        # Check message types
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

        assert isinstance(lc_messages[0], HumanMessage)
        assert isinstance(lc_messages[1], AIMessage)
        assert isinstance(lc_messages[2], SystemMessage)


class TestTaskResult:
    """Tests for TaskResult dataclass."""

    def test_task_result_creation(self):
        """Test creating a task result."""
        result = TaskResult(
            success=True,
            output="Test output",
            data={"key": "value"},
            agent=AgentNode.METRICS,
            execution_time_ms=150,
            tool_calls=[{"name": "get_metrics"}],
        )

        assert result.success is True
        assert result.output == "Test output"
        assert result.data == {"key": "value"}
        assert result.agent == AgentNode.METRICS
        assert result.execution_time_ms == 150
        assert len(result.tool_calls) == 1

    def test_task_result_to_dict(self):
        """Test converting task result to dictionary."""
        result = TaskResult(
            success=False,
            output="Error occurred",
            error="Connection failed",
            agent=AgentNode.SETUP,
            execution_time_ms=50,
        )

        result_dict = result.to_dict()

        assert result_dict["success"] is False
        assert result_dict["output"] == "Error occurred"
        assert result_dict["error"] == "Connection failed"
        assert result_dict["agent"] == "setup"
        assert result_dict["execution_time_ms"] == 50

    def test_task_result_defaults(self):
        """Test task result default values."""
        result = TaskResult(success=True, output="Done")

        assert result.data == {}
        assert result.error is None
        assert result.agent is None
        assert result.execution_time_ms == 0
        assert result.tool_calls == []


class TestWorkflowStatus:
    """Tests for WorkflowStatus enum."""

    def test_all_statuses_defined(self):
        """Test all expected statuses are defined."""
        expected_statuses = [
            "pending",
            "routing",
            "executing",
            "waiting_input",
            "completed",
            "failed",
            "cancelled",
        ]

        for status in expected_statuses:
            assert hasattr(WorkflowStatus, status.upper())
            assert WorkflowStatus(status).value == status

    def test_status_values(self):
        """Test status enum values."""
        assert WorkflowStatus.PENDING.value == "pending"
        assert WorkflowStatus.ROUTING.value == "routing"
        assert WorkflowStatus.EXECUTING.value == "executing"
        assert WorkflowStatus.WAITING_INPUT.value == "waiting_input"
        assert WorkflowStatus.COMPLETED.value == "completed"
        assert WorkflowStatus.FAILED.value == "failed"
        assert WorkflowStatus.CANCELLED.value == "cancelled"


class TestAgentNode:
    """Tests for AgentNode enum."""

    def test_all_nodes_defined(self):
        """Test all expected agent nodes are defined."""
        expected_nodes = [
            "router",
            "setup",
            "metrics",
            "query",
            "insights",
            "code_analysis",
            "supervisor",
            "human",
            "end",
        ]

        for node in expected_nodes:
            assert hasattr(AgentNode, node.upper())


# =============================================================================
# Intent Router Tests
# =============================================================================


class TestIntentRouter:
    """Tests for IntentRouter."""

    def test_router_initialization(self, intent_router):
        """Test intent router initialization."""
        assert intent_router.use_llm is False
        assert len(intent_router._compiled_patterns) > 0

    def test_router_initialization_with_llm(self):
        """Test intent router initialization with LLM enabled."""
        router = IntentRouter(use_llm=True)
        assert router.use_llm is True

    @pytest.mark.parametrize(
        "input_text,expected_intent",
        [
            ("set up devlake", TaskIntent.SETUP_DEVLAKE),
            ("configure devlake", TaskIntent.SETUP_DEVLAKE),
            ("install devlake", TaskIntent.SETUP_DEVLAKE),
            ("connect to github", TaskIntent.CONFIGURE_CONNECTION),
            ("add gitlab connection", TaskIntent.CONFIGURE_CONNECTION),
            ("test the connection", TaskIntent.TEST_CONNECTION),
            ("verify connection", TaskIntent.TEST_CONNECTION),
        ],
    )
    def test_classify_setup_intents(self, intent_router, input_text, expected_intent):
        """Test classification of setup-related intents."""
        classification = intent_router.classify(input_text)
        assert classification.intent == expected_intent
        assert classification.target_agent == AgentNode.SETUP

    @pytest.mark.parametrize(
        "input_text,expected_intent",
        [
            ("show my dora metrics", TaskIntent.GET_DORA_METRICS),
            ("get dora metrics", TaskIntent.GET_DORA_METRICS),
            ("deployment frequency", TaskIntent.DEPLOYMENT_FREQUENCY),
            ("how often do we deploy", TaskIntent.DEPLOYMENT_FREQUENCY),
            ("lead time for changes", TaskIntent.LEAD_TIME),
            ("time to production", TaskIntent.LEAD_TIME),
            ("change failure rate", TaskIntent.CHANGE_FAILURE_RATE),
            ("cfr", TaskIntent.CHANGE_FAILURE_RATE),
            ("mttr", TaskIntent.MTTR),
            ("mean time to recover", TaskIntent.MTTR),
        ],
    )
    def test_classify_metrics_intents(self, intent_router, input_text, expected_intent):
        """Test classification of metrics-related intents."""
        classification = intent_router.classify(input_text)
        assert classification.intent == expected_intent
        assert classification.target_agent == AgentNode.METRICS

    @pytest.mark.parametrize(
        "input_text,expected_intent",
        [
            ("list my repositories", TaskIntent.LIST_REPOSITORIES),
            ("show repos", TaskIntent.LIST_REPOSITORIES),
            ("get commits", TaskIntent.GET_COMMITS),
            ("commit history", TaskIntent.GET_COMMITS),
            ("show pull requests", TaskIntent.GET_PULL_REQUESTS),
            ("list prs", TaskIntent.GET_PULL_REQUESTS),
            ("search projects", TaskIntent.SEARCH_PROJECTS),
        ],
    )
    def test_classify_query_intents(self, intent_router, input_text, expected_intent):
        """Test classification of query-related intents."""
        classification = intent_router.classify(input_text)
        assert classification.intent == expected_intent
        assert classification.target_agent == AgentNode.QUERY

    @pytest.mark.parametrize(
        "input_text,expected_intent",
        [
            ("analyze trends", TaskIntent.ANALYZE_TRENDS),
            ("how is the team performing", TaskIntent.ANALYZE_TRENDS),
            ("give recommendations", TaskIntent.GET_RECOMMENDATIONS),
            ("how to improve", TaskIntent.GET_RECOMMENDATIONS),
            ("identify bottlenecks", TaskIntent.IDENTIFY_BOTTLENECKS),
            ("what is slowing us down", TaskIntent.IDENTIFY_BOTTLENECKS),
            ("compare teams", TaskIntent.COMPARE_TEAMS),
        ],
    )
    def test_classify_insights_intents(self, intent_router, input_text, expected_intent):
        """Test classification of insights-related intents."""
        classification = intent_router.classify(input_text)
        assert classification.intent == expected_intent
        assert classification.target_agent == AgentNode.INSIGHTS

    @pytest.mark.parametrize(
        "input_text,expected_intent",
        [
            ("review code", TaskIntent.REVIEW_CODE),
            ("code review", TaskIntent.REVIEW_CODE),
            ("analyze this PR", TaskIntent.ANALYZE_PR),
            ("review pull request", TaskIntent.ANALYZE_PR),
            ("check code quality", TaskIntent.CHECK_QUALITY),
            ("code smell", TaskIntent.CHECK_QUALITY),
        ],
    )
    def test_classify_code_analysis_intents(self, intent_router, input_text, expected_intent):
        """Test classification of code analysis intents."""
        classification = intent_router.classify(input_text)
        assert classification.intent == expected_intent
        assert classification.target_agent == AgentNode.CODE_ANALYSIS

    def test_classify_help_intent(self, intent_router):
        """Test classification of help intent."""
        classification = intent_router.classify("help")
        assert classification.intent == TaskIntent.HELP
        assert classification.target_agent == AgentNode.SUPERVISOR

    def test_classify_unknown_intent(self, intent_router):
        """Test classification of unknown input."""
        classification = intent_router.classify("random gibberish xyz")
        assert classification.intent == TaskIntent.UNKNOWN
        assert classification.target_agent == AgentNode.SUPERVISOR

    def test_classification_confidence(self, intent_router):
        """Test that classification returns confidence scores."""
        classification = intent_router.classify("show my dora metrics")

        assert 0 <= classification.confidence <= 1.0
        assert classification.confidence > 0.8  # High confidence for exact match

    def test_classification_extracts_entities(self, intent_router):
        """Test that classification extracts entities."""
        classification = intent_router.classify(
            "show commits for repository my-project last 7 days"
        )

        assert "extracted_entities" in dir(classification)
        # Should extract time range
        entities = classification.extracted_entities
        if "time_range" in entities:
            assert entities["time_range"]["value"] == "last 7 days"

    def test_extract_repository_entity(self, intent_router):
        """Test extracting repository entity."""
        classification = intent_router.classify("show repo my-org/my-repo")
        entities = classification.extracted_entities

        assert "repository" in entities
        assert entities["repository"] == "my-org/my-repo"

    def test_extract_team_entity(self, intent_router):
        """Test extracting team entity."""
        classification = intent_router.classify("metrics for team backend-team")
        entities = classification.extracted_entities

        assert "team" in entities
        assert "backend-team" in entities["team"]

    def test_extract_platform_entity(self, intent_router):
        """Test extracting platform entity."""
        classification = intent_router.classify("connect to github")
        entities = classification.extracted_entities

        assert "platform" in entities
        assert entities["platform"] == "github"

    def test_route_with_classified_intent(self, intent_router, sample_state):
        """Test routing based on classified intent."""
        sample_state.current_intent = TaskIntent.GET_DORA_METRICS.value

        target = intent_router.route(sample_state)

        assert target == AgentNode.METRICS

    def test_route_with_human_input_required(self, intent_router, sample_state):
        """Test routing when human input is required."""
        sample_state.requires_human_input = True

        target = intent_router.route(sample_state)

        assert target == AgentNode.HUMAN

    def test_route_with_many_errors(self, intent_router, sample_state):
        """Test routing to supervisor when many errors occur."""
        sample_state.current_intent = None
        sample_state.errors = ["Error 1", "Error 2", "Error 3"]

        target = intent_router.route(sample_state)

        assert target == AgentNode.SUPERVISOR

    def test_get_available_intents(self, intent_router):
        """Test getting available intents."""
        intents = intent_router.get_available_intents()

        assert len(intents) > 0
        assert all("intent" in i for i in intents)
        assert all("target_agent" in i for i in intents)


class TestIntentClassification:
    """Tests for IntentClassification dataclass."""

    def test_classification_creation(self):
        """Test creating an intent classification."""
        classification = IntentClassification(
            intent=TaskIntent.GET_DORA_METRICS,
            confidence=0.95,
            target_agent=AgentNode.METRICS,
            extracted_entities={"team": "backend"},
            reasoning="Pattern match",
        )

        assert classification.intent == TaskIntent.GET_DORA_METRICS
        assert classification.confidence == 0.95
        assert classification.target_agent == AgentNode.METRICS
        assert classification.extracted_entities == {"team": "backend"}
        assert classification.reasoning == "Pattern match"


# =============================================================================
# Agent Node Execution Tests
# =============================================================================


class TestBaseAgentNode:
    """Tests for BaseAgentNode."""

    def test_node_initialization(self, mock_llm_gateway):
        """Test base node initialization."""
        node = SupervisorNode(llm_gateway=mock_llm_gateway, tools=[{"name": "tool1"}])

        assert node.llm_gateway == mock_llm_gateway
        assert len(node.tools) == 1

    def test_create_system_prompt(self, mock_llm_gateway, sample_state):
        """Test system prompt creation."""
        node = SupervisorNode(llm_gateway=mock_llm_gateway)
        prompt = node._create_system_prompt(sample_state)

        assert "Supervisor" in prompt
        assert "NexusAI" in prompt
        assert sample_state.user_id in prompt


class TestSupervisorNode:
    """Tests for SupervisorNode."""

    def test_supervisor_node_attributes(self):
        """Test supervisor node has correct attributes."""
        node = SupervisorNode()

        assert node.node_type == AgentNode.SUPERVISOR
        assert node.name == "Supervisor"
        assert "coordinate" in node.description.lower()

    @pytest.mark.asyncio
    async def test_supervisor_execute_without_results(self, mock_llm_gateway, sample_state):
        """Test supervisor execution without prior results."""
        node = SupervisorNode(llm_gateway=mock_llm_gateway)

        result_state = await node.execute(sample_state)

        assert result_state.status == WorkflowStatus.COMPLETED
        assert result_state.current_node == AgentNode.SUPERVISOR
        assert result_state.iteration_count == 1
        assert result_state.final_response is not None
        assert len(result_state.task_results) == 1

    @pytest.mark.asyncio
    async def test_supervisor_execute_with_results(
        self, mock_llm_gateway, sample_state_with_results
    ):
        """Test supervisor execution with prior results."""
        node = SupervisorNode(llm_gateway=mock_llm_gateway)

        result_state = await node.execute(sample_state_with_results)

        assert result_state.status == WorkflowStatus.COMPLETED
        # Should have original result plus supervisor result
        assert len(result_state.task_results) == 2

    @pytest.mark.asyncio
    async def test_supervisor_without_llm(self, sample_state):
        """Test supervisor without LLM gateway."""
        node = SupervisorNode(llm_gateway=None)

        result_state = await node.execute(sample_state)

        assert result_state.status == WorkflowStatus.COMPLETED
        assert "LLM gateway not configured" in result_state.final_response


class TestSetupAgentNode:
    """Tests for SetupAgentNode."""

    def test_setup_node_attributes(self):
        """Test setup node has correct attributes."""
        node = SetupAgentNode()

        assert node.node_type == AgentNode.SETUP
        assert node.name == "Setup Agent"
        assert "devlake" in node.description.lower()

    @pytest.mark.asyncio
    async def test_setup_devlake_intent(self, mock_llm_gateway):
        """Test setup agent handles devlake setup intent."""
        node = SetupAgentNode(llm_gateway=mock_llm_gateway)
        state = create_initial_state("set up devlake")
        state.current_intent = "setup_devlake"

        result_state = await node.execute(state)

        assert result_state.status == WorkflowStatus.COMPLETED
        assert "DevLake" in result_state.final_response
        assert "Configure Data Sources" in result_state.final_response

    @pytest.mark.asyncio
    async def test_configure_connection_intent(self, mock_llm_gateway):
        """Test setup agent handles connection configuration."""
        node = SetupAgentNode(llm_gateway=mock_llm_gateway)
        state = create_initial_state("connect to github")
        state.current_intent = "configure_connection"
        state.context["extracted_entities"] = {"platform": "github"}

        result_state = await node.execute(state)

        assert result_state.status == WorkflowStatus.COMPLETED
        assert "github" in result_state.final_response.lower()
        assert "API Token" in result_state.final_response

    @pytest.mark.asyncio
    async def test_test_connection_intent(self, mock_llm_gateway):
        """Test setup agent handles connection testing."""
        node = SetupAgentNode(llm_gateway=mock_llm_gateway)
        state = create_initial_state("test the connection")
        state.current_intent = "test_connection"

        result_state = await node.execute(state)

        assert result_state.status == WorkflowStatus.COMPLETED
        assert "test" in result_state.final_response.lower()


class TestMetricsAgentNode:
    """Tests for MetricsAgentNode."""

    def test_metrics_node_attributes(self):
        """Test metrics node has correct attributes."""
        node = MetricsAgentNode()

        assert node.node_type == AgentNode.METRICS
        assert node.name == "Metrics Agent"
        assert "dora" in node.description.lower()

    @pytest.mark.asyncio
    async def test_dora_metrics_intent(self, mock_llm_gateway):
        """Test metrics agent handles DORA metrics request."""
        node = MetricsAgentNode(llm_gateway=mock_llm_gateway)
        state = create_initial_state("show my dora metrics")
        state.current_intent = "get_dora_metrics"

        result_state = await node.execute(state)

        assert result_state.status == WorkflowStatus.COMPLETED
        assert "DORA" in result_state.final_response
        assert "Deployment Frequency" in result_state.final_response

    @pytest.mark.asyncio
    async def test_deployment_frequency_intent(self, mock_llm_gateway):
        """Test metrics agent handles deployment frequency request."""
        node = MetricsAgentNode(llm_gateway=mock_llm_gateway)
        state = create_initial_state("deployment frequency")
        state.current_intent = "deployment_frequency"

        result_state = await node.execute(state)

        assert result_state.status == WorkflowStatus.COMPLETED
        assert "Deployment Frequency" in result_state.final_response
        assert "Elite" in result_state.final_response  # Benchmark reference

    @pytest.mark.asyncio
    async def test_lead_time_intent(self, mock_llm_gateway):
        """Test metrics agent handles lead time request."""
        node = MetricsAgentNode(llm_gateway=mock_llm_gateway)
        state = create_initial_state("lead time for changes")
        state.current_intent = "lead_time"

        result_state = await node.execute(state)

        assert result_state.status == WorkflowStatus.COMPLETED
        assert "Lead Time" in result_state.final_response

    @pytest.mark.asyncio
    async def test_cfr_intent(self, mock_llm_gateway):
        """Test metrics agent handles change failure rate request."""
        node = MetricsAgentNode(llm_gateway=mock_llm_gateway)
        state = create_initial_state("change failure rate")
        state.current_intent = "change_failure_rate"

        result_state = await node.execute(state)

        assert result_state.status == WorkflowStatus.COMPLETED
        assert "Change Failure Rate" in result_state.final_response

    @pytest.mark.asyncio
    async def test_mttr_intent(self, mock_llm_gateway):
        """Test metrics agent handles MTTR request."""
        node = MetricsAgentNode(llm_gateway=mock_llm_gateway)
        state = create_initial_state("mttr")
        state.current_intent = "mttr"

        result_state = await node.execute(state)

        assert result_state.status == WorkflowStatus.COMPLETED
        assert "Mean Time to Recovery" in result_state.final_response


class TestQueryAgentNode:
    """Tests for QueryAgentNode."""

    def test_query_node_attributes(self):
        """Test query node has correct attributes."""
        node = QueryAgentNode()

        assert node.node_type == AgentNode.QUERY
        assert node.name == "Query Agent"
        assert "queries" in node.description.lower() or "retrieves" in node.description.lower()

    @pytest.mark.asyncio
    async def test_list_repositories_intent(self, mock_llm_gateway):
        """Test query agent handles list repositories request."""
        node = QueryAgentNode(llm_gateway=mock_llm_gateway)
        state = create_initial_state("list repositories")
        state.current_intent = "list_repositories"

        result_state = await node.execute(state)

        assert result_state.status == WorkflowStatus.COMPLETED
        assert "Repositories" in result_state.final_response

    @pytest.mark.asyncio
    async def test_get_commits_intent(self, mock_llm_gateway):
        """Test query agent handles get commits request."""
        node = QueryAgentNode(llm_gateway=mock_llm_gateway)
        state = create_initial_state("show commits last 7 days")
        state.current_intent = "get_commits"
        state.context["extracted_entities"] = {"time_range": {"value": "last 7 days"}}

        result_state = await node.execute(state)

        assert result_state.status == WorkflowStatus.COMPLETED
        assert "Commits" in result_state.final_response
        assert "last 7 days" in result_state.final_response

    @pytest.mark.asyncio
    async def test_get_pull_requests_intent(self, mock_llm_gateway):
        """Test query agent handles get PRs request."""
        node = QueryAgentNode(llm_gateway=mock_llm_gateway)
        state = create_initial_state("show pull requests")
        state.current_intent = "get_pull_requests"

        result_state = await node.execute(state)

        assert result_state.status == WorkflowStatus.COMPLETED
        assert "Pull Requests" in result_state.final_response


class TestInsightsAgentNode:
    """Tests for InsightsAgentNode."""

    def test_insights_node_attributes(self):
        """Test insights node has correct attributes."""
        node = InsightsAgentNode()

        assert node.node_type == AgentNode.INSIGHTS
        assert node.name == "Insights Agent"
        assert "insights" in node.description.lower()

    @pytest.mark.asyncio
    async def test_analyze_trends_intent(self, mock_llm_gateway):
        """Test insights agent handles trend analysis request."""
        node = InsightsAgentNode(llm_gateway=mock_llm_gateway)
        state = create_initial_state("analyze trends")
        state.current_intent = "analyze_trends"

        result_state = await node.execute(state)

        assert result_state.status == WorkflowStatus.COMPLETED
        assert "Trend" in result_state.final_response

    @pytest.mark.asyncio
    async def test_get_recommendations_intent(self, mock_llm_gateway):
        """Test insights agent handles recommendations request."""
        node = InsightsAgentNode(llm_gateway=mock_llm_gateway)
        state = create_initial_state("give recommendations")
        state.current_intent = "get_recommendations"

        result_state = await node.execute(state)

        assert result_state.status == WorkflowStatus.COMPLETED
        assert "Recommendations" in result_state.final_response
        assert "Quick Wins" in result_state.final_response

    @pytest.mark.asyncio
    async def test_identify_bottlenecks_intent(self, mock_llm_gateway):
        """Test insights agent handles bottleneck identification."""
        node = InsightsAgentNode(llm_gateway=mock_llm_gateway)
        state = create_initial_state("identify bottlenecks")
        state.current_intent = "identify_bottlenecks"

        result_state = await node.execute(state)

        assert result_state.status == WorkflowStatus.COMPLETED
        assert "Bottleneck" in result_state.final_response


class TestCodeAnalysisNode:
    """Tests for CodeAnalysisNode."""

    def test_code_analysis_node_attributes(self):
        """Test code analysis node has correct attributes."""
        node = CodeAnalysisNode()

        assert node.node_type == AgentNode.CODE_ANALYSIS
        assert node.name == "Code Analysis Agent"
        assert "code" in node.description.lower()

    @pytest.mark.asyncio
    async def test_code_analysis_execute(self, mock_llm_gateway):
        """Test code analysis agent execution."""
        node = CodeAnalysisNode(llm_gateway=mock_llm_gateway)
        state = create_initial_state("review this code")
        state.current_intent = "review_code"

        result_state = await node.execute(state)

        assert result_state.status == WorkflowStatus.COMPLETED
        assert "Code Analysis" in result_state.final_response
        assert "PR Review" in result_state.final_response


class TestHumanInputNode:
    """Tests for HumanInputNode."""

    def test_human_input_node_attributes(self):
        """Test human input node has correct attributes."""
        node = HumanInputNode()

        assert node.node_type == AgentNode.HUMAN
        assert node.name == "Human Input"

    @pytest.mark.asyncio
    async def test_human_input_execute_default_prompt(self, mock_llm_gateway):
        """Test human input node with default prompt."""
        node = HumanInputNode(llm_gateway=mock_llm_gateway)
        state = create_initial_state("test")

        result_state = await node.execute(state)

        assert result_state.status == WorkflowStatus.WAITING_INPUT
        assert result_state.current_node == AgentNode.HUMAN
        assert "Please provide additional information" in result_state.final_response

    @pytest.mark.asyncio
    async def test_human_input_execute_with_custom_prompt(self, mock_llm_gateway):
        """Test human input node with custom prompt."""
        node = HumanInputNode(llm_gateway=mock_llm_gateway)
        state = create_initial_state("test")
        state.human_input_prompt = "Which project would you like to analyze?"

        result_state = await node.execute(state)

        assert result_state.status == WorkflowStatus.WAITING_INPUT
        assert "Which project" in result_state.final_response

    @pytest.mark.asyncio
    async def test_human_input_execute_with_options(self, mock_llm_gateway):
        """Test human input node with options."""
        node = HumanInputNode(llm_gateway=mock_llm_gateway)
        state = create_initial_state("test")
        state.human_input_prompt = "Select a repository:"
        state.human_input_options = ["repo-a", "repo-b", "repo-c"]

        result_state = await node.execute(state)

        assert result_state.status == WorkflowStatus.WAITING_INPUT
        assert "repo-a" in result_state.final_response
        assert "repo-b" in result_state.final_response
        assert "Options:" in result_state.final_response


class TestGetAgentNode:
    """Tests for get_agent_node factory function."""

    def test_get_supervisor_node(self, mock_llm_gateway):
        """Test getting supervisor node."""
        node = get_agent_node(AgentNode.SUPERVISOR, mock_llm_gateway)
        assert isinstance(node, SupervisorNode)

    def test_get_setup_node(self, mock_llm_gateway):
        """Test getting setup node."""
        node = get_agent_node(AgentNode.SETUP, mock_llm_gateway)
        assert isinstance(node, SetupAgentNode)

    def test_get_metrics_node(self, mock_llm_gateway):
        """Test getting metrics node."""
        node = get_agent_node(AgentNode.METRICS, mock_llm_gateway)
        assert isinstance(node, MetricsAgentNode)

    def test_get_query_node(self, mock_llm_gateway):
        """Test getting query node."""
        node = get_agent_node(AgentNode.QUERY, mock_llm_gateway)
        assert isinstance(node, QueryAgentNode)

    def test_get_insights_node(self, mock_llm_gateway):
        """Test getting insights node."""
        node = get_agent_node(AgentNode.INSIGHTS, mock_llm_gateway)
        assert isinstance(node, InsightsAgentNode)

    def test_get_code_analysis_node(self, mock_llm_gateway):
        """Test getting code analysis node."""
        node = get_agent_node(AgentNode.CODE_ANALYSIS, mock_llm_gateway)
        assert isinstance(node, CodeAnalysisNode)

    def test_get_human_node(self, mock_llm_gateway):
        """Test getting human input node."""
        node = get_agent_node(AgentNode.HUMAN, mock_llm_gateway)
        assert isinstance(node, HumanInputNode)

    def test_get_unknown_node_defaults_to_supervisor(self, mock_llm_gateway):
        """Test that unknown node type defaults to supervisor."""
        # Using an invalid node type should default to supervisor
        node = get_agent_node(AgentNode.ROUTER, mock_llm_gateway)
        assert isinstance(node, SupervisorNode)


# =============================================================================
# Human-in-the-Loop Workflow Tests
# =============================================================================


class TestHumanInTheLoopWorkflow:
    """Tests for human-in-the-loop workflow functionality."""

    def test_state_requires_human_input_flag(self, sample_state):
        """Test requires_human_input flag."""
        assert sample_state.requires_human_input is False

        sample_state.requires_human_input = True
        assert sample_state.requires_human_input is True

    def test_state_human_input_prompt(self, sample_state):
        """Test human input prompt."""
        sample_state.human_input_prompt = "Please select an option"
        assert sample_state.human_input_prompt == "Please select an option"

    def test_state_human_input_options(self, sample_state):
        """Test human input options."""
        sample_state.human_input_options = ["Option A", "Option B"]
        assert len(sample_state.human_input_options) == 2

    @pytest.mark.asyncio
    async def test_workflow_pauses_for_human_input(self, orchestrator_no_llm):
        """Test that workflow pauses when human input is required."""
        state = create_initial_state("test input")
        state.requires_human_input = True
        state.human_input_prompt = "Please confirm"

        # The human node should set status to waiting
        human_node = orchestrator_no_llm.nodes[AgentNode.HUMAN]
        result = await human_node.execute(state)

        assert result.status == WorkflowStatus.WAITING_INPUT

    def test_should_continue_respects_human_input(self, orchestrator_no_llm, sample_state):
        """Test _should_continue respects waiting_input status."""
        sample_state.status = WorkflowStatus.WAITING_INPUT

        result = orchestrator_no_llm._should_continue(sample_state)

        assert result == "human"

    def test_should_continue_requires_human_input_flag(self, orchestrator_no_llm, sample_state):
        """Test _should_continue respects requires_human_input flag."""
        sample_state.requires_human_input = True
        sample_state.status = WorkflowStatus.EXECUTING

        result = orchestrator_no_llm._should_continue(sample_state)

        assert result == "human"

    def test_after_human_input_continues(self, orchestrator_no_llm, sample_state):
        """Test _after_human_input continues when input provided."""
        sample_state.requires_human_input = False

        result = orchestrator_no_llm._after_human_input(sample_state)

        assert result == "continue"

    def test_after_human_input_ends_when_still_waiting(self, orchestrator_no_llm, sample_state):
        """Test _after_human_input ends when still waiting."""
        sample_state.requires_human_input = True

        result = orchestrator_no_llm._after_human_input(sample_state)

        assert result == "end"


# =============================================================================
# Conversation State Management Tests
# =============================================================================


class TestConversationStateManagement:
    """Tests for conversation state management."""

    def test_message_accumulation(self, sample_state):
        """Test messages accumulate correctly."""
        sample_state.add_message("assistant", "Response 1")
        sample_state.add_message("user", "Follow up 1")
        sample_state.add_message("assistant", "Response 2")

        assert len(sample_state.messages) == 4  # Initial + 3 new
        assert sample_state.messages[1]["content"] == "Response 1"
        assert sample_state.messages[2]["content"] == "Follow up 1"

    def test_message_metadata(self, sample_state):
        """Test messages can include metadata."""
        sample_state.add_message(
            "assistant",
            "Response with metadata",
            metadata={"confidence": 0.95},
        )

        last_message = sample_state.messages[-1]
        assert last_message["metadata"]["confidence"] == 0.95

    def test_context_preservation(self, sample_state):
        """Test context is preserved across state changes."""
        sample_state.context["new_key"] = "new_value"
        sample_state.status = WorkflowStatus.EXECUTING

        assert sample_state.context["platform"] == "github"
        assert sample_state.context["new_key"] == "new_value"

    def test_devlake_config_storage(self, sample_state):
        """Test DevLake config can be stored in state."""
        sample_state.devlake_config = {
            "endpoint": "http://localhost:8080",
            "api_key": "test_key",
        }

        assert sample_state.devlake_config["endpoint"] == "http://localhost:8080"

    def test_available_metrics_storage(self, sample_state):
        """Test available metrics can be stored."""
        sample_state.available_metrics = [
            "deployment_frequency",
            "lead_time",
            "cfr",
            "mttr",
        ]

        assert len(sample_state.available_metrics) == 4
        assert "deployment_frequency" in sample_state.available_metrics

    def test_retrieved_documents_storage(self, sample_state):
        """Test retrieved documents can be stored."""
        sample_state.retrieved_documents = [
            {"id": "doc1", "content": "Document 1"},
            {"id": "doc2", "content": "Document 2"},
        ]

        assert len(sample_state.retrieved_documents) == 2

    def test_memory_context_storage(self, sample_state):
        """Test memory context can be stored."""
        sample_state.memory_context = {
            "previous_queries": ["query1", "query2"],
            "user_preferences": {"theme": "dark"},
        }

        assert len(sample_state.memory_context["previous_queries"]) == 2


# =============================================================================
# Error Handling and Recovery Tests
# =============================================================================


class TestErrorHandlingAndRecovery:
    """Tests for error handling and recovery."""

    def test_add_error_to_state(self, sample_state):
        """Test adding errors to state."""
        sample_state.add_error("Error 1")
        sample_state.add_error("Error 2")

        assert len(sample_state.errors) == 2
        assert sample_state.errors[0] == "Error 1"

    def test_should_continue_ends_on_failure(self, orchestrator_no_llm, sample_state):
        """Test workflow ends on failure status."""
        sample_state.status = WorkflowStatus.FAILED

        result = orchestrator_no_llm._should_continue(sample_state)

        assert result == "end"

    def test_max_iterations_stops_workflow(self, orchestrator_no_llm, sample_state):
        """Test workflow stops at max iterations."""
        sample_state.iteration_count = 10
        sample_state.max_iterations = 10

        result = orchestrator_no_llm._should_continue(sample_state)

        assert result == "end"

    @pytest.mark.asyncio
    async def test_orchestrator_handles_exception(self, orchestrator_no_llm):
        """Test orchestrator handles exceptions gracefully."""
        # Replace compiled_graph with a mock that raises an exception
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(side_effect=Exception("Test error"))
        orchestrator_no_llm.compiled_graph = mock_graph

        result = await orchestrator_no_llm.run(
            user_input="test",
            user_id="user_1",
        )

        assert result.status == WorkflowStatus.FAILED
        assert len(result.errors) > 0
        assert "Test error" in result.errors[0]
        assert result.final_response is not None

    @pytest.mark.asyncio
    async def test_llm_call_failure_handling(self, sample_state):
        """Test handling of LLM call failures."""
        mock_gateway = MagicMock()
        mock_gateway.complete = AsyncMock(side_effect=Exception("LLM error"))

        node = SupervisorNode(llm_gateway=mock_gateway)
        result = await node._call_llm(sample_state)

        assert "Error calling LLM" in result

    def test_decide_next_node_ends_when_should_not_continue(self, orchestrator_no_llm, sample_state):
        """Test _decide_next_node returns end when should_continue is false."""
        sample_state.status = WorkflowStatus.COMPLETED

        result = orchestrator_no_llm._decide_next_node(sample_state)

        assert result == "end"

    def test_task_result_with_error(self):
        """Test task result with error information."""
        result = TaskResult(
            success=False,
            output="Operation failed",
            error="Connection timeout",
            agent=AgentNode.SETUP,
        )

        assert result.success is False
        assert result.error == "Connection timeout"

        result_dict = result.to_dict()
        assert result_dict["error"] == "Connection timeout"


# =============================================================================
# Orchestrator Tests
# =============================================================================


class TestAgentOrchestrator:
    """Tests for AgentOrchestrator."""

    def test_orchestrator_initialization(self, orchestrator):
        """Test orchestrator initialization."""
        assert orchestrator.llm_gateway is not None
        assert orchestrator.intent_router is not None
        assert orchestrator.checkpointer is not None
        assert orchestrator.graph is not None
        assert orchestrator.compiled_graph is not None

    def test_orchestrator_initialization_without_llm(self, orchestrator_no_llm):
        """Test orchestrator initialization without LLM."""
        assert orchestrator_no_llm.llm_gateway is None
        assert orchestrator_no_llm.intent_router.use_llm is False

    def test_orchestrator_nodes_initialized(self, orchestrator):
        """Test all agent nodes are initialized."""
        expected_nodes = [
            AgentNode.SUPERVISOR,
            AgentNode.SETUP,
            AgentNode.METRICS,
            AgentNode.QUERY,
            AgentNode.INSIGHTS,
            AgentNode.CODE_ANALYSIS,
            AgentNode.HUMAN,
        ]

        for node_type in expected_nodes:
            assert node_type in orchestrator.nodes

    def test_get_available_agents(self, orchestrator):
        """Test getting available agents information."""
        agents = orchestrator.get_available_agents()

        assert len(agents) > 0
        for agent in agents:
            assert "type" in agent
            assert "name" in agent
            assert "description" in agent

    def test_decide_next_node_routes_to_human(self, orchestrator, sample_state):
        """Test _decide_next_node routes to human when required."""
        sample_state.requires_human_input = True

        result = orchestrator._decide_next_node(sample_state)

        assert result == "human"

    def test_decide_next_node_routes_based_on_intent(self, orchestrator, sample_state):
        """Test _decide_next_node routes based on classified intent."""
        sample_state.current_intent = TaskIntent.GET_DORA_METRICS.value

        # Mock intent_router.route to return the expected node
        with patch.object(
            orchestrator.intent_router,
            "route",
            return_value=AgentNode.METRICS,
        ):
            result = orchestrator._decide_next_node(sample_state)

        assert result == "metrics"

    def test_should_continue_returns_end_on_completion(self, orchestrator, sample_state):
        """Test _should_continue returns end on completion."""
        sample_state.status = WorkflowStatus.COMPLETED

        result = orchestrator._should_continue(sample_state)

        assert result == "end"

    def test_should_continue_returns_end_with_final_response(self, orchestrator, sample_state):
        """Test _should_continue returns end when final response exists."""
        sample_state.final_response = "Final answer"
        sample_state.pending_tool_calls = []
        sample_state.status = WorkflowStatus.EXECUTING

        result = orchestrator._should_continue(sample_state)

        assert result == "end"

    def test_should_continue_returns_continue(self, orchestrator, sample_state):
        """Test _should_continue returns continue when workflow should proceed."""
        sample_state.status = WorkflowStatus.EXECUTING
        sample_state.final_response = None
        sample_state.iteration_count = 1

        result = orchestrator._should_continue(sample_state)

        assert result == "continue"

    @pytest.mark.asyncio
    async def test_orchestrator_run_basic(self, orchestrator_no_llm):
        """Test basic orchestrator run."""
        # Mock the compiled_graph.ainvoke to return a state
        mock_state = create_initial_state("test input", user_id="user_1")
        mock_state.status = WorkflowStatus.COMPLETED
        mock_state.final_response = "Test response"

        # Create a mock graph and replace the compiled_graph
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(return_value=mock_state)
        orchestrator_no_llm.compiled_graph = mock_graph

        result = await orchestrator_no_llm.run(
            user_input="test input",
            user_id="user_1",
            tenant_id="tenant_1",
        )

        assert result.status == WorkflowStatus.COMPLETED
        assert result.final_response == "Test response"

    @pytest.mark.asyncio
    async def test_orchestrator_run_with_thread_id(self, orchestrator_no_llm):
        """Test orchestrator run with explicit thread ID."""
        mock_state = create_initial_state("test")
        mock_state.status = WorkflowStatus.COMPLETED

        # Create a mock graph and replace the compiled_graph
        mock_graph = MagicMock()
        mock_invoke = AsyncMock(return_value=mock_state)
        mock_graph.ainvoke = mock_invoke
        orchestrator_no_llm.compiled_graph = mock_graph

        await orchestrator_no_llm.run(
            user_input="test",
            thread_id="custom-thread-123",
        )

        # Verify thread_id was passed in config
        call_args = mock_invoke.call_args
        assert call_args[1]["config"]["configurable"]["thread_id"] == "custom-thread-123"

    @pytest.mark.asyncio
    async def test_orchestrator_get_state(self, orchestrator_no_llm):
        """Test getting orchestrator state by thread ID."""
        mock_state_dict = {
            "workflow_id": "test-workflow",
            "status": WorkflowStatus.COMPLETED,
            "current_node": AgentNode.ROUTER,
            "messages": [],
            "current_input": "test",
        }

        mock_snapshot = MagicMock()
        mock_snapshot.values = mock_state_dict

        # Create a mock graph and replace the compiled_graph
        mock_graph = MagicMock()
        mock_graph.aget_state = AsyncMock(return_value=mock_snapshot)
        orchestrator_no_llm.compiled_graph = mock_graph

        state = await orchestrator_no_llm.get_state("test-thread")

        # get_state may return either OrchestratorState or dict depending on implementation
        if hasattr(state, 'workflow_id'):
            assert state.workflow_id == "test-workflow"
            assert state.status == WorkflowStatus.COMPLETED
        else:
            assert state["workflow_id"] == "test-workflow"
            assert state["status"] == WorkflowStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_orchestrator_get_state_not_found_placeholder(self, orchestrator_no_llm):
        """Test getting orchestrator state when not found."""
        mock_snapshot = MagicMock()
        mock_snapshot.values = None

        # Create a mock graph and replace the compiled_graph
        mock_graph = MagicMock()
        mock_graph.aget_state = AsyncMock(return_value=mock_snapshot)
        orchestrator_no_llm.compiled_graph = mock_graph

        state = await orchestrator_no_llm.get_state("nonexistent-thread")

        assert state is None


class TestAgentOrchestratorContinued:
    """Continuation of AgentOrchestrator tests."""

    @pytest.fixture
    def orchestrator_no_llm(self):
        """Create an orchestrator without LLM gateway."""
        return AgentOrchestrator(llm_gateway=None)

    @pytest.mark.asyncio
    async def test_orchestrator_resume(self, orchestrator_no_llm):
        """Test resuming a paused workflow."""
        # Create a waiting state
        waiting_state = create_initial_state("original input")
        waiting_state.status = WorkflowStatus.WAITING_INPUT
        waiting_state.requires_human_input = True

        mock_snapshot = MagicMock()
        mock_snapshot.values = waiting_state.model_dump()

        # Create completed state after resume
        completed_state = create_initial_state("original input")
        completed_state.status = WorkflowStatus.COMPLETED
        completed_state.final_response = "Resumed and completed"

        # Create a mock graph and replace the compiled_graph
        mock_graph = MagicMock()
        mock_graph.aget_state = AsyncMock(return_value=mock_snapshot)
        mock_graph.ainvoke = AsyncMock(return_value=completed_state)
        orchestrator_no_llm.compiled_graph = mock_graph

        result = await orchestrator_no_llm.resume(
            thread_id="test-thread",
            human_input="user's response",
        )

        assert result.status == WorkflowStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_orchestrator_resume_no_workflow(self, orchestrator_no_llm):
        """Test resuming when no workflow exists."""
        mock_snapshot = MagicMock()
        mock_snapshot.values = None

        # Create a mock graph and replace the compiled_graph
        mock_graph = MagicMock()
        mock_graph.aget_state = AsyncMock(return_value=mock_snapshot)
        orchestrator_no_llm.compiled_graph = mock_graph

        with pytest.raises(ValueError, match="No workflow found"):
            await orchestrator_no_llm.resume(
                thread_id="nonexistent-thread",
                human_input="test",
            )


class TestOrchestratorFactory:
    """Tests for orchestrator factory functions."""

    def test_get_orchestrator_creates_instance(self):
        """Test get_orchestrator creates global instance."""
        # Clear any existing instance
        import app.services.agents.orchestrator.orchestrator as orch_module

        orch_module._orchestrator = None

        orchestrator = get_orchestrator()

        assert orchestrator is not None
        assert isinstance(orchestrator, AgentOrchestrator)

    def test_get_orchestrator_returns_same_instance(self):
        """Test get_orchestrator returns same instance."""
        orch1 = get_orchestrator()
        orch2 = get_orchestrator()

        assert orch1 is orch2

    @pytest.mark.asyncio
    async def test_create_orchestrator_new_instance(self, mock_llm_gateway):
        """Test create_orchestrator creates new instance."""
        orch = await create_orchestrator(llm_gateway=mock_llm_gateway)

        assert orch is not None
        assert orch.llm_gateway == mock_llm_gateway


# =============================================================================
# Routing Decision Tests
# =============================================================================


class TestRoutingDecisions:
    """Tests for routing decision logic."""

    @pytest.mark.parametrize(
        "intent,expected_node",
        [
            (TaskIntent.SETUP_DEVLAKE, AgentNode.SETUP),
            (TaskIntent.CONFIGURE_CONNECTION, AgentNode.SETUP),
            (TaskIntent.TEST_CONNECTION, AgentNode.SETUP),
            (TaskIntent.GET_DORA_METRICS, AgentNode.METRICS),
            (TaskIntent.DEPLOYMENT_FREQUENCY, AgentNode.METRICS),
            (TaskIntent.LEAD_TIME, AgentNode.METRICS),
            (TaskIntent.CHANGE_FAILURE_RATE, AgentNode.METRICS),
            (TaskIntent.MTTR, AgentNode.METRICS),
            (TaskIntent.QUERY_DATA, AgentNode.QUERY),
            (TaskIntent.LIST_REPOSITORIES, AgentNode.QUERY),
            (TaskIntent.GET_COMMITS, AgentNode.QUERY),
            (TaskIntent.GET_PULL_REQUESTS, AgentNode.QUERY),
            (TaskIntent.ANALYZE_TRENDS, AgentNode.INSIGHTS),
            (TaskIntent.GET_RECOMMENDATIONS, AgentNode.INSIGHTS),
            (TaskIntent.IDENTIFY_BOTTLENECKS, AgentNode.INSIGHTS),
            (TaskIntent.REVIEW_CODE, AgentNode.CODE_ANALYSIS),
            (TaskIntent.ANALYZE_PR, AgentNode.CODE_ANALYSIS),
            (TaskIntent.CHECK_QUALITY, AgentNode.CODE_ANALYSIS),
            (TaskIntent.HELP, AgentNode.SUPERVISOR),
            (TaskIntent.UNKNOWN, AgentNode.SUPERVISOR),
        ],
    )
    def test_intent_agent_mapping(self, intent, expected_node):
        """Test that intents map to correct agents."""
        assert INTENT_AGENT_MAP[intent] == expected_node


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_user_input(self, intent_router):
        """Test handling empty user input."""
        classification = intent_router.classify("")

        assert classification.intent == TaskIntent.UNKNOWN
        assert classification.confidence < 0.5

    def test_very_long_input(self, intent_router):
        """Test handling very long input."""
        long_input = "show my dora metrics " * 100
        classification = intent_router.classify(long_input)

        # Should still classify correctly
        assert classification.intent == TaskIntent.GET_DORA_METRICS

    def test_special_characters_in_input(self, intent_router):
        """Test handling special characters in input."""
        classification = intent_router.classify("show me metrics for repo @#$%^&*()")

        # Should handle gracefully
        assert classification is not None

    def test_case_insensitive_classification(self, intent_router):
        """Test classification is case insensitive."""
        lower = intent_router.classify("show my dora metrics")
        upper = intent_router.classify("SHOW MY DORA METRICS")
        mixed = intent_router.classify("ShOw My DoRa MeTrIcS")

        assert lower.intent == upper.intent == mixed.intent

    def test_state_with_none_values(self):
        """Test state handles None values correctly."""
        state = OrchestratorState(
            user_id=None,
            tenant_id=None,
            session_id=None,
        )

        assert state.user_id is None
        assert state.should_continue() is True

    def test_iteration_boundary(self, sample_state):
        """Test iteration count boundary conditions."""
        sample_state.iteration_count = 9
        sample_state.max_iterations = 10
        assert sample_state.should_continue() is True

        sample_state.iteration_count = 10
        assert sample_state.should_continue() is False

    def test_concurrent_state_modifications(self, sample_state):
        """Test state can be modified concurrently."""
        # Add multiple items
        for i in range(10):
            sample_state.add_message("user", f"Message {i}")
            sample_state.add_error(f"Error {i}")

        assert len(sample_state.messages) == 11  # Initial + 10
        assert len(sample_state.errors) == 10


# =============================================================================
# Integration-like Tests (with mocks)
# =============================================================================


class TestOrchestratorIntegration:
    """Integration-like tests for orchestrator with mocked components."""

    @pytest.mark.asyncio
    async def test_full_workflow_metrics_request(self, mock_llm_gateway):
        """Test full workflow for a metrics request."""
        orchestrator = AgentOrchestrator(llm_gateway=mock_llm_gateway)

        # Mock the compiled graph to simulate full workflow
        final_state = create_initial_state("show my dora metrics")
        final_state.status = WorkflowStatus.COMPLETED
        final_state.current_intent = TaskIntent.GET_DORA_METRICS.value
        final_state.final_response = "Here are your DORA metrics..."
        final_state.add_task_result(
            TaskResult(
                success=True,
                output="Metrics retrieved",
                agent=AgentNode.METRICS,
            )
        )

        # Replace compiled_graph with a mock that returns the final state as dict
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(return_value=final_state.model_dump())
        orchestrator.compiled_graph = mock_graph

        result = await orchestrator.run(
            user_input="show my dora metrics",
            user_id="user_123",
            tenant_id="tenant_456",
        )

        assert result.status == WorkflowStatus.COMPLETED
        assert result.current_intent == TaskIntent.GET_DORA_METRICS.value
        assert len(result.task_results) > 0

    @pytest.mark.asyncio
    async def test_workflow_with_human_interaction(self, mock_llm_gateway):
        """Test workflow that requires human interaction."""
        orchestrator = AgentOrchestrator(llm_gateway=mock_llm_gateway)

        # First run pauses for human input
        paused_state = create_initial_state("configure github")
        paused_state.status = WorkflowStatus.WAITING_INPUT
        paused_state.requires_human_input = True
        paused_state.human_input_prompt = "Please provide your API token"

        # Replace compiled_graph with a mock
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(return_value=paused_state.model_dump())
        orchestrator.compiled_graph = mock_graph

        result = await orchestrator.run(
            user_input="configure github",
            thread_id="test-thread",
        )

        assert result.status == WorkflowStatus.WAITING_INPUT
        assert result.requires_human_input is True

        # Resume with human input
        resumed_state = create_initial_state("configure github")
        resumed_state.status = WorkflowStatus.COMPLETED
        resumed_state.final_response = "GitHub configured successfully"

        mock_graph.aget_state = AsyncMock(return_value=MagicMock(values=paused_state.model_dump()))
        mock_graph.ainvoke = AsyncMock(return_value=resumed_state.model_dump())

        result = await orchestrator.resume(
            thread_id="test-thread",
            human_input="my-api-token",
        )

        assert result.status == WorkflowStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, mock_llm_gateway):
        """Test workflow error recovery."""
        orchestrator = AgentOrchestrator(llm_gateway=mock_llm_gateway)

        # Replace compiled_graph with a mock that raises an exception
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(side_effect=Exception("Connection failed"))
        orchestrator.compiled_graph = mock_graph

        result = await orchestrator.run(
            user_input="test",
            user_id="user_123",
        )

        assert result.status == WorkflowStatus.FAILED
        assert len(result.errors) > 0


# =============================================================================
# Pattern Matching Tests
# =============================================================================


class TestPatternMatching:
    """Tests for intent pattern matching."""

    def test_all_patterns_compile(self):
        """Test all intent patterns compile correctly."""
        for intent, patterns in INTENT_PATTERNS.items():
            for pattern, confidence in patterns:
                import re

                try:
                    re.compile(pattern, re.IGNORECASE)
                except re.error as e:
                    pytest.fail(f"Pattern '{pattern}' for {intent} failed to compile: {e}")

    def test_pattern_confidence_ranges(self):
        """Test all pattern confidences are in valid range."""
        for intent, patterns in INTENT_PATTERNS.items():
            for pattern, confidence in patterns:
                assert 0 < confidence <= 1.0, (
                    f"Invalid confidence {confidence} for pattern '{pattern}'"
                )

    def test_no_overlapping_high_confidence_patterns(self, intent_router):
        """Test similar inputs don't have conflicting high-confidence matches."""
        # These should each match their specific intent clearly
        test_cases = [
            ("deployment frequency", TaskIntent.DEPLOYMENT_FREQUENCY),
            ("lead time", TaskIntent.LEAD_TIME),
            ("change failure rate", TaskIntent.CHANGE_FAILURE_RATE),
            ("mttr", TaskIntent.MTTR),
        ]

        for input_text, expected_intent in test_cases:
            classification = intent_router.classify(input_text)
            assert classification.intent == expected_intent, (
                f"Expected {expected_intent} for '{input_text}', "
                f"got {classification.intent}"
            )
