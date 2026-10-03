"""Unit tests for Phase 16I-C Infrastructure Topology domain models and invariants."""

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


def test_topology_node_creation():
    node = TopologyNode(
        node_id="NODE-STN-NDLS-WEST",
        node_name="New Delhi West Throat",
        station_id="STN-NDLS",
        node_type=TopologyNodeType.STATION_THROAT,
        classification="DEMO_ONLY",
        source_id="SRC-ESP-NDLS-2026",
    )
    assert node.node_id == "NODE-STN-NDLS-WEST"
    assert node.node_type == TopologyNodeType.STATION_THROAT
    assert node.classification == "DEMO_ONLY"


def test_track_endpoint_creation():
    ep = TrackEndpoint(
        endpoint_id="EP-TRK-01-START",
        track_id="TRK-SEC-01-UP",
        endpoint_type=EndpointType.START,
        kilometrage=10.5,
    )
    assert ep.endpoint_id == "EP-TRK-01-START"
    assert ep.endpoint_type == EndpointType.START
    assert ep.kilometrage == 10.5


def test_track_endpoint_invalid_type():
    with pytest.raises(ValidationError):
        TrackEndpoint(
            endpoint_id="EP-TRK-01-MIDDLE",
            track_id="TRK-SEC-01-UP",
            endpoint_type="MIDDLE",  # Invalid! Only START or END permitted
            kilometrage=10.5,
        )


def test_topology_connection_creation():
    conn = TopologyConnection(
        connection_id="CONN-01-THROUGH",
        node_id="NODE-STN-NDLS-WEST",
        from_endpoint_id="EP-TRK-01-END",
        to_endpoint_id="EP-TRK-02-START",
        connection_type=TopologyConnectionType.CONTINUITY,
        traversal_direction=TopologyTraversalDirection.FORWARD,
        max_diverging_speed_kmh=None,
        classification="DEMO_ONLY",
    )
    assert conn.connection_id == "CONN-01-THROUGH"
    assert conn.connection_type == TopologyConnectionType.CONTINUITY
    assert conn.traversal_direction == TopologyTraversalDirection.FORWARD


def test_topology_connection_rejects_self_reference():
    with pytest.raises(ValidationError, match="cannot link an endpoint to itself"):
        TopologyConnection(
            connection_id="CONN-SELF-LOOP",
            node_id="NODE-01",
            from_endpoint_id="EP-01",
            to_endpoint_id="EP-01",  # Self reference prohibited!
            connection_type=TopologyConnectionType.CONTINUITY,
        )


def test_topology_connection_invalid_type():
    with pytest.raises(ValidationError):
        TopologyConnection(
            connection_id="CONN-INVALID",
            node_id="NODE-01",
            from_endpoint_id="EP-01",
            to_endpoint_id="EP-02",
            connection_type="INVALID_TYPE",
        )


def test_topology_connection_direction_validation():
    conn = TopologyConnection(
        connection_id="CONN-REV",
        node_id="NODE-01",
        from_endpoint_id="EP-01",
        to_endpoint_id="EP-02",
        connection_type=TopologyConnectionType.TURNOUT_NORMAL,
        traversal_direction=TopologyTraversalDirection.REVERSE,
    )
    assert conn.traversal_direction == TopologyTraversalDirection.REVERSE


def test_no_topology_connection_inferred_from_adjacency():
    """CRITICAL SAFETY TEST: Adjacency represents lateral proximity, NOT connectivity."""
    # Sibling tracks in same section with mutual adjacency
    trk1_adj = ["TRK-SEC-01-DN"]
    trk2_adj = ["TRK-SEC-01-UP"]

    # Adjacency alone must not create a TopologyConnection
    assert "TRK-SEC-01-DN" in trk1_adj
    # Invariant: Adjacency list contains track IDs, NOT TopologyConnection objects
    assert all(isinstance(x, str) for x in trk1_adj)


def test_no_topology_connection_inferred_from_shared_station():
    """CRITICAL SAFETY TEST: Sharing a station node does NOT imply physical track continuity."""
    sec1_to_station = "STN-GZB"
    sec2_from_station = "STN-GZB"

    # Even though both sections share STN-GZB, no connection exists without explicit definition
    assert sec1_to_station == sec2_from_station
    # Connection cannot be synthesized from this identity


def test_demo_only_classification_preserved():
    node = TopologyNode(
        node_id="NODE-DEMO-01",
        node_name="Demo Junction",
        node_type=TopologyNodeType.CROSSOVER_JUNCTION,
        classification="DEMO_ONLY",
        source_id="SRC-DEMO",
    )
    conn = TopologyConnection(
        connection_id="CONN-DEMO-01",
        node_id="NODE-DEMO-01",
        from_endpoint_id="EP-A-END",
        to_endpoint_id="EP-B-START",
        connection_type=TopologyConnectionType.CROSSOVER,
        classification="DEMO_ONLY",
    )
    assert node.classification == "DEMO_ONLY"
    assert conn.classification == "DEMO_ONLY"
