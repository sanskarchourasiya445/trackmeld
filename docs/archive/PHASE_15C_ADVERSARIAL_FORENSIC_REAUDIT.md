# Phase 15C: Adversarial Forensic Re-Audit Report

**Project:** TrackMeld Railway Possession Planning & Decision Support Platform  
**Audit Date:** 2026-10-03  
**Auditor / Forensic Role:** Lead Adversarial Security & Domain Architecture Auditor  
**Audit Mode:** READ-ONLY (No code, test, migration, or configuration modifications)  
**Git Baseline Under Audit:** `d96f0ab` (`main`)  
**Database Cluster Under Test:** PostgreSQL 18.x on port 5433 (Alembic Migration HEAD `9c2d1e4f7a01`)  

---

## 1. Executive Summary & Audit Baseline

### Forensic Verdict: **QUALIFIED PASS — CORE SAFETY INVARIANTS UPHELD, KEY ARCHITECTURAL LIMITATIONS & FRONTEND AUTH GAPS IDENTIFIED**

This adversarial audit independently scrutinized the implementation, state transitions, authentication barriers, concurrency controls, and test suites established in Phase 15A and Phase 15B.

### Summary of Disproved or Qualified Claims:
1. **Frontend Authentication UI Missing:** While Phase 15A successfully purged hardcoded administrative tokens (`admin-token-2026`) from the browser bundle and Phase 15B verified backend fail-closed authentication in production, **no UI mechanism exists in the frontend for an operator or planner to authenticate or supply an authorization token**. In production, all frontend actions fail with `401 Unauthorized`; in development, actions requiring `write:operational` or `plan:approve` fail with `403 Forbidden` unless an operator manually executes JavaScript in the browser console (`sessionStorage.setItem('trackmeld_auth_token', '...')`).
2. **"Cryptographic Schedule Fingerprint" Scope Overstated:** The schedule fingerprint is a SHA-256 digest of scheduled task intervals, affected sections, and assigned equipment. However, **modifications to `crew_id`, `assigned_track`, `priority_score`, unscheduled task diagnostics, and overall objective metrics do NOT change the fingerprint**. Calling the schedule "cryptographically immutable" overstates what is actually hashed.
3. **Cancellation Race Verification Incomplete for In-Flight Solvers:** The cooperative cancellation checkpoints reliably abort execution *before* optimization and *before* validation. However, **an active CP-SAT optimization running inside the synchronous C++ thread pool cannot be cancelled mid-solve**; the worker must wait for the solver time-out or completion before checking cancellation flags.
4. **Rate Limiting Scope Restricted to a Single Route:** The in-memory sliding-window rate limiter is applied **strictly to `POST /api/v1/planning-runs`**. Synchronous compute-intensive endpoints (`/planning/solve`, `/planning/validate`, `/planning/diagnostics`, and `/copilot/explain`) are completely unthrottled. Furthermore, the limiter uses `request.client.host` directly, which collides all clients behind a reverse proxy.
5. **Separation of Duties Weakness:** A single authenticated identity with administrative privileges (`role=ADMIN`) can create a plan candidate, start the review, and formally approve the plan. The backend does not enforce the four-eyes railway principle (`creator != approver`).
6. **Synthetic Demo Data Still Rendered on Offline Startup:** While operational errors no longer mutate state to `APPROVED`, opening the Planning Workspace with the backend offline initializes the view with `DEMO_SCHEDULE_RESULT` and `DEMO_VALIDATION_RESULT`, visually presenting a certified "VALID" schedule (albeit badged as synthetic in the audit view).

---

## 2. Authentication Adversarial Review

### Findings:
1. **Production Mode Fail-Closed (`PROVEN`):**
   - In `backend/app/core/auth.py` lines 156–169, when `settings.is_production == True`, any request lacking an Authorization Bearer token or API key raises `HTTPException(401, detail={"error": {"code": "AUTHENTICATION_REQUIRED", ...}})`.
   - `DEMO_CREDENTIALS` (`admin-token-2026`, etc.) are purged from the active credentials registry when `is_production == True`.
2. **Missing Frontend Login / Token Injection Interface (`DEFECT / USABILITY GAP`):**
   - `frontend/src/lib/api/client.ts` exports `getAuthToken()` reading `sessionStorage` and `localStorage`.
   - A global grep across `frontend/src` for `login`, `setAuthToken`, and `trackmeld_auth_token` confirmed that **zero UI forms, inputs, modals, or profile menus call `setAuthToken()`**.
   - As a consequence, normal web users are perpetually unauthenticated. In development, they are mapped to `DEFAULT_DEMO_USER` (`role=VIEWER`), which cannot approve or submit planning runs. In production, every request is rejected with HTTP 401.
3. **Token Impersonation & Identity Authority (`PROTOTYPE LIMITATION`):**
   - The token model uses static bearer strings (`admin-token-2026`, `approver-token-2026`, or environment tokens like `AUTH_APPROVER_TOKEN`).
   - All users possessing `approver-token-2026` share the identical identity: `user_id="USR-APPR-01", username="divisional_operations_manager"`. There is no individual identity attribution, password verification, or MFA.
4. **Authoritative Endpoint RBAC (`PROVEN`):**
   - Governance endpoints in `backend/app/api/v1/plan_versions.py` strictly require explicit permissions:
     - `POST /plan-versions`: `write:operational`
     - `POST /plan-versions/{id}/review/start`: `plan:review`
     - `POST /plan-versions/{id}/review/comment`: `plan:review`
     - `POST /plan-versions/{id}/approve`: `plan:approve`
     - `POST /plan-versions/{id}/reject`: `plan:reject`
   - Tested empirically: when `DEFAULT_DEMO_USER` attempts to approve or create versions, the backend returns `403 Forbidden`.

---

## 3. Data Fabrication Adversarial Review

### Findings:
1. **Error-to-Approval Conversion Defeated (`PROVEN`):**
   - In `frontend/src/app/(workspace)/planning/page.tsx` (lines 224–228) and `audit/page.tsx` (lines 232–238), catch blocks for `approvePlanVersion` explicitly discard local state mutations and display:
     `ACTION NOT COMPLETED: The backend did not confirm this governance action... No local state transition has been applied.`
   - No network failure or HTTP 4xx/5xx error can trick the frontend into displaying an unapproved plan as `APPROVED`.
2. **Startup Static Demo State (`PARTIALLY CONTRADICTED CLAIM`):**
   - In `frontend/src/app/(workspace)/planning/page.tsx` lines 78–86:
     ```typescript
     const [scheduleResult, setScheduleResult] = useState<ScheduleResult | null>(DEMO_SCHEDULE_RESULT);
     const [validationResult, setValidationResult] = useState<ScheduleValidationResult | null>(DEMO_VALIDATION_RESULT);
     const [planVersion, setPlanVersion] = useState<PlanVersion | null>(DEMO_PLAN_VERSION);
     ```
   - When the page is mounted while the backend is offline, the initial render displays `DEMO_VALIDATION_RESULT` with status `VALID`, `valid: true`, `is_approvable: true`, and `approval_gate_message: "Approval ELIGIBLE: Schedule independently certified 100% valid under all modeled hard constraints."`
   - While this does not trigger an actual backend approval, **it violates strict zero-fabrication presentation when the backend is offline**. The UI should start in a clean uncomputed/loading state (`null`) and render an explicit error banner if the backend is unreachable.

---

## 4. Governance State Machine Analysis

### State Transition Matrix (Derived from `backend/app/repositories/plan_version_repo.py`):

| Current State | Permitted Next States | Terminal? | Code Enforcement |
|---|---|:---:|---|
| `PENDING_REVIEW` | `UNDER_REVIEW`, `APPROVED`, `REJECTED` | No | `LEGAL_PLAN_TRANSITIONS` |
| `UNDER_REVIEW` | `APPROVED`, `REJECTED`, `PENDING_REVIEW` | No | `LEGAL_PLAN_TRANSITIONS` |
| `APPROVED` | `SUPERSEDED` | Yes (operational) | `LEGAL_PLAN_TRANSITIONS` + Row Lock |
| `REJECTED` | $\emptyset$ (None) | Yes | `LEGAL_PLAN_TRANSITIONS` |
| `SUPERSEDED` | $\emptyset$ (None) | Yes | `LEGAL_PLAN_TRANSITIONS` |

### Key State Transition Findings:
1. **`APPROVED -> REJECTED`**: **IMPOSSIBLE**. Blocked by `LEGAL_PLAN_TRANSITIONS` and `PlanVersionImmutableError`.
2. **`REJECTED -> APPROVED`**: **IMPOSSIBLE**. Blocked by `LEGAL_PLAN_TRANSITIONS` (`allowed = set()`).
3. **`SUPERSEDED -> APPROVED`**: **IMPOSSIBLE**. Blocked by `LEGAL_PLAN_TRANSITIONS`.
4. **`APPROVED -> APPROVED`**: **IMPOSSIBLE**. Explicitly blocked by `PlanGovernanceService.approve_plan` line 278 (`raise PlanVersionImmutableError`).
5. **`PENDING_REVIEW -> APPROVED` (Direct Approval)**: **PERMITTED BY DESIGN**. `UNDER_REVIEW` is optional; an authorized approver can directly approve a `PENDING_REVIEW` plan version if all preconditions pass.
6. **Terminology Discrepancy (`DRAFT` vs `PENDING_REVIEW`):**
   - The backend model (`PlanVersionStatus`) defines `PENDING_REVIEW`, `UNDER_REVIEW`, `APPROVED`, `REJECTED`, `SUPERSEDED`.
   - The status `"DRAFT"` **does not exist in the backend database schema**.
   - Frontends and verification reports use `"DRAFT"` colloquially to refer to `PENDING_REVIEW`.

---

## 5. Separation of Duties Analysis

### Finding: **GOVERNANCE WEAKNESS (Absence of Four-Eyes Principle)**
- File: `backend/app/services/plan_governance_service.py` line 263 (`approve_plan`).
- **Observed Behavior:** The approval method validates technical validation status, error count, and cryptographic hash matches. However, it **does not check whether `actor.username == plan.created_by` or `actor.user_id == plan.created_by`**.
- An operator with `role=ADMIN` possesses `*` permissions and can:
  1. Instantiate a plan candidate (`created_by="chief_operations_admin"`).
  2. Approve the plan candidate (`approved_by="chief_operations_admin"`).
- **Classification:** Governance weakness in prototype. In formal railway operations (Ministry of Railways / CRIS), the person who authored/requested the possession window must never be the same officer who signs the operational approval.

---

## 6. Approval Revalidation & TOCTOU Audit

### Finding: **STRONG AUTHORITATIVE PERSISTENCE, NO TOCTOU VULNERABILITY**
- Trace: `POST /plan-versions/{id}/approve` $\rightarrow$ `PlanGovernanceService.approve_plan()`.
- **Database Row Lock:** `await self.plan_repo.get_by_id_for_update(plan_version_id)` executes `SELECT ... FOR UPDATE` on PostgreSQL.
- **Revalidation of Persisted Data:**
  - `approve_plan()` re-queries the source run: `run = await self.run_repo.get_by_run_id(plan.planning_run_id)`.
  - Re-checks: `run.validation_fingerprint == plan.schedule_identity`.
  - Re-checks: `run.snapshot_hash == plan.snapshot_hash`.
  - Re-checks: `run.input_hash == plan.input_hash`.
  - Re-checks: `plan.validation_status == "VALID"`.
  - Re-checks: `plan.is_approvable is True`.
  - Re-checks: `findings_summary.get("error_count", 0) == 0`.
- **Absence of Mutation Routes:** There are zero `PUT`, `PATCH`, or `DELETE` endpoints for `PlanVersionModel` in FastAPI. Once created, schedule intervals cannot be modified in the database.
- **Verdict:** Authoritative data is revalidated under lock. No TOCTOU window exists.

---

## 7. Audit Integrity & Database Schema Analysis

### Finding: **APPLICATION-LEVEL APPEND-ONLY, NOT CRYPTOGRAPHICALLY CHAINED**
- Model: `GovernanceAuditEventModel` in `backend/app/db/models/plan_version.py`.
- **Database Enforcement vs Application Convention:**
  - The application provides no update or delete routes for audit records.
  - However, in PostgreSQL, `governance_audit_events` has standard primary keys and indexes with **no `BEFORE UPDATE OR DELETE` triggers or row-level security (RLS) rules** preventing database administrators or compromised SQL sessions from updating or deleting rows.
  - There is **no Foreign Key** linking `entity_id` to `plan_versions.plan_version_id` (it is a polymorphic string column).
- **Absence of Hash Chaining:**
  - Audit records store `schedule_identity`, `snapshot_hash`, and `input_hash`.
  - However, records **do not store `parent_event_hash` or Merkle tree roots**. Consecutive audit events are not cryptographically chained.
- **Verdict:** This is an application-enforced audit log with cryptographic evidence references, not a WORM or cryptographically tamper-evident blockchain.

---

## 8. Worker Concurrency & Edge-Case Failure Modes

### Concurrency Matrix:

| Concurrency Scenario | Code Handling | Status / Risk |
|---|---|---|
| **Multi-Worker Claim** | `SELECT ... FOR UPDATE SKIP LOCKED` | **PROVEN BY TEST**. Zero double-claims observed. |
| **Worker Crash After Claim** | `find_stale_runs()` reaper detects `heartbeat_at < cutoff` and marks `TIMED_OUT` | **PROVEN BY CODE**. Background sweep marks expired jobs. |
| **Stale Worker Revival** | Waking worker attempts `mark_validating()` $\rightarrow$ `IllegalStateTransitionError` | **PROVEN BY CODE**. State machine prevents completion. |
| **State Mutation on Revival** | `mark_failed()` overwrites `TIMED_OUT` to `FAILED` | **MINOR ANOMALY**. Line 228 allows `TIMED_OUT` $\rightarrow$ `FAILED`. |
| **Cancellation Pre-Solve** | Cooperative check at Line 146 marks `CANCELLED` | **PROVEN BY TEST**. |
| **Cancellation Pre-Validation**| Cooperative check at Line 177 marks `CANCELLED` | **PROVEN BY TEST**. |
| **Cancellation During CP-SAT Solve**| Solver thread executes `solver.Solve(model)` synchronously in thread pool | **UNTESTED / LIMITATION**. C++ solver cannot be cancelled mid-flight. |

---

## 9. Rate Limiting Analysis & Bypass Vectors

### Finding: **RESTRICTED SCOPE & PROXY BYPASS VECTORS**
- File: `backend/app/core/rate_limit.py`.
- **Scope Limitation:** Only `POST /api/v1/planning-runs` includes `Depends(enforce_planning_rate_limit)`. Other expensive routes (`/planning/solve`, `/planning/validate`, `/copilot/explain`) have **zero rate limiting**.
- **Reverse Proxy Colocation:**
  - Line 59: `client_ip = request.client.host if request.client else "unknown"`.
  - Does not inspect `X-Forwarded-For` or `CF-Connecting-IP`.
  - In a standard production deployment behind Nginx, AWS ALB, or Cloudflare, all incoming requests share the reverse proxy's internal IP (e.g. `10.0.0.1`).
  - Consequently, **all unauthenticated or identically-tokened clients share a single 60 req/min quota**, causing denial of service for legitimate users.
- **Process Isolation:** The sliding window is stored in `self._history` inside Python memory. In a multi-worker setup (`uvicorn --workers 4`), rate limits are partitioned across processes and not synchronized.

---

## 10. CORS & Web Security Header Audit

### Finding: **CORS SECURE, BROWSER SECURITY HEADERS MISSING**
- File: `backend/app/main.py`.
- **CORS Configuration:**
  - `allow_origins=settings.cors_allowed_origins` (defaults to `http://localhost:3000,http://127.0.0.1:3000`).
  - In production (`is_production=True`), wildcards (`*`) raise an explicit `ValueError`.
  - `allow_credentials=True`.
- **Missing Browser Security Headers:**
  - `Content-Security-Policy` (CSP): **MISSING**.
  - `X-Frame-Options` (Clickjacking): **MISSING**.
  - `X-Content-Type-Options: nosniff`: **MISSING**.
  - `Strict-Transport-Security` (HSTS): **MISSING**.
  - `Referrer-Policy`: **MISSING**.

---

## 11. Frontend Security & Token Storage Threat Model

### Finding: **CLEAN BUNDLE, STORAGE EXPOSURE VECTOR**
- **Bundle Secrets:** Production build assets in `frontend/.next/static` contain **0 matches** for `admin-token-2026`, `approver-token-2026`, or other credentials.
- **Environment Variables:** Only `NEXT_PUBLIC_API_URL` is exposed in frontend build output.
- **Browser Storage Threat Model:**
  - `trackmeld_auth_token` is read from `sessionStorage` and `localStorage`.
  - Any successful Cross-Site Scripting (XSS) exploit on the domain can extract the operator token via `sessionStorage.getItem()`.
  - Enterprise mitigation: Migrate to server-managed `HttpOnly`, `Secure`, `SameSite=Strict` session cookies.

---

## 12. Copilot Safety & Hallucination Resistance

### Finding: **100% READ-ONLY, DETERMINISTIC GROUNDING**
- Files: `backend/app/services/copilot/tools.py`, `backend/app/services/copilot/engine.py`.
- **Mutation Impossibility:** Copilot exposes only 5 read-only queries (`get_task_decision`, `get_conflicts_for_task`, `get_run_summary`, `get_rule_provenance`, `get_plan_version_status`). There are zero database `add()`, `commit()`, `delete()`, or state transition calls anywhere in the copilot package.
- **Hallucination Resistance:**
  - `CopilotEngine` queries live database models.
  - When a requested entity (run, task, rule, plan version) does not exist, it constructs an explicit `EvidenceItem` of type `UNCERTAINTY` and states: *"Plan version ... was not found... The Copilot cannot invent hypothetical or fabricated plan versions."*
  - The copilot cannot fabricate train movements or approve plans.

---

## 13. Independent Validator Architectural Independence

### Finding: **TRUE INDEPENDENCE (PROVEN)**
- File: `backend/app/services/validation/checks.py`.
- **Import Audit:**
  - Does NOT import `CompatibilityEngine`.
  - Does NOT import `FCFSScheduler`, `PriorityGreedyScheduler`, or `CPSATScheduler`.
  - Does NOT import OR-Tools CP-SAT.
- **Data Flow Audit:**
  - Receives only raw `PlanningSnapshot` and output `ScheduleResult`.
  - Independently reconstructs track headways, train conflicts, buffer windows, and resource capacities from scratch.
  - A solver claiming `OPTIMAL` with overlapping track possessions is immediately flagged as `INVALID` with hard `ERROR` findings.

---

## 14. Solver / Validator / Governance Boundary Trace

### Finding: **STRICTLY ENFORCED HUMAN APPROVAL GATEWAY**
- **Solver Step:** `PlanningWorker` computes schedule and saves to `planning_runs` with `status="COMPLETED"`. Zero `PlanVersion` records are created.
- **Plan Version Step:** An authorized human with `write:operational` calls `POST /plan-versions`. Creates `PlanVersion` with `status="PENDING_REVIEW"`.
- **Approval Step:** The **ONLY** line of code in the entire repository that transitions a plan version to `APPROVED` is line 356 of `backend/app/services/plan_governance_service.py` inside `approve_plan()`.
- **Trigger:** Only `POST /plan-versions/{id}/approve` with `plan:approve` permission can trigger this line.
- **Verdict:** No mathematical outcome (`OPTIMAL`, `FEASIBLE`, `VALID`, `APPROVABLE`) can bypass human approval.

---

## 15. Canonical Hash / Fingerprint Boundary Analysis

### Adversarial Question: *"What modifications to a schedule can occur without changing the fingerprint?"*

Inspection of `IndependentScheduleValidator.compute_schedule_identity()` reveals that the fingerprint payload consists of:
```python
{
    "snapshot_id": snapshot.snapshot_id,
    "scenario_id": snapshot.scenario_id,
    "scheduler_type": schedule.scheduler_type,
    "solver_status": schedule.status,
    "scheduled_tasks": [
        {
            "task_id": st.task_id,
            "start": st.interval.start,
            "end": st.interval.end,
            "pos_start": st.possession_interval.start,
            "pos_end": st.possession_interval.end,
            "sections": sorted(st.affected_sections),
            "resources": sorted(st.assigned_resources),
        }
    ]
}
```

### Schedule Fields NOT Protected by the Fingerprint:
1. **`crew_id`**: Reassigning a maintenance task to a different maintenance crew does not alter the fingerprint.
2. **`assigned_track`**: Reassigning a task to a different track within the same section code without altering `affected_sections` does not alter the fingerprint.
3. **`priority_score` and `priority_breakdown`**: Altering priority arithmetic does not alter the fingerprint.
4. **`unscheduled_tasks`**: Adding, removing, or reclassifying unscheduled tasks and their root-cause reason codes does not alter the fingerprint.
5. **Schedule Metrics**: Altering `completion_rate`, total duration, or priority capture metrics does not alter the fingerprint.

---

## 16. Test Quality Audit

### Evaluation of Phase 15B Automated Tests:

| Test Name | File | Real DB Path? | Could Pass if Broken? | Concurrency Realism | Weakness Identified |
|---|---|:---:|:---:|:---:|---|
| `test_end_to_end_lifecycle_requires_explicit_approval` | `test_phase15b_lifecycle.py` | Yes | No | Sequential | None. Strong end-to-end integration assertion. |
| `test_atomic_claim_prevents_duplicate_processing` | `test_phase15b_worker_concurrency.py` | Yes | No | Concurrent | High quality. Genuine concurrent claim test. |
| `test_multi_worker_queue_concurrency` | `test_phase15b_worker_concurrency.py` | Yes | Minor | Concurrent | Line 163 allows `len(worker_ids_seen) >= 1` due to timing. |
| `test_cancellation_before_solve_real_db` | `test_phase15b_cancellation_race.py` | Yes | No | Sequential Steps | Checkpoint tested deterministically; does not test mid-solve interrupt. |
| `test_simultaneous_approvals_race` | `test_phase15b_governance_concurrency.py` | Yes | No | Concurrent | High quality. Tests real PostgreSQL row lock conflict. |
| `test_approval_vs_rejection_race` | `test_phase15b_governance_concurrency.py` | Yes | No | Concurrent | High quality. Confirms 409 conflict serialization. |
| `test_deterministic_schedule_fingerprint` | `test_phase15b_hash_integrity.py` | Unit | No | Unit | Unit test correctly tests SHA-256 sensitivity. |

---

## 17. Claim Verification Matrix

| Claim from Phase 15A/15B | Source Document | Forensic Evidence | Classification | Reason |
|---|---|---|:---:|---|
| **Zero fake state transitions** | Phase 15B Report §1 | Backend rejects unapproved states; catch blocks do not mutate local state | **PROVEN** | Mechanical state check verified. |
| **Multi-worker concurrency protected** | Phase 15B Report §1 | `SELECT FOR UPDATE SKIP LOCKED` verified with concurrent workers | **PROVEN** | PostgreSQL lock isolation verified. |
| **Cancellation races cleanly resolved** | Phase 15B Report §1 | Checkpoints tested; mid-solve CP-SAT thread interrupt not wired | **PARTIALLY PROVEN** | Pre-solve and pre-validation work; in-solve interrupt untested. |
| **Governance concurrency proven** | Phase 15B Report §1 | Simultaneous approvals and rejection races raise 409 Conflict | **PROVEN** | Atomic row lock serialization verified. |
| **Schedule fingerprint tamper resistance** | Phase 15B Report §1 | SHA-256 hashes intervals and sections, but omits crew_id and unscheduled tasks | **PARTIALLY PROVEN** | Protects task timings; does not protect crew or unscheduled metadata. |
| **Production authentication fail-closed** | Phase 15B Report §1 | `auth.py` raises 401 in production mode when credentials absent | **PROVEN** | Verified against production configuration. |
| **API rate limiting proven** | Phase 15B Report §1 | Rate limiter active only on `POST /planning-runs`; bypassable via reverse proxy IP | **PARTIALLY PROVEN** | Narrow route scope; missing X-Forwarded-For handling. |
| **Zero production secrets in client** | Phase 15A Report §1 | Verified 0 occurrences of secret tokens across `.next/static` | **PROVEN** | Confirmed by recursive file inspection. |

---

## 18. Final Risk Register

### P0 — Immediate Safety / Operational Blockers
*None. No critical safety-critical bypasses or operational command capabilities exist.*

### P1 — Serious Integrity / Security Issues
| ID | File | Location | Observed Behavior | Why It Matters | Remediation |
|---|---|---|---|---|---|
| **TM-AG-P1-01** | `frontend/src/app` | All pages | No UI exists to enter/manage authentication tokens. | Legitimate operators cannot authenticate or perform governance actions without browser console hacks; in production, all UI requests fail with HTTP 401. | Implement operator login modal or API key configuration drawer in AppShell. |
| **TM-AG-P1-02** | `backend/app/services/plan_governance_service.py` | Line 263 (`approve_plan`) | Approver identity is not checked against plan creator. | Allows a single admin user to create a plan candidate and approve it without independent four-eyes oversight. | Add constraint: `if plan.created_by == actor.username: raise PlanApprovalBlockedError("Author cannot approve own plan.")`. |

### P2 — Material Prototype Limitations
| ID | File | Location | Observed Behavior | Why It Matters | Remediation |
|---|---|---|---|---|---|
| **TM-AG-P2-01** | `frontend/src/app/(workspace)/planning/page.tsx` | Line 83 | Initializes state with `DEMO_VALIDATION_RESULT`. | When backend is offline, UI visually displays a certified "VALID" schedule with 0 errors. | Initialize validation state as `null` and render explicit offline banner. |
| **TM-AG-P2-02** | `backend/app/core/rate_limit.py` | Lines 56–76 | Limiter only applied to `POST /planning-runs`; uses `request.client.host`. | Other heavy endpoints (`/solve`, `/validate`, `/copilot`) are unthrottled; clients behind a reverse proxy share a single IP quota. | Apply limiter to all compute routes; parse `X-Forwarded-For` with trusted proxy validation. |
| **TM-AG-P2-03** | `backend/app/services/validation/validator.py` | Lines 33–53 | Fingerprint omits `crew_id`, `assigned_track`, and `unscheduled_tasks`. | Schedule metadata can be modified without triggering a fingerprint mismatch during approval. | Expand canonical fingerprint schema to include all scheduled task attributes and unscheduled task IDs. |
| **TM-AG-P2-04** | `backend/app/main.py` | Lines 37–56 | Missing security headers (CSP, HSTS, X-Frame-Options, nosniff). | Standard web security protections against clickjacking and MIME-sniffing are absent. | Add SecurityHeadersMiddleware. |

### P3 — Improvements & Code Quality
| ID | File | Location | Observed Behavior | Why It Matters | Remediation |
|---|---|---|---|---|---|
| **TM-AG-P3-01** | `backend/app/repositories/planning_run_repo.py` | Line 228 | `mark_failed` allows overwriting a `TIMED_OUT` run to `FAILED`. | Minor state machine inconsistency if a dead worker revives after heartbeat timeout. | Add `TIMED_OUT` to terminal states in `mark_failed`. |
| **TM-AG-P3-02** | `frontend/src/types/planning.ts` | Line 32 | Includes status `'DRAFT'`, which does not exist in backend enum. | Terminology confusion between frontend and backend schemas. | Normalize frontend enum to match backend `PlanVersionStatus`. |

---

## 19. Final Verdict by Architecture Category

| Category | Forensic Verdict | Summary Assessment |
|---|:---:|---|
| **Domain / Scheduling** | **PASS** | Strict interval-based model; physical headway and track isolation enforced. |
| **Optimization** | **PASS** | CP-SAT mathematical model cleanly separated from API and UI layers. |
| **Independent Validation**| **PASS** | True architectural independence; recomputes all constraints without solver imports. |
| **Persistence** | **PASS** | PostgreSQL and Alembic migrations serve as authoritative single source of truth. |
| **Worker Concurrency** | **QUALIFIED PASS** | Atomic claims via `SKIP LOCKED` verified; mid-flight solver interrupt untested. |
| **Governance** | **QUALIFIED PASS** | Concurrency and state transitions proven; four-eyes separation of duties missing. |
| **Authentication** | **QUALIFIED PASS** | Production mode fails closed; however, frontend lacks an authentication UI. |
| **Authorization / RBAC** | **PASS** | Server-side permission checks strictly enforced across all governance routes. |
| **Audit Integrity** | **QUALIFIED PASS** | Application append-only verified; lacks database-level triggers and hash chains. |
| **Frontend Data Integrity**| **QUALIFIED PASS** | Errors never become approvals; initial mount displays static demo validation. |
| **Copilot Safety** | **PASS** | Strictly read-only, deterministic evidence grounding, zero hallucination of absent data. |
| **API Security** | **QUALIFIED PASS** | CORS secure; rate limiting restricted to 1 route; missing HTTP security headers. |
| **Testing Quality** | **PASS** | Real PostgreSQL integration tests with genuine concurrent race condition testing. |
| **Production Readiness** | **NOT READY FOR PRODUCTION** | Prototype status confirmed; enterprise SSO, rate limiting, and UI auth needed. |

---

## 20. Conclusion & Next Steps

This adversarial forensic re-audit confirms that **TrackMeld's fundamental safety invariant ($\text{COMPLETED} \neq \text{APPROVED}$) is mechanically enforced and unbreachable through API or UI actions**. The Independent Validator and AI Copilot strictly adhere to their bounded architectural responsibilities.

The primary issues uncovered by this adversarial review are operational and architectural maturity gaps:
1. Providing an authentication UI in the frontend.
2. Enforcing four-eyes separation of duties in plan approvals.
3. Expanding rate limiting and fingerprint hashing coverage.
4. Suppressing static mock validation when the backend is offline.
