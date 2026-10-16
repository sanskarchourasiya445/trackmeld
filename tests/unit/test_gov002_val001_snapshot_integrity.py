"""Unit regression tests for GOV-002 / VAL-001: Planning Snapshot and Validation Integrity.

Verifies:
1. Valid, unchanged snapshot and matching validation certificate succeeds formal approval.
2. Missing snapshot hash fails closed (PlanSnapshotIntegrityError).
3. Corrupted or malformed snapshot hash fails closed (PlanSnapshotIntegrityError).
4. Missing or malformed input hash and schedule identity fail closed.
5. Scenario ID mismatch between plan, source run, or schedule result fails closed.
6. Dataset version mismatch (stale snapshot against current scenario) fails closed.
7. Snapshot hash tampering against source run fails closed.
8. Plan mutation after validation detected via embedded validation certificate mismatch.
9. Plan mutation after validation detected via deterministic schedule identity recomputation.
10. Stale or invalid validation evidence strictly rejected during approval.
11. IndependentScheduleValidator directly verifies snapshot and scenario provenance.
12. Creating PlanVersion candidate rejects missing or malformed snapshot in source run.
13. Existing valid REAL-scenario approval flow remains fully supported.
14. Synthetic-scenario approval remains blocked by GOV-001.
"""

from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock
import pytest

from backend.app.core.auth import AuthUser, UserRole
from backend.app.domain.enums import DataClass
from backend.app.domain.temporal import PlanningHorizon, TimeInterval
from backend.app.domain.scheduling import (
    ScheduleResult,
    ScheduledTaskResult,
    UnscheduledTaskResult,
    ScheduleMetrics,
    SchedulerType,
    SchedulerStatus,
)
from backend.app.domain.planning_snapshot import PlanningSnapshot
from backend.app.db.models.planning_run import PlanningRunModel
from backend.app.db.models.plan_version import PlanVersionModel
from backend.app.db.models.scenario import OperationalScenarioModel
from backend.app.schemas.plan_version import PlanVersionStatus, GovernanceEventType
from backend.app.repositories.plan_version_repo import (
    PlanVersionApprovalBlockedError,
    PlanFingerprintMismatchError,
    PlanSnapshotIntegrityError,
    FourEyesViolationError,
)
from backend.app.services.plan_governance_service import PlanGovernanceService
from backend.app.services.validation.validator import IndependentScheduleValidator
from backend.app.services.validation.models import (
    ValidationStatus,
    ValidationSeverity,
    ValidationCategory,
)


# =============================================================================
# Test Helpers & Fixtures
# =============================================================================

VALID_SNAPSHOT_HASH = "a" * 64
VALID_INPUT_HASH = "b" * 64
VALID_SCHEDULE_IDENTITY = IndependentScheduleValidator.compute_schedule_identity_from_dict(
    schedule_dict={
        "scheduler_type": "CP_SAT",
        "status": "OPTIMAL",
        "scheduled_tasks": [],
        "unscheduled_tasks": [],
    },
    snapshot_id="SNAP-TEST-001",
    scenario_id="SCN-REAL-OPERATIONAL-001",
)


def _build_test_schedule_result(
    scenario_id: str = "SCN-REAL-OPERATIONAL-001",
    snapshot_id: str = "SNAP-TEST-001",
    include_tasks: bool = False,
    val_identity: str = None,
    val_status: str = "VALID",
    val_approvable: bool = True,
    assigned_track_id: str = None,
) -> dict:
    scheduled_tasks = []
    if include_tasks:
        task_dict = {
            "task_id": "TSK-001",
            "task_code": "TRACK-RENEWAL-01",
            "interval": {
                "start": "2026-10-01T02:00:00+00:00",
                "end": "2026-10-01T06:00:00+00:00",
            },
            "possession_interval": {
                "start": "2026-10-01T01:45:00+00:00",
                "end": "2026-10-01T06:15:00+00:00",
            },
            "duration_minutes": 240,
            "affected_sections": ["SEC-DEL-01"],
            "assigned_resources": ["CREW-TRK-01"],
            "sequence_order": 1,
            "scheduling_reason": "FEASIBLE",
            "assigned_track_id": assigned_track_id,
        }
        scheduled_tasks.append(task_dict)

    if val_identity is None:
        val_identity = IndependentScheduleValidator.compute_schedule_identity_from_dict(
            schedule_dict={
                "scheduler_type": "CP_SAT",
                "status": "OPTIMAL",
                "scheduled_tasks": scheduled_tasks,
                "unscheduled_tasks": [],
            },
            snapshot_id=snapshot_id,
            scenario_id=scenario_id,
        )

    res = {
        "schedule_id": "SCHED-TEST-001",
        "scheduler_type": "CP_SAT",
        "scheduler_version": "1.0.0",
        "scenario_id": scenario_id,
        "snapshot_id": snapshot_id,
        "planning_start": "2026-10-01T00:00:00+00:00",
        "planning_end": "2026-10-02T00:00:00+00:00",
        "status": "OPTIMAL",
        "scheduled_tasks": scheduled_tasks,
        "unscheduled_tasks": [],
        "metrics": {
            "total_tasks": 1 if include_tasks else 0,
            "scheduled_tasks": 1 if include_tasks else 0,
            "unscheduled_tasks": 0,
            "completion_rate": 1.0,
            "mandatory_tasks": 0,
            "mandatory_scheduled": 0,
            "mandatory_unscheduled": 0,
            "mandatory_completion_rate": 1.0,
            "total_scheduled_duration_minutes": 240 if include_tasks else 0,
            "total_possession_duration_minutes": 270 if include_tasks else 0,
            "total_priority_score_available": 100.0,
            "scheduled_priority_score": 100.0,
            "unscheduled_priority_score": 0.0,
            "priority_score_capture_rate": 1.0,
        },
        "configuration": {},
        "execution_time_ms": 150.0,
        "validation": {
            "status": val_status,
            "valid": val_status == "VALID",
            "is_approvable": val_approvable,
            "error_count": 0 if val_status == "VALID" else 1,
            "warning_count": 0,
            "info_count": 0,
            "validator_version": "1.0.0",
            "input_snapshot_id": snapshot_id,
            "input_snapshot_hash": VALID_SNAPSHOT_HASH,
            "schedule_identity": val_identity,
            "approval_gate_message": "Approval ELIGIBLE",
        },
    }
    return res


def _build_test_plan(
    plan_version_id: str = "PV-TEST-001",
    scenario_id: str = "SCN-REAL-OPERATIONAL-001",
    planning_run_id: str = "RUN-TEST-001",
    snapshot_hash: str = VALID_SNAPSHOT_HASH,
    input_hash: str = VALID_INPUT_HASH,
    schedule_identity: str = None,
    dataset_version: str = "v1.0",
    created_by: str = "planner_officer",
    schedule_result: dict = None,
    include_tasks: bool = False,
    assigned_track_id: str = None,
) -> PlanVersionModel:
    if schedule_result is None:
        schedule_result = _build_test_schedule_result(
            scenario_id=scenario_id,
            include_tasks=include_tasks,
            assigned_track_id=assigned_track_id,
            val_identity=schedule_identity,
        )

    if schedule_identity is None:
        val_sec = schedule_result.get("validation") if isinstance(schedule_result, dict) else None
        if isinstance(val_sec, dict) and val_sec.get("schedule_identity"):
            schedule_identity = val_sec["schedule_identity"]
        else:
            schedule_identity = IndependentScheduleValidator.compute_schedule_identity_from_dict(
                schedule_dict=schedule_result if isinstance(schedule_result, dict) else {},
                snapshot_id="SNAP-TEST-001",
                scenario_id=scenario_id,
            )

    plan = MagicMock(spec=PlanVersionModel)
    plan.plan_version_id = plan_version_id
    plan.scenario_id = scenario_id
    plan.planning_run_id = planning_run_id
    plan.version_number = 1
    plan.status = PlanVersionStatus.PENDING_REVIEW.value
    plan.validation_status = "VALID"
    plan.is_approvable = True
    plan.validation_findings_summary = {"error_count": 0, "warning_count": 0}
    plan.schedule_identity = schedule_identity
    plan.snapshot_hash = snapshot_hash
    plan.input_hash = input_hash
    plan.dataset_version = dataset_version
    plan.created_by = created_by
    plan.previous_plan_version_id = None
    plan.schedule_result = (
        schedule_result
        if schedule_result is not None
        else _build_test_schedule_result(scenario_id=scenario_id, val_identity=schedule_identity)
    )
    return plan


def _build_test_run(
    plan: PlanVersionModel,
    snapshot_id: str = "SNAP-TEST-001",
    scenario_id: str = None,
    dataset_version: str = "v1.0",
) -> PlanningRunModel:
    run = MagicMock(spec=PlanningRunModel)
    run.run_id = plan.planning_run_id
    run.scenario_id = scenario_id or plan.scenario_id
    run.snapshot_id = snapshot_id
    run.snapshot_hash = plan.snapshot_hash
    run.input_hash = plan.input_hash
    run.validation_fingerprint = plan.schedule_identity
    run.validation_status = "VALID"
    run.is_approvable = True
    run.dataset_version = dataset_version
    run.schedule_result = plan.schedule_result
    run.status = "COMPLETED"
    return run


def _build_test_scenario(
    scenario_id: str = "SCN-REAL-OPERATIONAL-001",
    classification: DataClass = DataClass.REAL,
    dataset_version: str = "v1.0",
) -> OperationalScenarioModel:
    scen = MagicMock(spec=OperationalScenarioModel)
    scen.scenario_id = scenario_id
    scen.classification = classification
    scen.dataset_version = dataset_version
    return scen


def _build_approver(username: str = "independent_approver") -> AuthUser:
    return AuthUser(
        user_id="USR-APPROVER-01",
        username=username,
        role=UserRole.OPERATOR,
        permissions=["read:reference", "read:operational", "plan:review", "plan:approve"],
    )


# =============================================================================
# 1. Valid Snapshot Approval Flow
# =============================================================================

@pytest.mark.asyncio
async def test_valid_unchanged_snapshot_approval_succeeds():
    """Valid, unchanged snapshot with certified evidence cleanly passes all preconditions."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    plan = _build_test_plan()
    run = _build_test_run(plan)
    scen = _build_test_scenario()
    actor = _build_approver()

    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=plan)
    service.plan_repo.get_latest_approved = AsyncMock(return_value=None)
    service.plan_repo.add_review_comment = AsyncMock()
    service.plan_repo.add_audit_event = AsyncMock()
    service.plan_repo.get_by_plan_version_id = AsyncMock(return_value=plan)
    service.run_repo.get_by_run_id = AsyncMock(return_value=run)
    service.scenario_repo.get_by_id = AsyncMock(return_value=scen)

    approved = await service.approve_plan(
        plan.plan_version_id,
        actor=actor,
        comment="Certified valid plan approved.",
        declared_reviewer_name="Shri V. K. Malhotra",
        declared_reviewer_role="Chief Operations Manager",
    )

    assert plan.status == PlanVersionStatus.APPROVED.value
    assert plan.approved_by == actor.username
    assert plan.approved_at is not None
    service.plan_repo.add_audit_event.assert_called_once()
    session.commit.assert_called_once()


# =============================================================================
# 2. Missing Snapshot Hash
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize("missing_val", [None, "", "   "])
async def test_missing_snapshot_hash_fails_closed(missing_val):
    """Missing or empty snapshot hash fails closed with PlanSnapshotIntegrityError."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    plan = _build_test_plan(snapshot_hash=missing_val)
    actor = _build_approver()

    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=plan)

    with pytest.raises(PlanSnapshotIntegrityError) as exc_info:
        await service.approve_plan(plan.plan_version_id, actor=actor)

    assert "planning snapshot hash is missing" in str(exc_info.value).lower()
    assert plan.status != PlanVersionStatus.APPROVED.value
    session.commit.assert_not_called()


# =============================================================================
# 3. Corrupted or Malformed Snapshot Hash
# =============================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize("corrupt_val", [
    "CORRUPTED_HASH",
    "MALFORMED_SNAPSHOT_001",
    "z" * 64,  # invalid hex digits
    "bad hash with spaces",
    "abc!@#$%",
    "abc",
])
async def test_corrupted_or_malformed_snapshot_hash_fails_closed(corrupt_val):
    """Corrupted or malformed snapshot hash strictly fails closed."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    plan = _build_test_plan(snapshot_hash=corrupt_val)
    actor = _build_approver()

    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=plan)

    with pytest.raises(PlanSnapshotIntegrityError) as exc_info:
        await service.approve_plan(plan.plan_version_id, actor=actor)

    assert "malformed" in str(exc_info.value).lower()
    assert plan.status != PlanVersionStatus.APPROVED.value


# =============================================================================
# 4. Missing or Malformed Input Hash & Schedule Identity
# =============================================================================

@pytest.mark.asyncio
async def test_missing_input_hash_fails_closed():
    """Missing input hash fails closed with PlanSnapshotIntegrityError."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    plan = _build_test_plan(input_hash="")
    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=plan)

    with pytest.raises(PlanSnapshotIntegrityError, match="input configuration hash is missing"):
        await service.approve_plan(plan.plan_version_id, actor=_build_approver())


@pytest.mark.asyncio
async def test_missing_schedule_identity_fails_closed():
    """Missing schedule identity fingerprint fails closed with PlanSnapshotIntegrityError."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    plan = _build_test_plan(schedule_identity="")
    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=plan)

    with pytest.raises(PlanSnapshotIntegrityError, match="(?i)schedule identity fingerprint is missing"):
        await service.approve_plan(plan.plan_version_id, actor=_build_approver())


# =============================================================================
# 5. Scenario ID & Version Mismatch
# =============================================================================

@pytest.mark.asyncio
async def test_source_run_scenario_mismatch_fails_closed():
    """PlanVersion scenario different from source planning run scenario fails closed."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    plan = _build_test_plan(scenario_id="SCN-REAL-OPERATIONAL-001")
    # Run has mismatched scenario
    run = _build_test_run(plan, scenario_id="SCN-OTHER-002")

    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=plan)
    service.run_repo.get_by_run_id = AsyncMock(return_value=run)

    with pytest.raises(PlanFingerprintMismatchError) as exc_info:
        await service.approve_plan(plan.plan_version_id, actor=_build_approver())

    assert "Scenario mismatch" in str(exc_info.value)


@pytest.mark.asyncio
async def test_schedule_result_scenario_mismatch_fails_closed():
    """Schedule result containing a different scenario_id fails closed."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    sched_res = _build_test_schedule_result(scenario_id="SCN-TAMPERED-999")
    plan = _build_test_plan(scenario_id="SCN-REAL-OPERATIONAL-001", schedule_result=sched_res)
    run = _build_test_run(plan)

    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=plan)
    service.run_repo.get_by_run_id = AsyncMock(return_value=run)

    with pytest.raises(PlanFingerprintMismatchError) as exc_info:
        await service.approve_plan(plan.plan_version_id, actor=_build_approver())

    assert "Scenario mismatch" in str(exc_info.value)


@pytest.mark.asyncio
async def test_scenario_dataset_version_mismatch_fails_closed():
    """Scenario dataset version newer than PlanVersion dataset version fails closed (stale snapshot)."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    plan = _build_test_plan(dataset_version="v1.0")
    run = _build_test_run(plan, dataset_version="v1.0")
    # Scenario has progressed to v2.0
    scen = _build_test_scenario(dataset_version="v2.0")

    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=plan)
    service.run_repo.get_by_run_id = AsyncMock(return_value=run)
    service.scenario_repo.get_by_id = AsyncMock(return_value=scen)

    with pytest.raises(PlanFingerprintMismatchError) as exc_info:
        await service.approve_plan(plan.plan_version_id, actor=_build_approver())

    assert "Dataset version mismatch" in str(exc_info.value)
    assert "Stored snapshot is stale" in str(exc_info.value)


# =============================================================================
# 6. Snapshot Hash Mismatch Against Source Run
# =============================================================================

@pytest.mark.asyncio
async def test_snapshot_hash_tampering_against_run_fails_closed():
    """Plan snapshot_hash differing from run.snapshot_hash fails closed."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    plan = _build_test_plan(snapshot_hash="a" * 64)
    run = _build_test_run(plan)
    run.snapshot_hash = "f" * 64  # Mismatch

    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=plan)
    service.run_repo.get_by_run_id = AsyncMock(return_value=run)

    with pytest.raises(PlanFingerprintMismatchError, match="snapshot hash does not match source run"):
        await service.approve_plan(plan.plan_version_id, actor=_build_approver())


# =============================================================================
# 7. Plan Mutation After Validation (Tamper Detection)
# =============================================================================

@pytest.mark.asyncio
async def test_embedded_validation_identity_mismatch_fails_closed():
    """Tampering with plan.schedule_identity while certificate has original identity fails closed."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    # Schedule has certificate for VALID_SCHEDULE_IDENTITY
    sched_res = _build_test_schedule_result(val_identity=VALID_SCHEDULE_IDENTITY)
    # Plan has tampered schedule_identity
    plan = _build_test_plan(
        schedule_identity="d" * 64,
        schedule_result=sched_res,
    )
    run = _build_test_run(plan)
    run.validation_fingerprint = "d" * 64

    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=plan)
    service.run_repo.get_by_run_id = AsyncMock(return_value=run)

    with pytest.raises(PlanFingerprintMismatchError) as exc_info:
        await service.approve_plan(plan.plan_version_id, actor=_build_approver())

    assert "Plan mutation detected" in str(exc_info.value)


@pytest.mark.asyncio
async def test_recomputed_schedule_identity_tamper_detection():
    """Mutating task placement within schedule_result is caught by recomputing identity."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    # 1. Compute valid schedule identity with tasks
    sched_res = _build_test_schedule_result(include_tasks=True)
    real_identity = IndependentScheduleValidator.compute_schedule_identity_from_dict(
        schedule_dict=sched_res,
        snapshot_id="SNAP-TEST-001",
        scenario_id="SCN-REAL-OPERATIONAL-001",
    )
    # Set matching identity
    sched_res["validation"]["schedule_identity"] = real_identity

    plan = _build_test_plan(schedule_identity=real_identity, schedule_result=sched_res)
    run = _build_test_run(plan, snapshot_id="SNAP-TEST-001")

    # 2. Maliciously tamper with task start time after validation
    plan.schedule_result["scheduled_tasks"][0]["interval"]["start"] = "2026-10-01T05:00:00+00:00"

    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=plan)
    service.run_repo.get_by_run_id = AsyncMock(return_value=run)

    with pytest.raises(PlanFingerprintMismatchError) as exc_info:
        await service.approve_plan(plan.plan_version_id, actor=_build_approver())

    assert "Schedule content tampered after validation" in str(exc_info.value)


# =============================================================================
# 8. Stale or Invalid Validation Evidence
# =============================================================================

@pytest.mark.asyncio
async def test_stale_validation_status_blocks_approval():
    """Plan with validation_status != VALID cannot receive approval."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    plan = _build_test_plan()
    plan.validation_status = "INVALID"
    plan.is_approvable = False

    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=plan)

    with pytest.raises(PlanVersionApprovalBlockedError) as exc_info:
        await service.approve_plan(plan.plan_version_id, actor=_build_approver())

    assert "Only certified valid schedules may be approved" in str(exc_info.value)


@pytest.mark.asyncio
async def test_embedded_invalid_validation_evidence_blocks_approval():
    """Embedded validation certificate with status != VALID blocks approval."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    sched_res = _build_test_schedule_result(val_status="INVALID", val_approvable=False)
    plan = _build_test_plan(schedule_result=sched_res)
    run = _build_test_run(plan)

    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=plan)
    service.run_repo.get_by_run_id = AsyncMock(return_value=run)

    with pytest.raises(PlanVersionApprovalBlockedError) as exc_info:
        await service.approve_plan(plan.plan_version_id, actor=_build_approver())

    assert "Stale or uncertified validation evidence cannot authorize approval" in str(exc_info.value)


# =============================================================================
# 9. IndependentScheduleValidator Provenance and Snapshot Checks
# =============================================================================

def test_independent_validator_catches_scenario_provenance_mismatch():
    """IndependentScheduleValidator emits ERROR when schedule.scenario_id != snapshot.scenario_id."""
    h = PlanningHorizon(
        start=datetime(2026, 10, 1, tzinfo=timezone.utc),
        end=datetime(2026, 10, 2, tzinfo=timezone.utc),
    )
    snap = PlanningSnapshot(
        scenario_id="SCN-SNAP-001",
        snapshot_id="SNAP-001",
        horizon=h,
        tasks=[],
        tasks_map={},
        work_orders_map={},
        resources=[],
        resources_map={},
        resource_availabilities=[],
        dependencies=[],
        dependencies_by_successor={},
        dependencies_by_predecessor={},
        sections_map={},
        rules_map={},
        train_passes=[],
    )
    sched = ScheduleResult(
        schedule_id="SCH-01",
        scheduler_type=SchedulerType.CP_SAT,
        scheduler_version="1.0",
        scenario_id="SCN-DIFFERENT-002",  # Mismatch
        snapshot_id="SNAP-001",
        planning_start=h.start,
        planning_end=h.end,
        status=SchedulerStatus.OPTIMAL,
        scheduled_tasks=[],
        unscheduled_tasks=[],
        metrics=ScheduleMetrics(
            total_tasks=0, scheduled_tasks=0, unscheduled_tasks=0, completion_rate=1.0,
            mandatory_tasks=0, mandatory_scheduled=0, mandatory_unscheduled=0, mandatory_completion_rate=1.0,
            total_scheduled_duration_minutes=0, total_possession_duration_minutes=0,
            total_priority_score_available=0.0, scheduled_priority_score=0.0, unscheduled_priority_score=0.0,
            priority_score_capture_rate=1.0,
        ),
        configuration={},
        execution_time_ms=10.0,
    )

    result = IndependentScheduleValidator.validate(snap, sched)
    assert result.status == ValidationStatus.INVALID
    assert result.is_approvable is False
    codes = [f.code for f in result.findings]
    assert "SCENARIO_PROVENANCE_MISMATCH" in codes


def test_independent_validator_catches_snapshot_id_mismatch():
    """IndependentScheduleValidator emits ERROR when schedule.snapshot_id != snapshot.snapshot_id."""
    h = PlanningHorizon(
        start=datetime(2026, 10, 1, tzinfo=timezone.utc),
        end=datetime(2026, 10, 2, tzinfo=timezone.utc),
    )
    snap = PlanningSnapshot(
        scenario_id="SCN-SNAP-001",
        snapshot_id="SNAP-ORIGINAL-001",
        horizon=h,
        tasks=[],
        tasks_map={},
        work_orders_map={},
        resources=[],
        resources_map={},
        resource_availabilities=[],
        dependencies=[],
        dependencies_by_successor={},
        dependencies_by_predecessor={},
        sections_map={},
        rules_map={},
        train_passes=[],
    )
    sched = ScheduleResult(
        schedule_id="SCH-01",
        scheduler_type=SchedulerType.CP_SAT,
        scheduler_version="1.0",
        scenario_id="SCN-SNAP-001",
        snapshot_id="SNAP-OTHER-002",  # Mismatch
        planning_start=h.start,
        planning_end=h.end,
        status=SchedulerStatus.OPTIMAL,
        scheduled_tasks=[],
        unscheduled_tasks=[],
        metrics=ScheduleMetrics(
            total_tasks=0, scheduled_tasks=0, unscheduled_tasks=0, completion_rate=1.0,
            mandatory_tasks=0, mandatory_scheduled=0, mandatory_unscheduled=0, mandatory_completion_rate=1.0,
            total_scheduled_duration_minutes=0, total_possession_duration_minutes=0,
            total_priority_score_available=0.0, scheduled_priority_score=0.0, unscheduled_priority_score=0.0,
            priority_score_capture_rate=1.0,
        ),
        configuration={},
        execution_time_ms=10.0,
    )

    result = IndependentScheduleValidator.validate(snap, sched)
    assert result.status == ValidationStatus.INVALID
    assert result.is_approvable is False
    codes = [f.code for f in result.findings]
    assert "SNAPSHOT_PROVENANCE_MISMATCH" in codes
    assert result.input_snapshot_hash is not None


# =============================================================================
# 10. Candidate Creation Rejects Missing/Malformed Snapshot
# =============================================================================

@pytest.mark.asyncio
async def test_create_plan_version_rejects_missing_run_snapshot_hash():
    """create_plan_version_from_run rejects a run with missing snapshot hash."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    run = MagicMock(spec=PlanningRunModel)
    run.run_id = "RUN-BAD-01"
    run.status = "COMPLETED"
    run.validation_status = "VALID"
    run.is_approvable = True
    run.schedule_result = {"status": "OPTIMAL"}
    run.snapshot_hash = None  # Missing

    service.run_repo.get_by_run_id = AsyncMock(return_value=run)
    service.plan_repo.get_by_planning_run_id = AsyncMock(return_value=None)

    with pytest.raises(PlanSnapshotIntegrityError, match="missing planning snapshot hash"):
        await service.create_plan_version_from_run(
            run_id="RUN-BAD-01",
            actor=_build_approver(),
        )


# =============================================================================
# 11. Synthetic Scenario Still Blocked (GOV-001 Invariant)
# =============================================================================

@pytest.mark.asyncio
async def test_synthetic_scenario_still_blocked_by_gov001():
    """Even with 100% valid snapshot and hashes, synthetic scenarios remain blocked."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    plan = _build_test_plan(scenario_id="SCN-DEMO-001")
    run = _build_test_run(plan)
    scen = _build_test_scenario(scenario_id="SCN-DEMO-001", classification=DataClass.SYNTHETIC)

    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=plan)
    service.run_repo.get_by_run_id = AsyncMock(return_value=run)
    service.scenario_repo.get_by_id = AsyncMock(return_value=scen)

    with pytest.raises(PlanVersionApprovalBlockedError) as exc_info:
        await service.approve_plan(plan.plan_version_id, actor=_build_approver())

    assert "SYNTHETIC" in str(exc_info.value)
    assert "cannot be approved as real operational plans" in str(exc_info.value)


# =============================================================================
# 12. VAL-002: Schedule Identity & Track Assignment Integrity
# =============================================================================

def _build_domain_schedule_with_tasks(
    tasks: list[ScheduledTaskResult],
    scenario_id: str = "SCN-REAL-OPERATIONAL-001",
    snapshot_id: str = "SNAP-TEST-001",
) -> ScheduleResult:
    start = datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc)
    metrics = ScheduleMetrics(
        total_tasks=len(tasks),
        scheduled_tasks=len(tasks),
        unscheduled_tasks=0,
        completion_rate=1.0,
        mandatory_tasks=0,
        mandatory_scheduled=0,
        mandatory_unscheduled=0,
        mandatory_completion_rate=1.0,
        total_scheduled_duration_minutes=sum(t.duration_minutes for t in tasks),
        total_possession_duration_minutes=sum(t.duration_minutes for t in tasks),
        total_priority_score_available=100.0,
        scheduled_priority_score=100.0,
        unscheduled_priority_score=0.0,
        priority_score_capture_rate=1.0,
    )
    return ScheduleResult(
        schedule_id="SCHED-VAL002-01",
        scheduler_type=SchedulerType.CP_SAT,
        scheduler_version="1.0.0",
        scenario_id=scenario_id,
        snapshot_id=snapshot_id,
        planning_start=start,
        planning_end=start + timedelta(hours=24),
        status=SchedulerStatus.OPTIMAL,
        scheduled_tasks=tasks,
        unscheduled_tasks=[],
        metrics=metrics,
        configuration={},
        execution_time_ms=100.0,
    )


def test_val002_identical_schedules_produce_identical_identities():
    """Identical schedules with assigned tracks produce identical identities, including whitespace normalization."""
    start = datetime(2026, 10, 1, 2, 0, tzinfo=timezone.utc)
    end = datetime(2026, 10, 1, 6, 0, tzinfo=timezone.utc)
    snap = MagicMock(spec=PlanningSnapshot)
    snap.snapshot_id = "SNAP-TEST-001"
    snap.scenario_id = "SCN-REAL-OPERATIONAL-001"

    task1 = ScheduledTaskResult(
        task_id="TSK-01",
        task_code="TC-01",
        interval=TimeInterval(start=start, end=end),
        possession_interval=TimeInterval(start=start, end=end),
        duration_minutes=240,
        sequence_order=1,
        assigned_resources=["RES-01"],
        affected_sections=["SEC-01"],
        assigned_track_id="TRK-SEC-01-UP",
    )
    task2 = ScheduledTaskResult(
        task_id="TSK-01",
        task_code="TC-01",
        interval=TimeInterval(start=start, end=end),
        possession_interval=TimeInterval(start=start, end=end),
        duration_minutes=240,
        sequence_order=1,
        assigned_resources=["RES-01"],
        affected_sections=["SEC-01"],
        assigned_track_id="  TRK-SEC-01-UP  ",  # with whitespace
    )

    sched1 = _build_domain_schedule_with_tasks([task1])
    sched2 = _build_domain_schedule_with_tasks([task2])

    id1 = IndependentScheduleValidator.compute_schedule_identity(snap, sched1)
    id2 = IndependentScheduleValidator.compute_schedule_identity(snap, sched2)

    assert id1 == id2, "Identical track assignments (even with whitespace) must yield identical identities"
    assert len(id1) == 64


def test_val002_changing_only_assigned_track_id_changes_identity():
    """Changing only assigned_track_id is identity-bearing and changes the SHA-256 fingerprint."""
    start = datetime(2026, 10, 1, 2, 0, tzinfo=timezone.utc)
    end = datetime(2026, 10, 1, 6, 0, tzinfo=timezone.utc)
    snap = MagicMock(spec=PlanningSnapshot)
    snap.snapshot_id = "SNAP-TEST-001"
    snap.scenario_id = "SCN-REAL-OPERATIONAL-001"

    base_kwargs = dict(
        task_id="TSK-01",
        task_code="TC-01",
        interval=TimeInterval(start=start, end=end),
        possession_interval=TimeInterval(start=start, end=end),
        duration_minutes=240,
        sequence_order=1,
        assigned_resources=["RES-01"],
        affected_sections=["SEC-01"],
    )

    task_up = ScheduledTaskResult(**base_kwargs, assigned_track_id="TRK-SEC-01-UP")
    task_dn = ScheduledTaskResult(**base_kwargs, assigned_track_id="TRK-SEC-01-DN")
    task_none = ScheduledTaskResult(**base_kwargs, assigned_track_id=None)

    id_up = IndependentScheduleValidator.compute_schedule_identity(snap, _build_domain_schedule_with_tasks([task_up]))
    id_dn = IndependentScheduleValidator.compute_schedule_identity(snap, _build_domain_schedule_with_tasks([task_dn]))
    id_none = IndependentScheduleValidator.compute_schedule_identity(snap, _build_domain_schedule_with_tasks([task_none]))

    assert id_up != id_dn, "Different track assignments must produce different identities"
    assert id_up != id_none, "Assigned track vs unassigned track must produce different identities"
    assert id_dn != id_none, "Down track vs unassigned track must produce different identities"


def test_val002_object_and_dict_identities_produce_same_hash():
    """Object-based and serialized-dictionary schedule identity functions produce the exact same hash."""
    start = datetime(2026, 10, 1, 2, 0, tzinfo=timezone.utc)
    end = datetime(2026, 10, 1, 6, 0, tzinfo=timezone.utc)
    snap = MagicMock(spec=PlanningSnapshot)
    snap.snapshot_id = "SNAP-TEST-001"
    snap.scenario_id = "SCN-REAL-OPERATIONAL-001"

    t1 = ScheduledTaskResult(
        task_id="TSK-01",
        task_code="TC-01",
        interval=TimeInterval(start=start, end=end),
        possession_interval=TimeInterval(start=start, end=end),
        duration_minutes=240,
        sequence_order=1,
        assigned_resources=["RES-01"],
        affected_sections=["SEC-01"],
        assigned_track_id="TRK-SEC-01-UP",
    )
    t2 = ScheduledTaskResult(
        task_id="TSK-02",
        task_code="TC-02",
        interval=TimeInterval(start=start, end=end),
        possession_interval=TimeInterval(start=start, end=end),
        duration_minutes=240,
        sequence_order=2,
        assigned_resources=["RES-02"],
        affected_sections=["SEC-02"],
        assigned_track_id=None,
    )

    sched = _build_domain_schedule_with_tasks([t1, t2])
    sched_dict = sched.model_dump(mode="json")

    h_obj = IndependentScheduleValidator.compute_schedule_identity(snap, sched)
    h_dict = IndependentScheduleValidator.compute_schedule_identity_from_dict(
        schedule_dict=sched_dict,
        snapshot_id=snap.snapshot_id,
        scenario_id=snap.scenario_id,
    )

    assert h_obj == h_dict, "Object-based and dict-based identity must produce identical fingerprints"


@pytest.mark.asyncio
async def test_val002_track_assignment_tamper_after_validation_blocks_approval():
    """Mutating assigned_track_id after validation invalidates identity and strictly blocks approval."""
    session = AsyncMock()
    service = PlanGovernanceService(session)

    # Valid plan candidate with assigned_track_id="TRK-SEC-01-UP"
    plan = _build_test_plan(
        include_tasks=True,
        assigned_track_id="TRK-SEC-01-UP",
    )
    run = _build_test_run(plan, snapshot_id="SNAP-TEST-001")
    scen = _build_test_scenario()

    service.plan_repo.get_by_id_for_update = AsyncMock(return_value=plan)
    service.run_repo.get_by_run_id = AsyncMock(return_value=run)
    service.scenario_repo.get_by_id = AsyncMock(return_value=scen)

    # Maliciously tamper with assigned track after validation certification
    plan.schedule_result["scheduled_tasks"][0]["assigned_track_id"] = "TRK-SEC-01-DN"

    with pytest.raises(PlanFingerprintMismatchError) as exc_info:
        await service.approve_plan(plan.plan_version_id, actor=_build_approver())

    assert "Schedule content tampered after validation" in str(exc_info.value)
    assert plan.status != PlanVersionStatus.APPROVED.value


def test_val002_existing_schedules_without_track_assignment_handled_cleanly():
    """Existing / legacy schedule payloads omitting assigned_track_id or set to None/empty match cleanly."""
    task_omitted = {
        "task_id": "TSK-01",
        "interval": {"start": "2026-10-01T02:00:00+00:00", "end": "2026-10-01T06:00:00+00:00"},
        "possession_interval": {"start": "2026-10-01T01:45:00+00:00", "end": "2026-10-01T06:15:00+00:00"},
        "affected_sections": ["SEC-01"],
        "assigned_resources": ["RES-01"],
        # 'assigned_track_id' is omitted
    }
    task_none = {**task_omitted, "assigned_track_id": None}
    task_empty = {**task_omitted, "assigned_track_id": "   "}

    def _sched_with(task_data):
        return {
            "scheduler_type": "CP_SAT",
            "status": "OPTIMAL",
            "scheduled_tasks": [task_data],
            "unscheduled_tasks": [],
        }

    h_omitted = IndependentScheduleValidator.compute_schedule_identity_from_dict(_sched_with(task_omitted), "SNAP-01", "SCN-01")
    h_none = IndependentScheduleValidator.compute_schedule_identity_from_dict(_sched_with(task_none), "SNAP-01", "SCN-01")
    h_empty = IndependentScheduleValidator.compute_schedule_identity_from_dict(_sched_with(task_empty), "SNAP-01", "SCN-01")

    assert h_omitted == h_none == h_empty, "Omitted, None, and whitespace track assignments must normalize identically"
