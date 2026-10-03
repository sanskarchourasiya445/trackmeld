"""Independent Post-Solve Schedule Validator for TrackMeld.

CRITICAL ARCHITECTURAL BOUNDARY:
This validator is an independent quality and safety gate.
It does NOT modify, repair, or mutate the schedule.
Solver optimality does NOT imply operational validity.
"""

import time
import hashlib
import json
from typing import List, Dict, Any, Optional

from backend.app.domain.scheduling import ScheduleResult, SchedulerStatus
from backend.app.domain.planning_snapshot import PlanningSnapshot
from backend.app.services.validation.models import (
    ValidationStatus,
    ValidationSeverity,
    ScheduleValidationResult,
)
from backend.app.services.validation.checks import ScheduleCheckRunner
from backend.app.services.validation.exceptions import ScheduleApprovalBlockedError


class IndependentScheduleValidator:
    """Independent post-solve validation and approval safety gate."""

    VERSION = "1.0.0"

    @classmethod
    def compute_schedule_identity(cls, snapshot: PlanningSnapshot, schedule: ScheduleResult) -> str:
        """Compute deterministic SHA-256 fingerprint from canonical sorted schedule content.

        Canonical Schedule Identity Schema
        -----------------------------------
        The fingerprint covers fields that define WHAT was scheduled and HOW.
        Any change to these fields produces a different fingerprint.

        Identity-bearing fields (hashed):
          Per scheduled task (sorted by task_id):
            - task_id          (str)  — authoritative task identifier
            - start            (ISO)  — placement window start
            - end              (ISO)  — placement window end
            - pos_start        (ISO)  — possession interval start (with safety buffers)
            - pos_end          (ISO)  — possession interval end
            - sections         (list) — sorted affected section codes
            - resources        (list) — sorted assigned resource identifiers

          Per unscheduled task (sorted by task_id):
            - task_id          (str)  — task that could not be feasibly placed

          Scenario provenance:
            - snapshot_id      (str)  — immutable planning snapshot identifier
            - scenario_id      (str)  — scenario under which schedule was computed
            - scheduler_type   (str)  — algorithm that produced this schedule
            - solver_status    (str)  — terminal solver outcome (OPTIMAL/FEASIBLE/etc.)

        Explicitly NOT hashed (non-identity):
          - priority_score, priority_breakdown  — derived metrics, not placement decisions
          - sequence_order, scheduling_reason   — explanatory annotations
          - execution_time_ms, solver_diagnostics — performance telemetry
          - decision_trace, rule_evidence_ids   — audit evidence, not placement
          - crew_id, assigned_track             — these fields do not exist on the
                                                  ScheduledTaskResult domain model;
                                                  if added in future, include them here
                                                  with a VERIFIED_SOURCE provenance record.

        Classification: ASSUMPTION
        Provenance: Internal TrackMeld design — not derived from a published
        railway standard. Review scope if operational requirements change.
        """
        canonical_tasks = []
        for st in sorted(schedule.scheduled_tasks, key=lambda t: t.task_id):
            canonical_tasks.append({
                "task_id": st.task_id,
                "start": st.interval.start.isoformat() if st.interval else "",
                "end": st.interval.end.isoformat() if st.interval else "",
                "pos_start": st.possession_interval.start.isoformat() if st.possession_interval else "",
                "pos_end": st.possession_interval.end.isoformat() if st.possession_interval else "",
                "sections": sorted(st.affected_sections),
                "resources": sorted(st.assigned_resources),
            })

        # Sorted unscheduled task IDs are identity-bearing: a schedule that
        # leaves a different set of tasks unscheduled is a different schedule.
        unscheduled_ids = sorted(ut.task_id for ut in schedule.unscheduled_tasks)

        identity_payload = {
            "snapshot_id": snapshot.snapshot_id,
            "scenario_id": snapshot.scenario_id,
            "scheduler_type": schedule.scheduler_type.value if hasattr(schedule.scheduler_type, "value") else str(schedule.scheduler_type),
            "solver_status": schedule.status.value if hasattr(schedule.status, "value") else str(schedule.status),
            "scheduled_tasks": canonical_tasks,
            "unscheduled_task_ids": unscheduled_ids,
        }
        serialized = json.dumps(identity_payload, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @classmethod
    def validate(
        cls,
        snapshot: PlanningSnapshot,
        schedule: ScheduleResult,
    ) -> ScheduleValidationResult:
        """Independently audit all hard constraints, safety barriers, and invariants of a schedule."""
        start_time = time.perf_counter()

        runner = ScheduleCheckRunner(snapshot=snapshot, schedule=schedule)
        findings = runner.run_all_checks()

        error_count = sum(1 for f in findings if f.severity == ValidationSeverity.ERROR)
        warning_count = sum(1 for f in findings if f.severity == ValidationSeverity.WARNING)
        info_count = sum(1 for f in findings if f.severity == ValidationSeverity.INFO)

        # Status determination
        if schedule.status in [SchedulerStatus.UNKNOWN, SchedulerStatus.INVALID_INPUT]:
            status = ValidationStatus.UNKNOWN
            valid = False
            is_approvable = False
            gate_msg = f"Approval BLOCKED: Solver status is {schedule.status.value}."
        elif schedule.status == SchedulerStatus.INFEASIBLE:
            status = ValidationStatus.INVALID
            valid = False
            is_approvable = False
            gate_msg = "Approval BLOCKED: Solver proved scenario mathematically INFEASIBLE."
        elif error_count > 0:
            status = ValidationStatus.INVALID
            valid = False
            is_approvable = False
            gate_msg = f"Approval BLOCKED: Schedule contains {error_count} hard safety/constraint violations."
        else:
            status = ValidationStatus.VALID
            valid = True
            is_approvable = True
            gate_msg = "Approval ELIGIBLE: Schedule independently certified 100% valid under all modeled hard constraints."

        schedule_identity = cls.compute_schedule_identity(snapshot, schedule)
        runtime_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return ScheduleValidationResult(
            status=status,
            valid=valid,
            is_approvable=is_approvable,
            findings=findings,
            error_count=error_count,
            warning_count=warning_count,
            info_count=info_count,
            checked_task_count=runner.checked_task_count,
            checked_section_count=runner.checked_section_count,
            checked_resource_count=runner.checked_resource_count,
            checked_train_movement_count=runner.checked_train_movement_count,
            validator_version=cls.VERSION,
            input_snapshot_id=snapshot.snapshot_id,
            schedule_identity=schedule_identity,
            validation_runtime_ms=runtime_ms,
            checks_executed=runner.checks_executed,
            approval_gate_message=gate_msg,
        )

    @classmethod
    def assert_schedule_approvable(
        cls,
        snapshot: PlanningSnapshot,
        schedule: ScheduleResult,
    ) -> ScheduleValidationResult:
        """Enforce strict approval gate. Raises ScheduleApprovalBlockedError if schedule is not approvable."""
        result = cls.validate(snapshot, schedule)
        if not result.is_approvable:
            raise ScheduleApprovalBlockedError(
                message=result.approval_gate_message,
                status=result.status.value,
                error_count=result.error_count,
            )
        return result
