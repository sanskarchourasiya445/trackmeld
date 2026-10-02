from typing import Optional, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.db.models.work_order import WorkOrderModel
from backend.app.domain.enums import WorkOrderStatus, WorkDepartment
from backend.app.repositories.base import BaseRepository


class WorkOrderRepository(BaseRepository[WorkOrderModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(WorkOrderModel, session)

    async def get_by_number(self, work_order_number: str) -> Optional[WorkOrderModel]:
        stmt = select(WorkOrderModel).where(WorkOrderModel.work_order_number == work_order_number)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_by_scenario(self, scenario_id: str) -> Sequence[WorkOrderModel]:
        stmt = select(WorkOrderModel).where(WorkOrderModel.scenario_id == scenario_id).order_by(WorkOrderModel.work_order_number)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_department(self, department: WorkDepartment, scenario_id: Optional[str] = None) -> Sequence[WorkOrderModel]:
        stmt = select(WorkOrderModel).where(WorkOrderModel.department == department)
        if scenario_id:
            stmt = stmt.where(WorkOrderModel.scenario_id == scenario_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_status(self, status: WorkOrderStatus, scenario_id: Optional[str] = None) -> Sequence[WorkOrderModel]:
        stmt = select(WorkOrderModel).where(WorkOrderModel.status == status)
        if scenario_id:
            stmt = stmt.where(WorkOrderModel.scenario_id == scenario_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def upsert(self, work_order: WorkOrderModel) -> WorkOrderModel:
        existing = await self.get_by_id(work_order.work_order_id)
        if existing:
            existing.work_order_number = work_order.work_order_number
            existing.title = work_order.title
            existing.department = work_order.department
            existing.requesting_unit = work_order.requesting_unit
            existing.requested_by = work_order.requested_by
            existing.status = work_order.status
            existing.priority = work_order.priority
            existing.mandatory = work_order.mandatory
            existing.scenario_id = work_order.scenario_id
            existing.requested_execution_start = work_order.requested_execution_start
            existing.requested_execution_end = work_order.requested_execution_end
            existing.remarks = work_order.remarks
            existing.classification = work_order.classification
            existing.source_id = work_order.source_id
            return existing
        else:
            self.session.add(work_order)
            return work_order
