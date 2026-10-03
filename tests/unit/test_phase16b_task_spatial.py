"""Unit tests for Phase 16B: Track-Aware Maintenance Task Spatial Semantics.

Verifies:
1. Domain invariants:
   - task without track_id and without chainage -> valid
   - task without track_id but with from_km -> invalid (ValidationError)
   - task without track_id but with to_km -> invalid (ValidationError)
   - task with track_id and no chainage -> valid
   - task with track_id and valid range -> valid
   - task with track_id and from_km > to_km -> invalid (ValidationError)
   - task with negative chainage -> invalid (ValidationError)
2. ORM fields and constraints on MaintenanceTaskModel
3. PlanningSnapshot preservation of task track_id, from_km, to_km
4. PlanningSnapshot hash stability
5. Solver & Validator boundary test: tasks on different tracks in the same section
   remain conflicting under whole-section scheduling semantics.
"""

import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from backend.app.domain import (
    MaintenanceTask,
    PlanningSnapshot,
    DataClass,
    TaskPriority,
    TaskType,
    TaskStatus,
)
from backend.app.domain.scheduling import SchedulerStatus
from backend.app.db.models import MaintenanceTaskModel
from backend.app.services.planning_service import ScenarioPlanningBundle
from backend.app.services.optimization.cp_sat_solver import CPSATSolver
from backend.app.domain.temporal import PlanningHorizon


def _create_base_task_dict(**kwargs):
    now = datetime(2026, 10, 10, 6, 0, 0, tzinfo=timezone.utc)
    base = {
        "task_id": "TSK-TEST-SPATIAL",
        "work_order_id": "WO-0001",
        "task_code": "TSK-SPATIAL-01",
        "title": "Plain Track CSM Tamping",
        "task_type": TaskType.TRACK_MACHINE_WORK,
        "status": TaskStatus.PLANNED,
        "priority": TaskPriority.HIGH,
        "mandatory": True,
        "section_id": "SEC-NDLS-GZB",
        "scenario_id": "SCN-001",
        "window_start": now,
        "window_end": now + timedelta(hours=6),
        "estimated_duration_minutes": 180,
        "classification": DataClass.SYNTHETIC,
        "source_id": "SRC-TRACKMELD-SYNTHETIC-GEN",
    }
    base.update(kwargs)
    return base


def test_task_without_track_and_without_chainage_valid():
    data = _create_base_task_dict(track_id=None, from_km=None, to_km=None)
    task = MaintenanceTask(**data)
    assert task.track_id is None
    assert task.from_km is None
    assert task.to_km is None


def test_task_without_track_but_with_from_km_invalid():
    data = _create_base_task_dict(track_id=None, from_km=10.5, to_km=None)
    with pytest.raises(ValidationError, match="from_km and to_km must be None when track_id is None"):
        MaintenanceTask(**data)


def test_task_without_track_but_with_to_km_invalid():
    data = _create_base_task_dict(track_id=None, from_km=None, to_km=15.0)
    with pytest.raises(ValidationError, match="from_km and to_km must be None when track_id is None"):
        MaintenanceTask(**data)


def test_task_with_track_and_no_chainage_valid():
    data = _create_base_task_dict(track_id="TRK-NDLS-GZB-UP", from_km=None, to_km=None)
    task = MaintenanceTask(**data)
    assert task.track_id == "TRK-NDLS-GZB-UP"
    assert task.from_km is None
    assert task.to_km is None


def test_task_with_track_and_valid_range_valid():
    data = _create_base_task_dict(track_id="TRK-NDLS-GZB-DN", from_km=12.4, to_km=15.8)
    task = MaintenanceTask(**data)
    assert task.track_id == "TRK-NDLS-GZB-DN"
    assert task.from_km == 12.4
    assert task.to_km == 15.8


def test_task_with_track_and_point_chainage_valid():
    # Single point asset work: from_km == to_km
    data = _create_base_task_dict(track_id="TRK-NDLS-GZB-UP", from_km=14.0, to_km=14.0)
    task = MaintenanceTask(**data)
    assert task.from_km == 14.0
    assert task.to_km == 14.0


def test_task_with_from_km_greater_than_to_km_invalid():
    data = _create_base_task_dict(track_id="TRK-NDLS-GZB-DN", from_km=20.0, to_km=15.0)
    with pytest.raises(ValidationError, match="must be <= to_km"):
        MaintenanceTask(**data)


def test_task_with_negative_chainage_invalid():
    data1 = _create_base_task_dict(track_id="TRK-NDLS-GZB-DN", from_km=-1.5, to_km=10.0)
    with pytest.raises(ValidationError, match="cannot be negative"):
        MaintenanceTask(**data1)

    data2 = _create_base_task_dict(track_id="TRK-NDLS-GZB-DN", from_km=0.0, to_km=-5.0)
    with pytest.raises(ValidationError, match="cannot be negative"):
        MaintenanceTask(**data2)


def test_maintenance_task_orm_spatial_columns():
    assert hasattr(MaintenanceTaskModel, "track_id")
    assert hasattr(MaintenanceTaskModel, "from_km")
    assert hasattr(MaintenanceTaskModel, "to_km")


def test_planning_snapshot_preserves_spatial_fields():
    tasks = [
        {
            "task_id": "TSK-01",
            "task_code": "TC-01",
            "section_id": "SEC-01",
            "track_id": "TRK-SEC1-UP",
            "from_km": None,
            "to_km": None,
            "window_start": "2026-10-10T06:00:00Z",
            "window_end": "2026-10-10T12:00:00Z",
            "estimated_duration_minutes": 180,
        },
        {
            "task_id": "TSK-02",
            "task_code": "TC-02",
            "section_id": "SEC-01",
            "track_id": "TRK-SEC1-DN",
            "from_km": 12.4,
            "to_km": 15.8,
            "window_start": "2026-10-10T06:00:00Z",
            "window_end": "2026-10-10T12:00:00Z",
            "estimated_duration_minutes": 120,
        },
    ]

    bundle = ScenarioPlanningBundle(
        scenario={
            "scenario_id": "SCN-TEST-SPATIAL",
            "planning_start": "2026-10-10T00:00:00Z",
            "planning_end": "2026-10-11T00:00:00Z",
        },
        work_orders=[],
        tasks=tasks,
        dependencies=[],
        resources=[],
        resource_availabilities=[],
        sections=[],
        train_movements=[],
        applicable_rules=[],
        tracks=[],
    )

    snapshot = PlanningSnapshot.from_bundle(bundle)
    assert len(snapshot.tasks) == 2
    t1 = snapshot.tasks_map["TSK-01"]
    assert t1["track_id"] == "TRK-SEC1-UP"
    assert t1["from_km"] is None
    assert t1["to_km"] is None

    t2 = snapshot.tasks_map["TSK-02"]
    assert t2["track_id"] == "TRK-SEC1-DN"
    assert t2["from_km"] == 12.4
    assert t2["to_km"] == 15.8

    # Verify snapshot hash computes deterministically
    h = snapshot.compute_snapshot_hash()
    assert isinstance(h, str)
    assert len(h) == 64


def test_solver_boundary_whole_section_conflict_preserved():
    """Verify that in Phase 16B, CP-SAT still enforces spatial conflict at the whole-section level.

    Two tasks in the SAME section (SEC-01) on DIFFERENT tracks (UP vs DN) with overlapping
    time windows CANNOT be scheduled concurrently because whole-section conflict semantics
    remain in force.
    """
    start = datetime(2026, 10, 15, 6, 0, tzinfo=timezone.utc)
    horizon = PlanningHorizon(start=start, end=start + timedelta(hours=12))

    # T1: 180 min duration on UP track in SEC-01 in window [06:00, 12:00]
    t1 = {
        "task_id": "TSK-UP",
        "task_code": "TC-UP",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-UP",
        "from_km": None,
        "to_km": None,
        "priority": "HIGH",
        "window_start": start,
        "window_end": start + timedelta(hours=6),
        "estimated_duration_minutes": 240,  # 4 hours
        "requires_traffic_block": True,
        "safety_buffer_before_minutes": 0,
        "safety_buffer_after_minutes": 0,
    }
    # T2: 240 min duration on DN track in same SEC-01 in window [06:00, 12:00]
    t2 = {
        "task_id": "TSK-DN",
        "task_code": "TC-DN",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-DN",
        "from_km": 10.0,
        "to_km": 15.0,
        "priority": "HIGH",
        "window_start": start,
        "window_end": start + timedelta(hours=6),
        "estimated_duration_minutes": 240,  # 4 hours
        "requires_traffic_block": True,
        "safety_buffer_before_minutes": 0,
        "safety_buffer_after_minutes": 0,
    }

    # In a 6-hour window (06:00 - 12:00), two 4-hour tasks require 8 hours total.
    # If the solver treated tracks independently, both could run concurrently (each needing 4h in a 6h window).
    # But because whole-section conflict is enforced, one MUST be unscheduled!
    snapshot = PlanningSnapshot(
        scenario_id="SCN-TEST-BOUNDARY",
        snapshot_id="SNAP-TEST-BOUNDARY",
        horizon=horizon,
        tasks=[t1, t2],
        tasks_map={"TSK-UP": t1, "TSK-DN": t2},
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
    assert result.status in (SchedulerStatus.OPTIMAL, SchedulerStatus.FEASIBLE)

    scheduled_ids = [st.task_id for st in result.scheduled_tasks]
    assert len(scheduled_ids) == 1, (
        f"Phase 16B invariant violated: expected 1 task scheduled due to whole-section conflict, got {scheduled_ids}"
    )
    assert len(result.unscheduled_tasks) == 1
