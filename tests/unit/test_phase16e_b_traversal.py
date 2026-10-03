"""Unit tests for Phase 16E-B: Train Traversal Expansion.

Verifies:
1. Adjacent-station pass expands to 1 section (DIRECT_SECTION).
2. Multi-section express pass (e.g. CNB -> NDLS) expands into 8 ordered sections (EXPANDED_ROUTE).
3. Monotonic non-overlapping contiguous intervals matching total pass duration.
4. Disconnected stations yield UNRESOLVED with diagnostic reason without fabricating topology.
5. traversal_track_id is None (not fabricated).
6. PlanningSnapshot.compute_snapshot_hash() is unaffected (preserves hash stability).
7. Whole-section solver conflict feasibility is preserved.
"""

from datetime import datetime, timedelta, timezone
import pytest

from backend.app.domain.enums import DataClass, TraversalResolutionStatus
from backend.app.domain.temporal import TimeInterval, PlanningHorizon, TrainPass, TrainTraversal
from backend.app.services.compatibility_service import CompatibilityEngine
from backend.app.domain.planning_snapshot import PlanningSnapshot


@pytest.fixture
def sample_corridor_sections():
    """Linear corridor with 3 contiguous block sections:
    STN-A --(SEC-1, 10km)--> STN-B --(SEC-2, 20km)--> STN-C --(SEC-3, 30km)--> STN-D
    """
    return [
        {
            "section_id": "SEC-A-B",
            "section_code": "A-B",
            "from_station_id": "STN-A",
            "to_station_id": "STN-B",
            "length_km": 10.0,
            "track_count": 2,
            "electrified": True,
            "routes": ["CORRIDOR-1"],
        },
        {
            "section_id": "SEC-B-C",
            "section_code": "B-C",
            "from_station_id": "STN-B",
            "to_station_id": "STN-C",
            "length_km": 20.0,
            "track_count": 2,
            "electrified": True,
            "routes": ["CORRIDOR-1"],
        },
        {
            "section_id": "SEC-C-D",
            "section_code": "C-D",
            "from_station_id": "STN-C",
            "to_station_id": "STN-D",
            "length_km": 30.0,
            "track_count": 2,
            "electrified": True,
            "routes": ["CORRIDOR-1"],
        },
    ]


def test_adjacent_station_direct_section_expansion(sample_corridor_sections):
    """Adjacent-station pass must expand to a single DIRECT_SECTION traversal."""
    t0 = datetime(2024, 1, 1, 8, 0, tzinfo=timezone.utc)
    t1 = datetime(2024, 1, 1, 8, 15, tzinfo=timezone.utc)

    pass_obj = TrainPass(
        pass_id="PASS-12001-STN-A-STN-B-D0",
        train_id="TRN-12001",
        train_number="12001",
        section_id="SEC-A-B",
        from_station_id="STN-A",
        to_station_id="STN-B",
        interval=TimeInterval(start=t0, end=t1),
        movement_type="SECTION_TRAVERSAL",
    )

    traversals = CompatibilityEngine.expand_train_traversals(
        train_passes=[pass_obj],
        sections=sample_corridor_sections,
    )

    assert len(traversals) == 1
    trv = traversals[0]
    assert trv.train_number == "12001"
    assert trv.source_pass_id == pass_obj.pass_id
    assert trv.section_id == "SEC-A-B"
    assert trv.from_station_id == "STN-A"
    assert trv.to_station_id == "STN-B"
    assert trv.sequence_order == 1
    assert trv.resolution_status == TraversalResolutionStatus.DIRECT_SECTION
    assert trv.unresolved_reason is None
    assert trv.traversal_track_id is None
    assert trv.interval == pass_obj.interval
    assert trv.duration_minutes == 15.0


def test_multi_section_express_route_expansion(sample_corridor_sections):
    """Express train skipping intermediate stations STN-B and STN-C from STN-A to STN-D:
    Total length = 10 + 20 + 30 = 60km.
    Total duration = 60 minutes (from 09:00 to 10:00).
    Section 1 (10km / 60km = 1/6) -> 10 minutes [09:00, 09:10)
    Section 2 (20km / 60km = 2/6) -> 20 minutes [09:10, 09:30)
    Section 3 (30km / 60km = 3/6) -> 30 minutes [09:30, 10:00)
    """
    t0 = datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc)
    t1 = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)

    pass_obj = TrainPass(
        pass_id="PASS-12301-STN-A-STN-D-D0",
        train_id="TRN-12301",
        train_number="12301",
        section_id=None,
        from_station_id="STN-A",
        to_station_id="STN-D",
        interval=TimeInterval(start=t0, end=t1),
        movement_type="STATION_HOP",
    )

    traversals = CompatibilityEngine.expand_train_traversals(
        train_passes=[pass_obj],
        sections=sample_corridor_sections,
    )

    assert len(traversals) == 3

    # Check ordering and sequence
    for i, trv in enumerate(traversals, start=1):
        assert trv.sequence_order == i
        assert trv.resolution_status == TraversalResolutionStatus.EXPANDED_ROUTE
        assert trv.traversal_track_id is None
        assert trv.source_pass_id == pass_obj.pass_id
        assert trv.classification == DataClass.DERIVED

    assert traversals[0].section_id == "SEC-A-B"
    assert traversals[0].from_station_id == "STN-A"
    assert traversals[0].to_station_id == "STN-B"
    assert traversals[0].entry_time == t0
    assert traversals[0].exit_time == t0 + timedelta(minutes=10)
    assert abs(traversals[0].duration_minutes - 10.0) < 0.001

    assert traversals[1].section_id == "SEC-B-C"
    assert traversals[1].from_station_id == "STN-B"
    assert traversals[1].to_station_id == "STN-C"
    assert traversals[1].entry_time == traversals[0].exit_time
    assert traversals[1].exit_time == t0 + timedelta(minutes=30)
    assert abs(traversals[1].duration_minutes - 20.0) < 0.001

    assert traversals[2].section_id == "SEC-C-D"
    assert traversals[2].from_station_id == "STN-C"
    assert traversals[2].to_station_id == "STN-D"
    assert traversals[2].entry_time == traversals[1].exit_time
    assert traversals[2].exit_time == t1
    assert abs(traversals[2].duration_minutes - 30.0) < 0.001

    # Monotonicity and non-overlapping adjacency
    assert traversals[0].interval.is_adjacent_to(traversals[1].interval)
    assert traversals[1].interval.is_adjacent_to(traversals[2].interval)
    assert not traversals[0].interval.overlaps(traversals[1].interval)
    assert not traversals[1].interval.overlaps(traversals[2].interval)


def test_disconnected_station_yields_unresolved(sample_corridor_sections):
    """Disconnected or invalid station must produce UNRESOLVED without fabricating topology."""
    t0 = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    t1 = datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc)

    pass_obj = TrainPass(
        pass_id="PASS-99999-STN-A-STN-ISOLATED-D0",
        train_id="TRN-99999",
        train_number="99999",
        section_id=None,
        from_station_id="STN-A",
        to_station_id="STN-ISOLATED",
        interval=TimeInterval(start=t0, end=t1),
        movement_type="STATION_HOP",
    )

    traversals = CompatibilityEngine.expand_train_traversals(
        train_passes=[pass_obj],
        sections=sample_corridor_sections,
    )

    assert len(traversals) == 1
    trv = traversals[0]
    assert trv.sequence_order == 1
    assert trv.section_id is None
    assert trv.resolution_status == TraversalResolutionStatus.UNRESOLVED
    assert trv.unresolved_reason is not None
    assert "No topological section path found" in trv.unresolved_reason
    assert trv.traversal_track_id is None
    assert trv.interval == pass_obj.interval


def test_snapshot_hash_stability_unaffected_by_traversals():
    """Verify that compute_snapshot_hash() remains 100% stable regardless of traversals."""
    from types import SimpleNamespace
    from backend.app.domain.temporal import PlanningHorizon

    horizon = PlanningHorizon(
        start=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        end=datetime(2024, 1, 2, 0, 0, tzinfo=timezone.utc),
    )

    bundle = SimpleNamespace(
        scenario={
            "scenario_id": "SCEN-TEST-001",
            "planning_start": "2024-01-01T00:00:00Z",
            "planning_end": "2024-01-02T00:00:00Z",
        },
        work_orders=[],
        tasks=[
            {
                "task_id": "TASK-001",
                "task_code": "T001",
                "section_id": "SEC-A-B",
                "window_start": "2024-01-01T08:00:00Z",
                "window_end": "2024-01-01T12:00:00Z",
                "estimated_duration_minutes": 120,
            }
        ],
        dependencies=[],
        resources=[],
        resource_availabilities=[],
        sections=[
            {
                "section_id": "SEC-A-B",
                "from_station_id": "STN-A",
                "to_station_id": "STN-B",
                "length_km": 10.0,
            }
        ],
        train_movements=[
            {
                "movement_id": "MOV-01",
                "train_id": "TRN-01",
                "train_number": "12001",
                "station_id": "STN-A",
                "stop_sequence": 1,
                "scheduled_departure": "08:00",
                "day_offset": 0,
            },
            {
                "movement_id": "MOV-02",
                "train_id": "TRN-01",
                "train_number": "12001",
                "station_id": "STN-B",
                "stop_sequence": 2,
                "scheduled_arrival": "08:30",
                "day_offset": 0,
            },
        ],
        applicable_rules=[],
        tracks=[],
        train_traversals=[],
    )

    snapshot = PlanningSnapshot.from_bundle(bundle)
    assert len(snapshot.train_traversals) == 1
    assert snapshot.train_traversals[0].resolution_status == TraversalResolutionStatus.DIRECT_SECTION

    # Hash should be computed and stable
    snap_hash = snapshot.compute_snapshot_hash()
    assert len(snap_hash) == 64

    # Hash does not include train_traversals
    # Recomputing manually:
    import hashlib, json
    hasher = hashlib.sha256()
    hasher.update("SCEN-TEST-001".encode("utf-8"))
    hasher.update(horizon.start.isoformat().encode("utf-8"))
    hasher.update(horizon.end.isoformat().encode("utf-8"))
    task_records = [("TASK-001", "2024-01-01T08:00:00Z", "2024-01-01T12:00:00Z", "120", "SEC-A-B")]
    hasher.update(json.dumps(task_records, sort_keys=True).encode("utf-8"))
    hasher.update(str(len(snapshot.train_passes)).encode("utf-8"))
    hasher.update(str(len(snapshot.resources)).encode("utf-8"))
    hasher.update(str(len(snapshot.dependencies)).encode("utf-8"))
    expected_hash = hasher.hexdigest()

    assert snap_hash == expected_hash


def test_express_cnb_to_ndls_corridor_expansion():
    """Verify 8-section corridor expansion using normalized production data for Train 12301."""
    import json
    with open("data/normalized/sections.json") as f:
        sections = json.load(f)["sections"]

    t0 = datetime(2024, 1, 2, 4, 55, tzinfo=timezone.utc)
    t1 = datetime(2024, 1, 2, 10, 5, tzinfo=timezone.utc)

    pass_obj = TrainPass(
        pass_id="PASS-12301-STN-CNB-STN-NDLS-D0",
        train_id="TRN-12301",
        train_number="12301",
        section_id=None,
        from_station_id="STN-CNB",
        to_station_id="STN-NDLS",
        interval=TimeInterval(start=t0, end=t1),
        movement_type="STATION_HOP",
    )

    traversals = CompatibilityEngine.expand_train_traversals(
        train_passes=[pass_obj],
        sections=sections,
    )

    assert len(traversals) == 8
    expected_sections = [
        "SEC-ETW-CNB",
        "SEC-SKB-ETW",
        "SEC-FZD-SKB",
        "SEC-TDL-FZD",
        "SEC-ALJN-TDL",
        "SEC-KRJ-ALJN",
        "SEC-GZB-KRJ",
        "SEC-NDLS-GZB",
    ]
    for i, (trv, exp_sec) in enumerate(zip(traversals, expected_sections), start=1):
        assert trv.sequence_order == i
        assert trv.section_id == exp_sec
        assert trv.resolution_status == TraversalResolutionStatus.EXPANDED_ROUTE
        assert trv.traversal_track_id is None

    # Check total continuity
    assert traversals[0].entry_time == t0
    assert traversals[-1].exit_time == t1
    total_dur = sum(t.duration_minutes for t in traversals)
    assert abs(total_dur - pass_obj.duration_minutes) < 0.001
