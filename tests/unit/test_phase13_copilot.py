"""
Unit tests for Phase 13 Read-Only Copilot & Decision Support.
Verifies tool specs, read-only guardrails, mutation refusals, and uncertainty semantics.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.schemas.copilot import (
    CopilotQueryRequest,
    EvidenceType,
)
from backend.app.services.copilot.tools import CopilotToolRegistry
from backend.app.services.copilot.engine import CopilotEngine


def test_copilot_tool_registry_specs():
    """Verify tool specifications are complete, typed, and read-only."""
    tools = CopilotToolRegistry.list_tools()
    assert len(tools) == 5
    tool_names = [t.name for t in tools]
    assert "get_task_decision" in tool_names
    assert "get_conflicts_for_task" in tool_names
    assert "get_run_summary" in tool_names
    assert "get_rule_provenance" in tool_names
    assert "get_plan_version_status" in tool_names

    for t in tools:
        assert len(t.description) > 10
        assert len(t.parameters) > 0


def test_copilot_mutation_refusal():
    """Verify strictly read-only guardrail blocks any write, approval, or deletion intent."""
    mutation_prompts = [
        "Please approve plan version 1 immediately",
        "Sign off on this schedule",
        "Delete task TSK-0001 from the scenario",
        "Cancel planning run RUN-20261002-12345678",
        "Reschedule task TSK-0007 to start at 05:00 UTC",
        "Move window for task TSK-0002",
        "Force placement on section SEC-NDLS-GZB",
    ]

    for p in mutation_prompts:
        refusal = CopilotEngine.check_mutation_refusal(p)
        assert refusal is not None, f"Expected refusal for: {p}"
        assert "Strictly Read-Only" in refusal
        assert "COMPLETED ≠ APPROVED" in refusal


def test_copilot_entity_id_extraction():
    """Verify extraction of railway entity identifiers from natural language queries."""
    task_id, run_id, rule_id, pv_id = CopilotEngine.extract_entity_ids("Why was TSK-0007 not scheduled in run RUN-20261002-ABC?")
    assert task_id == "TSK-0007"
    assert run_id == "RUN-20261002-ABC"
    assert rule_id is None
    assert pv_id is None

    t_id, _, r_id, _ = CopilotEngine.extract_entity_ids("What is the clause for rule RULE-STAT-RBP-1502C?")
    assert t_id is None
    assert r_id == "RULE-STAT-RBP-1502C"

    _, _, _, p_id = CopilotEngine.extract_entity_ids("Show me status of plan version 2")
    assert p_id == "2"


@pytest.mark.asyncio
async def test_copilot_rule_provenance(db_session: AsyncSession):
    """Verify retrieval of verified railway rule clauses without hallucination."""
    ev = await CopilotToolRegistry.get_rule_provenance(db_session, "RULE-STAT-RBP-1502C")
    assert ev is not None
    assert ev.evidence_type == EvidenceType.RULE_PROVENANCE
    assert ev.evidence_id == "RULE:RULE-STAT-RBP-1502C"
    assert ev.data["classification"] == "VERIFIED_SOURCE"
    assert "15.02" in ev.data["clause_reference"]


@pytest.mark.asyncio
async def test_copilot_task_decision(db_session: AsyncSession):
    """Verify task decision retrieval from operational database and planning snapshot."""
    # Scheduled task
    ev_sched = await CopilotToolRegistry.get_task_decision(db_session, "TSK-0001", scenario_id="SCN-DEMO-001")
    assert ev_sched is not None
    assert ev_sched.evidence_type == EvidenceType.TASK_DECISION
    assert ev_sched.data["task_id"] == "TSK-0001"
    assert ev_sched.data["mandatory"] is True

    # Unscheduled task
    ev_unsched = await CopilotToolRegistry.get_task_decision(db_session, "TSK-0007", scenario_id="SCN-DEMO-001")
    assert ev_unsched is not None
    assert ev_unsched.evidence_type == EvidenceType.TASK_DECISION
    assert ev_unsched.data["task_id"] == "TSK-0007"


@pytest.mark.asyncio
async def test_copilot_uncertainty_handling(db_session: AsyncSession):
    """Verify unknown entities return explicit uncertainty without inventing facts."""
    req = CopilotQueryRequest(prompt="Why was task TSK-9999 rejected?", scenario_id="SCN-DEMO-001")
    resp = await CopilotEngine.explain(db_session, req)
    assert resp.evidence[0].evidence_type == EvidenceType.UNCERTAINTY
    assert "Uncertainty Notice" in resp.answer
    assert "TSK-9999" in resp.answer


@pytest.mark.asyncio
async def test_copilot_mutation_refusal_execution(db_session: AsyncSession):
    """Verify end-to-end execution of refusal on write request."""
    req = CopilotQueryRequest(prompt="Please approve plan version PV-SCN-DEMO-001-V001")
    resp = await CopilotEngine.explain(db_session, req)
    assert resp.provider_used == "GOVERNANCE_GUARDRAIL"
    assert resp.evidence[0].evidence_type == EvidenceType.REFUSAL
    assert "Strictly Read-Only" in resp.answer
