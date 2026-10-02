from typing import Optional, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.db.models.station import StationModel
from backend.app.repositories.base import BaseRepository


class StationRepository(BaseRepository[StationModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(StationModel, session)

    async def get_by_code(self, station_code: str) -> Optional[StationModel]:
        stmt = select(StationModel).where(StationModel.station_code == station_code.upper())
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_by_division(self, division: str) -> Sequence[StationModel]:
        stmt = select(StationModel).where(StationModel.division == division)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_zone(self, zone: str) -> Sequence[StationModel]:
        stmt = select(StationModel).where(StationModel.zone == zone)
        result = await self.session.execute(stmt)
        return result.scalars().all()
