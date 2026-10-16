"""Unit and API-level tests for Reviewer Identity, Role Validation, and Authorization Enforcement (F5 / GOV-005).

Safety & Governance Invariants:
1. Role-based authorization: Review requires 'plan:review' permission; approval requires 'plan:approve' permission.
2. Non-authoritative client metadata: `declared_reviewer_name` and `declared_reviewer_role` are non-authoritative
   audit metadata and CANNOT grant permissions or override server-authenticated identity.
3. Fail-closed role checks: Callers with unauthorized roles (VIEWER, MAINTENANCE_PLANNER on approval, RESTRICTED_EXTERNAL)
   are strictly rejected at both HTTP route layer (HTTP 403) and service layer (PlanVersionApprovalBlockedError).
4. Unauthenticated callers are rejected with HTTP 401 Unauthorized in production mode.
5. Max length boundaries: Pydantic rejects oversized declared reviewer metadata (HTTP 422).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.core.auth import AuthUser, UserRole, require_permission
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
    plan.approved_by = None
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


def _configure_service_mocks(
    service: PlanGovernanceService,
    plan: PlanVersionModel,
) -> None:
    run = MagicMock(spec=PlanningRunModel)
    run.run_id = plan.planning_run_id
    run.scenario_id = plan.scenario_id
    run.snapshot_id = "SNAP-TEST-001"
    run.snapshot_hash = plan.snapshot_hash
    run.input_hash = plan.input_hash
    run.validation_fingerprint = plan.schedule_identity
    run.validation_status = "VALID"
    run.is_approvable = True
    run.dataset_version = plan.dataset_version
    run.schedule_result = plan.schedule_result
    run.status = "COMPLETED"

    scenario = MagicMock(spec=OperationalScenarioModel)
    scenario.scenario_id = plan.scenario_id
    scenario.classification = DataClass.REAL
    scenario.dataset_version = plan.dataset_version

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
    snap.snapshot_id = "SNAP-TEST-001"
    snap.compute_snapshot_hash = MagicMock(return_value=plan.snapshot_hash)
    snap.compute_input_hash = MagicMock(return_value=plan.input_hash)
    service.scenario_repo.get_snapshot = AsyncMock(return_value=snap)


# =============================================================================
# 1. SERVICE LAYER ROLE AUTHORIZATION TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_f5_viewer_role_blocked_from_approving_at_service_layer():
    """Viewer role lacks 'plan:approve' permission and is blocked from approval."""
    service = PlanGovernanceService(AsyncMock())
    plan = _build_test_plan(created_by="planner_officer")
    _configure_service_mocks(service, plan)

    viewer_actor = AuthUser(
        user_id="USR-VIEW-01",
        username="guest_auditor",
        role=UserRole.VIEWER,
        permissions=["read:reference", "read:operational"],
    )

    with pytest.raises(PlanVersionApprovalBlockedError, match="lacks required permission 'plan:approve'"):
        await service.approve_plan(plan.plan_version_id, viewer_actor)


@pytest.mark.asyncio
async def test_f5_planner_role_blocked_from_approving_at_service_layer():
    """Maintenance Planner lacks 'plan:approve' permission and is blocked from approval."""
    service = PlanGovernanceService(AsyncMock())
    plan = _build_test_plan(created_by="other_planner")
    _configure_service_mocks(service, plan)

    planner_actor = AuthUser(
        user_id="USR-PLAN-02",
        username="another_planner",
        role=UserRole.MAINTENANCE_PLANNER,
        permissions=["read:reference", "read:operational", "write:operational", "plan:review"],
    )

    with pytest.raises(PlanVersionApprovalBlockedError, match="lacks required permission 'plan:approve'"):
        await service.approve_plan(plan.plan_version_id, planner_actor)


@pytest.mark.asyncio
async def test_f5_viewer_role_blocked_from_reviewing_at_service_layer():
    """Viewer role lacks 'plan:review' permission and is blocked from starting review."""
    service = PlanGovernanceService(AsyncMock())
    plan = _build_test_plan(created_by="planner_officer")
    _configure_service_mocks(service, plan)

    viewer_actor = AuthUser(
        user_id="USR-VIEW-01",
        username="guest_auditor",
        role=UserRole.VIEWER,
        permissions=["read:reference", "read:operational"],
    )

    with pytest.raises(PlanVersionApprovalBlockedError, match="lacks required permission 'plan:review'"):
        await service.start_review(plan.plan_version_id, viewer_actor)


# =============================================================================
# 2. CLIENT-DECLARED METADATA CANNOT GRANT AUTHORITY
# =============================================================================

@pytest.mark.asyncio
async def test_f5_declared_role_cannot_grant_approval_authority_to_unauthorized_actor():
    """Supplying declared_reviewer_role='OPERATOR' CANNOT grant authority to an unauthorized caller."""
    service = PlanGovernanceService(AsyncMock())
    plan = _build_test_plan(created_by="planner_officer")
    _configure_service_mocks(service, plan)

    unauthorized_actor = AuthUser(
        user_id="USR-VIEW-01",
        username="viewer_user",
        role=UserRole.VIEWER,
        permissions=["read:reference", "read:operational"],
    )

    # Actor attempts to claim authority via free-text declared metadata
    with pytest.raises(PlanVersionApprovalBlockedError, match="lacks required permission 'plan:approve'"):
        await service.approve_plan(
            plan.plan_version_id,
            unauthorized_actor,
            declared_reviewer_name="Shri V. K. Malhotra",
            declared_reviewer_role="OPERATOR",
        )


@pytest.mark.asyncio
async def test_f5_declared_name_does_not_override_authenticated_approver_attribution():
    """Approved plan strictly records authenticated actor.username, never declared_reviewer_name."""
    service = PlanGovernanceService(AsyncMock())
    plan = _build_test_plan(created_by="planner_officer")
    _configure_service_mocks(service, plan)

    approver = AuthUser(
        user_id="USR-APPR-01",
        username="divisional_operations_manager",
        role=UserRole.OPERATOR,
        permissions=["read:reference", "read:operational", "plan:review", "plan:approve"],
    )

    approved = await service.approve_plan(
        plan.plan_version_id,
        approver,
        declared_reviewer_name="Declared Ghost Reviewer",
        declared_reviewer_role="Chief Signatory",
    )

    # Core invariant: Server authenticated identity is strictly authoritative
    assert approved.approved_by == "divisional_operations_manager"
    assert approved.approved_by != "Declared Ghost Reviewer"

    # Audit event records declared metadata with is_authoritative: False
    audit_call = service.plan_repo.add_audit_event.call_args[0][0]
    assert audit_call.actor_username == "divisional_operations_manager"
    assert audit_call.event_metadata["declared_reviewer"]["name"] == "Declared Ghost Reviewer"
    assert audit_call.event_metadata["declared_reviewer"]["role"] == "Chief Signatory"
    assert audit_call.event_metadata["declared_reviewer"]["is_authoritative"] is False


@pytest.mark.asyncio
async def test_f5_whitespace_sanitization_on_declared_reviewer_metadata():
    """Whitespace-only declared metadata normalizes to None; padded whitespace is trimmed."""
    service = PlanGovernanceService(AsyncMock())
    plan = _build_test_plan(created_by="planner_officer")
    _configure_service_mocks(service, plan)

    approver = AuthUser(
        user_id="USR-APPR-01",
        username="divisional_operations_manager",
        role=UserRole.OPERATOR,
        permissions=["plan:approve"],
    )

    await service.approve_plan(
        plan.plan_version_id,
        approver,
        declared_reviewer_name="  Shri A. P. Singh  ",
        declared_reviewer_role="   ",  # Blank -> None
    )

    audit_call = service.plan_repo.add_audit_event.call_args[0][0]
    assert audit_call.event_metadata["declared_reviewer"]["name"] == "Shri A. P. Singh"
    assert audit_call.event_metadata["declared_reviewer"]["role"] is None


# =============================================================================
# 3. HTTP API-LEVEL AUTHORIZATION TESTS (FastAPI TestClient)
# =============================================================================

@pytest.fixture
def api_client():
    return TestClient(app)


def test_f5_api_approve_endpoint_forbidden_for_viewer_token(api_client):
    """POST /plan-versions/{id}/approve rejects VIEWER token with HTTP 403 Forbidden."""
    headers = {"Authorization": "Bearer viewer-token-2026"}
    payload = {
        "comment": "Attempted approval by viewer",
        "declared_reviewer_name": "Chief Operations Manager",
        "declared_reviewer_role": "ADMIN",
    }
    resp = api_client.post("/api/v1/plan-versions/PV-TEST-001/approve", json=payload, headers=headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"
    assert "plan:approve" in resp.json()["error"]["message"]


def test_f5_api_approve_endpoint_forbidden_for_planner_token(api_client):
    """POST /plan-versions/{id}/approve rejects MAINTENANCE_PLANNER token with HTTP 403 Forbidden."""
    headers = {"Authorization": "Bearer planner-token-2026"}
    payload = {"comment": "Attempted approval by planner"}
    resp = api_client.post("/api/v1/plan-versions/PV-TEST-001/approve", json=payload, headers=headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"
    assert "plan:approve" in resp.json()["error"]["message"]


def test_f5_api_review_endpoint_forbidden_for_viewer_token(api_client):
    """POST /plan-versions/{id}/review rejects VIEWER token with HTTP 403 Forbidden."""
    headers = {"Authorization": "Bearer viewer-token-2026"}
    resp = api_client.post("/api/v1/plan-versions/PV-TEST-001/review", json={}, headers=headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"
    assert "plan:review" in resp.json()["error"]["message"]


def test_f5_api_review_endpoint_forbidden_for_restricted_token(api_client):
    """POST /plan-versions/{id}/review rejects RESTRICTED_EXTERNAL token with HTTP 403 Forbidden."""
    headers = {"Authorization": "Bearer restricted-token-2026"}
    resp = api_client.post("/api/v1/plan-versions/PV-TEST-001/review", json={}, headers=headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"
    assert "plan:review" in resp.json()["error"]["message"]


def test_f5_api_declared_reviewer_name_exceeding_max_length_rejected(api_client):
    """POST /plan-versions/{id}/approve rejects declared_reviewer_name > 128 chars with HTTP 422."""
    headers = {"Authorization": "Bearer approver-token-2026"}
    payload = {
        "comment": "Valid approval note",
        "declared_reviewer_name": "X" * 129,  # Exceeds max_length=128
        "declared_reviewer_role": "OPERATOR",
    }
    resp = api_client.post("/api/v1/plan-versions/PV-TEST-001/approve", json=payload, headers=headers)
    assert resp.status_code == 422


def test_f5_api_declared_reviewer_role_exceeding_max_length_rejected(api_client):
    """POST /plan-versions/{id}/approve rejects declared_reviewer_role > 128 chars with HTTP 422."""
    headers = {"Authorization": "Bearer approver-token-2026"}
    payload = {
        "comment": "Valid approval note",
        "declared_reviewer_name": "Valid Name",
        "declared_reviewer_role": "R" * 129,  # Exceeds max_length=128
    }
    resp = api_client.post("/api/v1/plan-versions/PV-TEST-001/approve", json=payload, headers=headers)
    assert resp.status_code == 422
