"""Unit tests for FCFS and Priority-Greedy baseline schedulers."""

import pytest
from datetime import datetime, timedelta, timezone

from backend.app.domain.planning_snapshot import PlanningSnapshot
from backend.app.domain.temporal import PlanningHorizon, TimeInterval, TrainPass
from backend.app.domain.scheduling import (
    SchedulerType,
    SchedulerStatus,
    SchedulerConfig,
    PriorityConfig,
)
from backend.app.domain.compatibility import ReasonCode
from backend.app.services.schedulers.fcfs import FCFSScheduler
from backend.app.services.schedulers.priority_greedy import PriorityGreedyScheduler


@pytest.fixture
def base_snapshot():
    now = datetime(2026, 10, 15, 0, 0, tzinfo=timezone.utc)
    horizon = PlanningHorizon(start=now, end=now + timedelta(days=2))

    # A train passes on SEC-01 from 04:00 to 05:00
    tp = TrainPass(
        pass_id="PASS-01",
        train_id="TRN-01",
        train_number="12004",
        section_id="SEC-01",
        interval=TimeInterval(start=now + timedelta(hours=4), end=now + timedelta(hours=5)),
    )

    t1 = {
        "task_id": "TSK-01",
        "task_code": "TC-01",
        "section_id": "SEC-01",
        "priority": "LOW",
        "mandatory": False,
        "window_start": now + timedelta(hours=1),
        "window_end": now + timedelta(hours=8),
        "estimated_duration_minutes": 60,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }
    t2 = {
        "task_id": "TSK-02",
        "task_code": "TC-02",
        "section_id": "SEC-01",
        "priority": "CRITICAL",
        "mandatory": True,
        "window_start": now + timedelta(hours=2),
        "window_end": now + timedelta(hours=8),
        "estimated_duration_minutes": 60,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }

    tasks = [t1, t2]
    tasks_map = {t["task_id"]: t for t in tasks}

    return PlanningSnapshot(
        scenario_id="SCN-TEST",
        snapshot_id="SNAP-TEST-001",
        horizon=horizon,
        tasks=tasks,
        tasks_map=tasks_map,
        work_orders_map={},
        resources=[],
        resources_map={},
        resource_availabilities=[],
        dependencies=[],
        dependencies_by_successor={},
        dependencies_by_predecessor={},
        sections_map={"SEC-01": {"section_id": "SEC-01", "electrified": True}},
        rules_map={},
        train_passes=[tp],
    )


def test_fcfs_orders_by_arrival(base_snapshot):
    scheduler = FCFSScheduler()
    res = scheduler.schedule(base_snapshot)

    assert res.status == SchedulerStatus.COMPLETED
    assert len(res.scheduled_tasks) == 2
    # In FCFS, TSK-01 (window_start 01:00) is considered before TSK-02 (window_start 02:00)
    assert res.scheduled_tasks[0].task_id == "TSK-01"
    assert res.scheduled_tasks[1].task_id == "TSK-02"


def test_priority_greedy_orders_by_priority(base_snapshot):
    scheduler = PriorityGreedyScheduler()
    res = scheduler.schedule(base_snapshot)

    assert res.status == SchedulerStatus.COMPLETED
    assert len(res.scheduled_tasks) == 2
    # In Priority-Greedy, TSK-02 (CRITICAL + mandatory) is considered before TSK-01 (LOW)
    assert res.scheduled_tasks[0].task_id == "TSK-02"
    assert res.scheduled_tasks[1].task_id == "TSK-01"


def test_no_hard_violations_in_placements(base_snapshot):
    scheduler = PriorityGreedyScheduler()
    res = scheduler.schedule(base_snapshot)

    # 1. No overlap between tasks on same section
    p1 = res.scheduled_tasks[0].possession_interval
    p2 = res.scheduled_tasks[1].possession_interval
    assert not p1.overlaps(p2)

    # 2. No overlap with train pass
    tp_int = base_snapshot.train_passes[0].interval
    assert not p1.overlaps(tp_int)
    assert not p2.overlaps(tp_int)


def test_dependency_precedence_enforcement():
    now = datetime(2026, 10, 15, 0, 0, tzinfo=timezone.utc)
    horizon = PlanningHorizon(start=now, end=now + timedelta(days=2))

    t_pred = {
        "task_id": "T-PRED",
        "task_code": "TC-PRED",
        "section_id": "SEC-01",
        "window_start": now + timedelta(hours=1),
        "window_end": now + timedelta(hours=10),
        "estimated_duration_minutes": 60,
    }
    t_succ = {
        "task_id": "T-SUCC",
        "task_code": "TC-SUCC",
        "section_id": "SEC-01",
        "window_start": now + timedelta(hours=1),
        "window_end": now + timedelta(hours=10),
        "estimated_duration_minutes": 60,
    }

    dep = {
        "predecessor_task_id": "T-PRED",
        "successor_task_id": "T-SUCC",
    }

    snapshot = PlanningSnapshot(
        scenario_id="SCN-DEP",
        snapshot_id="SNAP-DEP",
        horizon=horizon,
        tasks=[t_pred, t_succ],
        tasks_map={"T-PRED": t_pred, "T-SUCC": t_succ},
        work_orders_map={},
        resources=[],
        resources_map={},
        resource_availabilities=[],
        dependencies=[dep],
        dependencies_by_successor={"T-SUCC": [dep]},
        dependencies_by_predecessor={"T-PRED": [dep]},
        sections_map={"SEC-01": {"section_id": "SEC-01", "electrified": True}},
        rules_map={},
        train_passes=[],
    )

    scheduler = FCFSScheduler()
    res = scheduler.schedule(snapshot)

    assert len(res.scheduled_tasks) == 2
    pred_res = next(s for s in res.scheduled_tasks if s.task_id == "T-PRED")
    succ_res = next(s for s in res.scheduled_tasks if s.task_id == "T-SUCC")

    # Successor must start after predecessor completes
    assert succ_res.interval.start >= pred_res.interval.end


def test_dependency_cycle_detection():
    now = datetime(2026, 10, 15, 0, 0, tzinfo=timezone.utc)
    horizon = PlanningHorizon(start=now, end=now + timedelta(days=1))

    t1 = {"task_id": "T-1", "window_start": now, "window_end": now + timedelta(hours=5), "estimated_duration_minutes": 60}
    t2 = {"task_id": "T-2", "window_start": now, "window_end": now + timedelta(hours=5), "estimated_duration_minutes": 60}

    # Cycle: T-1 -> T-2 -> T-1
    dep1 = {"predecessor_task_id": "T-1", "successor_task_id": "T-2"}
    dep2 = {"predecessor_task_id": "T-2", "successor_task_id": "T-1"}

    snapshot = PlanningSnapshot(
        scenario_id="SCN-CYCLE",
        snapshot_id="SNAP-CYCLE",
        horizon=horizon,
        tasks=[t1, t2],
        tasks_map={"T-1": t1, "T-2": t2},
        work_orders_map={},
        resources=[],
        resources_map={},
        resource_availabilities=[],
        dependencies=[dep1, dep2],
        dependencies_by_successor={"T-2": [dep1], "T-1": [dep2]},
        dependencies_by_predecessor={"T-1": [dep1], "T-2": [dep2]},
        sections_map={},
        rules_map={},
        train_passes=[],
    )

    scheduler = PriorityGreedyScheduler()
    res = scheduler.schedule(snapshot)

    assert res.status == SchedulerStatus.INVALID_INPUT
    assert len(res.scheduled_tasks) == 0
    assert len(res.unscheduled_tasks) == 2
    assert res.unscheduled_tasks[0].reason_codes == [ReasonCode.DEPENDENCY_NOT_SATISFIED]


def test_immutability_and_repeatability(base_snapshot):
    scheduler = PriorityGreedyScheduler()

    # Pre-snapshot state
    task_keys_before = [list(t.keys()) for t in base_snapshot.tasks]

    res1 = scheduler.schedule(base_snapshot)
    res2 = scheduler.schedule(base_snapshot)

    # Immutability check
    task_keys_after = [list(t.keys()) for t in base_snapshot.tasks]
    assert task_keys_before == task_keys_after

    # Repeatability check
    assert res1.metrics.completion_rate == res2.metrics.completion_rate
    assert res1.metrics.total_scheduled_duration_minutes == res2.metrics.total_scheduled_duration_minutes
    assert [s.interval.start for s in res1.scheduled_tasks] == [s.interval.start for s in res2.scheduled_tasks]
