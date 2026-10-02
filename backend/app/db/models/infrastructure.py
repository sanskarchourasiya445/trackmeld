from typing import Dict, Any, List
from sqlalchemy import String, Text, Float, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.db.base import Base, TimestampMixin
from backend.app.domain.enums import DataClass


class InfrastructureSpecModel(Base, TimestampMixin):
    """Global technical specifications for railway infrastructure standards."""
    __tablename__ = "infrastructure_specs"

    spec_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    spec_key: Mapped[str] = mapped_column(String(64), nullable=False)
    spec_value: Mapped[str] = mapped_column(Text, nullable=False)
    attributes: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Provenance
    classification: Mapped[DataClass] = mapped_column(
        SQLEnum(DataClass, name="data_class_enum"),
        default=DataClass.REAL,
        nullable=False,
    )
    source_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("source_documents.source_id", ondelete="RESTRICT"),
        nullable=False,
    )


class CorridorModel(Base, TimestampMixin):
    """Trunk railway corridors grouping contiguous sections and operating divisions."""
    __tablename__ = "corridors"

    corridor_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    length_km: Mapped[float] = mapped_column(Float, nullable=False)
    zones: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    divisions: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    primary_table: Mapped[str] = mapped_column(String(64), nullable=False)

    # Provenance
    classification: Mapped[DataClass] = mapped_column(
        SQLEnum(DataClass, name="data_class_enum"),
        default=DataClass.REAL,
        nullable=False,
    )
    source_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("source_documents.source_id", ondelete="RESTRICT"),
        nullable=False,
    )
