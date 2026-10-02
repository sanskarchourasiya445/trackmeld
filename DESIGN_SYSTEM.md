# TrackMeld Design System

**Visual direction:** Premium infrastructure software × railway operations center × cinematic railway network at night.  
**Primary goal:** High-quality product experience with operational clarity, not a generic AI dashboard.

## 1. Design principles

1. **Legibility over spectacle.** Planning timelines, task states, conflicts, and evidence must be easy to scan.
2. **Dark, precise, restrained.** Use graphite surfaces, white typography, and electric blue for primary interaction.
3. **Visuals explain the system.** Network and timeline visuals should teach the planning model, not merely decorate the page.
4. **Motion communicates state.** Animate route activation, transitions, progress, and selection; avoid constant distracting movement.
5. **Progressive enhancement.** The interface remains usable without WebGL, animation, or the Copilot.
6. **Truthful presentation.** Clearly distinguish synthetic demo data, calculated results, assumptions, and verified sources.

## 2. Color tokens

```css
:root {
  color-scheme: dark;

  --tm-bg: #0A0A0A;
  --tm-bg-pure: #000000;
  --tm-surface: #141418;
  --tm-surface-elevated: #18181C;
  --tm-surface-hover: #1E1E24;

  --tm-border: #29292F;
  --tm-border-subtle: #202024;

  --tm-text-primary: #F5F5F5;
  --tm-text-secondary: #A1A1AA;
  --tm-text-muted: #71717A;

  --tm-accent: #4C87E7;
  --tm-accent-bright: #3B82F6;
  --tm-accent-soft: rgba(76, 135, 231, 0.12);
  --tm-accent-glow: rgba(76, 135, 231, 0.20);

  --tm-success: #35B779;
  --tm-warning: #F4B740;
  --tm-danger: #F06464;
  --tm-info: #75A7F7;
}
```

Semantic colors must not be the only indication of state; pair them with labels/icons/patterns. Check text and interactive contrast, including subdued secondary text.

## 3. Typography

- Use a modern sans-serif such as Geist, Inter, or the repository's existing equivalent.
- Use tabular numerals for metrics, timestamps, durations, and IDs where available.
- Use a clear scale: display, page title, section title, body, compact label, metadata.
- Keep long explanatory copy at a comfortable line length.
- Reserve uppercase tracking for small section labels, not paragraphs.
- Do not use oversized typography in dense operational workspaces.

## 4. Layout and spacing

- Use a consistent 4px base spacing scale.
- Landing page: generous whitespace, strong editorial hierarchy, full-width cinematic railway scene, restrained supporting sections.
- Operations workspace: denser, grid-aligned, with clear separation between navigation, task list, timeline, inspector, and diagnostics.
- Use borders and surface contrast before shadows.
- Avoid rounding every container. Use modest radii consistently: small controls, medium panels, larger feature surfaces.
- Maintain responsive behavior; on narrow screens convert multi-column workspace panels into navigable tabs/drawers rather than shrinking them until unusable.

## 5. Motion

### Appropriate
- A train moving slowly along a clearly highlighted route in the landing hero.
- A selected block section becoming highlighted.
- A planning run showing staged progress and final status.
- A panel opening with short opacity/translate transitions.
- Before/after plan transitions that clearly identify a conceptual or computed comparison.

### Avoid
- Constant camera spinning.
- Strong bloom, neon trails, or cyberpunk effects.
- Animating every card on scroll.
- Motion that obscures data or makes the interface feel unstable.
- Fake progress percentages that imply actual solver progress.

### Accessibility
- Respect `prefers-reduced-motion`.
- Provide a static railway illustration fallback if WebGL is unavailable.
- Do not communicate solver status through animation alone.
- Ensure animations can be paused or disabled if they are long-running.

## 6. Landing page structure

1. Small announcement strip identifying TrackMeld as a prototype.
2. Navbar: logo, Product, How It Works, Planning Workspace, About, Demo CTA.
3. Hero: “Smarter maintenance planning for a more reliable railway.”
4. Supporting copy: coordinate maintenance, inspect constraints, compare plans, keep the planner in control.
5. Cinematic 3D railway scene: track, sleepers, stations, signals, overhead structures, train, blue active route, selected maintenance zone.
6. Product preview with the `SYNTHETIC DEMONSTRATION` badge visible near any metrics.
7. Planning problem narrative: requests → constraints → conflicts → feasible windows.
8. Feature sections: network model, compatibility, optimization, explainability, human approval.
9. Workflow section: ingest → validate → baseline → optimize → validate → review → approve.
10. Human-in-the-loop section.
11. Read-only Copilot section.
12. Trust/data-boundary section.
13. Final CTA and footer.

Avoid claiming live integration or displaying unverified impact percentages.

## 7. Application shell

### Primary navigation
- Overview
- Planning
- Scenarios
- Optimization Runs
- Data & Network
- Reports
- Audit
- Settings

Show current scenario/corridor and synthetic-data status in the shell.

### Overview dashboard
- Dataset provenance badge
- Planning horizon and selected scenario
- Task counts and latest run status
- Latest validated plan
- Computed comparison metrics
- Recent audit activity
- Clear path to continue planning

Metrics must be derived from API data, not fixed presentation constants.

## 8. Planning workspace

Use a three-zone desktop layout:
- **Left:** task list and filters.
- **Center:** time-space chart/network timeline.
- **Right or bottom drawer:** selected task, constraints, reason codes, validation, and explanation.

The time-space visualization should show:
- Section/line rows
- Time axis with clear timezone and units
- Train occupancy intervals
- Candidate maintenance intervals
- Conflict markers
- Selected task and its constraints
- Plan status and solver status

Provide zoom, time-range navigation, filtering, and keyboard-accessible selection. Do not use a decorative 3D scene as a substitute for a precise planning chart.

## 9. Status language

Use explicit status labels:
- `DRAFT`
- `QUEUED`
- `RUNNING`
- `VALIDATING`
- `VALIDATED`
- `READY_FOR_REVIEW`
- `APPROVED`
- `REJECTED`
- `SUPERSEDED`
- `INFEASIBLE`
- `FAILED`
- `UNKNOWN`

Do not collapse `FEASIBLE` and `OPTIMAL` into one status. Show solver status and independent validation status separately.

## 10. Component inventory

Create reusable components where repeated behavior exists:
- `AppShell`, `Sidebar`, `TopBar`, `Breadcrumbs`
- `SyntheticDataBadge`, `SourceStatusBadge`, `StatusBadge`
- `MetricValue`, `MetricDelta`, `EmptyState`, `ErrorState`, `LoadingState`
- `TaskTable`, `TaskFilters`, `TaskInspector`
- `TimeSpaceChart`, `TimelineAxis`, `TrainOccupancy`, `MaintenanceInterval`, `ConflictMarker`
- `PlanRunStatus`, `SolverSummary`, `ValidationSummary`
- `ScenarioComparisonTable`, `MetricDefinitionTooltip`
- `RuleEvidence`, `DiagnosticList`, `AuditTimeline`
- `CopilotDrawer`, `EvidenceReference`
- `RailwayScene3D` and `RailwaySceneFallback`

Do not build an abstraction until at least two real use cases justify it.

## 11. Accessibility and responsive behavior

- Semantic landmarks and heading hierarchy.
- Full keyboard navigation and visible focus rings.
- Accessible labels for icon-only buttons.
- Screen-reader status updates for long-running planning jobs.
- Text labels in addition to color.
- Reduced-motion and WebGL fallback.
- Mobile: prioritize summary, task inspection, and status; use separate tabs/drawers for timeline and inspector.
- Do not make hover the only way to reveal critical information.

## 12. Visual quality acceptance checklist

- No overflow or clipped text at supported breakpoints.
- The most important action is visually obvious.
- Synthetic data is labeled before metrics are interpreted.
- Timeline labels, units, and timezone are clear.
- Conflict and validation states are distinguishable without color alone.
- 3D content has a fallback and does not block core tasks.
- Loading, empty, failure, stale, and permission states exist.
- The page does not resemble a generic gradient-heavy AI SaaS template.
