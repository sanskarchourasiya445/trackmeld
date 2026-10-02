from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db_session
from backend.app.repositories.section_repo import SectionRepository
from backend.app.schemas.responses import SectionResponse
from backend.app.schemas.common import ErrorResponse
from backend.app.core.auth import get_current_user, AuthUser

router = APIRouter(prefix="/sections", tags=["Sections"])


@router.get(
    "/{section_code}",
    response_model=SectionResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_section_by_code(
    section_code: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(get_current_user),
) -> SectionResponse:
    """Retrieve section topology by hyphenated section code (e.g. NDLS-GZB) or section ID (e.g. SEC-NDLS-GZB)."""
    repo = SectionRepository(session)
    section = await repo.get_by_id_or_code(section_code)
    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "RESOURCE_NOT_FOUND",
                    "message": f"Section with code or ID '{section_code.upper()}' not found.",
                }
            },
        )
    return SectionResponse.model_validate(section)


@router.get("", response_model=List[SectionResponse])
async def list_sections(
    response: Response,
    zone: Optional[str] = Query(None, description="Filter by railway zone code (e.g. NR, NCR)"),
    division: Optional[str] = Query(None, description="Filter by railway division code (e.g. DLI)"),
    electrified: Optional[bool] = Query(None, description="Filter by electrification status"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of items to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(get_current_user),
) -> List[SectionResponse]:
    """List block sections with pagination, filtering, and total count metadata."""
    repo = SectionRepository(session)
    sections = await repo.filter_sections(
        zone=zone,
        division=division,
        electrified=electrified,
        limit=limit,
        offset=offset,
    )
    total_count = await repo.count_sections(
        zone=zone,
        division=division,
        electrified=electrified,
    )

    response.headers["X-Total-Count"] = str(total_count)
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)

    return [SectionResponse.model_validate(s) for s in sections]
