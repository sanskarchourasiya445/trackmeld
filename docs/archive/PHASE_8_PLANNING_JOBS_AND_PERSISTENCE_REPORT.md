# TrackMeld Phase 8 — Planning Jobs, Persistence & Background Execution Report

**Status:** COMPLETE  
**Executed:** October 2, 2026  
**Target Context:** Smart India Hackathon 2026 / Ministry of Railways / CRIS  
**Core Architectural Principle:**  
`Rules classify → Optimization schedules → Independent Validator verifies → Diagnostics explain → Human reviews → Human approves.`

---

## 1. Executive Summary & Purpose

In railway maintenance planning and decision-support systems, running complex combinatorial solvers (such as Google OR-Tools CP-SAT or multi-pass heuristic baseline schedulers) inside synchronous HTTP request-response cycles violates production resiliency and scalability principles. Heavy mathematical optimization blocks web worker threads, risks HTTP connection timeouts, and leaves no auditable, persistent job lifecycle.

**Phase 8 introduces TrackMeld's persistent asynchronous job orchestration, reproducibility ledger, and background execution architecture**:
- **Asynchronous Decoupling:** Long-running solver operations are completely removed from the FastAPI request cycle. Submitting a planning run requisition creates a database-backed job in `PENDING` status and returns `HTTP 201 Created` immediately with a queue token URL (`/api/v1/planning-runs/{run_id}`).
- **Native PostgreSQL Queue (No Unneeded Brokers):** In adherence to dependency discipline, the job worker utilizes PostgreSQL row-level locking (`SELECT ... FOR UPDATE SKIP LOCKED`) directly on the `planning_runs` table, providing atomic claiming, multi-worker race safety, and crash-resilient queue semantics without requiring Redis, Celery, or RabbitMQ.
- **Reproducibility & Provenance Ledger:** Every planning run immutably records a 64-character SHA-256 snapshot hash, configuration snapshot, random seed, solver name, solver version, and dataset version. Re-executing with identical parameters guarantees mathematically identical outcomes.
- **Audited State Machine:** Strict transitions (`PENDING` → `RUNNING` → `VALIDATING` → `COMPLETED` / `FAILED` / `CANCELLED` / `TIMED_OUT`) are enforced in code and database constraints.
- **Zero-Bypass Independent Validation:** Background workers execute Phase 7's `IndependentScheduleValidator` and attach certified cryptographic fingerprints before completing. Invalid schedules are captured with `is_approvable = False`.
- **Non-Negotiable Product Boundary:** `COMPLETED != APPROVED`. Job completion merely indicates that the computation, validation, and diagnostics pipeline finished. Human approval remains an independent future governance action.

---

## 2. Architectural Boundary & Workflow

```
   HTTP Client (FastAPI)                     PostgreSQL DB                    Background Worker
  ───────────────────────                   ───────────────                  ───────────────────
            │                                      │                                  │
  POST /api/v1/planning-runs                       │                                  │
  ───────────────────────────► Insert PENDING Run  │                                  │
  ◄────────────────────────── (status=PENDING)     │                                  │
    HTTP 201 Created                               │                                  │
    (run_id, status_url)                           │                                  │
                                                   │◄───── Claim Pending Run ─────────┤
                                                   │       (FOR UPDATE SKIP LOCKED)   │
                                                   │────── Returns Run / Sets RUNNING ┤
                                                   │                                  │
                                                   │                       Load PlanningSnapshot
                                                   │                       Compute Snapshot Hash
                                                   │                                  │
                                                   │                       Run Solver in Thread Pool
                                                   │                       (CP-SAT / Baseline)
                                                   │                                  │
                                                   │                       Run Phase 7 Validator
                                                   │                       (Certify VALID / INVALID)
                                                   │                                  │
                                                   │                       Run Diagnostics
                                                   │                       (If unplaced tasks)
                                                   │                                  │
                                                   │◄───── Persist ScheduleResult ────┤
                                                   │       Mark COMPLETED             │
                                                   │       (Set is_approvable)        │
            │                                      │                                  │
  GET /api/v1/planning-runs/{id}/result            │                                  │
  ────────────────────────────────────────────────►│                                  │
  ◄────────────────────────────────────────────────│                                  │
    HTTP 200 OK (ScheduleResult + Validation)
```

---

## 3. Database Schema & Migration Details

### Migration: `8a4f21d9b301_003_planning_runs_schema.py`
Created table `planning_runs` with composite indexes and PostgreSQL JSONB structures:

| Column | Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| `id` | Integer (PK) | No | Auto-increment primary key |
| `run_id` | String(64) | No | Unique business identifier (`RUN-YYYYMMDD-HEX`) |
| `scenario_id` | String(64) | No | FK to `operational_scenarios.scenario_id` |
| `status` | String(32) | No | High-level status (`PENDING`, `RUNNING`, `VALIDATING`, etc.) |
| `stage` | String(32) | No | Granular progression stage |
| `run_type` | String(32) | No | Execution category (`SINGLE`, `BATCH`, `BENCHMARK`) |
| `scheduler_type` | String(32) | No | Algorithm strategy (`CP_SAT`, `FCFS`, `PRIORITY_GREEDY`) |
| `scheduler_version`| String(32) | No | Engine semantic version |
| `planning_start` | DateTime(tz) | Yes | Planning horizon start |
| `planning_end` | DateTime(tz) | Yes | Planning horizon end |
| `snapshot_id` | String(64) | Yes | Snapshot business identifier |
| `snapshot_hash` | String(64) | Yes | 64-char SHA-256 fingerprint over all input data |
| `input_hash` | String(64) | Yes | 64-char SHA-256 over snapshot, config, and seed |
| `configuration_snapshot`| JSONB | No | Full configuration parameters |
| `priority_configuration`| JSONB | Yes | Priority weights and components |
| `optimization_configuration`| JSONB| Yes | Solver time limit, search workers, seed |
| `random_seed` | Integer | No | Randomization seed for reproducibility |
| `solver_name` | String(64) | No | Solver implementation identity |
| `solver_version` | String(32) | No | Solver library version |
| `dataset_version` | String(32) | No | Reference operational dataset version |
| `started_at` | DateTime(tz) | Yes | Execution start timestamp |
| `validation_started_at`| DateTime(tz)| Yes | Independent validation start timestamp |
| `completed_at` | DateTime(tz) | Yes | Final completion timestamp |
| `failed_at` | DateTime(tz) | Yes | Failure timestamp |
| `heartbeat_at` | DateTime(tz) | Yes | Worker liveness heartbeat timestamp |
| `execution_duration_ms`| Float | Yes | Wall-clock execution time in milliseconds |
| `attempt_count` | Integer | No | Number of execution attempts |
| `worker_id` | String(64) | Yes | Worker identity holding the run lease |
| `created_by` | String(64) | No | User or system identity initiating the run |
| `idempotency_key` | String(128)| Yes | Client idempotency token (Unique Index) |
| `error_code` | String(64) | Yes | Structured error code |
| `error_message` | Text | Yes | Human-readable error description |
| `error_details` | JSONB | Yes | Detailed error context / stack metadata |
| `result_summary` | JSONB | Yes | Top-level summary metrics for fast dashboard queries |
| `schedule_result` | JSONB | Yes | Complete serialized `ScheduleResult` domain model |
| `validation_status`| String(32) | Yes | Phase 7 status (`VALID`, `INVALID`, `UNCHECKED`) |
| `validation_fingerprint`| String(64)| Yes| Cryptographic schedule identity hash |
| `is_approvable` | Boolean | No | Approval eligibility gate |
| `validation_findings_summary`| JSONB| Yes | Summary counts and top finding codes |
| `diagnostics_summary`| JSONB | Yes | Root causes and relaxation analyses for unplaced tasks |
| `created_at` | DateTime(tz) | No | Record creation timestamp |
| `updated_at` | DateTime(tz) | No | Last update timestamp |

---

## 4. State Machine & Transition Rules

```
                      ┌───────────────┐
                      │    PENDING    │
                      └───────┬───────┘
                              │
             ┌────────────────┼────────────────┐
             │                │                │
             ▼                ▼                ▼
     ┌───────────────┐┌───────────────┐┌───────────────┐
     │   CANCELLED   ││    FAILED     ││    RUNNING    │
     └───────────────┘└───────────────┘└───────┬───────┘
                                               │
                               ┌───────────────┼───────────────┐
                               │               │               │
                               ▼               ▼               ▼
                       ┌───────────────┐┌───────────────┐┌───────────────┐
                       │  CANCEL_REQ   ││  VALIDATING   ││   TIMED_OUT   │
                       └───────┬───────┘└───────┬───────┘└───────────────┘
                               │                │
                               ▼                ▼
                       ┌───────────────┐┌───────────────┐
                       │   CANCELLED   ││   COMPLETED   │
                       └───────────────┘└───────────────┘
```

- **Enforcement:** Enforced in `PlanningRunRepository.validate_transition()` with `IllegalStateTransitionError`.
- **Immutability:** Once a run reaches `COMPLETED` or `FAILED`, all transitions are strictly disallowed. Completed schedules are permanently immutable audit artifacts.

---

## 5. Reproducibility & Provenance Hashing

1. **Snapshot Hash (`compute_snapshot_hash`):**
   - Hashes `scenario_id`, `planning_start`, `planning_end`, and a canonical sorted array of all tasks `(task_id, window_start, window_end, duration, section_id)`.
   - Incorporates count of train passes, resources, and dependencies.
   - Result: 64-character SHA-256 hexadecimal string.
2. **Input Hash (`compute_input_hash`):**
   - Hashes `snapshot_hash` + canonical key-sorted JSON of configuration snapshot + randomization seed.
   - Changing seed, time limit, or algorithm changes the hash; re-running with identical inputs produces the identical input hash.

---

## 6. REST API Specification

Mounted at `/api/v1/planning-runs`:

1. **`POST /api/v1/planning-runs`**
   - Body: `CreatePlanningRunRequest` (scenario_id, scheduler_type, time_limit_seconds, num_search_workers, random_seed, validate_after_solve, priority_config, optimization_config, idempotency_key).
   - Returns: `HTTP 201 Created` with `CreatePlanningRunResponse` (run_id, scenario_id, status=PENDING, stage=QUEUED, status_url).
2. **`GET /api/v1/planning-runs/{run_id}`**
   - Returns: `PlanningRunDetailResponse` with status, progress stage, execution duration, result summary, validation status, and `is_approvable`.
3. **`GET /api/v1/planning-runs/{run_id}/result`**
   - Returns: `ScheduleResult` with all task placements, priority scores, and attached Phase 7 independent validation findings.
   - If not yet completed: Returns `HTTP 409 Conflict` with `PLANNING_RUN_NOT_COMPLETED`.
4. **`GET /api/v1/planning-runs`**
   - Query params: `scenario_id`, `status`, `scheduler_type`, `limit`, `offset`.
   - Returns: `List[PlanningRunSummary]` with `X-Total-Count` header.
5. **`POST /api/v1/planning-runs/{run_id}/cancel`**
   - Cancels pending run or marks running job as cancel-requested.

---

## 7. Verification Evidence & Quality Gates

### A. Phase 8 Unit Test Suite (`tests/unit/test_phase8_planning_run.py`)
- `test_planning_run_state_machine_legal_transitions`: Verified all legal transitions.
- `test_planning_run_state_machine_illegal_transitions`: Verified that illegal jumps are rejected.
- `test_snapshot_hash_determinism_and_sensitivity`: Verified SHA-256 determinism and payload sensitivity.
- `test_input_hash_determinism`: Verified canonical dictionary normalization in input hashing.
- `test_create_planning_run_request_validation`: Verified schema field constraints and bounds.
- `test_planning_run_progress_reporting`: Verified telemetry progress structures.
- `test_completed_run_immutability`: Verified terminal state protection.
- `test_single_run_type_default`: Verified default run type contract.
- **Result:** **8 passed in 0.09s**.

### B. Phase 8 Integration Test Suite (`tests/integration/test_phase8_planning_jobs_api.py`)
- `test_create_planning_run_api_queued_immediately`: HTTP 201 immediate queue response.
- `test_get_planning_run_details_and_not_found`: Detail retrieval and 404 behavior.
- `test_client_idempotency_key`: Deduplication of duplicate submissions.
- `test_worker_execution_e2e`: Full background worker claim, CP-SAT solve, Phase 7 validate, and persistence.
- `test_result_endpoint_not_completed_returns_409`: Conflict protection for incomplete runs.
- `test_list_planning_runs_filtering_and_pagination`: Query filtering and `X-Total-Count`.
- `test_cancellation_flow`: Cancellation transition.
- `test_worker_atomic_job_claiming_concurrency`: Concurrent worker race safety (`FOR UPDATE SKIP LOCKED`).
- **Result:** **8 passed in 2.60s**.

### C. Full Project Regression Test Suite
- Executed `python -m pytest` across all test suites (Phases 0 through 8).
- **Result:** **173 passed, 0 failed in 13.35s**.

### D. Deterministic Phase 8 Milestone Invariant Validation Script (`scripts/validate_phase8_planning_jobs.py`)
- 22 comprehensive automated invariant checks:
  1. `planning_runs` PostgreSQL schema and indexes.
  2. Pydantic request/response model validation.
  3. Job creation in `PENDING` / `QUEUED` state.
  4. Idempotency key deduplication.
  5. Atomic job claim with `FOR UPDATE SKIP LOCKED`.
  6. Multi-worker concurrency safety.
  7. PlanningSnapshot SHA-256 hashing determinism.
  8. Input configuration SHA-256 hashing.
  9. End-to-end background worker execution pipeline.
  10. Phase 7 Independent Validator certified fingerprint attachment.
  11. Unscheduled task diagnostics attachment.
  12. ScheduleResult persistence in PostgreSQL JSONB.
  13. Non-negotiable product boundary: `COMPLETED != APPROVED`.
  14. Legal state machine transitions.
  15. Illegal state machine transitions rejected.
  16. Immutability of completed runs.
  17. Cooperative job cancellation flow.
  18. Worker heartbeat tracking.
  19. Stale run timeout detection.
  20. Structured error capture.
  21. Nonexistent run 404 behavior.
  22. Multi-parameter pagination and filtering.
- **Result:** **ALL 22/22 CHECKS PASSED**.

---

## 8. Compliance with Architectural Principles

| Mandate | Verification | Status |
| :--- | :--- | :--- |
| **Rules classify** | Maintained from Phase 0/1/4. CompatibilityEngine and Validator enforce domain rules. | Verified |
| **Optimization schedules**| CP-SAT and baselines schedule placements in background threads (`asyncio.to_thread`). | Verified |
| **Independent Validator verifies**| Phase 7 Independent Validator runs after every solver run before marking completed. | Verified |
| **Diagnostics explain**| UnscheduledTaskDiagnosticsService runs for all unplaced tasks with root-cause relaxation analyses. | Verified |
| **Humans approve** | `COMPLETED` never implies `APPROVED`. `is_approvable` indicates eligibility only. | Verified |
| **AI explains** | Copilot remains read-only decision support for future phases; never given scheduling authority. | Verified |
