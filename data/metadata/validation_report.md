# TrackMeld Phase 0 — Data Quality Validation Report

**Generated:** 2026-10-02T17:05:25.567601  
**Overall Validation Status:** **PASSED**  
**Pass Rate:** 100.0% (11228 checks passed, 0 failed)

## 1. Verified Record Counts

| Dataset | Scope | Classification | Record Count | Integrity Status |
| :--- | :--- | :--- | :--- | :--- |
| **Sources** | Official Gov/Railway Publications | OFFICIAL | 18 | VERIFIED (100% SHA-256 Hashed) |
| **Stations** | Trunk Corridor Stations | REAL | 68 | VERIFIED (100% Unique Codes) |
| **Trains** | All-India Train Catalog | REAL | 3429 | VERIFIED (100% Unique Numbers) |
| **Sections** | Block Sections | DERIVED | 66 | VERIFIED (100% Valid Endpoints) |
| **Movements** | Scheduled Timetable Passes | REAL | 82 | VERIFIED (100% Valid References) |
| **Rules** | Statutory & Operating Rules | REAL | 9 | VERIFIED (100% Original Text Preserved) |

## 2. Validation Checks Executed

- [x] **Duplicate Station Codes:** No duplicates found across 68 stations.
- [x] **Duplicate Train Numbers:** No duplicates found across 3429 trains.
- [x] **Missing Identifiers:** Primary keys present and validated across all entities.
- [x] **Broken Foreign Keys:** All train movements reference valid `train_id` and `station_id`.
- [x] **Section Topology:** All section endpoints reference valid canonical stations with positive kilometrage.
- [x] **Source Provenance:** 100% of stations, trains, movements, sections, and rules trace back to registered `source_id` entries.
- [x] **Safety Rule Authority:** 100% of extracted rules contain exact verbatim `original_text` alongside summaries.
- [x] **Classification Transparency:** Real vs. Derived vs. Synthetic strictly declared on every record.

## 3. Issues and Anomalies

No validation issues or schema errors detected.
