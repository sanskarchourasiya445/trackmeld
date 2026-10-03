from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db_session
from backend.app.repositories.topology_repo import TopologyRepository
from backend.app.schemas.responses import (
    TopologyNodeResponse,
    TrackEndpointResponse,
    TopologyConnectionResponse,
    TrackTopologyResponse,
)
from backend.app.schemas.common import ErrorResponse
from backend.app.core.auth import get_current_user, AuthUser

router = APIRouter(prefix="/topology", tags=["Infrastructure Topology"])


# -----------------------------------------------------------------------------
# Topology Nodes
# -----------------------------------------------------------------------------
@router.get("/nodes", response_model=List[TopologyNodeResponse])
async def list_topology_nodes(
    response: Response,
    station_id: Optional[str] = Query(None, description="Filter by station ID"),
    node_type: Optional[str] = Query(None, description="Filter by node type (BOUNDARY_JOINT, STATION_THROAT, CROSSOVER_JUNCTION)"),
    limit: int = Query(100, ge=1, le=500, description="Maximum items to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(get_current_user),
) -> List[TopologyNodeResponse]:
    """List topology junction and boundary nodes with pagination and filtering."""
    repo = TopologyRepository(session)
    nodes = await repo.filter_nodes(
        station_id=station_id,
        node_type=node_type,
        limit=limit,
        offset=offset,
    )
    total_count = await repo.count_nodes(
        station_id=station_id,
        node_type=node_type,
    )
    response.headers["X-Total-Count"] = str(total_count)
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)
    return [TopologyNodeResponse.model_validate(n) for n in nodes]


@router.get(
    "/nodes/{node_id}",
    response_model=TopologyNodeResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_topology_node(
    node_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(get_current_user),
) -> TopologyNodeResponse:
    """Retrieve a single topology node by ID."""
    repo = TopologyRepository(session)
    node = await repo.get_node_by_id(node_id)
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "RESOURCE_NOT_FOUND",
                    "message": f"Topology node with ID '{node_id}' not found.",
                }
            },
        )
    return TopologyNodeResponse.model_validate(node)


# -----------------------------------------------------------------------------
# Track Endpoints
# -----------------------------------------------------------------------------
@router.get("/endpoints", response_model=List[TrackEndpointResponse])
async def list_track_endpoints(
    response: Response,
    track_id: Optional[str] = Query(None, description="Filter by track ID"),
    endpoint_type: Optional[str] = Query(None, description="Filter by endpoint type (START, END)"),
    limit: int = Query(100, ge=1, le=500, description="Maximum items to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(get_current_user),
) -> List[TrackEndpointResponse]:
    """List track boundary endpoints with pagination and filtering."""
    repo = TopologyRepository(session)
    endpoints = await repo.filter_endpoints(
        track_id=track_id,
        endpoint_type=endpoint_type,
        limit=limit,
        offset=offset,
    )
    total_count = await repo.count_endpoints(
        track_id=track_id,
        endpoint_type=endpoint_type,
    )
    response.headers["X-Total-Count"] = str(total_count)
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)
    return [TrackEndpointResponse.model_validate(ep) for ep in endpoints]


@router.get(
    "/endpoints/{endpoint_id}",
    response_model=TrackEndpointResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_track_endpoint(
    endpoint_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(get_current_user),
) -> TrackEndpointResponse:
    """Retrieve a single track boundary endpoint by ID."""
    repo = TopologyRepository(session)
    ep = await repo.get_endpoint_by_id(endpoint_id)
    if not ep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "RESOURCE_NOT_FOUND",
                    "message": f"Track endpoint with ID '{endpoint_id}' not found.",
                }
            },
        )
    return TrackEndpointResponse.model_validate(ep)


# -----------------------------------------------------------------------------
# Topology Connections
# -----------------------------------------------------------------------------
@router.get("/connections", response_model=List[TopologyConnectionResponse])
async def list_topology_connections(
    response: Response,
    node_id: Optional[str] = Query(None, description="Filter by topology node ID"),
    from_endpoint_id: Optional[str] = Query(None, description="Filter by outbound endpoint ID"),
    to_endpoint_id: Optional[str] = Query(None, description="Filter by inbound endpoint ID"),
    connection_type: Optional[str] = Query(None, description="Filter by connection type (CONTINUITY, TURNOUT_NORMAL, TURNOUT_REVERSE, CROSSOVER)"),
    limit: int = Query(100, ge=1, le=500, description="Maximum items to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(get_current_user),
) -> List[TopologyConnectionResponse]:
    """List physical rail connections between endpoints across nodes."""
    repo = TopologyRepository(session)
    conns = await repo.filter_connections(
        node_id=node_id,
        from_endpoint_id=from_endpoint_id,
        to_endpoint_id=to_endpoint_id,
        connection_type=connection_type,
        limit=limit,
        offset=offset,
    )
    total_count = await repo.count_connections(
        node_id=node_id,
        from_endpoint_id=from_endpoint_id,
        to_endpoint_id=to_endpoint_id,
        connection_type=connection_type,
    )
    response.headers["X-Total-Count"] = str(total_count)
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)
    return [TopologyConnectionResponse.model_validate(c) for c in conns]


@router.get(
    "/connections/{connection_id}",
    response_model=TopologyConnectionResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_topology_connection(
    connection_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(get_current_user),
) -> TopologyConnectionResponse:
    """Retrieve a single topology connection by ID."""
    repo = TopologyRepository(session)
    conn = await repo.get_connection_by_id(connection_id)
    if not conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "RESOURCE_NOT_FOUND",
                    "message": f"Topology connection with ID '{connection_id}' not found.",
                }
            },
        )
    return TopologyConnectionResponse.model_validate(conn)


# -----------------------------------------------------------------------------
# Track Topology Aggregation
# -----------------------------------------------------------------------------
@router.get(
    "/tracks/{track_id}",
    response_model=TrackTopologyResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_track_topology(
    track_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: AuthUser = Depends(get_current_user),
) -> TrackTopologyResponse:
    """Retrieve complete topology context for a track including boundary endpoints and connections."""
    repo = TopologyRepository(session)
    data = await repo.get_track_topology(track_id)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "RESOURCE_NOT_FOUND",
                    "message": f"Track with ID '{track_id}' not found.",
                }
            },
        )
    return TrackTopologyResponse(
        track_id=data["track_id"],
        section_id=data["section_id"],
        endpoints=[TrackEndpointResponse.model_validate(ep) for ep in data["endpoints"]],
        outgoing_connections=[TopologyConnectionResponse.model_validate(c) for c in data["outgoing_connections"]],
        incoming_connections=[TopologyConnectionResponse.model_validate(c) for c in data["incoming_connections"]],
    )
