"""Domain models for deterministic baseline scheduling, priority scoring, and benchmark metrics.

Implements the common scheduling contract shared by:
- Baseline A: FCFS (First-Come, First-Served)
- Baseline B: Priority-Greedy
- Future Phase 6: CP-SAT Optimization
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, model_validator

from backend.app.domain.temporal import TimeInterval
from backend.app.domain.compatibility import (
    ReasonCode,
    ConflictDetail,
    ConstraintSeverity,
    ScheduledTaskPlacement,
)


class SchedulerType(str, Enum):
    """Categorization of deterministic scheduling strategies."""
    FCFS = "FCFS"
    PRIORITY_GREEDY = "PRIORITY_GREEDY"
    CP_SAT = "CP_SAT"  # Reserved for Phase 6


class SchedulerStatus(str, Enum):
    """Lifecycle status of a scheduling execution."""
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_UNSCHEDULED_TASKS = "COMPLETED_WITH_UNSCHEDULED_TASKS"
    FAILED = "FAILED"
    INVALID_INPUT = "INVALID_INPUT"
    OPTIMAL = "OPTIMAL"
    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"
    UNKNOWN = "UNKNOWN"


# =============================================================================
# PRIORITY SCORING MODELS
# =============================================================================

class PriorityComponent(BaseModel):
    """Detailed explainable breakdown of a single priority score factor."""
    feature_name: str
    raw_value: Any
    normalized_value: float = Field(..., ge=0.0, le=1.0, description="Normalized scale [0.0, 1.0]")
    weight: float = Field(..., ge=0.0, description="Configured feature weight")
    contribution: float = Field(..., ge=0.0, description="normalized_value * weight")
    description: str


class PriorityConfig(BaseModel):
    """Versioned and configurable priority scoring parameters."""
    config_id: str = Field(default="priority-config-v1", description="Configuration identifier")
    version: str = Field(default="1.0.0", description="Configuration semver")
    description: str = Field(
        default="Experimental scheduling weights for benchmark purposes.",
        description="Explicit notice that weights are experimental heuristics, not railway law."
    )
    mandatory_weight: float = Field(default=100.0, ge=0.0)
    urgency_weight: float = Field(default=40.0, ge=0.0)
    window_tightness_weight: float = Field(default=20.0, ge=0.0)
    dependency_weight: float = Field(default=20.0, ge=0.0)
    operational_impact_weight: float = Field(default=10.0, ge=0.0)

    model_config = {"frozen": True}


class PriorityScore(BaseModel):
    """Explainable total priority score with complete component breakdown."""
    task_id: str
    total_score: float = Field(..., ge=0.0, description="Sum of all component contributions")
    components: Dict[str, PriorityComponent] = Field(
        default_factory=dict,
        description="Explainable breakdown per feature"
    )
    config_id: str
    config_version: str

    model_config = {"frozen": True}


# =============================================================================
# SCHEDULER EXECUTION CONFIGURATION
# =============================================================================

class SchedulerConfig(BaseModel):
    """Execution parameters for baseline schedulers."""
    scheduler_type: Optional[SchedulerType] = None
    scheduler_version: str = Field(default="1.0.0")
    priority_config: PriorityConfig = Field(default_factory=PriorityConfig)
    max_candidate_attempts: int = Field(default=50, gt=0, description="Maximum candidate starts evaluated per task")
    candidate_policy: str = Field(default="EARLIEST_FEASIBLE", description="Candidate placement selection strategy")


# =============================================================================
# SCHEDULING RESULTS & DIAGNOSTICS
# =============================================================================

class ScheduledTaskResult(BaseModel):
    """Derived schedule placement for an accepted maintenance task."""
    task_id: str
    task_code: str
    interval: TimeInterval = Field(..., description="Active maintenance window [start, end)")
    possession_interval: TimeInterval = Field(
        ...,
        description="Effective corridor block with safety buffers [start - buf_before, end + buf_after)"
    )
    duration_minutes: int
    affected_sections: List[str] = Field(default_factory=list)
    assigned_resources: List[str] = Field(default_factory=list)
    priority_score: Optional[float] = None
    priority_breakdown: Optional[Dict[str, float]] = None
    sequence_order: int = Field(..., description="1-indexed sequence order in which task was scheduled")
    scheduling_reason: str = Field(default="FEASIBLE")
    rule_evidence_ids: List[str] = Field(default_factory=list)
    assigned_track_id: Optional[str] = Field(
        default=None,
        description="Physical running track ID if assigned and verified"
    )


class UnscheduledTaskResult(BaseModel):
    """Diagnostic outcome for a task that could not be placed feasibly."""
    task_id: str
    task_code: str
    mandatory: bool
    priority_score: Optional[float] = None
    reason_codes: List[ReasonCode] = Field(default_factory=list)
    conflicts: List[ConflictDetail] = Field(default_factory=list)
    attempted_candidates_count: int
    diagnostic_message: str


class TaskDecisionTrace(BaseModel):
    """Audit trail record explaining a single task's scheduling progression."""
    task_id: str
    task_code: str
    order_position: int
    priority_score: Optional[float] = None
    status: str = Field(..., description="SCHEDULED or UNSCHEDULED")
    candidates_evaluated: int
    selected_start: Optional[datetime] = None
    selected_end: Optional[datetime] = None
    primary_reason: str


class ScheduleMetrics(BaseModel):
    """Common scheduling evaluation metrics across all schedulers."""
    total_tasks: int
    scheduled_tasks: int
    unscheduled_tasks: int
    completion_rate: float = Field(..., description="scheduled_tasks / total_tasks")
    mandatory_tasks: int
    mandatory_scheduled: int
    mandatory_unscheduled: int
    mandatory_completion_rate: float = Field(
        ...,
        description="mandatory_scheduled / mandatory_tasks (1.0 if 0 mandatory tasks and scheduled > 0; 0.0 if 0 scheduled tasks)"
    )
    total_scheduled_duration_minutes: int
    total_possession_duration_minutes: int
    total_priority_score_available: float
    scheduled_priority_score: float
    unscheduled_priority_score: float
    priority_score_capture_rate: float = Field(
        ...,
        description="scheduled_priority_score / total_priority_score_available"
    )
    earliest_scheduled_start: Optional[datetime] = None
    latest_scheduled_end: Optional[datetime] = None


class ScheduleResult(BaseModel):
    """Authoritative outcome contract of a scheduling run."""
    schedule_id: str
    scheduler_type: SchedulerType
    scheduler_version: str
    scenario_id: str
    snapshot_id: str
    planning_start: datetime
    planning_end: datetime
    status: SchedulerStatus
    scheduled_tasks: List[ScheduledTaskResult] = Field(default_factory=list)
    unscheduled_tasks: List[UnscheduledTaskResult] = Field(default_factory=list)
    metrics: ScheduleMetrics
    configuration: Dict[str, Any]
    execution_time_ms: float
    decision_trace: List[TaskDecisionTrace] = Field(default_factory=list)
    solver_diagnostics: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Diagnostic metrics and metadata from mathematical optimizer"
    )
    validation: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Independent post-solve validation result and safety audit certification"
    )
    snapshot_hash: Optional[str] = Field(
        default=None,
        description="Authoritative 64-character SHA-256 planning snapshot hash for provenance verification"
    )


class BenchmarkComparisonResult(BaseModel):
    """Side-by-side comparison contract evaluating multiple scheduling strategies on the exact same snapshot."""
    scenario_id: str
    snapshot_id: str
    planning_start: datetime
    planning_end: datetime
    schedules: Dict[str, ScheduleResult]
    comparison_table: List[Dict[str, Any]]
