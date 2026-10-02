from typing import Optional, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from backend.app.db.models.train import TrainModel
from backend.app.domain.enums import DataClass
from backend.app.repositories.base import BaseRepository


class TrainRepository(BaseRepository[TrainModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(TrainModel, session)

    async def get_by_number(self, train_number: str) -> Optional[TrainModel]:
        stmt = select(TrainModel).where(TrainModel.train_number == train_number.strip())
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_id_or_number(self, identifier: str) -> Optional[TrainModel]:
        train = await self.get_by_number(identifier)
        if train:
            return train
        return await self.get_by_id(identifier)

    async def list_by_type(self, train_type: str, limit: int = 100) -> Sequence[TrainModel]:
        stmt = select(TrainModel).where(TrainModel.train_type == train_type).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def filter_trains(
        self,
        train_type: Optional[str] = None,
        corridor_table: Optional[str] = None,
        classification: Optional[DataClass] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[TrainModel]:
        stmt = select(TrainModel)
        if train_type:
            stmt = stmt.where(TrainModel.train_type == train_type)
        if corridor_table:
            stmt = stmt.where(TrainModel.corridor_table == corridor_table)
        if classification:
            stmt = stmt.where(TrainModel.classification == classification)
        stmt = stmt.order_by(TrainModel.train_number).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_trains(
        self,
        train_type: Optional[str] = None,
        corridor_table: Optional[str] = None,
        classification: Optional[DataClass] = None,
    ) -> int:
        stmt = select(func.count()).select_from(TrainModel)
        if train_type:
            stmt = stmt.where(TrainModel.train_type == train_type)
        if corridor_table:
            stmt = stmt.where(TrainModel.corridor_table == corridor_table)
        if classification:
            stmt = stmt.where(TrainModel.classification == classification)
        result = await self.session.execute(stmt)
        return result.scalar() or 0
