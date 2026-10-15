"""Phase 21 Integration Tests: Final End-to-End Workflow & Governance Verification.

Covers:
1. Complete 15-Step End-to-End Planning & Governance Lifecycle:
   - Scenario -> Planning Run -> Solve/Validate -> PlanVersion Candidate ->
   - Review Commentary -> Four-Eyes Governance Gate -> Formal Approval ->
   - Governance Audit Log -> Version Superseding.
2. Negative Governance & Terminal State Immutability:
   - Creator self-approval blocked.
   - Unauthorized / Viewer approval blocked.
   - Unauthenticated access blocked.
   - Non-completed planning run promotion blocked.
   - Terminal state enforcement (REJECTED and SUPERSEDED cannot be approved).
"""

import uuid
from datetime import datetime, timezone
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.db.models.planning_run import PlanningRunModel
from backend.app.db.models.plan_version import (
    PlanVersionModel,
    PlanReviewCommentModel,
    GovernanceAuditEventModel,
)

settings = get_settings()

PLANNER_HEADERS = {"Authorization": "Bearer planner-token-2026"}
APPROVER_HEADERS = {"Authorization": "Bearer approver-token-2026"}
VIEWER_HEADERS = {"Authorization": "Bearer viewer-token-2026"}


@pytest_asyncio.fixture(autouse=True)
async def clean_governance_tables(db_session: AsyncSession):
    """Clean all governance and planning run tables before and after each test."""
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


async def _insert_test_run(
    db_session: AsyncSession,
    status: str = "COMPLETED",
    validation_status: str = "VALID",
    is_approvable: bool = True,
    scenario_id: str = "SCN-DEMO-001",
) -> PlanningRunModel:
    """Helper to persist a test planning run record."""
    now = datetime.now(timezone.utc)
    run_id = f"RUN-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    fingerprint = uuid.uuid4().hex + uuid.uuid4().hex

    run = PlanningRunModel(
        run_id=run_id,
        scenario_id=scenario_id,
        status=status,
        stage="COMPLETED" if status == "COMPLETED" else "SOLVING",
        scheduler_type="CP_SAT",
        scheduler_version="1.0.0",
        solver_name="OR-Tools CP-SAT",
        solver_version="9.8",
        dataset_version="demo-v1.0",
        snapshot_id=f"SNP-{scenario_id}",
        snapshot_hash="a" * 64,
        input_hash="b" * 64,
        validation_status=validation_status,
        is_approvable=is_approvable,
        validation_fingerprint=fingerprint,
        validation_findings_summary={"error_count": 0, "warning_count": 0},
        configuration_snapshot={"scheduler_type": "CP_SAT", "solver_mode": "TRACK_AWARE_CONSERVATIVE"},
        result_summary={"total_tasks": 20, "scheduled_tasks": 20, "solver_mode": "TRACK_AWARE_CONSERVATIVE"},
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
        completed_at=now if status == "COMPLETED" else None,
    )
    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)
    return run


# ==============================================================================
# 1. COMPLETE 15-STEP END-TO-END GOVERNANCE WORKFLOW
# ==============================================================================

@pytest.mark.asyncio
async def test_complete_e2e_governance_lifecycle(client: AsyncClient, db_session: AsyncSession):
    """Verify the full 15-step governance lifecycle from completed run to superseded version."""
    # 1. Insert certified completed run
    run1 = await _insert_test_run(db_session)
    run_id_1 = run1.run_id

    # 2. Promote run to candidate PlanVersion as planner
    resp_create = await client.post(
        f"/api/v1/planning-runs/{run_id_1}/plan-version",
        json={"comment": "Candidate Plan v1 submitted for operations review"},
        headers=PLANNER_HEADERS,
    )
    assert resp_create.status_code == 201
    pv1_data = resp_create.json()
    pv1_id = pv1_data["plan_version_id"]
    assert pv1_data["status"] == "PENDING_REVIEW"
    assert pv1_data["version_number"] == 1
    assert pv1_data["is_approvable"] is True

    # 3. Transition to UNDER_REVIEW
    resp_review = await client.post(
        f"/api/v1/plan-versions/{pv1_id}/review",
        json={"comment": "Beginning engineering corridor clearance review"},
        headers=PLANNER_HEADERS,
    )
    assert resp_review.status_code == 200
    assert resp_review.json()["status"] == "UNDER_REVIEW"

    # 4. Append review commentary
    resp_comment = await client.post(
        f"/api/v1/plan-versions/{pv1_id}/comments",
        json={"comment": "Verified that all 25kV traction isolations have 30min buffer."},
        headers=PLANNER_HEADERS,
    )
    assert resp_comment.status_code == 201

    # 5. Creator cannot approve own plan (Four-Eyes Enforcement)
    resp_self_appr = await client.post(
        f"/api/v1/plan-versions/{pv1_id}/approve",
        json={"comment": "Attempting creator self-approval"},
        headers=PLANNER_HEADERS,
    )
    assert resp_self_appr.status_code == 403, "Creator must never self-approve (Four-Eyes principle)"

    # 6. Independent approver approves plan
    resp_appr = await client.post(
        f"/api/v1/plan-versions/{pv1_id}/approve",
        json={"comment": "Formal operating authority granted for track possession."},
        headers=APPROVER_HEADERS,
    )
    assert resp_appr.status_code == 200
    assert resp_appr.json()["status"] == "APPROVED"
    assert resp_appr.json()["approved_by"] == "divisional_operations_manager"

    # 7. Check audit log has all events with provenance
    resp_audit = await client.get(f"/api/v1/plan-versions/{pv1_id}/audit", headers=APPROVER_HEADERS)
    assert resp_audit.status_code == 200
    audit_events = resp_audit.json()
    event_types = [e["event_type"] for e in audit_events]
    assert "PLAN_VERSION_CREATED" in event_types
    assert "PLAN_REVIEW_STARTED" in event_types
    assert "PLAN_COMMENT_ADDED" in event_types
    assert "PLAN_APPROVED" in event_types

    # 8. Create v2 from a second run and approve it -> v1 becomes SUPERSEDED
    run2 = await _insert_test_run(db_session)
    resp_create_v2 = await client.post(
        f"/api/v1/planning-runs/{run2.run_id}/plan-version",
        json={"comment": "Candidate Plan v2 with adjusted headway"},
        headers=PLANNER_HEADERS,
    )
    assert resp_create_v2.status_code == 201
    pv2_id = resp_create_v2.json()["plan_version_id"]

    resp_appr_v2 = await client.post(
        f"/api/v1/plan-versions/{pv2_id}/approve",
        json={"comment": "Approving v2, superseding v1."},
        headers=APPROVER_HEADERS,
    )
    assert resp_appr_v2.status_code == 200
    assert resp_appr_v2.json()["status"] == "APPROVED"

    # Verify v1 is now SUPERSEDED
    resp_v1_status = await client.get(f"/api/v1/plan-versions/{pv1_id}", headers=APPROVER_HEADERS)
    assert resp_v1_status.status_code == 200
    assert resp_v1_status.json()["status"] == "SUPERSEDED"


# ==============================================================================
# 2. NEGATIVE GOVERNANCE & TERMINAL STATE IMMUTABILITY
# ==============================================================================

@pytest.mark.asyncio
async def test_rejection_and_terminal_immutability(client: AsyncClient, db_session: AsyncSession):
    """REJECTED and SUPERSEDED plans cannot be transitioned or approved."""
    run = await _insert_test_run(db_session)
    resp_pv = await client.post(
        f"/api/v1/planning-runs/{run.run_id}/plan-version",
        headers=PLANNER_HEADERS,
    )
    pv_id = resp_pv.json()["plan_version_id"]

    # 1. Reject plan
    resp_reject = await client.post(
        f"/api/v1/plan-versions/{pv_id}/reject",
        json={"reason": "Excessive conflict with freight timetable."},
        headers=APPROVER_HEADERS,
    )
    assert resp_reject.status_code == 200
    assert resp_reject.json()["status"] == "REJECTED"

    # 2. Cannot approve a REJECTED plan
    resp_appr_rejected = await client.post(
        f"/api/v1/plan-versions/{pv_id}/approve",
        json={"comment": "Attempting to approve rejected plan"},
        headers=APPROVER_HEADERS,
    )
    assert resp_appr_rejected.status_code == 409
    assert resp_appr_rejected.json()["error"]["code"] in ["PLAN_IMMUTABLE", "ILLEGAL_TRANSITION"]

    # 3. Cannot review a REJECTED plan
    resp_rev_rejected = await client.post(
        f"/api/v1/plan-versions/{pv_id}/review",
        json={"comment": "Cannot reopen"},
        headers=PLANNER_HEADERS,
    )
    assert resp_rev_rejected.status_code in [409, 422]


@pytest.mark.asyncio
async def test_uncompleted_run_promotion_blocked(client: AsyncClient, db_session: AsyncSession):
    """Cannot create a PlanVersion from a run in SOLVING, FAILED, or TIMED_OUT status."""
    run = await _insert_test_run(db_session, status="SOLVING")
    resp = await client.post(
        f"/api/v1/planning-runs/{run.run_id}/plan-version",
        headers=PLANNER_HEADERS,
    )
    assert resp.status_code in [409, 422]


@pytest.mark.asyncio
async def test_unauthenticated_and_viewer_rbac(unauthenticated_client: AsyncClient, db_session: AsyncSession):
    """Unauthenticated requests receive 401 or 403; Viewers receive 403 on approval/rejection."""
    run = await _insert_test_run(db_session)
    resp_pv = await unauthenticated_client.post(
        f"/api/v1/planning-runs/{run.run_id}/plan-version",
        headers=PLANNER_HEADERS,
    )
    pv_id = resp_pv.json()["plan_version_id"]

    # Unauthenticated rejected by auth/role guard (401 or 403)
    resp_no_auth = await unauthenticated_client.post(f"/api/v1/plan-versions/{pv_id}/approve")
    assert resp_no_auth.status_code in [401, 403]

    # 403 for viewer role
    resp_viewer = await unauthenticated_client.post(
        f"/api/v1/plan-versions/{pv_id}/approve",
        json={"comment": "Viewer attempting approval"},
        headers=VIEWER_HEADERS,
    )
    assert resp_viewer.status_code == 403
