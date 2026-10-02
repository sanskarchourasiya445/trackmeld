"""Unit tests for PriorityScorer and PriorityConfig."""

import pytest
from datetime import datetime, timedelta, timezone

from backend.app.domain.scheduling import (
    PriorityConfig,
    PriorityScore,
    PriorityComponent,
)
from backend.app.domain.planning_snapshot import PlanningSnapshot
from backend.app.domain.temporal import PlanningHorizon
from backend.app.domain.enums import TaskPriority
from backend.app.services.priority_scorer import PriorityScorer


@pytest.fixture
def mock_snapshot():
    now = datetime(2026, 10, 15, 0, 0, tzinfo=timezone.utc)
    horizon = PlanningHorizon(start=now, end=now + timedelta(days=3))
    return PlanningSnapshot(
        scenario_id="SCN-TEST",
        snapshot_id="SNAP-TEST-001",
        horizon=horizon,
        tasks=[],
        tasks_map={},
        work_orders_map={},
        resources=[],
        resources_map={},
        resource_availabilities=[],
        dependencies=[],
        dependencies_by_successor={},
        dependencies_by_predecessor={"TSK-BOTTLENECK": ["TSK-SUCC-1", "TSK-SUCC-2", "TSK-SUCC-3"]},
        sections_map={},
        rules_map={},
        train_passes=[],
    )


def test_score_breakdown_structure(mock_snapshot):
    now = datetime(2026, 10, 15, 0, 0, tzinfo=timezone.utc)
    task = {
        "task_id": "TSK-001",
        "priority": "HIGH",
        "mandatory": True,
        "window_start": now,
        "window_end": now + timedelta(hours=4),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 10,
        "safety_buffer_after_minutes": 10,
        "requires_traffic_block": True,
        "requires_power_block": True,
    }

    score = PriorityScorer.score_task(task, mock_snapshot)
    assert isinstance(score, PriorityScore)
    assert score.task_id == "TSK-001"
    assert "mandatory" in score.components
    assert "urgency" in score.components
    assert "window_tightness" in score.components
    assert "dependency_bottleneck" in score.components
    assert "operational_impact" in score.components

    # Sum of component contributions equals total_score
    calc_sum = sum(c.contribution for c in score.components.values())
    assert abs(score.total_score - calc_sum) < 0.001


def test_mandatory_feature_weight(mock_snapshot):
    now = datetime(2026, 10, 15, 0, 0, tzinfo=timezone.utc)
    task_mand = {
        "task_id": "T-MAND",
        "mandatory": True,
        "priority": "LOW",
        "window_start": now,
        "window_end": now + timedelta(hours=4),
    }
    task_opt = {
        "task_id": "T-OPT",
        "mandatory": False,
        "priority": "LOW",
        "window_start": now,
        "window_end": now + timedelta(hours=4),
    }

    score_mand = PriorityScorer.score_task(task_mand, mock_snapshot)
    score_opt = PriorityScorer.score_task(task_opt, mock_snapshot)

    assert score_mand.components["mandatory"].normalized_value == 1.0
    assert score_mand.components["mandatory"].contribution == 100.0
    assert score_opt.components["mandatory"].normalized_value == 0.0
    assert score_opt.components["mandatory"].contribution == 0.0
    assert score_mand.total_score > score_opt.total_score


def test_urgency_hierarchy(mock_snapshot):
    now = datetime(2026, 10, 15, 0, 0, tzinfo=timezone.utc)
    priors = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    scores = []
    for p in priors:
        t = {
            "task_id": f"T-{p}",
            "priority": p,
            "mandatory": False,
            "window_start": now,
            "window_end": now + timedelta(hours=4),
        }
        scores.append(PriorityScorer.score_task(t, mock_snapshot).components["urgency"].contribution)

    # Strictly descending
    assert scores[0] > scores[1] > scores[2] > scores[3]


def test_dependency_bottleneck_impact(mock_snapshot):
    now = datetime(2026, 10, 15, 0, 0, tzinfo=timezone.utc)
    task_bottle = {
        "task_id": "TSK-BOTTLENECK",
        "mandatory": False,
        "window_start": now,
        "window_end": now + timedelta(hours=4),
    }
    task_leaf = {
        "task_id": "TSK-LEAF",
        "mandatory": False,
        "window_start": now,
        "window_end": now + timedelta(hours=4),
    }

    score_bottle = PriorityScorer.score_task(task_bottle, mock_snapshot)
    score_leaf = PriorityScorer.score_task(task_leaf, mock_snapshot)

    assert score_bottle.components["dependency_bottleneck"].contribution == 20.0  # 3 successors = 1.0 norm * 20
    assert score_leaf.components["dependency_bottleneck"].contribution == 0.0


def test_configurable_weights(mock_snapshot):
    now = datetime(2026, 10, 15, 0, 0, tzinfo=timezone.utc)
    task = {
        "task_id": "TSK-001",
        "mandatory": True,
        "priority": "HIGH",
        "window_start": now,
        "window_end": now + timedelta(hours=4),
    }

    config_custom = PriorityConfig(
        config_id="custom-cfg",
        version="2.0.0",
        mandatory_weight=200.0,
        urgency_weight=10.0,
    )

    score = PriorityScorer.score_task(task, mock_snapshot, config=config_custom)
    assert score.components["mandatory"].weight == 200.0
    assert score.components["mandatory"].contribution == 200.0
    assert score.components["urgency"].weight == 10.0
    assert score.config_id == "custom-cfg"
    assert score.config_version == "2.0.0"


def test_priority_score_determinism(mock_snapshot):
    now = datetime(2026, 10, 15, 0, 0, tzinfo=timezone.utc)
    task = {
        "task_id": "TSK-001",
        "mandatory": True,
        "priority": "HIGH",
        "window_start": now,
        "window_end": now + timedelta(hours=4),
        "estimated_duration_minutes": 90,
    }

    score1 = PriorityScorer.score_task(task, mock_snapshot)
    score2 = PriorityScorer.score_task(task, mock_snapshot)

    assert score1.total_score == score2.total_score
    assert score1.model_dump() == score2.model_dump()
