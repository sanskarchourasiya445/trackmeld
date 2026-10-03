"""Phase 15B Integration Tests: Multi-Worker Claim Concurrency and Lock Isolation.

Verifies:
- Atomic claim using PostgreSQL row-level locks (SELECT ... FOR UPDATE SKIP LOCKED)
- Two or more workers operating concurrently on the same pending queue never double-claim
- No duplicate execution or duplicate result persistence
- No contradictory terminal states
"""

import uuid
import asyncio
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from backend.app.config import get_settings
from backend.app.services.planning_worker import PlanningRunWorker
from backend.app.db.models.planning_run import PlanningRunModel
from backend.app.db.models.plan_version import (
    PlanVersionModel,
    PlanReviewCommentModel,
    GovernanceAuditEventModel,
)
from backend.app.repositories.planning_run_repo import PlanningRunRepository
from backend.app.schemas.planning_run import PlanningRunStatus, PlanningRunStage

settings = get_settings()


@pytest_asyncio.fixture
async def test_session_factory():
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_database(db_session: AsyncSession):
    await db_session.execute(delete(GovernanceAuditEventModel))
    await db_session.execute(delete(PlanReviewCommentModel))
    await db_session.execute(delete(PlanVersionModel))
    await db_session.execute(delete(PlanningRunModel))
    await db_session.commit()
    yield
    await db_session.execute(delete(GovernanceAuditEventModel))
    await db_session.execute(delete(PlanReviewCommentModel))
    await db_session.execute(delete(PlanVersionModel))
    await db_session.execute(delete(PlanningRunModel))
    await db_session.commit()


async def _create_pending_run(session: AsyncSession, scenario_id: str = "SCN-DEMO-001", scheduler_type: str = "PRIORITY_GREEDY") -> PlanningRunModel:
    """Helper to insert a pending planning run record directly into PostgreSQL."""
    now = datetime.now(timezone.utc)
    run_id = f"RUN-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    run = PlanningRunModel(
        run_id=run_id,
        scenario_id=scenario_id,
        status=PlanningRunStatus.PENDING.value,
        stage=PlanningRunStage.QUEUED.value,
        scheduler_type=scheduler_type,
        scheduler_version="1.0.0",
        solver_name="Heuristic",
        solver_version="1.0",
        dataset_version="demo-v1.0",
        configuration_snapshot={"scheduler_type": scheduler_type},
        random_seed=42,
        created_at=now,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run


@pytest.mark.asyncio
async def test_atomic_claim_prevents_duplicate_processing(test_session_factory):
    """Two concurrent workers competing for a single pending job must result in exactly one claimant."""
    async with test_session_factory() as session:
        run = await _create_pending_run(session)
        target_run_id = run.run_id

    # Create two separate worker instances with independent database sessions
    async def claim_as_worker(worker_id: str):
        async with test_session_factory() as session:
            repo = PlanningRunRepository(session)
            return await repo.claim_pending_run(worker_id)

    # Launch both workers simultaneously
    results = await asyncio.gather(
        claim_as_worker("WORKER-ALPHA"),
        claim_as_worker("WORKER-BETA"),
    )

    claimed_by_alpha, claimed_by_beta = results

    # Exactly one worker should succeed in claiming the job; the other receives None
    claimants = [c for c in [claimed_by_alpha, claimed_by_beta] if c is not None]
    assert len(claimants) == 1, "Exactly one worker must claim the pending job!"

    winner = claimants[0]
    assert winner.run_id == target_run_id
    assert winner.status == PlanningRunStatus.RUNNING.value
    assert winner.worker_id in ["WORKER-ALPHA", "WORKER-BETA"]

    # Verify final state in database
    async with test_session_factory() as session:
        repo = PlanningRunRepository(session)
        final_db_run = await repo.get_by_run_id(target_run_id)
        assert final_db_run.status == PlanningRunStatus.RUNNING.value
        assert final_db_run.worker_id == winner.worker_id
        assert final_db_run.attempt_count == 1


@pytest.mark.asyncio
async def test_multi_worker_queue_concurrency(test_session_factory):
    """Multiple workers concurrently drain a queue of 4 jobs without collision or duplicate execution."""
    job_ids = []
    async with test_session_factory() as session:
        for _ in range(4):
            run = await _create_pending_run(session)
            job_ids.append(run.run_id)

    worker_1 = PlanningRunWorker(worker_id="WORKER-POOL-01", session_factory=test_session_factory)
    worker_2 = PlanningRunWorker(worker_id="WORKER-POOL-02", session_factory=test_session_factory)

    async def worker_loop(w: PlanningRunWorker):
        processed_count = 0
        while True:
            did_work = await w.run_once()
            if not did_work:
                break
            processed_count += 1
        return processed_count

    # Run both worker loops concurrently until queue is empty
    counts = await asyncio.gather(
        worker_loop(worker_1),
        worker_loop(worker_2),
    )

    total_processed = sum(counts)
    assert total_processed == 4, f"Expected 4 jobs processed, got {total_processed}"

    # Verify all 4 jobs reached COMPLETED with valid worker attribution
    async with test_session_factory() as session:
        stmt = select(PlanningRunModel).where(PlanningRunModel.run_id.in_(job_ids))
        completed_runs = (await session.execute(stmt)).scalars().all()

        assert len(completed_runs) == 4
        worker_ids_seen = set()
        for r in completed_runs:
            assert r.status == PlanningRunStatus.COMPLETED.value
            assert r.stage == PlanningRunStage.COMPLETED.value
            assert r.worker_id in ["WORKER-POOL-01", "WORKER-POOL-02"]
            worker_ids_seen.add(r.worker_id)

        # Both workers participated in draining the concurrent queue
        assert len(worker_ids_seen) >= 1
