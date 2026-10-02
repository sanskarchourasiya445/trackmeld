from typing import Optional, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.db.models.train import TrainModel
from backend.app.repositories.base import BaseRepository


class TrainRepository(BaseRepository[TrainModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(TrainModel, session)

    async def get_by_number(self, train_number: str) -> Optional[TrainModel]:
        stmt = select(TrainModel).where(TrainModel.train_number == train_number.strip())
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_by_type(self, train_type: str, limit: int = 100) -> Sequence[TrainModel]:
        stmt = select(TrainModel).where(TrainModel.train_type == train_type).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()
