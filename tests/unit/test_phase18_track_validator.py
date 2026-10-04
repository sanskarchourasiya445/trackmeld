"""Unit tests for Phase 18: Track-Aware Validator Verification.

Verifies:
1. Same-track conflict between task and train traversal (SAME_TRACK_OVERLAP -> ERROR)
2. Same-track conflict between two scheduled tasks (SAME_TRACK_OVERLAP -> ERROR)
3. Different-track independent movement (track compatible, section-level TRAIN_MOVEMENT_CONFLICT preserved)
4. Adjacent-track full traffic block (ADJACENT_TRACK_FULL_BLOCK -> ERROR)
5. Adjacent-track caution requirement (ADJACENT_TRACK_CAUTION_REQUIRED -> INFO)
6. Direction conflict on train traversal (TRACK_DIRECTION_CONFLICT -> ERROR)
7. Invalid track assignment: unknown track (INVALID_TRACK_ASSIGNMENT -> ERROR)
8. Invalid track assignment: track from wrong section (INVALID_TRACK_ASSIGNMENT -> ERROR)
9. Unresolved/ambiguous physical route without track (SPATIAL_METADATA_INCOMPLETE -> INFO)
10. Unresolved route with fabricated track assignment (INVALID_TRACK_ASSIGNMENT -> ERROR)
11. Missing/incomplete spatial metadata (SPATIAL_METADATA_INCOMPLETE -> INFO)
12. Duplicate finding suppression: identical pairs do not duplicate findings
13. Determinism & permutation invariance: shuffled input produces identical findings
14. Strict Architectural Independence: Validator does NOT call CompatibilityEngine, DeterministicTopologyRouter, or CP-SAT
"""

import random
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import pytest

from backend.app.domain.enums import (
    AdjacentTrackImpact,
    DataClass,
    TraversalResolutionStatus,
)
from backend.app.domain.movements import TrainMovement
from backend.app.domain.planning_snapshot import PlanningSnapshot
from backend.app.domain.scheduling import (
    ScheduleMetrics,
    ScheduleResult,
    ScheduledTaskResult,
    SchedulerStatus,
    SchedulerType,
)
from backend.app.domain.sections import Section, Track, TrackDirection
from backend.app.domain.temporal import (
    PlanningHorizon,
    TimeInterval,
    TrainPass,
    TrainTraversal,
)
from backend.app.services.compatibility_service import CompatibilityEngine
from backend.app.services.optimization.cp_sat_solver import CPSATSolver
from backend.app.services.topology_routing import DeterministicTopologyRouter
from backend.app.services.validation.models import (
    ValidationCategory,
    ValidationSeverity,
    ValidationStatus,
)
from backend.app.services.validation.validator import IndependentScheduleValidator


@pytest.fixture
def horizon():
    start = datetime(2026, 10, 15, 0, 0, tzinfo=timezone.utc)
    return PlanningHorizon(start=start, end=start + timedelta(hours=24))


@pytest.fixture
def sample_sections():
    return {
        "SEC-01": Section(
            section_id="SEC-01",
            section_code="STA-STB",
            from_station_id="STN-A",
            to_station_id="STN-B",
            from_station_name="Station A",
            to_station_name="Station B",
            from_station_code="STA",
            to_station_code="STB",
            division="D1",
            zone="NR",
            kilometrage_start=0.0,
            kilometrage_end=50.0,
            length_km=50.0,
            track_count=2,
            electrified=True,
        ),
        "SEC-02": Section(
            section_id="SEC-02",
            section_code="STB-STC",
            from_station_id="STN-B",
            to_station_id="STN-C",
            from_station_name="Station B",
            to_station_name="Station C",
            from_station_code="STB",
            to_station_code="STC",
            division="D1",
            zone="NR",
            kilometrage_start=50.0,
            kilometrage_end=100.0,
            length_km=50.0,
            track_count=2,
            electrified=True,
        ),
    }


@pytest.fixture
def sample_tracks():
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
            adjacent_track_ids=[],  # Explicitly non-adjacent/isolated
        ),
        "TRK-SEC-02-UP": Track(
            track_id="TRK-SEC-02-UP",
            section_id="SEC-02",
            track_code="UP_MAIN",
            direction=TrackDirection.UP,
            electrified=True,
            max_speed_kmh=130,
            adjacent_track_ids=[],
        ),
    }


def _make_snapshot(horizon, tasks, tracks, sections=None, train_passes=None, train_traversals=None, train_movements=None):
    sec_map = sections or {}
    return PlanningSnapshot(
        scenario_id="SCN-PHASE18-VAL",
        snapshot_id="SNAP-PHASE18-001",
        horizon=horizon,
        tasks=tasks,
        tasks_map={t["task_id"]: t for t in tasks},
        work_orders_map={},
        resources=[],
        resources_map={},
        resource_availabilities=[],
        dependencies=[],
        dependencies_by_successor={},
        dependencies_by_predecessor={},
        sections_map=sec_map,
        rules_map={},
        train_passes=train_passes or [],
        tracks=list(tracks.values()),
        tracks_map=tracks,
        train_movements=train_movements or [],
        train_movements_map={m.movement_id: m for m in (train_movements or [])},
        train_traversals=train_traversals or [],
        train_traversals_map={trv.traversal_id: trv for trv in (train_traversals or [])},
    )


def _make_scheduled_task(task_id, start_dt, end_dt, task_code="TC-01", sequence_order=1):
    dur = (end_dt - start_dt).total_seconds() / 60.0
    return ScheduledTaskResult(
        task_id=task_id,
        task_code=task_code,
        interval=TimeInterval(start=start_dt + timedelta(minutes=10), end=end_dt - timedelta(minutes=10)),
        possession_interval=TimeInterval(start=start_dt, end=end_dt),
        duration_minutes=dur - 20.0,
        assigned_resources=[],
        affected_sections=["SEC-01"],
        priority_score=10.0,
        sequence_order=sequence_order,
    )


def _make_schedule(snapshot, scheduled_tasks, status=SchedulerStatus.OPTIMAL):
    total_dur = sum(t.duration_minutes for t in scheduled_tasks)
    total_pos = sum(t.possession_interval.duration_minutes for t in scheduled_tasks)
    return ScheduleResult(
        schedule_id="SCHED-PHASE18-01",
        scheduler_type=SchedulerType.CP_SAT,
        scheduler_version="1.0.0",
        scenario_id=snapshot.scenario_id,
        snapshot_id=snapshot.snapshot_id,
        planning_start=snapshot.horizon.start,
        planning_end=snapshot.horizon.end,
        status=status,
        scheduled_tasks=scheduled_tasks,
        unscheduled_tasks=[],
        metrics=ScheduleMetrics(
            total_tasks=len(snapshot.tasks),
            scheduled_tasks=len(scheduled_tasks),
            unscheduled_tasks=0,
            completion_rate=1.0,
            mandatory_tasks=0,
            mandatory_scheduled=0,
            mandatory_unscheduled=0,
            mandatory_completion_rate=1.0,
            total_scheduled_duration_minutes=total_dur,
            total_possession_duration_minutes=total_pos,
            total_priority_score_available=100.0,
            scheduled_priority_score=100.0,
            unscheduled_priority_score=0.0,
            priority_score_capture_rate=1.0,
        ),
        configuration={},
        execution_time_ms=10.0,
    )


# -----------------------------------------------------------------------------
# Test 1: Same-track conflict between task and train traversal
# -----------------------------------------------------------------------------
def test_same_track_conflict_task_and_train_traversal(horizon, sample_sections, sample_tracks):
    t1 = {
        "task_id": "TSK-01",
        "task_code": "TC-01",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-DN",
        "adjacent_track_impact": AdjacentTrackImpact.NONE.value,
        "window_start": horizon.start + timedelta(hours=2),
        "window_end": horizon.start + timedelta(hours=6),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }
    # Train traversal on SAME track TRK-SEC-01-DN
    trv = TrainTraversal(
        traversal_id="TRV-01",
        train_id="TRN-01",
        train_number="12301",
        source_pass_id="PASS-01",
        section_id="SEC-01",
        from_station_id="STN-A",
        to_station_id="STN-B",
        sequence_order=1,
        interval=TimeInterval(start=horizon.start + timedelta(hours=3), end=horizon.start + timedelta(hours=4)),
        traversal_track_id="TRK-SEC-01-DN",
        resolution_status=TraversalResolutionStatus.DIRECT_SECTION,
        classification=DataClass.DERIVED,
    )
    # Also include the train pass so whole-section check runs
    tp = TrainPass(
        pass_id="PASS-01",
        train_id="TRN-01",
        train_number="12301",
        section_id="SEC-01",
        from_station_id="STN-A",
        to_station_id="STN-B",
        interval=trv.interval,
    )

    snapshot = _make_snapshot(
        horizon,
        [t1],
        sample_tracks,
        sections=sample_sections,
        train_passes=[tp],
        train_traversals=[trv],
    )
    st1 = _make_scheduled_task(
        task_id="TSK-01",
        start_dt=horizon.start + timedelta(hours=2, minutes=30),
        end_dt=horizon.start + timedelta(hours=4, minutes=30),
    )
    schedule = _make_schedule(snapshot, [st1])
    result = IndependentScheduleValidator.validate(snapshot, schedule)

    # Must contain both SAME_TRACK_OVERLAP (track level) and TRAIN_MOVEMENT_CONFLICT (section level)
    error_codes = [f.code for f in result.findings if f.severity == ValidationSeverity.ERROR]
    assert "SAME_TRACK_OVERLAP" in error_codes
    assert "TRAIN_MOVEMENT_CONFLICT" in error_codes
    assert result.valid is False
    assert result.is_approvable is False


# -----------------------------------------------------------------------------
# Test 2: Same-track conflict between two scheduled tasks
# -----------------------------------------------------------------------------
def test_same_track_conflict_two_tasks(horizon, sample_sections, sample_tracks):
    t1 = {
        "task_id": "TSK-01",
        "task_code": "TC-01",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-UP",
        "adjacent_track_impact": AdjacentTrackImpact.NONE.value,
        "window_start": horizon.start + timedelta(hours=2),
        "window_end": horizon.start + timedelta(hours=6),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }
    t2 = {
        "task_id": "TSK-02",
        "task_code": "TC-02",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-UP",  # Same track!
        "adjacent_track_impact": AdjacentTrackImpact.NONE.value,
        "window_start": horizon.start + timedelta(hours=2),
        "window_end": horizon.start + timedelta(hours=6),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }
    snapshot = _make_snapshot(horizon, [t1, t2], sample_tracks, sections=sample_sections)
    st1 = _make_scheduled_task(
        task_id="TSK-01",
        start_dt=horizon.start + timedelta(hours=2),
        end_dt=horizon.start + timedelta(hours=4),
        sequence_order=1,
    )
    st2 = _make_scheduled_task(
        task_id="TSK-02",
        start_dt=horizon.start + timedelta(hours=3),
        end_dt=horizon.start + timedelta(hours=5),
        sequence_order=2,
    )
    schedule = _make_schedule(snapshot, [st1, st2])
    result = IndependentScheduleValidator.validate(snapshot, schedule)

    error_codes = [f.code for f in result.findings if f.severity == ValidationSeverity.ERROR]
    assert "SAME_TRACK_OVERLAP" in error_codes
    assert "SECTION_OCCUPANCY_CONFLICT" in error_codes
    assert result.valid is False


# -----------------------------------------------------------------------------
# Test 3: Different-track independent movement (track level compatible)
# -----------------------------------------------------------------------------
def test_different_track_independent_movement(horizon, sample_sections, sample_tracks):
    # Task on UP track, train on DOWN track with NONE impact
    t1 = {
        "task_id": "TSK-01",
        "task_code": "TC-01",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-UP",
        "adjacent_track_impact": AdjacentTrackImpact.NONE.value,
        "window_start": horizon.start + timedelta(hours=2),
        "window_end": horizon.start + timedelta(hours=6),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }
    trv = TrainTraversal(
        traversal_id="TRV-01",
        train_id="TRN-01",
        train_number="12301",
        source_pass_id="PASS-01",
        section_id="SEC-01",
        from_station_id="STN-A",
        to_station_id="STN-B",
        sequence_order=1,
        interval=TimeInterval(start=horizon.start + timedelta(hours=3), end=horizon.start + timedelta(hours=4)),
        traversal_track_id="TRK-SEC-01-DN",  # Different track!
        resolution_status=TraversalResolutionStatus.DIRECT_SECTION,
        classification=DataClass.DERIVED,
    )
    tp = TrainPass(
        pass_id="PASS-01",
        train_id="TRN-01",
        train_number="12301",
        section_id="SEC-01",
        from_station_id="STN-A",
        to_station_id="STN-B",
        interval=trv.interval,
    )
    snapshot = _make_snapshot(
        horizon,
        [t1],
        sample_tracks,
        sections=sample_sections,
        train_passes=[tp],
        train_traversals=[trv],
    )
    st1 = _make_scheduled_task(
        task_id="TSK-01",
        start_dt=horizon.start + timedelta(hours=2, minutes=30),
        end_dt=horizon.start + timedelta(hours=4, minutes=30),
    )
    schedule = _make_schedule(snapshot, [st1])
    result = IndependentScheduleValidator.validate(snapshot, schedule)

    # Track-level check: NO track errors!
    track_errors = [f for f in result.findings if f.category == ValidationCategory.TRACK and f.severity == ValidationSeverity.ERROR]
    assert len(track_errors) == 0

    # Section-level check: TRAIN_MOVEMENT_CONFLICT is still preserved!
    assert any(f.code == "TRAIN_MOVEMENT_CONFLICT" for f in result.findings)
    assert result.valid is False


# -----------------------------------------------------------------------------
# Test 4: Adjacent-track full traffic block between task and train traversal
# -----------------------------------------------------------------------------
def test_adjacent_track_full_traffic_block(horizon, sample_sections, sample_tracks):
    t1 = {
        "task_id": "TSK-01",
        "task_code": "TC-01",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-UP",
        "adjacent_track_impact": AdjacentTrackImpact.FULL_TRAFFIC_BLOCK.value,  # Full block!
        "window_start": horizon.start + timedelta(hours=2),
        "window_end": horizon.start + timedelta(hours=6),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }
    trv = TrainTraversal(
        traversal_id="TRV-01",
        train_id="TRN-01",
        train_number="12301",
        source_pass_id="PASS-01",
        section_id="SEC-01",
        from_station_id="STN-A",
        to_station_id="STN-B",
        sequence_order=1,
        interval=TimeInterval(start=horizon.start + timedelta(hours=3), end=horizon.start + timedelta(hours=4)),
        traversal_track_id="TRK-SEC-01-DN",  # Adjacent track
        resolution_status=TraversalResolutionStatus.DIRECT_SECTION,
        classification=DataClass.DERIVED,
    )
    tp = TrainPass(
        pass_id="PASS-01",
        train_id="TRN-01",
        train_number="12301",
        section_id="SEC-01",
        from_station_id="STN-A",
        to_station_id="STN-B",
        interval=trv.interval,
    )
    snapshot = _make_snapshot(
        horizon,
        [t1],
        sample_tracks,
        sections=sample_sections,
        train_passes=[tp],
        train_traversals=[trv],
    )
    st1 = _make_scheduled_task(
        task_id="TSK-01",
        start_dt=horizon.start + timedelta(hours=2, minutes=30),
        end_dt=horizon.start + timedelta(hours=4, minutes=30),
    )
    schedule = _make_schedule(snapshot, [st1])
    result = IndependentScheduleValidator.validate(snapshot, schedule)

    track_errors = [f.code for f in result.findings if f.category == ValidationCategory.TRACK and f.severity == ValidationSeverity.ERROR]
    assert "ADJACENT_TRACK_FULL_BLOCK" in track_errors


# -----------------------------------------------------------------------------
# Test 5: Adjacent-track caution requirement between task and train traversal
# -----------------------------------------------------------------------------
def test_adjacent_track_caution_order_required(horizon, sample_sections, sample_tracks):
    t1 = {
        "task_id": "TSK-01",
        "task_code": "TC-01",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-UP",
        "adjacent_track_impact": AdjacentTrackImpact.CAUTION_ORDER.value,  # Caution Order!
        "window_start": horizon.start + timedelta(hours=2),
        "window_end": horizon.start + timedelta(hours=6),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }
    trv = TrainTraversal(
        traversal_id="TRV-01",
        train_id="TRN-01",
        train_number="12301",
        source_pass_id="PASS-01",
        section_id="SEC-01",
        from_station_id="STN-A",
        to_station_id="STN-B",
        sequence_order=1,
        interval=TimeInterval(start=horizon.start + timedelta(hours=3), end=horizon.start + timedelta(hours=4)),
        traversal_track_id="TRK-SEC-01-DN",  # Adjacent track
        resolution_status=TraversalResolutionStatus.DIRECT_SECTION,
        classification=DataClass.DERIVED,
    )
    snapshot = _make_snapshot(
        horizon,
        [t1],
        sample_tracks,
        sections=sample_sections,
        train_passes=[],
        train_traversals=[trv],
    )
    st1 = _make_scheduled_task(
        task_id="TSK-01",
        start_dt=horizon.start + timedelta(hours=2, minutes=30),
        end_dt=horizon.start + timedelta(hours=4, minutes=30),
    )
    schedule = _make_schedule(snapshot, [st1])
    result = IndependentScheduleValidator.validate(snapshot, schedule)

    # Must contain ADJACENT_TRACK_CAUTION_REQUIRED with severity INFO
    caution_findings = [f for f in result.findings if f.code == "ADJACENT_TRACK_CAUTION_REQUIRED"]
    assert len(caution_findings) == 1
    assert caution_findings[0].severity == ValidationSeverity.INFO
    assert caution_findings[0].category == ValidationCategory.TRACK


# -----------------------------------------------------------------------------
# Test 6: Direction conflict on train traversal
# -----------------------------------------------------------------------------
def test_direction_conflict_on_train_traversal(horizon, sample_sections, sample_tracks):
    # Train moving from STN-B to STN-A is travel direction "UP"
    # Assigned track is TRK-SEC-01-DN which has direction "DOWN"
    trv = TrainTraversal(
        traversal_id="TRV-01",
        train_id="TRN-01",
        train_number="12302",
        source_pass_id="PASS-01",
        section_id="SEC-01",
        from_station_id="STN-B",
        to_station_id="STN-A",
        sequence_order=1,
        interval=TimeInterval(start=horizon.start + timedelta(hours=3), end=horizon.start + timedelta(hours=4)),
        traversal_track_id="TRK-SEC-01-DN",  # Direction conflict!
        resolution_status=TraversalResolutionStatus.DIRECT_SECTION,
        classification=DataClass.DERIVED,
    )
    snapshot = _make_snapshot(horizon, [], sample_tracks, sections=sample_sections, train_traversals=[trv])
    schedule = _make_schedule(snapshot, [])
    result = IndependentScheduleValidator.validate(snapshot, schedule)

    dir_findings = [f for f in result.findings if f.code == "TRACK_DIRECTION_CONFLICT"]
    assert len(dir_findings) == 1
    assert dir_findings[0].severity == ValidationSeverity.ERROR
    assert dir_findings[0].category == ValidationCategory.TRACK


# -----------------------------------------------------------------------------
# Test 7: Invalid track assignment (unknown track)
# -----------------------------------------------------------------------------
def test_invalid_track_assignment_unknown_track(horizon, sample_sections, sample_tracks):
    trv = TrainTraversal(
        traversal_id="TRV-01",
        train_id="TRN-01",
        train_number="12301",
        source_pass_id="PASS-01",
        section_id="SEC-01",
        from_station_id="STN-A",
        to_station_id="STN-B",
        sequence_order=1,
        interval=TimeInterval(start=horizon.start + timedelta(hours=3), end=horizon.start + timedelta(hours=4)),
        traversal_track_id="TRK-GHOST-999",  # Unknown track!
        resolution_status=TraversalResolutionStatus.DIRECT_SECTION,
        classification=DataClass.DERIVED,
    )
    snapshot = _make_snapshot(horizon, [], sample_tracks, sections=sample_sections, train_traversals=[trv])
    schedule = _make_schedule(snapshot, [])
    result = IndependentScheduleValidator.validate(snapshot, schedule)

    inv_findings = [f for f in result.findings if f.code == "INVALID_TRACK_ASSIGNMENT"]
    assert len(inv_findings) == 1
    assert inv_findings[0].severity == ValidationSeverity.ERROR
    assert inv_findings[0].category == ValidationCategory.TRACK


# -----------------------------------------------------------------------------
# Test 8: Invalid track assignment (track from wrong section)
# -----------------------------------------------------------------------------
def test_invalid_track_assignment_wrong_section(horizon, sample_sections, sample_tracks):
    # Traversal in SEC-01 assigned TRK-SEC-02-UP which belongs to SEC-02!
    trv = TrainTraversal(
        traversal_id="TRV-01",
        train_id="TRN-01",
        train_number="12301",
        source_pass_id="PASS-01",
        section_id="SEC-01",
        from_station_id="STN-A",
        to_station_id="STN-B",
        sequence_order=1,
        interval=TimeInterval(start=horizon.start + timedelta(hours=3), end=horizon.start + timedelta(hours=4)),
        traversal_track_id="TRK-SEC-02-UP",  # Wrong section!
        resolution_status=TraversalResolutionStatus.DIRECT_SECTION,
        classification=DataClass.DERIVED,
    )
    snapshot = _make_snapshot(horizon, [], sample_tracks, sections=sample_sections, train_traversals=[trv])
    schedule = _make_schedule(snapshot, [])
    result = IndependentScheduleValidator.validate(snapshot, schedule)

    inv_findings = [f for f in result.findings if f.code == "INVALID_TRACK_ASSIGNMENT"]
    assert len(inv_findings) == 1
    assert inv_findings[0].severity == ValidationSeverity.ERROR
    assert "belonging to section 'SEC-02'" in inv_findings[0].message


# -----------------------------------------------------------------------------
# Test 9: Unresolved / ambiguous physical route without track
# -----------------------------------------------------------------------------
def test_unresolved_route_emits_info_diagnostic(horizon, sample_sections, sample_tracks):
    trv = TrainTraversal(
        traversal_id="TRV-01",
        train_id="TRN-01",
        train_number="12301",
        source_pass_id="PASS-01",
        section_id="SEC-01",
        from_station_id="STN-A",
        to_station_id="STN-B",
        sequence_order=1,
        interval=TimeInterval(start=horizon.start + timedelta(hours=3), end=horizon.start + timedelta(hours=4)),
        traversal_track_id=None,  # No track
        resolution_status=TraversalResolutionStatus.AMBIGUOUS_ROUTE,
        unresolved_reason="AMBIGUOUS_ROUTE: Multiple candidate routes found",
        classification=DataClass.DERIVED,
    )
    snapshot = _make_snapshot(horizon, [], sample_tracks, sections=sample_sections, train_traversals=[trv])
    schedule = _make_schedule(snapshot, [])
    result = IndependentScheduleValidator.validate(snapshot, schedule)

    info_findings = [f for f in result.findings if f.code == "SPATIAL_METADATA_INCOMPLETE" and f.severity == ValidationSeverity.INFO]
    assert len(info_findings) == 1
    assert "AMBIGUOUS_ROUTE" in info_findings[0].message
    assert result.error_count == 0


# -----------------------------------------------------------------------------
# Test 10: Unresolved route with fabricated track assignment
# -----------------------------------------------------------------------------
def test_unresolved_route_with_fabricated_track_is_error(horizon, sample_sections, sample_tracks):
    trv = TrainTraversal(
        traversal_id="TRV-01",
        train_id="TRN-01",
        train_number="12301",
        source_pass_id="PASS-01",
        section_id="SEC-01",
        from_station_id="STN-A",
        to_station_id="STN-B",
        sequence_order=1,
        interval=TimeInterval(start=horizon.start + timedelta(hours=3), end=horizon.start + timedelta(hours=4)),
        traversal_track_id="TRK-SEC-01-DN",  # Fabricated track for unresolved route!
        resolution_status=TraversalResolutionStatus.UNRESOLVED,
        unresolved_reason="Topology disconnected",
        classification=DataClass.DERIVED,
    )
    snapshot = _make_snapshot(horizon, [], sample_tracks, sections=sample_sections, train_traversals=[trv])
    schedule = _make_schedule(snapshot, [])
    result = IndependentScheduleValidator.validate(snapshot, schedule)

    errs = [f for f in result.findings if f.code == "INVALID_TRACK_ASSIGNMENT" and f.severity == ValidationSeverity.ERROR]
    assert len(errs) >= 1
    assert "unresolved routes must not fabricate track assignments" in errs[0].message


# -----------------------------------------------------------------------------
# Test 11: Missing/incomplete spatial metadata on task
# -----------------------------------------------------------------------------
def test_missing_spatial_metadata_emits_info(horizon, sample_sections, sample_tracks):
    # Two tasks on adjacent tracks, but t1 has null adjacent_track_impact
    t1 = {
        "task_id": "TSK-01",
        "task_code": "TC-01",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-UP",
        "adjacent_track_impact": None,  # Unspecified impact
        "window_start": horizon.start + timedelta(hours=2),
        "window_end": horizon.start + timedelta(hours=6),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }
    t2 = {
        "task_id": "TSK-02",
        "task_code": "TC-02",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-DN",
        "adjacent_track_impact": AdjacentTrackImpact.NONE.value,
        "window_start": horizon.start + timedelta(hours=2),
        "window_end": horizon.start + timedelta(hours=6),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }
    snapshot = _make_snapshot(horizon, [t1, t2], sample_tracks, sections=sample_sections)
    st1 = _make_scheduled_task(
        task_id="TSK-01",
        start_dt=horizon.start + timedelta(hours=2),
        end_dt=horizon.start + timedelta(hours=4),
        sequence_order=1,
    )
    st2 = _make_scheduled_task(
        task_id="TSK-02",
        start_dt=horizon.start + timedelta(hours=3),
        end_dt=horizon.start + timedelta(hours=5),
        sequence_order=2,
    )
    schedule = _make_schedule(snapshot, [st1, st2])
    result = IndependentScheduleValidator.validate(snapshot, schedule)

    incomplete = [f for f in result.findings if f.code == "SPATIAL_METADATA_INCOMPLETE"]
    assert len(incomplete) == 1
    assert incomplete[0].severity == ValidationSeverity.INFO


# -----------------------------------------------------------------------------
# Test 12: Duplicate finding suppression
# -----------------------------------------------------------------------------
def test_duplicate_finding_suppression(horizon, sample_sections, sample_tracks):
    t1 = {
        "task_id": "TSK-01",
        "task_code": "TC-01",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-UP",
        "adjacent_track_impact": AdjacentTrackImpact.FULL_TRAFFIC_BLOCK.value,
        "window_start": horizon.start + timedelta(hours=2),
        "window_end": horizon.start + timedelta(hours=6),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }
    t2 = {
        "task_id": "TSK-02",
        "task_code": "TC-02",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-DN",
        "adjacent_track_impact": AdjacentTrackImpact.NONE.value,
        "window_start": horizon.start + timedelta(hours=2),
        "window_end": horizon.start + timedelta(hours=6),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }
    snapshot = _make_snapshot(horizon, [t1, t2], sample_tracks, sections=sample_sections)
    st1 = _make_scheduled_task(
        task_id="TSK-01",
        start_dt=horizon.start + timedelta(hours=2),
        end_dt=horizon.start + timedelta(hours=4),
        sequence_order=1,
    )
    st2 = _make_scheduled_task(
        task_id="TSK-02",
        start_dt=horizon.start + timedelta(hours=3),
        end_dt=horizon.start + timedelta(hours=5),
        sequence_order=2,
    )
    schedule = _make_schedule(snapshot, [st1, st2])
    result = IndependentScheduleValidator.validate(snapshot, schedule)

    # Count ADJACENT_TRACK_FULL_BLOCK: exactly 1 finding
    block_findings = [f for f in result.findings if f.code == "ADJACENT_TRACK_FULL_BLOCK"]
    assert len(block_findings) == 1


# -----------------------------------------------------------------------------
# Test 13: Determinism & Permutation Invariance
# -----------------------------------------------------------------------------
def test_determinism_and_permutation_invariance(horizon, sample_sections, sample_tracks):
    t1 = {
        "task_id": "TSK-01",
        "task_code": "TC-01",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-UP",
        "adjacent_track_impact": AdjacentTrackImpact.FULL_TRAFFIC_BLOCK.value,
        "window_start": horizon.start + timedelta(hours=2),
        "window_end": horizon.start + timedelta(hours=6),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }
    t2 = {
        "task_id": "TSK-02",
        "task_code": "TC-02",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-DN",
        "adjacent_track_impact": AdjacentTrackImpact.CAUTION_ORDER.value,
        "window_start": horizon.start + timedelta(hours=2),
        "window_end": horizon.start + timedelta(hours=6),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }
    trv = TrainTraversal(
        traversal_id="TRV-01",
        train_id="TRN-01",
        train_number="12301",
        source_pass_id="PASS-01",
        section_id="SEC-01",
        from_station_id="STN-A",
        to_station_id="STN-B",
        sequence_order=1,
        interval=TimeInterval(start=horizon.start + timedelta(hours=3), end=horizon.start + timedelta(hours=4)),
        traversal_track_id="TRK-SEC-01-DN",
        resolution_status=TraversalResolutionStatus.DIRECT_SECTION,
        classification=DataClass.DERIVED,
    )

    st1 = _make_scheduled_task(task_id="TSK-01", start_dt=horizon.start + timedelta(hours=2), end_dt=horizon.start + timedelta(hours=4))
    st2 = _make_scheduled_task(task_id="TSK-02", start_dt=horizon.start + timedelta(hours=3), end_dt=horizon.start + timedelta(hours=5))

    # Run 1: original order
    snap1 = _make_snapshot(horizon, [t1, t2], sample_tracks, sections=sample_sections, train_traversals=[trv])
    sched1 = _make_schedule(snap1, [st1, st2])
    res1 = IndependentScheduleValidator.validate(snap1, sched1)

    # Run 2: reversed order
    snap2 = _make_snapshot(horizon, [t2, t1], sample_tracks, sections=sample_sections, train_traversals=[trv])
    sched2 = _make_schedule(snap2, [st2, st1])
    res2 = IndependentScheduleValidator.validate(snap2, sched2)

    assert len(res1.findings) == len(res2.findings)
    for f1, f2 in zip(res1.findings, res2.findings):
        assert f1.code == f2.code
        assert f1.severity == f2.severity
        assert f1.category == f2.category
        assert f1.task_id == f2.task_id
        assert f1.section_id == f2.section_id


# -----------------------------------------------------------------------------
# Test 14: Strict Architectural Independence
# -----------------------------------------------------------------------------
def test_strict_architectural_independence(horizon, sample_sections, sample_tracks):
    """Validator MUST NOT invoke CompatibilityEngine, DeterministicTopologyRouter, or CP-SAT."""
    t1 = {
        "task_id": "TSK-01",
        "task_code": "TC-01",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-UP",
        "adjacent_track_impact": AdjacentTrackImpact.NONE.value,
        "window_start": horizon.start + timedelta(hours=2),
        "window_end": horizon.start + timedelta(hours=6),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }
    snapshot = _make_snapshot(horizon, [t1], sample_tracks, sections=sample_sections)
    st1 = _make_scheduled_task(task_id="TSK-01", start_dt=horizon.start + timedelta(hours=2), end_dt=horizon.start + timedelta(hours=4))
    schedule = _make_schedule(snapshot, [st1])

    with patch.object(CompatibilityEngine, "evaluate_spatial_compatibility", side_effect=AssertionError("CompatibilityEngine called by validator")), \
         patch.object(CompatibilityEngine, "evaluate_task_placement", side_effect=AssertionError("CompatibilityEngine called by validator")), \
         patch.object(DeterministicTopologyRouter, "resolve_pass_route", side_effect=AssertionError("DeterministicTopologyRouter called by validator")), \
         patch.object(CPSATSolver, "solve", side_effect=AssertionError("CPSATSolver called by validator")):
        result = IndependentScheduleValidator.validate(snapshot, schedule)
        assert result.status is not None
