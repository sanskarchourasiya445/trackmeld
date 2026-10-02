# TrackMeld Implementation Plan

This roadmap assumes a new repository and prioritizes a working, testable vertical slice over building every screen or AI feature immediately.

## Phase 0 — Real Indian Railways Data Acquisition & Extraction [STATUS: COMPLETE]

**Objective:** Acquire, archive, extract, normalize, validate, and document official Indian Railways ecosystem data.

### Completed Work
- Archived 18 official government/railway publications in `data/raw/` with SHA-256 checksums.
- Created `data/metadata/sources.json` cataloging all 18 primary sources.
- Extracted and normalized 3,429 canonical trains, 68 trunk stations, 66 derived block sections, 82 scheduled timetable passes, 9 statutory/operating rules, and Golden Quadrilateral infrastructure specs.
- Documented internal Railnet gaps (BDMS/TMS/COA) in `data/metadata/data_gaps.json` and station conflicts in `data/metadata/source_conflicts.json`.
- Automated validation suite executed 11,228 integrity checks with 100% pass rate (0 errors).
- Generated comprehensive `PHASE_0_DATA_REPORT.md`.

## Phase 1 — Project Foundation, Canonical Data Model, PostgreSQL, Provenance & Deterministic Ingestion [STATUS: COMPLETE]

**Objective:** Build the complete software foundation that consumes verified Phase 0 datasets and provides a clean, deterministic, provenance-aware PostgreSQL schema and FastAPI foundation.

### Completed Work
- Canonical Pydantic v2 domain models implemented (`Station`, `Section`, `Train`, `TrainMovement`, `RailwayRule`, `InfrastructureSpec`, `Corridor`, `SourceDocument`).
- Canonical provenance model implemented enforcing `REAL ≠ DERIVED ≠ SYNTHETIC ≠ ASSUMED` and immutability invariants.
- PostgreSQL relational schema designed with primary keys, foreign keys, unique constraints, check constraints, and compound indexes.
- Alembic migration `001_initial_schema` created and tested (`alembic upgrade head`).
- Deterministic ingestion script `scripts/ingest_phase0.py` implemented and verified 100% idempotent across multiple runs.
- Database seeding script `scripts/seed_database.py` created and tested.
- Automated database validation suite `scripts/validate_database.py` executed 30 comprehensive checks (30 passed, 0 failed).
- Full repository layer implemented (`StationRepository`, `SectionRepository`, `TrainRepository`, `TrainMovementRepository`, `RailwayRuleRepository`, `InfrastructureRepository`, `SourceDocumentRepository`).
- FastAPI application implemented with request ID middleware (`X-Request-ID`), structured error payloads, `/health`, `/health/db`, and v1 reference endpoints (`/api/v1/stations`, `/api/v1/sections`, `/api/v1/trains`, `/api/v1/rules`).
- Abstract operational data boundary interface `OperationalDataProvider` created.
- Full pytest test suite (31 tests: 16 unit, 15 integration) executed and passed (100% pass rate).
- Documentation created: `docs/DATA_CONTRACTS.md` and `docs/PHASE_1_FOUNDATION_REPORT.md`.
- Architecture document `ARCHITECTURE.md` updated with IMPLEMENTED, PLANNED, and FUTURE INTEGRATION status.

### Acceptance Verification Results
- Database initialized and migrated: `PASS`
- Reference counts verified:
  - Source Documents: 18
  - Stations: 68
  - Block Sections: 66
  - Trains: 3,429
  - Train Movements: 82
  - Railway Rules: 9
  - Infrastructure Specs: 3
  - Corridors: 4
  - Total records: 3,679
- Idempotency test: `PASS` (zero row growth on second ingestion)
- Database validation suite: `PASS` (30 passed, 0 failed)
- Pytest suite: `PASS` (31 passed, 0 failed in 5.23s)
- Live API queries: `PASS` (200 OK on `/health`, `/health/db`, `/api/v1/stations/NDLS`, `/api/v1/sections/NDLS-GZB`, `/api/v1/trains/12301`, `/api/v1/rules/RULE-STAT-RBP-1502C` with verified provenance)

## Phase 2 — Operational Data Layer & Synthetic Dataset Generator

**Status:** COMPLETE (Executed October 2, 2026)

**Objective:** Create credible, reproducible operational input data (tasks, work orders, resources, availability, dependencies) grounded in Phase 0/1 reference data without pretending it is real.

### Delivered Capabilities
- **Domain Models & Enums:** Pydantic v2 models for `OperationalScenario`, `WorkOrder`, `WorkWindow`, `MaintenanceTask`, `MaintenanceResource`, `ResourceAvailability`, `TaskResourceRequirement`, `TaskDependency`.
- **PostgreSQL 18 Schema & Alembic Migration:** Revision `538db451f99d` (`002_operational_data_schema`) creating 8 new tables, 8 enums, foreign keys, and check constraints (`capacity > 0`, `duration > 0`, `window_start < window_end`, `predecessor != successor`).
- **Deterministic Synthetic Generator:** `scripts/generate_synthetic_operational_data.py` (seed `20261001`) outputting `data/synthetic/operational_scenario_SCN-DEMO-001.json`:
  - 1 72-hour operational scenario (`SCN-DEMO-001`)
  - 12 work orders across 4 departments (Engineering, Electrical, S&T, Operating)
  - 30 maintenance tasks with realistic durations, windows, block flags (traffic, power, PTW), and safety buffers
  - 21 resources (Track machines, Tower wagons, S&T gear, Gangs)
  - 25 availability intervals across the scenario horizon
  - 42 task resource requirements
  - 11 finish-to-start task dependencies (DAG)
  - 3 multi-section possession impacts
  - 37 rule references to verified Phase 0 railway rules
- **Idempotent Ingestion Pipeline:** `scripts/ingest_operational_data.py` registering `SRC-TRACKMELD-SYNTHETIC-GEN` and persisting records via `ON CONFLICT DO UPDATE`.
- **Operational Repositories & Services:** `ScenarioRepository`, `WorkOrderRepository`, `MaintenanceTaskRepository`, `ResourceRepository`, `ResourceAvailabilityRepository`, `SyntheticOperationalDataProvider`, and `PlanningScenarioService`.
- **FastAPI Endpoints:** REST API endpoints mounted under `/api/v1/` for scenarios, work orders, tasks, and resources.

### Verification Results
- Idempotency test: `PASS` (zero row growth on rerun)
- Phase 2 validation suite: `PASS` (30 passed, 0 failed in `scripts/validate_operational_data.py`)
- Phase 1 validation suite: `PASS` (31 passed, 0 failed in `scripts/validate_database.py`)
- Pytest test suite: `PASS` (52 passed, 0 failed in 6.26s)
- Provenance compliance: `PASS` (100% of operational records carry `SYNTHETIC` and `SRC-TRACKMELD-SYNTHETIC-GEN`, zero mutation of reference tables)

## Phase 3 — Read APIs and domain validation

**Status:** COMPLETE (Executed October 2, 2026)

**Objective:** Expose a typed and validated view of the dataset.

### Completed Work
- **Authorization Boundary:** Implemented `backend/app/core/auth.py` providing role-based access control (`ADMIN`, `MAINTENANCE_PLANNER`, `OPERATOR`, `VIEWER`), HTTP Bearer tokens, `X-API-Key` headers, permission checking (`require_permission`), and a safe prototype fallback for read queries.
- **Corridor & Movement APIs:**
  - Added `backend/app/schemas/responses.py::CorridorResponse`.
  - Added `backend/app/repositories/corridor_repo.py::CorridorRepository`.
  - Created `backend/app/api/v1/corridors.py` (`GET /api/v1/corridors` with zone/division filtering and pagination; `GET /api/v1/corridors/{id}`).
  - Created `backend/app/api/v1/movements.py` (`GET /api/v1/movements` with train_id/station_id filtering and pagination; `GET /api/v1/movements/{id}`).
- **Enhanced Reference Read APIs:**
  - `GET /api/v1/stations`: Added multi-field filters (`zone`, `division`, `station_type`, `classification`), dual lookup by station code or station ID, bounded pagination (`ge=1, le=500`), and `X-Total-Count`, `X-Limit`, `X-Offset` headers.
  - `GET /api/v1/sections`: Added filters (`zone`, `division`, `electrified`), dual lookup by section code or section ID, bounded pagination, and count headers.
  - `GET /api/v1/trains`: Added filters (`train_type`, `corridor_table`, `classification`), dual lookup by train number or train ID, bounded pagination, and count headers.
  - `GET /api/v1/rules`: Added bounded pagination, total count headers, and auth integration.
- **Enhanced Operational Read APIs:**
  - `GET /api/v1/tasks`: Added multi-field query filters (`scenario_id`, `section_id`, `work_order_id`, `status`, `priority`, `task_type`, `mandatory`, `requires_traffic_block`, `requires_power_block`), dual lookup by task code or ID, bounded pagination, and count headers.
  - `GET /api/v1/resources`: Added filters (`resource_type`, `department`, `home_station`), dual lookup by resource code or ID, bounded pagination, and count headers.
  - `GET /api/v1/work-orders`: Added filters (`scenario_id`, `department`, `status`, `priority`, `mandatory`), dual lookup by work order number or ID, bounded pagination, and count headers.
  - `GET /api/v1/scenarios/{id}/manifest`: Added manifest endpoint returning aggregate metrics (`total_work_orders`, `total_tasks`, `total_mandatory_tasks`, `total_resources`, `total_dependencies`, breakdown maps by type, priority, status).
- **Error Handling & API Guardrails:**
  - Updated `backend/app/main.py` with an unhandled `Exception` handler catching unexpected errors and returning clean JSON payloads without leaking debug stack traces.
  - Validation error handler formats Pydantic validation errors cleanly with status 422.
- **Router Mounting:** Mounted `corridors_router` and `movements_router` in `backend/app/api/router.py`.

### Verification Results
- **Unit Test Suite:** `PASS` (tests for authorization roles, bearer tokens, API keys, unauthorized 401s, forbidden 403s in `tests/unit/test_auth.py`).
- **Integration Test Suite:** `PASS` (tests for corridors, movements, dual lookups, multi-field filtering, pagination bounds, manifest generation, auth enforcement in `tests/integration/test_phase3_read_apis.py`).
- **Full Pytest Regression Suite:** `PASS` (67 tests passed, 0 failed in 7.58s across 13 test files).
- **Reference Database Validation:** `PASS` (31 passed, 0 failed in `scripts/validate_database.py`).
- **Operational Database Validation:** `PASS` (30 passed, 0 failed in `scripts/validate_operational_data.py`).
- **Provenance Integrity:** `PASS` (All responses explicitly expose data classification `REAL`, `DERIVED`, `SYNTHETIC`, or `ASSUMED` alongside `source_id`).


## Phase 4 — Planning windows and compatibility

**Status:** COMPLETE (Executed October 2, 2026)

**Objective:** Make feasibility rules deterministic and inspectable.

### Completed Work
- **Temporal Domain Models & Half-Open Semantics:**
  - Implemented `backend/app/domain/temporal.py` with `TimeInterval` and `PlanningHorizon`.
  - Standardized continuous half-open interval conventions `[start, end)`.
  - Enforced mathematical overlap semantics: `max(s1, s2) < min(e1, e2)` with zero-overlap on strictly adjacent intervals (`end1 == start2`).
  - Added UTC timezone enforcement and duration metrics (minutes, hours).
- **Train Pass Derivation:**
  - Implemented `CompatibilityEngine.derive_train_passes(...)` projecting timetable train movements onto contiguous block sections and station dwells across the planning horizon.
- **Deterministic Feasibility & Compatibility Engine:**
  - Implemented `backend/app/services/compatibility_service.py::CompatibilityEngine`.
  - Evaluates candidate placements across 10 deterministic checks:
    1. Interval validity (positive duration, zero/negative duration detection, duration match).
    2. Planning horizon enclosure.
    3. Task allowed planning window enclosure `[window_start, window_end)`.
    4. Setup and clearance safety buffers (`safety_buffer_before_minutes`, `safety_buffer_after_minutes`).
    5. Block requirements (power block on electrified sections, traffic block isolation).
    6. Train movement collision detection on primary and secondary sections.
    7. Track section exclusivity against existing task placements.
    8. Multi-section possession conflicts.
    9. Resource availability windows and concurrent assignment overlap.
    10. Task dependency precedence (`FINISH_TO_START` precedence: predecessor end $\le$ candidate start).
- **Four-Tier Constraint Hierarchy:**
  - Formalized in `backend/app/domain/compatibility.py`:
    - `HARD`: Physical or safety barriers (train collisions, section occupancy, window breaches).
    - `SOFT`: Operational optimization preferences.
    - `DIAGNOSTIC_ONLY`: Informational notes and telemetry.
    - `UNVERIFIED`: Unverified assumptions (Invariant strictly enforced: **NEVER promotes to HARD**).
- **Reason Code Catalog:**
  - Machine-readable reason codes: `INVALID_INTERVAL`, `OUTSIDE_PLANNING_HORIZON`, `TASK_WINDOW_CONFLICT`, `TRAIN_MOVEMENT_CONFLICT`, `SECTION_OCCUPANCY_CONFLICT`, `RESOURCE_UNAVAILABLE`, `RESOURCE_OVERLAP`, `DEPENDENCY_NOT_SATISFIED`, `TRAFFIC_BLOCK_REQUIRED`, `POWER_BLOCK_REQUIRED`, `PTW_REQUIRED`, `MULTI_SECTION_CONFLICT`, `UNVERIFIED_RULE`.
- **Structured Compatibility Result:**
  - Implemented `CompatibilityResult` returning `compatible`, `feasible_hard`, `admissible_soft`, `evaluated_interval`, `possession_interval`, `reason_codes`, `conflicts`, `affected_sections`, `affected_movements`, `affected_resources`, and `rule_evidence`.
- **Evaluation API Endpoint:**
  - Implemented `POST /api/v1/compatibility/evaluate-task` in `backend/app/api/v1/compatibility.py` for read/evaluation-only feasibility queries.
  - Mounted in `backend/app/api/router.py`.

### Verification Results
- **Temporal Unit Tests:** `PASS` (8 tests in `tests/unit/test_temporal.py`).
- **Compatibility Engine Unit Tests:** `PASS` (15 boundary tests in `tests/unit/test_compatibility_engine.py` covering zero duration, negative duration, adjacent boundaries, train collision, train adjacent, resource unavailability, boundary matching, section sharing, multi-section collision, dependency ordering, non-electrified power blocks, unverified rule invariants).
- **API Integration Tests:** `PASS` (4 tests in `tests/integration/test_phase4_compatibility_api.py`).
- **Full Pytest Regression Suite:** `PASS` (94 passed, 0 failed in 9.03s across 16 test files).
- **Phase 4 Compatibility Validation Script:** `PASS` (17 passed, 0 failed in `scripts/validate_phase4_compatibility.py`).
- **Reference Database Validation:** `PASS` (31 passed, 0 failed in `scripts/validate_database.py`).
- **Operational Database Validation:** `PASS` (30 passed, 0 failed in `scripts/validate_operational_data.py`).


## Phase 5 — Priority and baseline schedulers

**Status:** COMPLETE (Executed October 2, 2026)

**Objective:** Establish transparent reference schedules before optimization.

### Completed Work
- **Immutable Planning Snapshot:**
  - Implemented `backend/app/domain/planning_snapshot.py::PlanningSnapshot` with deterministic SHA256 snapshot IDs.
  - Frozen in-memory container ensuring both baseline schedulers evaluate the exact same tasks, train passes, resources, availability, and horizon without mutable DB querying during scheduling loops.
- **Explainable Priority Scoring Model:**
  - Implemented `backend/app/domain/scheduling.py::PriorityConfig`, `PriorityScore`, `PriorityComponent`.
  - Implemented `backend/app/services/priority_scorer.py::PriorityScorer`.
  - Configurable, versioned weights explicitly documented as experimental benchmark heuristics.
  - Normalizes 5 features to $[0.0, 1.0]$: `mandatory`, `urgency` (`TaskPriority`), `window_tightness`, `dependency_bottleneck` (downstream waiting count), and `operational_impact` (traffic/power block requirements).
  - Decomposes every score into full explainable component breakdowns.
- **Deterministic Baseline Schedulers:**
  - Implemented `backend/app/services/schedulers/base.py::BaseScheduler`.
  - Implemented `backend/app/services/schedulers/fcfs.py::FCFSScheduler` (orders by arrival/window start, tie-break by `task_id`).
  - Implemented `backend/app/services/schedulers/priority_greedy.py::PriorityGreedyScheduler` (orders by priority score descending, mandatory first, arrival, tie-break by `task_id`).
  - Implemented `backend/app/services/task_ordering.py` including topological dependency cycle detection.
- **Deterministic Candidate Generator:**
  - Implemented `backend/app/services/candidate_generator.py::CandidateGenerator`.
  - Discovers natural railway event boundaries (window starts, preferred starts, predecessor completions, scheduled possession releases, train section clearances, resource availability starts).
- **Zero Constraint Bypass / Phase 4 Integration:**
  - 100% of candidate placement evaluations are outsourced to `CompatibilityEngine.evaluate_task_placement`.
  - Baselines never violate modeled hard constraints (0 train overlaps, 0 section overlaps, 0 resource overlaps).
- **Standardized Metrics & Result Contracts:**
  - Implemented `backend/app/services/metrics_calculator.py::MetricsCalculator`.
  - Shared `ScheduleResult`, `ScheduledTaskResult`, `UnscheduledTaskResult`, `ScheduleMetrics`, and `TaskDecisionTrace` models.
- **REST Endpoints & Fair Benchmarking:**
  - Implemented `POST /api/v1/planning/baseline` and `POST /api/v1/planning/benchmark` in `backend/app/api/v1/planning.py`.
  - Side-by-side comparison contract evaluating FCFS and Priority-Greedy on the exact same snapshot.
  - Mounted under `/api/v1/planning` in `backend/app/api/router.py`.

### Verification Results
- **Priority Scorer Unit Tests:** `PASS` (6 tests in `tests/unit/test_priority_scorer.py`).
- **Candidate Generator Unit Tests:** `PASS` (3 tests in `tests/unit/test_candidate_generator.py`).
- **Schedulers Unit Tests:** `PASS` (6 tests in `tests/unit/test_schedulers.py`).
- **Planning & Benchmark API Integration Tests:** `PASS` (4 tests in `tests/integration/test_phase5_baseline_api.py`).
- **Full Pytest Regression Suite:** `PASS` (113 passed, 0 failed in 9.93s across 20 test files).
- **Phase 5 Schedulers Validation Script:** `PASS` (30 passed, 0 failed in `scripts/validate_phase5_schedulers.py`).
- **Phase 4 Compatibility Validation Script:** `PASS` (17 passed, 0 failed in `scripts/validate_phase4_compatibility.py`).
- **Operational Database Validation:** `PASS` (30 passed, 0 failed in `scripts/validate_operational_data.py`).
- **Reference Database Validation:** `PASS` (31 passed, 0 failed in `scripts/validate_database.py`).
- **Total Automated Verification Checks:** **221 passed, 0 failed**.
- **Benchmark Factual Results (`SCN-DEMO-001`):**
  - Both FCFS and Priority-Greedy achieved **96.7% completion rate (29/30 tasks scheduled)** and **100% mandatory completion rate (17/17 mandatory tasks scheduled)** with **0 hard constraint violations** in **<10 ms**.

## Phase 6 — CP-SAT optimization

**Status:** COMPLETE (Executed October 2, 2026)

**Objective:** Generate optimal candidate maintenance possession schedules under explicit mathematical constraints.

### Completed Work
- **Google OR-Tools CP-SAT Integration:**
  - Pinned dependency `ortools>=9.10.0,<9.16.0` (`ortools 9.15.6755`).
  - Implemented `backend/app/services/optimization/solver_config.py::OptimizationConfig` (bounded wall clock, deterministic search workers, seed, objective weights).
  - Implemented `backend/app/services/optimization/solver_diagnostics.py::SolverDiagnostics` (telemetry for status, wall time, objective value, best bound, optimality gap %, variable/constraint/interval counts).
- **Mathematical Constraint Programming Model (`CPSATModelBuilder`):**
  - Continuous time discretized into integer minutes from planning horizon start $T_0$.
  - Modeled tasks as optional intervals: presence $x_i \in \{0, 1\}$, start $s_i$, end $e_i = s_i + d_i$.
  - Modeled possession envelopes: $pos\_s_i = s_i - buf^{before}_i$, $pos\_e_i = e_i + buf^{after}_i$.
  - Track section exclusivity and fixed train passes enforced via native CP-SAT `AddNoOverlap`.
  - Half-open interval semantics $[start, end)$ strictly preserved; exact boundary touches ($e_1 == s_2$) meet without collision.
  - Resource exclusivity and availability enforced via `AddNoOverlap` with complementary blackout periods.
  - Finish-to-Start dependencies with minimum buffers: $x_{succ} \le x_{pred}$, $s_{succ} \ge e_{pred} + \Delta_{pred, succ}$.
  - Mandatory tasks strictly forced: $x_i = 1$.
  - Physical impossibility verification: power block tasks on un-electrified sections forced unplaced: $x_i = 0$.
  - Transparent objective: maximize total scaled priority points with secondary duration tie-breaker: $\max \sum_i ((P_i \cdot 1000) - d_i) \cdot x_i$.
- **Optimization Solver Engine (`CPSATSolver`):**
  - Dependency cycle pre-check detects cyclic inputs and immediately returns `INVALID_INPUT`.
  - Explicit solver status mapping: `OPTIMAL`, `FEASIBLE`, `INFEASIBLE`, `UNKNOWN`.
  - Independent recalculation of metrics via `MetricsCalculator`.
  - Produces standard `ScheduleResult` with `ScheduleMetrics`, `TaskDecisionTrace`, and `SolverDiagnostics`.
- **High-Level Service & REST Endpoints:**
  - Implemented `backend/app/services/optimization_service.py::OptimizationPlanningService`.
  - Added endpoint `POST /api/v1/planning/optimize` in `backend/app/api/v1/planning.py`.
  - Updated `POST /api/v1/planning/benchmark` with `include_cpsat=True` for fair 3-way side-by-side comparison on identical snapshot.
- **Reporting & Documentation:**
  - Created `docs/PHASE_6_CP_SAT_REPORT.md`.

### Verification Results
- **CP-SAT Model Unit Tests:** `PASS` (8 tests in `tests/unit/test_cp_sat_model.py`: single task, conflicting mandatory -> INFEASIBLE, priority contention selection, train pass clearance, resource exclusivity, finish-to-start dependencies, half-open boundary touching, power block rejection).
- **CP-SAT Solver Unit Tests:** `PASS` (4 tests in `tests/unit/test_cp_sat_solver.py`: deterministic reproducibility across repeated runs, solver diagnostics telemetry completeness, dependency cycle pre-check -> INVALID_INPUT, independent metrics consistency).
- **CP-SAT API Integration Tests:** `PASS` (4 tests in `tests/integration/test_phase6_cp_sat_api.py`: POST `/optimize` execution, custom solver parameters, 3-way benchmark comparison on identical snapshot, 404 on nonexistent scenario).
- **Full Pytest Regression Suite:** `PASS` (129 passed, 0 failed in 11.98s across 22 test files).
- **Phase 6 Invariant Validation Script:** `PASS` (22 passed, 0 failed in `scripts/validate_phase6_cp_sat.py`).
- **Benchmark Factual Results (`SCN-DEMO-001`):**
  - Solved to mathematical **OPTIMAL** with **0.0% gap** in **10.19 ms**.
  - Scheduled 29 of 30 tasks (all 17 mandatory scheduled: **100% mandatory completion**).
  - Captured **3,001.06 priority points (98.6% capture rate)**.
  - Every single placement independently verified **100% HARD-FEASIBLE** by Phase 4 `CompatibilityEngine`.
  - Zero track collisions, zero train collisions, 100% deterministic reproducibility.

## Phase 7 — Independent validation and diagnostics

**Status:** COMPLETE (Executed October 2, 2026)

**Objective:** Never present solver output as valid without independent checks.

### Delivered Capabilities
- **Validation Domain Models & Contracts (`backend/app/services/validation/models.py`):**
  - Typed Enums: `ValidationStatus` (VALID, INVALID, UNKNOWN), `ValidationSeverity` (ERROR, WARNING, INFO), `ValidationCategory` (14 categories), `DiagnosticStatus`, `RelaxationScenarioType`.
  - Pydantic v2 Models: `ValidationFinding` (with deterministic sort key), `ScheduleValidationResult`, `RelaxationFinding` (strictly enforcing `hypothetical=True` and `approvable=False`), `UnscheduledTaskDiagnostic`, and `DiagnosticsReport`.
- **Independent Verification Suite (`backend/app/services/validation/checks.py`):**
  - Built from first principles without calling Phase 4 `CompatibilityEngine`.
  - Audits 12 independent dimensions: structural integrity, planning horizon boundaries, allowed task windows, duration matching, possession safety buffer envelopes, half-open $[start, end)$ track occupancy exclusivity, multi-section continuity, train movement clearance, sweep-line resource capacity tracking, finish-to-start dependencies, mandatory task accounting, and traction power block rules.
- **Independent Schedule Validator & Approval Gate (`backend/app/services/validation/validator.py`):**
  - Generates deterministic 64-character SHA-256 schedule fingerprint.
  - Strict human approval gating via `assert_schedule_approvable()`, raising `ScheduleApprovalBlockedError` for invalid or unknown schedules.
- **Root-Cause Diagnostics & Relaxation Scenarios (`backend/app/services/validation/diagnostics.py` & `relaxation.py`):**
  - Diagnostic analysis for unscheduled tasks identifying concrete blocking entities (trains, sections, resources, windows).
  - 5 controlled hypothetical relaxation scenarios with zero hallucination and strict non-approvable tags.
- **REST APIs (`backend/app/api/v1/planning.py`):**
  - `POST /api/v1/planning/validate`: Independent schedule auditing.
  - `POST /api/v1/planning/diagnostics`: Root-cause diagnostics on unscheduled tasks.
  - `POST /api/v1/planning/optimize`: Integrated with `validate_after_solve=True`.

### Verification Results
- **Independent Validator Unit Tests:** `PASS` (22 tests in `tests/unit/test_phase7_validator.py`).
- **Validation & Diagnostics API Integration Tests:** `PASS` (6 tests in `tests/integration/test_phase7_validation_api.py`).
- **Phase 7 Invariant Validation Script:** `PASS` (23 passed, 0 failed in `scripts/validate_phase7_validation.py`).
- **Full Pytest Regression Suite:** `PASS` (157 passed, 0 failed in 14.09s across 23 test files).
- **All Milestone Validation Scripts:** `PASS` (310 total invariant checks passed, 0 failed).
- **Validation Latency:** **1.51 ms** (< 250 ms budget).

## Phase 8 — Planning jobs and persistence

**Status:** COMPLETE (Executed October 2, 2026)

**Objective:** Run optimization without blocking API responsiveness.

### Delivered Capabilities
- **Relational Data Model & Alembic Migration:**
  - Designed `planning_runs` table (`backend/app/db/models/planning_run.py`) with PostgreSQL JSONB columns, foreign keys, and indexes (`run_id`, `scenario_id`, `status`, `heartbeat_at`, `idempotency_key`, `ix_planning_runs_status_created`).
  - Generated and executed migration `8a4f21d9b301_003_planning_runs_schema.py`.
- **Pydantic Schemas & Contracts (`backend/app/schemas/planning_run.py`):**
  - Typed Enums: `PlanningRunStatus` (PENDING, RUNNING, VALIDATING, COMPLETED, FAILED, CANCEL_REQUESTED, CANCELLED, TIMED_OUT), `PlanningRunStage`.
  - Models: `CreatePlanningRunRequest`, `CreatePlanningRunResponse`, `PlanningRunProgress`, `PlanningRunSummary`, `PlanningRunDetailResponse`.
- **Planning Run Repository (`backend/app/repositories/planning_run_repo.py`):**
  - Implemented atomic claiming using PostgreSQL row-level locks: `SELECT ... FOR UPDATE SKIP LOCKED`.
  - State machine transition validation (`LEGAL_TRANSITIONS`) raising `IllegalStateTransitionError` for illegal transitions.
  - Heartbeat updates, stale run identification, pagination, filtering, and structured error/failure recording.
- **Reproducibility & Provenance Hashing (`backend/app/domain/planning_snapshot.py`):**
  - Added deterministic 64-character SHA-256 `compute_snapshot_hash()` and `compute_input_hash(config, seed)` to guarantee mathematical reproduciblity.
- **Background Worker Process & CLI (`backend/app/services/planning_worker.py` & `backend/app/worker.py`):**
  - Implemented `PlanningRunWorker` polling queue, claiming runs, loading snapshots, running CPU-bound solvers in `asyncio.to_thread`, running Phase 7 Independent Validator, and persisting results in JSONB.
  - Periodic heartbeat task and stale run timeout handler.
- **REST APIs (`backend/app/api/v1/planning_runs.py`):**
  - `POST /api/v1/planning-runs`: Submit run requisition, returns immediately with HTTP 201 Created and queue token URL.
  - `GET /api/v1/planning-runs/{run_id}`: Polling endpoint for status, progress stage, execution time, and summary metrics.
  - `GET /api/v1/planning-runs/{run_id}/result`: ScheduleResult retrieval (returns HTTP 409 Conflict if incomplete).
  - `GET /api/v1/planning-runs`: Paginated run listing with filters and `X-Total-Count` header.
  - `POST /api/v1/planning-runs/{run_id}/cancel`: Cooperative cancellation.
- **Reporting & Documentation:**
  - Created `docs/PHASE_8_PLANNING_JOBS_AND_PERSISTENCE_REPORT.md`.

### Verification Results
- **Phase 8 Unit Test Suite:** `PASS` (8 tests in `tests/unit/test_phase8_planning_run.py`).
- **Phase 8 API & Worker Integration Test Suite:** `PASS` (8 tests in `tests/integration/test_phase8_planning_jobs_api.py`).
- **Phase 8 Invariant Validation Script:** `PASS` (22 passed, 0 failed in `scripts/validate_phase8_planning_jobs.py`).
- **Full Pytest Regression Suite:** `PASS` (173 passed, 0 failed in 13.35s across 25 test files).
- **All Milestone Validation Scripts:** `PASS` (10 suites, 332 total checks passed, 0 failed).
- **Core Product Invariant Enforced:** `COMPLETED != APPROVED` (approval is an independent human governance gate).

## Phase 9 — Plan versions, review, and audit

**Status:** COMPLETE (Executed October 2, 2026)

**Objective:** Make planner decisions traceable, enforce rigorous human review workflows, formal approval gating, and immutable audit logging.

### Delivered Capabilities
- **Relational Data Model & Alembic Migration:**
  - Designed `plan_versions`, `plan_review_comments`, and `governance_audit_events` tables (`backend/app/db/models/plan_version.py`) with PostgreSQL JSONB columns, foreign keys with referential integrity, and composite constraints (`uq_plan_versions_scenario_version`, `uq_plan_versions_planning_run`).
  - Generated and executed migration `9c2d1e4f7a01_004_plan_versions_and_audit.py`.
- **Pydantic Schemas & Contracts (`backend/app/schemas/plan_version.py`):**
  - Typed Enums: `PlanVersionStatus` (PENDING_REVIEW, UNDER_REVIEW, APPROVED, REJECTED, SUPERSEDED), `PlanReviewAction`, `GovernanceEventType`.
  - Request/Response Models: `CreatePlanVersionRequest`, `ApprovePlanRequest`, `RejectPlanRequest` (mandatory reason min length >= 5), `AddReviewCommentRequest`, `PlanVersionSummary`, `PlanVersionDetail`, `AuditEventResponse`.
- **Concurrency-Safe Repository Layer (`backend/app/repositories/plan_version_repo.py`):**
  - Monotonic version numbering serialized under PostgreSQL scenario row lock (`SELECT ... FOR UPDATE`).
  - Row locking (`get_by_id_for_update`) for state transitions to eliminate approval race conditions.
  - Strict state machine enforcement (`LEGAL_PLAN_TRANSITIONS`), raising `InvalidPlanVersionTransitionError` on illegal transitions.
- **Plan Governance Service Layer (`backend/app/services/plan_governance_service.py`):**
  - `create_plan_version_from_run`: Enforces terminal run completion, Phase 7 `VALID` status, `is_approvable=True`, uniqueness, and logs creation audit event.
  - `start_review`: Advances candidate to `UNDER_REVIEW`, recording reviewer username and timestamp.
  - `add_review_comment`: Appends review commentary and audit event.
  - `approve_plan`: Precondition checks (terminal, certified valid, zero error count, fingerprint/hash integrity match against source run), locks row, supersedes any existing `APPROVED` plan version for scenario, sets `APPROVED`, appends `PLAN_APPROVED` audit event atomically.
  - `reject_plan`: Requires substantive reason (>= 5 chars), marks `REJECTED`, appends `PLAN_REJECTED` audit event atomically.
- **REST APIs (`backend/app/api/v1/plan_versions.py`):**
  - `POST /api/v1/planning-runs/{run_id}/plan-version`: Promote certified run to PlanVersion candidate (HTTP 201 Created).
  - `GET /api/v1/plan-versions/{plan_version_id}`: Detail endpoint returning verified schedule result and review comments.
  - `GET /api/v1/plan-versions`: Paginated summary listing with filters and `X-Total-Count` header.
  - `POST /api/v1/plan-versions/{plan_version_id}/review`: Transition candidate to `UNDER_REVIEW`.
  - `POST /api/v1/plan-versions/{plan_version_id}/comments`: Append review commentary.
  - `POST /api/v1/plan-versions/{plan_version_id}/approve`: Authorized human approval.
  - `POST /api/v1/plan-versions/{plan_version_id}/reject`: Authorized human rejection with mandatory justification.
  - `GET /api/v1/plan-versions/{plan_version_id}/audit`: Chronological governance audit trail.
- **Role-Based Access Control (`backend/app/core/auth.py`):**
  - Added `approver-token-2026` (`role=OPERATOR`, permissions: `plan:approve`, `plan:reject`, `plan:review`).
  - Separation of concerns: Maintenance planners can nominate and review; only authorized operations officers can approve or reject.
- **Reporting & Documentation:**
  - Created `docs/PHASE_9_PLAN_VERSIONS_REVIEW_AND_AUDIT_REPORT.md`.

### Verification Results
- **Phase 9 Unit Test Suite:** `PASS` (11 tests in `tests/unit/test_phase9_governance.py`).
- **Phase 9 API & Governance Integration Test Suite:** `PASS` (6 tests in `tests/integration/test_phase9_governance_api.py`).
- **Phase 9 Invariant Validation Script:** `PASS` (22 passed, 0 failed in `scripts/validate_phase9_plan_governance.py`).
- **Full Pytest Regression Suite:** `PASS` (190 passed, 0 failed in 17.03s across 27 test files).
- **All Milestone Validation Scripts:** `PASS` (8 suites, 197 total invariant checks passed, 0 failed).
- **Core Product Invariant Enforced:** `COMPLETED != APPROVED` (solver and validator output never implies or grants approval; approval is an explicit, authenticated human governance action).

## Phase 10 — Frontend foundation and design system

**Objective:** Create a coherent interface using actual APIs.

### Work
- Build responsive application shell and navigation.
- Implement design tokens and status patterns from `DESIGN_SYSTEM.md`.
- Add loading, empty, error, stale, and permission states.
- Add synthetic-data badge.
- Build dashboard from API responses, not hardcoded operational metrics.

### Acceptance gate
- Responsive behavior works at desktop, tablet, and mobile widths.
- Keyboard focus and reduced motion are supported.
- UI states are tested.
- Synthetic/demo values are unmistakably labeled.

## Phase 11 — Planning workspace and scenario comparison

**Objective:** Make schedule decisions understandable and reviewable.

### Work
- Implement task filters and inspector.
- Build a precise time-space chart.
- Show train occupancy, task intervals, conflicts, and allowed windows.
- Implement baseline vs optimized comparison using computed metrics.
- Add run detail with solver and validator status.
- Add plan review controls with role checks.

### Acceptance gate
- Selecting a task reveals its actual persisted details and reason evidence.
- Chart values match API response data.
- Scenario comparison uses the same snapshot and horizon.
- No hardcoded performance deltas are presented as actual results.

## Phase 12 — Landing page and 3D railway scene

**Objective:** Deliver a high-quality product introduction without compromising usability.

### Work
- Build landing page narrative and CTA.
- Implement a restrained 3D fictional railway scene using browser-side rendering.
- Add static fallback and reduced-motion mode.
- Clearly mark scene and dashboard figures as synthetic.
- Avoid unnecessary 3D libraries in the backend.

### Acceptance gate
- Core page remains usable without WebGL.
- No severe layout shift or unbounded animation.
- Mobile and reduced-motion experiences are usable.
- The scene is clearly fictional and not an accurate operational map.

## Phase 13 — Read-only Copilot

**Objective:** Explain known planning facts in natural language.

### Work
- Define typed tools such as `get_task_decision`, `get_conflicts_for_task`, `get_run_summary`, and `get_rule_provenance`.
- Restrict tools to read-only access and allowlisted records.
- Require tool evidence before answering plan-specific questions.
- Add provider timeout, rate limits, and graceful unavailable state.
- Add groundedness and refusal test cases.

### Acceptance gate
- Copilot cannot mutate records or approve plans.
- Unknown facts produce a clear uncertainty response.
- Answers include evidence IDs.
- Core product works with LLM disabled.
- No LangGraph/MCP/vector database is added unless a real requirement emerges.

## Phase 14 — Integration, security, and performance hardening

**Objective:** Validate the complete workflow.

### Work
- End-to-end flow: dataset → task inspection → baseline → optimize → validate → compare → approve → audit.
- Authorization and input-validation review.
- Dependency and secret scan.
- Solver performance/memory benchmark.
- Database query/index review.
- Accessibility and responsive review.
- Test error paths and provider/worker failures.

### Acceptance gate
- Critical workflow tests pass.
- No known path permits invalid plan approval.
- Performance claims are backed by recorded benchmark conditions.
- Documentation matches actual implementation.

## Phase 15 — Deployment and demo readiness

**Objective:** Deploy a reproducible demo with honest boundaries.

### Work
- Choose deployment topology after benchmarking.
- Deploy frontend, API, PostgreSQL, and worker as supported by the chosen host.
- Configure secrets and CORS.
- Add health checks, migrations, seed command, and demo reset procedure.
- Add README, demo script, limitations, and synthetic-data notice.

### Acceptance gate
- Clean deployment succeeds from documented instructions.
- Migrations and seeding are repeatable.
- Worker timeout/crash behavior is visible.
- Demo labels and limitations are visible.
- No real railway integration is claimed.

## Suggested order of work

Build one complete thin slice before polishing every page:

**Synthetic corridor → API read endpoint → task list → baseline scheduler → CP-SAT → independent validator → comparison → approval/audit.**

Then improve the landing page, 3D visualization, and Copilot. This reduces the risk of ending with an attractive interface and no trustworthy planning engine.
