from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db_session
from backend.app.repositories.corridor_repo import CorridorRepository
from backend.app.schemas.responses import CorridorResponse
from backend.app.schemas.common import ErrorResponse
from backend.app.core.auth import get_current_user, AuthUser

router = APIRouter(prefix="/corridors", tags=["Corridors"])


@router.get(
    "/{corridor_id}",
    response_model=CorridorResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_corridor_by_id(
    corridor_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(get_current_user),
) -> CorridorResponse:
    """Retrieve corridor details by ID."""
    repo = CorridorRepository(session)
    corridor = await repo.get_by_id(corridor_id)
    if not corridor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "RESOURCE_NOT_FOUND",
                    "message": f"Corridor with ID '{corridor_id}' not found.",
                }
            },
        )
    return CorridorResponse.model_validate(corridor)


@router.get("", response_model=List[CorridorResponse])
async def list_corridors(
    response: Response,
    zone: Optional[str] = Query(None, description="Filter by zone abbreviation (e.g. NR)"),
    division: Optional[str] = Query(None, description="Filter by division code (e.g. DLI)"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of items to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(get_current_user),
) -> List[CorridorResponse]:
    """List trunk railway corridors with pagination and zone/division filtering."""
    repo = CorridorRepository(session)
    corridors = await repo.filter_corridors(zone=zone, division=division, limit=limit, offset=offset)
    total_count = await repo.count_corridors(zone=zone, division=division)

    response.headers["X-Total-Count"] = str(total_count)
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)

    return [CorridorResponse.model_validate(c) for c in corridors]
