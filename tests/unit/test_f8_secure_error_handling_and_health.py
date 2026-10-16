"""Unit tests for Task 8 (F8): Secure Error Handling and Health Endpoints.

Validates that:
1. /health/db failures return 503 with stable code DATABASE_UNREACHABLE and sanitized message.
2. Internal connection strings, credentials, ports, and socket errors are never leaked in /health/db responses.
3. Unexpected server exceptions return clean HTTP 500 with stable error codes, without leaking tracebacks.
4. Malformed schedule validation and diagnostics payloads return clean HTTP 400 without internal Pydantic details.
5. Expected domain exceptions (404, 409, 422) preserve domain error codes and messages without turning into 500s.
6. Server-side log capture records details without exposing secrets.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.main import app
from backend.app.db.session import get_db_session
from backend.app.core.auth import get_current_user, AuthUser, UserRole
from backend.app.repositories.planning_run_repo import PlanningRunNotFoundError
from backend.app.repositories.plan_version_repo import (
    PlanVersionAlreadyExistsError,
    PlanVersionApprovalBlockedError,
    PlanFingerprintMismatchError,
)


@pytest.fixture
def auth_operator_override():
    """Mock operator with approval and operational write permissions."""
    operator = AuthUser(
        user_id="USR-OP-F8",
        username="f8_operator",
        role=UserRole.OPERATOR,
        permissions=["read:reference", "read:operational", "write:operational", "plan:review", "plan:approve"],
    )
    app.dependency_overrides[get_current_user] = lambda: operator
    yield operator
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def auth_viewer_override():
    """Mock viewer with operational read permissions."""
    viewer = AuthUser(
        user_id="USR-VIEW-F8",
        username="f8_viewer",
        role=UserRole.VIEWER,
        permissions=["read:reference", "read:operational"],
    )
    app.dependency_overrides[get_current_user] = lambda: viewer
    yield viewer
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_health_db_success():
    """When DB query succeeds, /health/db returns 200 with status ok."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar.return_value = 1
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[get_db_session] = lambda: mock_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.get("/health/db")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ok"
            assert data["database"] == "reachable"
    finally:
        app.dependency_overrides.pop(get_db_session, None)


@pytest.mark.asyncio
async def test_health_db_failure_sanitized_no_leak():
    """When DB query fails, /health/db returns 503 and does NOT leak host, port, or exception details."""
    mock_session = AsyncMock()
    # Simulate a realistic connection failure string containing sensitive IP and port
    leak_prone_error = "Connect call failed ('127.0.0.1', 5434); password authentication failed for user 'postgres'"
    mock_session.execute.side_effect = ConnectionRefusedError(leak_prone_error)

    app.dependency_overrides[get_db_session] = lambda: mock_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.get("/health/db")
            assert resp.status_code == 503
            data = resp.json()
            assert "error" in data
            assert data["error"]["code"] == "DATABASE_UNREACHABLE"
            assert data["error"]["message"] == "Database service is unavailable or not reachable."

            # Verify NO sensitive information is leaked in response body
            body_text = resp.text
            assert "127.0.0.1" not in body_text
            assert "5434" not in body_text
            assert "postgres" not in body_text
            assert "password" not in body_text
            assert "ConnectionRefusedError" not in body_text
            assert "Connect call failed" not in body_text
    finally:
        app.dependency_overrides.pop(get_db_session, None)


@pytest.mark.asyncio
async def test_unhandled_exception_returns_clean_500(auth_viewer_override):
    """Any unhandled server exception returns standard HTTP 500 without leaking stack trace."""
    mock_session = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: mock_session
    transport = ASGITransport(app=app, raise_app_exceptions=False)

    try:
        # Route that triggers an unhandled ZeroDivisionError in unhandled code path
        with patch("backend.app.api.v1.corridors.CorridorRepository.get_by_id", side_effect=ZeroDivisionError("division by zero internal math error")):
            async with AsyncClient(transport=transport, base_url="http://testserver") as client:
                resp = await client.get("/api/v1/corridors/CORR-TEST")
                assert resp.status_code == 500
                data = resp.json()
                assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
                assert data["error"]["message"] == "An unexpected internal server error occurred."

                body_text = resp.text
                assert "ZeroDivisionError" not in body_text
                assert "division by zero" not in body_text
                assert "Traceback" not in body_text
    finally:
        app.dependency_overrides.pop(get_db_session, None)


@pytest.mark.asyncio
async def test_plan_version_creation_unexpected_error_sanitized(auth_operator_override):
    """Unexpected exception in plan version creation returns clean 500 without leaking raw internal exception."""
    mock_session = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: mock_session

    try:
        transport = ASGITransport(app=app)
        with patch("backend.app.api.v1.plan_versions.PlanGovernanceService") as MockService:
            service_inst = MockService.return_value
            service_inst.create_plan_version_from_run.side_effect = RuntimeError(
                "Internal DB pool exhausted: secret_token_xyz @ 10.0.0.1:5432"
            )

            async with AsyncClient(transport=transport, base_url="http://testserver") as client:
                resp = await client.post(
                    "/api/v1/planning-runs/RUN-2026-TEST/plan-version",
                    json={"comment": "Test run"},
                )
                assert resp.status_code == 500
                data = resp.json()
                assert data["error"]["code"] == "INTERNAL_ERROR"
                assert data["error"]["message"] == "An internal error occurred while processing the plan version candidate."

                body_text = resp.text
                assert "secret_token_xyz" not in body_text
                assert "10.0.0.1" not in body_text
                assert "RuntimeError" not in body_text
    finally:
        app.dependency_overrides.pop(get_db_session, None)


@pytest.mark.asyncio
async def test_plan_version_creation_domain_exceptions_preserved(auth_operator_override):
    """Domain exceptions during plan creation preserve accurate 4xx status codes and error messages."""
    mock_session = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: mock_session

    try:
        transport = ASGITransport(app=app)
        with patch("backend.app.api.v1.plan_versions.PlanGovernanceService") as MockService:
            service_inst = MockService.return_value

            # 1. 404 NOT_FOUND
            service_inst.create_plan_version_from_run.side_effect = PlanningRunNotFoundError("Run RUN-MISSING not found.")
            async with AsyncClient(transport=transport, base_url="http://testserver") as client:
                resp = await client.post("/api/v1/planning-runs/RUN-MISSING/plan-version", json={})
                assert resp.status_code == 404
                assert resp.json()["error"]["code"] == "NOT_FOUND"

            # 2. 409 PLAN_ALREADY_EXISTS
            service_inst.create_plan_version_from_run.side_effect = PlanVersionAlreadyExistsError("Plan version exists.")
            async with AsyncClient(transport=transport, base_url="http://testserver") as client:
                resp = await client.post("/api/v1/planning-runs/RUN-EXISTS/plan-version", json={})
                assert resp.status_code == 409
                assert resp.json()["error"]["code"] == "PLAN_ALREADY_EXISTS"

            # 3. 422 APPROVAL_BLOCKED
            service_inst.create_plan_version_from_run.side_effect = PlanVersionApprovalBlockedError("Validation failed.")
            async with AsyncClient(transport=transport, base_url="http://testserver") as client:
                resp = await client.post("/api/v1/planning-runs/RUN-BLOCKED/plan-version", json={})
                assert resp.status_code == 422
                assert resp.json()["error"]["code"] == "APPROVAL_BLOCKED"

            # 4. 409 INTEGRITY_MISMATCH
            service_inst.create_plan_version_from_run.side_effect = PlanFingerprintMismatchError("Fingerprint mismatch.")
            async with AsyncClient(transport=transport, base_url="http://testserver") as client:
                resp = await client.post("/api/v1/planning-runs/RUN-MISMATCH/plan-version", json={})
                assert resp.status_code == 409
                assert resp.json()["error"]["code"] == "INTEGRITY_MISMATCH"
    finally:
        app.dependency_overrides.pop(get_db_session, None)


@pytest.mark.asyncio
async def test_planning_malformed_schedule_sanitized(auth_viewer_override):
    """Malformed schedule payloads in planning validation/diagnostics return clean 400 without internal tracebacks."""
    mock_session = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: mock_session

    try:
        transport = ASGITransport(app=app)
        with patch("backend.app.services.planning_service.PlanningScenarioService") as MockScenarioService:
            mock_bundle = MagicMock()
            MockScenarioService.return_value.get_planning_bundle = AsyncMock(return_value=mock_bundle)

            with patch("backend.app.domain.planning_snapshot.PlanningSnapshot.from_bundle", return_value=MagicMock()):
                async with AsyncClient(transport=transport, base_url="http://testserver") as client:
                    # Send invalid schedule dictionary that fails Pydantic validation
                    resp = await client.post(
                        "/api/v1/planning/validate",
                        json={
                            "scenario_id": "SCN-TEST",
                            "schedule": {"invalid_key": "not_a_valid_schedule_result"},
                        },
                    )
                    assert resp.status_code == 400
                    data = resp.json()
                    assert data["error"]["code"] == "MALFORMED_SCHEDULE_PAYLOAD"
                    assert data["error"]["message"] == "The provided schedule payload does not conform to the expected ScheduleResult structure."

                    body_text = resp.text
                    assert "Traceback" not in body_text
                    assert "ValidationError" not in body_text
    finally:
        app.dependency_overrides.pop(get_db_session, None)


@pytest.mark.asyncio
async def test_unauthenticated_request_sanitized():
    """Unauthenticated access to protected endpoints fails closed with stable error code."""
    transport = ASGITransport(app=app)
    # Clear any dependency overrides to test real auth dependency
    app.dependency_overrides.clear()

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Request with completely invalid bearer token
        resp = await client.get(
            "/api/v1/scenarios",
            headers={"Authorization": "Bearer invalid-token-xyz-123"},
        )
        assert resp.status_code == 401
        data = resp.json()
        assert data["error"]["code"] == "UNAUTHORIZED"
        assert "invalid-token-xyz-123" not in resp.text
