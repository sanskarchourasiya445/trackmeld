"""Temporal domain models and half-open interval conventions.

Standardizes interval representation for TrackMeld:
- Convention: Half-open interval [start, end)
- Timezone: UTC timezone-aware datetimes
- Overlap rule: max(start1, start2) < min(end1, end2)
- Adjacency rule: end1 == start2 does NOT overlap
"""

from datetime import datetime, timezone
from typing import Optional, Tuple, List
from pydantic import BaseModel, Field, model_validator
from backend.app.domain.enums import DataClass, TraversalResolutionStatus


class TimeInterval(BaseModel):
    """Half-open continuous time interval [start, end)."""

    start: datetime = Field(..., description="Inclusive start timestamp (UTC)")
    end: datetime = Field(..., description="Exclusive end timestamp (UTC)")

    model_config = {"frozen": True}

    @model_validator(mode="after")
    def validate_utc_and_bounds(self) -> "TimeInterval":
        # Ensure UTC timezone awareness
        if self.start.tzinfo is None:
            object.__setattr__(self, "start", self.start.replace(tzinfo=timezone.utc))
        if self.end.tzinfo is None:
            object.__setattr__(self, "end", self.end.replace(tzinfo=timezone.utc))
        return self

    @property
    def is_valid(self) -> bool:
        """A strictly valid non-empty interval requires start < end."""
        return self.start < self.end

    @property
    def duration_seconds(self) -> float:
        return (self.end - self.start).total_seconds()

    @property
    def duration_minutes(self) -> float:
        return self.duration_seconds / 60.0

    @property
    def duration_hours(self) -> float:
        return self.duration_seconds / 3600.0

    def overlaps(self, other: "TimeInterval") -> bool:
        """Determine if two half-open intervals [s1, e1) and [s2, e2) overlap.
        
        Under half-open semantics:
        max(s1, s2) < min(e1, e2)
        If e1 == s2, max(s1, s2) == min(e1, e2), returning False (strictly adjacent).
        """
        if not self.is_valid or not other.is_valid:
            return False
        return max(self.start, other.start) < min(self.end, other.end)

    def is_adjacent_to(self, other: "TimeInterval") -> bool:
        """Check if two intervals meet at an exact boundary without overlapping."""
        if not self.is_valid or not other.is_valid:
            return False
        return self.end == other.start or other.end == self.start

    def intersection(self, other: "TimeInterval") -> Optional["TimeInterval"]:
        """Compute the intersecting half-open interval if one exists."""
        if not self.overlaps(other):
            return None
        return TimeInterval(
            start=max(self.start, other.start),
            end=min(self.end, other.end),
        )

    def contains_point(self, point: datetime) -> bool:
        """Half-open point containment: start <= point < end."""
        if point.tzinfo is None:
            point = point.replace(tzinfo=timezone.utc)
        return self.start <= point < self.end

    def contains_interval(self, other: "TimeInterval") -> bool:
        """Check if self completely encloses other: self.start <= other.start and other.end <= self.end."""
        if not self.is_valid or not other.is_valid:
            return False
        return self.start <= other.start and other.end <= self.end

    def __str__(self) -> str:
        return f"[{self.start.isoformat()}, {self.end.isoformat()})"


class PlanningHorizon(BaseModel):
    """The master planning horizon bounding all scenario scheduling."""

    start: datetime = Field(..., description="Horizon start timestamp (UTC)")
    end: datetime = Field(..., description="Horizon end timestamp (UTC)")
    timezone_name: str = Field(default="UTC", description="Operating timezone (e.g. UTC, Asia/Kolkata)")

    model_config = {"frozen": True}

    @model_validator(mode="after")
    def validate_horizon(self) -> "PlanningHorizon":
        if self.start.tzinfo is None:
            object.__setattr__(self, "start", self.start.replace(tzinfo=timezone.utc))
        if self.end.tzinfo is None:
            object.__setattr__(self, "end", self.end.replace(tzinfo=timezone.utc))
        if self.start >= self.end:
            raise ValueError(f"Planning horizon start ({self.start}) must precede end ({self.end}).")
        return self

    @property
    def interval(self) -> TimeInterval:
        return TimeInterval(start=self.start, end=self.end)

    @property
    def duration_hours(self) -> float:
        return (self.end - self.start).total_seconds() / 3600.0

    def contains_interval(self, interval: TimeInterval) -> bool:
        """Ensure an interval lies strictly inside the planning horizon."""
        return self.start <= interval.start and interval.end <= self.end

    def contains_point(self, point: datetime) -> bool:
        if point.tzinfo is None:
            point = point.replace(tzinfo=timezone.utc)
        return self.start <= point < self.end


class TrainPass(BaseModel):
    """A train's continuous occupancy of a block section or station during its journey."""

    pass_id: str = Field(..., description="Unique pass identifier (e.g. PASS-12301-SEC-NDLS-GZB-D0)")
    train_id: str = Field(..., description="Train identifier")
    train_number: str = Field(..., description="Official train number")
    section_id: Optional[str] = Field(default=None, description="Affected block section ID")
    station_id: Optional[str] = Field(default=None, description="Affected station ID (if station dwell)")
    from_station_id: Optional[str] = Field(default=None, description="Origin station of the section traverse")
    to_station_id: Optional[str] = Field(default=None, description="Destination station of the section traverse")
    interval: TimeInterval = Field(..., description="Occupancy half-open interval [start, end)")
    movement_type: str = Field(default="SECTION_TRAVERSAL", description="SECTION_TRAVERSAL or STATION_DWELL")
    source_movement_ids: List[str] = Field(default_factory=list, description="IDs of underlying timetable records")
    classification: DataClass = Field(default=DataClass.REAL, description="Data provenance classification")

    @property
    def duration_minutes(self) -> float:
        return self.interval.duration_minutes


class TrainTraversal(BaseModel):
    """Explicit ordered physical section traversal representation for a train pass.
    
    Distinguishes:
    1. TrainMovement: Timetable station occurrence
    2. TrainPass: Station-to-station timing interval
    3. TrainTraversal: Physical block section traversal with deterministic transit intervals
    """
    traversal_id: str = Field(..., description="Unique traversal ID (e.g. TRV-12301-SEC-NDLS-GZB-S1-D0)")
    train_id: str = Field(..., description="Train identifier")
    train_number: str = Field(..., description="Official train number")
    source_pass_id: str = Field(..., description="References parent TrainPass pass_id")
    section_id: Optional[str] = Field(default=None, description="Physical block section traversed")
    from_station_id: str = Field(..., description="Traversed segment origin station ID")
    to_station_id: str = Field(..., description="Traversed segment destination station ID")
    sequence_order: int = Field(..., description="1-based sequence order within the parent pass")
    interval: TimeInterval = Field(..., description="Deterministic physical occupancy half-open interval [entry_time, exit_time)")
    traversal_track_id: Optional[str] = Field(default=None, description="Physical running track ID (None in Phase 16E-B, unassigned)")
    resolution_status: TraversalResolutionStatus = Field(default=TraversalResolutionStatus.DIRECT_SECTION, description="Expansion resolution status")
    unresolved_reason: Optional[str] = Field(default=None, description="Diagnostic reason if traversal could not be resolved")
    classification: DataClass = Field(default=DataClass.DERIVED, description="Data provenance classification")

    @property
    def entry_time(self) -> datetime:
        return self.interval.start

    @property
    def exit_time(self) -> datetime:
        return self.interval.end

    @property
    def duration_minutes(self) -> float:
        return self.interval.duration_minutes
