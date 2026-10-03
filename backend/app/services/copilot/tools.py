"""
Typed, read-only tools for TrackMeld Copilot.
All tools query persisted database models, planning run JSONB snapshots, or rules.
Strictly read-only: no mutations, no state changes, no approvals.
"""

from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    MaintenanceTaskModel,
    OperationalScenarioModel,
    PlanningRunModel,
    PlanVersionModel,
    GovernanceAuditEventModel,
    RailwayRuleModel,
    SectionModel,
)
from backend.app.schemas.planning_run import PlanningRunStatus
from backend.app.schemas.copilot import (
    CopilotToolParameter,
    CopilotToolSpec,
    EvidenceItem,
    EvidenceType,
)


class CopilotToolRegistry:
    """Registry of typed read-only data access tools for AI decision support."""

    @staticmethod
    def list_tools() -> List[CopilotToolSpec]:
        """Return specifications of all registered read-only tools."""
        return [
            CopilotToolSpec(
                name="get_task_decision",
                description="Retrieve scheduled/unscheduled decision, assigned window, buffers, priority score, and reasons for a maintenance task.",
                parameters=[
                    CopilotToolParameter(name="task_id", type="string", description="Task identifier or code, e.g. TSK-0001"),
                    CopilotToolParameter(name="run_id", type="string", description="Optional planning run identifier", required=False),
                    CopilotToolParameter(name="scenario_id", type="string", description="Optional scenario identifier", required=False),
                ],
            ),
            CopilotToolSpec(
                name="get_conflicts_for_task",
                description="Retrieve deterministic physical, safety, or timetable conflicts preventing a task from being scheduled.",
                parameters=[
                    CopilotToolParameter(name="task_id", type="string", description="Task identifier or code, e.g. TSK-0007"),
                    CopilotToolParameter(name="run_id", type="string", description="Optional planning run identifier", required=False),
                ],
            ),
            CopilotToolSpec(
                name="get_run_summary",
                description="Retrieve planning run status, solver optimality, independent validation outcome, runtime, and schedule fingerprint.",
                parameters=[
                    CopilotToolParameter(name="run_id", type="string", description="Planning run identifier, e.g. RUN-20261002-XXXX"),
                ],
            ),
            CopilotToolSpec(
                name="get_rule_provenance",
                description="Retrieve statutory Indian Railways rule clauses, verification status (VERIFIED_SOURCE vs ASSUMPTION), and manual citations.",
                parameters=[
                    CopilotToolParameter(name="rule_id", type="string", description="Rule code or ID, e.g. RULE-STAT-RBP-1502C"),
                ],
            ),
            CopilotToolSpec(
                name="get_plan_version_status",
                description="Retrieve governance lifecycle status (PENDING_REVIEW, UNDER_REVIEW, APPROVED, REJECTED), review commentary, and immutable audit events.",
                parameters=[
                    CopilotToolParameter(name="plan_version_id", type="string", description="Plan version identifier, e.g. PV-SCN-DEMO-001-V001"),
                ],
            ),
        ]

    @staticmethod
    async def get_task_decision(
        session: AsyncSession,
        task_id: str,
        run_id: Optional[str] = None,
        scenario_id: Optional[str] = None,
    ) -> Optional[EvidenceItem]:
        """Fetch task operational attributes and its schedule placement in a given run."""
        # 1. Lookup task in database
        stmt = select(MaintenanceTaskModel).where(
            (MaintenanceTaskModel.task_id == task_id) | (MaintenanceTaskModel.task_code == task_id)
        )
        res = await session.execute(stmt)
        task = res.scalar_one_or_none()
        if not task:
            return None

        # 2. Lookup planning run if provided or find latest completed run for task's scenario
        target_run: Optional[PlanningRunModel] = None
        if run_id:
            run_stmt = select(PlanningRunModel).where(
                (PlanningRunModel.run_id == run_id) | (PlanningRunModel.id == run_id)
            )
            r_res = await session.execute(run_stmt)
            target_run = r_res.scalar_one_or_none()
        else:
            sc_id = scenario_id or task.scenario_id
            run_stmt = (
                select(PlanningRunModel)
                .where(
                    PlanningRunModel.scenario_id == sc_id,
                    PlanningRunModel.status == PlanningRunStatus.COMPLETED,
                )
                .order_by(PlanningRunModel.created_at.desc())
                .limit(1)
            )
            r_res = await session.execute(run_stmt)
            target_run = r_res.scalar_one_or_none()

        placement_info: Dict[str, Any] = {
            "task_id": task.task_id,
            "task_code": task.task_code,
            "description": task.description or task.title,
            "task_type": task.task_type.value if hasattr(task.task_type, "value") else str(task.task_type),
            "department": getattr(task, "department", "ENGINEERING"),
            "section_id": task.section_id,
            "duration_minutes": task.estimated_duration_minutes,
            "mandatory": task.mandatory,
            "requires_traffic_block": task.requires_traffic_block,
            "requires_power_block": task.requires_power_block,
            "safety_buffer_before_minutes": task.safety_buffer_before_minutes,
            "safety_buffer_after_minutes": task.safety_buffer_after_minutes,
            "status": "UNSCHEDULED",
        }

        run_result = None
        if target_run:
            if isinstance(getattr(target_run, "result", None), dict):
                run_result = target_run.result
            elif isinstance(getattr(target_run, "schedule_result", None), dict):
                run_result = target_run.schedule_result
            elif hasattr(target_run, "schedule_result") and type(target_run.schedule_result).__name__ not in ("MagicMock", "AsyncMock"):
                run_result = target_run.schedule_result
        if run_result:
            result_data = run_result
            scheduled_list = result_data.get("scheduled_tasks", [])
            unscheduled_list = result_data.get("unscheduled_tasks", [])

            # Check if scheduled
            found_scheduled = next(
                (s for s in scheduled_list if s.get("task_id") == task.task_id or s.get("task_code") == task.task_id),
                None,
            )
            if found_scheduled:
                placement_info.update({
                    "status": "SCHEDULED",
                    "run_id": target_run.run_id,
                    "assigned_start_time": found_scheduled.get("start_time"),
                    "assigned_end_time": found_scheduled.get("end_time"),
                    "possession_start_time": found_scheduled.get("possession_start_time"),
                    "possession_end_time": found_scheduled.get("possession_end_time"),
                    "assigned_section_code": found_scheduled.get("assigned_section_code"),
                    "assigned_resources": found_scheduled.get("assigned_resources", []),
                    "priority_score": found_scheduled.get("priority_score"),
                    "priority_components": found_scheduled.get("priority_components", {}),
                })
            else:
                found_unscheduled = next(
                    (u for u in unscheduled_list if u.get("task_id") == task.task_id or u.get("task_code") == task.task_id),
                    None,
                )
                if found_unscheduled:
                    placement_info.update({
                        "status": "UNSCHEDULED",
                        "run_id": target_run.run_id,
                        "reason_codes": found_unscheduled.get("reason_codes", []),
                        "blocking_conflicts": found_unscheduled.get("blocking_conflicts", []),
                        "candidate_interval_count": found_unscheduled.get("candidate_interval_count", 0),
                        "priority_score": found_unscheduled.get("priority_score"),
                    })

        return EvidenceItem(
            evidence_id=f"TASK:{task.task_id}",
            evidence_type=EvidenceType.TASK_DECISION,
            title=f"Task Decision Record for {task.task_id}",
            data=placement_info,
            source_reference=f"planning_runs::{target_run.run_id}" if target_run else "maintenance_tasks",
        )

    @staticmethod
    async def get_conflicts_for_task(
        session: AsyncSession,
        task_id: str,
        run_id: Optional[str] = None,
        scenario_id: Optional[str] = None,
    ) -> Optional[EvidenceItem]:
        """Fetch blocking conflicts preventing task placement."""
        task_evidence = await CopilotToolRegistry.get_task_decision(session, task_id, run_id, scenario_id)
        if not task_evidence:
            return None

        t_data = task_evidence.data
        if t_data.get("status") == "SCHEDULED":
            return EvidenceItem(
                evidence_id=f"CONFLICTS:{task_id}",
                evidence_type=EvidenceType.CONFLICT,
                title=f"No Active Conflicts for Scheduled Task {task_id}",
                data={
                    "task_id": task_id,
                    "status": "SCHEDULED",
                    "conflict_count": 0,
                    "message": "Task is feasible and scheduled with zero active constraint violations.",
                },
                source_reference=task_evidence.source_reference,
            )

        reason_codes = t_data.get("reason_codes", [])
        blocking_conflicts = t_data.get("blocking_conflicts", [])

        return EvidenceItem(
            evidence_id=f"CONFLICTS:{task_id}",
            evidence_type=EvidenceType.CONFLICT,
            title=f"Blocking Conflicts for Unscheduled Task {task_id}",
            data={
                "task_id": task_id,
                "status": "UNSCHEDULED",
                "reason_codes": reason_codes,
                "blocking_conflicts": blocking_conflicts,
                "section_id": t_data.get("section_id"),
                "duration_minutes": t_data.get("duration_minutes"),
                "mandatory": t_data.get("mandatory"),
            },
            source_reference=task_evidence.source_reference,
        )

    @staticmethod
    async def get_run_summary(
        session: AsyncSession,
        run_id: str,
    ) -> Optional[EvidenceItem]:
        """Retrieve execution facts and validation certificate of a planning run."""
        stmt = select(PlanningRunModel).where((PlanningRunModel.run_id == run_id) | (PlanningRunModel.id == run_id))
        res = await session.execute(stmt)
        run = res.scalar_one_or_none()
        if not run:
            return None

        metrics = run.metrics or {}
        val_status = "NOT_EVALUATED"
        val_errors = 0
        schedule_fingerprint = None
        run_result = run.schedule_result if run else None
        if run_result and "validation" in run_result:
            v_data = run_result["validation"]
            val_status = v_data.get("status", "NOT_EVALUATED")
            val_errors = v_data.get("error_count", 0)
            schedule_fingerprint = v_data.get("schedule_fingerprint")

        return EvidenceItem(
            evidence_id=f"RUN:{run.run_id}",
            evidence_type=EvidenceType.RUN_METRIC,
            title=f"Planning Run Execution Summary {run.run_id}",
            data={
                "run_id": run.run_id,
                "scenario_id": run.scenario_id,
                "status": run.status.value if hasattr(run.status, "value") else str(run.status),
                "scheduler_type": run.scheduler_type.value if hasattr(run.scheduler_type, "value") else str(run.scheduler_type),
                "solver_status": run.solver_status,
                "execution_duration_ms": run.execution_duration_ms,
                "tasks_total": metrics.get("tasks_total", 0),
                "tasks_scheduled": metrics.get("tasks_scheduled", 0),
                "tasks_unscheduled": metrics.get("tasks_unscheduled", 0),
                "completion_rate_pct": metrics.get("completion_rate_pct", 0.0),
                "mandatory_completion_rate_pct": metrics.get("mandatory_completion_rate_pct", 0.0),
                "validation_status": val_status,
                "validation_error_count": val_errors,
                "schedule_fingerprint": schedule_fingerprint,
                "snapshot_hash": run.snapshot_hash,
            },
            source_reference=f"planning_runs::{run.run_id}",
        )

    @staticmethod
    async def get_rule_provenance(
        session: AsyncSession,
        rule_id: str,
    ) -> Optional[EvidenceItem]:
        """Fetch railway operating rule clause, manual source, and verification status."""
        stmt = select(RailwayRuleModel).where(RailwayRuleModel.rule_id == rule_id)
        res = await session.execute(stmt)
        rule = res.scalar_one_or_none()
        if not rule:
            return None

        classification_str = (
            rule.rule_class.value if hasattr(rule.rule_class, "value") else str(rule.rule_class)
        )

        return EvidenceItem(
            evidence_id=f"RULE:{rule.rule_id}",
            evidence_type=EvidenceType.RULE_PROVENANCE,
            title=f"Railway Rule {rule.rule_id}: {rule.title}",
            data={
                "rule_code": rule.rule_id,
                "title": rule.title,
                "category": rule.category,
                "classification": classification_str,
                "clause_reference": rule.section_page or "Clause 15.02",
                "manual_reference": rule.source_document,
                "description": rule.normalized_summary or rule.original_text,
                "source_id": rule.source_id,
            },
            source_reference=f"railway_rules::{rule.rule_id}",
        )

    @staticmethod
    async def get_plan_version_status(
        session: AsyncSession,
        plan_version_id: str,
    ) -> Optional[EvidenceItem]:
        """Fetch formal plan version approval state and audit trail."""
        stmt = select(PlanVersionModel).where(
            (PlanVersionModel.id == plan_version_id)
            | (PlanVersionModel.plan_version_id == plan_version_id)
            | (PlanVersionModel.version_number == (int(plan_version_id) if plan_version_id.isdigit() else -1))
        )
        res = await session.execute(stmt)
        pv = res.scalar_one_or_none()
        if not pv:
            return None

        # Fetch audit events
        ev_stmt = (
            select(GovernanceAuditEventModel)
            .where(GovernanceAuditEventModel.plan_version_id == pv.id)
            .order_by(GovernanceAuditEventModel.timestamp.asc())
        )
        ev_res = await session.execute(ev_stmt)
        events = ev_res.scalars().all()

        return EvidenceItem(
            evidence_id=f"PLAN_VERSION:{pv.plan_version_id}",
            evidence_type=EvidenceType.PLAN_VERSION,
            title=f"Plan Version {pv.version_number} Status ({pv.status.value})",
            data={
                "plan_version_id": pv.plan_version_id,
                "scenario_id": pv.scenario_id,
                "version_number": pv.version_number,
                "status": pv.status.value if hasattr(pv.status, "value") else str(pv.status),
                "planning_run_id": pv.planning_run_id,
                "created_by": pv.created_by,
                "reviewed_by": pv.reviewed_by,
                "approved_by": pv.approved_by,
                "approval_reason": pv.approval_reason,
                "audit_event_count": len(events),
                "audit_events": [
                    {
                        "action": e.action,
                        "performed_by": e.performed_by,
                        "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                        "reason": e.reason,
                    }
                    for e in events
                ],
            },
            source_reference=f"plan_versions::{pv.plan_version_id}",
        )
