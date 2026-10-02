from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db_session
from backend.app.repositories.station_repo import StationRepository
from backend.app.schemas.responses import StationResponse
from backend.app.schemas.common import ErrorResponse
from backend.app.domain.enums import DataClass
from backend.app.core.auth import get_current_user, AuthUser

router = APIRouter(prefix="/stations", tags=["Stations"])


@router.get(
    "/{station_code}",
    response_model=StationResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_station_by_code(
    station_code: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(get_current_user),
) -> StationResponse:
    """Retrieve station details by official station code (e.g. NDLS) or station ID (e.g. STN-NDLS)."""
    repo = StationRepository(session)
    station = await repo.get_by_id_or_code(station_code)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "RESOURCE_NOT_FOUND",
                    "message": f"Station with code or ID '{station_code.upper()}' not found.",
                }
            },
        )
    return StationResponse.model_validate(station)


@router.get("", response_model=List[StationResponse])
async def list_stations(
    response: Response,
    zone: Optional[str] = Query(None, description="Filter by railway zone code (e.g. NR, NCR)"),
    division: Optional[str] = Query(None, description="Filter by railway division code (e.g. DLI)"),
    station_type: Optional[str] = Query(None, description="Filter by station type"),
    classification: Optional[DataClass] = Query(None, description="Filter by data provenance classification"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of items to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(get_current_user),
) -> List[StationResponse]:
    """List stations with pagination, filtering, and total count metadata."""
    repo = StationRepository(session)
    stations = await repo.filter_stations(
        zone=zone,
        division=division,
        station_type=station_type,
        classification=classification,
        limit=limit,
        offset=offset,
    )
    total_count = await repo.count_stations(
        zone=zone,
        division=division,
        station_type=station_type,
        classification=classification,
    )

    response.headers["X-Total-Count"] = str(total_count)
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)

    return [StationResponse.model_validate(s) for s in stations]
