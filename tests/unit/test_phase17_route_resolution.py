"""Unit tests for Phase 17: Deterministic Route Resolution.

Verifies:
1. Direct Single-Section Traversal: adjacent stations resolve to DIRECT_SECTION with matching traversal_track_id.
2. Multi-Section Express Traversal: express pass expands into ordered traversals with sequential track IDs.
3. Bidirectional support: tests both DOWN and UP nominal travel directions.
4. Crossover & Direction Conflict: diverging crossover is rejected when conflicting with track direction.
5. Multi-Route Ambiguity: if multiple valid physical paths exist without priority, returns AMBIGUOUS_ROUTE with traversal_track_id = None.
6. Disconnected Topology: missing connection on topology corridor yields UNRESOLVED with explicit reason.
7. Determinism & Permutation Invariance: shuffling connections/tracks yields identical output.
8. Backward Compatibility Fallback: corridors without topology fall back to section expansion (traversal_track_id = None).
9. PlanningSnapshot hash stability: snapshot_hash is unaffected by topology routing.
10. Architectural boundary invariant: whole-section solver and validator invariants remain untouched.
"""

from datetime import datetime, timedelta, timezone
import random
import pytest

from backend.app.domain.enums import (
    DataClass,
    EndpointType,
    TopologyNodeType,
    TopologyConnectionType,
    TopologyTraversalDirection,
    TraversalResolutionStatus,
)
from backend.app.domain.temporal import TimeInterval, PlanningHorizon, TrainPass, TrainTraversal
from backend.app.domain.topology import TopologyNode, TrackEndpoint, TopologyConnection
from backend.app.services.topology_routing import (
    DeterministicTopologyRouter,
    RouteResolutionResult,
    ResolvedHop,
)
from backend.app.services.compatibility_service import CompatibilityEngine
from backend.app.domain.planning_snapshot import PlanningSnapshot


@pytest.fixture
def curated_corridor_fixture():
    """Curated 3-section corridor fixture identical to Phase 16K:
    STN-NDLS (km 0.0) -> [SEC-NDLS-GZB, 25km] -> STN-GZB (km 25.0)
    STN-GZB (km 25.0) -> [SEC-GZB-KRJ, 70km] -> STN-KRJ (km 95.0)
    STN-KRJ (km 95.0) -> [SEC-KRJ-ALJN, 31km] -> STN-ALJN (km 126.0)
    """
    sections = [
        {
            "section_id": "SEC-NDLS-GZB",
            "section_code": "NDLS-GZB",
            "from_station_id": "STN-NDLS",
            "to_station_id": "STN-GZB",
            "kilometrage_start": 0.0,
            "kilometrage_end": 25.0,
            "length_km": 25.0,
            "track_count": 2,
            "electrified": True,
        },
        {
            "section_id": "SEC-GZB-KRJ",
            "section_code": "GZB-KRJ",
            "from_station_id": "STN-GZB",
            "to_station_id": "STN-KRJ",
            "kilometrage_start": 25.0,
            "kilometrage_end": 95.0,
            "length_km": 70.0,
            "track_count": 2,
            "electrified": True,
        },
        {
            "section_id": "SEC-KRJ-ALJN",
            "section_code": "KRJ-ALJN",
            "from_station_id": "STN-KRJ",
            "to_station_id": "STN-ALJN",
            "kilometrage_start": 95.0,
            "kilometrage_end": 126.0,
            "length_km": 31.0,
            "track_count": 2,
            "electrified": True,
        },
    ]

    tracks = [
        # SEC-NDLS-GZB
        {"track_id": "TRK-NDLS-GZB-DN", "section_id": "SEC-NDLS-GZB", "track_code": "DN_MAIN", "direction": "DOWN", "electrified": True, "max_speed_kmh": 130},
        {"track_id": "TRK-NDLS-GZB-UP", "section_id": "SEC-NDLS-GZB", "track_code": "UP_MAIN", "direction": "UP", "electrified": True, "max_speed_kmh": 130},
        # SEC-GZB-KRJ
        {"track_id": "TRK-GZB-KRJ-DN", "section_id": "SEC-GZB-KRJ", "track_code": "DN_MAIN", "direction": "DOWN", "electrified": True, "max_speed_kmh": 130},
        {"track_id": "TRK-GZB-KRJ-UP", "section_id": "SEC-GZB-KRJ", "track_code": "UP_MAIN", "direction": "UP", "electrified": True, "max_speed_kmh": 130},
        # SEC-KRJ-ALJN
        {"track_id": "TRK-KRJ-ALJN-DN", "section_id": "SEC-KRJ-ALJN", "track_code": "DN_MAIN", "direction": "DOWN", "electrified": True, "max_speed_kmh": 130},
        {"track_id": "TRK-KRJ-ALJN-UP", "section_id": "SEC-KRJ-ALJN", "track_code": "UP_MAIN", "direction": "UP", "electrified": True, "max_speed_kmh": 130},
    ]

    endpoints = [
        # TRK-NDLS-GZB-DN
        {"endpoint_id": "EP-TRK-NDLS-GZB-DN-START", "track_id": "TRK-NDLS-GZB-DN", "endpoint_type": "START", "kilometrage": 0.0},
        {"endpoint_id": "EP-TRK-NDLS-GZB-DN-END", "track_id": "TRK-NDLS-GZB-DN", "endpoint_type": "END", "kilometrage": 25.0},
        # TRK-NDLS-GZB-UP
        {"endpoint_id": "EP-TRK-NDLS-GZB-UP-START", "track_id": "TRK-NDLS-GZB-UP", "endpoint_type": "START", "kilometrage": 0.0},
        {"endpoint_id": "EP-TRK-NDLS-GZB-UP-END", "track_id": "TRK-NDLS-GZB-UP", "endpoint_type": "END", "kilometrage": 25.0},
        # TRK-GZB-KRJ-DN
        {"endpoint_id": "EP-TRK-GZB-KRJ-DN-START", "track_id": "TRK-GZB-KRJ-DN", "endpoint_type": "START", "kilometrage": 25.0},
        {"endpoint_id": "EP-TRK-GZB-KRJ-DN-END", "track_id": "TRK-GZB-KRJ-DN", "endpoint_type": "END", "kilometrage": 95.0},
        # TRK-GZB-KRJ-UP
        {"endpoint_id": "EP-TRK-GZB-KRJ-UP-START", "track_id": "TRK-GZB-KRJ-UP", "endpoint_type": "START", "kilometrage": 25.0},
        {"endpoint_id": "EP-TRK-GZB-KRJ-UP-END", "track_id": "TRK-GZB-KRJ-UP", "endpoint_type": "END", "kilometrage": 95.0},
        # TRK-KRJ-ALJN-DN
        {"endpoint_id": "EP-TRK-KRJ-ALJN-DN-START", "track_id": "TRK-KRJ-ALJN-DN", "endpoint_type": "START", "kilometrage": 95.0},
        {"endpoint_id": "EP-TRK-KRJ-ALJN-DN-END", "track_id": "TRK-KRJ-ALJN-DN", "endpoint_type": "END", "kilometrage": 126.0},
        # TRK-KRJ-ALJN-UP
        {"endpoint_id": "EP-TRK-KRJ-ALJN-UP-START", "track_id": "TRK-KRJ-ALJN-UP", "endpoint_type": "START", "kilometrage": 95.0},
        {"endpoint_id": "EP-TRK-KRJ-ALJN-UP-END", "track_id": "TRK-KRJ-ALJN-UP", "endpoint_type": "END", "kilometrage": 126.0},
    ]

    nodes = [
        {"node_id": "NODE-GZB-THROAT", "node_name": "Ghaziabad Throat", "station_id": "STN-GZB", "node_type": "STATION_THROAT", "classification": "DEMO_ONLY"},
        {"node_id": "NODE-KRJ-THROAT", "node_name": "Khurja Throat", "station_id": "STN-KRJ", "node_type": "STATION_THROAT", "classification": "DEMO_ONLY"},
    ]

    connections = [
        # GZB DN Through: NDLS-GZB-DN (END) -> GZB-KRJ-DN (START)
        {
            "connection_id": "CONN-GZB-DN-THROUGH",
            "node_id": "NODE-GZB-THROAT",
            "from_endpoint_id": "EP-TRK-NDLS-GZB-DN-END",
            "to_endpoint_id": "EP-TRK-GZB-KRJ-DN-START",
            "connection_type": "CONTINUITY",
            "traversal_direction": "FORWARD",
            "max_diverging_speed_kmh": None,
        },
        # GZB UP Through: GZB-KRJ-UP (START) -> NDLS-GZB-UP (END)
        {
            "connection_id": "CONN-GZB-UP-THROUGH",
            "node_id": "NODE-GZB-THROAT",
            "from_endpoint_id": "EP-TRK-GZB-KRJ-UP-START",
            "to_endpoint_id": "EP-TRK-NDLS-GZB-UP-END",
            "connection_type": "CONTINUITY",
            "traversal_direction": "FORWARD",
            "max_diverging_speed_kmh": None,
        },
        # GZB Crossover: NDLS-GZB-DN (END) -> GZB-KRJ-UP (START)
        {
            "connection_id": "CONN-GZB-CROSSOVER-DN-UP",
            "node_id": "NODE-GZB-THROAT",
            "from_endpoint_id": "EP-TRK-NDLS-GZB-DN-END",
            "to_endpoint_id": "EP-TRK-GZB-KRJ-UP-START",
            "connection_type": "CROSSOVER",
            "traversal_direction": "FORWARD",
            "max_diverging_speed_kmh": 30,
        },
        # KRJ DN Through: GZB-KRJ-DN (END) -> KRJ-ALJN-DN (START)
        {
            "connection_id": "CONN-KRJ-DN-THROUGH",
            "node_id": "NODE-KRJ-THROAT",
            "from_endpoint_id": "EP-TRK-GZB-KRJ-DN-END",
            "to_endpoint_id": "EP-TRK-KRJ-ALJN-DN-START",
            "connection_type": "CONTINUITY",
            "traversal_direction": "FORWARD",
            "max_diverging_speed_kmh": None,
        },
        # KRJ UP Through: KRJ-ALJN-UP (START) -> GZB-KRJ-UP (END)
        {
            "connection_id": "CONN-KRJ-UP-THROUGH",
            "node_id": "NODE-KRJ-THROAT",
            "from_endpoint_id": "EP-TRK-KRJ-ALJN-UP-START",
            "to_endpoint_id": "EP-TRK-GZB-KRJ-UP-END",
            "connection_type": "CONTINUITY",
            "traversal_direction": "FORWARD",
            "max_diverging_speed_kmh": None,
        },
    ]

    return {
        "sections": sections,
        "tracks": tracks,
        "endpoints": endpoints,
        "nodes": nodes,
        "connections": connections,
    }


def test_direct_single_section_resolution_down(curated_corridor_fixture):
    """Adjacent-station pass in DOWN direction must resolve to DIRECT_SECTION on DN_MAIN."""
    f = curated_corridor_fixture
    router = DeterministicTopologyRouter(
        sections=f["sections"],
        tracks=f["tracks"],
        topology_nodes=f["nodes"],
        topology_connections=f["connections"],
        track_endpoints=f["endpoints"],
    )

    t0 = datetime(2026, 10, 10, 6, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 10, 10, 6, 30, tzinfo=timezone.utc)

    pass_obj = TrainPass(
        pass_id="PASS-12004-NDLS-GZB",
        train_id="TRN-12004",
        train_number="12004",
        section_id="SEC-NDLS-GZB",
        from_station_id="STN-NDLS",
        to_station_id="STN-GZB",
        interval=TimeInterval(start=t0, end=t1),
        movement_type="SECTION_TRAVERSAL",
    )

    result = router.resolve_pass_route(pass_obj)
    assert result.status == TraversalResolutionStatus.DIRECT_SECTION
    assert result.unresolved_reason is None
    assert len(result.hops) == 1
    hop = result.hops[0]
    assert hop.section_id == "SEC-NDLS-GZB"
    assert hop.track_id == "TRK-NDLS-GZB-DN"
    assert hop.from_station_id == "STN-NDLS"
    assert hop.to_station_id == "STN-GZB"


def test_direct_single_section_resolution_up(curated_corridor_fixture):
    """Adjacent-station pass in UP direction must resolve to DIRECT_SECTION on UP_MAIN."""
    f = curated_corridor_fixture
    router = DeterministicTopologyRouter(
        sections=f["sections"],
        tracks=f["tracks"],
        topology_nodes=f["nodes"],
        topology_connections=f["connections"],
        track_endpoints=f["endpoints"],
    )

    t0 = datetime(2026, 10, 10, 7, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 10, 10, 7, 30, tzinfo=timezone.utc)

    pass_obj = TrainPass(
        pass_id="PASS-12005-GZB-NDLS",
        train_id="TRN-12005",
        train_number="12005",
        section_id="SEC-NDLS-GZB",
        from_station_id="STN-GZB",
        to_station_id="STN-NDLS",
        interval=TimeInterval(start=t0, end=t1),
        movement_type="SECTION_TRAVERSAL",
    )

    result = router.resolve_pass_route(pass_obj)
    assert result.status == TraversalResolutionStatus.DIRECT_SECTION
    assert result.unresolved_reason is None
    assert len(result.hops) == 1
    hop = result.hops[0]
    assert hop.section_id == "SEC-NDLS-GZB"
    assert hop.track_id == "TRK-NDLS-GZB-UP"
    assert hop.from_station_id == "STN-GZB"
    assert hop.to_station_id == "STN-NDLS"


def test_multi_section_express_down_resolution(curated_corridor_fixture):
    """Express train NDLS -> ALJN traverses 3 sections, assigning DN tracks to all hops."""
    f = curated_corridor_fixture
    router = DeterministicTopologyRouter(
        sections=f["sections"],
        tracks=f["tracks"],
        topology_nodes=f["nodes"],
        topology_connections=f["connections"],
        track_endpoints=f["endpoints"],
    )

    t0 = datetime(2026, 10, 10, 6, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)

    pass_obj = TrainPass(
        pass_id="PASS-12301-NDLS-ALJN",
        train_id="TRN-12301",
        train_number="12301",
        section_id=None,
        from_station_id="STN-NDLS",
        to_station_id="STN-ALJN",
        interval=TimeInterval(start=t0, end=t1),
        movement_type="STATION_HOP",
    )

    result = router.resolve_pass_route(pass_obj)
    assert result.status == TraversalResolutionStatus.EXPANDED_ROUTE
    assert result.unresolved_reason is None
    assert len(result.hops) == 3

    assert result.hops[0].section_id == "SEC-NDLS-GZB"
    assert result.hops[0].track_id == "TRK-NDLS-GZB-DN"
    assert result.hops[0].from_station_id == "STN-NDLS"
    assert result.hops[0].to_station_id == "STN-GZB"

    assert result.hops[1].section_id == "SEC-GZB-KRJ"
    assert result.hops[1].track_id == "TRK-GZB-KRJ-DN"
    assert result.hops[1].from_station_id == "STN-GZB"
    assert result.hops[1].to_station_id == "STN-KRJ"
    assert result.hops[1].connection_id == "CONN-GZB-DN-THROUGH"

    assert result.hops[2].section_id == "SEC-KRJ-ALJN"
    assert result.hops[2].track_id == "TRK-KRJ-ALJN-DN"
    assert result.hops[2].from_station_id == "STN-KRJ"
    assert result.hops[2].to_station_id == "STN-ALJN"
    assert result.hops[2].connection_id == "CONN-KRJ-DN-THROUGH"


def test_multi_section_express_up_resolution(curated_corridor_fixture):
    """Express train ALJN -> NDLS traverses 3 sections in reverse, assigning UP tracks to all hops."""
    f = curated_corridor_fixture
    router = DeterministicTopologyRouter(
        sections=f["sections"],
        tracks=f["tracks"],
        topology_nodes=f["nodes"],
        topology_connections=f["connections"],
        track_endpoints=f["endpoints"],
    )

    t0 = datetime(2026, 10, 10, 14, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 10, 10, 16, 0, tzinfo=timezone.utc)

    pass_obj = TrainPass(
        pass_id="PASS-12302-ALJN-NDLS",
        train_id="TRN-12302",
        train_number="12302",
        section_id=None,
        from_station_id="STN-ALJN",
        to_station_id="STN-NDLS",
        interval=TimeInterval(start=t0, end=t1),
        movement_type="STATION_HOP",
    )

    result = router.resolve_pass_route(pass_obj)
    assert result.status == TraversalResolutionStatus.EXPANDED_ROUTE
    assert result.unresolved_reason is None
    assert len(result.hops) == 3

    assert result.hops[0].section_id == "SEC-KRJ-ALJN"
    assert result.hops[0].track_id == "TRK-KRJ-ALJN-UP"
    assert result.hops[0].from_station_id == "STN-ALJN"
    assert result.hops[0].to_station_id == "STN-KRJ"

    assert result.hops[1].section_id == "SEC-GZB-KRJ"
    assert result.hops[1].track_id == "TRK-GZB-KRJ-UP"
    assert result.hops[1].from_station_id == "STN-KRJ"
    assert result.hops[1].to_station_id == "STN-GZB"
    assert result.hops[1].connection_id == "CONN-KRJ-UP-THROUGH"

    assert result.hops[2].section_id == "SEC-NDLS-GZB"
    assert result.hops[2].track_id == "TRK-NDLS-GZB-UP"
    assert result.hops[2].from_station_id == "STN-GZB"
    assert result.hops[2].to_station_id == "STN-NDLS"
    assert result.hops[2].connection_id == "CONN-GZB-UP-THROUGH"


def test_crossover_direction_conflict_pruning(curated_corridor_fixture):
    """GZB crossover connects DN line to UP line. For a DOWN train, UP track is incompatible,
    so crossover candidate path is pruned, leaving exactly 1 valid through path."""
    f = curated_corridor_fixture
    router = DeterministicTopologyRouter(
        sections=f["sections"],
        tracks=f["tracks"],
        topology_nodes=f["nodes"],
        topology_connections=f["connections"],
        track_endpoints=f["endpoints"],
    )

    t0 = datetime(2026, 10, 10, 6, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 10, 10, 7, 30, tzinfo=timezone.utc)

    pass_obj = TrainPass(
        pass_id="PASS-12004-NDLS-KRJ",
        train_id="TRN-12004",
        train_number="12004",
        section_id=None,
        from_station_id="STN-NDLS",
        to_station_id="STN-KRJ",
        interval=TimeInterval(start=t0, end=t1),
        movement_type="STATION_HOP",
    )

    result = router.resolve_pass_route(pass_obj)
    assert result.status == TraversalResolutionStatus.EXPANDED_ROUTE
    assert len(result.hops) == 2
    # Confirms through path was selected, not crossover
    assert result.hops[1].track_id == "TRK-GZB-KRJ-DN"
    assert result.hops[1].connection_id == "CONN-GZB-DN-THROUGH"


def test_ambiguous_route_detection(curated_corridor_fixture):
    """When the crossover target track is BIDIRECTIONAL, both through path and crossover path
    are valid. Router MUST return AMBIGUOUS_ROUTE and MUST NOT fabricate track assignment."""
    f = curated_corridor_fixture

    # Modify GZB-KRJ-UP to be BIDIRECTIONAL
    modified_tracks = [dict(t) for t in f["tracks"]]
    for t in modified_tracks:
        if t["track_id"] == "TRK-GZB-KRJ-UP":
            t["direction"] = "BIDIRECTIONAL"

    router = DeterministicTopologyRouter(
        sections=f["sections"],
        tracks=modified_tracks,
        topology_nodes=f["nodes"],
        topology_connections=f["connections"],
        track_endpoints=f["endpoints"],
    )

    t0 = datetime(2026, 10, 10, 6, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 10, 10, 7, 30, tzinfo=timezone.utc)

    pass_obj = TrainPass(
        pass_id="PASS-12004-NDLS-KRJ",
        train_id="TRN-12004",
        train_number="12004",
        section_id=None,
        from_station_id="STN-NDLS",
        to_station_id="STN-KRJ",
        interval=TimeInterval(start=t0, end=t1),
        movement_type="STATION_HOP",
    )

    result = router.resolve_pass_route(pass_obj)
    assert result.status == TraversalResolutionStatus.AMBIGUOUS_ROUTE
    assert result.candidate_path_count == 2
    assert "Multiple valid physical paths" in result.unresolved_reason

    # Expand into traversals via CompatibilityEngine
    trvs = CompatibilityEngine.expand_train_traversals(
        train_passes=[pass_obj],
        sections=f["sections"],
        tracks=modified_tracks,
        topology_nodes=f["nodes"],
        topology_connections=f["connections"],
        track_endpoints=f["endpoints"],
    )
    assert len(trvs) == 1
    assert trvs[0].resolution_status == TraversalResolutionStatus.AMBIGUOUS_ROUTE
    assert trvs[0].traversal_track_id is None
    assert "AMBIGUOUS_ROUTE" in trvs[0].unresolved_reason


def test_disconnected_topology_yields_unresolved(curated_corridor_fixture):
    """When a required connection is missing on the corridor, returns UNRESOLVED with explicit reason."""
    f = curated_corridor_fixture

    # Remove the KRJ DN connection
    missing_krj_conns = [c for c in f["connections"] if c["connection_id"] != "CONN-KRJ-DN-THROUGH"]

    router = DeterministicTopologyRouter(
        sections=f["sections"],
        tracks=f["tracks"],
        topology_nodes=f["nodes"],
        topology_connections=missing_krj_conns,
        track_endpoints=f["endpoints"],
    )

    t0 = datetime(2026, 10, 10, 6, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)

    pass_obj = TrainPass(
        pass_id="PASS-12301-NDLS-ALJN",
        train_id="TRN-12301",
        train_number="12301",
        section_id=None,
        from_station_id="STN-NDLS",
        to_station_id="STN-ALJN",
        interval=TimeInterval(start=t0, end=t1),
        movement_type="STATION_HOP",
    )

    result = router.resolve_pass_route(pass_obj)
    assert result.status == TraversalResolutionStatus.UNRESOLVED
    assert result.hops == []
    assert "DISCONNECTED_ROUTE" in result.unresolved_reason


def test_permutation_invariance_and_determinism(curated_corridor_fixture):
    """Shuffling the input list of connections and tracks produces identical resolution output."""
    f = curated_corridor_fixture

    t0 = datetime(2026, 10, 10, 6, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)
    pass_obj = TrainPass(
        pass_id="PASS-12301-NDLS-ALJN",
        train_id="TRN-12301",
        train_number="12301",
        section_id=None,
        from_station_id="STN-NDLS",
        to_station_id="STN-ALJN",
        interval=TimeInterval(start=t0, end=t1),
        movement_type="STATION_HOP",
    )

    baseline_router = DeterministicTopologyRouter(
        sections=f["sections"],
        tracks=f["tracks"],
        topology_nodes=f["nodes"],
        topology_connections=f["connections"],
        track_endpoints=f["endpoints"],
    )
    baseline_res = baseline_router.resolve_pass_route(pass_obj)

    # Repeat with 10 random permutations
    rng = random.Random(42)
    for _ in range(10):
        shuffled_conns = list(f["connections"])
        shuffled_tracks = list(f["tracks"])
        shuffled_endpoints = list(f["endpoints"])
        rng.shuffle(shuffled_conns)
        rng.shuffle(shuffled_tracks)
        rng.shuffle(shuffled_endpoints)

        router = DeterministicTopologyRouter(
            sections=f["sections"],
            tracks=shuffled_tracks,
            topology_nodes=f["nodes"],
            topology_connections=shuffled_conns,
            track_endpoints=shuffled_endpoints,
        )
        res = router.resolve_pass_route(pass_obj)

        assert res.status == baseline_res.status
        assert res.unresolved_reason == baseline_res.unresolved_reason
        assert len(res.hops) == len(baseline_res.hops)
        for h1, h2 in zip(res.hops, baseline_res.hops):
            assert h1.section_id == h2.section_id
            assert h1.track_id == h2.track_id
            assert h1.connection_id == h2.connection_id


def test_backward_compatibility_fallback_no_topology(curated_corridor_fixture):
    """When a corridor has no topology at all, expand_train_traversals preserves coarse
    section expansion with traversal_track_id = None."""
    f = curated_corridor_fixture

    # An unrelated corridor STN-X -> STN-Y -> STN-Z
    other_sections = [
        {
            "section_id": "SEC-X-Y",
            "section_code": "X-Y",
            "from_station_id": "STN-X",
            "to_station_id": "STN-Y",
            "length_km": 15.0,
            "track_count": 1,
            "electrified": False,
        },
        {
            "section_id": "SEC-Y-Z",
            "section_code": "Y-Z",
            "from_station_id": "STN-Y",
            "to_station_id": "STN-Z",
            "length_km": 25.0,
            "track_count": 1,
            "electrified": False,
        },
    ]

    all_sections = f["sections"] + other_sections

    t0 = datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 10, 10, 9, 0, tzinfo=timezone.utc)

    pass_obj = TrainPass(
        pass_id="PASS-99001-X-Z",
        train_id="TRN-99001",
        train_number="99001",
        section_id=None,
        from_station_id="STN-X",
        to_station_id="STN-Z",
        interval=TimeInterval(start=t0, end=t1),
        movement_type="STATION_HOP",
    )

    trvs = CompatibilityEngine.expand_train_traversals(
        train_passes=[pass_obj],
        sections=all_sections,
        tracks=f["tracks"],
        topology_nodes=f["nodes"],
        topology_connections=f["connections"],
        track_endpoints=f["endpoints"],
    )

    assert len(trvs) == 2
    assert trvs[0].section_id == "SEC-X-Y"
    assert trvs[0].traversal_track_id is None
    assert trvs[0].resolution_status == TraversalResolutionStatus.EXPANDED_ROUTE

    assert trvs[1].section_id == "SEC-Y-Z"
    assert trvs[1].traversal_track_id is None
    assert trvs[1].resolution_status == TraversalResolutionStatus.EXPANDED_ROUTE


def test_snapshot_hash_stability_unaffected_by_phase17_routing(curated_corridor_fixture):
    """PlanningSnapshot.compute_snapshot_hash() remains 100% stable regardless of topology presence."""
    from types import SimpleNamespace

    f = curated_corridor_fixture
    horizon = PlanningHorizon(
        start=datetime(2026, 10, 10, 0, 0, tzinfo=timezone.utc),
        end=datetime(2026, 10, 11, 0, 0, tzinfo=timezone.utc),
    )

    tasks = [
        {
            "task_id": "TSK-001",
            "task_code": "T1",
            "section_id": "SEC-NDLS-GZB",
            "window_start": "2026-10-10T06:00:00Z",
            "window_end": "2026-10-10T10:00:00Z",
            "estimated_duration_minutes": 120,
        }
    ]

    bundle_without_topology = SimpleNamespace(
        scenario={
            "scenario_id": "SCEN-TEST-STABILITY",
            "planning_start": "2026-10-10T00:00:00Z",
            "planning_end": "2026-10-11T00:00:00Z",
        },
        work_orders=[],
        tasks=tasks,
        dependencies=[],
        resources=[],
        resource_availabilities=[],
        sections=f["sections"],
        train_movements=[],
        applicable_rules=[],
        tracks=[],
        train_traversals=[],
    )

    bundle_with_topology = SimpleNamespace(
        scenario={
            "scenario_id": "SCEN-TEST-STABILITY",
            "planning_start": "2026-10-10T00:00:00Z",
            "planning_end": "2026-10-11T00:00:00Z",
        },
        work_orders=[],
        tasks=tasks,
        dependencies=[],
        resources=[],
        resource_availabilities=[],
        sections=f["sections"],
        train_movements=[],
        applicable_rules=[],
        tracks=f["tracks"],
        train_traversals=[],
        topology_nodes=f["nodes"],
        topology_connections=f["connections"],
        track_endpoints=f["endpoints"],
    )

    snap1 = PlanningSnapshot.from_bundle(bundle_without_topology)
    snap2 = PlanningSnapshot.from_bundle(bundle_with_topology)

    assert snap1.compute_snapshot_hash() == snap2.compute_snapshot_hash()
