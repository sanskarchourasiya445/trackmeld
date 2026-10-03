# Phase 16E-B: Deterministic Train Traversal Expansion Report

**Phase:** 16E-B — Train Traversal Expansion  
**Status:** Completed & Verified  
**Date:** 2026-10-04  
**Author:** AI Coding Agent (Antigravity)  
**Baseline Commit:** `84f8aa5` (`feat(phase-16e): add spatial safety semantics foundation`)  

---

## 1. Executive Summary & Objective

In Indian Railways operations and spatial planning, a train's journey across a corridor involves three distinct levels of operational granularity:
1. **TrainMovement:** Timetable station stop or pass-through event with arrival/departure scheduled times and platform track assignments.
2. **TrainPass:** Continuous station-to-station operational interval $[t_{\text{dep\_A}}, t_{\text{arr\_B}})$ between consecutive timetable stops. Express trains regularly skip intermediate stations, causing a single station-to-station hop to span several physical block sections.
3. **TrainTraversal:** Explicit, ordered physical traversal of individual block sections, mapping exactly which section is occupied at which moment in time.

**Phase 16E-B objective:** Introduce deterministic train traversal expansion into TrackMeld's domain layer without modifying conservative whole-section CP-SAT scheduling conflict semantics or relaxing safety boundaries.

---

## 2. Core Architectural & Safety Boundaries

```
Rules classify → Optimization schedules → Independent Validator verifies → Human reviews → Human approves
```

- **Decision-Support Boundary Maintained:** TrackMeld generates advisory schedules and diagnostics only. It does NOT command signalling, dispatch, interlocking, or route locking.
- **Whole-Section Exclusivity Preserved:** CP-SAT solver and Independent Schedule Validator continue enforcing unrelaxed whole-section resource exclusivity. No per-track `AddNoOverlap` relaxation was introduced.
- **Snapshot Hash Invariance:** `PlanningSnapshot.compute_snapshot_hash()` remains 100% stable; traversals are derived domain objects and do not alter the authoritative input fingerprint.
- **No Track Assignment Fabrication:** `traversal_track_id` is explicitly set to `None` (unassigned) across all traversals, reflecting that sectional running track assignment requires route allocation and interlocking models scheduled for future phases.

---

## 3. Mathematical & Algorithmic Formulation

### 3.1 Topological Route Expansion
Given physical block sections $S = \{s_1, s_2, \dots, s_m\}$ with station endpoints $u_i, v_i$ and length $L_i$:
- A bidirectional topological graph $G = (V, E)$ is constructed where vertices are station IDs and edges are block sections with weight $L_i$.
- For adjacent stations directly linked by section $s$, traversal status is classified as `DIRECT_SECTION` ($n=1$).
- For non-adjacent station hops (express bypasses), Dijkstra's shortest path algorithm identifies the ordered linear chain of sections $P = \langle s_1, s_2, \dots, s_n \rangle$ connecting origin to destination.
- If endpoints are topologically disconnected, status is classified as `UNRESOLVED` with an explicit diagnostic reason without fabricating synthetic topology.

### 3.2 Proportional Transit Time Allocation
For an expanded route of $n$ sections over parent pass interval $[T_{\text{start}}, T_{\text{end}})$ with duration $\Delta T = T_{\text{end}} - T_{\text{start}}$:
$$\text{Total Length } L_{\text{total}} = \sum_{k=1}^n L_k$$
$$\text{Fractional Duration } \Delta t_k = \Delta T \times \frac{L_k}{L_{\text{total}}}$$

Intermediate timestamps are computed monotonically to avoid cumulative rounding drift:
$$t_0 = T_{\text{start}}$$
$$t_k = T_{\text{start}} + \sum_{j=1}^k \Delta t_j \quad (k = 1, \dots, n-1)$$
$$t_n = T_{\text{end}}$$

Each traversal interval $I_k = [t_{k-1}, t_k)$ satisfies:
1. Strict validity: $t_{k-1} < t_k$.
2. Strict adjacency: $I_k.\text{end} == I_{k+1}.\text{start}$.
3. Non-overlapping half-open semantics: $\max(t_{k-1}, t_k) \not< \min(t_k, t_{k+1})$.
4. Exact domain boundary conservation: $\sum_{k=1}^n \text{duration}(I_k) == \Delta T$.

---

## 4. Implementation Details

### 4.1 Backend Domain & Temporal Models
- **`backend/app/domain/enums.py`**:
  - Added `TraversalResolutionStatus` enum (`DIRECT_SECTION`, `EXPANDED_ROUTE`, `UNRESOLVED`).
- **`backend/app/domain/temporal.py`**:
  - Implemented `TrainTraversal` Pydantic model (`traversal_id`, `train_id`, `train_number`, `source_pass_id`, `section_id`, `from_station_id`, `to_station_id`, `sequence_order`, `interval`, `traversal_track_id`, `resolution_status`, `unresolved_reason`, `classification`).
  - Added properties `@entry_time`, `@exit_time`, and `@duration_minutes`.
- **`backend/app/domain/__init__.py`**:
  - Re-exported `TraversalResolutionStatus` and `TrainTraversal`.

### 4.2 Compatibility & Planning Services
- **`backend/app/services/compatibility_service.py`**:
  - Implemented `CompatibilityEngine.expand_train_traversals(train_passes, sections)` with graph pathfinding, tie-breaking determinism, and duration partitioning.
- **`backend/app/domain/planning_snapshot.py`**:
  - Added `train_traversals` and `train_traversals_map` to `PlanningSnapshot`.
  - Populated traversals in `PlanningSnapshot.from_bundle()` without altering `compute_snapshot_hash()`.
- **`backend/app/services/planning_service.py`**:
  - Added `train_traversals` to `ScenarioPlanningBundle`.
  - Derived and serialized traversals in `PlanningScenarioService.get_planning_bundle()`.

### 4.3 Schemas & REST APIs
- **`backend/app/schemas/responses.py`**:
  - Added `TrainTraversalResponse` Pydantic response schema.
- **`backend/app/schemas/operational_responses.py`**:
  - Added `train_traversals` to `ScenarioPlanningBundleResponse`.
- **`backend/app/api/v1/scenarios.py`**:
  - Added `GET /api/v1/scenarios/{scenario_id}/traversals` returning `List[TrainTraversalResponse]`.
  - Included `train_traversals` in `GET /api/v1/scenarios/{scenario_id}/bundle`.

### 4.4 Frontend UI & Railway Types
- **`frontend/src/types/railway.ts`**:
  - Added `TraversalResolutionStatus` and `TrainTraversal` interfaces.
  - Added `train_traversals?: TrainTraversal[]` to `ScenarioPlanningBundle`.
- **`frontend/src/components/planning/EntityInspector.tsx`**:
  - Added `traversals?: TrainTraversal[]` to `EntityInspectorProps`.
  - Rendered "Physical Section Traversals" panel in train inspector view showing sequence number, section code, origin/destination stations, timestamps, duration, and status badge (`DIRECT`, `EXPANDED`, `UNRESOLVED`).
- **`frontend/src/components/planning/TaskInspector.tsx`**:
  - Added `traversals?: TrainTraversal[]` and rendered physical route sections under the `TRAIN` tab.

---

## 5. Verification & Test Evidence

### 5.1 Unit Tests (`tests/unit/test_phase16e_b_traversal.py`)
- `test_adjacent_station_direct_section_expansion`: Passed.
- `test_multi_section_express_route_expansion`: Passed.
- `test_disconnected_station_yields_unresolved`: Passed.
- `test_snapshot_hash_stability_unaffected_by_traversals`: Passed.
- `test_express_cnb_to_ndls_corridor_expansion`: Passed (verified exact 8 ordered sections for Train 12301 from Kanpur to New Delhi).

### 5.2 Integration Tests (`tests/integration/test_phase16e_b_traversal_api.py`)
- `test_get_scenario_train_traversals`: Passed (HTTP 200, valid schema).
- `test_scenario_traversals_contain_expanded_routes`: Passed (contains both DIRECT and EXPANDED traversals).
- `test_scenario_bundle_includes_train_traversals`: Passed (HTTP 200, bundle includes traversals list).
- `test_get_traversals_nonexistent_scenario_404`: Passed (HTTP 404).

### 5.3 Full Regression Suite
- Ran `python -m pytest tests/unit tests/integration`:
  - **331 passed, 0 failed** in 39.31s.
- Ran frontend validations:
  - `npx tsc --noEmit`: 0 errors.
  - `npm run lint`: 0 errors.
  - `npm run build`: Compiled successfully in 2.7s with static generation.

---

## 6. Files Created and Modified

| File | Status | Description |
|---|---|---|
| `backend/app/domain/enums.py` | Modified | Added `TraversalResolutionStatus` enum |
| `backend/app/domain/temporal.py` | Modified | Added `TrainTraversal` model |
| `backend/app/domain/__init__.py` | Modified | Exported traversal domain models |
| `backend/app/domain/planning_snapshot.py` | Modified | Added `train_traversals` and `train_traversals_map` |
| `backend/app/services/compatibility_service.py` | Modified | Implemented `expand_train_traversals` route expansion |
| `backend/app/services/planning_service.py` | Modified | Derived and attached traversals to scenario bundle |
| `backend/app/schemas/responses.py` | Modified | Added `TrainTraversalResponse` schema |
| `backend/app/schemas/operational_responses.py` | Modified | Added `train_traversals` to bundle response |
| `backend/app/api/v1/scenarios.py` | Modified | Added `/{scenario_id}/traversals` endpoint |
| `backend/app/services/copilot/tools.py` | Modified | Hardened mock handling in `get_task_decision` |
| `frontend/src/types/railway.ts` | Modified | Added `TrainTraversal` frontend types |
| `frontend/src/components/planning/EntityInspector.tsx` | Modified | Displayed section traversals in train inspector |
| `frontend/src/components/planning/TaskInspector.tsx` | Modified | Displayed section traversals in TRAIN tab |
| `tests/unit/test_phase16e_b_traversal.py` | Created | Unit tests for traversal expansion |
| `tests/integration/test_phase16e_b_traversal_api.py` | Created | API integration tests for traversals |
| `tests/unit/test_auth.py` | Modified | Synchronized username assertion with config |

---

## 7. Next Phase Recommendation

Phase 16E-B provides the necessary spatial expansion of train movements into physical block sections.
**Recommendation:** Proceed to **Phase 16F: Track-Aware Scheduling Candidate Generation** (or Phase 16E-C / Phase 17 per project roadmap) only upon explicit confirmation.
TrackMeld remains decision support only.
