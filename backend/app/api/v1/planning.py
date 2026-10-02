"""API endpoints for baseline scheduling execution and fair benchmark comparisons.

Exposes:
- POST /api/v1/planning/baseline: Execute FCFS or Priority-Greedy baseline scheduler
- POST /api/v1/planning/benchmark: Compare both baselines side-by-side on the exact same snapshot
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db_session
from backend.app.core.auth import get_current_user, AuthUser
from backend.app.schemas.common import ErrorResponse
from backend.app.schemas.planning_requests import (
    BaselineScheduleRequest,
    BenchmarkComparisonRequest,
    OptimizeScheduleRequest,
)
from backend.app.domain.scheduling import (
    SchedulerConfig,
    ScheduleResult,
    BenchmarkComparisonResult,
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
    current_user: AuthUser = Depends(get_current_user),
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
    current_user: AuthUser = Depends(get_current_user),
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
    current_user: AuthUser = Depends(get_current_user),
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

