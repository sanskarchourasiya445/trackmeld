# Phase 20: Operational Realism & Production Hardening

## 1. Executive Summary

TrackMeld Phase 20 establishes the operational hardening, database performance foundations, asynchronous worker lifecycle resilience, and truthful operational presentation required for a realistic prototype decision-support system.

This phase hardens existing scheduling and verification pipelines without introducing out-of-scope operational control functions (such as live signalling, interlocking emulation, or autonomous dispatch). All core invariants—most critically that automated optimization and validation never constitute plan approval—have been strictly reinforced across the backend worker, relational database indexes, API schemas, synthetic data providers, and frontend interfaces.

---

## 2. Baseline Architecture & Core Invariants

TrackMeld operates under a strict separation of concerns across mathematical optimization, automated certification, and human governance:

```
[Rules Classify] ➔ [CP-SAT Optimizes] ➔ [Independent Validator Certifies] ➔ [Human Reviews] ➔ [Four-Eyes Approves]
```

### Inviolable Invariants
- **`COMPLETED != APPROVED`**: A planning run transitioning to `COMPLETED` merely indicates that the solver and validator have finished computation.
- **`OPTIMAL != APPROVED`**: Mathematical optimality according to an objective function does not imply operational acceptability.
- **`FEASIBLE != APPROVED`**: Meeting mathematical constraints is a prerequisite, not an approval.
- **`VALID != APPROVED`**: Passing all 12 independent safety and feasibility checks provides mathematical confidence but never authorizes track access.
- **`VALIDATION != APPROVAL`**: Automated verification is deterministic and algorithmic; approval requires human railway engineering responsibility.
- **`CREATOR != APPROVER`**: Enforced four-eyes governance requires that the actor creating a plan version cannot be the reviewer who approves it.
- **Read-Only AI Copilot**: The Copilot provides explanation and diagnostic inquiry only. It possesses zero mutation endpoints, zero write tools, and zero authority to trigger or approve plan transitions.
- **Decision-Support Boundary**: TrackMeld does not send electrical interlocking commands, set points, clear signals, or dispatch trains. It generates advisory possession plans for human review.

---

## 3. Database Migration 012 & Compound Index Strategy

### Schema Migration
Alembic migration `012_production_hardening` (`c3d4e5f6a7b8`, down revision: `b2c3d4e5f6a7`) was created and applied to the PostgreSQL schema. Both forward (`upgrade head`) and reverse (`downgrade -1`) migrations were verified clean and idempotent.

### Performance Index Design
To support high-throughput polling and concurrent queries during operational use, three targeted compound indexes were established:

1. **`ix_planning_runs_scenario_status_created`**:
   - Columns: `(scenario_id, status, created_at DESC)`
   - Purpose: Optimizes worker job claiming queries and API polling for scenario-specific planning runs by avoiding sequential table scans.
2. **`ix_tasks_track_window`**:
   - Columns: `(track_id, window_start, window_end)`
   - Purpose: Enables efficient spatial-temporal queries for maintenance task possession windows across specific physical tracks.
3. **`ix_movements_train_station`**:
   - Columns: `(train_id, station_id)`
   - Purpose: Speeds up timetable traversal lookups and station stop sequence resolution during schedule construction.

SQLAlchemy ORM models (`PlanningRunModel`, `MaintenanceTaskModel`, `TrainMovementModel`) were updated to reflect these compound indexes in their `__table_args__`.

---

## 4. Planning Worker Hardening & Lifecycle Diagnostics

The background asynchronous worker (`backend.app.services.planning_worker.PlanningRunWorker`) was hardened against unhandled exceptions, worker stalling, and state desynchronization:

- **Asynchronous Timeout Enforcement**: Every optimization invocation is wrapped in an `asyncio.wait_for` block configured with `PLANNING_JOB_TIMEOUT_SECONDS` (120 seconds).
- **Graceful Timeout Transitions**: If a solve exceeds the threshold, the worker traps `asyncio.TimeoutError`, marks the planning run as `TIMED_OUT`, sets error code `PLANNING_JOB_TIMED_OUT`, and releases resources without crashing.
- **Lifecycle Integrity**: Transitions from `PENDING` ➔ `SOLVING` ➔ `VALIDATING` ➔ `COMPLETED` (or `FAILED` / `TIMED_OUT` / `CANCELLED`) maintain atomic state consistency. Candidate plan creation is strictly blocked unless the planning run is in `COMPLETED` status.
- **Cooperative Cancellation**: Ongoing runs honor cooperative cancellation checks prior to solver invocation, prior to validator execution, and prior to final persistence.

---

## 5. Structured Observability & Telemetry

Every completed planning run persists structured telemetry within its `result_summary` JSON payload, facilitating operational monitoring, forensic audit, and benchmarking:

| Metric Field | Type | Description |
|---|---|---|
| `solver_mode` | string | Solver execution mode (`TRACK_AWARE_CONSERVATIVE` or `WHOLE_SECTION`) |
| `worker_id` | string | Identifier of the worker instance that claimed and executed the job |
| `solve_duration_ms` | float | Execution wall time of the CP-SAT solver in milliseconds |
| `validation_duration_ms` | float | Execution wall time of the Independent Validator in milliseconds |
| `unresolved_spatial_entities_count` | integer | Number of tasks or traversals requiring fallback to section-level safety |
| `track_aware_fallback_count` | integer | Count of conservative fallback activations |
| `mandatory_tasks_count` | integer | Total number of mandatory maintenance tasks submitted |
| `mandatory_tasks_scheduled` | integer | Mandatory tasks successfully placed in the schedule |
| `mandatory_tasks_unscheduled` | integer | Mandatory tasks unplaced due to conflicts or window constraints |

---

## 6. Solver Mode Support & Config Snapshot

Phase 20 exposes explicit solver mode configuration through the API and worker:

- **Supported Modes**:
  - `TRACK_AWARE_CONSERVATIVE` (Default): Uses physical track assignments and curated topology where available, falling back conservatively to whole-section locks when spatial data is incomplete.
  - `WHOLE_SECTION`: Strict whole-section reservation mode without track-level concurrency.
- **Configuration Snapshot**: The user-selected `solver_mode` is validated in `CreatePlanningRunRequest`, recorded in the immutable `config_snapshot` of the `PlanningRunModel`, passed through to `OptimizationConfig`, and logged in worker diagnostics.

---

## 7. Synthetic Data Integrity & Operational Boundaries

TrackMeld explicitly identifies synthetic data to prevent confusing simulated schedules with live railway operations:

- **Data Tagging**: All synthetic train services, task dependencies, and resource contention fixtures are generated with explicit metadata tags:
  - `source: "SYNTHETIC"`
  - `provenance: "SRC-TRACKMELD-SYNTHETIC-GEN"`
- **Provider Methods**: The `SyntheticDataProvider` supplies standard demonstration services (`get_train_services`, `get_task_dependencies`, `get_resource_contentions`) clearly designated as synthetic fixtures.
- **No Fabricated Authoritative Rules**: Safety rules, headway buffers, and braking curves remain tagged as `DEMO_ONLY` or `ASSUMPTION` per project governance standards.

---

## 8. Frontend Truthfulness Hardening

The web workstation UI was audited and updated to eliminate misleading visual cues:

1. **TopBar Truthfulness**:
   - Replaced ambiguous "Live Data" / green "LIVE" badges with explicit amber badges reading `SYNTHETIC` and `Synthetic Demo Dataset`.
   - Tooltip clearly states: *"Simulated demonstration dataset. Not connected to live signaling or real-time telemetry."*
2. **Workstation Engine Badges**:
   - Schedule Status: `CP-SAT (TRACK-AWARE)` / `CP-SAT (WHOLE-SECTION)`
   - Automated Verification: `VALID (Automated)` with subtext clarifying independent algorithmic certification.
   - Governance Status: `APPROVED (Human Operator)` or `NOT APPROVED (Pending Review)` with explicit tooltips declaring `OPTIMAL != APPROVED` and `VALID != APPROVED`.
3. **No Optimistic State Fabrications**:
   - Initial state explicitly warns: *"No schedule computed. Backend unavailable or optimization has not yet run. Planning data is unverified — no approval decision can be made."*
   - Network disconnections or backend solver failures render clear alerts without falling back to hidden mock data.

---

## 9. Security & Governance Invariants

- **Role-Based Access Control (RBAC)**: All sensitive governance and planning endpoints enforce granular role boundaries (`ADMIN`, `MAINTENANCE_PLANNER`, `OPERATOR`, `VIEWER`).
- **Four-Eyes Enforcement**: The user who initiates a planning run or creates a candidate `PlanVersion` (`created_by`) is strictly forbidden by backend database-level checks from approving that plan version.
- **Credential Hygiene**: Session tokens are isolated in `sessionStorage`; no privileged tokens are written to `localStorage` or rendered into client-side DOM attributes.
- **HTTP Security Headers**: API responses include `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, and strict Content Security Policies.

---

## 10. Test Strategy & Verification Results

Verification encompasses 462 automated tests across unit, integration, and end-to-end browser suites:

### 1. Backend Unit Tests
- **Suite**: `tests/unit/`
- **Result**: 304 passing (including 8 Phase 20 unit tests)
- **Focus**:
  - Compound database index definitions on ORM models
  - Planning worker timeout handling and `asyncio.wait_for` error trapping
  - Structured telemetry compilation and field accuracy
  - Solver mode configuration parsing and propagation
  - Synthetic data provider tagging and provenance

### 2. Backend Integration Tests
- **Suite**: `tests/integration/`
- **Result**: 144 passing (including 4 Phase 20 integration tests)
- **Focus**:
  - `POST /api/v1/planning-runs` solver mode propagation
  - Blocking plan version creation on non-completed runs (`HTTP 409 Conflict`)
  - End-to-end planning run lifecycle with worker execution and telemetry persistence
  - Four-eyes governance state machine transition rules

### 3. Frontend End-to-End Browser Tests (Playwright)
- **Suite**: `frontend/e2e/` (Chromium headless)
- **Result**: 14 passing out of 14 tests across 5 test specs:
  - `01-happy-path-governance.spec.ts`: Complete 12-step governance workflow with four-eyes approval
  - `02-auth-security.spec.ts`: Authentication, RBAC, and credential leak prevention
  - `03-negative-governance.spec.ts`: Creator self-approval prevention, rejection immutability, superseding versions, API failure resilience
  - `04-truthful-ui.spec.ts`: Uncomputed notices, backend failure handling, network error resilience, canonical governance status display
  - `05-train-occurrence-keys.spec.ts`: Multi-movement train occurrences and duplicate-key warning prevention

### 4. Code Quality & Linting
- **Frontend ESLint**: 0 errors
- **TypeScript Typecheck (`tsc --noEmit`)**: 0 errors
- **Frontend Production Build (`next build`)**: Clean compilation and SSG prerender

---

## 11. Limitations & Explicit Exclusions

To maintain safety and scope boundaries, TrackMeld Phase 20 explicitly excludes:
- **No Safety Integrity Level (SIL) Certification**: TrackMeld is an engineering prototype for decision-support and is NOT certified under CENELEC EN 50126 / EN 50128 / EN 50129 standards.
- **No Direct Interlocking / Signalling**: TrackMeld cannot lock points, set routes, clear aspects, or interface with Solid State Interlocking (SSI) / Computer Based Interlocking (CBI).
- **No Automated Dispatch**: Schedules produced by TrackMeld are advisory proposals requiring formal human authorization and dispatch coordination.

---

## 12. Operational Readiness Evaluation

| Dimension | Evaluation | Evidence |
|---|---|---|
| Optimization & Scheduling | Verified Prototype | Multi-track conservative CP-SAT optimization with deterministic fallback |
| Independent Verification | Verified Prototype | 12 hard feasibility checks verified before human review |
| Human Governance | Verified Prototype | Cryptographically hashed plan versions with 4-eyes approval |
| Database Scalability | Verified Prototype | Compound indexes on critical query paths, PostgreSQL 18 tested |
| Worker Concurrency | Verified Prototype | Isolated async worker with heartbeats, timeouts, and job locking |
| Truthfulness & UX | Verified Prototype | Explicit synthetic badging, clear audit trail, zero optimistic spoofing |

---

## 13. Recommendation for Next Steps

With Phase 20 operational realism and production hardening complete, the platform is prepared for:
1. Long-term performance profiling under larger synthetic networks (>1,000 tasks, >500 train movements).
2. Advanced conflict resolution visualization in the 3D railway canvas.
3. Demonstration scenarios for stakeholder review under realistic operational possession constraints.
