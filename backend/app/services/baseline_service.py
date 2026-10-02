"""High-level Baseline Scheduling and Benchmarking Service.

Coordinates snapshot acquisition, scheduler execution, and side-by-side comparison.
"""

from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.domain.scheduling import (
    SchedulerType,
    SchedulerConfig,
    ScheduleResult,
    BenchmarkComparisonResult,
)
from backend.app.domain.planning_snapshot import PlanningSnapshot
from backend.app.services.planning_service import PlanningScenarioService
from backend.app.services.schedulers.fcfs import FCFSScheduler
from backend.app.services.schedulers.priority_greedy import PriorityGreedyScheduler


class BaselinePlanningService:
    """Manages baseline scheduling runs and fair benchmark comparisons."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.scenario_service = PlanningScenarioService(session)

    async def get_snapshot(self, scenario_id: str) -> Optional[PlanningSnapshot]:
        """Assemble an immutable planning snapshot for the given scenario."""
        bundle = await self.scenario_service.get_planning_bundle(scenario_id)
        if not bundle:
            return None
        return PlanningSnapshot.from_bundle(bundle)

    async def run_baseline_scheduler(
        self,
        scenario_id: str,
        scheduler_type: SchedulerType,
        config: Optional[SchedulerConfig] = None,
    ) -> Optional[ScheduleResult]:
        """Run a single baseline scheduler against a scenario."""
        snapshot = await self.get_snapshot(scenario_id)
        if not snapshot:
            return None

        if scheduler_type == SchedulerType.FCFS:
            scheduler = FCFSScheduler()
        elif scheduler_type == SchedulerType.PRIORITY_GREEDY:
            scheduler = PriorityGreedyScheduler()
        else:
            raise ValueError(f"Unsupported scheduler type for baseline: {scheduler_type}")

        return scheduler.schedule(snapshot, config)

    async def run_benchmark(
        self,
        scenario_id: str,
        config: Optional[SchedulerConfig] = None,
    ) -> Optional[BenchmarkComparisonResult]:
        """Run both FCFS and Priority-Greedy on the exact same snapshot and return side-by-side comparison."""
        snapshot = await self.get_snapshot(scenario_id)
        if not snapshot:
            return None

        fcfs_scheduler = FCFSScheduler()
        prio_scheduler = PriorityGreedyScheduler()

        # Both receive the EXACT same snapshot object
        fcfs_res = fcfs_scheduler.schedule(snapshot, config)
        prio_res = prio_scheduler.schedule(snapshot, config)

        comparison_table = [
            {
                "metric": "Total Tasks In Scope",
                "FCFS": fcfs_res.metrics.total_tasks,
                "Priority-Greedy": prio_res.metrics.total_tasks,
            },
            {
                "metric": "Scheduled Tasks Count",
                "FCFS": fcfs_res.metrics.scheduled_tasks,
                "Priority-Greedy": prio_res.metrics.scheduled_tasks,
            },
            {
                "metric": "Unscheduled Tasks Count",
                "FCFS": fcfs_res.metrics.unscheduled_tasks,
                "Priority-Greedy": prio_res.metrics.unscheduled_tasks,
            },
            {
                "metric": "Completion Rate",
                "FCFS": f"{fcfs_res.metrics.completion_rate * 100:.1f}%",
                "Priority-Greedy": f"{prio_res.metrics.completion_rate * 100:.1f}%",
            },
            {
                "metric": "Mandatory Tasks Total",
                "FCFS": fcfs_res.metrics.mandatory_tasks,
                "Priority-Greedy": prio_res.metrics.mandatory_tasks,
            },
            {
                "metric": "Mandatory Tasks Scheduled",
                "FCFS": fcfs_res.metrics.mandatory_scheduled,
                "Priority-Greedy": prio_res.metrics.mandatory_scheduled,
            },
            {
                "metric": "Mandatory Completion Rate",
                "FCFS": f"{fcfs_res.metrics.mandatory_completion_rate * 100:.1f}%",
                "Priority-Greedy": f"{prio_res.metrics.mandatory_completion_rate * 100:.1f}%",
            },
            {
                "metric": "Total Scheduled Work (mins)",
                "FCFS": fcfs_res.metrics.total_scheduled_duration_minutes,
                "Priority-Greedy": prio_res.metrics.total_scheduled_duration_minutes,
            },
            {
                "metric": "Total Track Possession (mins)",
                "FCFS": fcfs_res.metrics.total_possession_duration_minutes,
                "Priority-Greedy": prio_res.metrics.total_possession_duration_minutes,
            },
            {
                "metric": "Available Priority Points",
                "FCFS": round(fcfs_res.metrics.total_priority_score_available, 2),
                "Priority-Greedy": round(prio_res.metrics.total_priority_score_available, 2),
            },
            {
                "metric": "Captured Priority Points",
                "FCFS": round(fcfs_res.metrics.scheduled_priority_score, 2),
                "Priority-Greedy": round(prio_res.metrics.scheduled_priority_score, 2),
            },
            {
                "metric": "Priority Capture Rate",
                "FCFS": f"{fcfs_res.metrics.priority_score_capture_rate * 100:.1f}%",
                "Priority-Greedy": f"{prio_res.metrics.priority_score_capture_rate * 100:.1f}%",
            },
            {
                "metric": "Execution Latency (ms)",
                "FCFS": f"{fcfs_res.execution_time_ms} ms",
                "Priority-Greedy": f"{prio_res.execution_time_ms} ms",
            },
        ]

        return BenchmarkComparisonResult(
            scenario_id=scenario_id,
            snapshot_id=snapshot.snapshot_id,
            planning_start=snapshot.horizon.start,
            planning_end=snapshot.horizon.end,
            schedules={
                "FCFS": fcfs_res,
                "PRIORITY_GREEDY": prio_res,
            },
            comparison_table=comparison_table,
        )
