# TrackMeld Phase 11 — Planning Workspace & Live Backend Integration Report

## 1. Phase & Status
- **Phase:** Phase 11 — Planning Workspace + Real Backend Integration + Deep Diagnostics
- **Status:** Complete & Verified
- **Target Context:** Smart India Hackathon 2026 / Ministry of Railways / CRIS

---

## 2. Core Architecture Principle Maintained
```text
Rules classify
      ↓
Optimization schedules
      ↓
Independent Validator verifies
      ↓
Diagnostics explain
      ↓
Human reviews
      ↓
Human approves

COMPLETED ≠ APPROVED
```
The optimizer is strictly segregated from self-certification: the independent validator (`/api/v1/planning/validate`) audits every schedule independently across 12 hard constraint checks. The AI and diagnostics explain causal root causes and relaxation alternatives, while human railway operations officers retain exclusive authority to approve or reject plan versions.

---

## 3. What Changed & Implemented

### A. Real FastAPI Backend Integration
- Connected the frontend directly to live FastAPI services running on `http://127.0.0.1:8000/api/v1` with Bearer authentication (`admin-token-2026`).
- Integrated live operational endpoints:
  - `GET /api/v1/scenarios/SCN-DEMO-001/bundle` (30 maintenance tasks, 50 train movements, 32 block sections)
  - `POST /api/v1/planning/optimize` (CP-SAT bounded mathematical optimization)
  - `POST /api/v1/planning/validate` (Independent feasibility certification)
  - `POST /api/v1/planning/diagnostics` (Causal root-cause and relaxation analysis)
  - `POST /api/v1/planning/benchmark` (Side-by-side comparative metrics across FCFS, Priority-Greedy, and CP-SAT)
  - `GET /api/v1/plan-versions` & `POST /api/v1/plan-versions/{id}/approve` / `/reject`
  - `GET /api/v1/plan-versions/{id}/audit` (Cryptographic immutable audit trail)
- Maintained client-side synthetic fallback datasets strictly as an offline safety measure.

### B. 4-Quadrant Operational Layout (`/planning`)
Constructed an integrated 4-quadrant layout for railway planning operations:
1. **Top-Left (Quadrant 1): Task Queue Table**
   - Search filter (search by code, title, section, department).
   - Filter tabs: `All (30)`, `Scheduled (29)`, `Unscheduled (1)`, `Mandatory (17)`.
   - Displays task ID, title, department, section code, required duration, and status badge.
   - Synchronized selection across the workspace.
2. **Top-Right (Quadrant 2): 2D Time-Space Diagram**
   - Renders 50 real corridor train movements (distance vs time trajectories) across stations: NDLS (0km), GZB (26km), ALJN (131km), TDL (209km), ETW (301km), CNB (440km).
   - Renders scheduled maintenance possession windows (blue hatched blocks), shadow bundled possessions (green hatched blocks), and unplaced task windows (red dashed hatched blocks).
   - Interactive zoom controls (100% to 250%) and multi-day filtering (72h full horizon vs single days).
3. **Bottom-Left (Quadrant 3): 3D Railway Corridor View**
   - Interactive 3D corridor visualization with progressive 2D schematic fallback.
   - Spatial block section markers, rail tracks, rakes, and possession blocks.
   - Bi-directional selection with the task queue and inspector.
4. **Bottom-Right (Quadrant 4): Task Inspector & Deep Causal Diagnostics**
   - For scheduled tasks: shows assigned work interval, possession interval with safety buffers, assigned track and resources (`RES-TM-CSM-01`, `RES-CREW-ENG-G01`), and priority breakdown.
   - For unscheduled tasks (e.g. `TSK-0007`): visualizes the step-by-step causal decision pipeline:
     `Candidate Generated → Allowed Window Evaluated → Section Track Contention Checked → Resource & Precedence Competition → Rejection Decision`.
   - Renders real backend relaxation analyses (`IGNORE_RESOURCE_AVAILABILITY`, `IGNORE_DEPENDENCIES`, `WIDEN_TASK_WINDOW` by +/- 4h to 09:00–11:00 UTC) with clear "Hypothetical Decision-Support Only — Not Auto-Applied" notice.

### C. Factual Comparative Strategy Benchmark Modal
- Created `BenchmarkComparisonModal.tsx` connected to `POST /api/v1/planning/benchmark`.
- Displays 13 empirical evaluation metrics side-by-side across FCFS, Priority-Greedy, and CP-SAT.
- Strictly adheres to the rule: zero biased labels like "WINNER" or "BEST". Purely factual metrics (latency, work minutes, track possession minutes, priority points captured, completion rates).

### D. Governance, Approval, and Immutable Audit Trail
- Connected `PlanApprovalModal.tsx` to `POST /api/v1/plan-versions/{id}/approve` and `/reject`.
- Prominently displays the SHA-256 schedule fingerprint (`bae346ecf37b1fd8...`) and independent validator status.
- Enforces reviewer name, official designation, and operational justification.
- Integrated `/audit` page to fetch live audit events from `GET /api/v1/plan-versions/{id}/audit`, showing cryptographic hash, actor username, event types, and state transitions.

---

## 4. Files Created / Modified

| File | Action | Purpose |
| :--- | :--- | :--- |
| `frontend/src/types/railway.ts` | Modified | Updated domain types to match backend bundle schemas (sections, train movements, tasks). |
| `frontend/src/types/planning.ts` | Modified | Updated types for `ScheduleResult`, `ScheduleValidationResult`, `DiagnosticsReport`, `BenchmarkComparisonResult`, `PlanVersion`, `AuditLogEntry`. |
| `frontend/src/lib/api/client.ts` | Modified | Implemented typed API client with Bearer auth (`admin-token-2026`), live backend methods, and robust fallbacks. |
| `frontend/src/components/planning/BenchmarkComparisonModal.tsx` | Created | Neutral, factual comparative benchmark modal for FCFS vs Priority-Greedy vs CP-SAT. |
| `frontend/src/components/planning/TaskQueueTable.tsx` | Modified | Added search bar, filter tabs (`All`, `Scheduled`, `Unscheduled`, `Mandatory`), and sticky table layout. |
| `frontend/src/components/planning/TimeSpaceChart.tsx` | Modified | Added multi-day horizon support, UTC time-to-distance mapping, stations Y-axis, and interactive tooltips. |
| `frontend/src/components/planning/TaskInspector.tsx` | Modified | Implemented 6-step causal decision pipeline, relaxation analyses, and priority score breakdown. |
| `frontend/src/components/governance/PlanApprovalModal.tsx` | Modified | Displayed SHA-256 fingerprint, operational boundary disclaimers, and wired up approve/reject payloads. |
| `frontend/src/app/(workspace)/planning/page.tsx` | Modified | Assembled 4-quadrant operational layout with optimize pipeline, benchmark trigger, and governance modal. |
| `frontend/src/app/(workspace)/overview/page.tsx` | Modified | Connected live bundle statistics and planning runs to overview dashboard. |
| `frontend/src/app/(workspace)/audit/page.tsx` | Modified | Connected live PostgreSQL audit ledger with cryptographic hashes and human sign-off history. |

---

## 5. Verification & Test Evidence

### A. Frontend Linting (`npm run lint`)
- **Command:** `npm run lint` in `d:\Trackmeld\frontend`
- **Result:** Exited with code `0`. 0 errors, 0 warnings.

### B. Frontend Production Build (`npm run build`)
- **Command:** `npm run build` in `d:\Trackmeld\frontend`
- **Result:** Exited with code `0`.
- **Output:**
  ```text
  ▲ Next.js 16.3.8 (Turbopack)
  ✓ Compiled successfully in 3.8s
  ✓ Finished TypeScript in 10.0s
  ✓ Generating static pages using 7 workers (7/7) in 1009ms
  Route (app)
  ┌ ○ /
  ├ ○ /_not-found
  ├ ○ /audit
  ├ ○ /overview
  └ ○ /planning
  ```

### C. Backend Test Suite (`pytest`)
- **Command:** `python -m pytest tests/unit tests/integration -q`
- **Result:** Exited with code `0`.
- **Outcome:** **190 tests passed** (125 unit tests + 65 integration tests), 0 failures.

### D. Live Endpoint Verifications
- Verified `GET /api/v1/scenarios/SCN-DEMO-001/bundle` returns 30 tasks, 50 trains, 32 sections.
- Verified `POST /api/v1/planning/optimize` returns 29 scheduled tasks, 1 unplaced task in 1.48s.
- Verified `POST /api/v1/planning/validate` certifies 12 hard checks and returns `status: VALID`, `is_approvable: True`.
- Verified `POST /api/v1/planning/diagnostics` returns causal relaxation findings for `TSK-0007`.
- Verified `POST /api/v1/planning/benchmark` returns comparative metrics across FCFS, Priority-Greedy, and CP-SAT.
- Verified `GET /api/v1/plan-versions/PV-20261002-5F8A180A/audit` returns chronological cryptographic audit entries.

---

## 6. Known Limitations
1. **Corridor Topologies:** The demonstration corridor covers Northern Trunk Corridor (NDLS to CNB, 440 km); additional Indian Railway corridors (e.g. Western Corridor, Southern Railway) are seeded in the database but currently defaulted to SCN-DEMO-001 in the primary workspace.
2. **WebGL Fallback:** In low-power environments where WebGL is unavailable or GPU drivers are software-emulated, the 3D railway corridor seamlessly falls back to the 2D schematic canvas as designed.
3. **Synthetic Data Disclaimer:** The scenario is synthetic prototype data generated for Smart India Hackathon demonstration purposes. Operational deployment requires integration with CRIS COA / FOIS systems.

---

## 7. Security & Domain Boundaries
- Authentication is enforced across backend routes using Bearer token authentication (`admin-token-2026` / `approver-token-2026`).
- No private chain-of-thought or raw unredacted prompts are stored or exposed.
- All relaxation analyses are explicitly flagged as hypothetical decision-support aids; they are never auto-committed.
- The rule `COMPLETED ≠ APPROVED` remains strictly enforced: solver completion and validator checks produce candidates; human operations officers must formally approve a plan version.
