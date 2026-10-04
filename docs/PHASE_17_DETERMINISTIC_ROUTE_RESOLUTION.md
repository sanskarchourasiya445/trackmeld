# Phase 17 — Deterministic Route Resolution Report

**Phase:** Phase 17 — Deterministic Route Resolution  
**Status:** Completed & Verified  
**Baseline Git HEAD:** `da8ae42` (`feat(phase-16k): add curated demo topology connectivity`)  
**Branch:** `main`  
**Date:** October 2026  

---

## 1. Executive Summary

Phase 17 implements **deterministic railway route resolution**, translating abstract `TrainPass` intervals into physically resolved, track-specific `TrainTraversal` records (with populated `traversal_track_id`) using the explicit meso-level infrastructure topology models introduced in Phase 16I-C and the curated `DEMO_ONLY` topology fixture introduced in Phase 16K.

### Architectural Invariant Enforcement
1. **Separation of Concerns:** Route resolution is a pure spatial mapping service (`TrainPass` $\to$ physical route $\to$ ordered traversals $\to$ `traversal_track_id`). It does **NOT** schedule, optimize, or resolve resource contentions.
2. **CP-SAT Invariance:** The CP-SAT solver (`cp_sat_model.py`) and its interval non-overlap constraints (`AddNoOverlap`) were **NOT modified**.
3. **Validator Invariance:** The Independent Validator conflict detection engine (`checks.py`) was **NOT modified**.
4. **Snapshot Hash Stability:** `PlanningSnapshot.compute_snapshot_hash()` was **NOT modified** and remains 100% stable, guaranteeing identical deterministic input fingerprints for schedulers.
5. **No Synthetic Inference:** Zero topology was inferred from station adjacency, section ordering, track IDs, or naming conventions. Only explicit `TopologyNode`, `TrackEndpoint`, and `TopologyConnection` records are traversed.
6. **Ambiguity Safety:** When multiple valid physical paths exist through topology without authoritative dispatch priority, the system flags `AMBIGUOUS_ROUTE` and **strictly sets `traversal_track_id = None`**, refusing to fabricate track assignments.
7. **Safe Fallback:** Corridors lacking topology connections safely fall back to coarse section-level expansion (`traversal_track_id = None`) ensuring 100% backward compatibility.

---

## 2. Infrastructure Topology Consumption

Phase 17 consumes the explicit topology foundation delivered in Phase 16I-C and Phase 16K:
- **Curated Corridor Sections:**
  - `SEC-NDLS-GZB` (km 0.0 – 25.0, 2 tracks: `TRK-NDLS-GZB-DN`, `TRK-NDLS-GZB-UP`)
  - `SEC-GZB-KRJ` (km 25.0 – 95.0, 2 tracks: `TRK-GZB-KRJ-DN`, `TRK-GZB-KRJ-UP`)
  - `SEC-KRJ-ALJN` (km 95.0 – 126.0, 2 tracks: `TRK-KRJ-ALJN-DN`, `TRK-KRJ-ALJN-UP`)
- **Stations:** `STN-NDLS`, `STN-GZB`, `STN-KRJ`, `STN-ALJN`
- **Topology Nodes:**
  - `NODE-GZB-THROAT` (`STATION_THROAT`, km 25.0, `DEMO_ONLY`)
  - `NODE-KRJ-THROAT` (`STATION_THROAT`, km 95.0, `DEMO_ONLY`)
- **Topology Connections:**
  - `CONN-GZB-DN-THROUGH`: Continuity from `EP-TRK-NDLS-GZB-DN-END` to `EP-TRK-GZB-KRJ-DN-START` (`FORWARD`)
  - `CONN-GZB-UP-THROUGH`: Continuity from `EP-TRK-GZB-KRJ-UP-START` to `EP-TRK-NDLS-GZB-UP-END` (`FORWARD`)
  - `CONN-GZB-CROSSOVER-DN-UP`: Diverging crossover from `EP-TRK-NDLS-GZB-DN-END` to `EP-TRK-GZB-KRJ-UP-START` (`FORWARD`, 30 km/h)
  - `CONN-KRJ-DN-THROUGH`: Continuity from `EP-TRK-GZB-KRJ-DN-END` to `EP-TRK-KRJ-ALJN-DN-START` (`FORWARD`)
  - `CONN-KRJ-UP-THROUGH`: Continuity from `EP-TRK-KRJ-ALJN-UP-START` to `EP-TRK-GZB-KRJ-UP-END` (`FORWARD`)

---

## 3. Deterministic Routing Architecture

The core routing algorithm is implemented in `backend/app/services/topology_routing.py` via `DeterministicTopologyRouter`.

### 3.1 Algorithm Stages
```
TrainPass(from_stn, to_stn, interval)
       │
       ▼
Check Corridor Topology Coverage ──(No topology on corridor)──► Fallback to Section Expansion
       │                                                         (traversal_track_id = None)
       ▼ (Topology present)
Determine Travel Direction (DOWN / UP chainage)
       │
       ▼
Find Candidate Initial Tracks (Filter by direction compatibility)
       │
       ▼
Path Search across Explicit TopologyConnections
  ├─ Enforce connection traversal_direction (FORWARD, REVERSE, BIDIRECTIONAL)
  ├─ Enforce track direction compatibility (DOWN / UP / BIDIRECTIONAL)
  ├─ Loop detection (visited section set)
  └─ Sort connections and tracks deterministically
       │
       ▼
Evaluate Candidate Path Count:
  ├─ Count == 0:
  │    ├─ Paths exist ignoring direction ──► UNRESOLVED (DIRECTION_CONFLICT)
  │    └─ No paths exist ──────────────────► UNRESOLVED (DISCONNECTED_ROUTE)
  ├─ Count > 1:  ──────────────────────────► AMBIGUOUS_ROUTE (traversal_track_id = None)
  └─ Count == 1: ──────────────────────────► DIRECT_SECTION or EXPANDED_ROUTE
                                             (traversal_track_id = hop.track_id)
```

### 3.2 Direction Compatibility & Crossover Pruning
At `NODE-GZB-THROAT`, a DOWN train departing `TRK-NDLS-GZB-DN` encounters two candidate connections:
1. `CONN-GZB-DN-THROUGH` $\to$ `TRK-GZB-KRJ-DN` (`direction = DOWN`). Compatible with train direction (`DOWN == DOWN`).
2. `CONN-GZB-CROSSOVER-DN-UP` $\to$ `TRK-GZB-KRJ-UP` (`direction = UP`). Incompatible with train direction (`UP != DOWN`).

The router strictly prunes the crossover candidate path, yielding exactly 1 direction-compatible physical path (`CONN-GZB-DN-THROUGH`).

### 3.3 Multi-Route Ambiguity Detection
If `TRK-GZB-KRJ-UP` were configured as `BIDIRECTIONAL`, both paths would be physically valid and direction-compatible. Because TrackMeld does not possess authoritative dispatching priority rules for this turnout in synthetic demo space, the router detects `candidate_path_count == 2`, marks `resolution_status = AMBIGUOUS_ROUTE`, sets `unresolved_reason = "AMBIGUOUS_ROUTE: Multiple valid physical paths (2) found through topology without authoritative priority."`, and **strictly assigns `traversal_track_id = None`**.

---

## 4. Timing Proportions & Traversal Serialization

When an express train traverses multiple sections, the total pass duration $[t_{start}, t_{end})$ is partitioned across resolved hops proportionally by physical section distance ($km$), matching the Phase 16E-B timing standard:
$$\Delta t_i = D \times \frac{L_i}{\sum_{j} L_j}$$

Each hop is assigned a strict half-open interval $[s_i, e_i)$ with:
- $s_1 = t_{start}$
- $e_k = t_{end}$
- $e_i = s_{i+1}$ (adjacent, non-overlapping)
- `traversal_id = f"TRV-{train_number}-{section_id}-S{seq_idx}-{day_token}"`
- `traversal_track_id = hop.track_id`

---

## 5. Verification Results

### 5.1 Unit Tests (`tests/unit/test_phase17_route_resolution.py`)
10 tests executed and passed (0.09s):
1. `test_direct_single_section_resolution_down`: Verified `STN-NDLS` $\to$ `STN-GZB` resolves `TRK-NDLS-GZB-DN` (`DIRECT_SECTION`).
2. `test_direct_single_section_resolution_up`: Verified `STN-GZB` $\to$ `STN-NDLS` resolves `TRK-NDLS-GZB-UP` (`DIRECT_SECTION`).
3. `test_multi_section_express_down_resolution`: Verified `STN-NDLS` $\to$ `STN-ALJN` expands into 3 hops:
   - `SEC-NDLS-GZB`: `TRK-NDLS-GZB-DN`
   - `SEC-GZB-KRJ`: `TRK-GZB-KRJ-DN`
   - `SEC-KRJ-ALJN`: `TRK-KRJ-ALJN-DN`
4. `test_multi_section_express_up_resolution`: Verified `STN-ALJN` $\to$ `STN-NDLS` expands into 3 reverse hops:
   - `SEC-KRJ-ALJN`: `TRK-KRJ-ALJN-UP`
   - `SEC-GZB-KRJ`: `TRK-GZB-KRJ-UP`
   - `SEC-NDLS-GZB`: `TRK-NDLS-GZB-UP`
5. `test_crossover_direction_conflict_pruning`: Verified diverging crossover is pruned when conflicting with track direction.
6. `test_ambiguous_route_detection`: Verified multiple valid paths flag `AMBIGUOUS_ROUTE` with `traversal_track_id = None`.
7. `test_disconnected_topology_yields_unresolved`: Verified missing corridor connection returns `UNRESOLVED` (`DISCONNECTED_ROUTE`).
8. `test_permutation_invariance_and_determinism`: Verified 10 shuffled permutations of connections and tracks produce identical results.
9. `test_backward_compatibility_fallback_no_topology`: Verified corridors without topology preserve section-level expansion (`traversal_track_id = None`).
10. `test_snapshot_hash_stability_unaffected_by_phase17_routing`: Verified `PlanningSnapshot.compute_snapshot_hash()` remains identical.

### 5.2 Integration Tests (`tests/integration/test_phase17_route_resolution_api.py`)
3 tests executed and passed (1.03s against live PostgreSQL cluster):
1. `test_scenario_bundle_returns_topology_and_traversals`: Verified `GET /api/v1/scenarios/{id}/bundle` returns `tracks`, `train_traversals`, `topology_nodes`, `topology_connections`, and `track_endpoints`.
2. `test_scenario_traversals_api_endpoint`: Verified `GET /api/v1/scenarios/{id}/traversals` returns valid `TrainTraversalResponse` objects.
3. `test_corridor_scenario_resolves_physical_tracks`: Verified live database tasks on the curated corridor produce `traversal_track_id = 'TRK-GZB-KRJ-DN'` and `traversal_track_id = 'TRK-KRJ-ALJN-DN'` on Train 12004, while non-corridor section `SEC-ALJN-TDL` retains `traversal_track_id = None`.

### 5.3 Full Test Suite Regression
- **All Unit Tests:** 266 passed in 0.98s (`pytest tests/unit/`)
- **Topology & Traversal Integration Tests:** 22 passed in 3.81s (`pytest tests/integration/test_phase16* tests/integration/test_phase17*`)
- **Alembic Database Status:** Revision `b2c3d4e5f6a7` (`011_curated_demo_topology`) is current head.

---

## 6. Files Created & Modified

### Modified Application Source
- `backend/app/domain/enums.py`: Added `AMBIGUOUS_ROUTE = "AMBIGUOUS_ROUTE"` to `TraversalResolutionStatus`.
- `frontend/src/types/railway.ts`: Updated `TraversalResolutionStatus` TypeScript union type to include `'AMBIGUOUS_ROUTE'`.
- `backend/app/services/compatibility_service.py`: Updated `expand_train_traversals` to accept optional topology arguments, invoke `DeterministicTopologyRouter`, and resolve track IDs or fall back cleanly.
- `backend/app/services/planning_service.py`: Added topology query (`TrackEndpointModel`, `TopologyNodeModel`, `TopologyConnectionModel`) in `get_planning_bundle`, populated `ScenarioPlanningBundle`, and forwarded topology to `expand_train_traversals`.
- `backend/app/schemas/operational_responses.py`: Added optional `topology_nodes`, `topology_connections`, and `track_endpoints` fields to `ScenarioPlanningBundleResponse`.
- `backend/app/domain/planning_snapshot.py`: Added topology fields to `PlanningSnapshot` dataclass and forwarded topology from `bundle` to `expand_train_traversals` in `from_bundle` (preserving snapshot hash).
- `backend/app/api/v1/scenarios.py`: Forwarded topology fields from `bundle` to `ScenarioPlanningBundleResponse` in `get_scenario_bundle`.

### Created Source & Tests
- `backend/app/services/topology_routing.py`: Pure domain service implementing `DeterministicTopologyRouter`, `RouteResolutionResult`, and `ResolvedHop`.
- `tests/unit/test_phase17_route_resolution.py`: 10 comprehensive unit tests.
- `tests/integration/test_phase17_route_resolution_api.py`: 3 API and database integration tests.
- `docs/PHASE_17_DETERMINISTIC_ROUTE_RESOLUTION.md`: Architectural documentation and completion report.

---

## 7. Security and Domain Boundaries

- **Prototype Boundary:** TrackMeld remains an optimization and decision support prototype. Route resolution establishes physical track assignments from explicit infrastructure data; it does not replace operational interlocking or signalling.
- **Data Provenance:** All curated topology connections and nodes are explicitly labeled `classification = 'DEMO_ONLY'`.
- **Integrity Verification:** CP-SAT interval scheduling and the Independent Validator continue to enforce whole-section safety constraints. Route resolution does not weaken or bypass any scheduling or validation rules.
- **Read-Only Invariance:** Route resolution is deterministic, pure, and read-only. No live database writes occur during routing.
