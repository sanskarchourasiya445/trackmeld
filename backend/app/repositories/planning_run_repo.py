"""Repository for persistent planning run lifecycle and query operations."""

from datetime import datetime, timezone, timedelta
from typing import Optional, Sequence, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from backend.app.repositories.base import BaseRepository
from backend.app.db.models.planning_run import PlanningRunModel
from backend.app.schemas.planning_run import PlanningRunStatus, PlanningRunStage


class IllegalStateTransitionError(ValueError):
    """Raised when an illegal planning run status transition is attempted."""
    def __init__(self, current_status: str, target_status: str) -> None:
        super().__init__(
            f"Illegal planning run transition from '{current_status}' to '{target_status}'."
        )
        self.current_status = current_status
        self.target_status = target_status


class PlanningRunNotFoundError(KeyError):
    """Raised when a planning run is not found."""
    pass


LEGAL_TRANSITIONS: Dict[PlanningRunStatus, set] = {
    PlanningRunStatus.PENDING: {
        PlanningRunStatus.RUNNING,
        PlanningRunStatus.FAILED,
        PlanningRunStatus.CANCELLED,
    },
    PlanningRunStatus.RUNNING: {
        PlanningRunStatus.VALIDATING,
        PlanningRunStatus.FAILED,
        PlanningRunStatus.CANCEL_REQUESTED,
        PlanningRunStatus.TIMED_OUT,
    },
    PlanningRunStatus.VALIDATING: {
        PlanningRunStatus.COMPLETED,
        PlanningRunStatus.FAILED,
        PlanningRunStatus.TIMED_OUT,
    },
    PlanningRunStatus.CANCEL_REQUESTED: {
        PlanningRunStatus.CANCELLED,
        PlanningRunStatus.FAILED,
    },
    PlanningRunStatus.COMPLETED: set(),
    PlanningRunStatus.FAILED: set(),
    PlanningRunStatus.CANCELLED: set(),
    PlanningRunStatus.TIMED_OUT: set(),
}


class PlanningRunRepository(BaseRepository[PlanningRunModel]):
    """Thread-safe and atomic repository operations for PlanningRunModel."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(PlanningRunModel, session)

    async def get_by_run_id(self, run_id: str) -> Optional[PlanningRunModel]:
        """Lookup planning run by unique run_id."""
        stmt = select(PlanningRunModel).where(PlanningRunModel.run_id == run_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(self, key: str) -> Optional[PlanningRunModel]:
        """Lookup planning run by client idempotency key."""
        stmt = select(PlanningRunModel).where(PlanningRunModel.idempotency_key == key)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_run(self, run: PlanningRunModel) -> PlanningRunModel:
        """Persist a new pending planning run."""
        self.session.add(run)
        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def claim_pending_run(self, worker_id: str) -> Optional[PlanningRunModel]:
        """Atomically claim the oldest pending planning run using row-level locking."""
        stmt = (
            select(PlanningRunModel)
            .where(PlanningRunModel.status == PlanningRunStatus.PENDING.value)
            .order_by(PlanningRunModel.created_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        result = await self.session.execute(stmt)
        run = result.scalar_one_or_none()
        if not run:
            return None

        now = datetime.now(timezone.utc)
        run.status = PlanningRunStatus.RUNNING.value
        run.stage = PlanningRunStage.CLAIMED.value
        run.worker_id = worker_id
        run.started_at = now
        run.heartbeat_at = now
        run.attempt_count += 1

        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def heartbeat(self, run_id: str, worker_id: str) -> bool:
        """Update worker heartbeat timestamp for an active run."""
        stmt = select(PlanningRunModel).where(
            and_(
                PlanningRunModel.run_id == run_id,
                PlanningRunModel.worker_id == worker_id,
                PlanningRunModel.status.in_([
                    PlanningRunStatus.RUNNING.value,
                    PlanningRunStatus.VALIDATING.value,
                ]),
            )
        )
        result = await self.session.execute(stmt)
        run = result.scalar_one_or_none()
        if not run:
            return False

        run.heartbeat_at = datetime.now(timezone.utc)
        await self.session.commit()
        return True

    def validate_transition(self, current: str, target: PlanningRunStatus) -> None:
        """Ensure proposed state transition adheres to strict state machine."""
        curr_enum = PlanningRunStatus(current)
        allowed = LEGAL_TRANSITIONS.get(curr_enum, set())
        if target not in allowed:
            raise IllegalStateTransitionError(current, target.value)

    async def update_stage(
        self,
        run_id: str,
        stage: PlanningRunStage,
        status: Optional[PlanningRunStatus] = None,
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> Optional[PlanningRunModel]:
        """Advance run progress stage and optional status."""
        run = await self.get_by_run_id(run_id)
        if not run:
            return None

        if status and status.value != run.status:
            self.validate_transition(run.status, status)
            run.status = status.value

        run.stage = stage.value
        run.heartbeat_at = datetime.now(timezone.utc)

        if extra_fields:
            for k, v in extra_fields.items():
                setattr(run, k, v)

        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def mark_validating(self, run_id: str) -> Optional[PlanningRunModel]:
        """Mark planning run as transitioning to independent validation."""
        run = await self.get_by_run_id(run_id)
        if not run:
            return None

        self.validate_transition(run.status, PlanningRunStatus.VALIDATING)
        now = datetime.now(timezone.utc)
        run.status = PlanningRunStatus.VALIDATING.value
        run.stage = PlanningRunStage.VALIDATING.value
        run.validation_started_at = now
        run.heartbeat_at = now

        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def mark_completed(
        self,
        run_id: str,
        schedule_result: Dict[str, Any],
        result_summary: Dict[str, Any],
        validation_status: str,
        validation_fingerprint: str,
        is_approvable: bool,
        duration_ms: float,
        validation_findings_summary: Optional[Dict[str, Any]] = None,
        diagnostics_summary: Optional[Dict[str, Any]] = None,
    ) -> Optional[PlanningRunModel]:
        """Persist final completed planning results and certification."""
        run = await self.get_by_run_id(run_id)
        if not run:
            return None

        self.validate_transition(run.status, PlanningRunStatus.COMPLETED)
        now = datetime.now(timezone.utc)
        run.status = PlanningRunStatus.COMPLETED.value
        run.stage = PlanningRunStage.COMPLETED.value
        run.completed_at = now
        run.execution_duration_ms = duration_ms
        run.schedule_result = schedule_result
        run.result_summary = result_summary
        run.validation_status = validation_status
        run.validation_fingerprint = validation_fingerprint
        run.is_approvable = is_approvable
        run.validation_findings_summary = validation_findings_summary
        run.diagnostics_summary = diagnostics_summary

        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def mark_failed(
        self,
        run_id: str,
        error_code: str,
        error_message: str,
        stage: PlanningRunStage,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> Optional[PlanningRunModel]:
        """Persist structured failure details and error telemetry."""
        run = await self.get_by_run_id(run_id)
        if not run:
            return None

        # Allow marking failed from non-terminal states only.
        # COMPLETED, CANCELLED, and TIMED_OUT are all terminal; stale workers
        # must not overwrite a timed-out run with FAILED.
        if run.status in [
            PlanningRunStatus.COMPLETED.value,
            PlanningRunStatus.CANCELLED.value,
            PlanningRunStatus.TIMED_OUT.value,
        ]:
            raise IllegalStateTransitionError(run.status, PlanningRunStatus.FAILED.value)

        now = datetime.now(timezone.utc)
        run.status = PlanningRunStatus.FAILED.value
        run.stage = stage.value
        run.failed_at = now
        run.error_code = error_code
        run.error_message = error_message
        run.error_details = error_details

        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def mark_timed_out(self, run_id: str, error_message: str) -> Optional[PlanningRunModel]:
        """Mark an expired run as timed out."""
        run = await self.get_by_run_id(run_id)
        if not run:
            return None

        # FAILED, COMPLETED, and CANCELLED are terminal; do not overwrite with TIMED_OUT.
        if run.status in [
            PlanningRunStatus.COMPLETED.value,
            PlanningRunStatus.CANCELLED.value,
            PlanningRunStatus.FAILED.value,
        ]:
            raise IllegalStateTransitionError(run.status, PlanningRunStatus.TIMED_OUT.value)

        now = datetime.now(timezone.utc)
        run.status = PlanningRunStatus.TIMED_OUT.value
        run.stage = PlanningRunStage.TIMED_OUT.value
        run.failed_at = now
        run.error_code = "PLANNING_JOB_TIMED_OUT"
        run.error_message = error_message

        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def request_cancellation(self, run_id: str) -> Optional[PlanningRunModel]:
        """Request cooperative cancellation of a pending or running job."""
        run = await self.get_by_run_id(run_id)
        if not run:
            return None

        if run.status == PlanningRunStatus.PENDING.value:
            run.status = PlanningRunStatus.CANCELLED.value
            run.stage = PlanningRunStage.CANCELLED.value
        elif run.status == PlanningRunStatus.RUNNING.value:
            run.status = PlanningRunStatus.CANCEL_REQUESTED.value
        else:
            raise IllegalStateTransitionError(run.status, PlanningRunStatus.CANCEL_REQUESTED.value)

        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def mark_cancelled(self, run_id: str, reason: Optional[str] = None) -> Optional[PlanningRunModel]:
        """Formally transition a run to CANCELLED from PENDING or CANCEL_REQUESTED."""
        run = await self.get_by_run_id(run_id)
        if not run:
            return None

        self.validate_transition(run.status, PlanningRunStatus.CANCELLED)
        now = datetime.now(timezone.utc)
        run.status = PlanningRunStatus.CANCELLED.value
        run.stage = PlanningRunStage.CANCELLED.value
        run.completed_at = now
        if reason:
            run.error_message = reason

        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def find_stale_runs(self, stale_threshold_seconds: float) -> Sequence[PlanningRunModel]:
        """Find active runs whose worker heartbeat has expired."""
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=stale_threshold_seconds)
        stmt = (
            select(PlanningRunModel)
            .where(
                and_(
                    PlanningRunModel.status.in_([
                        PlanningRunStatus.RUNNING.value,
                        PlanningRunStatus.VALIDATING.value,
                    ]),
                    or_(
                        PlanningRunModel.heartbeat_at == None,
                        PlanningRunModel.heartbeat_at < cutoff,
                    ),
                )
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_runs(
        self,
        scenario_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[PlanningRunModel]:
        """List planning runs with optional filtering and pagination."""
        stmt = select(PlanningRunModel)
        if scenario_id:
            stmt = stmt.where(PlanningRunModel.scenario_id == scenario_id)
        if status:
            stmt = stmt.where(PlanningRunModel.status == status)

        safe_limit = max(1, min(limit, 100))
        safe_offset = max(0, offset)
        stmt = stmt.order_by(
            PlanningRunModel.created_at.desc(),
            PlanningRunModel.run_id.desc(),
        ).offset(safe_offset).limit(safe_limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_runs(
        self,
        scenario_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> int:
        """Count planning runs matching optional filters."""
        stmt = select(func.count()).select_from(PlanningRunModel)
        if scenario_id:
            stmt = stmt.where(PlanningRunModel.scenario_id == scenario_id)
        if status:
            stmt = stmt.where(PlanningRunModel.status == status)

        result = await self.session.execute(stmt)
        return result.scalar() or 0
