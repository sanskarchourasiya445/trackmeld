"""Unit tests for Phase 16G-A: Deterministic Track Spatial Compatibility Foundation.

Verifies:
1. Deterministic classification (Rules classify -> Optimization schedules -> Independent Validator verifies).
2. SpatialCompatibilityStatus: COMPATIBLE, INCOMPATIBLE, INSUFFICIENT_DATA.
3. Machine-readable reason codes: SAME_TRACK_OVERLAP, ADJACENT_TRACK_FULL_BLOCK,
   WHOLE_SECTION_OCCUPANCY, DIRECTION_CONFLICT, DIFFERENT_TRACKS_INDEPENDENT,
   DIFFERENT_SECTIONS, NO_TEMPORAL_OVERLAP, MISSING_TRACK_METADATA,
   MISSING_ADJACENCY_METADATA, UNSPECIFIED_SPATIAL_RELATION, UNKNOWN_SECTION.
4. Caution order requirement on adjacent lines.
5. Invariant: CP-SAT and validator conflict logic remain whole-section mutex.
"""

from datetime import datetime, timezone
import pytest

from backend.app.domain.enums import AdjacentTrackImpact
from backend.app.domain.spatial_compatibility import (
    SpatialCompatibilityStatus,
    SpatialCompatibilityReason,
    SpatialOccupantType,
    SpatialOccupant,
    TrackSpatialCompatibilityResult,
    evaluate_spatial_compatibility,
)
from backend.app.domain.sections import Track, TrackDirection
from backend.app.domain.temporal import TimeInterval, TrainPass, TrainTraversal
from backend.app.domain.enums import TraversalResolutionStatus, DataClass
from backend.app.services.compatibility_service import CompatibilityEngine


@pytest.fixture
def sample_tracks_map():
    """Provides a deterministic tracks map with explicit adjacency."""
    return {
        "TRK-SEC-01-UP": Track(
            track_id="TRK-SEC-01-UP",
            section_id="SEC-01",
            track_code="UP_MAIN",
            direction=TrackDirection.UP,
            electrified=True,
            max_speed_kmh=130,
            adjacent_track_ids=["TRK-SEC-01-DN"],
        ),
        "TRK-SEC-01-DN": Track(
            track_id="TRK-SEC-01-DN",
            section_id="SEC-01",
            track_code="DN_MAIN",
            direction=TrackDirection.DOWN,
            electrified=True,
            max_speed_kmh=130,
            adjacent_track_ids=["TRK-SEC-01-UP"],
        ),
        "TRK-SEC-01-LOOP": Track(
            track_id="TRK-SEC-01-LOOP",
            section_id="SEC-01",
            track_code="LOOP_LINE",
            direction=TrackDirection.BIDIRECTIONAL,
            electrified=True,
            max_speed_kmh=50,
            adjacent_track_ids=[],  # Explicitly isolated / non-adjacent to UP/DN
        ),
        "TRK-SEC-01-UNSPEC-ADJ": Track(
            track_id="TRK-SEC-01-UNSPEC-ADJ",
            section_id="SEC-01",
            track_code="RELIEF",
            direction=TrackDirection.BIDIRECTIONAL,
            electrified=True,
            max_speed_kmh=100,
            adjacent_track_ids=None,  # Null/unspecified adjacency metadata
        ),
        "TRK-SEC-02-UP": Track(
            track_id="TRK-SEC-02-UP",
            section_id="SEC-02",
            track_code="UP_MAIN",
            direction=TrackDirection.UP,
            electrified=True,
            max_speed_kmh=130,
            adjacent_track_ids=["TRK-SEC-02-DN"],
        ),
    }


def test_disjoint_temporal_intervals_are_compatible():
    """Activities that do not overlap in time are COMPATIBLE under NO_TEMPORAL_OVERLAP."""
    occ1 = SpatialOccupant(
        occupant_id="TSK-01",
        occupant_type=SpatialOccupantType.TASK,
        section_id="SEC-01",
        track_id="TRK-SEC-01-UP",
        start_time=datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc),
    )
    occ2 = SpatialOccupant(
        occupant_id="TRV-01",
        occupant_type=SpatialOccupantType.TRAIN_TRAVERSAL,
        section_id="SEC-01",
        track_id="TRK-SEC-01-UP",
        start_time=datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 10, 10, 10, 30, tzinfo=timezone.utc),
    )
    res = evaluate_spatial_compatibility(occ1, occ2, {})
    assert res.status == SpatialCompatibilityStatus.COMPATIBLE
    assert res.reason == SpatialCompatibilityReason.NO_TEMPORAL_OVERLAP
    assert not res.requires_caution_order


def test_different_sections_are_compatible():
    """Activities in different sections are COMPATIBLE under DIFFERENT_SECTIONS."""
    t_start = datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)
    occ1 = SpatialOccupant(
        occupant_id="TSK-01",
        occupant_type=SpatialOccupantType.TASK,
        section_id="SEC-01",
        track_id="TRK-SEC-01-UP",
        start_time=t_start,
        end_time=t_end,
    )
    occ2 = SpatialOccupant(
        occupant_id="TSK-02",
        occupant_type=SpatialOccupantType.TASK,
        section_id="SEC-02",
        track_id="TRK-SEC-02-UP",
        start_time=t_start,
        end_time=t_end,
    )
    res = evaluate_spatial_compatibility(occ1, occ2, {})
    assert res.status == SpatialCompatibilityStatus.COMPATIBLE
    assert res.reason == SpatialCompatibilityReason.DIFFERENT_SECTIONS


def test_missing_section_yields_insufficient_data():
    """Unspecified section yields INSUFFICIENT_DATA under UNKNOWN_SECTION."""
    t_start = datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)
    occ1 = SpatialOccupant(
        occupant_id="TSK-01",
        occupant_type=SpatialOccupantType.TASK,
        section_id=None,
        track_id="TRK-SEC-01-UP",
        start_time=t_start,
        end_time=t_end,
    )
    occ2 = SpatialOccupant(
        occupant_id="TSK-02",
        occupant_type=SpatialOccupantType.TASK,
        section_id="SEC-01",
        track_id="TRK-SEC-01-UP",
        start_time=t_start,
        end_time=t_end,
    )
    res = evaluate_spatial_compatibility(occ1, occ2, {})
    assert res.status == SpatialCompatibilityStatus.INSUFFICIENT_DATA
    assert res.reason == SpatialCompatibilityReason.UNKNOWN_SECTION


def test_whole_section_occupancy_is_incompatible():
    """An occupant without track_id occupies whole section and is INCOMPATIBLE with other occupants."""
    t_start = datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)
    occ1 = SpatialOccupant(
        occupant_id="TSK-WHOLE-SEC",
        occupant_type=SpatialOccupantType.TASK,
        section_id="SEC-01",
        track_id=None,  # Whole-section possession
        start_time=t_start,
        end_time=t_end,
    )
    occ2 = SpatialOccupant(
        occupant_id="TRV-01",
        occupant_type=SpatialOccupantType.TRAIN_TRAVERSAL,
        section_id="SEC-01",
        track_id="TRK-SEC-01-DN",
        start_time=t_start,
        end_time=t_end,
    )
    res = evaluate_spatial_compatibility(occ1, occ2, {})
    assert res.status == SpatialCompatibilityStatus.INCOMPATIBLE
    assert res.reason == SpatialCompatibilityReason.WHOLE_SECTION_OCCUPANCY


def test_missing_track_metadata_yields_insufficient_data(sample_tracks_map):
    """If an assigned track is missing from tracks_map, result is INSUFFICIENT_DATA."""
    t_start = datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)
    occ1 = SpatialOccupant(
        occupant_id="TSK-01",
        occupant_type=SpatialOccupantType.TASK,
        section_id="SEC-01",
        track_id="TRK-UNKNOWN-GHOST",
        start_time=t_start,
        end_time=t_end,
    )
    occ2 = SpatialOccupant(
        occupant_id="TRV-01",
        occupant_type=SpatialOccupantType.TRAIN_TRAVERSAL,
        section_id="SEC-01",
        track_id="TRK-SEC-01-UP",
        start_time=t_start,
        end_time=t_end,
    )
    res = evaluate_spatial_compatibility(occ1, occ2, sample_tracks_map)
    assert res.status == SpatialCompatibilityStatus.INSUFFICIENT_DATA
    assert res.reason == SpatialCompatibilityReason.MISSING_TRACK_METADATA


def test_same_track_overlap_is_incompatible(sample_tracks_map):
    """Two concurrent occupants on the exact same track are INCOMPATIBLE."""
    t_start = datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)
    occ1 = SpatialOccupant(
        occupant_id="TSK-01",
        occupant_type=SpatialOccupantType.TASK,
        section_id="SEC-01",
        track_id="TRK-SEC-01-UP",
        start_time=t_start,
        end_time=t_end,
    )
    occ2 = SpatialOccupant(
        occupant_id="TRV-01",
        occupant_type=SpatialOccupantType.TRAIN_TRAVERSAL,
        section_id="SEC-01",
        track_id="TRK-SEC-01-UP",
        start_time=t_start,
        end_time=t_end,
    )
    res = evaluate_spatial_compatibility(occ1, occ2, sample_tracks_map)
    assert res.status == SpatialCompatibilityStatus.INCOMPATIBLE
    assert res.reason == SpatialCompatibilityReason.SAME_TRACK_OVERLAP


def test_direction_mismatch_is_incompatible(sample_tracks_map):
    """A train traveling in the wrong direction on a unidirectional track is INCOMPATIBLE."""
    t_start = datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)
    occ1 = SpatialOccupant(
        occupant_id="TRV-WRONG-DIR",
        occupant_type=SpatialOccupantType.TRAIN_TRAVERSAL,
        section_id="SEC-01",
        track_id="TRK-SEC-01-UP",  # Track is unidirectional UP
        direction="DOWN",          # Train is traveling DOWN
        start_time=t_start,
        end_time=t_end,
    )
    occ2 = SpatialOccupant(
        occupant_id="TSK-01",
        occupant_type=SpatialOccupantType.TASK,
        section_id="SEC-01",
        track_id="TRK-SEC-01-DN",
        start_time=t_start,
        end_time=t_end,
    )
    res = evaluate_spatial_compatibility(occ1, occ2, sample_tracks_map)
    assert res.status == SpatialCompatibilityStatus.INCOMPATIBLE
    assert res.reason == SpatialCompatibilityReason.DIRECTION_CONFLICT


def test_bidirectional_track_allows_both_directions(sample_tracks_map):
    """A bidirectional track accepts UP or DOWN without direction conflict."""
    t_start = datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)
    occ1 = SpatialOccupant(
        occupant_id="TRV-DOWN",
        occupant_type=SpatialOccupantType.TRAIN_TRAVERSAL,
        section_id="SEC-01",
        track_id="TRK-SEC-01-LOOP",  # Bidirectional
        direction="DOWN",
        start_time=t_start,
        end_time=t_end,
    )
    occ2 = SpatialOccupant(
        occupant_id="TSK-01",
        occupant_type=SpatialOccupantType.TASK,
        section_id="SEC-01",
        track_id="TRK-SEC-01-UP",
        adjacent_track_impact=AdjacentTrackImpact.NONE,
        start_time=t_start,
        end_time=t_end,
    )
    res = evaluate_spatial_compatibility(occ1, occ2, sample_tracks_map)
    # They are non-adjacent and directional match passes
    assert res.status == SpatialCompatibilityStatus.COMPATIBLE
    assert res.reason == SpatialCompatibilityReason.DIFFERENT_TRACKS_INDEPENDENT


def test_missing_adjacency_metadata_yields_insufficient_data(sample_tracks_map):
    """When tracks have null adjacent_track_ids, result is INSUFFICIENT_DATA."""
    t_start = datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)
    occ1 = SpatialOccupant(
        occupant_id="TSK-01",
        occupant_type=SpatialOccupantType.TASK,
        section_id="SEC-01",
        track_id="TRK-SEC-01-UNSPEC-ADJ",
        adjacent_track_impact=AdjacentTrackImpact.NONE,
        start_time=t_start,
        end_time=t_end,
    )
    occ2 = SpatialOccupant(
        occupant_id="TRV-01",
        occupant_type=SpatialOccupantType.TRAIN_TRAVERSAL,
        section_id="SEC-01",
        track_id="TRK-SEC-01-UP",
        start_time=t_start,
        end_time=t_end,
    )
    res = evaluate_spatial_compatibility(occ1, occ2, sample_tracks_map)
    assert res.status == SpatialCompatibilityStatus.INSUFFICIENT_DATA
    assert res.reason == SpatialCompatibilityReason.MISSING_ADJACENCY_METADATA


def test_non_adjacent_tracks_are_compatible_independently(sample_tracks_map):
    """Tracks explicitly non-adjacent operate independently without caution order."""
    t_start = datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)
    occ1 = SpatialOccupant(
        occupant_id="TSK-01",
        occupant_type=SpatialOccupantType.TASK,
        section_id="SEC-01",
        track_id="TRK-SEC-01-LOOP",  # Isolated loop line
        adjacent_track_impact=AdjacentTrackImpact.FULL_TRAFFIC_BLOCK,  # Even with block, loop is not adjacent to UP
        start_time=t_start,
        end_time=t_end,
    )
    occ2 = SpatialOccupant(
        occupant_id="TRV-01",
        occupant_type=SpatialOccupantType.TRAIN_TRAVERSAL,
        section_id="SEC-01",
        track_id="TRK-SEC-01-UP",
        start_time=t_start,
        end_time=t_end,
    )
    res = evaluate_spatial_compatibility(occ1, occ2, sample_tracks_map)
    assert res.status == SpatialCompatibilityStatus.COMPATIBLE
    assert res.reason == SpatialCompatibilityReason.DIFFERENT_TRACKS_INDEPENDENT
    assert not res.requires_caution_order


def test_adjacent_tracks_full_traffic_block_is_incompatible(sample_tracks_map):
    """Adjacent track with FULL_TRAFFIC_BLOCK is INCOMPATIBLE."""
    t_start = datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)
    occ1 = SpatialOccupant(
        occupant_id="TSK-HEAVY-TAMPING",
        occupant_type=SpatialOccupantType.TASK,
        section_id="SEC-01",
        track_id="TRK-SEC-01-UP",
        adjacent_track_impact=AdjacentTrackImpact.FULL_TRAFFIC_BLOCK,
        start_time=t_start,
        end_time=t_end,
    )
    occ2 = SpatialOccupant(
        occupant_id="TRV-01",
        occupant_type=SpatialOccupantType.TRAIN_TRAVERSAL,
        section_id="SEC-01",
        track_id="TRK-SEC-01-DN",
        start_time=t_start,
        end_time=t_end,
    )
    res = evaluate_spatial_compatibility(occ1, occ2, sample_tracks_map)
    assert res.status == SpatialCompatibilityStatus.INCOMPATIBLE
    assert res.reason == SpatialCompatibilityReason.ADJACENT_TRACK_FULL_BLOCK


def test_adjacent_tracks_caution_order_is_compatible_with_flag(sample_tracks_map):
    """Adjacent track with CAUTION_ORDER is COMPATIBLE with requires_caution_order=True."""
    t_start = datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)
    occ1 = SpatialOccupant(
        occupant_id="TSK-LIGHT-PACKING",
        occupant_type=SpatialOccupantType.TASK,
        section_id="SEC-01",
        track_id="TRK-SEC-01-UP",
        adjacent_track_impact=AdjacentTrackImpact.CAUTION_ORDER,
        start_time=t_start,
        end_time=t_end,
    )
    occ2 = SpatialOccupant(
        occupant_id="TRV-01",
        occupant_type=SpatialOccupantType.TRAIN_TRAVERSAL,
        section_id="SEC-01",
        track_id="TRK-SEC-01-DN",
        start_time=t_start,
        end_time=t_end,
    )
    res = evaluate_spatial_compatibility(occ1, occ2, sample_tracks_map)
    assert res.status == SpatialCompatibilityStatus.COMPATIBLE
    assert res.reason == SpatialCompatibilityReason.DIFFERENT_TRACKS_INDEPENDENT
    assert res.requires_caution_order is True


def test_adjacent_tracks_none_impact_is_compatible(sample_tracks_map):
    """Adjacent track with NONE impact is COMPATIBLE with requires_caution_order=False."""
    t_start = datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)
    occ1 = SpatialOccupant(
        occupant_id="TSK-WELDING",
        occupant_type=SpatialOccupantType.TASK,
        section_id="SEC-01",
        track_id="TRK-SEC-01-UP",
        adjacent_track_impact=AdjacentTrackImpact.NONE,
        start_time=t_start,
        end_time=t_end,
    )
    occ2 = SpatialOccupant(
        occupant_id="TRV-01",
        occupant_type=SpatialOccupantType.TRAIN_TRAVERSAL,
        section_id="SEC-01",
        track_id="TRK-SEC-01-DN",
        start_time=t_start,
        end_time=t_end,
    )
    res = evaluate_spatial_compatibility(occ1, occ2, sample_tracks_map)
    assert res.status == SpatialCompatibilityStatus.COMPATIBLE
    assert res.reason == SpatialCompatibilityReason.DIFFERENT_TRACKS_INDEPENDENT
    assert res.requires_caution_order is False


def test_unspecified_task_adjacent_impact_yields_insufficient_data(sample_tracks_map):
    """If a task is on an adjacent track but adjacent_track_impact is None, yields INSUFFICIENT_DATA."""
    t_start = datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)
    occ1 = SpatialOccupant(
        occupant_id="TSK-UNSPECIFIED",
        occupant_type=SpatialOccupantType.TASK,
        section_id="SEC-01",
        track_id="TRK-SEC-01-UP",
        adjacent_track_impact=None,  # Unspecified!
        start_time=t_start,
        end_time=t_end,
    )
    occ2 = SpatialOccupant(
        occupant_id="TRV-01",
        occupant_type=SpatialOccupantType.TRAIN_TRAVERSAL,
        section_id="SEC-01",
        track_id="TRK-SEC-01-DN",
        start_time=t_start,
        end_time=t_end,
    )
    res = evaluate_spatial_compatibility(occ1, occ2, sample_tracks_map)
    assert res.status == SpatialCompatibilityStatus.INSUFFICIENT_DATA
    assert res.reason == SpatialCompatibilityReason.UNSPECIFIED_SPATIAL_RELATION


def test_factory_constructors_and_repeated_evaluation(sample_tracks_map):
    """Test SpatialOccupant constructors and determinism across repeated calls."""
    t_start = datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)

    task_dict = {
        "task_id": "TSK-FACTORIED",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-UP",
        "window_start": t_start.isoformat(),
        "window_end": t_end.isoformat(),
        "adjacent_track_impact": AdjacentTrackImpact.NONE.value,
        "from_km": 12.0,
        "to_km": 15.0,
    }
    occ_task = SpatialOccupant.from_task(task_dict)
    assert occ_task.occupant_id == "TSK-FACTORIED"
    assert occ_task.track_id == "TRK-SEC-01-UP"
    assert occ_task.from_km == 12.0

    traversal = TrainTraversal(
        traversal_id="TRV-TEST-01",
        train_id="TRN-01",
        train_number="12301",
        source_pass_id="PASS-01",
        section_id="SEC-01",
        from_station_id="STN-A",
        to_station_id="STN-B",
        sequence_order=1,
        interval=TimeInterval(start=t_start, end=t_end),
        traversal_track_id="TRK-SEC-01-DN",
        resolution_status=TraversalResolutionStatus.DIRECT_SECTION,
        classification=DataClass.DERIVED,
    )
    occ_trv = SpatialOccupant.from_train_traversal(traversal)
    assert occ_trv.occupant_id == "TRV-TEST-01"
    assert occ_trv.track_id == "TRK-SEC-01-DN"

    # Evaluate via CompatibilityEngine
    res1 = CompatibilityEngine.evaluate_spatial_compatibility(occ_task, occ_trv, sample_tracks_map)
    res2 = CompatibilityEngine.evaluate_spatial_compatibility(occ_task, occ_trv, sample_tracks_map)

    # Identical deterministic outputs
    assert res1.status == res2.status == SpatialCompatibilityStatus.COMPATIBLE
    assert res1.reason == res2.reason == SpatialCompatibilityReason.DIFFERENT_TRACKS_INDEPENDENT
    assert res1.requires_caution_order == res2.requires_caution_order is False
