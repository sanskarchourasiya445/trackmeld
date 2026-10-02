from typing import Optional, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.db.models.rule import RailwayRuleModel
from backend.app.repositories.base import BaseRepository


class RailwayRuleRepository(BaseRepository[RailwayRuleModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(RailwayRuleModel, session)

    async def list_by_category(self, category: str) -> Sequence[RailwayRuleModel]:
        stmt = select(RailwayRuleModel).where(RailwayRuleModel.category == category)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_safety_critical(self) -> Sequence[RailwayRuleModel]:
        stmt = select(RailwayRuleModel).where(RailwayRuleModel.safety_critical == True)
        result = await self.session.execute(stmt)
        return result.scalars().all()
