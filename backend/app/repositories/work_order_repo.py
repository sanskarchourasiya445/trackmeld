from typing import Optional, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from backend.app.db.models.work_order import WorkOrderModel
from backend.app.domain.enums import WorkOrderStatus, WorkDepartment, TaskPriority
from backend.app.repositories.base import BaseRepository


class WorkOrderRepository(BaseRepository[WorkOrderModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(WorkOrderModel, session)

    async def get_by_number(self, work_order_number: str) -> Optional[WorkOrderModel]:
        stmt = select(WorkOrderModel).where(WorkOrderModel.work_order_number == work_order_number)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_id_or_number(self, identifier: str) -> Optional[WorkOrderModel]:
        wo = await self.get_by_number(identifier)
        if wo:
            return wo
        return await self.get_by_id(identifier)

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

    async def filter_work_orders(
        self,
        scenario_id: Optional[str] = None,
        department: Optional[WorkDepartment] = None,
        status: Optional[WorkOrderStatus] = None,
        priority: Optional[TaskPriority] = None,
        mandatory: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[WorkOrderModel]:
        stmt = select(WorkOrderModel)
        if scenario_id:
            stmt = stmt.where(WorkOrderModel.scenario_id == scenario_id)
        if department:
            stmt = stmt.where(WorkOrderModel.department == department)
        if status:
            stmt = stmt.where(WorkOrderModel.status == status)
        if priority:
            stmt = stmt.where(WorkOrderModel.priority == priority)
        if mandatory is not None:
            stmt = stmt.where(WorkOrderModel.mandatory == mandatory)
        stmt = stmt.order_by(WorkOrderModel.work_order_number).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_work_orders(
        self,
        scenario_id: Optional[str] = None,
        department: Optional[WorkDepartment] = None,
        status: Optional[WorkOrderStatus] = None,
        priority: Optional[TaskPriority] = None,
        mandatory: Optional[bool] = None,
    ) -> int:
        stmt = select(func.count()).select_from(WorkOrderModel)
        if scenario_id:
            stmt = stmt.where(WorkOrderModel.scenario_id == scenario_id)
        if department:
            stmt = stmt.where(WorkOrderModel.department == department)
        if status:
            stmt = stmt.where(WorkOrderModel.status == status)
        if priority:
            stmt = stmt.where(WorkOrderModel.priority == priority)
        if mandatory is not None:
            stmt = stmt.where(WorkOrderModel.mandatory == mandatory)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

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
