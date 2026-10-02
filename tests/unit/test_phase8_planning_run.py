"""Unit tests for Phase 8 Planning Jobs, Lifecycle Transitions, and Reproducibility Hashing."""

import pytest
from datetime import datetime, timezone, timedelta

from backend.app.schemas.planning_run import (
    PlanningRunStatus,
    PlanningRunStage,
    CreatePlanningRunRequest,
    PlanningRunProgress,
)
from backend.app.domain.scheduling import (
    SchedulerType,
    PriorityConfig,
    TimeInterval,
)
from backend.app.domain.temporal import PlanningHorizon, TrainPass
from backend.app.domain.planning_snapshot import PlanningSnapshot
from backend.app.repositories.planning_run_repo import (
    LEGAL_TRANSITIONS,
    IllegalStateTransitionError,
    PlanningRunRepository,
)
from backend.app.api.v1.planning_runs import _map_to_progress
from backend.app.db.models.planning_run import PlanningRunModel


# -----------------------------------------------------------------------------
# FIXTURES
# -----------------------------------------------------------------------------

@pytest.fixture
def sample_horizon():
    start = datetime(2026, 10, 15, 0, 0, tzinfo=timezone.utc)
    return PlanningHorizon(start=start, end=start + timedelta(hours=24))


@pytest.fixture
def dummy_snapshot(sample_horizon):
    t1 = {
        "task_id": "TSK-01",
        "task_code": "TC-01",
        "section_id": "SEC-01",
        "priority": "HIGH",
        "mandatory": True,
        "window_start": sample_horizon.start + timedelta(hours=2),
        "window_end": sample_horizon.start + timedelta(hours=8),
        "estimated_duration_minutes": 120,
    }
    t2 = {
        "task_id": "TSK-02",
        "task_code": "TC-02",
        "section_id": "SEC-02",
        "priority": "MEDIUM",
        "mandatory": False,
        "window_start": sample_horizon.start + timedelta(hours=4),
        "window_end": sample_horizon.start + timedelta(hours=12),
        "estimated_duration_minutes": 60,
    }
    tp = TrainPass(
        pass_id="PASS-01",
        train_id="TRN-01",
        train_number="12004",
        section_id="SEC-01",
        interval=TimeInterval(start=sample_horizon.start + timedelta(hours=10), end=sample_horizon.start + timedelta(hours=11)),
    )
    return PlanningSnapshot(
        scenario_id="SCN-TEST-001",
        snapshot_id="SNAP-TEST-001",
        horizon=sample_horizon,
        tasks=[t1, t2],
        tasks_map={"TSK-01": t1, "TSK-02": t2},
        work_orders_map={},
        resources=[{"resource_id": "RES-01"}],
        resources_map={"RES-01": {"resource_id": "RES-01"}},
        resource_availabilities=[],
        dependencies=[{"predecessor_task_id": "TSK-01", "successor_task_id": "TSK-02"}],
        dependencies_by_successor={"TSK-02": [{"predecessor_task_id": "TSK-01"}]},
        dependencies_by_predecessor={"TSK-01": [{"successor_task_id": "TSK-02"}]},
        sections_map={"SEC-01": {}, "SEC-02": {}},
        rules_map={},
        train_passes=[tp],
    )


# -----------------------------------------------------------------------------
# 1. LIFECYCLE STATE MACHINE & TRANSITIONS
# -----------------------------------------------------------------------------

def test_01_legal_state_transitions():
    """Verify legal state transitions defined in state machine."""
    assert PlanningRunStatus.RUNNING in LEGAL_TRANSITIONS[PlanningRunStatus.PENDING]
    assert PlanningRunStatus.FAILED in LEGAL_TRANSITIONS[PlanningRunStatus.PENDING]
    assert PlanningRunStatus.CANCELLED in LEGAL_TRANSITIONS[PlanningRunStatus.PENDING]

    assert PlanningRunStatus.VALIDATING in LEGAL_TRANSITIONS[PlanningRunStatus.RUNNING]
    assert PlanningRunStatus.FAILED in LEGAL_TRANSITIONS[PlanningRunStatus.RUNNING]
    assert PlanningRunStatus.TIMED_OUT in LEGAL_TRANSITIONS[PlanningRunStatus.RUNNING]

    assert PlanningRunStatus.COMPLETED in LEGAL_TRANSITIONS[PlanningRunStatus.VALIDATING]
    assert PlanningRunStatus.FAILED in LEGAL_TRANSITIONS[PlanningRunStatus.VALIDATING]
    assert PlanningRunStatus.TIMED_OUT in LEGAL_TRANSITIONS[PlanningRunStatus.VALIDATING]


def test_02_illegal_state_transitions():
    """Verify illegal transitions are strictly rejected by the validator."""
    repo = PlanningRunRepository(None)

    # Cannot transition out of terminal state COMPLETED
    with pytest.raises(IllegalStateTransitionError):
        repo.validate_transition(PlanningRunStatus.COMPLETED.value, PlanningRunStatus.RUNNING)

    with pytest.raises(IllegalStateTransitionError):
        repo.validate_transition(PlanningRunStatus.COMPLETED.value, PlanningRunStatus.PENDING)

    # Cannot jump directly from PENDING to COMPLETED (must execute & validate)
    with pytest.raises(IllegalStateTransitionError):
        repo.validate_transition(PlanningRunStatus.PENDING.value, PlanningRunStatus.COMPLETED)

    # Cannot jump from FAILED to VALIDATING
    with pytest.raises(IllegalStateTransitionError):
        repo.validate_transition(PlanningRunStatus.FAILED.value, PlanningRunStatus.VALIDATING)


# -----------------------------------------------------------------------------
# 2. REPRODUCIBILITY HASHING CONTRACTS
# -----------------------------------------------------------------------------

def test_03_snapshot_hash_determinism(dummy_snapshot):
    """Snapshot hash must be 100% deterministic across repeated evaluations."""
    h1 = dummy_snapshot.compute_snapshot_hash()
    h2 = dummy_snapshot.compute_snapshot_hash()

    assert len(h1) == 64
    assert h1 == h2


def test_04_snapshot_hash_sensitivity_to_task_changes(dummy_snapshot, sample_horizon):
    """Mutating task parameters produces a distinctly different snapshot hash."""
    h_orig = dummy_snapshot.compute_snapshot_hash()

    # Create snapshot with modified duration
    modified_task = dict(dummy_snapshot.tasks_map["TSK-01"])
    modified_task["estimated_duration_minutes"] = 999
    snap_mod = PlanningSnapshot(
        scenario_id=dummy_snapshot.scenario_id,
        snapshot_id=dummy_snapshot.snapshot_id,
        horizon=sample_horizon,
        tasks=[modified_task, dummy_snapshot.tasks_map["TSK-02"]],
        tasks_map={"TSK-01": modified_task, "TSK-02": dummy_snapshot.tasks_map["TSK-02"]},
        work_orders_map=dummy_snapshot.work_orders_map,
        resources=dummy_snapshot.resources,
        resources_map=dummy_snapshot.resources_map,
        resource_availabilities=dummy_snapshot.resource_availabilities,
        dependencies=dummy_snapshot.dependencies,
        dependencies_by_successor=dummy_snapshot.dependencies_by_successor,
        dependencies_by_predecessor=dummy_snapshot.dependencies_by_predecessor,
        sections_map=dummy_snapshot.sections_map,
        rules_map=dummy_snapshot.rules_map,
        train_passes=dummy_snapshot.train_passes,
    )

    h_mod = snap_mod.compute_snapshot_hash()
    assert h_orig != h_mod


def test_05_input_hash_determinism(dummy_snapshot):
    """Input hash combines snapshot hash, configuration snapshot, and seed."""
    cfg = {"scheduler_type": "CP_SAT", "time_limit_seconds": 15.0}
    seed = 42

    ih1 = dummy_snapshot.compute_input_hash(cfg, seed=seed)
    ih2 = dummy_snapshot.compute_input_hash(cfg, seed=seed)

    assert len(ih1) == 64
    assert ih1 == ih2

    # Different seed yields different input hash
    ih_diff_seed = dummy_snapshot.compute_input_hash(cfg, seed=99)
    assert ih1 != ih_diff_seed

    # Different config yields different input hash
    cfg_diff = {"scheduler_type": "CP_SAT", "time_limit_seconds": 60.0}
    ih_diff_cfg = dummy_snapshot.compute_input_hash(cfg_diff, seed=seed)
    assert ih1 != ih_diff_cfg


# -----------------------------------------------------------------------------
# 3. CONFIGURATION SNAPSHOT & SCHEMAS
# -----------------------------------------------------------------------------

def test_06_create_planning_run_request_validation():
    """CreatePlanningRunRequest correctly validates input parameters and defaults."""
    req = CreatePlanningRunRequest(
        scenario_id="SCN-DEMO-001",
        scheduler_type=SchedulerType.CP_SAT,
        time_limit_seconds=25.0,
        random_seed=7,
    )
    assert req.scenario_id == "SCN-DEMO-001"
    assert req.scheduler_type == SchedulerType.CP_SAT
    assert req.time_limit_seconds == 25.0
    assert req.random_seed == 7
    assert req.validate_after_solve is True


def test_07_progress_mapping_telemetry():
    """Verify progress telemetry reflects stage progression accurately."""
    run = PlanningRunModel(
        run_id="RUN-TEST-01",
        scenario_id="SCN-TEST-001",
        status=PlanningRunStatus.RUNNING.value,
        stage=PlanningRunStage.SOLVING.value,
        scheduler_type="CP_SAT",
    )
    prog = _map_to_progress(run)
    assert prog.stage == PlanningRunStage.SOLVING
    assert "CP_SAT" in prog.message
    assert prog.percent_complete == 60.0

    run.stage = PlanningRunStage.COMPLETED.value
    run.status = PlanningRunStatus.COMPLETED.value
    prog_comp = _map_to_progress(run)
    assert prog_comp.stage == PlanningRunStage.COMPLETED
    assert prog_comp.percent_complete == 100.0


def test_08_immutable_completed_run_rejection():
    """Attempting to mark a COMPLETED run as failed or timed out raises error."""
    repo = PlanningRunRepository(None)

    with pytest.raises(IllegalStateTransitionError):
        repo.validate_transition(PlanningRunStatus.COMPLETED.value, PlanningRunStatus.FAILED)

    with pytest.raises(IllegalStateTransitionError):
        repo.validate_transition(PlanningRunStatus.COMPLETED.value, PlanningRunStatus.TIMED_OUT)
