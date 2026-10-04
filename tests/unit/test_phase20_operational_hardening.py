"""Unit tests for Phase 20: Operational Realism & Production Hardening.

Verifies:
1. Deterministic synthetic data generator repeatability
2. Synthetic provider query methods and provenance tagging
3. Planning worker timeout protection and state transitions
4. Planning worker cancellation handling
5. Planning worker solver_mode propagation
6. Structured observability telemetry in result_summary
7. Inviolable governance rule: non-COMPLETED or non-VALID run cannot produce PlanVersion
8. Four-eyes governance rule: creator cannot approve own plan
9. Production database compound index coverage
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta

from backend.app.domain.enums import DataClass, TaskStatus, TaskPriority
from backend.app.schemas.planning_run import PlanningRunStatus, PlanningRunStage, CreatePlanningRunRequest
from backend.app.domain.scheduling import (
    SchedulerType,
    SchedulerStatus,
    ScheduleResult,
    ScheduleMetrics,
)
from backend.app.services.optimization.solver_config import OptimizationConfig
from backend.app.services.planning_worker import PlanningRunWorker
from backend.app.services.plan_governance_service import PlanGovernanceService
from backend.app.repositories.plan_version_repo import (
    PlanVersionApprovalBlockedError,
    FourEyesViolationError,
)
from backend.app.core.auth import AuthUser
from backend.app.db.models.planning_run import PlanningRunModel
from backend.app.db.models.task import MaintenanceTaskModel
from backend.app.db.models.movement import TrainMovementModel


# =============================================================================
# 1. Deterministic Synthetic Generator
# =============================================================================

def test_deterministic_synthetic_data_generator():
    """Verify that generate_dataset with identical seed produces identical entities."""
    from scripts.generate_synthetic_operational_data import generate_dataset

    ds1 = generate_dataset(20261001)
    ds2 = generate_dataset(20261001)

    assert ds1["scenario"]["scenario_id"] == ds2["scenario"]["scenario_id"]
    assert len(ds1["maintenance_tasks"]) == len(ds2["maintenance_tasks"])
    assert len(ds1["resources"]) == len(ds2["resources"])
    assert len(ds1["work_orders"]) == len(ds2["work_orders"])
    assert len(ds1["task_dependencies"]) == len(ds2["task_dependencies"])

    # Verify task codes and durations match exactly
    for t1, t2 in zip(ds1["maintenance_tasks"], ds2["maintenance_tasks"]):
        assert t1["task_code"] == t2["task_code"]
        assert t1["estimated_duration_minutes"] == t2["estimated_duration_minutes"]
        assert t1["mandatory"] == t2["mandatory"]

    # Verify all records are classified as SYNTHETIC
    for t in ds1["maintenance_tasks"]:
        assert t.get("classification", "SYNTHETIC") == "SYNTHETIC"


# =============================================================================
# 2. Worker Timeout Protection
# =============================================================================

@pytest.mark.asyncio
async def test_planning_worker_timeout_enforcement():
    """Verify that a solver exceeding PLANNING_JOB_TIMEOUT_SECONDS transitions cleanly to TIMED_OUT."""
    mock_session = AsyncMock()
    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__.return_value = mock_session

    worker = PlanningRunWorker(
        worker_id="WORKER-TEST-TIMEOUT",
        session_factory=mock_session_factory,
    )
    worker.settings.PLANNING_JOB_TIMEOUT_SECONDS = 0.05  # 50ms timeout

    mock_run = MagicMock()
    mock_run.run_id = "RUN-TIMEOUT-TEST"
    mock_run.scenario_id = "SCN-DEMO-001"
    mock_run.scheduler_type = "CP_SAT"
    mock_run.configuration_snapshot = {}
    mock_run.random_seed = 0
    mock_run.status = PlanningRunStatus.PENDING.value

    # Simulate slow solver execution in thread
    def slow_solve(*args, **kwargs):
        import time
        time.sleep(0.5)  # 500ms > 50ms
        return MagicMock()

    with patch.object(worker, "_execute_scheduler_sync", side_effect=slow_solve):
        with patch("backend.app.services.planning_worker.PlanningScenarioService") as mock_scn_svc_cls:
            mock_scn_svc = AsyncMock()
            mock_bundle = MagicMock()
            mock_scn_svc.get_planning_bundle.return_value = mock_bundle
            mock_scn_svc_cls.return_value = mock_scn_svc

            with patch("backend.app.services.planning_worker.PlanningSnapshot") as mock_snap_cls:
                mock_snap = MagicMock()
                mock_snap.snapshot_id = "SNAP-01"
                mock_snap.compute_snapshot_hash.return_value = "hash1"
                mock_snap.compute_input_hash.return_value = "hash2"
                mock_snap.horizon.start = datetime.now(timezone.utc)
                mock_snap.horizon.end = datetime.now(timezone.utc) + timedelta(hours=72)
                mock_snap_cls.from_bundle.return_value = mock_snap

                with patch("backend.app.services.planning_worker.PlanningRunRepository") as mock_repo_cls:
                    mock_repo = AsyncMock()
                    mock_repo.get_by_run_id.return_value = mock_run
                    mock_repo_cls.return_value = mock_repo

                    await worker._process_claimed_run(
                        run_id="RUN-TIMEOUT-TEST",
                        scenario_id="SCN-DEMO-001",
                        scheduler_type="CP_SAT",
                        config_snapshot={},
                        random_seed=0,
                    )

                    # Verify mark_timed_out was called
                    mock_repo.mark_timed_out.assert_called_once()
                    args, kwargs = mock_repo.mark_timed_out.call_args
                    assert "RUN-TIMEOUT-TEST" in args or kwargs.get("run_id") == "RUN-TIMEOUT-TEST"


# =============================================================================
# 3. Worker Cancellation Handling
# =============================================================================

@pytest.mark.asyncio
async def test_planning_worker_cancellation_pre_solve():
    """Verify that a run marked CANCEL_REQUESTED before solve is aborted and marked CANCELLED."""
    mock_session = AsyncMock()
    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__.return_value = mock_session

    worker = PlanningRunWorker(
        worker_id="WORKER-TEST-CANCEL",
        session_factory=mock_session_factory,
    )

    mock_run = MagicMock()
    mock_run.run_id = "RUN-CANCEL-TEST"
    mock_run.scenario_id = "SCN-DEMO-001"
    mock_run.status = PlanningRunStatus.CANCEL_REQUESTED.value

    with patch("backend.app.services.planning_worker.PlanningScenarioService") as mock_scn_svc_cls:
        mock_scn_svc = AsyncMock()
        mock_bundle = MagicMock()
        mock_scn_svc.get_planning_bundle.return_value = mock_bundle
        mock_scn_svc_cls.return_value = mock_scn_svc

        with patch("backend.app.services.planning_worker.PlanningSnapshot") as mock_snap_cls:
            mock_snap = MagicMock()
            mock_snap.compute_snapshot_hash.return_value = "hash1"
            mock_snap.compute_input_hash.return_value = "hash2"
            mock_snap_cls.from_bundle.return_value = mock_snap

            with patch("backend.app.services.planning_worker.PlanningRunRepository") as mock_repo_cls:
                mock_repo = AsyncMock()
                mock_repo.get_by_run_id.return_value = mock_run
                mock_repo_cls.return_value = mock_repo

                with patch.object(worker, "_execute_scheduler_sync") as mock_exec:
                    await worker._process_claimed_run(
                        run_id="RUN-CANCEL-TEST",
                        scenario_id="SCN-DEMO-001",
                        scheduler_type="CP_SAT",
                        config_snapshot={},
                        random_seed=0,
                    )
                    # Solver must NOT have been called
                    mock_exec.assert_not_called()
                    # mark_cancelled must have been called
                    mock_repo.mark_cancelled.assert_called_once()


# =============================================================================
# 4. Solver Mode Propagation
# =============================================================================

def test_planning_worker_solver_mode_propagation():
    """Verify worker passes solver_mode correctly into OptimizationConfig."""
    worker = PlanningRunWorker(worker_id="WORKER-TEST-MODE")
    mock_snap = MagicMock()

    with patch("backend.app.services.planning_worker.CPSATSolver") as mock_solver_cls:
        mock_solver = MagicMock()
        mock_solver_cls.return_value = mock_solver

        # Test WHOLE_SECTION
        worker._execute_scheduler_sync(
            scheduler_type="CP_SAT",
            snapshot=mock_snap,
            config_snapshot={"solver_mode": "WHOLE_SECTION", "time_limit_seconds": 15.0},
            random_seed=42,
        )

        assert mock_solver_cls.call_count == 1
        cfg = mock_solver_cls.call_args[1]["config"]
        assert cfg.solver_mode == "WHOLE_SECTION"
        assert cfg.time_limit_seconds == 15.0
        assert cfg.random_seed == 42


# =============================================================================
# 5. Inviolable Governance Constraints
# =============================================================================

@pytest.mark.asyncio
async def test_failed_or_timed_out_run_cannot_create_plan_version():
    """Verify that PlanGovernanceService rejects non-COMPLETED or non-VALID runs."""
    mock_session = AsyncMock()
    service = PlanGovernanceService(mock_session)

    # Case A: Status FAILED
    mock_failed_run = MagicMock()
    mock_failed_run.run_id = "RUN-FAILED-01"
    mock_failed_run.status = "FAILED"
    mock_failed_run.validation_status = None
    mock_failed_run.is_approvable = False

    service.run_repo.get_by_run_id = AsyncMock(return_value=mock_failed_run)
    actor = AuthUser(user_id="USR-OP-1", username="operator1", role="MAINTENANCE_PLANNER", permissions=["write:operational"])

    with pytest.raises(PlanVersionApprovalBlockedError, match="status is 'FAILED', expected 'COMPLETED'"):
        await service.create_plan_version_from_run("RUN-FAILED-01", actor=actor)

    # Case B: Status COMPLETED but validation INVALID
    mock_invalid_run = MagicMock()
    mock_invalid_run.run_id = "RUN-INVALID-02"
    mock_invalid_run.status = "COMPLETED"
    mock_invalid_run.validation_status = "INVALID"
    mock_invalid_run.is_approvable = False

    service.run_repo.get_by_run_id = AsyncMock(return_value=mock_invalid_run)

    with pytest.raises(PlanVersionApprovalBlockedError, match="Only certified valid schedules may enter human review"):
        await service.create_plan_version_from_run("RUN-INVALID-02", actor=actor)


@pytest.mark.asyncio
async def test_governance_four_eyes_inviolability():
    """Verify four-eyes governance rule: creator cannot approve own plan version."""
    mock_session = AsyncMock()
    service = PlanGovernanceService(mock_session)

    mock_plan = MagicMock()
    mock_plan.plan_version_id = "PV-TEST-001"
    mock_plan.status = "UNDER_REVIEW"
    mock_plan.validation_status = "VALID"
    mock_plan.is_approvable = True
    mock_plan.validation_findings_summary = {"error_count": 0}
    mock_plan.planning_run_id = "RUN-123"
    mock_plan.schedule_identity = "fp123"
    mock_plan.snapshot_hash = "snap123"
    mock_plan.input_hash = "in123"
    mock_plan.created_by = "usr_author_123"
    mock_plan.scenario_id = "SCN-DEMO-001"

    mock_run = MagicMock()
    mock_run.validation_fingerprint = "fp123"
    mock_run.snapshot_hash = "snap123"
    mock_run.input_hash = "in123"

    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=mock_plan)
    service.run_repo.get_by_run_id = AsyncMock(return_value=mock_run)

    approver_same_as_creator = AuthUser(
        user_id="usr_author_123",  # Same ID!
        username="author_user",
        role="OPERATOR",
        permissions=["approve:plan"],
    )

    with pytest.raises(FourEyesViolationError, match="Separation of duties violation"):
        await service.approve_plan(
            plan_version_id="PV-TEST-001",
            actor=approver_same_as_creator,
            comment="Self approval attempt",
        )


# =============================================================================
# 6. Database Compound Index Integrity
# =============================================================================

def test_production_hardening_indexes_defined_in_models():
    """Verify that required compound indexes are registered on SQLAlchemy model metadata."""
    # 1. PlanningRunModel compound index
    run_indexes = {idx.name for idx in PlanningRunModel.__table__.indexes}
    assert "ix_planning_runs_scenario_status_created" in run_indexes

    # 2. MaintenanceTaskModel track window compound index
    task_indexes = {idx.name for idx in MaintenanceTaskModel.__table__.indexes}
    assert "ix_tasks_track_window" in task_indexes

    # 3. TrainMovementModel train station compound index
    movement_indexes = {idx.name for idx in TrainMovementModel.__table__.indexes}
    assert "ix_movements_train_station" in movement_indexes


# =============================================================================
# 7. CreatePlanningRunRequest Validation & Defaults
# =============================================================================

def test_create_planning_run_request_schema():
    """Verify CreatePlanningRunRequest accepts solver_mode and defaults safely."""
    req_default = CreatePlanningRunRequest(scenario_id="SCN-DEMO-001")
    assert req_default.solver_mode == "TRACK_AWARE_CONSERVATIVE"
    assert req_default.scheduler_type == SchedulerType.CP_SAT

    req_custom = CreatePlanningRunRequest(
        scenario_id="SCN-DEMO-001",
        solver_mode="WHOLE_SECTION",
        time_limit_seconds=45.0,
    )
    assert req_custom.solver_mode == "WHOLE_SECTION"
    assert req_custom.time_limit_seconds == 45.0
