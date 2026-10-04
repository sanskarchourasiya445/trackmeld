"""CP-SAT Optimization Engine for TrackMeld Maintenance Scheduling.

Executes Google OR-Tools CP-SAT discrete optimization, maps status explicitly,
extracts scheduled placements, and recomputes independent metrics.
"""

from datetime import datetime, timezone
import time
import uuid
from typing import List, Dict, Any, Optional, Set

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
from backend.app.services.optimization.solver_config import OptimizationConfig
from backend.app.services.optimization.solver_diagnostics import SolverDiagnostics
from backend.app.services.optimization.cp_sat_model import CPSATModelBuilder


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
            empty_metrics = ScheduleMetrics(
                total_tasks=len(snapshot.tasks),
                scheduled_tasks=0,
                unscheduled_tasks=len(snapshot.tasks),
                completion_rate=0.0,
                mandatory_tasks=0,
                mandatory_scheduled=0,
                mandatory_unscheduled=0,
                mandatory_completion_rate=1.0,
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
        wall_time_s = round(solver.WallTime(), 4)
        user_time_s = round(solver.UserTime(), 4)

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

        obj_val = round(solver.ObjectiveValue(), 2) if has_solution else None
        best_bound = round(solver.BestObjectiveBound(), 2) if raw_status in (cp_model.OPTIMAL, cp_model.FEASIBLE, cp_model.UNKNOWN) else None

        gap = None
        gap_pct = None
        if obj_val is not None and best_bound is not None:
            gap = round(abs(best_bound - obj_val), 4)
            if raw_status == cp_model.OPTIMAL:
                gap_pct = 0.0
            elif abs(best_bound) > 0.001:
                gap_pct = round((gap / abs(best_bound)) * 100.0, 2)

        diagnostics = SolverDiagnostics(
            status=domain_status.value,
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
            for task in sorted_tasks:
                task_id = task.get("task_id", "UNKNOWN") if isinstance(task, dict) else getattr(task, "task_id", "UNKNOWN")
                task_code = task.get("task_code", task_id) if isinstance(task, dict) else getattr(task, "task_code", task_id)
                is_mandatory = task.get("mandatory", False) if isinstance(task, dict) else getattr(task, "mandatory", False)
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
                else:
                    # Task not placed by solver
                    unscheduled_results.append(
                        UnscheduledTaskResult(
                            task_id=task_id,
                            task_code=task_code,
                            mandatory=is_mandatory,
                            priority_score=prio_score.total_score if prio_score else None,
                            reason_codes=[ReasonCode.SECTION_OCCUPANCY_CONFLICT],
                            conflicts=[],
                            attempted_candidates_count=0,
                            diagnostic_message="Task unplaced: excluded by global optimization objective or track contention.",
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
                            primary_reason="EXCLUDED_BY_OBJECTIVE",
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

                fail_msg = (
                    "Global CP-SAT model proved mathematically INFEASIBLE under mandatory constraints."
                    if domain_status == SchedulerStatus.INFEASIBLE
                    else f"Solver terminated with status {domain_status.value}."
                )

                unscheduled_results.append(
                    UnscheduledTaskResult(
                        task_id=task_id,
                        task_code=task_code,
                        mandatory=is_mandatory,
                        priority_score=prio_score.total_score if prio_score else None,
                        reason_codes=[ReasonCode.INVALID_INTERVAL] if domain_status == SchedulerStatus.INFEASIBLE else [],
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
                        primary_reason=domain_status.value,
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
