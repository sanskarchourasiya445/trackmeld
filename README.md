# TrackMeld Documentation Pack

**Product:** TrackMeld — Railway Maintenance Planning & Decision Support  
**Context:** SIH 2026 prototype  
**Status:** Initial implementation specification  
**Principle:** **Rules classify. Optimization schedules. Humans approve. AI explains.**

This pack translates the TrackMeld system design into a consistent, implementation-oriented source of truth for a coding agent such as Google Antigravity or Claude Code.

## Documents

| File | Purpose |
|---|---|
| `PRD.md` | Product purpose, users, workflows, scope, requirements, and acceptance criteria |
| `AGENTS.md` | Mandatory instructions for AI coding agents |
| `DESIGN_SYSTEM.md` | Visual identity, UI patterns, motion, accessibility, and screen requirements |
| `ARCHITECTURE.md` | Application boundaries, service responsibilities, API, deployment, and key decisions |
| `DATA_AND_DOMAIN_MODEL.md` | Synthetic-data policy, domain entities, schema guidance, provenance, and validation |
| `IMPLEMENTATION_PLAN.md` | Phased build plan, dependencies, deliverables, and phase gates |
| `DECISIONS_AND_RISKS.md` | Important architectural corrections, assumptions, risks, and decision records |

## Read order

1. `PRD.md`
2. `ARCHITECTURE.md`
3. `DATA_AND_DOMAIN_MODEL.md`
4. `DESIGN_SYSTEM.md`
5. `IMPLEMENTATION_PLAN.md`
6. `AGENTS.md` (keep this at the repository root for coding agents)
7. `DECISIONS_AND_RISKS.md`

## Non-negotiable product boundary

TrackMeld is a **prototype decision-support system**, not a railway-control system. The initial demo uses fictional, reproducible synthetic data. Do not claim live CRIS/BDMS/COA/TMS/TDMS/SMMS integration, real-time operational data, official railway approval, safety certification, or measured operational impact unless those claims are separately verified and authorized.

Public documents can support terminology and research, but a public source is not automatically an approved operational rule. Safety-sensitive rules must carry a verifiable source reference and review status. Until verified, label them as assumptions and do not use them as authoritative safety constraints.

## Source-of-truth rule

These documents describe the intended product. The codebase, migrations, tests, and actual runtime behavior determine what is implemented. When implementation differs from the documents, the coding agent must report the discrepancy and update the relevant document after the change is approved and tested. Do not mark a feature complete just because its UI exists.

## Recommended first action

Create a new repository, put this pack at its root, and ask the coding agent to execute **Phase 0 only** from `IMPLEMENTATION_PLAN.md`. Do not ask it to build the entire product in one pass.
