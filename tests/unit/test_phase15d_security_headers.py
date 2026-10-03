"""Phase 15D Unit Tests — HTTP Security Headers.

Verifies that every API response includes the required security headers.

Headers tested:
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()
  Content-Security-Policy: frame-ancestors 'none' (must be present)

Headers intentionally absent:
  Strict-Transport-Security: NOT set on HTTP development server
"""

import pytest
from starlette.testclient import TestClient

from backend.app.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def test_security_headers_present_on_health(client: TestClient) -> None:
    """Security headers must be present on unauthenticated endpoints."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert "strict-origin" in r.headers.get("Referrer-Policy", "").lower()
    assert "frame-ancestors" in r.headers.get("Content-Security-Policy", "").lower()
    assert "camera=()" in r.headers.get("Permissions-Policy", "")


def test_no_hsts_on_http(client: TestClient) -> None:
    """Strict-Transport-Security MUST NOT be present on plain HTTP development server.

    HSTS on HTTP is harmful: it causes browsers to upgrade connections that
    are not actually served over TLS.
    """
    r = client.get("/health")
    assert "Strict-Transport-Security" not in r.headers, (
        "HSTS must not be set on a plain HTTP development server"
    )


def test_content_security_policy_blocks_framing(client: TestClient) -> None:
    """CSP must include frame-ancestors 'none' to block clickjacking."""
    r = client.get("/health")
    csp = r.headers.get("Content-Security-Policy", "")
    assert "frame-ancestors 'none'" in csp


def test_x_frame_options_deny(client: TestClient) -> None:
    """X-Frame-Options must be DENY (defense in depth alongside CSP)."""
    r = client.get("/health")
    assert r.headers.get("X-Frame-Options") == "DENY"


def test_security_headers_present_on_api_route(client: TestClient) -> None:
    """Security headers must be present on API endpoints, not just health."""
    # 401 or 200 — headers must always be present regardless of auth outcome
    r = client.get("/api/v1/planning-runs")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert "frame-ancestors" in r.headers.get("Content-Security-Policy", "").lower()
