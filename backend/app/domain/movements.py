import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from backend.app.domain.enums import DataClass, MovementBasis, MovementType


TIME_PATTERN = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


class TrainMovement(BaseModel):
    """Scheduled train stop or transit event along a corridor timetable."""
    movement_id: str = Field(..., description="Unique timetable movement identifier (e.g. MOV-12301-HWH-01)")
    train_id: str = Field(..., description="Referenced train identifier (TRN-xxxxx)")
    train_number: str = Field(..., description="Official train number")
    train_name: str = Field(..., description="Train commercial name")
    station_id: str = Field(..., description="Station identifier where event takes place")
    station_code: str = Field(..., description="Station alphabetical code")
    station_name: str = Field(..., description="Station English name")
    stop_sequence: int = Field(..., ge=1, description="1-indexed sequence order along the journey")
    scheduled_arrival: Optional[str] = Field(default=None, description="24-hour HH:MM arrival time (null for origin)")
    scheduled_departure: Optional[str] = Field(default=None, description="24-hour HH:MM departure time (null for destination)")
    day_offset: int = Field(default=0, ge=0, description="Day index from journey origin (Day 0, Day 1, etc.)")
    distance_km: float = Field(default=0.0, ge=0.0, description="Cumulative distance from origin in kilometers")
    movement_type: str = Field(..., description="SCHEDULED_ORIGIN, SCHEDULED_INTERMEDIATE_STOP, or SCHEDULED_DESTINATION")
    basis: str = Field(default="SCHEDULED_TIMETABLE", description="SCHEDULED_TIMETABLE or OPERATIONAL_LOG")
    track_id: Optional[str] = Field(default=None, description="Optional referenced track identifier (e.g. TRK-NDLS-GZB-UP)")
    classification: DataClass = Field(default=DataClass.REAL, description="Data authenticity classification")
    source_id: str = Field(..., description="Referenced source publication")
    source_reference: Optional[str] = Field(default=None, description="Table or schedule reference citation")

    @field_validator("scheduled_arrival", "scheduled_departure")
    @classmethod
    def validate_time_format(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not TIME_PATTERN.match(v):
            raise ValueError(f"Time value '{v}' must be in 24-hour HH:MM format.")
        return v
