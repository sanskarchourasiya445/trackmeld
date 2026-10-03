"""Phase 15B Unit Tests: SHA-256 Cryptographic Hash & Provenance Integrity.

Verifies:
- Canonical snapshot hashing determinism & order-independence
- Snapshot hash sensitivity to operational parameters (duration, window, sections)
- Input configuration hash determinism & seed sensitivity
- Schedule identity fingerprinting order-invariance and mutation sensitivity
- Independent verification and recomputation of historical stored hashes
"""

import copy
from datetime import datetime, timezone, timedelta
from backend.app.domain.temporal import PlanningHorizon, TrainPass
from backend.app.domain.scheduling import (
    ScheduleResult,
    ScheduledTaskResult,
    TimeInterval,
    SchedulerType,
    SchedulerStatus,
    ScheduleMetrics,
)
from backend.app.domain.planning_snapshot import PlanningSnapshot
from backend.app.services.validation.validator import IndependentScheduleValidator


def _make_dummy_snapshot() -> PlanningSnapshot:
    start = datetime(2026, 10, 15, 0, 0, tzinfo=timezone.utc)
    horizon = PlanningHorizon(start=start, end=start + timedelta(hours=24))

    t1 = {
        "task_id": "TSK-01",
        "task_code": "TC-01",
        "section_id": "SEC-01",
        "priority": "HIGH",
        "window_start": start + timedelta(hours=2),
        "window_end": start + timedelta(hours=8),
        "estimated_duration_minutes": 120,
    }
    t2 = {
        "task_id": "TSK-02",
        "task_code": "TC-02",
        "section_id": "SEC-02",
        "priority": "MEDIUM",
        "window_start": start + timedelta(hours=4),
        "window_end": start + timedelta(hours=10),
        "estimated_duration_minutes": 60,
    }
    tp = TrainPass(
        pass_id="PASS-01",
        train_id="TRN-01",
        train_number="12004",
        section_id="SEC-01",
        interval=TimeInterval(start=start + timedelta(hours=12), end=start + timedelta(hours=13)),
    )
    return PlanningSnapshot(
        scenario_id="SCN-TEST-HASH",
        snapshot_id="SNAP-HASH-01",
        horizon=horizon,
        tasks=[t1, t2],
        tasks_map={"TSK-01": t1, "TSK-02": t2},
        work_orders_map={},
        resources=[{"resource_id": "RES-01"}],
        resources_map={"RES-01": {"resource_id": "RES-01"}},
        resource_availabilities=[],
        dependencies=[],
        dependencies_by_successor={},
        dependencies_by_predecessor={},
        sections_map={"SEC-01": {}, "SEC-02": {}},
        rules_map={},
        train_passes=[tp],
    )


def test_snapshot_hash_determinism_and_reproducibility():
    """Identical snapshot data must generate the exact same 64-char SHA-256 hash."""
    snap1 = _make_dummy_snapshot()
    snap2 = _make_dummy_snapshot()

    h1 = snap1.compute_snapshot_hash()
    h2 = snap2.compute_snapshot_hash()

    assert len(h1) == 64
    assert h1 == h2


def test_snapshot_hash_order_invariance():
    """Permuting task list order in memory must produce the exact same hash (canonical sorting)."""
    snap_normal = _make_dummy_snapshot()
    tasks_reversed = list(reversed(snap_normal.tasks))

    snap_permuted = PlanningSnapshot(
        scenario_id=snap_normal.scenario_id,
        snapshot_id=snap_normal.snapshot_id,
        horizon=snap_normal.horizon,
        tasks=tasks_reversed,
        tasks_map=snap_normal.tasks_map,
        work_orders_map=snap_normal.work_orders_map,
        resources=snap_normal.resources,
        resources_map=snap_normal.resources_map,
        resource_availabilities=snap_normal.resource_availabilities,
        dependencies=snap_normal.dependencies,
        dependencies_by_successor=snap_normal.dependencies_by_successor,
        dependencies_by_predecessor=snap_normal.dependencies_by_predecessor,
        sections_map=snap_normal.sections_map,
        rules_map=snap_normal.rules_map,
        train_passes=snap_normal.train_passes,
    )

    assert snap_normal.compute_snapshot_hash() == snap_permuted.compute_snapshot_hash()


def test_snapshot_hash_sensitivity_to_task_mutation():
    """Mutating task parameters (duration, section, window) must produce a distinct hash."""
    base_snap = _make_dummy_snapshot()
    base_hash = base_snap.compute_snapshot_hash()

    # 1. Mutate duration
    mutated_tasks = copy.deepcopy(base_snap.tasks)
    mutated_tasks[0]["estimated_duration_minutes"] = 180
    snap_dur = PlanningSnapshot(**{**base_snap.__dict__, "tasks": mutated_tasks})
    assert snap_dur.compute_snapshot_hash() != base_hash

    # 2. Mutate section
    mutated_sec = copy.deepcopy(base_snap.tasks)
    mutated_sec[0]["section_id"] = "SEC-OTHER"
    snap_sec = PlanningSnapshot(**{**base_snap.__dict__, "tasks": mutated_sec})
    assert snap_sec.compute_snapshot_hash() != base_hash


def test_input_hash_determinism_and_seed_sensitivity():
    """Input hash combines snapshot hash, configuration dictionary, and random seed."""
    snap = _make_dummy_snapshot()
    cfg = {"scheduler_type": "CP_SAT", "time_limit_seconds": 15.0}

    h_seed_0 = snap.compute_input_hash(cfg, seed=0)
    h_seed_0_repeat = snap.compute_input_hash(cfg, seed=0)
    h_seed_42 = snap.compute_input_hash(cfg, seed=42)
    h_diff_cfg = snap.compute_input_hash({"scheduler_type": "FCFS"}, seed=0)

    assert h_seed_0 == h_seed_0_repeat
    assert h_seed_0 != h_seed_42
    assert h_seed_0 != h_diff_cfg


def test_schedule_identity_fingerprint_invariance_and_sensitivity():
    """Schedule fingerprint must be order-invariant, but sensitive to any scheduled interval changes."""
    snap = _make_dummy_snapshot()
    start = snap.horizon.start

    st1 = ScheduledTaskResult(
        task_id="TSK-01",
        task_code="TC-01",
        interval=TimeInterval(start=start + timedelta(hours=2), end=start + timedelta(hours=4)),
        possession_interval=TimeInterval(start=start + timedelta(hours=2), end=start + timedelta(hours=4)),
        duration_minutes=120,
        sequence_order=1,
        assigned_resources=["RES-01"],
        affected_sections=["SEC-01"],
    )
    st2 = ScheduledTaskResult(
        task_id="TSK-02",
        task_code="TC-02",
        interval=TimeInterval(start=start + timedelta(hours=5), end=start + timedelta(hours=6)),
        possession_interval=TimeInterval(start=start + timedelta(hours=5), end=start + timedelta(hours=6)),
        duration_minutes=60,
        sequence_order=2,
        assigned_resources=["RES-01"],
        affected_sections=["SEC-02"],
    )

    metrics = ScheduleMetrics(
        total_tasks=2,
        scheduled_tasks=2,
        unscheduled_tasks=0,
        completion_rate=1.0,
        mandatory_tasks=0,
        mandatory_scheduled=0,
        mandatory_unscheduled=0,
        mandatory_completion_rate=1.0,
        total_scheduled_duration_minutes=180,
        total_possession_duration_minutes=180,
        total_priority_score_available=100.0,
        scheduled_priority_score=100.0,
        unscheduled_priority_score=0.0,
        priority_score_capture_rate=1.0,
    )
    res_normal = ScheduleResult(
        schedule_id="SCHED-01",
        scheduler_type=SchedulerType.CP_SAT,
        scheduler_version="1.0.0",
        scenario_id="SCN-TEST-HASH",
        snapshot_id="SNAP-HASH-01",
        planning_start=start,
        planning_end=start + timedelta(hours=24),
        status=SchedulerStatus.OPTIMAL,
        metrics=metrics,
        configuration={},
        execution_time_ms=10.0,
        scheduled_tasks=[st1, st2],
        unscheduled_tasks=[],
    )
    res_permuted = ScheduleResult(
        schedule_id="SCHED-01",
        scheduler_type=SchedulerType.CP_SAT,
        scheduler_version="1.0.0",
        scenario_id="SCN-TEST-HASH",
        snapshot_id="SNAP-HASH-01",
        planning_start=start,
        planning_end=start + timedelta(hours=24),
        status=SchedulerStatus.OPTIMAL,
        metrics=metrics,
        configuration={},
        execution_time_ms=10.0,
        scheduled_tasks=[st2, st1],  # Reversed order
        unscheduled_tasks=[],
    )

    fp_normal = IndependentScheduleValidator.compute_schedule_identity(snap, res_normal)
    fp_permuted = IndependentScheduleValidator.compute_schedule_identity(snap, res_permuted)

    # Order invariance
    assert fp_normal == fp_permuted
    assert len(fp_normal) == 64

    # Sensitivity: mutate start time by 1 minute
    st1_shifted = ScheduledTaskResult(
        task_id="TSK-01",
        task_code="TC-01",
        interval=TimeInterval(start=start + timedelta(hours=2, minutes=1), end=start + timedelta(hours=4, minutes=1)),
        possession_interval=TimeInterval(start=start + timedelta(hours=2, minutes=1), end=start + timedelta(hours=4, minutes=1)),
        duration_minutes=120,
        sequence_order=1,
        assigned_resources=["RES-01"],
        affected_sections=["SEC-01"],
    )
    res_shifted = ScheduleResult(
        schedule_id="SCHED-01",
        scheduler_type=SchedulerType.CP_SAT,
        scheduler_version="1.0.0",
        scenario_id="SCN-TEST-HASH",
        snapshot_id="SNAP-HASH-01",
        planning_start=start,
        planning_end=start + timedelta(hours=24),
        status=SchedulerStatus.OPTIMAL,
        metrics=metrics,
        configuration={},
        execution_time_ms=10.0,
        scheduled_tasks=[st1_shifted, st2],
        unscheduled_tasks=[],
    )
    fp_shifted = IndependentScheduleValidator.compute_schedule_identity(snap, res_shifted)
    assert fp_normal != fp_shifted
