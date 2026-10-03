"""Unit tests for Phase 15A: Planning Worker Cancellation Race Condition & Transition Integrity."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.app.schemas.planning_run import (
    PlanningRunStatus,
    PlanningRunStage,
)
from backend.app.repositories.planning_run_repo import (
    PlanningRunRepository,
    IllegalStateTransitionError,
    LEGAL_TRANSITIONS,
)
from backend.app.db.models.planning_run import PlanningRunModel
from backend.app.services.planning_worker import PlanningRunWorker


def test_legal_transitions_include_cancellation_pathways():
    """Verify state machine allows CANCEL_REQUESTED -> CANCELLED, and prohibits illegal jumps."""
    assert PlanningRunStatus.CANCELLED in LEGAL_TRANSITIONS[PlanningRunStatus.CANCEL_REQUESTED]
    assert PlanningRunStatus.VALIDATING not in LEGAL_TRANSITIONS[PlanningRunStatus.CANCEL_REQUESTED]
    assert PlanningRunStatus.COMPLETED not in LEGAL_TRANSITIONS[PlanningRunStatus.CANCEL_REQUESTED]
    assert PlanningRunStatus.RUNNING not in LEGAL_TRANSITIONS[PlanningRunStatus.CANCEL_REQUESTED]

    # CANCELLED is terminal; no forward transitions allowed
    assert len(LEGAL_TRANSITIONS.get(PlanningRunStatus.CANCELLED, set())) == 0


def test_illegal_transition_from_cancel_requested():
    """Attempting to transition from CANCEL_REQUESTED to VALIDATING or COMPLETED must fail."""
    repo = PlanningRunRepository(None)

    with pytest.raises(IllegalStateTransitionError):
        repo.validate_transition(
            PlanningRunStatus.CANCEL_REQUESTED.value,
            PlanningRunStatus.VALIDATING,
        )

    with pytest.raises(IllegalStateTransitionError):
        repo.validate_transition(
            PlanningRunStatus.CANCEL_REQUESTED.value,
            PlanningRunStatus.COMPLETED,
        )


def test_illegal_transition_from_cancelled():
    """Attempting to transition out of terminal CANCELLED state must raise IllegalStateTransitionError."""
    repo = PlanningRunRepository(None)

    for target in [
        PlanningRunStatus.RUNNING,
        PlanningRunStatus.VALIDATING,
        PlanningRunStatus.COMPLETED,
        PlanningRunStatus.FAILED,
    ]:
        with pytest.raises(IllegalStateTransitionError):
            repo.validate_transition(PlanningRunStatus.CANCELLED.value, target)


@pytest.mark.asyncio
async def test_mark_cancelled_from_cancel_requested():
    """mark_cancelled should cleanly transition CANCEL_REQUESTED run to CANCELLED."""
    session = AsyncMock()
    repo = PlanningRunRepository(session)

    mock_run = MagicMock(spec=PlanningRunModel)
    mock_run.status = PlanningRunStatus.CANCEL_REQUESTED.value
    mock_run.stage = PlanningRunStage.SOLVING.value

    repo.get_by_run_id = AsyncMock(return_value=mock_run)

    result = await repo.mark_cancelled("RUN-TEST-001", reason="Operator cancelled job.")

    assert result is not None
    assert result.status == PlanningRunStatus.CANCELLED.value
    assert result.stage == PlanningRunStage.CANCELLED.value
    assert result.error_message == "Operator cancelled job."
    assert session.commit.called


@pytest.mark.asyncio
async def test_worker_respects_cancel_requested_before_solve():
    """If user requested cancellation before solve, worker marks CANCELLED and aborts."""
    mock_session = AsyncMock()
    session_factory = MagicMock()
    session_factory.return_value.__aenter__.return_value = mock_session
    session_factory.return_value.__aexit__.return_value = False

    worker = PlanningRunWorker(worker_id="test-worker", session_factory=session_factory)

    mock_run = MagicMock(spec=PlanningRunModel)
    mock_run.run_id = "RUN-CANCEL-001"
    mock_run.scenario_id = "SCN-TEST"
    mock_run.scheduler_type = "CP_SAT"
    mock_run.configuration_snapshot = {}
    mock_run.random_seed = 42

    # Return CANCEL_REQUESTED on second check (before solve)
    mock_run_cancelled = MagicMock(spec=PlanningRunModel)
    mock_run_cancelled.status = PlanningRunStatus.CANCEL_REQUESTED.value

    # Mock PlanningScenarioService and PlanningRunRepository inside session
    mock_bundle = MagicMock()
    mock_bundle.scenario_id = "SCN-TEST"
    mock_bundle.horizon_start = "2026-10-15T00:00:00Z"
    mock_bundle.horizon_end = "2026-10-16T00:00:00Z"
    mock_bundle.tasks = []
    mock_bundle.work_orders = []
    mock_bundle.resources = []
    mock_bundle.resource_availabilities = []
    mock_bundle.dependencies = []
    mock_bundle.sections = []
    mock_bundle.rules = []
    mock_bundle.train_passes = []

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "backend.app.services.planning_worker.PlanningScenarioService.get_planning_bundle",
            AsyncMock(return_value=mock_bundle),
        )
        mp.setattr(
            "backend.app.services.planning_worker.PlanningSnapshot.from_bundle",
            MagicMock(return_value=MagicMock(
                snapshot_id="SNAP-1",
                compute_snapshot_hash=MagicMock(return_value="h1"),
                compute_input_hash=MagicMock(return_value="h2"),
                horizon=MagicMock(start="start", end="end"),
            )),
        )
        mp.setattr(
            "backend.app.services.planning_worker.PlanningRunRepository.get_by_run_id",
            AsyncMock(return_value=mock_run_cancelled),
        )
        mock_mark_cancelled = AsyncMock()
        mp.setattr(
            "backend.app.services.planning_worker.PlanningRunRepository.mark_cancelled",
            mock_mark_cancelled,
        )
        mock_solver = MagicMock()
        mp.setattr(
            worker,
            "_execute_scheduler_sync",
            mock_solver,
        )

        await worker._process_claimed_run(
            run_id="RUN-CANCEL-001",
            scenario_id="SCN-TEST",
            scheduler_type="CP_SAT",
            config_snapshot={},
            random_seed=42,
        )

        # Worker must have called mark_cancelled and NOT invoked solver
        assert mock_mark_cancelled.called
        assert not mock_solver.called
