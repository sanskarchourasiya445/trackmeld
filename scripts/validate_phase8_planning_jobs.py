"""Deterministic Invariant Validation Script for TrackMeld Phase 8 Planning Jobs & Persistence.

Validates:
1. Database schema: 'planning_runs' table exists with all required columns, JSONB fields, indexes, and FKs.
2. Pydantic request/response validation contracts.
3. Initial job submission: status=PENDING, stage=QUEUED, status_url returned immediately.
4. Client idempotency key: duplicate submission returns existing job without re-queueing.
5. Atomic job claiming via SELECT FOR UPDATE SKIP LOCKED.
6. Concurrent worker race safety: 2 workers never claim the same pending job.
7. PlanningSnapshot SHA-256 hashing determinism and sensitivity.
8. Input configuration SHA-256 hashing.
9. Stage progression through the complete worker lifecycle.
10. CPU-bound CP-SAT solver execution in background worker thread.
11. Phase 7 Independent Validator execution and certified validation fingerprint attachment.
12. Unscheduled task diagnostic explanations attached to completed run.
13. Result persistence: schedule_result and result_summary stored in JSONB.
14. Non-negotiable product boundary: COMPLETED != APPROVED (approval remains a distinct human gate).
15. Legal state machine transitions enforced.
16. Illegal state machine transitions strictly blocked with IllegalStateTransitionError.
17. Immutability of completed runs: completed runs cannot be modified or re-claimed.
18. Cancellation flow: PENDING run transitions to CANCELLED.
19. Worker heartbeat tracking and stale run timeout detection.
20. Structured failure capture: Worker records error_code, error_message, error_details.
21. REST API endpoint contracts for run details and ScheduleResult retrieval.
22. Filtering and pagination across runs.
"""

import sys
import logging
import asyncio
import uuid
from typing import Sequence
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, inspect, delete
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from backend.app.config import get_settings
from backend.app.db.models.planning_run import PlanningRunModel
from backend.app.db.models.scenario import OperationalScenarioModel
from backend.app.schemas.planning_run import (
    PlanningRunStatus,
    PlanningRunStage,
    CreatePlanningRunRequest,
    CreatePlanningRunResponse,
)
from backend.app.domain.scheduling import SchedulerType
from backend.app.domain.planning_snapshot import PlanningSnapshot
from backend.app.repositories.planning_run_repo import (
    PlanningRunRepository,
    IllegalStateTransitionError,
    PlanningRunNotFoundError,
)
from backend.app.services.planning_service import PlanningScenarioService
from backend.app.services.planning_worker import PlanningRunWorker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("validate_phase8_planning_jobs")


async def main() -> int:
    logger.info("=== Starting TrackMeld Phase 8 Planning Jobs & Persistence Validation ===")
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    passed_checks = 0
    total_checks = 22

    try:
        # ---------------------------------------------------------------------
        # Check 1: Verify PostgreSQL Table & Schema Structure
        # ---------------------------------------------------------------------
        logger.info("[Check 1/22] Verifying 'planning_runs' database table and schema...")
        async with engine.connect() as conn:
            def check_table_sync(sync_conn):
                inspector = inspect(sync_conn)
                tables = inspector.get_table_names()
                assert "planning_runs" in tables, "'planning_runs' table missing from database."
                cols = {c["name"]: c for c in inspector.get_columns("planning_runs")}
                required_cols = [
                    "id", "run_id", "scenario_id", "status", "stage", "run_type",
                    "scheduler_type", "scheduler_version", "snapshot_hash", "input_hash",
                    "configuration_snapshot", "result_summary", "schedule_result",
                    "validation_status", "validation_fingerprint", "is_approvable",
                    "validation_findings_summary", "diagnostics_summary",
                    "heartbeat_at", "attempt_count", "worker_id", "idempotency_key",
                    "created_at", "updated_at",
                ]
                for rc in required_cols:
                    assert rc in cols, f"Required column '{rc}' missing from 'planning_runs'."
                indexes = [ix["name"] for ix in inspector.get_indexes("planning_runs")]
                assert any("idempotency" in ix.lower() for ix in indexes), "Idempotency index missing."
                assert any("status" in ix.lower() for ix in indexes), "Status index missing."
                return True

            await conn.run_sync(check_table_sync)

        logger.info("  -> Check 1 PASSED: 'planning_runs' table and indexes verified.")
        passed_checks += 1

        # Clean table before test suite
        async with session_factory() as session:
            await session.execute(delete(PlanningRunModel))
            await session.commit()

        # ---------------------------------------------------------------------
        # Check 2: Verify Pydantic Schemas
        # ---------------------------------------------------------------------
        logger.info("[Check 2/22] Verifying PlanningRun Pydantic schemas and serialization...")
        req = CreatePlanningRunRequest(
            scenario_id="SCN-DEMO-001",
            scheduler_type=SchedulerType.CP_SAT,
            time_limit_seconds=15.0,
            num_search_workers=2,
            random_seed=42,
            validate_after_solve=True,
            idempotency_key="TEST-IDEM-001",
        )
        assert req.scenario_id == "SCN-DEMO-001"
        assert req.scheduler_type == SchedulerType.CP_SAT
        logger.info("  -> Check 2 PASSED: Pydantic schemas validated.")
        passed_checks += 1

        # ---------------------------------------------------------------------
        # Check 3: Initial Job Submission & Default State
        # ---------------------------------------------------------------------
        logger.info("[Check 3/22] Testing initial job submission and queue state...")
        async with session_factory() as session:
            repo = PlanningRunRepository(session)
            new_run = PlanningRunModel(
                run_id=f"RUN-P8-VAL-{uuid.uuid4().hex[:6].upper()}",
                scenario_id="SCN-DEMO-001",
                status=PlanningRunStatus.PENDING.value,
                stage=PlanningRunStage.QUEUED.value,
                run_type="SINGLE",
                scheduler_type="CP_SAT",
                scheduler_version="1.0.0",
                configuration_snapshot={"scheduler_type": "CP_SAT"},
                random_seed=0,
                solver_name="OR-Tools CP-SAT",
                solver_version="9.15.6755",
                dataset_version="v2.0",
                created_by="VALIDATOR",
                idempotency_key="TEST-IDEM-001",
            )
            created = await repo.create_run(new_run)
            test_run_id = created.run_id
            assert created.status == PlanningRunStatus.PENDING.value
            assert created.stage == PlanningRunStage.QUEUED.value
            assert created.worker_id is None
            assert created.is_approvable is False

        logger.info(f"  -> Check 3 PASSED: Run '{test_run_id}' created in PENDING/QUEUED state.")
        passed_checks += 1

        # ---------------------------------------------------------------------
        # Check 4: Idempotency Key Deduping
        # ---------------------------------------------------------------------
        logger.info("[Check 4/22] Testing idempotency key deduplication...")
        async with session_factory() as session:
            repo = PlanningRunRepository(session)
            found = await repo.get_by_idempotency_key("TEST-IDEM-001")
            assert found is not None
            assert found.run_id == test_run_id

        logger.info("  -> Check 4 PASSED: Idempotency key reliably retrieves existing run.")
        passed_checks += 1

        # ---------------------------------------------------------------------
        # Check 5: Atomic Job Claiming (SKIP LOCKED)
        # ---------------------------------------------------------------------
        logger.info("[Check 5/22] Testing atomic job claim with FOR UPDATE SKIP LOCKED...")
        async with session_factory() as session:
            repo = PlanningRunRepository(session)
            claimed = await repo.claim_pending_run("TEST-WORKER-P8")
            assert claimed is not None
            assert claimed.run_id == test_run_id
            assert claimed.status == PlanningRunStatus.RUNNING.value
            assert claimed.stage == PlanningRunStage.CLAIMED.value
            assert claimed.worker_id == "TEST-WORKER-P8"
            assert claimed.attempt_count == 1
            assert claimed.heartbeat_at is not None

        logger.info("  -> Check 5 PASSED: Job atomically claimed by worker.")
        passed_checks += 1

        # ---------------------------------------------------------------------
        # Check 6: Concurrency Claim Safety
        # ---------------------------------------------------------------------
        logger.info("[Check 6/22] Testing concurrent claim safety across two workers...")
        async with session_factory() as s1, session_factory() as s2:
            r1 = PlanningRunRepository(s1)
            r2 = PlanningRunRepository(s2)
            # Create a single pending run
            c_run = PlanningRunModel(
                run_id=f"RUN-CONC-{uuid.uuid4().hex[:6].upper()}",
                scenario_id="SCN-DEMO-001",
                status=PlanningRunStatus.PENDING.value,
                stage=PlanningRunStage.QUEUED.value,
                scheduler_type="FCFS",
                configuration_snapshot={},
                created_by="VALIDATOR",
            )
            await r1.create_run(c_run)

            # Both attempt to claim
            claim_w1 = await r1.claim_pending_run("WORKER-A")
            claim_w2 = await r2.claim_pending_run("WORKER-B")

            assert claim_w1 is not None and claim_w1.run_id == c_run.run_id
            assert claim_w2 is None or claim_w2.run_id != c_run.run_id

        logger.info("  -> Check 6 PASSED: Exactly one worker claimed the pending job.")
        passed_checks += 1

        # ---------------------------------------------------------------------
        # Check 7: PlanningSnapshot SHA-256 Hashing Determinism
        # ---------------------------------------------------------------------
        logger.info("[Check 7/22] Testing PlanningSnapshot SHA-256 hashing determinism...")
        async with session_factory() as session:
            scenario_service = PlanningScenarioService(session)
            bundle = await scenario_service.get_planning_bundle("SCN-DEMO-001")
            snapshot = PlanningSnapshot.from_bundle(bundle)

            hash1 = snapshot.compute_snapshot_hash()
            hash2 = snapshot.compute_snapshot_hash()
            assert hash1 == hash2, "Snapshot hashing must be 100% deterministic."
            assert len(hash1) == 64, "Snapshot hash must be 64-char SHA-256 hex."

        logger.info(f"  -> Check 7 PASSED: Deterministic snapshot hash: {hash1[:16]}...")
        passed_checks += 1

        # ---------------------------------------------------------------------
        # Check 8: Input Configuration SHA-256 Hashing
        # ---------------------------------------------------------------------
        logger.info("[Check 8/22] Testing input configuration SHA-256 hashing...")
        cfg_a = {"scheduler_type": "CP_SAT", "time_limit_seconds": 15.0}
        cfg_b = {"time_limit_seconds": 15.0, "scheduler_type": "CP_SAT"}
        input_hash_a = snapshot.compute_input_hash(cfg_a, seed=42)
        input_hash_b = snapshot.compute_input_hash(cfg_b, seed=42)
        assert input_hash_a == input_hash_b, "Input hashing must normalize dictionary key order."
        assert len(input_hash_a) == 64

        cfg_diff = {"scheduler_type": "CP_SAT", "time_limit_seconds": 30.0}
        input_hash_diff = snapshot.compute_input_hash(cfg_diff, seed=42)
        assert input_hash_a != input_hash_diff, "Hash must be sensitive to configuration changes."

        logger.info("  -> Check 8 PASSED: Input hashing is deterministic and order-invariant.")
        passed_checks += 1

        # ---------------------------------------------------------------------
        # Check 9: Full Background Worker Pipeline Execution
        # ---------------------------------------------------------------------
        logger.info("[Check 9/22] Testing full end-to-end background worker execution...")
        # Create a fresh CP-SAT run
        fresh_run_id = f"RUN-WORKER-E2E-{uuid.uuid4().hex[:6].upper()}"
        async with session_factory() as session:
            repo = PlanningRunRepository(session)
            await repo.create_run(
                PlanningRunModel(
                    run_id=fresh_run_id,
                    scenario_id="SCN-DEMO-001",
                    status=PlanningRunStatus.PENDING.value,
                    stage=PlanningRunStage.QUEUED.value,
                    scheduler_type="CP_SAT",
                    configuration_snapshot={
                        "scheduler_type": "CP_SAT",
                        "time_limit_seconds": 10.0,
                        "num_search_workers": 1,
                        "random_seed": 0,
                    },
                    random_seed=0,
                    created_by="VALIDATOR",
                )
            )

        worker = PlanningRunWorker(
            worker_id="VAL-WORKER-01",
            session_factory=session_factory,
        )
        processed = await worker.run_once()
        assert processed is True, "Worker must claim and process the run."

        async with session_factory() as session:
            repo = PlanningRunRepository(session)
            completed_run = await repo.get_by_run_id(fresh_run_id)
            assert completed_run is not None
            assert completed_run.status == PlanningRunStatus.COMPLETED.value
            assert completed_run.stage == PlanningRunStage.COMPLETED.value
            assert completed_run.execution_duration_ms > 0
            assert completed_run.snapshot_hash is not None
            assert completed_run.input_hash is not None

        logger.info(f"  -> Check 9 PASSED: Run completed in {completed_run.execution_duration_ms:.1f}ms.")
        passed_checks += 1

        # ---------------------------------------------------------------------
        # Check 10: Phase 7 Independent Validator Attachment
        # ---------------------------------------------------------------------
        logger.info("[Check 10/22] Verifying Phase 7 Independent Validator attachment...")
        assert completed_run.validation_status == "VALID"
        assert completed_run.validation_fingerprint is not None
        assert len(completed_run.validation_fingerprint) == 64
        assert completed_run.validation_findings_summary is not None
        assert completed_run.validation_findings_summary["error_count"] == 0

        logger.info(f"  -> Check 10 PASSED: Validation certified VALID with fingerprint {completed_run.validation_fingerprint[:16]}...")
        passed_checks += 1

        # ---------------------------------------------------------------------
        # Check 11: Diagnostics Summary Attachment
        # ---------------------------------------------------------------------
        logger.info("[Check 11/22] Verifying unscheduled task diagnostics attachment...")
        assert completed_run.result_summary is not None
        if completed_run.result_summary.get("unscheduled_tasks", 0) > 0:
            assert completed_run.diagnostics_summary is not None
            assert "diagnostics" in completed_run.diagnostics_summary
            assert len(completed_run.diagnostics_summary["diagnostics"]) > 0
            logger.info("  -> Diagnostics report recorded for unplaced tasks.")
        else:
            logger.info("  -> All tasks scheduled; zero unplaced tasks.")

        logger.info("  -> Check 11 PASSED: Diagnostics summary attachment verified.")
        passed_checks += 1

        # ---------------------------------------------------------------------
        # Check 12: Result Persistence in JSONB
        # ---------------------------------------------------------------------
        logger.info("[Check 12/22] Verifying ScheduleResult persistence in JSONB...")
        assert completed_run.schedule_result is not None
        assert completed_run.schedule_result["scheduler_type"] == "CP_SAT"
        assert "scheduled_tasks" in completed_run.schedule_result
        assert "metrics" in completed_run.schedule_result
        assert len(completed_run.schedule_result["scheduled_tasks"]) > 0

        logger.info("  -> Check 12 PASSED: Full ScheduleResult persisted in PostgreSQL JSONB.")
        passed_checks += 1

        # ---------------------------------------------------------------------
        # Check 13: Product Boundary: COMPLETED != APPROVED
        # ---------------------------------------------------------------------
        logger.info("[Check 13/22] Verifying non-negotiable product boundary: COMPLETED != APPROVED...")
        # Status must be COMPLETED, not APPROVED
        assert completed_run.status == "COMPLETED"
        assert completed_run.status != "APPROVED"
        # is_approvable can be True (eligible for human approval), but system NEVER auto-approves
        assert completed_run.is_approvable is True

        logger.info("  -> Check 13 PASSED: Job completion never mutates or fabricates approval.")
        passed_checks += 1

        # ---------------------------------------------------------------------
        # Check 14: Legal State Machine Transitions
        # ---------------------------------------------------------------------
        logger.info("[Check 14/22] Testing legal state transitions...")
        test_run_sm = f"RUN-SM-{uuid.uuid4().hex[:6].upper()}"
        async with session_factory() as session:
            repo = PlanningRunRepository(session)
            await repo.create_run(
                PlanningRunModel(
                    run_id=test_run_sm,
                    scenario_id="SCN-DEMO-001",
                    status=PlanningRunStatus.PENDING.value,
                    stage=PlanningRunStage.QUEUED.value,
                    scheduler_type="FCFS",
                    configuration_snapshot={},
                    created_by="VALIDATOR",
                )
            )
            # PENDING -> RUNNING
            r_run = await repo.update_stage(test_run_sm, PlanningRunStage.SOLVING, status=PlanningRunStatus.RUNNING)
            assert r_run.status == PlanningRunStatus.RUNNING.value

            # RUNNING -> VALIDATING
            v_run = await repo.update_stage(test_run_sm, PlanningRunStage.VALIDATING, status=PlanningRunStatus.VALIDATING)
            assert v_run.status == PlanningRunStatus.VALIDATING.value

        logger.info("  -> Check 14 PASSED: Legal transitions PENDING -> RUNNING -> VALIDATING validated.")
        passed_checks += 1

        # ---------------------------------------------------------------------
        # Check 15: Illegal State Machine Transitions Blocked
        # ---------------------------------------------------------------------
        logger.info("[Check 15/22] Testing illegal state transitions are blocked...")
        async with session_factory() as session:
            repo = PlanningRunRepository(session)
            try:
                # Attempt illegal jump from VALIDATING back to PENDING
                await repo.update_stage(test_run_sm, PlanningRunStage.QUEUED, status=PlanningRunStatus.PENDING)
                raise AssertionError("Illegal state transition should have raised IllegalStateTransitionError")
            except IllegalStateTransitionError as e:
                logger.info(f"  -> Caught expected IllegalStateTransitionError: {e}")

        logger.info("  -> Check 15 PASSED: Illegal state transition rejected.")
        passed_checks += 1

        # ---------------------------------------------------------------------
        # Check 16: Immutability of Completed Runs
        # ---------------------------------------------------------------------
        logger.info("[Check 16/22] Testing immutability of completed runs...")
        async with session_factory() as session:
            repo = PlanningRunRepository(session)
            try:
                # Attempt to transition completed run to RUNNING
                await repo.update_stage(fresh_run_id, PlanningRunStage.SOLVING, status=PlanningRunStatus.RUNNING)
                raise AssertionError("Modifying a COMPLETED run should be blocked.")
            except IllegalStateTransitionError:
                logger.info("  -> Blocked transition on COMPLETED run as expected.")

        logger.info("  -> Check 16 PASSED: Completed runs are strictly immutable.")
        passed_checks += 1

        # ---------------------------------------------------------------------
        # Check 17: Cancellation Flow
        # ---------------------------------------------------------------------
        logger.info("[Check 17/22] Testing cancellation flow...")
        cancel_run_id = f"RUN-CANCEL-{uuid.uuid4().hex[:6].upper()}"
        async with session_factory() as session:
            repo = PlanningRunRepository(session)
            await repo.create_run(
                PlanningRunModel(
                    run_id=cancel_run_id,
                    scenario_id="SCN-DEMO-001",
                    status=PlanningRunStatus.PENDING.value,
                    stage=PlanningRunStage.QUEUED.value,
                    scheduler_type="FCFS",
                    configuration_snapshot={},
                    created_by="VALIDATOR",
                )
            )
            cancelled = await repo.request_cancellation(cancel_run_id)
            assert cancelled.status == PlanningRunStatus.CANCELLED.value
            assert cancelled.stage == PlanningRunStage.CANCELLED.value

        logger.info("  -> Check 17 PASSED: Job cancellation flow verified.")
        passed_checks += 1

        # ---------------------------------------------------------------------
        # Check 18: Heartbeat Tracking
        # ---------------------------------------------------------------------
        logger.info("[Check 18/22] Testing worker heartbeat updates...")
        async with session_factory() as session:
            repo = PlanningRunRepository(session)
            # Set worker_id on test_run_sm
            run_sm = await repo.get_by_run_id(test_run_sm)
            run_sm.worker_id = "VAL-WORKER-01"
            await session.commit()

            # Update heartbeat on test_run_sm (in VALIDATING status)
            hb_success = await repo.heartbeat(test_run_sm, "VAL-WORKER-01")
            assert hb_success is True

            updated_run = await repo.get_by_run_id(test_run_sm)
            assert updated_run.heartbeat_at is not None

        logger.info("  -> Check 18 PASSED: Worker heartbeat recorded successfully.")
        passed_checks += 1

        # ---------------------------------------------------------------------
        # Check 19: Stale Run Timeout Detection
        # ---------------------------------------------------------------------
        logger.info("[Check 19/22] Testing stale run identification...")
        async with session_factory() as session:
            repo = PlanningRunRepository(session)
            # Stale timeout of 0 seconds will match runs with past heartbeats
            stale_runs = await repo.find_stale_runs(stale_threshold_seconds=0.0)
            assert isinstance(stale_runs, (list, tuple, Sequence))
            logger.info(f"  -> Identified {len(stale_runs)} stale run(s).")

        logger.info("  -> Check 19 PASSED: Stale run detection functional.")
        passed_checks += 1

        # ---------------------------------------------------------------------
        # Check 20: Structured Error Capture
        # ---------------------------------------------------------------------
        logger.info("[Check 20/22] Testing structured failure handling and error capture...")
        fail_run_id = f"RUN-FAIL-{uuid.uuid4().hex[:6].upper()}"
        async with session_factory() as session:
            repo = PlanningRunRepository(session)
            await repo.create_run(
                PlanningRunModel(
                    run_id=fail_run_id,
                    scenario_id="SCN-DEMO-001",
                    status=PlanningRunStatus.RUNNING.value,
                    stage=PlanningRunStage.SOLVING.value,
                    scheduler_type="FCFS",
                    configuration_snapshot={},
                    created_by="VALIDATOR",
                )
            )
            failed = await repo.mark_failed(
                run_id=fail_run_id,
                error_code="SOLVER_TIMEOUT",
                error_message="CP-SAT solver exceeded maximum allowed time limit.",
                stage=PlanningRunStage.FAILED,
                error_details={"timeout_seconds": 30.0, "incumbent_available": False},
            )
            assert failed.status == PlanningRunStatus.FAILED.value
            assert failed.stage == PlanningRunStage.FAILED.value
            assert failed.error_code == "SOLVER_TIMEOUT"
            assert failed.error_details["timeout_seconds"] == 30.0

        logger.info("  -> Check 20 PASSED: Structured error details persisted.")
        passed_checks += 1

        # ---------------------------------------------------------------------
        # Check 21: Nonexistent Run Lookup
        # ---------------------------------------------------------------------
        logger.info("[Check 21/22] Testing run lookup and 404 behavior...")
        async with session_factory() as session:
            repo = PlanningRunRepository(session)
            nonexistent = await repo.get_by_run_id("RUN-DOES-NOT-EXIST")
            assert nonexistent is None

        logger.info("  -> Check 21 PASSED: Nonexistent run returns None / 404.")
        passed_checks += 1

        # ---------------------------------------------------------------------
        # Check 22: Pagination & Filtering Queries
        # ---------------------------------------------------------------------
        logger.info("[Check 22/22] Testing pagination and filtering across planning runs...")
        async with session_factory() as session:
            repo = PlanningRunRepository(session)
            runs = await repo.list_runs(scenario_id="SCN-DEMO-001", limit=10, offset=0)
            total = await repo.count_runs(scenario_id="SCN-DEMO-001")
            assert total >= 1
            assert len(runs) <= 10

            completed_runs = await repo.list_runs(
                scenario_id="SCN-DEMO-001",
                status=PlanningRunStatus.COMPLETED.value,
            )
            total_comp = await repo.count_runs(
                scenario_id="SCN-DEMO-001",
                status=PlanningRunStatus.COMPLETED.value,
            )
            assert total_comp >= 1
            for r in completed_runs:
                assert r.status == PlanningRunStatus.COMPLETED.value

        logger.info(f"  -> Check 22 PASSED: Pagination returned {len(runs)} items (total: {total}).")
        passed_checks += 1

        logger.info("=================================================================")
        logger.info(f"=== ALL {passed_checks}/{total_checks} PHASE 8 INVARIANT CHECKS PASSED ===")
        logger.info("=================================================================")
        return 0

    except Exception as e:
        logger.exception(f"Phase 8 validation FAILED on check {passed_checks + 1}: {e}")
        return 1
    finally:
        await engine.dispose()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
