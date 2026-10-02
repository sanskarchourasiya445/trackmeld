from typing import Optional, List
from sqlalchemy import String, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, TimestampMixin
from backend.app.domain.enums import DataClass


class TrainModel(Base, TimestampMixin):
    """Canonical train services operating on the Indian Railways network."""
    __tablename__ = "trains"

    train_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    train_number: Mapped[str] = mapped_column(String(16), unique=True, index=True, nullable=False)
    train_name: Mapped[str] = mapped_column(String(256), nullable=False)
    train_type: Mapped[Optional[str]] = mapped_column(String(64), default="MAIL_EXPRESS", index=True, nullable=True)
    source_station: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    destination_station: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    corridor_table: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    running_days: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)

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
    source_doc = relationship("SourceDocumentModel", back_populates="trains")
    movements = relationship("TrainMovementModel", back_populates="train", cascade="all, delete-orphan")
