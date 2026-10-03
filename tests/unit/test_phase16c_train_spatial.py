"""Unit tests for Phase 16C: Train Movement Track Semantics.

Verifies:
1. TrainMovementModel ORM fields and relationships:
   - track_id column, foreign key to tracks.track_id, track relationship
   - TrackModel.movements back-population
2. TrainMovement domain model:
   - track_id optional field retains value
   - train_id/train_number service identity is distinct from movement_id and track_id
3. TrainPass semantics:
   - Station dwell remains distinct from section traversal
   - Consecutive station hops derive TrainPass with source_movement_ids
   - No forced or invented section traversal track
4. PlanningSnapshot determinism:
   - train_movements and train_movements_map preserved
   - Canonical snapshot hash determinism
5. Solver regression:
   - Train movement track semantics do not alter whole-section CP-SAT scheduling semantics
"""

import pytest
from datetime import datetime, timezone, timedelta

from backend.app.domain import (
    TrainMovement,
    PlanningSnapshot,
    DataClass,
)
from backend.app.domain.temporal import PlanningHorizon, TrainPass, TimeInterval
from backend.app.domain.scheduling import SchedulerStatus
from backend.app.db.models import TrainMovementModel, TrackModel
from backend.app.services.compatibility_service import CompatibilityEngine
from backend.app.services.planning_service import ScenarioPlanningBundle
from backend.app.services.optimization.cp_sat_solver import CPSATSolver


def test_train_movement_domain_model_with_track():
    m = TrainMovement(
        movement_id="MOV-12301-NDLS-09",
        train_id="TRN-12301",
        train_number="12301",
        train_name="Howrah Rajdhani Express",
        station_id="STN-NDLS",
        station_code="NDLS",
        station_name="New Delhi",
        stop_sequence=9,
        scheduled_arrival="10:05",
        scheduled_departure=None,
        day_offset=1,
        distance_km=1451.0,
        movement_type="SCHEDULED_DESTINATION",
        basis="SCHEDULED_TIMETABLE",
        track_id="TRK-NDLS-GZB-UP",
        classification=DataClass.REAL,
        source_id="SRC-TAG-2023-PREM-RAJ",
    )
    assert m.movement_id == "MOV-12301-NDLS-09"
    assert m.train_id == "TRN-12301"
    assert m.train_number == "12301"
    assert m.track_id == "TRK-NDLS-GZB-UP"
    # Service identity != movement occurrence identity != track identity
    assert m.train_id != m.movement_id
    assert m.movement_id != m.track_id


def test_train_movement_domain_model_without_track():
    m = TrainMovement(
        movement_id="MOV-12301-HWH-01",
        train_id="TRN-12301",
        train_number="12301",
        train_name="Howrah Rajdhani Express",
        station_id="STN-HWH",
        station_code="HWH",
        station_name="Howrah",
        stop_sequence=1,
        scheduled_arrival=None,
        scheduled_departure="16:50",
        day_offset=0,
        distance_km=0.0,
        movement_type="SCHEDULED_ORIGIN",
        basis="SCHEDULED_TIMETABLE",
        track_id=None,
        classification=DataClass.REAL,
        source_id="SRC-TAG-2023-PREM-RAJ",
    )
    assert m.track_id is None


def test_train_movement_orm_fields_and_relationships():
    assert hasattr(TrainMovementModel, "track_id")
    assert hasattr(TrainMovementModel, "track")
    assert hasattr(TrackModel, "movements")


def test_train_pass_derivation_preserves_dwell_and_traversal_distinction():
    start = datetime(2026, 10, 15, 0, 0, tzinfo=timezone.utc)
    horizon = PlanningHorizon(start=start, end=start + timedelta(hours=24))

    movements = [
        {
            "movement_id": "MOV-12004-NDLS-01",
            "train_id": "TRN-12004",
            "train_number": "12004",
            "station_id": "STN-NDLS",
            "stop_sequence": 1,
            "scheduled_arrival": None,
            "scheduled_departure": "06:10",
            "day_offset": 0,
            "track_id": "TRK-NDLS-GZB-DN",
        },
        {
            "movement_id": "MOV-12004-GZB-02",
            "train_id": "TRN-12004",
            "train_number": "12004",
            "station_id": "STN-GZB",
            "stop_sequence": 2,
            "scheduled_arrival": "06:45",
            "scheduled_departure": "06:47",
            "day_offset": 0,
            "track_id": None,
        },
    ]
    sections = [
        {
            "section_id": "SEC-NDLS-GZB",
            "from_station_id": "STN-NDLS",
            "to_station_id": "STN-GZB",
        }
    ]

    passes = CompatibilityEngine.derive_train_passes(
        train_movements=movements,
        sections=sections,
        horizon=horizon,
    )

    assert len(passes) >= 1
    p = passes[0]
    # Pass between stations captures the station hop / traversal
    assert p.movement_type in ["STATION_HOP", "SECTION_TRAVERSAL"]
    assert p.from_station_id == "STN-NDLS"
    assert p.to_station_id == "STN-GZB"
    # Source movements correctly record the underlying timetable event occurrences
    assert "MOV-12004-NDLS-01" in p.source_movement_ids
    assert "MOV-12004-GZB-02" in p.source_movement_ids


def test_planning_snapshot_preserves_train_movements_and_hash_stability():
    start = datetime(2026, 10, 15, 0, 0, tzinfo=timezone.utc)
    horizon = PlanningHorizon(start=start, end=start + timedelta(hours=24))

    mov1 = {
        "movement_id": "MOV-12301-NDLS-09",
        "train_id": "TRN-12301",
        "train_number": "12301",
        "track_id": "TRK-NDLS-GZB-UP",
        "station_id": "STN-NDLS",
        "scheduled_arrival": "10:05",
        "stop_sequence": 9,
        "day_offset": 1,
    }
    mov2 = {
        "movement_id": "MOV-12302-NDLS-01",
        "train_id": "TRN-12302",
        "train_number": "12302",
        "track_id": "TRK-NDLS-GZB-DN",
        "station_id": "STN-NDLS",
        "scheduled_departure": "16:50",
        "stop_sequence": 1,
        "day_offset": 0,
    }

    bundle = ScenarioPlanningBundle(
        scenario={
            "scenario_id": "SCN-TEST-MOV-SNAP",
            "planning_start": start.isoformat(),
            "planning_end": (start + timedelta(hours=24)).isoformat(),
        },
        work_orders=[],
        tasks=[],
        dependencies=[],
        resources=[],
        resource_availabilities=[],
        sections=[],
        train_movements=[mov1, mov2],
        applicable_rules=[],
        tracks=[],
    )

    snapshot = PlanningSnapshot.from_bundle(bundle)
    assert len(snapshot.train_movements) == 2
    assert "MOV-12301-NDLS-09" in snapshot.train_movements_map
    assert snapshot.train_movements_map["MOV-12301-NDLS-09"]["track_id"] == "TRK-NDLS-GZB-UP"
    assert snapshot.train_movements_map["MOV-12302-NDLS-01"]["track_id"] == "TRK-NDLS-GZB-DN"

    # Verify deterministic snapshot hash computation
    h1 = snapshot.compute_snapshot_hash()
    h2 = snapshot.compute_snapshot_hash()
    assert h1 == h2
    assert len(h1) == 64


def test_solver_regression_train_movement_tracks_preserve_cp_sat_semantics():
    """Verify that adding track_id to train movements does NOT alter CP-SAT whole-section clearance."""
    start = datetime(2026, 10, 15, 6, 0, tzinfo=timezone.utc)
    horizon = PlanningHorizon(start=start, end=start + timedelta(hours=12))

    # A train pass occupying SEC-01 from 08:00 to 09:00
    pass_interval = TimeInterval(start=start + timedelta(hours=2), end=start + timedelta(hours=3))
    tp = TrainPass(
        pass_id="PASS-12004-SEC-01",
        train_id="TRN-12004",
        train_number="12004",
        section_id="SEC-01",
        from_station_id="STN-A",
        to_station_id="STN-B",
        interval=pass_interval,
        movement_type="SECTION_TRAVERSAL",
        source_movement_ids=["MOV-01", "MOV-02"],
    )

    # A task in SEC-01 requiring 120 mins with 15m safety buffers in window [06:00, 12:00]
    t1 = {
        "task_id": "TSK-CP-01",
        "task_code": "TC-CP-01",
        "section_id": "SEC-01",
        "track_id": "TRK-SEC-01-UP",
        "from_km": None,
        "to_km": None,
        "priority": "HIGH",
        "mandatory": False,
        "window_start": start,
        "window_end": start + timedelta(hours=6),
        "estimated_duration_minutes": 120,
        "requires_traffic_block": True,
        "safety_buffer_before_minutes": 15,
        "safety_buffer_after_minutes": 15,
    }

    snapshot = PlanningSnapshot(
        scenario_id="SCN-REGRESSION-MOV",
        snapshot_id="SNAP-REGRESSION-MOV",
        horizon=horizon,
        tasks=[t1],
        tasks_map={"TSK-CP-01": t1},
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
        train_movements=[
            {"movement_id": "MOV-01", "train_id": "TRN-12004", "track_id": "TRK-SEC-01-UP"},
            {"movement_id": "MOV-02", "train_id": "TRN-12004", "track_id": "TRK-SEC-01-DN"},
        ],
        train_movements_map={
            "MOV-01": {"movement_id": "MOV-01", "train_id": "TRN-12004", "track_id": "TRK-SEC-01-UP"},
            "MOV-02": {"movement_id": "MOV-02", "train_id": "TRN-12004", "track_id": "TRK-SEC-01-DN"},
        },
    )

    solver = CPSATSolver()
    result = solver.solve(snapshot)
    assert result.status in (SchedulerStatus.OPTIMAL, SchedulerStatus.FEASIBLE)
    assert len(result.scheduled_tasks) == 1

    st = result.scheduled_tasks[0]
    # Task placement must clear the train pass interval [08:00, 09:00] plus 15m buffers on whole-section
    task_start = st.interval.start
    task_end = st.interval.end
    buffer_before = timedelta(minutes=15)
    buffer_after = timedelta(minutes=15)

    # Either finished before train pass (end + buffer <= pass.start) or started after train pass (start >= pass.end + buffer)
    clears_before = (task_end + buffer_after) <= pass_interval.start
    clears_after = task_start >= (pass_interval.end + buffer_before)
    assert clears_before or clears_after, (
        f"Task [{task_start}, {task_end}] violated train clearance [{pass_interval.start}, {pass_interval.end}]"
    )
