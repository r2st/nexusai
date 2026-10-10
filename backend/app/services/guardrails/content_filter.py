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
    PRIVACY_VIOLATION = "privacy_violation"
    COPYRIGHT = "copyright"
    TOXICITY = "toxicity"
    PROMPT_INJECTION = "prompt_injection"


# Keywords and patterns for content filtering.
# These are pattern-based heuristics — production deployments should layer
# ML-based classifiers (e.g. OpenAI Moderation, Perspective API) on top.
CONTENT_PATTERNS: dict[ContentCategory, list[tuple[str, float]]] = {
    ContentCategory.HATE_SPEECH: [
        (r'\b(hate|kill)\s+(all|every)\s+\w+\b', 0.8),
        (r'\b(exterminate|eliminate|eradicate)\s+(all|every|the)\s+\w+\b', 0.85),
        (r'\b\w+\s+(are|is)\s+(subhuman|inferior|vermin|parasites?)\b', 0.8),
    ],
    ContentCategory.VIOLENCE: [
        (r'\b(how\s+to\s+)?(make|build|create)\s+(a\s+)?(bomb|explosive|weapon)\b', 0.9),
        (r'\b(attack|assault|hurt|harm)\s+(someone|people|person)\b', 0.7),
        (r'\b(instructions?\s+(?:for|to)\s+(?:poison|murder|kidnap))\b', 0.9),
        (r'\b(synthesiz(?:e|ing)|manufactur(?:e|ing))\s+(?:poison|toxin|nerve\s+agent)\b', 0.95),
    ],
    ContentCategory.SELF_HARM: [
        (r'\b(how\s+to\s+)?(kill|harm|hurt)\s+(myself|yourself|oneself)\b', 0.9),
        (r'\b(suicide|self-harm)\s+(method|way|how)\b', 0.9),
        (r'\b(best\s+way\s+to\s+(?:die|end\s+(?:it|my\s+life)))\b', 0.95),
    ],
    ContentCategory.MALWARE: [
        (r'\b(ransomware|malware|virus|trojan|keylogger)\s+(code|script|create)\b', 0.85),
        (r'\b(hack|exploit|bypass)\s+(password|security|firewall)\b', 0.7),
        (r'\b(write|generate|create)\s+(?:a\s+)?(?:zero[\s-]?day|rootkit|backdoor)\b', 0.9),
        (r'\b(sql\s+injection|xss|cross[\s-]site\s+scripting)\s+(?:payload|attack|exploit)\b', 0.7),
    ],
    ContentCategory.ILLEGAL: [
        (r'\b(steal|fraud|scam|phishing)\s+(money|credit|identity)\b', 0.8),
        (r'\b(fake|counterfeit)\s+(id|passport|document)\b', 0.85),
        (r'\b(money\s+laundering|tax\s+evasion)\s+(how|method|guide)\b', 0.85),
        (r'\b(human\s+trafficking|child\s+exploitation)\b', 0.95),
    ],
    ContentCategory.PRIVACY_VIOLATION: [
        # PII patterns
        (r'\b(?:social\s+security(?:\s+number)?|ssn)\b.{0,20}\d{3}[\s-]?\d{2}[\s-]?\d{4}\b', 0.95),
        (r'\b(?:credit\s+card|cc)\b.{0,20}\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', 0.95),
        (r'\b(dox|doxx|doxing)\s+(someone|person|user|them)\b', 0.85),
        (r'\b(reveal|expose|leak)\s+(?:someone\'?s?\s+)?(?:address|phone|email|identity)\b', 0.7),
    ],
    ContentCategory.COPYRIGHT: [
        (r'\b(reproduce|copy)\s+(?:the\s+)?(?:entire|full|complete)\s+(?:book|article|paper|chapter)\b', 0.75),
        (r'\b(?:pirate|torrent|crack|keygen)\s+(?:software|game|movie|music)\b', 0.8),
    ],
    ContentCategory.TOXICITY: [
        (r'\b(you\s+are\s+(?:an?\s+)?(?:idiot|moron|stupid|worthless|pathetic))\b', 0.7),
        (r'\b(shut\s+up|go\s+(?:away|die)|nobody\s+(?:cares|asked))\b', 0.6),
    ],
    ContentCategory.PROMPT_INJECTION: [
        (r'(?:ignore|disregard|forget)\s+(?:all\s+)?(?:previous|above|prior)\s+(?:instructions?|rules?|prompts?)', 0.9),
        (r'(?:you\s+are\s+now|act\s+as|pretend\s+(?:to\s+be|you\s+are))\s+(?:DAN|jailbreak|unrestricted)', 0.9),
        (r'(?:override|bypass)\s+(?:your\s+)?(?:safety|content|ethical)\s+(?:filters?|guidelines?|rules?)', 0.85),
        (r'(?:system|developer)\s*(?:prompt|message)\s*[:=]', 0.75),
    ],
}

# Output-specific patterns (for validating LLM responses)
OUTPUT_BLOCKED_PATTERNS = [
    # Instructions for harmful activities
    (r'(?:step\s*\d+|first|then|next|finally)[:\s]+.{0,50}(?:explosive|weapon|hack)', 0.9),
    # Leaked system prompts
    (r'(?:my\s+system\s+prompt|i\s+am\s+instructed\s+to|my\s+instructions\s+are)', 0.8),
    (r'(?:here\s+(?:is|are)\s+my\s+(?:system|initial)\s+(?:prompt|instructions?))', 0.85),
    # PII leakage in output
    (r'\b\d{3}[\s-]?\d{2}[\s-]?\d{4}\b', 0.6),  # SSN-like
    (r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', 0.6),  # CC-like
    # Jailbreak acknowledgment
    (r'(?:okay|sure|alright),?\s+(?:i\'?ll|let\s+me)\s+(?:ignore|bypass|disregard)\s+(?:my|the)\s+(?:rules|guidelines|restrictions)', 0.95),
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
        _SAFE_RESPONSES: dict[ContentCategory, str] = {
            ContentCategory.SELF_HARM: (
                "I'm concerned about what you've shared. If you're having thoughts "
                "of self-harm, please reach out to a crisis helpline. In the US, "
                "you can call or text 988 for the Suicide & Crisis Lifeline."
            ),
            ContentCategory.VIOLENCE: (
                "I can't help with requests that could lead to harm. "
                "If you're in danger, please contact emergency services."
            ),
            ContentCategory.MALWARE: (
                "I can't provide assistance with creating malicious software "
                "or bypassing security measures."
            ),
            ContentCategory.ILLEGAL: (
                "I can't help with activities that appear to be illegal. "
                "Please ensure your requests comply with applicable laws."
            ),
            ContentCategory.PRIVACY_VIOLATION: (
                "I can't help with requests that could violate someone's privacy "
                "or expose personal information."
            ),
            ContentCategory.COPYRIGHT: (
                "I can't reproduce copyrighted content in its entirety. "
                "I can summarize or discuss the material instead."
            ),
            ContentCategory.TOXICITY: (
                "Let's keep our conversation respectful and constructive."
            ),
            ContentCategory.PROMPT_INJECTION: (
                "I've detected a prompt injection attempt. My safety guidelines "
                "remain in effect regardless of instructions within the input."
            ),
            ContentCategory.HATE_SPEECH: (
                "I can't engage with content that promotes hatred or "
                "discrimination against any group."
            ),
        }

        if category and category in _SAFE_RESPONSES:
            return _SAFE_RESPONSES[category]

        return (
            "I'm not able to help with this request as it may involve "
            "content that violates our usage policies."
        )
