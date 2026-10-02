import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_corridors_api(client: AsyncClient):
    # List corridors
    response = await client.get("/api/v1/corridors")
    assert response.status_code == 200
    corridors = response.json()
    assert len(corridors) >= 1
    assert "X-Total-Count" in response.headers
    assert int(response.headers["X-Total-Count"]) >= 1

    # Get single corridor by ID
    corr_id = corridors[0]["corridor_id"]
    single_resp = await client.get(f"/api/v1/corridors/{corr_id}")
    assert single_resp.status_code == 200
    assert single_resp.json()["corridor_id"] == corr_id
    assert single_resp.json()["classification"] in ["REAL", "DERIVED", "SYNTHETIC", "ASSUMED"]

    # Filter by zone
    zone_resp = await client.get("/api/v1/corridors?zone=NR")
    assert zone_resp.status_code == 200
    assert len(zone_resp.json()) >= 1

    # Not found
    nf_resp = await client.get("/api/v1/corridors/NONEXISTENT_CORR")
    assert nf_resp.status_code == 404
    assert nf_resp.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_movements_api(client: AsyncClient):
    # List movements
    response = await client.get("/api/v1/movements")
    assert response.status_code == 200
    movements = response.json()
    assert len(movements) >= 10
    assert "X-Total-Count" in response.headers
    assert int(response.headers["X-Total-Count"]) >= 50

    # Get single movement by ID
    mov_id = movements[0]["movement_id"]
    single_resp = await client.get(f"/api/v1/movements/{mov_id}")
    assert single_resp.status_code == 200
    assert single_resp.json()["movement_id"] == mov_id

    # Filter by train_id
    train_id = movements[0]["train_id"]
    train_mov_resp = await client.get(f"/api/v1/movements?train_id={train_id}")
    assert train_mov_resp.status_code == 200
    filtered = train_mov_resp.json()
    assert len(filtered) >= 1
    assert all(m["train_id"] == train_id for m in filtered)

    # Not found
    nf_resp = await client.get("/api/v1/movements/NONEXISTENT_MOV")
    assert nf_resp.status_code == 404
    assert nf_resp.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_stations_lookup_and_filtering(client: AsyncClient):
    # Lookup by station_code
    code_resp = await client.get("/api/v1/stations/NDLS")
    assert code_resp.status_code == 200
    assert code_resp.json()["station_code"] == "NDLS"

    # Lookup by station_id
    id_resp = await client.get("/api/v1/stations/STN-NDLS")
    assert id_resp.status_code == 200
    assert id_resp.json()["station_code"] == "NDLS"

    # Filter by zone
    filter_resp = await client.get("/api/v1/stations?zone=NR&limit=50")
    assert filter_resp.status_code == 200
    stations = filter_resp.json()
    assert len(stations) >= 4
    assert all(s["zone"] == "NR" for s in stations)
    assert int(filter_resp.headers["X-Total-Count"]) >= len(stations)

    # Bounded pagination validation
    bad_limit_resp = await client.get("/api/v1/stations?limit=0")
    assert bad_limit_resp.status_code == 422
    assert bad_limit_resp.json()["error"]["code"] == "VALIDATION_ERROR"

    over_limit_resp = await client.get("/api/v1/stations?limit=999")
    assert over_limit_resp.status_code == 422


@pytest.mark.asyncio
async def test_sections_lookup_and_filtering(client: AsyncClient):
    # Lookup by section_code
    code_resp = await client.get("/api/v1/sections/NDLS-GZB")
    assert code_resp.status_code == 200
    assert code_resp.json()["section_code"] == "NDLS-GZB"

    # Lookup by section_id
    id_resp = await client.get("/api/v1/sections/SEC-NDLS-GZB")
    assert id_resp.status_code == 200
    assert id_resp.json()["section_code"] == "NDLS-GZB"

    # Filter by electrified
    elec_resp = await client.get("/api/v1/sections?electrified=true")
    assert elec_resp.status_code == 200
    sections = elec_resp.json()
    assert len(sections) >= 5
    assert all(s["electrified"] is True for s in sections)
    assert "X-Total-Count" in elec_resp.headers


@pytest.mark.asyncio
async def test_trains_lookup_and_filtering(client: AsyncClient):
    # Lookup by train_number
    num_resp = await client.get("/api/v1/trains/12301")
    assert num_resp.status_code == 200
    assert num_resp.json()["train_number"] == "12301"

    # Lookup by train_id
    id_resp = await client.get("/api/v1/trains/TRN-12301")
    assert id_resp.status_code == 200
    assert id_resp.json()["train_number"] == "12301"

    # Filter by train_type
    raj_resp = await client.get("/api/v1/trains?train_type=RAJDHANI")
    assert raj_resp.status_code == 200
    raj_trains = raj_resp.json()
    assert len(raj_trains) >= 1
    assert all(t["train_type"] == "RAJDHANI" for t in raj_trains)
    assert "X-Total-Count" in raj_resp.headers


@pytest.mark.asyncio
async def test_tasks_filtering_and_code_lookup(client: AsyncClient):
    # Lookup by task_code
    code_resp = await client.get("/api/v1/tasks/TSK-TRK-001")
    assert code_resp.status_code == 200
    assert code_resp.json()["task_code"] == "TSK-TRK-001"

    # Lookup by task_id
    id_resp = await client.get("/api/v1/tasks/TSK-0001")
    assert id_resp.status_code == 200
    assert id_resp.json()["task_id"] == "TSK-0001"

    # Multi-field filtering
    multi_resp = await client.get("/api/v1/tasks?scenario_id=SCN-DEMO-001&mandatory=true")
    assert multi_resp.status_code == 200
    tasks = multi_resp.json()
    assert len(tasks) >= 1
    assert all(t["mandatory"] is True for t in tasks)
    assert "X-Total-Count" in multi_resp.headers
    assert "X-Limit" in multi_resp.headers
    assert "X-Offset" in multi_resp.headers

    # Not found
    nf_resp = await client.get("/api/v1/tasks/NONEXISTENT_TASK")
    assert nf_resp.status_code == 404
    assert nf_resp.json()["error"]["code"] == "TASK_NOT_FOUND"


@pytest.mark.asyncio
async def test_scenario_manifest(client: AsyncClient):
    # Get manifest for demo scenario
    response = await client.get("/api/v1/scenarios/SCN-DEMO-001/manifest")
    assert response.status_code == 200
    manifest = response.json()
    assert manifest["scenario_code"] == "SCN-DEMO-001"
    assert manifest["total_work_orders"] >= 10
    assert manifest["total_tasks"] >= 20
    assert manifest["total_mandatory_tasks"] >= 5
    assert manifest["total_resources"] >= 10
    assert manifest["total_dependencies"] >= 1
    assert "tasks_by_type" in manifest
    assert "tasks_by_priority" in manifest
    assert "tasks_by_status" in manifest

    # Nonexistent scenario manifest -> 404
    nf_resp = await client.get("/api/v1/scenarios/NONEXISTENT_SCN/manifest")
    assert nf_resp.status_code == 404
    assert nf_resp.json()["error"]["code"] == "SCENARIO_NOT_FOUND"


@pytest.mark.asyncio
async def test_authentication_headers(client: AsyncClient):
    # Valid planner token
    valid_resp = await client.get(
        "/api/v1/stations",
        headers={"Authorization": "Bearer planner-token-2026"},
    )
    assert valid_resp.status_code == 200

    # Valid admin API key
    valid_key_resp = await client.get(
        "/api/v1/stations",
        headers={"X-API-Key": "admin-token-2026"},
    )
    assert valid_key_resp.status_code == 200

    # Invalid token rejected with 401
    invalid_resp = await client.get(
        "/api/v1/stations",
        headers={"Authorization": "Bearer fraudulent-token"},
    )
    assert invalid_resp.status_code == 401
    assert invalid_resp.json()["error"]["code"] == "UNAUTHORIZED"

    # Invalid API key rejected with 401
    invalid_key_resp = await client.get(
        "/api/v1/stations",
        headers={"X-API-Key": "fraudulent-key"},
    )
    assert invalid_key_resp.status_code == 401
    assert invalid_key_resp.json()["error"]["code"] == "UNAUTHORIZED"
