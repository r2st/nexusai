"""Prompt injection detection."""

import re
from dataclasses import dataclass
from enum import Enum

import structlog

logger = structlog.get_logger()


class InjectionType(str, Enum):
    """Types of injection attacks."""

    DIRECT = "direct"  # Direct prompt manipulation
    INDIRECT = "indirect"  # Via retrieved content
    JAILBREAK = "jailbreak"  # Bypass safety measures
    PROMPT_LEAK = "prompt_leak"  # Extract system prompt
    CONTEXT_SWITCH = "context_switch"  # Change context/role


@dataclass
class InjectionPattern:
    """A pattern for detecting injection attempts."""

    name: str
    pattern: str
    type: InjectionType
    severity: float  # 0-1
    description: str


# Common injection patterns
INJECTION_PATTERNS = [
    # Direct instruction overrides
    InjectionPattern(
        name="ignore_instructions",
        pattern=r"ignore\s+(previous\s+|all\s+|above\s+|prior\s+)*(instructions?|prompts?|rules?)",
        type=InjectionType.DIRECT,
        severity=0.9,
        description="Attempt to ignore previous instructions",
    ),
    InjectionPattern(
        name="forget_instructions",
        pattern=r"forget\s+(everything|all|previous|your)\s*(instructions?|prompts?|rules?)?",
        type=InjectionType.DIRECT,
        severity=0.9,
        description="Attempt to make model forget instructions",
    ),
    InjectionPattern(
        name="new_instructions",
        pattern=r"(new|updated?|revised?|actual)\s+(instructions?|prompts?|rules?|directive)",
        type=InjectionType.DIRECT,
        severity=0.8,
        description="Attempt to inject new instructions",
    ),
    InjectionPattern(
        name="system_override",
        pattern=r"(system|admin|root)\s*(:|prompt|message|override)",
        type=InjectionType.DIRECT,
        severity=0.85,
        description="Attempt to simulate system message",
    ),
    # Role manipulation
    InjectionPattern(
        name="role_play",
        pattern=r"(pretend|act|imagine|roleplay)\s+(you\s+are|to\s+be|as|that)\s+.{5,}",
        type=InjectionType.JAILBREAK,
        severity=0.7,
        description="Attempt to change AI role",
    ),
    InjectionPattern(
        name="dan_jailbreak",
        pattern=r"(DAN|do\s+anything\s+now|jailbreak|dev\s*mode)",
        type=InjectionType.JAILBREAK,
        severity=0.95,
        description="Known jailbreak attempt (DAN)",
    ),
    InjectionPattern(
        name="hypothetical",
        pattern=r"(hypothetically|in\s+theory|if\s+you\s+could|just\s+imagine)",
        type=InjectionType.JAILBREAK,
        severity=0.5,
        description="Hypothetical bypass attempt",
    ),
    # Prompt extraction
    InjectionPattern(
        name="reveal_prompt",
        pattern=r"(reveal|show|display|print|output|repeat)\s*(your\s+)?(the\s+)?(system\s+)?(prompt|instructions?|rules?)",
        type=InjectionType.PROMPT_LEAK,
        severity=0.8,
        description="Attempt to extract system prompt",
    ),
    InjectionPattern(
        name="what_prompt",
        pattern=r"what\s+(is|are)\s+(your|the)\s+(system\s+)?(prompt|instructions?|rules?)",
        type=InjectionType.PROMPT_LEAK,
        severity=0.7,
        description="Question about system prompt",
    ),
    # Context manipulation
    InjectionPattern(
        name="end_conversation",
        pattern=r"(end|stop|terminate|finish)\s+(this\s+)?(conversation|chat|session)",
        type=InjectionType.CONTEXT_SWITCH,
        severity=0.6,
        description="Attempt to reset context",
    ),
    InjectionPattern(
        name="delimiter_injection",
        pattern=r"(```|###|---)\s*(system|end|new|ignore)",
        type=InjectionType.INDIRECT,
        severity=0.75,
        description="Delimiter-based injection",
    ),
    # Encoding tricks
    InjectionPattern(
        name="base64_command",
        pattern=r"(decode|base64|hex)\s*:\s*[A-Za-z0-9+/=]{10,}",
        type=InjectionType.INDIRECT,
        severity=0.7,
        description="Encoded command attempt",
    ),
    # Developer mode
    InjectionPattern(
        name="dev_mode",
        pattern=r"(developer|debug|maintenance|admin)\s*(mode|access|override)",
        type=InjectionType.JAILBREAK,
        severity=0.85,
        description="Developer mode bypass attempt",
    ),
]


class InjectionDetector:
    """Detects prompt injection attempts."""

    def __init__(self, patterns: list[InjectionPattern] | None = None):
        self.patterns = patterns or INJECTION_PATTERNS
        self._compiled_patterns = [
            (p, re.compile(p.pattern, re.IGNORECASE))
            for p in self.patterns
        ]

    def detect(self, text: str) -> list[tuple[InjectionPattern, float, str]]:
        """
        Detect injection patterns in text.

        Returns:
            List of (pattern, confidence, matched_text) tuples
        """
        detections = []

        for pattern, compiled in self._compiled_patterns:
            matches = compiled.findall(text)
            if matches:
                # Get the actual matched text
                match_obj = compiled.search(text)
                matched_text = match_obj.group(0) if match_obj else str(matches[0])

                # Calculate confidence based on context
                confidence = self._calculate_confidence(
                    pattern, text, matched_text
                )

                if confidence > 0.3:  # Minimum threshold
                    detections.append((pattern, confidence, matched_text))

        # Sort by severity * confidence
        detections.sort(
            key=lambda x: x[0].severity * x[1],
            reverse=True,
        )

        return detections

    def _calculate_confidence(
        self,
        pattern: InjectionPattern,
        full_text: str,
        matched_text: str,
    ) -> float:
        """Calculate confidence score for a detection."""
        base_confidence = pattern.severity

        # Adjust based on context
        text_lower = full_text.lower()

        # Higher confidence if appears at start
        if text_lower.strip().startswith(matched_text.lower()):
            base_confidence *= 1.2

        # Higher confidence if standalone (not in a question context)
        if "?" not in full_text:
            base_confidence *= 1.1

        # Lower confidence if in quotes (might be discussing injection)
        if f'"{matched_text}"' in full_text or f"'{matched_text}'" in full_text:
            base_confidence *= 0.5

        # Higher confidence for known attack sequences
        attack_indicators = [
            "ignore", "forget", "override", "bypass", "disable",
            "jailbreak", "dan", "developer mode"
        ]
        if any(ind in text_lower for ind in attack_indicators):
            base_confidence *= 1.15

        return min(base_confidence, 1.0)

    def get_threat_level(
        self,
        detections: list[tuple[InjectionPattern, float, str]],
    ) -> tuple[str, float]:
        """
        Get overall threat level from detections.

        Returns:
            (threat_level, max_score) tuple
        """
        if not detections:
            return "none", 0.0

        max_score = max(p.severity * conf for p, conf, _ in detections)

        if max_score >= 0.8:
            return "critical", max_score
        elif max_score >= 0.6:
            return "high", max_score
        elif max_score >= 0.4:
            return "medium", max_score
        elif max_score >= 0.2:
            return "low", max_score
        else:
            return "none", max_score

    def should_block(
        self,
        detections: list[tuple[InjectionPattern, float, str]],
        threshold: float = 0.8,
    ) -> bool:
        """Determine if the input should be blocked."""
        if not detections:
            return False

        max_score = max(p.severity * conf for p, conf, _ in detections)
        return max_score >= threshold
