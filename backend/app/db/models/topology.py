from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import (
    String,
    Float,
    Integer,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base


class TopologyTimestampMixin:
    """Provides standardized UTC created_at and updated_at timestamps with explicit timezone=True."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class TopologyNodeModel(Base, TopologyTimestampMixin):
    """Physical or operational junction point where track endpoints interface."""
    __tablename__ = "topology_nodes"
    __table_args__ = (
        CheckConstraint(
            "node_type IN ('BOUNDARY_JOINT', 'STATION_THROAT', 'CROSSOVER_JUNCTION')",
            name="ck_topology_nodes_type_valid",
        ),
        Index("ix_topology_nodes_station_id", "station_id"),
    )

    node_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    node_name: Mapped[str] = mapped_column(String(128), nullable=False)
    station_id: Mapped[Optional[str]] = mapped_column(
        String(32),
        ForeignKey("stations.station_id", ondelete="SET NULL"),
        nullable=True,
    )
    node_type: Mapped[str] = mapped_column(String(32), nullable=False)
    classification: Mapped[str] = mapped_column(String(32), default="DEMO_ONLY", nullable=False)
    source_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("source_documents.source_id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Relationships
    station = relationship("StationModel")
    connections = relationship("TopologyConnectionModel", back_populates="node", cascade="all, delete-orphan")


class TrackEndpointModel(Base, TopologyTimestampMixin):
    """Boundary port / termination of a specific running track."""
    __tablename__ = "track_endpoints"
    __table_args__ = (
        UniqueConstraint("track_id", "endpoint_type", name="uq_track_endpoints_track_type"),
        CheckConstraint("endpoint_type IN ('START', 'END')", name="ck_track_endpoints_type_valid"),
        Index("ix_track_endpoints_track_id", "track_id"),
    )

    endpoint_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    track_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("tracks.track_id", ondelete="CASCADE"),
        nullable=False,
    )
    endpoint_type: Mapped[str] = mapped_column(String(16), nullable=False)
    kilometrage: Mapped[float] = mapped_column(Float, nullable=False)

    # Relationships
    track = relationship("TrackModel", back_populates="endpoints")


class TopologyConnectionModel(Base, TopologyTimestampMixin):
    """Permitted physical rail path linking an outbound endpoint to an inbound endpoint across a node."""
    __tablename__ = "topology_connections"
    __table_args__ = (
        UniqueConstraint("from_endpoint_id", "to_endpoint_id", name="uq_topology_connections_endpoints"),
        CheckConstraint("from_endpoint_id != to_endpoint_id", name="ck_topology_connections_distinct_endpoints"),
        CheckConstraint(
            "connection_type IN ('CONTINUITY', 'TURNOUT_NORMAL', 'TURNOUT_REVERSE', 'CROSSOVER')",
            name="ck_topology_connections_type_valid",
        ),
        CheckConstraint(
            "traversal_direction IN ('FORWARD', 'REVERSE', 'BIDIRECTIONAL')",
            name="ck_topology_connections_direction_valid",
        ),
        Index("ix_topology_connections_node_id", "node_id"),
        Index("ix_topology_connections_from_ep", "from_endpoint_id"),
        Index("ix_topology_connections_to_ep", "to_endpoint_id"),
    )

    connection_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    node_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("topology_nodes.node_id", ondelete="CASCADE"),
        nullable=False,
    )
    from_endpoint_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("track_endpoints.endpoint_id", ondelete="CASCADE"),
        nullable=False,
    )
    to_endpoint_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("track_endpoints.endpoint_id", ondelete="CASCADE"),
        nullable=False,
    )
    connection_type: Mapped[str] = mapped_column(String(32), nullable=False)
    traversal_direction: Mapped[str] = mapped_column(String(32), default="FORWARD", nullable=False)
    max_diverging_speed_kmh: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    classification: Mapped[str] = mapped_column(String(32), default="DEMO_ONLY", nullable=False)

    # Relationships
    node = relationship("TopologyNodeModel", back_populates="connections")
    from_endpoint = relationship("TrackEndpointModel", foreign_keys=[from_endpoint_id])
    to_endpoint = relationship("TrackEndpointModel", foreign_keys=[to_endpoint_id])
