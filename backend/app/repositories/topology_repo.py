from typing import Optional, Sequence, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from backend.app.db.models.topology import (
    TopologyNodeModel,
    TrackEndpointModel,
    TopologyConnectionModel,
)
from backend.app.db.models.track import TrackModel
from backend.app.repositories.base import BaseRepository


class TopologyRepository:
    """Read-oriented repository for infrastructure topology entities."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # -------------------------------------------------------------------------
    # Topology Nodes
    # -------------------------------------------------------------------------
    async def get_node_by_id(self, node_id: str) -> Optional[TopologyNodeModel]:
        stmt = select(TopologyNodeModel).where(TopologyNodeModel.node_id == node_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def filter_nodes(
        self,
        station_id: Optional[str] = None,
        node_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[TopologyNodeModel]:
        stmt = select(TopologyNodeModel)
        if station_id:
            stmt = stmt.where(TopologyNodeModel.station_id == station_id)
        if node_type:
            stmt = stmt.where(TopologyNodeModel.node_type == node_type.upper())
        stmt = stmt.order_by(TopologyNodeModel.node_id).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_nodes(
        self,
        station_id: Optional[str] = None,
        node_type: Optional[str] = None,
    ) -> int:
        stmt = select(func.count()).select_from(TopologyNodeModel)
        if station_id:
            stmt = stmt.where(TopologyNodeModel.station_id == station_id)
        if node_type:
            stmt = stmt.where(TopologyNodeModel.node_type == node_type.upper())
        result = await self.session.execute(stmt)
        return result.scalar_one()

    # -------------------------------------------------------------------------
    # Track Endpoints
    # -------------------------------------------------------------------------
    async def get_endpoint_by_id(self, endpoint_id: str) -> Optional[TrackEndpointModel]:
        stmt = select(TrackEndpointModel).where(TrackEndpointModel.endpoint_id == endpoint_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_endpoints_by_track(self, track_id: str) -> Sequence[TrackEndpointModel]:
        stmt = select(TrackEndpointModel).where(TrackEndpointModel.track_id == track_id).order_by(TrackEndpointModel.endpoint_type.asc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def filter_endpoints(
        self,
        track_id: Optional[str] = None,
        endpoint_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[TrackEndpointModel]:
        stmt = select(TrackEndpointModel)
        if track_id:
            stmt = stmt.where(TrackEndpointModel.track_id == track_id)
        if endpoint_type:
            stmt = stmt.where(TrackEndpointModel.endpoint_type == endpoint_type.upper())
        stmt = stmt.order_by(TrackEndpointModel.endpoint_id).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_endpoints(
        self,
        track_id: Optional[str] = None,
        endpoint_type: Optional[str] = None,
    ) -> int:
        stmt = select(func.count()).select_from(TrackEndpointModel)
        if track_id:
            stmt = stmt.where(TrackEndpointModel.track_id == track_id)
        if endpoint_type:
            stmt = stmt.where(TrackEndpointModel.endpoint_type == endpoint_type.upper())
        result = await self.session.execute(stmt)
        return result.scalar_one()

    # -------------------------------------------------------------------------
    # Topology Connections
    # -------------------------------------------------------------------------
    async def get_connection_by_id(self, connection_id: str) -> Optional[TopologyConnectionModel]:
        stmt = select(TopologyConnectionModel).where(TopologyConnectionModel.connection_id == connection_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def filter_connections(
        self,
        node_id: Optional[str] = None,
        from_endpoint_id: Optional[str] = None,
        to_endpoint_id: Optional[str] = None,
        connection_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[TopologyConnectionModel]:
        stmt = select(TopologyConnectionModel)
        if node_id:
            stmt = stmt.where(TopologyConnectionModel.node_id == node_id)
        if from_endpoint_id:
            stmt = stmt.where(TopologyConnectionModel.from_endpoint_id == from_endpoint_id)
        if to_endpoint_id:
            stmt = stmt.where(TopologyConnectionModel.to_endpoint_id == to_endpoint_id)
        if connection_type:
            stmt = stmt.where(TopologyConnectionModel.connection_type == connection_type.upper())
        stmt = stmt.order_by(TopologyConnectionModel.connection_id).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_connections(
        self,
        node_id: Optional[str] = None,
        from_endpoint_id: Optional[str] = None,
        to_endpoint_id: Optional[str] = None,
        connection_type: Optional[str] = None,
    ) -> int:
        stmt = select(func.count()).select_from(TopologyConnectionModel)
        if node_id:
            stmt = stmt.where(TopologyConnectionModel.node_id == node_id)
        if from_endpoint_id:
            stmt = stmt.where(TopologyConnectionModel.from_endpoint_id == from_endpoint_id)
        if to_endpoint_id:
            stmt = stmt.where(TopologyConnectionModel.to_endpoint_id == to_endpoint_id)
        if connection_type:
            stmt = stmt.where(TopologyConnectionModel.connection_type == connection_type.upper())
        result = await self.session.execute(stmt)
        return result.scalar_one()

    # -------------------------------------------------------------------------
    # Track Topology Aggregation
    # -------------------------------------------------------------------------
    async def get_track_topology(self, track_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve track metadata, boundary endpoints, and attached connections."""
        stmt_t = select(TrackModel).where(TrackModel.track_id == track_id)
        res_t = await self.session.execute(stmt_t)
        track = res_t.scalars().first()
        if not track:
            return None

        endpoints = await self.list_endpoints_by_track(track_id)
        ep_ids = [ep.endpoint_id for ep in endpoints]

        outgoing_conns: List[TopologyConnectionModel] = []
        incoming_conns: List[TopologyConnectionModel] = []

        if ep_ids:
            stmt_out = select(TopologyConnectionModel).where(TopologyConnectionModel.from_endpoint_id.in_(ep_ids))
            res_out = await self.session.execute(stmt_out)
            outgoing_conns = list(res_out.scalars().all())

            stmt_in = select(TopologyConnectionModel).where(TopologyConnectionModel.to_endpoint_id.in_(ep_ids))
            res_in = await self.session.execute(stmt_in)
            incoming_conns = list(res_in.scalars().all())

        return {
            "track_id": track.track_id,
            "section_id": track.section_id,
            "endpoints": endpoints,
            "outgoing_connections": outgoing_conns,
            "incoming_connections": incoming_conns,
        }
