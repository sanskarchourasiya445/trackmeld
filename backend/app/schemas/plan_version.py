"""Pydantic schemas and enums for Plan Versions, Review Workflow, and Governance Audit."""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class PlanVersionStatus(str, Enum):
    """Lifecycle status of a plan version under human governance."""
    PENDING_REVIEW = "PENDING_REVIEW"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


class PlanReviewAction(str, Enum):
    """Actions performed during human review of a plan version."""
    START_REVIEW = "START_REVIEW"
    COMMENT = "COMMENT"
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class GovernanceEventType(str, Enum):
    """Immutable audit event categories."""
    PLAN_VERSION_CREATED = "PLAN_VERSION_CREATED"
    PLAN_REVIEW_STARTED = "PLAN_REVIEW_STARTED"
    PLAN_COMMENT_ADDED = "PLAN_COMMENT_ADDED"
    PLAN_APPROVED = "PLAN_APPROVED"
    PLAN_REJECTED = "PLAN_REJECTED"
    PLAN_SUPERSEDED = "PLAN_SUPERSEDED"


# =============================================================================
# REQUEST SCHEMAS
# =============================================================================

class CreatePlanVersionRequest(BaseModel):
    """Request payload to instantiate a governance plan version from a completed planning run."""
    comment: Optional[str] = Field(default=None, description="Optional creation note or context")


class ApprovePlanRequest(BaseModel):
    """Request payload for an authorized human approval action."""
    comment: Optional[str] = Field(default=None, max_length=4000, description="Optional human approval note or operational sign-off rationale")
    declared_reviewer_name: Optional[str] = Field(
        default=None,
        max_length=128,
        description="Optional declared reviewing officer name for audit attestation (non-authoritative metadata)",
    )
    declared_reviewer_role: Optional[str] = Field(
        default=None,
        max_length=128,
        description="Optional declared reviewing officer designation or role for audit attestation (non-authoritative metadata)",
    )


class RejectPlanRequest(BaseModel):
    """Request payload for an explicit human rejection action."""
    reason: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        description="Mandatory clear explanation of operational or safety rationale for rejecting the schedule",
    )


class AddReviewCommentRequest(BaseModel):
    """Request payload to attach a commentary entry to a plan under review."""
    comment: str = Field(
        ...,
        min_length=3,
        max_length=4000,
        description="Human reviewer feedback or operational observation",
    )


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================

class PlanReviewCommentResponse(BaseModel):
    """Serialized review commentary or state action event."""
    review_id: str
    plan_version_id: str
    actor_id: str
    actor_username: str
    action: str
    comment: str
    created_at: datetime


class AuditEventResponse(BaseModel):
    """Factual, append-only governance audit record."""
    event_id: str
    entity_type: str
    entity_id: str
    event_type: str
    actor_id: str
    actor_username: str
    actor_role: str
    timestamp: datetime
    previous_state: Optional[str] = None
    new_state: Optional[str] = None
    reason: Optional[str] = None
    comment: Optional[str] = None
    schedule_identity: Optional[str] = None
    snapshot_hash: Optional[str] = None
    input_hash: Optional[str] = None
    event_metadata: Optional[Dict[str, Any]] = None
    sequence_number: Optional[int] = None
    previous_event_hash: Optional[str] = None
    event_hash: Optional[str] = None


class PlanVersionSummary(BaseModel):
    """Concise representation of a plan version for listings and summary dashboards."""
    plan_version_id: str
    scenario_id: str
    planning_run_id: str
    version_number: int
    status: PlanVersionStatus
    scheduler_type: str
    schedule_identity: str
    is_approvable: bool
    validation_status: str
    result_summary: Dict[str, Any]
    created_at: datetime
    created_by: str
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    rejected_at: Optional[datetime] = None
    rejected_by: Optional[str] = None
    superseded_at: Optional[datetime] = None
    superseded_by: Optional[str] = None


class PlanVersionDetail(BaseModel):
    """Comprehensive plan version representation including verified schedule and review trail."""
    plan_version_id: str
    scenario_id: str
    planning_run_id: str
    version_number: int
    status: PlanVersionStatus
    scheduler_type: str
    scheduler_version: str
    solver_name: str
    solver_version: str
    dataset_version: str

    schedule_identity: str
    snapshot_hash: str
    input_hash: str

    validation_status: str
    is_approvable: bool
    validation_findings_summary: Optional[Dict[str, Any]] = None
    diagnostics_summary: Optional[Dict[str, Any]] = None

    configuration_snapshot: Dict[str, Any]
    priority_configuration: Optional[Dict[str, Any]] = None
    optimization_configuration: Optional[Dict[str, Any]] = None
    result_summary: Dict[str, Any]
    schedule_result: Dict[str, Any]

    created_at: datetime
    created_by: str
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    rejected_at: Optional[datetime] = None
    rejected_by: Optional[str] = None

    review_comment: Optional[str] = None
    rejection_reason: Optional[str] = None

    previous_plan_version_id: Optional[str] = None
    superseded_at: Optional[datetime] = None
    superseded_by: Optional[str] = None
    updated_at: datetime

    review_comments: List[PlanReviewCommentResponse] = Field(default_factory=list)
