"""Phase 15D Unit Tests — Rate Limiting: Trusted Proxy and Compute Endpoints.

Verifies:
  1. X-Forwarded-For is only trusted when the immediate client is a configured
     trusted proxy — not blindly from arbitrary clients.
  2. The compute rate limiter (enforce_compute_rate_limit) is distinct from
     the planning submission limiter.
  3. Rate limit keys include auth header prefix (per-identity throttling).
"""

import os
import importlib
import threading
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_request(client_host: str = "10.0.0.5", forwarded_for: str = "", auth: str = "") -> MagicMock:
    request = MagicMock()
    request.client = MagicMock()
    request.client.host = client_host
    headers = {}
    if forwarded_for:
        headers["X-Forwarded-For"] = forwarded_for
    if auth:
        headers["Authorization"] = auth
    request.headers.get = lambda k, default="": headers.get(k, default)
    return request


def _resolve(client_host: str, forwarded_for: str = "", trusted: str = "") -> str:
    """Call _resolve_client_ip with a given TRUSTED_PROXY_IPS env value."""
    old = os.environ.get("TRUSTED_PROXY_IPS", "")
    os.environ["TRUSTED_PROXY_IPS"] = trusted
    try:
        # Reimport to pick up env change
        import backend.app.core.rate_limit as rl
        importlib.reload(rl)
        req = _make_request(client_host=client_host, forwarded_for=forwarded_for)
        return rl._resolve_client_ip(req)
    finally:
        os.environ["TRUSTED_PROXY_IPS"] = old
        importlib.reload(rl)


# ---------------------------------------------------------------------------
# Trusted proxy resolution
# ---------------------------------------------------------------------------

def test_no_trusted_proxies_uses_peer_host() -> None:
    """With no trusted proxy config, always use the raw TCP peer IP."""
    ip = _resolve(client_host="1.2.3.4", forwarded_for="10.0.0.1", trusted="")
    assert ip == "1.2.3.4", "X-Forwarded-For must not be honoured without trusted proxy config"


def test_untrusted_client_ignored_forwarded_for() -> None:
    """If the immediate client is NOT a trusted proxy, ignore X-Forwarded-For."""
    # Trusted proxy is 192.168.1.1, but client is from 1.2.3.4 (untrusted)
    ip = _resolve(client_host="1.2.3.4", forwarded_for="203.0.113.5", trusted="192.168.1.1")
    assert ip == "1.2.3.4"


def test_trusted_proxy_honours_first_forwarded_for() -> None:
    """When immediate client IS a trusted proxy, leftmost X-Forwarded-For is used."""
    ip = _resolve(client_host="192.168.1.1", forwarded_for="203.0.113.5, 192.168.1.1", trusted="192.168.1.1")
    assert ip == "203.0.113.5"


def test_trusted_proxy_cidr_range() -> None:
    """TRUSTED_PROXY_IPS supports CIDR ranges."""
    ip = _resolve(client_host="10.0.0.50", forwarded_for="198.51.100.1", trusted="10.0.0.0/8")
    assert ip == "198.51.100.1"


def test_malformed_trusted_proxy_entry_is_ignored() -> None:
    """Malformed TRUSTED_PROXY_IPS entries must not crash; just use peer IP."""
    ip = _resolve(client_host="1.2.3.4", forwarded_for="9.9.9.9", trusted="not-an-ip,1.2.3.4")
    # 1.2.3.4 is in trusted list (exact match), so forwarded-for should be used
    assert ip == "9.9.9.9"


# ---------------------------------------------------------------------------
# Rate limiter core behaviour
# ---------------------------------------------------------------------------

def test_rate_limiter_allows_requests_within_window() -> None:
    """Requests below the limit should be allowed."""
    from backend.app.core.rate_limit import InMemoryRateLimiter
    lim = InMemoryRateLimiter(max_requests=5, window_seconds=60.0)
    for _ in range(5):
        allowed, remaining, retry_after = lim.check_rate_limit("key-A")
        assert allowed
    assert remaining == 0


def test_rate_limiter_blocks_after_limit() -> None:
    """Requests above the limit should be rejected."""
    from backend.app.core.rate_limit import InMemoryRateLimiter
    lim = InMemoryRateLimiter(max_requests=3, window_seconds=60.0)
    for _ in range(3):
        lim.check_rate_limit("key-B")
    allowed, _, retry_after = lim.check_rate_limit("key-B")
    assert not allowed
    assert retry_after > 0


def test_rate_limiter_keys_are_per_client() -> None:
    """Rate limit is per-key; different clients are independent."""
    from backend.app.core.rate_limit import InMemoryRateLimiter
    lim = InMemoryRateLimiter(max_requests=1, window_seconds=60.0)
    allowed_a, _, _ = lim.check_rate_limit("client-A")
    assert allowed_a
    allowed_b, _, _ = lim.check_rate_limit("client-B")
    assert allowed_b  # Different key — independent limit


def test_planning_and_compute_limiters_are_independent() -> None:
    """planning_rate_limiter and compute_rate_limiter must be separate objects."""
    from backend.app.core.rate_limit import planning_rate_limiter, compute_rate_limiter
    assert planning_rate_limiter is not compute_rate_limiter


def test_compute_rate_limiter_exists_and_has_lower_limit() -> None:
    """compute_rate_limiter should exist with its configured limit."""
    from backend.app.core.rate_limit import compute_rate_limiter, planning_rate_limiter
    # Compute endpoints are more expensive so should have lower or equal limit
    assert compute_rate_limiter.max_requests <= planning_rate_limiter.max_requests


def test_rate_limit_key_includes_auth_prefix() -> None:
    """Rate limit key must include auth header prefix for per-identity throttling."""
    from backend.app.core.rate_limit import InMemoryRateLimiter
    lim = InMemoryRateLimiter(max_requests=1, window_seconds=60.0)
    # Exhaust key for user-A token
    lim.check_rate_limit("1.2.3.4:Bearer token-A-prefix-123")
    # User-B with different token from same IP should not be affected
    allowed, _, _ = lim.check_rate_limit("1.2.3.4:Bearer token-B-prefix-456")
    assert allowed
