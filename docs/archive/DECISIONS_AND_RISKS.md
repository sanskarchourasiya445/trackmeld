# TrackMeld Architecture Decisions, Assumptions, and Risks

## 1. Important refinements to the initial design

### D-001 — Synthetic data is the MVP source of truth

**Decision:** Use a fictional corridor and reproducible generated data.  
**Reason:** Internal railway operational data and APIs are not assumed to be available.  
**Consequence:** All demo values must be labeled synthetic; public references must retain source and date; real-data integration remains a future adapter.  
**Not allowed:** presenting generated train movements or impact metrics as real.

### D-002 — Do not rely on bounded clique enumeration as a linear-size guarantee

**Problem:** Restricting clique size to `K ≤ 4` limits group size but does not generally guarantee at most `4 × task_count` candidate bundles. The number of compatible groups can still grow rapidly.  
**Decision:** Start with task-level interval variables and explicit constraints. Add bundle variables only if required and benchmarked.  
**Consequence:** Simpler modeling and more transparent tests; bundling semantics must be designed explicitly.

### D-003 — Model bundled duration explicitly

**Problem:** `max(task durations) + setup` is not universally correct. It depends on whether tasks execute in parallel, whether resources are shared, and how setup/clearance is defined.  
**Decision:** For the MVP, define exactly which tasks can overlap, which consume separate resources, and what a shared possession interval means. If this is not specified, do not claim the bundling model is operationally realistic.  
**Consequence:** Use a clearly labeled simplified model until reviewed.

### D-004 — Separate feasibility from preference

**Decision:** Hard constraints determine whether a candidate is valid. Objective weights only choose among valid candidates.  
**Reason:** A large penalty should not allow a safety-critical hard constraint to be violated.  
**Consequence:** Mandatory tasks should not be represented only by a large penalty. If mandatory tasks cannot be scheduled, report infeasibility or explicit unscheduled status according to a documented policy.

### D-005 — Priority weights are experimental until calibrated

**Decision:** Store feature values, score breakdown, formula version, and configuration.  
**Reason:** Arbitrary weights cannot be presented as validated railway policy.  
**Consequence:** Add sensitivity tests and disclose assumptions in demo documentation.

### D-006 — Solver status and validation status are separate

**Decision:** Persist solver status and independent validator status separately.  
**Reason:** A solver may find a feasible incumbent without proving optimality; a returned result must still be independently checked.  
**Consequence:** A plan is approvable only when it is independently validated and in an eligible lifecycle state.

### D-007 — Human approval is a product workflow, not railway authorization

**Decision:** Prototype approval records who approved a candidate inside TrackMeld.  
**Reason:** The system has no authority to grant real operational blocks or certify railway safety.  
**Consequence:** UI copy must not imply an approved TrackMeld plan is an official railway instruction.

### D-008 — Audit hashes are tamper-evident aids, not immutability by themselves

**Decision:** Use append-only application behavior and optional hash chaining.  
**Reason:** SHA-256 on a row does not prevent an administrator from rewriting the row and hash unless the expected digest is protected elsewhere.  
**Consequence:** Describe the feature as an integrity/tamper-evidence mechanism, not a cryptographic legal signature.

### D-009 — No LangGraph, MCP, or vector RAG in MVP

**Decision:** Use direct typed Python tools and a small provider adapter for read-only explanations.  
**Reason:** Structured data and a compact rule catalog do not yet justify graph orchestration, a tool protocol server, or vector retrieval.  
**Consequence:** Add these technologies only after a demonstrated requirement and measurable benefit.

### D-010 — Keep the API lightweight and isolate solver work

**Decision:** Run long/CPU-bound planning in a separate worker process where practical.  
**Reason:** API responsiveness and memory/CPU limits.  
**Consequence:** Persist job state and provide timeouts. Measure real RAM/CPU before deciding whether the deployment needs a dedicated worker service.

## 2. Assumptions register

| ID | Assumption | Status | How to validate |
|---|---|---|---|
| A-001 | Initial corridor is fictional | Accepted for MVP | Ensure labels and generator agree |
| A-002 | Initial workload is 30–50 tasks | Provisional | Benchmark and tune generator |
| A-003 | A short horizon is sufficient for the demo | Provisional | Confirm demo workflow |
| A-004 | `Asia/Kolkata` is the initial display timezone | Provisional | Make configurable and test |
| A-005 | Department categories include Engineering, TRD, S&T | Demo assumption | Review if domain scope changes |
| A-006 | CP-SAT can solve target instances within 5 seconds | Unverified target | Benchmark on actual host/hardware |
| A-007 | Copilot uses a provider API | Optional | Keep feature disabled when unconfigured |
| A-008 | Approval roles are prototype roles | Accepted boundary | State in UI/docs |

## 3. Risk register

| Risk | Impact | Mitigation | Fallback |
|---|---|---|---|
| Synthetic data looks like real operations | High credibility risk | Persistent badges, manifest, fictional IDs, explicit docs | Disable misleading views |
| Incorrect safety rule encoded | Critical | Provenance, verification status, domain review, tests | Keep as assumption/diagnostic only |
| Solver returns invalid or partial output | High | Independent validator, solver status handling | Block approval and show failure |
| Candidate bundles explode combinatorially | High performance risk | Task-level intervals, bounded input, benchmark | Disable bundle mode |
| Arbitrary objective weights distort schedule | Medium/high | Expose breakdown, version weights, sensitivity tests | Use simpler objective |
| Worker exhausts host memory | High availability risk | Limits, timeout, small snapshots, measured benchmarks | Run smaller workload or dedicated worker |
| LLM invents a cause | High trust risk | Tool-grounded responses, evidence IDs, evaluation tests | Show deterministic diagnostics only |
| LLM provider unavailable | Low/moderate | Optional Copilot and graceful failure | Continue without AI |
| 3D scene hurts performance/accessibility | Medium | Static fallback, reduced motion, lazy load | Disable 3D |
| Approval is mistaken for official authorization | Critical | Explicit wording and product boundary | Remove approval language that implies official status |
| Metrics are hardcoded or misleading | High | Compute from persisted results; define formulas | Hide metrics until data is available |
| Data source licensing unclear | High | Record source and terms before use | Use synthetic data only |

## 4. Metric definitions to establish before UI implementation

Do not display metrics until each has a formula. Suggested definitions:

- **Tasks scheduled:** number of distinct tasks assigned a valid interval.
- **Tasks unscheduled:** number of input tasks without a valid assignment, categorized by reason.
- **Possessions/windows:** count according to the product's explicit grouping semantics.
- **Blocked lane-minutes:** sum of exclusive interval duration per modeled track/line; avoid double-counting overlapping intervals unless the metric explicitly counts lane-minutes.
- **Conflicts:** count of unique conflict records after deduplication, not raw pairwise conflict messages.
- **Runtime:** wall-clock time for the run, with hardware and workload context for benchmarks.
- **Improvement vs baseline:** calculate from the same input snapshot and horizon; report absolute and relative differences; do not label as real-world operational improvement.

## 5. Definition of a credible demo

A credible demonstration should prove:
1. The dataset is synthetic and reproducible.
2. The baseline and optimizer use the same inputs.
3. The optimizer obeys the modeled constraints.
4. An independent validator verifies the candidate.
5. A user can inspect why a task was or was not scheduled.
6. Comparison metrics are calculated from results.
7. A human can approve only a validated candidate.
8. Approval creates a new immutable version and audit record.
9. The Copilot can explain only the facts returned by tools.
10. The system remains useful when the Copilot or 3D scene is disabled.
