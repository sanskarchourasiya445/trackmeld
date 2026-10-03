"""Unit tests for Phase 16G-C: Track-Aware Validator Diagnostic & Safety Extension.

Verifies all 15 required validator test contracts:
1. invalid task track_id (ERROR)
2. invalid train movement track_id (ERROR)
3. valid track assignment (no track error)
4. deterministic supported direction conflict (ERROR)
5. FULL_TRAFFIC_BLOCK against explicitly adjacent track (ERROR)
6. FULL_TRAFFIC_BLOCK against non-adjacent track (no adjacent block error)
7. CAUTION_ORDER produces advisory/diagnostic only (INFO, not ERROR)
8. missing adjacency metadata (INFO, not ERROR)
9. unresolved traversal track (handled safely without fabrication)
10. no temporal overlap (zero spatial conflicts)
11. different tracks do NOT bypass section-level conflict (SECTION_OCCUPANCY_CONFLICT remains)
12. existing section occupancy conflict still blocks approval
13. existing train movement conflict still blocks approval
14. validator does not call CompatibilityEngine (architectural independence)
15. validator does not call CP-SAT solver (architectural independence)
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from backend.app.domain.temporal import PlanningHorizon, TimeInterval, TrainPass, TrainTraversal
from backend.app.domain.planning_snapshot import PlanningSnapshot
from backend.app.domain.sections import Track, TrackDirection
from backend.app.domain.enums import AdjacentTrackImpact, TraversalResolutionStatus, DataClass
from backend.app.domain.scheduling import (
    SchedulerType,
    SchedulerStatus,
    ScheduledTaskResult,
    ScheduleResult,
    ScheduleMetrics,
)
from backend.app.domain.movements import TrainMovement
from backend.app.services.validation.models import (
    ValidationStatus,
    ValidationSeverity,
    ValidationCategory,
)
from backend.app.services.validation.validator import IndependentScheduleValidator
from backend.app.services.compatibility_service import CompatibilityEngine
from backend.app.services.optimization.cp_sat_solver import CPSATSolver
from backend.app.services.optimization.cp_sat_model import CPSATModelBuilder


@pytest.fixture
def horizon():
    start = datetime(2026, 10, 15, 0, 0, tzinfo=timezone.utc)
    return PlanningHorizon(start=start, end=start + timedelta(hours=24))


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
            adjacent_track_ids=[],  # Explicitly isolated
        ),
        "TRK-SEC-01-UNSPEC": Track(
            track_id="TRK-SEC-01-UNSPEC",
            section_id="SEC-01",
            track_code="RELIEF",
            direction=TrackDirection.BIDIRECTIONAL,
            electrified=True,
            max_speed_kmh=80,
            adjacent_track_ids=None,  # Null adjacency
        ),
    }


def _make_snapshot(horizon, tasks, tracks, train_passes=None, train_movements=None, train_traversals=None):
    return PlanningSnapshot(
        scenario_id="SCN-TRACK-VAL",
        snapshot_id="SNAP-TRK-VAL-001",
        horizon=horizon,
        tasks=tasks,
        tasks_map={t["task_id"]: dict(t) for t in tasks},
        work_orders_map={},
        resources=[],
        resources_map={},
        resource_availabilities=[],
        dependencies=[],
        dependencies_by_successor={},
        dependencies_by_predecessor={},
        sections_map={
            "SEC-01": {"section_id": "SEC-01", "electrified": True},
        },
        rules_map={},
        train_passes=train_passes or [],
        tracks_map=tracks,
        train_movements=train_movements or [],
        train_traversals=train_traversals or [],
    )


def _make_scheduled_task(
    task_id: str,
    start_dt: datetime,
    end_dt: datetime,
    task_code: str = "TC-01",
    buffer_before: int = 10,
    buffer_after: int = 10,
    section_id: str = "SEC-01",
    sequence_order: int = 1,
) -> ScheduledTaskResult:
    dur = (end_dt - start_dt).total_seconds() / 60.0
    return ScheduledTaskResult(
        task_id=task_id,
        task_code=task_code,
        interval=TimeInterval(start=start_dt, end=end_dt),
        possession_interval=TimeInterval(
            start=start_dt - timedelta(minutes=buffer_before),
            end=end_dt + timedelta(minutes=buffer_after),
        ),
        duration_minutes=dur,
        affected_sections=[section_id],
        assigned_resources=[],
        sequence_order=sequence_order,
    )


def _make_schedule(snapshot, scheduled_tasks, status=SchedulerStatus.OPTIMAL):
    total_dur = sum(t.duration_minutes for t in scheduled_tasks)
    total_pos = sum(t.possession_interval.duration_minutes for t in scheduled_tasks)
    return ScheduleResult(
        schedule_id="SCHED-TRK-VAL-01",
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
# Test 1: Invalid task track_id produces ERROR
# -----------------------------------------------------------------------------
def test_invalid_task_track_id_produces_error(horizon, sample_tracks):
    t1 = {
        "task_id": "TSK-01",
        "task_code": "TC-01",
        "section_id": "SEC-01",
        "track_id": "TRK-NONEXISTENT",
        "window_start": horizon.start + timedelta(hours=2),
        "window_end": horizon.start + timedelta(hours=10),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }
    snapshot = _make_snapshot(horizon, [t1], sample_tracks)

    st1 = _make_scheduled_task(
        task_id="TSK-01",
        start_dt=horizon.start + timedelta(hours=3),
        end_dt=horizon.start + timedelta(hours=5),
    )
    schedule = _make_schedule(snapshot, [st1])
    result = IndependentScheduleValidator.validate(snapshot, schedule)

    assert result.valid is False
    assert result.is_approvable is False
    error_codes = [f.code for f in result.findings if f.severity == ValidationSeverity.ERROR]
    assert "INVALID_TRACK_ASSIGNMENT" in error_codes


# -----------------------------------------------------------------------------
# Test 2: Invalid train movement track_id produces ERROR
# -----------------------------------------------------------------------------
def test_invalid_train_movement_track_id_produces_error(horizon, sample_tracks):
    t1 = {
        "task_id": "TSK-01",
        "task_code": "TC-01",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-UP",
        "window_start": horizon.start + timedelta(hours=2),
        "window_end": horizon.start + timedelta(hours=10),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }
    mov = TrainMovement(
        movement_id="MOV-01",
        train_id="TRN-01",
        train_number="12301",
        train_name="Rajdhani",
        station_id="STN-A",
        station_code="STA",
        station_name="Station A",
        stop_sequence=1,
        scheduled_departure="08:00",
        track_id="TRK-GHOST-LINE",  # Invalid
        movement_type="SCHEDULED_ORIGIN",
        source_id="SRC-01",
    )
    snapshot = _make_snapshot(horizon, [t1], sample_tracks, train_movements=[mov])

    st1 = _make_scheduled_task(
        task_id="TSK-01",
        start_dt=horizon.start + timedelta(hours=3),
        end_dt=horizon.start + timedelta(hours=5),
    )
    schedule = _make_schedule(snapshot, [st1])
    result = IndependentScheduleValidator.validate(snapshot, schedule)

    assert result.valid is False
    assert result.is_approvable is False
    error_codes = [f.code for f in result.findings if f.severity == ValidationSeverity.ERROR]
    assert "INVALID_TRACK_ASSIGNMENT" in error_codes


# -----------------------------------------------------------------------------
# Test 3: Valid track assignment generates no track errors
# -----------------------------------------------------------------------------
def test_valid_track_assignment_passes(horizon, sample_tracks):
    t1 = {
        "task_id": "TSK-01",
        "task_code": "TC-01",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-UP",
        "window_start": horizon.start + timedelta(hours=2),
        "window_end": horizon.start + timedelta(hours=10),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }
    snapshot = _make_snapshot(horizon, [t1], sample_tracks)

    st1 = _make_scheduled_task(
        task_id="TSK-01",
        start_dt=horizon.start + timedelta(hours=3),
        end_dt=horizon.start + timedelta(hours=5),
    )
    schedule = _make_schedule(snapshot, [st1])
    result = IndependentScheduleValidator.validate(snapshot, schedule)

    track_findings = [f for f in result.findings if f.category == ValidationCategory.TRACK]
    assert len(track_findings) == 0
    assert result.valid is True
    assert result.is_approvable is True


# -----------------------------------------------------------------------------
# Test 4: Deterministic supported direction conflict produces ERROR
# -----------------------------------------------------------------------------
def test_deterministic_direction_conflict_produces_error(horizon, sample_tracks):
    t1 = {
        "task_id": "TSK-01",
        "task_code": "TC-01",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-UP",  # Track is UP only
        "direction": "DOWN",          # Conflict!
        "window_start": horizon.start + timedelta(hours=2),
        "window_end": horizon.start + timedelta(hours=10),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }
    snapshot = _make_snapshot(horizon, [t1], sample_tracks)

    st1 = _make_scheduled_task(
        task_id="TSK-01",
        start_dt=horizon.start + timedelta(hours=3),
        end_dt=horizon.start + timedelta(hours=5),
    )
    schedule = _make_schedule(snapshot, [st1])
    result = IndependentScheduleValidator.validate(snapshot, schedule)

    assert result.valid is False
    assert result.is_approvable is False
    error_codes = [f.code for f in result.findings if f.severity == ValidationSeverity.ERROR]
    assert "TRACK_DIRECTION_CONFLICT" in error_codes


# -----------------------------------------------------------------------------
# Test 5: FULL_TRAFFIC_BLOCK against explicitly adjacent track produces ERROR
# -----------------------------------------------------------------------------
def test_full_traffic_block_against_adjacent_track_produces_error(horizon, sample_tracks):
    t1 = {
        "task_id": "TSK-01",
        "task_code": "TC-01",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-UP",
        "adjacent_track_impact": AdjacentTrackImpact.FULL_TRAFFIC_BLOCK.value,
        "window_start": horizon.start + timedelta(hours=2),
        "window_end": horizon.start + timedelta(hours=10),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }
    t2 = {
        "task_id": "TSK-02",
        "task_code": "TC-02",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-DN",  # Adjacent track!
        "adjacent_track_impact": AdjacentTrackImpact.NONE.value,
        "window_start": horizon.start + timedelta(hours=2),
        "window_end": horizon.start + timedelta(hours=10),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }
    snapshot = _make_snapshot(horizon, [t1, t2], sample_tracks)

    # Overlapping intervals
    st1 = _make_scheduled_task(
        task_id="TSK-01",
        task_code="TC-01",
        start_dt=horizon.start + timedelta(hours=3),
        end_dt=horizon.start + timedelta(hours=5),
        sequence_order=1,
    )
    st2 = _make_scheduled_task(
        task_id="TSK-02",
        task_code="TC-02",
        start_dt=horizon.start + timedelta(hours=4),
        end_dt=horizon.start + timedelta(hours=6),
        sequence_order=2,
    )
    schedule = _make_schedule(snapshot, [st1, st2])
    result = IndependentScheduleValidator.validate(snapshot, schedule)

    assert result.valid is False
    error_codes = [f.code for f in result.findings if f.severity == ValidationSeverity.ERROR]
    assert "ADJACENT_TRACK_FULL_BLOCK" in error_codes


# -----------------------------------------------------------------------------
# Test 6: FULL_TRAFFIC_BLOCK against non-adjacent track does NOT produce adjacent error
# -----------------------------------------------------------------------------
def test_full_traffic_block_against_non_adjacent_track_no_adjacent_error(horizon, sample_tracks):
    t1 = {
        "task_id": "TSK-01",
        "task_code": "TC-01",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-LOOP",  # Explicitly non-adjacent loop
        "adjacent_track_impact": AdjacentTrackImpact.FULL_TRAFFIC_BLOCK.value,
        "window_start": horizon.start + timedelta(hours=2),
        "window_end": horizon.start + timedelta(hours=10),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }
    t2 = {
        "task_id": "TSK-02",
        "task_code": "TC-02",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-UP",  # Non-adjacent to loop
        "adjacent_track_impact": AdjacentTrackImpact.NONE.value,
        "window_start": horizon.start + timedelta(hours=2),
        "window_end": horizon.start + timedelta(hours=10),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }
    snapshot = _make_snapshot(horizon, [t1, t2], sample_tracks)

    st1 = _make_scheduled_task(
        task_id="TSK-01",
        task_code="TC-01",
        start_dt=horizon.start + timedelta(hours=3),
        end_dt=horizon.start + timedelta(hours=5),
        sequence_order=1,
    )
    st2 = _make_scheduled_task(
        task_id="TSK-02",
        task_code="TC-02",
        start_dt=horizon.start + timedelta(hours=4),
        end_dt=horizon.start + timedelta(hours=6),
        sequence_order=2,
    )
    schedule = _make_schedule(snapshot, [st1, st2])
    result = IndependentScheduleValidator.validate(snapshot, schedule)

    # ADJACENT_TRACK_FULL_BLOCK should NOT be emitted because tracks are non-adjacent
    error_codes = [f.code for f in result.findings if f.severity == ValidationSeverity.ERROR]
    assert "ADJACENT_TRACK_FULL_BLOCK" not in error_codes


# -----------------------------------------------------------------------------
# Test 7: CAUTION_ORDER produces advisory/diagnostic only (INFO)
# -----------------------------------------------------------------------------
def test_caution_order_produces_info_only(horizon, sample_tracks):
    t1 = {
        "task_id": "TSK-01",
        "task_code": "TC-01",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-UP",
        "adjacent_track_impact": AdjacentTrackImpact.CAUTION_ORDER.value,
        "window_start": horizon.start + timedelta(hours=2),
        "window_end": horizon.start + timedelta(hours=10),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }
    t2 = {
        "task_id": "TSK-02",
        "task_code": "TC-02",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-DN",  # Adjacent track
        "adjacent_track_impact": AdjacentTrackImpact.NONE.value,
        "window_start": horizon.start + timedelta(hours=2),
        "window_end": horizon.start + timedelta(hours=10),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }
    snapshot = _make_snapshot(horizon, [t1, t2], sample_tracks)

    st1 = _make_scheduled_task(
        task_id="TSK-01",
        task_code="TC-01",
        start_dt=horizon.start + timedelta(hours=3),
        end_dt=horizon.start + timedelta(hours=5),
        sequence_order=1,
    )
    st2 = _make_scheduled_task(
        task_id="TSK-02",
        task_code="TC-02",
        start_dt=horizon.start + timedelta(hours=4),
        end_dt=horizon.start + timedelta(hours=6),
        sequence_order=2,
    )
    schedule = _make_schedule(snapshot, [st1, st2])
    result = IndependentScheduleValidator.validate(snapshot, schedule)

    # Check for INFO finding
    info_codes = [f.code for f in result.findings if f.severity == ValidationSeverity.INFO]
    assert "ADJACENT_TRACK_CAUTION_REQUIRED" in info_codes


# -----------------------------------------------------------------------------
# Test 8: Missing adjacency metadata emits SPATIAL_METADATA_INCOMPLETE (INFO)
# -----------------------------------------------------------------------------
def test_missing_adjacency_metadata_emits_info(horizon, sample_tracks):
    t1 = {
        "task_id": "TSK-01",
        "task_code": "TC-01",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-UNSPEC",  # Null adjacent_track_ids
        "adjacent_track_impact": AdjacentTrackImpact.NONE.value,
        "window_start": horizon.start + timedelta(hours=2),
        "window_end": horizon.start + timedelta(hours=10),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }
    t2 = {
        "task_id": "TSK-02",
        "task_code": "TC-02",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-UP",
        "adjacent_track_impact": AdjacentTrackImpact.NONE.value,
        "window_start": horizon.start + timedelta(hours=2),
        "window_end": horizon.start + timedelta(hours=10),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }
    snapshot = _make_snapshot(horizon, [t1, t2], sample_tracks)

    st1 = _make_scheduled_task(
        task_id="TSK-01",
        task_code="TC-01",
        start_dt=horizon.start + timedelta(hours=3),
        end_dt=horizon.start + timedelta(hours=5),
        sequence_order=1,
    )
    st2 = _make_scheduled_task(
        task_id="TSK-02",
        task_code="TC-02",
        start_dt=horizon.start + timedelta(hours=4),
        end_dt=horizon.start + timedelta(hours=6),
        sequence_order=2,
    )
    schedule = _make_schedule(snapshot, [st1, st2])
    result = IndependentScheduleValidator.validate(snapshot, schedule)

    info_codes = [f.code for f in result.findings if f.severity == ValidationSeverity.INFO]
    assert "SPATIAL_METADATA_INCOMPLETE" in info_codes


# -----------------------------------------------------------------------------
# Test 9: Unresolved traversal track handled safely without crash
# -----------------------------------------------------------------------------
def test_unresolved_traversal_track_handled_safely(horizon, sample_tracks):
    t1 = {
        "task_id": "TSK-01",
        "task_code": "TC-01",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-UP",
        "window_start": horizon.start + timedelta(hours=2),
        "window_end": horizon.start + timedelta(hours=10),
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
        from_station_id="STA",
        to_station_id="STB",
        sequence_order=1,
        interval=TimeInterval(start=horizon.start + timedelta(hours=3), end=horizon.start + timedelta(hours=4)),
        traversal_track_id=None,  # Deliberately unassigned
        resolution_status=TraversalResolutionStatus.DIRECT_SECTION,
        classification=DataClass.DERIVED,
    )
    snapshot = _make_snapshot(horizon, [t1], sample_tracks, train_traversals=[trv])

    st1 = _make_scheduled_task(
        task_id="TSK-01",
        start_dt=horizon.start + timedelta(hours=3),
        end_dt=horizon.start + timedelta(hours=5),
    )
    schedule = _make_schedule(snapshot, [st1])
    result = IndependentScheduleValidator.validate(snapshot, schedule)

    # Validates cleanly without throwing AttributeError or fabricating tracks
    assert "TRACK_SPATIAL_SAFETY" in result.checks_executed


# -----------------------------------------------------------------------------
# Test 10: No temporal overlap produces zero spatial conflicts
# -----------------------------------------------------------------------------
def test_no_temporal_overlap_zero_spatial_conflicts(horizon, sample_tracks):
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
        "adjacent_track_impact": AdjacentTrackImpact.FULL_TRAFFIC_BLOCK.value,
        "window_start": horizon.start + timedelta(hours=8),
        "window_end": horizon.start + timedelta(hours=14),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }
    snapshot = _make_snapshot(horizon, [t1, t2], sample_tracks)

    # Disjoint intervals: 03:00-05:00 and 09:00-11:00
    st1 = _make_scheduled_task(
        task_id="TSK-01",
        task_code="TC-01",
        start_dt=horizon.start + timedelta(hours=3),
        end_dt=horizon.start + timedelta(hours=5),
        sequence_order=1,
    )
    st2 = _make_scheduled_task(
        task_id="TSK-02",
        task_code="TC-02",
        start_dt=horizon.start + timedelta(hours=9),
        end_dt=horizon.start + timedelta(hours=11),
        sequence_order=2,
    )
    schedule = _make_schedule(snapshot, [st1, st2])
    result = IndependentScheduleValidator.validate(snapshot, schedule)

    track_findings = [f for f in result.findings if f.category == ValidationCategory.TRACK]
    assert len(track_findings) == 0
    assert result.valid is True
    assert result.is_approvable is True


# -----------------------------------------------------------------------------
# Test 11: Different tracks do NOT bypass existing section-level conflict
# -----------------------------------------------------------------------------
def test_different_tracks_do_not_bypass_section_occupancy_conflict(horizon, sample_tracks):
    """CRITICAL SAFETY TEST: Even if tasks are on different tracks with NONE impact,
    the whole-section occupancy check must STILL flag SECTION_OCCUPANCY_CONFLICT.
    """
    t1 = {
        "task_id": "TSK-01",
        "task_code": "TC-01",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-UP",
        "adjacent_track_impact": AdjacentTrackImpact.NONE.value,
        "window_start": horizon.start + timedelta(hours=2),
        "window_end": horizon.start + timedelta(hours=10),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }
    t2 = {
        "task_id": "TSK-02",
        "task_code": "TC-02",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-DN",  # Different track!
        "adjacent_track_impact": AdjacentTrackImpact.NONE.value,
        "window_start": horizon.start + timedelta(hours=2),
        "window_end": horizon.start + timedelta(hours=10),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }
    snapshot = _make_snapshot(horizon, [t1, t2], sample_tracks)

    st1 = _make_scheduled_task(
        task_id="TSK-01",
        task_code="TC-01",
        start_dt=horizon.start + timedelta(hours=3),
        end_dt=horizon.start + timedelta(hours=5),
        sequence_order=1,
    )
    st2 = _make_scheduled_task(
        task_id="TSK-02",
        task_code="TC-02",
        start_dt=horizon.start + timedelta(hours=4),
        end_dt=horizon.start + timedelta(hours=6),
        sequence_order=2,
    )
    schedule = _make_schedule(snapshot, [st1, st2])
    result = IndependentScheduleValidator.validate(snapshot, schedule)

    # Invariant: Section-level safety barrier is NOT bypassed!
    error_codes = [f.code for f in result.findings if f.severity == ValidationSeverity.ERROR]
    assert "SECTION_OCCUPANCY_CONFLICT" in error_codes


# -----------------------------------------------------------------------------
# Test 12: Section occupancy conflict still blocks approval
# -----------------------------------------------------------------------------
def test_section_occupancy_conflict_blocks_approval(horizon, sample_tracks):
    """Assert that when SECTION_OCCUPANCY_CONFLICT is present, valid is False and is_approvable is False."""
    t1 = {
        "task_id": "TSK-01",
        "task_code": "TC-01",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-UP",
        "adjacent_track_impact": AdjacentTrackImpact.NONE.value,
        "window_start": horizon.start + timedelta(hours=2),
        "window_end": horizon.start + timedelta(hours=10),
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
        "window_end": horizon.start + timedelta(hours=10),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }
    snapshot = _make_snapshot(horizon, [t1, t2], sample_tracks)

    st1 = _make_scheduled_task(
        task_id="TSK-01",
        task_code="TC-01",
        start_dt=horizon.start + timedelta(hours=3),
        end_dt=horizon.start + timedelta(hours=5),
        sequence_order=1,
    )
    st2 = _make_scheduled_task(
        task_id="TSK-02",
        task_code="TC-02",
        start_dt=horizon.start + timedelta(hours=4),
        end_dt=horizon.start + timedelta(hours=6),
        sequence_order=2,
    )
    schedule = _make_schedule(snapshot, [st1, st2])
    result = IndependentScheduleValidator.validate(snapshot, schedule)

    assert result.valid is False
    assert result.is_approvable is False


# -----------------------------------------------------------------------------
# Test 13: Existing train movement conflict still blocks approval
# -----------------------------------------------------------------------------
def test_existing_train_movement_conflict_still_blocks(horizon, sample_tracks):
    t1 = {
        "task_id": "TSK-01",
        "task_code": "TC-01",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-UP",
        "adjacent_track_impact": AdjacentTrackImpact.NONE.value,
        "window_start": horizon.start + timedelta(hours=2),
        "window_end": horizon.start + timedelta(hours=10),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }
    # Train pass on SEC-01 on different track TRK-SEC-01-DN
    tp = TrainPass(
        pass_id="PASS-01",
        train_id="TRN-01",
        train_number="12004",
        section_id="SEC-01",
        track_id="TRK-SEC-01-DN",
        interval=TimeInterval(start=horizon.start + timedelta(hours=3), end=horizon.start + timedelta(hours=5)),
    )
    snapshot = _make_snapshot(horizon, [t1], sample_tracks, train_passes=[tp])

    st1 = _make_scheduled_task(
        task_id="TSK-01",
        start_dt=horizon.start + timedelta(hours=3),
        end_dt=horizon.start + timedelta(hours=5),
    )
    schedule = _make_schedule(snapshot, [st1])
    result = IndependentScheduleValidator.validate(snapshot, schedule)

    # Invariant: Whole-section train clearance remains authoritative
    error_codes = [f.code for f in result.findings if f.severity == ValidationSeverity.ERROR]
    assert "TRAIN_MOVEMENT_CONFLICT" in error_codes
    assert result.valid is False
    assert result.is_approvable is False


# -----------------------------------------------------------------------------
# Test 14: Validator does not call CompatibilityEngine (Architectural Independence)
# -----------------------------------------------------------------------------
def test_validator_does_not_call_compatibility_engine(horizon, sample_tracks):
    t1 = {
        "task_id": "TSK-01",
        "task_code": "TC-01",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-UP",
        "window_start": horizon.start + timedelta(hours=2),
        "window_end": horizon.start + timedelta(hours=10),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }
    snapshot = _make_snapshot(horizon, [t1], sample_tracks)

    st1 = _make_scheduled_task(
        task_id="TSK-01",
        start_dt=horizon.start + timedelta(hours=3),
        end_dt=horizon.start + timedelta(hours=5),
    )
    schedule = _make_schedule(snapshot, [st1])

    # Monkeypatch CompatibilityEngine to fail if called
    with patch.object(CompatibilityEngine, "evaluate_spatial_compatibility", side_effect=RuntimeError("Validator violated independence by calling CompatibilityEngine!")):
        with patch.object(CompatibilityEngine, "evaluate_task_placement", side_effect=RuntimeError("Validator called CompatibilityEngine!")):
            result = IndependentScheduleValidator.validate(snapshot, schedule)
            assert result.valid is True
            assert result.is_approvable is True


# -----------------------------------------------------------------------------
# Test 15: Validator does not call CP-SAT solver (Architectural Independence)
# -----------------------------------------------------------------------------
def test_validator_does_not_call_cp_sat(horizon, sample_tracks):
    t1 = {
        "task_id": "TSK-01",
        "task_code": "TC-01",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-UP",
        "window_start": horizon.start + timedelta(hours=2),
        "window_end": horizon.start + timedelta(hours=10),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }
    snapshot = _make_snapshot(horizon, [t1], sample_tracks)

    st1 = _make_scheduled_task(
        task_id="TSK-01",
        start_dt=horizon.start + timedelta(hours=3),
        end_dt=horizon.start + timedelta(hours=5),
    )
    schedule = _make_schedule(snapshot, [st1])

    with patch.object(CPSATSolver, "solve", side_effect=RuntimeError("Validator violated independence by calling CPSATSolver!")):
        with patch.object(CPSATModelBuilder, "_add_section_and_train_constraints", side_effect=RuntimeError("Validator called CPSATModelBuilder!")):
            result = IndependentScheduleValidator.validate(snapshot, schedule)
            assert result.valid is True
            assert result.is_approvable is True
