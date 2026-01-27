"""Intent routing for the agent orchestrator."""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

import structlog

from app.services.agents.orchestrator.state import AgentNode, OrchestratorState

logger = structlog.get_logger()


class TaskIntent(str, Enum):
    """Task intents that map to agent nodes."""

    # Setup intents
    SETUP_DEVLAKE = "setup_devlake"
    CONFIGURE_CONNECTION = "configure_connection"
    TEST_CONNECTION = "test_connection"

    # Metrics intents
    GET_DORA_METRICS = "get_dora_metrics"
    DEPLOYMENT_FREQUENCY = "deployment_frequency"
    LEAD_TIME = "lead_time"
    CHANGE_FAILURE_RATE = "change_failure_rate"
    MTTR = "mttr"
    FLOW_METRICS = "flow_metrics"

    # Query intents
    QUERY_DATA = "query_data"
    SEARCH_PROJECTS = "search_projects"
    LIST_REPOSITORIES = "list_repositories"
    GET_COMMITS = "get_commits"
    GET_PULL_REQUESTS = "get_pull_requests"

    # Insights intents
    ANALYZE_TRENDS = "analyze_trends"
    GET_RECOMMENDATIONS = "get_recommendations"
    COMPARE_TEAMS = "compare_teams"
    IDENTIFY_BOTTLENECKS = "identify_bottlenecks"

    # Code analysis intents
    REVIEW_CODE = "review_code"
    ANALYZE_PR = "analyze_pr"
    CHECK_QUALITY = "check_quality"

    # General
    GENERAL_QUESTION = "general_question"
    HELP = "help"
    UNKNOWN = "unknown"


@dataclass
class IntentClassification:
    """Result of intent classification."""

    intent: TaskIntent
    confidence: float
    target_agent: AgentNode
    extracted_entities: dict[str, Any]
    reasoning: str | None = None


# Intent patterns for rule-based classification
INTENT_PATTERNS: dict[TaskIntent, list[tuple[str, float]]] = {
    # Setup patterns
    TaskIntent.SETUP_DEVLAKE: [
        (r"set\s*up\s+devlake", 0.95),
        (r"configure\s+devlake", 0.9),
        (r"install\s+devlake", 0.9),
        (r"get\s+started\s+with\s+devlake", 0.85),
    ],
    TaskIntent.CONFIGURE_CONNECTION: [
        (r"(connect|add|configure)\s+(to\s+)?(github|gitlab|jira|jenkins|bitbucket)", 0.9),
        (r"set\s*up\s+(github|gitlab|jira|jenkins|bitbucket)\s+connection", 0.95),
    ],
    TaskIntent.TEST_CONNECTION: [
        (r"test\s+(the\s+)?connection", 0.9),
        (r"verify\s+(the\s+)?connection", 0.9),
        (r"check\s+if\s+.+\s+is\s+connected", 0.85),
    ],

    # DORA metrics patterns
    TaskIntent.GET_DORA_METRICS: [
        (r"(show|get|display|what\s+are)\s+(my\s+)?dora\s+metrics", 0.95),
        (r"dora\s+(4|four)\s+metrics", 0.9),
        (r"engineering\s+metrics", 0.8),
    ],
    TaskIntent.DEPLOYMENT_FREQUENCY: [
        (r"deployment\s+frequency", 0.95),
        (r"how\s+often\s+(do\s+we|are\s+we)\s+deploy", 0.9),
        (r"deployments?\s+per\s+(day|week|month)", 0.85),
    ],
    TaskIntent.LEAD_TIME: [
        (r"lead\s+time(\s+for\s+changes?)?", 0.95),
        (r"how\s+long\s+(does\s+it\s+take|until)\s+(to\s+)?deploy", 0.85),
        (r"time\s+to\s+production", 0.85),
    ],
    TaskIntent.CHANGE_FAILURE_RATE: [
        (r"change\s+failure\s+rate", 0.95),
        (r"cfr", 0.8),
        (r"failed\s+deployments?", 0.8),
        (r"deployment\s+failures?", 0.8),
    ],
    TaskIntent.MTTR: [
        (r"(mttr|mean\s+time\s+to\s+recover)", 0.95),
        (r"recovery\s+time", 0.85),
        (r"how\s+(long|quickly)\s+(to|do\s+we)\s+recover", 0.8),
    ],

    # Query patterns
    TaskIntent.QUERY_DATA: [
        (r"(show|list|get|find|query)\s+.+\s+(data|information|records)", 0.8),
        (r"what\s+(is|are)\s+the\s+.+\s+for", 0.7),
    ],
    TaskIntent.SEARCH_PROJECTS: [
        (r"(search|find|list|show)\s+(my\s+)?projects?", 0.9),
        (r"what\s+projects?\s+(do\s+we|are\s+there)", 0.85),
    ],
    TaskIntent.LIST_REPOSITORIES: [
        (r"(list|show|get)\s+(all\s+)?(my\s+)?repos(itories)?", 0.9),
        (r"what\s+repos(itories)?\s+(do\s+we\s+have|are\s+there)", 0.85),
    ],
    TaskIntent.GET_COMMITS: [
        (r"(show|get|list)\s+(recent\s+)?commits?", 0.9),
        (r"commit\s+history", 0.85),
        (r"who\s+committed", 0.8),
    ],
    TaskIntent.GET_PULL_REQUESTS: [
        (r"(show|get|list)\s+(open\s+|closed\s+|merged\s+)?p(ull\s+)?r(equest)?s?", 0.9),
        (r"pending\s+reviews?", 0.8),
        (r"merge\s+requests?", 0.85),
    ],

    # Insights patterns
    TaskIntent.ANALYZE_TRENDS: [
        (r"(analyze|show|what\s+are)\s+(the\s+)?trends?", 0.9),
        (r"how\s+(is|are)\s+(we|the\s+team)\s+(doing|performing)", 0.85),
        (r"performance\s+over\s+time", 0.85),
    ],
    TaskIntent.GET_RECOMMENDATIONS: [
        (r"(give|suggest|recommend|what\s+should)", 0.85),
        (r"how\s+(can|to)\s+improve", 0.9),
        (r"recommendations?\s+(for|to)", 0.9),
    ],
    TaskIntent.COMPARE_TEAMS: [
        (r"compare\s+(teams?|projects?|repos?)", 0.9),
        (r"(team|project)\s+comparison", 0.9),
        (r"which\s+team\s+(is\s+)?(better|faster|more)", 0.85),
    ],
    TaskIntent.IDENTIFY_BOTTLENECKS: [
        (r"(find|identify|what\s+are)\s+(the\s+)?bottlenecks?", 0.95),
        (r"what('s|\s+is)\s+slowing\s+(us|the\s+team)\s+down", 0.9),
        (r"blockers?", 0.7),
    ],

    # Code analysis patterns
    TaskIntent.REVIEW_CODE: [
        (r"review\s+(this\s+|my\s+)?code", 0.9),
        (r"code\s+review", 0.9),
    ],
    TaskIntent.ANALYZE_PR: [
        (r"(analyze|review)\s+(this\s+)?p(ull\s+)?r(equest)?", 0.9),
        (r"(what|how)\s+(about|is)\s+this\s+pr", 0.85),
    ],
    TaskIntent.CHECK_QUALITY: [
        (r"(check|analyze)\s+(code\s+)?quality", 0.9),
        (r"code\s+(quality|standards?|smell)", 0.85),
    ],

    # General patterns
    TaskIntent.HELP: [
        (r"^help$", 0.95),
        (r"what\s+can\s+you\s+do", 0.9),
        (r"how\s+do\s+I\s+use", 0.85),
        (r"show\s+commands?", 0.85),
    ],
}

# Intent to agent mapping
INTENT_AGENT_MAP: dict[TaskIntent, AgentNode] = {
    # Setup agent
    TaskIntent.SETUP_DEVLAKE: AgentNode.SETUP,
    TaskIntent.CONFIGURE_CONNECTION: AgentNode.SETUP,
    TaskIntent.TEST_CONNECTION: AgentNode.SETUP,

    # Metrics agent
    TaskIntent.GET_DORA_METRICS: AgentNode.METRICS,
    TaskIntent.DEPLOYMENT_FREQUENCY: AgentNode.METRICS,
    TaskIntent.LEAD_TIME: AgentNode.METRICS,
    TaskIntent.CHANGE_FAILURE_RATE: AgentNode.METRICS,
    TaskIntent.MTTR: AgentNode.METRICS,
    TaskIntent.FLOW_METRICS: AgentNode.METRICS,

    # Query agent
    TaskIntent.QUERY_DATA: AgentNode.QUERY,
    TaskIntent.SEARCH_PROJECTS: AgentNode.QUERY,
    TaskIntent.LIST_REPOSITORIES: AgentNode.QUERY,
    TaskIntent.GET_COMMITS: AgentNode.QUERY,
    TaskIntent.GET_PULL_REQUESTS: AgentNode.QUERY,

    # Insights agent
    TaskIntent.ANALYZE_TRENDS: AgentNode.INSIGHTS,
    TaskIntent.GET_RECOMMENDATIONS: AgentNode.INSIGHTS,
    TaskIntent.COMPARE_TEAMS: AgentNode.INSIGHTS,
    TaskIntent.IDENTIFY_BOTTLENECKS: AgentNode.INSIGHTS,

    # Code analysis agent
    TaskIntent.REVIEW_CODE: AgentNode.CODE_ANALYSIS,
    TaskIntent.ANALYZE_PR: AgentNode.CODE_ANALYSIS,
    TaskIntent.CHECK_QUALITY: AgentNode.CODE_ANALYSIS,

    # General
    TaskIntent.GENERAL_QUESTION: AgentNode.QUERY,
    TaskIntent.HELP: AgentNode.SUPERVISOR,
    TaskIntent.UNKNOWN: AgentNode.SUPERVISOR,
}


class IntentRouter:
    """Routes user intents to appropriate agents."""

    def __init__(self, use_llm: bool = True):
        """
        Initialize the intent router.

        Args:
            use_llm: Whether to use LLM for intent classification
                     as fallback to pattern matching.
        """
        self.use_llm = use_llm
        self._compiled_patterns: dict[TaskIntent, list[tuple[re.Pattern, float]]] = {}

        # Compile patterns
        for intent, patterns in INTENT_PATTERNS.items():
            self._compiled_patterns[intent] = [
                (re.compile(p, re.IGNORECASE), conf)
                for p, conf in patterns
            ]

    def classify(
        self,
        user_input: str,
        context: dict[str, Any] | None = None,
    ) -> IntentClassification:
        """
        Classify user input to determine intent.

        Uses pattern matching first, then LLM as fallback.
        """
        # Try pattern-based classification first
        classification = self._pattern_classify(user_input)

        if classification.confidence >= 0.8:
            return classification

        # Use LLM classification as fallback if enabled
        if self.use_llm and classification.confidence < 0.6:
            llm_classification = self._llm_classify(user_input, context)
            if llm_classification.confidence > classification.confidence:
                return llm_classification

        return classification

    def _pattern_classify(self, user_input: str) -> IntentClassification:
        """Classify using pattern matching."""
        best_intent = TaskIntent.UNKNOWN
        best_confidence = 0.0
        entities: dict[str, Any] = {}

        for intent, patterns in self._compiled_patterns.items():
            for pattern, base_confidence in patterns:
                match = pattern.search(user_input)
                if match:
                    # Adjust confidence based on match quality
                    confidence = base_confidence

                    # Boost if match covers significant portion
                    match_ratio = len(match.group(0)) / len(user_input)
                    if match_ratio > 0.5:
                        confidence *= 1.1

                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_intent = intent

                        # Extract entities from match groups
                        if match.groups():
                            for i, group in enumerate(match.groups()):
                                if group:
                                    entities[f"group_{i}"] = group

        # Extract common entities
        entities.update(self._extract_entities(user_input))

        return IntentClassification(
            intent=best_intent,
            confidence=min(best_confidence, 1.0),
            target_agent=INTENT_AGENT_MAP.get(best_intent, AgentNode.SUPERVISOR),
            extracted_entities=entities,
            reasoning="Pattern matching classification",
        )

    def _llm_classify(
        self,
        user_input: str,
        context: dict[str, Any] | None = None,
    ) -> IntentClassification:
        """
        Classify using LLM.

        Note: This is a placeholder - actual implementation would
        use the LLM Gateway service.
        """
        # For now, return a low-confidence classification
        # In production, this would call the LLM
        logger.debug(
            "LLM classification not implemented, using fallback",
            input=user_input[:100],
        )

        return IntentClassification(
            intent=TaskIntent.GENERAL_QUESTION,
            confidence=0.5,
            target_agent=AgentNode.QUERY,
            extracted_entities=self._extract_entities(user_input),
            reasoning="LLM fallback classification",
        )

    def _extract_entities(self, user_input: str) -> dict[str, Any]:
        """Extract common entities from user input."""
        entities = {}

        # Extract project/repo names
        repo_match = re.search(r"(?:repo(?:sitory)?|project)\s+['\"]?(\w[\w-]*/?\w[\w-]*)['\"]?", user_input, re.I)
        if repo_match:
            entities["repository"] = repo_match.group(1)

        # Extract team names
        team_match = re.search(r"team\s+['\"]?(\w[\w\s-]+)['\"]?", user_input, re.I)
        if team_match:
            entities["team"] = team_match.group(1).strip()

        # Extract time ranges
        time_patterns = [
            (r"last\s+(\d+)\s+(days?|weeks?|months?)", "relative"),
            (r"past\s+(\d+)\s+(days?|weeks?|months?)", "relative"),
            (r"this\s+(week|month|quarter|year)", "current"),
        ]

        for pattern, time_type in time_patterns:
            match = re.search(pattern, user_input, re.I)
            if match:
                entities["time_range"] = {
                    "type": time_type,
                    "value": match.group(0),
                }
                break

        # Extract platform mentions
        platforms = ["github", "gitlab", "jira", "jenkins", "bitbucket", "azure"]
        for platform in platforms:
            if platform in user_input.lower():
                entities["platform"] = platform
                break

        return entities

    def route(self, state: OrchestratorState) -> AgentNode:
        """
        Route based on current state.

        Returns the next agent node to execute.
        """
        # If we have a classified intent, use its target agent
        if state.current_intent:
            try:
                intent = TaskIntent(state.current_intent)
                return INTENT_AGENT_MAP.get(intent, AgentNode.SUPERVISOR)
            except ValueError:
                pass

        # If human input is required, route to human
        if state.requires_human_input:
            return AgentNode.HUMAN

        # If we have errors, might need supervisor
        if len(state.errors) > 2:
            return AgentNode.SUPERVISOR

        # Default to supervisor for unhandled cases
        return AgentNode.SUPERVISOR

    def get_available_intents(self) -> list[dict[str, Any]]:
        """Get list of available intents with descriptions."""
        return [
            {
                "intent": intent.value,
                "target_agent": INTENT_AGENT_MAP.get(intent, AgentNode.SUPERVISOR).value,
            }
            for intent in TaskIntent
        ]
