"""Domain schemas and enums for Phase 8 Planning Jobs and Persistence."""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from backend.app.domain.scheduling import (
    SchedulerType,
    SchedulerStatus,
    PriorityConfig,
    ScheduleResult,
)
from backend.app.services.optimization.solver_config import OptimizationConfig


class PlanningRunStatus(str, Enum):
    """Lifecycle status of a planning run job."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    VALIDATING = "VALIDATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"


class PlanningRunStage(str, Enum):
    """Current execution stage of a running planning job."""
    QUEUED = "QUEUED"
    CLAIMED = "CLAIMED"
    LOADING_SNAPSHOT = "LOADING_SNAPSHOT"
    SOLVING = "SOLVING"
    VALIDATING = "VALIDATING"
    DIAGNOSING = "DIAGNOSING"
    PERSISTING = "PERSISTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"


class CreatePlanningRunRequest(BaseModel):
    """Requisition payload to create a new persistent asynchronous planning job."""
    scenario_id: str = Field(..., description="Operational scenario ID to schedule")
    scheduler_type: SchedulerType = Field(
        default=SchedulerType.CP_SAT,
        description="Algorithm strategy: FCFS, PRIORITY_GREEDY, or CP_SAT"
    )
    priority_config: Optional[PriorityConfig] = Field(
        default=None,
        description="Optional priority scoring parameters and heuristic feature weights"
    )
    optimization_config: Optional[OptimizationConfig] = Field(
        default=None,
        description="Optional CP-SAT optimization parameters (time limit, workers, seed)"
    )
    validate_after_solve: bool = Field(
        default=True,
        description="Execute independent validation and root-cause diagnostics upon solve"
    )
    time_limit_seconds: Optional[float] = Field(
        default=None,
        ge=1.0,
        le=300.0,
        description="Override solver time limit in seconds"
    )
    num_search_workers: Optional[int] = Field(
        default=None,
        ge=1,
        le=16,
        description="Search workers (default 1 for deterministic reproducibility)"
    )
    random_seed: Optional[int] = Field(
        default=None,
        ge=0,
        description="Search randomization seed"
    )
    idempotency_key: Optional[str] = Field(
        default=None,
        max_length=128,
        description="Optional client idempotency key to prevent duplicate job creation"
    )
    solver_mode: Optional[str] = Field(
        default="TRACK_AWARE_CONSERVATIVE",
        description="Spatial optimization mode: 'TRACK_AWARE_CONSERVATIVE' or 'WHOLE_SECTION'"
    )


class PlanningRunProgress(BaseModel):
    """Real-time progress telemetry for polling clients."""
    stage: PlanningRunStage
    message: str
    percent_complete: Optional[float] = None


class PlanningRunSummary(BaseModel):
    """Concise representation of a planning run for list views."""
    run_id: str
    scenario_id: str
    status: PlanningRunStatus
    stage: PlanningRunStage
    scheduler_type: SchedulerType
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_duration_ms: Optional[float] = None
    validation_status: Optional[str] = None
    is_approvable: bool = False
    total_tasks: Optional[int] = None
    scheduled_tasks: Optional[int] = None
    error_code: Optional[str] = None


class PlanningRunDetailResponse(BaseModel):
    """Comprehensive lifecycle and result representation of a planning run."""
    run_id: str
    scenario_id: str
    status: PlanningRunStatus
    stage: PlanningRunStage
    scheduler_type: SchedulerType
    scheduler_version: str
    planning_start: Optional[datetime] = None
    planning_end: Optional[datetime] = None
    snapshot_id: Optional[str] = None
    snapshot_hash: Optional[str] = None
    input_hash: Optional[str] = None
    configuration_snapshot: Dict[str, Any] = Field(default_factory=dict)
    random_seed: int
    solver_name: str
    solver_version: str
    dataset_version: str
    created_at: datetime
    started_at: Optional[datetime] = None
    validation_started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    execution_duration_ms: Optional[float] = None
    heartbeat_at: Optional[datetime] = None
    attempt_count: int
    worker_id: Optional[str] = None
    created_by: str
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    result_summary: Optional[Dict[str, Any]] = None
    validation_status: Optional[str] = None
    validation_fingerprint: Optional[str] = None
    is_approvable: bool = False
    validation_findings_summary: Optional[Dict[str, Any]] = None
    diagnostics_summary: Optional[Dict[str, Any]] = None
    status_url: str
    result_url: Optional[str] = None
    progress: PlanningRunProgress


class CreatePlanningRunResponse(BaseModel):
    """Immediate acknowledgment response when an asynchronous planning run is queued."""
    run_id: str
    scenario_id: str
    status: PlanningRunStatus
    stage: PlanningRunStage
    scheduler_type: SchedulerType
    created_at: datetime
    status_url: str
