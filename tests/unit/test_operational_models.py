import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from backend.app.domain import (
    OperationalScenario,
    WorkOrder,
    WorkWindow,
    MaintenanceTask,
    MaintenanceResource,
    ResourceAvailability,
    TaskResourceRequirement,
    TaskDependency,
    DataClass,
    WorkOrderStatus,
    TaskPriority,
    WorkDepartment,
    TaskType,
    TaskStatus,
    ResourceType,
    AvailabilityStatus,
    DependencyType,
)


def test_operational_scenario_valid():
    start = datetime(2026, 10, 10, 0, 0, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=72)
    scenario = OperationalScenario(
        scenario_id="SCN-001",
        scenario_code="SCN-TEST-001",
        name="Test 72-Hour Scenario",
        description="Scenario for unit testing",
        planning_start=start,
        planning_end=end,
        generation_seed=20261001,
        dataset_version="2.0.0",
        classification=DataClass.SYNTHETIC,
    )
    assert scenario.scenario_id == "SCN-001"
    assert scenario.planning_end > scenario.planning_start
    assert scenario.classification == DataClass.SYNTHETIC


def test_operational_scenario_invalid_window():
    start = datetime(2026, 10, 10, 0, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(ValidationError):
        OperationalScenario(
            scenario_id="SCN-002",
            scenario_code="SCN-TEST-002",
            name="Invalid Scenario",
            description="End before start",
            planning_start=start,
            planning_end=start - timedelta(hours=1),
            generation_seed=20261001,
            dataset_version="2.0.0",
        )


def test_work_order_valid():
    start = datetime(2026, 10, 10, 6, 0, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=12)
    wo = WorkOrder(
        work_order_id="WO-0001",
        work_order_number="WO-2026-10-001",
        title="Track Tamping Package",
        department=WorkDepartment.ENGINEERING,
        requesting_unit="SSE/P-Way/GZB",
        requested_by="Sr.DEN/DLI",
        status=WorkOrderStatus.APPROVED,
        priority=TaskPriority.HIGH,
        mandatory=True,
        scenario_id="SCN-001",
        requested_execution_start=start,
        requested_execution_end=end,
        classification=DataClass.SYNTHETIC,
        source_id="SRC-TRACKMELD-SYNTHETIC-GEN",
    )
    assert wo.work_order_id == "WO-0001"
    assert wo.mandatory is True


def test_work_order_invalid_dates():
    start = datetime(2026, 10, 10, 6, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(ValidationError):
        WorkOrder(
            work_order_id="WO-0002",
            work_order_number="WO-2026-10-002",
            title="Invalid Window WO",
            department=WorkDepartment.ELECTRICAL,
            requesting_unit="SSE/TRD",
            requested_by="Sr.DEE",
            scenario_id="SCN-001",
            requested_execution_start=start,
            requested_execution_end=start,  # Equal dates invalid
            source_id="SRC-TRACKMELD-SYNTHETIC-GEN",
        )


def test_work_window_validation():
    start = datetime(2026, 10, 10, 8, 0, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=6)
    pref_start = start + timedelta(hours=1)
    pref_end = start + timedelta(hours=4)

    window = WorkWindow(
        window_start=start,
        window_end=end,
        preferred_start=pref_start,
        preferred_end=pref_end,
    )
    assert window.window_start < window.window_end
    assert window.preferred_start < window.preferred_end

    # Test preferred window outside allowed window
    with pytest.raises(ValidationError):
        WorkWindow(
            window_start=start,
            window_end=end,
            preferred_start=start - timedelta(hours=1),
            preferred_end=pref_end,
        )


def test_maintenance_task_valid():
    start = datetime(2026, 10, 10, 8, 0, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=6)
    task = MaintenanceTask(
        task_id="TSK-0001",
        work_order_id="WO-0001",
        task_code="TSK-TRK-001",
        title="Plain Track CSM Tamping",
        task_type=TaskType.TRACK_MACHINE_WORK,
        status=TaskStatus.PLANNED,
        priority=TaskPriority.CRITICAL,
        mandatory=True,
        section_id="SEC-NDLS-GZB",
        corridor_id="CORR-NDLS-HWH",
        scenario_id="SCN-001",
        window_start=start,
        window_end=end,
        preferred_start=start + timedelta(minutes=30),
        preferred_end=start + timedelta(minutes=210),
        estimated_duration_minutes=180,
        requires_traffic_block=True,
        requires_power_block=False,
        requires_ptw=True,
        safety_buffer_before_minutes=15,
        safety_buffer_after_minutes=15,
        crew_size_required=12,
        classification=DataClass.SYNTHETIC,
        source_id="SRC-TRACKMELD-SYNTHETIC-GEN",
    )
    assert task.task_id == "TSK-0001"
    assert task.estimated_duration_minutes == 180
    assert task.requires_traffic_block is True


def test_maintenance_task_duration_exceeds_window():
    start = datetime(2026, 10, 10, 8, 0, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=2)  # 120 minutes window
    with pytest.raises(ValidationError):
        MaintenanceTask(
            task_id="TSK-0002",
            work_order_id="WO-0001",
            task_code="TSK-TRK-002",
            title="Oversized Task",
            task_type=TaskType.TRACK_MAINTENANCE,
            section_id="SEC-NDLS-GZB",
            scenario_id="SCN-001",
            window_start=start,
            window_end=end,
            estimated_duration_minutes=180,  # 180 > 120 window
            crew_size_required=10,
            source_id="SRC-TRACKMELD-SYNTHETIC-GEN",
        )


def test_task_dependency_distinct():
    dep = TaskDependency(
        dependency_id="DEP-0001",
        predecessor_task_id="TSK-0001",
        successor_task_id="TSK-0002",
        dependency_type=DependencyType.FINISH_TO_START,
    )
    assert dep.predecessor_task_id != dep.successor_task_id

    # Self-dependency must fail validation
    with pytest.raises(ValidationError):
        TaskDependency(
            dependency_id="DEP-0002",
            predecessor_task_id="TSK-0001",
            successor_task_id="TSK-0001",
            dependency_type=DependencyType.FINISH_TO_START,
        )


def test_maintenance_resource_validation():
    resource = MaintenanceResource(
        resource_id="RES-TM-CSM-01",
        resource_code="TM-CSM-01",
        name="Continuous Action Tamping Machine CSM-01",
        resource_type=ResourceType.TRACK_MACHINE,
        department=WorkDepartment.ENGINEERING,
        capacity=1,
        home_station="STN-GZB",
        qualification_tags=["tamping", "plain_track"],
        classification=DataClass.SYNTHETIC,
        source_id="SRC-TRACKMELD-SYNTHETIC-GEN",
    )
    assert resource.capacity == 1
    assert "tamping" in resource.qualification_tags

    # Non-positive capacity must fail
    with pytest.raises(ValidationError):
        MaintenanceResource(
            resource_id="RES-BAD",
            resource_code="BAD",
            name="Bad Resource",
            resource_type=ResourceType.CREW,
            department=WorkDepartment.ENGINEERING,
            capacity=0,
            source_id="SRC-TRACKMELD-SYNTHETIC-GEN",
        )


def test_resource_availability_validation():
    start = datetime(2026, 10, 10, 0, 0, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=24)
    avail = ResourceAvailability(
        availability_id="AVL-0001",
        resource_id="RES-TM-CSM-01",
        scenario_id="SCN-001",
        available_from=start,
        available_until=end,
        availability_status=AvailabilityStatus.AVAILABLE,
        quantity=1,
    )
    assert avail.quantity == 1

    with pytest.raises(ValidationError):
        ResourceAvailability(
            availability_id="AVL-BAD",
            resource_id="RES-TM-CSM-01",
            scenario_id="SCN-001",
            available_from=end,
            available_until=start,  # End before start
            quantity=1,
        )


def test_task_resource_requirement_validation():
    req = TaskResourceRequirement(
        requirement_id="REQ-0001",
        task_id="TSK-0001",
        resource_id="RES-TM-CSM-01",
        resource_type=ResourceType.TRACK_MACHINE,
        quantity=1,
        mandatory=True,
    )
    assert req.quantity == 1
    assert req.mandatory is True

    with pytest.raises(ValidationError):
        TaskResourceRequirement(
            requirement_id="REQ-BAD",
            task_id="TSK-0001",
            resource_type=ResourceType.TRACK_MACHINE,
            quantity=0,
            mandatory=True,
        )
