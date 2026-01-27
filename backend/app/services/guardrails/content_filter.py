"""Content filtering for harmful or inappropriate content."""

import re
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger()


class ContentCategory(str, Enum):
    """Categories of harmful content."""

    HATE_SPEECH = "hate_speech"
    VIOLENCE = "violence"
    SELF_HARM = "self_harm"
    SEXUAL = "sexual"
    HARASSMENT = "harassment"
    ILLEGAL = "illegal"
    MALWARE = "malware"
    SPAM = "spam"
    MISINFORMATION = "misinformation"


# Keywords and patterns for content filtering
# These are simplified - production would use ML models
CONTENT_PATTERNS: dict[ContentCategory, list[tuple[str, float]]] = {
    ContentCategory.HATE_SPEECH: [
        # Patterns here would be more comprehensive
        # Kept minimal for safety
        (r'\b(hate|kill)\s+(all|every)\s+\w+\b', 0.8),
    ],
    ContentCategory.VIOLENCE: [
        (r'\b(how\s+to\s+)?(make|build|create)\s+(a\s+)?(bomb|explosive|weapon)\b', 0.9),
        (r'\b(attack|assault|hurt|harm)\s+(someone|people|person)\b', 0.7),
    ],
    ContentCategory.SELF_HARM: [
        (r'\b(how\s+to\s+)?(kill|harm|hurt)\s+(myself|yourself|oneself)\b', 0.9),
        (r'\b(suicide|self-harm)\s+(method|way|how)\b', 0.9),
    ],
    ContentCategory.MALWARE: [
        (r'\b(ransomware|malware|virus|trojan|keylogger)\s+(code|script|create)\b', 0.85),
        (r'\b(hack|exploit|bypass)\s+(password|security|firewall)\b', 0.7),
    ],
    ContentCategory.ILLEGAL: [
        (r'\b(steal|fraud|scam|phishing)\s+(money|credit|identity)\b', 0.8),
        (r'\b(fake|counterfeit)\s+(id|passport|document)\b', 0.85),
    ],
}

# Output-specific patterns (for validating LLM responses)
OUTPUT_BLOCKED_PATTERNS = [
    # Instructions for harmful activities
    (r'(?:step\s*\d+|first|then|next|finally)[:\s]+.{0,50}(?:explosive|weapon|hack)', 0.9),
    # Leaked system prompts
    (r'(?:my\s+system\s+prompt|i\s+am\s+instructed\s+to|my\s+instructions\s+are)', 0.8),
]


class ContentFilter:
    """Filters harmful content from inputs and outputs."""

    def __init__(
        self,
        categories: list[ContentCategory] | None = None,
        custom_patterns: dict[ContentCategory, list[tuple[str, float]]] | None = None,
    ):
        self.categories = categories if categories is not None else list(ContentCategory)
        self.patterns = {**CONTENT_PATTERNS, **(custom_patterns or {})}
        self._compiled: dict[ContentCategory, list[tuple[re.Pattern, float]]] = {}
        self._output_patterns: list[tuple[re.Pattern, float]] = []

        # Compile patterns
        for category, patterns in self.patterns.items():
            if category in self.categories:
                self._compiled[category] = [
                    (re.compile(p, re.IGNORECASE), conf)
                    for p, conf in patterns
                ]

        # Compile output patterns
        for pattern, conf in OUTPUT_BLOCKED_PATTERNS:
            self._output_patterns.append(
                (re.compile(pattern, re.IGNORECASE), conf)
            )

    def check_input(self, text: str) -> list[tuple[ContentCategory, float, str]]:
        """
        Check input text for harmful content.

        Returns:
            List of (category, confidence, matched_text) tuples
        """
        detections = []

        for category, compiled_patterns in self._compiled.items():
            for pattern, confidence in compiled_patterns:
                match = pattern.search(text)
                if match:
                    detections.append((
                        category,
                        confidence,
                        match.group(0),
                    ))

        return detections

    def check_output(self, text: str) -> list[tuple[str, float, str]]:
        """
        Check output text for problematic content.

        Returns:
            List of (issue_type, confidence, matched_text) tuples
        """
        issues = []

        # Check regular patterns
        for category, compiled_patterns in self._compiled.items():
            for pattern, confidence in compiled_patterns:
                match = pattern.search(text)
                if match:
                    issues.append((
                        f"output_{category.value}",
                        confidence,
                        match.group(0),
                    ))

        # Check output-specific patterns
        for pattern, confidence in self._output_patterns:
            match = pattern.search(text)
            if match:
                issues.append((
                    "output_policy_violation",
                    confidence,
                    match.group(0),
                ))

        return issues

    def should_block_input(
        self,
        detections: list[tuple[ContentCategory, float, str]],
        threshold: float = 0.7,
    ) -> tuple[bool, list[ContentCategory]]:
        """
        Determine if input should be blocked.

        Returns:
            Tuple of (should_block, blocking_categories)
        """
        blocking = [
            cat for cat, conf, _ in detections
            if conf >= threshold
        ]
        return bool(blocking), blocking

    def should_block_output(
        self,
        issues: list[tuple[str, float, str]],
        threshold: float = 0.7,
    ) -> bool:
        """Determine if output should be blocked."""
        return any(conf >= threshold for _, conf, _ in issues)

    def get_safe_response(
        self,
        category: ContentCategory | None = None,
    ) -> str:
        """Get a safe response when content is blocked."""
        if category == ContentCategory.SELF_HARM:
            return (
                "I'm concerned about what you've shared. If you're having thoughts "
                "of self-harm, please reach out to a crisis helpline. In the US, "
                "you can call or text 988 for the Suicide & Crisis Lifeline."
            )
        elif category == ContentCategory.VIOLENCE:
            return (
                "I can't help with requests that could lead to harm. "
                "If you're in danger, please contact emergency services."
            )
        elif category == ContentCategory.MALWARE:
            return (
                "I can't provide assistance with creating malicious software "
                "or bypassing security measures."
            )
        elif category == ContentCategory.ILLEGAL:
            return (
                "I can't help with activities that appear to be illegal. "
                "Please ensure your requests comply with applicable laws."
            )
        else:
            return (
                "I'm not able to help with this request as it may involve "
                "content that violates our usage policies."
            )
