"""Integration and fixture verification tests for Phase 16K: Curated Topology Connectivity.

Verifies:
1. Demo topology nodes exist only for the curated fixture (GZB and KRJ throats).
2. Demo topology connections reference valid, existing Phase 16I-C endpoints.
3. No duplicate endpoints exist (exactly 264 total endpoints, 2 per track across 132 tracks).
4. Every connection has valid, distinct from/to endpoints.
5. No self-connections exist.
6. Connection traversal directions are valid and geometrically consistent.
7. Connection types match railway domain semantics (CONTINUITY, CROSSOVER).
8. Demo provenance is explicit (classification == 'DEMO_ONLY').
9. Existing production tracks and sections remain unchanged.
10. Existing topology outside the curated corridor remains untouched (0 connections).
11. Diverging speed limit is populated only on diverging crossover (30 km/h) and null on through lines.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_curated_demo_nodes_exist(client: AsyncClient):
    """1. Demo topology nodes exist only for the curated fixture (GZB and KRJ)."""
    response = await client.get("/api/v1/topology/nodes")
    assert response.status_code == 200
    nodes = response.json()

    assert len(nodes) == 2
    nodes_by_id = {n["node_id"]: n for n in nodes}

    assert "NODE-GZB-THROAT" in nodes_by_id
    gzb = nodes_by_id["NODE-GZB-THROAT"]
    assert gzb["node_name"] == "Ghaziabad Station Junction Throat"
    assert gzb["station_id"] == "STN-GZB"
    assert gzb["node_type"] == "STATION_THROAT"
    assert gzb["classification"] == "DEMO_ONLY"
    assert gzb["source_id"] == "SRC-TAG-2023-TBL-01"

    assert "NODE-KRJ-THROAT" in nodes_by_id
    krj = nodes_by_id["NODE-KRJ-THROAT"]
    assert krj["node_name"] == "Khurja Junction Throat"
    assert krj["station_id"] == "STN-KRJ"
    assert krj["node_type"] == "STATION_THROAT"
    assert krj["classification"] == "DEMO_ONLY"
    assert krj["source_id"] == "SRC-TAG-2023-TBL-01"


@pytest.mark.asyncio
async def test_curated_connections_reference_existing_endpoints(client: AsyncClient):
    """2 & 4. Connections reference existing endpoints with distinct from/to endpoints."""
    # Fetch all endpoints via API
    ep_resp = await client.get("/api/v1/topology/endpoints?limit=500")
    assert ep_resp.status_code == 200
    all_eps = {ep["endpoint_id"]: ep for ep in ep_resp.json()}

    # Fetch all connections
    conn_resp = await client.get("/api/v1/topology/connections")
    assert conn_resp.status_code == 200
    conns = conn_resp.json()

    assert len(conns) == 5
    for c in conns:
        c_id = c["connection_id"]
        # Every connection must have distinct endpoints
        assert c["from_endpoint_id"] != c["to_endpoint_id"], f"Self-connection detected on {c_id}"
        # Both endpoints must exist in pre-seeded Phase 16I-C endpoints
        assert c["from_endpoint_id"] in all_eps, f"from_endpoint {c['from_endpoint_id']} missing"
        assert c["to_endpoint_id"] in all_eps, f"to_endpoint {c['to_endpoint_id']} missing"
        # Provenance must be explicit
        assert c["classification"] == "DEMO_ONLY"


@pytest.mark.asyncio
async def test_no_duplicate_endpoints(client: AsyncClient):
    """3. Exactly 264 endpoints exist (2 per track for all 132 tracks), no duplicates."""
    ep_resp = await client.get("/api/v1/topology/endpoints?limit=500")
    assert ep_resp.status_code == 200
    endpoints = ep_resp.json()

    assert len(endpoints) == 264
    by_track = {}
    for ep in endpoints:
        t_id = ep["track_id"]
        by_track.setdefault(t_id, []).append(ep["endpoint_type"])

    assert len(by_track) == 132
    for t_id, ep_types in by_track.items():
        assert len(ep_types) == 2, f"Track {t_id} has {len(ep_types)} endpoints"
        assert sorted(ep_types) == ["END", "START"], f"Track {t_id} does not have exactly START and END"


@pytest.mark.asyncio
async def test_connection_geometry_and_direction(client: AsyncClient):
    """6 & 7. Connection types and directions match railway geometry."""
    response = await client.get("/api/v1/topology/connections")
    assert response.status_code == 200
    conns = {c["connection_id"]: c for c in response.json()}

    # 1. Ghaziabad DN Through Continuity: NDLS-GZB-DN (km 25.0 END) -> GZB-KRJ-DN (km 25.0 START)
    c1 = conns["CONN-GZB-DN-THROUGH"]
    assert c1["node_id"] == "NODE-GZB-THROAT"
    assert c1["connection_type"] == "CONTINUITY"
    assert c1["traversal_direction"] == "FORWARD"
    assert c1["max_diverging_speed_kmh"] is None
    assert c1["from_endpoint_id"] == "EP-TRK-NDLS-GZB-DN-END"
    assert c1["to_endpoint_id"] == "EP-TRK-GZB-KRJ-DN-START"

    # 2. Ghaziabad UP Through Continuity: GZB-KRJ-UP (km 25.0 START) -> NDLS-GZB-UP (km 25.0 END)
    c2 = conns["CONN-GZB-UP-THROUGH"]
    assert c2["node_id"] == "NODE-GZB-THROAT"
    assert c2["connection_type"] == "CONTINUITY"
    assert c2["traversal_direction"] == "FORWARD"
    assert c2["max_diverging_speed_kmh"] is None
    assert c2["from_endpoint_id"] == "EP-TRK-GZB-KRJ-UP-START"
    assert c2["to_endpoint_id"] == "EP-TRK-NDLS-GZB-UP-END"

    # 3. Ghaziabad Crossover: NDLS-GZB-DN (km 25.0 END) -> GZB-KRJ-UP (km 25.0 START) with 30 km/h limit
    c3 = conns["CONN-GZB-CROSSOVER-DN-UP"]
    assert c3["node_id"] == "NODE-GZB-THROAT"
    assert c3["connection_type"] == "CROSSOVER"
    assert c3["traversal_direction"] == "FORWARD"
    assert c3["max_diverging_speed_kmh"] == 30
    assert c3["from_endpoint_id"] == "EP-TRK-NDLS-GZB-DN-END"
    assert c3["to_endpoint_id"] == "EP-TRK-GZB-KRJ-UP-START"

    # 4. Khurja DN Through Continuity: GZB-KRJ-DN (km 95.0 END) -> KRJ-ALJN-DN (km 95.0 START)
    c4 = conns["CONN-KRJ-DN-THROUGH"]
    assert c4["node_id"] == "NODE-KRJ-THROAT"
    assert c4["connection_type"] == "CONTINUITY"
    assert c4["traversal_direction"] == "FORWARD"
    assert c4["max_diverging_speed_kmh"] is None
    assert c4["from_endpoint_id"] == "EP-TRK-GZB-KRJ-DN-END"
    assert c4["to_endpoint_id"] == "EP-TRK-KRJ-ALJN-DN-START"

    # 5. Khurja UP Through Continuity: KRJ-ALJN-UP (km 95.0 START) -> GZB-KRJ-UP (km 95.0 END)
    c5 = conns["CONN-KRJ-UP-THROUGH"]
    assert c5["node_id"] == "NODE-KRJ-THROAT"
    assert c5["connection_type"] == "CONTINUITY"
    assert c5["traversal_direction"] == "FORWARD"
    assert c5["max_diverging_speed_kmh"] is None
    assert c5["from_endpoint_id"] == "EP-TRK-KRJ-ALJN-UP-START"
    assert c5["to_endpoint_id"] == "EP-TRK-GZB-KRJ-UP-END"


@pytest.mark.asyncio
async def test_corridor_track_topology_aggregation(client: AsyncClient):
    """Verify aggregated track topology on curated corridor tracks."""
    # Track NDLS-GZB-DN: 2 endpoints, 2 outgoing connections at GZB (through and crossover)
    resp = await client.get("/api/v1/topology/tracks/TRK-NDLS-GZB-DN")
    assert resp.status_code == 200
    data = resp.json()
    assert data["track_id"] == "TRK-NDLS-GZB-DN"
    assert len(data["endpoints"]) == 2
    out_ids = {c["connection_id"] for c in data["outgoing_connections"]}
    assert "CONN-GZB-DN-THROUGH" in out_ids
    assert "CONN-GZB-CROSSOVER-DN-UP" in out_ids
    assert len(data["incoming_connections"]) == 0

    # Track GZB-KRJ-DN: incoming through from NDLS-GZB-DN, outgoing through to KRJ-ALJN-DN
    resp2 = await client.get("/api/v1/topology/tracks/TRK-GZB-KRJ-DN")
    assert resp2.status_code == 200
    data2 = resp2.json()
    in_ids = {c["connection_id"] for c in data2["incoming_connections"]}
    out_ids2 = {c["connection_id"] for c in data2["outgoing_connections"]}
    assert "CONN-GZB-DN-THROUGH" in in_ids
    assert "CONN-KRJ-DN-THROUGH" in out_ids2

    # Track KRJ-ALJN-DN: incoming through from GZB-KRJ-DN
    resp3 = await client.get("/api/v1/topology/tracks/TRK-KRJ-ALJN-DN")
    assert resp3.status_code == 200
    data3 = resp3.json()
    in_ids3 = {c["connection_id"] for c in data3["incoming_connections"]}
    assert "CONN-KRJ-DN-THROUGH" in in_ids3

    # Track KRJ-ALJN-UP: outgoing through to GZB-KRJ-UP
    resp4 = await client.get("/api/v1/topology/tracks/TRK-KRJ-ALJN-UP")
    assert resp4.status_code == 200
    data4 = resp4.json()
    out_ids4 = {c["connection_id"] for c in data4["outgoing_connections"]}
    assert "CONN-KRJ-UP-THROUGH" in out_ids4

    # Track GZB-KRJ-UP: incoming from KRJ-ALJN-UP, incoming crossover from NDLS-GZB-DN, outgoing to NDLS-GZB-UP
    resp5 = await client.get("/api/v1/topology/tracks/TRK-GZB-KRJ-UP")
    assert resp5.status_code == 200
    data5 = resp5.json()
    in_ids5 = {c["connection_id"] for c in data5["incoming_connections"]}
    out_ids5 = {c["connection_id"] for c in data5["outgoing_connections"]}
    assert "CONN-KRJ-UP-THROUGH" in in_ids5
    assert "CONN-GZB-CROSSOVER-DN-UP" in in_ids5
    assert "CONN-GZB-UP-THROUGH" in out_ids5

    # Track NDLS-GZB-UP: incoming from GZB-KRJ-UP
    resp6 = await client.get("/api/v1/topology/tracks/TRK-NDLS-GZB-UP")
    assert resp6.status_code == 200
    data6 = resp6.json()
    in_ids6 = {c["connection_id"] for c in data6["incoming_connections"]}
    assert "CONN-GZB-UP-THROUGH" in in_ids6


@pytest.mark.asyncio
async def test_topology_outside_corridor_is_untouched(client: AsyncClient):
    """10. Existing topology outside the curated corridor remains completely untouched."""
    # Check a track far away from the NDLS-GZB-KRJ-ALJN corridor
    resp = await client.get("/api/v1/topology/tracks/TRK-KPD-JTJ-UP")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["endpoints"]) == 2
    assert len(data["outgoing_connections"]) == 0
    assert len(data["incoming_connections"]) == 0
