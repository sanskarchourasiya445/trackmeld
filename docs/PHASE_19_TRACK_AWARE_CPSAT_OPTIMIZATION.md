# Phase 19 — Track-Aware CP-SAT Optimization Report

**Phase:** Phase 19 — Track-Aware CP-SAT Optimization  
**Status:** COMPLETED  
**Baseline HEAD:** `7465069` (`feat(phase-18): add track-aware validator verification`)  
**Commit:** `feat(phase-19): add conservative track-aware cp-sat optimization`  
**Date:** October 2026  

---

## 1. Objective

Phase 19 extends TrackMeld's discrete optimization engine (`Google OR-Tools CP-SAT`) so that maintenance work and train movements can utilize explicit physical running lines where sufficient spatial and topology information is present, while strictly preserving the whole-section safety model as the authoritative fallback whenever spatial certainty is incomplete.

### Core Architectural Principle
```
Rules classify
    ↓
Optimization schedules
    ↓
Independent Validator verifies
    ↓
Human approves

And:
OPTIMAL != APPROVED
FEASIBLE != APPROVED
VALID != APPROVED
```

Track-aware optimization is designed to be **more informed, never less conservative**:
- Missing or unresolved track assignment $\implies$ retain section-level exclusivity.
- Missing adjacency metadata $\implies$ retain section-level exclusivity.
- Ambiguous or unresolved route $\implies$ retain section-level exclusivity.
- Physical track conflict / full adjacent block $\implies$ strict mutual exclusion.

---

## 2. Existing Whole-Section Solver Baseline

Prior to Phase 19, `CPSATModelBuilder` (`backend/app/services/optimization/cp_sat_model.py`) operated strictly at the block-section level:
- Tasks were modeled with optional intervals `[start, end)` bounded by work windows.
- Possession envelopes were expanded with safety buffers: `[start - buf_before, end + buf_after)`.
- For each section `sec_id`, all task possession intervals and all train pass intervals were placed into a single list `section_intervals`.
- A single disjunctive constraint `model.AddNoOverlap(section_intervals)` was posted for each section.
- Tasks on physically distinct running lines (e.g. UP track vs DOWN track) in the same section were unconditionally blocked from running concurrently.

---

## 3. Track-Aware Conservative Extension

Phase 19 introduces a conservative resource hierarchy in `CPSATModelBuilder` controlled by `OptimizationConfig.solver_mode`:
- `WHOLE_SECTION`: Retains the historical single `AddNoOverlap` per section across all occupants.
- `TRACK_AWARE_CONSERVATIVE` (default): Uses track-aware disjunctive constraints where provably safe, and enforces section-level mutual exclusion elsewhere.

### 3.1 Resource Hierarchy

| Case | Scenario | Solver Behavior |
| :--- | :--- | :--- |
| **Case A: Fully Resolved** | All occupants in section have validated physical tracks, complete adjacency metadata, no full traffic blocks, and no direction conflicts. | Occupants on separate tracks may run concurrently; same-track occupants enforce per-track `AddNoOverlap`. |
| **Case B: Partially Resolved** | Some occupants have physical track assignments, while others have `track_id = None` or unresolved traversals. | Resolved compatible tracks may run concurrently; unresolved occupants enforce mutual exclusion (`AddNoOverlap`) against **all** other occupants in the section. |
| **Case C: No Spatial Resolution** | Sections outside topology or missing track/adjacency metadata. | The solver falls back to whole-section exclusivity across all occupants in the section. |

---

## 4. Track Interval Model & Maintenance Track Validation

When a maintenance task specifies `track_id`:
1. **Track Existence:** Verified against `snapshot.tracks_map`. If unknown and track database is active, forced to `presence == 0` (infeasible if mandatory, unscheduled if optional).
2. **Section Matching:** Verified that `track.section_id == task.section_id`. If mismatched, forced to `presence == 0`.
3. **Direction Compatibility:** Verified that task direction matches track authorized direction (`UP`, `DOWN`, `BIDIRECTIONAL`). If mismatched, forced to `presence == 0`.
4. **Multi-Section Enclosure:** If a task spans additional sections (`additional_sections`), it receives physical track resolution on its primary section, while secondary sections without designated tracks receive whole-section protection.

---

## 5. Train Traversal Integration

In accordance with Phase 17 deterministic route resolution:
- Traversals with `resolution_status in (RESOLVED, EXPANDED_ROUTE, DIRECT_SECTION)` and a populated `traversal_track_id` provide track-aware physical occupancy on that specific track.
- Traversals with `resolution_status in (AMBIGUOUS_ROUTE, UNRESOLVED)` receive `track_id = None`, forcing section-level fallback exclusivity.
- Train passes with section IDs from legacy/unit test fixtures continue to enforce section-level clearance.

---

## 6. Provable Spatial Compatibility Evaluation

Within each active section, pairwise compatibility between occupants `(occ1, occ2)` is evaluated via `CPSATModelBuilder._are_occupants_provably_compatible()`:

```
                                  [Check Both Track IDs]
                                             |
                         +-------------------+-------------------+
                         | Both present                          | One or both None
                         v                                       v
               [Distinct Tracks?]                           [INCOMPATIBLE]
                         |                                  (AddNoOverlap)
          +--------------+--------------+
          | Different                   | Same track
          v                             v
[Adjacency Metadata Present?]     [INCOMPATIBLE]
          |                       (AddNoOverlap)
    +-----+-----+
    | Yes       | Missing (None)
    v           v
[Adjacent?]  [INCOMPATIBLE]
    |        (AddNoOverlap)
    +---------------------------+
    | No                        | Yes
    v                           v
[COMPATIBLE]        [Task Impact Check]
(Coexistence)                   |
                    +-----------+-----------+
                    | Full Block/Unspecified| None / Caution
                    v                       v
              [INCOMPATIBLE]          [COMPATIBLE]
              (AddNoOverlap)          (Coexistence)
```

### Hard vs. Soft Rules
- **HARD (Mutual Exclusion):**
  - Same-track overlap.
  - Adjacent track `FULL_TRAFFIC_BLOCK` or `ADJACENT_TRACK_FOULING`.
  - Unspecified adjacent impact on adjacent line.
  - Missing adjacency metadata (`adjacent_track_ids is None`).
  - Unresolved track assignment (`track_id is None`).
  - Direction conflict.
- **SOFT (Permitted in Solver, Audited by Independent Validator):**
  - `CAUTION_ORDER` / `SPEED_RESTRICTION` on adjacent track does not create a hard solver block; it permits coexistence in CP-SAT while the Phase 18 Independent Validator independently flags `ADJACENT_TRACK_CAUTION_REQUIRED` (`INFO`).

---

## 7. Determinism & Objective Preservation

1. **Deterministic Construction:** Sections, tracks, tasks, traversals, and constraints are sorted deterministically before variable and constraint generation. Shuffling input ordering produces bit-for-bit identical schedule identities.
2. **Objective Function Unchanged:** Primary objective maximizes total scaled priority score; secondary penalty discourages gratuitously long possession envelopes. No arbitrary track preference weights are injected.
3. **Solver Independence:** CP-SAT never imports or calls `IndependentScheduleValidator` or `CompatibilityEngine`.

---

## 8. ScheduleResult & Identity Contract

`ScheduledTaskResult` was extended with `assigned_track_id: Optional[str] = None`.
- The historical `compute_schedule_identity()` fingerprint hashes `(task_id, start, end, pos_start, pos_end, sections, resources)`, keeping schedule identities 100% backward-compatible.
- `PlanningSnapshot.compute_snapshot_hash()` was untouched.

---

## 9. Performance & Solver Telemetry Comparison

Benchmarked on `SCN-DEMO-001` (30 maintenance tasks, 101 train passes, 64 physical tracks):

| Metric | Whole-Section Baseline | Track-Aware Conservative (Phase 19) | Delta |
| :--- | :--- | :--- | :--- |
| **Solver Status** | `OPTIMAL` | `OPTIMAL` | Identical |
| **Scheduled Tasks** | 29 / 30 | 29 / 30 | Identical |
| **Mandatory Tasks Scheduled** | 16 / 16 (100%) | 16 / 16 (100%) | Identical |
| **Wall Clock Time** | ~0.15s | ~0.16s | +0.01s (negligible) |
| **Model Constraints** | 258 | 264 | +6 track-level constraints |
| **Optimality Gap** | 0.0% | 0.0% | 0.0% |
| **Post-Solve Validation** | `VALID` | `VALID` | Certified |

---

## 10. Test Matrix & Verification

### Focused Phase 19 Suite (`tests/unit/test_phase19_track_aware_cpsat.py`)
16 comprehensive unit tests verifying all contracts:
1. `test_existing_whole_section_scheduling_still_works`: WHOLE_SECTION mode prevents overlap.
2. `test_track_specific_maintenance_surfaces_assigned_track`: `assigned_track_id` surfaced.
3. `test_same_track_maintenance_train_overlap_prevented`: Same-track task/train collision rejected.
4. `test_same_track_maintenance_maintenance_overlap_prevented`: Same-track task/task collision rejected.
5. `test_different_compatible_tracks_can_coexist`: Parallel work on UP and DN tracks schedules concurrently.
6. `test_adjacent_full_traffic_block_prevents_coexistence`: Full traffic block prevents adjacent placement.
7. `test_missing_adjacency_metadata_falls_back_to_section_protection`: Missing metadata enforces section fallback.
8. `test_unresolved_and_ambiguous_traversal_falls_back_to_section_protection`: AMBIGUOUS_ROUTE forces section exclusivity.
9. `test_invalid_task_track_assignment_infeasible`: Non-existent track ID proves infeasible.
10. `test_track_from_wrong_section_infeasible`: Track assigned to wrong section proves infeasible.
11. `test_directionally_incompatible_task_infeasible`: Travel direction mismatch proves infeasible.
12. `test_sections_outside_topology_remain_schedulable`: Unmodeled sections solve under fallback model.
13. `test_resource_and_dependency_constraints_remain_correct`: Precedence and machine exclusivity preserved.
14. `test_adversarial_ordering_independence_and_deterministic_solve`: Shuffled inputs produce identical fingerprint.
15. `test_solver_independence_and_validator_runnability`: Mocks confirm zero validator calls; validator audits post-solve.
16. `test_caution_order_permits_coexistence_in_solver`: Caution order permits coexistence; validator logs INFO.

### Full Regression Suite
- **Unit Tests:** 296 passed (100%).
- **Integration Tests:** 140 passed (100%).
- **Total Passing Tests:** 436 passed.

---

## 11. Explicit Non-Goals & Handoff to Future Work

> [!WARNING]
> **Track-aware CP-SAT optimization does NOT mean the railway is now operationally interlocked.**

The following domain capabilities remain explicitly outside the scope of Phase 19:
- Signalling aspects, route locking, overlap locking, and flank protection.
- Dynamic point machine / turnout switching.
- Real-time train dispatch and headway simulation.
- Human approval automation: Plans scheduled by CP-SAT remain unapproved until two authorized human operators certify them under four-eyes governance.
