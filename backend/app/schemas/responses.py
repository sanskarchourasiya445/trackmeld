from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from backend.app.domain.enums import DataClass, RuleClass, SourceClass, TraversalResolutionStatus



class CorridorResponse(BaseModel):
    corridor_id: str
    name: str
    length_km: float
    zones: List[str]
    divisions: List[str]
    primary_table: str
    classification: DataClass
    source_id: str

    model_config = {"from_attributes": True}


class StationResponse(BaseModel):
    station_id: str
    station_code: str
    station_name: str
    zone: str
    division: str
    route: Optional[str] = None
    route_km: Optional[float] = None
    station_type: str
    classification: DataClass
    source_id: str
    source_reference: Optional[str] = None

    model_config = {"from_attributes": True}


class TrackResponse(BaseModel):
    track_id: str
    section_id: str
    track_code: str
    direction: str
    electrified: bool
    max_speed_kmh: Optional[int] = None
    adjacent_track_ids: Optional[List[str]] = None

    model_config = {"from_attributes": True}


class SectionResponse(BaseModel):
    section_id: str
    section_code: str
    from_station_id: str
    to_station_id: str
    from_station_name: str
    to_station_name: str
    from_station_code: str
    to_station_code: str
    routes: List[str]
    division: str
    zone: str
    kilometrage_start: float
    kilometrage_end: float
    length_km: float
    track_count: int
    electrified: bool
    gauge: str
    signalling_type: str
    classification: DataClass
    derivation_method: Optional[str] = None
    input_source_ids: List[str]
    confidence: float
    tracks: List[TrackResponse] = []

    model_config = {"from_attributes": True}



class TrainResponse(BaseModel):
    train_id: str
    train_number: str
    train_name: str
    train_type: Optional[str] = None
    source_station: Optional[str] = None
    destination_station: Optional[str] = None
    corridor_table: Optional[str] = None
    running_days: List[str]
    classification: DataClass
    source_id: str
    source_reference: Optional[str] = None

    model_config = {"from_attributes": True}


class TrainMovementResponse(BaseModel):
    movement_id: str
    train_id: str
    train_number: str
    train_name: str
    station_id: str
    station_code: str
    station_name: str
    stop_sequence: int
    scheduled_arrival: Optional[str] = None
    scheduled_departure: Optional[str] = None
    day_offset: int
    distance_km: float
    movement_type: str
    basis: str
    track_id: Optional[str] = None
    classification: DataClass
    source_id: str
    source_reference: Optional[str] = None

    model_config = {"from_attributes": True}


class RuleResponse(BaseModel):
    rule_id: str
    category: str
    title: str
    source_document: str
    source_id: str
    section_page: Optional[str] = None
    original_text: str
    normalized_summary: str
    applicability: str
    safety_critical: bool
    rule_class: RuleClass
    confidence: float

    model_config = {"from_attributes": True}


class TrainTraversalResponse(BaseModel):
    traversal_id: str
    train_id: str
    train_number: str
    source_pass_id: str
    section_id: Optional[str] = None
    from_station_id: str
    to_station_id: str
    sequence_order: int
    entry_time: datetime
    exit_time: datetime
    duration_minutes: float
    traversal_track_id: Optional[str] = None
    resolution_status: TraversalResolutionStatus
    unresolved_reason: Optional[str] = None
    classification: DataClass

    model_config = {"from_attributes": True}
