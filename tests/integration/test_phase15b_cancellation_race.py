"""Phase 15B Integration Tests: Cancellation Race Condition against Real Database.

Verifies:
- Cancellation of an active planning run transitions: RUNNING -> CANCEL_REQUESTED -> CANCELLED
- Worker cooperative cancellation checkpoints before solve and before validation
- After cancellation, worker NEVER transitions to VALIDATING or COMPLETED
- Worker does NOT transition to FAILED due to cancellation
- Persisted database state remains consistent and terminal
"""

import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from backend.app.config import get_settings
from backend.app.services.planning_worker import PlanningRunWorker
from backend.app.db.models.planning_run import PlanningRunModel
from backend.app.repositories.planning_run_repo import (
    PlanningRunRepository,
    IllegalStateTransitionError,
)
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
    await db_session.execute(delete(PlanningRunModel))
    await db_session.commit()
    yield
    await db_session.execute(delete(PlanningRunModel))
    await db_session.commit()


@pytest.mark.asyncio
async def test_cancellation_before_solve_real_db(
    client: AsyncClient,
    db_session: AsyncSession,
    test_session_factory,
):
    """Client cancels run after worker claims it; worker cooperative check marks CANCELLED and aborts."""
    # 1. Submit run
    payload = {
        "scenario_id": "SCN-DEMO-001",
        "scheduler_type": "CP_SAT",
        "time_limit_seconds": 10.0,
    }
    resp_create = await client.post("/api/v1/planning-runs", json=payload)
    assert resp_create.status_code == 201
    run_id = resp_create.json()["run_id"]

    # 2. Worker claims run
    async with test_session_factory() as session:
        repo = PlanningRunRepository(session)
        claimed_run = await repo.claim_pending_run("TEST-CANCEL-WORKER-01")
        assert claimed_run is not None
        assert claimed_run.status == PlanningRunStatus.RUNNING.value

    # 3. Client issues cooperative cancellation request (RUNNING -> CANCEL_REQUESTED)
    resp_cancel = await client.post(f"/api/v1/planning-runs/{run_id}/cancel")
    assert resp_cancel.status_code == 200
    assert resp_cancel.json()["status"] == "CANCEL_REQUESTED"

    # Verify DB state is CANCEL_REQUESTED
    stmt = select(PlanningRunModel).where(PlanningRunModel.run_id == run_id)
    run_db = (await db_session.execute(stmt)).scalar_one()
    assert run_db.status == PlanningRunStatus.CANCEL_REQUESTED.value

    # 4. Worker continues processing claimed run
    worker = PlanningRunWorker(worker_id="TEST-CANCEL-WORKER-01", session_factory=test_session_factory)
    await worker._process_claimed_run(
        run_id=run_id,
        scenario_id=run_db.scenario_id,
        scheduler_type=run_db.scheduler_type,
        config_snapshot=dict(run_db.configuration_snapshot or {}),
        random_seed=run_db.random_seed,
    )

    # 5. Assert authoritative final DB state
    await db_session.refresh(run_db)
    assert run_db.status == PlanningRunStatus.CANCELLED.value, "Run must be marked CANCELLED!"
    assert run_db.stage == PlanningRunStage.CANCELLED.value
    assert run_db.completed_at is not None
    assert "Cancelled by user request" in (run_db.error_message or "")

    # Ensure worker did NOT leave the run in FAILED or VALIDATING
    assert run_db.status != PlanningRunStatus.FAILED.value
    assert run_db.status != PlanningRunStatus.VALIDATING.value
    assert run_db.status != PlanningRunStatus.COMPLETED.value


@pytest.mark.asyncio
async def test_cancellation_before_validation_real_db(
    client: AsyncClient,
    db_session: AsyncSession,
    test_session_factory,
):
    """Simulate user cancellation requested right before validation stage."""
    # 1. Submit and claim run
    payload = {
        "scenario_id": "SCN-DEMO-001",
        "scheduler_type": "PRIORITY_GREEDY",
    }
    resp_create = await client.post("/api/v1/planning-runs", json=payload)
    run_id = resp_create.json()["run_id"]

    async with test_session_factory() as session:
        repo = PlanningRunRepository(session)
        await repo.claim_pending_run("TEST-CANCEL-WORKER-02")
        await repo.update_stage(run_id, PlanningRunStage.SOLVING)

    # 2. While in SOLVING, client requests cancellation
    resp_cancel = await client.post(f"/api/v1/planning-runs/{run_id}/cancel")
    assert resp_cancel.status_code == 200
    assert resp_cancel.json()["status"] == "CANCEL_REQUESTED"

    # 3. Execute worker pre-validation logic by checking repo mark_cancelled
    async with test_session_factory() as session:
        repo = PlanningRunRepository(session)
        current_run = await repo.get_by_run_id(run_id)
        assert current_run.status == PlanningRunStatus.CANCEL_REQUESTED.value

        # Worker calls mark_cancelled instead of mark_validating
        cancelled_run = await repo.mark_cancelled(run_id, reason="Cancelled before validation.")
        assert cancelled_run.status == PlanningRunStatus.CANCELLED.value
        assert cancelled_run.stage == PlanningRunStage.CANCELLED.value

    # 4. Attempting to subsequently call mark_validating or mark_completed on CANCELLED run must fail
    async with test_session_factory() as session:
        repo = PlanningRunRepository(session)
        with pytest.raises(IllegalStateTransitionError):
            await repo.mark_validating(run_id)

        with pytest.raises(IllegalStateTransitionError):
            await repo.mark_completed(
                run_id=run_id,
                schedule_result={},
                result_summary={},
                validation_status="VALID",
                validation_fingerprint="abc",
                is_approvable=True,
                duration_ms=10.0,
            )
