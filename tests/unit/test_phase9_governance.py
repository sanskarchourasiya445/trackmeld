"""Unit tests for Phase 9: Plan Versions, Human Review, Approval Gating, and Audit Invariants."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from pydantic import ValidationError

from backend.app.schemas.plan_version import (
    PlanVersionStatus,
    PlanReviewAction,
    GovernanceEventType,
    RejectPlanRequest,
    AddReviewCommentRequest,
    CreatePlanVersionRequest,
    ApprovePlanRequest,
)
from backend.app.repositories.plan_version_repo import (
    PlanVersionRepository,
    InvalidPlanVersionTransitionError,
    PlanVersionApprovalBlockedError,
    PlanFingerprintMismatchError,
    PlanVersionImmutableError,
    PlanVersionAlreadyExistsError,
    LEGAL_PLAN_TRANSITIONS,
)
from backend.app.core.auth import KNOWN_CREDENTIALS, AuthUser, UserRole
from backend.app.db.models.planning_run import PlanningRunModel
from backend.app.db.models.plan_version import PlanVersionModel
from backend.app.services.plan_governance_service import PlanGovernanceService


# =============================================================================
# 1. ENUMS AND SCHEMAS
# =============================================================================

def test_governance_enums():
    """Verify state machine status and audit event categories."""
    assert PlanVersionStatus.PENDING_REVIEW == "PENDING_REVIEW"
    assert PlanVersionStatus.UNDER_REVIEW == "UNDER_REVIEW"
    assert PlanVersionStatus.APPROVED == "APPROVED"
    assert PlanVersionStatus.REJECTED == "REJECTED"
    assert PlanVersionStatus.SUPERSEDED == "SUPERSEDED"

    assert GovernanceEventType.PLAN_VERSION_CREATED == "PLAN_VERSION_CREATED"
    assert GovernanceEventType.PLAN_APPROVED == "PLAN_APPROVED"
    assert GovernanceEventType.PLAN_REJECTED == "PLAN_REJECTED"
    assert GovernanceEventType.PLAN_SUPERSEDED == "PLAN_SUPERSEDED"


def test_reject_request_validation():
    """Rejection requires a substantive reason (>= 5 chars)."""
    # Valid reason
    req = RejectPlanRequest(reason="Maintenance conflicts with Vande Bharat corridor window.")
    assert "Vande Bharat" in req.reason

    # Too short -> ValidationError
    with pytest.raises(ValidationError):
        RejectPlanRequest(reason="Bad")

    # Empty -> ValidationError
    with pytest.raises(ValidationError):
        RejectPlanRequest(reason="")


def test_comment_request_validation():
    """Review comment requires >= 3 chars."""
    req = AddReviewCommentRequest(comment="Window looks adequate for OHE works.")
    assert req.comment.startswith("Window")

    with pytest.raises(ValidationError):
        AddReviewCommentRequest(comment="ok")


# =============================================================================
# 2. STATE MACHINE TRANSITIONS
# =============================================================================

def test_legal_state_machine_transitions():
    """Enforce permitted lifecycle transitions."""
    repo = PlanVersionRepository(session=MagicMock())

    # Valid transitions
    repo.validate_transition(PlanVersionStatus.PENDING_REVIEW, PlanVersionStatus.UNDER_REVIEW)
    repo.validate_transition(PlanVersionStatus.PENDING_REVIEW, PlanVersionStatus.APPROVED)
    repo.validate_transition(PlanVersionStatus.PENDING_REVIEW, PlanVersionStatus.REJECTED)

    repo.validate_transition(PlanVersionStatus.UNDER_REVIEW, PlanVersionStatus.APPROVED)
    repo.validate_transition(PlanVersionStatus.UNDER_REVIEW, PlanVersionStatus.REJECTED)
    repo.validate_transition(PlanVersionStatus.UNDER_REVIEW, PlanVersionStatus.PENDING_REVIEW)

    repo.validate_transition(PlanVersionStatus.APPROVED, PlanVersionStatus.SUPERSEDED)


def test_illegal_state_machine_transitions():
    """Enforce blocked transitions."""
    repo = PlanVersionRepository(session=MagicMock())

    # Cannot approve or edit an already rejected plan
    with pytest.raises(InvalidPlanVersionTransitionError):
        repo.validate_transition(PlanVersionStatus.REJECTED, PlanVersionStatus.APPROVED)

    with pytest.raises(InvalidPlanVersionTransitionError):
        repo.validate_transition(PlanVersionStatus.REJECTED, PlanVersionStatus.UNDER_REVIEW)

    # Cannot modify an already approved plan (must supersede instead)
    with pytest.raises(InvalidPlanVersionTransitionError):
        repo.validate_transition(PlanVersionStatus.APPROVED, PlanVersionStatus.UNDER_REVIEW)

    with pytest.raises(InvalidPlanVersionTransitionError):
        repo.validate_transition(PlanVersionStatus.APPROVED, PlanVersionStatus.REJECTED)

    # Superseded is terminal
    with pytest.raises(InvalidPlanVersionTransitionError):
        repo.validate_transition(PlanVersionStatus.SUPERSEDED, PlanVersionStatus.APPROVED)


# =============================================================================
# 3. RBAC CREDENTIALS & PERMISSIONS
# =============================================================================

def test_rbac_governance_permissions():
    """Verify role permissions for governance operations."""
    approver = KNOWN_CREDENTIALS["approver-token-2026"]
    planner = KNOWN_CREDENTIALS["planner-token-2026"]
    viewer = KNOWN_CREDENTIALS["viewer-token-2026"]
    admin = KNOWN_CREDENTIALS["admin-token-2026"]

    # Approver
    assert approver.has_permission("plan:approve")
    assert approver.has_permission("plan:reject")
    assert approver.has_permission("plan:review")

    # Planner can review and write, but CANNOT approve or reject
    assert planner.has_permission("plan:review")
    assert planner.has_permission("write:operational")
    assert not planner.has_permission("plan:approve")
    assert not planner.has_permission("plan:reject")

    # Viewer cannot review, write, approve, or reject
    assert not viewer.has_permission("plan:review")
    assert not viewer.has_permission("plan:approve")
    assert not viewer.has_permission("plan:reject")
    assert not viewer.has_permission("write:operational")

    # Admin has all permissions
    assert admin.has_permission("plan:approve")
    assert admin.has_permission("plan:reject")
    assert admin.has_permission("plan:review")


# =============================================================================
# 4. SERVICE PRECONDITION CHECKS (UNIT)
# =============================================================================

@pytest.mark.asyncio
async def test_create_plan_version_blocks_uncompleted_run():
    """Cannot create a plan version from an uncompleted or running run."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    uncompleted_run = MagicMock(spec=PlanningRunModel)
    uncompleted_run.status = "RUNNING"
    service.run_repo.get_by_run_id = AsyncMock(return_value=uncompleted_run)

    actor = KNOWN_CREDENTIALS["planner-token-2026"]
    with pytest.raises(PlanVersionApprovalBlockedError, match="expected 'COMPLETED'"):
        await service.create_plan_version_from_run("RUN-123", actor)


@pytest.mark.asyncio
async def test_create_plan_version_blocks_invalid_or_unapprovable_run():
    """Cannot promote an invalid or non-approvable run to a plan candidate."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    invalid_run = MagicMock(spec=PlanningRunModel)
    invalid_run.status = "COMPLETED"
    invalid_run.validation_status = "INVALID"
    invalid_run.is_approvable = False
    service.run_repo.get_by_run_id = AsyncMock(return_value=invalid_run)

    actor = KNOWN_CREDENTIALS["planner-token-2026"]
    with pytest.raises(PlanVersionApprovalBlockedError, match="Only certified valid schedules"):
        await service.create_plan_version_from_run("RUN-123", actor)


@pytest.mark.asyncio
async def test_approve_plan_blocks_unverified_plan():
    """Approval must fail if technical validation is not VALID or is_approvable is False."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    mock_plan = MagicMock(spec=PlanVersionModel)
    mock_plan.status = PlanVersionStatus.PENDING_REVIEW.value
    mock_plan.validation_status = "UNKNOWN"
    mock_plan.is_approvable = False
    mock_plan.plan_version_id = "PV-TEST-01"

    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=mock_plan)

    actor = KNOWN_CREDENTIALS["approver-token-2026"]
    with pytest.raises(PlanVersionApprovalBlockedError, match="Only certified valid schedules may be approved"):
        await service.approve_plan("PV-TEST-01", actor)


@pytest.mark.asyncio
async def test_approve_plan_blocks_fingerprint_mismatch():
    """Approval must fail if schedule fingerprint has been tampered with or differs from source run."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    mock_plan = MagicMock(spec=PlanVersionModel)
    mock_plan.plan_version_id = "PV-TEST-01"
    mock_plan.planning_run_id = "RUN-TEST-01"
    mock_plan.status = PlanVersionStatus.PENDING_REVIEW.value
    mock_plan.validation_status = "VALID"
    mock_plan.is_approvable = True
    mock_plan.validation_findings_summary = {"error_count": 0}
    mock_plan.schedule_identity = "FINGERPRINT_AAA"
    mock_plan.snapshot_hash = "SNAPSHOT_HASH_AAA"
    mock_plan.input_hash = "INPUT_HASH_AAA"

    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=mock_plan)

    mock_run = MagicMock(spec=PlanningRunModel)
    mock_run.validation_fingerprint = "FINGERPRINT_BBB_DIFFERENT"
    mock_run.snapshot_hash = "SNAPSHOT_HASH_AAA"
    mock_run.input_hash = "INPUT_HASH_AAA"
    service.run_repo.get_by_run_id = AsyncMock(return_value=mock_run)

    actor = KNOWN_CREDENTIALS["approver-token-2026"]
    with pytest.raises(PlanFingerprintMismatchError, match="Cryptographic fingerprint mismatch"):
        await service.approve_plan("PV-TEST-01", actor)


@pytest.mark.asyncio
async def test_approve_plan_blocks_if_already_approved():
    """An approved plan cannot be re-approved; immutability must be preserved."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    mock_plan = MagicMock(spec=PlanVersionModel)
    mock_plan.plan_version_id = "PV-TEST-01"
    mock_plan.status = PlanVersionStatus.APPROVED.value

    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=mock_plan)

    actor = KNOWN_CREDENTIALS["approver-token-2026"]
    with pytest.raises(PlanVersionImmutableError, match="is already APPROVED"):
        await service.approve_plan("PV-TEST-01", actor)


def test_approve_plan_request_schema_supports_declared_reviewer():
    """Verify ApprovePlanRequest schema accepts declared reviewer name and role."""
    req = ApprovePlanRequest(
        approval_notes="Approved for Sunday block window.",
        declared_reviewer_name="Shri R. K. Sharma",
        declared_reviewer_role="Senior Divisional Operations Manager (Sr. DOM)",
    )
    assert req.declared_reviewer_name == "Shri R. K. Sharma"
    assert req.declared_reviewer_role == "Senior Divisional Operations Manager (Sr. DOM)"


@pytest.mark.asyncio
async def test_approve_plan_persists_declared_reviewer_in_audit_metadata():
    """Approval persists declared reviewer metadata while preserving authenticated actor ID."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    mock_plan = MagicMock(spec=PlanVersionModel)
    mock_plan.plan_version_id = "PV-TEST-01"
    mock_plan.planning_run_id = "RUN-TEST-01"
    mock_plan.status = PlanVersionStatus.PENDING_REVIEW.value
    mock_plan.validation_status = "VALID"
    mock_plan.is_approvable = True
    mock_plan.validation_findings_summary = {"error_count": 0}
    mock_plan.schedule_identity = "FINGERPRINT_AAA"
    mock_plan.snapshot_hash = "SNAPSHOT_HASH_AAA"
    mock_plan.input_hash = "INPUT_HASH_AAA"
    mock_plan.scenario_id = "SCN-TEST-01"
    mock_plan.version_number = 1
    mock_plan.scheduler_type = "CP_SAT"
    mock_plan.previous_plan_version_id = None

    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=mock_plan)
    service.plan_repo.get_latest_approved = AsyncMock(return_value=None)
    service.plan_repo.add_review_comment = AsyncMock()
    service.plan_repo.add_audit_event = AsyncMock()
    service.plan_repo.get_by_plan_version_id = AsyncMock(return_value=mock_plan)

    mock_run = MagicMock(spec=PlanningRunModel)
    mock_run.validation_fingerprint = "FINGERPRINT_AAA"
    mock_run.snapshot_hash = "SNAPSHOT_HASH_AAA"
    mock_run.input_hash = "INPUT_HASH_AAA"
    service.run_repo.get_by_run_id = AsyncMock(return_value=mock_run)

    actor = KNOWN_CREDENTIALS["approver-token-2026"]
    result = await service.approve_plan(
        plan_version_id="PV-TEST-01",
        actor=actor,
        comment="Formal block granted.",
        declared_reviewer_name="Shri R. K. Sharma",
        declared_reviewer_role="Sr. DOM / DLI",
    )

    # 1. Authoritative actor on plan must be the authenticated user
    assert mock_plan.status == PlanVersionStatus.APPROVED.value
    assert mock_plan.approved_by == actor.username

    # 2. Audit event record must capture both authoritative actor and declared reviewer
    service.plan_repo.add_audit_event.assert_called_once()
    audit_event = service.plan_repo.add_audit_event.call_args[0][0]
    assert audit_event.actor_id == actor.user_id
    assert audit_event.actor_username == actor.username
    assert audit_event.actor_role == actor.role.value
    assert audit_event.event_metadata["declared_reviewer"]["name"] == "Shri R. K. Sharma"
    assert audit_event.event_metadata["declared_reviewer"]["role"] == "Sr. DOM / DLI"

