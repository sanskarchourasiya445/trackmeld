from typing import Optional, List
from pydantic import BaseModel, Field, model_validator
from backend.app.domain.enums import DataClass


class Section(BaseModel):
    """Contiguous block section between two stations for train clearance and maintenance possession."""
    section_id: str = Field(..., description="Unique section identifier (e.g. SEC-NDLS-GZB)")
    section_code: str = Field(..., description="Hyphenated endpoint station codes (e.g. NDLS-GZB)")
    from_station_id: str = Field(..., description="Starting station ID")
    to_station_id: str = Field(..., description="Terminating station ID")
    from_station_name: str = Field(..., description="Starting station English name")
    to_station_name: str = Field(..., description="Terminating station English name")
    from_station_code: str = Field(..., description="Starting station code")
    to_station_code: str = Field(..., description="Terminating station code")
    routes: List[str] = Field(default_factory=list, description="Associated corridor route names")
    division: str = Field(..., description="Operational railway division")
    zone: str = Field(..., description="Zonal Railway code")
    kilometrage_start: float = Field(..., ge=0.0, description="Start chainage KM post")
    kilometrage_end: float = Field(..., ge=0.0, description="End chainage KM post")
    length_km: float = Field(..., gt=0.0, description="Physical length in kilometers")
    track_count: int = Field(default=2, ge=1, description="Number of running lines (e.g. 2 for UP/DN)")
    electrified: bool = Field(default=True, description="25 kV AC OHE electrification status")
    gauge: str = Field(default="BROAD_GAUGE_1676MM", description="Track gauge specification")
    signalling_type: str = Field(
        default="AUTOMATIC_BLOCK_OR_ABSOLUTE_BLOCK_MACLS",
        description="Block signalling and interlocking architecture"
    )
    classification: DataClass = Field(
        default=DataClass.DERIVED,
        description="Data classification: DERIVED from official station chainages"
    )
    derivation_method: Optional[str] = Field(
        default="Topological connection established from contiguous corridor kilometrage in TAG official tables",
        description="Explanation of derivation process"
    )
    input_source_ids: List[str] = Field(
        default_factory=list,
        description="Source documents utilized in topological derivation"
    )
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_endpoints_and_length(self) -> "Section":
        if self.from_station_id == self.to_station_id:
            raise ValueError(f"Section endpoint stations cannot be identical: {self.from_station_id}")
        if self.length_km <= 0.0:
            raise ValueError(f"Section length must be strictly positive: {self.length_km}")
        return self
