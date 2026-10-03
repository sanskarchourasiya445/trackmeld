# Phase 16G-A: Deterministic Track Spatial Compatibility Foundation

**Phase:** Phase 16G-A — Deterministic Track Spatial Compatibility Foundation  
**Status:** Implemented & Verified  
**Date:** 2026-10-04  
**Author:** AI Coding Agent (Antigravity)  
**Baseline Commit:** `a0bd998` (`feat(phase-16e): add deterministic train traversal expansion`)  
**Product Boundary:** Rules classify $\rightarrow$ Optimization schedules $\rightarrow$ Independent Validator verifies $\rightarrow$ Human reviews $\rightarrow$ Human approves. Decision support only; no autonomous dispatch, interlocking, signalling, or movement commands.

---

## 1. Executive Summary

Phase 16G-A implements the smallest deterministic domain foundation for track-aware spatial compatibility, directly answering the question:
> *"Given these two spatial occupants and the available track metadata, are they spatially compatible, incompatible, or insufficiently specified?"*

Crucially, this phase **does NOT make CP-SAT track-aware**. The existing whole-section scheduling mutex remains the active safety baseline. Optimization schedules; rules classify.

### What Was Delivered:
1. **Explicit Track Adjacency Representation:**
   - Added `adjacent_track_ids: Optional[List[str]]` to `TrackModel`, `Track` domain entity, `TrackResponse` API schema, and frontend `Track` interface.
   - Database migration `009_track_adjacency` (`f0a1b2c3d4e5`): Added JSON column to `tracks` table and seeded mutual adjacency for all 66 double-line sections (`UP_MAIN` $\leftrightarrow$ `DN_MAIN`) and explicit empty lists `[]` for single lines.
2. **Deterministic Spatial Compatibility Domain Models:**
   - Created [`backend/app/domain/spatial_compatibility.py`](file:///d:/Trackmeld/backend/app/domain/spatial_compatibility.py) defining:
     - `SpatialCompatibilityStatus`: `COMPATIBLE`, `INCOMPATIBLE`, `INSUFFICIENT_DATA`.
     - `SpatialCompatibilityReason`: 11 deterministic reason codes.
     - `SpatialOccupant`: Normalized occupant representation with factory methods (`from_task`, `from_train_pass`, `from_train_traversal`).
     - `TrackSpatialCompatibilityResult`: Structured outcome including `requires_caution_order` flag and diagnostic evidence.
3. **Deterministic Evaluation Engine:**
   - Implemented `evaluate_spatial_compatibility()` and exposed via `CompatibilityEngine.evaluate_spatial_compatibility()`.
   - Conservative missing-data handling: never assumes safety when metadata (track presence, adjacency, or adjacent-track impact) is missing.
4. **Preserved Invariants:**
   - Zero changes to CP-SAT `CPSATModelBuilder` conflict formulation.
   - Zero changes to Independent Schedule Validator `ScheduleCheckRunner` section occupancy checks.
   - Snapshot hash calculation (`compute_snapshot_hash()`) remains strictly identical.

---

## 2. Architecture Boundary & Invariants

```mermaid
flowchart TD
    subgraph ClassificationLayer ["1. Deterministic Rule Classification (Phase 16G-A)"]
        SO1[SpatialOccupant 1\nTask / Pass / Traversal]
        SO2[SpatialOccupant 2\nTask / Pass / Traversal]
        TM[Tracks Map\nExplicit adjacent_track_ids]
        EVAL[evaluate_spatial_compatibility]
        SO1 --> EVAL
        SO2 --> EVAL
        TM --> EVAL
        EVAL --> RES[TrackSpatialCompatibilityResult\nCOMPATIBLE | INCOMPATIBLE | INSUFFICIENT_DATA\n+ Deterministic Reason Code\n+ requires_caution_order]
    end

    subgraph SafetyBaseline ["2. Active Safety Baseline (Unchanged)"]
        CP[CP-SAT Model Builder\nWhole-Section Mutex AddNoOverlap]
        VAL[Independent Validator\nSECTION_OCCUPANCY_CONFLICT\nTRAIN_MOVEMENT_CONFLICT]
    end

    subgraph Governance ["3. Human Decision Layer (Unchanged)"]
        REV[Human Planner Review]
        APP[Human Authorization Approval]
        REV --> APP
    end

    classDef rule fill:#1e293b,stroke:#3b82f6,stroke-width:2px,color:#f8fafc;
    classDef safety fill:#0f172a,stroke:#eab308,stroke-width:2px,color:#f8fafc;
    classDef human fill:#0f172a,stroke:#22c55e,stroke-width:2px,color:#f8fafc;
    class SO1,SO2,TM,EVAL,RES rule;
    class CP,VAL safety;
    class REV,APP human;
```

---

## 3. Deterministic Spatial Compatibility Rules

When evaluating `occupant_1` and `occupant_2` against `tracks_map`, the rules execute in strict, deterministic order:

| Step | Rule Condition | Outcome Status | Outcome Reason | Operational Rationale |
|---|---|---|---|---|
| **1** | Half-open intervals $[t_1, t_2)$ do not overlap | `COMPATIBLE` | `NO_TEMPORAL_OVERLAP` | No temporal coexistence; physical occupancy does not collide. |
| **2** | Either occupant has `section_id = NULL` | `INSUFFICIENT_DATA` | `UNKNOWN_SECTION` | Section topology is not determined; cannot verify spatial isolation. |
| **3** | `occupant_1.section_id != occupant_2.section_id` | `COMPATIBLE` | `DIFFERENT_SECTIONS` | Activities are in physically separate block sections. |
| **4** | Either occupant has `track_id = NULL` | `INCOMPATIBLE` | `WHOLE_SECTION_OCCUPANCY` | An activity without specific track allocation occupies the entire section. |
| **5** | Either occupant's `track_id` not found in `tracks_map` | `INSUFFICIENT_DATA` | `MISSING_TRACK_METADATA` | Incomplete infrastructure inventory; conservative refusal to guess. |
| **6** | Direction mismatch on unidirectional track (e.g. DOWN on UP track) | `INCOMPATIBLE` | `DIRECTION_CONFLICT` | Prevents unauthorized wrong-line running. |
| **7** | `occupant_1.track_id == occupant_2.track_id` | `INCOMPATIBLE` | `SAME_TRACK_OVERLAP` | Two concurrent occupants on the same physical running line. |
| **8a** | `adjacent_track_ids` is `None` on either track | `INSUFFICIENT_DATA` | `MISSING_ADJACENCY_METADATA` | Physical layout / track separation distance unknown. |
| **8b** | Tracks are explicitly non-adjacent | `COMPATIBLE` | `DIFFERENT_TRACKS_INDEPENDENT` | Independent lines (e.g. separated by intermediate tracks or isolated loop lines). |
| **8c** | Adjacent + Task has `adjacent_track_impact = NULL` | `INSUFFICIENT_DATA` | `UNSPECIFIED_SPATIAL_RELATION` | Safety fouling risk of maintenance work has not been classified. |
| **8d** | Adjacent + Task has `FULL_TRAFFIC_BLOCK` | `INCOMPATIBLE` | `ADJACENT_TRACK_FULL_BLOCK` | Heavy on-track machinery or scaffolding fouls the structure gauge clearance. |
| **8e** | Adjacent + Task has `CAUTION_ORDER` | `COMPATIBLE` | `DIFFERENT_TRACKS_INDEPENDENT` (`requires_caution_order=True`) | Coexistence permitted with temporary speed restriction / whistle warning. |
| **8f** | Adjacent + `NONE` impact or trains on adjacent lines | `COMPATIBLE` | `DIFFERENT_TRACKS_INDEPENDENT` (`requires_caution_order=False`) | Standard independent running lines under clear structure gauge. |

---

## 4. Database & Persistence Layer

### Alembic Migration `009_track_adjacency` (`f0a1b2c3d4e5`):
- Added column: `tracks.adjacent_track_ids` (`JSON`, nullable).
- Seeded data:
  - 66 paired double-line tracks:
    - `TRK-{code}-UP.adjacent_track_ids = ["TRK-{code}-DN"]`
    - `TRK-{code}-DN.adjacent_track_ids = ["TRK-{code}-UP"]`
  - Single-line tracks:
    - `adjacent_track_ids = []` (explicitly isolated; no adjacent running lines).
- Verification:
  - Successfully applied via `alembic upgrade head`.
  - Database query confirmed all 132 tracks properly populated.

---

## 5. Verification & Test Evidence

### 1. New Unit Tests (`tests/unit/test_phase16g_a_spatial_compatibility.py`)
15 test cases covering 100% of defined rules:
- `test_disjoint_temporal_intervals_are_compatible` $\rightarrow$ PASS
- `test_different_sections_are_compatible` $\rightarrow$ PASS
- `test_missing_section_yields_insufficient_data` $\rightarrow$ PASS
- `test_whole_section_occupancy_is_incompatible` $\rightarrow$ PASS
- `test_missing_track_metadata_yields_insufficient_data` $\rightarrow$ PASS
- `test_same_track_overlap_is_incompatible` $\rightarrow$ PASS
- `test_direction_mismatch_is_incompatible` $\rightarrow$ PASS
- `test_bidirectional_track_allows_both_directions` $\rightarrow$ PASS
- `test_missing_adjacency_metadata_yields_insufficient_data` $\rightarrow$ PASS
- `test_non_adjacent_tracks_are_compatible_independently` $\rightarrow$ PASS
- `test_adjacent_tracks_full_traffic_block_is_incompatible` $\rightarrow$ PASS
- `test_adjacent_tracks_caution_order_is_compatible_with_flag` $\rightarrow$ PASS
- `test_adjacent_tracks_none_impact_is_compatible` $\rightarrow$ PASS
- `test_unspecified_task_adjacent_impact_yields_insufficient_data` $\rightarrow$ PASS
- `test_factory_constructors_and_repeated_evaluation` $\rightarrow$ PASS

### 2. Regression & Solver Invariant Test Suite
- `test_cp_sat_model.py`: 8 passed
- `test_cp_sat_solver.py`: 4 passed
- `test_phase7_validator.py`: 22 passed
- `test_phase16a_tracks.py`: 5 passed
- `test_phase16b_task_spatial.py`: 11 passed
- `test_phase16c_train_spatial.py`: 6 passed
- `test_phase16e_a_spatial_safety.py`: 5 passed
- `test_phase16e_b_traversal.py`: 5 passed
- **Total Unit Tests Run:** 81 passed in < 0.5s.

### 3. Integration Tests
- `test_phase16a_tracks_api.py`: 5 passed
- `test_phase16b_task_spatial_api.py`: 4 passed
- `test_phase16c_train_spatial_api.py`: 5 passed
- `test_phase16e_a_spatial_safety_api.py`: 5 passed
- `test_phase16e_b_traversal_api.py`: 4 passed
- **Total Integration Tests:** 23 passed in 4.10s.

### 4. Frontend Type & Build Verification
- `npm run build` executed Turbopack compilation and TypeScript check.
- Result: 0 errors; all static routes generated cleanly.

---

## 6. Files Created & Modified

| File | Status | Description |
|---|---|---|
| [`backend/alembic/versions/f0a1b2c3d4e5_009_track_adjacency.py`](file:///d:/Trackmeld/backend/alembic/versions/f0a1b2c3d4e5_009_track_adjacency.py) | Created | Alembic migration adding `adjacent_track_ids` JSON column and seeding double/single-line adjacency. |
| [`backend/app/domain/spatial_compatibility.py`](file:///d:/Trackmeld/backend/app/domain/spatial_compatibility.py) | Created | Core domain models (`SpatialOccupant`, `SpatialCompatibilityStatus`, `SpatialCompatibilityReason`, `TrackSpatialCompatibilityResult`, `evaluate_spatial_compatibility`). |
| [`backend/app/db/models/track.py`](file:///d:/Trackmeld/backend/app/db/models/track.py) | Modified | Added `adjacent_track_ids` mapped column. |
| [`backend/app/domain/sections.py`](file:///d:/Trackmeld/backend/app/domain/sections.py) | Modified | Added `adjacent_track_ids` to domain `Track` entity. |
| [`backend/app/domain/__init__.py`](file:///d:/Trackmeld/backend/app/domain/__init__.py) | Modified | Re-exported spatial compatibility domain symbols. |
| [`backend/app/schemas/responses.py`](file:///d:/Trackmeld/backend/app/schemas/responses.py) | Modified | Added `adjacent_track_ids` to `TrackResponse`. |
| [`backend/app/services/planning_service.py`](file:///d:/Trackmeld/backend/app/services/planning_service.py) | Modified | Propagated `adjacent_track_ids` in ScenarioPlanningBundle `tracks`. |
| [`backend/app/services/compatibility_service.py`](file:///d:/Trackmeld/backend/app/services/compatibility_service.py) | Modified | Added `CompatibilityEngine.evaluate_spatial_compatibility()` entry point. |
| [`frontend/src/types/railway.ts`](file:///d:/Trackmeld/frontend/src/types/railway.ts) | Modified | Added `adjacent_track_ids?: string[] \| null` to frontend `Track` interface. |
| [`tests/unit/test_phase16g_a_spatial_compatibility.py`](file:///d:/Trackmeld/tests/unit/test_phase16g_a_spatial_compatibility.py) | Created | 15 deterministic unit test cases covering all compatibility outcomes. |

---

## 7. Known Limitations & Next Steps

### Limitations:
1. **No Kilometrage Sub-Interval Adjacency:** Phase 16G-A checks adjacent track impact at the section level; sub-kilometrage worksite bounds $[km_{\text{start}}, km_{\text{end}}]$ are preserved in metadata but do not yet carve out localized sub-intervals.
2. **CP-SAT Remains Whole-Section:** The optimization solver continues scheduling with whole-section exclusivity. Track-aware coexistence is evaluated only via the classification engine.
3. **No Dynamic Train Runtime Expansion:** Caution order indicates diagnostic requirement for TSR, but train runtime math ($+4$ min delay) is not applied to train schedules.

### Recommendation for Phase 16G-B:
Expose spatial compatibility diagnostic reporting in the Planning API and frontend Entity Inspector so operators can visually inspect pairwise track compatibility and caution order requirements before solver track-relaxation is introduced.
