# TrackMeld

> **Railway possession planning and AI-assisted decision-support platform combining deterministic domain rules, constraint-based optimization, independent schedule validation, spatial infrastructure semantics, human governance, and grounded operational explanation.**

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Google OR-Tools](https://img.shields.io/badge/Google%20OR--Tools-CP--SAT-F4B400)](https://developers.google.com/optimization)
[![Next.js 16](https://img.shields.io/badge/Next.js-16%20App%20Router-000000?logo=next.js&logoColor=white)](https://nextjs.org/)
[![TypeScript 5](https://img.shields.io/badge/TypeScript-5.x-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Playwright E2E](https://img.shields.io/badge/Playwright-E2E%20Verified-45ba4b?logo=playwright&logoColor=white)](https://playwright.dev/)
[![Automated Tests](https://img.shields.io/badge/Tests-472%20Passing-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 1. Why TrackMeld?

Railway infrastructure requires taking physical tracks out of commercial service for maintenance, renewal, and inspection—periods known as **engineering possessions** or **track blocks**. In high-density mixed-traffic corridors, allocating possession windows is one of the most operationally demanding combinatorial challenges in transport logistics.

Track maintenance cannot be scheduled in a vacuum. Every possession requisition directly contends with:
- **Commercial Timetables**: Passenger express, suburban, and freight services operating across shared running lines.
- **Inter-Departmental Work**: Track Engineering (P-Way), Overhead Electrical Traction (OHE power isolations), and Signalling & Telecom (S&T interlocking and point machines) competing for identical track blocks.
- **Safety Buffers & Headways**: Mandatory setup and teardown clearance buffers before and after physical work.
- **Resource Constraints**: High-value specialized track machinery (tamping machines, ballast cleaners) and certified maintenance gangs with strict shift limits.
- **Precedence Dependencies**: Multi-stage maintenance tasks where track lifting, tamping, and track dressing must occur in strict sequential order.
- **Adjacent-Track Hazards**: Maintenance work on one line frequently imposes caution orders or full traffic blocks on neighboring parallel running lines.

### The Failure of Heuristic & Calendar Schedulers

When possession planning relies on manual deliberation, isolated spreadsheets, or local greedy schedulers:
1. **Global Constraint Coupling**: Scheduling one task on a section alters the feasibility of multiple downstream tasks across adjacent sections and intersecting train paths.
2. **Cascading Timetable Delay**: Late possession cancelations or improperly buffered worksites force trains to slow unexpectedly, propagating delays across entire zonal divisions.
3. **Safety Vulnerabilities**: Human schedulers cannot reliably track complex multi-track adjacent clearances and traction power boundaries across dozens of simultaneous worksites.

TrackMeld formulates possession scheduling as a **mathematically rigorous discrete constraint programming problem**, verifies generated schedules through an **isolated 13-category safety audit engine**, and enforces **four-eyes human authorization** before any operational plan can be enacted.

---

## 2. Core Governance Principle

TrackMeld is an operational **decision-support platform**, not an autonomous railway dispatch or signalling control system. The system enforces an uncompromising separation of responsibilities:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                           TRACKMELD GOVERNANCE CHAIN                                             │
│                                                                                                                  │
│    Rules Classify  ──►  Optimization Schedules  ──►  Validator Verifies  ──►  Human Reviews  ──►  Human Approves │
│                                                                                                                  │
│    OPTIMAL ≠ APPROVED   │   FEASIBLE ≠ APPROVED   │   VALID ≠ APPROVED   │   APPROVABLE ≠ APPROVED   │   CREATOR ≠ APPROVER   │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Non-Negotiable Operational Boundaries

- **`COMPLETED ≠ APPROVED`**: The successful execution of a background planning job merely persists a mathematical schedule result. It does not authorize operational execution.
- **`OPTIMAL ≠ APPROVED`**: An optimal solver outcome means the objective function was maximized subject to the modeled mathematical constraints. It does not replace operational judgment.
- **`FEASIBLE ≠ APPROVED`**: A feasible placement is one that does not violate encoded constraints. It is not an authorized maintenance block.
- **`VALID ≠ APPROVED`**: Certification by the independent validator proves that zero hard safety or domain invariants were violated in the model. Approval remains a separate, human action.
- **`APPROVABLE ≠ APPROVED`**: A plan marked `is_approvable = True` meets all preconditions to enter the formal review workflow. It is eligible for approval, not approved.
- **`AI EXPLAINS ≠ AI APPROVES`**: The AI Copilot is strictly read-only and assists human operators by providing grounded causal explanations and diagnostics. It has zero mutation privileges and cannot approve, reject, or modify schedules.
- **`CREATOR ≠ APPROVER`**: A maintenance planner who constructs or triggers a planning run is barred by database-level constraints from approving the resulting plan candidate (Four-Eyes Principle).

---

## 3. System Architecture

TrackMeld enforces strict separation between domain data assembly, mathematical optimization, independent safety validation, state machine governance, and user interaction.

### End-to-End Operational Pipeline

```mermaid
flowchart LR
    subgraph Ingestion["1. Snapshot Assembly"]
        A[Corridor Scenario] --> B[Planning Snapshot]
        B --> C[Canonical SHA-256 Hash]
    end

    subgraph Resolution["2. Topology & Routing"]
        B --> D[Deterministic Router]
        D --> E[Track-Resolved Traversals]
    end

    subgraph Optimization["3. CP-SAT Engine"]
        E --> F[Discrete Interval Model]
        C --> F
        F --> G[OR-Tools CP-SAT Solver]
        G --> H[Schedule Result]
    end

    subgraph Verification["4. Independent Audit"]
        H --> I[Independent Validator]
        B --> I
        I --> J{Valid & Approvable?}
    end

    subgraph Governance["5. Four-Eyes Governance"]
        J -- Yes --> K[Plan Version Candidate]
        K --> L[Operational Review]
        L --> M[Four-Eyes Approval]
        M --> N[(Immutable Audit Ledger)]
        J -- No --> O[Diagnostics & Root-Cause]
    end

    subgraph Explanation["6. Read-Only Copilot"]
        H -. Grounded Tools .-> P[AI Copilot Engine]
        I -. Diagnostic Evidence .-> P
        P -. Explanations .-> L
    end
```

### Detailed Layered Architecture

```mermaid
flowchart TD
    subgraph DataLayer["Data & Persistence Layer (PostgreSQL 18)"]
        direction TB
        DB_SCEN["Scenarios & Corridors (NDLS-GZB-ALJN)"]
        DB_TRACK["Physical Tracks (132 Tracks, 264 Endpoints)"]
        DB_TOPO["Topology Graph (Nodes & Turnout Connections)"]
        DB_TIME["Train Timetables & Commercial Services"]
        DB_TASK["Maintenance Work Orders & Tasks"]
        DB_RUN["Planning Runs (State Machine & History)"]
        DB_PLAN["Plan Versions & Review Commentary"]
        DB_AUDIT["Governance Audit Ledger (Append-Only)"]
    end

    subgraph CoreEngine["Deterministic Engine Pipeline (Python 3.11+)"]
        direction TB
        SNAP["PlanningSnapshot (Frozen In-Memory Dataclass)"]
        HASH["Authoritative SHA-256 Content Fingerprint"]
        ROUTER["DeterministicTopologyRouter (Graph Traversal)"]
        CPSAT_BUILDER["CPSATModelBuilder (Optional Intervals & Envelopes)"]
        CPSAT_SOLVER["CPSATSolver (Bounded Google OR-Tools)"]
        VALIDATOR["IndependentScheduleValidator (13 Check Categories)"]
        DIAGNOSTICS["UnscheduledTaskDiagnostics & RelaxationAnalyzer"]
    end

    subgraph ServiceLayer["Service & Worker Layer (FastAPI Async)"]
        direction TB
        WORKER["PlanningRunWorker (FOR UPDATE SKIP LOCKED)"]
        THREAD_POOL["Solver Thread Pool (asyncio.to_thread)"]
        GOV_SVC["PlanGovernanceService (State Machine & RBAC)"]
        COPILOT_ENG["CopilotEngine (Read-Only Guardrails)"]
        REST_API["FastAPI REST Endpoints (/api/v1)"]
    end

    subgraph PresentationLayer["Operational Workstation (Next.js 16 + React 19)"]
        direction TB
        UI_DASH["Planning Dashboard & Metric KPI Cards"]
        UI_TS["Multi-Track Time-Space Conflict Canvas"]
        UI_REVIEW["Four-Eyes Review & Promotion Drawer"]
        UI_COPILOT["Grounded AI Copilot Assistant Drawer"]
        UI_MAP["Infrastructure GIS & Track Topology View"]
    end

    DataLayer --> SNAP
    SNAP --> HASH
    SNAP --> ROUTER
    ROUTER --> CPSAT_BUILDER
    CPSAT_BUILDER --> CPSAT_SOLVER
    CPSAT_SOLVER --> VALIDATOR
    VALIDATOR --> GOV_SVC
    CPSAT_SOLVER --> DIAGNOSTICS

    REST_API --> WORKER
    WORKER --> THREAD_POOL
    THREAD_POOL --> CPSAT_SOLVER
    GOV_SVC --> DataLayer
    REST_API --> COPILOT_ENG
    COPILOT_ENG -. Read-Only .-> DataLayer

    REST_API <== HTTP/JSON ==> PresentationLayer
```

---

## 4. Domain Model

TrackMeld's domain models reflect physical railway operational entities and their spatial-temporal relationships:

| Domain Entity | Module | Description & Operational Purpose |
|---|---|---|
| **`Scenario`** | `domain.scenarios` | Planning study scope defining the geographical corridor, planning horizon (`start` to `end`), and operational assumptions. |
| **`BlockSection`** | `domain.sections` | Running line segment between two block stations. Defines nominal length (km), electrification status, and speed limits. |
| **`Track`** | `domain.infrastructure` | First-class physical track within a section (`UP_MAIN`, `DOWN_MAIN`, `LOOP`). Carries assigned direction and adjacent track relationships. |
| **`TopologyNode`** | `domain.topology` | Physical junction point (boundary joint, station throat, crossover junction) connecting track endpoints. |
| **`TrackEndpoint`** | `domain.topology` | Start or end boundary termination of a physical track segment (`START` or `END`). |
| **`TopologyConnection`** | `domain.topology` | Physical rail link between endpoints (`CONTINUITY`, `TURNOUT_NORMAL`, `TURNOUT_REVERSE`, `CROSSOVER`) with traversal direction permissions. |
| **`MaintenanceTask`** | `domain.maintenance_tasks` | Individual work activity requiring a track possession. Specifies department, duration, work window, buffers, track, and direction. |
| **`WorkOrder`** | `domain.work_orders` | Administrative container grouping related maintenance tasks for a specific track renewal or repair project. |
| **`TrainMovement`** | `domain.movements` | Timetable event representing a train arrival, departure, or pass-through at a specific station or block section boundary. |
| **`TrainPass`** | `domain.temporal` | Derived continuous temporal interval during which a train occupies a specific block section between adjacent stations. |
| **`TrainTraversal`** | `domain.temporal` | Physical route expansion resolving a `TrainPass` down to an explicit track assignment (`traversal_track_id`) via topology routing. |
| **`PlanningSnapshot`** | `domain.planning_snapshot` | Frozen, immutable data container grouping all inputs for a scenario, sealed with a 64-character SHA-256 fingerprint. |
| **`PlanningRun`** | `db.models.planning_run` | Asynchronous execution record tracking the solver lifecycle, configuration parameters, and schedule result. |
| **`PlanVersion`** | `db.models.plan_version` | Human-reviewable candidate plan derived from a completed, certified planning run. Governed by a strict state machine. |
| **`GovernanceAuditEvent`** | `db.models.plan_version` | Tamper-evident append-only ledger record documenting every state transition, actor identity, timestamp, and justification. |

---

## 5. Deterministic Planning Snapshots

To guarantee auditability and repeatability, TrackMeld enforces a strict architectural boundary: **The optimization engine never queries mutating database tables directly.**

Instead, all scenario inputs are loaded into an immutable `PlanningSnapshot` dataclass:
1. **Canonical Sorting**: Tasks are deterministically sorted by `task_id`. Resources, dependencies, and rules are mapped to indexed lookups.
2. **Derived Train Passes**: Timetable entries are translated into continuous section occupancy intervals via `CompatibilityEngine.derive_train_passes`.
3. **Physical Traversal Expansion**: Train passes are expanded into track-assigned `TrainTraversal` records via `DeterministicTopologyRouter`.
4. **Authoritative SHA-256 Fingerprint**: A 64-character hash is computed over the scenario bounds, canonical task records (task ID, allowed window, duration, section), and item counts.
5. **Configuration Hash**: An extended input fingerprint incorporates the snapshot hash, solver configuration parameters, and random seed.

```python
# Guaranteed Invariant: Identical snapshot inputs always produce identical fingerprints
snapshot_a = PlanningSnapshot.from_bundle(bundle_a)
snapshot_b = PlanningSnapshot.from_bundle(bundle_b_permuted)
assert snapshot_a.compute_snapshot_hash() == snapshot_b.compute_snapshot_hash()
```

---

## 6. CP-SAT Optimization Engine

TrackMeld models maintenance possession scheduling as an exact discrete constraint programming problem using **Google OR-Tools CP-SAT** (`ortools.sat.python.cp_model`).

### Mathematical Formulation

- **Time Discretization**: Continuous time across the planning horizon is mapped to integer minutes starting at `horizon_start = 0`.
- **Optional Interval Variables**: Each task $i$ is modeled as an optional interval variable with a presence boolean variable $p_i \in \{0, 1\}$:
  $$\text{task\_interval}_i = \text{NewOptionalIntervalVar}(\text{start}_i, \text{duration}_i, \text{end}_i, p_i)$$
- **Allowed Execution Window**: Task bounds are constrained to lie strictly inside the allowed window $[W_{\text{start}, i}, W_{\text{end}, i}]$:
  $$W_{\text{start}, i} \le \text{start}_i \le W_{\text{end}, i} - \text{duration}_i$$
- **Possession Envelopes**: Safety buffers before and after physical work are modeled as enclosing possession intervals:
  $$\text{pos\_start}_i = \text{start}_i - \text{buffer\_before}_i, \quad \text{pos\_end}_i = \text{end}_i + \text{buffer\_after}_i$$
- **Disjunctive Section Occupancy**: For any section $S$, no two possession intervals or train passes may overlap:
  $$\text{AddNoOverlap}(\{\text{pos\_interval}_i \mid i \in \text{Tasks}_S\} \cup \{\text{train\_interval}_k \mid k \in \text{Trains}_S\})$$
- **Resource Constraints**: Specialized machinery and certified gangs are bounded by disjunctive or cumulative capacity constraints across their assigned tasks.
- **Task Precedence**: Sequential dependency constraints ($i \to j$) enforce:
  $$\text{start}_j \ge \text{end}_i$$
- **Mandatory Tasks**: High-priority statutory tasks cannot be dropped:
  $$p_i = 1 \quad \forall i \in \text{MandatoryTasks}$$
- **Objective Function**: Maximizes the total priority score of scheduled tasks with a secondary penalty for excessive durations to encourage tight packing:
  $$\max \sum_{i} \left( p_i \cdot \text{PriorityScore}_i \cdot 1000 \right) - \sum_{i} \left( \text{duration}_i \cdot \text{duration\_penalty\_weight} \right)$$

### Solver Configuration & Control

Bounded execution is configured through `OptimizationConfig`:
- `time_limit_seconds`: Hard wall-clock limit (default: 30.0s, maximum: 300.0s).
- `num_search_workers`: Default `1` for deterministic single-threaded repeatability; configurable up to 16.
- `random_seed`: Fixed deterministic integer seed (default: `0`).
- `solver_mode`: `TRACK_AWARE_CONSERVATIVE` (default) or `WHOLE_SECTION` fallback.

The engine explicitly maps OR-Tools return codes to domain statuses: `OPTIMAL`, `FEASIBLE`, `INFEASIBLE`, `UNKNOWN` (timeout), `INVALID_INPUT`, or `FAILED`.

---

## 7. Track-Aware Spatial Planning

Earlier scheduling baselines locked an entire block section whenever maintenance was scheduled. TrackMeld implements **Track-Aware Conservative Optimization**:

```
WHOLE-SECTION OCCUPANCY (Coarse Baseline)
[ SECTION NDLS-GZB: Blocked by Task A ────────────────────────────────────────── ]
  UP MAIN:   [ BLOCKED by Task A ]
  DOWN MAIN: [ BLOCKED (Unusable despite being physically intact) ]

TRACK-AWARE CONSERVATIVE (TrackMeld Mode)
  UP MAIN:   [ Task A: Tamping Machine (Possession Window) ─────────────────── ]
  DOWN MAIN: [ Commercial Train Pass (Operating under Caution Order) ───────── ]
```

### Spatial Safety Semantics

1. **Physical Track Identity**: Tasks and train passes associate with explicit tracks within a section (`UP_MAIN`, `DOWN_MAIN`, `LOOP`).
2. **Direction Alignment**: Enforces unidirectional line safety. Tasks or train movements whose travel direction opposes track design (`UP` on a `DOWN` track) are rejected as infeasible.
3. **Adjacent Track Impact Classification**:
   - `NONE`: Work is contained within track clearances. Parallel lines operate normally.
   - `CAUTION_ORDER`: Work poses proximity hazards (e.g., ballast profiling). Adjacent running lines permit train movements under speed restrictions.
   - `FULL_TRAFFIC_BLOCK`: Heavy crane slewing or overhead bridge demolition requires simultaneous total possession of adjacent tracks.
4. **Conservative Fallback**: If track metadata is missing, incomplete, or marked `UNRESOLVED`, the optimizer automatically degrades to whole-section reservation. **Safety is never compromised for throughput.**

---

## 8. Spatial Infrastructure & Topology Model

TrackMeld represents railway infrastructure at a meso-level topology graph rather than a flat list of station names:

```
[STN-NDLS]                                                                     [STN-GZB]
  Endpoint-01 (START) ─── TRK-NDLS-GZB-UP (UP MAIN) ─── Endpoint-02 (END) ──┐
                                                                            ├── Node-GZB-THROAT ── (Continuity)
  Endpoint-03 (START) ─── TRK-NDLS-GZB-DN (DOWN MAIN) ── Endpoint-04 (END) ──┘
```

- **`TrackEndpoint`**: Explicit start and end boundary interfaces for each running line.
- **`TopologyNode`**: Boundary joints, station throats, and crossover junctions.
- **`TopologyConnection`**: Physical turnouts and crossovers with explicit connection types (`CONTINUITY`, `TURNOUT_NORMAL`, `TURNOUT_REVERSE`, `CROSSOVER`) and directional permissions (`FORWARD`, `REVERSE`, `BIDIRECTIONAL`).
- **Chainage Positioning**: Station and worksite locations are indexed using physical kilometre markers (`kilometrage_start`, `kilometrage_end`).

### Deterministic Topology Routing

The `DeterministicTopologyRouter` resolves commercial train passes into physical track-level traversals:
- Consumes **strictly explicit topology**. Zero connectivity is guessed or inferred from station adjacency, section ordering, or naming patterns.
- If multiple valid physical paths exist through topology without authoritative priority, the router marks the route as `AMBIGUOUS_ROUTE` and **refuses to fabricate a track assignment**.
- Unresolved routes safely fall back to section-level handling.

---

## 9. Train Traversal Model

Understanding TrackMeld requires distinguishing three distinct train representations:

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│  TrainMovement  │  ──►  │    TrainPass    │  ──►  │  TrainTraversal │
│ (Timetable Log) │       │ (Section Level) │       │  (Track Level)  │
└─────────────────┘       └─────────────────┘       └─────────────────┘
```

1. **`TrainMovement`**: Represents commercial timetable stop or passing events at specific stations (e.g., Train 12004 departs NDLS at 06:10, arrives GZB at 06:42).
2. **`TrainPass`**: Synthesized continuous temporal interval during which a train occupies a specific block section (e.g., Train 12004 occupies section `SEC-NDLS-GZB` from 06:10 to 06:42 UTC).
3. **`TrainTraversal`**: Physically grounded hop tracing the exact track (`traversal_track_id`) traversed through topology connections, verified for directional alignment.

---

## 10. Independent Schedule Validation

The **`IndependentScheduleValidator`** is an isolated safety auditor. It executes after the solver and **does not share solver memory, constraints, or heuristics**. It inspects the generated schedule against the raw `PlanningSnapshot` across **13 independent check categories**:

```mermaid
flowchart TD
    Schedule[Schedule Result] --> Runner[ScheduleCheckRunner]
    Snapshot[Planning Snapshot] --> Runner

    Runner --> C1[1. STRUCTURAL: Task existence, intervals, unique placement]
    Runner --> C2[2. HORIZON: Bounds inside planning window]
    Runner --> C3[3. TASK_WINDOW: Placement inside allowed work window]
    Runner --> C4[4. DURATION_AND_BUFFERS: Duration match & buffer integrity]
    Runner --> C5[5. SECTION_OCCUPANCY: Half-open interval section exclusivity]
    Runner --> C6[6. MULTI_SECTION: Multi-block corridor consistency]
    Runner --> C7[7. TRAIN_MOVEMENT: Zero conflict with scheduled train passes]
    Runner --> C8[8. TRACK_SPATIAL_SAFETY: Direction, same-track, adjacent blocks]
    Runner --> C9[9. RESOURCES: No overlapping crew or fleet commitments]
    Runner --> C10[10. DEPENDENCIES: Predecessor finish <= Successor start]
    Runner --> C11[11. MANDATORY_TASKS: 100% presence of mandatory work]
    Runner --> C12[12. DOMAIN_RULES: Statutory railway rule adherence]
    Runner --> C13[13. SOLVER_OUTPUT_SANITY: Metric and status consistency]

    C1 & C2 & C3 & C4 & C5 & C6 & C7 & C8 & C9 & C10 & C11 & C12 & C13 --> Gate{Any ERROR Findings?}
    Gate -- Yes --> Blocked[is_approvable = FALSE: Approval Gate BLOCKED]
    Gate -- No --> Certified[is_approvable = TRUE: Certified Valid Candidate]
```

### Cryptographic Schedule Identity Fingerprint

The validator computes an independent 64-character SHA-256 fingerprint over the identity-bearing decisions of the schedule:
- Canonical task placements (sorted `task_id`, work start/end, possession start/end, sections, assigned resources).
- Unscheduled task IDs.
- Scenario ID and snapshot ID.
- Solver termination status.

Telemetric fields (solve runtime, optimality gap, priority breakdowns) are explicitly excluded from the fingerprint, ensuring that schedule identity reflects purely operational decisions.

---

## 11. Root-Cause Diagnostics & Relaxation Analysis

When tasks cannot be scheduled, TrackMeld runs causal diagnostics (`UnscheduledTaskDiagnosticsService`) to determine why:
- Categorizes blockers: `TRAIN_MOVEMENT_CONFLICT`, `SECTION_OCCUPANCY_CONFLICT`, `RESOURCE_UNAVAILABLE`, `DEPENDENCY_NOT_SATISFIED`, or `WINDOW_TOO_TIGHT`.
- Identifies exact conflicting train numbers, competing task IDs, or unavailable machinery.

### Hypothetical Relaxation Analysis

To assist maintenance engineers in negotiating track blocks, the `RelaxationAnalyzer` evaluates 5 controlled relaxation scenarios:
1. `IGNORE_TRAIN_CONFLICTS`: Tests if the task would fit if train paths were rescheduled.
2. `IGNORE_SECTION_OCCUPANCY`: Tests if the blocker is competing maintenance.
3. `IGNORE_RESOURCE_AVAILABILITY`: Tests if acquiring additional machinery would resolve contention.
4. `IGNORE_DEPENDENCIES`: Tests if predecessor delays are the sole blocker.
5. `WIDEN_TASK_WINDOW`: Tests if widening the work window by $\pm 2$ hours yields feasibility.

> **CRITICAL SAFETY INVARIANT**: Relaxation analysis is **purely diagnostic**. It evaluates hypothetical possibilities to explain infeasibility. It **NEVER** alters production schedules and explicitly flags all relaxation placements as unapprovable.

---

## 12. Planning Jobs & Asynchronous Execution

Planning runs execute asynchronously to prevent long-running solver calculations from blocking web APIs.

### Job Worker Architecture (`PlanningRunWorker`)

- **State Lifecycle**: `PENDING` $\to$ `CLAIMED` $\to$ `SNAPSHOT_BUILT` $\to$ `OPTIMIZING` $\to$ `VALIDATING` $\to$ `COMPLETED` (or `FAILED` / `TIMED_OUT` / `CANCELLED`).
- **Atomic Job Claiming**: Uses PostgreSQL row-level locks via `SELECT ... FOR UPDATE SKIP LOCKED` to ensure a job is claimed by exactly one worker process.
- **Thread Pool Isolation**: Solvers execute in a dedicated worker thread via `asyncio.to_thread`, keeping the event loop responsive.
- **Durable Timeout Trapping**: Enforces an explicit 120-second timeout ceiling (`asyncio.wait_for`), safely terminating runaway solves and transitioning the run to `TIMED_OUT`.
- **Heartbeat & Zombie Recovery**: Workers emit heartbeats every 5 seconds. If a worker process dies unexpectedly, stale jobs (inactive $>30$s) are automatically reclaimed.

---

## 13. Human Governance & Four-Eyes Control

TrackMeld enforces strict administrative controls around candidate plan versions (`PlanGovernanceService`):

```mermaid
stateDiagram-v2
    [*] --> PENDING_REVIEW: create_plan_version_from_run()
    PENDING_REVIEW --> UNDER_REVIEW: start_review()
    UNDER_REVIEW --> UNDER_REVIEW: add_review_comment()
    UNDER_REVIEW --> APPROVED: approve_plan() [Four-Eyes Enforced]
    UNDER_REVIEW --> REJECTED: reject_plan() [Mandatory Rationale]
    APPROVED --> SUPERSEDED: When newer version is approved
    REJECTED --> [*]
    SUPERSEDED --> [*]
```

### Preconditions for Operational Approval

Before `approve_plan()` transitions a plan to `APPROVED`, all 7 preconditions must pass:
1. **Plan Exists & Row Locked**: Target plan version exists and is locked with `FOR UPDATE`.
2. **Not Already Approved**: Cannot re-approve an approved plan.
3. **Legal State Transition**: Must be in `UNDER_REVIEW` state.
4. **Certified Valid**: Run validation status must be `VALID` and `is_approvable == True`.
5. **Zero Errors**: Total validation `error_count == 0`.
6. **Cryptographic Identity Match**: Schedule fingerprint, snapshot hash, and input hash must match source run records bit-for-bit.
7. **Four-Eyes Segregation**: **`plan.created_by != actor.username`**. The user who triggered the planning run cannot approve the resulting plan. Operational approval requires independent human review.

### Immutable Audit Ledger

Every governance action appends an immutable `GovernanceAuditEvent` record capturing:
- Unique event ID and timestamp (UTC).
- Actor ID, username, and assigned role.
- Transition states (`previous_state` $\to$ `new_state`).
- Cryptographic schedule identity and snapshot hashes.
- Mandatory reviewer justification comments.

---

## 14. Security & Hardening

TrackMeld implements role-based access control and API-level defense-in-depth:

- **Role-Based Access Control (RBAC)**: Token-based Bearer authentication enforcing explicit permissions:
  - `ADMIN`: Full system management and worker configuration.
  - `MAINTENANCE_PLANNER`: Work order ingestion, planning run trigger, and commentary.
  - `OPERATOR` (Approver): Formal operational review, plan approval, and rejection.
  - `VIEWER`: Read-only access to corridors, timetables, and approved plans.
- **Fail-Closed Security**: In production mode (`ENVIRONMENT=production`), unauthenticated requests are strictly rejected with HTTP 401. Prototype environments fall back to a read-only viewer.
- **Governance Concurrency Protection**: Database row locks prevent approval/rejection race conditions.
- **Security Headers & Rate Limiting**: Production middleware enforces CSP, X-Frame-Options, HSTS, and route-level token bucket rate limits on heavy optimization endpoints.
- **Static Secret Scanning**: Automated test suites scan codebase and configuration to prevent credentials or private keys from entering source control.

---

## 15. AI Copilot (Read-Only & Grounded)

The TrackMeld Copilot provides intelligent decision-support and causal explanation for operational staff:

```
[Human Operator Query]
         │
         ▼
[Copilot Engine] ──► [Write Intent Check] ──► (Contains 'approve', 'modify', 'delete'?)
         │                                               │
         │ (Read-Only Verified)                          ▼ YES: HARD REFUSAL
         ▼                                      "Action Refusal: Strictly Read-Only"
[Typed Retrieval Tool]                           "Governance Boundary: COMPLETED ≠ APPROVED"
         │
         ▼
[Deterministic Database Evidence]
         │
         ▼
[Grounded Operational Explanation]
```

### Copilot Capabilities & Constraints

- **Mutation Refusal**: Pattern matches against write/approval intent (`approve`, `reject`, `modify`, `force override`). Immediately refuses with a governance reminder: *Copilot cannot approve plans or modify records.*
- **Typed Read-Only Tools**:
  - `get_task_decision`: Explains why a task was scheduled at a specific time or why it was left unplaced.
  - `get_conflicts_for_task`: Retrieves blocking train numbers and competing maintenance tasks.
  - `get_run_summary`: Summarizes solve performance, completion rates, and validation findings.
  - `get_rule_provenance`: Cites statutory railway manual clauses and verification status.
  - `get_plan_version_status`: Reports review and four-eyes approval status.
- **Uncertainty Reporting**: If an entity does not exist, the Copilot reports uncertainty rather than hallucinating details.
- **Core Operating Rule**: **AI Explains, Humans Decide.**

---

## 16. Frontend Planning Workstation

Built with **Next.js 16 (App Router + Turbopack)**, React 19, TypeScript 5, and Tailwind CSS.

### Workstation Interface Highlights

- **Multi-Track Time-Space Canvas**: Interactive distance-versus-time graph plotting train movements as continuous sloped trajectory lines and maintenance possessions as shaded spatial blocks across distinct running tracks (`UP`, `DOWN`).
- **Synchronized Viewports**: Interactive filtering by block section, date range, department, and priority.
- **Truthful Status Indicators**: Clear visual separation between engine states:
  - `CP-SAT (TRACK-AWARE)` / `CP-SAT (WHOLE-SECTION)`: Solver execution mode.
  - `VALID (Automated)`: Automated 13-category certification.
  - `APPROVED (Human Operator)`: Formal four-eyes human operational authorization.
  - `SYNTHETIC`: Prominent warning badge indicating demo data environment.
- **Governance Drawer**: Allows authorized approvers to review validation reports, inspect audit trails, input required operational rationale, and execute approvals.
- **Copilot Drawer**: Embedded conversational pane for grounded decision support.

---

## 17. Synthetic Data Boundary

TrackMeld is configured with synthetic demonstration datasets designed to replicate real-world operational complexity while remaining safely decoupled from live railway systems:

- **Curated Demonstration Corridor**: 3 contiguous block sections between New Delhi, Ghaziabad, and Aligarh Junction (`NDLS-GZB-ALJN`) representing 132 tracks, 264 endpoints, 2 topology nodes, and 5 topology connections.
- **Synthetic Timetables**: Passenger and freight train patterns modeled after Indian Railways operational patterns, marked with `SYNTHETIC_PATTERN` provenance.
- **Demonstration Provenance**: All corridor topology, station names, train numbers, and maintenance schedules bundled with this repository are synthetic demo datasets created for reproducibility. TrackMeld does **not** interface with CRIS, COA, TMS, or live signalling systems.

---

## 18. Verified API Reference

The FastAPI backend exposes typed REST endpoints documented with OpenAPI at `/docs`:

| Method | Endpoint | Description | Required Role |
|---|---|---|---|
| `GET` | `/api/v1/scenarios` | List operational planning scenarios | `VIEWER` |
| `GET` | `/api/v1/corridors` | List railway corridors and route definitions | `VIEWER` |
| `GET` | `/api/v1/sections` | List block sections with chainage and track counts | `VIEWER` |
| `GET` | `/api/v1/tracks` | List physical running tracks with direction metadata | `VIEWER` |
| `GET` | `/api/v1/topology/nodes` | Query topology junction and throat nodes | `VIEWER` |
| `GET` | `/api/v1/topology/connections` | Query physical rail turnout and crossover connections | `VIEWER` |
| `GET` | `/api/v1/work-orders` | List maintenance work orders | `VIEWER` |
| `GET` | `/api/v1/tasks` | List maintenance task requisitions | `VIEWER` |
| `GET` | `/api/v1/trains` | List commercial train services | `VIEWER` |
| `GET` | `/api/v1/movements` | Query train movements and station stop events | `VIEWER` |
| `POST` | `/api/v1/compatibility/evaluate-task` | Deterministically evaluate single-task feasibility | `VIEWER` |
| `POST` | `/api/v1/planning/baseline` | Execute FCFS or Priority-Greedy baseline scheduler | `PLANNER` |
| `POST` | `/api/v1/planning/benchmark` | Compare baselines on identical snapshot | `PLANNER` |
| `POST` | `/api/v1/planning/optimize` | Synchronous direct CP-SAT solve (debug/test) | `PLANNER` |
| `POST` | `/api/v1/planning-runs` | Submit asynchronous CP-SAT planning job | `PLANNER` |
| `GET` | `/api/v1/planning-runs/{run_id}` | Query planning job lifecycle progress and stage | `VIEWER` |
| `GET` | `/api/v1/planning-runs/{run_id}/result` | Retrieve finalized ScheduleResult and certificates | `VIEWER` |
| `POST` | `/api/v1/planning-runs/{run_id}/cancel` | Request cooperative cancellation of running job | `PLANNER` |
| `POST` | `/api/v1/plan-versions` | Instantiate candidate PlanVersion from certified run | `PLANNER` |
| `GET` | `/api/v1/plan-versions/{plan_version_id}` | Inspect plan details, schedule, and review history | `VIEWER` |
| `POST` | `/api/v1/plan-versions/{plan_version_id}/review` | Transition candidate plan to `UNDER_REVIEW` | `OPERATOR` |
| `POST` | `/api/v1/plan-versions/{plan_version_id}/comments` | Attach human reviewer commentary entry | `PLANNER` |
| `POST` | `/api/v1/plan-versions/{plan_version_id}/approve` | Formally approve plan (Four-Eyes enforced) | `OPERATOR` |
| `POST` | `/api/v1/plan-versions/{plan_version_id}/reject` | Formally reject plan with mandatory rationale | `OPERATOR` |
| `GET` | `/api/v1/plan-versions/{plan_version_id}/audit` | Retrieve immutable append-only governance audit log | `VIEWER` |
| `POST` | `/api/v1/copilot/explain` | Submit inquiry to read-only AI decision-support Copilot | `VIEWER` |
| `GET` | `/api/v1/copilot/tools` | Inspect specifications of read-only Copilot tools | `VIEWER` |

---

## 19. Project Structure

```text
TrackMeld/
├── backend/
│   ├── alembic/                    # Database schema migrations (001 through 012)
│   │   └── versions/               # Production-hardened migration scripts
│   ├── app/
│   │   ├── api/v1/                 # FastAPI typed REST route controllers
│   │   ├── core/                   # Security, Bearer RBAC, rate-limiting
│   │   ├── db/                     # SQLAlchemy models, sessions, base classes
│   │   ├── domain/                 # Pure domain models, enums, temporal logic
│   │   ├── repositories/           # Database access repositories
│   │   ├── schemas/                # Pydantic request/response validation schemas
│   │   ├── services/
│   │   │   ├── copilot/            # Read-only grounded AI Copilot engine & tools
│   │   │   ├── optimization/       # CP-SAT model builder, solver, diagnostics
│   │   │   ├── schedulers/         # FCFS and Priority-Greedy baseline schedulers
│   │   │   ├── validation/         # 13-category validator & relaxation analyzer
│   │   │   ├── planning_worker.py  # Asynchronous background job daemon
│   │   │   ├── plan_governance_service.py # Four-Eyes state machine & audit log
│   │   │   └── topology_routing.py # Deterministic physical route resolver
│   │   ├── config.py               # Pydantic BaseSettings environment loader
│   │   ├── main.py                 # FastAPI application factory & middleware
│   │   └── worker.py               # Standalone worker daemon entrypoint
│   └── requirements.txt            # Python backend dependencies
├── frontend/
│   ├── e2e/                        # Playwright full-stack browser E2E test specs
│   ├── src/
│   │   ├── app/                    # Next.js 16 App Router (workspaces, review)
│   │   ├── components/             # Time-space canvas, GIS, review drawer, Copilot
│   │   ├── hooks/                  # Custom React query and mutation hooks
│   │   └── lib/api/                # Typed REST client with RBAC auth token handling
│   ├── package.json                # Frontend dependencies (React 19, Tailwind)
│   ├── playwright.config.ts        # Playwright E2E configuration & webServer
│   └── tsconfig.json               # TypeScript strict configuration
├── docs/                           # Architecture specifications & system contracts
│   ├── archive/                    # Archived historical phase implementation reports (1–21)
│   ├── TRACKMELD_FINAL_ARCHITECTURE.md # Comprehensive system architecture reference
│   └── DATA_CONTRACTS.md           # Domain schemas & operational data contracts
├── tests/
│   ├── conftest.py                 # Shared test fixtures & async session wiring
│   ├── integration/                # 148 API, database, and governance integration tests
│   └── unit/                       # 310 discrete mathematical solver & domain unit tests
├── .env.example                    # Environment variable configuration template
├── LICENSE                         # MIT License
└── README.md                       # Root system documentation & portfolio reference
```

---

## 20. Quick Start & Local Development

### Prerequisites

- **Python**: Version 3.11 or higher
- **PostgreSQL**: Version 18 or higher (running locally or in a container)
- **Node.js**: Version 20 or higher with `npm`

### 1. Repository Setup & Environment

```bash
git clone https://github.com/sanskarchourasiya445/trackmeld.git
cd Trackmeld

# Copy environment configuration
cp .env.example .env
```

Edit `.env` to match your local PostgreSQL cluster connection:
```ini
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/trackmeld
DATABASE_URL_SYNC=postgresql+psycopg2://postgres:postgres@localhost:5433/trackmeld
```

### 2. Backend Installation & Database Migration

```bash
# Set up Python virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Run all 12 Alembic migrations to build schema
cd backend
alembic upgrade head
cd ..

# Seed synthetic corridor data (NDLS-GZB-ALJN demo scenario)
python -m backend.app.cli.seed
```

### 3. Start Backend Services

In two separate terminals:

```bash
# Terminal 1: Background planning job worker
python -m backend.app.worker

# Terminal 2: FastAPI application server
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
Interactive API documentation will be available at `http://127.0.0.1:8000/docs`.

### 4. Frontend Workstation Setup

In a third terminal:

```bash
cd frontend
npm install
npm run dev
```
The operational workstation will be running at `http://localhost:3000`.

### 5. Running Automated Verification Suites

```bash
# Run 310 backend unit tests (CP-SAT model, validator checks, router, snapshots)
pytest tests/unit/ -v

# Run 148 backend integration tests (requires running PostgreSQL instance)
pytest tests/integration/ -v

# Run 14 Playwright browser E2E tests (requires running backend & frontend)
cd frontend
npx playwright test
```

---

## 21. Configuration Reference

All settings are managed via `backend/app/config.py` using Pydantic `BaseSettings`:

| Environment Variable | Default Value | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://...@localhost:5433/trackmeld` | Async database URI for FastAPI async sessions |
| `DATABASE_URL_SYNC` | `postgresql+psycopg2://...@localhost:5433/trackmeld` | Synchronous database URI for Alembic migrations |
| `ENVIRONMENT` | `development` | Runtime environment (`development` or `production`) |
| `LOG_LEVEL` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `APP_HOST` | `127.0.0.1` | REST API bind address |
| `APP_PORT` | `8000` | REST API port |
| `TIMEZONE` | `Asia/Kolkata` | Canonical planning display timezone |
| `ALLOWED_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | CORS permitted origins |
| `WORKER_POLL_INTERVAL_SECONDS` | `1.0` | Job queue polling interval for idle workers |
| `WORKER_HEARTBEAT_INTERVAL_SECONDS` | `5.0` | Worker active heartbeat write interval |
| `WORKER_STALE_TIMEOUT_SECONDS` | `30.0` | Inactivity threshold before reclaiming zombie jobs |
| `PLANNING_JOB_TIMEOUT_SECONDS` | `120.0` | Maximum solver wall-clock limit before timeout trapping |
| `AUTH_ADMIN_TOKEN` | `demo-admin-token` | Bearer token for `ADMIN` role operations |
| `AUTH_APPROVER_TOKEN` | `demo-approver-token` | Bearer token for `OPERATOR` review & approval |
| `AUTH_PLANNER_TOKEN` | `demo-planner-token` | Bearer token for `MAINTENANCE_PLANNER` mutations |
| `AUTH_VIEWER_TOKEN` | `demo-viewer-token` | Bearer token for read-only `VIEWER` access |

---

## 22. Testing & Final Verification

TrackMeld's Phase 21 release verification established complete test coverage across all architectural tiers:

```
================================= TEST VERIFICATION SUMMARY =================================
Suite                              Count    Status    Execution Context
─────────────────────────────────────────────────────────────────────────────────────────────
Backend Unit Tests                   310    PASSED    Discrete CP-SAT, Validator, Snapshots, Routing
Backend Integration & API Tests      148    PASSED    PostgreSQL 18 Migrations, RBAC, Governance
Playwright Browser E2E Journeys       14    PASSED    Full Stack (Chromium, Firefox, WebKit)
─────────────────────────────────────────────────────────────────────────────────────────────
Total Automated Test Suite           472    PASSED    Zero regressions, zero skipped

Static Type Analysis (TSC)             0    CLEAN     TypeScript 5.x strict mode
Code Quality & Linting (ESLint)        0    CLEAN     Next.js / React hooks recommended
=============================================================================================
```

*Note: The 310 unit tests execute independently of external databases. The 148 integration tests and 14 Playwright E2E tests require an active PostgreSQL 18 instance and running services.*

---

## 23. Benchmark Performance Reference

The following performance profile was measured on the `SCN-DEMO-001` synthetic corridor benchmark in the Phase 21 verification environment:

| Benchmark Pipeline Stage | Measured Latency | Operational Activity |
|---|---|---|
| **Bundle Ingestion & Parse** | $\approx 367.8\text{ ms}$ | Loading scenario records, tracks, timetable passes, and work orders |
| **Planning Snapshot Assembly** | $\approx 4.7\text{ ms}$ | Canonical sorting, traversal expansion, and SHA-256 fingerprinting |
| **CP-SAT Mathematical Solve** | $\approx 20.0\text{ ms}$ | OR-Tools discrete interval search, yielding `OPTIMAL` (29/30 tasks scheduled) |
| **Independent Validation Audit** | $\approx 2.1\text{ ms}$ | Recomputing all 13 check categories across raw snapshot data (`VALID`) |
| **Typical API Endpoint Response** | $< 45\text{ ms}$ | P95 REST latency across corridor, track, and run detail queries |

> *Notice: These figures reflect performance on the curated demonstration corridor in the Phase 21 benchmark environment. They are scenario- and hardware-specific and do not constitute universal production SLAs.*

---

## 24. Key Engineering Decisions & Trade-offs

1. **Deterministic Snapshots over Live Queries**: Optimization against live mutating database tables leads to unreproducible race conditions. Assembling an immutable, fingerprinted snapshot guarantees that schedules can be verified and re-solved bit-for-bit.
2. **CP-SAT over Greedy Heuristics**: Greedy schedulers make early suboptimal decisions that strand high-priority tasks. CP-SAT searches globally across the constraint graph, maximizing priority capture while proving feasibility.
3. **Independent Validator over Solver Self-Trust**: Solvers are complex and may contain modeling bugs or subtle formulation relaxations. An isolated validator that re-evaluates raw snapshot data ensures that a bug in the model builder cannot result in an invalid schedule being certified.
4. **Enforced Four-Eyes Governance over Automation**: No algorithm or AI system possesses the operational context, legal responsibility, or safety mandate to approve railway possessions. The system enforces `CREATOR ≠ APPROVER` at the database level.
5. **Conservative Spatial Fallback**: Full track-circuit interlocking is outside the scope of planning decision support. Where spatial data is complete, TrackMeld optimizes per-track; where data is incomplete, it safely falls back to whole-section reservation.
6. **Read-Only AI Copilot**: LLMs can hallucinate plausible-sounding routes or rules. By denying the Copilot all write permissions and grounding responses in typed tool queries, TrackMeld eliminates hallucinated approvals.

---

## 25. System Boundaries

TrackMeld maintains strict operational boundaries:

### What TrackMeld Controls
- Mathematical possession scheduling and window allocation.
- Intersite safety buffer and duration calculation.
- Constraint feasibility and conflict diagnostics.
- Independent multi-category safety auditing.
- Multi-version plan review and four-eyes approval state machine.
- Grounded causal explanations and diagnostic evidence retrieval.

### What TrackMeld Does NOT Control
- Physical railway signals, aspects, or route locking.
- Points, switch machines, or physical interlocking.
- Live train dispatch, speed enforcement, or train describer systems.
- Autonomous operational execution or automatic plan sign-off.
- On-track personnel safety interlocks or physical red-band tags.

---

## 26. Prototype Limitations

TrackMeld is an advanced decision-support prototype. Transparent engineering requires stating its current limitations:

- **Synthetic Data**: All bundled corridor data, timetables, and work orders are synthetic demonstration datasets.
- **Curated Topology Coverage**: Explicit physical topology connections currently cover 3 demonstration sections between New Delhi, Ghaziabad, and Aligarh Junction (`NDLS-GZB-ALJN`). Other corridor sections operate under whole-section modeling.
- **No CENELEC / Safety Certification**: TrackMeld has not undergone CENELEC EN 50128 / EN 50129 software safety integrity certification. It must not be connected to live interlocking systems.
- **Experimental Priority Weights**: Priority scoring feature weights are heuristic parameters configured for demonstration purposes, not railway-calibrated operational policies.
- **Prototype Authentication**: RBAC token management uses bearer strings suitable for demonstration and local testing; production deployment requires integration with enterprise Identity Providers (OAuth2/OIDC/SAML).

---

## 27. Project Evolution (Phases 1–21)

TrackMeld was developed through a rigorous 21-phase evolutionary roadmap:

```
Foundation & Ingestion (Phases 1–3)
  └── PostgreSQL schema, Alembic migrations, typed FastAPI read endpoints
Deterministic Baselines & Compatibility (Phases 4–5)
  └── Section compatibility matrix, FCFS and Priority-Greedy comparative schedulers
CP-SAT Optimization & Validation (Phases 6–7)
  └── Google OR-Tools discrete interval model, 13-category independent validator
Asynchronous Persistence & Governance (Phases 8–10)
  └── Background job queue, snapshot hashing, Four-Eyes plan review state machine
Workstation UI & AI Copilot (Phases 11–15)
  └── Next.js 16 time-space diagram, read-only grounded Copilot, browser E2E test suite
Spatial Infrastructure & Topology (Phases 16–18)
  └── First-class track models, topology nodes/turnouts, deterministic route resolution
Track-Aware CP-SAT & Hardening (Phases 19–20)
  └── Multi-track optimization, adjacent caution orders, production compound indexes
Final Verification & Portfolio Release (Phase 21)
  └── Determinism stress testing, full E2E audit, complete 472-test sign-off
```

*Detailed milestone reports for every phase are preserved in [`docs/archive/README.md`](docs/archive/README.md).*

---

## 28. Documentation & Portfolio References

- **[System Architecture Reference](docs/TRACKMELD_FINAL_ARCHITECTURE.md)**: Deep dive into the mathematical formulation, topology graph structure, and state machine.
- **[Design System Specification](DESIGN_SYSTEM.md)**: Visual language, time-space graph standards, and dark-theme tokens.
- **[Data Contracts & Domain Specifications](docs/DATA_CONTRACTS.md)**: Schemas, operational responses, and event payloads.
- **[Historical Phase Archive](docs/archive/README.md)**: Complete archive of all 40+ implementation and audit reports across Phases 1–21.

---

## 29. License

TrackMeld is open-source software licensed under the **[MIT License](LICENSE)**.
