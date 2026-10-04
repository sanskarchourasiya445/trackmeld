from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    String,
    Text,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
    Index,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, TimestampMixin
from backend.app.domain.enums import (
    DataClass,
    TaskType,
    TaskStatus,
    TaskPriority,
    DependencyType,
)


class MaintenanceTaskModel(Base, TimestampMixin):
    """Schedulable maintenance task requisition."""
    __tablename__ = "maintenance_tasks"
    __table_args__ = (
        CheckConstraint("estimated_duration_minutes > 0", name="ck_tasks_duration_positive"),
        CheckConstraint("window_start < window_end", name="ck_tasks_window_valid"),
        CheckConstraint("crew_size_required > 0", name="ck_tasks_crew_positive"),
        CheckConstraint("from_km IS NULL OR to_km IS NULL OR from_km <= to_km", name="ck_tasks_chainage_range"),
        CheckConstraint("from_km IS NULL OR from_km >= 0", name="ck_tasks_from_km_non_negative"),
        CheckConstraint("to_km IS NULL OR to_km >= 0", name="ck_tasks_to_km_non_negative"),
        CheckConstraint("track_id IS NOT NULL OR (from_km IS NULL AND to_km IS NULL)", name="ck_tasks_track_required_for_chainage"),
        Index("ix_tasks_scenario_status", "scenario_id", "status"),
        Index("ix_tasks_section_window", "section_id", "window_start", "window_end"),
        Index("ix_tasks_track_window", "track_id", "window_start", "window_end"),
    )

    task_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    work_order_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("work_orders.work_order_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    task_code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    task_type: Mapped[TaskType] = mapped_column(
        SQLEnum(TaskType, name="task_type_enum"),
        index=True,
        nullable=False,
    )
    status: Mapped[TaskStatus] = mapped_column(
        SQLEnum(TaskStatus, name="task_status_enum", create_type=False),
        default=TaskStatus.REQUESTED,
        index=True,
        nullable=False,
    )
    priority: Mapped[TaskPriority] = mapped_column(
        SQLEnum(TaskPriority, name="task_priority_enum", create_type=False),
        default=TaskPriority.MEDIUM,
        index=True,
        nullable=False,
    )
    mandatory: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    section_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("sections.section_id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    track_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        ForeignKey("tracks.track_id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    from_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    to_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    adjacent_track_impact: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    station_id: Mapped[Optional[str]] = mapped_column(
        String(32),
        ForeignKey("stations.station_id", ondelete="SET NULL"),
        nullable=True,
    )
    corridor_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        ForeignKey("corridors.corridor_id", ondelete="SET NULL"),
        nullable=True,
    )
    scenario_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("operational_scenarios.scenario_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    preferred_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    preferred_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    estimated_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    minimum_duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    maximum_duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    requires_traffic_block: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requires_power_block: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requires_ptw: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requires_ohe_isolation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requires_signal_disconnection: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    safety_buffer_before_minutes: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    safety_buffer_after_minutes: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    crew_size_required: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Provenance
    classification: Mapped[DataClass] = mapped_column(
        SQLEnum(DataClass, name="data_class_enum", create_type=False),
        default=DataClass.SYNTHETIC,
        nullable=False,
    )
    source_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("source_documents.source_id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Relationships
    work_order = relationship("WorkOrderModel", back_populates="tasks")
    scenario = relationship("OperationalScenarioModel", back_populates="tasks")
    section = relationship("SectionModel", foreign_keys=[section_id])
    track = relationship("TrackModel", foreign_keys=[track_id], back_populates="tasks")
    station = relationship("StationModel", foreign_keys=[station_id])

    corridor = relationship("CorridorModel", foreign_keys=[corridor_id])
    affected_sections = relationship("TaskSectionModel", back_populates="task", cascade="all, delete-orphan")
    rule_references = relationship("TaskRuleReferenceModel", back_populates="task", cascade="all, delete-orphan")
    resource_requirements = relationship("TaskResourceRequirementModel", back_populates="task", cascade="all, delete-orphan")
    outgoing_dependencies = relationship(
        "TaskDependencyModel",
        foreign_keys="[TaskDependencyModel.predecessor_task_id]",
        back_populates="predecessor",
        cascade="all, delete-orphan",
    )
    incoming_dependencies = relationship(
        "TaskDependencyModel",
        foreign_keys="[TaskDependencyModel.successor_task_id]",
        back_populates="successor",
        cascade="all, delete-orphan",
    )


class TaskSectionModel(Base):
    """Multi-section spatial impact table for maintenance tasks."""
    __tablename__ = "maintenance_task_sections"

    task_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("maintenance_tasks.task_id", ondelete="CASCADE"),
        primary_key=True,
    )
    section_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("sections.section_id", ondelete="RESTRICT"),
        primary_key=True,
    )

    task = relationship("MaintenanceTaskModel", back_populates="affected_sections")
    section = relationship("SectionModel")


class TaskDependencyModel(Base):
    """Precedence ordering between maintenance tasks."""
    __tablename__ = "maintenance_task_dependencies"
    __table_args__ = (
        CheckConstraint("predecessor_task_id != successor_task_id", name="ck_task_deps_distinct"),
        UniqueConstraint("predecessor_task_id", "successor_task_id", name="uq_task_deps_pair"),
    )

    dependency_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    predecessor_task_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("maintenance_tasks.task_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    successor_task_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("maintenance_tasks.task_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    dependency_type: Mapped[DependencyType] = mapped_column(
        SQLEnum(DependencyType, name="dependency_type_enum"),
        default=DependencyType.FINISH_TO_START,
        nullable=False,
    )

    predecessor = relationship("MaintenanceTaskModel", foreign_keys=[predecessor_task_id], back_populates="outgoing_dependencies")
    successor = relationship("MaintenanceTaskModel", foreign_keys=[successor_task_id], back_populates="incoming_dependencies")


class TaskRuleReferenceModel(Base):
    """Links maintenance tasks directly to referenced statutory/operating safety rules."""
    __tablename__ = "task_rule_references"

    task_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("maintenance_tasks.task_id", ondelete="CASCADE"),
        primary_key=True,
    )
    rule_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("railway_rules.rule_id", ondelete="RESTRICT"),
        primary_key=True,
    )

    task = relationship("MaintenanceTaskModel", back_populates="rule_references")
    rule = relationship("RailwayRuleModel")
