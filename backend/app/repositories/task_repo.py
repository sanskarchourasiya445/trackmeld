from typing import Optional, Sequence
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from backend.app.db.models.task import (
    MaintenanceTaskModel,
    TaskSectionModel,
    TaskDependencyModel,
    TaskRuleReferenceModel,
)
from backend.app.domain.enums import TaskStatus, TaskPriority, TaskType
from backend.app.repositories.base import BaseRepository


class MaintenanceTaskRepository(BaseRepository[MaintenanceTaskModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(MaintenanceTaskModel, session)

    async def get_by_code(self, task_code: str) -> Optional[MaintenanceTaskModel]:
        stmt = select(MaintenanceTaskModel).where(MaintenanceTaskModel.task_code == task_code)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_with_relations(self, task_id: str) -> Optional[MaintenanceTaskModel]:
        stmt = (
            select(MaintenanceTaskModel)
            .where(MaintenanceTaskModel.task_id == task_id)
            .options(
                selectinload(MaintenanceTaskModel.resource_requirements),
                selectinload(MaintenanceTaskModel.affected_sections),
                selectinload(MaintenanceTaskModel.outgoing_dependencies),
                selectinload(MaintenanceTaskModel.incoming_dependencies),
                selectinload(MaintenanceTaskModel.rule_references),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_by_scenario(self, scenario_id: str) -> Sequence[MaintenanceTaskModel]:
        stmt = (
            select(MaintenanceTaskModel)
            .where(MaintenanceTaskModel.scenario_id == scenario_id)
            .order_by(MaintenanceTaskModel.window_start, MaintenanceTaskModel.task_code)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_work_order(self, work_order_id: str) -> Sequence[MaintenanceTaskModel]:
        stmt = (
            select(MaintenanceTaskModel)
            .where(MaintenanceTaskModel.work_order_id == work_order_id)
            .order_by(MaintenanceTaskModel.task_code)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_section(
        self, section_id: str, scenario_id: Optional[str] = None
    ) -> Sequence[MaintenanceTaskModel]:
        stmt = select(MaintenanceTaskModel).where(MaintenanceTaskModel.section_id == section_id)
        if scenario_id:
            stmt = stmt.where(MaintenanceTaskModel.scenario_id == scenario_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_status(
        self, status: TaskStatus, scenario_id: Optional[str] = None
    ) -> Sequence[MaintenanceTaskModel]:
        stmt = select(MaintenanceTaskModel).where(MaintenanceTaskModel.status == status)
        if scenario_id:
            stmt = stmt.where(MaintenanceTaskModel.scenario_id == scenario_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_window(
        self, scenario_id: str, window_start: datetime, window_end: datetime
    ) -> Sequence[MaintenanceTaskModel]:
        stmt = select(MaintenanceTaskModel).where(
            and_(
                MaintenanceTaskModel.scenario_id == scenario_id,
                MaintenanceTaskModel.window_start <= window_end,
                MaintenanceTaskModel.window_end >= window_start,
            )
        ).order_by(MaintenanceTaskModel.window_start)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def upsert(self, task: MaintenanceTaskModel) -> MaintenanceTaskModel:
        existing = await self.get_by_id(task.task_id)
        if existing:
            existing.work_order_id = task.work_order_id
            existing.task_code = task.task_code
            existing.title = task.title
            existing.description = task.description
            existing.task_type = task.task_type
            existing.status = task.status
            existing.priority = task.priority
            existing.mandatory = task.mandatory
            existing.section_id = task.section_id
            existing.station_id = task.station_id
            existing.corridor_id = task.corridor_id
            existing.scenario_id = task.scenario_id
            existing.window_start = task.window_start
            existing.window_end = task.window_end
            existing.preferred_start = task.preferred_start
            existing.preferred_end = task.preferred_end
            existing.estimated_duration_minutes = task.estimated_duration_minutes
            existing.minimum_duration_minutes = task.minimum_duration_minutes
            existing.maximum_duration_minutes = task.maximum_duration_minutes
            existing.requires_traffic_block = task.requires_traffic_block
            existing.requires_power_block = task.requires_power_block
            existing.requires_ptw = task.requires_ptw
            existing.requires_ohe_isolation = task.requires_ohe_isolation
            existing.requires_signal_disconnection = task.requires_signal_disconnection
            existing.safety_buffer_before_minutes = task.safety_buffer_before_minutes
            existing.safety_buffer_after_minutes = task.safety_buffer_after_minutes
            existing.crew_size_required = task.crew_size_required
            existing.classification = task.classification
            existing.source_id = task.source_id
            return existing
        else:
            self.session.add(task)
            return task

    async def add_dependency(self, dep: TaskDependencyModel) -> TaskDependencyModel:
        existing = await self.session.get(TaskDependencyModel, dep.dependency_id)
        if existing:
            existing.dependency_type = dep.dependency_type
            return existing
        self.session.add(dep)
        return dep

    async def list_dependencies_for_scenario(self, scenario_id: str) -> Sequence[TaskDependencyModel]:
        stmt = (
            select(TaskDependencyModel)
            .join(
                MaintenanceTaskModel,
                TaskDependencyModel.predecessor_task_id == MaintenanceTaskModel.task_id,
            )
            .where(MaintenanceTaskModel.scenario_id == scenario_id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def link_section(self, task_id: str, section_id: str) -> TaskSectionModel:
        existing = await self.session.get(TaskSectionModel, (task_id, section_id))
        if not existing:
            link = TaskSectionModel(task_id=task_id, section_id=section_id)
            self.session.add(link)
            return link
        return existing

    async def link_rule(self, task_id: str, rule_id: str) -> TaskRuleReferenceModel:
        existing = await self.session.get(TaskRuleReferenceModel, (task_id, rule_id))
        if not existing:
            link = TaskRuleReferenceModel(task_id=task_id, rule_id=rule_id)
            self.session.add(link)
            return link
        return existing
