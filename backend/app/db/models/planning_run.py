"""SQLAlchemy model for persistent planning runs and optimization jobs."""

from datetime import datetime, timezone
from sqlalchemy import (
    String,
    Text,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class PlanningRunModel(Base):
    """Persistent execution job and audited outcome of a planning optimization run."""
    __tablename__ = "planning_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    scenario_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("operational_scenarios.scenario_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False, default="PENDING")
    stage: Mapped[str] = mapped_column(String(32), nullable=False, default="QUEUED")
    run_type: Mapped[str] = mapped_column(String(32), nullable=False, default="SINGLE")
    scheduler_type: Mapped[str] = mapped_column(String(32), nullable=False, default="CP_SAT")
    scheduler_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")

    planning_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    planning_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    snapshot_id: Mapped[str] = mapped_column(String(64), nullable=True)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=True)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=True)

    configuration_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    priority_configuration: Mapped[dict] = mapped_column(JSONB, nullable=True)
    optimization_configuration: Mapped[dict] = mapped_column(JSONB, nullable=True)
    objective_configuration: Mapped[dict] = mapped_column(JSONB, nullable=True)

    random_seed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    solver_name: Mapped[str] = mapped_column(String(64), nullable=False, default="OR-Tools CP-SAT")
    solver_version: Mapped[str] = mapped_column(String(32), nullable=False, default="9.15.6755")
    dataset_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1.0")

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    validation_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=True)
    execution_duration_ms: Mapped[float] = mapped_column(Float, nullable=True)

    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    worker_id: Mapped[str] = mapped_column(String(64), index=True, nullable=True)
    created_by: Mapped[str] = mapped_column(String(64), nullable=False, default="SYSTEM")
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=True)

    error_code: Mapped[str] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    error_details: Mapped[dict] = mapped_column(JSONB, nullable=True)

    result_summary: Mapped[dict] = mapped_column(JSONB, nullable=True)
    schedule_result: Mapped[dict] = mapped_column(JSONB, nullable=True)

    validation_status: Mapped[str] = mapped_column(String(32), nullable=True)
    validation_fingerprint: Mapped[str] = mapped_column(String(64), nullable=True)
    is_approvable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    validation_findings_summary: Mapped[dict] = mapped_column(JSONB, nullable=True)
    diagnostics_summary: Mapped[dict] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship back to scenario
    scenario = relationship("OperationalScenarioModel")

    __table_args__ = (
        Index("ix_planning_runs_status_created", "status", "created_at"),
        Index("ix_planning_runs_scenario_status_created", "scenario_id", "status", "created_at"),
    )
