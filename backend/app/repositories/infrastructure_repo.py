from typing import Optional, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.db.models.infrastructure import InfrastructureSpecModel, CorridorModel
from backend.app.repositories.base import BaseRepository


class InfrastructureRepository:
    """Repository accessing infrastructure technical standards and corridors."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_specs(self) -> Sequence[InfrastructureSpecModel]:
        stmt = select(InfrastructureSpecModel)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_spec(self, spec_id: str) -> Optional[InfrastructureSpecModel]:
        return await self.session.get(InfrastructureSpecModel, spec_id)

    async def list_corridors(self) -> Sequence[CorridorModel]:
        stmt = select(CorridorModel)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_corridor(self, corridor_id: str) -> Optional[CorridorModel]:
        return await self.session.get(CorridorModel, corridor_id)
