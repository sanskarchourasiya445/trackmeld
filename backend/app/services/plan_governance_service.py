"""Service implementing human review workflows, formal approval gating, and immutable audit logging."""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

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
from backend.app.domain.enums import DataClass
from backend.app.repositories.scenario_repo import ScenarioRepository
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
    PlanSnapshotIntegrityError,
    PlanVersionImmutableError,
    PlanApprovalConflictError,
    FourEyesViolationError,
)
from backend.app.services.validation.validator import IndependentScheduleValidator

logger = logging.getLogger("trackmeld.governance")

TARGET_SCENARIO_APPROVAL_CONSTRAINT = "uq_plan_versions_one_approved_per_scenario"


def is_scenario_approval_unique_violation(e: Exception) -> bool:
    """Determine whether an IntegrityError is specifically caused by the
    partial unique index `uq_plan_versions_one_approved_per_scenario`.

    Extracts PostgreSQL driver diagnostics (asyncpg / psycopg) where available,
    and falls back to exact constraint name matching in error text. Generic SQLSTATE
    23505 or unrelated unique constraint violations return False.
    """
    if not isinstance(e, IntegrityError):
        return False

    orig = getattr(e, "orig", None)
    if orig is not None:
        # 1. asyncpg driver: orig.constraint_name
        constraint = getattr(orig, "constraint_name", None)
        if isinstance(constraint, str) and constraint.strip():
            return constraint.strip().lower() == TARGET_SCENARIO_APPROVAL_CONSTRAINT.lower()

        # 2. psycopg2/3 driver: orig.diag.constraint_name
        diag = getattr(orig, "diag", None)
        if diag is not None:
            diag_constraint = getattr(diag, "constraint_name", None)
            if isinstance(diag_constraint, str) and diag_constraint.strip():
                return diag_constraint.strip().lower() == TARGET_SCENARIO_APPROVAL_CONSTRAINT.lower()

        # 3. If orig is an Exception or str with constraint info
        orig_str = str(orig).lower()
        if TARGET_SCENARIO_APPROVAL_CONSTRAINT.lower() in orig_str:
            return True

    # 4. Fallback to SQLAlchemy IntegrityError string representation
    return TARGET_SCENARIO_APPROVAL_CONSTRAINT.lower() in str(e).lower()


def _is_missing_hash(h: Any) -> bool:
    if h is None:
        return True
    if not isinstance(h, str):
        return True
    return len(h.strip()) == 0


def _is_valid_sha256(h: Any) -> bool:
    if not isinstance(h, str) or len(h) != 64:
        return False
    try:
        int(h, 16)
        return True
    except ValueError:
        return False


def _is_malformed_hash(h: Any) -> bool:
    return not _is_valid_sha256(h)


class PlanGovernanceService:
    """Orchestrates human review, approval preconditions, and immutable audit trail."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.plan_repo = PlanVersionRepository(session)
        self.run_repo = PlanningRunRepository(session)
        self.scenario_repo = ScenarioRepository(session)

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

        # Precondition D: Snapshot and Fingerprint Integrity on Source Run (GOV-002 / VAL-001)
        if _is_missing_hash(run.snapshot_hash):
            raise PlanSnapshotIntegrityError(
                f"Cannot create PlanVersion: Source run '{run_id}' has missing planning snapshot hash."
            )
        if _is_malformed_hash(run.snapshot_hash):
            raise PlanSnapshotIntegrityError(
                f"Cannot create PlanVersion: Source run '{run_id}' has malformed planning snapshot hash {repr(run.snapshot_hash)}."
            )
        if _is_missing_hash(run.input_hash) or _is_malformed_hash(run.input_hash):
            raise PlanSnapshotIntegrityError(
                f"Cannot create PlanVersion: Source run '{run_id}' has missing or malformed input hash {repr(run.input_hash)}."
            )
        sched_id = run.validation_fingerprint or (run.schedule_result.get("validation", {}).get("schedule_identity") if isinstance(run.schedule_result, dict) else None)
        if _is_missing_hash(sched_id) or _is_malformed_hash(sched_id):
            raise PlanSnapshotIntegrityError(
                f"Cannot create PlanVersion: Source run '{run_id}' has missing or malformed schedule identity {repr(sched_id)}."
            )
        if isinstance(run.schedule_result, dict):
            val_evidence = run.schedule_result.get("validation")
            if isinstance(val_evidence, dict):
                cert_id = val_evidence.get("schedule_identity")
                if cert_id and sched_id and cert_id != sched_id:
                    raise PlanFingerprintMismatchError(
                        f"Cannot create PlanVersion: Embedded validation certificate schedule_identity '{cert_id}' "
                        f"does not match run validation fingerprint '{sched_id}'."
                    )
            sched_scen = run.schedule_result.get("scenario_id")
            if sched_scen and sched_scen != run.scenario_id:
                raise PlanFingerprintMismatchError(
                    f"Cannot create PlanVersion: Schedule result scenario '{sched_scen}' "
                    f"does not match source run scenario '{run.scenario_id}'."
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
        try:
            return await self._start_review_internal(
                plan_version_id=plan_version_id,
                actor=actor,
                comment=comment,
            )
        except Exception:
            await self.session.rollback()
            raise

    async def _start_review_internal(
        self,
        plan_version_id: str,
        actor: AuthUser,
        comment: Optional[str] = None,
    ) -> PlanVersionModel:
        plan = await self.plan_repo.get_by_id_for_update(plan_version_id)
        if not plan:
            raise PlanVersionNotFoundError(f"PlanVersion '{plan_version_id}' not found.")

        # Validate legal transition
        self.plan_repo.validate_transition(plan.status, PlanVersionStatus.UNDER_REVIEW)

        # Precondition: Separation of duties (Four-Eyes Principle)
        # Verify creator provenance exists and is valid (fail closed)
        if not getattr(plan, "created_by", None) or not isinstance(plan.created_by, str) or not plan.created_by.strip():
            raise FourEyesViolationError(
                f"Cannot review PlanVersion '{plan_version_id}': Target plan row has missing, blank, or invalid creator provenance (created_by). "
                f"Missing creator identity fails closed under Four-Eyes governance."
            )
        # Verify reviewer actor identity exists and is valid (fail closed)
        if not actor or not getattr(actor, "username", None) or not isinstance(actor.username, str) or not actor.username.strip():
            raise FourEyesViolationError(
                f"Cannot review PlanVersion '{plan_version_id}': Authenticated reviewer has missing, blank, or invalid actor identity. "
                f"Missing reviewer identity fails closed under Four-Eyes governance."
            )

        # Verify role authorization: Actor must possess 'plan:review' permission
        if hasattr(actor, "has_permission") and callable(actor.has_permission):
            if not actor.has_permission("plan:review"):
                raise PlanVersionApprovalBlockedError(
                    f"Actor '{actor.username}' with role '{getattr(actor.role, 'value', actor.role)}' "
                    f"lacks required permission 'plan:review' to review plan version '{plan_version_id}'."
                )

        creator_clean = plan.created_by.strip().lower()
        actor_user_clean = actor.username.strip().lower()
        actor_id_clean = str(getattr(actor, "user_id", "")).strip().lower() if getattr(actor, "user_id", None) else ""
        if creator_clean == actor_user_clean or (actor_id_clean and creator_clean == actor_id_clean):
            raise FourEyesViolationError(
                f"Separation of duties violation: Author '{plan.created_by}' cannot review their own "
                f"plan version '{plan_version_id}'. Formal operational review requires an independent reviewer."
            )

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
        declared_reviewer_name: Optional[str] = None,
        declared_reviewer_role: Optional[str] = None,
    ) -> PlanVersionModel:
        """Formally approve an independently verified plan candidate."""
        try:
            return await self._approve_plan_internal(
                plan_version_id=plan_version_id,
                actor=actor,
                comment=comment,
                declared_reviewer_name=declared_reviewer_name,
                declared_reviewer_role=declared_reviewer_role,
            )
        except Exception:
            await self.session.rollback()
            raise

    async def _approve_plan_internal(
        self,
        plan_version_id: str,
        actor: AuthUser,
        comment: Optional[str] = None,
        declared_reviewer_name: Optional[str] = None,
        declared_reviewer_role: Optional[str] = None,
    ) -> PlanVersionModel:
        # Step 1: Pre-read target plan version to discover scenario identity
        # Uses lightweight read without row lock to establish target scenario for canonical locking order
        target_pre = await self.plan_repo.get_by_plan_version_id(plan_version_id)
        if not target_pre and hasattr(self.plan_repo, "get_by_id_for_update"):
            target_pre = await self.plan_repo.get_by_id_for_update(plan_version_id)

        if not target_pre:
            raise PlanVersionNotFoundError(f"PlanVersion '{plan_version_id}' not found.")

        target_scenario_id = target_pre.scenario_id
        if not target_scenario_id:
            raise PlanVersionApprovalBlockedError(
                f"Cannot approve PlanVersion '{plan_version_id}': PlanVersion has no associated scenario_id."
            )

        # Step 2: Acquire row lock on parent scenario FIRST (canonical lock ordering: Scenario -> Plan)
        # to serialize all approval requests across different plan versions for the same scenario.
        scenario = await self.scenario_repo.get_by_id_for_update(target_scenario_id)
        if not scenario and hasattr(self.scenario_repo, "get_by_id"):
            scenario = await self.scenario_repo.get_by_id(target_scenario_id)

        if not scenario:
            raise PlanVersionApprovalBlockedError(
                f"Cannot approve PlanVersion '{plan_version_id}': Operational scenario '{target_scenario_id}' "
                f"not found. Missing scenario provenance fails closed."
            )

        # Step 3: Fetch and lock target plan version row under the scenario lock
        plan = await self.plan_repo.get_by_id_for_update(plan_version_id)
        if not plan:
            raise PlanVersionNotFoundError(f"PlanVersion '{plan_version_id}' not found.")

        # Precondition 2: Check current status and metadata - cannot re-approve an already approved plan
        is_already_approved = (
            plan.status == PlanVersionStatus.APPROVED.value
            or isinstance(getattr(plan, "approved_at", None), (datetime, str))
            or (isinstance(getattr(plan, "approved_by", None), str) and bool(getattr(plan, "approved_by").strip()))
        )
        if is_already_approved:
            approver_info = getattr(plan, "approved_by", "prior approval") if isinstance(getattr(plan, "approved_by", None), str) else "prior approval"
            raise PlanVersionImmutableError(
                f"PlanVersion '{plan_version_id}' is already APPROVED (by '{approver_info}') and cannot be re-approved."
            )

        # Precondition 3: Legal transition check
        self.plan_repo.validate_transition(plan.status, PlanVersionStatus.APPROVED)

        # Step 4: Validate scenario binding under lock (fail-closed)
        plan_scen_id = getattr(plan, "scenario_id", None)
        locked_scen_id = getattr(scenario, "scenario_id", None)

        if not isinstance(plan_scen_id, str) or not plan_scen_id.strip():
            raise PlanFingerprintMismatchError(
                f"Cannot approve PlanVersion '{plan_version_id}': Target plan row has missing, blank, or invalid scenario_id."
            )
        if not isinstance(locked_scen_id, str) or not locked_scen_id.strip():
            raise PlanFingerprintMismatchError(
                f"Cannot approve PlanVersion '{plan_version_id}': Locked scenario has missing, blank, or invalid scenario_id."
            )
        if plan_scen_id.strip() != locked_scen_id.strip():
            raise PlanFingerprintMismatchError(
                f"Scenario mismatch under lock: Target plan scenario '{plan_scen_id.strip()}' does not match "
                f"locked scenario '{locked_scen_id.strip()}'."
            )

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

        # Precondition 6: Planning Snapshot & Fingerprint Integrity (GOV-002 / VAL-001)
        # 6.1 Stored snapshot hash must be present and not malformed
        if _is_missing_hash(plan.snapshot_hash):
            raise PlanSnapshotIntegrityError(
                f"Cannot approve PlanVersion '{plan_version_id}': Stored planning snapshot hash is missing."
            )
        if _is_malformed_hash(plan.snapshot_hash):
            raise PlanSnapshotIntegrityError(
                f"Cannot approve PlanVersion '{plan_version_id}': Stored planning snapshot hash is malformed ({repr(plan.snapshot_hash)})."
            )

        # 6.2 Stored input hash must be present and not malformed
        if _is_missing_hash(plan.input_hash):
            raise PlanSnapshotIntegrityError(
                f"Cannot approve PlanVersion '{plan_version_id}': Stored input configuration hash is missing."
            )
        if _is_malformed_hash(plan.input_hash):
            raise PlanSnapshotIntegrityError(
                f"Cannot approve PlanVersion '{plan_version_id}': Stored input configuration hash is malformed ({repr(plan.input_hash)})."
            )

        # 6.3 Schedule identity must be present and not malformed
        if _is_missing_hash(plan.schedule_identity):
            raise PlanSnapshotIntegrityError(
                f"Cannot approve PlanVersion '{plan_version_id}': Schedule identity fingerprint is missing."
            )
        if _is_malformed_hash(plan.schedule_identity):
            raise PlanSnapshotIntegrityError(
                f"Cannot approve PlanVersion '{plan_version_id}': Schedule identity fingerprint is malformed ({repr(plan.schedule_identity)})."
            )

        # 6.4 Source run binding and cryptographic consistency
        run = await self.run_repo.get_by_run_id(plan.planning_run_id)
        if not run:
            raise PlanFingerprintMismatchError(
                f"Source planning run '{plan.planning_run_id}' missing for PlanVersion '{plan_version_id}'."
            )
        if _is_missing_hash(run.snapshot_hash) or _is_malformed_hash(run.snapshot_hash):
            raise PlanSnapshotIntegrityError(
                f"Cannot approve PlanVersion '{plan_version_id}': Source run '{run.run_id}' has missing or malformed snapshot hash."
            )
        if run.snapshot_hash != plan.snapshot_hash:
            raise PlanFingerprintMismatchError("Planning snapshot hash does not match source run.")

        if _is_missing_hash(run.input_hash) or _is_malformed_hash(run.input_hash):
            raise PlanSnapshotIntegrityError(
                f"Cannot approve PlanVersion '{plan_version_id}': Source run '{run.run_id}' has missing or malformed input hash."
            )
        if run.input_hash != plan.input_hash:
            raise PlanFingerprintMismatchError("Input configuration hash does not match source run.")

        if _is_missing_hash(run.validation_fingerprint) or _is_malformed_hash(run.validation_fingerprint):
            raise PlanSnapshotIntegrityError(
                f"Cannot approve PlanVersion '{plan_version_id}': Source run '{run.run_id}' has missing or malformed validation fingerprint."
            )
        if run.validation_fingerprint != plan.schedule_identity:
            raise PlanFingerprintMismatchError(
                f"Cryptographic fingerprint mismatch: PlanVersion has '{plan.schedule_identity}', "
                f"source run has '{run.validation_fingerprint}'."
            )
        if isinstance(getattr(run, "scenario_id", None), str) and isinstance(getattr(plan, "scenario_id", None), str):
            if run.scenario_id != plan.scenario_id:
                raise PlanFingerprintMismatchError(
                    f"Scenario mismatch: PlanVersion scenario '{plan.scenario_id}' does not match "
                    f"source planning run scenario '{run.scenario_id}'."
                )

        # 6.5 Schedule result payload and embedded validation evidence
        if plan.schedule_result is None:
            raise PlanSnapshotIntegrityError(
                f"Cannot approve PlanVersion '{plan_version_id}': Schedule result payload is missing."
            )
        if isinstance(plan.schedule_result, dict):
            sched_scen = plan.schedule_result.get("scenario_id")
            if sched_scen and sched_scen != plan.scenario_id:
                raise PlanFingerprintMismatchError(
                    f"Scenario mismatch: Plan schedule result scenario '{sched_scen}' does not match "
                    f"PlanVersion scenario '{plan.scenario_id}'."
                )
            sched_snap = plan.schedule_result.get("snapshot_id")
            if sched_snap and isinstance(getattr(run, "snapshot_id", None), str) and sched_snap != run.snapshot_id:
                raise PlanFingerprintMismatchError(
                    f"Snapshot mismatch: Plan schedule result snapshot '{sched_snap}' does not match "
                    f"source run snapshot '{run.snapshot_id}'."
                )

            val_evidence = plan.schedule_result.get("validation")
            if isinstance(val_evidence, dict):
                val_identity = val_evidence.get("schedule_identity")
                if val_identity and val_identity != plan.schedule_identity:
                    raise PlanFingerprintMismatchError(
                        f"Plan mutation detected: Embedded validation certificate schedule_identity "
                        f"'{val_identity}' does not match PlanVersion schedule_identity '{plan.schedule_identity}'."
                    )
                if val_evidence.get("status") in ["INVALID", "UNKNOWN"] or val_evidence.get("is_approvable") is False:
                    raise PlanVersionApprovalBlockedError(
                        f"Cannot approve PlanVersion '{plan_version_id}': Embedded validation evidence indicates "
                        f"schedule is not approvable (status='{val_evidence.get('status')}', is_approvable={val_evidence.get('is_approvable')}). "
                        f"Stale or uncertified validation evidence cannot authorize approval."
                    )

            # 6.6 Recompute schedule identity from serialized task placements if full structure is present
            if "scheduled_tasks" in plan.schedule_result and _is_valid_sha256(plan.schedule_identity):
                snap_id_for_recompute = getattr(run, "snapshot_id", None) or plan.schedule_result.get("snapshot_id", "")
                if isinstance(snap_id_for_recompute, str) and snap_id_for_recompute:
                    recomputed_identity = IndependentScheduleValidator.compute_schedule_identity_from_dict(
                        schedule_dict=plan.schedule_result,
                        snapshot_id=snap_id_for_recompute,
                        scenario_id=plan.scenario_id,
                    )
                    if recomputed_identity != plan.schedule_identity:
                        raise PlanFingerprintMismatchError(
                            f"Schedule content tampered after validation: Recomputed schedule identity '{recomputed_identity}' "
                            f"does not match certified identity '{plan.schedule_identity}'."
                        )

        # Precondition 7: Separation of duties (Four-Eyes Principle)
        # 7.1 Verify creator provenance exists and is valid (fail closed)
        if not getattr(plan, "created_by", None) or not isinstance(plan.created_by, str) or not plan.created_by.strip():
            raise FourEyesViolationError(
                f"Cannot approve PlanVersion '{plan_version_id}': Target plan row has missing, blank, or invalid creator provenance (created_by). "
                f"Missing creator identity fails closed under Four-Eyes governance."
            )
        # 7.2 Verify approver actor identity exists and is valid (fail closed)
        if not actor or not getattr(actor, "username", None) or not isinstance(actor.username, str) or not actor.username.strip():
            raise FourEyesViolationError(
                f"Cannot approve PlanVersion '{plan_version_id}': Authenticated approver has missing, blank, or invalid actor identity. "
                f"Missing approver identity fails closed under Four-Eyes governance."
            )

        creator_clean = plan.created_by.strip().lower()
        actor_user_clean = actor.username.strip().lower()
        actor_id_clean = str(getattr(actor, "user_id", "")).strip().lower() if getattr(actor, "user_id", None) else ""

        # 7.3 Author of the plan cannot approve their own candidate
        if creator_clean == actor_user_clean or (actor_id_clean and creator_clean == actor_id_clean):
            raise FourEyesViolationError(
                f"Separation of duties violation: Author '{plan.created_by}' cannot approve their own "
                f"plan version '{plan_version_id}'. Formal operational approval requires independent review."
            )

        # 7.4 Reviewer independence: If plan was put under review, author cannot have been the reviewer
        reviewed_by = getattr(plan, "reviewed_by", None)
        if isinstance(reviewed_by, str) and reviewed_by.strip():
            reviewer_clean = reviewed_by.strip().lower()
            if reviewer_clean == creator_clean:
                raise FourEyesViolationError(
                    f"Separation of duties violation: PlanVersion '{plan_version_id}' was reviewed by its author "
                    f"'{plan.created_by}'. Independent review required."
                )

        # 7.5 Role authorization: Actor must possess 'plan:approve' permission
        if hasattr(actor, "has_permission") and callable(actor.has_permission):
            if not actor.has_permission("plan:approve"):
                raise PlanVersionApprovalBlockedError(
                    f"Actor '{actor.username}' with role '{getattr(actor.role, 'value', actor.role)}' "
                    f"lacks required permission 'plan:approve' to authorize plan version '{plan_version_id}'."
                )

        # Precondition 8: Scenario Provenance Integrity & Dataset Version (GOV-001 / GOV-002)
        if not scenario:
            scenario = await self.scenario_repo.get_by_id(plan.scenario_id)
        if not scenario:
            raise PlanVersionApprovalBlockedError(
                f"Cannot approve PlanVersion '{plan_version_id}': Operational scenario '{plan.scenario_id}' "
                f"not found. Missing scenario provenance fails closed."
            )

        # 8.1 Scenario dataset version check (detect stale snapshot / version mismatch)
        scen_dataset_ver = getattr(scenario, "dataset_version", None)
        plan_dataset_ver = getattr(plan, "dataset_version", None)
        if isinstance(scen_dataset_ver, str) and isinstance(plan_dataset_ver, str) and scen_dataset_ver != plan_dataset_ver:
            raise PlanFingerprintMismatchError(
                f"Dataset version mismatch: PlanVersion was compiled for dataset version '{plan_dataset_ver}', "
                f"but current scenario '{plan.scenario_id}' has dataset version '{scen_dataset_ver}'. "
                f"Stored snapshot is stale."
            )

        # 8.2 Real operational classification check (GOV-001)
        classification = getattr(scenario, "classification", None)
        if classification is None:
            raise PlanVersionApprovalBlockedError(
                f"Cannot approve PlanVersion '{plan_version_id}': Operational scenario '{plan.scenario_id}' "
                f"has unknown or missing data classification. Missing provenance fails closed."
            )

        if classification != DataClass.REAL:
            class_str = classification.value if hasattr(classification, "value") else str(classification)
            raise PlanVersionApprovalBlockedError(
                f"Cannot approve PlanVersion '{plan_version_id}': Operational scenario '{plan.scenario_id}' "
                f"has classification '{class_str}'. Synthetic, demonstration, or assumed scenarios "
                f"cannot be approved as real operational plans."
            )

        # Precondition 9 (F3 / GOV-002): Approval-time scenario snapshot & input hash recomputation
        # Verify that current persisted scenario data has not changed since the plan's snapshot hashes
        # were created, even if dataset_version is unchanged.
        current_snapshot = await self.scenario_repo.get_snapshot(plan.scenario_id)
        if current_snapshot is None:
            raise PlanSnapshotIntegrityError(
                f"Cannot approve PlanVersion '{plan_version_id}': Failed to load current planning "
                f"snapshot for scenario '{plan.scenario_id}'. Missing scenario data fails closed."
            )

        if not hasattr(current_snapshot, "compute_snapshot_hash") or not callable(current_snapshot.compute_snapshot_hash):
            raise PlanSnapshotIntegrityError(
                f"Cannot approve PlanVersion '{plan_version_id}': Current planning snapshot for "
                f"scenario '{plan.scenario_id}' is malformed. Missing hash computation fails closed."
            )

        try:
            recomputed_snapshot_hash = current_snapshot.compute_snapshot_hash()
        except Exception as exc:
            raise PlanSnapshotIntegrityError(
                f"Cannot approve PlanVersion '{plan_version_id}': Failed to compute snapshot hash "
                f"from current scenario data: {exc}. Malformed scenario data fails closed."
            )

        if _is_missing_hash(recomputed_snapshot_hash) or _is_malformed_hash(recomputed_snapshot_hash):
            raise PlanSnapshotIntegrityError(
                f"Cannot approve PlanVersion '{plan_version_id}': Recomputed current snapshot hash is malformed "
                f"({repr(recomputed_snapshot_hash)}). Malformed scenario data fails closed."
            )

        if recomputed_snapshot_hash != plan.snapshot_hash:
            raise PlanFingerprintMismatchError(
                f"Cannot approve PlanVersion '{plan_version_id}': Current scenario snapshot hash "
                f"'{recomputed_snapshot_hash}' does not match stored snapshot hash '{plan.snapshot_hash}'. "
                f"Underlying scenario data has changed since plan generation."
            )

        # Canonical input hash recomputation from current snapshot
        if not hasattr(current_snapshot, "compute_input_hash") or not callable(current_snapshot.compute_input_hash):
            raise PlanSnapshotIntegrityError(
                f"Cannot approve PlanVersion '{plan_version_id}': Current planning snapshot for "
                f"scenario '{plan.scenario_id}' lacks input hash capability."
            )

        config_snapshot = getattr(run, "configuration_snapshot", None) or getattr(plan, "configuration_snapshot", {}) or {}
        random_seed = getattr(run, "random_seed", 0) or 0
        try:
            recomputed_input_hash = current_snapshot.compute_input_hash(config_snapshot, seed=random_seed)
        except Exception as exc:
            raise PlanSnapshotIntegrityError(
                f"Cannot approve PlanVersion '{plan_version_id}': Failed to compute input hash "
                f"from current scenario data: {exc}."
            )

        if _is_missing_hash(recomputed_input_hash) or _is_malformed_hash(recomputed_input_hash):
            raise PlanSnapshotIntegrityError(
                f"Cannot approve PlanVersion '{plan_version_id}': Recomputed current input hash is malformed "
                f"({repr(recomputed_input_hash)})."
            )

        if recomputed_input_hash != plan.input_hash:
            raise PlanFingerprintMismatchError(
                f"Cannot approve PlanVersion '{plan_version_id}': Recomputed input hash '{recomputed_input_hash}' "
                f"does not match stored input hash '{plan.input_hash}'. "
                f"Underlying scenario inputs have changed since plan generation."
            )

        # Verify current snapshot ID against source run
        current_snap_id = getattr(current_snapshot, "snapshot_id", None)
        if _is_missing_hash(current_snap_id):
            raise PlanSnapshotIntegrityError(
                f"Cannot approve PlanVersion '{plan_version_id}': Current planning snapshot lacks snapshot_id."
            )
        run_snap_id = getattr(run, "snapshot_id", None)
        if isinstance(run_snap_id, str) and run_snap_id.strip() and current_snap_id != run_snap_id:
            raise PlanFingerprintMismatchError(
                f"Cannot approve PlanVersion '{plan_version_id}': Current snapshot identifier '{current_snap_id}' "
                f"does not match source run snapshot identifier '{run_snap_id}'."
            )

        now = datetime.now(timezone.utc)
        prev_status = plan.status

        # Supersede any previous APPROVED plan version for this scenario (locked for update)
        prev_approved = await self.plan_repo.get_latest_approved(plan.scenario_id, for_update=True)
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
            # Flush supersede first so previous approved status is cleared before new approval
            await self.session.flush()

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
                "declared_reviewer": {
                    "name": (declared_reviewer_name.strip() if isinstance(declared_reviewer_name, str) and declared_reviewer_name.strip() else None),
                    "role": (declared_reviewer_role.strip() if isinstance(declared_reviewer_role, str) and declared_reviewer_role.strip() else None),
                    "is_authoritative": False,
                } if (declared_reviewer_name or declared_reviewer_role) else None,
            },
        )
        await self.plan_repo.add_audit_event(approval_audit)

        try:
            await self.session.commit()
        except IntegrityError as e:
            if is_scenario_approval_unique_violation(e):
                raise PlanApprovalConflictError(
                    f"Approval conflict: Another plan version for scenario '{plan.scenario_id}' was concurrently approved."
                ) from e
            raise
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
        try:
            return await self._reject_plan_internal(
                plan_version_id=plan_version_id,
                actor=actor,
                reason=reason,
            )
        except Exception:
            await self.session.rollback()
            raise

    async def _reject_plan_internal(
        self,
        plan_version_id: str,
        actor: AuthUser,
        reason: str,
    ) -> PlanVersionModel:
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
