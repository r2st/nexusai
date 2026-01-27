"""Agent nodes for the orchestrator workflow."""

import time
from abc import ABC, abstractmethod
from typing import Any

import structlog

from app.services.agents.orchestrator.state import (
    AgentNode,
    OrchestratorState,
    TaskResult,
    WorkflowStatus,
)

logger = structlog.get_logger()


class BaseAgentNode(ABC):
    """Base class for agent nodes in the workflow."""

    node_type: AgentNode = AgentNode.SUPERVISOR
    name: str = "base"
    description: str = "Base agent node"

    def __init__(self, llm_gateway=None, tools: list | None = None):
        """
        Initialize the agent node.

        Args:
            llm_gateway: LLM gateway for model calls
            tools: Available tools for this agent
        """
        self.llm_gateway = llm_gateway
        self.tools = tools or []

    @abstractmethod
    async def execute(self, state: OrchestratorState) -> OrchestratorState:
        """
        Execute the agent logic.

        Args:
            state: Current orchestrator state

        Returns:
            Updated state
        """
        pass

    def _create_system_prompt(self, state: OrchestratorState) -> str:
        """Create the system prompt for this agent."""
        return f"""You are the {self.name} agent for NexusAI, an engineering intelligence platform.

Your role: {self.description}

Available context:
- User ID: {state.user_id}
- Session ID: {state.session_id}
- Current intent: {state.current_intent}

Be helpful, concise, and accurate. If you need more information, ask clarifying questions.
"""

    async def _call_llm(
        self,
        state: OrchestratorState,
        user_message: str | None = None,
        system_prompt: str | None = None,
    ) -> str:
        """Call the LLM with the current context."""
        if not self.llm_gateway:
            return "LLM gateway not configured"

        messages = []

        # Add system prompt
        prompt = system_prompt or self._create_system_prompt(state)
        messages.append({"role": "system", "content": prompt})

        # Add conversation history
        for msg in state.messages[-10:]:  # Last 10 messages
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
            })

        # Add current message if provided
        if user_message:
            messages.append({"role": "user", "content": user_message})

        try:
            response = await self.llm_gateway.complete(
                messages=messages,
                model="gpt-4o-mini",  # Use fast model for agents
                temperature=0.7,
            )
            return response.content
        except Exception as e:
            logger.error("LLM call failed", error=str(e), agent=self.name)
            return f"Error calling LLM: {str(e)}"


class SupervisorNode(BaseAgentNode):
    """Supervisor agent that coordinates other agents."""

    node_type = AgentNode.SUPERVISOR
    name = "Supervisor"
    description = "Coordinates agent workflow and handles complex queries"

    async def execute(self, state: OrchestratorState) -> OrchestratorState:
        """Execute supervisor logic."""
        start_time = time.time()

        state.status = WorkflowStatus.EXECUTING
        state.current_node = self.node_type
        state.iteration_count += 1

        # Generate response based on context
        if state.task_results:
            # Summarize results from other agents
            response = await self._summarize_results(state)
        else:
            # Handle as general question
            response = await self._handle_general(state)

        # Create task result
        result = TaskResult(
            success=True,
            output=response,
            agent=self.node_type,
            execution_time_ms=int((time.time() - start_time) * 1000),
        )

        state.add_task_result(result)
        state.add_message("assistant", response)
        state.final_response = response
        state.status = WorkflowStatus.COMPLETED

        return state

    async def _summarize_results(self, state: OrchestratorState) -> str:
        """Summarize results from other agents."""
        results_text = "\n".join([
            f"- {r.get('agent', 'Unknown')}: {r.get('output', '')[:200]}"
            for r in state.task_results
        ])

        prompt = f"""Based on the following agent results, provide a helpful summary for the user:

{results_text}

User's original request: {state.current_input}

Provide a clear, concise response."""

        return await self._call_llm(state, user_message=prompt)

    async def _handle_general(self, state: OrchestratorState) -> str:
        """Handle general questions."""
        return await self._call_llm(state)


class SetupAgentNode(BaseAgentNode):
    """Agent for DevLake setup and configuration."""

    node_type = AgentNode.SETUP
    name = "Setup Agent"
    description = "Helps with DevLake setup, connection configuration, and initial onboarding"

    def _create_system_prompt(self, state: OrchestratorState) -> str:
        return """You are the Setup Agent for NexusAI, specializing in DevLake configuration.

You help users:
1. Set up DevLake for their organization
2. Configure connections to GitHub, GitLab, Jira, Jenkins, etc.
3. Validate and test connections
4. Set up project scopes and collection schedules

Available tools:
- check_devlake_status: Check if DevLake is running
- list_connections: List configured connections
- create_connection: Create a new data source connection
- test_connection: Test a connection's validity
- create_project: Create a new project scope

Always guide users step-by-step and confirm actions before making changes."""

    async def execute(self, state: OrchestratorState) -> OrchestratorState:
        """Execute setup agent logic."""
        start_time = time.time()

        state.status = WorkflowStatus.EXECUTING
        state.current_node = self.node_type
        state.iteration_count += 1

        # Determine what setup action is needed
        intent = state.current_intent

        if intent == "setup_devlake":
            response = await self._handle_devlake_setup(state)
        elif intent == "configure_connection":
            response = await self._handle_connection_config(state)
        elif intent == "test_connection":
            response = await self._handle_connection_test(state)
        else:
            response = await self._call_llm(state)

        result = TaskResult(
            success=True,
            output=response,
            agent=self.node_type,
            execution_time_ms=int((time.time() - start_time) * 1000),
        )

        state.add_task_result(result)
        state.add_message("assistant", response)
        state.final_response = response
        state.status = WorkflowStatus.COMPLETED

        return state

    async def _handle_devlake_setup(self, state: OrchestratorState) -> str:
        """Handle DevLake initial setup."""
        return """I'll help you set up DevLake for your engineering metrics. Here's what we need to do:

1. **Check DevLake Status**: First, let me verify that DevLake is running properly.

2. **Configure Data Sources**: You'll need to connect your development tools:
   - Version Control (GitHub, GitLab, Bitbucket)
   - Issue Tracking (Jira, GitHub Issues)
   - CI/CD (Jenkins, GitHub Actions, GitLab CI)

3. **Create Projects**: Define project scopes to collect metrics for specific teams or repositories.

4. **Set Up Collection**: Configure how often to sync data.

Would you like me to check the current DevLake status and available connections?"""

    async def _handle_connection_config(self, state: OrchestratorState) -> str:
        """Handle connection configuration."""
        entities = state.context.get("extracted_entities", {})
        platform = entities.get("platform", "your data source")

        return f"""To configure a connection to {platform}, I'll need the following information:

1. **API Token/Credentials**: A personal access token or API key
2. **Base URL** (if self-hosted): The URL of your {platform} instance
3. **Scope**: Which repositories or projects to sync

Please provide your {platform} API token to continue.

⚠️ **Security Note**: Your credentials will be encrypted and stored securely."""

    async def _handle_connection_test(self, state: OrchestratorState) -> str:
        """Handle connection testing."""
        return """I'll test your connections to verify they're working properly.

Testing connections...

Results will show:
- ✅ Connection successful
- ⚠️ Partial access (some scopes missing)
- ❌ Connection failed (with error details)

Which connection would you like me to test?"""


class MetricsAgentNode(BaseAgentNode):
    """Agent for DORA and engineering metrics."""

    node_type = AgentNode.METRICS
    name = "Metrics Agent"
    description = "Calculates and explains DORA metrics and engineering performance indicators"

    def _create_system_prompt(self, state: OrchestratorState) -> str:
        return """You are the Metrics Agent for NexusAI, specializing in DORA and engineering metrics.

You help users understand:
1. **Deployment Frequency**: How often code is deployed to production
2. **Lead Time for Changes**: Time from commit to production
3. **Change Failure Rate**: Percentage of deployments causing failures
4. **MTTR (Mean Time to Recovery)**: Average time to recover from failures

You can also provide:
- Flow metrics (WIP, cycle time, throughput)
- Team performance comparisons
- Trend analysis over time

Always provide context for metrics and explain what good/bad values look like.
Reference industry benchmarks when relevant (DORA State of DevOps reports)."""

    async def execute(self, state: OrchestratorState) -> OrchestratorState:
        """Execute metrics agent logic."""
        start_time = time.time()

        state.status = WorkflowStatus.EXECUTING
        state.current_node = self.node_type
        state.iteration_count += 1

        intent = state.current_intent

        # Handle specific metric requests
        metric_handlers = {
            "get_dora_metrics": self._handle_dora_metrics,
            "deployment_frequency": self._handle_deployment_frequency,
            "lead_time": self._handle_lead_time,
            "change_failure_rate": self._handle_cfr,
            "mttr": self._handle_mttr,
        }

        handler = metric_handlers.get(intent, self._handle_general_metrics)
        response = await handler(state)

        result = TaskResult(
            success=True,
            output=response,
            agent=self.node_type,
            execution_time_ms=int((time.time() - start_time) * 1000),
        )

        state.add_task_result(result)
        state.add_message("assistant", response)
        state.final_response = response
        state.status = WorkflowStatus.COMPLETED

        return state

    async def _handle_dora_metrics(self, state: OrchestratorState) -> str:
        """Handle DORA metrics overview request."""
        return """Here's your DORA metrics overview:

## 📊 DORA Metrics Summary

| Metric | Value | Benchmark | Status |
|--------|-------|-----------|--------|
| Deployment Frequency | -- | Weekly+ | ⏳ Collecting |
| Lead Time for Changes | -- | < 1 day | ⏳ Collecting |
| Change Failure Rate | -- | < 15% | ⏳ Collecting |
| Mean Time to Recovery | -- | < 1 hour | ⏳ Collecting |

To see actual metrics, I need to query your DevLake data. Would you like me to:
1. Check which data sources are connected
2. Set up missing connections
3. View metrics for a specific project or team

What would you like to do?"""

    async def _handle_deployment_frequency(self, state: OrchestratorState) -> str:
        return """## 🚀 Deployment Frequency

**What it measures**: How often your team deploys code to production.

**Industry Benchmarks** (DORA 2023):
- Elite: On-demand (multiple deploys per day)
- High: Between once per day and once per week
- Medium: Between once per week and once per month
- Low: Less than once per month

To calculate your deployment frequency, I need:
1. CI/CD pipeline data (deployments to production)
2. Time range for analysis

Would you like me to query your deployment data?"""

    async def _handle_lead_time(self, state: OrchestratorState) -> str:
        return """## ⏱️ Lead Time for Changes

**What it measures**: Time from code commit to running in production.

**Industry Benchmarks** (DORA 2023):
- Elite: Less than one hour
- High: Between one day and one week
- Medium: Between one week and one month
- Low: More than one month

This metric includes:
- Coding time
- PR review time
- CI/CD pipeline time
- Deployment time

Would you like me to analyze your lead time breakdown?"""

    async def _handle_cfr(self, state: OrchestratorState) -> str:
        return """## ⚠️ Change Failure Rate

**What it measures**: Percentage of deployments causing production failures.

**Industry Benchmarks** (DORA 2023):
- Elite: 0-15%
- High: 0-15%
- Medium: 16-30%
- Low: 31-45%

Failures include:
- Rollbacks
- Hotfixes
- Service degradations
- Outages

Would you like me to analyze your failure patterns?"""

    async def _handle_mttr(self, state: OrchestratorState) -> str:
        return """## 🔧 Mean Time to Recovery (MTTR)

**What it measures**: Average time to restore service after a failure.

**Industry Benchmarks** (DORA 2023):
- Elite: Less than one hour
- High: Less than one day
- Medium: Less than one week
- Low: More than one week

MTTR is calculated from:
- Incident detection time
- Diagnosis time
- Fix implementation time
- Deployment time

Would you like me to analyze your incident recovery patterns?"""

    async def _handle_general_metrics(self, state: OrchestratorState) -> str:
        return await self._call_llm(state)


class QueryAgentNode(BaseAgentNode):
    """Agent for querying DevLake data."""

    node_type = AgentNode.QUERY
    name = "Query Agent"
    description = "Queries and retrieves data from DevLake and connected sources"

    def _create_system_prompt(self, state: OrchestratorState) -> str:
        return """You are the Query Agent for NexusAI, specializing in data retrieval.

You help users:
1. Query project and repository information
2. Retrieve commit and PR data
3. Search across connected data sources
4. Filter and aggregate engineering data

You can query:
- Repositories and projects
- Commits and code changes
- Pull requests and reviews
- Issues and incidents
- CI/CD pipelines and builds

Always clarify the scope (time range, projects, teams) before running queries."""

    async def execute(self, state: OrchestratorState) -> OrchestratorState:
        """Execute query agent logic."""
        start_time = time.time()

        state.status = WorkflowStatus.EXECUTING
        state.current_node = self.node_type
        state.iteration_count += 1

        # Generate query response
        response = await self._handle_query(state)

        result = TaskResult(
            success=True,
            output=response,
            agent=self.node_type,
            execution_time_ms=int((time.time() - start_time) * 1000),
        )

        state.add_task_result(result)
        state.add_message("assistant", response)
        state.final_response = response
        state.status = WorkflowStatus.COMPLETED

        return state

    async def _handle_query(self, state: OrchestratorState) -> str:
        """Handle data query requests."""
        intent = state.current_intent
        entities = state.context.get("extracted_entities", {})

        if intent == "list_repositories":
            return self._list_repositories_response()
        elif intent == "get_commits":
            return self._get_commits_response(entities)
        elif intent == "get_pull_requests":
            return self._get_prs_response(entities)
        else:
            return await self._call_llm(state)

    def _list_repositories_response(self) -> str:
        return """## 📁 Repositories

To list your repositories, I need to query DevLake.

Available filters:
- By project scope
- By team/organization
- By activity level

Would you like me to:
1. List all connected repositories
2. Filter by specific criteria
3. Show repository statistics

What would you prefer?"""

    def _get_commits_response(self, entities: dict) -> str:
        time_range = entities.get("time_range", {}).get("value", "last 7 days")
        repo = entities.get("repository", "all repositories")

        return f"""## 📝 Commits Query

**Scope**: {repo}
**Time Range**: {time_range}

I can show you:
- Commit count by author
- Commit frequency over time
- File change statistics
- Lines added/removed

Preparing query..."""

    def _get_prs_response(self, entities: dict) -> str:
        return """## 🔀 Pull Requests

I can retrieve:
- Open PRs awaiting review
- Recently merged PRs
- PR review statistics
- Average merge time

What type of PR information would you like?"""


class InsightsAgentNode(BaseAgentNode):
    """Agent for generating insights and recommendations."""

    node_type = AgentNode.INSIGHTS
    name = "Insights Agent"
    description = "Analyzes data to provide insights, trends, and recommendations"

    def _create_system_prompt(self, state: OrchestratorState) -> str:
        return """You are the Insights Agent for NexusAI, specializing in analysis and recommendations.

You help users:
1. Identify performance trends
2. Spot bottlenecks and issues
3. Compare team performance
4. Provide actionable recommendations

Your insights should be:
- Data-driven when data is available
- Actionable with clear next steps
- Contextual to the user's situation
- Prioritized by impact

Always explain the reasoning behind your recommendations."""

    async def execute(self, state: OrchestratorState) -> OrchestratorState:
        """Execute insights agent logic."""
        start_time = time.time()

        state.status = WorkflowStatus.EXECUTING
        state.current_node = self.node_type
        state.iteration_count += 1

        intent = state.current_intent

        if intent == "analyze_trends":
            response = await self._analyze_trends(state)
        elif intent == "get_recommendations":
            response = await self._get_recommendations(state)
        elif intent == "identify_bottlenecks":
            response = await self._identify_bottlenecks(state)
        else:
            response = await self._call_llm(state)

        result = TaskResult(
            success=True,
            output=response,
            agent=self.node_type,
            execution_time_ms=int((time.time() - start_time) * 1000),
        )

        state.add_task_result(result)
        state.add_message("assistant", response)
        state.final_response = response
        state.status = WorkflowStatus.COMPLETED

        return state

    async def _analyze_trends(self, state: OrchestratorState) -> str:
        return """## 📈 Trend Analysis

To provide trend analysis, I'll look at your metrics over time.

**Available Trend Views**:
1. **Deployment Velocity** - Are you deploying more or less frequently?
2. **Quality Trends** - Is your failure rate improving?
3. **Efficiency Trends** - Is lead time decreasing?
4. **Team Velocity** - Story points/issues completed over time

**Time Ranges Available**:
- Last 7 days
- Last 30 days
- Last 90 days
- Quarter-over-quarter

Which trend would you like to explore?"""

    async def _get_recommendations(self, state: OrchestratorState) -> str:
        return """## 💡 Recommendations

Based on engineering best practices, here are common improvement areas:

### Quick Wins
1. **Automate more tests** - Increase test coverage to reduce manual testing time
2. **Smaller PRs** - Break large PRs into smaller, reviewable chunks
3. **Async code reviews** - Set up automated review assignment

### Strategic Improvements
1. **Continuous deployment** - Move towards trunk-based development
2. **Feature flags** - Decouple deployment from release
3. **Observability** - Improve monitoring and alerting

To provide personalized recommendations, I need to analyze your current metrics.

Would you like me to:
1. Analyze your current workflow
2. Compare with industry benchmarks
3. Create an improvement roadmap

What would be most helpful?"""

    async def _identify_bottlenecks(self, state: OrchestratorState) -> str:
        return """## 🔍 Bottleneck Analysis

I'll help identify where your delivery pipeline slows down.

**Common Bottleneck Areas**:

1. **Code Review**
   - Long wait times for reviews
   - Large PR sizes
   - Limited reviewers

2. **Testing**
   - Slow test suites
   - Flaky tests
   - Manual testing requirements

3. **Deployment**
   - Manual deployment steps
   - Approval bottlenecks
   - Environment availability

4. **Planning**
   - Unclear requirements
   - Large batch sizes
   - Dependencies between teams

To identify your specific bottlenecks, I need to analyze:
- PR review times
- Build durations
- Deployment frequency patterns

Should I start the analysis?"""


class CodeAnalysisNode(BaseAgentNode):
    """Agent for code analysis and review."""

    node_type = AgentNode.CODE_ANALYSIS
    name = "Code Analysis Agent"
    description = "Analyzes code quality, reviews PRs, and identifies improvements"

    async def execute(self, state: OrchestratorState) -> OrchestratorState:
        """Execute code analysis logic."""
        start_time = time.time()

        state.status = WorkflowStatus.EXECUTING
        state.current_node = self.node_type
        state.iteration_count += 1

        response = """## 🔬 Code Analysis

I can help with:

1. **PR Review Analysis**
   - Review complexity and risk assessment
   - Code quality metrics
   - Test coverage impact

2. **Code Quality Checks**
   - Identify code smells
   - Security vulnerabilities
   - Performance issues

3. **Repository Health**
   - Technical debt assessment
   - Dependency analysis
   - Documentation coverage

What would you like me to analyze?"""

        result = TaskResult(
            success=True,
            output=response,
            agent=self.node_type,
            execution_time_ms=int((time.time() - start_time) * 1000),
        )

        state.add_task_result(result)
        state.add_message("assistant", response)
        state.final_response = response
        state.status = WorkflowStatus.COMPLETED

        return state


class HumanInputNode(BaseAgentNode):
    """Node for requesting human input."""

    node_type = AgentNode.HUMAN
    name = "Human Input"
    description = "Requests input from the user"

    async def execute(self, state: OrchestratorState) -> OrchestratorState:
        """Request human input."""
        state.status = WorkflowStatus.WAITING_INPUT
        state.current_node = self.node_type

        # The workflow will pause here until human input is provided
        prompt = state.human_input_prompt or "Please provide additional information."

        if state.human_input_options:
            options_text = "\n".join([f"- {opt}" for opt in state.human_input_options])
            prompt = f"{prompt}\n\nOptions:\n{options_text}"

        state.add_message("assistant", prompt)
        state.final_response = prompt

        return state


# Node factory
def get_agent_node(node_type: AgentNode, llm_gateway=None) -> BaseAgentNode:
    """Get an agent node instance by type."""
    node_map = {
        AgentNode.SUPERVISOR: SupervisorNode,
        AgentNode.SETUP: SetupAgentNode,
        AgentNode.METRICS: MetricsAgentNode,
        AgentNode.QUERY: QueryAgentNode,
        AgentNode.INSIGHTS: InsightsAgentNode,
        AgentNode.CODE_ANALYSIS: CodeAnalysisNode,
        AgentNode.HUMAN: HumanInputNode,
    }

    node_class = node_map.get(node_type, SupervisorNode)
    return node_class(llm_gateway=llm_gateway)
