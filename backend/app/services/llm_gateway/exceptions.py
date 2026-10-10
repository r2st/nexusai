"""Provider-specific exceptions for LLM gateway.

Provides structured error classification for intelligent failover decisions.
"""

from typing import Any


class LLMProviderError(Exception):
    """Base exception for all LLM provider errors."""

    retryable: bool = True
    status_code: int | None = None

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        model: str | None = None,
        original_error: Exception | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.model = model
        self.original_error = original_error
        self.details = details or {}

    def __str__(self) -> str:
        parts = [self.message]
        if self.provider:
            parts.append(f"provider={self.provider}")
        if self.model:
            parts.append(f"model={self.model}")
        return " ".join(parts)


class RateLimitError(LLMProviderError):
    """Rate limit exceeded - should retry after backoff."""

    retryable = True
    status_code = 429

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: float | None = None,
        **kwargs: Any,
    ):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class AuthenticationError(LLMProviderError):
    """Authentication failed - not retryable without fixing credentials."""

    retryable = False
    status_code = 401


class AuthorizationError(LLMProviderError):
    """Authorization failed - insufficient permissions."""

    retryable = False
    status_code = 403


class CapacityError(LLMProviderError):
    """Provider at capacity - retry with different provider or later."""

    retryable = True
    status_code = 503


class ModelNotFoundError(LLMProviderError):
    """Model not available on this provider."""

    retryable = False
    status_code = 404


class ContentFilterError(LLMProviderError):
    """Content blocked by safety filters - not retryable."""

    retryable = False
    status_code = 400


class ProviderTimeoutError(LLMProviderError):
    """Request timed out - may retry."""

    retryable = True
    status_code = 408


class ConnectionError(LLMProviderError):
    """Failed to connect to provider - may retry."""

    retryable = True
    status_code = 502


class InvalidRequestError(LLMProviderError):
    """Invalid request parameters - not retryable without fixing request."""

    retryable = False
    status_code = 400


class ContextLengthError(LLMProviderError):
    """Context length exceeded - not retryable without reducing input."""

    retryable = False
    status_code = 400


class ServiceUnavailableError(LLMProviderError):
    """Service temporarily unavailable - retry later."""

    retryable = True
    status_code = 503


class InternalProviderError(LLMProviderError):
    """Internal error at provider - may retry."""

    retryable = True
    status_code = 500


def classify_error(
    provider: str,
    error: Exception,
    status_code: int | None = None,
    response_body: dict[str, Any] | None = None,
) -> LLMProviderError:
    """
    Classify a provider error into a specific exception type.

    Args:
        provider: The provider name (openai, anthropic, google, etc.)
        error: The original exception
        status_code: HTTP status code if available
        response_body: Response body if available

    Returns:
        A specific LLMProviderError subclass
    """
    error_str = str(error).lower()
    response_body = response_body or {}

    # Check status code first
    if status_code:
        if status_code == 401:
            return AuthenticationError(
                message="Authentication failed",
                provider=provider,
                original_error=error,
            )
        if status_code == 403:
            return AuthorizationError(
                message="Authorization failed",
                provider=provider,
                original_error=error,
            )
        if status_code == 404:
            return ModelNotFoundError(
                message="Model not found",
                provider=provider,
                original_error=error,
            )
        if status_code == 429:
            retry_after = _extract_retry_after(response_body, provider)
            return RateLimitError(
                message="Rate limit exceeded",
                provider=provider,
                original_error=error,
                retry_after=retry_after,
            )
        if status_code == 503:
            return ServiceUnavailableError(
                message="Service unavailable",
                provider=provider,
                original_error=error,
            )

    # Check error message patterns
    if any(term in error_str for term in ["rate limit", "ratelimit", "too many requests"]):
        return RateLimitError(
            message=str(error),
            provider=provider,
            original_error=error,
        )

    if any(term in error_str for term in ["authentication", "api key", "invalid key", "unauthorized"]):
        return AuthenticationError(
            message=str(error),
            provider=provider,
            original_error=error,
        )

    if any(term in error_str for term in ["timeout", "timed out", "deadline"]):
        return ProviderTimeoutError(
            message=str(error),
            provider=provider,
            original_error=error,
        )

    if any(term in error_str for term in ["connection", "connect", "network", "unreachable"]):
        return ConnectionError(
            message=str(error),
            provider=provider,
            original_error=error,
        )

    if any(term in error_str for term in ["capacity", "overloaded", "busy", "503"]):
        return CapacityError(
            message=str(error),
            provider=provider,
            original_error=error,
        )

    if any(term in error_str for term in ["content filter", "safety", "blocked", "harmful"]):
        return ContentFilterError(
            message=str(error),
            provider=provider,
            original_error=error,
        )

    if any(term in error_str for term in ["context length", "token limit", "too long", "max.*token"]):
        return ContextLengthError(
            message=str(error),
            provider=provider,
            original_error=error,
        )

    if any(term in error_str for term in ["model", "not found", "does not exist", "invalid model"]):
        return ModelNotFoundError(
            message=str(error),
            provider=provider,
            original_error=error,
        )

    if any(term in error_str for term in ["invalid", "bad request", "malformed"]):
        return InvalidRequestError(
            message=str(error),
            provider=provider,
            original_error=error,
        )

    # Provider-specific error handling
    classified = _classify_provider_specific(provider, error, error_str, response_body)
    if classified:
        return classified

    # Default to internal error (retryable)
    return InternalProviderError(
        message=str(error),
        provider=provider,
        original_error=error,
    )


def _extract_retry_after(response_body: dict[str, Any], provider: str) -> float | None:
    """Extract retry-after time from response body."""
    # OpenAI format
    if "error" in response_body:
        error_obj = response_body["error"]
        if isinstance(error_obj, dict):
            # Check for retry_after in message or metadata
            if "retry_after" in error_obj:
                return float(error_obj["retry_after"])

    # Anthropic format
    if "retry_after" in response_body:
        return float(response_body["retry_after"])

    # Headers would be handled at HTTP level
    return None


def _classify_provider_specific(
    provider: str,
    error: Exception,
    error_str: str,
    response_body: dict[str, Any],
) -> LLMProviderError | None:
    """Provider-specific error classification."""
    if provider == "openai":
        return _classify_openai_error(error, error_str, response_body)
    if provider == "anthropic":
        return _classify_anthropic_error(error, error_str, response_body)
    if provider == "google":
        return _classify_google_error(error, error_str, response_body)
    if provider == "groq":
        return _classify_groq_error(error, error_str, response_body)
    return None


def _classify_openai_error(
    error: Exception,
    error_str: str,
    response_body: dict[str, Any],
) -> LLMProviderError | None:
    """Classify OpenAI-specific errors."""
    # OpenAI error codes
    error_obj = response_body.get("error", {})
    error_code = error_obj.get("code") if isinstance(error_obj, dict) else None

    if error_code == "insufficient_quota":
        return RateLimitError(
            message="OpenAI quota exceeded",
            provider="openai",
            original_error=error,
        )
    if error_code == "context_length_exceeded":
        return ContextLengthError(
            message="Context length exceeded",
            provider="openai",
            original_error=error,
        )
    if error_code == "content_policy_violation":
        return ContentFilterError(
            message="Content policy violation",
            provider="openai",
            original_error=error,
        )
    return None


def _classify_anthropic_error(
    error: Exception,
    error_str: str,
    response_body: dict[str, Any],
) -> LLMProviderError | None:
    """Classify Anthropic-specific errors."""
    error_type = response_body.get("error", {}).get("type")

    if error_type == "overloaded_error":
        return CapacityError(
            message="Anthropic API overloaded",
            provider="anthropic",
            original_error=error,
        )
    if error_type == "rate_limit_error":
        return RateLimitError(
            message="Anthropic rate limit",
            provider="anthropic",
            original_error=error,
        )
    return None


def _classify_google_error(
    error: Exception,
    error_str: str,
    response_body: dict[str, Any],
) -> LLMProviderError | None:
    """Classify Google (Gemini/Vertex) specific errors."""
    if "quota" in error_str:
        return RateLimitError(
            message="Google quota exceeded",
            provider="google",
            original_error=error,
        )
    if "safety" in error_str or "blocked" in error_str:
        return ContentFilterError(
            message="Content blocked by Google safety filters",
            provider="google",
            original_error=error,
        )
    return None


def _classify_groq_error(
    error: Exception,
    error_str: str,
    response_body: dict[str, Any],
) -> LLMProviderError | None:
    """Classify Groq-specific errors."""
    if "rate limit" in error_str or "requests per" in error_str:
        return RateLimitError(
            message="Groq rate limit exceeded",
            provider="groq",
            original_error=error,
        )
    return None
