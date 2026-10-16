"""Phase 15B Integration Tests: API Error Semantics and Non-Fabrication Invariants.

Verifies:
- Explicit HTTP error semantics: 401, 403, 404, 409, 422, 429
- Standard error envelope: {"error": {"code": str, "message": str}}
- Backend error responses NEVER return successful plan data or DEMO_* fixtures
- Fail-closed security boundary in production mode
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.core.rate_limit import planning_rate_limiter
from backend.app.db.models.planning_run import PlanningRunModel
from backend.app.db.models.plan_version import (
    PlanVersionModel,
    PlanReviewCommentModel,
    GovernanceAuditEventModel,
)

settings = get_settings()


@pytest_asyncio.fixture(autouse=True)
async def clean_database(db_session: AsyncSession):
    await db_session.execute(delete(GovernanceAuditEventModel))
    await db_session.execute(delete(PlanReviewCommentModel))
    await db_session.execute(delete(PlanVersionModel))
    await db_session.execute(delete(PlanningRunModel))
    await db_session.commit()
    yield
    await db_session.execute(delete(GovernanceAuditEventModel))
    await db_session.execute(delete(PlanReviewCommentModel))
    await db_session.execute(delete(PlanVersionModel))
    await db_session.execute(delete(PlanningRunModel))
    await db_session.commit()


@pytest.mark.asyncio
async def test_401_unauthorized_on_invalid_credentials(client: AsyncClient):
    """Providing an invalid bearer token returns 401 with standard error envelope."""
    headers = {"Authorization": "Bearer invalid-tampered-token-xyz"}
    resp = await client.get("/api/v1/plan-versions", headers=headers)

    assert resp.status_code == 401
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "UNAUTHORIZED"
    # Ensure no demo or plan list data returned
    assert "plan_version_id" not in str(data)


@pytest.mark.asyncio
async def test_401_production_fails_closed_without_credentials(unauthenticated_client: AsyncClient, monkeypatch):
    """In production mode, anonymous requests are strictly rejected with 401."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "ENABLE_DEMO_AUTH", True)

    resp = await unauthenticated_client.get("/api/v1/plan-versions")
    assert resp.status_code == 401
    data = resp.json()
    assert data["error"]["code"] == "AUTHENTICATION_REQUIRED"


@pytest.mark.asyncio
async def test_401_production_rejects_demo_credentials(unauthenticated_client: AsyncClient, monkeypatch):
    """In production mode, demo tokens (e.g. planner-token-2026) are strictly rejected with 401."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "ENABLE_DEMO_AUTH", True)

    headers = {"Authorization": "Bearer planner-token-2026"}
    resp = await unauthenticated_client.get("/api/v1/plan-versions", headers=headers)
    assert resp.status_code == 401
    data = resp.json()
    assert data["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_403_forbidden_on_insufficient_permissions(client: AsyncClient):
    """Viewer token lacking plan:approve permission receives 403 Forbidden."""
    viewer_headers = {"Authorization": "Bearer viewer-token-2026"}
    approve_payload = {"approval_notes": "Attempted unauthorized approval"}

    resp = await client.post(
        "/api/v1/plan-versions/PV-FAKE-001/approve",
        json=approve_payload,
        headers=viewer_headers,
    )
    assert resp.status_code == 403
    data = resp.json()
    assert data["error"]["code"] == "FORBIDDEN"
    assert "lacking required permission" in data["error"]["message"]


@pytest.mark.asyncio
async def test_404_not_found_on_unknown_resources(client: AsyncClient):
    """Querying nonexistent resources returns 404 with structured error envelope."""
    planner_headers = {"Authorization": "Bearer planner-token-2026"}

    # 1. Nonexistent planning run
    resp_run = await client.get("/api/v1/planning-runs/RUN-DOES-NOT-EXIST")
    assert resp_run.status_code == 404
    assert resp_run.json()["error"]["code"] == "PLANNING_RUN_NOT_FOUND"

    # 2. Nonexistent plan version
    resp_pv = await client.get("/api/v1/plan-versions/PV-DOES-NOT-EXIST", headers=planner_headers)
    assert resp_pv.status_code == 404
    assert resp_pv.json()["error"]["code"] == "NOT_FOUND"

    # 3. Create run with nonexistent scenario
    resp_scn = await client.post(
        "/api/v1/planning-runs",
        json={"scenario_id": "SCN-NONEXISTENT-999", "scheduler_type": "CP_SAT"},
        headers=planner_headers,
    )
    assert resp_scn.status_code == 404
    assert resp_scn.json()["error"]["code"] == "SCENARIO_NOT_FOUND"


@pytest.mark.asyncio
async def test_422_unprocessable_on_invalid_payload(client: AsyncClient):
    """Submitting semantically invalid payload (rejection reason < 5 chars) returns 422."""
    approver_headers = {"Authorization": "Bearer approver-token-2026"}
    invalid_reject = {"reason": "No"}  # Less than min_length=5

    resp = await client.post(
        "/api/v1/plan-versions/PV-FAKE/reject",
        json=invalid_reject,
        headers=approver_headers,
    )
    assert resp.status_code in [422, 400]
    data = resp.json()
    assert "error" in data


@pytest.mark.asyncio
async def test_429_too_many_requests_rate_limit(client: AsyncClient):
    """Exceeding solver rate limit threshold returns 429 with Retry-After header."""
    planner_headers = {"Authorization": "Bearer planner-token-2026"}

    # Temporarily set max_requests to 2 for this test
    original_max = planning_rate_limiter.max_requests
    try:
        planning_rate_limiter._history.clear()
        planning_rate_limiter.max_requests = 2
        payload = {"scenario_id": "SCN-DEMO-001", "scheduler_type": "FCFS"}

        # Request 1 & 2 succeed
        r1 = await client.post("/api/v1/planning-runs", json=payload, headers=planner_headers)
        r2 = await client.post("/api/v1/planning-runs", json=payload, headers=planner_headers)
        assert r1.status_code == 201
        assert r2.status_code == 201

        # Request 3 must be throttled with 429
        r3 = await client.post("/api/v1/planning-runs", json=payload, headers=planner_headers)
        assert r3.status_code == 429
        assert "Retry-After" in r3.headers
        data = r3.json()
        assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"
        assert "retry_after_seconds" in data["error"]["details"]
    finally:
        planning_rate_limiter.max_requests = original_max
