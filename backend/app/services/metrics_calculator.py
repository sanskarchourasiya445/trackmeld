"""Deterministic metrics calculator for baseline and future CP-SAT schedules.

Guarantees:
1. Identical, pure calculation logic across FCFS, Priority-Greedy, and CP-SAT.
2. Defensible domain metrics with explicit zero-handling.
3. No hallucinated or unmodeled metrics.
"""

from typing import List, Dict, Optional
from datetime import datetime

from backend.app.domain.scheduling import (
    ScheduleMetrics,
    ScheduledTaskResult,
    UnscheduledTaskResult,
    PriorityScore,
)
from backend.app.domain.planning_snapshot import PlanningSnapshot


class MetricsCalculator:
    """Calculates standardized operational scheduling metrics."""

    @classmethod
    def calculate(
        cls,
        scheduled_tasks: List[ScheduledTaskResult],
        unscheduled_tasks: List[UnscheduledTaskResult],
        scores_map: Dict[str, PriorityScore],
        snapshot: PlanningSnapshot,
    ) -> ScheduleMetrics:
        """Compute standard metrics across scheduled and unscheduled results."""
        total_tasks = len(snapshot.tasks)
        num_scheduled = len(scheduled_tasks)
        num_unscheduled = len(unscheduled_tasks)

        completion_rate = (num_scheduled / total_tasks) if total_tasks > 0 else 0.0

        # Mandatory analysis
        mandatory_tasks_count = 0
        mandatory_scheduled_count = 0

        for t in snapshot.tasks:
            is_mand = getattr(t, "mandatory", False) if hasattr(t, "mandatory") else t.get("mandatory", False)
            if is_mand:
                mandatory_tasks_count += 1

        for s in scheduled_tasks:
            t = snapshot.tasks_map.get(s.task_id)
            if t:
                is_mand = getattr(t, "mandatory", False) if hasattr(t, "mandatory") else t.get("mandatory", False)
                if is_mand:
                    mandatory_scheduled_count += 1

        mandatory_unscheduled_count = mandatory_tasks_count - mandatory_scheduled_count

        # Denominator and edge-case semantics:
        # 1. If mandatory_tasks_count > 0:
        #    mandatory_completion_rate = mandatory_scheduled_count / mandatory_tasks_count
        # 2. If mandatory_tasks_count == 0 (scenario contains 0 mandatory tasks):
        #    - If num_scheduled == 0: zero work was scheduled. A result with zero scheduled
        #      tasks must never report a mandatory completion rate of 100%. Returns 0.0.
        #    - If num_scheduled > 0: tasks were scheduled and 0 mandatory constraints were
        #      violated. Vacuously satisfied -> 1.0 (100%).
        if mandatory_tasks_count > 0:
            mandatory_completion_rate = mandatory_scheduled_count / mandatory_tasks_count
        elif num_scheduled > 0:
            mandatory_completion_rate = 1.0
        else:
            mandatory_completion_rate = 0.0

        # Duration metrics
        total_scheduled_duration = sum(s.duration_minutes for s in scheduled_tasks)
        total_possession_duration = sum(
            int(s.possession_interval.duration_minutes)
            for s in scheduled_tasks
        )

        # Priority score capture metrics
        total_prio_avail = sum(score.total_score for score in scores_map.values())
        scheduled_prio = sum(
            scores_map[s.task_id].total_score
            for s in scheduled_tasks
            if s.task_id in scores_map
        )
        unscheduled_prio = sum(
            scores_map[u.task_id].total_score
            for u in unscheduled_tasks
            if u.task_id in scores_map
        )

        prio_capture_rate = (
            (scheduled_prio / total_prio_avail)
            if total_prio_avail > 0.0
            else 1.0
        )

        # Horizon bounds of placed work
        earliest_start: Optional[datetime] = None
        latest_end: Optional[datetime] = None

        if scheduled_tasks:
            earliest_start = min(s.interval.start for s in scheduled_tasks)
            latest_end = max(s.interval.end for s in scheduled_tasks)

        return ScheduleMetrics(
            total_tasks=total_tasks,
            scheduled_tasks=num_scheduled,
            unscheduled_tasks=num_unscheduled,
            completion_rate=round(completion_rate, 4),
            mandatory_tasks=mandatory_tasks_count,
            mandatory_scheduled=mandatory_scheduled_count,
            mandatory_unscheduled=mandatory_unscheduled_count,
            mandatory_completion_rate=round(mandatory_completion_rate, 4),
            total_scheduled_duration_minutes=total_scheduled_duration,
            total_possession_duration_minutes=total_possession_duration,
            total_priority_score_available=round(total_prio_avail, 4),
            scheduled_priority_score=round(scheduled_prio, 4),
            unscheduled_priority_score=round(unscheduled_prio, 4),
            priority_score_capture_rate=round(prio_capture_rate, 4),
            earliest_scheduled_start=earliest_start,
            latest_scheduled_end=latest_end,
        )
