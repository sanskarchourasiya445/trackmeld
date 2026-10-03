"""Phase 15D Unit Tests — Schedule Identity Fingerprint.

Adversarial tests verifying that compute_schedule_identity produces
different fingerprints when any identity-bearing field changes, and
the same fingerprint for equivalent schedules.

Classification: ASSUMPTION (fingerprint scope is internal design)
"""

import hashlib
import json
from copy import deepcopy
from datetime import datetime, timezone

import pytest

from backend.app.services.validation.validator import IndependentScheduleValidator
from backend.app.domain.scheduling import (
    ScheduleResult,
    ScheduledTaskResult,
    UnscheduledTaskResult,
    ScheduleMetrics,
    SchedulerType,
    SchedulerStatus,
    TimeInterval,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_interval(start: str, end: str) -> TimeInterval:
    return TimeInterval(
        start=datetime.fromisoformat(start),
        end=datetime.fromisoformat(end),
    )


def _base_task(task_id: str = "TSK-001") -> ScheduledTaskResult:
    return ScheduledTaskResult(
        task_id=task_id,
        task_code=f"CODE-{task_id}",
        interval=_make_interval("2026-10-01T02:00:00+00:00", "2026-10-01T06:00:00+00:00"),
        possession_interval=_make_interval("2026-10-01T01:45:00+00:00", "2026-10-01T06:15:00+00:00"),
        duration_minutes=240,
        affected_sections=["SEC-01", "SEC-02"],
        assigned_resources=["RES-A"],
        sequence_order=1,
        scheduling_reason="FEASIBLE",
    )


def _base_unscheduled(task_id: str = "TSK-UNSCH-001") -> UnscheduledTaskResult:
    return UnscheduledTaskResult(
        task_id=task_id,
        task_code=f"CODE-{task_id}",
        mandatory=False,
        reason_codes=[],
        conflicts=[],
        attempted_candidates_count=5,
        diagnostic_message="No feasible slot",
    )


def _base_metrics() -> ScheduleMetrics:
    return ScheduleMetrics(
        total_tasks=2,
        scheduled_tasks=1,
        unscheduled_tasks=1,
        completion_rate=0.5,
        mandatory_tasks=0,
        mandatory_scheduled=0,
        mandatory_unscheduled=0,
        mandatory_completion_rate=1.0,
        total_scheduled_duration_minutes=240,
        total_possession_duration_minutes=270,
        total_priority_score_available=100.0,
        scheduled_priority_score=60.0,
        unscheduled_priority_score=40.0,
        priority_score_capture_rate=0.6,
    )


def _base_schedule(
    snapshot_id: str = "SNAP-001",
    scenario_id: str = "SCN-001",
    scheduled_tasks=None,
    unscheduled_tasks=None,
    status: SchedulerStatus = SchedulerStatus.OPTIMAL,
) -> ScheduleResult:
    return ScheduleResult(
        schedule_id="SCHED-001",
        scheduler_type=SchedulerType.CP_SAT,
        scheduler_version="1.0",
        scenario_id=scenario_id,
        snapshot_id=snapshot_id,
        planning_start=datetime.fromisoformat("2026-10-01T00:00:00+00:00"),
        planning_end=datetime.fromisoformat("2026-10-04T00:00:00+00:00"),
        status=status,
        scheduled_tasks=scheduled_tasks or [_base_task()],
        unscheduled_tasks=unscheduled_tasks or [_base_unscheduled()],
        metrics=_base_metrics(),
        configuration={},
        execution_time_ms=1200.0,
    )


def _base_snapshot(snapshot_id: str = "SNAP-001", scenario_id: str = "SCN-001"):
    """Return a minimal snapshot-like object with only the fields used by compute_schedule_identity."""
    from types import SimpleNamespace
    snap = SimpleNamespace(snapshot_id=snapshot_id, scenario_id=scenario_id)
    return snap


# ---------------------------------------------------------------------------
# Determinism / stability
# ---------------------------------------------------------------------------

def test_fingerprint_is_deterministic() -> None:
    """Same inputs must always produce the same fingerprint."""
    snap = _base_snapshot()
    sched = _base_schedule()
    h1 = IndependentScheduleValidator.compute_schedule_identity(snap, sched)
    h2 = IndependentScheduleValidator.compute_schedule_identity(snap, sched)
    assert h1 == h2, "Fingerprint is non-deterministic"


def test_fingerprint_is_hex_sha256() -> None:
    """Fingerprint must be a 64-character lowercase hex string (SHA-256)."""
    snap = _base_snapshot()
    sched = _base_schedule()
    h = IndependentScheduleValidator.compute_schedule_identity(snap, sched)
    assert len(h) == 64
    assert h == h.lower()
    int(h, 16)  # Should not raise


# ---------------------------------------------------------------------------
# Adversarial: identity-bearing field changes must change fingerprint
# ---------------------------------------------------------------------------

def test_different_task_start_time_changes_fingerprint() -> None:
    """Changing task start time is identity-bearing."""
    snap = _base_snapshot()
    t1 = _base_task()
    t2 = deepcopy(t1)
    t2.interval = _make_interval("2026-10-01T03:00:00+00:00", "2026-10-01T07:00:00+00:00")

    h1 = IndependentScheduleValidator.compute_schedule_identity(snap, _base_schedule(scheduled_tasks=[t1]))
    h2 = IndependentScheduleValidator.compute_schedule_identity(snap, _base_schedule(scheduled_tasks=[t2]))
    assert h1 != h2, "Changing task start time must change fingerprint"


def test_different_affected_sections_changes_fingerprint() -> None:
    """Changing affected sections is identity-bearing."""
    snap = _base_snapshot()
    t1 = _base_task()
    t2 = deepcopy(t1)
    t2.affected_sections = ["SEC-99"]

    h1 = IndependentScheduleValidator.compute_schedule_identity(snap, _base_schedule(scheduled_tasks=[t1]))
    h2 = IndependentScheduleValidator.compute_schedule_identity(snap, _base_schedule(scheduled_tasks=[t2]))
    assert h1 != h2, "Changing affected sections must change fingerprint"


def test_different_assigned_resources_changes_fingerprint() -> None:
    """Changing assigned resources is identity-bearing."""
    snap = _base_snapshot()
    t1 = _base_task()
    t2 = deepcopy(t1)
    t2.assigned_resources = ["RES-DIFFERENT"]

    h1 = IndependentScheduleValidator.compute_schedule_identity(snap, _base_schedule(scheduled_tasks=[t1]))
    h2 = IndependentScheduleValidator.compute_schedule_identity(snap, _base_schedule(scheduled_tasks=[t2]))
    assert h1 != h2, "Changing assigned resources must change fingerprint"


def test_adding_unscheduled_task_changes_fingerprint() -> None:
    """Adding an unscheduled task changes what the schedule decided — identity-bearing."""
    snap = _base_snapshot()
    s1 = _base_schedule(unscheduled_tasks=[])
    s2 = _base_schedule(unscheduled_tasks=[_base_unscheduled("TSK-EXTRA-99")])

    h1 = IndependentScheduleValidator.compute_schedule_identity(snap, s1)
    h2 = IndependentScheduleValidator.compute_schedule_identity(snap, s2)
    assert h1 != h2, "Adding unscheduled task must change fingerprint"


def test_different_unscheduled_task_id_changes_fingerprint() -> None:
    """Swapping which tasks are unscheduled changes the fingerprint."""
    snap = _base_snapshot()
    s1 = _base_schedule(unscheduled_tasks=[_base_unscheduled("TSK-A")])
    s2 = _base_schedule(unscheduled_tasks=[_base_unscheduled("TSK-B")])

    h1 = IndependentScheduleValidator.compute_schedule_identity(snap, s1)
    h2 = IndependentScheduleValidator.compute_schedule_identity(snap, s2)
    assert h1 != h2, "Different unscheduled task IDs must change fingerprint"


def test_different_snapshot_id_changes_fingerprint() -> None:
    """Changing snapshot_id is identity-bearing (different planning context)."""
    snap1 = _base_snapshot(snapshot_id="SNAP-A")
    snap2 = _base_snapshot(snapshot_id="SNAP-B")
    sched = _base_schedule(snapshot_id="SNAP-A")

    h1 = IndependentScheduleValidator.compute_schedule_identity(snap1, sched)

    sched2 = _base_schedule(snapshot_id="SNAP-B")
    h2 = IndependentScheduleValidator.compute_schedule_identity(snap2, sched2)
    assert h1 != h2, "Different snapshot_id must change fingerprint"


def test_different_solver_status_changes_fingerprint() -> None:
    """FEASIBLE vs OPTIMAL solver status is identity-bearing (different solution quality)."""
    snap = _base_snapshot()
    s1 = _base_schedule(status=SchedulerStatus.OPTIMAL)
    s2 = _base_schedule(status=SchedulerStatus.FEASIBLE)

    h1 = IndependentScheduleValidator.compute_schedule_identity(snap, s1)
    h2 = IndependentScheduleValidator.compute_schedule_identity(snap, s2)
    assert h1 != h2, "OPTIMAL vs FEASIBLE solver status must change fingerprint"


# ---------------------------------------------------------------------------
# Non-identity fields must NOT change fingerprint
# ---------------------------------------------------------------------------

def test_execution_time_does_not_change_fingerprint() -> None:
    """Execution time is performance telemetry, not identity-bearing."""
    snap = _base_snapshot()
    s1 = _base_schedule()
    s2 = deepcopy(s1)
    s2.execution_time_ms = 99999.99

    h1 = IndependentScheduleValidator.compute_schedule_identity(snap, s1)
    h2 = IndependentScheduleValidator.compute_schedule_identity(snap, s2)
    assert h1 == h2, "Execution time must NOT affect fingerprint"


def test_priority_score_does_not_change_fingerprint() -> None:
    """Priority scores are derived metrics, not placement decisions."""
    snap = _base_snapshot()
    t1 = _base_task()
    t2 = deepcopy(t1)
    t2.priority_score = 9999.0  # Changed

    h1 = IndependentScheduleValidator.compute_schedule_identity(snap, _base_schedule(scheduled_tasks=[t1]))
    h2 = IndependentScheduleValidator.compute_schedule_identity(snap, _base_schedule(scheduled_tasks=[t2]))
    assert h1 == h2, "Priority score must NOT affect fingerprint"


def test_scheduling_reason_does_not_change_fingerprint() -> None:
    """scheduling_reason is an explanatory annotation, not placement."""
    snap = _base_snapshot()
    t1 = _base_task()
    t2 = deepcopy(t1)
    t2.scheduling_reason = "PRIORITY_OVERRIDE"

    h1 = IndependentScheduleValidator.compute_schedule_identity(snap, _base_schedule(scheduled_tasks=[t1]))
    h2 = IndependentScheduleValidator.compute_schedule_identity(snap, _base_schedule(scheduled_tasks=[t2]))
    assert h1 == h2, "scheduling_reason must NOT affect fingerprint"
