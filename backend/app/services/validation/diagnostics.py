"""Root-cause diagnostics and evidence extraction for unscheduled maintenance tasks."""

import time
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

from backend.app.domain.temporal import TimeInterval
from backend.app.domain.scheduling import ScheduleResult
from backend.app.domain.planning_snapshot import PlanningSnapshot
from backend.app.services.validation.models import (
    DiagnosticStatus,
    UnscheduledTaskDiagnostic,
    DiagnosticsReport,
)
from backend.app.services.validation.relaxation import RelaxationAnalyzer


class UnscheduledTaskDiagnosticsService:
    """Diagnoses root causes for why maintenance tasks could not be placed in a schedule."""

    def __init__(self, snapshot: PlanningSnapshot, schedule: ScheduleResult) -> None:
        self.snapshot = snapshot
        self.schedule = schedule
        self.relaxation_analyzer = RelaxationAnalyzer(snapshot, schedule)

    def diagnose_all(self, target_task_id: Optional[str] = None) -> DiagnosticsReport:
        """Run root-cause diagnostics across unscheduled tasks (or a single task if target_task_id is given)."""
        start_time = time.perf_counter()

        unscheduled_tasks = self.schedule.unscheduled_tasks
        if target_task_id:
            unscheduled_tasks = [ut for ut in unscheduled_tasks if ut.task_id == target_task_id]

        diagnostics_list: List[UnscheduledTaskDiagnostic] = []

        for ut in unscheduled_tasks:
            diag = self.diagnose_task(ut.task_id)
            diagnostics_list.append(diag)

        runtime_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return DiagnosticsReport(
            scenario_id=self.snapshot.scenario_id,
            snapshot_id=self.snapshot.snapshot_id,
            total_unscheduled_tasks=len(diagnostics_list),
            diagnostics=diagnostics_list,
            execution_time_ms=runtime_ms,
        )

    def diagnose_task(self, task_id: str) -> UnscheduledTaskDiagnostic:
        """Investigate why a specific task was not placed, gathering concrete evidence."""
        orig = self.snapshot.tasks_map.get(task_id)
        if not orig:
            return UnscheduledTaskDiagnostic(
                task_id=task_id,
                task_code=task_id,
                mandatory=False,
                status=DiagnosticStatus.UNKNOWN,
                primary_reason="Task ID not found in input PlanningSnapshot.",
            )

        task_code = orig.get("task_code", task_id) if isinstance(orig, dict) else getattr(orig, "task_code", task_id)
        mandatory = orig.get("mandatory", False) if isinstance(orig, dict) else getattr(orig, "mandatory", False)
        duration = orig.get("estimated_duration_minutes", 60) if isinstance(orig, dict) else getattr(orig, "estimated_duration_minutes", 60)
        buf_before = orig.get("safety_buffer_before_minutes", 10) if isinstance(orig, dict) else getattr(orig, "safety_buffer_before_minutes", 10)
        buf_after = orig.get("safety_buffer_after_minutes", 10) if isinstance(orig, dict) else getattr(orig, "safety_buffer_after_minutes", 10)
        req_power = orig.get("requires_power_block", False) if isinstance(orig, dict) else getattr(orig, "requires_power_block", False)
        primary_sec = orig.get("section_id") if isinstance(orig, dict) else getattr(orig, "section_id", None)
        add_secs = orig.get("additional_sections", []) if isinstance(orig, dict) else [s.section_id for s in getattr(orig, "affected_sections", [])]
        all_secs = {primary_sec} | set(add_secs)

        w_start_raw = orig.get("window_start") if isinstance(orig, dict) else getattr(orig, "window_start")
        w_end_raw = orig.get("window_end") if isinstance(orig, dict) else getattr(orig, "window_end")

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

        reason_codes: List[str] = []
        conflicting_tasks: List[str] = []
        conflicting_trains: List[str] = []
        conflicting_resources: List[str] = []
        conflicting_windows: List[str] = []
        dependency_blockers: List[str] = []
        rule_blockers: List[str] = []
        evidence: Dict[str, Any] = {}

        # ---------------------------------------------------------------------
        # 1. Physical Rule Feasibility Check: Power Block on Unelectrified Section
        # ---------------------------------------------------------------------
        if req_power and primary_sec:
            sec_obj = self.snapshot.sections_map.get(primary_sec, {})
            electrified = sec_obj.get("electrified", True) if isinstance(sec_obj, dict) else getattr(sec_obj, "electrified", True)
            if not electrified:
                primary_reason = f"Physically impossible: Task requires traction power block, but section '{primary_sec}' is not electrified."
                rule_blockers.append("ACT-1989-S15")
                reason_codes.append("UNMET_BLOCK_REQUIREMENT")
                evidence["section_electrified"] = False
                evidence["rule_reference"] = "ACT-1989-S15"

                relaxation_results = self.relaxation_analyzer.analyze_task(task_id)
                return UnscheduledTaskDiagnostic(
                    task_id=task_id,
                    task_code=task_code,
                    mandatory=mandatory,
                    status=DiagnosticStatus.DIAGNOSED,
                    primary_reason=primary_reason,
                    reason_codes=reason_codes,
                    affected_sections=list(all_secs),
                    rule_blockers=rule_blockers,
                    evidence=evidence,
                    relaxation_analyses=relaxation_results,
                )

        # ---------------------------------------------------------------------
        # 2. Static Window Sufficiency Check
        # ---------------------------------------------------------------------
        window_duration = (w_end - w_start).total_seconds() / 60
        required_pos_duration = duration + buf_before + buf_after

        if window_duration < required_pos_duration:
            primary_reason = f"Execution window duration ({window_duration:.0f}m) is strictly shorter than required possession ({required_pos_duration}m)."
            conflicting_windows.append(f"[{w_start.isoformat()}, {w_end.isoformat()})")
            reason_codes.append("NO_FEASIBLE_TIME_WINDOW")
            evidence["window_duration_minutes"] = window_duration
            evidence["required_possession_minutes"] = required_pos_duration

            relaxation_results = self.relaxation_analyzer.analyze_task(task_id)
            return UnscheduledTaskDiagnostic(
                task_id=task_id,
                task_code=task_code,
                mandatory=mandatory,
                status=DiagnosticStatus.DIAGNOSED,
                primary_reason=primary_reason,
                reason_codes=reason_codes,
                conflicting_windows=conflicting_windows,
                affected_sections=list(all_secs),
                evidence=evidence,
                relaxation_analyses=relaxation_results,
            )

        # ---------------------------------------------------------------------
        # 3. Predecessor Dependency Check
        # ---------------------------------------------------------------------
        sched_map = {st.task_id: st for st in self.schedule.scheduled_tasks}
        preds = self.snapshot.dependencies_by_successor.get(task_id, [])
        for dep in preds:
            p_id = dep.get("predecessor_task_id") if isinstance(dep, dict) else getattr(dep, "predecessor_task_id")
            if p_id not in sched_map:
                dependency_blockers.append(p_id)
                reason_codes.append("DEPENDENCY_NOT_SATISFIED")

        if dependency_blockers:
            primary_reason = f"Predecessor task(s) {dependency_blockers} were not scheduled, blocking this task by Finish-to-Start dependency."
            evidence["unplaced_predecessors"] = dependency_blockers
            relaxation_results = self.relaxation_analyzer.analyze_task(task_id)
            return UnscheduledTaskDiagnostic(
                task_id=task_id,
                task_code=task_code,
                mandatory=mandatory,
                status=DiagnosticStatus.DIAGNOSED,
                primary_reason=primary_reason,
                reason_codes=reason_codes,
                dependency_blockers=dependency_blockers,
                affected_sections=list(all_secs),
                evidence=evidence,
                relaxation_analyses=relaxation_results,
            )

        # ---------------------------------------------------------------------
        # 4. Track Contention & Train Path Interference
        # ---------------------------------------------------------------------
        # Sample timepoints across window
        curr = w_start
        train_interferences = set()
        task_interferences = set()
        slots_evaluated = 0

        while curr + timedelta(minutes=duration) <= w_end and slots_evaluated < 30:
            slots_evaluated += 1
            cand_pos = TimeInterval(
                start=curr - timedelta(minutes=buf_before),
                end=curr + timedelta(minutes=duration + buf_after),
            )

            # Check trains
            for tp in self.snapshot.train_passes:
                if tp.section_id in all_secs and cand_pos.overlaps(tp.interval):
                    train_interferences.add(f"{tp.train_number} ({tp.section_id})")

            # Check scheduled tasks
            for st in self.schedule.scheduled_tasks:
                if any(s in all_secs for s in st.affected_sections) and cand_pos.overlaps(st.possession_interval):
                    task_interferences.add(st.task_id)

            curr += timedelta(minutes=30)

        if train_interferences and not task_interferences:
            primary_reason = f"Corridor train movements {list(train_interferences)[:3]} block all feasible clearance intervals in window."
            reason_codes.append("TRAIN_MOVEMENT_CONFLICT")
            conflicting_trains = list(train_interferences)
            evidence["colliding_trains"] = conflicting_trains
        elif task_interferences:
            primary_reason = f"Concurrent scheduled maintenance tasks {list(task_interferences)[:3]} occupy the track during the allowed window."
            reason_codes.append("SECTION_OCCUPANCY_CONFLICT")
            conflicting_tasks = list(task_interferences)
            evidence["colliding_tasks"] = conflicting_tasks
        else:
            primary_reason = "Excluded by global solver objective or resource competition."
            reason_codes.append("SOLVER_DID_NOT_RETURN_PLACEMENT")

        relaxation_results = self.relaxation_analyzer.analyze_task(task_id)

        return UnscheduledTaskDiagnostic(
            task_id=task_id,
            task_code=task_code,
            mandatory=mandatory,
            status=DiagnosticStatus.DIAGNOSED,
            primary_reason=primary_reason,
            reason_codes=reason_codes,
            conflicting_tasks=conflicting_tasks,
            conflicting_train_movements=conflicting_trains,
            conflicting_resources=conflicting_resources,
            conflicting_windows=conflicting_windows,
            dependency_blockers=dependency_blockers,
            affected_sections=list(all_secs),
            rule_blockers=rule_blockers,
            evidence=evidence,
            relaxation_analyses=relaxation_results,
        )
