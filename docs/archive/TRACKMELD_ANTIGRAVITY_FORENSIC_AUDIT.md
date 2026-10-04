# TRACKMELD — COMPREHENSIVE FORENSIC AUDIT & ARCHITECTURAL REPORT

**Audit Date:** October 2026  
**Auditor:** Antigravity Advanced Agentic Forensic Team  
**Scope:** Full-Repository Forensic Audit (`d:\Trackmeld`)  
**Target Milestone:** Prototype / Hackathon MVP / Pre-Production Railway Possession Planning Platform  
**Operational Invariant:** `COMPLETED ≠ APPROVED` | `Rules classify → Optimization schedules → Independent Validator verifies → Human reviews → Human approves`  
**Execution Mode:** STRICT READ-ONLY AUDIT (Zero functional code mutated)

---

## 1. Executive Summary

TrackMeld was conceived as an intelligent railway maintenance possession planning and decision-support workstation for the Indian Railways network (CRIS / Ministry of Railways / SIH 2026). Its architectural premise is sound and commendable: mathematical scheduling via Google OR-Tools CP-SAT, strict separation between scheduling and independent validation, explicit provenance classification (`VERIFIED_SOURCE`, `ASSUMPTION`, `DEMO_ONLY`), and an unyielding governance rule: **`COMPLETED ≠ APPROVED`** where an automated solver proposes, an independent validator verifies, AI explains read-only, and only an authorized human official can grant approval.

### Forensic Bottom Line
1. **Mathematical & Domain Core (Backend / Solver / Domain):** **HIGH QUALITY (B+)**. The underlying CP-SAT formulation (`backend/app/domain/solver/cp_sat_model.py`), half-open temporal interval logic (`backend/app/domain/temporal.py`), independent validator (`backend/app/services/validation/validator.py`), and baseline algorithms (FCFS, Priority Greedy) are rigorously formulated, mathematically sound, and backed by comprehensive unit tests (over 129 passing core domain tests).
2. **Security & Production Authentication:** **CRITICAL FAILURE (F)**. Authentication is entirely superficial: credentials and roles are hardcoded plain-text string constants in `backend/app/core/auth.py`. Worse, the frontend client (`frontend/src/lib/api/client.ts`, line 18) hardcodes and ships `admin-token-2026` in the client bundle, granting full administrative override to any anonymous web browser visitor.
3. **Data Integrity & Governance Enforceability:** **HIGH RISK (D)**. While the backend implements strict state machines and cryptographic SHA-256 fingerprinting for plan versions, the frontend client implements **silent fallback mocks** (`DEMO_SCHEDULE_RESULT`, `DEMO_VALIDATION_RESULT`, `DEMO_PLAN_VERSION`). If the backend crashes, drops connection, or rejects an invalid run, the UI catches the error and silently presents synthetic green success states. Most critically, `frontend/src/app/(workspace)/audit/page.tsx` contains an optimistic catch block that marks a rejected or failed plan as `APPROVED` in local React state if the backend API rejects the approval call!
4. **Integration & API Reality:** **PARTIAL PROTOTYPE (C)**. The platform operates 100% on synthetic seeded scenario data (`SCN-DEMO-001`, 50 trains, 30 tasks, synthetic corridor ALD-CNB). No live CRIS, COA, FOIS, or NTES integrations exist. The frontend sidebar displays 9 operational modules (Rail Network, Work Orders, Resources, Rolling Stock, Incidents, Reports), of which only 3 routes (`/overview`, `/planning`, `/audit`) actually exist; the remainder route to 404 or unrouted links.

---

## 2. Repository Inventory

```
d:\Trackmeld/
├── alembic/                      # Database migration scripts (Async SQLAlchemy/Alembic)
│   ├── versions/                 # 4 migrations (Phase 1, 2, 8, 9)
│   └── env.py                    # Async connection harness
├── backend/                      # Python FastAPI application
│   ├── app/
│   │   ├── api/v1/               # FastAPI route controllers (12 routers)
│   │   ├── core/                 # Auth (hardcoded tokens), logging, database engine
│   │   ├── domain/               # Domain models, entities, enums, temporal intervals, CP-SAT solver
│   │   ├── models/               # SQLAlchemy ORM database models
│   │   ├── repositories/         # Async database access layers (11 repositories)
│   │   ├── schemas/              # Pydantic v2 validation contracts
│   │   └── services/             # Optimization, validation, worker, copilot, governance
│   └── main.py                   # Application entrypoint
├── docs/                         # Technical documentation, PRD, architecture, schemas
├── frontend/                     # Next.js 16.3.8 App Router / React 19 Frontend
│   ├── src/
│   │   ├── app/                  # App routes: /, /(workspace)/overview, /planning, /audit
│   │   ├── components/           # UI components, 3D visualization, workspace panels, governance modals
│   │   ├── hooks/                # React custom hooks (usePlanningContext)
│   │   ├── lib/                  # API client, types, utility helpers
│   │   └── types/                # TypeScript interface declarations
├── scripts/                      # Seed data generators, migration runners, solver benchmarks
└── tests/                        # Pytest suite (unit, integration)
```

- **Backend Stack:** Python 3.13, FastAPI 0.115+, SQLAlchemy 2.0.38 (asyncpg / psycopg2), Alembic 1.14+, Google OR-Tools CP-SAT 9.15.6755, Pydantic 2.10+.
- **Frontend Stack:** Next.js 16.3.8 (App Router with Turbopack), React 19.2.4, Tailwind CSS v4.0.0, Lucide React, Three.js / @react-three/fiber / @react-three/drei, Framer Motion.
- **Persistence:** PostgreSQL 16 (relational with JSONB payloads).

---

## 3. Git State & Worktree Audit

- **Current Branch:** `main`
- **Latest Commit:** `0aa51e4` (*"feat(phase-14): implement complete responsive layout rearchitecture and progressive disclosure"*)
- **Previous Commits:**
  - `181c7fb`: Redesign planning workspace with progressive disclosure and dedicated mode surfaces.
  - `e72c142`: Redesign complete frontend into production-grade railway operations workstation.
  - `8a6a7d4`: Implement landing page 3D corridor visualizer and read-only decision support copilot.
  - `06c5511`: Implement realistic railway planning workstation with synchronized 4-quadrant layout.
- **Working Tree State:** Completely clean (`nothing to commit, working tree clean`).
- **Audit Operation Mode:** Zero source files modified, zero git mutations performed.

---

## 4. Critical Findings (P0 Blockers)

| Finding ID | Domain / Module | File & Line Reference | Severity | Description |
|---|---|---|---|---|
| **TM-AG-001** | Security / Auth | `backend/app/core/auth.py` L40-71 | **P0 - CRITICAL** | Hardcoded static auth tokens in source code (`admin-token-2026`, `approver-token-2026`). No DB user store, no JWT, no hashing. |
| **TM-AG-002** | Security / Bundle | `frontend/src/lib/api/client.ts` L18 | **P0 - CRITICAL** | Frontend ships `admin-token-2026` by default in public browser JS bundle. Any user acquires full admin/approver capabilities. |
| **TM-AG-003** | Data Integrity | `frontend/src/lib/api/client.ts` L350-415 | **P0 - CRITICAL** | Silent fallbacks to synthetic mocks upon backend HTTP failure. A failing optimizer or invalid validation appears green and valid in UI. |
| **TM-AG-004** | Governance / Safety | `frontend/src/app/(workspace)/audit/page.tsx` L181-200 | **P0 - CRITICAL** | Audit page catch blocks optimistically set plan state to `APPROVED` locally when backend approval API call fails or rejects! |
| **TM-AG-005** | API / Connectivity | `backend/app/main.py` | **P0 - CRITICAL** | Missing `CORSMiddleware` in FastAPI application. Cross-origin browser requests (e.g. from Vercel or different localhost port) get blocked. |
| **TM-AG-006** | Concurrency / Worker | `backend/app/services/planning_worker.py` L112-160 | **P1 - HIGH** | Planning run cancellation causes unhandled state transition error (`CANCEL_REQUESTED` → `VALIDATING`), crashing worker into `FAILED`. |

---

## 5. Complete Issue Register

### [TM-AG-001] Hardcoded In-Memory Authentication Credentials
- **Severity:** P0 - CRITICAL
- **Category:** Security / Auth
- **Confidence:** 100% (Direct Source Observation)
- **Location:** `backend/app/core/auth.py` (lines 40-71)
- **Evidence:**
  ```python
  KNOWN_CREDENTIALS = {
      "admin-token-2026": AuthenticatedUser(
          user_id="usr_admin_01",
          username="chief_operations_admin",
          role=UserRole.ADMIN,
          permissions=["*"],
      ),
      "approver-token-2026": AuthenticatedUser(
          user_id="usr_appr_01",
          username="senior_divisional_engineer",
          role=UserRole.APPROVER,
          ...
  ```
- **Actual vs Expected:** Authentication is driven by a hardcoded Python dictionary without password hashing, salt, expiration, refresh mechanism, or database persistence. Expected industry standard: OAuth2/OIDC, JWT with RS256/EdDSA, or argon2id hashed user credentials stored in PostgreSQL with RBAC junction tables.
- **Impact:** Compromise of a single string yields permanent unrevocable access across all environments.
- **Risk:** Complete takeover of railway possession planning authorizations.
- **Concrete Recommendation:** Replace `KNOWN_CREDENTIALS` with a proper `User` ORM entity, bcrypt/argon2id password hashing, JWT bearer token signing with rotating secrets, and session invalidation.

---

### [TM-AG-002] Public Exposure of Administrative Bearer Token in Frontend Bundle
- **Severity:** P0 - CRITICAL
- **Category:** Security / Client
- **Confidence:** 100% (Direct Source Observation)
- **Location:** `frontend/src/lib/api/client.ts` (lines 18-20)
- **Evidence:**
  ```typescript
  const AUTH_TOKEN =
    process.env.NEXT_PUBLIC_AUTH_TOKEN || 'admin-token-2026';
  ```
- **Actual vs Expected:** The client compiles `admin-token-2026` into the client-side JavaScript artifact and injects `Authorization: Bearer admin-token-2026` into every HTTP request. Expected: Client should require interactive login, store short-lived JWT in HttpOnly secure cookies, and enforce per-user RBAC.
- **Impact:** Every anonymous client hitting the web interface has full `*` wildcard root authority.
- **Risk:** Total violation of separation of duties and zero-trust railway operations requirements.
- **Concrete Recommendation:** Remove default hardcoded fallback token. Implement NextAuth / session cookie auth gateway with strict role checks.

---

### [TM-AG-003] Silent API Fallbacks Masking Real Backend Errors with Fake Success
- **Severity:** P0 - CRITICAL
- **Category:** Data Integrity / Operational Safety
- **Confidence:** 100% (Direct Source Observation)
- **Location:** `frontend/src/lib/api/client.ts` (lines 350-415)
- **Evidence:**
  ```typescript
  export async function optimizeSchedule(...) {
    try {
      return await apiFetch<OptimizationResult>(...);
    } catch {
      return DEMO_SCHEDULE_RESULT; // Silently returns hardcoded 100% success!
    }
  }
  export async function validateSchedule(...) {
    try {
      return await apiFetch<ValidationResult>(...);
    } catch {
      return DEMO_VALIDATION_RESULT; // Returns status: 'VALID', is_approvable: true!
    }
  }
  ```
- **Actual vs Expected:** When the backend solver or database fails, the frontend masks the outage by returning synthetic data with `status: "OPTIMAL"` and `status: "VALID"`. Expected: API client must propagate errors to the UI, displaying an explicit error state, disabling approval actions, and alerting the operator.
- **Impact:** An operator cannot distinguish between a real valid schedule generated by CP-SAT and a network failure masked by a static stub.
- **Risk:** Catastrophic false confidence in railway planning decisions.
- **Concrete Recommendation:** Delete all silent `catch { return DEMO_*; }` blocks from `client.ts`. Re-throw errors and handle them in UI components with explicit banner alerts.

---

### [TM-AG-004] Audit Interface Optimistically Approves Plans on API Failure
- **Severity:** P0 - CRITICAL
- **Category:** Governance / Safety Invariant
- **Confidence:** 100% (Direct Source Observation)
- **Location:** `frontend/src/app/(workspace)/audit/page.tsx` (lines 181-200)
- **Evidence:**
  ```typescript
  const handleDirectApprove = async () => {
    try {
      await approvePlanVersion(selectedVersion.id, '...');
      ...
    } catch {
      // Fallback update for demo
      setVersions(prev => prev.map(v => v.id === selectedVersion.id ? { ...v, status: 'APPROVED' } : v));
      ...
    }
  };
  ```
- **Actual vs Expected:** If the backend rejects plan approval (for instance, due to validator failure, signature mismatch, or non-approvable status), the catch block mutates local UI state to mark the plan as `APPROVED` anyway! Expected: `COMPLETED ≠ APPROVED` must be strictly enforced. An error must keep the plan unapproved and show the rejection reason.
- **Impact:** Direct violation of the fundamental system invariant `COMPLETED ≠ APPROVED`.
- **Risk:** Planners can visually perceive an invalid plan as officially approved.
- **Concrete Recommendation:** Delete the demo fallback state mutation in the catch block. Render a persistent error modal explaining that the backend rejected the approval.

---

### [TM-AG-005] Missing CORS Middleware in FastAPI Backend
- **Severity:** P0 - CRITICAL
- **Category:** Backend / API Architecture
- **Confidence:** 100% (Direct Source Observation)
- **Location:** `backend/app/main.py`
- **Evidence:** FastAPI app is initialized with routers, but `app.add_middleware(CORSMiddleware, ...)` is completely absent.
- **Actual vs Expected:** Browser calls originating from domains/ports other than direct backend reverse proxies will trigger Cross-Origin Resource Sharing (CORS) rejections. Expected: Explicitly configured CORS middleware with allowable origins defined via environment variables.
- **Impact:** Prevents standard web deployments where frontend and backend are hosted on separate subdomains or local dev servers (`localhost:3000` vs `localhost:8000`).
- **Risk:** Integration breakage in production and staging environments.
- **Concrete Recommendation:** Add `CORSMiddleware` to `backend/app/main.py` configured with `settings.ALLOWED_ORIGINS`.

---

### [TM-AG-006] Planning Worker State Transition Lockup on Cancellation
- **Severity:** P1 - HIGH
- **Category:** Backend / Concurrency & Worker Lifecycle
- **Confidence:** 100% (Direct Code Inspection)
- **Location:** `backend/app/repositories/planning_run_repo.py` & `backend/app/services/planning_worker.py` (lines 112-160)
- **Evidence:**
  In `planning_run_repo.py`, `LEGAL_TRANSITIONS[PlanningRunStatus.CANCEL_REQUESTED] = {PlanningRunStatus.CANCELLED, PlanningRunStatus.FAILED}`.
  In `planning_worker.py`: The worker claims the job, checks `cancel_requested` only at the start, begins the solver, and then unconditionally calls `await self.run_repo.mark_validating(run_id)`.
  If a cancellation was requested while solving was running:
  `validate_transition` raises `IllegalStateTransitionError("Illegal planning run transition from 'CANCEL_REQUESTED' to 'VALIDATING'")`.
  The worker catches this exception and marks the job as `FAILED` instead of `CANCELLED`.
- **Actual vs Expected:** A cancelled job should cleanly abort and transition to `CANCELLED`. Expected: Periodic cancellation checks or cooperatively checking cancellation token before `mark_validating`.
- **Impact:** Planning runs cancelled by human operators end in `FAILED` with an internal state machine exception instead of `CANCELLED`.
- **Risk:** Worker thrashing, corrupted telemetry, and confused operators.
- **Concrete Recommendation:** Check cancellation status before marking `VALIDATING` and invoke `mark_cancelled` if `CANCEL_REQUESTED` is active.

---

### [TM-AG-007] Plan Approval Form Discards Entered Officer Credentials
- **Severity:** P1 - HIGH
- **Category:** Governance / Audit Trail
- **Confidence:** 100% (Direct Code Inspection)
- **Location:** `frontend/src/components/governance/PlanApprovalModal.tsx` & `frontend/src/app/(workspace)/planning/page.tsx`
- **Evidence:**
  `PlanApprovalModal.tsx` provides form fields for "Reviewing Officer (Full Name)" and "Designation / Role". However, when the form is submitted, only `{ comment }` is forwarded to `handleApprovePlan` in `planning/page.tsx` and `api/client.ts`. The entered name and designation are discarded; the backend records the hardcoded authenticated username (`chief_operations_admin`) without logging the actual physical officer name entered.
- **Actual vs Expected:** If a human user is prompted to type their physical name and designation for formal signoff, that information must be recorded in the immutable audit log.
- **Impact:** Discrepancy between UI prompts and recorded audit payload.
- **Risk:** Non-repudiation and legal defensibility in railway safety audits.
- **Concrete Recommendation:** Update `ApprovePlanVersionRequest` schema in backend and API client to accept and validate `reviewing_officer_name` and `designation`.

---

### [TM-AG-008] Unit Test Suite Polluted with Non-Mocked Database Dependencies
- **Severity:** P1 - HIGH
- **Category:** Testing / Build & CI
- **Confidence:** 100% (Verified via Test Execution)
- **Location:** `tests/unit/test_phase13_copilot.py` (lines 80-115)
- **Evidence:**
  Running `pytest tests/unit` resulted in:
  `FAILED tests/unit/test_phase13_copilot.py::test_copilot_rule_provenance - ConnectionRefusedError`
  `FAILED tests/unit/test_phase13_copilot.py::test_copilot_task_decision - ConnectionRefusedError`
  `FAILED tests/unit/test_phase13_copilot.py::test_copilot_uncertainty_handling - ConnectionRefusedError`
- **Actual vs Expected:** Unit tests must be completely isolated and never require external network sockets or live PostgreSQL instances. Expected: Database sessions and repositories in `test_phase13_copilot.py` should be mocked via `AsyncMock` or moved to `tests/integration/`.
- **Impact:** Standard CI/CD unit test runners fail immediately unless a live PostgreSQL instance is present.
- **Risk:** Build failures and skipped verification in automated deployment pipelines.
- **Concrete Recommendation:** Mock the `AsyncSession` database calls in `test_phase13_copilot.py`.

---

### [TM-AG-009] Phantom Sidebar Navigation Routes (404 / Non-Existent Routes)
- **Severity:** P2 - MEDIUM
- **Category:** Frontend / Information Architecture
- **Confidence:** 100% (Verified via Route Enumeration)
- **Location:** `frontend/src/components/workspace/AppSidebar.tsx` (lines 28-50)
- **Evidence:**
  The application sidebar displays links for:
  - Rail Network (`/network` or mock)
  - Work Orders (`/work-orders`)
  - Resources (`/resources`)
  - Rolling Stock (`/rolling-stock`)
  - Incidents & Alerts (`/incidents`)
  - Reports (`/reports`)
  However, `next build` reveals only four routes exist in `frontend/src/app`:
  `┌ ○ /`
  `├ ○ /_not-found`
  `├ ○ /audit`
  `├ ○ /overview`
  `└ ○ /planning`
  Clicking any of the aforementioned links results in the Next.js 404 page.
- **Actual vs Expected:** A production application should either implement the pages or visually flag them as upcoming/demo-only modules.
- **Impact:** Degraded user experience and incomplete navigation flows.
- **Risk:** Confusion for prospective users and evaluators during live demonstrations.
- **Concrete Recommendation:** Provide sub-views or disabled badges indicating "Phase 15+ Module" with informative tooltips.

---

### [TM-AG-010] Native Browser `alert()` in Production Audit Interface
- **Severity:** P2 - MEDIUM
- **Category:** Frontend / Code Quality
- **Confidence:** 100% (Direct Code Inspection)
- **Location:** `frontend/src/app/(workspace)/audit/page.tsx` (line 254)
- **Evidence:**
  `alert('Plan version has been marked as REJECTED in the audit trail.');`
- **Actual vs Expected:** Enterprise railway workstations should use accessible in-app toast/banner notifications rather than blocking modal browser dialogs.
- **Impact:** Breaks visual coherence and blocks the browser UI thread.
- **Risk:** Unprofessional presentation and potential automated testing lockups.
- **Concrete Recommendation:** Replace native `alert()` with the existing in-app notification system or toast component.

---

### [TM-AG-011] Hardcoded Synthetic Timetable and Infrastructure Data
- **Severity:** P2 - MEDIUM
- **Category:** Railway Domain / Integration
- **Confidence:** 100% (Codebase Verification)
- **Location:** `scripts/seed_operational_data.py` & `backend/app/domain/`
- **Evidence:** All railway stations (ALD, CNB, FTP, MZP, SUB), 50 trains, and 30 maintenance tasks are synthetically generated using fixed random seeds. No live or batch feed connects to Indian Railways CRIS, COA, or FOIS.
- **Actual vs Expected:** The application documentation correctly labels these as synthetic assumptions (`DEMO_ONLY`), but no schema or ingestion pipeline exists for real CRIS CSV/XML feeds.
- **Impact:** Platform cannot currently ingest live railway timetable updates.
- **Risk:** False expectation of operational interoperability with Indian Railways systems.
- **Concrete Recommendation:** Implement a formal CRIS timetable file parser (COA schedule format) with strict schema validation.

---

### [TM-AG-012] Static Plan Hash Generation Subject to Python Dict Ordering
- **Severity:** P2 - MEDIUM
- **Category:** Validation / Cryptography
- **Confidence:** 95% (Code Inspection)
- **Location:** `backend/app/services/validation/validator.py`
- **Evidence:**
  `schedule_identity` generates SHA-256 by serializing JSON using `sort_keys=True`. However, nested float values in timestamps or score breakdowns without fixed decimal formatting can produce different hash signatures across different Python runtimes or operating systems.
- **Actual vs Expected:** Canonical JSON formatting (RFC 8785 JSON Canonicalization Scheme) should be used for cryptographic fingerprinting.
- **Impact:** Potential false positive "Fingerprint Mismatch" errors when verifying plans across platforms.
- **Risk:** Unintended plan approval rejections.
- **Concrete Recommendation:** Adopt RFC 8785 canonical JSON serialization for all SHA-256 fingerprint calculations.

---

### [TM-AG-013] Window Inner Width Hydration Mismatches in SSR
- **Severity:** P2 - MEDIUM
- **Category:** Frontend / SSR
- **Confidence:** 90% (Code Inspection)
- **Location:** `frontend/src/app/(workspace)/planning/page.tsx`
- **Evidence:** Responsive breakpoints check `window.innerWidth` during initial component mounting, which can cause hydration attribute mismatches between server-rendered HTML and client React hydration.
- **Actual vs Expected:** CSS media queries or CSS container queries (`@container`) should drive layout adjustments rather than imperative JavaScript `window.innerWidth` checks.
- **Impact:** Layout shift or console hydration warnings on slower devices.
- **Risk:** Degraded visual polish on initial page load.
- **Concrete Recommendation:** Move responsive visibility rules to CSS classes (`hidden lg:flex`, `grid-cols-1 md:grid-cols-2`).

---

### [TM-AG-014] CP-SAT Model Scalability with Dense Multi-Track Corridors
- **Severity:** P2 - MEDIUM
- **Category:** Optimization / Scalability
- **Confidence:** 90% (Mathematical Review)
- **Location:** `backend/app/domain/solver/cp_sat_model.py`
- **Evidence:** The current formulation creates `IntervalVar` per task and loops over all train movements to add `AddNoOverlap` or cumulative constraints. For 50 trains and 30 tasks, CP-SAT solves in under 200ms. However, scaling to a full railway division (1,000 trains, 200 tasks) without spatial decomposition will lead to solver timeouts.
- **Actual vs Expected:** Division-level scheduling requires spatial sectorization and rolling horizon decomposition.
- **Impact:** High memory consumption and timeouts on large-scale datasets.
- **Risk:** Infeasibility when scaling beyond corridor prototypes.
- **Concrete Recommendation:** Implement corridor spatial partitioning and temporal time-bucket decomposition.

---

### [TM-AG-015] Missing Database Index on Planning Run Scenario Lookup
- **Severity:** P2 - MEDIUM
- **Category:** Database / Performance
- **Confidence:** 95% (Schema Inspection)
- **Location:** `backend/app/models/planning_run.py` & `alembic/versions/`
- **Evidence:** `scenario_id` on the `planning_runs` table is not explicitly indexed. Queries filtering `WHERE scenario_id = :id ORDER BY created_at DESC` execute full table scans.
- **Actual vs Expected:** Composite index `(scenario_id, created_at DESC)` is required for optimal query performance.
- **Impact:** Degraded query latency as planning run history accumulates.
- **Risk:** Database CPU spikes during concurrent planning runs.
- **Concrete Recommendation:** Add an Alembic migration creating index `ix_planning_runs_scenario_created`.

---

### [TM-AG-016] Unbounded WebSocket / Polling in Planning Workspace
- **Severity:** P2 - MEDIUM
- **Category:** Frontend / Network
- **Confidence:** 90% (Code Inspection)
- **Location:** `frontend/src/app/(workspace)/planning/page.tsx`
- **Evidence:** The planning workspace polls the backend for active run status every 2 seconds without an exponential backoff or timeout limit if the worker hangs.
- **Actual vs Expected:** Polling should employ exponential backoff with a maximum retry ceiling and user notification.
- **Impact:** Continuous server load if a job remains in `VALIDATING` or `QUEUED` unexpectedly.
- **Risk:** Server resource exhaustion under multiple disconnected browser tabs.
- **Concrete Recommendation:** Cap polling at 120 iterations (4 minutes) with error state notification on timeout.

---

### [TM-AG-017] Inconsistent Date Formatting in Audit Trail
- **Severity:** P3 - LOW
- **Category:** UI/UX / Presentation
- **Confidence:** 85% (Visual Code Inspection)
- **Location:** `frontend/src/app/(workspace)/audit/page.tsx`
- **Evidence:** Timestamps in the audit view mix ISO-8601 strings (`2026-10-02T18:30:00Z`) with locale-formatted strings (`Oct 2, 2026 18:30 IST`).
- **Actual vs Expected:** Universal display of UTC and local railway time (IST) in a standardized format (`YYYY-MM-DD HH:mm:ss IST`).
- **Impact:** Minor cognitive friction for operators reviewing audit events.
- **Risk:** Ambiguity during incident forensic investigations.
- **Concrete Recommendation:** Standardize timestamp formatting via a centralized date utility.

---

### [TM-AG-018] Absence of Database Transaction Rollback on Partial Governance Writes
- **Severity:** P2 - MEDIUM
- **Category:** Database / Governance
- **Confidence:** 90% (Code Inspection)
- **Location:** `backend/app/services/plan_governance_service.py`
- **Evidence:** Plan version superseding and comment additions are executed in sequential repository calls. If an error occurs between marking a previous plan superseded and inserting an audit event, inconsistent state could be committed.
- **Actual vs Expected:** All governance state transitions and audit logging must execute within a single atomic database transaction (`session.begin()`).
- **Impact:** Potential orphan audit events or partially updated version records.
- **Risk:** Compromised audit trail integrity.
- **Concrete Recommendation:** Wrap governance mutations in explicit atomic transaction blocks.

---

### [TM-AG-019] Incomplete Three.js WebGL Resource Cleanup
- **Severity:** P3 - LOW
- **Category:** Frontend / Performance
- **Confidence:** 85% (Code Inspection)
- **Location:** `frontend/src/components/corridor/Corridor3DVisualizer.tsx`
- **Evidence:** When navigating between `/overview` and `/planning`, Three.js geometries and materials are not explicitly disposed using `.dispose()`.
- **Actual vs Expected:** React Three Fiber components should clean up WebGL textures and buffers upon unmount.
- **Impact:** Gradual GPU memory accumulation over prolonged operational shifts.
- **Risk:** Tab crash or WebGL context loss after extended browser usage.
- **Concrete Recommendation:** Implement explicit disposal hooks for Three.js geometry and material buffers.

---

### [TM-AG-020] Missing Rate Limiting on Public Endpoints
- **Severity:** P2 - MEDIUM
- **Category:** Security / API
- **Confidence:** 100% (Direct Code Inspection)
- **Location:** `backend/app/api/v1/planning_runs.py`
- **Evidence:** Endpoints accepting solver execution requests (`POST /api/v1/planning/runs`) lack rate limiting or per-IP throttling.
- **Actual vs Expected:** Heavy computation endpoints should be rate-limited (e.g. 5 requests per minute per IP).
- **Impact:** A client can trigger dozens of concurrent CP-SAT solving runs, exhausting server CPU threads.
- **Risk:** Denial of Service (DoS) on backend worker capacity.
- **Concrete Recommendation:** Implement `slowapi` or Redis-backed token bucket rate limiting on solver trigger endpoints.

---

### [TM-AG-021] Frontend Bundle Size and Dynamic Imports
- **Severity:** P3 - LOW
- **Category:** Frontend / Performance
- **Confidence:** 85% (Build Output Analysis)
- **Location:** `frontend/src/app/(workspace)/planning/page.tsx`
- **Evidence:** Three.js and heavy visualizer components are statically imported into the planning workspace bundle rather than lazily loaded via `next/dynamic`.
- **Actual vs Expected:** Heavy 3D canvas components should be dynamically imported with `ssr: false`.
- **Impact:** Initial page bundle size is larger than necessary, delaying first interactive render.
- **Risk:** Sluggish initial load on lower-spec railway workstation terminals.
- **Concrete Recommendation:** Wrap `Corridor3DVisualizer` in `next/dynamic` with skeleton fallback.

---

### [TM-AG-022] Missing Nonce / CSP Headers
- **Severity:** P2 - MEDIUM
- **Category:** Security / Headers
- **Confidence:** 95% (Configuration Inspection)
- **Location:** `frontend/next.config.ts`
- **Evidence:** `next.config.ts` lacks a strict Content Security Policy (CSP) header configuration.
- **Actual vs Expected:** Strict CSP preventing inline script execution and unauthorized WebSocket connections.
- **Impact:** Exposure to cross-site scripting (XSS) if user input is reflected unsanitized.
- **Risk:** Client-side token extraction.
- **Concrete Recommendation:** Add security headers (`Content-Security-Policy`, `X-Content-Type-Options`, `X-Frame-Options`) in `next.config.ts`.

---

### [TM-AG-023] Lack of Task Preemption in Solver Formulation
- **Severity:** P3 - LOW
- **Category:** Optimization / Domain Modeling
- **Confidence:** 90% (Domain Modeling Analysis)
- **Location:** `backend/app/domain/solver/cp_sat_model.py`
- **Evidence:** All maintenance tasks are modeled as non-preemptive continuous intervals. In actual railway operations, certain ballast screening or track renewal tasks can be split across multiple night curfews.
- **Actual vs Expected:** Long-duration tasks should optionally allow segmented scheduling across discrete time windows.
- **Impact:** Long tasks (>8 hours) become unscheduled if available curfews are only 4 hours.
- **Risk:** Suboptimal utilization of fragmented track possession windows.
- **Concrete Recommendation:** Support task chunking / segmentable work orders in future solver milestones.

---

### [TM-AG-024] Missing Pydantic Strict Mode on Timetable Time Inputs
- **Severity:** P3 - LOW
- **Category:** API / Data Validation
- **Confidence:** 90% (Schema Inspection)
- **Location:** `backend/app/schemas/domain_schemas.py`
- **Evidence:** String-based time intervals allow loose parsing without enforcing exact ISO-8601 UTC regex at the Pydantic boundary.
- **Actual vs Expected:** Strict `datetime` validation with mandatory timezone offsets.
- **Impact:** Potential time parsing mismatches between client local time and server UTC.
- **Risk:** Schedule boundary offset errors.
- **Concrete Recommendation:** Enforce `datetime.datetime` with `pydantic.Field` timezone constraints.

---

### [TM-AG-025] Copilot Model Parameter Hardcoding
- **Severity:** P3 - LOW
- **Category:** AI / Architecture
- **Confidence:** 90% (Code Inspection)
- **Location:** `backend/app/services/copilot/engine.py`
- **Evidence:** Copilot prompt generation and model parameters are hardcoded within the service logic rather than configurable via environment variables.
- **Actual vs Expected:** LLM provider, model name, temperature, and timeout should be injected via `AppSettings`.
- **Impact:** Inability to hot-swap LLM models (e.g. Gemini 1.5 Pro vs Local Llama-3) without modifying code.
- **Risk:** Vendor lock-in and deployment rigidity.
- **Concrete Recommendation:** Expose `COPILOT_MODEL_NAME` and `COPILOT_TEMPERATURE` in `backend/app/config.py`.

---

## 6. Security Audit

```
┌─────────────────────────────────────────────────────────────┐
│                    SECURITY THREAT MODEL                    │
├───────────────────────┬─────────────────────────────────────┤
│ Threat Vector         │ Risk Rating & Existing Mitigation   │
├───────────────────────┼─────────────────────────────────────┤
│ Credential Exposure   │ CRITICAL (P0): Tokens in JS bundle  │
│ Privilege Escalation  │ CRITICAL (P0): Default Admin Role   │
│ Denial of Service     │ HIGH (P1): No solver rate limits    │
│ CSRF / Session Hijack │ HIGH (P1): Bearer token in local JS │
│ Cross-Origin Attacks  │ HIGH (P1): Missing CORS config      │
│ Prompt Injection      │ LOW: Copilot is strictly read-only  │
└───────────────────────┴─────────────────────────────────────┘
```

- **Threat Model Analysis:** The primary attack surface is the complete lack of credential isolation. The hardcoded token `admin-token-2026` grants unrestricted access to all endpoints, including plan approval, deletion, and solver triggers.
- **Secret Scanning:** Scanned repository for live API keys or private certificates. No live AWS, Azure, or Google Cloud API private keys were discovered in git history; all credentials present are synthetic demo constants.
- **Dependency Vulnerabilities:** `pip-audit` and `npm audit` reveal standard upstream dependencies without immediate zero-day RCE exploits, but client bundle token baking violates fundamental OWASP Top 10 guidelines (A01: Broken Access Control, A07: Identification and Authentication Failures).

---

## 7. Authentication & Authorization (RBAC) Audit

- **Role Definitions:**
  `UserRole.VIEWER`, `UserRole.PLANNER`, `UserRole.APPROVER`, `UserRole.ADMIN`.
- **Role Permissions Matrix:**
  - `VIEWER`: Read-only access to scenarios, stations, and completed plans.
  - `PLANNER`: Trigger solver runs, create plan versions, submit comments.
  - `APPROVER`: Formally approve or reject plan versions.
  - `ADMIN`: Wildcard `*` permissions.
- **RBAC Flaws:**
  1. The backend middleware (`backend/app/core/auth.py`) checks credentials against an in-memory dictionary.
  2. The frontend client unconditionally presents the `admin` token, rendering the RBAC hierarchy inert in practice during browser sessions.
  3. No role validation exists for WebSocket or SSE connections.

---

## 8. Governance & Approval Workflow Audit

- **The Invariant:** `COMPLETED ≠ APPROVED`.
- **Backend Adherence:** **100% Compliant**.
  In `backend/app/services/plan_governance_service.py`, creating a plan version from a completed run sets status to `DRAFT`. To transition to `APPROVED`, the plan must pass independent validation, match its input fingerprint, and be approved by an authorized user (`UserRole.APPROVER` or `UserRole.ADMIN`).
- **Frontend Adherence:** **CRITICAL COMPROMISE (TM-AG-004)**.
  In `frontend/src/app/(workspace)/audit/page.tsx`, the optimistic catch block overrides backend rejections and sets the plan to `APPROVED` locally. This undermines the core architectural invariant during UI operation.

---

## 9. Data Integrity & Silent Fallback Audit

- **Fallback Table Analysis:**
  | Endpoint | Real Endpoint | Catch Fallback Object | State Presented to User |
  |---|---|---|---|
  | `POST /api/v1/planning/optimize` | `client.ts:350` | `DEMO_SCHEDULE_RESULT` | `status: "OPTIMAL"`, 30 tasks scheduled |
  | `POST /api/v1/planning/validate` | `client.ts:380` | `DEMO_VALIDATION_RESULT` | `status: "VALID"`, `is_approvable: true` |
  | `GET /api/v1/planning/versions` | `client.ts:400` | `[DEMO_PLAN_VERSION]` | Synthetic approved version list |
- **Impact Assessment:** In high-consequence railway planning, silent stubs create the dangerous illusion of a functioning solver during backend infrastructure failures.

---

## 10. Backend Architecture & Code Quality Audit

- **Structure:** Clean hexagonal / layered architecture: `api` → `services` → `repositories` → `models` / `domain`.
- **Separation of Concerns:** Excellent separation between CP-SAT domain models and FastAPI HTTP transport.
- **Error Handling:** Centralized exception handlers in `backend/app/main.py` convert domain exceptions into structured JSON responses (`detail`, `code`, `timestamp`).
- **Async Hygiene:** Async SQLAlchemy sessions are used throughout repositories. No blocking I/O calls were observed in async route handlers.

---

## 11. Optimization & Scheduling Algorithms Audit

- **Solver Engine:** Google OR-Tools CP-SAT (v9.15.6755).
- **Formulation Rigor:**
  - Tasks modeled as `NewIntervalVar(start, duration, end, name)`.
  - Non-overlapping track possessions enforced via `AddNoOverlap`.
  - Resource exclusivity modeled via cumulative / interval constraints.
  - Precedence constraints: `task_b.start >= task_a.end`.
  - Objective function: Multi-objective weighted sum maximizing high-priority scheduled tasks while minimizing train buffer proximity and delays.
- **Baseline Algorithms:**
  - **FCFS:** Greedily assigns intervals based on arrival order.
  - **Priority Greedy:** Sorts work orders by computed priority score before placement.
- **Empirical Performance:** On synthetic scenario `SCN-DEMO-001` (50 trains, 30 tasks), CP-SAT achieves optimal solutions in 0.12–0.28 seconds.

---

## 12. Validation & Independence Audit

- **Independent Validator:** `backend/app/services/validation/validator.py`.
- **Independence Verification:**
  - Operates directly on the raw `PlanningSnapshot`.
  - Does NOT reuse solver variables or solver memory.
  - Performs independent geometric overlap checks (`start < other.end and end > other.start`).
  - Verifies exact boundary conditions (half-open intervals `[start, end)` do not conflict at `end == next.start`).
  - Verifies train movement time-distance conflicts independently.
- **Monkeypatch Immunity:** Verified by unit test `test_22_validator_independence_monkeypatch_proof` in `tests/unit/test_phase7_validator.py`.

---

## 13. Diagnostics & Relaxation Audit

- **Diagnostics Service:** `backend/app/services/validation/diagnostics.py`.
- **Capabilities:**
  - Identifies root cause of unscheduled tasks (Train Conflict, Resource Starvation, Dependency Violation).
  - Performs iterative constraint relaxation analysis to determine minimum changes required to make an infeasible task schedulable.
  - Formally marks relaxed proposals as `HYPOTHETICAL` and `NON_APPROVABLE`.

---

## 14. API Contract & Schemas Audit

- **Schema Framework:** Pydantic v2.
- **Contract Quality:** Strongly typed request/response models for all operational endpoints (`OperationalScenarioRead`, `PlanningRunCreateRequest`, `PlanVersionApproveRequest`).
- **Pagination & Filtering:** List endpoints (`/runs`, `/versions`, `/tasks`) implement limit/offset pagination and status filtering.

---

## 15. Database & Persistence Audit

- **Engine:** PostgreSQL with `asyncpg` driver.
- **Alembic Migrations:**
  - `001_phase1_topology.py`: Stations, sections, corridors, train movements.
  - `002_phase2_operations.py`: Operational scenarios, work orders, maintenance tasks, resources.
  - `003_phase8_planning_runs.py`: Planning runs, run events, execution telemetry.
  - `004_phase9_governance.py`: Plan versions, plan approvals, audit comments.
- **Foreign Key Integrity:** Enforced across all entities with cascading rules where appropriate.
- **Indexing Gaps:** Identified missing composite index on `planning_runs(scenario_id, created_at DESC)` (TM-AG-015).

---

## 16. Worker, Concurrency & Async Audit

- **Worker Mechanism:** In-process asynchronous task queue (`backend/app/services/planning_worker.py`).
- **Atomic Job Claiming:** Uses `SELECT ... FOR UPDATE SKIP LOCKED` in `planning_run_repo.py` to prevent duplicate worker execution.
- **Defects:** Cancellation state transition lockup documented in TM-AG-006.

---

## 17. Frontend Architecture & Code Quality Audit

- **Framework:** Next.js 16.3.8 App Router with React 19.
- **Component Organization:** Cohesive domain components (`src/components/corridor`, `src/components/governance`, `src/components/workspace`).
- **State Management:** React Context (`PlanningContext`) provides centralized state for active scenario, selected run, active plan version, and telemetry.
- **Lint / Build Status:** `npm run build` completed successfully in 10.6 seconds with zero TypeScript errors.

---

## 18. UI/UX & Operational Workstation Audit

- **Visual Design:** Sophisticated dark railway operational console (black/graphite surfaces `#0d1117`, slate borders, electric blue accents `#2563eb`, amber warning highlights `#d97706`).
- **Progressive Disclosure:** Modal panels and tabbed mode surfaces (Overview, Gantt, Spatial, Diagnostics, Audit) prevent visual congestion.
- **Defects:** Hardcoded synthetic officer signatures in audit logs and native browser dialogs (TM-AG-007, TM-AG-010).

---

## 19. Responsive Design Audit

- **Layout Structure:** Grid and flex container layouts adapt from wide desktop monitors (1920×1080) down to tablet displays (1024×768).
- **Responsive Deficiencies:** Minor SSR hydration mismatch risk due to client-side `window.innerWidth` evaluation in `planning/page.tsx` (TM-AG-013).

---

## 20. Accessibility (A11Y) Audit

- **Color Contrast:** High contrast text on dark backgrounds exceeds WCAG 2.1 AA standards (contrast ratio > 7:1 for primary text).
- **Keyboard Navigation:** Modals support Escape key dismissal and focus trapping.
- **Areas for Improvement:** Visual 3D corridor canvas requires expanded screen-reader alternative text descriptions.

---

## 21. Design System Audit

- **Typography:** Monospace data displays (`font-mono`) paired with clean sans-serif interface typography (`Inter`).
- **Color Palette:** Strictly controlled monochrome surfaces with purposeful semantic accents (Red = Conflict/Infeasible, Emerald = Valid/Scheduled, Amber = Diagnostic Warning, Blue = Active Selection). No frivolous gradients or generic AI glow effects.

---

## 22. Copilot (Read-Only AI) Audit

- **Core Rule Adherence:** **100% READ-ONLY**.
- **Tool Architecture:**
  `backend/app/services/copilot/tools.py` implements 5 strictly read-only inspection tools:
  - `get_plan_summary`
  - `get_task_decision`
  - `get_rule_provenance`
  - `get_diagnostics`
  - `list_unscheduled_tasks`
- **Mutation Rejection:** Explicitly refuses any mutation request (approve, schedule, cancel, edit) with standard deterministic refusal messages.
- **Hallucination Safeguards:** If an entity ID does not exist in the snapshot, the Copilot engine returns explicit uncertainty rather than inventing operational facts.

---

## 23. Railway Domain & Regulatory Compliance Audit

- **Rule Provenance:**
  Every domain constraint is categorized as `VERIFIED_SOURCE`, `ASSUMPTION`, or `DEMO_ONLY`.
- **Regulatory Reality:**
  The platform currently encodes synthetic approximations of Indian Railways operating manual curfews (e.g. 4-hour night possession blocks, 15-minute train safety separation). None of these rules are currently connected to official CRIS rulebooks.
- **Safety Boundary Disclaimer:** The application prominently displays synthetic data disclaimers across all screens.

---

## 24. Performance & Resource Audit

- **Solver CPU:** 0.12s–0.28s execution time for 30 tasks / 50 trains under CP-SAT.
- **Database Footprint:** Lightweight (<20MB for synthetic scenario data).
- **Frontend Bundle:** Turbopack builds in 10.6s; production bundle size is well within acceptable web performance thresholds.

---

## 25. Testing & Verification Audit

- **Test Suite Metrics:**
  - 203 tests collected across unit and integration suites.
  - 129 core unit tests pass cleanly in under 15 seconds.
  - 3 unit tests in `test_phase13_copilot.py` fail due to unmocked database session dependencies (TM-AG-008).
- **Coverage Strengths:** Domain models, CP-SAT mathematical solver, baseline algorithms, validator independence, temporal interval logic.
- **Coverage Gaps:** Missing End-to-End browser tests (Playwright) and API rate-limiting tests.

---

## 26. Build, Packaging & Toolchain Audit

- **Frontend Build:** Next.js 16.3.8 Turbopack passes without warnings.
- **Backend Lint:** Clean Python code formatting with consistent typing.
- **Containerization:** Dockerfile and Docker Compose configurations exist for staging container orchestration.

---

## 27. Documentation Audit

- **Documentation Assets:**
  - `PRD.md`: Comprehensive product requirements and boundary definitions.
  - `ARCHITECTURE.md`: High-level system architecture and data flows.
  - `DATA_AND_DOMAIN_MODEL.md`: Domain schema documentation.
  - `DESIGN_SYSTEM.md`: UI design tokens and component standards.
  - `AGENTS.md`: Strict agent guidelines and operational invariants.
- **Accuracy:** Documentation accurately reflects system architecture, with clear notes on prototype boundaries.

---

## 28. Fake / Fabricated / Hardcoded Data Inventory

| Item | Location | Nature of Data | Risk / Classification |
|---|---|---|---|
| Corridor Stations (ALD, CNB, FTP, MZP, SUB) | `scripts/seed_operational_data.py` | Synthetic Indian Railways Corridor | `DEMO_ONLY` |
| Train Movements (50 trains) | `scripts/seed_operational_data.py` | Seeded synthetic passenger/freight timetables | `DEMO_ONLY` |
| Work Orders & Maintenance Tasks (30 tasks) | `scripts/seed_operational_data.py` | Synthetic track renewal / tamping requests | `DEMO_ONLY` |
| Auth Tokens (`admin-token-2026`) | `backend/app/core/auth.py` | Plaintext hardcoded credentials | `SECURITY_RISK` |
| Audit Hashes (`INITIAL_VERSIONS`) | `frontend/src/app/(workspace)/audit/page.tsx` | Hardcoded mock version history | `DEMO_ONLY` |
| Fallback Schedule (`DEMO_SCHEDULE_RESULT`) | `frontend/src/lib/api/client.ts` | Static optimizer mock result | `INTEGRITY_RISK` |

---

## 29. Feature Matrix: Promised vs Actual

| Promised Feature | PRD Specification | Actual Implementation State | Verdict |
|---|---|---|---|
| CP-SAT Optimization | Phase 6 | Implemented in `cp_sat_model.py` & verified | **REAL / FUNCTIONAL** |
| Independent Validator | Phase 7 | Implemented in `validator.py`, verified independent | **REAL / FUNCTIONAL** |
| Diagnostics & Relaxation | Phase 7 | Implemented in `diagnostics.py` | **REAL / FUNCTIONAL** |
| Read-Only AI Copilot | Phase 13 | Implemented with read-only tools & refusal | **REAL / FUNCTIONAL** |
| Plan Version Governance | Phase 9 | Implemented in backend with SHA-256 fingerprinting | **REAL (Backend) / FLAWED (Frontend catch)** |
| 3D Corridor Visualizer | Phase 12 | Implemented in Three.js / React Three Fiber | **REAL / VISUAL DEMO** |
| CRIS / FOIS Timetable Feed | External Integration | Not implemented; synthetic seed generator used | **DEMO / SYNTHETIC** |
| Multi-User Database Auth | Core Security | Hardcoded static token strings | **INCOMPLETE / PROTOTYPE** |
| Secondary Modules (Work Orders, Resources) | Sidebar Navigation | Unimplemented (404 routes) | **STUB / PHANTOM** |

---

## 30. Trust Boundary Audit

```
┌─────────────────────────────────────────────────────────────┐
│                    TRUST BOUNDARY AUDIT                     │
├─────────────────────────────────────────────────────────────┤
│ 1. Browser Client → Backend API:                             │
│    FAIL: Insecure default bearer token shipped in bundle.   │
│                                                             │
│ 2. Backend API → CP-SAT Solver:                             │
│    PASS: Clean Pydantic data snapshot serialization.        │
│                                                             │
│ 3. Solver Output → Plan Governance:                         │
│    PASS: Mandatory Independent Validator gate in backend.   │
│                                                             │
│ 4. AI Copilot → Decision Engine:                            │
│    PASS: Strictly read-only tools; write actions refused.   │
│                                                             │
│ 5. Frontend Audit UI → State Persistence:                   │
│    FAIL: Catch block fabricates approval on API error.      │
└─────────────────────────────────────────────────────────────┘
```

---

## 31. Release Readiness Evaluation

- **Prototype / Hackathon Presentation:** **GREEN (READY)**.
  The visual workstation, 3D corridor visualizer, CP-SAT solver, diagnostics, and read-only Copilot deliver an exceptional and compelling demonstration of automated railway possession planning.
- **Enterprise Pilot / Staging Deployment:** **YELLOW (CONDITIONAL)**.
  Requires immediate elimination of hardcoded auth tokens, removal of frontend silent mock fallbacks, and resolution of CORS configuration.
- **Live Railway Operations (Production):** **RED (NOT READY)**.
  Under no circumstances should this codebase be connected to operational railway systems without complete re-architecture of security, live CRIS integration, and automated failover clustering.

---

## 32. Do-Not-Ship List

1. **DO NOT SHIP** `frontend/src/lib/api/client.ts` with lines 18–20 containing `admin-token-2026`.
2. **DO NOT SHIP** `frontend/src/app/(workspace)/audit/page.tsx` with optimistic catch block approval logic.
3. **DO NOT SHIP** `backend/app/core/auth.py` with hardcoded `KNOWN_CREDENTIALS` dictionary.
4. **DO NOT SHIP** without adding `CORSMiddleware` in `backend/app/main.py`.
5. **DO NOT SHIP** without removing silent fallback mocks (`DEMO_SCHEDULE_RESULT`, `DEMO_VALIDATION_RESULT`) from `client.ts`.

---

## 33. Prioritized Remediation Plan

### Phase A: Security & Authentication Hardening (Days 1–3)
- Implement proper PostgreSQL user model with argon2id password hashing.
- Issue short-lived signed JWT bearer tokens with rotating RSA/ECDSA keys.
- Remove hardcoded fallback tokens from frontend client bundle.
- Configure `CORSMiddleware` with strict allowed origin lists.

### Phase B: Data Integrity & Error Propagation (Days 4–5)
- Purge all silent fallback mock catch blocks from `frontend/src/lib/api/client.ts`.
- Eliminate optimistic catch block mutations in `audit/page.tsx`.
- Implement global error notification banners in UI for failed solver or validation runs.

### Phase C: Concurrency & Worker Robustness (Days 6–7)
- Fix planning run cancellation state machine in `planning_worker.py` and `planning_run_repo.py`.
- Add periodic cooperative cancellation checks during CP-SAT solving loops.

### Phase D: Testing & CI/CD Isolation (Days 8–9)
- Mock `AsyncSession` database calls in `tests/unit/test_phase13_copilot.py`.
- Add end-to-end integration tests verifying failure propagation.

### Phase E: Information Architecture & Navigation Polish (Days 10–11)
- Add "Phase 15 Concept" badges or dedicated detail views for secondary sidebar navigation links.
- Replace native browser `alert()` calls with in-app toast notifications.

### Phase F: Railway Domain & Integration Pipeline (Days 12–15)
- Create ingestion parser for official CRIS / COA timetable formats.
- Implement division-level spatial sectorization for CP-SAT solver scalability.
