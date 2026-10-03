"""Phase 15D Unit Tests — TIMED_OUT Terminal State Protection.

Verifies that stale workers calling mark_failed after a run has already
reached TIMED_OUT cannot overwrite the terminal state with FAILED.

Safety invariant: once a run is in a terminal state (COMPLETED, CANCELLED,
TIMED_OUT, FAILED), no subsequent state mutation is permitted.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.app.repositories.planning_run_repo import (
    IllegalStateTransitionError,
    PlanningRunRepository,
    PlanningRunStatus,
)


def _make_run_in_status(status_value: str) -> MagicMock:
    """Build a minimal mock PlanningRunModel with the given status."""
    run = MagicMock()
    run.run_id = "RUN-TEST-001"
    run.status = status_value
    return run


class _MockRepo(PlanningRunRepository):
    """Minimal stub that overrides get_by_run_id to return a pre-built run."""

    def __init__(self, run):
        self._run = run
        # We don't need a real session for these unit tests
        super().__init__(session=MagicMock())  # type: ignore

    async def get_by_run_id(self, run_id: str):  # type: ignore
        return self._run


# ---------------------------------------------------------------------------
# mark_failed terminal guard tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mark_failed_refuses_to_overwrite_completed() -> None:
    """mark_failed must not transition COMPLETED → FAILED."""
    repo = _MockRepo(_make_run_in_status(PlanningRunStatus.COMPLETED.value))
    with pytest.raises(IllegalStateTransitionError):
        await repo.mark_failed(
            "RUN-TEST-001",
            error_code="X",
            error_message="x",
            stage=MagicMock(),
        )


@pytest.mark.asyncio
async def test_mark_failed_refuses_to_overwrite_cancelled() -> None:
    """mark_failed must not transition CANCELLED → FAILED."""
    repo = _MockRepo(_make_run_in_status(PlanningRunStatus.CANCELLED.value))
    with pytest.raises(IllegalStateTransitionError):
        await repo.mark_failed(
            "RUN-TEST-001",
            error_code="X",
            error_message="x",
            stage=MagicMock(),
        )


@pytest.mark.asyncio
async def test_mark_failed_refuses_to_overwrite_timed_out() -> None:
    """REGRESSION (Phase 15D): mark_failed must not overwrite TIMED_OUT.

    A stale worker that finishes processing a run that was already killed by
    the timeout watchdog must not silently rewrite the terminal state to FAILED.
    This would corrupt the audit trail and misattribute the termination cause.
    """
    repo = _MockRepo(_make_run_in_status(PlanningRunStatus.TIMED_OUT.value))
    with pytest.raises(IllegalStateTransitionError):
        await repo.mark_failed(
            "RUN-TEST-001",
            error_code="X",
            error_message="x",
            stage=MagicMock(),
        )


# ---------------------------------------------------------------------------
# mark_timed_out terminal guard tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mark_timed_out_refuses_to_overwrite_completed() -> None:
    """mark_timed_out must not overwrite COMPLETED."""
    repo = _MockRepo(_make_run_in_status(PlanningRunStatus.COMPLETED.value))
    with pytest.raises(IllegalStateTransitionError):
        await repo.mark_timed_out("RUN-TEST-001", error_message="timeout")


@pytest.mark.asyncio
async def test_mark_timed_out_refuses_to_overwrite_cancelled() -> None:
    """mark_timed_out must not overwrite CANCELLED."""
    repo = _MockRepo(_make_run_in_status(PlanningRunStatus.CANCELLED.value))
    with pytest.raises(IllegalStateTransitionError):
        await repo.mark_timed_out("RUN-TEST-001", error_message="timeout")


@pytest.mark.asyncio
async def test_mark_timed_out_refuses_to_overwrite_failed() -> None:
    """REGRESSION (Phase 15D): mark_timed_out must not overwrite FAILED.

    A redundant timeout trigger must not silently re-label a run that already
    completed with a concrete FAILED determination.
    """
    repo = _MockRepo(_make_run_in_status(PlanningRunStatus.FAILED.value))
    with pytest.raises(IllegalStateTransitionError):
        await repo.mark_timed_out("RUN-TEST-001", error_message="timeout")
