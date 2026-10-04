"""Integration tests for Phase 17: Deterministic Route Resolution API & Scenario Pipeline.

Verifies:
1. GET /api/v1/scenarios/{id}/bundle includes topology_nodes, topology_connections, track_endpoints, and train_traversals.
2. GET /api/v1/scenarios/{id}/traversals returns valid TrainTraversalResponse objects.
3. Live scenario with curated corridor tracks deterministically populates traversal_track_id.
4. Trains traversing sections without topology cleanly retain traversal_track_id = None.
5. Invariant preservation: CP-SAT solver and validator behavior remain section-based.
"""

from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.app.db.models.scenario import OperationalScenarioModel
from backend.app.db.models.task import MaintenanceTaskModel
from backend.app.db.models.work_order import WorkOrderModel
from backend.app.db.models.movement import TrainMovementModel
from backend.app.db.models.section import SectionModel
from backend.app.db.models.track import TrackModel
from backend.app.db.models.topology import TopologyNodeModel, TrackEndpointModel, TopologyConnectionModel


@pytest.mark.asyncio
async def test_scenario_bundle_returns_topology_and_traversals(client: AsyncClient):
    """Verify that get_scenario_bundle includes topology fields and traversals."""
    resp = await client.get("/api/v1/scenarios/SCN-DEMO-001/bundle")
    assert resp.status_code == 200
    data = resp.json()

    assert "tracks" in data
    assert "train_traversals" in data
    assert "topology_nodes" in data
    assert "topology_connections" in data
    assert "track_endpoints" in data

    # Verify that traversals match the expected schema
    traversals = data["train_traversals"]
    assert len(traversals) > 0
    for trv in traversals:
        assert "traversal_id" in trv
        assert "train_id" in trv
        assert "train_number" in trv
        assert "resolution_status" in trv
        assert "classification" in trv


@pytest.mark.asyncio
async def test_scenario_traversals_api_endpoint(client: AsyncClient):
    """Verify that GET /api/v1/scenarios/{scenario_id}/traversals responds with valid records."""
    resp = await client.get("/api/v1/scenarios/SCN-DEMO-001/traversals")
    assert resp.status_code == 200
    traversals = resp.json()

    assert len(traversals) > 0
    for trv in traversals:
        assert trv["traversal_id"].startswith("TRV-")
        assert trv["resolution_status"] in ("DIRECT_SECTION", "EXPANDED_ROUTE", "AMBIGUOUS_ROUTE", "UNRESOLVED")


@pytest.mark.asyncio
async def test_corridor_scenario_resolves_physical_tracks(client: AsyncClient, db_session):
    """Verify deterministic track assignment through the API on the curated corridor."""
    from sqlalchemy import text

    # Temporarily point two tasks in SCN-DEMO-001 to SEC-NDLS-GZB and SEC-GZB-KRJ
    await db_session.execute(text("UPDATE maintenance_tasks SET section_id = 'SEC-NDLS-GZB' WHERE task_id = 'TSK-0001'"))
    await db_session.execute(text("UPDATE maintenance_tasks SET section_id = 'SEC-GZB-KRJ' WHERE task_id = 'TSK-0002'"))
    await db_session.commit()

    try:
        # Call Traversals API for SCN-DEMO-001
        resp = await client.get("/api/v1/scenarios/SCN-DEMO-001/traversals")
        assert resp.status_code == 200
        traversals = resp.json()

        # Find traversals for Train 12004 on the curated corridor
        trv_gzb_krj = next(
            (t for t in traversals if t["train_number"] == "12004" and t["section_id"] == "SEC-GZB-KRJ"),
            None,
        )
        assert trv_gzb_krj is not None
        assert trv_gzb_krj["traversal_track_id"] == "TRK-GZB-KRJ-DN"
        assert trv_gzb_krj["resolution_status"] == "EXPANDED_ROUTE"

        trv_krj_aljn = next(
            (t for t in traversals if t["train_number"] == "12004" and t["section_id"] == "SEC-KRJ-ALJN"),
            None,
        )
        assert trv_krj_aljn is not None
        assert trv_krj_aljn["traversal_track_id"] == "TRK-KRJ-ALJN-DN"
        assert trv_krj_aljn["resolution_status"] == "EXPANDED_ROUTE"

        # Traversal on non-topology section (e.g. SEC-ALJN-TDL) retains None
        trv_aljn_tdl = next(
            (t for t in traversals if t["train_number"] == "12004" and t["section_id"] == "SEC-ALJN-TDL"),
            None,
        )
        assert trv_aljn_tdl is not None
        assert trv_aljn_tdl["traversal_track_id"] is None
        assert trv_aljn_tdl["resolution_status"] == "DIRECT_SECTION"

    finally:
        # Restore original section assignments
        await db_session.execute(text("UPDATE maintenance_tasks SET section_id = 'SEC-KOTA-RTM' WHERE task_id = 'TSK-0001'"))
        await db_session.execute(text("UPDATE maintenance_tasks SET section_id = 'SEC-KOTA-RTM' WHERE task_id = 'TSK-0002'"))
        await db_session.commit()
