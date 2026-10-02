from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db_session
from backend.app.repositories.task_repo import MaintenanceTaskRepository
from backend.app.services.planning_service import PlanningScenarioService
from backend.app.services.compatibility_service import CompatibilityEngine
from backend.app.domain.temporal import PlanningHorizon
from backend.app.domain.compatibility import CompatibilityResult
from backend.app.schemas.operational_responses import TaskEvaluationRequest
from backend.app.schemas.common import ErrorResponse
from backend.app.core.auth import get_current_user, AuthUser

router = APIRouter(prefix="/compatibility", tags=["Compatibility & Feasibility"])


@router.post(
    "/evaluate-task",
    response_model=CompatibilityResult,
    responses={404: {"model": ErrorResponse}},
)
async def evaluate_task_placement(
    request: TaskEvaluationRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(get_current_user),
) -> CompatibilityResult:
    """Deterministically evaluate feasibility and constraint compatibility for a candidate task placement.
    
    Returns structured results including hard/soft feasibility, conflict diagnostics, and rule evidence.
    This is an evaluation endpoint; it does not mutate schedule states.
    """
    task_repo = MaintenanceTaskRepository(session)
    task = await task_repo.get_with_relations(request.task_id)
    if not task:
        task = await task_repo.get_by_code(request.task_id)
        if task:
            task = await task_repo.get_with_relations(task.task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "TASK_NOT_FOUND",
                    "message": f"Maintenance task '{request.task_id}' not found.",
                }
            },
        )

    scenario_id = request.scenario_id or task.scenario_id
    planning_service = PlanningScenarioService(session)
    bundle = await planning_service.get_planning_bundle(scenario_id)
    if not bundle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "SCENARIO_NOT_FOUND",
                    "message": f"Operational scenario '{scenario_id}' not found.",
                }
            },
        )

    # Build PlanningHorizon
    scen_start = datetime.fromisoformat(bundle.scenario["planning_start"])
    scen_end = datetime.fromisoformat(bundle.scenario["planning_end"])
    if scen_start.tzinfo is None:
        scen_start = scen_start.replace(tzinfo=timezone.utc)
    if scen_end.tzinfo is None:
        scen_end = scen_end.replace(tzinfo=timezone.utc)
    horizon = PlanningHorizon(start=scen_start, end=scen_end)

    # Derive train passes from movements and sections
    train_passes = CompatibilityEngine.derive_train_passes(
        train_movements=bundle.train_movements,
        sections=bundle.sections,
        horizon=horizon,
    )

    # Build lookup maps
    sections_map = {s["section_id"]: s for s in bundle.sections}
    rules_map = {r["rule_id"]: r for r in bundle.applicable_rules}

    # Evaluate compatibility
    result = CompatibilityEngine.evaluate_task_placement(
        task=task,
        candidate_start=request.start_time,
        candidate_end=request.end_time,
        horizon=horizon,
        train_passes=train_passes,
        existing_placements=[],  # Single task isolated check or existing placements
        resource_availabilities=bundle.resource_availabilities,
        dependencies=bundle.dependencies,
        sections_map=sections_map,
        rules_map=rules_map,
    )

    return result
