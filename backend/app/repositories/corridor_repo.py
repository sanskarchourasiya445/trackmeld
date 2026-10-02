from typing import Optional, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, String, cast
from backend.app.db.models.infrastructure import CorridorModel
from backend.app.repositories.base import BaseRepository


class CorridorRepository(BaseRepository[CorridorModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(CorridorModel, session)

    async def filter_corridors(
        self,
        zone: Optional[str] = None,
        division: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[CorridorModel]:
        stmt = select(CorridorModel)
        if zone:
            stmt = stmt.where(cast(CorridorModel.zones, String).like(f"%{zone}%"))
        if division:
            stmt = stmt.where(cast(CorridorModel.divisions, String).like(f"%{division}%"))
        stmt = stmt.order_by(CorridorModel.corridor_id).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_corridors(
        self,
        zone: Optional[str] = None,
        division: Optional[str] = None,
    ) -> int:
        stmt = select(func.count()).select_from(CorridorModel)
        if zone:
            stmt = stmt.where(cast(CorridorModel.zones, String).like(f"%{zone}%"))
        if division:
            stmt = stmt.where(cast(CorridorModel.divisions, String).like(f"%{division}%"))
        result = await self.session.execute(stmt)
        return result.scalar() or 0
