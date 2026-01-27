"""Validators - Smart input validation and suggestions for setup chatbot."""

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from enum import Enum
from typing import Any, Callable
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


# ===================
# Validation Result
# ===================

class ValidationSeverity(str, Enum):
    """Severity levels for validation issues."""
    ERROR = "error"  # Prevents proceeding
    WARNING = "warning"  # Can proceed with caution
    INFO = "info"  # Informational only


@dataclass
class ValidationIssue:
    """A single validation issue."""
    field: str
    message: str
    severity: ValidationSeverity
    suggestion: str | None = None
    auto_fix: str | None = None  # Value that would fix the issue


@dataclass
class ValidationResult:
    """Result of validation."""
    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    normalized_value: Any = None  # The value after normalization/fixing
    suggestions: list[str] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return any(i.severity == ValidationSeverity.ERROR for i in self.issues)

    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return any(i.severity == ValidationSeverity.WARNING for i in self.issues)

    def get_error_messages(self) -> list[str]:
        """Get all error messages."""
        return [i.message for i in self.issues if i.severity == ValidationSeverity.ERROR]

    def get_warning_messages(self) -> list[str]:
        """Get all warning messages."""
        return [i.message for i in self.issues if i.severity == ValidationSeverity.WARNING]


# ===================
# Field Validators
# ===================

class FieldValidator:
    """Base class for field validators."""

    def validate(self, value: Any, field_name: str = "value") -> ValidationResult:
        """Validate a value."""
        raise NotImplementedError


class RequiredValidator(FieldValidator):
    """Validates that a value is present."""

    def validate(self, value: Any, field_name: str = "value") -> ValidationResult:
        if value is None or (isinstance(value, str) and not value.strip()):
            return ValidationResult(
                is_valid=False,
                issues=[ValidationIssue(
                    field=field_name,
                    message=f"{field_name} is required",
                    severity=ValidationSeverity.ERROR,
                )],
            )
        return ValidationResult(is_valid=True, normalized_value=value)


class LengthValidator(FieldValidator):
    """Validates string length."""

    def __init__(self, min_length: int = 0, max_length: int = 10000):
        self.min_length = min_length
        self.max_length = max_length

    def validate(self, value: Any, field_name: str = "value") -> ValidationResult:
        if not isinstance(value, str):
            return ValidationResult(is_valid=True, normalized_value=value)

        issues = []
        if len(value) < self.min_length:
            issues.append(ValidationIssue(
                field=field_name,
                message=f"{field_name} must be at least {self.min_length} characters",
                severity=ValidationSeverity.ERROR,
            ))
        elif len(value) > self.max_length:
            issues.append(ValidationIssue(
                field=field_name,
                message=f"{field_name} must be at most {self.max_length} characters",
                severity=ValidationSeverity.ERROR,
                suggestion=f"Try shortening your input",
                auto_fix=value[:self.max_length],
            ))

        return ValidationResult(
            is_valid=len(issues) == 0,
            issues=issues,
            normalized_value=value,
        )


class PatternValidator(FieldValidator):
    """Validates against a regex pattern."""

    def __init__(
        self,
        pattern: str,
        message: str | None = None,
        example: str | None = None,
    ):
        self.pattern = re.compile(pattern)
        self.message = message or f"Invalid format"
        self.example = example

    def validate(self, value: Any, field_name: str = "value") -> ValidationResult:
        if not isinstance(value, str):
            return ValidationResult(is_valid=True, normalized_value=value)

        if self.pattern.match(value):
            return ValidationResult(is_valid=True, normalized_value=value)

        suggestion = f"Example: {self.example}" if self.example else None

        return ValidationResult(
            is_valid=False,
            issues=[ValidationIssue(
                field=field_name,
                message=self.message,
                severity=ValidationSeverity.ERROR,
                suggestion=suggestion,
            )],
        )


class UrlValidator(FieldValidator):
    """Validates URLs with smart suggestions."""

    COMMON_ENDPOINTS = {
        "github": "https://api.github.com",
        "gitlab": "https://gitlab.com",
        "jira": "https://your-domain.atlassian.net",
        "jenkins": "http://localhost:8080",
        "bitbucket": "https://api.bitbucket.org/2.0",
        "sonarqube": "http://localhost:9000",
        "azure": "https://dev.azure.com",
    }

    def __init__(
        self,
        require_https: bool = False,
        allowed_schemes: list[str] | None = None,
        plugin_hint: str | None = None,
    ):
        self.require_https = require_https
        self.allowed_schemes = allowed_schemes or ["http", "https"]
        self.plugin_hint = plugin_hint

    def validate(self, value: Any, field_name: str = "value") -> ValidationResult:
        if not isinstance(value, str):
            return ValidationResult(is_valid=True, normalized_value=value)

        value = value.strip()
        issues = []
        suggestions = []

        # Auto-fix: Add https:// if missing
        if not value.startswith(("http://", "https://")):
            if self.require_https:
                value = f"https://{value}"
            else:
                value = f"http://{value}"
            suggestions.append(f"Added scheme to make: {value}")

        try:
            parsed = urlparse(value)

            # Check scheme
            if parsed.scheme not in self.allowed_schemes:
                issues.append(ValidationIssue(
                    field=field_name,
                    message=f"URL must use {' or '.join(self.allowed_schemes)}",
                    severity=ValidationSeverity.ERROR,
                ))

            # Warn about http
            if parsed.scheme == "http" and self.require_https:
                issues.append(ValidationIssue(
                    field=field_name,
                    message="HTTPS is recommended for security",
                    severity=ValidationSeverity.WARNING,
                    auto_fix=value.replace("http://", "https://"),
                ))

            # Check host
            if not parsed.netloc:
                issues.append(ValidationIssue(
                    field=field_name,
                    message="Invalid URL - missing host",
                    severity=ValidationSeverity.ERROR,
                ))

            # Remove trailing slash for consistency
            if value.endswith("/"):
                value = value.rstrip("/")
                suggestions.append("Removed trailing slash")

            # Plugin-specific suggestions
            if self.plugin_hint:
                expected = self.COMMON_ENDPOINTS.get(self.plugin_hint)
                if expected and expected not in value:
                    suggestions.append(f"Common endpoint for {self.plugin_hint}: {expected}")

        except Exception:
            issues.append(ValidationIssue(
                field=field_name,
                message="Invalid URL format",
                severity=ValidationSeverity.ERROR,
            ))

        return ValidationResult(
            is_valid=not any(i.severity == ValidationSeverity.ERROR for i in issues),
            issues=issues,
            normalized_value=value,
            suggestions=suggestions,
        )


class TokenValidator(FieldValidator):
    """Validates API tokens with format detection."""

    TOKEN_PATTERNS = {
        "github_classic": (
            r"^gh[ps]_[A-Za-z0-9]{36,}$",
            "Classic GitHub Personal Access Token",
        ),
        "github_fine_grained": (
            r"^github_pat_[A-Za-z0-9_]{22,}$",
            "Fine-grained GitHub Personal Access Token",
        ),
        "gitlab": (
            r"^glpat-[A-Za-z0-9\-]{20,}$",
            "GitLab Personal Access Token",
        ),
        "gitlab_legacy": (
            r"^[A-Za-z0-9\-_]{20,}$",
            "GitLab Token (legacy format)",
        ),
        "jira": (
            r"^[A-Za-z0-9+/=]{40,}$",
            "Jira API Token",
        ),
        "jenkins": (
            r"^[a-fA-F0-9]{32,}$",
            "Jenkins API Token",
        ),
        "azure_pat": (
            r"^[a-z0-9]{52}$",
            "Azure DevOps Personal Access Token",
        ),
        "sonarqube": (
            r"^squ_[A-Za-z0-9]{40}$",
            "SonarQube Token",
        ),
        "slack_bot": (
            r"^xoxb-[0-9]+-[0-9A-Za-z]+$",
            "Slack Bot Token",
        ),
        "slack_user": (
            r"^xoxp-[0-9]+-[0-9A-Za-z]+$",
            "Slack User Token",
        ),
    }

    def __init__(
        self,
        expected_plugin: str | None = None,
        min_length: int = 10,
    ):
        self.expected_plugin = expected_plugin
        self.min_length = min_length

    def validate(self, value: Any, field_name: str = "value") -> ValidationResult:
        if not isinstance(value, str):
            return ValidationResult(is_valid=True, normalized_value=value)

        value = value.strip()
        issues = []
        suggestions = []

        # Basic length check
        if len(value) < self.min_length:
            issues.append(ValidationIssue(
                field=field_name,
                message=f"Token seems too short (minimum {self.min_length} characters)",
                severity=ValidationSeverity.ERROR,
            ))
            return ValidationResult(is_valid=False, issues=issues)

        # Detect token type
        detected_type = None
        for token_type, (pattern, description) in self.TOKEN_PATTERNS.items():
            if re.match(pattern, value):
                detected_type = token_type
                suggestions.append(f"Detected: {description}")
                break

        # Check if detected type matches expected plugin
        if self.expected_plugin and detected_type:
            expected_types = {
                "github": ["github_classic", "github_fine_grained"],
                "gitlab": ["gitlab", "gitlab_legacy"],
                "jira": ["jira"],
                "jenkins": ["jenkins"],
                "azuredevops": ["azure_pat"],
                "sonarqube": ["sonarqube"],
                "slack": ["slack_bot", "slack_user"],
            }

            valid_types = expected_types.get(self.expected_plugin, [])
            if valid_types and detected_type not in valid_types:
                issues.append(ValidationIssue(
                    field=field_name,
                    message=f"Token format doesn't match expected {self.expected_plugin} format",
                    severity=ValidationSeverity.WARNING,
                    suggestion="Please verify you're using the correct token",
                ))

        # Warn if token looks like it might be a password
        if " " in value or len(value) < 20:
            issues.append(ValidationIssue(
                field=field_name,
                message="This doesn't look like an API token",
                severity=ValidationSeverity.WARNING,
                suggestion="API tokens are typically long strings without spaces",
            ))

        # Check for common mistakes
        if value.startswith("ghp_") and len(value) < 40:
            issues.append(ValidationIssue(
                field=field_name,
                message="GitHub token seems incomplete",
                severity=ValidationSeverity.WARNING,
                suggestion="GitHub tokens are typically 40+ characters",
            ))

        return ValidationResult(
            is_valid=not any(i.severity == ValidationSeverity.ERROR for i in issues),
            issues=issues,
            normalized_value=value,
            suggestions=suggestions,
        )


class EmailValidator(FieldValidator):
    """Validates email addresses."""

    EMAIL_PATTERN = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )

    COMMON_DOMAINS = [
        "gmail.com", "outlook.com", "yahoo.com", "hotmail.com",
        "icloud.com", "protonmail.com", "company.com",
    ]

    def validate(self, value: Any, field_name: str = "value") -> ValidationResult:
        if not isinstance(value, str):
            return ValidationResult(is_valid=True, normalized_value=value)

        value = value.strip().lower()
        issues = []
        suggestions = []

        if not self.EMAIL_PATTERN.match(value):
            # Try to provide helpful suggestions
            if "@" not in value:
                suggestions.append("Email must contain @")
            elif value.count("@") > 1:
                suggestions.append("Email should have only one @")
            elif "." not in value.split("@")[1]:
                suggestions.append("Domain must include a TLD (e.g., .com)")

            issues.append(ValidationIssue(
                field=field_name,
                message="Invalid email format",
                severity=ValidationSeverity.ERROR,
                suggestion=suggestions[0] if suggestions else None,
            ))
        else:
            # Check for common typos in domain
            domain = value.split("@")[1]
            similar = self._find_similar_domain(domain)
            if similar and similar != domain:
                corrected = value.replace(domain, similar)
                issues.append(ValidationIssue(
                    field=field_name,
                    message=f"Did you mean {similar}?",
                    severity=ValidationSeverity.INFO,
                    auto_fix=corrected,
                ))

        return ValidationResult(
            is_valid=not any(i.severity == ValidationSeverity.ERROR for i in issues),
            issues=issues,
            normalized_value=value,
            suggestions=suggestions,
        )

    def _find_similar_domain(self, domain: str) -> str | None:
        """Find a similar common domain (for typo detection)."""
        best_match = None
        best_ratio = 0.0

        for common in self.COMMON_DOMAINS:
            ratio = SequenceMatcher(None, domain, common).ratio()
            if ratio > 0.8 and ratio > best_ratio and ratio < 1.0:
                best_match = common
                best_ratio = ratio

        return best_match


class NameValidator(FieldValidator):
    """Validates names (connection names, project names, etc.)."""

    def __init__(
        self,
        min_length: int = 2,
        max_length: int = 100,
        allow_spaces: bool = True,
        allow_special: bool = False,
    ):
        self.min_length = min_length
        self.max_length = max_length
        self.allow_spaces = allow_spaces
        self.allow_special = allow_special

    def validate(self, value: Any, field_name: str = "value") -> ValidationResult:
        if not isinstance(value, str):
            return ValidationResult(is_valid=True, normalized_value=value)

        value = value.strip()
        issues = []
        suggestions = []

        # Length checks
        if len(value) < self.min_length:
            issues.append(ValidationIssue(
                field=field_name,
                message=f"Name must be at least {self.min_length} characters",
                severity=ValidationSeverity.ERROR,
            ))

        if len(value) > self.max_length:
            issues.append(ValidationIssue(
                field=field_name,
                message=f"Name must be at most {self.max_length} characters",
                severity=ValidationSeverity.ERROR,
                auto_fix=value[:self.max_length],
            ))

        # Character checks
        if self.allow_spaces:
            pattern = r'^[a-zA-Z0-9][a-zA-Z0-9\s\-_\.]*$' if not self.allow_special else r'^.+$'
        else:
            pattern = r'^[a-zA-Z0-9][a-zA-Z0-9\-_\.]*$'

        if not re.match(pattern, value):
            if value and not value[0].isalnum():
                issues.append(ValidationIssue(
                    field=field_name,
                    message="Name must start with a letter or number",
                    severity=ValidationSeverity.ERROR,
                ))
            elif not self.allow_spaces and " " in value:
                # Auto-fix by replacing spaces
                fixed = value.replace(" ", "-")
                issues.append(ValidationIssue(
                    field=field_name,
                    message="Spaces are not allowed in this name",
                    severity=ValidationSeverity.ERROR,
                    suggestion="Use hyphens or underscores instead",
                    auto_fix=fixed,
                ))
            else:
                issues.append(ValidationIssue(
                    field=field_name,
                    message="Name contains invalid characters",
                    severity=ValidationSeverity.ERROR,
                    suggestion="Use only letters, numbers, hyphens, and underscores",
                ))

        # Suggest normalization
        normalized = self._normalize_name(value)
        if normalized != value:
            suggestions.append(f"Suggested: {normalized}")

        return ValidationResult(
            is_valid=not any(i.severity == ValidationSeverity.ERROR for i in issues),
            issues=issues,
            normalized_value=value,
            suggestions=suggestions,
        )

    def _normalize_name(self, name: str) -> str:
        """Normalize a name for consistency."""
        # Replace multiple spaces/dashes with single dash
        normalized = re.sub(r'[\s\-_]+', '-', name)
        # Remove leading/trailing dashes
        normalized = normalized.strip('-')
        # Lowercase
        normalized = normalized.lower()
        return normalized


class CronValidator(FieldValidator):
    """Validates cron expressions."""

    FIELD_RANGES = {
        0: (0, 59, "minute"),
        1: (0, 23, "hour"),
        2: (1, 31, "day of month"),
        3: (1, 12, "month"),
        4: (0, 6, "day of week"),
    }

    PRESETS = {
        "hourly": "0 * * * *",
        "daily": "0 0 * * *",
        "weekly": "0 0 * * 0",
        "monthly": "0 0 1 * *",
        "every 4 hours": "0 */4 * * *",
        "weekdays": "0 9 * * 1-5",
    }

    def validate(self, value: Any, field_name: str = "value") -> ValidationResult:
        if not isinstance(value, str):
            return ValidationResult(is_valid=True, normalized_value=value)

        value = value.strip()
        issues = []
        suggestions = []

        # Check for preset names
        if value.lower() in self.PRESETS:
            return ValidationResult(
                is_valid=True,
                normalized_value=self.PRESETS[value.lower()],
                suggestions=[f"Converted to: {self.PRESETS[value.lower()]}"],
            )

        # Parse cron expression
        parts = value.split()
        if len(parts) != 5:
            issues.append(ValidationIssue(
                field=field_name,
                message="Cron expression must have 5 parts: minute hour day month weekday",
                severity=ValidationSeverity.ERROR,
                suggestion="Example: 0 9 * * 1-5 (9 AM on weekdays)",
            ))
            return ValidationResult(is_valid=False, issues=issues, suggestions=list(self.PRESETS.keys()))

        # Validate each field
        for i, part in enumerate(parts):
            min_val, max_val, name = self.FIELD_RANGES[i]
            valid, msg = self._validate_field(part, min_val, max_val, name)
            if not valid:
                issues.append(ValidationIssue(
                    field=field_name,
                    message=msg,
                    severity=ValidationSeverity.ERROR,
                ))

        # Provide human-readable description
        if not issues:
            description = self._describe_cron(parts)
            suggestions.append(f"Schedule: {description}")

        return ValidationResult(
            is_valid=not any(i.severity == ValidationSeverity.ERROR for i in issues),
            issues=issues,
            normalized_value=value,
            suggestions=suggestions,
        )

    def _validate_field(
        self,
        field: str,
        min_val: int,
        max_val: int,
        name: str,
    ) -> tuple[bool, str]:
        """Validate a single cron field."""
        if field == "*":
            return True, ""

        # Handle step values (*/5)
        if field.startswith("*/"):
            try:
                step = int(field[2:])
                if step < 1 or step > max_val:
                    return False, f"Invalid step value for {name}: {step}"
                return True, ""
            except ValueError:
                return False, f"Invalid step value for {name}"

        # Handle ranges (1-5)
        if "-" in field:
            try:
                start, end = field.split("-")
                start, end = int(start), int(end)
                if start < min_val or end > max_val or start > end:
                    return False, f"Invalid range for {name}: {field}"
                return True, ""
            except ValueError:
                return False, f"Invalid range for {name}"

        # Handle lists (1,3,5)
        if "," in field:
            for part in field.split(","):
                valid, msg = self._validate_field(part.strip(), min_val, max_val, name)
                if not valid:
                    return False, msg
            return True, ""

        # Handle single values
        try:
            val = int(field)
            if val < min_val or val > max_val:
                return False, f"{name} must be between {min_val} and {max_val}"
            return True, ""
        except ValueError:
            return False, f"Invalid value for {name}: {field}"

    def _describe_cron(self, parts: list[str]) -> str:
        """Generate a human-readable description of a cron expression."""
        minute, hour, dom, month, dow = parts

        descriptions = []

        # Time
        if minute == "0" and hour == "*":
            descriptions.append("Every hour")
        elif minute == "*" and hour == "*":
            descriptions.append("Every minute")
        elif minute == "0" and hour == "0":
            descriptions.append("At midnight")
        elif minute == "0":
            if hour.isdigit():
                h = int(hour)
                time_str = f"{h}:00 AM" if h < 12 else f"{h - 12 if h > 12 else 12}:00 PM"
                descriptions.append(f"At {time_str}")
            else:
                descriptions.append(f"At hour {hour}")

        # Day of week
        dow_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        if dow != "*":
            if dow == "1-5":
                descriptions.append("on weekdays")
            elif dow == "0,6":
                descriptions.append("on weekends")
            elif dow.isdigit():
                descriptions.append(f"on {dow_names[int(dow)]}")

        return " ".join(descriptions) if descriptions else "Custom schedule"


# ===================
# Smart Suggestions
# ===================

class SmartSuggestionEngine:
    """Provides smart suggestions based on context and input."""

    def __init__(self):
        self._validators: dict[str, FieldValidator] = {
            "url": UrlValidator(),
            "email": EmailValidator(),
            "token": TokenValidator(),
            "name": NameValidator(),
            "cron": CronValidator(),
        }

    def validate(
        self,
        field_type: str,
        value: Any,
        field_name: str = "value",
        context: dict[str, Any] | None = None,
    ) -> ValidationResult:
        """Validate a value with smart suggestions."""
        validator = self._validators.get(field_type)
        if not validator:
            return ValidationResult(is_valid=True, normalized_value=value)

        # Add context to certain validators
        if context:
            if field_type == "url" and "plugin" in context:
                validator = UrlValidator(plugin_hint=context["plugin"])
            elif field_type == "token" and "plugin" in context:
                validator = TokenValidator(expected_plugin=context["plugin"])

        return validator.validate(value, field_name)

    def get_suggestions_for_field(
        self,
        field_type: str,
        partial_value: str = "",
        context: dict[str, Any] | None = None,
    ) -> list[str]:
        """Get suggestions for a field based on partial input."""
        suggestions = []

        if field_type == "url":
            plugin = context.get("plugin") if context else None
            if plugin and plugin in UrlValidator.COMMON_ENDPOINTS:
                endpoint = UrlValidator.COMMON_ENDPOINTS[plugin]
                if not partial_value or endpoint.startswith(partial_value):
                    suggestions.append(endpoint)

        elif field_type == "cron":
            for name, expr in CronValidator.PRESETS.items():
                if not partial_value or name.startswith(partial_value.lower()):
                    suggestions.append(f"{name} ({expr})")

        elif field_type == "name":
            # Suggest naming conventions
            if context and context.get("item_type") == "connection":
                plugin = context.get("plugin", "").title()
                suggestions.extend([
                    f"Production {plugin}",
                    f"Development {plugin}",
                    f"Main {plugin}",
                ])
            elif context and context.get("item_type") == "project":
                suggestions.extend([
                    "my-project",
                    "backend-services",
                    "mobile-app",
                    "platform-team",
                ])

        return suggestions[:5]

    def auto_correct(
        self,
        field_type: str,
        value: str,
        context: dict[str, Any] | None = None,
    ) -> tuple[str, list[str]]:
        """Attempt to auto-correct a value and return corrections made."""
        result = self.validate(field_type, value, context=context)
        corrections = []

        if result.normalized_value and result.normalized_value != value:
            corrections.extend(result.suggestions)
            return result.normalized_value, corrections

        # Apply auto-fixes from issues
        for issue in result.issues:
            if issue.auto_fix:
                corrections.append(f"Fixed: {issue.message}")
                return issue.auto_fix, corrections

        return value, corrections


# Singleton suggestion engine
suggestion_engine = SmartSuggestionEngine()


# ===================
# Composite Validators
# ===================

class CompositeValidator(FieldValidator):
    """Combines multiple validators."""

    def __init__(self, validators: list[FieldValidator], stop_on_error: bool = True):
        self.validators = validators
        self.stop_on_error = stop_on_error

    def validate(self, value: Any, field_name: str = "value") -> ValidationResult:
        all_issues = []
        all_suggestions = []
        normalized = value

        for validator in self.validators:
            result = validator.validate(normalized, field_name)

            all_issues.extend(result.issues)
            all_suggestions.extend(result.suggestions)

            if result.normalized_value is not None:
                normalized = result.normalized_value

            if self.stop_on_error and result.has_errors:
                break

        return ValidationResult(
            is_valid=not any(i.severity == ValidationSeverity.ERROR for i in all_issues),
            issues=all_issues,
            normalized_value=normalized,
            suggestions=all_suggestions,
        )


def create_connection_validator(plugin: str) -> CompositeValidator:
    """Create a validator for connection configuration."""
    return CompositeValidator([
        RequiredValidator(),
        LengthValidator(min_length=1, max_length=500),
        TokenValidator(expected_plugin=plugin),
    ])


def create_project_name_validator() -> CompositeValidator:
    """Create a validator for project names."""
    return CompositeValidator([
        RequiredValidator(),
        NameValidator(min_length=2, max_length=100, allow_spaces=False),
    ])
