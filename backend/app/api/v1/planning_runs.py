"""API endpoints for managing asynchronous planning runs and job lifecycles.

Exposes:
- POST /api/v1/planning-runs: Submit and queue an asynchronous planning job
- GET  /api/v1/planning-runs/{run_id}: Inspect lifecycle, progress, and execution metadata
- GET  /api/v1/planning-runs/{run_id}/result: Retrieve finalized ScheduleResult and audit certificates
- GET  /api/v1/planning-runs: List past and active planning jobs with filtering and pagination
- POST /api/v1/planning-runs/{run_id}/cancel: Request cooperative cancellation
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db_session
from backend.app.core.auth import get_current_user, require_permission, AuthUser
from backend.app.core.rate_limit import enforce_planning_rate_limit
from backend.app.schemas.common import ErrorResponse
from backend.app.schemas.planning_run import (
    PlanningRunStatus,
    PlanningRunStage,
    CreatePlanningRunRequest,
    CreatePlanningRunResponse,
    PlanningRunDetailResponse,
    PlanningRunSummary,
    PlanningRunProgress,
)
from backend.app.domain.scheduling import ScheduleResult
from backend.app.db.models.planning_run import PlanningRunModel
from backend.app.repositories.planning_run_repo import (
    PlanningRunRepository,
    IllegalStateTransitionError,
)
from backend.app.repositories.scenario_repo import ScenarioRepository

router = APIRouter(prefix="/planning-runs", tags=["Planning Jobs & Persistence"])


def _map_to_progress(run: PlanningRunModel) -> PlanningRunProgress:
    """Format human-readable progress telemetry for polling clients."""
    stage_enum = PlanningRunStage(run.stage)
    messages = {
        PlanningRunStage.QUEUED: "Job is queued and waiting for an available worker.",
        PlanningRunStage.CLAIMED: "Worker has claimed the job and is initializing.",
        PlanningRunStage.LOADING_SNAPSHOT: "Loading immutable planning snapshot and validating constraints.",
        PlanningRunStage.SOLVING: f"Executing {run.scheduler_type} optimization search.",
        PlanningRunStage.VALIDATING: "Independent Schedule Validator is verifying all hard constraints.",
        PlanningRunStage.DIAGNOSING: "Executing root-cause diagnostics on unscheduled tasks.",
        PlanningRunStage.PERSISTING: "Persisting final schedule and certification.",
        PlanningRunStage.COMPLETED: "Planning execution completed and verified.",
        PlanningRunStage.FAILED: f"Execution failed: {run.error_message or 'Unknown error'}",
        PlanningRunStage.CANCELLED: "Planning run was cancelled by user.",
        PlanningRunStage.TIMED_OUT: "Planning run timed out.",
    }
    percent_map = {
        PlanningRunStage.QUEUED: 0.0,
        PlanningRunStage.CLAIMED: 10.0,
        PlanningRunStage.LOADING_SNAPSHOT: 25.0,
        PlanningRunStage.SOLVING: 60.0,
        PlanningRunStage.VALIDATING: 85.0,
        PlanningRunStage.DIAGNOSING: 90.0,
        PlanningRunStage.PERSISTING: 95.0,
        PlanningRunStage.COMPLETED: 100.0,
        PlanningRunStage.FAILED: 100.0,
        PlanningRunStage.CANCELLED: 100.0,
        PlanningRunStage.TIMED_OUT: 100.0,
    }
    return PlanningRunProgress(
        stage=stage_enum,
        message=messages.get(stage_enum, "Processing"),
        percent_complete=percent_map.get(stage_enum, 50.0),
    )


def _map_to_detail(run: PlanningRunModel) -> PlanningRunDetailResponse:
    """Map DB model to public detail response schema."""
    return PlanningRunDetailResponse(
        run_id=run.run_id,
        scenario_id=run.scenario_id,
        status=PlanningRunStatus(run.status),
        stage=PlanningRunStage(run.stage),
        scheduler_type=run.scheduler_type,
        scheduler_version=run.scheduler_version,
        planning_start=run.planning_start,
        planning_end=run.planning_end,
        snapshot_id=run.snapshot_id,
        snapshot_hash=run.snapshot_hash,
        input_hash=run.input_hash,
        configuration_snapshot=run.configuration_snapshot or {},
        random_seed=run.random_seed,
        solver_name=run.solver_name,
        solver_version=run.solver_version,
        dataset_version=run.dataset_version,
        created_at=run.created_at,
        started_at=run.started_at,
        validation_started_at=run.validation_started_at,
        completed_at=run.completed_at,
        failed_at=run.failed_at,
        execution_duration_ms=run.execution_duration_ms,
        heartbeat_at=run.heartbeat_at,
        attempt_count=run.attempt_count,
        worker_id=run.worker_id,
        created_by=run.created_by,
        error_code=run.error_code,
        error_message=run.error_message,
        error_details=run.error_details,
        result_summary=run.result_summary,
        validation_status=run.validation_status,
        validation_fingerprint=run.validation_fingerprint,
        is_approvable=run.is_approvable,
        validation_findings_summary=run.validation_findings_summary,
        diagnostics_summary=run.diagnostics_summary,
        status_url=f"/api/v1/planning-runs/{run.run_id}",
        result_url=f"/api/v1/planning-runs/{run.run_id}/result" if run.status == PlanningRunStatus.COMPLETED.value else None,
        progress=_map_to_progress(run),
    )


@router.post(
    "",
    response_model=CreatePlanningRunResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def create_planning_run(
    request: CreatePlanningRunRequest,
    idempotency_key_header: Optional[str] = Header(None, alias="Idempotency-Key"),
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(require_permission("write:operational")),
    _rate_limit: None = Depends(enforce_planning_rate_limit),
) -> CreatePlanningRunResponse:
    """Submit a planning run requisition to the persistent background worker queue.
    
    Returns HTTP 201 immediately with a queue token without blocking for solver completion.
    """
    scenario_repo = ScenarioRepository(session)
    scenario = await scenario_repo.get_by_id_or_code(request.scenario_id)
    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "SCENARIO_NOT_FOUND",
                    "message": f"Operational scenario '{request.scenario_id}' does not exist.",
                }
            },
        )

    run_repo = PlanningRunRepository(session)

    # Check client idempotency key
    client_idempotency_key = request.idempotency_key or idempotency_key_header
    if client_idempotency_key:
        existing_run = await run_repo.get_by_idempotency_key(client_idempotency_key)
        if existing_run:
            return CreatePlanningRunResponse(
                run_id=existing_run.run_id,
                scenario_id=existing_run.scenario_id,
                status=PlanningRunStatus(existing_run.status),
                stage=PlanningRunStage(existing_run.stage),
                scheduler_type=existing_run.scheduler_type,
                created_at=existing_run.created_at,
                status_url=f"/api/v1/planning-runs/{existing_run.run_id}",
            )

    # Assemble configuration snapshot
    solver_mode = request.solver_mode or (
        request.optimization_config.solver_mode if request.optimization_config else "TRACK_AWARE_CONSERVATIVE"
    )
    config_snapshot = {
        "scheduler_type": request.scheduler_type.value,
        "validate_after_solve": request.validate_after_solve,
        "solver_mode": solver_mode,
        "time_limit_seconds": request.time_limit_seconds or (
            request.optimization_config.time_limit_seconds if request.optimization_config else 30.0
        ),
        "num_search_workers": request.num_search_workers or (
            request.optimization_config.num_search_workers if request.optimization_config else 1
        ),
        "random_seed": request.random_seed if request.random_seed is not None else (
            request.optimization_config.random_seed if request.optimization_config else 0
        ),
        "priority_config": request.priority_config.model_dump() if request.priority_config else None,
        "optimization_config": request.optimization_config.model_dump() if request.optimization_config else None,
    }

    run_id = f"RUN-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

    new_run = PlanningRunModel(
        run_id=run_id,
        scenario_id=scenario.scenario_id,
        status=PlanningRunStatus.PENDING.value,
        stage=PlanningRunStage.QUEUED.value,
        run_type="SINGLE",
        scheduler_type=request.scheduler_type.value,
        scheduler_version="1.0.0",
        configuration_snapshot=config_snapshot,
        priority_configuration=request.priority_config.model_dump() if request.priority_config else None,
        optimization_configuration=request.optimization_config.model_dump() if request.optimization_config else None,
        random_seed=config_snapshot["random_seed"],
        solver_name="OR-Tools CP-SAT" if request.scheduler_type == "CP_SAT" else "Deterministic Baseline",
        solver_version="9.15.6755",
        dataset_version=scenario.dataset_version,
        created_by=current_user.username,
        idempotency_key=client_idempotency_key,
    )

    created_run = await run_repo.create_run(new_run)

    return CreatePlanningRunResponse(
        run_id=created_run.run_id,
        scenario_id=created_run.scenario_id,
        status=PlanningRunStatus(created_run.status),
        stage=PlanningRunStage(created_run.stage),
        scheduler_type=created_run.scheduler_type,
        created_at=created_run.created_at,
        status_url=f"/api/v1/planning-runs/{created_run.run_id}",
    )


@router.get(
    "/{run_id}",
    response_model=PlanningRunDetailResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_planning_run_details(
    run_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(require_permission("read:operational")),
) -> PlanningRunDetailResponse:
    """Retrieve execution status, lifecycle stages, metrics, and certification for a planning run."""
    run_repo = PlanningRunRepository(session)
    run = await run_repo.get_by_run_id(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "PLANNING_RUN_NOT_FOUND",
                    "message": f"Planning run '{run_id}' not found.",
                }
            },
        )
    return _map_to_detail(run)


@router.get(
    "/{run_id}/result",
    response_model=ScheduleResult,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
async def get_planning_run_schedule_result(
    run_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(require_permission("read:operational")),
) -> ScheduleResult:
    """Retrieve full finalized ScheduleResult payload for a completed planning run."""
    run_repo = PlanningRunRepository(session)
    run = await run_repo.get_by_run_id(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "PLANNING_RUN_NOT_FOUND",
                    "message": f"Planning run '{run_id}' not found.",
                }
            },
        )

    if run.status != PlanningRunStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "PLANNING_RUN_NOT_COMPLETED",
                    "message": f"Planning run '{run_id}' is currently in status '{run.status}' (stage: '{run.stage}') and has not finalized a result yet.",
                }
            },
        )

    if not run.schedule_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "SCHEDULE_RESULT_NOT_PERSISTED",
                    "message": f"Schedule result for run '{run_id}' is missing from persistence store.",
                }
            },
        )

    return ScheduleResult.model_validate(run.schedule_result)


@router.get(
    "",
    response_model=List[PlanningRunSummary],
)
async def list_planning_runs(
    scenario_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    response: Response = None,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(require_permission("read:operational")),
) -> List[PlanningRunSummary]:
    """List planning runs with optional scenario/status filtering and bounded pagination."""
    clamped_limit = max(1, min(limit, 100))
    run_repo = PlanningRunRepository(session)

    runs = await run_repo.list_runs(
        scenario_id=scenario_id,
        status=status,
        limit=clamped_limit,
        offset=offset,
    )
    total_count = await run_repo.count_runs(scenario_id=scenario_id, status=status)

    if response:
        response.headers["X-Total-Count"] = str(total_count)
        response.headers["X-Limit"] = str(clamped_limit)
        response.headers["X-Offset"] = str(offset)

    summaries = []
    for r in runs:
        res_sum = r.result_summary or {}
        summaries.append(
            PlanningRunSummary(
                run_id=r.run_id,
                scenario_id=r.scenario_id,
                status=PlanningRunStatus(r.status),
                stage=PlanningRunStage(r.stage),
                scheduler_type=r.scheduler_type,
                created_at=r.created_at,
                started_at=r.started_at,
                completed_at=r.completed_at,
                execution_duration_ms=r.execution_duration_ms,
                validation_status=r.validation_status,
                is_approvable=r.is_approvable,
                total_tasks=res_sum.get("total_tasks"),
                scheduled_tasks=res_sum.get("scheduled_tasks"),
                error_code=r.error_code,
            )
        )
    return summaries


@router.post(
    "/{run_id}/cancel",
    response_model=PlanningRunDetailResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
async def cancel_planning_run(
    run_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(require_permission("write:operational")),
) -> PlanningRunDetailResponse:
    """Request cooperative cancellation of a pending or running planning job."""
    run_repo = PlanningRunRepository(session)
    try:
        updated_run = await run_repo.request_cancellation(run_id)
    except IllegalStateTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "ILLEGAL_STATE_TRANSITION", "message": str(e)}},
        )

    if not updated_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "PLANNING_RUN_NOT_FOUND",
                    "message": f"Planning run '{run_id}' not found.",
                }
            },
        )

    return _map_to_detail(updated_run)
