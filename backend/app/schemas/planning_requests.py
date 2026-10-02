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
    include_cpsat: bool = Field(
        default=False,
        description="Include CP-SAT solver in the side-by-side comparison"
    )
    cpsat_time_limit: float = Field(
        default=10.0,
        ge=0.1,
        le=300.0,
        description="CP-SAT time limit in seconds when include_cpsat is True"
    )


class OptimizeScheduleRequest(BaseModel):
    """Requisition to execute the CP-SAT mathematical optimization solver."""
    scenario_id: str = Field(..., description="Operational scenario ID to optimize")
    priority_config: Optional[PriorityConfig] = Field(
        default=None,
        description="Optional custom priority scoring parameters"
    )
    time_limit_seconds: float = Field(
        default=30.0,
        gt=0.1,
        le=300.0,
        description="Maximum CP-SAT execution wall time in seconds"
    )
    num_search_workers: int = Field(
        default=1,
        ge=1,
        le=16,
        description="Search workers (default 1 for deterministic reproducibility)"
    )
    random_seed: int = Field(
        default=0,
        ge=0,
        description="Random seed for search initialization"
    )
    log_search_progress: bool = Field(
        default=False,
        description="Emit CP-SAT search log"
    )

