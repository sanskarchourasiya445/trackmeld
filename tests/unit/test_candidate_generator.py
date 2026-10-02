"""Unit tests for CandidateGenerator."""

import pytest
from datetime import datetime, timedelta, timezone

from backend.app.domain.planning_snapshot import PlanningSnapshot
from backend.app.domain.temporal import PlanningHorizon, TimeInterval, TrainPass
from backend.app.domain.compatibility import ScheduledTaskPlacement
from backend.app.services.candidate_generator import CandidateGenerator


@pytest.fixture
def test_snapshot():
    now = datetime(2026, 10, 15, 0, 0, tzinfo=timezone.utc)
    horizon = PlanningHorizon(start=now, end=now + timedelta(days=2))

    train_pass = TrainPass(
        pass_id="PASS-TEST-1",
        train_id="TRN-001",
        train_number="12004",
        section_id="SEC-01",
        interval=TimeInterval(start=now + timedelta(hours=3), end=now + timedelta(hours=3, minutes=30)),
    )

    return PlanningSnapshot(
        scenario_id="SCN-TEST",
        snapshot_id="SNAP-TEST-001",
        horizon=horizon,
        tasks=[],
        tasks_map={},
        work_orders_map={},
        resources=[],
        resources_map={},
        resource_availabilities=[
            {
                "resource_id": "RES-01",
                "available_from": (now + timedelta(hours=1)).isoformat(),
                "available_until": (now + timedelta(hours=8)).isoformat(),
            }
        ],
        dependencies=[],
        dependencies_by_successor={},
        dependencies_by_predecessor={},
        sections_map={},
        rules_map={},
        train_passes=[train_pass],
    )


def test_candidate_generation_bounds(test_snapshot):
    now = datetime(2026, 10, 15, 0, 0, tzinfo=timezone.utc)
    task = {
        "task_id": "T-BOUNDS",
        "section_id": "SEC-01",
        "window_start": now + timedelta(hours=2),
        "window_end": now + timedelta(hours=6),
        "estimated_duration_minutes": 60,
    }

    candidates = CandidateGenerator.generate_candidate_starts(
        task=task,
        snapshot=test_snapshot,
        existing_placements=[],
        max_candidates=20,
    )

    assert len(candidates) > 0
    # All candidate starts must allow the 60 min task to finish by window_end
    for c in candidates:
        assert c >= now + timedelta(hours=2)
        assert c + timedelta(minutes=60) <= now + timedelta(hours=6)


def test_candidate_generation_includes_event_boundaries(test_snapshot):
    now = datetime(2026, 10, 15, 0, 0, tzinfo=timezone.utc)
    task = {
        "task_id": "T-EVENTS",
        "section_id": "SEC-01",
        "window_start": now,
        "window_end": now + timedelta(hours=10),
        "preferred_start": now + timedelta(hours=4),
        "estimated_duration_minutes": 60,
        "resource_requirements": [{"resource_id": "RES-01"}],
    }

    candidates = CandidateGenerator.generate_candidate_starts(
        task=task,
        snapshot=test_snapshot,
        existing_placements=[],
        max_candidates=50,
    )

    cand_set = set(candidates)
    # Event 1: Window start
    assert now in cand_set
    # Event 2: Preferred start
    assert now + timedelta(hours=4) in cand_set
    # Event 5: Train pass exit (03:30)
    assert now + timedelta(hours=3, minutes=30) in cand_set
    # Event 6: Resource availability start (01:00)
    assert now + timedelta(hours=1) in cand_set


def test_candidate_generation_insufficient_window(test_snapshot):
    now = datetime(2026, 10, 15, 0, 0, tzinfo=timezone.utc)
    task = {
        "task_id": "T-NARROW",
        "section_id": "SEC-01",
        "window_start": now + timedelta(hours=1),
        "window_end": now + timedelta(hours=1, minutes=30),  # 30 min window
        "estimated_duration_minutes": 60,  # 60 min duration
    }

    candidates = CandidateGenerator.generate_candidate_starts(
        task=task,
        snapshot=test_snapshot,
        existing_placements=[],
    )

    assert candidates == []
