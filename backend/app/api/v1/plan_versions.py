"""API endpoints for Plan Versions, Human Review, Approval Gating, and Governance Audit.

Exposes:
- POST /api/v1/planning-runs/{run_id}/plan-version: Instantiate candidate PlanVersion from certified run
- POST /api/v1/plan-versions: Alternate endpoint to create PlanVersion with body
- GET  /api/v1/plan-versions/{plan_version_id}: Inspect full plan details, schedule, and review trail
- GET  /api/v1/plan-versions: Paginated list of plan versions with filtering
- POST /api/v1/plan-versions/{plan_version_id}/review: Transition plan candidate to UNDER_REVIEW
- POST /api/v1/plan-versions/{plan_version_id}/comments: Add review commentary entry
- POST /api/v1/plan-versions/{plan_version_id}/approve: Formal human approval by authorized operator
- POST /api/v1/plan-versions/{plan_version_id}/reject: Formal human rejection with mandatory justification
- GET  /api/v1/plan-versions/{plan_version_id}/audit: Immutable chronological governance audit trail
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db_session
from backend.app.core.auth import get_current_user, require_permission, AuthUser
from backend.app.schemas.common import ErrorResponse
from backend.app.schemas.plan_version import (
    PlanVersionStatus,
    CreatePlanVersionRequest,
    ApprovePlanRequest,
    RejectPlanRequest,
    AddReviewCommentRequest,
    PlanReviewCommentResponse,
    AuditEventResponse,
    PlanVersionSummary,
    PlanVersionDetail,
)
from backend.app.db.models.plan_version import PlanVersionModel
from backend.app.repositories.planning_run_repo import PlanningRunNotFoundError
from backend.app.repositories.plan_version_repo import (
    PlanVersionRepository,
    PlanVersionNotFoundError,
    InvalidPlanVersionTransitionError,
    PlanVersionAlreadyExistsError,
    PlanVersionApprovalBlockedError,
    PlanFingerprintMismatchError,
    PlanVersionImmutableError,
)
from backend.app.services.plan_governance_service import PlanGovernanceService

router = APIRouter(tags=["Plan Governance & Human Review"])


class DirectCreatePlanVersionRequest(BaseModel):
    """Payload when creating a plan version via POST /api/v1/plan-versions."""
    planning_run_id: str = Field(..., description="ID of completed, validated planning run")
    comment: Optional[str] = Field(default=None, description="Optional creation context or note")


def _map_to_detail(plan: PlanVersionModel) -> PlanVersionDetail:
    """Map DB PlanVersionModel to public detail response schema."""
    comments = [
        PlanReviewCommentResponse(
            review_id=c.review_id,
            plan_version_id=c.plan_version_id,
            actor_id=c.actor_id,
            actor_username=c.actor_username,
            action=c.action,
            comment=c.comment,
            created_at=c.created_at,
        )
        for c in (plan.review_comments or [])
    ]
    return PlanVersionDetail(
        plan_version_id=plan.plan_version_id,
        scenario_id=plan.scenario_id,
        planning_run_id=plan.planning_run_id,
        version_number=plan.version_number,
        status=PlanVersionStatus(plan.status),
        scheduler_type=plan.scheduler_type,
        scheduler_version=plan.scheduler_version,
        solver_name=plan.solver_name,
        solver_version=plan.solver_version,
        dataset_version=plan.dataset_version,
        schedule_identity=plan.schedule_identity,
        snapshot_hash=plan.snapshot_hash,
        input_hash=plan.input_hash,
        validation_status=plan.validation_status,
        is_approvable=plan.is_approvable,
        validation_findings_summary=plan.validation_findings_summary,
        diagnostics_summary=plan.diagnostics_summary,
        configuration_snapshot=plan.configuration_snapshot or {},
        priority_configuration=plan.priority_configuration,
        optimization_configuration=plan.optimization_configuration,
        result_summary=plan.result_summary or {},
        schedule_result=plan.schedule_result or {},
        created_at=plan.created_at,
        created_by=plan.created_by,
        reviewed_at=plan.reviewed_at,
        reviewed_by=plan.reviewed_by,
        approved_at=plan.approved_at,
        approved_by=plan.approved_by,
        rejected_at=plan.rejected_at,
        rejected_by=plan.rejected_by,
        review_comment=plan.review_comment,
        rejection_reason=plan.rejection_reason,
        previous_plan_version_id=plan.previous_plan_version_id,
        superseded_at=plan.superseded_at,
        superseded_by=plan.superseded_by,
        updated_at=plan.updated_at,
        review_comments=comments,
    )


def _map_to_summary(plan: PlanVersionModel) -> PlanVersionSummary:
    """Map DB PlanVersionModel to public summary response schema."""
    return PlanVersionSummary(
        plan_version_id=plan.plan_version_id,
        scenario_id=plan.scenario_id,
        planning_run_id=plan.planning_run_id,
        version_number=plan.version_number,
        status=PlanVersionStatus(plan.status),
        scheduler_type=plan.scheduler_type,
        schedule_identity=plan.schedule_identity,
        is_approvable=plan.is_approvable,
        validation_status=plan.validation_status,
        result_summary=plan.result_summary or {},
        created_at=plan.created_at,
        created_by=plan.created_by,
        reviewed_at=plan.reviewed_at,
        reviewed_by=plan.reviewed_by,
        approved_at=plan.approved_at,
        approved_by=plan.approved_by,
        rejected_at=plan.rejected_at,
        rejected_by=plan.rejected_by,
        superseded_at=plan.superseded_at,
        superseded_by=plan.superseded_by,
    )


# =============================================================================
# PLAN VERSION CREATION ENDPOINTS
# =============================================================================

@router.post(
    "/planning-runs/{run_id}/plan-version",
    response_model=PlanVersionDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Instantiate a PlanVersion candidate from a certified planning run",
)
async def create_plan_version_from_run(
    run_id: str,
    payload: Optional[CreatePlanVersionRequest] = None,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(require_permission("write:operational")),
):
    service = PlanGovernanceService(session)
    comment = payload.comment if payload else None
    try:
        plan = await service.create_plan_version_from_run(
            run_id=run_id,
            actor=current_user,
            comment=comment,
        )
        return _map_to_detail(plan)
    except PlanningRunNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": str(e)}},
        )
    except PlanVersionAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "PLAN_ALREADY_EXISTS", "message": str(e)}},
        )
    except PlanVersionApprovalBlockedError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": "APPROVAL_BLOCKED", "message": str(e)}},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "INTERNAL_ERROR", "message": str(e)}},
        )


@router.post(
    "/plan-versions",
    response_model=PlanVersionDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create a PlanVersion candidate by planning_run_id",
)
async def create_plan_version(
    payload: DirectCreatePlanVersionRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(require_permission("write:operational")),
):
    service = PlanGovernanceService(session)
    try:
        plan = await service.create_plan_version_from_run(
            run_id=payload.planning_run_id,
            actor=current_user,
            comment=payload.comment,
        )
        return _map_to_detail(plan)
    except PlanningRunNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": str(e)}},
        )
    except PlanVersionAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "PLAN_ALREADY_EXISTS", "message": str(e)}},
        )
    except PlanVersionApprovalBlockedError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": "APPROVAL_BLOCKED", "message": str(e)}},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "INTERNAL_ERROR", "message": str(e)}},
        )


# =============================================================================
# PLAN VERSION QUERY ENDPOINTS
# =============================================================================

@router.get(
    "/plan-versions",
    response_model=List[PlanVersionSummary],
    status_code=status.HTTP_200_OK,
    summary="List plan versions with filtering and pagination",
)
async def list_plan_versions(
    response: Response,
    scenario_id: Optional[str] = None,
    status: Optional[PlanVersionStatus] = None,
    planning_run_id: Optional[str] = None,
    created_by: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(require_permission("read:operational")),
):
    repo = PlanVersionRepository(session)
    total = await repo.count_plan_versions(
        scenario_id=scenario_id,
        status=status,
        planning_run_id=planning_run_id,
        created_by=created_by,
    )
    plans = await repo.list_plan_versions(
        scenario_id=scenario_id,
        status=status,
        planning_run_id=planning_run_id,
        created_by=created_by,
        limit=limit,
        offset=offset,
    )
    response.headers["X-Total-Count"] = str(total)
    return [_map_to_summary(p) for p in plans]


@router.get(
    "/plan-versions/{plan_version_id}",
    response_model=PlanVersionDetail,
    status_code=status.HTTP_200_OK,
    summary="Get detailed plan version including full schedule result and review comments",
)
async def get_plan_version_detail(
    plan_version_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(require_permission("read:operational")),
):
    repo = PlanVersionRepository(session)
    plan = await repo.get_by_plan_version_id(plan_version_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": f"PlanVersion '{plan_version_id}' not found."}},
        )
    return _map_to_detail(plan)


# =============================================================================
# HUMAN REVIEW WORKFLOW ENDPOINTS
# =============================================================================

@router.post(
    "/plan-versions/{plan_version_id}/review",
    response_model=PlanVersionDetail,
    status_code=status.HTTP_200_OK,
    summary="Commence formal human review on a plan candidate",
)
async def start_plan_review(
    plan_version_id: str,
    payload: Optional[CreatePlanVersionRequest] = None,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(require_permission("plan:review")),
):
    service = PlanGovernanceService(session)
    comment = payload.comment if payload else None
    try:
        plan = await service.start_review(plan_version_id, current_user, comment)
        return _map_to_detail(plan)
    except PlanVersionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": str(e)}},
        )
    except InvalidPlanVersionTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "ILLEGAL_TRANSITION", "message": str(e)}},
        )


@router.post(
    "/plan-versions/{plan_version_id}/comments",
    response_model=PlanReviewCommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an operational review comment to a plan version",
)
async def add_review_comment(
    plan_version_id: str,
    payload: AddReviewCommentRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(require_permission("plan:review")),
):
    service = PlanGovernanceService(session)
    try:
        comment_record = await service.add_review_comment(
            plan_version_id=plan_version_id,
            actor=current_user,
            comment_text=payload.comment,
        )
        return PlanReviewCommentResponse(
            review_id=comment_record.review_id,
            plan_version_id=comment_record.plan_version_id,
            actor_id=comment_record.actor_id,
            actor_username=comment_record.actor_username,
            action=comment_record.action,
            comment=comment_record.comment,
            created_at=comment_record.created_at,
        )
    except PlanVersionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": str(e)}},
        )


@router.post(
    "/plan-versions/{plan_version_id}/approve",
    response_model=PlanVersionDetail,
    status_code=status.HTTP_200_OK,
    summary="Formally approve a verified plan candidate (Authorized human operations officers only)",
)
async def approve_plan(
    plan_version_id: str,
    payload: Optional[ApprovePlanRequest] = None,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(require_permission("plan:approve")),
):
    service = PlanGovernanceService(session)
    comment = payload.comment if payload else None
    try:
        plan = await service.approve_plan(plan_version_id, current_user, comment)
        return _map_to_detail(plan)
    except PlanVersionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": str(e)}},
        )
    except PlanVersionImmutableError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "PLAN_IMMUTABLE", "message": str(e)}},
        )
    except InvalidPlanVersionTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "ILLEGAL_TRANSITION", "message": str(e)}},
        )
    except PlanVersionApprovalBlockedError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": "APPROVAL_BLOCKED", "message": str(e)}},
        )
    except PlanFingerprintMismatchError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "INTEGRITY_MISMATCH", "message": str(e)}},
        )


@router.post(
    "/plan-versions/{plan_version_id}/reject",
    response_model=PlanVersionDetail,
    status_code=status.HTTP_200_OK,
    summary="Explicitly reject a plan candidate with mandatory operational justification",
)
async def reject_plan(
    plan_version_id: str,
    payload: RejectPlanRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(require_permission("plan:reject")),
):
    service = PlanGovernanceService(session)
    try:
        plan = await service.reject_plan(plan_version_id, current_user, payload.reason)
        return _map_to_detail(plan)
    except PlanVersionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": str(e)}},
        )
    except PlanVersionImmutableError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "PLAN_IMMUTABLE", "message": str(e)}},
        )
    except InvalidPlanVersionTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "ILLEGAL_TRANSITION", "message": str(e)}},
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "INVALID_ARGUMENT", "message": str(e)}},
        )


# =============================================================================
# AUDIT TRAIL ENDPOINT
# =============================================================================

@router.get(
    "/plan-versions/{plan_version_id}/audit",
    response_model=List[AuditEventResponse],
    status_code=status.HTTP_200_OK,
    summary="Retrieve immutable chronological governance audit trail for a plan version",
)
async def get_plan_audit_trail(
    plan_version_id: str,
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(require_permission("read:operational")),
):
    repo = PlanVersionRepository(session)
    plan = await repo.get_by_plan_version_id(plan_version_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": f"PlanVersion '{plan_version_id}' not found."}},
        )

    events = await repo.list_audit_events(
        entity_id=plan_version_id,
        entity_type="PLAN_VERSION",
        limit=limit,
        offset=offset,
    )
    return [
        AuditEventResponse(
            event_id=e.event_id,
            entity_type=e.entity_type,
            entity_id=e.entity_id,
            event_type=e.event_type,
            actor_id=e.actor_id,
            actor_username=e.actor_username,
            actor_role=e.actor_role,
            timestamp=e.timestamp,
            previous_state=e.previous_state,
            new_state=e.new_state,
            reason=e.reason,
            comment=e.comment,
            schedule_identity=e.schedule_identity,
            snapshot_hash=e.snapshot_hash,
            input_hash=e.input_hash,
            event_metadata=e.event_metadata,
        )
        for e in events
    ]
