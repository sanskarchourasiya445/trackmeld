from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, model_validator
from backend.app.domain.enums import (
    DataClass,
    WorkDepartment,
    ResourceType,
    AvailabilityStatus,
)


class MaintenanceResource(BaseModel):
    """Crew, track machine, tower wagon, or equipment used in maintenance blocks."""
    resource_id: str = Field(..., description="Unique resource identifier (e.g. RES-TM-001)")
    resource_code: str = Field(..., description="Business key code")
    name: str = Field(..., description="Human-readable resource name (e.g. BCM-01 Ballast Cleaner)")
    resource_type: ResourceType = Field(..., description="Category: CREW, TRACK_MACHINE, OHE_EQUIPMENT, etc.")
    department: WorkDepartment = Field(..., description="Operating railway department")
    description: Optional[str] = Field(default=None, description="Technical specifications or gang notes")
    capacity: int = Field(default=1, gt=0, description="Available simultaneous unit capacity")
    home_station: Optional[str] = Field(default=None, description="Station ID where machine or gang is depot-based")
    qualification_tags: List[str] = Field(default_factory=list, description="Qualifications (e.g. OHE_CERTIFIED)")
    classification: DataClass = Field(default=DataClass.SYNTHETIC, description="Must remain SYNTHETIC")
    source_id: str = Field(default="SRC-TRACKMELD-SYNTHETIC-GEN", description="Generator provenance source")


class ResourceAvailability(BaseModel):
    """Calendar interval when a resource is available or undergoing maintenance."""
    availability_id: str = Field(..., description="Unique availability window ID")
    resource_id: str = Field(..., description="Referenced resource ID")
    scenario_id: str = Field(..., description="Associated operational scenario ID")
    available_from: datetime = Field(..., description="Start of availability window (UTC)")
    available_until: datetime = Field(..., description="End of availability window (UTC)")
    availability_status: AvailabilityStatus = Field(default=AvailabilityStatus.AVAILABLE)
    quantity: int = Field(default=1, gt=0, description="Capacity quantity available in this window")

    @model_validator(mode="after")
    def validate_interval(self) -> "ResourceAvailability":
        if self.available_from >= self.available_until:
            raise ValueError(f"available_from ({self.available_from}) must precede available_until ({self.available_until})")
        return self


class TaskResourceRequirement(BaseModel):
    """Resource requirement attached to a maintenance task."""
    requirement_id: str = Field(..., description="Unique requirement identifier")
    task_id: str = Field(..., description="Referenced maintenance task ID")
    resource_id: Optional[str] = Field(default=None, description="Specific pinned resource ID if required")
    resource_type: ResourceType = Field(..., description="Category of resource required")
    quantity: int = Field(default=1, gt=0, description="Quantity required")
    mandatory: bool = Field(default=True, description="Whether requirement is hard or optional")
