from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db_session
from backend.app.repositories.resource_repo import (
    ResourceRepository,
    ResourceAvailabilityRepository,
)
from backend.app.schemas.operational_responses import (
    MaintenanceResourceResponse,
    ResourceAvailabilityResponse,
)
from backend.app.schemas.common import ErrorResponse
from backend.app.domain.enums import ResourceType, WorkDepartment

router = APIRouter(prefix="/resources", tags=["Maintenance Resources"])


@router.get("", response_model=List[MaintenanceResourceResponse])
async def list_resources(
    resource_type: Optional[ResourceType] = Query(None, description="Filter by resource type"),
    department: Optional[WorkDepartment] = Query(None, description="Filter by department"),
    home_station: Optional[str] = Query(None, description="Filter by home station code/id"),
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db_session),
) -> List[MaintenanceResourceResponse]:
    """List maintenance resources with optional filtering."""
    repo = ResourceRepository(session)
    if resource_type:
        resources = await repo.list_by_type(resource_type)
    elif department:
        resources = await repo.list_by_department(department)
    elif home_station:
        resources = await repo.list_by_home_station(home_station)
    else:
        resources = await repo.list_all(limit=limit, offset=offset)
    return [MaintenanceResourceResponse.model_validate(r) for r in resources]


@router.get(
    "/{resource_id}",
    response_model=MaintenanceResourceResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_resource(
    resource_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> MaintenanceResourceResponse:
    """Retrieve maintenance resource by ID or resource code."""
    repo = ResourceRepository(session)
    resource = await repo.get_by_id(resource_id)
    if not resource:
        resource = await repo.get_by_code(resource_id)
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "RESOURCE_NOT_FOUND",
                    "message": f"Maintenance resource '{resource_id}' not found.",
                }
            },
        )
    return MaintenanceResourceResponse.model_validate(resource)


@router.get(
    "/{resource_id}/availability",
    response_model=List[ResourceAvailabilityResponse],
    responses={404: {"model": ErrorResponse}},
)
async def get_resource_availability(
    resource_id: str,
    scenario_id: Optional[str] = Query(None, description="Filter by scenario ID"),
    session: AsyncSession = Depends(get_db_session),
) -> List[ResourceAvailabilityResponse]:
    """Retrieve availability intervals for a specific resource."""
    res_repo = ResourceRepository(session)
    resource = await res_repo.get_by_id(resource_id)
    if not resource:
        resource = await res_repo.get_by_code(resource_id)
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "RESOURCE_NOT_FOUND",
                    "message": f"Maintenance resource '{resource_id}' not found.",
                }
            },
        )

    avail_repo = ResourceAvailabilityRepository(session)
    availabilities = await avail_repo.list_by_resource(resource.resource_id, scenario_id=scenario_id)
    return [ResourceAvailabilityResponse.model_validate(a) for a in availabilities]
