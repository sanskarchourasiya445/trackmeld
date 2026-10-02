from typing import Optional
from pydantic import BaseModel, Field
from backend.app.domain.enums import DataClass, StationType


class Station(BaseModel):
    """Railway station network node with geographical and operational attributes."""
    station_id: str = Field(..., description="Unique station identifier (e.g. STN-NDLS)")
    station_code: str = Field(..., description="Official Indian Railways alphabetical code (e.g. NDLS)")
    station_name: str = Field(..., description="Full English station name")
    zone: str = Field(..., description="Zonal Railway code (e.g. NR, NCR, ER, CR)")
    division: str = Field(..., description="Operational railway division (e.g. Delhi, Prayagraj)")
    route: Optional[str] = Field(default=None, description="Trunk route name")
    route_km: Optional[float] = Field(default=None, ge=0.0, description="Route kilometrage from corridor datum")
    station_type: str = Field(default="JUNCTION", description="Operational category")
    classification: DataClass = Field(default=DataClass.REAL, description="Data authenticity classification")
    source_id: str = Field(..., description="Referenced source publication identifier")
    source_reference: Optional[str] = Field(default=None, description="Specific table/index reference")
