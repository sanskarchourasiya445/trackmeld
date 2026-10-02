"""Pydantic request schemas for planning and baseline scheduling endpoints."""

from typing import Optional
from pydantic import BaseModel, Field

from backend.app.domain.scheduling import (
    SchedulerType,
    PriorityConfig,
)


class BaselineScheduleRequest(BaseModel):
    """Requisition to execute a deterministic baseline scheduler."""
    scenario_id: str = Field(..., description="Operational scenario ID to schedule")
    scheduler_type: SchedulerType = Field(
        default=SchedulerType.PRIORITY_GREEDY,
        description="Baseline scheduling algorithm (FCFS or PRIORITY_GREEDY)"
    )
    priority_config: Optional[PriorityConfig] = Field(
        default=None,
        description="Optional custom priority scoring parameters"
    )
    max_candidate_attempts: int = Field(
        default=50,
        ge=5,
        le=200,
        description="Max candidate timepoints evaluated per task"
    )


class BenchmarkComparisonRequest(BaseModel):
    """Requisition to execute side-by-side benchmark comparison between baseline schedulers."""
    scenario_id: str = Field(..., description="Operational scenario ID to benchmark")
    priority_config: Optional[PriorityConfig] = Field(
        default=None,
        description="Optional custom priority scoring parameters"
    )
    max_candidate_attempts: int = Field(
        default=50,
        ge=5,
        le=200,
        description="Max candidate timepoints evaluated per task"
    )
