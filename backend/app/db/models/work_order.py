from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Enum as SQLEnum, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, TimestampMixin
from backend.app.domain.enums import (
    DataClass,
    WorkDepartment,
    WorkOrderStatus,
    TaskPriority,
)


class WorkOrderModel(Base, TimestampMixin):
    """Parent maintenance requisition grouping tasks."""
    __tablename__ = "work_orders"
    __table_args__ = (
        CheckConstraint("requested_execution_start < requested_execution_end", name="ck_work_orders_window_valid"),
    )

    work_order_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    work_order_number: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    department: Mapped[WorkDepartment] = mapped_column(
        SQLEnum(WorkDepartment, name="work_department_enum", create_type=False),
        nullable=False,
    )
    requesting_unit: Mapped[str] = mapped_column(String(128), nullable=False)
    requested_by: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[WorkOrderStatus] = mapped_column(
        SQLEnum(WorkOrderStatus, name="work_order_status_enum"),
        default=WorkOrderStatus.SUBMITTED,
        index=True,
        nullable=False,
    )
    priority: Mapped[TaskPriority] = mapped_column(
        SQLEnum(TaskPriority, name="task_priority_enum"),
        default=TaskPriority.MEDIUM,
        index=True,
        nullable=False,
    )
    mandatory: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    scenario_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("operational_scenarios.scenario_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    requested_execution_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    requested_execution_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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
    scenario = relationship("OperationalScenarioModel", back_populates="work_orders")
    tasks = relationship("MaintenanceTaskModel", back_populates="work_order", cascade="all, delete-orphan")
