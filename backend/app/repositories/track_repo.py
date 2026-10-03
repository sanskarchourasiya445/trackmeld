from typing import Optional, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from backend.app.db.models.track import TrackModel
from backend.app.repositories.base import BaseRepository


class TrackRepository(BaseRepository[TrackModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(TrackModel, session)

    async def get_by_id(self, track_id: str) -> Optional[TrackModel]:
        stmt = select(TrackModel).where(TrackModel.track_id == track_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_by_section(self, section_id: str) -> Sequence[TrackModel]:
        stmt = select(TrackModel).where(TrackModel.section_id == section_id).order_by(TrackModel.track_code.asc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def filter_tracks(
        self,
        section_id: Optional[str] = None,
        direction: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[TrackModel]:
        stmt = select(TrackModel)
        if section_id:
            stmt = stmt.where(TrackModel.section_id == section_id)
        if direction:
            stmt = stmt.where(TrackModel.direction == direction.upper())
        stmt = stmt.order_by(TrackModel.track_id).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_tracks(
        self,
        section_id: Optional[str] = None,
        direction: Optional[str] = None,
    ) -> int:
        stmt = select(func.count()).select_from(TrackModel)
        if section_id:
            stmt = stmt.where(TrackModel.section_id == section_id)
        if direction:
            stmt = stmt.where(TrackModel.direction == direction.upper())
        result = await self.session.execute(stmt)
        return result.scalar_one()
