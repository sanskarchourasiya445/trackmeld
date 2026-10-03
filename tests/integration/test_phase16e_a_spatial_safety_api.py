"""Integration tests for Phase 16E-A: Spatial Safety Semantics API.

Verifies:
1. GET /api/v1/tasks includes adjacent_track_impact field.
2. GET /api/v1/tasks/TSK-0001 returns adjacent_track_impact = "CAUTION_ORDER".
3. GET /api/v1/tasks/TSK-0002 returns adjacent_track_impact = "FULL_TRAFFIC_BLOCK".
4. GET /api/v1/tasks/TSK-0003 (unspecified whole-section task) returns adjacent_track_impact = None.
5. GET /api/v1/scenarios/SCN-DEMO-001/bundle preserves adjacent_track_impact on tasks.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_tasks_list_contains_adjacent_track_impact_field(client: AsyncClient):
    response = await client.get("/api/v1/tasks")
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) >= 20

    # Ensure all tasks have adjacent_track_impact in response model
    for t in tasks:
        assert "adjacent_track_impact" in t


@pytest.mark.asyncio
async def test_task_0001_caution_order_adjacent_impact(client: AsyncClient):
    response = await client.get("/api/v1/tasks/TSK-0001")
    assert response.status_code == 200
    task = response.json()
    assert task["task_id"] == "TSK-0001"
    assert task["track_id"] == "TRK-ETW-CNB-UP"
    assert task["adjacent_track_impact"] == "CAUTION_ORDER"


@pytest.mark.asyncio
async def test_task_0002_full_traffic_block_adjacent_impact(client: AsyncClient):
    response = await client.get("/api/v1/tasks/TSK-0002")
    assert response.status_code == 200
    task = response.json()
    assert task["task_id"] == "TSK-0002"
    assert task["track_id"] == "TRK-ARA-PNBE-DN"
    assert task["from_km"] == 12.4
    assert task["to_km"] == 15.8
    assert task["adjacent_track_impact"] == "FULL_TRAFFIC_BLOCK"


@pytest.mark.asyncio
async def test_task_without_track_returns_none_adjacent_impact(client: AsyncClient):
    response = await client.get("/api/v1/tasks/TSK-0003")
    assert response.status_code == 200
    task = response.json()
    assert task["task_id"] == "TSK-0003"
    assert task["track_id"] is None
    assert task["adjacent_track_impact"] is None


@pytest.mark.asyncio
async def test_scenario_bundle_preserves_adjacent_track_impact(client: AsyncClient):
    bundle_resp = await client.get("/api/v1/scenarios/SCN-DEMO-001/bundle")
    assert bundle_resp.status_code == 200
    bundle = bundle_resp.json()

    tasks_by_id = {t["task_id"]: t for t in bundle["tasks"]}
    assert "TSK-0001" in tasks_by_id
    assert "TSK-0002" in tasks_by_id
    assert "TSK-0003" in tasks_by_id

    assert tasks_by_id["TSK-0001"]["adjacent_track_impact"] == "CAUTION_ORDER"
    assert tasks_by_id["TSK-0002"]["adjacent_track_impact"] == "FULL_TRAFFIC_BLOCK"
    assert tasks_by_id["TSK-0003"].get("adjacent_track_impact") is None
