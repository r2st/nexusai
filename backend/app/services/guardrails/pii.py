"""PII (Personally Identifiable Information) detection and redaction."""

import re

import structlog

from app.services.guardrails.models import PIIMatch, PIIType

logger = structlog.get_logger()


# Regex patterns for PII detection
PII_PATTERNS: dict[PIIType, list[tuple[str, float]]] = {
    PIIType.EMAIL: [
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 0.95),
    ],
    PIIType.PHONE: [
        # US phone formats
        (r'\b(?:\+1[-.]?)?\(?[0-9]{3}\)?[-.]?[0-9]{3}[-.]?[0-9]{4}\b', 0.9),
        # International
        (r'\b\+[0-9]{1,3}[-.]?[0-9]{1,4}[-.]?[0-9]{1,4}[-.]?[0-9]{1,9}\b', 0.85),
    ],
    PIIType.SSN: [
        (r'\b[0-9]{3}[-]?[0-9]{2}[-]?[0-9]{4}\b', 0.9),
    ],
    PIIType.CREDIT_CARD: [
        # Major card patterns
        (r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9][0-9])[0-9]{12})\b', 0.95),
        # With separators
        (r'\b(?:4[0-9]{3}|5[1-5][0-9]{2}|3[47][0-9]{2}|6(?:011|5[0-9]{2}))[-\s]?[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}\b', 0.95),
    ],
    PIIType.IP_ADDRESS: [
        # IPv4
        (r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b', 0.9),
        # IPv6 (simplified)
        (r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b', 0.9),
    ],
    PIIType.API_KEY: [
        # Common API key patterns
        (r'\b(?:sk|pk|api|key)[-_]?[a-zA-Z0-9]{20,}\b', 0.85),
        # OpenAI
        (r'\bsk-[a-zA-Z0-9]{40,}\b', 0.95),
        # GitHub token
        (r'\b(?:ghp|gho|ghu|ghs|ghr)_[a-zA-Z0-9]{36,}\b', 0.95),
        # AWS
        (r'\bAKIA[0-9A-Z]{16}\b', 0.95),
    ],
    PIIType.PASSWORD: [
        # Password in context
        (r'(?:password|passwd|pwd)[\s:=]+["\']?([^\s"\']{8,})["\']?', 0.8),
    ],
    PIIType.DATE_OF_BIRTH: [
        # Various date formats
        (r'\b(?:0?[1-9]|1[0-2])[/.-](?:0?[1-9]|[12][0-9]|3[01])[/.-](?:19|20)[0-9]{2}\b', 0.7),
        (r'\b(?:19|20)[0-9]{2}[/.-](?:0?[1-9]|1[0-2])[/.-](?:0?[1-9]|[12][0-9]|3[01])\b', 0.7),
    ],
    PIIType.PASSPORT: [
        # US Passport
        (r'\b[0-9]{9}\b', 0.5),  # Low confidence, needs context
    ],
    PIIType.BANK_ACCOUNT: [
        # Routing + Account
        (r'\b[0-9]{9}\s+[0-9]{10,17}\b', 0.8),
        # IBAN
        (r'\b[A-Z]{2}[0-9]{2}[A-Z0-9]{4}[0-9]{7}([A-Z0-9]?){0,16}\b', 0.9),
    ],
}


class PIIDetector:
    """Detects PII in text."""

    def __init__(
        self,
        types_to_detect: list[PIIType] | None = None,
        custom_patterns: dict[PIIType, list[tuple[str, float]]] | None = None,
    ):
        self.types_to_detect = types_to_detect if types_to_detect is not None else list(PIIType)
        self.patterns = {**PII_PATTERNS, **(custom_patterns or {})}
        self._compiled: dict[PIIType, list[tuple[re.Pattern, float]]] = {}

        # Compile patterns
        for pii_type, patterns in self.patterns.items():
            if pii_type in self.types_to_detect:
                self._compiled[pii_type] = [
                    (re.compile(p, re.IGNORECASE), conf)
                    for p, conf in patterns
                ]

    def detect(self, text: str) -> list[PIIMatch]:
        """
        Detect PII in text.

        Returns:
            List of PIIMatch objects
        """
        matches = []

        for pii_type, compiled_patterns in self._compiled.items():
            for pattern, base_confidence in compiled_patterns:
                for match in pattern.finditer(text):
                    # Adjust confidence based on context
                    confidence = self._adjust_confidence(
                        pii_type, match.group(0), text, base_confidence
                    )

                    if confidence > 0.5:  # Minimum threshold
                        matches.append(PIIMatch(
                            type=pii_type,
                            value=match.group(0),
                            start=match.start(),
                            end=match.end(),
                            confidence=confidence,
                        ))

        # Remove overlapping matches (keep highest confidence)
        matches = self._remove_overlaps(matches)

        return matches

    def _adjust_confidence(
        self,
        pii_type: PIIType,
        value: str,
        context: str,
        base_confidence: float,
    ) -> float:
        """Adjust confidence based on context."""
        confidence = base_confidence

        # Context keywords that increase confidence
        context_lower = context.lower()

        if pii_type == PIIType.PHONE:
            if any(kw in context_lower for kw in ["phone", "call", "mobile", "cell", "tel"]):
                confidence *= 1.1

        elif pii_type == PIIType.EMAIL:
            if any(kw in context_lower for kw in ["email", "mail", "contact"]):
                confidence *= 1.1

        elif pii_type == PIIType.SSN:
            if any(kw in context_lower for kw in ["ssn", "social security", "social"]):
                confidence *= 1.2
            else:
                confidence *= 0.7  # Lower if no context

        elif pii_type == PIIType.CREDIT_CARD:
            if any(kw in context_lower for kw in ["card", "credit", "payment", "visa", "mastercard"]):
                confidence *= 1.1
            # Validate Luhn algorithm for higher confidence
            if self._validate_credit_card(value):
                confidence *= 1.1

        elif pii_type == PIIType.API_KEY:
            if any(kw in context_lower for kw in ["key", "token", "api", "secret"]):
                confidence *= 1.1

        return min(confidence, 1.0)

    def _validate_credit_card(self, number: str) -> bool:
        """Validate credit card using Luhn algorithm."""
        digits = [int(d) for d in re.sub(r'\D', '', number)]
        if len(digits) < 13 or len(digits) > 19:
            return False

        checksum = 0
        for i, d in enumerate(reversed(digits)):
            if i % 2 == 1:
                d *= 2
                if d > 9:
                    d -= 9
            checksum += d

        return checksum % 10 == 0

    def _remove_overlaps(self, matches: list[PIIMatch]) -> list[PIIMatch]:
        """Remove overlapping matches, keeping highest confidence."""
        if not matches:
            return []

        # Sort by start position, then by confidence (descending)
        sorted_matches = sorted(
            matches,
            key=lambda m: (m.start, -m.confidence)
        )

        result = []
        last_end = -1

        for match in sorted_matches:
            if match.start >= last_end:
                result.append(match)
                last_end = match.end
            elif match.confidence > result[-1].confidence:
                # Replace if higher confidence
                result[-1] = match
                last_end = match.end

        return result


class PIIRedactor:
    """Redacts PII from text."""

    # Redaction formats per PII type
    REDACTION_FORMATS: dict[PIIType, str] = {
        PIIType.EMAIL: "[EMAIL]",
        PIIType.PHONE: "[PHONE]",
        PIIType.SSN: "[SSN]",
        PIIType.CREDIT_CARD: "[CREDIT_CARD]",
        PIIType.IP_ADDRESS: "[IP_ADDRESS]",
        PIIType.NAME: "[NAME]",
        PIIType.ADDRESS: "[ADDRESS]",
        PIIType.DATE_OF_BIRTH: "[DOB]",
        PIIType.PASSPORT: "[PASSPORT]",
        PIIType.DRIVER_LICENSE: "[LICENSE]",
        PIIType.BANK_ACCOUNT: "[BANK_ACCOUNT]",
        PIIType.API_KEY: "[API_KEY]",
        PIIType.PASSWORD: "[PASSWORD]",
    }

    def __init__(self, partial_redact: bool = False):
        """
        Initialize redactor.

        Args:
            partial_redact: If True, show partial values (e.g., ***-**-1234 for SSN)
        """
        self.partial_redact = partial_redact

    def redact(
        self,
        text: str,
        matches: list[PIIMatch],
    ) -> tuple[str, list[PIIMatch]]:
        """
        Redact PII from text.

        Returns:
            Tuple of (redacted_text, updated_matches)
        """
        if not matches:
            return text, matches

        # Sort by position (reverse order for replacement)
        sorted_matches = sorted(matches, key=lambda m: m.start, reverse=True)
        redacted = text
        updated_matches = []

        for match in sorted_matches:
            redaction = self._get_redaction(match)
            redacted = redacted[:match.start] + redaction + redacted[match.end:]

            updated_match = match.copy()
            updated_match.redacted = redaction
            updated_matches.append(updated_match)

        # Reverse to maintain original order
        updated_matches.reverse()

        return redacted, updated_matches

    def _get_redaction(self, match: PIIMatch) -> str:
        """Get redaction string for a match."""
        if self.partial_redact:
            return self._partial_redact(match)
        return self.REDACTION_FORMATS.get(match.type, "[REDACTED]")

    def _partial_redact(self, match: PIIMatch) -> str:
        """Create a partial redaction showing some of the value."""
        value = match.value

        if match.type == PIIType.EMAIL:
            parts = value.split("@")
            if len(parts) == 2:
                return f"{parts[0][0]}***@{parts[1]}"

        elif match.type == PIIType.PHONE:
            digits = re.sub(r'\D', '', value)
            if len(digits) >= 4:
                return f"***-***-{digits[-4:]}"

        elif match.type == PIIType.SSN:
            digits = re.sub(r'\D', '', value)
            if len(digits) >= 4:
                return f"***-**-{digits[-4:]}"

        elif match.type == PIIType.CREDIT_CARD:
            digits = re.sub(r'\D', '', value)
            if len(digits) >= 4:
                return f"****-****-****-{digits[-4:]}"

        elif match.type == PIIType.API_KEY:
            if len(value) > 8:
                return f"{value[:4]}...{value[-4:]}"

        return self.REDACTION_FORMATS.get(match.type, "[REDACTED]")
