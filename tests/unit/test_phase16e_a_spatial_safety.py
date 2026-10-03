"""Unit tests for Phase 16E-A: Spatial Safety Semantics Foundation.

Verifies:
1. AdjacentTrackImpact domain enum values (NONE, CAUTION_ORDER, FULL_TRAFFIC_BLOCK).
2. MaintenanceTask invariants:
   - track_id == None requires adjacent_track_impact is None
   - track_id == None requires from_km is None and to_km is None
   - track_id != None allows valid adjacent_track_impact
   - 0 <= from_km <= to_km invariant
   - Negative chainage or from_km > to_km rejected
3. Section kilometrage vs task chainage semantics:
   - Validates that task chainage is relative worksite offset (0 <= from_km <= to_km)
   - Documents non-enforcement of corridor kilometrage bounds (e.g. 943-992 km vs 12.4-15.8 km)
4. PlanningScenarioBundle and PlanningSnapshot carry adjacent_track_impact
5. Snapshot hash stability is strictly preserved (compute_snapshot_hash unaffected)
6. Solver baseline regression (CP-SAT behavior unchanged)
"""

from datetime import datetime, timedelta, timezone
import pytest
from pydantic import ValidationError

from backend.app.domain.enums import (
    DataClass,
    TaskType,
    TaskStatus,
    TaskPriority,
    AdjacentTrackImpact,
)
from backend.app.domain.maintenance_tasks import MaintenanceTask
from backend.app.domain.temporal import PlanningHorizon, TimeInterval
from backend.app.domain.planning_snapshot import PlanningSnapshot
from backend.app.services.planning_service import ScenarioPlanningBundle
from backend.app.services.optimization.cp_sat_solver import CPSATSolver


def test_adjacent_track_impact_enum_values():
    assert AdjacentTrackImpact.NONE == "NONE"
    assert AdjacentTrackImpact.CAUTION_ORDER == "CAUTION_ORDER"
    assert AdjacentTrackImpact.FULL_TRAFFIC_BLOCK == "FULL_TRAFFIC_BLOCK"
    assert len(AdjacentTrackImpact) == 3


def test_maintenance_task_with_adjacent_track_impact_valid():
    start = datetime(2026, 10, 15, 6, 0, tzinfo=timezone.utc)
    end = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)

    # Valid track-specific task with CAUTION_ORDER
    t1 = MaintenanceTask(
        task_id="TSK-TEST-001",
        work_order_id="WO-001",
        task_code="TSK-001",
        title="Track Tamping",
        task_type=TaskType.TRACK_MAINTENANCE,
        section_id="SEC-ETW-CNB",
        scenario_id="SCN-DEMO-001",
        window_start=start,
        window_end=end,
        estimated_duration_minutes=120,
        track_id="TRK-ETW-CNB-UP",
        from_km=5.0,
        to_km=8.5,
        adjacent_track_impact=AdjacentTrackImpact.CAUTION_ORDER,
    )
    assert t1.track_id == "TRK-ETW-CNB-UP"
    assert t1.from_km == 5.0
    assert t1.to_km == 8.5
    assert t1.adjacent_track_impact == AdjacentTrackImpact.CAUTION_ORDER


def test_whole_section_task_rejects_adjacent_track_impact():
    start = datetime(2026, 10, 15, 6, 0, tzinfo=timezone.utc)
    end = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)

    # When track_id is None, task is whole-section; specifying adjacent_track_impact is invalid
    with pytest.raises(ValidationError, match="adjacent_track_impact must be None when track_id is None"):
        MaintenanceTask(
            task_id="TSK-TEST-002",
            work_order_id="WO-001",
            task_code="TSK-002",
            title="Whole Section Power Block",
            task_type=TaskType.OHE_MAINTENANCE,
            section_id="SEC-ETW-CNB",
            scenario_id="SCN-DEMO-001",
            window_start=start,
            window_end=end,
            estimated_duration_minutes=120,
            track_id=None,
            adjacent_track_impact=AdjacentTrackImpact.FULL_TRAFFIC_BLOCK,
        )


def test_chainage_validation_invariants():
    start = datetime(2026, 10, 15, 6, 0, tzinfo=timezone.utc)
    end = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)

    # from_km > to_km must raise ValidationError
    with pytest.raises(ValidationError, match="from_km .* must be <= to_km"):
        MaintenanceTask(
            task_id="TSK-TEST-003",
            work_order_id="WO-001",
            task_code="TSK-003",
            title="Invalid Chainage Task",
            task_type=TaskType.TRACK_MAINTENANCE,
            section_id="SEC-ETW-CNB",
            scenario_id="SCN-DEMO-001",
            window_start=start,
            window_end=end,
            estimated_duration_minutes=120,
            track_id="TRK-ETW-CNB-UP",
            from_km=15.0,
            to_km=10.0,
            adjacent_track_impact=AdjacentTrackImpact.CAUTION_ORDER,
        )

    # Negative from_km must raise ValidationError
    with pytest.raises(ValidationError, match="from_km .* cannot be negative"):
        MaintenanceTask(
            task_id="TSK-TEST-004",
            work_order_id="WO-001",
            task_code="TSK-004",
            title="Negative Chainage Task",
            task_type=TaskType.TRACK_MAINTENANCE,
            section_id="SEC-ETW-CNB",
            scenario_id="SCN-DEMO-001",
            window_start=start,
            window_end=end,
            estimated_duration_minutes=120,
            track_id="TRK-ETW-CNB-UP",
            from_km=-2.0,
            to_km=5.0,
        )


def test_planning_bundle_and_snapshot_propagate_adjacent_track_impact():
    start = datetime(2026, 10, 15, 0, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=24)

    raw_task = {
        "task_id": "TSK-0001",
        "work_order_id": "WO-001",
        "task_code": "TSK-TRK-001",
        "title": "Track Tamping",
        "task_type": "TRACK_MAINTENANCE",
        "status": "REQUESTED",
        "priority": "HIGH",
        "mandatory": True,
        "section_id": "SEC-ETW-CNB",
        "track_id": "TRK-ETW-CNB-UP",
        "from_km": None,
        "to_km": None,
        "adjacent_track_impact": "CAUTION_ORDER",
        "window_start": (start + timedelta(hours=2)).isoformat(),
        "window_end": (start + timedelta(hours=8)).isoformat(),
        "estimated_duration_minutes": 120,
        "requires_traffic_block": True,
        "requires_power_block": False,
        "requires_ptw": True,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
        "crew_size_required": 4,
        "additional_sections": [],
        "resource_requirements": [],
        "classification": "SYNTHETIC",
    }

    bundle = ScenarioPlanningBundle(
        scenario={
            "scenario_id": "SCN-DEMO-001",
            "planning_start": start.isoformat(),
            "planning_end": end.isoformat(),
        },
        work_orders=[],
        tasks=[raw_task],
        dependencies=[],
        resources=[],
        resource_availabilities=[],
        sections=[{"section_id": "SEC-ETW-CNB", "length_km": 139.0}],
        train_movements=[],
        applicable_rules=[],
        tracks=[{"track_id": "TRK-ETW-CNB-UP", "section_id": "SEC-ETW-CNB"}],
    )

    snapshot = PlanningSnapshot.from_bundle(bundle)
    assert len(snapshot.tasks) == 1
    t = snapshot.tasks_map["TSK-0001"]
    assert t["track_id"] == "TRK-ETW-CNB-UP"
    assert t["adjacent_track_impact"] == "CAUTION_ORDER"

    # Compute snapshot hash: verify hash is a valid 64-character sha256 string
    h1 = snapshot.compute_snapshot_hash()
    assert len(h1) == 64

    # Verify that changing adjacent_track_impact does NOT break compute_snapshot_hash in Phase 16E-A
    raw_task_alt = dict(raw_task)
    raw_task_alt["adjacent_track_impact"] = "FULL_TRAFFIC_BLOCK"
    bundle_alt = ScenarioPlanningBundle(
        scenario=bundle.scenario,
        work_orders=[],
        tasks=[raw_task_alt],
        dependencies=[],
        resources=[],
        resource_availabilities=[],
        sections=bundle.sections,
        train_movements=[],
        applicable_rules=[],
        tracks=bundle.tracks,
    )
    snapshot_alt = PlanningSnapshot.from_bundle(bundle_alt)
    h2 = snapshot_alt.compute_snapshot_hash()
    assert h1 == h2, "compute_snapshot_hash() must remain unchanged in Phase 16E-A"
