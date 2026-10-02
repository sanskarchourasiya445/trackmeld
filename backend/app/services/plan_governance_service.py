"""Service implementing human review workflows, formal approval gating, and immutable audit logging."""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.auth import AuthUser
from backend.app.schemas.plan_version import (
    PlanVersionStatus,
    PlanReviewAction,
    GovernanceEventType,
)
from backend.app.db.models.plan_version import (
    PlanVersionModel,
    PlanReviewCommentModel,
    GovernanceAuditEventModel,
)
from backend.app.repositories.planning_run_repo import (
    PlanningRunRepository,
    PlanningRunNotFoundError,
)
from backend.app.repositories.plan_version_repo import (
    PlanVersionRepository,
    PlanVersionNotFoundError,
    InvalidPlanVersionTransitionError,
    PlanVersionAlreadyExistsError,
    PlanVersionApprovalBlockedError,
    PlanFingerprintMismatchError,
    PlanVersionImmutableError,
)

logger = logging.getLogger("trackmeld.governance")


class PlanGovernanceService:
    """Orchestrates human review, approval preconditions, and immutable audit trail."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.plan_repo = PlanVersionRepository(session)
        self.run_repo = PlanningRunRepository(session)

    async def create_plan_version_from_run(
        self,
        run_id: str,
        actor: AuthUser,
        comment: Optional[str] = None,
    ) -> PlanVersionModel:
        """Create a candidate PlanVersion from a completed, certified planning run."""
        run = await self.run_repo.get_by_run_id(run_id)
        if not run:
            raise PlanningRunNotFoundError(f"Planning run '{run_id}' not found.")

        # Precondition A: Source run must be terminal and completed
        if run.status != "COMPLETED":
            raise PlanVersionApprovalBlockedError(
                f"Cannot create PlanVersion: Planning run '{run_id}' status is '{run.status}', expected 'COMPLETED'."
            )

        # Precondition B: Source run must have been certified VALID by Phase 7 Independent Validator
        if run.validation_status != "VALID" or not run.is_approvable:
            raise PlanVersionApprovalBlockedError(
                f"Cannot create PlanVersion: Planning run '{run_id}' validation status is '{run.validation_status}' "
                f"(is_approvable={run.is_approvable}). Only certified valid schedules may enter human review."
            )

        if not run.schedule_result:
            raise PlanVersionApprovalBlockedError(
                f"Cannot create PlanVersion: Planning run '{run_id}' has no persisted schedule_result."
            )

        # Precondition C: Check duplicate plan version for this run
        existing = await self.plan_repo.get_by_planning_run_id(run_id)
        if existing:
            raise PlanVersionAlreadyExistsError(
                f"PlanVersion '{existing.plan_version_id}' already exists for planning run '{run_id}'."
            )

        # Determine next sequential version number atomically under lock
        version_num = await self.plan_repo.get_next_version_number(run.scenario_id)

        now = datetime.now(timezone.utc)
        plan_version_id = f"PV-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

        new_plan = PlanVersionModel(
            plan_version_id=plan_version_id,
            scenario_id=run.scenario_id,
            planning_run_id=run.run_id,
            version_number=version_num,
            status=PlanVersionStatus.PENDING_REVIEW.value,
            schedule_identity=run.validation_fingerprint or run.schedule_result.get("validation", {}).get("schedule_identity", ""),
            snapshot_hash=run.snapshot_hash or "",
            input_hash=run.input_hash or "",
            schedule_result=dict(run.schedule_result),
            result_summary=dict(run.result_summary or {}),
            validation_status=run.validation_status,
            is_approvable=run.is_approvable,
            validation_findings_summary=dict(run.validation_findings_summary or {}),
            diagnostics_summary=dict(run.diagnostics_summary or {}) if run.diagnostics_summary else None,
            scheduler_type=run.scheduler_type,
            scheduler_version=run.scheduler_version,
            solver_name=run.solver_name,
            solver_version=run.solver_version,
            dataset_version=run.dataset_version,
            configuration_snapshot=dict(run.configuration_snapshot),
            priority_configuration=dict(run.priority_configuration or {}) if run.priority_configuration else None,
            optimization_configuration=dict(run.optimization_configuration or {}) if run.optimization_configuration else None,
            created_at=now,
            created_by=actor.username,
            review_comment=comment,
        )

        await self.plan_repo.create_plan_version(new_plan)

        # Append creation audit event
        audit_event = GovernanceAuditEventModel(
            event_id=f"AUD-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}",
            entity_type="PLAN_VERSION",
            entity_id=plan_version_id,
            event_type=GovernanceEventType.PLAN_VERSION_CREATED.value,
            actor_id=actor.user_id,
            actor_username=actor.username,
            actor_role=actor.role.value,
            timestamp=now,
            previous_state=None,
            new_state=PlanVersionStatus.PENDING_REVIEW.value,
            comment=comment or f"Instantiated PlanVersion {version_num} from certified run '{run_id}'.",
            schedule_identity=new_plan.schedule_identity,
            snapshot_hash=new_plan.snapshot_hash,
            input_hash=new_plan.input_hash,
            event_metadata={
                "scenario_id": run.scenario_id,
                "planning_run_id": run.run_id,
                "version_number": version_num,
                "scheduler_type": run.scheduler_type,
            },
        )
        await self.plan_repo.add_audit_event(audit_event)

        if comment:
            review_comment = PlanReviewCommentModel(
                review_id=f"REV-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}",
                plan_version_id=plan_version_id,
                actor_id=actor.user_id,
                actor_username=actor.username,
                action=PlanReviewAction.COMMENT.value,
                comment=comment,
                created_at=now,
            )
            await self.plan_repo.add_review_comment(review_comment)

        await self.session.commit()
        logger.info(
            f"Created PlanVersion '{plan_version_id}' (v{version_num}) for scenario '{run.scenario_id}' "
            f"from run '{run_id}' by actor {actor.username}."
        )
        return await self.plan_repo.get_by_plan_version_id(plan_version_id)

    async def start_review(
        self,
        plan_version_id: str,
        actor: AuthUser,
        comment: Optional[str] = None,
    ) -> PlanVersionModel:
        """Advance plan version to UNDER_REVIEW state."""
        plan = await self.plan_repo.get_by_id_for_update(plan_version_id)
        if not plan:
            raise PlanVersionNotFoundError(f"PlanVersion '{plan_version_id}' not found.")

        # Validate legal transition
        self.plan_repo.validate_transition(plan.status, PlanVersionStatus.UNDER_REVIEW)

        now = datetime.now(timezone.utc)
        prev_status = plan.status
        plan.status = PlanVersionStatus.UNDER_REVIEW.value
        plan.reviewed_at = now
        plan.reviewed_by = actor.username

        # Audit event
        audit_event = GovernanceAuditEventModel(
            event_id=f"AUD-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}",
            entity_type="PLAN_VERSION",
            entity_id=plan_version_id,
            event_type=GovernanceEventType.PLAN_REVIEW_STARTED.value,
            actor_id=actor.user_id,
            actor_username=actor.username,
            actor_role=actor.role.value,
            timestamp=now,
            previous_state=prev_status,
            new_state=PlanVersionStatus.UNDER_REVIEW.value,
            comment=comment or "Reviewer commenced formal operational audit.",
            schedule_identity=plan.schedule_identity,
            snapshot_hash=plan.snapshot_hash,
            input_hash=plan.input_hash,
            event_metadata={"scenario_id": plan.scenario_id, "version_number": plan.version_number},
        )
        await self.plan_repo.add_audit_event(audit_event)

        # Review action
        review_record = PlanReviewCommentModel(
            review_id=f"REV-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}",
            plan_version_id=plan_version_id,
            actor_id=actor.user_id,
            actor_username=actor.username,
            action=PlanReviewAction.START_REVIEW.value,
            comment=comment or "Started human review.",
            created_at=now,
        )
        await self.plan_repo.add_review_comment(review_record)

        await self.session.commit()
        logger.info(f"PlanVersion '{plan_version_id}' entered UNDER_REVIEW by {actor.username}.")
        return await self.plan_repo.get_by_plan_version_id(plan_version_id)

    async def add_review_comment(
        self,
        plan_version_id: str,
        actor: AuthUser,
        comment_text: str,
    ) -> PlanReviewCommentModel:
        """Attach an immutable commentary entry to a plan version."""
        plan = await self.plan_repo.get_by_plan_version_id(plan_version_id)
        if not plan:
            raise PlanVersionNotFoundError(f"PlanVersion '{plan_version_id}' not found.")

        now = datetime.now(timezone.utc)
        comment_record = PlanReviewCommentModel(
            review_id=f"REV-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}",
            plan_version_id=plan_version_id,
            actor_id=actor.user_id,
            actor_username=actor.username,
            action=PlanReviewAction.COMMENT.value,
            comment=comment_text,
            created_at=now,
        )
        await self.plan_repo.add_review_comment(comment_record)

        audit_event = GovernanceAuditEventModel(
            event_id=f"AUD-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}",
            entity_type="PLAN_VERSION",
            entity_id=plan_version_id,
            event_type=GovernanceEventType.PLAN_COMMENT_ADDED.value,
            actor_id=actor.user_id,
            actor_username=actor.username,
            actor_role=actor.role.value,
            timestamp=now,
            previous_state=plan.status,
            new_state=plan.status,
            comment=comment_text,
            schedule_identity=plan.schedule_identity,
            snapshot_hash=plan.snapshot_hash,
            input_hash=plan.input_hash,
            event_metadata={"scenario_id": plan.scenario_id, "version_number": plan.version_number},
        )
        await self.plan_repo.add_audit_event(audit_event)

        await self.session.commit()
        return comment_record

    async def approve_plan(
        self,
        plan_version_id: str,
        actor: AuthUser,
        comment: Optional[str] = None,
    ) -> PlanVersionModel:
        """Formally approve an independently verified plan candidate."""
        # Precondition 1: Plan version exists and acquire row lock
        plan = await self.plan_repo.get_by_id_for_update(plan_version_id)
        if not plan:
            raise PlanVersionNotFoundError(f"PlanVersion '{plan_version_id}' not found.")

        # Precondition 2: Check current status - cannot re-approve an already approved plan
        if plan.status == PlanVersionStatus.APPROVED.value:
            raise PlanVersionImmutableError(
                f"PlanVersion '{plan_version_id}' is already APPROVED and cannot be re-approved."
            )

        # Precondition 3: Legal transition check
        self.plan_repo.validate_transition(plan.status, PlanVersionStatus.APPROVED)

        # Precondition 4: Technical validation status must be VALID and is_approvable True
        if plan.validation_status != "VALID" or not plan.is_approvable:
            raise PlanVersionApprovalBlockedError(
                f"Cannot approve PlanVersion '{plan_version_id}': Technical validation status is '{plan.validation_status}' "
                f"(is_approvable={plan.is_approvable}). Only certified valid schedules may be approved."
            )

        # Precondition 5: Zero blocking validation errors
        findings_summary = plan.validation_findings_summary or {}
        if findings_summary.get("error_count", 0) > 0:
            raise PlanVersionApprovalBlockedError(
                f"Cannot approve PlanVersion '{plan_version_id}': Contains {findings_summary.get('error_count')} "
                f"unresolved hard validation errors."
            )

        # Precondition 6: Fingerprint and provenance integrity check against source run
        run = await self.run_repo.get_by_run_id(plan.planning_run_id)
        if not run:
            raise PlanFingerprintMismatchError(
                f"Source planning run '{plan.planning_run_id}' missing for PlanVersion '{plan_version_id}'."
            )
        if run.validation_fingerprint and run.validation_fingerprint != plan.schedule_identity:
            raise PlanFingerprintMismatchError(
                f"Cryptographic fingerprint mismatch: PlanVersion has '{plan.schedule_identity}', "
                f"source run has '{run.validation_fingerprint}'."
            )
        if run.snapshot_hash and run.snapshot_hash != plan.snapshot_hash:
            raise PlanFingerprintMismatchError("Planning snapshot hash does not match source run.")
        if run.input_hash and run.input_hash != plan.input_hash:
            raise PlanFingerprintMismatchError("Input configuration hash does not match source run.")

        now = datetime.now(timezone.utc)
        prev_status = plan.status

        # Supersede any previous APPROVED plan version for this scenario
        prev_approved = await self.plan_repo.get_latest_approved(plan.scenario_id)
        if prev_approved and prev_approved.plan_version_id != plan.plan_version_id:
            logger.info(
                f"Superseding previous approved PlanVersion '{prev_approved.plan_version_id}' (v{prev_approved.version_number}) "
                f"by newly approved PlanVersion '{plan.plan_version_id}' (v{plan.version_number})."
            )
            prev_approved.status = PlanVersionStatus.SUPERSEDED.value
            prev_approved.superseded_at = now
            prev_approved.superseded_by = actor.username
            plan.previous_plan_version_id = prev_approved.plan_version_id

            # Audit event for superseded plan
            sup_audit = GovernanceAuditEventModel(
                event_id=f"AUD-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}",
                entity_type="PLAN_VERSION",
                entity_id=prev_approved.plan_version_id,
                event_type=GovernanceEventType.PLAN_SUPERSEDED.value,
                actor_id=actor.user_id,
                actor_username=actor.username,
                actor_role=actor.role.value,
                timestamp=now,
                previous_state=PlanVersionStatus.APPROVED.value,
                new_state=PlanVersionStatus.SUPERSEDED.value,
                reason=f"Superseded by newly approved PlanVersion '{plan.plan_version_id}' (v{plan.version_number}).",
                schedule_identity=prev_approved.schedule_identity,
                snapshot_hash=prev_approved.snapshot_hash,
                input_hash=prev_approved.input_hash,
                event_metadata={
                    "superseding_plan_version_id": plan.plan_version_id,
                    "superseding_version_number": plan.version_number,
                },
            )
            await self.plan_repo.add_audit_event(sup_audit)

        # Transition plan to APPROVED
        plan.status = PlanVersionStatus.APPROVED.value
        plan.approved_at = now
        plan.approved_by = actor.username
        plan.review_comment = comment

        # Add review record
        rev_comment = PlanReviewCommentModel(
            review_id=f"REV-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}",
            plan_version_id=plan_version_id,
            actor_id=actor.user_id,
            actor_username=actor.username,
            action=PlanReviewAction.APPROVE.value,
            comment=comment or "Plan explicitly approved by authorized operations officer.",
            created_at=now,
        )
        await self.plan_repo.add_review_comment(rev_comment)

        # Add audit event for PLAN_APPROVED
        approval_audit = GovernanceAuditEventModel(
            event_id=f"AUD-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}",
            entity_type="PLAN_VERSION",
            entity_id=plan_version_id,
            event_type=GovernanceEventType.PLAN_APPROVED.value,
            actor_id=actor.user_id,
            actor_username=actor.username,
            actor_role=actor.role.value,
            timestamp=now,
            previous_state=prev_status,
            new_state=PlanVersionStatus.APPROVED.value,
            comment=comment or "Authorized operational approval.",
            schedule_identity=plan.schedule_identity,
            snapshot_hash=plan.snapshot_hash,
            input_hash=plan.input_hash,
            event_metadata={
                "scenario_id": plan.scenario_id,
                "version_number": plan.version_number,
                "planning_run_id": plan.planning_run_id,
                "scheduler_type": plan.scheduler_type,
                "previous_plan_version_id": plan.previous_plan_version_id,
            },
        )
        await self.plan_repo.add_audit_event(approval_audit)

        await self.session.commit()
        logger.info(
            f"PlanVersion '{plan_version_id}' (v{plan.version_number}) APPROVED by {actor.username} "
            f"for scenario '{plan.scenario_id}'."
        )
        return await self.plan_repo.get_by_plan_version_id(plan_version_id)

    async def reject_plan(
        self,
        plan_version_id: str,
        actor: AuthUser,
        reason: str,
    ) -> PlanVersionModel:
        """Explicitly reject a plan candidate with mandatory operational justification."""
        if not reason or len(reason.strip()) < 5:
            raise ValueError("A clear, substantive rejection reason is required (minimum 5 characters).")

        plan = await self.plan_repo.get_by_id_for_update(plan_version_id)
        if not plan:
            raise PlanVersionNotFoundError(f"PlanVersion '{plan_version_id}' not found.")

        # Approved plans cannot be rejected retroactively
        if plan.status == PlanVersionStatus.APPROVED.value:
            raise PlanVersionImmutableError(
                f"Approved PlanVersion '{plan_version_id}' cannot be rejected; create a superseding version instead."
            )

        if plan.status == PlanVersionStatus.REJECTED.value:
            raise PlanVersionImmutableError(f"PlanVersion '{plan_version_id}' is already REJECTED.")

        self.plan_repo.validate_transition(plan.status, PlanVersionStatus.REJECTED)

        now = datetime.now(timezone.utc)
        prev_status = plan.status

        plan.status = PlanVersionStatus.REJECTED.value
        plan.rejected_at = now
        plan.rejected_by = actor.username
        plan.rejection_reason = reason.strip()

        # Add review commentary
        rev_comment = PlanReviewCommentModel(
            review_id=f"REV-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}",
            plan_version_id=plan_version_id,
            actor_id=actor.user_id,
            actor_username=actor.username,
            action=PlanReviewAction.REJECT.value,
            comment=f"REJECTED: {reason.strip()}",
            created_at=now,
        )
        await self.plan_repo.add_review_comment(rev_comment)

        # Add audit event for PLAN_REJECTED
        reject_audit = GovernanceAuditEventModel(
            event_id=f"AUD-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}",
            entity_type="PLAN_VERSION",
            entity_id=plan_version_id,
            event_type=GovernanceEventType.PLAN_REJECTED.value,
            actor_id=actor.user_id,
            actor_username=actor.username,
            actor_role=actor.role.value,
            timestamp=now,
            previous_state=prev_status,
            new_state=PlanVersionStatus.REJECTED.value,
            reason=reason.strip(),
            comment=f"Rejected by {actor.username}: {reason.strip()}",
            schedule_identity=plan.schedule_identity,
            snapshot_hash=plan.snapshot_hash,
            input_hash=plan.input_hash,
            event_metadata={
                "scenario_id": plan.scenario_id,
                "version_number": plan.version_number,
                "planning_run_id": plan.planning_run_id,
            },
        )
        await self.plan_repo.add_audit_event(reject_audit)

        await self.session.commit()
        logger.info(
            f"PlanVersion '{plan_version_id}' (v{plan.version_number}) REJECTED by {actor.username}. "
            f"Reason: {reason.strip()}"
        )
        return await self.plan_repo.get_by_plan_version_id(plan_version_id)
