import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_evaluate_task_api_inside_window(client: AsyncClient):
    payload = {
        "task_id": "TSK-TRK-001",
        "start_time": "2026-10-10T08:00:00Z",
        "end_time": "2026-10-10T11:00:00Z",
        "scenario_id": "SCN-DEMO-001",
    }
    response = await client.post("/api/v1/compatibility/evaluate-task", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == "TSK-0001"
    assert "compatible" in data
    assert "feasible_hard" in data
    assert "admissible_soft" in data
    assert "evaluated_interval" in data
    assert "possession_interval" in data
    assert len(data["affected_sections"]) >= 1
    assert "rule_evidence" in data


@pytest.mark.asyncio
async def test_evaluate_task_api_outside_window(client: AsyncClient):
    # Window for TSK-TRK-001 is 2026-10-10 07:00 to 12:00
    payload = {
        "task_id": "TSK-TRK-001",
        "start_time": "2026-10-11T14:00:00Z",
        "end_time": "2026-10-11T17:00:00Z",
        "scenario_id": "SCN-DEMO-001",
    }
    response = await client.post("/api/v1/compatibility/evaluate-task", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert not data["compatible"]
    assert not data["feasible_hard"]
    assert "TASK_WINDOW_CONFLICT" in data["reason_codes"]
    assert any(c["reason_code"] == "TASK_WINDOW_CONFLICT" for c in data["conflicts"])


@pytest.mark.asyncio
async def test_evaluate_task_api_invalid_interval(client: AsyncClient):
    # Inverted start and end
    payload = {
        "task_id": "TSK-TRK-001",
        "start_time": "2026-10-10T12:00:00Z",
        "end_time": "2026-10-10T09:00:00Z",
        "scenario_id": "SCN-DEMO-001",
    }
    response = await client.post("/api/v1/compatibility/evaluate-task", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert not data["compatible"]
    assert not data["feasible_hard"]
    assert "INVALID_INTERVAL" in data["reason_codes"]


@pytest.mark.asyncio
async def test_evaluate_task_api_not_found(client: AsyncClient):
    payload = {
        "task_id": "NONEXISTENT_TASK_ID",
        "start_time": "2026-10-10T08:00:00Z",
        "end_time": "2026-10-10T11:00:00Z",
    }
    response = await client.post("/api/v1/compatibility/evaluate-task", json=payload)
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "TASK_NOT_FOUND"
