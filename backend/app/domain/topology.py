"""Domain models for meso-level railway infrastructure topology.

Part of Phase 16I-C: Infrastructure Topology Persistence & Explicit Demo Data.

Core Principle:
Rules classify -> Optimization schedules -> Independent Validator verifies.
Topology entities represent physical track endpoints and connections between them.
They do NOT represent:
- route selection or train dispatching
- conflict or safety guarantees
- scheduling feasibility or approval
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator

from backend.app.domain.enums import (
    EndpointType,
    TopologyNodeType,
    TopologyConnectionType,
    TopologyTraversalDirection,
)


class TopologyNode(BaseModel):
    """Physical or operational junction point where track endpoints meet, continue, or diverge."""
    node_id: str = Field(..., description="Unique topology node identifier (e.g. NODE-STN-GZB-WEST)")
    node_name: str = Field(..., description="Descriptive human-readable name of junction")
    station_id: Optional[str] = Field(default=None, description="Associated station identifier if located at station")
    node_type: TopologyNodeType = Field(..., description="Junction category: BOUNDARY_JOINT, STATION_THROAT, CROSSOVER_JUNCTION")
    classification: str = Field(default="DEMO_ONLY", description="Provenance classification (DEMO_ONLY, SYNTHETIC, REAL)")
    source_id: str = Field(..., description="Referenced engineering scale plan or source document")

    model_config = {"frozen": True}


class TrackEndpoint(BaseModel):
    """Boundary port / termination of a specific running track."""
    endpoint_id: str = Field(..., description="Unique endpoint identifier (e.g. EP-TRK-SEC-NDLS-GZB-UP-START)")
    track_id: str = Field(..., description="Parent running track identifier")
    endpoint_type: EndpointType = Field(..., description="Boundary orientation: START or END")
    kilometrage: float = Field(..., ge=0.0, description="Chainage kilometrage at this endpoint")

    model_config = {"frozen": True}


class TopologyConnection(BaseModel):
    """Permitted physical rail path linking an outbound endpoint to an inbound endpoint across a node."""
    connection_id: str = Field(..., description="Unique connection identifier (e.g. CONN-GZB-UP-THROUGH)")
    node_id: str = Field(..., description="Topology node where connection is physically located")
    from_endpoint_id: str = Field(..., description="Outbound / entry track endpoint identifier")
    to_endpoint_id: str = Field(..., description="Inbound / exit track endpoint identifier")
    connection_type: TopologyConnectionType = Field(..., description="Connection geometry: CONTINUITY, TURNOUT_NORMAL, TURNOUT_REVERSE, CROSSOVER")
    traversal_direction: TopologyTraversalDirection = Field(default=TopologyTraversalDirection.FORWARD, description="Permitted movement direction: FORWARD, REVERSE, BIDIRECTIONAL")
    max_diverging_speed_kmh: Optional[int] = Field(default=None, ge=0, description="Speed limit across turnout/crossover if applicable")
    classification: str = Field(default="DEMO_ONLY", description="Provenance classification (DEMO_ONLY, SYNTHETIC, REAL)")

    model_config = {"frozen": True}

    @model_validator(mode="after")
    def validate_distinct_endpoints(self) -> "TopologyConnection":
        if self.from_endpoint_id == self.to_endpoint_id:
            raise ValueError(f"TopologyConnection cannot link an endpoint to itself: {self.from_endpoint_id}")
        return self
