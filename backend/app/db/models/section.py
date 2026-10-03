from typing import Optional, List
from sqlalchemy import (
    String,
    Float,
    Integer,
    Boolean,
    Text,
    ForeignKey,
    Enum as SQLEnum,
    JSON,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, TimestampMixin
from backend.app.domain.enums import DataClass


class SectionModel(Base, TimestampMixin):
    """Contiguous block section between two stations for train clearance and possession."""
    __tablename__ = "sections"
    __table_args__ = (
        CheckConstraint("length_km > 0", name="ck_sections_length_positive"),
        CheckConstraint("from_station_id != to_station_id", name="ck_sections_distinct_endpoints"),
    )

    section_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    section_code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    from_station_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("stations.station_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    to_station_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("stations.station_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    from_station_name: Mapped[str] = mapped_column(String(128), nullable=False)
    to_station_name: Mapped[str] = mapped_column(String(128), nullable=False)
    from_station_code: Mapped[str] = mapped_column(String(16), nullable=False)
    to_station_code: Mapped[str] = mapped_column(String(16), nullable=False)
    routes: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    division: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    zone: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    kilometrage_start: Mapped[float] = mapped_column(Float, nullable=False)
    kilometrage_end: Mapped[float] = mapped_column(Float, nullable=False)
    length_km: Mapped[float] = mapped_column(Float, nullable=False)
    track_count: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    electrified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    gauge: Mapped[str] = mapped_column(String(32), default="BROAD_GAUGE_1676MM", nullable=False)
    signalling_type: Mapped[str] = mapped_column(
        String(128),
        default="AUTOMATIC_BLOCK_OR_ABSOLUTE_BLOCK_MACLS",
        nullable=False,
    )

    # Provenance
    classification: Mapped[DataClass] = mapped_column(
        SQLEnum(DataClass, name="data_class_enum"),
        default=DataClass.DERIVED,
        nullable=False,
    )
    derivation_method: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    input_source_ids: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    # Relationships
    from_station = relationship(
        "StationModel",
        foreign_keys=[from_station_id],
        back_populates="outgoing_sections",
    )
    to_station = relationship(
        "StationModel",
        foreign_keys=[to_station_id],
        back_populates="incoming_sections",
    )
    tracks = relationship("TrackModel", back_populates="section", cascade="all, delete-orphan", lazy="selectin")

