import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from backend.app.services.planning_worker import PlanningRunWorker
from backend.app.db.models.planning_run import PlanningRunModel
from backend.app.db.models.plan_version import (
    PlanVersionModel,
    PlanReviewCommentModel,
    GovernanceAuditEventModel,
)
from backend.app.repositories.planning_run_repo import PlanningRunRepository
from backend.app.config import get_settings

settings = get_settings()


@pytest_asyncio.fixture
async def test_session_factory():
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_planning_runs(db_session: AsyncSession):
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


@pytest.mark.asyncio
async def test_create_planning_run_api_queued_immediately(client: AsyncClient):
    """POST /api/v1/planning-runs queues job immediately and returns HTTP 201."""
    payload = {
        "scenario_id": "SCN-DEMO-001",
        "scheduler_type": "CP_SAT",
        "time_limit_seconds": 10.0,
        "num_search_workers": 1,
        "random_seed": 0,
        "validate_after_solve": True,
    }
    response = await client.post("/api/v1/planning-runs", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["run_id"].startswith("RUN-")
    assert data["scenario_id"] == "SCN-DEMO-001"
    assert data["status"] == "PENDING"
    assert data["stage"] == "QUEUED"
    assert data["scheduler_type"] == "CP_SAT"
    assert "status_url" in data


@pytest.mark.asyncio
async def test_get_planning_run_details_and_not_found(client: AsyncClient):
    """GET /api/v1/planning-runs/{run_id} returns details or 404."""
    # 1. 404 on nonexistent run
    resp_404 = await client.get("/api/v1/planning-runs/RUN-DOES-NOT-EXIST")
    assert resp_404.status_code == 404

    # 2. 200 on created run
    payload = {"scenario_id": "SCN-DEMO-001", "scheduler_type": "PRIORITY_GREEDY"}
    resp_create = await client.post("/api/v1/planning-runs", json=payload)
    assert resp_create.status_code == 201
    run_id = resp_create.json()["run_id"]

    resp_get = await client.get(f"/api/v1/planning-runs/{run_id}")
    assert resp_get.status_code == 200
    detail = resp_get.json()
    assert detail["run_id"] == run_id
    assert detail["status"] == "PENDING"
    assert detail["stage"] == "QUEUED"
    assert detail["progress"]["stage"] == "QUEUED"


@pytest.mark.asyncio
async def test_client_idempotency_key(client: AsyncClient):
    """Submitting multiple requests with identical Idempotency-Key returns same run."""
    key = "idem-test-key-2026-xyz"
    payload = {
        "scenario_id": "SCN-DEMO-001",
        "scheduler_type": "FCFS",
        "idempotency_key": key,
    }
    resp1 = await client.post("/api/v1/planning-runs", json=payload)
    assert resp1.status_code == 201
    run_id_1 = resp1.json()["run_id"]

    resp2 = await client.post("/api/v1/planning-runs", json=payload)
    assert resp2.status_code == 201
    run_id_2 = resp2.json()["run_id"]

    # Must be identical run
    assert run_id_1 == run_id_2


@pytest.mark.asyncio
async def test_worker_execution_e2e(client: AsyncClient, test_session_factory):
    """End-to-End: Submit run, background worker processes and independently validates it."""
    # 1. Submit run
    payload = {
        "scenario_id": "SCN-DEMO-001",
        "scheduler_type": "CP_SAT",
        "time_limit_seconds": 10.0,
        "num_search_workers": 1,
        "random_seed": 0,
        "validate_after_solve": True,
    }
    resp_create = await client.post("/api/v1/planning-runs", json=payload)
    assert resp_create.status_code == 201
    run_id = resp_create.json()["run_id"]

    # 2. Worker executes job
    worker = PlanningRunWorker(worker_id="TEST-WORKER-01", session_factory=test_session_factory)
    processed = await worker.run_once()
    assert processed is True

    # 3. Verify completed run details
    resp_detail = await client.get(f"/api/v1/planning-runs/{run_id}")
    assert resp_detail.status_code == 200
    data = resp_detail.json()

    assert data["status"] == "COMPLETED"
    assert data["stage"] == "COMPLETED"
    assert data["worker_id"] == "TEST-WORKER-01"
    assert len(data["snapshot_hash"]) == 64
    assert len(data["input_hash"]) == 64
    assert data["validation_status"] == "VALID"
    assert data["is_approvable"] is True
    assert data["execution_duration_ms"] > 0

    assert data["result_summary"]["total_tasks"] == 30
    assert data["result_summary"]["scheduled_tasks"] > 0
    assert data["result_url"] is not None

    # 4. Verify ScheduleResult retrieval endpoint
    resp_res = await client.get(f"/api/v1/planning-runs/{run_id}/result")
    assert resp_res.status_code == 200
    sched = resp_res.json()
    assert sched["scheduler_type"] == "CP_SAT"
    assert "validation" in sched
    assert sched["validation"]["status"] == "VALID"
    assert len(sched["scheduled_tasks"]) > 0


@pytest.mark.asyncio
async def test_result_endpoint_not_completed_returns_409(client: AsyncClient):
    """GET /api/v1/planning-runs/{run_id}/result returns 409 if run is not completed yet."""
    payload = {"scenario_id": "SCN-DEMO-001", "scheduler_type": "FCFS"}
    resp_create = await client.post("/api/v1/planning-runs", json=payload)
    run_id = resp_create.json()["run_id"]

    resp_res = await client.get(f"/api/v1/planning-runs/{run_id}/result")
    assert resp_res.status_code == 409
    assert resp_res.json()["error"]["code"] == "PLANNING_RUN_NOT_COMPLETED"


@pytest.mark.asyncio
async def test_list_planning_runs_filtering_and_pagination(client: AsyncClient):
    """GET /api/v1/planning-runs supports pagination and scenario filtering."""
    resp = await client.get("/api/v1/planning-runs?scenario_id=SCN-DEMO-001&limit=5")
    assert resp.status_code == 200
    runs = resp.json()
    assert isinstance(runs, list)
    assert "x-total-count" in resp.headers


@pytest.mark.asyncio
async def test_cancellation_flow(client: AsyncClient):
    """POST /api/v1/planning-runs/{run_id}/cancel cancels a pending run."""
    payload = {"scenario_id": "SCN-DEMO-001", "scheduler_type": "FCFS"}
    resp_create = await client.post("/api/v1/planning-runs", json=payload)
    run_id = resp_create.json()["run_id"]

    resp_cancel = await client.post(f"/api/v1/planning-runs/{run_id}/cancel")
    assert resp_cancel.status_code == 200
    data = resp_cancel.json()
    assert data["status"] == "CANCELLED"
    assert data["stage"] == "CANCELLED"


@pytest.mark.asyncio
async def test_worker_atomic_job_claiming_concurrency(client: AsyncClient, test_session_factory):
    """Multiple workers claiming jobs simultaneously: exactly one worker gets the job."""
    payload = {"scenario_id": "SCN-DEMO-001", "scheduler_type": "PRIORITY_GREEDY"}
    resp_create = await client.post("/api/v1/planning-runs", json=payload)
    run_id = resp_create.json()["run_id"]

    async with test_session_factory() as session1, test_session_factory() as session2:
        repo1 = PlanningRunRepository(session1)
        repo2 = PlanningRunRepository(session2)

        # Worker 1 claims
        claim1 = await repo1.claim_pending_run("WORKER-CONC-01")
        assert claim1 is not None
        assert claim1.run_id == run_id
        assert claim1.worker_id == "WORKER-CONC-01"

        # Worker 2 attempts to claim
        claim2 = await repo2.claim_pending_run("WORKER-CONC-02")
        # Should not claim the same run (claim2 is None or a different run)
        if claim2 is not None:
            assert claim2.run_id != run_id
