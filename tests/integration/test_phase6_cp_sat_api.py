"""Integration tests for Phase 6 CP-SAT mathematical optimization APIs."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_optimize_cp_sat_api_execution(client: AsyncClient):
    """POST /api/v1/planning/optimize executes discrete CP-SAT optimization on SCN-DEMO-001."""
    payload = {
        "scenario_id": "SCN-DEMO-001",
        "time_limit_seconds": 15.0,
        "num_search_workers": 1,
        "random_seed": 0,
    }
    response = await client.post("/api/v1/planning/optimize", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["scheduler_type"] == "CP_SAT"
    assert data["scenario_id"] == "SCN-DEMO-001"
    assert "snapshot_id" in data
    assert data["status"] in ["OPTIMAL", "FEASIBLE"]
    assert "metrics" in data
    assert data["metrics"]["total_tasks"] == 30
    assert data["metrics"]["scheduled_tasks"] > 0
    assert len(data["scheduled_tasks"]) > 0
    assert "execution_time_ms" in data
    assert "decision_trace" in data

    # Verify solver diagnostics payload
    assert "solver_diagnostics" in data
    diag = data["solver_diagnostics"]
    assert diag is not None
    assert diag["status"] in ["OPTIMAL", "FEASIBLE"]
    assert diag["wall_time_seconds"] > 0
    assert diag["num_booleans"] > 0
    assert diag["num_integers"] > 0
    assert diag["num_constraints"] > 0
    assert diag["num_intervals"] > 0
    assert diag["num_workers"] == 1
    assert diag["random_seed"] == 0

    # Verify priority score breakdown on scheduled tasks
    for st in data["scheduled_tasks"]:
        assert st["priority_score"] is not None
        assert st["priority_breakdown"] is not None
        assert st["interval"]["start"] < st["interval"]["end"]
        assert st["possession_interval"]["start"] <= st["interval"]["start"]
        assert st["possession_interval"]["end"] >= st["interval"]["end"]


@pytest.mark.asyncio
async def test_optimize_cp_sat_custom_config(client: AsyncClient):
    """POST /api/v1/planning/optimize respects custom time limits and configurations."""
    payload = {
        "scenario_id": "SCN-DEMO-001",
        "time_limit_seconds": 5.0,
        "num_search_workers": 2,
        "random_seed": 42,
    }
    response = await client.post("/api/v1/planning/optimize", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["scheduler_type"] == "CP_SAT"
    diag = data["solver_diagnostics"]
    assert diag["num_workers"] == 2
    assert diag["random_seed"] == 42


@pytest.mark.asyncio
async def test_benchmark_comparison_api_with_cpsat(client: AsyncClient):
    """POST /api/v1/planning/benchmark includes CP-SAT when include_cpsat is True."""
    payload = {
        "scenario_id": "SCN-DEMO-001",
        "max_candidate_attempts": 20,
        "include_cpsat": True,
        "cpsat_time_limit": 5.0,
    }
    response = await client.post("/api/v1/planning/benchmark", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["scenario_id"] == "SCN-DEMO-001"
    assert "schedules" in data
    assert "FCFS" in data["schedules"]
    assert "PRIORITY_GREEDY" in data["schedules"]
    assert "CP_SAT" in data["schedules"]

    # Check all three schedules ran on the EXACT same snapshot
    snap_fcfs = data["schedules"]["FCFS"]["snapshot_id"]
    snap_prio = data["schedules"]["PRIORITY_GREEDY"]["snapshot_id"]
    snap_cpsat = data["schedules"]["CP_SAT"]["snapshot_id"]
    assert snap_fcfs == snap_prio == snap_cpsat

    # Verify comparison table contains all 3 algorithms
    assert "comparison_table" in data
    row = data["comparison_table"][0]
    assert "FCFS" in row
    assert "Priority-Greedy" in row
    assert "CP-SAT" in row


@pytest.mark.asyncio
async def test_optimize_nonexistent_scenario(client: AsyncClient):
    """POST /api/v1/planning/optimize returns 404 for unknown scenario."""
    payload = {
        "scenario_id": "SCN-NONEXISTENT",
        "time_limit_seconds": 5.0,
    }
    response = await client.post("/api/v1/planning/optimize", json=payload)
    assert response.status_code == 404
