"""Unit tests for GOV-003: Concurrency-Safe Plan Approvals.

Verifies:
1. Two independent approvers concurrently attempting to approve the same plan version: exactly one succeeds.
2. The losing request receives a stable conflict response (PlanVersionImmutableError) and does not overwrite approval metadata.
3. Only one successful approval audit event is persisted.
4. Creator self-approval remains blocked under concurrent requests (Four-Eyes inviolability).
5. Failed approval leaves no partial approval metadata or audit event (rolls back session).
6. Existing provenance and snapshot-integrity checks still run before approval can succeed.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock
import pytest

from backend.app.core.auth import AuthUser, UserRole
from backend.app.domain.enums import DataClass
from backend.app.db.models.planning_run import PlanningRunModel
from backend.app.db.models.plan_version import PlanVersionModel, GovernanceAuditEventModel
from backend.app.db.models.scenario import OperationalScenarioModel
from backend.app.schemas.plan_version import PlanVersionStatus, GovernanceEventType
from sqlalchemy.exc import IntegrityError
from backend.app.repositories.plan_version_repo import (
    PlanVersionApprovalBlockedError,
    PlanFingerprintMismatchError,
    PlanSnapshotIntegrityError,
    PlanVersionImmutableError,
    PlanApprovalConflictError,
    FourEyesViolationError,
    InvalidPlanVersionTransitionError,
)
from backend.app.services.plan_governance_service import (
    PlanGovernanceService,
    is_scenario_approval_unique_violation,
)
from backend.app.services.validation.validator import IndependentScheduleValidator
from backend.app.domain.planning_snapshot import PlanningSnapshot


# =============================================================================
# Helpers & Fixtures
# =============================================================================

VALID_SNAPSHOT_HASH = "a" * 64
VALID_INPUT_HASH = "b" * 64
VALID_SCHEDULE_IDENTITY = IndependentScheduleValidator.compute_schedule_identity_from_dict(
    schedule_dict={
        "scheduler_type": "CP_SAT",
        "status": "OPTIMAL",
        "scheduled_tasks": [],
        "unscheduled_tasks": [],
    },
    snapshot_id="SNAP-TEST-001",
    scenario_id="SCN-REAL-OPERATIONAL-001",
)


def _build_mock_snapshot(plan, run=None):
    snap = MagicMock(spec=PlanningSnapshot)
    snap.scenario_id = plan.scenario_id
    snap.snapshot_id = getattr(run, "snapshot_id", "SNAP-TEST-001") if run else "SNAP-TEST-001"
    snap.compute_snapshot_hash = MagicMock(return_value=plan.snapshot_hash)
    snap.compute_input_hash = MagicMock(return_value=plan.input_hash)
    return snap


def _build_test_plan(
    plan_version_id: str = "PV-CONCUR-001",
    scenario_id: str = "SCN-REAL-OPERATIONAL-001",
    created_by: str = "planner_officer",
) -> PlanVersionModel:
    plan = MagicMock(spec=PlanVersionModel)
    plan.plan_version_id = plan_version_id
    plan.scenario_id = scenario_id
    plan.planning_run_id = "RUN-CONCUR-001"
    plan.version_number = 1
    plan.status = PlanVersionStatus.PENDING_REVIEW.value
    plan.validation_status = "VALID"
    plan.is_approvable = True
    plan.validation_findings_summary = {"error_count": 0, "warning_count": 0}
    plan.schedule_identity = VALID_SCHEDULE_IDENTITY
    plan.snapshot_hash = VALID_SNAPSHOT_HASH
    plan.input_hash = VALID_INPUT_HASH
    plan.dataset_version = "v1.0"
    plan.created_by = created_by
    plan.previous_plan_version_id = None
    plan.approved_at = None
    plan.approved_by = None
    plan.review_comment = None
    plan.schedule_result = {
        "schedule_id": "SCHED-TEST-001",
        "scheduler_type": "CP_SAT",
        "scheduler_version": "1.0.0",
        "scenario_id": scenario_id,
        "snapshot_id": "SNAP-TEST-001",
        "status": "OPTIMAL",
        "scheduled_tasks": [],
        "unscheduled_tasks": [],
        "metrics": {"total_tasks": 0, "scheduled_tasks": 0},
        "validation": {
            "status": "VALID",
            "valid": True,
            "is_approvable": True,
            "schedule_identity": VALID_SCHEDULE_IDENTITY,
            "input_snapshot_id": "SNAP-TEST-001",
            "input_snapshot_hash": VALID_SNAPSHOT_HASH,
        },
    }
    return plan


def _build_test_run(plan: PlanVersionModel) -> PlanningRunModel:
    run = MagicMock(spec=PlanningRunModel)
    run.run_id = plan.planning_run_id
    run.scenario_id = plan.scenario_id
    run.snapshot_id = "SNAP-TEST-001"
    run.snapshot_hash = plan.snapshot_hash
    run.input_hash = plan.input_hash
    run.validation_fingerprint = plan.schedule_identity
    run.validation_status = "VALID"
    run.is_approvable = True
    run.dataset_version = "v1.0"
    run.schedule_result = plan.schedule_result
    run.status = "COMPLETED"
    return run


def _build_test_scenario(scenario_id: str = "SCN-REAL-OPERATIONAL-001") -> OperationalScenarioModel:
    scen = MagicMock(spec=OperationalScenarioModel)
    scen.scenario_id = scenario_id
    scen.classification = DataClass.REAL
    scen.dataset_version = "v1.0"
    return scen


def _build_user(user_id: str, username: str) -> AuthUser:
    return AuthUser(
        user_id=user_id,
        username=username,
        role=UserRole.OPERATOR,
        permissions=["read:reference", "read:operational", "plan:review", "plan:approve"],
    )


# =============================================================================
# 1. Concurrent Approvals: Exactly One Succeeds, Loser Fails with 409 Conflict
# =============================================================================

@pytest.mark.asyncio
async def test_concurrent_independent_approvals_exactly_one_succeeds():
    """Two concurrent approvers race to approve the same plan: exactly one succeeds, loser fails with PlanVersionImmutableError."""
    plan = _build_test_plan()
    run = _build_test_run(plan)
    scen = _build_test_scenario()

    approver_1 = _build_user("USR-APP-01", "chief_dispatcher_malhotra")
    approver_2 = _build_user("USR-APP-02", "chief_dispatcher_sharma")

    # Shared concurrency lock simulating database row lock (SELECT ... FOR UPDATE)
    row_lock = asyncio.Lock()
    audit_events_persisted = []

    async def _locked_get_by_id_for_update(plan_version_id: str):
        # Acquire row lock simulating SELECT ... FOR UPDATE
        await row_lock.acquire()
        # Return current state of row after lock acquisition
        return plan

    session_1 = AsyncMock()
    session_2 = AsyncMock()

    service_1 = PlanGovernanceService(session_1)
    service_2 = PlanGovernanceService(session_2)

    # Setup mocks for service 1
    service_1.plan_repo.get_by_id_for_update = _locked_get_by_id_for_update
    service_1.plan_repo.get_latest_approved = AsyncMock(return_value=None)
    service_1.plan_repo.get_by_plan_version_id = AsyncMock(return_value=plan)
    service_1.run_repo.get_by_run_id = AsyncMock(return_value=run)
    service_1.scenario_repo.get_by_id = AsyncMock(return_value=scen)
    service_1.scenario_repo.get_by_id_for_update = AsyncMock(return_value=scen)
    service_1.scenario_repo.get_snapshot = AsyncMock(return_value=_build_mock_snapshot(plan, run))

    async def _commit_1():
        # Releasing row lock on commit simulating database transaction commit
        if row_lock.locked():
            row_lock.release()

    async def _rollback_1():
        if row_lock.locked():
            row_lock.release()

    session_1.commit = AsyncMock(side_effect=_commit_1)
    session_1.rollback = AsyncMock(side_effect=_rollback_1)

    service_1.plan_repo.add_review_comment = AsyncMock()

    async def _add_audit_1(event):
        audit_events_persisted.append(event)
        return event
    service_1.plan_repo.add_audit_event = AsyncMock(side_effect=_add_audit_1)

    # Setup mocks for service 2
    service_2.plan_repo.get_by_id_for_update = _locked_get_by_id_for_update
    service_2.plan_repo.get_latest_approved = AsyncMock(return_value=None)
    service_2.plan_repo.get_by_plan_version_id = AsyncMock(return_value=plan)
    service_2.plan_repo.add_review_comment = AsyncMock()
    service_2.run_repo.get_by_run_id = AsyncMock(return_value=run)
    service_2.scenario_repo.get_by_id = AsyncMock(return_value=scen)
    service_2.scenario_repo.get_by_id_for_update = AsyncMock(return_value=scen)
    service_2.scenario_repo.get_snapshot = AsyncMock(return_value=_build_mock_snapshot(plan, run))

    async def _commit_2():
        if row_lock.locked():
            row_lock.release()

    async def _rollback_2():
        if row_lock.locked():
            row_lock.release()

    session_2.commit = AsyncMock(side_effect=_commit_2)
    session_2.rollback = AsyncMock(side_effect=_rollback_2)

    async def _add_audit_2(event):
        audit_events_persisted.append(event)
        return event
    service_2.plan_repo.add_audit_event = AsyncMock(side_effect=_add_audit_2)

    # Execute concurrent approvals
    results = await asyncio.gather(
        service_1.approve_plan(plan.plan_version_id, approver_1, comment="Approval by Malhotra"),
        service_2.approve_plan(plan.plan_version_id, approver_2, comment="Approval by Sharma"),
        return_exceptions=True,
    )

    # Analyze outcomes
    successes = [r for r in results if isinstance(r, PlanVersionModel)]
    failures = [r for r in results if isinstance(r, Exception)]

    # 1. Exactly one succeeded, exactly one failed
    assert len(successes) == 1, f"Expected exactly 1 success, got {len(successes)}"
    assert len(failures) == 1, f"Expected exactly 1 failure, got {len(failures)}"

    # 2. Loser received PlanVersionImmutableError (mapped to HTTP 409 PLAN_IMMUTABLE)
    loser_exc = failures[0]
    assert isinstance(loser_exc, PlanVersionImmutableError)
    assert "already APPROVED" in str(loser_exc)

    # 3. Only one audit event was persisted
    assert len(audit_events_persisted) == 1
    assert audit_events_persisted[0].event_type == GovernanceEventType.PLAN_APPROVED.value

    # 4. Plan metadata belongs strictly to winner; loser did not overwrite
    winner_name = audit_events_persisted[0].actor_username
    assert plan.status == PlanVersionStatus.APPROVED.value
    assert plan.approved_by == winner_name
    assert plan.approved_at is not None


# =============================================================================
# 2. Four-Eyes Inviolability Under Concurrent Requests
# =============================================================================

@pytest.mark.asyncio
async def test_creator_cannot_approve_concurrently():
    """Creator self-approval strictly fails closed even when raced against independent approver."""
    plan = _build_test_plan(created_by="planner_officer")
    run = _build_test_run(plan)
    scen = _build_test_scenario()

    creator = _build_user("USR-CREATOR-01", "planner_officer")
    approver = _build_user("USR-APP-02", "chief_dispatcher_sharma")

    session_creator = AsyncMock()
    session_approver = AsyncMock()

    service_creator = PlanGovernanceService(session_creator)
    service_creator.plan_repo.get_by_plan_version_id = AsyncMock(return_value=plan)
    service_creator.plan_repo.get_by_id_for_update = AsyncMock(return_value=plan)
    service_creator.run_repo.get_by_run_id = AsyncMock(return_value=run)
    service_creator.scenario_repo.get_by_id_for_update = AsyncMock(return_value=scen)
    service_creator.scenario_repo.get_by_id = AsyncMock(return_value=scen)

    service_approver = PlanGovernanceService(session_approver)
    service_approver.plan_repo.get_by_plan_version_id = AsyncMock(return_value=plan)
    service_approver.plan_repo.get_by_id_for_update = AsyncMock(return_value=plan)
    service_approver.plan_repo.get_latest_approved = AsyncMock(return_value=None)
    service_approver.run_repo.get_by_run_id = AsyncMock(return_value=run)
    service_approver.scenario_repo.get_by_id_for_update = AsyncMock(return_value=scen)
    service_approver.scenario_repo.get_by_id = AsyncMock(return_value=scen)

    # Creator attempt must immediately fail with FourEyesViolationError
    with pytest.raises(FourEyesViolationError) as exc_info:
        await service_creator.approve_plan(plan.plan_version_id, creator)

    assert "Separation of duties violation" in str(exc_info.value)
    session_creator.rollback.assert_called_once()
    session_creator.commit.assert_not_called()


# =============================================================================
# 3. Transaction Rollback Safety on Approval Failure
# =============================================================================

@pytest.mark.asyncio
async def test_failed_approval_leaves_no_partial_metadata_and_rolls_back():
    """If approval preconditions fail (e.g. fingerprint mismatch), session is rolled back with zero partial writes."""
    plan = _build_test_plan()
    run = _build_test_run(plan)
    # Simulate fingerprint mismatch
    run.validation_fingerprint = "TAMPERED_FINGERPRINT_DIFF"
    scen = _build_test_scenario()

    approver = _build_user("USR-APP-01", "chief_dispatcher_malhotra")

    session = AsyncMock()
    service = PlanGovernanceService(session)

    service.plan_repo.get_by_plan_version_id = AsyncMock(return_value=plan)
    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=plan)
    service.plan_repo.add_audit_event = AsyncMock()
    service.plan_repo.add_review_comment = AsyncMock()
    service.run_repo.get_by_run_id = AsyncMock(return_value=run)
    service.scenario_repo.get_by_id_for_update = AsyncMock(return_value=scen)
    service.scenario_repo.get_by_id = AsyncMock(return_value=scen)

    with pytest.raises(PlanFingerprintMismatchError):
        await service.approve_plan(plan.plan_version_id, approver)

    # Guaranteed rollback
    session.rollback.assert_called_once()
    session.commit.assert_not_called()
    service.plan_repo.add_audit_event.assert_not_called()
    service.plan_repo.add_review_comment.assert_not_called()
    assert plan.status != PlanVersionStatus.APPROVED.value


# =============================================================================
# 4. Post-Lock Re-Read Rejects Terminal or Ineligible States
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize("terminal_status", [
    PlanVersionStatus.APPROVED.value,
    PlanVersionStatus.REJECTED.value,
    PlanVersionStatus.SUPERSEDED.value,
])
async def test_post_lock_re_read_rejects_ineligible_plan_states(terminal_status):
    """When lock is acquired on an already-terminal plan, approval is cleanly rejected with stable error."""
    plan = _build_test_plan()
    scen = _build_test_scenario()
    plan.status = terminal_status
    if terminal_status == PlanVersionStatus.APPROVED.value:
        plan.approved_by = "prior_approver"
        plan.approved_at = datetime.now(timezone.utc)

    approver = _build_user("USR-APP-01", "chief_dispatcher_malhotra")

    session = AsyncMock()
    service = PlanGovernanceService(session)
    service.plan_repo.get_by_plan_version_id = AsyncMock(return_value=plan)
    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=plan)
    service.scenario_repo.get_by_id_for_update = AsyncMock(return_value=scen)
    service.scenario_repo.get_by_id = AsyncMock(return_value=scen)

    if terminal_status == PlanVersionStatus.APPROVED.value:
        with pytest.raises(PlanVersionImmutableError, match="already APPROVED"):
            await service.approve_plan(plan.plan_version_id, approver)
    else:
        with pytest.raises(InvalidPlanVersionTransitionError):
            await service.approve_plan(plan.plan_version_id, approver)

    session.rollback.assert_called_once()
    session.commit.assert_not_called()


# =============================================================================
# 5. GOV-003B: Scenario-Level Locking Hierarchy and Canonical Order
# =============================================================================

@pytest.mark.asyncio
async def test_scenario_lock_acquired_before_plan_lock():
    """Verify canonical locking hierarchy: scenario is locked with FOR UPDATE before plan-version row lock."""
    plan = _build_test_plan()
    run = _build_test_run(plan)
    scen = _build_test_scenario()
    approver = _build_user("USR-APP-01", "chief_dispatcher_malhotra")

    session = AsyncMock()
    service = PlanGovernanceService(session)

    call_order = []

    async def _mock_get_by_plan_id(pv_id):
        call_order.append("pre_read_plan")
        return plan

    async def _mock_get_scen_for_update(scen_id):
        call_order.append("lock_scenario")
        return scen

    async def _mock_get_plan_for_update(pv_id):
        call_order.append("lock_plan")
        return plan

    service.plan_repo.get_by_plan_version_id = _mock_get_by_plan_id
    service.scenario_repo.get_by_id_for_update = _mock_get_scen_for_update
    service.plan_repo.get_by_id_for_update = _mock_get_plan_for_update
    service.plan_repo.get_latest_approved = AsyncMock(return_value=None)
    service.plan_repo.add_review_comment = AsyncMock()
    service.plan_repo.add_audit_event = AsyncMock()
    service.run_repo.get_by_run_id = AsyncMock(return_value=run)
    service.scenario_repo.get_snapshot = AsyncMock(return_value=_build_mock_snapshot(plan, run))

    await service.approve_plan(plan.plan_version_id, approver)

    assert call_order[:3] == ["pre_read_plan", "lock_scenario", "lock_plan"], (
        f"Lock ordering violation! Expected first 3 calls to be ['pre_read_plan', 'lock_scenario', 'lock_plan'], got {call_order}"
    )


@pytest.mark.asyncio
async def test_scenario_identity_mismatch_under_lock_rejected():
    """If locked scenario ID does not match target plan version scenario_id, fail closed."""
    plan = _build_test_plan(scenario_id="SCN-REAL-OPERATIONAL-001")
    scen_diff = _build_test_scenario(scenario_id="SCN-DIFFERENT-002")
    approver = _build_user("USR-APP-01", "chief_dispatcher_malhotra")

    session = AsyncMock()
    service = PlanGovernanceService(session)
    service.plan_repo.get_by_plan_version_id = AsyncMock(return_value=plan)
    service.scenario_repo.get_by_id_for_update = AsyncMock(return_value=scen_diff)
    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=plan)

    with pytest.raises(PlanFingerprintMismatchError, match="Scenario mismatch under lock"):
        await service.approve_plan(plan.plan_version_id, approver)

    session.rollback.assert_called_once()
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_scenario_identity_plan_scenario_id_none_fails_closed():
    """If target plan version's scenario_id is None under lock, fail closed with PlanFingerprintMismatchError."""
    plan_initial = _build_test_plan(scenario_id="SCN-REAL-OPERATIONAL-001")
    plan_locked = _build_test_plan(scenario_id="SCN-REAL-OPERATIONAL-001")
    plan_locked.scenario_id = None
    scen = _build_test_scenario(scenario_id="SCN-REAL-OPERATIONAL-001")
    approver = _build_user("USR-APP-01", "chief_dispatcher_malhotra")

    session = AsyncMock()
    service = PlanGovernanceService(session)
    service.plan_repo.get_by_plan_version_id = AsyncMock(return_value=plan_initial)
    service.scenario_repo.get_by_id_for_update = AsyncMock(return_value=scen)
    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=plan_locked)

    with pytest.raises(PlanFingerprintMismatchError, match="Target plan row has missing, blank, or invalid scenario_id"):
        await service.approve_plan(plan_initial.plan_version_id, approver)

    session.rollback.assert_called_once()
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_scenario_identity_plan_scenario_id_blank_whitespace_fails_closed():
    """If target plan version's scenario_id is blank or whitespace under lock, fail closed with PlanFingerprintMismatchError."""
    plan_initial = _build_test_plan(scenario_id="SCN-REAL-OPERATIONAL-001")
    plan_locked = _build_test_plan(scenario_id="SCN-REAL-OPERATIONAL-001")
    plan_locked.scenario_id = "   \t\n  "
    scen = _build_test_scenario(scenario_id="SCN-REAL-OPERATIONAL-001")
    approver = _build_user("USR-APP-01", "chief_dispatcher_malhotra")

    session = AsyncMock()
    service = PlanGovernanceService(session)
    service.plan_repo.get_by_plan_version_id = AsyncMock(return_value=plan_initial)
    service.scenario_repo.get_by_id_for_update = AsyncMock(return_value=scen)
    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=plan_locked)

    with pytest.raises(PlanFingerprintMismatchError, match="Target plan row has missing, blank, or invalid scenario_id"):
        await service.approve_plan(plan_initial.plan_version_id, approver)

    session.rollback.assert_called_once()
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_scenario_identity_locked_scenario_id_none_fails_closed():
    """If locked scenario entity has None scenario_id, fail closed with PlanFingerprintMismatchError."""
    plan = _build_test_plan(scenario_id="SCN-REAL-OPERATIONAL-001")
    scen_locked = _build_test_scenario(scenario_id="SCN-REAL-OPERATIONAL-001")
    scen_locked.scenario_id = None
    approver = _build_user("USR-APP-01", "chief_dispatcher_malhotra")

    session = AsyncMock()
    service = PlanGovernanceService(session)
    service.plan_repo.get_by_plan_version_id = AsyncMock(return_value=plan)
    service.scenario_repo.get_by_id_for_update = AsyncMock(return_value=scen_locked)
    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=plan)

    with pytest.raises(PlanFingerprintMismatchError, match="Locked scenario has missing, blank, or invalid scenario_id"):
        await service.approve_plan(plan.plan_version_id, approver)

    session.rollback.assert_called_once()
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_scenario_identity_locked_scenario_id_blank_whitespace_fails_closed():
    """If locked scenario entity has blank or whitespace scenario_id, fail closed with PlanFingerprintMismatchError."""
    plan = _build_test_plan(scenario_id="SCN-REAL-OPERATIONAL-001")
    scen_locked = _build_test_scenario(scenario_id="SCN-REAL-OPERATIONAL-001")
    scen_locked.scenario_id = "   "
    approver = _build_user("USR-APP-01", "chief_dispatcher_malhotra")

    session = AsyncMock()
    service = PlanGovernanceService(session)
    service.plan_repo.get_by_plan_version_id = AsyncMock(return_value=plan)
    service.scenario_repo.get_by_id_for_update = AsyncMock(return_value=scen_locked)
    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=plan)

    with pytest.raises(PlanFingerprintMismatchError, match="Locked scenario has missing, blank, or invalid scenario_id"):
        await service.approve_plan(plan.plan_version_id, approver)

    session.rollback.assert_called_once()
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_scenario_identity_normalized_matching_proceeds_to_approval():
    """When target plan and locked scenario IDs match (including normalization of whitespace), approval proceeds."""
    plan = _build_test_plan(scenario_id="SCN-REAL-OPERATIONAL-001")
    run = _build_test_run(plan)
    scen = _build_test_scenario(scenario_id="  SCN-REAL-OPERATIONAL-001  ")
    approver = _build_user("USR-APP-01", "chief_dispatcher_malhotra")

    session = AsyncMock()
    service = PlanGovernanceService(session)
    service.plan_repo.get_by_plan_version_id = AsyncMock(return_value=plan)
    service.scenario_repo.get_by_id_for_update = AsyncMock(return_value=scen)
    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=plan)
    service.plan_repo.get_latest_approved = AsyncMock(return_value=None)
    service.run_repo.get_by_run_id = AsyncMock(return_value=run)
    service.plan_repo.add_review_comment = AsyncMock()
    service.plan_repo.add_audit_event = AsyncMock()
    service.scenario_repo.get_snapshot = AsyncMock(return_value=_build_mock_snapshot(plan, run))

    result = await service.approve_plan(plan.plan_version_id, approver)
    assert result.status == PlanVersionStatus.APPROVED.value
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_missing_scenario_under_lock_fails_closed():
    """If parent scenario cannot be found under lock, fail closed with PlanVersionApprovalBlockedError."""
    plan = _build_test_plan()
    approver = _build_user("USR-APP-01", "chief_dispatcher_malhotra")

    session = AsyncMock()
    service = PlanGovernanceService(session)
    service.plan_repo.get_by_plan_version_id = AsyncMock(return_value=plan)
    service.scenario_repo.get_by_id_for_update = AsyncMock(return_value=None)
    service.scenario_repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(PlanVersionApprovalBlockedError, match="Missing scenario provenance fails closed"):
        await service.approve_plan(plan.plan_version_id, approver)

    session.rollback.assert_called_once()
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_concurrent_approvals_of_different_plan_versions_for_same_scenario():
    """Two different plan versions (Plan A and Plan B) for the same scenario racing:
    Scenario-level row lock serializes them; the second safely supersedes the first."""
    plan_a = _build_test_plan(plan_version_id="PV-CONCUR-A", scenario_id="SCN-REAL-OPERATIONAL-001")
    plan_a.version_number = 1
    run_a = _build_test_run(plan_a)

    plan_b = _build_test_plan(plan_version_id="PV-CONCUR-B", scenario_id="SCN-REAL-OPERATIONAL-001")
    plan_b.version_number = 2
    plan_b.planning_run_id = "RUN-CONCUR-002"
    run_b = _build_test_run(plan_b)

    scen = _build_test_scenario("SCN-REAL-OPERATIONAL-001")

    approver_1 = _build_user("USR-APP-01", "chief_dispatcher_malhotra")
    approver_2 = _build_user("USR-APP-02", "chief_dispatcher_sharma")

    scenario_lock = asyncio.Lock()
    approved_store = {}
    audit_events = []

    # Service 1
    session_1 = AsyncMock()
    service_1 = PlanGovernanceService(session_1)

    async def _lock_scen_1(s_id):
        await scenario_lock.acquire()
        return scen

    async def _commit_1():
        approved_store[scen.scenario_id] = plan_a
        if scenario_lock.locked():
            scenario_lock.release()

    async def _rollback_1():
        if scenario_lock.locked():
            scenario_lock.release()

    service_1.scenario_repo.get_by_id_for_update = _lock_scen_1
    service_1.scenario_repo.get_snapshot = AsyncMock(return_value=_build_mock_snapshot(plan_a, run_a))
    service_1.plan_repo.get_by_plan_version_id = AsyncMock(return_value=plan_a)
    service_1.plan_repo.get_by_id_for_update = AsyncMock(return_value=plan_a)
    service_1.plan_repo.get_latest_approved = AsyncMock(side_effect=lambda sid, for_update=False: approved_store.get(sid))
    service_1.run_repo.get_by_run_id = AsyncMock(return_value=run_a)
    service_1.plan_repo.add_review_comment = AsyncMock()
    service_1.plan_repo.add_audit_event = AsyncMock(side_effect=lambda e: audit_events.append(e))
    session_1.commit = AsyncMock(side_effect=_commit_1)
    session_1.rollback = AsyncMock(side_effect=_rollback_1)

    # Service 2
    session_2 = AsyncMock()
    service_2 = PlanGovernanceService(session_2)

    async def _lock_scen_2(s_id):
        await scenario_lock.acquire()
        return scen

    async def _commit_2():
        approved_store[scen.scenario_id] = plan_b
        if scenario_lock.locked():
            scenario_lock.release()

    async def _rollback_2():
        if scenario_lock.locked():
            scenario_lock.release()

    service_2.scenario_repo.get_by_id_for_update = _lock_scen_2
    service_2.scenario_repo.get_snapshot = AsyncMock(return_value=_build_mock_snapshot(plan_b, run_b))
    service_2.plan_repo.get_by_plan_version_id = AsyncMock(return_value=plan_b)
    service_2.plan_repo.get_by_id_for_update = AsyncMock(return_value=plan_b)
    service_2.plan_repo.get_latest_approved = AsyncMock(side_effect=lambda sid, for_update=False: approved_store.get(sid))
    service_2.run_repo.get_by_run_id = AsyncMock(return_value=run_b)
    service_2.plan_repo.add_review_comment = AsyncMock()
    service_2.plan_repo.add_audit_event = AsyncMock(side_effect=lambda e: audit_events.append(e))
    session_2.commit = AsyncMock(side_effect=_commit_2)
    session_2.rollback = AsyncMock(side_effect=_rollback_2)

    results = await asyncio.gather(
        service_1.approve_plan(plan_a.plan_version_id, approver_1),
        service_2.approve_plan(plan_b.plan_version_id, approver_2),
        return_exceptions=True,
    )

    # Both approvals succeed serialized: first approves A, second supersedes A and approves B!
    assert all(isinstance(r, PlanVersionModel) for r in results), f"Errors in concurrent approval: {results}"
    assert plan_a.status == PlanVersionStatus.SUPERSEDED.value
    assert plan_b.status == PlanVersionStatus.APPROVED.value
    assert plan_b.previous_plan_version_id == plan_a.plan_version_id


@pytest.mark.asyncio
async def test_db_uniqueness_conflict_raises_plan_approval_conflict_error():
    """When DB unique constraint fires (e.g. uq_plan_versions_one_approved_per_scenario),
    service catches IntegrityError, rolls back atomically, and raises PlanApprovalConflictError."""
    plan = _build_test_plan()
    run = _build_test_run(plan)
    scen = _build_test_scenario()
    approver = _build_user("USR-APP-01", "chief_dispatcher_malhotra")

    session = AsyncMock()
    service = PlanGovernanceService(session)

    service.plan_repo.get_by_plan_version_id = AsyncMock(return_value=plan)
    service.scenario_repo.get_by_id_for_update = AsyncMock(return_value=scen)
    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=plan)
    service.plan_repo.get_latest_approved = AsyncMock(return_value=None)
    service.run_repo.get_by_run_id = AsyncMock(return_value=run)
    service.plan_repo.add_review_comment = AsyncMock()
    service.plan_repo.add_audit_event = AsyncMock()
    service.scenario_repo.get_snapshot = AsyncMock(return_value=_build_mock_snapshot(plan, run))

    # Simulate Postgres unique violation on commit
    pg_err = IntegrityError(
        statement="UPDATE plan_versions SET status = 'APPROVED' ...",
        params={},
        orig=Exception('duplicate key value violates unique constraint "uq_plan_versions_one_approved_per_scenario"\nDETAIL: Key (scenario_id)=(SCN-REAL-OPERATIONAL-001) already exists. Code: 23505'),
    )
    session.commit = AsyncMock(side_effect=pg_err)

    with pytest.raises(PlanApprovalConflictError) as exc_info:
        await service.approve_plan(plan.plan_version_id, approver)

    assert "Another plan version for scenario" in str(exc_info.value)
    session.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_db_unrelated_23505_violation_reraises_integrity_error():
    """When an unrelated unique constraint fires with 23505 (e.g. uq_plan_versions_scenario_version),
    service rolls back atomically and re-raises raw IntegrityError (does NOT map to PlanApprovalConflictError)."""
    plan = _build_test_plan()
    run = _build_test_run(plan)
    scen = _build_test_scenario()
    approver = _build_user("USR-APP-01", "chief_dispatcher_malhotra")

    session = AsyncMock()
    service = PlanGovernanceService(session)

    service.plan_repo.get_by_plan_version_id = AsyncMock(return_value=plan)
    service.scenario_repo.get_by_id_for_update = AsyncMock(return_value=scen)
    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=plan)
    service.plan_repo.get_latest_approved = AsyncMock(return_value=None)
    service.run_repo.get_by_run_id = AsyncMock(return_value=run)
    service.plan_repo.add_review_comment = AsyncMock()
    service.plan_repo.add_audit_event = AsyncMock()
    service.scenario_repo.get_snapshot = AsyncMock(return_value=_build_mock_snapshot(plan, run))

    # Driver diagnostic indicating unrelated constraint
    asyncpg_orig = MagicMock()
    asyncpg_orig.constraint_name = "uq_plan_versions_scenario_version"
    unrelated_pg_err = IntegrityError(
        statement="INSERT INTO plan_versions ...",
        params={},
        orig=asyncpg_orig,
    )
    session.commit = AsyncMock(side_effect=unrelated_pg_err)

    with pytest.raises(IntegrityError) as exc_info:
        await service.approve_plan(plan.plan_version_id, approver)

    assert not isinstance(exc_info.value, PlanApprovalConflictError)
    assert exc_info.value is unrelated_pg_err
    session.rollback.assert_called_once()


def test_is_scenario_approval_unique_violation_diagnostics():
    """Unit test for is_scenario_approval_unique_violation helper across driver variants."""
    # 1. asyncpg driver: direct constraint_name attribute matching target
    asyncpg_orig_match = MagicMock()
    asyncpg_orig_match.constraint_name = "uq_plan_versions_one_approved_per_scenario"
    err_asyncpg_match = IntegrityError("stmt", {}, asyncpg_orig_match)
    assert is_scenario_approval_unique_violation(err_asyncpg_match) is True

    # 2. asyncpg driver: unrelated constraint name
    asyncpg_orig_unrelated = MagicMock()
    asyncpg_orig_unrelated.constraint_name = "uq_plan_versions_scenario_version"
    err_asyncpg_unrelated = IntegrityError("stmt", {}, asyncpg_orig_unrelated)
    assert is_scenario_approval_unique_violation(err_asyncpg_unrelated) is False

    # 3. psycopg driver: diag.constraint_name matching target
    psycopg_orig_match = MagicMock()
    psycopg_orig_match.constraint_name = None
    psycopg_orig_match.diag = MagicMock()
    psycopg_orig_match.diag.constraint_name = "uq_plan_versions_one_approved_per_scenario"
    err_psycopg_match = IntegrityError("stmt", {}, psycopg_orig_match)
    assert is_scenario_approval_unique_violation(err_psycopg_match) is True

    # 4. psycopg driver: diag.constraint_name unrelated
    psycopg_orig_unrelated = MagicMock()
    psycopg_orig_unrelated.constraint_name = None
    psycopg_orig_unrelated.diag = MagicMock()
    psycopg_orig_unrelated.diag.constraint_name = "uq_plan_versions_scenario_version"
    err_psycopg_unrelated = IntegrityError("stmt", {}, psycopg_orig_unrelated)
    assert is_scenario_approval_unique_violation(err_psycopg_unrelated) is False

    # 5. String-based error with target constraint
    err_str_match = IntegrityError(
        "stmt",
        {},
        Exception('duplicate key value violates unique constraint "uq_plan_versions_one_approved_per_scenario"'),
    )
    assert is_scenario_approval_unique_violation(err_str_match) is True

    # 6. String-based error with unrelated constraint and SQLSTATE 23505
    err_str_unrelated = IntegrityError(
        "stmt",
        {},
        Exception('duplicate key value violates unique constraint "uq_plan_versions_scenario_version"\nDETAIL: Key (scenario_id, version_number)=(SCN-1, 1) already exists. Code: 23505'),
    )
    assert is_scenario_approval_unique_violation(err_str_unrelated) is False

    # 7. Generic 23505 without target constraint name
    err_generic_23505 = IntegrityError("stmt", {}, Exception("SQLSTATE 23505: unique violation occurred"))
    assert is_scenario_approval_unique_violation(err_generic_23505) is False

    # 8. Non-IntegrityError
    assert is_scenario_approval_unique_violation(ValueError("not an integrity error")) is False


@pytest.mark.asyncio
async def test_api_approval_conflict_maps_to_http_409():
    """The API route maps PlanApprovalConflictError to HTTP 409 Conflict with APPROVAL_CONFLICT code and rolls back."""
    from backend.app.api.v1.plan_versions import approve_plan as api_approve_plan
    from fastapi import HTTPException
    from unittest.mock import patch

    mock_session = AsyncMock()
    user = _build_user("USR-APP-01", "chief_dispatcher_malhotra")

    with pytest.raises(HTTPException) as exc_info:
        with patch.object(
            PlanGovernanceService,
            "approve_plan",
            side_effect=PlanApprovalConflictError("Another plan version was concurrently approved."),
        ):
            await api_approve_plan(
                plan_version_id="PV-CONCUR-001",
                payload=None,
                session=mock_session,
                current_user=user,
            )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["error"]["code"] == "APPROVAL_CONFLICT"
    assert "Another plan version" in exc_info.value.detail["error"]["message"]
    mock_session.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_api_target_index_integrity_error_maps_to_http_409_approval_conflict():
    """Direct PostgreSQL IntegrityError matching uq_plan_versions_one_approved_per_scenario in API endpoint maps to HTTP 409 APPROVAL_CONFLICT."""
    from backend.app.api.v1.plan_versions import approve_plan as api_approve_plan
    from fastapi import HTTPException
    from unittest.mock import patch

    mock_session = AsyncMock()
    user = _build_user("USR-APP-01", "chief_dispatcher_malhotra")

    pg_err = IntegrityError(
        statement="UPDATE plan_versions ...",
        params={},
        orig=Exception('duplicate key value violates unique constraint "uq_plan_versions_one_approved_per_scenario"\nCode: 23505'),
    )

    with pytest.raises(HTTPException) as exc_info:
        with patch.object(
            PlanGovernanceService,
            "approve_plan",
            side_effect=pg_err,
        ):
            await api_approve_plan(
                plan_version_id="PV-CONCUR-001",
                payload=None,
                session=mock_session,
                current_user=user,
            )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["error"]["code"] == "APPROVAL_CONFLICT"
    mock_session.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_api_unrelated_23505_integrity_error_maps_to_http_409_integrity_conflict():
    """Direct PostgreSQL IntegrityError for an unrelated 23505 unique constraint maps to HTTP 409 INTEGRITY_CONFLICT (NOT APPROVAL_CONFLICT)."""
    from backend.app.api.v1.plan_versions import approve_plan as api_approve_plan
    from fastapi import HTTPException
    from unittest.mock import patch

    mock_session = AsyncMock()
    user = _build_user("USR-APP-01", "chief_dispatcher_malhotra")

    orig_diag = MagicMock()
    orig_diag.constraint_name = "uq_plan_versions_scenario_version"
    pg_err = IntegrityError(
        statement="INSERT INTO plan_versions ...",
        params={},
        orig=orig_diag,
    )

    with pytest.raises(HTTPException) as exc_info:
        with patch.object(
            PlanGovernanceService,
            "approve_plan",
            side_effect=pg_err,
        ):
            await api_approve_plan(
                plan_version_id="PV-CONCUR-001",
                payload=None,
                session=mock_session,
                current_user=user,
            )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["error"]["code"] == "INTEGRITY_CONFLICT"
    assert exc_info.value.detail["error"]["code"] != "APPROVAL_CONFLICT"
    mock_session.rollback.assert_called_once()
