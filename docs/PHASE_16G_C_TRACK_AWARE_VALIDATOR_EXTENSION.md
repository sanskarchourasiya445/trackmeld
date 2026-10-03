# Phase 16G-C: Track-Aware Validator Diagnostic & Safety Extension

**Status**: Implemented & Verified  
**Date**: October 2026  
**Baseline Commit**: `a55cb19` (Phase 16G-A)  
**Preceding Discovery**: `docs/PHASE_16G_B_VALIDATOR_INTEGRATION_DISCOVERY.md`  

---

## 1. Executive Summary

Phase 16G-C implements the **Track-Aware Validator Diagnostic & Safety Extension** for TrackMeld. It extends the Independent Schedule Validator (`ScheduleCheckRunner` / `IndependentScheduleValidator`) with additive track-level diagnostic and safety verification (`_check_track_spatial_safety()`), evaluating:
1. Physical track existence and section-track ownership consistency
2. Unidirectional track travel/work direction conformance
3. Adjacent-track possession containment (`FULL_TRAFFIC_BLOCK`) across temporally overlapping tasks and train movements
4. Adjacent-track caution order visibility (`CAUTION_ORDER`)
5. Spatial metadata completeness diagnostics (`SPATIAL_METADATA_INCOMPLETE`)

Crucially, this phase **strictly adheres to the safety-conservative architectural invariant**:
- Whole-section mutual exclusion (`SECTION_OCCUPANCY_CONFLICT`) and train clearance (`TRAIN_MOVEMENT_CONFLICT`) remain **100% authoritative hard safety barriers**.
- CP-SAT continues to schedule with whole-section mutual exclusion.
- Two activities occupying different tracks within the same section during overlapping intervals **still fail validation with `SECTION_OCCUPANCY_CONFLICT`** and **block plan approval**.
- Track-aware validation is **purely additive**: it catches track errors that whole-section validation would miss, but **never relaxes** whole-section conflicts.

---

## 2. Architectural Boundary & Separation of Concerns

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Rules Classify                                           │
│    - evaluate_spatial_compatibility()                       │
│    - Pure domain function, zero ORM/solver dependencies     │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Optimization Schedules                                   │
│    - CP-SAT Model Builder (Whole-section AddNoOverlap)      │
│    - Unchanged, track-unaware, safety-conservative          │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Independent Validator Verifies                           │
│    - Section checks: SECTION_OCCUPANCY_CONFLICT (ERROR)     │
│    - Train checks: TRAIN_MOVEMENT_CONFLICT (ERROR)          │
│    - Track check: _check_track_spatial_safety()             │
│      * INVALID_TRACK_ASSIGNMENT (ERROR)                     │
│      * TRACK_DIRECTION_CONFLICT (ERROR)                     │
│      * ADJACENT_TRACK_FULL_BLOCK (ERROR)                    │
│      * ADJACENT_TRACK_CAUTION_REQUIRED (INFO)               │
│      * SPATIAL_METADATA_INCOMPLETE (INFO)                   │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Human Reviews & Approves                                 │
│    - PlanVersion governance: is_approvable = (errors == 0)  │
│    - Human authority retained                               │
└─────────────────────────────────────────────────────────────┘
```

### Architectural Independence of the Validator
The Independent Schedule Validator must never trust or depend upon the scheduling engine or the compatibility engine:
- `ScheduleCheckRunner` directly imports the pure domain function `evaluate_spatial_compatibility` from `backend.app.domain.spatial_compatibility`.
- `ScheduleCheckRunner` **does not call** `CompatibilityEngine`.
- `ScheduleCheckRunner` **does not call** `CPSATModelBuilder` or `CPSATSolver`.
- Verified by unit tests with runtime monkeypatches raising errors if `CompatibilityEngine` or `CPSATSolver` is called.

---

## 3. Validator Safety Invariants Preserved

| Invariant | Status | Mechanism |
| :--- | :--- | :--- |
| **Whole-Section Mutex Authoritative** | Preserved | `_check_section_occupancy()` executes unconditionally; flags `SECTION_OCCUPANCY_CONFLICT` whenever two tasks overlap on the same section, regardless of track IDs. |
| **Train Clearance Mutex Authoritative** | Preserved | `_check_train_movements()` executes unconditionally; flags `TRAIN_MOVEMENT_CONFLICT` whenever a task overlaps with a train pass on the same section. |
| **CP-SAT Section-Level AddNoOverlap** | Unchanged | Solver maintains whole-section interval constraints. Zero track-based relaxation. |
| **Snapshot Identity & Hash** | Unchanged | `compute_snapshot_hash()` algorithm untouched. |
| **Schedule Identity & Hash** | Unchanged | `compute_schedule_identity()` algorithm untouched. |
| **Governance & Approval Gate** | Preserved | `valid = (len(errors) == 0)` and `is_approvable = valid`. Any `ERROR` blocks approval. |
| **Train Traversal Track ID** | Unassigned | `traversal_track_id` remains `None`. No heuristic track fabrication. |

---

## 4. Implementation Details

### 4.1. ValidationCategory.TRACK
Added `TRACK = "TRACK"` to `ValidationCategory` in `backend/app/services/validation/models.py`.

### 4.2. Diagnostic Codes & Severity Rules

| Finding Code | Category | Severity | Condition | Approval Impact |
| :--- | :--- | :--- | :--- | :--- |
| `INVALID_TRACK_ASSIGNMENT` | `TRACK` | `ERROR` | `track_id` does not exist in `snapshot.tracks_map` or belongs to a different section. | **Blocks Approval** |
| `TRACK_DIRECTION_CONFLICT` | `TRACK` | `ERROR` | Activity direction contradicts track's `supported_direction` (e.g. `DOWN` task on `UP` line). | **Blocks Approval** |
| `ADJACENT_TRACK_FULL_BLOCK` | `TRACK` | `ERROR` | Activity requires `FULL_TRAFFIC_BLOCK` on adjacent track, but another task or train pass is occupying that adjacent track simultaneously. | **Blocks Approval** |
| `ADJACENT_TRACK_CAUTION_REQUIRED` | `TRACK` | `INFO` | Activity requires `CAUTION_ORDER` on adjacent track during concurrent occupancy. Informs dispatchers of necessary speed restriction. | **Permits Approval** (Advisory) |
| `SPATIAL_METADATA_INCOMPLETE` | `TRACK` | `INFO` | Spatial occupants are concurrent on same section but missing track IDs or kilometrage bounds, leaving spatial clearance indeterminate. | **Permits Approval** (Advisory) |

### 4.3. Check Implementation: `_check_track_spatial_safety()`
Located in `backend/app/services/validation/checks.py`:
1. Registered in `run_all_checks()` immediately after `_check_train_movements()`, and added to `checks_executed` as `"TRACK_SPATIAL_SAFETY"`.
2. Inspects all scheduled tasks:
   - Verifies `task.track_id` exists in `snapshot.tracks_map` and matches `task.section_id`.
   - Validates task direction against track `supported_direction`.
3. Inspects all train movements, passes, and traversals:
   - Validates explicitly assigned track IDs against `snapshot.tracks_map`.
   - Validates movement direction against track `supported_direction`.
4. Evaluates pairwise temporal overlaps between tasks on adjacent tracks using `evaluate_spatial_compatibility()`:
   - `INCOMPATIBLE` $\rightarrow$ `ADJACENT_TRACK_FULL_BLOCK` (`ERROR`).
   - `COMPATIBLE_WITH_CONDITIONS` $\rightarrow$ `ADJACENT_TRACK_CAUTION_REQUIRED` (`INFO`).
   - `INSUFFICIENT_METADATA` $\rightarrow$ `SPATIAL_METADATA_INCOMPLETE` (`INFO`).
5. Evaluates temporal overlaps between scheduled tasks and train passes on adjacent tracks:
   - If task has `FULL_TRAFFIC_BLOCK` and train pass is on an adjacent track $\rightarrow$ `ADJACENT_TRACK_FULL_BLOCK` (`ERROR`).
   - If task has `CAUTION_ORDER` and train pass is on an adjacent track $\rightarrow$ `ADJACENT_TRACK_CAUTION_REQUIRED` (`INFO`).

---

## 5. Verification & Test Contracts

All 15 targeted test contracts implemented in `tests/unit/test_phase16g_c_validator.py` pass:

1. `test_invalid_task_track_id_produces_error`: Non-existent track ID produces `INVALID_TRACK_ASSIGNMENT` (`ERROR`).
2. `test_invalid_train_movement_track_id_produces_error`: Non-existent train track ID produces `INVALID_TRACK_ASSIGNMENT` (`ERROR`).
3. `test_valid_track_assignment_passes`: Consistent track assignment passes with 0 track errors.
4. `test_deterministic_direction_conflict_produces_error`: `DOWN` task on `UP` track produces `TRACK_DIRECTION_CONFLICT` (`ERROR`).
5. `test_full_traffic_block_against_adjacent_track_produces_error`: Overlapping task on adjacent track under `FULL_TRAFFIC_BLOCK` produces `ADJACENT_TRACK_FULL_BLOCK` (`ERROR`).
6. `test_full_traffic_block_does_not_fire_on_non_adjacent_tracks`: 3-track section where Track 1 and Track 3 are not adjacent does not produce adjacent block errors.
7. `test_caution_order_produces_info_not_error`: Concurrent adjacent occupancy with `CAUTION_ORDER` produces `ADJACENT_TRACK_CAUTION_REQUIRED` (`INFO`) and keeps `valid = True`, `is_approvable = True`.
8. `test_missing_adjacent_track_metadata_produces_info`: Missing track assignment produces `SPATIAL_METADATA_INCOMPLETE` (`INFO`), keeping `valid = True`.
9. `test_unresolved_traversal_track_validates_cleanly`: `TrainTraversal` with `traversal_track_id = None` validates without error.
10. `test_no_temporal_overlap_zero_spatial_conflicts`: Disjoint time intervals produce 0 spatial conflicts.
11. `test_different_tracks_do_not_bypass_section_occupancy_conflict`: Overlapping tasks on different tracks still trigger `SECTION_OCCUPANCY_CONFLICT`.
12. `test_section_occupancy_conflict_blocks_approval`: `SECTION_OCCUPANCY_CONFLICT` sets `valid = False` and `is_approvable = False`.
13. `test_existing_train_movement_conflict_still_blocks`: Train on different track still triggers `TRAIN_MOVEMENT_CONFLICT` and blocks approval.
14. `test_validator_does_not_call_compatibility_engine`: Validator executes independently of `CompatibilityEngine`.
15. `test_validator_does_not_call_cp_sat`: Validator executes independently of `CPSATSolver` and `CPSATModelBuilder`.

---

## 6. Limitations & Future Work

1. **Section Mutex Relaxation (Deferred to Future Phase)**:
   - Currently, tasks on different tracks in the same section cannot be scheduled concurrently because `SECTION_OCCUPANCY_CONFLICT` remains a hard error.
   - Any future relaxation must be paired with CP-SAT track-aware scheduling and proven safety invariants.
2. **Train Traversal Track Resolution**:
   - `TrainTraversal.traversal_track_id` remains `None`. In a future phase, route/switch topology could deterministically resolve traversal tracks.
3. **Kilometrage Buffer Modeling**:
   - Worksite kilometrage overlap (`from_km`, `to_km`) is evaluated by `evaluate_spatial_compatibility`, but longitudinal safety stopping margins remain uncalibrated demo constants.
