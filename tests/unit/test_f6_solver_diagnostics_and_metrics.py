"""Unit tests for F6: Solver Diagnostics, Honest Reason Codes, and Completion Metrics.

Verifies:
1. Infeasible models with multiple unplaced tasks do NOT receive blanket INVALID_INTERVAL.
2. Genuinely invalid intervals receive INVALID_INTERVAL; valid tasks in infeasible models receive UNRESOLVED_CONSTRAINT_CONFLICT.
3. Dependency cycles correctly count mandatory tasks and report mandatory_completion_rate == 0.0.
4. Empty mandatory-task sets report 0.0 when 0 tasks are scheduled, and 1.0 only when tasks are scheduled.
5. Solver distinguishes OPTIMAL, FEASIBLE, INFEASIBLE, UNKNOWN, and TIMEOUT outcomes truthfully.
6. Unplaced optional tasks are NOT assigned blanket SECTION_OCCUPANCY_CONFLICT unless verified by post-solve analysis.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from backend.app.domain.planning_snapshot import PlanningSnapshot
from backend.app.domain.temporal import PlanningHorizon, TimeInterval, TrainPass
from backend.app.domain.scheduling import (
    SchedulerType,
    SchedulerStatus,
    ScheduleMetrics,
    ScheduledTaskResult,
    UnscheduledTaskResult,
    PriorityScore,
)
from backend.app.domain.compatibility import ReasonCode
from backend.app.services.metrics_calculator import MetricsCalculator
from backend.app.services.optimization.solver_config import OptimizationConfig
from backend.app.services.optimization.cp_sat_solver import CPSATSolver
from backend.app.services.schedulers.base import BaseScheduler
from backend.app.services.schedulers.fcfs import FCFSScheduler


# =============================================================================
# Helpers and Fixtures
# =============================================================================

@pytest.fixture
def base_horizon():
    start = datetime(2026, 10, 15, 0, 0, tzinfo=timezone.utc)
    return PlanningHorizon(start=start, end=start + timedelta(hours=24))


def _make_snapshot(
    horizon: PlanningHorizon,
    tasks: list,
    dependencies: list = None,
    train_passes: list = None,
    sections: list = None,
) -> PlanningSnapshot:
    tasks_map = {
        (t["task_id"] if isinstance(t, dict) else t.task_id): t
        for t in tasks
    }
    dependencies = dependencies or []
    train_passes = train_passes or []
    sections = sections or ["SEC-01", "SEC-02"]
    sections_map = {
        s: {"section_id": s, "electrified": True} for s in sections
    }

    dep_succ = {}
    dep_pred = {}
    for d in dependencies:
        p = d["predecessor_task_id"] if isinstance(d, dict) else d.predecessor_task_id
        s = d["successor_task_id"] if isinstance(d, dict) else d.successor_task_id
        dep_succ.setdefault(s, []).append(d)
        dep_pred.setdefault(p, []).append(d)

    return PlanningSnapshot(
        scenario_id="SCN-F6-TEST",
        snapshot_id="SNAP-F6-TEST",
        horizon=horizon,
        tasks=tasks,
        tasks_map=tasks_map,
        work_orders_map={},
        resources=[],
        resources_map={},
        resource_availabilities=[],
        dependencies=dependencies,
        dependencies_by_successor=dep_succ,
        dependencies_by_predecessor=dep_pred,
        sections_map=sections_map,
        rules_map={},
        train_passes=train_passes,
    )


# =============================================================================
# Test 1: Infeasible model with multiple tasks does not assign INVALID_INTERVAL
# =============================================================================

def test_infeasible_model_does_not_assign_invalid_interval_to_valid_tasks(base_horizon):
    """When a model is INFEASIBLE under global constraints, tasks with valid intervals

    must receive UNRESOLVED_CONSTRAINT_CONFLICT, NOT INVALID_INTERVAL.
    """
    start = base_horizon.start

    # Two mandatory tasks on the same section whose windows and durations mutually overlap
    # in a way that CP-SAT proves mathematically INFEASIBLE (e.g. 2 x 12h tasks + buffers in 12h window)
    t1 = {
        "task_id": "TSK-INF-1",
        "task_code": "TC-INF-1",
        "section_id": "SEC-01",
        "priority": "HIGH",
        "mandatory": True,
        "window_start": start + timedelta(hours=2),
        "window_end": start + timedelta(hours=14),
        "estimated_duration_minutes": 600,  # 10 hours
        "safety_buffer_before_minutes": 60,
        "safety_buffer_after_minutes": 60,
    }
    t2 = {
        "task_id": "TSK-INF-2",
        "task_code": "TC-INF-2",
        "section_id": "SEC-01",
        "priority": "CRITICAL",
        "mandatory": True,
        "window_start": start + timedelta(hours=2),
        "window_end": start + timedelta(hours=14),
        "estimated_duration_minutes": 600,  # 10 hours
        "safety_buffer_before_minutes": 60,
        "safety_buffer_after_minutes": 60,
    }
    # Both need 12h possession within a 12h window on the same single track section -> INFEASIBLE

    snapshot = _make_snapshot(base_horizon, [t1, t2])
    solver = CPSATSolver()
    res = solver.solve(snapshot)

    assert res.status == SchedulerStatus.INFEASIBLE
    assert len(res.scheduled_tasks) == 0
    assert len(res.unscheduled_tasks) == 2

    for ut in res.unscheduled_tasks:
        assert ReasonCode.INVALID_INTERVAL not in ut.reason_codes, (
            f"Task {ut.task_id} had valid intervals; must NOT receive INVALID_INTERVAL."
        )
        assert ReasonCode.UNRESOLVED_CONSTRAINT_CONFLICT in ut.reason_codes
        assert "INFEASIBLE" in ut.diagnostic_message

    # Decision traces must truthfully report INFEASIBLE
    for dt in res.decision_trace:
        assert dt.status == "UNSCHEDULED"
        assert dt.primary_reason == "INFEASIBLE"

    # Metrics must report 0.0 mandatory completion rate when 0 tasks are scheduled
    assert res.metrics.scheduled_tasks == 0
    assert res.metrics.mandatory_tasks == 2
    assert res.metrics.mandatory_scheduled == 0
    assert res.metrics.mandatory_completion_rate == 0.0


# =============================================================================
# Test 2: Genuinely invalid intervals vs. general infeasibility
# =============================================================================

def test_genuinely_invalid_intervals_vs_general_infeasibility(base_horizon):
    """A task with an invalid interval (duration <= 0 or start >= end) receives INVALID_INTERVAL,

    while a task with a valid interval in the same infeasible model receives UNRESOLVED_CONSTRAINT_CONFLICT.
    """
    start = base_horizon.start

    # T1 has duration <= 0 (genuinely invalid interval)
    t1_bad_dur = {
        "task_id": "TSK-BAD-DUR",
        "task_code": "TC-BAD-DUR",
        "section_id": "SEC-01",
        "priority": "HIGH",
        "mandatory": True,
        "window_start": start + timedelta(hours=2),
        "window_end": start + timedelta(hours=10),
        "estimated_duration_minutes": 0,  # Invalid duration!
    }

    # T2 has duration exceeding its window (TASK_WINDOW_CONFLICT)
    t2_bad_win = {
        "task_id": "TSK-BAD-WIN",
        "task_code": "TC-BAD-WIN",
        "section_id": "SEC-01",
        "priority": "HIGH",
        "mandatory": True,
        "window_start": start + timedelta(hours=2),
        "window_end": start + timedelta(hours=4),  # 2h window
        "estimated_duration_minutes": 240,  # 4h duration > 2h window!
    }

    # T3 has a completely valid interval and window
    t3_valid = {
        "task_id": "TSK-VALID",
        "task_code": "TC-VALID",
        "section_id": "SEC-01",
        "priority": "HIGH",
        "mandatory": True,
        "window_start": start + timedelta(hours=5),
        "window_end": start + timedelta(hours=15),
        "estimated_duration_minutes": 60,
    }

    snapshot = _make_snapshot(base_horizon, [t1_bad_dur, t2_bad_win, t3_valid])
    solver = CPSATSolver()
    res = solver.solve(snapshot)

    assert res.status in (SchedulerStatus.INFEASIBLE, SchedulerStatus.INVALID_INPUT)

    unscheduled_by_id = {ut.task_id: ut for ut in res.unscheduled_tasks}

    # T1 must receive INVALID_INTERVAL
    assert ReasonCode.INVALID_INTERVAL in unscheduled_by_id["TSK-BAD-DUR"].reason_codes

    # T2 must receive TASK_WINDOW_CONFLICT
    assert ReasonCode.TASK_WINDOW_CONFLICT in unscheduled_by_id["TSK-BAD-WIN"].reason_codes

    # T3 (valid interval) must NOT receive INVALID_INTERVAL
    assert ReasonCode.INVALID_INTERVAL not in unscheduled_by_id["TSK-VALID"].reason_codes
    assert ReasonCode.UNRESOLVED_CONSTRAINT_CONFLICT in unscheduled_by_id["TSK-VALID"].reason_codes


# =============================================================================
# Test 3: Zero scheduled tasks and dependency cycle detection
# =============================================================================

def test_dependency_cycle_detection_mandatory_completion_rate(base_horizon):
    """When a dependency cycle is detected, zero tasks are scheduled.

    The mandatory completion rate must be 0.0, NOT 1.0!
    """
    start = base_horizon.start

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
    t3_optional = {
        "task_id": "TSK-C3-OPT",
        "task_code": "TC-C3-OPT",
        "section_id": "SEC-02",
        "priority": "LOW",
        "mandatory": False,
        "window_start": start,
        "window_end": start + timedelta(hours=6),
        "estimated_duration_minutes": 60,
    }

    # Circular dependency: C1 -> C2 -> C1
    dep1 = {"predecessor_task_id": "TSK-C1", "successor_task_id": "TSK-C2"}
    dep2 = {"predecessor_task_id": "TSK-C2", "successor_task_id": "TSK-C1"}

    snapshot = _make_snapshot(
        base_horizon,
        [t1, t2, t3_optional],
        dependencies=[dep1, dep2],
    )

    # Test in CPSATSolver
    solver = CPSATSolver()
    res_cpsat = solver.solve(snapshot)

    assert res_cpsat.status == SchedulerStatus.INVALID_INPUT
    assert len(res_cpsat.scheduled_tasks) == 0
    assert len(res_cpsat.unscheduled_tasks) == 3
    assert res_cpsat.metrics.total_tasks == 3
    assert res_cpsat.metrics.scheduled_tasks == 0
    assert res_cpsat.metrics.mandatory_tasks == 2  # t1 and t2
    assert res_cpsat.metrics.mandatory_scheduled == 0
    assert res_cpsat.metrics.mandatory_unscheduled == 2
    assert res_cpsat.metrics.completion_rate == 0.0
    assert res_cpsat.metrics.mandatory_completion_rate == 0.0, (
        "Zero scheduled tasks must NEVER report 1.0 (100%) mandatory completion!"
    )

    # Test in FCFSScheduler (BaseDeterministicScheduler)
    fcfs = FCFSScheduler()
    res_fcfs = fcfs.schedule(snapshot)

    assert res_fcfs.status == SchedulerStatus.INVALID_INPUT
    assert res_fcfs.metrics.mandatory_tasks == 2
    assert res_fcfs.metrics.mandatory_scheduled == 0
    assert res_fcfs.metrics.mandatory_completion_rate == 0.0


# =============================================================================
# Test 4: Empty mandatory-task sets and denominator semantics
# =============================================================================

def test_empty_mandatory_task_sets_metrics_semantics(base_horizon):
    """Explicitly verify denominator semantics for scenarios with zero mandatory tasks.

    - 0 scheduled tasks -> mandatory_completion_rate == 0.0
    - >0 scheduled tasks -> mandatory_completion_rate == 1.0 (vacuously satisfied)
    """
    start = base_horizon.start

    t_opt1 = {
        "task_id": "TSK-OPT-1",
        "task_code": "TC-OPT-1",
        "section_id": "SEC-01",
        "mandatory": False,
        "window_start": start,
        "window_end": start + timedelta(hours=6),
        "estimated_duration_minutes": 60,
    }
    t_opt2 = {
        "task_id": "TSK-OPT-2",
        "task_code": "TC-OPT-2",
        "section_id": "SEC-01",
        "mandatory": False,
        "window_start": start,
        "window_end": start + timedelta(hours=6),
        "estimated_duration_minutes": 60,
    }

    snapshot = _make_snapshot(base_horizon, [t_opt1, t_opt2])

    # Case A: 0 scheduled tasks (e.g. unscheduled run)
    unscheduled = [
        UnscheduledTaskResult(
            task_id="TSK-OPT-1",
            task_code="TC-OPT-1",
            mandatory=False,
            reason_codes=[ReasonCode.UNRESOLVED_CONSTRAINT_CONFLICT],
            conflicts=[],
            attempted_candidates_count=0,
            diagnostic_message="Unplaced.",
        ),
        UnscheduledTaskResult(
            task_id="TSK-OPT-2",
            task_code="TC-OPT-2",
            mandatory=False,
            reason_codes=[ReasonCode.UNRESOLVED_CONSTRAINT_CONFLICT],
            conflicts=[],
            attempted_candidates_count=0,
            diagnostic_message="Unplaced.",
        ),
    ]

    metrics_zero = MetricsCalculator.calculate(
        scheduled_tasks=[],
        unscheduled_tasks=unscheduled,
        scores_map={},
        snapshot=snapshot,
    )

    assert metrics_zero.mandatory_tasks == 0
    assert metrics_zero.scheduled_tasks == 0
    assert metrics_zero.completion_rate == 0.0
    assert metrics_zero.mandatory_completion_rate == 0.0, (
        "Zero scheduled tasks must result in 0.0 mandatory completion rate even if 0 mandatory tasks."
    )

    # Case B: 1 scheduled task
    scheduled = [
        ScheduledTaskResult(
            task_id="TSK-OPT-1",
            task_code="TC-OPT-1",
            interval=TimeInterval(start=start, end=start + timedelta(hours=1)),
            possession_interval=TimeInterval(start=start, end=start + timedelta(hours=1)),
            duration_minutes=60,
            affected_sections=["SEC-01"],
            assigned_resources=[],
            sequence_order=1,
            scheduling_reason="FEASIBLE",
        )
    ]
    unscheduled_one = [unscheduled[1]]

    metrics_one = MetricsCalculator.calculate(
        scheduled_tasks=scheduled,
        unscheduled_tasks=unscheduled_one,
        scores_map={},
        snapshot=snapshot,
    )

    assert metrics_one.mandatory_tasks == 0
    assert metrics_one.scheduled_tasks == 1
    assert metrics_one.completion_rate == 0.5
    assert metrics_one.mandatory_completion_rate == 1.0, (
        "When work is scheduled and 0 mandatory tasks were required, mandatory completion is 1.0."
    )


# =============================================================================
# Test 5: Solver status distinctions (OPTIMAL, FEASIBLE, INFEASIBLE, UNKNOWN, TIMEOUT)
# =============================================================================

def test_solver_status_distinctions_optimal_and_timeout(base_horizon):
    """Solver must truthfully distinguish OPTIMAL from timeout and UNKNOWN."""
    start = base_horizon.start

    t1 = {
        "task_id": "TSK-S1",
        "task_code": "TC-S1",
        "section_id": "SEC-01",
        "priority": "HIGH",
        "mandatory": True,
        "window_start": start + timedelta(hours=1),
        "window_end": start + timedelta(hours=6),
        "estimated_duration_minutes": 60,
    }

    snapshot = _make_snapshot(base_horizon, [t1])

    # 1. OPTIMAL solve
    solver_opt = CPSATSolver()
    res_opt = solver_opt.solve(snapshot)
    assert res_opt.status == SchedulerStatus.OPTIMAL
    assert res_opt.solver_diagnostics["status"] == "OPTIMAL"
    assert res_opt.solver_diagnostics["optimality_gap_percentage"] == 0.0

    # 2. Simulated TIMEOUT / UNKNOWN
    # Using mock to simulate cp_model.UNKNOWN with elapsed wall time >= time limit
    with patch("ortools.sat.python.cp_model.CpSolver.Solve") as mock_solve, \
         patch("ortools.sat.python.cp_model.CpSolver.WallTime") as mock_wall:
        from ortools.sat.python import cp_model
        mock_solve.return_value = cp_model.UNKNOWN
        mock_wall.return_value = 5.0  # limit is 5.0s

        cfg_timeout = OptimizationConfig(time_limit_seconds=5.0)
        solver_timeout = CPSATSolver(config=cfg_timeout)
        res_timeout = solver_timeout.solve(snapshot)

        assert res_timeout.status == SchedulerStatus.UNKNOWN
        assert res_timeout.solver_diagnostics["status"] == "TIMEOUT"
        assert len(res_timeout.unscheduled_tasks) == 1
        ut = res_timeout.unscheduled_tasks[0]
        assert ReasonCode.UNRESOLVED_CONSTRAINT_CONFLICT in ut.reason_codes
        assert ReasonCode.INVALID_INTERVAL not in ut.reason_codes
        assert "timed out" in ut.diagnostic_message
        assert res_timeout.decision_trace[0].primary_reason == "TIMEOUT"


# =============================================================================
# Test 6: Unplaced optional task: no blanket SECTION_OCCUPANCY_CONFLICT
# =============================================================================

def test_unplaced_optional_task_no_blanket_section_conflict(base_horizon):
    """When an optional task is unplaced, it must NOT receive SECTION_OCCUPANCY_CONFLICT

    unless a real section conflict was established against existing placements.
    """
    start = base_horizon.start

    # Task 1 on SEC-01 is scheduled
    t1 = {
        "task_id": "TSK-01",
        "task_code": "TC-01",
        "section_id": "SEC-01",
        "priority": "CRITICAL",
        "mandatory": True,
        "window_start": start + timedelta(hours=1),
        "window_end": start + timedelta(hours=6),
        "estimated_duration_minutes": 60,
    }

    # Task 2 is on SEC-02 (completely empty section with NO trains and NO other tasks)
    # It is optional (mandatory=False)
    t2_opt = {
        "task_id": "TSK-02-OPT",
        "task_code": "TC-02-OPT",
        "section_id": "SEC-02",
        "priority": "LOW",
        "mandatory": False,
        "window_start": start + timedelta(hours=1),
        "window_end": start + timedelta(hours=6),
        "estimated_duration_minutes": 60,
    }

    # Solve with both tasks: both can be placed
    snapshot = _make_snapshot(base_horizon, [t1, t2_opt])
    solver = CPSATSolver()
    res = solver.solve(snapshot)

    # In this unconstrained scenario, both are scheduled
    assert len(res.scheduled_tasks) == 2

    # Now simulate a scenario where presence of t2_opt is forced to 0
    # (e.g. excluded by solver objective or budget)
    with patch("ortools.sat.python.cp_model.CpSolver.Value") as mock_val:
        def value_side_effect(var):
            # If checking presence for TSK-02-OPT, simulate 0 (unplaced)
            name = str(var)
            if "presence_TSK-02-OPT" in name:
                return 0
            if "presence_TSK-01" in name:
                return 1
            if "start_" in name or "pos_start_" in name:
                return 60
            if "end_" in name or "pos_end_" in name:
                return 120
            return 1

        mock_val.side_effect = value_side_effect
        res_partial = solver.solve(snapshot)

        assert len(res_partial.scheduled_tasks) == 1
        assert len(res_partial.unscheduled_tasks) == 1

        unplaced = res_partial.unscheduled_tasks[0]
        assert unplaced.task_id == "TSK-02-OPT"

        # TSK-02-OPT is on SEC-02 which has NO tasks scheduled!
        # It must NOT receive SECTION_OCCUPANCY_CONFLICT!
        assert ReasonCode.SECTION_OCCUPANCY_CONFLICT not in unplaced.reason_codes, (
            "TSK-02-OPT is on SEC-02 with no track contention; must NOT receive blanket SECTION_OCCUPANCY_CONFLICT!"
        )
        assert ReasonCode.UNRESOLVED_CONSTRAINT_CONFLICT in unplaced.reason_codes
        assert "excluded by global optimization objective" in unplaced.diagnostic_message
        assert res_partial.decision_trace[1].primary_reason == "EXCLUDED_BY_OBJECTIVE"


# =============================================================================
# Test 7: Unplaced task WITH real section occupancy conflict
# =============================================================================

def test_unplaced_optional_task_with_real_section_conflict(base_horizon):
    """When an optional task genuinely conflicts with a scheduled task on the same section

    and has no alternative feasible placement window, it receives SECTION_OCCUPANCY_CONFLICT
    with verified conflicts attached.
    """
    start = base_horizon.start

    # T1 occupies SEC-01 from hour 2 to hour 8
    t1 = {
        "task_id": "TSK-SEC-1",
        "task_code": "TC-SEC-1",
        "section_id": "SEC-01",
        "priority": "CRITICAL",
        "mandatory": True,
        "window_start": start + timedelta(hours=2),
        "window_end": start + timedelta(hours=8),
        "estimated_duration_minutes": 360,  # 6h
        "safety_buffer_before_minutes": 15,
        "safety_buffer_after_minutes": 15,
    }

    # T2 is an optional task on SEC-01 whose window is strictly inside T1's possession: hours 3 to 5
    t2_opt = {
        "task_id": "TSK-SEC-2-OPT",
        "task_code": "TC-SEC-2-OPT",
        "section_id": "SEC-01",
        "priority": "LOW",
        "mandatory": False,
        "window_start": start + timedelta(hours=3),
        "window_end": start + timedelta(hours=5),  # 2h window
        "estimated_duration_minutes": 60,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
    }

    snapshot = _make_snapshot(base_horizon, [t1, t2_opt])
    solver = CPSATSolver()
    res = solver.solve(snapshot)

    assert res.status in (SchedulerStatus.OPTIMAL, SchedulerStatus.FEASIBLE)
    assert len(res.scheduled_tasks) == 1
    assert res.scheduled_tasks[0].task_id == "TSK-SEC-1"

    assert len(res.unscheduled_tasks) == 1
    unplaced = res.unscheduled_tasks[0]
    assert unplaced.task_id == "TSK-SEC-2-OPT"

    # Because TSK-SEC-2-OPT was physically evaluated across all candidate points on SEC-01
    # and genuinely collided with TSK-SEC-1's possession, it must receive SECTION_OCCUPANCY_CONFLICT
    assert ReasonCode.SECTION_OCCUPANCY_CONFLICT in unplaced.reason_codes
    assert len(unplaced.conflicts) > 0
    assert any(c.conflicting_entity_id == "TSK-SEC-1" for c in unplaced.conflicts)
