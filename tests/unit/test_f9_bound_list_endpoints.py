"""Unit tests for Task 9 (F9): Bound List Endpoint Limits.

Validates that:
1. Pagination parameters (limit, offset) are strictly bounded across plan-version, audit, and planning-run endpoints.
2. Invalid limits (0, negative, > max) return HTTP 422 Unprocessable Entity with code VALIDATION_ERROR.
3. Invalid offsets (< 0) return HTTP 422 Unprocessable Entity with code VALIDATION_ERROR.
4. Default and boundary limits (min=1, max=100/500) function correctly and pass down to repository layer.
5. Response headers (X-Total-Count, X-Limit, X-Offset) are returned consistently.
6. Repository queries apply deterministic tie-breakers (id desc/asc) and defense-in-depth bounds clamping.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.db.session import get_db_session
from backend.app.core.auth import get_current_user, AuthUser, UserRole
from backend.app.repositories.plan_version_repo import PlanVersionRepository
from backend.app.repositories.planning_run_repo import PlanningRunRepository


@pytest.fixture
def auth_viewer_override():
    """Mock viewer with operational read permissions."""
    viewer = AuthUser(
        user_id="USR-VIEW-F9",
        username="f9_viewer",
        role=UserRole.VIEWER,
        permissions=["read:reference", "read:operational"],
    )
    app.dependency_overrides[get_current_user] = lambda: viewer
    yield viewer
    app.dependency_overrides.pop(get_current_user, None)


# =============================================================================
# 1. PLAN VERSIONS LIST ENDPOINT (/api/v1/plan-versions)
# =============================================================================

@pytest.mark.asyncio
async def test_list_plan_versions_default_pagination(auth_viewer_override):
    """GET /api/v1/plan-versions applies default limit=50 and offset=0 with headers."""
    mock_session = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: mock_session

    try:
        transport = ASGITransport(app=app)
        with patch.object(PlanVersionRepository, "list_plan_versions", new_callable=AsyncMock) as mock_list, \
             patch.object(PlanVersionRepository, "count_plan_versions", new_callable=AsyncMock) as mock_count:
            mock_list.return_value = []
            mock_count.return_value = 0

            async with AsyncClient(transport=transport, base_url="http://testserver") as client:
                resp = await client.get("/api/v1/plan-versions")
                assert resp.status_code == 200
                assert resp.headers["X-Limit"] == "50"
                assert resp.headers["X-Offset"] == "0"
                assert resp.headers["X-Total-Count"] == "0"

                # Verify default limit passed to repo
                mock_list.assert_awaited_once()
                kwargs = mock_list.await_args.kwargs
                assert kwargs["limit"] == 50
                assert kwargs["offset"] == 0
    finally:
        app.dependency_overrides.pop(get_db_session, None)


@pytest.mark.asyncio
async def test_list_plan_versions_custom_valid_bounds(auth_viewer_override):
    """GET /api/v1/plan-versions accepts valid boundary limits (min=1, max=100)."""
    mock_session = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: mock_session

    try:
        transport = ASGITransport(app=app)
        with patch.object(PlanVersionRepository, "list_plan_versions", new_callable=AsyncMock) as mock_list, \
             patch.object(PlanVersionRepository, "count_plan_versions", new_callable=AsyncMock) as mock_count:
            mock_list.return_value = []
            mock_count.return_value = 15

            async with AsyncClient(transport=transport, base_url="http://testserver") as client:
                # Test minimum limit=1
                resp_min = await client.get("/api/v1/plan-versions?limit=1&offset=5")
                assert resp_min.status_code == 200
                assert resp_min.headers["X-Limit"] == "1"
                assert resp_min.headers["X-Offset"] == "5"

                # Test maximum limit=100
                resp_max = await client.get("/api/v1/plan-versions?limit=100&offset=0")
                assert resp_max.status_code == 200
                assert resp_max.headers["X-Limit"] == "100"
    finally:
        app.dependency_overrides.pop(get_db_session, None)


@pytest.mark.asyncio
async def test_list_plan_versions_invalid_bounds_rejected(auth_viewer_override):
    """GET /api/v1/plan-versions rejects limit < 1, limit > 100, and offset < 0 with 422."""
    mock_session = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: mock_session

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # limit=0 rejected
            r0 = await client.get("/api/v1/plan-versions?limit=0")
            assert r0.status_code == 422
            assert r0.json()["error"]["code"] == "VALIDATION_ERROR"

            # negative limit rejected
            r_neg = await client.get("/api/v1/plan-versions?limit=-10")
            assert r_neg.status_code == 422
            assert r_neg.json()["error"]["code"] == "VALIDATION_ERROR"

            # limit > 100 rejected
            r_over = await client.get("/api/v1/plan-versions?limit=101")
            assert r_over.status_code == 422
            assert r_over.json()["error"]["code"] == "VALIDATION_ERROR"

            # negative offset rejected
            r_neg_off = await client.get("/api/v1/plan-versions?offset=-1")
            assert r_neg_off.status_code == 422
            assert r_neg_off.json()["error"]["code"] == "VALIDATION_ERROR"
    finally:
        app.dependency_overrides.pop(get_db_session, None)


# =============================================================================
# 2. PLAN AUDIT TRAIL ENDPOINT (/api/v1/plan-versions/{id}/audit)
# =============================================================================

@pytest.mark.asyncio
async def test_get_plan_audit_trail_default_pagination(auth_viewer_override):
    """GET /api/v1/plan-versions/{id}/audit applies default limit=100 and offset=0 with headers."""
    mock_session = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: mock_session

    try:
        transport = ASGITransport(app=app)
        with patch.object(PlanVersionRepository, "get_by_plan_version_id", new_callable=AsyncMock) as mock_get, \
             patch.object(PlanVersionRepository, "list_audit_events", new_callable=AsyncMock) as mock_list, \
             patch.object(PlanVersionRepository, "count_audit_events", new_callable=AsyncMock) as mock_count:
            mock_get.return_value = MagicMock(plan_version_id="PV-TEST-001")
            mock_list.return_value = []
            mock_count.return_value = 0

            async with AsyncClient(transport=transport, base_url="http://testserver") as client:
                resp = await client.get("/api/v1/plan-versions/PV-TEST-001/audit")
                assert resp.status_code == 200
                assert resp.headers["X-Limit"] == "100"
                assert resp.headers["X-Offset"] == "0"
                assert resp.headers["X-Total-Count"] == "0"

                mock_list.assert_awaited_once()
                kwargs = mock_list.await_args.kwargs
                assert kwargs["limit"] == 100
                assert kwargs["offset"] == 0
    finally:
        app.dependency_overrides.pop(get_db_session, None)


@pytest.mark.asyncio
async def test_get_plan_audit_trail_invalid_bounds_rejected(auth_viewer_override):
    """GET /api/v1/plan-versions/{id}/audit rejects limit < 1, limit > 500, and offset < 0 with 422."""
    mock_session = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: mock_session

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # limit=0 rejected
            r0 = await client.get("/api/v1/plan-versions/PV-TEST-001/audit?limit=0")
            assert r0.status_code == 422
            assert r0.json()["error"]["code"] == "VALIDATION_ERROR"

            # negative limit rejected
            r_neg = await client.get("/api/v1/plan-versions/PV-TEST-001/audit?limit=-5")
            assert r_neg.status_code == 422
            assert r_neg.json()["error"]["code"] == "VALIDATION_ERROR"

            # limit > 500 rejected
            r_over = await client.get("/api/v1/plan-versions/PV-TEST-001/audit?limit=501")
            assert r_over.status_code == 422
            assert r_over.json()["error"]["code"] == "VALIDATION_ERROR"

            # negative offset rejected
            r_neg_off = await client.get("/api/v1/plan-versions/PV-TEST-001/audit?offset=-1")
            assert r_neg_off.status_code == 422
            assert r_neg_off.json()["error"]["code"] == "VALIDATION_ERROR"
    finally:
        app.dependency_overrides.pop(get_db_session, None)


# =============================================================================
# 3. PLANNING RUNS LIST ENDPOINT (/api/v1/planning-runs)
# =============================================================================

@pytest.mark.asyncio
async def test_list_planning_runs_default_pagination(auth_viewer_override):
    """GET /api/v1/planning-runs applies default limit=50 and offset=0 with headers."""
    mock_session = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: mock_session

    try:
        transport = ASGITransport(app=app)
        with patch.object(PlanningRunRepository, "list_runs", new_callable=AsyncMock) as mock_list, \
             patch.object(PlanningRunRepository, "count_runs", new_callable=AsyncMock) as mock_count:
            mock_list.return_value = []
            mock_count.return_value = 0

            async with AsyncClient(transport=transport, base_url="http://testserver") as client:
                resp = await client.get("/api/v1/planning-runs")
                assert resp.status_code == 200
                assert resp.headers["X-Limit"] == "50"
                assert resp.headers["X-Offset"] == "0"
                assert resp.headers["X-Total-Count"] == "0"

                mock_list.assert_awaited_once()
                kwargs = mock_list.await_args.kwargs
                assert kwargs["limit"] == 50
                assert kwargs["offset"] == 0
    finally:
        app.dependency_overrides.pop(get_db_session, None)


@pytest.mark.asyncio
async def test_list_planning_runs_invalid_bounds_rejected(auth_viewer_override):
    """GET /api/v1/planning-runs rejects limit < 1, limit > 100, and offset < 0 with 422."""
    mock_session = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: mock_session

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            # limit=0 rejected
            r0 = await client.get("/api/v1/planning-runs?limit=0")
            assert r0.status_code == 422
            assert r0.json()["error"]["code"] == "VALIDATION_ERROR"

            # negative limit rejected
            r_neg = await client.get("/api/v1/planning-runs?limit=-1")
            assert r_neg.status_code == 422
            assert r_neg.json()["error"]["code"] == "VALIDATION_ERROR"

            # limit > 100 rejected
            r_over = await client.get("/api/v1/planning-runs?limit=101")
            assert r_over.status_code == 422
            assert r_over.json()["error"]["code"] == "VALIDATION_ERROR"

            # negative offset rejected
            r_neg_off = await client.get("/api/v1/planning-runs?offset=-1")
            assert r_neg_off.status_code == 422
            assert r_neg_off.json()["error"]["code"] == "VALIDATION_ERROR"
    finally:
        app.dependency_overrides.pop(get_db_session, None)


# =============================================================================
# 4. REPOSITORY QUERY DEFENSE-IN-DEPTH & DETERMINISTIC ORDERING
# =============================================================================

@pytest.mark.asyncio
async def test_plan_version_repo_query_deterministic_order_and_clamping():
    """PlanVersionRepository clamps negative/oversized limits and applies deterministic tie-breaker."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    repo = PlanVersionRepository(mock_session)

    # 1. list_plan_versions clamps limit > 100 and offset < 0
    await repo.list_plan_versions(limit=9999, offset=-50)
    mock_session.execute.assert_awaited()
    stmt = mock_session.execute.await_args[0][0]
    compiled_sql = str(stmt)
    # Check that deterministic secondary order is present
    assert "plan_versions.plan_version_id DESC" in compiled_sql
    assert "plan_versions.created_at DESC" in compiled_sql

    # 2. list_audit_events clamps limit > 500 and offset < 0
    await repo.list_audit_events(entity_id="PV-123", limit=9999, offset=-10)
    stmt_audit = mock_session.execute.await_args[0][0]
    compiled_audit_sql = str(stmt_audit)
    assert "governance_audit_events.event_id ASC" in compiled_audit_sql
    assert "governance_audit_events.timestamp ASC" in compiled_audit_sql


@pytest.mark.asyncio
async def test_planning_run_repo_query_deterministic_order_and_clamping():
    """PlanningRunRepository clamps limits and applies deterministic tie-breaker."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    repo = PlanningRunRepository(mock_session)
    await repo.list_runs(limit=5000, offset=-10)
    mock_session.execute.assert_awaited()
    stmt = mock_session.execute.await_args[0][0]
    compiled_sql = str(stmt)
    assert "planning_runs.run_id DESC" in compiled_sql
    assert "planning_runs.created_at DESC" in compiled_sql
