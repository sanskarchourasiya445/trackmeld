# TrackMeld — Phase 3 Read APIs & Domain Validation Report

## 1. Executive Summary

TrackMeld Phase 3 ("Read APIs & Domain Validation") has been completed. This phase exposes a fully typed, validated, and provenance-aware API surface across all railway reference data (from Phase 0/1) and operational planning entities (from Phase 2).

All endpoints enforce server-side validation, bounded pagination, dual identifier lookups, response count headers, structured error handling without tracebacks, and an explicit server-side authorization boundary.

---

## 2. API Surface Catalog

All endpoints are mounted under `/api/v1/` and return typed Pydantic models.

### Reference Data Endpoints

| Method | Endpoint | Description | Query Parameters / Filters | Identifier Lookups |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/stations` | List stations with pagination | `zone`, `division`, `station_type`, `classification`, `limit`, `offset` | N/A |
| `GET` | `/api/v1/stations/{code_or_id}` | Station details | None | Station code (e.g. `NDLS`) or ID (`STN-NDLS`) |
| `GET` | `/api/v1/sections` | List block sections | `zone`, `division`, `electrified`, `limit`, `offset` | N/A |
| `GET` | `/api/v1/sections/{code_or_id}` | Section topology | None | Section code (e.g. `NDLS-GZB`) or ID (`SEC-NDLS-GZB`) |
| `GET` | `/api/v1/trains` | List canonical trains | `train_type`, `corridor_table`, `classification`, `limit`, `offset` | N/A |
| `GET` | `/api/v1/trains/{number_or_id}` | Train details | None | Train number (e.g. `12301`) or ID (`TRN-12301`) |
| `GET` | `/api/v1/corridors` | List trunk corridors | `zone`, `division`, `limit`, `offset` | N/A |
| `GET` | `/api/v1/corridors/{id}` | Corridor details | None | Corridor ID (e.g. `CORR-DLI-MGS`) |
| `GET` | `/api/v1/movements` | List timetable movements | `train_id`, `station_id`, `limit`, `offset` | N/A |
| `GET` | `/api/v1/movements/{id}` | Movement entry | None | Movement ID (e.g. `MOV-12301-NDLS`) |
| `GET` | `/api/v1/rules` | List statutory rules | `limit`, `offset` | N/A |
| `GET` | `/api/v1/rules/{id}` | Rule details | None | Rule ID (e.g. `RULE-STAT-RBP-1502C`) |

### Operational Planning Endpoints

| Method | Endpoint | Description | Query Parameters / Filters | Identifier Lookups |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/tasks` | List maintenance tasks | `scenario_id`, `section_id`, `work_order_id`, `status`, `priority`, `task_type`, `mandatory`, `requires_traffic_block`, `requires_power_block`, `limit`, `offset` | N/A |
| `GET` | `/api/v1/tasks/{id_or_code}` | Task details with full graph relations | None | Task code (e.g. `TSK-TRK-001`) or ID (`TSK-0001`) |
| `GET` | `/api/v1/resources` | List maintenance resources | `resource_type`, `department`, `home_station`, `limit`, `offset` | N/A |
| `GET` | `/api/v1/resources/{id_or_code}` | Resource details | None | Resource code (e.g. `TM-BCM-01`) or ID (`RES-TM-BCM-01`) |
| `GET` | `/api/v1/resources/{id_or_code}/availability` | Resource availability intervals | `scenario_id` | Resource code or ID |
| `GET` | `/api/v1/work-orders` | List work orders | `scenario_id`, `department`, `status`, `priority`, `mandatory`, `limit`, `offset` | N/A |
| `GET` | `/api/v1/work-orders/{id_or_number}` | Work order details | None | Work order number (`WO-2026-ENG-001`) or ID |
| `GET` | `/api/v1/scenarios` | List operational scenarios | `limit`, `offset` | N/A |
| `GET` | `/api/v1/scenarios/{id_or_code}` | Scenario details | None | Scenario code (`SCN-DEMO-001`) or ID |
| `GET` | `/api/v1/scenarios/{id_or_code}/manifest` | Summarized operational manifest | None | Scenario code or ID |
| `GET` | `/api/v1/scenarios/{id_or_code}/bundle` | Fully assembled planning bundle | None | Scenario code or ID |

---

## 3. Architecture & Design Principles

### 3.1 Bounded Pagination & Metadata Headers
- All list endpoints enforce `limit: int = Query(100, ge=1, le=500)` and `offset: int = Query(0, ge=0)`.
- Requests specifying `limit <= 0` or `limit > 500` are rejected immediately with `422 Unprocessable Content`.
- Every collection response includes standard pagination headers:
  - `X-Total-Count`: Total number of matching records in the database satisfying the query filters.
  - `X-Limit`: Bounded limit applied.
  - `X-Offset`: Offset applied.

### 3.2 Server-Side Authorization Boundary (`backend/app/core/auth.py`)
- Supports `Authorization: Bearer <token>` and `X-API-Key: <key>`.
- Distinct roles: `ADMIN`, `MAINTENANCE_PLANNER`, `OPERATOR`, `VIEWER`.
- Fine-grained permission dependency: `require_permission("...")`.
- Safe prototype fallback: Unauthenticated read requests receive default viewer privileges (`UserRole.VIEWER`), ensuring smooth local testing while enforcing strict 401 rejection on invalid tokens and 403 on forbidden permissions.

### 3.3 Stable Error Payloads
- Structured JSON response for all error statuses:
  ```json
  {
    "error": {
      "code": "RESOURCE_NOT_FOUND",
      "message": "Station with code or ID 'XYZ' not found.",
      "details": null
    }
  }
  ```
- Unhandled server exceptions are caught globally, logged to system logging with stack traces, and returned as clean `HTTP 500` payloads without exposing server internals.

### 3.4 Provenance Transparency
- Every returned record contains its explicit provenance classification (`REAL`, `DERIVED`, `SYNTHETIC`, or `ASSUMED`) and associated `source_id`.

---

## 4. Verification & Audit Results

1. **Unit Test Suite (`tests/unit/test_auth.py`):**
   - 7/7 tests passed: Default viewer, valid bearer token, valid API key, invalid bearer 401, invalid API key 401, permission granted, permission denied 403.
2. **Integration Test Suite (`tests/integration/test_phase3_read_apis.py`):**
   - 8/8 test suites passed: Corridors API, Movements API, Stations dual-lookup & filtering, Sections dual-lookup & filtering, Trains dual-lookup & filtering, Tasks multi-field filtering & relations lookup, Scenario Manifest metrics, Authentication header enforcement.
3. **Full Pytest Suite:**
   - **67 passed, 0 failed** in 7.58s across 13 test files.
4. **Reference Database Integrity (`scripts/validate_database.py`):**
   - **31 passed, 0 failed** (100% integrity across 3,679 reference rows).
5. **Operational Database Integrity (`scripts/validate_operational_data.py`):**
   - **30 passed, 0 failed** (100% integrity across synthetic scenario `SCN-DEMO-001`).

---

## 5. Domain & Operational Boundary Statement

TrackMeld remains a planning and decision-support prototype. In compliance with `AGENTS.md`:
- Rules classify. Optimization schedules. Humans approve. AI explains.
- Real reference data (`REAL`, `DERIVED`) remains strictly unmutated and isolated from operational inputs (`SYNTHETIC`).
- No solver scheduling, window evaluation, or heuristic prioritization logic has been prematurely embedded in the read API layer.
