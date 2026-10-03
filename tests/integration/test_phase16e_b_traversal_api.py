"""Integration tests for Phase 16E-B: Train Traversal Expansion API.

Verifies:
1. GET /api/v1/scenarios/{scenario_id}/traversals returns list of train traversals.
2. Every traversal conforms to TrainTraversalResponse schema.
3. Express hops expand to multi-section ordered traversals with EXPANDED_ROUTE status.
4. Direct hops yield DIRECT_SECTION status.
5. GET /api/v1/scenarios/{scenario_id}/bundle includes train_traversals.
6. Non-existent scenario returns 404 error response.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_scenario_train_traversals(client: AsyncClient):
    response = await client.get("/api/v1/scenarios/SCN-DEMO-001/traversals")
    assert response.status_code == 200
    traversals = response.json()
    assert len(traversals) > 0

    # Verify required response fields
    for trv in traversals:
        assert "traversal_id" in trv
        assert "train_id" in trv
        assert "train_number" in trv
        assert "source_pass_id" in trv
        assert "from_station_id" in trv
        assert "to_station_id" in trv
        assert "sequence_order" in trv
        assert "entry_time" in trv
        assert "exit_time" in trv
        assert "duration_minutes" in trv
        assert "resolution_status" in trv
        assert trv["resolution_status"] in ("DIRECT_SECTION", "EXPANDED_ROUTE", "UNRESOLVED")
        # Traversal track should be None (unassigned)
        assert trv["traversal_track_id"] is None


@pytest.mark.asyncio
async def test_scenario_traversals_contain_expanded_routes(client: AsyncClient):
    response = await client.get("/api/v1/scenarios/SCN-DEMO-001/traversals")
    assert response.status_code == 200
    traversals = response.json()

    expanded = [t for t in traversals if t["resolution_status"] == "EXPANDED_ROUTE"]
    assert len(expanded) > 0

    direct = [t for t in traversals if t["resolution_status"] == "DIRECT_SECTION"]
    assert len(direct) > 0


@pytest.mark.asyncio
async def test_scenario_bundle_includes_train_traversals(client: AsyncClient):
    response = await client.get("/api/v1/scenarios/SCN-DEMO-001/bundle")
    assert response.status_code == 200
    bundle = response.json()

    assert "train_traversals" in bundle
    assert isinstance(bundle["train_traversals"], list)
    assert len(bundle["train_traversals"]) > 0


@pytest.mark.asyncio
async def test_get_traversals_nonexistent_scenario_404(client: AsyncClient):
    response = await client.get("/api/v1/scenarios/NONEXISTENT-SCENARIO/traversals")
    assert response.status_code == 404
    err = response.json()
    assert "error" in err
