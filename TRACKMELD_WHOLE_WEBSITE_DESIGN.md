# TrackMeld --- Whole-Website Product & UI Design Specification

**Audience:** Product owner, UX/UI designer, frontend engineers, QA\
**Status:** Proposed design direction. Verify against the current
repository before implementation.\
**Repository:** `D:\Trackmeld`

## 1. Purpose

TrackMeld is a railway maintenance planning, optimization, validation,
and governance platform. It should feel like a calm, high-density
railway operations workstation---not a generic analytics dashboard. Each
page should have a clear job, every panel should support a user
decision, and the interface must distinguish real operational data from
synthetic, demo, stale, unverified, or unavailable data.

This is a design contract, not a claim that the current application
already implements every behavior described here.

## 2. Core principles

1.  **Purpose before decoration:** each route has one primary user goal
    and a clear hierarchy.
2.  **One source of truth:** shared scenario, corridor, selected entity,
    plan, validation, and approval state must not drift.
3.  **Share primitives, preserve semantics:** reuse behavior and visual
    foundations without merging unrelated workflows.
4.  **Purposeful maps:** a map must be a primary workspace,
    planning-specific view, or compact contextual preview.
5.  **Visible operational truth:** clearly distinguish REAL,
    SYNTHETIC/DEMO, UNVERIFIED, STALE, UNAVAILABLE, IDLE, and BLOCKED
    where the data supports these states.
6.  **Human governance remains human:** solver completion and validation
    do not equal approval; preserve Four-Eyes governance and
    authorization.
7.  **Copilot is read-only:** it explains available evidence and does
    not mutate plans or approve work.
8.  **Intentional scrolling:** every page and bounded component has a
    clear scroll owner; critical content must remain reachable.
9.  **Progressive disclosure:** show the most important status and next
    action first.
10. **No fake certainty:** loading, empty, error, stale, synthetic, and
    unavailable states must be honest.

## 3. Visual language

### Mood and surfaces

Use a restrained industrial dark theme: deep navy/near-black
backgrounds, layered slate/navy surfaces, subtle borders, readable muted
metadata, cyan/blue focus and selection, blue primary actions,
green/teal success, amber warning/unverified, and red error/conflict.
Prefer existing design tokens and Tailwind conventions rather than
creating a parallel design system.

Avoid excessive glows, decorative borders, nested cards, and
terminal-style typography on every label. Use monospaced text
selectively for IDs, hashes, track codes, solver diagnostics, and
compact system telemetry.

### Hierarchy and spacing

Use one clear page title, concise section headings, readable primary
values, and subdued but accessible metadata. Align panel edges to a
consistent grid. Remove redundant labels and repeated metrics when they
do not support a separate decision. Keep desktop layouts spacious enough
to distinguish the primary work surface from supporting information;
reflow instead of compressing on small screens.

### Shared interaction patterns

Standardize buttons, status badges, alerts, filters, tables, inspectors,
dialogs, loading states, empty states, and error states. Shared patterns
should have consistent behavior and accessibility, but allow semantic
variants. Icon-only controls need accessible names; important
information must not exist only in a tooltip.

## 4. Application shell

### Top bar

Provide brand/navigation control, current scenario, corridor or
operational context when relevant, planning horizon when relevant,
provenance badge, search/command access if supported, notifications, and
account state. Keep the bar compact. At narrow widths, collapse
secondary context rather than clipping or crowding controls.

### Sidebar

Use clear labels, recognizable icons, keyboard-accessible navigation,
visible active state, and tooltips when collapsed. The proposed core
routes are Overview, Planning, Work Orders, Network, Governance, Audit,
and Copilot. Inventory actual routes before changing navigation; do not
remove or add entries solely to match this proposal.

### Status bar

Summarize backend/worker/validator status and relevant task or
provenance details only when the values are available and accurate.
Distinguish IDLE from UNAVAILABLE and UNKNOWN. The status bar must not
cover the final row of content or block page scrolling. Avoid duplicate
warning banners unless the repetition supports a separate decision.

### Scroll contract

Use an explicit model for each route: - **Document/page scroll:**
long-form or stacked page content. - **Main-region scroll:** fixed shell
navigation with the central page region scrolling. - **Component
scroll:** bounded tables, chat histories, inspectors, maps, or
timelines. - **Hybrid scroll:** page scrolling plus intentional bounded
regions for long component content.

Do not apply `overflow-hidden`, `h-screen`, or nested `overflow-y-auto`
without a reason. Test short desktop heights as well as mobile widths.
Avoid competing scrollbars and ensure the last row, inspector action,
dialog footer, and page footer remain reachable.

## 5. Page-purpose specification

Validate this proposed division against the current code and product
workflow before implementing changes.

### Overview --- operational summary

**Question:** What needs attention now?

Show prioritized alerts/action items, a small set of meaningful
operational indicators, planning/validation/governance summaries, and
recent evidence when it helps a decision.

**Map policy:** at most a compact contextual preview when it helps
explain an alert or corridor status. Do not duplicate the full Network
map or Planning workstation. Link to the specialist workspace with
context preserved where supported.

Avoid repeating every metric from specialist pages or showing synthetic
values without provenance.

### Planning --- plan creation and evaluation

**Question:** Can we create a feasible maintenance plan, understand its
trade-offs, and prepare it for independent review?

Core flow: choose scenario/corridor/horizon; inspect tasks and
constraints; run optimization; inspect the candidate schedule;
understand conflicts; validate; compare candidates where useful; hand
the candidate into authorized human governance.

A solver run, candidate plan, successful validation, or completed
pipeline stage must never be presented as approval. Action availability
must reflect actual backend state and permissions.

Nine modes must remain meaningful: - `INTEGRATED` --- 3-Panel
Workstation. - `MAP` --- Railway Map. - `TIMESPACE` --- Time-Space. -
`TIMELINE` --- Corridor Timeline. - `TASKS` --- Tasks Queue. -
`CONFLICTS` --- Conflicts. - `VALIDATION` --- Validation. -
`DIAGNOSTICS` --- Diagnostics. - `COPILOT` --- Copilot Explainer.

**Shared across modes:** scenario/corridor/horizon, candidate plan/run
state, compatible entity selection, task/section references, validation
state and provenance, consistent inspector primitives, and consistent
loading/error/empty patterns.

**Mode-specific:** map layers; time-space chart encoding; timeline
scheduling; task triage; conflict evidence; validation rules; solver
diagnostics; and read-only Copilot explanations.

**Integrated 3-panel layout** - Left/context panel: task queue or
planning inputs. - Center: the primary planning visualization. - Right:
selected entity/task inspector and relevant actions. - Center receives
the strongest visual emphasis. - Avoid repeating the same metrics,
filters, and controls in all three panels. - Keep inspector selection
synchronized with the selected entity. - Preserve page-level vertical
scrolling; do not restore the removed Expand/full-screen control or
obsolete state. - Reflow/stack at narrow widths instead of squeezing
three columns into mobile. - Component scrolling is allowed for long
tables/details but must not trap users away from the page. - At short
heights, the user must be able to reach the bottom of the task list,
visualization, and inspector actions.

**Planning map policy:** use a planning-aware adapter on shared map
primitives. Planning adds task/plan context and specialized overlays; it
should not duplicate all Network exploration workflows. Label
schematic/synthetic map content honestly.

### Network --- geographic railway exploration

**Question:** What does the network look like, and how are its entities
connected?

Make this the primary geographic exploration workspace. Include the
supported railway map, station/section/track/corridor layers, legend,
filters, selection, and topology relationships where available.

Share the map engine, layer primitives, and selection contract with
Planning where appropriate. Network owns broad geographic exploration;
Planning owns schedule and maintenance-plan interpretation. Do not
duplicate solver controls or planning-specific approval actions here.
Never invent geographic detail when data is missing.

### Work Orders --- maintenance record management

**Question:** Which work orders need inspection or management?

Prioritize a searchable/filterable work-order table or list,
status/priority/time window/location fields where supported, selected
work-order details, related tasks/evidence, and a path into Planning
when relevant.

**Map policy:** use only a small contextual location preview if it
materially helps identify the work order. Do not mount a full Network
map by default. Keep work-order semantics distinct from planning
task-queue semantics.

### Governance --- independent review and approval

**Question:** Is this candidate eligible for review, and what decision
was recorded?

Prioritize the review queue, candidate/version context, validation
summary, reviewer/approver identity and permissions, Four-Eyes
separation, decision actions when authorized, and decision evidence.

A contextual map is optional only when it materially supports
understanding operational impact. Do not duplicate a full
Network/Planning map by default. Never weaken permissions, state
transitions, reviewer separation, or audit integrity to simplify UI.

### Audit --- traceability and evidence

**Question:** What happened, when, by whom, and against which
version/evidence?

Prioritize searchable audit events, actor, timestamp, action, target,
outcome, plan/scenario references, evidence hashes, filters, and a
readable selected-event detail.

No full map by default. Use a map link or compact reference only when an
event's geographic target helps investigation. Preserve
selection/copying for IDs and hashes. Distinguish recorded facts from
derived summaries.

### Copilot --- read-only explanation

**Question:** What does the available evidence mean?

Provide a conversation/explanation surface, grounded references to
available scenario/plan/validation/audit evidence, and honest
loading/error/no-evidence states. Clearly disclose synthetic, stale,
unavailable, or incomplete context.

No full map by default. A small contextual reference or link is
appropriate only when it explains a specific geographic question.
Copilot must not mutate plans, execute privileged actions, approve work,
or claim evidence it did not consult.

## 6. Map architecture

### Target structure

Investigate a shared map foundation with explicit workflow adapters: 1.
**Engine adapter:** renderer lifecycle, viewport, resize behavior. 2.
**Controls:** zoom, pan/reset, layer toggles, legend, selection. 3.
**Railway primitives:** station, section, track, corridor, train, task,
and supported overlays. 4. **Selection contract:** selected entity
type/ID and supported navigation/context. 5. **Workflow adapters:**
Network explorer, Planning context, compact preview. 6.
**Provenance/state:** source, synthetic/demo status, loading/error/empty
state, layer availability.

This is a target for investigation, not a mandate to rewrite the current
implementation immediately.

### Map classifications

For every map occurrence, record route/component, full map vs preview,
engine, data source, layers, interactions, state owner,
error/empty/provenance behavior, and distinct value. Classify it as: -
Primary map workspace. - Planning-specific map. - Contextual preview. -
Redundant implementation. - Unclear purpose requiring a product
decision.

Repeated appearance alone does not prove redundancy. A preview should be
visually subordinate and have a clear purpose. Prefer named variants
such as `network-explorer`, `planning-context`, and `compact-preview`
over many unrelated boolean props. Keep viewport state local unless
cross-route persistence is a demonstrated requirement.

### Required map states

Support loading, real data, synthetic/demo data, empty result, partial
layer availability, backend error, stale data, and schematic/approximate
geography. Never imply synthetic coordinates or schematic geometry are
verified GIS data.

## 7. Component architecture

### Reuse candidates to verify

Inspect the actual implementations before extracting anything.
Candidates include: - Page header/contextual actions. -
Status/provenance badges and operational alerts. - Filter bar and
active-filter summary. - Inspector shell with stable header, tabs,
content scroll, and close behavior. - Table primitives for sorting,
selection, pagination, and responsive behavior. - Loading, empty, and
error states. - Map controls, legend, and railway layer primitives. -
Entity/evidence references. - Metric cards only where metrics support a
decision.

These are investigation candidates, not a checklist of components that
must all be created.

### Keep domain semantics distinct

Do not force these into one generic component merely because they look
similar: - Work-order management table vs planning task queue. -
Candidate-plan validation vs work-order validation. - Governance
approval card vs generic status card. - Solver diagnostics vs
user-facing conflict explanation. - Audit event detail vs operational
entity inspector. - Network map explorer vs Planning map adapter. -
Copilot suggestion vs executable action.

Share visual primitives and low-level behavior when it is genuinely
common. A small amount of orchestration duplication can be safer than a
universal abstraction.

### Component contract

For each shared component, document its purpose, inputs/outputs, state
ownership, supported variants, loading/error/empty behavior,
accessibility requirements, mutation capability, and domain invariants.
Avoid components with dozens of flags or unrelated responsibilities.

## 8. Shared state and data ownership

Use this ownership model as a starting point and verify it against
current APIs and code.

  -----------------------------------------------------------------------
  Concept                 Recommended owner       Rule
  ----------------------- ----------------------- -----------------------
  Scenario                App/workspace context   Shared where relevant;
                          or canonical route      clear dependent
                          state                   selections when it
                                                  changes

  Corridor                Workspace context or    Share only where
                          route state             required

  Selected entity         Route/workspace         Share within linked
                          selection contract      panels; avoid unrelated
                                                  routes inheriting stale
                                                  selection

  Map viewport            Local map state by      Persist only with
                          default                 demonstrated need

  Map layers              Map view state          Share within the
                                                  relevant map workflow

  Planning horizon        Planning context        Avoid independent
                                                  copies per mode

  Candidate plan/run      Canonical planning      Local UI state is not
                          API/state               authoritative solver
                                                  output

  Validation              Canonical result keyed  Mark stale or
                          to plan/version         invalidate when
                                                  candidate changes

  Conflicts               Derived from canonical  Do not fabricate
                          plan/validation         independent
                          evidence                authoritative conflicts

  Governance status       Backend-governed state  Never infer approval
                                                  from solver/validation
                                                  completion

  Audit evidence          Canonical audit records Preserve hashes, IDs,
                                                  actor attribution,
                                                  copyability

  Copilot context         Read-only references to Must not become a
                          selected evidence       mutation channel
  -----------------------------------------------------------------------

### Fetching and re-rendering

-   Deduplicate requests only when parameters and freshness requirements
    match.
-   Make loading/error/stale states explicit.
-   Cancel or ignore obsolete requests after scenario/route changes
    where appropriate.
-   Avoid refetching every dataset on every Planning mode switch.
-   Do not cache approval/validation state beyond its plan/version
    validity.
-   Keep API contracts unchanged unless evidence demonstrates a defect
    and the change is approved.
-   Stabilize callbacks/state updates where identity matters; avoid
    context updates with semantically identical values.
-   Keep high-frequency map viewport state local when possible.
-   Test stale selection, repeated mode switching, and identical
    telemetry updates.

## 9. Planning mode matrix

  ---------------------------------------------------------------------------
  Mode              Primary job        Main surface        Must not become
  ----------------- ------------------ ------------------- ------------------
  `INTEGRATED`      Coordinate         Balanced            A wall of
                    preparation and    three-panel         duplicated
                    inspection         workstation         metrics/toolbars

  `MAP`             Understand         Planning-aware      A full copy of
                    geographic         railway map         Network
                    distribution of                        
                    plan assets/tasks                      

  `TIMESPACE`       Inspect train      Time-space chart    A generic map or
                    movement/time                          KPI dashboard
                    relationships and                      
                    occupancy                              

  `TIMELINE`        Inspect            Corridor            A duplicate task
                    maintenance        timeline/Gantt      table plus
                    windows and                            unrelated panels
                    dependencies                           

  `TASKS`           Triage and inspect Task queue/table    A duplicate Work
                    tasks                                  Orders page

  `CONFLICTS`       Understand         Conflict list and   A generic
                    unresolved         evidence            red-alert wall
                    conflicts                              

  `VALIDATION`      Inspect rule       Validation summary  An approval screen
                    checks and         and rule results    or unverified
                    candidate                              green check
                    eligibility                            

  `DIAGNOSTICS`     Understand solver  Solver              A duplicate
                    behavior/runtime   diagnostics/trace   validation panel

  `COPILOT`         Explain candidate  Read-only           A second planning
                    plan and evidence  explanation         controller
  ---------------------------------------------------------------------------

Mode switching should preserve compatible
scenario/corridor/horizon/plan/selection state; reset only state that is
invalid in the new mode; avoid duplicate requests; keep active mode
accessible; and show useful empty/error states. A visualization must not
imply plan validity by itself.

## 10. Page composition and redundancy test

Use this hierarchy where appropriate: 1. Context: page name,
scenario/corridor, provenance. 2. Decision status: the most important
condition or blocker. 3. Primary work surface: map, table, timeline,
queue, evidence list, or conversation. 4. Contextual detail:
inspector/drawer for the selected item. 5. Secondary information:
metrics, metadata, evidence, optional diagnostics.

Do not force every page to contain a map, KPI row, alert banner, filter
row, timeline, and inspector.

For every panel, ask: - What user question does this answer? - What
decision does it enable? - Is the information already visible nearby? -
Is it authoritative or copied? - Could the user reach a specialist route
instead? - Does it belong on this page or only in a preview? - Would
removing it remove unique functionality or evidence?

If no clear answer exists, investigate before retaining it.

## 11. Responsive behavior

Test at minimum: - 1920 × 1080 - 1802 × 786 - 1440 × 900 - 1280 × 720 -
1024 × 600 - 768 × 1024 - 390 × 844 - 320 × 700

Acceptance expectations: - No horizontal page overflow. - No clipped
critical action, final table row, inspector action, or dialog footer. -
No footer/status bar covering content. - Page scroll works when content
exceeds the viewport. - Bounded component scroll is reserved for
genuinely long content. - Planning's three panels reflow on small
widths. - Tables have an intentional narrow-screen pattern. -
Drawers/dialogs remain reachable. - Keyboard focus stays visible and
does not target inaccessible content. - IDs, hashes, diagnostics, and
Copilot evidence remain selectable/copyable. - Sticky headers do not
cover selected rows or focus targets.

Do not claim WCAG compliance based only on viewport tests. Combine
automated accessibility checks with manual keyboard and
assistive-technology review.

## 12. Accessibility

-   Use semantic landmarks and ordered headings.
-   Name icon-only controls.
-   Support keyboard navigation and visible focus.
-   Announce important asynchronous status changes where appropriate.
-   Never rely on color alone for status/provenance.
-   Use native links/buttons for navigation and actions.
-   Manage dialog focus and close behavior.
-   Respect reduced-motion preferences.
-   Make tables accessible and provide text alternatives/summaries for
    visualizations where needed.
-   Do not hide essential information in tooltips alone.

## 13. Operational truth and domain invariants

Use only status states supported by the backend. Do not infer REAL from
absence of a synthetic flag, infer success from HTTP 200, or show READY
when the state is unknown.

Preserve: - Accurate solver lifecycle/outcome. - Constraint and
validation semantics. - Four-Eyes governance. - Reviewer/approver
identity and authorization. - Audit integrity and traceability. -
Read-only Copilot. - Honest error/unavailable states.

## 14. Proposed refactor order

### P0 --- Correctness and reachability

-   Preserve and test page/component scrolling.
-   Test every Planning mode at short heights.
-   Verify removed Expand/full-screen controls and obsolete state remain
    absent.
-   Verify provenance and blocked actions are truthful.
-   Test shared-state loops and stale selections.

### P1 --- Purpose and redundancy

-   Complete route/page-purpose matrix.
-   Inventory all full-size maps, previews, charts, tables, inspectors,
    and alerts.
-   Identify redundant panels that enable no unique decision.
-   Clarify Overview, Network, Planning, Work Orders, Governance, Audit,
    and Copilot responsibilities.
-   Get product-owner approval for map placement/navigation changes.

### P2 --- Shared primitives

-   Consolidate exact duplicates and clear shared primitives only.
-   Define map variants and selection contracts.
-   Standardize inspector shell, provenance/status, and
    loading/error/empty states.
-   Keep domain-specific task, work-order, validation, governance, and
    audit contracts distinct.

### P3 --- State and fetching

-   Document canonical owners.
-   Reduce duplicate requests where parameters/freshness match.
-   Test mode switching, stale selection, and state identity.
-   Avoid API contract changes without evidence and approval.

### P4 --- Visual refinement

-   Refine hierarchy, typography, density, spacing, and responsive
    behavior.
-   Remove unnecessary nesting and duplicate labels.
-   Improve loading/error/empty states.
-   Validate keyboard and accessibility behavior.

## 15. Product decisions requiring approval

Do not silently decide: 1. Whether Overview should show a map preview.
2. Whether Work Orders needs a map preview or only a Network link. 3.
Whether Governance needs a candidate-impact map. 4. Which
layers/interactions Planning `MAP` mode requires. 5. Whether map
viewport/layers persist across routes. 6. Which selections are global
versus route-specific. 7. Which selections survive Planning mode
changes. 8. Which metrics belong on Overview versus specialist routes.
9. Whether any route/mode should be merged, hidden, or removed. 10.
Whether changing map engines/libraries is justified.

For each, present evidence, options, trade-offs, and a recommendation.

## 16. Verification checklist

For every refactor: - \[ \] Exact source evidence identifies the
issue. - \[ \] Page purpose/workflow is documented. - \[ \] Domain
semantics are preserved. - \[ \] REAL/SYNTHETIC/DEMO/stale/unavailable
states remain accurate. - \[ \] Authorization and Four-Eyes remain
unchanged. - \[ \] Audit IDs/hashes and actor attribution remain
intact. - \[ \] Copilot remains read-only. - \[ \] Page and component
scrolling are tested. - \[ \] Relevant Playwright tests pass. - \[ \]
`npx tsc --noEmit` passes. - \[ \] `npm run lint` completes and warnings
are reported honestly. - \[ \] `git diff --check` passes. - \[ \]
`git status --short` and `git diff --stat` are reviewed. - \[ \]
`.agents/` and `skills-lock.json` remain untouched. - \[ \] No
commit/push, database reset/reseed, or destructive database action
occurs without explicit authorization.

Do not use component-count reduction, a subjective quality score, or
route-load tests as proof of architecture quality.

## 17. Engineering execution protocol

1.  Reconnaissance: inventory routes, components, maps, requests, state
    owners, and navigation.
2.  Evidence report: document page purposes, map duplication
    classifications, reuse opportunities, and risks.
3.  Product decisions: request approval for changes to page
    responsibilities, map placement, or navigation.
4.  Small corrections: implement only low-risk, evidence-backed changes.
5.  Targeted refactors: consolidate exact duplicates and well-defined
    primitives.
6.  Regression verification: run focused Playwright tests, typecheck,
    lint, and diff checks.
7.  Independent review: check domain correctness, abstraction quality,
    regressions, and scope.
8.  Handoff: list changed files, decisions, raw test results, unresolved
    issues, and blocked checks.

### Repository safeguards

-   Repository: `D:\Trackmeld`.
-   Preserve `.agents/` and `skills-lock.json` completely.
-   Preserve user changes and the recent Planning scrolling repair.
-   Do not commit or push.
-   Do not reset/reseed or destructively alter the database.
-   Do not change Docker internals.
-   Do not fabricate tests, findings, or source behavior.
-   If a service is unavailable, report verification as blocked rather
    than passed.

## 18. Design north star

**TrackMeld should be one coherent railway operations product with
specialized workspaces---not a collection of pages competing to show the
same map, status cards, and controls.**

Network explains railway geography. Planning explains how maintenance
work fits into time, resources, and constraints. Work Orders manages
maintenance records. Governance manages independent human decisions.
Audit preserves evidence. Copilot explains available evidence without
changing it. Overview helps users decide where to go next.

Share the foundations. Keep workflows distinct. Make operational truth
unmistakable. Ensure every important action and the last row of content
remain reachable.
