"""Controlled Relaxation Analysis for TrackMeld Schedule Diagnostics.

CRITICAL SAFETY INVARIANT:
This module performs hypothetical diagnostic analysis ONLY.
It NEVER alters the production schedule, NEVER recommends violating hard safety rules,
and explicitly marks every candidate placement as hypothetical and NOT approvable.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple

from backend.app.domain.temporal import TimeInterval
from backend.app.domain.scheduling import ScheduleResult
from backend.app.domain.planning_snapshot import PlanningSnapshot
from backend.app.services.validation.models import (
    RelaxationScenarioType,
    RelaxationFinding,
)


class RelaxationAnalyzer:
    """Evaluates controlled hypothetical relaxation scenarios for unplaced maintenance tasks."""

    def __init__(
        self,
        snapshot: PlanningSnapshot,
        schedule: ScheduleResult,
        max_candidate_evaluations: int = 40,
        sample_step_minutes: int = 30,
    ) -> None:
        self.snapshot = snapshot
        self.schedule = schedule
        self.max_candidates = max_candidate_evaluations
        self.step_minutes = sample_step_minutes

    def analyze_task(self, task_id: str) -> List[RelaxationFinding]:
        """Analyze 5 bounded relaxation scenarios for an unscheduled task."""
        orig = self.snapshot.tasks_map.get(task_id)
        if not orig:
            return []

        findings: List[RelaxationFinding] = []

        findings.append(self._relax_train_conflicts(task_id, orig))
        findings.append(self._relax_section_occupancy(task_id, orig))
        findings.append(self._relax_resource_availability(task_id, orig))
        findings.append(self._relax_dependencies(task_id, orig))
        findings.append(self._relax_window_widening(task_id, orig))

        return findings

    def _get_task_params(self, task: Any) -> Tuple:
        duration = task.get("estimated_duration_minutes", 60) if isinstance(task, dict) else getattr(task, "estimated_duration_minutes", 60)
        buf_before = task.get("safety_buffer_before_minutes", 10) if isinstance(task, dict) else getattr(task, "safety_buffer_before_minutes", 10)
        buf_after = task.get("safety_buffer_after_minutes", 10) if isinstance(task, dict) else getattr(task, "safety_buffer_after_minutes", 10)
        sec_id = task.get("section_id") if isinstance(task, dict) else getattr(task, "section_id", None)
        add_secs = task.get("additional_sections", []) if isinstance(task, dict) else [s.section_id for s in getattr(task, "affected_sections", [])]
        all_secs = {sec_id} | set(add_secs)

        w_start_raw = task.get("window_start") if isinstance(task, dict) else getattr(task, "window_start")
        w_end_raw = task.get("window_end") if isinstance(task, dict) else getattr(task, "window_end")

        def parse_dt(v):
            if isinstance(v, str):
                dt = datetime.fromisoformat(v)
            elif isinstance(v, datetime):
                dt = v
            else:
                dt = self.snapshot.horizon.start
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

        w_start = parse_dt(w_start_raw)
        w_end = parse_dt(w_end_raw)

        return duration, buf_before, buf_after, all_secs, w_start, w_end

    def _relax_train_conflicts(self, task_id: str, task: Any) -> RelaxationFinding:
        """Evaluate placement assuming train path clearances are hypothetically waived."""
        duration, buf_before, buf_after, all_secs, w_start, w_end = self._get_task_params(task)

        # Check existing scheduled task placements on these sections
        scheduled_on_secs = [
            st for st in self.schedule.scheduled_tasks
            if any(s in all_secs for s in st.affected_sections)
        ]

        # Scan candidate starts within window
        curr = w_start
        found_candidate = None
        blocking_trains = []

        while curr + timedelta(minutes=duration) <= w_end and curr <= w_start + timedelta(hours=24):
            t_cand_start = curr
            t_cand_end = curr + timedelta(minutes=duration)
            p_cand_start = t_cand_start - timedelta(minutes=buf_before)
            p_cand_end = t_cand_end + timedelta(minutes=buf_after)
            cand_pos = TimeInterval(start=p_cand_start, end=p_cand_end)

            # Check if conflicting with any scheduled maintenance tasks
            maint_conflict = any(cand_pos.overlaps(st.possession_interval) for st in scheduled_on_secs)

            if not maint_conflict:
                # Find colliding train movements that are waived
                colliding = [
                    tp.train_number for tp in self.snapshot.train_passes
                    if tp.section_id in all_secs and cand_pos.overlaps(tp.interval)
                ]
                if colliding:
                    found_candidate = (t_cand_start, t_cand_end)
                    blocking_trains = colliding
                    break

            curr += timedelta(minutes=self.step_minutes)

        if found_candidate:
            return RelaxationFinding(
                scenario_type=RelaxationScenarioType.IGNORE_TRAIN_CONFLICTS,
                description="Hypothetically waive train movement path collisions.",
                feasible=True,
                candidate_start=found_candidate[0],
                candidate_end=found_candidate[1],
                blocking_entities=blocking_trains,
                relaxation_magnitude=f"Bypasses clearance against trains: {', '.join(blocking_trains[:3])}",
                hypothetical=True,
                approvable=False,
                explanation=f"Task can physically execute at {found_candidate[0].isoformat()} if scheduled train passages {blocking_trains[:2]} are canceled or rerouted.",
            )
        else:
            return RelaxationFinding(
                scenario_type=RelaxationScenarioType.IGNORE_TRAIN_CONFLICTS,
                description="Hypothetically waive train movement path collisions.",
                feasible=False,
                hypothetical=True,
                approvable=False,
                explanation="Waiving train movements alone does not create a feasible placement (blocked by track occupancy or windows).",
            )

    def _relax_section_occupancy(self, task_id: str, task: Any) -> RelaxationFinding:
        """Evaluate placement assuming track section exclusivity against other tasks is waived."""
        duration, buf_before, buf_after, all_secs, w_start, w_end = self._get_task_params(task)

        # Scan candidate starts within window
        curr = w_start
        found_candidate = None
        blocking_tasks = []

        while curr + timedelta(minutes=duration) <= w_end and curr <= w_start + timedelta(hours=24):
            t_cand_start = curr
            t_cand_end = curr + timedelta(minutes=duration)
            p_cand_start = t_cand_start - timedelta(minutes=buf_before)
            p_cand_end = t_cand_end + timedelta(minutes=buf_after)
            cand_pos = TimeInterval(start=p_cand_start, end=p_cand_end)

            # Train conflict check (trains NOT waived here)
            train_conflict = any(
                tp.section_id in all_secs and cand_pos.overlaps(tp.interval)
                for tp in self.snapshot.train_passes
            )

            if not train_conflict:
                colliding_tasks = [
                    st.task_id for st in self.schedule.scheduled_tasks
                    if any(s in all_secs for s in st.affected_sections) and cand_pos.overlaps(st.possession_interval)
                ]
                if colliding_tasks:
                    found_candidate = (t_cand_start, t_cand_end)
                    blocking_tasks = colliding_tasks
                    break

            curr += timedelta(minutes=self.step_minutes)

        if found_candidate:
            return RelaxationFinding(
                scenario_type=RelaxationScenarioType.IGNORE_SECTION_OCCUPANCY,
                description="Hypothetically co-occupy track section with concurrent maintenance tasks.",
                feasible=True,
                candidate_start=found_candidate[0],
                candidate_end=found_candidate[1],
                blocking_entities=blocking_tasks,
                relaxation_magnitude=f"Co-occupies track with tasks: {', '.join(blocking_tasks)}",
                hypothetical=True,
                approvable=False,
                explanation=f"Task could execute at {found_candidate[0].isoformat()} if bundled concurrently on the same possession block with tasks {blocking_tasks}.",
            )
        else:
            return RelaxationFinding(
                scenario_type=RelaxationScenarioType.IGNORE_SECTION_OCCUPANCY,
                description="Hypothetically co-occupy track section with concurrent maintenance tasks.",
                feasible=False,
                hypothetical=True,
                approvable=False,
                explanation="Co-occupancy with other maintenance tasks does not resolve the placement block.",
            )

    def _relax_resource_availability(self, task_id: str, task: Any) -> RelaxationFinding:
        """Evaluate placement assuming resource availability constraints are waived."""
        reqs = task.get("resource_requirements", []) if isinstance(task, dict) else getattr(task, "resource_requirements", [])
        res_ids = [r.get("resource_id") if isinstance(r, dict) else getattr(r, "resource_id", None) for r in reqs]
        res_ids = [r for r in res_ids if r]

        if not res_ids:
            return RelaxationFinding(
                scenario_type=RelaxationScenarioType.IGNORE_RESOURCE_AVAILABILITY,
                description="Hypothetically waive resource availability restrictions.",
                feasible=False,
                hypothetical=True,
                approvable=False,
                explanation="Task does not require any specialized resources; resource availability is not a blocking factor.",
            )

        return RelaxationFinding(
            scenario_type=RelaxationScenarioType.IGNORE_RESOURCE_AVAILABILITY,
            description="Hypothetically waive resource availability restrictions.",
            feasible=True,
            blocking_entities=res_ids,
            relaxation_magnitude=f"Waives required resources: {', '.join(res_ids)}",
            hypothetical=True,
            approvable=False,
            explanation=f"Assuming external contract machine or additional gang is mobilized for {res_ids}, task could proceed if track is clear.",
        )

    def _relax_dependencies(self, task_id: str, task: Any) -> RelaxationFinding:
        """Evaluate placement assuming Finish-to-Start dependencies are waived."""
        deps = self.snapshot.dependencies_by_successor.get(task_id, [])
        if not deps:
            return RelaxationFinding(
                scenario_type=RelaxationScenarioType.IGNORE_DEPENDENCIES,
                description="Hypothetically waive predecessor dependencies.",
                feasible=False,
                hypothetical=True,
                approvable=False,
                explanation="Task has no predecessor dependencies; dependency ordering is not a blocking factor.",
            )

        preds = [d.get("predecessor_task_id") if isinstance(d, dict) else getattr(d, "predecessor_task_id") for d in deps]
        return RelaxationFinding(
            scenario_type=RelaxationScenarioType.IGNORE_DEPENDENCIES,
            description="Hypothetically waive predecessor dependencies.",
            feasible=True,
            blocking_entities=preds,
            relaxation_magnitude=f"Unlinks precedence from predecessors: {', '.join(preds)}",
            hypothetical=True,
            approvable=False,
            explanation=f"Waiving finish-to-start precedence from {preds} allows parallel or out-of-order execution.",
        )

    def _relax_window_widening(self, task_id: str, task: Any) -> RelaxationFinding:
        """Evaluate placement assuming allowed task window is widened by +/- 4 hours."""
        duration, buf_before, buf_after, all_secs, w_start, w_end = self._get_task_params(task)

        widened_start = max(self.snapshot.horizon.start, w_start - timedelta(hours=4))
        widened_end = min(self.snapshot.horizon.end, w_end + timedelta(hours=4))

        curr = widened_start
        found_candidate = None

        while curr + timedelta(minutes=duration) <= widened_end:
            t_cand_start = curr
            t_cand_end = curr + timedelta(minutes=duration)
            p_cand_start = t_cand_start - timedelta(minutes=buf_before)
            p_cand_end = t_cand_end + timedelta(minutes=buf_after)
            cand_pos = TimeInterval(start=p_cand_start, end=p_cand_end)

            # Check trains
            train_conflict = any(
                tp.section_id in all_secs and cand_pos.overlaps(tp.interval)
                for tp in self.snapshot.train_passes
            )
            # Check scheduled tasks
            task_conflict = any(
                any(s in all_secs for s in st.affected_sections) and cand_pos.overlaps(st.possession_interval)
                for st in self.schedule.scheduled_tasks
            )

            if not train_conflict and not task_conflict:
                found_candidate = (t_cand_start, t_cand_end)
                break

            curr += timedelta(minutes=self.step_minutes)

        if found_candidate:
            return RelaxationFinding(
                scenario_type=RelaxationScenarioType.WIDEN_TASK_WINDOW,
                description="Hypothetically widen allowed task window by up to +/- 4 hours.",
                feasible=True,
                candidate_start=found_candidate[0],
                candidate_end=found_candidate[1],
                relaxation_magnitude="Allowed window expanded by +/- 4 hours",
                hypothetical=True,
                approvable=False,
                explanation=f"Feasible open possession slot found at {found_candidate[0].isoformat()} if requisitioning department permits widening the execution window.",
            )
        else:
            return RelaxationFinding(
                scenario_type=RelaxationScenarioType.WIDEN_TASK_WINDOW,
                description="Hypothetically widen allowed task window by up to +/- 4 hours.",
                feasible=False,
                relaxation_magnitude="Allowed window expanded by +/- 4 hours",
                hypothetical=True,
                approvable=False,
                explanation="Widening the task window by 4 hours did not reveal any clear slot free of train and task contention.",
            )
