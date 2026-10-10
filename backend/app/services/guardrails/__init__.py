"""Security Guardrails for LLM Applications.

Multi-layered security aligned with OWASP LLM Top 10:
- Input validation and sanitization
- Prompt injection detection
- PII detection and redaction
- Secret detection and redaction
- Output content filtering
- Output redaction pipeline
- Rate limiting integration

Usage:
    from app.services.guardrails import GuardrailsService, GuardrailResult

    service = GuardrailsService()

    # Check input
    result = await service.check_input(user_message)
    if not result.passed:
        return result.message

    # Check output
    result = await service.check_output(llm_response)

    # Redact secrets
    from app.services.guardrails import SecretFilter, redact_secrets
    clean_text = redact_secrets(text_with_secrets)

    # Full output redaction
    from app.services.guardrails import OutputRedactor, redact_output
    clean_output = redact_output(llm_response)
"""

from app.services.guardrails.models import (
    GuardrailResult,
    SecurityEvent,
    SecurityEventType,
    ThreatLevel,
    PIIType,
    PIIMatch,
)
from app.services.guardrails.injection import (
    InjectionDetector,
    InjectionPattern,
)
from app.services.guardrails.pii import (
    PIIDetector,
    PIIRedactor,
)
from app.services.guardrails.content_filter import (
    ContentFilter,
    ContentCategory,
)
from app.services.guardrails.secrets import (
    SecretFilter,
    SecretType,
    SecretMatch,
    SecretPattern,
    FilterResult,
    detect_secrets,
    redact_secrets,
    has_secrets,
)
from app.services.guardrails.redactor import (
    OutputRedactor,
    RedactionRule,
    RedactionType,
    RedactionAction,
    RedactionMatch,
    RedactionResult,
    RedactionPipeline,
    redact_output,
    create_default_redactor,
)
from app.services.guardrails.service import (
    GuardrailsService,
    get_guardrails_service,
)
from app.services.guardrails.nemo import (
    NeMoGuardrailsAdapter,
    get_nemo_guardrails_adapter,
)

__all__ = [
    # Models
    "GuardrailResult",
    "SecurityEvent",
    "SecurityEventType",
    "ThreatLevel",
    "PIIType",
    "PIIMatch",
    # Injection Detection
    "InjectionDetector",
    "InjectionPattern",
    # PII
    "PIIDetector",
    "PIIRedactor",
    # Content Filter
    "ContentFilter",
    "ContentCategory",
    # Secret Detection
    "SecretFilter",
    "SecretType",
    "SecretMatch",
    "SecretPattern",
    "FilterResult",
    "detect_secrets",
    "redact_secrets",
    "has_secrets",
    # Output Redaction
    "OutputRedactor",
    "RedactionRule",
    "RedactionType",
    "RedactionAction",
    "RedactionMatch",
    "RedactionResult",
    "RedactionPipeline",
    "redact_output",
    "create_default_redactor",
    # Service
    "GuardrailsService",
    "get_guardrails_service",
    # NeMo integration
    "NeMoGuardrailsAdapter",
    "get_nemo_guardrails_adapter",
]
