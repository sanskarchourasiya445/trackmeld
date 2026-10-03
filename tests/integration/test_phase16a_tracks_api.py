"""Integration tests for Phase 16A Track APIs and Scenario Bundle propagation.

Verifies:
1. GET /api/v1/tracks lists all tracks with pagination and count headers
2. GET /api/v1/tracks?section_id=... filters tracks correctly
3. GET /api/v1/tracks/{track_id} retrieves a specific track
4. GET /api/v1/tracks/{track_id} returns 404 for unknown track
5. GET /api/v1/scenarios/SCN-DEMO-001/bundle contains tracks array
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_tracks_list_api(client: AsyncClient):
    response = await client.get("/api/v1/tracks")
    assert response.status_code == 200
    tracks = response.json()
    assert isinstance(tracks, list)
    assert len(tracks) >= 50
    assert "x-total-count" in response.headers

    # Validate schema of track entity
    first = tracks[0]
    assert "track_id" in first
    assert "section_id" in first
    assert "track_code" in first
    assert "direction" in first
    assert "electrified" in first
    assert first["direction"] in ["UP", "DOWN", "BIDIRECTIONAL"]


@pytest.mark.asyncio
async def test_tracks_filter_by_section(client: AsyncClient):
    # Fetch first track to get a valid section_id
    response = await client.get("/api/v1/tracks?limit=5")
    assert response.status_code == 200
    tracks = response.json()
    assert len(tracks) > 0

    target_sec_id = tracks[0]["section_id"]
    filtered_resp = await client.get(f"/api/v1/tracks?section_id={target_sec_id}")
    assert filtered_resp.status_code == 200
    filtered_tracks = filtered_resp.json()
    assert len(filtered_tracks) >= 1
    assert all(t["section_id"] == target_sec_id for t in filtered_tracks)


@pytest.mark.asyncio
async def test_track_get_by_id(client: AsyncClient):
    # Fetch all tracks to get an ID
    response = await client.get("/api/v1/tracks?limit=1")
    assert response.status_code == 200
    target_id = response.json()[0]["track_id"]

    # Fetch by ID
    single_resp = await client.get(f"/api/v1/tracks/{target_id}")
    assert single_resp.status_code == 200
    track_data = single_resp.json()
    assert track_data["track_id"] == target_id
    assert "track_code" in track_data
    assert "direction" in track_data


@pytest.mark.asyncio
async def test_track_not_found(client: AsyncClient):
    response = await client.get("/api/v1/tracks/TRK-DOES-NOT-EXIST")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_scenario_bundle_includes_tracks(client: AsyncClient):
    bundle_resp = await client.get("/api/v1/scenarios/SCN-DEMO-001/bundle")
    assert bundle_resp.status_code == 200
    bundle = bundle_resp.json()

    assert "tracks" in bundle
    assert isinstance(bundle["tracks"], list)
    assert len(bundle["tracks"]) >= 20

    # Ensure track fields are populated
    sample_trk = bundle["tracks"][0]
    assert "track_id" in sample_trk
    assert "section_id" in sample_trk
    assert "track_code" in sample_trk
    assert "direction" in sample_trk
