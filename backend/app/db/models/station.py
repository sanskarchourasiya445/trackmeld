from typing import Optional
from sqlalchemy import String, Float, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, TimestampMixin
from backend.app.domain.enums import DataClass


class StationModel(Base, TimestampMixin):
    """Railway station network nodes."""
    __tablename__ = "stations"

    station_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    station_code: Mapped[str] = mapped_column(String(16), unique=True, index=True, nullable=False)
    station_name: Mapped[str] = mapped_column(String(128), nullable=False)
    zone: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    division: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    route: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    route_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    station_type: Mapped[str] = mapped_column(String(32), default="JUNCTION", nullable=False)
    
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
    source_reference: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    # Relationships
    source_doc = relationship("SourceDocumentModel", back_populates="stations")
    outgoing_sections = relationship(
        "SectionModel",
        foreign_keys="[SectionModel.from_station_id]",
        back_populates="from_station",
    )
    incoming_sections = relationship(
        "SectionModel",
        foreign_keys="[SectionModel.to_station_id]",
        back_populates="to_station",
    )
    movements = relationship("TrainMovementModel", back_populates="station")
