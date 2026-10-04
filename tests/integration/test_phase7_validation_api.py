"""Integration tests for Phase 7 Independent Schedule Validation and Diagnostics APIs."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_validate_schedule_api_valid(client: AsyncClient):
    """POST /api/v1/planning/validate returns VALID for a compliant baseline schedule."""
    # 1. Obtain a valid schedule from baseline priority-greedy
    resp_plan = await client.post(
        "/api/v1/planning/baseline",
        json={
            "scenario_id": "SCN-DEMO-001",
            "scheduler_type": "PRIORITY_GREEDY",
            "max_candidate_attempts": 20,
        },
    )
    assert resp_plan.status_code == 200
    plan_data = resp_plan.json()
    assert plan_data["status"] in ["COMPLETED", "COMPLETED_WITH_UNSCHEDULED_TASKS"]

    # 2. Submit to Independent Validator
    val_payload = {
        "scenario_id": "SCN-DEMO-001",
        "schedule": plan_data,
    }
    resp_val = await client.post("/api/v1/planning/validate", json=val_payload)
    assert resp_val.status_code == 200
    val_data = resp_val.json()
    assert val_data["status"] == "VALID", "; ".join(f"{f['code']}: {f['message']}" for f in val_data['findings'] if f['severity'] == 'ERROR')
    assert val_data["valid"] is True
    assert val_data["is_approvable"] is True
    assert val_data["error_count"] == 0
    assert len(val_data["schedule_identity"]) == 64
    assert len(val_data["checks_executed"]) >= 10
    assert "STRUCTURAL" in val_data["checks_executed"]
    assert "SECTION_OCCUPANCY" in val_data["checks_executed"]
    assert "TRAIN_MOVEMENT" in val_data["checks_executed"]
    assert "RESOURCES" in val_data["checks_executed"]


@pytest.mark.asyncio
async def test_validate_schedule_api_invalid_tampered(client: AsyncClient):
    """POST /api/v1/planning/validate detects violations when schedule is tampered."""
    # 1. Obtain a schedule
    resp_plan = await client.post(
        "/api/v1/planning/baseline",
        json={
            "scenario_id": "SCN-DEMO-001",
            "scheduler_type": "PRIORITY_GREEDY",
            "max_candidate_attempts": 20,
        },
    )
    assert resp_plan.status_code == 200
    plan_data = resp_plan.json()
    assert len(plan_data["scheduled_tasks"]) > 0

    # 2. Tamper with the duration of the first scheduled task
    st = plan_data["scheduled_tasks"][0]
    st["duration_minutes"] = 999  # Corrupt duration

    val_payload = {
        "scenario_id": "SCN-DEMO-001",
        "schedule": plan_data,
    }
    resp_val = await client.post("/api/v1/planning/validate", json=val_payload)
    assert resp_val.status_code == 200
    val_data = resp_val.json()

    # 3. Assert validator rejects tampered schedule
    assert val_data["status"] == "INVALID"
    assert val_data["valid"] is False
    assert val_data["is_approvable"] is False
    assert val_data["error_count"] > 0
    error_codes = [f["code"] for f in val_data["findings"]]
    assert "DURATION_MISMATCH" in error_codes


@pytest.mark.asyncio
async def test_validate_schedule_api_scenario_not_found(client: AsyncClient):
    """POST /api/v1/planning/validate returns 404 for unknown scenario."""
    val_payload = {
        "scenario_id": "SCN-DOES-NOT-EXIST",
        "schedule": {
            "scheduler_type": "FCFS",
            "scenario_id": "SCN-DOES-NOT-EXIST",
            "snapshot_id": "SNAP-NONE",
            "status": "COMPLETED",
            "scheduled_tasks": [],
            "unscheduled_tasks": [],
            "metrics": {
                "total_tasks": 0,
                "scheduled_tasks": 0,
                "unscheduled_tasks": 0,
                "scheduled_duration_minutes": 0.0,
                "unscheduled_duration_minutes": 0.0,
                "scheduled_percentage": 0.0,
                "total_delay_minutes": 0.0,
                "average_delay_minutes": 0.0,
                "track_possession_minutes": 0.0,
                "resource_utilization": {},
            },
            "execution_time_ms": 1.0,
            "decision_trace": [],
        },
    }
    response = await client.post("/api/v1/planning/validate", json=val_payload)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_diagnostics_api_success(client: AsyncClient):
    """POST /api/v1/planning/diagnostics generates root-cause analysis on unscheduled tasks."""
    # Obtain a schedule first
    resp_plan = await client.post(
        "/api/v1/planning/baseline",
        json={
            "scenario_id": "SCN-DEMO-001",
            "scheduler_type": "PRIORITY_GREEDY",
            "max_candidate_attempts": 20,
        },
    )
    assert resp_plan.status_code == 200
    plan_data = resp_plan.json()

    payload = {
        "scenario_id": "SCN-DEMO-001",
        "schedule": plan_data,
    }
    response = await client.post("/api/v1/planning/diagnostics", json=payload)
    assert response.status_code == 200
    diag_data = response.json()

    assert diag_data["scenario_id"] == "SCN-DEMO-001"
    assert "snapshot_id" in diag_data
    assert "total_unscheduled_tasks" in diag_data
    assert "diagnostics" in diag_data
    assert isinstance(diag_data["diagnostics"], list)

    for task_diag in diag_data["diagnostics"]:
        assert "task_id" in task_diag
        assert "task_code" in task_diag
        assert "primary_reason" in task_diag
        assert "relaxation_analyses" in task_diag
        # Ensure relaxation scenarios are strictly marked hypothetical and not approvable
        for rel in task_diag["relaxation_analyses"]:
            assert rel["hypothetical"] is True
            assert rel["approvable"] is False


@pytest.mark.asyncio
async def test_diagnostics_api_scenario_not_found(client: AsyncClient):
    """POST /api/v1/planning/diagnostics returns 404 for missing scenario."""
    payload = {
        "scenario_id": "SCN-DOES-NOT-EXIST",
        "schedule": {
            "scheduler_type": "FCFS",
            "scenario_id": "SCN-DOES-NOT-EXIST",
            "snapshot_id": "SNAP-NONE",
            "status": "COMPLETED",
            "scheduled_tasks": [],
            "unscheduled_tasks": [],
            "metrics": {
                "total_tasks": 0,
                "scheduled_tasks": 0,
                "unscheduled_tasks": 0,
                "scheduled_duration_minutes": 0.0,
                "unscheduled_duration_minutes": 0.0,
                "scheduled_percentage": 0.0,
                "total_delay_minutes": 0.0,
                "average_delay_minutes": 0.0,
                "track_possession_minutes": 0.0,
                "resource_utilization": {},
            },
            "execution_time_ms": 1.0,
            "decision_trace": [],
        },
    }
    response = await client.post("/api/v1/planning/diagnostics", json=payload)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_optimize_with_validation_flag(client: AsyncClient):
    """POST /api/v1/planning/optimize embeds independent validation when validate_after_solve is True."""
    payload = {
        "scenario_id": "SCN-DEMO-001",
        "time_limit_seconds": 5.0,
        "num_search_workers": 1,
        "random_seed": 0,
        "validate_after_solve": True,
    }
    response = await client.post("/api/v1/planning/optimize", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["scheduler_type"] == "CP_SAT"
    assert "validation" in data
    val = data["validation"]
    assert val is not None
    assert val["status"] in ["VALID", "INVALID"]
    assert "schedule_identity" in val
    assert len(val["schedule_identity"]) == 64
    assert "is_approvable" in val
