from typing import Optional
from sqlalchemy import String, Text, Boolean, Float, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, TimestampMixin
from backend.app.domain.enums import RuleClass


class RailwayRuleModel(Base, TimestampMixin):
    """Statutory, operating, electrical, and signalling rules governing possessions."""
    __tablename__ = "railway_rules"

    rule_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    source_document: Mapped[str] = mapped_column(String(256), nullable=False)
    source_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("source_documents.source_id", ondelete="RESTRICT"),
        nullable=False,
    )
    section_page: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_summary: Mapped[str] = mapped_column(Text, nullable=False)
    applicability: Mapped[str] = mapped_column(String(128), nullable=False)
    safety_critical: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    rule_class: Mapped[RuleClass] = mapped_column(
        SQLEnum(RuleClass, name="rule_class_enum"),
        default=RuleClass.VERIFIED_SOURCE,
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    # Relationships
    source_doc = relationship("SourceDocumentModel", back_populates="rules")
