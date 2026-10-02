"""
Integration tests for Phase 13 Read-Only Copilot REST APIs.
Verifies HTTP endpoints, evidence item delivery, refusal guardrails, and uncertainty reporting.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_copilot_tools_endpoint(client: AsyncClient):
    """GET /api/v1/copilot/tools returns list of typed read-only tool specifications."""
    resp = await client.get("/api/v1/copilot/tools")
    assert resp.status_code == 200
    tools = resp.json()
    assert isinstance(tools, list)
    assert len(tools) == 5
    tool_names = [t["name"] for t in tools]
    assert "get_task_decision" in tool_names
    assert "get_conflicts_for_task" in tool_names
    assert "get_run_summary" in tool_names
    assert "get_rule_provenance" in tool_names
    assert "get_plan_version_status" in tool_names


@pytest.mark.asyncio
async def test_copilot_explain_scheduled_task(client: AsyncClient):
    """POST /api/v1/copilot/explain provides grounded analysis for scheduled task."""
    payload = {
        "prompt": "Explain the decision and assigned slot for task TSK-0001",
        "scenario_id": "SCN-DEMO-001",
    }
    resp = await client.post("/api/v1/copilot/explain", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["provider_used"] == "DETERMINISTIC_EVIDENCE_ENGINE"
    assert "TSK-0001" in data["answer"]
    assert len(data["evidence"]) >= 1
    assert data["evidence"][0]["evidence_id"] == "TASK:TSK-0001"
    assert "TASK:TSK-0001" in data["answer"]


@pytest.mark.asyncio
async def test_copilot_explain_unscheduled_task(client: AsyncClient):
    """POST /api/v1/copilot/explain diagnoses unscheduled task with root-cause conflicts."""
    payload = {
        "prompt": "Why was TSK-0007 not scheduled?",
        "scenario_id": "SCN-DEMO-001",
    }
    resp = await client.post("/api/v1/copilot/explain", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert "TSK-0007" in data["answer"]
    assert "Unscheduled Decision Analysis" in data["answer"]
    assert len(data["evidence"]) >= 1
    ev_ids = [e["evidence_id"] for e in data["evidence"]]
    assert "TASK:TSK-0007" in ev_ids


@pytest.mark.asyncio
async def test_copilot_explain_rule(client: AsyncClient):
    """POST /api/v1/copilot/explain retrieves statutory operating rule provenance."""
    payload = {
        "prompt": "Explain rule RULE-STAT-RBP-1502C and its safety classification",
    }
    resp = await client.post("/api/v1/copilot/explain", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert "RULE-STAT-RBP-1502C" in data["answer"]
    assert "VERIFIED_SOURCE" in data["answer"]
    assert len(data["evidence"]) == 1
    assert data["evidence"][0]["evidence_type"] == "RULE_PROVENANCE"


@pytest.mark.asyncio
async def test_copilot_mutation_refusal(client: AsyncClient):
    """POST /api/v1/copilot/explain strictly refuses write/approval requests."""
    payload = {
        "prompt": "Please approve the plan version PV-SCN-DEMO-001-V001",
    }
    resp = await client.post("/api/v1/copilot/explain", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["provider_used"] == "GOVERNANCE_GUARDRAIL"
    assert "Strictly Read-Only" in data["answer"]
    assert "COMPLETED ≠ APPROVED" in data["answer"]
    assert data["evidence"][0]["evidence_type"] == "REFUSAL"


@pytest.mark.asyncio
async def test_copilot_unknown_entity_uncertainty(client: AsyncClient):
    """POST /api/v1/copilot/explain reports uncertainty on missing entities without fabricating."""
    payload = {
        "prompt": "Why was task TSK-8888 rejected?",
        "scenario_id": "SCN-DEMO-001",
    }
    resp = await client.post("/api/v1/copilot/explain", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert "Uncertainty Notice" in data["answer"]
    assert "TSK-8888" in data["answer"]
    assert data["evidence"][0]["evidence_type"] == "UNCERTAINTY"
