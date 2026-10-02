from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, model_validator
from backend.app.domain.enums import DataClass


class ProvenanceMetadata(BaseModel):
    """Canonical provenance payload attached to all domain records."""
    data_class: DataClass = Field(
        ...,
        description="Data authenticity class: REAL, DERIVED, SYNTHETIC, or ASSUMED"
    )
    source_id: str = Field(
        ...,
        description="Identifier referencing the authoritative source document"
    )
    source_reference: Optional[str] = Field(
        default=None,
        description="Document section, chapter, table, or page reference"
    )
    derivation_method: Optional[str] = Field(
        default=None,
        description="Methodology description if record was computed or topologically derived"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score [0.0 - 1.0]"
    )
    extracted_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of extraction or creation"
    )

    @model_validator(mode="after")
    def validate_provenance_invariants(self) -> "ProvenanceMetadata":
        # Invariant: DERIVED records must specify a derivation_method or reference
        if self.data_class == DataClass.DERIVED and not self.derivation_method and not self.source_reference:
            raise ValueError("DERIVED records must provide either derivation_method or source_reference.")
        return self


def assert_classification_immutable(original_class: DataClass, target_class: DataClass) -> None:
    """Enforce security invariant: Non-REAL records cannot be silently promoted to REAL."""
    if original_class != DataClass.REAL and target_class == DataClass.REAL:
        raise ValueError(
            f"Security/Integrity Violation: Cannot promote classification '{original_class.value}' to 'REAL'."
        )
    if original_class == DataClass.SYNTHETIC and target_class in (DataClass.REAL, DataClass.DERIVED):
        raise ValueError(
            f"Security/Integrity Violation: Cannot promote synthetic record to '{target_class.value}'."
        )
