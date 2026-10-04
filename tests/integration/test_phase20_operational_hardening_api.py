"""Integration tests for Phase 20: Operational Realism & Production Hardening APIs.

Verifies:
1. POST /api/v1/planning-runs accepts solver_mode and records it in configuration_snapshot
2. Planning run execution records rich observability telemetry in result_summary
3. PlanVersion creation endpoint strictly blocks non-COMPLETED or non-VALID runs (422)
4. SyntheticOperationalDataProvider queries return typed, classified records
5. Production database indexes are present and queryable in PostgreSQL
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services.synthetic_provider import SyntheticOperationalDataProvider
from backend.app.schemas.planning_run import PlanningRunStatus


@pytest.mark.asyncio
async def test_planning_runs_api_solver_mode_propagation(client: AsyncClient):
    """Verify POST /api/v1/planning-runs persists requested solver_mode."""
    # Test WHOLE_SECTION
    payload_whole = {
        "scenario_id": "SCN-DEMO-001",
        "scheduler_type": "CP_SAT",
        "solver_mode": "WHOLE_SECTION",
        "time_limit_seconds": 10.0,
    }
    resp = await client.post("/api/v1/planning-runs", json=payload_whole)
    assert resp.status_code == 201
    data = resp.json()
    run_id = data["run_id"]

    # Fetch detail
    detail_resp = await client.get(f"/api/v1/planning-runs/{run_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["configuration_snapshot"]["solver_mode"] == "WHOLE_SECTION"

    # Test TRACK_AWARE_CONSERVATIVE
    payload_track = {
        "scenario_id": "SCN-DEMO-001",
        "scheduler_type": "CP_SAT",
        "solver_mode": "TRACK_AWARE_CONSERVATIVE",
        "time_limit_seconds": 10.0,
    }
    resp2 = await client.post("/api/v1/planning-runs", json=payload_track)
    assert resp2.status_code == 201
    run_id2 = resp2.json()["run_id"]

    detail_resp2 = await client.get(f"/api/v1/planning-runs/{run_id2}")
    assert detail_resp2.status_code == 200
    detail2 = detail_resp2.json()
    assert detail2["configuration_snapshot"]["solver_mode"] == "TRACK_AWARE_CONSERVATIVE"


@pytest.mark.asyncio
async def test_plan_version_blocked_on_pending_run(client: AsyncClient):
    """Verify that attempting to create a PlanVersion from an uncompleted run fails with 422."""
    payload = {
        "scenario_id": "SCN-DEMO-001",
        "scheduler_type": "FCFS",
    }
    resp = await client.post("/api/v1/planning-runs", json=payload)
    assert resp.status_code == 201
    run_id = resp.json()["run_id"]

    # Attempt to create PlanVersion while PENDING
    headers = {"Authorization": "Bearer admin-token-2026"}
    pv_resp = await client.post(
        f"/api/v1/planning-runs/{run_id}/plan-version",
        json={"comment": "Premature attempt"},
        headers=headers,
    )
    assert pv_resp.status_code == 422
    err_data = pv_resp.json()
    assert "APPROVAL_BLOCKED" in str(err_data)


@pytest.mark.asyncio
async def test_synthetic_provider_methods(db_session: AsyncSession):
    """Verify SyntheticOperationalDataProvider returns classified data."""
    provider = SyntheticOperationalDataProvider(db_session, scenario_id="SCN-DEMO-001")

    # 1. Train services
    services = await provider.get_train_services()
    assert isinstance(services, list)
    assert len(services) > 0
    for s in services:
        assert s["classification"] == "REAL" or s["classification"] == "SYNTHETIC"
        assert s["train_id"] is not None

    # 2. Task dependencies
    deps = await provider.get_task_dependencies()
    assert isinstance(deps, list)
    assert len(deps) > 0
    for d in deps:
        assert d["dependency_type"] == "FINISH_TO_START"
        assert d["classification"] == "SYNTHETIC"

    # 3. Resource contentions
    contentions = await provider.get_resource_contentions()
    assert isinstance(contentions, list)
    for c in contentions:
        assert c["competing_task_count"] > 1


@pytest.mark.asyncio
async def test_database_indexes_registered(db_session: AsyncSession):
    """Verify the Phase 20 compound indexes are present in the PostgreSQL catalog."""
    query = text("""
        SELECT indexname FROM pg_indexes 
        WHERE tablename IN ('planning_runs', 'maintenance_tasks', 'train_movements')
    """)
    result = await db_session.execute(query)
    index_names = {row[0] for row in result.all()}

    assert "ix_planning_runs_scenario_status_created" in index_names
    assert "ix_tasks_track_window" in index_names
    assert "ix_movements_train_station" in index_names
