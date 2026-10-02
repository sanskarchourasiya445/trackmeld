"""SQLAlchemy models for Plan Versions, Review Comments, and Immutable Governance Audit Events."""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    String,
    Text,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class PlanVersionModel(Base):
    """Immutable, versioned operational plan candidate subject to human governance."""
    __tablename__ = "plan_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_version_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    scenario_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("operational_scenarios.scenario_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    planning_run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("planning_runs.run_id", ondelete="RESTRICT"),
        unique=True,
        index=True,
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False, default="PENDING_REVIEW")

    # Cryptographic fingerprints and provenance
    schedule_identity: Mapped[str] = mapped_column(String(64), nullable=False)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Serialized schedule and diagnostics
    schedule_result: Mapped[dict] = mapped_column(JSONB, nullable=False)
    result_summary: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    validation_status: Mapped[str] = mapped_column(String(32), nullable=False, default="VALID")
    is_approvable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    validation_findings_summary: Mapped[dict] = mapped_column(JSONB, nullable=True)
    diagnostics_summary: Mapped[dict] = mapped_column(JSONB, nullable=True)

    # Solver parameters
    scheduler_type: Mapped[str] = mapped_column(String(32), nullable=False)
    scheduler_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")
    solver_name: Mapped[str] = mapped_column(String(64), nullable=False)
    solver_version: Mapped[str] = mapped_column(String(32), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(32), nullable=False)

    configuration_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    priority_configuration: Mapped[dict] = mapped_column(JSONB, nullable=True)
    optimization_configuration: Mapped[dict] = mapped_column(JSONB, nullable=True)

    # Lifecycle and human actors
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    created_by: Mapped[str] = mapped_column(String(64), nullable=False)

    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    rejected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    review_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Superseding lineage
    previous_plan_version_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    superseded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    superseded_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    scenario = relationship("OperationalScenarioModel")
    planning_run = relationship("PlanningRunModel")
    review_comments = relationship("PlanReviewCommentModel", back_populates="plan_version", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("scenario_id", "version_number", name="uq_plan_versions_scenario_version"),
        Index("ix_plan_versions_scenario_status", "scenario_id", "status"),
        Index("ix_plan_versions_created_at", "created_at"),
        Index("ix_plan_versions_approved_at", "approved_at"),
    )


class PlanReviewCommentModel(Base):
    """Immutable audit record of a human reviewer's comment or review state event."""
    __tablename__ = "plan_review_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    review_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    plan_version_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("plan_versions.plan_version_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    actor_id: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_username: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)  # START_REVIEW, COMMENT, APPROVE, REJECT
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    plan_version = relationship("PlanVersionModel", back_populates="review_comments")


class GovernanceAuditEventModel(Base):
    """Append-only immutable governance ledger event."""
    __tablename__ = "governance_audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor_username: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(32), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )
    previous_state: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    new_state: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    schedule_identity: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    snapshot_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    input_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    event_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_audit_events_entity", "entity_type", "entity_id"),
        Index("ix_audit_events_actor", "actor_id"),
        Index("ix_audit_events_timestamp", "timestamp"),
        Index("ix_audit_events_type", "event_type"),
    )
