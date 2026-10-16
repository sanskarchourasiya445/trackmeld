"""Unit and API regression tests for Batch 19:
- Scope A (VAL-003): Block schedules with unscheduled mandatory tasks.
- Scope B (SEC-002): Enforce RBAC permissions on operational write/compute and read endpoints.
"""

from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from starlette.testclient import TestClient
from fastapi import HTTPException

from backend.app.main import app
from backend.app.config import get_settings
from backend.app.db.session import get_db_session
from backend.app.core.auth import (
    require_permission,
    get_current_user,
    DEMO_CREDENTIALS,
    DEFAULT_DEMO_USER,
    UserRole,
    AuthUser,
)
from backend.app.domain.temporal import TimeInterval
from backend.app.domain.planning_snapshot import PlanningSnapshot
from backend.app.domain.scheduling import (
    ScheduleResult,
    ScheduledTaskResult,
    UnscheduledTaskResult,
    SchedulerType,
    SchedulerStatus,
    ScheduleMetrics,
)
from backend.app.services.validation.models import (
    ValidationStatus,
    ValidationSeverity,
    ValidationCategory,
)
from backend.app.services.validation.validator import IndependentScheduleValidator
from backend.app.services.validation.exceptions import ScheduleApprovalBlockedError


# =============================================================================
# FIXTURES FOR SCOPE A (VAL-003)
# =============================================================================

@pytest.fixture
def horizon():
    start = datetime(2026, 10, 15, 0, 0, tzinfo=timezone.utc)
    return TimeInterval(start=start, end=start + timedelta(hours=24))


@pytest.fixture
def val_snapshot(horizon):
    """Snapshot with one MANDATORY task (TSK-MANDATORY) and one OPTIONAL task (TSK-OPTIONAL)."""
    task_mandatory = {
        "task_id": "TSK-MANDATORY",
        "task_code": "TC-MAND",
        "section_id": "SEC-01",
        "priority": "CRITICAL",
        "mandatory": True,
        "window_start": horizon.start + timedelta(hours=1),
        "window_end": horizon.start + timedelta(hours=10),
        "estimated_duration_minutes": 120,
        "safety_buffer_before_minutes": 15,
        "safety_buffer_after_minutes": 15,
        "requires_power_block": False,
        "requires_traffic_block": True,
        "resource_requirements": [],
    }

    task_optional = {
        "task_id": "TSK-OPTIONAL",
        "task_code": "TC-OPT",
        "section_id": "SEC-02",
        "priority": "LOW",
        "mandatory": False,
        "window_start": horizon.start + timedelta(hours=1),
        "window_end": horizon.start + timedelta(hours=10),
        "estimated_duration_minutes": 60,
        "safety_buffer_before_minutes": 15,
        "safety_buffer_after_minutes": 15,
        "requires_power_block": False,
        "requires_traffic_block": True,
        "resource_requirements": [],
    }

    tasks = [task_mandatory, task_optional]

    return PlanningSnapshot(
        scenario_id="SCN-VAL003-TEST",
        snapshot_id="SNAP-VAL003-01",
        horizon=horizon,
        tasks=tasks,
        tasks_map={t["task_id"]: dict(t) for t in tasks},
        work_orders_map={},
        resources=[],
        resources_map={},
        resource_availabilities=[],
        dependencies=[],
        dependencies_by_successor={},
        dependencies_by_predecessor={},
        sections_map={
            "SEC-01": {"section_id": "SEC-01", "electrified": True},
            "SEC-02": {"section_id": "SEC-02", "electrified": True},
        },
        rules_map={},
        train_passes=[],
    )


def _make_unscheduled_result(
    task_id: str,
    task_code: str,
    mandatory: bool = False,
    reason_codes: list = None,
) -> UnscheduledTaskResult:
    return UnscheduledTaskResult(
        task_id=task_id,
        task_code=task_code,
        mandatory=mandatory,
        priority_score=10.0,
        reason_codes=reason_codes or ["RESOURCE_UNAVAILABLE"],
        conflicts=[],
        attempted_candidates_count=0,
        diagnostic_message="Unplaced task",
    )


def _build_schedule(
    snapshot: PlanningSnapshot,
    scheduled: list[ScheduledTaskResult],
    unscheduled: list[UnscheduledTaskResult],
    status: SchedulerStatus = SchedulerStatus.OPTIMAL,
) -> ScheduleResult:
    return ScheduleResult(
        schedule_id="SCHED-VAL003-TEST",
        scheduler_type=SchedulerType.CP_SAT,
        scheduler_version="1.0.0",
        scenario_id=snapshot.scenario_id,
        snapshot_id=snapshot.snapshot_id,
        planning_start=snapshot.horizon.start,
        planning_end=snapshot.horizon.end,
        status=status,
        scheduled_tasks=scheduled,
        unscheduled_tasks=unscheduled,
        metrics=ScheduleMetrics(
            total_tasks=len(snapshot.tasks),
            scheduled_tasks=len(scheduled),
            unscheduled_tasks=len(unscheduled),
            completion_rate=len(scheduled) / max(1, len(snapshot.tasks)),
            mandatory_tasks=1,
            mandatory_scheduled=1 if any(t.task_id == "TSK-MANDATORY" for t in scheduled) else 0,
            mandatory_unscheduled=1 if any(t.task_id == "TSK-MANDATORY" for t in unscheduled) else 0,
            mandatory_completion_rate=1.0 if any(t.task_id == "TSK-MANDATORY" for t in scheduled) else 0.0,
            total_scheduled_duration_minutes=sum(t.duration_minutes for t in scheduled),
            total_possession_duration_minutes=sum(t.possession_interval.duration_minutes for t in scheduled),
            total_priority_score_available=100.0,
            scheduled_priority_score=100.0,
            unscheduled_priority_score=0.0,
            priority_score_capture_rate=1.0,
        ),
        configuration={},
        execution_time_ms=10.0,
        decision_trace=[],
    )


# =============================================================================
# SCOPE A TESTS (VAL-003): MANDATORY UNSCHEDULED BLOCKS APPROVAL
# =============================================================================

def test_val003_mandatory_task_unscheduled_is_error_and_blocks_approval(val_snapshot, horizon):
    """VAL-003: When a mandatory task cannot be scheduled, validator emits ERROR, marks INVALID, and blocks approval."""
    # Mandatory task is unscheduled with reason codes
    unscheduled_mandatory = _make_unscheduled_result(
        task_id="TSK-MANDATORY",
        task_code="TC-MAND",
        mandatory=True,
        reason_codes=["RESOURCE_UNAVAILABLE"],
    )

    # Optional task is scheduled
    st_optional = ScheduledTaskResult(
        task_id="TSK-OPTIONAL",
        task_code="TC-OPT",
        interval=TimeInterval(start=horizon.start + timedelta(hours=2), end=horizon.start + timedelta(hours=3)),
        possession_interval=TimeInterval(start=horizon.start + timedelta(hours=1, minutes=45), end=horizon.start + timedelta(hours=3, minutes=15)),
        duration_minutes=60,
        affected_sections=["SEC-02"],
        assigned_resources=[],
        sequence_order=1,
    )

    schedule = _build_schedule(val_snapshot, scheduled=[st_optional], unscheduled=[unscheduled_mandatory])

    res = IndependentScheduleValidator.validate(val_snapshot, schedule)

    # Must be marked INVALID
    assert res.status == ValidationStatus.INVALID
    assert res.valid is False
    assert res.is_approvable is False
    assert res.error_count >= 1

    # Finding must be code MANDATORY_TASK_UNSCHEDULED with severity ERROR
    mandatory_findings = [f for f in res.findings if f.code == "MANDATORY_TASK_UNSCHEDULED"]
    assert len(mandatory_findings) == 1
    f = mandatory_findings[0]
    assert f.severity == ValidationSeverity.ERROR
    assert f.category == ValidationCategory.MANDATORY
    assert f.task_id == "TSK-MANDATORY"

    # assert_schedule_approvable must raise ScheduleApprovalBlockedError
    with pytest.raises(ScheduleApprovalBlockedError) as exc_info:
        IndependentScheduleValidator.assert_schedule_approvable(val_snapshot, schedule)
    assert exc_info.value.status == "INVALID"
    assert exc_info.value.error_count >= 1


def test_val003_optional_task_unscheduled_remains_valid_and_approvable(val_snapshot, horizon):
    """VAL-003: When only an optional task is unscheduled, schedule remains VALID and approvable."""
    # Mandatory task is scheduled
    st_mandatory = ScheduledTaskResult(
        task_id="TSK-MANDATORY",
        task_code="TC-MAND",
        interval=TimeInterval(start=horizon.start + timedelta(hours=2), end=horizon.start + timedelta(hours=4)),
        possession_interval=TimeInterval(start=horizon.start + timedelta(hours=1, minutes=45), end=horizon.start + timedelta(hours=4, minutes=15)),
        duration_minutes=120,
        affected_sections=["SEC-01"],
        assigned_resources=[],
        sequence_order=1,
    )

    # Optional task is unscheduled
    unscheduled_optional = _make_unscheduled_result(
        task_id="TSK-OPTIONAL",
        task_code="TC-OPT",
        mandatory=False,
        reason_codes=["RESOURCE_UNAVAILABLE"],
    )

    schedule = _build_schedule(val_snapshot, scheduled=[st_mandatory], unscheduled=[unscheduled_optional])

    res = IndependentScheduleValidator.validate(val_snapshot, schedule)

    # Mandatory check passes; no MANDATORY_TASK_UNSCHEDULED finding
    assert not any(f.code == "MANDATORY_TASK_UNSCHEDULED" for f in res.findings)
    assert res.error_count == 0
    assert res.status == ValidationStatus.VALID
    assert res.valid is True
    assert res.is_approvable is True

    # assert_schedule_approvable succeeds
    approved_res = IndependentScheduleValidator.assert_schedule_approvable(val_snapshot, schedule)
    assert approved_res.is_approvable is True


def test_val003_mixed_tasks_unscheduled_blocks_approval(val_snapshot, horizon):
    """VAL-003: When both mandatory and optional tasks are unscheduled, mandatory error dominates and blocks approval."""
    unscheduled_mandatory = _make_unscheduled_result(
        task_id="TSK-MANDATORY",
        task_code="TC-MAND",
        mandatory=True,
        reason_codes=["TRAIN_MOVEMENT_CONFLICT"],
    )
    unscheduled_optional = _make_unscheduled_result(
        task_id="TSK-OPTIONAL",
        task_code="TC-OPT",
        mandatory=False,
        reason_codes=["RESOURCE_UNAVAILABLE"],
    )

    schedule = _build_schedule(
        val_snapshot,
        scheduled=[],
        unscheduled=[unscheduled_mandatory, unscheduled_optional],
        status=SchedulerStatus.FEASIBLE,
    )

    res = IndependentScheduleValidator.validate(val_snapshot, schedule)

    assert res.status == ValidationStatus.INVALID
    assert res.valid is False
    assert res.is_approvable is False
    assert any(f.code == "MANDATORY_TASK_UNSCHEDULED" and f.severity == ValidationSeverity.ERROR for f in res.findings)

    with pytest.raises(ScheduleApprovalBlockedError):
        IndependentScheduleValidator.assert_schedule_approvable(val_snapshot, schedule)


def test_val003_mandatory_task_silently_dropped_remains_error(val_snapshot, horizon):
    """VAL-003: Mandatory task silently dropped (not in unscheduled_tasks) produces MANDATORY_TASK_SILENTLY_DROPPED ERROR."""
    # Neither scheduled nor accounted for in unscheduled
    schedule = _build_schedule(val_snapshot, scheduled=[], unscheduled=[])

    res = IndependentScheduleValidator.validate(val_snapshot, schedule)

    assert res.status == ValidationStatus.INVALID
    assert res.is_approvable is False
    assert any(f.code == "MANDATORY_TASK_SILENTLY_DROPPED" and f.severity == ValidationSeverity.ERROR for f in res.findings)


# =============================================================================
# SCOPE B TESTS (SEC-002): ENFORCE RBAC PERMISSIONS ON API ROUTERS
# =============================================================================

@pytest.fixture
def test_client():
    return TestClient(app)


def test_sec002_viewer_forbidden_on_operational_write_endpoints(test_client):
    """SEC-002: Viewer token (lacking write:operational) is denied with HTTP 403 on all operational write/compute routes."""
    viewer_headers = {"Authorization": "Bearer viewer-token-2026"}

    # 1. POST /api/v1/planning-runs (create run)
    resp = test_client.post(
        "/api/v1/planning-runs",
        json={"scenario_id": "SCN-DEMO-001", "scheduler_type": "CP_SAT"},
        headers=viewer_headers,
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"
    assert "write:operational" in resp.json()["error"]["message"]

    # 2. POST /api/v1/planning-runs/{run_id}/cancel (cancel run)
    resp = test_client.post(
        "/api/v1/planning-runs/RUN-TEST-001/cancel",
        headers=viewer_headers,
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"

    # 3. POST /api/v1/planning/optimize (run CP-SAT optimization)
    resp = test_client.post(
        "/api/v1/planning/optimize",
        json={"scenario_id": "SCN-DEMO-001"},
        headers=viewer_headers,
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"

    # 4. POST /api/v1/planning/baseline (run baseline scheduler)
    resp = test_client.post(
        "/api/v1/planning/baseline",
        json={"scenario_id": "SCN-DEMO-001", "scheduler_type": "FCFS"},
        headers=viewer_headers,
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"

    # 5. POST /api/v1/planning/benchmark (run benchmark comparison)
    resp = test_client.post(
        "/api/v1/planning/benchmark",
        json={"scenario_id": "SCN-DEMO-001"},
        headers=viewer_headers,
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


def test_sec002_approver_forbidden_on_operational_writes(test_client):
    """SEC-002: Approver (role OPERATOR with plan:approve but without write:operational) cannot trigger runs or solvers."""
    approver_headers = {"Authorization": "Bearer approver-token-2026"}

    # Approver cannot submit planning run
    resp = test_client.post(
        "/api/v1/planning-runs",
        json={"scenario_id": "SCN-DEMO-001", "scheduler_type": "CP_SAT"},
        headers=approver_headers,
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"

    # Approver cannot trigger solver
    resp = test_client.post(
        "/api/v1/planning/optimize",
        json={"scenario_id": "SCN-DEMO-001"},
        headers=approver_headers,
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


def test_sec002_unauthenticated_dev_viewer_forbidden_on_writes(test_client):
    """SEC-002: Unauthenticated callers default to read-only demo viewer and are denied HTTP 403 on write endpoints."""
    # No Authorization header
    resp = test_client.post(
        "/api/v1/planning-runs",
        json={"scenario_id": "SCN-DEMO-001", "scheduler_type": "CP_SAT"},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


def test_sec002_restricted_viewer_forbidden_on_operational_reads(test_client):
    """SEC-002: Restricted token (lacking read:operational) is denied with HTTP 403 on operational read routes."""
    restricted_headers = {"Authorization": "Bearer restricted-token-2026"}

    routes_to_test = [
        ("GET", "/api/v1/tasks", None),
        ("GET", "/api/v1/tasks/TSK-01", None),
        ("GET", "/api/v1/scenarios", None),
        ("GET", "/api/v1/scenarios/SCN-01", None),
        ("GET", "/api/v1/scenarios/SCN-01/manifest", None),
        ("GET", "/api/v1/scenarios/SCN-01/bundle", None),
        ("GET", "/api/v1/scenarios/SCN-01/traversals", None),
        ("GET", "/api/v1/work-orders", None),
        ("GET", "/api/v1/work-orders/WO-01", None),
        ("GET", "/api/v1/planning-runs", None),
        ("GET", "/api/v1/planning-runs/RUN-01", None),
        ("GET", "/api/v1/planning-runs/RUN-01/result", None),
        ("GET", "/api/v1/movements", None),
        ("GET", "/api/v1/movements/MOV-01", None),
        ("GET", "/api/v1/resources", None),
        ("GET", "/api/v1/resources/RES-01", None),
        ("GET", "/api/v1/resources/RES-01/availability", None),
        ("POST", "/api/v1/planning/validate", {"scenario_id": "SCN-01"}),
        ("POST", "/api/v1/planning/diagnostics", {"scenario_id": "SCN-01"}),
        ("POST", "/api/v1/compatibility/evaluate-task", {"task_id": "TSK-01"}),
        ("POST", "/api/v1/copilot/explain", {"prompt": "Why was task delayed?"}),
    ]

    for method, path, payload in routes_to_test:
        if method == "GET":
            resp = test_client.get(path, headers=restricted_headers)
        else:
            resp = test_client.post(path, json=payload or {}, headers=restricted_headers)
        assert resp.status_code == 403, f"Expected 403 on {method} {path}, got {resp.status_code}"
        assert resp.json()["error"]["code"] == "FORBIDDEN"
        assert "read:operational" in resp.json()["error"]["message"]


def test_sec002_restricted_viewer_permitted_on_reference_reads(test_client):
    """SEC-002: Restricted token (possessing read:reference) is authorized for reference and tooling endpoints."""
    restricted_headers = {"Authorization": "Bearer restricted-token-2026"}

    # 1. Tooling endpoint has no database dependency and returns HTTP 200
    resp = test_client.get("/api/v1/copilot/tools", headers=restricted_headers)
    assert resp.status_code == 200

    # 2. Reference routes succeed with 200 without 403 Forbidden
    async def _mock_db():
        mock_s = AsyncMock()
        mock_res = MagicMock()
        mock_res.scalars.return_value.all.return_value = []
        mock_res.scalar.return_value = 0
        mock_s.execute.return_value = mock_res
        yield mock_s

    app.dependency_overrides[get_db_session] = _mock_db
    try:
        reference_routes = [
            "/api/v1/corridors",
            "/api/v1/sections",
            "/api/v1/stations",
            "/api/v1/rules",
            "/api/v1/tracks",
            "/api/v1/topology/nodes",
            "/api/v1/trains",
        ]

        for path in reference_routes:
            r = test_client.get(path, headers=restricted_headers)
            assert r.status_code == 200, f"Expected 200 for reference route {path}, got {r.status_code}"
    finally:
        app.dependency_overrides.pop(get_db_session, None)


@pytest.mark.asyncio
async def test_sec002_role_permission_resolution():
    """SEC-002: Direct test of role permissions against canonical requirements."""
    planner = DEMO_CREDENTIALS["planner-token-2026"]
    admin = DEMO_CREDENTIALS["admin-token-2026"]
    viewer = DEMO_CREDENTIALS["viewer-token-2026"]
    approver = DEMO_CREDENTIALS["approver-token-2026"]
    restricted = DEMO_CREDENTIALS["restricted-token-2026"]

    # Write permissions
    write_check = require_permission("write:operational")
    assert await write_check(planner) == planner
    assert await write_check(admin) == admin
    with pytest.raises(HTTPException) as exc_p:
        await write_check(viewer)
    assert exc_p.value.status_code == 403

    with pytest.raises(HTTPException) as exc_app:
        await write_check(approver)
    assert exc_app.value.status_code == 403

    # Operational Read permissions
    read_check = require_permission("read:operational")
    assert await read_check(planner) == planner
    assert await read_check(admin) == admin
    assert await read_check(viewer) == viewer
    assert await read_check(approver) == approver
    with pytest.raises(HTTPException) as exc_restr:
        await read_check(restricted)
    assert exc_restr.value.status_code == 403

    # Reference Read permissions (all roles including restricted viewer have read:reference)
    ref_check = require_permission("read:reference")
    assert await ref_check(planner) == planner
    assert await ref_check(admin) == admin
    assert await ref_check(viewer) == viewer
    assert await ref_check(approver) == approver
    assert await ref_check(restricted) == restricted
