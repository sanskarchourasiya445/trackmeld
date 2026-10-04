# TrackMeld Phase 7 — Independent Validation and Diagnostics Report

**Status:** COMPLETE  
**Executed:** October 2, 2026  
**Target Context:** Smart India Hackathon 2026 / Ministry of Railways / CRIS  
**Core Architectural Principle:**  
`Rules classify → Optimization schedules → Independent Validator verifies → Humans approve → AI explains.`

---

## 1. Executive Summary & Purpose

In railway possession planning, **mathematical solver optimality does NOT imply operational or safety validity**. A solver output may claim optimality under its internal objective formulation while failing to model an operational subtlety, suffering numerical edge-case defects, or having its input corrupted.

Phase 7 introduces TrackMeld's **Independent Schedule Validator and Diagnostics Engine**:
- **Strict Separation of Concerns:** The validator is a completely independent post-solve safety gate. It does not call the Phase 4 `CompatibilityEngine` to verify placements; it evaluates the schedules from first principles.
- **Read-Only Invariant:** The validator never repairs, mutates, or adjusts a schedule. It audits the schedule strictly as presented.
- **Deterministic Approval Gating:** An invalid schedule or a solver returning `UNKNOWN` or `INFEASIBLE` is strictly blocked from human approval (`is_approvable = False`).
- **Root-Cause Diagnostics:** Unplaced tasks undergo deep diagnostic evaluation to pinpoint conflicting trains, occupied sections, unavailable resources, or temporal limits, coupled with controlled, hypothetical relaxation analyses.
- **Zero Hallucination / Strict Safety Boundary:** All relaxation scenarios are explicitly marked `hypothetical=True` and `approvable=False`.

---

## 2. Architectural Boundary & Design Principles

```
  ┌─────────────────────────┐
  │  Phase 1/2 Data Layer   │
  │    (PostgreSQL / DB)    │
  └───────────┬─────────────┘
              │ Immutable Snapshot
              ▼
  ┌─────────────────────────┐       ┌─────────────────────────┐
  │   Phase 4 Feasibility   │       │  Phase 5/6 Schedulers   │
  │   CompatibilityEngine   │◄─────┤ (FCFS, Greedy, CP-SAT)  │
  └─────────────────────────┘       └───────────┬─────────────┘
                                                │ Raw ScheduleResult
                                                ▼
                                    ┌─────────────────────────┐
                                    │    PHASE 7 GATEWAY      │
                                    │  Independent Validator  │
                                    └───────────┬─────────────┘
                                                │ Certified / Rejected
                                                ▼
                                    ┌─────────────────────────┐
                                    │     Approval Gate       │
                                    │  VALID -> Approvable    │
                                    │  INVALID -> Blocked     │
                                    └─────────────────────────┘
```

### Architectural Safeguards
1. **Never Self-Certify:** The solver never certifies its own results.
2. **Double-Checked Semantics:** Section occupancy, train passes, and resource availability are re-evaluated from the immutable `PlanningSnapshot`.
3. **Sweep-Line Concurrency:** Resource capacity tracking uses a discrete sweep-line event model `(time, delta)` where departure events are processed before arrival events at identical timestamps, preserving half-open interval boundaries $[start, end)$.
4. **Deterministic Fingerprint:** A SHA-256 schedule fingerprint is derived from canonically sorted tasks, intervals, sections, and resources, ensuring tamper detection.

---

## 3. Data Contracts & Domain Models

Located in `backend/app/services/validation/models.py`:

- **Enums:**
  - `ValidationStatus`: `VALID`, `INVALID`, `UNKNOWN`.
  - `ValidationSeverity`: `ERROR` (blocks approval), `WARNING` (informational / operational flag), `INFO` (telemetry).
  - `ValidationCategory`: `STRUCTURAL`, `HORIZON`, `WINDOW`, `DURATION`, `TEMPORAL`, `SECTION`, `MULTI_SECTION`, `TRAIN_MOVEMENT`, `RESOURCE`, `DEPENDENCY`, `MANDATORY`, `RULE`, `SOLVER_OUTPUT`, `INTERNAL`.
  - `DiagnosticStatus`: `DIAGNOSED`, `FEASIBLE_ALTERNATIVE_FOUND`, `UNRESOLVED`, `UNKNOWN`.
  - `RelaxationScenarioType`: `IGNORE_TRAIN_CONFLICTS`, `IGNORE_SECTION_OCCUPANCY`, `IGNORE_RESOURCE_AVAILABILITY`, `IGNORE_DEPENDENCIES`, `WIDEN_TASK_WINDOW`.

- **Key Models:**
  - `ValidationFinding`: Precise finding with `code`, `severity`, `category`, `message`, `task_id`, `section_id`, `resource_id`, `train_movement_id`, `evidence`, `expected`, `actual`, and deterministic `sort_key()`.
  - `ScheduleValidationResult`: Authoritative outcome contract containing `status`, `valid`, `is_approvable`, `findings`, `schedule_identity` (64-char SHA-256), `checks_executed`, and audit counts.
  - `RelaxationFinding`: Diagnostic analysis of constraint relaxations with mandatory invariant `hypothetical=True` and `approvable=False`.
  - `UnscheduledTaskDiagnostic`: Root-cause explanation with primary bottleneck and relaxation scenario evaluations.
  - `DiagnosticsReport`: Comprehensive report of all unplaced tasks across a planning horizon.

---

## 4. Independent Verification Engine

Implemented in `backend/app/services/validation/checks.py` and `validator.py`:

| Check ID | Verification Domain | Description |
|---|---|---|
| `STRUCTURAL` | Schedule Structure | Validates task IDs, non-null intervals, duration positivity, absence of duplicate tasks. |
| `HORIZON` | Planning Horizon | Ensures all work and possession intervals fall completely within $[T_{start}, T_{end})$. |
| `TASK_WINDOW` | Allowed Work Windows | Verifies that scheduled work $[start, end)$ is strictly enclosed within $[window\_start, window\_end)$. |
| `DURATION_AND_BUFFERS` | Durations & Envelopes | Validates scheduled duration matches task duration; ensures possession envelope reflects safety buffers. |
| `SECTION_OCCUPANCY` | Track Exclusivity | Verifies zero simultaneous track possession on any section using half-open collision checks. |
| `MULTI_SECTION` | Multi-Section Continuum | Validates that multi-section tasks occupy all spanned track sections without conflict. |
| `TRAIN_MOVEMENT` | Train Path Clearance | Proves zero overlap between track possession intervals and scheduled train passes. |
| `RESOURCES` | Capacity & Availability | Validates resource availability windows and executes sweep-line capacity audits against concurrency limits. |
| `DEPENDENCIES` | Precedence Constraints | Enforces Finish-to-Start relationships: predecessor scheduled, buffer delay satisfied. |
| `MANDATORY_TASKS` | Mandatory Accounting | Confirms mandatory tasks are either scheduled or explicitly accounted for with reason codes. |
| `DOMAIN_RULES` | Traction Power Blocks | Verifies power block requirements are only assigned to electrified block sections. |
| `SOLVER_OUTPUT` | Solver Status Sanity | Rejects schedules with solver status `UNKNOWN`, `INFEASIBLE`, or `INVALID_INPUT`. |

---

## 5. Approval Gate Enforcement

Implemented via `IndependentScheduleValidator.assert_schedule_approvable(snapshot, schedule)`:
- Returns `ScheduleValidationResult` if `is_approvable == True`.
- Raises `ScheduleApprovalBlockedError` if `is_approvable == False`.
- Prevents invalid schedules from ever being marked as approved or committed to operational databases.

---

## 6. Root-Cause Diagnostics & Relaxation Scenarios

Implemented in `backend/app/services/validation/diagnostics.py` and `relaxation.py`:
- For each unscheduled task, gathers concrete conflicting entities:
  - Conflicting scheduled tasks occupying the same block sections.
  - Conflicting corridor train passes.
  - Concurrently allocated maintenance resources.
  - Temporal boundary restrictions (tight windows).
- Evaluates 5 controlled hypothetical relaxation scenarios:
  1. `IGNORE_TRAIN_CONFLICTS`: Tests if placement is possible if train movements were halted.
  2. `IGNORE_SECTION_OCCUPANCY`: Tests if placement is possible if other maintenance tasks were cleared.
  3. `IGNORE_RESOURCE_AVAILABILITY`: Tests if placement is possible with unconstrained machinery/crews.
  4. `IGNORE_DEPENDENCIES`: Tests if placement is possible without predecessor waiting times.
  5. `WIDEN_TASK_WINDOW`: Tests if a +60-minute window extension would permit placement.
- **Safety Invariant:** All relaxation findings enforce `hypothetical = True` and `approvable = False`.

---

## 7. REST APIs

- `POST /api/v1/planning/validate`:
  - Request: `ValidateScheduleRequest(scenario_id, schedule)`
  - Response: `ScheduleValidationResult`
- `POST /api/v1/planning/diagnostics`:
  - Request: `ScheduleDiagnosticsRequest(scenario_id, schedule, target_task_id=None)`
  - Response: `DiagnosticsReport`
- `POST /api/v1/planning/optimize`:
  - Supports `validate_after_solve=True` parameter.
  - Automatically embeds independent validation results in the `ScheduleResult.validation` field.

---

## 8. Verification Results

### A. Unit Tests (`tests/unit/test_phase7_validator.py`)
All 22 unit tests passed with 100% success rate:
- `test_01_valid_schedule_passes`: Valid schedule certified `VALID` and `is_approvable == True`.
- `test_02_section_occupancy_conflict_rejected`: Overlapping tasks on same section rejected (`SECTION_OCCUPANCY_CONFLICT`).
- `test_03_adjacent_half_open_intervals_pass`: Exact boundary touches $[t_1, t_2)$ and $[t_2, t_3)$ pass without collision.
- `test_04_horizon_boundary_breach_rejected`: Task starting before or ending after horizon rejected (`HORIZON_BOUNDARY_BREACH`).
- `test_05_task_window_violation_rejected`: Task placed outside allowed work window rejected (`TASK_WINDOW_VIOLATION`).
- `test_06_duration_mismatch_rejected`: Tampered duration rejected (`DURATION_MISMATCH`).
- `test_07_possession_buffer_corrupted_rejected`: Possession interval failing to reflect safety buffers rejected.
- `test_08_train_movement_conflict_rejected`: Possession colliding with train pass rejected (`TRAIN_MOVEMENT_CONFLICT`).
- `test_09_resource_capacity_exceeded_rejected`: Concurrently scheduled tasks exceeding resource capacity rejected.
- `test_10_multi_section_task_conflict`: Multi-section task conflicting on secondary section rejected.
- `test_11_unknown_task_scheduled`: Non-existent task ID in schedule rejected (`UNKNOWN_TASK_SCHEDULED`).
- `test_12_dependency_predecessor_not_scheduled`: Successor scheduled without predecessor rejected.
- `test_13_dependency_timing_violation`: Successor starting before predecessor completion + buffer rejected.
- `test_14_mandatory_task_silently_dropped`: Mandatory task dropped from results rejected.
- `test_15_mandatory_task_unscheduled_warning`: Mandatory task accounted for produces operational warning.
- `test_16_solver_status_infeasible_rejected`: Solver status `INFEASIBLE` rejected as `INVALID`.
- `test_17_solver_status_unknown_rejected`: Solver status `UNKNOWN` rejected as `UNKNOWN`.
- `test_18_deterministic_schedule_identity`: Identical schedules yield exact same 64-char SHA-256 fingerprint.
- `test_19_approval_gate_blocks_invalid_schedule`: Approval gate raises `ScheduleApprovalBlockedError`.
- `test_20_approval_gate_permits_valid_schedule`: Approval gate succeeds for certified schedule.
- `test_21_relaxation_scenarios_strictly_hypothetical`: Validates all relaxation scenarios are hypothetical and not approvable.
- `test_22_independent_validator_does_not_call_compatibility_engine`: Monkeypatched `CompatibilityEngine` proves genuine architectural separation.

### B. Integration Tests (`tests/integration/test_phase7_validation_api.py`)
All 6 integration tests passed:
- `test_validate_schedule_api_valid`: 200 OK, `status == "VALID"`, `is_approvable == True`.
- `test_validate_schedule_api_invalid_tampered`: 200 OK, `status == "INVALID"`, `is_approvable == False`.
- `test_validate_schedule_api_scenario_not_found`: 404 Not Found on missing scenario.
- `test_diagnostics_api_success`: 200 OK, full diagnostic breakdown and relaxation analyses returned.
- `test_diagnostics_api_scenario_not_found`: 404 Not Found on missing scenario.
- `test_optimize_with_validation_flag`: 200 OK, optimization returns embedded independent validation.

### C. Deterministic Validation Script (`scripts/validate_phase7_validation.py`)
- Executed 23 invariant checks across live database, baseline scheduler, and CP-SAT optimizer: **23 passed, 0 failed**.
- Validation latency measured: **1.51 ms** (< 250 ms budget).

### D. Full Repository Regression Test
- **Pytest Suite:** **157 passed, 0 failed** in 14.09 seconds across 23 test files.
- **Milestone Validation Scripts:**
  - `validate_database.py`: 31 passed, 0 failed.
  - `validate_operational_data.py`: 30 passed, 0 failed.
  - `validate_phase4_compatibility.py`: 17 passed, 0 failed.
  - `validate_phase5_schedulers.py`: 30 passed, 0 failed.
  - `validate_phase6_cp_sat.py`: 22 passed, 0 failed.
  - `validate_phase7_validation.py`: 23 passed, 0 failed.
- **Total Automated Invariant Checks:** **310 passed, 0 failed**.

---

## 9. Limitations & Forward Roadmap

1. **In-Memory Post-Solve Validation:** Validation currently operates on in-memory `ScheduleResult` objects passed via API.
2. **Forward Integration with Phase 8 & 9:**
   - In **Phase 8 (Planning Jobs & Persistence)**, validation will run as an asynchronous pipeline step following solver job completion and persist validation results to PostgreSQL.
   - In **Phase 9 (Plan Versions, Review & Audit)**, the Approval Gate will enforce database-level state transitions (`CANDIDATE` → `APPROVED` only if `is_approvable == True`).
