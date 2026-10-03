"""Unit tests for Phase 15A: Explicit CORS Configuration and Origin Whitelisting."""

import pytest
from starlette.testclient import TestClient
from backend.app.main import app
from backend.app.config import get_settings


def test_cors_allowed_origin():
    """Requests from an explicitly allowed origin should receive CORS allow origin headers."""
    client = TestClient(app)
    settings = get_settings()
    allowed_origin = settings.cors_allowed_origins[0]

    # Preflight OPTIONS request
    headers = {
        "Origin": allowed_origin,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Authorization, Content-Type",
    }
    response = client.options("/health", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == allowed_origin
    assert response.headers.get("access-control-allow-credentials") == "true"

    # Actual GET request
    response = client.get("/health", headers={"Origin": allowed_origin})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == allowed_origin


def test_cors_disallowed_origin():
    """Requests from disallowed/untrusted origins must NOT receive CORS allow origin headers."""
    client = TestClient(app)
    disallowed_origin = "https://unauthorized-malicious-domain.com"

    # Preflight OPTIONS request
    headers = {
        "Origin": disallowed_origin,
        "Access-Control-Request-Method": "POST",
    }
    response = client.options("/health", headers=headers)
    # Origin should not be allowed
    assert response.headers.get("access-control-allow-origin") != disallowed_origin

    # Actual GET request
    response = client.get("/health", headers={"Origin": disallowed_origin})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") is None
