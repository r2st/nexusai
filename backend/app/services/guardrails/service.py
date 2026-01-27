"""Main guardrails service."""

import time
from typing import Any

import structlog

from app.services.guardrails.models import (
    GuardrailConfig,
    GuardrailResult,
    PIIMatch,
    SecurityEvent,
    SecurityEventType,
    ThreatLevel,
)
from app.services.guardrails.injection import InjectionDetector
from app.services.guardrails.pii import PIIDetector, PIIRedactor
from app.services.guardrails.content_filter import ContentCategory, ContentFilter

logger = structlog.get_logger()


class GuardrailsService:
    """
    Comprehensive guardrails service for LLM security.

    Provides:
    - Input validation and sanitization
    - Prompt injection detection
    - PII detection and redaction
    - Content filtering
    - Output validation
    """

    def __init__(self, config: GuardrailConfig | None = None):
        self.config = config or GuardrailConfig()

        # Initialize components
        self.injection_detector = InjectionDetector()
        self.pii_detector = PIIDetector(
            types_to_detect=self.config.pii_types_to_detect
        )
        self.pii_redactor = PIIRedactor(partial_redact=False)
        self.content_filter = ContentFilter()

        # Event log (in production, this would go to a database)
        self._events: list[SecurityEvent] = []

    async def check_input(
        self,
        text: str,
        user_id: str | None = None,
        tenant_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> GuardrailResult:
        """
        Check user input for security issues.

        This should be called before sending user input to the LLM.
        """
        start_time = time.time()
        result = GuardrailResult(original_content=text)
        current_text = text

        # 1. Check for prompt injection
        if self.config.enable_injection_detection:
            injection_result = self._check_injection(text, user_id, tenant_id)
            if injection_result.blocked:
                injection_result.check_time_ms = (time.time() - start_time) * 1000
                return injection_result

            if injection_result.threats_detected:
                result.threats_detected.extend(injection_result.threats_detected)
                result.threat_level = injection_result.threat_level
                result.events.extend(injection_result.events)

        # 2. Check for harmful content
        if self.config.enable_content_filter:
            content_result = self._check_content(text, user_id, tenant_id)
            if content_result.blocked:
                content_result.check_time_ms = (time.time() - start_time) * 1000
                return content_result

            result.events.extend(content_result.events)

        # 3. Detect and optionally redact PII
        if self.config.enable_pii_detection:
            pii_matches = self.pii_detector.detect(text)

            if pii_matches:
                result.pii_detected = pii_matches

                if self.config.auto_redact_pii:
                    current_text, updated_matches = self.pii_redactor.redact(
                        current_text, pii_matches
                    )
                    result.pii_detected = updated_matches
                    result.pii_redacted = True
                    result.modified = True
                    result.modified_content = current_text

                # Log PII detection
                self._log_event(
                    SecurityEventType.PII_DETECTED,
                    ThreatLevel.MEDIUM,
                    f"Detected {len(pii_matches)} PII items",
                    user_id,
                    tenant_id,
                    {"pii_types": [m.type.value for m in pii_matches]},
                )
                result.events.append(self._events[-1])

        result.check_time_ms = (time.time() - start_time) * 1000
        return result

    async def check_output(
        self,
        text: str,
        user_id: str | None = None,
        tenant_id: str | None = None,
    ) -> GuardrailResult:
        """
        Check LLM output for security issues.

        This should be called before returning LLM output to the user.
        """
        start_time = time.time()
        result = GuardrailResult(original_content=text)

        # 1. Check for harmful content in output
        if self.config.enable_content_filter:
            issues = self.content_filter.check_output(text)

            if self.content_filter.should_block_output(issues):
                result.passed = False
                result.blocked = True
                result.threat_level = ThreatLevel.HIGH
                result.message = (
                    "Response blocked due to potentially harmful content."
                )

                self._log_event(
                    SecurityEventType.HARMFUL_CONTENT,
                    ThreatLevel.HIGH,
                    f"Blocked output with issues: {[i[0] for i in issues]}",
                    user_id,
                    tenant_id,
                    {"issues": [(i[0], i[2]) for i in issues]},
                    blocked=True,
                )
                result.events.append(self._events[-1])

                result.check_time_ms = (time.time() - start_time) * 1000
                return result

        # 2. Check for PII leakage
        if self.config.enable_pii_detection:
            pii_matches = self.pii_detector.detect(text)

            if pii_matches:
                # Always redact PII in output
                current_text, updated_matches = self.pii_redactor.redact(
                    text, pii_matches
                )
                result.pii_detected = updated_matches
                result.pii_redacted = True
                result.modified = True
                result.modified_content = current_text

                self._log_event(
                    SecurityEventType.DATA_EXFILTRATION,
                    ThreatLevel.HIGH,
                    f"Redacted {len(pii_matches)} PII items from output",
                    user_id,
                    tenant_id,
                    {"pii_types": [m.type.value for m in pii_matches]},
                )
                result.events.append(self._events[-1])

        # 3. Validate output length
        if self.config.enable_output_validation:
            if len(text) > self.config.max_output_length:
                result.modified = True
                result.modified_content = (
                    text[: self.config.max_output_length] + "... [truncated]"
                )

        result.check_time_ms = (time.time() - start_time) * 1000
        return result

    def _check_injection(
        self,
        text: str,
        user_id: str | None,
        tenant_id: str | None,
    ) -> GuardrailResult:
        """Check for prompt injection."""
        result = GuardrailResult(original_content=text)

        detections = self.injection_detector.detect(text)

        if not detections:
            return result

        # Get threat level
        threat_str, max_score = self.injection_detector.get_threat_level(detections)
        result.threat_level = ThreatLevel(threat_str)
        result.threats_detected = [f"{d[0].name}: {d[2]}" for d in detections]

        # Check if should block
        if self.injection_detector.should_block(
            detections, self.config.injection_block_threshold
        ):
            result.passed = False
            result.blocked = True
            result.message = (
                "Your message was blocked because it appears to contain "
                "an attempt to manipulate the AI system."
            )

            self._log_event(
                SecurityEventType.PROMPT_INJECTION,
                result.threat_level,
                f"Blocked injection attempt: {detections[0][0].name}",
                user_id,
                tenant_id,
                {
                    "patterns": [d[0].name for d in detections],
                    "max_score": max_score,
                },
                blocked=True,
                original_content=text,
            )
            result.events.append(self._events[-1])
        else:
            # Log but don't block
            self._log_event(
                SecurityEventType.PROMPT_INJECTION,
                result.threat_level,
                f"Detected potential injection: {detections[0][0].name}",
                user_id,
                tenant_id,
                {
                    "patterns": [d[0].name for d in detections],
                    "max_score": max_score,
                },
            )
            result.events.append(self._events[-1])

        return result

    def _check_content(
        self,
        text: str,
        user_id: str | None,
        tenant_id: str | None,
    ) -> GuardrailResult:
        """Check for harmful content."""
        result = GuardrailResult(original_content=text)

        detections = self.content_filter.check_input(text)

        if not detections:
            return result

        should_block, blocking_categories = self.content_filter.should_block_input(
            detections
        )

        if should_block and self.config.block_harmful_content:
            result.passed = False
            result.blocked = True
            result.threat_level = ThreatLevel.CRITICAL

            # Get appropriate response
            main_category = blocking_categories[0] if blocking_categories else None
            result.message = self.content_filter.get_safe_response(main_category)

            self._log_event(
                SecurityEventType.HARMFUL_CONTENT,
                ThreatLevel.CRITICAL,
                f"Blocked harmful content: {[c.value for c in blocking_categories]}",
                user_id,
                tenant_id,
                {"categories": [c.value for c in blocking_categories]},
                blocked=True,
                original_content=text if self.config.log_blocked_content else None,
            )
            result.events.append(self._events[-1])

        return result

    def _log_event(
        self,
        event_type: SecurityEventType,
        threat_level: ThreatLevel,
        description: str,
        user_id: str | None = None,
        tenant_id: str | None = None,
        details: dict[str, Any] | None = None,
        blocked: bool = False,
        original_content: str | None = None,
    ):
        """Log a security event."""
        event = SecurityEvent(
            event_type=event_type,
            threat_level=threat_level,
            user_id=user_id,
            tenant_id=tenant_id,
            description=description,
            details=details or {},
            blocked=blocked,
            original_content=original_content,
        )

        self._events.append(event)

        # Also log to structured logger
        logger.warning(
            "Security event",
            event_type=event_type.value,
            threat_level=threat_level.value,
            user_id=user_id,
            blocked=blocked,
            description=description,
        )

    def get_recent_events(
        self,
        limit: int = 100,
        user_id: str | None = None,
        threat_level: ThreatLevel | None = None,
    ) -> list[SecurityEvent]:
        """Get recent security events."""
        events = self._events

        if user_id:
            events = [e for e in events if e.user_id == user_id]

        if threat_level:
            events = [e for e in events if e.threat_level == threat_level]

        return events[-limit:]


# Global instance
_guardrails_service: GuardrailsService | None = None


def get_guardrails_service() -> GuardrailsService:
    """Get the global guardrails service."""
    global _guardrails_service
    if _guardrails_service is None:
        _guardrails_service = GuardrailsService()
    return _guardrails_service
