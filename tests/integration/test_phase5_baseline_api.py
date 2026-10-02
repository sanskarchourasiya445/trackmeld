"""Integration tests for Phase 5 baseline planning and benchmarking APIs."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_baseline_fcfs_api_execution(client: AsyncClient):
    payload = {
        "scenario_id": "SCN-DEMO-001",
        "scheduler_type": "FCFS",
        "max_candidate_attempts": 20,
    }
    response = await client.post("/api/v1/planning/baseline", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["scheduler_type"] == "FCFS"
    assert data["scenario_id"] == "SCN-DEMO-001"
    assert "snapshot_id" in data
    assert data["status"] in ["COMPLETED", "COMPLETED_WITH_UNSCHEDULED_TASKS"]
    assert "metrics" in data
    assert data["metrics"]["total_tasks"] == 30
    assert data["metrics"]["scheduled_tasks"] > 0
    assert len(data["scheduled_tasks"]) > 0
    assert "execution_time_ms" in data
    assert "decision_trace" in data


@pytest.mark.asyncio
async def test_baseline_priority_greedy_api_execution(client: AsyncClient):
    payload = {
        "scenario_id": "SCN-DEMO-001",
        "scheduler_type": "PRIORITY_GREEDY",
        "max_candidate_attempts": 20,
    }
    response = await client.post("/api/v1/planning/baseline", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["scheduler_type"] == "PRIORITY_GREEDY"
    assert data["scenario_id"] == "SCN-DEMO-001"
    assert data["status"] in ["COMPLETED", "COMPLETED_WITH_UNSCHEDULED_TASKS"]
    assert data["metrics"]["total_tasks"] == 30
    assert data["metrics"]["scheduled_tasks"] > 0
    # Every scheduled task must contain priority score and breakdown
    for st in data["scheduled_tasks"]:
        assert st["priority_score"] is not None
        assert st["priority_breakdown"] is not None


@pytest.mark.asyncio
async def test_benchmark_comparison_api(client: AsyncClient):
    payload = {
        "scenario_id": "SCN-DEMO-001",
        "max_candidate_attempts": 20,
    }
    response = await client.post("/api/v1/planning/benchmark", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["scenario_id"] == "SCN-DEMO-001"
    assert "schedules" in data
    assert "FCFS" in data["schedules"]
    assert "PRIORITY_GREEDY" in data["schedules"]
    assert "comparison_table" in data
    assert len(data["comparison_table"]) > 5

    # Check both schedules ran on the EXACT same snapshot
    assert data["schedules"]["FCFS"]["snapshot_id"] == data["schedules"]["PRIORITY_GREEDY"]["snapshot_id"]
    assert data["schedules"]["FCFS"]["metrics"]["total_tasks"] == data["schedules"]["PRIORITY_GREEDY"]["metrics"]["total_tasks"]


@pytest.mark.asyncio
async def test_baseline_nonexistent_scenario(client: AsyncClient):
    payload = {
        "scenario_id": "SCN-DOES-NOT-EXIST",
        "scheduler_type": "FCFS",
    }
    response = await client.post("/api/v1/planning/baseline", json=payload)
    assert response.status_code == 404
