import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_scenarios_api(client: AsyncClient):
    response = await client.get("/api/v1/scenarios")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["scenario_code"] == "SCN-DEMO-001"

    # Get single scenario
    scn_resp = await client.get("/api/v1/scenarios/SCN-DEMO-001")
    assert scn_resp.status_code == 200
    assert scn_resp.json()["scenario_id"] == "SCN-DEMO-001"

    # Get scenario planning bundle
    bundle_resp = await client.get("/api/v1/scenarios/SCN-DEMO-001/bundle")
    assert bundle_resp.status_code == 200
    bundle = bundle_resp.json()
    assert "scenario" in bundle
    assert "tasks" in bundle
    assert "resources" in bundle
    assert len(bundle["tasks"]) >= 20
    assert len(bundle["resources"]) >= 15


@pytest.mark.asyncio
async def test_work_orders_api(client: AsyncClient):
    response = await client.get("/api/v1/work-orders")
    assert response.status_code == 200
    orders = response.json()
    assert len(orders) >= 10

    # Filter by department
    eng_resp = await client.get("/api/v1/work-orders?department=ENGINEERING")
    assert eng_resp.status_code == 200
    eng_orders = eng_resp.json()
    assert len(eng_orders) >= 1
    assert all(o["department"] == "ENGINEERING" for o in eng_orders)

    # Get single work order
    wo_id = orders[0]["work_order_id"]
    wo_resp = await client.get(f"/api/v1/work-orders/{wo_id}")
    assert wo_resp.status_code == 200
    assert wo_resp.json()["work_order_id"] == wo_id


@pytest.mark.asyncio
async def test_tasks_api(client: AsyncClient):
    response = await client.get("/api/v1/tasks")
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) >= 20

    # Filter by status
    planned_resp = await client.get("/api/v1/tasks?status=PLANNED")
    assert planned_resp.status_code == 200
    planned_tasks = planned_resp.json()
    assert len(planned_tasks) >= 1
    assert all(t["status"] == "PLANNED" for t in planned_tasks)

    # Get single task detail
    task_id = tasks[0]["task_id"]
    task_resp = await client.get(f"/api/v1/tasks/{task_id}")
    assert task_resp.status_code == 200
    task_detail = task_resp.json()
    assert task_detail["task_id"] == task_id
    assert "resource_requirements" in task_detail
    assert "rule_reference_ids" in task_detail


@pytest.mark.asyncio
async def test_resources_api(client: AsyncClient):
    response = await client.get("/api/v1/resources")
    assert response.status_code == 200
    resources = response.json()
    assert len(resources) >= 15

    # Filter by type
    tm_resp = await client.get("/api/v1/resources?resource_type=TRACK_MACHINE")
    assert tm_resp.status_code == 200
    machines = tm_resp.json()
    assert len(machines) >= 3
    assert all(m["resource_type"] == "TRACK_MACHINE" for m in machines)

    # Get single resource and its availability
    res_id = resources[0]["resource_id"]
    res_resp = await client.get(f"/api/v1/resources/{res_id}")
    assert res_resp.status_code == 200

    avail_resp = await client.get(f"/api/v1/resources/{res_id}/availability")
    assert avail_resp.status_code == 200
    avails = avail_resp.json()
    assert len(avails) >= 1
    assert avails[0]["resource_id"] == res_id
