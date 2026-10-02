"""Domain models for deterministic feasibility, compatibility evaluation, and rule evidence.

Implements the four-tier constraint severity hierarchy:
- HARD: Physical or regulatory safety barrier. If violated, placement is infeasible.
- SOFT: Operational optimization preference. If violated, placement is feasible but flagged.
- DIAGNOSTIC_ONLY: Advisory notes or prototype-level telemetry.
- UNVERIFIED: Unverified domain assumptions. Invariant: NEVER promotes to HARD!
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from backend.app.domain.temporal import TimeInterval
from backend.app.domain.enums import RuleClass


class ConstraintSeverity(str, Enum):
    """Categorization of scheduling constraint boundaries."""
    HARD = "HARD"
    SOFT = "SOFT"
    DIAGNOSTIC_ONLY = "DIAGNOSTIC_ONLY"
    UNVERIFIED = "UNVERIFIED"


class ReasonCode(str, Enum):
    """Stable, machine-readable explanation codes for scheduling decisions."""
    INVALID_INTERVAL = "INVALID_INTERVAL"
    OUTSIDE_PLANNING_HORIZON = "OUTSIDE_PLANNING_HORIZON"
    TASK_WINDOW_CONFLICT = "TASK_WINDOW_CONFLICT"
    TRAIN_MOVEMENT_CONFLICT = "TRAIN_MOVEMENT_CONFLICT"
    SECTION_OCCUPANCY_CONFLICT = "SECTION_OCCUPANCY_CONFLICT"
    RESOURCE_UNAVAILABLE = "RESOURCE_UNAVAILABLE"
    RESOURCE_OVERLAP = "RESOURCE_OVERLAP"
    DEPENDENCY_NOT_SATISFIED = "DEPENDENCY_NOT_SATISFIED"
    TRAFFIC_BLOCK_REQUIRED = "TRAFFIC_BLOCK_REQUIRED"
    POWER_BLOCK_REQUIRED = "POWER_BLOCK_REQUIRED"
    PTW_REQUIRED = "PTW_REQUIRED"
    MULTI_SECTION_CONFLICT = "MULTI_SECTION_CONFLICT"
    UNVERIFIED_RULE = "UNVERIFIED_RULE"


class ConflictType(str, Enum):
    """Granular classification of operational collisions."""
    INTERVAL_INVALID = "INTERVAL_INVALID"
    HORIZON_BREACH = "HORIZON_BREACH"
    WINDOW_BREACH = "WINDOW_BREACH"
    TRAIN_CROSSING = "TRAIN_CROSSING"
    SECTION_OCCUPANCY = "SECTION_OCCUPANCY"
    RESOURCE_SHORTAGE = "RESOURCE_SHORTAGE"
    RESOURCE_BUSY = "RESOURCE_BUSY"
    PRECEDENCE_VIOLATION = "PRECEDENCE_VIOLATION"
    BLOCK_MISMATCH = "BLOCK_MISMATCH"
    UNVERIFIED_CONSTRAINT = "UNVERIFIED_CONSTRAINT"


class ConflictDetail(BaseModel):
    """Diagnostic information for an individual feasibility conflict."""
    conflict_type: ConflictType
    severity: ConstraintSeverity
    reason_code: ReasonCode
    message: str
    conflicting_entity_type: str = Field(
        ...,
        description="Entity type responsible for the conflict (e.g. TRAIN_PASS, MAINTENANCE_TASK, RESOURCE, HORIZON, SECTION)"
    )
    conflicting_entity_id: str = Field(..., description="Identifier of the colliding entity")
    conflict_interval: Optional[TimeInterval] = Field(
        default=None,
        description="Exact temporal intersection where the conflict takes place"
    )
    evidence: Optional[Dict[str, Any]] = Field(default=None, description="Detailed conflict metadata")


class RuleEvidence(BaseModel):
    """Provenance and verification evidence for a rule evaluated during compatibility."""
    rule_id: str
    title: str
    rule_class: RuleClass
    source_id: str
    severity: ConstraintSeverity
    satisfied: bool
    explanation: str


class ScheduledTaskPlacement(BaseModel):
    """Representation of an already accepted/placed task used for collision checks."""
    task_id: str
    task_code: str
    section_id: str
    additional_section_ids: List[str] = Field(default_factory=list)
    interval: TimeInterval = Field(..., description="Active maintenance execution interval [start, end)")
    possession_interval: TimeInterval = Field(
        ...,
        description="Effective track possession interval including safety buffers [start - buf_before, end + buf_after)"
    )
    assigned_resource_ids: List[str] = Field(default_factory=list)
    requires_traffic_block: bool = True
    requires_power_block: bool = False


class CompatibilityResult(BaseModel):
    """Comprehensive structured outcome of a task placement evaluation."""
    task_id: str
    compatible: bool = Field(..., description="True if and only if zero HARD conflicts occurred")
    feasible_hard: bool = Field(..., description="True if no physical or safety barriers violated")
    admissible_soft: bool = Field(..., description="True if no soft operational preferences violated")
    evaluated_interval: TimeInterval = Field(..., description="Requested work execution interval")
    possession_interval: TimeInterval = Field(
        ...,
        description="Calculated possession window with safety buffers applied"
    )
    reason_codes: List[ReasonCode] = Field(default_factory=list, description="Aggregated unique reason codes")
    conflicts: List[ConflictDetail] = Field(default_factory=list, description="Itemized list of all detected conflicts")
    affected_sections: List[str] = Field(default_factory=list, description="All primary and secondary sections inspected")
    affected_movements: List[str] = Field(default_factory=list, description="Colliding train movement identifiers")
    affected_resources: List[str] = Field(default_factory=list, description="Contended or unavailable resource identifiers")
    rule_evidence: List[RuleEvidence] = Field(default_factory=list, description="Audit trail of evaluated domain rules")
