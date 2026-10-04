# Phase 18 — Track-Aware Validator Verification Report

**Phase:** Phase 18 — Track-Aware Validator Verification  
**Status:** COMPLETED  
**Baseline HEAD:** `4836dd3` (`feat(phase-17): add deterministic train route resolution`)  
**Commit:** `feat(phase-18): add track-aware validator verification`  
**Date:** October 2026  

---

## 1. Executive Summary

Phase 18 extends TrackMeld's **Independent Validator** (`backend/app/services/validation/checks.py`) to verify the physical spatial semantics introduced by Phase 16 infrastructure topology persistence and Phase 17 deterministic route resolution (`TrainTraversal.traversal_track_id`).

### The Safety Boundary
In strict accordance with the core TrackMeld architecture (**Rules classify. Optimization schedules. Humans approve. AI explains.**):
1. **Whole-Section Safety is Preserved:** Existing section-level occupancy checks (`_check_section_occupancy` emitting `SECTION_OCCUPANCY_CONFLICT` and `_check_train_movements` emitting `TRAIN_MOVEMENT_CONFLICT`) remain fully active and authoritative.
2. **CP-SAT Solver Unmodified:** No solver constraints, interval models, objective functions, or penalty formulations were modified in `backend/app/domain/solver/cp_sat_model.py`.
3. **Validator Independence Maintained:** The validator remains completely decoupled from the solver and planner:
   - Does **NOT** invoke `CompatibilityEngine` (pure rule classifier).
   - Does **NOT** invoke `DeterministicTopologyRouter` (route resolver).
   - Does **NOT** invoke `CP-SAT` or `PlanningScenarioService`.
   - Uses the pure domain spatial compatibility evaluator (`backend/app/domain/spatial_compatibility.py`) directly against static database snapshot data.
4. **Deterministic and Deduplicated:** Findings are ordered deterministically by `(category, rule_id, severity, section_id, track_id, entity_type, entity_id, message)` with pairwise finding deduplication.
5. **Governance Unmodified:** The validator only inspects and reports findings; it does not approve plans, modify `PlanVersion` status, or alter four-eyes approval controls.

---

## 2. Spatial Verification Architecture

The validator rule `TRACK_SPATIAL_SAFETY` verifies spatial compatibility and topology assignments across three layers of entities:

```
+-----------------------------------------------------------------------------------+
|                           Independent Validator Engine                            |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                         Rule: TRACK_SPATIAL_SAFETY                                |
+-----------------------------------------------------------------------------------+
       |                                  |                                 |
       v                                  v                                 v
[Scheduled Tasks Audit]        [Train Traversals Audit]       [Pairwise Spatial Check]
- Track existence              - Track existence              - Task <-> Task
- Section-Track alignment      - Section-Track alignment      - Task <-> TrainTraversal
- Track travel direction       - Travel direction vs Track    - Evaluates:
                               - Unresolved route diagnostics   * Same-track overlap
                               - Fabricated track detection     * Adjacent track block
                                                                * Adjacent caution
                                                                * Direction conflict
                                                                * Metadata completeness
```

### 2.1 Entity Integrity Checks

1. **Scheduled Tasks Integrity:**
   - If a task references a `track_id` that does not exist in the database $\to$ `INVALID_TRACK_ASSIGNMENT` (ERROR).
   - If a task references a `track_id` whose `section_id` does not match the task's assigned `section_id` $\to$ `INVALID_TRACK_ASSIGNMENT` (ERROR).
   - If a task has a travel direction incompatible with the physical track's allowed direction $\to$ `TRACK_DIRECTION_CONFLICT` (ERROR).

2. **Train Movements Integrity:**
   - If a scheduled train movement references an unknown track $\to$ `INVALID_TRACK_ASSIGNMENT` (ERROR).
   - If a train movement direction conflicts with track direction $\to$ `TRACK_DIRECTION_CONFLICT` (ERROR).

3. **Train Traversals & Route Integrity:**
   - Inspects `train_traversals` (with fallback to `train_passes`).
   - If a traversal route is unresolved (`traversal_track_id is None` or `resolution_status != RESOLVED`):
     - Logs `SPATIAL_METADATA_INCOMPLETE` (INFO) documenting the specific reason (e.g. `AMBIGUOUS_ROUTE`, `NO_CONTINUITY_CONNECTION`, `SECTION_NOT_CONNECTED`, `NO_TOPOLOGY_ENDPOINTS`).
   - If a traversal claims an unresolved or failed status but has a populated `traversal_track_id` (fabricated track assignment) $\to$ `INVALID_TRACK_ASSIGNMENT` (ERROR).
   - If a traversal has a `traversal_track_id` that does not exist in the database $\to$ `INVALID_TRACK_ASSIGNMENT` (ERROR).
   - If a traversal's track does not belong to the traversal's section $\to$ `INVALID_TRACK_ASSIGNMENT` (ERROR).
   - If the traversal direction violates the physical track direction $\to$ `TRACK_DIRECTION_CONFLICT` (ERROR).

---

## 3. Physical Spatial Compatibility Evaluation

Pairwise temporal overlaps in the same section are evaluated for spatial compatibility:

| Finding Code | Severity | Category | Trigger Condition |
| :--- | :--- | :--- | :--- |
| `SAME_TRACK_OVERLAP` | `ERROR` | `TRACK` | Two maintenance tasks, or a maintenance task and a train movement/traversal, occupy the same physical track simultaneously. |
| `ADJACENT_TRACK_FULL_BLOCK` | `ERROR` | `TRACK` | A task requiring a full adjacent-track block (`AdjacentTrackImpact.FULL_TRAFFIC_BLOCK` / `ADJACENT_TRACK_FOULING`) overlaps with another task or train on an adjacent physical track. |
| `ADJACENT_TRACK_CAUTION_REQUIRED` | `INFO` | `TRACK` | A task requiring a speed restriction or caution order (`AdjacentTrackImpact.SPEED_RESTRICTION` / `CAUTION_ORDER`) overlaps temporally on an adjacent physical track. |
| `TRACK_DIRECTION_CONFLICT` | `ERROR` | `TRACK` | A task or train movement runs against the authorized direction of travel for that physical running line. |
| `SPATIAL_METADATA_INCOMPLETE` | `INFO` | `TRACK` | Track assignment or adjacent track metadata is absent or unresolved, preventing physical separation verification. |
| `INVALID_TRACK_ASSIGNMENT` | `ERROR` | `TRACK` | Entity assigned to non-existent track, mismatched section track, or unresolvable route with fabricated track. |

### Diagnostic Separation: Different Tracks on Same Section
When two tasks or a task and a train operate in the same section at overlapping times on distinct, compatible running tracks (e.g. UP track vs DOWN track with `AdjacentTrackImpact.NONE`):
- `TRACK_SPATIAL_SAFETY` records **no error** (track-level separation is physically valid).
- `_check_section_occupancy` or `_check_train_movements` still records `SECTION_OCCUPANCY_CONFLICT` or `TRAIN_MOVEMENT_CONFLICT`.
- **Result:** The system accurately exposes the diagnostic distinction between track-level feasibility and whole-section corridor safety constraints without relaxing the safety baseline.

---

## 4. Verification & Testing

### 4.1 Unit Test Suite (`tests/unit/test_phase18_track_validator.py`)
14 comprehensive unit tests verifying all contracts:
- `test_track_spatial_safety_clean_passes`: Clean disjoint tasks pass without error.
- `test_track_spatial_safety_same_track_overlap_error`: Concurrent tasks on same track trigger `SAME_TRACK_OVERLAP` (ERROR).
- `test_track_spatial_safety_different_tracks_compatible`: Tasks on separate running lines pass track safety cleanly.
- `test_track_spatial_safety_adjacent_track_full_block_error`: Task requiring full adjacent block triggers `ADJACENT_TRACK_FULL_BLOCK` (ERROR).
- `test_track_spatial_safety_adjacent_track_caution_info`: Task requiring caution triggers `ADJACENT_TRACK_CAUTION_REQUIRED` (INFO).
- `test_track_spatial_safety_direction_conflict_error`: Movement against track direction triggers `TRACK_DIRECTION_CONFLICT` (ERROR).
- `test_track_spatial_safety_missing_track_info`: Missing track assignment triggers `SPATIAL_METADATA_INCOMPLETE` (INFO).
- `test_track_spatial_safety_invalid_track_id_error`: Unknown track ID triggers `INVALID_TRACK_ASSIGNMENT` (ERROR).
- `test_track_spatial_safety_track_section_mismatch_error`: Track belonging to another section triggers `INVALID_TRACK_ASSIGNMENT` (ERROR).
- `test_track_spatial_safety_train_traversal_same_track_overlap`: Task and train traversal on same track trigger `SAME_TRACK_OVERLAP` (ERROR).
- `test_track_spatial_safety_unresolved_traversal_route_info`: Unresolved route triggers `SPATIAL_METADATA_INCOMPLETE` (INFO).
- `test_track_spatial_safety_fabricated_track_on_unresolved_route_error`: Fabricated track on unresolved route triggers `INVALID_TRACK_ASSIGNMENT` (ERROR).
- `test_track_spatial_safety_deduplication`: Symmetric pairs produce single deduplicated finding.
- `test_track_spatial_safety_deterministic_sorting`: Findings follow deterministic multi-column sort key.

### 4.2 Integration Test Suite (`tests/integration/test_phase18_validator_integration.py`)
3 end-to-end integration tests using live database snapshots and validation APIs:
- `test_phase18_validator_track_spatial_safety_integration`: Validates generated plan snapshot passes validation pipeline.
- `test_phase18_validator_detects_unknown_track_in_snapshot`: Injected unknown track ID in plan snapshot triggers `INVALID_TRACK_ASSIGNMENT`.
- `test_phase18_validator_detects_same_track_overlap_on_tampered_schedule`: Tampered task duration causing same-track overlap triggers `SAME_TRACK_OVERLAP`.

### 4.3 Full Suite Test Results
- **Unit Tests:** 280 passed (100%).
- **Integration Tests:** 140 passed (100%).
- **Total Tests Passing:** 420 passed.

---

## 5. Architectural Boundaries Preserved

1. **CP-SAT Solver:** Zero modifications. `AddNoOverlap` remains section-wide.
2. **Approval & Governance:** `PlanGovernanceService` and `PlanVersion` status lifecycle unmodified.
3. **Decoupled Evaluator:** Validator performs direct evaluations without relying on solver state or router instances.
4. **Deterministic Findings:** All validation runs produce bit-for-bit identical diagnostic reports for identical snapshots.
