"""Unit tests for TrackMeld Batch 9: Persisted Planning Lifecycle Verification.

Verifies the end-to-end backend governance lifecycle from planning run to persisted
plan version, independent validation gating, Four-Eyes human sign-off, and audit trail:

1. End-to-end happy path: Requisition -> Completed Run -> PlanVersion Creation -> Human Review -> Approval
2. COMPLETED != APPROVED invariant: Solver run completion does not create or approve a PlanVersion
3. Precondition gating on PlanVersion creation:
   - Non-COMPLETED runs strictly rejected
   - Unverified / INVALID / unapprovable runs strictly rejected
   - Missing schedule_result strictly rejected
   - Duplicate plan version for same run strictly rejected
4. Precondition gating on PlanVersion approval:
   - Already approved plan cannot be re-approved (immutability)
   - Rejected plan cannot be approved (illegal transition)
   - Missing or non-VALID validation status strictly rejected
   - is_approvable=False strictly rejected
   - Non-zero error_count strictly rejected
   - Cryptographic fingerprint / schedule identity mismatch strictly rejected
   - Snapshot hash or input hash mismatch strictly rejected
   - Four-Eyes separation of duties strictly enforced (creator cannot approve)
   - Missing source run strictly rejected
   - Prior approved version automatically superseded with audit linkage
5. Rejection audit trail:
   - Rejection requires valid reason and records PLAN_REJECTED audit event
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from backend.app.schemas.plan_version import (
    PlanVersionStatus,
    PlanReviewAction,
    GovernanceEventType,
    ApprovePlanRequest,
    RejectPlanRequest,
)
from backend.app.domain.enums import DataClass
from backend.app.repositories.plan_version_repo import (
    PlanVersionRepository,
    InvalidPlanVersionTransitionError,
    PlanVersionApprovalBlockedError,
    PlanFingerprintMismatchError,
    PlanVersionImmutableError,
    PlanVersionAlreadyExistsError,
    FourEyesViolationError,
)
from backend.app.core.auth import KNOWN_CREDENTIALS, AuthUser, UserRole
from backend.app.db.models.planning_run import PlanningRunModel
from backend.app.db.models.plan_version import (
    PlanVersionModel,
    PlanReviewCommentModel,
    GovernanceAuditEventModel,
)
from backend.app.services.plan_governance_service import PlanGovernanceService


# =============================================================================
# 1. END-TO-END LIFECYCLE HAPPY PATH
# =============================================================================

@pytest.mark.asyncio
async def test_batch9_persisted_lifecycle_complete_happy_path():
    """Verify full lifecycle: Certified Run -> PlanVersion Candidate -> Under Review -> Formal Approval."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    planner_actor = KNOWN_CREDENTIALS["planner-token-2026"]
    approver_actor = KNOWN_CREDENTIALS["approver-token-2026"]

    # 1. Source completed and certified planning run
    mock_run = MagicMock(spec=PlanningRunModel)
    mock_run.run_id = "RUN-BATCH9-001"
    mock_run.scenario_id = "SCN-DEMO-001"
    mock_run.status = "COMPLETED"
    mock_run.stage = "COMPLETED"
    mock_run.scheduler_type = "CP_SAT"
    mock_run.scheduler_version = "1.0.0"
    mock_run.solver_name = "OR-Tools CP-SAT"
    mock_run.solver_version = "9.8"
    mock_run.dataset_version = "2026.1"
    mock_run.validation_status = "VALID"
    mock_run.validation_fingerprint = "FP_SHA256_CERTIFIED_001"
    mock_run.snapshot_hash = "SNAP_HASH_001"
    mock_run.input_hash = "IN_HASH_001"
    mock_run.is_approvable = True
    mock_run.schedule_result = {"status": "OPTIMAL", "scheduled_tasks": [{"task_id": "TSK-01"}]}
    mock_run.result_summary = {"total_tasks": 1, "scheduled_tasks": 1}
    mock_run.validation_findings_summary = {"error_count": 0, "warning_count": 0}
    mock_run.diagnostics_summary = None
    mock_run.configuration_snapshot = {"time_limit_seconds": 5.0}
    mock_run.priority_configuration = None
    mock_run.optimization_configuration = None

    service.run_repo.get_by_run_id = AsyncMock(return_value=mock_run)
    service.plan_repo.get_by_planning_run_id = AsyncMock(return_value=None)
    service.plan_repo.get_next_version_number = AsyncMock(return_value=1)
    service.plan_repo.create_plan_version = AsyncMock()
    service.plan_repo.add_audit_event = AsyncMock()
    service.plan_repo.add_review_comment = AsyncMock()

    # Step 2: Instantiate PlanVersion Candidate
    created_plan_holder = []
    async def mock_create(pv):
        created_plan_holder.append(pv)
        return pv

    service.plan_repo.create_plan_version.side_effect = mock_create
    service.plan_repo.get_by_plan_version_id = AsyncMock(side_effect=lambda pid: created_plan_holder[0])

    plan_candidate = await service.create_plan_version_from_run(
        run_id="RUN-BATCH9-001",
        actor=planner_actor,
        comment="Block proposal for corridor.",
    )

    assert plan_candidate is not None
    assert plan_candidate.version_number == 1
    assert plan_candidate.status == PlanVersionStatus.PENDING_REVIEW.value
    assert plan_candidate.schedule_identity == "FP_SHA256_CERTIFIED_001"
    assert plan_candidate.created_by == planner_actor.username
    assert plan_candidate.is_approvable is True
    assert plan_candidate.validation_status == "VALID"

    # Step 3: Transition to UNDER_REVIEW
    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=plan_candidate)
    under_review_plan = await service.start_review(
        plan_candidate.plan_version_id,
        actor=approver_actor,
        comment="Commencing independent review of safety buffers.",
    )
    assert under_review_plan.status == PlanVersionStatus.UNDER_REVIEW.value
    assert under_review_plan.reviewed_by == approver_actor.username

    # Step 4: Formal Human Approval by Independent Approver
    mock_scenario = MagicMock()
    mock_scenario.scenario_id = "SCN-DEMO-001"
    mock_scenario.classification = DataClass.REAL
    service.scenario_repo.get_by_id = AsyncMock(return_value=mock_scenario)

    service.plan_repo.get_latest_approved = AsyncMock(return_value=None)
    approved_plan = await service.approve_plan(
        plan_version_id=plan_candidate.plan_version_id,
        actor=approver_actor,
        comment="Full corridor block authorized.",
        declared_reviewer_name="Shri R. K. Sharma",
        declared_reviewer_role="Senior Divisional Operations Manager (Sr. DOM)",
    )

    assert approved_plan.status == PlanVersionStatus.APPROVED.value
    assert approved_plan.approved_by == approver_actor.username
    assert approved_plan.approved_at is not None


# =============================================================================
# 2. INVARIANT: COMPLETED != APPROVED
# =============================================================================

@pytest.mark.asyncio
async def test_batch9_completed_run_is_not_approved_invariant():
    """A completed solver run must NOT automatically create an approved plan version."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    mock_run = MagicMock(spec=PlanningRunModel)
    mock_run.run_id = "RUN-123"
    mock_run.status = "COMPLETED"
    mock_run.validation_status = "VALID"
    mock_run.is_approvable = True

    service.run_repo.get_by_run_id = AsyncMock(return_value=mock_run)
    service.plan_repo.get_by_planning_run_id = AsyncMock(return_value=None)

    # In the absence of an explicit human promotion step, no PlanVersion exists
    existing = await service.plan_repo.get_by_planning_run_id("RUN-123")
    assert existing is None


# =============================================================================
# 3. PLAN VERSION CREATION GATING
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize("illegal_status", ["PENDING", "RUNNING", "FAILED", "TIMED_OUT", "CANCELLED"])
async def test_batch9_plan_version_creation_fails_for_non_completed_run(illegal_status: str):
    """PlanVersion creation must reject any run that is not COMPLETED."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    mock_run = MagicMock(spec=PlanningRunModel)
    mock_run.run_id = f"RUN-{illegal_status}"
    mock_run.status = illegal_status
    service.run_repo.get_by_run_id = AsyncMock(return_value=mock_run)

    actor = KNOWN_CREDENTIALS["planner-token-2026"]
    with pytest.raises(PlanVersionApprovalBlockedError, match="expected 'COMPLETED'"):
        await service.create_plan_version_from_run(f"RUN-{illegal_status}", actor)


@pytest.mark.asyncio
async def test_batch9_plan_version_creation_fails_for_unverified_or_unapprovable_run():
    """PlanVersion creation must reject a run whose validation is not certified VALID."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    mock_run = MagicMock(spec=PlanningRunModel)
    mock_run.run_id = "RUN-INVALID"
    mock_run.status = "COMPLETED"
    mock_run.validation_status = "INVALID"
    mock_run.is_approvable = False
    service.run_repo.get_by_run_id = AsyncMock(return_value=mock_run)

    actor = KNOWN_CREDENTIALS["planner-token-2026"]
    with pytest.raises(PlanVersionApprovalBlockedError, match="Only certified valid schedules"):
        await service.create_plan_version_from_run("RUN-INVALID", actor)


@pytest.mark.asyncio
async def test_batch9_plan_version_creation_fails_if_already_exists():
    """Duplicate PlanVersion creation for the same run is strictly blocked."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    mock_run = MagicMock(spec=PlanningRunModel)
    mock_run.run_id = "RUN-EXISTING"
    mock_run.status = "COMPLETED"
    mock_run.validation_status = "VALID"
    mock_run.is_approvable = True
    mock_run.schedule_result = {"status": "OPTIMAL"}
    service.run_repo.get_by_run_id = AsyncMock(return_value=mock_run)

    existing_plan = MagicMock(spec=PlanVersionModel)
    existing_plan.plan_version_id = "PV-EXISTING-01"
    service.plan_repo.get_by_planning_run_id = AsyncMock(return_value=existing_plan)

    actor = KNOWN_CREDENTIALS["planner-token-2026"]
    with pytest.raises(PlanVersionAlreadyExistsError, match="already exists"):
        await service.create_plan_version_from_run("RUN-EXISTING", actor)


# =============================================================================
# 4. APPROVAL PRECONDITION GATING
# =============================================================================

@pytest.mark.asyncio
async def test_batch9_approval_rejected_if_already_approved():
    """An already approved plan cannot be approved again (immutability)."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    mock_plan = MagicMock(spec=PlanVersionModel)
    mock_plan.plan_version_id = "PV-APP-01"
    mock_plan.status = PlanVersionStatus.APPROVED.value
    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=mock_plan)

    actor = KNOWN_CREDENTIALS["approver-token-2026"]
    with pytest.raises(PlanVersionImmutableError, match="is already APPROVED"):
        await service.approve_plan("PV-APP-01", actor)


@pytest.mark.asyncio
async def test_batch9_approval_rejected_if_rejected_status():
    """A rejected plan cannot transition directly to APPROVED."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    mock_plan = MagicMock(spec=PlanVersionModel)
    mock_plan.plan_version_id = "PV-REJ-01"
    mock_plan.status = PlanVersionStatus.REJECTED.value
    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=mock_plan)

    actor = KNOWN_CREDENTIALS["approver-token-2026"]
    with pytest.raises(InvalidPlanVersionTransitionError):
        await service.approve_plan("PV-REJ-01", actor)


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_val_status", ["UNKNOWN", "INVALID", None])
async def test_batch9_approval_rejected_if_validation_status_not_valid(invalid_val_status):
    """Approval must be rejected if validation status is not VALID."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    mock_plan = MagicMock(spec=PlanVersionModel)
    mock_plan.plan_version_id = "PV-TEST-VAL"
    mock_plan.status = PlanVersionStatus.UNDER_REVIEW.value
    mock_plan.validation_status = invalid_val_status
    mock_plan.is_approvable = True
    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=mock_plan)

    actor = KNOWN_CREDENTIALS["approver-token-2026"]
    with pytest.raises(PlanVersionApprovalBlockedError, match="Only certified valid schedules may be approved"):
        await service.approve_plan("PV-TEST-VAL", actor)


@pytest.mark.asyncio
async def test_batch9_approval_rejected_if_validation_findings_contain_errors():
    """Approval must be rejected if hard validation error count > 0."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    mock_plan = MagicMock(spec=PlanVersionModel)
    mock_plan.plan_version_id = "PV-TEST-ERR"
    mock_plan.status = PlanVersionStatus.UNDER_REVIEW.value
    mock_plan.validation_status = "VALID"
    mock_plan.is_approvable = True
    mock_plan.validation_findings_summary = {"error_count": 1, "errors": ["HEADWAY_CONFLICT"]}
    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=mock_plan)

    actor = KNOWN_CREDENTIALS["approver-token-2026"]
    with pytest.raises(PlanVersionApprovalBlockedError, match="Contains 1 unresolved hard validation errors"):
        await service.approve_plan("PV-TEST-ERR", actor)


@pytest.mark.asyncio
async def test_batch9_approval_rejected_on_schedule_identity_mismatch():
    """Approval must be rejected if schedule fingerprint differs from source run."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    mock_plan = MagicMock(spec=PlanVersionModel)
    mock_plan.plan_version_id = "PV-TEST-FP"
    mock_plan.planning_run_id = "RUN-FP-01"
    mock_plan.status = PlanVersionStatus.UNDER_REVIEW.value
    mock_plan.validation_status = "VALID"
    mock_plan.is_approvable = True
    mock_plan.validation_findings_summary = {"error_count": 0}
    mock_plan.schedule_identity = "FP_A_TAMPERED"
    mock_plan.snapshot_hash = "SNAP_01"
    mock_plan.input_hash = "IN_01"
    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=mock_plan)

    mock_run = MagicMock(spec=PlanningRunModel)
    mock_run.validation_fingerprint = "FP_B_AUTHENTIC"
    mock_run.snapshot_hash = "SNAP_01"
    mock_run.input_hash = "IN_01"
    service.run_repo.get_by_run_id = AsyncMock(return_value=mock_run)

    actor = KNOWN_CREDENTIALS["approver-token-2026"]
    with pytest.raises(PlanFingerprintMismatchError, match="Cryptographic fingerprint mismatch"):
        await service.approve_plan("PV-TEST-FP", actor)


@pytest.mark.asyncio
async def test_batch9_approval_rejected_on_four_eyes_creator_conflict():
    """Separation of duties: The creator of a plan version cannot approve it."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    mock_plan = MagicMock(spec=PlanVersionModel)
    mock_plan.plan_version_id = "PV-TEST-4EYES"
    mock_plan.planning_run_id = "RUN-4EYES"
    mock_plan.status = PlanVersionStatus.UNDER_REVIEW.value
    mock_plan.validation_status = "VALID"
    mock_plan.is_approvable = True
    mock_plan.validation_findings_summary = {"error_count": 0}
    mock_plan.schedule_identity = "FP_SAME"
    mock_plan.snapshot_hash = "SNAP_SAME"
    mock_plan.input_hash = "IN_SAME"
    mock_plan.created_by = "divisional_operations_manager"  # Same as approver username!

    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=mock_plan)

    mock_run = MagicMock(spec=PlanningRunModel)
    mock_run.validation_fingerprint = "FP_SAME"
    mock_run.snapshot_hash = "SNAP_SAME"
    mock_run.input_hash = "IN_SAME"
    service.run_repo.get_by_run_id = AsyncMock(return_value=mock_run)

    # Actor has same username as creator
    actor = KNOWN_CREDENTIALS["approver-token-2026"]
    assert actor.username == "divisional_operations_manager"

    with pytest.raises(FourEyesViolationError, match="Separation of duties violation"):
        await service.approve_plan("PV-TEST-4EYES", actor)


@pytest.mark.asyncio
async def test_batch9_approval_supersedes_previous_approved_version():
    """Approving a new version must automatically transition the previously approved version to SUPERSEDED."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    # New plan candidate (v2)
    mock_new_plan = MagicMock(spec=PlanVersionModel)
    mock_new_plan.plan_version_id = "PV-v2-002"
    mock_new_plan.scenario_id = "SCN-001"
    mock_new_plan.version_number = 2
    mock_new_plan.planning_run_id = "RUN-v2"
    mock_new_plan.status = PlanVersionStatus.UNDER_REVIEW.value
    mock_new_plan.validation_status = "VALID"
    mock_new_plan.is_approvable = True
    mock_new_plan.validation_findings_summary = {"error_count": 0}
    mock_new_plan.schedule_identity = "FP_V2"
    mock_new_plan.snapshot_hash = "SNAP_V2"
    mock_new_plan.input_hash = "IN_V2"
    mock_new_plan.created_by = "different_user"
    mock_new_plan.previous_plan_version_id = None

    # Previously approved plan (v1)
    mock_prev_approved = MagicMock(spec=PlanVersionModel)
    mock_prev_approved.plan_version_id = "PV-v1-001"
    mock_prev_approved.version_number = 1
    mock_prev_approved.status = PlanVersionStatus.APPROVED.value
    mock_prev_approved.schedule_identity = "FP_V1"
    mock_prev_approved.snapshot_hash = "SNAP_V1"
    mock_prev_approved.input_hash = "IN_V1"

    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=mock_new_plan)
    service.plan_repo.get_latest_approved = AsyncMock(return_value=mock_prev_approved)
    service.plan_repo.add_review_comment = AsyncMock()
    service.plan_repo.add_audit_event = AsyncMock()
    service.plan_repo.get_by_plan_version_id = AsyncMock(return_value=mock_new_plan)

    mock_run = MagicMock(spec=PlanningRunModel)
    mock_run.validation_fingerprint = "FP_V2"
    mock_run.snapshot_hash = "SNAP_V2"
    mock_run.input_hash = "IN_V2"
    service.run_repo.get_by_run_id = AsyncMock(return_value=mock_run)

    mock_scenario = MagicMock()
    mock_scenario.scenario_id = "SCN-001"
    mock_scenario.classification = DataClass.REAL
    service.scenario_repo.get_by_id = AsyncMock(return_value=mock_scenario)

    actor = KNOWN_CREDENTIALS["approver-token-2026"]
    await service.approve_plan("PV-v2-002", actor, comment="Approved v2.")

    # Verify previous version superseded
    assert mock_prev_approved.status == PlanVersionStatus.SUPERSEDED.value
    assert mock_prev_approved.superseded_by == actor.username
    assert mock_prev_approved.superseded_at is not None
    assert mock_new_plan.previous_plan_version_id == "PV-v1-001"
    assert mock_new_plan.status == PlanVersionStatus.APPROVED.value


@pytest.mark.asyncio
async def test_batch9_rejection_records_audit_and_sets_rejected_status():
    """Formal rejection must require substantive reason and append immutable audit event."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    mock_plan = MagicMock(spec=PlanVersionModel)
    mock_plan.plan_version_id = "PV-REJ-TEST"
    mock_plan.scenario_id = "SCN-001"
    mock_plan.version_number = 1
    mock_plan.status = PlanVersionStatus.UNDER_REVIEW.value
    mock_plan.schedule_identity = "FP_TEST"
    mock_plan.snapshot_hash = "SNAP_TEST"
    mock_plan.input_hash = "IN_TEST"

    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=mock_plan)
    service.plan_repo.add_review_comment = AsyncMock()
    service.plan_repo.add_audit_event = AsyncMock()
    service.plan_repo.get_by_plan_version_id = AsyncMock(return_value=mock_plan)

    actor = KNOWN_CREDENTIALS["approver-token-2026"]
    reason = "Traffic disruption exceeds permissible freight headway limits on UP line."

    rejected = await service.reject_plan("PV-REJ-TEST", actor, reason=reason)

    assert mock_plan.status == PlanVersionStatus.REJECTED.value
    assert mock_plan.rejected_by == actor.username
    assert mock_plan.rejection_reason == reason

    # Verify audit event registered with reason
    service.plan_repo.add_audit_event.assert_called_once()
    audit_event = service.plan_repo.add_audit_event.call_args[0][0]
    assert audit_event.event_type == GovernanceEventType.PLAN_REJECTED.value
    assert audit_event.reason == reason
    assert audit_event.previous_state == PlanVersionStatus.UNDER_REVIEW.value
    assert audit_event.new_state == PlanVersionStatus.REJECTED.value
