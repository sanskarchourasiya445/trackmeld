# TrackMeld Phase 9 — Plan Versions, Human Review, Approval & Immutable Audit Report

**Status:** COMPLETE  
**Executed:** October 2, 2026  
**Target Context:** Smart India Hackathon 2026 / Ministry of Railways / CRIS  
**Core Architectural Principle:**  
`Rules classify → Optimization schedules → Independent Validator verifies → Diagnostics explain → Human reviews → Human approves.`

---

## 1. Executive Summary & Purpose

In safety-critical infrastructure operations such as railway possession and maintenance scheduling, mathematical optimization algorithms and automated validation engines must **never possess autonomous approval or dispatch authority**. 

Phase 8 established an asynchronous, reproducible planning run lifecycle (`POST /api/v1/planning-runs` → background worker → independent validation → persistence). However, completing an optimization job and verifying that it is technically conflict-free is merely a prerequisite for human governance.

**Phase 9 introduces TrackMeld's formal Plan Governance, Versioning, Human Review, and Immutable Audit architecture**:
- **Candidate Plan Promotion:** A maintenance planner nominates a candidate plan (`PlanVersion`) from a completed, independently certified planning run (`is_approvable=True`, `validation_status="VALID"`).
- **Sequential Version Numbering:** Plan versions (`v1`, `v2`, `v3`) are sequentially numbered per operational scenario under PostgreSQL scenario row locks (`SELECT ... FOR UPDATE`), eliminating concurrency gaps and duplicates.
- **Collaborative Human Review Lifecycle:** Candidate plans enter a formal `PENDING_REVIEW` → `UNDER_REVIEW` state. Reviewers can attach commentary observations, evaluate timetable alignments, and verify crew arrangements.
- **Strict Approval Gating:** Approval is strictly restricted to authenticated users holding the `plan:approve` permission (e.g. `divisional_operations_manager`). Prior to approval, the system enforces:
  1. Technical validation status must be `VALID` and `is_approvable=True`.
  2. Zero unresolved hard validation errors (`error_count == 0`).
  3. Strict cryptographic fingerprint integrity (`schedule_identity`, `snapshot_hash`, `input_hash`) matching the certified source run.
- **Automatic Superseding:** Approving a new plan version (e.g. `v2`) automatically transitions any currently approved version (`v1`) to `SUPERSEDED`, recording superseding timestamps and provenance pointers (`previous_plan_version_id = v1.plan_version_id`).
- **Explicit Rejection with Mandatory Justification:** Operational rejections require a substantive explanation (minimum 5 characters) capturing operational rationale. Rejected plans cannot be resurrected or approved.
- **Immutability of Approved & Terminal Plans:** Approved plans cannot be modified, re-approved, or rejected in place. Any schedule revision requires generating and nominating a new candidate plan version.
- **Append-Only Governance Audit Trail:** Every lifecycle transition (`PLAN_VERSION_CREATED`, `PLAN_REVIEW_STARTED`, `PLAN_COMMENT_ADDED`, `PLAN_APPROVED`, `PLAN_REJECTED`, `PLAN_SUPERSEDED`) is immutably recorded with actor ID, username, role, timestamp, previous state, new state, reason, commentary, and cryptographic schedule hashes.
- **Core Product Invariant Enforced:** `COMPLETED != APPROVED`. Solver completion and independent validation NEVER imply or grant plan approval. Only authorized humans can approve a plan.

---

## 2. Architectural Boundary & Workflow

```
   Maintenance Planner                     Operations Officer (Approver)                PostgreSQL Database
  ─────────────────────                   ───────────────────────────────              ─────────────────────
            │                                            │                                       │
  1. Complete Planning Run                               │                                       │
     (Phase 8 Worker)                                    │                                       │
            │                                            │                                       │
  2. POST /planning-runs/{id}/plan-version               │                                       │
     ────────────────────────────────────────────────────┼──────────────────────────────────────►│
     Promote certified run to PlanVersion v1             │                                       │
     ◄───────────────────────────────────────────────────┼───────────────────────────────────────│
     HTTP 201 Created (status=PENDING_REVIEW)            │                                       │
            │                                            │                                       │
  3. POST /plan-versions/{id}/review                     │                                       │
     ────────────────────────────────────────────────────┼──────────────────────────────────────►│
     Start review (status=UNDER_REVIEW)                  │                                       │
     ◄───────────────────────────────────────────────────┼───────────────────────────────────────│
     HTTP 200 OK (reviewed_by, reviewed_at)              │                                       │
            │                                            │                                       │
  4. POST /plan-versions/{id}/comments                   │                                       │
     ────────────────────────────────────────────────────┼──────────────────────────────────────►│
     Add review commentary                               │                                       │
     ◄───────────────────────────────────────────────────┼───────────────────────────────────────│
     HTTP 201 Created (recorded in audit log)            │                                       │
            │                                            │                                       │
            │                                 5. POST /plan-versions/{id}/approve                │
            │                                    ───────────────────────────────────────────────►│ Lock row FOR UPDATE
            │                                    Verify Technical VALID & 0 errors               │ Verify integrity hashes
            │                                    Supersede any existing approved version         │ Set status=APPROVED
            │                                    ◄───────────────────────────────────────────────│ Log PLAN_APPROVED
            │                                    HTTP 200 OK (approved_by, approved_at)          │
            │                                            │                                       │
            │                                 6. GET /plan-versions/{id}/audit                   │
            │                                    ───────────────────────────────────────────────►│ Fetch audit trail
            │                                    ◄───────────────────────────────────────────────│
            │                                    HTTP 200 OK (complete immutable history)        │
```

---

## 3. Database Schema & Migration Details

### Migration: `9c2d1e4f7a01_004_plan_versions_and_audit.py`
Created tables `plan_versions`, `plan_review_comments`, and `governance_audit_events` with composite indexes and PostgreSQL JSONB structures:

#### Table `plan_versions`
| Column | Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| `id` | Integer (PK) | No | Auto-increment primary key |
| `plan_version_id` | String(64) | No | Unique business identifier (`PV-YYYYMMDD-HEX`) |
| `scenario_id` | String(64) | No | Foreign key to `operational_scenarios.scenario_id` |
| `planning_run_id` | String(64) | No | Unique foreign key to `planning_runs.run_id` |
| `version_number` | Integer | No | Sequential version index per scenario (1, 2, 3...) |
| `status` | String(32) | No | State: `PENDING_REVIEW`, `UNDER_REVIEW`, `APPROVED`, `REJECTED`, `SUPERSEDED` |
| `schedule_identity`| String(64) | No | 64-char SHA-256 fingerprint generated by Independent Validator |
| `snapshot_hash` | String(64) | No | 64-char SHA-256 snapshot hash |
| `input_hash` | String(64) | No | 64-char SHA-256 input configuration hash |
| `schedule_result` | JSONB | No | Full verified schedule placements, intervals, and envelopes |
| `result_summary` | JSONB | No | Summary metrics (scheduled tasks, total possession time, completion rate) |
| `validation_status`| String(32) | No | Technical validation status (`VALID`, `INVALID`, `UNKNOWN`) |
| `is_approvable` | Boolean | No | Independent approval gate boolean assertion |
| `validation_findings_summary` | JSONB | Yes | Error and warning count breakdown |
| `diagnostics_summary` | JSONB | Yes | Root-cause analysis on unscheduled tasks |
| `scheduler_type` | String(32) | No | Algorithm strategy (`CP_SAT`, `FCFS`, `PRIORITY_GREEDY`) |
| `scheduler_version`| String(32)| No | Solver/engine version string |
| `solver_name` | String(64) | No | Solver implementation identity |
| `solver_version` | String(32) | No | Solver library version |
| `dataset_version` | String(32) | No | Operational dataset version |
| `configuration_snapshot` | JSONB | No | Configuration parameters used during execution |
| `priority_configuration` | JSONB | Yes | Priority weights snapshot |
| `optimization_configuration` | JSONB | Yes | Solver search parameters |
| `created_at` | DateTime(tz) | No | Plan creation timestamp (UTC) |
| `created_by` | String(64) | No | Username of maintenance planner |
| `reviewed_at` | DateTime(tz) | Yes | Timestamp review commenced |
| `reviewed_by` | String(64) | Yes | Username of reviewer |
| `approved_at` | DateTime(tz) | Yes | Formal approval timestamp |
| `approved_by` | String(64) | Yes | Username of authorized operations officer |
| `rejected_at` | DateTime(tz) | Yes | Rejection timestamp |
| `rejected_by` | String(64) | Yes | Username of rejecting officer |
| `review_comment` | Text | Yes | General commentary or creation context |
| `rejection_reason`| Text | Yes | Mandatory operational justification for rejection |
| `previous_plan_version_id` | String(64) | Yes | Pointer to superseded plan version |
| `superseded_at` | DateTime(tz) | Yes | Timestamp this plan was superseded by a newer approved version |
| `superseded_by` | String(64) | Yes | Username that approved the superseding version |
| `updated_at` | DateTime(tz) | No | Last modification timestamp |

#### Table `plan_review_comments`
| Column | Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| `id` | Integer (PK) | No | Auto-increment primary key |
| `review_id` | String(64) | No | Unique business identifier (`REV-YYYYMMDD-HEX`) |
| `plan_version_id` | String(64) | No | Foreign key to `plan_versions.plan_version_id` |
| `actor_id` | String(64) | No | User ID of the reviewer |
| `actor_username` | String(64) | No | Username of the reviewer |
| `action` | String(32) | No | `START_REVIEW`, `COMMENT`, `APPROVE`, `REJECT` |
| `comment` | Text | No | Review feedback or operational observation |
| `created_at` | DateTime(tz) | No | Timestamp comment was created (UTC) |

#### Table `governance_audit_events`
| Column | Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| `id` | Integer (PK) | No | Auto-increment primary key |
| `event_id` | String(64) | No | Unique business identifier (`AUD-YYYYMMDD-HEX`) |
| `entity_type` | String(32) | No | Fixed entity type (`PLAN_VERSION`) |
| `entity_id` | String(64) | No | Target plan version identifier |
| `event_type` | String(32) | No | `PLAN_VERSION_CREATED`, `PLAN_REVIEW_STARTED`, `PLAN_COMMENT_ADDED`, `PLAN_APPROVED`, `PLAN_REJECTED`, `PLAN_SUPERSEDED` |
| `actor_id` | String(64) | No | User ID performing the action |
| `actor_username` | String(64) | No | Username performing the action |
| `actor_role` | String(32) | No | Role of the actor (`ADMIN`, `OPERATOR`, `MAINTENANCE_PLANNER`) |
| `timestamp` | DateTime(tz) | No | UTC event occurrence timestamp |
| `previous_state`| String(32) | Yes | Pre-transition status |
| `new_state` | String(32) | Yes | Post-transition status |
| `reason` | Text | Yes | Formal operational reason |
| `comment` | Text | Yes | Commentary or audit note |
| `schedule_identity`| String(64)| Yes| Cryptographic fingerprint of schedule at event time |
| `snapshot_hash` | String(64) | Yes | 64-char snapshot hash |
| `input_hash` | String(64) | Yes | 64-char input configuration hash |
| `event_metadata` | JSONB | Yes | Structured contextual metadata |

---

## 4. State Machine & Legal Transitions

The PlanVersion lifecycle enforces strict legal state transitions:

```
                  ┌────────────────────────┐
                  │     PENDING_REVIEW     │
                  └───────────┬────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
      ┌───────────────┐ ┌───────────┐ ┌───────────────┐
      │ UNDER_REVIEW  │ │ APPROVED  │ │   REJECTED    │
      └───────┬───────┘ └─────┬─────┘ └───────────────┘
              │               │          (Terminal)
              ├───────────────┤
              │               ▼
              │       ┌───────────────┐
              └──────►│  SUPERSEDED   │
                      └───────────────┘
                         (Terminal)
```

| Current Status | Allowed Target Statuses | Notes |
| :--- | :--- | :--- |
| `PENDING_REVIEW` | `UNDER_REVIEW`, `APPROVED`, `REJECTED` | Initial candidate state upon nomination from certified run |
| `UNDER_REVIEW` | `APPROVED`, `REJECTED`, `PENDING_REVIEW` | Active human review in progress |
| `APPROVED` | `SUPERSEDED` | Approved schedule. Immutable; only transitioned when a newer plan is approved |
| `REJECTED` | *(None - Terminal)* | Explicit human rejection. Cannot be resurrected or approved |
| `SUPERSEDED` | *(None - Terminal)* | Historical predecessor plan. Permanently archived |

Attempting any disallowed transition (e.g. `REJECTED` → `APPROVED`, or `APPROVED` → `REJECTED`) raises `InvalidPlanVersionTransitionError` and returns `HTTP 409 Conflict`.

---

## 5. Role-Based Access Control (RBAC) Matrix

| User Role | Credentials Token | Can Nominate Candidate | Can Review / Comment | Can Formally Approve | Can Formally Reject |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **OPERATOR** (Approver) | `approver-token-2026` | Yes | Yes | **Yes** | **Yes** |
| **MAINTENANCE_PLANNER** | `planner-token-2026` | **Yes** | **Yes** | No (HTTP 403) | No (HTTP 403) |
| **VIEWER** | `viewer-token-2026` | No (HTTP 403) | No (HTTP 403) | No (HTTP 403) | No (HTTP 403) |
| **ADMIN** | `admin-token-2026` | Yes | Yes | Yes | Yes |

---

## 6. REST API Endpoints Delivered

Mounted under `/api/v1`:

1. `POST /api/v1/planning-runs/{run_id}/plan-version` (`status=201 Created`):
   - Promotes a completed, certified planning run to a candidate `PlanVersion`.
   - Requires `write:operational` permission.
   - Blocks with `HTTP 422` if run is uncompleted or unverified (`is_approvable=False`).
   - Blocks with `HTTP 409` if a `PlanVersion` already exists for this run.

2. `POST /api/v1/plan-versions` (`status=201 Created`):
   - Direct candidate creation accepting `{ "planning_run_id": "...", "comment": "..." }`.

3. `GET /api/v1/plan-versions/{plan_version_id}` (`status=200 OK`):
   - Retrieves full plan version details including complete schedule result, result summary, validation findings, diagnostics summary, and chronological review comments.

4. `GET /api/v1/plan-versions` (`status=200 OK`):
   - Paginated listing with filtering by `scenario_id`, `status`, `planning_run_id`, `created_by`.
   - Returns `X-Total-Count` HTTP response header.

5. `POST /api/v1/plan-versions/{plan_version_id}/review` (`status=200 OK`):
   - Transitions plan candidate to `UNDER_REVIEW`. Requires `plan:review`.

6. `POST /api/v1/plan-versions/{plan_version_id}/comments` (`status=201 Created`):
   - Appends review commentary. Requires `plan:review`.

7. `POST /api/v1/plan-versions/{plan_version_id}/approve` (`status=200 OK`):
   - Formally approves candidate plan. Restricted to `plan:approve` (authorized operations officer).
   - Enforces validation status `VALID`, `error_count == 0`, and cryptographic fingerprint match.
   - Automatically supersedes any previously approved plan for the scenario.

8. `POST /api/v1/plan-versions/{plan_version_id}/reject` (`status=200 OK`):
   - Explicit rejection with mandatory `reason` (minimum 5 characters).
   - Restricted to `plan:reject`.

9. `GET /api/v1/plan-versions/{plan_version_id}/audit` (`status=200 OK`):
   - Retrieves immutable chronological governance audit trail.

---

## 7. Verification & Invariant Audit Results

### Summary of Test Execution
- **Phase 9 Unit Tests:** 11 passed, 0 failed in `tests/unit/test_phase9_governance.py`.
- **Phase 9 Integration Tests:** 6 passed, 0 failed in `tests/integration/test_phase9_governance_api.py`.
- **Phase 9 Invariant Validation Script:** 22/22 checks passed in `scripts/validate_phase9_plan_governance.py`.
- **Full Pytest Regression Suite:** 190 passed, 0 failed in 17.03s across 27 test files.
- **All Milestone Validation Scripts:** 8 suites, 197 total checks passed, 0 failed:
  - `validate_database.py`: 31/31 passed
  - `validate_operational_data.py`: 30/30 passed
  - `validate_phase4_compatibility.py`: 17/17 passed
  - `validate_phase5_schedulers.py`: 30/30 passed
  - `validate_phase6_cp_sat.py`: 22/22 passed
  - `validate_phase7_validation.py`: 23/23 passed
  - `validate_phase8_planning_jobs.py`: 22/22 passed
  - `validate_phase9_plan_governance.py`: 22/22 passed

---

## 8. Non-Negotiable Boundary Checks

1. **COMPLETED ≠ APPROVED:** An optimization run completing with status `COMPLETED` and validation status `VALID` is NEVER automatically approved. Plan approval requires explicit, authenticated human operator action.
2. **Zero In-Place Edits:** An approved plan is strictly immutable. If track conditions change, a new planning run and candidate plan version must be created and approved.
3. **Audit Hashes as Tamper-Evidence:** Stored 64-character SHA-256 hashes (`schedule_identity`, `snapshot_hash`, `input_hash`) serve as mathematical tamper-evidence and reproducibility assertions, not as standalone legal signatures.
