from typing import Optional
from sqlalchemy import (
    String,
    Integer,
    Float,
    ForeignKey,
    Enum as SQLEnum,
    Index,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, TimestampMixin
from backend.app.domain.enums import DataClass


class TrainMovementModel(Base, TimestampMixin):
    """Scheduled train transit/stop event along a timetable route."""
    __tablename__ = "train_movements"
    __table_args__ = (
        CheckConstraint("stop_sequence >= 1", name="ck_movements_stop_sequence_positive"),
        Index("ix_movements_station_dep", "station_id", "scheduled_departure"),
        Index("ix_movements_train_seq", "train_id", "stop_sequence"),
        Index("ix_movements_train_station", "train_id", "station_id"),
    )

    movement_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    train_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("trains.train_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    train_number: Mapped[str] = mapped_column(String(16), nullable=False)
    train_name: Mapped[str] = mapped_column(String(256), nullable=False)
    station_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("stations.station_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    station_code: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    station_name: Mapped[str] = mapped_column(String(128), nullable=False)
    stop_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    scheduled_arrival: Mapped[Optional[str]] = mapped_column(String(8), nullable=True, index=True)
    scheduled_departure: Mapped[Optional[str]] = mapped_column(String(8), nullable=True, index=True)
    day_offset: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    distance_km: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    movement_type: Mapped[str] = mapped_column(String(32), nullable=False)
    basis: Mapped[str] = mapped_column(String(32), default="SCHEDULED_TIMETABLE", nullable=False)
    track_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        ForeignKey("tracks.track_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

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
    train = relationship("TrainModel", back_populates="movements")
    station = relationship("StationModel", back_populates="movements")
    track = relationship("TrackModel", back_populates="movements")
