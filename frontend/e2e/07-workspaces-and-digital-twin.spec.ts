import { test, expect } from '@playwright/test';

test.describe('Phase 21: Six Core Workspaces & 3D Digital Twin Integration', () => {
  test.beforeEach(async ({ page }) => {
    // Intercept planning-runs to return empty list so auth checks succeed cleanly
    await page.route('**/api/v1/planning-runs*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: [] }),
      });
    });
  });

  test('01. Navigation Sidebar contains the 6 canonical workspaces with active corridor telemetry', async ({ page }) => {
    await page.goto('/planning');

    const navSidebar = page.getByRole('complementary', { name: 'Railway Operations Navigation' });
    await expect(navSidebar.getByRole('link', { name: /overview/i })).toBeVisible();
    await expect(navSidebar.getByRole('link', { name: /planning/i })).toBeVisible();
    await expect(navSidebar.getByRole('link', { name: /network/i })).toBeVisible();
    await expect(navSidebar.getByRole('link', { name: /work orders/i })).toBeVisible();
    await expect(navSidebar.getByRole('link', { name: /governance & sign-off/i })).toBeVisible();
    await expect(navSidebar.getByRole('link', { name: /copilot/i })).toBeVisible();

    // Verify Active Corridor Telemetry link in sidebar footer
    const corridorLink = navSidebar.getByRole('link', { name: /Active Corridor/i });
    await expect(corridorLink).toBeVisible();
    await expect(corridorLink).toContainText('NDLS → CNB');
    await expect(corridorLink).toContainText('440 km');
  });

  test('02. /overview renders operational briefing and 4 core situational questions', async ({ page }) => {
    await page.goto('/overview');

    // Verify headline and 4 core questions
    await expect(page.getByRole('heading', { name: 'Railway Operations Situation Briefing' })).toBeVisible();
    await expect(page.getByText('1. WHAT IS HAPPENING?')).toBeVisible();
    await expect(page.getByText('2. WHAT NEEDS ATTENTION?')).toBeVisible();
    await expect(page.getByText('3. IS THE PLAN SAFE?')).toBeVisible();
    await expect(page.getByText('4. DECISION REQUIRED')).toBeVisible();

    // Verify corridor info
    await expect(page.getByText('New Delhi to Kanpur Central, 440 km')).toBeVisible();

    // Verification screenshot at 1440x900
    await page.screenshot({ path: 'test-results/overview-1440x900.png', fullPage: true });
  });

  test('03. /planning renders operational top bar, dominant railway map, entity inspector, and launches 3D Digital Twin modal', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/planning');

    // 1. Verify Top Operational Bar
    await expect(page.getByText('NDLS → CNB (440 km Trunk)').first()).toBeVisible();
    await expect(page.getByText('Scenario A (24h Window)')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Run Optimization' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Validate' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Approve' })).toBeVisible();

    // 2. Verify View Switcher and Dominant Map
    await expect(page.getByRole('button', { name: 'Railway Map' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Time-Space' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Corridor Timeline' })).toBeVisible();

    // 3. Switch to Time-Space view and verify chart renders
    await page.getByRole('button', { name: 'Time-Space' }).click();
    await expect(page.getByText('Corridor Time-Space Diagram')).toBeVisible();
    await expect(page.getByText('72h All')).toBeVisible();

    // 4. Switch back to Railway Map View
    await page.getByRole('button', { name: 'Railway Map' }).click();

    // 5. Verify Contextual Inspector is present
    const inspector = page.getByRole('complementary', { name: 'Contextual Entity Inspector' });
    await expect(inspector).toBeVisible();
    await expect(inspector.getByText('Inspector')).toBeVisible();

    // 6. Launch 3D Digital Twin Inspection Modal
    const launchTwinBtn = page.getByRole('button', { name: 'Inspect Work Zone in 3D Digital Twin' });
    await expect(launchTwinBtn).toBeVisible();
    await launchTwinBtn.click();

    // Verify 3D Digital Twin Modal
    await expect(page.getByText('DIGITAL TWIN INSPECTION')).toBeVisible();
    await expect(page.getByText('PHYSICAL UIC-60 / 25kV OHE MODEL')).toBeVisible();
    await expect(page.getByText('DIGITAL TWIN HUD')).toBeVisible();

    // Verify camera preset buttons
    await expect(page.getByRole('button', { name: 'Cab' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Drone' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Orbit' })).toBeVisible();

    // Switch camera mode to Cab
    await page.getByRole('button', { name: 'Cab' }).click();

    // Screenshot 3D Digital Twin Modal
    await page.screenshot({ path: 'test-results/planning-3d-digital-twin-modal.png' });

    // Close 3D Modal
    await page.locator('button[title="Close inspection"]').click();
    await expect(page.getByText('DIGITAL TWIN INSPECTION')).not.toBeVisible();

    // Screenshot planning workspace at 1440x900
    await page.screenshot({ path: 'test-results/planning-workspace-1440x900.png' });
  });

  test('04. /network displays infrastructure tables and launches digital twin', async ({ page }) => {
    await page.goto('/network');

    // Verify Network Workspace Header & Tabs
    await expect(page.getByRole('heading', { name: 'Railway Network Infrastructure' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Infrastructure Map' })).toBeVisible();
    await expect(page.getByRole('button', { name: /Stations/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Track Sections/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Signals/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Catenary/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Fleet/i })).toBeVisible();

    // Switch to Track Sections tab
    await page.getByRole('button', { name: /Track Sections/i }).click();
    await expect(page.getByText('SEC-01')).toBeVisible();
    await expect(page.getByText('New Delhi – Ghaziabad Suburban Section')).toBeVisible();

    // Switch to Signals tab
    await page.getByRole('button', { name: /Signals/i }).click();
    await expect(page.getByText('AUTOMATIC_BLOCK').first()).toBeVisible();

    // Switch to Train Fleet tab
    await page.getByRole('button', { name: /Fleet/i }).click();
    await expect(page.getByText('Lucknow Swarna Shatabdi')).toBeVisible();
    await expect(page.getByText('Vande Bharat Express')).toBeVisible();

    // Launch 3D Digital Twin from top bar
    const twinBtn = page.getByRole('button', { name: 'Open 3D Twin' }).first();
    await expect(twinBtn).toBeVisible();
    await twinBtn.click();

    await expect(page.getByText('DIGITAL TWIN INSPECTION')).toBeVisible();
    await page.locator('button[title="Close inspection"]').click();
    await expect(page.getByText('DIGITAL TWIN INSPECTION')).not.toBeVisible();

    // Screenshot network workspace
    await page.screenshot({ path: 'test-results/network-workspace-1440x900.png' });
  });

  test('05. /work-orders enables filtering, search, and work order inspection drawer', async ({ page }) => {
    await page.goto('/work-orders');

    // Verify Work Orders Workspace Header
    await expect(page.getByRole('heading', { name: 'Maintenance Work Orders & Requisitions' })).toBeVisible();
    await expect(page.getByText('Engineering, Signalling, and 25 kV Traction electrical possession blocks')).toBeVisible();

    // Verify Search input and filter by CSM
    const searchInput = page.getByPlaceholder('Search by Work Order ID, asset, task code, or location...');
    await expect(searchInput).toBeVisible();
    await searchInput.fill('CSM');

    // Row should filter in table
    const tableRow = page.getByRole('table').getByText('Plain Track CSM Tamping - Up Main Line');
    await expect(tableRow).toBeVisible();

    // Click on work order row to inspect
    await tableRow.click();

    // Verify detail drawer opens
    const inspector = page.getByRole('complementary', { name: 'Contextual Entity Inspector' });
    await expect(inspector).toBeVisible();
    await expect(inspector.getByText('TSK-TRK-001')).toBeVisible();
    await expect(inspector.getByText('POSSESSION WINDOW & SCHEDULE')).toBeVisible();

    // Screenshot work orders workspace
    await page.screenshot({ path: 'test-results/work-orders-1440x900.png' });
  });

  test('06. /governance presents safety validation findings, Four-Eyes status, and SHA-256 fingerprint', async ({ page }) => {
    await page.route('**/api/v1/plan-versions*', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            plan_version_id: 'PV-20261002-5F8A180A',
            version_number: 1,
            planning_run_id: 'RUN-20261002-FAAAEF76',
            scenario_id: 'SCN-DEMO-001',
            status: 'PENDING_REVIEW',
            scheduler_type: 'CP_SAT',
            schedule_identity: 'bae346ecf37b1fd80608cc5e0b8dae030517a44d5d5305f640d5767ed46999aa',
            is_approvable: true,
            validation_status: 'VALID',
            created_at: '2026-10-02T18:56:37.403807Z',
            created_by: 'chief_operations_admin',
            total_scheduled: 29,
            total_unscheduled: 1,
          },
        ]),
      });
    });

    await page.goto('/governance');

    // Verify Governance Header & Pipeline
    await expect(page.getByRole('heading', { name: 'Safety Validation & Human Governance' })).toBeVisible();
    await expect(page.getByText('FORMAL OPERATIONAL GOVERNANCE PIPELINE')).toBeVisible();

    // Verify Four-Eyes principle status card
    await expect(page.getByText('Four-Eyes Operational Principle')).toBeVisible();
    await expect(page.getByText('chief_operations_admin').first()).toBeVisible();

    // Verify Cryptographic SHA-256 fingerprint section
    await expect(page.getByText('Cryptographic Plan Identity & Proof')).toBeVisible();
    await expect(page.getByText('bae346ecf37b1fd80608cc5e0b8dae030517a44d5d5305f640d5767ed46999aa')).toBeVisible();

    // Screenshot governance workspace
    await page.screenshot({ path: 'test-results/governance-1440x900.png' });
  });

  test('07. /copilot presents explainable AI interface with citations and safety disclaimers', async ({ page }) => {
    await page.goto('/copilot');

    // Verify Copilot Header and Read-Only Explainer role
    await expect(page.getByRole('heading', { name: 'AI Decision Support Copilot' })).toBeVisible();
    await expect(page.getByText('READ-ONLY EXPLAINER')).toBeVisible();
    await expect(page.getByText('Zero write-tools • Does NOT schedule trains')).toBeVisible();

    // Verify safety disclaimer banner
    await expect(page.getByText(/The Copilot cannot approve plans/i)).toBeVisible();

    // Verify deterministic evidence chips exist
    await expect(page.getByText('Verified Evidence Records')).toBeVisible();
    await expect(page.getByText('Deterministic Safety Boundary')).toBeVisible();

    // Verify quick inquiry button
    await expect(page.getByRole('button', { name: /Why was TSK-0007 not scheduled\?/i })).toBeVisible();

    // Screenshot copilot workspace
    await page.screenshot({ path: 'test-results/copilot-1440x900.png' });
  });

  test('08. Full HD Viewport (1920x1080) Layout and Responsiveness Check', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.goto('/planning');

    // Verify layout stability at 1080p using specific accessible role
    const navSidebar = page.getByRole('complementary', { name: 'Railway Operations Navigation' });
    await expect(navSidebar).toBeVisible();
    await expect(page.getByRole('button', { name: 'Railway Map' })).toBeVisible();

    // Screenshot planning at 1920x1080
    await page.screenshot({ path: 'test-results/planning-workspace-1920x1080.png', fullPage: true });
  });

  test('09. Global Command Palette (Ctrl+K) opens, filters corridor assets, and closes via Escape', async ({ page }) => {
    await page.goto('/planning');

    // 1. Open search via TopBar search button
    const searchBtn = page.getByRole('button', { name: 'Global Search' });
    await expect(searchBtn).toBeVisible();
    await searchBtn.click();

    // 2. Verify dialog is open
    const searchDialog = page.getByRole('dialog', { name: 'Corridor Command Search' });
    await expect(searchDialog).toBeVisible();

    // 3. Type search query for high-speed train
    const searchInput = searchDialog.getByPlaceholder('Search trains, work orders, tracks, stations, signals, OHE, rules...');
    await expect(searchInput).toBeVisible();
    await searchInput.fill('Vande Bharat');

    // 4. Verify search result appears
    await expect(searchDialog.getByText('22436 — Vande Bharat Express')).toBeVisible();

    // Screenshot command search palette
    await page.screenshot({ path: 'test-results/command-search-overlay.png' });

    // 5. Close with Escape key
    await page.keyboard.press('Escape');
    await expect(searchDialog).not.toBeVisible();
  });

  test('10. Operational Notification Drawer opens, displays severity groups, and supports filtering', async ({ page }) => {
    await page.goto('/planning');

    // 1. Open notification drawer via TopBar bell
    const notifBtn = page.getByRole('button', { name: 'Operational Notifications' });
    await expect(notifBtn).toBeVisible();
    await notifBtn.click();

    // 2. Verify drawer is open
    const notifDrawer = page.getByRole('dialog', { name: 'Operational Notifications' });
    await expect(notifDrawer).toBeVisible();
    await expect(notifDrawer.getByText('Headway Buffer Compression on SEC-12')).toBeVisible();

    // 3. Filter by CRITICAL
    await notifDrawer.getByRole('button', { name: 'CRITICAL' }).click();
    await expect(notifDrawer.getByText('Headway Buffer Compression on SEC-12')).toBeVisible();

    // Screenshot notification drawer
    await page.screenshot({ path: 'test-results/notification-drawer.png' });

    // 4. Close notification drawer
    await notifDrawer.getByRole('button', { name: 'Close dialog' }).click();
    await expect(notifDrawer).not.toBeVisible();
  });

  test('11. /overview situational cards 2 and 4 open conflict drawer and Four-Eyes approval modal', async ({ page }) => {
    await page.goto('/overview');

    // 1. Card 2: Click "2. WHAT NEEDS ATTENTION?"
    const conflictCard = page.getByText('2. WHAT NEEDS ATTENTION?');
    await expect(conflictCard).toBeVisible();
    await conflictCard.click();

    // Verify Entity Inspector drawer opens with the conflict
    const inspector = page.getByRole('complementary', { name: 'Contextual Entity Inspector' });
    await expect(inspector).toBeVisible();
    await expect(inspector.getByText('CONF-HDW-01')).toBeVisible();
    await expect(inspector.getByText('CRITICAL CONFLICT')).toBeVisible();

    // Close conflict drawer
    await page.getByRole('button', { name: 'Close dialog' }).click();
    await expect(inspector).not.toBeVisible();

    // 2. Card 4: Click "4. DECISION REQUIRED" navigates to formal Governance workspace
    const decisionCard = page.getByText('4. DECISION REQUIRED');
    await expect(decisionCard).toBeVisible();
    await decisionCard.click();

    // Verify operator is navigated to the formal Four-Eyes governance workspace
    await expect(page).toHaveURL(/.*governance/);
    await expect(page.getByRole('heading', { name: 'Safety Validation & Human Governance' })).toBeVisible();
  });

  test('12. /planning operates as unified full-workspace layout without Expand modal obstruction', async ({ page }) => {
    await page.goto('/planning');

    // 1. Verify Expand button does NOT exist
    const expandBtn = page.getByRole('button', { name: 'Expand', exact: true });
    await expect(expandBtn).not.toBeVisible();

    // 2. Verify corridor workspace is directly rendered
    await expect(page.getByText('NDLS → CNB (440 km Trunk)').first()).toBeVisible();
    await page.screenshot({ path: 'test-results/planning-unified-workspace.png' });
  });
});
