import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.repositories.scenario_repo import ScenarioRepository
from backend.app.repositories.work_order_repo import WorkOrderRepository
from backend.app.repositories.task_repo import MaintenanceTaskRepository
from backend.app.repositories.resource_repo import (
    ResourceRepository,
    ResourceAvailabilityRepository,
    TaskResourceRequirementRepository,
)
from backend.app.domain.enums import (
    WorkDepartment,
    WorkOrderStatus,
    TaskStatus,
    ResourceType,
)


@pytest.mark.asyncio
async def test_scenario_repository(db_session: AsyncSession):
    repo = ScenarioRepository(db_session)
    scenarios = await repo.list_all(limit=10)
    assert len(scenarios) >= 1
    scn = await repo.get_by_code("SCN-DEMO-001")
    assert scn is not None
    assert scn.scenario_code == "SCN-DEMO-001"


@pytest.mark.asyncio
async def test_work_order_repository(db_session: AsyncSession):
    repo = WorkOrderRepository(db_session)
    orders = await repo.list_by_scenario("SCN-DEMO-001")
    assert len(orders) >= 10
    wo = await repo.get_by_number("WO-2026-10-001")
    assert wo is not None
    assert wo.work_order_number == "WO-2026-10-001"

    eng_orders = await repo.list_by_department(WorkDepartment.ENGINEERING)
    assert len(eng_orders) >= 1
    assert all(o.department == WorkDepartment.ENGINEERING for o in eng_orders)


@pytest.mark.asyncio
async def test_task_repository(db_session: AsyncSession):
    repo = MaintenanceTaskRepository(db_session)
    tasks = await repo.list_by_scenario("SCN-DEMO-001")
    assert len(tasks) >= 20

    t1 = await repo.get_by_code("TSK-TRK-001")
    assert t1 is not None
    assert t1.task_code == "TSK-TRK-001"

    t1_relations = await repo.get_with_relations(t1.task_id)
    assert t1_relations is not None
    assert len(t1_relations.resource_requirements) >= 1
    assert len(t1_relations.rule_references) >= 1


@pytest.mark.asyncio
async def test_resource_repositories(db_session: AsyncSession):
    res_repo = ResourceRepository(db_session)
    resources = await res_repo.list_all(limit=50)
    assert len(resources) >= 15

    track_machines = await res_repo.list_by_type(ResourceType.TRACK_MACHINE)
    assert len(track_machines) >= 3

    avail_repo = ResourceAvailabilityRepository(db_session)
    availabilities = await avail_repo.list_by_scenario("SCN-DEMO-001")
    assert len(availabilities) >= 20
