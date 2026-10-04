"""CP-SAT Mathematical Model Builder for TrackMeld Maintenance Scheduling.

Translates the canonical PlanningSnapshot into a discrete Constraint Programming model
using Google OR-Tools CP-SAT with exact Phase 4 half-open interval semantics.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Tuple, Set, Optional
from collections import defaultdict
from dataclasses import dataclass
import math

from ortools.sat.python import cp_model

from backend.app.domain.planning_snapshot import PlanningSnapshot
from backend.app.domain.scheduling import PriorityScore
from backend.app.domain.temporal import TrainPass
from backend.app.services.optimization.solver_config import OptimizationConfig


@dataclass(frozen=True)
class _SectionOccupant:
    """Internal normalized representation of a section occupant for CP-SAT constraint generation."""
    occupant_id: str
    occupant_type: str  # "TASK", "TRAIN_TRAVERSAL", "TRAIN_PASS"
    interval_var: cp_model.IntervalVar
    track_id: Optional[str]
    adjacent_track_impact: Optional[Any]
    direction: Optional[str]


class CPSATModelBuilder:
    """Builds the mathematical constraint programming model for CP-SAT."""

    def __init__(
        self,
        snapshot: PlanningSnapshot,
        scores_map: Dict[str, PriorityScore],
        config: OptimizationConfig,
    ) -> None:
        self.snapshot = snapshot
        self.scores_map = scores_map
        self.config = config

        self.model = cp_model.CpModel()
        self.horizon_start = snapshot.horizon.start
        self.horizon_end = snapshot.horizon.end
        self.horizon_minutes = int((self.horizon_end - self.horizon_start).total_seconds() // 60)

        # Variables dictionaries
        self.presence_vars: Dict[str, cp_model.BoolVar] = {}
        self.start_vars: Dict[str, cp_model.IntVar] = {}
        self.end_vars: Dict[str, cp_model.IntVar] = {}
        self.task_intervals: Dict[str, cp_model.IntervalVar] = {}

        self.pos_start_vars: Dict[str, cp_model.IntVar] = {}
        self.pos_end_vars: Dict[str, cp_model.IntVar] = {}
        self.pos_intervals: Dict[str, cp_model.IntervalVar] = {}

        # Lookups
        self.task_durations: Dict[str, int] = {}
        self.task_affected_sections: Dict[str, List[str]] = {}
        self.task_resources: Dict[str, List[str]] = {}

    def dt_to_min(self, dt: datetime) -> int:
        """Convert UTC datetime to integer minute offset from planning horizon start."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta_sec = (dt - self.horizon_start).total_seconds()
        return int(delta_sec // 60)

    def min_to_dt(self, minutes: int) -> datetime:
        """Convert integer minute offset back to UTC datetime."""
        return self.horizon_start + timedelta(minutes=minutes)

    def build(self) -> cp_model.CpModel:
        """Assemble all decision variables, operational constraints, and priority objective."""
        self._create_task_variables()
        self._add_section_and_train_constraints()
        self._add_resource_constraints()
        self._add_dependency_constraints()
        self._add_objective()
        return self.model

    def _create_task_variables(self) -> None:
        """Create optional interval variables and possession envelopes for each task."""
        sorted_tasks = sorted(
            self.snapshot.tasks,
            key=lambda t: t.get("task_id", "") if isinstance(t, dict) else getattr(t, "task_id", "")
        )
        for task in sorted_tasks:
            task_id = task.get("task_id", "UNKNOWN") if isinstance(task, dict) else getattr(task, "task_id", "UNKNOWN")
            primary_sec = task.get("section_id") if isinstance(task, dict) else getattr(task, "section_id", None)
            is_mandatory = task.get("mandatory", False) if isinstance(task, dict) else getattr(task, "mandatory", False)

            duration = int(task.get("estimated_duration_minutes", 60) if isinstance(task, dict) else getattr(task, "estimated_duration_minutes", 60))
            buf_before = int(task.get("safety_buffer_before_minutes", 10) if isinstance(task, dict) else getattr(task, "safety_buffer_before_minutes", 10))
            buf_after = int(task.get("safety_buffer_after_minutes", 10) if isinstance(task, dict) else getattr(task, "safety_buffer_after_minutes", 10))
            pos_duration = duration + buf_before + buf_after

            self.task_durations[task_id] = duration

            # Parse execution window
            w_start_raw = task.get("window_start") if isinstance(task, dict) else getattr(task, "window_start")
            w_end_raw = task.get("window_end") if isinstance(task, dict) else getattr(task, "window_end")
            if isinstance(w_start_raw, str):
                w_start_dt = datetime.fromisoformat(w_start_raw)
            else:
                w_start_dt = w_start_raw
            if isinstance(w_end_raw, str):
                w_end_dt = datetime.fromisoformat(w_end_raw)
            else:
                w_end_dt = w_end_raw

            w_start_min = max(0, self.dt_to_min(w_start_dt))
            w_end_min = min(self.horizon_minutes, self.dt_to_min(w_end_dt))

            # Additional / affected sections
            additional_sec_ids = []
            if isinstance(task, dict) and "additional_sections" in task:
                additional_sec_ids = task["additional_sections"]
            elif hasattr(task, "affected_sections"):
                additional_sec_ids = [s.section_id for s in task.affected_sections]
            all_secs = [primary_sec] + [s for s in additional_sec_ids if s and s != primary_sec]
            self.task_affected_sections[task_id] = all_secs

            # Required resources
            res_ids = []
            if isinstance(task, dict) and "required_resource_ids" in task:
                res_ids.extend(task["required_resource_ids"])
            reqs = task.get("resource_requirements", []) if isinstance(task, dict) else getattr(task, "resource_requirements", [])
            for r in reqs:
                rid = r.get("resource_id") if isinstance(r, dict) else getattr(r, "resource_id", None)
                if rid and rid not in res_ids:
                    res_ids.append(rid)
            self.task_resources[task_id] = res_ids

            # Presence variable
            presence = self.model.NewBoolVar(f"presence_{task_id}")
            self.presence_vars[task_id] = presence

            # Mandatory constraint
            if is_mandatory:
                self.model.Add(presence == 1)

            # Phase 19: Physical track validation
            raw_trk_id = task.get("track_id") if isinstance(task, dict) else getattr(task, "track_id", None)
            if raw_trk_id and len(self.snapshot.tracks_map) > 0:
                trk_obj = self.snapshot.tracks_map.get(raw_trk_id)
                if trk_obj is None:
                    # Infeasible: Unknown track assigned when track database is active
                    self.model.Add(presence == 0)
                else:
                    trk_sec = getattr(trk_obj, "section_id", None) if not isinstance(trk_obj, dict) else trk_obj.get("section_id")
                    if trk_sec != primary_sec:
                        # Infeasible: Track does not belong to task primary section
                        self.model.Add(presence == 0)

                    task_dir = task.get("direction") if isinstance(task, dict) else getattr(task, "direction", None)
                    trk_dir = getattr(trk_obj, "direction", None) if not isinstance(trk_obj, dict) else trk_obj.get("direction")
                    if task_dir in ("UP", "DOWN") and trk_dir in ("UP", "DOWN") and task_dir != trk_dir:
                        # Infeasible: Direction conflict with physical track
                        self.model.Add(presence == 0)

            # Check if task cannot possibly fit within allowed window
            if w_start_min + duration > w_end_min:
                # Impossible window
                self.model.Add(presence == 0)
                # Create dummy interval
                start_var = self.model.NewIntVar(0, self.horizon_minutes, f"start_{task_id}")
                end_var = self.model.NewIntVar(0, self.horizon_minutes, f"end_{task_id}")
                self.model.Add(end_var == start_var + duration)
                task_interval = self.model.NewOptionalIntervalVar(start_var, duration, end_var, presence, f"interval_{task_id}")

                pos_start_var = self.model.NewIntVar(-buf_before, self.horizon_minutes, f"pos_start_{task_id}")
                pos_end_var = self.model.NewIntVar(0, self.horizon_minutes + buf_after, f"pos_end_{task_id}")
                self.model.Add(pos_start_var == start_var - buf_before)
                self.model.Add(pos_end_var == end_var + buf_after)
                pos_interval = self.model.NewOptionalIntervalVar(pos_start_var, pos_duration, pos_end_var, presence, f"pos_interval_{task_id}")

                self.start_vars[task_id] = start_var
                self.end_vars[task_id] = end_var
                self.task_intervals[task_id] = task_interval
                self.pos_start_vars[task_id] = pos_start_var
                self.pos_end_vars[task_id] = pos_end_var
                self.pos_intervals[task_id] = pos_interval
                continue

            # Task start and end bounded strictly by window
            start_var = self.model.NewIntVar(w_start_min, w_end_min - duration, f"start_{task_id}")
            end_var = self.model.NewIntVar(w_start_min + duration, w_end_min, f"end_{task_id}")
            self.model.Add(end_var == start_var + duration)
            task_interval = self.model.NewOptionalIntervalVar(start_var, duration, end_var, presence, f"interval_{task_id}")

            # Possession envelope: [start - buf_before, end + buf_after)
            pos_start_var = self.model.NewIntVar(w_start_min - buf_before, w_end_min - duration - buf_before, f"pos_start_{task_id}")
            pos_end_var = self.model.NewIntVar(w_start_min + duration + buf_after, w_end_min + buf_after, f"pos_end_{task_id}")
            self.model.Add(pos_start_var == start_var - buf_before)
            self.model.Add(pos_end_var == end_var + buf_after)
            pos_interval = self.model.NewOptionalIntervalVar(pos_start_var, pos_duration, pos_end_var, presence, f"pos_interval_{task_id}")

            # Power block check
            req_power = task.get("requires_power_block", False) if isinstance(task, dict) else getattr(task, "requires_power_block", False)
            if req_power:
                for sec_id in all_secs:
                    sec_obj = self.snapshot.sections_map.get(sec_id)
                    is_electrified = (
                        sec_obj.get("electrified", True)
                        if isinstance(sec_obj, dict)
                        else getattr(sec_obj, "electrified", True)
                    )
                    if not is_electrified:
                        self.model.Add(presence == 0)

            self.start_vars[task_id] = start_var
            self.end_vars[task_id] = end_var
            self.task_intervals[task_id] = task_interval
            self.pos_start_vars[task_id] = pos_start_var
            self.pos_end_vars[task_id] = pos_end_var
            self.pos_intervals[task_id] = pos_interval

    def _add_section_and_train_constraints(self) -> None:
        """Enforce section/track exclusivity and train movement collision prevention via NoOverlap."""
        # 1. Group train occupants by section_id
        # Train traversals where they provide resolved physical track occupancy or explicit route resolution diagnostics
        traversals_by_sec = defaultdict(list)
        for trv in getattr(self.snapshot, "train_traversals", []):
            sec = getattr(trv, "section_id", None) or (trv.get("section_id") if isinstance(trv, dict) else None)
            if not sec:
                continue
            res_status = getattr(trv, "resolution_status", None) or (trv.get("resolution_status") if isinstance(trv, dict) else None)
            res_status_val = res_status.value if hasattr(res_status, "value") else str(res_status)
            trv_trk = getattr(trv, "traversal_track_id", None) or (trv.get("traversal_track_id") if isinstance(trv, dict) else None)

            # Include if resolved physical track OR if explicitly unresolved/ambiguous
            if res_status_val in ("RESOLVED", "EXPANDED_ROUTE", "DIRECT_SECTION") and trv_trk:
                traversals_by_sec[sec].append(trv)
            elif res_status_val in ("AMBIGUOUS_ROUTE", "UNRESOLVED") and trv_trk is None:
                traversals_by_sec[sec].append(trv)

        # Train passes with section_id (preserves existing TrainPass section-level baseline)
        train_passes_by_sec = defaultdict(list)
        for tp in self.snapshot.train_passes:
            sec = getattr(tp, "section_id", None) or (tp.get("section_id") if isinstance(tp, dict) else None)
            if sec:
                train_passes_by_sec[sec].append(tp)

        # 2. Group task possession intervals by section_id
        tasks_by_sec = defaultdict(list)
        for task_id, secs in self.task_affected_sections.items():
            for s in secs:
                tasks_by_sec[s].append(task_id)

        all_active_sections = sorted(
            set(train_passes_by_sec.keys()) | set(traversals_by_sec.keys()) | set(tasks_by_sec.keys())
        )

        solver_mode = getattr(self.config, "solver_mode", "TRACK_AWARE_CONSERVATIVE")
        tracks_map = self.snapshot.tracks_map

        for sec_id in all_active_sections:
            occupants: List[_SectionOccupant] = []

            # A. Add tasks affecting this section
            for task_id in sorted(tasks_by_sec.get(sec_id, [])):
                t_obj = self.snapshot.tasks_map.get(task_id, {})
                primary_sec = t_obj.get("section_id") if isinstance(t_obj, dict) else getattr(t_obj, "section_id", None)
                raw_trk_id = t_obj.get("track_id") if isinstance(t_obj, dict) else getattr(t_obj, "track_id", None)
                adj_impact = t_obj.get("adjacent_track_impact") if isinstance(t_obj, dict) else getattr(t_obj, "adjacent_track_impact", None)
                t_dir = t_obj.get("direction") if isinstance(t_obj, dict) else getattr(t_obj, "direction", None)

                # Validate track assignment for this section
                resolved_trk = None
                if raw_trk_id and raw_trk_id in tracks_map:
                    trk_obj = tracks_map[raw_trk_id]
                    trk_sec = getattr(trk_obj, "section_id", None) if not isinstance(trk_obj, dict) else trk_obj.get("section_id")
                    if trk_sec == sec_id:
                        resolved_trk = raw_trk_id

                occupants.append(
                    _SectionOccupant(
                        occupant_id=task_id,
                        occupant_type="TASK",
                        interval_var=self.pos_intervals[task_id],
                        track_id=resolved_trk,
                        adjacent_track_impact=adj_impact,
                        direction=t_dir,
                    )
                )

            # B. Add trains affecting this section
            sec_traversals = traversals_by_sec.get(sec_id, [])
            covered_pass_ids = set()

            if sec_traversals:
                for trv in sorted(sec_traversals, key=lambda x: getattr(x, "traversal_id", None) or (x.get("traversal_id") if isinstance(x, dict) else "")):
                    trv_id = getattr(trv, "traversal_id", None) or (trv.get("traversal_id") if isinstance(trv, dict) else "")
                    source_pass_id = getattr(trv, "source_pass_id", None) or (trv.get("source_pass_id") if isinstance(trv, dict) else None)
                    if source_pass_id:
                        covered_pass_ids.add(source_pass_id)

                    interval = getattr(trv, "interval", None) or (trv.get("interval") if isinstance(trv, dict) else None)
                    if not interval:
                        continue

                    start_min = self.dt_to_min(interval.start)
                    end_min = self.dt_to_min(interval.end)
                    if end_min <= 0 or start_min >= self.horizon_minutes:
                        continue
                    clamped_start = max(0, start_min)
                    clamped_end = min(self.horizon_minutes, end_min)
                    clamped_dur = clamped_end - clamped_start
                    if clamped_dur <= 0:
                        continue

                    # Track resolution
                    res_status = getattr(trv, "resolution_status", None) or (trv.get("resolution_status") if isinstance(trv, dict) else None)
                    res_status_val = res_status.value if hasattr(res_status, "value") else str(res_status)
                    trv_trk = getattr(trv, "traversal_track_id", None) or (trv.get("traversal_track_id") if isinstance(trv, dict) else None)

                    resolved_trk = None
                    if res_status_val in ("RESOLVED", "EXPANDED_ROUTE", "DIRECT_SECTION") and trv_trk and trv_trk in tracks_map:
                        trk_obj = tracks_map[trv_trk]
                        trk_sec = getattr(trk_obj, "section_id", None) if not isinstance(trk_obj, dict) else trk_obj.get("section_id")
                        if trk_sec == sec_id:
                            resolved_trk = trv_trk

                    trv_var = self.model.NewFixedSizeIntervalVar(
                        clamped_start, clamped_dur, f"train_trv_{trv_id}_{sec_id}"
                    )
                    occupants.append(
                        _SectionOccupant(
                            occupant_id=trv_id,
                            occupant_type="TRAIN_TRAVERSAL",
                            interval_var=trv_var,
                            track_id=resolved_trk,
                            adjacent_track_impact=None,
                            direction=None,
                        )
                    )

            # Fallback/uncovered train passes
            for tp in sorted(train_passes_by_sec.get(sec_id, []), key=lambda x: getattr(x, "pass_id", None) or (x.get("pass_id") if isinstance(x, dict) else "")):
                pass_id = getattr(tp, "pass_id", None) or (tp.get("pass_id") if isinstance(tp, dict) else "")
                if pass_id in covered_pass_ids:
                    continue

                interval = getattr(tp, "interval", None) or (tp.get("interval") if isinstance(tp, dict) else None)
                if not interval:
                    continue

                start_min = self.dt_to_min(interval.start)
                end_min = self.dt_to_min(interval.end)
                if end_min <= 0 or start_min >= self.horizon_minutes:
                    continue
                clamped_start = max(0, start_min)
                clamped_end = min(self.horizon_minutes, end_min)
                clamped_dur = clamped_end - clamped_start
                if clamped_dur <= 0:
                    continue

                tp_trk = getattr(tp, "track_id", None) or (tp.get("track_id") if isinstance(tp, dict) else None)
                resolved_trk = None
                if tp_trk and tp_trk in tracks_map:
                    trk_obj = tracks_map[tp_trk]
                    trk_sec = getattr(trk_obj, "section_id", None) if not isinstance(trk_obj, dict) else trk_obj.get("section_id")
                    if trk_sec == sec_id:
                        resolved_trk = tp_trk

                tp_var = self.model.NewFixedSizeIntervalVar(
                    clamped_start, clamped_dur, f"train_{pass_id}_{sec_id}"
                )
                occupants.append(
                    _SectionOccupant(
                        occupant_id=pass_id,
                        occupant_type="TRAIN_PASS",
                        interval_var=tp_var,
                        track_id=resolved_trk,
                        adjacent_track_impact=None,
                        direction=None,
                    )
                )

            if len(occupants) <= 1:
                continue

            # Deterministic sorting of occupants
            occupants.sort(key=lambda o: (o.occupant_type, o.occupant_id))

            if solver_mode == "WHOLE_SECTION":
                # Strict whole-section model: single NoOverlap across all occupants in section
                self.model.AddNoOverlap([o.interval_var for o in occupants])
            else:
                # TRACK_AWARE_CONSERVATIVE
                # 1. Group occupants by physical track and enforce per-track NoOverlap
                track_occupants = defaultdict(list)
                for occ in occupants:
                    if occ.track_id:
                        track_occupants[occ.track_id].append(occ)

                for trk_id in sorted(track_occupants.keys()):
                    occ_list = track_occupants[trk_id]
                    if len(occ_list) > 1:
                        self.model.AddNoOverlap([o.interval_var for o in occ_list])

                # 2. Check if all occupants in section lack track resolution (Case C)
                all_unresolved = all(occ.track_id is None for occ in occupants)
                if all_unresolved:
                    self.model.AddNoOverlap([o.interval_var for o in occupants])
                else:
                    # 3. For every pair of occupants across different tracks or involving an unresolved occupant:
                    for i in range(len(occupants)):
                        for j in range(i + 1, len(occupants)):
                            occ1 = occupants[i]
                            occ2 = occupants[j]

                            # If both are on the same track, already covered by per-track NoOverlap
                            if occ1.track_id and occ2.track_id and occ1.track_id == occ2.track_id:
                                continue

                            if not self._are_occupants_provably_compatible(occ1, occ2, sec_id, tracks_map):
                                self.model.AddNoOverlap([occ1.interval_var, occ2.interval_var])

    @staticmethod
    def _are_occupants_provably_compatible(
        occ1: "_SectionOccupant",
        occ2: "_SectionOccupant",
        sec_id: str,
        tracks_map: Dict[str, Any],
    ) -> bool:
        """Evaluate if two occupants in the same section are provably compatible to coexist.

        Conservative principle: If spatial information is incomplete, missing, or indicates conflict,
        returns False (triggering mutual exclusion / whole-section fallback).
        """
        # 1. Both occupants must have resolved track assignments
        if not occ1.track_id or not occ2.track_id:
            return False

        # 2. Both tracks must exist in snapshot and belong to sec_id
        trk1 = tracks_map.get(occ1.track_id)
        trk2 = tracks_map.get(occ2.track_id)
        if not trk1 or not trk2:
            return False

        sec1 = getattr(trk1, "section_id", None) if not isinstance(trk1, dict) else trk1.get("section_id")
        sec2 = getattr(trk2, "section_id", None) if not isinstance(trk2, dict) else trk2.get("section_id")
        if sec1 != sec_id or sec2 != sec_id:
            return False

        # 3. Must be distinct physical tracks
        if occ1.track_id == occ2.track_id:
            return False

        # 4. Check track direction compatibility
        dir1 = getattr(trk1, "direction", None) if not isinstance(trk1, dict) else trk1.get("direction")
        dir2 = getattr(trk2, "direction", None) if not isinstance(trk2, dict) else trk2.get("direction")
        if occ1.direction in ("UP", "DOWN") and dir1 in ("UP", "DOWN") and occ1.direction != dir1:
            return False
        if occ2.direction in ("UP", "DOWN") and dir2 in ("UP", "DOWN") and occ2.direction != dir2:
            return False

        # 5. Adjacency metadata MUST be present on both tracks
        adj1 = getattr(trk1, "adjacent_track_ids", None) if not isinstance(trk1, dict) else trk1.get("adjacent_track_ids")
        adj2 = getattr(trk2, "adjacent_track_ids", None) if not isinstance(trk2, dict) else trk2.get("adjacent_track_ids")
        if adj1 is None or adj2 is None:
            # Missing adjacency metadata -> cannot prove independence -> fallback to exclusion
            return False

        is_adjacent = (occ2.track_id in adj1) or (occ1.track_id in adj2)

        # 6. If not adjacent, distinct physical tracks are compatible
        if not is_adjacent:
            return True

        # 7. If adjacent, inspect task adjacent_track_impact
        # Any task requiring FULL_TRAFFIC_BLOCK or ADJACENT_TRACK_FOULING prevents coexistence
        for occ in (occ1, occ2):
            if occ.occupant_type == "TASK":
                impact = occ.adjacent_track_impact
                if impact is None:
                    # Unspecified adjacent impact on adjacent track -> cannot prove safe
                    return False
                impact_val = impact.value if hasattr(impact, "value") else str(impact)
                if impact_val in ("FULL_TRAFFIC_BLOCK", "ADJACENT_TRACK_FOULING"):
                    return False

        # CAUTION_ORDER / SPEED_RESTRICTION or NONE on adjacent track -> permitted coexistence in solver
        return True

    def _add_resource_constraints(self) -> None:
        """Enforce resource exclusivity and active availability window enclosure."""
        # 1. Group tasks by required resource
        tasks_by_res = defaultdict(list)
        for task_id, res_ids in self.task_resources.items():
            for r in res_ids:
                tasks_by_res[r].append(task_id)

        # 2. Parse resource availability intervals
        avail_by_res = defaultdict(list)
        for a in self.snapshot.resource_availabilities:
            r_id = a.get("resource_id") if isinstance(a, dict) else getattr(a, "resource_id", None)
            status = a.get("availability_status", "AVAILABLE") if isinstance(a, dict) else getattr(a, "availability_status", "AVAILABLE")
            if hasattr(status, "value"):
                status = status.value

            if status == "AVAILABLE":
                a_from = a.get("available_from") if isinstance(a, dict) else getattr(a, "available_from")
                a_until = a.get("available_until") if isinstance(a, dict) else getattr(a, "available_until")
                if isinstance(a_from, str):
                    a_from_dt = datetime.fromisoformat(a_from)
                else:
                    a_from_dt = a_from
                if isinstance(a_until, str):
                    a_until_dt = datetime.fromisoformat(a_until)
                else:
                    a_until_dt = a_until

                start_min = max(0, self.dt_to_min(a_from_dt))
                end_min = min(self.horizon_minutes, self.dt_to_min(a_until_dt))
                if end_min > start_min:
                    avail_by_res[r_id].append((start_min, end_min))

        # 3. For each resource, add exclusivity and availability constraints
        for r_id in sorted(tasks_by_res.keys()):
            task_ids = sorted(tasks_by_res[r_id])
            res_intervals: List[cp_model.IntervalVar] = [self.task_intervals[tid] for tid in task_ids]

            # Compute complementary unavailable intervals only if availability records are defined
            if r_id in avail_by_res:
                windows = sorted(avail_by_res[r_id])
                unavail_intervals: List[Tuple[int, int]] = []

                curr = 0
                for w_start, w_end in windows:
                    if w_start > curr:
                        unavail_intervals.append((curr, w_start))
                    curr = max(curr, w_end)
                if curr < self.horizon_minutes:
                    unavail_intervals.append((curr, self.horizon_minutes))

                for u_start, u_end in unavail_intervals:
                    u_dur = u_end - u_start
                    if u_dur > 0:
                        unavail_var = self.model.NewFixedSizeIntervalVar(
                            u_start, u_dur, f"unavail_{r_id}_{u_start}"
                        )
                        res_intervals.append(unavail_var)

            if len(res_intervals) > 1:
                self.model.AddNoOverlap(res_intervals)

    def _add_dependency_constraints(self) -> None:
        """Enforce Finish-to-Start precedence relationships between tasks."""
        sorted_deps = sorted(
            self.snapshot.dependencies,
            key=lambda d: (
                d.get("predecessor_task_id", "") if isinstance(d, dict) else getattr(d, "predecessor_task_id", ""),
                d.get("successor_task_id", "") if isinstance(d, dict) else getattr(d, "successor_task_id", ""),
            )
        )
        for dep in sorted_deps:
            pred_id = dep.get("predecessor_task_id") if isinstance(dep, dict) else getattr(dep, "predecessor_task_id")
            succ_id = dep.get("successor_task_id") if isinstance(dep, dict) else getattr(dep, "successor_task_id")
            min_interval = dep.get("min_interval_minutes", 0) if isinstance(dep, dict) else getattr(dep, "min_interval_minutes", 0)

            if pred_id in self.presence_vars and succ_id in self.presence_vars:
                # Predecessor presence condition: succ can only be present if pred is present
                self.model.Add(self.presence_vars[succ_id] <= self.presence_vars[pred_id])

                # Finish-to-Start: succ_start >= pred_end + min_interval
                self.model.Add(
                    self.start_vars[succ_id] >= self.end_vars[pred_id] + min_interval
                ).OnlyEnforceIf([self.presence_vars[succ_id], self.presence_vars[pred_id]])

    def _add_objective(self) -> None:
        """Formulate transparent objective: maximize total scaled priority score with duration tie-breaker."""
        objective_terms = []
        for task_id in sorted(self.presence_vars.keys()):
            presence = self.presence_vars[task_id]
            score_obj = self.scores_map.get(task_id)
            total_score = score_obj.total_score if score_obj else 1.0

            # Scale priority score to integer coefficient
            scaled_prio = int(round(total_score * self.config.objective_scale))

            # Primary term: scaled priority score * 1000
            # Secondary term: - duration * duration_penalty_weight
            dur = self.task_durations.get(task_id, 60)
            net_coeff = (scaled_prio * 1000) - (dur * self.config.duration_penalty_weight)

            objective_terms.append(net_coeff * presence)

        self.model.Maximize(sum(objective_terms))
