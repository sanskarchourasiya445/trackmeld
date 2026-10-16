"""Unit regression tests for Task 11 (F11): Fail-Closed Snapshot Hash Validation.

Verifies:
1. Successfully computed snapshot hash that matches expected hash passes validation cleanly.
2. Successfully computed snapshot hash that does not match expected hash produces SNAPSHOT_HASH_MISMATCH (ERROR).
3. Missing compute_snapshot_hash method or empty computed hash produces SNAPSHOT_HASH_MISSING (ERROR).
4. Malformed computed snapshot hash produces SNAPSHOT_HASH_MALFORMED (ERROR).
5. Empty or malformed expected snapshot hash on schedule produces SNAPSHOT_HASH_MISSING / MALFORMED (ERROR).
6. Exception during snapshot hash computation produces SNAPSHOT_HASH_COMPUTATION_FAILED (ERROR),
   never silently caught or substituted with None to create a false pass.
7. assert_schedule_approvable raises ScheduleApprovalBlockedError on any hash failure.
8. Compatibility with F3 approval-time snapshot re-hashing: both layers fail closed consistently.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, AsyncMock
import pytest

from backend.app.domain.temporal import PlanningHorizon, TimeInterval
from backend.app.domain.scheduling import (
    ScheduleResult,
    ScheduledTaskResult,
    ScheduleMetrics,
    SchedulerType,
    SchedulerStatus,
)
from backend.app.domain.planning_snapshot import PlanningSnapshot
from backend.app.services.validation.validator import IndependentScheduleValidator
from backend.app.services.validation.checks import (
    ScheduleCheckRunner,
    _is_valid_sha256,
    _is_missing_hash,
    _is_malformed_hash,
)
from backend.app.services.validation.models import (
    ValidationStatus,
    ValidationSeverity,
    ValidationCategory,
)
from backend.app.services.validation.exceptions import ScheduleApprovalBlockedError
from backend.app.core.auth import AuthUser, UserRole
from backend.app.db.models.planning_run import PlanningRunModel
from backend.app.db.models.plan_version import PlanVersionModel
from backend.app.db.models.scenario import OperationalScenarioModel
from backend.app.domain.enums import DataClass
from backend.app.schemas.plan_version import PlanVersionStatus
from backend.app.repositories.plan_version_repo import (
    PlanVersionApprovalBlockedError,
    PlanFingerprintMismatchError,
    PlanSnapshotIntegrityError,
)
from backend.app.services.plan_governance_service import PlanGovernanceService


# Canonical test hashes
VALID_HASH_A = "a" * 64
VALID_HASH_B = "b" * 64
VALID_HASH_C = "c" * 64


def _create_minimal_snapshot(
    scenario_id: str = "SCN-REAL-001",
    snapshot_id: str = "SNAP-REAL-001",
    hash_value: str = VALID_HASH_A,
) -> MagicMock:
    """Create a mock PlanningSnapshot that satisfies basic structural invariants."""
    h_start = datetime(2026, 10, 15, 0, 0, tzinfo=timezone.utc)
    h_end = h_start + timedelta(hours=24)
    horizon = PlanningHorizon(start=h_start, end=h_end)

    snap = MagicMock(spec=PlanningSnapshot)
    snap.scenario_id = scenario_id
    snap.snapshot_id = snapshot_id
    snap.horizon = horizon
    snap.tasks = []
    snap.tasks_map = {}
    snap.work_orders_map = {}
    snap.resources = []
    snap.resources_map = {}
    snap.resource_availabilities = []
    snap.dependencies = []
    snap.dependencies_by_successor = {}
    snap.dependencies_by_predecessor = {}
    snap.sections_map = {}
    snap.rules_map = {}
    snap.train_passes = []
    snap.tracks_map = {}
    snap.train_movements = []
    snap.train_movements_map = {}
    snap.train_traversals = []
    snap.train_traversals_map = {}
    snap.compute_snapshot_hash = MagicMock(return_value=hash_value)
    return snap


def _create_minimal_schedule(
    snapshot: MagicMock,
    snapshot_hash: str = None,
    status: SchedulerStatus = SchedulerStatus.OPTIMAL,
) -> ScheduleResult:
    """Create a minimal valid ScheduleResult matching the snapshot."""
    return ScheduleResult(
        schedule_id="SCHED-001",
        scheduler_type=SchedulerType.CP_SAT,
        scheduler_version="1.0.0",
        scenario_id=snapshot.scenario_id,
        snapshot_id=snapshot.snapshot_id,
        planning_start=snapshot.horizon.start,
        planning_end=snapshot.horizon.end,
        status=status,
        scheduled_tasks=[],
        unscheduled_tasks=[],
        metrics=ScheduleMetrics(
            total_tasks=0,
            scheduled_tasks=0,
            unscheduled_tasks=0,
            completion_rate=1.0,
            mandatory_tasks=0,
            mandatory_scheduled=0,
            mandatory_unscheduled=0,
            mandatory_completion_rate=1.0,
            total_scheduled_duration_minutes=0,
            total_possession_duration_minutes=0,
            total_priority_score_available=0.0,
            scheduled_priority_score=0.0,
            unscheduled_priority_score=0.0,
            priority_score_capture_rate=1.0,
        ),
        configuration={},
        execution_time_ms=10.0,
        snapshot_hash=snapshot_hash,
    )


# =============================================================================
# 1. SHA-256 Utility Unit Tests
# =============================================================================

def test_f11_sha256_helpers():
    """Verify SHA-256 helper predicates correctly distinguish valid, missing, and malformed."""
    assert _is_valid_sha256("a" * 64) is True
    assert _is_valid_sha256("0123456789abcdef" * 4) is True
    assert _is_valid_sha256("ABCDEF0123456789" * 4) is True

    # Missing
    assert _is_missing_hash(None) is True
    assert _is_missing_hash("") is True
    assert _is_missing_hash("   ") is True
    assert _is_missing_hash("a" * 64) is False

    # Malformed
    assert _is_malformed_hash(None) is True
    assert _is_malformed_hash("") is True
    assert _is_malformed_hash("too_short") is True
    assert _is_malformed_hash("z" * 64) is True  # Non-hex characters
    assert _is_malformed_hash("a" * 63) is True
    assert _is_malformed_hash("a" * 65) is True
    assert _is_malformed_hash("a" * 64) is False


# =============================================================================
# 2. Matching Hash (Clean Pass)
# =============================================================================

def test_f11_matching_snapshot_hash_succeeds():
    """When computed snapshot hash matches expected snapshot hash, validation succeeds."""
    snap = _create_minimal_snapshot(hash_value=VALID_HASH_A)
    sched = _create_minimal_schedule(snap, snapshot_hash=VALID_HASH_A)

    result = IndependentScheduleValidator.validate(snap, sched)

    assert result.status == ValidationStatus.VALID
    assert result.valid is True
    assert result.is_approvable is True
    assert result.error_count == 0
    assert result.input_snapshot_hash == VALID_HASH_A

    # Confirm zero findings related to snapshot hash
    hash_findings = [f for f in result.findings if f.code.startswith("SNAPSHOT_HASH")]
    assert len(hash_findings) == 0


def test_f11_matching_snapshot_hash_via_embedded_validation():
    """When schedule has embedded validation with input_snapshot_hash, matching succeeds."""
    snap = _create_minimal_snapshot(hash_value=VALID_HASH_A)
    sched = _create_minimal_schedule(snap, snapshot_hash=None)
    sched.validation = {"input_snapshot_hash": VALID_HASH_A}

    result = IndependentScheduleValidator.validate(snap, sched)

    assert result.status == ValidationStatus.VALID
    assert result.valid is True
    assert result.is_approvable is True
    assert result.input_snapshot_hash == VALID_HASH_A


# =============================================================================
# 3. Hash Mismatch (Tamper Detection)
# =============================================================================

def test_f11_snapshot_hash_mismatch_fails_closed():
    """When computed hash differs from expected hash, validation fails closed with SNAPSHOT_HASH_MISMATCH."""
    snap = _create_minimal_snapshot(hash_value=VALID_HASH_A)
    sched = _create_minimal_schedule(snap, snapshot_hash=VALID_HASH_B)

    result = IndependentScheduleValidator.validate(snap, sched)

    assert result.status == ValidationStatus.INVALID
    assert result.valid is False
    assert result.is_approvable is False
    assert result.error_count >= 1

    mismatch_findings = [f for f in result.findings if f.code == "SNAPSHOT_HASH_MISMATCH"]
    assert len(mismatch_findings) == 1
    finding = mismatch_findings[0]
    assert finding.severity == ValidationSeverity.ERROR
    assert finding.category == ValidationCategory.PROVENANCE
    assert finding.expected == VALID_HASH_B
    assert finding.actual == VALID_HASH_A
    assert "mutated or was tampered" in finding.message

    # Must also block assert_schedule_approvable
    with pytest.raises(ScheduleApprovalBlockedError):
        IndependentScheduleValidator.assert_schedule_approvable(snap, sched)


def test_f11_embedded_validation_hash_mismatch_fails_closed():
    """When schedule carries embedded validation with mismatched hash, it fails closed."""
    snap = _create_minimal_snapshot(hash_value=VALID_HASH_A)
    sched = _create_minimal_schedule(snap, snapshot_hash=None)
    sched.validation = {"input_snapshot_hash": VALID_HASH_C}

    result = IndependentScheduleValidator.validate(snap, sched)

    assert result.status == ValidationStatus.INVALID
    assert result.valid is False
    assert result.is_approvable is False
    assert any(f.code == "SNAPSHOT_HASH_MISMATCH" for f in result.findings)


# =============================================================================
# 4. Missing or Malformed Snapshot / Hash Data
# =============================================================================

def test_f11_missing_compute_snapshot_hash_capability_fails_closed():
    """If snapshot object lacks compute_snapshot_hash method, validation fails closed."""
    snap = _create_minimal_snapshot()
    del snap.compute_snapshot_hash  # Remove capability

    sched = _create_minimal_schedule(snap)

    result = IndependentScheduleValidator.validate(snap, sched)

    assert result.status == ValidationStatus.INVALID
    assert result.valid is False
    assert result.is_approvable is False
    assert result.input_snapshot_hash is None

    missing_findings = [f for f in result.findings if f.code == "SNAPSHOT_HASH_MISSING"]
    assert len(missing_findings) >= 1
    assert missing_findings[0].severity == ValidationSeverity.ERROR
    assert "lacks callable compute_snapshot_hash" in missing_findings[0].message

    with pytest.raises(ScheduleApprovalBlockedError):
        IndependentScheduleValidator.assert_schedule_approvable(snap, sched)


@pytest.mark.parametrize("empty_hash", ["", "   ", None])
def test_f11_empty_computed_hash_fails_closed(empty_hash):
    """If compute_snapshot_hash returns None or whitespace, validation fails closed."""
    snap = _create_minimal_snapshot()
    snap.compute_snapshot_hash = MagicMock(return_value=empty_hash)

    sched = _create_minimal_schedule(snap)

    result = IndependentScheduleValidator.validate(snap, sched)

    assert result.status == ValidationStatus.INVALID
    assert result.valid is False
    assert result.is_approvable is False
    assert result.input_snapshot_hash is None
    assert any(f.code == "SNAPSHOT_HASH_MISSING" for f in result.findings)


@pytest.mark.parametrize("malformed_val", [
    "not-a-hash",
    "short_hash",
    "z" * 64,  # invalid hex digits
    "a" * 63,  # wrong length
    "a" * 65,  # wrong length
    "bad hash with spaces" + "0" * 44,
])
def test_f11_malformed_computed_hash_fails_closed(malformed_val):
    """If compute_snapshot_hash returns a malformed string, validation fails closed."""
    snap = _create_minimal_snapshot(hash_value=malformed_val)
    sched = _create_minimal_schedule(snap)

    result = IndependentScheduleValidator.validate(snap, sched)

    assert result.status == ValidationStatus.INVALID
    assert result.valid is False
    assert result.is_approvable is False
    assert result.input_snapshot_hash is None

    malformed_findings = [f for f in result.findings if f.code == "SNAPSHOT_HASH_MALFORMED"]
    assert len(malformed_findings) >= 1
    assert malformed_findings[0].severity == ValidationSeverity.ERROR


@pytest.mark.parametrize("malformed_expected", [
    "short_exp",
    "z" * 64,
    "bad_char!",
])
def test_f11_malformed_expected_hash_on_schedule_fails_closed(malformed_expected):
    """If schedule specifies a malformed expected snapshot hash, validation fails closed."""
    snap = _create_minimal_snapshot(hash_value=VALID_HASH_A)
    sched = _create_minimal_schedule(snap, snapshot_hash=malformed_expected)

    result = IndependentScheduleValidator.validate(snap, sched)

    assert result.status == ValidationStatus.INVALID
    assert result.valid is False
    assert result.is_approvable is False
    assert any(f.code == "SNAPSHOT_HASH_MALFORMED" for f in result.findings)


# =============================================================================
# 5. Exception During Hash Computation (The Core F11 Fix)
# =============================================================================

def test_f11_exception_during_hash_computation_never_produces_false_pass():
    """An exception during snapshot hash computation MUST NOT be silently swallowed.

    It must produce SNAPSHOT_HASH_COMPUTATION_FAILED (ERROR), set status=INVALID,
    and block approval.
    """
    snap = _create_minimal_snapshot()
    snap.compute_snapshot_hash = MagicMock(
        side_effect=RuntimeError("PostgreSQL connection lost during snapshot read.")
    )

    sched = _create_minimal_schedule(snap)

    result = IndependentScheduleValidator.validate(snap, sched)

    # Core invariant: NEVER a false pass!
    assert result.status == ValidationStatus.INVALID
    assert result.valid is False
    assert result.is_approvable is False
    assert result.error_count >= 1
    assert result.input_snapshot_hash is None

    # Finding MUST explain the exception
    comp_fail_findings = [f for f in result.findings if f.code == "SNAPSHOT_HASH_COMPUTATION_FAILED"]
    assert len(comp_fail_findings) == 1
    finding = comp_fail_findings[0]
    assert finding.severity == ValidationSeverity.ERROR
    assert finding.category == ValidationCategory.PROVENANCE
    assert "PostgreSQL connection lost" in finding.message
    assert finding.evidence["error_type"] == "RuntimeError"

    # assert_schedule_approvable must raise
    with pytest.raises(ScheduleApprovalBlockedError):
        IndependentScheduleValidator.assert_schedule_approvable(snap, sched)


@pytest.mark.parametrize("exc", [
    TypeError("Unserializable object encountered in task records"),
    ValueError("Invalid timestamp format in horizon"),
    KeyError("task_id missing from raw record"),
    AttributeError("'NoneType' object has no attribute 'isoformat'"),
])
def test_f11_various_exceptions_fail_closed(exc):
    """Any exception type during hash computation fails closed with error finding."""
    snap = _create_minimal_snapshot()
    snap.compute_snapshot_hash = MagicMock(side_effect=exc)

    sched = _create_minimal_schedule(snap)

    result = IndependentScheduleValidator.validate(snap, sched)

    assert result.status == ValidationStatus.INVALID
    assert result.valid is False
    assert result.is_approvable is False
    assert any(f.code == "SNAPSHOT_HASH_COMPUTATION_FAILED" for f in result.findings)


# =============================================================================
# 6. Real PlanningSnapshot Hash Canonical Behavior
# =============================================================================

def test_f11_real_planning_snapshot_hash_validation():
    """A real PlanningSnapshot instance validates its canonical hash without errors."""
    h_start = datetime(2026, 10, 15, 0, 0, tzinfo=timezone.utc)
    horizon = PlanningHorizon(start=h_start, end=h_start + timedelta(hours=24))

    snap = PlanningSnapshot(
        scenario_id="SCN-REAL-OP-01",
        snapshot_id="SNAP-REAL-OP-01",
        horizon=horizon,
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

    canonical_hash = snap.compute_snapshot_hash()
    assert _is_valid_sha256(canonical_hash) is True

    # With matching hash on schedule: passes
    sched_matching = _create_minimal_schedule(snap, snapshot_hash=canonical_hash)
    res_matching = IndependentScheduleValidator.validate(snap, sched_matching)
    assert res_matching.status == ValidationStatus.VALID
    assert res_matching.valid is True
    assert res_matching.input_snapshot_hash == canonical_hash

    # With tampered hash on schedule: fails closed
    sched_tampered = _create_minimal_schedule(snap, snapshot_hash="f" * 64)
    res_tampered = IndependentScheduleValidator.validate(snap, sched_tampered)
    assert res_tampered.status == ValidationStatus.INVALID
    assert res_tampered.valid is False
    assert any(f.code == "SNAPSHOT_HASH_MISMATCH" for f in res_tampered.findings)


# =============================================================================
# 7. Governance Integration (F3 & F11 Cross-Check)
# =============================================================================

@pytest.mark.asyncio
async def test_f11_plan_version_creation_blocked_if_validation_failed_closed():
    """If planning run validation failed closed (e.g. hash computation error),

    PlanGovernanceService.create_plan_version_from_run rejects it.
    """
    session = AsyncMock()
    service = PlanGovernanceService(session)

    run = MagicMock(spec=PlanningRunModel)
    run.run_id = "RUN-FAIL-HASH-01"
    run.status = "COMPLETED"
    # Run validation failed closed due to hash failure
    run.validation_status = "INVALID"
    run.is_approvable = False
    run.snapshot_hash = None
    run.schedule_result = {"status": "OPTIMAL"}

    service.run_repo.get_by_run_id = AsyncMock(return_value=run)

    with pytest.raises(PlanVersionApprovalBlockedError, match="validation status is 'INVALID'"):
        await service.create_plan_version_from_run(
            run_id="RUN-FAIL-HASH-01",
            actor=AuthUser(
                user_id="USR-01",
                username="planner",
                role=UserRole.MAINTENANCE_PLANNER,
            ),
        )
