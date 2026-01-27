"""Intent Classifier - Fast intent recognition for chatbot responses."""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


class Intent(str, Enum):
    """User intents for the setup chatbot."""

    # Setup intents
    CONNECT = "connect"
    CREATE_PROJECT = "create_project"
    CREATE_PIPELINE = "create_pipeline"
    START_ONBOARDING = "start_onboarding"

    # Information intents
    GET_STATUS = "get_status"
    LIST_CONNECTIONS = "list_connections"
    LIST_PROJECTS = "list_projects"
    LIST_PLUGINS = "list_plugins"
    GET_HELP = "get_help"
    EXPLAIN_CONCEPT = "explain_concept"

    # Flow control
    CONFIRM = "confirm"
    CANCEL = "cancel"
    GO_BACK = "go_back"
    SKIP = "skip"

    # Greetings
    GREETING = "greeting"
    FAREWELL = "farewell"

    # Unknown
    UNKNOWN = "unknown"


@dataclass
class IntentMatch:
    """Result of intent classification."""

    intent: Intent
    confidence: float
    entities: dict[str, Any]
    raw_text: str


class IntentClassifier:
    """Fast rule-based intent classifier with entity extraction."""

    def __init__(self):
        # Pattern definitions for each intent
        self._patterns = {
            Intent.CONNECT: [
                r'\b(connect|setup|configure|add)\b.*(github|gitlab|jira|jenkins|source|connection)',
                r'\b(github|gitlab|jira|jenkins)\b.*(connect|setup)',
                r'\bnew\s+connection\b',
                r'\bconnect\s+to\b',
                r'\blink\s+(my\s+)?(github|gitlab|jira|jenkins)',
            ],
            Intent.CREATE_PROJECT: [
                r'\b(create|new|setup|start)\b.*(project|workspace)',
                r'\bproject\b.*(create|new|setup)',
                r'\bnew\s+project\b',
            ],
            Intent.CREATE_PIPELINE: [
                r'\b(create|new|setup|configure)\b.*(pipeline|sync|collection)',
                r'\bpipeline\b.*(create|new|setup)',
                r'\bschedule\s+(data\s+)?(sync|collection)',
                r'\bautomate\s+data',
            ],
            Intent.START_ONBOARDING: [
                r'\b(start|begin|run)\s+onboarding\b',
                r'\bget\s+started\b',
                r'\bguide\s+me\b',
                r'\bwalk\s+(me\s+)?through\b',
                r'\bfirst\s+time\s+setup\b',
            ],
            Intent.GET_STATUS: [
                r'\b(status|health|check)\b',
                r'\b(is|are)\s+(everything|devlake|system)\s+(ok|working|online)',
                r'\bsystem\s+status\b',
            ],
            Intent.LIST_CONNECTIONS: [
                r'\b(list|show|view|get)\b.*(connection|source)',
                r'\bmy\s+connections?\b',
                r'\bwhat.*(connected|linked)',
            ],
            Intent.LIST_PROJECTS: [
                r'\b(list|show|view|get)\b.*project',
                r'\bmy\s+projects?\b',
                r'\bwhat\s+projects\b',
            ],
            Intent.LIST_PLUGINS: [
                r'\b(list|show|view|available)\b.*(plugin|source|integration)',
                r'\bwhat.*(support|integrate|connect)',
                r'\bsupported\s+(sources|tools|plugins)',
            ],
            Intent.GET_HELP: [
                r'^help\b',
                r'\bhelp\s+me\b',
                r'\bwhat\s+can\s+you\s+do\b',
                r'\bhow\s+(do|can|to)\b',
                r'\bexplain\b',
                r'\?\s*$',  # Ends with question mark
            ],
            Intent.EXPLAIN_CONCEPT: [
                r'\bwhat\s+(is|are)\s+(a\s+)?(project|pipeline|connection|dora|metric)',
                r'\bexplain\s+(project|pipeline|connection|dora|metric)',
                r'\btell\s+me\s+about\s+(project|pipeline|connection|dora)',
            ],
            Intent.CONFIRM: [
                r'^(yes|yeah|yep|sure|ok|okay|confirm|proceed|go\s+ahead|do\s+it|create|submit)$',
                r'^y$',
                r'\byes\s+(please|do\s+it)\b',
                r'\bsounds\s+good\b',
                r'\blooks\s+(good|correct|right)\b',
            ],
            Intent.CANCEL: [
                r'^(cancel|stop|quit|exit|abort|nevermind|never\s+mind)$',
                r'^n$',
                r'^no$',
                r'\bcancel\s+(this|that|setup)\b',
                r'\bstop\s+(this|that|setup)\b',
                r'\bdon\'?t\s+(do\s+it|proceed|continue)\b',
            ],
            Intent.GO_BACK: [
                r'^(back|previous|go\s+back|undo)$',
                r'\bgo\s+back\b',
                r'\bprevious\s+(step|question)\b',
                r'\bstart\s+over\b',
            ],
            Intent.SKIP: [
                r'^(skip|later|not\s+now)$',
                r'\bskip\s+(this|that)\b',
                r'\bdo\s+(this|it)\s+later\b',
            ],
            Intent.GREETING: [
                r'^(hi|hello|hey|howdy|greetings|good\s+(morning|afternoon|evening))[\s!.,]*$',
                r'^yo\b',
            ],
            Intent.FAREWELL: [
                r'^(bye|goodbye|see\s+you|later|exit|done|finish)[\s!.,]*$',
                r'\bthanks?\s*(you)?\s*(bye|goodbye)?$',
            ],
        }

        # Entity patterns
        self._entity_patterns = {
            'plugin': r'\b(github|gitlab|jira|jenkins|azure\s*devops|sonarqube|pagerduty|bitbucket)\b',
            'project_name': r'(?:project\s+(?:named?|called?)\s+)?["\']?([a-zA-Z0-9_-]+)["\']?',
            'time_range': r'\b(daily|weekly|monthly|hourly|every\s+\d+\s+(?:hour|day|week)s?)\b',
        }

        # Compile patterns for efficiency
        self._compiled_patterns = {
            intent: [re.compile(p, re.IGNORECASE) for p in patterns]
            for intent, patterns in self._patterns.items()
        }
        self._compiled_entities = {
            name: re.compile(pattern, re.IGNORECASE)
            for name, pattern in self._entity_patterns.items()
        }

    def classify(self, text: str) -> IntentMatch:
        """Classify the intent of a text message."""
        text = text.strip()
        normalized = text.lower()

        # Check each intent pattern
        best_intent = Intent.UNKNOWN
        best_confidence = 0.0

        for intent, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(normalized):
                    # Higher confidence for exact matches
                    confidence = 0.9 if pattern.match(normalized) else 0.7
                    if confidence > best_confidence:
                        best_intent = intent
                        best_confidence = confidence

        # Extract entities
        entities = self._extract_entities(text)

        # Boost confidence if entities match intent
        if best_intent == Intent.CONNECT and entities.get('plugin'):
            best_confidence = min(best_confidence + 0.1, 1.0)

        return IntentMatch(
            intent=best_intent,
            confidence=best_confidence,
            entities=entities,
            raw_text=text,
        )

    def _extract_entities(self, text: str) -> dict[str, Any]:
        """Extract entities from text."""
        entities = {}

        for name, pattern in self._compiled_entities.items():
            match = pattern.search(text)
            if match:
                # Use the first capture group if present, otherwise the whole match
                entities[name] = match.group(1) if match.groups() else match.group(0)

        return entities

    def get_plugin_from_text(self, text: str) -> str | None:
        """Extract plugin name from text."""
        match = self._compiled_entities['plugin'].search(text.lower())
        if match:
            plugin = match.group(0).lower().replace(' ', '')
            # Normalize variations
            plugin_map = {
                'azuredevops': 'azuredevops',
                'azure': 'azuredevops',
            }
            return plugin_map.get(plugin, plugin)
        return None


# Singleton instance
intent_classifier = IntentClassifier()


def classify_intent(text: str) -> IntentMatch:
    """Classify the intent of a text message."""
    return intent_classifier.classify(text)


def get_plugin_from_text(text: str) -> str | None:
    """Extract plugin name from text."""
    return intent_classifier.get_plugin_from_text(text)
