"""CP-SAT Optimization Engine for TrackMeld Maintenance Scheduling.

Executes Google OR-Tools CP-SAT discrete optimization, maps status explicitly,
extracts scheduled placements, and recomputes independent metrics.
"""

from datetime import datetime, timedelta, timezone
import time
import uuid
from typing import List, Dict, Any, Optional, Set, Tuple

from ortools.sat.python import cp_model

from backend.app.domain.temporal import TimeInterval
from backend.app.domain.compatibility import (
    ReasonCode,
    ConflictDetail,
    ConstraintSeverity,
    ScheduledTaskPlacement,
)
from backend.app.domain.scheduling import (
    SchedulerType,
    SchedulerStatus,
    ScheduledTaskResult,
    UnscheduledTaskResult,
    TaskDecisionTrace,
    ScheduleMetrics,
    ScheduleResult,
    PriorityScore,
)
from backend.app.domain.planning_snapshot import PlanningSnapshot
from backend.app.services.priority_scorer import PriorityScorer
from backend.app.services.metrics_calculator import MetricsCalculator
from backend.app.services.task_ordering import detect_dependency_cycles
from backend.app.services.candidate_generator import CandidateGenerator
from backend.app.services.compatibility_service import CompatibilityEngine
from backend.app.services.optimization.solver_config import OptimizationConfig
from backend.app.services.optimization.solver_diagnostics import SolverDiagnostics
from backend.app.services.optimization.cp_sat_model import CPSATModelBuilder


def _validate_task_interval_and_window(
    task: Any,
    horizon: Any,
) -> Tuple[bool, Optional[ReasonCode], Optional[str]]:
    """Validate task duration, execution window, and relationship to planning horizon.

    Returns:
        (is_valid, reason_code, message)
    """
    est_duration = (
        task.get("estimated_duration_minutes", 60)
        if isinstance(task, dict)
        else getattr(task, "estimated_duration_minutes", 60)
    )
    if est_duration is None or est_duration <= 0:
        return (
            False,
            ReasonCode.INVALID_INTERVAL,
            f"Task duration ({est_duration}) must be positive.",
        )

    w_start = getattr(task, "window_start", None) or (task.get("window_start") if isinstance(task, dict) else None)
    w_end = getattr(task, "window_end", None) or (task.get("window_end") if isinstance(task, dict) else None)

    if w_start is None or w_end is None:
        return (
            False,
            ReasonCode.INVALID_INTERVAL,
            "Task window_start and window_end must be defined.",
        )

    if isinstance(w_start, str):
        w_start = datetime.fromisoformat(w_start)
    if isinstance(w_end, str):
        w_end = datetime.fromisoformat(w_end)

    if w_start.tzinfo is None:
        w_start = w_start.replace(tzinfo=timezone.utc)
    if w_end.tzinfo is None:
        w_end = w_end.replace(tzinfo=timezone.utc)

    if w_start >= w_end:
        return (
            False,
            ReasonCode.INVALID_INTERVAL,
            f"Task window_start ({w_start.isoformat()}) must strictly precede window_end ({w_end.isoformat()}).",
        )

    h_start = horizon.start if horizon.start.tzinfo else horizon.start.replace(tzinfo=timezone.utc)
    h_end = horizon.end if horizon.end.tzinfo else horizon.end.replace(tzinfo=timezone.utc)

    if w_end <= h_start or w_start >= h_end:
        return (
            False,
            ReasonCode.OUTSIDE_PLANNING_HORIZON,
            f"Task window [{w_start.isoformat()}, {w_end.isoformat()}) lies entirely outside planning horizon [{h_start.isoformat()}, {h_end.isoformat()}).",
        )

    window_duration_minutes = (w_end - w_start).total_seconds() / 60.0
    if est_duration > window_duration_minutes:
        return (
            False,
            ReasonCode.TASK_WINDOW_CONFLICT,
            f"Task duration ({est_duration}m) exceeds available window duration ({window_duration_minutes}m).",
        )

    eff_start = max(w_start, h_start)
    eff_end = min(w_end, h_end)
    eff_duration_minutes = (eff_end - eff_start).total_seconds() / 60.0
    if est_duration > eff_duration_minutes:
        return (
            False,
            ReasonCode.TASK_WINDOW_CONFLICT,
            f"Task duration ({est_duration}m) exceeds available horizon-bounded window duration ({eff_duration_minutes}m).",
        )

    return (True, None, None)


class CPSATSolver:
    """Deterministic, bounded CP-SAT optimization engine for TrackMeld."""

    def __init__(self, config: Optional[OptimizationConfig] = None) -> None:
        self.config = config or OptimizationConfig()

    def solve(
        self,
        snapshot: PlanningSnapshot,
        config: Optional[OptimizationConfig] = None,
    ) -> ScheduleResult:
        """Execute CP-SAT mathematical optimization on the given planning snapshot."""
        cfg = config or self.config
        start_time_perf = time.perf_counter()
        schedule_id = f"SCHED-CPSAT-{uuid.uuid4().hex[:8].upper()}"

        # ---------------------------------------------------------------------
        # 1. Pre-Check: Dependency Cycle Detection
        # ---------------------------------------------------------------------
        cycles = detect_dependency_cycles(snapshot.dependencies, set(snapshot.tasks_map.keys()))
        if cycles:
            cycle_desc = " -> ".join(cycles[0])
            mandatory_count = sum(
                1 for t in (snapshot.tasks_map.values() if snapshot.tasks_map else snapshot.tasks)
                if (getattr(t, "mandatory", False) if hasattr(t, "mandatory") else (t.get("mandatory", False) if isinstance(t, dict) else False))
            )
            empty_metrics = ScheduleMetrics(
                total_tasks=len(snapshot.tasks),
                scheduled_tasks=0,
                unscheduled_tasks=len(snapshot.tasks),
                completion_rate=0.0,
                mandatory_tasks=mandatory_count,
                mandatory_scheduled=0,
                mandatory_unscheduled=mandatory_count,
                mandatory_completion_rate=0.0,
                total_scheduled_duration_minutes=0,
                total_possession_duration_minutes=0,
                total_priority_score_available=0.0,
                scheduled_priority_score=0.0,
                unscheduled_priority_score=0.0,
                priority_score_capture_rate=0.0,
            )
            return ScheduleResult(
                schedule_id=schedule_id,
                scheduler_type=SchedulerType.CP_SAT,
                scheduler_version=cfg.solver_version,
                scenario_id=snapshot.scenario_id,
                snapshot_id=snapshot.snapshot_id,
                planning_start=snapshot.horizon.start,
                planning_end=snapshot.horizon.end,
                status=SchedulerStatus.INVALID_INPUT,
                scheduled_tasks=[],
                unscheduled_tasks=[
                    UnscheduledTaskResult(
                        task_id=t_id,
                        task_code=getattr(t, "task_code", t_id) if hasattr(t, "task_code") else t.get("task_code", t_id),
                        mandatory=getattr(t, "mandatory", False) if hasattr(t, "mandatory") else t.get("mandatory", False),
                        priority_score=None,
                        reason_codes=[ReasonCode.DEPENDENCY_NOT_SATISFIED],
                        conflicts=[],
                        attempted_candidates_count=0,
                        diagnostic_message=f"Circular dependency detected in scenario: {cycle_desc}",
                    )
                    for t_id, t in snapshot.tasks_map.items()
                ],
                metrics=empty_metrics,
                configuration=cfg.model_dump(),
                execution_time_ms=round((time.perf_counter() - start_time_perf) * 1000, 2),
                decision_trace=[],
                solver_diagnostics=None,
            )

        # ---------------------------------------------------------------------
        # 2. Priority Scoring
        # ---------------------------------------------------------------------
        scores_map = PriorityScorer.score_all_tasks(snapshot, cfg.priority_config)

        # ---------------------------------------------------------------------
        # 3. Model Assembly
        # ---------------------------------------------------------------------
        builder = CPSATModelBuilder(snapshot, scores_map, cfg)
        model = builder.build()

        # ---------------------------------------------------------------------
        # 4. Configure OR-Tools CP-SAT Solver
        # ---------------------------------------------------------------------
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = cfg.time_limit_seconds
        solver.parameters.num_search_workers = cfg.num_search_workers
        solver.parameters.random_seed = cfg.random_seed
        solver.parameters.log_search_progress = cfg.log_search_progress

        # ---------------------------------------------------------------------
        # 5. Solve Execution
        # ---------------------------------------------------------------------
        raw_status = solver.Solve(model)
        try:
            wall_time_s = round(solver.WallTime(), 4)
        except Exception:
            wall_time_s = 0.0

        try:
            user_time_s = round(solver.UserTime(), 4)
        except Exception:
            user_time_s = wall_time_s

        # Map CP-SAT status to domain SchedulerStatus
        status_map = {
            cp_model.OPTIMAL: SchedulerStatus.OPTIMAL,
            cp_model.FEASIBLE: SchedulerStatus.FEASIBLE,
            cp_model.INFEASIBLE: SchedulerStatus.INFEASIBLE,
            cp_model.MODEL_INVALID: SchedulerStatus.INVALID_INPUT,
            cp_model.UNKNOWN: SchedulerStatus.UNKNOWN,
        }
        domain_status = status_map.get(raw_status, SchedulerStatus.FAILED)

        # ---------------------------------------------------------------------
        # 6. Extract Solution & Diagnostics
        # ---------------------------------------------------------------------
        scheduled_results: List[ScheduledTaskResult] = []
        unscheduled_results: List[UnscheduledTaskResult] = []
        decision_traces: List[TaskDecisionTrace] = []

        has_solution = raw_status in (cp_model.OPTIMAL, cp_model.FEASIBLE)

        obj_val = None
        if has_solution:
            try:
                obj_val = round(solver.ObjectiveValue(), 2)
            except Exception:
                obj_val = None

        best_bound = None
        if raw_status in (cp_model.OPTIMAL, cp_model.FEASIBLE, cp_model.UNKNOWN):
            try:
                best_bound = round(solver.BestObjectiveBound(), 2)
            except Exception:
                best_bound = None

        gap = None
        gap_pct = None
        if obj_val is not None and best_bound is not None:
            gap = round(abs(best_bound - obj_val), 4)
            if raw_status == cp_model.OPTIMAL:
                gap_pct = 0.0
            elif abs(best_bound) > 0.001:
                gap_pct = round((gap / abs(best_bound)) * 100.0, 2)

        is_timeout = (
            raw_status == cp_model.UNKNOWN
            and cfg.time_limit_seconds > 0
            and wall_time_s >= (cfg.time_limit_seconds - 0.5)
        )
        diag_status = "TIMEOUT" if is_timeout else domain_status.value

        diagnostics = SolverDiagnostics(
            status=diag_status,
            wall_time_seconds=wall_time_s,
            user_time_seconds=user_time_s,
            objective_value=obj_val,
            best_bound=best_bound,
            optimality_gap=gap,
            optimality_gap_percentage=gap_pct,
            num_booleans=len(model.Proto().variables),
            num_integers=len(builder.start_vars),
            num_constraints=len(model.Proto().constraints),
            num_intervals=len(builder.task_intervals),
            num_workers=cfg.num_search_workers,
            random_seed=cfg.random_seed,
            model_version=cfg.model_version,
            solver_version=cfg.solver_version,
            solver_mode=cfg.solver_mode,
        )

        sequence_counter = 1

        if has_solution:
            sorted_tasks = sorted(
                snapshot.tasks,
                key=lambda t: t.get("task_id", "") if isinstance(t, dict) else getattr(t, "task_id", "")
            )

            scheduled_placements: List[ScheduledTaskPlacement] = []
            scheduled_task_ids: Set[str] = set()

            # Pass 1: Extract placed/scheduled tasks
            for task in sorted_tasks:
                task_id = task.get("task_id", "UNKNOWN") if isinstance(task, dict) else getattr(task, "task_id", "UNKNOWN")
                task_code = task.get("task_code", task_id) if isinstance(task, dict) else getattr(task, "task_code", task_id)
                prio_score = scores_map.get(task_id)

                presence_val = solver.Value(builder.presence_vars[task_id])

                if presence_val == 1:
                    start_min = solver.Value(builder.start_vars[task_id])
                    end_min = solver.Value(builder.end_vars[task_id])
                    pos_start_min = solver.Value(builder.pos_start_vars[task_id])
                    pos_end_min = solver.Value(builder.pos_end_vars[task_id])

                    start_dt = builder.min_to_dt(start_min)
                    end_dt = builder.min_to_dt(end_min)
                    pos_start_dt = builder.min_to_dt(pos_start_min)
                    pos_end_dt = builder.min_to_dt(pos_end_min)

                    work_interval = TimeInterval(start=start_dt, end=end_dt)
                    pos_interval = TimeInterval(start=pos_start_dt, end=pos_end_dt)

                    duration = builder.task_durations.get(task_id, 60)
                    affected_sections = builder.task_affected_sections.get(task_id, [])
                    assigned_resources = builder.task_resources.get(task_id, [])

                    task_track_id = task.get("track_id") if isinstance(task, dict) else getattr(task, "track_id", None)
                    assigned_track = None
                    if task_track_id and task_track_id in snapshot.tracks_map:
                        trk_obj = snapshot.tracks_map[task_track_id]
                        trk_sec = getattr(trk_obj, "section_id", None) if not isinstance(trk_obj, dict) else trk_obj.get("section_id")
                        primary_sec = task.get("section_id") if isinstance(task, dict) else getattr(task, "section_id", None)
                        if trk_sec == primary_sec:
                            assigned_track = task_track_id

                    req_traffic = getattr(task, "requires_traffic_block", True) if hasattr(task, "requires_traffic_block") else task.get("requires_traffic_block", True)
                    req_power = getattr(task, "requires_power_block", False) if hasattr(task, "requires_power_block") else task.get("requires_power_block", False)

                    primary_sec_id = task.get("section_id") if isinstance(task, dict) else getattr(task, "section_id", "UNKNOWN")
                    placement = ScheduledTaskPlacement(
                        task_id=task_id,
                        task_code=task_code,
                        section_id=primary_sec_id,
                        additional_section_ids=[s for s in affected_sections if s != primary_sec_id],
                        interval=work_interval,
                        possession_interval=pos_interval,
                        assigned_resource_ids=assigned_resources,
                        requires_traffic_block=req_traffic,
                        requires_power_block=req_power,
                    )
                    scheduled_placements.append(placement)
                    scheduled_task_ids.add(task_id)

                    scheduled_results.append(
                        ScheduledTaskResult(
                            task_id=task_id,
                            task_code=task_code,
                            interval=work_interval,
                            possession_interval=pos_interval,
                            duration_minutes=duration,
                            affected_sections=affected_sections,
                            assigned_resources=assigned_resources,
                            priority_score=prio_score.total_score if prio_score else None,
                            priority_breakdown={k: v.contribution for k, v in prio_score.components.items()} if prio_score else None,
                            sequence_order=sequence_counter,
                            scheduling_reason="OPTIMAL" if raw_status == cp_model.OPTIMAL else "FEASIBLE",
                            rule_evidence_ids=[],
                            assigned_track_id=assigned_track,
                        )
                    )

                    decision_traces.append(
                        TaskDecisionTrace(
                            task_id=task_id,
                            task_code=task_code,
                            order_position=sequence_counter,
                            priority_score=prio_score.total_score if prio_score else None,
                            status="SCHEDULED",
                            candidates_evaluated=1,
                            selected_start=start_dt,
                            selected_end=end_dt,
                            primary_reason=domain_status.value,
                        )
                    )
                    sequence_counter += 1

            # Pass 2: Evaluate unscheduled tasks with post-solve analysis
            for task in sorted_tasks:
                task_id = task.get("task_id", "UNKNOWN") if isinstance(task, dict) else getattr(task, "task_id", "UNKNOWN")
                task_code = task.get("task_code", task_id) if isinstance(task, dict) else getattr(task, "task_code", task_id)
                is_mandatory = task.get("mandatory", False) if isinstance(task, dict) else getattr(task, "mandatory", False)
                prio_score = scores_map.get(task_id)

                presence_val = solver.Value(builder.presence_vars[task_id])

                if presence_val == 0:
                    is_valid, interval_reason, interval_msg = _validate_task_interval_and_window(task, snapshot.horizon)
                    if not is_valid:
                        task_reason_codes = [interval_reason]
                        diag_msg = interval_msg
                        task_conflicts: List[ConflictDetail] = []
                        cands_evaluated = 0
                        primary_reason_str = interval_reason.value
                    else:
                        preds = snapshot.dependencies_by_successor.get(task_id, [])
                        unscheduled_preds = [
                            (getattr(d, "predecessor_task_id", None) or d.get("predecessor_task_id"))
                            for d in preds
                            if (getattr(d, "predecessor_task_id", None) or d.get("predecessor_task_id")) not in scheduled_task_ids
                        ]
                        if unscheduled_preds:
                            task_reason_codes = [ReasonCode.DEPENDENCY_NOT_SATISFIED]
                            diag_msg = f"Predecessor task(s) {unscheduled_preds} were not scheduled."
                            task_conflicts = []
                            cands_evaluated = 0
                            primary_reason_str = "DEPENDENCY_NOT_SATISFIED"
                        elif len(snapshot.resources_map) > 0 and any(rid not in snapshot.resources_map for rid in builder.task_resources.get(task_id, [])):
                            unknown_res = [rid for rid in builder.task_resources.get(task_id, []) if rid not in snapshot.resources_map]
                            task_reason_codes = [ReasonCode.RESOURCE_UNAVAILABLE]
                            diag_msg = f"Task references unknown resource(s) {unknown_res} not present in scenario resource catalog."
                            task_conflicts = []
                            cands_evaluated = 0
                            primary_reason_str = "RESOURCE_UNAVAILABLE"
                        elif len(snapshot.resources_map) > 0 and any(
                            builder.task_resource_demands.get((task_id, rid), 1) > (
                                snapshot.resources_map[rid].get("capacity", 1)
                                if isinstance(snapshot.resources_map[rid], dict)
                                else getattr(snapshot.resources_map[rid], "capacity", 1)
                            )
                            for rid in builder.task_resources.get(task_id, [])
                            if rid in snapshot.resources_map
                        ):
                            cap_exceeded_res = [
                                rid for rid in builder.task_resources.get(task_id, [])
                                if rid in snapshot.resources_map and builder.task_resource_demands.get((task_id, rid), 1) > (
                                    snapshot.resources_map[rid].get("capacity", 1)
                                    if isinstance(snapshot.resources_map[rid], dict)
                                    else getattr(snapshot.resources_map[rid], "capacity", 1)
                                )
                            ]
                            task_reason_codes = [ReasonCode.RESOURCE_UNAVAILABLE]
                            diag_msg = f"Task resource demand exceeds capacity for resource(s) {cap_exceeded_res}."
                            task_conflicts = []
                            cands_evaluated = 0
                            primary_reason_str = "RESOURCE_UNAVAILABLE"
                        else:
                            candidates = CandidateGenerator.generate_candidate_starts(
                                task=task,
                                snapshot=snapshot,
                                existing_placements=scheduled_placements,
                                max_candidates=10,
                            )
                            cands_evaluated = len(candidates)
                            evaluated_reasons: Set[ReasonCode] = set()
                            evaluated_conflicts: List[ConflictDetail] = []
                            has_physically_compatible_candidate = False

                            duration = builder.task_durations.get(task_id, 60)
                            for cand_start in candidates:
                                cand_end = cand_start + timedelta(minutes=duration)
                                comp_res = CompatibilityEngine.evaluate_task_placement(
                                    task=task,
                                    candidate_start=cand_start,
                                    candidate_end=cand_end,
                                    horizon=snapshot.horizon,
                                    train_passes=snapshot.train_passes,
                                    existing_placements=scheduled_placements,
                                    resource_availabilities=snapshot.resource_availabilities,
                                    dependencies=snapshot.dependencies,
                                    sections_map=snapshot.sections_map,
                                    rules_map=snapshot.rules_map,
                                    resources_map=snapshot.resources_map,
                                )
                                if comp_res.compatible:
                                    has_physically_compatible_candidate = True
                                    break
                                else:
                                    evaluated_reasons.update(comp_res.reason_codes)
                                    evaluated_conflicts.extend(comp_res.conflicts)

                            if not candidates:
                                task_reason_codes = [ReasonCode.UNRESOLVED_CONSTRAINT_CONFLICT]
                                diag_msg = "Task unplaced: no candidate execution window available within horizon/window bounds."
                                task_conflicts = []
                                primary_reason_str = "EXCLUDED_BY_OBJECTIVE"
                            elif not has_physically_compatible_candidate and evaluated_reasons:
                                task_reason_codes = sorted(list(evaluated_reasons), key=lambda r: r.value)
                                diag_msg = f"Task unplaced: conflicting constraints across evaluated candidate windows ({cands_evaluated} evaluated)."
                                task_conflicts = evaluated_conflicts[:10]
                                primary_reason_str = task_reason_codes[0].value
                            else:
                                task_reason_codes = [ReasonCode.UNRESOLVED_CONSTRAINT_CONFLICT]
                                diag_msg = "Task unplaced: excluded by global optimization objective or capacity trade-offs."
                                task_conflicts = []
                                primary_reason_str = "EXCLUDED_BY_OBJECTIVE"

                    unscheduled_results.append(
                        UnscheduledTaskResult(
                            task_id=task_id,
                            task_code=task_code,
                            mandatory=is_mandatory,
                            priority_score=prio_score.total_score if prio_score else None,
                            reason_codes=task_reason_codes,
                            conflicts=task_conflicts,
                            attempted_candidates_count=cands_evaluated,
                            diagnostic_message=diag_msg,
                        )
                    )

                    decision_traces.append(
                        TaskDecisionTrace(
                            task_id=task_id,
                            task_code=task_code,
                            order_position=sequence_counter,
                            priority_score=prio_score.total_score if prio_score else None,
                            status="UNSCHEDULED",
                            candidates_evaluated=cands_evaluated,
                            primary_reason=primary_reason_str,
                        )
                    )
                    sequence_counter += 1
        else:
            # Infeasible, Timeout (Unknown), or Model Invalid
            for task in snapshot.tasks:
                task_id = task.get("task_id", "UNKNOWN") if isinstance(task, dict) else getattr(task, "task_id", "UNKNOWN")
                task_code = task.get("task_code", task_id) if isinstance(task, dict) else getattr(task, "task_code", task_id)
                is_mandatory = task.get("mandatory", False) if isinstance(task, dict) else getattr(task, "mandatory", False)
                prio_score = scores_map.get(task_id)

                is_valid, interval_reason, interval_msg = _validate_task_interval_and_window(task, snapshot.horizon)
                if not is_valid:
                    task_reason_codes = [interval_reason]
                    fail_msg = interval_msg
                    task_primary = interval_reason.value
                else:
                    if domain_status == SchedulerStatus.INFEASIBLE:
                        task_reason_codes = [ReasonCode.UNRESOLVED_CONSTRAINT_CONFLICT]
                        fail_msg = "Global CP-SAT model proved mathematically INFEASIBLE under mandatory constraints."
                        task_primary = "INFEASIBLE"
                    elif domain_status == SchedulerStatus.UNKNOWN:
                        task_reason_codes = [ReasonCode.UNRESOLVED_CONSTRAINT_CONFLICT]
                        if is_timeout:
                            fail_msg = f"Solver timed out after {wall_time_s}s (limit: {cfg.time_limit_seconds}s) with status UNKNOWN without finding a feasible placement."
                            task_primary = "TIMEOUT"
                        else:
                            fail_msg = "Solver terminated with status UNKNOWN without finding a feasible placement."
                            task_primary = "UNKNOWN"
                    elif domain_status == SchedulerStatus.INVALID_INPUT:
                        task_reason_codes = [ReasonCode.UNRESOLVED_CONSTRAINT_CONFLICT]
                        fail_msg = "Model assembly was rejected as INVALID_INPUT."
                        task_primary = "INVALID_INPUT"
                    else:
                        task_reason_codes = [ReasonCode.UNRESOLVED_CONSTRAINT_CONFLICT]
                        fail_msg = f"Solver terminated with status {domain_status.value}."
                        task_primary = domain_status.value

                unscheduled_results.append(
                    UnscheduledTaskResult(
                        task_id=task_id,
                        task_code=task_code,
                        mandatory=is_mandatory,
                        priority_score=prio_score.total_score if prio_score else None,
                        reason_codes=task_reason_codes,
                        conflicts=[],
                        attempted_candidates_count=0,
                        diagnostic_message=fail_msg,
                    )
                )

                decision_traces.append(
                    TaskDecisionTrace(
                        task_id=task_id,
                        task_code=task_code,
                        order_position=sequence_counter,
                        priority_score=prio_score.total_score if prio_score else None,
                        status="UNSCHEDULED",
                        candidates_evaluated=0,
                        primary_reason=task_primary,
                    )
                )
                sequence_counter += 1

        # ---------------------------------------------------------------------
        # 7. Independent Metrics Recalculation
        # ---------------------------------------------------------------------
        metrics = MetricsCalculator.calculate(
            scheduled_tasks=scheduled_results,
            unscheduled_tasks=unscheduled_results,
            scores_map=scores_map,
            snapshot=snapshot,
        )

        exec_time_ms = round((time.perf_counter() - start_time_perf) * 1000, 2)

        return ScheduleResult(
            schedule_id=schedule_id,
            scheduler_type=SchedulerType.CP_SAT,
            scheduler_version=cfg.solver_version,
            scenario_id=snapshot.scenario_id,
            snapshot_id=snapshot.snapshot_id,
            planning_start=snapshot.horizon.start,
            planning_end=snapshot.horizon.end,
            status=domain_status,
            scheduled_tasks=scheduled_results,
            unscheduled_tasks=unscheduled_results,
            metrics=metrics,
            configuration=cfg.model_dump(),
            execution_time_ms=exec_time_ms,
            decision_trace=decision_traces,
            solver_diagnostics=diagnostics.model_dump(),
        )
