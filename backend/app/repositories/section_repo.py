from typing import Optional, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from backend.app.db.models.section import SectionModel
from backend.app.repositories.base import BaseRepository


class SectionRepository(BaseRepository[SectionModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(SectionModel, session)

    async def get_by_code(self, section_code: str) -> Optional[SectionModel]:
        stmt = select(SectionModel).where(SectionModel.section_code == section_code.upper())
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_connecting_station(self, station_id: str) -> Sequence[SectionModel]:
        stmt = select(SectionModel).where(
            or_(
                SectionModel.from_station_id == station_id,
                SectionModel.to_station_id == station_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_division(self, division: str) -> Sequence[SectionModel]:
        stmt = select(SectionModel).where(SectionModel.division == division)
        result = await self.session.execute(stmt)
        return result.scalars().all()
