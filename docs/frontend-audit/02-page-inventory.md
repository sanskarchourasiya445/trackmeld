# Report B — Complete Page & Route Inventory

**Document ID:** `TM-FRONTEND-AUDIT-02`  
**Target:** TrackMeld Railway Maintenance Planning & Digital Twin Platform  
**Inspection Date:** October 14, 2026  
**Auditor:** Principal Frontend Systems Architect & Railway Simulation Engineer  
**Scope:** Comprehensive page-by-page inventory of all 8 registered routes, interactive controls, data contracts, dependencies, and preservation requirements.

---

## 1. Master Route Summary Table

| Route Path | Page Name | Primary Component & Source File | Shell / Layout | Primary Data Sources | Primary Actions / Interactive Controls | Apparent Completeness |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `/` | Canonical Homepage | `HomePage`<br>[`src/app/page.tsx`](file:///d:/Trackmeld/frontend/src/app/page.tsx) | `LandingNavbar` + Custom Layout | Static showcase content, 3D WebGL procedural simulation | Camera controls (Cinematic, Cab, Drone, Orbit), Speed slider, Atmosphere toggle, Demo modal trigger | **Implemented** |
| `/overview` | Operational Situation Briefing | `OverviewPage`<br>[`src/app/(workspace)/overview/page.tsx`](file:///d:/Trackmeld/frontend/src/app/(workspace)/overview/page.tsx) | `<AppShell>` | `DEMO_SCENARIO`, `DEMO_CORRIDOR`, `DEMO_PLAN_VERSION`, `SAMPLE_CONFLICT` | Interactive MapLibre corridor map, 3D Twin modal trigger, Conflict drawer, Fullscreen toggle, Approval modal trigger | **Implemented** |
| `/planning` | Planning & CP-SAT Workspace | `PlanningPageContent`<br>[`src/app/(workspace)/planning/page.tsx`](file:///d:/Trackmeld/frontend/src/app/(workspace)/planning/page.tsx) | `<AppShell>` | `getScenarioBundle()`, `optimizeSchedule()`, `validateSchedule()`, `diagnoseSchedule()`, `getPlanVersions()` | 9 workspace subtab views (Integrated 3-panel, Map, Time-Space, Timeline, Tasks, Conflicts, Validation, Diagnostics, Copilot), Run CP-SAT solver, Plan sign-off, Compare plans modal, Entity inspector | **Implemented** |
| `/work-orders` | Maintenance Work Orders | `WorkOrdersPage`<br>[`src/app/(workspace)/work-orders/page.tsx`](file:///d:/Trackmeld/frontend/src/app/(workspace)/work-orders/page.tsx) | `<AppShell>` | `EXTENDED_WORK_ORDERS` (local seeded array based on `DEMO_TASKS`) | Text search, Department filter, Status filter, Row inspection drawer, 3D Twin modal trigger | **Partially Implemented** *(Ignores `?tab=resources`)* |
| `/network` | Rail Network & Infrastructure | `NetworkPageContent`<br>[`src/app/(workspace)/network/page.tsx`](file:///d:/Trackmeld/frontend/src/app/(workspace)/network/page.tsx) | `<AppShell>` | `corridorGisData.ts` (GIS fixtures), `DEMO_CORRIDOR` | 6 subtabs (`MAP`, `STATIONS`, `TRACKS`, `SIGNALS`, `OHE`, `FLEET`), GIS layer toggles, Text search, Entity inspector drawer, 3D Twin modal trigger | **Implemented** |
| `/governance` | Safety Firewall & Four-Eyes | `GovernancePage`<br>[`src/app/(workspace)/governance/page.tsx`](file:///d:/Trackmeld/frontend/src/app/(workspace)/governance/page.tsx) | `<AppShell>` | `VALIDATION_CHECKS` (13 rules), `DEMO_PLAN_VERSION`, `DEMO_AUDIT_LOGS` | 13 hard safety rule cards with evidence refs, Four-Eyes DRM approval modal trigger, SHA-256 hash display | **Implemented** |
| `/copilot` | AI Decision Support Copilot | `CopilotPage`<br>[`src/app/(workspace)/copilot/page.tsx`](file:///d:/Trackmeld/frontend/src/app/(workspace)/copilot/page.tsx) | `<AppShell>` | `/copilot/explain` (`askCopilot()`) via FastAPI backend | Freeform question prompt input, Causal explanation chat stream, Evidence citations drawer, Pre-canned inquiry suggestions | **Implemented** |
| `/audit` | Compliance & Plan Ledger | `AuditPage`<br>[`src/app/(workspace)/audit/page.tsx`](file:///d:/Trackmeld/frontend/src/app/(workspace)/audit/page.tsx) | `<AppShell>` | `getPlanVersions()`, `getPlanVersionAudit()`, `approvePlanVersion()`, `rejectPlanVersion()` | Plan version history selector, Cryptographic SHA-256 hash inspection, Formal approval/rejection modal, Audit event log table, Multi-disciplinary engineering review comments thread | **Implemented** |

---

## 2. Detailed Page-by-Page Inventory

### 2.1 Route: `/` — Canonical Product Homepage

* **Source File:** [`frontend/src/app/page.tsx`](file:///d:/Trackmeld/frontend/src/app/page.tsx)
* **Component Name:** `HomePage`
* **Purpose:** Public landing page demonstrating TrackMeld's railway digital twin capabilities, CP-SAT mathematical optimization solver, 13-category safety validation firewall, explainable AI copilot, and end-to-end railway governance.

#### Visual Layout & Main Sections
1. **Fixed Navigation Bar (`LandingNavbar.tsx`):** TrackMeld emblem, platform links (Overview, Topology, Constraints, CP-SAT Engine, Validation, Copilot, Architecture), and "Launch Workspace" CTA linking to `/overview`.
2. **Hero Viewport (`LandingHero3D.tsx`):**
   - Full-bleed Three.js WebGL canvas running `RailwayScene.tsx` with high-resolution Vande Bharat trainset moving continuously down broad-gauge UIC-60 track.
   - Glassmorphic telemetry HUD overlay (`DigitalTwinHUD.tsx`) showing velocity, block section (`SEC-03`), catenary status (`25.4 kV AC`), and safety clearance.
   - Interactive camera control pills: `Cinematic` (3/4 trackside telephoto), `Cab` (driver cockpit), `Drone` (overhead multi-track survey), `Orbit` (interactive 360° rotation/zoom).
   - Atmospheric lighting presets: `Dawn`, `Night` (illuminated projector headlamps), `Overcast`.
   - Continuous velocity slider ($0\text{--}180\text{ km/h}$) and simulation pause/play toggle.
3. **Section 2 — Meso-Topology (`SectionDigitalTwin.tsx`):** 440 km corridor diagram with station chainages and interlocking nodes.
4. **Section 3 — Hard Safety Constraints (`SectionConstraints.tsx`):** Interactive conflict matrix displaying headway, electrical clearance, and track occupancy rules.
5. **Section 4 — Mathematical Optimization Engine (`SectionOptimization.tsx`):** CP-SAT discrete interval formulation, objective function weights, and solve performance benchmark.
6. **Section 5 — Independent Safety Firewall (`SectionValidation.tsx`):** 13 statutory rule categories audited by independent validator.
7. **Section 6 — Grounded Read-Only AI Copilot (`SectionCopilot.tsx`):** Interactive terminal showcasing causal explanations with exact rule and timetable citations.
8. **Section 7 — Three-Way Plan Comparison (`SectionPlanComparison.tsx`):** Comparison matrix contrasting Manual Planning, Priority-Greedy Dispatch, and TrackMeld CP-SAT Optimization.
9. **Section 8 — Governance Architecture (`SectionArchitecture.tsx`):** Inviolable end-to-end railway safety architecture.
10. **Section 9 — Footer CTA (`SectionFooterCTA.tsx`):** Platform links and "Launch Workspace" actions.
11. **Modal Overlay (`DemoRequestModal.tsx`):** Dialog for enterprise credential issuance and technical dossier downloads.

#### Interactive Controls & Event Handlers
- **Camera Mode Buttons:** Updates `cameraMode` state (`cinematic`, `cab`, `drone`, `orbit`).
- **Atmosphere Buttons:** Updates `lighting` state (`dawn`, `night`, `overcast`).
- **Speed Slider:** Adjusts simulation train velocity via `SimulationContext`.
- **"Launch Workspace" Buttons:** Navigates via Next.js `Link` to `/overview`.
- **"Request Architecture Dossier" Buttons:** Toggles `isDemoModalOpen` modal dialog.

#### Data Sources & Dependencies
- **Data Source:** Static presentation content, procedural 3D WebGL scene, local React state. No external API calls on this page.
- **Dependencies:** `@react-three/fiber`, `@react-three/drei`, `three`, `lucide-react`.

#### Usability & Preservation Requirements
- **Preservation:** The 3D scene engine (`LandingHero3D`, `RailwayScene`, `VandeBharatTrainModel`, `CameraRig`) is shared with the operational `DigitalTwinInspectionModal` and must not be altered or broken.

---

### 2.2 Route: `/overview` — Operational Situation Briefing

* **Source File:** [`frontend/src/app/(workspace)/overview/page.tsx`](file:///d:/Trackmeld/frontend/src/app/(workspace)/overview/page.tsx)
* **Component Name:** `OverviewPage`
* **Purpose:** Executive operations dashboard answering the 4 critical railway operational questions: What is happening? What needs attention? Is the plan safe? What requires my decision?

#### Visual Layout & Main Sections
1. **Briefing Header:** Active scenario (`SCN-DEMO-001`), corridor chainage (`NDLS → CNB`, 440 km), planning clock (`18 Oct 2026, 06:00 UTC`), and "Enter Planning Workspace" button.
2. **The 4 Situational Questions Cards:**
   - **Card 1 ("What is happening?"):** 8 active possessions, 12 work zones, 29 scheduled maintenance tasks across 440 km.
   - **Card 2 ("What needs attention?"):** Highlights 1 critical conflict (`CONF-HDW-01`, headway buffer compression between Express 12004 and Freight 401 at SEC-12). Clicking card opens contextual `ResponsiveDrawer`.
   - **Card 3 ("Is the plan safe?"):** 100% certified badge (13/13 hard rules passed). Clicking card navigates to `/governance`.
   - **Card 4 ("Decision required"):** Four-Eyes review pending on `PlanVersion 1`. Clicking card opens `PlanApprovalModal`.
3. **Live Corridor GIS Map Viewport (`MapLibreRailwayMap.tsx`):**
   - Interactive MapLibre GL map showing stations, block sections, and active train coordinates.
   - Controls: "3D Twin View" button (opens `DigitalTwinInspectionModal`), "Full Screen" toggle button, and "Interactive Workspace" link (`/planning`).
4. **Action Center (Bottom Grid):**
   - **Left Panel:** CP-SAT Optimization vs Manual Baseline comparative metrics (Requisition Coverage: 96.7% vs 80.0%, Express Train Delay: +11m vs +68m, Headway Violations: 0 vs 4).
   - **Right Panel:** Pending Operational Decisions list (Four-Eyes sign-off trigger, headway conflict resolve link).
5. **Overlays & Drawers:**
   - `ResponsiveDrawer` housing `EntityInspector` for `SAMPLE_CONFLICT`.
   - `PlanApprovalModal` for DRM sign-off.
   - `DigitalTwinInspectionModal` for 3D trackside inspection of selected section (`SEC-12`).

#### Interactive Controls & Event Handlers
- **"3D Twin View" Button:** Invokes `handleOpenDigitalTwin('SEC-12')` which sets `isDigitalTwinOpen(true)`.
- **"Full Screen" Button:** Toggles `isMapFullScreen` state. Also listens for `Escape` key to exit full screen.
- **Card 2 Click:** Sets `isConflictDrawerOpen(true)` to slide out the conflict inspection drawer.
- **Card 4 Click / "Sign Off" Button:** Sets `isApprovalModalOpen(true)` to present the Four-Eyes approval dialog.
- **"Resolve" Button:** Navigates via `Link` to `/planning?subtab=CONFLICTS`.

#### Data Sources & Dependencies
- **Data Sources:** `DEMO_SCENARIO`, `DEMO_CORRIDOR`, `DEMO_PLAN_VERSION`, `SAMPLE_CONFLICT` from `@/lib/api/client`.
- **Dependencies:** `AppShell`, `MapLibreRailwayMap`, `EntityInspector`, `PlanApprovalModal`, `DigitalTwinInspectionModal`, `ResponsiveDrawer`.

#### Usability & Preservation Requirements
- **Preservation:** The 4-question executive briefing structure provides immediate situational awareness and connects directly to Planning, Governance, and Digital Twin workflows.

---

### 2.3 Route: `/planning` — Planning & CP-SAT Solver Workspace

* **Source File:** [`frontend/src/app/(workspace)/planning/page.tsx`](file:///d:/Trackmeld/frontend/src/app/(workspace)/planning/page.tsx)
* **Component Name:** `PlanningPageContent` (wrapped in `Suspense`)
* **Purpose:** Core railway planning workspace where planners view timetable trajectories, detect headway and resource conflicts, execute the CP-SAT discrete optimization solver, validate safety constraints, run causal diagnostics, and prepare plans for executive approval.

#### Visual Layout & View Modes
The workspace supports **9 distinct view modes** controlled via `activeViewMode` (synchronized with `?subtab=` URL query param):

1. **`INTEGRATED` Mode (Default 3-Panel Split):**
   - **Left Panel:** `MapLibreRailwayMap` (GIS corridor view) with section/task click selection.
   - **Top-Right Panel:** `TaskQueueTable` (interactive table of 30 maintenance requisitions with priority, duration, window, and status).
   - **Bottom-Right Panel:** Tabbed container toggling between:
     - `TIMELINE`: Gantt possession schedule view (`TimelineScheduleView`).
     - `TIMESPACE`: Stringline distance-time trajectories (`TimeSpaceChart`).
     - `DIAGNOSTICS`: Causal diagnostics report (`DiagnosticsWorkspace`).
2. **`MAP` Mode:** Full-height GIS corridor map with spatial station nodes and train positions.
3. **`TIMESPACE` Mode:** Full-height Stringline diagram plotting train movement trajectories against planned possession block rectangles across the 440 km corridor.
4. **`TIMELINE` Mode:** Full-height Gantt possession schedule visualizer.
5. **`TASKS` Mode:** Full-height maintenance task requisition workspace (`TasksWorkspace`).
6. **`CONFLICTS` Mode:** Active conflict resolution workspace (`ConflictsWorkspace`).
7. **`VALIDATION` Mode:** Independent 13-category safety validation firewall report (`ValidationWorkspace`).
8. **`DIAGNOSTICS` Mode:** Solver causal diagnostics report (`DiagnosticsWorkspace`).
9. **`COPILOT` Mode:** Embedded conversational AI decision support terminal (`CopilotWorkspace`).

#### Interactive Controls & Event Handlers
- **"Run CP-SAT Solver" Button (`handleTriggerSolve`):**
  1. Sets `isSolving(true)` and displays animated solver progress messages (`Compiling 127 discrete interval constraints...`).
  2. Calls `optimizeSchedule(scenario.scenario_id, 5.0)` via FastAPI. (Gracefully falls back to certified `DEMO_SCHEDULE_RESULT` if backend is offline).
  3. Calls `validateSchedule(scenario.scenario_id, sched)` via FastAPI.
  4. Calls `diagnoseSchedule(scenario.scenario_id, sched)`.
  5. Refreshes active plan version via `getPlanVersions()`.
- **"Compare Plans" Button:** Opens `ComparePlansModal` comparing Manual Baseline vs CP-SAT vs Whole-Section possession strategies.
- **"Approve Plan" Button:** Opens `PlanApprovalModal` for Four-Eyes sign-off.
- **"3D Twin" Button:** Opens `DigitalTwinInspectionModal` targeting the currently selected track section.
- **Docked Entity Inspector (`EntityInspector`):** Automatically docks on desktop screens $\ge 1280\text{px}$ (collapsible via icon). Updates reactively when any Task, Train, Section, Station, or Conflict is clicked.
- **Selection Synchronization:** Selecting a task in `TaskQueueTable` highlights the corresponding section on `MapLibreRailwayMap`, updates the inspection drawer, and centers the timeline view.

#### Data Sources & API Endpoints
- `GET /scenarios/{id}/bundle` (`getScenarioBundle`)
- `POST /planning/optimize` (`optimizeSchedule`)
- `POST /planning/validate` (`validateSchedule`)
- `POST /planning/diagnostics` (`diagnoseSchedule`)
- `GET /plan-versions?scenario_id={id}` (`getPlanVersions`)
- `POST /plan-versions/{id}/approve` (`approvePlanVersion`)
- `POST /plan-versions/{id}/reject` (`rejectPlanVersion`)

#### Usability & Preservation Requirements
- **Critical Preservation:** Must strictly maintain the bidirectional selection synchronization between `MapLibreRailwayMap`, `TaskQueueTable`, `TimeSpaceChart`, and `EntityInspector`. Must preserve the multi-stage solve-validate-diagnose pipeline.

---

### 2.4 Route: `/work-orders` — Maintenance Work Orders & Requisitions

* **Source File:** [`frontend/src/app/(workspace)/work-orders/page.tsx`](file:///d:/Trackmeld/frontend/src/app/(workspace)/work-orders/page.tsx)
* **Component Name:** `WorkOrdersPage`
* **Purpose:** Comprehensive inventory and management interface for track maintenance requisitions, permanent way work orders, S&T point machine overhauls, and 25 kV AC OHE power block requests.

#### Visual Layout & Main Sections
1. **Header Bar:** Requisition count, "3D Twin" button, and "Inspect Selected" drawer toggle button.
2. **Operational Statistics Strip:** 4 compact KPI tiles: Total Requisitions (30), Certified (29), Unplaced (1 due to headway contention), Active Possessions (8 blocks).
3. **Filter Bar:** Real-time text search input, Department filter dropdown (`ALL`, `ENGINEERING`, `ELECTRICAL_TRD`, `SIGNAL_AND_TELECOM`), and Status filter dropdown (`ALL`, `SCHEDULED`, `UNSCHEDULED`).
4. **Master Work Orders Data Table:**
   - Columns: Order Code, Title, Department Badge, Work Type, Section, Spatial Span (`km X.X to Y.Y`), Execution Window, Traffic Block Required, Priority Badge, Actions.
   - Interactive rows: Clicking any row highlights the record and opens `EntityInspector`.
5. **Slide-Out Inspector Drawer:** `EntityInspector` displaying required duration, earliest start/latest finish, machinery required, crew assignment, and traction isolation requirements.
6. **3D Digital Twin Modal:** `DigitalTwinInspectionModal` targeting the active work order's block section.

#### Interactive Controls & Event Handlers
- **Text Search Input:** Filters rows matching task code, title, or section code.
- **Department Dropdown:** Filters table by railway department.
- **Status Dropdown:** Filters by scheduled vs unplaced status.
- **Row Click:** Invokes `handleRowClick(taskId)` which sets `selectedTaskId` and opens the inspector.
- **"3D Twin" Action Button:** Invokes `handleOpenDigitalTwin(selectedTask.section_code)`.

#### Disconnected Feature Finding
- **Sidebar Tab Disconnect:** The sidebar links to `/work-orders?tab=resources`. However, `WorkOrdersPage` currently does not read `useSearchParams()` for `tab=resources`, rendering the standard work orders list instead of a dedicated crew/machinery resource allocation view.

#### Data Sources & Dependencies
- **Data Sources:** `EXTENDED_WORK_ORDERS` (seeded in component file, expanding on `DEMO_TASKS`), `DEMO_SCHEDULE_RESULT`.
- **Dependencies:** `AppShell`, `EntityInspector`, `DigitalTwinInspectionModal`, `ResponsiveDrawer`, `Button`.

---

### 2.5 Route: `/network` — Rail Network & Infrastructure GIS

* **Source File:** [`frontend/src/app/(workspace)/network/page.tsx`](file:///d:/Trackmeld/frontend/src/app/(workspace)/network/page.tsx)
* **Component Name:** `NetworkPageContent` (wrapped in `Suspense`)
* **Purpose:** Deep domain explorer for railway physical infrastructure, geographic topology, signaling assets, traction electrification, and rolling stock fleet.

#### Visual Layout & 6 Subtabs
Controlled via `activeSubTab` state and URL query parameter (`?subtab=` or `?tab=rolling-stock`):
1. **`MAP` Subtab:** Full-height `MapLibreRailwayMap` with interactive layer toggles (Tracks, Stations, Signals, OHE, Trains), zoom/fit bounds controls, and full-screen toggle.
2. **`STATIONS` Subtab:** Data table of corridor stations (NDLS, GZB, ALJN, TDL, ETW, CNB) with distance chainages, track count, platform count, facilities, and interlocking status.
3. **`TRACKS` Subtab:** Data table of 32 block sections with gauge ($1676\text{mm}$ Broad Gauge), rail type (UIC 60), speed limits ($130\text{--}160\text{ km/h}$), traction voltage ($25\text{ kV AC}$), and track condition.
4. **`SIGNALS` Subtab:** Inventory table of automatic block signals, signal type (4-Aspect Color Light), aspect (Green/Double Yellow/Yellow/Red), and kilometer chainage.
5. **`OHE` Subtab:** 25 kV AC Traction overhead equipment posts, feeding posts, sectioning posts, and neutral sections.
6. **`FLEET` Subtab:** Active train movements table showing rake type (Vande Bharat EMU, WAP-7 Shatabdi/Rajdhani, Freight Container), direction (UP/DN), entry/exit stations, priority tier, and timetable.
   *(Note: The sidebar link `/network?tab=rolling-stock` maps directly to this `FLEET` subtab via URL parameter normalization).*

#### Interactive Controls & Event Handlers
- **Subtab Navigation Pills:** Updates active subtab and synchronizes browser history via `router.push(`${pathname}?subtab=${tab}`)`.
- **Search & Filter Input:** Performs live search filtering across stations, sections, signals, and trains.
- **Row Click / Inspect:** Opens `EntityInspector` populated with contextual GIS metadata.
- **"3D Twin" Button:** Launches `DigitalTwinInspectionModal` for the selected block section.

#### Data Sources & Dependencies
- **Data Sources:** `corridorGisData.ts` (`CORRIDOR_STATIONS_GIS`, `CORRIDOR_SECTIONS_GIS`, `CORRIDOR_SIGNALS_GIS`, `CORRIDOR_OHE_POSTS_GIS`, `ACTIVE_TRAINS_GIS`), `DEMO_CORRIDOR`.
- **Dependencies:** `AppShell`, `MapLibreRailwayMap`, `EntityInspector`, `DigitalTwinInspectionModal`, `ResponsiveDrawer`.

---

### 2.6 Route: `/governance` — Safety Firewall & Four-Eyes Governance

* **Source File:** [`frontend/src/app/(workspace)/governance/page.tsx`](file:///d:/Trackmeld/frontend/src/app/(workspace)/governance/page.tsx)
* **Component Name:** `GovernancePage`
* **Purpose:** Statutory safety compliance auditing and executive Four-Eyes sign-off interface enforcing the inviolable railway rule: **Optimization schedules. Humans approve.**

#### Visual Layout & Main Sections
1. **Header Bar:** Safety status badge (`100% Certified · 13/13 Hard Rules Verified`), active scenario identity, and "Sign Off Candidate Plan" CTA button.
2. **Four-Eyes Governance Gate Card:**
   - Visual step indicator: `SOLVER COMPLETED` $\to$ `INDEPENDENT VALIDATION PASS` $\to$ `PENDING FOUR-EYES REVIEW` $\to$ `ISSUED TO TRACK`.
   - Cryptographic Schedule Identity display (SHA-256 hash: `bae346ecf37b1fd80608cc5e0b8dae030517a44d5d5305f640d5767ed46999aa`).
   - Sign-off button triggering `PlanApprovalModal`.
3. **The 13 Statutory Safety Validation Check Cards:**
   Displays explicit audit cards for all 13 independent validator rules:
   1. `VAL-STRUCT-01`: Structural Topology & Adjacency Continuity
   2. `VAL-HORIZON-02`: Planning Horizon Bounds (24h)
   3. `VAL-TASKWIN-03`: Task Window Feasibility
   4. `VAL-BUFFERS-04`: Mandatory Possession Buffers (15m setup + 15m clearance)
   5. `VAL-OCCUPANCY-05`: Track Occupancy Non-Overlap
   6. `VAL-MULTISECT-06`: Multi-Section Spatial Continuity
   7. `VAL-HEADWAY-07`: Train Movement Clearance & Headway (7m minimum)
   8. `VAL-RESOURCE-08`: Resource Non-Overlap (CSM, BCM, Gangs)
   9. `VAL-DEPENDENCY-09`: Finish-to-Start Precedence
   10. `VAL-MANDATORY-10`: Mandatory Requisition Coverage (100%)
   11. `VAL-ADJACENT-11`: Adjacent Track Safety & Caution Orders
   12. `VAL-ISOLATION-12`: Electrical Traction Isolation (25 kV AC OHE)
   13. `VAL-IDENTITY-13`: Cryptographic Schedule Identity Preservation
4. **Audit Trail Summary & Multi-Disciplinary Reviews:**
   - Displays history of creation, validation, and review actions.

#### Interactive Controls & Event Handlers
- **"Sign Off Candidate Plan" Button:** Sets `isApprovalModalOpen(true)` to launch `PlanApprovalModal`.
- **`PlanApprovalModal` Handlers:** Submits reviewer name, role, and comments to `approvePlanVersion()` or `rejectPlanVersion()`.

#### Data Sources & Dependencies
- **Data Sources:** `VALIDATION_CHECKS` array, `DEMO_PLAN_VERSION`, `DEMO_AUDIT_LOGS`, `approvePlanVersion()`, `rejectPlanVersion()`.
- **Dependencies:** `AppShell`, `PlanApprovalModal`, `ResponsiveDrawer`, `Button`.

---

### 2.7 Route: `/copilot` — AI Decision Support Copilot

* **Source File:** [`frontend/src/app/(workspace)/copilot/page.tsx`](file:///d:/Trackmeld/frontend/src/app/(workspace)/copilot/page.tsx)
* **Component Name:** `CopilotPage`
* **Purpose:** Dedicated conversational decision support terminal providing grounded, read-only causal explanations of solver choices, conflict resolutions, and Indian Railways operating manual citations.

#### Visual Layout & Main Sections
1. **Header Bar:** Copilot identity, "READ-ONLY EXPLAINER" badge, and statutory safety notice: `Zero write-tools • Does NOT schedule trains`.
2. **Embedded Terminal Surface (`CopilotWorkspace.tsx`):**
   - Message stream displaying user queries and structured Copilot responses formatted via `MarkdownRenderer`.
   - Evidence Chips: Structured cards citing exact task IDs, train movements, block sections, and statutory rule codes (`RULE-HDW-01`, `IRS-TRACK-MANUAL-C12`).
   - Slide-out Evidence Detail Drawer (`ResponsiveDrawer`) displaying the raw underlying telemetry snapshot when an evidence card is clicked.
   - Suggested Inquiry Quick Pills (e.g., *"Why was TSK-0007 unscheduled?"*, *"Explain the 15m possession safety buffer"*).
   - Prompt Input Bar: Multiline textarea with `Enter` (send) and `Shift+Enter` (newline) handlers, and send button.

#### Interactive Controls & Event Handlers
- **`handleSend`:** Calls `askCopilot({ prompt, scenario_id: 'SCN-DEMO-001' })` pointing to `/api/v1/copilot/explain`.
- **Evidence Click Handler:** Clicking an evidence chip slides out the evidence inspector drawer.
- **Pre-canned Question Pills:** Inserts question text into prompt input and automatically sends query.

#### Guardrail & Safety Boundaries
- If the backend is unreachable or returns an error, Copilot displays a formal decision support notice explaining that under Indian Railways operating boundaries, it cannot speculate or hallucinate answers without live verified database records.

#### Data Sources & Dependencies
- **Data Sources:** `askCopilot()` via `/api/v1/copilot/explain`.
- **Dependencies:** `AppShell`, `CopilotWorkspace`, `MarkdownRenderer`, `ResponsiveDrawer`.

---

### 2.8 Route: `/audit` — Compliance & Plan Version Ledger

* **Source File:** [`frontend/src/app/(workspace)/audit/page.tsx`](file:///d:/Trackmeld/frontend/src/app/(workspace)/audit/page.tsx)
* **Component Name:** `AuditPage`
* **Purpose:** Statutory audit log, version ledger, and multi-disciplinary engineering sign-off record tracking the entire lifecycle of every generated plan version.

#### Visual Layout & Main Sections
1. **Header Bar:** Audit ledger title, version count, and refresh button.
2. **Left Panel — Plan Version History Selector:**
   - Chronological list of plan versions (`v1.2`, `v1.1`, `v1.0`, `v0.9`).
   - Cards display version badge, status (`PENDING_REVIEW`, `APPROVED`, `REJECTED`), creator, timestamp, task coverage metrics, and truncated SHA-256 cryptographic identity.
3. **Right Panel (Top) — Plan Version Detailed Record:**
   - Selected version details, full 64-character SHA-256 hash with copy button, validation status, and dual approval/rejection action buttons.
4. **Right Panel (Middle) — Multi-Disciplinary Engineering Review Thread:**
   - Comments from Traction Power Inspector (OHE), Chief Operations Officer, Permanent Way Engineer.
   - Text input allowing operators to add dated review comments to the ledger.
5. **Right Panel (Bottom) — Immutable Audit Event Trail:**
   - Historical event ledger displaying timestamp, event type (`PLAN_VERSION_CREATED`, `PLAN_APPROVED`), actor username, actor role, and schedule hash.

#### Interactive Controls & Event Handlers
- **Version Card Click:** Updates `selectedVersionId` to inspect the chosen historical plan.
- **"Approve Plan" / "Reject Plan" Buttons:** Opens `PlanApprovalModal`.
- **Add Review Comment:** Appends a new timestamped review comment to `comments` state.
- **Copy Hash Button:** Copies full SHA-256 schedule identity to system clipboard.

#### Data Sources & Dependencies
- **Data Sources:** `getPlanVersions()`, `getPlanVersionAudit()`, `approvePlanVersion()`, `rejectPlanVersion()`, `INITIAL_VERSIONS`, `INITIAL_COMMENTS`.
- **Dependencies:** `AppShell`, `PlanApprovalModal`, `Button`.
