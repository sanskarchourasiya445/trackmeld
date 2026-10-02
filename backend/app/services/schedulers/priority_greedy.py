"""Priority-Greedy Deterministic Baseline Scheduler.

Orders tasks by descending priority score, with mandatory status, arrival, and task_id tie-breakers.
Evaluates earliest-feasible placement using Phase 4 compatibility.
"""

from typing import List, Dict, Any

from backend.app.domain.scheduling import (
    SchedulerType,
    SchedulerConfig,
    PriorityScore,
)
from backend.app.domain.planning_snapshot import PlanningSnapshot
from backend.app.services.schedulers.base import BaseScheduler
from backend.app.services.task_ordering import order_tasks_priority_greedy


class PriorityGreedyScheduler(BaseScheduler):
    """Priority-Greedy baseline scheduler."""

    def __init__(self, scheduler_version: str = "1.0.0") -> None:
        super().__init__(scheduler_type=SchedulerType.PRIORITY_GREEDY, scheduler_version=scheduler_version)

    def order_tasks(
        self,
        snapshot: PlanningSnapshot,
        scores_map: Dict[str, PriorityScore],
        config: SchedulerConfig,
    ) -> List[Any]:
        """Sort tasks by descending priority score, then mandatory, arrival, task_id."""
        return order_tasks_priority_greedy(snapshot.tasks, scores_map, snapshot.work_orders_map)
