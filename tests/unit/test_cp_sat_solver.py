"""Unit tests for the CP-SAT solver engine, diagnostics, and deterministic reproducibility."""

import pytest
from datetime import datetime, timedelta, timezone

from backend.app.domain.planning_snapshot import PlanningSnapshot
from backend.app.domain.temporal import PlanningHorizon, TimeInterval, TrainPass
from backend.app.domain.scheduling import (
    SchedulerType,
    SchedulerStatus,
    PriorityConfig,
)
from backend.app.domain.compatibility import ReasonCode
from backend.app.services.optimization.solver_config import OptimizationConfig
from backend.app.services.optimization.cp_sat_solver import CPSATSolver


@pytest.fixture
def complex_snapshot():
    start = datetime(2026, 10, 15, 0, 0, tzinfo=timezone.utc)
    horizon = PlanningHorizon(start=start, end=start + timedelta(hours=48))

    # Two trains passing on SEC-01
    tp1 = TrainPass(
        pass_id="PASS-01",
        train_id="TRN-01",
        train_number="12004",
        section_id="SEC-01",
        interval=TimeInterval(start=start + timedelta(hours=4), end=start + timedelta(hours=6)),
    )
    tp2 = TrainPass(
        pass_id="PASS-02",
        train_id="TRN-02",
        train_number="12005",
        section_id="SEC-01",
        interval=TimeInterval(start=start + timedelta(hours=14), end=start + timedelta(hours=16)),
    )

    t1 = {
        "task_id": "TSK-01",
        "task_code": "TC-01",
        "section_id": "SEC-01",
        "priority": "HIGH",
        "mandatory": True,
        "window_start": start + timedelta(hours=1),
        "window_end": start + timedelta(hours=12),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 15,
        "safety_buffer_after_minutes": 15,
    }
    t2 = {
        "task_id": "TSK-02",
        "task_code": "TC-02",
        "section_id": "SEC-01",
        "priority": "CRITICAL",
        "mandatory": True,
        "window_start": start + timedelta(hours=2),
        "window_end": start + timedelta(hours=24),
        "estimated_duration_minutes": 180,
        "safety_buffer_before_minutes": 15,
        "safety_buffer_after_minutes": 15,
    }
    t3 = {
        "task_id": "TSK-03",
        "task_code": "TC-03",
        "section_id": "SEC-02",
        "priority": "LOW",
        "mandatory": False,
        "window_start": start + timedelta(hours=6),
        "window_end": start + timedelta(hours=36),
        "estimated_duration_minutes": 60,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }

    dep = {
        "predecessor_task_id": "TSK-01",
        "successor_task_id": "TSK-02",
        "dependency_type": "FINISH_TO_START",
        "min_interval_minutes": 0,
    }

    tasks = [t1, t2, t3]
    return PlanningSnapshot(
        scenario_id="SCN-COMPLEX",
        snapshot_id="SNAP-COMPLEX",
        horizon=horizon,
        tasks=tasks,
        tasks_map={t["task_id"]: t for t in tasks},
        work_orders_map={},
        resources=[],
        resources_map={},
        resource_availabilities=[],
        dependencies=[dep],
        dependencies_by_successor={"TSK-02": [dep]},
        dependencies_by_predecessor={"TSK-01": [dep]},
        sections_map={
            "SEC-01": {"section_id": "SEC-01", "electrified": True},
            "SEC-02": {"section_id": "SEC-02", "electrified": True},
        },
        rules_map={},
        train_passes=[tp1, tp2],
    )


def test_cp_sat_solver_deterministic_reproducibility(complex_snapshot):
    """Two executions with seed 0 must yield identical schedules and objectives."""
    cfg = OptimizationConfig(num_search_workers=1, random_seed=0, time_limit_seconds=10.0)
    solver = CPSATSolver(config=cfg)

    res1 = solver.solve(complex_snapshot)
    res2 = solver.solve(complex_snapshot)

    assert res1.status == SchedulerStatus.OPTIMAL
    assert res2.status == SchedulerStatus.OPTIMAL

    assert res1.metrics.scheduled_tasks == res2.metrics.scheduled_tasks
    assert res1.metrics.completion_rate == res2.metrics.completion_rate
    assert res1.metrics.scheduled_priority_score == res2.metrics.scheduled_priority_score

    # Check that exact placement timestamps are identical
    for t1, t2 in zip(res1.scheduled_tasks, res2.scheduled_tasks):
        assert t1.task_id == t2.task_id
        assert t1.interval.start == t2.interval.start
        assert t1.interval.end == t2.interval.end
        assert t1.possession_interval.start == t2.possession_interval.start
        assert t1.possession_interval.end == t2.possession_interval.end


def test_cp_sat_solver_diagnostics(complex_snapshot):
    """Diagnostics payload must contain all required solver telemetry."""
    cfg = OptimizationConfig(num_search_workers=1, random_seed=0, time_limit_seconds=10.0)
    solver = CPSATSolver(config=cfg)
    res = solver.solve(complex_snapshot)

    diag = res.solver_diagnostics
    assert diag is not None
    assert diag["status"] == "OPTIMAL"
    assert "wall_time_seconds" in diag
    assert diag["wall_time_seconds"] > 0
    assert diag["objective_value"] is not None
    assert diag["best_bound"] is not None
    assert diag["optimality_gap"] == 0.0
    assert diag["optimality_gap_percentage"] == 0.0
    assert diag["num_booleans"] > 0
    assert diag["num_integers"] > 0
    assert diag["num_constraints"] > 0
    assert diag["num_intervals"] > 0
    assert diag["num_workers"] == 1
    assert diag["random_seed"] == 0


def test_dependency_cycle_detection():
    """Cyclic dependencies must be caught immediately and return INVALID_INPUT without calling solver."""
    start = datetime(2026, 10, 15, 0, 0, tzinfo=timezone.utc)
    horizon = PlanningHorizon(start=start, end=start + timedelta(hours=24))

    t1 = {
        "task_id": "TSK-C1",
        "task_code": "TC-C1",
        "section_id": "SEC-01",
        "priority": "HIGH",
        "mandatory": True,
        "window_start": start,
        "window_end": start + timedelta(hours=6),
        "estimated_duration_minutes": 60,
    }
    t2 = {
        "task_id": "TSK-C2",
        "task_code": "TC-C2",
        "section_id": "SEC-01",
        "priority": "HIGH",
        "mandatory": True,
        "window_start": start,
        "window_end": start + timedelta(hours=6),
        "estimated_duration_minutes": 60,
    }

    # Circular dependency: C1 -> C2 -> C1
    dep1 = {"predecessor_task_id": "TSK-C1", "successor_task_id": "TSK-C2"}
    dep2 = {"predecessor_task_id": "TSK-C2", "successor_task_id": "TSK-C1"}

    snapshot = PlanningSnapshot(
        scenario_id="SCN-CYCLE",
        snapshot_id="SNAP-CYCLE",
        horizon=horizon,
        tasks=[t1, t2],
        tasks_map={"TSK-C1": t1, "TSK-C2": t2},
        work_orders_map={},
        resources=[],
        resources_map={},
        resource_availabilities=[],
        dependencies=[dep1, dep2],
        dependencies_by_successor={"TSK-C2": [dep1], "TSK-C1": [dep2]},
        dependencies_by_predecessor={"TSK-C1": [dep1], "TSK-C2": [dep2]},
        sections_map={"SEC-01": {"section_id": "SEC-01", "electrified": True}},
        rules_map={},
        train_passes=[],
    )

    solver = CPSATSolver()
    res = solver.solve(snapshot)

    assert res.status == SchedulerStatus.INVALID_INPUT
    assert len(res.scheduled_tasks) == 0
    assert len(res.unscheduled_tasks) == 2
    assert ReasonCode.DEPENDENCY_NOT_SATISFIED in res.unscheduled_tasks[0].reason_codes
    assert "Circular dependency detected" in res.unscheduled_tasks[0].diagnostic_message


def test_independent_metrics_consistency(complex_snapshot):
    """Metrics in ScheduleResult must match placed tasks and snapshot properties."""
    solver = CPSATSolver()
    res = solver.solve(complex_snapshot)

    metrics = res.metrics
    assert metrics.total_tasks == len(complex_snapshot.tasks)
    assert metrics.scheduled_tasks == len(res.scheduled_tasks)
    assert metrics.unscheduled_tasks == len(res.unscheduled_tasks)
    assert metrics.completion_rate == metrics.scheduled_tasks / metrics.total_tasks

    # Verify work duration sum
    expected_work_mins = sum(t.duration_minutes for t in res.scheduled_tasks)
    assert metrics.total_scheduled_duration_minutes == expected_work_mins

    # Verify possession duration sum
    expected_pos_mins = sum(t.possession_interval.duration_minutes for t in res.scheduled_tasks)
    assert metrics.total_possession_duration_minutes == expected_pos_mins
