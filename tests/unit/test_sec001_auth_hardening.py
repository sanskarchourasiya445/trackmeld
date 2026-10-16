"""Unit regression tests for SEC-001: Production Authentication Hardening.

Verifies:
1. Demo authentication is disabled by default when the opt-in flag is absent.
2. Demo authentication behaves as intended when explicitly enabled in permitted local environments.
3. Production strictly rejects demo credentials even when the opt-in flag is enabled.
4. Production strictly rejects anonymous/unauthenticated requests without assigning any demo identity.
5. Unknown or misspelled environment values (e.g., 'prod', 'prodution', 'unknown') fail startup validation
   or fail closed safely without enabling demo credentials.
6. Valid configured authentication (AUTH_*_TOKEN) continues working across all environments.
7. Role permissions and authorization boundaries are preserved.
"""

from unittest.mock import MagicMock
import pytest
from pydantic import ValidationError
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from backend.app.config import Settings, get_settings
from backend.app.core.auth import (
    get_current_user,
    get_active_credentials,
    require_permission,
    AuthUser,
    UserRole,
    DEFAULT_DEMO_USER,
    DEMO_CREDENTIALS,
)


def _make_request(headers: dict | None = None) -> MagicMock:
    req = MagicMock()
    req.headers = headers or {}
    return req


# =============================================================================
# 1. DEMO AUTH DISABLED BY DEFAULT (FLAG ABSENT OR FALSE)
# =============================================================================

@pytest.mark.asyncio
async def test_demo_auth_disabled_by_default(monkeypatch):
    """When ENABLE_DEMO_AUTH is False (default), demo credentials are not loaded and anonymous requests fail closed."""
    s = get_settings()
    monkeypatch.setattr(s, "ENABLE_DEMO_AUTH", False)
    monkeypatch.setattr(s, "ENVIRONMENT", "development")
    monkeypatch.setattr(s, "AUTH_ADMIN_TOKEN", None)

    assert s.is_demo_auth_active is False

    # 1. Demo credentials are not present in active registry
    active_creds = get_active_credentials()
    assert "planner-token-2026" not in active_creds
    assert "admin-token-2026" not in active_creds
    assert "viewer-token-2026" not in active_creds

    # 2. Bearer request with demo token is rejected with 401 UNAUTHORIZED
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="planner-token-2026")
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request=_make_request(), auth_creds=creds)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["error"]["code"] == "UNAUTHORIZED"

    # 3. Anonymous request is rejected with 401 AUTHENTICATION_REQUIRED (no demo fallback)
    with pytest.raises(HTTPException) as exc_info_anon:
        await get_current_user(request=_make_request(), auth_creds=None)
    assert exc_info_anon.value.status_code == 401
    assert exc_info_anon.value.detail["error"]["code"] == "AUTHENTICATION_REQUIRED"


# =============================================================================
# 2. EXPLICITLY ENABLED LOCAL DEMO MODE
# =============================================================================

@pytest.mark.asyncio
async def test_demo_auth_explicitly_enabled_in_development(monkeypatch):
    """When ENABLE_DEMO_AUTH is True in permitted environment (development/test), demo mode operates as intended."""
    s = get_settings()
    monkeypatch.setattr(s, "ENABLE_DEMO_AUTH", True)
    monkeypatch.setattr(s, "ENVIRONMENT", "development")

    assert s.is_demo_auth_allowed is True
    assert s.is_demo_auth_active is True

    # 1. Demo credentials are active
    active_creds = get_active_credentials()
    assert "planner-token-2026" in active_creds
    assert "admin-token-2026" in active_creds
    assert "viewer-token-2026" in active_creds

    # 2. Valid bearer demo token is authenticated
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="planner-token-2026")
    user = await get_current_user(request=_make_request(), auth_creds=creds)
    assert user.role == UserRole.MAINTENANCE_PLANNER
    assert user.username == "senior_planner_dli"
    assert user.has_permission("write:operational")

    # 3. Anonymous request receives DEFAULT_DEMO_USER (viewer)
    anon_user = await get_current_user(request=_make_request(), auth_creds=None)
    assert anon_user == DEFAULT_DEMO_USER
    assert anon_user.role == UserRole.VIEWER
    assert not anon_user.has_permission("write:operational")


# =============================================================================
# 3. PRODUCTION REJECTS DEMO CREDENTIALS EVEN IF OPT-IN FLAG IS ENABLED
# =============================================================================

@pytest.mark.asyncio
async def test_production_rejects_demo_credentials_even_with_flag(monkeypatch):
    """In production, demo authentication is strictly forbidden even if ENABLE_DEMO_AUTH is True."""
    s = get_settings()
    monkeypatch.setattr(s, "ENABLE_DEMO_AUTH", True)
    monkeypatch.setattr(s, "ENVIRONMENT", "production")
    monkeypatch.setattr(s, "AUTH_ADMIN_TOKEN", None)

    assert s.is_production is True
    assert s.is_demo_auth_allowed is False
    assert s.is_demo_auth_active is False

    # 1. Demo credentials are NOT loaded in active registry
    active_creds = get_active_credentials()
    assert "planner-token-2026" not in active_creds
    assert "admin-token-2026" not in active_creds
    assert "viewer-token-2026" not in active_creds

    # 2. Attempting to use demo token is rejected with 401 UNAUTHORIZED
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="planner-token-2026")
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request=_make_request(), auth_creds=creds)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["error"]["code"] == "UNAUTHORIZED"


# =============================================================================
# 4. PRODUCTION REJECTS ANONYMOUS REQUESTS WITHOUT DEMO IDENTITY
# =============================================================================

@pytest.mark.asyncio
async def test_production_rejects_anonymous_requests(monkeypatch):
    """In production, anonymous requests fail closed without assigning any demo user."""
    s = get_settings()
    monkeypatch.setattr(s, "ENABLE_DEMO_AUTH", True)
    monkeypatch.setattr(s, "ENVIRONMENT", "production")

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request=_make_request(), auth_creds=None)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["error"]["code"] == "AUTHENTICATION_REQUIRED"
    assert "required" in exc_info.value.detail["error"]["message"].lower()


# =============================================================================
# 5. ENVIRONMENT VALIDATION & MISSPELLED / UNKNOWN ENVIRONMENTS
# =============================================================================

def test_startup_validation_rejects_abbreviated_prod():
    """Startup validation raises ValidationError when ENVIRONMENT is set to 'prod'."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(ENVIRONMENT="prod")
    error_msg = str(exc_info.value)
    assert "Invalid environment 'prod'" in error_msg
    assert "production" in error_msg


def test_startup_validation_rejects_misspelled_environment():
    """Startup validation raises ValidationError when ENVIRONMENT is misspelled or unknown."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(ENVIRONMENT="prodution")
    assert "Invalid environment 'prodution'" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info_unknown:
        Settings(ENVIRONMENT="staging_cloud_aws")
    assert "Invalid environment 'staging_cloud_aws'" in str(exc_info_unknown.value)


@pytest.mark.asyncio
async def test_misspelled_environment_fails_closed_if_bypassed(monkeypatch):
    """Even if an unknown environment bypassed Settings constructor, is_demo_auth_active evaluates False."""
    s = get_settings()
    monkeypatch.setattr(s, "ENABLE_DEMO_AUTH", True)
    monkeypatch.setattr(s, "ENVIRONMENT", "prod")

    # 'prod' is recognized as production and not an allowed demo environment
    assert s.is_production is True
    assert s.is_demo_auth_allowed is False
    assert s.is_demo_auth_active is False

    # Unknown environment
    monkeypatch.setattr(s, "ENVIRONMENT", "unknown_custom_env")
    assert s.is_demo_auth_allowed is False
    assert s.is_demo_auth_active is False

    # Active creds has no demo credentials
    active_creds = get_active_credentials()
    assert "planner-token-2026" not in active_creds

    # Anonymous request fails closed
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request=_make_request(), auth_creds=None)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["error"]["code"] == "AUTHENTICATION_REQUIRED"


# =============================================================================
# 6. VALID CONFIGURED AUTHENTICATION WORKS IN ALL MODES
# =============================================================================

@pytest.mark.asyncio
async def test_configured_credentials_work_in_production(monkeypatch):
    """Explicitly configured environment tokens work in production mode regardless of demo auth status."""
    s = get_settings()
    monkeypatch.setattr(s, "ENVIRONMENT", "production")
    monkeypatch.setattr(s, "ENABLE_DEMO_AUTH", False)
    monkeypatch.setattr(s, "AUTH_ADMIN_TOKEN", "prod-secret-admin-token-999")
    monkeypatch.setattr(s, "AUTH_PLANNER_TOKEN", "prod-secret-planner-token-888")

    active_creds = get_active_credentials()
    assert "prod-secret-admin-token-999" in active_creds
    assert "prod-secret-planner-token-888" in active_creds

    # 1. Configured planner token works via Bearer
    planner_creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="prod-secret-planner-token-888")
    planner_user = await get_current_user(request=_make_request(), auth_creds=planner_creds)
    assert planner_user.role == UserRole.MAINTENANCE_PLANNER
    assert planner_user.username == "production_planner"
    assert planner_user.has_permission("write:operational")

    # 2. Configured admin token works via X-API-Key
    admin_user = await get_current_user(
        request=_make_request(headers={"X-API-Key": "prod-secret-admin-token-999"}),
        auth_creds=None,
    )
    assert admin_user.role == UserRole.ADMIN
    assert admin_user.username == "production_admin"
    assert admin_user.has_permission("*")


# =============================================================================
# 7. AUTHORIZATION AND RBAC BOUNDARIES PRESERVED
# =============================================================================

@pytest.mark.asyncio
async def test_rbac_permission_enforcement_preserved():
    """Operational RBAC boundaries are strictly enforced."""
    planner = AuthUser(
        user_id="USR-P1",
        username="planner_test",
        role=UserRole.MAINTENANCE_PLANNER,
        permissions=["read:reference", "read:operational", "write:operational", "plan:review"],
    )
    viewer = AuthUser(
        user_id="USR-V1",
        username="viewer_test",
        role=UserRole.VIEWER,
        permissions=["read:reference", "read:operational"],
    )

    write_guard = require_permission("write:operational")
    assert await write_guard(planner) == planner

    with pytest.raises(HTTPException) as exc_info:
        await write_guard(viewer)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["error"]["code"] == "FORBIDDEN"
