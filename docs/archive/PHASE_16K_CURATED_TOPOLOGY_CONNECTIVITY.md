# PHASE 16K — CURATED TOPOLOGY CONNECTIVITY IMPLEMENTATION REPORT

**Phase:** Phase 16K — Curated Topology Connectivity  
**Status:** Completed  
**Date:** 2026-10-04  
**Baseline Commit:** `ce2e344` (Phase 16I-C baseline)  

---

## 1. Objective

Phase 16K creates a small, explicitly curated `DEMO_ONLY` infrastructure topology dataset that connects a limited existing corridor through the Phase 16I-C topology model (`TopologyNode`, `TrackEndpoint`, `TopologyConnection`).

This phase provides explicit topology connectivity for future route-resolution work (Phase 16L).
It does **NOT**:
- implement route resolution
- implement track-aware optimization
- modify CP-SAT behavior
- modify independent Validator behavior
- modify governance or approval workflows

---

## 2. Selected Corridor

The curated topology fixture spans **3 contiguous block sections** along the Delhi–Howrah main line:

1. **`SEC-NDLS-GZB`** (km 0.0 to 25.0): From New Delhi (`STN-NDLS`) to Ghaziabad (`STN-GZB`).
2. **`SEC-GZB-KRJ`** (km 25.0 to 95.0): From Ghaziabad (`STN-GZB`) to Khurja (`STN-KRJ`).
3. **`SEC-KRJ-ALJN`** (km 95.0 to 126.0): From Khurja (`STN-KRJ`) to Aligarh (`STN-ALJN`).

Total corridor length: **126.0 km**.

---

## 3. Why This Corridor Was Selected

1. **Active Operational Scenario:** This corridor forms the core backbone of `SCN-DEMO-001`, containing the highest concentration of timetable train services (e.g. 12004 Shatabdi, 12301/12302 Rajdhani).
2. **Direct Section vs Express Hop Exercise:**
   - 12004 operates `NDLS -> GZB` (direct adjacent-station hop) followed by `GZB -> ALJN` (an express hop skipping intermediate station `KRJ`, traversing `SEC-GZB-KRJ` and `SEC-KRJ-ALJN`).
   - This provides the exact combination needed to test both single-section and multi-section continuous track routing.
3. **Existing Track Assignments in Migration 007:**
   - `MOV-12302-NDLS-01` (DN Rajdhani departure) was pre-assigned to `TRK-NDLS-GZB-DN`.
   - `MOV-12301-NDLS-09` (UP Rajdhani arrival) was pre-assigned to `TRK-NDLS-GZB-UP`.
   - Reusing this corridor ensures seamless alignment between timetable movements, train passes, and physical tracks.

---

## 4. Existing Infrastructure Entities Reused

Phase 16K reuses **existing database entities without modification**:

- **Stations (4):** `STN-NDLS` (km 0.0), `STN-GZB` (km 25.0), `STN-KRJ` (km 95.0), `STN-ALJN` (km 126.0).
- **Sections (3):** `SEC-NDLS-GZB`, `SEC-GZB-KRJ`, `SEC-KRJ-ALJN`.
- **Tracks (6):**
  - `TRK-NDLS-GZB-DN` (DOWN) & `TRK-NDLS-GZB-UP` (UP)
  - `TRK-GZB-KRJ-DN` (DOWN) & `TRK-GZB-KRJ-UP` (UP)
  - `TRK-KRJ-ALJN-DN` (DOWN) & `TRK-KRJ-ALJN-UP` (UP)
- **Track Endpoints (12 total, 8 connected across junctions):**
  - All endpoints were pre-seeded in migration 010. Zero new endpoints were created.
- **Source Document:** `SRC-TAG-2023-TBL-01` (existing Indian Railways timetable source).

---

## 5. Demo Topology Nodes

Two explicit junction throat nodes were created at the section interfaces:

| Node ID | Node Name | Station ID | Node Type | Classification | Source ID |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`NODE-GZB-THROAT`** | Ghaziabad Station Junction Throat | `STN-GZB` | `STATION_THROAT` | `DEMO_ONLY` | `SRC-TAG-2023-TBL-01` |
| **`NODE-KRJ-THROAT`** | Khurja Junction Throat | `STN-KRJ` | `STATION_THROAT` | `DEMO_ONLY` | `SRC-TAG-2023-TBL-01` |

**Rationale:**  
- `NODE-GZB-THROAT` physically and operationally interfaces `SEC-NDLS-GZB` (ending at km 25.0) with `SEC-GZB-KRJ` (starting at km 25.0).
- `NODE-KRJ-THROAT` interfaces `SEC-GZB-KRJ` (ending at km 95.0) with `SEC-KRJ-ALJN` (starting at km 95.0).

---

## 6. Demo Topology Endpoints Reused

The following 8 pre-existing Phase 16I-C endpoints interface across the two nodes:

| Endpoint ID | Parent Track ID | Type | Kilometrage | Section ID | Role at Junction |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `EP-TRK-NDLS-GZB-DN-END` | `TRK-NDLS-GZB-DN` | `END` | 25.0 km | `SEC-NDLS-GZB` | Entry to GZB throat from NDLS (DN) |
| `EP-TRK-GZB-KRJ-DN-START` | `TRK-GZB-KRJ-DN` | `START` | 25.0 km | `SEC-GZB-KRJ` | Exit from GZB throat towards KRJ (DN) |
| `EP-TRK-GZB-KRJ-UP-START` | `TRK-GZB-KRJ-UP` | `START` | 25.0 km | `SEC-GZB-KRJ` | Entry to GZB throat from KRJ (UP) |
| `EP-TRK-NDLS-GZB-UP-END` | `TRK-NDLS-GZB-UP` | `END` | 25.0 km | `SEC-NDLS-GZB` | Exit from GZB throat towards NDLS (UP) |
| `EP-TRK-GZB-KRJ-DN-END` | `TRK-GZB-KRJ-DN` | `END` | 95.0 km | `SEC-GZB-KRJ` | Entry to KRJ throat from GZB (DN) |
| `EP-TRK-KRJ-ALJN-DN-START` | `TRK-KRJ-ALJN-DN` | `START` | 95.0 km | `SEC-KRJ-ALJN` | Exit from KRJ throat towards ALJN (DN) |
| `EP-TRK-KRJ-ALJN-UP-START` | `TRK-KRJ-ALJN-UP` | `START` | 95.0 km | `SEC-KRJ-ALJN` | Entry to KRJ throat from ALJN (UP) |
| `EP-TRK-GZB-KRJ-UP-END` | `TRK-GZB-KRJ-UP` | `END` | 95.0 km | `SEC-GZB-KRJ` | Exit from KRJ throat towards GZB (UP) |

---

## 7. Demo Topology Connections

Five explicit connections were created across the two junction throat nodes:

| Connection ID | Node ID | From Endpoint ID | To Endpoint ID | Type | Direction | Max Speed | Classification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`CONN-GZB-DN-THROUGH`** | `NODE-GZB-THROAT` | `EP-TRK-NDLS-GZB-DN-END` | `EP-TRK-GZB-KRJ-DN-START` | `CONTINUITY` | `FORWARD` | `None` | `DEMO_ONLY` |
| **`CONN-GZB-UP-THROUGH`** | `NODE-GZB-THROAT` | `EP-TRK-GZB-KRJ-UP-START` | `EP-TRK-NDLS-GZB-UP-END` | `CONTINUITY` | `FORWARD` | `None` | `DEMO_ONLY` |
| **`CONN-GZB-CROSSOVER-DN-UP`** | `NODE-GZB-THROAT` | `EP-TRK-NDLS-GZB-DN-END` | `EP-TRK-GZB-KRJ-UP-START` | `CROSSOVER` | `FORWARD` | `30 km/h` | `DEMO_ONLY` |
| **`CONN-KRJ-DN-THROUGH`** | `NODE-KRJ-THROAT` | `EP-TRK-GZB-KRJ-DN-END` | `EP-TRK-KRJ-ALJN-DN-START` | `CONTINUITY` | `FORWARD` | `None` | `DEMO_ONLY` |
| **`CONN-KRJ-UP-THROUGH`** | `NODE-KRJ-THROAT` | `EP-TRK-KRJ-ALJN-UP-START` | `EP-TRK-GZB-KRJ-UP-END` | `CONTINUITY` | `FORWARD` | `None` | `DEMO_ONLY` |

---

## 8. Compact Topology Trace Table

| Node ID | From Endpoint | To Endpoint | From Track | To Track | From Section | To Section | Connection ID | Dir | Type | Provenance |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `NODE-GZB-THROAT` | `...NDLS-GZB-DN-END` | `...GZB-KRJ-DN-START` | `...NDLS-GZB-DN` | `...GZB-KRJ-DN` | `SEC-NDLS-GZB` | `SEC-GZB-KRJ` | `CONN-GZB-DN-THROUGH` | `FWD` | `CONTINUITY` | `DEMO_ONLY` |
| `NODE-GZB-THROAT` | `...GZB-KRJ-UP-START` | `...NDLS-GZB-UP-END` | `...GZB-KRJ-UP` | `...NDLS-GZB-UP` | `SEC-GZB-KRJ` | `SEC-NDLS-GZB` | `CONN-GZB-UP-THROUGH` | `FWD` | `CONTINUITY` | `DEMO_ONLY` |
| `NODE-GZB-THROAT` | `...NDLS-GZB-DN-END` | `...GZB-KRJ-UP-START` | `...NDLS-GZB-DN` | `...GZB-KRJ-UP` | `SEC-NDLS-GZB` | `SEC-GZB-KRJ` | `CONN-GZB-CROSSOVER-DN-UP`| `FWD` | `CROSSOVER` | `DEMO_ONLY` |
| `NODE-KRJ-THROAT` | `...GZB-KRJ-DN-END` | `...KRJ-ALJN-DN-START` | `...GZB-KRJ-DN` | `...KRJ-ALJN-DN` | `SEC-GZB-KRJ` | `SEC-KRJ-ALJN` | `CONN-KRJ-DN-THROUGH` | `FWD` | `CONTINUITY` | `DEMO_ONLY` |
| `NODE-KRJ-THROAT` | `...KRJ-ALJN-UP-START` | `...GZB-KRJ-UP-END` | `...KRJ-ALJN-UP` | `...GZB-KRJ-UP` | `SEC-KRJ-ALJN` | `SEC-GZB-KRJ` | `CONN-KRJ-UP-THROUGH` | `FWD` | `CONTINUITY` | `DEMO_ONLY` |

---

## 9. Direction Semantics

1. **DOWN Through Direction:**
   - A DOWN train travels away from NDLS (increasing chainage: 0.0 -> 25.0 -> 95.0 -> 126.0).
   - In `SEC-NDLS-GZB`: runs along `TRK-NDLS-GZB-DN`, exiting at `EP-TRK-NDLS-GZB-DN-END` (km 25.0).
   - At Ghaziabad: traverses `CONN-GZB-DN-THROUGH` in the `FORWARD` direction into `EP-TRK-GZB-KRJ-DN-START`.
   - In `SEC-GZB-KRJ`: runs along `TRK-GZB-KRJ-DN`, exiting at `EP-TRK-GZB-KRJ-DN-END` (km 95.0).
   - At Khurja: traverses `CONN-KRJ-DN-THROUGH` in the `FORWARD` direction into `EP-TRK-KRJ-ALJN-DN-START`.
   - In `SEC-KRJ-ALJN`: runs along `TRK-KRJ-ALJN-DN`.
2. **UP Through Direction:**
   - An UP train travels towards NDLS (decreasing chainage: 126.0 -> 95.0 -> 25.0 -> 0.0).
   - In `SEC-KRJ-ALJN`: runs along `TRK-KRJ-ALJN-UP`, exiting at `EP-TRK-KRJ-ALJN-UP-START` (km 95.0).
   - At Khurja: traverses `CONN-KRJ-UP-THROUGH` in the `FORWARD` direction into `EP-TRK-GZB-KRJ-UP-END`.
   - In `SEC-GZB-KRJ`: runs along `TRK-GZB-KRJ-UP`, exiting at `EP-TRK-GZB-KRJ-UP-START` (km 25.0).
   - At Ghaziabad: traverses `CONN-GZB-UP-THROUGH` in the `FORWARD` direction into `EP-TRK-NDLS-GZB-UP-END`.
   - In `SEC-NDLS-GZB`: runs along `TRK-NDLS-GZB-UP`.
3. **Crossover Diverging Direction:**
   - `CONN-GZB-CROSSOVER-DN-UP` links `EP-TRK-NDLS-GZB-DN-END` to `EP-TRK-GZB-KRJ-UP-START` in the `FORWARD` direction.
   - This provides an explicit diverging path crossing from the DOWN line to the UP line at GZB throat, with a 30 km/h turnout speed limit.

---

## 10. Connection Types & Speed Metadata

- **`CONTINUITY`:** Used for straight through rail alignment along the main lines (`CONN-GZB-DN-THROUGH`, `CONN-GZB-UP-THROUGH`, `CONN-KRJ-DN-THROUGH`, `CONN-KRJ-UP-THROUGH`). `max_diverging_speed_kmh` is strictly `None`.
- **`CROSSOVER`:** Used for the diagonal turnout switch linking the DOWN line to the UP line (`CONN-GZB-CROSSOVER-DN-UP`). `max_diverging_speed_kmh` is set to `30` (representing a standard 1-in-12 turnout restriction on Indian Railways).

---

## 11. Provenance / `DEMO_ONLY` Boundary

- **Explicit Tagging:** Every node and connection has `classification = "DEMO_ONLY"` persisted in PostgreSQL.
- **Source Citation:** Referenced source document is `SRC-TAG-2023-TBL-01`.
- **Truthful Scope:** Only 2 junction nodes and 5 connections exist. The remaining 30 block sections and 126 running tracks remain strictly disconnected (`0` inferred connections).

---

## 12. What Was Intentionally NOT Inferred

To uphold TrackMeld's core safety and data integrity principles, the following were **NOT inferred**:
1. **Zero Global Connectivity:** We did not infer connections between adjacent sections across the remaining 30 sections.
2. **Zero Platform / Station Yard Synthesis:** We did not manufacture platform tracks or station yard loops at Ghaziabad, Khurja, or Aligarh.
3. **Zero Signalling or Interlocking Logic:** The connections represent passive rail geometry, not signal routes, aspect sequences, or route locking.
4. **Zero Traversal Track Assignment:** `TrainTraversal.traversal_track_id` remains `None`.

---

## 13. Database Migration Behavior

Migration `b2c3d4e5f6a7_011_curated_demo_topology.py`:
- **Downstream of:** `a1b2c3d4e5f6` (migration 010).
- **Upgrade:** Deterministically bulk inserts the 2 nodes and 5 connections.
- **Downgrade:** Explicitly deletes only the 5 connections and 2 nodes by primary key.
- **Verification:** Downgrade and re-upgrade tested and confirmed 100% idempotent and reversible.

---

## 14. Test Verification Results

### Dedicated Phase 16K Test Suites
- **Unit Tests (`tests/unit/test_phase16k_curated_topology.py`):** 4 / 4 passed.
  - Verifies pure domain model instantiation, enums, crossover attributes, and self-connection rejection.
- **Integration Tests (`tests/integration/test_phase16k_topology_api.py`):** 6 / 6 passed.
  - Verifies API retrieval of nodes, connections, endpoint integrity, track topology aggregation, and isolation of non-corridor tracks.

### Full Regression Test Suites
- **Phase 16I-C Topology Tests:** 9 / 9 passed (`tests/integration/test_phase16i_c_topology_api.py`).
- **Targeted Regression Suite:** 148 / 148 passed (`tests/unit/test_phase16*`, `tests/unit/test_phase7*`, `tests/unit/test_cp_sat*`, `tests/integration/test_phase16*`).
- **All Unit Tests:** 292 / 292 passed (`0` failures).
- **All Integration Tests:** 134 / 134 passed (`0` failures).

---

## 15. Architectural Boundaries Preserved

- **CP-SAT Solver (`cp_sat_model.py`):** 100% untouched. Whole-section `AddNoOverlap` remains authoritative.
- **Independent Validator (`checks.py`):** 100% untouched. Whole-section `SECTION_OCCUPANCY_CONFLICT` remains authoritative.
- **TrainPass / TrainTraversal:** Untouched. No routing algorithm was added. `traversal_track_id` remains `None`.
- **Planning Snapshot Hashing:** Untouched.

---

## 16. Future Handoff Contract

> **MANDATORY NOTICE:**  
> This topology fixture exists solely to exercise future deterministic route-resolution logic. It does not constitute engineering-authoritative railway infrastructure and must not be used to infer real-world signalling, interlocking, movement authority, braking, headway, OHE isolation, or operational approval.

**Contract for Phase 16L (Deterministic Route Resolution):**
1. Future route resolution must consume **explicit `TopologyConnection` records**.
2. It must **NOT** reconstruct or synthesize connections from station adjacency or track names.
3. If a train pass cannot find a contiguous sequence of explicit connections, it must return `resolution_status = UNRESOLVED` with `traversal_track_id = None`.
