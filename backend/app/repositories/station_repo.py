from typing import Optional, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from backend.app.db.models.station import StationModel
from backend.app.domain.enums import DataClass
from backend.app.repositories.base import BaseRepository


class StationRepository(BaseRepository[StationModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(StationModel, session)

    async def get_by_code(self, station_code: str) -> Optional[StationModel]:
        stmt = select(StationModel).where(StationModel.station_code == station_code.upper())
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_id_or_code(self, identifier: str) -> Optional[StationModel]:
        station = await self.get_by_code(identifier)
        if station:
            return station
        return await self.get_by_id(identifier)

    async def list_by_division(self, division: str) -> Sequence[StationModel]:
        stmt = select(StationModel).where(StationModel.division == division)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_zone(self, zone: str) -> Sequence[StationModel]:
        stmt = select(StationModel).where(StationModel.zone == zone)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def filter_stations(
        self,
        zone: Optional[str] = None,
        division: Optional[str] = None,
        station_type: Optional[str] = None,
        classification: Optional[DataClass] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[StationModel]:
        stmt = select(StationModel)
        if zone:
            stmt = stmt.where(StationModel.zone == zone.upper())
        if division:
            stmt = stmt.where(StationModel.division == division.upper())
        if station_type:
            stmt = stmt.where(StationModel.station_type == station_type.upper())
        if classification:
            stmt = stmt.where(StationModel.classification == classification)
        stmt = stmt.order_by(StationModel.station_code).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_stations(
        self,
        zone: Optional[str] = None,
        division: Optional[str] = None,
        station_type: Optional[str] = None,
        classification: Optional[DataClass] = None,
    ) -> int:
        stmt = select(func.count()).select_from(StationModel)
        if zone:
            stmt = stmt.where(StationModel.zone == zone.upper())
        if division:
            stmt = stmt.where(StationModel.division == division.upper())
        if station_type:
            stmt = stmt.where(StationModel.station_type == station_type.upper())
        if classification:
            stmt = stmt.where(StationModel.classification == classification)
        result = await self.session.execute(stmt)
        return result.scalar() or 0
