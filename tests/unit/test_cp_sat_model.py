"""Unit tests for the CP-SAT mathematical model builder and feasibility semantics."""

import pytest
from datetime import datetime, timedelta, timezone

from backend.app.domain.planning_snapshot import PlanningSnapshot
from backend.app.domain.temporal import PlanningHorizon, TimeInterval, TrainPass
from backend.app.domain.scheduling import (
    SchedulerStatus,
    PriorityConfig,
)
from backend.app.domain.compatibility import ReasonCode
from backend.app.services.priority_scorer import PriorityScorer
from backend.app.services.optimization.solver_config import OptimizationConfig
from backend.app.services.optimization.cp_sat_model import CPSATModelBuilder
from backend.app.services.optimization.cp_sat_solver import CPSATSolver


@pytest.fixture
def base_horizon():
    start = datetime(2026, 10, 15, 0, 0, tzinfo=timezone.utc)
    return PlanningHorizon(start=start, end=start + timedelta(hours=24))


def test_single_task_optimal_placement(base_horizon):
    """A single flexible task in an open horizon should solve to OPTIMAL."""
    t1 = {
        "task_id": "TSK-01",
        "task_code": "TC-01",
        "section_id": "SEC-01",
        "priority": "HIGH",
        "mandatory": False,
        "window_start": base_horizon.start + timedelta(hours=2),
        "window_end": base_horizon.start + timedelta(hours=6),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 15,
        "safety_buffer_after_minutes": 15,
    }
    snapshot = PlanningSnapshot(
        scenario_id="SCN-SINGLE",
        snapshot_id="SNAP-SINGLE",
        horizon=base_horizon,
        tasks=[t1],
        tasks_map={"TSK-01": t1},
        work_orders_map={},
        resources=[],
        resources_map={},
        resource_availabilities=[],
        dependencies=[],
        dependencies_by_successor={},
        dependencies_by_predecessor={},
        sections_map={"SEC-01": {"section_id": "SEC-01", "electrified": True}},
        rules_map={},
        train_passes=[],
    )

    solver = CPSATSolver()
    result = solver.solve(snapshot)

    assert result.status == SchedulerStatus.OPTIMAL
    assert len(result.scheduled_tasks) == 1
    assert result.scheduled_tasks[0].task_id == "TSK-01"
    assert result.metrics.completion_rate == 1.0

    # Verify possession envelope includes safety buffers
    work_start = result.scheduled_tasks[0].interval.start
    work_end = result.scheduled_tasks[0].interval.end
    pos_start = result.scheduled_tasks[0].possession_interval.start
    pos_end = result.scheduled_tasks[0].possession_interval.end

    assert pos_start == work_start - timedelta(minutes=15)
    assert pos_end == work_end + timedelta(minutes=15)
    assert (work_end - work_start).total_seconds() == 120 * 60


def test_conflicting_mandatory_tasks_infeasible(base_horizon):
    """Two mandatory tasks demanding the same section during a tight window proves INFEASIBLE."""
    # Window is 1 hour (60 min). Both tasks take 40 min work + 15 min buffer before & after = 70 min possession.
    # Neither fits together, both are mandatory -> Model is mathematically INFEASIBLE.
    t1 = {
        "task_id": "TSK-M1",
        "task_code": "TC-M1",
        "section_id": "SEC-01",
        "priority": "CRITICAL",
        "mandatory": True,
        "window_start": base_horizon.start + timedelta(hours=2),
        "window_end": base_horizon.start + timedelta(hours=3),
        "estimated_duration_minutes": 40,
        "safety_buffer_before_minutes": 15,
        "safety_buffer_after_minutes": 15,
    }
    t2 = {
        "task_id": "TSK-M2",
        "task_code": "TC-M2",
        "section_id": "SEC-01",
        "priority": "CRITICAL",
        "mandatory": True,
        "window_start": base_horizon.start + timedelta(hours=2),
        "window_end": base_horizon.start + timedelta(hours=3),
        "estimated_duration_minutes": 40,
        "safety_buffer_before_minutes": 15,
        "safety_buffer_after_minutes": 15,
    }
    snapshot = PlanningSnapshot(
        scenario_id="SCN-INFEASIBLE",
        snapshot_id="SNAP-INFEASIBLE",
        horizon=base_horizon,
        tasks=[t1, t2],
        tasks_map={"TSK-M1": t1, "TSK-M2": t2},
        work_orders_map={},
        resources=[],
        resources_map={},
        resource_availabilities=[],
        dependencies=[],
        dependencies_by_successor={},
        dependencies_by_predecessor={},
        sections_map={"SEC-01": {"section_id": "SEC-01", "electrified": True}},
        rules_map={},
        train_passes=[],
    )

    solver = CPSATSolver()
    result = solver.solve(snapshot)

    assert result.status == SchedulerStatus.INFEASIBLE
    assert len(result.scheduled_tasks) == 0
    assert len(result.unscheduled_tasks) == 2
    assert result.metrics.completion_rate == 0.0
    assert result.solver_diagnostics["status"] == "INFEASIBLE"


def test_priority_selection_under_contention(base_horizon):
    """When only one task can fit on a track, CP-SAT selects the higher priority task."""
    # Window is 2 hours. Both tasks take 90 minutes + 15 min buffer = 120 mins possession.
    # Only one can fit.
    t_high = {
        "task_id": "TSK-HIGH",
        "task_code": "TC-HIGH",
        "section_id": "SEC-01",
        "priority": "CRITICAL",
        "mandatory": False,
        "window_start": base_horizon.start + timedelta(hours=1),
        "window_end": base_horizon.start + timedelta(hours=3),
        "estimated_duration_minutes": 90,
        "safety_buffer_before_minutes": 15,
        "safety_buffer_after_minutes": 15,
    }
    t_low = {
        "task_id": "TSK-LOW",
        "task_code": "TC-LOW",
        "section_id": "SEC-01",
        "priority": "LOW",
        "mandatory": False,
        "window_start": base_horizon.start + timedelta(hours=1),
        "window_end": base_horizon.start + timedelta(hours=3),
        "estimated_duration_minutes": 90,
        "safety_buffer_before_minutes": 15,
        "safety_buffer_after_minutes": 15,
    }
    snapshot = PlanningSnapshot(
        scenario_id="SCN-PRIORITY",
        snapshot_id="SNAP-PRIORITY",
        horizon=base_horizon,
        tasks=[t_low, t_high],  # t_low presented first
        tasks_map={"TSK-HIGH": t_high, "TSK-LOW": t_low},
        work_orders_map={},
        resources=[],
        resources_map={},
        resource_availabilities=[],
        dependencies=[],
        dependencies_by_successor={},
        dependencies_by_predecessor={},
        sections_map={"SEC-01": {"section_id": "SEC-01", "electrified": True}},
        rules_map={},
        train_passes=[],
    )

    solver = CPSATSolver()
    result = solver.solve(snapshot)

    assert result.status == SchedulerStatus.OPTIMAL
    assert len(result.scheduled_tasks) == 1
    # Global optimizer MUST choose TSK-HIGH over TSK-LOW despite input order
    assert result.scheduled_tasks[0].task_id == "TSK-HIGH"
    assert result.unscheduled_tasks[0].task_id == "TSK-LOW"


def test_train_conflict_avoidance(base_horizon):
    """Task possession window must strictly avoid fixed train passes."""
    # Train occupies SEC-01 from 03:00 to 05:00
    tp = TrainPass(
        pass_id="PASS-01",
        train_id="TRN-01",
        train_number="12004",
        section_id="SEC-01",
        interval=TimeInterval(
            start=base_horizon.start + timedelta(hours=3),
            end=base_horizon.start + timedelta(hours=5),
        ),
    )
    # Task window is 01:00 to 07:00, duration 60 mins, buffers 15 mins
    t1 = {
        "task_id": "TSK-TRAIN",
        "task_code": "TC-TRAIN",
        "section_id": "SEC-01",
        "priority": "MEDIUM",
        "mandatory": True,
        "window_start": base_horizon.start + timedelta(hours=1),
        "window_end": base_horizon.start + timedelta(hours=7),
        "estimated_duration_minutes": 60,
        "safety_buffer_before_minutes": 15,
        "safety_buffer_after_minutes": 15,
    }
    snapshot = PlanningSnapshot(
        scenario_id="SCN-TRAIN",
        snapshot_id="SNAP-TRAIN",
        horizon=base_horizon,
        tasks=[t1],
        tasks_map={"TSK-TRAIN": t1},
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

    solver = CPSATSolver()
    result = solver.solve(snapshot)

    assert result.status == SchedulerStatus.OPTIMAL
    assert len(result.scheduled_tasks) == 1
    placed = result.scheduled_tasks[0]

    # Possession interval [pos_start, pos_end)
    # Train interval is [03:00, 05:00)
    train_start = base_horizon.start + timedelta(hours=3)
    train_end = base_horizon.start + timedelta(hours=5)

    # Must be either strictly before (pos_end <= train_start) OR strictly after (pos_start >= train_end)
    assert placed.possession_interval.end <= train_start or placed.possession_interval.start >= train_end


def test_resource_exclusivity(base_horizon):
    """Two tasks requiring the exact same machine on different sections cannot overlap."""
    t1 = {
        "task_id": "TSK-RES1",
        "task_code": "TC-RES1",
        "section_id": "SEC-01",
        "required_resource_ids": ["RES-TAMPER-01"],
        "priority": "HIGH",
        "mandatory": True,
        "window_start": base_horizon.start + timedelta(hours=1),
        "window_end": base_horizon.start + timedelta(hours=6),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 0,
        "safety_buffer_after_minutes": 0,
    }
    t2 = {
        "task_id": "TSK-RES2",
        "task_code": "TC-RES2",
        "section_id": "SEC-02",  # Different section!
        "required_resource_ids": ["RES-TAMPER-01"],  # Same resource!
        "priority": "HIGH",
        "mandatory": True,
        "window_start": base_horizon.start + timedelta(hours=1),
        "window_end": base_horizon.start + timedelta(hours=6),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 0,
        "safety_buffer_after_minutes": 0,
    }
    res = {
        "resource_id": "RES-TAMPER-01",
        "resource_type": "MACHINE",
        "name": "Heavy Tamping Machine 01",
    }
    snapshot = PlanningSnapshot(
        scenario_id="SCN-RES",
        snapshot_id="SNAP-RES",
        horizon=base_horizon,
        tasks=[t1, t2],
        tasks_map={"TSK-RES1": t1, "TSK-RES2": t2},
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
        train_passes=[],
    )

    solver = CPSATSolver()
    result = solver.solve(snapshot)

    assert result.status == SchedulerStatus.OPTIMAL
    assert len(result.scheduled_tasks) == 2

    t1_res = next(st for st in result.scheduled_tasks if st.task_id == "TSK-RES1")
    t2_res = next(st for st in result.scheduled_tasks if st.task_id == "TSK-RES2")

    # Half-open no-overlap: either t1 ends before t2 starts or t2 ends before t1 starts
    assert t1_res.interval.end <= t2_res.interval.start or t2_res.interval.end <= t1_res.interval.start


def test_finish_to_start_dependency(base_horizon):
    """Predecessor must finish before successor starts, and successor requires predecessor."""
    t_pred = {
        "task_id": "TSK-PRED",
        "task_code": "TC-PRED",
        "section_id": "SEC-01",
        "priority": "MEDIUM",
        "mandatory": False,
        "window_start": base_horizon.start + timedelta(hours=1),
        "window_end": base_horizon.start + timedelta(hours=8),
        "estimated_duration_minutes": 60,
        "safety_buffer_before_minutes": 0,
        "safety_buffer_after_minutes": 0,
    }
    t_succ = {
        "task_id": "TSK-SUCC",
        "task_code": "TC-SUCC",
        "section_id": "SEC-01",
        "priority": "HIGH",
        "mandatory": False,
        "window_start": base_horizon.start + timedelta(hours=1),
        "window_end": base_horizon.start + timedelta(hours=8),
        "estimated_duration_minutes": 60,
        "safety_buffer_before_minutes": 0,
        "safety_buffer_after_minutes": 0,
    }
    dep = {
        "predecessor_task_id": "TSK-PRED",
        "successor_task_id": "TSK-SUCC",
        "dependency_type": "FINISH_TO_START",
        "min_interval_minutes": 30,  # 30 min cooling/transit buffer
    }
    snapshot = PlanningSnapshot(
        scenario_id="SCN-DEP",
        snapshot_id="SNAP-DEP",
        horizon=base_horizon,
        tasks=[t_pred, t_succ],
        tasks_map={"TSK-PRED": t_pred, "TSK-SUCC": t_succ},
        work_orders_map={},
        resources=[],
        resources_map={},
        resource_availabilities=[],
        dependencies=[dep],
        dependencies_by_successor={"TSK-SUCC": [dep]},
        dependencies_by_predecessor={"TSK-PRED": [dep]},
        sections_map={"SEC-01": {"section_id": "SEC-01", "electrified": True}},
        rules_map={},
        train_passes=[],
    )

    solver = CPSATSolver()
    result = solver.solve(snapshot)

    assert result.status == SchedulerStatus.OPTIMAL
    assert len(result.scheduled_tasks) == 2

    p_res = next(st for st in result.scheduled_tasks if st.task_id == "TSK-PRED")
    s_res = next(st for st in result.scheduled_tasks if st.task_id == "TSK-SUCC")

    # Successor start >= predecessor end + 30 min
    assert s_res.interval.start >= p_res.interval.end + timedelta(minutes=30)


def test_half_open_exact_boundary_touching(base_horizon):
    """Under [start, end), Task 1 possession ending at T and Task 2 starting at T is valid with zero slack."""
    # Window 4 hours (240 min).
    # Task 1: 120 min duration, 0 buffer.
    # Task 2: 120 min duration, 0 buffer.
    # Exactly fits into 240 min if they touch end-to-start.
    t1 = {
        "task_id": "TSK-TOUCH1",
        "task_code": "TC-TOUCH1",
        "section_id": "SEC-01",
        "priority": "HIGH",
        "mandatory": True,
        "window_start": base_horizon.start,
        "window_end": base_horizon.start + timedelta(minutes=240),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 0,
        "safety_buffer_after_minutes": 0,
    }
    t2 = {
        "task_id": "TSK-TOUCH2",
        "task_code": "TC-TOUCH2",
        "section_id": "SEC-01",
        "priority": "HIGH",
        "mandatory": True,
        "window_start": base_horizon.start,
        "window_end": base_horizon.start + timedelta(minutes=240),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 0,
        "safety_buffer_after_minutes": 0,
    }
    snapshot = PlanningSnapshot(
        scenario_id="SCN-TOUCH",
        snapshot_id="SNAP-TOUCH",
        horizon=base_horizon,
        tasks=[t1, t2],
        tasks_map={"TSK-TOUCH1": t1, "TSK-TOUCH2": t2},
        work_orders_map={},
        resources=[],
        resources_map={},
        resource_availabilities=[],
        dependencies=[],
        dependencies_by_successor={},
        dependencies_by_predecessor={},
        sections_map={"SEC-01": {"section_id": "SEC-01", "electrified": True}},
        rules_map={},
        train_passes=[],
    )

    solver = CPSATSolver()
    result = solver.solve(snapshot)

    assert result.status == SchedulerStatus.OPTIMAL
    assert len(result.scheduled_tasks) == 2

    res1 = next(st for st in result.scheduled_tasks if st.task_id == "TSK-TOUCH1")
    res2 = next(st for st in result.scheduled_tasks if st.task_id == "TSK-TOUCH2")

    # One must end exactly when the other starts
    touch_point_valid = (res1.interval.end == res2.interval.start) or (res2.interval.end == res1.interval.start)
    assert touch_point_valid, f"Expected exact boundary touch: T1={res1.interval.start}..{res1.interval.end}, T2={res2.interval.start}..{res2.interval.end}"


def test_unelectrified_power_block_rejection(base_horizon):
    """Task requiring a power block on an unelectrified section is rejected."""
    t1 = {
        "task_id": "TSK-OHE",
        "task_code": "TC-OHE",
        "section_id": "SEC-UNELEC",
        "requires_power_block": True,
        "priority": "HIGH",
        "mandatory": False,
        "window_start": base_horizon.start,
        "window_end": base_horizon.start + timedelta(hours=6),
        "estimated_duration_minutes": 60,
    }
    snapshot = PlanningSnapshot(
        scenario_id="SCN-UNELEC",
        snapshot_id="SNAP-UNELEC",
        horizon=base_horizon,
        tasks=[t1],
        tasks_map={"TSK-OHE": t1},
        work_orders_map={},
        resources=[],
        resources_map={},
        resource_availabilities=[],
        dependencies=[],
        dependencies_by_successor={},
        dependencies_by_predecessor={},
        sections_map={"SEC-UNELEC": {"section_id": "SEC-UNELEC", "electrified": False}},
        rules_map={},
        train_passes=[],
    )

    solver = CPSATSolver()
    result = solver.solve(snapshot)

    assert result.status == SchedulerStatus.OPTIMAL
    assert len(result.scheduled_tasks) == 0
    assert len(result.unscheduled_tasks) == 1
    assert result.unscheduled_tasks[0].task_id == "TSK-OHE"
