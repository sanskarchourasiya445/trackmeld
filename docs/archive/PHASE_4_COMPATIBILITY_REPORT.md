# TrackMeld — Phase 4 Planning Windows & Compatibility Report

## 1. Executive Summary

TrackMeld Phase 4 ("Planning Windows and Compatibility") has been completed. This phase establishes the deterministic feasibility, interval mathematics, and constraint evaluation engine that future baseline schedulers (Phase 5) and CP-SAT optimization (Phase 6) will consume.

The engine answers the foundational planning question:
> **"Can this task be placed at this time and location under the currently modeled data and rules, and exactly why?"**

All feasibility rules are deterministic, explainable, and inspectable, strictly adhering to the core principle:
**Rules classify. Optimization schedules. Humans approve. AI explains — never decides.**

---

## 2. Time Model & Half-Open Interval Semantics

### 2.1. The Half-Open Convention $[start, end)$
In continuous railway timetabling and maintenance possession scheduling, discrete or closed intervals $[start, end]$ create boundary ambiguity at handovers. TrackMeld enforces a strict half-open interval convention:
$$I = [start, end) = \{ t \in \mathbb{R} \mid start \le t < end \}$$

Under this model:
- **Duration:** $\Delta t = end - start > 0$.
- **Overlap Criterion:** Two intervals $I_1 = [s_1, e_1)$ and $I_2 = [s_2, e_2)$ overlap if and only if:
  $$\max(s_1, s_2) < \min(e_1, e_2)$$
- **Strict Adjacency:** If task A executes in $[10:00, 11:00)$ and task B executes in $[11:00, 12:00)$, they meet at the exact boundary $11:00$ without overlapping:
  $$\max(10:00, 11:00) < \min(11:00, 12:00) \implies 11:00 < 11:00 \quad (\text{False})$$
  No artificial minute offsets (e.g. 10:59) are required.
- **Degenerate / Inverted Intervals:**
  - $start == end$: Zero-duration interval, strictly invalid.
  - $start > end$: Negative duration interval, strictly invalid.
- **Timezone Invariant:** All datetimes are forced to UTC timezone-awareness (`tzinfo=timezone.utc`).

### 2.2. Effective Track Possession & Safety Buffers
Maintenance tasks have an active execution duration $D$ and setup/clearance safety buffers:
- `safety_buffer_before_minutes` ($\Delta_{before}$, default 15 min): Track protection setup, OHE isolation, signal disconnection.
- `safety_buffer_after_minutes` ($\Delta_{after}$, default 15 min): Track restoration, packing clearance, OHE recharging, safety clearance.

For a candidate execution interval $[t_{start}, t_{end})$:
$$I_{possession} = [t_{start} - \Delta_{before}, \, t_{end} + \Delta_{after})$$
Track exclusivity, train crossing conflicts, and multi-section possessions are evaluated against $I_{possession}$, not merely the active work interval.

---

## 3. Planning Horizon

The `PlanningHorizon` models the continuous time span bounding all scheduling activities:
- Default demonstration horizon: 72 hours (e.g. `2026-10-10 00:00:00 UTC` to `2026-10-13 00:00:00 UTC`).
- Enclosure constraint: For any task placement $I = [start, end)$, the condition $H_{start} \le start \land end \le H_{end}$ must hold.

---

## 4. Four-Tier Constraint Classification Hierarchy

To prevent unverified assumptions from silently becoming safety-critical hard constraints, TrackMeld categorizes all constraints into four distinct tiers:

| Tier | Severity | Definition | Engine Behavior on Violation |
| :--- | :--- | :--- | :--- |
| **HARD** | `ConstraintSeverity.HARD` | Physical reality or statutory safety rules (e.g., train collision, section occupancy, window breach, predecessor unfinished, non-electrified power block). | Infeasible (`compatible = False`, `feasible_hard = False`). Solver / scheduler must reject. |
| **SOFT** | `ConstraintSeverity.SOFT` | Operational preferences, secondary resource shortages, or unmandated guidelines. | Feasible (`compatible = True`, `admissible_soft = False`). Solver penalizes in objective function. |
| **DIAGNOSTIC_ONLY** | `ConstraintSeverity.DIAGNOSTIC_ONLY` | Advisory telemetry, demo heuristics, shift guidelines. | Logged in diagnostics. Does not alter feasibility or objective score. |
| **UNVERIFIED** | `ConstraintSeverity.UNVERIFIED` | Domain assumptions without verified authoritative citations. | **NEVER promoted to HARD.** Recorded with `UNVERIFIED_RULE` reason code and diagnostic evidence. |

---

## 5. Compatibility Engine Architecture & Reason Codes

The `CompatibilityEngine` (`backend/app/services/compatibility_service.py`) evaluates candidate task placements across 10 deterministic checks:

```text
Candidate Task Placement [start, end)
                  │
                  ▼
1. Interval Validity Check [start < end, duration match]
                  │
                  ▼
2. Planning Horizon Enclosure [horizon_start <= start and end <= horizon_end]
                  │
                  ▼
3. Task Planning Window Check [window_start <= start and end <= window_end]
                  │
                  ▼
4. Effective Possession Calculation [apply before/after safety buffers]
                  │
                  ▼
5. Block Requirements Check [electrification verification for power blocks]
                  │
                  ▼
6. Train Occupancy Conflict Detection [train passes across affected sections]
                  │
                  ▼
7. Section Exclusivity & Multi-Section Collisions [concurrent task possessions]
                  │
                  ▼
8. Resource Availability & Concurrent Overlap [depot schedules and tool collisions]
                  │
                  ▼
9. Task Dependency Precedence [FINISH_TO_START precedence validation]
                  │
                  ▼
10. Rule Evidence & Provenance Compilation [audit trail of statutory citations]
                  │
                  ▼
       Structured CompatibilityResult
```

### Reason Code Catalog

| Reason Code | Severity | Trigger Condition |
| :--- | :--- | :--- |
| `INVALID_INTERVAL` | HARD | Zero-duration, negative duration, or duration does not match task requirement. |
| `OUTSIDE_PLANNING_HORIZON` | HARD | Candidate interval extends beyond the scenario planning horizon. |
| `TASK_WINDOW_CONFLICT` | HARD | Candidate interval extends outside the task's allowed planning window. |
| `TRAIN_MOVEMENT_CONFLICT` | HARD | Train movement traverses the section during the effective possession window. |
| `SECTION_OCCUPANCY_CONFLICT` | HARD | Another task concurrently occupies the primary block section. |
| `MULTI_SECTION_CONFLICT` | HARD | Another task concurrently occupies one of the secondary affected sections. |
| `RESOURCE_UNAVAILABLE` | HARD / SOFT | Required resource has no active availability schedule enclosing the task. |
| `RESOURCE_OVERLAP` | HARD | A required resource is concurrently assigned to another task. |
| `DEPENDENCY_NOT_SATISFIED` | HARD | Predecessor task is unscheduled or finishes after candidate start time ($t_{pred, end} > t_{start}$). |
| `TRAFFIC_BLOCK_REQUIRED` | HARD | Traffic block required but track has conflicting train traffic. |
| `POWER_BLOCK_REQUIRED` | HARD | Power block requested on a non-electrified block section. |
| `PTW_REQUIRED` | SOFT | Permit-to-Work protocol required under safety rules. |
| `UNVERIFIED_RULE` | UNVERIFIED | Unverified assumption evaluated; kept strictly non-hard. |

---

## 6. Structured Result Schema (`CompatibilityResult`)

Every evaluation returns a structured payload:

```json
{
  "task_id": "TSK-0001",
  "compatible": false,
  "feasible_hard": false,
  "admissible_soft": true,
  "evaluated_interval": {
    "start": "2026-10-11T14:00:00Z",
    "end": "2026-10-11T17:00:00Z"
  },
  "possession_interval": {
    "start": "2026-10-11T13:45:00Z",
    "end": "2026-10-11T17:15:00Z"
  },
  "reason_codes": ["TASK_WINDOW_CONFLICT"],
  "conflicts": [
    {
      "conflict_type": "WINDOW_BREACH",
      "severity": "HARD",
      "reason_code": "TASK_WINDOW_CONFLICT",
      "message": "Candidate interval [2026-10-11T14:00:00+00:00, 2026-10-11T17:00:00+00:00) extends outside allowed task window [2026-10-10T07:00:00+00:00, 2026-10-10T12:00:00+00:00).",
      "conflicting_entity_type": "WORK_WINDOW",
      "conflicting_entity_id": "TSK-0001",
      "conflict_interval": null
    }
  ],
  "affected_sections": ["SEC-NDLS-GZB", "SEC-GZB-KRJ"],
  "affected_movements": [],
  "affected_resources": ["RES-TM-CSM-01"],
  "rule_evidence": [
    {
      "rule_id": "RULE-STAT-RBP-1502C",
      "title": "Indian Railways Rolling Block Programme Mandate",
      "rule_class": "VERIFIED_SOURCE",
      "source_id": "SRC-IR-RBP-2023",
      "severity": "HARD",
      "satisfied": false,
      "explanation": "Verified railway rule RULE-STAT-RBP-1502C evaluated under hard constraint enforcement (SRC-IR-RBP-2023)."
    }
  ]
}
```

---

## 7. Sample Evaluations

### Example 1: Feasible Placement
- **Task:** `TSK-TRK-001` (Tamping on `SEC-NDLS-GZB`, duration 180m, window 07:00–12:00)
- **Candidate Time:** `2026-10-10 08:00 to 11:00 UTC`
- **Result:**
  - `compatible`: `True`
  - `feasible_hard`: `True`
  - `admissible_soft`: `True`
  - `reason_codes`: `[]`
  - `conflicts`: `[]`

### Example 2: Train Collision
- **Task:** `TSK-TRK-001` (requires traffic block on `SEC-NDLS-GZB`)
- **Collision:** Express train `TRN-12301` occupies section `SEC-NDLS-GZB` from 09:15 to 09:45 UTC.
- **Result:**
  - `compatible`: `False`
  - `feasible_hard`: `False`
  - `reason_codes`: `["TRAIN_MOVEMENT_CONFLICT", "TRAFFIC_BLOCK_REQUIRED"]`
  - `conflicts`: Itemized collision with exact `conflict_interval`.

### Example 3: Half-Open Boundary Clearance
- **Scenario:** Train pass finishes at exactly `09:45:00 UTC`. Task possession starts at exactly `09:45:00 UTC`.
- **Result:**
  - `compatible`: `True`
  - `conflicts`: `[]` (Adjacency does not constitute an overlap).

---

## 8. Verification & Audit Results

1. **Pytest Regression Suite:**
   - **94 passed, 0 failed** in 9.03s across 16 test files.
   - 8 temporal unit tests (`tests/unit/test_temporal.py`).
   - 15 compatibility boundary unit tests (`tests/unit/test_compatibility_engine.py`).
   - 4 API integration tests (`tests/integration/test_phase4_compatibility_api.py`).
2. **Phase 4 Compatibility Validation Script (`scripts/validate_phase4_compatibility.py`):**
   - **17 passed, 0 failed** across half-open mathematics, database integration, train passes, and conflict detection.
3. **Reference Database Integrity (`scripts/validate_database.py`):**
   - **31 passed, 0 failed** (100% integrity across 3,679 reference rows).
4. **Operational Database Integrity (`scripts/validate_operational_data.py`):**
   - **30 passed, 0 failed** (100% integrity across synthetic scenario `SCN-DEMO-001`).

---

## 9. Known Limitations

- **Station Dwell Approximations:** Train passes currently model section travel and intermediate station stops; complex station yard crossover routing will be enhanced when topological junction interlocking graphs are modeled.
- **Unidirectional Blocks:** In double-track sections, traffic block currently reserves the primary section direction; bi-directional single line operations use the same section entity.

---

## 10. Phase 5 Readiness

TrackMeld is now **100% READY** for **Phase 5 — Priority & Baseline Schedulers**:
- The priority and greedy baseline schedulers can directly call `CompatibilityEngine.evaluate_task_placement(...)` to test whether a candidate task placement is feasible before accepting it into the baseline schedule.
- Objective metrics and reason codes are standardized across all methods.
- The independent validation layer can reuse this exact compatibility engine to verify CP-SAT solver candidate outputs in Phase 6.
