from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, TimestampMixin
from backend.app.domain.enums import DataClass


class OperationalScenarioModel(Base, TimestampMixin):
    """Scoped operational planning scenarios."""
    __tablename__ = "operational_scenarios"

    scenario_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    scenario_code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    planning_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    planning_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    generation_seed: Mapped[int] = mapped_column(Integer, nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(32), nullable=False)
    classification: Mapped[DataClass] = mapped_column(
        SQLEnum(DataClass, name="data_class_enum", create_type=False),
        default=DataClass.SYNTHETIC,
        nullable=False,
    )

    # Relationships
    work_orders = relationship("WorkOrderModel", back_populates="scenario", cascade="all, delete-orphan")
    tasks = relationship("MaintenanceTaskModel", back_populates="scenario", cascade="all, delete-orphan")
    availabilities = relationship("ResourceAvailabilityModel", back_populates="scenario", cascade="all, delete-orphan")
