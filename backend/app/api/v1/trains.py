from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db_session
from backend.app.repositories.train_repo import TrainRepository
from backend.app.schemas.responses import TrainResponse
from backend.app.schemas.common import ErrorResponse
from backend.app.domain.enums import DataClass
from backend.app.core.auth import require_permission, AuthUser

router = APIRouter(prefix="/trains", tags=["Trains"])


@router.get(
    "/{train_number}",
    response_model=TrainResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_train_by_number(
    train_number: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(require_permission("read:reference")),
) -> TrainResponse:
    """Retrieve train details by 5-digit train number (e.g. 12301) or train ID (e.g. TRN-12301)."""
    repo = TrainRepository(session)
    train = await repo.get_by_id_or_number(train_number)
    if not train:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "RESOURCE_NOT_FOUND",
                    "message": f"Train with number or ID '{train_number}' not found.",
                }
            },
        )
    return TrainResponse.model_validate(train)


@router.get("", response_model=List[TrainResponse])
async def list_trains(
    response: Response,
    train_type: Optional[str] = Query(None, description="Filter by train type (e.g. RAJDHANI, EXPRESS)"),
    corridor_table: Optional[str] = Query(None, description="Filter by corridor table identifier"),
    classification: Optional[DataClass] = Query(None, description="Filter by data provenance classification"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of items to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(require_permission("read:reference")),
) -> List[TrainResponse]:
    """List canonical trains with pagination, filtering, and total count metadata."""
    repo = TrainRepository(session)
    trains = await repo.filter_trains(
        train_type=train_type,
        corridor_table=corridor_table,
        classification=classification,
        limit=limit,
        offset=offset,
    )
    total_count = await repo.count_trains(
        train_type=train_type,
        corridor_table=corridor_table,
        classification=classification,
    )

    response.headers["X-Total-Count"] = str(total_count)
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)

    return [TrainResponse.model_validate(t) for t in trains]
