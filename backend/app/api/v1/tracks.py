from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db_session
from backend.app.repositories.track_repo import TrackRepository
from backend.app.schemas.responses import TrackResponse
from backend.app.schemas.common import ErrorResponse
from backend.app.core.auth import get_current_user, AuthUser

router = APIRouter(prefix="/tracks", tags=["Tracks"])


@router.get(
    "/{track_id}",
    response_model=TrackResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_track_by_id(
    track_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(get_current_user),
) -> TrackResponse:
    """Retrieve track line infrastructure by track ID."""
    repo = TrackRepository(session)
    track = await repo.get_by_id(track_id)
    if not track:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "RESOURCE_NOT_FOUND",
                    "message": f"Track with ID '{track_id}' not found.",
                }
            },
        )
    return TrackResponse.model_validate(track)


@router.get("", response_model=List[TrackResponse])
async def list_tracks(
    response: Response,
    section_id: Optional[str] = Query(None, description="Filter by section ID"),
    direction: Optional[str] = Query(None, description="Filter by running direction (UP, DOWN, BIDIRECTIONAL)"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of items to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(get_current_user),
) -> List[TrackResponse]:
    """List running tracks with pagination, filtering, and total count metadata."""
    repo = TrackRepository(session)
    tracks = await repo.filter_tracks(
        section_id=section_id,
        direction=direction,
        limit=limit,
        offset=offset,
    )
    total_count = await repo.count_tracks(
        section_id=section_id,
        direction=direction,
    )
    response.headers["X-Total-Count"] = str(total_count)
    return [TrackResponse.model_validate(t) for t in tracks]
