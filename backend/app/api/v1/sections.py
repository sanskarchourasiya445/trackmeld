from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db_session
from backend.app.repositories.section_repo import SectionRepository
from backend.app.schemas.responses import SectionResponse
from backend.app.schemas.common import ErrorResponse

router = APIRouter(prefix="/sections", tags=["Sections"])


@router.get(
    "/{section_code}",
    response_model=SectionResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_section_by_code(
    section_code: str,
    session: AsyncSession = Depends(get_db_session),
) -> SectionResponse:
    """Retrieve section topology by hyphenated section code (e.g. NDLS-GZB)."""
    repo = SectionRepository(session)
    section = await repo.get_by_code(section_code)
    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "RESOURCE_NOT_FOUND",
                    "message": f"Section with code '{section_code.upper()}' not found.",
                }
            },
        )
    return SectionResponse.model_validate(section)


@router.get("", response_model=List[SectionResponse])
async def list_sections(
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db_session),
) -> List[SectionResponse]:
    """List block sections with pagination."""
    repo = SectionRepository(session)
    sections = await repo.list_all(limit=limit, offset=offset)
    return [SectionResponse.model_validate(s) for s in sections]
