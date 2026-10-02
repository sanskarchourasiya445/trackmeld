from typing import Optional, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from backend.app.db.models.movement import TrainMovementModel
from backend.app.repositories.base import BaseRepository


class TrainMovementRepository(BaseRepository[TrainMovementModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(TrainMovementModel, session)

    async def list_by_train(self, train_id: str) -> Sequence[TrainMovementModel]:
        stmt = (
            select(TrainMovementModel)
            .where(TrainMovementModel.train_id == train_id)
            .order_by(TrainMovementModel.stop_sequence.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_station(self, station_id: str) -> Sequence[TrainMovementModel]:
        stmt = (
            select(TrainMovementModel)
            .where(TrainMovementModel.station_id == station_id)
            .order_by(TrainMovementModel.scheduled_departure.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_station_time_window(
        self,
        station_id: str,
        start_time: str,
        end_time: str,
    ) -> Sequence[TrainMovementModel]:
        """Find movements passing through a station within a scheduled daily time window."""
        stmt = (
            select(TrainMovementModel)
            .where(
                and_(
                    TrainMovementModel.station_id == station_id,
                    TrainMovementModel.scheduled_departure >= start_time,
                    TrainMovementModel.scheduled_departure < end_time,
                )
            )
            .order_by(TrainMovementModel.scheduled_departure.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
