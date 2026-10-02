"""Deterministic task ordering strategies and dependency cycle validation.

Guarantees:
1. Pure deterministic ordering with explicit tie-breakers.
2. Topological cycle detection to prevent deadlocks or infinite loops.
3. Zero reliance on unstable iteration or database row order.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Set, Tuple
from collections import defaultdict, deque

from backend.app.domain.scheduling import PriorityScore
from backend.app.domain.planning_snapshot import PlanningSnapshot


class InvalidDependencyGraphError(ValueError):
    """Raised when circular or invalid task dependencies are detected."""
    pass


def detect_dependency_cycles(dependencies: List[Any], task_ids: Set[str]) -> List[List[str]]:
    """Detect directed cycles in the task dependency graph using Tarjan's/DFS algorithm."""
    adj = defaultdict(list)
    for dep in dependencies:
        pred = getattr(dep, "predecessor_task_id", None) or dep.get("predecessor_task_id")
        succ = getattr(dep, "successor_task_id", None) or dep.get("successor_task_id")
        if pred in task_ids and succ in task_ids:
            adj[pred].append(succ)

    # 0 = unvisited, 1 = visiting (on current path), 2 = visited
    state: Dict[str, int] = {t_id: 0 for t_id in task_ids}
    path: List[str] = []
    cycles: List[List[str]] = []

    def dfs(node: str):
        state[node] = 1
        path.append(node)

        for neighbor in adj[node]:
            if state[neighbor] == 1:
                # Cycle detected
                cycle_start_idx = path.index(neighbor)
                cycle = path[cycle_start_idx:] + [neighbor]
                cycles.append(cycle)
            elif state[neighbor] == 0:
                dfs(neighbor)

        path.pop()
        state[node] = 2

    for t_id in sorted(task_ids):
        if state[t_id] == 0:
            dfs(t_id)

    return cycles


def get_task_request_timestamp(task: Any, work_orders_map: Dict[str, Any]) -> datetime:
    """Extract deterministic request/arrival timestamp for FCFS ordering."""
    # Check task window_start
    w_start = getattr(task, "window_start", None) or task.get("window_start")
    if w_start:
        if isinstance(w_start, str):
            w_start = datetime.fromisoformat(w_start)
        if w_start.tzinfo is None:
            w_start = w_start.replace(tzinfo=timezone.utc)
        return w_start

    # Fallback to parent work order requested_execution_start
    wo_id = getattr(task, "work_order_id", None) or task.get("work_order_id")
    wo = work_orders_map.get(wo_id)
    if wo:
        wo_start = getattr(wo, "requested_execution_start", None) or wo.get("requested_execution_start")
        if wo_start:
            if isinstance(wo_start, str):
                wo_start = datetime.fromisoformat(wo_start)
            if wo_start.tzinfo is None:
                wo_start = wo_start.replace(tzinfo=timezone.utc)
            return wo_start

    return datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)


def order_tasks_fcfs(tasks: List[Any], work_orders_map: Dict[str, Any]) -> List[Any]:
    """Order tasks by First-Come, First-Served strategy with deterministic tie-breaking.
    
    Tie-breaking hierarchy:
    1. Primary: Request / window_start timestamp (ascending)
    2. Secondary: task_id (alphabetical ascending)
    """
    return sorted(
        tasks,
        key=lambda t: (
            get_task_request_timestamp(t, work_orders_map),
            getattr(t, "task_id", None) or t.get("task_id", "")
        )
    )


def order_tasks_priority_greedy(
    tasks: List[Any],
    scores_map: Dict[str, PriorityScore],
    work_orders_map: Dict[str, Any],
) -> List[Any]:
    """Order tasks by Priority-Greedy strategy with deterministic tie-breaking.
    
    Tie-breaking hierarchy:
    1. Primary: Priority score (descending)
    2. Secondary: Mandatory status (mandatory True first)
    3. Tertiary: Request / window_start timestamp (ascending)
    4. Quaternary / Final: task_id (alphabetical ascending)
    """
    def sort_key(t: Any) -> Tuple[float, int, datetime, str]:
        t_id = getattr(t, "task_id", None) or t.get("task_id", "")
        score = scores_map.get(t_id)
        total_score = score.total_score if score else 0.0

        is_mandatory = getattr(t, "mandatory", False) if hasattr(t, "mandatory") else t.get("mandatory", False)
        # 0 for mandatory=True (sorted first), 1 for mandatory=False
        mandatory_order = 0 if is_mandatory else 1

        req_time = get_task_request_timestamp(t, work_orders_map)
        return (-total_score, mandatory_order, req_time, t_id)

    return sorted(tasks, key=sort_key)
