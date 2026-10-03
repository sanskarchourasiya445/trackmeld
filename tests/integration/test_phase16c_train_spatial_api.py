"""Integration tests for Phase 16C: Train Movement Track Semantics API.

Verifies:
1. GET /api/v1/movements includes track_id field
2. GET /api/v1/movements/MOV-12301-NDLS-09 returns seeded track assignment (TRK-NDLS-GZB-UP)
3. GET /api/v1/movements/MOV-12302-NDLS-01 returns seeded track assignment (TRK-NDLS-GZB-DN)
4. Unassigned movements return track_id=None
5. GET /api/v1/scenarios/SCN-DEMO-001/bundle preserves track_id on train_movements
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_movements_list_contains_track_id_field(client: AsyncClient):
    response = await client.get("/api/v1/movements")
    assert response.status_code == 200
    movements = response.json()
    assert len(movements) >= 10

    # Ensure all movements include track_id in the response model
    for m in movements:
        assert "track_id" in m


@pytest.mark.asyncio
async def test_movement_12301_ndls_up_track_assigned(client: AsyncClient):
    response = await client.get("/api/v1/movements/MOV-12301-NDLS-09")
    assert response.status_code == 200
    movement = response.json()
    assert movement["movement_id"] == "MOV-12301-NDLS-09"
    assert movement["train_id"] == "TRN-12301"
    assert movement["station_id"] == "STN-NDLS"
    assert movement["track_id"] == "TRK-NDLS-GZB-UP"


@pytest.mark.asyncio
async def test_movement_12302_ndls_dn_track_assigned(client: AsyncClient):
    response = await client.get("/api/v1/movements/MOV-12302-NDLS-01")
    assert response.status_code == 200
    movement = response.json()
    assert movement["movement_id"] == "MOV-12302-NDLS-01"
    assert movement["train_id"] == "TRN-12302"
    assert movement["station_id"] == "STN-NDLS"
    assert movement["track_id"] == "TRK-NDLS-GZB-DN"


@pytest.mark.asyncio
async def test_movement_without_track_id_returns_none(client: AsyncClient):
    response = await client.get("/api/v1/movements/MOV-12301-HWH-01")
    assert response.status_code == 200
    movement = response.json()
    assert movement["movement_id"] == "MOV-12301-HWH-01"
    assert movement["track_id"] is None


@pytest.mark.asyncio
async def test_scenario_bundle_preserves_train_movement_track_semantics(client: AsyncClient):
    bundle_resp = await client.get("/api/v1/scenarios/SCN-DEMO-001/bundle")
    assert bundle_resp.status_code == 200
    bundle = bundle_resp.json()

    assert "train_movements" in bundle
    movements_by_id = {m["movement_id"]: m for m in bundle["train_movements"]}

    # CNB movements are part of SCN-DEMO-001 (affected by SEC-ETW-CNB task TSK-0001)
    assert "MOV-12301-CNB-08" in movements_by_id
    assert movements_by_id["MOV-12301-CNB-08"]["track_id"] == "TRK-ETW-CNB-UP"

    assert "MOV-12302-CNB-02" in movements_by_id
    assert movements_by_id["MOV-12302-CNB-02"]["track_id"] == "TRK-ETW-CNB-DN"

    assert "MOV-12001-AGC-06" in movements_by_id
    assert movements_by_id["MOV-12001-AGC-06"]["track_id"] is None
