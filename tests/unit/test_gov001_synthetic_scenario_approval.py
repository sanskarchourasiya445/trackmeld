"""Unit regression tests for GOV-001: Synthetic Scenario Approval Prevention.

Verifies:
1. Synthetic scenarios (DataClass.SYNTHETIC) cannot be approved as real operational plans.
2. Assumed scenarios (DataClass.ASSUMED) cannot be approved as real operational plans.
3. Derived scenarios (DataClass.DERIVED) cannot be approved as real operational plans.
4. Non-existent scenarios fail closed (missing scenario provenance).
5. Scenarios with missing/null data classification fail closed.
6. Genuine operational scenarios (DataClass.REAL) can be approved when all preconditions pass.
7. Four-Eyes separation of duties remains strictly enforced for eligible real scenarios.
8. Validation evidence and zero blocking error checks remain strictly enforced for real scenarios.
9. Superseding of prior approved versions remains strictly preserved for real scenarios.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest

from backend.app.core.auth import AuthUser, UserRole
from backend.app.domain.enums import DataClass
from backend.app.db.models.planning_run import PlanningRunModel
from backend.app.db.models.plan_version import PlanVersionModel
from backend.app.db.models.scenario import OperationalScenarioModel
from backend.app.schemas.plan_version import (
    PlanVersionStatus,
    GovernanceEventType,
)
from backend.app.repositories.plan_version_repo import (
    PlanVersionApprovalBlockedError,
    PlanVersionImmutableError,
    FourEyesViolationError,
)
from backend.app.services.plan_governance_service import PlanGovernanceService


def _build_mock_plan(
    plan_version_id: str = "PV-TEST-001",
    scenario_id: str = "SCN-TEST-001",
    status: str = PlanVersionStatus.PENDING_REVIEW.value,
    validation_status: str = "VALID",
    is_approvable: bool = True,
    error_count: int = 0,
    created_by: str = "creator_user",
) -> PlanVersionModel:
    plan = MagicMock(spec=PlanVersionModel)
    plan.plan_version_id = plan_version_id
    plan.scenario_id = scenario_id
    plan.planning_run_id = f"RUN-{plan_version_id}"
    plan.version_number = 1
    plan.status = status
    plan.validation_status = validation_status
    plan.is_approvable = is_approvable
    plan.validation_findings_summary = {"error_count": error_count, "warning_count": 0}
    plan.schedule_identity = "FP_SHA256_TEST_001"
    plan.snapshot_hash = "SNAP_HASH_TEST_001"
    plan.input_hash = "IN_HASH_TEST_001"
    plan.created_by = created_by
    plan.previous_plan_version_id = None
    return plan


def _build_mock_run(plan: PlanVersionModel) -> PlanningRunModel:
    run = MagicMock(spec=PlanningRunModel)
    run.run_id = plan.planning_run_id
    run.validation_fingerprint = plan.schedule_identity
    run.snapshot_hash = plan.snapshot_hash
    run.input_hash = plan.input_hash
    return run


def _build_approver_actor(username: str = "approver_officer") -> AuthUser:
    return AuthUser(
        user_id="USR-APPR-01",
        username=username,
        role=UserRole.OPERATOR,
        permissions=["read:reference", "read:operational", "plan:review", "plan:approve", "plan:reject"],
    )


# =============================================================================
# 1. SYNTHETIC SCENARIO REJECTION (GOV-001 CORE)
# =============================================================================

@pytest.mark.asyncio
async def test_synthetic_scenario_approval_blocked():
    """Synthetic scenario plans (DataClass.SYNTHETIC) must strictly be rejected from approval."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    plan = _build_mock_plan(scenario_id="SCN-DEMO-001")
    run = _build_mock_run(plan)
    actor = _build_approver_actor()

    mock_scenario = MagicMock(spec=OperationalScenarioModel)
    mock_scenario.scenario_id = "SCN-DEMO-001"
    mock_scenario.classification = DataClass.SYNTHETIC

    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=plan)
    service.run_repo.get_by_run_id = AsyncMock(return_value=run)
    service.scenario_repo.get_by_id = AsyncMock(return_value=mock_scenario)
    service.plan_repo.add_audit_event = AsyncMock()

    with pytest.raises(PlanVersionApprovalBlockedError) as exc_info:
        await service.approve_plan(plan.plan_version_id, actor, comment="Attempted synthetic approval")

    error_msg = str(exc_info.value)
    assert "Synthetic, demonstration, or assumed scenarios cannot be approved as real operational plans" in error_msg
    assert "SYNTHETIC" in error_msg

    # Plan status must remain unchanged, and no approval audit event may be committed
    assert plan.status != PlanVersionStatus.APPROVED.value
    service.plan_repo.add_audit_event.assert_not_called()
    session.commit.assert_not_called()


# =============================================================================
# 2. ASSUMED & DERIVED SCENARIO REJECTION
# =============================================================================

@pytest.mark.asyncio
async def test_assumed_scenario_approval_blocked():
    """Assumed scenario plans (DataClass.ASSUMED) must strictly be rejected from approval."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    plan = _build_mock_plan(scenario_id="SCN-ASSUMED-001")
    run = _build_mock_run(plan)
    actor = _build_approver_actor()

    mock_scenario = MagicMock(spec=OperationalScenarioModel)
    mock_scenario.scenario_id = "SCN-ASSUMED-001"
    mock_scenario.classification = DataClass.ASSUMED

    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=plan)
    service.run_repo.get_by_run_id = AsyncMock(return_value=run)
    service.scenario_repo.get_by_id = AsyncMock(return_value=mock_scenario)

    with pytest.raises(PlanVersionApprovalBlockedError) as exc_info:
        await service.approve_plan(plan.plan_version_id, actor)

    assert "ASSUMED" in str(exc_info.value)
    assert "cannot be approved as real operational plans" in str(exc_info.value)


@pytest.mark.asyncio
async def test_derived_scenario_approval_blocked():
    """Derived scenario plans (DataClass.DERIVED) must strictly be rejected from operational approval."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    plan = _build_mock_plan(scenario_id="SCN-DERIVED-001")
    run = _build_mock_run(plan)
    actor = _build_approver_actor()

    mock_scenario = MagicMock(spec=OperationalScenarioModel)
    mock_scenario.scenario_id = "SCN-DERIVED-001"
    mock_scenario.classification = DataClass.DERIVED

    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=plan)
    service.run_repo.get_by_run_id = AsyncMock(return_value=run)
    service.scenario_repo.get_by_id = AsyncMock(return_value=mock_scenario)

    with pytest.raises(PlanVersionApprovalBlockedError) as exc_info:
        await service.approve_plan(plan.plan_version_id, actor)

    assert "DERIVED" in str(exc_info.value)
    assert "cannot be approved as real operational plans" in str(exc_info.value)


# =============================================================================
# 3. MISSING OR UNKNOWN SCENARIO PROVENANCE (FAIL CLOSED)
# =============================================================================

@pytest.mark.asyncio
async def test_missing_scenario_fails_closed():
    """Non-existent scenario in repository fails closed on approval."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    plan = _build_mock_plan(scenario_id="SCN-DOES-NOT-EXIST")
    run = _build_mock_run(plan)
    actor = _build_approver_actor()

    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=plan)
    service.run_repo.get_by_run_id = AsyncMock(return_value=run)
    # Scenario not found
    service.scenario_repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(PlanVersionApprovalBlockedError) as exc_info:
        await service.approve_plan(plan.plan_version_id, actor)

    error_msg = str(exc_info.value)
    assert "not found" in error_msg.lower()
    assert "missing scenario provenance fails closed" in error_msg.lower()


@pytest.mark.asyncio
async def test_missing_scenario_classification_fails_closed():
    """Scenario with None classification fails closed on approval."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    plan = _build_mock_plan(scenario_id="SCN-NULL-CLASS-001")
    run = _build_mock_run(plan)
    actor = _build_approver_actor()

    mock_scenario = MagicMock(spec=OperationalScenarioModel)
    mock_scenario.scenario_id = "SCN-NULL-CLASS-001"
    mock_scenario.classification = None

    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=plan)
    service.run_repo.get_by_run_id = AsyncMock(return_value=run)
    service.scenario_repo.get_by_id = AsyncMock(return_value=mock_scenario)

    with pytest.raises(PlanVersionApprovalBlockedError) as exc_info:
        await service.approve_plan(plan.plan_version_id, actor)

    error_msg = str(exc_info.value)
    assert "unknown or missing data classification" in error_msg.lower()
    assert "missing provenance fails closed" in error_msg.lower()


# =============================================================================
# 4. ELIGIBLE REAL OPERATIONAL SCENARIO APPROVAL
# =============================================================================

@pytest.mark.asyncio
async def test_eligible_real_scenario_approval_succeeds():
    """Genuine operational scenario (DataClass.REAL) successfully approves and records audit trail."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    plan = _build_mock_plan(scenario_id="SCN-REAL-OPERATIONAL-001", created_by="senior_planner")
    run = _build_mock_run(plan)
    actor = _build_approver_actor(username="independent_approver")

    mock_scenario = MagicMock(spec=OperationalScenarioModel)
    mock_scenario.scenario_id = "SCN-REAL-OPERATIONAL-001"
    mock_scenario.classification = DataClass.REAL

    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=plan)
    service.run_repo.get_by_run_id = AsyncMock(return_value=run)
    service.scenario_repo.get_by_id = AsyncMock(return_value=mock_scenario)
    service.plan_repo.get_latest_approved = AsyncMock(return_value=None)
    service.plan_repo.add_review_comment = AsyncMock()
    service.plan_repo.add_audit_event = AsyncMock()
    service.plan_repo.get_by_plan_version_id = AsyncMock(return_value=plan)

    approved = await service.approve_plan(
        plan_version_id=plan.plan_version_id,
        actor=actor,
        comment="Corridor track possession formally approved.",
        declared_reviewer_name="Shri V. K. Malhotra",
        declared_reviewer_role="Chief Operations Manager",
    )

    assert plan.status == PlanVersionStatus.APPROVED.value
    assert plan.approved_by == actor.username
    assert plan.approved_at is not None

    # Review comment and audit event must be recorded
    service.plan_repo.add_audit_event.assert_called_once()
    audit_call = service.plan_repo.add_audit_event.call_args[0][0]
    assert audit_call.event_type == GovernanceEventType.PLAN_APPROVED.value
    assert audit_call.actor_id == actor.user_id
    assert audit_call.actor_username == actor.username
    assert audit_call.event_metadata["declared_reviewer"]["name"] == "Shri V. K. Malhotra"

    # Transaction committed
    session.commit.assert_called_once()


# =============================================================================
# 5. PRESERVED GOVERNANCE INVARIANTS ON ELIGIBLE REAL SCENARIOS
# =============================================================================

@pytest.mark.asyncio
async def test_eligible_real_scenario_still_enforces_four_eyes():
    """Even for DataClass.REAL, creator self-approval is strictly forbidden."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    plan = _build_mock_plan(scenario_id="SCN-REAL-001", created_by="chief_planner")
    run = _build_mock_run(plan)
    # Approver username matches creator username
    same_actor = _build_approver_actor(username="chief_planner")

    mock_scenario = MagicMock(spec=OperationalScenarioModel)
    mock_scenario.scenario_id = "SCN-REAL-001"
    mock_scenario.classification = DataClass.REAL

    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=plan)
    service.run_repo.get_by_run_id = AsyncMock(return_value=run)
    service.scenario_repo.get_by_id = AsyncMock(return_value=mock_scenario)

    with pytest.raises(FourEyesViolationError, match="Separation of duties violation"):
        await service.approve_plan(plan.plan_version_id, same_actor)


@pytest.mark.asyncio
async def test_eligible_real_scenario_still_enforces_validation_evidence():
    """Even for DataClass.REAL, uncertified or errored schedules cannot be approved."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    # Error count > 0 blocks approval
    plan = _build_mock_plan(scenario_id="SCN-REAL-001", error_count=1)
    run = _build_mock_run(plan)
    actor = _build_approver_actor()

    mock_scenario = MagicMock(spec=OperationalScenarioModel)
    mock_scenario.scenario_id = "SCN-REAL-001"
    mock_scenario.classification = DataClass.REAL

    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=plan)
    service.run_repo.get_by_run_id = AsyncMock(return_value=run)
    service.scenario_repo.get_by_id = AsyncMock(return_value=mock_scenario)

    with pytest.raises(PlanVersionApprovalBlockedError, match="unresolved hard validation errors"):
        await service.approve_plan(plan.plan_version_id, actor)


@pytest.mark.asyncio
async def test_eligible_real_scenario_supersedes_prior_approved_plan():
    """Approving a new version on a DataClass.REAL scenario supersedes the previous approved version."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    prior_plan = _build_mock_plan(plan_version_id="PV-PRIOR-001", scenario_id="SCN-REAL-001")
    prior_plan.version_number = 1
    prior_plan.status = PlanVersionStatus.APPROVED.value

    new_plan = _build_mock_plan(plan_version_id="PV-NEW-002", scenario_id="SCN-REAL-001")
    new_plan.version_number = 2
    run = _build_mock_run(new_plan)
    actor = _build_approver_actor()

    mock_scenario = MagicMock(spec=OperationalScenarioModel)
    mock_scenario.scenario_id = "SCN-REAL-001"
    mock_scenario.classification = DataClass.REAL

    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=new_plan)
    service.run_repo.get_by_run_id = AsyncMock(return_value=run)
    service.scenario_repo.get_by_id = AsyncMock(return_value=mock_scenario)
    service.plan_repo.get_latest_approved = AsyncMock(return_value=prior_plan)
    service.plan_repo.add_review_comment = AsyncMock()
    service.plan_repo.add_audit_event = AsyncMock()
    service.plan_repo.get_by_plan_version_id = AsyncMock(return_value=new_plan)

    await service.approve_plan(new_plan.plan_version_id, actor)

    # Prior plan is superseded
    assert prior_plan.status == PlanVersionStatus.SUPERSEDED.value
    assert prior_plan.superseded_by == actor.username
    assert prior_plan.superseded_at is not None
    assert new_plan.previous_plan_version_id == prior_plan.plan_version_id

    # New plan is approved
    assert new_plan.status == PlanVersionStatus.APPROVED.value
    assert new_plan.approved_by == actor.username
