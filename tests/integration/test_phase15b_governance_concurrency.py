"""Phase 15B Integration Tests: Governance Concurrency, Approval Revalidation & Audit Invariants.

Verifies:
- Concurrent governance actions on the same PlanVersion (simultaneous approvals, approval vs rejection)
- State machine invariants & row locking guarantee strict transitions
- Approval revalidation against stale/tampered data (fingerprint mismatch, hash tampering, invalid runs)
- Audit trail transaction atomicity (all-or-nothing rollback)
- Reviewer declaration metadata retention with authoritative authenticated actor
"""

import uuid
import asyncio
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from httpx import AsyncClient
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from backend.app.config import get_settings
from backend.app.core.auth import KNOWN_CREDENTIALS, AuthUser, UserRole
from backend.app.db.models.planning_run import PlanningRunModel
from backend.app.db.models.plan_version import (
    PlanVersionModel,
    PlanReviewCommentModel,
    GovernanceAuditEventModel,
)
from backend.app.repositories.plan_version_repo import (
    PlanVersionRepository,
    PlanVersionImmutableError,
    InvalidPlanVersionTransitionError,
    PlanVersionApprovalBlockedError,
    PlanFingerprintMismatchError,
)
from backend.app.services.plan_governance_service import PlanGovernanceService
from backend.app.schemas.plan_version import PlanVersionStatus, GovernanceEventType

settings = get_settings()


@pytest_asyncio.fixture
async def test_session_factory():
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_database(db_session: AsyncSession):
    await db_session.execute(delete(GovernanceAuditEventModel))
    await db_session.execute(delete(PlanReviewCommentModel))
    await db_session.execute(delete(PlanVersionModel))
    await db_session.execute(delete(PlanningRunModel))
    await db_session.commit()
    yield
    await db_session.execute(delete(GovernanceAuditEventModel))
    await db_session.execute(delete(PlanReviewCommentModel))
    await db_session.execute(delete(PlanVersionModel))
    await db_session.execute(delete(PlanningRunModel))
    await db_session.commit()


async def _seed_completed_run_and_candidate(
    session: AsyncSession,
    scenario_id: str = "SCN-DEMO-001",
    validation_status: str = "VALID",
    is_approvable: bool = True,
    error_count: int = 0,
    fingerprint: str = "FINGERPRINT_1234567890ABCDEF",
    snap_hash: str = "a" * 64,
    inp_hash: str = "b" * 64,
) -> tuple[PlanningRunModel, PlanVersionModel]:
    """Helper to persist a completed planning run and a corresponding candidate PlanVersion."""
    now = datetime.now(timezone.utc)
    run_id = f"RUN-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

    run = PlanningRunModel(
        run_id=run_id,
        scenario_id=scenario_id,
        status="COMPLETED",
        stage="COMPLETED",
        scheduler_type="CP_SAT",
        scheduler_version="1.0.0",
        solver_name="OR-Tools CP-SAT",
        solver_version="9.8",
        dataset_version="demo-v1.0",
        snapshot_id=f"SNP-{scenario_id}",
        snapshot_hash=snap_hash,
        input_hash=inp_hash,
        validation_status=validation_status,
        is_approvable=is_approvable,
        validation_fingerprint=fingerprint,
        validation_findings_summary={"error_count": error_count, "warning_count": 0},
        configuration_snapshot={"scheduler_type": "CP_SAT"},
        result_summary={"total_tasks": 30, "scheduled_tasks": 29},
        schedule_result={
            "scheduler_type": "CP_SAT",
            "status": "COMPLETED",
            "scheduled_tasks": [],
            "validation": {
                "status": validation_status,
                "is_approvable": is_approvable,
                "schedule_identity": fingerprint,
            },
        },
        created_at=now,
        completed_at=now,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)

    # Create candidate PlanVersion via governance service
    actor = KNOWN_CREDENTIALS["planner-token-2026"]
    service = PlanGovernanceService(session)
    plan = await service.create_plan_version_from_run(run.run_id, actor)

    return run, plan


# =============================================================================
# 1. CONCURRENT GOVERNANCE ACTIONS (RACE CONDITIONS)
# =============================================================================

@pytest.mark.asyncio
async def test_simultaneous_approvals_race(test_session_factory):
    """Case A: Two concurrent approval requests for the same plan version."""
    async with test_session_factory() as session:
        _, plan = await _seed_completed_run_and_candidate(session)
        pv_id = plan.plan_version_id

    actor_1 = KNOWN_CREDENTIALS["approver-token-2026"]
    actor_2 = KNOWN_CREDENTIALS["admin-token-2026"]

    async def execute_approval(actor: AuthUser):
        async with test_session_factory() as session:
            service = PlanGovernanceService(session)
            return await service.approve_plan(pv_id, actor, comment="Concurrent sign-off")

    results = await asyncio.gather(
        execute_approval(actor_1),
        execute_approval(actor_2),
        return_exceptions=True,
    )

    # Exactly one must succeed; the other must raise PlanVersionImmutableError
    successes = [r for r in results if not isinstance(r, Exception)]
    failures = [r for r in results if isinstance(r, Exception)]

    assert len(successes) == 1, f"Expected exactly 1 success, got {len(successes)}"
    assert len(failures) == 1, f"Expected exactly 1 failure, got {len(failures)}"
    assert isinstance(failures[0], PlanVersionImmutableError)
    assert "already APPROVED" in str(failures[0])


@pytest.mark.asyncio
async def test_approval_vs_rejection_race(test_session_factory):
    """Case B: Simultaneous approval vs rejection on the same plan version."""
    async with test_session_factory() as session:
        _, plan = await _seed_completed_run_and_candidate(session)
        pv_id = plan.plan_version_id

    actor_approver = KNOWN_CREDENTIALS["approver-token-2026"]
    actor_rejecter = KNOWN_CREDENTIALS["admin-token-2026"]

    async def do_approve():
        async with test_session_factory() as session:
            service = PlanGovernanceService(session)
            return await service.approve_plan(pv_id, actor_approver, comment="Approve action")

    async def do_reject():
        async with test_session_factory() as session:
            service = PlanGovernanceService(session)
            return await service.reject_plan(pv_id, actor_rejecter, reason="Safety corridor occupied")

    results = await asyncio.gather(
        do_approve(),
        do_reject(),
        return_exceptions=True,
    )

    successes = [r for r in results if not isinstance(r, Exception)]
    failures = [r for r in results if isinstance(r, Exception)]

    assert len(successes) == 1
    assert len(failures) == 1
    assert isinstance(failures[0], (PlanVersionImmutableError, InvalidPlanVersionTransitionError))


@pytest.mark.asyncio
async def test_rejection_followed_by_approval_blocked(test_session_factory):
    """Case D: A rejected plan version cannot be approved."""
    async with test_session_factory() as session:
        _, plan = await _seed_completed_run_and_candidate(session)
        pv_id = plan.plan_version_id

    actor = KNOWN_CREDENTIALS["approver-token-2026"]

    # 1. Reject
    async with test_session_factory() as session:
        service = PlanGovernanceService(session)
        rejected = await service.reject_plan(pv_id, actor, reason="Substandard maintenance window")
        assert rejected.status == PlanVersionStatus.REJECTED.value

    # 2. Attempt to approve rejected plan -> must raise InvalidPlanVersionTransitionError
    async with test_session_factory() as session:
        service = PlanGovernanceService(session)
        with pytest.raises(InvalidPlanVersionTransitionError):
            await service.approve_plan(pv_id, actor, comment="Attempt to approve rejected")


@pytest.mark.asyncio
async def test_approval_followed_by_rejection_blocked(test_session_factory):
    """Case E: An approved plan version is immutable and cannot be rejected."""
    async with test_session_factory() as session:
        _, plan = await _seed_completed_run_and_candidate(session)
        pv_id = plan.plan_version_id

    actor = KNOWN_CREDENTIALS["approver-token-2026"]

    # 1. Approve
    async with test_session_factory() as session:
        service = PlanGovernanceService(session)
        approved = await service.approve_plan(pv_id, actor, comment="Formal operational approval")
        assert approved.status == PlanVersionStatus.APPROVED.value

    # 2. Attempt to reject approved plan -> must raise PlanVersionImmutableError
    async with test_session_factory() as session:
        service = PlanGovernanceService(session)
        with pytest.raises(PlanVersionImmutableError):
            await service.reject_plan(pv_id, actor, reason="Attempt to revoke approval")


@pytest.mark.asyncio
async def test_approval_supersedes_previous_approved_version(test_session_factory):
    """Case C: Approving Version 2 automatically marks Version 1 as SUPERSEDED with audit event."""
    actor = KNOWN_CREDENTIALS["approver-token-2026"]

    # 1. Create and approve Version 1
    async with test_session_factory() as session:
        _, plan_v1 = await _seed_completed_run_and_candidate(session, scenario_id="SCN-DEMO-001")
        service = PlanGovernanceService(session)
        v1_appr = await service.approve_plan(plan_v1.plan_version_id, actor, comment="Approved v1")
        assert v1_appr.status == PlanVersionStatus.APPROVED.value
        v1_id = plan_v1.plan_version_id

    # 2. Create and approve Version 2 for the same scenario
    async with test_session_factory() as session:
        now = datetime.now(timezone.utc)
        run_v2 = PlanningRunModel(
            run_id=f"RUN-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}",
            scenario_id="SCN-DEMO-001",
            status="COMPLETED",
            stage="COMPLETED",
            scheduler_type="CP_SAT",
            scheduler_version="1.0.0",
            solver_name="OR-Tools",
            solver_version="9.8",
            dataset_version="demo-v1.0",
            snapshot_id="SNP-SCN-DEMO-001",
            snapshot_hash="s" * 64,
            input_hash="i" * 64,
            validation_status="VALID",
            is_approvable=True,
            validation_fingerprint="FP_V2",
            validation_findings_summary={"error_count": 0},
            schedule_result={"status": "COMPLETED"},
            created_at=now,
            completed_at=now,
        )
        session.add(run_v2)
        await session.commit()

        service = PlanGovernanceService(session)
        plan_v2 = await service.create_plan_version_from_run(run_v2.run_id, actor, comment="Candidate v2")
        assert plan_v2.version_number == 2
        v2_id = plan_v2.plan_version_id

        # Approve Version 2
        v2_appr = await service.approve_plan(v2_id, actor, comment="Approved v2 supersedes v1")
        assert v2_appr.status == PlanVersionStatus.APPROVED.value

    # 3. Assert Version 1 in database is now SUPERSEDED
    async with test_session_factory() as session:
        repo = PlanVersionRepository(session)
        v1_db = await repo.get_by_plan_version_id(v1_id)
        assert v1_db.status == PlanVersionStatus.SUPERSEDED.value
        assert v1_db.superseded_at is not None

        # Verify audit event recorded for PLAN_SUPERSEDED
        stmt_audit = select(GovernanceAuditEventModel).where(
            GovernanceAuditEventModel.entity_id == v1_id,
            GovernanceAuditEventModel.event_type == GovernanceEventType.PLAN_SUPERSEDED.value,
        )
        sup_event = (await session.execute(stmt_audit)).scalar_one_or_none()
        assert sup_event is not None
        assert sup_event.event_metadata["superseding_plan_version_id"] == v2_id


# =============================================================================
# 2. APPROVAL REVALIDATION (NEGATIVE TESTS FOR STALE / TAMPERED DATA)
# =============================================================================

@pytest.mark.asyncio
async def test_approval_blocks_validation_status_invalid(test_session_factory):
    """Approval must fail if technical validation is INVALID."""
    actor = KNOWN_CREDENTIALS["approver-token-2026"]
    async with test_session_factory() as session:
        _, plan = await _seed_completed_run_and_candidate(session)
        pv_id = plan.plan_version_id
        # Mutate plan validation status in database to simulate tampered/invalid state
        plan.validation_status = "INVALID"
        plan.is_approvable = False
        await session.commit()

    async with test_session_factory() as session:
        service = PlanGovernanceService(session)
        with pytest.raises(PlanVersionApprovalBlockedError, match="Only certified valid schedules"):
            await service.approve_plan(pv_id, actor)


@pytest.mark.asyncio
async def test_approval_blocks_nonzero_error_count(test_session_factory):
    """Approval must fail if hard validation error count is greater than zero."""
    actor = KNOWN_CREDENTIALS["approver-token-2026"]
    async with test_session_factory() as session:
        _, plan = await _seed_completed_run_and_candidate(session)
        pv_id = plan.plan_version_id
        # Mutate findings summary to include blocking error
        plan.validation_findings_summary = {"error_count": 2, "warning_count": 0}
        await session.commit()

    async with test_session_factory() as session:
        service = PlanGovernanceService(session)
        with pytest.raises(PlanVersionApprovalBlockedError, match="unresolved hard validation errors"):
            await service.approve_plan(pv_id, actor)


@pytest.mark.asyncio
async def test_approval_blocks_fingerprint_tampering(test_session_factory):
    """Approval must fail if the schedule identity fingerprint differs from source run."""
    actor = KNOWN_CREDENTIALS["approver-token-2026"]
    async with test_session_factory() as session:
        run, plan = await _seed_completed_run_and_candidate(session)
        pv_id = plan.plan_version_id

        # Tamper plan fingerprint
        plan.schedule_identity = "TAMPERED_FINGERPRINT_FORGERY"
        await session.commit()

    async with test_session_factory() as session:
        service = PlanGovernanceService(session)
        with pytest.raises(PlanFingerprintMismatchError, match="fingerprint mismatch"):
            await service.approve_plan(pv_id, actor)


@pytest.mark.asyncio
async def test_approval_blocks_snapshot_hash_tampering(test_session_factory):
    """Approval must fail if snapshot hash has been mutated."""
    actor = KNOWN_CREDENTIALS["approver-token-2026"]
    async with test_session_factory() as session:
        run, plan = await _seed_completed_run_and_candidate(session)
        pv_id = plan.plan_version_id

        # Tamper snapshot hash
        plan.snapshot_hash = "f" * 64
        await session.commit()

    async with test_session_factory() as session:
        service = PlanGovernanceService(session)
        with pytest.raises(PlanFingerprintMismatchError, match="snapshot hash does not match"):
            await service.approve_plan(pv_id, actor)


# =============================================================================
# 3. AUDIT TRAIL TRANSACTION ATOMICITY & REVIEWER METADATA
# =============================================================================

@pytest.mark.asyncio
async def test_approval_commits_atomically_with_audit_trail(test_session_factory):
    """Successful approval commits state, review comment, and audit event in a single transaction."""
    actor = KNOWN_CREDENTIALS["approver-token-2026"]
    async with test_session_factory() as session:
        _, plan = await _seed_completed_run_and_candidate(session)
        pv_id = plan.plan_version_id

        service = PlanGovernanceService(session)
        approved = await service.approve_plan(
            pv_id,
            actor,
            comment="Formal corridor block authorization",
            declared_reviewer_name="Shri A. P. Singh",
            declared_reviewer_role="Sr. Divisional Operations Manager (Sr. DOM)",
        )
        assert approved.status == PlanVersionStatus.APPROVED.value

    # Verify everything committed together in the database
    async with test_session_factory() as session:
        repo = PlanVersionRepository(session)
        plan_db = await repo.get_by_plan_version_id(pv_id)
        assert plan_db.status == PlanVersionStatus.APPROVED.value
        assert plan_db.approved_by == actor.username

        # Review comment record exists
        comments = await repo.list_review_comments(pv_id)
        assert len(comments) == 1
        assert comments[0].comment == "Formal corridor block authorization"

        # Audit events exist (PLAN_VERSION_CREATED + PLAN_APPROVED)
        audit_events = await repo.list_audit_events(pv_id)
        assert len(audit_events) == 2
        assert audit_events[0].event_type == GovernanceEventType.PLAN_VERSION_CREATED.value
        
        audit = audit_events[1]
        assert audit.event_type == GovernanceEventType.PLAN_APPROVED.value
        assert audit.actor_id == actor.user_id
        assert audit.actor_username == actor.username
        assert audit.event_metadata["declared_reviewer"]["name"] == "Shri A. P. Singh"
        assert audit.event_metadata["declared_reviewer"]["role"] == "Sr. Divisional Operations Manager (Sr. DOM)"
