# TrackMeld — Phase 5 Baseline Schedulers & Priority Scoring Report

## 1. Executive Summary

Phase 5 implements the **deterministic baseline scheduling framework** and **transparent priority scoring model** for TrackMeld.

**Core Principle:**
> *Rules classify → Optimization schedules → Humans approve → AI explains — never decides.*

Phase 5 establishes two deterministic reference schedulers:
1. **Baseline A: FCFS (First-Come, First-Served):** Orders tasks by requisition arrival/execution window start timestamp, breaking ties by `task_id`.
2. **Baseline B: Priority-Greedy:** Orders tasks by descending explainable priority score, breaking ties by mandatory status, window start, and `task_id`.

Both schedulers:
- Consume the exact same immutable in-memory **`PlanningSnapshot`**.
- Outsource 100% of feasibility and collision checks to the **Phase 4 `CompatibilityEngine`**.
- Produce the exact same **`ScheduleResult`** and **`ScheduleMetrics`** contracts.
- Serve as transparent benchmarks against which Phase 6 CP-SAT optimization will be compared.

Neither scheduler is claimed to represent official Indian Railways scheduling policy; all priority weights are explicitly documented as experimental heuristics for benchmarking.

---

## 2. Architecture & Component Separation

```text
               Operational Scenario (PostgreSQL)
                              │
                              ▼
                      Planning Snapshot
               (Immutable, Hash-Identified)
                              │
               ┌──────────────┴──────────────┐
               │                             │
               ▼                             ▼
         Priority Scorer                    FCFS
         (5 Explainable Factors)       (Arrival Order)
               │                             │
               ▼                             │
        Priority-Greedy                      │
               │                             │
               └──────────────┬──────────────┘
                              ▼
                     Candidate Generator
               (Event-Boundary Clearance Times)
                              │
                              ▼
                    Phase 4 Compatibility
               (Train, Section, Resource, Deps)
                              │
               ┌──────────────┴──────────────┐
               ▼                             ▼
        Scheduled Placements          Unscheduled Tasks
        (Zero Hard Violations)        (Diagnostics & Reasons)
               │                             │
               └──────────────┬──────────────┘
                              ▼
                      Schedule Metrics
               (Common Pure Calculations)
                              │
                              ▼
                 ScheduleResult / Benchmark
```

---

## 3. Planning Snapshot Abstraction

Schedulers must not query mutable database state in tight loops or observe concurrent modifications. `PlanningSnapshot` is an immutable, frozen data container:

- **Identity:** `snapshot_id = SNAP-{SHA256(scenario_id + start + end + sorted_task_ids)[:12]}`
- **Planning Horizon:** Immutable `[horizon.start, horizon.end)`
- **Task Registry:** Canonical list of tasks sorted deterministically by `task_id`
- **Lookup Maps:** `tasks_map`, `work_orders_map`, `sections_map`, `rules_map`, `resources_map`
- **Dependencies Index:** `dependencies_by_successor` and `dependencies_by_predecessor`
- **Corridor Train Passes:** Continuous train passes pre-projected across the planning horizon via `CompatibilityEngine.derive_train_passes()`

---

## 4. Priority Scoring Model

### 4.1 Philosophy & Governance
- **Experimental Notice:** *"Priority weights are experimental configuration values for benchmark scheduling and are not official railway policy."*
- **Explainability:** Every score yields an explainable component breakdown with `raw_value`, `normalized_value`, `weight`, `contribution`, and `description`.
- **Normalization:** Every feature maps strictly to $[0.0, 1.0]$.
- **Contribution Formula:**
  $$\text{Contribution}_i = \text{Normalized}_i \times \text{Weight}_i$$
  $$\text{Total Score} = \sum_{i=1}^5 \text{Contribution}_i$$

### 4.2 Feature Definitions

| Feature | Raw Domain Source | Normalization Rule | Default Weight | Description |
| :--- | :--- | :--- | :---: | :--- |
| **`mandatory`** | `task.mandatory` (bool) | `1.0` if mandatory, else `0.0` | 100.0 | Statutory safety requirement |
| **`urgency`** | `task.priority` (enum) | CRITICAL: `1.0`, HIGH: `0.75`, MEDIUM: `0.50`, LOW: `0.25` | 40.0 | Operational urgency level |
| **`window_tightness`** | `(duration + buffers) / window_span` | Clamped to $[0.0, 1.0]$ | 20.0 | Ratio of needed time to window |
| **`dependency_bottleneck`** | Downstream successors count | $\min(1.0, \frac{\text{successors}}{3.0})$ | 20.0 | Bottleneck unlocking downstream work |
| **`operational_impact`** | Block requirements | Traffic & Power: `1.0`, Traffic: `0.75`, Power: `0.50`, None: `0.20` | 10.0 | Extent of track/traction isolation |

### 4.3 Real Example Breakdown (`TSK-0001` on Corridor)
```json
{
  "task_id": "TSK-0001",
  "total_score": 147.22,
  "config_id": "priority-config-v1",
  "config_version": "1.0.0",
  "components": {
    "mandatory": {
      "raw_value": true,
      "normalized_value": 1.0,
      "weight": 100.0,
      "contribution": 100.0,
      "description": "Statutory or regulatory mandatory maintenance requisition."
    },
    "urgency": {
      "raw_value": "HIGH",
      "normalized_value": 0.75,
      "weight": 40.0,
      "contribution": 30.0,
      "description": "Requisition operational priority level (CRITICAL=1.0, HIGH=0.75, MEDIUM=0.5, LOW=0.25)."
    },
    "window_tightness": {
      "raw_value": 0.4861,
      "normalized_value": 0.4861,
      "weight": 20.0,
      "contribution": 9.72,
      "description": "Ratio of required possession duration to allowed execution window."
    },
    "dependency_bottleneck": {
      "raw_value": 0,
      "normalized_value": 0.0,
      "weight": 20.0,
      "contribution": 0.0,
      "description": "Normalized count of downstream successor tasks waiting on completion of this task."
    },
    "operational_impact": {
      "raw_value": {"requires_traffic_block": true, "requires_power_block": false},
      "normalized_value": 0.75,
      "weight": 10.0,
      "contribution": 7.5,
      "description": "Requires traffic block on primary track section."
    }
  }
}
```

---

## 5. Baseline Scheduling Algorithms

### 5.1 FCFS (First-Come, First-Served)
- **Ordering Key:**
  1. Primary: Requisition arrival timestamp (`task.window_start` or `work_order.requested_execution_start`) ascending.
  2. Secondary (Tie-Breaker): `task_id` alphabetical ascending.
- **Candidate Selection:** Evaluates candidate start times in ascending chronological order; selects the **first feasible** slot meeting all Phase 4 hard constraints.
- **Non-Bypass Rule:** FCFS is never allowed to schedule a task if it violates a train path, track exclusivity, resource window, or dependency.

### 5.2 Priority-Greedy
- **Ordering Key:**
  1. Primary: `-total_score` (descending priority score).
  2. Secondary: `mandatory` (True before False).
  3. Tertiary: Requisition arrival timestamp (`window_start`) ascending.
  4. Quaternary (Tie-Breaker): `task_id` alphabetical ascending.
- **Greedy Placement Policy:** Iterates through high-priority tasks first. If an earlier task cannot be placed due to conflicts, it is marked unscheduled and the scheduler proceeds to the next task without global backtracking.

### 5.3 Candidate Timepoint Generation
Rather than brute-force minute-by-minute scanning across a 72-hour planning horizon, `CandidateGenerator` identifies natural railway event boundaries:
1. `task.window_start`
2. `task.preferred_start` (if configured)
3. Predecessor task completion time: $t_{\text{pred, end}}$
4. Previously scheduled task possession release times on same/overlapping sections
5. Train pass section clearance times: $t_{\text{train, end}}$
6. Resource availability window starts: $t_{\text{res, start}}$
7. Periodic interval step points (30-min increments) to cover gaps

All candidate start times are validated to satisfy $start + duration \le \min(window\_end, horizon.end)$, deduplicated, sorted ascending, and bounded to `max_candidate_attempts` (default 50).

---

## 6. Dependency Handling & Cycle Detection

- **Topological Cycle Detection:** Before any scheduling begins, directed dependencies are inspected via DFS cycle detection. If a circular chain ($A \to B \to A$) is detected, the run immediately terminates with `SchedulerStatus.INVALID_INPUT` and logs the exact cycle path.
- **Finish-to-Start Precedence:** A task $T_{\text{succ}}$ depending on $T_{\text{pred}}$ is deferred until $T_{\text{pred}}$ is evaluated. If $T_{\text{pred}}$ is scheduled, $T_{\text{succ}}$ candidates are restricted such that $t_{\text{succ, start}} \ge t_{\text{pred, end}}$. If $T_{\text{pred}}$ cannot be placed, $T_{\text{succ}}$ is marked unscheduled with `ReasonCode.DEPENDENCY_NOT_SATISFIED`.

---

## 7. Factual Benchmark Results on `SCN-DEMO-001`

Both baseline schedulers were executed against the canonical 72-hour operational corridor scenario `SCN-DEMO-001` (30 maintenance tasks, 100 corridor train passes, 21 maintenance resources).

| Metric | Baseline A: FCFS | Baseline B: Priority-Greedy | Description |
| :--- | :---: | :---: | :--- |
| **Total Tasks In Scope** | 30 | 30 | Total tasks in scenario snapshot |
| **Scheduled Tasks** | 29 | 29 | Tasks successfully allocated feasible windows |
| **Unscheduled Tasks** | 1 | 1 | Tasks rejected by hard safety constraints |
| **Completion Rate** | **96.7%** | **96.7%** | $\text{scheduled} / \text{total}$ |
| **Mandatory Tasks Total** | 17 | 17 | Regulatory safety tasks |
| **Mandatory Tasks Scheduled** | **17** | **17** | Mandatory tasks placed feasibly |
| **Mandatory Completion Rate**| **100.0%** | **100.0%** | All statutory tasks placed |
| **Total Scheduled Work** | 3,615 mins (60.25h) | 3,615 mins (60.25h) | Net productive maintenance time |
| **Total Track Possession** | 4,485 mins (74.75h) | 4,485 mins (74.75h) | Gross track occupancy with safety buffers |
| **Available Priority Points** | 3,045.22 | 3,045.22 | Total score across all 30 tasks |
| **Captured Priority Points** | **3,001.06** | **3,001.06** | Score captured by scheduled tasks |
| **Priority Capture Rate** | **98.6%** | **98.6%** | Captured / Available score |
| **Execution Latency** | **6.77 ms** | **7.01 ms** | Wall-clock execution time |

### Unscheduled Task Analysis
- **Unscheduled Task:** `TSK-0007` (`TSK-TRK-007`, Mandatory: False)
- **Reason:** `DEPENDENCY_NOT_SATISFIED`
- **Cause:** Predecessor task `TSK-TRK-006` completed at `2026-10-11T16:00:00 UTC`. The execution window for `TSK-TRK-007` expired before `TSK-TRK-006` cleared the track. Phase 4 strictly prevented an invalid execution order.

---

## 8. Test & Validation Summary

| Test / Script | Scope | Passed | Failed | Status |
| :--- | :--- | :---: | :---: | :---: |
| **Full Pytest Suite** | Unit + Integration across all phases | **113** | **0** | **PASS** |
| - `test_priority_scorer.py` | Priority weights, normalization, breakdown | 6 | 0 | **PASS** |
| - `test_candidate_generator.py` | Event boundaries, bounds, deduplication | 3 | 0 | **PASS** |
| - `test_schedulers.py` | FCFS vs Greedy, ties, dependencies, cycles | 6 | 0 | **PASS** |
| - `test_phase5_baseline_api.py` | Fast REST API baseline and benchmark endpoints | 4 | 0 | **PASS** |
| - Phase 1–4 Tests | Grounding, Reference, Operational, Feasibility | 94 | 0 | **PASS** |
| **`validate_phase5_schedulers.py`** | 30 Automated Phase 5 Invariant Checks | **30** | **0** | **PASS** |
| **`validate_phase4_compatibility.py`**| 17 Automated Feasibility Invariant Checks | **17** | **0** | **PASS** |
| **`validate_operational_data.py`** | 30 Automated Operational Schema Checks | **30** | **0** | **PASS** |
| **`validate_database.py`** | 31 Automated Canonical Reference Checks | **31** | **0** | **PASS** |
| **Total Automated Checks** | Full Stack Invariants | **221** | **0** | **PASS** |

---

## 9. Phase 6 Handoff Contract

### What Phase 6 CP-SAT Will Consume
1. **`PlanningSnapshot`:** Identical immutable input context containing tasks, train passes, resources, availability, dependencies, and horizon.
2. **Phase 4 `CompatibilityEngine` / Hard Constraint Semantics:** Native interval modeling in CP-SAT ($IntervalVar$) with identical setup/clearance buffers, section exclusivity ($NoOverlap$), resource capacities ($Cumulative$), and train path clearances.
3. **`PriorityScore`:** CP-SAT objective function weights can align with the configurable `PriorityScore` components ($maximize \sum w_i x_i$).
4. **`ScheduleResult` & `ScheduleMetrics`:** CP-SAT solver output will be mapped to the exact same `ScheduleResult` schema, enabling three-way side-by-side benchmarking:
   $$\text{FCFS} \quad \text{vs} \quad \text{Priority-Greedy} \quad \text{vs} \quad \text{CP-SAT}$$

### What Phase 6 Does NOT Depend On
- Internal ordering heuristic implementations of FCFS or Priority-Greedy.
