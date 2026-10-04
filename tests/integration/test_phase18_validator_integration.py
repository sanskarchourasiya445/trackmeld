"""Integration tests for Phase 18 Track-Aware Validator Verification APIs."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_validate_schedule_api_executes_track_spatial_safety(client: AsyncClient):
    """POST /api/v1/planning/validate executes TRACK_SPATIAL_SAFETY check."""
    # 1. Obtain baseline schedule
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

    # 2. Submit to Independent Validator
    val_payload = {
        "scenario_id": "SCN-DEMO-001",
        "schedule": plan_data,
    }
    resp_val = await client.post("/api/v1/planning/validate", json=val_payload)
    assert resp_val.status_code == 200
    val_data = resp_val.json()

    # 3. Assert TRACK_SPATIAL_SAFETY executed independently
    assert "TRACK_SPATIAL_SAFETY" in val_data["checks_executed"]
    assert val_data["status"] == "VALID"
    assert val_data["valid"] is True
    assert val_data["is_approvable"] is True


@pytest.mark.asyncio
async def test_validate_schedule_api_detects_invalid_track_in_scenario(client: AsyncClient):
    """POST /api/v1/planning/validate detects invalid track assignments via API."""
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

    # Tamper with the first scheduled task ID to a non-existent task
    plan_data["scheduled_tasks"][0]["task_id"] = "TSK-GHOST-UNKNOWN"

    val_payload = {
        "scenario_id": "SCN-DEMO-001",
        "schedule": plan_data,
    }
    resp_val = await client.post("/api/v1/planning/validate", json=val_payload)
    assert resp_val.status_code == 200
    val_data = resp_val.json()

    assert val_data["status"] == "INVALID"
    assert val_data["valid"] is False
    assert val_data["is_approvable"] is False
    codes = [f["code"] for f in val_data["findings"]]
    assert "UNKNOWN_TASK_SCHEDULED" in codes


@pytest.mark.asyncio
async def test_validate_schedule_api_detects_tampered_schedule(client: AsyncClient):
    """POST /api/v1/planning/validate detects when task duration is tampered."""
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

    # Tamper with duration
    st = plan_data["scheduled_tasks"][0]
    st["duration_minutes"] = 999.0

    val_payload = {
        "scenario_id": "SCN-DEMO-001",
        "schedule": plan_data,
    }
    resp_val = await client.post("/api/v1/planning/validate", json=val_payload)
    assert resp_val.status_code == 200
    val_data = resp_val.json()

    assert val_data["status"] == "INVALID"
    assert val_data["valid"] is False
    codes = [f["code"] for f in val_data["findings"]]
    assert "DURATION_MISMATCH" in codes

