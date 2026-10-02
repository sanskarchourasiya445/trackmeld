import pytest
from datetime import datetime, timezone, timedelta
from backend.app.domain.temporal import TimeInterval, PlanningHorizon, TrainPass
from backend.app.domain.compatibility import (
    ConstraintSeverity,
    ReasonCode,
    ScheduledTaskPlacement,
)
from backend.app.domain.enums import RuleClass, DataClass
from backend.app.services.compatibility_service import CompatibilityEngine


@pytest.fixture
def base_horizon():
    start = datetime(2026, 10, 10, 0, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=72)
    return PlanningHorizon(start=start, end=end)


@pytest.fixture
def sample_task():
    return {
        "task_id": "TSK-TEST-001",
        "task_code": "TSK-TRK-001",
        "section_id": "SEC-NDLS-GZB",
        "additional_sections": ["SEC-GZB-KRJ"],
        "window_start": "2026-10-10T08:00:00Z",
        "window_end": "2026-10-10T16:00:00Z",
        "estimated_duration_minutes": 120,
        "requires_traffic_block": True,
        "requires_power_block": True,
        "safety_buffer_before_minutes": 15,
        "safety_buffer_after_minutes": 15,
        "resource_requirements": [
            {"requirement_id": "REQ-01", "resource_id": "RES-TM-01", "mandatory": True}
        ],
        "rule_references": [{"rule_id": "RULE-STAT-01"}],
    }


def test_zero_duration_interval_rejected(base_horizon, sample_task):
    t = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)
    res = CompatibilityEngine.evaluate_task_placement(
        task=sample_task,
        candidate_start=t,
        candidate_end=t,
        horizon=base_horizon,
        train_passes=[],
        existing_placements=[],
        resource_availabilities=[],
        dependencies=[],
        sections_map={},
        rules_map={},
    )
    assert not res.compatible
    assert not res.feasible_hard
    assert ReasonCode.INVALID_INTERVAL in res.reason_codes


def test_negative_duration_interval_rejected(base_horizon, sample_task):
    t_start = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)
    res = CompatibilityEngine.evaluate_task_placement(
        task=sample_task,
        candidate_start=t_start,
        candidate_end=t_end,
        horizon=base_horizon,
        train_passes=[],
        existing_placements=[],
        resource_availabilities=[],
        dependencies=[],
        sections_map={},
        rules_map={},
    )
    assert not res.compatible
    assert not res.feasible_hard
    assert ReasonCode.INVALID_INTERVAL in res.reason_codes


def test_task_outside_allowed_window(base_horizon, sample_task):
    # Task window is 08:00 - 16:00; evaluate at 18:00 - 20:00
    t_start = datetime(2026, 10, 10, 18, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 10, 20, 0, tzinfo=timezone.utc)
    res = CompatibilityEngine.evaluate_task_placement(
        task=sample_task,
        candidate_start=t_start,
        candidate_end=t_end,
        horizon=base_horizon,
        train_passes=[],
        existing_placements=[],
        resource_availabilities=[],
        dependencies=[],
        sections_map={},
        rules_map={},
    )
    assert not res.compatible
    assert ReasonCode.TASK_WINDOW_CONFLICT in res.reason_codes


def test_task_outside_planning_horizon(sample_task):
    h_start = datetime(2026, 10, 10, 0, 0, tzinfo=timezone.utc)
    h_end = h_start + timedelta(hours=24)
    horizon = PlanningHorizon(start=h_start, end=h_end)

    # Placed on day 2
    t_start = datetime(2026, 10, 11, 10, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)
    res = CompatibilityEngine.evaluate_task_placement(
        task=sample_task,
        candidate_start=t_start,
        candidate_end=t_end,
        horizon=horizon,
        train_passes=[],
        existing_placements=[],
        resource_availabilities=[],
        dependencies=[],
        sections_map={},
        rules_map={},
    )
    assert not res.compatible
    assert ReasonCode.OUTSIDE_PLANNING_HORIZON in res.reason_codes


def test_train_crossing_task_interval(base_horizon, sample_task):
    # Task placed 10:00 - 12:00 (possession with 15m buffers is 09:45 - 12:15)
    t_start = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)

    # Train crosses section SEC-NDLS-GZB from 10:30 to 11:00
    pass_int = TimeInterval(
        start=datetime(2026, 10, 10, 10, 30, tzinfo=timezone.utc),
        end=datetime(2026, 10, 10, 11, 0, tzinfo=timezone.utc),
    )
    train_pass = TrainPass(
        pass_id="PASS-12301",
        train_id="TRN-12301",
        train_number="12301",
        section_id="SEC-NDLS-GZB",
        interval=pass_int,
    )

    res = CompatibilityEngine.evaluate_task_placement(
        task=sample_task,
        candidate_start=t_start,
        candidate_end=t_end,
        horizon=base_horizon,
        train_passes=[train_pass],
        existing_placements=[],
        resource_availabilities=[
            {"resource_id": "RES-TM-01", "available_from": "2026-10-10T00:00:00Z", "available_until": "2026-10-10T23:59:59Z", "availability_status": "AVAILABLE"}
        ],
        dependencies=[],
        sections_map={"SEC-NDLS-GZB": {"electrified": True}, "SEC-GZB-KRJ": {"electrified": True}},
        rules_map={},
    )
    assert not res.compatible
    assert ReasonCode.TRAIN_MOVEMENT_CONFLICT in res.reason_codes
    assert "TRN-12301" in res.affected_movements


def test_train_ending_exactly_when_possession_starts(base_horizon, sample_task):
    # Task placed 10:00 - 12:00 with 15m buffer -> possession starts at 09:45
    t_start = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)

    # Train clears section at exactly 09:45 [09:15, 09:45)
    pass_int = TimeInterval(
        start=datetime(2026, 10, 10, 9, 15, tzinfo=timezone.utc),
        end=datetime(2026, 10, 10, 9, 45, tzinfo=timezone.utc),
    )
    train_pass = TrainPass(
        pass_id="PASS-12301",
        train_id="TRN-12301",
        train_number="12301",
        section_id="SEC-NDLS-GZB",
        interval=pass_int,
    )

    res = CompatibilityEngine.evaluate_task_placement(
        task=sample_task,
        candidate_start=t_start,
        candidate_end=t_end,
        horizon=base_horizon,
        train_passes=[train_pass],
        existing_placements=[],
        resource_availabilities=[
            {"resource_id": "RES-TM-01", "available_from": "2026-10-10T00:00:00Z", "available_until": "2026-10-10T23:59:59Z", "availability_status": "AVAILABLE"}
        ],
        dependencies=[],
        sections_map={"SEC-NDLS-GZB": {"electrified": True}, "SEC-GZB-KRJ": {"electrified": True}},
        rules_map={},
    )
    # Under half-open semantics [09:15, 09:45) and [09:45, 12:15) do NOT overlap!
    assert ReasonCode.TRAIN_MOVEMENT_CONFLICT not in res.reason_codes


def test_task_possession_ending_exactly_when_train_starts(base_horizon, sample_task):
    # Task placed 10:00 - 12:00 with 15m buffer -> possession ends at 12:15
    t_start = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)

    # Train enters section at exactly 12:15 [12:15, 12:45)
    pass_int = TimeInterval(
        start=datetime(2026, 10, 10, 12, 15, tzinfo=timezone.utc),
        end=datetime(2026, 10, 10, 12, 45, tzinfo=timezone.utc),
    )
    train_pass = TrainPass(
        pass_id="PASS-12302",
        train_id="TRN-12302",
        train_number="12302",
        section_id="SEC-NDLS-GZB",
        interval=pass_int,
    )

    res = CompatibilityEngine.evaluate_task_placement(
        task=sample_task,
        candidate_start=t_start,
        candidate_end=t_end,
        horizon=base_horizon,
        train_passes=[train_pass],
        existing_placements=[],
        resource_availabilities=[
            {"resource_id": "RES-TM-01", "available_from": "2026-10-10T00:00:00Z", "available_until": "2026-10-10T23:59:59Z", "availability_status": "AVAILABLE"}
        ],
        dependencies=[],
        sections_map={"SEC-NDLS-GZB": {"electrified": True}, "SEC-GZB-KRJ": {"electrified": True}},
        rules_map={},
    )
    assert ReasonCode.TRAIN_MOVEMENT_CONFLICT not in res.reason_codes


def test_resource_unavailable(base_horizon, sample_task):
    t_start = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)

    # Resource availability is only from 14:00 to 18:00
    res_avail = [
        {
            "resource_id": "RES-TM-01",
            "available_from": "2026-10-10T14:00:00Z",
            "available_until": "2026-10-10T18:00:00Z",
            "availability_status": "AVAILABLE",
        }
    ]

    res = CompatibilityEngine.evaluate_task_placement(
        task=sample_task,
        candidate_start=t_start,
        candidate_end=t_end,
        horizon=base_horizon,
        train_passes=[],
        existing_placements=[],
        resource_availabilities=res_avail,
        dependencies=[],
        sections_map={"SEC-NDLS-GZB": {"electrified": True}, "SEC-GZB-KRJ": {"electrified": True}},
        rules_map={},
    )
    assert not res.compatible
    assert ReasonCode.RESOURCE_UNAVAILABLE in res.reason_codes


def test_resource_availability_exact_boundary(base_horizon, sample_task):
    t_start = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)

    # Resource available exactly from 10:00 to 12:00
    res_avail = [
        {
            "resource_id": "RES-TM-01",
            "available_from": "2026-10-10T10:00:00Z",
            "available_until": "2026-10-10T12:00:00Z",
            "availability_status": "AVAILABLE",
        }
    ]

    res = CompatibilityEngine.evaluate_task_placement(
        task=sample_task,
        candidate_start=t_start,
        candidate_end=t_end,
        horizon=base_horizon,
        train_passes=[],
        existing_placements=[],
        resource_availabilities=res_avail,
        dependencies=[],
        sections_map={"SEC-NDLS-GZB": {"electrified": True}, "SEC-GZB-KRJ": {"electrified": True}},
        rules_map={},
    )
    assert ReasonCode.RESOURCE_UNAVAILABLE not in res.reason_codes


def test_two_tasks_sharing_primary_section(base_horizon, sample_task):
    t_start = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)

    # Another task already occupies SEC-NDLS-GZB from 11:00 to 13:00
    other_possession = TimeInterval(
        start=datetime(2026, 10, 10, 10, 45, tzinfo=timezone.utc),
        end=datetime(2026, 10, 10, 13, 15, tzinfo=timezone.utc),
    )
    existing = ScheduledTaskPlacement(
        task_id="TSK-OTHER-002",
        task_code="TSK-OTHER-002",
        section_id="SEC-NDLS-GZB",
        interval=TimeInterval(start=datetime(2026, 10, 10, 11, 0, tzinfo=timezone.utc), end=datetime(2026, 10, 10, 13, 0, tzinfo=timezone.utc)),
        possession_interval=other_possession,
    )

    res = CompatibilityEngine.evaluate_task_placement(
        task=sample_task,
        candidate_start=t_start,
        candidate_end=t_end,
        horizon=base_horizon,
        train_passes=[],
        existing_placements=[existing],
        resource_availabilities=[
            {"resource_id": "RES-TM-01", "available_from": "2026-10-10T00:00:00Z", "available_until": "2026-10-10T23:59:59Z", "availability_status": "AVAILABLE"}
        ],
        dependencies=[],
        sections_map={"SEC-NDLS-GZB": {"electrified": True}, "SEC-GZB-KRJ": {"electrified": True}},
        rules_map={},
    )
    assert not res.compatible
    assert ReasonCode.SECTION_OCCUPANCY_CONFLICT in res.reason_codes


def test_multi_section_overlap(base_horizon, sample_task):
    # sample_task has primary SEC-NDLS-GZB and additional SEC-GZB-KRJ
    t_start = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)

    # Other task occupies SEC-GZB-KRJ at the same time
    other_possession = TimeInterval(
        start=datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc),
        end=datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc),
    )
    existing = ScheduledTaskPlacement(
        task_id="TSK-MULTI-003",
        task_code="TSK-MULTI-003",
        section_id="SEC-GZB-KRJ",
        interval=other_possession,
        possession_interval=other_possession,
    )

    res = CompatibilityEngine.evaluate_task_placement(
        task=sample_task,
        candidate_start=t_start,
        candidate_end=t_end,
        horizon=base_horizon,
        train_passes=[],
        existing_placements=[existing],
        resource_availabilities=[
            {"resource_id": "RES-TM-01", "available_from": "2026-10-10T00:00:00Z", "available_until": "2026-10-10T23:59:59Z", "availability_status": "AVAILABLE"}
        ],
        dependencies=[],
        sections_map={"SEC-NDLS-GZB": {"electrified": True}, "SEC-GZB-KRJ": {"electrified": True}},
        rules_map={},
    )
    assert not res.compatible
    assert ReasonCode.MULTI_SECTION_CONFLICT in res.reason_codes


def test_dependency_ordering_violation(base_horizon, sample_task):
    # Candidate starts at 10:00
    t_start = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)

    # Predecessor finishes at 10:30 (violates FINISH_TO_START)
    pred_placement = ScheduledTaskPlacement(
        task_id="TSK-PRED-001",
        task_code="TSK-PRED-001",
        section_id="SEC-SOME-OTHER",
        interval=TimeInterval(start=datetime(2026, 10, 10, 8, 30, tzinfo=timezone.utc), end=datetime(2026, 10, 10, 10, 30, tzinfo=timezone.utc)),
        possession_interval=TimeInterval(start=datetime(2026, 10, 10, 8, 15, tzinfo=timezone.utc), end=datetime(2026, 10, 10, 10, 45, tzinfo=timezone.utc)),
    )
    deps = [{"predecessor_task_id": "TSK-PRED-001", "successor_task_id": "TSK-TEST-001"}]

    res = CompatibilityEngine.evaluate_task_placement(
        task=sample_task,
        candidate_start=t_start,
        candidate_end=t_end,
        horizon=base_horizon,
        train_passes=[],
        existing_placements=[pred_placement],
        resource_availabilities=[
            {"resource_id": "RES-TM-01", "available_from": "2026-10-10T00:00:00Z", "available_until": "2026-10-10T23:59:59Z", "availability_status": "AVAILABLE"}
        ],
        dependencies=deps,
        sections_map={"SEC-NDLS-GZB": {"electrified": True}, "SEC-GZB-KRJ": {"electrified": True}},
        rules_map={},
    )
    assert not res.compatible
    assert ReasonCode.DEPENDENCY_NOT_SATISFIED in res.reason_codes


def test_dependency_ordering_satisfied_at_exact_boundary(base_horizon, sample_task):
    # Candidate starts at exactly 10:00
    t_start = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)

    # Predecessor finishes at exactly 10:00
    pred_placement = ScheduledTaskPlacement(
        task_id="TSK-PRED-001",
        task_code="TSK-PRED-001",
        section_id="SEC-SOME-OTHER",
        interval=TimeInterval(start=datetime(2026, 10, 10, 8, 0, tzinfo=timezone.utc), end=datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)),
        possession_interval=TimeInterval(start=datetime(2026, 10, 10, 7, 45, tzinfo=timezone.utc), end=datetime(2026, 10, 10, 10, 15, tzinfo=timezone.utc)),
    )
    deps = [{"predecessor_task_id": "TSK-PRED-001", "successor_task_id": "TSK-TEST-001"}]

    res = CompatibilityEngine.evaluate_task_placement(
        task=sample_task,
        candidate_start=t_start,
        candidate_end=t_end,
        horizon=base_horizon,
        train_passes=[],
        existing_placements=[pred_placement],
        resource_availabilities=[
            {"resource_id": "RES-TM-01", "available_from": "2026-10-10T00:00:00Z", "available_until": "2026-10-10T23:59:59Z", "availability_status": "AVAILABLE"}
        ],
        dependencies=deps,
        sections_map={"SEC-NDLS-GZB": {"electrified": True}, "SEC-GZB-KRJ": {"electrified": True}},
        rules_map={},
    )
    # Predecessor end == candidate start is valid FINISH_TO_START
    assert ReasonCode.DEPENDENCY_NOT_SATISFIED not in res.reason_codes


def test_power_block_on_non_electrified_section(base_horizon, sample_task):
    t_start = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)

    # Section is NOT electrified
    sections_map = {
        "SEC-NDLS-GZB": {"electrified": False},
        "SEC-GZB-KRJ": {"electrified": True},
    }

    res = CompatibilityEngine.evaluate_task_placement(
        task=sample_task,
        candidate_start=t_start,
        candidate_end=t_end,
        horizon=base_horizon,
        train_passes=[],
        existing_placements=[],
        resource_availabilities=[
            {"resource_id": "RES-TM-01", "available_from": "2026-10-10T00:00:00Z", "available_until": "2026-10-10T23:59:59Z", "availability_status": "AVAILABLE"}
        ],
        dependencies=[],
        sections_map=sections_map,
        rules_map={},
    )
    assert not res.compatible
    assert ReasonCode.POWER_BLOCK_REQUIRED in res.reason_codes


def test_unverified_rule_never_becomes_hard_constraint(base_horizon, sample_task):
    # Rule with unknown authority
    unverified_rule = {
        "rule_id": "RULE-UNVERIFIED-99",
        "title": "Unverified speed restriction heuristic",
        "rule_class": "UNVERIFIED",
        "source_id": "SRC-UNOFFICIAL",
    }
    sample_task_unverified = dict(sample_task)
    sample_task_unverified["rule_references"] = [{"rule_id": "RULE-UNVERIFIED-99"}]

    t_start = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)

    res = CompatibilityEngine.evaluate_task_placement(
        task=sample_task_unverified,
        candidate_start=t_start,
        candidate_end=t_end,
        horizon=base_horizon,
        train_passes=[],
        existing_placements=[],
        resource_availabilities=[
            {"resource_id": "RES-TM-01", "available_from": "2026-10-10T00:00:00Z", "available_until": "2026-10-10T23:59:59Z", "availability_status": "AVAILABLE"}
        ],
        dependencies=[],
        sections_map={"SEC-NDLS-GZB": {"electrified": True}, "SEC-GZB-KRJ": {"electrified": True}},
        rules_map={"RULE-UNVERIFIED-99": unverified_rule},
    )

    # Invariant: Unverified rules never make the task incompatible!
    assert res.compatible
    assert res.feasible_hard
    assert ReasonCode.UNVERIFIED_RULE in res.reason_codes
    assert any(re.severity == ConstraintSeverity.UNVERIFIED for re in res.rule_evidence)
