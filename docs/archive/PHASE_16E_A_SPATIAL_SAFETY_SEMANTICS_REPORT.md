# Phase 16E-A: Spatial Safety Semantics Foundation Report

## 1. Baseline Commit
- **Baseline Commit:** `0a7660b` (`feat(phase-16c): add train movement track semantics`)
- **Repository:** `D:\Trackmeld`
- **Execution Phase:** Phase 16E-A (Spatial Safety Semantics Foundation)

---

## 2. Exact Files Changed / Created

### Created Files
1. `backend/alembic/versions/e9f3b2a1c0d4_008_adjacent_track_impact.py` (Alembic migration adding `adjacent_track_impact` to `maintenance_tasks`)
2. `tests/unit/test_phase16e_a_spatial_safety.py` (Unit tests for enum, invariants, chainage, snapshot propagation, and solver regression)
3. `tests/integration/test_phase16e_a_spatial_safety_api.py` (API integration tests for task read endpoints and scenario bundle)
4. `docs/PHASE_16E_A_SPATIAL_SAFETY_SEMANTICS_REPORT.md` (This document)

### Modified Files
1. `backend/app/db/models/task.py` (Added `adjacent_track_impact: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)`)
2. `backend/app/domain/enums.py` (Added `AdjacentTrackImpact` enum with `NONE`, `CAUTION_ORDER`, `FULL_TRAFFIC_BLOCK`)
3. `backend/app/domain/__init__.py` (Exported `AdjacentTrackImpact`)
4. `backend/app/domain/maintenance_tasks.py` (Added `adjacent_track_impact: Optional[AdjacentTrackImpact] = None` and spatial validation invariants)
5. `backend/app/schemas/operational_responses.py` (Added `adjacent_track_impact: Optional[str] = None` to `MaintenanceTaskResponse`)
6. `backend/app/services/planning_service.py` (Propagated `"adjacent_track_impact": t.adjacent_track_impact` in `ScenarioPlanningBundle`)
7. `scripts/ingest_operational_data.py` (Ingested `adjacent_track_impact` into `MaintenanceTaskModel` values and conflict updates)
8. `data/synthetic/operational_scenario_SCN-DEMO-001.json` (Assigned provisional adjacent-track impact for representative tasks `TSK-0001` and `TSK-0002`)
9. `frontend/src/types/railway.ts` (Added `adjacent_track_impact?: 'NONE' | 'CAUTION_ORDER' | 'FULL_TRAFFIC_BLOCK'` to `MaintenanceTask`)
10. `frontend/src/components/planning/TaskInspector.tsx` (Rendered truthful `Adjacent-Track Impact` metadata in Task inspector)
11. `frontend/src/components/planning/EntityInspector.tsx` (Rendered truthful `Adjacent Track` metadata in Entity inspector)

---

## 3. Database Migration
- **Migration File:** `backend/alembic/versions/e9f3b2a1c0d4_008_adjacent_track_impact.py`
- **Revises:** `d8a2b3c4e5f6`
- **Operations:**
  - Adds nullable column `adjacent_track_impact VARCHAR(32)` to table `maintenance_tasks`.
  - Seeds representative data:
    - `TSK-0001` (track tamping on `TRK-ETW-CNB-UP`) $\rightarrow$ `'CAUTION_ORDER'`
    - `TSK-0002` (deep screening on `TRK-ARA-PNBE-DN`) $\rightarrow$ `'FULL_TRAFFIC_BLOCK'`
  - Downgrade drops `adjacent_track_impact` cleanly.
- **Verification:** Verified bidirectional migration (`alembic upgrade head` $\rightarrow$ `alembic downgrade -1` $\rightarrow$ `alembic upgrade head`).

---

## 4. Domain Semantics
The provisional `AdjacentTrackImpact` enum represents the operational clearance impact on adjacent running line(s) during a track possession:

```python
class AdjacentTrackImpact(str, Enum):
    """Provisional classification of maintenance impact on adjacent running line(s)."""
    NONE = "NONE"
    CAUTION_ORDER = "CAUTION_ORDER"
    FULL_TRAFFIC_BLOCK = "FULL_TRAFFIC_BLOCK"
```

- **`NONE`**: The maintenance work is physically confined within the primary track's structural clearance envelope (e.g. manual track inspections, in-track tightening, rail lubricator servicing with dedicated lookout protection). Traffic on the adjacent line may operate at normal maximum permissible speed.
- **`CAUTION_ORDER`**: The maintenance work involves equipment or personnel working near the clearance line (e.g. routine track tamping, shoulder ballast cleaning), requiring a Temporary Speed Restriction (TSR / Caution Order e.g. 30–50 km/h or whistle board instructions) on the adjacent running line.
- **`FULL_TRAFFIC_BLOCK`**: The maintenance work physically infringes or endangers the adjacent track clearance (e.g. ballast cleaning machine cross-discharging spoil, crane slewing, turnout renewal, heavy bridge girder replacement), necessitating a full traffic block on the adjacent line.

> [!IMPORTANT]
> **Domain Model Status:**  
> The `AdjacentTrackImpact` enum is a **provisional TrackMeld domain abstraction** for spatial planning support, **not an official or comprehensive railway safety standard**. Real-world railway engineering (e.g. Indian Railways Permanent Way Manual / IRPWM, General & Subsidiary Rules) relies on multi-factor physical clearance calculations, slew gauges, speed tables, and station interlocking rules. TrackMeld does not claim complete safety-rule coverage.

---

## 5. NULL vs Default Decision
- **Choice Made:** `NULL` (nullable column, optional domain field `Optional[AdjacentTrackImpact] = None`).
- **Rationale:**
  1. **Whole-Section Tasks:** For a task with `track_id = None`, the task already claims and blocks the entire section. There is no distinct "adjacent track", so `adjacent_track_impact` is semantically `None`.
  2. **Backward Compatibility:** All existing historical tasks without assessed adjacent-track impact naturally evaluate to `None` without requiring synthetic data fabrication or breaking existing database constraints.
  3. **Preservation of Safety Baseline:** In TrackMeld's current scheduling engine, any task with `track_id = None` or unspecified adjacent impact falls back to whole-section mutual exclusivity.

---

## 6. Chainage Validation Decision
- **Enforced Invariants:**
  1. `track_id == None => from_km is None and to_km is None and adjacent_track_impact is None`.
  2. `0 <= from_km <= to_km` when chainage is populated.
  3. Negative chainage or `from_km > to_km` raises `ValidationError`.
- **Corridor Kilometrage vs Task Chainage Incompatibility (Documented Limitation):**
  - Section kilometrage (`SectionModel.kilometrage_start` and `kilometrage_end`) represents **cumulative corridor route distance** from the origin terminus (e.g., `SEC-ARA-PNBE` has `kilometrage_start = 943.0 km`, `kilometrage_end = 992.0 km`).
  - Task chainage (`MaintenanceTask.from_km` and `to_km`) represents **section-relative worksite linear offset** (e.g., `TSK-0002` on `SEC-ARA-PNBE` has `from_km = 12.4 km`, `to_km = 15.8 km`, within the 49.0 km section).
  - Attempting to enforce `from_km >= section.kilometrage_start` would be a **false invariant** that incorrectly confuses corridor chainage with section-relative worksite bounds.
  - Therefore, corridor-level chainage clamping is explicitly NOT enforced in Phase 16E-A.

---

## 7. Planning Snapshot & Hash Decision
- `adjacent_track_impact` is propagated into `ScenarioPlanningBundle` (`bundle.tasks`) and `PlanningSnapshot` (`snapshot.tasks` and `snapshot.tasks_map`).
- **Hash Decision:** `compute_snapshot_hash()` was **deliberately NOT modified**.
- **Rationale:** Modifying `compute_snapshot_hash()` would invalidate all historical scenario fingerprints and break determinism across existing baseline runs. Introducing hash updates is reserved for a future versioned hashing phase (`v1` whole-section vs `v2` track-aware).

---

## 8. Solver & Validator Boundary Confirmation
- **CP-SAT Constraints:** **Zero changes.** Whole-section mutual exclusivity via `AddNoOverlap` remains 100% active.
- **Independent Schedule Validator:** **Zero changes.** Recomputes whole-section conflicts and train clearance identically.
- **Governance State Machine:** **Zero changes.** Four-eyes review, human approval gates, and run lifecycle invariants remain completely untouched.

---

## 9. Synthetic Data Changes
- In `data/synthetic/operational_scenario_SCN-DEMO-001.json`:
  - `TSK-0001`: Added `"adjacent_track_impact": "CAUTION_ORDER"`.
  - `TSK-0002`: Added `"adjacent_track_impact": "FULL_TRAFFIC_BLOCK"`.
  - Remaining 28 tasks: `"adjacent_track_impact": null`.

---

## 10. Tests and Results
- `tests/unit/test_phase16e_a_spatial_safety.py`: 5 passed.
- `tests/integration/test_phase16e_a_spatial_safety_api.py`: 5 passed.
- **Full Comprehensive Regression Suite:** **59 passed in 8.30s**:
  - Phase 16A tracks unit tests (5 passed)
  - Phase 16B task spatial unit tests (11 passed)
  - Phase 16C train spatial unit tests (6 passed)
  - Phase 16E-A spatial safety unit tests (5 passed)
  - Phase 16B task spatial API integration tests (4 passed)
  - Phase 16C train spatial API integration tests (5 passed)
  - Phase 16E-A spatial safety API integration tests (5 passed)
  - Phase 15B hash integrity tests (5 passed)
  - Phase 6 CP-SAT solver execution tests (4 passed)
  - Phase 8 planning jobs worker E2E tests (8 passed)
  - Phase 15B end-to-end lifecycle governance tests (1 passed)
- **Frontend Checks:**
  - `npx tsc --noEmit`: 0 errors.
  - `npm run lint`: 0 errors.
  - `npm run build`: Production build succeeded; all routes pre-rendered.

---

## 11. Known Limitations
- Adjacent-track impact is metadata only; it does not yet trigger automatic caution order timetable simulation or train headway adjustments.
- Express train timetable hops spanning multiple physical block sections remain as `STATION_HOP` passes awaiting contiguous route expansion.

---

## 12. Explicit Operational Notice

> [!CAUTION]
> **Track-aware CP-SAT scheduling is NOT implemented in Phase 16E-A.**  
> The CP-SAT solver and Independent Schedule Validator strictly continue to treat each section as an indivisible whole-section spatial conflict resource. The `AdjacentTrackImpact` enum introduced in this phase provides the foundational domain data required for future multi-track scheduling models, but does NOT relax physical collision or possession exclusivity in the current solver.
