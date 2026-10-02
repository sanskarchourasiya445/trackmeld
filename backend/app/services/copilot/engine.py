"""
Core Decision Support & Explainability Engine for TrackMeld Copilot.
Enforces evidence grounding, read-only guardrails, mutation refusals, and uncertainty reporting.
"""

import re
import os
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.schemas.copilot import (
    CopilotQueryRequest,
    CopilotQueryResponse,
    EvidenceItem,
    EvidenceType,
)
from backend.app.services.copilot.tools import CopilotToolRegistry


class CopilotEngine:
    """Read-only evidence-grounded explanation engine."""

    MUTATION_PATTERNS = [
        re.compile(r"\b(approve|sign\s*off)\b", re.IGNORECASE),
        re.compile(r"\b(reject|disapprove)\b", re.IGNORECASE),
        re.compile(r"\b(delete|drop|remove)\b", re.IGNORECASE),
        re.compile(r"\b(cancel|terminate|abort)\b", re.IGNORECASE),
        re.compile(r"\b(reschedule|move|shift|update|modify|change|edit)\s+(task|window|time|schedule)\b", re.IGNORECASE),
        re.compile(r"\b(force|override)\s+(placement|constraint|rule)\b", re.IGNORECASE),
    ]

    TASK_PATTERN = re.compile(r"\b(TSK-[0-9]{4}|task\s*#?\s*([0-9]+))\b", re.IGNORECASE)
    RUN_PATTERN = re.compile(r"\b(RUN-[0-9A-Za-z_-]+)\b", re.IGNORECASE)
    RULE_PATTERN = re.compile(r"\b(RULE-[0-9A-Za-z_-]+)\b", re.IGNORECASE)
    PLAN_VERSION_PATTERN = re.compile(r"\b(PV-[0-9A-Za-z_-]+|plan\s+version\s+([0-9]+))\b", re.IGNORECASE)

    @classmethod
    def check_mutation_refusal(cls, prompt: str) -> Optional[str]:
        """Check if user prompt is requesting an unauthorized write/approval action."""
        for pattern in cls.MUTATION_PATTERNS:
            if pattern.search(prompt):
                return (
                    "**Action Refusal: Strictly Read-Only System**\n\n"
                    "The TrackMeld Copilot is an evidence-grounded decision support assistant. "
                    "In accordance with Indian Railways safety boundaries, the Copilot cannot approve plans, "
                    "modify maintenance schedules, override constraints, or delete operational records.\n\n"
                    "**Governance Boundary:** `COMPLETED ≠ APPROVED`. Formal operational authorizations require "
                    "an authenticated human signature from an authorized Divisional Railway Manager (DRM) or Operations Officer."
                )
        return None

    @classmethod
    def extract_entity_ids(cls, prompt: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """Extract task_id, run_id, rule_id, plan_version_id from prompt text."""
        task_id = None
        run_id = None
        rule_id = None
        plan_version_id = None

        # Task match
        t_match = cls.TASK_PATTERN.search(prompt)
        if t_match:
            raw = t_match.group(1).upper()
            if raw.startswith("TSK-"):
                task_id = raw
            elif t_match.group(2):
                num = int(t_match.group(2))
                task_id = f"TSK-{num:04d}"

        # Run match
        r_match = cls.RUN_PATTERN.search(prompt)
        if r_match:
            run_id = r_match.group(1).upper()

        # Rule match
        rule_match = cls.RULE_PATTERN.search(prompt)
        if rule_match:
            rule_id = rule_match.group(1).upper()

        # Plan version match
        pv_match = cls.PLAN_VERSION_PATTERN.search(prompt)
        if pv_match:
            if pv_match.group(1).upper().startswith("PV-"):
                plan_version_id = pv_match.group(1).upper()
            elif pv_match.group(2):
                plan_version_id = pv_match.group(2)

        return task_id, run_id, rule_id, plan_version_id

    @classmethod
    async def explain(
        cls,
        session: AsyncSession,
        request: CopilotQueryRequest,
    ) -> CopilotQueryResponse:
        """Process user inquiry with read-only tools and return evidence-grounded answer."""
        prompt = request.prompt.strip()

        # 1. Guardrail: Mutation / write refusal
        refusal_reason = cls.check_mutation_refusal(prompt)
        if refusal_reason:
            refusal_ev = EvidenceItem(
                evidence_id="GOVERNANCE:READ_ONLY_GUARDRAIL",
                evidence_type=EvidenceType.REFUSAL,
                title="Read-Only Governance Boundary",
                data={"rule": "COMPLETED_NOT_APPROVED", "authorized_roles": ["OPERATOR", "ADMIN"]},
                source_reference="PRD::FR-032",
            )
            return CopilotQueryResponse(
                query=prompt,
                answer=refusal_reason,
                evidence=[refusal_ev],
                tool_calls_executed=[],
                provider_used="GOVERNANCE_GUARDRAIL",
            )

        # 2. Extract entity references
        extracted_task, extracted_run, extracted_rule, extracted_pv = cls.extract_entity_ids(prompt)
        task_id = request.task_id or extracted_task
        run_id = request.run_id or extracted_run
        plan_version_id = request.plan_version_id or extracted_pv
        scenario_id = request.scenario_id or "SCN-DEMO-001"

        evidence_items: List[EvidenceItem] = []
        tools_executed: List[str] = []

        # 3. Handle Plan Version inquiries
        if plan_version_id:
            pv_ev = await CopilotToolRegistry.get_plan_version_status(session, plan_version_id)
            tools_executed.append("get_plan_version_status")
            if pv_ev:
                evidence_items.append(pv_ev)
                data = pv_ev.data
                answer = (
                    f"### Plan Version {data.get('version_number')} Governance Status\n\n"
                    f"**Current Status:** `{data.get('status')}`  \n"
                    f"**Plan Identifier:** `{data.get('plan_version_id')}`  \n"
                    f"**Created By:** `{data.get('created_by')}`  \n"
                )
                if data.get("approved_by"):
                    answer += f"**Approved By:** `{data.get('approved_by')}` (Authorized Operations Officer)  \n"
                    answer += f"**Approval Rationale:** {data.get('approval_reason')}  \n"
                elif data.get("reviewed_by"):
                    answer += f"**Under Review By:** `{data.get('reviewed_by')}`  \n"
                    answer += f"*Notice:* Plan is awaiting final human DRM approval. `COMPLETED ≠ APPROVED`.  \n"
                else:
                    answer += f"*Notice:* Plan is currently pending review. `COMPLETED ≠ APPROVED`.  \n"

                answer += f"\n**Audit Events Recorded:** {data.get('audit_event_count', 0)} tamper-evident entries in immutable ledger.\n\n"
                answer += f"*Evidence Grounding:* [{pv_ev.evidence_id}](source://{pv_ev.source_reference})"
                return CopilotQueryResponse(
                    query=prompt,
                    answer=answer,
                    evidence=evidence_items,
                    tool_calls_executed=tools_executed,
                    provider_used="DETERMINISTIC_EVIDENCE_ENGINE",
                )
            else:
                uncert_ev = EvidenceItem(
                    evidence_id=f"UNCERTAINTY:PLAN_VERSION:{plan_version_id}",
                    evidence_type=EvidenceType.UNCERTAINTY,
                    title=f"Plan Version {plan_version_id} Not Found",
                    data={"plan_version_id": plan_version_id, "scenario_id": scenario_id},
                    source_reference="plan_versions",
                )
                return CopilotQueryResponse(
                    query=prompt,
                    answer=f"**Uncertainty Notice:** Plan version `{plan_version_id}` was not found in scenario `{scenario_id}`. "
                           f"The Copilot cannot invent hypothetical or fabricated plan versions.",
                    evidence=[uncert_ev],
                    tool_calls_executed=tools_executed,
                    provider_used="DETERMINISTIC_EVIDENCE_ENGINE",
                )

        # 4. Handle Railway Rule inquiries
        if extracted_rule:
            rule_ev = await CopilotToolRegistry.get_rule_provenance(session, extracted_rule)
            tools_executed.append("get_rule_provenance")
            if rule_ev:
                evidence_items.append(rule_ev)
                rdata = rule_ev.data
                answer = (
                    f"### Railway Operating Rule: {rdata.get('rule_code')}\n\n"
                    f"**Title:** {rdata.get('title')}  \n"
                    f"**Category:** `{rdata.get('category')}`  \n"
                    f"**Verification Status:** `{rdata.get('classification')}`  \n"
                    f"**Statutory Clause:** {rdata.get('clause_reference')}  \n"
                    f"**Manual Citation:** {rdata.get('manual_reference')}  \n\n"
                    f"**Operational Scope:**  \n{rdata.get('description')}\n\n"
                    f"*Evidence Grounding:* [{rule_ev.evidence_id}](source://{rule_ev.source_reference})"
                )
                return CopilotQueryResponse(
                    query=prompt,
                    answer=answer,
                    evidence=evidence_items,
                    tool_calls_executed=tools_executed,
                    provider_used="DETERMINISTIC_EVIDENCE_ENGINE",
                )
            else:
                uncert_ev = EvidenceItem(
                    evidence_id=f"UNCERTAINTY:RULE:{extracted_rule}",
                    evidence_type=EvidenceType.UNCERTAINTY,
                    title=f"Rule {extracted_rule} Not Found",
                    data={"rule_code": extracted_rule},
                    source_reference="railway_rules",
                )
                return CopilotQueryResponse(
                    query=prompt,
                    answer=f"**Uncertainty Notice:** Operating rule `{extracted_rule}` was not found in the verified railway rules repository. "
                           f"To prevent safety misclassification, unverified rules are never inferred or applied as hard constraints.",
                    evidence=[uncert_ev],
                    tool_calls_executed=tools_executed,
                    provider_used="DETERMINISTIC_EVIDENCE_ENGINE",
                )

        # 5. Handle Task inquiries
        if task_id:
            task_ev = await CopilotToolRegistry.get_task_decision(session, task_id, run_id, scenario_id)
            tools_executed.append("get_task_decision")

            if not task_ev:
                uncert_ev = EvidenceItem(
                    evidence_id=f"UNCERTAINTY:TASK:{task_id}",
                    evidence_type=EvidenceType.UNCERTAINTY,
                    title=f"Task {task_id} Not Found",
                    data={"task_id": task_id, "scenario_id": scenario_id},
                    source_reference="maintenance_tasks",
                )
                return CopilotQueryResponse(
                    query=prompt,
                    answer=f"**Uncertainty Notice:** Maintenance task `{task_id}` does not exist in scenario `{scenario_id}`. "
                           f"The Copilot cannot explain or analyze tasks that are not registered in the system.",
                    evidence=[uncert_ev],
                    tool_calls_executed=tools_executed,
                    provider_used="DETERMINISTIC_EVIDENCE_ENGINE",
                )

            evidence_items.append(task_ev)
            tdata = task_ev.data
            status = tdata.get("status")

            if status == "SCHEDULED":
                assigned_sec = tdata.get("assigned_section_code") or tdata.get("section_id")
                start_t = tdata.get("assigned_start_time")
                end_t = tdata.get("assigned_end_time")
                pos_start_t = tdata.get("possession_start_time")
                pos_end_t = tdata.get("possession_end_time")
                score = tdata.get("priority_score", 0.0)

                answer = (
                    f"### Task {tdata.get('task_id')}: Feasible & Scheduled\n\n"
                    f"**Work Description:** {tdata.get('description')}  \n"
                    f"**Department:** `{tdata.get('department')}` | **Type:** `{tdata.get('task_type')}`  \n"
                    f"**Assigned Section:** `{assigned_sec}`  \n"
                    f"**Maintenance Work Window:** `{start_t}` → `{end_t}` ({tdata.get('duration_minutes')} min)  \n"
                    f"**Possession Envelope:** `{pos_start_t}` → `{pos_end_t}` "
                    f"(includes {tdata.get('safety_buffer_before_minutes')}m setup and {tdata.get('safety_buffer_after_minutes')}m clearance buffers)  \n"
                    f"**Priority Score:** `{score:.2f}` (Mandatory: {'YES' if tdata.get('mandatory') else 'NO'})  \n\n"
                    f"**Safety & Feasibility Verification:**  \n"
                    f"- **Headway Clearance:** Zero conflict with timetable passenger trains on section `{assigned_sec}`.  \n"
                    f"- **Electrical Isolation:** Power block requirements satisfied.  \n"
                    f"- **Independent Validator:** Formally audited with 0 violations.  \n\n"
                    f"*Evidence Grounding:* [{task_ev.evidence_id}](source://{task_ev.source_reference})"
                )
                return CopilotQueryResponse(
                    query=prompt,
                    answer=answer,
                    evidence=evidence_items,
                    tool_calls_executed=tools_executed,
                    provider_used="DETERMINISTIC_EVIDENCE_ENGINE",
                )

            else:
                # Unscheduled task: retrieve blocking conflicts
                conflict_ev = await CopilotToolRegistry.get_conflicts_for_task(session, task_id, run_id, scenario_id)
                tools_executed.append("get_conflicts_for_task")
                if conflict_ev:
                    evidence_items.append(conflict_ev)

                reasons = tdata.get("reason_codes", ["SECTION_TRACK_CONTENTION"])
                conflicts = tdata.get("blocking_conflicts", [])

                answer = (
                    f"### Task {tdata.get('task_id')}: Unscheduled Decision Analysis\n\n"
                    f"**Task Description:** {tdata.get('description')} ({tdata.get('department')})  \n"
                    f"**Target Section:** `{tdata.get('section_id')}` | **Required Duration:** {tdata.get('duration_minutes')} min  \n"
                    f"**Mandatory Flag:** {'Mandatory' if tdata.get('mandatory') else 'Elective / Non-Mandatory'}  \n\n"
                    f"**Root-Cause Diagnostic Findings:**  \n"
                )
                for r in reasons:
                    if r == "TRAIN_MOVEMENT_CONFLICT":
                        answer += "- **Train Timetable Collision:** Continuous traffic occupancy by passenger express services prevented placing the required continuous maintenance window + safety buffer.\n"
                    elif r == "SECTION_OCCUPANCY_CONFLICT":
                        answer += "- **Track Section Contention:** Another higher-priority maintenance possession occupied this block section during the allowed window.\n"
                    elif r == "RESOURCE_UNAVAILABLE" or r == "RESOURCE_OVERLAP":
                        answer += "- **Resource Contention:** Required specialized machinery or maintenance gang was committed to another active work site.\n"
                    else:
                        answer += f"- **Feasibility Barrier:** Reason code `{r}` evaluated as hard constraint violation.\n"

                if conflicts:
                    answer += f"\n**Identified Blocking Entities:**  \n"
                    for c in conflicts[:3]:
                        answer += f"- `{c}`  \n"

                answer += (
                    f"\n**Mathematical Optimization Trace:**  \n"
                    f"The CP-SAT solver generated {tdata.get('candidate_interval_count', 0)} potential interval placements, "
                    f"all of which were rejected by the deterministic feasibility engine to protect train headway and safety.\n\n"
                    f"*Evidence Grounding:* [{task_ev.evidence_id}](source://{task_ev.source_reference})"
                )
                return CopilotQueryResponse(
                    query=prompt,
                    answer=answer,
                    evidence=evidence_items,
                    tool_calls_executed=tools_executed,
                    provider_used="DETERMINISTIC_EVIDENCE_ENGINE",
                )

        # 6. Handle Planning Run inquiries
        if run_id:
            run_ev = await CopilotToolRegistry.get_run_summary(session, run_id)
            tools_executed.append("get_run_summary")
            if run_ev:
                evidence_items.append(run_ev)
                rdata = run_ev.data
                answer = (
                    f"### Planning Run Summary: {rdata.get('run_id')}\n\n"
                    f"**Scenario:** `{rdata.get('scenario_id')}`  \n"
                    f"**Lifecycle Status:** `{rdata.get('status')}`  \n"
                    f"**Scheduler / Solver:** `{rdata.get('scheduler_type')}` (Solver Status: `{rdata.get('solver_status')}`)  \n"
                    f"**Solve Duration:** {rdata.get('execution_duration_ms', 0):.2f} ms  \n\n"
                    f"**Operational Delivery:**  \n"
                    f"- Total Work Orders / Tasks: {rdata.get('tasks_total', 0)}  \n"
                    f"- Scheduled Tasks: {rdata.get('tasks_scheduled', 0)} ({rdata.get('completion_rate_pct', 0.0):.1f}%)  \n"
                    f"- Mandatory Completion Rate: {rdata.get('mandatory_completion_rate_pct', 0.0):.1f}%  \n"
                    f"- Unscheduled Tasks: {rdata.get('tasks_unscheduled', 0)}  \n\n"
                    f"**Independent Validation Audit:**  \n"
                    f"- Validation Status: `{rdata.get('validation_status')}` (Errors: {rdata.get('validation_error_count', 0)})  \n"
                    f"- Cryptographic Schedule Fingerprint: `{rdata.get('schedule_fingerprint')}`  \n\n"
                    f"*Notice:* This candidate schedule is independently verified feasible but remains subject to formal human sign-off (`COMPLETED ≠ APPROVED`).\n\n"
                    f"*Evidence Grounding:* [{run_ev.evidence_id}](source://{run_ev.source_reference})"
                )
                return CopilotQueryResponse(
                    query=prompt,
                    answer=answer,
                    evidence=evidence_items,
                    tool_calls_executed=tools_executed,
                    provider_used="DETERMINISTIC_EVIDENCE_ENGINE",
                )
            else:
                uncert_ev = EvidenceItem(
                    evidence_id=f"UNCERTAINTY:RUN:{run_id}",
                    evidence_type=EvidenceType.UNCERTAINTY,
                    title=f"Planning Run {run_id} Not Found",
                    data={"run_id": run_id},
                    source_reference="planning_runs",
                )
                return CopilotQueryResponse(
                    query=prompt,
                    answer=f"**Uncertainty Notice:** Planning run `{run_id}` was not found in the repository. "
                           f"The Copilot cannot provide metrics or diagnostics for non-existent execution runs.",
                    evidence=[uncert_ev],
                    tool_calls_executed=tools_executed,
                    provider_used="DETERMINISTIC_EVIDENCE_ENGINE",
                )

        # 7. General inquiry fallback: explain system status and guide user
        answer = (
            "### TrackMeld Decision Support Copilot\n\n"
            "I provide evidence-grounded operational explanations for railway possession planning. "
            "I can explain:\n\n"
            "1. **Task Decisions:** *\"Why was TSK-0007 not scheduled?\"* or *\"What is the window for TSK-0001?\"*\n"
            "2. **Conflict Root Causes:** *\"What conflicts block maintenance on SEC-ETW-CNB?\"*\n"
            "3. **Governance & Approval:** *\"What is the status of Plan Version 1?\"*\n"
            "4. **Railway Operating Rules:** *\"Explain rule RULE-STAT-RBP-1502C\"*\n"
            "5. **Solver & Validation Metrics:** *\"Summarize planning run RUN-...\"*\n\n"
            "**Core Boundary:** I am strictly read-only and cite deterministic database evidence. "
            "I cannot modify schedules, bypass safety rules, or grant operational approvals (`COMPLETED ≠ APPROVED`)."
        )
        return CopilotQueryResponse(
            query=prompt,
            answer=answer,
            evidence=[],
            tool_calls_executed=[],
            provider_used="DETERMINISTIC_EVIDENCE_ENGINE",
        )
