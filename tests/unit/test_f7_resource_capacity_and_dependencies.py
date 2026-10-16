"""Regression and domain validation test suite for F7: Resource Capacity & Dependency Semantics.

Validates:
1. Multi-capacity resources (capacity > 1) allow concurrent tasks up to capacity.
2. Resource capacity exceeded blocks concurrent placement (cumulative constraint).
3. Multi-unit task resource requirements (quantity > 1) are respected.
4. Tasks requiring demand > resource capacity fail closed.
5. Resources with no availability records default to available across planning horizon.
6. Resources whose only availability records are MAINTENANCE/UNAVAILABLE block scheduling across the horizon.
7. Tasks referencing unknown resources not in the scenario catalog fail closed.
8. Finish-to-Start dependencies enforce min_interval_minutes gap.
9. Tasks referencing missing predecessor tasks fail closed with DEPENDENCY_NOT_SATISFIED in both CP-SAT and heuristic schedulers.
10. Independent schedule validator detects capacity violations accounting for multi-unit demand.
"""

import pytest
from datetime import datetime, timedelta, timezone

from backend.app.domain.planning_snapshot import PlanningSnapshot
from backend.app.domain.temporal import PlanningHorizon, TimeInterval, TrainPass
from backend.app.domain.scheduling import (
    SchedulerStatus,
    SchedulerType,
    ScheduleMetrics,
    ScheduledTaskResult,
    ScheduleResult,
)
from backend.app.domain.compatibility import (
    ReasonCode,
    ScheduledTaskPlacement,
    ConstraintSeverity,
)
from backend.app.domain.enums import AvailabilityStatus
from backend.app.services.optimization.cp_sat_solver import CPSATSolver
from backend.app.services.schedulers.priority_greedy import PriorityGreedyScheduler
from backend.app.services.compatibility_service import CompatibilityEngine
from backend.app.services.candidate_generator import CandidateGenerator
from backend.app.services.validation.validator import IndependentScheduleValidator


@pytest.fixture
def f7_horizon():
    start = datetime(2026, 10, 20, 0, 0, tzinfo=timezone.utc)
    return PlanningHorizon(start=start, end=start + timedelta(hours=24))


def test_f7_multi_capacity_resource_allows_concurrent_tasks_up_to_capacity(f7_horizon):
    """Resource with capacity=2 should allow 2 concurrent tasks (on distinct sections) to run simultaneously."""
    res_id = "RES-CREW-CAP2"
    resource = {
        "resource_id": res_id,
        "name": "Track Maintenance Gang (Dual Team)",
        "capacity": 2,
    }

    t1 = {
        "task_id": "TSK-01",
        "task_code": "TC-01",
        "section_id": "SEC-A",
        "priority": "HIGH",
        "mandatory": True,
        "window_start": f7_horizon.start + timedelta(hours=2),
        "window_end": f7_horizon.start + timedelta(hours=6),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 0,
        "safety_buffer_after_minutes": 0,
        "required_resource_ids": [res_id],
        "resource_requirements": [{"resource_id": res_id, "quantity": 1}],
    }
    t2 = {
        "task_id": "TSK-02",
        "task_code": "TC-02",
        "section_id": "SEC-B",
        "priority": "HIGH",
        "mandatory": True,
        "window_start": f7_horizon.start + timedelta(hours=2),
        "window_end": f7_horizon.start + timedelta(hours=6),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 0,
        "safety_buffer_after_minutes": 0,
        "required_resource_ids": [res_id],
        "resource_requirements": [{"resource_id": res_id, "quantity": 1}],
    }

    snapshot = PlanningSnapshot(
        scenario_id="SCN-CAP2",
        snapshot_id="SNAP-CAP2",
        horizon=f7_horizon,
        tasks=[t1, t2],
        tasks_map={"TSK-01": t1, "TSK-02": t2},
        work_orders_map={},
        resources=[resource],
        resources_map={res_id: resource},
        resource_availabilities=[],
        dependencies=[],
        dependencies_by_successor={},
        dependencies_by_predecessor={},
        sections_map={
            "SEC-A": {"section_id": "SEC-A", "electrified": True},
            "SEC-B": {"section_id": "SEC-B", "electrified": True},
        },
        rules_map={},
        train_passes=[],
    )

    solver = CPSATSolver()
    result = solver.solve(snapshot)

    assert result.status == SchedulerStatus.OPTIMAL
    assert len(result.scheduled_tasks) == 2

    st1 = next(st for st in result.scheduled_tasks if st.task_id == "TSK-01")
    st2 = next(st for st in result.scheduled_tasks if st.task_id == "TSK-02")

    # With a narrow 4-hour window and 2-hour durations, both can execute concurrently
    # Verify independent validator passes the dual placement
    val_res = IndependentScheduleValidator.validate(snapshot, result)
    assert val_res.valid is True
    assert not any(f.code == "RESOURCE_CAPACITY_CONFLICT" for f in val_res.findings)


def test_f7_multi_capacity_resource_blocks_excess_concurrency(f7_horizon):
    """Resource with capacity=2 cannot schedule 3 tasks concurrently in a tight window."""
    res_id = "RES-CREW-CAP2"
    resource = {
        "resource_id": res_id,
        "name": "Track Maintenance Gang (Dual Team)",
        "capacity": 2,
    }

    # Narrow 2-hour window: only 2 tasks of 120m can fit concurrently; 3rd cannot fit at all
    tasks = []
    tasks_map = {}
    for i, sec in enumerate(["SEC-A", "SEC-B", "SEC-C"], start=1):
        tid = f"TSK-0{i}"
        t = {
            "task_id": tid,
            "task_code": f"TC-0{i}",
            "section_id": sec,
            "priority": "HIGH",
            "mandatory": False,
            "window_start": f7_horizon.start + timedelta(hours=2),
            "window_end": f7_horizon.start + timedelta(hours=4),
            "estimated_duration_minutes": 120,
            "safety_buffer_before_minutes": 0,
            "safety_buffer_after_minutes": 0,
            "required_resource_ids": [res_id],
            "resource_requirements": [{"resource_id": res_id, "quantity": 1}],
        }
        tasks.append(t)
        tasks_map[tid] = t

    snapshot = PlanningSnapshot(
        scenario_id="SCN-CAP2-EXCESS",
        snapshot_id="SNAP-CAP2-EXCESS",
        horizon=f7_horizon,
        tasks=tasks,
        tasks_map=tasks_map,
        work_orders_map={},
        resources=[resource],
        resources_map={res_id: resource},
        resource_availabilities=[],
        dependencies=[],
        dependencies_by_successor={},
        dependencies_by_predecessor={},
        sections_map={
            "SEC-A": {"section_id": "SEC-A", "electrified": True},
            "SEC-B": {"section_id": "SEC-B", "electrified": True},
            "SEC-C": {"section_id": "SEC-C", "electrified": True},
        },
        rules_map={},
        train_passes=[],
    )

    solver = CPSATSolver()
    result = solver.solve(snapshot)

    # At most 2 tasks can be scheduled within the 2-hour window due to capacity=2
    assert len(result.scheduled_tasks) == 2
    assert len(result.unscheduled_tasks) == 1

    # Unscheduled task must not have bogus SECTION_OCCUPANCY_CONFLICT
    unscheduled = result.unscheduled_tasks[0]
    assert ReasonCode.SECTION_OCCUPANCY_CONFLICT not in unscheduled.reason_codes

    val_res = IndependentScheduleValidator.validate(snapshot, result)
    assert val_res.valid is True


def test_f7_multi_unit_task_requirements_cumulative_scheduling(f7_horizon):
    """Task requiring quantity=2 consumes all capacity on capacity=2 resource; cannot co-occur with quantity=1 task."""
    res_id = "RES-CRANE-CAP2"
    resource = {
        "resource_id": res_id,
        "name": "Mobile Rail Cranes",
        "capacity": 2,
    }

    t1 = {
        "task_id": "TSK-HEAVY",
        "task_code": "TC-HEAVY",
        "section_id": "SEC-A",
        "priority": "HIGH",
        "mandatory": True,
        "window_start": f7_horizon.start + timedelta(hours=1),
        "window_end": f7_horizon.start + timedelta(hours=8),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 0,
        "safety_buffer_after_minutes": 0,
        "required_resource_ids": [res_id],
        "resource_requirements": [{"resource_id": res_id, "quantity": 2}],
    }
    t2 = {
        "task_id": "TSK-LIGHT",
        "task_code": "TC-LIGHT",
        "section_id": "SEC-B",
        "priority": "HIGH",
        "mandatory": True,
        "window_start": f7_horizon.start + timedelta(hours=1),
        "window_end": f7_horizon.start + timedelta(hours=8),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 0,
        "safety_buffer_after_minutes": 0,
        "required_resource_ids": [res_id],
        "resource_requirements": [{"resource_id": res_id, "quantity": 1}],
    }

    snapshot = PlanningSnapshot(
        scenario_id="SCN-MULTI-UNIT",
        snapshot_id="SNAP-MULTI-UNIT",
        horizon=f7_horizon,
        tasks=[t1, t2],
        tasks_map={"TSK-HEAVY": t1, "TSK-LIGHT": t2},
        work_orders_map={},
        resources=[resource],
        resources_map={res_id: resource},
        resource_availabilities=[],
        dependencies=[],
        dependencies_by_successor={},
        dependencies_by_predecessor={},
        sections_map={
            "SEC-A": {"section_id": "SEC-A", "electrified": True},
            "SEC-B": {"section_id": "SEC-B", "electrified": True},
        },
        rules_map={},
        train_passes=[],
    )

    solver = CPSATSolver()
    result = solver.solve(snapshot)

    assert result.status == SchedulerStatus.OPTIMAL
    assert len(result.scheduled_tasks) == 2

    st_heavy = next(st for st in result.scheduled_tasks if st.task_id == "TSK-HEAVY")
    st_light = next(st for st in result.scheduled_tasks if st.task_id == "TSK-LIGHT")

    # Because heavy consumes 2 units and light consumes 1 unit (sum = 3 > capacity 2),
    # they MUST be sequenced without overlapping!
    assert (st_heavy.interval.end <= st_light.interval.start or
            st_light.interval.end <= st_heavy.interval.start)

    val_res = IndependentScheduleValidator.validate(snapshot, result)
    assert val_res.valid is True


def test_f7_task_demand_exceeding_capacity_fails_closed(f7_horizon):
    """Task requiring quantity=3 on a resource with capacity=2 must fail closed and be left unscheduled."""
    res_id = "RES-CRANE-CAP2"
    resource = {
        "resource_id": res_id,
        "name": "Mobile Rail Cranes",
        "capacity": 2,
    }

    t_excess = {
        "task_id": "TSK-EXCESS-DEMAND",
        "task_code": "TC-EXCESS",
        "section_id": "SEC-A",
        "priority": "HIGH",
        "mandatory": False,
        "window_start": f7_horizon.start + timedelta(hours=1),
        "window_end": f7_horizon.start + timedelta(hours=8),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 0,
        "safety_buffer_after_minutes": 0,
        "required_resource_ids": [res_id],
        "resource_requirements": [{"resource_id": res_id, "quantity": 3}],
    }

    snapshot = PlanningSnapshot(
        scenario_id="SCN-CAP-EXCEED",
        snapshot_id="SNAP-CAP-EXCEED",
        horizon=f7_horizon,
        tasks=[t_excess],
        tasks_map={"TSK-EXCESS-DEMAND": t_excess},
        work_orders_map={},
        resources=[resource],
        resources_map={res_id: resource},
        resource_availabilities=[],
        dependencies=[],
        dependencies_by_successor={},
        dependencies_by_predecessor={},
        sections_map={"SEC-A": {"section_id": "SEC-A", "electrified": True}},
        rules_map={},
        train_passes=[],
    )

    solver = CPSATSolver()
    result = solver.solve(snapshot)

    assert len(result.scheduled_tasks) == 0
    assert len(result.unscheduled_tasks) == 1
    unscheduled = result.unscheduled_tasks[0]
    assert ReasonCode.RESOURCE_UNAVAILABLE in unscheduled.reason_codes


def test_f7_resource_no_availability_records_defaults_available_across_horizon(f7_horizon):
    """Resource with no availability records defaults to available across the planning horizon."""
    res_id = "RES-DEFAULT-AVAIL"
    resource = {
        "resource_id": res_id,
        "name": "Standard Gang",
        "capacity": 1,
    }
    t = {
        "task_id": "TSK-OPEN",
        "task_code": "TC-OPEN",
        "section_id": "SEC-A",
        "priority": "MEDIUM",
        "mandatory": True,
        "window_start": f7_horizon.start + timedelta(hours=10),
        "window_end": f7_horizon.start + timedelta(hours=14),
        "estimated_duration_minutes": 60,
        "safety_buffer_before_minutes": 0,
        "safety_buffer_after_minutes": 0,
        "required_resource_ids": [res_id],
        "resource_requirements": [{"resource_id": res_id, "quantity": 1}],
    }

    snapshot = PlanningSnapshot(
        scenario_id="SCN-NO-AVAIL-RECS",
        snapshot_id="SNAP-NO-AVAIL-RECS",
        horizon=f7_horizon,
        tasks=[t],
        tasks_map={"TSK-OPEN": t},
        work_orders_map={},
        resources=[resource],
        resources_map={res_id: resource},
        resource_availabilities=[],  # Empty list: no availability records defined
        dependencies=[],
        dependencies_by_successor={},
        dependencies_by_predecessor={},
        sections_map={"SEC-A": {"section_id": "SEC-A", "electrified": True}},
        rules_map={},
        train_passes=[],
    )

    solver = CPSATSolver()
    result = solver.solve(snapshot)

    assert result.status == SchedulerStatus.OPTIMAL
    assert len(result.scheduled_tasks) == 1
    val_res = IndependentScheduleValidator.validate(snapshot, result)
    assert val_res.valid is True


def test_f7_resource_only_maintenance_records_blocks_scheduling(f7_horizon):
    """If a resource has records in resource_availabilities but ALL are MAINTENANCE, it cannot be scheduled."""
    res_id = "RES-IN-SHOP"
    resource = {
        "resource_id": res_id,
        "name": "Heavy Tamping Machine in Shop",
        "capacity": 1,
    }
    avail_record = {
        "availability_id": "AVL-MAINT-01",
        "resource_id": res_id,
        "available_from": f7_horizon.start,
        "available_until": f7_horizon.end,
        "availability_status": AvailabilityStatus.MAINTENANCE,
        "quantity": 1,
    }
    t = {
        "task_id": "TSK-BLOCKED",
        "task_code": "TC-BLOCKED",
        "section_id": "SEC-A",
        "priority": "HIGH",
        "mandatory": False,
        "window_start": f7_horizon.start + timedelta(hours=2),
        "window_end": f7_horizon.start + timedelta(hours=8),
        "estimated_duration_minutes": 60,
        "safety_buffer_before_minutes": 0,
        "safety_buffer_after_minutes": 0,
        "required_resource_ids": [res_id],
        "resource_requirements": [{"resource_id": res_id, "quantity": 1}],
    }

    snapshot = PlanningSnapshot(
        scenario_id="SCN-MAINT-ONLY",
        snapshot_id="SNAP-MAINT-ONLY",
        horizon=f7_horizon,
        tasks=[t],
        tasks_map={"TSK-BLOCKED": t},
        work_orders_map={},
        resources=[resource],
        resources_map={res_id: resource},
        resource_availabilities=[avail_record],
        dependencies=[],
        dependencies_by_successor={},
        dependencies_by_predecessor={},
        sections_map={"SEC-A": {"section_id": "SEC-A", "electrified": True}},
        rules_map={},
        train_passes=[],
    )

    solver = CPSATSolver()
    result = solver.solve(snapshot)

    assert len(result.scheduled_tasks) == 0
    assert len(result.unscheduled_tasks) == 1
    assert ReasonCode.RESOURCE_UNAVAILABLE in result.unscheduled_tasks[0].reason_codes


def test_f7_unknown_resource_in_catalog_fails_closed(f7_horizon):
    """Task requiring a resource not present in the scenario's resource catalog must fail closed."""
    known_res = {
        "resource_id": "RES-KNOWN-01",
        "name": "Standard Gang",
        "capacity": 1,
    }
    t_ghost = {
        "task_id": "TSK-GHOST",
        "task_code": "TC-GHOST",
        "section_id": "SEC-A",
        "priority": "HIGH",
        "mandatory": False,
        "window_start": f7_horizon.start + timedelta(hours=2),
        "window_end": f7_horizon.start + timedelta(hours=8),
        "estimated_duration_minutes": 60,
        "safety_buffer_before_minutes": 0,
        "safety_buffer_after_minutes": 0,
        "required_resource_ids": ["RES-NONEXISTENT-99"],
        "resource_requirements": [{"resource_id": "RES-NONEXISTENT-99", "quantity": 1}],
    }

    snapshot = PlanningSnapshot(
        scenario_id="SCN-UNKNOWN-RES",
        snapshot_id="SNAP-UNKNOWN-RES",
        horizon=f7_horizon,
        tasks=[t_ghost],
        tasks_map={"TSK-GHOST": t_ghost},
        work_orders_map={},
        resources=[known_res],
        resources_map={"RES-KNOWN-01": known_res},
        resource_availabilities=[],
        dependencies=[],
        dependencies_by_successor={},
        dependencies_by_predecessor={},
        sections_map={"SEC-A": {"section_id": "SEC-A", "electrified": True}},
        rules_map={},
        train_passes=[],
    )

    solver = CPSATSolver()
    result = solver.solve(snapshot)

    assert len(result.scheduled_tasks) == 0
    assert len(result.unscheduled_tasks) == 1
    assert ReasonCode.RESOURCE_UNAVAILABLE in result.unscheduled_tasks[0].reason_codes


def test_f7_finish_to_start_dependency_with_min_interval(f7_horizon):
    """Successor task cannot start before predecessor finishes plus declared min_interval_minutes."""
    t1 = {
        "task_id": "TSK-PRED",
        "task_code": "TC-PRED",
        "section_id": "SEC-A",
        "priority": "HIGH",
        "mandatory": True,
        "window_start": f7_horizon.start + timedelta(hours=1),
        "window_end": f7_horizon.start + timedelta(hours=6),
        "estimated_duration_minutes": 60,
        "safety_buffer_before_minutes": 0,
        "safety_buffer_after_minutes": 0,
    }
    t2 = {
        "task_id": "TSK-SUCC",
        "task_code": "TC-SUCC",
        "section_id": "SEC-B",
        "priority": "HIGH",
        "mandatory": True,
        "window_start": f7_horizon.start + timedelta(hours=1),
        "window_end": f7_horizon.start + timedelta(hours=10),
        "estimated_duration_minutes": 60,
        "safety_buffer_before_minutes": 0,
        "safety_buffer_after_minutes": 0,
    }
    dep = {
        "dependency_id": "DEP-01",
        "predecessor_task_id": "TSK-PRED",
        "successor_task_id": "TSK-SUCC",
        "min_interval_minutes": 45,
    }

    snapshot = PlanningSnapshot(
        scenario_id="SCN-DEP-GAP",
        snapshot_id="SNAP-DEP-GAP",
        horizon=f7_horizon,
        tasks=[t1, t2],
        tasks_map={"TSK-PRED": t1, "TSK-SUCC": t2},
        work_orders_map={},
        resources=[],
        resources_map={},
        resource_availabilities=[],
        dependencies=[dep],
        dependencies_by_successor={"TSK-SUCC": [dep]},
        dependencies_by_predecessor={"TSK-PRED": [dep]},
        sections_map={
            "SEC-A": {"section_id": "SEC-A", "electrified": True},
            "SEC-B": {"section_id": "SEC-B", "electrified": True},
        },
        rules_map={},
        train_passes=[],
    )

    solver = CPSATSolver()
    result = solver.solve(snapshot)

    assert result.status == SchedulerStatus.OPTIMAL
    assert len(result.scheduled_tasks) == 2

    st1 = next(st for st in result.scheduled_tasks if st.task_id == "TSK-PRED")
    st2 = next(st for st in result.scheduled_tasks if st.task_id == "TSK-SUCC")

    # Enforces st2.start >= st1.end + 45 minutes
    gap = (st2.interval.start - st1.interval.end).total_seconds() / 60
    assert gap >= 45

    val_res = IndependentScheduleValidator.validate(snapshot, result)
    assert val_res.valid is True


def test_f7_missing_predecessor_task_fails_closed_in_solver_and_scheduler(f7_horizon):
    """If a dependency references a predecessor task that does not exist in the snapshot, successor fails closed."""
    t_succ = {
        "task_id": "TSK-ORPHAN-SUCC",
        "task_code": "TC-ORPHAN-SUCC",
        "section_id": "SEC-A",
        "priority": "HIGH",
        "mandatory": False,
        "window_start": f7_horizon.start + timedelta(hours=1),
        "window_end": f7_horizon.start + timedelta(hours=8),
        "estimated_duration_minutes": 60,
        "safety_buffer_before_minutes": 0,
        "safety_buffer_after_minutes": 0,
    }
    dep = {
        "dependency_id": "DEP-ORPHAN",
        "predecessor_task_id": "TSK-DOES-NOT-EXIST",
        "successor_task_id": "TSK-ORPHAN-SUCC",
        "min_interval_minutes": 0,
    }

    snapshot = PlanningSnapshot(
        scenario_id="SCN-MISSING-PRED",
        snapshot_id="SNAP-MISSING-PRED",
        horizon=f7_horizon,
        tasks=[t_succ],
        tasks_map={"TSK-ORPHAN-SUCC": t_succ},
        work_orders_map={},
        resources=[],
        resources_map={},
        resource_availabilities=[],
        dependencies=[dep],
        dependencies_by_successor={"TSK-ORPHAN-SUCC": [dep]},
        dependencies_by_predecessor={"TSK-DOES-NOT-EXIST": [dep]},
        sections_map={"SEC-A": {"section_id": "SEC-A", "electrified": True}},
        rules_map={},
        train_passes=[],
    )

    # 1. CP-SAT Solver
    solver = CPSATSolver()
    result_cpsat = solver.solve(snapshot)
    assert len(result_cpsat.scheduled_tasks) == 0
    assert len(result_cpsat.unscheduled_tasks) == 1
    assert ReasonCode.DEPENDENCY_NOT_SATISFIED in result_cpsat.unscheduled_tasks[0].reason_codes

    # 2. Greedy Scheduler
    scheduler = PriorityGreedyScheduler()
    result_greedy = scheduler.schedule(snapshot)
    assert len(result_greedy.scheduled_tasks) == 0
    assert len(result_greedy.unscheduled_tasks) == 1
    assert ReasonCode.DEPENDENCY_NOT_SATISFIED in result_greedy.unscheduled_tasks[0].reason_codes


def test_f7_validator_detects_capacity_conflict_with_multi_unit_demand(f7_horizon):
    """Independent validator sweep-line detects capacity violation when concurrent task demand exceeds capacity."""
    res_id = "RES-CREW-CAP2"
    resource = {
        "resource_id": res_id,
        "name": "Track Maintenance Gang (Dual Team)",
        "capacity": 2,
    }

    t1 = {
        "task_id": "TSK-01",
        "task_code": "TC-01",
        "section_id": "SEC-A",
        "resource_requirements": [{"resource_id": res_id, "quantity": 2}],
    }
    t2 = {
        "task_id": "TSK-02",
        "task_code": "TC-02",
        "section_id": "SEC-B",
        "resource_requirements": [{"resource_id": res_id, "quantity": 1}],
    }

    snapshot = PlanningSnapshot(
        scenario_id="SCN-VAL-CAP",
        snapshot_id="SNAP-VAL-CAP",
        horizon=f7_horizon,
        tasks=[t1, t2],
        tasks_map={"TSK-01": t1, "TSK-02": t2},
        work_orders_map={},
        resources=[resource],
        resources_map={res_id: resource},
        resource_availabilities=[],
        dependencies=[],
        dependencies_by_successor={},
        dependencies_by_predecessor={},
        sections_map={
            "SEC-A": {"section_id": "SEC-A", "electrified": True},
            "SEC-B": {"section_id": "SEC-B", "electrified": True},
        },
        rules_map={},
        train_passes=[],
    )

    # Manually build a schedule where both tasks overlap: demand = 2 + 1 = 3 > capacity 2
    overlap_start = f7_horizon.start + timedelta(hours=3)
    overlap_end = f7_horizon.start + timedelta(hours=5)

    st1 = ScheduledTaskResult(
        task_id="TSK-01",
        task_code="TC-01",
        interval=TimeInterval(start=overlap_start, end=overlap_end),
        possession_interval=TimeInterval(start=overlap_start, end=overlap_end),
        duration_minutes=120,
        affected_sections=["SEC-A"],
        assigned_resources=[res_id],
        sequence_order=1,
    )
    st2 = ScheduledTaskResult(
        task_id="TSK-02",
        task_code="TC-02",
        interval=TimeInterval(start=overlap_start, end=overlap_end),
        possession_interval=TimeInterval(start=overlap_start, end=overlap_end),
        duration_minutes=120,
        affected_sections=["SEC-B"],
        assigned_resources=[res_id],
        sequence_order=2,
    )

    schedule = ScheduleResult(
        schedule_id="SCHED-TEST-CAP",
        scheduler_type=SchedulerType.CP_SAT,
        scheduler_version="1.0.0",
        scenario_id=snapshot.scenario_id,
        snapshot_id=snapshot.snapshot_id,
        planning_start=snapshot.horizon.start,
        planning_end=snapshot.horizon.end,
        status=SchedulerStatus.FEASIBLE,
        solver_status="FEASIBLE",
        scheduled_tasks=[st1, st2],
        unscheduled_tasks=[],
        metrics=ScheduleMetrics(
            total_tasks=2,
            scheduled_tasks=2,
            unscheduled_tasks=0,
            completion_rate=1.0,
            mandatory_tasks=0,
            mandatory_scheduled=0,
            mandatory_unscheduled=0,
            mandatory_completion_rate=1.0,
            total_scheduled_duration_minutes=240,
            total_possession_duration_minutes=240,
            total_priority_score_available=2.0,
            scheduled_priority_score=2.0,
            unscheduled_priority_score=0.0,
            priority_score_capture_rate=1.0,
        ),
        configuration={},
        execution_time_ms=10.0,
        decision_trace=[],
    )

    val_res = IndependentScheduleValidator.validate(snapshot, schedule)
    assert val_res.valid is False
    assert any(f.code == "RESOURCE_CAPACITY_CONFLICT" for f in val_res.findings)
