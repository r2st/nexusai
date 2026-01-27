"""
Secret Filter Service

Detect and redact secrets from text:
- API keys
- Passwords
- Tokens
- Private keys
- Connection strings
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import re
import logging
import hashlib

logger = logging.getLogger(__name__)


class SecretType(str, Enum):
    """Types of secrets."""
    API_KEY = "api_key"
    PASSWORD = "password"
    TOKEN = "token"
    PRIVATE_KEY = "private_key"
    CERTIFICATE = "certificate"
    CONNECTION_STRING = "connection_string"
    AWS_KEY = "aws_key"
    GCP_KEY = "gcp_key"
    AZURE_KEY = "azure_key"
    GITHUB_TOKEN = "github_token"
    SLACK_TOKEN = "slack_token"
    JWT = "jwt"
    SSH_KEY = "ssh_key"
    GENERIC = "generic"


@dataclass
class SecretMatch:
    """A detected secret."""
    type: SecretType
    value: str
    start: int
    end: int
    confidence: float  # 0-1
    context: str = ""  # Surrounding text
    
    # For audit
    value_hash: str = ""  # SHA256 of original value
    
    def __post_init__(self):
        if not self.value_hash:
            self.value_hash = hashlib.sha256(self.value.encode()).hexdigest()[:16]


@dataclass
class SecretPattern:
    """Pattern for detecting secrets."""
    type: SecretType
    pattern: re.Pattern
    confidence: float = 0.9
    description: str = ""
    
    # Validation
    min_length: int = 8
    max_length: int = 500
    validator: Optional[Callable[[str], bool]] = None


@dataclass
class FilterResult:
    """Result of secret filtering."""
    original_text: str
    filtered_text: str
    secrets_found: List[SecretMatch] = field(default_factory=list)
    redaction_count: int = 0
    
    @property
    def has_secrets(self) -> bool:
        return len(self.secrets_found) > 0


class SecretFilter:
    """
    Detects and redacts secrets from text.
    
    Features:
    - Pattern-based detection
    - Entropy-based detection
    - Configurable redaction
    - Audit logging
    """
    
    # Built-in patterns for common secrets
    PATTERNS: List[SecretPattern] = [
        # API Keys
        SecretPattern(
            type=SecretType.API_KEY,
            pattern=re.compile(r'(?i)(?:api[_-]?key|apikey)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{20,})["\']?'),
            confidence=0.95,
            description="Generic API key",
        ),
        SecretPattern(
            type=SecretType.API_KEY,
            pattern=re.compile(r'(?i)(?:secret[_-]?key|secretkey)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{20,})["\']?'),
            confidence=0.95,
            description="Secret key",
        ),
        
        # AWS
        SecretPattern(
            type=SecretType.AWS_KEY,
            pattern=re.compile(r'(?:AKIA|ABIA|ACCA|ASIA)[A-Z0-9]{16}'),
            confidence=0.99,
            description="AWS Access Key ID",
            min_length=20,
            max_length=20,
        ),
        SecretPattern(
            type=SecretType.AWS_KEY,
            pattern=re.compile(r'(?i)aws[_-]?secret[_-]?(?:access[_-]?)?key["\']?\s*[:=]\s*["\']?([a-zA-Z0-9/+=]{40})["\']?'),
            confidence=0.95,
            description="AWS Secret Access Key",
        ),
        
        # GCP
        SecretPattern(
            type=SecretType.GCP_KEY,
            pattern=re.compile(r'AIza[0-9A-Za-z_-]{35}'),
            confidence=0.99,
            description="Google API Key",
        ),
        
        # Azure
        SecretPattern(
            type=SecretType.AZURE_KEY,
            pattern=re.compile(r'(?i)azure[_-]?(?:storage[_-]?)?(?:account[_-]?)?key["\']?\s*[:=]\s*["\']?([a-zA-Z0-9/+=]{88})["\']?'),
            confidence=0.9,
            description="Azure Storage Key",
        ),
        
        # GitHub
        SecretPattern(
            type=SecretType.GITHUB_TOKEN,
            pattern=re.compile(r'gh[pousr]_[A-Za-z0-9_]{36,}'),
            confidence=0.99,
            description="GitHub Token",
        ),
        SecretPattern(
            type=SecretType.GITHUB_TOKEN,
            pattern=re.compile(r'github_pat_[A-Za-z0-9_]{22,}'),
            confidence=0.99,
            description="GitHub Personal Access Token",
        ),
        
        # Slack
        SecretPattern(
            type=SecretType.SLACK_TOKEN,
            pattern=re.compile(r'xox[baprs]-[0-9]{10,13}-[0-9]{10,13}[a-zA-Z0-9-]*'),
            confidence=0.99,
            description="Slack Token",
        ),
        
        # JWT
        SecretPattern(
            type=SecretType.JWT,
            pattern=re.compile(r'eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*'),
            confidence=0.95,
            description="JSON Web Token",
        ),
        
        # Private Keys
        SecretPattern(
            type=SecretType.PRIVATE_KEY,
            pattern=re.compile(r'-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----'),
            confidence=0.99,
            description="Private Key Header",
        ),
        SecretPattern(
            type=SecretType.SSH_KEY,
            pattern=re.compile(r'-----BEGIN OPENSSH PRIVATE KEY-----'),
            confidence=0.99,
            description="SSH Private Key",
        ),
        
        # Certificates
        SecretPattern(
            type=SecretType.CERTIFICATE,
            pattern=re.compile(r'-----BEGIN CERTIFICATE-----'),
            confidence=0.8,
            description="Certificate (may be public)",
        ),
        
        # Connection Strings
        SecretPattern(
            type=SecretType.CONNECTION_STRING,
            pattern=re.compile(r'(?i)(?:mongodb|postgres|mysql|redis|amqp)(?:\+srv)?://[^\s]+:[^\s@]+@[^\s]+'),
            confidence=0.95,
            description="Database Connection String",
        ),
        SecretPattern(
            type=SecretType.CONNECTION_STRING,
            pattern=re.compile(r'(?i)(?:Server|Data Source)=[^;]+;.*(?:Password|Pwd)=[^;]+'),
            confidence=0.9,
            description="SQL Connection String",
        ),
        
        # Passwords
        SecretPattern(
            type=SecretType.PASSWORD,
            pattern=re.compile(r'(?i)(?:password|passwd|pwd)["\']?\s*[:=]\s*["\']?([^\s"\']{8,})["\']?'),
            confidence=0.85,
            description="Password assignment",
        ),
        
        # Generic high-entropy strings
        SecretPattern(
            type=SecretType.GENERIC,
            pattern=re.compile(r'(?i)(?:token|secret|key|auth)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{32,})["\']?'),
            confidence=0.7,
            description="Generic secret pattern",
        ),
    ]
    
    # Default redaction placeholder
    DEFAULT_REDACTION = "[REDACTED]"
    
    def __init__(
        self,
        patterns: Optional[List[SecretPattern]] = None,
        redaction_format: str = "[REDACTED:{type}]",
        min_confidence: float = 0.7,
        enable_entropy_detection: bool = True,
        entropy_threshold: float = 4.5,
        custom_patterns: Optional[List[SecretPattern]] = None,
    ):
        """
        Initialize the secret filter.
        
        Args:
            patterns: Override default patterns
            redaction_format: Format string for redaction (supports {type})
            min_confidence: Minimum confidence to flag as secret
            enable_entropy_detection: Use entropy for detection
            entropy_threshold: Shannon entropy threshold
            custom_patterns: Additional patterns to include
        """
        self.patterns = patterns or self.PATTERNS.copy()
        if custom_patterns:
            self.patterns.extend(custom_patterns)
        
        self.redaction_format = redaction_format
        self.min_confidence = min_confidence
        self.enable_entropy = enable_entropy_detection
        self.entropy_threshold = entropy_threshold
        
        # Compile word patterns for entropy detection
        self._high_entropy_pattern = re.compile(r'[a-zA-Z0-9_\-/+=]{20,}')
    
    def filter(
        self,
        text: str,
        types_to_detect: Optional[Set[SecretType]] = None,
        redact: bool = True,
    ) -> FilterResult:
        """
        Filter text for secrets.
        
        Args:
            text: Text to filter
            types_to_detect: Specific types to look for (None = all)
            redact: Whether to redact found secrets
            
        Returns:
            FilterResult with findings and filtered text
        """
        result = FilterResult(original_text=text, filtered_text=text)
        
        # Track positions to avoid duplicate matches
        matched_ranges: List[Tuple[int, int]] = []
        
        # Pattern-based detection
        for pattern in self.patterns:
            if types_to_detect and pattern.type not in types_to_detect:
                continue
            
            for match in pattern.pattern.finditer(text):
                # Get the actual secret value (group 1 if exists, else full match)
                if match.lastindex and match.lastindex >= 1:
                    value = match.group(1)
                    start = match.start(1)
                    end = match.end(1)
                else:
                    value = match.group(0)
                    start = match.start()
                    end = match.end()
                
                # Check length constraints
                if len(value) < pattern.min_length or len(value) > pattern.max_length:
                    continue
                
                # Check confidence threshold
                if pattern.confidence < self.min_confidence:
                    continue
                
                # Run custom validator if present
                if pattern.validator and not pattern.validator(value):
                    continue
                
                # Check for overlap with existing matches
                if any(self._ranges_overlap((start, end), r) for r in matched_ranges):
                    continue
                
                # Get context
                context_start = max(0, start - 20)
                context_end = min(len(text), end + 20)
                context = text[context_start:context_end]
                
                secret = SecretMatch(
                    type=pattern.type,
                    value=value,
                    start=start,
                    end=end,
                    confidence=pattern.confidence,
                    context=context,
                )
                
                result.secrets_found.append(secret)
                matched_ranges.append((start, end))
        
        # Entropy-based detection for high-entropy strings
        if self.enable_entropy:
            for match in self._high_entropy_pattern.finditer(text):
                value = match.group(0)
                start = match.start()
                end = match.end()
                
                # Skip if already matched
                if any(self._ranges_overlap((start, end), r) for r in matched_ranges):
                    continue
                
                # Calculate entropy
                entropy = self._calculate_entropy(value)
                
                if entropy >= self.entropy_threshold:
                    # High entropy string detected
                    context_start = max(0, start - 20)
                    context_end = min(len(text), end + 20)
                    context = text[context_start:context_end]
                    
                    # Adjust confidence based on entropy
                    confidence = min(0.9, 0.5 + (entropy - self.entropy_threshold) * 0.1)
                    
                    if confidence >= self.min_confidence:
                        secret = SecretMatch(
                            type=SecretType.GENERIC,
                            value=value,
                            start=start,
                            end=end,
                            confidence=confidence,
                            context=context,
                        )
                        result.secrets_found.append(secret)
                        matched_ranges.append((start, end))
        
        # Sort by position
        result.secrets_found.sort(key=lambda s: s.start)
        
        # Redact if requested
        if redact and result.secrets_found:
            result.filtered_text = self._redact_secrets(text, result.secrets_found)
            result.redaction_count = len(result.secrets_found)
        
        return result
    
    def detect(self, text: str) -> List[SecretMatch]:
        """Detect secrets without redacting."""
        result = self.filter(text, redact=False)
        return result.secrets_found
    
    def redact(self, text: str) -> str:
        """Redact secrets and return filtered text."""
        result = self.filter(text, redact=True)
        return result.filtered_text
    
    def _redact_secrets(
        self,
        text: str,
        secrets: List[SecretMatch],
    ) -> str:
        """Replace secrets with redaction placeholders."""
        # Work backwards to preserve positions
        result = text
        for secret in reversed(secrets):
            redaction = self.redaction_format.format(type=secret.type.value)
            result = result[:secret.start] + redaction + result[secret.end:]
        return result
    
    def _calculate_entropy(self, text: str) -> float:
        """Calculate Shannon entropy of a string."""
        if not text:
            return 0.0
        
        # Count character frequencies
        freq: Dict[str, int] = {}
        for char in text:
            freq[char] = freq.get(char, 0) + 1
        
        # Calculate entropy
        length = len(text)
        entropy = 0.0
        
        import math
        for count in freq.values():
            prob = count / length
            entropy -= prob * math.log2(prob)
        
        return entropy
    
    def _ranges_overlap(
        self,
        range1: Tuple[int, int],
        range2: Tuple[int, int],
    ) -> bool:
        """Check if two ranges overlap."""
        return range1[0] < range2[1] and range2[0] < range1[1]
    
    def add_pattern(self, pattern: SecretPattern) -> None:
        """Add a custom pattern."""
        self.patterns.append(pattern)
    
    def get_stats(self, results: List[FilterResult]) -> Dict[str, Any]:
        """Get statistics from multiple filter results."""
        total_secrets = sum(len(r.secrets_found) for r in results)
        total_redactions = sum(r.redaction_count for r in results)
        
        type_counts: Dict[str, int] = {}
        for r in results:
            for secret in r.secrets_found:
                type_counts[secret.type.value] = type_counts.get(secret.type.value, 0) + 1
        
        return {
            "total_texts_processed": len(results),
            "total_secrets_found": total_secrets,
            "total_redactions": total_redactions,
            "secrets_by_type": type_counts,
            "texts_with_secrets": sum(1 for r in results if r.has_secrets),
        }


# Convenience functions
def detect_secrets(text: str) -> List[SecretMatch]:
    """Detect secrets in text."""
    filter = SecretFilter()
    return filter.detect(text)


def redact_secrets(text: str) -> str:
    """Redact secrets from text."""
    filter = SecretFilter()
    return filter.redact(text)


def has_secrets(text: str) -> bool:
    """Check if text contains secrets."""
    filter = SecretFilter()
    result = filter.filter(text, redact=False)
    return result.has_secrets
