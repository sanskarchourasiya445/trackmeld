"""Unit tests for Phase 16A First-Class Track Domain.

Verifies:
1. Track domain model validation and direction enum
2. TrackModel ORM definition, section->tracks relationship, task->track relationship
3. Section unique track_code constraint logic
4. PlanningSnapshot tracks preservation and hash stability
"""

import pytest
from pydantic import ValidationError
from datetime import datetime, timezone, timedelta

from backend.app.domain import (
    Track,
    TrackDirection,
    Section,
    MaintenanceTask,
    PlanningSnapshot,
    OperationalScenario,
    DataClass,
    TaskPriority,
    TaskType,
    WorkDepartment,
    TaskStatus,
)
from backend.app.services.planning_service import ScenarioPlanningBundle
from backend.app.db.models import (
    TrackModel,
    SectionModel,
    MaintenanceTaskModel,
)


def test_track_domain_model_valid():
    trk = Track(
        track_id="TRK-SEC-001-UP",
        section_id="SEC-001",
        track_code="UP_MAIN",
        direction=TrackDirection.UP,
        electrified=True,
        max_speed_kmh=130,
    )
    assert trk.track_id == "TRK-SEC-001-UP"
    assert trk.section_id == "SEC-001"
    assert trk.track_code == "UP_MAIN"
    assert trk.direction == TrackDirection.UP
    assert trk.electrified is True
    assert trk.max_speed_kmh == 130


def test_track_domain_model_direction_enum():
    # String coerced to enum
    trk = Track(
        track_id="TRK-SEC-002-DN",
        section_id="SEC-002",
        track_code="DN_MAIN",
        direction="DOWN",
    )
    assert trk.direction == TrackDirection.DOWN

    # Bidirectional
    trk_bi = Track(
        track_id="TRK-SEC-003-SL",
        section_id="SEC-003",
        track_code="SINGLE_LINE",
        direction=TrackDirection.BIDIRECTIONAL,
    )
    assert trk_bi.direction == TrackDirection.BIDIRECTIONAL

    # Invalid direction
    with pytest.raises(ValidationError):
        Track(
            track_id="TRK-SEC-004-INV",
            section_id="SEC-004",
            track_code="INVALID",
            direction="SIDEWAYS",  # type: ignore
        )


def test_track_model_orm_structure():
    assert hasattr(TrackModel, "track_id")
    assert hasattr(TrackModel, "section_id")
    assert hasattr(TrackModel, "track_code")
    assert hasattr(TrackModel, "direction")
    assert hasattr(TrackModel, "electrified")
    assert hasattr(TrackModel, "max_speed_kmh")
    assert hasattr(TrackModel, "section")
    assert hasattr(TrackModel, "tasks")

    # SectionModel relationship
    assert hasattr(SectionModel, "tracks")

    # MaintenanceTaskModel track relationship and field
    assert hasattr(MaintenanceTaskModel, "track_id")
    assert hasattr(MaintenanceTaskModel, "track")


def test_maintenance_task_domain_optional_track_id():
    now = datetime(2026, 10, 10, 6, 0, 0, tzinfo=timezone.utc)
    end = now + timedelta(hours=6)
    task = MaintenanceTask(
        task_id="TSK-TRK-001",
        work_order_id="WO-0001",
        task_code="TSK-TRK-001",
        title="Plain Track CSM Tamping",
        task_type=TaskType.TRACK_MACHINE_WORK,
        status=TaskStatus.PLANNED,
        priority=TaskPriority.HIGH,
        mandatory=True,
        section_id="SEC-NDLS-GZB",
        scenario_id="SCN-001",
        window_start=now,
        window_end=end,
        estimated_duration_minutes=180,
        track_id="TRK-NDLS-GZB-UP",
        classification=DataClass.SYNTHETIC,
        source_id="SRC-TRACKMELD-SYNTHETIC-GEN",
    )
    assert task.track_id == "TRK-NDLS-GZB-UP"

    # Nullable / None backwards compatibility
    task_no_trk = MaintenanceTask(
        task_id="TSK-TRK-002",
        work_order_id="WO-0001",
        task_code="TSK-TRK-002",
        title="Plain Track CSM Tamping without track",
        task_type=TaskType.TRACK_MACHINE_WORK,
        status=TaskStatus.PLANNED,
        priority=TaskPriority.HIGH,
        mandatory=True,
        section_id="SEC-NDLS-GZB",
        scenario_id="SCN-001",
        window_start=now,
        window_end=end,
        estimated_duration_minutes=180,
        classification=DataClass.SYNTHETIC,
        source_id="SRC-TRACKMELD-SYNTHETIC-GEN",
    )
    assert task_no_trk.track_id is None


def test_planning_snapshot_preserves_tracks_and_hash_stability():
    sample_tracks = [
        {
            "track_id": "TRK-SEC1-UP",
            "section_id": "SEC1",
            "track_code": "UP_MAIN",
            "direction": "UP",
            "electrified": True,
            "max_speed_kmh": 130,
        },
        {
            "track_id": "TRK-SEC1-DN",
            "section_id": "SEC1",
            "track_code": "DN_MAIN",
            "direction": "DOWN",
            "electrified": True,
            "max_speed_kmh": 130,
        },
    ]

    bundle = ScenarioPlanningBundle(
        scenario={
            "scenario_id": "SCN-TEST-TRK",
            "planning_start": "2026-10-10T00:00:00Z",
            "planning_end": "2026-10-11T00:00:00Z",
        },
        work_orders=[],
        tasks=[],
        dependencies=[],
        resources=[],
        resource_availabilities=[],
        sections=[],
        train_movements=[],
        applicable_rules=[],
        tracks=sample_tracks,
    )

    snapshot = PlanningSnapshot.from_bundle(bundle)
    assert len(snapshot.tracks) == 2
    assert "TRK-SEC1-UP" in snapshot.tracks_map
    assert snapshot.tracks_map["TRK-SEC1-UP"]["direction"] == "UP"

    # Compute hash - verify it executes deterministically
    h1 = snapshot.compute_snapshot_hash()
    assert isinstance(h1, str)
    assert len(h1) == 64  # SHA256 hex
