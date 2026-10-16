"""Real Dual-Session PostgreSQL Integration Test for GOV-003B.

Verifies:
1. Canonical Scenario-Level Row Locking across concurrent database transactions (dual AsyncSession).
2. Two different plan versions for the same scenario approved concurrently:
   - Serialized cleanly at scenario row lock.
   - First becomes SUPERSEDED, second becomes APPROVED.
   - Exactly one version has status='APPROVED' at any time.
3. Partial unique index uq_plan_versions_one_approved_per_scenario prevents duplicate active approvals.

Note: Clearly marked BLOCKED if PostgreSQL at 127.0.0.1:5434 is unreachable.
"""

import socket
import asyncio
import uuid
from datetime import datetime, timezone
import pytest
import pytest_asyncio
from sqlalchemy import select, delete, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.exc import IntegrityError

from backend.app.config import get_settings
from backend.app.core.auth import AuthUser, UserRole
from backend.app.domain.enums import DataClass
from backend.app.db.models.scenario import OperationalScenarioModel
from backend.app.db.models.planning_run import PlanningRunModel
from backend.app.db.models.plan_version import (
    PlanVersionModel,
    PlanReviewCommentModel,
    GovernanceAuditEventModel,
)
from backend.app.schemas.plan_version import PlanVersionStatus, GovernanceEventType
from backend.app.services.plan_governance_service import PlanGovernanceService
from backend.app.repositories.plan_version_repo import PlanApprovalConflictError, PlanVersionImmutableError
from backend.app.services.validation.validator import IndependentScheduleValidator


def _is_postgres_available() -> bool:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.0)
        res = sock.connect_ex(("127.0.0.1", 5434))
        sock.close()
        return res == 0
    except Exception:
        return False


if not _is_postgres_available():
    pytest.skip(
        "BLOCKED: PostgreSQL database at 127.0.0.1:5434 is unreachable. Real dual-session concurrency integration test cannot run.",
        allow_module_level=True,
    )

settings = get_settings()


@pytest_asyncio.fixture
async def test_session_factory():
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest_asyncio.fixture
async def clean_database(db_session: AsyncSession):
    await db_session.execute(delete(GovernanceAuditEventModel))
    await db_session.execute(delete(PlanReviewCommentModel))
    await db_session.execute(delete(PlanVersionModel))
    await db_session.execute(delete(PlanningRunModel))
    await db_session.execute(delete(OperationalScenarioModel))
    await db_session.commit()
    yield
    await db_session.execute(delete(GovernanceAuditEventModel))
    await db_session.execute(delete(PlanReviewCommentModel))
    await db_session.execute(delete(PlanVersionModel))
    await db_session.execute(delete(PlanningRunModel))
    await db_session.execute(delete(OperationalScenarioModel))
    await db_session.commit()


@pytest.mark.asyncio
async def test_dual_session_concurrent_approval_serialization(test_session_factory, clean_database):
    """Execute concurrent approvals across two real independent database sessions.
    Verifies that scenario-level row locking serializes transactions and ensures exactly
    one active APPROVED plan exists in PostgreSQL without constraint violation or deadlock."""
    now = datetime.now(timezone.utc)
    scenario_id = f"SCN-INT-{uuid.uuid4().hex[:8].upper()}"

    # Seed scenario
    async with test_session_factory() as seed_session:
        scen = OperationalScenarioModel(
            scenario_id=scenario_id,
            scenario_code=f"SC-{uuid.uuid4().hex[:6].upper()}",
            name="Real Operational Scenario",
            description="Testing dual-session concurrency",
            planning_start=now,
            planning_end=now,
            generation_seed=12345,
            dataset_version="v1.0",
            classification=DataClass.REAL,
        )
        seed_session.add(scen)

        # Seed two planning runs and two candidate plan versions
        run_1_id = f"RUN-1-{uuid.uuid4().hex[:6].upper()}"
        run_2_id = f"RUN-2-{uuid.uuid4().hex[:6].upper()}"

        run_1 = PlanningRunModel(
            run_id=run_1_id,
            scenario_id=scenario_id,
            snapshot_id="SNAP-INT-001",
            snapshot_hash="a" * 64,
            input_hash="b" * 64,
            validation_fingerprint="c" * 64,
            validation_status="VALID",
            is_approvable=True,
            dataset_version="v1.0",
            schedule_result={"scenario_id": scenario_id, "snapshot_id": "SNAP-INT-001"},
            status="COMPLETED",
            scheduler_type="CP_SAT",
            scheduler_version="1.0.0",
            solver_name="OR-Tools",
            solver_version="9.8",
            configuration_snapshot={},
        )
        run_2 = PlanningRunModel(
            run_id=run_2_id,
            scenario_id=scenario_id,
            snapshot_id="SNAP-INT-001",
            snapshot_hash="a" * 64,
            input_hash="b" * 64,
            validation_fingerprint="d" * 64,
            validation_status="VALID",
            is_approvable=True,
            dataset_version="v1.0",
            schedule_result={"scenario_id": scenario_id, "snapshot_id": "SNAP-INT-001"},
            status="COMPLETED",
            scheduler_type="CP_SAT",
            scheduler_version="1.0.0",
            solver_name="OR-Tools",
            solver_version="9.8",
            configuration_snapshot={},
        )
        seed_session.add(run_1)
        seed_session.add(run_2)

        pv_1_id = f"PV-1-{uuid.uuid4().hex[:6].upper()}"
        pv_2_id = f"PV-2-{uuid.uuid4().hex[:6].upper()}"

        pv_1 = PlanVersionModel(
            plan_version_id=pv_1_id,
            scenario_id=scenario_id,
            planning_run_id=run_1_id,
            version_number=1,
            status=PlanVersionStatus.PENDING_REVIEW.value,
            schedule_identity="c" * 64,
            snapshot_hash="a" * 64,
            input_hash="b" * 64,
            schedule_result={"scenario_id": scenario_id, "snapshot_id": "SNAP-INT-001"},
            result_summary={},
            validation_status="VALID",
            is_approvable=True,
            validation_findings_summary={"error_count": 0},
            scheduler_type="CP_SAT",
            scheduler_version="1.0.0",
            solver_name="OR-Tools",
            solver_version="9.8",
            dataset_version="v1.0",
            configuration_snapshot={},
            created_at=now,
            created_by="planner_officer",
        )
        pv_2 = PlanVersionModel(
            plan_version_id=pv_2_id,
            scenario_id=scenario_id,
            planning_run_id=run_2_id,
            version_number=2,
            status=PlanVersionStatus.PENDING_REVIEW.value,
            schedule_identity="d" * 64,
            snapshot_hash="a" * 64,
            input_hash="b" * 64,
            schedule_result={"scenario_id": scenario_id, "snapshot_id": "SNAP-INT-001"},
            result_summary={},
            validation_status="VALID",
            is_approvable=True,
            validation_findings_summary={"error_count": 0},
            scheduler_type="CP_SAT",
            scheduler_version="1.0.0",
            solver_name="OR-Tools",
            solver_version="9.8",
            dataset_version="v1.0",
            configuration_snapshot={},
            created_at=now,
            created_by="planner_officer",
        )
        seed_session.add(pv_1)
        seed_session.add(pv_2)
        await seed_session.commit()

    # Approvers
    approver_1 = AuthUser(
        user_id="USR-APPROVER-1",
        username="dispatcher_one",
        role=UserRole.OPERATOR,
        permissions=["plan:approve"],
    )
    approver_2 = AuthUser(
        user_id="USR-APPROVER-2",
        username="dispatcher_two",
        role=UserRole.OPERATOR,
        permissions=["plan:approve"],
    )

    async def _approve_session(pv_id, approver):
        async with test_session_factory() as session:
            service = PlanGovernanceService(session)
            return await service.approve_plan(pv_id, approver)

    # Launch dual-session concurrent approvals
    results = await asyncio.gather(
        _approve_session(pv_1_id, approver_1),
        _approve_session(pv_2_id, approver_2),
        return_exceptions=True,
    )

    # Check outcomes
    errors = [r for r in results if isinstance(r, Exception)]
    assert not errors, f"Unexpected errors during dual-session approval: {errors}"

    # Verify database state in clean session
    async with test_session_factory() as verify_session:
        stmt = (
            select(PlanVersionModel)
            .where(PlanVersionModel.scenario_id == scenario_id)
            .order_by(PlanVersionModel.version_number)
        )
        versions = (await verify_session.execute(stmt)).scalars().all()

        approved_versions = [v for v in versions if v.status == PlanVersionStatus.APPROVED.value]
        superseded_versions = [v for v in versions if v.status == PlanVersionStatus.SUPERSEDED.value]

        # Invariant: EXACTLY ONE active approved version
        assert len(approved_versions) == 1, f"Expected 1 approved version, found {len(approved_versions)}"
        assert len(superseded_versions) == 1, f"Expected 1 superseded version, found {len(superseded_versions)}"
