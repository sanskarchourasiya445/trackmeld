from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db_session
from backend.app.repositories.station_repo import StationRepository
from backend.app.schemas.responses import StationResponse
from backend.app.schemas.common import ErrorResponse

router = APIRouter(prefix="/stations", tags=["Stations"])


@router.get(
    "/{station_code}",
    response_model=StationResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_station_by_code(
    station_code: str,
    session: AsyncSession = Depends(get_db_session),
) -> StationResponse:
    """Retrieve station details by official station code (e.g. NDLS)."""
    repo = StationRepository(session)
    station = await repo.get_by_code(station_code)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "RESOURCE_NOT_FOUND",
                    "message": f"Station with code '{station_code.upper()}' not found.",
                }
            },
        )
    return StationResponse.model_validate(station)


@router.get("", response_model=List[StationResponse])
async def list_stations(
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db_session),
) -> List[StationResponse]:
    """List stations with pagination."""
    repo = StationRepository(session)
    stations = await repo.list_all(limit=limit, offset=offset)
    return [StationResponse.model_validate(s) for s in stations]
