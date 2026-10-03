"""TrackMeld Phase 2 — Deterministic Operational Data Ingestion Script.

Reads synthetic operational scenario datasets, validates them against
Pydantic domain models, ensures generator provenance registration, and
loads entities idempotently into PostgreSQL.
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
import argparse

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from backend.app.db.session import sync_engine
from backend.app.domain import (
    OperationalScenario,
    WorkOrder,
    MaintenanceTask,
    MaintenanceResource,
    ResourceAvailability,
    TaskResourceRequirement,
    TaskDependency,
)
from backend.app.db.models import (
    SourceDocumentModel,
    OperationalScenarioModel,
    WorkOrderModel,
    MaintenanceTaskModel,
    MaintenanceResourceModel,
    ResourceAvailabilityModel,
    TaskResourceRequirementModel,
    TaskDependencyModel,
    TaskSectionModel,
    TaskRuleReferenceModel,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ingest_operational_data")


def ensure_synthetic_provenance_source(session: Session) -> None:
    """Ensure the synthetic generator source document exists in source_documents table."""
    logger.info("Verifying synthetic generator source document provenance...")
    stmt = insert(SourceDocumentModel).values(
        source_id="SRC-TRACKMELD-SYNTHETIC-GEN",
        title="TrackMeld Synthetic Operational Scenario Generator",
        publisher="TrackMeld Synthetic Data Pipeline",
        organization="TrackMeld",
        source_class="SECONDARY_REFERENCE",
        source_url="https://github.com/trackmeld/trackmeld/scripts/generate_synthetic_operational_data.py",
        local_path="scripts/generate_synthetic_operational_data.py",
        file_size_bytes=32000,
        document_date="2026-10-02",
        version="2.0.0",
        downloaded_at=datetime.now(timezone.utc),
        sha256="SYNTHETIC-GENERATOR-VER-2.0.0-PROVENANCE",
        data_types=["MAINTENANCE_TASKS", "WORK_ORDERS", "RESOURCES", "SCENARIOS"],
        authority_level="DEMO_ONLY_SYNTHETIC",
        notes="Official synthetic dataset generator for TrackMeld SIH 2026 Phase 2 operational simulations.",
    ).on_conflict_do_update(
        index_elements=[SourceDocumentModel.source_id],
        set_={
            "title": "TrackMeld Synthetic Operational Scenario Generator",
            "version": "2.0.0",
            "authority_level": "DEMO_ONLY_SYNTHETIC",
        },
    )
    session.execute(stmt)


def ingest_scenario(session: Session, raw_scenario: dict) -> int:
    logger.info(f"Ingesting Operational Scenario: {raw_scenario['scenario_code']}...")
    validated = OperationalScenario.model_validate(raw_scenario)
    stmt = insert(OperationalScenarioModel).values(
        scenario_id=validated.scenario_id,
        scenario_code=validated.scenario_code,
        name=validated.name,
        description=validated.description,
        planning_start=validated.planning_start,
        planning_end=validated.planning_end,
        generation_seed=validated.generation_seed,
        dataset_version=validated.dataset_version,
        classification=validated.classification.value,
    ).on_conflict_do_update(
        index_elements=[OperationalScenarioModel.scenario_id],
        set_={
            "name": validated.name,
            "description": validated.description,
            "planning_start": validated.planning_start,
            "planning_end": validated.planning_end,
            "generation_seed": validated.generation_seed,
            "dataset_version": validated.dataset_version,
            "classification": validated.classification.value,
        },
    )
    session.execute(stmt)
    return 1


def ingest_resources(session: Session, raw_resources: list) -> int:
    logger.info(f"Ingesting {len(raw_resources)} Maintenance Resources...")
    count = 0
    for r in raw_resources:
        validated = MaintenanceResource.model_validate(r)
        stmt = insert(MaintenanceResourceModel).values(
            resource_id=validated.resource_id,
            resource_code=validated.resource_code,
            name=validated.name,
            resource_type=validated.resource_type.value,
            department=validated.department.value,
            description=validated.description,
            capacity=validated.capacity,
            home_station=validated.home_station,
            qualification_tags=validated.qualification_tags,
            classification=validated.classification.value,
            source_id=validated.source_id,
        ).on_conflict_do_update(
            index_elements=[MaintenanceResourceModel.resource_id],
            set_={
                "resource_code": validated.resource_code,
                "name": validated.name,
                "resource_type": validated.resource_type.value,
                "department": validated.department.value,
                "description": validated.description,
                "capacity": validated.capacity,
                "home_station": validated.home_station,
                "qualification_tags": validated.qualification_tags,
                "classification": validated.classification.value,
                "source_id": validated.source_id,
            },
        )
        session.execute(stmt)
        count += 1
    return count


def ingest_availabilities(session: Session, raw_availabilities: list) -> int:
    logger.info(f"Ingesting {len(raw_availabilities)} Resource Availability intervals...")
    count = 0
    for a in raw_availabilities:
        validated = ResourceAvailability.model_validate(a)
        stmt = insert(ResourceAvailabilityModel).values(
            availability_id=validated.availability_id,
            resource_id=validated.resource_id,
            scenario_id=validated.scenario_id,
            available_from=validated.available_from,
            available_until=validated.available_until,
            availability_status=validated.availability_status.value,
            quantity=validated.quantity,
        ).on_conflict_do_update(
            index_elements=[ResourceAvailabilityModel.availability_id],
            set_={
                "resource_id": validated.resource_id,
                "scenario_id": validated.scenario_id,
                "available_from": validated.available_from,
                "available_until": validated.available_until,
                "availability_status": validated.availability_status.value,
                "quantity": validated.quantity,
            },
        )
        session.execute(stmt)
        count += 1
    return count


def ingest_work_orders(session: Session, raw_work_orders: list) -> int:
    logger.info(f"Ingesting {len(raw_work_orders)} Work Orders...")
    count = 0
    for wo in raw_work_orders:
        validated = WorkOrder.model_validate(wo)
        stmt = insert(WorkOrderModel).values(
            work_order_id=validated.work_order_id,
            work_order_number=validated.work_order_number,
            title=validated.title,
            department=validated.department.value,
            requesting_unit=validated.requesting_unit,
            requested_by=validated.requested_by,
            status=validated.status.value,
            priority=validated.priority.value,
            mandatory=validated.mandatory,
            scenario_id=validated.scenario_id,
            requested_execution_start=validated.requested_execution_start,
            requested_execution_end=validated.requested_execution_end,
            remarks=validated.remarks,
            classification=validated.classification.value,
            source_id=validated.source_id,
        ).on_conflict_do_update(
            index_elements=[WorkOrderModel.work_order_id],
            set_={
                "work_order_number": validated.work_order_number,
                "title": validated.title,
                "department": validated.department.value,
                "requesting_unit": validated.requesting_unit,
                "requested_by": validated.requested_by,
                "status": validated.status.value,
                "priority": validated.priority.value,
                "mandatory": validated.mandatory,
                "scenario_id": validated.scenario_id,
                "requested_execution_start": validated.requested_execution_start,
                "requested_execution_end": validated.requested_execution_end,
                "remarks": validated.remarks,
                "classification": validated.classification.value,
                "source_id": validated.source_id,
            },
        )
        session.execute(stmt)
        count += 1
    return count


def ingest_tasks(session: Session, raw_tasks: list) -> int:
    logger.info(f"Ingesting {len(raw_tasks)} Maintenance Tasks...")
    count = 0
    for t in raw_tasks:
        validated = MaintenanceTask.model_validate(t)
        stmt = insert(MaintenanceTaskModel).values(
            task_id=validated.task_id,
            work_order_id=validated.work_order_id,
            task_code=validated.task_code,
            title=validated.title,
            description=validated.description,
            task_type=validated.task_type.value,
            status=validated.status.value,
            priority=validated.priority.value,
            mandatory=validated.mandatory,
            section_id=validated.section_id,
            track_id=validated.track_id,
            from_km=validated.from_km,
            to_km=validated.to_km,
            station_id=validated.station_id,
            corridor_id=validated.corridor_id,
            scenario_id=validated.scenario_id,
            window_start=validated.window_start,
            window_end=validated.window_end,
            preferred_start=validated.preferred_start,
            preferred_end=validated.preferred_end,
            estimated_duration_minutes=validated.estimated_duration_minutes,
            minimum_duration_minutes=validated.minimum_duration_minutes,
            maximum_duration_minutes=validated.maximum_duration_minutes,
            requires_traffic_block=validated.requires_traffic_block,
            requires_power_block=validated.requires_power_block,
            requires_ptw=validated.requires_ptw,
            requires_ohe_isolation=validated.requires_ohe_isolation,
            requires_signal_disconnection=validated.requires_signal_disconnection,
            safety_buffer_before_minutes=validated.safety_buffer_before_minutes,
            safety_buffer_after_minutes=validated.safety_buffer_after_minutes,
            crew_size_required=validated.crew_size_required,
            classification=validated.classification.value,
            source_id=validated.source_id,
        ).on_conflict_do_update(
            index_elements=[MaintenanceTaskModel.task_id],
            set_={
                "work_order_id": validated.work_order_id,
                "task_code": validated.task_code,
                "title": validated.title,
                "description": validated.description,
                "task_type": validated.task_type.value,
                "status": validated.status.value,
                "priority": validated.priority.value,
                "mandatory": validated.mandatory,
                "section_id": validated.section_id,
                "track_id": validated.track_id,
                "from_km": validated.from_km,
                "to_km": validated.to_km,
                "station_id": validated.station_id,
                "corridor_id": validated.corridor_id,
                "scenario_id": validated.scenario_id,
                "window_start": validated.window_start,
                "window_end": validated.window_end,
                "preferred_start": validated.preferred_start,
                "preferred_end": validated.preferred_end,
                "estimated_duration_minutes": validated.estimated_duration_minutes,
                "minimum_duration_minutes": validated.minimum_duration_minutes,
                "maximum_duration_minutes": validated.maximum_duration_minutes,
                "requires_traffic_block": validated.requires_traffic_block,
                "requires_power_block": validated.requires_power_block,
                "requires_ptw": validated.requires_ptw,
                "requires_ohe_isolation": validated.requires_ohe_isolation,
                "requires_signal_disconnection": validated.requires_signal_disconnection,
                "safety_buffer_before_minutes": validated.safety_buffer_before_minutes,
                "safety_buffer_after_minutes": validated.safety_buffer_after_minutes,
                "crew_size_required": validated.crew_size_required,
                "classification": validated.classification.value,
                "source_id": validated.source_id,
            },
        )
        session.execute(stmt)
        count += 1
    return count


def ingest_resource_requirements(session: Session, raw_requirements: list) -> int:
    logger.info(f"Ingesting {len(raw_requirements)} Task Resource Requirements...")
    count = 0
    for req in raw_requirements:
        validated = TaskResourceRequirement.model_validate(req)
        stmt = insert(TaskResourceRequirementModel).values(
            requirement_id=validated.requirement_id,
            task_id=validated.task_id,
            resource_id=validated.resource_id,
            resource_type=validated.resource_type.value,
            quantity=validated.quantity,
            mandatory=validated.mandatory,
        ).on_conflict_do_update(
            index_elements=[TaskResourceRequirementModel.requirement_id],
            set_={
                "task_id": validated.task_id,
                "resource_id": validated.resource_id,
                "resource_type": validated.resource_type.value,
                "quantity": validated.quantity,
                "mandatory": validated.mandatory,
            },
        )
        session.execute(stmt)
        count += 1
    return count


def ingest_dependencies(session: Session, raw_dependencies: list) -> int:
    logger.info(f"Ingesting {len(raw_dependencies)} Task Dependencies...")
    count = 0
    for dep in raw_dependencies:
        validated = TaskDependency.model_validate(dep)
        stmt = insert(TaskDependencyModel).values(
            dependency_id=validated.dependency_id,
            predecessor_task_id=validated.predecessor_task_id,
            successor_task_id=validated.successor_task_id,
            dependency_type=validated.dependency_type.value,
        ).on_conflict_do_update(
            index_elements=[TaskDependencyModel.dependency_id],
            set_={
                "predecessor_task_id": validated.predecessor_task_id,
                "successor_task_id": validated.successor_task_id,
                "dependency_type": validated.dependency_type.value,
            },
        )
        session.execute(stmt)
        count += 1
    return count


def ingest_additional_sections(session: Session, raw_links: list) -> int:
    logger.info(f"Ingesting {len(raw_links)} Task Additional Sections...")
    count = 0
    for link in raw_links:
        stmt = insert(TaskSectionModel).values(
            task_id=link["task_id"],
            section_id=link["section_id"],
        ).on_conflict_do_nothing(
            index_elements=[TaskSectionModel.task_id, TaskSectionModel.section_id]
        )
        session.execute(stmt)
        count += 1
    return count


def ingest_rule_references(session: Session, raw_links: list) -> int:
    logger.info(f"Ingesting {len(raw_links)} Task Rule References...")
    count = 0
    for link in raw_links:
        stmt = insert(TaskRuleReferenceModel).values(
            task_id=link["task_id"],
            rule_id=link["rule_id"],
        ).on_conflict_do_nothing(
            index_elements=[TaskRuleReferenceModel.task_id, TaskRuleReferenceModel.rule_id]
        )
        session.execute(stmt)
        count += 1
    return count


def main():
    parser = argparse.ArgumentParser(description="Ingest TrackMeld Phase 2 operational dataset.")
    parser.add_argument(
        "--input",
        type=Path,
        default=BASE_DIR / "data" / "synthetic" / "operational_scenario_SCN-DEMO-001.json",
        help="Path to synthetic scenario JSON file.",
    )
    args = parser.parse_args()

    if not args.input.exists():
        logger.error(f"Dataset file not found: {args.input}")
        sys.exit(1)

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    with Session(sync_engine) as session:
        try:
            ensure_synthetic_provenance_source(session)
            c_scn = ingest_scenario(session, data["scenario"])
            c_res = ingest_resources(session, data["resources"])
            c_avl = ingest_availabilities(session, data["resource_availabilities"])
            c_wo = ingest_work_orders(session, data["work_orders"])
            c_tsk = ingest_tasks(session, data["maintenance_tasks"])
            c_req = ingest_resource_requirements(session, data["task_resource_requirements"])
            c_dep = ingest_dependencies(session, data["task_dependencies"])
            c_sec = ingest_additional_sections(session, data["task_additional_sections"])
            c_rul = ingest_rule_references(session, data["task_rule_references"])

            session.commit()
            logger.info("Successfully committed all operational records to PostgreSQL!")
            print("\n=== Phase 2 Ingestion Summary ===")
            print(f"Scenarios:             {c_scn}")
            print(f"Resources:             {c_res}")
            print(f"Availabilities:        {c_avl}")
            print(f"Work Orders:           {c_wo}")
            print(f"Maintenance Tasks:     {c_tsk}")
            print(f"Resource Requirements: {c_req}")
            print(f"Task Dependencies:     {c_dep}")
            print(f"Additional Sections:   {c_sec}")
            print(f"Rule References:       {c_rul}")
            print("=================================\n")
        except Exception as e:
            session.rollback()
            logger.error(f"Ingestion failed: {e}", exc_info=True)
            sys.exit(1)


if __name__ == "__main__":
    main()
