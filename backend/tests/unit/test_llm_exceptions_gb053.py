"""GB053: M18 testing — LLM error classification and exception hierarchy."""

import pytest

from app.services.llm_gateway.exceptions import (
    AuthenticationError,
    AuthorizationError,
    CapacityError,
    ConnectionError,
    ContentFilterError,
    ContextLengthError,
    InternalProviderError,
    InvalidRequestError,
    LLMProviderError,
    ModelNotFoundError,
    ProviderTimeoutError,
    RateLimitError,
    ServiceUnavailableError,
    classify_error,
    _extract_retry_after,
)


class TestLLMProviderErrorBase:
    def test_retryable_default(self):
        err = LLMProviderError("test")
        assert err.retryable is True

    def test_str_with_provider_and_model(self):
        err = LLMProviderError("oops", provider="openai", model="gpt-4")
        assert "oops" in str(err)
        assert "provider=openai" in str(err)
        assert "model=gpt-4" in str(err)

    def test_str_without_provider(self):
        err = LLMProviderError("oops")
        s = str(err)
        assert s == "oops"
        assert "provider=" not in s

    def test_original_error_stored(self):
        orig = ValueError("inner")
        err = LLMProviderError("outer", original_error=orig)
        assert err.original_error is orig

    def test_details_default_empty(self):
        err = LLMProviderError("test")
        assert err.details == {}


class TestExceptionRetryability:
    def test_rate_limit_is_retryable(self):
        assert RateLimitError.retryable is True
        assert RateLimitError.status_code == 429

    def test_auth_error_not_retryable(self):
        assert AuthenticationError.retryable is False

    def test_authorization_not_retryable(self):
        assert AuthorizationError.retryable is False

    def test_capacity_retryable(self):
        assert CapacityError.retryable is True

    def test_model_not_found_not_retryable(self):
        assert ModelNotFoundError.retryable is False

    def test_content_filter_not_retryable(self):
        assert ContentFilterError.retryable is False

    def test_timeout_retryable(self):
        assert ProviderTimeoutError.retryable is True

    def test_connection_retryable(self):
        assert ConnectionError.retryable is True

    def test_invalid_request_not_retryable(self):
        assert InvalidRequestError.retryable is False

    def test_context_length_not_retryable(self):
        assert ContextLengthError.retryable is False

    def test_service_unavailable_retryable(self):
        assert ServiceUnavailableError.retryable is True

    def test_internal_error_retryable(self):
        assert InternalProviderError.retryable is True


class TestRateLimitError:
    def test_retry_after(self):
        err = RateLimitError(retry_after=30.0, provider="openai")
        assert err.retry_after == 30.0

    def test_retry_after_none_by_default(self):
        err = RateLimitError()
        assert err.retry_after is None


class TestClassifyErrorByStatusCode:
    def test_401_returns_auth_error(self):
        err = classify_error("openai", Exception("fail"), status_code=401)
        assert isinstance(err, AuthenticationError)
        assert err.provider == "openai"

    def test_403_returns_authorization_error(self):
        err = classify_error("openai", Exception("fail"), status_code=403)
        assert isinstance(err, AuthorizationError)

    def test_404_returns_model_not_found(self):
        err = classify_error("openai", Exception("fail"), status_code=404)
        assert isinstance(err, ModelNotFoundError)

    def test_429_returns_rate_limit(self):
        err = classify_error("openai", Exception("fail"), status_code=429)
        assert isinstance(err, RateLimitError)

    def test_429_extracts_retry_after(self):
        body = {"error": {"retry_after": 5.0}}
        err = classify_error("openai", Exception("fail"), status_code=429, response_body=body)
        assert isinstance(err, RateLimitError)
        assert err.retry_after == 5.0

    def test_503_returns_service_unavailable(self):
        err = classify_error("openai", Exception("fail"), status_code=503)
        assert isinstance(err, ServiceUnavailableError)


class TestClassifyErrorByMessage:
    def test_rate_limit_pattern(self):
        err = classify_error("test", Exception("Rate limit exceeded"))
        assert isinstance(err, RateLimitError)

    def test_too_many_requests_pattern(self):
        err = classify_error("test", Exception("too many requests"))
        assert isinstance(err, RateLimitError)

    def test_authentication_pattern(self):
        err = classify_error("test", Exception("Invalid API key provided"))
        assert isinstance(err, AuthenticationError)

    def test_unauthorized_pattern(self):
        err = classify_error("test", Exception("Unauthorized access"))
        assert isinstance(err, AuthenticationError)

    def test_timeout_pattern(self):
        err = classify_error("test", Exception("Request timed out"))
        assert isinstance(err, ProviderTimeoutError)

    def test_deadline_pattern(self):
        err = classify_error("test", Exception("Deadline exceeded"))
        assert isinstance(err, ProviderTimeoutError)

    def test_connection_pattern(self):
        err = classify_error("test", Exception("Connection refused"))
        assert isinstance(err, ConnectionError)

    def test_network_unreachable_pattern(self):
        err = classify_error("test", Exception("Network unreachable"))
        assert isinstance(err, ConnectionError)

    def test_capacity_pattern(self):
        err = classify_error("test", Exception("Server overloaded"))
        assert isinstance(err, CapacityError)

    def test_content_filter_pattern(self):
        err = classify_error("test", Exception("Content blocked by safety filter"))
        assert isinstance(err, ContentFilterError)

    def test_context_length_pattern(self):
        err = classify_error("test", Exception("Context length exceeded"))
        assert isinstance(err, ContextLengthError)

    def test_max_token_pattern(self):
        err = classify_error("test", Exception("max token limit reached"))
        assert isinstance(err, ContextLengthError)

    def test_model_not_found_pattern(self):
        err = classify_error("test", Exception("Model does not exist"))
        assert isinstance(err, ModelNotFoundError)

    def test_invalid_request_pattern(self):
        err = classify_error("test", Exception("Bad request: malformed input"))
        assert isinstance(err, InvalidRequestError)

    def test_unknown_error_returns_internal(self):
        err = classify_error("test", Exception("something completely unknown"))
        assert isinstance(err, InternalProviderError)
        assert err.retryable is True


class TestClassifyProviderSpecific:
    def test_openai_insufficient_quota(self):
        body = {"error": {"code": "insufficient_quota"}}
        err = classify_error("openai", Exception("quota"), response_body=body)
        assert isinstance(err, RateLimitError)

    def test_openai_context_length_exceeded(self):
        body = {"error": {"code": "context_length_exceeded"}}
        err = classify_error("openai", Exception("too long"), response_body=body)
        assert isinstance(err, ContextLengthError)

    def test_openai_content_policy_violation(self):
        body = {"error": {"code": "content_policy_violation"}}
        err = classify_error("openai", Exception("blocked"), response_body=body)
        assert isinstance(err, ContentFilterError)

    def test_anthropic_overloaded(self):
        body = {"error": {"type": "overloaded_error"}}
        err = classify_error("anthropic", Exception("busy"), response_body=body)
        assert isinstance(err, CapacityError)

    def test_anthropic_rate_limit(self):
        body = {"error": {"type": "rate_limit_error"}}
        err = classify_error("anthropic", Exception("limit"), response_body=body)
        assert isinstance(err, RateLimitError)

    def test_google_quota(self):
        err = classify_error("google", Exception("quota exceeded"))
        assert isinstance(err, RateLimitError)

    def test_google_safety(self):
        err = classify_error("google", Exception("blocked by safety"))
        assert isinstance(err, ContentFilterError)

    def test_groq_rate_limit(self):
        err = classify_error("groq", Exception("rate limit reached"))
        assert isinstance(err, RateLimitError)

    def test_groq_requests_per(self):
        err = classify_error("groq", Exception("exceeded requests per minute"))
        assert isinstance(err, RateLimitError)

    def test_unknown_provider_falls_through(self):
        err = classify_error("unknown_provider", Exception("something weird"))
        assert isinstance(err, InternalProviderError)


class TestExtractRetryAfter:
    def test_openai_format(self):
        body = {"error": {"retry_after": 10}}
        assert _extract_retry_after(body, "openai") == 10.0

    def test_anthropic_format(self):
        body = {"retry_after": 5}
        assert _extract_retry_after(body, "anthropic") == 5.0

    def test_no_retry_after(self):
        assert _extract_retry_after({}, "openai") is None

    def test_non_dict_error_field(self):
        body = {"error": "string error"}
        assert _extract_retry_after(body, "openai") is None
