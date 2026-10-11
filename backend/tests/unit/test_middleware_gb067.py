"""GB067: Tests for core/middleware.py — CircuitBreaker, client ID extraction, tenant extraction."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.middleware import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    RateLimitMiddleware,
    TenantMiddleware,
    get_circuit_breaker,
)


# ---------------------------------------------------------------------------
# CircuitBreaker state machine
# ---------------------------------------------------------------------------

class TestCircuitBreakerStates:
    def test_starts_closed(self):
        cb = CircuitBreaker("test")
        assert cb.state == CircuitBreaker.CLOSED
        assert cb.is_available()

    def test_opens_after_failure_threshold(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitBreaker.OPEN
        assert not cb.is_available()

    def test_stays_closed_below_threshold(self):
        cb = CircuitBreaker("test", failure_threshold=5)
        for _ in range(4):
            cb.record_failure()
        assert cb.state == CircuitBreaker.CLOSED
        assert cb.is_available()

    def test_success_resets_failure_count(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreaker.CLOSED

    def test_transitions_to_half_open_after_timeout(self):
        cb = CircuitBreaker("test", failure_threshold=1, timeout=1)
        cb.record_failure()
        assert cb.state == CircuitBreaker.OPEN
        time.sleep(1.1)
        assert cb.state == CircuitBreaker.HALF_OPEN

    def test_half_open_closes_after_success_threshold(self):
        cb = CircuitBreaker("test", failure_threshold=1, success_threshold=2, timeout=0)
        cb.record_failure()
        # Timeout=0 means it transitions immediately on next check
        _ = cb.state  # triggers half_open transition
        cb.record_success()
        assert cb.state == CircuitBreaker.HALF_OPEN  # need 2 successes
        cb.record_success()
        assert cb.state == CircuitBreaker.CLOSED

    def test_half_open_reopens_on_failure(self):
        cb = CircuitBreaker("test", failure_threshold=1, timeout=0)
        cb.record_failure()
        _ = cb.state  # triggers half_open
        assert cb.state == CircuitBreaker.HALF_OPEN
        cb.record_failure()
        # record_failure sets state to OPEN, but timeout=0 means the
        # .state property will transition back to HALF_OPEN on the next read.
        # Verify the internal state was set to OPEN by record_failure.
        assert cb._state == CircuitBreaker.OPEN


class TestCircuitBreakerCall:
    @pytest.mark.asyncio
    async def test_call_succeeds_when_closed(self):
        cb = CircuitBreaker("test")
        result = await cb.call(AsyncMock(return_value=42))
        assert result == 42

    @pytest.mark.asyncio
    async def test_call_raises_when_open(self):
        cb = CircuitBreaker("test", failure_threshold=1)
        cb.record_failure()
        with pytest.raises(CircuitBreakerOpenError, match="test"):
            await cb.call(AsyncMock())

    @pytest.mark.asyncio
    async def test_call_records_failure_on_exception(self):
        cb = CircuitBreaker("test", failure_threshold=2)
        with pytest.raises(ValueError):
            await cb.call(AsyncMock(side_effect=ValueError("boom")))
        assert cb._failure_count == 1

    @pytest.mark.asyncio
    async def test_call_records_success(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        await cb.call(AsyncMock(return_value="ok"))
        assert cb._failure_count == 0  # success resets


class TestGetCircuitBreaker:
    def test_returns_preconfigured(self):
        cb = get_circuit_breaker("openai")
        assert cb.name == "openai"

    def test_creates_new_on_unknown_name(self):
        cb = get_circuit_breaker("new-service-xyz")
        assert cb.name == "new-service-xyz"
        assert get_circuit_breaker("new-service-xyz") is cb


# ---------------------------------------------------------------------------
# RateLimitMiddleware._get_client_id
# ---------------------------------------------------------------------------

class TestRateLimitClientId:
    def _make_middleware(self):
        return RateLimitMiddleware(app=MagicMock(), requests_per_minute=60)

    def _make_request(self, headers=None):
        req = MagicMock()
        req.headers = headers or {}
        req.client = MagicMock()
        req.client.host = "192.168.1.1"
        return req

    def test_bearer_token_hashed(self):
        mw = self._make_middleware()
        req = self._make_request(headers={"Authorization": "Bearer abc123"})
        cid = mw._get_client_id(req)
        assert cid.startswith("token:")
        assert "abc123" not in cid  # token is hashed

    def test_forwarded_ip(self):
        mw = self._make_middleware()
        req = self._make_request(headers={"X-Forwarded-For": "10.0.0.1, 10.0.0.2"})
        cid = mw._get_client_id(req)
        assert cid == "ip:10.0.0.1"

    def test_direct_ip(self):
        mw = self._make_middleware()
        req = self._make_request()
        cid = mw._get_client_id(req)
        assert cid == "ip:192.168.1.1"

    def test_no_client(self):
        mw = self._make_middleware()
        req = self._make_request()
        req.client = None
        cid = mw._get_client_id(req)
        assert cid == "ip:unknown"

    def test_bearer_takes_priority_over_forwarded(self):
        mw = self._make_middleware()
        req = self._make_request(
            headers={"Authorization": "Bearer tok", "X-Forwarded-For": "1.2.3.4"}
        )
        cid = mw._get_client_id(req)
        assert cid.startswith("token:")


# ---------------------------------------------------------------------------
# TenantMiddleware._extract_tenant_id
# ---------------------------------------------------------------------------

class TestTenantExtraction:
    def _make_middleware(self):
        return TenantMiddleware(app=MagicMock())

    def _make_request(self, headers=None):
        req = MagicMock()
        req.headers = headers or {}
        return req

    def test_x_tenant_id_header(self):
        mw = self._make_middleware()
        req = self._make_request(headers={"X-Tenant-ID": "tenant-1"})
        assert mw._extract_tenant_id(req) == "tenant-1"

    def test_x_organization_id_header(self):
        mw = self._make_middleware()
        req = self._make_request(headers={"X-Organization-ID": "org-2"})
        assert mw._extract_tenant_id(req) == "org-2"

    def test_tenant_id_takes_priority_over_org_id(self):
        mw = self._make_middleware()
        req = self._make_request(
            headers={"X-Tenant-ID": "t1", "X-Organization-ID": "o2"}
        )
        assert mw._extract_tenant_id(req) == "t1"

    def test_no_headers_returns_none(self):
        mw = self._make_middleware()
        req = self._make_request()
        assert mw._extract_tenant_id(req) is None

    def test_invalid_bearer_token_returns_none(self):
        mw = self._make_middleware()
        req = self._make_request(headers={"Authorization": "Bearer invalid.jwt"})
        assert mw._extract_tenant_id(req) is None
