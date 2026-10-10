"""Guardrails data models."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ThreatLevel(str, Enum):
    """Threat level classification."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityEventType(str, Enum):
    """Types of security events."""

    PROMPT_INJECTION = "prompt_injection"
    PII_DETECTED = "pii_detected"
    HARMFUL_CONTENT = "harmful_content"
    RATE_LIMIT = "rate_limit"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    DATA_EXFILTRATION = "data_exfiltration"
    JAILBREAK_ATTEMPT = "jailbreak_attempt"
    POLICY_VIOLATION = "policy_violation"


class PIIType(str, Enum):
    """Types of PII that can be detected."""

    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"
    NAME = "name"
    ADDRESS = "address"
    DATE_OF_BIRTH = "date_of_birth"
    PASSPORT = "passport"
    DRIVER_LICENSE = "driver_license"
    BANK_ACCOUNT = "bank_account"
    API_KEY = "api_key"
    PASSWORD = "password"


class PIIMatch(BaseModel):
    """A detected PII match."""

    type: PIIType
    value: str
    start: int
    end: int
    confidence: float = 1.0
    redacted: str | None = None  # Redacted version


class SecurityEvent(BaseModel):
    """A security event for logging."""

    event_type: SecurityEventType
    threat_level: ThreatLevel
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: str | None = None
    tenant_id: str | None = None
    description: str
    details: dict[str, Any] = Field(default_factory=dict)
    blocked: bool = False
    original_content: str | None = None  # For audit


class GuardrailResult(BaseModel):
    """Result of a guardrail check."""

    passed: bool = True
    blocked: bool = False
    modified: bool = False

    # Original and potentially modified content
    original_content: str | None = None
    modified_content: str | None = None

    # Threat assessment
    threat_level: ThreatLevel = ThreatLevel.NONE
    threats_detected: list[str] = Field(default_factory=list)

    # PII
    pii_detected: list[PIIMatch] = Field(default_factory=list)
    pii_redacted: bool = False

    # Events
    events: list[SecurityEvent] = Field(default_factory=list)

    # User message
    message: str | None = None

    # Processing time
    check_time_ms: float = 0.0


class GuardrailConfig(BaseModel):
    """Configuration for guardrails."""

    # Injection detection
    enable_injection_detection: bool = True
    injection_block_threshold: float = 0.8

    # PII detection
    enable_pii_detection: bool = True
    pii_types_to_detect: list[PIIType] = Field(
        default_factory=lambda: list(PIIType)
    )
    auto_redact_pii: bool = True

    # Content filtering
    enable_content_filter: bool = True
    block_harmful_content: bool = True

    # Output validation
    enable_output_validation: bool = True
    max_output_length: int = 100000

    # Logging
    log_all_events: bool = True
    log_blocked_content: bool = True

    # Contextual allowlists (to reduce false positives in docs/training examples)
    allowlist_enabled: bool = True
    allowlist_phrases: list[str] = Field(
        default_factory=lambda: [
            "for documentation",
            "as an example",
            "security training",
            "quoted text",
            "example payload",
            "red team exercise",
        ]
    )
    allowlist_context_keywords: list[str] = Field(
        default_factory=lambda: [
            "example",
            "documentation",
            "docs",
            "quoted",
            "tutorial",
            "training",
            "test case",
        ]
    )
    allowlist_regex_patterns: list[str] = Field(default_factory=list)

    # NeMo Guardrails integration (optional)
    enable_nemo_guardrails: bool = False
    nemo_config_path: str | None = None
