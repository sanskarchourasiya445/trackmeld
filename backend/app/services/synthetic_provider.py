"""Synthetic Operational Data Provider.

Provides operational data for demonstration and planning simulations using
the synthetic dataset generated for TrackMeld.

All records returned by this provider are explicitly tagged with:
- classification: SYNTHETIC
- source_id: SRC-TRACKMELD-SYNTHETIC-GEN

This provider NEVER claims to connect to live CRIS / BDMS / TMS / COA systems.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from backend.app.services.operational_provider import OperationalDataProvider
from backend.app.db.models.task import MaintenanceTaskModel
from backend.app.db.models.work_order import WorkOrderModel
from backend.app.db.models.movement import TrainMovementModel
from backend.app.domain.enums import DataClass


class SyntheticOperationalDataProvider(OperationalDataProvider):
    """Provides synthetic operational data loaded from the TrackMeld database."""

    def __init__(self, session: AsyncSession, scenario_id: Optional[str] = None) -> None:
        self.session = session
        self.scenario_id = scenario_id

    async def get_maintenance_requests(
        self,
        division: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """Retrieve synthetic maintenance work orders within a window."""
        stmt = select(WorkOrderModel).where(
            and_(
                WorkOrderModel.requested_execution_start <= end_date,
                WorkOrderModel.requested_execution_end >= start_date,
            )
        )
        if self.scenario_id:
            stmt = stmt.where(WorkOrderModel.scenario_id == self.scenario_id)
        result = await self.session.execute(stmt)
        work_orders = result.scalars().all()

        return [
            {
                "work_order_id": wo.work_order_id,
                "work_order_number": wo.work_order_number,
                "title": wo.title,
                "department": wo.department.value,
                "requesting_unit": wo.requesting_unit,
                "requested_by": wo.requested_by,
                "status": wo.status.value,
                "priority": wo.priority.value,
                "mandatory": wo.mandatory,
                "scenario_id": wo.scenario_id,
                "requested_execution_start": wo.requested_execution_start.isoformat(),
                "requested_execution_end": wo.requested_execution_end.isoformat(),
                "remarks": wo.remarks,
                "classification": DataClass.SYNTHETIC.value,
                "source_id": wo.source_id,
            }
            for wo in work_orders
        ]

    async def get_block_requests(
        self,
        corridor_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """Retrieve synthetic task block requests within a window."""
        stmt = select(MaintenanceTaskModel).where(
            and_(
                MaintenanceTaskModel.window_start <= end_date,
                MaintenanceTaskModel.window_end >= start_date,
            )
        )
        if corridor_id:
            stmt = stmt.where(MaintenanceTaskModel.corridor_id == corridor_id)
        if self.scenario_id:
            stmt = stmt.where(MaintenanceTaskModel.scenario_id == self.scenario_id)
        result = await self.session.execute(stmt)
        tasks = result.scalars().all()

        return [
            {
                "task_id": t.task_id,
                "task_code": t.task_code,
                "title": t.title,
                "task_type": t.task_type.value,
                "status": t.status.value,
                "priority": t.priority.value,
                "section_id": t.section_id,
                "corridor_id": t.corridor_id,
                "window_start": t.window_start.isoformat(),
                "window_end": t.window_end.isoformat(),
                "estimated_duration_minutes": t.estimated_duration_minutes,
                "requires_traffic_block": t.requires_traffic_block,
                "requires_power_block": t.requires_power_block,
                "requires_ptw": t.requires_ptw,
                "classification": DataClass.SYNTHETIC.value,
                "source_id": t.source_id,
            }
            for t in tasks
        ]

    async def get_block_history(
        self,
        section_id: str,
        lookback_days: int = 30,
    ) -> List[Dict[str, Any]]:
        """Historical block record stub for synthetic testing."""
        return []

    async def get_operational_train_movements(
        self,
        section_id: str,
        window_start: datetime,
        window_end: datetime,
    ) -> List[Dict[str, Any]]:
        """Retrieve train movements traversing the section in the given window."""
        from backend.app.db.models.section import SectionModel
        sec = await self.session.get(SectionModel, section_id)
        if not sec:
            return []

        stmt = select(TrainMovementModel).where(
            TrainMovementModel.station_id.in_([sec.from_station_id, sec.to_station_id])
        )
        result = await self.session.execute(stmt)
        movements = result.scalars().all()

        return [
            {
                "movement_id": m.movement_id,
                "train_id": m.train_id,
                "train_number": m.train_number,
                "train_name": m.train_name,
                "station_id": m.station_id,
                "station_code": m.station_code,
                "scheduled_arrival": m.scheduled_arrival,
                "scheduled_departure": m.scheduled_departure,
                "track_id": m.track_id,
                "classification": m.classification.value,
                "source_id": m.source_id,
            }
            for m in movements
        ]

    async def get_train_services(
        self,
        train_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve synthetic train service definitions with operational characteristics."""
        from backend.app.db.models.train import TrainModel
        stmt = select(TrainModel)
        if train_type:
            stmt = stmt.where(TrainModel.train_type == train_type)
        result = await self.session.execute(stmt)
        trains = result.scalars().all()

        return [
            {
                "train_id": tr.train_id,
                "train_number": tr.train_number,
                "train_name": tr.train_name,
                "train_type": tr.train_type,
                "source_station": tr.source_station,
                "destination_station": tr.destination_station,
                "running_days": tr.running_days,
                "classification": tr.classification.value,
                "source_id": tr.source_id,
            }
            for tr in trains
        ]

    async def get_task_dependencies(
        self,
        scenario_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve task precedence and sequence dependencies."""
        from backend.app.db.models.task import TaskDependencyModel
        target_scenario = scenario_id or self.scenario_id
        stmt = select(TaskDependencyModel)
        result = await self.session.execute(stmt)
        deps = result.scalars().all()

        return [
            {
                "dependency_id": d.dependency_id,
                "predecessor_task_id": d.predecessor_task_id,
                "successor_task_id": d.successor_task_id,
                "dependency_type": d.dependency_type.value,
                "classification": DataClass.SYNTHETIC.value,
                "source_id": "SRC-TRACKMELD-SYNTHETIC-GEN",
            }
            for d in deps
        ]

    async def get_resource_contentions(
        self,
        scenario_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Identify resources with multiple competing task requisitions in the scenario."""
        from backend.app.db.models.resource import TaskResourceRequirementModel
        from backend.app.db.models.task import MaintenanceTaskModel
        from sqlalchemy import func
        target_scenario = scenario_id or self.scenario_id

        stmt = (
            select(
                TaskResourceRequirementModel.resource_id,
                func.count(TaskResourceRequirementModel.task_id).label("task_count"),
            )
            .join(MaintenanceTaskModel, TaskResourceRequirementModel.task_id == MaintenanceTaskModel.task_id)
            .group_by(TaskResourceRequirementModel.resource_id)
            .having(func.count(TaskResourceRequirementModel.task_id) > 1)
        )
        if target_scenario:
            stmt = stmt.where(MaintenanceTaskModel.scenario_id == target_scenario)

        result = await self.session.execute(stmt)
        return [
            {
                "resource_id": row[0],
                "competing_task_count": row[1],
                "classification": DataClass.SYNTHETIC.value,
                "source_id": "SRC-TRACKMELD-SYNTHETIC-GEN",
            }
            for row in result.all()
            if row[0] is not None
        ]
