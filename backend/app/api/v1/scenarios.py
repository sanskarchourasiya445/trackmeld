from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db_session
from backend.app.repositories.scenario_repo import ScenarioRepository
from backend.app.services.planning_service import PlanningScenarioService
from backend.app.schemas.operational_responses import (
    OperationalScenarioResponse,
    ScenarioPlanningBundleResponse,
    ScenarioManifestResponse,
)
from backend.app.schemas.responses import TrainTraversalResponse
from backend.app.schemas.common import ErrorResponse
from backend.app.core.auth import get_current_user, AuthUser

router = APIRouter(prefix="/scenarios", tags=["Operational Scenarios"])


@router.get("", response_model=List[OperationalScenarioResponse])
async def list_scenarios(
    response: Response,
    limit: int = Query(100, ge=1, le=500, description="Maximum number of items to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(get_current_user),
) -> List[OperationalScenarioResponse]:
    """List operational scenarios with pagination metadata."""
    repo = ScenarioRepository(session)
    scenarios = await repo.list_all(limit=limit, offset=offset)
    total_count = await repo.count()

    response.headers["X-Total-Count"] = str(total_count)
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)

    return [OperationalScenarioResponse.model_validate(s) for s in scenarios]


@router.get(
    "/{scenario_id}",
    response_model=OperationalScenarioResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_scenario_by_id(
    scenario_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(get_current_user),
) -> OperationalScenarioResponse:
    """Retrieve operational scenario by ID or scenario code."""
    repo = ScenarioRepository(session)
    scenario = await repo.get_by_id_or_code(scenario_id)
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
    "/{scenario_id}/manifest",
    response_model=ScenarioManifestResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_scenario_manifest(
    scenario_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(get_current_user),
) -> ScenarioManifestResponse:
    """Retrieve summarized operational manifest and entity counts for a scenario."""
    repo = ScenarioRepository(session)
    manifest = await repo.get_manifest_data(scenario_id)
    if not manifest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "SCENARIO_NOT_FOUND",
                    "message": f"Operational scenario '{scenario_id}' not found.",
                }
            },
        )
    return ScenarioManifestResponse(**manifest)


@router.get(
    "/{scenario_id}/bundle",
    response_model=ScenarioPlanningBundleResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_scenario_planning_bundle(
    scenario_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(get_current_user),
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
        tracks=bundle.tracks,
        train_traversals=bundle.train_traversals,
    )


@router.get(
    "/{scenario_id}/traversals",
    response_model=List[TrainTraversalResponse],
    responses={404: {"model": ErrorResponse}},
)
async def get_scenario_train_traversals(
    scenario_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(get_current_user),
) -> List[TrainTraversalResponse]:
    """Retrieve derived physical section traversals for all trains in the scenario."""
    service = PlanningScenarioService(session)
    bundle = await service.get_planning_bundle(scenario_id)
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
    return [TrainTraversalResponse.model_validate(trv) for trv in bundle.train_traversals]
