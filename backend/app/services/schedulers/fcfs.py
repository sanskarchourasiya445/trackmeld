"""First-Come, First-Served (FCFS) Deterministic Baseline Scheduler.

Orders tasks by request / window arrival timestamp, with task_id as deterministic tie-breaker.
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
from backend.app.services.task_ordering import order_tasks_fcfs


class FCFSScheduler(BaseScheduler):
    """First-Come, First-Served baseline scheduler."""

    def __init__(self, scheduler_version: str = "1.0.0") -> None:
        super().__init__(scheduler_type=SchedulerType.FCFS, scheduler_version=scheduler_version)

    def order_tasks(
        self,
        snapshot: PlanningSnapshot,
        scores_map: Dict[str, PriorityScore],
        config: SchedulerConfig,
    ) -> List[Any]:
        """Sort tasks by arrival / window_start timestamp with task_id tie-breaker."""
        return order_tasks_fcfs(snapshot.tasks, snapshot.work_orders_map)
