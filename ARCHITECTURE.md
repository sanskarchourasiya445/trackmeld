# TrackMeld System Architecture

**Architecture style:** Modular application with a separate optimization worker  
**Initial deployment:** Single web app + API + PostgreSQL; worker may run as a separate process/service  
**Product boundary:** Prototype decision support only

## 1. System context & Implementation Status

### Architecture Status Overview
- **IMPLEMENTED (Phase 1):**
  - Canonical Pydantic v2 domain models with strict cryptographic and domain provenance (`REAL`, `DERIVED`, `SYNTHETIC`, `ASSUMED`).
  - PostgreSQL schema with Alembic migration `001_initial_schema` reproducing all 8 domain tables, constraints, foreign keys, and indexes.
  - Deterministic, 100% idempotent reference data ingestion (`scripts/ingest_phase0.py`) loading 3,679 Phase 0 records.
  - Repository access layer (`StationRepository`, `SectionRepository`, `TrainRepository`, `TrainMovementRepository`, `RailwayRuleRepository`, `InfrastructureRepository`, `SourceDocumentRepository`).
  - FastAPI foundation with request ID middleware (`X-Request-ID`), structured error payloads, health probes (`/health`, `/health/db`), and v1 reference endpoints.
  - Abstract operational data interface boundary (`OperationalDataProvider`).
  - Automated database validation suite (`scripts/validate_database.py`) and comprehensive test suite (`pytest`).
- **PLANNED (Phase 2 & Phase 3):**
  - Phase 2: Maintenance task requisition models, resource catalog, and deterministic synthetic task generator.
  - Phase 3: OR-Tools CP-SAT interval scheduler, hard compatibility constraints, independent schedule validator, baseline comparisons.
  - Phase 4: Next.js frontend workstation and interactive time-space diagram.
  - Phase 5: Read-only evidence-grounded AI copilot service.
- **FUTURE INTEGRATION (Post-Hackathon / Authorized Access):**
  - Authorized Indian Railways Railnet / CRIS system connectors for BDMS, TMS, and COA.

```mermaid
flowchart LR
    U[Planner / Requester / Reviewer] --> WEB[Next.js Web App (Planned)]
    WEB -->|HTTPS REST| API[FastAPI API (Implemented)]
    API --> DB[(PostgreSQL 16 Implemented)]
    API --> JOB[Planning Job / Worker Interface (Planned)]
    JOB --> WORKER[Solver Worker (Planned)]
    WORKER --> DB
    WORKER --> ENGINE[CP-SAT Optimization Engine (Planned)]
    ENGINE --> DB
    API --> COP[Read-only Copilot Service (Planned)]
    COP --> TOOLS[Typed Diagnostic Tools (Planned)]
    TOOLS --> DB
    TOOLS --> ENGINE
```

The Copilot is optional. The core workflow functions without an LLM provider. The reference data layer is fully operational and verified against PostgreSQL.

## 2. Technology choices

### Web
- Next.js + React + TypeScript
- Tailwind CSS and a consistent component system
- Lucide icons
- Three.js / React Three Fiber only for the landing-page network scene and only with a fallback
- A dedicated time-space chart for planning data; 3D is not the primary operational schedule representation

### API
- Python + FastAPI
- Pydantic request/response schemas
- SQLAlchemy
- Alembic migrations
- Structured logging and request IDs

### Data
- PostgreSQL
- Synthetic data generator with reproducible seeds and provenance
- No vector database for structured rule records in MVP

### Optimization
- Google OR-Tools CP-SAT
- Separate, bounded planning job execution
- Independent validation module
- FCFS and priority-greedy baselines

### AI
- Provider-agnostic LLM behind a small interface
- Typed read-only tools
- No schedule generation authority, approval tool, or write access
- No LangGraph/MCP in MVP unless a later requirement proves the value

## 3. Core module boundaries

```text
apps/
  web/       Next.js UI, view models, API client
  api/       FastAPI routes, auth, request orchestration
  worker/    planning job runner and resource limits
packages/
  domain/    entities, enums, time/unit helpers, reason codes
  schemas/   shared API/data contracts where practical
  planning/  window derivation, priority, compatibility, baselines,
             CP-SAT model, validator, diagnostics, metrics
  copilot/   prompt, provider adapter, read-only tool definitions
data/
  synthetic/ seed configurations and generator metadata
docs/
tests/
```

This is a logical layout, not a command to create a monorepo with unnecessary packaging overhead. If a simpler repository layout better fits the initial setup, preserve the same boundaries without overengineering.

## 4. Request-to-plan flow

1. API validates user authorization and request schema.
2. API resolves corridor, horizon, scenario, and input data version.
3. API creates a `planning_run` and immutable input snapshot/reference.
4. Worker loads the snapshot and runs input validation.
5. Window engine derives candidate windows and train occupancy intervals.
6. Priority engine calculates configured priority features and stores the feature breakdown.
7. Compatibility engine evaluates task/task, task/track, resource, and modeled rule relationships.
8. FCFS and priority-greedy baselines run on the same input snapshot.
9. CP-SAT produces a candidate schedule under a time limit.
10. Independent validator checks every assignment, interval, resource use, and hard constraint.
11. Diagnostics produce stable reason codes and evidence references.
12. Metrics service calculates comparison metrics from actual outputs.
13. Results and run metadata are persisted.
14. UI shows solver status and validation status separately.
15. Human review can create a new version, reject, or approve a validated candidate.

## 5. Optimization modeling guidance

### Avoid combinatorial bundle pre-generation as the default

Do not enumerate the powerset of tasks. A bounded clique strategy can still generate many candidates; it does **not** guarantee at most `K × task_count` bundles.

Start with task-level optional intervals:
- One optional interval per task or task placement alternative.
- Explicit allowed start windows.
- Train occupancy as fixed intervals on the relevant section/line.
- `NoOverlap`/disjunctive constraints where the domain model supports them.
- Resource capacities and compatibility constraints.
- Objective terms for task coverage/priority, number of work windows, and modeled duration/cost.

If bundling tasks into one possession is a required decision variable, model it explicitly and introduce candidate groups only with a documented generation bound and benchmark. Do not assume `max(duration_i)` is always the correct bundled duration: work sequencing, setup, clearance, resource sharing, and overlap semantics must be explicitly modeled. For the MVP, use a simpler transparent bundling model and label all assumptions.

### Hard constraints vs objective preferences

Hard constraints determine feasibility and cannot be traded away through objective weights. Soft preferences guide selection among feasible candidates. Do not represent a safety-critical constraint merely as a large penalty.

### Solver results

Persist:
- solver status
- independent validation status
- elapsed time
- time limit
- objective value and best bound when available
- number of tasks assigned/unassigned
- model/configuration version
- input snapshot ID
- solver warnings/errors

Never call a feasible incumbent “optimal” unless the solver status confirms optimality.

## 6. Job execution and deployment

The solver may be CPU/memory-heavy. Keep the FastAPI API process responsive:
- Use a separate worker process/service for solver jobs where practical.
- Apply a solver time limit and bounded input size.
- Persist job state so UI refresh does not lose progress.
- Make job submission idempotent where possible.
- Return a `run_id` and poll or stream status.
- Do not assume the API host supports long-running CPU-bound tasks.

For an initial low-resource deployment, use PostgreSQL plus a lightweight API and a separate worker only if the platform permits it. If the host has a strict RAM cap, benchmark real memory before selecting the deployment topology. A small synthetic CP-SAT workload is not automatically “heavy”; measure it. Avoid deploying a 3D rendering process on the backend—WebGL rendering happens in the browser.

## 7. API conventions

Prefix: `/api/v1`

Use stable request/response models, pagination, and consistent errors. Suggested endpoints:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Liveness/readiness information (avoid leaking secrets) |
| `GET` | `/api/v1/corridors` | List demo corridors |
| `GET` | `/api/v1/sections` | List sections and topology |
| `GET` | `/api/v1/trains` | List synthetic trains |
| `GET` | `/api/v1/train-passes` | List occupancy intervals for a horizon |
| `GET` | `/api/v1/tasks` | Filter and paginate maintenance tasks |
| `POST` | `/api/v1/tasks` | Create a draft task |
| `GET` | `/api/v1/tasks/{task_id}` | Task detail |
| `POST` | `/api/v1/planning-runs` | Create a run from a selected input snapshot |
| `GET` | `/api/v1/planning-runs/{run_id}` | Run status and summary |
| `GET` | `/api/v1/planning-runs/{run_id}/results` | Plan assignments, diagnostics, metrics |
| `GET` | `/api/v1/planning-runs/{run_id}/comparison` | Compare baselines and optimized result |
| `POST` | `/api/v1/plans/{plan_id}/approve` | Approve a validated candidate, subject to authorization |
| `POST` | `/api/v1/plans/{plan_id}/reject` | Reject a candidate with reason |
| `GET` | `/api/v1/plans/{plan_id}/audit` | Retrieve audit events |
| `POST` | `/api/v1/copilot/explain` | Evidence-grounded read-only explanation |

Use `202 Accepted` for asynchronous planning run creation. Include errors for invalid input, unauthorized access, missing entities, duplicate/idempotent submissions, infeasible plans, worker failures, and provider failures.

## 8. Data and persistence boundaries

- PostgreSQL is the source of truth for persisted domain entities and plan versions.
- Alembic migrations are authoritative for schema evolution.
- Generated dataset files are input artifacts, not a substitute for relational integrity.
- A planning run must point to the exact input snapshot/configuration used.
- Approved plans are immutable; edits create a new candidate/version.
- Audit logs should be append-only at the application layer. A SHA-256 hash can detect changes only if the expected digest is protected; hashing alone is not immutable storage or a legal signature.

## 9. Security

- Enforce role permissions in API/service layer.
- Use short, explicit permissions for approval and administration.
- Keep LLM tools read-only and allowlist tool functions.
- Validate all tool arguments independently of model output.
- Do not pass secrets or unrestricted database access to the LLM.
- Use timeouts and error boundaries for external provider calls.
- Redact tokens, credentials, and sensitive payloads from logs.
- Treat user prompts and imported documents as untrusted input.

## 10. Observability

Use structured events with:
- `request_id`
- `user_id` or actor ID where appropriate
- `planning_run_id`
- `input_snapshot_id`
- `tool_execution_id` for Copilot tools
- duration, status, error category, and solver result status

Do not log credentials or unnecessary raw prompts. Capture metrics for API latency, queue/run duration, solver status distribution, validation failures, memory usage, and LLM errors.

## 11. Failure behavior

- API unavailable: UI shows retryable error.
- Worker unavailable: run is marked queued/failed accurately; do not leave it `RUNNING` forever.
- Solver timeout: return a validated feasible incumbent if one exists; otherwise show timeout/no-feasible-result.
- Validator failure: candidate is not eligible for approval.
- Database failure: no false success response.
- LLM provider failure: hide/disable Copilot with clear message; planning remains available.
- WebGL failure: render static network fallback.
- Missing evidence: Copilot says it cannot determine the answer from available records.

## 12. Architecture decision summary

- Modular application, not premature microservices.
- PostgreSQL + Alembic for structured data.
- CP-SAT for constrained optimization.
- Separate worker boundary for CPU-bound planning.
- Synthetic data only for initial demonstration.
- Deterministic rules/diagnostics before LLM explanation.
- No LangGraph, MCP, or vector RAG in MVP.
