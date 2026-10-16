from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db_session
from backend.app.repositories.movement_repo import TrainMovementRepository
from backend.app.schemas.responses import TrainMovementResponse
from backend.app.schemas.common import ErrorResponse
from backend.app.core.auth import require_permission, AuthUser

router = APIRouter(prefix="/movements", tags=["Movements"])


@router.get(
    "/{movement_id}",
    response_model=TrainMovementResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_movement_by_id(
    movement_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(require_permission("read:operational")),
) -> TrainMovementResponse:
    """Retrieve train movement / timetable entry by ID."""
    repo = TrainMovementRepository(session)
    movement = await repo.get_by_id(movement_id)
    if not movement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "RESOURCE_NOT_FOUND",
                    "message": f"Train movement with ID '{movement_id}' not found.",
                }
            },
        )
    return TrainMovementResponse.model_validate(movement)


@router.get("", response_model=List[TrainMovementResponse])
async def list_movements(
    response: Response,
    train_id: Optional[str] = Query(None, description="Filter by train ID"),
    station_id: Optional[str] = Query(None, description="Filter by station ID"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of items to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(require_permission("read:operational")),
) -> List[TrainMovementResponse]:
    """List train movement records with filtering by train/station and pagination."""
    repo = TrainMovementRepository(session)
    movements = await repo.filter_movements(
        train_id=train_id,
        station_id=station_id,
        limit=limit,
        offset=offset,
    )
    total_count = await repo.count_movements(train_id=train_id, station_id=station_id)

    response.headers["X-Total-Count"] = str(total_count)
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)

    return [TrainMovementResponse.model_validate(m) for m in movements]
