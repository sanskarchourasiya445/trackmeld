"""Integration tests for Phase 16I-C Infrastructure Topology APIs.

Verifies:
1. GET /api/v1/topology/endpoints lists seeded track endpoints with pagination
2. GET /api/v1/topology/endpoints?track_id=... filters endpoints (returns exactly START and END)
3. GET /api/v1/topology/endpoints/{endpoint_id} retrieves specific endpoint
4. GET /api/v1/topology/endpoints/{endpoint_id} returns 404 for unknown endpoint
5. GET /api/v1/topology/nodes returns empty list truthfully when no nodes exist
6. GET /api/v1/topology/connections returns empty list truthfully (zero inferred connections)
7. GET /api/v1/topology/tracks/{track_id} returns track topology context with endpoints
8. Curated DEMO_ONLY topology fixture can be created, retrieved, and verified
"""

import pytest
from httpx import AsyncClient
from backend.app.db.session import AsyncSessionLocal
from backend.app.db.models.topology import (
    TopologyNodeModel,
    TopologyConnectionModel,
)


@pytest.mark.asyncio
async def test_track_endpoints_list_api(client: AsyncClient):
    response = await client.get("/api/v1/topology/endpoints")
    assert response.status_code == 200
    endpoints = response.json()
    assert isinstance(endpoints, list)
    assert len(endpoints) >= 50
    assert "x-total-count" in response.headers
    total_count = int(response.headers["x-total-count"])
    assert total_count >= 100

    first = endpoints[0]
    assert "endpoint_id" in first
    assert "track_id" in first
    assert "endpoint_type" in first
    assert first["endpoint_type"] in ["START", "END"]
    assert "kilometrage" in first


@pytest.mark.asyncio
async def test_track_endpoints_filter_by_track(client: AsyncClient):
    # Fetch first endpoint to get a valid track_id
    response = await client.get("/api/v1/topology/endpoints?limit=1")
    assert response.status_code == 200
    target_track = response.json()[0]["track_id"]

    filtered_resp = await client.get(f"/api/v1/topology/endpoints?track_id={target_track}")
    assert filtered_resp.status_code == 200
    eps = filtered_resp.json()
    # Invariant: Each track must have exactly one START and one END endpoint
    assert len(eps) == 2
    types = {ep["endpoint_type"] for ep in eps}
    assert types == {"START", "END"}


@pytest.mark.asyncio
async def test_track_endpoint_get_by_id(client: AsyncClient):
    response = await client.get("/api/v1/topology/endpoints?limit=1")
    assert response.status_code == 200
    target_id = response.json()[0]["endpoint_id"]

    single_resp = await client.get(f"/api/v1/topology/endpoints/{target_id}")
    assert single_resp.status_code == 200
    data = single_resp.json()
    assert data["endpoint_id"] == target_id
    assert data["endpoint_type"] in ["START", "END"]


@pytest.mark.asyncio
async def test_track_endpoint_404(client: AsyncClient):
    response = await client.get("/api/v1/topology/endpoints/EP-DOES-NOT-EXIST")
    assert response.status_code == 404
    err = response.json()
    assert err["error"]["code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_topology_nodes_truthfully_empty(client: AsyncClient):
    """Confirm only explicit curated DEMO_ONLY nodes exist, with zero fabricated nodes for other stations."""
    response = await client.get("/api/v1/topology/nodes")
    assert response.status_code == 200
    nodes = response.json()
    assert isinstance(nodes, list)
    # Only the 2 curated DEMO_ONLY nodes exist
    assert len(nodes) == 2
    node_ids = {n["node_id"] for n in nodes}
    assert node_ids == {"NODE-GZB-THROAT", "NODE-KRJ-THROAT"}
    for n in nodes:
        assert n["classification"] == "DEMO_ONLY"


@pytest.mark.asyncio
async def test_topology_connections_truthfully_empty(client: AsyncClient):
    """CRITICAL SAFETY TEST: Confirm only explicit curated DEMO_ONLY connections exist, with zero inferred connections."""
    response = await client.get("/api/v1/topology/connections")
    assert response.status_code == 200
    conns = response.json()
    assert isinstance(conns, list)
    # Only the 5 curated DEMO_ONLY connections exist
    assert len(conns) == 5
    conn_ids = {c["connection_id"] for c in conns}
    assert conn_ids == {
        "CONN-GZB-DN-THROUGH",
        "CONN-GZB-UP-THROUGH",
        "CONN-GZB-CROSSOVER-DN-UP",
        "CONN-KRJ-DN-THROUGH",
        "CONN-KRJ-UP-THROUGH",
    }
    for c in conns:
        assert c["classification"] == "DEMO_ONLY"


@pytest.mark.asyncio
async def test_track_topology_aggregation(client: AsyncClient):
    # Fetch first track
    t_resp = await client.get("/api/v1/tracks?limit=1")
    assert t_resp.status_code == 200
    track_id = t_resp.json()[0]["track_id"]

    topo_resp = await client.get(f"/api/v1/topology/tracks/{track_id}")
    assert topo_resp.status_code == 200
    topo = topo_resp.json()
    assert topo["track_id"] == track_id
    assert len(topo["endpoints"]) == 2
    assert isinstance(topo["outgoing_connections"], list)
    assert isinstance(topo["incoming_connections"], list)


@pytest.mark.asyncio
async def test_track_topology_404(client: AsyncClient):
    response = await client.get("/api/v1/topology/tracks/TRK-DOES-NOT-EXIST")
    assert response.status_code == 404
    err = response.json()
    assert err["error"]["code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_curated_demo_topology_fixture(client: AsyncClient):
    """Test explicit DEMO_ONLY curated topology lifecycle without polluting permanent data."""
    # 1. Fetch two endpoints to connect
    ep_resp = await client.get("/api/v1/topology/endpoints?limit=2")
    assert ep_resp.status_code == 200
    eps = ep_resp.json()
    ep1_id = eps[0]["endpoint_id"]
    ep2_id = eps[1]["endpoint_id"]
    track1_id = eps[0]["track_id"]

    demo_node_id = "NODE-DEMO-TEST-THROAT"
    demo_conn_id = "CONN-DEMO-TEST-01"

    # 2. Insert curated DEMO_ONLY fixture
    async with AsyncSessionLocal() as session:
        node = TopologyNodeModel(
            node_id=demo_node_id,
            node_name="Curated Demo Junction Node",
            station_id=None,
            node_type="STATION_THROAT",
            classification="DEMO_ONLY",
            source_id="SRC-TAG-2023-TBL-01",
        )
        session.add(node)
        await session.flush()

        conn = TopologyConnectionModel(
            connection_id=demo_conn_id,
            node_id=demo_node_id,
            from_endpoint_id=ep1_id,
            to_endpoint_id=ep2_id,
            connection_type="CONTINUITY",
            traversal_direction="FORWARD",
            classification="DEMO_ONLY",
        )
        session.add(conn)
        await session.commit()

    try:
        # 3. Verify node via API
        n_resp = await client.get(f"/api/v1/topology/nodes/{demo_node_id}")
        assert n_resp.status_code == 200
        n_data = n_resp.json()
        assert n_data["node_id"] == demo_node_id
        assert n_data["classification"] == "DEMO_ONLY"

        # 4. Verify connection via API
        c_resp = await client.get(f"/api/v1/topology/connections/{demo_conn_id}")
        assert c_resp.status_code == 200
        c_data = c_resp.json()
        assert c_data["connection_id"] == demo_conn_id
        assert c_data["classification"] == "DEMO_ONLY"

        # 5. Verify track topology includes outgoing connection
        tt_resp = await client.get(f"/api/v1/topology/tracks/{track1_id}")
        assert tt_resp.status_code == 200
        tt_data = tt_resp.json()
        out_ids = [c["connection_id"] for c in tt_data["outgoing_connections"]]
        assert demo_conn_id in out_ids

    finally:
        # Clean up fixture
        async with AsyncSessionLocal() as session:
            c = await session.get(TopologyConnectionModel, demo_conn_id)
            if c:
                await session.delete(c)
            n = await session.get(TopologyNodeModel, demo_node_id)
            if n:
                await session.delete(n)
            await session.commit()
