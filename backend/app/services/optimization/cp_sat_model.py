"""CP-SAT Mathematical Model Builder for TrackMeld Maintenance Scheduling.

Translates the canonical PlanningSnapshot into a discrete Constraint Programming model
using Google OR-Tools CP-SAT with exact Phase 4 half-open interval semantics.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Tuple, Set, Optional
from collections import defaultdict
import math

from ortools.sat.python import cp_model

from backend.app.domain.planning_snapshot import PlanningSnapshot
from backend.app.domain.scheduling import PriorityScore
from backend.app.domain.temporal import TrainPass
from backend.app.services.optimization.solver_config import OptimizationConfig


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
        for task in self.snapshot.tasks:
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
        """Enforce section exclusivity and train movement collision prevention via NoOverlap."""
        # 1. Group train passes by section_id
        train_passes_by_sec = defaultdict(list)
        for tp in self.snapshot.train_passes:
            if tp.section_id:
                train_passes_by_sec[tp.section_id].append(tp)

        # 2. Group task possession intervals by section_id
        tasks_by_sec = defaultdict(list)
        for task_id, secs in self.task_affected_sections.items():
            for s in secs:
                tasks_by_sec[s].append(task_id)

        # 3. For each active section in scenario, enforce AddNoOverlap
        all_active_sections = set(train_passes_by_sec.keys()) | set(tasks_by_sec.keys())

        for sec_id in all_active_sections:
            section_intervals: List[cp_model.IntervalVar] = []

            # Add all task possession intervals affecting this section
            for task_id in tasks_by_sec.get(sec_id, []):
                section_intervals.append(self.pos_intervals[task_id])

            # Add all fixed train pass intervals on this section
            for tp in train_passes_by_sec.get(sec_id, []):
                tp_start = self.dt_to_min(tp.interval.start)
                tp_end = self.dt_to_min(tp.interval.end)
                dur = tp_end - tp_start

                # Clip to planning horizon
                if tp_end <= 0 or tp_start >= self.horizon_minutes:
                    continue

                clamped_start = max(0, tp_start)
                clamped_end = min(self.horizon_minutes, tp_end)
                clamped_dur = clamped_end - clamped_start

                if clamped_dur > 0:
                    tp_var = self.model.NewFixedSizeIntervalVar(
                        clamped_start, clamped_dur, f"train_{tp.pass_id}_{sec_id}"
                    )
                    section_intervals.append(tp_var)

            if len(section_intervals) > 1:
                self.model.AddNoOverlap(section_intervals)

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
        for r_id, task_ids in tasks_by_res.items():
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
        for dep in self.snapshot.dependencies:
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
        for task_id, presence in self.presence_vars.items():
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
