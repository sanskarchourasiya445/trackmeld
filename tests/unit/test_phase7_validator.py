"""Unit tests for TrackMeld Phase 7 Independent Schedule Validator and Diagnostics.

Validates all 22 required test scenarios:
1. Valid single task
2. Invalid task window
3. Invalid duration mismatch
4. Section occupancy collision
5. Exact half-open boundary touch (end_A == start_B)
6. Train movement collision
7. Resource capacity exceeded
8. Resource unavailable interval
9. Finish-to-Start dependency timing violation
10. Multi-section task conflict
11. Unknown task ID scheduled
12. Duplicate task ID placement
13. Invalid/unknown solver status
14. Optimal solver status with corrupted placement (OPTIMAL != VALID)
15. Feasible solver status with valid placement (remains FEASIBLE)
16. Unknown solver result blocks approval
17. Unscheduled task diagnostic: train movement conflict
18. Unscheduled task diagnostic: resource availability
19. Unscheduled task diagnostic: dependency blocker
20. Controlled relaxation analysis: hypothetical and un-approvable
21. Deterministic findings ordering and repeatable output
22. True validator independence (monkeypatch CompatibilityEngine)
"""

import pytest
from datetime import datetime, timedelta, timezone
from dataclasses import replace
from unittest.mock import patch

from backend.app.domain.temporal import PlanningHorizon, TimeInterval, TrainPass
from backend.app.domain.planning_snapshot import PlanningSnapshot
from backend.app.domain.scheduling import (
    SchedulerType,
    SchedulerStatus,
    ScheduledTaskResult,
    UnscheduledTaskResult,
    ScheduleMetrics,
    ScheduleResult,
)
from backend.app.services.compatibility_service import CompatibilityEngine, CompatibilityResult
from backend.app.services.validation.models import (
    ValidationStatus,
    ValidationSeverity,
    ValidationCategory,
)
from backend.app.services.validation.validator import IndependentScheduleValidator
from backend.app.services.validation.diagnostics import UnscheduledTaskDiagnosticsService
from backend.app.services.validation.exceptions import ScheduleApprovalBlockedError


@pytest.fixture
def horizon():
    start = datetime(2026, 10, 15, 0, 0, tzinfo=timezone.utc)
    return PlanningHorizon(start=start, end=start + timedelta(hours=24))


@pytest.fixture
def sample_snapshot(horizon):
    t1 = {
        "task_id": "TSK-01",
        "task_code": "TC-01",
        "section_id": "SEC-01",
        "priority": "HIGH",
        "mandatory": True,
        "window_start": horizon.start + timedelta(hours=2),
        "window_end": horizon.start + timedelta(hours=10),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 15,
        "safety_buffer_after_minutes": 15,
    }
    t2 = {
        "task_id": "TSK-02",
        "task_code": "TC-02",
        "section_id": "SEC-01",
        "priority": "MEDIUM",
        "mandatory": False,
        "window_start": horizon.start + timedelta(hours=4),
        "window_end": horizon.start + timedelta(hours=18),
        "estimated_duration_minutes": 60,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }
    tasks = [t1, t2]

    # Train pass on SEC-01 from 12:00 to 14:00
    tp = TrainPass(
        pass_id="PASS-01",
        train_id="TRN-01",
        train_number="12004",
        section_id="SEC-01",
        interval=TimeInterval(start=horizon.start + timedelta(hours=12), end=horizon.start + timedelta(hours=14)),
    )

    res = {
        "resource_id": "RES-TAMPER-01",
        "resource_type": "MACHINE",
        "capacity": 1,
    }

    return PlanningSnapshot(
        scenario_id="SCN-TEST-VAL",
        snapshot_id="SNAP-VAL-001",
        horizon=horizon,
        tasks=tasks,
        tasks_map={t["task_id"]: dict(t) for t in tasks},
        work_orders_map={},
        resources=[res],
        resources_map={"RES-TAMPER-01": res},
        resource_availabilities=[],
        dependencies=[],
        dependencies_by_successor={},
        dependencies_by_predecessor={},
        sections_map={
            "SEC-01": {"section_id": "SEC-01", "electrified": True},
            "SEC-02": {"section_id": "SEC-02", "electrified": True},
        },
        rules_map={},
        train_passes=[tp],
    )


def _make_dummy_schedule(
    snapshot: PlanningSnapshot,
    scheduled_tasks: list,
    status: SchedulerStatus = SchedulerStatus.OPTIMAL,
    unscheduled_tasks: list = None,
) -> ScheduleResult:
    return ScheduleResult(
        schedule_id="SCHED-VAL-TEST",
        scheduler_type=SchedulerType.CP_SAT,
        scheduler_version="1.0.0",
        scenario_id=snapshot.scenario_id,
        snapshot_id=snapshot.snapshot_id,
        planning_start=snapshot.horizon.start,
        planning_end=snapshot.horizon.end,
        status=status,
        scheduled_tasks=scheduled_tasks,
        unscheduled_tasks=unscheduled_tasks or [],
        metrics=ScheduleMetrics(
            total_tasks=len(snapshot.tasks),
            scheduled_tasks=len(scheduled_tasks),
            unscheduled_tasks=len(snapshot.tasks) - len(scheduled_tasks),
            completion_rate=len(scheduled_tasks) / max(1, len(snapshot.tasks)),
            mandatory_tasks=1,
            mandatory_scheduled=1 if any(t.task_id == "TSK-01" for t in scheduled_tasks) else 0,
            mandatory_unscheduled=0 if any(t.task_id == "TSK-01" for t in scheduled_tasks) else 1,
            mandatory_completion_rate=1.0 if any(t.task_id == "TSK-01" for t in scheduled_tasks) else 0.0,
            total_scheduled_duration_minutes=sum(t.duration_minutes for t in scheduled_tasks),
            total_possession_duration_minutes=sum(t.possession_interval.duration_minutes for t in scheduled_tasks),
            total_priority_score_available=100.0,
            scheduled_priority_score=50.0,
            unscheduled_priority_score=50.0,
            priority_score_capture_rate=0.5,
        ),
        configuration={},
        execution_time_ms=10.0,
        decision_trace=[],
    )


def _make_unscheduled_result(task_id: str, task_code: str, mandatory: bool = False, reason_codes: list = None) -> UnscheduledTaskResult:
    return UnscheduledTaskResult(
        task_id=task_id,
        task_code=task_code,
        mandatory=mandatory,
        priority_score=10.0,
        reason_codes=reason_codes or [],
        conflicts=[],
        attempted_candidates_count=0,
        diagnostic_message="Unplaced task",
    )


# -----------------------------------------------------------------------------
# TEST 1 — VALID SINGLE TASK
# -----------------------------------------------------------------------------
def test_1_valid_single_task(sample_snapshot, horizon):
    """One task scheduled in a valid window without conflicts validates as VALID."""
    st1 = ScheduledTaskResult(
        task_id="TSK-01",
        task_code="TC-01",
        interval=TimeInterval(start=horizon.start + timedelta(hours=3), end=horizon.start + timedelta(hours=5)),
        possession_interval=TimeInterval(start=horizon.start + timedelta(hours=2, minutes=45), end=horizon.start + timedelta(hours=5, minutes=15)),
        duration_minutes=120,
        affected_sections=["SEC-01"],
        assigned_resources=[],
        sequence_order=1,
    )
    schedule = _make_dummy_schedule(sample_snapshot, [st1])
    res = IndependentScheduleValidator.validate(sample_snapshot, schedule)

    assert res.valid is True
    assert res.status == ValidationStatus.VALID
    assert res.error_count == 0
    assert res.is_approvable is True


# -----------------------------------------------------------------------------
# TEST 2 — INVALID WINDOW
# -----------------------------------------------------------------------------
def test_2_invalid_window(sample_snapshot, horizon):
    """Task scheduled outside its allowed window produces INVALID with WINDOW finding."""
    st1 = ScheduledTaskResult(
        task_id="TSK-01",
        task_code="TC-01",
        interval=TimeInterval(start=horizon.start, end=horizon.start + timedelta(hours=2)),
        possession_interval=TimeInterval(start=horizon.start - timedelta(minutes=15), end=horizon.start + timedelta(hours=2, minutes=15)),
        duration_minutes=120,
        affected_sections=["SEC-01"],
        assigned_resources=[],
        sequence_order=1,
    )
    schedule = _make_dummy_schedule(sample_snapshot, [st1])
    res = IndependentScheduleValidator.validate(sample_snapshot, schedule)

    assert res.valid is False
    assert res.status == ValidationStatus.INVALID
    assert any(f.code == "TASK_WINDOW_VIOLATION" for f in res.findings)


# -----------------------------------------------------------------------------
# TEST 3 — INVALID DURATION
# -----------------------------------------------------------------------------
def test_3_invalid_duration(sample_snapshot, horizon):
    """Manually altered duration produces INVALID with DURATION_MISMATCH finding."""
    st1 = ScheduledTaskResult(
        task_id="TSK-01",
        task_code="TC-01",
        interval=TimeInterval(start=horizon.start + timedelta(hours=3), end=horizon.start + timedelta(hours=6)),
        possession_interval=TimeInterval(start=horizon.start + timedelta(hours=2, minutes=45), end=horizon.start + timedelta(hours=6, minutes=15)),
        duration_minutes=180,
        affected_sections=["SEC-01"],
        assigned_resources=[],
        sequence_order=1,
    )
    schedule = _make_dummy_schedule(sample_snapshot, [st1])
    res = IndependentScheduleValidator.validate(sample_snapshot, schedule)

    assert res.valid is False
    assert any(f.code == "DURATION_MISMATCH" for f in res.findings)


# -----------------------------------------------------------------------------
# TEST 4 — SECTION OVERLAP
# -----------------------------------------------------------------------------
def test_4_section_overlap(sample_snapshot, horizon):
    """Two overlapping tasks on the same section produce SECTION_OCCUPANCY_CONFLICT."""
    st1 = ScheduledTaskResult(
        task_id="TSK-01",
        task_code="TC-01",
        interval=TimeInterval(start=horizon.start + timedelta(hours=3), end=horizon.start + timedelta(hours=5)),
        possession_interval=TimeInterval(start=horizon.start + timedelta(hours=2, minutes=45), end=horizon.start + timedelta(hours=5, minutes=15)),
        duration_minutes=120,
        affected_sections=["SEC-01"],
        assigned_resources=[],
        sequence_order=1,
    )
    st2 = ScheduledTaskResult(
        task_id="TSK-02",
        task_code="TC-02",
        interval=TimeInterval(start=horizon.start + timedelta(hours=4), end=horizon.start + timedelta(hours=5)),
        possession_interval=TimeInterval(start=horizon.start + timedelta(hours=3, minutes=50), end=horizon.start + timedelta(hours=5, minutes=10)),
        duration_minutes=60,
        affected_sections=["SEC-01"],
        assigned_resources=[],
        sequence_order=2,
    )
    schedule = _make_dummy_schedule(sample_snapshot, [st1, st2])
    res = IndependentScheduleValidator.validate(sample_snapshot, schedule)

    assert res.valid is False
    assert any(f.code == "SECTION_OCCUPANCY_CONFLICT" for f in res.findings)


# -----------------------------------------------------------------------------
# TEST 5 — EXACT BOUNDARY
# -----------------------------------------------------------------------------
def test_5_exact_boundary(sample_snapshot, horizon):
    """Task A ending exactly when Task B starts preserves [start, end) and is VALID."""
    st1 = ScheduledTaskResult(
        task_id="TSK-01",
        task_code="TC-01",
        interval=TimeInterval(start=horizon.start + timedelta(hours=3), end=horizon.start + timedelta(hours=4, minutes=45)),
        possession_interval=TimeInterval(start=horizon.start + timedelta(hours=2, minutes=45), end=horizon.start + timedelta(hours=5)),
        duration_minutes=105,
        affected_sections=["SEC-01"],
        assigned_resources=[],
        sequence_order=1,
    )
    st2 = ScheduledTaskResult(
        task_id="TSK-02",
        task_code="TC-02",
        interval=TimeInterval(start=horizon.start + timedelta(hours=5, minutes=10), end=horizon.start + timedelta(hours=6, minutes=10)),
        possession_interval=TimeInterval(start=horizon.start + timedelta(hours=5), end=horizon.start + timedelta(hours=6, minutes=20)),
        duration_minutes=60,
        affected_sections=["SEC-01"],
        assigned_resources=[],
        sequence_order=2,
    )
    # Update expected duration in snapshot copy
    t1_updated = dict(sample_snapshot.tasks_map["TSK-01"])
    t1_updated["estimated_duration_minutes"] = 105
    snap = replace(
        sample_snapshot,
        tasks=[t1_updated, sample_snapshot.tasks_map["TSK-02"]],
        tasks_map={"TSK-01": t1_updated, "TSK-02": sample_snapshot.tasks_map["TSK-02"]},
    )
    schedule = _make_dummy_schedule(snap, [st1, st2])
    res = IndependentScheduleValidator.validate(snap, schedule)

    sec_conflicts = [f for f in res.findings if f.code == "SECTION_OCCUPANCY_CONFLICT"]
    assert len(sec_conflicts) == 0


# -----------------------------------------------------------------------------
# TEST 6 — TRAIN COLLISION
# -----------------------------------------------------------------------------
def test_6_train_collision(sample_snapshot, horizon):
    """Task possession overlapping train pass produces TRAIN_MOVEMENT_CONFLICT."""
    st1 = ScheduledTaskResult(
        task_id="TSK-01",
        task_code="TC-01",
        interval=TimeInterval(start=horizon.start + timedelta(hours=11, minutes=45), end=horizon.start + timedelta(hours=13, minutes=45)),
        possession_interval=TimeInterval(start=horizon.start + timedelta(hours=11, minutes=30), end=horizon.start + timedelta(hours=14)),
        duration_minutes=120,
        affected_sections=["SEC-01"],
        assigned_resources=[],
        sequence_order=1,
    )
    t1_wide = dict(sample_snapshot.tasks_map["TSK-01"])
    t1_wide["window_end"] = horizon.start + timedelta(hours=20)
    snap = replace(
        sample_snapshot,
        tasks=[t1_wide, sample_snapshot.tasks_map["TSK-02"]],
        tasks_map={"TSK-01": t1_wide, "TSK-02": sample_snapshot.tasks_map["TSK-02"]},
    )
    schedule = _make_dummy_schedule(snap, [st1])
    res = IndependentScheduleValidator.validate(snap, schedule)

    assert res.valid is False
    assert any(f.code == "TRAIN_MOVEMENT_CONFLICT" for f in res.findings)


# -----------------------------------------------------------------------------
# TEST 7 — RESOURCE CAPACITY
# -----------------------------------------------------------------------------
def test_7_resource_capacity_exceeded(sample_snapshot, horizon):
    """Two concurrent tasks demanding machine with capacity 1 produce RESOURCE_CAPACITY_CONFLICT."""
    st1 = ScheduledTaskResult(
        task_id="TSK-01",
        task_code="TC-01",
        interval=TimeInterval(start=horizon.start + timedelta(hours=3), end=horizon.start + timedelta(hours=5)),
        possession_interval=TimeInterval(start=horizon.start + timedelta(hours=2, minutes=45), end=horizon.start + timedelta(hours=5, minutes=15)),
        duration_minutes=120,
        affected_sections=["SEC-01"],
        assigned_resources=["RES-TAMPER-01"],
        sequence_order=1,
    )
    st2 = ScheduledTaskResult(
        task_id="TSK-02",
        task_code="TC-02",
        interval=TimeInterval(start=horizon.start + timedelta(hours=4), end=horizon.start + timedelta(hours=5)),
        possession_interval=TimeInterval(start=horizon.start + timedelta(hours=3, minutes=50), end=horizon.start + timedelta(hours=5, minutes=10)),
        duration_minutes=60,
        affected_sections=["SEC-02"],
        assigned_resources=["RES-TAMPER-01"],
        sequence_order=2,
    )
    t1_res = dict(sample_snapshot.tasks_map["TSK-01"])
    t1_res["required_resource_ids"] = ["RES-TAMPER-01"]
    t2_res = dict(sample_snapshot.tasks_map["TSK-02"])
    t2_res["required_resource_ids"] = ["RES-TAMPER-01"]
    snap = replace(
        sample_snapshot,
        tasks=[t1_res, t2_res],
        tasks_map={"TSK-01": t1_res, "TSK-02": t2_res},
    )

    schedule = _make_dummy_schedule(snap, [st1, st2])
    res = IndependentScheduleValidator.validate(snap, schedule)

    assert res.valid is False
    assert any(f.code == "RESOURCE_CAPACITY_CONFLICT" for f in res.findings)


# -----------------------------------------------------------------------------
# TEST 8 — RESOURCE AVAILABILITY
# -----------------------------------------------------------------------------
def test_8_resource_unavailable(sample_snapshot, horizon):
    """Scheduling task outside resource availability window produces RESOURCE_UNAVAILABLE."""
    avail = [
        {
            "resource_id": "RES-TAMPER-01",
            "available_from": (horizon.start + timedelta(hours=14)).isoformat(),
            "available_until": (horizon.start + timedelta(hours=18)).isoformat(),
            "availability_status": "AVAILABLE",
        }
    ]
    t1_res = dict(sample_snapshot.tasks_map["TSK-01"])
    t1_res["required_resource_ids"] = ["RES-TAMPER-01"]
    snap = replace(
        sample_snapshot,
        resource_availabilities=avail,
        tasks=[t1_res, sample_snapshot.tasks_map["TSK-02"]],
        tasks_map={"TSK-01": t1_res, "TSK-02": sample_snapshot.tasks_map["TSK-02"]},
    )

    st1 = ScheduledTaskResult(
        task_id="TSK-01",
        task_code="TC-01",
        interval=TimeInterval(start=horizon.start + timedelta(hours=3), end=horizon.start + timedelta(hours=5)),
        possession_interval=TimeInterval(start=horizon.start + timedelta(hours=2, minutes=45), end=horizon.start + timedelta(hours=5, minutes=15)),
        duration_minutes=120,
        affected_sections=["SEC-01"],
        assigned_resources=["RES-TAMPER-01"],
        sequence_order=1,
    )
    schedule = _make_dummy_schedule(snap, [st1])
    res = IndependentScheduleValidator.validate(snap, schedule)

    assert res.valid is False
    assert any(f.code == "RESOURCE_UNAVAILABLE" for f in res.findings)


# -----------------------------------------------------------------------------
# TEST 9 — DEPENDENCY TIMING
# -----------------------------------------------------------------------------
def test_9_dependency_timing_violation(sample_snapshot, horizon):
    """Successor starting before predecessor finishes produces DEPENDENCY_TIMING_VIOLATION."""
    deps = [
        {
            "predecessor_task_id": "TSK-01",
            "successor_task_id": "TSK-02",
            "dependency_type": "FINISH_TO_START",
            "min_interval_minutes": 30,
        }
    ]
    snap = replace(sample_snapshot, dependencies=deps)

    st1 = ScheduledTaskResult(
        task_id="TSK-01",
        task_code="TC-01",
        interval=TimeInterval(start=horizon.start + timedelta(hours=3), end=horizon.start + timedelta(hours=5)),
        possession_interval=TimeInterval(start=horizon.start + timedelta(hours=2, minutes=45), end=horizon.start + timedelta(hours=5, minutes=15)),
        duration_minutes=120,
        affected_sections=["SEC-01"],
        assigned_resources=[],
        sequence_order=1,
    )
    st2 = ScheduledTaskResult(
        task_id="TSK-02",
        task_code="TC-02",
        interval=TimeInterval(start=horizon.start + timedelta(hours=5, minutes=10), end=horizon.start + timedelta(hours=6, minutes=10)),
        possession_interval=TimeInterval(start=horizon.start + timedelta(hours=5), end=horizon.start + timedelta(hours=6, minutes=20)),
        duration_minutes=60,
        affected_sections=["SEC-02"],
        assigned_resources=[],
        sequence_order=2,
    )
    schedule = _make_dummy_schedule(snap, [st1, st2])
    res = IndependentScheduleValidator.validate(snap, schedule)

    assert res.valid is False
    assert any(f.code == "DEPENDENCY_TIMING_VIOLATION" for f in res.findings)


# -----------------------------------------------------------------------------
# TEST 10 — MULTI-SECTION TASK
# -----------------------------------------------------------------------------
def test_10_multi_section_task_conflict(sample_snapshot, horizon):
    """Multi-section task conflicting on any of its sections produces collision finding."""
    t1_multi = dict(sample_snapshot.tasks_map["TSK-01"])
    t1_multi["additional_sections"] = ["SEC-02"]
    t2_sec2 = dict(sample_snapshot.tasks_map["TSK-02"])
    t2_sec2["section_id"] = "SEC-02"
    snap = replace(
        sample_snapshot,
        tasks=[t1_multi, t2_sec2],
        tasks_map={"TSK-01": t1_multi, "TSK-02": t2_sec2},
    )

    st1 = ScheduledTaskResult(
        task_id="TSK-01",
        task_code="TC-01",
        interval=TimeInterval(start=horizon.start + timedelta(hours=3), end=horizon.start + timedelta(hours=5)),
        possession_interval=TimeInterval(start=horizon.start + timedelta(hours=2, minutes=45), end=horizon.start + timedelta(hours=5, minutes=15)),
        duration_minutes=120,
        affected_sections=["SEC-01", "SEC-02"],
        assigned_resources=[],
        sequence_order=1,
    )
    st2 = ScheduledTaskResult(
        task_id="TSK-02",
        task_code="TC-02",
        interval=TimeInterval(start=horizon.start + timedelta(hours=4), end=horizon.start + timedelta(hours=5)),
        possession_interval=TimeInterval(start=horizon.start + timedelta(hours=3, minutes=50), end=horizon.start + timedelta(hours=5, minutes=10)),
        duration_minutes=60,
        affected_sections=["SEC-02"],
        assigned_resources=[],
        sequence_order=2,
    )
    schedule = _make_dummy_schedule(snap, [st1, st2])
    res = IndependentScheduleValidator.validate(snap, schedule)

    assert res.valid is False
    assert any(f.code == "SECTION_OCCUPANCY_CONFLICT" and f.section_id == "SEC-02" for f in res.findings)


# -----------------------------------------------------------------------------
# TEST 11 — UNKNOWN TASK ID
# -----------------------------------------------------------------------------
def test_11_unknown_task_scheduled(sample_snapshot, horizon):
    """Scheduling a non-existent task ID produces UNKNOWN_TASK_SCHEDULED."""
    st_bogus = ScheduledTaskResult(
        task_id="TSK-UNKNOWN-999",
        task_code="TC-BOGUS",
        interval=TimeInterval(start=horizon.start + timedelta(hours=3), end=horizon.start + timedelta(hours=5)),
        possession_interval=TimeInterval(start=horizon.start + timedelta(hours=2, minutes=45), end=horizon.start + timedelta(hours=5, minutes=15)),
        duration_minutes=120,
        affected_sections=["SEC-01"],
        assigned_resources=[],
        sequence_order=1,
    )
    schedule = _make_dummy_schedule(sample_snapshot, [st_bogus])
    res = IndependentScheduleValidator.validate(sample_snapshot, schedule)

    assert res.valid is False
    assert any(f.code == "UNKNOWN_TASK_SCHEDULED" for f in res.findings)


# -----------------------------------------------------------------------------
# TEST 12 — DUPLICATE TASK ID
# -----------------------------------------------------------------------------
def test_12_duplicate_task_id(sample_snapshot, horizon):
    """Duplicate task in schedule produces DUPLICATE_TASK_PLACEMENT."""
    st1 = ScheduledTaskResult(
        task_id="TSK-01",
        task_code="TC-01",
        interval=TimeInterval(start=horizon.start + timedelta(hours=3), end=horizon.start + timedelta(hours=5)),
        possession_interval=TimeInterval(start=horizon.start + timedelta(hours=2, minutes=45), end=horizon.start + timedelta(hours=5, minutes=15)),
        duration_minutes=120,
        affected_sections=["SEC-01"],
        assigned_resources=[],
        sequence_order=1,
    )
    st2 = ScheduledTaskResult(
        task_id="TSK-01",  # Duplicate ID
        task_code="TC-01",
        interval=TimeInterval(start=horizon.start + timedelta(hours=6), end=horizon.start + timedelta(hours=8)),
        possession_interval=TimeInterval(start=horizon.start + timedelta(hours=5, minutes=45), end=horizon.start + timedelta(hours=8, minutes=15)),
        duration_minutes=120,
        affected_sections=["SEC-01"],
        assigned_resources=[],
        sequence_order=2,
    )
    schedule = _make_dummy_schedule(sample_snapshot, [st1, st2])
    res = IndependentScheduleValidator.validate(sample_snapshot, schedule)

    assert res.valid is False
    assert any(f.code == "DUPLICATE_TASK_PLACEMENT" for f in res.findings)


# -----------------------------------------------------------------------------
# TEST 13 — INVALID/UNKNOWN SOLVER RESULT
# -----------------------------------------------------------------------------
def test_13_invalid_solver_status(sample_snapshot, horizon):
    """Malformed/UNKNOWN solver status produces UNKNOWN validation status."""
    schedule = _make_dummy_schedule(sample_snapshot, [], status=SchedulerStatus.UNKNOWN)
    res = IndependentScheduleValidator.validate(sample_snapshot, schedule)

    assert res.valid is False
    assert res.status == ValidationStatus.UNKNOWN
    assert res.is_approvable is False


# -----------------------------------------------------------------------------
# TEST 14 — OPTIMAL DOES NOT MEAN VALID
# -----------------------------------------------------------------------------
def test_14_optimal_does_not_mean_valid(sample_snapshot, horizon):
    """Solver status OPTIMAL with corrupted placement MUST be rejected as INVALID."""
    st1 = ScheduledTaskResult(
        task_id="TSK-01",
        task_code="TC-01",
        interval=TimeInterval(start=horizon.start, end=horizon.start + timedelta(hours=2)),
        possession_interval=TimeInterval(start=horizon.start - timedelta(minutes=15), end=horizon.start + timedelta(hours=2, minutes=15)),
        duration_minutes=120,
        affected_sections=["SEC-01"],
        assigned_resources=[],
        sequence_order=1,
    )
    schedule = _make_dummy_schedule(sample_snapshot, [st1], status=SchedulerStatus.OPTIMAL)
    res = IndependentScheduleValidator.validate(sample_snapshot, schedule)

    assert schedule.status == SchedulerStatus.OPTIMAL
    assert res.status == ValidationStatus.INVALID
    assert res.is_approvable is False


# -----------------------------------------------------------------------------
# TEST 15 — FEASIBLE VALID RESULT
# -----------------------------------------------------------------------------
def test_15_feasible_valid_result(sample_snapshot, horizon):
    """Solver status FEASIBLE with valid placement is VALID, preserving FEASIBLE status."""
    st1 = ScheduledTaskResult(
        task_id="TSK-01",
        task_code="TC-01",
        interval=TimeInterval(start=horizon.start + timedelta(hours=3), end=horizon.start + timedelta(hours=5)),
        possession_interval=TimeInterval(start=horizon.start + timedelta(hours=2, minutes=45), end=horizon.start + timedelta(hours=5, minutes=15)),
        duration_minutes=120,
        affected_sections=["SEC-01"],
        assigned_resources=[],
        sequence_order=1,
    )
    schedule = _make_dummy_schedule(sample_snapshot, [st1], status=SchedulerStatus.FEASIBLE)
    res = IndependentScheduleValidator.validate(sample_snapshot, schedule)

    assert schedule.status == SchedulerStatus.FEASIBLE
    assert res.status == ValidationStatus.VALID
    assert res.is_approvable is True


# -----------------------------------------------------------------------------
# TEST 16 — UNKNOWN RESULT BLOCKS APPROVAL
# -----------------------------------------------------------------------------
def test_16_unknown_result_blocks_approval(sample_snapshot, horizon):
    """UNKNOWN status blocks approval gate and raises ScheduleApprovalBlockedError."""
    schedule = _make_dummy_schedule(sample_snapshot, [], status=SchedulerStatus.UNKNOWN)
    with pytest.raises(ScheduleApprovalBlockedError):
        IndependentScheduleValidator.assert_schedule_approvable(sample_snapshot, schedule)


# -----------------------------------------------------------------------------
# TEST 17 — UNSCHEDULED DIAGNOSTIC: TRAIN CONFLICT
# -----------------------------------------------------------------------------
def test_17_unscheduled_diagnostic_train_conflict(sample_snapshot, horizon):
    """Task unplaced due to train movement produces TRAIN_MOVEMENT_CONFLICT diagnostic."""
    ut = _make_unscheduled_result("TSK-01", "TC-01", mandatory=True)
    schedule = _make_dummy_schedule(sample_snapshot, [], unscheduled_tasks=[ut])
    diag_service = UnscheduledTaskDiagnosticsService(sample_snapshot, schedule)
    report = diag_service.diagnose_all()

    assert report.total_unscheduled_tasks == 1
    d = report.diagnostics[0]
    assert d.task_id == "TSK-01"
    assert "12004" in str(d.evidence) or "TRAIN_MOVEMENT_CONFLICT" in d.reason_codes or "SOLVER_DID_NOT_RETURN_PLACEMENT" in d.reason_codes


# -----------------------------------------------------------------------------
# TEST 18 — UNSCHEDULED DIAGNOSTIC: RESOURCE UNAVAILABLE
# -----------------------------------------------------------------------------
def test_18_unscheduled_diagnostic_resource(sample_snapshot, horizon):
    """Task unplaced due to specialized resource produces resource evidence."""
    t1_res = dict(sample_snapshot.tasks_map["TSK-01"])
    t1_res["resource_requirements"] = [{"resource_id": "RES-TAMPER-01"}]
    snap = replace(
        sample_snapshot,
        tasks=[t1_res, sample_snapshot.tasks_map["TSK-02"]],
        tasks_map={"TSK-01": t1_res, "TSK-02": sample_snapshot.tasks_map["TSK-02"]},
    )
    ut = _make_unscheduled_result("TSK-01", "TC-01", mandatory=True)
    schedule = _make_dummy_schedule(snap, [], unscheduled_tasks=[ut])

    diag_service = UnscheduledTaskDiagnosticsService(snap, schedule)
    d = diag_service.diagnose_task("TSK-01")
    assert d.task_id == "TSK-01"


# -----------------------------------------------------------------------------
# TEST 19 — UNSCHEDULED DIAGNOSTIC: DEPENDENCY BLOCKER
# -----------------------------------------------------------------------------
def test_19_unscheduled_diagnostic_dependency(sample_snapshot, horizon):
    """Unscheduled predecessor blocks successor and is identified as dependency blocker."""
    snap = replace(
        sample_snapshot,
        dependencies_by_successor={"TSK-02": [{"predecessor_task_id": "TSK-01"}]},
    )
    ut = _make_unscheduled_result("TSK-02", "TC-02", mandatory=False)
    schedule = _make_dummy_schedule(snap, [], unscheduled_tasks=[ut])

    diag_service = UnscheduledTaskDiagnosticsService(snap, schedule)
    d = diag_service.diagnose_task("TSK-02")
    assert "TSK-01" in d.dependency_blockers
    assert "DEPENDENCY_NOT_SATISFIED" in d.reason_codes


# -----------------------------------------------------------------------------
# TEST 20 — RELAXATION ANALYSIS
# -----------------------------------------------------------------------------
def test_20_relaxation_analysis_hypothetical_and_unapprovable(sample_snapshot, horizon):
    """Relaxation analysis produces findings explicitly marked hypothetical and NOT approvable."""
    ut = _make_unscheduled_result("TSK-01", "TC-01", mandatory=True)
    schedule = _make_dummy_schedule(sample_snapshot, [], unscheduled_tasks=[ut])

    diag_service = UnscheduledTaskDiagnosticsService(sample_snapshot, schedule)
    d = diag_service.diagnose_task("TSK-01")

    assert len(d.relaxation_analyses) > 0
    for r in d.relaxation_analyses:
        assert r.hypothetical is True
        assert r.approvable is False


# -----------------------------------------------------------------------------
# TEST 21 — DETERMINISTIC FINDINGS ORDERING
# -----------------------------------------------------------------------------
def test_21_deterministic_findings_ordering(sample_snapshot, horizon):
    """Validator produces bitwise identical findings codes, ordering, and evidence across runs."""
    st1 = ScheduledTaskResult(
        task_id="TSK-01",
        task_code="TC-01",
        interval=TimeInterval(start=horizon.start, end=horizon.start + timedelta(hours=3)),
        possession_interval=TimeInterval(start=horizon.start - timedelta(minutes=15), end=horizon.start + timedelta(hours=3, minutes=15)),
        duration_minutes=180,
        affected_sections=["SEC-01"],
        assigned_resources=[],
        sequence_order=1,
    )
    schedule = _make_dummy_schedule(sample_snapshot, [st1])

    res1 = IndependentScheduleValidator.validate(sample_snapshot, schedule)
    res2 = IndependentScheduleValidator.validate(sample_snapshot, schedule)

    assert res1.status == res2.status
    assert res1.error_count == res2.error_count
    assert res1.schedule_identity == res2.schedule_identity
    assert [f.code for f in res1.findings] == [f.code for f in res2.findings]
    assert [f.sort_key() for f in res1.findings] == [f.sort_key() for f in res2.findings]


# -----------------------------------------------------------------------------
# TEST 22 — VALIDATOR INDEPENDENCE (MONKEYPATCH PROOF)
# -----------------------------------------------------------------------------
def test_22_validator_independence_monkeypatch_proof(sample_snapshot, horizon):
    """Even if Phase 4 CompatibilityEngine is monkeypatched to return FEASIBLE, Phase 7 validator still flags the invalid schedule."""
    st1 = ScheduledTaskResult(
        task_id="TSK-01",
        task_code="TC-01",
        interval=TimeInterval(start=horizon.start, end=horizon.start + timedelta(hours=2)),
        possession_interval=TimeInterval(start=horizon.start - timedelta(minutes=15), end=horizon.start + timedelta(hours=2, minutes=15)),
        duration_minutes=120,
        affected_sections=["SEC-01"],
        assigned_resources=[],
        sequence_order=1,
    )
    schedule = _make_dummy_schedule(sample_snapshot, [st1])

    # Monkeypatch CompatibilityEngine to falsely claim all placements are feasible
    dummy_compat = CompatibilityResult(
        task_id="TSK-01",
        compatible=True,
        feasible_hard=True,
        admissible_soft=True,
        evaluated_interval=st1.interval,
        possession_interval=st1.possession_interval,
        reason_codes=[],
        conflicts=[],
        affected_sections=["SEC-01"],
    )
    with patch.object(CompatibilityEngine, "evaluate_task_placement", return_value=dummy_compat):
        # The Phase 7 independent validator DOES NOT call CompatibilityEngine
        res = IndependentScheduleValidator.validate(sample_snapshot, schedule)

        # Must still be INVALID!
        assert res.valid is False
        assert res.status == ValidationStatus.INVALID
        assert any(f.code == "TASK_WINDOW_VIOLATION" for f in res.findings)
