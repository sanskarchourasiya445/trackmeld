from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db_session
from backend.app.repositories.scenario_repo import ScenarioRepository
from backend.app.services.planning_service import PlanningScenarioService
from backend.app.schemas.operational_responses import (
    OperationalScenarioResponse,
    ScenarioPlanningBundleResponse,
)
from backend.app.schemas.common import ErrorResponse

router = APIRouter(prefix="/scenarios", tags=["Operational Scenarios"])


@router.get("", response_model=List[OperationalScenarioResponse])
async def list_scenarios(
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db_session),
) -> List[OperationalScenarioResponse]:
    """List operational scenarios with pagination."""
    repo = ScenarioRepository(session)
    scenarios = await repo.list_all(limit=limit, offset=offset)
    return [OperationalScenarioResponse.model_validate(s) for s in scenarios]


@router.get(
    "/{scenario_id}",
    response_model=OperationalScenarioResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_scenario_by_id(
    scenario_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> OperationalScenarioResponse:
    """Retrieve operational scenario by ID or scenario code."""
    repo = ScenarioRepository(session)
    scenario = await repo.get_by_id(scenario_id)
    if not scenario:
        scenario = await repo.get_by_code(scenario_id)
    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "SCENARIO_NOT_FOUND",
                    "message": f"Operational scenario '{scenario_id}' not found.",
                }
            },
        )
    return OperationalScenarioResponse.model_validate(scenario)


@router.get(
    "/{scenario_id}/bundle",
    response_model=ScenarioPlanningBundleResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_scenario_planning_bundle(
    scenario_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> ScenarioPlanningBundleResponse:
    """Retrieve the fully assembled planning bundle (tasks, resources, train movements, rules) for solver consumption."""
    service = PlanningScenarioService(session)
    bundle = await service.get_planning_bundle(scenario_id)
    if not bundle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "SCENARIO_NOT_FOUND",
                    "message": f"Operational scenario '{scenario_id}' not found for planning bundle.",
                }
            },
        )
    return ScenarioPlanningBundleResponse(
        scenario=bundle.scenario,
        work_orders=bundle.work_orders,
        tasks=bundle.tasks,
        dependencies=bundle.dependencies,
        resources=bundle.resources,
        resource_availabilities=bundle.resource_availabilities,
        sections=bundle.sections,
        train_movements=bundle.train_movements,
        applicable_rules=bundle.applicable_rules,
    )
