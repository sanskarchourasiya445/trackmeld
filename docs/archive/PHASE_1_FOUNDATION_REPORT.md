# TrackMeld Phase 1 — Project Foundation & Canonical Data Model Report

**Status:** Phase 1 Complete  
**Date:** October 2, 2026  
**Auditor / Agent:** Software Architecture & Data Engineering Agent  
**Context:** TrackMeld — Decision Support & Maintenance Possession Planning (Smart India Hackathon 2026 / Ministry of Railways / CRIS Use Case)  

---

## Executive Summary

Phase 1 successfully builds the complete software foundation for TrackMeld, consuming the verified Phase 0 datasets and establishing a clean, deterministic, provenance-aware PostgreSQL database and FastAPI service.

In strict compliance with project rules:
- **No missing railway data was fabricated.**
- **No CP-SAT optimizer, AI copilot, or frontend workstation was built.**
- **No fake BDMS/TMS/COA adapters were created.**
- **The canonical provenance invariant was strictly enforced:** `REAL ≠ DERIVED ≠ SYNTHETIC ≠ ASSUMED`.
- **Alembic migration reproduces the entire relational schema from an empty database.**
- **Deterministic ingestion is 100% idempotent:** verified across multiple runs with zero row growth.
- **Automated database validation suite executed 30 comprehensive integrity checks: 30 passed, 0 failed.**
- **Full test suite executed 31 unit and integration tests: 31 passed, 0 failed in 5.23s.**

---

## 1. Repository Inspection & Data Structures Consumed

Prior to implementation, the repository was inspected. The implementation directly consumes the actual Phase 0 normalized datasets:

| Dataset | Phase 0 Source Path | Records Consumed | Target Table | Classification |
| :--- | :--- | :--- | :--- | :--- |
| **Sources** | `data/metadata/sources.json` | 18 | `source_documents` | `OFFICIAL_MINISTRY`, `OFFICIAL_RAILWAY_BOARD`, `OFFICIAL_CRIS` |
| **Stations** | `data/normalized/stations.json` | 68 | `stations` | `REAL` |
| **Sections** | `data/normalized/sections.json` | 66 | `sections` | `DERIVED` |
| **Trains** | `data/normalized/trains.json` | 3,429 | `trains` | `REAL` |
| **Movements** | `data/normalized/train_movements.json` | 82 | `train_movements` | `REAL` |
| **Rules** | `data/normalized/rules.json` | 9 | `railway_rules` | `VERIFIED_SOURCE` |
| **Specs** | `data/normalized/infrastructure.json` | 3 | `infrastructure_specs` | `REAL` |
| **Corridors** | `data/normalized/infrastructure.json` | 4 | `corridors` | `REAL` |
| **Total** | — | **3,679** | — | — |

---

## 2. Architecture Implemented

The backend is organized with clear separation of concerns:

```
backend/
├── app/
│   ├── config.py             # Settings loaded via pydantic-settings (.env)
│   ├── main.py               # FastAPI application with request_id middleware
│   ├── api/
│   │   ├── health.py         # Liveness & DB readiness probes (/health, /health/db)
│   │   ├── router.py         # Master API router
│   │   └── v1/               # Versioned REST reference endpoints (stations, sections, trains, rules)
│   ├── db/
│   │   ├── base.py           # DeclarativeBase with constraint naming conventions
│   │   ├── session.py        # Async & Sync SQLAlchemy 2.0 engine factories
│   │   └── models/           # SQLAlchemy ORM models with foreign keys & indexes
│   ├── domain/               # Strict Pydantic domain models & provenance validators
│   ├── repositories/         # Async database access layer (StationRepo, TrainRepo, etc.)
│   ├── schemas/              # Consistent API response payloads & error envelopes
│   └── services/             # OperationalDataProvider abstract interface boundary
├── alembic/                  # Database migration environment
└── tests/                    # Unit and integration test suites
```

---

## 3. Database Schema & Migration Status

Alembic initial migration [`backend/alembic/versions/7cddc023e092_001_initial_schema.py`](file:///d:/Trackmeld/backend/alembic/versions/7cddc023e092_001_initial_schema.py) was generated and applied:
- Applied cleanly to PostgreSQL 18.4 via `alembic upgrade head`.
- Generated tables:
  1. `source_documents` (PK: `source_id`, unique hashes, authority metadata)
  2. `stations` (PK: `station_id`, unique: `station_code`, FK: `source_id`)
  3. `sections` (PK: `section_id`, unique: `section_code`, FK: `from_station_id`, `to_station_id`, check: `length_km > 0`, check: `from != to`)
  4. `trains` (PK: `train_id`, unique: `train_number`, FK: `source_id`)
  5. `train_movements` (PK: `movement_id`, FK: `train_id`, `station_id`, `source_id`, check: `stop_sequence >= 1`, index: `(station_id, scheduled_departure)`)
  6. `railway_rules` (PK: `rule_id`, FK: `source_id`, index: `category`)
  7. `infrastructure_specs` (PK: `spec_id`, FK: `source_id`)
  8. `corridors` (PK: `corridor_id`, FK: `source_id`)

---

## 4. Deterministic Ingestion & Idempotency

Script [`scripts/ingest_phase0.py`](file:///d:/Trackmeld/scripts/ingest_phase0.py) reads normalized Phase 0 datasets, parses into Pydantic models, and executes PostgreSQL `ON CONFLICT DO UPDATE` upserts:
- **Execution Speed:** 3,679 records ingested in **3.44 seconds**.
- **Idempotency Verification:** Re-running the script produces identical row counts (3,679 records) with zero duplicate keys or orphaned rows.

---

## 5. Automated Validation & Test Suite

### 5.1. Database Validation Suite (`scripts/validate_database.py`)
Executed 30 integrity checks:
- **Source Documents:** 18 records, 0 duplicates, 0 nulls.
- **Stations:** 68 stations, 0 duplicate codes, 0 orphan FKs, 100% `REAL`.
- **Sections:** 66 sections, 0 duplicate codes, strictly positive lengths, strictly distinct endpoints, 0 orphan FKs, 100% `DERIVED`.
- **Trains:** 3,429 trains, 0 duplicate numbers, 0 orphan FKs, 100% `REAL`.
- **Movements:** 82 movements, 0 duplicate IDs, 0 orphan FKs, valid 24h timetable times, stop sequence >= 1, 100% `REAL`.
- **Rules:** 9 rules, 0 orphan FKs, 100% `VERIFIED_SOURCE`.
- **Infrastructure:** 3 specs, 4 corridors, 0 orphan FKs.
- **Result:** **30 passed, 0 failed.**

### 5.2. Pytest Test Suite (`python -m pytest`)
Executed 31 automated tests across unit and integration categories:
- **Unit Tests (16 passed):**
  - Provenance classification distinctness (`REAL != DERIVED != SYNTHETIC != ASSUMED`).
  - Immutability guards preventing promotion of non-REAL to REAL.
  - Domain model validations for Station, Section, Train, Movement, and Rule.
- **Integration Tests (15 passed):**
  - PostgreSQL async connectivity (`current_database() == "trackmeld"`).
  - Repositories (`StationRepository`, `SectionRepository`, `TrainRepository`, `TrainMovementRepository`, `RailwayRuleRepository`, `InfrastructureRepository`).
  - FastAPI endpoints (`/health`, `/health/db`, `/api/v1/stations/NDLS`, `/api/v1/sections/NDLS-GZB`, `/api/v1/trains/12301`, `/api/v1/rules/RULE-STAT-RBP-1502C`).
  - Error handling: 404 structured payload for unknown resources.
  - Ingestion idempotency test.
- **Result:** **31 passed in 5.23s (100% pass rate).**

---

## 6. Known Limitations & Phase 2 Readiness

1. **Timetable Sparsity:**
   - 82 movements represent flagship express services on trunk corridors. Unreserved passenger services and non-timetabled freight paths are not published in public TAG.
2. **Operational Data Boundary:**
   - Real maintenance possession requisitions and live control logs are internal to Indian Railways Railnet (BDMS/TMS/COA). In Phase 2, candidate work orders will be generated using a deterministic synthetic task generator adhering to IRPWM/ACTM standards.

**Phase 2 Readiness:** The repository is fully prepared to begin **Phase 2: Backend Domain & Operational Data Layer** (synthetic maintenance task generator, resource registry, and possession requisition models).
