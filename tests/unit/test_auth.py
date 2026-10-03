import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from backend.app.core.auth import (
    get_current_user,
    require_permission,
    AuthUser,
    UserRole,
    KNOWN_CREDENTIALS,
)


@pytest.mark.asyncio
async def test_auth_default_viewer_when_no_credentials():
    mock_request = MagicMock()
    mock_request.headers = {}
    user = await get_current_user(request=mock_request, auth_creds=None)
    assert user.role == UserRole.VIEWER
    assert user.has_permission("read:reference")
    assert user.has_permission("read:operational")
    assert not user.has_permission("write:operational")


@pytest.mark.asyncio
async def test_auth_valid_bearer_token():
    mock_request = MagicMock()
    mock_request.headers = {}
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="planner-token-2026")
    user = await get_current_user(request=mock_request, auth_creds=creds)
    assert user.role == UserRole.MAINTENANCE_PLANNER
    assert user.username == "senior_planner_dli"
    assert user.has_permission("write:operational")


@pytest.mark.asyncio
async def test_auth_valid_api_key():
    mock_request = MagicMock()
    mock_request.headers = {"X-API-Key": "admin-token-2026"}
    user = await get_current_user(request=mock_request, auth_creds=None)
    assert user.role == UserRole.ADMIN
    assert user.username in ("chief_operations_admin", "production_admin")
    assert user.has_permission("anything:anywhere")


@pytest.mark.asyncio
async def test_auth_invalid_bearer_token():
    mock_request = MagicMock()
    mock_request.headers = {}
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid-token-xyz")
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request=mock_request, auth_creds=creds)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_auth_invalid_api_key():
    mock_request = MagicMock()
    mock_request.headers = {"X-API-Key": "invalid-api-key-xyz"}
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request=mock_request, auth_creds=None)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_require_permission_granted():
    user = AuthUser(
        user_id="test-1",
        username="tester",
        role=UserRole.MAINTENANCE_PLANNER,
        permissions=["read:reference", "plan:schedule"],
    )
    perm_checker = require_permission("plan:schedule")
    res = await perm_checker(user)
    assert res == user


@pytest.mark.asyncio
async def test_require_permission_denied():
    user = AuthUser(
        user_id="test-2",
        username="tester",
        role=UserRole.VIEWER,
        permissions=["read:reference"],
    )
    perm_checker = require_permission("admin:system")
    with pytest.raises(HTTPException) as exc_info:
        await perm_checker(user)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["error"]["code"] == "FORBIDDEN"
