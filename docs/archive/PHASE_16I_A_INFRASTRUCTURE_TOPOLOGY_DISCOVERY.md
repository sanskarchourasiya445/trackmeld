# Phase 16I-A — Infrastructure Topology Discovery

**Status**: Discovery & Architecture Audit Only  
**Date**: October 2026  
**Baseline HEAD**: `bcb860c` (includes Phase 16H discovery doc on top of `168d8e3`)  
**Branch**: `main` (synchronized with `origin/main`)  
**Working Tree**: Clean  

---

## 1. Baseline & Safety Boundary

### 1.1. Operating Boundary
TrackMeld is an AI-assisted decision-support prototype for railway maintenance planning. It operates strictly under the governance boundary:
```
Rules classify
    ↓
Optimization schedules
    ↓
Independent Validator verifies
    ↓
Human reviews
    ↓
Human approves
```
- **Rules classify**: Hard physical, topological, and operational constraints define the feasible solution space.
- **Optimization schedules**: Google OR-Tools CP-SAT discrete solver searches feasible schedules to maximize maintenance throughput and safety buffer compliance.
- **Independent Validator verifies**: A completely detached validation service (`ScheduleCheckRunner` / `IndependentScheduleValidator`) re-proves all safety checks from first principles.
- **Human reviews & approves**: Railway controllers and safety officers hold exclusive authority to approve or reject proposed plan versions.
- **Non-negotiable product boundary**: TrackMeld **never** issues signalling commands, interlocking locks, route reservations, or autonomous dispatching directives.

### 1.2. Baseline State
- **Phase 16G-C**: Integrated track-aware diagnostic checks into the validator (`INVALID_TRACK_ASSIGNMENT`, `TRACK_DIRECTION_CONFLICT`, `ADJACENT_TRACK_FULL_BLOCK`, `ADJACENT_TRACK_CAUTION_REQUIRED`, `SPATIAL_METADATA_INCOMPLETE`).
- **Phase 16H**: Proved that CP-SAT track-aware optimization cannot be implemented safely without physical topology, cross-section track continuity, and verified lateral clearance models.
- **Whole-section safety baseline**: CP-SAT and the Independent Validator continue to enforce whole-section mutual exclusion (`SECTION_OCCUPANCY_CONFLICT`, `TRAIN_MOVEMENT_CONFLICT`, and CP-SAT `AddNoOverlap`). Different tracks within the same section cannot coexist in a valid plan.

---

## 2. Current Infrastructure Model

Forensic inspection of the TrackMeld codebase establishes the following facts regarding how railway infrastructure is currently modeled:

### 2.1. Answers to Core Infrastructure Questions

| Question | Current Implementation State | Exact Code Citation | Architectural Implication |
| :--- | :--- | :--- | :--- |
| **1. What identifies a section?** | `section_id` (String primary key, e.g. `SEC-NDLS-GZB`) | `backend/app/db/models/section.py#L26` | Section is a first-class infrastructure resource representing a block corridor between two stations. |
| **2. What identifies a track?** | `track_id` (String primary key, e.g. `TRK-SEC-NDLS-GZB-UP`) | `backend/app/db/models/track.py#L25` | Track is an infrastructure entity scoped strictly beneath a parent section. |
| **3. Is a track identity globally unique?** | **YES** (Database primary key) | `backend/app/db/models/track.py#L25` | Keys are globally unique strings in Postgres, but semantically section-local. |
| **4. Is track identity meaningful beyond its section?** | **NO** | `backend/app/db/models/track.py#L26-L30` | `section_id` is a mandatory foreign key (`ondelete="CASCADE"`). Tracks terminate at section boundaries. |
| **5. How is track direction represented?** | `direction`: `'UP'`, `'DOWN'`, or `'BIDIRECTIONAL'` | `backend/app/db/models/track.py#L32` | Stored as a string with a database check constraint `ck_tracks_direction_valid`. |
| **6. How is section direction represented?** | **NOT REPRESENTED** | `backend/app/db/models/section.py#L18-L58` | `SectionModel` has endpoints (`from_station_id`, `to_station_id`), but no direction attribute. |
| **7. How is adjacency represented?** | `adjacent_track_ids`: Nullable JSON list of track IDs | `backend/app/db/models/track.py#L35` | Stores parallel running tracks within the same section. |
| **8. Adjacency: physical proximity or route connectivity?** | **PHYSICAL PROXIMITY ONLY** | `backend/app/domain/sections.py#L69-L72` | Explicitly defined as "directly adjacent running track IDs in the same section". |
| **9. Is there any cross-section connectivity today?** | **NO** | `backend/app/db/models/track.py` | No foreign keys, pointers, or continuity tables link tracks across adjoining sections. |
| **10. Is there any topology graph today?** | **PARTIALLY (Macro-level only)** | `backend/app/services/compatibility_service.py#L172-L187` | Undirected station-to-station graph used solely for Dijkstra section-path expansion. |
| **11. Are station platforms modeled as resources?** | **NO** | `backend/app/db/models/station.py#L8-L47` | Stations are point nodes; platforms and platform lines do not exist in the schema. |
| **12. Are junctions represented?** | **DESCRIPTIVE ONLY** | `backend/app/db/models/station.py#L19` | `station_type="JUNCTION"` is an informational string; no branching topology exists. |
| **13. Are turnouts represented?** | **NO** | Full backend search | Zero models, columns, or tables represent turnouts or points. |
| **14. Are crossovers represented?** | **NO** | Full backend search | Zero models, columns, or tables represent crossovers between parallel tracks. |
| **15. Are dead ends / buffer stops represented?** | **NO** | Full backend search | Zero representation of dead ends, sidings, or terminating buffers. |
| **16. Are track merges/splits represented?** | **NO** | Full backend search | Zero representation of track branching, merging, or converging junctions. |

---

## 3. Adjacency vs Continuity

A central architectural risk in track-aware modeling is conflating **lateral adjacency** with **longitudinal continuity**. TrackMeld must keep these concepts strictly distinct:

```
Physical Distinction in Railway Infrastructure:

                    ┌───────────────── Section SEC-A ──────────────────┐ ┌───────────────── Section SEC-B ──────────────────┐
                    │                                                  │ │                                                  │
Track 1 (UP)  ──────┼──────────────────────────────────────────────────┼─┼──────────────────────────────────────────────────┼──────
                    │                      ▲                           │ │                                                  │
                    │                      │ Lateral Adjacency         │ │               Longitudinal Continuity            │
                    │                      ▼ (Fouling / Clearances)    │ │               (End-to-End Route Flow)            │
Track 2 (DN)  ──────┼──────────────────────────────────────────────────┼─┼──────────────────────────────────────────────────┼──────
                    │                                                  │ │                                                  │
                    └──────────────────────────────────────────────────┘ └──────────────────────────────────────────────────┘
```

### 3.1. Current Semantics of `Track.adjacent_track_ids`
In `backend/app/domain/sections.py#L69-L72`:
```python
adjacent_track_ids: Optional[List[str]] = Field(
    default=None,
    description="Explicit list of directly adjacent running track IDs in the same section, or empty list if isolated, or None if unspecified."
)
```
- **Meaning**: Parallel running lines situated immediately beside each other across track ballast within the same section corridor.
- **Evaluated by**: `evaluate_spatial_compatibility()` (`backend/app/domain/spatial_compatibility.py#L346-L396`) to determine if a maintenance possession with `adjacent_track_impact = FULL_TRAFFIC_BLOCK` or `CAUTION_ORDER` fouls the neighbor line.
- **Evidence**: It does **not** signify that a train can switch from Track 1 to Track 2, nor does it mean Track 1 continues into Track 2.

### 3.2. Taxonomy of Spatial & Topological Relations
To prevent accidental architectural conflation, TrackMeld establishes the following formal definitions:

1. **Adjacent Track**: Runs parallel to a given track within the same physical corridor segment (subject to lateral fouling envelopes, crane swing, ballast destabilization, or common-portal OHE isolation).
2. **Continuous Track**: The longitudinal physical continuation of the same running line across a block section boundary without passing through a switch or turnout.
3. **Connected Track**: A track that can be physically entered from another track via a switch, turnout, crossover, or slip switch.
4. **Routable Track**: A sequence of connected tracks forming an authorized, signalled movement path between an entry signal and an exit signal.
5. **Conflicting Track**: Tracks whose clearance envelopes intersect at grade (e.g. diamond crossings, scissor crossovers, gathering lines) where concurrent occupancy causes collision.
6. **Alternative Route**: A distinct parallel or bypass track (e.g. Loop Line vs Main Line) between the same two geographic boundaries.

**Strict Architectural Invariant**: No single database column or domain field may serve more than one of these six roles.

---

## 4. Section Connectivity

### 4.1. Current Implicit Connection Mechanism
Sections do not link directly to neighboring sections. Instead, they reference terminal station nodes:
- `SectionModel.from_station_id` $\rightarrow$ `StationModel.station_id` (`backend/app/db/models/section.py#L28-L33`)
- `SectionModel.to_station_id` $\rightarrow$ `StationModel.station_id` (`backend/app/db/models/section.py#L34-L39`)

### 4.2. Operational Tracing
1. **Can Section A explicitly identify neighboring Section B?**  
   **NO.** There is no `next_section_id` or neighbor table. Adjacency between sections must be inferred by finding another section where `SectionB.from_station_id == SectionA.to_station_id`.
2. **Is the relationship directional?**  
   **NO.** In `CompatibilityEngine.expand_train_traversals` (`backend/app/services/compatibility_service.py#L183-L186`):
   ```python
   direct_lookup[(u, v)] = (sec_id, length_km, s)
   direct_lookup[(v, u)] = (sec_id, length_km, s)
   adj[u].append((v, sec_id, length_km, s))
   adj[v].append((u, sec_id, length_km, s))
   ```
   Sections are modeled as **undirected graph edges** connecting station vertices.
3. **Can multiple sections connect at the same station?**  
   **YES.** A junction station (e.g. `STN-GZB`) has multiple incident section edges connecting to New Delhi, Aligarh, and Moradabad.
4. **Can one section branch into multiple sections?**  
   **Only at station boundaries.** Within the interior of a section, branching is structurally impossible in the current schema.
5. **Can a train traverse a section without knowing its physical route?**  
   **YES.** `TrainPass` only knows `section_id` and half-open time interval `[start, end)`. It has no route or track detail.
6. **What happens for express movements skipping stations?**  
   In `expand_train_traversals` (`backend/app/services/compatibility_service.py#L275-L315`): Dijkstra finds the shortest sequence of section edges between timetable stops, and linearly partitions the total traversal duration across sections proportional to `length_km`. **It has zero awareness of which physical tracks or platform lines are traversed.**

---

## 5. Station & Platform Semantics

### 5.1. The Station Point-Node Model
In `backend/app/db/models/station.py`:
- `station_id`: Primary key (e.g. `STN-NDLS`).
- `station_code`: IR code (e.g. `NDLS`).
- `route_km`: Scalar chainage datum.
- `station_type`: String (e.g. `"JUNCTION"`, `"STATION"`).

**Entities Conflated or Absent**:
- **Platforms**: Completely absent.
- **Platform Lines**: Completely absent.
- **Through / Main Lines**: Completely absent.
- **Loop Lines / Passing Sidings**: Completely absent.
- **Station Throat / Interlocking Matrix**: Completely absent.

In TrackMeld today, an entire complex terminal station with 16 platforms, 40 points, and multiple route throats is represented as a single dimensionless point node.

### 5.2. Analysis of `TrainMovement.track_id`
In Phase 16C, `track_id` was added to `TrainMovementModel` (`backend/app/db/models/movement.py#L26`):
```python
track_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("tracks.track_id", ondelete="SET NULL"), nullable=True)
```
**Forensic Audit of `TrainMovement.track_id`**:
1. It is a foreign key to `TrackModel`.
2. Because `TrackModel` belongs strictly to a `section_id`, any `track_id` assigned to a `TrainMovement` actually points to a **running track in an adjacent section**, not a station platform track.
3. In `ScheduleCheckRunner._check_track_spatial_safety()` (`backend/app/services/validation/checks.py#L457-L487`), it is validated only for:
   - Existence in `snapshot.tracks_map` (`INVALID_TRACK_ASSIGNMENT`).
   - Movement direction matching track direction (`TRACK_DIRECTION_CONFLICT`).
4. **Crucial Finding**: `TrainMovement.track_id` is **never copied** to `TrainPass`, is **never copied** to `TrainTraversal`, and is **never inspected** by CP-SAT.
5. **Architectural Rule**: `TrainMovement.track_id` must **NOT** be reinterpreted as a section traversal track or a platform track without explicit schema migration and domain definition.

---

## 6. Junction, Turnout & Crossover Findings

A comprehensive static analysis of the backend codebase was conducted for physical track switching entities:
- `turnout`: 0 occurrences
- `switch_point`: 0 occurrences
- `crossover`: 0 occurrences
- `crossing_loop`: 0 occurrences
- `platform_track`: 0 occurrences
- `interlocking`: 1 occurrence (descriptive string in `backend/app/domain/sections.py#L29`)

### 6.1. Current State
**TrackMeld contains zero domain models or database tables representing track switches, points, turnouts, crossovers, or interlocking routes.**

### 6.2. What a Future Topology Model Minimally Needs to Represent Branching
Without prematurely prescribing a schema, any truthful representation of railway branching must capture three fundamental elements:
1. **Topology Nodes (Connection Points)**: Points on the network where tracks meet, terminate, or diverge (e.g., station throats, switch tips, block boundary joints).
2. **Topology Edges (Track Segments)**: Continuous rails between two topology nodes with defined length, direction, and speed attributes.
3. **Movable Points / Route Compatibility**: Rules declaring which edges can connect to which edges, and which edge combinations mutually exclude each other at grade.

---

## 7. Direction Semantics

### 7.1. Global vs Local Direction
- `TrackDirection` (`UP`, `DOWN`, `BIDIRECTIONAL`) is defined in `backend/app/domain/sections.py#L54-L59`.
- In Indian Railways operational practice, **UP** indicates trains travelling toward a primary headquarters or kilometer zero (e.g. towards New Delhi or Howrah), while **DOWN** indicates trains travelling away.
- In TrackMeld's domain layer, direction is **section-local**: a track within section `SEC-01` has a direction attribute, but there is no corridor-wide coordinate system validating directional continuity.

### 7.2. Directional Constraints in the Solver vs Validator
- **In CP-SAT**: Direction is **100% invisible**. The solver does not inspect task direction, train direction, or track direction.
- **In the Independent Validator**: Direction is an **authoritative safety check**. `_check_track_spatial_safety()` verifies that `task.direction` and `movement.direction` conform to `track.direction`, raising `TRACK_DIRECTION_CONFLICT` (`ERROR`) on violation.

### 7.3. Direction Reversals & Opposing Traffic
- TrackMeld currently cannot represent a train reversing direction (e.g. locomotive run-around, push-pull reversal, or cab change).
- A `BIDIRECTIONAL` track permits traffic in either direction, but TrackMeld currently lacks opposing-train interlocking rules (e.g. absolute block directional locking) that prevent two trains from entering opposite ends of the same bidirectional track simultaneously.

---

## 8. Single-Line Semantics

### 8.1. Current Implemented Semantics
- In sections where `track_count == 1`, seed data generates a single track: `TRK-{sec_code}-SL` with `direction = BIDIRECTIONAL` (`backend/alembic/versions/b4e6a8c1d302_005_tracks_schema.py#L88-L97`).
- In both CP-SAT and the Validator, single-line sections are protected by **whole-section mutual exclusion**.
- Exactly one train or maintenance possession can occupy the section at any given moment. Collision between opposing trains is strictly prevented by this macro-mutex.

### 8.2. Potential Future Semantics vs Current Absence
In real-world single-line railway operations:
- Trains moving in opposite directions cross each other at **crossing loops** (passing loops) located at intermediate stations.
- One train enters the loop and halts, while the opposing train proceeds along the main line.
- **Current Absence**: TrackMeld has no loop tracks, no station reception lines, and no crossing rules. Modeling single-line train meets is **impossible** with the current data.

---

## 9. Minimum Topology Information Matrix

The following matrix documents every topology concept, its current status, and what is missing:

| Topology Information | Exists Now? | Location in Code | Current Meaning | Sufficient for Track Routing? | Missing Semantics |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Station Node** | YES | `backend/app/db/models/station.py` | Point vertex in corridor | NO | Platform tracks, station throat, loops |
| **Section Edge** | YES | `backend/app/db/models/section.py` | Macro block corridor | NO | Internal track layout, switches |
| **Track Line** | YES | `backend/app/db/models/track.py` | Line under a section | NO | Continuity to adjacent sections |
| **Track Direction** | YES | `backend/app/db/models/track.py#L32` | UP / DOWN / BIDIRECTIONAL | NO | Directional route locking |
| **Track Adjacency** | YES | `backend/app/db/models/track.py#L35` | Parallel line proximity | NO | Longitudinal chainage overlap, spacing |
| **Section Adjacency** | PARTIALLY | Inferred from station IDs | Shared terminal station | NO | Directional connectivity |
| **Track Continuity** | **NO** | None | Absent | **NO** | Cross-section track alignment |
| **Topology Nodes** | **NO** | None | Absent | **NO** | Switch tips, fouling joints, boundary joints |
| **Topology Edges** | **NO** | None | Absent | **NO** | Physical rail segments |
| **Branching / Turnout** | **NO** | None | Absent | **NO** | Points, switch states (Normal/Reverse) |
| **Crossovers** | **NO** | None | Absent | **NO** | Track-to-track switching |
| **Platform Tracks** | **NO** | None | Absent | **NO** | Stopping berths, platform lengths |
| **Route Identity** | **NO** | `SectionModel.routes` (JSON names) | Descriptive text tags | **NO** | Physical interlocking routes |
| **Movement Path** | **NO** | None | Absent | **NO** | Sequence of physical tracks traversed |
| **At-Grade Conflicts** | **NO** | None | Absent | **NO** | Diamond crossings, slip switches |

---

## 10. Evaluation of Candidate Representation Concepts

TrackMeld must evaluate potential topology modeling paradigms without prematurely selecting one as "standard":

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ TOPOLOGY CANDIDATE MODELS                                                   │
├──────────────────────┬──────────────────────┬───────────────────────────────┤
│ Concept A: Pointers  │ Concept B: Node/Edge │ Concept D: Explicit Routes    │
│                      │                      │                               │
│ [Track 1] ──next──►  │ (Node)──Edge──►(Node)│ Route R1:                     │
│ [Track 2] ──next──►  │   │                  │   [Track 1A] → [Turnout 1]    │
│                      │   └──Edge──►(Node)   │   → [Track 2B]                │
└──────────────────────┴──────────────────────┴───────────────────────────────┘
```

### Concept A: Track-to-Track Next/Previous Pointers
- **Description**: Add `next_track_id: Optional[str]` and `prev_track_id: Optional[str]` directly to `TrackModel`.
- **What it Represents**: Simple end-to-end alignment of tracks across double-line sections where Track UP always continues into Track UP.
- **What it Cannot Represent**: Branching, turnouts, crossovers, junctions, or bidirectional track reversals.
- **Risks**: Fails immediately at any station with more than 1 inbound or outbound route. High risk of false physical continuity assumptions.

### Concept B: Microscopic Node-Edge Topology Graph
- **Description**: Full directed graph where edges are track segments and nodes are points/turnouts, signals, or boundary joints.
- **What it Represents**: Microscopic physical railway reality; exact switch geometries and point positions.
- **What it Cannot Represent**: Macro-level corridor planning without enormous data capture overhead.
- **Risks**: Extreme implementation complexity; severe data availability barrier (TrackMeld does not have CAD/GIS point data for Indian Railways); combinatorial explosion in CP-SAT.

### Concept C: Section-Track Endpoint Boundary Graph
- **Description**: Sections retain tracks, but station junctions contain explicit `TrackConnection` records: `(from_section_id, from_track_id) -> (to_section_id, to_track_id)`.
- **What it Represents**: Meso-level continuity across stations without modeling microscopic turnout mechanisms.
- **What it Cannot Represent**: Internal station dwell paths, individual switch failures, or sub-ballast maintenance inside station throats.
- **Risks**: Requires defining allowable transitions at every station.

### Concept D: Explicit Route / Path Objects
- **Description**: Pre-defined legal operational paths across multiple sections and tracks (e.g., `Route-NDLS-GZB-UP-MAIN`).
- **What it Represents**: Operational timetable routes authorized by railway Working Time Tables (WTT).
- **What it Cannot Represent**: Emergency wrong-line routing or un-signalled shunt moves.
- **Risks**: Scalability depends on enumerating valid paths.

### Concept E: Explicit Infrastructure Conflict Matrix
- **Description**: A lookup table defining which tracks and routes mutually foul each other: `Conflict(Track_A, Track_B) = INCOMPATIBLE`.
- **What it Represents**: Direct translation of railway Station Working Rules (SWR) interlocking tables.
- **What it Cannot Represent**: Dynamic speed and headway profiles.
- **Risks**: Requires complete pair-wise validation.

---

## 11. Synthetic Data Honesty Check

### 11.1. Forensic Audit of Seed Data
Inspection of migrations `backend/alembic/versions/b4e6a8c1d302_005_tracks_schema.py` and `backend/alembic/versions/f0a1b2c3d4e5_009_track_adjacency.py` reveals:
1. All tracks in the database today were **synthetically synthesized**:
   - Every section with `track_count >= 2` was assigned two synthetic tracks: `TRK-{sec_code}-UP` and `TRK-{sec_code}-DN`.
   - Every section with `track_count == 1` was assigned one synthetic track: `TRK-{sec_code}-SL`.
2. Adjacency lists were **synthetically paired**:
   - `TRK-{sec_code}-UP` was marked adjacent to `TRK-{sec_code}-DN`, and vice-versa.
3. **No engineering survey data, GIS track alignments, or official Station Working Rules were imported.**

### 11.2. The Honesty Principle
- **Critical Safety Finding**: The current database does **NOT** contain sufficient data to construct a truthful physical switch and turnout topology.
- If TrackMeld were to algorithmically invent connections between `TRK-SEC-01-UP` and `TRK-SEC-02-UP` based purely on string naming conventions, it would violate Rule 4 of `AGENTS.md`:
  > *"Never imply synthetic route topology is real. Use fictional, seeded synthetic data for the demo... If a rule's authoritative status is unknown, label it unverified."*
- **Mandate**: Any topology introduced must be explicitly declared as `DEMO_ONLY` or backed by a lawful, verified data source.

---

## 12. Boundary Between Topology and Scheduling

To prevent architectural contamination, TrackMeld enforces a strict division of responsibility:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. INFRASTRUCTURE TOPOLOGY LAYER (Static Infrastructure Truth)               │
│    - What tracks exist?                                                     │
│    - What are their physical lengths, gradients, and speeds?                │
│    - Which tracks run physically adjacent to which?                         │
│    - What connections physically exist between tracks?                      │
│    - Which movements physically foul which other movements?                 │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Permitted Physical Graph
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. ROUTE ASSIGNMENT LAYER (Deterministic Pre-Solve Derivation)              │
│    - Given a train's timetable endpoints, which legal track route does it    │
│      occupy?                                                                │
│    - Resolves TrainTraversal.traversal_track_id                             │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Concrete Occupancy Demands
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. SCHEDULING & OPTIMIZATION LAYER (CP-SAT Solver)                          │
│    - At what time does an activity occupy the infrastructure?               │
│    - Can maintenance be scheduled in the temporal gaps between trains?      │
│    - Maximizes priority and throughput within rule-permitted windows        │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Prohibited Boundary Crossing**:
- Topology must **never** make scheduling decisions (e.g. topology cannot state "Train 12004 passes at 10:00").
- The CP-SAT solver must **never** invent or alter infrastructure topology (e.g. solver cannot synthesize a crossover connection to avoid a maintenance conflict).

---

## 13. Future Dependency Graph

Based strictly on codebase evidence, the safe progression toward track-aware optimization requires sequential prerequisites:

```
Phase 16I-A: Infrastructure Topology Discovery (CURRENT — Complete)
    ↓
Phase 16I-B: Topology Domain Model & Schema Specification
    • Formally specify connection/continuity entities
    • Distinguish lateral adjacency from longitudinal continuity
    • Establish synthetic data generation standards
    ↓
Phase 16I-C: Topology Seed Migration & Repository Ingestion
    • Implement schema migrations for cross-section track connectivity
    • Update PlanningSnapshot to index topology relations
    ↓
Phase 16J: Deterministic Train Route & Traversal Track Assignment
    • Resolve TrainTraversal.traversal_track_id using topology
    • Map station-to-station traversals to physical track sequences
    ↓
Phase 16K: Independent Validator Track-Aware Hard Safety Invariants
    • Authoritative track-level conflict verification
    • Mathematical proof of zero cross-track collision
    ↓
Phase 16L: CP-SAT Track-Aware Optimization Modeling
    • Hierarchical resource formulation
    • Controlled relaxation of whole-section mutex
```

### Dependency Rationale:
- **16I-B & 16I-C must precede 16J**: A train traversal cannot be assigned to a physical track across multiple sections if the tracks do not physically connect in the data model.
- **16J must precede 16K**: The validator cannot verify track collision invariants while train passes have unassigned tracks (`traversal_track_id = None`).
- **16K must precede 16L**: The Independent Validator must independently enforce track safety invariants **before** the solver is allowed to relax the whole-section mutex.

---

## 14. Open Questions & Evidence Gaps

The following questions cannot be answered from repository evidence and are formally cataloged as:  
`UNRESOLVED / REQUIRES DOMAIN EVIDENCE`

1. `[UNRESOLVED / REQUIRES DOMAIN EVIDENCE]`: Does TrackMeld require modeling microscopic switch geometries (turnout points and switch blades), or is a meso-level track connection graph across stations sufficient for maintenance planning?
2. `[UNRESOLVED / REQUIRES DOMAIN EVIDENCE]`: In real-world Indian Railways operations, how are non-stopping express train track assignments determined when passing through intermediate stations (e.g. through Main Line vs Platform Loop)?
3. `[UNRESOLVED / REQUIRES DOMAIN EVIDENCE]`: What official data source exists for station layout diagrams (Engineering Scale Plans - ESP) that could replace synthetic track seeds with verified physical infrastructure?
4. `[UNRESOLVED / REQUIRES DOMAIN EVIDENCE]`: How are crossover points between UP and DOWN tracks maintained (does possession of a crossover block both UP and DOWN lines simultaneously)?

---

## 15. Explicit Non-Goals

TrackMeld explicitly rejects the following as **NON-GOALS**:
1. **Computer Based Interlocking (CBI) Emulation**: TrackMeld will not simulate relay logic, route locking circuits, or fail-safe signal aspects.
2. **Microscopic Train Movement Simulation**: TrackMeld will not simulate wheel-rail friction, tractive effort curves, or braking physics.
3. **Live Dispatch Control**: TrackMeld will not send track occupancy authorizations or speed limit modifications to locomotives.
4. **Heuristic Track Fabrication**: TrackMeld will not fabricate turnout connections based on string guessing.

---

## 16. Conclusion

1. **Current TrackMeld infrastructure has zero physical topology.** Tracks exist only as isolated children of block sections.
2. **Track adjacency (`adjacent_track_ids`) represents lateral proximity within a section, NOT route continuity.**
3. **Sections connect only as an undirected macro-graph of station vertices.**
4. **Current track data is 100% synthetic.**
5. **No track-aware optimization or route assignment can safely proceed without an explicit, structured topology model (Phase 16I-B/C).**
6. **The current whole-section safety baseline remains authoritative and essential.**
