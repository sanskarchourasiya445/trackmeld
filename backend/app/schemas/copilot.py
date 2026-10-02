"""
Pydantic schemas and contracts for Phase 13 Read-Only Copilot & Decision Support.
Enforces typed read-only tools, evidence grounding, and refusal semantics.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EvidenceType(str, Enum):
    TASK_DECISION = "TASK_DECISION"
    CONFLICT = "CONFLICT"
    RUN_METRIC = "RUN_METRIC"
    RULE_PROVENANCE = "RULE_PROVENANCE"
    PLAN_VERSION = "PLAN_VERSION"
    AUDIT_EVENT = "AUDIT_EVENT"
    UNCERTAINTY = "UNCERTAINTY"
    REFUSAL = "REFUSAL"


class EvidenceItem(BaseModel):
    """Structured evidence fact retrieved deterministically from database or solver snapshot."""
    evidence_id: str = Field(..., description="Unique evidence identifier, e.g. TASK:TSK-0007")
    evidence_type: EvidenceType = Field(..., description="Category of retrieved fact")
    title: str = Field(..., description="Human-readable title of evidence")
    data: Dict[str, Any] = Field(default_factory=dict, description="Deterministic key-value facts")
    source_reference: Optional[str] = Field(None, description="Database table, snapshot hash, or rule source")


class CopilotToolParameter(BaseModel):
    name: str
    type: str
    description: str
    required: bool = True


class CopilotToolSpec(BaseModel):
    """Specification of a typed read-only tool available to the Copilot."""
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="What factual records this tool retrieves")
    parameters: List[CopilotToolParameter] = Field(default_factory=list)


class CopilotQueryRequest(BaseModel):
    """User inquiry sent to the read-only Copilot."""
    prompt: str = Field(..., min_length=2, max_length=1500, description="Natural language question or request")
    scenario_id: Optional[str] = Field("SCN-DEMO-001", description="Target scenario context")
    run_id: Optional[str] = Field(None, description="Optional planning run context")
    task_id: Optional[str] = Field(None, description="Optional task context")
    plan_version_id: Optional[str] = Field(None, description="Optional plan version context")


class CopilotQueryResponse(BaseModel):
    """Evidence-grounded response from the read-only Copilot."""
    query: str = Field(..., description="Original user prompt")
    answer: str = Field(..., description="Grounded explanation citing evidence tags")
    evidence: List[EvidenceItem] = Field(default_factory=list, description="Verified facts backing the explanation")
    tool_calls_executed: List[str] = Field(default_factory=list, description="Names of typed tools invoked")
    provider_used: str = Field("DETERMINISTIC_EVIDENCE_ENGINE", description="Underlying provider or engine")
    read_only_notice: str = Field(
        "TrackMeld Copilot is an evidence-grounded read-only assistant. It cannot alter schedules, mutate records, or grant operational approval.",
        description="Mandatory governance disclaimer",
    )
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
