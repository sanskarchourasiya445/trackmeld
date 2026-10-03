from typing import Optional, List
from sqlalchemy import (
    String,
    Integer,
    Boolean,
    ForeignKey,
    UniqueConstraint,
    Index,
    CheckConstraint,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, TimestampMixin


class TrackModel(Base, TimestampMixin):
    """Running track / line within a block section."""
    __tablename__ = "tracks"
    __table_args__ = (
        UniqueConstraint("section_id", "track_code", name="uq_tracks_section_track_code"),
        CheckConstraint("direction IN ('UP', 'DOWN', 'BIDIRECTIONAL')", name="ck_tracks_direction_valid"),
        Index("ix_tracks_section_id", "section_id"),
    )

    track_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    section_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("sections.section_id", ondelete="CASCADE"),
        nullable=False,
    )
    track_code: Mapped[str] = mapped_column(String(32), nullable=False)
    direction: Mapped[str] = mapped_column(String(32), default="BIDIRECTIONAL", nullable=False)
    electrified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    max_speed_kmh: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    adjacent_track_ids: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True, default=None)

    # Relationships
    section = relationship("SectionModel", back_populates="tracks")
    tasks = relationship("MaintenanceTaskModel", back_populates="track")
    movements = relationship("TrainMovementModel", back_populates="track")
