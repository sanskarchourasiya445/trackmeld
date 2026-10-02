from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from backend.app.domain.enums import DataClass


class InfrastructureSpec(BaseModel):
    """Global technical infrastructure baseline standards (Traction, Gauge, Signalling)."""
    category: str = Field(..., description="Infrastructure domain (e.g. ELECTRIFICATION, TRACK_GAUGE, SIGNALLING)")
    spec_key: str = Field(..., description="Specific parameter key name")
    spec_value: str = Field(..., description="Standard engineering value description")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Detailed attributes")
    classification: DataClass = Field(default=DataClass.REAL, description="Data authenticity classification")
    source_id: str = Field(..., description="Referenced official manual/source")


class Corridor(BaseModel):
    """Trunk railway corridor grouping contiguous sections and monitored divisions."""
    corridor_id: str = Field(..., description="Unique corridor identifier (e.g. CORR-NDLS-HWH)")
    name: str = Field(..., description="Corridor descriptive name")
    length_km: float = Field(..., gt=0.0, description="Total route length in kilometers")
    zones: List[str] = Field(default_factory=list, description="Traversed railway zones")
    divisions: List[str] = Field(default_factory=list, description="Traversed railway divisions")
    primary_table: str = Field(..., description="Trains at a Glance corridor table reference")
    classification: DataClass = Field(default=DataClass.REAL, description="Data authenticity classification")
    source_id: str = Field(default="SRC-TAG-2023-TBL-01", description="Source document identifier")
