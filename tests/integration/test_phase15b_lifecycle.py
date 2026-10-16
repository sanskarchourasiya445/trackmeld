"""Phase 15B Integration Tests: End-to-End Planning & Governance Lifecycle.

Proves the complete decision-support boundary:
scenario -> run requisition -> worker claim -> CP-SAT optimization ->
independent validation -> COMPLETED -> plan version creation ->
human review -> human approval -> immutable audit trail.

CRITICAL INVARIANT PROVEN:
COMPLETED != APPROVED
A completed planning run does NOT automatically create an approved plan version.
"""

import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from backend.app.config import get_settings
from backend.app.services.planning_worker import PlanningRunWorker
from backend.app.db.models.planning_run import PlanningRunModel
from backend.app.db.models.plan_version import (
    PlanVersionModel,
    PlanReviewCommentModel,
    GovernanceAuditEventModel,
)
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


@pytest.mark.asyncio
async def test_e2e_lifecycle_and_completed_not_approved_invariant(
    client: AsyncClient,
    db_session: AsyncSession,
    test_session_factory,
):
    """End-to-end proof: Requisition -> Worker Solve -> Validation -> COMPLETED -> Human Review -> Approval.
    
    Verifies that COMPLETED run strictly does NOT create an APPROVED plan.
    """
    # -------------------------------------------------------------------------
    # 1. Submit Planning Run Requisition
    # -------------------------------------------------------------------------
    planner_headers = {"Authorization": "Bearer planner-token-2026"}
    approver_headers = {"Authorization": "Bearer approver-token-2026"}

    req_payload = {
        "scenario_id": "SCN-REAL-OPERATIONAL-001",
        "scheduler_type": "CP_SAT",
        "time_limit_seconds": 10.0,
        "num_search_workers": 1,
        "random_seed": 42,
        "validate_after_solve": True,
    }
    resp_create = await client.post("/api/v1/planning-runs", json=req_payload, headers=planner_headers)
    assert resp_create.status_code == 201
    run_id = resp_create.json()["run_id"]

    # Verify initial persisted state is QUEUED / PENDING
    stmt_run = select(PlanningRunModel).where(PlanningRunModel.run_id == run_id)
    run_db = (await db_session.execute(stmt_run)).scalar_one()
    assert run_db.status == "PENDING"
    assert run_db.stage == "QUEUED"

    # -------------------------------------------------------------------------
    # 2. Worker Claims and Executes Optimization & Validation
    # -------------------------------------------------------------------------
    worker = PlanningRunWorker(worker_id="INTEGRATION-WORKER-01", session_factory=test_session_factory)
    claimed = await worker.run_once()
    assert claimed is True

    # Re-fetch run from DB
    await db_session.refresh(run_db)
    assert run_db.status == "COMPLETED"
    assert run_db.stage == "COMPLETED"
    assert run_db.worker_id == "INTEGRATION-WORKER-01"
    assert run_db.validation_status == "VALID"
    assert run_db.is_approvable is True
    assert run_db.validation_fingerprint is not None

    # -------------------------------------------------------------------------
    # CRITICAL INVARIANT ASSERTION: COMPLETED != APPROVED
    # -------------------------------------------------------------------------
    # At this point, the solver and validator have finished.
    # Assert that NO PlanVersionModel exists yet.
    stmt_versions = select(PlanVersionModel).where(PlanVersionModel.planning_run_id == run_id)
    versions_after_solve = (await db_session.execute(stmt_versions)).scalars().all()
    assert len(versions_after_solve) == 0, "INVARIANT VIOLATION: Optimization completion must NOT create a PlanVersion!"

    # -------------------------------------------------------------------------
    # 3. Human Planner Creates PlanVersion Candidate (PENDING_REVIEW)
    # -------------------------------------------------------------------------
    pv_payload = {"comment": "Formal block proposal for Delhi-Ghaziabad section."}
    resp_pv = await client.post(
        f"/api/v1/planning-runs/{run_id}/plan-version",
        json=pv_payload,
        headers=planner_headers,
    )
    assert resp_pv.status_code == 201
    pv_data = resp_pv.json()
    pv_id = pv_data["plan_version_id"]

    # Verify plan version is PENDING_REVIEW, NOT APPROVED
    assert pv_data["status"] == "PENDING_REVIEW"
    assert pv_data["version_number"] == 1
    assert pv_data["is_approvable"] is True

    # Verify audit event recorded for PLAN_VERSION_CREATED
    stmt_audit = select(GovernanceAuditEventModel).where(GovernanceAuditEventModel.entity_id == pv_id)
    events = (await db_session.execute(stmt_audit)).scalars().all()
    assert len(events) == 1
    assert events[0].event_type == GovernanceEventType.PLAN_VERSION_CREATED.value
    assert events[0].actor_username == "senior_planner_dli"

    # -------------------------------------------------------------------------
    # 4. Operations Officer Starts Human Review (UNDER_REVIEW)
    # -------------------------------------------------------------------------
    resp_review = await client.post(
        f"/api/v1/plan-versions/{pv_id}/review",
        json={"comment": "Reviewing corridor capacity impact against freight timetable."},
        headers=approver_headers,
    )
    assert resp_review.status_code == 200
    assert resp_review.json()["status"] == "UNDER_REVIEW"

    # -------------------------------------------------------------------------
    # 5. Operations Officer Formally Approves Plan
    # -------------------------------------------------------------------------
    approve_payload = {
        "approval_notes": "Possession approved with electric traction isolation confirmed.",
        "declared_reviewer_name": "Shri V. K. Malhotra",
        "declared_reviewer_role": "Chief Operations Manager (Coaching)",
    }
    resp_appr = await client.post(
        f"/api/v1/plan-versions/{pv_id}/approve",
        json=approve_payload,
        headers=approver_headers,
    )
    assert resp_appr.status_code == 200
    appr_data = resp_appr.json()

    assert appr_data["status"] == "APPROVED"
    assert appr_data["approved_by"] == "divisional_operations_manager"
    assert appr_data["approved_at"] is not None

    # -------------------------------------------------------------------------
    # 6. Verify Transactional Audit Trail and Metadata Persistence
    # -------------------------------------------------------------------------
    stmt_all_audit = (
        select(GovernanceAuditEventModel)
        .where(GovernanceAuditEventModel.entity_id == pv_id)
        .order_by(GovernanceAuditEventModel.timestamp.asc())
    )
    audit_records = (await db_session.execute(stmt_all_audit)).scalars().all()
    assert len(audit_records) == 3

    event_types = [e.event_type for e in audit_records]
    assert event_types == [
        GovernanceEventType.PLAN_VERSION_CREATED.value,
        GovernanceEventType.PLAN_REVIEW_STARTED.value,
        GovernanceEventType.PLAN_APPROVED.value,
    ]

    # Verify declared reviewer metadata stored in PLAN_APPROVED audit event
    approved_event = audit_records[2]
    assert approved_event.actor_username == "divisional_operations_manager"
    assert approved_event.event_metadata["declared_reviewer"]["name"] == "Shri V. K. Malhotra"
    assert approved_event.event_metadata["declared_reviewer"]["role"] == "Chief Operations Manager (Coaching)"


@pytest.mark.asyncio
async def test_synthetic_scenario_completed_cannot_be_approved_gov001(
    client: AsyncClient,
    db_session: AsyncSession,
    test_session_factory,
):
    """GOV-001: Completed run on synthetic scenario SCN-DEMO-001 can create candidate but CANNOT receive operational approval."""
    planner_headers = {"Authorization": "Bearer planner-token-2026"}
    approver_headers = {"Authorization": "Bearer approver-token-2026"}

    # 1. Submit planning run requisition for synthetic scenario
    req_payload = {
        "scenario_id": "SCN-DEMO-001",
        "scheduler_type": "CP_SAT",
        "time_limit_seconds": 10.0,
        "num_search_workers": 1,
        "random_seed": 42,
        "validate_after_solve": True,
    }
    resp_create = await client.post("/api/v1/planning-runs", json=req_payload, headers=planner_headers)
    assert resp_create.status_code == 201
    run_id = resp_create.json()["run_id"]

    # 2. Worker executes optimization & validation
    worker = PlanningRunWorker(worker_id="INTEGRATION-WORKER-02", session_factory=test_session_factory)
    claimed = await worker.run_once()
    assert claimed is True

    # 3. Promote completed synthetic run to PlanVersion candidate
    resp_pv = await client.post(
        f"/api/v1/planning-runs/{run_id}/plan-version",
        json={"comment": "Synthetic candidate block proposal"},
        headers=planner_headers,
    )
    assert resp_pv.status_code == 201
    pv_id = resp_pv.json()["plan_version_id"]

    # 4. Review synthetic plan version
    resp_review = await client.post(
        f"/api/v1/plan-versions/{pv_id}/review",
        json={"comment": "Reviewing synthetic corridor proposal"},
        headers=approver_headers,
    )
    assert resp_review.status_code == 200

    # 5. Formal operational approval MUST be blocked by GOV-001 Precondition 8
    approve_payload = {
        "approval_notes": "Attempting operational approval on synthetic scenario.",
        "declared_reviewer_name": "Shri V. K. Malhotra",
        "declared_reviewer_role": "Chief Operations Manager (Coaching)",
    }
    resp_appr = await client.post(
        f"/api/v1/plan-versions/{pv_id}/approve",
        json=approve_payload,
        headers=approver_headers,
    )
    assert resp_appr.status_code == 422
    err = resp_appr.json()["error"]
    assert err["code"] == "APPROVAL_BLOCKED"
    assert "SYNTHETIC" in err["message"]
    assert "Synthetic, demonstration, or assumed scenarios cannot be approved" in err["message"]

    # 6. Verify zero state mutation in database
    stmt_pv = select(PlanVersionModel).where(PlanVersionModel.plan_version_id == pv_id)
    pv_db = (await db_session.execute(stmt_pv)).scalar_one()
    assert pv_db.status == PlanVersionStatus.UNDER_REVIEW
    assert pv_db.approved_by is None
    assert pv_db.approved_at is None
