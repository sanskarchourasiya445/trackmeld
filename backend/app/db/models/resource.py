from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    String,
    Text,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
    JSON,
    Index,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, TimestampMixin
from backend.app.domain.enums import (
    DataClass,
    WorkDepartment,
    ResourceType,
    AvailabilityStatus,
)


class MaintenanceResourceModel(Base, TimestampMixin):
    """Crews, machines, tower wagons, and specialised equipment."""
    __tablename__ = "maintenance_resources"
    __table_args__ = (
        CheckConstraint("capacity > 0", name="ck_resources_capacity_positive"),
    )

    resource_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    resource_code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    resource_type: Mapped[ResourceType] = mapped_column(
        SQLEnum(ResourceType, name="resource_type_enum"),
        index=True,
        nullable=False,
    )
    department: Mapped[WorkDepartment] = mapped_column(
        SQLEnum(WorkDepartment, name="work_department_enum", create_type=False),
        index=True,
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    capacity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    home_station: Mapped[Optional[str]] = mapped_column(
        String(32),
        ForeignKey("stations.station_id", ondelete="SET NULL"),
        nullable=True,
    )
    qualification_tags: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)

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
    station = relationship("StationModel")
    availabilities = relationship("ResourceAvailabilityModel", back_populates="resource", cascade="all, delete-orphan")


class ResourceAvailabilityModel(Base):
    """Temporal availability intervals for resources."""
    __tablename__ = "resource_availability"
    __table_args__ = (
        CheckConstraint("available_from < available_until", name="ck_avail_window_valid"),
        CheckConstraint("quantity > 0", name="ck_avail_quantity_positive"),
        Index("ix_avail_resource_window", "resource_id", "available_from", "available_until"),
    )

    availability_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    resource_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("maintenance_resources.resource_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    scenario_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("operational_scenarios.scenario_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    available_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    available_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    availability_status: Mapped[AvailabilityStatus] = mapped_column(
        SQLEnum(AvailabilityStatus, name="availability_status_enum"),
        default=AvailabilityStatus.AVAILABLE,
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    resource = relationship("MaintenanceResourceModel", back_populates="availabilities")
    scenario = relationship("OperationalScenarioModel", back_populates="availabilities")


class TaskResourceRequirementModel(Base):
    """Resource requirement attached to a maintenance task."""
    __tablename__ = "task_resource_requirements"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_req_quantity_positive"),
    )

    requirement_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("maintenance_tasks.task_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    resource_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        ForeignKey("maintenance_resources.resource_id", ondelete="SET NULL"),
        nullable=True,
    )
    resource_type: Mapped[ResourceType] = mapped_column(
        SQLEnum(ResourceType, name="resource_type_enum", create_type=False),
        index=True,
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    mandatory: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    task = relationship("MaintenanceTaskModel", back_populates="resource_requirements")
    resource = relationship("MaintenanceResourceModel")
