from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Text, BigInteger, DateTime, Enum as SQLEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, TimestampMixin
from backend.app.domain.enums import SourceClass


class SourceDocumentModel(Base, TimestampMixin):
    """Authoritative source publications providing provenance for reference data."""
    __tablename__ = "source_documents"

    source_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    publisher: Mapped[str] = mapped_column(String(256), nullable=False)
    organization: Mapped[str] = mapped_column(String(256), nullable=False)
    source_class: Mapped[SourceClass] = mapped_column(
        SQLEnum(SourceClass, name="source_class_enum"),
        nullable=False,
    )
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    local_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    document_date: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    downloaded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    data_types: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    authority_level: Mapped[str] = mapped_column(String(128), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    stations = relationship("StationModel", back_populates="source_doc", cascade="all, delete-orphan")
    trains = relationship("TrainModel", back_populates="source_doc", cascade="all, delete-orphan")
    rules = relationship("RailwayRuleModel", back_populates="source_doc", cascade="all, delete-orphan")
