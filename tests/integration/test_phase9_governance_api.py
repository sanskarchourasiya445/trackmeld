"""Integration tests for Phase 9: Plan Versions, Human Review, Approval Gating, and Audit API."""

import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timezone
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


async def _insert_completed_run(
    db_session: AsyncSession,
    scenario_id: str = "SCN-DEMO-001",
    status: str = "COMPLETED",
    validation_status: str = "VALID",
    is_approvable: bool = True,
    error_count: int = 0,
) -> PlanningRunModel:
    """Helper to persist a certified, completed planning run record."""
    now = datetime.now(timezone.utc)
    run_id = f"RUN-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    fingerprint = uuid.uuid4().hex + uuid.uuid4().hex
    snap_hash = "a" * 64
    inp_hash = "b" * 64

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
        completed_at=now if status == "COMPLETED" else None,
    )
    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)
    return run


@pytest.mark.asyncio
async def test_create_plan_version_from_completed_run(client: AsyncClient, db_session: AsyncSession):
    """Promoting a certified completed run creates a candidate PlanVersion (201 Created)."""
    run = await _insert_completed_run(db_session)
    run_id = run.run_id

    headers = {"Authorization": "Bearer planner-token-2026"}
    payload = {"comment": "Initial candidate plan for corridor review"}

    resp = await client.post(f"/api/v1/planning-runs/{run_id}/plan-version", json=payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()

    assert data["plan_version_id"].startswith("PV-")
    assert data["planning_run_id"] == run_id
    assert data["scenario_id"] == "SCN-DEMO-001"
    assert data["version_number"] == 1
    assert data["status"] == "PENDING_REVIEW"
    assert data["is_approvable"] is True
    assert data["validation_status"] == "VALID"
    assert len(data["schedule_identity"]) == 64
    assert data["created_by"] == "senior_planner_dli"

    plan_id = data["plan_version_id"]

    # Duplicate creation returns 409 Conflict
    resp_dup = await client.post(f"/api/v1/planning-runs/{run_id}/plan-version", json=payload, headers=headers)
    assert resp_dup.status_code == 409
    assert resp_dup.json()["error"]["code"] == "PLAN_ALREADY_EXISTS"

    # Detail endpoint returns complete record
    resp_detail = await client.get(f"/api/v1/plan-versions/{plan_id}", headers=headers)
    assert resp_detail.status_code == 200
    assert resp_detail.json()["plan_version_id"] == plan_id


@pytest.mark.asyncio
async def test_create_plan_version_uncompleted_run_blocked(client: AsyncClient, db_session: AsyncSession):
    """Attempting to promote an uncompleted or running run is blocked with 422."""
    run = await _insert_completed_run(db_session, status="RUNNING")
    run_id = run.run_id

    headers = {"Authorization": "Bearer planner-token-2026"}
    resp_pv = await client.post(f"/api/v1/planning-runs/{run_id}/plan-version", headers=headers)
    assert resp_pv.status_code == 422
    assert resp_pv.json()["error"]["code"] == "APPROVAL_BLOCKED"


@pytest.mark.asyncio
async def test_plan_review_and_comments_workflow(client: AsyncClient, db_session: AsyncSession):
    """Review workflow: Transition to UNDER_REVIEW and append comments."""
    run = await _insert_completed_run(db_session)
    run_id = run.run_id

    headers = {"Authorization": "Bearer planner-token-2026"}
    resp_pv = await client.post(f"/api/v1/planning-runs/{run_id}/plan-version", headers=headers)
    plan_id = resp_pv.json()["plan_version_id"]

    # 1. Start review
    resp_rev = await client.post(
        f"/api/v1/plan-versions/{plan_id}/review",
        json={"comment": "Starting detailed timetable clearance inspection."},
        headers=headers,
    )
    assert resp_rev.status_code == 200
    assert resp_rev.json()["status"] == "UNDER_REVIEW"
    assert resp_rev.json()["reviewed_by"] == "senior_planner_dli"

    # 2. Add review commentary
    comment_payload = {"comment": "Freight slots 12056 and 14002 cleared without conflict."}
    resp_comm = await client.post(
        f"/api/v1/plan-versions/{plan_id}/comments",
        json=comment_payload,
        headers=headers,
    )
    assert resp_comm.status_code == 201
    comm_data = resp_comm.json()
    assert comm_data["action"] == "COMMENT"
    assert comm_data["actor_username"] == "senior_planner_dli"
    assert comm_data["comment"] == comment_payload["comment"]

    # 3. Check audit trail
    resp_audit = await client.get(f"/api/v1/plan-versions/{plan_id}/audit", headers=headers)
    assert resp_audit.status_code == 200
    events = resp_audit.json()
    event_types = [e["event_type"] for e in events]
    assert "PLAN_VERSION_CREATED" in event_types
    assert "PLAN_REVIEW_STARTED" in event_types
    assert "PLAN_COMMENT_ADDED" in event_types


@pytest.mark.asyncio
async def test_rbac_and_plan_approval_and_supersede(client: AsyncClient, db_session: AsyncSession):
    """Approval gating: Only approver role can approve; previous approved plan is superseded."""
    run1 = await _insert_completed_run(db_session)
    run_id_1 = run1.run_id

    planner_headers = {"Authorization": "Bearer planner-token-2026"}
    approver_headers = {"Authorization": "Bearer approver-token-2026"}
    viewer_headers = {"Authorization": "Bearer viewer-token-2026"}

    # Create v1
    resp_pv1 = await client.post(f"/api/v1/planning-runs/{run_id_1}/plan-version", headers=planner_headers)
    plan_id_1 = resp_pv1.json()["plan_version_id"]

    # 1. Viewer cannot approve (403)
    resp_view_appr = await client.post(f"/api/v1/plan-versions/{plan_id_1}/approve", headers=viewer_headers)
    assert resp_view_appr.status_code == 403

    # 2. Planner cannot approve (403)
    resp_plan_appr = await client.post(f"/api/v1/plan-versions/{plan_id_1}/approve", headers=planner_headers)
    assert resp_plan_appr.status_code == 403

    # 3. Approver approves v1 (200 OK)
    appr_payload = {"comment": "Authorized formal approval for weekly maintenance window."}
    resp_appr1 = await client.post(
        f"/api/v1/plan-versions/{plan_id_1}/approve",
        json=appr_payload,
        headers=approver_headers,
    )
    assert resp_appr1.status_code == 200
    data1 = resp_appr1.json()
    assert data1["status"] == "APPROVED"
    assert data1["approved_by"] == "divisional_operations_manager"
    assert data1["approved_at"] is not None

    # 4. Immutability: Cannot re-approve or reject an approved plan
    resp_re_appr = await client.post(f"/api/v1/plan-versions/{plan_id_1}/approve", headers=approver_headers)
    assert resp_re_appr.status_code == 409
    assert resp_re_appr.json()["error"]["code"] == "PLAN_IMMUTABLE"

    resp_reject_appr = await client.post(
        f"/api/v1/plan-versions/{plan_id_1}/reject",
        json={"reason": "Cannot reject approved plan directly."},
        headers=approver_headers,
    )
    assert resp_reject_appr.status_code == 409
    assert resp_reject_appr.json()["error"]["code"] == "PLAN_IMMUTABLE"

    # 5. Create v2 from another run
    run2 = await _insert_completed_run(db_session)
    run_id_2 = run2.run_id
    resp_pv2 = await client.post(f"/api/v1/planning-runs/{run_id_2}/plan-version", headers=planner_headers)
    plan_id_2 = resp_pv2.json()["plan_version_id"]
    assert resp_pv2.json()["version_number"] == 2

    # 6. Approving v2 automatically supersedes v1
    resp_appr2 = await client.post(
        f"/api/v1/plan-versions/{plan_id_2}/approve",
        json={"comment": "Superseding v1 with optimized possession allocation."},
        headers=approver_headers,
    )
    assert resp_appr2.status_code == 200
    assert resp_appr2.json()["status"] == "APPROVED"
    assert resp_appr2.json()["previous_plan_version_id"] == plan_id_1

    # Check v1 status is now SUPERSEDED
    resp_v1_check = await client.get(f"/api/v1/plan-versions/{plan_id_1}", headers=approver_headers)
    assert resp_v1_check.status_code == 200
    assert resp_v1_check.json()["status"] == "SUPERSEDED"
    assert resp_v1_check.json()["superseded_by"] == "divisional_operations_manager"


@pytest.mark.asyncio
async def test_plan_rejection_workflow(client: AsyncClient, db_session: AsyncSession):
    """Explicit human rejection requires mandatory justification and records audit trail."""
    run = await _insert_completed_run(db_session)
    run_id = run.run_id

    planner_headers = {"Authorization": "Bearer planner-token-2026"}
    approver_headers = {"Authorization": "Bearer approver-token-2026"}

    resp_pv = await client.post(f"/api/v1/planning-runs/{run_id}/plan-version", headers=planner_headers)
    plan_id = resp_pv.json()["plan_version_id"]

    # 1. Rejection without substantive reason fails (422)
    resp_bad_rej = await client.post(
        f"/api/v1/plan-versions/{plan_id}/reject",
        json={"reason": "bad"},
        headers=approver_headers,
    )
    assert resp_bad_rej.status_code == 422

    # 2. Authorized rejection with valid reason succeeds
    reason = "Excessive track possession clash with heavy grain freight corridor."
    resp_rej = await client.post(
        f"/api/v1/plan-versions/{plan_id}/reject",
        json={"reason": reason},
        headers=approver_headers,
    )
    assert resp_rej.status_code == 200
    rej_data = resp_rej.json()
    assert rej_data["status"] == "REJECTED"
    assert rej_data["rejected_by"] == "divisional_operations_manager"
    assert rej_data["rejection_reason"] == reason

    # 3. Cannot resurrect or approve a rejected plan (409)
    resp_re_appr = await client.post(f"/api/v1/plan-versions/{plan_id}/approve", headers=approver_headers)
    assert resp_re_appr.status_code == 409


@pytest.mark.asyncio
async def test_list_plan_versions_filtering(client: AsyncClient, db_session: AsyncSession):
    """GET /api/v1/plan-versions supports scenario and status filters."""
    run = await _insert_completed_run(db_session)
    run_id = run.run_id
    headers = {"Authorization": "Bearer planner-token-2026"}

    await client.post(f"/api/v1/planning-runs/{run_id}/plan-version", headers=headers)

    resp = await client.get("/api/v1/plan-versions?scenario_id=SCN-DEMO-001&status=PENDING_REVIEW", headers=headers)
    assert resp.status_code == 200
    assert "x-total-count" in resp.headers
    plans = resp.json()
    assert len(plans) == 1
    assert plans[0]["scenario_id"] == "SCN-DEMO-001"
    assert plans[0]["status"] == "PENDING_REVIEW"
