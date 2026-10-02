from typing import Optional, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
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

    async def filter_movements(
        self,
        train_id: Optional[str] = None,
        station_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[TrainMovementModel]:
        stmt = select(TrainMovementModel)
        if train_id:
            stmt = stmt.where(TrainMovementModel.train_id == train_id)
        if station_id:
            stmt = stmt.where(TrainMovementModel.station_id == station_id)
        stmt = stmt.order_by(TrainMovementModel.movement_id).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_movements(
        self,
        train_id: Optional[str] = None,
        station_id: Optional[str] = None,
    ) -> int:
        stmt = select(func.count()).select_from(TrainMovementModel)
        if train_id:
            stmt = stmt.where(TrainMovementModel.train_id == train_id)
        if station_id:
            stmt = stmt.where(TrainMovementModel.station_id == station_id)
        result = await self.session.execute(stmt)
        return result.scalar() or 0
