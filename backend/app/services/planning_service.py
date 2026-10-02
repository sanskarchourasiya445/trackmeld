"""Planning Scenario Service.

Assembles all necessary domain entities for an operational scenario
to prepare for optimization and decision support (Phase 3).
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.db.models.scenario import OperationalScenarioModel
from backend.app.db.models.work_order import WorkOrderModel
from backend.app.db.models.task import MaintenanceTaskModel, TaskDependencyModel
from backend.app.db.models.resource import MaintenanceResourceModel, ResourceAvailabilityModel
from backend.app.db.models.movement import TrainMovementModel
from backend.app.db.models.rule import RailwayRuleModel
from backend.app.db.models.section import SectionModel


@dataclass
class ScenarioPlanningBundle:
    """Complete assembled scenario bundle ready for solver ingestion."""

    scenario: Dict[str, Any]
    work_orders: List[Dict[str, Any]]
    tasks: List[Dict[str, Any]]
    dependencies: List[Dict[str, Any]]
    resources: List[Dict[str, Any]]
    resource_availabilities: List[Dict[str, Any]]
    sections: List[Dict[str, Any]]
    train_movements: List[Dict[str, Any]]
    applicable_rules: List[Dict[str, Any]]


class PlanningScenarioService:
    """Assembles scenario data across operational and reference layers."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_planning_bundle(self, scenario_id: str) -> Optional[ScenarioPlanningBundle]:
        # 1. Fetch Scenario
        scenario = await self.session.get(OperationalScenarioModel, scenario_id)
        if not scenario:
            return None

        # 2. Fetch Work Orders
        stmt_wo = select(WorkOrderModel).where(WorkOrderModel.scenario_id == scenario_id)
        res_wo = await self.session.execute(stmt_wo)
        work_orders = res_wo.scalars().all()

        # 3. Fetch Tasks with eager loaded relations
        stmt_tasks = (
            select(MaintenanceTaskModel)
            .where(MaintenanceTaskModel.scenario_id == scenario_id)
            .options(
                selectinload(MaintenanceTaskModel.resource_requirements),
                selectinload(MaintenanceTaskModel.affected_sections),
                selectinload(MaintenanceTaskModel.rule_references),
            )
        )
        res_tasks = await self.session.execute(stmt_tasks)
        tasks = res_tasks.scalars().all()

        # 4. Fetch Dependencies for tasks in this scenario
        task_ids = [t.task_id for t in tasks]
        dependencies = []
        if task_ids:
            stmt_deps = select(TaskDependencyModel).where(
                TaskDependencyModel.predecessor_task_id.in_(task_ids)
            )
            res_deps = await self.session.execute(stmt_deps)
            dependencies = res_deps.scalars().all()

        # 5. Fetch Resources and Availability for this scenario
        stmt_avail = select(ResourceAvailabilityModel).where(
            ResourceAvailabilityModel.scenario_id == scenario_id
        )
        res_avail = await self.session.execute(stmt_avail)
        availabilities = res_avail.scalars().all()

        resource_ids = list(set([a.resource_id for a in availabilities] + [
            req.resource_id for t in tasks for req in t.resource_requirements if req.resource_id
        ]))
        resources = []
        if resource_ids:
            stmt_res = select(MaintenanceResourceModel).where(
                MaintenanceResourceModel.resource_id.in_(resource_ids)
            )
            res_res = await self.session.execute(stmt_res)
            resources = res_res.scalars().all()

        # 6. Fetch Affected Sections
        section_ids = list(set(
            [t.section_id for t in tasks] +
            [s.section_id for t in tasks for s in t.affected_sections]
        ))
        sections = []
        if section_ids:
            stmt_sec = select(SectionModel).where(SectionModel.section_id.in_(section_ids))
            res_sec = await self.session.execute(stmt_sec)
            sections = res_sec.scalars().all()

        # 7. Fetch Train Movements in affected stations
        train_movements = []
        if sections:
            station_ids = list(set([s.from_station_id for s in sections] + [s.to_station_id for s in sections]))
            if station_ids:
                stmt_mov = select(TrainMovementModel).where(
                    TrainMovementModel.station_id.in_(station_ids)
                )
                res_mov = await self.session.execute(stmt_mov)
                train_movements = res_mov.scalars().all()

        # 8. Fetch Applicable Rules
        rule_ids = list(set([r.rule_id for t in tasks for r in t.rule_references]))
        rules = []
        if rule_ids:
            stmt_rules = select(RailwayRuleModel).where(RailwayRuleModel.rule_id.in_(rule_ids))
            res_rules = await self.session.execute(stmt_rules)
            rules = res_rules.scalars().all()
        else:
            # Fallback: all rules in system
            stmt_rules = select(RailwayRuleModel)
            res_rules = await self.session.execute(stmt_rules)
            rules = res_rules.scalars().all()

        return ScenarioPlanningBundle(
            scenario={
                "scenario_id": scenario.scenario_id,
                "scenario_code": scenario.scenario_code,
                "name": scenario.name,
                "description": scenario.description,
                "planning_start": scenario.planning_start.isoformat(),
                "planning_end": scenario.planning_end.isoformat(),
                "generation_seed": scenario.generation_seed,
                "dataset_version": scenario.dataset_version,
                "classification": scenario.classification.value,
            },
            work_orders=[
                {
                    "work_order_id": wo.work_order_id,
                    "work_order_number": wo.work_order_number,
                    "title": wo.title,
                    "department": wo.department.value,
                    "requesting_unit": wo.requesting_unit,
                    "status": wo.status.value,
                    "priority": wo.priority.value,
                    "mandatory": wo.mandatory,
                    "requested_execution_start": wo.requested_execution_start.isoformat(),
                    "requested_execution_end": wo.requested_execution_end.isoformat(),
                    "classification": wo.classification.value,
                }
                for wo in work_orders
            ],
            tasks=[
                {
                    "task_id": t.task_id,
                    "work_order_id": t.work_order_id,
                    "task_code": t.task_code,
                    "title": t.title,
                    "task_type": t.task_type.value,
                    "status": t.status.value,
                    "priority": t.priority.value,
                    "mandatory": t.mandatory,
                    "section_id": t.section_id,
                    "station_id": t.station_id,
                    "corridor_id": t.corridor_id,
                    "window_start": t.window_start.isoformat(),
                    "window_end": t.window_end.isoformat(),
                    "estimated_duration_minutes": t.estimated_duration_minutes,
                    "requires_traffic_block": t.requires_traffic_block,
                    "requires_power_block": t.requires_power_block,
                    "requires_ptw": t.requires_ptw,
                    "safety_buffer_before_minutes": t.safety_buffer_before_minutes,
                    "safety_buffer_after_minutes": t.safety_buffer_after_minutes,
                    "crew_size_required": t.crew_size_required,
                    "additional_sections": [s.section_id for s in t.affected_sections],
                    "resource_requirements": [
                        {
                            "requirement_id": r.requirement_id,
                            "resource_type": r.resource_type.value,
                            "resource_id": r.resource_id,
                            "quantity": r.quantity,
                            "mandatory": r.mandatory,
                        }
                        for r in t.resource_requirements
                    ],
                    "classification": t.classification.value,
                }
                for t in tasks
            ],
            dependencies=[
                {
                    "dependency_id": d.dependency_id,
                    "predecessor_task_id": d.predecessor_task_id,
                    "successor_task_id": d.successor_task_id,
                    "dependency_type": d.dependency_type.value,
                }
                for d in dependencies
            ],
            resources=[
                {
                    "resource_id": r.resource_id,
                    "resource_code": r.resource_code,
                    "name": r.name,
                    "resource_type": r.resource_type.value,
                    "department": r.department.value,
                    "capacity": r.capacity,
                    "home_station": r.home_station,
                    "classification": r.classification.value,
                }
                for r in resources
            ],
            resource_availabilities=[
                {
                    "availability_id": a.availability_id,
                    "resource_id": a.resource_id,
                    "available_from": a.available_from.isoformat(),
                    "available_until": a.available_until.isoformat(),
                    "availability_status": a.availability_status.value,
                    "quantity": a.quantity,
                }
                for a in availabilities
            ],
            sections=[
                {
                    "section_id": s.section_id,
                    "section_code": s.section_code,
                    "from_station_id": s.from_station_id,
                    "to_station_id": s.to_station_id,
                    "from_station_name": s.from_station_name,
                    "to_station_name": s.to_station_name,
                    "length_km": s.length_km,
                    "division": s.division,
                    "zone": s.zone,
                    "track_count": s.track_count,
                    "electrified": s.electrified,
                    "classification": s.classification.value,
                }
                for s in sections
            ],
            train_movements=[
                {
                    "movement_id": m.movement_id,
                    "train_id": m.train_id,
                    "train_number": m.train_number,
                    "train_name": m.train_name,
                    "station_id": m.station_id,
                    "station_code": m.station_code,
                    "scheduled_arrival": m.scheduled_arrival,
                    "scheduled_departure": m.scheduled_departure,
                    "day_offset": m.day_offset,
                    "classification": m.classification.value,
                }
                for m in train_movements
            ],
            applicable_rules=[
                {
                    "rule_id": r.rule_id,
                    "category": r.category,
                    "title": r.title,
                    "safety_critical": r.safety_critical,
                    "rule_class": r.rule_class.value,
                    "classification": r.rule_class.value,
                }
                for r in rules
            ],
        )
