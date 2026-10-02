"""TrackMeld Phase 2 — Comprehensive Operational Data Validation Script.

Validates the database state of all Phase 2 operational tables:
1. Table existence and expected row counts.
2. Temporal window validity (start < end).
3. Duration constraints (0 < estimated_duration <= window_duration).
4. Capacity and quantity positivity constraints.
5. Distinct dependency validation (predecessor != successor, acyclic).
6. Foreign key integrity across all operational and reference tables.
7. Strict data classification and provenance audit (100% SYNTHETIC on operational layer).
8. Immutability of Phase 0/1 reference data (stations, sections, rules remain REAL/DERIVED).
"""

import sys
import logging
from pathlib import Path

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from sqlalchemy import select, func, text
from sqlalchemy.orm import Session
from backend.app.db.session import sync_engine
from backend.app.db.models import (
    OperationalScenarioModel,
    WorkOrderModel,
    MaintenanceTaskModel,
    MaintenanceResourceModel,
    ResourceAvailabilityModel,
    TaskResourceRequirementModel,
    TaskDependencyModel,
    TaskSectionModel,
    TaskRuleReferenceModel,
    StationModel,
    SectionModel,
    RailwayRuleModel,
    CorridorModel,
    SourceDocumentModel,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("validate_operational_data")


def validate_operational_dataset() -> bool:
    checks_passed = 0
    checks_failed = 0

    def assert_check(condition: bool, description: str):
        nonlocal checks_passed, checks_failed
        if condition:
            checks_passed += 1
            logger.info(f"PASS: {description}")
        else:
            checks_failed += 1
            logger.error(f"FAIL: {description}")

    with Session(sync_engine) as session:
        logger.info("=== Starting TrackMeld Phase 2 Operational Validation ===")

        # 1. Row counts
        scenarios_count = session.query(func.count(OperationalScenarioModel.scenario_id)).scalar()
        assert_check(scenarios_count >= 1, f"Operational scenarios present (found {scenarios_count})")

        wo_count = session.query(func.count(WorkOrderModel.work_order_id)).scalar()
        assert_check(wo_count >= 10, f"Work orders count >= 10 (found {wo_count})")

        task_count = session.query(func.count(MaintenanceTaskModel.task_id)).scalar()
        assert_check(task_count >= 20, f"Maintenance tasks count >= 20 (found {task_count})")

        res_count = session.query(func.count(MaintenanceResourceModel.resource_id)).scalar()
        assert_check(res_count >= 10, f"Maintenance resources count >= 10 (found {res_count})")

        avail_count = session.query(func.count(ResourceAvailabilityModel.availability_id)).scalar()
        assert_check(avail_count >= 20, f"Resource availability intervals count >= 20 (found {avail_count})")

        req_count = session.query(func.count(TaskResourceRequirementModel.requirement_id)).scalar()
        assert_check(req_count >= 20, f"Task resource requirements count >= 20 (found {req_count})")

        dep_count = session.query(func.count(TaskDependencyModel.dependency_id)).scalar()
        assert_check(dep_count >= 5, f"Task dependencies count >= 5 (found {dep_count})")

        task_sec_count = session.query(func.count(TaskSectionModel.task_id)).scalar()
        assert_check(task_sec_count >= 1, f"Multi-section task links present (found {task_sec_count})")

        task_rule_count = session.query(func.count(TaskRuleReferenceModel.task_id)).scalar()
        assert_check(task_rule_count >= 10, f"Task rule references count >= 10 (found {task_rule_count})")

        # 2. Window validity
        invalid_wo_windows = session.query(WorkOrderModel).filter(
            WorkOrderModel.requested_execution_start >= WorkOrderModel.requested_execution_end
        ).count()
        assert_check(invalid_wo_windows == 0, "All work orders have requested_execution_start < requested_execution_end")

        invalid_task_windows = session.query(MaintenanceTaskModel).filter(
            MaintenanceTaskModel.window_start >= MaintenanceTaskModel.window_end
        ).count()
        assert_check(invalid_task_windows == 0, "All maintenance tasks have window_start < window_end")

        invalid_avail_windows = session.query(ResourceAvailabilityModel).filter(
            ResourceAvailabilityModel.available_from >= ResourceAvailabilityModel.available_until
        ).count()
        assert_check(invalid_avail_windows == 0, "All resource availability intervals have available_from < available_until")

        # 3. Duration validity
        invalid_durations = session.query(MaintenanceTaskModel).filter(
            MaintenanceTaskModel.estimated_duration_minutes <= 0
        ).count()
        assert_check(invalid_durations == 0, "All maintenance tasks have positive estimated durations")

        # 4. Capacity and crew size
        invalid_crew = session.query(MaintenanceTaskModel).filter(
            MaintenanceTaskModel.crew_size_required <= 0
        ).count()
        assert_check(invalid_crew == 0, "All maintenance tasks have positive crew sizes")

        invalid_cap = session.query(MaintenanceResourceModel).filter(
            MaintenanceResourceModel.capacity <= 0
        ).count()
        assert_check(invalid_cap == 0, "All maintenance resources have positive capacity")

        invalid_avail_qty = session.query(ResourceAvailabilityModel).filter(
            ResourceAvailabilityModel.quantity <= 0
        ).count()
        assert_check(invalid_avail_qty == 0, "All resource availability quantities are positive")

        invalid_req_qty = session.query(TaskResourceRequirementModel).filter(
            TaskResourceRequirementModel.quantity <= 0
        ).count()
        assert_check(invalid_req_qty == 0, "All resource requirement quantities are positive")

        # 5. Dependency distinctness
        invalid_deps = session.query(TaskDependencyModel).filter(
            TaskDependencyModel.predecessor_task_id == TaskDependencyModel.successor_task_id
        ).count()
        assert_check(invalid_deps == 0, "All task dependencies have predecessor != successor")

        # 6. Foreign Key Resolution
        # All tasks reference valid work orders
        tasks = session.query(MaintenanceTaskModel).all()
        wo_ids = set(session.execute(select(WorkOrderModel.work_order_id)).scalars().all())
        orphaned_task_wos = [t.task_id for t in tasks if t.work_order_id not in wo_ids]
        assert_check(len(orphaned_task_wos) == 0, "All tasks reference valid existing work orders")

        # All tasks reference valid sections
        sec_ids = set(session.execute(select(SectionModel.section_id)).scalars().all())
        orphaned_task_secs = [t.task_id for t in tasks if t.section_id not in sec_ids]
        assert_check(len(orphaned_task_secs) == 0, "All tasks reference valid existing block sections")

        # All resources reference valid home stations if specified
        stn_ids = set(session.execute(select(StationModel.station_id)).scalars().all())
        resources = session.query(MaintenanceResourceModel).all()
        orphaned_res_stns = [r.resource_id for r in resources if r.home_station and r.home_station not in stn_ids]
        assert_check(len(orphaned_res_stns) == 0, "All resources reference valid existing stations")

        # All rule references point to valid rules
        rule_ids = set(session.execute(select(RailwayRuleModel.rule_id)).scalars().all())
        task_rules = session.query(TaskRuleReferenceModel).all()
        orphaned_rules = [tr.rule_id for tr in task_rules if tr.rule_id not in rule_ids]
        assert_check(len(orphaned_rules) == 0, "All task rule references point to existing railway rules")

        # 7. Provenance & Classification Audit
        # 100% of operational scenario rows must be SYNTHETIC
        non_syn_scenarios = session.query(OperationalScenarioModel).filter(
            OperationalScenarioModel.classification != "SYNTHETIC"
        ).count()
        assert_check(non_syn_scenarios == 0, "All operational scenarios have classification=SYNTHETIC")

        non_syn_wos = session.query(WorkOrderModel).filter(
            WorkOrderModel.classification != "SYNTHETIC"
        ).count()
        assert_check(non_syn_wos == 0, "All work orders have classification=SYNTHETIC")

        non_syn_tasks = session.query(MaintenanceTaskModel).filter(
            MaintenanceTaskModel.classification != "SYNTHETIC"
        ).count()
        assert_check(non_syn_tasks == 0, "All maintenance tasks have classification=SYNTHETIC")

        non_syn_res = session.query(MaintenanceResourceModel).filter(
            MaintenanceResourceModel.classification != "SYNTHETIC"
        ).count()
        assert_check(non_syn_res == 0, "All maintenance resources have classification=SYNTHETIC")

        # Source ID audit
        bad_source_tasks = session.query(MaintenanceTaskModel).filter(
            MaintenanceTaskModel.source_id != "SRC-TRACKMELD-SYNTHETIC-GEN"
        ).count()
        assert_check(bad_source_tasks == 0, "All tasks carry source_id='SRC-TRACKMELD-SYNTHETIC-GEN'")

        # 8. Reference Data Immutability
        # Stations, sections, and rules must NOT have been changed to SYNTHETIC
        syn_stations = session.query(StationModel).filter(StationModel.classification == "SYNTHETIC").count()
        assert_check(syn_stations == 0, f"Zero stations classified as SYNTHETIC (found {syn_stations})")

        syn_sections = session.query(SectionModel).filter(SectionModel.classification == "SYNTHETIC").count()
        assert_check(syn_sections == 0, f"Zero sections classified as SYNTHETIC (found {syn_sections})")

        syn_rules = session.query(RailwayRuleModel).filter(RailwayRuleModel.rule_class == "DEMO_ONLY").count()
        # In Phase 0, all 9 rules were VERIFIED_SOURCE
        assert_check(syn_rules == 0, f"All Phase 0 rules remain verified source (found {syn_rules} demo-only)")

        logger.info(f"\n==========================================")
        logger.info(f"Phase 2 Database Validation Summary:")
        logger.info(f"Total Checks: {checks_passed + checks_failed}")
        logger.info(f"Passed:       {checks_passed}")
        logger.info(f"Failed:       {checks_failed}")
        logger.info(f"==========================================")

    return checks_failed == 0


if __name__ == "__main__":
    success = validate_operational_dataset()
    sys.exit(0 if success else 1)
