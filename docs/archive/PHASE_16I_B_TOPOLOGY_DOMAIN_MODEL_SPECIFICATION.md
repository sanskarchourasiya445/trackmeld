# Phase 16I-B — Infrastructure Topology Domain Model & Schema Specification

**Status**: Specification & Architectural Design Only  
**Date**: October 2026  
**Baseline HEAD**: `bcb860c`  
**Preceding Discovery**:  
- `docs/PHASE_16H_TRACK_AWARE_OPTIMIZATION_DISCOVERY.md`  
- `docs/PHASE_16I_A_INFRASTRUCTURE_TOPOLOGY_DISCOVERY.md`  
**Working Tree**: Clean  

---

## 1. Baseline and Source Reports

### 1.1. Operating Boundary
TrackMeld operates under a strict, non-negotiable separation of responsibilities:
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
- **Rules classify**: Physical, topological, and operational constraints define what is permissible.
- **Optimization schedules**: The mathematical solver (Google OR-Tools CP-SAT) searches within the rule-permitted feasible space.
- **Independent Validator verifies**: An isolated validation service reproduces and audits all safety rules from first principles without trusting the solver.
- **Human reviews & approves**: Controllers and infrastructure managers hold exclusive authority over plan adoption.
- **Product boundary**: TrackMeld is a **decision-support prototype**. It never issues live signalling, route-locking, interlocking, or dispatch commands.

### 1.2. Baseline Architectural State
1. **Whole-Section Safety Baseline Active**: CP-SAT enforces whole-section `AddNoOverlap` across all tasks and train passes affecting a section (`backend/app/services/optimization/cp_sat_model.py#L204-L233`). The Independent Validator enforces whole-section `SECTION_OCCUPANCY_CONFLICT` and `TRAIN_MOVEMENT_CONFLICT` (`backend/app/services/validation/checks.py#L60-L100, L310-L395`).
2. **Track-Aware Diagnostics Active**: The validator audits physical track existence, direction alignment, and adjacent-track fouling envelopes (`_check_track_spatial_safety()` in `backend/app/services/validation/checks.py#L397-L545`).
3. **No Track-Aware Optimization**: As proved in Phase 16H, CP-SAT cannot safely schedule at the track level because TrackMeld currently lacks track continuity, switch topology, and calibrated clearance envelopes.
4. **No Physical Topology in Current Code**: As proved in Phase 16I-A, tracks exist only as isolated children of block sections. There are zero models for turnouts, crossovers, points, switches, platform lines, or track continuity.

---

## 2. Current Infrastructure Model to Target Model

### 2.1. Current Implemented Model
The existing infrastructure schema is strictly hierarchical and macro-oriented:

```
[StationModel] (STN-NDLS) ───────── from_station_id ────────┐
                                                            ▼
[StationModel] (STN-GZB)  ───────── to_station_id   ───► [SectionModel] (SEC-NDLS-GZB)
                                                            │
                                                            ├── track_count = 2
                                                            │
                                                            ├──► [TrackModel] (TRK-SEC-NDLS-GZB-UP)
                                                            │      ├── direction = "UP"
                                                            │      └── adjacent_track_ids = ["TRK-SEC-NDLS-GZB-DN"]
                                                            │
                                                            └──► [TrackModel] (TRK-SEC-NDLS-GZB-DN)
                                                                   ├── direction = "DOWN"
                                                                   └── adjacent_track_ids = ["TRK-SEC-NDLS-GZB-UP"]
```

- **`StationModel`** (`backend/app/db/models/station.py`): Point vertex representing a station node (`station_id`, `station_code`, `route_km`, `station_type`). Contains zero platform, track, or switch definitions.
- **`SectionModel`** (`backend/app/db/models/section.py`): Contiguous corridor edge between two station nodes (`section_id`, `from_station_id`, `to_station_id`, `length_km`, `track_count`).
- **`TrackModel`** (`backend/app/db/models/track.py`): Running line scoped under a parent section (`track_id`, `section_id`, `track_code`, `direction`, `adjacent_track_ids`). Contains zero cross-section continuity links.

### 2.2. Candidate Target Conceptual Model
To support track-aware decision support truthfully, TrackMeld requires an additive topology layer that models physical connectivity at corridor boundaries without replacing macro entities:

```
[Section SEC-A]                               [Station Junction STN-J]                             [Section SEC-B]
┌─────────────────────────────────┐           ┌────────────────────────────────────────┐           ┌─────────────────────────────────┐
│ Track A-UP                      │           │ TopologyNode: J-UP-ENTRY               │           │ Track B-UP                      │
│   Endpoint: A-UP-END ───────────┼──────────►│   ├── Connection (Normal): Through     │──────────►│   Endpoint: B-UP-START          │
│                                 │           │   └── Connection (Reverse): Crossover  │──┐        │                                 │
├─────────────────────────────────┤           │                                        │  │        ├─────────────────────────────────┤
│ Track A-DN                      │           │ TopologyNode: J-DN-ENTRY               │  │        │ Track B-DN                      │
│   Endpoint: A-DN-START ◄────────┼───────────│   ◄────────────────────────────────────┼──┴────────┼── Endpoint: B-DN-END            │
└─────────────────────────────────┘           └────────────────────────────────────────┘           └─────────────────────────────────┘
```

### 2.3. Categorical Status of Infrastructure Concepts

| Infrastructure Concept | Categorical Status | Current Representation in Repository | Target Role |
| :--- | :--- | :--- | :--- |
| **Block Section** | **CURRENT IMPLEMENTED** | `SectionModel` (`sections.section_id`) | Macro corridor container and absolute possession boundary |
| **Running Track** | **CURRENT IMPLEMENTED** | `TrackModel` (`tracks.track_id`) | Physical rail segment within section bounds |
| **Track Adjacency** | **CURRENT IMPLEMENTED** | `TrackModel.adjacent_track_ids` | Lateral proximity for fouling and clearance audits |
| **Station Node** | **CURRENT IMPLEMENTED** | `StationModel` (`stations.station_id`) | Macro geographical network vertex |
| **Track Endpoints** | **PROPOSED DOMAIN CONCEPT** | Absent (implicit at section bounds) | Boundary ports where tracks interface with junctions |
| **Topology Connection** | **PROPOSED DOMAIN CONCEPT** | Absent | Physical link joining two track endpoints across a node |
| **Topology Node** | **PROPOSED DOMAIN CONCEPT** | Absent | Point of continuity, divergence, or convergence |
| **Route Path** | **PROPOSED DOMAIN CONCEPT** | Absent (`TrainTraversal` has section path only) | Ordered sequence of connected tracks forming a movement |
| **Platform Lines** | **NOT YET ESTABLISHED** | Absent | Passenger stopping berths inside stations |
| **Switch Blades / Turnouts** | **NOT YET ESTABLISHED** | Absent | Microscopic mechanical point geometry |
| **Interlocking Logic / Signal Aspects** | **NOT YET ESTABLISHED** | Absent | Signal aspects, route locking, track circuits |

---

## 3. Proposed Topology Vocabulary

To establish semantic precision before specifying schemas, the following candidate definitions are formulated:

1. **Infrastructure Element**: Any physical or geographic asset on the railway network (e.g. section, track, station, node).
2. **Topology Node**: A discrete junction point on the infrastructure graph where track endpoints meet, continue, terminate, or diverge (e.g. station boundary joint, throat junction).
3. **Topology Endpoint**: The physical boundary termination of a specific running track (e.g. `UP_START` at section origin, `UP_END` at section terminus).
4. **Topology Connection**: A permitted physical rail path linking an outbound track endpoint to an inbound track endpoint through a topology node.
5. **Track Segment**: A contiguous piece of physical track bounded by two specific endpoints with uniform characteristics (gauge, electrification, line speed).
6. **Track Continuity**: An invariant relationship where an endpoint of Track $A$ directly aligns with an endpoint of Track $B$ without crossing points or turnouts.
7. **Physical Adjacency**: A lateral relationship where Track $A$ runs parallel to Track $B$ within the same corridor such that an activity or incident on Track $A$ may foul Track $B$.
8. **Route Candidate**: An operationally valid, directed sequence of continuous or connected tracks that a train could physically traverse between its journey endpoints.
9. **Junction**: A location where two or more tracks converge or diverge, permitting route choice.
10. **Branch (Facing Divergence)**: A point where a single incoming track splits into two or more outgoing tracks.
11. **Merge (Trailing Convergence)**: A point where two or more incoming tracks converge into a single outgoing track.
12. **Crossover**: A pair of turnouts connecting two parallel tracks, allowing trains on Track 1 to switch to Track 2.
13. **Turnout / Point**: A movable track mechanism that directs rolling stock from one track to another. (In this specification, modeled at the meso-level via connections, not microscopic blade mechanics).
14. **Station Transition**: The topological interface where open-corridor section tracks enter the station junction zone.
15. **Platform Association**: The linkage between a passenger train stop and a specific platform track inside a station.
16. **Directional Connectivity**: A property of a connection indicating whether movement across it is permitted in the Forward direction, Reverse direction, or Both.

---

## 4. Critical Semantic Distinctions

Forensic discovery in Phase 16I-A established that confusing spatial proximity with longitudinal connectivity causes catastrophic optimization errors. TrackMeld strictly isolates these five concepts:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ FIVE FUNDAMENTALLY DISTINCT SPATIAL / TOPOLOGICAL RELATIONS                 │
├──────────────────────────┬──────────────────────────────────────────────────┤
│ 1. Track Adjacency       │ Lateral proximity: "Track 1 is beside Track 2." │
│                          │ Fouling envelope, ballast impact, OHE portals.   │
├──────────────────────────┼──────────────────────────────────────────────────┤
│ 2. Track Continuity      │ Longitudinal flow: "Track 1 continues into       │
│                          │ Track 2 across a boundary joint."                │
├──────────────────────────┼──────────────────────────────────────────────────┤
│ 3. Route Connectivity    │ Switchable path: "A train on Track 1 can reach   │
│                          │ Track 2 via a crossover switch."                 │
├──────────────────────────┼──────────────────────────────────────────────────┤
│ 4. Conflict Relationship │ Safety rule: "Activity A and Activity B cannot   │
│                          │ coexist simultaneously."                         │
├──────────────────────────┼──────────────────────────────────────────────────┤
│ 5. Scheduling Occupancy  │ Temporal lock: "Train T occupies Track 1 during  │
│                          │ interval [09:00, 09:15)."                        │
└──────────────────────────┴──────────────────────────────────────────────────┘
```

### Inviolable Separation Rules:
- **Rule 4.1**: `adjacent_track_ids` must **never** be interpreted as a route path.
- **Rule 4.2**: The existence of a physical `TopologyConnection` between two tracks does **not** imply that movements across them are conflict-free.
- **Rule 4.3**: A conflict relationship is a domain rule outcome, not an infrastructure attribute.
- **Rule 4.4**: Scheduling occupancy belongs to the solver and timetable layer; it must not be hardcoded into topology tables.

---

## 5. Evaluation of Topology Representation Options

The five representation candidates investigated in Phase 16I-A are evaluated systematically:

| Dimension | Option A: Track Pointers (`next_track_id`) | Option B: Microscopic Node/Edge Graph | Option C: Track Endpoints & Connections (Meso Port Model) | Option D: Explicit Pre-Defined Routes | Option E: Infrastructure Conflict Matrix |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **What it Represents** | Simple 1:1 track link across section boundary | Full CAD/GIS switch blades, points, and rail segments | Ports on track boundaries connected by junction links | Pre-enumerated corridor paths (e.g. from WTT) | Pairwise mutual exclusion lookup table |
| **What it Cannot Represent** | Branching, turnouts, crossovers, loop lines | Macro planning without overwhelming microscopic detail | Moving point mechanics; dynamic interlocking circuits | Flexible real-time path deviation | Dynamic kinematic speed and headway curves |
| **Branching (1 $\rightarrow$ N)** | **IMPOSSIBLE** (Single pointer cannot branch) | Fully supported | Supported via multiple outbound connections | Supported as separate route instances | N/A (Represents conflicts, not topology) |
| **Merging (N $\rightarrow$ 1)** | **IMPOSSIBLE** | Fully supported | Supported via multiple inbound connections | Supported as separate route instances | N/A |
| **Directional Semantics** | Bidirectional lines fail completely | Supported via directed edges | Supported via connection direction attribute | Supported (routes are inherently directed) | N/A |
| **Station Transitions** | Fails at multi-track stations | Microscopic track layout | Meso station throat connections | End-to-end station passage | N/A |
| **Crossovers** | **IMPOSSIBLE** | Supported as 2 turnout nodes + connecting edge | Supported as diagonal connection between endpoints | Supported | Direct conflict pair: `(UP, DN)` |
| **Route Derivation** | Trivial follow-pointer, but wrong at junctions | Complex graph traversal (Dijkstra / DFS) | Clean graph search over endpoints and connections | Direct lookup of route code | N/A |
| **Validator Usage** | Inadequate for track safety proofs | Extreme overhead for schedule auditing | Verifies path continuity and conflict isolation | Audits train conformance to assigned route | Audits pairwise concurrent assignments |
| **CP-SAT Usage** | N/A | Unusable in CP-SAT (combinatorial explosion) | Enables hierarchical resource allocation | Enables route-choice integer variables | Enables explicit clique/no-overlap constraints |
| **Migration Complexity** | Minimal (1 column) | Extreme (new spatial engine required) | Moderate (additive tables, clean FKs) | Moderate (route tables) | Moderate (conflict tables) |
| **Risks of False Assumptions** | **CRITICAL RISK**: Fabricates false 1:1 continuity | High risk of data gaps halting the system | Low risk: unmodeled connections remain unresolved | Risk of missing non-standard operational paths | Risk of stale or incomplete conflict pairs |

---

## 6. Candidate Domain Concepts (Meso-Level Port Model)

To balance mathematical rigor, auditability, and data availability, TrackMeld specifies a **Meso-Level Endpoint & Connection Model** (combining the strengths of Option C with Option D for route assignments).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ CANDIDATE ENTITY RELATIONSHIP MODEL                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  [SectionModel]                                                            │
│       │ 1                                                                   │
│       │ has many (1:N)                                                      │
│       ▼                                                                     │
│  [TrackModel] (TRK-SEC-01-UP)                                               │
│       │ 1                                                                   │
│       │ has exactly two (1:2)                                               │
│       ▼                                                                     │
│  [TrackEndpoint] (EP-TRK-SEC-01-UP-START, EP-TRK-SEC-01-UP-END)             │
│       │                                                                     │
│       │ from_endpoint_id                                                    │
│       ▼                                                                     │
│  [TopologyConnection] ◄── to_endpoint_id ── [TrackEndpoint]                 │
│       │                                                                     │
│       │ located at                                                          │
│       ▼                                                                     │
│  [TopologyNode] (NODE-STN-GZB-THROAT-WEST)                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Detailed Entity Specifications

#### 1. `Track` (Existing, Retained)
- **Why It Exists**: Represents a physical running line within a block section.
- **What It Represents**: Continuous rail between two section endpoints.
- **What It Must NOT Represent**: Cross-section continuity or switch positions.
- **Required**: **NOW** (Already implemented in Phase 16A).

#### 2. `TrackEndpoint` (Proposed)
- **Why It Exists**: Tracks must terminate at defined geographic boundaries where they interface with junctions, stations, or adjacent sections.
- **What It Represents**: The physical boundary joint of a track (e.g. `START` at lower kilometrage, `END` at higher kilometrage).
- **What It Must NOT Represent**: A route, switch, or timetable event.
- **Required**: **Phase 16I-C**.

#### 3. `TopologyNode` (Proposed)
- **Why It Exists**: Identifies physical junction points where track endpoints meet (e.g. station throats, block boundaries, crossover zones).
- **What It Represents**: A physical network junction or boundary joint.
- **What It Must NOT Represent**: An operational train schedule or timetable event.
- **Required**: **Phase 16I-C**.

#### 4. `TopologyConnection` (Proposed)
- **Why It Exists**: Declares permitted traversals from an outbound endpoint to an inbound endpoint across a node.
- **What It Represents**: A permanent physical rail connection (straight continuity, turnout divergence, crossover diagonal).
- **What It Must NOT Represent**: Dynamic switch blade status or route reservation locks.
- **Required**: **Phase 16I-C**.

#### 5. `RoutePath` (Proposed for Future Phase 16J)
- **Why It Exists**: Trains follow pre-determined sequences of tracks through corridors.
- **What It Represents**: An ordered list of `(Track, TopologyConnection)` segments from origin to destination.
- **What It Must NOT Represent**: Real-time train location or speed.
- **Required**: **Phase 16J** (Train Route Assignment).

---

## 7. Track Identity Architecture

### 7.1. Global Uniqueness vs Section Scoping
In the current schema (`backend/app/db/models/track.py#L25-L30`):
- `track_id` is a `VARCHAR(64)` primary key.
- It is globally unique across the database, but scoped hierarchically to `section_id`.
- Example format: `TRK-{sec_code}-{suffix}` (e.g. `TRK-NDLS-GZB-UP`).

### 7.2. Evaluation of Identity Alternatives

| Identity Model | Feasibility | Impact on Existing Code | Recommendation |
| :--- | :--- | :--- | :--- |
| **Model 1: Retain Section-Local `track_id`** | High | **Zero breaking changes**. Preserves all existing FKs in `maintenance_tasks`, `train_movements`, and `validation_findings`. | **RECOMMENDED** |
| **Model 2: Universal Corridor Track ID** (e.g. `TRK-CORR-01-UP-MAIN`) | Low | Massive breaking refactor. Fails because running lines change character (e.g. 2 tracks expand to 4 tracks, then narrow to 3). | Rejected |
| **Model 3: Compound Primary Key `(section_id, track_code)`** | Moderate | Breaks existing single-string foreign keys in Postgres. | Rejected |

### 7.3. Preservation of Historical Replay
- Existing historical plans and snapshots rely on `track_id` strings.
- Retaining `track_id` as the primary identifier on `TrackModel` guarantees that past `PlanningRun` and `PlanVersion` records remain 100% reproducible.

---

## 8. Topology Versioning and Provenance

### 8.1. Why Topology Requires Versioning
If infrastructure topology drives train route derivation and track conflict modeling:
1. Physical track layout changes over time (e.g., corridor doubling, adding a loop line, installing a new crossover, commissioning a new platform).
2. A maintenance plan scheduled under 2026 topology cannot be re-validated or replayed under 2028 topology without producing false errors.
3. Therefore, topology must possess **cryptographic and temporal provenance**.

### 8.2. Specification of Topology Provenance
Each topology record (node, connection) must incorporate TrackMeld's standard provenance fields:
- `classification`: `DataClass` (`REAL`, `DERIVED`, `SYNTHETIC`, `DEMO_ONLY`).
- `source_id`: Foreign key referencing the engineering scale plan (ESP) or Working Time Table (WTT).
- `topology_version`: Version string (e.g. `TOPOLOGY-V1.0-2026`) linking the graph to a scenario.

---

## 9. Direction Semantics

### 9.1. Track Direction Metadata vs Traversal Direction
TrackMeld must explicitly distinguish:
1. **Nominal Track Direction** (`TrackModel.direction`):
   - Enum: `UP`, `DOWN`, `BIDIRECTIONAL`.
   - Represents the infrastructure design intent under standard timetable operation.
2. **Topological Traversal Direction** (`TopologyConnection.traversal_direction`):
   - Directed flow from `from_endpoint` $\rightarrow$ `to_endpoint`.
   - When traversing a connection, the movement vector must be compatible with the track's nominal direction.

### 9.2. Direction Compatibility Rules
- If `track.direction == 'UP'`: only `UP` traversals permitted.
- If `track.direction == 'DOWN'`: only `DOWN` traversals permitted.
- If `track.direction == 'BIDIRECTIONAL'`: both `UP` and `DOWN` traversals permitted, subject to head-on collision protection (opposing-movement mutual exclusion).

---

## 10. Station Transitions

### 10.1. Meso-Level Station Representation
Without modeling microscopic switch mechanics, station junctions are represented as **Junction Nodes** bridging open-corridor section tracks:

```
Section 1 (NDLS-GZB)                        Ghaziabad Station (GZB)                    Section 2 (GZB-ALJN)
Track: TRK-NDLS-GZB-UP                     Node: NODE-GZB-THROAT                       Track: TRK-GZB-ALJN-UP
  Endpoint: EP-NDLS-GZB-UP-END  ──────►     ├── Straight Continuity ─────────────►     Endpoint: EP-GZB-ALJN-UP-START
                                            └── Crossover to DN ─────────────────┐
Track: TRK-NDLS-GZB-DN                      Node: NODE-GZB-DN-THROAT             │     Track: TRK-GZB-ALJN-DN
  Endpoint: EP-NDLS-GZB-DN-START ◄─────     ◄────────────────────────────────────┴──── Endpoint: EP-GZB-ALJN-DN-END
```

### 10.2. Permitted Station Scenarios
1. **Straight Through Track**: Connection joins `Section1-UP-END` to `Section2-UP-START` (`connection_type = CONTINUITY`).
2. **Crossover Switch**: Connection joins `Section1-UP-END` to `Section2-DN-END` (`connection_type = CROSSOVER`).
3. **Terminating Track (Bay Platform)**: Track endpoint terminates at a node with zero outgoing connections (`connection_type = BUFFER_TERMINATION`).

---

## 11. Branching and Merging Specifications

The meso-level connection model mathematically supports all railway track configurations:

### 11.1. One $\rightarrow$ Many (Divergence / Facing Switch)
- **Topology**: One outbound endpoint `EP-01` links to multiple `TopologyConnection` records:
  - Connection 1: `EP-01` $\rightarrow$ `EP-02` (Main line, position `NORMAL`)
  - Connection 2: `EP-01` $\rightarrow$ `EP-03` (Branch line, position `REVERSE`)
- **Semantics**: A train approaching `EP-01` has 2 potential routing choices.

### 11.2. Many $\rightarrow$ One (Convergence / Trailing Switch)
- **Topology**: Multiple outbound endpoints (`EP-02`, `EP-03`) link via separate connections to a single inbound endpoint `EP-04`.
- **Semantics**: Two separate lines converge onto a single running line. Mutual exclusion rules apply at the convergence zone.

### 11.3. Many $\rightarrow$ Many (Crossover Ladders)
- Supported by a matrix of directional `TopologyConnection` records connecting parallel track endpoints across a station throat node.

---

## 12. Topology, Route, and Scheduling Boundary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ CLEAR SEPARATION OF TOPOLOGY, ROUTING, SCHEDULING, AND VALIDATION           │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. TOPOLOGY LAYER (Static Infrastructure Graph)                             │
│    - Endpoints, Nodes, Connections, Adjacencies                             │
│    - "Does a physical connection exist between Track A and Track B?"        │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. ROUTE ASSIGNMENT LAYER (Deterministic Path Derivation)                   │
│    - RoutePaths, Traversal track mapping                                    │
│    - "Which permitted sequence of tracks does Train 12004 traverse?"        │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. SCHEDULING LAYER (CP-SAT Solver)                                         │
│    - Mathematical interval decision variables, start times, durations       │
│    - "At what time window does Task T or Train P occupy Track A?"           │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. VALIDATION LAYER (Independent Schedule Validator)                        │
│    - Post-solve verification of physical and temporal feasibility            │
│    - "Does any pair of activities violate track or section safety rules?"   │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Boundary Violations to Prevent**:
- The topology model must never decide train priority or departure times.
- The solver must never synthesize non-existent topology connections.
- The validator must never trust route assignment flags without verifying endpoint continuity.

---

## 13. Safety Boundary

1. **Topology is Descriptive, Not Assertive**: Stating that Track 1 connects to Track 2 does **not** mean two trains can use the connection safely without block clearance.
2. **Whole-Section Mutex Retained**: The implementation of topology in TrackMeld must **not** alter CP-SAT whole-section `AddNoOverlap` or validator `SECTION_OCCUPANCY_CONFLICT`.
3. **No Automatic Safety Declarations**: Topology provides the graph over which routes and conflicts are evaluated; it never declares a plan approvable.

---

## 14. Synthetic Data Policy

1. **No Invented Continuity**: Current synthetic tracks (`TRK-{sec_code}-UP` and `TRK-{sec_code}-DN`) must **NOT** be automatically wired into continuous corridor lines via string heuristics.
2. **Missing Topology Remains Missing**: If continuity between Section 1 and Section 2 has not been explicitly defined in a verified seed dataset, it must remain `None` / `UNRESOLVED`.
3. **Explicit Synthetic Provenance**: Any demo topology created for test scenarios must carry `classification = DEMO_ONLY`.
4. **Safety Default**: Where topology is unresolved, the system defaults to conservative whole-section exclusivity.

---

## 15. Hash and Governance Implications

### 15.1. Point of Hashing Ingestion
In Phase 16H, forensic analysis proved that `track_id`, `adjacent_track_impact`, and `tracks` are currently **not** hashed in `compute_snapshot_hash()` (`backend/app/domain/planning_snapshot.py#L45-L67`).

**Specification Rule**:
- During Phase 16I, topology remains a structural foundation and does not modify snapshot hashing.
- **At the exact phase where topology drives route assignment and solver constraints (Phase 16J/16L)**, `compute_snapshot_hash()` must be updated to include the canonical SHA-256 fingerprint of the active `topology_version` and all connection records.
- This ensures 100% cryptographic reproducibility for audits and legal inquiries.

---

## 16. Conceptual Migration Specification (No Migration Created)

The following schema objects are specified conceptually for future implementation in Phase 16I-C:

### 16.1. Table: `topology_nodes`
- `node_id`: `VARCHAR(64)` PRIMARY KEY (e.g. `NODE-STN-NDLS-EAST-THROAT`).
- `node_name`: `VARCHAR(128)` NOT NULL.
- `station_id`: `VARCHAR(32)` NULLABLE, REFERENCES `stations(station_id)` ON DELETE SET NULL.
- `node_type`: `VARCHAR(32)` NOT NULL (`'BOUNDARY_JOINT'`, `'STATION_THROAT'`, `'CROSSOVER_JUNCTION'`).
- `classification`: `VARCHAR(32)` NOT NULL DEFAULT `'DEMO_ONLY'`.
- `source_id`: `VARCHAR(64)` NOT NULL.
- Indexes: `ix_topology_nodes_station_id`.

### 16.2. Table: `track_endpoints`
- `endpoint_id`: `VARCHAR(64)` PRIMARY KEY (e.g. `EP-TRK-SEC-NDLS-GZB-UP-START`).
- `track_id`: `VARCHAR(64)` NOT NULL, REFERENCES `tracks(track_id)` ON DELETE CASCADE.
- `endpoint_type`: `VARCHAR(16)` NOT NULL CHECK (`endpoint_type IN ('START', 'END')`).
- `kilometrage`: `FLOAT` NOT NULL.
- UniqueConstraint: `("track_id", "endpoint_type")`.
- Indexes: `ix_track_endpoints_track_id`.

### 16.3. Table: `topology_connections`
- `connection_id`: `VARCHAR(64)` PRIMARY KEY (e.g. `CONN-NDLS-GZB-UP-THROUGH`).
- `node_id`: `VARCHAR(64)` NOT NULL, REFERENCES `topology_nodes(node_id)` ON DELETE RESTRICT.
- `from_endpoint_id`: `VARCHAR(64)` NOT NULL, REFERENCES `track_endpoints(endpoint_id)` ON DELETE RESTRICT.
- `to_endpoint_id`: `VARCHAR(64)` NOT NULL, REFERENCES `track_endpoints(endpoint_id)` ON DELETE RESTRICT.
- `connection_type`: `VARCHAR(32)` NOT NULL (`'CONTINUITY'`, `'TURNOUT_NORMAL'`, `'TURNOUT_REVERSE'`, `'CROSSOVER'`).
- `traversal_direction`: `VARCHAR(32)` NOT NULL DEFAULT `'FORWARD'` CHECK (`traversal_direction IN ('FORWARD', 'REVERSE', 'BIDIRECTIONAL')`).
- `max_diverging_speed_kmh`: `INTEGER` NULLABLE (e.g. 30 km/h for turnouts; NULL for straight continuity).
- `classification`: `VARCHAR(32)` NOT NULL DEFAULT `'DEMO_ONLY'`.
- UniqueConstraint: `("from_endpoint_id", "to_endpoint_id")`.
- Indexes: `ix_connections_node_id`, `ix_connections_from_ep`, `ix_connections_to_ep`.

---

## 17. Future Phase Dependencies

The architectural path forward is strictly ordered:

```
Phase 16I-A: Infrastructure Topology Discovery (Complete)
    ↓
Phase 16I-B: Domain Model & Schema Specification (CURRENT — Complete)
    ↓
Phase 16I-C: Topology Seed Migration & Repository Ingestion
    • Implement Alembic migrations for nodes, endpoints, connections
    • Expose read-only topology APIs
    • Populate curated demo topology for specific test corridor
    ↓
Phase 16J: Deterministic Train Route & Traversal Track Assignment
    • Implement RoutePath domain entities
    • Resolve TrainTraversal.traversal_track_id deterministically
    ↓
Phase 16K: Independent Validator Track-Aware Hard Verification
    • Authoritative track-level conflict verification
    • Mathematical proof of zero cross-track collision
    ↓
Phase 16L: CP-SAT Track-Aware Optimization Modeling
    • Hierarchical resource formulation
    • Controlled relaxation of whole-section mutex
```

---

## 18. Open Questions & Evidence Gaps

The following domain requirements remain cataloged as:  
`UNRESOLVED / REQUIRES DOMAIN EVIDENCE`

1. `[UNRESOLVED / REQUIRES DOMAIN EVIDENCE]`: What are the standard turnout speed restrictions (e.g. 1 in 8.5 vs 1 in 12 turnouts: 15 km/h vs 30 km/h) for Indian Railways Broad Gauge, and how should they affect traversal timing?
2. `[UNRESOLVED / REQUIRES DOMAIN EVIDENCE]`: When a crossover between UP and DOWN lines is under maintenance possession, does IR regulation require blocking both running lines or only the line where the physical work occurs?
3. `[UNRESOLVED / REQUIRES DOMAIN EVIDENCE]`: What official electronic format (e.g. railML, GIS shapefiles, or ESP tables) is available from Indian Railways for importing authentic yard topology?

---

## 19. Explicit Non-Goals

1. **No Microscopic Interlocking Simulation**: TrackMeld will not simulate relay logic, route-locking circuits, or track circuit drop delays.
2. **No Dynamic Signal Sighting**: TrackMeld will not calculate optical signal sighting distances or braking deceleration curves.
3. **No Autonomous Route Setting**: TrackMeld will not issue commands to electronic interlocking equipment.
4. **No Premature Optimization Relaxation**: TrackMeld will not relax the section-level CP-SAT mutex during topology modeling.

---

## 20. Conclusion

1. **Meso-Level Port Model (Option C + D) is the appropriate paradigm**: Modeling tracks with boundary endpoints and junction connections provides physical continuity without the impossible complexity of microscopic switch blade CAD data.
2. **Strict Semantic Isolation Maintained**: Adjacency, continuity, route connectivity, conflict rules, and scheduling occupancy remain completely distinct.
3. **Zero Impact on Current Safety**: Whole-section mutual exclusion remains 100% active in CP-SAT and the Independent Validator.
4. **Next Step**: Phase 16I-C can proceed to implement the specified schema migrations, repository interfaces, and curated demo topology.
