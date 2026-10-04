# PHASE 16J — DETERMINISTIC TRAIN ROUTE & TRAVERSAL TRACK ASSIGNMENT DISCOVERY

**Document Type:** Architectural & Technical Discovery Report  
**Phase:** Phase 16J — Discovery Only  
**Date:** 2026-10-04  
**Baseline Git Commit:** `ce2e344` (Phase 16I-C baseline)  
**Status:** Complete  

---

## 1. Executive Summary

Phase 16J investigates how TrackMeld can deterministically transform high-level timetable train movements and station-to-station `TrainPass` intervals into physically verified, track-resolved `TrainTraversal` records using the meso-level infrastructure topology persisted in Phase 16I-C.

### Key Discoveries & Architectural Boundaries
1. **Current Route Expansion Status (`VERIFIED FROM CODE`):**
   In Phase 16E-B, `CompatibilityEngine.expand_train_traversals` introduced Dijkstra-based station-graph pathfinding across contiguous block sections. However, every resulting `TrainTraversal` currently sets `traversal_track_id = None`. Track assignment has remained intentionally unassigned to avoid unverified guessing.
2. **Current Baseline Topology State (`VERIFIED FROM CODE`):**
   Migration 010 (`a1b2c3d4e5f6_010_infrastructure_topology.py`) deterministically seeded **264 track endpoints** (exactly 1 `START` and 1 `END` per running track for all 132 tracks across 33 sections). Following the strict "honest zero-inferred connectivity policy", migration 010 seeded **0 topology nodes** and **0 topology connections**. Therefore, in the baseline dataset, physical track continuity across stations is currently completely disconnected.
3. **The Semantic Divide between Sections and Tracks (`VERIFIED FROM CODE`):**
   Sections represent macroscopic traffic blocks (from Station A to Station B). Tracks represent specific running lines within a section (`UP`, `DN`, `SL`). In multi-track sections, selecting a specific track cannot be inferred purely from station adjacency or track numbering.
4. **`TrainMovement.track_id` Limitations (`VERIFIED FROM CODE`):**
   Timetable occurrences in `TrainMovementModel` possess an optional `track_id` foreign key. However, this is populated for only 4 demo movements in migration 007 and represents an arrival or departure running track, not a complete multi-section traversal track sequence. Crucially, `TrainPass` drops `track_id` completely during pass derivation.
5. **Multiple Route Selection & Determinism (`INFERRED FROM CURRENT DESIGN`):**
   The repository does NOT possess authoritative train routing priority tables, route interlocking records, or train-class route preference rules. When multiple physical paths exist, selecting one based solely on heuristics (e.g., shortest length, lowest track ID, or query insertion order) violates railway domain safety. Unranked alternatives must yield `AMBIGUOUS_ROUTE`.
6. **CP-SAT & Validator Safety Invariant (`VERIFIED FROM CODE`):**
   Both CP-SAT (`cp_sat_model.py`) and the Independent Validator (`checks.py`) currently operate on whole-section exclusivity (`AddNoOverlap` and `SECTION_OCCUPANCY_CONFLICT`). Track-aware routing must remain an explanatory and diagnostic derivation; it must NOT prematurely relax whole-section safety barriers.

---

## 2. Current TrainPass / TrainTraversal Architecture

### 2.1 Entity Model Trace (`VERIFIED FROM CODE`)

The journey of train data flows through four distinct abstractions:

```
+------------------------------------+
|         TrainModel                 |  Canonical train definition
|  (train_id, train_number, type)    |  backend/app/db/models/train.py
+-----------------+------------------+
                  | 1:N
                  v
+------------------------------------+
|      TrainMovementModel            |  Timetable station stop/transit
|  (movement_id, station_id,         |  backend/app/db/models/movement.py
|   stop_seq, arr/dep, track_id)     |  backend/app/domain/movements.py
+-----------------+------------------+
                  | CompatibilityEngine.derive_train_passes()
                  v
+------------------------------------+
|          TrainPass                 |  Station-to-station timing interval
|  (pass_id, from_stn, to_stn,       |  backend/app/domain/temporal.py
|   interval, section_id=Optional)   |
+-----------------+------------------+
                  | CompatibilityEngine.expand_train_traversals()
                  v
+------------------------------------+
|        TrainTraversal              |  Physical block section traversal
|  (traversal_id, section_id,        |  backend/app/domain/temporal.py
|   interval, traversal_track_id)    |
+------------------------------------+
```

### 2.2 Precise Code Tracing (`VERIFIED FROM CODE`)

1. **`TrainPass` Construction:**
   - **Location:** `CompatibilityEngine.derive_train_passes` in `backend/app/services/compatibility_service.py:38-154`.
   - **Mechanism:** Chronologically sorts movements for each `train_id` by `stop_sequence`. For each consecutive pair $(m_i, m_{i+1})$, checks `sec_lookup[(curr_stn, next_stn)]`.
   - **`section_id` Assignment:** If `curr_stn` and `next_stn` are directly connected by a known section, `TrainPass.section_id` is populated and `movement_type = "SECTION_TRAVERSAL"`. If the train skips stations (express hop), `section_id = None` and `movement_type = "STATION_HOP"`.
   - **`track_id` Handling:** Neither `curr_mov.track_id` nor `next_mov.track_id` is copied into `TrainPass`. `TrainPass` only stores `source_movement_ids=[curr_mov_id, next_mov_id]`.

2. **`TrainTraversal` Construction:**
   - **Location:** `CompatibilityEngine.expand_train_traversals` in `backend/app/services/compatibility_service.py:157-330`.
   - **Cases Handled:**
     - **Case A (Dwell / Zero-distance):** `from_stn == to_stn` -> `traversal_track_id = None`, `resolution_status = DIRECT_SECTION` if `section_id` else `UNRESOLVED`.
     - **Case B (Direct Section):** `(from_stn, to_stn) in direct_lookup` -> creates 1 traversal, `section_id = sec_id`, `traversal_track_id = None`, `resolution_status = DIRECT_SECTION`.
     - **Case C (Expanded Route Hop):** Express hop -> calls `find_section_path(from_stn, to_stn)` using Dijkstra shortest path over `sections.length_km`. Slices `pass.interval` proportionally by hop length. For each hop: `traversal_track_id = None`, `resolution_status = EXPANDED_ROUTE`.
     - **Case D (Unresolved):** Disconnected stations -> `section_id = None`, `traversal_track_id = None`, `resolution_status = UNRESOLVED`.

3. **Current Consumers of `TrainTraversal` (`VERIFIED FROM CODE`):**
   - `backend/app/domain/planning_snapshot.py:177`: `PlanningSnapshot.from_bundle()` invokes `expand_train_traversals()` and stores `snapshot.train_traversals` and `snapshot.train_traversals_map`.
   - `backend/app/services/planning_service.py:188`: `get_planning_bundle()` populates `bundle.train_traversals`.
   - `backend/app/api/v1/scenarios.py:134`: `GET /api/v1/scenarios/{scenario_id}/train-traversals` returns serialized `TrainTraversalResponse`.
   - `backend/app/domain/spatial_compatibility.py:138`: `SpatialOccupant.from_train_traversal()` adapts a `TrainTraversal` into a `SpatialOccupant`.
   - `frontend/src/types/railway.ts:92`: TypeScript interface for frontend scenario bundle visualization.

---

## 3. Phase 16I Topology Architecture

### 3.1 Entities and Constraints (`VERIFIED FROM CODE`)

Phase 16I-C introduced three relational and domain entities in `backend/app/domain/topology.py` and `backend/app/db/models/topology.py`:

```
+--------------------------------------------------------------+
|                        TopologyNode                          |
|  node_id: VARCHAR(64) [PK]                                   |
|  node_name: VARCHAR(128)                                     |
|  station_id: VARCHAR(32) [FK -> stations, NULLABLE]          |
|  node_type: BOUNDARY_JOINT | STATION_THROAT | CROSSOVER_...   |
|  classification: VERIFIED_SOURCE | ASSUMPTION | DEMO_ONLY    |
|  source_id: VARCHAR(64) [FK -> source_documents]             |
+------------------------------+-------------------------------+
                               | 1:N
                               v
+--------------------------------------------------------------+
|                     TopologyConnection                       |
|  connection_id: VARCHAR(64) [PK]                             |
|  node_id: VARCHAR(64) [FK -> topology_nodes]                 |
|  from_endpoint_id: VARCHAR(64) [FK -> track_endpoints]       |
|  to_endpoint_id: VARCHAR(64) [FK -> track_endpoints]         |
|  connection_type: CONTINUITY | TURNOUT_NORMAL | ...          |
|  traversal_direction: FORWARD | REVERSE | BIDIRECTIONAL      |
|  max_diverging_speed_kmh: INTEGER [NULLABLE]                 |
|  classification: DEMO_ONLY | ...                             |
|  CHECK: from_endpoint_id != to_endpoint_id                   |
|  UNIQUE: (from_endpoint_id, to_endpoint_id)                  |
+-------------------+----------------------+-------------------+
                    |                      |
                    | FK                   | FK
                    v                      v
+--------------------------------------------------------------+
|                        TrackEndpoint                         |
|  endpoint_id: VARCHAR(64) [PK] (e.g. EP-TRK-NDLS-GZB-UP-START)
|  track_id: VARCHAR(64) [FK -> tracks]                        |
|  endpoint_type: START | END                                  |
|  kilometrage: FLOAT (matching section start_km / end_km)     |
|  UNIQUE: (track_id, endpoint_type)                           |
+--------------------------------------------------------------+
```

### 3.2 Conceptual Boundaries (`VERIFIED FROM CODE`)

The architecture strictly distinguishes five concepts that must never be conflated:

| Concept | Scope | Stored In | Semantic Role |
| :--- | :--- | :--- | :--- |
| **A. Track Adjacency** | Lateral physical proximity | `tracks.adjacent_track_ids` | Safety clearances, caution orders, simultaneous possession rules. |
| **B. Longitudinal Continuity** | Direct end-to-end rail alignment | `TopologyConnection` (`CONTINUITY`) | Physical capability of rolling stock to proceed into the next section track without diverging. |
| **C. Topology Connectivity** | Network rail path | `TopologyConnection` (all types) | Graph edge connecting two track boundary ports across a node. |
| **D. Route Selection** | Operational train path | Future Router / Interlocking | Choosing *which* valid topological path a specific train service traverses. |
| **E. Scheduling Occupancy** | Temporal reservation | `TrainPass` / `TrainTraversal` / CP-SAT | Reserving physical infrastructure during a time interval $[t_{start}, t_{end})$. |

---

## 4. Verified Data Flow

The complete data pipeline from timetable ingestion to planning and validation:

```
[ Timetable CSV / DB ]
         │
         ▼
[ TrainMovementModel ] ────(movement_id, stop_seq, arr, dep, track_id)
         │
         ▼ CompatibilityEngine.derive_train_passes()
[ TrainPass ] ────────────(pass_id, from_stn, to_stn, [t_start, t_end), section_id)
         │                 (NOTE: track_id is NOT propagated here!)
         │
         ├───► Passed to [ PlanningSnapshot.train_passes ]
         │            │
         │            ├───► Consumed by [ CP-SAT Solver (cp_sat_model.py) ]
         │            │        (Whole-section AddNoOverlap)
         │            │
         │            └───► Consumed by [ Independent Validator (checks.py) ]
         │                     (_check_train_movements whole-section collision)
         │
         ▼ CompatibilityEngine.expand_train_traversals()
[ TrainTraversal ] ───────(traversal_id, section_id, sequence_order, interval,
         │                 traversal_track_id=None, resolution_status)
         │
         ├───► Stored in [ PlanningSnapshot.train_traversals ] (Diagnostic only)
         │
         ├───► Exposed via [ GET /api/v1/scenarios/{id}/train-traversals ]
         │
         └───► Consumed by [ SpatialOccupant.from_train_traversal() ] (Diagnostic)
```

**Critical Architectural Fact:**  
Neither CP-SAT nor the Independent Validator's hard conflict checks consume `TrainTraversal` or `traversal_track_id`. Both currently rely exclusively on `TrainPass.section_id` and whole-section intervals.

---

## 5. `TrainMovement.track_id` Semantics

### 5.1 What Does `TrainMovement.track_id` Represent? (`VERIFIED FROM CODE`)

In `backend/app/db/models/movement.py`:
```python
track_id: Mapped[Optional[str]] = mapped_column(
    String(64),
    ForeignKey("tracks.track_id", ondelete="SET NULL"),
    nullable=True,
    index=True,
)
```

1. **Foreign Key Target:** Points to `tracks.track_id`. In TrackMeld, all `tracks` belong to block sections (`tracks.section_id`), NOT stations.
2. **Current Database Values:**
   In migration 007 (`d8a2b3c4e5f6_007_train_movement_track_semantics.py`), exactly 4 demo timetable records were assigned track IDs:
   - `MOV-12301-NDLS-09` (UP Rajdhani arrival at NDLS): assigned `TRK-NDLS-GZB-UP` (section `SEC-NDLS-GZB`).
   - `MOV-12302-NDLS-01` (DN Rajdhani departure from NDLS): assigned `TRK-NDLS-GZB-DN` (section `SEC-NDLS-GZB`).
   - `MOV-12301-CNB-08` (UP Rajdhani stop at CNB): assigned `TRK-ETW-CNB-UP` (section `SEC-ETW-CNB`).
   - `MOV-12302-CNB-02` (DN Rajdhani stop at CNB): assigned `TRK-ETW-CNB-DN` (section `SEC-ETW-CNB`).
3. **Semantic Inconsistency:**
   A timetable movement represents an event at a **station** (`station_id`). But `track_id` points to a track in an **adjacent section**.
   For an intermediate station like CNB (which sits between `SEC-ETW-CNB` and `SEC-CNB-PRYJ`), a single `track_id` on the movement cannot represent both the arrival track from ETW and the departure track to PRYJ.
4. **Conclusion for Routing:**
   `TrainMovement.track_id` is an incomplete and station-centric hint. It cannot be treated as an authoritative specification of track occupancy across the entire corridor.

---

## 6. Direction Semantics

### 6.1 Direction Representation Across the Repository (`VERIFIED FROM CODE`)

| Domain Entity | Direction Field | Allowed Values | Semantic Meaning |
| :--- | :--- | :--- | :--- |
| `TrackModel` | `direction` | `UP`, `DOWN`, `BIDIRECTIONAL` | Permitted traffic flow along the running track. |
| `SectionModel` | `direction` | `UP`, `DOWN`, `BIDIRECTIONAL` | Default corridor flow (or inferred from track count). |
| `TopologyConnection` | `traversal_direction` | `FORWARD`, `REVERSE`, `BIDIRECTIONAL` | Permitted traversal from `from_endpoint_id` to `to_endpoint_id`. |
| `TrainModel` | *None* | N/A | Direction is NOT stored on the train record. |
| `TrainMovement` | *None* | N/A | Direction is NOT stored on the movement record. |
| `TrainPass` | *None* | N/A | Inferred solely from `from_station_id -> to_station_id`. |
| `TrainTraversal` | *None* | N/A | Inferred solely from `from_station_id -> to_station_id`. |
| `SpatialOccupant` | `direction` | `UP`, `DOWN`, `None` | Used by `spatial_compatibility.py` for direction compatibility. |

### 6.2 Direction Mapping & Contradictions (`INFERRED FROM CURRENT DESIGN`)

1. **Station Ordering vs Railway Direction:**
   - In Indian Railways, `UP` generally denotes movements towards a designated administrative/corridor origin (e.g. towards NDLS/HWH), and `DOWN` denotes movements away.
   - However, in `SectionModel`, `from_station_id` and `to_station_id` are fixed in the database schema (e.g., `from_station_id = "STN-NDLS"`, `to_station_id = "STN-GZB"`).
   - A train traveling from NDLS to GZB moves in the direction `from_station -> to_station` (increasing kilometrage). A train traveling from GZB to NDLS moves `to_station -> from_station` (decreasing kilometrage).
2. **Endpoint Semantics:**
   - Migration 010 created `EP-{track_id}-START` at `kilometrage_start` (`from_station`) and `EP-{track_id}-END` at `kilometrage_end` (`to_station`).
   - A train traveling from NDLS to GZB enters at `START` and exits at `END`.
   - A train traveling from GZB to NDLS enters at `END` and exits at `START`.
3. **Connection `FORWARD` vs `REVERSE`:**
   - In `TopologyConnection`, `from_endpoint_id` and `to_endpoint_id` are specific boundary ports.
   - If a connection links `EP-TRK-SEC1-END` to `EP-TRK-SEC2-START`, a movement traversing from SEC1 to SEC2 follows `from_endpoint -> to_endpoint` (`FORWARD`).
   - If a movement traverses from SEC2 to SEC1, it enters at `to_endpoint` and exits at `from_endpoint` (`REVERSE`). If `traversal_direction` is `FORWARD`, this reverse move is prohibited.

---

## 7. Route Resolution Capability Matrix

Assessment of what train routing scenarios can be resolved today versus what requires additional topology data:

| Traversal Scenario | Current Resolution Status | Blocking Data / Rule Gap |
| :--- | :--- | :--- |
| **A. Direct adjacent-station movement (Single track section)** | **Partially Resolvable** | Resolvable if section has exactly 1 track (`track_count=1`, `TRK-xxx-SL`). Unambiguous track selection. |
| **B. Direct adjacent-station movement (Double/multi-track section)** | **Unresolved** | No authoritative rule to select between `UP_MAIN` and `DN_MAIN` when `TrainMovement.track_id` is null. |
| **C. Multi-section express movement** | **Unresolved (at track level)** | Section path is resolved via Dijkstra, but zero track continuity connections exist between sections. |
| **D. Bidirectional running on single line** | **Partially Resolvable** | Track is unique (`SL`), but requires dynamic opposing train clearance check. |
| **E. Reverse traversal on unidirectional track** | **Resolvable as Prohibited** | Track direction check (`ck_tracks_direction_valid`) correctly identifies directional violation. |
| **F. Multiple candidate paths (e.g. main vs loop line)** | **Unresolved / Unsafe to Infer** | No route priority or interlocking preference rules exist in the repository. |
| **G. Disconnected topology (Base dataset)** | **Unresolved (`NO_TOPOLOGY`)** | Migration 010 seeded 0 connections. All routing must truthfully return `NO_TOPOLOGY`. |
| **H. Incomplete topology (Partial station throats)** | **Unresolved (`INCOMPLETE_TOPOLOGY`)** | Cannot route through a junction if throat nodes are missing. |
| **I. Crossover / Turnout alternatives** | **Unresolved / Unsafe to Infer** | Requires signaling route setting or dispatcher decision rules. |

---

## 8. Multi-Route Resolution Analysis

### 8.1 Candidate Ranking Signals Evaluated (`VERIFIED FROM CODE` & `NOT REPRESENTED IN CURRENT DATA`)

| Candidate Signal | Availability in Repository | Nature of Data | Can be used as Authoritative Routing Rule? |
| :--- | :--- | :--- | :--- |
| **Section Length (`length_km`)** | Available | Geometric metadata | **NO.** Shortest distance does not reflect platforming, line rules, or operational routing. |
| **Section Count** | Available | Graph metric | **NO.** Fewest sections does not dictate railway route clearance. |
| **Topology Connection Type** | Available | Geometry category (`CONTINUITY`, `TURNOUT`) | **PARTIALLY.** Straight (`CONTINUITY`) is preferred over turnout, but not sufficient to resolve route choice. |
| **Maximum Speed (`max_speed_kmh`)** | Available | Technical rating | **NO.** Trains do not always take the highest speed line (e.g. stopping trains must take platform loops). |
| **Scheduled Movement `track_id`** | Sparse (4 records) | Timetable hint | **NO.** Missing for >95% of movements; only covers single station events. |
| **Train Direction (`UP` / `DOWN`)** | Inferred from route | Timetable characteristic | **YES (as feasibility filter).** UP trains must not use DOWN unidirectional tracks. |
| **Explicit Route Priority** | **ABSENT** | Operational rule | **N/A.** Does not exist in the database. |

### 8.2 The Ambiguity Rule

> **CRITICAL RULE:**  
> If multiple physically connected paths exist through topology, and no authoritative domain rule or timetable constraint dictates which line the train is authorized to take, the system **MUST NOT** silently choose a route based on database row order, string comparison of track IDs, or shortest distance.  
> The system must classify the route as `AMBIGUOUS_ROUTE` and leave `traversal_track_id = None`.

---

## 9. Express / Multi-Section Routing Analysis

### 9.1 How Phase 16E-B Works Today (`VERIFIED FROM CODE`)

In `backend/app/services/compatibility_service.py:171-216`:
1. Constructs station adjacency graph `adj: Dict[str, List[Tuple[neighbor, sec_id, length_km]]]`.
2. For express passes (e.g. `PASS-12301-CNB-NDLS`), runs Dijkstra's algorithm to find the shortest contiguous sequence of sections connecting the two stations.
3. Partitions the total pass duration proportionally:
   $$\Delta t_k = \text{total\_duration} \times \frac{\text{length}_k}{\sum \text{length}}$$
4. Generates ordered `TrainTraversal` records for each intermediate section with `sequence_order = 1, 2, \dots, N`.

### 9.2 Risks of Coexisting Station-Graph Routing with Topology Routing (`INFERRED FROM CURRENT DESIGN`)

1. **Topological Disconnect:** Station-graph routing guarantees section adjacency, but DOES NOT guarantee track continuity. For example, Section 1 may terminate on Track UP-1, but the only turnout at the intermediate station throat may lead to Track DN-2.
2. **Proportional Timing Slicing vs Real Transit:** Slicing pass duration strictly by `length_km` ignores acceleration, deceleration, signal aspects, and turnout speed limits (`max_diverging_speed_kmh`).
3. **Architectural Recommendation:**
   Station-graph routing should serve as a **coarse corridor corridor guide (Meso Level 1)** to determine the sequence of block sections. Topology routing should then serve as the **physical line verifier (Meso Level 2)** that checks whether contiguous track connections exist along that sequence. If track connections do not exist, the traversal remains at the section level (`traversal_track_id = None`).

---

## 10. Deterministic Routing Requirements

To achieve repeatable, deterministic route resolution:

1. **Strict Ordering of Database Queries:**  
   All queries for endpoints, nodes, and connections must specify deterministic `ORDER BY` clauses (e.g. `ORDER BY connection_id ASC`).
2. **Deterministic Priority Tuples:**  
   When traversing topology connections at a node, candidate connections must be evaluated in a deterministic order:
   $$\text{Candidate Sort Key} = (\text{connection\_type\_rank}, \text{diverging\_speed\_desc}, \text{to\_endpoint\_id})$$
   Where `connection_type_rank`: `CONTINUITY = 1`, `TURNOUT_NORMAL = 2`, `TURNOUT_REVERSE = 3`, `CROSSOVER = 4`.
3. **No Dynamic State Guessing:**  
   The router must NOT guess turnout positions. Turnouts represent physical connections. If multiple connections lead out of an endpoint, an authoritative selection rule must be supplied.

---

## 11. Failure / Unresolved State Taxonomy

A formal, deterministic taxonomy of traversal resolution failure states:

| Failure Code | Severity | Description | System Action |
| :--- | :--- | :--- | :--- |
| `NO_TOPOLOGY` | Expected Baseline | No topology nodes or connections exist in the database for the traversed section/station. | Fall back to whole-section traversal (`traversal_track_id = None`). |
| `DISCONNECTED_ROUTE` | Data Gap | Endpoints exist, but no sequence of connections connects origin to destination. | Keep `traversal_track_id = None`, flag diagnostic. |
| `AMBIGUOUS_ROUTE` | Domain Indeterminate | Multiple valid physical paths exist with equal or unranked priority. | Keep `traversal_track_id = None`, record candidate track IDs in diagnostics. |
| `DIRECTION_CONFLICT` | Safety Invalidation | The physical track or connection prohibits traversal in the train's travel direction. | Route rejected; traversal fails validation. |
| `INVALID_ENDPOINT` | Structural Error | A connection references an endpoint ID that does not exist in `track_endpoints`. | Database integrity error. |
| `INVALID_CONNECTION` | Structural Error | A connection links an endpoint to itself or crosses non-adjacent nodes. | Rejected by model validation / check constraint. |
| `INCOMPLETE_TOPOLOGY` | Partial Data | Some sections in the path have track-level topology while intermediate nodes are missing. | Fall back to section-level for missing segments. |
| `CONFLICTING_TRACK_ASSIGNMENT` | Timetable Conflict | Timetable `TrainMovement.track_id` does not match the topologically valid track. | Flag diagnostic mismatch between timetable and topology. |

---

## 12. Snapshot & Cryptographic Hash Impact

### 12.1 Current Snapshot Hash Inspection (`VERIFIED FROM CODE`)

In `backend/app/domain/planning_snapshot.py:45-67`:
```python
def compute_snapshot_hash(self) -> str:
    hasher = hashlib.sha256()
    hasher.update(self.scenario_id.encode("utf-8"))
    hasher.update(self.horizon.start.isoformat().encode("utf-8"))
    hasher.update(self.horizon.end.isoformat().encode("utf-8"))
    # Hashes sorted task records: (task_id, w_start, w_end, dur, sec)
    hasher.update(json.dumps(task_records, sort_keys=True).encode("utf-8"))
    hasher.update(str(len(self.train_passes)).encode("utf-8"))
    hasher.update(str(len(self.resources)).encode("utf-8"))
    hasher.update(str(len(self.dependencies)).encode("utf-8"))
    return hasher.hexdigest()
```

### 12.2 Classification of Routing Inputs

| Future Routing Element | Classification Category | Rationale |
| :--- | :--- | :--- |
| **`topology_nodes` / `topology_connections`** | **D. Requires Hash-Versioning** | If topology determines whether a plan is feasible or alters track occupancy, changes to connections alter planning inputs. Adding them to `snapshot_hash` must be gated by a snapshot schema version increment. |
| **`TrackEndpoint` records** | **B. Derived & Reproducible** | Endpoints are deterministically generated from track chainage. |
| **`TrainTraversal.traversal_track_id`** | **B. Derived & Reproducible** | Derived deterministically by the router from `TrainPass` + topology. Does not need to be in the input hash. |
| **`resolution_status` & `unresolved_reason`** | **C. Descriptive Metadata** | Diagnostic metadata explaining the derivation; does not alter input truth. |
| **`TopologyConnection.classification`** | **C. Descriptive Metadata** | Provenance marker (`VERIFIED_SOURCE` vs `DEMO_ONLY`). |

---

## 13. Independent Validator Requirements

To maintain TrackMeld's core architectural principle (**"Rules classify -> Optimization schedules -> Independent Validator verifies"**), a future validator must be capable of verifying route assignments independently:

1. **No Dependency on Router or Solver:**  
   The validator must NOT invoke `CompatibilityEngine` or CP-SAT.
2. **Pure Domain Verification Contract:**  
   A dedicated check function in `backend/app/services/validation/checks.py`:
   ```python
   def _check_train_traversal_topology(self) -> None:
       """Independently verify that every assigned traversal_track_id is physically valid."""
       for trv in self.snapshot.train_traversals:
           if trv.traversal_track_id is None:
               continue  # Whole-section fallback, verified by existing section checks
           
           # 1. Track belongs to section
           track = self.snapshot.tracks_map.get(trv.traversal_track_id)
           if not track or track.section_id != trv.section_id:
               self.findings.append(Finding(...))
           
           # 2. Track direction compatibility
           if not is_track_direction_compatible(track.direction, trv.direction):
               self.findings.append(Finding(...))
   ```
3. **Continuity Verification for Multi-Section Traversals:**  
   For consecutive traversals $T_k$ and $T_{k+1}$ of the same train:
   - Check that an explicit `TopologyConnection` exists from $T_k$'s exit endpoint to $T_{k+1}$'s entry endpoint.
   - Verify connection direction permits traversal.

---

## 14. CP-SAT Optimization Boundary

### 14.1 Separation of Concerns

```
+------------------------------------+
|          TOPOLOGY ROUTER           |  DETERMINES PHYSICAL PATH
|  - Validates rail continuity       |  Input: TrainPass + Topology
|  - Assigns traversal_track_id      |  Output: TrainTraversal(track_id)
+-----------------+------------------+
                  |
                  v
+------------------------------------+
|          CP-SAT SOLVER             |  DETERMINES TEMPORAL SCHEDULE
|  - Solves task start times         |  Input: Tasks + TrainTraversals
|  - Respects track possession       |  Output: ScheduleResult
|  - Never performs pathfinding      |
+------------------------------------+
```

### 14.2 Future Solver Interface Requirements
If CP-SAT is upgraded to track-aware scheduling in a future phase:
1. The solver must receive fixed, pre-resolved `(section_id, traversal_track_id, interval)` tuples.
2. If `traversal_track_id` is resolved, the solver creates a fixed interval variable on that track.
3. If `traversal_track_id` is `None` (unresolved or whole-section), the solver conservatively blocks ALL tracks in that section (`AddNoOverlap` across all section tracks).
4. The solver must NEVER be responsible for selecting which track a train uses.

---

## 15. Safety & Governance Boundary

### What Topology Does NOT Prove:
1. **No Signaling Authority:** A physical rail connection does not grant authority to enter. Real railways require signal clearance (green/yellow aspect).
2. **No Interlocking / Route Locking:** Topology models passive geometry, not switch machine positions, detector bars, or electronic interlocking logic.
3. **No Flank Protection:** Parallel movements on adjacent tracks may be prohibited by interlocking flank protection rules even if the tracks do not physically intersect.
4. **No OHE / Traction Isolation:** Electric trains cannot traverse unelectrified tracks (`electrified = False`), and maintenance on an overhead contact wire may require electrical isolation of adjacent tracks.

---

## 16. Required Data Gaps

To move from discovery to full track-level routing, the following missing data must be addressed:

| Data Gap | Nature of Missing Information | Impact on System | Recommended Resolution |
| :--- | :--- | :--- | :--- |
| **Station Throat Schematics** | Physical layout of switches and turnouts connecting platform lines to section running lines. | Station-to-section continuity cannot be established. | Ingest verified Engineering Scale Plans (ESP) or maintain honest `NO_TOPOLOGY` state. |
| **Section Boundary Continuity** | Connections linking `SEC-A-B-UP-END` to `SEC-B-C-UP-START`. | Cannot track-route express trains through stations without stopping. | Define explicit `CONTINUITY` connections at boundary joints. |
| **Station Platform Lines** | Dedicated track records for station loop lines and platforms. | Trains stopping at stations currently dwell on generic section tracks. | Model station tracks as distinct from block section tracks. |
| **Train Operating Direction** | Explicit `UP` / `DOWN` attribute on `TrainModel` or `TrainMovement`. | Direction must be inferred from station sequence. | Add explicit `direction` to timetable domain model. |

---

## 17. Proposed Phase 16J Implementation Contract

When implementation proceeds in a future phase, it must conform to the following contract:

### 17.1 Input
- `TrainPass`: Station-to-station movement interval with `from_station_id`, `to_station_id`, `interval`.
- `InfrastructureTopology`:
  - `tracks`: Available running tracks for each section.
  - `track_endpoints`: Validated boundary ports (`START`, `END`).
  - `topology_nodes`: Junction nodes at stations and block boundaries.
  - `topology_connections`: Explicit permitted physical connections.

### 17.2 Output: `RouteResolutionResult`
```python
class RouteResolutionResult(BaseModel):
    traversals: List[TrainTraversal]
    resolution_status: TraversalResolutionStatus
    unresolved_reason: Optional[str] = None
    traversed_connections: List[str] = Field(default_factory=list)
    diagnostics: Dict[str, Any] = Field(default_factory=dict)
```

### 17.3 Invariants to Enforce
1. **Zero Fabrication:** Never invent a `TopologyConnection` or assign a `traversal_track_id` that is not connected by explicit database records.
2. **Direction Respect:** Rejects any path traversing a track against its unidirectional constraint.
3. **Conservative Fallback:** If topology is absent or path is ambiguous, set `traversal_track_id = None` and preserve whole-section conflict safety.
4. **No Solver Mutation:** The route resolver is a pure domain service; it does not alter CP-SAT, migrations, or database schemas.

---

## 18. Explicit Non-Goals

The following are explicitly **out of scope** for Phase 16J and any immediate follow-up:
1. **Dynamic Dispatching:** We are not building a computerized train dispatching or traffic management system (TMS).
2. **Interlocking Emulation:** We will not model relay racks, ladder tracks, route relays, or signal lamps.
3. **Automated Topology Synthesis:** We will not run machine learning or heuristics to guess track connections from synthetic timetable names.
4. **Solver Track Variables:** CP-SAT will not be given track-level binary decision variables until routing is fully validated and independently verified.

---

## 19. Recommended Next Phase Sequence

1. **Phase 16K — Curated Infrastructure Topology Dataset (`DEMO_ONLY`):**
   - Create a realistic, hand-verified junction topology fixture for a representative corridor segment (e.g. `STN-NDLS` to `STN-GZB` including station throats and crossover junctions).
   - Verify that all connections, nodes, and endpoints satisfy relational check constraints.
2. **Phase 16L — Deterministic Topology Route Resolver:**
   - Implement the pure domain route resolver specified in Section 17.
   - Test against the Phase 16K fixture, verifying deterministic resolution of `DIRECT_SECTION`, `EXPANDED_ROUTE`, and explicit rejection of `AMBIGUOUS_ROUTE` and `NO_TOPOLOGY`.
3. **Phase 16M — Independent Validator Traversal Verification:**
   - Implement `_check_train_traversal_topology` in `checks.py`.
   - Ensure the validator independently flags invalid track assignments.
4. **Phase 16N — Track-Aware CP-SAT Optimization (Experimental):**
   - Only after 16K–16M are proven and approved, introduce track-level interval reservations in CP-SAT while retaining whole-section safety as a configurable baseline.

---

## 20. Verification Evidence

### Trace Summary (`VERIFIED FROM CODE`)

| File Path | Symbol / Entity | Role in Routing Pipeline |
| :--- | :--- | :--- |
| `backend/app/db/models/train.py` | `TrainModel` | Master train record (`train_id`, `train_number`). |
| `backend/app/db/models/movement.py` | `TrainMovementModel` | Timetable event; contains optional `track_id`. |
| `backend/app/domain/temporal.py` | `TrainPass` | Station-to-station pass; drops `track_id`. |
| `backend/app/domain/temporal.py` | `TrainTraversal` | Physical traversal record; `traversal_track_id = None`. |
| `backend/app/services/compatibility_service.py` | `derive_train_passes` | Converts movements into passes. |
| `backend/app/services/compatibility_service.py` | `expand_train_traversals` | Expands passes into section traversals via Dijkstra. |
| `backend/app/domain/planning_snapshot.py` | `PlanningSnapshot` | Stores passes and traversals; computes snapshot hash. |
| `backend/app/domain/topology.py` | `TopologyNode`, `TrackEndpoint`, `TopologyConnection` | Meso-level topology persistence domain models. |
| `backend/app/db/models/topology.py` | `TopologyNodeModel`, `TrackEndpointModel`, `TopologyConnectionModel` | Relational tables with check/unique constraints. |
| `backend/app/services/optimization/cp_sat_model.py` | `CPSATModelBuilder` | Whole-section `AddNoOverlap` solver constraint. |
| `backend/app/services/validation/checks.py` | `ScheduleCheckRunner` | Authoritative whole-section collision validator. |
