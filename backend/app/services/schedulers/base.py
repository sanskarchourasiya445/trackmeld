"""Abstract Base Scheduler defining the common scheduling lifecycle for TrackMeld.

Enforces:
1. Exact same snapshot and hard constraint semantics across all schedulers.
2. Topological dependency awareness with deadlock prevention.
3. Common metrics and structured diagnostic execution trace.
4. Total immutability: zero mutation of underlying domain objects.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
import time
import uuid
from typing import List, Dict, Any, Optional, Set

from backend.app.domain.temporal import TimeInterval
from backend.app.domain.compatibility import (
    ReasonCode,
    ConflictDetail,
    ConstraintSeverity,
    ScheduledTaskPlacement,
    CompatibilityResult,
)
from backend.app.domain.scheduling import (
    SchedulerType,
    SchedulerStatus,
    SchedulerConfig,
    ScheduledTaskResult,
    UnscheduledTaskResult,
    TaskDecisionTrace,
    ScheduleMetrics,
    ScheduleResult,
    PriorityScore,
)
from backend.app.domain.planning_snapshot import PlanningSnapshot
from backend.app.services.compatibility_service import CompatibilityEngine
from backend.app.services.priority_scorer import PriorityScorer
from backend.app.services.candidate_generator import CandidateGenerator
from backend.app.services.metrics_calculator import MetricsCalculator
from backend.app.services.task_ordering import detect_dependency_cycles, InvalidDependencyGraphError


class BaseScheduler(ABC):
    """Abstract common scheduling engine for baseline and future solvers."""

    def __init__(self, scheduler_type: SchedulerType, scheduler_version: str = "1.0.0") -> None:
        self.scheduler_type = scheduler_type
        self.scheduler_version = scheduler_version

    @abstractmethod
    def order_tasks(
        self,
        snapshot: PlanningSnapshot,
        scores_map: Dict[str, PriorityScore],
        config: SchedulerConfig,
    ) -> List[Any]:
        """Order tasks deterministically according to scheduling strategy."""
        pass

    def schedule(
        self,
        snapshot: PlanningSnapshot,
        config: Optional[SchedulerConfig] = None,
    ) -> ScheduleResult:
        """Execute deterministic scheduling against the planning snapshot."""
        start_time_perf = time.perf_counter()

        if config is None:
            config = SchedulerConfig(scheduler_type=self.scheduler_type, scheduler_version=self.scheduler_version)

        schedule_id = f"SCHED-{self.scheduler_type.value}-{uuid.uuid4().hex[:8].upper()}"

        # 1. Detect Dependency Cycles in Planning Snapshot
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
                scheduler_type=self.scheduler_type,
                scheduler_version=self.scheduler_version,
                scenario_id=snapshot.scenario_id,
                snapshot_id=snapshot.snapshot_id,
                planning_start=snapshot.horizon.start,
                planning_end=snapshot.horizon.end,
                status=SchedulerStatus.INVALID_INPUT,
                scheduled_tasks=[],
                unscheduled_tasks=[
                    UnscheduledTaskResult(
                        task_id=t_id,
                        task_code=getattr(t, "task_code", t_id),
                        mandatory=getattr(t, "mandatory", False),
                        priority_score=None,
                        reason_codes=[ReasonCode.DEPENDENCY_NOT_SATISFIED],
                        conflicts=[],
                        attempted_candidates_count=0,
                        diagnostic_message=f"Circular dependency detected in scenario: {cycle_desc}",
                    )
                    for t_id, t in snapshot.tasks_map.items()
                ],
                metrics=empty_metrics,
                configuration=config.model_dump(),
                execution_time_ms=round((time.perf_counter() - start_time_perf) * 1000, 2),
                decision_trace=[],
            )

        # 2. Compute Priority Scores for all tasks
        scores_map = PriorityScorer.score_all_tasks(snapshot, config.priority_config)

        # 3. Order tasks deterministically according to strategy
        ordered_tasks = self.order_tasks(snapshot, scores_map, config)

        # 4. Scheduling State
        scheduled_placements: List[ScheduledTaskPlacement] = []
        scheduled_results: List[ScheduledTaskResult] = []
        unscheduled_results: List[UnscheduledTaskResult] = []
        decision_traces: List[TaskDecisionTrace] = []

        scheduled_task_ids: Set[str] = set()
        failed_task_ids: Set[str] = set()

        remaining_tasks = list(ordered_tasks)
        order_position_counter = 1

        # Iterative greedy pass resolving dependencies
        while remaining_tasks:
            progress_made = False

            for task in list(remaining_tasks):
                task_id = getattr(task, "task_id", None) or task.get("task_id")
                task_code = getattr(task, "task_code", None) or task.get("task_code", task_id)
                is_mandatory = getattr(task, "mandatory", False) if hasattr(task, "mandatory") else task.get("mandatory", False)
                prio_score = scores_map.get(task_id)

                # Check if predecessors are still pending
                preds = snapshot.dependencies_by_successor.get(task_id, [])
                pending_preds = [
                    (getattr(d, "predecessor_task_id", None) or d.get("predecessor_task_id"))
                    for d in preds
                    if (getattr(d, "predecessor_task_id", None) or d.get("predecessor_task_id")) in {
                        getattr(t, "task_id", None) or t.get("task_id") for t in remaining_tasks
                    }
                ]

                if pending_preds:
                    # Predecessor is still in remaining queue; defer this task to later pass
                    continue

                # If any predecessor has permanently failed/unscheduled, this task cannot satisfy dependency
                failed_preds = [
                    (getattr(d, "predecessor_task_id", None) or d.get("predecessor_task_id"))
                    for d in preds
                    if (getattr(d, "predecessor_task_id", None) or d.get("predecessor_task_id")) in failed_task_ids
                ]

                if failed_preds:
                    unscheduled_results.append(
                        UnscheduledTaskResult(
                            task_id=task_id,
                            task_code=task_code,
                            mandatory=is_mandatory,
                            priority_score=prio_score.total_score if prio_score else None,
                            reason_codes=[ReasonCode.DEPENDENCY_NOT_SATISFIED],
                            conflicts=[],
                            attempted_candidates_count=0,
                            diagnostic_message=f"Predecessor task(s) {failed_preds} could not be scheduled.",
                        )
                    )
                    decision_traces.append(
                        TaskDecisionTrace(
                            task_id=task_id,
                            task_code=task_code,
                            order_position=order_position_counter,
                            priority_score=prio_score.total_score if prio_score else None,
                            status="UNSCHEDULED",
                            candidates_evaluated=0,
                            primary_reason="DEPENDENCY_NOT_SATISFIED",
                        )
                    )
                    order_position_counter += 1
                    failed_task_ids.add(task_id)
                    remaining_tasks.remove(task)
                    progress_made = True
                    break

                # 5. Generate Candidate Placements
                candidates = CandidateGenerator.generate_candidate_starts(
                    task=task,
                    snapshot=snapshot,
                    existing_placements=scheduled_placements,
                    max_candidates=config.max_candidate_attempts,
                )

                est_duration = task.get("estimated_duration_minutes", 60) if isinstance(task, dict) else getattr(task, "estimated_duration_minutes", 60)
                buf_before = task.get("safety_buffer_before_minutes", 10) if isinstance(task, dict) else getattr(task, "safety_buffer_before_minutes", 10)
                buf_after = task.get("safety_buffer_after_minutes", 10) if isinstance(task, dict) else getattr(task, "safety_buffer_after_minutes", 10)
                primary_sec = task.get("section_id") if isinstance(task, dict) else getattr(task, "section_id", None)

                additional_sec_ids = []
                if hasattr(task, "affected_sections"):
                    additional_sec_ids = [s.section_id for s in task.affected_sections]
                elif "additional_sections" in task:
                    additional_sec_ids = task["additional_sections"]
                all_sections = [primary_sec] + [s for s in additional_sec_ids if s != primary_sec]

                reqs = getattr(task, "resource_requirements", [])
                if not reqs and "resource_requirements" in task:
                    reqs = task["resource_requirements"]
                assigned_resource_ids = [
                    getattr(r, "resource_id", None) or r.get("resource_id")
                    for r in reqs
                    if getattr(r, "resource_id", None) or r.get("resource_id")
                ]

                req_traffic = getattr(task, "requires_traffic_block", True) if hasattr(task, "requires_traffic_block") else task.get("requires_traffic_block", True)
                req_power = getattr(task, "requires_power_block", False) if hasattr(task, "requires_power_block") else task.get("requires_power_block", False)

                placed = False
                all_conflicts: List[ConflictDetail] = []
                all_reasons: Set[ReasonCode] = set()

                for cand_start in candidates:
                    cand_end = cand_start + timedelta(minutes=est_duration)

                    comp_res: CompatibilityResult = CompatibilityEngine.evaluate_task_placement(
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
                    )

                    if comp_res.compatible:
                        # Feasible placement found!
                        placement = ScheduledTaskPlacement(
                            task_id=task_id,
                            task_code=task_code,
                            section_id=primary_sec,
                            additional_section_ids=additional_sec_ids,
                            interval=comp_res.evaluated_interval,
                            possession_interval=comp_res.possession_interval,
                            assigned_resource_ids=assigned_resource_ids,
                            requires_traffic_block=req_traffic,
                            requires_power_block=req_power,
                        )
                        scheduled_placements.append(placement)

                        scheduled_result = ScheduledTaskResult(
                            task_id=task_id,
                            task_code=task_code,
                            interval=comp_res.evaluated_interval,
                            possession_interval=comp_res.possession_interval,
                            duration_minutes=est_duration,
                            affected_sections=all_sections,
                            assigned_resources=assigned_resource_ids,
                            priority_score=prio_score.total_score if prio_score else None,
                            priority_breakdown={k: v.contribution for k, v in prio_score.components.items()} if prio_score else None,
                            sequence_order=len(scheduled_results) + 1,
                            scheduling_reason="FEASIBLE",
                            rule_evidence_ids=[re.rule_id for re in comp_res.rule_evidence if re.satisfied],
                        )
                        scheduled_results.append(scheduled_result)

                        decision_traces.append(
                            TaskDecisionTrace(
                                task_id=task_id,
                                task_code=task_code,
                                order_position=order_position_counter,
                                priority_score=prio_score.total_score if prio_score else None,
                                status="SCHEDULED",
                                candidates_evaluated=len(all_conflicts) + 1,
                                selected_start=cand_start,
                                selected_end=cand_end,
                                primary_reason="FEASIBLE",
                            )
                        )
                        order_position_counter += 1
                        scheduled_task_ids.add(task_id)
                        placed = True
                        progress_made = True
                        remaining_tasks.remove(task)
                        break
                    else:
                        all_conflicts.extend(comp_res.conflicts)
                        all_reasons.update(comp_res.reason_codes)

                if not placed:
                    # Infeasible across all evaluated candidate points
                    primary_reason_str = next(iter(all_reasons)).value if all_reasons else "NO_FEASIBLE_CANDIDATE"
                    unscheduled_results.append(
                        UnscheduledTaskResult(
                            task_id=task_id,
                            task_code=task_code,
                            mandatory=is_mandatory,
                            priority_score=prio_score.total_score if prio_score else None,
                            reason_codes=sorted(list(all_reasons), key=lambda r: r.value),
                            conflicts=all_conflicts[:10],  # Bound conflict diagnostic list
                            attempted_candidates_count=len(candidates),
                            diagnostic_message=f"No feasible candidate found under evaluated policy ({len(candidates)} candidates evaluated).",
                        )
                    )
                    decision_traces.append(
                        TaskDecisionTrace(
                            task_id=task_id,
                            task_code=task_code,
                            order_position=order_position_counter,
                            priority_score=prio_score.total_score if prio_score else None,
                            status="UNSCHEDULED",
                            candidates_evaluated=len(candidates),
                            primary_reason=primary_reason_str,
                        )
                    )
                    order_position_counter += 1
                    failed_task_ids.add(task_id)
                    remaining_tasks.remove(task)
                    progress_made = True
                    break

            if not progress_made and remaining_tasks:
                # Deadlock or cyclic dependence between remaining tasks
                for task in remaining_tasks:
                    t_id = getattr(task, "task_id", None) or task.get("task_id")
                    t_code = getattr(task, "task_code", None) or task.get("task_code", t_id)
                    is_mand = getattr(task, "mandatory", False) if hasattr(task, "mandatory") else task.get("mandatory", False)
                    p_score = scores_map.get(t_id)

                    unscheduled_results.append(
                        UnscheduledTaskResult(
                            task_id=t_id,
                            task_code=t_code,
                            mandatory=is_mand,
                            priority_score=p_score.total_score if p_score else None,
                            reason_codes=[ReasonCode.DEPENDENCY_NOT_SATISFIED],
                            conflicts=[],
                            attempted_candidates_count=0,
                            diagnostic_message="Unresolvable dependency blocking task placement.",
                        )
                    )
                    decision_traces.append(
                        TaskDecisionTrace(
                            task_id=t_id,
                            task_code=t_code,
                            order_position=order_position_counter,
                            priority_score=p_score.total_score if p_score else None,
                            status="UNSCHEDULED",
                            candidates_evaluated=0,
                            primary_reason="DEPENDENCY_NOT_SATISFIED",
                        )
                    )
                    order_position_counter += 1
                remaining_tasks.clear()

        # 6. Calculate Standard Metrics
        metrics = MetricsCalculator.calculate(
            scheduled_tasks=scheduled_results,
            unscheduled_tasks=unscheduled_results,
            scores_map=scores_map,
            snapshot=snapshot,
        )

        overall_status = (
            SchedulerStatus.COMPLETED
            if len(unscheduled_results) == 0
            else SchedulerStatus.COMPLETED_WITH_UNSCHEDULED_TASKS
        )

        exec_time_ms = round((time.perf_counter() - start_time_perf) * 1000, 2)

        return ScheduleResult(
            schedule_id=schedule_id,
            scheduler_type=self.scheduler_type,
            scheduler_version=self.scheduler_version,
            scenario_id=snapshot.scenario_id,
            snapshot_id=snapshot.snapshot_id,
            planning_start=snapshot.horizon.start,
            planning_end=snapshot.horizon.end,
            status=overall_status,
            scheduled_tasks=scheduled_results,
            unscheduled_tasks=unscheduled_results,
            metrics=metrics,
            configuration=config.model_dump(),
            execution_time_ms=exec_time_ms,
            decision_trace=decision_traces,
        )
