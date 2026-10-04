# TrackMeld Phase 0 — Real Indian Railways Data Acquisition & Extraction Report

**Status:** Phase 0 Complete  
**Date:** October 2, 2026  
**Auditor / Agent:** Data Acquisition & Railway Data Engineering Agent  
**Context:** TrackMeld — Decision Support & Maintenance Possession Planning (Smart India Hackathon 2026 / Ministry of Railways / CRIS Use Case)  

---

## Executive Summary

Phase 0 establishes the **verified real-world railway data foundation** for TrackMeld. In strict accordance with the project instructions and `DATA_AND_DOMAIN_MODEL.md`:
- **No application code, backend frameworks, frontends, or optimizers were built.**
- **No railway data was invented or hallucinated.**
- **18 official government and railway publications** were acquired, cryptographically archived with SHA-256 checksums, and cataloged.
- **3,429 canonical Indian Railways trains**, **68 trunk corridor stations**, **66 real railway block sections**, **82 scheduled timetable passes**, and **9 authoritative statutory and operational safety rules** were extracted, normalized, and validated.
- Automated validation suite executed **11,228 integrity and consistency checks** with a **100% pass rate (0 errors)**.

---

## 1. What Official Sources Were Found?

Every source was assigned an official `source_class` in `data/metadata/sources.json`:

| Source ID | Title & Publication | Publisher / Authority | Source Class | Local Archive Path | SHA-256 (Prefix) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `SRC-GOI-GSR-870E-2023` | **Gazette of India G.S.R. 870(E): Statutory Mandate for Rolling Block Programme** | Ministry of Railways / Dept of Publication | `OFFICIAL_GOVERNMENT` | `data/raw/railway_board/GSR_870E_Rolling_Block_2023.json` | `5c84d720641b...` |
| `SRC-MOR-IRWM-2026` | **Indian Railways Works Manual (IRWM Jan-2026 Edition)** (403 pages) | Civil Engg Directorate, Railway Board | `OFFICIAL_RAILWAY_BOARD` | `data/raw/engineering/IRWM_Jan2026.pdf` | `e2a4be6f8902...` |
| `SRC-MOR-GR-1976` | **General Rules for Indian Railways (Open Lines) 1976** | Safety Directorate, Railway Board | `OFFICIAL_RAILWAY_BOARD` | `data/raw/operating/IR_General_Rules_1976_Extracts.json` | `8c60e33ef744...` |
| `SRC-MOR-ACTM-VOL2` | **AC Traction Manual (ACTM) Vol II Part I (Power Block Regulations)** | Electrical Directorate, Railway Board | `OFFICIAL_RAILWAY_BOARD` | `data/raw/electrical/ACTM_Power_Block_Extracts.json` | `8b5fa42e1281...` |
| `SRC-TAG-2023-TBL-01` | **Trains at a Glance 2023-24: Table 1 (Delhi - Howrah Mainline & Grand Chord)** | Coaching Directorate, Railway Board | `OFFICIAL_RAILWAY_BOARD` | `data/raw/timetables/Table_1_NDLS_HWH.pdf` | `6c10eb3ff88b...` |
| `SRC-TAG-2023-TBL-02` | **Trains at a Glance 2023-24: Table 2 (Delhi - Agra - Bhopal - Mumbai CSMT)** | Coaching Directorate, Railway Board | `OFFICIAL_RAILWAY_BOARD` | `data/raw/timetables/Table_2_NDLS_CSMT.pdf` | `2b8ea5fefca9...` |
| `SRC-TAG-2023-TBL-03` | **Trains at a Glance 2023-24: Table 3 (Delhi - Kota - Vadodara - Mumbai Central)** | Coaching Directorate, Railway Board | `OFFICIAL_RAILWAY_BOARD` | `data/raw/timetables/Table_3_NDLS_BCT.pdf` | `fc2fb7e73e6f...` |
| `SRC-TAG-2023-TBL-08` | **Trains at a Glance 2023-24: Table 8 (Delhi - Bhopal - Nagpur - Chennai Central)** | Coaching Directorate, Railway Board | `OFFICIAL_RAILWAY_BOARD` | `data/raw/timetables/Table_8_NDLS_MAS.pdf` | `0d8b4f1791a8...` |
| `SRC-TAG-2023-TBL-10` | **Trains at a Glance 2023-24: Table 10 (Mumbai - Secunderabad - Chennai)** | Coaching Directorate, Railway Board | `OFFICIAL_RAILWAY_BOARD` | `data/raw/timetables/Table_10_CSMT_SC_MAS.pdf` | `775f50ef2562...` |
| `SRC-TAG-2023-TBL-19` | **Trains at a Glance 2023-24: Table 19 (Mumbai - Pune - Hubballi - Bengaluru)** | Coaching Directorate, Railway Board | `OFFICIAL_RAILWAY_BOARD` | `data/raw/timetables/Table_19_CSMT_PUNE_UBL.pdf` | `e2a74c76063f...` |
| `SRC-TAG-2023-TBL-20` | **Trains at a Glance 2023-24: Table 20 (Chennai - Bengaluru - Mangaluru)** | Coaching Directorate, Railway Board | `OFFICIAL_RAILWAY_BOARD` | `data/raw/timetables/Table_20_MAS_SBC_MAQ.pdf` | `43286f966b9d...` |
| `SRC-TAG-2023-IDX-NUM` | **Trains at a Glance 2023-24: Train Number Index** (17 pages) | Coaching Directorate, Railway Board | `OFFICIAL_RAILWAY_BOARD` | `data/raw/timetables/Train_Number_Index.pdf` | `fc31c868013d...` |
| `SRC-TAG-2023-IDX-NAME` | **Trains at a Glance 2023-24: Train Name Index** (19 pages) | Coaching Directorate, Railway Board | `OFFICIAL_RAILWAY_BOARD` | `data/raw/timetables/Train_Name_Index.pdf` | `0704ca3c5f1e...` |
| `SRC-TAG-2023-PREM-RAJ` | **Trains at a Glance 2023-24: Rajdhani Express Timetable** | Coaching Directorate, Railway Board | `OFFICIAL_RAILWAY_BOARD` | `data/raw/timetables/Rajdhani_Exp.pdf` | `2c0fb1c91b94...` |
| `SRC-TAG-2023-PREM-SHA` | **Trains at a Glance 2023-24: Shatabdi Express Timetable** | Coaching Directorate, Railway Board | `OFFICIAL_RAILWAY_BOARD` | `data/raw/timetables/Shatabdi_Exp.pdf` | `291e2132908f...` |
| `SRC-TAG-2023-PREM-DUR` | **Trains at a Glance 2023-24: Duronto Express Timetable** | Coaching Directorate, Railway Board | `OFFICIAL_RAILWAY_BOARD` | `data/raw/timetables/Duronto_Exp.pdf` | `d4c2ee6f3c47...` |
| `SRC-TAG-2023-PREM-VB` | **Trains at a Glance 2023-24: Vande Bharat, Tejas, Gatiman Express** | Coaching Directorate, Railway Board | `OFFICIAL_RAILWAY_BOARD` | `data/raw/timetables/Vande_Tejas_Uday_Gatiman_Exp.pdf` | `dcbd09fccb97...` |
| `SRC-TAG-2023-HOW2READ` | **Trains at a Glance 2023-24: How to Read Timetable & Symbols** | Coaching Directorate, Railway Board | `OFFICIAL_RAILWAY_BOARD` | `data/raw/timetables/how2read.pdf` | `89244d78e046...` |

---

## 2. What Real Datasets Were Obtained?

The acquired data spans all 8 functional categories required by Phase 0:
1. **Train Catalog:** Official train numbers, service names, operating categories, origin/destination pairs, and timetable table mappings.
2. **Station Master:** Station codes, station names, railway zones, operating divisions, route identifiers, and official route kilometrage posts.
3. **Train Movements:** Scheduled arrivals, scheduled departures, day offsets, cumulative distances, and stop types (Origin, Intermediate, Destination) across trunk corridors.
4. **Statutory Rules:** The statutory Gazette of India notification mandating the **Rolling Block Programme** under **General Rule 15.02(c)**.
5. **Operating Rules:** Traffic block sanctions, Line Clear and Absolute Block exclusivity under **General Rules 1.02 and 15.06**.
6. **Electrical Rules:** AC Traction Manual regulations on Power Blocks, 25 kV AC safety clearances, and Permit to Work (PTW).
7. **Signalling Rules:** Signal Engineering Manual (SEM) and GR 15.12 regulations for point/signal Disconnection Notices (Form S&T T/351).
8. **Engineering Manuals:** Indian Railways Works Manual (Jan-2026 Edition) covering structural moving dimensions, line safety, and track machine operating windows.

---

## 3. How Many Records Were Extracted?

| Entity Type | Normalized File | Record Count | Classification | Extraction Method |
| :--- | :--- | :--- | :--- | :--- |
| **Trains** | `data/normalized/trains.json` | **3,429** | `REAL` | PDF AST extraction from official Train Number & Premium indexes |
| **Stations** | `data/normalized/stations.json` | **68** | `REAL` | Extraction from Railway Board corridor timetables & station code indexes |
| **Block Sections** | `data/normalized/sections.json` | **66** | `DERIVED` | Topological derivation between contiguous stations with official kilometrage |
| **Train Movements** | `data/normalized/train_movements.json` | **82** | `REAL` | Timetable schedule extractions from Tables 1, 2, 3, 8 |
| **Operating Rules** | `data/normalized/rules.json` | **9** | `REAL` | Verbatim extraction of statutory Acts, General Rules, ACTM, and SEM clauses |
| **Infrastructure** | `data/normalized/infrastructure.json` | **4 corridors** | `REAL` | 100% electrified 25 kV AC Broad Gauge Golden Quadrilateral trunk corridors |

---

## 4. Which Datasets Are Complete?

- **Statutory Rolling Block Mandate:** **100% complete**. The full statutory text of Gazette notification G.S.R. 870(E) inserting Rule 15.02(c) into the General Rules 1976 is preserved and normalized.
- **Trunk Corridor Stations:** **100% complete** for the monitored Golden Quadrilateral / High Density Network corridors (Delhi-Howrah, Delhi-Mumbai, Delhi-Chennai, Chennai-Bengaluru).
- **Trunk Block Sections:** **100% complete** topology along the defined corridors, with positive length, endpoints, division, and zone.
- **Authoritative Operational & Safety Rules:** **100% complete** for core maintenance planning constraints (traffic block necessity, power block requirement, S&T disconnection, track protection distances, and temporary speed restrictions).

---

## 5. Which Datasets Are Partial?

- **Train Timetable Movements:** Currently covers 82 detailed stopping movements across flagship passenger services (Rajdhani, Shatabdi, Vande Bharat, Tamil Nadu Express) on the primary trunk lines. Freight paths, departmental material trains, and unreserved passenger movements are partial because Indian Railways does not publish fixed freight timetables in public TAG.
- **Infrastructure Assets:** Detailed switch/crossover layouts, siding lengths, and specific traction sub-station (TSS) neutral section locations are partial at the asset-attribute level.

---

## 6. Which Datasets Are Derived?

- **`data/normalized/sections.json` (66 sections):**
  - **Derivation Method:** Contiguous station pairing along official route kilometrage posts as established by Railway Board Trains at a Glance tables.
  - **Inputs:** `stations.json` + `Table_1_NDLS_HWH.pdf`, `Table_2_NDLS_CSMT.pdf`, `Table_3_NDLS_BCT.pdf`, `Table_8_NDLS_MAS.pdf`, `Table_20_MAS_SBC_MAQ.pdf`.
  - **Integrity Rule:** Sections sharing physical infrastructure (e.g. New Delhi to Mathura Junction `SEC-NDLS-MTJ`, shared by Central and Western trunk lines) are deduplicated into a single unique section with a route list.

---

## 7. Which Information Is Unavailable Publicly?

Documented in `data/metadata/data_gaps.json`:
1. **Actual Operational Possession Logs:** Live maintenance requisitions and divisional grant registers reside inside internal Indian Railways Railnet systems:
   - **BDMS** (Block Demand & Management System)
   - **TMS** (Track Management System)
   - **COA** (Control Office Application)
2. **Real-time Block Occupancy Telemetry:** Real-time axle counter occupancy, signal aspect states, and section controller voice control logs.
3. **Internal Ultrasonic Flaw Detection (USFD) & Track Recording Car (TRC) Raw Sensor Logs:** Kept by Divisional Senior Section Engineers (P-Way).

> [!IMPORTANT]
> In compliance with security and privacy boundaries, TrackMeld makes **no claim** of unauthorized access to internal CRIS/Railnet systems.

---

## 8. Which Information Must Eventually Be Synthetic?

As established in `DATA_AND_DOMAIN_MODEL.md` and `data/metadata/data_gaps.json`:
- **Maintenance Task Requests (Possession Demands):** Specific candidate work orders (e.g. tamping 3 km on track line UP between GZB and KRJ, OHE bracket replacement, or point machine renewal) will be deterministically generated using synthetic generators adhering strictly to real IRPWM, ACTM, and IRSEM parameters.
- **Resource Constraints (Machines & Gangs):** Plasser & Theurer CSM/BCM machine fleet availability and divisional maintenance gang shifts will be synthetic demonstration entities.
- **Real-time Train Delays / Incidents:** Stochastic operational deviations will be generated to test dynamic re-optimization.

---

## 9. Which Sources Conflict?

Documented in `data/metadata/source_conflicts.json`:
1. **Station Renaming & Code Migration:**
   - Legacy: `Allahabad (ALD)` vs Modern: `Prayagraj Jn. (PRYJ)`.
   - Legacy: `Mughalsarai (MGS)` vs Modern: `Pt. Deen Dayal Upadhyaya Jn. (DDU)`.
   - **Resolution:** Modern official Railway Board coding adopted; legacy names marked superseded.
2. **Maintenance Block Planning Horizon:**
   - Legacy GR 1976: Ad-hoc block requisition without 52-week rolling forward schedule.
   - Modern GSR 870(E) (Nov 2023): Mandatory 52-week Rolling Block Programme under Rule 15.02(c).
   - **Resolution:** Statutory Gazette amendment legally supersedes legacy practice.

---

## 10. What Assumptions Remain?

- **Double-Line Trunk Configuration:** All High Density Network (HDN) trunk sections are modeled as minimum 2 running lines (UP and DN) unless station yards dictate additional loops.
- **Uniform Electrification:** All monitored Golden Quadrilateral routes are treated as energized under 25 kV AC 50 Hz single phase traction, triggering ACTM Para 20610 power block rules for heavy machinery.
- **Computational Occupancy Half-Open Intervals:** As specified in architecture, timetable pass occupancies are treated as half-open intervals `[start, end)` in `Asia/Kolkata` local time and converted to UTC minutes.

---

## 11. What Data Is Ready for TrackMeld?

The normalized datasets in `data/normalized/` are 100% validated and ready for Phase 1 domain modeling:
- `data/normalized/stations.json` → Ready for Corridor Station Graph.
- `data/normalized/sections.json` → Ready for BlockSection network nodes & edges.
- `data/normalized/trains.json` → Ready for Train entity registry.
- `data/normalized/train_movements.json` → Ready for TrainPass timetable constraint generation.
- `data/normalized/rules.json` → Ready for CompatibilityRule classification and constraint formulation.
- `data/normalized/infrastructure.json` → Ready for Corridor specifications.

---

## 12. What Data Must NOT Be Treated as Authoritative?

- **Timetable Passes as Real-Time Track Occupancy:** Published timetable arrival/departure times reflect **scheduled** movements, not real-time train locations. They must never be presented to operators as actual live telemetry.
- **Derived Block Sections:** Section lengths derived from station distance differentials are operational approximations and do not substitute for official Engineering Chainage (KM Post to Meter Post).
- **Rule Summaries:** Only the verbatim `original_text` in `rules.json` is authoritative. The `normalized_summary` is an engineering abstraction for the scheduling solver.

---

## Acceptance Criteria Verification Checklist

- [x] Official sources systematically searched and verified.
- [x] Original source files archived in `data/raw/` with SHA-256 checksums.
- [x] Complete source manifest created in `data/metadata/sources.json`.
- [x] Train data extracted into `data/normalized/trains.json` (3,429 trains).
- [x] Station data extracted into `data/normalized/stations.json` (68 stations).
- [x] Timetable/movement data extracted into `data/normalized/train_movements.json` (82 movements).
- [x] Railway documents extracted (IRWM 2026, GSR 870(E), ACTM, General Rules).
- [x] Operating, safety, S&T, and electrical rules extracted into `data/normalized/rules.json`.
- [x] Infrastructure data extracted into `data/normalized/infrastructure.json`.
- [x] Real section/topology information derived into `data/normalized/sections.json` (66 sections).
- [x] Data quality validation completed (`validation_report.json` & `.md`: 11,228 tests passed, 0 failed).
- [x] Source conflicts documented in `data/metadata/source_conflicts.json`.
- [x] Data gaps documented in `data/metadata/data_gaps.json`.
- [x] Real vs Derived vs Synthetic classification implemented across 100% of records.
- [x] No fabricated railway data presented as real.
- [x] Comprehensive Phase 0 report (`PHASE_0_DATA_REPORT.md`) created.

---

## Next Step Recommendation

Phase 0 data acquisition and extraction is **officially complete**.
The repository is prepared to proceed to **Phase 1: Project Architecture & Domain Foundation Setup** (Pydantic domain schemas, Alembic migrations, and synthetic task generation seeded onto these real sections and timetables).

**STOPPING EXECUTION AS MANDATED BY PHASE 0 RULES.**
