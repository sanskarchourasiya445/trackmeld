from typing import Optional, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from backend.app.db.models.section import SectionModel
from backend.app.repositories.base import BaseRepository


class SectionRepository(BaseRepository[SectionModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(SectionModel, session)

    async def get_by_code(self, section_code: str) -> Optional[SectionModel]:
        stmt = select(SectionModel).where(SectionModel.section_code == section_code.upper())
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_id_or_code(self, identifier: str) -> Optional[SectionModel]:
        sec = await self.get_by_code(identifier)
        if sec:
            return sec
        return await self.get_by_id(identifier)

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
        stmt = select(SectionModel).where(SectionModel.division == division.upper())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def filter_sections(
        self,
        zone: Optional[str] = None,
        division: Optional[str] = None,
        electrified: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[SectionModel]:
        stmt = select(SectionModel)
        if zone:
            stmt = stmt.where(SectionModel.zone == zone.upper())
        if division:
            stmt = stmt.where(SectionModel.division == division.upper())
        if electrified is not None:
            stmt = stmt.where(SectionModel.electrified == electrified)
        stmt = stmt.order_by(SectionModel.section_code).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_sections(
        self,
        zone: Optional[str] = None,
        division: Optional[str] = None,
        electrified: Optional[bool] = None,
    ) -> int:
        stmt = select(func.count()).select_from(SectionModel)
        if zone:
            stmt = stmt.where(SectionModel.zone == zone.upper())
        if division:
            stmt = stmt.where(SectionModel.division == division.upper())
        if electrified is not None:
            stmt = stmt.where(SectionModel.electrified == electrified)
        result = await self.session.execute(stmt)
        return result.scalar() or 0
