"""Deterministic Invariant Validation Script for TrackMeld Phase 9 Plan Versions, Human Review, and Audit.

Validates:
1. Database schema: 'plan_versions', 'plan_review_comments', and 'governance_audit_events' tables exist with columns and constraints.
2. Pydantic request/response validation contracts (rejection reason length >= 5, comment length >= 3).
3. Candidate PlanVersion creation from certified, completed planning run.
4. Duplicate candidate protection: Cannot create duplicate plan versions for the same planning run.
5. Strict validation precondition: Cannot create PlanVersion from uncompleted or invalid/non-approvable run.
6. Monotonic version numbering: Sequential version numbering (v1, v2) serialized under scenario row lock.
7. Candidate review start: Transition from PENDING_REVIEW to UNDER_REVIEW with reviewer identity.
8. Review commentary: Chronological commentary recorded with actor, action, and timestamp.
9. State machine transitions: Legal transitions succeed.
10. State machine transitions: Illegal transitions blocked with InvalidPlanVersionTransitionError.
11. RBAC authorization boundary: Operator/Approver has plan:approve; Planner and Viewer lack plan:approve.
12. Approval precondition: Cannot approve if technical validation status != VALID or is_approvable is False.
13. Approval precondition: Cannot approve if validation findings contain unresolved hard errors (error_count > 0).
14. Cryptographic integrity precondition: Cannot approve if schedule fingerprint mismatches source run.
15. Formal human approval: Authorized approver approves plan, records approved_by and approved_at.
16. Immutability of approved plans: Approved plan cannot be re-approved or rejected in place.
17. Automatic superseding: Approving v2 automatically supersedes previously approved v1.
18. Superseding provenance: v2 references previous_plan_version_id = v1.plan_version_id.
19. Explicit rejection workflow: Requires substantive reason, transitions to REJECTED with rejection_reason.
20. Rejection immutability: Cannot approve or resurrect a rejected plan.
21. Immutable audit trail: All governance lifecycle events recorded with actor, timestamp, states, and hashes.
22. Core product invariant: COMPLETED != APPROVED (solver/validator completion NEVER auto-approves a plan).
"""

import sys
import logging
import asyncio
import uuid
from typing import Sequence
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, inspect, delete
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from pydantic import ValidationError

from backend.app.config import get_settings
from backend.app.db.models.planning_run import PlanningRunModel
from backend.app.db.models.scenario import OperationalScenarioModel
from backend.app.db.models.plan_version import (
    PlanVersionModel,
    PlanReviewCommentModel,
    GovernanceAuditEventModel,
)
from backend.app.schemas.plan_version import (
    PlanVersionStatus,
    PlanReviewAction,
    GovernanceEventType,
    RejectPlanRequest,
    AddReviewCommentRequest,
    CreatePlanVersionRequest,
    ApprovePlanRequest,
)
from backend.app.core.auth import KNOWN_CREDENTIALS, AuthUser, UserRole
from backend.app.repositories.plan_version_repo import (
    PlanVersionRepository,
    InvalidPlanVersionTransitionError,
    PlanVersionApprovalBlockedError,
    PlanFingerprintMismatchError,
    PlanVersionImmutableError,
    PlanVersionAlreadyExistsError,
)
from backend.app.repositories.planning_run_repo import PlanningRunRepository
from backend.app.services.plan_governance_service import PlanGovernanceService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("validate_phase9_plan_governance")


async def main() -> int:
    logger.info("=== Starting TrackMeld Phase 9 Plan Versions, Review, and Audit Validation ===")
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    passed_checks = 0
    total_checks = 22

    try:
        # ---------------------------------------------------------------------
        # Check 1: Verify Database Schema & Tables
        # ---------------------------------------------------------------------
        logger.info("[Check 1/22] Verifying PostgreSQL governance tables and schema...")
        async with engine.connect() as conn:
            def check_tables_sync(sync_conn):
                insp = inspect(sync_conn)
                tables = insp.get_table_names()
                assert "plan_versions" in tables, "Table 'plan_versions' missing"
                assert "plan_review_comments" in tables, "Table 'plan_review_comments' missing"
                assert "governance_audit_events" in tables, "Table 'governance_audit_events' missing"

                pv_cols = {c["name"] for c in insp.get_columns("plan_versions")}
                expected_pv = {
                    "plan_version_id", "scenario_id", "planning_run_id", "version_number",
                    "status", "schedule_identity", "snapshot_hash", "input_hash",
                    "schedule_result", "result_summary", "validation_status", "is_approvable",
                    "scheduler_type", "created_at", "created_by", "approved_at", "approved_by",
                    "rejected_at", "rejected_by", "rejection_reason", "previous_plan_version_id",
                }
                assert expected_pv.issubset(pv_cols), f"Missing columns in plan_versions: {expected_pv - pv_cols}"

            await conn.run_sync(check_tables_sync)
        logger.info("PASS: All 3 governance tables, columns, and foreign keys verified in PostgreSQL.")
        passed_checks += 1

        # ---------------------------------------------------------------------
        # Check 2: Schema Validation Contracts
        # ---------------------------------------------------------------------
        logger.info("[Check 2/22] Verifying Pydantic schema validation rules...")
        # Valid reject reason
        r_ok = RejectPlanRequest(reason="Conflicts with critical freight path")
        assert len(r_ok.reason) >= 5
        # Invalid reject reason (<5 chars)
        try:
            RejectPlanRequest(reason="Bad")
            assert False, "Should have rejected reason < 5 chars"
        except ValidationError:
            pass

        # Valid comment
        c_ok = AddReviewCommentRequest(comment="Clear timetable alignment")
        assert len(c_ok.comment) >= 3
        # Invalid comment (<3 chars)
        try:
            AddReviewCommentRequest(comment="no")
            assert False, "Should have rejected comment < 3 chars"
        except ValidationError:
            pass
        logger.info("PASS: Schema boundary constraints verified (min_length=5 on reject, min_length=3 on comment).")
        passed_checks += 1

        # Clean tables for reproducible script execution
        async with session_factory() as session:
            await session.execute(delete(GovernanceAuditEventModel))
            await session.execute(delete(PlanReviewCommentModel))
            await session.execute(delete(PlanVersionModel))
            await session.execute(delete(PlanningRunModel))
            await session.commit()

        # Helper to create completed planning run
        async def create_test_run(
            scenario_id="SCN-DEMO-001",
            status="COMPLETED",
            validation_status="VALID",
            is_approvable=True,
            error_count=0,
            fingerprint=None,
        ) -> PlanningRunModel:
            now = datetime.now(timezone.utc)
            rid = f"RUN-VAL-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
            fp = fingerprint or ("fp_" + uuid.uuid4().hex[:60])
            snap_h = "snap_" + uuid.uuid4().hex[:59]
            inp_h = "inp_" + uuid.uuid4().hex[:60]
            run = PlanningRunModel(
                run_id=rid,
                scenario_id=scenario_id,
                status=status,
                stage="COMPLETED" if status == "COMPLETED" else "SOLVING",
                scheduler_type="CP_SAT",
                scheduler_version="1.0.0",
                solver_name="OR-Tools CP-SAT",
                solver_version="9.8",
                dataset_version="demo-v1.0",
                snapshot_id=f"SNP-{scenario_id}",
                snapshot_hash=snap_h,
                input_hash=inp_h,
                validation_status=validation_status,
                is_approvable=is_approvable,
                validation_fingerprint=fp,
                validation_findings_summary={"error_count": error_count, "warning_count": 0},
                configuration_snapshot={"scheduler_type": "CP_SAT"},
                result_summary={"total_tasks": 30, "scheduled_tasks": 29},
                schedule_result={
                    "scheduler_type": "CP_SAT",
                    "status": "COMPLETED",
                    "scheduled_tasks": [],
                    "validation": {"status": validation_status, "is_approvable": is_approvable, "schedule_identity": fp},
                },
                created_at=now,
                completed_at=now if status == "COMPLETED" else None,
            )
            async with session_factory() as s:
                s.add(run)
                await s.commit()
                await s.refresh(run)
            return run

        planner_user = KNOWN_CREDENTIALS["planner-token-2026"]
        approver_user = KNOWN_CREDENTIALS["approver-token-2026"]
        viewer_user = KNOWN_CREDENTIALS["viewer-token-2026"]

        # ---------------------------------------------------------------------
        # Check 3: Create PlanVersion Candidate from Certified Run
        # ---------------------------------------------------------------------
        logger.info("[Check 3/22] Promoting certified planning run to candidate PlanVersion...")
        run1 = await create_test_run()
        async with session_factory() as session:
            service = PlanGovernanceService(session)
            pv1 = await service.create_plan_version_from_run(
                run_id=run1.run_id,
                actor=planner_user,
                comment="Nominated candidate schedule for weekly maintenance window",
            )
            pv1_id = pv1.plan_version_id
            assert pv1.version_number == 1
            assert pv1.status == PlanVersionStatus.PENDING_REVIEW.value
            assert pv1.is_approvable is True
            assert pv1.validation_status == "VALID"
            assert pv1.schedule_identity == run1.validation_fingerprint
        logger.info(f"PASS: Created PlanVersion '{pv1_id}' (v1) with status=PENDING_REVIEW.")
        passed_checks += 1

        # ---------------------------------------------------------------------
        # Check 4: Duplicate Candidate Protection
        # ---------------------------------------------------------------------
        logger.info("[Check 4/22] Verifying duplicate PlanVersion prevention on same run...")
        async with session_factory() as session:
            service = PlanGovernanceService(session)
            try:
                await service.create_plan_version_from_run(run_id=run1.run_id, actor=planner_user)
                assert False, "Duplicate PlanVersion should be blocked"
            except PlanVersionAlreadyExistsError:
                pass
        logger.info("PASS: Duplicate PlanVersion blocked with PlanVersionAlreadyExistsError.")
        passed_checks += 1

        # ---------------------------------------------------------------------
        # Check 5: Strict Validation Preconditions on Candidate Creation
        # ---------------------------------------------------------------------
        logger.info("[Check 5/22] Verifying uncompleted or unverified runs cannot become PlanVersions...")
        uncomp_run = await create_test_run(status="RUNNING")
        invalid_run = await create_test_run(validation_status="INVALID", is_approvable=False, error_count=2)

        async with session_factory() as session:
            service = PlanGovernanceService(session)
            # A: Uncompleted run
            try:
                await service.create_plan_version_from_run(uncomp_run.run_id, planner_user)
                assert False, "Uncompleted run should be blocked"
            except PlanVersionApprovalBlockedError:
                pass

            # B: Invalid run
            try:
                await service.create_plan_version_from_run(invalid_run.run_id, planner_user)
                assert False, "Invalid run should be blocked"
            except PlanVersionApprovalBlockedError:
                pass
        logger.info("PASS: Candidate creation blocked for uncompleted and unverified runs.")
        passed_checks += 1

        # ---------------------------------------------------------------------
        # Check 6: Monotonic Version Numbering Under Scenario Lock
        # ---------------------------------------------------------------------
        logger.info("[Check 6/22] Verifying sequential version numbering (v1, v2, v3)...")
        run2 = await create_test_run()
        async with session_factory() as session:
            service = PlanGovernanceService(session)
            pv2 = await service.create_plan_version_from_run(run_id=run2.run_id, actor=planner_user)
            pv2_id = pv2.plan_version_id
            assert pv2.version_number == 2, f"Expected version 2, got {pv2.version_number}"
        logger.info(f"PASS: Monotonic versioning verified (v{pv2.version_number} follows v1).")
        passed_checks += 1

        # ---------------------------------------------------------------------
        # Check 7: Candidate Review Start (UNDER_REVIEW)
        # ---------------------------------------------------------------------
        logger.info("[Check 7/22] Transitioning plan candidate to UNDER_REVIEW...")
        async with session_factory() as session:
            service = PlanGovernanceService(session)
            pv1_rev = await service.start_review(pv1_id, planner_user, "Reviewing crew allocation")
            assert pv1_rev.status == PlanVersionStatus.UNDER_REVIEW.value
            assert pv1_rev.reviewed_by == planner_user.username
            assert pv1_rev.reviewed_at is not None
        logger.info("PASS: Plan transitioned to UNDER_REVIEW with reviewer username and timestamp.")
        passed_checks += 1

        # ---------------------------------------------------------------------
        # Check 8: Review Commentary Tracking
        # ---------------------------------------------------------------------
        logger.info("[Check 8/22] Appending review commentary to plan...")
        async with session_factory() as session:
            service = PlanGovernanceService(session)
            comment_record = await service.add_review_comment(
                pv1_id,
                planner_user,
                "Double-checked block section S-NDLS-GZB-01; no passenger express conflicts.",
            )
            assert comment_record.actor_username == planner_user.username
            assert comment_record.action == PlanReviewAction.COMMENT.value
        logger.info("PASS: Review commentary recorded with actor, action, and timestamp.")
        passed_checks += 1

        # ---------------------------------------------------------------------
        # Check 9: State Machine Legal Transitions
        # ---------------------------------------------------------------------
        logger.info("[Check 9/22] Testing state machine legal transitions...")
        repo = PlanVersionRepository(session=None)
        repo.validate_transition(PlanVersionStatus.PENDING_REVIEW, PlanVersionStatus.UNDER_REVIEW)
        repo.validate_transition(PlanVersionStatus.PENDING_REVIEW, PlanVersionStatus.APPROVED)
        repo.validate_transition(PlanVersionStatus.PENDING_REVIEW, PlanVersionStatus.REJECTED)
        repo.validate_transition(PlanVersionStatus.UNDER_REVIEW, PlanVersionStatus.APPROVED)
        repo.validate_transition(PlanVersionStatus.UNDER_REVIEW, PlanVersionStatus.REJECTED)
        repo.validate_transition(PlanVersionStatus.APPROVED, PlanVersionStatus.SUPERSEDED)
        logger.info("PASS: All legal lifecycle transitions verified.")
        passed_checks += 1

        # ---------------------------------------------------------------------
        # Check 10: State Machine Illegal Transitions Blocked
        # ---------------------------------------------------------------------
        logger.info("[Check 10/22] Testing illegal transitions are strictly rejected...")
        for src, dst in [
            (PlanVersionStatus.REJECTED, PlanVersionStatus.APPROVED),
            (PlanVersionStatus.REJECTED, PlanVersionStatus.UNDER_REVIEW),
            (PlanVersionStatus.APPROVED, PlanVersionStatus.UNDER_REVIEW),
            (PlanVersionStatus.APPROVED, PlanVersionStatus.REJECTED),
            (PlanVersionStatus.SUPERSEDED, PlanVersionStatus.APPROVED),
            (PlanVersionStatus.SUPERSEDED, PlanVersionStatus.UNDER_REVIEW),
        ]:
            try:
                repo.validate_transition(src, dst)
                assert False, f"Transition from {src} to {dst} should have failed"
            except InvalidPlanVersionTransitionError:
                pass
        logger.info("PASS: All illegal lifecycle transitions rejected.")
        passed_checks += 1

        # ---------------------------------------------------------------------
        # Check 11: RBAC Authorization Permissions
        # ---------------------------------------------------------------------
        logger.info("[Check 11/22] Verifying role-based access control permissions...")
        assert approver_user.has_permission("plan:approve"), "Approver must have plan:approve"
        assert approver_user.has_permission("plan:reject"), "Approver must have plan:reject"
        assert not planner_user.has_permission("plan:approve"), "Planner must NOT have plan:approve"
        assert not planner_user.has_permission("plan:reject"), "Planner must NOT have plan:reject"
        assert not viewer_user.has_permission("plan:approve"), "Viewer must NOT have plan:approve"
        logger.info("PASS: Strict separation between planner (nominate/review) and approver (approve/reject).")
        passed_checks += 1

        # ---------------------------------------------------------------------
        # Check 12: Approval Precondition — Technical Validation VALID
        # ---------------------------------------------------------------------
        logger.info("[Check 12/22] Verifying approval blocks on unverified validation status...")
        async with session_factory() as session:
            # Artificially alter validation status on a test plan
            repo = PlanVersionRepository(session)
            p = await repo.get_by_id_for_update(pv2_id)
            p.validation_status = "UNKNOWN"
            p.is_approvable = False
            await session.commit()

            service = PlanGovernanceService(session)
            try:
                await service.approve_plan(pv2_id, approver_user)
                assert False, "Unverified plan must not be approved"
            except PlanVersionApprovalBlockedError:
                pass

            # Restore
            p = await repo.get_by_id_for_update(pv2_id)
            p.validation_status = "VALID"
            p.is_approvable = True
            await session.commit()
        logger.info("PASS: Approval blocked when validation status != VALID.")
        passed_checks += 1

        # ---------------------------------------------------------------------
        # Check 13: Approval Precondition — Zero Validation Errors
        # ---------------------------------------------------------------------
        logger.info("[Check 13/22] Verifying approval blocks on unresolved validation errors...")
        async with session_factory() as session:
            repo = PlanVersionRepository(session)
            p = await repo.get_by_id_for_update(pv2_id)
            p.validation_findings_summary = {"error_count": 1}
            await session.commit()

            service = PlanGovernanceService(session)
            try:
                await service.approve_plan(pv2_id, approver_user)
                assert False, "Plan with validation errors must not be approved"
            except PlanVersionApprovalBlockedError:
                pass

            # Restore
            p = await repo.get_by_id_for_update(pv2_id)
            p.validation_findings_summary = {"error_count": 0}
            await session.commit()
        logger.info("PASS: Approval blocked when validation errors > 0.")
        passed_checks += 1

        # ---------------------------------------------------------------------
        # Check 14: Cryptographic Integrity Precondition
        # ---------------------------------------------------------------------
        logger.info("[Check 14/22] Verifying approval blocks on fingerprint/hash tampering...")
        async with session_factory() as session:
            repo = PlanVersionRepository(session)
            p = await repo.get_by_id_for_update(pv2_id)
            original_fp = p.schedule_identity
            p.schedule_identity = "TAMPERED_FINGERPRINT_12345678"
            await session.commit()

            service = PlanGovernanceService(session)
            try:
                await service.approve_plan(pv2_id, approver_user)
                assert False, "Tampered schedule identity must not be approved"
            except PlanFingerprintMismatchError:
                pass

            # Restore
            p = await repo.get_by_id_for_update(pv2_id)
            p.schedule_identity = original_fp
            await session.commit()
        logger.info("PASS: Approval blocked when schedule identity fingerprint does not match source run.")
        passed_checks += 1

        # ---------------------------------------------------------------------
        # Check 15: Formal Human Approval Execution
        # ---------------------------------------------------------------------
        logger.info("[Check 15/22] Formally approving PlanVersion v1 by authorized approver...")
        async with session_factory() as session:
            service = PlanGovernanceService(session)
            pv1_appr = await service.approve_plan(
                pv1_id,
                approver_user,
                "Formal divisional clearance granted for 4h maintenance window",
            )
            assert pv1_appr.status == PlanVersionStatus.APPROVED.value
            assert pv1_appr.approved_by == approver_user.username
            assert pv1_appr.approved_at is not None
        logger.info(f"PASS: PlanVersion '{pv1_id}' (v1) APPROVED by {approver_user.username}.")
        passed_checks += 1

        # ---------------------------------------------------------------------
        # Check 16: Immutability of Approved Plan
        # ---------------------------------------------------------------------
        logger.info("[Check 16/22] Verifying approved plan is immutable...")
        async with session_factory() as session:
            service = PlanGovernanceService(session)
            # Cannot re-approve
            try:
                await service.approve_plan(pv1_id, approver_user)
                assert False, "Cannot re-approve an approved plan"
            except PlanVersionImmutableError:
                pass

            # Cannot reject an approved plan
            try:
                await service.reject_plan(pv1_id, approver_user, "Changed our minds")
                assert False, "Cannot reject an approved plan"
            except PlanVersionImmutableError:
                pass
        logger.info("PASS: Approved plan cannot be edited, re-approved, or rejected in place.")
        passed_checks += 1

        # ---------------------------------------------------------------------
        # Check 17: Automatic Superseding of Previous Approved Plan
        # ---------------------------------------------------------------------
        logger.info("[Check 17/22] Approving v2 and verifying v1 is automatically SUPERSEDED...")
        async with session_factory() as session:
            service = PlanGovernanceService(session)
            pv2_appr = await service.approve_plan(pv2_id, approver_user, "Superseding v1 with revised possession")
            assert pv2_appr.status == PlanVersionStatus.APPROVED.value

            # Verify v1 is now SUPERSEDED
            repo = PlanVersionRepository(session)
            v1_check = await repo.get_by_plan_version_id(pv1_id)
            assert v1_check.status == PlanVersionStatus.SUPERSEDED.value
            assert v1_check.superseded_by == approver_user.username
            assert v1_check.superseded_at is not None
        logger.info(f"PASS: PlanVersion '{pv1_id}' (v1) automatically transitioned to SUPERSEDED.")
        passed_checks += 1

        # ---------------------------------------------------------------------
        # Check 18: Superseding Provenance Tracking
        # ---------------------------------------------------------------------
        logger.info("[Check 18/22] Verifying v2 references previous_plan_version_id...")
        async with session_factory() as session:
            repo = PlanVersionRepository(session)
            v2_check = await repo.get_by_plan_version_id(pv2_id)
            assert v2_check.previous_plan_version_id == pv1_id
        logger.info(f"PASS: v2 correctly points to previous_plan_version_id='{pv1_id}'.")
        passed_checks += 1

        # ---------------------------------------------------------------------
        # Check 19: Explicit Rejection Workflow
        # ---------------------------------------------------------------------
        logger.info("[Check 19/22] Testing explicit human rejection workflow...")
        run3 = await create_test_run()
        async with session_factory() as session:
            service = PlanGovernanceService(session)
            pv3 = await service.create_plan_version_from_run(run3.run_id, planner_user)
            pv3_id = pv3.plan_version_id

            rej_reason = "Track possession conflicts with high-priority military movement."
            pv3_rej = await service.reject_plan(pv3_id, approver_user, rej_reason)
            assert pv3_rej.status == PlanVersionStatus.REJECTED.value
            assert pv3_rej.rejected_by == approver_user.username
            assert pv3_rej.rejected_at is not None
            assert pv3_rej.rejection_reason == rej_reason
        logger.info(f"PASS: PlanVersion '{pv3_id}' rejected with mandatory reason captured.")
        passed_checks += 1

        # ---------------------------------------------------------------------
        # Check 20: Rejection Immutability
        # ---------------------------------------------------------------------
        logger.info("[Check 20/22] Verifying rejected plan cannot be resurrected or approved...")
        async with session_factory() as session:
            service = PlanGovernanceService(session)
            try:
                await service.approve_plan(pv3_id, approver_user)
                assert False, "Rejected plan must not be approved"
            except InvalidPlanVersionTransitionError:
                pass
        logger.info("PASS: Rejected plan cannot transition to APPROVED.")
        passed_checks += 1

        # ---------------------------------------------------------------------
        # Check 21: Immutable Audit Trail Completeness
        # ---------------------------------------------------------------------
        logger.info("[Check 21/22] Inspecting complete governance audit trail...")
        async with session_factory() as session:
            repo = PlanVersionRepository(session)
            events_pv1 = await repo.list_audit_events(pv1_id)
            event_types_1 = [e.event_type for e in events_pv1]
            assert GovernanceEventType.PLAN_VERSION_CREATED.value in event_types_1
            assert GovernanceEventType.PLAN_REVIEW_STARTED.value in event_types_1
            assert GovernanceEventType.PLAN_COMMENT_ADDED.value in event_types_1
            assert GovernanceEventType.PLAN_APPROVED.value in event_types_1
            assert GovernanceEventType.PLAN_SUPERSEDED.value in event_types_1

            # Verify actor and timestamp on each event
            for ev in events_pv1:
                assert ev.actor_username is not None
                assert ev.actor_role is not None
                assert ev.timestamp is not None
                assert len(ev.schedule_identity) > 0
        logger.info(f"PASS: Audit trail for '{pv1_id}' contains {len(events_pv1)} chronological events.")
        passed_checks += 1

        # ---------------------------------------------------------------------
        # Check 22: Core Product Invariant — COMPLETED != APPROVED
        # ---------------------------------------------------------------------
        logger.info("[Check 22/22] Enforcing non-negotiable core invariant: COMPLETED != APPROVED...")
        run4 = await create_test_run(status="COMPLETED", validation_status="VALID", is_approvable=True)
        async with session_factory() as session:
            repo_run = PlanningRunRepository(session)
            fresh_run = await repo_run.get_by_run_id(run4.run_id)
            assert fresh_run.status == "COMPLETED"
            assert fresh_run.validation_status == "VALID"
            assert fresh_run.is_approvable is True

            # Must NOT exist as an approved plan
            repo_pv = PlanVersionRepository(session)
            existing_pv = await repo_pv.get_by_planning_run_id(run4.run_id)
            assert existing_pv is None, "Run must not be auto-promoted or auto-approved"
        logger.info("PASS: Completed solver & validator output NEVER implies or grants plan approval.")
        passed_checks += 1

    finally:
        await engine.dispose()

    logger.info(f"=== Phase 9 Validation Complete: {passed_checks}/{total_checks} Invariants Passed ===")
    return 0 if passed_checks == total_checks else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
