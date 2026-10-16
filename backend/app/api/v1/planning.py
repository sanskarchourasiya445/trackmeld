"""API endpoints for baseline scheduling execution and fair benchmark comparisons.

Exposes:
- POST /api/v1/planning/baseline: Execute FCFS or Priority-Greedy baseline scheduler
- POST /api/v1/planning/benchmark: Compare both baselines side-by-side on the exact same snapshot
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("trackmeld.planning")

from backend.app.db.session import get_db_session
from backend.app.core.auth import get_current_user, require_permission, AuthUser
from backend.app.core.rate_limit import enforce_compute_rate_limit
from backend.app.schemas.common import ErrorResponse
from backend.app.schemas.planning_requests import (
    BaselineScheduleRequest,
    BenchmarkComparisonRequest,
    OptimizeScheduleRequest,
    ValidateScheduleRequest,
    ScheduleDiagnosticsRequest,
)
from backend.app.domain.scheduling import (
    SchedulerConfig,
    ScheduleResult,
    BenchmarkComparisonResult,
)
from backend.app.services.validation.models import (
    ScheduleValidationResult,
    DiagnosticsReport,
)
from backend.app.services.baseline_service import BaselinePlanningService

router = APIRouter(prefix="/planning", tags=["Planning & Baseline Schedulers"])


@router.post(
    "/baseline",
    response_model=ScheduleResult,
    responses={
        404: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
    },
)
async def execute_baseline_schedule(
    request: BaselineScheduleRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(require_permission("write:operational")),
) -> ScheduleResult:
    """Execute a deterministic baseline scheduler (FCFS or Priority-Greedy) on a scenario.
    
    This is a read/evaluation planning endpoint; it computes derived schedules without mutating operational task state.
    """
    service = BaselinePlanningService(session)
    config = SchedulerConfig(
        scheduler_type=request.scheduler_type,
        priority_config=request.priority_config or None,
        max_candidate_attempts=request.max_candidate_attempts,
    ) if request.priority_config else SchedulerConfig(
        scheduler_type=request.scheduler_type,
        max_candidate_attempts=request.max_candidate_attempts,
    )

    try:
        result = await service.run_baseline_scheduler(
            scenario_id=request.scenario_id,
            scheduler_type=request.scheduler_type,
            config=config,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "INVALID_SCHEDULER_CONFIG", "message": str(e)}},
        )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "SCENARIO_NOT_FOUND",
                    "message": f"Operational scenario '{request.scenario_id}' not found.",
                }
            },
        )

    return result


@router.post(
    "/benchmark",
    response_model=BenchmarkComparisonResult,
    responses={
        404: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
    },
)
async def execute_benchmark_comparison(
    request: BenchmarkComparisonRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(require_permission("write:operational")),
) -> BenchmarkComparisonResult:
    """Execute side-by-side benchmark comparison between FCFS and Priority-Greedy on the exact same snapshot."""
    service = BaselinePlanningService(session)
    config = SchedulerConfig(
        scheduler_type=None,  # Config applied to both
        priority_config=request.priority_config or None,
        max_candidate_attempts=request.max_candidate_attempts,
    ) if request.priority_config else SchedulerConfig(
        scheduler_type=None,
        max_candidate_attempts=request.max_candidate_attempts,
    )

    try:
        comparison = await service.run_benchmark(
            scenario_id=request.scenario_id,
            config=config,
            include_cpsat=request.include_cpsat,
            cpsat_time_limit=request.cpsat_time_limit,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "INVALID_BENCHMARK_CONFIG", "message": str(e)}},
        )

    if not comparison:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "SCENARIO_NOT_FOUND",
                    "message": f"Operational scenario '{request.scenario_id}' not found.",
                }
            },
        )

    return comparison


@router.post(
    "/optimize",
    response_model=ScheduleResult,
    responses={
        404: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
    },
)
async def execute_optimization_schedule(
    request: OptimizeScheduleRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(require_permission("write:operational")),
    _rate_limit: None = Depends(enforce_compute_rate_limit),
) -> ScheduleResult:
    """Execute bounded mathematical optimization (CP-SAT) on an operational scenario.
    
    This evaluates global discrete feasibility and priority optimization without mutating operational task state.
    """
    from backend.app.services.optimization_service import OptimizationPlanningService
    from backend.app.services.optimization.solver_config import OptimizationConfig

    service = OptimizationPlanningService(session)
    config = OptimizationConfig(
        time_limit_seconds=request.time_limit_seconds,
        num_search_workers=request.num_search_workers,
        random_seed=request.random_seed,
        log_search_progress=request.log_search_progress,
        priority_config=request.priority_config if request.priority_config else None,
    ) if request.priority_config else OptimizationConfig(
        time_limit_seconds=request.time_limit_seconds,
        num_search_workers=request.num_search_workers,
        random_seed=request.random_seed,
        log_search_progress=request.log_search_progress,
    )

    try:
        result = await service.run_optimizer(
            scenario_id=request.scenario_id,
            config=config,
            validate_after_solve=request.validate_after_solve,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "INVALID_OPTIMIZER_CONFIG", "message": str(e)}},
        )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "SCENARIO_NOT_FOUND",
                    "message": f"Operational scenario '{request.scenario_id}' not found.",
                }
            },
        )

    return result


@router.post(
    "/validate",
    response_model=ScheduleValidationResult,
    responses={
        404: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
    },
)
async def validate_schedule_endpoint(
    request: ValidateScheduleRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(require_permission("read:operational")),
    _rate_limit: None = Depends(enforce_compute_rate_limit),
) -> ScheduleValidationResult:
    """Independently audit a schedule against all hard constraints without mutating schedule state."""
    from backend.app.services.planning_service import PlanningScenarioService
    from backend.app.domain.planning_snapshot import PlanningSnapshot
    from backend.app.services.validation import validate_schedule

    scenario_service = PlanningScenarioService(session)
    bundle = await scenario_service.get_planning_bundle(request.scenario_id)
    if not bundle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "SCENARIO_NOT_FOUND",
                    "message": f"Operational scenario '{request.scenario_id}' not found.",
                }
            },
        )
    snapshot = PlanningSnapshot.from_bundle(bundle)

    try:
        schedule = ScheduleResult.model_validate(request.schedule)
    except Exception as e:
        logger.warning("Malformed schedule payload received for validation: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "MALFORMED_SCHEDULE_PAYLOAD",
                    "message": "The provided schedule payload does not conform to the expected ScheduleResult structure.",
                }
            },
        )

    return validate_schedule(snapshot, schedule)


@router.post(
    "/diagnostics",
    response_model=DiagnosticsReport,
    responses={
        404: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
    },
)
async def schedule_diagnostics_endpoint(
    request: ScheduleDiagnosticsRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(require_permission("read:operational")),
    _rate_limit: None = Depends(enforce_compute_rate_limit),
) -> DiagnosticsReport:
    """Investigate root causes and relaxation scenarios for unscheduled tasks."""
    from backend.app.services.planning_service import PlanningScenarioService
    from backend.app.domain.planning_snapshot import PlanningSnapshot
    from backend.app.services.validation import UnscheduledTaskDiagnosticsService

    scenario_service = PlanningScenarioService(session)
    bundle = await scenario_service.get_planning_bundle(request.scenario_id)
    if not bundle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "SCENARIO_NOT_FOUND",
                    "message": f"Operational scenario '{request.scenario_id}' not found.",
                }
            },
        )
    snapshot = PlanningSnapshot.from_bundle(bundle)

    try:
        schedule = ScheduleResult.model_validate(request.schedule)
    except Exception as e:
        logger.warning("Malformed schedule payload received for diagnostics: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "MALFORMED_SCHEDULE_PAYLOAD",
                    "message": "The provided schedule payload does not conform to the expected ScheduleResult structure.",
                }
            },
        )

    diag_service = UnscheduledTaskDiagnosticsService(snapshot, schedule)
    return diag_service.diagnose_all(target_task_id=request.target_task_id)


