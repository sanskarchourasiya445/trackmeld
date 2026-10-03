"""Asynchronous worker for durable background execution of planning runs.

ARCHITECTURAL PRINCIPLES:
1. One planning run has at most one worker owner at a time (atomic claim via FOR UPDATE SKIP LOCKED).
2. Database transactions are NEVER held open during long CPU-bound solver solves.
3. CPU-bound solvers execute in worker thread pool via asyncio.to_thread, never blocking the event loop.
4. Independent validation (Phase 7) and root-cause diagnostics are executed before marking complete.
5. All completed results and validation certificates are immutable.
"""

import sys
import uuid
import time
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import AsyncSessionLocal
from backend.app.schemas.planning_run import PlanningRunStatus, PlanningRunStage
from backend.app.repositories.planning_run_repo import PlanningRunRepository
from backend.app.domain.scheduling import (
    SchedulerType,
    SchedulerStatus,
    PriorityConfig,
    ScheduleResult,
)
from backend.app.domain.planning_snapshot import PlanningSnapshot
from backend.app.services.planning_service import PlanningScenarioService
from backend.app.services.schedulers import FCFSScheduler, PriorityGreedyScheduler
from backend.app.services.optimization.solver_config import OptimizationConfig
from backend.app.services.optimization.cp_sat_solver import CPSATSolver
from backend.app.services.validation.validator import IndependentScheduleValidator
from backend.app.services.validation.diagnostics import UnscheduledTaskDiagnosticsService
from backend.app.config import get_settings

logger = logging.getLogger("trackmeld.worker")


class PlanningRunWorker:
    """Worker responsible for claiming and executing planning jobs asynchronously."""

    def __init__(
        self,
        worker_id: Optional[str] = None,
        poll_interval: Optional[float] = None,
        heartbeat_interval: Optional[float] = None,
        stale_timeout: Optional[float] = None,
        session_factory: Optional[Any] = None,
    ) -> None:
        self.settings = get_settings()
        self.worker_id = worker_id or f"WORKER-{uuid.uuid4().hex[:8].upper()}"
        self.poll_interval = poll_interval or getattr(self.settings, "WORKER_POLL_INTERVAL_SECONDS", 1.0)
        self.heartbeat_interval = heartbeat_interval or getattr(self.settings, "WORKER_HEARTBEAT_INTERVAL_SECONDS", 5.0)
        self.stale_timeout = stale_timeout or getattr(self.settings, "WORKER_STALE_TIMEOUT_SECONDS", 30.0)
        self.session_factory = session_factory or AsyncSessionLocal
        self._running = False

    async def run_once(self) -> bool:
        """Poll and claim one pending job. Returns True if a job was processed."""
        # 1. Atomic claim in a short transaction
        async with self.session_factory() as session:
            repo = PlanningRunRepository(session)
            run = await repo.claim_pending_run(self.worker_id)
            if not run:
                # Optionally check for stale runs
                stale_runs = await repo.find_stale_runs(self.stale_timeout)
                for s in stale_runs:
                    logger.warning(f"Detected stale run '{s.run_id}' with expired heartbeat. Marking TIMED_OUT.")
                    await repo.mark_timed_out(s.run_id, f"Worker heartbeat timed out after {self.stale_timeout}s.")
                return False

            run_id = run.run_id
            scenario_id = run.scenario_id
            scheduler_type = run.scheduler_type
            config_snapshot = dict(run.configuration_snapshot)
            random_seed = run.random_seed

        logger.info(f"[{self.worker_id}] Claimed pending run '{run_id}' for scenario '{scenario_id}' ({scheduler_type}).")

        # 2. Execute job lifecycle
        await self._process_claimed_run(
            run_id=run_id,
            scenario_id=scenario_id,
            scheduler_type=scheduler_type,
            config_snapshot=config_snapshot,
            random_seed=random_seed,
        )
        return True

    async def _process_claimed_run(
        self,
        run_id: str,
        scenario_id: str,
        scheduler_type: str,
        config_snapshot: Dict[str, Any],
        random_seed: int,
    ) -> None:
        """Execute the planning, validation, and persistence pipeline for a claimed run."""
        start_time = time.perf_counter()
        heartbeat_task: Optional[asyncio.Task] = None

        try:
            # -----------------------------------------------------------------
            # Step A: Load immutable PlanningSnapshot
            # -----------------------------------------------------------------
            async with self.session_factory() as session:
                repo = PlanningRunRepository(session)
                await repo.update_stage(run_id, PlanningRunStage.LOADING_SNAPSHOT)

                scenario_service = PlanningScenarioService(session)
                bundle = await scenario_service.get_planning_bundle(scenario_id)
                if not bundle:
                    await repo.mark_failed(
                        run_id=run_id,
                        error_code="SCENARIO_NOT_FOUND",
                        error_message=f"Operational scenario '{scenario_id}' could not be loaded from database.",
                        stage=PlanningRunStage.LOADING_SNAPSHOT,
                    )
                    return

                snapshot = PlanningSnapshot.from_bundle(bundle)
                snap_hash = snapshot.compute_snapshot_hash()
                input_hash = snapshot.compute_input_hash(config_snapshot, seed=random_seed)

                # Persist snapshot metadata and update stage to SOLVING
                await repo.update_stage(
                    run_id,
                    PlanningRunStage.SOLVING,
                    extra_fields={
                        "snapshot_id": snapshot.snapshot_id,
                        "snapshot_hash": snap_hash,
                        "input_hash": input_hash,
                        "planning_start": snapshot.horizon.start,
                        "planning_end": snapshot.horizon.end,
                    },
                )

            # Check cancellation before starting scheduler
            async with self.session_factory() as session:
                repo = PlanningRunRepository(session)
                current_run = await repo.get_by_run_id(run_id)
                if current_run and current_run.status == PlanningRunStatus.CANCEL_REQUESTED.value:
                    logger.info(f"[{self.worker_id}] Run '{run_id}' has CANCEL_REQUESTED before solve. Aborting and marking CANCELLED.")
                    await repo.mark_cancelled(run_id, reason="Cancelled by user request before optimization.")
                    return

            # -----------------------------------------------------------------
            # Step B: Start background heartbeat task
            # -----------------------------------------------------------------
            heartbeat_task = asyncio.create_task(self._heartbeat_loop(run_id))

            # -----------------------------------------------------------------
            # Step C: Execute CPU-bound Scheduler outside DB transaction
            # -----------------------------------------------------------------
            logger.info(f"[{self.worker_id}] Executing {scheduler_type} optimization for run '{run_id}' in thread pool...")
            schedule_result = await asyncio.to_thread(
                self._execute_scheduler_sync,
                scheduler_type=scheduler_type,
                snapshot=snapshot,
                config_snapshot=config_snapshot,
                random_seed=random_seed,
            )

            # -----------------------------------------------------------------
            # Step D: Independent Validation & Root-Cause Diagnostics
            # -----------------------------------------------------------------
            # Check authoritative state before entering VALIDATING
            async with self.session_factory() as session:
                repo = PlanningRunRepository(session)
                current_run = await repo.get_by_run_id(run_id)
                if not current_run:
                    return
                if current_run.status == PlanningRunStatus.CANCEL_REQUESTED.value:
                    logger.info(f"[{self.worker_id}] Run '{run_id}' has CANCEL_REQUESTED after solve. Aborting validation and marking CANCELLED.")
                    await repo.mark_cancelled(run_id, reason="Cancelled by user request before validation.")
                    return
                await repo.mark_validating(run_id)

            logger.info(f"[{self.worker_id}] Running Phase 7 Independent Validator for run '{run_id}'...")
            validation_res = await asyncio.to_thread(
                IndependentScheduleValidator.validate,
                snapshot,
                schedule_result,
            )

            diagnostics_summary = None
            if schedule_result.unscheduled_tasks:
                logger.info(f"[{self.worker_id}] Running diagnostics for {len(schedule_result.unscheduled_tasks)} unplaced tasks...")
                diag_service = UnscheduledTaskDiagnosticsService(snapshot, schedule_result)
                diag_report = await asyncio.to_thread(diag_service.diagnose_all)
                diagnostics_summary = diag_report.model_dump(mode="json")

            # Attach validation to ScheduleResult
            schedule_result.validation = validation_res.model_dump(mode="json")

            # -----------------------------------------------------------------
            # Step E: Persist Results and Mark Complete
            # -----------------------------------------------------------------
            elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            result_summary = {
                "schedule_id": schedule_result.schedule_id,
                "status": schedule_result.status.value,
                "total_tasks": schedule_result.metrics.total_tasks,
                "scheduled_tasks": schedule_result.metrics.scheduled_tasks,
                "unscheduled_tasks": schedule_result.metrics.unscheduled_tasks,
                "completion_rate": schedule_result.metrics.completion_rate,
                "mandatory_completion_rate": schedule_result.metrics.mandatory_completion_rate,
                "priority_score_capture_rate": schedule_result.metrics.priority_score_capture_rate,
                "scheduled_priority_score": schedule_result.metrics.scheduled_priority_score,
                "total_scheduled_duration_minutes": schedule_result.metrics.total_scheduled_duration_minutes,
                "total_possession_duration_minutes": schedule_result.metrics.total_possession_duration_minutes,
                "earliest_scheduled_start": schedule_result.metrics.earliest_scheduled_start.isoformat() if schedule_result.metrics.earliest_scheduled_start else None,
                "latest_scheduled_end": schedule_result.metrics.latest_scheduled_end.isoformat() if schedule_result.metrics.latest_scheduled_end else None,
            }

            validation_findings_summary = {
                "error_count": validation_res.error_count,
                "warning_count": validation_res.warning_count,
                "info_count": validation_res.info_count,
                "checks_executed": validation_res.checks_executed,
                "top_finding_codes": [f.code for f in validation_res.findings[:5]],
            }

            async with self.session_factory() as session:
                repo = PlanningRunRepository(session)
                current_run = await repo.get_by_run_id(run_id)
                if current_run and current_run.status == PlanningRunStatus.CANCEL_REQUESTED.value:
                    logger.info(f"[{self.worker_id}] Run '{run_id}' has CANCEL_REQUESTED before completion. Marking CANCELLED.")
                    await repo.mark_cancelled(run_id, reason="Cancelled by user request before persistence.")
                    return

                await repo.mark_completed(
                    run_id=run_id,
                    schedule_result=schedule_result.model_dump(mode="json"),
                    result_summary=result_summary,
                    validation_status=validation_res.status.value,
                    validation_fingerprint=validation_res.schedule_identity,
                    is_approvable=validation_res.is_approvable,
                    duration_ms=elapsed_ms,
                    validation_findings_summary=validation_findings_summary,
                    diagnostics_summary=diagnostics_summary,
                )

            logger.info(
                f"[{self.worker_id}] Run '{run_id}' COMPLETED in {elapsed_ms}ms "
                f"(Status: {schedule_result.status.value}, Validation: {validation_res.status.value}, "
                f"Approvable: {validation_res.is_approvable})."
            )

        except Exception as e:
            logger.exception(f"[{self.worker_id}] Execution failed for run '{run_id}': {e}")
            try:
                async with self.session_factory() as session:
                    repo = PlanningRunRepository(session)
                    current_run = await repo.get_by_run_id(run_id)
                    if current_run and current_run.status in [PlanningRunStatus.CANCELLED.value, PlanningRunStatus.CANCEL_REQUESTED.value]:
                        await repo.mark_cancelled(run_id, reason=f"Cancelled during exception handling: {e}")
                    else:
                        await repo.mark_failed(
                            run_id=run_id,
                            error_code="WORKER_EXECUTION_EXCEPTION",
                            error_message=str(e),
                            stage=PlanningRunStage.FAILED,
                            error_details={"exception_type": type(e).__name__},
                        )
            except Exception as mark_err:
                logger.error(f"[{self.worker_id}] Failed to record run failure status: {mark_err}")
        finally:
            if heartbeat_task and not heartbeat_task.done():
                heartbeat_task.cancel()

    def _execute_scheduler_sync(
        self,
        scheduler_type: str,
        snapshot: PlanningSnapshot,
        config_snapshot: Dict[str, Any],
        random_seed: int,
    ) -> ScheduleResult:
        """Synchronously execute requested algorithm strategy inside thread pool."""
        sched_type = SchedulerType(scheduler_type)

        if sched_type == SchedulerType.FCFS:
            scheduler = FCFSScheduler()
            return scheduler.schedule(snapshot)

        elif sched_type == SchedulerType.PRIORITY_GREEDY:
            prio_data = config_snapshot.get("priority_config") or {}
            prio_cfg = PriorityConfig.model_validate(prio_data) if prio_data else PriorityConfig()
            scheduler = PriorityGreedyScheduler()
            sched_cfg = SchedulerConfig(scheduler_type=SchedulerType.PRIORITY_GREEDY, priority_config=prio_cfg)
            return scheduler.schedule(snapshot, config=sched_cfg)

        elif sched_type == SchedulerType.CP_SAT:
            opt_data = config_snapshot.get("optimization_config") or {}
            time_limit = config_snapshot.get("time_limit_seconds") or opt_data.get("time_limit_seconds", 30.0)
            workers = config_snapshot.get("num_search_workers") or opt_data.get("num_search_workers", 1)
            seed = random_seed if random_seed is not None else opt_data.get("random_seed", 0)

            opt_cfg = OptimizationConfig(
                time_limit_seconds=float(time_limit),
                num_search_workers=int(workers),
                random_seed=int(seed),
            )
            solver = CPSATSolver(config=opt_cfg)
            return solver.solve(snapshot, config=opt_cfg)

        else:
            raise ValueError(f"Unsupported scheduler strategy: {scheduler_type}")

    async def _heartbeat_loop(self, run_id: str) -> None:
        """Periodic background task updating run heartbeat while active."""
        try:
            while True:
                await asyncio.sleep(self.heartbeat_interval)
                async with self.session_factory() as session:
                    repo = PlanningRunRepository(session)
                    await repo.heartbeat(run_id, self.worker_id)
        except asyncio.CancelledError:
            pass

    async def start(self) -> None:
        """Start worker polling loop."""
        self._running = True
        logger.info(f"Starting PlanningRunWorker '{self.worker_id}' (poll={self.poll_interval}s, heartbeat={self.heartbeat_interval}s)...")
        while self._running:
            try:
                processed = await self.run_once()
                if not processed:
                    await asyncio.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                await asyncio.sleep(self.poll_interval)

    def stop(self) -> None:
        """Signal worker to stop gracefully."""
        logger.info(f"Stopping PlanningRunWorker '{self.worker_id}'...")
        self._running = False
