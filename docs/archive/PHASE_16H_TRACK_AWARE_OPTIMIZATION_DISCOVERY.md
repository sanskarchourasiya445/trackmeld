# Phase 16H — Track-Aware Optimization Discovery

**Status**: Discovery & Architecture Audit Only  
**Date**: October 2026  
**Baseline HEAD**: `168d8e3` (`feat(phase-16g): add track-aware validator diagnostic and safety extension`)  
**Branch**: `main` (synchronized with `origin/main`)  
**Working Tree**: Clean  

---

## 1. Baseline & Current Safety Boundary

### 1.1. Core Architectural Boundary
TrackMeld operates under a strict separation of concerns:
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
- **Rules classify**: Domain rules establish spatial, temporal, and operational compatibility.
- **Optimization schedules**: Mathematical solvers (Google OR-Tools CP-SAT) search the feasible space defined by the rules to optimize maintenance throughput and priority.
- **Independent Validator verifies**: An isolated validation engine independently reproduces all physical, safety, and operational constraints without trusting the solver.
- **Human reviews & approves**: Railway planners and safety controllers retain exclusive authority to approve, reject, or modify schedules.
- **Product boundary**: TrackMeld is a **decision-support prototype**. It never issues live signalling, route-locking, interlocking, or dispatch commands.

### 1.2. Active Spatial Safety Baseline
Prior to Phase 16H, the following spatial progression occurred:
1. **Phase 16A–16C**: Introduced `TrackModel` under `SectionModel`, optional `track_id`, `from_km`, `to_km`, and `adjacent_track_impact` on `MaintenanceTaskModel`, and optional `track_id` on `TrainMovementModel`.
2. **Phase 16E-A & 16E-B**: Added spatial safety enums (`AdjacentTrackImpact`) and deterministic train section traversal expansion (`TrainTraversal`).
3. **Phase 16G-A**: Implemented pure deterministic spatial compatibility classification (`evaluate_spatial_compatibility`).
4. **Phase 16G-C**: Added track-aware diagnostic checks to the Independent Validator (`_check_track_spatial_safety`).

**The Hard Safety Invariant**:
Despite these domain additions, **CP-SAT and the Independent Validator enforce whole-section mutual exclusion**.
- In CP-SAT: Every task possession and train pass in section $S$ participates in `model.AddNoOverlap([intervals_in_S])`.
- In the Validator: `_check_section_occupancy` generates `SECTION_OCCUPANCY_CONFLICT` (`ERROR`) for any concurrent tasks in section $S$, and `_check_train_movements` generates `TRAIN_MOVEMENT_CONFLICT` (`ERROR`) for any concurrent task and train pass in section $S$.
- **Different tracks within the same section CANNOT coexist in a valid schedule.**
- `TrainTraversal.traversal_track_id` is explicitly `None` (unresolved).
- CAUTION_ORDER is advisory (`INFO`), not an optimization constraint.
- No turnout, interlocking, signal headway, or kinematic braking model exists.

---

## 2. Current Optimization Resource Model

### 2.1. Mathematical Variables in CP-SAT
The CP-SAT model builder (`CPSATModelBuilder` in `backend/app/services/optimization/cp_sat_model.py`) translates the immutable `PlanningSnapshot` into integer programming decision variables:

| Domain Entity | Variable Name in CP-SAT | Variable Type | Domain / Bounds | Location in Code |
| :--- | :--- | :--- | :--- | :--- |
| **Task Presence** | `presence_{task_id}` | `cp_model.BoolVar` | $\{0, 1\}$ (forced to 1 if `mandatory=True`) | `cp_sat_model.py#L123-L129` |
| **Task Work Interval** | `interval_{task_id}` | `cp_model.IntervalVar` | Optional interval: `start_var`, `duration`, `end_var`, `presence` | `cp_sat_model.py#L158` |
| **Task Possession** | `pos_interval_{task_id}` | `cp_model.IntervalVar` | Optional envelope: `[start - buf_before, end + buf_after)` | `cp_sat_model.py#L165` |
| **Train Pass** | `train_{tp.pass_id}_{sec_id}` | `cp_model.IntervalVar` | Fixed-size interval: `[clamped_start, clamped_dur]` | `cp_sat_model.py#L226-L229` |
| **Resource Unavailability** | `unavail_{r_id}_{u_start}` | `cp_model.IntervalVar` | Fixed-size interval covering unavailable crew/machine windows | `cp_sat_model.py#L287-L290` |

### 2.2. Resource Keys and Mutex Construction
The solver models resource exclusivity via `model.AddNoOverlap()` on two distinct resource types:
1. **Spatial Sections (`sec_id`)**:
   - `tasks_by_sec` groups `pos_intervals[task_id]` by `sec_id` across `primary_sec` and `additional_sections` (`cp_sat_model.py#L196-L200`).
   - `train_passes_by_sec` groups fixed-size train intervals by `tp.section_id` (`cp_sat_model.py#L190-L194`).
   - For every active section, `cp_sat_model.py#L232` executes:
     ```python
     if len(section_intervals) > 1:
         self.model.AddNoOverlap(section_intervals)
     ```
   - **Resource Key**: The sole spatial resource key is `sec_id` (the whole block section ID). Track identity does not exist in this key.
2. **Crew & Equipment Resources (`r_id`)**:
   - `tasks_by_res` groups `task_intervals[task_id]` by required resource identifier (`cp_sat_model.py#L237-L240`).
   - `cp_sat_model.py#L293` executes `self.model.AddNoOverlap(res_intervals)` for each resource.

### 2.3. Train Traversal vs Train Pass in CP-SAT
- **Does `TrainTraversal` reach CP-SAT?** **NO.**
- **Where information gets lost**:
  - `PlanningSnapshot.from_bundle()` invokes `CompatibilityEngine.expand_train_traversals()` (`backend/app/domain/planning_snapshot.py#L177-L186`) and persists `train_traversals` on the snapshot.
  - However, `CPSATModelBuilder` (`backend/app/services/optimization/cp_sat_model.py#L191`) iterates **strictly** over `self.snapshot.train_passes`.
  - `TrainTraversal` is completely ignored during constraint generation.
  - Furthermore, `TrainPass` has no `track_id` parameter (`backend/app/domain/temporal.py#L129-L148`), while `TrainTraversal.traversal_track_id` is initialized to `None` (`backend/app/services/compatibility_service.py#L243, L266`).

### 2.4. Visibility Matrix: Optimization vs Validator vs Descriptive

| Field / Attribute | Entity | Optimization-Visible? | Validator-Visible? | Role in System |
| :--- | :--- | :--- | :--- | :--- |
| `task.section_id` | `MaintenanceTask` | **YES** (`cp_sat_model.py#L198`) | **YES** (`checks.py#L65`) | Primary spatial conflict key |
| `task.additional_sections` | `MaintenanceTask` | **YES** (`cp_sat_model.py#L108`) | **YES** (`checks.py#L108`) | Multi-section spatial corridor block |
| `task.track_id` | `MaintenanceTask` | **NO** (Ignored) | **YES** (`checks.py#L420`) | Track existence & direction validation |
| `task.from_km`, `task.to_km` | `MaintenanceTask` | **NO** (Ignored) | **YES** (Evaluated in `checks.py#L457`) | Worksite longitudinal chainage |
| `task.adjacent_track_impact` | `MaintenanceTask` | **NO** (Ignored) | **YES** (`checks.py#L457`) | Lateral fouling & block audit |
| `task.direction` | `MaintenanceTask` | **NO** (Ignored) | **YES** (`checks.py#L438`) | Directional track alignment check |
| `tp.section_id` | `TrainPass` | **YES** (`cp_sat_model.py#L192`) | **YES** (`checks.py#L320`) | Whole-section train clearance key |
| `tp.track_id` | `TrainPass` | **NO** (Ignored) | **YES** (`checks.py#L490`) | Train track assignment audit |
| `track.adjacent_track_ids` | `Track` | **NO** (Ignored) | **YES** (`checks.py#L457`) | Adjacency relationship graph |
| `track.direction` | `Track` | **NO** (Ignored) | **YES** (`checks.py#L439`) | Unidirectional travel constraint |
| `train_traversals` | `PlanningSnapshot` | **NO** (Ignored) | **YES** (`checks.py#L448`) | Traversal existence audit |
| `section.electrified` | `Section` | **YES** (`cp_sat_model.py#L173`) | **YES** (`checks.py#L240`) | Power block feasibility check |

---

## 3. Current Semantics Matrix

The following matrix documents the exact behavior of TrackMeld across spatial, operational, and metadata configurations:

| Occupant Pair / Scenario | Current CP-SAT Behavior | Current Validator Behavior | Phase 16G Compatibility Result | Semantic Status | Required Evidence Before Changing |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Task vs Task: Same track** | Blocked by whole-section `AddNoOverlap` | `SECTION_OCCUPANCY_CONFLICT` (`ERROR`) | `INCOMPATIBLE` (`SAME_TRACK_OVERLAP`) | Intentional & Sound | None; same-track overlap is physically impossible. |
| **Task vs Task: Different tracks, NONE impact** | Blocked by whole-section `AddNoOverlap` | `SECTION_OCCUPANCY_CONFLICT` (`ERROR`) | `COMPATIBLE` (`DIFFERENT_TRACKS_INDEPENDENT`) | **Conservative Barrier** | Physical track clearance proof, lateral boundary verification, safety buffer validation. |
| **Task vs Task: Adjacent tracks, FULL_TRAFFIC_BLOCK** | Blocked by whole-section `AddNoOverlap` | `SECTION_OCCUPANCY_CONFLICT` (`ERROR`) + `ADJACENT_TRACK_FULL_BLOCK` (`ERROR`) | `INCOMPATIBLE` (`ADJACENT_TRACK_FULL_BLOCK`) | Intentional & Sound | None; lateral fouling blocks adjacent line. |
| **Task vs Task: Adjacent tracks, CAUTION_ORDER** | Blocked by whole-section `AddNoOverlap` | `SECTION_OCCUPANCY_CONFLICT` (`ERROR`) + `ADJACENT_TRACK_CAUTION_REQUIRED` (`INFO`) | `COMPATIBLE` (`DIFFERENT_TRACKS_INDEPENDENT`, `requires_caution_order=True`) | **Conservative Barrier** | Speed restriction model, crew safety regulations, train dispatching protocol. |
| **Task vs Task: Non-adjacent tracks** (e.g. Track 1 & Track 3) | Blocked by whole-section `AddNoOverlap` | `SECTION_OCCUPANCY_CONFLICT` (`ERROR`) | `COMPATIBLE` (`DIFFERENT_TRACKS_INDEPENDENT`) | **Conservative Barrier** | Accurate multi-track section topology, middle track isolation rules. |
| **Task vs Task: Different sections** | Independent (No constraint) | Valid (No conflict) | `COMPATIBLE` (`DIFFERENT_SECTIONS`) | Intentional & Sound | None. |
| **Task vs Train Pass: Same section, any track** | Blocked by whole-section `AddNoOverlap` | `TRAIN_MOVEMENT_CONFLICT` (`ERROR`) | Not directly paired in CP-SAT (Pass treated as section interval) | Intentional & Sound | Section-level clearance is the railway default. |
| **Task vs Train Pass: Adjacent track, FULL_TRAFFIC_BLOCK** | Blocked by whole-section `AddNoOverlap` | `TRAIN_MOVEMENT_CONFLICT` (`ERROR`) + `ADJACENT_TRACK_FULL_BLOCK` (`ERROR`) | `INCOMPATIBLE` (`ADJACENT_TRACK_FULL_BLOCK`) | Intentional & Sound | None; train cannot run through lateral fouling block. |
| **Task vs Train Pass: Adjacent track, CAUTION_ORDER** | Blocked by whole-section `AddNoOverlap` | `TRAIN_MOVEMENT_CONFLICT` (`ERROR`) + `ADJACENT_TRACK_CAUTION_REQUIRED` (`INFO`) | `COMPATIBLE` (`requires_caution_order=True`) | **Conservative Barrier** | Dynamic timetable dilation model; train deceleration/acceleration curves. |
| **Train Traversal vs Train Traversal** | Not modeled in CP-SAT (Timetable assumed fixed) | Not evaluated for conflict (Timetable assumed conflict-free) | `COMPATIBLE` (or unclassified) | Intentional (Prototype Scope) | Signal headway model, block section block-overlap rules, timetable validation. |
| **Single-line section** | Blocked by whole-section `AddNoOverlap` | `SECTION_OCCUPANCY_CONFLICT` (`ERROR`) | `INCOMPATIBLE` (`SAME_TRACK_OVERLAP` or `WHOLE_SECTION_OCCUPANCY`) | Intentional & Sound | Track count = 1 implies whole-section is track-level. |
| **Bidirectional section** | Blocked by whole-section `AddNoOverlap` | `SECTION_OCCUPANCY_CONFLICT` (`ERROR`) | Depends on direction alignment | Conservative | Opposing train protection rules, crossing-loop topology. |
| **Task direction contradicts track direction** | Solver does not inspect direction; places if section free | `TRACK_DIRECTION_CONFLICT` (`ERROR`) | `INCOMPATIBLE` (`DIRECTION_CONFLICT`) | **Dangerous Solver Gap** (Prevented by Validator) | CP-SAT must reject or validator must block approval. (Validator currently blocks). |
| **Missing track metadata (`track_id=None`)** | Placed on section | Handled by section check | `INCOMPATIBLE` (`WHOLE_SECTION_OCCUPANCY`) | Intentional & Conservative | Unspecified track must claim entire section. |
| **Missing adjacency metadata (`adjacent_track_ids=None`)** | Placed on section | `SPATIAL_METADATA_INCOMPLETE` (`INFO`) | `INSUFFICIENT_DATA` (`MISSING_ADJACENCY_METADATA`) | Conservative Diagnostic | Adjacency survey data must be provided. |
| **Unresolved traversal (`traversal_track_id=None`)** | Solver ignores traversal; uses pass section | Validates cleanly without error | `INCOMPATIBLE` (`WHOLE_SECTION_OCCUPANCY`) if paired | Conservative Default | Physical route/track resolution engine. |

---

## 4. Track-Aware Resource Model Candidates

Before modifying optimization, TrackMeld must rigorously evaluate candidate resource models without preselecting one as "best" or "standard":

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ CANDIDATE ARCHITECTURAL MODELS                                              │
├──────────────────────┬──────────────────────┬───────────────────────────────┤
│ Model A: Section Mutex│ Model B: Track Mutex │ Model C: Hierarchical Envelope│
│                      │                      │                               │
│   [Section SEC-01]   │   [Track UP]  [Track DN]   │   [Section SEC-01]            │
│   ┌────────────────┐ │   ┌────────┐  ┌────────┐   │   ┌───[Track UP]──────────┐   │
│   │ Exclusive Lock │ │   │ Mutex  │  │ Mutex  │   │   │   + Lateral Envelope  │   │
│   └────────────────┘ │   └────────┘  └────────┘   │   └───[Track DN]──────────┘   │
└──────────────────────┴──────────────────────┴───────────────────────────────┘
```

### Model A: Section-Only Mutex (Status Quo)
- **Required Data**: `section_id`, `task.section_id`, `train_pass.section_id`.
- **Conflict Semantics**: Exactly one occupant per section interval: $\text{NoOverlap}(\{T_i, P_j \mid \text{section}(T_i) = S\})$.
- **What it Represents**: Conservative absolute block section possession; guaranteed zero collision risk.
- **What it Cannot Represent**: Simultaneous work and train running on parallel tracks of double-line sections.
- **Failure Modes**: Artificial capacity bottlenecks; unnecessary task rejections.
- **CP-SAT / Validator Implications**: Simple, linear scaling, zero false-safe risk.
- **TrackMeld Sufficiency**: 100% supported by current data and code.

### Model B: Track-Only Mutex
- **Required Data**: Explicit `track_id` on every task and train pass.
- **Conflict Semantics**: Exclusivity enforced per physical track: $\text{NoOverlap}(\{T_i, P_j \mid \text{track}(T_i) = \text{TRK}\})$.
- **What it Represents**: Independent running lines operating with zero lateral interaction.
- **What it Cannot Represent**: Lateral fouling, crane swing encroachment, ballast shoulder destabilization, traction power isolation boundaries.
- **Failure Modes**: **Catastrophic safety failure**: Permits trains at 130 km/h on Track Down while a heavy tamping machine operates on adjacent Track Up with ballast excavation undercutting the track bed.
- **CP-SAT / Validator Implications**: Relaxes all cross-track constraints; dangerous without lateral protection.
- **TrackMeld Sufficiency**: **INSUFFICIENT**. TrackMeld has no physical clearance/distance data between track centerlines.

### Model C: Hierarchical Section $\rightarrow$ Track $\rightarrow$ Safety Envelope
- **Required Data**: `section_id`, `track_id`, `adjacent_track_ids`, `adjacent_track_impact`, chainage `[from_km, to_km]`.
- **Conflict Semantics**:
  - Primary track: Hard `NoOverlap` on assigned `track_id`.
  - Adjacent track: Hard `NoOverlap` on adjacent tracks **only if** `adjacent_track_impact = FULL_TRAFFIC_BLOCK` and chainage intervals overlap.
  - Caution order: Advisory notification or travel time dilation if `adjacent_track_impact = CAUTION_ORDER`.
- **What it Represents**: Railway possession engineering practice: main possession envelope with conditional adjacent line protection.
- **What it Cannot Represent**: Dynamic interlocking routes, switch fouling points, diamond crossings.
- **Failure Modes**: Incomplete adjacency metadata causes failure to protect adjacent line; missing chainage causes conservative full-track block.
- **CP-SAT / Validator Implications**: Conditional CP-SAT intervals (`presence` variables on adjacent track virtual intervals).
- **TrackMeld Sufficiency**: Partially supported in domain (Phase 16G-A), but track continuity and calibrated braking models are absent.

### Model D: Explicit Infrastructure Conflict Graph
- **Required Data**: Full topological node-edge graph of track circuits, turnout points, fouling points, interlocking route tables, and signal aspect sequences.
- **Conflict Semantics**: Graph vertex / edge reservation table. An activity locks a subgraph of infrastructure resources (e.g. Route $R_1$ locks Points 101, 102, Track Circuit TC-04).
- **What it Represents**: Real-world electronic interlocking / Computer Based Interlocking (CBI) safety logic.
- **What it Cannot Represent**: Broad macro-level corridor planning without microscopic data.
- **Failure Modes**: Combinatorial explosion in CP-SAT; extreme data acquisition overhead.
- **CP-SAT / Validator Implications**: Requires discrete resource locking model rather than interval-based scheduling.
- **TrackMeld Sufficiency**: **COMPLETELY INSUFFICIENT**. TrackMeld has no switch, point, turnout, or track circuit data.

---

## 5. Track Continuity Findings

### 5.1. The Local Track ID Problem
In the current TrackMeld database schema (`backend/app/db/models/track.py#L25-L35`):
- `track_id` has a foreign key to `sections.section_id`.
- Track IDs are local to a specific section (e.g. `TRK-SEC-NDLS-GZB-UP` and `TRK-SEC-GZB-ALJN-UP`).
- **There is no relationship connecting Track A in Section 1 to Track B in Section 2.**

### 5.2. Why `Track.next_track_id` is Insufficient
A naive proposal might suggest adding a foreign key `next_track_id: Optional[str]` to `TrackModel`. Forensic examination demonstrates this is fundamentally inadequate for railway infrastructure:

```
Station Throat / Junction Divergence:

Section 1 (Double Track)             Station Junction            Section 2 (Triple Track)
───────────────── Track UP ─────────┬── Turnout 1A ───────────── Track UP SLOW ─────
                                    └── Cross-over 1B ────────── Track UP FAST ─────
───────────────── Track DOWN ───────┬── Turnout 2A ───────────── Track DOWN ────────
                                    └── Siding 2B ────────────── Loop Line ─────────
```

1. **Turnouts and Point Switches**: At a junction, a single running track diverges into 2 or 3 routes depending on point orientation. A static `next_track_id` pointer cannot represent route divergence.
2. **Crossovers**: Parallel tracks have crossover switches permitting trains to switch from UP to DOWN lines.
3. **Station Platform Disconnect**: Block sections terminate at station outer signals; tracks inside stations are platform lines, reception lines, or shunting necks. Section tracks do not directly abut adjacent section tracks without traversing station interlocking.
4. **Bidirectional Lines**: A track supporting `BIDIRECTIONAL` traffic has two completely different "next" tracks depending on the train's direction of travel.
5. **Single-Line Crossing Loops**: A single-line section splits into two loop tracks at an intermediate crossing station to allow train crossings, then merges back into a single track.

**Conclusion**: Track continuity cannot be solved with a simple foreign key pointer. It requires a directed route/topology relationship or station-switch connectivity model.

---

## 6. Train Traversal Track Assignment Findings

In Phase 16E-B, `TrainTraversal` was defined with:
```python
traversal_track_id: Optional[str] = Field(default=None, description="Physical running track ID (None in Phase 16E-B, unassigned)")
```

### 6.1. Information Required to Assign Traversal Tracks
To safely map a train traversal to a physical track `track_id`, the system requires:
1. **Direction Matching**: Train movement direction must match track `supported_direction`.
2. **Station Platform/Line Assignment**: For stopping trains, the platform track at `from_station_id` and `to_station_id`.
3. **Through/Express Route Consistency**: For non-stopping trains, whether the train uses the FAST line or SLOW line.
4. **Topological Feasibility**: Proof that a turnout route exists connecting the arrival track to the departure track.

### 6.2. Architectural Options for Traversal Track Assignment

| Option | Description | Trade-offs | Feasibility with Current Data |
| :--- | :--- | :--- | :--- |
| **Option 1: Explicit Timetable Input** | Timetable records explicitly specify `track_id` for every section traversal. | Zero ambiguity; solver has fixed train track intervals. However, real-world passenger timetables rarely publish section track assignments. | Low (Track IDs not in public timetables). |
| **Option 2: Deterministic Pre-Solve Derivation** | Rule engine assigns tracks based on nominal direction (e.g. UP trains $\rightarrow$ UP track; DOWN trains $\rightarrow$ DOWN track). | Simple and deterministic for pure double-track corridors. Fails completely at single-line sections, 3-track/4-track corridors, or bidirectional bypasses. | Moderate (Only valid for simple double-track lines). |
| **Option 3: Optimization Decision Variable** | Solver treats train track assignment as a choice variable: $x_{train, track} \in \{0, 1\}$. | Maximizes flexibility; allows solver to route trains around maintenance. However, this converts the problem into a full **Train Dispatching and Rescheduling Problem (TDRP)**, massively increasing CP-SAT complexity. | **Prohibited by Product Boundary** (TrackMeld is maintenance scheduling, not train dispatching). |
| **Option 4: Retain Unresolved Traversal Track (Current)** | `traversal_track_id = None`; train pass reserves the entire section. | 100% safe; prevents train collision; reflects actual absence of interlocking data. | **Current Safe Baseline**. |

---

## 7. FULL_TRAFFIC_BLOCK Findings

### 7.1. Current Semantics
In `backend/app/domain/spatial_compatibility.py#L382-L396` and `backend/app/services/validation/checks.py#L464-L483`:
- `FULL_TRAFFIC_BLOCK` is a provisional enum value on `MaintenanceTask.adjacent_track_impact`.
- It indicates that maintenance activity on Track 1 (e.g. Track Renewal Train, deep screening, crane operations) fouls the safety clearance envelope of adjacent Track 2.
- In the Validator: If Task 1 is on Track 1 with `FULL_TRAFFIC_BLOCK`, and Task 2 or Train Pass $P$ overlaps temporally on an adjacent track, the validator raises `ADJACENT_TRACK_FULL_BLOCK` (`ERROR`), blocking plan approval.

### 7.2. Why Adjacency Alone is Insufficient
1. **Longitudinal Chainage Disjointness**: If Task 1 on Track UP is at km 10.0–12.0, and Task 2 on Track DN is at km 25.0–27.0 in a 40 km section, Task 1 does NOT physically foul Task 2. Treating whole-track adjacency as a mutual block across the entire section reintroduces macro-bottlenecks.
2. **OHE (Traction Power) Sectioning**: An electrical power block may isolate OHE across all tracks under a common portal structure, regardless of whether tracks are physically adjacent.
3. **Track Centerline Distance**: On modernized corridors, track centers may exceed 5.3 meters, permitting certain mechanized maintenance without an adjacent line block under railway regulations (subject to specific safety fences).

### 7.3. Can CP-SAT Support This Today?
- To enforce `FULL_TRAFFIC_BLOCK` in CP-SAT, the model builder would need to create a conditional interval variable on adjacent tracks linked to `presence_{task_id}`.
- However, because CP-SAT already enforces whole-section `AddNoOverlap`, **all adjacent track conflicts are already strictly prevented**.
- Introducing track-level `FULL_TRAFFIC_BLOCK` into CP-SAT without full topology would be redundant under the whole-section mutex, and unsafe if the section mutex were prematurely relaxed.

---

## 8. CAUTION_ORDER Findings

### 8.1. Current Semantics
- In Phase 16G-C, `CAUTION_ORDER` generates `ADJACENT_TRACK_CAUTION_REQUIRED` as an **`INFO` finding**.
- It does **not** invalidate a schedule and does **not** block plan approval.
- It acts as an operational advisory for dispatchers indicating that trains running on the adjacent line must be issued speed restriction notices (e.g. 30 km/h caution).

### 8.2. Why a Fixed "+N Minutes" CP-SAT Constraint is Unjustified
A naive proposal might attempt to make `CAUTION_ORDER` an optimization constraint by adding a fixed time buffer (e.g., adding +5 minutes to train traversal intervals when passing an active maintenance site). Forensic review proves this is mathematically and physically uncalibrated:
1. **Absence of Speed Profiles**: TrackMeld has no record of section line speeds, maximum permissible speeds (MPS), or caution speed limits (e.g. 20 km/h vs 30 km/h vs 45 km/h).
2. **Absence of Train Kinematics**: Deceleration and acceleration times depend on train trailing load, locomotive tractive effort, braking percentage, and train length (e.g. a 600m freight train of 4,000 tonnes takes several kilometers to decelerate to 30 km/h and recover line speed, whereas an 8-car Vande Bharat/EMU recovers line speed in seconds).
3. **Absence of Gradient & Curvature**: Longitudinal gradients (e.g. 1 in 100 rising) drastically alter acceleration recovery times.
4. **Arbitrary Dilation Violates Timetable Authority**: TrackMeld does not own train timetables. Expanding a train pass by an arbitrary +5 minutes without validating downstream path conflicts causes synthetic collisions downstream.

**Conclusion**: Until calibrated train performance curves and timetable adjustment protocols exist, `CAUTION_ORDER` **must remain diagnostic-only**.

---

## 9. Minimum Data Required for Track-Aware Optimization

The following dependency matrix establishes the concrete prerequisites before CP-SAT can safely schedule at the track level:

| Data Requirement | Currently Available? | Current Model / Location | Trustworthy for Solver? | Missing Semantics | Blocking Status for Track CP-SAT |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Track Identity** | YES | `TrackModel` (`tracks.track_id`) | YES | None | Non-blocking |
| **Track Direction** | YES | `TrackModel.direction` | YES | None | Non-blocking |
| **Track Adjacency** | PARTIALLY | `TrackModel.adjacent_track_ids` | PROVISIONAL | Manual adjacency lists; no physical spacing | **BLOCKER** |
| **Cross-Section Continuity** | **NO** | None | **NO** | No track-to-track continuity across sections | **CRITICAL BLOCKER** |
| **Station Switch / Interlocking** | **NO** | None | **NO** | No points, turnouts, or route tables | **CRITICAL BLOCKER** |
| **Train Traversal Route** | PARTIALLY | `TrainTraversal` (`traversal.py`) | YES (Section path) | Multi-track route choice is unresolved | **CRITICAL BLOCKER** |
| **Traversal Track Assignment** | **NO** | `TrainTraversal.traversal_track_id=None` | **NO** | Unassigned | **CRITICAL BLOCKER** |
| **Worksite Chainage (`km`)** | YES | `MaintenanceTask.from_km, to_km` | PROVISIONAL | Chainage range exists, but zero stopping buffer model | **BLOCKER** |
| **Lateral Fouling Impact** | YES | `AdjacentTrackImpact` enum | PROVISIONAL | Discrete 3-state enum; no kinematic envelope | **BLOCKER** |
| **OHE Isolation Electrical Zones** | **NO** | `SectionModel.electrified` (Boolean) | **NO** | No electrical neutral sectioning / feeder zones | **BLOCKER** |
| **Speed Restrictions & Braking** | **NO** | None | **NO** | No train physics / kinematic engine | **BLOCKER** |
| **Independent Invariant Proof** | **NO** | None | **NO** | Formal proof of zero collision under track mutex | **CRITICAL BLOCKER** |

---

## 10. Rules / Optimization / Validator Boundary

To preserve railway safety and prevent catastrophic optimization failures, future development must enforce strict domain boundaries:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ STRICT DOMAIN BOUNDARY ENFORCEMENT                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. RULES (Pure Domain Classifiers)                                          │
│    - Classifies spatial compatibility: evaluate_spatial_compatibility()     │
│    - Defines hard physical eligibility (e.g. direction, electrification)   │
│    - Declares fouling and clearance envelopes                               │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. OPTIMIZATION (Mathematical Solver — CP-SAT)                              │
│    - Searches strictly within rule-permitted feasible space                 │
│    - Never creates or overrides physical safety rules                       │
│    - Selects start times and assigned resources                             │
│    - Solves only what rules declare feasible                                │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. INDEPENDENT VALIDATOR (Post-Solve Verification)                          │
│    - Re-evaluates schedule from first principles without solver state       │
│    - Does NOT import solver or trust solver status                          │
│    - Catches any mathematical leakage or constraint bugs                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. HUMAN AUTHORITY (Planning & Dispatch Controllers)                        │
│    - Final approval authority (is_approvable is advisory gate)              │
│    - Operational safety overrides                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Prohibited Architectural Anti-Patterns:
1. **Solver Inventing Safety Semantics**: CP-SAT must never implement heuristic compatibility logic that does not exist in the domain rule layer.
2. **Validator Trusting Solver Feasibility**: The validator must never inspect `solver_status == OPTIMAL` as evidence that section or track constraints are satisfied.
3. **Objective Function Trading Safety for Throughput**: Safety constraints must be strictly hard (`AddNoOverlap`, `Add`). They must never be soft penalty terms in the objective function.
4. **Track Compatibility Existing Only in Solver**: If a spatial combination is permitted by the solver but rejected by domain rules or the validator, the schedule will fail at the approval gate.
5. **Autonomous Dispatching / Rescheduling**: Optimization outputs are maintenance plan proposals, never direct commands to signalling systems.

---

## 11. Historical Replay and Hash Implications

### 11.1. Current Snapshot Fingerprint Gap
Inspection of `compute_snapshot_hash()` in `backend/app/domain/planning_snapshot.py#L45-L67` reveals a critical forensic fact:
```python
task_records = []
for t in self.tasks:
    task_records.append((t_id, w_start, w_end, dur, sec))
...
hasher.update(str(len(self.train_passes)).encode("utf-8"))
hasher.update(str(len(self.resources)).encode("utf-8"))
hasher.update(str(len(self.dependencies)).encode("utf-8"))
```
**Fields NOT included in `compute_snapshot_hash()`**:
- `task.track_id` is NOT hashed.
- `task.from_km` and `task.to_km` are NOT hashed.
- `task.adjacent_track_impact` is NOT hashed.
- `task.direction` is NOT hashed.
- `snapshot.tracks` list and track definitions are NOT hashed.
- `snapshot.train_traversals` are NOT hashed.

### 11.2. Schedule Identity Fingerprint Gap
Inspection of `compute_schedule_identity()` in `backend/app/services/validation/validator.py#L31-L67`:
- Hashed: `task_id`, `start`, `end`, `pos_start`, `pos_end`, `sections`, `resources`, `unscheduled_tasks`, `snapshot_id`, `scheduler_type`, `solver_status`.
- Explicitly documented:
  ```python
  # crew_id, assigned_track — these fields do not exist on the
  # ScheduledTaskResult domain model; if added in future, include
  # them here with a VERIFIED_SOURCE provenance record.
  ```

### 11.3. Replay & Governance Impact
If future track-aware optimization is introduced without updating the hashing contracts:
1. Two different scenarios with different track assignments or adjacent track impacts would produce the **identical snapshot hash**.
2. A plan scheduled on Track UP and an identical plan scheduled on Track DOWN would produce the **identical schedule identity hash**.
3. Persisted `PlanningRun` and `PlanVersion` audit trails would lose cryptographic reproducibility.
4. **Contract Requirement**: Before track-aware optimization is activated, snapshot hashing and schedule identity hashing must be versioned and extended to cover track identities and lateral impact attributes.

---

## 12. Dependency Graph for Future Phases

The path toward safe track-aware optimization requires sequential, staged phases where each phase establishes the proof and data required by the next:

```
Phase 16H: Track-Aware Optimization Discovery (Current)
    ↓
Phase 16I: Infrastructure Topology & Track Adjacency Foundation
    • Station switch/turnout connectivity
    • Cross-section track continuity graph
    • Verified track spacing and fouling point data
    ↓
Phase 16J: Deterministic Train Route & Traversal Track Assignment
    • Resolution of TrainTraversal.traversal_track_id
    • Platform line mapping and express route designation
    • Multi-track direction and headway rules
    ↓
Phase 16K: Independent Validator Track-Aware Hard Safety Invariants
    • Promotion of track spatial rules to authoritative validators
    • Mathematical proof of zero cross-track collision
    • Dual-layer validation (Section Mutex + Track Mutex)
    ↓
Phase 16L: CP-SAT Track-Aware Optimization Modeling
    • Hierarchical resource formulation (Model C)
    • Conditional adjacent track possession intervals
    • Benchmark against whole-section safety baseline
```

### Rationale for Sequencing:
1. **16I must precede 16J**: Train traversals cannot be assigned to physical tracks without cross-section track continuity and station junction topology.
2. **16J must precede 16K**: The validator cannot verify track-level safety invariants while train traversals have unassigned tracks (`traversal_track_id=None`).
3. **16K must precede 16L**: The Independent Validator must have full, proven track-aware verification capabilities **before** the solver is allowed to relax whole-section mutex constraints.

---

## 13. Explicit Non-Goals

To maintain software integrity and safety compliance, TrackMeld explicitly declares the following as **NON-GOALS**:
1. **Autonomous Train Dispatching**: TrackMeld does not route, reroute, or clear real-time train movements.
2. **Live Signalling / Interlocking Control**: TrackMeld never sends commands to Computer Based Interlocking (CBI) or Relay Interlocking systems.
3. **Emergency Train Control**: TrackMeld does not replace automatic train protection (ATP / Kavach / ETCS).
4. **Arbitrary Heuristic Solver Loosening**: TrackMeld will not relax whole-section mutex in CP-SAT merely to artificially boost scheduled task throughput.
5. **Real-Time Moving Possessions**: TrackMeld schedules fixed, bounded possession intervals; it does not model moving work trains in live traffic.

---

## 14. Open Questions & Evidence Gaps

The following architectural and domain questions cannot be resolved from existing repository data and are formally classified as `UNRESOLVED / REQUIRES DOMAIN EVIDENCE`:

1. `[UNRESOLVED / REQUIRES DOMAIN EVIDENCE]`: What is the authoritative minimum track centerline separation distance (in meters) under Indian Railways (IR) Schedule of Dimensions (SOD) that permits simultaneous maintenance on Track 1 and line-speed traffic on Track 2?
2. `[UNRESOLVED / REQUIRES DOMAIN EVIDENCE]`: Which specific maintenance machine types (e.g. BCM, CSM, TRT, DGS) require a `FULL_TRAFFIC_BLOCK` on the adjacent line versus a `CAUTION_ORDER` versus no restriction under IR General & Subsidiary Rules (G&SR)?
3. `[UNRESOLVED / REQUIRES DOMAIN EVIDENCE]`: What are the calibrated train deceleration/acceleration time losses for different train classes (Rajdhani, Freight, EMU) under a 30 km/h caution order?
4. `[UNRESOLVED / REQUIRES DOMAIN EVIDENCE]`: How should common-portal 25kV AC traction overhead equipment (OHE) electrical isolation boundaries be mapped to individual track possessions?
5. `[UNRESOLVED / REQUIRES DOMAIN EVIDENCE]`: What station platform track assignment data source exists for non-stopping express trains passing intermediate stations?

---

## 15. Conclusion

Based on forensic analysis of the TrackMeld codebase across domain models, database schemas, solver constraint builders, independent validation checks, and cryptographic hashing:

1. **Track-aware CP-SAT optimization is NOT ready to be implemented.**
2. **Different track IDs do NOT imply safe coexistence.** Current infrastructure data lacks cross-section track continuity, switch topology, and calibrated lateral clearance envelopes.
3. **The current whole-section safety baseline is intentional, mathematically sound, and must remain active.**
4. **Progress toward track-aware optimization must be incremental, data-driven, and strictly staged** through infrastructure topology (Phase 16I), train route assignment (Phase 16J), and validator invariant proofs (Phase 16K) before any CP-SAT solver constraints are altered.
