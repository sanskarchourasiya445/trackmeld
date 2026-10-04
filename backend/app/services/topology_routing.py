"""Deterministic railway infrastructure topology route resolution service.

Part of Phase 17: Deterministic Route Resolution.

Mission:
Transforms high-level TrainPass intervals into physical, track-resolved TrainTraversal
records using explicit meso-level infrastructure topology (TopologyNode, TrackEndpoint,
TopologyConnection, Track, Section).

Core Architectural Invariants:
1. Rules classify -> Optimization schedules -> Independent Validator verifies -> Humans approve.
2. Route resolution determines physical path and track assignments. It does NOT schedule or optimize.
3. Consumes strictly EXPLICIT topology. Zero connectivity is inferred from station adjacency,
   section ordering, track IDs, or naming conventions.
4. When multiple valid physical paths exist through topology without authoritative priority,
   the system MUST return AMBIGUOUS_ROUTE and MUST NOT fabricate a track assignment.
5. If no topology exists at all for the requested corridor, safely falls back to coarse section-level
   expansion for backward compatibility.
6. CP-SAT solver and independent validator conflict rules remain untouched.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.app.domain.enums import (
    DataClass,
    EndpointType,
    TopologyConnectionType,
    TopologyTraversalDirection,
    TraversalResolutionStatus,
)
from backend.app.domain.temporal import TimeInterval, TrainPass, TrainTraversal


@dataclass
class ResolvedHop:
    """A single traversed block section and physical track along a route."""
    section_id: str
    from_station_id: str
    to_station_id: str
    track_id: str
    length_km: float
    connection_id: Optional[str] = None


@dataclass
class RouteResolutionResult:
    """Outcome of attempting to resolve a physical route for a TrainPass."""
    status: TraversalResolutionStatus
    unresolved_reason: Optional[str] = None
    hops: List[ResolvedHop] = field(default_factory=list)
    fallback_to_section: bool = False
    candidate_path_count: int = 0


class DeterministicTopologyRouter:
    """Pure domain router that deterministically maps TrainPass objects to physical track traversals."""

    def __init__(
        self,
        sections: List[Any],
        tracks: List[Any],
        topology_nodes: Optional[List[Any]] = None,
        topology_connections: Optional[List[Any]] = None,
        track_endpoints: Optional[List[Any]] = None,
    ) -> None:
        self.raw_sections = sections or []
        self.raw_tracks = tracks or []
        self.raw_nodes = topology_nodes or []
        self.raw_conns = topology_connections or []
        self.raw_endpoints = track_endpoints or []

        self._build_indexes()

    def _get_val(self, obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def _build_indexes(self) -> None:
        """Build deterministic in-memory graph lookups."""
        # 1. Sections
        self.sections_by_id: Dict[str, Any] = {}
        self.station_chainage: Dict[str, float] = {}
        self.direct_section_by_pair: Dict[Tuple[str, str], Any] = {}

        for s in self.raw_sections:
            sec_id = self._get_val(s, "section_id")
            if not sec_id:
                continue
            self.sections_by_id[sec_id] = s

            u = self._get_val(s, "from_station_id")
            v = self._get_val(s, "to_station_id")
            km_start = float(self._get_val(s, "kilometrage_start", 0.0) or 0.0)
            km_end = float(self._get_val(s, "kilometrage_end", 0.0) or 0.0)

            if u:
                self.station_chainage.setdefault(u, km_start)
            if v:
                self.station_chainage.setdefault(v, km_end)

            if u and v:
                self.direct_section_by_pair[(u, v)] = s
                self.direct_section_by_pair[(v, u)] = s

        # 2. Tracks
        self.tracks_by_id: Dict[str, Any] = {}
        self.tracks_by_section: Dict[str, List[Any]] = defaultdict(list)

        for t in self.raw_tracks:
            t_id = self._get_val(t, "track_id")
            sec_id = self._get_val(t, "section_id")
            if not t_id or not sec_id:
                continue
            self.tracks_by_id[t_id] = t
            self.tracks_by_section[sec_id].append(t)

        # Sort tracks by track_id for determinism
        for sec_id in self.tracks_by_section:
            self.tracks_by_section[sec_id].sort(key=lambda x: self._get_val(x, "track_id"))

        # 3. Endpoints
        self.endpoints_by_id: Dict[str, Any] = {}
        self.endpoints_by_track: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.track_by_endpoint: Dict[str, Any] = {}

        for ep in self.raw_endpoints:
            ep_id = self._get_val(ep, "endpoint_id")
            t_id = self._get_val(ep, "track_id")
            ep_type = self._get_val(ep, "endpoint_type")
            if not ep_id or not t_id or not ep_type:
                continue
            self.endpoints_by_id[ep_id] = ep
            self.endpoints_by_track[t_id][ep_type] = ep
            if t_id in self.tracks_by_id:
                self.track_by_endpoint[ep_id] = self.tracks_by_id[t_id]

        # 4. Topology Nodes
        self.nodes_by_id: Dict[str, Any] = {}
        self.nodes_by_station: Dict[str, List[Any]] = defaultdict(list)

        for n in self.raw_nodes:
            n_id = self._get_val(n, "node_id")
            stn_id = self._get_val(n, "station_id")
            if not n_id:
                continue
            self.nodes_by_id[n_id] = n
            if stn_id:
                self.nodes_by_station[stn_id].append(n)

        # 5. Topology Connections
        # Connections sorted deterministically by (type_rank, connection_id)
        type_rank = {
            "CONTINUITY": 1,
            "TURNOUT_NORMAL": 2,
            "TURNOUT_REVERSE": 3,
            "CROSSOVER": 4,
        }

        self.outgoing_conns: Dict[str, List[Any]] = defaultdict(list)
        self.incoming_conns: Dict[str, List[Any]] = defaultdict(list)

        sorted_conns = sorted(
            self.raw_conns,
            key=lambda c: (
                type_rank.get(str(self._get_val(c, "connection_type")), 99),
                self._get_val(c, "connection_id") or "",
            ),
        )

        for c in sorted_conns:
            from_ep = self._get_val(c, "from_endpoint_id")
            to_ep = self._get_val(c, "to_endpoint_id")
            if from_ep and to_ep:
                self.outgoing_conns[from_ep].append(c)
                self.incoming_conns[to_ep].append(c)

    def determine_travel_direction(self, from_stn: str, to_stn: str) -> str:
        """Determine nominal corridor direction ('DOWN' = increasing chainage, 'UP' = decreasing chainage)."""
        km_from = self.station_chainage.get(from_stn)
        km_to = self.station_chainage.get(to_stn)

        if km_from is not None and km_to is not None and km_from != km_to:
            return "DOWN" if km_from < km_to else "UP"

        # Fallback to direct section nominal orientation
        direct_sec = self.direct_section_by_pair.get((from_stn, to_stn))
        if direct_sec:
            sec_from = self._get_val(direct_sec, "from_station_id")
            return "DOWN" if sec_from == from_stn else "UP"

        return "DOWN"

    def _section_has_topology(self, sec_id: str) -> bool:
        """Check if any track on the section has endpoints referenced by topology connections."""
        for trk in self.tracks_by_section.get(sec_id, []):
            t_id = self._get_val(trk, "track_id")
            for ep_type in ("START", "END"):
                ep = self.endpoints_by_track.get(t_id, {}).get(ep_type)
                if ep:
                    ep_id = self._get_val(ep, "endpoint_id")
                    if ep_id in self.outgoing_conns or ep_id in self.incoming_conns:
                        return True
        return False

    def has_topology_for_corridor(self, from_stn: str, to_stn: str) -> bool:
        """Check whether explicit topology connections exist along the candidate corridor.
        
        If the corridor has no topology at all (e.g. tracks have zero connections, or endpoints
        lie outside the topology model), safe backward-compatible section expansion must be preserved.
        """
        if not self.raw_conns:
            return False

        if from_stn == to_stn or not from_stn or not to_stn:
            return False

        # Direct single section
        direct_sec = self.direct_section_by_pair.get((from_stn, to_stn))
        if direct_sec:
            sec_id = self._get_val(direct_sec, "section_id")
            return self._section_has_topology(sec_id)

        # Multi-section corridor: both origin and destination stations must touch sections with topology
        origin_has_topology = any(
            self._section_has_topology(self._get_val(s, "section_id"))
            for s in self.sections_by_id.values()
            if self._get_val(s, "from_station_id") == from_stn or self._get_val(s, "to_station_id") == from_stn
        )
        dest_has_topology = any(
            self._section_has_topology(self._get_val(s, "section_id"))
            for s in self.sections_by_id.values()
            if self._get_val(s, "from_station_id") == to_stn or self._get_val(s, "to_station_id") == to_stn
        )

        return origin_has_topology and dest_has_topology

    def is_track_direction_compatible(self, track: Any, travel_direction: str) -> bool:
        """Check if track's assigned direction allows train's travel direction."""
        trk_dir = self._get_val(track, "direction")
        if not trk_dir or trk_dir == "BIDIRECTIONAL":
            return True
        return trk_dir == travel_direction

    def resolve_pass_route(self, train_pass: TrainPass) -> RouteResolutionResult:
        """Deterministically resolve a TrainPass to physical section/track hops using explicit topology."""
        from_stn = train_pass.from_station_id or ""
        to_stn = train_pass.to_station_id or ""

        # 1. Dwell / Zero-distance
        if from_stn == to_stn or not from_stn or not to_stn:
            return RouteResolutionResult(
                status=TraversalResolutionStatus.UNRESOLVED,
                unresolved_reason=f"Station dwell or identical endpoints ({from_stn})",
                fallback_to_section=False,
            )

        # 2. Check if topology exists along this corridor
        if not self.has_topology_for_corridor(from_stn, to_stn):
            # Safe backward-compatible fallback: no topology exists anywhere on this corridor
            return RouteResolutionResult(
                status=TraversalResolutionStatus.UNRESOLVED,
                unresolved_reason="NO_TOPOLOGY",
                fallback_to_section=True,
            )

        # 3. Determine requested travel direction
        travel_dir = self.determine_travel_direction(from_stn, to_stn)

        # 4. Search for physical paths through explicit topology
        # A valid path is a sequence of ResolvedHop objects linking from_stn to to_stn.
        all_valid_paths = self._find_physical_paths(from_stn, to_stn, travel_dir)

        # 5. Evaluate search outcomes
        if not all_valid_paths:
            # Check if paths were rejected due to direction
            paths_ignoring_direction = self._find_physical_paths(from_stn, to_stn, travel_dir, ignore_direction=True)
            if paths_ignoring_direction:
                return RouteResolutionResult(
                    status=TraversalResolutionStatus.UNRESOLVED,
                    unresolved_reason="DIRECTION_CONFLICT: Physical connection exists but conflicts with track direction.",
                    fallback_to_section=False,
                    candidate_path_count=len(paths_ignoring_direction),
                )
            return RouteResolutionResult(
                status=TraversalResolutionStatus.UNRESOLVED,
                unresolved_reason="DISCONNECTED_ROUTE: Explicit topology exists on corridor but no continuous path connects endpoints.",
                fallback_to_section=False,
                candidate_path_count=0,
            )

        if len(all_valid_paths) > 1:
            # Multiple valid routes without authoritative priority -> AMBIGUOUS_ROUTE
            return RouteResolutionResult(
                status=TraversalResolutionStatus.AMBIGUOUS_ROUTE,
                unresolved_reason=f"AMBIGUOUS_ROUTE: Multiple valid physical paths ({len(all_valid_paths)}) found through topology without authoritative priority.",
                fallback_to_section=False,
                candidate_path_count=len(all_valid_paths),
            )

        # Exactly 1 valid physical route found
        unique_path = all_valid_paths[0]
        status = (
            TraversalResolutionStatus.DIRECT_SECTION
            if len(unique_path) == 1
            else TraversalResolutionStatus.EXPANDED_ROUTE
        )

        return RouteResolutionResult(
            status=status,
            unresolved_reason=None,
            hops=unique_path,
            fallback_to_section=False,
            candidate_path_count=1,
        )

    def _find_physical_paths(
        self,
        from_stn: str,
        to_stn: str,
        travel_dir: str,
        ignore_direction: bool = False,
    ) -> List[List[ResolvedHop]]:
        """Find all valid loop-free physical paths from from_stn to to_stn using explicit topology."""
        valid_paths: List[List[ResolvedHop]] = []

        # Find initial tracks departing from_stn
        # An initial section must touch from_stn
        initial_candidates: List[Tuple[Any, Any, str, str]] = []  # (track, section, entry_ep_type, exit_ep_type)

        for sec in self.sections_by_id.values():
            s_u = self._get_val(sec, "from_station_id")
            s_v = self._get_val(sec, "to_station_id")
            sec_id = self._get_val(sec, "section_id")

            if s_u == from_stn:
                entry_ep_type = "START"
                exit_ep_type = "END"
                hop_dest = s_v
            elif s_v == from_stn:
                entry_ep_type = "END"
                exit_ep_type = "START"
                hop_dest = s_u
            else:
                continue

            for trk in self.tracks_by_section.get(sec_id, []):
                if not ignore_direction and not self.is_track_direction_compatible(trk, travel_dir):
                    continue
                initial_candidates.append((trk, sec, entry_ep_type, exit_ep_type, hop_dest))

        # Sort initial candidates deterministically
        initial_candidates.sort(key=lambda x: self._get_val(x[0], "track_id"))

        # Queue for search: (current_track, current_section, current_exit_ep, current_station, current_path, visited_sections)
        for trk, sec, entry_ep_type, exit_ep_type, hop_dest in initial_candidates:
            trk_id = self._get_val(trk, "track_id")
            sec_id = self._get_val(sec, "section_id")
            length_km = float(self._get_val(sec, "length_km", 0.0) or 0.0)

            eps = self.endpoints_by_track.get(trk_id, {})
            exit_ep = eps.get(exit_ep_type)
            if not exit_ep:
                continue
            exit_ep_id = self._get_val(exit_ep, "endpoint_id")

            first_hop = ResolvedHop(
                section_id=sec_id,
                from_station_id=from_stn,
                to_station_id=hop_dest,
                track_id=trk_id,
                length_km=length_km,
                connection_id=None,
            )

            # If this single section already reaches to_stn
            if hop_dest == to_stn:
                valid_paths.append([first_hop])
                continue

            # Otherwise explore through outgoing connections from exit_ep_id
            stack: List[Tuple[str, str, str, List[ResolvedHop], Set[str]]] = [
                (trk_id, exit_ep_id, hop_dest, [first_hop], {sec_id})
            ]

            while stack:
                curr_trk_id, curr_exit_ep_id, curr_stn, path, visited_secs = stack.pop()

                if len(path) >= 10:  # Prevent runaway paths
                    continue

                # Query candidate connections connected to curr_exit_ep_id
                conns_fwd = self.outgoing_conns.get(curr_exit_ep_id, [])
                conns_rev = self.incoming_conns.get(curr_exit_ep_id, [])
                
                seen_c_ids = set()
                conns = []
                for c in conns_fwd + conns_rev:
                    cid = self._get_val(c, "connection_id")
                    if cid not in seen_c_ids:
                        seen_c_ids.add(cid)
                        conns.append(c)

                for conn in conns:
                    conn_id = self._get_val(conn, "connection_id")
                    from_ep = self._get_val(conn, "from_endpoint_id")
                    to_ep = self._get_val(conn, "to_endpoint_id")
                    dir_perm = self._get_val(conn, "traversal_direction", "FORWARD")

                    # Check connection traversal direction
                    if from_ep == curr_exit_ep_id:
                        if dir_perm not in ("FORWARD", "BIDIRECTIONAL"):
                            continue
                        next_ep_id = to_ep
                    elif to_ep == curr_exit_ep_id:
                        if dir_perm not in ("REVERSE", "BIDIRECTIONAL"):
                            continue
                        next_ep_id = from_ep
                    else:
                        continue

                    # Look up next track and section
                    next_ep = self.endpoints_by_id.get(next_ep_id)
                    if not next_ep:
                        continue
                    next_trk_id = self._get_val(next_ep, "track_id")
                    next_trk = self.tracks_by_id.get(next_trk_id)
                    if not next_trk:
                        continue

                    next_sec_id = self._get_val(next_trk, "section_id")
                    if next_sec_id in visited_secs:
                        continue  # Avoid loops

                    if not ignore_direction and not self.is_track_direction_compatible(next_trk, travel_dir):
                        continue

                    next_sec = self.sections_by_id.get(next_sec_id)
                    if not next_sec:
                        continue

                    # Determine next section endpoints and destination station
                    s_u = self._get_val(next_sec, "from_station_id")
                    s_v = self._get_val(next_sec, "to_station_id")
                    next_ep_type = self._get_val(next_ep, "endpoint_type")

                    if next_ep_type == "START":
                        next_exit_type = "END"
                        next_stn = s_v
                    else:
                        next_exit_type = "START"
                        next_stn = s_u

                    next_exit_ep = self.endpoints_by_track.get(next_trk_id, {}).get(next_exit_type)
                    if not next_exit_ep:
                        continue
                    next_exit_ep_id = self._get_val(next_exit_ep, "endpoint_id")

                    hop = ResolvedHop(
                        section_id=next_sec_id,
                        from_station_id=curr_stn,
                        to_station_id=next_stn,
                        track_id=next_trk_id,
                        length_km=float(self._get_val(next_sec, "length_km", 0.0) or 0.0),
                        connection_id=conn_id,
                    )

                    new_path = path + [hop]
                    if next_stn == to_stn:
                        valid_paths.append(new_path)
                    else:
                        stack.append(
                            (next_trk_id, next_exit_ep_id, next_stn, new_path, visited_secs | {next_sec_id})
                        )

        # Sort valid paths deterministically by track sequence
        valid_paths.sort(key=lambda p: tuple(h.track_id for h in p))
        return valid_paths
