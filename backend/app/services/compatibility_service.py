"""Deterministic Compatibility & Feasibility Evaluation Engine for TrackMeld.

Answers the core Phase 4 question:
"Can this task be placed at this time and location under the currently modeled data and rules, and exactly why?"

Guarantees:
1. Strict half-open interval conventions [start, end).
2. Four-tier constraint classification (HARD, SOFT, DIAGNOSTIC_ONLY, UNVERIFIED).
3. Unverified rules are NEVER promoted to HARD safety constraints.
4. Comprehensive, structured diagnostics with machine-readable reason codes.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import defaultdict

from backend.app.domain.temporal import TimeInterval, PlanningHorizon, TrainPass, TrainTraversal
from backend.app.domain.compatibility import (
    ConstraintSeverity,
    ReasonCode,
    ConflictType,
    ConflictDetail,
    RuleEvidence,
    ScheduledTaskPlacement,
    CompatibilityResult,
)
from backend.app.domain.enums import RuleClass, DataClass, TraversalResolutionStatus


class CompatibilityEngine:
    """Evaluates task feasibility and compatibility deterministically."""

    @staticmethod
    def derive_train_passes(
        train_movements: List[Any],
        sections: List[Any],
        horizon: PlanningHorizon,
    ) -> List[TrainPass]:
        """Derive continuous section traversal and station dwell passes across the planning horizon."""
        # 1. Build bidirectional station-pair lookup to section_id
        sec_lookup: Dict[Tuple[str, str], Any] = {}
        for s in sections:
            from_id = getattr(s, "from_station_id", None) or s.get("from_station_id")
            to_id = getattr(s, "to_station_id", None) or s.get("to_station_id")
            sec_id = getattr(s, "section_id", None) or s.get("section_id")
            if from_id and to_id and sec_id:
                sec_lookup[(from_id, to_id)] = s
                sec_lookup[(to_id, from_id)] = s

        # 2. Group movements by train_id
        by_train: Dict[str, List[Any]] = defaultdict(list)
        for m in train_movements:
            train_id = getattr(m, "train_id", None) or m.get("train_id")
            if train_id:
                by_train[train_id].append(m)

        train_passes: List[TrainPass] = []
        total_days = int(horizon.duration_hours // 24) + 1

        for train_id, movs in by_train.items():
            # Sort chronologically by stop_sequence
            sorted_movs = sorted(
                movs,
                key=lambda x: getattr(x, "stop_sequence", None) or x.get("stop_sequence", 0),
            )
            if not sorted_movs:
                continue

            train_number = getattr(sorted_movs[0], "train_number", None) or sorted_movs[0].get("train_number", "UNKNOWN")

            # Project across each 24-hour cycle in the planning horizon
            for day_idx in range(total_days):
                cycle_base_date = (horizon.start + timedelta(days=day_idx)).date()

                # Process consecutive station hops
                for i in range(len(sorted_movs) - 1):
                    m_curr = sorted_movs[i]
                    m_next = sorted_movs[i + 1]

                    curr_stn = getattr(m_curr, "station_id", None) or m_curr.get("station_id")
                    next_stn = getattr(m_next, "station_id", None) or m_next.get("station_id")

                    curr_dep_str = (
                        getattr(m_curr, "scheduled_departure", None)
                        or m_curr.get("scheduled_departure")
                        or getattr(m_curr, "scheduled_arrival", None)
                        or m_curr.get("scheduled_arrival")
                    )
                    next_arr_str = (
                        getattr(m_next, "scheduled_arrival", None)
                        or m_next.get("scheduled_arrival")
                        or getattr(m_next, "scheduled_departure", None)
                        or m_next.get("scheduled_departure")
                    )

                    if not curr_dep_str or not next_arr_str:
                        continue

                    curr_day_offset = getattr(m_curr, "day_offset", None) or m_curr.get("day_offset", 0)
                    next_day_offset = getattr(m_next, "day_offset", None) or m_next.get("day_offset", 0)

                    dep_h, dep_m = map(int, curr_dep_str.split(":"))
                    arr_h, arr_m = map(int, next_arr_str.split(":"))

                    t_start = datetime(
                        cycle_base_date.year,
                        cycle_base_date.month,
                        cycle_base_date.day,
                        dep_h,
                        dep_m,
                        tzinfo=timezone.utc,
                    ) + timedelta(days=curr_day_offset)

                    t_end = datetime(
                        cycle_base_date.year,
                        cycle_base_date.month,
                        cycle_base_date.day,
                        arr_h,
                        arr_m,
                        tzinfo=timezone.utc,
                    ) + timedelta(days=next_day_offset)

                    # Handle overnight traversal
                    if t_end <= t_start:
                        t_end += timedelta(days=1)

                    # If outside horizon entirely, skip
                    if t_end <= horizon.start or t_start >= horizon.end:
                        continue

                    # Look up section
                    matched_sec = sec_lookup.get((curr_stn, next_stn))
                    sec_id = getattr(matched_sec, "section_id", None) if matched_sec else None

                    curr_mov_id = getattr(m_curr, "movement_id", None) or m_curr.get("movement_id", "")
                    next_mov_id = getattr(m_next, "movement_id", None) or m_next.get("movement_id", "")

                    pass_id = f"PASS-{train_number}-{curr_stn}-{next_stn}-D{day_idx}"
                    train_passes.append(
                        TrainPass(
                            pass_id=pass_id,
                            train_id=train_id,
                            train_number=train_number,
                            section_id=sec_id,
                            from_station_id=curr_stn,
                            to_station_id=next_stn,
                            interval=TimeInterval(start=t_start, end=t_end),
                            movement_type="SECTION_TRAVERSAL" if sec_id else "STATION_HOP",
                            source_movement_ids=[curr_mov_id, next_mov_id],
                            classification=DataClass.REAL,
                        )
                    )

        return train_passes

    @classmethod
    def expand_train_traversals(
        cls,
        train_passes: List[TrainPass],
        sections: List[Any],
        tracks: Optional[List[Any]] = None,
        topology_nodes: Optional[List[Any]] = None,
        topology_connections: Optional[List[Any]] = None,
        track_endpoints: Optional[List[Any]] = None,
    ) -> List[TrainTraversal]:
        """Deterministically expand train passes into ordered physical section traversals.
        
        Distinguishes:
        - DIRECT_SECTION: Pass directly connects adjacent stations of a single block section.
        - EXPANDED_ROUTE: Pass traverses multiple intermediate block sections via topological shortest path.
        - AMBIGUOUS_ROUTE: Multiple valid physical paths found through topology without authoritative priority.
        - UNRESOLVED: Topological path between endpoints could not be resolved.
        """
        import heapq

        router = None
        if tracks:
            from backend.app.services.topology_routing import DeterministicTopologyRouter
            router = DeterministicTopologyRouter(
                sections=sections,
                tracks=tracks,
                topology_nodes=topology_nodes,
                topology_connections=topology_connections,
                track_endpoints=track_endpoints,
            )

        # 1. Build direct section lookup and adjacency graph
        direct_lookup: Dict[Tuple[str, str], Tuple[str, float, Any]] = {}
        # adj: station_id -> list of (neighbor_station_id, section_id, length_km, section_obj)
        adj: Dict[str, List[Tuple[str, str, float, Any]]] = defaultdict(list)

        for s in sections:
            u = getattr(s, "from_station_id", None) or (s.get("from_station_id") if isinstance(s, dict) else None)
            v = getattr(s, "to_station_id", None) or (s.get("to_station_id") if isinstance(s, dict) else None)
            sec_id = getattr(s, "section_id", None) or (s.get("section_id") if isinstance(s, dict) else None)
            raw_len = getattr(s, "length_km", None) or (s.get("length_km") if isinstance(s, dict) else 0.0)
            length_km = float(raw_len or 0.0)
            if u and v and sec_id:
                direct_lookup[(u, v)] = (sec_id, length_km, s)
                direct_lookup[(v, u)] = (sec_id, length_km, s)
                adj[u].append((v, sec_id, length_km, s))
                adj[v].append((u, sec_id, length_km, s))

        # Sort adjacency for deterministic tie-breaking
        for stn in adj:
            adj[stn].sort(key=lambda x: (x[2], x[1]))

        def find_section_path(start_stn: str, end_stn: str) -> Optional[List[Tuple[str, str, str, float]]]:
            """Dijkstra shortest path by distance between start_stn and end_stn.
            Returns ordered list of (from_stn, to_stn, section_id, length_km) or None.
            """
            if start_stn == end_stn:
                return []
            if start_stn not in adj or end_stn not in adj:
                return None

            pq: List[Tuple[float, str, List[Tuple[str, str, str, float]]]] = [(0.0, start_stn, [])]
            best_dist: Dict[str, float] = {start_stn: 0.0}

            while pq:
                d, curr, path = heapq.heappop(pq)
                if curr == end_stn:
                    return path
                if d > best_dist.get(curr, float("inf")):
                    continue

                for nbr, sec_id, length_km, _ in adj[curr]:
                    new_dist = d + length_km
                    if new_dist < best_dist.get(nbr, float("inf")):
                        best_dist[nbr] = new_dist
                        heapq.heappush(pq, (new_dist, nbr, path + [(curr, nbr, sec_id, length_km)]))
            return None

        traversals: List[TrainTraversal] = []

        for p in train_passes:
            from_stn = p.from_station_id or ""
            to_stn = p.to_station_id or ""

            # Extract day index from pass_id (e.g. PASS-12301-STN-A-STN-B-D0)
            day_token = "D0"
            if "-D" in p.pass_id:
                day_token = "D" + p.pass_id.split("-D")[-1]

            # Case A: Same station (dwell / zero-distance)
            if from_stn == to_stn:
                t_id = f"TRV-{p.train_number}-{p.section_id or 'STN'}-S1-{day_token}"
                traversals.append(
                    TrainTraversal(
                        traversal_id=t_id,
                        train_id=p.train_id,
                        train_number=p.train_number,
                        source_pass_id=p.pass_id,
                        section_id=p.section_id,
                        from_station_id=from_stn,
                        to_station_id=to_stn,
                        sequence_order=1,
                        interval=p.interval,
                        traversal_track_id=None,
                        resolution_status=TraversalResolutionStatus.DIRECT_SECTION if p.section_id else TraversalResolutionStatus.UNRESOLVED,
                        unresolved_reason=None if p.section_id else f"Station dwell or identical endpoints ({from_stn})",
                        classification=DataClass.DERIVED,
                    )
                )
                continue

            # Case B: Deterministic Topology Router (Phase 17)
            if router is not None:
                res = router.resolve_pass_route(p)
                if not res.fallback_to_section:
                    if res.status in (TraversalResolutionStatus.DIRECT_SECTION, TraversalResolutionStatus.EXPANDED_ROUTE):
                        total_len = sum(h.length_km for h in res.hops)
                        total_duration_sec = p.interval.duration_seconds
                        num_hops = len(res.hops)

                        t_start = p.interval.start
                        t_end = p.interval.end

                        cum_sec = 0.0
                        timestamps = [t_start]
                        for hop in res.hops[:-1]:
                            frac = (hop.length_km / total_len) if total_len > 0 else (1.0 / num_hops)
                            cum_sec += total_duration_sec * frac
                            timestamps.append(t_start + timedelta(seconds=cum_sec))
                        timestamps.append(t_end)

                        for seq_idx, hop in enumerate(res.hops, start=1):
                            hop_interval = TimeInterval(
                                start=timestamps[seq_idx - 1],
                                end=timestamps[seq_idx],
                            )
                            t_id = f"TRV-{p.train_number}-{hop.section_id}-S{seq_idx}-{day_token}"
                            traversals.append(
                                TrainTraversal(
                                    traversal_id=t_id,
                                    train_id=p.train_id,
                                    train_number=p.train_number,
                                    source_pass_id=p.pass_id,
                                    section_id=hop.section_id,
                                    from_station_id=hop.from_station_id,
                                    to_station_id=hop.to_station_id,
                                    sequence_order=seq_idx,
                                    interval=hop_interval,
                                    traversal_track_id=hop.track_id,
                                    resolution_status=res.status,
                                    unresolved_reason=None,
                                    classification=DataClass.DERIVED,
                                )
                            )
                        continue
                    elif res.status == TraversalResolutionStatus.AMBIGUOUS_ROUTE:
                        t_id = f"TRV-{p.train_number}-{p.section_id or 'AMBIGUOUS'}-S1-{day_token}"
                        traversals.append(
                            TrainTraversal(
                                traversal_id=t_id,
                                train_id=p.train_id,
                                train_number=p.train_number,
                                source_pass_id=p.pass_id,
                                section_id=p.section_id,
                                from_station_id=from_stn,
                                to_station_id=to_stn,
                                sequence_order=1,
                                interval=p.interval,
                                traversal_track_id=None,
                                resolution_status=TraversalResolutionStatus.AMBIGUOUS_ROUTE,
                                unresolved_reason=res.unresolved_reason,
                                classification=DataClass.DERIVED,
                            )
                        )
                        continue
                    elif res.status == TraversalResolutionStatus.UNRESOLVED:
                        t_id = f"TRV-{p.train_number}-UNRESOLVED-S1-{day_token}"
                        traversals.append(
                            TrainTraversal(
                                traversal_id=t_id,
                                train_id=p.train_id,
                                train_number=p.train_number,
                                source_pass_id=p.pass_id,
                                section_id=None,
                                from_station_id=from_stn,
                                to_station_id=to_stn,
                                sequence_order=1,
                                interval=p.interval,
                                traversal_track_id=None,
                                resolution_status=TraversalResolutionStatus.UNRESOLVED,
                                unresolved_reason=res.unresolved_reason,
                                classification=DataClass.DERIVED,
                            )
                        )
                        continue

            # Case B: Direct single block section
            if (from_stn, to_stn) in direct_lookup:
                sec_id, length_km, _ = direct_lookup[(from_stn, to_stn)]
                t_id = f"TRV-{p.train_number}-{sec_id}-S1-{day_token}"
                traversals.append(
                    TrainTraversal(
                        traversal_id=t_id,
                        train_id=p.train_id,
                        train_number=p.train_number,
                        source_pass_id=p.pass_id,
                        section_id=sec_id,
                        from_station_id=from_stn,
                        to_station_id=to_stn,
                        sequence_order=1,
                        interval=p.interval,
                        traversal_track_id=None,
                        resolution_status=TraversalResolutionStatus.DIRECT_SECTION,
                        unresolved_reason=None,
                        classification=DataClass.DERIVED,
                    )
                )
                continue

            # Case C: Route expansion across multi-section path
            path = find_section_path(from_stn, to_stn)
            if path:
                total_len = sum(h[3] for h in path)
                total_duration_sec = p.interval.duration_seconds
                num_hops = len(path)

                # Partition total duration proportionally by section length
                t_start = p.interval.start
                t_end = p.interval.end

                cum_sec = 0.0
                timestamps = [t_start]
                for hop in path[:-1]:
                    hop_len = hop[3]
                    frac = (hop_len / total_len) if total_len > 0 else (1.0 / num_hops)
                    cum_sec += total_duration_sec * frac
                    timestamps.append(t_start + timedelta(seconds=cum_sec))
                timestamps.append(t_end)

                for seq_idx, hop in enumerate(path, start=1):
                    hop_from, hop_to, hop_sec_id, _ = hop
                    hop_interval = TimeInterval(
                        start=timestamps[seq_idx - 1],
                        end=timestamps[seq_idx],
                    )
                    t_id = f"TRV-{p.train_number}-{hop_sec_id}-S{seq_idx}-{day_token}"
                    traversals.append(
                        TrainTraversal(
                            traversal_id=t_id,
                            train_id=p.train_id,
                            train_number=p.train_number,
                            source_pass_id=p.pass_id,
                            section_id=hop_sec_id,
                            from_station_id=hop_from,
                            to_station_id=hop_to,
                            sequence_order=seq_idx,
                            interval=hop_interval,
                            traversal_track_id=None,
                            resolution_status=TraversalResolutionStatus.EXPANDED_ROUTE,
                            unresolved_reason=None,
                            classification=DataClass.DERIVED,
                        )
                    )
                continue

            # Case D: Unresolved route
            t_id = f"TRV-{p.train_number}-UNRESOLVED-S1-{day_token}"
            traversals.append(
                TrainTraversal(
                    traversal_id=t_id,
                    train_id=p.train_id,
                    train_number=p.train_number,
                    source_pass_id=p.pass_id,
                    section_id=None,
                    from_station_id=from_stn,
                    to_station_id=to_stn,
                    sequence_order=1,
                    interval=p.interval,
                    traversal_track_id=None,
                    resolution_status=TraversalResolutionStatus.UNRESOLVED,
                    unresolved_reason=f"No topological section path found connecting station '{from_stn}' to '{to_stn}'",
                    classification=DataClass.DERIVED,
                )
            )

        return traversals

    @classmethod
    def evaluate_task_placement(
        cls,
        task: Any,
        candidate_start: datetime,
        candidate_end: datetime,
        horizon: PlanningHorizon,
        train_passes: List[TrainPass],
        existing_placements: List[ScheduledTaskPlacement],
        resource_availabilities: List[Any],
        dependencies: List[Any],
        sections_map: Dict[str, Any],
        rules_map: Dict[str, Any],
        resources_map: Optional[Dict[str, Any]] = None,
    ) -> CompatibilityResult:
        """Deterministically assess candidate task placement feasibility against all modeled constraints."""
        conflicts: List[ConflictDetail] = []
        reason_codes_set: Set[ReasonCode] = set()
        affected_sections: Set[str] = set()
        affected_movements: Set[str] = set()
        affected_resources: Set[str] = set()
        rule_evidence_list: List[RuleEvidence] = []

        task_id = getattr(task, "task_id", None) or task.get("task_id", "UNKNOWN")
        task_code = getattr(task, "task_code", None) or task.get("task_code", task_id)
        primary_section_id = getattr(task, "section_id", None) or task.get("section_id")
        if primary_section_id:
            affected_sections.add(primary_section_id)

        # Secondary / multi-section impacts
        additional_sec_ids = []
        if hasattr(task, "affected_sections"):
            additional_sec_ids = [s.section_id for s in task.affected_sections]
        elif "additional_sections" in task:
            additional_sec_ids = task["additional_sections"]
        for s_id in additional_sec_ids:
            affected_sections.add(s_id)

        # Ensure UTC timezone awareness
        if candidate_start.tzinfo is None:
            candidate_start = candidate_start.replace(tzinfo=timezone.utc)
        if candidate_end.tzinfo is None:
            candidate_end = candidate_end.replace(tzinfo=timezone.utc)

        # ---------------------------------------------------------------------
        # 1. TIME INTERVAL VALIDITY CHECK [start, end)
        # ---------------------------------------------------------------------
        interval_valid = candidate_start < candidate_end
        if not interval_valid:
            if candidate_start == candidate_end:
                conflicts.append(
                    ConflictDetail(
                        conflict_type=ConflictType.INTERVAL_INVALID,
                        severity=ConstraintSeverity.HARD,
                        reason_code=ReasonCode.INVALID_INTERVAL,
                        message=f"Candidate interval is zero-duration [{candidate_start.isoformat()}, {candidate_end.isoformat()}). Half-open interval requires start < end.",
                        conflicting_entity_type="INTERVAL",
                        conflicting_entity_id=task_id,
                    )
                )
            else:
                conflicts.append(
                    ConflictDetail(
                        conflict_type=ConflictType.INTERVAL_INVALID,
                        severity=ConstraintSeverity.HARD,
                        reason_code=ReasonCode.INVALID_INTERVAL,
                        message=f"Candidate interval has negative duration: start ({candidate_start.isoformat()}) > end ({candidate_end.isoformat()}).",
                        conflicting_entity_type="INTERVAL",
                        conflicting_entity_id=task_id,
                    )
                )
            reason_codes_set.add(ReasonCode.INVALID_INTERVAL)

            # Return degenerate interval with zero duration
            dummy_interval = TimeInterval(start=candidate_start, end=candidate_start + timedelta(seconds=1))
            return CompatibilityResult(
                task_id=task_id,
                compatible=False,
                feasible_hard=False,
                admissible_soft=False,
                evaluated_interval=dummy_interval,
                possession_interval=dummy_interval,
                reason_codes=list(reason_codes_set),
                conflicts=conflicts,
                affected_sections=list(affected_sections),
            )

        candidate_interval = TimeInterval(start=candidate_start, end=candidate_end)

        # Duration match check against task estimated duration
        est_duration = getattr(task, "estimated_duration_minutes", None) or task.get("estimated_duration_minutes")
        if est_duration is not None and abs(candidate_interval.duration_minutes - est_duration) > 0.01:
            conflicts.append(
                ConflictDetail(
                    conflict_type=ConflictType.INTERVAL_INVALID,
                    severity=ConstraintSeverity.HARD,
                    reason_code=ReasonCode.INVALID_INTERVAL,
                    message=f"Candidate duration ({candidate_interval.duration_minutes:.1f}m) does not match task estimated duration ({est_duration}m).",
                    conflicting_entity_type="TASK_DURATION",
                    conflicting_entity_id=task_id,
                )
            )
            reason_codes_set.add(ReasonCode.INVALID_INTERVAL)

        # ---------------------------------------------------------------------
        # 2. PLANNING HORIZON ENCLOSURE CHECK
        # ---------------------------------------------------------------------
        if not horizon.contains_interval(candidate_interval):
            conflicts.append(
                ConflictDetail(
                    conflict_type=ConflictType.HORIZON_BREACH,
                    severity=ConstraintSeverity.HARD,
                    reason_code=ReasonCode.OUTSIDE_PLANNING_HORIZON,
                    message=f"Candidate interval {candidate_interval} falls outside planning horizon {horizon.interval}.",
                    conflicting_entity_type="PLANNING_HORIZON",
                    conflicting_entity_id="HORIZON",
                )
            )
            reason_codes_set.add(ReasonCode.OUTSIDE_PLANNING_HORIZON)

        # ---------------------------------------------------------------------
        # 3. TASK ALLOWED PLANNING WINDOW CHECK
        # ---------------------------------------------------------------------
        win_start = getattr(task, "window_start", None) or task.get("window_start")
        win_end = getattr(task, "window_end", None) or task.get("window_end")
        if isinstance(win_start, str):
            win_start = datetime.fromisoformat(win_start)
        if isinstance(win_end, str):
            win_end = datetime.fromisoformat(win_end)

        if win_start and win_end:
            if win_start.tzinfo is None:
                win_start = win_start.replace(tzinfo=timezone.utc)
            if win_end.tzinfo is None:
                win_end = win_end.replace(tzinfo=timezone.utc)

            task_window = TimeInterval(start=win_start, end=win_end)
            if not task_window.contains_interval(candidate_interval):
                conflicts.append(
                    ConflictDetail(
                        conflict_type=ConflictType.WINDOW_BREACH,
                        severity=ConstraintSeverity.HARD,
                        reason_code=ReasonCode.TASK_WINDOW_CONFLICT,
                        message=f"Candidate interval {candidate_interval} extends outside allowed task window {task_window}.",
                        conflicting_entity_type="WORK_WINDOW",
                        conflicting_entity_id=task_id,
                    )
                )
                reason_codes_set.add(ReasonCode.TASK_WINDOW_CONFLICT)

        # ---------------------------------------------------------------------
        # 4. EFFECTIVE POSSESSION & SETUP/SAFETY BUFFERS
        # ---------------------------------------------------------------------
        buf_before = timedelta(minutes=getattr(task, "safety_buffer_before_minutes", None) or task.get("safety_buffer_before_minutes", 15))
        buf_after = timedelta(minutes=getattr(task, "safety_buffer_after_minutes", None) or task.get("safety_buffer_after_minutes", 15))
        possession_start = candidate_start - buf_before
        possession_end = candidate_end + buf_after
        possession_interval = TimeInterval(start=possession_start, end=possession_end)

        # ---------------------------------------------------------------------
        # 5. BLOCK REQUIREMENT COMPATIBILITY (Power & Electrification)
        # ---------------------------------------------------------------------
        requires_power = getattr(task, "requires_power_block", None)
        if requires_power is None:
            requires_power = task.get("requires_power_block", False)

        if requires_power:
            for sec_id in affected_sections:
                sec = sections_map.get(sec_id)
                electrified = True
                if isinstance(sec, dict):
                    electrified = sec.get("electrified", True)
                elif hasattr(sec, "electrified"):
                    electrified = sec.electrified
                if not electrified:
                    conflicts.append(
                        ConflictDetail(
                            conflict_type=ConflictType.BLOCK_MISMATCH,
                            severity=ConstraintSeverity.HARD,
                            reason_code=ReasonCode.POWER_BLOCK_REQUIRED,
                            message=f"Task requires power block but block section {sec_id} is not electrified.",
                            conflicting_entity_type="SECTION",
                            conflicting_entity_id=sec_id,
                        )
                    )
                    reason_codes_set.add(ReasonCode.POWER_BLOCK_REQUIRED)

        # ---------------------------------------------------------------------
        # 6. TRAIN OCCUPANCY CONFLICT DETECTION
        # ---------------------------------------------------------------------
        requires_traffic = getattr(task, "requires_traffic_block", None)
        if requires_traffic is None:
            requires_traffic = task.get("requires_traffic_block", True)

        if requires_traffic:
            for pass_obj in train_passes:
                if pass_obj.section_id in affected_sections:
                    # Check half-open overlap with possession interval
                    if possession_interval.overlaps(pass_obj.interval):
                        overlap = possession_interval.intersection(pass_obj.interval)
                        conflicts.append(
                            ConflictDetail(
                                conflict_type=ConflictType.TRAIN_CROSSING,
                                severity=ConstraintSeverity.HARD,
                                reason_code=ReasonCode.TRAIN_MOVEMENT_CONFLICT,
                                message=f"Train movement {pass_obj.train_number} occupies section {pass_obj.section_id} during possession window.",
                                conflicting_entity_type="TRAIN_PASS",
                                conflicting_entity_id=pass_obj.pass_id,
                                conflict_interval=overlap,
                                evidence={
                                    "train_id": pass_obj.train_id,
                                    "train_number": pass_obj.train_number,
                                    "section_id": pass_obj.section_id,
                                    "pass_interval": str(pass_obj.interval),
                                    "possession_interval": str(possession_interval),
                                },
                            )
                        )
                        reason_codes_set.add(ReasonCode.TRAIN_MOVEMENT_CONFLICT)
                        reason_codes_set.add(ReasonCode.TRAFFIC_BLOCK_REQUIRED)
                        affected_movements.add(pass_obj.train_id)

        # ---------------------------------------------------------------------
        # 7. SECTION EXCLUSIVITY & MULTI-SECTION TASK CONFLICTS
        # ---------------------------------------------------------------------
        for existing in existing_placements:
            if existing.task_id == task_id:
                continue

            # Does possession overlap with existing task's possession window?
            if possession_interval.overlaps(existing.possession_interval):
                overlap = possession_interval.intersection(existing.possession_interval)
                existing_sections = {existing.section_id} | set(existing.additional_section_ids)

                # Primary section overlap
                if primary_section_id in existing_sections:
                    conflicts.append(
                        ConflictDetail(
                            conflict_type=ConflictType.SECTION_OCCUPANCY,
                            severity=ConstraintSeverity.HARD,
                            reason_code=ReasonCode.SECTION_OCCUPANCY_CONFLICT,
                            message=f"Primary section {primary_section_id} concurrently occupied by task {existing.task_code}.",
                            conflicting_entity_type="MAINTENANCE_TASK",
                            conflicting_entity_id=existing.task_id,
                            conflict_interval=overlap,
                        )
                    )
                    reason_codes_set.add(ReasonCode.SECTION_OCCUPANCY_CONFLICT)

                # Multi-section / secondary section overlap
                common_secondary = set(additional_sec_ids) & existing_sections
                if common_secondary:
                    conflicts.append(
                        ConflictDetail(
                            conflict_type=ConflictType.SECTION_OCCUPANCY,
                            severity=ConstraintSeverity.HARD,
                            reason_code=ReasonCode.MULTI_SECTION_CONFLICT,
                            message=f"Multi-section overlap on {list(common_secondary)} with concurrent task {existing.task_code}.",
                            conflicting_entity_type="MAINTENANCE_TASK",
                            conflicting_entity_id=existing.task_id,
                            conflict_interval=overlap,
                        )
                    )
                    reason_codes_set.add(ReasonCode.MULTI_SECTION_CONFLICT)

        # ---------------------------------------------------------------------
        # 8. RESOURCE AVAILABILITY & CONCURRENT OVERLAP CHECKS
        # ---------------------------------------------------------------------
        requirements = getattr(task, "resource_requirements", [])
        if not requirements and "resource_requirements" in task:
            requirements = task["resource_requirements"]

        for req in requirements:
            res_id = getattr(req, "resource_id", None) or req.get("resource_id")
            mandatory_req = getattr(req, "mandatory", True) if hasattr(req, "mandatory") else req.get("mandatory", True)
            req_qty = getattr(req, "quantity", 1) if hasattr(req, "quantity") else (req.get("quantity", 1) if isinstance(req, dict) else 1)
            if req_qty is None or req_qty < 1:
                req_qty = 1

            if res_id:
                affected_resources.add(res_id)

                # Check resource catalog presence if resources_map is provided and non-empty
                if resources_map is not None and len(resources_map) > 0 and res_id not in resources_map:
                    conflicts.append(
                        ConflictDetail(
                            conflict_type=ConflictType.RESOURCE_SHORTAGE,
                            severity=ConstraintSeverity.HARD,
                            reason_code=ReasonCode.RESOURCE_UNAVAILABLE,
                            message=f"Required resource {res_id} does not exist in scenario resource catalog.",
                            conflicting_entity_type="RESOURCE",
                            conflicting_entity_id=res_id,
                        )
                    )
                    reason_codes_set.add(ReasonCode.RESOURCE_UNAVAILABLE)
                    continue

                res_obj = resources_map.get(res_id) if resources_map else None
                capacity = 1
                if res_obj:
                    capacity = res_obj.get("capacity", 1) if isinstance(res_obj, dict) else getattr(res_obj, "capacity", 1)
                if capacity < 1:
                    capacity = 1

                # Check if requested quantity exceeds capacity
                if req_qty > capacity:
                    conflicts.append(
                        ConflictDetail(
                            conflict_type=ConflictType.RESOURCE_SHORTAGE,
                            severity=ConstraintSeverity.HARD,
                            reason_code=ReasonCode.RESOURCE_UNAVAILABLE,
                            message=f"Required quantity ({req_qty}) for resource {res_id} exceeds available capacity ({capacity}).",
                            conflicting_entity_type="RESOURCE",
                            conflicting_entity_id=res_id,
                        )
                    )
                    reason_codes_set.add(ReasonCode.RESOURCE_UNAVAILABLE)

                # Check active availability window in scenario only if records are defined for this resource
                matching_avail = False
                res_has_records = False
                for a in resource_availabilities:
                    a_res_id = getattr(a, "resource_id", None) or a.get("resource_id")
                    if a_res_id == res_id:
                        res_has_records = True
                        a_from = getattr(a, "available_from", None) or a.get("available_from")
                        a_until = getattr(a, "available_until", None) or a.get("available_until")
                        if isinstance(a_from, str):
                            a_from = datetime.fromisoformat(a_from)
                        if isinstance(a_until, str):
                            a_until = datetime.fromisoformat(a_until)
                        if a_from.tzinfo is None:
                            a_from = a_from.replace(tzinfo=timezone.utc)
                        if a_until.tzinfo is None:
                            a_until = a_until.replace(tzinfo=timezone.utc)

                        avail_int = TimeInterval(start=a_from, end=a_until)
                        # Check status
                        a_status = a.get("availability_status", "AVAILABLE") if isinstance(a, dict) else getattr(a, "availability_status", "AVAILABLE")
                        if hasattr(a_status, "value"):
                            a_status = a_status.value
                        elif isinstance(a_status, dict):
                            a_status = a_status.get("value", "AVAILABLE")

                        if a_status == "AVAILABLE" and avail_int.contains_interval(candidate_interval):
                            matching_avail = True
                            break

                if res_has_records and not matching_avail:
                    severity = ConstraintSeverity.HARD if mandatory_req else ConstraintSeverity.SOFT
                    conflicts.append(
                        ConflictDetail(
                            conflict_type=ConflictType.RESOURCE_SHORTAGE,
                            severity=severity,
                            reason_code=ReasonCode.RESOURCE_UNAVAILABLE,
                            message=f"Required resource {res_id} has no active availability window enclosing {candidate_interval}.",
                            conflicting_entity_type="RESOURCE",
                            conflicting_entity_id=res_id,
                        )
                    )
                    reason_codes_set.add(ReasonCode.RESOURCE_UNAVAILABLE)

                # Check concurrent assignment to other placed tasks respecting capacity
                concurrent_demand = 0
                overlapping_task_codes = []
                last_overlap = None
                for existing in existing_placements:
                    if existing.task_id == task_id:
                        continue
                    if res_id in existing.assigned_resource_ids:
                        if candidate_interval.overlaps(existing.interval):
                            concurrent_demand += 1
                            overlapping_task_codes.append(existing.task_code)
                            last_overlap = candidate_interval.intersection(existing.interval)

                if concurrent_demand + req_qty > capacity:
                    conflicts.append(
                        ConflictDetail(
                            conflict_type=ConflictType.RESOURCE_BUSY,
                            severity=ConstraintSeverity.HARD,
                            reason_code=ReasonCode.RESOURCE_OVERLAP,
                            message=f"Resource {res_id} capacity ({capacity}) exceeded by concurrent tasks {overlapping_task_codes} plus demand ({req_qty}).",
                            conflicting_entity_type="RESOURCE",
                            conflicting_entity_id=res_id,
                            conflict_interval=last_overlap,
                        )
                    )
                    reason_codes_set.add(ReasonCode.RESOURCE_OVERLAP)

        # ---------------------------------------------------------------------
        # 9. TASK DEPENDENCY CHECKS (FINISH_TO_START)
        # ---------------------------------------------------------------------
        for dep in dependencies:
            succ_id = getattr(dep, "successor_task_id", None) or dep.get("successor_task_id")
            pred_id = getattr(dep, "predecessor_task_id", None) or dep.get("predecessor_task_id")
            min_int = getattr(dep, "min_interval_minutes", 0) if hasattr(dep, "min_interval_minutes") else (dep.get("min_interval_minutes", 0) if isinstance(dep, dict) else 0)
            if min_int is None or min_int < 0:
                min_int = 0

            if succ_id == task_id:
                pred_placement = next((p for p in existing_placements if p.task_id == pred_id), None)
                if not pred_placement:
                    conflicts.append(
                        ConflictDetail(
                            conflict_type=ConflictType.PRECEDENCE_VIOLATION,
                            severity=ConstraintSeverity.HARD,
                            reason_code=ReasonCode.DEPENDENCY_NOT_SATISFIED,
                            message=f"Predecessor task {pred_id} is not scheduled prior to candidate start {candidate_start.isoformat()}.",
                            conflicting_entity_type="MAINTENANCE_TASK",
                            conflicting_entity_id=pred_id,
                        )
                    )
                    reason_codes_set.add(ReasonCode.DEPENDENCY_NOT_SATISFIED)
                else:
                    req_start = pred_placement.interval.end + timedelta(minutes=min_int)
                    if candidate_start < req_start:
                        conflicts.append(
                            ConflictDetail(
                                conflict_type=ConflictType.PRECEDENCE_VIOLATION,
                                severity=ConstraintSeverity.HARD,
                                reason_code=ReasonCode.DEPENDENCY_NOT_SATISFIED,
                                message=f"Predecessor task {pred_placement.task_code} finishes at {pred_placement.interval.end.isoformat()}, requires min gap {min_int}m until {req_start.isoformat()} (violates FINISH_TO_START with candidate start {candidate_start.isoformat()}).",
                                conflicting_entity_type="MAINTENANCE_TASK",
                                conflicting_entity_id=pred_id,
                            )
                        )
                        reason_codes_set.add(ReasonCode.DEPENDENCY_NOT_SATISFIED)

        # ---------------------------------------------------------------------
        # 10. RULE EVIDENCE & UNVERIFIED CONSTRAINT HANDLING
        # ---------------------------------------------------------------------
        # Evaluate rules associated with the task
        task_rule_ids = []
        if hasattr(task, "rule_references"):
            task_rule_ids = [r.rule_id for r in task.rule_references]
        elif "rule_reference_ids" in task:
            task_rule_ids = task["rule_reference_ids"]
        elif "rule_references" in task:
            task_rule_ids = [r.get("rule_id") for r in task["rule_references"] if "rule_id" in r]

        if not task_rule_ids and rules_map:
            task_rule_ids = list(rules_map.keys())

        for r_id in task_rule_ids:
            rule_obj = rules_map.get(r_id)
            if not rule_obj:
                continue

            r_class = getattr(rule_obj, "rule_class", None) if not isinstance(rule_obj, dict) else rule_obj.get("rule_class")
            if isinstance(r_class, str):
                try:
                    r_class = RuleClass(r_class)
                except ValueError:
                    r_class = RuleClass.UNVERIFIED
            elif not isinstance(r_class, RuleClass):
                r_class = RuleClass.UNVERIFIED

            r_title = getattr(rule_obj, "title", None) if not isinstance(rule_obj, dict) else rule_obj.get("title")
            r_title = r_title or "Rule"
            source_id = getattr(rule_obj, "source_id", None) if not isinstance(rule_obj, dict) else rule_obj.get("source_id")
            source_id = source_id or "SRC-UNKNOWN"

            if r_class == RuleClass.VERIFIED_SOURCE:
                rule_severity = ConstraintSeverity.HARD
                # Satisfied if no hard conflicts on this placement
                rule_satisfied = len([c for c in conflicts if c.severity == ConstraintSeverity.HARD]) == 0
                rule_evidence_list.append(
                    RuleEvidence(
                        rule_id=r_id,
                        title=r_title,
                        rule_class=r_class,
                        source_id=source_id,
                        severity=rule_severity,
                        satisfied=rule_satisfied,
                        explanation=f"Verified railway rule {r_id} evaluated under hard constraint enforcement.",
                    )
                )
            elif r_class == RuleClass.ASSUMPTION:
                rule_severity = ConstraintSeverity.SOFT
                rule_evidence_list.append(
                    RuleEvidence(
                        rule_id=r_id,
                        title=r_title,
                        rule_class=r_class,
                        source_id=source_id,
                        severity=rule_severity,
                        satisfied=True,
                        explanation=f"Operational assumption {r_id} applied as soft preference guidance.",
                    )
                )
            elif r_class == RuleClass.DEMO_ONLY:
                rule_severity = ConstraintSeverity.DIAGNOSTIC_ONLY
                rule_evidence_list.append(
                    RuleEvidence(
                        rule_id=r_id,
                        title=r_title,
                        rule_class=r_class,
                        source_id=source_id,
                        severity=rule_severity,
                        satisfied=True,
                        explanation=f"Demo heuristic {r_id} recorded for diagnostic reporting.",
                    )
                )
            else:
                # UNVERIFIED rule - MUST NEVER BE HARD CONSTRAINT
                rule_severity = ConstraintSeverity.UNVERIFIED
                reason_codes_set.add(ReasonCode.UNVERIFIED_RULE)
                rule_evidence_list.append(
                    RuleEvidence(
                        rule_id=r_id,
                        title=r_title,
                        rule_class=r_class,
                        source_id=source_id,
                        severity=rule_severity,
                        satisfied=True,
                        explanation=f"Unverified rule {r_id} noted as unverified. Invariant enforced: never promotes to HARD constraint.",
                    )
                )

        # ---------------------------------------------------------------------
        # 11. COMPILE FINAL STRUCTURED COMPATIBILITY OUTCOME
        # ---------------------------------------------------------------------
        hard_conflicts = [c for c in conflicts if c.severity == ConstraintSeverity.HARD]
        soft_conflicts = [c for c in conflicts if c.severity == ConstraintSeverity.SOFT]

        is_compatible = len(hard_conflicts) == 0
        is_hard_feasible = len(hard_conflicts) == 0
        is_soft_admissible = len(soft_conflicts) == 0

        return CompatibilityResult(
            task_id=task_id,
            compatible=is_compatible,
            feasible_hard=is_hard_feasible,
            admissible_soft=is_soft_admissible,
            evaluated_interval=candidate_interval,
            possession_interval=possession_interval,
            reason_codes=list(reason_codes_set),
            conflicts=conflicts,
            affected_sections=list(affected_sections),
            affected_movements=list(affected_movements),
            affected_resources=list(affected_resources),
            rule_evidence=rule_evidence_list,
        )

    @staticmethod
    def evaluate_spatial_compatibility(
        occupant_1: Any,
        occupant_2: Any,
        tracks_map: Dict[str, Any],
    ) -> Any:
        """Evaluate deterministic spatial compatibility between two occupants.

        Part of Phase 16G-A: Rules classify compatibility. Optimization schedules.
        Preserves whole-section solver and validator behavior without modification.
        """
        from backend.app.domain.spatial_compatibility import (
            evaluate_spatial_compatibility as _eval_spatial,
            SpatialOccupant,
            TrackSpatialCompatibilityResult,
        )
        return _eval_spatial(occupant_1, occupant_2, tracks_map)

