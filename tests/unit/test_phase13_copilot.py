"""
Unit tests for Phase 13 Read-Only Copilot & Decision Support.
Verifies tool specs, read-only guardrails, mutation refusals, and uncertainty semantics.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.schemas.copilot import (
    CopilotQueryRequest,
    EvidenceType,
)
from backend.app.services.copilot.tools import CopilotToolRegistry
from backend.app.services.copilot.engine import CopilotEngine
from backend.app.db.models import RailwayRuleModel, MaintenanceTaskModel, PlanningRunModel
from backend.app.domain.enums import RuleClass, DataClass, TaskType, WorkDepartment


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
async def test_copilot_rule_provenance():
    """Verify retrieval of verified railway rule clauses without hallucination (isolated unit test)."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_rule = MagicMock(spec=RailwayRuleModel)
    mock_rule.rule_id = "RULE-STAT-RBP-1502C"
    mock_rule.title = "Statutory Rolling Block Possession"
    mock_rule.category = "SAFETY"
    mock_rule.rule_class = RuleClass.VERIFIED_SOURCE
    mock_rule.section_page = "Para 15.02 / SR 15.02-1"
    mock_rule.source_document = "Indian Railways Operating Manual (G&SR)"
    mock_rule.normalized_summary = "Mandatory 4-hour maintenance block window"
    mock_rule.original_text = "Mandatory 4-hour maintenance block window"
    mock_rule.source_id = "SRC-001"

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_rule
    mock_session.execute.return_value = mock_res

    ev = await CopilotToolRegistry.get_rule_provenance(mock_session, "RULE-STAT-RBP-1502C")
    assert ev is not None
    assert ev.evidence_type == EvidenceType.RULE_PROVENANCE
    assert ev.evidence_id == "RULE:RULE-STAT-RBP-1502C"
    assert ev.data["classification"] == "VERIFIED_SOURCE"
    assert "15.02" in ev.data["clause_reference"]


@pytest.mark.asyncio
async def test_copilot_task_decision():
    """Verify task decision retrieval from operational database and planning snapshot (isolated unit test)."""
    mock_session = AsyncMock(spec=AsyncSession)

    # 1. Scheduled task TSK-0001
    mock_task_1 = MagicMock(spec=MaintenanceTaskModel)
    mock_task_1.task_id = "TSK-0001"
    mock_task_1.task_code = "TSK-0001"
    mock_task_1.scenario_id = "SCN-DEMO-001"
    mock_task_1.description = "Track Tamping"
    mock_task_1.title = "Track Tamping"
    mock_task_1.task_type = TaskType.TRACK_MAINTENANCE
    mock_task_1.department = WorkDepartment.ENGINEERING
    mock_task_1.section_id = "SEC-NDLS-GZB"
    mock_task_1.estimated_duration_minutes = 120
    mock_task_1.mandatory = True
    mock_task_1.requires_traffic_block = True
    mock_task_1.requires_power_block = False
    mock_task_1.safety_buffer_before_minutes = 15
    mock_task_1.safety_buffer_after_minutes = 15

    mock_run_1 = MagicMock(spec=PlanningRunModel)
    mock_run_1.result = {
        "scheduled_tasks": [
            {
                "task_id": "TSK-0001",
                "start_time": "2026-10-10T01:00:00Z",
                "end_time": "2026-10-10T03:00:00Z",
                "assigned_section": "SEC-NDLS-GZB",
                "priority_score": 98.5,
            }
        ],
        "unscheduled_tasks": [],
    }

    mock_res_task_1 = MagicMock()
    mock_res_task_1.scalar_one_or_none.return_value = mock_task_1
    mock_res_run_1 = MagicMock()
    mock_res_run_1.scalar_one_or_none.return_value = mock_run_1

    # 2. Unscheduled task TSK-0007
    mock_task_7 = MagicMock(spec=MaintenanceTaskModel)
    mock_task_7.task_id = "TSK-0007"
    mock_task_7.task_code = "TSK-0007"
    mock_task_7.scenario_id = "SCN-DEMO-001"
    mock_task_7.description = "Deep Track Screening"
    mock_task_7.title = "Deep Track Screening"
    mock_task_7.task_type = TaskType.TRACK_MAINTENANCE
    mock_task_7.department = WorkDepartment.ENGINEERING
    mock_task_7.section_id = "SEC-NDLS-GZB"
    mock_task_7.estimated_duration_minutes = 180
    mock_task_7.mandatory = False
    mock_task_7.requires_traffic_block = True
    mock_task_7.requires_power_block = False
    mock_task_7.safety_buffer_before_minutes = 15
    mock_task_7.safety_buffer_after_minutes = 15

    mock_run_7 = MagicMock(spec=PlanningRunModel)
    mock_run_7.result = {
        "scheduled_tasks": [],
        "unscheduled_tasks": [
            {
                "task_id": "TSK-0007",
                "reason_codes": ["TRAIN_MOVEMENT_CONFLICT"],
            }
        ],
    }

    mock_res_task_7 = MagicMock()
    mock_res_task_7.scalar_one_or_none.return_value = mock_task_7
    mock_res_run_7 = MagicMock()
    mock_res_run_7.scalar_one_or_none.return_value = mock_run_7

    mock_session.execute.side_effect = [
        mock_res_task_1, mock_res_run_1,
        mock_res_task_7, mock_res_run_7,
    ]

    ev_sched = await CopilotToolRegistry.get_task_decision(mock_session, "TSK-0001", scenario_id="SCN-DEMO-001")
    assert ev_sched is not None
    assert ev_sched.evidence_type == EvidenceType.TASK_DECISION
    assert ev_sched.data["task_id"] == "TSK-0001"
    assert ev_sched.data["mandatory"] is True
    assert ev_sched.data["status"] == "SCHEDULED"

    ev_unsched = await CopilotToolRegistry.get_task_decision(mock_session, "TSK-0007", scenario_id="SCN-DEMO-001")
    assert ev_unsched is not None
    assert ev_unsched.evidence_type == EvidenceType.TASK_DECISION
    assert ev_unsched.data["task_id"] == "TSK-0007"
    assert ev_unsched.data["status"] == "UNSCHEDULED"


@pytest.mark.asyncio
async def test_copilot_uncertainty_handling():
    """Verify unknown entities return explicit uncertainty without inventing facts (isolated unit test)."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_res_none = MagicMock()
    mock_res_none.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_res_none

    req = CopilotQueryRequest(prompt="Why was task TSK-9999 rejected?", scenario_id="SCN-DEMO-001")
    resp = await CopilotEngine.explain(mock_session, req)
    assert resp.evidence[0].evidence_type == EvidenceType.UNCERTAINTY
    assert "Uncertainty Notice" in resp.answer
    assert "TSK-9999" in resp.answer


@pytest.mark.asyncio
async def test_copilot_mutation_refusal_execution():
    """Verify end-to-end execution of refusal on write request (isolated unit test)."""
    mock_session = AsyncMock(spec=AsyncSession)
    req = CopilotQueryRequest(prompt="Please approve plan version PV-SCN-DEMO-001-V001")
    resp = await CopilotEngine.explain(mock_session, req)
    assert resp.provider_used == "GOVERNANCE_GUARDRAIL"
    assert resp.evidence[0].evidence_type == EvidenceType.REFUSAL
    assert "Strictly Read-Only" in resp.answer
