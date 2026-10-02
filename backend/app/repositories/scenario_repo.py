from typing import Optional, Sequence, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from backend.app.db.models.scenario import OperationalScenarioModel
from backend.app.db.models.work_order import WorkOrderModel
from backend.app.db.models.task import MaintenanceTaskModel, TaskDependencyModel
from backend.app.db.models.resource import MaintenanceResourceModel, ResourceAvailabilityModel
from backend.app.repositories.base import BaseRepository


class ScenarioRepository(BaseRepository[OperationalScenarioModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(OperationalScenarioModel, session)

    async def get_by_code(self, scenario_code: str) -> Optional[OperationalScenarioModel]:
        stmt = select(OperationalScenarioModel).where(OperationalScenarioModel.scenario_code == scenario_code)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_id_or_code(self, identifier: str) -> Optional[OperationalScenarioModel]:
        scn = await self.get_by_code(identifier)
        if scn:
            return scn
        return await self.get_by_id(identifier)

    async def upsert(self, scenario: OperationalScenarioModel) -> OperationalScenarioModel:
        existing = await self.get_by_id(scenario.scenario_id)
        if existing:
            existing.scenario_code = scenario.scenario_code
            existing.name = scenario.name
            existing.description = scenario.description
            existing.planning_start = scenario.planning_start
            existing.planning_end = scenario.planning_end
            existing.generation_seed = scenario.generation_seed
            existing.dataset_version = scenario.dataset_version
            existing.classification = scenario.classification
            return existing
        else:
            self.session.add(scenario)
            return scenario

    async def get_manifest_data(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        scenario = await self.get_by_id_or_code(scenario_id)
        if not scenario:
            return None
        sid = scenario.scenario_id

        # Total work orders
        wo_count_stmt = select(func.count()).select_from(WorkOrderModel).where(WorkOrderModel.scenario_id == sid)
        wo_count = (await self.session.execute(wo_count_stmt)).scalar() or 0

        # Total tasks and mandatory tasks
        t_count_stmt = select(func.count()).select_from(MaintenanceTaskModel).where(MaintenanceTaskModel.scenario_id == sid)
        t_count = (await self.session.execute(t_count_stmt)).scalar() or 0

        m_count_stmt = select(func.count()).select_from(MaintenanceTaskModel).where(
            and_(MaintenanceTaskModel.scenario_id == sid, MaintenanceTaskModel.mandatory.is_(True))
        )
        m_count = (await self.session.execute(m_count_stmt)).scalar() or 0

        # Total unique resources in scenario
        r_count_stmt = select(func.count(func.distinct(ResourceAvailabilityModel.resource_id))).where(
            ResourceAvailabilityModel.scenario_id == sid
        )
        r_count = (await self.session.execute(r_count_stmt)).scalar() or 0

        # Total dependencies
        dep_count_stmt = (
            select(func.count())
            .select_from(TaskDependencyModel)
            .join(MaintenanceTaskModel, TaskDependencyModel.predecessor_task_id == MaintenanceTaskModel.task_id)
            .where(MaintenanceTaskModel.scenario_id == sid)
        )
        dep_count = (await self.session.execute(dep_count_stmt)).scalar() or 0

        # Tasks by type
        by_type_stmt = (
            select(MaintenanceTaskModel.task_type, func.count())
            .where(MaintenanceTaskModel.scenario_id == sid)
            .group_by(MaintenanceTaskModel.task_type)
        )
        by_type_res = (await self.session.execute(by_type_stmt)).all()
        tasks_by_type = {row[0].value if hasattr(row[0], "value") else str(row[0]): row[1] for row in by_type_res}

        # Tasks by priority
        by_priority_stmt = (
            select(MaintenanceTaskModel.priority, func.count())
            .where(MaintenanceTaskModel.scenario_id == sid)
            .group_by(MaintenanceTaskModel.priority)
        )
        by_priority_res = (await self.session.execute(by_priority_stmt)).all()
        tasks_by_priority = {row[0].value if hasattr(row[0], "value") else str(row[0]): row[1] for row in by_priority_res}

        # Tasks by status
        by_status_stmt = (
            select(MaintenanceTaskModel.status, func.count())
            .where(MaintenanceTaskModel.scenario_id == sid)
            .group_by(MaintenanceTaskModel.status)
        )
        by_status_res = (await self.session.execute(by_status_stmt)).all()
        tasks_by_status = {row[0].value if hasattr(row[0], "value") else str(row[0]): row[1] for row in by_status_res}

        return {
            "scenario_id": scenario.scenario_id,
            "scenario_code": scenario.scenario_code,
            "name": scenario.name,
            "description": scenario.description,
            "planning_start": scenario.planning_start,
            "planning_end": scenario.planning_end,
            "generation_seed": scenario.generation_seed,
            "dataset_version": scenario.dataset_version,
            "classification": scenario.classification,
            "total_work_orders": wo_count,
            "total_tasks": t_count,
            "total_mandatory_tasks": m_count,
            "total_resources": r_count,
            "total_dependencies": dep_count,
            "tasks_by_type": tasks_by_type,
            "tasks_by_priority": tasks_by_priority,
            "tasks_by_status": tasks_by_status,
        }
