"""Security - Rate limiting, audit logging, and input sanitization for setup chatbot."""

import hashlib
import hmac
import re
import secrets
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from enum import Enum
from functools import wraps
from typing import Any, Callable
import html
import bleach
import logging

logger = logging.getLogger(__name__)


# ===================
# Rate Limiting
# ===================

class RateLimitWindow(str, Enum):
    """Time windows for rate limiting."""
    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"


@dataclass
class RateLimitRule:
    """A rate limit rule definition."""
    max_requests: int
    window: RateLimitWindow
    key_prefix: str = "default"

    @property
    def window_seconds(self) -> int:
        """Get window duration in seconds."""
        windows = {
            RateLimitWindow.SECOND: 1,
            RateLimitWindow.MINUTE: 60,
            RateLimitWindow.HOUR: 3600,
            RateLimitWindow.DAY: 86400,
        }
        return windows[self.window]


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    remaining: int
    reset_at: datetime
    retry_after_seconds: int = 0


class RateLimiter:
    """In-memory rate limiter with sliding window."""

    # Default rules for different operations
    DEFAULT_RULES = {
        "message": RateLimitRule(max_requests=60, window=RateLimitWindow.MINUTE),
        "session_create": RateLimitRule(max_requests=10, window=RateLimitWindow.MINUTE),
        "connection_create": RateLimitRule(max_requests=20, window=RateLimitWindow.HOUR),
        "api_call": RateLimitRule(max_requests=100, window=RateLimitWindow.MINUTE),
        "sensitive_operation": RateLimitRule(max_requests=5, window=RateLimitWindow.MINUTE),
    }

    def __init__(self):
        # Store: {key: [(timestamp, count), ...]}
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._rules = self.DEFAULT_RULES.copy()
        self._lock_until: dict[str, float] = {}  # For temporary lockouts

    def add_rule(self, operation: str, rule: RateLimitRule) -> None:
        """Add or update a rate limit rule."""
        self._rules[operation] = rule

    def _get_key(self, operation: str, identifier: str) -> str:
        """Generate a unique key for rate limiting."""
        rule = self._rules.get(operation, self.DEFAULT_RULES["api_call"])
        return f"{rule.key_prefix}:{operation}:{identifier}"

    def _cleanup_old_requests(self, key: str, window_seconds: int) -> None:
        """Remove requests outside the current window."""
        now = time.time()
        cutoff = now - window_seconds
        self._requests[key] = [ts for ts in self._requests[key] if ts > cutoff]

    def check(self, operation: str, identifier: str) -> RateLimitResult:
        """Check if a request is allowed under rate limits."""
        rule = self._rules.get(operation, self.DEFAULT_RULES["api_call"])
        key = self._get_key(operation, identifier)
        now = time.time()

        # Check for temporary lockout
        if key in self._lock_until and now < self._lock_until[key]:
            lock_remaining = int(self._lock_until[key] - now)
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_at=datetime.fromtimestamp(self._lock_until[key], tz=UTC),
                retry_after_seconds=lock_remaining,
            )

        # Clean up old requests
        self._cleanup_old_requests(key, rule.window_seconds)

        # Count requests in current window
        request_count = len(self._requests[key])
        remaining = max(0, rule.max_requests - request_count)
        reset_at = datetime.now(UTC) + timedelta(seconds=rule.window_seconds)

        if request_count >= rule.max_requests:
            # Rate limited
            retry_after = rule.window_seconds - int(now - min(self._requests[key]))
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_at=reset_at,
                retry_after_seconds=max(1, retry_after),
            )

        return RateLimitResult(
            allowed=True,
            remaining=remaining - 1,  # Account for this request
            reset_at=reset_at,
        )

    def record(self, operation: str, identifier: str) -> None:
        """Record a request for rate limiting."""
        key = self._get_key(operation, identifier)
        self._requests[key].append(time.time())

    def check_and_record(self, operation: str, identifier: str) -> RateLimitResult:
        """Check rate limit and record the request if allowed."""
        result = self.check(operation, identifier)
        if result.allowed:
            self.record(operation, identifier)
        return result

    def lock_temporarily(self, operation: str, identifier: str, duration_seconds: int = 300) -> None:
        """Temporarily lock an identifier (e.g., after suspicious activity)."""
        key = self._get_key(operation, identifier)
        self._lock_until[key] = time.time() + duration_seconds
        logger.warning(f"Temporarily locked {identifier} for {operation} for {duration_seconds}s")

    def unlock(self, operation: str, identifier: str) -> None:
        """Remove a temporary lock."""
        key = self._get_key(operation, identifier)
        self._lock_until.pop(key, None)

    def reset(self, operation: str, identifier: str) -> None:
        """Reset rate limit counters for an identifier."""
        key = self._get_key(operation, identifier)
        self._requests.pop(key, None)
        self._lock_until.pop(key, None)


# Singleton rate limiter
rate_limiter = RateLimiter()


# ===================
# Input Sanitization
# ===================

class InputSanitizer:
    """Sanitize and validate user inputs."""

    # Dangerous patterns to detect
    INJECTION_PATTERNS = [
        r'<script[^>]*>',  # Script tags
        r'javascript:',  # JavaScript URLs
        r'on\w+\s*=',  # Event handlers
        r'\{\{.*\}\}',  # Template injection
        r'\$\{.*\}',  # Template literals
        r'eval\s*\(',  # eval() calls
        r'exec\s*\(',  # exec() calls
        r'__import__',  # Python import injection
        r'subprocess\.',  # Subprocess calls
        r'os\.(system|popen|exec)',  # OS command execution
        r'; *rm ',  # Shell command injection
        r'\|\| *rm ',  # Shell command injection
        r'&& *rm ',  # Shell command injection
        r'DROP\s+TABLE',  # SQL injection
        r'UNION\s+SELECT',  # SQL injection
        r"';--",  # SQL comment injection
        r'\\x[0-9a-fA-F]{2}',  # Hex escape sequences
    ]

    # Allowed HTML tags for rich text (very restrictive)
    ALLOWED_TAGS = []  # No HTML allowed by default
    ALLOWED_ATTRIBUTES = {}

    # Field-specific validators
    FIELD_VALIDATORS = {
        "name": r'^[a-zA-Z0-9][a-zA-Z0-9\s\-_\.]{0,99}$',
        "email": r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        "url": r'^https?://[a-zA-Z0-9][a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}(/[^\s]*)?$',
        "token": r'^[a-zA-Z0-9\-_\.]{10,500}$',
        "cron": r'^[0-9\*\/\-\,]+(\s+[0-9\*\/\-\,]+){4}$',
        "identifier": r'^[a-zA-Z][a-zA-Z0-9_]{0,63}$',
    }

    def __init__(self):
        self._compiled_patterns = [
            re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            for pattern in self.INJECTION_PATTERNS
        ]
        self._field_validators = {
            name: re.compile(pattern)
            for name, pattern in self.FIELD_VALIDATORS.items()
        }

    def detect_injection(self, text: str) -> list[str]:
        """Detect potential injection attacks in text."""
        detected = []
        for i, pattern in enumerate(self._compiled_patterns):
            if pattern.search(text):
                detected.append(self.INJECTION_PATTERNS[i])
        return detected

    def sanitize_text(self, text: str, max_length: int = 10000) -> str:
        """Sanitize plain text input."""
        if not text:
            return ""

        # Truncate to max length
        text = text[:max_length]

        # Strip HTML
        text = bleach.clean(text, tags=[], strip=True)

        # Escape HTML entities
        text = html.escape(text, quote=True)

        # Remove null bytes
        text = text.replace('\x00', '')

        # Normalize whitespace
        text = ' '.join(text.split())

        return text.strip()

    def sanitize_html(self, text: str, max_length: int = 10000) -> str:
        """Sanitize HTML input with whitelist."""
        if not text:
            return ""

        text = text[:max_length]

        return bleach.clean(
            text,
            tags=self.ALLOWED_TAGS,
            attributes=self.ALLOWED_ATTRIBUTES,
            strip=True,
        )

    def validate_field(self, field_type: str, value: str) -> tuple[bool, str | None]:
        """Validate a field against its expected pattern."""
        validator = self._field_validators.get(field_type)
        if not validator:
            return True, None

        if validator.match(value):
            return True, None

        return False, f"Invalid {field_type} format"

    def sanitize_credentials(self, credentials: dict[str, Any]) -> dict[str, Any]:
        """Sanitize credential inputs."""
        sanitized = {}
        for key, value in credentials.items():
            if isinstance(value, str):
                # Basic sanitization for credential fields
                sanitized[key] = value.strip()[:500]

                # Check for injection in non-token fields
                if key not in ("token", "password", "api_key", "secret"):
                    injections = self.detect_injection(value)
                    if injections:
                        logger.warning(f"Potential injection detected in {key}")
                        raise ValueError(f"Invalid characters in {key}")
            else:
                sanitized[key] = value

        return sanitized

    def mask_sensitive(self, value: str, visible_chars: int = 4) -> str:
        """Mask sensitive values for logging."""
        if not value or len(value) <= visible_chars:
            return "***"
        return value[:visible_chars] + "*" * (len(value) - visible_chars)


# Singleton sanitizer
input_sanitizer = InputSanitizer()


# ===================
# Audit Logging
# ===================

class AuditEventType(str, Enum):
    """Types of audit events."""
    SESSION_CREATED = "session_created"
    SESSION_DELETED = "session_deleted"
    MESSAGE_SENT = "message_sent"
    FLOW_STARTED = "flow_started"
    FLOW_COMPLETED = "flow_completed"
    FLOW_CANCELLED = "flow_cancelled"
    CONNECTION_CREATED = "connection_created"
    CONNECTION_TESTED = "connection_tested"
    CONNECTION_DELETED = "connection_deleted"
    PROJECT_CREATED = "project_created"
    PIPELINE_CREATED = "pipeline_created"
    CREDENTIALS_ENTERED = "credentials_entered"
    RATE_LIMITED = "rate_limited"
    SECURITY_ALERT = "security_alert"
    INJECTION_DETECTED = "injection_detected"
    AUTH_FAILURE = "auth_failure"


@dataclass
class AuditEvent:
    """An audit log event."""
    event_type: AuditEventType
    timestamp: datetime
    tenant_id: str
    user_id: str
    session_id: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    action: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    ip_address: str | None = None
    user_agent: str | None = None
    severity: str = "info"  # info, warning, error, critical

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "action": self.action,
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "severity": self.severity,
        }


class AuditLogger:
    """Audit logging service."""

    def __init__(self, max_buffer_size: int = 1000):
        self._buffer: list[AuditEvent] = []
        self._max_buffer_size = max_buffer_size
        self._handlers: list[Callable[[AuditEvent], None]] = []

    def add_handler(self, handler: Callable[[AuditEvent], None]) -> None:
        """Add an audit event handler."""
        self._handlers.append(handler)

    def log(
        self,
        event_type: AuditEventType,
        tenant_id: str,
        user_id: str,
        session_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        action: str | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        severity: str = "info",
    ) -> AuditEvent:
        """Log an audit event."""
        event = AuditEvent(
            event_type=event_type,
            timestamp=datetime.now(UTC),
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            severity=severity,
        )

        # Add to buffer
        self._buffer.append(event)
        if len(self._buffer) > self._max_buffer_size:
            self._buffer.pop(0)

        # Call handlers
        for handler in self._handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Audit handler error: {e}")

        # Log to standard logger
        log_message = (
            f"[AUDIT] {event_type.value} | "
            f"tenant={tenant_id} user={user_id} "
            f"session={session_id} resource={resource_type}:{resource_id} "
            f"action={action} severity={severity}"
        )

        if severity == "critical":
            logger.critical(log_message)
        elif severity == "error":
            logger.error(log_message)
        elif severity == "warning":
            logger.warning(log_message)
        else:
            logger.info(log_message)

        return event

    def log_security_event(
        self,
        event_type: AuditEventType,
        tenant_id: str,
        user_id: str,
        description: str,
        ip_address: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """Log a security-related event with elevated severity."""
        return self.log(
            event_type=event_type,
            tenant_id=tenant_id,
            user_id=user_id,
            action=description,
            details=details or {},
            ip_address=ip_address,
            severity="warning" if event_type != AuditEventType.INJECTION_DETECTED else "critical",
        )

    def get_recent_events(
        self,
        tenant_id: str | None = None,
        user_id: str | None = None,
        event_type: AuditEventType | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        """Get recent audit events (from buffer)."""
        events = self._buffer.copy()

        if tenant_id:
            events = [e for e in events if e.tenant_id == tenant_id]
        if user_id:
            events = [e for e in events if e.user_id == user_id]
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if since:
            events = [e for e in events if e.timestamp >= since]

        return events[-limit:]

    def get_security_events(
        self,
        tenant_id: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        """Get security-related events."""
        security_types = {
            AuditEventType.RATE_LIMITED,
            AuditEventType.SECURITY_ALERT,
            AuditEventType.INJECTION_DETECTED,
            AuditEventType.AUTH_FAILURE,
        }

        events = [e for e in self._buffer if e.event_type in security_types]

        if tenant_id:
            events = [e for e in events if e.tenant_id == tenant_id]
        if since:
            events = [e for e in events if e.timestamp >= since]

        return events[-limit:]


# Singleton audit logger
audit_logger = AuditLogger()


# ===================
# CSRF Protection
# ===================

class CSRFProtection:
    """CSRF token management."""

    def __init__(self, secret_key: str | None = None, token_lifetime: int = 3600):
        self._secret_key = secret_key or secrets.token_hex(32)
        self._token_lifetime = token_lifetime
        self._tokens: dict[str, tuple[str, float]] = {}  # session_id -> (token, created_at)

    def generate_token(self, session_id: str) -> str:
        """Generate a CSRF token for a session."""
        token = secrets.token_urlsafe(32)
        self._tokens[session_id] = (token, time.time())
        return token

    def validate_token(self, session_id: str, token: str) -> bool:
        """Validate a CSRF token."""
        stored = self._tokens.get(session_id)
        if not stored:
            return False

        stored_token, created_at = stored

        # Check expiration
        if time.time() - created_at > self._token_lifetime:
            del self._tokens[session_id]
            return False

        # Constant-time comparison
        return hmac.compare_digest(stored_token, token)

    def refresh_token(self, session_id: str) -> str:
        """Refresh a CSRF token (invalidates old one)."""
        return self.generate_token(session_id)

    def revoke_token(self, session_id: str) -> None:
        """Revoke a session's CSRF token."""
        self._tokens.pop(session_id, None)

    def cleanup_expired(self) -> int:
        """Remove expired tokens."""
        now = time.time()
        expired = [
            sid for sid, (_, created_at) in self._tokens.items()
            if now - created_at > self._token_lifetime
        ]
        for sid in expired:
            del self._tokens[sid]
        return len(expired)


# Singleton CSRF protection
csrf_protection = CSRFProtection()


# ===================
# Security Middleware
# ===================

@dataclass
class SecurityContext:
    """Security context for a request."""
    tenant_id: str
    user_id: str
    session_id: str | None
    ip_address: str | None
    user_agent: str | None
    is_rate_limited: bool = False
    rate_limit_result: RateLimitResult | None = None
    csrf_valid: bool = True


def rate_limit(operation: str = "api_call"):
    """Decorator for rate limiting functions."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Try to extract identifier from kwargs or args
            identifier = kwargs.get("user_id") or kwargs.get("tenant_id") or "anonymous"

            result = rate_limiter.check_and_record(operation, identifier)
            if not result.allowed:
                raise RateLimitExceeded(
                    f"Rate limit exceeded. Retry after {result.retry_after_seconds} seconds.",
                    retry_after=result.retry_after_seconds,
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def audit_action(event_type: AuditEventType, resource_type: str | None = None):
    """Decorator for auditing function calls."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            tenant_id = kwargs.get("tenant_id", "unknown")
            user_id = kwargs.get("user_id", "unknown")
            session_id = kwargs.get("session_id")

            try:
                result = await func(*args, **kwargs)

                audit_logger.log(
                    event_type=event_type,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    session_id=session_id,
                    resource_type=resource_type,
                    action="success",
                )

                return result
            except Exception as e:
                audit_logger.log(
                    event_type=event_type,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    session_id=session_id,
                    resource_type=resource_type,
                    action="failure",
                    details={"error": str(e)},
                    severity="error",
                )
                raise
        return wrapper
    return decorator


def sanitize_input(func: Callable):
    """Decorator for input sanitization."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Sanitize string kwargs
        sanitized_kwargs = {}
        for key, value in kwargs.items():
            if isinstance(value, str) and key not in ("password", "token", "api_key", "secret"):
                # Check for injection
                injections = input_sanitizer.detect_injection(value)
                if injections:
                    tenant_id = kwargs.get("tenant_id", "unknown")
                    user_id = kwargs.get("user_id", "unknown")
                    audit_logger.log_security_event(
                        event_type=AuditEventType.INJECTION_DETECTED,
                        tenant_id=tenant_id,
                        user_id=user_id,
                        description=f"Injection attempt in {key}",
                        details={"patterns": injections, "field": key},
                    )
                    raise SecurityException(f"Invalid input in {key}")

                sanitized_kwargs[key] = input_sanitizer.sanitize_text(value)
            else:
                sanitized_kwargs[key] = value

        return await func(*args, **sanitized_kwargs)
    return wrapper


# ===================
# Exceptions
# ===================

class SecurityException(Exception):
    """Base security exception."""
    pass


class RateLimitExceeded(SecurityException):
    """Rate limit exceeded exception."""

    def __init__(self, message: str, retry_after: int = 60):
        super().__init__(message)
        self.retry_after = retry_after


class CSRFValidationError(SecurityException):
    """CSRF token validation failed."""
    pass


class InjectionDetected(SecurityException):
    """Potential injection attack detected."""
    pass


# ===================
# Utility Functions
# ===================

def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure token."""
    return secrets.token_urlsafe(length)


def hash_identifier(identifier: str, salt: str = "") -> str:
    """Create a hash of an identifier for logging without exposing PII."""
    data = f"{salt}{identifier}".encode()
    return hashlib.sha256(data).hexdigest()[:16]


def is_safe_url(url: str, allowed_hosts: list[str] | None = None) -> bool:
    """Check if a URL is safe for redirect."""
    from urllib.parse import urlparse

    try:
        parsed = urlparse(url)

        # Only allow http(s)
        if parsed.scheme not in ("http", "https", ""):
            return False

        # If no host specified, it's a relative URL (safe)
        if not parsed.netloc:
            return True

        # Check against allowed hosts
        if allowed_hosts:
            return parsed.netloc in allowed_hosts

        return False
    except Exception:
        return False


def sanitize_log_data(data: dict[str, Any]) -> dict[str, Any]:
    """Sanitize data for safe logging (remove/mask sensitive fields)."""
    sensitive_keys = {
        "password", "token", "api_key", "secret", "credential",
        "auth", "key", "bearer", "authorization", "private",
    }

    sanitized = {}
    for key, value in data.items():
        key_lower = key.lower()
        if any(s in key_lower for s in sensitive_keys):
            if isinstance(value, str):
                sanitized[key] = input_sanitizer.mask_sensitive(value)
            else:
                sanitized[key] = "***"
        elif isinstance(value, dict):
            sanitized[key] = sanitize_log_data(value)
        else:
            sanitized[key] = value

    return sanitized
