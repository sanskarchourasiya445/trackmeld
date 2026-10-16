"""Deterministic candidate placement generation for maintenance tasks.

Guarantees:
1. Event-boundary driven: identifies natural handover and clearance timepoints.
2. Respects task work window and planning horizon bounds.
3. Fully deterministic, bounded, and reproducible.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Any, Set, Optional

from backend.app.domain.planning_snapshot import PlanningSnapshot
from backend.app.domain.compatibility import ScheduledTaskPlacement


class CandidateGenerator:
    """Generates discrete candidate start times for task placement evaluation."""

    @classmethod
    def generate_candidate_starts(
        cls,
        task: Any,
        snapshot: PlanningSnapshot,
        existing_placements: List[ScheduledTaskPlacement],
        max_candidates: int = 50,
        step_minutes: int = 30,
    ) -> List[datetime]:
        """Generate ordered candidate start timestamps for a task."""
        task_id = task.get("task_id", "UNKNOWN") if isinstance(task, dict) else getattr(task, "task_id", "UNKNOWN")
        primary_sec = task.get("section_id") if isinstance(task, dict) else getattr(task, "section_id", None)
        est_duration = task.get("estimated_duration_minutes", 60) if isinstance(task, dict) else getattr(task, "estimated_duration_minutes", 60)
        buf_before = task.get("safety_buffer_before_minutes", 10) if isinstance(task, dict) else getattr(task, "safety_buffer_before_minutes", 10)
        buf_after = task.get("safety_buffer_after_minutes", 10) if isinstance(task, dict) else getattr(task, "safety_buffer_after_minutes", 10)

        # Parse task window
        w_start = getattr(task, "window_start", None) or task.get("window_start")
        w_end = getattr(task, "window_end", None) or task.get("window_end")
        if isinstance(w_start, str):
            w_start = datetime.fromisoformat(w_start)
        if isinstance(w_end, str):
            w_end = datetime.fromisoformat(w_end)
        if w_start.tzinfo is None:
            w_start = w_start.replace(tzinfo=timezone.utc)
        if w_end.tzinfo is None:
            w_end = w_end.replace(tzinfo=timezone.utc)

        # Lower and upper bound on candidate start
        earliest_start = max(w_start, snapshot.horizon.start)
        latest_start = min(
            w_end - timedelta(minutes=est_duration),
            snapshot.horizon.end - timedelta(minutes=est_duration)
        )

        if earliest_start > latest_start:
            return []

        # Secondary / affected sections
        additional_sec_ids = []
        if hasattr(task, "affected_sections"):
            additional_sec_ids = [s.section_id for s in task.affected_sections]
        elif "additional_sections" in task:
            additional_sec_ids = task["additional_sections"]
        affected_sections = {primary_sec} | set(additional_sec_ids)

        candidate_set: Set[datetime] = set()

        # ---------------------------------------------------------------------
        # Event 1: Window start
        # ---------------------------------------------------------------------
        candidate_set.add(earliest_start)

        # ---------------------------------------------------------------------
        # Event 2: Preferred start (if provided and within bounds)
        # ---------------------------------------------------------------------
        pref_start = getattr(task, "preferred_start", None) or task.get("preferred_start")
        if pref_start:
            if isinstance(pref_start, str):
                pref_start = datetime.fromisoformat(pref_start)
            if pref_start.tzinfo is None:
                pref_start = pref_start.replace(tzinfo=timezone.utc)
            if earliest_start <= pref_start <= latest_start:
                candidate_set.add(pref_start)

        # ---------------------------------------------------------------------
        # Event 3: Predecessor task completion times
        # ---------------------------------------------------------------------
        preds = snapshot.dependencies_by_successor.get(task_id, [])
        for dep in preds:
            pred_id = getattr(dep, "predecessor_task_id", None) or dep.get("predecessor_task_id")
            min_int = getattr(dep, "min_interval_minutes", 0) if hasattr(dep, "min_interval_minutes") else (dep.get("min_interval_minutes", 0) if isinstance(dep, dict) else 0)
            if min_int is None or min_int < 0:
                min_int = 0
            for p in existing_placements:
                if p.task_id == pred_id:
                    t_cand = p.interval.end + timedelta(minutes=min_int)
                    if earliest_start <= t_cand <= latest_start:
                        candidate_set.add(t_cand)

        # ---------------------------------------------------------------------
        # Event 4: Existing scheduled possession completions on same sections
        # ---------------------------------------------------------------------
        for existing in existing_placements:
            existing_secs = {existing.section_id} | set(existing.additional_section_ids)
            if affected_sections & existing_secs:
                # When previous possession clears, this task could start (minus setup buffer if applicable)
                # But task execution interval starts at possession_interval.end:
                t_cand = existing.possession_interval.end
                if earliest_start <= t_cand <= latest_start:
                    candidate_set.add(t_cand)

        # ---------------------------------------------------------------------
        # Event 5: Train pass exit times on affected sections
        # ---------------------------------------------------------------------
        for tp in snapshot.train_passes:
            if tp.section_id in affected_sections:
                t_cand = tp.interval.end
                if earliest_start <= t_cand <= latest_start:
                    candidate_set.add(t_cand)

        # ---------------------------------------------------------------------
        # Event 6: Resource availability window starts
        # ---------------------------------------------------------------------
        reqs = getattr(task, "resource_requirements", [])
        if not reqs and "resource_requirements" in task:
            reqs = task["resource_requirements"]
        req_res_ids = {getattr(r, "resource_id", None) or r.get("resource_id") for r in reqs}

        for avail in snapshot.resource_availabilities:
            a_res_id = getattr(avail, "resource_id", None) or avail.get("resource_id")
            if a_res_id in req_res_ids:
                a_from = getattr(avail, "available_from", None) or avail.get("available_from")
                if isinstance(a_from, str):
                    a_from = datetime.fromisoformat(a_from)
                if a_from.tzinfo is None:
                    a_from = a_from.replace(tzinfo=timezone.utc)
                if earliest_start <= a_from <= latest_start:
                    candidate_set.add(a_from)

        # ---------------------------------------------------------------------
        # Event 7: Regular periodic steps (to provide coverage between event gaps)
        # ---------------------------------------------------------------------
        curr = earliest_start
        while curr <= latest_start and len(candidate_set) < max_candidates * 2:
            candidate_set.add(curr)
            curr += timedelta(minutes=step_minutes)

        # Filter strictly within [earliest_start, latest_start]
        valid_candidates = [
            t for t in candidate_set
            if earliest_start <= t <= latest_start
        ]

        # Sort chronologically ascending (Earliest-Feasible Candidate Policy)
        sorted_candidates = sorted(valid_candidates)

        return sorted_candidates[:max_candidates]
