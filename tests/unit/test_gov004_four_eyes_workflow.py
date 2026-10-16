"""Unit tests for Four-Eyes Governance, Reviewer Independence, and State Transitions (F4 / GOV-004).

Safety & Governance Invariants:
1. COMPLETED != APPROVED (Solver completion never implies operational approval).
2. Four-Eyes separation of duties: Author/creator strictly forbidden from approving own plan candidate.
3. Reviewer independence: Author/creator strictly forbidden from reviewing own plan candidate.
4. Fail-closed actor provenance: Missing, blank, or invalid creator or approver/reviewer identities fail closed.
5. Client-supplied metadata independence: `declared_reviewer_name` and `declared_reviewer_role` are non-authoritative
   audit notes and cannot satisfy Four-Eyes or override server-side authenticated identities.
6. State machine integrity: Only legal lifecycle transitions are permitted (PENDING_REVIEW -> APPROVED is valid).
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from backend.app.core.auth import AuthUser, UserRole
from backend.app.schemas.plan_version import (
    PlanVersionStatus,
    GovernanceEventType,
    PlanReviewAction,
)
from backend.app.db.models.plan_version import (
    PlanVersionModel,
    GovernanceAuditEventModel,
)
from backend.app.db.models.planning_run import PlanningRunModel
from backend.app.db.models.scenario import OperationalScenarioModel
from backend.app.domain.enums import DataClass
from backend.app.domain.planning_snapshot import PlanningSnapshot
from backend.app.repositories.plan_version_repo import (
    FourEyesViolationError,
    PlanVersionImmutableError,
    InvalidPlanVersionTransitionError,
    PlanVersionApprovalBlockedError,
)
from backend.app.services.plan_governance_service import PlanGovernanceService


# Canonical test hashes
VALID_SNAPSHOT_HASH = "a" * 64
VALID_INPUT_HASH = "b" * 64
VALID_SCHEDULE_IDENTITY = "c" * 64


def _build_test_plan(
    plan_version_id: str = "PV-TEST-001",
    scenario_id: str = "SCN-REAL-OPERATIONAL-001",
    planning_run_id: str = "RUN-TEST-001",
    status: str = PlanVersionStatus.PENDING_REVIEW.value,
    created_by: str = "planner_officer",
    reviewed_by: str = None,
    approved_by: str = None,
    dataset_version: str = "v1.0",
) -> PlanVersionModel:
    plan = MagicMock(spec=PlanVersionModel)
    plan.plan_version_id = plan_version_id
    plan.scenario_id = scenario_id
    plan.planning_run_id = planning_run_id
    plan.version_number = 1
    plan.status = status
    plan.created_by = created_by
    plan.reviewed_by = reviewed_by
    plan.approved_by = approved_by
    plan.dataset_version = dataset_version
    plan.validation_status = "VALID"
    plan.is_approvable = True
    plan.validation_findings_summary = {"error_count": 0}
    plan.schedule_identity = VALID_SCHEDULE_IDENTITY
    plan.snapshot_hash = VALID_SNAPSHOT_HASH
    plan.input_hash = VALID_INPUT_HASH
    plan.scheduler_type = "CP_SAT"
    plan.previous_plan_version_id = None
    plan.schedule_result = {
        "schedule_id": "SCH-TEST-01",
        "scenario_id": scenario_id,
        "snapshot_id": "SNAP-TEST-001",
        "status": "OPTIMAL",
        "validation": {
            "status": "VALID",
            "is_approvable": True,
            "schedule_identity": VALID_SCHEDULE_IDENTITY,
        },
    }
    return plan


def _build_test_run(
    plan: PlanVersionModel,
    snapshot_id: str = "SNAP-TEST-001",
) -> PlanningRunModel:
    run = MagicMock(spec=PlanningRunModel)
    run.run_id = plan.planning_run_id
    run.scenario_id = plan.scenario_id
    run.snapshot_id = snapshot_id
    run.snapshot_hash = plan.snapshot_hash
    run.input_hash = plan.input_hash
    run.validation_fingerprint = plan.schedule_identity
    run.validation_status = "VALID"
    run.is_approvable = True
    run.dataset_version = plan.dataset_version
    run.schedule_result = plan.schedule_result
    run.status = "COMPLETED"
    return run


def _build_test_scenario(
    scenario_id: str = "SCN-REAL-OPERATIONAL-001",
    classification: DataClass = DataClass.REAL,
    dataset_version: str = "v1.0",
) -> OperationalScenarioModel:
    scen = MagicMock(spec=OperationalScenarioModel)
    scen.scenario_id = scenario_id
    scen.classification = classification
    scen.dataset_version = dataset_version
    return scen


def _configure_mocks(
    service: PlanGovernanceService,
    plan: PlanVersionModel,
    run: PlanningRunModel = None,
    scenario: OperationalScenarioModel = None,
) -> None:
    if run is None:
        run = _build_test_run(plan)
    if scenario is None:
        scenario = _build_test_scenario(plan.scenario_id)

    service.plan_repo.get_by_plan_version_id = AsyncMock(return_value=plan)
    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=plan)
    service.run_repo.get_by_run_id = AsyncMock(return_value=run)
    service.scenario_repo.get_by_id_for_update = AsyncMock(return_value=scenario)
    service.scenario_repo.get_by_id = AsyncMock(return_value=scenario)
    service.plan_repo.get_latest_approved = AsyncMock(return_value=None)
    service.plan_repo.add_review_comment = AsyncMock()
    service.plan_repo.add_audit_event = AsyncMock()

    snap = MagicMock(spec=PlanningSnapshot)
    snap.scenario_id = plan.scenario_id
    snap.snapshot_id = getattr(run, "snapshot_id", "SNAP-TEST-001")
    snap.compute_snapshot_hash = MagicMock(return_value=plan.snapshot_hash)
    snap.compute_input_hash = MagicMock(return_value=plan.input_hash)
    service.scenario_repo.get_snapshot = AsyncMock(return_value=snap)


def _make_actor(username: str, user_id: str = None, role: UserRole = UserRole.OPERATOR) -> AuthUser:
    return AuthUser(
        user_id=user_id or f"USR-{username.upper()}-01",
        username=username,
        role=role,
        permissions=["read:reference", "read:operational", "plan:review", "plan:approve", "plan:reject"],
    )


# =============================================================================
# 1. PROHIBITED SELF-APPROVAL TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_f4_exact_match_self_approval_strictly_blocked():
    """Author cannot approve their own plan when username matches exactly."""
    service = PlanGovernanceService(AsyncMock())
    plan = _build_test_plan(created_by="planner_officer")
    _configure_mocks(service, plan)

    creator_actor = _make_actor(username="planner_officer")
    with pytest.raises(FourEyesViolationError, match="Separation of duties violation"):
        await service.approve_plan(plan.plan_version_id, creator_actor)


@pytest.mark.asyncio
async def test_f4_case_insensitive_self_approval_strictly_blocked():
    """Author cannot bypass Four-Eyes using alternate case casing in username."""
    service = PlanGovernanceService(AsyncMock())
    plan = _build_test_plan(created_by="Planner_Officer")
    _configure_mocks(service, plan)

    cased_actor = _make_actor(username="planner_officer")
    with pytest.raises(FourEyesViolationError, match="Separation of duties violation"):
        await service.approve_plan(plan.plan_version_id, cased_actor)


@pytest.mark.asyncio
async def test_f4_whitespace_padded_self_approval_strictly_blocked():
    """Author cannot bypass Four-Eyes using whitespace in username."""
    service = PlanGovernanceService(AsyncMock())
    plan = _build_test_plan(created_by="  planner_officer  ")
    _configure_mocks(service, plan)

    actor = _make_actor(username="planner_officer")
    with pytest.raises(FourEyesViolationError, match="Separation of duties violation"):
        await service.approve_plan(plan.plan_version_id, actor)


@pytest.mark.asyncio
async def test_f4_user_id_match_self_approval_strictly_blocked():
    """Author cannot bypass Four-Eyes when actor.user_id matches plan.created_by."""
    service = PlanGovernanceService(AsyncMock())
    plan = _build_test_plan(created_by="USR-PLANNER-99")
    _configure_mocks(service, plan)

    actor_diff_username_same_id = _make_actor(username="alias_user", user_id="USR-PLANNER-99")
    with pytest.raises(FourEyesViolationError, match="Separation of duties violation"):
        await service.approve_plan(plan.plan_version_id, actor_diff_username_same_id)


@pytest.mark.asyncio
async def test_f4_creator_cannot_bypass_self_approval_via_declared_reviewer_metadata():
    """Creator supplying a third-party declared_reviewer_name CANNOT bypass Four-Eyes check."""
    service = PlanGovernanceService(AsyncMock())
    plan = _build_test_plan(created_by="planner_officer")
    _configure_mocks(service, plan)

    creator_actor = _make_actor(username="planner_officer")
    with pytest.raises(FourEyesViolationError, match="Separation of duties violation"):
        await service.approve_plan(
            plan.plan_version_id,
            creator_actor,
            declared_reviewer_name="Shri V. K. Malhotra",
            declared_reviewer_role="Chief Operations Manager",
        )


# =============================================================================
# 2. MISMATCHED OR MISSING IDENTITY (FAIL-CLOSED) TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_f4_missing_creator_provenance_fails_closed():
    """Plan row with None as created_by fails closed under Four-Eyes check."""
    service = PlanGovernanceService(AsyncMock())
    plan = _build_test_plan(created_by=None)
    _configure_mocks(service, plan)

    approver = _make_actor(username="independent_approver")
    with pytest.raises(FourEyesViolationError, match="missing, blank, or invalid creator provenance"):
        await service.approve_plan(plan.plan_version_id, approver)


@pytest.mark.asyncio
async def test_f4_blank_creator_provenance_fails_closed():
    """Plan row with empty/blank whitespace created_by fails closed under Four-Eyes check."""
    service = PlanGovernanceService(AsyncMock())
    plan = _build_test_plan(created_by="   ")
    _configure_mocks(service, plan)

    approver = _make_actor(username="independent_approver")
    with pytest.raises(FourEyesViolationError, match="missing, blank, or invalid creator provenance"):
        await service.approve_plan(plan.plan_version_id, approver)


@pytest.mark.asyncio
async def test_f4_missing_approver_identity_fails_closed():
    """Approver AuthUser with missing/blank username fails closed."""
    service = PlanGovernanceService(AsyncMock())
    plan = _build_test_plan(created_by="planner_officer")
    _configure_mocks(service, plan)

    invalid_approver = _make_actor(username="   ")
    with pytest.raises(FourEyesViolationError, match="missing, blank, or invalid actor identity"):
        await service.approve_plan(plan.plan_version_id, invalid_approver)


@pytest.mark.asyncio
async def test_f4_creator_cannot_review_own_plan_candidate():
    """Creator attempting to call start_review is strictly blocked by Four-Eyes."""
    service = PlanGovernanceService(AsyncMock())
    plan = _build_test_plan(created_by="planner_officer")
    _configure_mocks(service, plan)

    creator_actor = _make_actor(username="planner_officer")
    with pytest.raises(FourEyesViolationError, match="Author 'planner_officer' cannot review their own plan version"):
        await service.start_review(plan.plan_version_id, creator_actor)


@pytest.mark.asyncio
async def test_f4_start_review_missing_creator_fails_closed():
    """start_review fails closed if plan.created_by is missing/blank."""
    service = PlanGovernanceService(AsyncMock())
    plan = _build_test_plan(created_by="")
    _configure_mocks(service, plan)

    reviewer = _make_actor(username="independent_reviewer")
    with pytest.raises(FourEyesViolationError, match="missing, blank, or invalid creator provenance"):
        await service.start_review(plan.plan_version_id, reviewer)


@pytest.mark.asyncio
async def test_f4_start_review_missing_reviewer_identity_fails_closed():
    """start_review fails closed if reviewer actor has blank username."""
    service = PlanGovernanceService(AsyncMock())
    plan = _build_test_plan(created_by="planner_officer")
    _configure_mocks(service, plan)

    blank_actor = _make_actor(username="  ")
    with pytest.raises(FourEyesViolationError, match="missing, blank, or invalid actor identity"):
        await service.start_review(plan.plan_version_id, blank_actor)


@pytest.mark.asyncio
async def test_f4_plan_reviewed_by_author_blocks_approval():
    """If plan was previously put under review by its author, approval is blocked."""
    service = PlanGovernanceService(AsyncMock())
    # Corrupted / tampered state: author reviewed their own plan
    plan = _build_test_plan(created_by="planner_officer", reviewed_by="planner_officer")
    _configure_mocks(service, plan)

    approver = _make_actor(username="independent_approver")
    with pytest.raises(FourEyesViolationError, match="was reviewed by its author 'planner_officer'"):
        await service.approve_plan(plan.plan_version_id, approver)


# =============================================================================
# 3. UNAUTHORIZED STATE TRANSITIONS
# =============================================================================

@pytest.mark.asyncio
async def test_f4_rejected_plan_cannot_be_approved():
    """A REJECTED plan version cannot be transitioned to APPROVED."""
    service = PlanGovernanceService(AsyncMock())
    plan = _build_test_plan(status=PlanVersionStatus.REJECTED.value)
    _configure_mocks(service, plan)

    approver = _make_actor(username="independent_approver")
    with pytest.raises(InvalidPlanVersionTransitionError):
        await service.approve_plan(plan.plan_version_id, approver)


@pytest.mark.asyncio
async def test_f4_superseded_plan_cannot_be_approved():
    """A SUPERSEDED plan version cannot be transitioned to APPROVED."""
    service = PlanGovernanceService(AsyncMock())
    plan = _build_test_plan(status=PlanVersionStatus.SUPERSEDED.value)
    _configure_mocks(service, plan)

    approver = _make_actor(username="independent_approver")
    with pytest.raises(InvalidPlanVersionTransitionError):
        await service.approve_plan(plan.plan_version_id, approver)


@pytest.mark.asyncio
async def test_f4_approved_plan_cannot_be_reapproved():
    """An already APPROVED plan version cannot be re-approved (immutable)."""
    service = PlanGovernanceService(AsyncMock())
    plan = _build_test_plan(status=PlanVersionStatus.APPROVED.value, approved_by="prior_approver")
    _configure_mocks(service, plan)

    approver = _make_actor(username="independent_approver")
    with pytest.raises(PlanVersionImmutableError, match="is already APPROVED"):
        await service.approve_plan(plan.plan_version_id, approver)


@pytest.mark.asyncio
async def test_f4_approved_plan_cannot_be_rejected():
    """An APPROVED plan version cannot be rejected retroactively."""
    service = PlanGovernanceService(AsyncMock())
    plan = _build_test_plan(status=PlanVersionStatus.APPROVED.value)
    _configure_mocks(service, plan)

    actor = _make_actor(username="independent_approver")
    with pytest.raises(PlanVersionImmutableError, match="Approved PlanVersion.*cannot be rejected"):
        await service.reject_plan(plan.plan_version_id, actor, reason="Unsafe track detected.")


@pytest.mark.asyncio
async def test_f4_rejected_plan_cannot_enter_review():
    """A REJECTED plan version cannot transition to UNDER_REVIEW."""
    service = PlanGovernanceService(AsyncMock())
    plan = _build_test_plan(status=PlanVersionStatus.REJECTED.value)
    _configure_mocks(service, plan)

    reviewer = _make_actor(username="independent_reviewer")
    with pytest.raises(InvalidPlanVersionTransitionError):
        await service.start_review(plan.plan_version_id, reviewer)


@pytest.mark.asyncio
async def test_f4_superseded_plan_cannot_enter_review():
    """A SUPERSEDED plan version cannot transition to UNDER_REVIEW."""
    service = PlanGovernanceService(AsyncMock())
    plan = _build_test_plan(status=PlanVersionStatus.SUPERSEDED.value)
    _configure_mocks(service, plan)

    reviewer = _make_actor(username="independent_reviewer")
    with pytest.raises(InvalidPlanVersionTransitionError):
        await service.start_review(plan.plan_version_id, reviewer)


# =============================================================================
# 4. LEGITIMATE APPROVAL PATHS
# =============================================================================

@pytest.mark.asyncio
async def test_f4_legitimate_direct_approval_succeeds():
    """Independent authorized approver can directly approve candidate from PENDING_REVIEW."""
    service = PlanGovernanceService(AsyncMock())
    plan = _build_test_plan(
        status=PlanVersionStatus.PENDING_REVIEW.value,
        created_by="planner_user",
    )
    _configure_mocks(service, plan)

    approver = _make_actor(username="divisional_operations_manager")
    approved = await service.approve_plan(
        plan.plan_version_id,
        approver,
        comment="Corridor blocks authorized under statutory regulations.",
    )

    assert approved.status == PlanVersionStatus.APPROVED.value
    assert approved.approved_by == approver.username
    assert approved.reviewed_by is None  # Direct approval without intermediate review

    # Audit event must capture authoritative actor
    audit_call = service.plan_repo.add_audit_event.call_args[0][0]
    assert audit_call.actor_username == approver.username
    assert audit_call.actor_id == approver.user_id
    assert audit_call.actor_role == approver.role.value


@pytest.mark.asyncio
async def test_f4_legitimate_two_step_review_approval_succeeds():
    """Legitimate workflow: Independent reviewer starts review, independent approver approves."""
    service = PlanGovernanceService(AsyncMock())
    plan = _build_test_plan(
        status=PlanVersionStatus.PENDING_REVIEW.value,
        created_by="planner_user",
    )
    _configure_mocks(service, plan)

    # Step 1: Independent reviewer starts review
    reviewer = _make_actor(username="safety_officer_verma")
    under_review = await service.start_review(
        plan.plan_version_id,
        reviewer,
        comment="Commencing independent safety spacing audit.",
    )
    assert under_review.status == PlanVersionStatus.UNDER_REVIEW.value
    assert under_review.reviewed_by == reviewer.username

    # Step 2: Independent approver approves plan
    approver = _make_actor(username="divisional_operations_manager")
    approved = await service.approve_plan(
        plan.plan_version_id,
        approver,
        comment="Safety clearance confirmed; operational schedule approved.",
    )
    assert approved.status == PlanVersionStatus.APPROVED.value
    assert approved.approved_by == approver.username
    assert approved.reviewed_by == reviewer.username


@pytest.mark.asyncio
async def test_f4_declared_reviewer_metadata_preserved_without_overwriting_authoritative_actor():
    """Free-text declared_reviewer_name is recorded in metadata but does NOT overwrite plan.approved_by."""
    service = PlanGovernanceService(AsyncMock())
    plan = _build_test_plan(created_by="planner_user")
    _configure_mocks(service, plan)

    approver = _make_actor(username="divisional_operations_manager")
    approved = await service.approve_plan(
        plan.plan_version_id,
        approver,
        comment="Authorized.",
        declared_reviewer_name="Shri V. K. Malhotra",
        declared_reviewer_role="Chief Operations Manager",
    )

    # Core invariant: Server authenticated identity is authoritative
    assert approved.approved_by == "divisional_operations_manager"
    assert approved.approved_by != "Shri V. K. Malhotra"

    # Audit event captures declared metadata
    audit_call = service.plan_repo.add_audit_event.call_args[0][0]
    assert audit_call.actor_username == "divisional_operations_manager"
    assert audit_call.event_metadata["declared_reviewer"]["name"] == "Shri V. K. Malhotra"
    assert audit_call.event_metadata["declared_reviewer"]["role"] == "Chief Operations Manager"


@pytest.mark.asyncio
async def test_f4_creator_can_reject_own_plan():
    """Creator IS permitted to reject/withdraw their own plan version for rework."""
    service = PlanGovernanceService(AsyncMock())
    plan = _build_test_plan(created_by="planner_user")
    _configure_mocks(service, plan)

    creator_actor = _make_actor(username="planner_user")
    rejected = await service.reject_plan(
        plan.plan_version_id,
        creator_actor,
        reason="Self-identified track conflict during review — withdrawing.",
    )

    assert rejected.status == PlanVersionStatus.REJECTED.value
    assert rejected.rejected_by == creator_actor.username
