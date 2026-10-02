from typing import Optional
from pydantic import BaseModel, Field
from backend.app.domain.enums import RuleClass


class RailwayRule(BaseModel):
    """Statutory, operating, electrical, or signalling safety rule governing possessions."""
    rule_id: str = Field(..., description="Unique rule identifier (e.g. RULE-STAT-RBP-1502C)")
    category: str = Field(..., description="Functional rule category (e.g. MAINTENANCE_PLANNING, TRAFFIC_BLOCK)")
    title: str = Field(..., description="Rule headline or clause title")
    source_document: str = Field(..., description="Title of authoritative parent document")
    source_id: str = Field(..., description="Referenced source publication identifier")
    section_page: Optional[str] = Field(default=None, description="Clause, chapter, or page reference")
    original_text: str = Field(..., description="Verbatim statutory or manual rule clause text")
    normalized_summary: str = Field(..., description="Operational summary for planning system")
    applicability: str = Field(..., description="Scope of application (e.g. ALL_ZONES_DIVISIONS, RUNNING_LINES)")
    safety_critical: bool = Field(default=True, description="Whether violation constitutes a critical safety breach")
    rule_class: RuleClass = Field(default=RuleClass.VERIFIED_SOURCE, description="Authority status")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
