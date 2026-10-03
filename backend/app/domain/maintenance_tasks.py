from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field, model_validator
from backend.app.domain.enums import (
    DataClass,
    TaskType,
    TaskStatus,
    TaskPriority,
    DependencyType,
)


class WorkWindow(BaseModel):
    """Allowed time window for scheduling maintenance work."""
    window_start: datetime = Field(..., description="Earliest permissible start time (UTC)")
    window_end: datetime = Field(..., description="Latest permissible completion time (UTC)")
    preferred_start: Optional[datetime] = Field(default=None, description="Preferred start time (UTC)")
    preferred_end: Optional[datetime] = Field(default=None, description="Preferred completion time (UTC)")

    @model_validator(mode="after")
    def validate_window_bounds(self) -> "WorkWindow":
        if self.window_start >= self.window_end:
            raise ValueError(f"window_start ({self.window_start}) must precede window_end ({self.window_end})")
        if (self.preferred_start is None) != (self.preferred_end is None):
            raise ValueError("Both preferred_start and preferred_end must be provided if either is set")
        if self.preferred_start and self.preferred_end:
            if self.preferred_start >= self.preferred_end:
                raise ValueError(f"preferred_start ({self.preferred_start}) must precede preferred_end ({self.preferred_end})")
            if self.preferred_start < self.window_start or self.preferred_end > self.window_end:
                raise ValueError("Preferred window must be a subset of the allowed window [window_start, window_end]")
        return self


class MaintenanceTask(BaseModel):
    """Schedulable maintenance task requisition."""
    task_id: str = Field(..., description="Unique task identifier (e.g. MT-2026-0001)")
    work_order_id: str = Field(..., description="Parent work order ID")
    task_code: str = Field(..., description="Human-readable business key")
    title: str = Field(..., description="Summary of work to be performed")
    description: Optional[str] = Field(default=None, description="Detailed scope of work")
    task_type: TaskType = Field(..., description="Operational category")
    status: TaskStatus = Field(default=TaskStatus.REQUESTED, description="Requisition lifecycle status")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Task urgency level")
    mandatory: bool = Field(default=False, description="Whether failure to schedule is penalized heavily")
    section_id: str = Field(..., description="Primary block section ID affected")
    station_id: Optional[str] = Field(default=None, description="Station ID if task is within station yard")
    corridor_id: Optional[str] = Field(default=None, description="Corridor ID")
    scenario_id: str = Field(..., description="Operational scenario ID")
    window_start: datetime = Field(..., description="Allowed window start (UTC)")
    window_end: datetime = Field(..., description="Allowed window end (UTC)")
    preferred_start: Optional[datetime] = Field(default=None, description="Preferred start time (UTC)")
    preferred_end: Optional[datetime] = Field(default=None, description="Preferred completion time (UTC)")
    estimated_duration_minutes: int = Field(..., gt=0, description="Estimated duration in integer minutes")
    minimum_duration_minutes: Optional[int] = Field(default=None, gt=0)
    maximum_duration_minutes: Optional[int] = Field(default=None, gt=0)
    requires_traffic_block: bool = Field(default=False, description="Requires track block from operating")
    requires_power_block: bool = Field(default=False, description="Requires 25 kV OHE de-energization")
    requires_ptw: bool = Field(default=False, description="Requires signed Permit to Work")
    requires_ohe_isolation: bool = Field(default=False, description="Requires physical earthing & isolation")
    requires_signal_disconnection: bool = Field(default=False, description="Requires S&T disconnection notice")
    safety_buffer_before_minutes: int = Field(default=10, ge=0, description="Block setup/clearing buffer before work")
    safety_buffer_after_minutes: int = Field(default=10, ge=0, description="Block clearance/testing buffer after work")
    crew_size_required: int = Field(default=1, gt=0, description="Minimum headcount required")
    classification: DataClass = Field(default=DataClass.SYNTHETIC, description="Must remain SYNTHETIC")
    source_id: str = Field(default="SRC-TRACKMELD-SYNTHETIC-GEN", description="Generator provenance source")
    track_id: Optional[str] = Field(default=None, description="Optional specific track assignment (e.g. TRK-NDLS-GZB-UP)")
    affected_section_ids: List[str] = Field(default_factory=list, description="All block sections requiring spatial block")
    rule_references: List[str] = Field(default_factory=list, description="Rule IDs from railway_rules justifying constraints")

    @model_validator(mode="after")
    def validate_task_constraints(self) -> "MaintenanceTask":
        if self.window_start >= self.window_end:
            raise ValueError(f"window_start ({self.window_start}) must precede window_end ({self.window_end})")
        
        # Duration bounds check
        if self.minimum_duration_minutes and self.minimum_duration_minutes > self.estimated_duration_minutes:
            raise ValueError(f"minimum_duration ({self.minimum_duration_minutes}) cannot exceed estimated ({self.estimated_duration_minutes})")
        if self.maximum_duration_minutes and self.maximum_duration_minutes < self.estimated_duration_minutes:
            raise ValueError(f"maximum_duration ({self.maximum_duration_minutes}) cannot be less than estimated ({self.estimated_duration_minutes})")

        # Window capacity check: window must be long enough to accommodate duration + safety buffers
        window_duration_minutes = (self.window_end - self.window_start).total_seconds() / 60.0
        needed_minutes = self.estimated_duration_minutes + self.safety_buffer_before_minutes + self.safety_buffer_after_minutes
        if window_duration_minutes < needed_minutes:
            raise ValueError(
                f"Window length ({window_duration_minutes:.1f} mins) is insufficient for "
                f"estimated duration ({self.estimated_duration_minutes} mins) + safety buffers ({needed_minutes} mins total)"
            )

        # Preferred window check
        if (self.preferred_start is None) != (self.preferred_end is None):
            raise ValueError("Both preferred_start and preferred_end must be provided if either is set")
        if self.preferred_start and self.preferred_end:
            if self.preferred_start >= self.preferred_end:
                raise ValueError("preferred_start must precede preferred_end")
            if self.preferred_start < self.window_start or self.preferred_end > self.window_end:
                raise ValueError("Preferred window must be within allowed [window_start, window_end]")

        return self


class TaskDependency(BaseModel):
    """Precedence dependency between two maintenance tasks."""
    dependency_id: str = Field(..., description="Unique dependency identifier")
    predecessor_task_id: str = Field(..., description="Task that must finish before successor starts")
    successor_task_id: str = Field(..., description="Task that depends on predecessor")
    dependency_type: DependencyType = Field(default=DependencyType.FINISH_TO_START)

    @model_validator(mode="after")
    def validate_distinct_tasks(self) -> "TaskDependency":
        if self.predecessor_task_id == self.successor_task_id:
            raise ValueError(f"Task cannot depend on itself: {self.predecessor_task_id}")
        return self
