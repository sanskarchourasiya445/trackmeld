"""Integration tests for Phase 16B: Track-Aware Task Spatial APIs.

Verifies:
1. GET /api/v1/tasks includes track_id, from_km, and to_km fields
2. GET /api/v1/tasks/TSK-0001 returns seeded track assignment (UP_MAIN, no chainage)
3. GET /api/v1/tasks/TSK-0002 returns seeded track assignment (DN_MAIN, 12.4–15.8 km)
4. GET /api/v1/scenarios/SCN-DEMO-001/bundle preserves track_id, from_km, to_km on tasks
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_tasks_list_contains_spatial_fields(client: AsyncClient):
    response = await client.get("/api/v1/tasks")
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) >= 20

    # Ensure all tasks have the new spatial keys in response
    for t in tasks:
        assert "track_id" in t
        assert "from_km" in t
        assert "to_km" in t


@pytest.mark.asyncio
async def test_task_0001_up_main_no_chainage(client: AsyncClient):
    response = await client.get("/api/v1/tasks/TSK-0001")
    assert response.status_code == 200
    task = response.json()
    assert task["task_id"] == "TSK-0001"
    assert task["track_id"] == "TRK-ETW-CNB-UP"
    assert task["from_km"] is None
    assert task["to_km"] is None


@pytest.mark.asyncio
async def test_task_0002_dn_main_with_chainage_range(client: AsyncClient):
    response = await client.get("/api/v1/tasks/TSK-0002")
    assert response.status_code == 200
    task = response.json()
    assert task["task_id"] == "TSK-0002"
    assert task["track_id"] == "TRK-ARA-PNBE-DN"
    assert task["from_km"] == 12.4
    assert task["to_km"] == 15.8


@pytest.mark.asyncio
async def test_scenario_bundle_preserves_task_spatial_semantics(client: AsyncClient):
    bundle_resp = await client.get("/api/v1/scenarios/SCN-DEMO-001/bundle")
    assert bundle_resp.status_code == 200
    bundle = bundle_resp.json()

    tasks_by_id = {t["task_id"]: t for t in bundle["tasks"]}
    assert "TSK-0001" in tasks_by_id
    assert "TSK-0002" in tasks_by_id

    t1 = tasks_by_id["TSK-0001"]
    assert t1["track_id"] == "TRK-ETW-CNB-UP"
    assert t1.get("from_km") is None
    assert t1.get("to_km") is None

    t2 = tasks_by_id["TSK-0002"]
    assert t2["track_id"] == "TRK-ARA-PNBE-DN"
    assert t2["from_km"] == 12.4
    assert t2["to_km"] == 15.8
