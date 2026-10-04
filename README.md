# TrackMeld

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18-4169E1.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Google OR-Tools](https://img.shields.io/badge/Google%20OR--Tools-CP--SAT-orange.svg)](https://developers.google.com/optimization)
[![Next.js](https://img.shields.io/badge/Next.js-16%20App%20Router-black.svg?logo=next.js&logoColor=white)](https://nextjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6.svg?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Playwright](https://img.shields.io/badge/Playwright-E2E%20Verified-2EAD33.svg?logo=playwright&logoColor=white)](https://playwright.dev/)
[![Tests Passing](https://img.shields.io/badge/Tests-472%20Passing-brightgreen.svg)]()

> **Decision-support platform for railway maintenance possession planning, constraint programming, and four-eyes operational governance.**

---

## 1. Overview

Railway infrastructure maintenance requires taking tracks out of commercial service for fixed durations—known as **engineering possessions** or **track blocks**. In high-density mixed-traffic corridors, allocating these windows is one of the most operationally demanding combinatorial challenges in transport logistics.

Track maintenance cannot be scheduled in isolation. Every possession request directly contends with scheduled commercial passenger and freight timetables, locomotive and gang availability, adjacent track safety clearances, electrical traction isolations (OHE power blocks), and physical track topology.

### The Operational Problem

When possession scheduling relies on manual deliberation or fragmented spreadsheets:
- **Possessions are canceled late**, idling specialized heavy machinery (e.g., track tamping and ballast cleaning machines) and work gangs.
- **Timetable punctuality collapses**, as unplanned speed restrictions (cautions) propagate cascading delay across contiguous blocks.
- **Adjacent-track hazards arise**, when maintenance gangs work alongside live running lines without enforced safety buffers.

TrackMeld solves this problem by formulating possession planning as a rigorous mathematical optimization task paired with an independent safety auditing engine and mandatory human approval controls.

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    OPERATIONAL GOVERNANCE CHAIN                                         │
│                                                                                                         │
│  [Rules Classify] ──► [CP-SAT Optimizes] ──► [Independent Validator] ──► [Human Reviews] ──► [Approved] │
│                                                                                                         │
│  OPTIMAL ≠ APPROVED    │    FEASIBLE ≠ APPROVED    │    VALID ≠ APPROVED    │    CREATOR ≠ APPROVER     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Architecture

TrackMeld enforces strict separation between optimization, safety auditing, persistence, and human authorization.

```mermaid
flowchart TD
    subgraph DataLayer["1. Data & Topology Layer"]
        Postgres[(PostgreSQL 18 DB)]
        Corridors["Corridors & Stations\n(NDLS - GZB - ALJN)"]
        Tracks["Physical Running Tracks\n(132 Tracks / 264 Endpoints)"]
        Topology["Topology Graph\n(Nodes & Turnout Connections)"]
        Tasks["Maintenance Work Orders\n(P-Way, S&T, TRD)"]
        Timetable["Commercial Timetable\n(Train Passes & Services)"]

        Postgres --> Corridors & Tracks & Topology & Tasks & Timetable
    end

    subgraph CoreEngine["2. Deterministic Engine Pipeline"]
        Snapshot["Planning Snapshot\n(SHA-256 Content-Hashed)"]
        Router["Deterministic Topology Router\n(Physical Traversal Resolution)"]
        CPSAT["Google OR-Tools CP-SAT\n(Interval Variables & NoOverlap)"]
        Validator["Independent Safety Validator\n(12 Invariant Checks)"]
        Diagnostics["Causal Diagnostics\n(Unscheduled Reason Attribution)"]

        Corridors & Tracks & Tasks & Timetable --> Snapshot
        Topology --> Router
        Router --> Snapshot
        Snapshot --> CPSAT
        CPSAT --> Validator
        CPSAT --> Diagnostics
    end

    subgraph ServiceLayer["3. Application & Worker Layer"]
        FastAPI["FastAPI Async API Server\n(/api/v1 REST Endpoints)"]
        Worker["Background Planning Worker\n(Job Claiming & Timeout Trapping)"]
        Governance["Four-Eyes Governance Engine\n(RBAC State Machine & Audit Log)"]
        Copilot["Read-Only AI Copilot\n(Typed Diagnostic Tools)"]

        CPSAT & Validator --> Worker
        Worker --> Postgres
        FastAPI --> Governance
        Governance --> Postgres
        FastAPI --> Copilot
    end

    subgraph PresentationLayer["4. Operational Workstation UI"]
        NextJS["Next.js 16 (App Router + Turbopack)"]
        TimeSpace["Multi-Track Time-Space Canvas\n(Distance vs. Time Conflict Grid)"]
        ReviewUI["Four-Eyes Review & Promotion\n(Audit History & Invariant Badging)"]
        CopilotChat["Grounded Copilot Drawer\n(Read-Only System Diagnostic Chat)"]

        FastAPI <==> NextJS
        NextJS --> TimeSpace & ReviewUI & CopilotChat
    end
```

---

## 3. Key Technological Innovations

### 1. Deterministic Planning Snapshots (SHA-256)
Optimization never operates directly against live mutating tables. Instead, an in-memory `PlanningSnapshot` is assembled, normalized, sorted, and fingerprinted with a 64-character SHA-256 hash. Any permutation of input records yields an identical fingerprint, ensuring 100% reproducible schedule outcomes across environments.

### 2. Track-Aware Mathematical Optimization (Google OR-Tools CP-SAT)
Unlike naive interval schedulers that lock entire corridor sections, TrackMeld provides a **track-aware conservative optimization engine**:
- **Discrete Interval Variables**: Models maintenance tasks and train occupancies as native CP-SAT interval variables.
- **Disjunctive Multi-Track Constraints**: Enforces `AddNoOverlap` per physical running line (`UP_MAIN`, `DOWN_MAIN`, `LOOP`).
- **Adjacent-Track Safety Buffer**: Automatically injects caution orders and dynamic safety margins on adjacent lines when heavy on-track machinery is scheduled.
- **Whole-Section Fallback**: Automatically degrades to whole-section reservation whenever track assignment metadata is incomplete or ambiguous.

### 3. Deterministic Topology Routing
Commercial passenger timetables specify station stop times, not switch positions. TrackMeld's `DeterministicTopologyRouter` traverses physical `TrackEndpoint` and `TopologyConnection` entities to resolve timetable movements into explicit, timestamped `TrainTraversal` segments with track assignments.

### 4. Independent Safety Validator (12 Verification Rules)
TrackMeld does not trust the optimizer as the sole authority. An independent verification service audits candidate plans against 12 strict safety rules without sharing internal solver heuristics or state:
- Same-track train/maintenance collision detection
- Adjacent-track clearance and caution adherence
- Task-to-task spatial overlap protection
- Crew, gang, and fleet capacity limits
- Work order earliest-start and latest-finish deadline adherence

### 5. Four-Eyes Human Governance & Immutable Audit Log
No algorithm or AI agent can authorize a plan. Candidate plans transition through an explicit relational state machine:
`CREATED` → `SUBMITTED` → `APPROVED` / `REJECTED`.
- **Database-Level Segregation**: Enforces `CREATOR ≠ APPROVER` (the user who triggers a run cannot approve it).
- **Append-Only Audit Ledger**: Persists actor identity, role, timestamp, transition state, and mandatory justification comments.

### 6. Read-Only Grounded AI Copilot
The embedded AI Copilot is strictly bounded:
- It has **zero write permissions** and cannot create, modify, or approve plans.
- It queries the system exclusively through typed inspection tools returning deterministic structured data.
- If evidence is absent, it reports the gap rather than hallucinating train paths.

---

## 4. Technology Stack

| Layer | Technologies |
|---|---|
| **Backend & Optimization** | Python 3.11+, FastAPI, Google OR-Tools (CP-SAT), Pydantic v2, SQLAlchemy 2.0 (AsyncIO), Alembic |
| **Database** | PostgreSQL 18+ with compound operational indexes (`pg_trgm`, `btree`) |
| **Frontend Workstation** | Next.js 16 (React 19, Turbopack), TypeScript 5, Tailwind CSS, Lucide Icons |
| **Testing & QA** | Pytest, Pytest-AsyncIO, Playwright (Chromium/Firefox/WebKit E2E), ESLint, TSC |

---

## 5. Quick Start & Setup

### Prerequisites
- **Python 3.11+**
- **Node.js 20+** and **npm**
- **PostgreSQL 18+**

### 1. Clone & Configure Environment

```bash
git clone https://github.com/your-username/trackmeld.git
cd Trackmeld

# Create your local environment configuration
cp .env.example .env
```

### 2. Backend Setup & Migrations

```bash
# Set up Python virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1

# Install backend dependencies
pip install -r backend/requirements.txt

# Run database migrations
cd backend
alembic upgrade head
cd ..

# Seed synthetic corridor data (NDLS-GZB-ALJN)
python -m backend.app.cli.seed
```

### 3. Start the Background Worker & API Server

In separate terminal sessions (or background processes):

```bash
# Terminal 1: Background planning job worker
python -m backend.app.services.planning_worker

# Terminal 2: FastAPI application server
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

API documentation will be accessible at: `http://127.0.0.1:8000/docs`

### 4. Frontend Workstation Setup

```bash
cd frontend
npm install
npm run dev
```

The operational workstation will be running at: `http://localhost:3000`

---

## 6. Role-Based Access Control (RBAC)

TrackMeld enforces role-based authorization headers for all mutations and reviews:

| Role | Default Header Token | Permissions |
|---|---|---|
| **Planner** | `Bearer demo-planner-token` | Ingest work orders, configure parameters, trigger CP-SAT planning runs. |
| **Approver** | `Bearer demo-approver-token` | Review candidate plans, inspect validator findings, issue Four-Eyes approval or rejection. |
| **Admin** | `Bearer demo-admin-token` | Manage system configuration, reset stalled worker jobs. |
| **Viewer** | `Bearer demo-viewer-token` | Read-only access to corridors, timetables, and approved plans. |

---

## 7. Verification & Automated Test Suite

TrackMeld maintains 100% pass rates across **472 automated tests**, spanning low-level discrete solver mathematics, database integrity, and full-stack browser workflows:

```
================================== TEST SUMMARY ==================================
Backend Unit Tests               : 310 passed (Pytest)
Backend Integration & API Tests  : 148 passed (Pytest + PostgreSQL)
Browser E2E User Journeys        :  14 passed (Playwright)
----------------------------------------------------------------------------------
Total Automated Test Suite       : 472 passed (0 failures, 0 regressions)
TypeScript Static Check          : Clean (0 errors)
ESLint Code Quality              : Clean (0 errors)
==================================================================================
```

### Running the Test Suite

```bash
# Run all backend unit and integration tests
pytest tests/ -v

# Run the Playwright browser E2E test suite
cd frontend
npx playwright test
```

---

## 8. Responsible AI & Domain Boundaries

- **Prototype Decision Support**: TrackMeld is an advanced decision-support prototype built for maintenance planning and operational scheduling. It is **not** an operational railway interlocking or live signalling system.
- **Synthetic Data Provenance**: All corridor topology, station names, train numbers, and maintenance schedules bundled with this repository are synthetic demo datasets created for reproducibility.
- **Human Authority**: The system adheres to the iron rule: *Rules classify, optimization schedules, independent validator verifies, human approves, and AI explains.* Automated systems cannot sign off on operational possessions.

---

## 9. Documentation Index

- **[System Architecture Reference](docs/TRACKMELD_FINAL_ARCHITECTURE.md)**: Deep dive into the mathematical formulation, topology graph structure, and state machine.
- **[Design System Specification](DESIGN_SYSTEM.md)**: Visual language, time-space graph standards, and dark-theme tokens.
- **[Historical Phase Archive](docs/archive/README.md)**: Full archive of 40+ implementation reports across all 21 development phases.

---

## 10. License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
