"""
Output Redactor Service

Comprehensive output redaction before returning to users:
- PII redaction
- Secret redaction
- Custom pattern redaction
- Audit logging
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
import re
import logging
import hashlib
import uuid

logger = logging.getLogger(__name__)


class RedactionType(str, Enum):
    """Types of redaction."""
    PII = "pii"
    SECRET = "secret"
    CUSTOM = "custom"
    PROFANITY = "profanity"
    INTERNAL = "internal"  # Internal system info


class RedactionAction(str, Enum):
    """What to do with detected content."""
    REDACT = "redact"  # Replace with placeholder
    MASK = "mask"  # Partial masking (e.g., email@****.com)
    HASH = "hash"  # Replace with hash
    REMOVE = "remove"  # Remove entirely
    WARN = "warn"  # Keep but log warning


@dataclass
class RedactionRule:
    """A rule for detecting and redacting content."""
    id: str
    name: str
    type: RedactionType
    pattern: re.Pattern
    action: RedactionAction = RedactionAction.REDACT
    replacement: str = "[REDACTED]"
    
    # Conditions
    enabled: bool = True
    min_confidence: float = 0.8
    
    # For masking
    mask_char: str = "*"
    mask_keep_start: int = 0
    mask_keep_end: int = 0
    
    # Custom handler
    handler: Optional[Callable[[str, re.Match], str]] = None
    
    # Audit
    log_matches: bool = True


@dataclass
class RedactionMatch:
    """A detected redaction match."""
    rule_id: str
    rule_name: str
    type: RedactionType
    original_value: str
    redacted_value: str
    start: int
    end: int
    
    # Audit
    value_hash: str = ""
    
    def __post_init__(self):
        if not self.value_hash:
            self.value_hash = hashlib.sha256(self.original_value.encode()).hexdigest()[:16]


@dataclass
class RedactionResult:
    """Result of redaction."""
    original_text: str
    redacted_text: str
    matches: List[RedactionMatch] = field(default_factory=list)
    
    # Metadata
    redaction_count: int = 0
    processing_time_ms: float = 0
    
    @property
    def was_modified(self) -> bool:
        return self.redaction_count > 0
    
    def to_audit_log(self) -> Dict[str, Any]:
        """Generate audit log entry."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "redaction_count": self.redaction_count,
            "types_redacted": list(set(m.type.value for m in self.matches)),
            "rules_triggered": list(set(m.rule_id for m in self.matches)),
            "matches": [
                {
                    "rule_id": m.rule_id,
                    "type": m.type.value,
                    "value_hash": m.value_hash,
                    "position": f"{m.start}-{m.end}",
                }
                for m in self.matches
            ],
        }


class OutputRedactor:
    """
    Comprehensive output redaction service.
    
    Features:
    - Multiple redaction strategies
    - Configurable rules
    - Audit logging
    - Performance optimization
    """
    
    # Built-in PII patterns
    PII_RULES: List[RedactionRule] = [
        RedactionRule(
            id="email",
            name="Email Address",
            type=RedactionType.PII,
            pattern=re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
            action=RedactionAction.MASK,
            mask_keep_start=2,
            mask_keep_end=4,
        ),
        RedactionRule(
            id="phone_us",
            name="US Phone Number",
            type=RedactionType.PII,
            pattern=re.compile(r'(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'),
            action=RedactionAction.REDACT,
            replacement="[PHONE]",
        ),
        RedactionRule(
            id="ssn",
            name="Social Security Number",
            type=RedactionType.PII,
            pattern=re.compile(r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b'),
            action=RedactionAction.REDACT,
            replacement="[SSN]",
        ),
        RedactionRule(
            id="credit_card",
            name="Credit Card Number",
            type=RedactionType.PII,
            pattern=re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
            action=RedactionAction.MASK,
            mask_keep_end=4,
        ),
        RedactionRule(
            id="ip_address",
            name="IP Address",
            type=RedactionType.PII,
            pattern=re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
            action=RedactionAction.REDACT,
            replacement="[IP]",
        ),
        RedactionRule(
            id="date_of_birth",
            name="Date of Birth Pattern",
            type=RedactionType.PII,
            pattern=re.compile(r'(?i)(?:dob|date of birth|born|birthday)[:\s]+\d{1,2}[-/]\d{1,2}[-/]\d{2,4}'),
            action=RedactionAction.REDACT,
            replacement="[DOB REDACTED]",
        ),
    ]
    
    # Built-in internal info patterns
    INTERNAL_RULES: List[RedactionRule] = [
        RedactionRule(
            id="internal_path",
            name="Internal File Path",
            type=RedactionType.INTERNAL,
            pattern=re.compile(r'/(?:home|Users|var|etc|opt)/[^\s]+'),
            action=RedactionAction.REDACT,
            replacement="[PATH]",
        ),
        RedactionRule(
            id="stack_trace",
            name="Stack Trace",
            type=RedactionType.INTERNAL,
            pattern=re.compile(r'(?:Traceback|at [a-zA-Z0-9_.]+\([^)]+\):|File "[^"]+", line \d+)'),
            action=RedactionAction.WARN,
        ),
        RedactionRule(
            id="internal_url",
            name="Internal URL",
            type=RedactionType.INTERNAL,
            pattern=re.compile(r'https?://(?:localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+)[^\s]*'),
            action=RedactionAction.REDACT,
            replacement="[INTERNAL_URL]",
        ),
    ]
    
    def __init__(
        self,
        rules: Optional[List[RedactionRule]] = None,
        enable_pii: bool = True,
        enable_secrets: bool = True,
        enable_internal: bool = True,
        custom_rules: Optional[List[RedactionRule]] = None,
        secret_filter: Optional[Any] = None,
        audit_logger: Optional[Callable[[Dict], None]] = None,
    ):
        """
        Initialize the output redactor.
        
        Args:
            rules: Override all rules
            enable_pii: Include PII detection
            enable_secrets: Include secret detection
            enable_internal: Include internal info detection
            custom_rules: Additional rules
            secret_filter: SecretFilter instance for secret detection
            audit_logger: Callback for audit logging
        """
        if rules is not None:
            self.rules = rules
        else:
            self.rules = []
            if enable_pii:
                self.rules.extend(self.PII_RULES)
            if enable_internal:
                self.rules.extend(self.INTERNAL_RULES)
        
        if custom_rules:
            self.rules.extend(custom_rules)
        
        self.secret_filter = secret_filter
        self.audit_logger = audit_logger
    
    def redact(
        self,
        text: str,
        types: Optional[Set[RedactionType]] = None,
        rules: Optional[Set[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> RedactionResult:
        """
        Redact sensitive content from text.
        
        Args:
            text: Text to redact
            types: Specific types to redact (None = all)
            rules: Specific rule IDs to apply (None = all)
            context: Additional context for audit
            
        Returns:
            RedactionResult with redacted text and matches
        """
        import time
        start_time = time.time()
        
        result = RedactionResult(original_text=text, redacted_text=text)
        
        # Track matched positions to avoid double-redaction
        matched_positions: List[tuple[int, int]] = []
        
        # Apply rules
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            if types and rule.type not in types:
                continue
            
            if rules and rule.id not in rules:
                continue
            
            # Find matches
            for match in rule.pattern.finditer(text):
                start, end = match.start(), match.end()
                
                # Skip if overlaps with existing match
                if any(self._overlaps((start, end), pos) for pos in matched_positions):
                    continue
                
                original_value = match.group(0)
                
                # Determine redacted value
                if rule.handler:
                    redacted_value = rule.handler(original_value, match)
                else:
                    redacted_value = self._apply_action(original_value, rule)
                
                # Record match
                redaction_match = RedactionMatch(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    type=rule.type,
                    original_value=original_value,
                    redacted_value=redacted_value,
                    start=start,
                    end=end,
                )
                
                result.matches.append(redaction_match)
                matched_positions.append((start, end))
        
        # Apply secret filter if enabled
        if self.secret_filter:
            from .secrets import SecretFilter
            if isinstance(self.secret_filter, SecretFilter):
                secret_result = self.secret_filter.filter(text, redact=False)
                
                for secret in secret_result.secrets_found:
                    # Skip if overlaps
                    if any(self._overlaps((secret.start, secret.end), pos) for pos in matched_positions):
                        continue
                    
                    redaction_match = RedactionMatch(
                        rule_id=f"secret_{secret.type.value}",
                        rule_name=f"Secret: {secret.type.value}",
                        type=RedactionType.SECRET,
                        original_value=secret.value,
                        redacted_value=f"[REDACTED:{secret.type.value}]",
                        start=secret.start,
                        end=secret.end,
                        value_hash=secret.value_hash,
                    )
                    
                    result.matches.append(redaction_match)
                    matched_positions.append((secret.start, secret.end))
        
        # Sort matches by position (descending for replacement)
        result.matches.sort(key=lambda m: m.start, reverse=True)
        
        # Apply redactions to text
        redacted_text = text
        for match in result.matches:
            if match.redacted_value != match.original_value:
                redacted_text = (
                    redacted_text[:match.start] +
                    match.redacted_value +
                    redacted_text[match.end:]
                )
        
        result.redacted_text = redacted_text
        result.redaction_count = sum(
            1 for m in result.matches
            if m.redacted_value != m.original_value
        )
        
        result.processing_time_ms = (time.time() - start_time) * 1000
        
        # Audit logging
        if self.audit_logger and result.was_modified:
            audit_entry = result.to_audit_log()
            if context:
                audit_entry["context"] = context
            self.audit_logger(audit_entry)
        
        # Re-sort matches by position (ascending for output)
        result.matches.sort(key=lambda m: m.start)
        
        return result
    
    def _apply_action(self, value: str, rule: RedactionRule) -> str:
        """Apply redaction action to a value."""
        if rule.action == RedactionAction.REDACT:
            return rule.replacement
        
        elif rule.action == RedactionAction.MASK:
            return self._mask_value(
                value,
                rule.mask_char,
                rule.mask_keep_start,
                rule.mask_keep_end,
            )
        
        elif rule.action == RedactionAction.HASH:
            hash_val = hashlib.sha256(value.encode()).hexdigest()[:12]
            return f"[HASH:{hash_val}]"
        
        elif rule.action == RedactionAction.REMOVE:
            return ""
        
        elif rule.action == RedactionAction.WARN:
            return value  # Keep original, just log
        
        return rule.replacement
    
    def _mask_value(
        self,
        value: str,
        mask_char: str,
        keep_start: int,
        keep_end: int,
    ) -> str:
        """Mask a value keeping some characters visible."""
        if len(value) <= keep_start + keep_end:
            return mask_char * len(value)
        
        start_part = value[:keep_start] if keep_start > 0 else ""
        end_part = value[-keep_end:] if keep_end > 0 else ""
        middle_len = len(value) - keep_start - keep_end
        
        return start_part + (mask_char * middle_len) + end_part
    
    def _overlaps(self, range1: tuple[int, int], range2: tuple[int, int]) -> bool:
        """Check if two ranges overlap."""
        return range1[0] < range2[1] and range2[0] < range1[1]
    
    def add_rule(self, rule: RedactionRule) -> None:
        """Add a custom redaction rule."""
        self.rules.append(rule)
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule by ID."""
        for i, rule in enumerate(self.rules):
            if rule.id == rule_id:
                del self.rules[i]
                return True
        return False
    
    def enable_rule(self, rule_id: str) -> bool:
        """Enable a rule."""
        for rule in self.rules:
            if rule.id == rule_id:
                rule.enabled = True
                return True
        return False
    
    def disable_rule(self, rule_id: str) -> bool:
        """Disable a rule."""
        for rule in self.rules:
            if rule.id == rule_id:
                rule.enabled = False
                return True
        return False


class RedactionPipeline:
    """
    Pipeline for applying multiple redactors in sequence.
    """
    
    def __init__(self):
        self.stages: List[tuple[str, OutputRedactor]] = []
    
    def add_stage(self, name: str, redactor: OutputRedactor) -> "RedactionPipeline":
        """Add a redaction stage."""
        self.stages.append((name, redactor))
        return self
    
    def process(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> tuple[str, Dict[str, RedactionResult]]:
        """
        Process text through all stages.
        
        Returns:
            Tuple of (final_text, results_by_stage)
        """
        current_text = text
        results: Dict[str, RedactionResult] = {}
        
        for stage_name, redactor in self.stages:
            result = redactor.redact(current_text, context=context)
            results[stage_name] = result
            current_text = result.redacted_text
        
        return current_text, results


# Convenience functions
def redact_output(
    text: str,
    enable_pii: bool = True,
    enable_secrets: bool = True,
) -> str:
    """
    Redact sensitive content from output text.
    
    Args:
        text: Text to redact
        enable_pii: Redact PII
        enable_secrets: Redact secrets
        
    Returns:
        Redacted text
    """
    from .secrets import SecretFilter
    
    secret_filter = SecretFilter() if enable_secrets else None
    
    redactor = OutputRedactor(
        enable_pii=enable_pii,
        enable_secrets=enable_secrets,
        secret_filter=secret_filter,
    )
    
    result = redactor.redact(text)
    return result.redacted_text


def create_default_redactor() -> OutputRedactor:
    """Create a redactor with default settings."""
    from .secrets import SecretFilter
    
    return OutputRedactor(
        enable_pii=True,
        enable_secrets=True,
        enable_internal=True,
        secret_filter=SecretFilter(),
    )
