from typing import Optional, Sequence
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from backend.app.db.models.resource import (
    MaintenanceResourceModel,
    ResourceAvailabilityModel,
    TaskResourceRequirementModel,
)
from backend.app.domain.enums import ResourceType, WorkDepartment, AvailabilityStatus
from backend.app.repositories.base import BaseRepository


class ResourceRepository(BaseRepository[MaintenanceResourceModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(MaintenanceResourceModel, session)

    async def get_by_code(self, resource_code: str) -> Optional[MaintenanceResourceModel]:
        stmt = select(MaintenanceResourceModel).where(MaintenanceResourceModel.resource_code == resource_code)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_id_or_code(self, identifier: str) -> Optional[MaintenanceResourceModel]:
        res = await self.get_by_code(identifier)
        if res:
            return res
        return await self.get_by_id(identifier)

    async def list_by_type(self, resource_type: ResourceType) -> Sequence[MaintenanceResourceModel]:
        stmt = select(MaintenanceResourceModel).where(MaintenanceResourceModel.resource_type == resource_type)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_department(self, department: WorkDepartment) -> Sequence[MaintenanceResourceModel]:
        stmt = select(MaintenanceResourceModel).where(MaintenanceResourceModel.department == department)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_home_station(self, home_station: str) -> Sequence[MaintenanceResourceModel]:
        stmt = select(MaintenanceResourceModel).where(MaintenanceResourceModel.home_station == home_station)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def filter_resources(
        self,
        resource_type: Optional[ResourceType] = None,
        department: Optional[WorkDepartment] = None,
        home_station: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[MaintenanceResourceModel]:
        stmt = select(MaintenanceResourceModel)
        if resource_type:
            stmt = stmt.where(MaintenanceResourceModel.resource_type == resource_type)
        if department:
            stmt = stmt.where(MaintenanceResourceModel.department == department)
        if home_station:
            stmt = stmt.where(MaintenanceResourceModel.home_station == home_station)
        stmt = stmt.order_by(MaintenanceResourceModel.resource_code).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_resources(
        self,
        resource_type: Optional[ResourceType] = None,
        department: Optional[WorkDepartment] = None,
        home_station: Optional[str] = None,
    ) -> int:
        stmt = select(func.count()).select_from(MaintenanceResourceModel)
        if resource_type:
            stmt = stmt.where(MaintenanceResourceModel.resource_type == resource_type)
        if department:
            stmt = stmt.where(MaintenanceResourceModel.department == department)
        if home_station:
            stmt = stmt.where(MaintenanceResourceModel.home_station == home_station)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def upsert(self, resource: MaintenanceResourceModel) -> MaintenanceResourceModel:
        existing = await self.get_by_id(resource.resource_id)
        if existing:
            existing.resource_code = resource.resource_code
            existing.name = resource.name
            existing.resource_type = resource.resource_type
            existing.department = resource.department
            existing.description = resource.description
            existing.capacity = resource.capacity
            existing.home_station = resource.home_station
            existing.qualification_tags = resource.qualification_tags
            existing.classification = resource.classification
            existing.source_id = resource.source_id
            return existing
        else:
            self.session.add(resource)
            return resource


class ResourceAvailabilityRepository(BaseRepository[ResourceAvailabilityModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ResourceAvailabilityModel, session)

    async def list_by_scenario(self, scenario_id: str) -> Sequence[ResourceAvailabilityModel]:
        stmt = select(ResourceAvailabilityModel).where(
            ResourceAvailabilityModel.scenario_id == scenario_id
        ).order_by(ResourceAvailabilityModel.available_from)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_resource(
        self, resource_id: str, scenario_id: Optional[str] = None
    ) -> Sequence[ResourceAvailabilityModel]:
        stmt = select(ResourceAvailabilityModel).where(ResourceAvailabilityModel.resource_id == resource_id)
        if scenario_id:
            stmt = stmt.where(ResourceAvailabilityModel.scenario_id == scenario_id)
        stmt = stmt.order_by(ResourceAvailabilityModel.available_from)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_available_in_window(
        self,
        resource_id: str,
        window_start: datetime,
        window_end: datetime,
        scenario_id: Optional[str] = None,
    ) -> Sequence[ResourceAvailabilityModel]:
        stmt = select(ResourceAvailabilityModel).where(
            and_(
                ResourceAvailabilityModel.resource_id == resource_id,
                ResourceAvailabilityModel.availability_status == AvailabilityStatus.AVAILABLE,
                ResourceAvailabilityModel.available_from <= window_end,
                ResourceAvailabilityModel.available_until >= window_start,
            )
        )
        if scenario_id:
            stmt = stmt.where(ResourceAvailabilityModel.scenario_id == scenario_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def upsert(self, availability: ResourceAvailabilityModel) -> ResourceAvailabilityModel:
        existing = await self.get_by_id(availability.availability_id)
        if existing:
            existing.resource_id = availability.resource_id
            existing.scenario_id = availability.scenario_id
            existing.available_from = availability.available_from
            existing.available_until = availability.available_until
            existing.availability_status = availability.availability_status
            existing.quantity = availability.quantity
            return existing
        else:
            self.session.add(availability)
            return availability


class TaskResourceRequirementRepository(BaseRepository[TaskResourceRequirementModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(TaskResourceRequirementModel, session)

    async def list_by_task(self, task_id: str) -> Sequence[TaskResourceRequirementModel]:
        stmt = select(TaskResourceRequirementModel).where(
            TaskResourceRequirementModel.task_id == task_id
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def upsert(self, requirement: TaskResourceRequirementModel) -> TaskResourceRequirementModel:
        existing = await self.get_by_id(requirement.requirement_id)
        if existing:
            existing.task_id = requirement.task_id
            existing.resource_id = requirement.resource_id
            existing.resource_type = requirement.resource_type
            existing.quantity = requirement.quantity
            existing.mandatory = requirement.mandatory
            return existing
        else:
            self.session.add(requirement)
            return requirement
