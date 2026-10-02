from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, model_validator
from backend.app.domain.enums import (
    DataClass,
    WorkDepartment,
    WorkOrderStatus,
    TaskPriority,
)


class WorkOrder(BaseModel):
    """Parent maintenance requisition grouping one or more maintenance tasks."""
    work_order_id: str = Field(..., description="Unique work order identifier (e.g. WO-2026-0001)")
    work_order_number: str = Field(..., description="Official requisition tracking number")
    title: str = Field(..., description="Summary title of the work requisition")
    department: WorkDepartment = Field(..., description="Responsible railway department")
    requesting_unit: str = Field(..., description="Division or SSE unit requesting work")
    requested_by: str = Field(..., description="Official designation of the requester")
    status: WorkOrderStatus = Field(default=WorkOrderStatus.SUBMITTED, description="Requisition status")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Overall priority")
    mandatory: bool = Field(default=False, description="Whether execution within horizon is mandatory")
    scenario_id: str = Field(..., description="Associated operational scenario ID")
    requested_execution_start: datetime = Field(..., description="Target execution window start (UTC)")
    requested_execution_end: datetime = Field(..., description="Target execution window end (UTC)")
    remarks: Optional[str] = Field(default=None, description="Engineering or operational notes")
    classification: DataClass = Field(default=DataClass.SYNTHETIC, description="Must remain SYNTHETIC")
    source_id: str = Field(default="SRC-TRACKMELD-SYNTHETIC-GEN", description="Generator provenance source")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def validate_execution_window(self) -> "WorkOrder":
        if self.requested_execution_start >= self.requested_execution_end:
            raise ValueError(
                f"requested_execution_start ({self.requested_execution_start}) must precede "
                f"requested_execution_end ({self.requested_execution_end})"
            )
        return self
