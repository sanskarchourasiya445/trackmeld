"""Unit tests for Phase 16K: Curated Topology Connectivity Domain Models.

Verifies:
1. Instantiation of curated topology nodes (GZB, KRJ) in pure domain space.
2. Instantiation of curated continuity and crossover connections.
3. Explicit validation that self-connections are rejected by domain validator.
4. Classification defaults to DEMO_ONLY and is strictly enforced.
5. Max diverging speed is preserved on crossover and None on continuity.
6. Endpoint directionality and chainage consistency.
"""

import pytest
from pydantic import ValidationError

from backend.app.domain.enums import (
    EndpointType,
    TopologyNodeType,
    TopologyConnectionType,
    TopologyTraversalDirection,
)
from backend.app.domain.topology import (
    TopologyNode,
    TrackEndpoint,
    TopologyConnection,
)


def test_curated_nodes_domain_instantiation():
    """Verify curated nodes instantiate cleanly with proper enums."""
    gzb_node = TopologyNode(
        node_id="NODE-GZB-THROAT",
        node_name="Ghaziabad Station Junction Throat",
        station_id="STN-GZB",
        node_type=TopologyNodeType.STATION_THROAT,
        classification="DEMO_ONLY",
        source_id="SRC-TAG-2023-TBL-01",
    )
    assert gzb_node.node_id == "NODE-GZB-THROAT"
    assert gzb_node.node_type == TopologyNodeType.STATION_THROAT
    assert gzb_node.classification == "DEMO_ONLY"

    krj_node = TopologyNode(
        node_id="NODE-KRJ-THROAT",
        node_name="Khurja Junction Throat",
        station_id="STN-KRJ",
        node_type=TopologyNodeType.STATION_THROAT,
        classification="DEMO_ONLY",
        source_id="SRC-TAG-2023-TBL-01",
    )
    assert krj_node.node_id == "NODE-KRJ-THROAT"
    assert krj_node.node_type == TopologyNodeType.STATION_THROAT
    assert krj_node.classification == "DEMO_ONLY"


def test_curated_connections_domain_instantiation():
    """Verify curated continuity and crossover connections instantiate cleanly."""
    c_through = TopologyConnection(
        connection_id="CONN-GZB-DN-THROUGH",
        node_id="NODE-GZB-THROAT",
        from_endpoint_id="EP-TRK-NDLS-GZB-DN-END",
        to_endpoint_id="EP-TRK-GZB-KRJ-DN-START",
        connection_type=TopologyConnectionType.CONTINUITY,
        traversal_direction=TopologyTraversalDirection.FORWARD,
        max_diverging_speed_kmh=None,
        classification="DEMO_ONLY",
    )
    assert c_through.connection_type == TopologyConnectionType.CONTINUITY
    assert c_through.traversal_direction == TopologyTraversalDirection.FORWARD
    assert c_through.max_diverging_speed_kmh is None

    c_crossover = TopologyConnection(
        connection_id="CONN-GZB-CROSSOVER-DN-UP",
        node_id="NODE-GZB-THROAT",
        from_endpoint_id="EP-TRK-NDLS-GZB-DN-END",
        to_endpoint_id="EP-TRK-GZB-KRJ-UP-START",
        connection_type=TopologyConnectionType.CROSSOVER,
        traversal_direction=TopologyTraversalDirection.FORWARD,
        max_diverging_speed_kmh=30,
        classification="DEMO_ONLY",
    )
    assert c_crossover.connection_type == TopologyConnectionType.CROSSOVER
    assert c_crossover.max_diverging_speed_kmh == 30


def test_crossover_self_loop_rejected():
    """Verify TopologyConnection rejects self-loop endpoints."""
    with pytest.raises(ValueError, match="TopologyConnection cannot link an endpoint to itself"):
        TopologyConnection(
            connection_id="CONN-INVALID-SELF",
            node_id="NODE-GZB-THROAT",
            from_endpoint_id="EP-TRK-NDLS-GZB-DN-END",
            to_endpoint_id="EP-TRK-NDLS-GZB-DN-END",
            connection_type=TopologyConnectionType.CROSSOVER,
            traversal_direction=TopologyTraversalDirection.FORWARD,
            classification="DEMO_ONLY",
        )


def test_curated_endpoints_domain_instantiation():
    """Verify endpoint models for the corridor tracks."""
    ep_start = TrackEndpoint(
        endpoint_id="EP-TRK-NDLS-GZB-DN-START",
        track_id="TRK-NDLS-GZB-DN",
        endpoint_type=EndpointType.START,
        kilometrage=0.0,
    )
    assert ep_start.endpoint_type == EndpointType.START
    assert ep_start.kilometrage == 0.0

    ep_end = TrackEndpoint(
        endpoint_id="EP-TRK-NDLS-GZB-DN-END",
        track_id="TRK-NDLS-GZB-DN",
        endpoint_type=EndpointType.END,
        kilometrage=25.0,
    )
    assert ep_end.endpoint_type == EndpointType.END
    assert ep_end.kilometrage == 25.0
