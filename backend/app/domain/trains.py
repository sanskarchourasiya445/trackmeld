from typing import Optional, List
from pydantic import BaseModel, Field
from backend.app.domain.enums import DataClass


class Train(BaseModel):
    """Canonical train service operating across the Indian Railways network."""
    train_id: str = Field(..., description="Unique train service identifier (e.g. TRN-12301)")
    train_number: str = Field(..., description="Official 5-digit Indian Railways train number (e.g. 12301)")
    train_name: str = Field(..., description="Official commercial service name")
    train_type: Optional[str] = Field(default="MAIL_EXPRESS", description="Operating category (e.g. RAJDHANI, VANDE_BHARAT)")
    source_station: Optional[str] = Field(default=None, description="Originating station name or code")
    destination_station: Optional[str] = Field(default=None, description="Terminating station name or code")
    corridor_table: Optional[str] = Field(default=None, description="Trains at a Glance table number reference")
    running_days: List[str] = Field(default_factory=lambda: ["DAILY"], description="Weekly frequency schedule")
    classification: DataClass = Field(default=DataClass.REAL, description="Data authenticity classification")
    source_id: str = Field(..., description="Referenced official source document")
    source_reference: Optional[str] = Field(default=None, description="Index or table schedule citation")
