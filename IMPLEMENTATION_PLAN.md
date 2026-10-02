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

**Objective:** Make feasibility rules deterministic and inspectable.

### Work
- Define time representation and half-open interval convention.
- Derive allowed windows from the synthetic scenario.
- Implement train occupancy conflict checks.
- Implement track/line and resource availability checks.
- Implement task compatibility and stable reason codes.
- Classify constraints as hard, soft, diagnostic-only, or unverified.
- Keep source/provenance metadata attached to rules.

### Acceptance gate
- Unit tests cover boundaries, adjacent intervals, overlaps, missing data, and multiple simultaneous conflicts.
- A task with an invalid window is rejected or marked explicitly.
- Unverified railway-specific assumptions cannot silently become authoritative safety rules.

## Phase 5 — Priority and baseline schedulers

**Objective:** Establish transparent reference schedules before optimization.

### Work
- Implement configurable priority formula with feature breakdown.
- Implement FCFS baseline.
- Implement priority-greedy baseline.
- Ensure both consume the same input snapshot and hard constraints.
- Produce comparable result schemas and metrics.

### Acceptance gate
- Scores are reproducible and explainable.
- Weights are configurable and documented as experimental.
- Baselines never violate modeled hard constraints.
- Metric definitions are shared across methods.

## Phase 6 — CP-SAT optimization

**Objective:** Generate candidate plans under explicit constraints.

### Work
- Model tasks as optional intervals or explicit placement alternatives.
- Add train occupancy, track exclusivity, resources, windows, and required dependencies.
- Define a transparent objective with separate hard constraints and soft preferences.
- Add solver time limit and bounded instance size.
- Persist solver status, objective/bound, runtime, model version, and input snapshot.
- Only introduce group/bundle variables after documenting how bundle duration, shared setup, clearance, and compatibility work.

### Acceptance gate
- Small hand-calculated instances have known expected behavior.
- Solver result is checked by independent validator.
- Tests distinguish `OPTIMAL`, `FEASIBLE`, `INFEASIBLE`, and `UNKNOWN`/timeout.
- A timeout cannot be reported as proven optimal.
- Benchmark the target workload on actual development/deployment hardware.

## Phase 7 — Independent validation and diagnostics

**Objective:** Never present solver output as valid without independent checks.

### Work
- Implement validator separately from the solver model where practical.
- Validate all hard constraints against the returned schedule.
- Generate structured conflict records and task decision reasons.
- Add bounded diagnostic/relaxation suggestions only when they can be re-solved and verified.
- Store evidence identifiers for every explanation.

### Acceptance gate
- Tests inject intentionally invalid assignments and validator catches them.
- A failed validation blocks approval.
- Unexplained tasks receive an explicit incomplete/unknown diagnostic status.

## Phase 8 — Planning jobs and persistence

**Objective:** Run optimization without blocking API responsiveness.

### Work
- Create planning-run/job lifecycle.
- Persist input snapshot reference and run configuration.
- Execute solver in a separate worker process/service where practical.
- Implement status polling and failure recovery.
- Make repeated submissions idempotent where feasible.
- Add resource limits and timeouts.

### Acceptance gate
- UI can refresh during a run without losing state.
- Worker crash/timeout produces a terminal status.
- Duplicate submission behavior is documented.
- API remains responsive during solver execution.

## Phase 9 — Plan versions, review, and audit

**Objective:** Make planner decisions traceable.

### Work
- Implement plan candidate/version tables.
- Add review, approval, rejection, and reason capture.
- Require independent validation before approval.
- Make approved versions immutable; edits create a new version.
- Append audit events and optional hash chaining.
- Add role-based access control tests.

### Acceptance gate
- Invalid candidate cannot be approved.
- Approved data cannot be edited in place.
- Each approval/rejection has actor, timestamp, and reason.
- Audit hashes are described as tamper-evidence, not as standalone immutability/legal signature.

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
