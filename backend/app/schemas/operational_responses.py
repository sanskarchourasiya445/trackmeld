from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from backend.app.domain.enums import (
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


class OperationalScenarioResponse(BaseModel):
    scenario_id: str
    scenario_code: str
    name: str
    description: str
    planning_start: datetime
    planning_end: datetime
    generation_seed: int
    dataset_version: str
    classification: DataClass

    model_config = {"from_attributes": True}


class WorkOrderResponse(BaseModel):
    work_order_id: str
    work_order_number: str
    title: str
    department: WorkDepartment
    requesting_unit: str
    requested_by: str
    status: WorkOrderStatus
    priority: TaskPriority
    mandatory: bool
    scenario_id: str
    requested_execution_start: datetime
    requested_execution_end: datetime
    remarks: Optional[str] = None
    classification: DataClass
    source_id: str

    model_config = {"from_attributes": True}


class MaintenanceResourceResponse(BaseModel):
    resource_id: str
    resource_code: str
    name: str
    resource_type: ResourceType
    department: WorkDepartment
    description: Optional[str] = None
    capacity: int
    home_station: Optional[str] = None
    qualification_tags: List[str]
    classification: DataClass
    source_id: str

    model_config = {"from_attributes": True}


class ResourceAvailabilityResponse(BaseModel):
    availability_id: str
    resource_id: str
    scenario_id: str
    available_from: datetime
    available_until: datetime
    availability_status: AvailabilityStatus
    quantity: int

    model_config = {"from_attributes": True}


class TaskResourceRequirementResponse(BaseModel):
    requirement_id: str
    task_id: str
    resource_id: Optional[str] = None
    resource_type: ResourceType
    quantity: int
    mandatory: bool

    model_config = {"from_attributes": True}


class TaskDependencyResponse(BaseModel):
    dependency_id: str
    predecessor_task_id: str
    successor_task_id: str
    dependency_type: DependencyType

    model_config = {"from_attributes": True}


class MaintenanceTaskResponse(BaseModel):
    task_id: str
    work_order_id: str
    task_code: str
    title: str
    description: Optional[str] = None
    task_type: TaskType
    status: TaskStatus
    priority: TaskPriority
    mandatory: bool
    section_id: str
    station_id: Optional[str] = None
    corridor_id: Optional[str] = None
    scenario_id: str
    window_start: datetime
    window_end: datetime
    preferred_start: Optional[datetime] = None
    preferred_end: Optional[datetime] = None
    estimated_duration_minutes: int
    minimum_duration_minutes: Optional[int] = None
    maximum_duration_minutes: Optional[int] = None
    requires_traffic_block: bool
    requires_power_block: bool
    requires_ptw: bool
    requires_ohe_isolation: bool
    requires_signal_disconnection: bool
    safety_buffer_before_minutes: int
    safety_buffer_after_minutes: int
    crew_size_required: int
    classification: DataClass
    source_id: str

    model_config = {"from_attributes": True}


class MaintenanceTaskDetailResponse(MaintenanceTaskResponse):
    additional_section_ids: List[str] = []
    rule_reference_ids: List[str] = []
    resource_requirements: List[TaskResourceRequirementResponse] = []
    predecessor_dependencies: List[TaskDependencyResponse] = []
    successor_dependencies: List[TaskDependencyResponse] = []


class ScenarioPlanningBundleResponse(BaseModel):
    scenario: Dict[str, Any]
    work_orders: List[Dict[str, Any]]
    tasks: List[Dict[str, Any]]
    dependencies: List[Dict[str, Any]]
    resources: List[Dict[str, Any]]
    resource_availabilities: List[Dict[str, Any]]
    sections: List[Dict[str, Any]]
    train_movements: List[Dict[str, Any]]
    applicable_rules: List[Dict[str, Any]]
