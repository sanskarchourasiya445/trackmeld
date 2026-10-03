"""Strongly-typed validation, diagnostic, and relaxation domain models for TrackMeld."""

from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ValidationStatus(str, Enum):
    """Authoritative outcome of an independent schedule validation run."""
    VALID = "VALID"
    INVALID = "INVALID"
    UNKNOWN = "UNKNOWN"


class ValidationSeverity(str, Enum):
    """Severity classification of validation findings."""
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class ValidationCategory(str, Enum):
    """Categorization of independent validation checks."""
    STRUCTURAL = "STRUCTURAL"
    TEMPORAL = "TEMPORAL"
    HORIZON = "HORIZON"
    WINDOW = "WINDOW"
    DURATION = "DURATION"
    SECTION = "SECTION"
    MULTI_SECTION = "MULTI_SECTION"
    TRAIN_MOVEMENT = "TRAIN_MOVEMENT"
    RESOURCE = "RESOURCE"
    DEPENDENCY = "DEPENDENCY"
    MANDATORY = "MANDATORY"
    RULE = "RULE"
    PROVENANCE = "PROVENANCE"
    SOLVER_OUTPUT = "SOLVER_OUTPUT"
    TRACK = "TRACK"


class ValidationFinding(BaseModel):
    """Diagnostic detail of a single rule, structural, or safety issue detected in a schedule."""
    code: str = Field(..., description="Unique machine-readable finding code")
    severity: ValidationSeverity = Field(..., description="ERROR blocks approval; WARNING indicates operational concern")
    category: ValidationCategory = Field(..., description="Category of the constraint check")
    message: str = Field(..., description="Human-readable description of the finding")
    task_id: Optional[str] = Field(default=None, description="Task ID involved in finding, if applicable")
    section_id: Optional[str] = Field(default=None, description="Section ID involved, if applicable")
    resource_id: Optional[str] = Field(default=None, description="Resource ID involved, if applicable")
    train_movement_id: Optional[str] = Field(default=None, description="Train pass/movement ID involved, if applicable")
    evidence: Optional[Dict[str, Any]] = Field(default=None, description="Concrete evidence payload proving finding")
    expected: Optional[str] = Field(default=None, description="Expected state according to authoritative requirements")
    actual: Optional[str] = Field(default=None, description="Actual state found in the schedule output")
    rule_reference: Optional[str] = Field(default=None, description="Rule code or provenance reference if applicable")

    def sort_key(self) -> tuple:
        """Deterministic sort key for reproducible findings ordering."""
        return (
            self.category.value,
            self.task_id or "",
            self.section_id or "",
            self.resource_id or "",
            self.train_movement_id or "",
            self.code,
        )


class ScheduleValidationResult(BaseModel):
    """Authoritative outcome contract returned by the Independent Schedule Validator."""
    status: ValidationStatus = Field(..., description="Overall validation status: VALID, INVALID, or UNKNOWN")
    valid: bool = Field(..., description="True if and only if zero ERROR findings exist")
    is_approvable: bool = Field(..., description="True if schedule passes the gate for human approval")
    findings: List[ValidationFinding] = Field(default_factory=list, description="Sorted list of all validation findings")
    error_count: int = Field(default=0, description="Total count of ERROR severity findings")
    warning_count: int = Field(default=0, description="Total count of WARNING severity findings")
    info_count: int = Field(default=0, description="Total count of INFO severity findings")
    checked_task_count: int = Field(default=0, description="Total scheduled tasks validated")
    checked_section_count: int = Field(default=0, description="Total physical sections audited")
    checked_resource_count: int = Field(default=0, description="Total maintenance resources verified")
    checked_train_movement_count: int = Field(default=0, description="Total corridor train movements checked for collision")
    validator_version: str = Field(default="1.0.0", description="Independent validator engine version")
    input_snapshot_id: str = Field(..., description="Snapshot ID against which schedule was verified")
    schedule_identity: str = Field(..., description="Deterministic SHA-256 fingerprint of the evaluated schedule")
    validation_runtime_ms: float = Field(default=0.0, description="Validation elapsed execution latency in milliseconds")
    checks_executed: List[str] = Field(default_factory=list, description="Names of all independent checks performed")
    approval_gate_message: str = Field(default="", description="Explanatory decision gate rationale")


class DiagnosticStatus(str, Enum):
    """Classification of an unscheduled task diagnostic investigation."""
    DIAGNOSED = "DIAGNOSED"
    FEASIBLE_ALTERNATIVE_FOUND = "FEASIBLE_ALTERNATIVE_FOUND"
    UNRESOLVED = "UNRESOLVED"
    UNKNOWN = "UNKNOWN"


class RelaxationScenarioType(str, Enum):
    """Types of controlled constraint relaxations analyzed for diagnostic purposes."""
    IGNORE_TRAIN_CONFLICTS = "IGNORE_TRAIN_CONFLICTS"
    IGNORE_SECTION_OCCUPANCY = "IGNORE_SECTION_OCCUPANCY"
    IGNORE_RESOURCE_AVAILABILITY = "IGNORE_RESOURCE_AVAILABILITY"
    IGNORE_DEPENDENCIES = "IGNORE_DEPENDENCIES"
    WIDEN_TASK_WINDOW = "WIDEN_TASK_WINDOW"


class RelaxationFinding(BaseModel):
    """Diagnostic outcome of a hypothetical constraint relaxation.

    CRITICAL SAFETY INVARIANT:
    This record is strictly diagnostic and hypothetical. It NEVER authorizes or
    recommends violating safety or operational rules in production schedules.
    """
    scenario_type: RelaxationScenarioType = Field(..., description="Type of constraint relaxed hypothetically")
    description: str = Field(..., description="Description of the hypothetical relaxation scenario")
    feasible: bool = Field(..., description="True if a placement becomes possible under this relaxation")
    candidate_start: Optional[datetime] = Field(default=None, description="Hypothetical start time if feasible")
    candidate_end: Optional[datetime] = Field(default=None, description="Hypothetical end time if feasible")
    blocking_entities: List[str] = Field(default_factory=list, description="Specific IDs of entities blocking placement")
    relaxation_magnitude: Optional[str] = Field(default=None, description="Quantification of relaxation (e.g. '+60 mins window')")
    hypothetical: bool = Field(default=True, description="Strictly True: never represents an approvable placement")
    approvable: bool = Field(default=False, description="Strictly False: relaxed placements are not approvable")
    explanation: str = Field(default="", description="Diagnostic explanation of what constraint caused infeasibility")


class UnscheduledTaskDiagnostic(BaseModel):
    """Structured diagnostic root-cause explanation for an unplaced maintenance task."""
    task_id: str
    task_code: str
    mandatory: bool
    priority_score: Optional[float] = None
    status: DiagnosticStatus
    primary_reason: str
    reason_codes: List[str] = Field(default_factory=list)
    conflicting_tasks: List[str] = Field(default_factory=list)
    conflicting_train_movements: List[str] = Field(default_factory=list)
    conflicting_resources: List[str] = Field(default_factory=list)
    conflicting_windows: List[str] = Field(default_factory=list)
    dependency_blockers: List[str] = Field(default_factory=list)
    affected_sections: List[str] = Field(default_factory=list)
    rule_blockers: List[str] = Field(default_factory=list)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    relaxation_analyses: List[RelaxationFinding] = Field(default_factory=list)


class DiagnosticsReport(BaseModel):
    """Report detailing root-cause diagnostics and relaxation analyses for all unplaced tasks."""
    scenario_id: str
    snapshot_id: str
    total_unscheduled_tasks: int
    diagnostics: List[UnscheduledTaskDiagnostic] = Field(default_factory=list)
    execution_time_ms: float = 0.0
