# Product Requirements Document — TrackMeld

**Version:** 1.0  
**Product stage:** SIH prototype / MVP  
**Status:** Proposed specification  
**Primary users:** Maintenance planners, operations planners, engineering/maintenance requesters, reviewers

## 1. Product summary

TrackMeld is a railway maintenance planning and decision-support prototype that helps planners coordinate maintenance tasks against railway topology, train occupancy, work windows, resource availability, and compatibility constraints. It produces candidate plans that can be compared, inspected, revised, and approved by a human.

TrackMeld is not an autonomous dispatcher and does not issue real railway blocks, power blocks, permits, or operational authorizations.

### Product principle

**Rules classify. Optimization schedules. Humans approve. AI explains.**

- Deterministic rules validate input and classify compatibility.
- Scheduling algorithms produce baseline plans.
- OR-Tools CP-SAT searches for an improved feasible plan under explicit constraints.
- An independent validator checks the returned plan.
- A human planner reviews and approves.
- An optional read-only AI Copilot explains facts returned by deterministic diagnostic tools.

## 2. Problem statement

Maintenance planning involves multiple competing requirements: where work occurs, when trains occupy a section, how long work takes, which resources are needed, which tasks may share a work window, and which requests should receive priority. Manual or fragmented planning can make it difficult to see conflicts and compare alternatives consistently.

TrackMeld aims to make these relationships visible and help produce explainable candidate schedules. The prototype must demonstrate this workflow with synthetic data and must not imply that it has access to internal railway systems.

## 3. Goals

1. Represent a small fictional railway corridor as stations, block sections, lines, train passes, and maintenance tasks.
2. Generate a reproducible synthetic dataset with explicit provenance.
3. Validate maintenance requests and derive candidate planning windows deterministically.
4. Produce at least two understandable baseline schedules: First-Come, First-Served (FCFS) and priority-greedy.
5. Use CP-SAT to generate a candidate schedule under modeled constraints.
6. Independently validate the solver output before presenting it as valid.
7. Explain scheduled/unscheduled decisions with deterministic reason codes and constraint evidence.
8. Compare baseline and optimized scenarios using transparent, computed metrics.
9. Support planner review, controlled edits, approval, versioning, and audit history.
10. Present the workflow in a polished, responsive operations workstation and landing page.

## 4. Non-goals

The MVP will not:
- Connect to internal Indian Railways, CRIS, COA, BDMS, TMS, TDMS, or SMMS systems.
- Control trains, dispatch movements, grant real blocks, issue PTW/disconnection permissions, or certify safety.
- Use fabricated train movements or synthetic values as if they were real.
- Claim operational benefits or percentage improvements without measured results.
- Use machine learning to predict railway failures.
- Add LangGraph, MCP, vector RAG, Kafka, Kubernetes, microservices, or a separate distributed platform without a demonstrated need.
- Perform network-wide optimization across real railway divisions.
- Treat an LLM response as a scheduling decision or safety authority.

## 5. Users and permissions

### Maintenance / Department Requester
- Create and edit draft maintenance requests.
- Specify location, duration, preferred window, department, resource needs, and operational requirements.
- View validation results and the disposition of their requests.
- Read reasons a task was not selected.

### Operations Planner
- Inspect train occupancy and modeled constraints.
- Generate baseline and optimized scenarios.
- Inspect conflicts and compare alternatives.
- Review candidate plan feasibility.

### Planning Approver
- Review validated plans and differences from earlier versions.
- Approve or reject a candidate plan within the prototype.
- Record a reason for a decision.
- View immutable plan versions and audit events.

### Administrator
- Manage demo users and roles.
- Manage synthetic corridor/configuration data.
- Inspect dataset provenance and scenario configuration.
- Change non-safety objective weights only through validated configuration.

For a local demo, authentication may initially use seeded demo accounts, but authorization must still be enforced in backend services. Never rely on hiding buttons in the frontend as the security boundary.

## 6. Primary workflow

1. Select a corridor and planning horizon.
2. Load or create maintenance requests.
3. Validate request fields and referenced sections/resources.
4. Derive allowed windows and train occupancy intervals.
5. Run deterministic compatibility checks and priority calculation.
6. Generate FCFS and priority-greedy baselines.
7. Run CP-SAT with a configurable time limit.
8. Independently validate every returned assignment and interval.
9. Generate diagnostics for scheduled, delayed, and unscheduled tasks.
10. Compare schedules using consistent metrics.
11. Inspect tasks, constraints, and reason codes in the planning UI.
12. Revise the scenario or pin selected decisions and rerun.
13. Approve a validated plan; persist a new immutable version and audit event.

The Copilot is an optional read-only sidecar to this workflow, not a required dependency for schedule generation.

## 7. Functional requirements

### Data and network
- **FR-001:** The system shall represent a fictional corridor with stations, block sections, track lines, and connectivity.
- **FR-002:** The system shall display a persistent `SYNTHETIC DEMONSTRATION DATA` label anywhere synthetic operational values are shown.
- **FR-003:** The system shall generate deterministic seed data from a configurable seed, defaulting to `42`.
- **FR-004:** Every generated dataset shall include generator version, seed, creation time, scenario identifier, and synthetic provenance.
- **FR-005:** The system shall validate foreign-key references, time ordering, interval durations, and required fields before planning.

### Maintenance requests and constraints
- **FR-006:** Users shall be able to list, filter, inspect, and create/edit draft maintenance tasks.
- **FR-007:** Each task shall identify a target section/line, department, duration, allowed window, status, resource requirements, and modeled operational requirements.
- **FR-008:** Compatibility shall be calculated by deterministic code and return stable reason codes.
- **FR-009:** Any railway-specific safety or operating rule shall include a source reference, clause, verification status, and reviewer metadata. Unverified rules shall be marked as assumptions and excluded from authoritative safety enforcement.
- **FR-010:** The system shall distinguish a hard feasibility constraint from a configurable optimization preference.

### Planning and optimization
- **FR-011:** The system shall generate an FCFS baseline.
- **FR-012:** The system shall generate a priority-greedy baseline.
- **FR-013:** The system shall run CP-SAT on a bounded planning horizon with a configurable solver time limit.
- **FR-014:** The system shall record solver status, elapsed time, objective/bound where available, and model/configuration version.
- **FR-015:** The system shall independently validate the solver output before marking it `VALIDATED`.
- **FR-016:** The system shall distinguish `OPTIMAL`, `FEASIBLE`, `INFEASIBLE`, `UNKNOWN`, `MODEL_INVALID`, and failed execution states where applicable.
- **FR-017:** A timeout with a feasible incumbent may return a candidate only if the solver status and independent validation are recorded accurately.
- **FR-018:** The system shall not claim that the optimal solution was found unless the solver reports that status.

### Diagnostics and comparison
- **FR-019:** The system shall record why each task was scheduled, delayed, or not scheduled using structured reason codes and relevant conflict references.
- **FR-020:** Diagnostics shall be generated from model/validator facts, not invented by the LLM.
- **FR-021:** The system shall compare FCFS, priority-greedy, and optimized results using the same dataset and horizon.
- **FR-022:** Metrics shall be computed from stored result data and include definitions; no hardcoded performance claims.
- **FR-023:** The system should support a limited counterfactual/relaxation analysis only where it can produce a verified result; otherwise it must report that no validated alternative was found.

### Review, approval, audit
- **FR-024:** Users shall be able to inspect a plan's tasks, time intervals, sections, constraints, and diagnostics.
- **FR-025:** Approval shall only be allowed for a plan that passed independent validation.
- **FR-026:** Approval shall create an immutable plan version rather than overwrite historical approved data.
- **FR-027:** Each approval/rejection/revision shall create an audit event with actor, timestamp, action, target, and reason.
- **FR-028:** The audit chain may include a SHA-256 digest for tamper-evidence, but the product shall not claim that hashing alone makes storage immutable or legally certified.

### AI Copilot
- **FR-029:** The Copilot shall answer only from task, plan, solver, validator, diagnostic, and rule records supplied through read-only tools.
- **FR-030:** The Copilot shall cite the task/plan/constraint/rule identifiers supporting a response.
- **FR-031:** The Copilot shall state when evidence is missing and shall not invent train IDs, rules, timestamps, or alternatives.
- **FR-032:** The Copilot shall not generate schedules, change constraints, approve plans, or mutate the database.
- **FR-033:** If the LLM provider is unavailable, all non-Copilot planning features shall continue to work.

## 8. Non-functional requirements

- **NFR-001 Correctness:** Every displayed candidate schedule must pass the independent validator or be visibly marked invalid.
- **NFR-002 Reproducibility:** Identical dataset seed, configuration, and code/model version should reproduce the same input data; solver output may require deterministic solver settings to be exactly reproducible.
- **NFR-003 Performance:** Initial target: solve a demonstration instance of up to 50 tasks and a few dozen train passes within 5 seconds on the development machine. This is a target to benchmark, not a verified promise.
- **NFR-004 Resource usage:** Keep the API process lightweight. Run CPU/memory-heavy optimization in a separate worker process where practical. Set explicit worker limits and solver timeouts.
- **NFR-005 Security:** Validate all inputs; enforce authorization server-side; keep secrets in environment variables; do not expose stack traces or secrets.
- **NFR-006 Explainability:** Scheduling outcomes must have machine-readable reasons before any natural-language explanation is attempted.
- **NFR-007 Accessibility:** Keyboard-operable navigation, visible focus, sufficient contrast, reduced-motion support, and semantic controls.
- **NFR-008 Resilience:** Failure of the LLM or 3D visualizer must not prevent access to core planning results.
- **NFR-009 Auditability:** Approved plan versions and audit events must be retained and queryable.
- **NFR-010 Honesty:** Synthetic, illustrative, unverified, failed, or partial results must be labeled accurately.

## 9. Core application screens

1. **Landing page:** product narrative, railway visualization, workflow explanation, synthetic-data boundary, CTA to demo.
2. **Overview dashboard:** dataset badge, task counts, plan status, recent runs, high-level computed metrics.
3. **Planning workspace:** task list, time-space chart, filters, selected-task inspector, conflict/diagnostic panel.
4. **Scenario comparison:** FCFS vs priority-greedy vs CP-SAT with shared metric definitions.
5. **Data & network:** stations, sections, lines, trains, train passes, resources, and dataset provenance.
6. **Optimization run detail:** run status, configuration, solver status, runtime, validation outcome, warnings.
7. **Audit/review:** plan versions, approval history, differences, reviewer reason.
8. **Settings:** demo users, safe objective configuration, dataset/scenario controls.
9. **Copilot drawer:** evidence-grounded answers and source identifiers.

## 10. Success criteria for the MVP

- A new developer can install and run the application using the README.
- A seeded synthetic dataset can be regenerated reproducibly.
- A user can generate FCFS, priority-greedy, and CP-SAT plans from the same snapshot.
- The independent validator catches deliberately injected invalid intervals/conflicts in tests.
- Every unscheduled task has a deterministic status/reason or an explicit `UNKNOWN/UNDIAGNOSED` state.
- A valid plan can be reviewed, approved, and retrieved as an immutable version.
- The dashboard's metrics are derived from result data rather than hardcoded claims.
- The core workflow still works if the LLM provider is disabled.
- No screen implies live railway data or real-world safety approval.
- Unit, API, database, solver, and end-to-end tests pass.

## 11. Open assumptions

- The corridor is fictional; names are illustrative and not a representation of verified operating geography.
- Initial planning horizon is a configurable short demonstration window. A 26-week rolling plan is a future direction unless a validated time model is implemented.
- Operational constraints and headways in the demo are synthetic scenario parameters, not approved railway rules.
- User roles and approval behavior are prototype workflow semantics, not official Railway authorization.
- Objective weights are configurable experimental parameters and require sensitivity analysis; they are not domain-calibrated facts.
