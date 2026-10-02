from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db_session
from backend.app.repositories.train_repo import TrainRepository
from backend.app.schemas.responses import TrainResponse
from backend.app.schemas.common import ErrorResponse

router = APIRouter(prefix="/trains", tags=["Trains"])


@router.get(
    "/{train_number}",
    response_model=TrainResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_train_by_number(
    train_number: str,
    session: AsyncSession = Depends(get_db_session),
) -> TrainResponse:
    """Retrieve train details by 5-digit train number (e.g. 12301)."""
    repo = TrainRepository(session)
    train = await repo.get_by_number(train_number)
    if not train:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "RESOURCE_NOT_FOUND",
                    "message": f"Train with number '{train_number}' not found.",
                }
            },
        )
    return TrainResponse.model_validate(train)


@router.get("", response_model=List[TrainResponse])
async def list_trains(
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db_session),
) -> List[TrainResponse]:
    """List canonical trains with pagination."""
    repo = TrainRepository(session)
    trains = await repo.list_all(limit=limit, offset=offset)
    return [TrainResponse.model_validate(t) for t in trains]
