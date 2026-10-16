"""Repository for Plan Version lifecycle, review workflows, and immutable governance audit events."""

from datetime import datetime, timezone
from typing import Optional, Sequence, Dict, Any, Tuple, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from backend.app.repositories.base import BaseRepository
from backend.app.db.models.plan_version import (
    PlanVersionModel,
    PlanReviewCommentModel,
    GovernanceAuditEventModel,
)
from backend.app.db.models.scenario import OperationalScenarioModel
from backend.app.schemas.plan_version import PlanVersionStatus, GovernanceEventType


# =============================================================================
# DOMAIN EXCEPTIONS
# =============================================================================

class PlanVersionNotFoundError(KeyError):
    """Raised when a specified plan version cannot be found."""
    pass


class InvalidPlanVersionTransitionError(ValueError):
    """Raised when an illegal plan version state machine transition is attempted."""
    def __init__(self, current_status: str, target_status: str) -> None:
        super().__init__(f"Illegal transition from '{current_status}' to '{target_status}'.")
        self.current_status = current_status
        self.target_status = target_status


class PlanVersionAlreadyExistsError(ValueError):
    """Raised when attempting to create a duplicate plan version for a planning run."""
    pass


class PlanVersionApprovalBlockedError(ValueError):
    """Raised when approval preconditions fail or technical validation is absent."""
    pass


class FourEyesViolationError(PlanVersionApprovalBlockedError):
    """Raised when the author of a plan version attempts to approve it (separation of duties violation)."""
    pass


class PlanFingerprintMismatchError(ValueError):
    """Raised when schedule fingerprint or snapshot hash fails integrity check."""
    pass


class PlanSnapshotIntegrityError(PlanFingerprintMismatchError):
    """Raised when planning snapshot integrity, hash format, or scenario binding fails."""
    pass


class PlanVersionImmutableError(ValueError):
    """Raised when an attempt is made to mutate an approved or terminal plan version."""
    pass


class PlanApprovalConflictError(ValueError):
    """Raised when concurrent approvals conflict on scenario approval uniqueness constraint."""
    pass


# =============================================================================
# STATE MACHINE TRANSITIONS
# =============================================================================

LEGAL_PLAN_TRANSITIONS: Dict[PlanVersionStatus, set] = {
    PlanVersionStatus.PENDING_REVIEW: {
        PlanVersionStatus.UNDER_REVIEW,
        PlanVersionStatus.APPROVED,
        PlanVersionStatus.REJECTED,
    },
    PlanVersionStatus.UNDER_REVIEW: {
        PlanVersionStatus.APPROVED,
        PlanVersionStatus.REJECTED,
        PlanVersionStatus.PENDING_REVIEW,
    },
    PlanVersionStatus.APPROVED: {
        PlanVersionStatus.SUPERSEDED,
    },
    PlanVersionStatus.REJECTED: set(),
    PlanVersionStatus.SUPERSEDED: set(),
}


# =============================================================================
# REPOSITORY
# =============================================================================

class PlanVersionRepository(BaseRepository[PlanVersionModel]):
    """Manages transactional persistence for Plan Versions, Review Comments, and Audit Records."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(PlanVersionModel, session)

    async def get_next_version_number(self, scenario_id: str) -> int:
        """Acquire a row lock on the scenario to compute the next version number atomically."""
        # 1. Lock scenario row to serialize version numbering across concurrent transactions
        scen_stmt = (
            select(OperationalScenarioModel)
            .where(OperationalScenarioModel.scenario_id == scenario_id)
            .with_for_update()
        )
        await self.session.execute(scen_stmt)

        # 2. Get current maximum version number
        max_stmt = (
            select(func.coalesce(func.max(PlanVersionModel.version_number), 0))
            .where(PlanVersionModel.scenario_id == scenario_id)
        )
        current_max = (await self.session.execute(max_stmt)).scalar() or 0
        return current_max + 1

    def validate_transition(self, current_status: str, target_status: PlanVersionStatus) -> None:
        """Enforce strict governance state machine rules."""
        curr_enum = PlanVersionStatus(current_status)
        allowed = LEGAL_PLAN_TRANSITIONS.get(curr_enum, set())
        if target_status not in allowed:
            raise InvalidPlanVersionTransitionError(current_status, target_status.value)

    async def get_by_plan_version_id(self, plan_version_id: str) -> Optional[PlanVersionModel]:
        """Fetch plan version with review comments eagerly loaded."""
        stmt = (
            select(PlanVersionModel)
            .where(PlanVersionModel.plan_version_id == plan_version_id)
            .options(selectinload(PlanVersionModel.review_comments))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_for_update(self, plan_version_id: str) -> Optional[PlanVersionModel]:
        """Fetch and lock plan version row for concurrency-safe state transitions."""
        stmt = (
            select(PlanVersionModel)
            .where(PlanVersionModel.plan_version_id == plan_version_id)
            .with_for_update()
            .execution_options(populate_existing=True)
            .options(selectinload(PlanVersionModel.review_comments))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_planning_run_id(self, planning_run_id: str) -> Optional[PlanVersionModel]:
        """Find the single governance plan version associated with a planning run."""
        stmt = (
            select(PlanVersionModel)
            .where(PlanVersionModel.planning_run_id == planning_run_id)
            .options(selectinload(PlanVersionModel.review_comments))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_approved(self, scenario_id: str, for_update: bool = False) -> Optional[PlanVersionModel]:
        """Find the currently active APPROVED plan version for a scenario, optionally locking it."""
        stmt = (
            select(PlanVersionModel)
            .where(
                and_(
                    PlanVersionModel.scenario_id == scenario_id,
                    PlanVersionModel.status == PlanVersionStatus.APPROVED.value,
                )
            )
            .order_by(PlanVersionModel.version_number.desc())
        )
        if for_update:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_plan_version(
        self,
        plan_version: PlanVersionModel,
    ) -> PlanVersionModel:
        """Persist a new PlanVersion within an active transaction."""
        self.session.add(plan_version)
        await self.session.flush()
        return plan_version

    async def list_plan_versions(
        self,
        scenario_id: Optional[str] = None,
        status: Optional[PlanVersionStatus] = None,
        planning_run_id: Optional[str] = None,
        created_by: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[PlanVersionModel]:
        """List plan versions with optional filtering and pagination."""
        stmt = select(PlanVersionModel)
        if scenario_id:
            stmt = stmt.where(PlanVersionModel.scenario_id == scenario_id)
        if status:
            stmt = stmt.where(PlanVersionModel.status == status.value)
        if planning_run_id:
            stmt = stmt.where(PlanVersionModel.planning_run_id == planning_run_id)
        if created_by:
            stmt = stmt.where(PlanVersionModel.created_by == created_by)

        stmt = stmt.order_by(PlanVersionModel.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_plan_versions(
        self,
        scenario_id: Optional[str] = None,
        status: Optional[PlanVersionStatus] = None,
        planning_run_id: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> int:
        """Count plan versions matching criteria."""
        stmt = select(func.count()).select_from(PlanVersionModel)
        if scenario_id:
            stmt = stmt.where(PlanVersionModel.scenario_id == scenario_id)
        if status:
            stmt = stmt.where(PlanVersionModel.status == status.value)
        if planning_run_id:
            stmt = stmt.where(PlanVersionModel.planning_run_id == planning_run_id)
        if created_by:
            stmt = stmt.where(PlanVersionModel.created_by == created_by)

        result = await self.session.execute(stmt)
        return result.scalar() or 0

    # -------------------------------------------------------------------------
    # REVIEW COMMENTS & AUDIT EVENTS
    # -------------------------------------------------------------------------

    async def add_review_comment(self, comment: PlanReviewCommentModel) -> PlanReviewCommentModel:
        """Append an immutable review commentary entry."""
        self.session.add(comment)
        await self.session.flush()
        return comment

    async def list_review_comments(self, plan_version_id: str) -> Sequence[PlanReviewCommentModel]:
        """Retrieve chronological review comments for a plan version."""
        stmt = (
            select(PlanReviewCommentModel)
            .where(PlanReviewCommentModel.plan_version_id == plan_version_id)
            .order_by(PlanReviewCommentModel.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def add_audit_event(self, event: GovernanceAuditEventModel) -> GovernanceAuditEventModel:
        """Append an immutable governance audit event."""
        self.session.add(event)
        await self.session.flush()
        return event

    async def list_audit_events(
        self,
        entity_id: str,
        entity_type: str = "PLAN_VERSION",
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[GovernanceAuditEventModel]:
        """Retrieve chronological governance audit events for an entity."""
        stmt = (
            select(GovernanceAuditEventModel)
            .where(
                and_(
                    GovernanceAuditEventModel.entity_type == entity_type,
                    GovernanceAuditEventModel.entity_id == entity_id,
                )
            )
            .order_by(GovernanceAuditEventModel.timestamp.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
